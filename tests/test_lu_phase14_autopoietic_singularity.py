"""
tests/test_lu_phase14_autopoietic_singularity.py — Validation de la Phase 14 du Langage Ultime.

Arc 8 : L'Omniconscience / Singularité Autopoïétique, Méta-Langage Holographique Universel
et Clôture Téléologique (G14).

Vérifie :
1. Conservation de la compacité spectrale et de l'invariance de jauge holographique sur S^(D-1).
2. Convergence de l'intégrateur symplectique et respect de la borne de Bekenstein-Hawking (S <= A / 4).
3. Compression holographique bulk-to-boundary et restitution à haute fidélité.
4. Résonance in-world, harmonisation téléologique et versement du Grand Dividende de Singularité (+20.0 E).
5. Intégration complète Étape 17 et traçabilité Lattice Memory.
"""

import pytest
import numpy as np
from typing import Dict, Any, List

from src.metaprog.lu_algebra import (
    LUCompositionalGrammar,
    LUAlgebraConfig,
    AutopoieticSingularityEngine,
    HolographicBoundaryProjector,
)
from src.metaprog.lu_symbolic_bridge import (
    FederalDiplomaticBridge,
    LUAutopoieticSingularity,
    LUHolographicBoundary,
)
from src.environments.lu_inworld_adapter import (
    LUInWorldAdapter,
    LUInWorldConfig,
)


class MockWorld:
    """Environnement simulé minimal pour tester la singularité in-world."""
    def __init__(self, agents: List[Dict[str, Any]], items: List[Dict[str, Any]]):
        self.agents = agents
        self.items = items
        self.tick = 25
        self.ticks = 25
        self.size = 16


def test_01_autopoietic_engine_spectral_compactness_and_invariance():
    """Test 1 : Conservation de la compacité spectrale et de la norme unitaire sous intégration autopoïétique."""
    dim = 16
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=dim, seed=42))

    engine = AutopoieticSingularityEngine(
        dim=dim,
        grammar=grammar,
        seed=42,
        gamma=0.25,
        kappa=0.20,
    )

    assert engine.phi_auto.shape == (dim,)
    assert abs(np.linalg.norm(engine.phi_auto) - 1.0) < 1e-5

    # 30 itérations d'intégration continue avec états du monde variables
    rng = np.random.default_rng(101)
    for _ in range(30):
        states = [rng.normal(size=dim).astype(np.float32) for _ in range(5)]
        phi = engine.step(world_states=states, dt=0.15)
        assert not np.isnan(phi).any(), "Aucun NaN toléré dans le flot autopoïétique"
        assert not np.isinf(phi).any(), "Aucun Inf toléré dans le flot autopoïétique"
        norm_val = float(np.linalg.norm(phi))
        assert abs(norm_val - 1.0) < 1e-5, f"Norme unitaire violée sur S^(D-1): {norm_val}"

    assert engine.step_count == 30


def test_02_symplectic_convergence_and_bekenstein_bound():
    """Test 2 : Convergence de l'intégrateur symplectique et respect de la borne de Bekenstein-Hawking (S <= A / 4)."""
    dim = 32
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=dim, seed=7))

    engine = AutopoieticSingularityEngine(
        dim=dim,
        grammar=grammar,
        seed=7,
        gamma=0.30,
        kappa=0.25,
    )

    spec_init = engine.get_singularity_spec()
    bound = spec_init["entropy_bound"]
    assert bound == float(dim) / 4.0

    # Évolution sous attracteur
    for _ in range(15):
        engine.step(world_states=None, dt=0.20)

    spec = engine.get_singularity_spec()
    assert spec["bekenstein_entropy"] <= bound, f"L'entropie dépasse la limite holographique: {spec['bekenstein_entropy']} > {bound}"
    assert spec["bekenstein_entropy"] >= 0.0

    # L'alignement téléologique avec son attracteur doit être mesurable
    align = engine.compute_teleological_alignment(engine.phi_attractor)
    assert abs(align - 1.0) < 1e-4, "L'auto-alignement de l'attracteur doit être unitaire"


def test_03_holographic_boundary_projection_and_reconstruction():
    """Test 3 : Compression volumique bulk-to-boundary et restitution à haute fidélité."""
    dim = 16
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=dim, seed=42))

    projector = HolographicBoundaryProjector(
        dim=dim,
        boundary_dim=16,
        grammar=grammar,
        seed=42,
    )

    rng = np.random.default_rng(999)
    # Création d'un bulk cohérent de 6 états sémantiques proches d'un thème commun
    base_theme = rng.normal(size=dim).astype(np.float32)
    base_theme /= np.linalg.norm(base_theme)

    bulk_states = []
    for _ in range(6):
        state = base_theme + 0.15 * rng.normal(size=dim).astype(np.float32)
        state /= np.linalg.norm(state)
        bulk_states.append(state)

    # 1. Encodage frontière
    z_holo = projector.project_bulk_to_boundary(bulk_states)
    assert z_holo.shape == (dim,)
    assert abs(np.linalg.norm(z_holo) - 1.0) < 1e-5

    # 2. Reconstitution prédictive
    steer_vec, fid = projector.reconstruct_from_boundary(z_holo)
    assert fid > 0.80, f"La fidélité holographique de reconstruction doit être >= 0.80, obtenu: {fid}"
    assert abs(np.linalg.norm(steer_vec) - 1.0) < 1e-5

    # 3. Mesure de fidélité globale bulk <-> boundary
    bulk_fid = projector.compute_holographic_fidelity(bulk_states, z_holo)
    assert bulk_fid > 0.60, f"La fidélité bulk/frontière doit être significative, obtenu: {bulk_fid}"


