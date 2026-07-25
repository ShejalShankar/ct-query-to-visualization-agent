from datetime import date

from app.clinical_trials.normalized_models import (
    NormalizedInterventionType,
)
from app.clinical_trials.normalizer import (
    normalize_studies,
    normalize_study,
)


def test_normalize_complete_study() -> None:
    raw_study = {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT01234567",
                "briefTitle": "Pembrolizumab Study",
            },
            "statusModule": {
                "overallStatus": "RECRUITING",
                "startDateStruct": {
                    "date": "2020-07-16",
                },
            },
            "designModule": {
                "phases": [
                    "PHASE2",
                ],
            },
            "conditionsModule": {
                "conditions": [
                    "Melanoma",
                    "Melanoma",
                ],
            },
            "armsInterventionsModule": {
                "interventions": [
                    {
                        "type": "DRUG",
                        "name": "Pembrolizumab",
                    },
                    {
                        "type": "DRUG",
                        "name": "Pembrolizumab",
                    },
                ],
            },
            "sponsorCollaboratorsModule": {
                "leadSponsor": {
                    "name": "Example Sponsor",
                    "class": "INDUSTRY",
                },
            },
            "contactsLocationsModule": {
                "locations": [
                    {
                        "country": "United States",
                    },
                    {
                        "country": "United States",
                    },
                    {
                        "country": "Canada",
                    },
                ],
            },
        }
    }

    normalized, warnings = normalize_study(raw_study)

    assert normalized is not None
    assert warnings == []

    assert normalized.nct_id == "NCT01234567"
    assert normalized.title == "Pembrolizumab Study"
    assert normalized.overall_status == "RECRUITING"
    assert normalized.start_date == date(2020, 7, 16)

    assert normalized.phases == ["PHASE2"]
    assert normalized.conditions == ["Melanoma"]
    assert normalized.countries == [
        "United States",
        "Canada",
    ]

    assert len(normalized.interventions) == 1
    assert normalized.interventions[0].name == "Pembrolizumab"
    assert (
        normalized.interventions[0].intervention_type
        == NormalizedInterventionType.DRUG
    )

    assert normalized.lead_sponsor is not None
    assert normalized.lead_sponsor.name == "Example Sponsor"
    assert normalized.lead_sponsor.sponsor_class == "INDUSTRY"


def test_normalize_year_only_start_date() -> None:
    raw_study = {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT01234568",
            },
            "statusModule": {
                "startDateStruct": {
                    "date": "2018",
                },
            },
        }
    }

    normalized, warnings = normalize_study(raw_study)

    assert normalized is not None
    assert normalized.start_date == date(2018, 1, 1)
    assert normalized.start_date_raw == "2018"
    assert warnings == []


def test_normalize_month_precision_start_date() -> None:
    raw_study = {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT01234569",
            },
            "statusModule": {
                "startDateStruct": {
                    "date": "2019-04",
                },
            },
        }
    }

    normalized, warnings = normalize_study(raw_study)

    assert normalized is not None
    assert normalized.start_date == date(2019, 4, 1)
    assert warnings == []


def test_invalid_start_date_creates_warning() -> None:
    raw_study = {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT01234570",
            },
            "statusModule": {
                "startDateStruct": {
                    "date": "not-a-date",
                },
            },
        }
    }

    normalized, warnings = normalize_study(raw_study)

    assert normalized is not None
    assert normalized.start_date is None
    assert len(warnings) == 1
    assert warnings[0].nct_id == "NCT01234570"


def test_study_without_nct_id_is_skipped() -> None:
    raw_study = {
        "protocolSection": {
            "identificationModule": {
                "briefTitle": "Missing ID",
            }
        }
    }

    normalized, warnings = normalize_study(raw_study)

    assert normalized is None
    assert len(warnings) == 1
    assert warnings[0].nct_id is None


def test_normalize_studies_returns_summary_counts() -> None:
    raw_studies = [
        {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT01234571",
                }
            }
        },
        {
            "protocolSection": {
                "identificationModule": {},
            }
        },
    ]

    result = normalize_studies(raw_studies)

    assert result.input_count == 2
    assert result.normalized_count == 1
    assert result.skipped_count == 1
    assert len(result.studies) == 1
    assert len(result.warnings) == 1


def test_unknown_intervention_type_is_preserved_as_unknown() -> None:
    raw_study = {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT01234572",
            },
            "armsInterventionsModule": {
                "interventions": [
                    {
                        "name": "Experimental intervention",
                        "type": "NEW_FUTURE_TYPE",
                    }
                ],
            },
        }
    }

    normalized, warnings = normalize_study(raw_study)

    assert normalized is not None
    assert warnings == []
    assert len(normalized.interventions) == 1
    assert (
        normalized.interventions[0].intervention_type
        == NormalizedInterventionType.UNKNOWN
    )