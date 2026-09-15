"""P3.4 — RUNNER : contrôle positif de l'apprenant LEGACY in-world, à DOSE PUBLIÉE, n seeds appariés.

Question (backlog P3.4, rang 14) : `MambaBatchModel.compute_policy_gradient` — l'Actor-Critic TD(0)
numpy, chemin actif pendant TOUT l'arc EVO (`use_torch_inworld=False`, modèle recréé à chaque tick) —
apprend-il la tâche linéaire 1-bit de S2-011 quand la dose de crédit n'est plus bornée par la mort ?
Le panel l'avait mesuré à n = 1 comme NON plat (OFF 0,13 = chance, naturel 0,35) : à confirmer ou
infirmer à n = 12, avec la même sonde, le même compteur et les mêmes bras que P1.6 (`learner_calibration`).

Dispositif : `tools.cognitive_demand_inworld.run_learner_probe(policy="legacy")` — cohorte IMMORTELLE,
DV = taux de coups par bloc, dose comptée (`legacy_calls` / `legacy_updates` / `dW_abs_sum`). Quatre bras
par seed, appariés (même seed, même monde) :

    oracle          LinearCognitiveOracle câblé — contrôle POSITIF de la DV (attendu 1.0)
    lr0_reference   legacy à lr=0 (LR_ACTOR = LR_CRITIC = 0) — le plafond de l'incapable, MÊME code à pas nul
    natural         legacy tel que publié (LR_ACTOR 0.04, LR_CRITIC 0.05)
    lr_low          legacy à lr 0.004 (critic 0.005, ratio publié gardé) — balayage E19

Les DEUX issues sont nommées d'avance : `LEARNER_LEARNS` sur `natural` confirme le panel et fait du
legacy un apprenant CALIBRÉ (l'arc EVO tournait sur un apprenant capable d'apprendre CETTE tâche) ;
`LEARNER_INERT` aux deux pas l'infirme et fait de l'arc EVO un arc à apprenant inerte sur la tâche —
ce qui change la lecture de « l'objectif in-world n'achète rien » (EVO-005). Le verdict est lu par
`learner_verdict` (barre = référence lr=0 + 0,05 du MÊME run, jamais « chance + marge »).

Coût : borné AVANT par `project_cost` sur une unité MESURÉE ici ; reprise par seed (JSON réécrit après
chaque bras). Usage : python tools/legacy_learner_calibration.py
      (env : LC_SEEDS=12 LC_TICKS=2000 LC_BLOCK=400 LC_AGENTS=12 LC_BUDGET_S=5400
             LC_OUT=results/legacy_learner_calibration.json)
"""
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.cognitive_demand_inworld import run_learner_probe  # noqa: E402
from tools.cost_guard import project_cost  # noqa: E402
from tools.experiment_preflight import assert_control_family, declare_design  # noqa: E402
from tools.learner_calibration import (  # noqa: E402
    MIN_GAIN, MIN_SEP, _git_provenance, _load, _save, summarize)

ARMS = {
    "oracle": dict(policy="oracle"),
    "lr0_reference": dict(policy="legacy", lr=0.0),
    "natural": dict(policy="legacy"),
    "lr_low": dict(policy="legacy", lr=0.004),
}
LEARNER_ARMS = ("natural", "lr_low")


