import numpy as np
import pytest
from src.seed_ai.harness import seed_at
from src.agents.mamba_agent import MambaAgent
from tools.lewis_survival_sweep import _fresh_genome


def test_fresh_genome_dims():
    seed_at(110, 0)
    g80 = _fresh_genome(80)
    assert g80.num_nodes == 247
    assert g80.num_inputs == 59
    assert g80.num_outputs == 108
    g5 = _fresh_genome(5)
    assert g5.num_nodes == 172


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
