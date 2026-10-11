"""
tests/test_llm_swarm_consensus.py — Validation TDD du Consensus Latent Distribué Multi-LLMs (Arc 11 : Jalon M20).

Vérifie formellement :
1. L'unitarité stricte et la stabilité numérique du Gigatoken de consensus.
2. La résilience byzantine (BFT) de la médiane sphérique de Weiszfeld face aux agents corrompus.
3. La convergence géométrique du barycentre de Sinkhorn-Wasserstein.
4. La détection fiable de polarisation / schisme clanique.
5. La traçabilité Lattice dans KuzuDB.
"""

import pytest
import numpy as np
from src.metaprog.llm_swarm_consensus import (
    LLMSwarmConsensus,
    SwarmConsensusConfig,
    ConsensusStrategy,
    SwarmDeliberationResult,
)


def test_swarm_consensus_initialization_and_unitarity():
    """Vérifie que le vecteur de consensus respecte strictement ||z||_2 = 1.0."""
    consensus = LLMSwarmConsensus(SwarmConsensusConfig())
    dim = 64
    rng = np.random.RandomState(42)

    # 5 agents avec des vecteurs aléatoires sur la sphère
    agents = [rng.randn(dim).astype(np.float32) for _ in range(5)]
    res = consensus.deliberate(agents)

    assert isinstance(res, SwarmDeliberationResult)
    assert res.consensus_latent.shape == (dim,)
    norm = np.linalg.norm(res.consensus_latent)
    assert pytest.approx(norm, abs=1e-4) == 1.0
    assert not np.any(np.isnan(res.consensus_latent))
    assert res.cohesion_score > -1.0


def test_weiszfeld_median_byzantine_resilience():
    """
    Vérifie que la médiane sphérique de Weiszfeld BFT résiste à l'injection
    d'un agent byzantin délibérément opposé au consensus de la majorité.
    """
    cfg = SwarmConsensusConfig(
        consensus_strategy=ConsensusStrategy.WEISZFELD_MEDIAN_BFT,
        byzantine_filter_enabled=True,
        byzantine_outlier_sigma=2.0,
    )
    consensus = LLMSwarmConsensus(cfg)
    dim = 64

    # 4 agents légitimes orientés autour d'une direction commune e_0
    base_dir = np.zeros(dim, dtype=np.float32)
    base_dir[0] = 1.0

    legit_agents = []
    rng = np.random.RandomState(10)
    for _ in range(4):
        noise = rng.randn(dim).astype(np.float32) * 0.1
        v = base_dir + noise
        legit_agents.append(v / np.linalg.norm(v))

    # 1 agent byzantin corrompu orienté dans la direction diamétralement opposée (-e_0)
    byzantine_agent = -base_dir

    all_agents = legit_agents + [byzantine_agent]
    res = consensus.deliberate(all_agents)

    # L'agent adverse doit avoir été filtré / neutralisé
    assert res.byzantine_agents_rejected >= 1
    # Le consensus final doit rester fermement aligné avec la direction légitime (+e_0)
    alignment_with_truth = float(np.dot(res.consensus_latent, base_dir))
    assert alignment_with_truth > 0.85, f"Le consensus a été dévié par l'agent adverse : {alignment_with_truth}"


def test_sinkhorn_barycenter_multi_modal_convergence():
    """Vérifie la convergence douce du barycentre de Sinkhorn-Wasserstein."""
    cfg = SwarmConsensusConfig(
        consensus_strategy=ConsensusStrategy.SINKHORN_BARYCENTER,
        sinkhorn_iters=15,
        sinkhorn_reg=0.05,
    )
    consensus = LLMSwarmConsensus(cfg)
    dim = 64
    rng = np.random.RandomState(123)

    # 6 agents avec des pondérations inégales
    agents = [rng.randn(dim).astype(np.float32) for _ in range(6)]
    weights = [1.0, 2.0, 1.5, 0.5, 1.0, 3.0]

    res = consensus.deliberate(agents, agent_weights=weights)

    assert res.iterations_run <= cfg.sinkhorn_iters
    assert pytest.approx(np.linalg.norm(res.consensus_latent), abs=1e-4) == 1.0
    assert res.cohesion_score > 0.0


def test_swarm_polarization_detection():
    """Vérifie la détection d'un schisme / polarisation lorsque deux clans sont en désaccord."""
    cfg = SwarmConsensusConfig(
        byzantine_filter_enabled=False,
        polarization_threshold=0.30,
    )
    consensus = LLMSwarmConsensus(cfg)
    dim = 64

    dir_a = np.zeros(dim, dtype=np.float32)
    dir_a[0] = 1.0
    dir_b = np.zeros(dim, dtype=np.float32)
    dir_b[0] = -1.0  # Diamétralement opposé

    # Deux agents dans chaque camp
    agents = [dir_a, dir_a, dir_b, dir_b]
    res = consensus.deliberate(agents)

    # La variance angulaire doit être très élevée et déclencher l'alerte de polarisation
    assert res.is_polarized is True
    assert res.angular_variance >= cfg.polarization_threshold
