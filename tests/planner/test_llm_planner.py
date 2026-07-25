from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.planner.llm_planner import LLMPlanner, PlannerError
from app.schemas.analysis_plan import (
    AnalysisFilters,
    AnalysisIntent,
    AnalysisPlan,
    GroupByDimension,
    VisualizationType,
)


def build_mock_client(
    *,
    parsed: AnalysisPlan | None = None,
    refusal: str | None = None,
) -> Mock:
    message = SimpleNamespace(
        parsed=parsed,
        refusal=refusal,
    )

    completion = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=message,
            )
        ]
    )

    client = Mock()
    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.parse = AsyncMock(
        return_value=completion
    )

    return client


@pytest.mark.asyncio
async def test_creates_typed_analysis_plan() -> None:
    expected_plan = AnalysisPlan(
        intent=AnalysisIntent.TIME_TREND,
        group_by=GroupByDimension.START_YEAR,
        filters=AnalysisFilters(
            drug_names=["Pembrolizumab"],
            start_year=2015,
        ),
        visualization_type=VisualizationType.TIME_SERIES,
        confidence=0.96,
        reasoning_summary=(
            "The question asks how trial volume changed over time."
        ),
    )

    client = build_mock_client(parsed=expected_plan)

    planner = LLMPlanner(
        client=client,
        model="gpt-5-mini",
    )

    result = await planner.create_plan(
        "How have pembrolizumab trials changed since 2015?"
    )

    assert result == expected_plan

    client.chat.completions.parse.assert_awaited_once()

    call_kwargs = (
        client.chat.completions.parse.await_args.kwargs
    )

    assert call_kwargs["model"] == "gpt-5-mini"
    assert call_kwargs["response_format"] is AnalysisPlan
    assert call_kwargs["messages"][1] == {
        "role": "user",
        "content": (
            "How have pembrolizumab trials changed since 2015?"
        ),
    }


@pytest.mark.asyncio
async def test_strips_query_whitespace() -> None:
    expected_plan = AnalysisPlan(
        intent=AnalysisIntent.GEOGRAPHIC_RANKING,
        group_by=GroupByDimension.COUNTRY,
        visualization_type=VisualizationType.BAR_CHART,
        confidence=0.91,
        reasoning_summary=(
            "The question asks for countries ranked by trial count."
        ),
    )

    client = build_mock_client(parsed=expected_plan)

    planner = LLMPlanner(
        client=client,
        model="gpt-5-mini",
    )

    await planner.create_plan(
        "  Which countries have the most clinical trials?  "
    )

    call_kwargs = (
        client.chat.completions.parse.await_args.kwargs
    )

    assert call_kwargs["messages"][1]["content"] == (
        "Which countries have the most clinical trials?"
    )


@pytest.mark.asyncio
async def test_rejects_empty_query_without_calling_model() -> None:
    client = build_mock_client()

    planner = LLMPlanner(
        client=client,
        model="gpt-5-mini",
    )

    with pytest.raises(
        ValueError,
        match="query must not be empty",
    ):
        await planner.create_plan("   ")

    client.chat.completions.parse.assert_not_awaited()


@pytest.mark.asyncio
async def test_raises_planner_error_for_refusal() -> None:
    client = build_mock_client(
        refusal="I cannot process this request.",
    )

    planner = LLMPlanner(
        client=client,
        model="gpt-5-mini",
    )

    with pytest.raises(
        PlannerError,
        match="refused",
    ):
        await planner.create_plan(
            "Analyze these clinical trials."
        )


@pytest.mark.asyncio
async def test_raises_planner_error_when_no_plan_is_returned() -> None:
    client = build_mock_client(parsed=None)

    planner = LLMPlanner(
        client=client,
        model="gpt-5-mini",
    )

    with pytest.raises(
        PlannerError,
        match="returned no structured plan",
    ):
        await planner.create_plan(
            "Show clinical trial trends."
        )


@pytest.mark.asyncio
async def test_wraps_openai_client_failure() -> None:
    client = build_mock_client()

    client.chat.completions.parse.side_effect = RuntimeError(
        "network unavailable"
    )

    planner = LLMPlanner(
        client=client,
        model="gpt-5-mini",
    )

    with pytest.raises(
        PlannerError,
        match="planner request failed",
    ):
        await planner.create_plan(
            "Show clinical trial trends."
        )