#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""S2-SUBJECT-VARIANCE — le verdict du marqueur de demande varie-t-il avec le SUJET, dans le MÊME monde ?

Conséquence directe d'`EDR-S6-FALLBACK-RATE` : en mini-monde, l'ablation mord sur 8 seeds sur 12 dès
que l'init de la politique n'est plus nulle, contre 0/12 à init nulle — le marqueur mesure si **CE
sujet** a un repli survivable sans X. Cette conclusion est jouet et sa portée est bornée dans le
record ; ce qui se transporte est la STRUCTURE de l'argument, et elle produit une prédiction in-world
testable : **dans le même monde, avec le même protocole, des sujets d'origines différentes doivent
rendre des verdicts différents.** Sinon la propriété est celle du monde, et S6 ne se transporte pas —
résultat tout aussi informatif, qui BORNE S6.

--------------------------------------------------------------------------------------------------
LE BRAS QUI REND LE DESIGN HONNÊTE (amendement du 2026-09-08, trouvé AVANT tout run)
--------------------------------------------------------------------------------------------------
La règle de lecture d'origine disait « ≥ 2 sujets rendent des verdicts DIFFÉRENTS → le verdict est
propriété du sujet ». Sur 7 sujets cela fait **21 paires** : si `ablation_verdict` a la moindre
variabilité d'échantillonnage — et il en a, il lit une médiane sur K ères —, ce critère peut être
franchi alors que le sujet ne change RIEN. C'est le symétrique exact du défaut mesuré sur EVO-011
(bande fixe sur 24 cellules → 0,216 de fausse alarme), c.-à-d. la classe **E23**.

On ne SUPPOSE donc pas le bruit, on le MESURE : un bras de **RÉPLICATION DU MÊME SUJET** (le champion,
mesuré sous N graines de monde différentes, tout le reste identique) donne le nombre de verdicts
distincts produits par le seul bruit. La divergence inter-sujets doit le DÉPASSER. Sans ce bras, le
design ne peut rendre qu'une seule issue informative — classe E1.

Unité de réplication : l'**ère** pour chaque cellule (K ères appariées, c'est `ablation_verdict` qui
la consomme) ; le **sujet** pour le contraste. Sous bail `kuzu`.

Usage :  python -m tools.evo_runs.s2_subject_variance --smoke     # 1 sujet + 1 réplicat, chronométré
         python -m tools.evo_runs.s2_subject_variance             # plan complet
