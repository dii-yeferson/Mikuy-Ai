"""Mikuy AI: entiende lo que pides, actúa sobre tu menú y responde como nutricionista y cocinera.

Con GROQ_API_KEY usa el modelo configurado para entender y redactar; las acciones siempre las
valida y ejecuta el servidor. Sin clave (o si la IA falla) responde un intérprete local, así la
app funciona igual.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import date, timedelta

import httpx

from ..catalog import BY_ID, INGREDIENTS, RECIPES
from ..catalog.prices import CITIES
from ..config import settings
from . import nutrition as nu
from . import plans as plan_service
from . import profiles, shopping
from .planner import DAYS, Planner

log = logging.getLogger("mikuy.ai")

MEALS = ("desayuno", "almuerzo", "cena", "snack")
DIETS = ("omnivoro", "vegetariano", "vegano", "pescetariano", "sin-gluten")
ALLERGY_WORDS = {"mani": "N", "nueces": "N", "frutos secos": "N", "gluten": "G", "trigo": "G", "lactosa": "D",
                 "leche": "D", "huevo": "E", "mariscos": "C", "camaron": "C", "pescado": "F", "soya": "S"}

SYSTEM = """Eres Mikuy AI, la asistente de la app Mikuy: nutricionista y cocinera peruana.
Hablas en español peruano, cálido, claro y breve (máximo 120 palabras salvo que pidan una receta).
Actúas con criterio profesional: metas calculadas, porciones, sodio, proteína, alergias y presupuesto.
No te disculpes por ser una IA ni mandes a la persona a otro profesional salvo urgencia médica real.
Puedes CAMBIAR el menú y el perfil usando acciones. Solo usa recipe_id que aparezcan en "recetas_disponibles".
Días válidos: lunes, martes, miércoles, jueves, viernes, sábado, domingo. Comidas: desayuno, almuerzo, cena, snack.
Responde SOLO un objeto JSON: {"reply": "texto", "actions": [ ... ]}
Acciones posibles:
- {"type":"swap_meal","day":"martes","meal":"almuerzo","recipe_id":"opcional","query":"opcional: pollo / más barato / vegetariano"}
- {"type":"regenerate_plan"}
- {"type":"make_cheaper","target":opcional número de soles por semana}
- {"type":"set_profile","weekly_budget":n,"people":n,"city":"lima","diet":"vegetariano","max_minutes":n,"add_excluded":["id_ingrediente"],"add_allergies":["N"]}
- {"type":"show_recipe","recipe_id":"id"}
- {"type":"show_shopping"}
Si piden un cambio, hazlo con una acción (no preguntes de más). Si solo conversan, actions = []."""


def norm(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def find_day(text: str) -> str | None:
    t = norm(text)
    if "pasado manana" in t:
        return DAYS[(date.today().weekday() + 2) % 7]
    if "manana" in t and not re.search(r"\b(en|por|de) la manana\b", t):
        return DAYS[(date.today().weekday() + 1) % 7]
    if re.search(r"\bhoy\b", t):
        return DAYS[date.today().weekday()]
    for d in DAYS:
        if norm(d) in t:
            return d
    return None


def find_meal(text: str) -> str | None:
    t = norm(text)
    for m in MEALS:
        if m in t:
            return m
    if "comida" in t or "almorzar" in t:
        return "almuerzo"
    if "lonche" in t or "merienda" in t or "postre" in t:
        return "snack"
    if "cenar" in t or "noche" in t:
        return "cena"
    return None


def search_recipes(text: str, limit: int = 12) -> list:
    t = norm(text)
    words = [w for w in re.findall(r"[a-z]{4,}", t) if w not in {"quiero", "cambia", "cambiar", "receta", "algo", "para", "como", "hago", "preparo", "menu", "dame"}]
    scored = []
    for r in RECIPES:
        hay = norm(r.name + " " + " ".join(r.tags) + " " + " ".join(i for i, _ in r.parts))
        score = sum(2 if w in norm(r.name) else 1 for w in words if w in hay)
        if score:
            scored.append((score, r))
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored[:limit]]


def find_ingredients(text: str) -> list[str]:
    t = norm(text)
    found = []
    for ing in INGREDIENTS.values():
        base = norm(ing.name.split(" (")[0].split(" / ")[0])
        names = {base, norm(ing.id.replace("-", " "))}
        first = base.split()[0]
        if len(first) >= 4 and first not in {"carne", "pasta", "harina", "aceite", "queso", "leche", "fideo", "papa", "pan"}:
            names.add(first)
        if any(len(n) > 2 and re.search(r"\b" + re.escape(n) + r"s?\b", t) for n in names):
            found.append(ing.id)
    return found


# ---------------------------------------------------------------------------------------------
# Acciones (siempre validadas en el servidor)
# ---------------------------------------------------------------------------------------------


class Ctx:
    def __init__(self, db, user, profile):
        self.db, self.user, self.profile = db, user, profile
        self.cards: list[dict] = []
        self.notes: list[str] = []
        self.plan_changed = False

    @property
    def plan(self):
        return plan_service.current(self.db, self.user.id)


def _ensure_plan(ctx: Ctx):
    plan = ctx.plan
    if not plan:
        plan = plan_service.generate(ctx.db, ctx.user.id, ctx.profile, count_usage=False)
        ctx.plan_changed = True
        ctx.notes.append("Creé tu menú de esta semana.")
    return plan


def apply(ctx: Ctx, action: dict) -> None:
    kind = action.get("type")
    city = ctx.profile.get("city", "lima")
    if kind == "swap_meal":
        plan = _ensure_plan(ctx)
        day = action.get("day") or DAYS[date.today().weekday()]
        day = next((d for d in DAYS if norm(d) == norm(day)), None) or DAYS[date.today().weekday()]
        meal = action.get("meal") if action.get("meal") in MEALS else "almuerzo"
        rid = action.get("recipe_id") if action.get("recipe_id") in BY_ID else None
        if rid and BY_ID[rid].meal != meal:
            meal = BY_ID[rid].meal
        res = plan_service.swap(ctx.db, plan, ctx.profile, day, meal, rid, action.get("query", ""))
        ctx.plan_changed = True
        ctx.cards.append({"type": "swap", "day": day, "meal": meal,
                          "from": nu.recipe_summary(BY_ID[res["from"]], city),
                          "to": nu.recipe_summary(BY_ID[res["to"]], city)})
    elif kind == "regenerate_plan":
        plan_service.generate(ctx.db, ctx.user.id, ctx.profile)
        ctx.plan_changed = True
        ctx.cards.append({"type": "plan"})
    elif kind == "make_cheaper":
        plan = _ensure_plan(ctx)
        p = Planner(ctx.profile)
        before = p.plan_cost(plan.data)
        target = float(action.get("target") or 0) or before * 0.85
        p.budget = target
        data = {**plan.data, "days": [dict(d, meals=[dict(m) for m in d["meals"]]) for d in plan.data["days"]]}
        p.fit_budget(data)
        plan_service._save(plan, data)
        ctx.db.flush()
        after = p.plan_cost(data)
        ctx.plan_changed = True
        ctx.cards.append({"type": "savings", "before": round(before, 2), "after": round(after, 2)})
    elif kind == "set_profile":
        changes = {}
        if isinstance(action.get("weekly_budget"), (int, float)) and 0 <= action["weekly_budget"] <= 5000:
            changes["weekly_budget"] = float(action["weekly_budget"])
        if isinstance(action.get("people"), int) and 1 <= action["people"] <= 12:
            from . import premium

            premium.check_people(ctx.db, ctx.user.id, action["people"])
            changes["people"] = action["people"]
        if action.get("city") in CITIES:
            changes["city"] = action["city"]
        if action.get("diet") in DIETS:
            changes["diet"] = action["diet"]
        if isinstance(action.get("max_minutes"), int) and 0 <= action["max_minutes"] <= 240:
            changes["max_minutes"] = action["max_minutes"]
        excl = [i for i in action.get("add_excluded", []) if i in INGREDIENTS]
        if excl:
            changes["excluded"] = sorted(set(ctx.profile.get("excluded", [])) | set(excl))
        allergies = [a for a in action.get("add_allergies", []) if a in "MFCDEGNS"]
        if allergies:
            changes["allergies"] = sorted(set(ctx.profile.get("allergies", [])) | set(allergies))
        if changes:
            ctx.profile = profiles.save(ctx.db, ctx.user.id, changes)
            ctx.cards.append({"type": "profile", "changes": changes})
            if ctx.plan and any(k in changes for k in ("weekly_budget", "people", "diet", "excluded", "allergies", "max_minutes")):
                plan_service.generate(ctx.db, ctx.user.id, ctx.profile, count_usage=False)
                ctx.plan_changed = True
                ctx.notes.append("Actualicé tu menú con estos cambios.")
    elif kind == "show_recipe":
        rid = action.get("recipe_id")
        if rid in BY_ID:
            ctx.cards.append({"type": "recipe", "recipe": nu.recipe_summary(BY_ID[rid], city)})
    elif kind == "show_shopping":
        plan = ctx.plan
        if plan:
            sh = shopping.build(plan.data, ctx.profile, plan.shopping)
            ctx.cards.append({"type": "shopping", "total": sh["total_buy"], "count": sh["count"], "pending": sh["pending"]})


# ---------------------------------------------------------------------------------------------
# Intérprete local (sin IA externa)
# ---------------------------------------------------------------------------------------------


def local_understand(text: str, ctx: Ctx) -> tuple[str, list[dict]]:
    t = norm(text)
    p = ctx.profile
    targets = nu.daily_targets(p)
    actions: list[dict] = []
    money = re.search(r"(?:s/\.?\s*|\b)(\d{2,4})(?:\s*(?:soles|sol|s/))?", t)
    people = re.search(r"\b(\d{1,2})\s*(?:personas|personitas|integrantes|somos)", t) or re.search(r"somos\s*(\d{1,2})", t)

    if any(w in t for w in ("presupuesto", "soles", "s/")) and money and ("semana" in t or "presupuesto" in t):
        amount = int(money.group(1))
        actions.append({"type": "set_profile", "weekly_budget": amount})
        return f"Listo, tu presupuesto semanal ahora es S/ {amount}. Ajusté el menú para que entre en ese monto.", actions
    if people:
        n = int(people.group(1))
        actions.append({"type": "set_profile", "people": n})
        return f"Perfecto, cocino para {n}. Recalculé porciones, costos y la lista de compras.", actions
    for diet in ("vegano", "vegetariano", "pescetariano"):
        if diet in t and any(w in t for w in ("soy", "quiero", "dieta", "volver", "hazme", "ahora", "menu")):
            actions.append({"type": "set_profile", "diet": diet})
            return f"Hecho: tu menú ahora es {diet}, con proteína de menestras, huevo, lácteos o soya según corresponda.", actions
    city = next((k for k, v in CITIES.items() if norm(v[0]) in t), None)
    if city and any(w in t for w in ("vivo", "estoy", "ciudad", "precios", "compro")):
        actions.append({"type": "set_profile", "city": city})
        return f"Ahora tus precios son aproximados para {CITIES[city][0]}.", actions
    allergy = next((v for k, v in ALLERGY_WORDS.items() if k in t), None)
    if allergy and any(w in t for w in ("alergi", "intoleran")):
        actions.append({"type": "set_profile", "add_allergies": [allergy]})
        return "Anotado. Saqué de tu menú todo lo que pueda tener ese alérgeno.", actions
    if re.search(r"\b(no (me gusta|como|quiero)|sin|odio|quita)\b", t) and not find_meal(t):
        ings = find_ingredients(t)
        if ings:
            actions.append({"type": "set_profile", "add_excluded": ings})
            names = ", ".join(INGREDIENTS[i].name.lower() for i in ings)
            return f"Entendido, no volverás a ver {names} en tu menú.", actions

    if any(w in t for w in ("nuevo menu", "otro menu", "regenera", "menu nuevo", "arma mi menu", "crea mi menu", "hazme un menu")):
        actions.append({"type": "regenerate_plan"})
        return "Te preparé un menú nuevo para la semana, cuidando tu meta y tu presupuesto.", actions

    wants_swap = re.search(r"\b(cambia|cambiar|cambiame|reemplaza|otro|otra|no quiero|en vez)\b", t)
    day, meal = find_day(t), find_meal(t)
    if wants_swap and (day or meal):
        query = ""
        m = re.search(r"\b(?:por|con|algo)\b(.+)$", t)
        if m:
            query = m.group(1)
        if any(w in t for w in ("barat", "econom", "ahorr")):
            query = (query + " barato").strip()
        named = search_recipes(query) if query else []
        rid = next((r.id for r in named if r.meal == (meal or r.meal)), None)
        actions.append({"type": "swap_meal", "day": day or DAYS[date.today().weekday()], "meal": meal or "almuerzo", "recipe_id": rid, "query": query})
        return "Listo, hice el cambio. Mira la tarjeta: puedes ver la receta o volver a cambiarla.", actions

    if any(w in t for w in ("barat", "ahorr", "econom", "gastar menos", "muy caro")):
        actions.append({"type": "make_cheaper"})
        return "Cambié los platos más caros por opciones igual de nutritivas y más económicas.", actions

    if any(w in t for w in ("lista", "compras", "mercado", "comprar")):
        actions.append({"type": "show_shopping"})
        return "Aquí está tu lista de compras con precios aproximados de tu ciudad.", actions

    if any(w in t for w in ("receta", "como hago", "como preparo", "como se hace", "preparar")):
        found = search_recipes(t, 3)
        if found:
            actions += [{"type": "show_recipe", "recipe_id": r.id} for r in found]
            return f"Te dejo {'esta receta' if len(found) == 1 else 'estas recetas'}. Toca para ver ingredientes y pasos.", actions

    if any(w in t for w in ("caloria", "proteina", "meta", "cuanto debo", "macros", "imc")):
        summary = ""
        if ctx.plan:
            from .planner import summarize

            s = summarize(ctx.plan.data, p)
            summary = f" Tu menú promedia {round(s['avg']['kcal'])} kcal y {round(s['avg']['protein'])} g de proteína al día."
        return (
            f"Tu meta diaria es de unas {targets['kcal']} kcal, con {targets['protein']} g de proteína, "
            f"{targets['carbs']} g de carbohidratos y {targets['fat']} g de grasa. Tu IMC es {targets['bmi']}.{summary} "
            "La calculé con la ecuación de Mifflin-St Jeor y tu nivel de actividad."
        ), actions

    found = search_recipes(t, 2)
    if found:
        actions += [{"type": "show_recipe", "recipe_id": r.id} for r in found]
        return "Encontré esto en el recetario. Si quieres, dime para qué día lo pongo en tu menú.", actions
    return (
        "Puedo armar tu menú, cambiar cualquier comida (\"cambia el almuerzo del martes por algo con pollo\"), "
        "ajustarlo a tu presupuesto, decirte tus calorías y preparar tu lista de compras. ¿Qué hacemos?"
    ), actions


# ---------------------------------------------------------------------------------------------
# IA externa (Groq)
# ---------------------------------------------------------------------------------------------


def ai_configured() -> bool:
    return bool(settings().groq_api_key)


def _context(ctx: Ctx, text: str, history: list[dict]) -> dict:
    p = ctx.profile
    plan = ctx.plan
    city = p.get("city", "lima")
    related = search_recipes(text, 15)
    if plan:
        meal = find_meal(text)
        pl = Planner(p)
        for m in [meal] if meal else ["almuerzo", "cena"]:
            related += [r for r in pl.alternatives(m, "", "", 6) if r not in related]
    return {
        "hoy": f"{DAYS[date.today().weekday()]} {date.today().isoformat()}",
        "perfil": {k: p.get(k) for k in ("name", "goal", "sex", "age", "weight_kg", "height_cm", "activity", "diet", "allergies", "excluded", "conditions", "city", "people", "weekly_budget", "max_minutes")},
        "metas_diarias": nu.daily_targets(p),
        "menu_semana": plan_service.compact(plan, p),
        "recetas_disponibles": [
            {"id": r.id, "nombre": r.name, "comida": r.meal, "costo_porcion": round(nu.recipe_cost(r, city), 2), "kcal": nu.recipe_nutrition(r)["kcal"]}
            for r in related[:24] if nu.allowed(r, p)
        ],
        "historial": history[-8:],
        "mensaje": text,
    }


def ai_understand(text: str, ctx: Ctx, history: list[dict]) -> tuple[str, list[dict]]:
    cfg = settings()
    body = {
        "model": cfg.groq_model,
        "temperature": 0.4,
        "max_tokens": 900,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(_context(ctx, text, history), ensure_ascii=False)},
        ],
    }
    with httpx.Client(base_url=cfg.groq_base_url, timeout=httpx.Timeout(30, connect=8),
                      headers={"Authorization": f"Bearer {cfg.groq_api_key}"}) as client:
        res = client.post("/chat/completions", json=body)
        res.raise_for_status()
        content = res.json()["choices"][0]["message"]["content"]
    data = json.loads(content)
    reply = str(data.get("reply", "")).strip()[:2000]
    actions = [a for a in data.get("actions", []) if isinstance(a, dict)][:4]
    if not reply:
        raise ValueError("respuesta vacía")
    return reply, actions


def respond(db, user, profile: dict, text: str, history: list[dict]) -> dict:
    ctx = Ctx(db, user, profile)
    source = "local"
    if ai_configured():
        try:
            reply, actions = ai_understand(text, ctx, history)
            source = "ia"
        except Exception as exc:  # la app sigue funcionando con el intérprete local
            log.warning("IA no disponible, uso el intérprete local: %s", exc)
            reply, actions = local_understand(text, ctx)
    else:
        reply, actions = local_understand(text, ctx)
    errors = []
    for action in actions:
        try:
            apply(ctx, action)
        except Exception as exc:  # una acción inválida no rompe la respuesta
            detail = getattr(exc, "detail", None) or str(exc)
            errors.append(detail)
    if errors:
        reply += "\n\n" + " ".join(f"⚠️ {e}" for e in errors[:2])
    if ctx.notes:
        reply += "\n\n" + " ".join(ctx.notes)
    return {"reply": reply, "cards": ctx.cards, "plan_changed": ctx.plan_changed, "source": source}


def day_from_date(d: str) -> str:
    return DAYS[date.fromisoformat(d).weekday()]


def week_dates() -> list[str]:
    start = date.today() - timedelta(days=date.today().weekday())
    return [(start + timedelta(days=i)).isoformat() for i in range(7)]
