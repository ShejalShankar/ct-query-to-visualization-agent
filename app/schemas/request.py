from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TrialPhase(StrEnum):
    EARLY_PHASE1 = "EARLY_PHASE1"
    PHASE1 = "PHASE1"
    PHASE2 = "PHASE2"
    PHASE3 = "PHASE3"
    PHASE4 = "PHASE4"
    NOT_APPLICABLE = "NA"


class RecruitmentStatus(StrEnum):
    NOT_YET_RECRUITING = "NOT_YET_RECRUITING"
    RECRUITING = "RECRUITING"
    ENROLLING_BY_INVITATION = "ENROLLING_BY_INVITATION"
    ACTIVE_NOT_RECRUITING = "ACTIVE_NOT_RECRUITING"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"
    COMPLETED = "COMPLETED"
    WITHDRAWN = "WITHDRAWN"
    UNKNOWN = "UNKNOWN"


class VisualizationRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "query": (
                        "How has the number of pembrolizumab trials "
                        "changed per year since 2015?"
                    ),
                    "drug_names": ["Pembrolizumab"],
                    "start_year": 2015,
                },
                {
                    "query": (
                        "Compare the distribution of trial phases for "
                        "Pembrolizumab and Nivolumab in melanoma."
                    ),
                    "drug_names": [
                        "Pembrolizumab",
                        "Nivolumab",
                    ],
                    "conditions": ["Melanoma"],
                },
                {
                    "query": (
                        "Which countries have the most recruiting "
                        "breast cancer trials?"
                    ),
                    "conditions": ["Breast Cancer"],
                    "recruitment_statuses": ["RECRUITING"],
                },
            ]
        },
    )

    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description=(
            "Natural-language question about clinical trials. "
            "This is the only required field."
        ),
    )

    drug_names: list[str] = Field(
        default_factory=list,
        max_length=5,
        description=(
            "Optional drug or intervention names. Explicit values override "
            "drug names inferred from the query."
        ),
    )

    conditions: list[str] = Field(
        default_factory=list,
        max_length=5,
        description=(
            "Optional conditions or diseases used to restrict the search."
        ),
    )

    phases: list[TrialPhase] = Field(
        default_factory=list,
        max_length=6,
        description="Optional ClinicalTrials.gov trial-phase filters.",
    )

    sponsors: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Optional lead sponsor names.",
    )

    countries: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Optional countries in which studies have locations.",
    )

    recruitment_statuses: list[RecruitmentStatus] = Field(
        default_factory=list,
        max_length=10,
        description="Optional overall study-status filters.",
    )

    start_year: int | None = Field(
        default=None,
        ge=1900,
        description="Optional inclusive lower bound for study start year.",
    )

    end_year: int | None = Field(
        default=None,
        ge=1900,
        description="Optional inclusive upper bound for study start year.",
    )

    max_studies: int = Field(
        default=2000,
        ge=1,
        le=5000,
        description=(
            "Maximum number of studies the service may retrieve and analyze."
        ),
    )

    include_citations: bool = Field(
        default=True,
        description=(
            "Whether the response should include source traceability "
            "for visualized values."
        ),
    )

    max_citations_per_datum: int = Field(
        default=10,
        ge=1,
        le=50,
        description=(
            "Maximum number of citation records returned for each "
            "visualized datum."
        ),
    )

    @field_validator(
        "drug_names",
        "conditions",
        "sponsors",
        "countries",
        mode="after",
    )
    @classmethod
    def clean_string_lists(cls, values: list[str]) -> list[str]:
        normalized_values: list[str] = []
        seen: set[str] = set()

        for value in values:
            cleaned_value = value.strip()

            if not cleaned_value:
                raise ValueError("List values must not be empty")

            if len(cleaned_value) > 150:
                raise ValueError(
                    "Each structured text value must be 150 characters or fewer"
                )

            comparison_key = cleaned_value.casefold()

            if comparison_key not in seen:
                seen.add(comparison_key)
                normalized_values.append(cleaned_value)

        return normalized_values

    @model_validator(mode="after")
    def validate_request(self) -> "VisualizationRequest":
        current_year = datetime.now(UTC).year

        if self.start_year is not None and self.start_year > current_year + 1:
            raise ValueError(
                f"start_year cannot be later than {current_year + 1}"
            )

        if self.end_year is not None and self.end_year > current_year + 1:
            raise ValueError(
                f"end_year cannot be later than {current_year + 1}"
            )

        if (
            self.start_year is not None
            and self.end_year is not None
            and self.start_year > self.end_year
        ):
            raise ValueError(
                "start_year must be less than or equal to end_year"
            )

        return self