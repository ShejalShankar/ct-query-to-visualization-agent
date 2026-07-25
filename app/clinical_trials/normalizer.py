from datetime import date, datetime
from typing import Any

from pydantic import ValidationError

from app.clinical_trials.normalized_models import (
    NormalizationWarning,
    NormalizedIntervention,
    NormalizedInterventionType,
    NormalizedSponsor,
    NormalizedStudy,
    StudyNormalizationResult,
)


INTERVENTION_TYPE_MAP: dict[str, NormalizedInterventionType] = {
    "DRUG": NormalizedInterventionType.DRUG,
    "BIOLOGICAL": NormalizedInterventionType.BIOLOGICAL,
    "DEVICE": NormalizedInterventionType.DEVICE,
    "PROCEDURE": NormalizedInterventionType.PROCEDURE,
    "BEHAVIORAL": NormalizedInterventionType.BEHAVIORAL,
    "DIETARY_SUPPLEMENT": (
        NormalizedInterventionType.DIETARY_SUPPLEMENT
    ),
    "COMBINATION_PRODUCT": (
        NormalizedInterventionType.COMBINATION_PRODUCT
    ),
    "DIAGNOSTIC_TEST": NormalizedInterventionType.DIAGNOSTIC_TEST,
    "GENETIC": NormalizedInterventionType.GENETIC,
    "RADIATION": NormalizedInterventionType.RADIATION,
    "OTHER": NormalizedInterventionType.OTHER,
}


def normalize_studies(
    raw_studies: list[dict[str, Any]],
) -> StudyNormalizationResult:
    normalized_studies: list[NormalizedStudy] = []
    warnings: list[NormalizationWarning] = []

    for raw_study in raw_studies:
        study, study_warnings = normalize_study(raw_study)
        warnings.extend(study_warnings)

        if study is None:
            continue

        normalized_studies.append(study)

    return StudyNormalizationResult(
        studies=normalized_studies,
        warnings=warnings,
        input_count=len(raw_studies),
        normalized_count=len(normalized_studies),
        skipped_count=len(raw_studies) - len(normalized_studies),
    )


def normalize_study(
    raw_study: dict[str, Any],
) -> tuple[NormalizedStudy | None, list[NormalizationWarning]]:
    warnings: list[NormalizationWarning] = []

    protocol_section = _get_dict(raw_study, "protocolSection")

    identification_module = _get_dict(
        protocol_section,
        "identificationModule",
    )
    status_module = _get_dict(protocol_section, "statusModule")
    design_module = _get_dict(protocol_section, "designModule")
    conditions_module = _get_dict(
        protocol_section,
        "conditionsModule",
    )
    interventions_module = _get_dict(
        protocol_section,
        "armsInterventionsModule",
    )
    sponsor_module = _get_dict(
        protocol_section,
        "sponsorCollaboratorsModule",
    )
    locations_module = _get_dict(
        protocol_section,
        "contactsLocationsModule",
    )

    nct_id = _clean_optional_string(
        identification_module.get("nctId")
    )

    if nct_id is None:
        warnings.append(
            NormalizationWarning(
                field="protocolSection.identificationModule.nctId",
                message=(
                    "Study was skipped because it did not contain an NCT ID."
                ),
            )
        )
        return None, warnings

    title = _clean_optional_string(
        identification_module.get("briefTitle")
    )

    overall_status = _clean_optional_string(
        status_module.get("overallStatus")
    )

    start_date_raw = _extract_start_date_raw(status_module)
    start_date = _parse_partial_date(start_date_raw)

    if start_date_raw is not None and start_date is None:
        warnings.append(
            NormalizationWarning(
                nct_id=nct_id,
                field="protocolSection.statusModule.startDateStruct.date",
                message=(
                    f"Start date '{start_date_raw}' could not be parsed."
                ),
            )
        )

    phases = _normalize_string_list(
        design_module.get("phases")
    )

    conditions = _normalize_string_list(
        conditions_module.get("conditions")
    )

    interventions = _normalize_interventions(
        interventions_module.get("interventions")
    )

    lead_sponsor = _normalize_sponsor(
        sponsor_module.get("leadSponsor")
    )

    countries = _normalize_countries(
        locations_module.get("locations")
    )

    try:
        normalized_study = NormalizedStudy(
            nct_id=nct_id,
            title=title,
            overall_status=overall_status,
            start_date=start_date,
            start_date_raw=start_date_raw,
            phases=phases,
            conditions=conditions,
            interventions=interventions,
            lead_sponsor=lead_sponsor,
            countries=countries,
        )

    except ValidationError as exc:
        warnings.append(
            NormalizationWarning(
                nct_id=nct_id,
                field="study",
                message=(
                    "Study was skipped because the normalized record "
                    f"failed validation: {exc.errors()}"
                ),
            )
        )
        return None, warnings

    return normalized_study, warnings


