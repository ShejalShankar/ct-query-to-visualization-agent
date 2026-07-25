from functools import lru_cache

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.planner.llm_planner import LLMPlanner


@lru_cache
def get_openai_client() -> AsyncOpenAI:
    settings = get_settings()

    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        timeout=20.0,
        max_retries=2,
    )


def get_planner() -> LLMPlanner:
    settings = get_settings()

    return LLMPlanner(
        client=get_openai_client(),
        model=settings.openai_model,
    )