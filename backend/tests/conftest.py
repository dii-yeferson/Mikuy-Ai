import os
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

test_url = os.getenv("TEST_DATABASE_URL", "")
if not test_url or not (make_url(test_url).database or "").endswith("_test"):
    raise RuntimeError(
        "TEST_DATABASE_URL debe apuntar explícitamente a una base PostgreSQL terminada en _test."
    )
os.environ["DATABASE_URL"] = test_url
os.environ["AI_PROVIDER"] = "nvidia"
os.environ["GROQ_API_KEY"] = ""
os.environ["NVIDIA_API_KEY"] = ""
os.environ["NVIDIA_MODEL"] = ""
os.environ["COACH_LIVE_RAG"] = "false"

from alembic import command
from alembic.config import Config
from app.db import engine
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest.fixture(scope="session", autouse=True)
def migrate():
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(cfg, "head")


@pytest.fixture(autouse=True)
def clean(migrate):
    # Only named tables on a separately verified *_test database.
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE onboarding_drafts, auth_attempts, entries, messages, shopping, plans, usage, sessions, profiles, users CASCADE"
            )
        )


@pytest.fixture
def client():
    with TestClient(app, headers={"X-Mikuy-Request": "1", "Origin": "http://localhost:5173"}) as c:
        yield c


def register(client, email="prueba@example.com"):
    r = client.post(
        "/api/auth/register",
        json=dict(name="Cuenta de prueba", email=email, password="prueba-segura-2026"),
    )
    assert r.status_code == 201, r.text
    return r.json()


def profile(client, **overrides):
    values = dict(
        completed=True,
        goal="Mantener peso",
        budget=150,
        servings=1,
        diet="Balanceado",
        allergies=[],
        excluded=[],
    )
    values.update(overrides)
    r = client.put("/api/profile", json=values)
    assert r.status_code == 200, r.text
    return r.json()


def plan(client, **overrides):
    values = dict(start_date="2026-10-19", source="catalogo")
    values.update(overrides)
    r = client.post("/api/plans", json=values)
    assert r.status_code == 201, r.text
    return r.json()
