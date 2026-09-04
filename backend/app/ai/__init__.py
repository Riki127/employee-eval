from app.ai.anthropic_provider import AnthropicAIProvider
from app.ai.base import AIProvider
from app.ai.mock import MockAIProvider
from app.config import settings


def get_ai_provider() -> AIProvider:
    if settings.ai_provider == "anthropic":
        return AnthropicAIProvider()
    return MockAIProvider()
