"""E34 (P2.132) — `E34-IDENTITY-CELL` : la cellule publiée `b_full` seed 2026 de P4.4 → P4.16, rejouée drapeau
ÉTEINT (témoin du CODE : même Σ|ΔW|, mêmes âges, même dose que le publié) puis drapeau ALLUMÉ (`slot_order_fix` :
chaque tranche W de la population torch garde SON corps après une résurrection). Une cellule = une SONDE, pas un
verdict : MATERIEL écrit un plan n = 12, NON_MATERIEL une note de robustesse bornée à cette cellule.

Pourquoi : le harnais immortel publié remet le mort en FIN de `e.agents` sans reconstruire la population
(`s2_credit_retention.py:107-113`, `world_1_stoneage.py:1060-1066`) ; après une mort en position p, les tranches
p..B-1 pilotent d'autres corps (tools/slot_identity.py). Les deux bras publient l'audit de l'invariant (lecture
seule) : la DOSE du défaut dans la cellule publiée est mesurée, pas supposée.

Règle SCELLÉE avant toute cellule : docs/preregistrations/E34-IDENTITY-CELL.json.

Usage :
  python -m tools.evo_runs.e34_identity_cell cellule --fix off|on [--seed 2026]   -> results/e34_identity_cell_<fix>.json
  python -m tools.evo_runs.e34_identity_cell lire [--temoin CHEMIN]                -> results/e34_identity_cell.json
  (env : E34_TICKS_LEARN=2000 E34_TICKS_TEST=200 E34_AGENTS=12 ; E34_SMOKE=1 -> 2 agents, 20/10 ticks, fichiers
   _smoke, règle non exigée : le smoke mesure le débit, il ne lit rien)
"""
import argparse
import json
import os
import platform
import sys
import time

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.evo_runs.s2_credit_retention import (  # noqa: E402
    DELTA_MIN, DOSE_MIN, REGIME as REGIME_P44, _finite, _git_provenance, _save, phase1_learn_immortal,
    phase2_survive_mortal)
from tools.evo_runs.s2_reward_ablation import _bassin_cohort, replication_check  # noqa: E402
from tools.grid_compare import cmp_grille  # noqa: E402

PREREG = "E34-IDENTITY-CELL"
SEED = 2026
ARMS = ("off", "on")
P416_RESULTS = "s2_credit_ablation_2.json"      # sous results/ : bras b_full (bande) et a_frozen (S_a), P4.16
BAND_ARM, FROZEN_ARM = "b_full", "a_frozen"
N_GRILLE = 2                                     # médiane de 12 âges entiers : un multiple de 0,5


def _p416(path=None):
    from src.paths import results_file
    p = path or str(results_file(P416_RESULTS))
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def published_band(path=None):
    """La dispersion ENTRE SEEDS du harnais publié : survie médiane de `b_full` sur les seeds de P4.16. Rend
    `{"min", "max", "values", "n"}` ; lève si un seed manque de survie finie (aucune bande n'est fabriquée)."""
    rows = _p416(path)["arms"][BAND_ARM]
    vals = []
    for s in sorted(rows):
        v = (rows[s].get("survival") or {}).get("survival_median")
        if not _finite(v):
            raise ValueError(f"published_band : seed {s} sans survie finie ({v!r}) -- aucune bande fabriquée")
        vals.append(float(v))
    if len(vals) < 12:
        raise ValueError(f"published_band : {len(vals)} seeds < 12 -- la dispersion publiée est incomplète")
    return {"min": min(vals), "max": max(vals), "values": vals, "n": len(vals), "source": P416_RESULTS,
            "arm": BAND_ARM}


def published_frozen(seed=SEED, path=None):
    """S_a du seed : le bassin GELÉ (P4.16, re-mesuré ; égal à P4.4). Lève s'il manque ou n'est pas fini."""
    v = ((_p416(path)["arms"][FROZEN_ARM].get(str(int(seed))) or {}).get("survival") or {}).get("survival_median")
    if not _finite(v):
        raise ValueError(f"published_frozen : seed {seed} sans S_a fini ({v!r})")
    return float(v)


