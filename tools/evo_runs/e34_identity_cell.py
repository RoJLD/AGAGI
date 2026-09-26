"""E34 (P2.132) — `E34-IDENTITY-CELL` : la cellule publiée `b_full` seed 2026 de P4.4 → P4.16, rejouée drapeau
ÉTEINT (témoin du CODE : mêmes âges, même dose, même Σ|ΔW| que le publié), drapeau ALLUMÉ (`slot_order_fix` : chaque
tranche W de la population torch garde SON corps après une résurrection), et ONZE bras SHAM (drapeau éteint + k
tirages numpy au tick exact où le drapeau fait diverger sa trajectoire, k = 1..11). Une cellule = une SONDE, pas un
verdict : MATERIEL écrit un plan n = 12, NON_MATERIEL une note de robustesse bornée à cette cellule et à sa dose.

Pourquoi ce dispositif (revue E34 v1, 16 critiques confirmées) : S_on doit se lire contre des trajectoires du MÊME
seed, au MÊME lieu, sous le harnais PUBLIÉ — {S_off, S_sham_1..11}, douze valeurs échangeables sous H0 (« le drapeau
n'est qu'une trajectoire de plus ») — et non contre la dispersion ENTRE seeds, dont S_off occupait le bord. La dose du
défaut est le nombre de COMMUTATIONS (une tranche change de corps), compté dans tous les bras.

Règle SCELLÉE avant toute cellule : docs/preregistrations/E34-IDENTITY-CELL.json.

Usage (batcave, un seul lieu pour les 13 cellules) :
  python -m tools.evo_runs.e34_identity_cell tout [--workers 6]   -> results/e34_identity_cell/<bras>.json + agrégat
  python -m tools.evo_runs.e34_identity_cell cellule --bras off    -> une cellule (bail kuzu pris ici)
  python -m tools.evo_runs.e34_identity_cell lire                  -> results/e34_identity_cell.json (verdict)
  (env : E34_SMOKE=1 -> 2 agents, 20/10 ticks, répertoires _smoke, règle non exigée : le smoke mesure le débit)
"""
import argparse
import json
import math
import os
import platform
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.evo_runs.s2_credit_retention import (  # noqa: E402
    DELTA_MIN, REGIME as REGIME_P44, _finite, _save, phase1_learn_immortal, phase2_survive_mortal)
from tools.evo_runs.s2_reward_ablation import _bassin_cohort, replication_check  # noqa: E402
from tools.grid_compare import cmp_grille  # noqa: E402

PREREG = "E34-IDENTITY-CELL"
SEED = 2026
K_SHAMS = 11
SHAMS = tuple(f"sham_{k:02d}" for k in range(1, K_SHAMS + 1))
ARMS = ("off", "on") + SHAMS
WORKERS_MAX = 6                                  # comme P4.18 sur la batcave (plafond de contention)
OUT_DIR = "e34_identity_cell"                    # sous results/ : une cellule par fichier
P416_RESULTS = "s2_credit_ablation_2.json"       # sous results/ : bras b_full (dispersion ENTRE seeds, descriptive) et a_frozen
BAND_ARM, FROZEN_ARM = "b_full", "a_frozen"
N_GRILLE = 2                                     # médiane de 12 âges entiers : un multiple de 0,5


def arm_config(arm):
    """Le traitement d'un bras : `slot_order_fix` et `sham_draws`. Lève sur un bras inconnu."""
    if arm == "off":
        return {"slot_order_fix": False, "sham_draws": 0}
    if arm == "on":
        return {"slot_order_fix": True, "sham_draws": 0}
    if arm in SHAMS:
        return {"slot_order_fix": False, "sham_draws": int(arm.split("_")[1])}
    raise ValueError(f"arm_config : bras inconnu {arm!r}")


def _p416(path=None):
    from src.paths import results_file
    p = path or str(results_file(P416_RESULTS))
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def published_band(path=None):
    """DESCRIPTIF (ne décide rien) : l'étendue de la survie médiane de `b_full` ENTRE les seeds de P4.16. Lève si un
    seed manque de survie finie ou si moins de 12 seeds (aucune étendue n'est fabriquée)."""
    rows = _p416(path)["arms"][BAND_ARM]
    vals = []
    for s in sorted(rows):
        v = (rows[s].get("survival") or {}).get("survival_median")
        if not _finite(v):
            raise ValueError(f"published_band : seed {s} sans survie finie ({v!r}) -- aucune étendue fabriquée")
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


