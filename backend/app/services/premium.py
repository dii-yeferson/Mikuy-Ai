"""Planes de suscripción. El cobro real aún no está conectado: se simula con un código."""

from __future__ import annotations

import secrets
from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select

from ..models import PaymentCode, Subscription, Usage, utcnow

PLANS = {
    "premium": {
        "name": "Mikuy Premium",
        "prices": {"mensual": 14.90, "anual": 119.00},
        "members": 1,
        "features": [
            "Mikuy AI sin límites, por texto y por voz",
            "Menús ilimitados y cambios de platos al instante",
            "Precios aproximados para tu ciudad",
            "Recetario completo con 300+ recetas peruanas",
        ],
    },
    "familia": {
        "name": "Mikuy Familia",
        "prices": {"mensual": 24.90, "anual": 199.00},
        "members": 6,
        "features": [
            "Todo lo de Premium",
            "Menú y compras para toda la familia (hasta 6)",
            "Porciones por persona y alergias de cada uno",
            "Lista de compras compartible por WhatsApp",
        ],
    },
}
FREE_LIMITS = {"ai_per_day": 5, "plans_per_week": 3}
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def subscription(db, user_id: str) -> Subscription:
    sub = db.get(Subscription, user_id)
    if not sub:
        sub = Subscription(user_id=user_id, plan="gratis")
        db.add(sub)
        db.flush()
    if sub.plan != "gratis" and sub.expires_at and sub.expires_at < utcnow():
        sub.plan, sub.period = "gratis", None
    return sub


def is_premium(db, user_id: str) -> bool:
    return subscription(db, user_id).plan in PLANS


def status(db, user_id: str) -> dict:
    sub = subscription(db, user_id)
    today = date.today()
    usage = db.get(Usage, (user_id, today))
    week_plans = db.scalar(
        select(func.coalesce(func.sum(Usage.plans), 0)).where(Usage.user_id == user_id, Usage.day > today - timedelta(days=7))
    )
    return {
        "plan": sub.plan,
        "plan_name": PLANS[sub.plan]["name"] if sub.plan in PLANS else "Gratis",
        "period": sub.period,
        "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
        "premium": sub.plan in PLANS,
        "simulated": sub.simulated,
        "limits": None if sub.plan in PLANS else {
            "ai_per_day": FREE_LIMITS["ai_per_day"],
            "ai_used_today": usage.ai_messages if usage else 0,
            "plans_per_week": FREE_LIMITS["plans_per_week"],
            "plans_used_week": int(week_plans or 0),
        },
    }


def _usage(db, user_id: str) -> Usage:
    today = date.today()
    row = db.get(Usage, (user_id, today))
    if not row:
        row = Usage(user_id=user_id, day=today, ai_messages=0, plans=0)
        db.add(row)
        db.flush()
    return row


def consume(db, user_id: str, kind: str) -> None:
    """Cuenta un uso; en el plan gratis respeta los límites."""
    premium = is_premium(db, user_id)
    row = _usage(db, user_id)
    if kind == "ai":
        if not premium and row.ai_messages >= FREE_LIMITS["ai_per_day"]:
            raise HTTPException(402, "Usaste tus 5 mensajes gratis de hoy. Con Premium hablas con Mikuy AI sin límites.")
        row.ai_messages += 1
    elif kind == "plan":
        week = db.scalar(
            select(func.coalesce(func.sum(Usage.plans), 0)).where(
                Usage.user_id == user_id, Usage.day > date.today() - timedelta(days=7)
            )
        )
        if not premium and week >= FREE_LIMITS["plans_per_week"]:
            raise HTTPException(402, "Generaste 3 menús esta semana. Con Premium creas todos los que quieras.")
        row.plans += 1


def new_code() -> str:
    pick = lambda n: "".join(secrets.choice(ALPHABET) for _ in range(n))  # noqa: E731
    return f"MIKUY-{pick(4)}-{pick(4)}"


def checkout(db, user_id: str, plan: str, period: str) -> PaymentCode:
    if plan not in PLANS or period not in ("mensual", "anual"):
        raise HTTPException(422, "Plan no válido.")
    code = PaymentCode(
        code=new_code(),
        user_id=user_id,
        plan=plan,
        period=period,
        amount=PLANS[plan]["prices"][period],
        expires_at=utcnow() + timedelta(minutes=30),
    )
    db.add(code)
    return code


def redeem(db, user_id: str, raw: str) -> Subscription:
    code_value = raw.strip().upper().replace(" ", "")
    code = db.get(PaymentCode, code_value)
    if not code or code.user_id != user_id:
        raise HTTPException(404, "Ese código no existe o no pertenece a tu cuenta.")
    if code.redeemed_at:
        raise HTTPException(409, "Ese código ya fue usado.")
    if code.expires_at < utcnow():
        raise HTTPException(410, "El código venció. Genera uno nuevo.")
    sub = subscription(db, user_id)
    start = utcnow()
    base = sub.expires_at if sub.plan in PLANS and sub.expires_at and sub.expires_at > start else start
    sub.plan, sub.period = code.plan, code.period
    sub.started_at = sub.started_at or start
    sub.expires_at = base + timedelta(days=365 if code.period == "anual" else 30)
    sub.simulated = True
    code.redeemed_at = start
    return sub


def cancel(db, user_id: str) -> Subscription:
    sub = subscription(db, user_id)
    sub.plan, sub.period, sub.expires_at = "gratis", None, None
    return sub
