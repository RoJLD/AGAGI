"""BILINEAR-ALIGNED-R1 (P2.70, 2026-09-15) — la séparation plain / bilinéaire d'EDR-BILINEAR tient-elle
quand l'entraînement supervisé est ALIGNÉ sur l'évaluation (softmax sur K classes, `n_classes=K`) ?

Règle scellée AVANT toute cellule de mesure : `docs/preregistrations/BILINEAR-ALIGNED-R1.json` (le seed 0
a servi de fumée de bit-identité et est EXCLU : seeds 1-12). Même régime que le bras décisif publié
(`results/bilinear_composition.json` : 300 épisodes, 16 agents, K=6, rank 16, same_tick, supervisé), deux
pas (`lr` 0,02 publié + 0,002, clause E19), `align_train_eval=True`. Résultats : `results/bilinear_aligned_r1.json`.
Pur torch CPU, aucun bail. Usage : python tools/bilinear_aligned_run.py
"""
import json
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.bilinear_composition_probe import _train_eval_one
from tools.experiment_preflight import assert_control_family, declare_design
from tools.preregister import stamp, verify
from src.paths import results_file   # noqa: E402  (porte 12)

RULE = "BILINEAR-ALIGNED-R1"


def _lecture(db, regle):
    """Branche scellée, dans l'ORDRE IMPOSÉ. Ne lit que des cellules présentes ; jamais une inférence."""
    c = regle["cellule"]
    seeds, lrs = c["seeds"], c["lr"]
    attendu = [f"{sub}|lr={lr}|seed={s}" for sub in ("plain", "bilinear") for lr in lrs for s in seeds]
    manquantes = [k for k in attendu if k not in db]
    if manquantes:
        return {"branche": "INCOMPLET", "manquantes": len(manquantes)}
    s = regle["seuils"]

    def med(sub, lr):
        return float(np.median([db[f"{sub}|lr={lr}|seed={sd}"] for sd in seeds]))
    lr_pub, lr_bas = lrs[0], lrs[1]
    mp, mb = med("plain", lr_pub), med("bilinear", lr_pub)
    mp2, mb2 = med("plain", lr_bas), med("bilinear", lr_bas)
    sep = sum(1 for sd in seeds
              if db[f"bilinear|lr={lr_pub}|seed={sd}"] > db[f"plain|lr={lr_pub}|seed={sd}"] + s["marge_seed"])
    out = {"mediane_plain_002": mp, "mediane_bilineaire_002": mb, "mediane_plain_0002": mp2,
           "mediane_bilineaire_0002": mb2, "separation_par_seed": f"{sep}/{len(seeds)}"}
    if mb >= s["seuil_bilineaire"] and mp <= s["seuil_plain_max"] and sep >= s["seeds_min"]:
        out["branche"] = "SEPARATION_TIENT"
    elif mp > s["seuil_plain_max"] or sep < s["seeds_min"]:
        out["branche"] = "SEPARATION_TOMBE"
    elif mb < s["seuil_bilineaire"] and mb2 < s["seuil_bilineaire"]:
        out["branche"] = "BILINEAIRE_SOUS_SEUIL"
    else:
        out["branche"] = "AUTRE"
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    regle = verify(RULE)
    out_path = str(results_file("bilinear_aligned_r1.json"))
    c = regle["cellule"]
    db = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    if "--lecture" in argv:
        print(json.dumps(_lecture(db, regle), indent=1, ensure_ascii=False))
        return db
    design = declare_design(
        question=regle["question"],
        replication_unit="seed (une population de %d agents par cellule ; 4 bras appariés par seed)" % c["n_agents"],
        n_independent=len(c["seeds"]),
        links={"accuracy_plain_alignee": "measured", "accuracy_bilineaire_alignee": "measured",
               "bit_identite_du_defaut": "measured", "plafond_plain_forme_close": "inferred"},   # 0,3889 = MINORANT importe
        cost_estimate=regle["cout"],
        allow_inferred_reason=("le plafond 0,3889 du plain est un MINORANT en forme close (tools/plain_substrate_ceiling.py, "
                               "34/36), pas une mesure de cette sonde : il sert de seuil scelle, et un plain qui le "
                               "depasse ne fait que rendre la branche SEPARATION_TOMBE -- le risque est borne par la regle"),
        control_family=assert_control_family(cells=2 * 2 * len(c["seeds"]), alpha_family=0.05))
    db.setdefault("_design", design)
    db.setdefault("_regime", {k: v for k, v in c.items() if k != "seeds"})
    t0 = time.time()
    for lr in c["lr"]:
        for s in c["seeds"]:
            for sub, bil in (("plain", False), ("bilinear", True)):
                k = f"{sub}|lr={lr}|seed={s}"
                if k in db:
                    continue
                tc = time.time()
                acc = _train_eval_one(seed=s, bilinear=bil, task="composition", episodes=c["episodes"],
                                      n_agents=c["n_agents"], K=c["K"], lr=lr, rank=c["rank"],
                                      same_tick=c["same_tick"], credit_mode=c["credit_mode"],
                                      align_train_eval=c["align_train_eval"])
                db[k] = float(acc)
                json.dump(stamp(db, RULE), open(out_path, "w", encoding="utf-8"), indent=1)
                print(f"  {k}: {acc:.3f} ({time.time() - tc:.1f} s)", flush=True)
    db["_cout_s"] = db.get("_cout_s", 0.0) + (time.time() - t0)
    db["_lecture"] = _lecture(db, regle)
    json.dump(stamp(db, RULE), open(out_path, "w", encoding="utf-8"), indent=1)
    print(json.dumps(db["_lecture"], indent=1, ensure_ascii=False))
    print("->", out_path)
    return db


if __name__ == "__main__":
    main()
