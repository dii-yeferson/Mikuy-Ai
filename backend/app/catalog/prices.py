"""Precios aproximados por ciudad.

El precio base de cada ingrediente es el minorista estimado en mercados de Lima
(noviembre de 2026). Para otras ciudades se aplica un factor general de la ciudad,
un factor por sección (pescado, tubérculos, frutas…) y, en algunos casos, un factor
por ingrediente (trucha en la sierra, plátano en la selva…).

Los factores son estimaciones de Mikuy construidas a partir de reportes de mercados
regionales (ver `sources.py`). Siempre se muestran como "aprox.".
"""

from .ingredients import INGREDIENTS, Ingredient

PRICE_DATE = "2026-11-04"

# id: (nombre, región, factor general, {sección: factor}, {ingrediente: factor})
_COAST_NORTH = {"pescados": 0.88, "frutas": 0.92, "verduras": 0.95}
_COAST_SOUTH = {"pescados": 0.95, "tuberculos": 0.92}
_HIGHLANDS = {
    "pescados": 1.25,
    "tuberculos": 0.78,
    "frutas": 1.12,
    "carnes": 1.08,
    "verduras": 0.95,
}
_HIGHLAND_ITEMS = {
    "trucha": 0.72,
    "quinua": 0.8,
    "kiwicha": 0.8,
    "chuno": 0.75,
    "oca": 0.75,
    "olluco": 0.8,
    "papa-huayro": 0.75,
    "alpaca": 0.7,
    "cuy": 0.75,
    "queso-andino": 0.8,
    "maca": 0.75,
    "haba": 0.85,
}
_JUNGLE = {"frutas": 0.85, "abarrotes": 1.15, "lacteos": 1.15, "pescados": 1.1}
_JUNGLE_ITEMS = {
    "platano": 0.65,
    "platano-verde": 0.55,
    "platano-maduro": 0.6,
    "yuca": 0.65,
    "papaya": 0.6,
    "pina": 0.6,
    "papa": 1.4,
    "papa-amarilla": 1.35,
    "tilapia": 0.85,
}

CITIES = {
    "lima": ("Lima", "Costa", 1.0, {}, {}),
    "callao": ("Callao", "Costa", 1.0, {"pescados": 0.95}, {}),
    "arequipa": ("Arequipa", "Costa sur / sierra", 1.02, {**_COAST_SOUTH, "carnes": 0.92}, {"trucha": 0.85, "queso-andino": 0.85}),
    "trujillo": ("Trujillo", "Costa norte", 0.97, _COAST_NORTH, {}),
    "chiclayo": ("Chiclayo", "Costa norte", 0.97, _COAST_NORTH, {"zapallo-loche": 0.75}),
    "piura": ("Piura", "Costa norte", 0.99, {**_COAST_NORTH, "carnes": 1.1}, {"mango": 0.6, "limon": 0.7, "platano-verde": 0.8}),
    "ica": ("Ica", "Costa sur", 0.98, _COAST_SOUTH, {"uva": 0.7, "pallar": 0.85}),
    "tacna": ("Tacna", "Costa sur", 1.04, _COAST_SOUTH, {"aceituna": 0.75}),
    "chimbote": ("Chimbote", "Costa norte", 0.96, {"pescados": 0.8}, {}),
    "cusco": ("Cusco", "Sierra", 1.06, _HIGHLANDS, _HIGHLAND_ITEMS),
    "huancayo": ("Huancayo", "Sierra", 0.98, _HIGHLANDS, _HIGHLAND_ITEMS),
    "puno": ("Puno", "Sierra", 1.05, {**_HIGHLANDS, "carnes": 1.2}, {**_HIGHLAND_ITEMS, "trucha": 0.6}),
    "ayacucho": ("Ayacucho", "Sierra", 1.0, _HIGHLANDS, _HIGHLAND_ITEMS),
    "cajamarca": ("Cajamarca", "Sierra", 1.0, {**_HIGHLANDS, "lacteos": 0.85}, {**_HIGHLAND_ITEMS, "queso-fresco": 0.75}),
    "huaraz": ("Huaraz", "Sierra", 1.02, _HIGHLANDS, _HIGHLAND_ITEMS),
    "iquitos": ("Iquitos", "Selva", 1.18, _JUNGLE, _JUNGLE_ITEMS),
    "pucallpa": ("Pucallpa", "Selva", 1.12, _JUNGLE, _JUNGLE_ITEMS),
    "tarapoto": ("Tarapoto", "Selva", 1.08, _JUNGLE, _JUNGLE_ITEMS),
}

DEFAULT_CITY = "lima"


def city_factor(ing: Ingredient, city: str) -> float:
    _, _, general, by_section, by_item = CITIES.get(city, CITIES[DEFAULT_CITY])
    return general * by_section.get(ing.section, 1.0) * by_item.get(ing.id, 1.0)


def unit_price(ing_id: str, city: str = DEFAULT_CITY) -> float:
    """Precio aproximado por kg, litro o unidad en la ciudad."""
    ing = INGREDIENTS[ing_id]
    return round(ing.price * city_factor(ing, city), 2)


def cost(ing_id: str, qty: float, city: str = DEFAULT_CITY) -> float:
    ing = INGREDIENTS[ing_id]
    return ing.cost(qty) * city_factor(ing, city)


def cities_payload():
    return [
        {"id": k, "name": v[0], "region": v[1]}
        for k, v in sorted(CITIES.items(), key=lambda kv: kv[1][0])
    ]
