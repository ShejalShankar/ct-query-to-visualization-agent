from pydantic import BaseModel, Field
from enum import StrEnum


class CitationGroup(BaseModel):
    """
    Connects one aggregated result back to the studies that contributed to it.
    """

    key: str
    nct_ids: list[str] = Field(default_factory=list)


class TimeTrendPoint(BaseModel):
    year: int
    count: int


class TimeTrendResult(BaseModel):
    points: list[TimeTrendPoint] = Field(default_factory=list)

    total_studies: int
    included_studies: int
    excluded_studies: int

    citations: list[CitationGroup] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class DistributionDimension(StrEnum):
    PHASE = "phase"
    OVERALL_STATUS = "overall_status"
    SPONSOR_CLASS = "sponsor_class"
    INTERVENTION_TYPE = "intervention_type"


class DistributionPoint(BaseModel):
    category: str
    count: int


class DistributionResult(BaseModel):
    dimension: DistributionDimension
    points: list[DistributionPoint] = Field(default_factory=list)

    total_studies: int
    included_studies: int
    excluded_studies: int
    assignment_count: int

    citations: list[CitationGroup] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class GeographicPoint(BaseModel):
    country: str
    count: int


class GeographicRankingResult(BaseModel):
    points: list[GeographicPoint] = Field(default_factory=list)

    total_studies: int
    included_studies: int
    excluded_studies: int
    country_assignments: int

    citations: list[CitationGroup] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ComparisonSeriesPoint(BaseModel):
    year: int
    count: int


class ComparisonSeries(BaseModel):
    label: str
    points: list[ComparisonSeriesPoint] = Field(default_factory=list)


class ComparisonResult(BaseModel):
    series: list[ComparisonSeries] = Field(default_factory=list)

    total_studies: int
    included_studies: int
    excluded_studies: int
    overlapping_studies: int

    citations: list[CitationGroup] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class NetworkNode(BaseModel):
    id: str
    label: str
    study_count: int


class NetworkEdge(BaseModel):
    source: str
    target: str
    weight: int


class RelationshipNetworkResult(BaseModel):
    nodes: list[NetworkNode] = Field(default_factory=list)
    edges: list[NetworkEdge] = Field(default_factory=list)

    total_studies: int
    included_studies: int
    excluded_studies: int

    citations: list[CitationGroup] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)