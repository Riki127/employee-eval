# POC Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working end-to-end POC — employee types a role, answers a 5-question AI-generated assessment (AI mocked), and receives a verdict + rationale + learning recommendation, backed by Postgres and covered by backend and Playwright e2e tests.

**Architecture:** FastAPI + SQLModel + Postgres backend behind a REST API, with the AI layer isolated behind an `AIProvider` interface (mocked for this POC, real Anthropic implementation later). React + TypeScript + Tailwind frontend (Vite) with three screens driven by that API. Playwright e2e tests exercise the real running stack.

**Tech Stack:** Python 3.11+, FastAPI, SQLModel, Pydantic v2, PostgreSQL 16 (via Docker Compose), pytest, httpx; React 18, TypeScript, Vite, Tailwind CSS, Playwright (`@playwright/test`).

**Spec:** [docs/superpowers/specs/2026-09-03-poc-vertical-slice-design.md](../specs/2026-09-03-poc-vertical-slice-design.md)

## Global Constraints

- Session length is fixed at **5 questions** per session.
- No authentication. A single hardcoded/seeded `Employee` row represents "the current user."
- The AI layer must sit entirely behind the `AIProvider` interface (`match_or_create_role`, `generate_next_question`, `evaluate_session`) so a real Anthropic-backed implementation can be swapped in later without touching routes, models, or frontend.
- Backend stack: FastAPI, SQLModel, Pydantic, PostgreSQL — no SQLite, no ORM substitutions.
- Frontend stack: React, TypeScript, Tailwind CSS — no additional state-management library.
- Frontend TypeScript types must match backend Pydantic schemas field-for-field.
- Postgres runs via Docker Compose (`docker compose up -d`) and must be running before backend tests or the app are started.
- e2e coverage uses Playwright (`@playwright/test`) against the real running stack, not mocked network calls.

## Refinement vs. the spec

- The spec's Testing section suggested proving role-rubric reuse "via the same rubric-derived question pool being asked." In implementation, the mock's question pool doesn't vary by role, so this plan instead exposes `role_id` in the session-start response and asserts on that directly (Task 5, Task 12) — same requirement (prove reuse happens), a more reliable mechanism to test it.
- The spec's data model lists `role_id` on `Employee`. Since the actual flow (per the later "employee types their role" decision) resolves the role per-session, not per-employee-profile, this plan drops `role_id` from `Employee` — the single seeded employee has no fixed role, and `AssessmentSession.role_id` is the only place role association lives. This matches every other part of the spec (API, frontend flow) more closely than the literal data-model bullet did.

---

## Task 1: Backend project scaffold + Postgres via Docker Compose

**Files:**
- Create: `docker-compose.yml`
- Create: `backend/requirements.txt`
- Create: `backend/requirements-dev.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/__init__.py`
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: `app.config.settings` (`Settings` with `database_url: str`, `session_question_count: int = 5`), a FastAPI `app` instance in `app.main` with a `GET /health` route, importable as `from app.main import app`.

- [ ] **Step 1: Create the Postgres Docker Compose file**

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: employee_eval
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

- [ ] **Step 2: Start Postgres and verify it's up**

Run: `docker compose up -d`
Expected: `db` container reports `running`/`healthy` via `docker compose ps`.

- [ ] **Step 3: Create backend dependency files**

```text
# backend/requirements.txt
fastapi>=0.115
uvicorn[standard]>=0.30
sqlmodel>=0.0.22
psycopg[binary]>=3.2
pydantic>=2.9
pydantic-settings>=2.5
```

```text
# backend/requirements-dev.txt
-r requirements.txt
pytest>=8.3
httpx>=0.27
```

- [ ] **Step 4: Create a virtualenv and install dependencies**

Run (from `backend/`): `python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt` (Windows) or `python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt` (POSIX)
Expected: install completes with no errors.

- [ ] **Step 5: Write config module**

```python
# backend/app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/employee_eval"
    session_question_count: int = 5


settings = Settings()
```

- [ ] **Step 6: Write the failing health-check test**

```python
# backend/app/__init__.py
```

```python
# backend/tests/__init__.py
```

```python
# backend/tests/test_health.py
from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 7: Run the test to verify it fails**

Run (from `backend/`): `pytest tests/test_health.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 8: Write the minimal FastAPI app**

```python
# backend/app/main.py
from fastapi import FastAPI

app = FastAPI(title="Employee Eval POC")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 9: Run the test to verify it passes**

Run (from `backend/`): `pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add docker-compose.yml backend/requirements.txt backend/requirements-dev.txt backend/app/__init__.py backend/app/config.py backend/app/main.py backend/tests/__init__.py backend/tests/test_health.py
git commit -m "feat: backend scaffold with health check and Postgres compose"
```

---

## Task 2: Data models (SQLModel tables) and DB engine

**Files:**
- Create: `backend/app/models.py`
- Create: `backend/app/db.py`
- Modify: `backend/app/main.py` (add startup hook that creates tables)
- Create: `backend/tests/conftest.py`
- Test: `backend/tests/test_models.py`

**Interfaces:**
- Consumes: `app.config.settings` (Task 1).
- Produces: SQLModel tables `Role`, `Employee`, `AssessmentSession` (`__tablename__ = "session"`), `QAPair`, `Evaluation`; enums `SessionStatus` (`in_progress`, `completed`) and `Verdict` (`below`, `meeting`, `exceeding`) in `app.models`. `app.db.engine`, `app.db.get_session()` (FastAPI dependency yielding a `sqlmodel.Session`), `app.db.create_db_and_tables()`.

- [ ] **Step 1: Write the models**

```python
# backend/app/models.py
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import JSON, Column, Field, SQLModel


