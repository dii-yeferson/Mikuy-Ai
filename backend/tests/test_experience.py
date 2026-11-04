import base64
from copy import deepcopy

import pytest
from app.experience_schemas import OnboardingAnswers
from app.main import app
from fastapi.testclient import TestClient
from pydantic import ValidationError

from .conftest import profile, register

HEADERS = {"X-Mikuy-Request": "1", "Origin": "http://localhost:5173"}
FOOD = {
    "date": "2026-10-21",
    "meal": "Desayuno",
    "name": "Avena declarada",
    "quantity": 50,
    "unit": "g",
    "kcal": 180,
    "protein": 6,
    "carbs": 30,
    "fat": 4,
    "nutrition_declared": True,
}


@pytest.mark.parametrize(
    "age,height,weight,target",
    [
        (10, 1, 5.25, 4.5),
        (14, 79.5, 19.9, 18.25),
        (15, 170.5, 62.35, 61.7),
        (0, 0.5, 0.1, 0.2),
        (180, 320.25, 12000.5, 13000.25),
    ],
)
def test_personal_values_are_not_limited_to_adults_or_fixed_ranges(
    client, age, height, weight, target
):
    data = client.get("/api/onboarding/draft").json()
    data["onboarding"].update(age=age, height=height, weight=weight, target_weight=target)
    assert client.put("/api/onboarding/draft", json=data).status_code == 200
    register(client)
    stored = client.get("/api/profile").json()["onboarding"]
    assert [stored[k] for k in ["age", "height", "weight", "target_weight"]] == [
        age,
        height,
        weight,
        target,
    ]
    updated = client.get("/api/profile").json()
    updated["onboarding"]["age"] = age + 1
    assert client.put("/api/profile", json=updated).status_code == 200
    assert client.get("/api/profile").json()["onboarding"]["age"] == age + 1


def test_personal_fields_reject_invalid_numbers_and_keep_saved_values(client):
    register(client)
    p = profile(client)
    p["onboarding"].update(age=10, height=140.5, weight=35.25)
    assert client.put("/api/profile", json=p).status_code == 200
    for field, value in [
        ("age", -1),
        ("age", 10.5),
        ("height", 0),
        ("height", -1),
        ("weight", 0),
        ("weight", -2),
        ("target_weight", 0),
    ]:
        invalid = deepcopy(p)
        invalid["onboarding"][field] = value
        assert client.put("/api/profile", json=invalid).status_code == 422
    assert client.get("/api/profile").json()["onboarding"] == p["onboarding"]
    for field in ["height", "weight", "target_weight"]:
        for value in [float("nan"), float("inf"), float("-inf")]:
            with pytest.raises(ValidationError):
                OnboardingAnswers.model_validate({field: value})
    for weight in [0.1, 12.45, 19.95, 62.35, 501, 10001]:
        r = client.post(
            "/api/entries", json={"kind": "peso", "date": "2026-10-21", "value": weight}
        )
        assert r.status_code == 201, r.text
        assert r.json()["value"] == weight
    for weight in [0, -1]:
        assert (
            client.post(
                "/api/entries", json={"kind": "peso", "date": "2026-10-21", "value": weight}
            ).status_code
            == 422
        )
    assert (
        client.post(
            "/api/entries", json={"kind": "agua", "date": "2026-10-21", "value": 3001}
        ).status_code
        == 422
    )


def test_onboarding_cookie_survives_and_is_consumed_only_by_owner(client):
    p = client.get("/api/onboarding/draft").json()
    p.update(completed=True, budget=190)
    p["onboarding"].update(age=28, height=170, weight=70)
    assert client.put("/api/onboarding/draft", json=p).status_code == 200
    cookie = client.cookies.get("mikuy_onboarding")
    assert cookie
    with TestClient(app, headers=HEADERS) as other:
        assert other.get("/api/onboarding/draft").json()["budget"] != 190
        register(other, "other@example.com")
        assert other.get("/api/profile").json()["completed"] is False
    assert client.get("/api/onboarding/draft").json()["onboarding"]["age"] == 28
    register(client)
    assert not client.cookies.get("mikuy_onboarding")
    assert client.get("/api/profile").json()["budget"] == 190
    assert client.get("/api/onboarding/draft").json()["completed"] is False


def test_settings_percentages_and_nested_persistence(client):
    register(client)
    p = profile(client)
    p["settings"].update(
        appearance="Claro",
        protein_percent=30,
        carbs_percent=40,
        fat_percent=30,
        reminders={"Agua": {"enabled": True, "time": "12:15", "days": [0, 2], "interval_hours": 2}},
    )
    assert client.put("/api/profile", json=p).status_code == 200
    assert client.get("/api/profile").json()["settings"]["reminders"]["Agua"]["days"] == [0, 2]
    p["settings"]["fat_percent"] = 50
    assert client.put("/api/profile", json=p).status_code == 422
    p["settings"]["fat_percent"] = 30
    p["settings"]["meal_distribution"] = {"Cena": 120}
    assert client.put("/api/profile", json=p).status_code == 422


