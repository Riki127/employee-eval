from pydantic import BaseModel

import anthropic

from app.config import settings
from app.models import QAPair, Role
from app.schemas import EvaluationOutput, QuestionOutput, RoleMatchResult, RoleRubric

_MODEL = "claude-sonnet-5"


class _RoleMatchDecision(BaseModel):
    matched_role_id: int | None


class AnthropicAIProvider:
    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        if client is not None:
            self._client = client
        elif settings.anthropic_api_key:
            # Explicit key from Settings (e.g. loaded from backend/.env), since the SDK's
            # own automatic os.environ lookup can't see values pydantic-settings read
            # from a .env file rather than the real process environment.
            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        else:
            # Falls back to the SDK's own credential resolution (ANTHROPIC_API_KEY set
            # directly in the process environment, `ant auth login`, etc.).
            self._client = anthropic.Anthropic()

    def match_or_create_role(self, title: str, existing_roles: list[Role]) -> RoleMatchResult:
        if existing_roles:
            existing_lines = "\n".join(f"- id={role.id}: {role.title}" for role in existing_roles)
            decision_prompt = (
                "You are helping an employee-assessment tool decide whether a newly typed job "
                "role title is effectively the same job as an existing one, based on "
                "responsibilities and skills, not just how similar the title text looks.\n\n"
                f"New role title: {title!r}\n\n"
                f"Existing roles:\n{existing_lines}\n\n"
                "If the new title is effectively the same role as one of the existing ones, set "
                "matched_role_id to that role's id. If it is a genuinely different role, set "
                "matched_role_id to null."
            )
            decision_response = self._client.messages.parse(
                model=_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": decision_prompt}],
                output_format=_RoleMatchDecision,
            )
            decision = decision_response.parsed_output

            if decision.matched_role_id is not None:
                matched_role = next(
                    (role for role in existing_roles if role.id == decision.matched_role_id), None
                )
                if matched_role is None:
                    raise RuntimeError(
                        f"AI provider matched to unknown role id {decision.matched_role_id}"
                    )
                return RoleMatchResult(
                    matched_role_id=matched_role.id, rubric=RoleRubric(**matched_role.rubric)
                )

        rubric_prompt = (
            f"Infer a career-ladder rubric for the job role {title!r}. Describe what's expected "
            "of someone at their current tier, what's expected at the next tier up, and give a "
            "one-sentence summary of the career ladder between the two."
        )
        rubric_response = self._client.messages.parse(
            model=_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": rubric_prompt}],
            output_format=RoleRubric,
        )
        return RoleMatchResult(matched_role_id=None, rubric=rubric_response.parsed_output)

    def generate_next_question(self, role: Role, qa_history: list[QAPair]) -> QuestionOutput:
        transcript = _format_transcript(qa_history) or "(no questions asked yet)"
        prompt = (
            f'You are assessing an employee for the role "{role.title}".\n'
            f"Role expectations: {role.rubric}\n\n"
            f"Conversation so far:\n{transcript}\n\n"
            "Ask the single next role-relevant question that will help you judge whether this "
            "person is below, meeting, or exceeding expectations for this role. Build on their "
            "prior answers rather than repeating ground already covered."
        )
        response = self._client.messages.parse(
            model=_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
            output_format=QuestionOutput,
        )
        return response.parsed_output

    def evaluate_session(self, role: Role, qa_history: list[QAPair]) -> EvaluationOutput:
        transcript = _format_transcript(qa_history)
        prompt = (
            f'You are evaluating an employee assessment for the role "{role.title}".\n'
            f"Role expectations: {role.rubric}\n\n"
            f"Full conversation:\n{transcript}\n\n"
            "Decide whether this person's answers are below, meeting, or exceeding expectations "
            "for this role's current tier. Give a concise rationale grounded in specific answers, "
            "and a concrete recommendation: if below, what to learn to close the gap to the "
            "current tier; if meeting or exceeding, what to learn to reach the next tier."
        )
        response = self._client.messages.parse(
            model=_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
            output_format=EvaluationOutput,
        )
        return response.parsed_output


def _format_transcript(qa_history: list[QAPair]) -> str:
    lines = []
    for qa in qa_history:
        lines.append(f"Q{qa.order + 1}: {qa.question}")
        if qa.answer:
            lines.append(f"A{qa.order + 1}: {qa.answer}")
    return "\n".join(lines)