class Verdict(str, Enum):
    below = "below"
    meeting = "meeting"
    exceeding = "exceeding"


class SessionStatus(str, Enum):
    in_progress = "in_progress"
    completed = "completed"


class Role(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    rubric: dict = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Employee(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class AssessmentSession(SQLModel, table=True):
    __tablename__ = "session"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employee.id")
    role_id: int = Field(foreign_key="role.id")
    status: SessionStatus = Field(default=SessionStatus.in_progress)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class QAPair(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="session.id")
    order: int
    question: str
    answer: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Evaluation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="session.id", unique=True)
    verdict: Verdict
    rationale: str
    recommendation: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

> Note: the table class is named `AssessmentSession`, not `Session` — `Session` is SQLModel's own DB-session class, imported constantly elsewhere in this codebase, and reusing the name would shadow it.

- [ ] **Step 2: Write the DB engine module**

```python
# backend/app/db.py
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

engine = create_engine(settings.database_url, echo=False)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
```

- [ ] **Step 3: Wire table creation into app startup**

```python
# backend/app/main.py
from fastapi import FastAPI

from app.db import create_db_and_tables

app = FastAPI(title="Employee Eval POC")


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 4: Write the DB test fixture**

```python
# backend/tests/conftest.py
import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

engine = create_engine(settings.database_url)


@pytest.fixture()
def db_session() -> Session:
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)
```

- [ ] **Step 5: Write the failing model round-trip test**

```python
# backend/tests/test_models.py
from sqlmodel import Session

from app.models import Employee, Role


def test_role_and_employee_round_trip(db_session: Session):
    role = Role(
        title="Software Engineer",
        rubric={"current_tier_expectations": ["writes clean code"], "next_tier_expectations": ["leads projects"], "career_ladder_summary": "IC ladder"},
    )
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    employee = Employee(name="Jordan Lee")
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)

    assert role.id is not None
    assert employee.id is not None
    assert role.rubric["current_tier_expectations"] == ["writes clean code"]
```

- [ ] **Step 6: Run test to verify it fails**

Run (from `backend/`, with `docker compose up -d` already running): `pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models'` (or import error, since the file didn't exist before Step 1 — after Step 1 this becomes a collection/connection error if Postgres isn't running; confirm Postgres is up before proceeding).

- [ ] **Step 7: Run test to verify it passes**

Run (from `backend/`): `pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/models.py backend/app/db.py backend/app/main.py backend/tests/conftest.py backend/tests/test_models.py
git commit -m "feat: add SQLModel data models and DB engine"
```

---

## Task 3: AI provider schemas, interface, and MockAIProvider

**Files:**
- Create: `backend/app/schemas.py`
- Create: `backend/app/ai/__init__.py`
- Create: `backend/app/ai/base.py`
- Create: `backend/app/ai/mock.py`
- Test: `backend/tests/test_mock_provider.py`

**Interfaces:**
- Consumes: `app.models.Role`, `app.models.QAPair`, `app.models.Verdict` (Task 2).
- Produces: `app.schemas.RoleRubric`, `app.schemas.RoleMatchResult` (`matched_role_id: int | None`, `rubric: RoleRubric`), `app.schemas.QuestionOutput` (`question: str`), `app.schemas.EvaluationOutput` (`verdict: Verdict`, `rationale: str`, `recommendation: str`). `app.ai.base.AIProvider` (`Protocol`) with `match_or_create_role(title, existing_roles) -> RoleMatchResult`, `generate_next_question(role, qa_history) -> QuestionOutput`, `evaluate_session(role, qa_history) -> EvaluationOutput`. `app.ai.mock.MockAIProvider` implementing it.

- [ ] **Step 1: Write the AI I/O schemas**

```python
# backend/app/schemas.py
from pydantic import BaseModel

from app.models import Verdict


class RoleRubric(BaseModel):
    current_tier_expectations: list[str]
    next_tier_expectations: list[str]
    career_ladder_summary: str


class RoleMatchResult(BaseModel):
    matched_role_id: int | None
    rubric: RoleRubric


class QuestionOutput(BaseModel):
    question: str


class EvaluationOutput(BaseModel):
    verdict: Verdict
    rationale: str
    recommendation: str
```

- [ ] **Step 2: Write the AIProvider interface**

```python
# backend/app/ai/__init__.py
```

```python
# backend/app/ai/base.py
from typing import Protocol

from app.models import QAPair, Role
from app.schemas import EvaluationOutput, QuestionOutput, RoleMatchResult


class AIProvider(Protocol):
    def match_or_create_role(self, title: str, existing_roles: list[Role]) -> RoleMatchResult: ...

    def generate_next_question(self, role: Role, qa_history: list[QAPair]) -> QuestionOutput: ...

    def evaluate_session(self, role: Role, qa_history: list[QAPair]) -> EvaluationOutput: ...
```

- [ ] **Step 3: Write the failing MockAIProvider tests**