def run_identity_cell(seed, fix, num_agents=12, ticks_learn=2000, ticks_test=200):
    """La cellule `b_full` du seed (bassin DAgger cloné ×num_agents, crédit publié), phase 1 immortelle avec
    `slot_order_fix = (fix == "on")` et l'audit de l'invariant TOUJOURS allumé (lecture seule), phase 2 mortelle à
    poids gelés. Garde EN TÊTE : un argument dégénéré lève avant tout monde."""
    if fix not in ARMS or int(num_agents) <= 0 or int(ticks_learn) <= 0 or int(ticks_test) <= 0:
        raise ValueError(f"run_identity_cell : argument dégénéré (fix={fix!r}, num_agents={num_agents}, "
                         f"ticks_learn={ticks_learn}, ticks_test={ticks_test}) -- aucune mesure possible")
    agents = _bassin_cohort(seed, num_agents)
    out = {"seed": int(seed), "arm": fix, "num_agents": int(num_agents), "ticks_learn": int(ticks_learn),
           "ticks_test": int(ticks_test), "lr": None}
    t0 = time.time()
    out["learning"] = phase1_learn_immortal(agents, seed, ticks_learn, slot_order_fix=(fix == "on"),
                                            identity_audit=True)
    out["survival"] = phase2_survive_mortal(agents, seed, ticks_test)
    out["elapsed_s"] = time.time() - t0
    return out


def witness_check(row, seed=SEED):
    """Le bras ÉTEINT reproduit-il AU BIT la cellule publiée (P4.4 `b_warm_credit`) : âges, dose TD, résurrections,
    paramètres (`replication_check`) ET Σ|ΔW| à égalité EXACTE ? `row["learning"]` peut porter `slot_identity`
    (audit en lecture seule) : il n'entre pas dans la comparaison."""
    rep = replication_check(row, seed)
    same_dw = rep["p44_dW_abs_sum"] is not None and rep["p44_dW_abs_sum"] == rep["measured_dW_abs_sum"]
    identical = bool(rep["identical"] and same_dw)
    reason = rep["reason"] if not rep["identical"] else ("bit-identique" if same_dw else "Σ|ΔW| différent")
    return dict(rep, identical=identical, reason=reason, same_dW_abs_sum=bool(same_dw))


def _needs(row, label):
    if row is None:
        return None
    lrn, srv = row.get("learning") or {}, row.get("survival") or {}
    ident = lrn.get("slot_identity")
    if ident is None:
        raise ValueError(f"{label} : pas d'audit `slot_identity` -- la dose du défaut ne serait pas mesurée")
    for k, v in (("survival_median", srv.get("survival_median")), ("td_updates", lrn.get("td_updates")),
                 ("slot_ticks_misaligned", ident.get("slot_ticks_misaligned")),
                 ("slot_ticks_total", ident.get("slot_ticks_total"))):
        if not _finite(v):
            raise ValueError(f"{label} : `{k}` absent ou non fini ({v!r}) -- aucun verdict n'est fabriqué")
    return float(srv["survival_median"]), int(lrn["td_updates"]), ident


