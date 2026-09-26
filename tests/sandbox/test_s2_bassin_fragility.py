"""P4.18 — `S2-BASSIN-FRAGILITY` : perturbation de W APPARIÉE en déplacement net contre le crédit.

Ce fichier calibre, sans monde : (1) la machinerie des shams à RÉPONSE CONNUE (support et normes exacts du sham
`sign`, L1 du sham `iso`, rendu au bit de ΔW sous des signes truqués, isolation du flux) et son pré-vol, avec un
contre-exemple (machinerie qui fuit -> le pré-vol LÈVE) ; (2) le VERDICT (pur, lignes synthétiques, branches dans
l'ordre imposé) ; (3) les gardes et l'ORCHESTRATION de `run_fragility_seed` par injection à dose connue (aucun monde) ;
(4) la lecture des mesures PUBLIÉES (`published`, `cold_floor`, `seed_row`) sur les JSON suivis.
"""
import copy
import os
import sys
import time

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.evo_runs import s2_bassin_fragility as R  # noqa: E402

try:                                   # les deux côtés (normes communes) : sans torch, le pré-vol (il vérifie aussi l'état
    import torch  # noqa: F401         # RNG de torch) et le monde réel sont SAUTÉS, nommément -- le reste tourne
    _TORCH = True
except ImportError:
    _TORCH = False
requires_torch = pytest.mark.skipif(not _TORCH, reason="torch absent : pré-vol (état RNG torch) et monde réel")

# --------------------------------------------------------------------------------------------------
# 1. Shams — réponse connue.
# --------------------------------------------------------------------------------------------------


