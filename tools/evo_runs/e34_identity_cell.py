"""E34 (P2.132) — `E34-IDENTITY-CELL` : la cellule publiée `b_full` seed 2026 de P4.4 → P4.16 sous QUINZE traitements,
au même seed, au même lieu, au même commit : drapeau ÉTEINT (témoin du CODE : mêmes âges, même dose, même Σ|ΔW| que le
publié), drapeau ALLUMÉ (`slot_order_fix` : chaque tranche W garde SON corps), DOUZE shams de PERMUTATION (à chaque tick
où la recharge change l'ordre, les corps sont permutés par un RNG PRIVÉ, sans réparer l'identité) et un CONTRÔLE POSITIF
(crédit coupé au premier de ces ticks, t1). Une cellule = une SONDE : MATERIEL écrit un plan n = 12, NON_MATERIEL une
note bornée à cette cellule et à sa dose, NON_TRANCHE dit que l'instrument ne voit pas un effet fort à ce t1.

Pourquoi ce dispositif (revues E34 v1 et v2) : sous H0 (« l'identité ne compte pas »), le correctif n'est qu'UNE
permutation des corps aux ticks où la recharge change l'ordre — il est échangeable par construction avec les douze
permutations témoins, qui touchent la même chose que lui (ordre de service, flux aléatoire du monde par position) sans
réparer l'identité. La dose du défaut est le nombre de COMMUTATIONS (une tranche change de corps).

Règle SCELLÉE avant toute cellule : docs/preregistrations/E34-IDENTITY-CELL.json.

Usage (batcave, un seul lieu, un seul commit, répertoire de cellules VIDE au départ) :
  python -m tools.evo_runs.e34_identity_cell tout [--workers 6]   -> results/e34_identity_cell/<bras>.json + agrégat
      (phase A : la cellule éteinte SEULE, témoin + unité de coût ; phase B : les 14 autres, plafond PENDANT)
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
    DELTA_MIN, FLOOR, REGIME as REGIME_P44, _finite, _save, phase1_learn_immortal, phase2_survive_mortal)
from tools.evo_runs.s2_reward_ablation import _bassin_cohort, replication_check  # noqa: E402
from tools.grid_compare import cmp_grille  # noqa: E402

PREREG = "E34-IDENTITY-CELL"
SEED = 2026
K_PERMS = 12
PERMS = tuple(f"perm_{k:02d}" for k in range(1, K_PERMS + 1))
ARMS = ("off", "on", "pos") + PERMS
WORKERS_MAX = 6                                  # comme P4.18 sur la batcave (plafond de contention)
OUT_DIR = "e34_identity_cell"                    # sous results/ : une cellule par fichier
P416_RESULTS = "s2_credit_ablation_2.json"       # sous results/ : dispersion ENTRE seeds (descriptive) et S_a
BAND_ARM, FROZEN_ARM = "b_full", "a_frozen"
N_GRILLE = 2                                     # médiane de 12 âges entiers : un multiple de 0,5


def arm_config(arm):
    """Le traitement d'un bras : `slot_order_fix`, `sham_perm`, `cut_credit_at_t1`. Lève sur un bras inconnu."""
    base = {"slot_order_fix": False, "sham_perm": 0, "cut_credit_at_t1": False}
    if arm == "off":
        return base
    if arm == "on":
        return dict(base, slot_order_fix=True)
    if arm == "pos":
        return dict(base, cut_credit_at_t1=True)
    if arm in PERMS:
        return dict(base, sham_perm=int(arm.split("_")[1]))
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
    out["learning"] = phase1_learn_immortal(agents, seed, ticks_learn, identity_audit=True, **cfg)
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
                 ("slot_ticks_misaligned", ident.get("slot_ticks_misaligned")),
                 ("order_changes", ident.get("order_changes")), ("td_updates", lrn.get("td_updates")),
                 ("dW_abs_sum", lrn.get("dW_abs_sum"))):
        if not _finite(v):
            raise ValueError(f"{label} : `{k}` absent ou non fini ({v!r}) -- aucun verdict n'est fabriqué")
    return float(srv["survival_median"]), ident


