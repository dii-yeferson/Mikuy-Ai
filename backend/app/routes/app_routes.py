"""Perfil, recetario, menú semanal, compras y favoritos."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete

from ..catalog import BY_ID, RECIPES
from ..catalog.prices import CITIES, PRICE_DATE, cities_payload
from ..catalog.sources import NUTRITION_NOTE, PRICE_NOTE, SOURCES
from ..db import get_db
from ..models import Favorite
from ..security import current_user
from ..services import nutrition as nu
from ..services import plans as plan_service
from ..services import profiles, shopping
from ..services.assistant import norm

router = APIRouter(prefix="/api", tags=["app"])


class ProfileIn(BaseModel):
    onboarded: bool | None = None
    goal: Literal["bajar", "mantener", "subir", "comer-mejor", "ahorrar"] | None = None
    sex: Literal["mujer", "hombre"] | None = None
    age: int | None = Field(None, ge=14, le=100)
    weight_kg: float | None = Field(None, ge=30, le=250)
    height_cm: float | None = Field(None, ge=120, le=230)
    activity: Literal["sedentaria", "ligera", "moderada", "intensa"] | None = None
    diet: Literal["omnivoro", "vegetariano", "vegano", "pescetariano", "sin-gluten"] | None = None
    allergies: list[Literal["M", "F", "C", "D", "E", "G", "N", "S"]] | None = None
    excluded: list[str] | None = None
    conditions: list[Literal["diabetes", "prediabetes", "hipertension", "colesterol", "embarazo", "gastritis"]] | None = None
    city: str | None = None
    people: int | None = Field(None, ge=1, le=12)
    weekly_budget: float | None = Field(None, ge=0, le=5000)
    max_minutes: int | None = Field(None, ge=0, le=240)
    snacks: bool | None = None
    sounds: bool | None = None
    haptics: bool | None = None
    voice_reply: bool | None = None
    theme: Literal["auto", "claro", "oscuro"] | None = None


@router.get("/profile")
def get_profile(user=Depends(current_user), db=Depends(get_db)):
    return profiles.load(db, user.id)


@router.put("/profile")
def put_profile(body: ProfileIn, user=Depends(current_user), db=Depends(get_db)):
    changes = body.model_dump(exclude_none=True)
    if "city" in changes and changes["city"] not in CITIES:
        raise HTTPException(422, "Ciudad no disponible.")
    if "excluded" in changes:
        from ..catalog import INGREDIENTS

        changes["excluded"] = [i for i in changes["excluded"] if i in INGREDIENTS]
    out = profiles.save(db, user.id, changes)
    db.commit()
    return {**out, "targets": nu.daily_targets(out)}


@router.get("/targets")
def targets(user=Depends(current_user), db=Depends(get_db)):
    return nu.daily_targets(profiles.load(db, user.id))


# --- Catálogo -------------------------------------------------------------------------------


@router.get("/catalog/meta")
def catalog_meta():
    from ..catalog import INGREDIENTS

    return {
        "cities": cities_payload(),
        "price_date": PRICE_DATE,
        "price_note": PRICE_NOTE,
        "nutrition_note": NUTRITION_NOTE,
        "sources": SOURCES,
        "recipes": len(RECIPES),
        "ingredients": [{"id": i.id, "name": i.name} for i in sorted(INGREDIENTS.values(), key=lambda i: i.name)],
    }


@router.get("/recipes")
def list_recipes(
    meal: str | None = None,
    q: str = "",
    tag: str | None = None,
    only_allowed: bool = True,
    user=Depends(current_user),
    db=Depends(get_db),
):
    profile = profiles.load(db, user.id)
    city = profile.get("city", "lima")
    words = [w for w in norm(q).split() if w]
    out = []
    for r in RECIPES:
        if meal and r.meal != meal:
            continue
        if tag and tag not in r.tags and tag not in nu.diet_labels(r):
            continue
        if words:
            hay = norm(r.name + " " + " ".join(r.tags) + " " + r.region + " " + " ".join(i for i, _ in r.parts))
            if not all(w in hay for w in words):
                continue
        ok = nu.allowed(r, profile)
        if only_allowed and not ok:
            continue
        item = nu.recipe_summary(r, city)
        item["favorite"] = r.id in profile["favorites"]
        item["allowed"] = ok
        out.append(item)
    return {"items": out, "total": len(out)}


@router.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: str, portion: float = Query(1, ge=0.25, le=12), user=Depends(current_user), db=Depends(get_db)):
    recipe = BY_ID.get(recipe_id)
    if not recipe:
        raise HTTPException(404, "Receta no encontrada.")
    profile = profiles.load(db, user.id)
    out = nu.recipe_payload(recipe, profile.get("city", "lima"), portion, profile)
    out["favorite"] = recipe_id in profile["favorites"]
    out["allowed"] = nu.allowed(recipe, profile)
    return out


@router.put("/favorites/{recipe_id}")
def add_favorite(recipe_id: str, user=Depends(current_user), db=Depends(get_db)):
    if recipe_id not in BY_ID:
        raise HTTPException(404, "Receta no encontrada.")
    if not db.get(Favorite, (user.id, recipe_id)):
        db.add(Favorite(user_id=user.id, recipe_id=recipe_id))
    db.commit()
    return {"ok": True}


@router.delete("/favorites/{recipe_id}")
def remove_favorite(recipe_id: str, user=Depends(current_user), db=Depends(get_db)):
    db.execute(delete(Favorite).where(Favorite.user_id == user.id, Favorite.recipe_id == recipe_id))
    db.commit()
    return {"ok": True}


# --- Menú -----------------------------------------------------------------------------------


class GenerateIn(BaseModel):
    seed: int | None = None


class SwapIn(BaseModel):
    day: str
    meal: Literal["desayuno", "almuerzo", "cena", "snack"]
    recipe_id: str | None = None
    query: str = ""


class PortionIn(BaseModel):
    day: str
    meal: Literal["desayuno", "almuerzo", "cena", "snack"]
    portion: float


@router.get("/plan")
def get_plan(user=Depends(current_user), db=Depends(get_db)):
    profile = profiles.load(db, user.id)
    return {"plan": plan_service.payload(plan_service.current(db, user.id), profile)}


@router.post("/plan/generate")
def generate_plan(body: GenerateIn | None = None, user=Depends(current_user), db=Depends(get_db)):
    profile = profiles.load(db, user.id)
    plan = plan_service.generate(db, user.id, profile, seed=body.seed if body else None)
    db.commit()
    return {"plan": plan_service.payload(plan, profile)}


@router.get("/plan/alternatives")
def alternatives(day: str, meal: str, q: str = "", user=Depends(current_user), db=Depends(get_db)):
    from ..services.planner import Planner

    profile = profiles.load(db, user.id)
    plan = plan_service.require(db, user.id)
    slot = plan_service._slot(plan, day, meal)
    options = Planner(profile).alternatives(meal, slot["recipe_id"], q, 12)
    return {"items": [nu.recipe_summary(r, profile.get("city", "lima")) for r in options]}


@router.post("/plan/swap")
def swap(body: SwapIn, user=Depends(current_user), db=Depends(get_db)):
    profile = profiles.load(db, user.id)
    plan = plan_service.require(db, user.id)
    plan_service.swap(db, plan, profile, body.day, body.meal, body.recipe_id, body.query)
    db.commit()
    return {"plan": plan_service.payload(plan, profile)}


@router.post("/plan/portion")
def portion(body: PortionIn, user=Depends(current_user), db=Depends(get_db)):
    profile = profiles.load(db, user.id)
    plan = plan_service.require(db, user.id)
    plan_service.set_portion(db, plan, body.day, body.meal, body.portion)
    db.commit()
    return {"plan": plan_service.payload(plan, profile)}


# --- Compras --------------------------------------------------------------------------------


class CheckIn(BaseModel):
    id: str
    checked: bool


class PantryIn(BaseModel):
    include_pantry: bool


@router.get("/shopping")
def get_shopping(user=Depends(current_user), db=Depends(get_db)):
    profile = profiles.load(db, user.id)
    plan = plan_service.current(db, user.id)
    if not plan:
        return {"shopping": None}
    data = shopping.build(plan.data, profile, plan.shopping)
    data["text"] = shopping.as_text(data)
    return {"shopping": data}


@router.post("/shopping/check")
def check(body: CheckIn, user=Depends(current_user), db=Depends(get_db)):
    plan = plan_service.require(db, user.id)
    checked = set(plan.shopping.get("checked", []))
    (checked.add if body.checked else checked.discard)(body.id)
    plan.shopping = {**plan.shopping, "checked": sorted(checked)}
    db.commit()
    return get_shopping(user, db)


@router.post("/shopping/pantry")
def pantry(body: PantryIn, user=Depends(current_user), db=Depends(get_db)):
    plan = plan_service.require(db, user.id)
    plan.shopping = {**plan.shopping, "include_pantry": body.include_pantry}
    db.commit()
    return get_shopping(user, db)