def lieu():
    """Le LIEU d'une cellule : plateforme, python, torch (version ET nombre de threads : la somme du chemin en dépend,
    mesuré par le témoin de lieu de P4.18), limite CPU et image du déport. Une valeur absente est publiée None."""
    try:
        import torch
        tv, th = torch.__version__, int(torch.get_num_threads())
    except Exception:                                # noqa: BLE001 — torch absent : dit, jamais deviné
        tv, th = None, None
    return {"platform": platform.platform(), "python": platform.python_version(), "torch": tv, "torch_threads": th,
            "AGAGI_CPU_LIMIT": os.environ.get("AGAGI_CPU_LIMIT"), "AGAGI_IMAGE": os.environ.get("AGAGI_IMAGE")}


def run_identity_cell(seed, arm, num_agents=12, ticks_learn=2000, ticks_test=200):
    """Une cellule `b_full` du seed (bassin DAgger cloné ×num_agents, crédit publié) sous le traitement du bras
    (`arm_config`), l'audit de l'invariant et des commutations TOUJOURS allumé (lecture seule), phase 2 mortelle à
    poids gelés. Garde EN TÊTE : un argument dégénéré ou un bras inconnu lève avant tout monde."""
    if arm not in ARMS or int(num_agents) <= 0 or int(ticks_learn) <= 0 or int(ticks_test) <= 0:
        raise ValueError(f"run_identity_cell : argument dégénéré (arm={arm!r}, num_agents={num_agents}, "
                         f"ticks_learn={ticks_learn}, ticks_test={ticks_test}) -- aucune mesure possible")
    cfg = arm_config(arm)
    agents = _bassin_cohort(seed, num_agents)
    out = {"seed": int(seed), "arm": arm, "num_agents": int(num_agents), "ticks_learn": int(ticks_learn),
           "ticks_test": int(ticks_test), "lr": None, "treatment": cfg}
    t0, c0 = time.time(), time.process_time()
    out["learning"] = phase1_learn_immortal(agents, seed, ticks_learn, slot_order_fix=cfg["slot_order_fix"],
                                            identity_audit=True, sham_draws=cfg["sham_draws"])
    out["survival"] = phase2_survive_mortal(agents, seed, ticks_test)
    out["elapsed_s"], out["cpu_s"] = time.time() - t0, time.process_time() - c0
    return out


def witness_check(row, seed=SEED):
    """Le bras ÉTEINT reproduit-il AU BIT la cellule publiée (P4.4 `b_warm_credit`) : âges, dose TD, résurrections,
    paramètres (`replication_check`) ET Σ|ΔW| à égalité EXACTE ? L'audit (`slot_identity`) n'entre pas dans la
    comparaison. Rend aussi âges et Σ|ΔW| MESURÉS : le verdict vérifie qu'ils sont ceux de la ligne qu'il lit."""
    rep = replication_check(row, seed)
    same_dw = rep["p44_dW_abs_sum"] is not None and rep["p44_dW_abs_sum"] == rep["measured_dW_abs_sum"]
    identical = bool(rep["identical"] and same_dw)
    reason = rep["reason"] if not rep["identical"] else ("bit-identique" if same_dw else "Σ|ΔW| différent")
    return dict(rep, identical=identical, reason=reason, same_dW_abs_sum=bool(same_dw))


def _needs(row, label):
    lrn, srv = row.get("learning") or {}, row.get("survival") or {}
    ident = lrn.get("slot_identity")
    if ident is None:
        raise ValueError(f"{label} : pas d'audit `slot_identity` -- la dose du défaut ne serait pas mesurée")
    for k, v in (("survival_median", srv.get("survival_median")), ("ticks_known", ident.get("ticks_known")),
                 ("ticks_unknown", ident.get("ticks_unknown")), ("slot_switches", ident.get("slot_switches")),
                 ("slot_ticks_misaligned", ident.get("slot_ticks_misaligned"))):
        if not _finite(v):
            raise ValueError(f"{label} : `{k}` absent ou non fini ({v!r}) -- aucun verdict n'est fabriqué")
    return float(srv["survival_median"]), ident


