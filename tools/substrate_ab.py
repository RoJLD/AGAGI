"""A/B de LEARNABILITÉ du substrat — ADR-003, Axe 1, barreau-0.

Question : sur une contingence contrôlée (obs fixe -> action cible), quel substrat
APPREND mieux — `legacy` (hebbien/Actor-Critic TD numpy, gradient dérivé à la main) ou
`torch` (même Actor-Critic TD, gradient par AUTOGRAD) ? Même interface PopulationModel,
appariement par seed, verdict par test de signe.

CE N'EST PAS un transfer_ratio. L'A/B transfert complet exige d'intégrer le backend torch
DANS `env.step()` (le monde possède le batching) avec le contrat forward complet
(NTM/attention/world-model/108 sorties) — gros chantier. Ce barreau-0 mesure la capacité
d'apprentissage minimale et runnable, et sert de PORTE DE DÉCISION avant cet investissement.

Usage : python tools/substrate_ab.py   (env: SAB_SEEDS, SAB_TICKS, SAB_AGENTS)
"""
import os
import sys
import math
import statistics

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.agents.mamba_agent import MambaAgent
from src.agents.backend import make_population

_MOVE = 8  # logits de déplacement


def _sign_p(k: int, n: int) -> float:
    """p-value binomiale exacte bilatérale (test de signe, H0 p=0.5)."""
    if n <= 0:
        return 1.0
    k_hi = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(k_hi, n + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def compute_ab_verdict(rows, band: float = 0.02, sign_alpha: float = 0.1) -> dict:
    """Lignes appariées {diff = torch_delta - legacy_delta} -> verdict. PUR (testable sans run).

    **GARDE DE PUISSANCE ARMÉE le 2026-07-21 (calibration P2.5).** `sign_p` était calculé, renvoyé et
    affiché — mais **ne conditionnait RIEN** : le verdict reposait entièrement sur `med > band`.
    Mesuré avant correctif, tous rendaient `GRADIENT_GAGNE` :
      * 6 favorables sur 11, **`sign_p = 1.000`** (le test de signe dit « aucune preuve, absolument ») ;
      * **n = 2** seulement, avec une grosse médiane ;
      * médiane 0.021 (à peine au-dessus de `band`) contre deux contre-exemples de −0.5.
    C'est un générateur de FAUX POSITIFS pur — et son garde-fou était déjà dans la fonction, débranché.
    `ablation_verdict`, lui, bloque à `n < 12` dans les DEUX sens depuis toujours.

    Le verdict exige désormais **la bande ET le test de signe** (`sign_p < sign_alpha`). Conséquence
    arithmétique à connaître : en séparation parfaite il faut **n ≥ 5** (`sign_p` vaut 0.25 à n=3,
    0.0625 à n=5) — trois réplicats ne peuvent porter aucun verdict, quelle que soit l'amplitude.

    ⚠️ Portée du changement : il ne peut que TRANSFORMER UN POSITIF EN NEUTRE, jamais l'inverse. Les
    conclusions NEUTRES du graphe sont donc intactes par construction, et les affirmations positives
    appliquaient déjà `sign_p` à la main."""
    diffs = [r["diff"] for r in rows]
    n = len(diffs)
    if n == 0:
        return {"n": 0, "median_diff": 0.0, "n_gradient_favorable": 0, "sign_p": 1.0,
                "verdict": "NEUTRE", "underpowered": False}
    med = float(statistics.median(diffs))
    eff = [d for d in diffs if abs(d) > 1e-12]
    n_grad = sum(1 for d in eff if d > 0)
    sign_p = _sign_p(n_grad, len(eff))
    powered = sign_p < sign_alpha
    if med > band and powered:
        verdict = "GRADIENT_GAGNE"
    elif med < -band and powered:
        verdict = "HEBBIEN_GAGNE"
    else:
        verdict = "NEUTRE"
    return {"n": n, "median_diff": med, "n_gradient_favorable": n_grad, "sign_p": sign_p,
            "verdict": verdict, "underpowered": bool(abs(med) > band and not powered)}


def run_substrate_ab(backend: str, seed: int = 0, ticks: int = 200,
                     n_agents: int = 8, target_move: int = 0) -> dict:
    """Entraîne une population à émettre `target_move` sur une obs fixe. Renvoie le taux
    de bonne action au début vs à la fin (delta = apprentissage)."""
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except Exception:
        pass
    agents = [MambaAgent() for _ in range(n_agents)]
    pop = make_population(agents, backend=backend)
    rng = np.random.RandomState(seed + 1)
    obs = (rng.randn(n_agents, agents[0].genome.num_inputs) * 0.5).astype(np.float32)  # contingence fixe

    hits = []
    for _ in range(ticks):
        preds, _ = pop.forward(obs)
        moves = np.asarray(preds)[:, :_MOVE].argmax(axis=1)
        reward = np.where(moves == target_move, 1.0, -1.0).astype(np.float32)
        pop.learn(reward, [{"move": int(m), "grab": 0, "rub": 0} for m in moves])
        hits.append(float(np.mean(moves == target_move)))

    q = max(1, ticks // 4)
    hit_start, hit_end = float(np.mean(hits[:q])), float(np.mean(hits[-q:]))
    return {"backend": backend, "seed": int(seed), "ticks": ticks, "n_agents": n_agents,
            "hit_start": hit_start, "hit_end": hit_end, "delta": hit_end - hit_start}


def compare(seeds=(0, 1, 2), ticks: int = 200, n_agents: int = 8) -> dict:
    """A/B apparié legacy vs torch par seed -> verdict de learnabilité."""
    rows = []
    for s in seeds:
        leg = run_substrate_ab("legacy", seed=s, ticks=ticks, n_agents=n_agents)
        tor = run_substrate_ab("torch", seed=s, ticks=ticks, n_agents=n_agents)
        rows.append({"seed": int(s), "legacy_delta": leg["delta"], "torch_delta": tor["delta"],
                     "diff": tor["delta"] - leg["delta"], "legacy": leg, "torch": tor})
    return {**compute_ab_verdict(rows), "per_seed": rows}


def main():
    seeds = [int(s) for s in os.environ.get("SAB_SEEDS", "0,1,2,3,4").split(",") if s.strip()]
    ticks = int(os.environ.get("SAB_TICKS", "300"))
    n_agents = int(os.environ.get("SAB_AGENTS", "8"))
    res = compare(seeds=seeds, ticks=ticks, n_agents=n_agents)
    print(f"VERDICT={res['verdict']} median_diff={res['median_diff']:+.3f} "
          f"(grad_fav={res['n_gradient_favorable']}/{res['n']}, sign_p={res['sign_p']:.3f})")
    for r in res["per_seed"]:
        print(f"  seed={r['seed']} legacy d={r['legacy_delta']:+.3f}  torch d={r['torch_delta']:+.3f}  "
              f"diff={r['diff']:+.3f}")
    return res


if __name__ == "__main__":
    main()
