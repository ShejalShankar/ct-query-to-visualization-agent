from datetime import date

from app.analysis.distribution import analyze_distribution
from app.analysis.models import DistributionDimension
from app.clinical_trials.normalized_models import (
    NormalizedIntervention,
    NormalizedInterventionType,
    NormalizedSponsor,
    NormalizedStudy,
)


def make_study(
    nct_id: str,
    *,
    phases: list[str] | None = None,
    overall_status: str | None = "COMPLETED",
    sponsor_class: str | None = None,
    intervention_types: list[NormalizedInterventionType] | None = None,
) -> NormalizedStudy:
    interventions = [
        NormalizedIntervention(
            name=f"Intervention {index}",
            intervention_type=intervention_type,
        )
        for index, intervention_type in enumerate(
            intervention_types or [],
            start=1,
        )
    ]

    lead_sponsor = (
        NormalizedSponsor(
            name="Example Sponsor",
            sponsor_class=sponsor_class,
        )
        if sponsor_class is not None
        else None
    )

    return NormalizedStudy(
        nct_id=nct_id,
        title=f"Study {nct_id}",
        overall_status=overall_status,
        start_date=date(2020, 1, 1),
        start_date_raw="2020-01-01",
        phases=phases or [],
        conditions=[],
        interventions=interventions,
        lead_sponsor=lead_sponsor,
        countries=[],
    )


def test_counts_distribution_by_status():
    studies = [
        make_study(
            "NCT00000001",
            overall_status="RECRUITING",
        ),
        make_study(
            "NCT00000002",
            overall_status="COMPLETED",
        ),
        make_study(
            "NCT00000003",
            overall_status="RECRUITING",
        ),
    ]

    result = analyze_distribution(
        studies,
        dimension=DistributionDimension.OVERALL_STATUS,
    )

    assert [
        (point.category, point.count)
        for point in result.points
    ] == [
        ("RECRUITING", 2),
        ("COMPLETED", 1),
    ]

    assert result.included_studies == 3
    assert result.assignment_count == 3
    assert result.excluded_studies == 0


def test_multi_phase_study_contributes_to_each_phase():
    studies = [
        make_study(
            "NCT00000001",
            phases=["PHASE1", "PHASE2"],
        ),
        make_study(
            "NCT00000002",
            phases=["PHASE2"],
        ),
    ]

    result = analyze_distribution(
        studies,
        dimension=DistributionDimension.PHASE,
    )

    assert [
        (point.category, point.count)
        for point in result.points
    ] == [
        ("PHASE2", 2),
        ("PHASE1", 1),
    ]

    assert result.included_studies == 2
    assert result.assignment_count == 3
    assert any(
        "multiple categories" in warning
        for warning in result.warnings
    )


def test_deduplicates_repeated_category_within_a_study():
    studies = [
        make_study(
            "NCT00000001",
            phases=["PHASE1", "PHASE1"],
        )
    ]

    result = analyze_distribution(
        studies,
        dimension=DistributionDimension.PHASE,
    )

    assert len(result.points) == 1
    assert result.points[0].category == "PHASE1"
    assert result.points[0].count == 1
    assert result.assignment_count == 1


def test_excludes_study_without_requested_dimension():
    studies = [
        make_study(
            "NCT00000001",
            phases=["PHASE1"],
        ),
        make_study(
            "NCT00000002",
            phases=[],
        ),
    ]

    result = analyze_distribution(
        studies,
        dimension=DistributionDimension.PHASE,
    )

    assert result.included_studies == 1
    assert result.excluded_studies == 1
    assert any(
        "excluded" in warning
        for warning in result.warnings
    )


def test_counts_distribution_by_sponsor_class():
    studies = [
        make_study(
            "NCT00000001",
            sponsor_class="INDUSTRY",
        ),
        make_study(
            "NCT00000002",
            sponsor_class="OTHER",
        ),
        make_study(
            "NCT00000003",
            sponsor_class="INDUSTRY",
        ),
    ]

    result = analyze_distribution(
        studies,
        dimension=DistributionDimension.SPONSOR_CLASS,
    )

    assert [
        (point.category, point.count)
        for point in result.points
    ] == [
        ("INDUSTRY", 2),
        ("OTHER", 1),
    ]


def test_counts_distribution_by_intervention_type():
    studies = [
        make_study(
            "NCT00000001",
            intervention_types=[
                NormalizedInterventionType.DRUG,
                NormalizedInterventionType.BIOLOGICAL,
            ],
        ),
        make_study(
            "NCT00000002",
            intervention_types=[
                NormalizedInterventionType.DRUG,
            ],
        ),
    ]

    result = analyze_distribution(
        studies,
        dimension=DistributionDimension.INTERVENTION_TYPE,
    )

    assert [
        (point.category, point.count)
        for point in result.points
    ] == [
        ("DRUG", 2),
        ("BIOLOGICAL", 1),
    ]


def test_generates_category_level_citations():
    studies = [
        make_study(
            "NCT00000002",
            overall_status="RECRUITING",
        ),
        make_study(
            "NCT00000001",
            overall_status="RECRUITING",
        ),
    ]

    result = analyze_distribution(
        studies,
        dimension=DistributionDimension.OVERALL_STATUS,
    )

    assert result.citations[0].key == "RECRUITING"
    assert result.citations[0].nct_ids == [
        "NCT00000001",
        "NCT00000002",
    ]


def test_returns_warning_when_no_values_exist():
    studies = [
        make_study(
            "NCT00000001",
            phases=[],
        ),
        make_study(
            "NCT00000002",
            phases=[],
        ),
    ]

    result = analyze_distribution(
        studies,
        dimension=DistributionDimension.PHASE,
    )

    assert result.points == []
    assert result.included_studies == 0
    assert result.excluded_studies == 2
    assert result.assignment_count == 0
    assert result.warnings