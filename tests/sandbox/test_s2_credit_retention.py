"""P4.4 — `S2-CREDIT-RETENTION` : le crédit in-world (calibré par [[EDR-CALIB-LEARNER]]) RETIENT-il ou
ÉTEND-il le bassin DAgger persisté de WARM-003, et construit-il de la survie à FROID, quand
l'apprentissage se fait à dose non bornée par la mort (phase 1 IMMORTELLE) et que la survie se mesure
ensuite à poids GELÉS (phase 2 MORTELLE) ?

Ce fichier calibre le VERDICT (pur, réponses connues, branches de la règle scellée dans l'ordre imposé)
et les gardes du runner. Aucun monde n'est simulé ici.
"""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.evo_runs import s2_credit_retention as R  # noqa: E402


def _rows(n=12, S_a=35.0, S_b=None, S_c=None, dose_b=1999, dose_c=1999, jitter=None):
    """n seeds ; S_b/S_c peuvent être une liste (par seed) ou un scalaire."""
    rows = []
    for i in range(n):
        sb = S_b[i] if isinstance(S_b, (list, tuple)) else (S_a if S_b is None else S_b)
        sc = S_c[i] if isinstance(S_c, (list, tuple)) else (9.0 if S_c is None else S_c)
        rows.append({"seed": 2026 + i, "S_a": float(S_a), "S_b": float(sb), "S_c": float(sc),
                     "dose_b": int(dose_b), "dose_c": int(dose_c)})
    return rows


def test_verdict_refuses_missing_or_non_finite_inputs():
    rows = _rows()
    rows[3]["S_b"] = float("nan")
    with pytest.raises(ValueError):
        R.credit_retention_verdict(rows)
    rows = _rows()
    del rows[5]["S_c"]
    with pytest.raises(ValueError):
        R.credit_retention_verdict(rows)
    with pytest.raises(ValueError):
        R.credit_retention_verdict([])


def test_verdict_branch_order_INCOMPLET_before_anything_else():
    v = R.credit_retention_verdict(_rows(n=7, S_a=2.0))      # harnais mort ET n<12 : INCOMPLET gagne
    assert v["verdict"] == "INCOMPLET" and v["n"] == 7


def test_verdict_INDETERMINE_HARNAIS_when_the_bassin_does_not_transfer():
    """WARM-003 a mesuré le bassin à 35,2 ; sous `harness_min` = 20 (plus de la moitié perdue), on ne
    teste pas la rétention d'un bassin qui n'est pas là."""
    v = R.credit_retention_verdict(_rows(S_a=15.0, S_b=30.0))
    assert v["verdict"] == "INDETERMINE_HARNAIS" and "S_a" in v["why"]


def test_verdict_INDETERMINE_DOSE_when_the_credit_did_not_fire():
    """P1.6 : 1999 mises à jour TD par agent en 2000 ticks immortels. Une dose médiane < 1000 dit que le
    crédit ne s'est pas appliqué (bras qui ne peut pas réussir, E2) — aucun verdict de rétention."""
    v = R.credit_retention_verdict(_rows(dose_b=40))
    assert v["verdict"] == "INDETERMINE_DOSE" and "dose_b" in v["why"]
    v = R.credit_retention_verdict(_rows(dose_c=40))
    assert v["verdict"] == "INDETERMINE_DOSE" and "dose_c" in v["why"]


def test_verdict_RETENU_ETENDU_needs_sign_10_of_12_AND_median_plus_5():
    v = R.credit_retention_verdict(_rows(S_a=35.0, S_b=[45.0] * 10 + [34.0, 33.0]))
    assert v["verdict_warm"] == "RETENU_ETENDU" and v["d_ba_median"] == pytest.approx(10.0)
    assert v["d_ba_positive"] == "10/12"
    v = R.credit_retention_verdict(_rows(S_a=35.0, S_b=[38.0] * 12))          # signe 12/12 mais +3 < 5
    assert v["verdict_warm"] == "RETENU_NEUTRE"
    v = R.credit_retention_verdict(_rows(S_a=35.0, S_b=[45.0] * 9 + [30.0] * 3))   # +10 mais 9/12
    assert v["verdict_warm"] == "RETENU_NEUTRE"


def test_verdict_ERODE_is_symmetric_to_ETENDU():
    v = R.credit_retention_verdict(_rows(S_a=35.0, S_b=[25.0] * 11 + [36.0]))
    assert v["verdict_warm"] == "ERODE" and v["d_ba_negative"] == "11/12"
    v = R.credit_retention_verdict(_rows(S_a=35.0, S_b=[33.0] * 12))          # −2 : dans la bande neutre
    assert v["verdict_warm"] == "RETENU_NEUTRE"


def test_verdict_cold_branch_uses_twice_the_measured_floor():
    """Plancher no-perception 9,0 ([[EDR-WARM-010]], même régime). APPRIS_FROID = ≥ 10/12 seeds au-dessus
    de 2 × plancher ET médiane ≥ 2 × plancher — le plus petit ratio jamais tenu pour un effet ici."""
    v = R.credit_retention_verdict(_rows(S_c=[20.0] * 10 + [12.0, 9.0]))
    assert v["verdict_cold"] == "APPRIS_FROID"
    v = R.credit_retention_verdict(_rows(S_c=[20.0] * 9 + [12.0] * 3))          # 9/12
    assert v["verdict_cold"] == "PAS_APPRIS_FROID"
    v = R.credit_retention_verdict(_rows(S_c=[14.0] * 12))                       # > plancher, < 2× : PAS
    assert v["verdict_cold"] == "PAS_APPRIS_FROID" and v["S_c_median"] == pytest.approx(14.0)


def test_verdict_publishes_the_full_reading_and_the_thresholds():
    v = R.credit_retention_verdict(_rows())
    for k in ("verdict", "verdict_warm", "verdict_cold", "n", "S_a_median", "S_b_median", "S_c_median",
              "d_ba_median", "d_ba_positive", "d_ba_negative", "dose_b_median", "dose_c_median",
              "thresholds", "why"):
        assert k in v, k
    assert v["verdict"] == "LU" and v["thresholds"]["floor"] == 9.0 and v["thresholds"]["harness_min"] == 20.0


def test_load_bassin_returns_the_persisted_dagger_genome_without_io_overlap():
    g = R.load_bassin()
    assert g.W.shape == (172, 172) and g.num_inputs + g.num_outputs <= g.num_nodes
    assert math.isfinite(float(g.W.sum()))


def test_run_arm_refuses_degenerate_args_before_any_world():
    import time
    t0 = time.time()
    for bad in (dict(num_agents=0), dict(ticks_learn=0), dict(ticks_test=0), dict(arm="zzz")):
        kw = dict(seed=2026, arm="b_warm_credit", num_agents=12, ticks_learn=10, ticks_test=10)
        kw.update(bad)
        with pytest.raises(ValueError):
            R.run_arm(**kw)
    assert time.time() - t0 < 0.5
