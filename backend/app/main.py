from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
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


# --- App web compilada (un solo servicio en producción) -------------------------------------
_static = Path(settings().static_dir) if settings().static_dir else None
if _static and (_static / "index.html").exists():

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "No encontrado.")
        target = (_static / path).resolve()
        if path and target.is_file() and target.is_relative_to(_static.resolve()):
            headers = {"Cache-Control": "public, max-age=31536000, immutable"} if path.startswith("assets/") else {"Cache-Control": "no-cache"}
            return FileResponse(target, headers=headers)
        return FileResponse(_static / "index.html", headers={"Cache-Control": "no-cache"})
