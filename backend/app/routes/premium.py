from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..config import settings
from ..db import get_db
from ..security import current_user
from ..services import premium

router = APIRouter(prefix="/api/premium", tags=["premium"])


class CheckoutIn(BaseModel):
    plan: Literal["premium", "familia"]
    period: Literal["mensual", "anual"]


class RedeemIn(BaseModel):
    code: str = Field(min_length=6, max_length=24)


@router.get("/plans")
def plans():
    return {
        "plans": premium.PLANS,
        "free": {"limits": premium.FREE_LIMITS},
        "simulated": settings().payments_simulated,
        "currency": "PEN",
    }


@router.get("/status")
def status(user=Depends(current_user), db=Depends(get_db)):
    out = premium.status(db, user.id)
    db.commit()
    return out


@router.post("/checkout")
def checkout(body: CheckoutIn, user=Depends(current_user), db=Depends(get_db)):
    """Simulación: en lugar de cobrar, la app genera un código de activación."""
    code = premium.checkout(db, user.id, body.plan, body.period)
    db.commit()
    return {
        "code": code.code,
        "amount": code.amount,
        "plan": code.plan,
        "period": code.period,
        "expires_at": code.expires_at.isoformat(),
        "simulated": True,
        "notice": "Pago real pendiente de configurar. Este código activa tu plan en modo de prueba.",
    }


@router.post("/redeem")
def redeem(body: RedeemIn, user=Depends(current_user), db=Depends(get_db)):
    premium.redeem(db, user.id, body.code)
    out = premium.status(db, user.id)
    db.commit()
    return out


@router.post("/cancel")
def cancel(user=Depends(current_user), db=Depends(get_db)):
    premium.cancel(db, user.id)
    out = premium.status(db, user.id)
    db.commit()
    return out
