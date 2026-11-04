from __future__ import annotations

from sqlalchemy import select

from ..models import Favorite, Profile

DEFAULTS = {
    "onboarded": False,
    "goal": "comer-mejor",
    "sex": "mujer",
    "age": 30,
    "weight_kg": 65,
    "height_cm": 162,
    "activity": "ligera",
    "diet": "omnivoro",
    "allergies": [],
    "excluded": [],
    "conditions": [],
    "city": "lima",
    "people": 1,
    "weekly_budget": 0,
    "max_minutes": 0,
    "snacks": False,
    "sounds": True,
    "haptics": True,
    "voice_reply": False,
    "theme": "auto",
}


def load(db, user_id: str) -> dict:
    row = db.get(Profile, user_id)
    data = {**DEFAULTS, **(row.data if row else {})}
    data["favorites"] = list(db.scalars(select(Favorite.recipe_id).where(Favorite.user_id == user_id)))
    return data


def save(db, user_id: str, changes: dict) -> dict:
    row = db.get(Profile, user_id)
    current = {**DEFAULTS, **(row.data if row else {})}
    current.update({k: v for k, v in changes.items() if k in DEFAULTS})
    if row:
        row.data = current
    else:
        db.add(Profile(user_id=user_id, data=current))
    db.flush()
    return load(db, user_id)
