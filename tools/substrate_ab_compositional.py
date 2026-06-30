"""A/B de learnabilité COMPOSITIONNELLE du substrat (means→ends) — porte de décision torch-prod.

Question : un substrat `torch` (autograd) apprend-il une contingence 2-étapes — faire X en S1
(récompense IMMÉDIATE nulle) puis Y en S2 récompensé SEULEMENT si X a été fait — que le substrat
`legacy` (hebbien/Actor-Critic TD numpy, ~5 cachés) NE peut pas ? C'est l'apex craft→chasse en
miniature. `obs_B` n'encode PAS `did_X` -> l'agent doit le MÉMORISER (récurrence) = vraie composition.

Réutilise le backend abstrait (`make_population`, ADR-003) + `compute_ab_verdict` de `substrate_ab`
SANS les modifier. PORTÉE : micro-tâche, PAS une preuve de transfert apex en prod.

Usage : python tools/substrate_ab_compositional.py   (env: SABC_SEEDS, SABC_TRIALS, SABC_AGENTS)
"""
import os
import sys

import numpy as np
import statistics

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.agents.mamba_agent import MambaAgent
from src.agents.backend import make_population
from tools.substrate_ab import compute_ab_verdict, _MOVE


def compositional_reward(move2: int, target_y: int, did_x: bool) -> float:
    """Récompense d'étape 2 : +1 SSI l'action Y est correcte ET X a été fait en S1, sinon −1.
    PURE et testable. C'est ce qui rend la tâche COMPOSITIONNELLE (Y ne paie que via X)."""
    return 1.0 if (move2 == target_y and did_x) else -1.0


def _init_factor(num_nodes: int, init_scale: str) -> float:
    """Facteur d'échelle d'init des poids. `normalized` = sqrt(171/(N-1)) → maintient la variance
    d'excitation (Σ_{k≠j} H_k W_kj ∝ (N-1)·Var(W)) ≈ invariante à N, calibrée sur N_ref=172.
    À N=172 → 1.0 (anchor identique à prod). `prod` → 1.0 (init MambaAgent intact). PUR."""
    if init_scale == "normalized":
        return float(np.sqrt(171.0 / (num_nodes - 1)))
    return 1.0


def _build_agents(n_agents: int, num_nodes: int, init_scale: str) -> list:
    """Construit n_agents MambaAgent à `num_nodes` (hidden = num_nodes-167, I/O fixes 59/108),
    puis applique l'échelle d'init au niveau GÉNOME (backend-agnostique : legacy et torch lisent
    le même W). Le caller seed np.random avant d'appeler (déterminisme)."""
    agents = [MambaAgent(num_nodes=num_nodes) for _ in range(n_agents)]
    factor = _init_factor(num_nodes, init_scale)
    if factor != 1.0:
        for a in agents:
            a.genome.W = (a.genome.W * factor).astype(np.float32)
    return agents


