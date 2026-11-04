import hashlib
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import delete, func, select

from .config import settings
from .db import get_db
from .models import AuthAttempt, Session, User, utcnow

COOKIE = "mikuy_session"
hasher = PasswordHasher()
DUMMY_HASH = hasher.hash("mikuy-dummy-password-for-timing")


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, digest: str) -> bool:
    try:
        return hasher.verify(digest, password)
    except (VerificationError, InvalidHashError):
        return False


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(db, response: Response, user: User) -> None:
    token = secrets.token_urlsafe(48)
    days = settings().session_days
    db.add(Session(digest=digest(token), user_id=user.id, expires_at=utcnow() + timedelta(days=days)))
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=settings().cookie_secure,
        samesite=settings().cookie_samesite,
        max_age=days * 86400,
        path="/",
    )


def end_session(db, request: Request, response: Response) -> None:
    token = request.cookies.get(COOKIE)
    if token:
        db.execute(delete(Session).where(Session.digest == digest(token)))
    response.delete_cookie(COOKIE, path="/")


def current_user(request: Request, db=Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE, "")
    session = db.get(Session, digest(token)) if token else None
    if not session or session.expires_at <= utcnow():
        raise HTTPException(401, "Inicia sesión para continuar.")
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, "Inicia sesión para continuar.")
    return user


def throttle(db, request: Request, action: str, limit: int = 15) -> None:
    address = request.client.host if request.client else "unknown"
    bucket = digest(f"{address}:{action}")
    since = utcnow() - timedelta(minutes=15)
    count = db.scalar(
        select(func.count()).select_from(AuthAttempt).where(AuthAttempt.bucket == bucket, AuthAttempt.created_at > since)
    )
    if count >= limit:
        raise HTTPException(429, "Demasiados intentos. Espera 15 minutos e inténtalo de nuevo.")
    db.add(AuthAttempt(bucket=bucket))
    db.commit()
