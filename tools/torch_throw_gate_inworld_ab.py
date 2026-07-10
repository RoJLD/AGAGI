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


def run_arm(shuffle=False, seed=0, ticks=400, warmup=200, n_agents=32, respawn_p=0.5,
            base_metabolism=1.0, forage_payoff=1.0):
    """Tourne un monde torch avec le throw-gate, sème/re-sème des spears, agrege le binding_gap
    sur la fenetre post-warmup (couples agent,tick sur la VRAIE presence-spear). CRN par seed.
    ON (shuffle=False) vs SHUFFLE (recompense permutee, contexte decorrele)."""
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except Exception:
        pass
    w = Biosphere3D(WorldConfig(base_metabolism=base_metabolism, forage_payoff=forage_payoff))
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
            "n_alive_end": int(len(w.agents)),
            "throw_rate": float((spear_thr + nospear_thr) / tot_n) if tot_n else 0.0}


def compare(seeds=(0, 1, 2, 3), ticks=400, warmup=200, n_agents=32,
            base_metabolism=1.0, forage_payoff=1.0):
    """A/B apparie ON vs SHUFFLE par seed -> verdict. diff = gap_ON - gap_SHUFFLE. diff>0 = le
    throw-gate route sur la VRAIE presence-spear et generalise (pas artefact : le shuffle est plat).
    base_metabolism/forage_payoff : regime energetique (defaut 1.0/1.0 = letal ; sweet EDR-085 =
    0.25/3.0 = survivable, laisse le temps au gate d'apprendre)."""
    rows = []
    for s in seeds:
        on = run_arm(shuffle=False, seed=s, ticks=ticks, warmup=warmup, n_agents=n_agents,
                     base_metabolism=base_metabolism, forage_payoff=forage_payoff)
        sh = run_arm(shuffle=True, seed=s, ticks=ticks, warmup=warmup, n_agents=n_agents,
                     base_metabolism=base_metabolism, forage_payoff=forage_payoff)
        rows.append({"seed": s, "on": on["binding_gap_inworld"], "shuffle": sh["binding_gap_inworld"],
                     "kills_on": on["kills_with_tool"],
                     "on_throw": on["throw_rate"], "on_sn": on["spear_n"], "on_nn": on["nospear_n"],
                     "sh_throw": sh["throw_rate"], "alive": on["n_alive_end"],
                     "diff": on["binding_gap_inworld"] - sh["binding_gap_inworld"]})
    return {"rows": rows, "verdict": compute_ab_verdict(rows, band=0.02)}


if __name__ == "__main__":
    seeds = tuple(int(x) for x in os.environ.get("TTG_SEEDS", "0,1,2,3").split(","))
    ticks = int(os.environ.get("TTG_TICKS", "400"))
    warmup = int(os.environ.get("TTG_WARMUP", "200"))
    agents = int(os.environ.get("TTG_AGENTS", "32"))
    bm = float(os.environ.get("TTG_BM", "1.0"))          # base_metabolism (sweet EDR-085 = 0.25)
    fp = float(os.environ.get("TTG_FP", "1.0"))          # forage_payoff  (sweet EDR-085 = 3.0)
    out = compare(seeds=seeds, ticks=ticks, warmup=warmup, n_agents=agents,
                  base_metabolism=bm, forage_payoff=fp)
    for r in out["rows"]:
        print(f"seed={r['seed']} gap_ON={r['on']:+.3f} gap_SHUF={r['shuffle']:+.3f} "
              f"diff={r['diff']:+.3f} | throw_ON={r['on_throw']:.3f} throw_SH={r['sh_throw']:.3f} "
              f"spear_n={r['on_sn']} nospear_n={r['on_nn']} alive={r['alive']} kills_ON={r['kills_on']}")
    print("VERDICT:", out["verdict"])
    _label = {"GRADIENT_GAGNE": "BINDING_INWORLD_REEL", "HEBBIEN_GAGNE": "SHUFFLE_BINDE_PLUS",
              "NEUTRE": "PAS_DE_BINDING_INWORLD"}
    print("INTERPRETATION:", _label.get(out["verdict"]["verdict"], out["verdict"]["verdict"]))