def run_compositional(backend: str, seed: int = 0, trials: int = 100, n_agents: int = 8,
                      target_x: int = 0, target_y: int = 4,
                      num_nodes: int = 172, init_scale: str = "prod") -> dict:
    """Entraîne une pop sur la tâche 2-étapes. Renvoie le taux d'essais PLEINEMENT corrects
    (X-puis-Y) début vs fin (delta = apprentissage compositionnel)."""
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except Exception:
        pass
    agents = _build_agents(n_agents, num_nodes, init_scale)
    pop = make_population(agents, backend=backend)
    rng = np.random.RandomState(seed + 1)
    n_in = agents[0].genome.num_inputs
    obs_a = (rng.randn(n_agents, n_in) * 0.5).astype(np.float32)   # état S1 (motif fixe)
    obs_b = (rng.randn(n_agents, n_in) * 0.5).astype(np.float32)   # état S2 (motif distinct)
    zeros = np.zeros(n_agents, dtype=np.float32)

    full = []
    for _ in range(trials):
        # Étape 1 (S1) : émettre X, récompense différée (0). La récurrence retient l'état.
        preds1, _ = pop.forward(obs_a)
        move1 = np.asarray(preds1)[:, :_MOVE].argmax(axis=1)
        did_x = (move1 == target_x)
        pop.learn(zeros, [{"move": int(m), "grab": 0, "rub": 0} for m in move1])
        # Étape 2 (S2) : émettre Y, récompensé SSI X fait en S1 (obs_b n'encode pas did_x).
        preds2, _ = pop.forward(obs_b)
        move2 = np.asarray(preds2)[:, :_MOVE].argmax(axis=1)
        reward2 = np.array([compositional_reward(int(move2[i]), target_y, bool(did_x[i]))
                            for i in range(n_agents)], dtype=np.float32)
        pop.learn(reward2, [{"move": int(m), "grab": 0, "rub": 0} for m in move2])
        full.append(float(np.mean((move2 == target_y) & did_x)))   # essai pleinement correct

    q = max(1, trials // 4)
    hit_start, hit_end = float(np.mean(full[:q])), float(np.mean(full[-q:]))
    return {"backend": backend, "seed": int(seed), "trials": trials, "n_agents": n_agents,
            "hit_start": hit_start, "hit_end": hit_end, "delta": hit_end - hit_start}


def sweep(hiddens=(5, 20, 50, 100), inits=("prod", "normalized"),
          seeds=(0, 1, 2, 3, 4), trials: int = 250, n_agents: int = 8) -> dict:
    """Grille A/B legacy↔torch par cellule (hidden, init). Déduplique normalized@5 == prod@5
    (même facteur 1.0). Renvoie {cells, curve} ; curve = hit_end médian par taille et backend
    (lecture décisive A/B/C). Jamais de scalaire nu : per_seed conservé par cellule."""
    cells = []
    curve = {"legacy": [], "torch": []}
    seen = set()
    for hidden in hiddens:
        num_nodes = 167 + hidden
        for init in inits:
            factor = round(_init_factor(num_nodes, init), 6)
            key = (hidden, factor)            # dédup : normalized@anchor (factor 1.0) == prod
            if key in seen:
                continue
            seen.add(key)
            rows = []
            for s in seeds:
                leg = run_compositional("legacy", seed=s, trials=trials, n_agents=n_agents,
                                        num_nodes=num_nodes, init_scale=init)
                tor = run_compositional("torch", seed=s, trials=trials, n_agents=n_agents,
                                        num_nodes=num_nodes, init_scale=init)
                rows.append({"seed": int(s), "legacy_delta": leg["delta"], "torch_delta": tor["delta"],
                             "diff": tor["delta"] - leg["delta"], "legacy": leg, "torch": tor})
            verdict = compute_ab_verdict(rows)
            cells.append({"hidden": hidden, "init": init, **verdict, "per_seed": rows})
            curve["legacy"].append({"hidden": hidden, "init": init,
                                    "median_hit_end": statistics.median([r["legacy"]["hit_end"] for r in rows]),
                                    "median_delta": statistics.median([r["legacy_delta"] for r in rows])})
            curve["torch"].append({"hidden": hidden, "init": init,
                                   "median_hit_end": statistics.median([r["torch"]["hit_end"] for r in rows]),
                                   "median_delta": statistics.median([r["torch_delta"] for r in rows])})
    return {"cells": cells, "curve": curve}


def compare(seeds=(0, 1, 2, 3, 4), trials: int = 100, n_agents: int = 8) -> dict:
    """A/B apparié legacy vs torch par seed -> verdict de learnabilité compositionnelle."""
    rows = []
    for s in seeds:
        leg = run_compositional("legacy", seed=s, trials=trials, n_agents=n_agents)
        tor = run_compositional("torch", seed=s, trials=trials, n_agents=n_agents)
        rows.append({"seed": int(s), "legacy_delta": leg["delta"], "torch_delta": tor["delta"],
                     "diff": tor["delta"] - leg["delta"], "legacy": leg, "torch": tor})
    return {**compute_ab_verdict(rows), "per_seed": rows}


def main():
    hiddens = [int(h) for h in os.environ.get("SABC_HIDDENS", "5,20,50,100").split(",") if h.strip()]
    inits = [x.strip() for x in os.environ.get("SABC_INITS", "prod,normalized").split(",") if x.strip()]
    seeds = [int(s) for s in os.environ.get("SABC_SEEDS", "0,1,2,3,4").split(",") if s.strip()]
    trials = int(os.environ.get("SABC_TRIALS", "250"))
    n_agents = int(os.environ.get("SABC_AGENTS", "8"))
    res = sweep(hiddens=hiddens, inits=inits, seeds=seeds, trials=trials, n_agents=n_agents)
    print("CELLS (hidden x init -> verdict, median diff, hit_end medians):")
    for c, lp, tp in zip(res["cells"], res["curve"]["legacy"], res["curve"]["torch"]):
        print(f"  hidden={c['hidden']:>3} init={c['init']:<10} verdict={c['verdict']:<14} "
              f"median_diff={c['median_diff']:+.3f} sign_p={c['sign_p']:.3f} "
              f"legacy_hit_end={lp['median_hit_end']:.3f} torch_hit_end={tp['median_hit_end']:.3f}")
    print("CURVE legacy:", [(p["hidden"], p["init"], round(p["median_hit_end"], 3)) for p in res["curve"]["legacy"]])
    print("CURVE torch :", [(p["hidden"], p["init"], round(p["median_hit_end"], 3)) for p in res["curve"]["torch"]])
    out = os.environ.get("SABC_OUT")
    if out:
        import json
        with open(out, "w") as f:
            json.dump(res, f, indent=2)
        print(f"WROTE {out}")
    return res


if __name__ == "__main__":
    main()