```python
# backend/tests/test_mock_provider.py
from app.ai.mock import MockAIProvider
from app.models import QAPair, Role, Verdict


def make_role(id: int, title: str, rubric: dict | None = None) -> Role:
    return Role(id=id, title=title, rubric=rubric or {"current_tier_expectations": [], "next_tier_expectations": [], "career_ladder_summary": ""})


def make_qa(order: int, answer: str) -> QAPair:
    return QAPair(id=order, session_id=1, order=order, question="q", answer=answer)


def test_match_or_create_role_reuses_overlapping_title():
    provider = MockAIProvider()
    existing = [make_role(1, "Software Engineer")]

    result = provider.match_or_create_role("Software Developer", existing)

    assert result.matched_role_id == 1


def test_match_or_create_role_creates_new_when_no_overlap():
    provider = MockAIProvider()
    existing = [make_role(1, "Software Engineer")]

    result = provider.match_or_create_role("Product Manager", existing)

    assert result.matched_role_id is None
    assert result.rubric.current_tier_expectations


def test_generate_next_question_is_deterministic_by_history_length():
    provider = MockAIProvider()
    role = make_role(1, "Software Engineer")

    first = provider.generate_next_question(role, [])
    second = provider.generate_next_question(role, [make_qa(0, "answer")])

    assert first.question != second.question


def test_evaluate_session_below_for_short_answers():
    provider = MockAIProvider()
    role = make_role(1, "Software Engineer")
    qa_history = [make_qa(i, "short") for i in range(5)]

    result = provider.evaluate_session(role, qa_history)

    assert result.verdict == Verdict.below


def test_evaluate_session_exceeding_for_long_detailed_answers():
    provider = MockAIProvider()
    role = make_role(1, "Software Engineer")
    long_answer = "This is a long and detailed answer. " * 10
    qa_history = [make_qa(i, long_answer) for i in range(5)]

    result = provider.evaluate_session(role, qa_history)

    assert result.verdict == Verdict.exceeding
```

- [ ] **Step 4: Run tests to verify they fail**

Run (from `backend/`): `pytest tests/test_mock_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.ai.mock'`

- [ ] **Step 5: Write MockAIProvider**

```python
# backend/app/ai/mock.py
from app.models import QAPair, Role, Verdict
from app.schemas import EvaluationOutput, QuestionOutput, RoleMatchResult, RoleRubric

_GENERIC_RUBRIC = RoleRubric(
    current_tier_expectations=[
        "Delivers assigned tasks independently with minimal guidance",
        "Communicates progress and blockers clearly to the team",
        "Applies core technical/domain skills correctly in day-to-day work",
    ],
    next_tier_expectations=[
        "Leads small initiatives end-to-end with limited oversight",
        "Mentors less experienced teammates",
        "Anticipates risks and proposes solutions proactively",
    ],
    career_ladder_summary="Generic individual-contributor progression from current tier to the next tier.",
)

_QUESTION_POOL = [
    "Describe a recent piece of work you're proud of and what made it successful.",
    "Tell me about a time you had to solve a problem with incomplete information.",
    "How do you prioritize your work when you have multiple competing deadlines?",
    "Describe a time you received difficult feedback. How did you respond?",
    "What's a skill you've been actively developing recently, and why?",
    "Tell me about a time you helped a teammate who was stuck.",
]


class MockAIProvider:
    def match_or_create_role(self, title: str, existing_roles: list[Role]) -> RoleMatchResult:
        normalized = title.strip().lower()
        normalized_words = set(normalized.split())

        for role in existing_roles:
            role_words = set(role.title.strip().lower().split())
            if normalized == role.title.strip().lower() or normalized_words & role_words:
                return RoleMatchResult(matched_role_id=role.id, rubric=RoleRubric(**role.rubric))

        return RoleMatchResult(matched_role_id=None, rubric=_GENERIC_RUBRIC)

    def generate_next_question(self, role: Role, qa_history: list[QAPair]) -> QuestionOutput:
        index = len(qa_history)
        return QuestionOutput(question=_QUESTION_POOL[index % len(_QUESTION_POOL)])

    def evaluate_session(self, role: Role, qa_history: list[QAPair]) -> EvaluationOutput:
        avg_len = sum(len(qa.answer or "") for qa in qa_history) / len(qa_history)

        if avg_len < 40:
            return EvaluationOutput(
                verdict=Verdict.below,
                rationale="Answers were brief and lacked concrete detail relative to role expectations.",
                recommendation="Practice giving specific, detailed examples (STAR format) for common work scenarios.",
            )
        if avg_len < 120:
            return EvaluationOutput(
                verdict=Verdict.meeting,
                rationale="Answers showed solid, specific examples matching current-tier expectations.",
                recommendation="Look for opportunities to lead a small initiative end-to-end to build toward the next tier.",
            )
        return EvaluationOutput(
            verdict=Verdict.exceeding,
            rationale="Answers consistently showed depth and initiative beyond current-tier expectations.",
            recommendation="Seek out mentoring opportunities and larger-scope initiatives to formalize readiness for the next tier.",
        )
```

- [ ] **Step 6: Run tests to verify they pass**