def identity_cell_verdict(off, on, shams, witness, s_frozen, ticks_learn, band_publiee=None, delta_min=DELTA_MIN,
                          n_shams=K_SHAMS, n_grille=N_GRILLE):
    """Lecture de la règle scellée E34-IDENTITY-CELL, branches dans l'ORDRE IMPOSÉ. `off`/`on` : lignes de
    `run_identity_cell` ; `shams` : la liste des n_shams lignes sham dans l'ordre k = 1..n (None = absente) ;
    `witness` : `witness_check` de la ligne `off` LUE ; `s_frozen` : `published_frozen` ; `ticks_learn` : la durée
    scellée de la phase 1 (l'audit doit la couvrir). Une valeur présente mais non finie LÈVE ; un harnais qui ment
    (drapeau sans remise en ordre, sham tiré ailleurs qu'au tick de divergence, témoin d'une autre exécution) LÈVE."""
    if not _finite(s_frozen):
        raise ValueError("identity_cell_verdict : S_a non fini -- aucune lecture")
    th = {"n_band": int(n_shams) + 1, "delta_min": float(delta_min), "n_grille": int(n_grille),
          "ticks_learn": int(ticks_learn)}
    base = {"thresholds": th, "fausse_alarme_h0": 2.0 / (int(n_shams) + 2), "band_publiee": band_publiee}
    shams = list(shams or [])
    rows = {"off": off, "on": on}
    rows.update({f"sham_{k:02d}": (shams[k - 1] if k <= len(shams) else None) for k in range(1, int(n_shams) + 1)})
    manquants = [a for a, r in rows.items() if r is None]
    if manquants or witness is None or len(shams) != int(n_shams):
        return dict(base, verdict="INCOMPLET", manquants=manquants + ([] if witness is not None else ["witness"]),
                    why="une cellule ou le témoin manque : reprise, aucune lecture")
    lus = {a: _needs(r, a) for a, r in rows.items()}
    aveugles = [a for a, (_, ident) in lus.items()
                if int(ident["ticks_known"]) != int(ticks_learn) or int(ident["ticks_unknown"]) != 0]
    if aveugles:
        return dict(base, verdict="INCOMPLET", audit_incomplet=aveugles,
                    why="audit de l'invariant incomplet (ticks non appariés) : une dose non mesurée n'est pas une "
                        "dose nulle, aucune lecture")
    lieux = {json.dumps(r.get("lieu"), sort_keys=True) for r in rows.values()}
    if len(lieux) != 1 or rows["off"].get("lieu") is None:
        return dict(base, verdict="LIEU_MIXTE", lieux=sorted(lieux),
                    why="les cellules ne viennent pas d'UN seul lieu (plateforme, torch, threads) : aucune lecture")
    if (list(witness.get("measured_ages") or []) != list(off["survival"].get("ages") or [])
            or witness.get("measured_dW_abs_sum") != off["learning"].get("dW_abs_sum")):
        raise ValueError("identity_cell_verdict : le témoin ne certifie pas la ligne éteinte lue (âges ou Σ|ΔW| "
                         "différents) -- témoin d'une autre exécution")
    s_off, id_off = lus["off"]
    s_on, id_on = lus["on"]
    B = int(off.get("num_agents") or 0)
    desc = {"S_off": s_off, "S_on": s_on, "S_shams": {a: lus[a][0] for a in rows if a.startswith("sham_")},
            "S_a": float(s_frozen), "erosion_off": float(s_frozen) - s_off, "dS": s_on - s_off,
            "switches_off": int(id_off["slot_switches"]), "first_switch_tick_off": id_off.get("first_switch_tick"),
            "fraction_transitions_td_a_cheval": (int(id_off["slot_switches"]) / (B * (int(ticks_learn) - 1))
                                                 if B > 0 and int(ticks_learn) > 1 else None),
            "positions_reordered_on": id_on.get("positions_reordered"),
            "resurrections": {a: (r.get("learning") or {}).get("resurrections") for a, r in rows.items()},
            "dW": {a: (r.get("learning") or {}).get("dW_abs_sum") for a, r in rows.items()},
            "witness_reason": witness.get("reason"), "lieu": rows["off"].get("lieu")}
    desc["part_erosion_levee"] = (desc["dS"] / desc["erosion_off"]) if desc["erosion_off"] > 0 else None
    desc["fort"] = not cmp_grille(abs(desc["dS"]), float(delta_min), 0.0, n_grille, sens=-1)   # descriptif
    out = dict(base, **desc)
    if not bool(witness.get("identical")):
        return dict(out, verdict="TEMOIN_ROMPU",
                    why=f"le bras éteint ne reproduit pas la cellule publiée ({witness.get('reason')}) : aucune lecture")
    if desc["switches_off"] == 0:
        return dict(out, verdict="SANS_OBJET",
                    why="aucune commutation dans la cellule publiée : le défaut n'a pas agi ici, elle ne tranche rien")
    t1 = id_off.get("first_switch_tick")
    if not (bool(id_on.get("slot_order_fix")) and int(id_on["slot_switches"]) == 0
            and int(id_on["slot_ticks_misaligned"]) == 0 and id_on.get("first_reorder_tick") == t1):
        raise ValueError("identity_cell_verdict : le bras allumé n'a pas tenu l'invariant ou n'a pas divergé au tick "
                         f"de la première commutation ({t1}) -- défaut du harnais, aucune lecture")
    for k in range(1, int(n_shams) + 1):
        ident = lus[f"sham_{k:02d}"][1]
        if bool(ident.get("slot_order_fix")) or int(ident.get("sham_draws") or 0) != k or ident.get("sham_tick") != t1:
            raise ValueError(f"identity_cell_verdict : sham_{k:02d} n'a pas tiré {k} valeur(s) au tick {t1} drapeau "
                             "éteint -- défaut du harnais, aucune lecture")
    band = [s_off] + [desc["S_shams"][f"sham_{k:02d}"] for k in range(1, int(n_shams) + 1)]
    out.update(band_min=min(band), band_max=max(band), band_values=band)
    if cmp_grille(s_on, out["band_max"], 0.0, n_grille, sens=+1):
        v = "MATERIEL_HAUSSE"
    elif cmp_grille(s_on, out["band_min"], 0.0, n_grille, sens=-1):
        v = "MATERIEL_BAISSE"
    else:
        return dict(out, verdict="NON_MATERIEL",
                    why=f"S_on {s_on} dans la bande [{out['band_min']}, {out['band_max']}] des trajectoires du même seed "
                        f"(éteint + {n_shams} shams) : aucun effet de l'ampleur de la variation entre trajectoires sur "
                        f"CETTE cellule, à SA dose ({desc['switches_off']} commutations)")
    return dict(out, verdict=v,
                why=f"S_on {s_on} hors de la bande [{out['band_min']}, {out['band_max']}] des trajectoires du même seed : "
                    "plan n = 12 et bandeaux candidats ÉCRITS, pas posés")


