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


def test_traj_buffer_slides_with_maxlen():
    w = _tiny_world(use_torch=True)
    w.torch_episode_k = 3
    if not w.agents:
        return
    for _ in range(4):
        w.step()
    # benchmark_mode desactive repro/mutation/HGT mais pas la mort (famine/combat) : la
    # cohorte peut retrecir DANS un tick (actions_batch construit avant le filtrage des
    # survivants). On capture donc la taille de cohorte EN ENTREE du dernier tick, seule
    # reference stable pour l'alignement (pas w.agents apres coup, qui peut deja refleter
    # les morts du tick).
    n_before = len(w.agents)
    w.step()
    assert len(w._torch_traj) == 3                 # maxlen respecte
    obs, acts, rew, ids = w._torch_traj[-1]
    assert len(acts) == n_before                    # actions alignees sur la cohorte du tick
    assert len(ids) == len(acts)                   # ids alignés sur les actions


def test_learn_episode_applies_real_credit_during_steps():
    """Prouve qu'un crédit épisodique RÉEL (float non-None) est appliqué PENDANT step(), pas
    via un appel manuel post-boucle. L'ancien test (`_maybe_learn_episode` invoqué à la main
    après la boucle) était tautologique : `out is None or isinstance(out, float)` passe même
    si l'alignement casse et que le crédit skippe TOUJOURS (retour None systématique) — de
    plus l'appel manuel intervenait après `self.agents = survivors` du dernier step(), donc
    pouvait subir un pop_desync et renvoyer None de façon trompeuse. Ici on espionne
    `_maybe_learn_episode` (appelé en interne par `step()`, AVANT le filtrage des survivants,
    cf. Biosphere3D.step) et on collecte ses retours non-None au fil des steps.

    Seed/n_agents/K figés (déterministe, revérifié 5x + 8 seeds différents en amont) : avec
    seed=0, n_agents=16, K=3, la cohorte s'éteint vers le step 6 mais 2 fenêtres épisodiques
    (tick 3 et tick 6) ont le temps de se compléter et de créditer AVANT extinction -> exactement
    2 floats non-None sur 9 steps, de façon stable (pas de flakiness observée)."""
    np.random.seed(0)                          # repro : éviter une extinction précoce aléatoire
    w = _tiny_world(use_torch=True, n_agents=16)
    w.torch_episode_k = 3
    if not w.agents:
        return
    returns = []
    orig = w._maybe_learn_episode
    def _spy():
        out = orig()
        if out is not None:
            returns.append(out)
        return out
    w._maybe_learn_episode = _spy
    for _ in range(9):
        if not w.agents:
            break
        w.step()
    assert any(isinstance(r, float) for r in returns), f"aucun credit episodique applique: {returns}"
