"""
tests/test_lu_phase15_demiurgic_entanglement.py — Tests Unitaires & Validation TDD pour le Langage Ultime (Phase 15).

Conforme aux 12 Commandements AGIseed :
- Commandement 3 : Haute Performance (Vectorisation pure NumPy).
- Commandement 5 : Transparent & Auditable (Lattice Memory).
- Commandement 7 : Validation Rigoureuse (Test-Driven Metaprogramming).
- Commandement 9 : Stabilité Numérique (Cohérence de phase, conservation unitaire et absence de divergence).
"""

import pytest
import numpy as np
from typing import Dict, Any

from src.metaprog.lu_algebra import (
    LUCompositionalGrammar,
    LUAlgebraConfig,
    SemanticEntanglementEngine,
    MultiverseDemiurgeEngine,
    circular_convolution,
    circular_correlation,
)
from src.metaprog.lu_symbolic_bridge import (
    FederalDiplomaticBridge,
    LUSymbolicBridgeConfig,
    LUSemanticEntanglement,
    LUDemiurgicCollapse,
)
from src.environments.lu_inworld_adapter import (
    LUInWorldAdapter,
    LUInWorldConfig,
)


class MockWorld:
    """Monde simulé pour validation in-world de la Phase 15."""
    def __init__(self, dim: int = 16, num_agents: int = 4):
        self.size = 16
        self.tick = 10
        self.ticks = 10
        self.dim = dim
        self.agents = []
        rng = np.random.default_rng(42)
        for i in range(num_agents):
            v = rng.standard_normal(dim).astype(np.float32)
            v /= np.linalg.norm(v) + 1e-12
            self.agents.append({
                "id": f"ag_{i}",
                "x": float(4 * i),
                "y": float(4 * i),
                "energy": 45.0,
                "lu_latent": v,
                "age": 20,
            })


def test_phase15_canonical_roles_and_bell_pair_synthesis():
    """Test 1 : Vérifie la synthèse de paires intriquées et les rôles canoniques unitaires sur S^(D-1)."""
    dim = 16
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=dim, seed=42))

    assert hasattr(grammar, "ROLE_ENTANGLEMENT")
    assert hasattr(grammar, "ROLE_RETROCAUSALITY")
    assert hasattr(grammar, "ROLE_DEMIURGE")
    assert hasattr(grammar, "ROLE_SUPERPOSITION")

    for role_name in ["ROLE_ENTANGLEMENT", "ROLE_RETROCAUSALITY", "ROLE_DEMIURGE", "ROLE_SUPERPOSITION"]:
        v = getattr(grammar, role_name)
        assert len(v) == dim
        assert pytest.approx(np.linalg.norm(v), abs=1e-5) == 1.0

    engine = SemanticEntanglementEngine(dim=dim, grammar=grammar, seed=42)

    rng = np.random.default_rng(123)
    va = rng.standard_normal(dim).astype(np.float32)
    vb = rng.standard_normal(dim).astype(np.float32)

    psi_ab = engine.synthesize_bell_pair(va, vb)
    assert len(psi_ab) == dim
    assert pytest.approx(np.linalg.norm(psi_ab), abs=1e-5) == 1.0
    assert engine.entangled_pairs_count == 1


def test_phase15_bell_chsh_violation_and_instantaneous_propagation():
    """Test 2 : Vérifie la violation formelle de Bell-CHSH (S_CHSH >= 2.10 > 2.0) et la transmission instantanée."""
    dim = 32
    engine = SemanticEntanglementEngine(dim=dim, seed=42)

    rng = np.random.default_rng(999)
    va = rng.standard_normal(dim).astype(np.float32)
    vb = rng.standard_normal(dim).astype(np.float32)

    psi_ab = engine.synthesize_bell_pair(va, vb)
    chsh_score = engine.measure_bell_chsh_correlation(psi_ab)

    # Violation formelle de l'inégalité classique de Bell (S <= 2.0)
    assert chsh_score >= 2.10
    assert chsh_score <= 2.83  # Borne de Tsirelson

    # Pureté quantique Tr(rho^2) = 1.0 sur état pur
    purity = engine.compute_entanglement_purity(psi_ab)
    assert pytest.approx(purity, abs=1e-4) == 1.0

    # Propagation instantanée d'insight
    insight_a = va.copy()
    projected_b = engine.propagate_instantaneous_insight(psi_ab, insight_a)
    assert len(projected_b) == dim
    assert pytest.approx(np.linalg.norm(projected_b), abs=1e-5) == 1.0


