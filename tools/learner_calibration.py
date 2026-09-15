"""P1.6 — RUNNER : contrôle positif de l'APPRENANT in-world, à DOSE PUBLIÉE, n seeds appariés.

Question (backlog, bloc « 🧭 2026-09-14 », rang 1) : l'apprenant tel que le monde le construit
(Actor-Critic TD(0) par tick + REINFORCE épisodique tous les `torch_episode_k` ticks) apprend-il la tâche
linéaire 1-bit de S2-011 quand la dose de crédit n'est plus bornée par la mort ? Les nuls publiés
(S2-009 §crédit, S2-010, S2-011) valaient quelques dizaines de mises à jour par agent, jamais comptées.

Dispositif : `tools.cognitive_demand_inworld.run_learner_probe` — cohorte IMMORTELLE, DV = taux de coups
par bloc, dose comptée. Six bras par seed, appariés (même seed, même monde) :

    oracle          LinearCognitiveOracle câblé — contrôle POSITIF de la DV (attendu 1.0)
    lr0_reference   apprenant à lr=0 — le plafond de l'incapable, mesuré DANS le dispositif (la barre)
    natural         l'apprenant tel que publié (lr 0.04, TD on, récompenses ×1)
    lr_low          lr 0.004 — le balayage E19 : un nul qui se referme sous le pas est un nul de RÉGLAGE
    td_off          chemin épisodique seul (le TD par tick coupé)
    x0.05           récompenses ×0.05 (le critic vit sur un nœud tanh face à r ≈ −18/tick)

Les DEUX issues sont nommées d'avance (backlog P1.6) : une variante apprend -> S2-010/S2-011 sont
ROUVERTS (bandeau APRÈS ce verdict, P3.6) et « in-world 0 » peut bouger ; aucune n'apprend à n=12 ->
S2-010/S2-011 sont RENFORCÉS et le run P4.4 devient légitime.

Coût : borné AVANT par `project_cost` sur une unité MESURÉE ici (pas extrapolée d'un préfixe court —
l'unité est un bras complet), reprise par seed (le JSON est réécrit après chaque bras).

Usage : python tools/learner_calibration.py   (env : LC_SEEDS=12 LC_TICKS=2000 LC_BLOCK=400 LC_AGENTS=12
        LC_BUDGET_S=9000 LC_OUT=results/learner_calibration.json)
"""
import json
import os
import sys
import time

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.cognitive_demand_inworld import learner_verdict, run_learner_probe  # noqa: E402
from tools.cost_guard import project_cost  # noqa: E402
from tools.experiment_preflight import (  # noqa: E402
    PreflightError, assert_control_family, assert_verdict_invariant_to_optimizer, declare_design)

ARMS = {
    "oracle": dict(policy="oracle"),
    "lr0_reference": dict(policy="torch", lr=0.0),
    "natural": dict(policy="torch"),
    "lr_low": dict(policy="torch", lr=0.004),
    "td_off": dict(policy="torch", td_enabled=False),
    "x0.05": dict(policy="torch", reward_scale=0.05),
}
LEARNER_ARMS = ("natural", "lr_low", "td_off", "x0.05")
MIN_SEP = 0.05          # barre = référence lr=0 + MIN_SEP (jamais « chance + marge », P2.15)
MIN_GAIN = 0.05


def _git_provenance():
    from tools.preregister import provenance        # P2.68 : un seul site de provenance
    return provenance()