def test_diary_math_copy_scale_favorites_streak_and_isolation(client):
    register(client)
    r = client.post("/api/diary", json=FOOD)
    assert r.status_code == 201, r.text
    food_id = r.json()["id"]

    def act(action, **extra):
        r = client.post(
            "/api/diary/actions", json={"action": action, "date": FOOD["date"], **extra}
        )
        assert r.status_code == 200, r.text

    act("porciones", meal="Desayuno", multiplier=2)
    d = client.get("/api/diary/" + FOOD["date"]).json()
    assert d["totals"]["kcal"] == 360 and d["foods"][0]["quantity"] == 100
    act("copiar", target_date="2026-10-22", target_meal="Cena")
    copied = client.get("/api/diary/2026-10-22").json()
    assert copied["foods"][0]["meal"] == "Cena" and copied["totals"]["kcal"] == 360
    act("finalizar")
    act("finalizar")
    assert client.get("/api/streaks").json()["registered"] == 1
    act("favorito", meal="Desayuno")
    favorite = client.get("/api/favorites").json()[0]
    r = client.post(
        "/api/favorites/" + favorite["id"] + "/use",
        json={"action": "copiar", "date": "2026-10-23", "meal": "Almuerzo"},
    )
    assert r.status_code == 201
    assert client.get("/api/diary/2026-10-23").json()["totals"]["kcal"] == 360
    with TestClient(app, headers=HEADERS) as other:
        register(other, "other@example.com")
        assert other.get("/api/diary/" + FOOD["date"]).json()["foods"] == []
        assert other.delete("/api/diary/food/" + food_id).status_code == 404
        assert (
            other.post(
                "/api/favorites/" + favorite["id"] + "/use",
                json={"action": "copiar", "date": FOOD["date"]},
            ).status_code
            == 404
        )
    act("vaciar")
    assert client.get("/api/streaks").json()["registered"] == 0


def test_diary_invalid_scale_is_422_and_rolls_back(client):
    register(client)
    data = {**FOOD, "quantity": 9000}
    assert client.post("/api/diary", json=data).status_code == 201
    assert (
        client.post(
            "/api/diary/actions",
            json={"action": "porciones", "date": FOOD["date"], "multiplier": 10},
        ).status_code
        == 422
    )
    assert client.get("/api/diary/" + FOOD["date"]).json()["foods"][0]["quantity"] == 9000


def test_photos_feedback_and_public_community_exclude_private_data(client):
    register(client)
    # Minimal valid PNG, isolated test fixture.
    image = (
        "data:image/png;base64,"
        + base64.b64encode(
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jWZkAAAAASUVORK5CYII="
            )
        ).decode()
    )
    photo = client.post("/api/photos", json={"date": FOOD["date"], "image": image}).json()
    attachment = client.post(
        "/api/photos", json={"date": FOOD["date"], "image": image, "purpose": "feedback"}
    ).json()
    assert len(client.get("/api/photos").json()) == 1
    assert all("image" not in r for r in client.get("/api/entries").json())
    assert (
        client.post(
            "/api/feedback",
            json={
                "category": "problema",
                "text": "Prueba de adjunto",
                "attachments": [attachment["id"]],
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/photos", json={"date": FOOD["date"], "image": "data:image/png;base64,YWJj"}
        ).status_code
        == 422
    )
    assert client.post("/api/community/posts", json={"text": "Texto público"}).status_code == 403
    p = profile(client, conditions="Información privada")
    p["settings"].update(public_profile=True, description="Mi descripción pública")
    assert client.put("/api/profile", json=p).status_code == 200
    assert (
        client.post("/api/community/posts", json={"text": "Publicación visible"}).status_code == 201
    )
    with TestClient(app, headers=HEADERS) as other:
        register(other, "other@example.com")
        assert other.get("/api/photos").json() == []
        assert other.delete("/api/entries/" + photo["id"]).status_code == 404
        assert (
            other.post(
                "/api/feedback",
                json={
                    "category": "problema",
                    "text": "Adjunto ajeno",
                    "attachments": [attachment["id"]],
                },
            ).status_code
            == 422
        )
        public = other.get("/api/community").json()
        assert len(public["people"]) == 1 and len(public["posts"]) == 1
        assert "Información privada" not in str(public) and "image" not in str(public)
    p["settings"]["public_profile"] = False
    client.put("/api/profile", json=p)
    assert client.get("/api/community").json()["posts"] == []
