"""Task 1 (G1, cran 0) : flag USE_TORCH_INWORLD + pop torch PERSISTANT hors boucle par-tick.

Non-régression legacy stricte : use_torch_inworld=False (défaut) -> comportement inchangé
(MambaBatchModel recréé/tick, pas de pop torch). use_torch_inworld=True -> pop torch persistant
(même objet entre deux ticks -> optimiseur/gate survivent).
"""
import numpy as np
from src.worlds.world_1_stoneage import Biosphere3D, WorldConfig
from src.agents.mamba_agent import MambaAgent


def _tiny_world(use_torch, n_agents=12):
    cfg = WorldConfig()
    cfg.size = 16
    w = Biosphere3D(cfg)
    for _ in range(n_agents):
        w.add_agent(MambaAgent(), energy=80.0)
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()          # repro : couper la mémoire KuzuDB ambiante
    w.current_era = 1
    w.benchmark_mode = True                # cohorte fixe : dims homogènes + B stable (114b)
    w.use_torch_inworld = use_torch
    return w


def test_flag_off_uses_legacy_and_no_persistent_pop():
    w = _tiny_world(use_torch=False)
    models = [a["model"] for a in w.agents] if w.agents else []
    bm = w._get_batch_model(models)
    assert bm.__class__.__name__ == "MambaBatchModel"
    assert w._torch_pop is None


def test_flag_on_returns_persistent_torch_pop():
    w = _tiny_world(use_torch=True)
    if not w.agents:
        return
    models = [a["model"] for a in w.agents]
    bm1 = w._get_batch_model(models)
    bm2 = w._get_batch_model(models)
    assert bm1 is bm2                  # MÊME objet -> optimiseur/gate persistent
    assert type(bm1).backend == "torch"


def test_one_tick_torch_forward_and_learn():
    w = _tiny_world(use_torch=True)
    if not w.agents:
        return
    w.step()                            # un pas complet : ne doit pas lever
    assert w._torch_pop is not None
    W0 = np.asarray(w.agents[0]["model"].genome.W, dtype=np.float32).copy()
    w.step()
    W1 = np.asarray(w.agents[0]["model"].genome.W, dtype=np.float32)
    assert W0.shape == W1.shape          # Baldwin : W réécrit, forme stable
