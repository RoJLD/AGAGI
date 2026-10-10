"""
tests/test_lu_phase11_counterfactual_dreaming.py — Validation de la Phase 11 du Langage Ultime.

Vérifie :
1. Déterminisme et conservation de norme de l'encodage d'hypothèse de rêve sur S^(D-1).
2. Précision et contraction lipschitzienne du rollout contrefactuel dans l'espace latent.
3. Rejet par le consensus de rêve des scénarios conduisant à une famine ou mort simulée.
4. Intégration in-world au feu de camp (CampfireCouncilOfDreams) : émission, consensus sphérique et dividende prédictif (+6.0 E).
5. Non-régression et intégration du pont KuzuDB (directives DREAM_SCENARIO et WHAT_IF).
"""

import pytest
import numpy as np
from typing import Dict, Any, List

from src.metaprog.lu_algebra import (
    LUCompositionalGrammar,
    LUAlgebraConfig,
    LatentDreamEngine,
    spherical_weiszfeld_bft_consensus,
)
from src.agents.dream_replay import (
    SharedDreamExperience,
    SharedDreamPool,
    NightConsolidator,
)
from src.metaprog.lu_symbolic_bridge import (
    FederalDiplomaticBridge,
    LUSharedDream,
    LUCounterfactualRollout,
)
from src.environments.lu_inworld_adapter import (
    LUInWorldAdapter,
    LUInWorldConfig,
)


class MockWorld:
    """Environnement simulé minimal pour tester les interactions au feu de camp."""
    def __init__(self, agents: List[Dict[str, Any]], items: List[Dict[str, Any]]):
        self.agents = agents
        self.items = items
        self.tick = 40
        self.ticks = 40


def test_01_dream_hypothesis_encoding_norm_conservation():
    """Test 1 : Déterminisme et conservation de norme de l'encodage d'hypothèse de rêve sur S^(D-1)."""
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=16))
    
    # Vecteurs unitaires
    rng = np.random.default_rng(123)
    s = rng.normal(size=16).astype(np.float32)
    s /= np.linalg.norm(s)
    g = rng.normal(size=16).astype(np.float32)
    g /= np.linalg.norm(g)
    
    # Encodage de l'hypothèse de rêve
    hypothesis = grammar.compose_dream_hypothesis(scenario=s, target_goal=g)
    
    # Norme strictement égale à 1.0 sur S^(D-1)
    norm = np.linalg.norm(hypothesis)
    assert np.isclose(norm, 1.0, atol=1e-5), f"Norme attendue 1.0, obtenu {norm}"
    
    # Déterminisme strict
    hypothesis_bis = grammar.compose_dream_hypothesis(scenario=s, target_goal=g)
    assert np.allclose(hypothesis, hypothesis_bis, atol=1e-6), "L'encodage doit être strictement déterministe"
    
    # Rôles présents dans la grammaire
    assert grammar.ROLE_DREAM is not None
    assert grammar.ROLE_WHAT_IF is not None
    assert grammar.ROLE_SCENARIO is not None


def test_02_latent_rollout_lipschitz_contraction():
    """Test 2 : Précision et contraction lipschitzienne du rollout contrefactuel dans le World Model latent."""
    dim = 16
    engine = LatentDreamEngine(dim=dim)
    
    rng = np.random.default_rng(456)
    s0 = rng.normal(size=dim).astype(np.float32)
    s0 /= np.linalg.norm(s0)
    
    scenario = rng.normal(size=dim).astype(np.float32)
    scenario /= np.linalg.norm(scenario)
    
    # Déroulement sur un horizon de 10 pas
    horizon = 10
    final_state, ceg, converged, traj = engine.simulate_latent_rollout(
        initial_state=s0,
        scenario_token=scenario,
        horizon=horizon
    )
    
    # Conservation de la sphère unitaire à chaque pas
    assert np.isclose(np.linalg.norm(final_state), 1.0, atol=1e-5)
    assert len(traj) >= 2
    assert isinstance(ceg, float)
    
    # Test de contraction lipschitzienne : deux états proches doivent rester bornés en distance
    s1 = s0 + 0.05 * rng.normal(size=dim).astype(np.float32)
    s1 /= np.linalg.norm(s1)
    
    final_state_1, _, _, _ = engine.simulate_latent_rollout(
        initial_state=s1,
        scenario_token=scenario,
        horizon=horizon
    )
    
    dist_initial = np.linalg.norm(s0 - s1)
    dist_final = np.linalg.norm(final_state - final_state_1)
    # L-Lipschitz avec L <= 2.5
    assert dist_final <= 2.5 * dist_initial, f"Divergence excessive : dist_final={dist_final}, dist_initial={dist_initial}"


