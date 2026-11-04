import hashlib
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import func, select

from .config import settings
from .db import get_db
from .models import AuthAttempt, Session, User, utcnow

password_hasher = PasswordHasher()
DUMMY_HASH = password_hasher.hash("dummy-for-timing-only-mikuy")


def verify(password, digest):
    try:
        return password_hasher.verify(digest, password)
    except (VerificationError, InvalidHashError):
        return False


def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def set_session(db, response: Response, user):
    token = secrets.token_urlsafe(48)
    db.add(
        Session(
            digest=token_digest(token),
            user_id=user.id,
            expires_at=utcnow() + timedelta(days=settings().session_days),
        )
    )
    response.set_cookie(
        "mikuy_session",
        token,
        httponly=True,
        secure=settings().cookie_secure,
        samesite="lax",
        max_age=settings().session_days * 86400,
        path="/api",
    )


def current_user(request: Request, db=Depends(get_db)):
    token = request.cookies.get("mikuy_session", "")
    session = db.get(Session, token_digest(token)) if token else None
    if not session or session.expires_at <= utcnow():
        raise HTTPException(401, "Tu sesión expiró. Inicia sesión para continuar.")
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, "Inicia sesión para continuar.")
    return user


def throttle(db, request, action):
    address = request.client.host if request.client else "unknown"
    bucket = token_digest(f"{address}:{action}")
    recent = utcnow() - timedelta(minutes=15)
    count = db.scalar(
        select(func.count())
        .select_from(AuthAttempt)
        .where(AuthAttempt.bucket == bucket, AuthAttempt.created_at > recent)
    )
    if count >= 20:
        raise HTTPException(429, "Demasiados intentos. Vuelve a intentar en 15 minutos.")
    db.add(AuthAttempt(bucket=bucket))
    db.commit()  # Persist failed attempts as well.
