from functools import lru_cache

from openai import AsyncOpenAI

from app.core.config import settings
from app.planner.llm_planner import LLMPlanner


@lru_cache
def get_openai_client() -> AsyncOpenAI:
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured"
        )

    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        timeout=20.0,
        max_retries=2,
    )


def get_planner() -> LLMPlanner:
    return LLMPlanner(
        client=get_openai_client(),
        model=settings.openai_model,
    )