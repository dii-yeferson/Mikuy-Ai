from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from app import coach_pipeline as pipeline
from app.coach_calculations import arithmetic, calculate
from app.coach_contracts import AnswerDraft, AnswerReview, FoodAmount, QueryIntent, SupportedClaim
from app.coach_intent import local_intent
from app.coach_rag import (
    DOCUMENTS,
    ArticleParser,
    _cache,
    evidence_for,
    fetch_document,
    rank_chunks,
)
from app.config import settings
from app.knowledge import CARDS
from app.safety import check_question
from app.schemas import ProfileIn
from fastapi import HTTPException


def intent(**values):
    return QueryIntent(topic="nutrition", rewritten_question="consulta", **values)


@pytest.mark.parametrize(
    "expression, expected",
    [("17.5 * 3 + 2", "54.5"), ("(12+8)/4", "5"), ("0.1+0.2", "0.3"), ("-2*3", "-6")],
)
def test_decimal_operations(expression, expected):
    assert arithmetic(expression) == Decimal(expected)


@pytest.mark.parametrize(
    "expression", ["__import__('os')", "2**10000", "1/0", "float('nan')", "[1,2]", "1e999"]
)
def test_calculator_rejects_code_and_invalid_operations(expression):
    with pytest.raises((ValueError, SyntaxError)):
        arithmetic(expression)


def test_nutrition_uses_catalog_math_not_generated_total():
    query = "Calcula 2 unidades de huevo"
    request = intent(
        calculation="nutrition",
        amounts=[
            FoodAmount(food="huevo", quantity=2, unit="unid", evidence_span="2 unidades de huevo")
        ],
    )
    from app.catalog import INGREDIENTS

    result = calculate(request, query, [], ProfileIn(), None)
    assert result["verified"]
    assert Decimal(result["totals"]["kcal"]) == 2 * Decimal(
        str(INGREDIENTS["huevo"]["nutrients"]["kcal"])
    )
    assert result["estimated"] and "estimaciones" in result["answer"]


@pytest.mark.parametrize(
    "food, unit, preparation, span",
    [
        ("pollo", "g", "", "200 g de pollo"),
        ("arroz", "g", "cocido", "200 g de arroz cocido"),
        ("huevo", "g", "", "200 g de huevo"),
        ("huevo", "unid", "", "2 unidades de huevo"),
    ],
)
def test_no_guessed_cut_preparation_conversion_or_amount(food, unit, preparation, span):
    request = intent(
        calculation="nutrition",
        amounts=[
            FoodAmount(
                food=food, quantity=200, unit=unit, preparation=preparation, evidence_span=span
            )
        ],
    )
    result = calculate(request, span, [], ProfileIn(), None)
    assert not result["verified"]


def test_operand_must_be_number_not_substring():
    request = QueryIntent(
        topic="general", rewritten_question="calcula", calculation="arithmetic", expression="5+5"
    )
    assert not calculate(request, "35 + 35", [], ProfileIn(), None)["verified"]


def test_contextual_followup_and_new_topic():
    previous = [
        SimpleNamespace(question="¿Puedo comer mango?", answer="Puedes incluir fruta entera.")
    ]
    assert "mango" in local_intent("¿y eso?", previous).rewritten_question
    assert "mango" not in local_intent("Explícame la gravedad", previous).rewritten_question


def test_general_topic_no_health_rag(monkeypatch):
    query = QueryIntent(topic="general", rewritten_question="¿Qué es la gravedad?")
    cards, state = evidence_for(query, ["diabetes"])
    assert cards == [] and state["scope"] == "general_knowledge"


def test_renal_document_not_excluded_by_nutrition_classification(monkeypatch):
    monkeypatch.setattr(settings(), "coach_live_rag", True)
    fetched = []
    monkeypatch.setattr("app.coach_rag.fetch_document", lambda key: fetched.append(key))
    evidence_for(QueryIntent(topic="nutrition", rewritten_question="potasio renal"))
    assert "nih-kidney" in fetched


def test_ingredient_price_does_not_return_whole_menu_budget():
    query = QueryIntent(
        topic="budget", rewritten_question="Cuánto cuesta el arroz", calculation="budget"
    )
    result = calculate(query, query.rewritten_question, [], ProfileIn(), None)
    assert "alimento y su cantidad" in result["answer"]


def test_colloquial_food_normalization():
    from app.coach_intent import normalized_input

    assert "pollo" in normalized_input("kiero poyo frito")


def test_server_binds_real_excerpt():
    card = next(c for c in CARDS if c["id"] == "frituras")
    draft = AnswerDraft(
        answer="Conviene limitar las frituras. [1]",
        sources=["frituras"],
        evidence_level="cited",
        claims=[SupportedClaim(statement="Conviene limitar las frituras", source_id="frituras")],
    )
    pipeline.validate_draft(draft, ProfileIn(), [card], intent())
    assert draft.claims[0].excerpt == card["text"]


