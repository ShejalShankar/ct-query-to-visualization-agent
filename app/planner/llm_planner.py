from openai import AsyncOpenAI

from app.schemas.analysis_plan import AnalysisPlan
from app.planner.prompts import PLANNER_SYSTEM_PROMPT


class PlannerError(RuntimeError):
    """Raised when the LLM cannot produce a valid analysis plan."""


class LLMPlanner:
    def __init__(
        self,
        *,
        client: AsyncOpenAI,
        model: str,
    ) -> None:
        self._client = client
        self._model = model

    async def create_plan(self, query: str) -> AnalysisPlan:
        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError("query must not be empty")

        try:
            completion = await self._client.chat.completions.parse(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": PLANNER_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": normalized_query,
                    },
                ],
                response_format=AnalysisPlan,
            )
        except Exception as exc:
            raise PlannerError(
                "The analysis planner request failed."
            ) from exc

        message = completion.choices[0].message

        if message.refusal:
            raise PlannerError(
                f"The analysis planner refused the request: "
                f"{message.refusal}"
            )

        plan = message.parsed

        if plan is None:
            raise PlannerError(
                "The analysis planner returned no structured plan."
            )

        return plan