def test_register_login_logout(client):
    r = client.post("/api/auth/register", json={"name": "Ana", "email": "Ana@Example.com", "password": "12345678"})
    assert r.status_code == 200
    assert r.json()["subscription"]["plan"] == "gratis"
    assert client.post("/api/auth/register", json={"name": "Ana", "email": "ana@example.com", "password": "12345678"}).status_code == 409
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json={"email": "ana@example.com", "password": "mal"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "ana@example.com", "password": "12345678"}).status_code == 200
    assert client.get("/api/auth/me").json()["name"] == "Ana"


def test_plan_shopping_flow(user):
    r = user.post("/api/plan/generate", json={"seed": 7})
    assert r.status_code == 200, r.text
    plan = r.json()["plan"]
    assert len(plan["days"]) == 7
    assert plan["summary"]["week_cost"] <= 160 * 1.05
    first = plan["days"][1]["meals"][1]
    alt = user.get("/api/plan/alternatives", params={"day": "martes", "meal": "almuerzo"}).json()["items"]
    assert alt
    r = user.post("/api/plan/swap", json={"day": "martes", "meal": "almuerzo", "recipe_id": alt[0]["id"]})
    assert r.json()["plan"]["days"][1]["meals"][1]["recipe"]["id"] == alt[0]["id"] != first["recipe"]["id"]
    shop = user.get("/api/shopping").json()["shopping"]
    assert shop["count"] > 5 and shop["total_buy"] >= shop["total_used"] * 0.9
    item = shop["sections"][0]["items"][0]["id"]
    shop2 = user.post("/api/shopping/check", json={"id": item, "checked": True}).json()["shopping"]
    assert shop2["pending"] < shop["pending"]


def test_recipe_detail_and_favorites(user):
    r = user.get("/api/recipes/lomo-saltado", params={"portion": 2}).json()
    assert r["nutrition"]["kcal"] > 0 and r["cost"] > 0 and r["steps"]
    assert user.put("/api/favorites/lomo-saltado").status_code == 200
    assert "lomo-saltado" in user.get("/api/profile").json()["favorites"]
    found = user.get("/api/recipes", params={"q": "cebiche"}).json()
    assert found["total"] >= 2


def test_free_limits_and_premium_code(user):
    for _ in range(5):
        assert user.post("/api/assistant/message", json={"text": "hola"}).status_code == 200
    assert user.post("/api/assistant/message", json={"text": "hola"}).status_code == 402
    co = user.post("/api/premium/checkout", json={"plan": "premium", "period": "mensual"}).json()
    assert co["code"].startswith("MIKUY-") and co["simulated"]
    assert user.post("/api/premium/redeem", json={"code": "MIKUY-XXXX-XXXX"}).status_code == 404
    st = user.post("/api/premium/redeem", json={"code": co["code"].lower()}).json()
    assert st["premium"] and st["plan"] == "premium"
    assert user.post("/api/premium/redeem", json={"code": co["code"]}).status_code == 409
    assert user.post("/api/assistant/message", json={"text": "hola"}).status_code == 200


def test_assistant_actions_local(user):
    user.post("/api/plan/generate", json={"seed": 3})
    r = user.post("/api/assistant/message", json={"text": "Cambia el almuerzo del martes por algo con pollo"}).json()
    assert r["plan"] is not None
    swap = next(c for c in r["message"]["cards"] if c["type"] == "swap")
    assert swap["day"] == "martes" and swap["meal"] == "almuerzo"
    r = user.post("/api/assistant/message", json={"text": "Mi presupuesto es 120 soles a la semana", "conversation_id": r["conversation_id"]}).json()
    assert user.get("/api/profile").json()["weekly_budget"] == 120
    r = user.post("/api/assistant/message", json={"text": "no me gusta el hígado", "conversation_id": r["conversation_id"]}).json()
    assert "higado-res" in user.get("/api/profile").json()["excluded"]
    r = user.post("/api/assistant/message", json={"text": "¿cuántas calorías debo comer?", "conversation_id": r["conversation_id"]}).json()
    assert "kcal" in r["message"]["content"]
    convs = user.get("/api/assistant/conversations").json()["items"]
    assert len(convs) == 1
    assert len(user.get(f"/api/assistant/conversations/{convs[0]['id']}").json()["messages"]) == 8


def test_other_user_cannot_read_conversation(client):
    client.post("/api/auth/register", json={"name": "Uno", "email": "uno@example.com", "password": "12345678"})
    cid = client.post("/api/assistant/message", json={"text": "hola"}).json()["conversation_id"]
    client.post("/api/auth/logout")
    client.post("/api/auth/register", json={"name": "Dos", "email": "dos@example.com", "password": "12345678"})
    assert client.get(f"/api/assistant/conversations/{cid}").status_code == 404
