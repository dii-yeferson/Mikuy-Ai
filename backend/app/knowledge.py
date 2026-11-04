"""Base de conocimiento verificable del coach de Mikuy (recuperación + citas).

Cada ficha resume una recomendación de una fuente reconocida (OMS, ADA, NHLBI, MINSA/INS).
El coach solo responde a partir de estas fichas y del plan del usuario, y cita la fuente.
Para ampliar la base, agrega fichas con su fuente y fecha; nunca fichas sin respaldo.
"""

import math
import re
from collections import Counter

from .schemas import normalize

SOURCES = {
    "ada-fruta": dict(
        title="ADA — Fruta y diabetes",
        url="https://diabetes.org/food-nutrition/reading-food-labels/fruit",
    ),
    "cdc-plato": dict(
        title="CDC — Planificación de comidas para la diabetes",
        url="https://www.cdc.gov/diabetes/healthy-eating/diabetes-meal-planning.html",
    ),
    "oms-sodio": dict(
        title="OMS — Reducción de la ingesta de sodio (nota descriptiva)",
        url="https://www.who.int/news-room/fact-sheets/detail/sodium-reduction",
    ),
    "oms-dieta": dict(
        title="OMS — Alimentación sana (nota descriptiva)",
        url="https://www.who.int/news-room/fact-sheets/detail/healthy-diet",
    ),
    "oms-diabetes": dict(
        title="OMS — Diabetes (nota descriptiva)",
        url="https://www.who.int/news-room/fact-sheets/detail/diabetes",
    ),
    "oms-hipertension": dict(
        title="OMS — Hipertensión (nota descriptiva)",
        url="https://www.who.int/news-room/fact-sheets/detail/hypertension",
    ),
    "oms-obesidad": dict(
        title="OMS — Obesidad y sobrepeso (nota descriptiva)",
        url="https://www.who.int/news-room/fact-sheets/detail/obesity-and-overweight",
    ),
    "oms-actividad": dict(
        title="OMS — Actividad física (nota descriptiva)",
        url="https://www.who.int/news-room/fact-sheets/detail/physical-activity",
    ),
    "ada-5": dict(
        title="ADA — Standards of Care in Diabetes 2026, Sección 5: Conductas saludables y nutrición",
        url="https://diabetesjournals.org/care/article/49/Supplement_1/S89/163932/5-Facilitating-Positive-Health-Behaviors-and-Well",
    ),
    "ada-3": dict(
        title="ADA — Standards of Care in Diabetes 2026, Sección 3: Prevención o retraso de la diabetes",
        url="https://diabetesjournals.org/care/article/49/Supplement_1/S50/163924/3-Prevention-or-Delay-of-Diabetes-and-Associated",
    ),
    "ada-sc": dict(
        title="ADA — Standards of Care in Diabetes 2026 (índice general)",
        url="https://professional.diabetes.org/standards-of-care",
    ),
    "nhlbi-dash": dict(
        title="NHLBI (NIH) — Plan de alimentación DASH",
        url="https://www.nhlbi.nih.gov/education/dash-eating-plan",
    ),
    "minsa-guias": dict(
        title="MINSA/INS — Guías Alimentarias para la Población Peruana (2019)",
        url="https://www.gob.pe/institucion/minsa/informes-publicaciones/314037-guias-alimentarias-para-la-poblacion-peruana",
    ),
    "ins-tablas": dict(
        title="INS/CENAN — Tablas Peruanas de Composición de Alimentos (2017)",
        url="https://repositorio.ins.gob.pe/items/7dd870ba-42db-449c-bef2-5d67d881383f",
    ),
    "ig-2021": dict(
        title="Atkinson et al. (2021) — International tables of glycemic index and glycemic load values, Am J Clin Nutr",
        url="https://doi.org/10.1093/ajcn/nqab233",
    ),
}

C = ("diabetes", "prediabetes", "hipertension", "obesidad", "general")

