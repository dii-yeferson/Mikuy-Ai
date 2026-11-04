import random
from collections import defaultdict
from decimal import Decimal

from fastapi import HTTPException

from .catalog import (
    BY_ID,
    CONDITION_LABELS,
    INGREDIENTS,
    NUTRITION_SOURCE,
    PRICE_NOTE,
    RECIPES,
    compatible,
    meal,
    money,
    suitable,
    traffic,
)
from .schemas import normalize

KINDS = ["Desayuno", "Almuerzo", "Cena"]
LIMITS = {
    "gratis": dict(plans=4, coach=50, servings=1, report=False),
    "premium": dict(plans=30, coach=150, servings=4, report=True),
    "familiar": dict(plans=60, coach=300, servings=6, report=True),
}


def aggregate(meals):
    quantities = defaultdict(lambda: Decimal("0"))
    info = {}
    for m in meals:
        for i in m["ingredients"]:
            key = i["ingredient_id"]
            quantities[key] += Decimal(str(i["quantity"]))
            info[key] = i
    items = [
        dict(
            ingredient_id=key,
            name=info[key]["name"],
            unit=info[key]["unit"],
            section=INGREDIENTS[key]["section"] if key in INGREDIENTS else "Otros",
            quantity=float(q),
            unit_price=info[key]["unit_price"],
            cost=money(q * Decimal(str(info[key]["unit_price"]))),
            checked=False,
        )
        for key, q in quantities.items()
    ]
    order = {
        s: i
        for i, s in enumerate(
            [
                "Verduras y hierbas",
                "Frutas",
                "Tubérculos y choclo",
                "Carnes y aves",
                "Pescados",
                "Huevos y lácteos",
                "Menestras y granos",
                "Abarrotes",
            ]
        )
    }
    return sorted(items, key=lambda i: (order.get(i["section"], 99), i["name"]))


def total(meals):
    return money(sum(Decimal(str(i["cost"])) for i in aggregate(meals)))


def check_budget(meals, budget):
    cost = total(meals)
    if cost > budget:
        raise HTTPException(
            422,
            f"El costo estimado S/ {cost:.2f} supera tu presupuesto S/ {budget:.2f}. "
            "Ajusta las porciones, el presupuesto o elige otra receta.",
        )
    return cost


def allowed_recipes(profile):
    return [r for r in RECIPES if suitable(r, profile)]


def _recipe_cost(r, servings):
    return sum(
        p["quantity"] * servings * INGREDIENTS[p["ingredient_id"]]["unit_price"]
        for p in r["ingredients"]
    )


def _score(r, profile):
    score = 0.0
    name = normalize(r["name"])
    for dish in profile.favorite_dishes:
        d = normalize(dish)
        if d and (d in name or any(w in name for w in d.split() if len(w) > 4)):
            score += 3
    lights = traffic(r)
    score += sum(1.5 for c in profile.health if lights[c] == "verde")
    if profile.cook_time == "Menos de 20 min" and r["minutes"] > 25:
        score -= 2
    if profile.cook_time == "20 a 40 min" and r["minutes"] > 45:
        score -= 1
    if "peruano" in r["tags"]:
        score += 0.5
    return score


def _week(candidates, rng, profile):
    ranked = sorted(candidates, key=lambda r: _score(r, profile) + rng.random() * 1.5, reverse=True)
    pool = ranked[: max(7, min(len(ranked), 10))]
    rng.shuffle(pool)
    return [pool[i % len(pool)] for i in range(7)]


def create_catalog_plan(profile, start_date, ids=None):
    allowed = allowed_recipes(profile)
    choices = {k: [r for r in allowed if r["kind"] == k] for k in KINDS}
    if any(not x for x in choices.values()):
        raise HTTPException(
            422,
            "No hay suficientes recetas compatibles con tus alergias, preferencias y condiciones. "
            "Revisa los alimentos excluidos; nunca ignoraremos tus alergias.",
        )
    conditions = list(profile.health)
    meals = []
    if ids is not None:
        if len(ids) != 21:
            raise HTTPException(502, "La IA devolvió un número de comidas inválido.")
        for day in range(7):
            for j, kind in enumerate(KINDS):
                r = BY_ID.get(ids[day * 3 + j])
                if not r or r not in choices[kind]:
                    raise HTTPException(
                        502, "La IA devolvió una receta incompatible. No se guardó el plan."
                    )
                meals.append(meal(r["id"], profile.servings, day, kind, conditions))
    else:
        rng = random.Random(start_date.toordinal() * 7 + len(profile.favorite_dishes))
        weeks = {k: _week(choices[k], rng, profile) for k in KINDS}
        for day in range(7):
            for kind in KINDS:
                meals.append(meal(weeks[kind][day]["id"], profile.servings, day, kind, conditions))
        # Presupuesto primero: reemplaza las comidas más caras por alternativas más baratas.
        for _ in range(60):
            if total(meals) <= profile.budget:
                break
            ranked = sorted(
                range(len(meals)),
                key=lambda i: _recipe_cost(BY_ID[meals[i]["recipe_id"]], 1),
                reverse=True,
            )
            changed = False
            for i in ranked:
                current = BY_ID[meals[i]["recipe_id"]]
                cheaper = sorted(
                    (
                        r
                        for r in choices[current["kind"]]
                        if _recipe_cost(r, 1) < _recipe_cost(current, 1)
                    ),
                    key=lambda r: (_recipe_cost(r, 1), -_score(r, profile)),
                )
                if cheaper:
                    used = [m["recipe_id"] for m in meals]
                    pick = min(cheaper[:3], key=lambda r: used.count(r["id"]))
                    meals[i] = meal(
                        pick["id"], profile.servings, meals[i]["day"], meals[i]["kind"], conditions
                    )
                    changed = True
                    break
            if not changed:
                break
    cost = check_budget(meals, profile.budget)
    days = []
    for d in range(7):
        day_meals = [m for m in meals if m["day"] == d]
        days.append(
            {
                k: round(sum(m["nutrition"][k] for m in day_meals), 0)
                for k in ("kcal", "carbs", "sodium")
            }
        )
    return dict(
        start_date=start_date.isoformat(),
        source="nvidia" if ids is not None else "catalogo",
        budget=profile.budget,
        cost=cost,
        servings=profile.servings,
        conditions=conditions,
        condition_labels=[CONDITION_LABELS[c] for c in conditions],
        daily=days,
        meals=meals,
        price_note=PRICE_NOTE,
        nutrition_source=NUTRITION_SOURCE,
        disclaimer=(
            "Mikuy organiza tu alimentación con información referencial; no reemplaza a tu médico "
            "ni a tu nutricionista. Sigue siempre sus indicaciones."
        ),
    )


def conflicts(plan, profile):
    return [m["slot"] for m in plan["meals"] if not compatible(BY_ID[m["recipe_id"]], profile)]
