#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""S2-BLIND-CHAMPION — un champion RENDU AVEUGLE survit-il MIEUX que le champion intact ?

Observation d'origine (2026-09-08, n=1 seed, faite en cherchant un contrôle NÉGATIF pour
S2-SUBJECT-VARIANCE) : dans `stoneage`, mettre à zéro les lignes d'entrée de `W` — l'observation
n'entre plus dans le calcul — fait passer la survie médiane de **27,5 à 38,2 ticks (+39 %)**. À n=1
ce n'est pas un résultat ; cette règle le met à l'épreuve à n=7 seeds appariées.

Si c'est réel, c'est le pendant **in-world et NON câblé** d'`EDR-EVO-011` (lire le canal de type coûte
la survie, r=0,631) : ici le sujet n'est pas un lecteur bricolé mais le CHAMPION ÉVOLUÉ, et la perte ne
vient pas d'un acte coûteux qu'on lui ajoute mais de son propre traitement de l'observation. Cela
expliquerait d'un coup S2-012, `EDR-EVO-004` (saillance au plancher sur TOUS les canaux) et le verdict
`PERCEPTION_DECOY` d'`EDR-124` : la sélection n'a pas « omis » de lire, elle a **élagué une lecture qui
coûte**.

⚠️ CONFOND DÉCLARÉ D'AVANCE, et non séparé par ce design : mettre à zéro les lignes d'entrée ne coupe
pas que l'information, cela baisse aussi le NIVEAU d'excitation du réseau. Un gain de survie pourrait
venir de la SÉDATION plutôt que de la cécité. Le séparer demanderait un bras à entrée BROUILLÉE (même
excitation, information détruite) — prochaine étape si le résultat est positif.

Usage :  python -m tools.evo_runs.s2_blind_champion
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import statistics
import sys
import time

PREREG = "S2-BLIND-CHAMPION"

WORLD = "stoneage"
REGIME = {"num_agents": 12, "max_ticks": 200}
K = 12
SEEDS = (2026, 3026, 3027, 3028, 3029, 3030, 3031)
FLOOR = 24.0                       # PLANCHER_NOPERC["stoneage"], MESURÉ (jamais importé d'ailleurs)

BAR_HIGH, BAR_LOW, ALPHA = 1.20, 1.05, 0.05
BLIND_INSENSIBLE_TOL = 0.05        # contrôle (ii) : l'aveugle ne doit plus réagir à l'ablation
ALPHA_FAMILY = 0.05
FAMILY_CELLS = len(SEEDS)          # les 7 contrôles (ii) forment une famille — classe E23
ALPHA_CELL = ALPHA_FAMILY / FAMILY_CELLS


# ==================================================================================================
# 1. VERDICT — PUR. Aucune simulation : c'est l'instrument, il se calibre.
# ==================================================================================================
def _sign_p(k, n):
    """p binomiale exacte bilatérale (test des signes, H0 p=0.5). Même statistique que le reste du dépôt."""
    if n <= 0:
        return 1.0
    k_hi = max(k, n - k)
    return min(1.0, 2.0 * sum(math.comb(n, i) for i in range(k_hi, n + 1)) / (2 ** n))