CARDS = [
    dict(
        id="frituras",
        conditions=C,
        title="Alternativas a las frituras",
        text="Conviene limitar las frituras. Para reducir la grasa de la preparación, se puede cocinar al vapor o hervir en lugar de freír y retirar la grasa visible de la carne. Esta orientación no determina una porción individual ni garantiza una respuesta de glucosa.",
        keywords="pollo frito frita fritos fritas fritura broaster apanado empanizado freir",
        source="oms-dieta",
        reviewed="2026-10-24",
    ),
    dict(
        id="sal-limite",
        conditions=("hipertension", "general"),
        title="Límite de sal al día",
        text="La OMS recomienda que los adultos consuman menos de 2 g de sodio al día, equivalente a menos de 5 g de sal (aprox. una cucharadita rasa), sumando la sal de cocina, los condimentos y los productos procesados.",
        keywords="sal sodio cucharadita limite cuanta sal presion",
        source="oms-sodio",
    ),
    dict(
        id="sal-fuentes",
        conditions=("hipertension", "general"),
        title="De dónde viene el sodio",
        text="Gran parte del sodio proviene de productos procesados y condimentos como el sillao (salsa de soya), cubitos, embutidos, snacks y panes, además de la sal que se agrega al cocinar o en la mesa. Leer etiquetas y cocinar en casa ayuda a reducirlo.",
        keywords="sillao cubito embutidos snacks pan procesados etiqueta sodio salsa",
        source="oms-sodio",
    ),
    dict(
        id="sal-sabor",
        conditions=("hipertension",),
        title="Dar sabor sin sal",
        text="Para reducir la sal sin perder sabor se recomienda cocinar con hierbas y especias, ajo, limón, culantro, comino u orégano, y retirar el salero de la mesa. El gusto por lo salado se adapta en pocas semanas cuando se reduce de forma gradual.",
        keywords="sabor sin sal hierbas especias limon ajo culantro comida sosa",
        source="oms-sodio",
    ),
    dict(
        id="dash",
        conditions=("hipertension",),
        title="Plan DASH para la presión arterial",
        text="El plan DASH prioriza verduras, frutas, granos integrales, lácteos bajos en grasa, pescado, aves, menestras y frutos secos, y limita sodio, azúcares y grasas saturadas. En ensayos clínicos redujo la presión arterial, y el efecto fue mayor al combinarlo con menos sodio.",
        keywords="dash presion arterial hipertension dieta frutas verduras lacteos",
        source="nhlbi-dash",
    ),
    dict(
        id="potasio",
        conditions=("hipertension",),
        title="Alimentos ricos en potasio",
        text="El plan DASH incluye alimentos ricos en potasio como plátano, papa, camote, menestras, espinaca y yogur. Las personas con enfermedad renal o que toman ciertos medicamentos deben consultar a su médico antes de aumentar el potasio.",
        keywords="potasio platano papa camote renal riñon",
        source="nhlbi-dash",
    ),
    dict(
        id="hta-habitos",
        conditions=("hipertension",),
        title="Hábitos que ayudan a controlar la presión",
        text="Según la OMS, comer más verduras y frutas, reducir la sal, mantenerse activo, no fumar, limitar el alcohol y mantener un peso saludable ayudan a prevenir y controlar la hipertensión, junto con el tratamiento indicado por el médico.",
        keywords="presion habitos alcohol fumar actividad tratamiento controlar",
        source="oms-hipertension",
    ),
    dict(
        id="plato",
        conditions=("diabetes", "prediabetes", "obesidad"),
        title="Método del plato",
        text="El método del plato, recomendado en el cuidado de la diabetes, propone llenar la mitad del plato con verduras sin almidón, un cuarto con proteína magra y un cuarto con carbohidratos de calidad (menestras, granos integrales, papa o camote), acompañado de agua.",
        keywords="plato porcion cuanto arroz cantidad mitad verduras cuarto proteina carbohidratos",
        source="cdc-plato",
    ),
    dict(
        id="carbos-calidad",
        conditions=("diabetes", "prediabetes"),
        title="Carbohidratos de calidad",
        text="La ADA indica que no existe un porcentaje ideal de carbohidratos para todas las personas con diabetes; recomienda priorizar verduras sin almidón, menestras, frutas enteras y granos integrales, y reducir azúcares añadidos y granos refinados como el pan blanco o el arroz blanco en exceso.",
        keywords="carbohidratos arroz pan harina fideo azucar integral menestras",
        source="ada-5",
    ),
    dict(
        id="fibra",
        conditions=("diabetes", "prediabetes", "general"),
        title="Fibra",
        text="La ADA recomienda que las personas con diabetes consuman al menos 14 g de fibra por cada 1000 kcal, principalmente de verduras, menestras, frutas enteras y granos integrales.",
        keywords="fibra integral menestras avena linaza",
        source="ada-5",
    ),
    dict(
        id="bebidas",
        conditions=("diabetes", "prediabetes", "obesidad", "general"),
        title="Bebidas azucaradas",
        text="La ADA recomienda reemplazar las bebidas azucaradas (gaseosas, refrescos, jugos con azúcar) por agua lo más posible para controlar la glucosa y el peso.",
        keywords="gaseosa refresco jugo bebida agua chicha azucar",
        source="ada-5",
    ),
    dict(
        id="azucares-libres",
        conditions=("general", "diabetes", "obesidad"),
        title="Azúcares libres",
        text="La OMS recomienda limitar los azúcares libres a menos del 10 % de la energía diaria, idealmente menos del 5 %. Incluyen el azúcar añadido y el azúcar presente en jugos de fruta y miel; la fruta entera no cuenta como azúcar libre.",
        keywords="azucar dulce postre miel jugo fruta mango",
        source="oms-dieta",
    ),
    dict(
        id="fruta",
        conditions=("diabetes", "prediabetes", "general"),
        title="La fruta en la diabetes",
        text="Las frutas enteras forman parte de una alimentación saludable para personas con diabetes; conviene comerlas enteras (no en jugo), en porciones moderadas y acompañadas de otras comidas. Así aportan fibra y no se consideran azúcar libre.",
        keywords="fruta mango platano papaya uva puedo comer fruta diabetes",
        source="ada-fruta",
    ),
    dict(
        id="ig",
        conditions=("diabetes", "prediabetes"),
        title="Índice glucémico",
        text="Las menestras, la avena en hojuelas y muchos granos integrales tienen un índice glucémico más bajo que el pan blanco o el arroz blanco. Combinar los carbohidratos con proteína, verduras y fibra ayuda a moderar la subida de glucosa.",
        keywords="indice glucemico subir glucosa azucar en sangre arroz pan quinua avena",
        source="ig-2021",
    ),
    dict(
        id="peso-prediabetes",
        conditions=("prediabetes", "obesidad"),
        title="Bajar un poco de peso sí importa",
        text="En personas con prediabetes y sobrepeso, programas que logran una pérdida de alrededor del 7 % del peso y al menos 150 minutos semanales de actividad física reducen el riesgo de desarrollar diabetes tipo 2.",
        keywords="prediabetes bajar peso riesgo prevenir diabetes",
        source="ada-3",
    ),
    dict(
        id="imc",
        conditions=("obesidad", "general"),
        title="Sobrepeso y obesidad",
        text="En adultos, la OMS define sobrepeso como un índice de masa corporal (IMC) igual o mayor a 25 y obesidad como igual o mayor a 30. El IMC es una referencia poblacional; tu profesional de salud evalúa tu caso con más datos.",
        keywords="imc indice masa corporal sobrepeso obesidad peso altura",
        source="oms-obesidad",
    ),
    dict(
        id="obesidad-habitos",
        conditions=("obesidad",),
        title="Prevenir y manejar el exceso de peso",
        text="La OMS recomienda limitar la energía de grasas y azúcares, aumentar verduras, frutas, menestras y granos integrales, y realizar actividad física regular para prevenir y manejar el sobrepeso.",
        keywords="bajar de peso adelgazar perder peso grasa",
        source="oms-obesidad",
    ),
    dict(
        id="actividad",
        conditions=C,
        title="Actividad física",
        text="La OMS recomienda que los adultos realicen entre 150 y 300 minutos semanales de actividad física moderada (por ejemplo, caminar a paso rápido) o su equivalente, y reducir el tiempo sentado.",
        keywords="ejercicio caminar actividad fisica minutos semana",
        source="oms-actividad",
    ),
    dict(
        id="frutas-verduras",
        conditions=("general",),
        title="Frutas y verduras",
        text="La OMS recomienda consumir al menos 400 g (unas 5 porciones) de frutas y verduras al día, sin contar papa, camote ni yuca.",
        keywords="frutas verduras porciones dia ensalada",
        source="oms-dieta",
    ),
    dict(
        id="grasas",
        conditions=("general", "obesidad", "hipertension"),
        title="Grasas",
        text="La OMS recomienda que las grasas no superen el 30 % de la energía total, que las saturadas sean menos del 10 % y las trans menos del 1 %, prefiriendo aceites vegetales, pescado y frutos secos.",
        keywords="grasa aceite fritura frito manteca saturada",
        source="oms-dieta",
    ),
    dict(
        id="guias-peru",
        conditions=C,
        title="Guías alimentarias del Perú",
        text="Las Guías Alimentarias para la Población Peruana recomiendan priorizar alimentos naturales y preparaciones caseras, consumir a diario verduras y frutas, incluir menestras y pescado, tomar agua y limitar los productos procesados con advertencias (octógonos).",
        keywords="peru guias alimentarias comida casera menestras pescado agua octogonos",
        source="minsa-guias",
    ),
    dict(
        id="octogonos",
        conditions=C,
        title="Octógonos en los empaques",
        text="En el Perú, los productos procesados llevan octógonos de advertencia como 'Alto en sodio', 'Alto en azúcar', 'Alto en grasas saturadas' o 'Contiene grasas trans'. Elegir productos sin octógonos o naturales es una forma práctica de cuidar la salud.",
        keywords="octogono etiqueta empaque procesado galleta alto en",
        source="minsa-guias",
    ),
    dict(
        id="hipoglucemia",
        conditions=("diabetes",),
        title="Hipoglucemia: señales de alerta",
        text="Si usas insulina u otros medicamentos que bajan la glucosa, saltarte comidas puede causar hipoglucemia (temblor, sudor, confusión). La ADA indica tratarla con unos 15 g de carbohidrato de acción rápida y volver a medir a los 15 minutos; sigue el plan que te dio tu médico.",
        keywords="hipoglucemia baja azucar temblor tiembla tiemblo sudor sudo sudando mareo mareada saltar comida",
        source="ada-sc",
    ),
    dict(
        id="composicion",
        conditions=("general",),
        title="De dónde salen los nutrientes de Mikuy",
        text="Los nutrientes que muestra Mikuy son referenciales y se calculan con valores aproximados de las Tablas Peruanas de Composición de Alimentos y USDA; pueden variar según la marca, la cocción y la porción real.",
        keywords="calorias nutrientes de donde tabla composicion exacto",
        source="ins-tablas",
    ),
    dict(
        id="diabetes-def",
        conditions=("diabetes", "prediabetes"),
        title="Diabetes tipo 2",
        text="Según la OMS, la diabetes tipo 2 se puede prevenir o retrasar con una alimentación saludable, actividad física regular, un peso saludable y evitando el tabaco; su tratamiento incluye dieta, actividad física y, cuando el médico lo indica, medicamentos y controles periódicos.",
        keywords="diabetes que es controlar tratamiento prevenir",
        source="oms-diabetes",
    ),
]

