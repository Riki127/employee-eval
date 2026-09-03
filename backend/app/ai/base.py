from typing import Protocol

from app.models import QAPair, Role
from app.schemas import EvaluationOutput, QuestionOutput, RoleMatchResult


class AIProvider(Protocol):
    def match_or_create_role(self, title: str, existing_roles: list[Role]) -> RoleMatchResult: ...

    def generate_next_question(self, role: Role, qa_history: list[QAPair]) -> QuestionOutput: ...

    def evaluate_session(self, role: Role, qa_history: list[QAPair]) -> EvaluationOutput: ...
