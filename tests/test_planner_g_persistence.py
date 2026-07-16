"""Régression : l'organe planner g doit PERSISTER son apprentissage in-world.

Bug (issue #123, EDR-135) : `planner_G` était extrait de `G_batch` dans le forward AVANT que
`compute_policy_gradient` ne mette à jour `G_batch` -> l'update était perdu au reset du forward
suivant, `g` restait ≡0 en monde réel (mean|G|=0), alors qu'il apprenait dans le banc-grille.
Ce test fait tourner une cohorte in-world avec le planner actif et vérifie que `g` accumule."""
import numpy as np
import pytest

from src.agents.mamba_agent import MambaAgent, MambaBatchModel
from src.worlds.world_1_stoneage import Biosphere3D
from src.environments.config import WorldConfig
from src.seed_ai.harness import SeedManager


@pytest.mark.slow
def test_planner_g_accumulates_in_world():
    """Avec le planner actif (PLAN_BIAS>0), `g` doit s'apprendre in-world : après quelques ticks,
    au moins un agent a un `planner_G` non nul. RED avant le fix de persistance (g≡0), GREEN après."""
    prev_bias, prev_lr = MambaBatchModel.PLAN_BIAS, MambaBatchModel.PLAN_LR
    MambaBatchModel.PLAN_BIAS, MambaBatchModel.PLAN_LR = 0.5, 0.1
    try:
        cfg = WorldConfig()
        cfg.base_metabolism = 0.25          # sweet-spot (EDR-085) : agents survivent assez pour apprendre
        cfg.forage_payoff = 3.0
        SeedManager(0).seed_boundary(0)
        env = Biosphere3D(cfg)
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
            env.memory_retriever.clear()
        env.benchmark_mode = True
        env.night_enabled = False
        env.current_era = 10_000
        for _ in range(12):
            a = MambaAgent()
            a.genome.organ_genes = np.array([True, False])   # planner ON
            env.add_agent(a, energy=80.0)
        max_g = 0.0
        for _ in range(20):
            env.step()
            if not env.agents:
                break
            max_g = max(max_g, max(float(np.mean(np.abs(getattr(ag["model"], "planner_G", np.zeros(1)))))
                                   for ag in env.agents))
        assert max_g > 0.0, f"planner_G reste nul in-world (g non persisté) : max|G|={max_g}"
    finally:
        MambaBatchModel.PLAN_BIAS, MambaBatchModel.PLAN_LR = prev_bias, prev_lr
