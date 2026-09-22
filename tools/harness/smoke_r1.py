"""
tools/harness/smoke_r1.py — SMOKE de la famille HARNESS-R1 : 3 seeds, sans bail. Mesure (a) la bit-identité de A et
de B au seed 0 (contre les valeurs déjà publiées), (b) le candidat second lr de B parmi {0.001, 0.0005} à
n_classes=6, (c) l'unité de coût COMPARABLE entre cellules, (d) la bande de bruit par cellule et par seed. Sortie :
results harness_r1_smoke_0(.json|_rerunN.json) (Harness, sans DB — le nominal est détourné si SUIVI par git, cf.
Harness._chemin_de_sortie). Usage : PYTHONIOENCODING=utf-8 python -m tools.harness.smoke_r1

Fix round 1/5 (revue contrôleur, tâche 10) — quatre défauts réels corrigés ici :
(2) `unit_s` mesurait le bras NU (sans ablations/contrôles) pour A et A', mais la valeur PUBLIÉE dans la
    règle scellée sert de proxy au coût du bras `full_eval=True` que `run_harness_cell` chronomètre
    RÉELLEMENT pour choisir son unité de projection de coût (cf. `tools/harness/cell.py::run_harness_cell`,
    `unit = max(clock() - t0, 1e-6)` mesuré sur le premier `_run_arm(..., full_eval=True)`). Les trois
    cellules n'étaient donc PAS comparables entre elles (B, avec 4 ablations + 2 splits contrôle, coûte
    largement plus que sa version nue) — corrigé en chronométrant le bras `full_eval=True` pour LES TROIS
    cellules (`unit_s`), et en publiant SÉPARÉMENT le coût du bras nu (`unit_s_nude`, les bras A0/A2/D/D2
    réels de `run_harness_cell`, qui ne sont jamais `full_eval`).
(3) `Aprime_ref` (référence lr=0 de la cellule A', 150 ép., 3 seeds) manquait : la prédiction ACQUIRED de
    A' n'était adossée à AUCUNE mesure de sa propre référence appariée.
(7) le plancher de bruit (`last`/`noop` du bras `full_eval`) n'était publié QUE pour la cellule A ; la
    prédiction « A' NOT_NECESSARY » et « B NECESSARY » en dépendent tout autant — publié maintenant PAR
    CELLULE et PAR SEED : `noise = {"A": {seed: ratio}, "Aprime": {...}, "B": {...}}`.
(11) ajoute une assertion de bit-identité GRATUITE (le fichier existe déjà, publié) sur la cellule B au
    seed 0, contre `results_file("retain_compose_lr_replication.json")["lr_0.002"]["per_seed"]["learned"][0]`.

Fix round 2/5 (revue contrôleur, tâche 10) point (3) : `B_SWEEP0_LR` vit désormais dans
`tools/harness/r1_constants.py`, SOURCE UNIQUE partagée avec `seal_r1.py` — plus de littéral `0.002`
dupliqué qui pourrait diverger en silence. `SMOKE_NAME` (même module) fixe le nom `Harness` du smoke,
que `seal_r1.py` réutilise pour calculer son chemin par défaut (point 2).
"""
import json
import os
import sys
import time

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.paths import results_file  # noqa: E402
from src.seed_ai.harness import Harness  # noqa: E402
from tools.harness.cell import _run_arm  # noqa: E402
from tools.harness.learners.connectome import ConnectomeLearner  # noqa: E402
from tools.harness.r1_constants import B_SWEEP0_LR, SMOKE_NAME, SMOKE_SEED  # noqa: E402
from tools.harness.tasks.composition import CompositionTask  # noqa: E402

SEEDS = (0, 1, 2)
H_A = {"lr": 0.02, "rank": 16, "n_classes": None, "credit": "supervised"}


def _hb(lr):
    return {"lr": lr, "rank": 16, "n_classes": 6, "credit": "supervised"}


