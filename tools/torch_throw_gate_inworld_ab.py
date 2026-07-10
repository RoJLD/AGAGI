"""B2 : câblage du throw-gate in-world (cran 2, biosphere). Banc A/B apparie ON vs SHUFFLE :
mesure binding_gap = P(throw | spear-en-inventaire) - P(throw | pas de spear) sur la VRAIE
presence, dans les deux bras. ON = tete entrainee sur la vraie recompense (kill-avec-outil) ;
SHUFFLE = recompense permutee (temoin d'artefact, joyau 169->171). Les spears sont SEMES
exogenement (decouplage du mur du craft EDR-125/127) : spawn + re-semis probabiliste quand
l'inventaire se vide -> melange dynamique spear/¬spear. Verdict via compute_ab_verdict.

Usage : python tools/torch_throw_gate_inworld_ab.py   (env: TTG_SEEDS, TTG_TICKS, TTG_WARMUP, TTG_AGENTS)
"""
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.worlds.world_1_stoneage import Biosphere3D, WorldConfig
from src.agents.mamba_agent import MambaAgent
from src.environments.stone_economy import has_spear
from tools.substrate_ab import compute_ab_verdict


def _seed_spears(world):
    """Sème un spear en tete d'inventaire de chaque agent (contexte present, throwable en premier)."""
    for a in world.agents:
        a["inventory"].insert(0, {"type": "Spear", "weight": 2.0})


def _reseed_spears(world, rng, respawn_p):
    """Re-sème un spear aux agents vivants qui n'en ont plus, avec proba respawn_p -> melange
    dynamique spear/¬spear a travers agents et temps (les deux contextes restent echantillonnes)."""
    for a in world.agents:
        if not has_spear(a["inventory"]) and rng.rand() < respawn_p:
            a["inventory"].insert(0, {"type": "Spear", "weight": 2.0})


def run_arm(shuffle=False, seed=0, ticks=400, warmup=200, n_agents=32, respawn_p=0.5):
    """Tourne un monde torch avec le throw-gate, sème/re-sème des spears, agrege le binding_gap
    sur la fenetre post-warmup (couples agent,tick sur la VRAIE presence-spear). CRN par seed.
    ON (shuffle=False) vs SHUFFLE (recompense permutee, contexte decorrele)."""
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except Exception:
        pass
    w = Biosphere3D(WorldConfig())
    for _ in range(n_agents):
        w.add_agent(MambaAgent(), energy=80.0)
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()               # repro : couper la memoire KuzuDB ambiante
    w.current_era = 1
    w.benchmark_mode = True                     # cohorte fixe -> dims homogenes (114b)
    w.use_torch_inworld = True
    w.torch_throw_gate = True
    w.torch_throw_shuffle = shuffle
    rng = np.random.RandomState(seed + 100)
    _seed_spears(w)
    spear_n = spear_thr = nospear_n = nospear_thr = 0
    for t in range(ticks):
        if not w.agents:
            break
        w.step()
        _reseed_spears(w, rng, respawn_p)
        if t >= warmup:
            for a in w.agents:
                ctx = a.get("_throw_ctx")
                if ctx is None:
                    continue
                did = 1 if a.get("_throw_did") else 0
                if ctx:
                    spear_n += 1
                    spear_thr += did
                else:
                    nospear_n += 1
                    nospear_thr += did
    p_spear = (spear_thr / spear_n) if spear_n else 0.0
    p_nospear = (nospear_thr / nospear_n) if nospear_n else 0.0
    tot_n = spear_n + nospear_n
    return {"shuffle": bool(shuffle), "seed": int(seed),
            "binding_gap_inworld": float(p_spear - p_nospear),
            "kills_with_tool": int(getattr(w, "_throw_kills_tool", 0)),
            "spear_n": int(spear_n), "nospear_n": int(nospear_n),
            "throw_rate": float((spear_thr + nospear_thr) / tot_n) if tot_n else 0.0}