def _cells_dir(smoke=False):
    from src.paths import results_file
    return str(results_file(OUT_DIR + ("_smoke" if smoke else "")))


def _cell_path(arm, smoke=False):
    return os.path.join(_cells_dir(smoke), f"{arm}.json")


def _ticks(smoke):
    if smoke:
        return 2, 20, 10
    return (int(os.environ.get("E34_AGENTS", "12")), int(os.environ.get("E34_TICKS_LEARN", "2000")),
            int(os.environ.get("E34_TICKS_TEST", "200")))


def _cell_record(row, rule, smoke):
    from tools.preregister import provenance
    from tools.evo_runs.s2_bassin_fragility import _charge
    rec = {"preregistration": PREREG, "provenance": provenance(None if smoke else PREREG), "smoke": smoke,
           "regime": dict(REGIME_P44, seed=row["seed"], agents=row["num_agents"], ticks_learn=row["ticks_learn"],
                          ticks_test=row["ticks_test"], treatment=row["treatment"], identity_audit=True,
                          lr_override=None, lr_effective_per_agent=(row["learning"] or {}).get("lr_effective_per_agent"),
                          lr_note="pas identique dans tous les bras : défaut du learner, aucun override"),
           "lieu": row.get("lieu"), "charge_fin": _charge(), "row": row}
    if rule is not None:
        rec["budget_s"] = rule["budget_s"]
    return rec


def _tache(seed, arm, agents, ticks_learn, ticks_test):
    """Processus OUVRIER (kuzu neutralisé par l'initialiseur) : une cellule, avec son lieu."""
    row = run_identity_cell(seed, arm, num_agents=agents, ticks_learn=ticks_learn, ticks_test=ticks_test)
    row["lieu"] = lieu()
    return row


def _lire(smoke=False):
    from src.paths import results_file
    from tools.preregister import provenance, verify
    rule = verify(PREREG)
    agents, ticks_learn, _ = _ticks(smoke)

    def _load(arm):
        p = _cell_path(arm, smoke)
        return json.load(open(p, encoding="utf-8"))["row"] if os.path.exists(p) else None
    rows = {a: _load(a) for a in ARMS}
    witness = witness_check(rows["off"], SEED) if rows["off"] is not None else None
    verdict = identity_cell_verdict(rows["off"], rows["on"], [rows[a] for a in SHAMS], witness,
                                    published_frozen(SEED), ticks_learn, band_publiee=published_band())
    data = {"preregistration": PREREG, "seal_verified": True, "question": rule["question"],
            "provenance": provenance(PREREG), "cells_dir": os.path.relpath(_cells_dir(smoke), _ROOT),
            "cells_present": [a for a in ARMS if rows[a] is not None], "witness": witness, "verdict": verdict}
    out = str(results_file("e34_identity_cell" + ("_smoke" if smoke else "") + ".json"))
    _save(out, data)
    print(f"[e34] {verdict['verdict']} : {verdict['why']} -> {out}", flush=True)
    return data


