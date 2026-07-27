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


def test_effective_competence_transfers_from_ancestor():
    from tools.ground_truth_worlds import effective_competence, fixture_world
    w = fixture_world()
    # Ah : own 0.1 + transfer 0.9 * eff(Z=1.0) = 1.0 (borné)
    assert effective_competence("Ah_food_chains", w) == 1.0
    # zeroer Z fait chuter Ah (perd le transfert) -> 0.1
    assert abs(effective_competence("Ah_food_chains", w, zeroed={"Z_producers"}) - 0.1) < 1e-9
    # zeroer Ah lui-même -> 0.0 (ablation chirurgicale)
    assert effective_competence("Ah_food_chains", w, zeroed={"Ah_food_chains"}) == 0.0


def test_acquisition_prob_matches_the_imposed_gate():
    from tools.ground_truth_worlds import acquisition_prob, fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    w, sg = fixture_world(), fixture_subgraph()
    assert abs(acquisition_prob(sg, w) - 0.7) < 1e-9                                  # intact
    assert abs(acquisition_prob(sg, w, zeroed={"Ah_food_chains"}) - 0.3) < 1e-9       # ablate dur
    assert abs(acquisition_prob(sg, w, zeroed={"As_biodiversity"}) - 0.5) < 1e-9      # ablate mou
    assert abs(acquisition_prob(sg, w, zeroed={"Aprime_rainforest_web"}) - 0.7) < 1e-9  # non-arête = inerte


def test_acquisition_scores_are_alive_and_seed_deterministic():
    from tools.ground_truth_worlds import acquisition_scores, fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    w, sg = fixture_world(), fixture_subgraph()
    seeds = list(range(12))
    s = acquisition_scores(sg, w, seeds)
    assert len(s) == 12
    assert 15.0 < sorted(s)[len(s) // 2] < 200.0, "métrique doit être VIVANTE"
    assert acquisition_scores(sg, w, seeds) == s, "doit être déterministe par seed"


def test_probe_recovers_hard_and_noops_on_correlated_non_edge():
    from tools.prerequisite_recovery_probe import run_prerequisite_recovery_probe
    from tools.ground_truth_worlds import fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    out = run_prerequisite_recovery_probe(fixture_subgraph(), fixture_world(), seeds=list(range(12)))
    by = {e["prereq"]: e for e in out["edges"]}
    assert by["Ah_food_chains"]["verdict"] == "X_DEMANDED"           # prérequis dur récupéré
    assert by["Aprime_rainforest_web"]["verdict"] == "X_DECOY"       # non-arête corrélée = inerte
    # monotonie : dur > mou > non-arête (~1)
    assert by["Ah_food_chains"]["ratio"] > by["As_biodiversity"]["ratio"] > by["Aprime_rainforest_web"]["ratio"]
    assert abs(by["Aprime_rainforest_web"]["ratio"] - 1.0) < 1e-9


def test_graph_recovery_is_perfect_on_the_fixture():
    from tools.prerequisite_recovery_probe import run_prerequisite_recovery_probe
    from tools.ground_truth_worlds import fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    rec = run_prerequisite_recovery_probe(fixture_subgraph(), fixture_world(), seeds=list(range(12)))["recovery"]
    assert rec["precision"] == 1.0 and rec["recall"] == 1.0
    assert rec["recovered"] == ["Ah_food_chains"]


def test_preflight_passes_and_main_reports_go():
    from tools.prerequisite_recovery_probe import main
    assert main() == 0, "le pré-vol + le go/no-go doivent PASSER sur la fixture calibrée"