def main():
    n = int(os.environ.get("LC_SEEDS", "12"))
    ticks = int(os.environ.get("LC_TICKS", "2000"))
    block = int(os.environ.get("LC_BLOCK", "400"))
    agents = int(os.environ.get("LC_AGENTS", "12"))
    budget_s = float(os.environ.get("LC_BUDGET_S", "5400"))
    from src.paths import results_file                       # porte 12 : jamais un chemin de données en dur
    out = os.environ.get("LC_OUT") or str(results_file("legacy_learner_calibration.json"))
    out = out if os.path.isabs(out) else os.path.join(_ROOT, out)
    seeds = [2026 + i for i in range(n)]

    design = declare_design(
        question="L'apprenant LEGACY (MambaBatchModel.compute_policy_gradient, TD(0) numpy par tick, chemin "
                 "de l'arc EVO) apprend-il la tâche linéaire 1-bit de S2-011 à dose non bornée par la mort ?",
        replication_unit="seed (une cohorte immortelle de %d agents, un monde par seed ; 4 bras appariés)" % agents,
        n_independent=n,
        links={"dose_de_credit_legacy": "measured", "controle_positif_oracle": "measured",
               "plafond_incapable_lr0": "measured", "taux_de_coups_legacy": "measured"},
        cost_estimate="unité = un bras legacy complet (%d ticks), mesurée sur le premier bras avant projection" % ticks,
        control_family=assert_control_family(cells=2 * n, alpha_family=0.05))

    data = _load(out) or {"design": design, "provenance": _git_provenance(), "params": {
        "seeds": seeds, "ticks": ticks, "block": block, "agents": agents, "budget_s": budget_s,
        "min_sep": MIN_SEP, "min_gain": MIN_GAIN, "arms": ARMS, "learner_arms": LEARNER_ARMS},
        "arms": {arm: {"params": p, "per_seed": {}} for arm, p in ARMS.items()}, "cost": {}}
    t_start = time.time()

    if "unit_s" not in data["cost"]:
        t0 = time.time()
        first = run_learner_probe(seed=seeds[0], num_agents=agents, ticks=ticks, block=block, **ARMS["natural"])
        unit_s = time.time() - t0
        first["elapsed_s"] = unit_s
        data["arms"]["natural"]["per_seed"][str(seeds[0])] = first
        data["regime"] = first["regime"]
        data["cost"]["unit_s"] = unit_s
        data["cost"]["projected_s"] = project_cost(unit_s, n_units=n * len(ARMS), budget_s=budget_s,
                                                   label="legacy-learner-calibration")
        _save(out, data)
        print(f"[cost] unité mesurée {unit_s:.1f}s ; projeté ×{n * len(ARMS)} ×marge = "
              f"{data['cost']['projected_s'] / 60:.0f} min (budget {budget_s / 60:.0f} min)", flush=True)

    for s in seeds:
        for arm, params in ARMS.items():
            if str(s) in data["arms"][arm]["per_seed"]:
                continue                                   # reprise : déjà mesuré
            t0 = time.time()
            try:
                r = run_learner_probe(seed=s, num_agents=agents, ticks=ticks, block=block, **params)
            except ValueError as exc:
                # Mesuré le 2026-09-15 (seed 2030, bras natural) : l'apprenant legacy DIVERGE (NaN dans
                # les logits, « Variable nan is not in scope » côté logger) et la cohorte ne prend plus
                # AUCUNE décision -> la sonde refuse de fabriquer un taux. La cellule est PUBLIÉE avec sa
                # raison, comptée dans n et dans le test des signes (jamais « au-dessus de la référence »).
                r = {"policy": params["policy"], "seed": int(s), "erreur": str(exc), "hit_first": None,
                     "hit_last": None, "blocks": [], "learning": None, "elapsed_s": time.time() - t0}
                data["arms"][arm]["per_seed"][str(s)] = r
                _save(out, data)
                print(f"[{arm:13s} seed {s}] NON MESURE : {exc}", flush=True)
                continue
            r["elapsed_s"] = time.time() - t0
            data["arms"][arm]["per_seed"][str(s)] = r
            _save(out, data)
            L = r["learning"]
            print(f"[{arm:13s} seed {s}] hit {r['hit_first']:.3f} -> {r['hit_last']:.3f} | "
                  f"legacy {L['legacy_updates']}/{L['legacy_calls']} dW {L['dW_abs_sum']:.2f} | "
                  f"{r['elapsed_s']:.0f}s", flush=True)

    data["summary"] = summarize(data["arms"], learner_arms=LEARNER_ARMS)
    # dose legacy publiée à côté des médianes (summarize ne connaît que les compteurs torch)
    for arm, rec in data["arms"].items():
        per = rec["per_seed"].values()
        import numpy as np
        data["summary"]["medians"][arm]["legacy_updates"] = float(np.median(
            [r["learning"]["legacy_updates"] for r in per if r.get("learning") is not None]))
    data["cost"]["elapsed_total_s"] = time.time() - t_start
    _save(out, data)
    print("\n=== P3.4 — apprenant LEGACY in-world, n=%d seeds, %d ticks ===" % (n, ticks))
    for arm, m in data["summary"]["medians"].items():
        print(f"{arm:13s} hit {m['hit_first']:.3f} -> {m['hit_last']:.3f}  legacy {m['legacy_updates']:.0f}  "
              f"dW {m['dW_abs_sum']:.1f}")
    for arm, v in data["summary"]["verdicts"].items():
        print(f"{arm:13s} {v['verdict']:22s} sep {v['sep']:+.3f} gain {v['gain']:+.3f} "
              f"seeds>ref {v['seeds_above_reference']}  ({v['why']})")
    print("E19 :", data["summary"]["e19"]["status"])
    print("->", out)
    return data


if __name__ == "__main__":
    main()