def test_unsupported_blanket_composition_rejected():
    draft = AnswerDraft(answer="Todo pollo frito tiene muchas grasas trans.")
    with pytest.raises(ValueError, match="No atribuyas"):
        pipeline.validate_draft(draft, ProfileIn(), [], intent())


def test_document_extraction_and_retrieval():
    parser = ArticleParser()
    parser.feed(
        "<nav>ignore this</nav><main><h1>Renal</h1><p>Kidneys manage potassium in the body.</p><script>ignore this too</script></main>"
    )
    assert "ignore" not in "".join(parser.parts)
    chunks = [
        dict(id="renal", text="Kidney potassium potassium balance."),
        dict(id="other", text="Fruit salad delicious recipe."),
    ]
    assert rank_chunks("kidney potassium", chunks)[0]["id"] == "renal"


def test_fetch_cache_registry_and_no_redirects(monkeypatch):
    _cache.clear()
    real = httpx.Client
    requests = []

    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="<p>" + "Nutrition and dietary evidence from an official document. " * 4 + "</p>",
        )

    monkeypatch.setattr(
        httpx, "Client", lambda **kw: real(**kw, transport=httpx.MockTransport(handler))
    )
    one = fetch_document("who-diet")
    two = fetch_document("who-diet")
    assert one == two and len(requests) == 1
    assert one["digest"] and one["fetched_at"] and not one["stale"]
    with pytest.raises(ValueError):
        fetch_document("http://127.0.0.1/secrets")
    assert requests == [DOCUMENTS["who-diet"]["url"]]
    _cache.clear()


def test_retrieval_outage_does_not_claim_live_evidence(monkeypatch):
    monkeypatch.setattr(settings(), "coach_live_rag", True)
    monkeypatch.setattr("app.coach_rag.fetch_document", lambda key: None)
    cards, state = evidence_for(
        QueryIntent(
            topic="clinical",
            rewritten_question="kidney potassium renal",
            search_terms=["kidney", "potassium"],
        )
    )
    assert state["live"] == 0 and state["unavailable"]
    assert not any(c["kind"] == "document_excerpt" for c in cards)


def test_claim_requires_actual_excerpt_and_registered_source():
    card = next(c for c in CARDS if c["id"] == "frituras")
    valid = AnswerDraft(
        answer="Conviene limitar las frituras. [1]",
        sources=[card["id"]],
        evidence_level="cited",
        claims=[
            SupportedClaim(
                statement="Conviene limitar las frituras.",
                source_id=card["id"],
                excerpt="Conviene limitar las frituras.",
            )
        ],
    )
    pipeline.validate_draft(valid, ProfileIn(), [card], intent())
    invalid = valid.model_copy(deep=True)
    invalid.claims[0].excerpt = "Un estudio de 2029 demuestra que esto cura la diabetes."
    with pytest.raises(ValueError):
        pipeline.validate_draft(invalid, ProfileIn(), [card], intent())
    invalid = valid.model_copy(deep=True)
    invalid.answer += " https://inventada.example/study"
    with pytest.raises(ValueError):
        pipeline.validate_draft(invalid, ProfileIn(), [card], intent())


def test_clinical_education_is_not_dose_change():
    assert check_question("¿Qué es la insulina y para qué sirve?") is None
    assert check_question("¿Por qué se ajusta el potasio en enfermedad renal?") is None
    assert check_question("¿Cuánta insulina me pongo?")
    assert check_question("Tengo dolor de pecho y no puedo respirar")


def test_pipeline_general_answer_has_no_nutrition_profile(monkeypatch):
    monkeypatch.setattr(pipeline, "configured", lambda: True)
    monkeypatch.setattr(
        pipeline,
        "interpret",
        lambda *a: QueryIntent(topic="general", rewritten_question="¿Por qué el cielo es azul?"),
    )
    seen = []

    def model(system, context, schema, **kwargs):
        seen.append(context)
        if schema is AnswerReview:
            return AnswerReview(accepted=True)
        return AnswerDraft(answer="Por la dispersión de la luz solar en la atmósfera.")

    monkeypatch.setattr(pipeline, "completion", model)
    result = pipeline.run_coach(
        "¿Por qué el cielo es azul?", ProfileIn(health=["diabetes"]), None, [], True
    )
    assert result.mode == "general" and not result.sources
    assert all(c["profile"] == {} and c["evidence"] == [] for c in seen)


def test_reviewer_failure_prevents_unverified_answer(monkeypatch):
    monkeypatch.setattr(pipeline, "configured", lambda: True)
    monkeypatch.setattr(
        pipeline,
        "interpret",
        lambda *a: QueryIntent(topic="general", rewritten_question="pregunta"),
    )

    def model(system, context, schema, **kwargs):
        return (
            AnswerReview(accepted=False, issues=["Contradice el contexto"])
            if schema is AnswerReview
            else AnswerDraft(answer="Respuesta inconsistente")
        )

    monkeypatch.setattr(pipeline, "completion", model)
    with pytest.raises(HTTPException) as error:
        pipeline.run_coach("pregunta", ProfileIn(), None, [], True)
    assert error.value.status_code == 502
