"""LEGACY-LR-CURVE-R1 (P2.72 a, 2026-09-15) — où commence l'instabilité de l'apprenant legacy ?

[[EDR-CALIB-LEGACY-LEARNER]] : `MambaBatchModel.compute_policy_gradient` est instable à son pas publié 0,04 (4 seeds
à 0,000 + 1 NaN) et apprend à 0,004 (11/12). Deux points de plus, lr 0,01 et 0,001, même dispositif
(`run_learner_probe(policy="legacy")`, cohorte immortelle, 2000 ticks, 12 agents), mêmes 12 seeds ; la référence
`lr0_reference` de P3.4 est IMPORTÉE par seed (même graine → même monde, pas nul → bras déterministe).
Règle scellée AVANT toute cellule : `docs/preregistrations/LEGACY-LR-CURVE-R1.json`. Résultats :
`results/legacy_lr_curve_r1.json`. Reprise par cellule ; une cellule refusée (apprenant divergent, aucune décision)
est PUBLIÉE avec sa raison et comptée « non mesurée ». Usage : python tools/legacy_lr_curve.py [--lecture]
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

RULE = "LEGACY-LR-CURVE-R1"
from src.paths import results_file   # noqa: E402  (porte 12 : jamais un chemin de donnees en dur)

REF_PATH = str(results_file("legacy_learner_calibration.json"))


def _reference():
    """hit_last de `lr0_reference` par seed, importé de P3.4 (bras déterministe à pas nul)."""
    r = json.load(open(REF_PATH, encoding="utf-8"))
    return {int(s): v["hit_last"] for s, v in r["arms"]["lr0_reference"]["per_seed"].items()}


def _lecture(db, regle, ref):
    c, s = regle["cellule"], regle["seuils"]
    seeds, lrs = c["seeds"], c["lr"]
    attendu = [f"lr={lr}|seed={sd}" for lr in lrs for sd in seeds]
    manquantes = [k for k in attendu if k not in db]
    if manquantes:
        return {"branche": "INCOMPLET", "manquantes": len(manquantes)}
    par_lr = {}
    for lr in lrs:
        cells = [db[f"lr={lr}|seed={sd}"] for sd in seeds]
        ok = [x for x in cells if x.get("learning") is not None]
        above = sum(1 for sd in seeds
                    if db[f"lr={lr}|seed={sd}"].get("hit_last") is not None
                    and db[f"lr={lr}|seed={sd}"]["hit_last"] > ref[sd] + s["min_sep"])
        par_lr[str(lr)] = {
            "mediane_hit_last": float(np.median([x["hit_last"] for x in ok])) if ok else None,
            "seeds_au_dessus": above, "non_mesures": len(cells) - len(ok),
            "effondres": sum(1 for x in ok if x["hit_last"] <= s["effondrement"]),
            "legacy_updates": float(np.median([x["learning"]["legacy_updates"] for x in ok])) if ok else None,
            "dW_abs_sum": float(np.median([x["learning"]["dW_abs_sum"] for x in ok])) if ok else None,
        }
    a, b = par_lr[str(lrs[0])], par_lr[str(lrs[1])]        # 0,01 puis 0,001
    out = {"par_lr": par_lr}
    if a["seeds_au_dessus"] >= s["seeds_min"] and a["effondres"] + a["non_mesures"] == 0:
        out["branche"] = "SEUIL_AU_DESSUS_DE_001"
    elif a["effondres"] + a["non_mesures"] >= 1 and b["seeds_au_dessus"] >= s["seeds_min"]:
        out["branche"] = "SEUIL_ENTRE_0001_ET_001"
    elif b["seeds_au_dessus"] < s["seeds_min"] and b["effondres"] + b["non_mesures"] == 0:
        out["branche"] = "TROP_BAS_A_0001"
    else:
        out["branche"] = "AUTRE"
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    regle = verify(RULE)
    c = regle["cellule"]
    out_path = str(results_file("legacy_lr_curve_r1.json"))
    db = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    ref = _reference()
    if "--lecture" in argv:
        print(json.dumps(_lecture(db, regle, ref), indent=1, ensure_ascii=False))
        return db
    design = declare_design(
        question=regle["question"],
        replication_unit="seed (une cohorte immortelle de %d agents, un monde par seed)" % c["num_agents"],
        n_independent=len(c["seeds"]),
        links={"taux_de_coups_legacy": "measured", "dose_legacy": "measured",
               "plafond_incapable_lr0": "inferred", "controle_positif_oracle": "inferred"},
        allow_inferred_reason=("lr0_reference et oracle sont IMPORTÉS du JSON de P3.4 (REF_PATH) : mêmes seeds, "
                               "même monde, bras déterministes (pas nul / oracle câblé) — les re-mesurer coûterait 12 × 40 s "
                               "pour reproduire des cellules bit-identiques ; le risque est borné par l'appariement par seed"),
        cost_estimate=regle["cout"],
        control_family=assert_control_family(cells=len(c["lr"]) * len(c["seeds"]), alpha_family=0.05))
    db.setdefault("_design", design)
    db.setdefault("_reference_importee", {"fichier": os.path.relpath(REF_PATH, _ROOT).replace("\\", "/"), "bras": "lr0_reference",
                                          "hit_last_par_seed": {str(k): v for k, v in ref.items()}})
    t0 = time.time()
    for lr in c["lr"]:
        for sd in c["seeds"]:
            k = f"lr={lr}|seed={sd}"
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
                L = r["learning"]
                print(f"  {k}: hit {r['hit_first']:.3f} -> {r['hit_last']:.3f} | legacy {L['legacy_updates']}/{L['legacy_calls']} "
                      f"dW {L['dW_abs_sum']:.1f} | resur {r['resurrections']} | {r['elapsed_s']:.0f}s", flush=True)
    db["_cout_s"] = db.get("_cout_s", 0.0) + (time.time() - t0)
    db["_lecture"] = _lecture(db, regle, ref)
    json.dump(stamp(db, RULE), open(out_path, "w", encoding="utf-8"), indent=1)
    print(json.dumps(db["_lecture"], indent=1, ensure_ascii=False))
    print("->", out_path)
    return db


if __name__ == "__main__":
    main()
