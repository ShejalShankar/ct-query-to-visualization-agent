from collections import defaultdict
from collections.abc import Iterable

from app.analysis.models import (
    CitationGroup,
    ComparisonResult,
    ComparisonSeries,
    ComparisonSeriesPoint,
)
from app.clinical_trials.normalized_models import NormalizedStudy


def analyze_intervention_comparison(
    studies: Iterable[NormalizedStudy],
    *,
    intervention_names: list[str],
    start_year: int | None = None,
    end_year: int | None = None,
    fill_missing_years: bool = True,
) -> ComparisonResult:
    """
    Compare named interventions by study start year.

    Group membership is verified against normalized intervention names using
    case-insensitive exact matching. A study may contribute to multiple
    comparison groups when it contains multiple requested interventions.
    """

    cleaned_names = _normalize_requested_names(intervention_names)

    if len(cleaned_names) < 2:
        raise ValueError(
            "At least two distinct intervention names are required."
        )

    study_list = list(studies)

    studies_by_group_and_year: dict[
        str,
        dict[int, set[str]],
    ] = {
        label: defaultdict(set)
        for label in cleaned_names.values()
    }

    included_nct_ids: set[str] = set()
    overlapping_nct_ids: set[str] = set()
    excluded_count = 0

    for study in study_list:
        if study.start_date is None:
            excluded_count += 1
            continue

        year = study.start_date.year

        if start_year is not None and year < start_year:
            continue

        if end_year is not None and year > end_year:
            continue

        study_interventions = {
            _normalize_name(intervention.name)
            for intervention in study.interventions
            if intervention.name.strip()
        }

        matching_groups = [
            normalized_name
            for normalized_name in cleaned_names
            if normalized_name in study_interventions
        ]

        if not matching_groups:
            excluded_count += 1
            continue

        included_nct_ids.add(study.nct_id)

        if len(matching_groups) > 1:
            overlapping_nct_ids.add(study.nct_id)

        for normalized_name in matching_groups:
            display_label = cleaned_names[normalized_name]
            studies_by_group_and_year[display_label][year].add(
                study.nct_id
            )

    observed_years = {
        year
        for yearly_counts in studies_by_group_and_year.values()
        for year in yearly_counts
    }

    warnings: list[str] = []

    if not observed_years:
        warnings.append(
            "No studies matched the requested intervention groups "
            "with a usable start date."
        )

        if excluded_count:
            warnings.append(
                f"{excluded_count} studies were excluded because they "
                "did not match a requested intervention or lacked a "
                "usable start date."
            )

        return ComparisonResult(
            series=[
                ComparisonSeries(label=label, points=[])
                for label in cleaned_names.values()
            ],
            total_studies=len(study_list),
            included_studies=0,
            excluded_studies=excluded_count,
            overlapping_studies=0,
            citations=[],
            warnings=warnings,
        )

    minimum_year = (
        start_year
        if start_year is not None
        else min(observed_years)
    )
    maximum_year = (
        end_year
        if end_year is not None
        else max(observed_years)
    )

    years = (
        list(range(minimum_year, maximum_year + 1))
        if fill_missing_years
        else sorted(observed_years)
    )

    series = [
        ComparisonSeries(
            label=label,
            points=[
                ComparisonSeriesPoint(
                    year=year,
                    count=len(
                        studies_by_group_and_year[label].get(
                            year,
                            set(),
                        )
                    ),
                )
                for year in years
            ],
        )
        for label in cleaned_names.values()
    ]

    citations = [
        CitationGroup(
            key=f"{label}:{year}",
            nct_ids=sorted(nct_ids),
        )
        for label in cleaned_names.values()
        for year, nct_ids in sorted(
            studies_by_group_and_year[label].items()
        )
        if nct_ids
    ]

    if excluded_count:
        warnings.append(
            f"{excluded_count} studies were excluded because they "
            "did not match a requested intervention or lacked a "
            "usable start date."
        )

    if overlapping_nct_ids:
        warnings.append(
            f"{len(overlapping_nct_ids)} studies matched more than one "
            "comparison group and contribute to multiple series."
        )

    empty_groups = [
        label
        for label in cleaned_names.values()
        if not studies_by_group_and_year[label]
    ]

    if empty_groups:
        warnings.append(
            "No exact intervention-name matches were found for: "
            + ", ".join(empty_groups)
            + "."
        )

    return ComparisonResult(
        series=series,
        total_studies=len(study_list),
        included_studies=len(included_nct_ids),
        excluded_studies=excluded_count,
        overlapping_studies=len(overlapping_nct_ids),
        citations=citations,
        warnings=warnings,
    )


def _normalize_requested_names(
    names: Iterable[str],
) -> dict[str, str]:
    normalized_names: dict[str, str] = {}

    for name in names:
        display_name = " ".join(name.split())

        if not display_name:
            continue

        normalized_names.setdefault(
            _normalize_name(display_name),
            display_name,
        )

    return normalized_names


def _normalize_name(value: str) -> str:
    return " ".join(value.casefold().split())