from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from app.db import SessionLocal
from app.main import app
from app.models import Entry, Message, Plan, Profile, Session, Usage, User
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from .conftest import plan, profile, register


def test_auth_persistence_logout_and_validation(client):
    user = register(client)
    assert (
        "HttpOnly" in client.cookies.get("mikuy_session")
        or len(client.cookies.get("mikuy_session")) >= 60
    )
    r = client.get("/api/auth/me")
    assert r.json()["id"] == user["id"]
    assert "password" not in r.text
    with SessionLocal() as db:
        stored = db.get(User, user["id"])
        assert stored.password_hash.startswith("$argon2id$")
        assert stored.password_hash != "prueba-segura-2026"
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    assert (
        client.post(
            "/api/auth/login", json=dict(email="prueba@example.com", password="incorrecta-2026")
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login", json=dict(email="PRUEBA@example.com", password="prueba-segura-2026")
        ).status_code
        == 200
    )
    assert client.put("/api/profile", json=dict(budget=-10)).status_code == 422
    assert client.put("/api/profile", json=dict(allergies=["desconocido"])).status_code == 422


def test_registration_duplicates_and_cookie_flags(client):
    r = client.post(
        "/api/auth/register",
        json=dict(name="Prueba", email="unico@example.com", password="1234567890"),
    )
    assert r.status_code == 201
    assert "HttpOnly" in r.headers["set-cookie"]
    assert "SameSite=lax" in r.headers["set-cookie"]
    assert "Path=/api" in r.headers["set-cookie"]
    assert (
        client.post(
            "/api/auth/register",
            json=dict(name="Otro", email="UNICO@example.com", password="1234567890"),
        ).status_code
        == 409
    )


def test_complete_plan_edit_consolidation_and_restart(client):
    register(client)
    profile(client)
    p = plan(client)
    assert len(p["meals"]) == 21
    shopping = client.get(f"/api/plans/{p['id']}/shopping").json()
    assert Decimal(str(p["cost"])) == sum(
        Decimal(str(i["planned_cost"])) for i in shopping["items"]
    )
    assert Decimal(str(shopping["shopping_cost"])) == sum(
        Decimal(str(i["cost"])) for i in shopping["items"]
    )
    for i in shopping["items"]:
        expected = sum(
            part["quantity"]
            for m in p["meals"]
            for part in m["ingredients"]
            if part["ingredient_id"] == i["ingredient_id"]
        )
        assert abs(i["planned_quantity"] - expected) < 1e-6
        assert i["quantity"] >= i["planned_quantity"]
    original = p["meals"][1:]
    r = client.patch(
        f"/api/plans/{p['id']}/meals/0-Desayuno",
        json=dict(recipe_id="quinua-manzana", servings=1, expected_version=1),
    )
    assert r.status_code == 200, r.text
    changed = r.json()
    assert changed["meals"][1:] == original
    assert changed["version"] == 2
    stale = client.patch(
        f"/api/plans/{p['id']}/meals/0-Desayuno",
        json=dict(recipe_id="avena-manzana", servings=1, expected_version=1),
    )
    assert stale.status_code == 409
    # New HTTP client and fresh DB connection confirm persistent state.
    with TestClient(app, headers=client.headers, cookies=client.cookies) as other:
        assert other.get(f"/api/plans/{p['id']}").json()["meals"] == changed["meals"]
    listing = client.get(f"/api/plans/{p['id']}/shopping").json()
    i = listing["items"][0]
    r = client.patch(
        f"/api/plans/{p['id']}/shopping/{i['ingredient_id']}",
        json=dict(quantity=22, unit_price=0.01, checked=True),
    )
    assert r.status_code == 200
    saved = next(x for x in r.json()["items"] if x["ingredient_id"] == i["ingredient_id"])
    assert saved["quantity"] == 22 and saved["checked"]
    assert client.get(f"/api/plans/{p['id']}").json()["cost"] == changed["cost"]


def test_cross_account_isolation_and_export(client):
    register(client)
    profile(client)
    p = plan(client)
    client.post(
        "/api/entries", json=dict(kind="nota", date="2026-10-21", text="Nota privada de prueba")
    )
    entry = client.get("/api/entries").json()[0]
    register(client, "otra@example.com")
    assert client.get("/api/plans").json() == []
    assert client.get(f"/api/plans/{p['id']}").status_code == 404
    assert client.get(f"/api/plans/{p['id']}/shopping").status_code == 404
    assert (
        client.patch(
            f"/api/plans/{p['id']}/meals/0-Desayuno",
            json=dict(recipe_id="pan-palta-huevo", servings=1, expected_version=1),
        ).status_code
        == 404
    )
    assert client.delete("/api/entries/" + entry["id"]).status_code == 404
    assert "Nota privada" not in client.get("/api/account/export").text
    assert client.get("/api/coach").json() == []
    assert client.get("/api/profile").json()["completed"] is False


