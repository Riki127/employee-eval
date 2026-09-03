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


class StartSessionRequest(BaseModel):
    role_title: str


class SessionStartResponse(BaseModel):
    session_id: int
    role_id: int
    question: str


class AnswerRequest(BaseModel):
    answer: str


class AnswerResponse(BaseModel):
    status: str
    question: str | None = None
    verdict: str | None = None
    rationale: str | None = None
    recommendation: str | None = None
