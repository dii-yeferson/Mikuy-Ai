"""Respuestas de la aplicación basadas en registros del dueño, sin inventar cifras por IA."""

import re
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select

from .coach_calculations import fmt
from .coach_pipeline import PipelineResult
from .models import Entry
from .schemas import normalize

GUIDE = {
    "compras": "Abre Compras para ver la compra aproximada, marcar artículos o editar cantidades y precios. El consumo de las recetas y el desembolso de compra se muestran por separado.",
    "menu": "Abre Menú para ver tu semana, consultar recetas y reemplazar platos. En Compras se actualizan los ingredientes de ese menú.",
    "comunidad": "En Comunidad puedes publicar; en Grupos puedes crear una comunidad con nombre y descripción, unirte y conversar. Activa tu perfil público para participar; tus datos de salud siguen privados.",
    "perfil": "En Mi perfil y Ajustes puedes editar tus preferencias y datos. El presupuesto se configura en tu perfil de planificación.",
    "progreso": "En Progreso puedes consultar tus registros. Registra agua, peso y comidas en el diario para mantenerlos actualizados.",
    "coach": "Aquí puedes preguntar por tu menú, presupuesto y compras, o hacer consultas generales. Enter envía, Shift + Enter añade una línea; el micrófono permite dictar si tu navegador lo admite.",
}


def records_reply(db, user, question):
    q = normalize(question)
    personal = bool(re.search(r"mi |mis |he |llevo|registre|registrado|hoy", q))
    if not personal:
        return None
    if re.search(r"debo|deberia|recomienda|conviene|que pasa", q):
        return None
    day = datetime.now(ZoneInfo("America/Lima")).date().isoformat()
    kind = (
        "agua"
        if "agua" in q
        else "peso"
        if re.search(r"mi peso|peso registrad|ultimo peso", q)
        else "comida"
        if re.search(r"calorias.*hoy|hoy.*calorias|comido hoy|comidas.*registr", q)
        else "pasos"
        if "pasos" in q
        else None
    )
    if not kind:
        return None
    query = select(Entry).where(Entry.user_id == user.id, Entry.kind == kind)
    if kind != "peso":
        query = query.where(Entry.data["date"].as_string() == day)
    rows = list(db.scalars(query.order_by(Entry.created_at.desc())))
    if kind == "peso":
        rows = sorted(rows, key=lambda r: r.data.get("date", ""), reverse=True)
        answer = (
            f"Tu último peso registrado es {rows[0].data['value']} kg, del {rows[0].data['date']}. Puedes revisarlo en Progreso."
            if rows
            else "Todavía no tienes registros de peso. Puedes añadir uno en Progreso."
        )
    elif kind == "comida":
        calories = sum(Decimal(str(r.data.get("kcal", 0))) for r in rows)
        answer = f"Hoy ({day}) tienes {len(rows)} comidas registradas en el diario, con {fmt(calories)} kcal declaradas en total. Esto refleja lo registrado, no todo lo que necesariamente has comido."
    else:
        value = sum(Decimal(str(r.data.get("value") or 0)) for r in rows)
        answer = f"Hoy ({day}) tienes registrados {fmt(value)} {'ml de agua' if kind == 'agua' else 'pasos'}. Puedes añadir o corregir registros en el diario."
    return PipelineResult(answer, [], "calculo", {"stage": "app_records"})


def app_reply(question, profile, plan, shopping, user, previous=()):
    q = normalize(question)
    if previous and re.fullmatch(
        r"[¿?¡! .]*(?:y )?(?:cuanto queda|cuanto me queda|y mi gasto|y el total|cuanto gastaria)[¿?¡! .]*",
        q,
    ):
        q = normalize(previous[-1].question) + " " + q
    financial = bool(
        re.search(
            r"presupuesto|gasto|gastaria|gastare|compra.*estimad|precio.*compra|costo.*compra|cuanto.*compra|cuanto.*queda|saldo|cuanto.*menu|costo.*menu",
            q,
        )
    )
    how = bool(re.search(r"como|donde|guiame|ayuda.*app|que puedo hacer", q))
    answer = None
    if financial and not (how and not re.search(r"cuanto|estimad|saldo", q)):
        answer = f"Tu presupuesto semanal registrado es S/ {profile.budget:.2f}."
        if shopping and plan:
            cost = shopping["shopping_cost"]
            difference = round(profile.budget - cost, 2)
            answer += f"\nPara tu menú del {plan.data['start_date']}, la compra aproximada es S/ {cost:.2f}, con tus cantidades y precios guardados. El consumo de las recetas representa S/ {shopping['planned_cost']:.2f}."
            answer += f"\nCon esa compra, {'te quedarían' if difference >= 0 else 'te faltarían'} aproximadamente S/ {abs(difference):.2f}. No es un gasto confirmado; puedes ajustar precios o descontar lo que ya tienes en Compras."
        else:
            answer += " Todavía no tienes un menú guardado para estimar la compra. Genera uno en Menú y podré darte el total."
    elif re.search(r"mi (?:menu|plan)|que (?:me toca|tengo para) comer", q) and not how:
        answer = "Todavía no tienes un menú guardado. Puedes generarlo en Menú."
        if plan:
            answer = (
                f"Tu último menú empieza el {plan.data['start_date']}. Incluye: "
                + "; ".join(dict.fromkeys(m["name"] for m in plan.data["meals"]))
                + ". Puedes ver las porciones y recetas en Menú."
            )
    elif re.search(r"mis (?:alergias|preferencias)|mi objetivo", q):
        answer = f"Tu objetivo registrado es {profile.goal}; preferencia: {profile.diet}. Alergias registradas: {', '.join(profile.allergies) or 'ninguna declarada'}."
    elif re.search(r"mis consultas|cuantas consultas|mi suscripcion", q):
        answer = f"Tu plan actual es {user.tier}. En Cuenta puedes consultar tus límites y el consumo mensual. Las suscripciones de esta beta son simuladas."
    elif how or "mikuy" in q or "aplicacion" in q:
        matches = [
            text
            for name, text in GUIDE.items()
            if name in q or (name == "comunidad" and "grupo" in q)
        ]
        if matches:
            answer = "\n".join(matches)
        elif "mikuy" in q or "aplicacion" in q:
            answer = "Mikuy integra Menú, Compras, Coach, Diario, Progreso y Comunidad. Puedo explicarte dónde encontrar cada función y consultar tu presupuesto o tu última compra guardada. ¿Qué quieres hacer?"
    return (
        PipelineResult(answer, [], "calculo" if financial else "orientacion", {"stage": "app_data"})
        if answer
        else None
    )
