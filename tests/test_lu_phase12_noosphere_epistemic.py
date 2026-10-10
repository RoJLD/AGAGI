"""
tests/test_lu_phase12_noosphere_epistemic.py — Validation de la Phase 12 du Langage Ultime.

Vérifie :
1. Conservation de norme sur S^(D-1), déterminisme et décomposition de résonance noosphérique.
2. Moteur de métacognition épistémique du second ordre (U_epistemic) et détection du biais de Dunning-Kruger.
3. Transport optimal multi-modal préservant la diversité des clans via Barycentre de Sinkhorn-Wasserstein sur S^(D-1).
4. Réseau télépathique in-world trans-mondes à longue distance et versement du dividende noosphérique (+8.0 E).
5. Traçabilité Lattice Memory / directives Cypher de résonance noosphérique et auditabilité.
"""

import pytest
import numpy as np
from typing import Dict, Any, List

from src.metaprog.lu_algebra import (
    LUCompositionalGrammar,
    LUAlgebraConfig,
    EpistemicUncertaintyEngine,
    spherical_sinkhorn_barycenter,
)
from src.metaprog.lu_symbolic_bridge import (
    FederalDiplomaticBridge,
    LUNoosphereField,
    LUEpistemicInsight,
)
from src.environments.lu_inworld_adapter import (
    LUInWorldAdapter,
    LUInWorldConfig,
    InscriptionStone,
)


class MockWorld:
    """Environnement simulé minimal pour tester les interactions trans-mondes."""
    def __init__(self, agents: List[Dict[str, Any]], items: List[Dict[str, Any]]):
        self.agents = agents
        self.items = items
        self.tick = 50
        self.ticks = 50
        self.size = 16


def test_01_noosphere_resonance_encoding_and_invariance():
    """Test 1 : Conservation de norme sur S^(D-1), déterminisme et extraction du contenu noosphérique."""
    dim = 16
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=dim))

    rng = np.random.default_rng(42)
    content = rng.normal(size=dim).astype(np.float32)
    content /= np.linalg.norm(content)

    resonance = rng.normal(size=dim).astype(np.float32)
    resonance /= np.linalg.norm(resonance)

    # 1. Composition noosphérique
    broadcast_vec = grammar.compose_noosphere_broadcast(content_token=content, resonance_token=resonance)

    assert broadcast_vec.shape == (dim,)
    norm_val = float(np.linalg.norm(broadcast_vec))
    assert abs(norm_val - 1.0) < 1e-5, f"Le Gigatoken noosphérique doit être unitaire sur S^(D-1), obtenu: {norm_val}"

    # 2. Déterminisme
    broadcast_vec_2 = grammar.compose_noosphere_broadcast(content_token=content, resonance_token=resonance)
    assert np.allclose(broadcast_vec, broadcast_vec_2, atol=1e-6), "La composition noosphérique doit être strictement déterministe"

    # 3. Extraction du contenu
    extracted = grammar.extract_noosphere_content(broadcast_vec)
    sim = float(np.dot(content, extracted))
    assert sim > 0.40, f"Le contenu extrait doit préserver la cohérence directionnelle, sim={sim}"


