"""LEGACY-LR-CURVE-R2 (E28, 2026-09-15) — la courbe de pas de l'apprenant legacy RE-MESURÉE sous la garde du World Model.

R1 (sans garde) : 0,04 → 0,249 ; 0,01 → 0,303 ; 0,004 → 0,446 ; 0,001 → 0,518 — mesurés pendant que le World Model
par agent divergeait (E28 : NaN → mort par tick, `LEGACY-WM-GUARD-R1` : ARTEFACT_WM). Ici cinq pas dont lr=0
(référence RE-MESURÉE sous garde, dans la même grille), 12 seeds, même dispositif. Règle scellée avant toute cellule :
`docs/preregistrations/LEGACY-LR-CURVE-R2.json` ; résultats `results/legacy_lr_curve_r2.json`.
Usage : python tools/legacy_lr_curve_r2.py [--lecture]
"""
import json
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.paths import results_file
from tools.cognitive_demand_inworld import run_learner_probe
from tools.experiment_preflight import assert_control_family, declare_design
from tools.preregister import stamp, verify

RULE = "LEGACY-LR-CURVE-R2"


def _reference(db, seeds):
    """hit_last du bras lr=0.0 par seed, RE-MESURÉ sous garde dans la même grille ; absent si non mesuré."""
    out = {}
    for sd in seeds:
        c = db.get(f"lr=0.0|seed={sd}")
        if c is not None and c.get("hit_last") is not None:
            out[sd] = c["hit_last"]
    return out


def _lecture(db, regle):
    c, s = regle["cellule"], regle["seuils"]
    seeds, lrs = c["seeds"], c["lr"]
    attendu = [f"lr={lr}|seed={sd}" for lr in lrs for sd in seeds]
    manquantes = [k for k in attendu if k not in db]
    if manquantes:
        return {"branche": "INCOMPLET", "manquantes": len(manquantes)}
    ref = _reference(db, seeds)
    par_lr = {}
    for lr in lrs:
        cells = [db[f"lr={lr}|seed={sd}"] for sd in seeds]
        ok = [x for x in cells if x.get("learning") is not None]
        above = sum(1 for sd in seeds
                    if db[f"lr={lr}|seed={sd}"].get("hit_last") is not None and sd in ref
                    and db[f"lr={lr}|seed={sd}"]["hit_last"] > ref[sd] + s["min_sep"])
        par_lr[str(lr)] = {
            "mediane_hit_last": float(np.median([x["hit_last"] for x in ok])) if ok else None,
            "seeds_au_dessus": above, "non_mesures": len(cells) - len(ok),
            "effondres": sum(1 for x in ok if x["hit_last"] <= s["effondrement"]),
            "resurrections": float(np.median([x["resurrections"] for x in ok])) if ok else None,
            "wm_resets": float(np.median([x.get("wm_resets", 0) for x in ok])) if ok else None,
            "legacy_updates": float(np.median([x["learning"]["legacy_updates"] for x in ok])) if ok else None,
        }
    out = {"par_lr": par_lr}
    apprend = [lr for lr in lrs if lr != 0.0 and par_lr[str(lr)]["seeds_au_dessus"] >= s["seeds_min"]
               and par_lr[str(lr)]["effondres"] + par_lr[str(lr)]["non_mesures"] == 0]
    if apprend:
        out["branche"] = "APPREND_QUELQUE_PART"
        out["pas_qui_apprennent"] = apprend
    elif all(par_lr[str(lr)]["seeds_au_dessus"] < s["seeds_min"] for lr in lrs if lr != 0.0):
        out["branche"] = "INERTE_PARTOUT"
    else:
        out["branche"] = "AUTRE"
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    regle = verify(RULE)
    c = regle["cellule"]
    out_path = str(results_file("legacy_lr_curve_r2.json"))
    db = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    if "--lecture" in argv:
        print(json.dumps(_lecture(db, regle), indent=1, ensure_ascii=False))
        return db
    design = declare_design(
        question=regle["question"],
        replication_unit="seed (une cohorte immortelle de %d agents, un monde par seed ; 5 bras appariés)" % c["num_agents"],
        n_independent=len(c["seeds"]),
        links={"taux_de_coups_legacy": "measured", "dose_legacy": "measured", "plafond_incapable_lr0": "measured",
               "wm_resets": "measured", "controle_positif_oracle": "inferred"},
        allow_inferred_reason=("l'oracle (1,000 sur 12/12, P3.4) est câblé et ne passe ni par le World Model ni par le "
                               "gradient : la garde E28 ne peut pas le changer ; le risque est nul"),
        cost_estimate=regle["cout"],
        control_family=assert_control_family(cells=len(c["lr"]) * len(c["seeds"]), alpha_family=0.05))
    db.setdefault("_design", design)
    t0 = time.time()
    for lr in c["lr"]:
        for sd in c["seeds"]:
            k = f"lr={lr}|seed={sd}"
            if k in db:
                continue
            tc = time.time()
            try:
                r = run_learner_probe(seed=sd, num_agents=c["num_agents"], ticks=c["ticks"], block=c["block"],
                                      policy=c["policy"], lr=(None if lr is None else float(lr)))
            except ValueError as exc:
                r = {"policy": c["policy"], "seed": int(sd), "lr": lr, "erreur": str(exc), "hit_first": None,
                     "hit_last": None, "blocks": [], "learning": None}
                print(f"  {k}: NON MESURE : {exc}", flush=True)
            r["elapsed_s"] = time.time() - tc
            db[k] = r
            json.dump(stamp(db, RULE), open(out_path, "w", encoding="utf-8"), indent=1)
            if r.get("learning") is not None:
                print(f"  {k}: hit {r['hit_first']:.3f} -> {r['hit_last']:.3f} | resur {r['resurrections']} | "
                      f"wm_resets {r['wm_resets']} | nan_skips {r['nan_skips']} | {r['elapsed_s']:.0f}s", flush=True)
    db["_cout_s"] = db.get("_cout_s", 0.0) + (time.time() - t0)
    db["_lecture"] = _lecture(db, regle)
    json.dump(stamp(db, RULE), open(out_path, "w", encoding="utf-8"), indent=1)
    print(json.dumps(db["_lecture"], indent=1, ensure_ascii=False))
    print("->", out_path)
    return db


if __name__ == "__main__":
    main()
