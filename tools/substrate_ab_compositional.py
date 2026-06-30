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


def run_compositional(backend: str, seed: int = 0, trials: int = 100, n_agents: int = 8,
                      target_x: int = 0, target_y: int = 4) -> dict:
    """Entraîne une pop sur la tâche 2-étapes. Renvoie le taux d'essais PLEINEMENT corrects
    (X-puis-Y) début vs fin (delta = apprentissage compositionnel)."""
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except Exception:
        pass
    agents = [MambaAgent() for _ in range(n_agents)]
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
    seeds = [int(s) for s in os.environ.get("SABC_SEEDS", "0,1,2,3,4").split(",") if s.strip()]
    trials = int(os.environ.get("SABC_TRIALS", "150"))
    n_agents = int(os.environ.get("SABC_AGENTS", "8"))
    res = compare(seeds=seeds, trials=trials, n_agents=n_agents)
    print(f"VERDICT={res['verdict']} median_diff={res['median_diff']:+.3f} "
          f"(grad_fav={res['n_gradient_favorable']}/{res['n']}, sign_p={res['sign_p']:.3f})")
    for r in res["per_seed"]:
        print(f"  seed={r['seed']} legacy d={r['legacy_delta']:+.3f}  torch d={r['torch_delta']:+.3f}  "
              f"diff={r['diff']:+.3f}  (legacy end={r['legacy']['hit_end']:.3f} torch end={r['torch']['hit_end']:.3f})")
    return res


if __name__ == "__main__":
    main()
