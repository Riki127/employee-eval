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