def _load(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return None


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def _median(xs):
    xs = [float(x) for x in xs if x is not None]
    if not xs:
        raise ValueError("médiane d'une liste VIDE demandée : aucune valeur n'est fabriquée")
    return float(np.median(xs))


def summarize(arms, learner_arms=LEARNER_ARMS):
    """Médianes par bras (unité = seed), verdicts appariés à la référence lr=0 et à l'oracle du MÊME run,
    signe par seed, et balayage E19 (natural @0.04 vs lr_low @0.004). `learner_arms` : les bras jugés
    (défaut : les quatre de P1.6 ; P3.4 passe ceux du legacy, mêmes noms, autre politique)."""
    med = {}
    for arm, rec in arms.items():
        per = rec["per_seed"]
        # P3.4 (2026-09-15) : une cellule NON MESURÉE (`erreur` posée par le runner : l'apprenant a divergé
        # et la cohorte n'a plus pris AUCUNE décision, `run_learner_probe` a refusé de fabriquer un taux)
        # est comptée dans `n` et publiée dans `non_mesures`, jamais avalée par la médiane.
        ok = [r for r in per.values() if r.get("learning") is not None]
        med[arm] = {"n": len(per), "non_mesures": len(per) - len(ok),
                    "hit_first": _median([r["hit_first"] for r in ok]),
                    "hit_last": _median([r["hit_last"] for r in ok]),
                    "td_updates": _median([r["learning"]["td_updates"] for r in ok]),
                    "episode_updates": _median([r["learning"]["episode_updates"] for r in ok]),
                    "dW_abs_sum": _median([r["learning"]["dW_abs_sum"] for r in ok])}
    ref, orc = med["lr0_reference"], med["oracle"]
    verdicts = {}
    for arm in learner_arms:
        v = learner_verdict(learner_first=med[arm]["hit_first"], learner_last=med[arm]["hit_last"],
                            reference_last=ref["hit_last"], oracle_last=orc["hit_last"],
                            min_sep=MIN_SEP, min_gain=MIN_GAIN)
        seeds = sorted(set(arms[arm]["per_seed"]) & set(arms["lr0_reference"]["per_seed"]))
        above = sum(1 for s in seeds
                    if arms[arm]["per_seed"][s].get("hit_last") is not None
                    and arms["lr0_reference"]["per_seed"][s].get("hit_last") is not None
                    and arms[arm]["per_seed"][s]["hit_last"] > arms["lr0_reference"]["per_seed"][s]["hit_last"] + MIN_SEP)
        v["seeds_above_reference"] = f"{above}/{len(seeds)}"     # un seed NON MESURÉ compte au dénominateur
        v["seeds_non_mesures"] = med[arm]["non_mesures"]
        verdicts[arm] = v

    def measure(lr):
        arm = {0.04: "natural", 0.004: "lr_low"}[lr]
        return med[arm]["hit_last"], orc["hit_last"]
    try:
        closure = assert_verdict_invariant_to_optimizer(measure, lrs=(0.04, 0.004), reference_floor=0.9,
                                                        label="nul de l'apprenant in-world")
        e19 = {"status": "INVARIANT_AU_PAS", "detail": closure}
    except PreflightError as exc:
        e19 = {"status": "NUL_ARTEFACT_DE_REGLAGE_OU_REFERENCE_EFFONDREE", "detail": str(exc)}
    return {"medians": med, "verdicts": verdicts, "e19": e19}


def main():
    n = int(os.environ.get("LC_SEEDS", "12"))
    ticks = int(os.environ.get("LC_TICKS", "2000"))
    block = int(os.environ.get("LC_BLOCK", "400"))
    agents = int(os.environ.get("LC_AGENTS", "12"))
    budget_s = float(os.environ.get("LC_BUDGET_S", "9000"))
    from src.paths import results_file                       # porte 12 : jamais un chemin de données en dur
    out = os.environ.get("LC_OUT") or str(results_file("learner_calibration.json"))
    out = out if os.path.isabs(out) else os.path.join(_ROOT, out)
    seeds = [2026 + i for i in range(n)]

    design = declare_design(
        question="L'apprenant in-world (TD(0) par tick + REINFORCE épisodique) apprend-il la tâche linéaire "
                 "1-bit de S2-011 quand la dose de crédit n'est plus bornée par la mort ?",
        replication_unit="seed (une cohorte immortelle de %d agents, un monde par seed ; 6 bras appariés)" % agents,
        n_independent=n,
        links={"dose_de_credit": "measured", "controle_positif_oracle": "measured",
               "plafond_incapable_lr0": "measured", "taux_de_coups_apprenant": "measured"},
        cost_estimate="unité = un bras complet (%d ticks), mesurée sur le premier bras avant projection" % ticks,
        control_family=assert_control_family(cells=2 * n, alpha_family=0.05))

    data = _load(out) or {"design": design, "provenance": _git_provenance(), "params": {
        "seeds": seeds, "ticks": ticks, "block": block, "agents": agents, "budget_s": budget_s,
        "min_sep": MIN_SEP, "min_gain": MIN_GAIN, "arms": ARMS},
        "arms": {arm: {"params": p, "per_seed": {}} for arm, p in ARMS.items()}, "cost": {}}
    t_start = time.time()

    # Coût : UNE unité du type le plus cher (apprenant torch, ticks complets), mesurée puis projetée.
    if "unit_s" not in data["cost"]:
        t0 = time.time()
        first = run_learner_probe(seed=seeds[0], num_agents=agents, ticks=ticks, block=block, **ARMS["natural"])
        unit_s = time.time() - t0
        first["elapsed_s"] = unit_s
        data["arms"]["natural"]["per_seed"][str(seeds[0])] = first
        data["regime"] = first["regime"]
        data["cost"]["unit_s"] = unit_s
        data["cost"]["projected_s"] = project_cost(unit_s, n_units=n * len(ARMS), budget_s=budget_s,
                                                   label="learner-calibration")
        _save(out, data)
        print(f"[cost] unité mesurée {unit_s:.1f}s ; projeté ×{n * len(ARMS)} ×marge = "
              f"{data['cost']['projected_s'] / 60:.0f} min (budget {budget_s / 60:.0f} min)", flush=True)

    for s in seeds:
        for arm, params in ARMS.items():
            if str(s) in data["arms"][arm]["per_seed"]:
                continue                                   # reprise : déjà mesuré
            t0 = time.time()
            r = run_learner_probe(seed=s, num_agents=agents, ticks=ticks, block=block, **params)
            r["elapsed_s"] = time.time() - t0
            data["arms"][arm]["per_seed"][str(s)] = r
            _save(out, data)
            print(f"[{arm:13s} seed {s}] hit {r['hit_first']:.3f} -> {r['hit_last']:.3f} | "
                  f"TD {r['learning']['td_updates']} ep {r['learning']['episode_updates']} "
                  f"dW {r['learning']['dW_abs_sum']:.2f} | {r['elapsed_s']:.0f}s", flush=True)

    data["summary"] = summarize(data["arms"])
    data["cost"]["elapsed_total_s"] = time.time() - t_start
    _save(out, data)
    print("\n=== P1.6 — apprenant in-world, n=%d seeds, %d ticks ===" % (n, ticks))
    for arm, m in data["summary"]["medians"].items():
        print(f"{arm:13s} hit {m['hit_first']:.3f} -> {m['hit_last']:.3f}  TD {m['td_updates']:.0f}  "
              f"ep {m['episode_updates']:.0f}  dW {m['dW_abs_sum']:.1f}")
    for arm, v in data["summary"]["verdicts"].items():
        print(f"{arm:13s} {v['verdict']:22s} sep {v['sep']:+.3f} gain {v['gain']:+.3f} "
              f"seeds>ref {v['seeds_above_reference']}  ({v['why']})")
    print("E19 :", data["summary"]["e19"]["status"])
    print("->", out)
    return data


if __name__ == "__main__":
    main()