Run (from `backend/`): `pytest tests/test_mock_provider.py -v`
Expected: PASS (5 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas.py backend/app/ai/__init__.py backend/app/ai/base.py backend/app/ai/mock.py backend/tests/test_mock_provider.py
git commit -m "feat: add AIProvider interface and MockAIProvider"
```

---

## Task 4: Employee lookup/seed helper

**Files:**
- Create: `backend/app/employees.py`
- Test: `backend/tests/test_employees.py`

**Interfaces:**
- Consumes: `app.models.Employee` (Task 2).
- Produces: `app.employees.get_or_seed_employee(db: Session) -> Employee` — idempotent: returns the existing single `Employee` row if one exists, otherwise creates and returns one named `"Jordan Lee"`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_employees.py
from sqlmodel import Session

from app.employees import get_or_seed_employee


def test_get_or_seed_employee_creates_once(db_session: Session):
    first = get_or_seed_employee(db_session)
    second = get_or_seed_employee(db_session)

    assert first.id == second.id
    assert first.name == "Jordan Lee"
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `pytest tests/test_employees.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.employees'`

- [ ] **Step 3: Write the helper**

```python
# backend/app/employees.py
from sqlmodel import Session, select

from app.models import Employee


def get_or_seed_employee(db: Session) -> Employee:
    employee = db.exec(select(Employee)).first()
    if employee is not None:
        return employee

    employee = Employee(name="Jordan Lee")
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `backend/`): `pytest tests/test_employees.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/employees.py backend/tests/test_employees.py
git commit -m "feat: add idempotent employee seed helper"
```

---

## Task 5: `POST /sessions` endpoint

**Files:**
- Modify: `backend/app/schemas.py` (add request/response models)
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/sessions.py`
- Modify: `backend/app/main.py` (include router)
- Create: `backend/tests/test_sessions_api.py`

**Interfaces:**
- Consumes: `app.employees.get_or_seed_employee` (Task 4), `app.ai.mock.MockAIProvider` (Task 3), `app.models.{Role, AssessmentSession, QAPair}` (Task 2), `app.db.get_session` (Task 2).
- Produces: `app.schemas.StartSessionRequest` (`role_title: str`), `app.schemas.SessionStartResponse` (`session_id: int`, `role_id: int`, `question: str`). Route `POST /sessions` registered on `app`, importable via `app.routers.sessions.router`.

- [ ] **Step 1: Add request/response schemas**

```python
# backend/app/schemas.py
# (append to the file created in Task 3)


class StartSessionRequest(BaseModel):
    role_title: str


class SessionStartResponse(BaseModel):
    session_id: int
    role_id: int
    question: str
```

- [ ] **Step 2: Write the failing API tests**

```python
# backend/tests/test_sessions_api.py
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run (from `backend/`): `pytest tests/test_sessions_api.py -v`
Expected: FAIL — `404 Not Found` for `POST /sessions` (route doesn't exist yet)

- [ ] **Step 4: Write the router**

```python
# backend/app/routers/__init__.py
```

```python
# backend/app/routers/sessions.py
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.ai.mock import MockAIProvider
from app.db import get_session
from app.employees import get_or_seed_employee
from app.models import QAPair, Role, AssessmentSession
from app.schemas import SessionStartResponse, StartSessionRequest

router = APIRouter(prefix="/sessions", tags=["sessions"])
ai_provider = MockAIProvider()


@router.post("", response_model=SessionStartResponse)
def start_session(body: StartSessionRequest, db: Session = Depends(get_session)) -> SessionStartResponse:
    employee = get_or_seed_employee(db)
    existing_roles = list(db.exec(select(Role)).all())
    match = ai_provider.match_or_create_role(body.role_title, existing_roles)

    if match.matched_role_id is not None:
        role = db.get(Role, match.matched_role_id)
        assert role is not None
    else:
        role = Role(title=body.role_title, rubric=match.rubric.model_dump())
        db.add(role)
        db.commit()
        db.refresh(role)

    session = AssessmentSession(employee_id=employee.id, role_id=role.id)
    db.add(session)
    db.commit()
    db.refresh(session)

    question = ai_provider.generate_next_question(role, [])
    qa = QAPair(session_id=session.id, order=0, question=question.question)
    db.add(qa)
    db.commit()

    return SessionStartResponse(session_id=session.id, role_id=role.id, question=question.question)
```

- [ ] **Step 5: Register the router**

```python
# backend/app/main.py
from fastapi import FastAPI

from app.db import create_db_and_tables
from app.routers import sessions

app = FastAPI(title="Employee Eval POC")


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(sessions.router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run (from `backend/`): `pytest tests/test_sessions_api.py -v`
Expected: PASS (2 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas.py backend/app/routers/__init__.py backend/app/routers/sessions.py backend/app/main.py backend/tests/test_sessions_api.py
git commit -m "feat: add POST /sessions endpoint"
```

---

## Task 6: `POST /sessions/{id}/answer` endpoint

**Files:**
- Modify: `backend/app/schemas.py` (add request/response models)
- Modify: `backend/app/routers/sessions.py` (add `submit_answer`)
- Modify: `backend/tests/test_sessions_api.py` (add tests)

**Interfaces:**
- Consumes: everything from Task 5, plus `app.models.{Evaluation, SessionStatus}` (Task 2), `app.config.settings.session_question_count` (Task 1).
- Produces: `app.schemas.AnswerRequest` (`answer: str`), `app.schemas.AnswerResponse` (`status: str`, `question: str | None`, `verdict: str | None`, `rationale: str | None`, `recommendation: str | None`). Route `POST /sessions/{session_id}/answer`. Both `start_session` and `submit_answer` wrap their `ai_provider` calls and raise `HTTPException(502, ...)` on failure, per the spec's "provider failures surface as a 502" requirement — leaving already-persisted state (the session, prior answers) untouched so a retry can pick up where it left off.

- [ ] **Step 1: Add request/response schemas**

```python
# backend/app/schemas.py
# (append)


class AnswerRequest(BaseModel):
    answer: str


class AnswerResponse(BaseModel):
    status: str
    question: str | None = None
    verdict: str | None = None
    rationale: str | None = None
    recommendation: str | None = None
```

- [ ] **Step 2: Write the failing tests**

```python
# backend/tests/test_sessions_api.py
# (append to the file from Task 5 — also add this import at the top of the file:
#  from app.models import AssessmentSession, SessionStatus)


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
```

- [ ] **Step 3: Run tests to verify they fail**

Run (from `backend/`): `pytest tests/test_sessions_api.py -v`
Expected: FAIL — `404 Not Found` for `POST /sessions/{id}/answer`

- [ ] **Step 4: Implement the endpoint**

```python
# backend/app/routers/sessions.py
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.ai.mock import MockAIProvider
from app.db import get_session
from app.employees import get_or_seed_employee
from app.models import Evaluation, QAPair, Role, AssessmentSession, SessionStatus
from app.config import settings
from app.schemas import AnswerRequest, AnswerResponse, SessionStartResponse, StartSessionRequest

router = APIRouter(prefix="/sessions", tags=["sessions"])
ai_provider = MockAIProvider()


@router.post("", response_model=SessionStartResponse)
def start_session(body: StartSessionRequest, db: Session = Depends(get_session)) -> SessionStartResponse:
    employee = get_or_seed_employee(db)
    existing_roles = list(db.exec(select(Role)).all())
    try:
        match = ai_provider.match_or_create_role(body.role_title, existing_roles)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="AI provider failed to resolve role") from exc

    if match.matched_role_id is not None:
        role = db.get(Role, match.matched_role_id)
        assert role is not None
    else:
        role = Role(title=body.role_title, rubric=match.rubric.model_dump())
        db.add(role)
        db.commit()
        db.refresh(role)

    session = AssessmentSession(employee_id=employee.id, role_id=role.id)
    db.add(session)
    db.commit()
    db.refresh(session)

    try:
        question = ai_provider.generate_next_question(role, [])
    except Exception as exc:
        raise HTTPException(status_code=502, detail="AI provider failed to generate a question") from exc
    qa = QAPair(session_id=session.id, order=0, question=question.question)
    db.add(qa)
    db.commit()

    return SessionStartResponse(session_id=session.id, role_id=role.id, question=question.question)


@router.post("/{session_id}/answer", response_model=AnswerResponse)
def submit_answer(session_id: int, body: AnswerRequest, db: Session = Depends(get_session)) -> AnswerResponse:
    session = db.get(AssessmentSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == SessionStatus.completed:
        raise HTTPException(status_code=409, detail="Session already completed")

    qa_pairs = list(
        db.exec(select(QAPair).where(QAPair.session_id == session_id).order_by(QAPair.order)).all()
    )
    current_qa = qa_pairs[-1]
    current_qa.answer = body.answer
    db.add(current_qa)
    db.commit()

    role = db.get(Role, session.role_id)
    assert role is not None

    if len(qa_pairs) >= settings.session_question_count:
        try:
            evaluation_result = ai_provider.evaluate_session(role, qa_pairs)
        except Exception as exc:
            raise HTTPException(status_code=502, detail="AI provider failed to evaluate the session") from exc

        evaluation = Evaluation(
            session_id=session.id,
            verdict=evaluation_result.verdict,
            rationale=evaluation_result.rationale,
            recommendation=evaluation_result.recommendation,
        )
        db.add(evaluation)
        session.status = SessionStatus.completed
        session.completed_at = datetime.utcnow()
        db.add(session)
        db.commit()

        return AnswerResponse(
            status="completed",
            verdict=evaluation_result.verdict.value,
            rationale=evaluation_result.rationale,
            recommendation=evaluation_result.recommendation,
        )

    try:
        next_question = ai_provider.generate_next_question(role, qa_pairs)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="AI provider failed to generate a question") from exc
    next_qa = QAPair(session_id=session.id, order=len(qa_pairs), question=next_question.question)
    db.add(next_qa)
    db.commit()

    return AnswerResponse(status="in_progress", question=next_question.question)
```

> Note: the answer to the current question (`current_qa.answer = body.answer`) is committed *before* the provider call, so a 502 here still preserves the just-submitted answer — a retry re-sends the same request and only the question-generation/evaluation step re-runs, nothing is lost.

- [ ] **Step 5: Run tests to verify they pass**

Run (from `backend/`): `pytest tests/test_sessions_api.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas.py backend/app/routers/sessions.py backend/tests/test_sessions_api.py
git commit -m "feat: add POST /sessions/{id}/answer endpoint with evaluation and 409 handling"
```

---

## Task 7: `GET /sessions/{id}` endpoint

**Files:**
- Modify: `backend/app/schemas.py` (add `QAPairRead`, `SessionRead`)
- Modify: `backend/app/routers/sessions.py` (add `get_session_detail`)
- Modify: `backend/tests/test_sessions_api.py` (add tests)

**Interfaces:**
- Consumes: everything from Task 6.
- Produces: `app.schemas.QAPairRead` (`order: int`, `question: str`, `answer: str | None`), `app.schemas.SessionRead` (`id: int`, `status: str`, `role_title: str`, `qa_pairs: list[QAPairRead]`, `verdict: str | None`, `rationale: str | None`, `recommendation: str | None`). Route `GET /sessions/{session_id}`.

- [ ] **Step 1: Add response schemas**

```python
# backend/app/schemas.py
# (append)


class QAPairRead(BaseModel):
    order: int
    question: str
    answer: str | None


class SessionRead(BaseModel):
    id: int
    status: str
    role_title: str
    qa_pairs: list[QAPairRead]
    verdict: str | None = None
    rationale: str | None = None
    recommendation: str | None = None
```

- [ ] **Step 2: Write the failing tests**

```python
# backend/tests/test_sessions_api.py
# (append)


def test_get_session_reflects_in_progress_state(db_session: Session):
    client = make_client(db_session)
    start = client.post("/sessions", json={"role_title": "Software Engineer"})
    session_id = start.json()["session_id"]

    response = client.get(f"/sessions/{session_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["role_title"] == "Software Engineer"
    assert len(body["qa_pairs"]) == 1
    assert body["verdict"] is None


def test_get_session_reflects_completed_state(db_session: Session):
    client = make_client(db_session)
    start = client.post("/sessions", json={"role_title": "Software Engineer"})
    session_id = start.json()["session_id"]
    for _ in range(5):
        client.post(f"/sessions/{session_id}/answer", json={"answer": "a reasonably detailed answer"})

    response = client.get(f"/sessions/{session_id}")

    body = response.json()
    assert body["status"] == "completed"
    assert len(body["qa_pairs"]) == 5
    assert body["verdict"] in {"below", "meeting", "exceeding"}
```

- [ ] **Step 3: Run tests to verify they fail**

Run (from `backend/`): `pytest tests/test_sessions_api.py -v`
Expected: FAIL — `404 Not Found` for `GET /sessions/{id}`

- [ ] **Step 4: Implement the endpoint**

```python
# backend/app/routers/sessions.py
# (add to the router defined in Task 6 — `Evaluation` is already imported at the top of the
#  file from Task 6, so only add this new import:)

from app.schemas import QAPairRead, SessionRead


@router.get("/{session_id}", response_model=SessionRead)
def get_session_detail(session_id: int, db: Session = Depends(get_session)) -> SessionRead:
    session = db.get(AssessmentSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    role = db.get(Role, session.role_id)
    assert role is not None

    qa_pairs = list(
        db.exec(select(QAPair).where(QAPair.session_id == session_id).order_by(QAPair.order)).all()
    )
    evaluation = db.exec(select(Evaluation).where(Evaluation.session_id == session_id)).first()

    return SessionRead(
        id=session.id,
        status=session.status.value,
        role_title=role.title,
        qa_pairs=[QAPairRead(order=qa.order, question=qa.question, answer=qa.answer) for qa in qa_pairs],
        verdict=evaluation.verdict.value if evaluation else None,
        rationale=evaluation.rationale if evaluation else None,
        recommendation=evaluation.recommendation if evaluation else None,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run (from `backend/`): `pytest tests/ -v`
Expected: PASS (all tests across all files so far)

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas.py backend/app/routers/sessions.py backend/tests/test_sessions_api.py
git commit -m "feat: add GET /sessions/{id} endpoint"
```

---

## Task 8: Frontend scaffold (Vite + React + TypeScript + Tailwind)

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/index.css`
- Create: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: nothing (frontend scaffold task).
- Produces: a runnable Vite dev server (`npm run dev`) and a `App` root component in `frontend/src/App.tsx`, ready for Task 9/10 to build on.

- [ ] **Step 1: Scaffold the Vite React-TS project**

Run (from `frontend/` — create the directory first if empty): `npm create vite@latest . -- --template react-ts`
Expected: project files created (accept overwriting an empty directory if prompted).

- [ ] **Step 2: Install Tailwind CSS**

Run (from `frontend/`): `npm install -D tailwindcss postcss autoprefixer && npx tailwindcss init -p`
Expected: `tailwind.config.js` and `postcss.config.js` created.

- [ ] **Step 3: Configure Tailwind content paths**

```javascript
// frontend/tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};
```

- [ ] **Step 4: Add Tailwind directives**

```css
/* frontend/src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 5: Replace the placeholder App component**

```tsx
// frontend/src/App.tsx
export default function App() {
  return <div className="p-6 text-lg">Employee Eval POC</div>;
}
```

- [ ] **Step 6: Run the dev server to verify it works**

Run (from `frontend/`): `npm run dev`
Expected: server starts on `http://localhost:5173`, page shows "Employee Eval POC" styled with Tailwind's `p-6 text-lg` (larger text, padding) — verify by opening the URL.

- [ ] **Step 7: Run a production build to verify it compiles**

Run (from `frontend/`): `npm run build`
Expected: build completes with no TypeScript or bundling errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold Vite + React + TypeScript + Tailwind frontend"
```

---

## Task 9: API client and TypeScript types

**Files:**
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api.ts`
- Create: `frontend/.env.development`

**Interfaces:**
- Consumes: backend response shapes from `app.schemas` (Tasks 5-7): `SessionStartResponse`, `AnswerResponse`, `SessionRead`, `QAPairRead`.
- Produces: `startSession(roleTitle: string): Promise<SessionStartResponse>`, `submitAnswer(sessionId: number, answer: string): Promise<AnswerResponse>`, `getSession(sessionId: number): Promise<SessionRead>` from `frontend/src/api.ts`.

- [ ] **Step 1: Write TypeScript types matching the backend schemas**

```typescript
// frontend/src/types.ts
export type Verdict = "below" | "meeting" | "exceeding";

export interface SessionStartResponse {
  session_id: number;
  role_id: number;
  question: string;
}

export interface AnswerResponse {
  status: "in_progress" | "completed";
  question?: string | null;
  verdict?: Verdict | null;
  rationale?: string | null;
  recommendation?: string | null;
}

export interface QAPairRead {
  order: number;
  question: string;
  answer: string | null;
}

export interface SessionRead {
  id: number;
  status: "in_progress" | "completed";
  role_title: string;
  qa_pairs: QAPairRead[];
  verdict?: Verdict | null;
  rationale?: string | null;
  recommendation?: string | null;
}
```

- [ ] **Step 2: Set the backend base URL for local dev**

```text
# frontend/.env.development
VITE_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 3: Write the API client**

```typescript
// frontend/src/api.ts
import type { AnswerResponse, SessionRead, SessionStartResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function startSession(roleTitle: string): Promise<SessionStartResponse> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role_title: roleTitle }),
  });
  if (!res.ok) {
    throw new Error(`Failed to start session: ${res.status}`);
  }
  return res.json();
}

export async function submitAnswer(sessionId: number, answer: string): Promise<AnswerResponse> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer }),
  });
  if (res.status === 409) {
    throw new Error("This session has already been completed.");
  }
  if (!res.ok) {
    throw new Error(`Failed to submit answer: ${res.status}`);
  }
  return res.json();
}

