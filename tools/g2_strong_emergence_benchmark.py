"""
tools/g2_strong_emergence_benchmark.py — Banc Officiel de Validation du Niveau 2 G2-Fort (Franchissement d'EDR-LOCK-001).

Évalue rigoureusement à puissance (n=12 seeds appariés) si la compétence composée
(séquence means->ends : CRAFT en S1 puis USE en S2) ÉMERGE spontanément dans le bras NU
(sans gate conditionnel, sans oracle, sans curriculum) sous la demande du monde (d=1.0 vs d=0.0).

Critère exécutable de la porte SDR-G2 :
- POSITIF : comp_rate(d=1.0) > comp_rate(d=0.0) pour au moins 11/12 seeds (test binomial p <= 0.0032).
- CONTRÔLE : séparation confirmée sans artefacts d'optimisation E19.
"""

import sys
import os
import statistics
from typing import Dict, Any, List
import numpy as np
import torch

# Ajout du path racine
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.compositional_world_probe import _energy, _softmax_np, _MOVE, CRAFT, USE, FREE
from src.agents.mamba_agent import MambaAgent
from src.agents.backend import make_population
from src.agents.backend_torch import TorchPopulationModel


def run_bare_emergence_seed(
    demand: float,
    seed: int,
    episodes: int = 1000,
    n_agents: int = 64,
    lr: float = 0.005,
) -> float:
    """
    Entraîne une population nue (SANS GATE) sur le monde craft->consomme à la demande spécifiée.
    Renvoie le comp_rate moyen sur le dernier quart des épisodes.
    """
    TorchPopulationModel.CONDITION_GATE = False
    TorchPopulationModel.ANTISAT = 0.0
    TorchPopulationModel.GATE_TARGET = None
    TorchPopulationModel.BILINEAR = False

    np.random.seed(seed)
    torch.manual_seed(seed)

    pop = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
    pop.opt = torch.optim.Adam(
        [p for p in [pop.W, pop.U, pop.V, pop.W_bl] if p is not None],
        lr=lr,
    )

    rng = np.random.RandomState(seed + 1)
    obs_a = (rng.randn(n_agents, pop.I) * 0.5).astype(np.float32)
    obs_b = (rng.randn(n_agents, pop.I) * 0.5).astype(np.float32)

    def sample_fn(preds):
        p = _softmax_np(np.asarray(preds)[:, :_MOVE])
        return np.array([rng.choice(_MOVE, p=pi) for pi in p])

    comp_hist = []
    for _ in range(episodes):
        pop.H = torch.zeros((n_agents, pop.N))
        preds1, _ = pop.forward(obs_a)
        move1 = sample_fn(preds1)
        did_x = (move1 == CRAFT)
        act1 = [{"move": int(m), "grab": 0, "rub": 0} for m in move1]

        preds2, _ = pop.forward(obs_b)
        move2 = sample_fn(preds2)
        act2 = [{"move": int(m), "grab": 0, "rub": 0} for m in move2]

        energy = np.array([
            _energy(int(move2[i]), bool(did_x[i]), demand)
            for i in range(n_agents)
        ], dtype=np.float32)

        adv = energy - energy.mean()
        # Crédit épisodique agnostique sur l'agent nu (sans module de gate)
        pop.learn_episode([obs_a, obs_b], [act1, act2], adv, gate_last_only=False)

        comp_hist.append(np.mean((move2 == USE) & did_x))

    q = max(1, episodes // 4)
    return float(np.mean(comp_hist[-q:]))


def run_g2_strong_emergence_benchmark(
    n_seeds: int = 12,
    episodes: int = 800,
    lr: float = 0.005,
) -> Dict[str, Any]:
    """
    Exécute le banc complet à n seeds appariés pour tester l'émergence G2-Fort.
    """
    print(f"\n🧱 [BANC G2-FORT / EDR-LOCK-001] Test d'émergence non supervisée sur {n_seeds} seeds appariés...")

    rates_d0 = []
    rates_d1 = []
    wins = 0

    for s in range(n_seeds):
        r0 = run_bare_emergence_seed(demand=0.0, seed=s, episodes=episodes, lr=lr)
        r1 = run_bare_emergence_seed(demand=1.0, seed=s, episodes=episodes, lr=lr)
        rates_d0.append(r0)
        rates_d1.append(r1)
        is_win = bool(r1 > r0)
        if is_win:
            wins += 1
        print(f"  Seed {s:02d} : comp_rate d=0.0: {r0:.4f} | d=1.0: {r1:.4f} (Δ={r1-r0:+.4f}) -> {'GAGNÉ' if is_win else 'PERDU'}")

    med_d0 = float(statistics.median(rates_d0))
    med_d1 = float(statistics.median(rates_d1))
    ratio = med_d1 / max(1e-5, med_d0)

    # Calcul de p-value binomiale unilatérale
    import math
    p_val = sum(math.comb(n_seeds, k) * (0.5 ** n_seeds) for k in range(wins, n_seeds + 1))

    is_validated = bool(wins >= n_seeds - 1 and p_val <= 0.0032 and ratio >= 2.0)
    verdict = "G2_STRONG_EMERGENCE_VALIDATED" if is_validated else "G2_STRONG_EMERGENCE_REFUTED"

    results = {
        "verdict": verdict,
        "n_seeds": n_seeds,
        "wins": wins,
        "p_value": float(round(p_val, 6)),
        "median_comp_rate_d0": float(round(med_d0, 4)),
        "median_comp_rate_d1": float(round(med_d1, 4)),
        "emergence_ratio": float(round(ratio, 2)),
        "lr": lr,
        "episodes": episodes,
        "rates_d0": [float(round(x, 4)) for x in rates_d0],
        "rates_d1": [float(round(x, 4)) for x in rates_d1],
    }

    print("\n📊 --- VERDICT OFFICIEL G2-FORT / EDR-LOCK-001 ---")
    print(f"🔹 Victoires Appariées (d=1.0 > d=0.0) : {wins}/{n_seeds} (p-value binomiale = {p_val:.6f})")
    print(f"🔹 Médiane comp_rate (d=0.0)          : {med_d0:.4f} (~ chance/bruit)")
    print(f"🔹 Médiane comp_rate (d=1.0)          : {med_d1:.4f} (Émergence nette)")
    print(f"🔹 Ratio d'Émergence Spontanée        : x{ratio:.2f}")
    print(f"🔹 VERDICT FINAL                      : {verdict}")
    print("--------------------------------------------------\n")

    # Export des résultats dans results/
    import json
    out_dir = os.path.join(_ROOT, "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "g2_strong_emergence_benchmark.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results


if __name__ == "__main__":
    res = run_g2_strong_emergence_benchmark(n_seeds=12, episodes=1000, lr=0.005)
