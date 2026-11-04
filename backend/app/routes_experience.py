from copy import deepcopy
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from .catalog import BY_ID, compatible
from .db import get_db
from .experience_schemas import DiaryAction, FeedbackIn, FoodIn, MetricIn, PhotoIn
from .models import Entry
from .security import current_user
from .services import lock_user, profile_for

router = APIRouter(tags=["Experiencia reconstruida"])


def owned_entries(db, user, kind=None):
    q = select(Entry).where(Entry.user_id == user.id)
    if kind:
        q = q.where(Entry.kind == kind)
    return list(db.scalars(q.order_by(Entry.created_at)))


def present(row):
    return dict(id=row.id, kind=row.kind, **row.data)


def validate_food(doc, db, user):
    try:
        data = FoodIn.model_validate(doc)
    except ValidationError:
        raise HTTPException(422, "Las cantidades o los nutrientes exceden el rango permitido.")
    if data.recipe_id:
        recipe = BY_ID.get(data.recipe_id)
        if not recipe or not compatible(recipe, profile_for(db, user)):
            raise HTTPException(422, "La receta ya no es compatible con tus restricciones.")
    return data.model_dump(mode="json")


@router.get("/diary/{day}")
def diary(day: date, user=Depends(current_user), db=Depends(get_db)):
    foods = [r for r in owned_entries(db, user, "comida") if r.data["date"] == day.isoformat()]
    total = {
        k: round(sum(r.data.get(k, 0) for r in foods), 2)
        for k in ["kcal", "protein", "carbs", "fat", "fiber", "sugar", "sodium", "saturated"]
    }
    finished = any(
        r.data.get("date") == day.isoformat() for r in owned_entries(db, user, "dia_finalizado")
    )
    return dict(
        date=day.isoformat(),
        foods=[present(r) for r in foods],
        totals=total,
        finished=finished,
        nutrition_source="Valores declarados manualmente por el usuario; verificar con etiquetas o fuente profesional.",
    )


@router.post("/diary", status_code=201)
def record_food(data: FoodIn, user=Depends(current_user), db=Depends(get_db)):
    if data.recipe_id:
        recipe = BY_ID.get(data.recipe_id)
        if not recipe or not compatible(recipe, profile_for(db, user)):
            raise HTTPException(422, "La receta no es compatible con tus restricciones.")
    row = Entry(user_id=user.id, kind="comida", data=data.model_dump(mode="json"))
    db.add(row)
    db.commit()
    return present(row)


@router.delete("/diary/food/{id}", status_code=204)
def remove_food(id: str, user=Depends(current_user), db=Depends(get_db)):
    row = db.scalar(
        select(Entry).where(Entry.id == id, Entry.user_id == user.id, Entry.kind == "comida")
    )
    if not row:
        raise HTTPException(404, "No se encontró ese registro de comida.")
    db.delete(row)
    db.commit()


@router.post("/diary/actions")
def action(data: DiaryAction, user=Depends(current_user), db=Depends(get_db)):
    user = lock_user(db, user)
    foods = [
        r
        for r in owned_entries(db, user, "comida")
        if r.data["date"] == data.date.isoformat()
        and (not data.meal or r.data["meal"] == data.meal)
    ]
    if data.action == "finalizar":
        if not foods:
            raise HTTPException(422, "Registra alguna comida antes de terminar el día.")
        if not any(
            r.data.get("date") == data.date.isoformat()
            for r in owned_entries(db, user, "dia_finalizado")
        ):
            db.add(
                Entry(user_id=user.id, kind="dia_finalizado", data={"date": data.date.isoformat()})
            )
    elif data.action == "vaciar":
        for r in foods:
            db.delete(r)
        for r in owned_entries(db, user, "dia_finalizado"):
            if r.data.get("date") == data.date.isoformat():
                db.delete(r)
    elif data.action == "porciones":
        for r in foods:
            doc = deepcopy(r.data)
            for k in [
                "quantity",
                "kcal",
                "protein",
                "carbs",
                "fat",
                "fiber",
                "sugar",
                "sodium",
                "saturated",
            ]:
                doc[k] = round(doc.get(k, 0) * data.multiplier, 3)
            r.data = validate_food(doc, db, user)
    elif data.action == "favorito":
        if not foods:
            raise HTTPException(422, "La comida está vacía.")
        db.add(
            Entry(
                user_id=user.id,
                kind="favorito",
                data={"name": data.meal or "Mi día", "foods": [r.data for r in foods]},
            )
        )
    else:
        if not foods:
            raise HTTPException(422, "No hay alimentos para copiar.")
        target = data.target_date or (data.date + timedelta(days=1))
        for r in foods:
            doc = deepcopy(r.data)
            doc["date"] = target.isoformat()
            if data.target_meal:
                doc["meal"] = data.target_meal
            db.add(Entry(user_id=user.id, kind="comida", data=validate_food(doc, db, user)))
    db.commit()
    return {"saved": True}


