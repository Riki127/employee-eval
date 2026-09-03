# POC: Full Vertical Slice — Design Spec

Date: 2026-09-03

## Purpose

Prove out the core loop of the employee-eval product end-to-end: an employee
types their current role, answers a dynamic AI-generated questionnaire, and
receives a structured evaluation (below/meeting/exceeding expectations) with
a tailored learning recommendation. See [docs/product.md](../../product.md)
for the full product context and [AGENTS.md](../../../AGENTS.md) for stack
and conventions.

This is a proof of concept, not production software. Scope is deliberately
narrow: one implicit user, no auth, no admin tooling, AI calls mocked (real
Anthropic API integration is a follow-up, not part of this POC).

## Goals

- A person can open the app, type a role title, answer a fixed-length
  AI-generated questionnaire that adapts to their prior answers, and see a
  verdict + rationale + learning recommendation — fully working end-to-end.
- The AI layer is mocked (zero API cost) but built behind an interface that
  a real Anthropic-backed implementation can drop into later without
  changing any other part of the app.
- Typing a role that's a near-match to an existing one reuses its rubric;
  typing a genuinely new role gets one generated (mocked) on the spot.

## Non-goals (out of scope for this POC)

- Authentication, authorization, multiple real users.
- Admin UI for managing roles/rubrics.
- Manager/admin review views of past sessions (product doc describes this;
  not built here).
- Real LLM calls (Anthropic/OpenAI) — provider interface is designed for
  it, but the POC ships with the mock implementation only.
- Automated frontend unit tests — covered by Playwright e2e instead.

## Architecture

FastAPI backend + PostgreSQL (via SQLModel) + React/TypeScript/Tailwind
frontend, communicating over a small REST API.

The AI layer sits behind a single `AIProvider` interface with three
methods:

```python
class AIProvider(Protocol):
    def match_or_create_role(self, title: str, existing_roles: list[Role]) -> Role: ...
    def generate_next_question(self, role: Role, qa_history: list[QAPair]) -> QuestionOutput: ...
    def evaluate_session(self, role: Role, qa_history: list[QAPair]) -> EvaluationOutput: ...
```

`MockAIProvider` implements all three with deterministic, canned logic (see
below). A future `AnthropicAIProvider` implements the same interface using
real structured-output calls. The rest of the app (API routes, DB layer,
frontend) never knows which implementation is active — it's selected once,
e.g. via a settings flag / dependency injection in FastAPI.

## Data model (SQLModel / Postgres)

- **Role** — `id`, `title` (as originally typed), `rubric` (JSON: current-
  tier expectations, next-tier expectations, brief description of the
  inferred career ladder), `created_at`.
- **Employee** — `id`, `name`, `role_id`. Single hardcoded/seeded row for
  this POC (no auth, no employee-creation flow).
- **Session** — `id`, `employee_id`, `role_id`, `status`
  (`in_progress` / `completed`), `created_at`, `completed_at`.
- **QAPair** — `id`, `session_id`, `order` (question index), `question`,
  `answer`, `created_at`.
- **Evaluation** — `id`, `session_id` (1:1), `verdict`
  (`below` / `meeting` / `exceeding`), `rationale`, `recommendation`,
  `created_at`.

## AI provider details

### `match_or_create_role(title, existing_roles)`

- Mock behavior: case-insensitive substring/keyword match against existing
  role titles (e.g. "solution developer" vs. "software engineer" sharing
  "developer"/"engineer"-adjacent keywords is intentionally crude for the
  POC — this is a placeholder for the real LLM-judged matching described in
  the product doc, not a faithful simulation of it).
- No match found → generate a canned rubric template (fixed structure:
  generic current-tier and next-tier expectations), labeled with the typed
  title, and persist it as a new `Role`.

### `generate_next_question(role, qa_history)`

- Mock behavior: returns the next question from a small fixed pool of
  generic role-relevant questions (order fixed, not actually adaptive in
  the mock — real adaptiveness is a property of the future real provider,
  not simulated here). Pool size must be >= the fixed session length below.

### `evaluate_session(role, qa_history)`

- Mock behavior: simple deterministic rule (e.g. based on average answer
  length or a fixed canned verdict) producing a valid `EvaluationOutput` —
  verdict + rationale + recommendation — so the full response shape and
  downstream UI are exercised realistically, even though the judgment
  itself is not real.

### Session length

Fixed at **5 questions** per session (constant in backend config). After the
5th answer is submitted, `evaluate_session` runs instead of generating
another question.

## API

- `POST /sessions` — body `{ role_title: string }`. Resolves/creates the
  `Role` via `match_or_create_role`, creates the `Employee`'s `Session`,
  generates and returns the first question.
- `POST /sessions/{id}/answer` — body `{ answer: string }`. Persists the
  answer to the current `QAPair`, reloads QA history, and either returns
  the next question (if fewer than 5 answered) or runs `evaluate_session`
  and returns the final verdict/rationale/recommendation, marking the
  session `completed`.
- `GET /sessions/{id}` — returns full session state (questions asked so
  far, answers given, verdict if completed). Used for page reload and
  viewing a finished result.

All requests/responses are Pydantic-validated. Answering a session that is
already `completed` returns `409 Conflict`.

## Frontend

Three screens, plain React state (no state-management library needed at
this scope):

1. **Start** — text input: "What's your current role?" → `POST /sessions`.
2. **Question loop** — shows current question, free-text answer input,
   submit → `POST /sessions/{id}/answer`, renders next question or
   transitions to Results.
3. **Results** — verdict, rationale, recommendation.

## Error handling

- Pydantic validates every request/response boundary (400 on shape
  mismatch).
- Answering a completed session → `409`.
- Provider failures (exercised even against the mock, to prove the path
  works) surface as a `502`-style error from the API; the frontend shows a
  retry affordance rather than losing the in-progress session.

## Testing

- **Backend**: pytest against the API routes and both `AIProvider` methods
  on `MockAIProvider` (fully deterministic, straightforward to assert on).
- **Frontend/e2e**: Playwright (`@playwright/test`) as a real dev
  dependency, with a suite in the repo covering:
  - Golden path: start → type a role → answer all 5 questions → see
    verdict/rationale/recommendation.
  - Completed-session `409` edge case.
  - Typing a role that matches an existing seeded role reuses its rubric
    (observable via the same rubric-derived question pool being asked).

## Open questions for after the POC

- What does real LLM-judged role matching look like in practice (replacing
  the mock's crude keyword match)? Tracked in [docs/product.md](../../product.md).
- Real Anthropic API integration (`AnthropicAIProvider`), including cost
  controls.
- Auth, multi-user, manager/admin views — all deferred per Non-goals above.
