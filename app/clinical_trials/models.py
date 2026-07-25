from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StudySearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    studies: list[dict[str, Any]] = Field(default_factory=list)

    total_count: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Total number of studies matching the API query, when supplied "
            "by ClinicalTrials.gov."
        ),
    )

    retrieved_count: int = Field(
        ge=0,
        description="Number of study records retrieved by this client call.",
    )

    pages_retrieved: int = Field(
        ge=0,
        description="Number of API pages requested.",
    )

    partial_results: bool = Field(
        description=(
            "Whether retrieval stopped before all matching records were "
            "returned because max_studies was reached."
        ),
    )