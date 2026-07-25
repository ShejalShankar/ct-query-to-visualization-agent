from collections import defaultdict
from collections.abc import Iterable

from app.analysis.models import (
    CitationGroup,
    DistributionDimension,
    DistributionPoint,
    DistributionResult,
)
from app.clinical_trials.normalized_models import NormalizedStudy


def analyze_distribution(
    studies: Iterable[NormalizedStudy],
    *,
    dimension: DistributionDimension,
) -> DistributionResult:
    """
    Count studies across a supported categorical dimension.

    A study contributes at most once to each category. For multi-valued
    dimensions, one study may contribute to multiple categories.
    """

    study_list = list(studies)

    studies_by_category: dict[str, set[str]] = defaultdict(set)
    included_nct_ids: set[str] = set()
    excluded_count = 0

    for study in study_list:
        categories = _extract_categories(
            study=study,
            dimension=dimension,
        )

        if not categories:
            excluded_count += 1
            continue

        included_nct_ids.add(study.nct_id)

        for category in categories:
            studies_by_category[category].add(study.nct_id)

    points = [
        DistributionPoint(
            category=category,
            count=len(nct_ids),
        )
        for category, nct_ids in sorted(
            studies_by_category.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )
    ]

    citations = [
        CitationGroup(
            key=point.category,
            nct_ids=sorted(studies_by_category[point.category]),
        )
        for point in points
    ]

    warnings: list[str] = []

    if excluded_count:
        warnings.append(
            f"{excluded_count} studies were excluded because they had no "
            f"usable value for '{dimension.value}'."
        )

    assignment_count = sum(point.count for point in points)

    if assignment_count > len(included_nct_ids):
        warnings.append(
            "Some studies contribute to multiple categories because the "
            f"'{dimension.value}' dimension is multi-valued."
        )

    if not points:
        warnings.insert(
            0,
            f"No usable values were found for '{dimension.value}'.",
        )

    return DistributionResult(
        dimension=dimension,
        points=points,
        total_studies=len(study_list),
        included_studies=len(included_nct_ids),
        excluded_studies=excluded_count,
        assignment_count=assignment_count,
        citations=citations,
        warnings=warnings,
    )


def _extract_categories(
    *,
    study: NormalizedStudy,
    dimension: DistributionDimension,
) -> set[str]:
    if dimension == DistributionDimension.PHASE:
        return _clean_categories(study.phases)

    if dimension == DistributionDimension.OVERALL_STATUS:
        return _clean_categories([study.overall_status])

    if dimension == DistributionDimension.SPONSOR_CLASS:
        if study.lead_sponsor is None:
            return set()

        return _clean_categories([study.lead_sponsor.sponsor_class])

    if dimension == DistributionDimension.INTERVENTION_TYPE:
        return _clean_categories(
            intervention.intervention_type
            for intervention in study.interventions
        )

    raise ValueError(f"Unsupported distribution dimension: {dimension}")


def _clean_categories(values: Iterable[object | None]) -> set[str]:
    categories: set[str] = set()

    for value in values:
        if value is None:
            continue

        normalized_value = getattr(value, "value", value)
        category = str(normalized_value).strip()

        if category:
            categories.add(category)

    return categories