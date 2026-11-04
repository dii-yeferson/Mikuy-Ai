"""Cálculos deterministas: ninguna cifra procede de una operación hecha por el LLM."""

import ast
import re
from decimal import Decimal, InvalidOperation, localcontext

from .catalog import INGREDIENTS, PRICE_DATE, PRICE_NOTE
from .domain import total
from .schemas import normalize


def arithmetic(expression):
    if len(expression) > 150 or not re.fullmatch(r"[\d\s.,+*/()\-]+", expression):
        raise ValueError("Expresión no permitida")
    tree = ast.parse(expression.replace(",", "."), mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 40:
        raise ValueError("Expresión demasiado larga")

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            return Decimal(ast.get_source_segment(expression.replace(",", "."), node))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = visit(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp) and isinstance(
            node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)
        ):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if not right:
                raise ValueError("No se puede dividir entre cero")
            return left / right
        raise ValueError("Operación no permitida")

    with localcontext() as ctx:
        ctx.prec = 28
        value = visit(tree)
    if not value.is_finite() or abs(value) > Decimal("1e15"):
        raise ValueError("Resultado fuera del rango admitido")
    return value


def fmt(value, places=2):
    return (
        format(Decimal(str(value)).quantize(Decimal(10) ** -places), "f").rstrip("0").rstrip(".")
        or "0"
    )


def calculate(intent, question, previous, profile, plan):
    if intent.calculation == "none":
        return None
    supplied = normalize(" ".join([question, *[m.question for m in previous]]))
    if intent.calculation == "arithmetic":
        expression = intent.expression
        # Los operandos deben estar en el texto del usuario, no en la respuesta previa.
        supplied_numbers = set(re.findall(r"\d+(?:\.\d+)?", supplied.replace(",", ".")))
        if "%" in supplied or "por ciento" in supplied:
            supplied_numbers.add("100")
        if any(n not in supplied_numbers for n in re.findall(r"\d+(?:\.\d+)?", expression)):
            return dict(
                answer="Necesito la operación y sus números para calcularla sin suponer valores.",
                verified=False,
            )
        try:
            value = arithmetic(expression)
            return dict(
                answer=f"{expression} = {fmt(value, 6)}",
                verified=True,
                result=str(value),
                expression=expression,
            )
        except (ValueError, SyntaxError, InvalidOperation, OverflowError):
            return dict(
                answer="No puedo calcular esa operación tal como está escrita. Indícame los números y la operación; no se admite dividir entre cero.",
                verified=False,
            )
    menu_budget = bool(
        re.search(
            r"menu|plan|semana|presupuesto|saldo|quedan", normalize(intent.rewritten_question)
        )
    )
    if intent.calculation == "budget" and not menu_budget and not intent.amounts:
        return dict(
            answer="Para estimar ese costo necesito el alimento y su cantidad. Los precios del catálogo son estimaciones, no cotizaciones de tiendas.",
            verified=False,
        )
    if intent.calculation == "budget" and menu_budget:
        if not plan:
            return dict(
                answer="Todavía no tienes un menú guardado para calcular su costo. ¿Quieres organizarlo con el presupuesto de tu perfil?",
                verified=False,
            )
        cost = Decimal(str(total(plan.data["meals"])))
        budget = Decimal(str(profile.budget))
        return dict(
            answer=f"Tu último menú guardado cuesta aproximadamente S/ {cost:.2f}. Con tu presupuesto semanal de S/ {budget:.2f}, {'quedan' if budget >= cost else 'faltan'} S/ {abs(budget - cost):.2f}. {PRICE_NOTE}",
            verified=True,
            cost=str(cost),
            budget=str(budget),
            remaining=str(budget - cost),
        )
    if not intent.amounts:
        return dict(
            answer="Para calcularlo necesito la cantidad y la preparación del alimento. ¿Cuántos gramos, mililitros o unidades tienes?",
            verified=False,
        )
    totals = {k: Decimal(0) for k in ("kcal", "carbs", "fiber", "protein", "fat", "sodium")}
    cost, rows = Decimal(0), []
    for amount in intent.amounts:
        span = normalize(amount.evidence_span)
        if (
            not span
            or span not in supplied
            or not any(
                Decimal(n.replace(",", ".")) == Decimal(str(amount.quantity))
                for n in re.findall(r"\d+(?:[.,]\d+)?", span)
            )
        ):
            return dict(
                answer="No encuentro una cantidad confirmada por ti. Dime la cantidad y la unidad del alimento que quieres calcular.",
                verified=False,
            )
        name = normalize(amount.food)
        exact = [
            (key, item)
            for key, item in INGREDIENTS.items()
            if name == normalize(item["name"]) or name == key
        ]
        matches = exact or [
            (key, item)
            for key, item in INGREDIENTS.items()
            if name in map(normalize, item["aliases"])
        ]
        if len(matches) != 1:
            return dict(
                answer=f"Necesito precisar «{amount.food}» para calcularlo: indica la variedad o el corte y si el peso es crudo o cocido.",
                verified=False,
            )
        key, item = matches[0]
        if any(
            t in normalize(amount.preparation + " " + span)
            for t in ("cocido", "frito", "horno", "hervido")
        ) and not any(
            t in normalize(item["name"]) for t in ("cocido", "frito", "horno", "hervido")
        ):
            return dict(
                answer=f"El catálogo no identifica una entrada equivalente a esa preparación de {item['name']}. No voy a sustituir peso cocido por crudo. Necesito una ficha o etiqueta correspondiente a la preparación.",
                verified=False,
            )
        quantity = Decimal(str(amount.quantity))
        unit = amount.unit
        if unit in {"kg", "l"}:
            quantity *= 1000
            unit = "g" if unit == "kg" else "ml"
        if unit != item["unit"]:
            return dict(
                answer=f"La ficha de {item['name']} usa {item['unit']}; no hay conversión verificada desde {amount.unit}. Indica la cantidad en {item['unit']}.",
                verified=False,
            )
        factor = quantity if item["per"] == "unid" else quantity / 100
        for nutrient in totals:
            totals[nutrient] += Decimal(str(item["nutrients"][nutrient])) * factor
        cost += quantity * Decimal(str(item["unit_price"]))
        rows.append(dict(id=key, amount=str(quantity), unit=unit, factor=str(factor)))
    description = ", ".join(
        f"{row['amount']} {row['unit']} de {INGREDIENTS[row['id']]['name']}" for row in rows
    )
    answer = f"Para {description}, el catálogo estimativo de Mikuy da: {fmt(totals['kcal'])} kcal; {fmt(totals['protein'])} g de proteína; {fmt(totals['carbs'])} g de carbohidratos; {fmt(totals['fat'])} g de grasa; {fmt(totals['fiber'])} g de fibra y {fmt(totals['sodium'])} mg de sodio. Costo estimado: S/ {cost:.2f}."
    answer += f"\nCálculo: valor de la ficha × cantidad / 100 (o por unidad). Son estimaciones del catálogo, no una medición del plato ni una cotización actual; precios de referencia del {PRICE_DATE}."
    return dict(
        answer=answer,
        verified=True,
        totals={k: str(v) for k, v in totals.items()},
        cost=str(cost),
        rows=rows,
        estimated=True,
    )
