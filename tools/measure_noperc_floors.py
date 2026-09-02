# -*- coding: utf-8 -*-
"""Campagne PLANCHER_NOPERC — les 2 derniers fichiers sans borne (s2_demand_ablation + s2_openloop).

Design du concepteur A (2026-09-02) : plancher par monde = max(zero_obs, random_action), les DEUX sur
CLONES DU CHAMPION (S2-003 : son edge de survie est corps/métabolisme — une politique aléatoire sur
agents frais perdrait aussi ce corps et SOUS-garderait). Régime GRAVÉ des records S2-002/S2-003 :
12 agents, 200 ticks, K=12. seed ≠ 2026 : la constante ne doit pas être couplée au tirage de la mesure
qu'elle garde.

⚠️ À LANCER SOUS BAIL kuzu UNIQUEMENT (mondes réels). Coût estimé 30-60 s (ancre WARM-010 : ~6 s pour
4 800 ticks sur le même banc ; les bras aveugles meurent tôt).
"""
import statistics
import sys

import numpy as np

sys.path.insert(0, '.')
from tools.jobs.run import hold

with hold("kuzu", owner="planchers-s2", ttl_s=1800):
    from tools.s2_demand import WORLDS, run_condition, load_champion_genome
    from tools.s2_openloop_probe import ZeroObsMamba
    from src.agents.baseline_models import RandomActionBatchModel

    champion = load_champion_genome()
    K, NUM_AGENTS, MAX_TICKS, SEED = 12, 12, 200, 3026
    print(f"regime GRAVE des records S2-002/S2-003 : {NUM_AGENTS} agents, {MAX_TICKS} ticks, K={K}, "
          f"seed={SEED} (!= 2026, decouple du tirage garde)")
    print(f"{'monde':<14} {'zero_obs':>9} {'random':>9} {'PLANCHER':>9}")
    floors = {}
    for w in list(WORLDS):
        zero = run_condition(WORLDS[w], ZeroObsMamba, champion, SEED,
                             num_agents=NUM_AGENTS, max_ticks=MAX_TICKS, n_eras=K)
        rand = run_condition(WORLDS[w], RandomActionBatchModel, champion, SEED,
                             num_agents=NUM_AGENTS, max_ticks=MAX_TICKS, n_eras=K)
        z = float(np.median(zero["era_survival"]))
        r = float(np.median(rand["era_survival"]))
        floors[w] = {"zero_obs": z, "random_action": r, "floor": max(z, r)}
        ecart = max(z, r) / max(min(z, r), 1e-9)
        note = "  ⚠️ constructions divergentes (>1.5x)" if ecart > 1.5 else ""
        print(f"{w:<14} {z:>9.1f} {r:>9.1f} {max(z, r):>9.1f}{note}")
    print("\nPLANCHER_NOPERC =", {w: v["floor"] for w, v in floors.items()})
    print("(controle de coherence WARM-010 : les deux constructions doivent concorder ; un ecart > 1.5x")
    print(" se rapporte — il dirait que la politique du champion vaut moins que le hasard a corps egal)")