def test_phase15_multiverse_demiurge_and_retrocausal_collapse():
    """Test 3 : Vérifie la résolution du champ démiurgique rétrocausal et le collapse de branches multivers."""
    dim = 16
    engine = MultiverseDemiurgeEngine(dim=dim, lambda_retro=0.25, mu_terra=0.35, seed=42)

    rng = np.random.default_rng(77)
    retarded = rng.standard_normal(dim).astype(np.float32)
    attractor = rng.standard_normal(dim).astype(np.float32)

    phi_dem = engine.step_demiurgic_field(retarded_field=retarded, advanced_attractor=attractor)
    assert len(phi_dem) == dim
    assert pytest.approx(np.linalg.norm(phi_dem), abs=1e-5) == 1.0
    assert engine.step_count == 1

    spec = engine.get_demiurge_spec()
    assert spec["retrocausal_potential"] is not None
    assert spec["latent_norm"] == 1.0

    # Collapse multivers parmi 4 branches candidates
    cands = [rng.standard_normal(dim).astype(np.float32) for _ in range(4)]
    best_branch, best_idx, score = engine.collapse_multiverse_branch(cands, future_objective=attractor)
    assert len(best_branch) == dim
    assert 0 <= best_idx < 4
    assert -1.0 <= score <= 1.0
    assert engine.total_collapses_count == 1


def test_phase15_inworld_integration_resonance_and_demiurgic_dividend():
    """Test 4 : Vérifie l'exécution in-world, le collapse d'intentions et l'octroi du dividende démiurgique (+25.0 E)."""
    dim = 16
    world = MockWorld(dim=dim, num_agents=4)
    config = LUInWorldConfig(
        latent_dim=dim,
        enable_demiurgic_multiverse=True,
        demiurgic_dividend_bonus=25.0,
    )
    adapter = LUInWorldAdapter(world=world, config=config)

    # 1. Étape de résolution du champ démiurgique in-world
    snapshot = adapter.step_demiurgic_multiverse()
    assert snapshot["chsh_score"] >= 2.10
    assert adapter.demiurgic_steps_count == 1
    assert adapter.entangled_pairs_count >= 1

    # 2. Effondrement cohérent et octroi du dividende (+25.0 E)
    init_energies = [ag["energy"] for ag in world.agents]
    succ, bonus = adapter.collapse_entangled_intentions(world.agents)
    assert succ is True
    assert bonus == 25.0

    for i, ag in enumerate(world.agents):
        assert ag["energy"] == init_energies[i] + 25.0
        assert ag.get("demiurgic_collapses_count", 0) >= 1
        assert ag.get("multiverse_aligned") is True

    assert adapter.demiurgic_dividends_count == len(world.agents)


def test_phase15_lattice_memory_recording():
    """Test 5 : Vérifie l'enregistrement et la traçabilité Lattice Memory dans FederalDiplomaticBridge."""
    bridge = FederalDiplomaticBridge(seed=42)


    # 1. Enregistrement d'une paire intriquée
    ent = bridge.record_entanglement_pair(
        entanglement_id="ent_test_42",
        chsh_score=2.35,
        purity=1.0,
        correlation_gain=0.35,
        tick=10,
    )
    assert isinstance(ent, LUSemanticEntanglement)
    assert "ent_test_42" in bridge.lattice_nodes
    assert bridge.lattice_nodes["ent_test_42"].chsh_score == 2.35

    # 2. Enregistrement d'un collapse démiurgique
    dem = bridge.record_demiurgic_event(
        collapse_id="demiurge_test_1",
        retro_potential=0.48,
        energy_injected=25.0,
        agents_aligned=4,
        version=1,
        tick=10,
    )
    assert isinstance(dem, LUDemiurgicCollapse)
    assert "demiurge_test_1" in bridge.lattice_nodes
    assert bridge.lattice_nodes["demiurge_test_1"].energy_injected == 25.0
