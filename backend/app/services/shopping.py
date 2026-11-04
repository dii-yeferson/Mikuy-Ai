"""Lista de compras consolidada con precios aproximados por ciudad."""

from __future__ import annotations

import math

from ..catalog import BY_ID, INGREDIENTS, SECTIONS
from ..catalog.prices import cost, unit_price

LOOSE = {"verduras", "frutas", "tuberculos", "carnes", "pescados"}
PANTRY = {"sal", "pimienta", "comino", "oregano", "palillo", "laurel", "canela", "clavo", "vainilla", "aceite", "aceite-oliva", "vinagre", "sillao", "azucar"}


def _round_loose(need: float, unit: str) -> float:
    if unit == "u":
        return math.ceil(need - 1e-9)
    step = 50 if need < 500 else 100
    return math.ceil(need / step) * step


def _fmt_qty(qty: float, unit: str) -> str:
    if unit == "u":
        n = int(qty) if float(qty).is_integer() else round(qty, 1)
        return f"{n} unid."
    if qty >= 1000:
        big = "kg" if unit == "g" else "L"
        return f"{qty / 1000:.2f}".rstrip("0").rstrip(".") + f" {big}"
    return f"{round(qty)} {unit}"


def build(plan: dict, profile: dict, state: dict | None = None) -> dict:
    state = state or {}
    checked = set(state.get("checked", []))
    include_pantry = bool(state.get("include_pantry", False))
    city = profile.get("city", "lima")
    people = max(1, int(profile.get("people") or 1))
    need: dict[str, float] = {}
    used_in: dict[str, set] = {}
    for d in plan["days"]:
        for m in d["meals"]:
            r = BY_ID[m["recipe_id"]]
            for ing_id, qty in r.parts:
                need[ing_id] = need.get(ing_id, 0) + qty * m["portion"] * people
                used_in.setdefault(ing_id, set()).add(r.name)
    sections: dict[str, list] = {}
    total_buy = total_used = 0.0
    pending = 0.0
    for ing_id, qty in need.items():
        ing = INGREDIENTS[ing_id]
        pantry = ing_id in PANTRY
        if ing.section in LOOSE or ing.unit == "u" and ing.pack <= 1:
            buy_qty = _round_loose(qty, ing.unit)
            packs = None
        else:
            packs = math.ceil(qty / ing.pack - 1e-9)
            buy_qty = packs * ing.pack
        buy_cost = cost(ing_id, buy_qty, city)
        used_cost = cost(ing_id, qty, city)
        item = {
            "id": ing_id,
            "name": ing.name,
            "need": _fmt_qty(qty, ing.unit),
            "buy": (f"{packs} × {_fmt_qty(ing.pack, ing.unit)}" if packs else _fmt_qty(buy_qty, ing.unit)),
            "buy_cost": round(buy_cost, 2),
            "used_cost": round(used_cost, 2),
            "unit_price": unit_price(ing_id, city),
            "price_unit": {"g": "kg", "ml": "L", "u": "unid."}[ing.unit],
            "pantry": pantry,
            "checked": ing_id in checked,
            "recipes": sorted(used_in[ing_id])[:4],
        }
        if pantry and not include_pantry:
            item["hidden"] = True
        sections.setdefault(ing.section, []).append(item)
        if not item.get("hidden"):
            total_buy += buy_cost
            total_used += used_cost
            if not item["checked"]:
                pending += buy_cost
    ordered = [
        {"id": key, "name": SECTIONS[key], "items": sorted(sections[key], key=lambda i: i["name"])}
        for key in SECTIONS
        if key in sections
    ]
    return {
        "city": city,
        "people": people,
        "sections": ordered,
        "total_buy": round(total_buy, 2),
        "total_used": round(total_used, 2),
        "pending": round(pending, 2),
        "include_pantry": include_pantry,
        "count": sum(1 for s in ordered for i in s["items"] if not i.get("hidden")),
    }


def as_text(shopping: dict) -> str:
    lines = ["🛒 Lista de compras Mikuy", ""]
    for section in shopping["sections"]:
        items = [i for i in section["items"] if not i.get("hidden")]
        if not items:
            continue
        lines.append(f"*{section['name']}*")
        for i in items:
            mark = "✅" if i["checked"] else "▫️"
            lines.append(f"{mark} {i['name']}: {i['buy']} (aprox. S/ {i['buy_cost']:.2f})")
        lines.append("")
    lines.append(f"Total aprox.: S/ {shopping['total_buy']:.2f}")
    return "\n".join(lines)
