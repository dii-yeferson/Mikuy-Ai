from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://mikuy:mikuy_local@localhost:5432/mikuy"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    cookie_secure: bool = False
    ai_provider: Literal["nvidia", "groq"] = "nvidia"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_analysis_model: str = ""
    groq_review_model: str = ""
    nvidia_api_key: str = ""
    nvidia_model: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    coach_live_rag: bool = True
    nvidia_analysis_model: str = ""
    nvidia_review_model: str = ""
    session_days: int = 7


@lru_cache
def settings():
    return Settings()