def blind_champion_verdict(rows, bar_high=BAR_HIGH, bar_low=BAR_LOW, alpha=ALPHA,
                           tol=BLIND_INSENSIBLE_TOL, floor=FLOOR):
    """`rows` : une ligne PAR SEED, avec {'seed', 'intact', 'blind'} où chaque bras porte
    {'intact_median', 'within_ratio', 'verdict', 'w_ok'}.

    Branches EXHAUSTIVES, contrôles AVANT la DV (ordre imposé par le sceau) :
      * un contrôle échoue sur un seed            -> `INDETERMINE-HARNAIS`
      * `r_blind >= 1.20` ET `sign_p < 0.05`      -> `AVEUGLE_SURVIT_MIEUX`
      * `r_blind <= 1.05`                         -> `PAS_DE_COUT` (l'observation n=1 est rétractée)
      * sinon                                     -> `INDETERMINE`
    Une entrée VIDE rend `INDETERMINE-SANS-MESURE`, jamais un verdict de fond."""
    rows = list(rows or [])
    out = {"verdict": None, "r_blind": float("nan"), "sign_p": float("nan"), "n": 0,
           "ratios": [], "echecs": [], "ecartes": []}
    if not rows:
        out["verdict"] = "INDETERMINE-SANS-MESURE"
        out["echecs"].append("aucune cellule mesurée : une absence de mesure n'est pas un résultat")
        return out

    for r in rows:
        s, i, b = r.get("seed"), r.get("intact") or {}, r.get("blind") or {}
        if not i or not b:
            out["echecs"].append(f"seed {s} : un bras manque — un bras absent n'est pas un bras nul")
            continue
        # (i) intervention réelle et MINIMALE
        if not b.get("w_ok"):
            out["echecs"].append(f"seed {s} : (i) le génome AVEUGLE n'est pas le champion aux seules "
                                 "lignes d'entrée annulées")
        # (ii) l'aveuglement MORD : l'ablation de perception ne doit plus rien lui faire
        wr = b.get("within_ratio")
        if wr is None or abs(float(wr) - 1.0) > tol:
            out["echecs"].append(f"seed {s} : (ii) l'AVEUGLE reste sensible à l'ablation de "
                                 f"perception (within_ratio={wr}) — il voit encore")
        # (iii) plancher sur le bras INTACT
        if float(i.get("intact_median", 0.0)) < float(floor):
            out["ecartes"].append(s)

    if out["echecs"]:
        out["verdict"] = "INDETERMINE-HARNAIS"
        return out

    paires = [(float(r["blind"]["intact_median"]), float(r["intact"]["intact_median"]))
              for r in rows if r.get("seed") not in out["ecartes"]]
    if len(paires) < 2:
        out["verdict"] = "INDETERMINE-DEGENERE"
        out["echecs"].append(f"{len(paires)} seed(s) exploitable(s) : on ne conclut pas sur moins de deux")
        return out

    ratios = [b / max(i, 1e-9) for b, i in paires]
    eff = [x for x in ratios if x != 1.0]
    out["ratios"], out["n"] = ratios, len(paires)
    out["r_blind"] = statistics.median(ratios)
    out["sign_p"] = _sign_p(sum(1 for x in eff if x > 1.0), len(eff))

    if out["r_blind"] >= bar_high and out["sign_p"] < alpha:
        out["verdict"] = "AVEUGLE_SURVIT_MIEUX"
    elif out["r_blind"] <= bar_low:
        out["verdict"] = "PAS_DE_COUT"
    else:
        out["verdict"] = "INDETERMINE"
    return out


# ==================================================================================================
# 2. SUJETS — l'intervention, et sa vérification
# ==================================================================================================
def make_blind(genome):
    """Copie PROFONDE du génome dont les LIGNES d'entrée de W sont annulées : l'observation n'entre
    plus nulle part. Rien d'autre n'est touché — corps, biais et récurrence restent identiques."""
    g = copy.deepcopy(genome)
    W = g.W.copy()
    W[:g.num_inputs, :] = 0.0
    g.W = W
    return g


def check_blind(blind, ref):
    """Contrôle (i) : l'intervention est-elle RÉELLE et MINIMALE ? Les lignes d'entrée à zéro EXACT,
    et tout le reste BIT-IDENTIQUE au champion. Sans ce contrôle, le contraste confondrait
    « l'observation n'entre plus » avec « le génome a changé »."""
    import numpy as np

    n = ref.num_inputs
    return bool(np.all(blind.W[:n, :] == 0.0) and np.array_equal(blind.W[n:, :], ref.W[n:, :]))


