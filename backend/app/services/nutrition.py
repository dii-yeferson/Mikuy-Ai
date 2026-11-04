"""Nutrición de Mikuy: nutrientes por receta, metas diarias y criterios de salud.

Metas: gasto energético en reposo de Mifflin-St Jeor (1990) multiplicado por el nivel de
actividad física (FAO/OMS/UNU, 2001); sodio < 2 000 mg/día (OMS); azúcares libres < 10 %
de la energía (OMS). Ver `catalog/sources.py`.
"""

from __future__ import annotations

from ..catalog import BY_ID, FLAG_LABELS, INGREDIENTS, Recipe
from ..catalog.ingredients import nutrient_amount
from ..catalog.images import image_for
from ..catalog.prices import cost as ingredient_cost

NUTRIENTS = ("kcal", "protein", "fat", "carbs", "fiber", "sodium")
MEAL_SHARE = {"desayuno": 0.25, "almuerzo": 0.40, "cena": 0.25, "snack": 0.10}
ACTIVITY = {"sedentaria": 1.4, "ligera": 1.55, "moderada": 1.75, "intensa": 1.95}
FREE_SUGAR_IDS = {"azucar", "miel"}
RAW_SEAFOOD_TAG = "sin-coccion"


def recipe_nutrition(recipe: Recipe, portion: float = 1.0) -> dict:
    totals = dict.fromkeys(NUTRIENTS, 0.0)
    sugar = 0.0
    for ing_id, qty in recipe.parts:
        ing = INGREDIENTS[ing_id]
        for field in NUTRIENTS:
            totals[field] += nutrient_amount(ing, qty * portion, field)
        if ing_id in FREE_SUGAR_IDS:
            sugar += nutrient_amount(ing, qty * portion, "carbs")
    out = {k: round(v, 1) for k, v in totals.items()}
    out["kcal"] = round(totals["kcal"])
    out["sodium"] = round(totals["sodium"])
    out["free_sugar"] = round(sugar, 1)
    return out


def recipe_flags(recipe: Recipe) -> set[str]:
    flags: set[str] = set()
    for ing_id, _ in recipe.parts:
        flags.update(INGREDIENTS[ing_id].flags)
    return flags


def diet_labels(recipe: Recipe) -> list[str]:
    flags = recipe_flags(recipe)
    ids = {i for i, _ in recipe.parts}
    labels = []
    if not flags & {"M", "F", "C"}:
        labels.append("vegetariano")
        if not flags & {"D", "E"} and "miel" not in ids:
            labels.append("vegano")
    elif not flags & {"M"}:
        labels.append("pescetariano")
    if "G" not in flags:
        labels.append("sin gluten")
    return labels


def recipe_cost(recipe: Recipe, city: str, portion: float = 1.0) -> float:
    return sum(ingredient_cost(i, q * portion, city) for i, q in recipe.parts)


def allowed(recipe: Recipe, profile: dict) -> bool:
    """¿La receta respeta la dieta, alergias, exclusiones y condiciones del perfil?"""
    flags = recipe_flags(recipe)
    ids = {i for i, _ in recipe.parts}
    diet = profile.get("diet", "omnivoro")
    if diet == "vegetariano" and flags & {"M", "F", "C"}:
        return False
    if diet == "vegano" and (flags & {"M", "F", "C", "D", "E"} or "miel" in ids):
        return False
    if diet == "pescetariano" and "M" in flags:
        return False
    if diet == "sin-gluten" and "G" in flags:
        return False
    if set(profile.get("allergies", [])) & flags:
        return False
    if ids & set(profile.get("excluded", [])):
        return False
    conditions = set(profile.get("conditions", []))
    if "embarazo" in conditions and RAW_SEAFOOD_TAG in recipe.tags and flags & {"F", "C"}:
        return False
    if "postre" in recipe.tags and conditions & {"diabetes", "prediabetes"}:
        return False
    return True


def warnings(recipe: Recipe, profile: dict, portion: float = 1.0) -> list[str]:
    """Avisos con criterio profesional sobre una receta para este perfil."""
    n = recipe_nutrition(recipe, portion)
    conditions = set(profile.get("conditions", []))
    out = []
    if n["sodium"] > 900:
        out.append("Alta en sodio: reduce la sal o el sillao si cuidas tu presión.")
    elif n["sodium"] > 600 and "hipertension" in conditions:
        out.append("Para hipertensión, usa la mitad de la sal indicada.")
    if n["free_sugar"] > 12 and conditions & {"diabetes", "prediabetes"}:
        out.append("Contiene azúcar añadida: prefiere una versión sin azúcar.")
    if n["kcal"] and n["protein"] * 4 / n["kcal"] < 0.1 and recipe.meal in {"almuerzo", "cena"}:
        out.append("Baja en proteína: acompaña con huevo, menestra o queso.")
    if "embarazo" in conditions and "higado-res" in {i for i, _ in recipe.parts}:
        out.append("En el embarazo, limita el hígado a una porción pequeña a la semana.")
    return out


