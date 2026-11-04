from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import Field
from sqlalchemy import delete, select

from .db import get_db
from .domain import LIMITS
from .models import Conversation, Entry, Message, Plan, Profile, User
from .schemas import DeleteAccount, ProfileIn, Strict, SubscriptionIn
from .security import current_user, verify
from .services import enforce_servings, lock_user, profile_for, public_user

router = APIRouter(tags=["Perfil y cuenta"])


@router.get("/profile")
def get_profile(user=Depends(current_user), db=Depends(get_db)):
    return profile_for(db, user)


@router.put("/profile")
def save_profile(data: ProfileIn, user=Depends(current_user), db=Depends(get_db)):
    user = lock_user(db, user)
    enforce_servings(user, data.servings)
    row = db.get(Profile, user.id)
    if not row:
        row = Profile(user_id=user.id)
        db.add(row)
    row.data = data.model_dump()
    db.commit()
    return data


@router.get("/subscription")
def subscription(user=Depends(current_user), db=Depends(get_db)):
    return dict(**public_user(db, user), simulation=True, tiers=LIMITS)


@router.post("/subscription")
def change_subscription(data: SubscriptionIn, user=Depends(current_user), db=Depends(get_db)):
    user = lock_user(db, user)
    profile = profile_for(db, user)
    if profile.servings > LIMITS[data.tier]["servings"]:
        raise HTTPException(
            422,
            "Reduce primero las porciones de tu perfil para cambiar a ese plan. Tus planes anteriores se conservan.",
        )
    user.tier = data.tier
    db.commit()
    return dict(**public_user(db, user), simulation=True)


class NameIn(Strict):
    name: str = Field(min_length=1, max_length=60)


@router.patch("/account")
def rename(data: NameIn, user=Depends(current_user), db=Depends(get_db)):
    user.name = data.name
    db.commit()
    return public_user(db, user)


@router.get("/account/export")
def export(user=Depends(current_user), db=Depends(get_db)):
    return dict(
        account=public_user(db, user),
        profile=profile_for(db, user).model_dump(),
        plans=[
            dict(id=r.id, version=r.version, **r.data)
            for r in db.scalars(select(Plan).where(Plan.user_id == user.id))
        ],
        coach=[
            dict(question=r.question, answer=r.answer, date=r.created_at.isoformat())
            for r in db.scalars(
                select(Message)
                .join(Conversation)
                .where(Message.user_id == user.id, Conversation.delete_after.is_(None))
            )
        ],
        entries=[
            dict(id=r.id, kind=r.kind, **r.data)
            for r in db.scalars(select(Entry).where(Entry.user_id == user.id))
        ],
    )


@router.delete("/account", status_code=204)
def delete_account(
    data: DeleteAccount, response: Response, user=Depends(current_user), db=Depends(get_db)
):
    user = lock_user(db, user)
    if not verify(data.password, user.password_hash):
        raise HTTPException(401, "La contraseña no coincide.")
    db.execute(delete(User).where(User.id == user.id))
    db.commit()
    response.delete_cookie("mikuy_session", path="/api")