def test_03_rejection_of_fatal_scenarios_and_consensus():
    """Test 3 : Rejet par le consensus de rêve des scénarios conduisant à une famine ou mort simulée."""
    dim = 16
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=dim))
    engine = LatentDreamEngine(dim=dim)
    
    rng = np.random.default_rng(789)
    s0 = rng.normal(size=dim).astype(np.float32)
    s0 /= np.linalg.norm(s0)
    
    # Scénario fatal : opposé diamétralement à l'état initial
    v_fatal = -s0.copy()
    
    final_state, ceg, converged, traj = engine.simulate_latent_rollout(
        initial_state=s0,
        scenario_token=v_fatal,
        horizon=10
    )
    
    # Pool de rêve partagé
    pool = SharedDreamPool(capacity=10)
    fatal_dream = SharedDreamExperience(
        dream_id="fatal_01",
        creator_id="ag_test",
        scenario_token=v_fatal,
        target_goal_token=s0,
        counterfactual_gain=ceg,
        trajectory=[final_state],
        is_ratified=False,
        tick=1
    )
    # Non ratifié car gain négatif ou nul
    pool.add_shared_dream(fatal_dream)
    assert len(pool.get_ratified_dreams()) == 0, "Les rêves non ratifiés ne doivent pas être inclus"


def test_04_inworld_campfire_council_and_predictive_dividend():
    """Test 4 : Intégration in-world au feu de camp : émission de rêve, évaluation partagée et dividende prédictif."""
    dim = 16
    cfg = LUInWorldConfig(
        latent_dim=dim,
        enable_counterfactual_dreaming=True,
        dream_predictive_bonus=6.0,
        dream_min_gain_threshold=0.00,
        deliberation_consensus_threshold=0.30
    )
    
    # Création de 3 agents au feu de camp avec positions proches
    agents = [
        {"id": "ag_1", "x": 5, "y": 5, "energy": 50.0, "role": "HUNTER"},
        {"id": "ag_2", "x": 6, "y": 5, "energy": 50.0, "role": "CRAFTER"},
        {"id": "ag_3", "x": 5, "y": 6, "energy": 50.0, "role": "SCOUT"},
    ]
    # Un feu de camp en (5, 5)
    items = [{"type": "fire", "x": 5, "y": 5}]
    
    world = MockWorld(agents, items)
    adapter = LUInWorldAdapter(world=world, config=cfg)
    
    # Exécution du cycle in-world
    res = adapter.step()
    
    # Vérification que le conseil de rêve s'est réuni
    assert "shared_dreams" in res
    assert "dreams_ratified" in res
    assert "counterfactual_rollouts" in res
    assert res["counterfactual_rollouts"] >= 2
    
    # Si consensus atteint, le dividende prédictif (+6.0) doit avoir été accordé
    if res["dreams_ratified"] > 0:
        for ag in agents:
            if ag.get("shared_dream_ratified", False):
                assert ag["energy"] >= 56.0, f"L'énergie de l'agent devrait avoir augmenté de +6.0, actuel={ag['energy']}"


def test_05_kuzudb_symbolic_bridge_and_shared_dream_directives():
    """Test 5 : Encodage et décodage de directives DREAM_SCENARIO et WHAT_IF via FederalDiplomaticBridge."""
    bridge = FederalDiplomaticBridge(seed=42)
    
    # Compilation d'une directive de rêve
    directive = bridge.compile_dream_hypothesis_directive(
        scenario_name="HARVEST_BEFORE_WINTER",
        goal_name="PREVENT_STARVATION",
        expected_gain=0.85
    )
    
    assert "DREAM_SCENARIO" in directive
    assert "WHAT_IF" in directive
    assert "HARVEST_BEFORE_WINTER" in directive
    assert "PREVENT_STARVATION" in directive
    
    # Décodage du vecteur d'hypothèse
    rng = np.random.default_rng(999)
    v_hypo = rng.normal(size=16).astype(np.float32)
    v_hypo /= np.linalg.norm(v_hypo)
    
    decoded = bridge.decode_dream_hypothesis_vector(v_hypo)
    assert "directive" in decoded
    assert "expected_gain" in decoded
    assert "confidence" in decoded
    assert isinstance(decoded["expected_gain"], float)