# ==================================================================================================
# 3. RUNNER
# ==================================================================================================
def run_blind_champion(seeds=SEEDS, k=K, regime=None, world=WORLD, map_fn=None,
                       champion_fn=None, verbose=True):
    """GARDE D'ARGUMENTS, EN TÊTE : un plan vide ou un régime dégénéré est une erreur d'APPEL, jamais
    un fait sur le monde. Le refus est instantané — aucun génome n'est chargé."""
    regime = dict(regime or REGIME)
    seeds = list(seeds or [])
    if not seeds or int(k) <= 0 or int(regime.get("num_agents", 0)) <= 0 \
            or int(regime.get("max_ticks", 0)) <= 0:
        raise ValueError(
            f"run_blind_champion : argument degenere (seeds={len(seeds)}, K={k}, regime={regime}) -- "
            "aucune mesure possible ; ne pas confondre avec une mesure nulle OBSERVEE.")

    if map_fn is None:
        from tools.s2_demand_ablation import run_ablation_map as map_fn
    if champion_fn is None:
        from tools.s2_demand import load_champion_genome as champion_fn

    rows = []
    for s in seeds:
        ref = champion_fn()
        blind = make_blind(ref)
        mi = map_fn(worlds=[world], seed=s, K=k, subject=ref, **regime)[world]
        mb = map_fn(worlds=[world], seed=s, K=k, subject=blind, **regime)[world]
        mb = dict(mb, w_ok=check_blind(blind, ref))
        rows.append({"seed": s, "intact": mi, "blind": mb})
        if verbose:
            print(f"  seed {s} : intact={mi['intact_median']:6.1f} ({mi['verdict']:22s}) | "
                  f"aveugle={mb['intact_median']:6.1f} ({mb['verdict']:22s}) | "
                  f"r={mb['intact_median'] / max(mi['intact_median'], 1e-9):.3f} "
                  f"| (i) {'ok' if mb['w_ok'] else 'ECHEC'} "
                  f"| (ii) within_aveugle={mb['within_ratio']:.3f}")
    return rows, blind_champion_verdict(rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=len(SEEDS))
    ap.add_argument("--k", type=int, default=K)
    ap.add_argument("--out", default=None, help="JSON de sortie ; `-` désactive")
    args = ap.parse_args(argv)

    from tools.experiment_preflight import assert_control_family, declare_design
    from tools.preregister import verify

    rule = verify(PREREG)
    print(f"[preregistration] {PREREG} : sceau VERIFIE")

    seeds = list(SEEDS)[:args.seeds]
    # GARDE E23 : les 7 contrôles (ii) forment une FAMILLE — le seuil par cellule est corrigé, jamais
    # celui d'un test unique. Mesure du 2026-09-07 : une bande fixe sur 24 cellules donnait 0,216 de
    # fausse alarme sur un harnais PARFAIT.
    famille = assert_control_family(cells=len(seeds), alpha_family=ALPHA_FAMILY,
                                    alpha_cell=ALPHA_FAMILY / max(1, len(seeds)),
                                    method="bonferroni")
    design = declare_design(
        question=rule["question"], control_family=famille,
        replication_unit="seed de monde (K ères appariées par cellule)",
        n_independent=len(seeds),
        links={"lignes d'entree a zero -> l'observation n'entre plus": "measured",
               "l'observation n'entre plus -> survie": "measured"},
        cost_estimate=f"{2 * len(seeds)} cellules x 3 conditions x {args.k} eres, ~29 s/cellule mesure")
    print(f"[design] unite = {design['replication_unit']} | famille = {famille['cells']} cellules, "
          f"alpha_cell={famille['alpha_cell']:.5f}")

    from tools.jobs.run import hold
    t0 = time.time()
    with hold("kuzu", owner="s2-blind-champion", ttl_s=3600):
        rows, v = run_blind_champion(seeds=seeds, k=args.k)
    elapsed = time.time() - t0

    print(f"\n  VERDICT : {v['verdict']}  (r_blind={v['r_blind']:.3f} sign_p={v['sign_p']:.4g} n={v['n']})")
    for e in v["echecs"]:
        print(f"      - {e}")
    if v["ecartes"]:
        print(f"      seeds ecartes (bras intact SOUS le plancher {FLOOR}) : {v['ecartes']}")
    print(f"  ratios par seed : {[round(x, 3) for x in v['ratios']]}")
    print(f"  COUT : {elapsed:.0f}s pour {2 * len(seeds)} cellules -> {elapsed / max(1, 2 * len(seeds)):.1f} s/cellule")

    out = args.out
    if out != "-":
        out = out or os.path.join("results", "s2_blind_champion.json")
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump({"preregistration": PREREG, "design": design, "world": WORLD,
                       "regime": REGIME, "K": args.k, "seeds": seeds, "floor": FLOOR,
                       "elapsed_s": elapsed, "verdict": v, "rows": rows}, fh, indent=1, default=str)
        print(f"  persiste -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
