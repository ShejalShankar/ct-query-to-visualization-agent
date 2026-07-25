from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.request import RecruitmentStatus, TrialPhase


class AnalysisIntent(StrEnum):
    TIME_TREND = "time_trend"
    DISTRIBUTION = "distribution"
    COMPARISON = "comparison"
    GEOGRAPHIC_RANKING = "geographic_ranking"
    RELATIONSHIP_NETWORK = "relationship_network"


class AnalysisMetric(StrEnum):
    TRIAL_COUNT = "trial_count"


class GroupByDimension(StrEnum):
    START_YEAR = "start_year"
    PHASE = "phase"
    INTERVENTION_TYPE = "intervention_type"
    COUNTRY = "country"
    SPONSOR_CATEGORY = "sponsor_category"
    DRUG = "drug"
    CONDITION = "condition"


class ComparisonDimension(StrEnum):
    DRUG = "drug"
    CONDITION = "condition"
    SPONSOR = "sponsor"


class VisualizationType(StrEnum):
    TIME_SERIES = "time_series"
    BAR_CHART = "bar_chart"
    GROUPED_BAR_CHART = "grouped_bar_chart"
    NETWORK_GRAPH = "network_graph"


class NetworkEntity(StrEnum):
    DRUG = "drug"
    SPONSOR = "sponsor"
    CONDITION = "condition"


class AnalysisFilters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    drug_names: list[str] = Field(default_factory=list, max_length=5)
    conditions: list[str] = Field(default_factory=list, max_length=5)
    phases: list[TrialPhase] = Field(default_factory=list, max_length=6)
    sponsors: list[str] = Field(default_factory=list, max_length=5)
    countries: list[str] = Field(default_factory=list, max_length=10)
    recruitment_statuses: list[RecruitmentStatus] = Field(
        default_factory=list,
        max_length=10,
    )

    start_year: int | None = Field(default=None, ge=1900)
    end_year: int | None = Field(default=None, ge=1900)


class NetworkDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: NetworkEntity
    target: NetworkEntity

    @model_validator(mode="after")
    def validate_distinct_entities(self) -> "NetworkDefinition":
        if self.source == self.target:
            raise ValueError(
                "Network source and target entities must be different"
            )

        return self


class AnalysisPlan(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "intent": "time_trend",
                    "metric": "trial_count",
                    "group_by": "start_year",
                    "filters": {
                        "drug_names": ["Pembrolizumab"],
                        "start_year": 2015,
                    },
                    "visualization_type": "time_series",
                    "confidence": 0.96,
                    "reasoning_summary": (
                        "The user asks how trial volume changed over time, "
                        "so studies should be grouped by start year."
                    ),
                },
                {
                    "intent": "comparison",
                    "metric": "trial_count",
                    "group_by": "phase",
                    "compare_by": "drug",
                    "filters": {
                        "drug_names": [
                            "Pembrolizumab",
                            "Nivolumab",
                        ],
                        "conditions": ["Melanoma"],
                    },
                    "visualization_type": "grouped_bar_chart",
                    "confidence": 0.94,
                    "reasoning_summary": (
                        "The user is comparing phase distributions "
                        "between two drugs."
                    ),
                },
                {
                    "intent": "relationship_network",
                    "metric": "trial_count",
                    "group_by": "drug",
                    "filters": {
                        "conditions": ["Breast Cancer"],
                    },
                    "network": {
                        "source": "sponsor",
                        "target": "drug",
                    },
                    "visualization_type": "network_graph",
                    "confidence": 0.91,
                    "reasoning_summary": (
                        "The query asks for relationships between "
                        "sponsors and drugs."
                    ),
                },
            ]
        },
    )

    intent: AnalysisIntent

    metric: AnalysisMetric = AnalysisMetric.TRIAL_COUNT

    group_by: GroupByDimension

    compare_by: ComparisonDimension | None = None

    network: NetworkDefinition | None = None

    filters: AnalysisFilters = Field(default_factory=AnalysisFilters)

    visualization_type: VisualizationType

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Planner confidence in the interpreted analysis.",
    )

    reasoning_summary: str = Field(
        min_length=10,
        max_length=300,
        description=(
            "Brief user-facing explanation of how the query was interpreted. "
            "This must not contain hidden chain-of-thought."
        ),
    )

    @model_validator(mode="after")
    def validate_plan_consistency(self) -> "AnalysisPlan":
        if self.intent == AnalysisIntent.TIME_TREND:
            if self.group_by != GroupByDimension.START_YEAR:
                raise ValueError(
                    "time_trend plans must group by start_year"
                )

            if self.visualization_type != VisualizationType.TIME_SERIES:
                raise ValueError(
                    "time_trend plans must use time_series visualization"
                )

        if self.intent == AnalysisIntent.COMPARISON:
            if self.compare_by is None:
                raise ValueError(
                    "comparison plans must define compare_by"
                )

            if (
                self.visualization_type
                != VisualizationType.GROUPED_BAR_CHART
            ):
                raise ValueError(
                    "comparison plans must use grouped_bar_chart"
                )

        if self.intent == AnalysisIntent.RELATIONSHIP_NETWORK:
            if self.network is None:
                raise ValueError(
                    "relationship_network plans must define a network"
                )

            if (
                self.visualization_type
                != VisualizationType.NETWORK_GRAPH
            ):
                raise ValueError(
                    "relationship_network plans must use network_graph"
                )

        if self.intent != AnalysisIntent.COMPARISON:
            if self.compare_by is not None:
                raise ValueError(
                    "compare_by is only valid for comparison plans"
                )

        if self.intent != AnalysisIntent.RELATIONSHIP_NETWORK:
            if self.network is not None:
                raise ValueError(
                    "network is only valid for relationship_network plans"
                )

        return self