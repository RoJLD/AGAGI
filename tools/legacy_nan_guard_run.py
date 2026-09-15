"""LEGACY-NAN-GUARD-R1 (E28, 2026-09-15) — la létalité et l'instabilité du pas publié de l'apprenant legacy
étaient-elles une CASCADE NaN ?

Diagnostic n=1 (200 ticks) : 669/669 morts de la cohorte immortelle avaient un `surprise_momentum` non fini,
663/669 un W non fini ; puits « brain » = 71 % de l'énergie perdue (0 % à lr=0) ; le monde fait
`energy = max(0.0, energy - brain_cost)` et `max(0.0, nan)` vaut 0.0 — un NaN devenait une MORT à chaque tick.
La garde E28 (`compute_policy_gradient` : un dW non fini est compté et sauté, W reste fini) est posée ; ce runner
re-mesure le bras `natural` (lr 0,04) sur les 12 seeds de P3.4. Règle scellée avant toute cellule :
`docs/preregistrations/LEGACY-NAN-GUARD-R1.json`. Résultats : `results/legacy_nan_guard_r1.json`.
Usage : python tools/legacy_nan_guard_run.py [--lecture]
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

RULE = "LEGACY-NAN-GUARD-R1"
REFERENCE_RESURRECTIONS = 18265.0        # natural SANS garde, médiane, results/legacy_learner_calibration.json


def _reference_lr0():
    r = json.load(open(str(results_file("legacy_learner_calibration.json")), encoding="utf-8"))
    return {int(s): v["hit_last"] for s, v in r["arms"]["lr0_reference"]["per_seed"].items()}


def _lecture(db, regle, ref):
    c, s = regle["cellule"], regle["seuils"]
    seeds = c["seeds"]
    cells = [db.get(f"seed={sd}") for sd in seeds]
    if any(x is None for x in cells):
        return {"branche": "INCOMPLET", "manquantes": sum(1 for x in cells if x is None)}
    ok = [x for x in cells if x.get("learning") is not None]
    non_mesures = len(cells) - len(ok)
    med = lambda k: float(np.median([x[k] for x in ok])) if ok else None    # noqa: E731
    out = {"resurrections": med("resurrections"), "reference_resurrections": REFERENCE_RESURRECTIONS,
           "ratio_resurrections": (med("resurrections") / REFERENCE_RESURRECTIONS) if ok else None,
           "effondres": sum(1 for x in ok if x["hit_last"] <= s["effondrement"]), "non_mesures": non_mesures,
           "nan_skips": med("nan_skips"), "morts_w_non_fini": med("morts_w_non_fini"),
           "mediane_hit_last": med("hit_last"),
           "seeds_au_dessus": sum(1 for sd in seeds if db[f"seed={sd}"].get("hit_last") is not None
                                  and db[f"seed={sd}"]["hit_last"] > ref[sd] + s["min_sep"])}
    if out["nan_skips"] == 0:
        out["branche"] = "GARDE_INACTIVE"
    elif out["ratio_resurrections"] <= s["artefact_max_ratio"] and out["effondres"] + non_mesures == 0:
        out["branche"] = "ARTEFACT_NAN"
    elif out["ratio_resurrections"] <= s["partiel_max_ratio"] or out["effondres"] + non_mesures == 0:
        out["branche"] = "PARTIEL"
    else:
        out["branche"] = "PAS_NAN"
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    regle = verify(RULE)
    c = regle["cellule"]
    out_path = str(results_file("legacy_nan_guard_r1.json"))
    db = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    ref = _reference_lr0()
    if "--lecture" in argv:
        print(json.dumps(_lecture(db, regle, ref), indent=1, ensure_ascii=False))
        return db
    design = declare_design(
        question=regle["question"],
        replication_unit="seed (une cohorte immortelle de %d agents, un monde par seed)" % c["num_agents"],
        n_independent=len(c["seeds"]),
        links={"resurrections_avec_garde": "measured", "nan_skips": "measured", "morts_w_non_fini": "measured",
               "resurrections_sans_garde": "inferred", "plafond_incapable_lr0": "inferred"},
        allow_inferred_reason=("les cellules SANS garde (natural, lr0) sont IMPORTÉES du JSON de P3.4 : mêmes seeds, même monde, "
                               "bit-identiques par construction (déterminisme par seed vérifié par LEGACY-CAUSE-DE-MORT-R1) ; "
                               "le risque est borné par l'appariement"),
        cost_estimate=regle["cout"],
        control_family=assert_control_family(cells=len(c["seeds"]), alpha_family=0.05))
    db.setdefault("_design", design)
    t0 = time.time()
    for sd in c["seeds"]:
        k = f"seed={sd}"
        if k in db:
            continue
        tc = time.time()
        try:
            r = run_learner_probe(seed=sd, num_agents=c["num_agents"], ticks=c["ticks"], block=c["block"], policy=c["policy"])
        except ValueError as exc:
            r = {"policy": c["policy"], "seed": int(sd), "erreur": str(exc), "hit_first": None, "hit_last": None,
                 "blocks": [], "learning": None}
            print(f"  {k}: NON MESURE : {exc}", flush=True)
        r["elapsed_s"] = time.time() - tc
        db[k] = r
        json.dump(stamp(db, RULE), open(out_path, "w", encoding="utf-8"), indent=1)
        if r.get("learning") is not None:
            print(f"  {k}: hit {r['hit_first']:.3f} -> {r['hit_last']:.3f} | resur {r['resurrections']} | nan_skips {r['nan_skips']} "
                  f"| W non fini {r['morts_w_non_fini']} | {r['elapsed_s']:.0f}s", flush=True)
    db["_cout_s"] = db.get("_cout_s", 0.0) + (time.time() - t0)
    db["_lecture"] = _lecture(db, regle, ref)
    json.dump(stamp(db, RULE), open(out_path, "w", encoding="utf-8"), indent=1)
    print(json.dumps(db["_lecture"], indent=1, ensure_ascii=False))
    print("->", out_path)
    return db


if __name__ == "__main__":
    main()