def main():
    lrn = ConnectomeLearner()
    A = CompositionTask(K=6, same_tick=True)
    Ap = CompositionTask(K=6, same_tick=True, kind="recall")
    B = CompositionTask(K=6, same_tick=False)

    out = {"A": {"0.02": {}}, "A_plain": {}, "A_ref": {},
           "Aprime": {}, "Aprime_plain": {}, "Aprime_ref": {},
           "B": {}, "B_ref": {},
           "noise": {"A": {}, "Aprime": {}, "B": {}},
           "unit_s": {}, "unit_s_nude": {}}
    unit_full, unit_nude = {}, {}

    for s in SEEDS:
        ss = str(s)

        # --- Cellule A : le bras full_eval=True EST le bras "A" que run_harness_cell chronomètre. ---
        t0 = time.perf_counter()
        rA = _run_arm(A, lrn, s, 16, 6, H_A, 300, 40, full_eval=True)
        unit_full.setdefault("A", []).append(time.perf_counter() - t0)
        out["A"]["0.02"][ss] = rA["last"]
        out["noise"]["A"][ss] = rA["last"] / rA["noop"]

        t0 = time.perf_counter()
        rA_plain = _run_arm(A, lrn, s, 16, 6, H_A, 300, 40, without={"bilinear": False})
        unit_nude.setdefault("A", []).append(time.perf_counter() - t0)
        out["A_plain"][ss] = rA_plain["last"]

        t0 = time.perf_counter()
        rA_ref = _run_arm(A, lrn, s, 16, 6, H_A, 300, 40, reference=True)
        unit_nude["A"].append(time.perf_counter() - t0)
        out["A_ref"][ss] = rA_ref["last"]

        # --- Cellule A' (recall) : même discipline. ---
        t0 = time.perf_counter()
        rAp = _run_arm(Ap, lrn, s, 16, 6, H_A, 150, 40, full_eval=True)
        unit_full.setdefault("Aprime", []).append(time.perf_counter() - t0)
        out["Aprime"][ss] = rAp["last"]
        out["noise"]["Aprime"][ss] = rAp["last"] / rAp["noop"]

        t0 = time.perf_counter()
        rAp_plain = _run_arm(Ap, lrn, s, 16, 6, H_A, 150, 40, without={"bilinear": False})
        unit_nude.setdefault("Aprime", []).append(time.perf_counter() - t0)
        out["Aprime_plain"][ss] = rAp_plain["last"]

        t0 = time.perf_counter()
        rAp_ref = _run_arm(Ap, lrn, s, 16, 6, H_A, 150, 40, reference=True)
        unit_nude["Aprime"].append(time.perf_counter() - t0)
        out["Aprime_ref"][ss] = rAp_ref["last"]

        # --- Cellule B : le bras full_eval=True est celui du PREMIER pas du sweep (B_SWEEP0_LR), pas
        # un choix arbitraire -- c'est exactement le hyper que run_harness_cell passerait à son bras "A".
        t0 = time.perf_counter()
        rB0 = _run_arm(B, lrn, s, 16, 6, _hb(B_SWEEP0_LR), 600, 40, full_eval=True)
        unit_full.setdefault("B", []).append(time.perf_counter() - t0)
        out["B"].setdefault(str(B_SWEEP0_LR), {})[ss] = rB0["last"]
        out["noise"]["B"][ss] = rB0["last"] / rB0["noop"]

        for lr in (0.001, 0.0005):
            t0 = time.perf_counter()
            r = _run_arm(B, lrn, s, 16, 6, _hb(lr), 600, 40)
            unit_nude.setdefault("B", []).append(time.perf_counter() - t0)
            out["B"].setdefault(str(lr), {})[ss] = r["last"]

        t0 = time.perf_counter()
        rBref = _run_arm(B, lrn, s, 16, 6, _hb(B_SWEEP0_LR), 600, 40, reference=True)
        unit_nude["B"].append(time.perf_counter() - t0)
        out["B_ref"][ss] = rBref["last"]

        print(f"seed {s}: A {out['A']['0.02'][ss]:.4f} plain {out['A_plain'][ss]:.4f} "
              f"ref {out['A_ref'][ss]:.4f} noise {out['noise']['A'][ss]:.3f} | "
              f"Aprime {out['Aprime'][ss]:.4f} plain {out['Aprime_plain'][ss]:.4f} "
              f"ref {out['Aprime_ref'][ss]:.4f} noise {out['noise']['Aprime'][ss]:.3f} | B " +
              " ".join(f"{lr}:{out['B'][str(lr)][ss]:.3f}" for lr in (B_SWEEP0_LR, 0.001, 0.0005)) +
              f" ref {out['B_ref'][ss]:.4f} noise {out['noise']['B'][ss]:.3f}")

    out["unit_s"] = {k: float(np.median(v)) for k, v in unit_full.items()}
    out["unit_s_nude"] = {k: float(np.median(v)) for k, v in unit_nude.items()}

    assert out["A"]["0.02"]["0"] == 0.932812511920929, "bit-identite de la cellule A PERDUE au seed 0"
    assert out["A_plain"]["0"] == 0.27031248807907104, "bit-identite du plain PERDUE au seed 0"
    with open(results_file("retain_compose_lr_replication.json"), encoding="utf-8") as f:
        pub_b = json.load(f)
    pub_b002_seed0 = pub_b["lr_0.002"]["per_seed"]["learned"][0]
    assert out["B"][str(B_SWEEP0_LR)]["0"] == pub_b002_seed0, \
        f"bit-identite de la cellule B (lr={B_SWEEP0_LR}) PERDUE au seed 0 (publie {pub_b002_seed0})"

    print("\n-- resume --")
    print(f"unit_s (bras full_eval, mediane s/bras -- ce que run_harness_cell chronometre) : {out['unit_s']}")
    print(f"unit_s_nude (bras nu, mediane s/bras) : {out['unit_s_nude']}")
    print(f"noise (last/noop, par cellule et par seed) : {out['noise']}")
    for lr in (B_SWEEP0_LR, 0.001, 0.0005):
        vals = [out["B"][str(lr)][str(s)] for s in SEEDS]
        print(f"B lr={lr} : {vals} (mediane {float(np.median(vals)):.4f})")

    h = Harness(seed=SMOKE_SEED, name=SMOKE_NAME, with_db=False)
    path = h.save(out)
    print("->", path)


if __name__ == "__main__":
    main()
