import json
import re

import pytest
from app.coach_response import checked_citations
from app.config import settings
from app.knowledge import CARDS, retrieve
from app.nvidia import CoachAnswer

from .conftest import profile, register
from .test_nvidia import provider


def ask(client, question, **extra):
    r = client.post("/api/coach", json=dict(question=question, **extra))
    assert r.status_code == 201, r.text
    return r.json()


def test_reported_question_direct_answer_and_persisted_followup(client):
    register(client)
    profile(client, health=["diabetes", "prediabetes", "obesidad"])
    r = ask(client, "QUIEROCOMO POLLO FRITO, ME RECOMIENDAS ?")
    assert r["answer"].startswith("Sobre el pollo frito:")
    assert "sin fritura" in r["answer"] and "30 %" not in r["answer"]
    assert "Considerando tu perfil" not in r["answer"]
    assert {s["id"] for s in r["sources"]} == {"frituras", "plato"}
    assert set(map(int, re.findall(r"\[(\d+)\]", r["answer"]))) == {1, 2}
    follow = ask(client, "¿Y cuánto me sirvo?")
    assert "pollo frito" in follow["answer"] and "No puedo fijar" in follow["answer"]
    changed = ask(client, "¿Puedo comer mango?")
    assert "mango" in changed["answer"] and "pollo" not in changed["answer"]
    assert len(client.get("/api/coach").json()) == 3


@pytest.mark.parametrize(
    "question, expected",
    [
        ("Quiero pollo broaster", "sin fritura"),
        ("¿Cuántas calorías tiene mi pollo frito?", "necesito la cantidad"),
        ("¿Puedo tomar gaseosa?", "agua"),
        ("¿Cuánto arroz me sirvo?", "un cuarto"),
        ("¿Cuánta sal al día?", "menos de 5 g"),
        ("Ayúdame a organizar mis compras", "lista de compras"),
        ("¿Qué puedo cenar?", "qué ingredientes"),
        ("¿Qué hago para bajar de peso sin pasar hambre?", "en qué momento"),
        ("quiero comer pollo frito toda la semana esta bien o no?", "No te recomendaría"),
    ],
)
def test_distinct_intents(client, question, expected):
    register(client)
    profile(client)
    assert expected.lower() in ask(client, question)["answer"].lower()


def test_unknown_question_does_not_return_disease_cards(client):
    register(client)
    profile(client, health=["diabetes"])
    assert retrieve("¿Quién ganó el partido de fútbol?", ["diabetes"]) == []
    r = ask(client, "¿Quién ganó el partido de fútbol?")
    assert r["sources"] == [] and r["mode"] == "orientacion"
    assert "Necesito concretar" in r["answer"]
    assert "diabetes" not in r["answer"]


def test_local_allergies_diet_and_exclusions(client):
    register(client)
    profile(client, allergies=["pescado"])
    assert "Evita" in ask(client, "¿Me recomiendas pescado frito?")["answer"]
    profile(client, diet="Vegano")
    assert "no coincide" in ask(client, "¿Me recomiendas pollo frito?")["answer"]
    profile(client, excluded=["pollo"])
    assert "exclusiones" in ask(client, "¿Me recomiendas pollo frito?")["answer"]


def test_no_adult_salt_target_for_minor(client):
    register(client)
    profile(client, onboarding=dict(age=10))
    r = ask(client, "¿Cuánta sal puedo comer?")
    assert "5 g" not in r["answer"] and r["sources"] == []


def test_sparse_citations_are_renumbered_and_bad_citations_rejected():
    cards = CARDS[:3]
    result = CoachAnswer(answer="Orientación respaldada [3].", sources=[cards[2]["id"]])
    answer, sources = checked_citations(result, cards)
    assert "[1]" in answer and sources[0]["id"] == cards[2]["id"]
    for answer, ids in [
        ("Texto [9].", []),
        ("Texto [1].", []),
        ("Texto [1].", ["inventada"]),
    ]:
        with pytest.raises(ValueError):
            checked_citations(CoachAnswer(answer=answer, sources=ids), cards)
    answer, sources = checked_citations(
        CoachAnswer(answer="Texto", sources=[cards[0]["id"]]), cards
    )
    assert answer == "Texto [1]" and sources[0]["id"] == cards[0]["id"]


def test_nvidia_direct_answer_and_prompt(client, monkeypatch):
    register(client)
    profile(client)
    calls = provider(
        monkeypatch,
        [
            json.dumps(
                dict(
                    answer="Para el pollo frito, prefiero recomendarte una preparación sin fritura [1].",
                    sources=["frituras"],
                )
            )
        ],
    )
    result = ask(client, "¿Me recomiendas pollo frito?", consent=True)
    assert result["mode"] == "ia"
    assert result["sources"][0]["id"] == "frituras"
    assert "Contesta directamente" in calls[0]["messages"][0]["content"]
    assert calls[0]["response_format"] == {"type": "json_object"}


def test_nvidia_irrelevant_valid_citation_retries_without_saving(client, monkeypatch):
    register(client)
    profile(client)
    calls = provider(
        monkeypatch,
        [json.dumps(dict(answer="Las grasas deben limitarse [1].", sources=["frituras"]))],
        review=dict(accepted=False, issues=["No responde a la pregunta sobre pollo frito"]),
    )
    r = client.post("/api/coach", json=dict(question="¿Me recomiendas pollo frito?", consent=True))
    assert r.status_code == 502 and len(calls) == 2
    assert client.get("/api/coach").json() == []
    assert client.get("/api/auth/me").json()["usage"]["coach"] == 0


def test_outage_retains_question_relevance(client, monkeypatch):
    register(client)
    profile(client)
    provider(monkeypatch, ["{}"], status=429)
    r = ask(client, "¿Me recomiendas pollo frito?", consent=True)
    assert r["mode"] == "fuentes" and r["answer"].startswith("Sobre el pollo frito:")


def test_lightning_uses_complete_json_without_thinking_budget(client, monkeypatch):
    register(client)
    profile(client)
    model = "nvidia/nemotron-3.5-lightning-30b-a3b"
    calls = provider(
        monkeypatch,
        [
            json.dumps(
                dict(
                    answer="Sobre el pollo frito, conviene limitar las frituras.",
                    sources=["frituras"],
                )
            )
        ],
        models=[model],
    )
    monkeypatch.setattr(settings(), "nvidia_model", model)
    result = ask(client, "¿Me recomiendas pollo frito?", consent=True)
    assert result["mode"] == "ia" and "[1]" in result["answer"]
    assert calls[0]["chat_template_kwargs"] == {"enable_thinking": False}