"""
from __future__ import annotations

import argparse
import json
import os
import sys

PREREG = "S2-SUBJECT-VARIANCE"

WORLD = "stoneage"                 # le seul monde où le plancher NOPERC est MESURÉ (24.0), pas importé
REGIME = {"num_agents": 12, "max_ticks": 200}      # le régime où `_floor_for` rend un plancher
K = 12
SEED = 2026
N_REPLICATS = 7                    # autant que de sujets : les deux bras se lisent à n égal
SIGMAS = (0.1, 0.3)

# Rôles — `pos` et `neg` sont les CONTRÔLES, les autres sont les SUJETS mesurés.
ROLE_SUJET, ROLE_REPLICAT, ROLE_POS, ROLE_NEG = "sujet", "replicat", "pos", "neg"


# ==================================================================================================
# 1. VERDICT — PUR : aucune simulation, aucun import lourd. C'est l'instrument, il se calibre.
# ==================================================================================================
def subject_variance_verdict(rows, floor_key="floor", median_key="intact_median",
                             body_ratio_max=2.0):
    """INSTRUMENT DE VERDICT. `rows` : une ligne par CELLULE mesurée, avec au moins
    {'name', 'role', 'verdict', 'ratio', 'intact_median', 'floor'}.

    Branches EXHAUSTIVES, dans l'ordre imposé — les contrôles AVANT toute lecture de la DV :

    * un contrôle câblé manque ou échoue      -> `INDETERMINE-INSTRUMENT`
    * moins de 2 sujets NON dégénérés          -> `INDETERMINE-DEGENERE`
    * aucun réplicat exploitable               -> `INDETERMINE-SANS-REFERENCE-DE-BRUIT`
    * `d_inter > d_intra`                      -> `VERDICT_IS_SUBJECT_BOUND`
    * `d_inter == 1` ET `d_intra == 1`         -> `VERDICT_IS_WORLD_BOUND`
    * sinon                                    -> `INDETERMINE-BRUIT`

    Une entrée VIDE ne rend JAMAIS un verdict de fond : elle rend `INDETERMINE-SANS-MESURE`. C'est la
    forme (a) du biais systématique du dépôt (donnée absente -> affirmation négative), et elle est
    refusée ici explicitement."""
    rows = list(rows or [])
    out = {"verdict": None, "d_inter": None, "d_intra": None, "n_sujets": 0, "n_replicats": 0,
           "degeneres": [], "controles": {}, "raisons": [], "corps": None}
    if not rows:
        out["verdict"] = "INDETERMINE-SANS-MESURE"
        out["raisons"].append("aucune cellule mesurée : une absence de mesure n'est pas un résultat")
        return out

    def _degenere(r):
        m, f = r.get(median_key), r.get(floor_key)
        return m is None or f is None or float(m) < float(f)

    # --- contrôles CÂBLÉS, avant toute lecture de la DV -------------------------------------------
    attendus = {ROLE_POS: "PERCEPTION_DEMANDED", ROLE_NEG: "PERCEPTION_DECOY"}
    for role, attendu in attendus.items():
        cell = next((r for r in rows if r.get("role") == role), None)
        if cell is None:
            out["controles"][role] = "ABSENT"
            out["raisons"].append(f"contrôle {role} ABSENT : un contrôle qu'on n'a pas lancé n'est "
                                  "pas un contrôle qui passe")
        else:
            ok = cell.get("verdict") == attendu
            out["controles"][role] = f"{cell.get('verdict')} ({'ok' if ok else 'ÉCHEC'})"
            if not ok:
                out["raisons"].append(f"contrôle {role} attendu {attendu}, obtenu {cell.get('verdict')}")
    if out["raisons"]:
        out["verdict"] = "INDETERMINE-INSTRUMENT"
        return out

    # --- domaine : un sujet sous SON plancher est INCONCLUSIVE_DEGENERATE, issue légitime ---------
    sujets = [r for r in rows if r.get("role") == ROLE_SUJET]
    replicats = [r for r in rows if r.get("role") == ROLE_REPLICAT]
    out["degeneres"] = sorted(r.get("name") for r in sujets + replicats if _degenere(r))
    sujets_ok = [r for r in sujets if not _degenere(r)]
    replicats_ok = [r for r in replicats if not _degenere(r)]
    out["n_sujets"], out["n_replicats"] = len(sujets_ok), len(replicats_ok)

    if len(sujets_ok) < 2:
        out["verdict"] = "INDETERMINE-DEGENERE"
        out["raisons"].append(f"{len(sujets_ok)} sujet(s) non dégénéré(s) : on ne contraste pas "
                              "moins de deux sujets")
        return out
    if not replicats_ok:
        out["verdict"] = "INDETERMINE-SANS-REFERENCE-DE-BRUIT"
        out["raisons"].append("aucun réplicat exploitable : sans référence de bruit, une divergence "
                              "inter-sujets ne prouve rien (classe E23)")
        return out

    # --- confond de CORPS, déclaré d'avance et RAPPORTÉ, jamais silencieux ------------------------
    med = [float(r[median_key]) for r in sujets_ok]
    ecart = max(med) / max(min(med), 1e-9)
    out["corps"] = {"ratio_max_min": ecart, "seuil": body_ratio_max,
                    "confondu": bool(ecart > body_ratio_max)}
    if out["corps"]["confondu"]:
        out["raisons"].append(f"survies INTACTES des sujets dans un rapport {ecart:.2f}x > "
                              f"{body_ratio_max}x : le contraste inter-sujets confond « repli » et "
                              "« corps » — rapporté, la lecture reste possible mais bornée")

    d_inter = len({r.get("verdict") for r in sujets_ok})
    d_intra = len({r.get("verdict") for r in replicats_ok})
    out["d_inter"], out["d_intra"] = d_inter, d_intra

    if d_inter > d_intra:
        out["verdict"] = "VERDICT_IS_SUBJECT_BOUND"
    elif d_inter == 1 and d_intra == 1:
        out["verdict"] = "VERDICT_IS_WORLD_BOUND"
    else:
        out["verdict"] = "INDETERMINE-BRUIT"
        out["raisons"].append(f"divergence inter-sujets ({d_inter}) non supérieure au bruit du MÊME "
                              f"sujet ({d_intra}) : l'instrument ne discrimine pas les sujets à ce n")
    return out


# ==================================================================================================
# 2. SUJETS — construits ici, jamais devinés ailleurs
# ==================================================================================================
def build_subjects(sigmas=SIGMAS, n_replicats=N_REPLICATS, seed=SEED):
    """[(nom, role, genome_fn, world_seed)] — `genome_fn` est différé : rien n'est construit tant que
    la cellule n'est pas lancée (une garde d'arguments doit pouvoir refuser sans rien charger)."""
    from tools.s2_demand import load_champion_genome

    def _champion():
        return load_champion_genome()

    def _soupe():
        from src.seed_ai.mutation import init_primordial_soup
        pop = init_primordial_soup(1, seed=seed)
        return pop[0] if isinstance(pop, (list, tuple)) else pop

    def _bruite(sigma):
        import numpy as np

        def f():
            g = load_champion_genome()
            rng = np.random.RandomState(90_000 + int(sigma * 1000))   # RNG DÉDIÉ (classe E5)
            g = _copie_genome(g)
            g.W = g.W + rng.normal(0.0, sigma, size=g.W.shape)
            return g
        return f

    plan = [("champion_hof", ROLE_SUJET, _champion, seed),
            ("soupe_fraiche", ROLE_SUJET, _soupe, seed)]
    plan += [(f"champion_bruit_{s}", ROLE_SUJET, _bruite(s), seed) for s in sigmas]
    plan += [(f"replicat_{i}", ROLE_REPLICAT, _champion, seed + 1000 + i) for i in range(n_replicats)]
    plan += [("reflexe_cable", ROLE_NEG, _reflexe_cable, seed),
             ("lecteur_cable", ROLE_POS, _lecteur_cable, seed)]
    return plan


def _copie_genome(g):
    import copy
    return copy.deepcopy(g)


def _reflexe_cable():
    """CONTRÔLE NÉGATIF : diagonale seule, aucune arête depuis l'observation -> il ne PEUT pas lire,
    donc l'ablation de perception ne doit rien lui faire (`PERCEPTION_DECOY`)."""
    import numpy as np

    from src.seed_ai.mutation import Genome
    from tools.s2_demand import load_champion_genome

    ref = load_champion_genome()
    W = np.zeros_like(ref.W)
    np.fill_diagonal(W, 10.0)
    return Genome(W, ref.num_inputs, ref.num_outputs)


