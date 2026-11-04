from datetime import timedelta
from types import SimpleNamespace

from app.db import SessionLocal
from app.main import app, purge_conversations
from app.models import Conversation, Message, utcnow
from fastapi.testclient import TestClient
from sqlalchemy import select

from .conftest import profile, register

HEADERS = {"X-Mikuy-Request": "1", "Origin": "http://localhost:5173"}
BASE = "/api/coach/conversations"


def test_conversation_context_and_owner_isolation(client, monkeypatch):
    register(client)
    profile(client)
    contexts = []

    def answer(question, profile, plan, previous, consent, **kwargs):
        contexts.append([r.question for r in previous])
        return SimpleNamespace(answer="Respuesta de prueba", sources=[], mode="general")

    monkeypatch.setattr("app.routes_coach.run_coach", answer)
    first = client.post(BASE).json()["id"]
    second = client.post(BASE).json()["id"]
    for id, question in [
        (first, "Explícame las estrellas"),
        (second, "Explícame los volcanes"),
        (first, "¿Y eso por qué?"),
    ]:
        r = client.post("/api/coach", json={"question": question, "conversation_id": id})
        assert r.status_code == 201, r.text
        assert r.json()["conversation_id"] == id
    assert contexts == [[], [], ["Explícame las estrellas"]]
    assert len(client.get("/api/coach", params={"conversation_id": first}).json()) == 2
    assert len(client.get("/api/coach", params={"conversation_id": second}).json()) == 1
    assert {c["title"] for c in client.get(BASE).json()} == {
        "Explícame las estrellas",
        "Explícame los volcanes",
    }
    with TestClient(app, headers=HEADERS) as other:
        register(other, "other-chat@example.com")
        assert other.get(BASE).json() == []
        assert other.get("/api/coach", params={"conversation_id": first}).status_code == 404
        assert (
            other.post(
                "/api/coach", json={"question": "¿Cuánta insulina?", "conversation_id": first}
            ).status_code
            == 404
        )
        assert other.delete(BASE + "/" + first).status_code == 404
        assert other.post(BASE + "/restore", json={"ids": [first]}).status_code == 404


def test_delete_restore_clear_and_expired_purge(client):
    register(client)
    profile(client)
    first = client.post(BASE).json()["id"]
    r = client.post(
        "/api/coach",
        json={"question": "¿Cuál es mi presupuesto semanal?", "conversation_id": first},
    )
    assert r.status_code == 201
    second = client.post(BASE).json()["id"]
    removed = client.delete(BASE + "/" + first).json()
    assert removed["ids"] == [first]
    assert len(client.get(BASE).json()) == 1
    assert client.get("/api/coach", params={"conversation_id": first}).status_code == 404
    assert client.get("/api/account/export").json()["coach"] == []
    assert client.post(BASE + "/restore", json={"ids": removed["ids"]}).status_code == 200
    assert len(client.get("/api/coach", params={"conversation_id": first}).json()) == 1
    removed = client.delete(BASE).json()
    assert set(removed["ids"]) == {first, second}
    assert client.get(BASE).json() == []
    assert client.post(BASE + "/restore", json={"ids": removed["ids"]}).status_code == 200
    client.delete(BASE)
    with SessionLocal() as db:
        for row in db.scalars(select(Conversation)):
            row.delete_after = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.post(BASE + "/restore", json={"ids": [first]}).status_code in (404, 410)
    purge_conversations()
    with SessionLocal() as db:
        assert list(db.scalars(select(Message))) == []
        assert list(db.scalars(select(Conversation))) == []


def test_reply_parent_validation_and_cascade(client):
    from .test_community import make_public

    register(client)
    make_public(client)
    one = client.post("/api/community/posts", json={"text": "Primera publicación"}).json()["id"]
    two = client.post("/api/community/posts", json={"text": "Segunda publicación"}).json()["id"]
    url = "/api/community/posts/" + one + "/comments"
    root = client.post(url, json={"text": "Comentario"}).json()["id"]
    reply = client.post(url, json={"text": "Respuesta", "parent_id": root}).json()["id"]
    assert client.post(url, json={"text": "Otra respuesta", "parent_id": reply}).status_code == 201
    rows = client.get(url).json()
    assert [r["parent_id"] for r in rows] == [None, root, root]
    assert (
        client.post(
            "/api/community/posts/" + two + "/comments",
            json={"text": "No cruzar publicaciones", "parent_id": root},
        ).status_code
        == 404
    )
    assert client.post(url, json={"text": "No existe", "parent_id": "missing"}).status_code == 404
    assert client.delete("/api/community/comments/" + root).status_code == 204
    assert client.get(url).json() == []
