"""Account-scoped progress, supplied restaurant menus and confirmed goal actions."""

import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from statistics import mean
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select

from .conversations import owned
from .db import get_db
from .models import Entry, Message, Profile
from .safety import ALLERGEN_ALIASES, contains
from .schemas import Strict, normalize
from .security import current_user
from .services import lock_user, profile_for

router = APIRouter(prefix="/coach-insights", tags=["Mikuy AI"])
FARE = dict(
    id="fare-dining",
    title="FARE — Dining Out",
    source="FARE — Dining Out",
    url="https://www.foodallergy.org/resources/dining-out",
)
CHILD = dict(
    id="niddk-children",
    title="NIDDK — Helping Your Child",
    source="NIDDK — Helping Your Child",
    url="https://www.niddk.nih.gov/health-information/weight-management/helping-your-child-who-is-overweight",
)


class Point(Strict):
    date: date
    value: float = Field(allow_inf_nan=False)


class Series(Strict):
    label: str
    unit: str
    points: list[Point] = Field(default_factory=list, max_length=28)


class Advice(Strict):
    text: str
    reason: str


class Dish(Strict):
    name: str
    supplied_text: str
    price: float | None = None
    budget_status: Literal["dentro", "fuera", "desconocido"] = "desconocido"
    cautions: list[str] = Field(default_factory=list)
    suggestion: str
    nutrition_note: str = (
        "Sin datos oficiales ni cantidades suficientes: no se asignan calorías ni nutrientes."
    )


class GoalAction(Strict):
    old_value: int | None
    new_value: int
    status: Literal["pending", "confirmed", "cancelled"] = "pending"
    explanation: str = "Valor solicitado por ti; no es un cálculo de tus necesidades energéticas."


class Insight(Strict):
    kind: Literal["progress", "dining", "goal"]
    title: str
    as_of: str
    summary: str
    series: list[Series] = Field(default_factory=list, max_length=3)
    facts: list[str] = Field(default_factory=list, max_length=12)
    recommendations: list[Advice] = Field(default_factory=list, max_length=6)
    dishes: list[Dish] = Field(default_factory=list, max_length=12)
    action: GoalAction | None = None


def clinical_guard(question, profile, previous=()):
    q = normalize(question)
    nutrition = bool(
        re.search(r"peso|caloria|dieta|ayun|comer|aliment|menu|plan|objetivo|progreso|porcion", q)
    )
    if not nutrition:
        return None
    age = profile.onboarding.age
    if age is not None and age < 18:
        return "Como tu perfil indica que eres menor de edad, no ajustaré calorías ni propondré un plan para perder peso. Un nutricionista o médico que atienda a menores puede valorar crecimiento y necesidades. Puedo ayudarte a organizar los registros para esa consulta."
    personal = " ".join([q, *[normalize(m.question) for m in previous]])
    if re.search(
        r"(?:estoy|soy|tengo|mi|con)\s+(?:\w+\s+){0,2}(?:embaraz|gestacion|enfermedad renal|insuficiencia renal|dialisis|anorexia|bulimia|trastorno aliment)",
        personal,
    ) or re.search(r"me provoco.*vom|quiero purgar|dejar de comer|ayunar.*(?:dias|semana)", q):
        return "Esta situación necesita evaluación individual de un nutricionista o médico. No modificaré objetivos ni elaboraré una dieta personalizada automáticamente. Puedo ayudarte a resumir tus registros y preparar preguntas para la consulta."
    return None


def profile_hash(profile):
    return hashlib.sha256(
        json.dumps(profile.model_dump(mode="json"), sort_keys=True).encode()
    ).hexdigest()


def linked(db, message):
    row = db.scalar(
        select(Entry).where(
            Entry.user_id == message.user_id,
            Entry.kind == "coach_insight",
            Entry.data["message_id"].as_string() == message.id,
        )
    )
    return (
        {"id": row.id, **Insight.model_validate(row.data["view"]).model_dump(mode="json")}
        if row
        else None
    )


def result(view, sources=(), private=None):
    return dict(
        answer=view.summary,
        sources=list(sources),
        view=view.model_dump(mode="json"),
        private=private or {},
    )