def identity_cell_verdict(off, on, witness, band, s_frozen, dose_min=DOSE_MIN, delta_min=DELTA_MIN,
                          n_grille=N_GRILLE):
    """Lecture de la règle scellée E34-IDENTITY-CELL, branches dans l'ORDRE IMPOSÉ. `off`/`on` : lignes de
    `run_identity_cell` (None = cellule absente) ; `witness` : `witness_check` du bras éteint au lieu déclaré
    fidèle ; `band` : `published_band` ; `s_frozen` : `published_frozen`. Une valeur présente mais non finie LÈVE."""
    if not (_finite(band.get("min")) and _finite(band.get("max")) and int(band.get("n") or 0) >= 12):
        raise ValueError("identity_cell_verdict : bande publiée invalide -- aucune lecture")
    if not _finite(s_frozen):
        raise ValueError("identity_cell_verdict : S_a non fini -- aucune lecture")
    th = {"band_min": float(band["min"]), "band_max": float(band["max"]), "band_n": int(band["n"]),
          "dose_min": int(dose_min), "delta_min": float(delta_min), "n_grille": int(n_grille)}
    base = {"thresholds": th, "fausse_alarme_h0": 2.0 / (int(band["n"]) + 1)}
    a, b = _needs(off, "bras éteint"), _needs(on, "bras allumé")
    if a is None or b is None or witness is None:
        return dict(base, verdict="INCOMPLET", why="une cellule ou le témoin manque : reprise, aucune lecture")
    (s_off, td_off, id_off), (s_on, td_on, id_on) = a, b
    if not bool((on.get("learning") or {}).get("slot_identity", {}).get("slot_order_fix")) or \
            int(id_on["slot_ticks_misaligned"]) != 0:
        raise ValueError("identity_cell_verdict : le bras allumé n'a pas tenu l'invariant (ou n'est pas allumé) -- "
                         "défaut du harnais, aucune lecture")
    desc = {"S_off": s_off, "S_on": s_on, "dS": s_on - s_off, "S_a": float(s_frozen),
            "erosion_off": float(s_frozen) - s_off, "td_off": td_off, "td_on": td_on,
            "misaligned_off": int(id_off["slot_ticks_misaligned"]), "slot_ticks_off": int(id_off["slot_ticks_total"]),
            "positions_reordered_on": id_on.get("positions_reordered"),
            "resurrections_off": (off.get("learning") or {}).get("resurrections"),
            "resurrections_on": (on.get("learning") or {}).get("resurrections"),
            "dW_off": (off.get("learning") or {}).get("dW_abs_sum"),
            "dW_on": (on.get("learning") or {}).get("dW_abs_sum"), "witness_reason": witness.get("reason")}
    desc["part_erosion_levee"] = (desc["dS"] / desc["erosion_off"]) if desc["erosion_off"] > 0 else None
    out = dict(base, **desc)
    if not bool(witness.get("identical")):
        return dict(out, verdict="TEMOIN_ROMPU",
                    why=f"le bras éteint ne reproduit pas la cellule publiée ({witness.get('reason')}) : aucune lecture")
    if desc["misaligned_off"] == 0:
        return dict(out, verdict="SANS_OBJET",
                    why="aucun slot-tick désaligné dans la cellule publiée : le défaut n'a pas agi ici")
    if td_on < int(dose_min):
        return dict(out, verdict="INDETERMINE_DOSE", why=f"td du bras allumé {td_on} < {dose_min}")
    fort = not cmp_grille(abs(desc["dS"]), float(delta_min), 0.0, n_grille, sens=-1)       # |dS| >= delta_min
    if cmp_grille(s_on, th["band_max"], 0.0, n_grille, sens=+1):
        v = "MATERIEL_HAUSSE"
    elif cmp_grille(s_on, th["band_min"], 0.0, n_grille, sens=-1):
        v = "MATERIEL_BAISSE"
    else:
        return dict(out, verdict="NON_MATERIEL", fort=fort,
                    why=f"S_on {s_on} dans l'étendue publiée [{th['band_min']}, {th['band_max']}] : note de robustesse "
                        "bornée à cette cellule")
    return dict(out, verdict=v, fort=fort,
                why=f"S_on {s_on} hors de l'étendue publiée [{th['band_min']}, {th['band_max']}] : plan n = 12 et "
                    "bandeaux candidats ÉCRITS, pas posés" + (" ; |dS| >= DELTA_MIN" if fort else ""))


def _lieu():
    try:
        import torch
        tv = torch.__version__
    except Exception:                                # noqa: BLE001 — torch absent : dit, jamais deviné
        tv = None
    return {"platform": platform.platform(), "python": platform.python_version(), "torch": tv,
            "AGAGI_CPU_LIMIT": os.environ.get("AGAGI_CPU_LIMIT"), "AGAGI_IMAGE": os.environ.get("AGAGI_IMAGE")}