_word = re.compile(r"[a-zñ0-9]+")
STOP = set(
    "de la el en y a los las un una que con por para mi me es se lo al del como puedo debo mas o cual cuanto quiero comer recomiendas recomienda tengo hacer ayuda favor".split()
)


def tokens(text):
    return [w for w in _word.findall(normalize(text)) if w not in STOP and len(w) > 2]


_DOCS = [Counter(tokens(c["title"] + " " + c["text"] + " " + c["keywords"] * 2)) for c in CARDS]
_DF = Counter(w for d in _DOCS for w in d)
_N = len(CARDS)


def retrieve(question, conditions=(), k=4):
    q = tokens(question)
    scores = []
    for card, doc in zip(CARDS, _DOCS):
        s = 0.0
        for w in q:
            matches = [
                t
                for t in doc
                if t == w or (len(w) > 4 and (t.startswith(w[:5]) or w.startswith(t[:5])))
            ]
            for t in matches:
                s += doc[t] / (doc[t] + 1.2) * math.log(1 + _N / (1 + _DF[t]))
        if s and set(conditions) & set(card["conditions"]):
            s *= 1.35
        scores.append((s, card))
    top = max((s for s, _ in scores), default=0)
    ranked = [c for s, c in sorted(scores, key=lambda x: -x[0]) if s > 0 and s >= top * 0.45]
    # No rellenar una consulta desconocida con fichas de las enfermedades del perfil.
    return ranked[:k]


def cite(card):
    src = SOURCES[card["source"]]
    return dict(id=card["id"], title=card["title"], source=src["title"], url=src["url"])
