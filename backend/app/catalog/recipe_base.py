"""Formato compacto de receta. Cantidades por 1 porción (g, ml o unidades)."""

from dataclasses import dataclass, field

MEALS = {"D": "desayuno", "A": "almuerzo", "C": "cena", "S": "snack"}


@dataclass(frozen=True)
class Recipe:
    id: str
    name: str
    meal: str  # desayuno | almuerzo | cena | snack
    minutes: int
    parts: tuple[tuple[str, float], ...]
    steps: tuple[str, ...]
    tags: tuple[str, ...] = field(default=())
    region: str = "Perú"


def R(id, name, meal, minutes, parts, steps, tags="", region="Perú"):
    items = []
    for chunk in parts.split(","):
        ing, qty = chunk.split()
        items.append((ing.strip(), float(qty)))
    return Recipe(
        id=id,
        name=name,
        meal=MEALS[meal],
        minutes=minutes,
        parts=tuple(items),
        steps=tuple(steps),
        tags=tuple(t for t in tags.split() if t),
        region=region,
    )
