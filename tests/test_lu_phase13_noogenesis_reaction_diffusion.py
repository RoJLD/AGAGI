"""
tests/test_lu_phase13_noogenesis_reaction_diffusion.py — Validation de la Phase 13 du Langage Ultime.

Arc 7 : L'Hyper-Conscience / Morphogenèse Noogénétique, Équations de Réaction-Diffusion Latente
et Hyper-Connectome Fédéral Distribué (G13).

Vérifie :
1. Conservation de la compacité spectrale et de la stabilité sous intégration PDE de Turing (||Phi|| <= 1.0).
2. Émergence de motifs stationnaires (focal points), calcul de l'énergie PDE et gradients d'orientation.
3. Synthèse lipschitzienne de l'Hyper-Connectome et vérification de non-explosion spectrale (rho < 0.95).
4. Distillation épigénétique dans un agent et confirmation d'alignement fonctionnel (gain de renaissance +12.0 E).
5. Intégration In-World complète (Étape 16) et traçabilité Lattice Memory.
"""

import pytest
import numpy as np
from typing import Dict, Any, List

from src.metaprog.lu_algebra import (
    LUCompositionalGrammar,
    LUAlgebraConfig,
    LatentReactionDiffusionPDE,
    HyperConnectomeSynthesizer,
    ConnectomeCompiler,
)
from src.metaprog.lu_symbolic_bridge import (
    FederalDiplomaticBridge,
    LUNoogeneticField,
    LUHyperConnectome,
)
from src.environments.lu_inworld_adapter import (
    LUInWorldAdapter,
    LUInWorldConfig,
    InscriptionStone,
)


class MockWorld:
    """Environnement simulé minimal pour tester les interactions in-world."""
    def __init__(self, agents: List[Dict[str, Any]], items: List[Dict[str, Any]]):
        self.agents = agents
        self.items = items
        self.tick = 30
        self.ticks = 30
        self.size = 16


class DummyNeuralModel:
    """Modèle neuronal minimal simulant un connectome d'agent pour la distillation."""
    def __init__(self, size: int = 16):
        self.size = size
        self.W = np.eye(size, dtype=np.float32) * 0.5

    def get_weights(self) -> np.ndarray:
        return self.W.copy()

    def set_weights(self, new_W: np.ndarray) -> None:
        self.W = new_W.copy().astype(np.float32)


def test_01_turing_reaction_diffusion_spectral_stability():
    """Test 1 : Conservation de la compacité spectrale et de la stabilité sous intégration PDE de Turing."""
    dim = 16
    grid_size = 16
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=dim, seed=42))

    pde = LatentReactionDiffusionPDE(
        grid_size=grid_size,
        dim=dim,
        diffusion_coef=0.15,
        reaction_rate=0.25,
        grammar=grammar,
        seed=42,
    )

    # Vérification initiale
    assert pde.phi.shape == (grid_size, grid_size, dim)
    init_norms = np.linalg.norm(pde.phi, axis=-1)
    assert np.all(init_norms <= 1.0 + 1e-5), "Les vecteurs initiaux doivent être dans la boule unitaire"

    # Intégration sur 25 pas avec sources externes aléatoires
    rng = np.random.default_rng(101)
    source_vec = rng.normal(size=dim).astype(np.float32)
    source_vec /= np.linalg.norm(source_vec)
    sources = [(4, 4, source_vec, 0.8), (12, 12, -source_vec, 0.5)]

    for _ in range(25):
        field = pde.step(dt=0.15, external_sources=sources)
        assert not np.isnan(field).any(), "Aucun NaN toléré sous intégration PDE"
        assert not np.isinf(field).any(), "Aucun Inf toléré sous intégration PDE"
        norms = np.linalg.norm(field, axis=-1)
        assert np.all(norms <= 1.0 + 1e-5), f"Stabilité spectrale violée: max norm={np.max(norms)}"

    assert pde.step_count == 25


def test_02_pde_focal_points_and_energy_entropy():
    """Test 2 : Émergence de motifs stationnaires (focal points), calcul de l'énergie et entropie."""
    dim = 16
    grid_size = 16
    pde = LatentReactionDiffusionPDE(
        grid_size=grid_size,
        dim=dim,
        diffusion_coef=0.10,
        reaction_rate=0.30,
        seed=7,
    )

    # Injection d'un foyer puissant au centre (8, 8)
    rng = np.random.default_rng(999)
    center_vec = rng.normal(size=dim).astype(np.float32)
    center_vec /= np.linalg.norm(center_vec)

    for _ in range(10):
        pde.step(dt=0.2, external_sources=[(8, 8, center_vec, 1.5)])

    # Détection des points focaux
    focal_points = pde.get_focal_points(threshold=0.50)
    assert len(focal_points) > 0, "Un foyer d'innovation doit émerger autour de la source d'injection"

    # Énergie L2 et Entropie de Shannon
    energy = pde.compute_pde_energy()
    entropy = pde.compute_morphogen_entropy()
    assert energy > 0.0, "L'énergie PDE doit être strictement positive"
    assert entropy > 0.0, "L'entropie morphogénétique doit être positive"

    # Gradient spatial d'orientation
    gx, gy = pde.get_gradient_at(7.0, 8.0)
    assert isinstance(gx, float) and isinstance(gy, float)
    assert not np.isnan(gx) and not np.isnan(gy)