def test_02_epistemic_uncertainty_engine_and_dunning_kruger_detection():
    """Test 2 : Calibration épistémique du second ordre et détection de l'illusion de certitude."""
    dim = 16
    engine = EpistemicUncertaintyEngine(dim=dim, beta=1.0)

    rng = np.random.default_rng(101)
    s0 = rng.normal(size=dim).astype(np.float32)
    s0 /= np.linalg.norm(s0)

    # Scénario A : Concordant et stable (petite perturbation)
    scen_a = (s0 + 0.1 * rng.normal(size=dim).astype(np.float32))
    scen_a /= np.linalg.norm(scen_a)

    conf_a, u_a, high_unc_a = engine.evaluate_epistemic_calibration(
        state_token=s0,
        scenario_token=scen_a,
        threshold=0.45
    )

    assert abs(np.linalg.norm(u_a) - 1.0) < 1e-5, "U_epistemic doit être sur S^(D-1)"
    assert 0.0 <= conf_a <= 1.0, f"La confiance doit être normalisée in [0, 1], obtenu: {conf_a}"
    assert not high_unc_a, f"Un scénario concordant doit être confiant, obtenu conf={conf_a}"

    # Scénario B : Divergent et orthogonal (haute incertitude / Dunning-Kruger)
    v_orth = rng.normal(size=dim).astype(np.float32)
    v_orth -= float(np.dot(v_orth, s0)) * s0
    v_orth /= np.linalg.norm(v_orth)

    conf_b, u_b, high_unc_b = engine.evaluate_epistemic_calibration(
        state_token=s0,
        scenario_token=v_orth,
        threshold=0.45
    )

    assert conf_b < conf_a, f"La confiance d'un scénario orthogonal ({conf_b}) doit être inférieure à un scénario concordant ({conf_a})"
    assert high_unc_b, f"Un scénario orthogonal doit déclencher high_uncertainty=True, obtenu conf={conf_b}"


def test_03_spherical_sinkhorn_barycenter_multimodal_preservation():
    """Test 3 : Transport optimal de Wasserstein préservant la multi-modalité des cultures sur S^(D-1)."""
    dim = 16
    rng = np.random.default_rng(202)

    # Trois tribus avec croyances distinctes (chasseurs, fermiers, forgerons)
    v1 = rng.normal(size=dim).astype(np.float32)
    v1 /= np.linalg.norm(v1)
    v2 = rng.normal(size=dim).astype(np.float32)
    v2 /= np.linalg.norm(v2)
    v3 = rng.normal(size=dim).astype(np.float32)
    v3 /= np.linalg.norm(v3)

    distributions = [v1, v2, v3]
    weights = np.array([0.4, 0.3, 0.3], dtype=np.float32)

    barycenter, entropy = spherical_sinkhorn_barycenter(
        distributions=distributions,
        weights=weights,
        max_iters=15,
        epsilon=0.05
    )

    assert barycenter.shape == (dim,)
    norm_val = float(np.linalg.norm(barycenter))
    assert abs(norm_val - 1.0) < 1e-4, f"Le barycentre de Sinkhorn doit être unitaire sur S^(D-1), obtenu: {norm_val}"

    # Vérification de l'entropie positive (préservation de diversité multi-modale)
    assert entropy > 0.0, f"L'entropie de transport doit être strictement positive, obtenu: {entropy}"

    # Le barycentre doit être corrélé positivement avec chacune des trois tribus
    sims = [float(np.dot(barycenter, v)) for v in distributions]
    assert all(s > 0.0 for s in sims), f"Toutes les tribus doivent avoir une affinité positive avec le barycentre: {sims}"


