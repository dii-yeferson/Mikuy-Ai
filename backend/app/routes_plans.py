from copy import deepcopy
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from .catalog import (
    BY_ID,
    CONDITION_LABELS,
    INGREDIENTS,
    PRICE_NOTE,
    RECIPES,
    meal,
    money,
    recipe_card,
    suitable,
)
from .db import get_db
from .domain import LIMITS, aggregate, allowed_recipes, check_budget, create_catalog_plan
from .models import Entry, Plan, Shopping
from .nvidia import Selection, completion
from .schemas import DoneIn, MealEdit, PlanIn, ShoppingEdit
from .security import current_user
from .services import enforce_servings, lock_user, owned_plan, plan_response, profile_for, quota
from .shopping_service import shopping_response

router = APIRouter(tags=["Planes y compras"])


@router.get("/catalog")
def catalog(user=Depends(current_user), db=Depends(get_db)):
    profile = profile_for(db, user)
    return dict(
        recipes=[recipe_card(r, profile) for r in RECIPES],
        ingredients=INGREDIENTS,
        note=PRICE_NOTE,
    )


@router.get("/recipes/{id}")
def recipe_detail(id: str, user=Depends(current_user), db=Depends(get_db)):
    r = BY_ID.get(id)
    if not r:
        raise HTTPException(404, "No se encontró esa receta.")
    return recipe_card(r, profile_for(db, user))


@router.get("/plans")
def history(user=Depends(current_user), db=Depends(get_db)):
    return [
        dict(
            id=r.id,
            start_date=r.data["start_date"],
            cost=r.data["cost"],
            source=r.data["source"],
            version=r.version,
        )
        for r in db.scalars(
            select(Plan).where(Plan.user_id == user.id).order_by(Plan.created_at.desc())
        )
    ]


@router.post("/plans", status_code=201)
def generate(data: PlanIn, user=Depends(current_user), db=Depends(get_db)):
    user = lock_user(db, user)
    profile = profile_for(db, user)
    if not profile.completed:
        raise HTTPException(422, "Completa primero tus preferencias y presupuesto.")
    enforce_servings(user, profile.servings)
    quota(db, user, "plans")
    if data.source == "nvidia":
        if not data.consent:
            raise HTTPException(
                422, "Autoriza el envío del contexto mínimo a NVIDIA para usar la IA."
            )
        context = dict(
            goal=profile.goal,
            diet=profile.diet,
            recipes=[dict(id=r["id"], kind=r["kind"]) for r in allowed_recipes(profile)],
            budget=profile.budget,
            servings=profile.servings,
        )
        result = completion(
            "Organiza 7 días de desayuno, almuerzo y cena en ese orden. Elige solo IDs del catálogo permitido. No ofrezcas tratamientos ni alteres el presupuesto.",
            context,
            Selection,
            validate=lambda result: create_catalog_plan(
                profile, data.start_date, result.recipe_ids
            ),
        )
        document = create_catalog_plan(profile, data.start_date, result.recipe_ids)
    else:
        document = create_catalog_plan(profile, data.start_date)
    row = Plan(user_id=user.id, data=document)
    db.add(row)
    quota(db, user, "plans", consume=True)
    db.commit()
    return plan_response(row, profile)


@router.get("/plans/{id}")
def get_plan(id: str, user=Depends(current_user), db=Depends(get_db)):
    return plan_response(owned_plan(db, user, id), profile_for(db, user))


@router.patch("/plans/{id}/meals/{slot}")
def edit_meal(id: str, slot: str, data: MealEdit, user=Depends(current_user), db=Depends(get_db)):
    user = lock_user(db, user)
    row = owned_plan(db, user, id, True)
    if row.version != data.expected_version:
        raise HTTPException(409, "Este plan cambió en otra ventana. Recárgalo antes de editar.")
    profile = profile_for(db, user)
    enforce_servings(user, data.servings)
    r = BY_ID.get(data.recipe_id)
    if not r or not suitable(r, profile):
        raise HTTPException(422, "La receta no es compatible con tus restricciones actuales.")
    document = deepcopy(row.data)
    index = next((i for i, m in enumerate(document["meals"]) if m["slot"] == slot), None)
    if index is None:
        raise HTTPException(404, "No se encontró esa comida.")
    old = document["meals"][index]
    if r["kind"] != old["kind"]:
        raise HTTPException(422, "Elige una receta del mismo tipo de comida.")
    document["meals"][index] = dict(
        **meal(r["id"], data.servings, old["day"], old["kind"], profile.health), edited=True
    )
    document["cost"] = check_budget(document["meals"], document["budget"])
    row.data = document
    row.version += 1
    # Avoid reviving overrides for ingredients removed and later reintroduced.
    present = {i["ingredient_id"] for i in aggregate(document["meals"])}
    for override in db.scalars(select(Shopping).where(Shopping.plan_id == id)):
        if override.ingredient_id not in present:
            db.delete(override)
    db.commit()
    return plan_response(row, profile)


