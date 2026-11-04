# Reglas de trabajo en Mikuy

- Responde siempre en español.
- No modifiques, borres ni subas nada sin explicarlo antes y recibir la confirmación del propietario. Él debe saber todo lo que se hace.
- Los commits van a nombre del propietario (`dii-yeferson <diego.quispe.hu@tecsup.edu.pe>`). Nunca te pongas como autor ni agregues `Co-Authored-By` o menciones a Claude en commits, código o archivos.
- Nunca subas claves ni archivos `.env`.
- El repositorio Qurri-Ai es otro proyecto: solo se lee como referencia de estilo, nunca se edita.

## Proyecto

Ver `README.md`. Backend FastAPI en `backend/`, frontend React + Vite en `frontend/`.

- Verificación: `cd backend && pytest` y `cd frontend && npm run build`.
- Recetas: `backend/app/catalog/recipes_*.py` (cantidades por porción; ids de ingrediente en `ingredients.py`).
- Precios por ciudad: `backend/app/catalog/prices.py`. Fuentes con enlace: `sources.py`.
- Sonidos y vibración: `frontend/src/lib/feel.ts`. Estilos y tokens: `frontend/src/styles.css`.