def test_03_hyperconnectome_lipschitzian_synthesis():
    """Test 3 : Synthèse lipschitzienne de l'Hyper-Connectome et vérification de non-explosion spectrale (rho < 0.95)."""
    dim = 16
    connectome_size = 16
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=dim, seed=42))

    synthesizer = HyperConnectomeSynthesizer(
        dim=dim,
        connectome_size=connectome_size,
        grammar=grammar,
        seed=42,
    )

    spec_init = synthesizer.get_hyperconnectome_spec()
    assert spec_init["spectral_radius"] < 0.95, f"Rayon spectral initial non contractant: {spec_init['spectral_radius']}"

    # Condensation d'une série de 5 barycentres synarchiques
    rng = np.random.default_rng(123)
    barycenters = []
    for _ in range(5):
        b = rng.normal(size=dim).astype(np.float32)
        b /= np.linalg.norm(b)
        barycenters.append(b)

    spec_updated = synthesizer.condense_synarchic_history_to_hyperconnectome(
        barycenters=barycenters,
        learning_rate=0.20,
    )

    assert spec_updated["version"] > spec_init["version"]
    assert spec_updated["spectral_radius"] < 0.95, f"Le rayon spectral doit rester strictement < 0.95, obtenu: {spec_updated['spectral_radius']}"
    assert spec_updated["latent_norm"] > 0.99, "Le Gigatoken z_hyper doit être de norme unitaire"


def test_04_noogenetic_distillation_and_rebirth_prior():
    """Test 4 : Distillation épigénétique dans un agent et confirmation d'alignement fonctionnel (+12.0 E)."""
    dim = 16
    synthesizer = HyperConnectomeSynthesizer(dim=dim, connectome_size=16, seed=42)

    # 1. Agent avec modèle neuronal dummy
    model = DummyNeuralModel(size=16)
    w_before = model.get_weights()

    rng = np.random.default_rng(55)
    z_ag = rng.normal(size=dim).astype(np.float32)
    z_ag /= np.linalg.norm(z_ag)

    agent_neural = {
        "id": "agent_neural_01",
        "model": model,
        "lu_latent": z_ag.copy(),
        "energy": 20.0,
        "age": 2,
    }

    success, fid, details = synthesizer.project_hyperconnectome_prior(agent_neural, alpha=0.30)
    assert success is True, "La distillation vers un modèle neuronal valide doit réussir"
    assert fid > 0.50, f"La fidélité d'infusion doit être significative: {fid}"
    assert agent_neural.get("hyperconnectome_distilled") is True

    w_after = model.get_weights()
    diff_norm = float(np.linalg.norm(w_after - w_before))
    assert diff_norm > 0.0, "Les poids du modèle doivent avoir été modulés par le prior"

    # 2. Agent synthétique (sans modèle physique) via l'adaptateur in-world
    adapter = LUInWorldAdapter(world=None, config=LUInWorldConfig(latent_dim=dim, noogenetic_rebirth_bonus=12.0))
    agent_synth = {
        "id": "agent_newborn_02",
        "lu_latent": z_ag.copy(),
        "energy": 10.0,
        "age": 1,
    }

    succ, bonus = adapter.distill_noogenetic_prior_to_agent(agent_synth, alpha=0.35)
    assert succ is True
    assert bonus == 12.0
    assert agent_synth["energy"] == 22.0, f"L'énergie doit recevoir le bonus de 12.0, obtenu: {agent_synth['energy']}"
    assert agent_synth.get("noogenetic_rebirth_count") == 1


def test_05_inworld_step16_full_cycle_and_lattice_trace():
    """Test 5 : Intégration In-World complète (Étape 16) et traçabilité Lattice Memory."""
    dim = 16
    cfg = LUInWorldConfig(
        latent_dim=dim,
        enable_reaction_diffusion_pde=True,
        enable_hyperconnectome_distillation=True,
        noogenetic_rebirth_bonus=12.0,
    )

    rng = np.random.default_rng(777)
    agents = [
        {"id": "ag_0", "x": 3.0, "y": 3.0, "energy": 50.0, "age": 2, "lu_latent": rng.normal(size=dim).astype(np.float32)},
        {"id": "ag_1", "x": 10.0, "y": 10.0, "energy": 15.0, "age": 40, "lu_latent": rng.normal(size=dim).astype(np.float32)},
        {"id": "ag_2", "x": 8.0, "y": 8.0, "energy": 80.0, "age": 100, "lu_latent": rng.normal(size=dim).astype(np.float32)},
    ]
    for ag in agents:
        ag["lu_latent"] /= np.linalg.norm(ag["lu_latent"])

    world = MockWorld(agents=agents, items=[])
    adapter = LUInWorldAdapter(world=world, config=cfg)

    # Pont symbolique avec auditabilité Lattice
    bridge = FederalDiplomaticBridge(grammar=adapter.grammar)
    adapter.diplomatic_bridge = bridge

    # Exécution de plusieurs pas temporels
    for tick in range(1, 10):
        world.tick = tick
        world.ticks = tick
        step_metrics = adapter.step()

        if tick % 3 == 0:
            assert step_metrics["tick_pde_steps"] == 1
            assert step_metrics["pde_steps"] > 0
            assert step_metrics["pde_energy"] > 0.0

    # Vérification des métriques accumulées
    assert adapter.pde_steps_count >= 3
    assert len(adapter.recent_pde_snapshots) >= 3
    assert adapter.noogenetic_distillations_count >= 1

    # Vérification des traçabilités Lattice enregistrées dans le pont
    pde_nodes = [n for n in bridge.lattice_nodes.values() if isinstance(n, LUNoogeneticField)]
    hc_nodes = [n for n in bridge.lattice_nodes.values() if isinstance(n, LUHyperConnectome)]
    assert len(pde_nodes) >= 3, "Des nœuds LUNoogeneticField doivent avoir été enregistrés dans le Lattice"
    assert len(hc_nodes) >= 3, "Des nœuds LUHyperConnectome doivent avoir été enregistrés dans le Lattice"
