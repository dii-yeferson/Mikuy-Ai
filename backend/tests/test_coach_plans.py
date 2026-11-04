from decimal import Decimal

from app.coach_plans import Selection, propose
from app.schemas import ProfileIn

from tests.conftest import profile, register


def proposal(c):
    register(c)
    profile(c)
    r = c.post("/api/coach", json={"question": "Prepara desayuno, almuerzo y cena con 20 soles"})
    assert r.status_code == 201, r.text
    return r.json()["proposal"]


def test_full_flow(client):
    c = client
    p = proposal(c)
    assert len(p["recipes"]) == 3 and p["total"] <= 20
    assert round(sum(r["cost"] for r in p["recipes"]), 2) == p["total"]
    for _ in range(2):
        r = c.post(
            f"/api/coach-plans/{p['id']}/save",
            json={"recipe_id": p["recipes"][0]["recipe_id"], "expected_version": 1},
        )
        assert r.status_code == 200, r.text
    assert len(c.get("/api/coach-plans/saved/recipes").json()) == 1
    data = {
        "expected_version": 1,
        "placements": [
            {"recipe_id": r["recipe_id"], "date": "2026-11-05", "meal": r["kind"]}
            for r in p["recipes"]
        ],
    }
    first = c.post(f"/api/coach-plans/{p['id']}/apply", json=data)
    assert first.status_code == 200, first.text
    first = first.json()
    assert len(first["plan"]["meals"]) == 3
    again = c.post(f"/api/coach-plans/{p['id']}/apply", json=data)
    assert again.status_code == 200 and again.json()["plan_id"] == first["plan_id"]
    assert len(c.get("/api/plans").json()) == 1
    expected = {}
    for r in p["recipes"]:
        for i in r["ingredients"]:
            expected[i["ingredient_id"]] = expected.get(i["ingredient_id"], Decimal(0)) + Decimal(
                str(i["quantity"])
            )
    shopping = c.get(f"/api/plans/{first['plan_id']}/shopping").json()
    assert {
        i["ingredient_id"]: Decimal(str(i["planned_quantity"])) for i in shopping["items"]
    } == expected
    assert c.get("/api/coach").json()[0]["proposal"]["id"] == p["id"]


def test_replace_stale_and_collision(client):
    p = proposal(client)
    new = client.patch(
        f"/api/coach-plans/{p['id']}", json={"expected_version": 1, "replace_kind": "Desayuno"}
    )
    assert new.status_code == 200, new.text
    new = new.json()
    assert new["recipes"][0]["recipe_id"] != p["recipes"][0]["recipe_id"] and new["total"] <= 20
    assert (
        client.patch(
            f"/api/coach-plans/{p['id']}", json={"expected_version": 1, "servings": 1}
        ).status_code
        == 409
    )
    item = new["recipes"][0]
    data = {
        "expected_version": 2,
        "placements": [
            {"recipe_id": item["recipe_id"], "date": "2026-11-05", "meal": item["kind"]}
        ],
    }
    assert client.post(f"/api/coach-plans/{p['id']}/apply", json=data).status_code == 200
    changed = client.patch(
        f"/api/coach-plans/{p['id']}", json={"expected_version": 2, "replace_kind": "Desayuno"}
    ).json()
    data["expected_version"] = 3
    data["placements"][0]["recipe_id"] = changed["recipes"][0]["recipe_id"]
    assert client.post(f"/api/coach-plans/{p['id']}/apply", json=data).status_code == 409


def test_scope(client):
    p = proposal(client)
    client.post("/api/auth/logout")
    register(client, "other@example.com")
    profile(client)
    assert (
        client.post(
            f"/api/coach-plans/{p['id']}/save",
            json={"recipe_id": p["recipes"][0]["recipe_id"], "expected_version": 1},
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/coach-plans/{p['id']}", json={"expected_version": 1, "servings": 1}
        ).status_code
        == 404
    )
    assert client.get("/api/coach-plans/saved/recipes").json() == []
    assert (
        client.post(
            f"/api/coach-plans/{p['id']}/apply",
            json={"expected_version": 1, "placements": [{"recipe_id": "fake", "meal": "Cena"}]},
        ).status_code
        == 422
    )


def test_missing_and_infeasible():
    p = ProfileIn(completed=True)
    assert propose("Prepara desayuno y cena", p, False)["doc"] is None
    assert propose("Prepara desayuno almuerzo y cena con 0.01 soles", p, False)["doc"] is None
    assert propose("¿Cuánto cuesta mi compra?", p, False) is None


