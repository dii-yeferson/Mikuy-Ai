"""Respuestas locales acotadas: contestar la intención o pedir el dato que falta.

No se presentan como IA. Las citas se asignan al construir la respuesta, sin
rellenar con fichas que no se usaron. NVIDIA puede resolver consultas más abiertas.
"""

import re

from fastapi import HTTPException

from .coach_rag import source_link
from .knowledge import CARDS, cite
from .safety import ALLERGEN_ALIASES, contains, validate_answer
from .schemas import normalize

DISCLAIMER = "Orientación general; no reemplaza una evaluación nutricional individual."
BY_ID = {card["id"]: card for card in CARDS}


def has(text, *terms):
    return any(contains(text, term) for term in terms)


def contextual_question(question, previous):
    """Resolver solo seguimientos explícitos y breves; nunca arrastrar otro tema."""
    q = normalize(question).strip(" ¿?¡!. ")
    if previous and re.fullmatch(
        r"(?:y )?(?:por que|como lo preparo|con que lo acompano|cuanto me sirvo|que cantidad|cuantas veces)(?: entonces)?",
        q,
    ):
        return previous[-1].question + "\nSeguimiento: " + question
    return question


def local_reply(question, profile, plan_names):
    q = normalize(question)
    sources = []

    def ref(card_id):
        card = BY_ID[card_id]
        if not any(s["id"] == card_id for s in sources):
            sources.append(cite(card))
        return f"[{next(i for i, s in enumerate(sources, 1) if s['id'] == card_id)}]"

    if q.strip(" ¿?¡!. ") in {"hola", "buenas", "buenos dias", "gracias", "muchas gracias"}:
        return (
            "¡Hola! Puedo ayudarte a elegir una comida, ajustar una preparación u organizar tus compras. ¿Qué tienes en mente?",
            [],
        )

    # Las restricciones explícitas tienen prioridad sobre cualquier sugerencia local.
    for allergy in profile.allergies:
        if has(q, *ALLERGEN_ALIASES.get(allergy, [allergy])):
            return (
                f"Tienes registrada alergia a {allergy}. Evita ese alimento y revisa los ingredientes y la posible contaminación cruzada. ¿Qué alternativa quieres preparar?",
                [],
            )
    if any(contains(q, item) for item in profile.excluded):
        return (
            "Ese alimento figura entre tus exclusiones. ¿Quieres buscar una alternativa que respete tus preferencias?",
            [],
        )
    if profile.diet in {"Vegetariano", "Vegano", "Pescetariano"} and has(
        q, "pollo", "carne", "cerdo"
    ):
        return (
            f"Esa preparación no coincide con tu preferencia {profile.diet.lower()}. ¿Buscas una alternativa compatible o preguntas para otra persona?",
            [],
        )

    fried = has(
        q,
        "frito",
        "frita",
        "fritos",
        "fritas",
        "fritura",
        "frituras",
        "broaster",
        "apanado",
        "empanizado",
        "freir",
    )
    portion = has(q, "cuanto", "cantidad", "porcion", "porciones", "gramos", "cuantas veces")
    if has(q, "calorias", "kcal"):
        return (
            "Para estimar las calorías necesito la cantidad y cómo se preparó: ingredientes, aceite y acompañamientos. ¿Qué porción vas a comer? Si es un plato de tu menú de Mikuy, abre su ficha para ver la estimación por porción.",
            [],
        )
    if fried:
        food = "el pollo frito" if "pollo" in q or "broaster" in q else "esa fritura"
        if portion:
            text = f"No puedo fijar una cantidad ni una frecuencia de {food} para ti con estos datos. Como orientación, conviene limitar las frituras y elegir una preparación con menos grasa. {ref('frituras')}\n¿Qué tamaño tiene la porción y con qué la acompañarías?"
        else:
            text = f"Sobre {food}: te recomendaría elegir una preparación sin fritura. Puedes cocinarlo al vapor o hervido; así reduces la grasa añadida. {ref('frituras')}"
            if any(
                term in q for term in ("toda la semana", "todos los dias", "diario", "cada dia")
            ):
                text = f"No te recomendaría comer {food} todos los días. Conviene limitar las frituras y variar la preparación; cocinar al vapor o hervir reduce la grasa añadida. {ref('frituras')}"
            if has(q, "diabetes", "prediabetes") or set(profile.health) & {
                "diabetes",
                "prediabetes",
            }:
                text += f"\nPara acompañarlo, usa como guía medio plato de verduras sin almidón, un cuarto de proteína y un cuarto de alimentos con carbohidratos. La porción individual depende de tu plan de alimentación. {ref('plato')}"
            text += "\n¿Lo prepararás en casa o lo vas a comprar?"
    elif has(q, "jugo", "gaseosa", "refresco", "chicha", "bebida", "bebidas"):
        text = f"Para beber, elige agua en lugar de una bebida con azúcar añadida. Si es jugo de fruta, incluso sin azúcar añadida contiene azúcares libres; es preferible la fruta entera. {ref('azucares-libres')}\n¿La bebida que tienes lleva azúcar añadida?"
    elif has(q, "mango", "platano", "papaya", "uva", "fruta", "frutas", "manzana"):
        fruit = next(
            (f for f in ("mango", "papaya", "manzana", "platano", "uva") if contains(q, f)), "fruta"
        )
        fruit = {"platano": "plátano"}.get(fruit, fruit)
        text = f"Sí, puedes incluir {fruit} como fruta entera; tener diabetes no obliga a eliminar toda la fruta. Cuenta sus carbohidratos dentro de tu comida y ajusta la porción a tu plan. {ref('fruta')}\n¿La comerás entera o en jugo, y qué cantidad pensabas servirte?"
    elif has(q, "arroz", "porcion", "porciones", "carbohidratos", "plato"):
        text = f"Como guía para servir arroz u otro alimento con carbohidratos, reserva un cuarto del plato; completa con un cuarto de proteína y medio plato de verduras sin almidón. {ref('plato')}\nNo equivale a una cantidad fija en gramos para todos. ¿Qué más llevará tu plato?"
    elif has(q, "sal", "sodio", "sillao"):
        age = profile.onboarding.age
        if age is not None and age < 18:
            return (
                "La cantidad de sal apropiada en menores depende de la edad y las necesidades de crecimiento. No voy a asignarte el límite de un adulto; puedes revisar la porción con tu profesional de salud. ¿Preguntas por un producto o por la sal al cocinar?",
                [],
            )
        text = f"Si preguntas por el total diario: en adultos la referencia es menos de 5 g de sal, contando también la de los alimentos y condimentos, no solo la que agregas. {ref('sal-limite')}\nPara cocinar, reduce la sal añadida y revisa el sodio de salsas y productos envasados. {ref('sal-fuentes')}"
    elif any(term in q for term in ("bajar de peso", "perder peso", "adelgazar", "pasar hambre")):
        if profile.onboarding.age is not None and profile.onboarding.age < 18:
            return (
                "Durante el crecimiento no voy a indicarte una dieta para adelgazar. Podemos organizar comidas variadas; para evaluar el peso y tus necesidades, conviene hablar con un profesional de salud. ¿Qué comida te cuesta organizar?",
                [],
            )
        text = f"Para empezar a cuidar tu peso, organiza comidas que incluyan verduras, menestras y granos integrales, y reduce las bebidas azucaradas y las frituras. {ref('obesidad-habitos')}\nNo puedo prometer que una dieta concreta te quite el hambre ni fijar un déficit sin evaluarte. ¿En qué momento del día te da más hambre y qué sueles comer entonces?"
    elif has(q, "compras", "comprar", "presupuesto", "ahorrar", "barato", "organiza"):
        text = "Para organizar tus compras, parte de tu menú semanal y revisa qué ingredientes ya tienes. En la lista de compras de Mikuy puedes ver las cantidades reunidas y marcar lo comprado."
        if plan_names:
            text += "\nTu último menú guardado incluye: " + ", ".join(plan_names[:3]) + "."
        else:
            text += " Todavía no tienes un menú guardado; puedes crearlo desde Plan."
        text += "\n¿Quieres ajustar el presupuesto o decidir qué comprar primero?"
    elif has(q, "menu", "cenar", "almorzar", "desayunar", "cocinar", "preparar"):
        if plan_names:
            text = (
                "En tu último menú guardado aparecen: "
                + ", ".join(plan_names[:3])
                + ". ¿Para qué comida y día buscas una opción?"
            )
        else:
            text = "Para proponerte algo concreto, dime qué ingredientes tienes y si buscas desayuno, almuerzo o cena. También puedes generar tu menú desde Plan."
    else:
        # No inventar una contestación a partir de coincidencias débiles.
        text = "Necesito concretar tu consulta para darte una respuesta útil. ¿Sobre qué alimento, preparación o parte de tu menú quieres hablar? Si buscas una cantidad, dime también la porción."

    try:
        validate_answer(text, profile)
    except HTTPException:
        return (
            "Para respetar tus alergias, necesito revisar los ingredientes de esa preparación. ¿Qué contiene y qué alternativa te gustaría usar?",
            [],
        )
    return text, sources


