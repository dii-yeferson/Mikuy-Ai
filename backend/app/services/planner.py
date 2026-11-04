"""Planificador semanal: elige recetas según presupuesto, metas, dieta y variedad."""

from __future__ import annotations

import random
from datetime import date, timedelta

from ..catalog import BY_ID, RECIPES, Recipe
from . import nutrition as nu

DAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
BUDGET_SHARE = {"desayuno": 0.2, "almuerzo": 0.47, "cena": 0.25, "snack": 0.08}
PROTEINS = (
    "pollo", "pechuga", "gallina", "pavita", "res", "lomo", "higado", "corazon", "cerdo",
    "cordero", "alpaca", "cuy", "bonito", "jurel", "caballa", "perico", "merluza", "tilapia",
    "trucha", "pota", "langostino", "choros", "atun", "huevo", "lenteja", "frejol", "garbanzo",
    "pallar", "tofu", "quinua",
)


def week_start(today: date | None = None) -> date:
    today = today or date.today()
    return today - timedelta(days=today.weekday())


def meals_for(profile: dict) -> list[str]:
    meals = ["desayuno", "almuerzo", "cena"]
    if profile.get("snacks"):
        meals.append("snack")
    return meals


def main_protein(recipe: Recipe) -> str:
    for ing_id, _ in recipe.parts:
        for p in PROTEINS:
            if ing_id.startswith(p):
                return p
    return "otro"


def candidates(profile: dict, meal: str) -> list[Recipe]:
    max_minutes = int(profile.get("max_minutes") or 0)
    pool = [r for r in RECIPES if r.meal == meal and nu.allowed(r, profile)]
    if max_minutes:
        quick = [r for r in pool if r.minutes <= max_minutes]
        pool = quick or pool
    return pool