def daily_targets(profile: dict) -> dict:
    """Meta diaria de energía y macronutrientes."""
    weight = float(profile.get("weight_kg") or 65)
    height = float(profile.get("height_cm") or 162)
    age = int(profile.get("age") or 30)
    sex = profile.get("sex", "mujer")
    bmr = 10 * weight + 6.25 * height - 5 * age + (5 if sex == "hombre" else -161)
    tdee = bmr * ACTIVITY.get(profile.get("activity", "ligera"), 1.55)
    goal = profile.get("goal", "comer-mejor")
    kcal = tdee
    if goal == "bajar":
        kcal = max(tdee * 0.82, 1500 if sex == "hombre" else 1200)
    elif goal == "subir":
        kcal = tdee * 1.1
    protein_per_kg = {"bajar": 1.6, "subir": 1.7}.get(goal, 1.2)
    if "embarazo" in profile.get("conditions", []):
        kcal += 340
        protein_per_kg = max(protein_per_kg, 1.3)
    protein = min(protein_per_kg * weight, kcal * 0.3 / 4)
    fat = kcal * 0.28 / 9
    carbs = (kcal - protein * 4 - fat * 9) / 4
    bmi = weight / (height / 100) ** 2
    return {
        "kcal": round(kcal),
        "protein": round(protein),
        "fat": round(fat),
        "carbs": round(carbs),
        "fiber": 30 if sex == "hombre" else 25,
        "sodium": 2000,
        "bmr": round(bmr),
        "tdee": round(tdee),
        "bmi": round(bmi, 1),
        "method": "Mifflin-St Jeor × nivel de actividad (FAO/OMS/UNU)",
    }


def portion_for(recipe: Recipe, target_kcal: float) -> float:
    """Porción (0,75 a 2) que acerca la receta a las calorías de esa comida."""
    base = recipe_nutrition(recipe)["kcal"] or 1
    raw = target_kcal / base
    return round(min(2.0, max(0.75, raw)) * 4) / 4


def recipe_payload(recipe: Recipe, city: str = "lima", portion: float = 1.0, profile: dict | None = None) -> dict:
    from ..catalog.prices import unit_price

    ingredients = []
    for ing_id, qty in recipe.parts:
        ing = INGREDIENTS[ing_id]
        amount = qty * portion
        ingredients.append(
            {
                "id": ing_id,
                "name": ing.name,
                "qty": round(amount, 1 if ing.unit == "u" else 0),
                "unit": "unid." if ing.unit == "u" else ing.unit,
                "cost": round(ingredient_cost(ing_id, amount, city), 2),
                "unit_price": unit_price(ing_id, city),
                "price_unit": {"g": "kg", "ml": "L", "u": "unid."}[ing.unit],
            }
        )
    flags = recipe_flags(recipe)
    return {
        "id": recipe.id,
        "name": recipe.name,
        "meal": recipe.meal,
        "minutes": recipe.minutes,
        "tags": list(recipe.tags),
        "region": recipe.region,
        "portion": portion,
        "ingredients": ingredients,
        "steps": list(recipe.steps),
        "nutrition": recipe_nutrition(recipe, portion),
        "cost": round(recipe_cost(recipe, city, portion), 2),
        "allergens": sorted(FLAG_LABELS[f] for f in flags if f in FLAG_LABELS and f != "M"),
        "diet": diet_labels(recipe),
        "warnings": warnings(recipe, profile or {}),
        "image": image_for(recipe.id),
    }


def recipe_summary(recipe: Recipe, city: str = "lima") -> dict:
    n = recipe_nutrition(recipe)
    return {
        "id": recipe.id,
        "name": recipe.name,
        "meal": recipe.meal,
        "minutes": recipe.minutes,
        "tags": list(recipe.tags),
        "region": recipe.region,
        "kcal": n["kcal"],
        "protein": n["protein"],
        "cost": round(recipe_cost(recipe, city), 2),
        "diet": diet_labels(recipe),
        "image": image_for(recipe.id),
    }


def get(recipe_id: str) -> Recipe:
    return BY_ID[recipe_id]
