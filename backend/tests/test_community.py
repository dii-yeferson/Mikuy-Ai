from app.main import app
from fastapi.testclient import TestClient

from .conftest import profile, register

HEADERS = {"X-Mikuy-Request": "1", "Origin": "http://localhost:5173"}


def make_public(client):
    p = profile(client)
    p["settings"]["public_profile"] = True
    assert client.put("/api/profile", json=p).status_code == 200


def test_group_membership_posts_reactions_comments_permissions(client):
    register(client)
    make_public(client)
    g = client.post(
        "/api/community/groups", json={"name": "Cocina de casa", "description": "Grupo de pruebas"}
    ).json()
    assert g["joined"] and g["members"] == 1
    p = client.post(
        "/api/community/posts", json={"text": "Hoy cocinamos juntos", "group_id": g["id"]}
    ).json()
    with TestClient(app, headers=HEADERS) as other:
        register(other, "community-other@example.com")
        make_public(other)
        assert (
            other.post(
                "/api/community/posts", json={"text": "Sin unirme", "group_id": g["id"]}
            ).status_code
            == 403
        )
        assert (
            other.put(
                "/api/community/groups/" + g["id"], json={"name": "No autorizado"}
            ).status_code
            == 403
        )
        assert other.delete("/api/community/groups/" + g["id"]).status_code == 403
        assert other.put("/api/community/groups/" + g["id"] + "/membership").json()["members"] == 2
        assert other.put("/api/community/groups/" + g["id"] + "/membership").json()["members"] == 2
        url = "/api/community/posts/" + p["id"]
        assert (
            other.put(url + "/reaction", json={"kind": "heart"}).json()["reactions"]["heart"] == 1
        )
        assert (
            other.put(url + "/reaction", json={"kind": "heart"}).json()["reactions"]["heart"] == 1
        )
        swapped = other.put(url + "/reaction", json={"kind": "like"}).json()
        assert swapped["reactions"]["heart"] == 0 and swapped["reactions"]["like"] == 1
        c = other.post(url + "/comments", json={"text": "¡Me sumo!"}).json()
        assert client.get(url + "/comments").json()[0]["text"] == "¡Me sumo!"
        assert other.delete(url).status_code == 403
        assert client.delete("/api/community/comments/" + c["id"]).status_code == 204
        other.post(url + "/comments", json={"text": "Otra respuesta"})
        assert other.put(url + "/reaction", json={"kind": None}).json()["reactions"]["like"] == 0
        assert other.delete("/api/community/groups/" + g["id"] + "/membership").status_code == 204
        assert other.post(url + "/comments", json={"text": "Ya no soy miembro"}).status_code == 403
    assert client.delete("/api/community/groups/" + g["id"]).status_code == 204
    assert client.get("/api/community").json()["posts"] == []
    assert client.get("/api/community/posts/" + p["id"] + "/comments").status_code == 404


def test_private_profile_and_validation(client):
    register(client)
    assert client.post("/api/community/groups", json={"name": "Prueba"}).status_code == 403
    make_public(client)
    assert client.post("/api/community/groups", json={"name": "  "}).status_code == 422
    assert client.post("/api/community/posts", json={"text": " "}).status_code == 422
    p = client.post("/api/community/posts", json={"text": "Público"}).json()
    assert (
        client.put(
            "/api/community/posts/" + p["id"] + "/reaction", json={"kind": "inventada"}
        ).status_code
        == 422
    )
    saved = client.get("/api/profile").json()
    saved["settings"]["public_profile"] = False
    client.put("/api/profile", json=saved)
    assert client.get("/api/community").json()["posts"] == []
    assert client.get("/api/community/posts/" + p["id"] + "/comments").status_code == 404