def test_allergies_diet_exclusions_and_changes(client):
    register(client)
    profile(
        client, allergies=["Glúten", "HUEVO", "Pescado"], excluded=["pollo"], diet="Vegetariano"
    )
    p = plan(client)
    for m in p["meals"]:
        for i in m["ingredients"]:
            assert not set(i["allergens"]) & {"gluten", "huevo", "pescado"}
            assert i["ingredient_id"] not in {"pechuga", "pollo-pierna", "res", "huevo", "bonito"}
    assert (
        client.patch(
            f"/api/plans/{p['id']}/meals/0-Desayuno",
            json=dict(recipe_id="pan-palta-huevo", servings=1, expected_version=1),
        ).status_code
        == 422
    )
    profile(client, allergies=["gluten", "leche"], excluded=["quinua"], diet="Vegano")
    assert client.post("/api/plans", json=dict(start_date="2026-10-21")).status_code == 422


def test_budget_failure_no_usage_and_existing_conflict_flag(client):
    register(client)
    profile(client, budget=20)
    r = client.post("/api/plans", json=dict(start_date="2026-10-21"))
    assert r.status_code == 422
    assert client.get("/api/auth/me").json()["usage"]["plans"] == 0
    profile(client)
    p = plan(client)
    profile(client, excluded=[p["meals"][0]["ingredients"][0]["name"]])
    assert client.get(f"/api/plans/{p['id']}").json()["conflicts"]


def test_tier_limits_and_simulation_cannot_reset_usage(client):
    register(client)
    profile(client)
    assert client.put("/api/profile", json=dict(servings=2)).status_code == 403
    for _ in range(4):
        plan(client)
    assert client.post("/api/plans", json=dict(start_date="2026-10-21")).status_code == 403
    assert (
        client.post("/api/subscription", json=dict(tier="premium", simulation=False)).status_code
        == 422
    )
    assert (
        client.post("/api/subscription", json=dict(tier="premium", simulation=True)).status_code
        == 200
    )
    profile(client, servings=3)
    assert (
        client.post("/api/subscription", json=dict(tier="gratis", simulation=True)).status_code
        == 422
    )
    profile(client, servings=1)
    assert (
        client.post("/api/subscription", json=dict(tier="gratis", simulation=True)).json()["usage"][
            "plans"
        ]
        == 4
    )


def test_concurrent_quota_atomic(client):
    register(client)
    profile(client)
    headers = {"X-Mikuy-Request": "1"}
    cookie = dict(client.cookies)

    def create(_):
        with TestClient(app, headers=headers, cookies=cookie) as c:
            return c.post("/api/plans", json=dict(start_date="2026-10-21")).status_code

    with ThreadPoolExecutor(max_workers=5) as pool:
        statuses = list(pool.map(create, range(5)))
    assert sorted(statuses) == [201, 201, 201, 201, 403]


def test_coach_without_ai_answers_from_sources_and_health_is_allowed(client):
    register(client)
    profile(client, health=["diabetes"])
    r = client.post("/api/coach", json=dict(question="¿Puedo comer mango si tengo diabetes?"))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["mode"] == "fuentes" and body["sources"]
    assert all(s["url"].startswith("https://") for s in body["sources"])
    assert client.get("/api/auth/me").json()["usage"]["coach"] == 1
    safety = client.post("/api/coach", json=dict(question="¿Cuánta insulina me pongo?"))
    assert safety.status_code == 201 and safety.json()["mode"] == "seguridad"
    assert client.get("/api/auth/me").json()["usage"]["coach"] == 1
    assert (
        client.post(
            "/api/plans", json=dict(start_date="2026-10-21", source="nvidia", consent=True)
        ).status_code
        == 503
    )
    p = plan(client)
    assert p["conditions"] == ["diabetes"]
    assert client.get("/api/auth/me").json()["usage"]["plans"] == 1


def test_today_done_adherence_and_report_limits(client):
    register(client)
    profile(client)
    p = plan(client)
    slot = p["meals"][0]["slot"]
    r = client.patch(f"/api/plans/{p['id']}/meals/{slot}/done", json=dict(done=True))
    assert r.status_code == 200 and r.json()["meals"][0]["done"] is True
    today = client.get("/api/today").json()
    assert today["adherence"]["done"] == 1 and today["plan"]["id"] == p["id"]
    assert client.get("/api/report").status_code == 403
    client.post("/api/subscription", json=dict(tier="premium", simulation=True))
    rep = client.get("/api/report?month=2026-10").json()
    assert rep["adherence"]["done"] == 1 and len(rep["weeks"]) == 1
    recipes = client.get("/api/catalog").json()["recipes"]
    assert len(recipes) >= 50 and all("nutrition" in x and "traffic" in x for x in recipes)


