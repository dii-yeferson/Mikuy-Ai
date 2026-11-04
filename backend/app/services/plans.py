"""Menú semanal guardado en la cuenta: crear, consultar y modificar."""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import select

from ..catalog import BY_ID
from ..models import Plan
from . import nutrition as nu
from . import planner, premium
from .planner import Planner

MEAL_LABEL = {"desayuno": "Desayuno", "almuerzo": "Almuerzo", "cena": "Cena", "snack": "Snack"}


def current(db, user_id: str, week: date | None = None) -> Plan | None:
    week = week or planner.week_start()
    return db.scalar(select(Plan).where(Plan.user_id == user_id, Plan.week_start == week))


def require(db, user_id: str) -> Plan:
    plan = current(db, user_id)
    if not plan:
        raise HTTPException(404, "Aún no tienes un menú esta semana. Créalo en Plan.")
    return plan


def generate(db, user_id: str, profile: dict, seed: int | None = None, count_usage: bool = True) -> Plan:
    if count_usage:
        premium.consume(db, user_id, "plan")
    week = planner.week_start()
    data = Planner(profile, seed=seed).generate(week)
    plan = current(db, user_id, week)
    if plan:
        plan.data = data
        plan.version += 1
        plan.shopping = {"checked": [], "include_pantry": plan.shopping.get("include_pantry", False)}
    else:
        plan = Plan(user_id=user_id, week_start=week, data=data, shopping={"checked": []})
        db.add(plan)
    db.flush()
    return plan


def _slot(plan: Plan, day: str, meal: str) -> dict:
    for d in plan.data["days"]:
        if d["day"] == day or d["date"] == day:
            for m in d["meals"]:
                if m["meal"] == meal:
                    return m
    raise HTTPException(404, f"No encontré el {meal} del {day} en tu menú.")


def _save(plan: Plan, data: dict) -> None:
    # Reasignar para que SQLAlchemy detecte el cambio en JSON.
    plan.data = {**data, "days": [dict(d, meals=[dict(m) for m in d["meals"]]) for d in data["days"]]}
    plan.version += 1


def swap(db, plan: Plan, profile: dict, day: str, meal: str, recipe_id: str | None = None, query: str = "") -> dict:
    data = {**plan.data, "days": [dict(d, meals=[dict(m) for m in d["meals"]]) for d in plan.data["days"]]}
    tmp = Plan(data=data)
    slot = _slot(tmp, day, meal)
    p = Planner(profile)
    if recipe_id:
        recipe = BY_ID.get(recipe_id)
        if not recipe:
            raise HTTPException(404, "Esa receta no existe.")
        if not nu.allowed(recipe, profile):
            raise HTTPException(409, f"{recipe.name} no es compatible con tu perfil (dieta, alergias o exclusiones).")
    else:
        options = p.alternatives(meal, slot["recipe_id"], query)
        if not options:
            raise HTTPException(409, "No encontré otra receta compatible para ese momento.")
        if query and any(w in query.lower() for w in ("barat", "económ", "econom", "ahorr")):
            options = sorted(options, key=p.cost)
        recipe = options[0]
    old = slot["recipe_id"]
    slot.update(p.entry(recipe, meal))
    _save(plan, data)
    db.flush()
    return {"from": old, "to": recipe.id}


def set_portion(db, plan: Plan, day: str, meal: str, portion: float) -> None:
    if not 0.5 <= portion <= 3:
        raise HTTPException(422, "La porción debe estar entre 0,5 y 3.")
    data = {**plan.data, "days": [dict(d, meals=[dict(m) for m in d["meals"]]) for d in plan.data["days"]]}
    slot = _slot(Plan(data=data), day, meal)
    slot["portion"] = portion
    _save(plan, data)
    db.flush()


def payload(plan: Plan | None, profile: dict) -> dict | None:
    if not plan:
        return None
    city = profile.get("city", "lima")
    days = []
    for d in plan.data["days"]:
        meals = []
        for m in d["meals"]:
            r = BY_ID[m["recipe_id"]]
            n = nu.recipe_nutrition(r, m["portion"])
            meals.append(
                {
                    "meal": m["meal"],
                    "label": MEAL_LABEL[m["meal"]],
                    "portion": m["portion"],
                    "recipe": nu.recipe_summary(r, city),
                    "kcal": n["kcal"],
                    "protein": n["protein"],
                    "cost": round(nu.recipe_cost(r, city, m["portion"]) * max(1, int(profile.get("people") or 1)), 2),
                }
            )
        days.append({"day": d["day"], "date": d["date"], "meals": meals})
    return {
        "id": plan.id,
        "week_start": plan.week_start.isoformat(),
        "version": plan.version,
        "days": days,
        "summary": planner.summarize(plan.data, profile),
    }


def compact(plan: Plan | None, profile: dict) -> list[str]:
    """Resumen breve del menú para el asistente."""
    if not plan:
        return []
    city = profile.get("city", "lima")
    lines = []
    for d in plan.data["days"]:
        parts = []
        for m in d["meals"]:
            r = BY_ID[m["recipe_id"]]
            parts.append(f"{m['meal']}: {r.name} (S/{nu.recipe_cost(r, city, m['portion']):.2f})")
        lines.append(f"{d['day']} {d['date']} → " + "; ".join(parts))
    return lines