def _extract_start_date_raw(
    status_module: dict[str, Any],
) -> str | None:
    start_date_struct = _get_dict(
        status_module,
        "startDateStruct",
    )

    return _clean_optional_string(
        start_date_struct.get("date")
    )


def _parse_partial_date(value: str | None) -> date | None:
    """
    ClinicalTrials.gov dates may have year, year-month, or full-date
    precision. Missing components are normalized to the first valid day.
    """

    if value is None:
        return None

    supported_formats: tuple[tuple[str, str], ...] = (
        ("%Y-%m-%d", value),
        ("%Y-%m", value),
        ("%Y", value),
    )

    for date_format, date_value in supported_formats:
        try:
            parsed = datetime.strptime(
                date_value,
                date_format,
            ).date()

            if date_format == "%Y-%m":
                return parsed.replace(day=1)

            if date_format == "%Y":
                return parsed.replace(month=1, day=1)

            return parsed

        except ValueError:
            continue

    return None


def _normalize_interventions(
    raw_interventions: Any,
) -> list[NormalizedIntervention]:
    if not isinstance(raw_interventions, list):
        return []

    normalized: list[NormalizedIntervention] = []
    seen: set[tuple[str, str]] = set()

    for raw_intervention in raw_interventions:
        if not isinstance(raw_intervention, dict):
            continue

        name = _clean_optional_string(
            raw_intervention.get("name")
        )

        if name is None:
            continue

        raw_type = _clean_optional_string(
            raw_intervention.get("type")
        )

        normalized_type = INTERVENTION_TYPE_MAP.get(
            raw_type or "",
            NormalizedInterventionType.UNKNOWN,
        )

        deduplication_key = (
            name.casefold(),
            normalized_type.value,
        )

        if deduplication_key in seen:
            continue

        seen.add(deduplication_key)

        normalized.append(
            NormalizedIntervention(
                name=name,
                intervention_type=normalized_type,
            )
        )

    return normalized


def _normalize_sponsor(
    raw_sponsor: Any,
) -> NormalizedSponsor | None:
    if not isinstance(raw_sponsor, dict):
        return None

    name = _clean_optional_string(raw_sponsor.get("name"))

    if name is None:
        return None

    sponsor_class = _clean_optional_string(
        raw_sponsor.get("class")
    )

    return NormalizedSponsor(
        name=name,
        sponsor_class=sponsor_class,
    )


def _normalize_countries(
    raw_locations: Any,
) -> list[str]:
    if not isinstance(raw_locations, list):
        return []

    countries: list[str] = []

    for raw_location in raw_locations:
        if not isinstance(raw_location, dict):
            continue

        country = _clean_optional_string(
            raw_location.get("country")
        )

        if country is not None:
            countries.append(country)

    return _deduplicate_strings(countries)


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    strings = [
        cleaned
        for item in value
        if (cleaned := _clean_optional_string(item)) is not None
    ]

    return _deduplicate_strings(strings)


def _deduplicate_strings(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        comparison_key = value.casefold()

        if comparison_key in seen:
            continue

        seen.add(comparison_key)
        result.append(value)

    return result


def _clean_optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    cleaned = value.strip()

    return cleaned or None


def _get_dict(
    source: Any,
    key: str,
) -> dict[str, Any]:
    if not isinstance(source, dict):
        return {}

    value = source.get(key)

    if not isinstance(value, dict):
        return {}

    return value