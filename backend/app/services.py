from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select

from .domain import LIMITS, conflicts
from .models import Plan, Profile, Usage, User
from .schemas import ProfileIn


def month():
    return datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m")


def lock_user(db, user):
    return db.scalar(
        select(User)
        .where(User.id == user.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def profile_for(db, user):
    row = db.get(Profile, user.id)
    return ProfileIn.model_validate(row.data if row else {})


def enforce_servings(user, servings):
    if servings > LIMITS[user.tier]["servings"]:
        raise HTTPException(
            403,
            f"Tu plan permite hasta {LIMITS[user.tier]['servings']} porciones. Revisa la suscripción simulada.",
        )


def quota(db, user, action, consume=False):
    key = (user.id, month(), action)
    row = db.get(Usage, key)
    count = row.count if row else 0
    if count >= LIMITS[user.tier][action]:
        raise HTTPException(
            403, "Alcanzaste el límite mensual de tu plan. Consulta la suscripción simulada."
        )
    if consume:
        if row:
            row.count += 1
        else:
            db.add(Usage(user_id=user.id, month=month(), action=action, count=1))


def public_user(db, user):
    usage = {
        a: (
            db.get(Usage, (user.id, month(), a)).count
            if db.get(Usage, (user.id, month(), a))
            else 0
        )
        for a in ["plans", "coach"]
    }
    return dict(
        id=user.id,
        name=user.name,
        email=user.email,
        tier=user.tier,
        limits=LIMITS[user.tier],
        usage=usage,
        month=month(),
    )


def owned_plan(db, user, id, lock=False):
    q = select(Plan).where(Plan.id == id, Plan.user_id == user.id)
    if lock:
        q = q.with_for_update()
    row = db.scalar(q.execution_options(populate_existing=True))
    if not row:
        raise HTTPException(404, "No se encontró ese plan.")
    return row


def plan_response(row, profile):
    return dict(
        id=row.id,
        version=row.version,
        created_at=row.created_at.isoformat(),
        **row.data,
        conflicts=conflicts(row.data, profile),
    )