def test_csrf_origins_and_rate_limit(client):
    assert (
        client.post(
            "/api/auth/login", headers={"Origin": "https://hostile.example"}, json={}
        ).status_code
        == 403
    )
    with TestClient(app) as raw:
        assert raw.post("/api/auth/register", json={}).status_code == 403
    for _ in range(20):
        assert (
            client.post(
                "/api/auth/login", json=dict(email="nadie@example.com", password="incorrecta-2026")
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/auth/login", json=dict(email="nadie@example.com", password="incorrecta-2026")
        ).status_code
        == 429
    )


def test_entries_and_account_deletion_cascade(client):
    user = register(client)
    profile(client)
    plan(client)
    assert (
        client.post(
            "/api/entries", json=dict(kind="agua", date="2026-10-21", value=250)
        ).status_code
        == 201
    )
    assert (
        client.post("/api/entries", json=dict(kind="peso", date="2026-10-21", value=62)).status_code
        == 201
    )
    assert (
        client.post(
            "/api/entries", json=dict(kind="nota", date="2026-10-21", text="Prueba")
        ).status_code
        == 201
    )
    assert (
        client.post("/api/entries", json=dict(kind="peso", date="2026-10-21", value=0)).status_code
        == 422
    )
    assert (
        client.post("/api/entries", json=dict(kind="nota", date="2026-10-21", text="")).status_code
        == 422
    )
    assert len(client.get("/api/account/export").json()["entries"]) == 3
    assert (
        client.request("DELETE", "/api/account", json=dict(password="incorrecta")).status_code
        == 401
    )
    assert (
        client.request(
            "DELETE", "/api/account", json=dict(password="prueba-segura-2026")
        ).status_code
        == 204
    )
    assert client.get("/api/auth/me").status_code == 401
    with SessionLocal() as db:
        assert db.get(User, user["id"]) is None
        for model in [Session, Profile, Plan, Message, Usage, Entry]:
            assert db.scalar(select(func.count()).select_from(model)) == 0


def test_same_origin_through_proxy_any_port_and_host_alias(client):
    # El navegador envía Origin y Host iguales cuando la app se sirve desde el proxy de Vite.
    for site in ["127.0.0.1:5180", "localhost:5174", "127.0.0.1:5173", "localhost:5173"]:
        r = client.post(
            "/api/auth/register",
            headers={"Origin": "http://" + site, "Host": site},
            json=dict(
                name="Proxy",
                email=f"proxy-{site.replace(':', '-')}@example.com",
                password="prueba-segura-2026",
            ),
        )
        assert r.status_code == 201, (site, r.text)
    # Un sitio ajeno no coincide con el Host aunque use la misma IP o un puerto distinto.
    for origin, host in [
        ("https://hostile.example", "127.0.0.1:5180"),
        ("http://127.0.0.1:9999", "127.0.0.1:5180"),
        ("http://localhost:5180", "127.0.0.1:5180"),
        ("null", "127.0.0.1:5180"),
    ]:
        r = client.post(
            "/api/auth/login",
            headers={"Origin": origin, "Host": host},
            json=dict(email="x@example.com", password="prueba-segura-2026"),
        )
        assert r.status_code == 403, (origin, r.status_code)
    # Sin la cabecera propia de Mikuy se rechaza aunque el origen coincida.
    with TestClient(app) as raw:
        r = raw.post(
            "/api/auth/login",
            headers={"Origin": "http://127.0.0.1:5180", "Host": "127.0.0.1:5180"},
            json={},
        )
        assert r.status_code == 403


def test_session_lifecycle_register_logout_login_persist(client):
    site = {"Origin": "http://127.0.0.1:5180", "Host": "127.0.0.1:5180"}
    creds = dict(email="ciclo@example.com", password="prueba-segura-2026")
    assert (
        client.post(
            "/api/auth/register", headers=site, json=dict(name="Ciclo", **creds)
        ).status_code
        == 201
    )
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout", headers=site).status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    assert (
        client.post(
            "/api/auth/login", headers=site, json=dict(creds, password="otra-clave-2026")
        ).status_code
        == 401
    )
    assert client.post("/api/auth/login", headers=site, json=creds).status_code == 200
    cookies = dict(client.cookies)
    with TestClient(app, cookies=cookies) as again:  # nueva conexión = sesión persistente
        assert again.get("/api/auth/me").json()["email"] == creds["email"]
    assert client.put("/api/profile", headers=site, json=dict(completed=True)).status_code == 200
