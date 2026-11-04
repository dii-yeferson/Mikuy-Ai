import json

import httpx
from app import nvidia
from app.coach_intent import local_intent
from app.config import settings
from app.knowledge import CARDS

from .conftest import profile, register


def provider(monkeypatch, replies, models=None, status=200, review=None):
    cfg = settings()
    monkeypatch.setattr(cfg, "nvidia_api_key", "not-a-real-key-for-tests")
    monkeypatch.setattr(cfg, "nvidia_model", "test-model")
    calls = []

    def handle(request):
        if request.url.path.endswith("/models"):
            return httpx.Response(
                200,
                json={
                    "data": [{"id": m} for m in (models if models is not None else ["test-model"])]
                },
            )
        payload = json.loads(request.content)
        system = payload["messages"][0]["content"]
        context = json.loads(payload["messages"][1]["content"])
        if status == 200 and '"title": "QueryIntent"' in system:
            reply = local_intent(context["question"], []).model_dump_json()
            return httpx.Response(200, json={"choices": [{"message": {"content": reply}}]})
        if status == 200 and '"title": "AnswerReview"' in system:
            reply = json.dumps(review or dict(accepted=True, issues=[]))
            return httpx.Response(200, json={"choices": [{"message": {"content": reply}}]})
        calls.append(payload)
        if status != 200:
            return httpx.Response(status, json={"error": "fake provider error"})
        reply = replies[min(len(calls) - 1, len(replies) - 1)]
        # Legacy fixtures describe generation only; supply explicit evidence contracts.
        try:
            data = json.loads(reply)
            if "answer" in data and data.get("sources") and "evidence_level" not in data:
                data["evidence_level"] = "cited"
                data["claims"] = [
                    dict(
                        statement=data["answer"],
                        source_id=s,
                        excerpt=next(c["text"] for c in CARDS if c["id"] == s),
                    )
                    for s in data["sources"]
                ]
                reply = json.dumps(data)
        except (ValueError, StopIteration):
            pass
        return httpx.Response(200, json={"choices": [{"message": {"content": reply}}]})

    real_client = httpx.Client
    monkeypatch.setattr(
        nvidia.httpx,
        "Client",
        lambda **kwargs: real_client(**kwargs, transport=httpx.MockTransport(handle)),
    )
    return calls


def test_invalid_json_retries_no_write_no_quota(client, monkeypatch):
    register(client)
    profile(client)
    calls = provider(monkeypatch, ["not json"])
    r = client.post("/api/coach", json={"question": "Organiza mis compras", "consent": True})
    assert r.status_code == 502
    assert len(calls) == 2
    assert client.get("/api/coach").json() == []
    assert client.get("/api/auth/me").json()["usage"]["coach"] == 0


def test_semantic_plan_retry_and_normalized_persistence(client, monkeypatch):
    register(client)
    profile(client, allergies=["huevo"])
    calls = provider(
        monkeypatch,
        [
            json.dumps({"recipe_ids": ["inventada"] * 21}),
            json.dumps({"recipe_ids": ["avena-manzana", "seco-pollo", "sopa-verduras-quinua"] * 7}),
        ],
    )
    r = client.post(
        "/api/plans", json={"start_date": "2026-10-19", "source": "nvidia", "consent": True}
    )
    assert r.status_code == 201, r.text
    assert len(calls) == 2
    assert r.json()["source"] == "nvidia"
    assert all(i["ingredient_id"] != "huevo" for m in r.json()["meals"] for i in m["ingredients"])
    assert client.get("/api/auth/me").json()["usage"]["plans"] == 1
    transmitted = json.loads(calls[0]["messages"][1]["content"])
    assert (
        "email" not in transmitted
        and "password" not in transmitted
        and "conditions" not in transmitted
    )


def test_coach_restricts_allergen_response_and_health_query(client, monkeypatch):
    register(client)
    profile(client, allergies=["huevo"])
    calls = provider(monkeypatch, [json.dumps({"answer": "Te sugiero comer huevos con pan."})])
    assert (
        client.post(
            "/api/coach", json={"question": "Ayúdame a organizar mi día", "consent": True}
        ).status_code
        == 502
    )
    assert len(calls) == 2
    assert client.get("/api/coach").json() == []
    r = client.post(
        "/api/coach", json={"question": "¿Qué comer si tengo diabetes?", "consent": True}
    )
    assert r.status_code == 502
    assert len(calls) == 4


def test_coach_success_persists_and_limits(client, monkeypatch):
    register(client)
    profile(client)
    provider(
        monkeypatch,
        [
            json.dumps(
                {"answer": "Revisa tu plan y agrupa las compras para la semana.", "sources": []}
            )
        ],
    )
    for _ in range(50):
        assert (
            client.post(
                "/api/coach", json={"question": "Ayúdame a organizar mis compras", "consent": True}
            ).status_code
            == 201
        )
    history = client.get("/api/coach").json()
    assert len(history) == 50 and history[0]["mode"] == "general"
    assert (
        client.post(
            "/api/coach", json={"question": "Una más por favor", "consent": True}
        ).status_code
        == 403
    )


def test_unavailable_model_and_provider_failures(client, monkeypatch):
    register(client)
    profile(client)
    provider(monkeypatch, ["{}"], models=[])
    r = client.post("/api/coach", json={"question": "Organiza mi día", "consent": True})
    assert r.status_code == 201 and r.json()["mode"] == "orientacion"


def test_provider_429_no_provider_body_exposed(client, monkeypatch):
    register(client)
    profile(client)
    provider(monkeypatch, ["{}"], status=429)
    r = client.post("/api/coach", json={"question": "Organiza mi día", "consent": True})
    assert r.status_code == 201 and r.json()["mode"] == "orientacion"
    assert "fake provider" not in r.text
