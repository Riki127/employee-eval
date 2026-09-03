from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db import get_session
from app.main import app


def make_client(db_session: Session) -> TestClient:
    app.dependency_overrides[get_session] = lambda: db_session
    client = TestClient(app)
    return client


def test_start_session_creates_new_role(db_session: Session):
    client = make_client(db_session)

    response = client.post("/sessions", json={"role_title": "Software Engineer"})

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] > 0
    assert body["role_id"] > 0
    assert isinstance(body["question"], str) and body["question"]


def test_start_session_reuses_matching_role(db_session: Session):
    client = make_client(db_session)

    first = client.post("/sessions", json={"role_title": "Software Engineer"})
    second = client.post("/sessions", json={"role_title": "Software Developer"})

    assert first.json()["role_id"] == second.json()["role_id"]