export async function getSession(sessionId: number): Promise<SessionRead> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch session: ${res.status}`);
  }
  return res.json();
}
```

- [ ] **Step 4: Verify the project still type-checks and builds**

Run (from `frontend/`): `npx tsc --noEmit && npm run build`
Expected: both complete with no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types.ts frontend/src/api.ts frontend/.env.development
git commit -m "feat: add API client and TypeScript types matching backend schemas"
```

---

## Task 10: Three screens wired end-to-end

**Files:**
- Create: `frontend/src/screens/StartScreen.tsx`
- Create: `frontend/src/screens/QuestionScreen.tsx`
- Create: `frontend/src/screens/ResultsScreen.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `startSession`, `submitAnswer` from `frontend/src/api.ts` (Task 9); types from `frontend/src/types.ts` (Task 9).
- Produces: a working three-screen flow in `App.tsx`, with `data-testid` attributes (`role-title-input`, `start-button`, `question-text`, `answer-input`, `submit-answer-button`, `verdict`, `rationale`, `recommendation`) that Task 11/12's Playwright tests hook into.

- [ ] **Step 1: Write the Start screen**

```tsx
// frontend/src/screens/StartScreen.tsx
import { useState } from "react";

interface StartScreenProps {
  onStart: (roleTitle: string) => void;
  isLoading: boolean;
  error: string | null;
}

export function StartScreen({ onStart, isLoading, error }: StartScreenProps) {
  const [roleTitle, setRoleTitle] = useState("");

  return (
    <div className="max-w-md mx-auto mt-16 p-6">
      <h1 className="text-2xl font-semibold mb-4">Employee Skill Assessment</h1>
      <label htmlFor="role-title" className="block mb-2 text-sm font-medium">
        What's your current role?
      </label>
      <input
        id="role-title"
        data-testid="role-title-input"
        className="w-full border rounded px-3 py-2 mb-4"
        value={roleTitle}
        onChange={(e) => setRoleTitle(e.target.value)}
        placeholder="e.g. Software Engineer"
      />
      {error && <p className="text-red-600 mb-4">{error}</p>}
      <button
        data-testid="start-button"
        className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        disabled={isLoading || roleTitle.trim().length === 0}
        onClick={() => onStart(roleTitle.trim())}
      >
        {isLoading ? "Starting..." : "Start Assessment"}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Write the Question screen**

```tsx
// frontend/src/screens/QuestionScreen.tsx
import { useState } from "react";