def test_model_validation(monkeypatch):
    from app import coach_plans

    p = ProfileIn(completed=True, allergies=["huevo", "leche"])
    monkeypatch.setattr(coach_plans, "configured", lambda: True)

    def fake(system, context, schema, validate, **kwargs):
        try:
            validate(Selection(recipe_ids=["inventada"]))
        except ValueError:
            pass
        else:
            assert False
        from fastapi import HTTPException

        raise HTTPException(502, "Modelo inválido")

    monkeypatch.setattr(coach_plans, "completion", fake)
    result = propose("Prepara desayuno almuerzo y cena con 20 soles", p, True)
    assert result["doc"]["source"] == "catalogo_respaldo"
    from app.catalog import BY_ID, suitable

    assert all(suitable(BY_ID[r], p) for r in result["doc"]["recipe_ids"])


def test_portions(client):
    p = proposal(client)
    from app.db import SessionLocal
    from app.models import User
    from sqlalchemy import select

    with SessionLocal() as db:
        user = db.scalar(select(User))
        user.tier = "familiar"
        db.commit()
    new = client.patch(f"/api/coach-plans/{p['id']}", json={"expected_version": 1, "servings": 2})
    assert new.status_code == 200, new.text
    new = new.json()
    for a, b in zip(p["recipes"], new["recipes"]):
        assert b["nutrition_total"]["kcal"] == round(a["nutrition_total"]["kcal"] * 2, 2)
        assert b["ingredients"][0]["quantity"] == a["ingredients"][0]["quantity"] * 2
    assert abs(new["total"] - 2 * p["total"]) < 0.05


def test_followup_and_profile_change(client):
    register(client)
    profile(client)
    first = client.post("/api/coach", json={"question": "Prepara desayuno y cena"}).json()
    assert first["proposal"] is None
    p = client.post(
        "/api/coach", json={"question": "20 soles", "conversation_id": first["conversation_id"]}
    ).json()["proposal"]
    assert len(p["recipes"]) == 2
    from app.catalog import BY_ID, INGREDIENTS

    rid = p["recipes"][0]["recipe_id"]
    ingredient = BY_ID[rid]["ingredients"][0]["ingredient_id"]
    profile(client, excluded=[INGREDIENTS[ingredient]["name"]])
    r = client.post(
        f"/api/coach-plans/{p['id']}/save", json={"recipe_id": rid, "expected_version": 1}
    )
    assert r.status_code == 422


def test_explicit_allergy():
    from app.catalog import BY_ID, INGREDIENTS

    result = propose(
        "Prepara desayuno y cena con 20 soles sin huevo", ProfileIn(completed=True), False
    )
    assert result["doc"]
    for rid in result["doc"]["recipe_ids"]:
        assert all(
            "huevo" not in INGREDIENTS[i["ingredient_id"]]["allergens"]
            for i in BY_ID[rid]["ingredients"]
        )


def test_individual_placement_and_duplicate_slots(client):
    p = proposal(client)
    rid = p["recipes"][0]["recipe_id"]
    payload = {
        "expected_version": 1,
        "placements": [{"recipe_id": rid, "date": "2026-11-10", "meal": "Cena"}],
    }
    saved = client.post(f"/api/coach-plans/{p['id']}/apply", json=payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()["plan"]["meals"][0]["kind"] == "Cena"
    assert saved.json()["plan"]["meals"][0]["recipe_id"] == rid
    payload["placements"] *= 2
    assert client.post(f"/api/coach-plans/{p['id']}/apply", json=payload).status_code == 422


def test_enumerated_model_schema(monkeypatch):
    import pytest
    from app import coach_plans
    from pydantic import ValidationError

    monkeypatch.setattr(coach_plans, "configured", lambda: True)

    def fake(system, context, schema, validate, **kwargs):
        with pytest.raises(ValidationError):
            schema.model_validate({"recipe_ids": ["inventada"] * len(context["kinds"])})
        result = schema.model_validate({"recipe_ids": context["valid_default"]})
        validate(result)
        return result

    monkeypatch.setattr(coach_plans, "completion", fake)
    result = propose(
        "Prepara desayuno almuerzo y cena con 20 soles", ProfileIn(completed=True), True
    )
    assert result["doc"]["source"] == "nvidia_catalogo"
