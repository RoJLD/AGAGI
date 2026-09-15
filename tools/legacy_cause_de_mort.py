"""LEGACY-CAUSE-DE-MORT-R1 (P2.72 b, 2026-09-15) — par quel canal le monde tue-t-il les apprenants legacy ?

[[EDR-CALIB-LEGACY-LEARNER]] : le bras `natural` ressuscite 18 265 fois par seed (0,76 mort/agent/tick), l'oracle 0.
`run_learner_probe` publie désormais `cause_de_mort` (énergie ≤ 0 / hp ≤ 0 / les deux / AUCUNE), compté AVANT la
recharge. Trois bras (natural 0,04 ; lr_low 0,004 ; lr0_reference 0), 12 seeds, même dispositif. Règle scellée avant
toute cellule : `docs/preregistrations/LEGACY-CAUSE-DE-MORT-R1.json`. Résultats : `results/legacy_cause_de_mort.json`.
Usage : python tools/legacy_cause_de_mort.py [--lecture]
"""
import json
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.cognitive_demand_inworld import run_learner_probe
from tools.experiment_preflight import assert_control_family, declare_design
from tools.preregister import stamp, verify
from src.paths import results_file   # noqa: E402  (porte 12)

RULE = "LEGACY-CAUSE-DE-MORT-R1"


def _parts(cdm):
    tot = sum(int(v) for v in cdm.values())
    if tot == 0:
        return {"part_energie": None, "part_hp": None, "part_les_deux": None, "aucune": int(cdm.get("AUCUNE", 0)), "total": 0}
    return {"part_energie": cdm.get("energie_epuisee", 0) / tot, "part_hp": cdm.get("hp_epuise", 0) / tot,
            "part_les_deux": cdm.get("les_deux", 0) / tot, "aucune": int(cdm.get("AUCUNE", 0)), "total": tot}


def _lecture(db, regle):
    c, s = regle["cellule"], regle["seuils"]
    bras, seeds = list(c["bras"]), c["seeds"]
    attendu = [f"{b}|seed={sd}" for b in bras for sd in seeds]
    if any(k not in db for k in attendu):
        return {"branche": "INCOMPLET", "manquantes": sum(1 for k in attendu if k not in db)}
    par_bras = {}
    for b in bras:
        cells = [db[f"{b}|seed={sd}"] for sd in seeds]
        ok = [x for x in cells if x.get("learning") is not None]
        parts = [_parts(x["cause_de_mort"]) for x in ok]
        avec = [p for p in parts if p["total"] > 0]

        def med(k):
            return float(np.median([p[k] for p in avec])) if avec else None
        par_bras[b] = {"part_energie": med("part_energie"), "part_hp": med("part_hp"), "part_les_deux": med("part_les_deux"),
                       "aucune": sum(p["aucune"] for p in parts), "non_mesures": len(cells) - len(ok),
                       "seeds_sans_mort": len(parts) - len(avec),
                       "resurrections": float(np.median([x["resurrections"] for x in ok])) if ok else None,
                       "hit_last": float(np.median([x["hit_last"] for x in ok])) if ok else None}
    out = {"par_bras": par_bras}
    nat = par_bras["natural"]
    if any(v["aucune"] > s["aucune_max"] for v in par_bras.values()):
        out["branche"] = "INSTRUMENT"
    elif nat["part_energie"] is not None and nat["part_energie"] >= s["dominant"]:
        out["branche"] = "ENERGIE"
    elif nat["part_hp"] is not None and nat["part_hp"] >= s["dominant"]:
        out["branche"] = "HP"
    else:
        out["branche"] = "MIXTE"
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    regle = verify(RULE)
    c = regle["cellule"]
    out_path = str(results_file("legacy_cause_de_mort.json"))
    db = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    if "--lecture" in argv:
        print(json.dumps(_lecture(db, regle), indent=1, ensure_ascii=False))
        return db
    design = declare_design(
        question=regle["question"],
        replication_unit="seed (une cohorte immortelle de %d agents, un monde par seed ; 3 bras appariés)" % c["num_agents"],
        n_independent=len(c["seeds"]),
        links={"cause_de_mort_par_bras": "measured", "resurrections": "measured", "taux_de_coups": "measured"},
        cost_estimate=regle["cout"],
        control_family=assert_control_family(cells=len(c["bras"]) * len(c["seeds"]), alpha_family=0.05))
    db.setdefault("_design", design)
    t0 = time.time()
    for b, lr in c["bras"].items():
        for sd in c["seeds"]:
            k = f"{b}|seed={sd}"
            if k in db:
                continue
            tc = time.time()
            try:
                r = run_learner_probe(seed=sd, num_agents=c["num_agents"], ticks=c["ticks"], block=c["block"],
                                      policy=c["policy"], lr=lr)
            except ValueError as exc:
                r = {"policy": c["policy"], "seed": int(sd), "lr": lr, "erreur": str(exc), "hit_first": None,
                     "hit_last": None, "blocks": [], "learning": None}
                print(f"  {k}: NON MESURE : {exc}", flush=True)
            r["elapsed_s"] = time.time() - tc
            db[k] = r
            json.dump(stamp(db, RULE), open(out_path, "w", encoding="utf-8"), indent=1)
            if r.get("learning") is not None:
                print(f"  {k}: hit {r['hit_last']:.3f} | resur {r['resurrections']} | {r['cause_de_mort']} | {r['elapsed_s']:.0f}s",
                      flush=True)
    db["_cout_s"] = db.get("_cout_s", 0.0) + (time.time() - t0)
    db["_lecture"] = _lecture(db, regle)
    json.dump(stamp(db, RULE), open(out_path, "w", encoding="utf-8"), indent=1)
    print(json.dumps(db["_lecture"], indent=1, ensure_ascii=False))
    print("->", out_path)
    return db


if __name__ == "__main__":
    main()