def test_04_inworld_resonance_grid_and_long_distance_telepathy():
    """Test 4 : Télépathie longue distance trans-mondes via résonance stigmargique et dividende noosphérique."""
    dim = 16
    cfg = LUInWorldConfig(
        latent_dim=dim,
        enable_noosphere_grid=True,
        resonance_decay=0.10,
        noosphere_dividend=8.0,
        deliberation_consensus_threshold=0.30,
    )

    # Agents situés à des distances extrêmes (Monde 1 en (1, 1), Monde 2 en (15, 15))
    agents = [
        {"id": "ag_world1", "x": 1, "y": 1, "energy": 50.0, "role": "HUNTER"},
        {"id": "ag_world2", "x": 15, "y": 15, "energy": 50.0, "role": "CRAFTER"},
    ]
    items = []

    world = MockWorld(agents, items)
    adapter = LUInWorldAdapter(world=world, config=cfg)

    # Ajout d'une stèle pour initialiser la résonance
    rng = np.random.default_rng(303)
    stele_vec = rng.normal(size=dim).astype(np.float32)
    stele_vec /= np.linalg.norm(stele_vec)
    adapter.steles["stele_central"] = InscriptionStone(
        id="stele_central",
        x=8.0,
        y=8.0,
        z=0.0,
        topic="NOOSPHERE_CORE",
        content_vector=stele_vec,
        author_id="ag_founder",
        creation_tick=0,
    )

    # 1. Mise à jour de la grille de résonance
    grid = adapter.update_noosphere_resonance_grid(grid_size=16)
    assert grid.shape == (16, 16, dim)
    assert abs(np.linalg.norm(grid[8, 8]) - 1.0) < 1e-4

    # 2. Tenue du Conseil Synarchique Trans-Mondes
    initial_e1 = agents[0]["energy"]
    initial_e2 = agents[1]["energy"]

    council_res = adapter.convene_synarchic_noosphere_council(agents)

    assert council_res["ratified"], f"Le conseil synarchique doit être ratifié: {council_res}"
    assert council_res["dividend"] == 8.0

    # Les agents distants doivent avoir perçu le dividende noosphérique (+8.0 E)
    assert agents[0]["energy"] >= initial_e1 + 8.0
    assert agents[1]["energy"] >= initial_e2 + 8.0
    assert agents[0].get("noosphere_ratified", False)
    assert agents[1].get("noosphere_ratified", False)

    # 3. Validation dans adapter.step()
    step_res = adapter.step()
    assert "noosphere_broadcasts" in step_res
    assert "synarchic_councils" in step_res
    assert step_res["synarchic_councils"] >= 1


def test_05_kuzudb_noosphere_directives_and_auditability():
    """Test 5 : Traçabilité Lattice Memory et directives Cypher de résonance noosphérique."""
    bridge = FederalDiplomaticBridge(seed=42)
    dim = 16

    rng = np.random.default_rng(404)
    content_vec = rng.normal(size=dim).astype(np.float32)
    content_vec /= np.linalg.norm(content_vec)

    # 1. Enregistrement d'un broadcast noosphérique
    field = bridge.record_noosphere_broadcast(
        broadcast_id="noo_50_1",
        content_vector=content_vec,
        resonance_freq=0.88,
        sender_id="ag_champion",
        tick=50,
    )
    assert isinstance(field, LUNoosphereField)
    assert field.broadcast_id == "noo_50_1"
    assert field.resonance_frequency == 0.88

    # 2. Compilation de la directive NOOSPHERE_BROADCAST
    cypher_broadcast = bridge.compile_noosphere_broadcast_directive(field)
    assert "CREATE (n:NoosphereField" in cypher_broadcast
    assert "broadcast_id: 'noo_50_1'" in cypher_broadcast

    # 3. Enregistrement et directive EPISTEMIC_QUERY
    u_vec = rng.normal(size=dim).astype(np.float32)
    u_vec /= np.linalg.norm(u_vec)
    insight = bridge.record_epistemic_insight(
        insight_id="ins_50_1",
        agent_id="ag_thinker",
        confidence_scalar=0.38,
        uncertainty_vector=u_vec,
        high_uncertainty=True,
        tick=50,
    )
    assert isinstance(insight, LUEpistemicInsight)
    assert insight.high_uncertainty is True

    cypher_epistemic = bridge.compile_epistemic_query_directive(insight)
    assert "CREATE (e:EpistemicInsight" in cypher_epistemic
    assert "high_uncertainty: true" in cypher_epistemic

    # 4. Directive SINKHORN_RATIFY
    bary_vec = rng.normal(size=dim).astype(np.float32)
    bary_vec /= np.linalg.norm(bary_vec)
    cypher_ratify = bridge.compile_sinkhorn_ratification_directive(
        council_id="counc_50_1",
        barycenter_vector=bary_vec,
        entropy=0.75,
        participant_ids=["ag_w1", "ag_w2"],
        tick=50,
    )
    assert "CREATE (c:SynarchicCouncil" in cypher_ratify
    assert "entropy: 0.75" in cypher_ratify
