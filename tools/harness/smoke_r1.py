"""
tools/harness/smoke_r1.py — SMOKE de la famille HARNESS-R1 : 3 seeds, sans bail. Mesure (a) la bit-identité de A au
seed 0, (b) le candidat second lr de B parmi {0.001, 0.0005} à n_classes=6, (c) l'unité de coût par bras, (d) une
première bande no-op. Sortie : results harness_r1_smoke_0.json (Harness, sans DB). Usage : PYTHONIOENCODING=utf-8
python -m tools.harness.smoke_r1
"""
import os
import sys
import time

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.seed_ai.harness import Harness  # noqa: E402
from tools.harness.cell import _run_arm  # noqa: E402
from tools.harness.learners.connectome import ConnectomeLearner  # noqa: E402
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
    out = {"A": {"0.02": {}}, "A_plain": {}, "A_ref": {}, "Aprime": {}, "Aprime_plain": {}, "B": {}, "B_ref": {},
           "noise": {}, "unit_s": {}}
    t = {}
    for s in SEEDS:
        t0 = time.perf_counter()
        r = _run_arm(A, lrn, s, 16, 6, H_A, 300, 40, full_eval=True)
        t.setdefault("A", []).append(time.perf_counter() - t0)
        out["A"]["0.02"][str(s)], out["noise"][str(s)] = r["last"], r["last"] / r["noop"]
        out["A_plain"][str(s)] = _run_arm(A, lrn, s, 16, 6, H_A, 300, 40, without={"bilinear": False})["last"]
        out["A_ref"][str(s)] = _run_arm(A, lrn, s, 16, 6, H_A, 300, 40, reference=True)["last"]
        t0 = time.perf_counter()
        out["Aprime"][str(s)] = _run_arm(Ap, lrn, s, 16, 6, H_A, 150, 40)["last"]
        t.setdefault("Aprime", []).append(time.perf_counter() - t0)
        out["Aprime_plain"][str(s)] = _run_arm(Ap, lrn, s, 16, 6, H_A, 150, 40, without={"bilinear": False})["last"]
        for lr in (0.002, 0.001, 0.0005):
            t0 = time.perf_counter()
            out["B"].setdefault(str(lr), {})[str(s)] = _run_arm(B, lrn, s, 16, 6, _hb(lr), 600, 40)["last"]
            t.setdefault("B", []).append(time.perf_counter() - t0)
        out["B_ref"][str(s)] = _run_arm(B, lrn, s, 16, 6, _hb(0.002), 600, 40, reference=True)["last"]
        print(f"seed {s}: A {out['A']['0.02'][str(s)]:.4f} plain {out['A_plain'][str(s)]:.4f} "
              f"ref {out['A_ref'][str(s)]:.4f} | Aprime {out['Aprime'][str(s)]:.4f} "
              f"plain {out['Aprime_plain'][str(s)]:.4f} | B " +
              " ".join(f"{lr}:{out['B'][str(lr)][str(s)]:.3f}" for lr in (0.002, 0.001, 0.0005)) +
              f" ref {out['B_ref'][str(s)]:.4f} | noise {out['noise'][str(s)]:.3f}")
    out["unit_s"] = {k: float(np.median(v)) for k, v in t.items()}
    assert out["A"]["0.02"]["0"] == 0.932812511920929, "bit-identite de la cellule A PERDUE au seed 0"
    assert out["A_plain"]["0"] == 0.27031248807907104, "bit-identite du plain PERDUE au seed 0"
    print("\n-- resume --")
    print(f"unit_s (mediane, s/bras) : {out['unit_s']}")
    print(f"noise (last/noop, par seed, bras A) : {out['noise']}")
    for lr in (0.002, 0.001, 0.0005):
        vals = [out["B"][str(lr)][str(s)] for s in map(str, SEEDS)]
        print(f"B lr={lr} : {vals} (mediane {float(np.median(vals)):.4f})")
    h = Harness(seed=0, name="harness_r1_smoke", with_db=False)
    print("->", h.save(out))


if __name__ == "__main__":
    main()
