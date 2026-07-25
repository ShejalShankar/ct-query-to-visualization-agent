from pydantic import BaseModel, Field


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