from collections import defaultdict
from collections.abc import Iterable
from itertools import combinations

from app.analysis.models import (
    CitationGroup,
    NetworkEdge,
    NetworkNode,
    RelationshipNetworkResult,
)
from app.clinical_trials.normalized_models import NormalizedStudy


def analyze_intervention_relationships(
    studies: Iterable[NormalizedStudy],
    *,
    minimum_edge_weight: int = 1,
    max_nodes: int | None = 25,
) -> RelationshipNetworkResult:
    """
    Build a co-occurrence network from normalized intervention names.

    Each node represents an intervention. An edge connects two interventions
    when they appear in the same study. Edge weight is the number of distinct
    studies in which the pair co-occurs.
    """

    if minimum_edge_weight <= 0:
        raise ValueError("minimum_edge_weight must be greater than zero")

    if max_nodes is not None and max_nodes <= 0:
        raise ValueError("max_nodes must be greater than zero or None")

    study_list = list(studies)

    studies_by_intervention: dict[str, set[str]] = defaultdict(set)
    studies_by_pair: dict[tuple[str, str], set[str]] = defaultdict(set)

    display_labels: dict[str, str] = {}

    included_nct_ids: set[str] = set()
    excluded_count = 0

    for study in study_list:
        interventions = _extract_interventions(study)

        if not interventions:
            excluded_count += 1
            continue

        included_nct_ids.add(study.nct_id)

        normalized_names = sorted(interventions)

        for normalized_name in normalized_names:
            studies_by_intervention[normalized_name].add(study.nct_id)

            display_labels.setdefault(
                normalized_name,
                interventions[normalized_name],
            )

        for source, target in combinations(normalized_names, 2):
            studies_by_pair[(source, target)].add(study.nct_id)

    ranked_nodes = sorted(
        studies_by_intervention.items(),
        key=lambda item: (-len(item[1]), display_labels[item[0]]),
    )

    total_nodes = len(ranked_nodes)

    if max_nodes is not None:
        ranked_nodes = ranked_nodes[:max_nodes]

    retained_node_ids = {
        normalized_name
        for normalized_name, _ in ranked_nodes
    }

    nodes = [
        NetworkNode(
            id=normalized_name,
            label=display_labels[normalized_name],
            study_count=len(nct_ids),
        )
        for normalized_name, nct_ids in ranked_nodes
    ]

    retained_pairs = [
        (pair, nct_ids)
        for pair, nct_ids in studies_by_pair.items()
        if pair[0] in retained_node_ids
        and pair[1] in retained_node_ids
        and len(nct_ids) >= minimum_edge_weight
    ]

    retained_pairs.sort(
        key=lambda item: (
            -len(item[1]),
            display_labels[item[0][0]],
            display_labels[item[0][1]],
        )
    )

    edges = [
        NetworkEdge(
            source=source,
            target=target,
            weight=len(nct_ids),
        )
        for (source, target), nct_ids in retained_pairs
    ]

    citations = [
        CitationGroup(
            key=f"{source}|{target}",
            nct_ids=sorted(nct_ids),
        )
        for (source, target), nct_ids in retained_pairs
    ]

    warnings: list[str] = []

    if excluded_count:
        warnings.append(
            f"{excluded_count} studies were excluded because they had no "
            "usable intervention names."
        )

    if max_nodes is not None and total_nodes > max_nodes:
        warnings.append(
            f"The network was limited to the top {max_nodes} of "
            f"{total_nodes} interventions."
        )

    removed_edge_count = sum(
        1
        for pair, nct_ids in studies_by_pair.items()
        if pair[0] in retained_node_ids
        and pair[1] in retained_node_ids
        and len(nct_ids) < minimum_edge_weight
    )

    if removed_edge_count:
        warnings.append(
            f"{removed_edge_count} relationships below the minimum edge "
            "weight were omitted."
        )

    if not nodes:
        warnings.insert(
            0,
            "No usable intervention relationships were found.",
        )
    elif not edges:
        warnings.append(
            "Interventions were found, but no qualifying co-occurrence "
            "relationships were identified."
        )

    return RelationshipNetworkResult(
        nodes=nodes,
        edges=edges,
        total_studies=len(study_list),
        included_studies=len(included_nct_ids),
        excluded_studies=excluded_count,
        citations=citations,
        warnings=warnings,
    )


def _extract_interventions(
    study: NormalizedStudy,
) -> dict[str, str]:
    interventions: dict[str, str] = {}

    for intervention in study.interventions:
        display_name = " ".join(intervention.name.split())

        if not display_name:
            continue

        normalized_name = _normalize_name(display_name)

        interventions.setdefault(
            normalized_name,
            display_name,
        )

    return interventions


def _normalize_name(value: str) -> str:
    return " ".join(value.casefold().split())