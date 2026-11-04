import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import delete

from .config import settings
from .db import get_db
from .models import OnboardingDraft, utcnow
from .schemas import ProfileIn
from .security import throttle, token_digest

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


def draft_for(request, db):
    token = request.cookies.get("mikuy_onboarding", "")
    row = db.get(OnboardingDraft, token_digest(token)) if token else None
    return row if row and row.expires_at > utcnow() else None


@router.get("/draft")
def read(request: Request, db=Depends(get_db)):
    row = draft_for(request, db)
    return ProfileIn.model_validate(row.data if row else {})


@router.put("/draft")
def save(data: ProfileIn, request: Request, response: Response, db=Depends(get_db)):
    row = draft_for(request, db)
    if not row:
        throttle(db, request, "onboarding")
        db.execute(delete(OnboardingDraft).where(OnboardingDraft.expires_at < utcnow()))
        token = secrets.token_urlsafe(48)
        row = OnboardingDraft(digest=token_digest(token), expires_at=utcnow() + timedelta(days=1))
        db.add(row)
        response.set_cookie(
            "mikuy_onboarding",
            token,
            httponly=True,
            secure=settings().cookie_secure,
            samesite="lax",
            max_age=86400,
            path="/api",
        )
    row.data = data.model_dump()
    db.commit()
    return data
