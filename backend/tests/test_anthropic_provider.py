from unittest.mock import MagicMock

import pytest

from app.ai.anthropic_provider import AnthropicAIProvider
from app.models import QAPair, Role, Verdict
from app.schemas import EvaluationOutput, QuestionOutput, RoleRubric


def make_role(id: int, title: str, rubric: dict | None = None) -> Role:
    return Role(
        id=id,
        title=title,
        rubric=rubric
        or {"current_tier_expectations": [], "next_tier_expectations": [], "career_ladder_summary": ""},
    )


def make_qa(order: int, question: str, answer: str | None) -> QAPair:
    return QAPair(id=order, session_id=1, order=order, question=question, answer=answer)


def make_fake_client(*parsed_outputs):
    client = MagicMock()
    client.messages.parse.side_effect = [MagicMock(parsed_output=output) for output in parsed_outputs]
    return client


class _MatchDecision:
    def __init__(self, matched_role_id: int | None):
        self.matched_role_id = matched_role_id


def test_match_or_create_role_with_no_existing_roles_skips_match_call_and_infers_rubric():
    rubric = RoleRubric(current_tier_expectations=["a"], next_tier_expectations=["b"], career_ladder_summary="c")
    client = make_fake_client(rubric)
    provider = AnthropicAIProvider(client=client)

    result = provider.match_or_create_role("Software Engineer", [])

    assert result.matched_role_id is None
    assert result.rubric == rubric
    assert client.messages.parse.call_count == 1


def test_match_or_create_role_reuses_existing_rubric_on_match():
    existing = make_role(
        7,
        "Software Engineer",
        rubric={"current_tier_expectations": ["x"], "next_tier_expectations": ["y"], "career_ladder_summary": "z"},
    )
    client = make_fake_client(_MatchDecision(matched_role_id=7))
    provider = AnthropicAIProvider(client=client)

    result = provider.match_or_create_role("Software Developer", [existing])

    assert result.matched_role_id == 7
    assert result.rubric.current_tier_expectations == ["x"]
    assert client.messages.parse.call_count == 1


def test_match_or_create_role_infers_new_rubric_when_no_match():
    existing = make_role(7, "Software Engineer")
    new_rubric = RoleRubric(current_tier_expectations=["a"], next_tier_expectations=["b"], career_ladder_summary="c")
    client = make_fake_client(_MatchDecision(matched_role_id=None), new_rubric)
    provider = AnthropicAIProvider(client=client)

    result = provider.match_or_create_role("Product Manager", [existing])

    assert result.matched_role_id is None
    assert result.rubric == new_rubric
    assert client.messages.parse.call_count == 2


def test_match_or_create_role_raises_on_hallucinated_role_id():
    existing = make_role(7, "Software Engineer")
    client = make_fake_client(_MatchDecision(matched_role_id=999))
    provider = AnthropicAIProvider(client=client)

    with pytest.raises(RuntimeError):
        provider.match_or_create_role("Software Developer", [existing])


def test_generate_next_question_returns_parsed_output():
    expected = QuestionOutput(question="What did you build recently?")
    client = make_fake_client(expected)
    provider = AnthropicAIProvider(client=client)
    role = make_role(1, "Software Engineer")

    result = provider.generate_next_question(role, [])

    assert result == expected
    assert client.messages.parse.call_count == 1


def test_evaluate_session_returns_parsed_output():
    expected = EvaluationOutput(verdict=Verdict.meeting, rationale="solid", recommendation="lead a project")
    client = make_fake_client(expected)
    provider = AnthropicAIProvider(client=client)
    role = make_role(1, "Software Engineer")
    qa_history = [make_qa(0, "q", "a")]

    result = provider.evaluate_session(role, qa_history)

    assert result == expected
    assert client.messages.parse.call_count == 1