def main(argv=None):
    from src.paths import results_file
    from tools.experiment_preflight import declare_design
    from tools.jobs.run import hold
    from tools.preregister import provenance, verify

    ap = argparse.ArgumentParser(prog="python -m tools.evo_runs.e34_identity_cell")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cellule")
    c.add_argument("--fix", choices=ARMS, required=True)
    c.add_argument("--seed", type=int, default=SEED)
    r = sub.add_parser("lire")
    r.add_argument("--temoin", default=None, help="JSON du bras éteint servant de TÉMOIN du code (défaut : _off)")
    args = ap.parse_args(argv)
    smoke = os.environ.get("E34_SMOKE") == "1"
    suffix = "_smoke" if smoke else ""

    if args.cmd == "cellule":
        rule = None if smoke else verify(PREREG)                  # lève si la règle manque ou a été retouchée
        agents = 2 if smoke else int(os.environ.get("E34_AGENTS", "12"))
        ticks_learn = 20 if smoke else int(os.environ.get("E34_TICKS_LEARN", "2000"))
        ticks_test = 10 if smoke else int(os.environ.get("E34_TICKS_TEST", "200"))
        design = declare_design(
            question=(rule or {}).get("question", "smoke : débit de la cellule, aucune lecture"),
            replication_unit="seed (UNE cellule : une cohorte de %d clones du bassin, un monde par phase)" % agents,
            n_independent=1,
            links={"invariant_slot_corps": "measured", "dose_de_credit": "measured", "resurrections": "measured",
                   "survie_mortelle_poids_geles": "measured", "temoin_cellule_publiee": "measured"},
            cost_estimate=(rule or {}).get("budget_s"))
        with hold("kuzu", owner="e34-identity-cell-" + args.fix + suffix, ttl_s=7200.0):
            row = run_identity_cell(args.seed, args.fix, num_agents=agents, ticks_learn=ticks_learn,
                                    ticks_test=ticks_test)
        data = {"preregistration": PREREG, "design": design, "provenance": provenance(None if smoke else PREREG),
                "regime": dict(REGIME_P44, slot_order_fix=(args.fix == "on"), identity_audit=True, seed=args.seed,
                               agents=agents, ticks_learn=ticks_learn, ticks_test=ticks_test),
                "lieu": _lieu(), "smoke": smoke, "row": row,
                "witness": witness_check(row, args.seed) if (args.fix == "off" and not smoke) else None}
        if rule is not None:
            data["budget_s"] = rule["budget_s"]
            data["budget_depasse"] = bool(row["elapsed_s"] > float(rule["budget_s"]))
        out = str(results_file(f"e34_identity_cell_{args.fix}{suffix}.json"))
        _save(out, data)
        ident = row["learning"]["slot_identity"]
        print(f"[e34] {args.fix} seed {args.seed} : S = {row['survival']['survival_median']} ; "
              f"td {row['learning']['td_updates']} ; résurrections {row['learning']['resurrections']} ; "
              f"slot-ticks désalignés {ident['slot_ticks_misaligned']}/{ident['slot_ticks_total']} ; "
              f"Σ|ΔW| {row['learning']['dW_abs_sum']!r} ; {row['elapsed_s']:.1f}s -> {out}", flush=True)
        if data["witness"] is not None:
            print(f"[e34] témoin du code : {data['witness']['reason']}", flush=True)
        return 0

    rule = verify(PREREG)
    def _load(p):
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    off_p, on_p = (str(results_file(f"e34_identity_cell_{f}.json")) for f in ARMS)
    off = _load(off_p) if os.path.exists(off_p) else None
    on = _load(on_p) if os.path.exists(on_p) else None
    tem_p = args.temoin or off_p
    tem = _load(tem_p) if os.path.exists(tem_p) else None
    witness = (tem or {}).get("witness")
    verdict = identity_cell_verdict((off or {}).get("row"), (on or {}).get("row"), witness, published_band(),
                                    published_frozen(SEED))
    data = {"preregistration": PREREG, "seal_verified": True, "question": rule["question"],
            "provenance": provenance(PREREG), "cells": {"off": off_p if off else None, "on": on_p if on else None,
                                                        "temoin": tem_p if tem else None},
            "lieux": {"off": (off or {}).get("lieu"), "on": (on or {}).get("lieu"), "temoin": (tem or {}).get("lieu")},
            "verdict": verdict}
    out = str(results_file("e34_identity_cell.json"))
    _save(out, data)
    print(f"[e34] {verdict['verdict']} : {verdict['why']} -> {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
