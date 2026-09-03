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
