import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_mikuy.db")
os.environ["GROQ_API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def user(client):
    r = client.post("/api/auth/register", json={"name": "Diego", "email": "diego@example.com", "password": "clave-segura-1"})
    assert r.status_code == 200, r.text
    client.put(
        "/api/profile",
        json={"onboarded": True, "goal": "bajar", "sex": "hombre", "age": 30, "weight_kg": 80, "height_cm": 172,
              "activity": "ligera", "city": "lima", "people": 2, "weekly_budget": 160},
    )
    return client
