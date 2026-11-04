from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from .db import get_db
from .models import Entry
from .schemas import EntryIn
from .security import current_user

router = APIRouter(prefix="/entries", tags=["Registros"])


@router.get("")
def entries(user=Depends(current_user), db=Depends(get_db)):
    return [
        dict(id=r.id, kind=r.kind, **r.data)
        for r in db.scalars(
            select(Entry)
            .where(Entry.user_id == user.id, Entry.kind.not_in(["foto", "feedback_attachment", "coach_proposal", "saved_recipe", "coach_insight"]))
            .order_by(Entry.created_at.desc())
        )
    ]


@router.post("", status_code=201)
def add_entry(data: EntryIn, user=Depends(current_user), db=Depends(get_db)):
    if data.kind == "nota" and not data.text:
        raise HTTPException(422, "Escribe una nota antes de guardar.")
    if data.kind == "agua" and (data.value is None or not 1 <= data.value <= 3000):
        raise HTTPException(422, "Registra entre 1 y 3000 ml de agua.")
    if data.kind == "peso" and (data.value is None or data.value <= 0):
        raise HTTPException(422, "Introduce un peso mayor que cero en kg.")
    row = Entry(
        user_id=user.id, kind=data.kind, data=data.model_dump(mode="json", exclude={"kind"})
    )
    db.add(row)
    db.commit()
    return dict(id=row.id, kind=row.kind, **row.data)


@router.delete("/{id}", status_code=204)
def remove(id: str, user=Depends(current_user), db=Depends(get_db)):
    row = db.scalar(select(Entry).where(Entry.id == id, Entry.user_id == user.id))
    if not row:
        raise HTTPException(404, "No se encontró ese registro.")
    db.delete(row)
    db.commit()