def _dW(B=3, N=6, seed=0, sparse=True):
    rng = np.random.default_rng(seed)
    d = rng.standard_normal((B, N, N))
    if sparse:
        d[:, :, : N // 2] = 0.0                    # support partiel, comme le crédit (colonnes lues par la perte)
    return d


def test_sign_sham_keeps_support_and_all_norms_and_only_draws_the_signs():
    d = _dW()
    s = R.sham_delta(d, "sign", R.sham_rng(2026, "b_full", "sign", 0))
    assert np.array_equal(np.abs(s), np.abs(d))                          # support ET magnitudes, au bit
    assert np.array_equal(s[d == 0.0], np.zeros(int((d == 0.0).sum())))  # une entrée nulle reste nulle
    assert not np.array_equal(s, d)                                      # la direction est tirée
    assert 0.3 < float(np.mean(np.sign(s[d != 0]) == np.sign(d[d != 0]))) < 0.7


def test_sign_sham_under_the_credit_signs_returns_the_credit_delta_bit_exact():
    d = _dW()

    class Signes:
        def integers(self, lo, hi, size):
            return (d >= 0.0).astype(np.int64)
    assert np.array_equal(R.sham_delta(d, "sign", Signes()), d)


def test_iso_sham_matches_L1_per_agent_and_accepts_an_explicit_target():
    d = _dW()
    i = R.sham_delta(d, "iso", R.sham_rng(2026, "b_full", "iso", 0))
    assert np.allclose(R.l1_per_agent(i), R.l1_per_agent(d), rtol=1e-12, atol=0)
    assert float((i == 0).mean()) < 1e-6                                 # isotrope : toutes les entrées bougent
    j = R.sham_delta(d, "iso", R.sham_rng(2026, None, "pos", 0), l1_target=7.5)
    assert np.allclose(R.l1_per_agent(j), 7.5, rtol=1e-12, atol=0)


def test_matching_reports_L1_error_and_L2_ratio_and_iso_is_weaker_in_L2_on_a_concentrated_delta():
    d = np.zeros((2, 20, 20))
    d[:, :, 0] = 1.0                                                     # masse concentrée sur UNE colonne
    s = R.sham_delta(d, "sign", R.sham_rng(1, "b_full", "sign", 0))
    i = R.sham_delta(d, "iso", R.sham_rng(1, "b_full", "iso", 0))
    ms, mi = R.matching(d, s), R.matching(d, i)
    assert ms["l1_rel_err_max"] == 0.0 and ms["l2_ratio_median"] == pytest.approx(1.0)
    # une seule colonne : la norme d'opérateur = la L2 de la colonne, INSENSIBLE aux signes (ratio 1 au bit près)
    assert ms["op_ratio_median"] == pytest.approx(1.0) and mi["op_ratio_median"] is not None
    d2 = np.zeros((2, 20, 20))
    d2[:, :, 0] = d2[:, :, 1] = 1.0                                      # rang 1 sur DEUX colonnes (P1.4)
    s2 = R.sham_delta(d2, "sign", R.sham_rng(1, "b_full", "sign", 0))
    assert R.matching(d2, s2)["op_ratio_median"] < 0.95                  # les signes tirés dispersent l'opérateur
    assert mi["l1_rel_err_max"] < 1e-12
    assert mi["l2_ratio_median"] < 0.5                                   # le biais qui fait du sign le PRIMAIRE


def test_sham_refuses_bad_shapes_kinds_and_targets():
    rng = R.sham_rng(1, "b_full", "sign", 0)
    with pytest.raises(ValueError):
        R.sham_delta(np.zeros((4, 4)), "sign", rng)
    with pytest.raises(ValueError):
        R.sham_delta(np.zeros((1, 3, 4)), "sign", rng)
    with pytest.raises(ValueError):
        R.sham_delta(_dW(), "gauss", rng)
    with pytest.raises(ValueError):
        R.sham_delta(_dW(), "iso", rng, l1_target=-1.0)
    with pytest.raises(ValueError):
        R.sham_delta(_dW(), "iso", rng, l1_target=float("nan"))


def test_streams_are_dedicated_reproducible_distinct_and_leave_global_rng_untouched():
    import random
    np.random.seed(7)
    random.seed(7)
    g_np, g_py = np.random.get_state()[1].copy(), random.getstate()
    a = R.sham_rng(2026, "b_const", "sign", 2).integers(0, 1 << 30, 8)
    b = R.sham_rng(2026, "b_const", "sign", 2).integers(0, 1 << 30, 8)
    c = R.sham_rng(2026, "b_const", "sign", 3).integers(0, 1 << 30, 8)
    e = R.sham_rng(2027, "b_const", "sign", 2).integers(0, 1 << 30, 8)
    f = R.sham_rng(2026, "b_eplr", "sign", 2).integers(0, 1 << 30, 8)
    assert np.array_equal(a, b) and not np.array_equal(a, c) and not np.array_equal(a, e)
    assert not np.array_equal(a, f)
    assert np.array_equal(np.random.get_state()[1], g_np) and random.getstate() == g_py


def test_apply_delta_is_bit_exact_on_the_credit_delta():
    rng = np.random.default_rng(3)
    W0 = rng.standard_normal((9, 9)).astype(np.float32)
    Wf = (W0[None] + 0.05 * rng.standard_normal((4, 9, 9))).astype(np.float32)
    dW = Wf.astype(np.float64) - W0.astype(np.float64)[None]
    out = R.apply_delta(W0, dW)
    assert out.dtype == np.float32 and np.array_equal(out, Wf)
    assert np.array_equal(R.apply_delta(W0, np.zeros_like(dW)), np.broadcast_to(W0, Wf.shape))


@requires_torch
def test_preflight_shams_passes_and_publishes_seven_checks():
    out = R.preflight_shams()
    assert set(out) == {"sign_identity_returns_dW", "sign_norms_exact", "iso_l1_matched", "apply_delta_bit_exact",
                        "global_rng_untouched", "stream_reproducible", "streams_distinct"}
    assert all(out.values())


@requires_torch
def test_preflight_shams_refuses_a_leaking_iso_sham(monkeypatch):
    from tools.experiment_preflight import PreflightError
    real = R.sham_delta

    def leaking(dW, kind, rng, l1_target=None):
        out = real(dW, kind, rng, l1_target)
        return out * 1.02 if kind == "iso" else out                     # 2 % de trop : hors appariement
    monkeypatch.setattr(R, "sham_delta", leaking)
    with pytest.raises(PreflightError):
        R.preflight_shams()


@requires_torch
def test_preflight_shams_refuses_a_sham_that_consumes_the_global_rng(monkeypatch):
    from tools.experiment_preflight import PreflightError
    real = R.sham_delta

    def global_consumer(dW, kind, rng, l1_target=None):
        np.random.random()                                               # fuite dans le flux GLOBAL
        return real(dW, kind, rng, l1_target)
    monkeypatch.setattr(R, "sham_delta", global_consumer)
    with pytest.raises(PreflightError):
        R.preflight_shams()


# --------------------------------------------------------------------------------------------------
# 2. Le verdict — branches scellées, dans l'ordre imposé.
# --------------------------------------------------------------------------------------------------

KS = ("full", "tdonly", "const", "eplr", "zero", "tdoff")
NET = {"full": 100.0, "tdonly": 80.0, "const": 20.0, "eplr": 15.0, "zero": 5.0, "tdoff": 60.0}
TR = {"full": 8.0, "tdonly": 8.5, "const": 23.0, "eplr": 17.0, "zero": 35.5, "tdoff": 7.5}


def _v(x, i):
    return x[i] if isinstance(x, (list, tuple)) else x


S_A_DEFAUT = [35.0, 36.0, 37.0] * 4                                    # médiane 36, non dégénéré (branche 3)


def _rows(n=12, S_a=None, S_c=7.5, S_pos=7.0, S_eps=36.0, tr=None, sign=None, iso=None, x2=None, x4=None, resur=None,
          commun=None, **flags):
    S_a = S_A_DEFAUT if S_a is None else S_a
    tr = dict(TR, **(tr or {}))
    sign = dict(tr, **(sign or {}))                                      # défaut : le sham érode AUTANT (FRAGILE)
    iso = dict(sign, **(iso or {}))
    x2 = dict(sign, **(x2 or {}))
    x4 = dict(sign, **(x4 or {}))
    commun = dict(sign, **(commun or {}))                               # défaut : les signes partagés = indépendants
    rows = []
    for i in range(n):
        r = {"seed": 2026 + i, "S_a": float(_v(S_a, i)), "S_c": float(S_c), "S_pos": float(_v(S_pos, i)),
             "S_eps": float(_v(S_eps, i)), "S_eps_draws": [float(_v(S_eps, i))] * 3, "match_eps": 0.0,
             "S_pos_draws": [float(_v(S_pos, i))] * 3,
             "noop_identical": bool(_v(flags.get("noop_identical", True), i))}
        for k in KS:
            r[f"S_tr_{k}"] = float(_v(tr[k], i))
            r[f"S_sign_{k}"] = float(_v(sign[k], i))
            r[f"S_iso_{k}"] = float(_v(iso[k], i))
            r[f"S_sign_{k}_draws"] = [r[f"S_sign_{k}"], r[f"S_sign_{k}"] + 1.0, r[f"S_sign_{k}"]]
            r[f"S_iso_{k}_draws"] = [r[f"S_iso_{k}"]] * 3
            r[f"S_sign_commun_{k}"] = float(_v(commun[k], i))
            r[f"S_sign_commun_{k}_draws"] = [r[f"S_sign_commun_{k}"]] * 3
            r[f"match_sign_commun_{k}"] = 0.0
            r[f"net_{k}"] = NET[k]
            r[f"net_total_{k}"] = 12.0 * NET[k]
            r[f"path_{k}"] = 180.0 * NET[k]
            r[f"match_sign_{k}"] = 0.0
            r[f"match_iso_{k}"] = float(flags.get("match_iso", 1e-15))
            r[f"resur_{k}"] = float((resur or {}).get(k, 10.0))
            r[f"op_sign_{k}"] = 0.75
            for e, src in (("sign_x2", x2), ("sign_x4", x4)):
                r[f"S_{e}_{k}"] = float(_v(src[k], i))
                r[f"S_{e}_{k}_draws"] = [r[f"S_{e}_{k}"]] * 3
                r[f"match_{e}_{k}"] = 0.0
            r[f"repl_{k}"] = bool(_v(flags.get("repl", True), i))
            r[f"transplant_ok_{k}"] = bool(_v(flags.get("transplant_ok", True), i))
        rows.append(r)
    return rows


def test_verdict_refuses_empty_missing_non_finite_and_non_boolean_inputs():
    with pytest.raises(ValueError):
        R.fragility_verdict([])
    rows = _rows()
    rows[3]["S_sign_const"] = float("nan")
    with pytest.raises(ValueError):
        R.fragility_verdict(rows)
    rows = _rows()
    del rows[0]["net_total_eplr"]
    with pytest.raises(ValueError):
        R.fragility_verdict(rows)
    rows = _rows()
    rows[5]["repl_full"] = None                                          # absence -> jamais lue comme « faux »
    with pytest.raises(ValueError):
        R.fragility_verdict(rows)


def test_branch_1_INCOMPLET_wins_over_everything():
    v = R.fragility_verdict(_rows(n=7, noop_identical=False, S_a=3.0))
    assert v["verdict"] == "INCOMPLET" and v["n"] == 7


def test_branch_2_INDETERMINE_NOOP_when_one_seed_does_not_reproduce_a_frozen():
    v = R.fragility_verdict(_rows(noop_identical=[True] * 11 + [False]))
    assert v["verdict"] == "INDETERMINE_NOOP" and "2037" in v["why"]


def test_branch_3_INDETERMINE_HARNAIS_on_a_low_or_DEGENERATE_frozen_bassin():
    assert R.fragility_verdict(_rows(S_a=[14.0, 15.0, 16.0] * 4))["verdict"] == "INDETERMINE_HARNAIS"
    v = R.fragility_verdict(_rows(S_a=36.0))                             # 12 × 36,0 : aucune dispersion
    assert v["verdict"] == "INDETERMINE_HARNAIS" and "dégénérescence" in v["why"] and "None" not in v["why"]


def test_branch_4_INDETERMINE_REPLICATION():
    v = R.fragility_verdict(_rows(repl=[True] * 5 + [False] + [True] * 6))
    assert v["verdict"] == "INDETERMINE_REPLICATION"


def test_branch_5_INDETERMINE_TRANSPLANT():
    v = R.fragility_verdict(_rows(transplant_ok=[False] + [True] * 11))
    assert v["verdict"] == "INDETERMINE_TRANSPLANT"


def test_branch_6_INDETERMINE_APPARIEMENT_on_the_secondary_sham_too():
    assert R.fragility_verdict(_rows(match_iso=0.02))["verdict"] == "INDETERMINE_APPARIEMENT"
    assert R.fragility_verdict(_rows(match_iso=0.009))["verdict"] == "LU"


def test_branch_7_INDETERMINE_INSTRUMENT_when_the_positive_control_does_not_erode():
    v = R.fragility_verdict(_rows(S_pos=34.0))
    assert v["verdict"] == "INDETERMINE_INSTRUMENT" and v["controles"]["pos"]["classe"] == "NEUTRE"


def test_branch_8_INDETERMINE_PREMISSE_when_the_full_transplant_does_not_erode():
    v = R.fragility_verdict(_rows(tr={"full": 34.0}))
    assert v["verdict"] == "INDETERMINE_PREMISSE"


def test_FRAGILE_when_the_sign_sham_erodes_as_much_on_every_eroding_arm():
    v = R.fragility_verdict(_rows())
    assert v["verdict"] == "LU" and v["lecture_globale"] == "FRAGILE"
    assert {k: v["par_bras"][k]["sign"]["lecture"] for k in KS} == {
        "full": "FRAGILE", "tdonly": "FRAGILE", "const": "FRAGILE", "eplr": "FRAGILE", "zero": "INOFFENSIF",
        "tdoff": "FRAGILE"}


def test_DIRECTION_when_the_sign_sham_does_not_erode_and_erodes_less_than_the_credit():
    sign = {k: 35.0 for k in KS}
    v = R.fragility_verdict(_rows(sign=sign))
    assert v["lecture_globale"] == "DIRECTION"
    assert v["par_bras"]["full"]["sign"]["lecture"] == "DIRECTION"
    assert v["par_bras"]["full"]["sign"]["moins_erode_que_le_credit"] is True


def test_PARTIEL_when_the_sham_erodes_but_clearly_less_counts_on_the_direction_side():
    sign = {"full": 20.0, "tdonly": 20.0, "const": 30.0, "eplr": 25.0, "tdoff": 16.0}  # érode mais ≥ +5 au-dessus
    v = R.fragility_verdict(_rows(sign=sign))
    assert v["par_bras"]["full"]["sign"]["lecture"] == "PARTIEL"
    assert v["lecture_globale"] == "DIRECTION"


def test_MIXTE_PAR_AMPLITUDE_when_direction_at_small_nets_and_fragile_at_large_nets():
    sign = {"const": 35.0, "eplr": 35.0, "tdoff": 35.0}                  # full/tdonly : FRAGILE (sham = transplant)
    v = R.fragility_verdict(_rows(sign=sign))
    assert v["lecture_globale"] == "MIXTE_PAR_AMPLITUDE"


def test_MIXTE_when_the_split_is_not_ordered_by_amplitude():
    sign = {"full": 35.0, "tdonly": 35.0}                                # direction aux GRANDS nets, fragile aux petits
    v = R.fragility_verdict(_rows(sign=sign))
    assert v["lecture_globale"] == "MIXTE"


def test_the_contrast_needs_11_of_12_and_5_ticks_not_the_single_test_10_of_12():
    sign = dict(TR, full=[20.0] * 10 + [5.0] * 2)                        # +12 sur 10/12 seulement
    v = R.fragility_verdict(_rows(sign=sign))
    assert v["par_bras"]["full"]["sign"]["moins_erode_que_le_credit"] is False
    # revue v4 P1.1 : un contraste MÉDIAN de +12 n'est pas « autant » -> ni FRAGILE ni PARTIEL
    assert v["par_bras"]["full"]["sign"]["lecture"] == "NON_TRANCHE"
    sign = dict(TR, full=[12.0] * 12)                                    # 12/12 mais +4 : sous la marge
    assert R.fragility_verdict(_rows(sign=sign))["par_bras"]["full"]["sign"]["lecture"] == "FRAGILE"
    sign = dict(TR, full=[20.0] * 11 + [5.0])                            # 11/12 et +12 : moins érodé
    assert R.fragility_verdict(_rows(sign=sign))["par_bras"]["full"]["sign"]["moins_erode_que_le_credit"] is True


def test_PROTECTRICE_when_the_credit_does_not_erode_but_its_sham_does():
    v = R.fragility_verdict(_rows(sign={"zero": 20.0}))
    assert v["par_bras"]["zero"]["transplant"]["classe"] == "NEUTRE"
    assert v["par_bras"]["zero"]["sign"]["lecture"] == "PROTECTRICE"


def test_the_secondary_iso_sham_is_published_and_never_changes_the_verdict():
    base = R.fragility_verdict(_rows())
    alt = R.fragility_verdict(_rows(iso={k: 36.0 for k in KS}))
    assert base["lecture_globale"] == alt["lecture_globale"] == "FRAGILE"
    assert alt["secondaire_iso"]["full"]["lecture_hors_famille"] == "DIRECTION"


def test_E19_the_episodic_direction_contrast_that_survives_a_10x_step_keeps_its_reading():
    # paire LISIBLE : b_tdoff à 20 (saturation 0,56), b_eplr à 17 ; sham inerte (35) aux deux pas
    v = R.fragility_verdict(_rows(tr={"tdoff": 20.0}, sign={k: 35.0 for k in KS}))
    e = v["e19"]
    assert e["lisible"] is True and e["a_defendre"] is True and e["invariant"] is True
    assert e["fractions_epargnees"] == {"0.04": pytest.approx(15.0 / 16.0), "0.004": pytest.approx(18.0 / 19.0)}
    assert v["par_bras"]["tdoff"]["sign"]["lecture"] == "DIRECTION" and v["lecture_globale"] == "DIRECTION"


def test_E19_a_direction_contrast_that_closes_under_the_setting_becomes_DIRECTION_DEPEND_DU_REGLAGE():
    sign = {k: 35.0 for k in KS}
    sign["eplr"] = 18.0                                                  # le sham n'épargne que 1/19 de la perte à 0,004
    v = R.fragility_verdict(_rows(tr={"tdoff": 20.0}, sign=sign))
    assert v["e19"]["lisible"] is True and v["e19"]["invariant"] is False and "artefact" in v["e19"]["raison"]
    for k in ("tdoff", "eplr"):
        assert v["par_bras"][k]["sign"]["lecture"] == "DIRECTION_DEPEND_DU_REGLAGE"
    assert v["par_bras"]["tdoff"]["sign"]["lecture_avant_E19"] == "DIRECTION"
    assert v["par_bras"]["eplr"]["sign"]["lecture_avant_E19"] == "FRAGILE"
    assert v["lecture_globale"] == "MIXTE"


def test_E19_at_the_floor_is_run_and_published_but_never_relabels__review_v4_P1_2():
    sign = {k: 35.0 for k in KS}
    sign["eplr"] = 18.0
    v = R.fragility_verdict(_rows(sign=sign))                            # b_tdoff à 7,5 = S_c : saturé
    e = v["e19"]
    assert e["lisible"] is False and "plancher" in e["raison_illisible"] and e["invariant"] is not None
    assert v["par_bras"]["tdoff"]["sign"]["lecture"] == "DIRECTION"      # rien n'est réétiqueté
    assert v["par_bras"]["eplr"]["sign"]["lecture"] == "FRAGILE"


def test_E19_is_silent_when_no_arm_shows_a_direction_gap():
    v = R.fragility_verdict(_rows(tr={"tdoff": 20.0}))                   # sham = crédit : rien à défendre
    assert v["e19"]["a_defendre"] is False and v["e19"]["lisible"] is False and v["lecture_globale"] == "FRAGILE"
    assert "rien à défendre" in v["e19"]["raison_illisible"]


def test_E19_exact_two_thirds_closure_is_kept_invariant__review_v4_P4_4():
    out = R._garde_e19({"tdoff": {"S_tr_median": 6.0, "saturation_transplant_median": 0.3,
                                  "sign": {"S_median": 21.0, "lecture": "DIRECTION"}},
                        "eplr": {"S_tr_median": 6.0, "saturation_transplant_median": 0.3,
                                 "sign": {"S_median": 11.0, "lecture": "DIRECTION"}}}, S_a_median=36.0)
    assert out["closure"] == pytest.approx(2.0 / 3.0) and out["invariant"] is True     # 15/30 contre 5/30


def test_E19_publishes_both_dose_factors_of_the_pair__review_v4_P7_2():
    e = R.fragility_verdict(_rows())["e19"]
    assert e["pas_effectif_par_agent"] == {"tdoff": pytest.approx(0.04 / 12), "eplr": pytest.approx(0.004 / 12)}
    assert e["masse_gradient_ratio_median"] == pytest.approx((15.0 * 180 / 0.004) / (60.0 * 180 / 0.04))


def test_NON_TRANCHE_when_the_sham_neither_erodes_nor_is_clearly_less_eroded__review_P5a():
    """Le scénario EXACT de la revue (P5.a) : le sham reste au niveau du no-op sur 10 seeds, érode sur 2 ; le
    contraste sham − crédit rate 11/12. Avant correction : FRAGILE (« toute perturbation détruit ») sans érosion."""
    # crédit complet à −10 (ERODE 12/12) ; sham au niveau du no-op sur 10 seeds, sous le crédit sur 2 : contraste +10
    # sur 10/12 seulement (sous 11/12) — le chiffre exact de la sonde p5 de la revue
    v = R.fragility_verdict(_rows(tr={"full": 26.0}, sign={"full": [36.0] * 10 + [25.0] * 2}))
    b = v["par_bras"]["full"]["sign"]
    assert b["classe_vs_S_a"] == "NEUTRE" and b["moins_erode_que_le_credit"] is False
    assert b["lecture"] == "NON_TRANCHE" and v["lecture_globale"] == "MIXTE"


def test_CRETE_A_TOUTE_ECHELLE_when_even_eps_erodes():
    v = R.fragility_verdict(_rows(S_eps=10.0))
    assert v["verdict"] == "LU" and v["lecture_globale"] == "CRETE_A_TOUTE_ECHELLE"
    assert v["controles"]["eps"]["classe"] == "ERODE"


def test_INDETERMINE_INSTRUMENT_when_eps_is_not_clearly_less_eroded_than_the_full_credit():
    """Contrôle positif de DIRECTION : un eps qui ne se distingue pas du crédit complet sur 11/12 seeds prouve que le
    contraste apparié ne sait pas voir un écart connu."""
    v = R.fragility_verdict(_rows(S_eps=[36.0] * 9 + [8.0] * 3))
    assert v["controles"]["eps"]["classe"] == "NEUTRE"
    assert v["verdict"] == "INDETERMINE_INSTRUMENT" and "DIRECTION" in v["why"]


def test_the_band_is_confronted_to_the_contrast_and_SAID__review_P6a():
    v = R.fragility_verdict(_rows())
    assert v["par_bras"]["full"]["sign"]["dans_la_bande"] is True        # sham = crédit : contraste 0
    assert "DANS sa bande de tirage" in v["why"]
    sign = {k: 35.0 for k in KS}                                         # +27 sur un bruit de tirage d'un tick
    v = R.fragility_verdict(_rows(sign=sign))
    assert v["par_bras"]["full"]["sign"]["dans_la_bande"] is False


def test_the_sign_scale_publishes_the_first_scale_that_erodes():
    sign = {k: 35.0 for k in KS}
    v = R.fragility_verdict(_rows(sign=sign, x2={k: 34.0 for k in KS}, x4={k: 12.0 for k in KS}))
    e = v["par_bras"]["const"]["echelle_sign"]
    assert e["sign_x2"]["classe_vs_S_a"] == "NEUTRE" and e["sign_x4"]["classe_vs_S_a"] == "ERODE"
    assert e["premiere_echelle_qui_erode"] == 4.0
    assert v["lecture_globale"] == "DIRECTION"                           # l'échelle est HORS verdict


def test_body_guard_can_FAIL_when_the_body_is_recomputed_on_the_posed_W__review_P10c():
    from src.agents.mamba_agent import MambaAgent
    from tools.experiment_preflight import phenotype_of
    bassin = R.load_bassin()
    a = MambaAgent()
    a.from_genome(bassin)
    R._assert_body_is_bassin([a], phenotype_of(bassin), "témoin")        # corps du bassin : passe
    W = np.array(a.genome.W, copy=True)
    W[0:5] += 0.5                                                        # lignes du corps
    a.genome.W = W
    R._assert_body_is_bassin([a], phenotype_of(bassin), "témoin")        # sans recalcul : passe encore
    a.update_phenotype()                                                 # recalcul sur le W posé
    with pytest.raises(AssertionError):
        R._assert_body_is_bassin([a], phenotype_of(bassin), "témoin")


def test_the_sign_threshold_is_tied_to_the_declared_family__review_v3_P4_3():
    ok, queue, alpha = R.seuil_tient(11, 12, 14)
    assert ok and queue == pytest.approx(13 / 4096) and alpha == pytest.approx(0.05 / 14)
    assert R.seuil_tient(11, 12, 15)[0] is True
    assert R.seuil_tient(11, 12, 16)[0] is False                        # 0,00317 > 0,003125
    assert R.seuil_tient(10, 12, 14)[0] is False                        # le seuil de P4.16 ne tient pas ici


def test_iso_readings_and_the_scale_are_labelled_out_of_family__review_v3_P4_4():
    v = R.fragility_verdict(_rows())
    iso = v["secondaire_iso"]["full"]
    assert "lecture" not in iso and iso["lecture_hors_famille"] == "FRAGILE" and iso["hors_famille"] is True
    assert v["par_bras"]["full"]["echelle_sign"]["sign_x2"]["hors_famille"] is True


def test_qualifiers_saturation_eps_floor_and_required_fraction_are_published_and_said__review_v3():
    v = R.fragility_verdict(_rows())                                     # FRAGILE partout, saturation 0,98
    q = v["par_bras"]["full"]["qualificatifs"]
    assert q["suffisance_seulement"] is True and q["au_dela_du_plancher_eps"] is True
    assert q["fraction_de_perte_requise_pour_FRAGILE"] == pytest.approx(1.0 - 5.0 / 28.0)
    assert "SUFFISANCE" in v["why"]
    v = R.fragility_verdict(_rows(S_eps=[29.0] * 10 + [40.0] * 2, tr={"const": 26.0}, sign={"const": 26.0}))
    q = v["par_bras"]["const"]["qualificatifs"]                          # eps perd 7 sur 10 seeds : pas ERODE (10/12)
    assert v["controles"]["eps"]["classe"] == "NEUTRE" and v["lecture_globale"] is not None
    assert v["par_bras"]["const"]["sign"]["lecture"] == "FRAGILE" and q["au_dela_du_plancher_eps"] is False
    assert "plancher eps" in v["why"]


def test_eps_equal_to_noop_is_counted_because_9b_then_mirrors_branch_8__review_v3_P5_1():
    v = R.fragility_verdict(_rows(S_eps=S_A_DEFAUT))
    assert v["controles"]["eps"]["seeds_eps_egal_noop"] == "12/12"
    assert R.fragility_verdict(_rows())["controles"]["eps"]["seeds_eps_egal_noop"] == "4/12"


def test_E19_publishes_what_the_pair_does_not_separate__review_v3_P1_1_P7_2():
    e = R.fragility_verdict(_rows())["e19"]
    assert e["chemin_ratio_median"] == pytest.approx(60.0 / 15.0) and e["net_ratio_median"] == pytest.approx(4.0)
    assert set(e["resurrections_medianes"]) == {"tdoff", "eplr"} and "létalité" in e["etiquette"]


def test_the_29_percent_sham_of_review_v4_P1_1_is_NON_TRANCHE_not_FRAGILE():
    """Crédit à −28 (12/12) ; sham à −8 sur 10 seeds (contraste +20), égal au crédit sur 2 : il ne reproduit que
    29 % de la perte. Avant v5 : FRAGILE (« toute perturbation détruit »). Désormais : NON_TRANCHE."""
    v = R.fragility_verdict(_rows(sign={"full": [28.0] * 10 + [8.0] * 2}))
    b = v["par_bras"]["full"]["sign"]
    assert b["classe_vs_S_a"] == "ERODE" and b["contraste_vs_transplant_mediane"] == 20.0
    assert b["moins_erode_que_le_credit"] is False and b["lecture"] == "NON_TRANCHE"


def test_the_contrast_band_is_measured_on_the_draws_and_the_eps_contrast_has_one__review_v4_P6_2_P6_3():
    v = R.fragility_verdict(_rows())
    assert v["par_bras"]["full"]["sign"]["dans_la_bande"] is True                      # contraste 0 : dans la bande
    assert R._bande_contraste([[1.0, 3.0, 2.0, 0.0, 4.0]] * 12, [2.0] * 12) > 0.0       # tirages bruités : une bande
    assert R._bande_contraste([[5.0, 5.0, 5.0]] * 12, [5.0] * 12) == pytest.approx(0.0) # tout identique : aucune
    assert R._bande_contraste([[1.0]] * 12, [0.0] * 12) is None                        # un seul tirage : inconnu
    assert R._bande_contraste([[1.0, 2.0]] * 11 + [[1.0, 2.0, 3.0]], [0.0] * 12) is None   # longueurs inégales
    b1 = R._bande_contraste([[1.0, 2.0, 1.0]] * 12, [0.0] * 12)
    assert b1 == R._bande_contraste([[1.0, 2.0, 1.0]] * 12, [0.0] * 12)               # flux PRIVÉ : reproductible


def test_power_ceiling_of_MOINS_and_untested_direction_control_are_published__review_v4_P5():
    v = R.fragility_verdict(_rows(tr={"const": [23.0] * 11 + [40.0]}, S_eps=S_A_DEFAUT))
    q = v["par_bras"]["const"]["qualificatifs"]
    assert q["moins_max_atteignable"] == "11/12" and q["moins_atteignable_avec_marge"] is False
    assert v["par_bras"]["full"]["qualificatifs"]["moins_atteignable_avec_marge"] is True
    assert v["controles"]["eps"]["controle_direction_non_eprouve"] is True


def _bande_demi_v5(draws, refs):
    """La bande de DEMI-TIRAGES de la v5, gardée ici comme CONTRE-EXEMPLE : le témoin de couverture doit la refuser."""
    pair = [float(np.median(d[0::2])) - t for d, t in zip(draws, refs)]
    imp = [float(np.median(d[1::2])) - t for d, t in zip(draws, refs)]
    return abs(float(np.median(pair)) - float(np.median(imp)))


def _couverture_du_nul(bande, sigma, reps, seed=7):
    rng = np.random.default_rng(seed)
    ok = 0
    for _ in range(reps):
        refs = np.round(rng.uniform(7, 45, size=12) * 2) / 2
        draws = [np.round((r + rng.normal(0, sigma, size=5)) * 2) / 2 for r in refs]
        m = float(np.median([np.median(d) - r for d, r in zip(draws, refs)]))
        ok += abs(m) <= bande([list(d) for d in draws], list(refs)) + 1e-12
    return ok / reps


def test_the_draw_band_COVERS_a_known_null_and_the_v5_half_draw_band_does_not__review_v5_P6a():
    """Contraste NUL connu (12 seeds × 5 tirages bruités, arrondis au demi-tick) : la bande doit le couvrir >= 95 %
    du temps. La bande de demi-tirages de la v5 le laissait dehors 14-31 % du temps (contre-exemple gelé)."""
    for sigma in (1.0, 2.0, 4.0):
        assert _couverture_du_nul(R._bande_contraste, sigma, reps=150) >= 0.95, sigma
    assert _couverture_du_nul(_bande_demi_v5, 2.0, reps=150) < 0.85


def _bande_v6(draws, refs, b=2000, q=0.95):
    """La bande BOOTSTRAP de la v6 (tirages seuls, référence tenue pour EXACTE), gardée comme second CONTRE-EXEMPLE."""
    d = np.asarray(draws, dtype=np.float64)
    ref = np.asarray(refs, dtype=np.float64)
    m = float(np.median(np.median(d, axis=1) - ref))
    rng = np.random.default_rng(np.random.SeedSequence([4181, d.shape[0], d.shape[1]]))
    idx = rng.integers(0, d.shape[1], size=(b,) + d.shape)
    rs = np.take_along_axis(np.broadcast_to(d, (b,) + d.shape), idx, axis=2)
    mb = np.median(np.median(rs, axis=2) - ref[None], axis=1)
    return float(np.quantile(np.abs(mb - m), q))


def _couverture_du_nul_echangeable(bande, sigma, reps, seed=7):
    """Nul ÉCHANGEABLE (hypothèse FRAGILE) : la référence est UNE réalisation de plus de la même loi que les tirages."""
    rng = np.random.default_rng(seed)
    ok = 0
    for _ in range(reps):
        c = np.round(rng.uniform(7, 45, size=12) * 2) / 2
        draws = [list(np.round((x + rng.normal(0, sigma, size=5)) * 2) / 2) for x in c]
        refs = list(np.round((c + rng.normal(0, sigma, size=12)) * 2) / 2)
        m = float(np.median([np.median(d) - r for d, r in zip(draws, refs)]))
        ok += abs(m) <= bande(draws, refs) + 1e-12
    return ok / reps


def test_the_draw_band_COVERS_the_EXCHANGEABLE_null_and_the_v6_bootstrap_does_not__review_v6_P6a():
    """Sous FRAGILE, la greffe n'est qu'une réalisation de plus : la bande v6 (référence exacte) laissait ce nul dehors
    8-13 % du temps ; la bande v7 (pool tirages + référence) le couvre. Témoin de RÉGRESSION à graine fixe, PAS une
    garantie de couverture (revue v9 P6.a : à 150 répétitions l'erreur Monte-Carlo vaut ≈ 0,018, et sur 8 graines la
    couverture va de 0,927 à 0,98) : la couverture qui fait foi est MESURÉE à 1000 répétitions dans
    results/s2_bassin_fragility_calibration_bande.json ; le seuil 0,92 tient sur toutes les graines rejouées."""
    for sigma in (2.0, 4.0):
        assert _couverture_du_nul_echangeable(R._bande_contraste, sigma, reps=150) >= 0.92, sigma
    assert _couverture_du_nul_echangeable(_bande_v6, 4.0, reps=150) < 0.93


# Contre-exemple à RÉPONSE CONNUE (Master 2) : un contraste NUL par construction -- 12 seeds, référence tirée,
# 5 tirages = référence + N(0, σ = 2) arrondis au demi-tick (numpy default_rng(102), valeurs GELÉES ici). Le contraste
# observé vaut +0,5 : du bruit de tirage, rien d'autre.
_NUL_REFS = [13.0, 29.5, 38.5, 18.5, 33.0, 24.5, 41.0, 28.5, 44.5, 16.0, 11.0, 20.0]
_NUL_DRAWS = [[12.5, 12.0, 12.5, 15.0, 12.0], [27.5, 31.0, 32.5, 28.5, 30.0], [35.5, 40.5, 43.5, 40.0, 38.5],
              [14.5, 18.0, 14.5, 20.5, 22.5], [36.0, 33.5, 34.0, 32.0, 33.5], [25.0, 24.5, 19.0, 25.0, 25.5],
              [39.5, 42.0, 42.5, 36.5, 43.0], [27.5, 26.0, 29.0, 27.0, 27.5], [42.5, 43.0, 42.0, 43.0, 42.0],
              [13.0, 18.0, 16.0, 17.0, 19.5], [12.5, 11.0, 8.5, 12.5, 12.0], [22.0, 19.5, 19.0, 15.5, 21.0]]


def test_a_KNOWN_null_is_left_OUT_by_the_v5_half_draw_band_and_COVERED_by_the_draw_band__review_v5_P6a():
    m = float(np.median([np.median(d) - r for d, r in zip(_NUL_DRAWS, _NUL_REFS)]))
    assert m == 0.5                                                      # le nul observé
    assert _bande_demi_v5(_NUL_DRAWS, _NUL_REFS) == 0.0                  # v5 : « hors de la bande » -> signal FABRIQUÉ
    assert abs(m) > _bande_demi_v5(_NUL_DRAWS, _NUL_REFS)
    b = R._bande_contraste(_NUL_DRAWS, _NUL_REFS)
    assert b >= 1.0 and abs(m) <= b                                      # bootstrap : couvert, avec une marge


def test_the_draw_band_still_SEES_a_known_effect__review_v5_P6a():
    """Spécificité sans aveuglement : un contraste de 4 ticks sous un bruit de tirage σ = 2 sort de la bande."""
    rng = np.random.default_rng(11)
    hors = 0
    for _ in range(100):
        refs = np.round(rng.uniform(7, 45, size=12) * 2) / 2
        draws = [list(np.round((r + 4.0 + rng.normal(0, 2.0, size=5)) * 2) / 2) for r in refs]
        m = float(np.median([np.median(d) - r for d, r in zip(draws, refs)]))
        hors += abs(m) > R._bande_contraste(draws, list(refs))
    assert hors >= 90


def test_bands_against_S_a_are_published_for_the_shams_and_both_controls__review_v5_P6b():
    v = R.fragility_verdict(_rows())
    s = v["par_bras"]["full"]["sign"]
    assert s["bande_vs_S_a"] > 0.0 and s["dans_la_bande_vs_S_a"] is False            # −28 : hors du bruit de tirage
    assert v["controles"]["pos"]["bande_vs_S_a"] > 0.0                                 # la référence entre au pool
    assert v["controles"]["pos"]["dans_la_bande_vs_S_a"] is False                      # −29 : hors de la bande
    assert v["controles"]["eps"]["dans_la_bande_vs_S_a"] is True                       # eps à 36 = S_a (médiane)
    assert v["secondaire_iso"]["full"]["bande_vs_S_a"] is not None


def test_the_untested_direction_control_is_flagged_from_11_of_12_and_SAID__review_v5_P5_2():
    S_eps = list(S_A_DEFAUT[:11]) + [30.0]                               # eps = no-op au bit sur 11/12 seeds
    v = R.fragility_verdict(_rows(S_eps=S_eps, sign={k: 35.0 for k in KS}))
    assert v["controles"]["eps"]["controle_direction_non_eprouve"] is True
    assert v["lecture_globale"] == "DIRECTION" and "NON ÉPROUVÉ" in v["why"]
    # revue v6 P5.a : l'inertie se juge par la BANDE, pas par == -- un eps à un demi-tick du no-op reste inerte
    rows = _rows(S_eps=[a + 0.5 for a in S_A_DEFAUT], sign={k: 35.0 for k in KS})    # décalage chaotique, bruité
    for r in rows:
        e = r["S_eps"]
        r["S_eps_draws"] = [e - 1.0, e, e + 0.5, e, e - 0.5]
    v = R.fragility_verdict(rows)
    assert v["controles"]["eps"]["seeds_eps_egal_noop"] == "0/12"
    assert v["controles"]["eps"]["eps_inerte_par_la_bande"] is True
    assert v["controles"]["eps"]["controle_direction_non_eprouve"] is True and "NON ÉPROUVÉ" in v["why"]
    rows = _rows(S_eps=[a - 4.0 for a in S_A_DEFAUT], sign={k: 35.0 for k in KS})   # eps s'écarte, sans éroder
    for r in rows:
        e = r["S_eps"]
        r["S_eps_draws"] = [e - 0.5, e, e, e, e + 0.5]
    v = R.fragility_verdict(rows)
    assert v["controles"]["eps"]["eps_inerte_par_la_bande"] is False and v["controles"]["eps"]["classe"] == "NEUTRE"
    assert v["controles"]["eps"]["eps_inerte"] is False
    # revue v7 P5.1 : même un eps qui s'écarte laisse 9b passer par ARITHMÉTIQUE (écart de la branche 8 + écart d'eps) --
    # le contrôle de DIRECTION n'est éprouvé dans AUCUN cas : non éprouvé par construction, et dit
    assert v["controles"]["eps"]["controle_direction_non_eprouve"] is True and "par construction" in v["why"]
    assert v["lecture_globale"] == "DIRECTION"


def test_MIXTE_AMPLITUDE_OU_LETALITE_when_the_amplitude_split_is_also_the_lethality_split__review_v5_P7_1():
    """Les résurrections PUBLIÉES : fragiles (full 10, tdonly 8, tdoff 3,5) meurent moins que les orientés (const 65,5,
    eplr 16,5) -- la partition par le net est aussi celle de la létalité : rien n'est attribué à l'amplitude."""
    resur = {"full": 10.0, "tdonly": 8.0, "const": 65.5, "eplr": 16.5, "zero": 179.0, "tdoff": 3.5}
    v = R.fragility_verdict(_rows(sign={"const": 35.0, "eplr": 35.0}, resur=resur))
    assert v["partition_par_letalite"] is True and v["lecture_globale"] == "MIXTE_AMPLITUDE_OU_LETALITE"
    assert "LÉTALITÉ" in v["why"] and "résurrections 65.5" in v["why"]
    resur = dict(resur, eplr=5.0)                                        # létalités entrelacées : l'amplitude reste lue
    v = R.fragility_verdict(_rows(sign={"const": 35.0, "eplr": 35.0}, resur=resur))
    assert v["partition_par_letalite"] is False and v["lecture_globale"] == "MIXTE_PAR_AMPLITUDE"


def test_a_DIRECTION_of_the_E19_pair_is_said_NOT_DEFENDED_against_the_step_when_the_guard_is_illegible__review_v5_P5_1():
    v = R.fragility_verdict(_rows(sign={"eplr": 35.0}))                  # b_tdoff à 7,5 = S_c : saturé, illisible
    assert v["e19"]["lisible"] is False
    assert v["par_bras"]["eplr"]["sign"]["lecture"] == "DIRECTION"
    assert v["par_bras"]["eplr"]["sign"]["defendu_contre_le_pas"] is False
    assert v["why"].startswith("NON DÉFENDU contre le pas")                   # Master 2 : AVANT les lectures
    assert "eplr" in v["why"].split(" ; ")[0]
    assert "defendu_contre_le_pas" not in v["par_bras"]["full"]["sign"]            # hors de la paire : sans objet


def test_the_operator_norm_of_the_draw_is_published_with_its_x2_crossing__review_v5_P1a():
    v = R.fragility_verdict(_rows(sign={k: 35.0 for k in KS}, x2={k: 34.0 for k in KS}))
    s = v["par_bras"]["full"]["sign"]
    assert s["op_ratio_tirage_sur_credit_median"] == pytest.approx(0.75)
    assert s["op_ratio_tirage_x2_sur_credit_median"] == pytest.approx(1.5)
    assert v["par_bras"]["full"]["echelle_sign"]["sign_x2"]["contraste_vs_transplant_mediane"] == pytest.approx(26.0)


def test_a_contrast_without_any_dispersion_is_flagged_DEGENERATE__review_v5_P5_3():
    v = R.fragility_verdict(_rows())                                     # sham = crédit partout : c ≡ 0
    assert v["par_bras"]["full"]["sign"]["contraste_degenere"] is not None and "DÉGÉNÉRÉ" in v["why"]
    v = R.fragility_verdict(_rows(sign={"full": [8.0] * 11 + [9.0]}))
    assert v["par_bras"]["full"]["sign"]["contraste_degenere"] is None


def test_the_seed_command_REFUSES_missing_cells_before_any_world__review_v5_P10b(tmp_path, monkeypatch):
    d = tmp_path / "cells"
    d.mkdir()
    monkeypatch.setattr(R, "cells_dir", lambda root=None: str(d))
    monkeypatch.setattr(R, "run_fragility_seed", lambda *a, **k: pytest.fail("un monde a été construit"))
    t0 = time.time()
    with pytest.raises(RuntimeError, match="cellules absentes"):
        R._tache_seed(2026, 200, 100)
    assert time.time() - t0 < 0.5 and R.cellules_manquantes(2026) == list(R.ARMS)
    with pytest.raises(RuntimeError, match="ne rejoue JAMAIS"):          # la relecture seule ne rejoue rien non plus
        R._cellule_relue(2026, "b_zero", ticks_learn=200, ticks_test=100)
    assert not list(d.iterdir())                                         # rien n'a été écrit


def test_the_population_rebuild_counter_counts_torch_constructions_at_known_answer_and_restores__review_v6_P8a():
    import src.agents.backend as backend
    orig = backend.make_population
    calls = []
    backend.make_population = lambda agents, backend="legacy", world_model=None: calls.append((len(agents), backend))
    try:
        with R.compter_reconstructions() as c:
            backend.make_population([1, 2, 3], backend="torch")
            backend.make_population([1, 2], backend="torch")
            backend.make_population([1], backend="legacy")                # le chemin legacy n'est pas compté
        assert c == {"constructions": 2, "B": [3, 2]} and calls == [(3, "torch"), (2, "torch"), (1, "legacy")]
        assert backend.make_population is not orig                           # l'enveloppe est bien retirée…
        with pytest.raises(RuntimeError):
            with R.compter_reconstructions():
                raise RuntimeError("panne au milieu d'une phase 2")
    finally:
        backend.make_population = orig
    assert backend.make_population is orig                                   # …et l'original restauré


@requires_torch
def test_the_optimizer_step_is_MEASURED_at_construction_and_the_class_is_restored__review_v6_P10c():
    from src.agents.backend_torch import TorchPopulationModel as T
    from src.agents.mamba_agent import MambaAgent
    orig = T.__init__
    with R.mesurer_pas_optimiseur() as pas:
        T([MambaAgent() for _ in range(2)])                                  # défaut du constructeur
        T([MambaAgent() for _ in range(2)], lr=0.004)
    assert pas == [pytest.approx(0.04), pytest.approx(0.004)] and T.__init__ is orig


def test_the_x2_scale_is_descriptive_and_decides_nothing__review_v6_P4a():
    v = R.fragility_verdict(_rows(sign={k: 35.0 for k in KS}, x2={k: 34.0 for k in KS}))
    e = v["par_bras"]["full"]["echelle_sign"]["sign_x2"]
    assert e["descriptif_ne_tranche_rien"] is True and e["contraste_positifs"] == "12/12"
    assert v["lecture_globale"] == "DIRECTION"
    v2 = R.fragility_verdict(_rows(sign={k: 35.0 for k in KS}, x2={k: 8.0 for k in KS}))   # ×2 érode : rien ne change
    assert v2["lecture_globale"] == "DIRECTION"


def test_control_bands_and_the_9b_band_are_SAID_in_the_motive__review_v6_P10a():
    v = R.fragility_verdict(_rows(sign={k: 35.0 for k in KS}))
    assert "contrôles contre S_a DANS leur bande de tirage : ['eps']" in v["why"]


def test_PROTECTRICE_needs_the_tested_PLUS_contrast_not_two_classes__review_v7_P4_1():
    """Le cas injecté de la revue : greffe b_zero NEUTRE, tirage 4,5 ticks SOUS la greffe sur 12/12 seeds (tirage
    ERODE contre S_a) -- avant v8, PROTECTRICE sans aucun test sur c ; désormais NON_TRANCHE (|c| < 5)."""
    tr = {"zero": [a - 0.75 for a in S_A_DEFAUT]}
    v = R.fragility_verdict(_rows(tr=tr, sign={"zero": [a - 5.25 for a in S_A_DEFAUT]}))
    b = v["par_bras"]["zero"]
    assert b["transplant"]["classe"] == "NEUTRE" and b["sign"]["classe_vs_S_a"] == "ERODE"
    assert b["sign"]["plus_erode_que_le_credit"] is False and b["sign"]["lecture"] == "NON_TRANCHE"
    v = R.fragility_verdict(_rows(tr=tr, sign={"zero": 20.0}))            # nettement plus érodé : PROTECTRICE tient
    assert v["par_bras"]["zero"]["sign"]["plus_erode_que_le_credit"] is True
    assert v["par_bras"]["zero"]["sign"]["lecture"] == "PROTECTRICE"
    assert R.seuil_tient(11, 12, R.FAMILLE)[0] is True and R.FAMILLE == 15


def test_band_coverage_measure_has_known_answers_at_both_extremes__review_v7_P6_2():
    inf = R.mesurer_couverture_bande(bande=lambda d, r: float("inf"), reps=20, sigmas=(1.0,), effets=(4.0,))
    nul = R.mesurer_couverture_bande(bande=lambda d, r: -1.0, reps=20, sigmas=(1.0,), effets=(4.0,))
    for k in ("exacte_sigma_1.0", "echangeable_sigma_1.0"):
        assert inf["couverture"][k]["homogene"]["taux"] == 1.0 and inf["couverture"][k]["heterogene"]["taux"] == 1.0
        assert nul["couverture"][k]["homogene"]["taux"] == 0.0
    assert inf["puissance"]["effet_4.0_sigma_2"]["taux"] == 0.0 and nul["puissance"]["effet_4.0_sigma_2"]["taux"] == 1.0
    reel = R.mesurer_couverture_bande(reps=60, sigmas=(2.0,), effets=(4.0,))       # la bande EXÉCUTÉE
    assert reel["couverture"]["echangeable_sigma_2.0"]["homogene"]["taux"] >= 0.9
    assert reel["puissance"]["effet_4.0_sigma_2"]["taux"] >= 0.9


def test_sign_commun_shares_ONE_sign_matrix_across_agents_and_keeps_every_norm__review_v8_P8_1():
    d = _dW(B=4, N=6, seed=3)
    c = R.sham_delta(d, "sign_commun", np.random.default_rng(0))
    assert np.array_equal(np.abs(c), np.abs(d))                                   # magnitudes et support exacts
    sg = np.sign(c[:, :, 3:])                                                      # support non nul
    assert np.all(sg == sg[0:1])                                                   # UNE matrice de signes pour tous
    i = R.sham_delta(d, "sign", np.random.default_rng(0))
    assert not np.all(np.sign(i[:, :, 3:]) == np.sign(i[0:1, :, 3:]))              # contre-exemple : l'indépendant
    assert R.KINDS.index("sign_commun") == len(R.KINDS) - 1                         # flux ajouté EN QUEUE


def test_the_shared_sign_sham_is_published_out_of_family_and_a_sensitive_issue_is_SAID__review_v8_P8_1():
    v = R.fragility_verdict(_rows(sign={k: 35.0 for k in KS}))
    c = v["secondaire_commun"]["full"]
    assert c["hors_famille"] is True and c["descriptif_ne_tranche_rien"] is True and c["meme_issue_que_sign"] is True
    assert "SENSIBLE" not in v["why"]
    v = R.fragility_verdict(_rows(sign={k: 35.0 for k in KS}, commun={"full": 8.0}))   # signes partagés : érode
    assert v["secondaire_commun"]["full"]["meme_issue_que_sign"] is False and v["lecture_globale"] == "DIRECTION"
    assert "SENSIBLE à la cohérence inter-agents" in v["why"] and "full" in v["why"].split("SENSIBLE")[1]


def test_every_DIRECTION_motive_carries_the_vote_bias_in_its_HEAD__review_v8_P8_1():
    v = R.fragility_verdict(_rows(sign={k: 35.0 for k in KS}))
    tete = v["why"].split(" ; full ")[0]
    assert "BIAIS POSSIBLE du vote social VERS DIRECTION" in tete and v["biais_vote_vers_direction"]
    assert "BIAIS POSSIBLE" not in R.fragility_verdict(_rows())["why"]           # tout FRAGILE : sans objet


def test_the_TD_only_columns_share_is_published_and_matches_the_backend_constants__review_v8_P7_1():
    from src.agents import backend_torch as bt
    assert R.TD_SEUL_SORTIES == (bt._GRAB_NODE, bt._RUB_NODE, bt._VALUE_NODE)
    W0 = np.asarray(R.load_bassin().W, dtype=np.float64)
    d = np.zeros((2,) + W0.shape)
    d[:, 5, 88] = 1.0                                                               # tout sur la colonne grab
    assert R.delta_structure(d)["td_seul_cols_share"] == pytest.approx(1.0)
    d[:, 5, 64] = 3.0                                                               # + trois fois plus sur un déplacement
    assert R.delta_structure(d)["td_seul_cols_share"] == pytest.approx(0.25)


def test_the_in_run_check_names_every_broken_branch_and_the_seed_task_STOPS__review_v8_P10_1(tmp_path, monkeypatch):
    cell = _cell_from_published(2026)
    cell["controls"]["eps"]["l1_rel_err_max"] = 0.0
    assert R.verifier_seed(cell, 2026) == []                                        # copie du publié : conforme
    bad = copy.deepcopy(cell)
    bad["arms"]["b_const"]["learned_objects"]["ages"][0] += 1
    bad["arms"]["b_eplr"]["sign_commun"]["l1_rel_err_max"] = 0.5
    e = R.verifier_seed(bad, 2026)
    assert any("branche 4" in x and "b_const" in x for x in e) and any("branche 6" in x and "b_eplr" in x for x in e)
    d = tmp_path / "cells"
    d.mkdir()
    monkeypatch.setattr(R, "cells_dir", lambda root=None: str(d))
    monkeypatch.setattr(R, "cellules_manquantes", lambda seed, arms=R.ARMS, root=None: [])
    monkeypatch.setattr(R, "run_fragility_seed", lambda *a, **k: copy.deepcopy(bad))
    with pytest.raises(RuntimeError, match="contrôle en cours de run ÉCHOUÉ"):
        R._tache_seed(2026, 200, 100)
    import json
    ecrit = json.load(open(d / "seed_2026.json", encoding="utf-8"))                 # la mesure est GARDÉE
    assert ecrit["verification_en_cours"] == e
    with pytest.raises(RuntimeError, match="passe précédente"):                      # revue v9 P10.a : la REPRISE relève
        R._tache_seed(2026, 200, 100)


def test_sealed_thresholds_must_equal_the_executed_ones__review_v4_P4_2():
    ok = {"seuils": R.seuils_du_runner()}
    assert R.verifier_seuils(ok) is True
    for mauvais in ({"seuils": dict(R.seuils_du_runner(), famille=16)}, {"seuils": dict(R.seuils_du_runner(), x=1)},
                    {}):
        with pytest.raises(ValueError):
            R.verifier_seuils(mauvais)


def test_workers_bound_is_enforced_before_anything__review_v4_P10_4():
    from types import SimpleNamespace as NS
    with pytest.raises(ValueError):
        R._commande_tout(NS(workers=7, smoke=True, seeds=1), {"question": "q", "plafond": "p"}, 1.0, "x.json")


def test_verdict_publishes_band_saturation_controls_ratios_and_thresholds():
    v = R.fragility_verdict(_rows())
    b = v["par_bras"]["full"]
    for key in ("net_l1_median_agent", "net_over_path_median", "saturation_transplant_median", "transplant", "sign"):
        assert key in b, key
    assert b["net_over_path_median"] == pytest.approx(12.0 / 180.0)
    assert b["saturation_transplant_median"] == pytest.approx((36.0 - 8.0) / (36.0 - 7.5))
    assert b["sign"]["bande_tirage0_moins_tirage1"] == {"mediane": -1.0, "abs_mediane": 1.0, "n": 12}
    assert set(v["controles"]) == {"eps", "pos"} and v["controles"]["eps"]["classe"] == "NEUTRE"
    assert v["thresholds"] == {"sign_min": 11, "delta_min": 5.0, "n_min": 12, "harness_min": 20.0,
                               "match_tol": 0.01, "saturation_high": 0.9, "e19_closure_max": 2.0 / 3.0}
    assert v["famille"] == 15 and v["par_bras"]["full"]["resurrections_phase1_median"] == 10.0


# --------------------------------------------------------------------------------------------------
# 3. Gardes et orchestration — injection à dose connue, aucun monde.
# --------------------------------------------------------------------------------------------------


def test_run_fragility_seed_and_replay_arm_refuse_degenerate_args_before_any_world():
    t0 = time.time()
    for bad in (dict(num_agents=0), dict(ticks_learn=0), dict(ticks_test=0), dict(r_draws=0), dict(arms=()),
                dict(arms=("b_zzz",))):
        kw = dict(seed=2026, arms=("b_const",), r_draws=2, num_agents=12, ticks_learn=10, ticks_test=10)
        kw.update(bad)
        with pytest.raises(ValueError):
            R.run_fragility_seed(**kw)
    for bad in (dict(arm="a_frozen"), dict(num_agents=0), dict(ticks_learn=0), dict(ticks_test=0)):
        kw = dict(seed=2026, arm="b_full", num_agents=12, ticks_learn=10, ticks_test=10)
        kw.update(bad)
        with pytest.raises(ValueError):
            R.replay_arm(**kw)
    assert time.time() - t0 < 0.5


def test_run_fragility_seed_orchestration_at_known_dose():
    """Monde FACTICE : la survie d'une cohorte est une fonction CONNUE de son déplacement à W_bassin
    (S = 40 − ‖W − W0‖₁ moyen par agent). Le runner doit rendre : noop = 40 exactement ; transplant = objets
    appris ; sign = transplant (mêmes magnitudes) ; iso = transplant (même L1) ; pos = 40 − ‖W0‖₁ ; eps ≈ 40."""
    W0 = np.asarray(R.load_bassin().W, dtype=np.float32)
    l1_W0 = float(np.abs(W0.astype(np.float64)).sum())
    B, calls = 4, []

    def S_of(Ws):
        d = np.asarray(Ws, dtype=np.float64) - W0.astype(np.float64)[None]
        return 40.0 - float(np.mean(np.abs(d).reshape(len(Ws), -1).sum(1)))

    def fake_phase2(seed, Ws, ticks_test=200):
        calls.append(np.array(Ws, copy=True))
        s = S_of(Ws)
        return {"survival_median": s, "ages": [round(s, 6)] * len(Ws), "censored": 0, "ticks": 1}

    def fake_replay(seed, arm, num_agents=12, ticks_learn=2000, ticks_test=200):
        rng = np.random.default_rng(99)
        dW = np.zeros((num_agents,) + W0.shape)
        dW[:, :, -3:] = 0.5 * rng.standard_normal((num_agents, W0.shape[0], 3))   # 3 colonnes, dose connue
        Wf = R.apply_delta(W0, dW)
        s = S_of(Wf)
        return {"W_final": Wf, "learning": {"dW_abs_sum": 50.0 * float(np.abs(dW).sum())},
                "survival": {"survival_median": s, "ages": [round(s, 6)] * num_agents, "censored": 0, "ticks": 1}}

    cell = R.run_fragility_seed(2026, arms=("b_const",), r_draws=2, num_agents=B,
                                _replay=fake_replay, _phase2=fake_phase2)
    a = cell["arms"]["b_const"]
    assert cell["noop"]["S"] == 40.0
    assert a["transplant"]["bit_exact_W"] is True and a["transplant"]["ages_identical_to_learned_objects"] is True
    # L1 mesurée sur le déplacement EFFECTIF (W arrondi en float32) : égale au nominal à l'arrondi près
    assert a["sign"]["S"] == pytest.approx(a["transplant"]["S"], abs=1e-4)
    assert a["iso"]["S"] == pytest.approx(a["transplant"]["S"], abs=1e-3)
    assert a["sign"]["l1_rel_err_max"] < 1e-5 and a["iso"]["l1_rel_err_max"] < 1e-4
    assert cell["controls"]["pos"]["S"] == pytest.approx(40.0 - l1_W0, rel=1e-5)
    l1_dW = float(np.mean(R.l1_per_agent(np.asarray(a["net_l1_per_agent"])[:, None, None] * np.ones((1, 1, 1)))))
    assert cell["controls"]["eps"]["S"] == pytest.approx(40.0 - R.EPS_SCALE * l1_dW, abs=1e-3)
    assert cell["controls"]["eps"]["reference"] == "b_const"             # sans b_full : le premier bras
    assert a["sign_x2"]["S"] == pytest.approx(40.0 - 2.0 * l1_dW, abs=1e-3)
    assert a["sign_x4"]["S"] == pytest.approx(40.0 - 4.0 * l1_dW, abs=1e-3)
    assert a["sign_x4"]["l1_rel_err_max"] < 1e-5
    assert a["net_over_path"] == pytest.approx(1.0 / 50.0)
    assert a["structure"]["input_cols_share"] == 0.0                     # rien dans les colonnes d'entrée
    # 1 noop + 1 transplant + 2 × (sign, iso, ×2, ×4) + 2 × (eps, pos) = 14 phases 2 ; noop d'abord
    assert a["sign_commun"]["S"] == pytest.approx(a["transplant"]["S"], abs=1e-4)   # mêmes magnitudes, signes partagés
    # 1 noop + 1 transplant + 2 × (sign, iso, ×2, ×4, commun) + 2 × (eps, pos) = 16 phases 2 ; noop d'abord
    assert len(calls) == 16 and np.array_equal(calls[0], np.broadcast_to(W0, (B,) + W0.shape))


def _fake_cell_replay(counter):
    def replay(seed, arm, num_agents=12, ticks_learn=2000, ticks_test=200):
        counter.append((seed, arm))
        W0 = np.asarray(R.load_bassin().W, dtype=np.float32)
        Wf = np.broadcast_to(W0, (num_agents,) + W0.shape).copy()
        Wf[:, 0, 64] += 0.5
        return {"W_final": Wf, "learning": {"dW_abs_sum": 12.0, "td_updates": 3},
                "survival": {"survival_median": 9.0, "ages": [9] * num_agents, "censored": 0, "ticks": 9},
                "wall_s": 1.0, "cpu_s": 2.0}
    return replay


def test_cellule_persists_W_and_is_idempotent_and_refuses_a_corrupted_or_mismatched_cell(tmp_path):
    calls = []
    a = R.cellule(2026, "b_const", num_agents=3, ticks_learn=10, ticks_test=5, root=str(tmp_path),
                  _replay=_fake_cell_replay(calls))
    assert a["reloaded"] is False and len(calls) == 1
    npz = tmp_path / "results" / R.GENOMES_DIR / "b_const_2026.npz"
    z = np.load(npz)
    assert np.array_equal(z["W_final"], a["W_final"]) and int(z["num_inputs"]) == 59 and int(z["num_outputs"]) == 108
    b = R.cellule(2026, "b_const", num_agents=3, ticks_learn=10, ticks_test=5, root=str(tmp_path),
                  _replay=_fake_cell_replay(calls))
    assert b["reloaded"] is True and len(calls) == 1                     # relue, JAMAIS recalculée
    assert np.array_equal(b["W_final"], a["W_final"]) and b["cpu_s"] == 2.0
    with pytest.raises(RuntimeError):                                    # autres paramètres : refus
        R.cellule(2026, "b_const", num_agents=3, ticks_learn=11, ticks_test=5, root=str(tmp_path))
    np.savez_compressed(npz, W_final=np.zeros((3, 172, 172), dtype=np.float32), num_inputs=59, num_outputs=108)
    with pytest.raises(RuntimeError):                                    # npz remplacé : sha256 discordant
        R.cellule(2026, "b_const", num_agents=3, ticks_learn=10, ticks_test=5, root=str(tmp_path))
    with pytest.raises(ValueError):
        R.cellule(2026, "a_frozen", root=str(tmp_path))


def test_agreger_reads_seed_files_applies_the_sealed_verdict_and_sums_the_costs(tmp_path, monkeypatch):
    import json
    d = tmp_path / "cells"
    d.mkdir()
    monkeypatch.setattr(R, "cells_dir", lambda root=None: str(d))
    for s in (2026, 2027):
        cell = _cell_from_published(s)
        cell.update({"cpu_s": 10.0, "cells_cpu_s": 100.0, "wall_s": 5.0})
        (d / f"seed_{s}.json").write_text(json.dumps(cell), encoding="utf-8")
    rule = {"question": "q", "plafond": "p"}
    out = str(tmp_path / "agg.json")
    data = R.agreger([2026, 2027, 2028], out, 1000.0, rule, extra={"execution": {"mode": "test"}})
    assert set(data["cells"]) == {"2026", "2027"} and len(data["rows"]) == 2
    assert data["verdict"]["verdict"] == "INCOMPLET" and data["verdict"]["n"] == 2   # 2028 absent : jamais fabriqué
    assert data["cost"]["cpu_total_s"] == pytest.approx(220.0) and data["execution"] == {"mode": "test"}
    assert data["design"]["control_family"]["cells"] == 15
    assert json.load(open(out, encoding="utf-8"))["verdict"]["verdict"] == "INCOMPLET"


def test_consensus_counter_counts_rewritten_rows_at_known_answer_and_always_restores_the_world():
    from types import SimpleNamespace as NS
    from src.worlds.world_1_stoneage import Biosphere3D
    orig = Biosphere3D._apply_social_consensus
    voted = np.full(20, 9.0, dtype=np.float32)
    logits = np.zeros((3, 20), dtype=np.float32)
    logits[:, 13], logits[:, 14] = 1.0, 1.0                              # partage ET acceptation au-dessus des seuils
    agent = lambda x: {"x": x, "y": 0, "energy": 50.0, "hp": 50.0, "id": str(x)}  # noqa: E731
    same = NS(agents=[agent(1), agent(1), agent(2)], consensus=NS(vote=lambda preds: voted))
    apart = NS(agents=[agent(1), agent(2), agent(3)], consensus=NS(vote=lambda preds: voted))
    with R.compter_consensus() as c:
        Biosphere3D._apply_social_consensus(same, logits.copy())         # deux agents sur la case 1 : 2 lignes
        Biosphere3D._apply_social_consensus(apart, logits.copy())        # personne ensemble : rien
    assert c == {"ticks_avec_reecriture": 1, "lignes_reecrites": 2}
    assert Biosphere3D._apply_social_consensus is orig
    with pytest.raises(RuntimeError):
        with R.compter_consensus():
            raise RuntimeError("panne au milieu d'une phase 2")
    assert Biosphere3D._apply_social_consensus is orig                   # restauré même sur exception


@requires_torch
def test_phase2_with_W_on_the_noop_reproduces_the_published_frozen_bassin_bit_exact():
    """Monde RÉEL (≈ 2-7 s, sauté si un run tient kuzu) : le no-op via phase2_with_W — garde de corps et compteur de
    consensus compris — rend les 12 âges publiés de a_frozen au seed 2026 : les deux enveloppes sont neutres."""
    W0 = np.asarray(R.load_bassin().W, dtype=np.float32)
    zero = np.zeros((12,) + W0.shape, dtype=np.float64)                    # revue v7 P6.1 : CE pipeline, au bit
    surv = R.phase2_with_W(2026, R.apply_delta(W0, zero), ticks_test=200)
    assert surv["ages"] == R.published("a_frozen", 2026)["ages"]
    assert set(surv["consensus"]) == {"ticks_avec_reecriture", "lignes_reecrites"}
    reco = surv["reconstructions"]                                        # revue v6 P8.a : le 3e écrivain, compté
    assert reco["constructions"] >= 1 and reco["B"][0] == 12 and reco["B"] == sorted(reco["B"], reverse=True)
    assert reco["reconstructions"] == reco["constructions"] - 1                   # revue v7 P10.2 : initiale exclue


def test_bail_du_parent_accepts_only_the_parents_kuzu_lease_under_the_declared_owner():
    from types import SimpleNamespace as L
    ok = L(owner="s2-bassin-fragility", pid=4242)
    assert R.bail_du_parent("s2-bassin-fragility", _read=lambda r: ok, _ppid=4242) is ok
    for lu, ppid in ((None, 4242), (L(owner="autre-job", pid=4242), 4242), (ok, 999)):
        with pytest.raises(RuntimeError):                                # absent, autre détenteur, autre processus
            R.bail_du_parent("s2-bassin-fragility", _read=lambda r, lu=lu: lu, _ppid=ppid)


# --------------------------------------------------------------------------------------------------
# 4. Mesures PUBLIÉES — réponse connue sur les JSON suivis.
# --------------------------------------------------------------------------------------------------


def test_published_reads_the_P416_and_P49_rows_and_the_P44_cold_floor():
    a = R.published("a_frozen", 2026)
    assert a["S"] == 31.5 and len(a["ages"]) == 12 and a["source"].endswith("s2_credit_ablation_2.json")
    f = R.published("b_full", 2026)
    assert f["S"] == 7.0 and f["dW_abs_sum"] == pytest.approx(18242.03954219818, rel=0, abs=0)
    assert (f["td_updates"], f["episode_updates"], f["resurrections"]) == (1999, 250, 12)
    z = R.published("b_zero", 2026)
    assert z["S"] == 32.0 and z["source"].endswith("s2_credit_ablation.json")
    assert R.cold_floor(2026) == 8.0 and R.cold_floor(2030) == 7.0


def _cell_from_published(seed):
    """Une cellule dont chaque mesure RECOPIE le publié : `seed_row` doit y lire des réplications parfaites."""
    cell = {"noop": {"S": R.published("a_frozen", seed)["S"], "ages": R.published("a_frozen", seed)["ages"]},
            "controls": {"eps": {"S": 30.0, "draws": [{"S": 30.0}], "l1_rel_err_max": 0.0},
                         "pos": {"S": 7.0, "draws": [{"S": 7.0}]}},
            "arms": {}}
    for arm in R.ARMS:
        p = R.published(arm, seed)
        cell["arms"][arm] = {
            "learning": {"dW_abs_sum": p["dW_abs_sum"], "td_updates": p["td_updates"],
                         "episode_updates": p["episode_updates"], "resurrections": p["resurrections"],
                         "ticks": p["ticks"]},
            "learned_objects": {"S": p["S"], "ages": list(p["ages"])},
            "transplant": {"S": p["S"], "ages": list(p["ages"]), "ages_identical_to_learned_objects": True},
            "net_l1_median_agent": 10.0, "net_l1_per_agent": [10.0] * 12, "path_total": p["dW_abs_sum"],
            "sign": {"S": p["S"], "draws": [{"S": p["S"], "matching": {"op_ratio_median": 0.8}}],
                     "l1_rel_err_max": 0.0},
            "iso": {"S": p["S"], "draws": [{"S": p["S"]}], "l1_rel_err_max": 0.0},
            "sign_x2": {"S": p["S"], "draws": [{"S": p["S"]}], "l1_rel_err_max": 0.0},
            "sign_x4": {"S": p["S"], "draws": [{"S": p["S"]}], "l1_rel_err_max": 0.0},
            "sign_commun": {"S": p["S"], "draws": [{"S": p["S"]}], "l1_rel_err_max": 0.0}}
    return cell


def test_seed_row_reads_perfect_replication_and_catches_one_changed_age():
    cell = _cell_from_published(2026)
    row = R.seed_row(cell, 2026)
    assert row["noop_identical"] is True and row["S_c"] == 8.0
    assert all(row[f"repl_{a[2:]}"] for a in R.ARMS)
    bad = copy.deepcopy(cell)
    bad["arms"]["b_eplr"]["learned_objects"]["ages"][0] += 1
    assert R.seed_row(bad, 2026)["repl_eplr"] is False
    bad = copy.deepcopy(cell)
    bad["arms"]["b_tdoff"]["learning"]["resurrections"] += 1             # dose/létalité rejouée ≠ publiée
    assert R.seed_row(bad, 2026)["repl_tdoff"] is False
    bad = copy.deepcopy(cell)
    bad["arms"]["b_zero"]["learning"]["ticks"] = 1999                    # revue v5 P10.d : les ticks sont comparés
    assert R.seed_row(bad, 2026)["repl_zero"] is False
    assert row["op_sign_full"] == pytest.approx(0.8) and row["S_pos_draws"] == [7.0]
    bad = copy.deepcopy(cell)
    bad["noop"]["ages"] = list(bad["noop"]["ages"])[::-1] if len(set(bad["noop"]["ages"])) > 1 else [0] * 12
    assert R.seed_row(bad, 2026)["noop_identical"] is False
