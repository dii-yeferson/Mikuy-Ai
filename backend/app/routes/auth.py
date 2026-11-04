from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from ..db import get_db
from ..models import User
from ..security import DUMMY_HASH, current_user, end_session, hash_password, start_session, throttle, verify_password
from ..services import premium, profiles

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Register(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class Login(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


def me_payload(db, user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "profile": profiles.load(db, user.id),
        "subscription": premium.status(db, user.id),
    }


@router.post("/register")
def register(body: Register, request: Request, response: Response, db=Depends(get_db)):
    throttle(db, request, "register", 10)
    email = body.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Ya existe una cuenta con ese correo. Inicia sesión.")
    user = User(email=email, name=body.name.strip(), password_hash=hash_password(body.password))
    db.add(user)
    db.flush()
    profiles.save(db, user.id, {})
    start_session(db, response, user)
    out = me_payload(db, user)
    db.commit()
    return out


@router.post("/login")
def login(body: Login, request: Request, response: Response, db=Depends(get_db)):
    throttle(db, request, "login")
    user = db.scalar(select(User).where(User.email == body.email.lower().strip()))
    if not verify_password(body.password, user.password_hash if user else DUMMY_HASH) or not user:
        raise HTTPException(401, "Correo o contraseña incorrectos.")
    start_session(db, response, user)
    out = me_payload(db, user)
    db.commit()
    return out


@router.post("/logout")
def logout(request: Request, response: Response, db=Depends(get_db)):
    end_session(db, request, response)
    db.commit()
    return {"ok": True}


@router.get("/me")
def me(user=Depends(current_user), db=Depends(get_db)):
    out = me_payload(db, user)
    db.commit()
    return out


@router.delete("/me")
def delete_account(request: Request, response: Response, user=Depends(current_user), db=Depends(get_db)):
    end_session(db, request, response)
    db.delete(user)
    db.commit()
    return {"ok": True}
