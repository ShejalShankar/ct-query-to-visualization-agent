from datetime import date

import pytest

from app.analysis.relationship import (
    analyze_intervention_relationships,
)
from app.clinical_trials.normalized_models import (
    NormalizedIntervention,
    NormalizedInterventionType,
    NormalizedStudy,
)


def make_study(
    nct_id: str,
    *,
    intervention_names: list[str],
) -> NormalizedStudy:
    return NormalizedStudy(
        nct_id=nct_id,
        title=f"Study {nct_id}",
        overall_status="COMPLETED",
        start_date=date(2020, 1, 1),
        start_date_raw="2020-01-01",
        phases=[],
        conditions=[],
        interventions=[
            NormalizedIntervention(
                name=name,
                intervention_type=NormalizedInterventionType.DRUG,
            )
            for name in intervention_names
        ],
        lead_sponsor=None,
        countries=[],
    )


def test_builds_intervention_cooccurrence_network():
    studies = [
        make_study(
            "NCT00000001",
            intervention_names=[
                "Pembrolizumab",
                "Chemotherapy",
            ],
        ),
        make_study(
            "NCT00000002",
            intervention_names=[
                "Pembrolizumab",
                "Chemotherapy",
            ],
        ),
        make_study(
            "NCT00000003",
            intervention_names=[
                "Pembrolizumab",
                "Radiation",
            ],
        ),
    ]

    result = analyze_intervention_relationships(studies)

    node_counts = {
        node.label: node.study_count
        for node in result.nodes
    }

    assert node_counts == {
        "Pembrolizumab": 3,
        "Chemotherapy": 2,
        "Radiation": 1,
    }

    edge_weights = {
        (edge.source, edge.target): edge.weight
        for edge in result.edges
    }

    assert edge_weights[
        ("chemotherapy", "pembrolizumab")
    ] == 2

    assert edge_weights[
        ("pembrolizumab", "radiation")
    ] == 1


def test_deduplicates_repeated_intervention_within_study():
    studies = [
        make_study(
            "NCT00000001",
            intervention_names=[
                "Pembrolizumab",
                "Pembrolizumab",
                "Chemotherapy",
            ],
        )
    ]

    result = analyze_intervention_relationships(studies)

    assert len(result.nodes) == 2
    assert len(result.edges) == 1
    assert result.edges[0].weight == 1


def test_matching_is_case_insensitive():
    studies = [
        make_study(
            "NCT00000001",
            intervention_names=[
                "Pembrolizumab",
                "Chemotherapy",
            ],
        ),
        make_study(
            "NCT00000002",
            intervention_names=[
                " PEMBROLIZUMAB ",
                "chemotherapy",
            ],
        ),
    ]

    result = analyze_intervention_relationships(studies)

    assert len(result.nodes) == 2
    assert len(result.edges) == 1
    assert result.edges[0].weight == 2


def test_excludes_studies_without_interventions():
    studies = [
        make_study(
            "NCT00000001",
            intervention_names=["Pembrolizumab"],
        ),
        make_study(
            "NCT00000002",
            intervention_names=[],
        ),
    ]

    result = analyze_intervention_relationships(studies)

    assert result.included_studies == 1
    assert result.excluded_studies == 1
    assert any(
        "excluded" in warning
        for warning in result.warnings
    )


def test_filters_edges_by_minimum_weight():
    studies = [
        make_study(
            "NCT00000001",
            intervention_names=[
                "Pembrolizumab",
                "Chemotherapy",
            ],
        ),
        make_study(
            "NCT00000002",
            intervention_names=[
                "Pembrolizumab",
                "Chemotherapy",
            ],
        ),
        make_study(
            "NCT00000003",
            intervention_names=[
                "Pembrolizumab",
                "Radiation",
            ],
        ),
    ]

    result = analyze_intervention_relationships(
        studies,
        minimum_edge_weight=2,
    )

    assert len(result.edges) == 1
    assert result.edges[0].weight == 2

    assert any(
        "minimum edge weight" in warning
        for warning in result.warnings
    )


def test_limits_network_to_top_nodes():
    studies = [
        make_study(
            "NCT00000001",
            intervention_names=["A", "B"],
        ),
        make_study(
            "NCT00000002",
            intervention_names=["A", "C"],
        ),
        make_study(
            "NCT00000003",
            intervention_names=["A", "D"],
        ),
    ]

    result = analyze_intervention_relationships(
        studies,
        max_nodes=2,
    )

    assert len(result.nodes) == 2
    assert all(
        edge.source in {node.id for node in result.nodes}
        and edge.target in {node.id for node in result.nodes}
        for edge in result.edges
    )

    assert any(
        "top 2" in warning
        for warning in result.warnings
    )


def test_generates_edge_level_citations():
    studies = [
        make_study(
            "NCT00000002",
            intervention_names=[
                "Pembrolizumab",
                "Chemotherapy",
            ],
        ),
        make_study(
            "NCT00000001",
            intervention_names=[
                "Pembrolizumab",
                "Chemotherapy",
            ],
        ),
    ]

    result = analyze_intervention_relationships(studies)

    citation = result.citations[0]

    assert citation.key == "chemotherapy|pembrolizumab"
    assert citation.nct_ids == [
        "NCT00000001",
        "NCT00000002",
    ]


def test_single_interventions_produce_nodes_without_edges():
    studies = [
        make_study(
            "NCT00000001",
            intervention_names=["Pembrolizumab"],
        ),
        make_study(
            "NCT00000002",
            intervention_names=["Nivolumab"],
        ),
    ]

    result = analyze_intervention_relationships(studies)

    assert len(result.nodes) == 2
    assert result.edges == []
    assert any(
        "no qualifying co-occurrence" in warning
        for warning in result.warnings
    )


def test_returns_warning_when_no_interventions_exist():
    studies = [
        make_study(
            "NCT00000001",
            intervention_names=[],
        )
    ]

    result = analyze_intervention_relationships(studies)

    assert result.nodes == []
    assert result.edges == []
    assert result.included_studies == 0
    assert result.excluded_studies == 1
    assert result.warnings


def test_rejects_invalid_options():
    with pytest.raises(
        ValueError,
        match="minimum_edge_weight",
    ):
        analyze_intervention_relationships(
            [],
            minimum_edge_weight=0,
        )

    with pytest.raises(
        ValueError,
        match="max_nodes",
    ):
        analyze_intervention_relationships(
            [],
            max_nodes=0,
        )