def progress(db, user, profile):
    end = datetime.now(ZoneInfo("America/Lima")).date()
    start = end - timedelta(days=27)
    rows = list(
        db.scalars(
            select(Entry)
            .where(
                Entry.user_id == user.id,
                Entry.kind.in_(["peso", "comida", "pasos", "ejercicio"]),
                Entry.data["date"].as_string() >= start.isoformat(),
                Entry.data["date"].as_string() <= end.isoformat(),
            )
            .order_by(Entry.created_at)
        )
    )
    weights = {}
    calories = {}
    steps = {}
    missing = 0
    exercise = 0
    food_days = set()
    for row in rows:
        d = row.data
        day = d.get("date")
        if row.kind == "peso" and d.get("value", 0) > 0:
            weights[day] = float(d["value"])
        elif row.kind == "comida":
            food_days.add(day)
            if d.get("nutrition_declared"):
                calories[day] = calories.get(day, Decimal(0)) + Decimal(str(d.get("kcal", 0)))
            else:
                missing += 1
        elif row.kind == "pasos" and d.get("value") is not None:
            steps[day] = steps.get(day, 0) + float(d["value"])
        elif row.kind == "ejercicio":
            exercise += 1
    current = [v for d, v in weights.items() if d >= (end - timedelta(days=6)).isoformat()]
    prior = [
        v
        for d, v in weights.items()
        if (end - timedelta(days=13)).isoformat() <= d < (end - timedelta(days=6)).isoformat()
    ]
    facts = [
        f"Objetivo registrado: {profile.goal}.",
        f"{len(weights)} días con peso, {len(food_days)} con comidas y {len(steps)} con pasos en los últimos 28 días.",
        f"{exercise} registros de ejercicio; no se infieren calorías gastadas.",
        f"{missing} comidas sin nutrientes declarados. Los días sin registro no equivalen a cero consumo.",
    ]
    recommendations = []
    if len(current) >= 3 and len(prior) >= 3:
        a = round(mean(prior), 2)
        b = round(mean(current), 2)
        delta = round(b - a, 2)
        summary = f"El promedio de tus pesos registrados pasó de {a} kg a {b} kg entre las dos últimas semanas ({delta:+.2f} kg). Es una comparación de registros, no una medición de grasa corporal."
        recommendations.append(
            Advice(
                text="Revisa la tendencia junto con tus comidas y cómo te encuentras, antes de cambiar el plan.",
                reason="El peso por sí solo no explica la causa del cambio; no se modificó ningún objetivo.",
            )
        )
    else:
        summary = "Todavía no hay suficientes días comparables de peso para describir una tendencia. No sacaré conclusiones por un solo día."
        recommendations.append(
            Advice(
                text="Añade registros de peso de varias fechas si quieres comparar semanas.",
                reason="Para esta comparación descriptiva se requieren al menos tres fechas en cada una de las dos últimas semanas; es un criterio del resumen, no una pauta médica de pesaje.",
            )
        )
    if not rows:
        summary = "Todavía no tienes registros de progreso. Para empezar, registra peso en distintas fechas o las comidas que quieras revisar."
    if calories:
        facts.append(
            f"Promedio de calorías declaradas por día con datos: {round(float(sum(calories.values())) / len(calories))} kcal. Puede ser un subtotal si faltan alimentos; no prueba un déficit ni un exceso."
        )
    if profile.settings.calorie_target:
        facts.append(
            f"Meta guardada: {profile.settings.calorie_target} kcal. No se recalculó a partir del peso."
        )
    if len(food_days) < 7:
        recommendations.append(
            Advice(
                text="Completa los alimentos y cantidades que falten en tu diario.",
                reason="Un registro incompleto no permite comparar la ingesta total con la meta.",
            )
        )
    series = [
        Series(
            label=label,
            unit=unit,
            points=[Point(date=d, value=float(v)) for d, v in sorted(values.items())],
        )
        for label, unit, values in [
            ("Peso registrado", "kg", weights),
            ("Calorías declaradas", "kcal", calories),
            ("Pasos registrados", "pasos", steps),
        ]
        if values
    ]
    return result(
        Insight(
            kind="progress",
            title="Tu progreso registrado",
            as_of=end.isoformat(),
            summary=summary,
            series=series,
            facts=facts,
            recommendations=recommendations,
        )
    )