def _fausse_alarme_ex_aequo(on_value, band):
    """Sous H0, S_on est une place au hasard parmi les n + 1 valeurs {S_on} ∪ bande : P(elle est STRICTEMENT seule au
    maximum ou au minimum), calculée sur les valeurs OBSERVÉES (les ex-aequo la réduisent ; 2/(n+1) sans ex-aequo)."""
    vals = list(band) + [on_value]
    n = len(vals)
    hi, lo = max(vals), min(vals)
    return ((1.0 if vals.count(hi) == 1 else 0.0) + (1.0 if vals.count(lo) == 1 and lo != hi else 0.0)) / n


def identity_cell_verdict(rows, witness, s_frozen, ticks_learn, band_publiee=None, delta_min=DELTA_MIN,
                          floor=FLOOR, n_grille=N_GRILLE):
    """Lecture de la règle scellée E34-IDENTITY-CELL v3, branches dans l'ORDRE IMPOSÉ. `rows` : {bras: ligne de
    `run_identity_cell` (avec `lieu` et `provenance`) ou None} sur les 15 bras ; `witness` : `witness_check` de la ligne
    `off` LUE ; `s_frozen` : `published_frozen` ; `ticks_learn` : la durée scellée de la phase 1. Une valeur présente
    mais non finie LÈVE ; un harnais qui ment (drapeau qui commute ou diverge ailleurs qu'à t1, sham ou coupe hors de
    t1, coupe sans effet sur la dose, témoin d'une autre exécution) LÈVE."""
    if not _finite(s_frozen):
        raise ValueError("identity_cell_verdict : S_a non fini -- aucune lecture")
    th = {"n_band": K_PERMS, "delta_min": float(delta_min), "floor": float(floor), "n_grille": int(n_grille),
          "ticks_learn": int(ticks_learn)}
    base = {"thresholds": th, "fausse_alarme_h0_borne": 2.0 / (K_PERMS + 1), "band_publiee": band_publiee}
    rows = {a: rows.get(a) for a in ARMS}
    off = rows["off"]
    if off is None or witness is None:
        return dict(base, verdict="INCOMPLET", manquants=["off"] if off is None else ["witness"],
                    why="la cellule éteinte ou son témoin manque : aucune lecture")
    if (list(witness.get("measured_ages") or []) != list((off.get("survival") or {}).get("ages") or [])
            or witness.get("measured_dW_abs_sum") != (off.get("learning") or {}).get("dW_abs_sum")):
        raise ValueError("identity_cell_verdict : le témoin ne certifie pas la ligne éteinte lue (âges ou Σ|ΔW| "
                         "différents) -- témoin d'une autre exécution")
    if not bool(witness.get("identical")):
        return dict(base, verdict="TEMOIN_ROMPU", witness_reason=witness.get("reason"),
                    why=f"le bras éteint ne reproduit pas la cellule publiée ({witness.get('reason')}) : aucune "
                        "lecture ; défaut au registre, le dispositif ne se relance pas tel quel")
    manquants = [a for a, r in rows.items() if r is None]
    if manquants:
        return dict(base, verdict="INCOMPLET", manquants=manquants, why="une cellule manque : reprise, aucune lecture")
    lus = {a: _needs(r, a) for a, r in rows.items()}
    aveugles = [a for a, (_, ident) in lus.items()
                if int(ident["ticks_known"]) != int(ticks_learn) or int(ident["ticks_unknown"]) != 0]
    if aveugles:
        return dict(base, verdict="INCOMPLET", audit_incomplet=aveugles,
                    why="audit de l'invariant incomplet (ticks non appariés) : une dose non mesurée n'est pas une "
                        "dose nulle, aucune lecture")
    provs = {(((r.get("provenance") or {}).get("git_sha")), bool((r.get("provenance") or {}).get("dirty")))
             for r in rows.values()}
    if len(provs) != 1 or next(iter(provs))[0] is None or next(iter(provs))[1]:
        return dict(base, verdict="PROVENANCE_MIXTE", provenances=sorted(str(p) for p in provs),
                    why="les cellules ne viennent pas d'UN seul commit propre : aucune lecture")
    lieux = {json.dumps(r.get("lieu"), sort_keys=True) for r in rows.values()}
    if len(lieux) != 1 or off.get("lieu") is None:
        return dict(base, verdict="LIEU_MIXTE", lieux=sorted(lieux),
                    why="les cellules ne viennent pas d'UN seul lieu (plateforme, torch, threads) : aucune lecture")
    s_off, id_off = lus["off"]
    s_on, id_on = lus["on"]
    s_pos, id_pos = lus["pos"]
    B = int(off.get("num_agents") or 0)
    t1 = id_off.get("first_order_change_tick")
    ep_off = (off.get("learning") or {}).get("episode_updates")
    perms = {a: lus[a][0] for a in PERMS}
    dose = {a: {"slot_switches": int(ident["slot_switches"]), "order_changes": int(ident["order_changes"]),
                "td_updates": (rows[a].get("learning") or {}).get("td_updates"),
                "episode_updates": (rows[a].get("learning") or {}).get("episode_updates"),
                "resurrections": (rows[a].get("learning") or {}).get("resurrections"),
                "dW_abs_sum": (rows[a].get("learning") or {}).get("dW_abs_sum")} for a, (_, ident) in lus.items()}
    erosion = float(s_frozen) - s_off
    desc = {"S_off": s_off, "S_on": s_on, "S_pos": s_pos, "S_perms": perms, "S_a": float(s_frozen),
            "erosion_off": erosion, "dS": s_on - s_off, "t1": t1,
            "levier_apres_t1": ((int(ticks_learn) - int(t1)) / int(ticks_learn)) if t1 is not None else None,
            "sous_plancher_off": bool(s_off < float(floor)), "dose": dose,
            "switches_off": int(id_off["slot_switches"]), "positions_reordered_on": id_on.get("positions_reordered"),
            "fraction_transitions_td_a_cheval": (int(id_off["slot_switches"]) / (B * (int(ticks_learn) - 1))
                                                 if B > 0 and int(ticks_learn) > 1 else None),
            "fraction_fenetres_episodiques_a_cheval_max": (int(id_off["slot_switches"]) / (B * int(ep_off))
                                                          if B > 0 and _finite(ep_off) and int(ep_off) > 0 else None),
            "witness_reason": witness.get("reason"), "lieu": off.get("lieu"),
            "git_sha": (off.get("provenance") or {}).get("git_sha")}
    desc["part_erosion_levee"] = (desc["dS"] / erosion) if erosion > 0 else None
    desc["fort"] = not cmp_grille(abs(desc["dS"]), float(delta_min), 0.0, n_grille, sens=-1)   # descriptif
    desc["perms_dS"] = {a: v - s_off for a, v in perms.items()}
    desc["perms_part_erosion"] = ({a: (v - s_off) / erosion for a, v in perms.items()} if erosion > 0 else None)
    desc["perms_fort"] = sum(1 for v in perms.values()
                             if not cmp_grille(abs(v - s_off), float(delta_min), 0.0, n_grille, sens=-1))
    out = dict(base, **desc)
    if desc["switches_off"] == 0:
        return dict(out, verdict="SANS_OBJET",
                    why="aucune commutation dans la cellule publiée : le défaut n'a pas agi ici, elle ne tranche rien")
    if not (bool(id_on.get("slot_order_fix")) and int(id_on["slot_switches"]) == 0
            and int(id_on["slot_ticks_misaligned"]) == 0 and id_on.get("first_reorder_tick") == t1):
        raise ValueError("identity_cell_verdict : le bras allumé a commuté, gardé un désalignement, ou fait sa PREMIÈRE "
                         f"remise en ordre ailleurs qu'à t1 ({t1}) -- défaut du harnais, aucune lecture")
    for k in range(1, K_PERMS + 1):
        ident = lus[f"perm_{k:02d}"][1]
        if bool(ident.get("slot_order_fix")) or int(ident.get("sham_perm") or 0) != k or ident.get("first_perm_tick") != t1:
            raise ValueError(f"identity_cell_verdict : perm_{k:02d} n'a pas fait sa PREMIÈRE permutation (RNG privé {k}) "
                             f"à t1 ({t1}) drapeau éteint -- défaut du harnais, aucune lecture")
    if id_pos.get("credit_cut_tick") != t1 or not (dose["pos"]["td_updates"] < dose["off"]["td_updates"]):
        raise ValueError(f"identity_cell_verdict : le contrôle positif n'a pas coupé le crédit à t1 ({t1}), ou sa dose TD "
                         "n'a pas baissé -- défaut du harnais, aucune lecture")
    band = [perms[a] for a in PERMS]
    dw_distincts = len({dose[a]["dW_abs_sum"] for a in PERMS})
    out.update(band_min=min(band), band_max=max(band), band_values=band, band_dW_distincts=dw_distincts,
               fausse_alarme_h0_ex_aequo=_fausse_alarme_ex_aequo(s_on, band))
    if dw_distincts < 2:
        return dict(out, verdict="BANDE_INERTE",
                    why="les douze permutations témoins n'ont pas divergé (Σ|ΔW| tous égaux) : aucune bande, aucune lecture")
    if cmp_grille(s_on, out["band_max"], 0.0, n_grille, sens=+1):
        return dict(out, verdict="MATERIEL_HAUSSE",
                    why=f"S_on {s_on} au-dessus des douze permutations [{out['band_min']}, {out['band_max']}] : plan n = 12 "
                        "et bandeaux candidats ÉCRITS, pas posés ; l'ordre de service reste une LIMITE écrite")
    if cmp_grille(s_on, out["band_min"], 0.0, n_grille, sens=-1):
        return dict(out, verdict="MATERIEL_BAISSE",
                    why=f"S_on {s_on} au-dessous des douze permutations [{out['band_min']}, {out['band_max']}] : plan n = 12 "
                        "et bandeaux candidats ÉCRITS, pas posés ; l'ordre de service reste une LIMITE écrite")
    if cmp_grille(s_pos, out["band_max"], 0.0, n_grille, sens=+1):
        return dict(out, verdict="NON_MATERIEL",
                    why=f"S_on {s_on} dans les douze permutations [{out['band_min']}, {out['band_max']}] alors que le contrôle "
                        f"positif en sort (S_pos {s_pos}) : aucun effet de l'ampleur de la variation entre permutations sur "
                        f"CETTE cellule, à SA dose (défaut : {desc['switches_off']} commutations ; drapeau : "
                        f"{desc['positions_reordered_on']} positions remises)")
    return dict(out, verdict="NON_TRANCHE",
                why=f"S_on {s_on} dans la bande, mais le contrôle positif n'en sort pas par le haut (S_pos {s_pos}) : "
                    f"l'instrument ne voit pas un effet fort à t1 = {t1} ; aucune note de robustesse")


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


