from collections import defaultdict
from collections.abc import Iterable

from app.analysis.models import (
    CitationGroup,
    TimeTrendPoint,
    TimeTrendResult,
)
from app.clinical_trials.normalized_models import NormalizedStudy


def analyze_time_trend(
    studies: Iterable[NormalizedStudy],
    *,
    start_year: int | None = None,
    end_year: int | None = None,
    fill_missing_years: bool = True,
) -> TimeTrendResult:
    """
    Aggregate clinical studies by normalized start year.

    Studies without a usable start year are excluded from the aggregation.
    Optional year boundaries are inclusive.
    """

    study_list = list(studies)

    studies_by_year: dict[int, list[str]] = defaultdict(list)
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

        studies_by_year[year].append(study.nct_id)

    if not studies_by_year:
        warnings = ["No studies with usable start dates matched the requested range."]

        if excluded_count:
            warnings.append(
                f"{excluded_count} studies were excluded because their "
                "start date was missing or invalid."
            )

        return TimeTrendResult(
            points=[],
            total_studies=len(study_list),
            included_studies=0,
            excluded_studies=excluded_count,
            citations=[],
            warnings=warnings,
        )

    minimum_year = start_year if start_year is not None else min(studies_by_year)
    maximum_year = end_year if end_year is not None else max(studies_by_year)

    if fill_missing_years:
        years = range(minimum_year, maximum_year + 1)
    else:
        years = sorted(studies_by_year)

    points = [
        TimeTrendPoint(
            year=year,
            count=len(studies_by_year.get(year, [])),
        )
        for year in years
    ]

    citations = [
        CitationGroup(
            key=str(year),
            nct_ids=sorted(studies_by_year.get(year, [])),
        )
        for year in years
        if studies_by_year.get(year)
    ]

    warnings: list[str] = []

    if excluded_count:
        warnings.append(
            f"{excluded_count} studies were excluded because their "
            "start date was missing or invalid."
        )

    return TimeTrendResult(
        points=points,
        total_studies=len(study_list),
        included_studies=sum(point.count for point in points),
        excluded_studies=excluded_count,
        citations=citations,
        warnings=warnings,
    )