def _lecteur_cable():
    """CONTRÔLE POSITIF : le réflexe, PLUS une arête observation -> action. Il DOIT rendre
    `PERCEPTION_DEMANDED`, sinon l'instrument est aveugle in-world et rien d'autre n'est lisible.
    C'est exactement ce qui manquait à WARM-002 et à S2-006 : un nul sans positif apparié."""
    import numpy as np

    from src.seed_ai.mutation import Genome
    from tools.s2_demand import load_champion_genome

    ref = load_champion_genome()
    W = np.zeros_like(ref.W)
    np.fill_diagonal(W, 10.0)
    out0 = W.shape[0] - ref.num_outputs
    for canal in range(min(5, ref.num_inputs)):        # les canaux de distance/type de l'obs
        W[canal, out0 + canal % 4] = 8.0
    return Genome(W, ref.num_inputs, ref.num_outputs)


# ==================================================================================================
# 3. RUNNER
# ==================================================================================================
def run_subject_variance(plan=None, map_fn=None, k=K, regime=None, world=WORLD, verbose=True):
    """Mesure chaque cellule du plan et rend (lignes, verdict). `map_fn` injectable = `run_ablation_map`.

    GARDE D'ARGUMENTS, EN TÊTE : un plan vide ou un régime dégénéré est une erreur d'APPEL, jamais un
    fait sur le monde. Le refus est instantané — aucun génome n'est construit."""
    regime = dict(regime or REGIME)
    plan = build_subjects() if plan is None else list(plan)
    if not plan or int(k) <= 0 or int(regime.get("num_agents", 0)) <= 0 \
            or int(regime.get("max_ticks", 0)) <= 0:
        raise ValueError(
            f"run_subject_variance : argument degenere (cellules={len(plan)}, K={k}, "
            f"regime={regime}) -- aucune mesure possible ; ne pas confondre avec une mesure nulle "
            "OBSERVEE.")
    if map_fn is None:
        from tools.s2_demand_ablation import run_ablation_map as map_fn

    lignes = []
    for nom, role, genome_fn, wseed in plan:
        m = map_fn(worlds=[world], seed=wseed, K=k, subject=genome_fn(), **regime)[world]
        lignes.append({"name": nom, "role": role, "world_seed": wseed, **m})
        if verbose:
            print(f"  {nom:22s} [{role:9s}] seed={wseed} -> {m['verdict']:22s} "
                  f"ratio={m['within_ratio']:.3f} intact={m['intact_median']:.1f} "
                  f"(plancher {m['floor']})")
    return lignes, subject_variance_verdict(lignes)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="1 sujet + 1 réplicat + les 2 contrôles")
    ap.add_argument("--k", type=int, default=K)
    ap.add_argument("--out", default=None, help="JSON de sortie ; `-` désactive")
    args = ap.parse_args(argv)

    from tools.experiment_preflight import assert_control_family, declare_design
    from tools.preregister import verify

    rule = verify(PREREG)
    print(f"[preregistration] {PREREG} : sceau VERIFIE")

    plan = build_subjects()
    if args.smoke:
        plan = [c for c in plan if c[1] in (ROLE_POS, ROLE_NEG)
                or c[0] in ("champion_hof", "replicat_0")]

    # GARDE E23 : les contrôles de PLANCHER (un par cellule) et les 2 contrôles câblés forment une
    # famille. Ce ne sont pas des tests d'hypothèse mais des gardes de DOMAINE : leur échec rend
    # INCONCLUSIVE_DEGENERATE pour CETTE cellule, issue légitime déclarée d'avance, et n'invalide pas
    # la lecture des autres. Cela se DÉCLARE ; le bruit de la DV, lui, est MESURÉ par le bras de
    # réplication, pas corrigé au doigt mouillé.
    famille = assert_control_family(
        cells=len(plan), method="none",
        reason="les contrôles sont des gardes de DOMAINE (le sujet est-il au-dessus du plancher "
               "MESURÉ du monde ?), pas des tests d'hypothèse : leur échec rend "
               "INCONCLUSIVE_DEGENERATE pour cette cellule seule, issue déclarée d'avance. La "
               "multiplicité qui COMPTE ici est celle du critère de lecture, et elle n'est pas "
               "corrigée mais MESURÉE par le bras de réplication du même sujet (d_intra).")
    design = declare_design(
        question=rule["question"], control_family=famille,
        replication_unit="ère pour chaque cellule (K appariées) ; SUJET pour le contraste",
        n_independent=len(plan),
        links={"sujet -> verdict du marqueur": "measured",
               "bruit de mesure -> divergence des verdicts": "measured"},
        cost_estimate=f"{len(plan)} cellules x 3 conditions x {args.k} eres x 12 agents x 200 ticks")
    print(f"[design] unite = {design['replication_unit']}")

    from tools.jobs.run import hold
    import time
    t0 = time.time()
    with hold("kuzu", owner="s2-subject-variance" + ("-smoke" if args.smoke else ""), ttl_s=3600):
        lignes, v = run_subject_variance(plan=plan, k=args.k)
    elapsed = time.time() - t0

    print(f"\n  VERDICT : {v['verdict']}  (d_inter={v['d_inter']} d_intra={v['d_intra']} "
          f"sujets={v['n_sujets']} replicats={v['n_replicats']})")
    for r in v["raisons"]:
        print(f"      - {r}")
    print(f"  controles : {v['controles']} | degeneres : {v['degeneres']} | corps : {v['corps']}")
    print(f"  COUT : {elapsed:.1f}s pour {len(plan)} cellules -> {elapsed / max(1, len(plan)):.1f} s/cellule")

    out = args.out
    if out != "-":
        out = out or os.path.join("results", "s2_subject_variance%s.json" % ("_smoke" if args.smoke else ""))
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump({"preregistration": PREREG, "design": design, "world": WORLD,
                       "regime": REGIME, "K": args.k, "elapsed_s": elapsed,
                       "verdict": v, "rows": lignes}, fh, indent=1, default=str)
        print(f"  persiste -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