def _tache(seed, arm, agents, ticks_learn, ticks_test, smoke):
    """Processus OUVRIER (kuzu neutralisé par l'initialiseur) : une cellule, avec son lieu, sa provenance et la charge
    machine au DÉBUT et à la FIN de la cellule (revue v2, P10.b)."""
    from tools.evo_runs.s2_bassin_fragility import _charge
    from tools.preregister import provenance
    debut = _charge()
    row = run_identity_cell(seed, arm, num_agents=agents, ticks_learn=ticks_learn, ticks_test=ticks_test)
    row.update(lieu=lieu(), provenance=provenance(None if smoke else PREREG), charge_debut=debut, charge_fin=_charge())
    return row


def _regime(row):
    return dict(REGIME_P44, seed=row["seed"], agents=row["num_agents"], ticks_learn=row["ticks_learn"],
                ticks_test=row["ticks_test"], treatment=row["treatment"], identity_audit=True, lr_override=None,
                lr_effective_per_agent=(row["learning"] or {}).get("lr_effective_per_agent"),
                lr_note="pas identique dans tous les bras : défaut du learner, aucun override")


def _save_cell(row, rule, smoke, extra=None):
    rec = {"preregistration": PREREG, "smoke": smoke, "regime": _regime(row), "row": row}
    if rule is not None:
        rec["budget_s"] = rule["budget_s"]
    rec.update(extra or {})
    _save(_cell_path(row["arm"], smoke), rec)