interface QuestionScreenProps {
  question: string;
  onSubmit: (answer: string) => void;
  isLoading: boolean;
  error: string | null;
}

export function QuestionScreen({ question, onSubmit, isLoading, error }: QuestionScreenProps) {
  const [answer, setAnswer] = useState("");

  return (
    <div className="max-w-md mx-auto mt-16 p-6">
      <p data-testid="question-text" className="text-lg font-medium mb-4">
        {question}
      </p>
      <textarea
        data-testid="answer-input"
        className="w-full border rounded px-3 py-2 mb-4"
        rows={4}
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
      />
      {error && <p className="text-red-600 mb-4">{error}</p>}
      <button
        data-testid="submit-answer-button"
        className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        disabled={isLoading || answer.trim().length === 0}
        onClick={() => {
          const submitted = answer.trim();
          setAnswer("");
          onSubmit(submitted);
        }}
      >
        {isLoading ? "Submitting..." : "Submit Answer"}
      </button>
    </div>
  );
}
```

- [ ] **Step 3: Write the Results screen**

```tsx
// frontend/src/screens/ResultsScreen.tsx
import type { Verdict } from "../types";

interface ResultsScreenProps {
  verdict: Verdict;
  rationale: string;
  recommendation: string;
}

const VERDICT_LABEL: Record<Verdict, string> = {
  below: "Below Expectations",
  meeting: "Meeting Expectations",
  exceeding: "Exceeding Expectations",
};

