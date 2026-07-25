from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.analysis_plan import AnalysisPlan, VisualizationType


class VisualizationChannel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str = Field(
        min_length=1,
        max_length=100,
        description="Name of the data field mapped to this visual channel.",
    )

    data_type: Literal[
        "nominal",
        "ordinal",
        "quantitative",
        "temporal",
    ] = Field(
        description="Semantic type of the field used by the renderer."
    )

    label: str | None = Field(
        default=None,
        max_length=100,
        description="Optional human-readable axis or legend label.",
    )

    unit: str | None = Field(
        default=None,
        max_length=50,
        description="Optional display unit such as trials, studies, or percent.",
    )


class CitationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nct_id: str = Field(
        pattern=r"^NCT\d{8}$",
        description="ClinicalTrials.gov study identifier.",
    )

    field: str = Field(
        min_length=1,
        max_length=250,
        description=(
            "ClinicalTrials.gov field path or normalized source field "
            "supporting the visualized datum."
        ),
    )

    excerpt: str = Field(
        min_length=1,
        max_length=500,
        description=(
            "Exact supporting field value or concise excerpt from the "
            "ClinicalTrials.gov API record."
        ),
    )


class CitationGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_records: int = Field(
        ge=0,
        description="Total number of source studies contributing to the datum.",
    )

    records_returned: int = Field(
        ge=0,
        description="Number of citation records included in the response.",
    )

    truncated: bool = Field(
        description=(
            "Whether additional source studies contributed but were omitted "
            "because of the citation limit."
        ),
    )

    records: list[CitationRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_counts(self) -> "CitationGroup":
        if self.records_returned != len(self.records):
            raise ValueError(
                "records_returned must equal the number of citation records"
            )

        if self.records_returned > self.total_records:
            raise ValueError(
                "records_returned cannot exceed total_records"
            )

        if self.truncated and self.records_returned >= self.total_records:
            raise ValueError(
                "truncated must be false when all citation records are returned"
            )

        return self


class ChartDatum(BaseModel):
    """
    A flexible chart row.

    Dynamic keys are required because different analyses produce different
    fields, such as year, phase, country, drug, and trial_count.
    """

    model_config = ConfigDict(extra="allow")

    datum_id: str = Field(
        min_length=1,
        max_length=200,
        description=(
            "Stable identifier used to associate this datum with citations."
        ),
    )

    citation_ref: str | None = Field(
        default=None,
        max_length=200,
        description="Key referencing an entry in the citations object.",
    )


class NetworkNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=250)
    label: str = Field(min_length=1, max_length=200)

    entity_type: Literal[
        "drug",
        "sponsor",
        "condition",
    ]

    weight: int | float | None = Field(
        default=None,
        ge=0,
        description=(
            "Optional node weight, such as the number of studies connected "
            "to the entity."
        ),
    )

    citation_ref: str | None = Field(
        default=None,
        max_length=200,
    )


class NetworkEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=300)
    source: str = Field(min_length=1, max_length=250)
    target: str = Field(min_length=1, max_length=250)

    weight: int = Field(
        ge=1,
        description="Number of studies supporting this relationship.",
    )

    citation_ref: str | None = Field(
        default=None,
        max_length=200,
    )


class VisualizationSpecification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: VisualizationType

    title: str = Field(
        min_length=3,
        max_length=200,
    )

    description: str | None = Field(
        default=None,
        max_length=500,
    )

    encoding: dict[str, VisualizationChannel] = Field(
        default_factory=dict,
        description=(
            "Mapping from visual channels such as x, y, series, source, "
            "target, or weight to response fields."
        ),
    )

    data: list[ChartDatum] | None = None

    nodes: list[NetworkNode] | None = None
    edges: list[NetworkEdge] | None = None

    @model_validator(mode="after")
    def validate_visualization_shape(
        self,
    ) -> "VisualizationSpecification":
        if self.type == VisualizationType.NETWORK_GRAPH:
            if self.nodes is None or self.edges is None:
                raise ValueError(
                    "network_graph visualizations require nodes and edges"
                )

            if self.data is not None:
                raise ValueError(
                    "network_graph visualizations must not include chart data"
                )

        else:
            if self.data is None:
                raise ValueError(
                    "chart visualizations require a data array"
                )

            if self.nodes is not None or self.edges is not None:
                raise ValueError(
                    "non-network visualizations must not include nodes or edges"
                )

        return self


class ResponseMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["ClinicalTrials.gov"] = "ClinicalTrials.gov"

    generated_at: datetime

    query: str = Field(
        min_length=3,
        max_length=500,
    )

    analysis_plan: AnalysisPlan

    filters_applied: dict[str, Any] = Field(default_factory=dict)

    records_matched: int = Field(
        ge=0,
        description=(
            "Number of studies returned or matched before analysis-specific "
            "exclusions."
        ),
    )

    records_used: int = Field(
        ge=0,
        description="Number of studies included in the final analysis.",
    )

    records_excluded: int = Field(
        ge=0,
        description=(
            "Number of matched studies excluded because required fields "
            "were missing or invalid."
        ),
    )

    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    partial_results: bool = Field(
        default=False,
        description=(
            "Whether the result was truncated because of max_studies or "
            "another retrieval constraint."
        ),
    )

    @model_validator(mode="after")
    def validate_record_counts(self) -> "ResponseMetadata":
        if self.records_used + self.records_excluded > self.records_matched:
            raise ValueError(
                "records_used plus records_excluded cannot exceed "
                "records_matched"
            )

        return self


class VisualizationResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "status": "completed",
                    "visualization": {
                        "type": "time_series",
                        "title": (
                            "Pembrolizumab Trials Started Per Year Since 2015"
                        ),
                        "description": (
                            "Number of matching studies grouped by study "
                            "start year."
                        ),
                        "encoding": {
                            "x": {
                                "field": "year",
                                "data_type": "temporal",
                                "label": "Start year",
                            },
                            "y": {
                                "field": "trial_count",
                                "data_type": "quantitative",
                                "label": "Number of trials",
                                "unit": "trials",
                            },
                        },
                        "data": [
                            {
                                "datum_id": "year:2015",
                                "year": 2015,
                                "trial_count": 18,
                                "citation_ref": "year:2015",
                            }
                        ],
                    },
                    "meta": {
                        "source": "ClinicalTrials.gov",
                        "generated_at": "2026-07-25T18:00:00Z",
                        "query": (
                            "How has the number of pembrolizumab trials "
                            "changed since 2015?"
                        ),
                        "analysis_plan": {
                            "intent": "time_trend",
                            "metric": "trial_count",
                            "group_by": "start_year",
                            "compare_by": None,
                            "network": None,
                            "filters": {
                                "drug_names": ["Pembrolizumab"],
                                "conditions": [],
                                "phases": [],
                                "sponsors": [],
                                "countries": [],
                                "recruitment_statuses": [],
                                "start_year": 2015,
                                "end_year": None,
                            },
                            "visualization_type": "time_series",
                            "confidence": 0.96,
                            "reasoning_summary": (
                                "The query asks how trial volume changed "
                                "over time."
                            ),
                        },
                        "filters_applied": {
                            "drug_names": ["Pembrolizumab"],
                            "start_year": 2015,
                        },
                        "records_matched": 143,
                        "records_used": 138,
                        "records_excluded": 5,
                        "assumptions": [
                            "Studies were grouped using the study start date."
                        ],
                        "warnings": [
                            "Five studies were excluded because no valid "
                            "start date was available."
                        ],
                        "partial_results": False,
                    },
                    "citations": {
                        "year:2015": {
                            "total_records": 18,
                            "records_returned": 1,
                            "truncated": True,
                            "records": [
                                {
                                    "nct_id": "NCT01234567",
                                    "field": (
                                        "protocolSection."
                                        "identificationModule.nctId"
                                    ),
                                    "excerpt": "NCT01234567",
                                }
                            ],
                        }
                    },
                }
            ]
        },
    )

    status: Literal["completed"] = "completed"

    visualization: VisualizationSpecification
    meta: ResponseMetadata

    citations: dict[str, CitationGroup] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_citation_references(self) -> "VisualizationResponse":
        available_refs = set(self.citations.keys())

        if self.visualization.data is not None:
            for datum in self.visualization.data:
                if (
                    datum.citation_ref is not None
                    and datum.citation_ref not in available_refs
                ):
                    raise ValueError(
                        f"Unknown citation reference: {datum.citation_ref}"
                    )

        if self.visualization.nodes is not None:
            for node in self.visualization.nodes:
                if (
                    node.citation_ref is not None
                    and node.citation_ref not in available_refs
                ):
                    raise ValueError(
                        f"Unknown citation reference: {node.citation_ref}"
                    )

        if self.visualization.edges is not None:
            for edge in self.visualization.edges:
                if (
                    edge.citation_ref is not None
                    and edge.citation_ref not in available_refs
                ):
                    raise ValueError(
                        f"Unknown citation reference: {edge.citation_ref}"
                    )

        return self