import re

from fastapi import HTTPException

from .schemas import normalize

# Decisiones que solo puede tomar un profesional: el coach no las responde.
MEDICATION_TERMS = [
    "dosis",
    "insulina",
    "metformina",
    "glibenclamida",
    "enalapril",
    "losartan",
    "amlodipino",
    "medicamento",
    "medicamentos",
    "pastilla",
    "pastillas",
    "suspender tratamiento",
    "dejar el tratamiento",
]
EMERGENCY_TERMS = [
    "dolor de pecho",
    "desmayo",
    "me desmaye",
    "convulsion",
    "no puedo respirar",
    "perdida de conciencia",
    "vision borrosa repentina",
    "glucosa de 300",
    "glucosa de 400",
    "presion de 180",
]
SENSITIVE_TERMS = ["embarazo", "embarazada", "renal", "dialisis", "anorexia", "bulimia", "purgar"]
ALLERGEN_ALIASES = {
    "leche": ["leche", "lacteo", "lacteos", "queso", "yogur", "mantequilla"],
    "huevo": ["huevo", "huevos"],
    "pescado": ["pescado", "atun", "bonito", "salmon", "jurel", "caballa", "merluza"],
    "mariscos": ["mariscos", "camaron", "camarones", "langostinos"],
    "mani": ["mani", "cacahuete", "cacahuates"],
    "frutos secos": ["almendra", "almendras", "nuez", "nueces", "avellana", "avellanas"],
    "soya": ["soya", "soja", "tofu", "sillao"],
    "gluten": ["gluten", "trigo", "pan", "avena", "cebada", "centeno", "fideo"],
    "sesamo": ["sesamo", "ajonjoli"],
}


def contains(text, term):
    return bool(re.search(r"(?<!\w)" + re.escape(normalize(term)) + r"(?!\w)", normalize(text)))


def check_question(text):
    """Return a safe redirect message when the question must not be answered by the coach."""
    if any(contains(text, t) for t in EMERGENCY_TERMS):
        return (
            "Lo que describes puede ser una urgencia. Acude de inmediato al centro de salud más cercano "
            "o llama a tu servicio de emergencias (SAMU 106 en Perú). Mikuy no puede evaluar síntomas."
        )
    medication = any(contains(text, t) for t in MEDICATION_TERMS)
    change = any(
        contains(text, t)
        for t in [
            "dosis",
            "cuanta",
            "cuanto",
            "me pongo",
            "suspender",
            "dejar",
            "aumentar",
            "reducir",
            "cambiar",
            "doblar",
        ]
    )
    if medication and change:
        return (
            "Las dosis y cambios de medicamentos (incluida la insulina) solo los indica tu médico. "
            "Puedo ayudarte con qué comer, porciones y cómo organizar tu menú."
        )
    if any(contains(text, t) for t in SENSITIVE_TERMS) and any(
        contains(text, t)
        for t in ["dieta exacta", "prescribeme", "tratamiento para mi", "cuanto potasio debo"]
    ):
        return (
            "En embarazo, enfermedad renal o trastornos de la conducta alimentaria la alimentación debe "
            "planificarla un profesional de salud. Consulta con tu médico o nutricionista."
        )
    return None


def validate_answer(text, profile):
    forbidden = []
    for a in profile.allergies:
        forbidden.extend(ALLERGEN_ALIASES.get(a, [a]))
    # Allergens may appear only inside an explicit warning ("evita", "alérgico").
    for sentence in re.split(r"[.!?\n]", text):
        if any(contains(sentence, t) for t in forbidden) and not any(
            contains(sentence, w)
            for w in ["evita", "evitar", "alergia", "alergico", "alergica", "sin"]
        ):
            raise HTTPException(
                502,
                "La respuesta mencionó un alimento al que eres alérgico y se descartó. No se consumió cuota.",
            )
    if any(
        contains(text, t) for t in ["dosis de", "unidades de insulina", "suspende tu medicamento"]
    ):
        raise HTTPException(502, "La respuesta excedió el alcance del coach y se descartó.")