def test_04_inworld_teleological_convergence_and_singularity_dividend():
    """Test 4 : Harmonisation téléologique in-world et versement du Grand Dividende (+20.0 E)."""
    dim = 16
    cfg = LUInWorldConfig(
        latent_dim=dim,
        enable_autopoietic_singularity=True,
        teleological_attractor_force=0.30,
        singularity_dividend_bonus=20.0,
    )

    rng = np.random.default_rng(555)
    agents = [
        {"id": "ag_scout", "x": 4.0, "y": 4.0, "energy": 30.0, "lu_latent": rng.normal(size=dim).astype(np.float32)},
        {"id": "ag_crafter", "x": 8.0, "y": 8.0, "energy": 25.0, "lu_latent": rng.normal(size=dim).astype(np.float32)},
        {"id": "ag_hunter", "x": 12.0, "y": 12.0, "energy": 40.0, "lu_latent": rng.normal(size=dim).astype(np.float32)},
    ]
    for ag in agents:
        ag["lu_latent"] /= np.linalg.norm(ag["lu_latent"])

    world = MockWorld(agents=agents, items=[])
    adapter = LUInWorldAdapter(world=world, config=cfg)

    # Avant harmonisation
    for ag in agents:
        assert ag.get("singularity_attuned") is not True

    # Résonance téléologique
    success, bonus = adapter.resonate_teleological_convergence(agents)
    assert success is True
    assert bonus == 20.0

    # Vérification des effets sur les agents
    assert agents[0]["energy"] == 50.0  # 30 + 20
    assert agents[1]["energy"] == 45.0  # 25 + 20
    assert agents[2]["energy"] == 60.0  # 40 + 20

    for ag in agents:
        assert ag.get("singularity_attuned") is True
        assert ag.get("teleological_alignment_count") == 1
        # Alignement cosinus avec l'attracteur
        sim = float(np.dot(ag["lu_latent"], adapter.autopoietic_engine.phi_attractor))
        assert sim > 0.15, "Le latent doit avoir été infléchi vers l'attracteur téléologique"

    assert adapter.teleological_convergences_count == 1
    assert adapter.singularity_dividends_count == 3


def test_05_inworld_step17_full_cycle_and_lattice_audit():
    """Test 5 : Intégration complète de l'Étape 17 dans step() et auditabilité Lattice Memory."""
    dim = 16
    cfg = LUInWorldConfig(
        latent_dim=dim,
        enable_autopoietic_singularity=True,
        singularity_dividend_bonus=20.0,
    )

    rng = np.random.default_rng(888)
    agents = [
        {"id": "ag_0", "x": 2.0, "y": 2.0, "energy": 45.0, "lu_latent": rng.normal(size=dim).astype(np.float32)},
        {"id": "ag_1", "x": 9.0, "y": 9.0, "energy": 55.0, "lu_latent": rng.normal(size=dim).astype(np.float32)},
    ]
    for ag in agents:
        ag["lu_latent"] /= np.linalg.norm(ag["lu_latent"])

    world = MockWorld(agents=agents, items=[])
    adapter = LUInWorldAdapter(world=world, config=cfg)

    # Pont diplomatique Lattice
    bridge = FederalDiplomaticBridge(grammar=adapter.grammar)
    adapter.diplomatic_bridge = bridge

    # Exécution sur 15 pas
    for tick in range(1, 16):
        world.tick = tick
        world.ticks = tick
        metrics = adapter.step()

        if tick % 5 == 0:
            assert metrics["tick_autopoietic_steps"] == 1
            assert metrics["tick_teleological_convergences"] == 1
            assert metrics["tick_singularity_dividends"] == len(agents)
            assert metrics["bekenstein_entropy"] >= 0.0

    assert adapter.autopoietic_steps_count >= 3
    assert adapter.holographic_projections_count >= 3
    assert len(adapter.recent_autopoietic_snapshots) >= 3

    # Vérification des nœuds enregistrés dans le Lattice
    auto_nodes = [n for n in bridge.lattice_nodes.values() if isinstance(n, LUAutopoieticSingularity)]
    holo_nodes = [n for n in bridge.lattice_nodes.values() if isinstance(n, LUHolographicBoundary)]
    assert len(auto_nodes) >= 3, "Des nœuds LUAutopoieticSingularity doivent être tracés dans le Lattice"
    assert len(holo_nodes) >= 3, "Des nœuds LUHolographicBoundary doivent être tracés dans le Lattice"