def dining(question, profile):
    q = normalize(question)
    amount = re.search(r"(\d+(?:[.,]\d+)?)\s*soles|s/\s*(\d+(?:[.,]\d+)?)", q)
    budget = float((amount.group(1) or amount.group(2)).replace(",", ".")) if amount else None
    supplied = re.split(r"(?:carta|platos|descripcion)\s*:", question, maxsplit=1, flags=re.I)
    lines = re.split(r"[\n;]+", supplied[-1]) if len(supplied) > 1 else []
    allergies = set(profile.allergies)
    if "alerg" in q:
        allergies.update(
            a
            for a, aliases in ALLERGEN_ALIASES.items()
            if any(contains(q, t) for t in [a, *aliases])
        )
    dishes = []
    for line in lines[:12]:
        line = line.strip()
        if not line or re.search(
            r"ignora|instruccion|system|assistant|api.key|guarda|ejecuta|diagnostica",
            normalize(line),
        ):
            continue
        price_match = re.search(
            r"(?:S/\s*|PEN\s*)(\d+(?:[.,]\d{1,2})?)|(\d+(?:[.,]\d{1,2})?)\s*soles", line, re.I
        )
        price = (
            float((price_match.group(1) or price_match.group(2)).replace(",", "."))
            if price_match
            else None
        )
        name = (line[: price_match.start()] if price_match else line).strip(" -:|")[
            :120
        ] or "Plato descrito"
        alerts = []
        for allergy in allergies:
            if any(contains(line, t) for t in [allergy, *ALLERGEN_ALIASES.get(allergy, [])]):
                alerts.append(
                    f"La descripción menciona un posible alérgeno ({allergy}); no lo elijas sin aclararlo con el establecimiento."
                )
        if allergies:
            alerts.append(
                "Confirma todos los ingredientes, salsas, aceite, utensilios y posible contaminación cruzada con el establecimiento. La carta no demuestra que sea seguro. [1]"
            )
        if any(contains(line, x) for x in profile.excluded):
            alerts.append("Incluye un alimento excluido en tu perfil.")
        if profile.diet in ["Vegetariano", "Vegano", "Pescetariano"] and any(
            contains(line, t) for t in ["pollo", "res", "cerdo", "carne"]
        ):
            alerts.append("La descripción no coincide con tu preferencia alimentaria.")
        if profile.diet == "Vegano" and any(
            contains(line, t) for t in ["huevo", "queso", "leche", "pescado"]
        ):
            alerts.append("La descripción contiene un alimento de origen animal.")
        advice = "Pregunta por el tamaño de la porción y los acompañamientos; pide salsas aparte si el establecimiento lo permite. No se presupone que esa modificación esté disponible."
        if alerts:
            advice = "Consulta una alternativa que no incluya tus restricciones; retirar un ingrediente del plato servido no permite descartar contaminación cruzada."
        status = (
            "desconocido"
            if price is None or budget is None
            else "dentro"
            if price <= budget
            else "fuera"
        )
        dishes.append(
            Dish(
                name=name,
                supplied_text=line[:600],
                price=price,
                budget_status=status,
                cautions=alerts,
                suggestion=advice,
            )
        )
    facts = [
        f"Preferencia: {profile.diet}. Objetivo registrado: {profile.goal}.",
        f"Alergias: {', '.join(sorted(allergies)) or 'ninguna declarada'}.",
        "Los precios y las descripciones provienen de tu mensaje; no se verificó disponibilidad ni se consultaron restaurantes en vivo.",
    ]
    if budget is not None:
        facts.append(
            f"Presupuesto indicado para esta salida: S/ {budget:.2f}. Verifica bebida, extras y cargos antes de pedir."
        )
    else:
        facts.append(
            "No se indicó presupuesto para esta salida; no se usa automáticamente el presupuesto semanal."
        )
    if dishes:
        usable = [d for d in dishes if d.budget_status == "dentro" and not d.cautions]
        summary = (
            "Comparé los platos que compartiste con tu presupuesto y restricciones. Ninguna opción se considera segura por la carta solamente."
            if allergies
            else "Comparé la información de tu carta; las cantidades e ingredientes no descritos siguen siendo desconocidos."
        )
        if usable:
            summary += " Por precio declarado, puedes revisar primero " + usable[0].name + "."
    else:
        summary = "Pega los platos y precios de la carta, uno por línea después de «Carta:». También puedes describir un plato. No tengo una integración de restaurantes en vivo para inventar opciones o precios."
    return result(
        Insight(
            kind="dining",
            title="Comer fuera",
            as_of=datetime.now(ZoneInfo("America/Lima")).date().isoformat(),
            summary=summary,
            dishes=dishes,
            facts=facts,
        ),
        [FARE] if allergies else [],
    )


