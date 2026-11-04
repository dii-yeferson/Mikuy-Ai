"""Separar consumo de recetas de compra sugerida. Presentaciones editables, no cotizaciones."""

from decimal import ROUND_CEILING, Decimal

from sqlalchemy import select

from .catalog import money
from .domain import aggregate
from .models import Shopping

# Convenciones de compra sugeridas, no mínimos obligatorios de un comercio.
PACKS = {
    "ajo": 100,
    "aji-panca": 100,
    "aji-amarillo": 100,
    "harina": 1000,
    "aceite": 1000,
    "aceite-oliva": 250,
    "sal": 500,
    "avena": 500,
    "arroz": 1000,
    "arroz-integral": 1000,
    "quinua": 500,
    "lenteja": 500,
    "lentejas": 500,
    "comino": 20,
    "oregano": 20,
    "pimienta": 20,
}


def purchase_quantity(item):
    step = PACKS.get(
        item["ingredient_id"], 1 if item["unit"] == "unid" else 100 if item["unit"] == "ml" else 250
    )
    quantity = Decimal(str(item["quantity"]))
    return float((quantity / step).to_integral_value(rounding=ROUND_CEILING) * step)


def shopping_response(db, row):
    items = aggregate(row.data["meals"])
    overrides = {
        r.ingredient_id: r.data
        for r in db.scalars(select(Shopping).where(Shopping.plan_id == row.id))
    }
    for item in items:
        item["planned_quantity"] = item["quantity"]
        item["planned_cost"] = item["cost"]
        item["suggested_quantity"] = purchase_quantity(item)
        item["quantity"] = item["suggested_quantity"]
        item["adjusted"] = item["ingredient_id"] in overrides
        if item["adjusted"]:
            item.update(overrides[item["ingredient_id"]])
        item["cost"] = money(Decimal(str(item["quantity"])) * Decimal(str(item["unit_price"])))
        item["leftover_quantity"] = max(0, round(item["quantity"] - item["planned_quantity"], 2))
    return dict(
        plan_id=row.id,
        version=row.version,
        items=items,
        planned_cost=row.data["cost"],
        shopping_cost=money(sum(Decimal(str(i["cost"])) for i in items)),
        note="Precios aproximados, no cotizaciones. Compra sugerida redondeada; ajusta al tamaño y precio de tu mercado. Si ya lo tienes, pon cantidad 0. El sobrante puede usarse después.",
    )
