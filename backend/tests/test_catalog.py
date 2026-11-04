from app.catalog import BY_ID, INGREDIENTS, RECIPES
from app.catalog.prices import CITIES, cost
from app.catalog.sources import SOURCES
from app.services import nutrition as nu


def test_catalog_has_300_valid_recipes():
    assert len(RECIPES) >= 300
    assert len(BY_ID) == len(RECIPES)
    for r in RECIPES:
        assert r.steps, r.id
        assert r.meal in {"desayuno", "almuerzo", "cena", "snack"}
        for ing_id, qty in r.parts:
            assert ing_id in INGREDIENTS, (r.id, ing_id)
            assert qty > 0


def test_nutrition_is_plausible():
    for r in RECIPES:
        n = nu.recipe_nutrition(r)
        assert 20 <= n["kcal"] <= 1500, (r.id, n["kcal"])


def test_prices_change_by_city():
    lima = cost("trucha", 1000, "lima")
    puno = cost("trucha", 1000, "puno")
    assert puno < lima
    assert all(cost("arroz", 1000, c) > 0 for c in CITIES)


def test_sources_have_links():
    assert all(s["url"].startswith("https://") for s in SOURCES)


def test_targets_mifflin():
    t = nu.daily_targets({"sex": "mujer", "age": 30, "weight_kg": 60, "height_cm": 160, "activity": "sedentaria", "goal": "mantener"})
    # 10*60 + 6.25*160 - 5*30 - 161 = 1289 ; ×1.4
    assert t["bmr"] == 1289
    assert t["kcal"] == round(1289 * 1.4)


def test_diet_filters():
    vegan = {"diet": "vegano"}
    assert not nu.allowed(BY_ID["lomo-saltado"], vegan)
    assert nu.allowed(BY_ID["saltado-champinones"], vegan)
    assert not nu.allowed(BY_ID["cebiche-pescado"], {"conditions": ["embarazo"]})
    assert not nu.allowed(BY_ID["avena-platano-mani"], {"allergies": ["N"]})
