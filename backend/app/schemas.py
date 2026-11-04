import unicodedata
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .experience_schemas import ExperienceSettings, OnboardingAnswers


def normalize(s: str):
    return "".join(
        c
        for c in unicodedata.normalize("NFD", s.strip().lower())
        if unicodedata.category(c) != "Mn"
    )


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Strict):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class Register(Login):
    name: str = Field(min_length=1, max_length=60)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value):
        if not value.strip():
            raise ValueError("El nombre no puede estar vacío.")
        return value.strip()


ALLERGENS = {
    "leche",
    "huevo",
    "pescado",
    "mariscos",
    "mani",
    "frutos secos",
    "soya",
    "gluten",
    "sesamo",
}


class ProfileIn(Strict):
    goal: Literal[
        "Comer más sano",
        "Bajar de peso",
        "Controlar mi condición",
        "Ahorrar y organizarme",
        "Perder grasa",
        "Ganar músculo",
        "Mantener peso",
    ] = "Comer más sano"
    health: list[Literal["diabetes", "prediabetes", "hipertension", "obesidad"]] = Field(
        default_factory=list, max_length=4
    )
    condition_owner: Literal["", "Yo", "Un familiar", "Varios en casa"] = ""
    cook_for: Literal["", "Solo para mí", "Para mi pareja o familia"] = ""
    shop_place: Literal["", "Mercado", "Supermercado", "Bodega", "Delivery"] = ""
    cook_time: Literal["", "Menos de 20 min", "20 a 40 min", "Más de 40 min"] = ""
    favorite_dishes: list[str] = Field(default_factory=list, max_length=20)
    servings: int = Field(default=1, ge=1, le=6)
    budget: float = Field(default=150, ge=20, le=3000, allow_inf_nan=False)
    diet: Literal["Balanceado", "Pescetariano", "Vegetariano", "Vegano"] = "Balanceado"
    allergies: list[str] = Field(default_factory=list, max_length=9)
    excluded: list[str] = Field(default_factory=list, max_length=30)
    conditions: str = Field(default="", max_length=500)
    preferences: str = Field(default="", max_length=500)
    activity: str = Field(default="No hago ejercicio", max_length=80)
    motivation: str = Field(default="", max_length=80)
    tone: Literal["Gentil", "Directo", "Empático"] = "Gentil"
    completed: bool = False
    # JSON-backed typed subdocuments; kept alongside existing profile data.
    onboarding: OnboardingAnswers = Field(default_factory=OnboardingAnswers)
    settings: ExperienceSettings = Field(default_factory=ExperienceSettings)

    @field_validator("health")
    @classmethod
    def unique_health(cls, values):
        return sorted(set(values))

    @field_validator("favorite_dishes")
    @classmethod
    def dishes(cls, values):
        if any(not v.strip() or len(v) > 60 for v in values):
            raise ValueError("Cada plato favorito debe tener de 1 a 60 caracteres.")
        return list(dict.fromkeys(v.strip() for v in values))

    @field_validator("allergies")
    @classmethod
    def known_allergens(cls, values):
        values = sorted(set(normalize(v) for v in values))
        if any(v not in ALLERGENS for v in values):
            raise ValueError(
                "Selecciona un alérgeno reconocido; otras restricciones van en alimentos excluidos."
            )
        return values

    @field_validator("excluded")
    @classmethod
    def exclusions(cls, values):
        if any(not v.strip() or len(v) > 60 for v in values):
            raise ValueError("Cada alimento excluido debe tener de 1 a 60 caracteres.")
        return sorted(set(normalize(v) for v in values))


class DoneIn(Strict):
    done: bool


class PlanIn(Strict):
    start_date: date
    source: Literal["catalogo", "nvidia"] = "catalogo"
    consent: bool = False


class MealEdit(Strict):
    recipe_id: str = Field(max_length=50)
    servings: int = Field(ge=1, le=6)
    expected_version: int = Field(ge=1)


class ShoppingEdit(Strict):
    quantity: float = Field(ge=0, le=100000, allow_inf_nan=False)
    unit_price: float = Field(ge=0, le=1000, allow_inf_nan=False)
    checked: bool


class CoachIn(Strict):
    question: str = Field(min_length=2, max_length=2000)
    consent: bool = False
    conversation_id: str | None = Field(default=None, max_length=36)


class SubscriptionIn(Strict):
    tier: Literal["gratis", "premium", "familiar"]
    simulation: Literal[True]


class DeleteAccount(Strict):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    password: str = Field(min_length=1, max_length=128)


class EntryIn(Strict):
    kind: Literal["agua", "peso", "nota"]
    date: date
    value: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    text: str = Field(default="", max_length=1500)

    @field_validator("text")
    @classmethod
    def plain_text(cls, s):
        return s.strip()