def checked_citations(result, cards):
    """Validar IDs y números y renumerar al filtrar fuentes usadas."""
    numbers = [int(n) for n in re.findall(r"\[(\d+)\]", result.answer)]
    if len(result.sources) != len(set(result.sources)):
        raise ValueError("Fuentes duplicadas")
    ids = {c["id"] for c in cards}
    if not set(result.sources) <= ids:
        raise ValueError("Fuente no entregada al modelo")
    if not numbers and result.sources:
        # Algunos modelos devuelven los IDs correctos sin marcadores inline.
        # Adjuntar referencias a la respuesta completa, sin inventar su procedencia.
        selected = [c for c in cards if c["id"] in result.sources]
        refs = " ".join(f"[{i}]" for i in range(1, len(selected) + 1))
        return result.answer.rstrip() + " " + refs, [source_link(c) for c in selected]
    if any(n < 1 or n > len(cards) for n in numbers):
        raise ValueError("Cita fuera de la evidencia entregada")
    used = {cards[n - 1]["id"] for n in numbers}
    if used != set(result.sources):
        raise ValueError("Las citas no corresponden a los IDs declarados")
    order = sorted(set(numbers))
    mapping = {old: new for new, old in enumerate(order, 1)}
    answer = re.sub(r"\[(\d+)\]", lambda m: f"[{mapping[int(m[1])]}]", result.answer)
    return answer, [source_link(cards[n - 1]) for n in order]