def handle(db, user, profile, question, previous=()):
    q = normalize(question)
    if re.search(r"comer fuera|restaurante|carta\s*:|menu del restaurante|comida fuera", q):
        return dining(question, profile)
    if re.search(r"(?:cambia|ajusta|pon|establece).*(?:meta|objetivo).*(?:kcal|calorias)", q):
        value = re.search(r"(\d{3,4})\s*(?:kcal|calorias)", q)
        if not value:
            return result(
                Insight(
                    kind="goal",
                    title="Confirmar objetivo",
                    as_of=date.today().isoformat(),
                    summary="¿Qué valor de calorías quieres registrar? No calcularé una meta clínica automáticamente.",
                )
            )
        target = int(value.group(1))
        if profile.onboarding.age is None or profile.health:
            return result(
                Insight(
                    kind="goal",
                    title="Objetivo individual",
                    as_of=date.today().isoformat(),
                    summary="No cambiaré una meta calórica sin conocer la edad ni cuando hay condiciones de salud que requieren valoración. Revisa el objetivo con tu nutricionista y completa el perfil.",
                )
            )
        if not 1200 <= target <= 6000:
            return result(
                Insight(
                    kind="goal",
                    title="Objetivo sin modificar",
                    as_of=date.today().isoformat(),
                    summary="Ese valor está fuera del rango admitido por la aplicación. No se modificó el objetivo; consulta una meta individual con tu nutricionista.",
                )
            )
        return result(
            Insight(
                kind="goal",
                title="Cambio pendiente",
                as_of=date.today().isoformat(),
                summary="Revisa el cambio solicitado. Solo se guardará si pulsas Confirmar.",
                action=GoalAction(old_value=profile.settings.calorie_target, new_value=target),
            ),
            private={
                "profile_hash": profile_hash(profile),
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    if re.search(
        r"mi progreso|mis tendencias|como voy|evoluci[oó]n|interpreta.*(?:peso|registro)|analiza.*(?:peso|registro)|tendencia.*(?:peso|comida)",
        q,
    ):
        return progress(db, user, profile)
    return None


class Decision(Strict):
    decision: Literal["confirm", "cancel"]


@router.post("/{id}/decision")
def decide(id: str, data: Decision, user=Depends(current_user), db=Depends(get_db)):
    user = lock_user(db, user)
    row = db.scalar(
        select(Entry)
        .where(Entry.id == id, Entry.user_id == user.id, Entry.kind == "coach_insight")
        .with_for_update()
    )
    if not row:
        raise HTTPException(404, "No se encontró esa acción.")
    msg = db.get(Message, row.data["message_id"])
    if not msg:
        raise HTTPException(404, "La conversación ya no está disponible.")
    owned(db, user, msg.conversation_id)
    doc = dict(row.data)
    view = Insight.model_validate(doc["view"])
    action = view.action
    if not action:
        raise HTTPException(422, "Esta respuesta no contiene un cambio pendiente.")
    if action.status != "pending":
        raise HTTPException(409, "Esta acción ya fue confirmada o cancelada.")
    if data.decision == "cancel":
        action.status = "cancelled"
    else:
        p = profile_for(db, user)
        history = list(
            db.scalars(
                select(Message)
                .where(Message.user_id == user.id, Message.conversation_id == msg.conversation_id)
                .order_by(Message.created_at.desc())
                .limit(20)
            )
        )
        if clinical_guard(msg.question, p, history) or p.health or p.onboarding.age is None:
            raise HTTPException(422, "Este cambio necesita evaluación individual; no se guardó.")
        if datetime.now(timezone.utc) - datetime.fromisoformat(
            doc["private"]["created_at"]
        ) > timedelta(hours=24):
            raise HTTPException(409, "La propuesta caducó. Solicita una nueva.")
        if profile_hash(p) != doc["private"]["profile_hash"]:
            raise HTTPException(
                409, "Tu perfil cambió. Solicita una nueva propuesta antes de confirmar."
            )
        p.settings.calorie_target = action.new_value
        target = db.get(Profile, user.id)
        target.data = p.model_dump(mode="json")
        action.status = "confirmed"
    doc["view"] = view.model_dump(mode="json")
    row.data = doc
    db.commit()
    return {"id": row.id, **view.model_dump(mode="json")}