export function ResultsScreen({ verdict, rationale, recommendation }: ResultsScreenProps) {
  return (
    <div className="max-w-md mx-auto mt-16 p-6">
      <h1 data-testid="verdict" className="text-2xl font-semibold mb-4">
        {VERDICT_LABEL[verdict]}
      </h1>
      <p className="text-sm text-gray-600 mb-1 font-medium">Rationale</p>
      <p data-testid="rationale" className="mb-4">
        {rationale}
      </p>
      <p className="text-sm text-gray-600 mb-1 font-medium">Recommended next step</p>
      <p data-testid="recommendation">{recommendation}</p>
    </div>
  );
}
```

- [ ] **Step 4: Wire the screens together in App**

```tsx
// frontend/src/App.tsx
import { useState } from "react";

import { startSession, submitAnswer } from "./api";
import { QuestionScreen } from "./screens/QuestionScreen";
import { ResultsScreen } from "./screens/ResultsScreen";
import { StartScreen } from "./screens/StartScreen";
import type { Verdict } from "./types";

type Screen =
  | { kind: "start" }
  | { kind: "question"; sessionId: number; question: string }
  | { kind: "results"; verdict: Verdict; rationale: string; recommendation: string };

export default function App() {
  const [screen, setScreen] = useState<Screen>({ kind: "start" });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleStart(roleTitle: string) {
    setIsLoading(true);
    setError(null);
    try {
      const res = await startSession(roleTitle);
      setScreen({ kind: "question", sessionId: res.session_id, question: res.question });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleAnswer(answer: string) {
    if (screen.kind !== "question") return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await submitAnswer(screen.sessionId, answer);
      if (res.status === "completed" && res.verdict && res.rationale && res.recommendation) {
        setScreen({ kind: "results", verdict: res.verdict, rationale: res.rationale, recommendation: res.recommendation });
      } else if (res.question) {
        setScreen({ kind: "question", sessionId: screen.sessionId, question: res.question });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  }

  if (screen.kind === "start") {
    return <StartScreen onStart={handleStart} isLoading={isLoading} error={error} />;
  }
  if (screen.kind === "question") {
    return <QuestionScreen question={screen.question} onSubmit={handleAnswer} isLoading={isLoading} error={error} />;
  }
  return <ResultsScreen verdict={screen.verdict} rationale={screen.rationale} recommendation={screen.recommendation} />;
}
```

- [ ] **Step 5: Manually verify the golden path in the browser**

Run: `docker compose up -d`, then (from `backend/`) `uvicorn app.main:app --reload --port 8000`, then (from `frontend/`) `npm run dev`.
Open `http://localhost:5173`, type a role, click Start, answer all 5 questions, confirm the Results screen renders a verdict, rationale, and recommendation.
Expected: full flow works with no console errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/screens frontend/src/App.tsx
git commit -m "feat: wire start/question/results screens to the backend API"
```

---

## Task 11: Playwright setup + golden path e2e test

**Files:**
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/golden-path.spec.ts`
- Modify: `frontend/package.json` (add `@playwright/test` dev dependency and `test:e2e` script)

**Interfaces:**
- Consumes: the running app from Task 10 (`data-testid` attributes on Start/Question/Results screens), the running backend from Tasks 5-7.
- Produces: a Playwright test suite runnable via `npm run test:e2e` from `frontend/`.

- [ ] **Step 1: Install Playwright**

Run (from `frontend/`): `npm install -D @playwright/test && npx playwright install --with-deps chromium`
Expected: install completes; Chromium browser downloaded.

- [ ] **Step 2: Add the `test:e2e` script**

```json
// frontend/package.json
// add inside "scripts"
"test:e2e": "playwright test"
```

- [ ] **Step 3: Write the Playwright config**

```typescript
// frontend/playwright.config.ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  use: {
    baseURL: "http://localhost:5173",
  },
});
```

- [ ] **Step 4: Write the golden path test**

```typescript
// frontend/e2e/golden-path.spec.ts
import { expect, test } from "@playwright/test";

test("employee completes assessment and sees a verdict", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("role-title-input").fill("Software Engineer");
  await page.getByTestId("start-button").click();

  for (let i = 0; i < 5; i++) {
    await expect(page.getByTestId("question-text")).toBeVisible();
    await page
      .getByTestId("answer-input")
      .fill(
        "This is a detailed example answer describing a specific situation, the actions I took, and the outcome I achieved."
      );
    await page.getByTestId("submit-answer-button").click();
  }

  await expect(page.getByTestId("verdict")).toBeVisible();
  await expect(page.getByTestId("rationale")).toBeVisible();
  await expect(page.getByTestId("recommendation")).toBeVisible();
});
```

- [ ] **Step 5: Run the test against the running stack**

Ensure `docker compose up -d`, the backend (`uvicorn app.main:app --reload --port 8000` from `backend/`), and the frontend (`npm run dev` from `frontend/`) are all running, then run (from `frontend/`): `npm run test:e2e`
Expected: PASS (1 test)

- [ ] **Step 6: Commit**

```bash
git add frontend/playwright.config.ts frontend/e2e/golden-path.spec.ts frontend/package.json frontend/package-lock.json
git commit -m "test: add Playwright golden-path e2e test"
```

---

## Task 12: Playwright edge-case tests

**Files:**
- Create: `frontend/e2e/completed-session-conflict.spec.ts`
- Create: `frontend/e2e/role-reuse.spec.ts`

**Interfaces:**
- Consumes: the running app and backend (Task 11 setup), `role_id` field on `SessionStartResponse` (Task 5).
- Produces: two additional passing Playwright tests.

- [ ] **Step 1: Write the completed-session 409 test**

```typescript
// frontend/e2e/completed-session-conflict.spec.ts
import { expect, test } from "@playwright/test";

test("answering a completed session returns 409", async ({ page, request }) => {
  await page.goto("/");
  await page.getByTestId("role-title-input").fill("Software Engineer");

  const [startResponse] = await Promise.all([
    page.waitForResponse((res) => res.url().endsWith("/sessions") && res.request().method() === "POST"),
    page.getByTestId("start-button").click(),
  ]);
  const { session_id: sessionId } = await startResponse.json();

  for (let i = 0; i < 5; i++) {
    await expect(page.getByTestId("question-text")).toBeVisible();
    await page.getByTestId("answer-input").fill("A detailed answer with specific, concrete examples of my work.");
    await page.getByTestId("submit-answer-button").click();
  }
  await expect(page.getByTestId("verdict")).toBeVisible();

  const res = await request.post(`http://localhost:8000/sessions/${sessionId}/answer`, {
    data: { answer: "late answer" },
  });
  expect(res.status()).toBe(409);
});
```

- [ ] **Step 2: Write the role-reuse test**

```typescript
// frontend/e2e/role-reuse.spec.ts
import { expect, test } from "@playwright/test";

test("a role title with an overlapping keyword reuses the existing role", async ({ request }) => {
  const first = await request.post("http://localhost:8000/sessions", {
    data: { role_title: "Software Engineer" },
  });
  expect(first.ok()).toBeTruthy();
  const firstBody = await first.json();

  const second = await request.post("http://localhost:8000/sessions", {
    data: { role_title: "Software Developer" },
  });
  expect(second.ok()).toBeTruthy();
  const secondBody = await second.json();

  expect(secondBody.role_id).toBe(firstBody.role_id);
});
```

- [ ] **Step 3: Run all e2e tests**

Ensure `docker compose up -d`, backend, and frontend are running, then run (from `frontend/`): `npm run test:e2e`
Expected: PASS (3 tests total: golden path, completed-session conflict, role reuse)

- [ ] **Step 4: Commit**

```bash
git add frontend/e2e/completed-session-conflict.spec.ts frontend/e2e/role-reuse.spec.ts
git commit -m "test: add Playwright edge-case tests for session conflict and role reuse"
```
