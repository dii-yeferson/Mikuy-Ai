from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import delete, select

from .db import get_db
from .models import Conversation, Entry, Message, utcnow
from .schemas import Strict
from .security import current_user
from .services import lock_user

router = APIRouter(prefix="/coach/conversations", tags=["Coach"])
UNDO_SECONDS = 10


def purge(db):
    expired = select(Message.id).join(Conversation).where(Conversation.delete_after <= utcnow())
    db.execute(
        delete(Entry).where(
            Entry.kind.in_(["coach_proposal", "coach_insight"]), Entry.data["message_id"].as_string().in_(expired)
        ),
        execution_options={"synchronize_session": False},
    )
    db.execute(delete(Conversation).where(Conversation.delete_after <= utcnow()))


def owned(db, user, id, include_deleted=False):
    row = db.scalar(select(Conversation).where(Conversation.id == id).with_for_update())
    if not row or row.user_id != user.id or (row.delete_after and not include_deleted):
        raise HTTPException(404, "No se encontró la conversación.")
    return row


def resolve(db, user, id, question):
    if id:
        return owned(db, user, id)
    # Backwards-compatible clients continue their latest active conversation.
    row = db.scalar(
        select(Conversation)
        .where(Conversation.user_id == user.id, Conversation.delete_after.is_(None))
        .order_by(Conversation.updated_at.desc())
        .limit(1)
    )
    if not row:
        row = Conversation(user_id=user.id, title=question[:100])
        db.add(row)
        db.flush()
    return row


def present(row):
    return dict(id=row.id, title=row.title, date=row.updated_at.isoformat())


@router.get("")
def listing(user=Depends(current_user), db=Depends(get_db)):
    purge(db)
    db.commit()
    return [
        present(r)
        for r in db.scalars(
            select(Conversation)
            .where(Conversation.user_id == user.id, Conversation.delete_after.is_(None))
            .order_by(Conversation.updated_at.desc())
        )
    ]


@router.post("", status_code=201)
def create(user=Depends(current_user), db=Depends(get_db)):
    row = Conversation(user_id=user.id)
    db.add(row)
    db.commit()
    return present(row)


def mark_deleted(db, rows):
    deadline = utcnow() + timedelta(seconds=UNDO_SECONDS)
    for row in rows:
        row.delete_after = deadline
    db.commit()
    return dict(ids=[r.id for r in rows], undo_until=deadline.isoformat())


@router.delete("")
def clear(user=Depends(current_user), db=Depends(get_db)):
    user = lock_user(db, user)
    rows = list(
        db.scalars(
            select(Conversation).where(
                Conversation.user_id == user.id, Conversation.delete_after.is_(None)
            )
        )
    )
    return mark_deleted(db, rows)


@router.delete("/{id}")
def remove(id: str, user=Depends(current_user), db=Depends(get_db)):
    user = lock_user(db, user)
    return mark_deleted(db, [owned(db, user, id)])


class RestoreIn(Strict):
    ids: list[str] = Field(min_length=1, max_length=10000)


@router.post("/restore")
def restore(data: RestoreIn, user=Depends(current_user), db=Depends(get_db)):
    user = lock_user(db, user)
    rows = [owned(db, user, id, include_deleted=True) for id in data.ids]
    if any(not r.delete_after or r.delete_after <= utcnow() for r in rows):
        raise HTTPException(410, "El plazo para deshacer terminó.")
    for row in rows:
        row.delete_after = None
    db.commit()
    return [present(r) for r in rows]
