import numpy as np
import pytest
from src.seed_ai.harness import seed_at
from src.agents.mamba_agent import MambaAgent
from tools.lewis_survival_sweep import _fresh_genome
from src.seed_ai.mutation import apply_mutations
from tools.lewis_survival_sweep import _capacity_mc, _capacity_arm, _cfg


def test_fresh_genome_dims():
    seed_at(110, 0)
    g80 = _fresh_genome(80)
    assert g80.num_nodes == 247
    assert g80.num_inputs == 59
    assert g80.num_outputs == 108
    g5 = _fresh_genome(5)
    assert g5.num_nodes == 172


def test_capacity_mc_freezes_capacity():
    mc = _capacity_mc()
    assert mc.add_node_rate == 0.0
    assert mc.prune_rate == 0.0


def test_apply_mutations_preserves_num_nodes_under_frozen_mc():
    seed_at(110, 0)
    g = _fresh_genome(40)  # 207 noeuds
    mc = _capacity_mc()
    for _ in range(10):
        g = apply_mutations(g, mc)
    assert g.num_nodes == 207


def test_capacity_arm_smoke_returns_expected_keys():
    cfg = _cfg(3, base_metabolism=0.0, trace_forage=True)
    mc = _capacity_mc()
    arm = _capacity_arm(cfg, mc, n_hidden=5, generations=2, num_agents=6,
                        max_ticks=40, base_seed=12345)
    assert arm["n_hidden"] == 5
    assert arm["num_nodes"] == 172
    assert len(arm["traj"]) == 2
    assert 0.0 <= arm["plateau"] <= 1.0
    assert 0.0 <= arm["gen0"] <= 1.0
    assert len(arm["stats"]) == 2


def test_capacity_materializes_in_phenotype():
    # De-risk go/no-go : un genome seme a N=80 materialise 247 noeuds, caches non-inertes,
    # forward sans exception. Si ce test echoue -> STOP (substrat ne supporte pas la capacite).
    seed_at(110, 0)
    g = _fresh_genome(80)
    a = MambaAgent()
    a.from_genome(g)
    assert a.genome.num_nodes == 247
    # bande cachee [59, 139) non tout-zero (caches reellement cables dans W)
    assert np.any(a.genome.W[59:139, :] != 0.0)
    # forward tourne et renvoie 108 logits finis
    obs = np.zeros(59, dtype=np.float32)
    logits = a.forward(obs)
    assert logits.shape[-1] == 108
    assert np.all(np.isfinite(logits))
