from .conftest import plan, profile, register


def test_consent_persists_and_revokes(client):
    register(client)
    assert not client.get("/api/coach/status").json()["consent"]
    assert client.put("/api/coach/consent", json={"consent": True}).status_code == 200
    assert client.get("/api/coach/status").json()["consent"]
    assert client.get("/api/profile").json()["settings"]["coach_intro_seen"]
    client.put("/api/coach/consent", json={"consent": False})
    assert not client.get("/api/coach/status").json()["consent"]


def test_coach_uses_actual_shopping_and_budget(client):
    register(client)
    profile(client, budget=175)
    p = plan(client)
    url = f"/api/plans/{p['id']}/shopping"
    shopping = client.get(url).json()
    assert shopping["shopping_cost"] >= shopping["planned_cost"]
    item = shopping["items"][0]
    changed = client.patch(
        url + "/" + item["ingredient_id"], json=dict(quantity=1000, unit_price=0.123, checked=False)
    ).json()
    reply = client.post(
        "/api/coach",
        json={"question": "¿Cuánto es el precio de mi compra estimada y mi presupuesto semanal?"},
    ).json()
    assert "175.00" in reply["answer"]
    assert f"{changed['shopping_cost']:.2f}" in reply["answer"]
    assert "gasto confirmado" in reply["answer"]
    assert (
        client.post("/api/coach", json={"question": "¿Cómo creo una comunidad?"}).status_code == 201
    )


def test_purchase_rounding():
    from app.shopping_service import purchase_quantity

    assert purchase_quantity(dict(ingredient_id="ajo", unit="g", quantity=30)) == 100
    assert purchase_quantity(dict(ingredient_id="harina", unit="g", quantity=30)) == 1000
    assert purchase_quantity(dict(ingredient_id="aji-panca", unit="g", quantity=2)) == 100
    assert purchase_quantity(dict(ingredient_id="huevo", unit="unid", quantity=1.5)) == 2


def test_budget_no_plan_and_account_isolation(client):
    register(client)
    profile(client, budget=240)
    reply = client.post("/api/coach", json={"question": "¿Cuál es mi presupuesto semanal?"}).json()
    assert "240.00" in reply["answer"] and "Todavía no tienes" in reply["answer"]
    client.post("/api/auth/logout")
    register(client, "other@example.com")
    assert not client.get("/api/coach/status").json()["consent"]
    reply = client.post("/api/coach", json={"question": "¿Cuál es mi presupuesto semanal?"}).json()
    assert "240.00" not in reply["answer"]


def test_coach_reads_today_records_not_planned_intake(client):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    register(client)
    day = datetime.now(ZoneInfo("America/Lima")).date().isoformat()
    client.post("/api/entries", json=dict(kind="agua", date=day, value=350))
    client.post("/api/entries", json=dict(kind="agua", date=day, value=200))
    reply = client.post("/api/coach", json=dict(question="¿Cuánta agua he registrado hoy?")).json()
    assert "550 ml de agua" in reply["answer"]
    client.post("/api/entries", json=dict(kind="peso", date=day, value=65.4))
    reply = client.post(
        "/api/coach", json=dict(question="¿Cuál es mi último peso registrado?")
    ).json()
    assert "65.4 kg" in reply["answer"]
    client.post(
        "/api/diary", json=dict(date=day, meal="Almuerzo", name="Comida de prueba", kcal=320)
    )
    reply = client.post(
        "/api/coach", json=dict(question="¿Cuántas calorías he registrado hoy?")
    ).json()
    assert "320 kcal" in reply["answer"]