def _lire(smoke=False):
    from src.paths import results_file
    from tools.preregister import provenance, verify
    rule = verify(PREREG)
    agents, ticks_learn, ticks_test = _ticks(smoke)

    def _load(arm):
        p = _cell_path(arm, smoke)
        return json.load(open(p, encoding="utf-8"))["row"] if os.path.exists(p) else None
    rows = {a: _load(a) for a in ARMS}
    witness = witness_check(rows["off"], SEED) if rows["off"] is not None else None
    verdict = identity_cell_verdict(rows, witness, published_frozen(SEED), ticks_learn, band_publiee=published_band())
    # Les fichiers de cellule vivent sous results/<OUT_DIR>/, IGNORÉ par git (.gitignore : results/* sauf results/*.json) :
    # c'est ce qui garde l'arbre propre pendant le run (provenance « dirty » de chaque cellule). L'ÉVIDENCE suivie est
    # CET agrégat : il embarque les quinze lignes, avec leur lieu, leur provenance et leur charge.
    data = {"preregistration": PREREG, "seal_verified": True, "question": rule["question"],
            "provenance": provenance(PREREG), "cells_dir": os.path.relpath(_cells_dir(smoke), _ROOT),
            "cells_present": [a for a in ARMS if rows[a] is not None], "witness": witness, "verdict": verdict,
            "regime": dict(REGIME_P44, seed=SEED, agents=agents, ticks_learn=ticks_learn, ticks_test=ticks_test,
                           arms=list(ARMS), identity_audit=True, lr_override=None,
                           lr_effective_per_agent=((rows["off"] or {}).get("learning") or {}).get("lr_effective_per_agent")),
            "rows": rows}
    out = str(results_file("e34_identity_cell" + ("_smoke" if smoke else "") + ".json"))
    _save(out, data)
    print(f"[e34] {verdict['verdict']} : {verdict['why']} -> {out}", flush=True)
    return data