def main(argv=None):
    from tools.experiment_preflight import declare_design
    from tools.jobs.run import hold
    from tools.preregister import verify

    ap = argparse.ArgumentParser(prog="python -m tools.evo_runs.e34_identity_cell")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cellule")
    c.add_argument("--bras", choices=ARMS, required=True)
    t = sub.add_parser("tout")
    t.add_argument("--workers", type=int, default=WORKERS_MAX)
    sub.add_parser("lire")
    args = ap.parse_args(argv)
    smoke = os.environ.get("E34_SMOKE") == "1"
    if args.cmd == "lire":
        _lire(smoke)
        return 0
    if args.cmd == "tout" and not 1 <= int(args.workers) <= WORKERS_MAX:
        raise ValueError(f"tout : --workers {args.workers} hors [1, {WORKERS_MAX}] -- plafond de contention")
    rule = None if smoke else verify(PREREG)                      # lève si la règle manque ou a été retouchée
    agents, ticks_learn, ticks_test = _ticks(smoke)
    design = declare_design(
        question=(rule or {}).get("question", "smoke : débit de la sonde, aucune lecture"),
        replication_unit="seed (UNE cellule de %d clones du bassin, 13 traitements sur le MÊME seed et le MÊME lieu)"
                         % agents,
        n_independent=1,
        links={"invariant_slot_corps": "measured", "commutations": "measured", "bande_sham_meme_seed": "measured",
               "survie_mortelle_poids_geles": "measured", "temoin_cellule_publiee": "measured"},
        cost_estimate=(rule or {}).get("budget_s"))
    os.makedirs(_cells_dir(smoke), exist_ok=True)
    owner = "e34-identity-cell" + ("-smoke" if smoke else "")
    if args.cmd == "cellule":
        with hold("kuzu", owner=owner, ttl_s=7200.0):
            row = run_identity_cell(SEED, args.bras, num_agents=agents, ticks_learn=ticks_learn, ticks_test=ticks_test)
        row["lieu"] = lieu()
        _save(_cell_path(args.bras, smoke), dict(_cell_record(row, rule, smoke), design=design))
        print(f"[e34] {args.bras} : S = {row['survival']['survival_median']} ; commutations "
              f"{row['learning']['slot_identity']['slot_switches']} ; {row['elapsed_s']:.1f}s", flush=True)
        return 0

    from concurrent.futures import ProcessPoolExecutor, as_completed
    from tools.cost_guard import project_cost
    from tools.evo_runs.s2_bassin_fragility import _charge, _neutraliser_kuzu
    budget_s = float((rule or {}).get("budget_s") or 3600.0)
    execution = {"workers": int(args.workers), "charge_depart": _charge(), "kuzu": "neutralise dans chaque ouvrier"}
    print(f"[e34] tout : 13 cellules, {args.workers} ouvriers, charge au départ {execution['charge_depart']}",
          flush=True)
    t_start = time.time()
    with hold("kuzu", owner=owner, ttl_s=max(3600.0, budget_s * 2)), \
            ProcessPoolExecutor(max_workers=int(args.workers), initializer=_neutraliser_kuzu) as ex:
        futs = {ex.submit(_tache, SEED, a, agents, ticks_learn, ticks_test): a for a in ARMS}
        premiere = True
        for f in as_completed(futs):
            arm = futs[f]
            row = f.result()
            _save(_cell_path(arm, smoke), dict(_cell_record(row, rule, smoke), design=design, execution=execution))
            print(f"[e34] {arm} : S = {row['survival']['survival_median']} ; commutations "
                  f"{row['learning']['slot_identity']['slot_switches']} ; {row['elapsed_s']:.1f}s", flush=True)
            if premiere:                                          # garde E13 : projection sur la 1re cellule mesurée
                premiere = False
                vagues = math.ceil(len(ARMS) / int(args.workers))
                try:
                    project_cost(row["elapsed_s"], n_units=vagues, budget_s=budget_s,
                                 label="e34-identity-cell (unité = une cellule, par vague d'ouvriers)")
                except Exception:
                    for g in futs:
                        g.cancel()
                    raise
            if arm == "off" and not smoke and not witness_check(row, SEED)["identical"]:
                for g in futs:
                    g.cancel()
                print("[e34] TÉMOIN ROMPU : cellules restantes annulées", flush=True)
                break
    print(f"[e34] tout : {time.time() - t_start:.0f}s de mur", flush=True)
    if not smoke:
        _lire(smoke)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
