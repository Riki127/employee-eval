from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db import get_session
from app.main import app
from app.models import AssessmentSession, SessionStatus


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


def test_answer_loop_completes_after_five_questions(db_session: Session):
    client = make_client(db_session)
    start = client.post("/sessions", json={"role_title": "Software Engineer"})
    session_id = start.json()["session_id"]

    for _ in range(4):
        response = client.post(f"/sessions/{session_id}/answer", json={"answer": "a reasonably detailed answer"})
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"
        assert response.json()["question"]

    final = client.post(f"/sessions/{session_id}/answer", json={"answer": "a final reasonably detailed answer"})

    assert final.status_code == 200
    body = final.json()
    assert body["status"] == "completed"
    assert body["verdict"] in {"below", "meeting", "exceeding"}
    assert body["rationale"]
    assert body["recommendation"]


def test_answering_completed_session_returns_409(db_session: Session):
    client = make_client(db_session)
    start = client.post("/sessions", json={"role_title": "Software Engineer"})
    session_id = start.json()["session_id"]

    for _ in range(5):
        client.post(f"/sessions/{session_id}/answer", json={"answer": "a reasonably detailed answer"})

    response = client.post(f"/sessions/{session_id}/answer", json={"answer": "late answer"})

    assert response.status_code == 409


def test_provider_failure_returns_502_and_leaves_session_in_progress(db_session: Session, monkeypatch):
    from app.routers import sessions as sessions_module

    client = make_client(db_session)
    start = client.post("/sessions", json={"role_title": "Software Engineer"})
    session_id = start.json()["session_id"]

    def raise_error(*args, **kwargs):
        raise RuntimeError("mock provider exploded")

    monkeypatch.setattr(sessions_module.ai_provider, "generate_next_question", raise_error)

    response = client.post(f"/sessions/{session_id}/answer", json={"answer": "a reasonably detailed answer"})
    assert response.status_code == 502

    monkeypatch.undo()
    # GET /sessions/{id} doesn't exist until Task 7 — verify persisted state directly instead.
    persisted = db_session.get(AssessmentSession, session_id)
    assert persisted is not None
    assert persisted.status == SessionStatus.in_progress