def _tout(args, rule, smoke, design):
    """Phase A : la cellule éteinte SEULE (témoin + unité de coût, machine libre) ; témoin rompu -> TEMOIN_ROMPU publié,
    arrêt. Garde E13 AVANT la phase B (unité × vagues × marge ≤ budget) ; phase B : 14 cellules en `workers` processus
    sous un PLAFOND PENDANT (Pool.terminate au dépassement, coupe publiée avec sa charge)."""
    import multiprocessing as mp
    from tools.cost_guard import project_cost
    from tools.evo_runs.s2_bassin_fragility import _charge, _neutraliser_kuzu
    from tools.jobs.run import hold
    budget_s = float((rule or {}).get("budget_s") or 3600.0)
    d = _cells_dir(smoke)
    if os.path.isdir(d) and os.listdir(d):
        raise RuntimeError(f"tout : {d} n'est pas vide -- une cellule d'une autre exécution comblerait un trou sans "
                           "trace (revue v2, P10.e) ; déplacer le répertoire d'abord")
    os.makedirs(d, exist_ok=True)
    agents, ticks_learn, ticks_test = _ticks(smoke)
    execution = {"workers": int(args.workers), "charge_depart": _charge(), "kuzu": "neutralise dans chaque ouvrier",
                 "budget_s": budget_s}
    owner = "e34-identity-cell" + ("-smoke" if smoke else "")
    t_start = time.time()
    ctx = mp.get_context("spawn")
    with hold("kuzu", owner=owner, ttl_s=max(3600.0, budget_s * 2)):
        with ctx.Pool(processes=1, initializer=_neutraliser_kuzu) as pool:            # phase A
            off = pool.apply(_tache, (SEED, "off", agents, ticks_learn, ticks_test, smoke))
        _save_cell(off, rule, smoke, {"design": design, "execution": dict(execution, phase="A")})
        unit = float(off["elapsed_s"])
        print(f"[e34] off : S = {off['survival']['survival_median']} ; commutations "
              f"{off['learning']['slot_identity']['slot_switches']} ; {unit:.1f}s", flush=True)
        if not smoke and not witness_check(off, SEED)["identical"]:
            print("[e34] TÉMOIN ROMPU : arrêt après la phase A", flush=True)
            return _lire(smoke)
        reste = [a for a in ARMS if a != "off"]
        vagues = math.ceil(len(reste) / int(args.workers))
        execution["unit_s_phase_A"] = unit
        execution["projected_s"] = project_cost(unit, n_units=vagues, budget_s=budget_s,
                                                label="e34-identity-cell (unité = la cellule éteinte seule, par vague)")
        pool = ctx.Pool(processes=int(args.workers), initializer=_neutraliser_kuzu)
        try:
            en_vol = {a: pool.apply_async(_tache, (SEED, a, agents, ticks_learn, ticks_test, smoke)) for a in reste}
            while en_vol:
                for a in [a for a, r in en_vol.items() if r.ready()]:
                    row = en_vol.pop(a).get()
                    _save_cell(row, rule, smoke, {"design": design, "execution": dict(execution, phase="B")})
                    print(f"[e34] {a} : S = {row['survival']['survival_median']} ; commutations "
                          f"{row['learning']['slot_identity']['slot_switches']} ; {row['elapsed_s']:.1f}s", flush=True)
                if en_vol and time.time() - t_start > budget_s:
                    pool.terminate()
                    coupe = {"coupe": True, "mur_s": time.time() - t_start, "charge": _charge(),
                             "non_terminees": sorted(en_vol)}
                    _save(os.path.join(d, "_coupe.json"), coupe)
                    print(f"[e34] PLAFOND DÉPASSÉ : coupe publiée ({sorted(en_vol)})", flush=True)
                    break
                time.sleep(2.0)
            else:
                pool.close()
        finally:
            pool.terminate()
            pool.join()
    print(f"[e34] tout : {time.time() - t_start:.0f}s de mur", flush=True)
    return None if smoke else _lire(smoke)


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
    agents, _, _ = _ticks(smoke)
    design = declare_design(
        question=(rule or {}).get("question", "smoke : débit de la sonde, aucune lecture"),
        replication_unit="seed (UNE cellule de %d clones du bassin, 15 traitements sur le MÊME seed, lieu et commit)"
                         % agents,
        n_independent=1,
        links={"invariant_slot_corps": "measured", "commutations": "measured", "bande_permutations": "measured",
               "controle_positif_credit_coupe": "measured", "survie_mortelle_poids_geles": "measured",
               "temoin_cellule_publiee": "measured"},
        cost_estimate=(rule or {}).get("budget_s"))
    if args.cmd == "tout":
        _tout(args, rule, smoke, design)
        return 0
    os.makedirs(_cells_dir(smoke), exist_ok=True)
    if os.path.exists(_cell_path(args.bras, smoke)):
        raise RuntimeError(f"cellule : {_cell_path(args.bras, smoke)} existe déjà -- aucune cellule n'est écrasée")
    from tools.evo_runs.s2_bassin_fragility import _neutraliser_kuzu
    _neutraliser_kuzu()
    with hold("kuzu", owner="e34-identity-cell" + ("-smoke" if smoke else ""), ttl_s=7200.0):
        _, tl, tt = _ticks(smoke)
        row = _tache(SEED, args.bras, agents, tl, tt, smoke)
    _save_cell(row, rule, smoke, {"design": design})
    print(f"[e34] {args.bras} : S = {row['survival']['survival_median']} ; commutations "
          f"{row['learning']['slot_identity']['slot_switches']} ; {row['elapsed_s']:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
