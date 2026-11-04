from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Base, engine
from .routes import app_routes, assistant, auth, premium


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Mikuy API", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)
for module in (auth, app_routes, assistant, premium):
    app.include_router(module.router)


@app.get("/api/health")
def health():
    from .catalog import RECIPES
    from .services.assistant import ai_configured

    return {"ok": True, "recipes": len(RECIPES), "ai": ai_configured(), "payments": "simulados" if settings().payments_simulated else "reales"}
