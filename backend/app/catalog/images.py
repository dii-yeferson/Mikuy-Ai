"""Fotos reales de recetas.

Para agregar una foto: guarda la imagen como `frontend/public/recetas/<id-de-receta>.webp`
(por ejemplo `lomo-saltado.webp`, 800×600 aprox.) y agrega el id a este conjunto.
Mientras una receta no tenga foto, la app muestra su portada ilustrada y animada.
"""

WITH_PHOTO: set[str] = set()


def image_for(recipe_id: str) -> str | None:
    return f"/recetas/{recipe_id}.webp" if recipe_id in WITH_PHOTO else None
