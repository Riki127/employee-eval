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