@router.get("/plans/{id}/shopping")
def shopping_list(id: str, user=Depends(current_user), db=Depends(get_db)):
    return shopping_response(db, owned_plan(db, user, id))


@router.patch("/plans/{id}/shopping/{ingredient}")
def edit_shopping(
    id: str, ingredient: str, data: ShoppingEdit, user=Depends(current_user), db=Depends(get_db)
):
    row = owned_plan(db, user, id, True)
    if ingredient not in {i["ingredient_id"] for i in aggregate(row.data["meals"])}:
        raise HTTPException(404, "El ingrediente no pertenece a este plan.")
    override = db.get(Shopping, (id, ingredient))
    if override:
        override.data = data.model_dump()
    else:
        db.add(Shopping(plan_id=id, ingredient_id=ingredient, data=data.model_dump()))
    db.commit()
    return shopping_response(db, row)


@router.patch("/plans/{id}/meals/{slot}/done")
def mark_done(id: str, slot: str, data: DoneIn, user=Depends(current_user), db=Depends(get_db)):
    row = owned_plan(db, user, id, True)
    document = deepcopy(row.data)
    found = next((m for m in document["meals"] if m["slot"] == slot), None)
    if not found:
        raise HTTPException(404, "No se encontró esa comida.")
    found["done"] = data.done
    row.data = document
    db.commit()
    return plan_response(row, profile_for(db, user))


def lima_today():
    return datetime.now(ZoneInfo("America/Lima")).date()


def adherence(rows):
    planned = done = 0
    for r in rows:
        for m in r.data["meals"]:
            planned += 1
            done += 1 if m.get("done") else 0
    return dict(planned=planned, done=done, percent=round(done * 100 / planned) if planned else 0)


@router.get("/today")
def today_view(user=Depends(current_user), db=Depends(get_db)):
    profile = profile_for(db, user)
    row = db.scalar(
        select(Plan).where(Plan.user_id == user.id).order_by(Plan.created_at.desc()).limit(1)
    )
    today = lima_today()
    if not row:
        return dict(
            plan=None,
            today=today.isoformat(),
            meals=[],
            day=None,
            budget=profile.budget,
            conditions=profile.health,
            adherence=dict(planned=0, done=0, percent=0),
        )
    start = date.fromisoformat(row.data["start_date"])
    day = (today - start).days
    meals = [m for m in row.data["meals"] if m["day"] == day] if 0 <= day < 7 else []
    return dict(
        plan=dict(
            id=row.id,
            start_date=row.data["start_date"],
            cost=row.data["cost"],
            budget=row.data["budget"],
            version=row.version,
        ),
        today=today.isoformat(),
        day=day if 0 <= day < 7 else None,
        meals=meals,
        totals={
            k: round(sum(m["nutrition"][k] for m in meals), 0) for k in ("kcal", "carbs", "sodium")
        }
        if meals
        else None,
        budget=row.data["budget"],
        cost=row.data["cost"],
        conditions=profile.health,
        adherence=adherence([row]),
        expired=day >= 7,
    )


@router.get("/report")
def report(month: str | None = None, user=Depends(current_user), db=Depends(get_db)):
    if not LIMITS[user.tier]["report"]:
        raise HTTPException(
            403, "El reporte para tu médico es parte de Premium y Familiar (suscripción simulada)."
        )
    today = lima_today()
    month = month or today.strftime("%Y-%m")
    try:
        first = date.fromisoformat(month + "-01")
    except ValueError:
        raise HTTPException(422, "Mes inválido. Usa el formato AAAA-MM.")
    nxt = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    rows = [
        r
        for r in db.scalars(select(Plan).where(Plan.user_id == user.id).order_by(Plan.created_at))
        if first <= date.fromisoformat(r.data["start_date"]) < nxt
    ]
    entries = [
        dict(date=e.data.get("date"), value=e.data.get("value"))
        for e in db.scalars(
            select(Entry)
            .where(Entry.user_id == user.id, Entry.kind == "peso")
            .order_by(Entry.created_at)
        )
        if str(e.data.get("date", "")).startswith(month)
    ]
    profile = profile_for(db, user)
    weeks = []
    for r in rows:
        a = adherence([r])
        weeks.append(
            dict(
                start_date=r.data["start_date"],
                cost=r.data["cost"],
                budget=r.data["budget"],
                **a,
                avg=dict(
                    (
                        k,
                        round(
                            sum(d[k] for d in r.data.get("daily", []))
                            / max(1, len(r.data.get("daily", []))),
                            0,
                        ),
                    )
                    for k in ("kcal", "carbs", "sodium")
                ),
            )
        )
    return dict(
        month=month,
        name=user.name,
        conditions=[CONDITION_LABELS[c] for c in profile.health],
        goal=profile.goal,
        weeks=weeks,
        adherence=adherence(rows),
        weights=entries,
        spent=money(sum(r.data["cost"] for r in rows)),
        generated=today.isoformat(),
        note="Reporte informativo generado por Mikuy con datos registrados por el usuario y valores nutricionales referenciales. No es un documento clínico.",
    )
