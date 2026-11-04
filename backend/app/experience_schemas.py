"""Typed contracts for the interactions visible in the reference screenshots."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


MealName = Literal["Desayuno", "Almuerzo", "Cena", "Snack 1", "Snack 2"]


class OnboardingAnswers(Strict):
    step: str = Field(default="objetivo", max_length=60)
    method: str = Field(default="", max_length=100)
    obstacles: list[str] = Field(default_factory=list, max_length=8)
    previous: list[str] = Field(default_factory=list, max_length=8)
    tedious: str = Field(default="", max_length=80)
    knowledge: str = Field(default="", max_length=80)
    sex: Literal["", "Hombre", "Mujer", "Prefiero no decir"] = ""
    age: int | None = Field(default=None, ge=0)
    height: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    weight: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    target_weight: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    strength: bool | None = None
    lifestyle: str = Field(default="", max_length=100)
    diet_style: str = Field(default="Recomendada", max_length=60)
    speed: str = Field(default="Recomendado", max_length=60)
    extra_goals: list[str] = Field(default_factory=list, max_length=6)
    rating: int | None = Field(default=None, ge=1, le=10)
    acquisition: str = Field(default="", max_length=100)


class Reminder(Strict):
    enabled: bool = False
    time: str = Field(default="09:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    days: list[int] = Field(default_factory=lambda: list(range(7)), max_length=7)
    interval_hours: int = Field(default=24, ge=1, le=72)

    @model_validator(mode="after")
    def valid_days(self):
        if any(day not in range(7) for day in self.days):
            raise ValueError("Días fuera del rango permitido.")
        self.days = sorted(set(self.days))
        return self


class ExperienceSettings(Strict):
    appearance: Literal["Tema del dispositivo", "Claro", "Oscuro"] = "Oscuro"
    vibration: bool = True
    food_weight: Literal["g", "oz"] = "g"
    liquid_volume: Literal["ml", "fl oz"] = "ml"
    body_weight: Literal["kg", "lb"] = "kg"
    height_unit: Literal["cm", "ft/in"] = "cm"
    energy_unit: Literal["kcal", "kJ"] = "kcal"
    calorie_target: int | None = Field(default=None, ge=1200, le=6000)
    protein_percent: int = Field(default=23, ge=5, le=60)
    carbs_percent: int = Field(default=47, ge=5, le=80)
    fat_percent: int = Field(default=30, ge=10, le=65)
    meal_distribution: dict[MealName, float] = Field(
        default_factory=lambda: {"Desayuno": 31.3, "Almuerzo": 40.6, "Cena": 28.1}
    )
    visible_cards: list[str] = Field(
        default_factory=lambda: [
            "Desayuno",
            "Almuerzo",
            "Cena",
            "Meds y Suplementos",
            "Actividad",
            "Agua",
            "Pasos",
            "Notas",
        ],
        max_length=10,
    )
    nutrients: list[str] = Field(
        default_factory=lambda: ["Azúcares", "Fibra", "Sodio", "Grasas Saturadas"], max_length=40
    )
    charts: list[str] = Field(
        default_factory=lambda: ["Calorías", "Peso Balanza", "% Grasa", "Fotos"], max_length=60
    )
    reminders: dict[str, Reminder] = Field(default_factory=dict, max_length=12)
    coach_alerts: bool = True
    coach_consent: bool = False
    coach_consent_provider: Literal["", "nvidia", "groq"] = ""
    coach_intro_seen: bool = False
    coach_memories: list[str] = Field(default_factory=list, max_length=30)
    copy_yesterday: bool = True
    portion_adjustment: bool = True
    plateau_detection: bool = False
    auto_calories: bool = False
    calories_by_day: bool = False
    public_profile: bool = False
    description: str = Field(default="", max_length=150)
    dismissed_banners: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def consistent(self):
        if self.protein_percent + self.carbs_percent + self.fat_percent != 100:
            raise ValueError("Los porcentajes de macros deben sumar 100.")
        if not self.meal_distribution or abs(sum(self.meal_distribution.values()) - 100) > 0.11:
            raise ValueError("La distribución de comidas debe sumar 100 %.")
        if any(v < 0 or v > 100 for v in self.meal_distribution.values()):
            raise ValueError("Porcentaje de comida inválido.")
        if any(len(s) > 500 for s in self.coach_memories):
            raise ValueError("Cada información guardada admite hasta 500 caracteres.")
        return self


class FoodIn(Strict):
    date: date
    meal: MealName
    name: str = Field(min_length=1, max_length=120)
    quantity: float = Field(default=1, gt=0, le=10000, allow_inf_nan=False)
    unit: Literal["g", "ml", "porción", "unid"] = "porción"
    kcal: float = Field(default=0, ge=0, le=10000, allow_inf_nan=False)
    protein: float = Field(default=0, ge=0, le=1000, allow_inf_nan=False)
    carbs: float = Field(default=0, ge=0, le=2000, allow_inf_nan=False)
    fat: float = Field(default=0, ge=0, le=1000, allow_inf_nan=False)
    fiber: float = Field(default=0, ge=0, le=200, allow_inf_nan=False)
    sugar: float = Field(default=0, ge=0, le=1000, allow_inf_nan=False)
    sodium: float = Field(default=0, ge=0, le=30000, allow_inf_nan=False)
    saturated: float = Field(default=0, ge=0, le=500, allow_inf_nan=False)
    recipe_id: str | None = Field(default=None, max_length=60)
    nutrition_declared: bool = False


class DiaryAction(Strict):
    action: Literal["copiar", "vaciar", "porciones", "repetir", "finalizar", "favorito"]
    date: date
    target_date: date | None = None
    meal: MealName | None = None
    target_meal: MealName | None = None
    multiplier: float = Field(default=1, gt=0, le=10, allow_inf_nan=False)


class MetricIn(Strict):
    kind: Literal["grasa", "medidas", "pasos", "sueno", "ejercicio", "suplemento"]
    date: date
    value: float | None = Field(default=None, ge=0, le=100000, allow_inf_nan=False)
    text: str = Field(default="", max_length=500)
    measurements: dict[str, float] = Field(default_factory=dict, max_length=8)

    @model_validator(mode="after")
    def reasonable(self):
        if self.kind == "grasa" and (self.value is None or not 2 <= self.value <= 75):
            raise ValueError("Grasa corporal fuera de rango.")
        if self.kind == "sueno" and (self.value is None or not 0 <= self.value <= 24):
            raise ValueError("Las horas de sueño deben estar entre 0 y 24.")
        if self.kind == "medidas" and (
            not self.measurements or any(not 1 <= v <= 300 for v in self.measurements.values())
        ):
            raise ValueError("Introduce medidas en cm entre 1 y 300.")
        if self.kind == "suplemento" and not self.text:
            raise ValueError("Introduce el nombre. No se recomiendan dosis.")
        return self


class FeedbackIn(Strict):
    category: Literal["sugerencia", "problema"]
    text: str = Field(min_length=3, max_length=3000)
    attachments: list[str] = Field(default_factory=list, max_length=4)


class PhotoIn(Strict):
    date: date
    purpose: Literal["progreso", "feedback"] = "progreso"
    image: str = Field(max_length=2800000)

    @model_validator(mode="after")
    def valid_image(self):
        import base64

        if not self.image.startswith(
            ("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,")
        ):
            raise ValueError("Formato de imagen no permitido.")
        try:
            raw = base64.b64decode(self.image.split(",", 1)[1], validate=True)
        except (ValueError, IndexError):
            raise ValueError("Imagen inválida.")
        if len(raw) > 2 * 1024 * 1024 or not (
            raw.startswith(b"\x89PNG\r\n\x1a\n")
            or raw.startswith(b"\xff\xd8\xff")
            or (raw.startswith(b"RIFF") and raw[8:12] == b"WEBP")
        ):
            raise ValueError("Imagen inválida o mayor a 2 MB.")
        return self


class PublicPostIn(Strict):
    text: str = Field(min_length=1, max_length=2000)
