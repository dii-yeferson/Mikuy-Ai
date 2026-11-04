from .ingredients import FLAG_LABELS, INGREDIENTS, SECTIONS, Ingredient
from .recipe_base import Recipe
from .recipes_almuerzos_1 import ALMUERZOS_1
from .recipes_almuerzos_2 import ALMUERZOS_2
from .recipes_cenas import CENAS
from .recipes_desayunos import DESAYUNOS
from .recipes_snacks import SNACKS

RECIPES: list[Recipe] = [*DESAYUNOS, *ALMUERZOS_1, *ALMUERZOS_2, *CENAS, *SNACKS]
BY_ID: dict[str, Recipe] = {r.id: r for r in RECIPES}

__all__ = ["BY_ID", "FLAG_LABELS", "INGREDIENTS", "RECIPES", "SECTIONS", "Ingredient", "Recipe"]
