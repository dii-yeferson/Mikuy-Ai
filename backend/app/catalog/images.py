"""Fotos reales de recetas.

Cada foto vive en `frontend/public/recetas/<id-de-receta>.webp` (800×600, < 120 KB).
El servidor detecta solo qué recetas tienen foto: basta con agregar o quitar el archivo.
Sin foto, la app muestra la portada ilustrada y animada.
"""

from pathlib import Path

from ..config import settings


def _scan() -> set[str]:
    folders = [Path(__file__).resolve().parents[3] / "frontend" / "public" / "recetas"]
    if settings().static_dir:
        folders.insert(0, Path(settings().static_dir) / "recetas")
    return {p.stem for folder in folders if folder.is_dir() for p in folder.glob("*.webp")}


WITH_PHOTO: set[str] = _scan()


def image_for(recipe_id: str) -> str | None:
    return f"/recetas/{recipe_id}.webp" if recipe_id in WITH_PHOTO else None
