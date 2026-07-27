"""A/B survie in-world : USE_TORCH_INWORLD off vs on, apparie par seed, cohorte fixe (114b).
Verdict via compute_ab_verdict (substrate_ab). C'est l'instrument des crans 0-1 (le livrable EDR).

Usage : python tools/torch_inworld_ab.py   (env: TIA_SEEDS, TIA_TICKS, TIA_AGENTS)
"""
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.worlds.world_1_stoneage import Biosphere3D, WorldConfig
from src.agents.mamba_agent import MambaAgent
from tools.substrate_ab import compute_ab_verdict


def run_arm(use_torch: bool, seed: int = 0, ticks: int = 200, n_agents: int = 16) -> dict:
    """Tourne un monde en cohorte fixe et renvoie la survie mediane (fraction d'agents vivants en fin
    de run). Apparie : meme seed, memes dims, seul le backend change. La memoire KuzuDB ambiante est
    coupee (repro : sinon l'appariement par seed est fausse)."""
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except Exception:
        pass
    cfg = WorldConfig()
    w = Biosphere3D(cfg)
    for _ in range(n_agents):
        w.add_agent(MambaAgent(), energy=80.0)
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()           # repro : couper la memoire KuzuDB ambiante
    w.current_era = 1
    w.benchmark_mode = True                 # cohorte fixe -> dims homogenes, B stable (114b)
    w.use_torch_inworld = use_torch
    n0 = len(w.agents)
    for _ in range(ticks):
        if not w.agents:
            break
        w.step()
    survival = (len(w.agents) / n0) if n0 else 0.0
    return {"use_torch": use_torch, "seed": int(seed), "ticks": ticks,
            "n_agents": n0, "survival": float(survival)}


def compare(seeds=(0, 1, 2, 3), ticks: int = 200, n_agents: int = 16) -> dict:
    """A/B apparie legacy vs torch in-world par seed -> verdict de survie."""
    rows = []
    for s in seeds:
        leg = run_arm(False, seed=s, ticks=ticks, n_agents=n_agents)
        tor = run_arm(True, seed=s, ticks=ticks, n_agents=n_agents)
        rows.append({"seed": s, "legacy": leg["survival"], "torch": tor["survival"],
                     "diff": tor["survival"] - leg["survival"]})
    verdict = compute_ab_verdict(rows, band=0.02)
    return {"rows": rows, "verdict": verdict}


if __name__ == "__main__":
    seeds = tuple(int(x) for x in os.environ.get("TIA_SEEDS", "0,1,2,3").split(","))
    ticks = int(os.environ.get("TIA_TICKS", "200"))
    agents = int(os.environ.get("TIA_AGENTS", "16"))
    out = compare(seeds=seeds, ticks=ticks, n_agents=agents)
    for r in out["rows"]:
        print(f"seed={r['seed']} legacy={r['legacy']:.3f} torch={r['torch']:.3f} diff={r['diff']:+.3f}")
    print("VERDICT:", out["verdict"])
