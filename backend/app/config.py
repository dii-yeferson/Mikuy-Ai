from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Local: SQLite sin instalar nada. Producción: postgresql+psycopg://... (Neon)
    database_url: str = "sqlite:///./mikuy.db"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    cookie_secure: bool = False
    cookie_samesite: str = "lax"  # "none" si el frontend y la API están en dominios distintos
    session_days: int = 30

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # Pagos: mientras sea True, el pago se simula con un código generado por la app.
    payments_simulated: bool = True


@lru_cache
def settings() -> Settings:
    return Settings()
