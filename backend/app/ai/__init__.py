from app.ai.base import AIProvider
from app.ai.mock import MockAIProvider


def get_ai_provider() -> AIProvider:
    return MockAIProvider()