@router.get("/favorites")
def favorites(user=Depends(current_user), db=Depends(get_db)):
    return [present(r) for r in owned_entries(db, user, "favorito")]


@router.post("/favorites/{id}/use", status_code=201)
def use_favorite(id: str, data: DiaryAction, user=Depends(current_user), db=Depends(get_db)):
    user = lock_user(db, user)
    row = db.scalar(
        select(Entry).where(Entry.id == id, Entry.user_id == user.id, Entry.kind == "favorito")
    )
    if not row:
        raise HTTPException(404, "No se encontró esa receta guardada.")
    for food in row.data["foods"]:
        doc = deepcopy(food)
        doc["date"] = data.date.isoformat()
        if data.meal:
            doc["meal"] = data.meal
        db.add(Entry(user_id=user.id, kind="comida", data=validate_food(doc, db, user)))
    db.commit()
    return {"saved": True}


@router.post("/metrics", status_code=201)
def metric(data: MetricIn, user=Depends(current_user), db=Depends(get_db)):
    row = Entry(
        user_id=user.id, kind=data.kind, data=data.model_dump(mode="json", exclude={"kind"})
    )
    db.add(row)
    db.commit()
    return present(row)


@router.get("/streaks")
def streaks(user=Depends(current_user), db=Depends(get_db)):
    days = sorted({r.data["date"] for r in owned_entries(db, user, "dia_finalizado")})
    longest = current = 0
    previous = None
    for raw in days:
        day = date.fromisoformat(raw)
        current = current + 1 if previous and day == previous + timedelta(days=1) else 1
        longest = max(longest, current)
        previous = day
    return {"days": days, "best": longest, "registered": len(days)}


@router.post("/feedback", status_code=201)
def feedback(data: FeedbackIn, user=Depends(current_user), db=Depends(get_db)):
    owned = {r.id for r in owned_entries(db, user, "feedback_attachment")}
    if any(id not in owned for id in data.attachments):
        raise HTTPException(422, "Los adjuntos no pertenecen a tu cuenta.")
    row = Entry(user_id=user.id, kind="feedback", data=data.model_dump())
    db.add(row)
    db.commit()
    return {
        "id": row.id,
        "saved": True,
        "delivery": "Guardado en Mikuy; no se envió correo ni mensaje externo.",
    }


@router.get("/photos")
def photos(user=Depends(current_user), db=Depends(get_db)):
    return [present(r) for r in owned_entries(db, user, "foto")]


@router.post("/photos", status_code=201)
def add_photo(data: PhotoIn, user=Depends(current_user), db=Depends(get_db)):
    user = lock_user(db, user)
    if (
        len(owned_entries(db, user, "foto")) + len(owned_entries(db, user, "feedback_attachment"))
        >= 20
    ):
        raise HTTPException(
            403,
            "El almacenamiento local permite hasta 20 imágenes por cuenta. Elimina una antes de subir otra.",
        )
    row = Entry(
        user_id=user.id,
        kind="foto" if data.purpose == "progreso" else "feedback_attachment",
        data=data.model_dump(mode="json", exclude={"purpose"}),
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "saved": True}
