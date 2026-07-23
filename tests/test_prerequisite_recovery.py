import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEPS = os.path.join(_ROOT, "data", "os_taxonomy", "dependencies.json")


def test_load_dependencies_reads_os_taxonomy_rows():
    from tools.os_taxonomy_adapter import load_dependencies
    rows = load_dependencies(_DEPS)
    assert isinstance(rows, list) and len(rows) == 4
    r = rows[0]
    assert set(r) >= {"topicId", "prerequisiteId", "strength", "reason"}
    assert {row["strength"] for row in rows} == {"hard", "soft"}


def test_subgraph_for_groups_by_strength_and_finds_non_edges():
    from tools.os_taxonomy_adapter import load_dependencies, subgraph_for
    sg = subgraph_for(load_dependencies(_DEPS), "B_matter_movement")
    assert sg["target"] == "B_matter_movement"
    assert sg["hard"] == ["Ah_food_chains"]
    assert sg["soft"] == ["As_biodiversity"]
    # Aprime n'est PAS un prérequis de B -> seul non_edge (candidat de spécificité, corrélé via Z)
    assert sg["non_edges"] == ["Aprime_rainforest_web"]
    # Z est un prérequis TRANSITIF de B (via Ah) -> EXCLU des non_edges
    assert "Z_producers" not in sg["non_edges"]
    assert "Ah_food_chains" not in sg["non_edges"]


def test_fixture_subgraph_is_the_single_source():
    from tools.os_taxonomy_adapter import fixture_subgraph
    sg = fixture_subgraph()
    assert sg["target"] == "B_matter_movement"
    assert sg["hard"] == ["Ah_food_chains"] and sg["soft"] == ["As_biodiversity"]
