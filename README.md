# Employee Eval POC

A vertical-slice proof of concept for an AI-assisted employee assessment flow: pick a
role, answer five generated questions, get a verdict with a rationale and a
recommendation.

Main reason for this project is to learn Agentic AI Engineering

- **Backend:** FastAPI + SQLModel + Postgres (`backend/`)
- **Frontend:** React + TypeScript + Vite + Tailwind (`frontend/`)
- **AI provider:** a deterministic mock (`backend/app/ai/mock.py`), injected via a
  FastAPI dependency (`app.ai.get_ai_provider`) so a real provider can be swapped in
  without touching the routes.

## Prerequisites

- Docker Desktop (for the Postgres container)
- Python 3.11+
- Node.js 20+

## 1. Start Postgres

From the repository root:

```bash
docker compose up -d
```

This runs `postgres:16` on `localhost:5432` with user/password `postgres/postgres` and
the database `employee_eval`.

## 2. Backend

From `backend/`:

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows; on macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

The API listens on `http://localhost:8000` (`GET /health` returns `{"status":"ok"}`).
Tables are created automatically on startup.

The database URL can be overridden with the `DATABASE_URL` environment variable; it
defaults to `postgresql+psycopg://postgres:postgres@localhost:5432/employee_eval`.

## 3. Frontend

From `frontend/`, in a second terminal:

```bash
npm install
npm run dev
```

The dev server listens on `http://localhost:5173`. It calls the backend at
`http://localhost:8000` by default; override with `VITE_API_BASE_URL`.

## 4. Use the app

Open <http://localhost:5173>, enter a role title, and answer the five questions.

## Running the tests

### Backend unit/API tests

Postgres must be running. From `backend/`:

```bash
pytest tests/ -v
```

These use their own `employee_eval_test` database (created automatically on first
run), so they are safe to run while the dev server and the e2e suite are using
`employee_eval`.

### End-to-end tests

Playwright drives the real stack, so Postgres, the backend (port 8000) and the
frontend dev server (port 5173) all have to be running first. Then, from `frontend/`:

```bash
npx playwright install chromium   # first run only
npm run test:e2e
```
