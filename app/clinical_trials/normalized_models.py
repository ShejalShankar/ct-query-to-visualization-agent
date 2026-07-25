from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class NormalizedInterventionType(StrEnum):
    DRUG = "DRUG"
    BIOLOGICAL = "BIOLOGICAL"
    DEVICE = "DEVICE"
    PROCEDURE = "PROCEDURE"
    BEHAVIORAL = "BEHAVIORAL"
    DIETARY_SUPPLEMENT = "DIETARY_SUPPLEMENT"
    COMBINATION_PRODUCT = "COMBINATION_PRODUCT"
    DIAGNOSTIC_TEST = "DIAGNOSTIC_TEST"
    GENETIC = "GENETIC"
    RADIATION = "RADIATION"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class NormalizedIntervention(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=500)
    intervention_type: NormalizedInterventionType


class NormalizedSponsor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=500)
    sponsor_class: str | None = Field(default=None, max_length=100)


class NormalizedStudy(BaseModel):
    """
    Stable internal representation of a ClinicalTrials.gov study.

    Analysis functions should depend on this model rather than directly on
    the external ClinicalTrials.gov JSON response shape.
    """

    model_config = ConfigDict(extra="forbid")

    nct_id: str = Field(pattern=r"^NCT\d{8}$")

    title: str | None = Field(default=None, max_length=1000)
    overall_status: str | None = Field(default=None, max_length=100)

    start_date: date | None = None
    start_date_raw: str | None = Field(default=None, max_length=100)

    phases: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    interventions: list[NormalizedIntervention] = Field(
        default_factory=list
    )

    lead_sponsor: NormalizedSponsor | None = None
    countries: list[str] = Field(default_factory=list)


class NormalizationWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nct_id: str | None = None
    field: str
    message: str


class StudyNormalizationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    studies: list[NormalizedStudy] = Field(default_factory=list)
    warnings: list[NormalizationWarning] = Field(default_factory=list)

    input_count: int = Field(ge=0)
    normalized_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)