class Planner:
    def __init__(self, profile: dict, seed: int | None = None):
        self.profile = profile
        self.city = profile.get("city", "lima")
        self.people = max(1, int(profile.get("people") or 1))
        self.budget = float(profile.get("weekly_budget") or 0)
        self.targets = nu.daily_targets(profile)
        self.rng = random.Random(seed)
        self.favorites = set(profile.get("favorites", []))
        self.meals = meals_for(profile)
        self.pools = {m: candidates(profile, m) for m in self.meals}
        self._cost_cache: dict[str, float] = {}

    def cost(self, recipe: Recipe) -> float:
        if recipe.id not in self._cost_cache:
            self._cost_cache[recipe.id] = nu.recipe_cost(recipe, self.city)
        return self._cost_cache[recipe.id]

    def meal_kcal(self, meal: str) -> float:
        return self.targets["kcal"] * nu.MEAL_SHARE[meal]

    def meal_budget(self, meal: str) -> float | None:
        if not self.budget:
            return None
        return self.budget / 7 / self.people * BUDGET_SHARE[meal] / sum(
            BUDGET_SHARE[m] for m in self.meals
        )

    def score(self, recipe: Recipe, meal: str, used: dict, prev_protein: str | None) -> float:
        portion = nu.portion_for(recipe, self.meal_kcal(meal))
        n = nu.recipe_nutrition(recipe, portion)
        cost = self.cost(recipe) * portion
        score = 0.0
        cap = self.meal_budget(meal)
        if cap:
            over = max(0.0, cost - cap) / cap
            score -= over * 6
            score += min(cap / max(cost, 0.5), 2) * 0.4
        else:
            score -= cost * 0.05
        target = self.meal_kcal(meal)
        score -= abs(n["kcal"] - target) / target * 1.5
        if meal in {"almuerzo", "cena"}:
            protein_goal = self.targets["protein"] * nu.MEAL_SHARE[meal]
            score -= max(0, protein_goal - n["protein"]) / protein_goal * 1.2
        score -= max(0, n["sodium"] - 900) / 900
        score -= used.get(recipe.id, 0) * 5
        if prev_protein and main_protein(recipe) == prev_protein:
            score -= 0.8
        if recipe.id in self.favorites:
            score += 0.6
        if "postre" in recipe.tags:
            score -= 0.5
        return score + self.rng.random() * 0.9

    def pick(self, meal: str, used: dict, prev_protein: str | None, exclude: set[str] = frozenset()) -> Recipe:
        pool = [r for r in self.pools[meal] if r.id not in exclude] or self.pools[meal]
        if not pool:
            raise ValueError(f"No hay recetas de {meal} compatibles con tu perfil.")
        return max(pool, key=lambda r: self.score(r, meal, used, prev_protein))

    def entry(self, recipe: Recipe, meal: str) -> dict:
        return {"meal": meal, "recipe_id": recipe.id, "portion": nu.portion_for(recipe, self.meal_kcal(meal))}

    def generate(self, start: date) -> dict:
        used: dict[str, int] = {}
        days = []
        prev = {m: None for m in self.meals}
        for i, name in enumerate(DAYS):
            meals = []
            for meal in self.meals:
                recipe = self.pick(meal, used, prev[meal])
                used[recipe.id] = used.get(recipe.id, 0) + 1
                prev[meal] = main_protein(recipe)
                meals.append(self.entry(recipe, meal))
            days.append({"day": name, "date": (start + timedelta(days=i)).isoformat(), "meals": meals})
        plan = {"week_start": start.isoformat(), "days": days}
        self.fit_budget(plan)
        return plan

    def plan_cost(self, plan: dict) -> float:
        return sum(
            self.cost(BY_ID[m["recipe_id"]]) * m["portion"] * self.people
            for d in plan["days"]
            for m in d["meals"]
        )

    def fit_budget(self, plan: dict) -> None:
        """Si el menú pasa el presupuesto, cambia los platos más caros por opciones más baratas."""
        if not self.budget:
            return
        for _ in range(40):
            total = self.plan_cost(plan)
            if total <= self.budget:
                return
            used_ids = {m["recipe_id"] for d in plan["days"] for m in d["meals"]}
            slots = sorted(
                ((d, m) for d in plan["days"] for m in d["meals"]),
                key=lambda dm: self.cost(BY_ID[dm[1]["recipe_id"]]) * dm[1]["portion"],
                reverse=True,
            )
            changed = False
            for day, entry in slots[:6]:
                current = BY_ID[entry["recipe_id"]]
                cheaper = [
                    r for r in self.pools[entry["meal"]]
                    if self.cost(r) < self.cost(current) * 0.8 and r.id not in used_ids
                ] or [r for r in self.pools[entry["meal"]] if self.cost(r) < self.cost(current) * 0.8]
                if cheaper:
                    best = max(cheaper, key=lambda r: self.score(r, entry["meal"], {}, None) - self.cost(r) * 0.3)
                    entry.update(self.entry(best, entry["meal"]))
                    changed = True
                    break
            if not changed:
                return

    def alternatives(self, meal: str, current_id: str, query: str = "", limit: int = 8) -> list[Recipe]:
        pool = [r for r in self.pools[meal] if r.id != current_id]
        query = (query or "").lower()
        if query:
            words = [w for w in query.split() if len(w) > 2]
            matched = [r for r in pool if any(w in (r.name + " " + " ".join(r.tags) + " " + " ".join(i for i, _ in r.parts)).lower() for w in words)]
            pool = matched or pool
        return sorted(pool, key=lambda r: self.score(r, meal, {}, None), reverse=True)[:limit]


def summarize(plan: dict, profile: dict) -> dict:
    """Totales del menú: costo semanal y nutrientes promedio por día (de la persona)."""
    city = profile.get("city", "lima")
    people = max(1, int(profile.get("people") or 1))
    week_cost = 0.0
    days_out = []
    sums = dict.fromkeys(nu.NUTRIENTS, 0.0)
    for d in plan["days"]:
        day_n = dict.fromkeys(nu.NUTRIENTS, 0.0)
        day_cost = 0.0
        for m in d["meals"]:
            r = BY_ID[m["recipe_id"]]
            n = nu.recipe_nutrition(r, m["portion"])
            for k in nu.NUTRIENTS:
                day_n[k] += n[k]
            day_cost += nu.recipe_cost(r, city, m["portion"]) * people
        week_cost += day_cost
        for k in nu.NUTRIENTS:
            sums[k] += day_n[k]
        days_out.append({"date": d["date"], "kcal": round(day_n["kcal"]), "protein": round(day_n["protein"]), "cost": round(day_cost, 2)})
    n_days = len(plan["days"]) or 1
    avg = {k: round(v / n_days, 1) for k, v in sums.items()}
    budget = float(profile.get("weekly_budget") or 0)
    return {
        "week_cost": round(week_cost, 2),
        "budget": budget,
        "within_budget": (week_cost <= budget) if budget else None,
        "per_person_day": round(week_cost / n_days / people, 2),
        "avg": avg,
        "days": days_out,
        "targets": nu.daily_targets(profile),
    }
