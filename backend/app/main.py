import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from . import (
    coach_insights,
    coach_plans,
    routes_auth,
    routes_coach,
    routes_community,
    routes_entries,
    routes_experience,
    routes_onboarding,
    routes_plans,
    routes_profile,
)
from .config import settings
from .conversations import purge
from .conversations import router as conversations_router
from .db import SessionLocal, get_db


def purge_conversations():
    with SessionLocal() as db:
        purge(db)
        db.commit()


@asynccontextmanager
async def lifespan(app):
    async def cleanup():
        while True:
            try:
                await asyncio.to_thread(purge_conversations)
            except OperationalError:
                logging.getLogger(__name__).warning(
                    "Limpieza de chats pendiente: base no disponible"
                )
            await asyncio.sleep(5)

    task = asyncio.create_task(cleanup())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="Mikuy",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
app.include_router(conversations_router, prefix="/api")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-Mikuy-Request"],
)


def trusted_origin(request: Request) -> bool:
    """CSRF por verificación de origen (OWASP): se acepta el origen si es el mismo sitio
    al que el navegador envió la solicitud (p. ej. a través del proxy de Vite o un mismo
    dominio) o si está en la lista explícita CORS_ORIGINS (frontend en otro dominio).
    Un sitio ajeno nunca coincide con el Host de Mikuy y además no puede enviar la
    cabecera X-Mikuy-Request sin una verificación CORS previa que se le deniega."""
    origin = request.headers.get("origin")
    if not origin:
        return True
    if origin in settings().cors_origins:
        return True
    parts = urlsplit(origin)
    host = (request.headers.get("host") or "").lower()
    return parts.scheme in {"http", "https"} and bool(host) and parts.netloc.lower() == host


@app.middleware("http")
async def protect_writes(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if request.headers.get("x-mikuy-request") != "1" or not trusted_origin(request):
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Solicitud rechazada por seguridad: el origen no es de confianza. "
                    "Abre Mikuy desde la dirección que muestra el script de inicio."
                },
            )
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    labels = {
        "name": "nombre",
        "email": "correo",
        "password": "contraseña",
        "budget": "presupuesto",
        "servings": "porciones",
        "allergies": "alergias",
        "excluded": "alimentos excluidos",
        "conditions": "condiciones declaradas",
        "preferences": "preferencias",
        "diet": "preferencia alimentaria",
        "goal": "objetivo",
        "start_date": "fecha inicial",
        "source": "origen",
        "consent": "consentimiento",
        "quantity": "cantidad",
        "unit_price": "precio",
        "checked": "marcado",
        "recipe_id": "receta",
        "expected_version": "versión del plan",
        "question": "pregunta",
        "tier": "suscripción",
        "simulation": "simulación",
        "kind": "tipo de registro",
        "date": "fecha",
        "value": "valor",
        "text": "texto",
    }
    fields = sorted(set(labels.get(str(e["loc"][-1]), "datos") for e in exc.errors()))
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Revisa los campos: "
            + ", ".join(fields)
            + ". Hay valores ausentes, inválidos o fuera del rango permitido."
        },
    )


@app.exception_handler(OperationalError)
async def database_error(request, exc):
    return JSONResponse(
        status_code=503,
        content={"detail": "No se pudo conectar con la base de datos. Inténtalo de nuevo."},
    )


@app.exception_handler(IntegrityError)
async def conflict_error(request, exc):
    return JSONResponse(
        status_code=409, content={"detail": "Los datos cambiaron. Recarga e inténtalo de nuevo."}
    )


@app.get("/api/health")
def health(db=Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "postgresql", "app": "mikuy"}


for router in [
    coach_plans.router,
    coach_insights.router,
    routes_auth.router,
    routes_community.router,
    routes_profile.router,
    routes_plans.router,
    routes_coach.router,
    routes_entries.router,
    routes_experience.router,
    routes_onboarding.router,
]:
    app.include_router(router, prefix="/api")
