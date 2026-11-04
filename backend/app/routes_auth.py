from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from .db import get_db
from .models import Profile, Session, User
from .routes_onboarding import draft_for
from .schemas import Login, Register
from .security import (
    DUMMY_HASH,
    current_user,
    password_hasher,
    set_session,
    throttle,
    token_digest,
    verify,
)
from .services import public_user

router = APIRouter(prefix="/auth", tags=["Sesión"])


@router.post("/register", status_code=201)
def register(data: Register, request: Request, response: Response, db=Depends(get_db)):
    throttle(db, request, "auth")
    user = User(
        email=str(data.email).lower(),
        name=data.name,
        password_hash=password_hasher.hash(data.password),
    )
    db.add(user)
    try:
        db.flush()
        draft = draft_for(request, db)
        db.add(Profile(user_id=user.id, data=draft.data if draft else {}))
        if draft:
            db.delete(draft)
            response.delete_cookie("mikuy_onboarding", path="/api")
        set_session(db, response, user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "No se pudo crear la cuenta con ese correo. Prueba iniciar sesión."
        )
    return public_user(db, user)


@router.post("/login")
def login(data: Login, request: Request, response: Response, db=Depends(get_db)):
    throttle(db, request, "auth")
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    valid = verify(data.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401, "Correo o contraseña incorrectos.")
    old = request.cookies.get("mikuy_session")
    if old:
        db.execute(delete(Session).where(Session.digest == token_digest(old)))
    set_session(db, response, user)
    db.commit()
    return public_user(db, user)


@router.get("/me")
def me(user=Depends(current_user), db=Depends(get_db)):
    return public_user(db, user)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db=Depends(get_db)):
    token = request.cookies.get("mikuy_session")
    if token:
        db.execute(delete(Session).where(Session.digest == token_digest(token)))
        db.commit()
    response.delete_cookie("mikuy_session", path="/api")
