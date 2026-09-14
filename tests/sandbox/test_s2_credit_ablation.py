"""P4.9 — `S2-CREDIT-ABLATION` : le crédit in-world publié EFFACE le bassin DAgger, à Δénergie seule autant
qu'à récompense complète ([[EDR-S2-REWARD-ABLATION]] : CREDIT_ERODE_SEUL, PLEIN). L'érosion vient-elle du
SIGNE du signal (avantage constant négatif sous critic saturé), du PAS (toute mise à jour à lr 0,04 détruit),
ou du TD par tick ? Bras sur le CRÉDIT via les seams de `count_learning_events` (calibrés par P1.6) :
`reward_scale` 0 (aucun signal), `reward_scale` −1 (signe inversé), `lr` 0,004 (E19), `td_enabled` False
(épisodique seul).

Ce fichier calibre : (1) les SEAMS à réponse connue — ce qui ATTEINT réellement le learner d'origine sous
chaque variante (récompenses nulles, négation exacte, TD jamais appelé, pas publié) ; (2) le VERDICT (pur,
lignes synthétiques, branches ordonnées) ; (3) les gardes du runner. Les tests 1 simulent un monde (≤ 32
ticks, 2 à 4 agents, cohorte immortelle) : sautés par conftest quand un run tient `kuzu`.
"""
import copy
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.evo_runs import s2_credit_ablation as R  # noqa: E402

# --------------------------------------------------------------------------------------------------
# 0. La table des bras.
# --------------------------------------------------------------------------------------------------


def test_arm_table_declares_the_frozen_control_the_full_credit_and_four_credit_variants():
    assert R.ARMS == ("a_frozen", "b_full", "b_zero", "b_neg", "b_lr", "b_tdoff")
    assert R.LEARNING_ARMS == ("b_full", "b_zero", "b_neg", "b_lr", "b_tdoff")
    assert R.ARM_CREDIT["b_full"] == {"reward_scale": 1.0, "td_enabled": True, "lr": None}   # chemin PUBLIÉ
    assert R.ARM_CREDIT["b_zero"] == {"reward_scale": 0.0, "td_enabled": True, "lr": None}
    assert R.ARM_CREDIT["b_neg"] == {"reward_scale": -1.0, "td_enabled": True, "lr": None}
    assert R.ARM_CREDIT["b_lr"] == {"reward_scale": 1.0, "td_enabled": True, "lr": R.LR_LOW} and R.LR_LOW == 0.004
    assert R.ARM_CREDIT["b_tdoff"] == {"reward_scale": 1.0, "td_enabled": False, "lr": None}
    assert "a_frozen" not in R.ARM_CREDIT


# --------------------------------------------------------------------------------------------------
# 1. Les seams — ce qui atteint le learner d'ORIGINE.
# --------------------------------------------------------------------------------------------------


def test_learning_trace_full_credit_reaches_the_learner_with_the_published_step():
    t = R._learning_trace(2026, num_agents=2, ticks=16)
    assert t["summary"]["td_updates"] >= 1 and len(t["td_rewards"]) >= 1
    assert t["lr_effective"] == pytest.approx(0.04)          # pas PUBLIÉ (backend_torch.py : lr=0.04)
    assert t["summary"]["dW_abs_sum"] > 0.0
    assert all(np.isfinite(t["td_rewards"]))


def test_learning_trace_zero_scale_passes_only_zero_rewards_to_the_learner():
    """`reward_scale = 0` : le learner d'origine reçoit des récompenses TOUTES nulles (TD et épisodique),
    et met quand même à jour (l'erreur TD = γV' − V n'est pas nulle) : un bras SANS signal, pas sans pas."""
    t = R._learning_trace(2026, num_agents=2, ticks=16, reward_scale=0.0)
    assert len(t["td_rewards"]) >= 1 and all(r == 0.0 for r in t["td_rewards"])
    assert len(t["episode_rewards"]) >= 1 and all(r == 0.0 for r in t["episode_rewards"])
    assert t["summary"]["td_updates"] >= 1 and t["summary"]["reward_scale"] == 0.0


def test_learning_trace_negative_scale_flips_the_sign_exactly():
    """`reward_scale = −1` : la trace atteignant le learner est la NÉGATION bit-exacte de la trace publiée
    (float32 : −x est exact) sur le PREMIER tick — après, les politiques divergent (elles apprennent
    autre chose), donc seule l'égalité du premier appel est une réponse connue."""
    full = R._learning_trace(2026, num_agents=2, ticks=2)
    neg = R._learning_trace(2026, num_agents=2, ticks=2, reward_scale=-1.0)
    n = len(full["first_td_rewards"])
    assert n == 2 and len(neg["first_td_rewards"]) == n
    assert neg["first_td_rewards"] == [-r for r in full["first_td_rewards"]]
    assert any(r != 0.0 for r in full["first_td_rewards"])      # la négation d'un zéro ne prouve rien


def test_learning_trace_td_off_never_reaches_the_td_learner_but_episodes_do():
    t = R._learning_trace(2026, num_agents=2, ticks=17, td_enabled=False)
    assert t["td_rewards"] == [] and t["summary"]["td_updates"] == 0 and t["summary"]["td_calls"] >= 17
    assert t["summary"]["episode_updates"] >= 1 and len(t["episode_rewards"]) >= 1
    assert t["summary"]["dW_abs_sum"] > 0.0                     # l'épisodique SEUL bouge les poids


def test_learning_trace_lr_low_publishes_the_step_and_moves_less():
    full = R._learning_trace(2026, num_agents=2, ticks=16)
    low = R._learning_trace(2026, num_agents=2, ticks=16, lr=0.004)
    assert low["lr_effective"] == pytest.approx(0.004) and full["lr_effective"] == pytest.approx(0.04)
    assert 0.0 < low["summary"]["dW_abs_sum"] < full["summary"]["dW_abs_sum"]


def test_preflight_credit_seams_publishes_the_five_traces():
    out = R.preflight_credit_seams(2026, num_agents=2, ticks=16)
    for k in ("seed", "num_agents", "ticks", "zero_all_rewards_null", "neg_first_tick_exact_negation",
              "tdoff_td_never_called", "tdoff_episode_updates", "lr_effective", "dW_abs_sum"):
        assert k in out, k
    assert out["zero_all_rewards_null"] is True and out["neg_first_tick_exact_negation"] is True
    assert out["tdoff_td_never_called"] is True and out["tdoff_episode_updates"] >= 1
    assert out["lr_effective"] == {"full": pytest.approx(0.04), "lr": pytest.approx(0.004)}
    assert set(out["dW_abs_sum"]) == {"full", "zero", "neg", "lr", "tdoff"}


def test_preflight_credit_seams_refuses_a_leaking_zero_seam(monkeypatch):
    """Contre-exemple : si le bras « zéro » laissait passer une récompense non nulle, le pré-vol LÈVE."""
    from tools.experiment_preflight import PreflightError
    real = R._learning_trace

    def leaking(seed, num_agents=4, ticks=32, reward_scale=1.0, td_enabled=True, lr=None):
        t = real(seed, num_agents=num_agents, ticks=ticks, reward_scale=reward_scale, td_enabled=td_enabled, lr=lr)
        if reward_scale == 0.0:
            t["td_rewards"] = [0.0] * (len(t["td_rewards"]) - 1) + [0.25]
        return t
    monkeypatch.setattr(R, "_learning_trace", leaking)
    with pytest.raises(PreflightError):
        R.preflight_credit_seams(2026, num_agents=2, ticks=8)


# --------------------------------------------------------------------------------------------------
# 2. Le verdict — branches scellées, dans l'ordre imposé.
# --------------------------------------------------------------------------------------------------


def _col(v, i, default):
    if v is None:
        return default
    return v[i] if isinstance(v, (list, tuple)) else v


def _rows(n=12, S_a=36.0, S_full=8.0, S_zero=8.0, S_neg=8.0, S_lr=8.0, S_tdoff=8.0, dose=1999,
          dose_tdoff=250, dW_full=18000.0, dW_zero=9000.0, dW_neg=18000.0, dW_lr=1800.0, dW_tdoff=3000.0,
          dose_zero=None):
    rows = []
    for i in range(n):
        rows.append({"seed": 2026 + i, "S_a": float(_col(S_a, i, 36.0)), "S_full": float(_col(S_full, i, 8.0)),
                     "S_zero": float(_col(S_zero, i, 8.0)), "S_neg": float(_col(S_neg, i, 8.0)),
                     "S_lr": float(_col(S_lr, i, 8.0)), "S_tdoff": float(_col(S_tdoff, i, 8.0)),
                     "dose_full": int(dose), "dose_zero": int(dose if dose_zero is None else dose_zero),
                     "dose_neg": int(dose), "dose_lr": int(dose), "dose_tdoff": int(dose_tdoff),
                     "dW_full": float(dW_full), "dW_zero": float(dW_zero), "dW_neg": float(dW_neg),
                     "dW_lr": float(dW_lr), "dW_tdoff": float(dW_tdoff)})
    return rows


def test_verdict_refuses_missing_or_non_finite_inputs():
    rows = _rows()
    rows[2]["S_neg"] = float("nan")
    with pytest.raises(ValueError):
        R.credit_ablation_verdict(rows)
    rows = _rows()
    del rows[7]["dW_lr"]
    with pytest.raises(ValueError):
        R.credit_ablation_verdict(rows)
    with pytest.raises(ValueError):
        R.credit_ablation_verdict([])


def test_verdict_branch_1_INCOMPLET_wins_over_everything():
    v = R.credit_ablation_verdict(_rows(n=5, S_a=3.0))
    assert v["verdict"] == "INCOMPLET" and v["n"] == 5


def test_verdict_branch_2_INDETERMINE_HARNAIS():
    v = R.credit_ablation_verdict(_rows(S_a=12.0))
    assert v["verdict"] == "INDETERMINE_HARNAIS"


def test_verdict_branch_3_INDETERMINE_DOSE_on_td_arms_and_on_the_episodic_arm():
    v = R.credit_ablation_verdict(_rows(dose_zero=30))
    assert v["verdict"] == "INDETERMINE_DOSE" and "dose_zero" in v["why"]
    v = R.credit_ablation_verdict(_rows(dose_tdoff=20))              # épisodique : 250 attendus, seuil 100
    assert v["verdict"] == "INDETERMINE_DOSE" and "dose_tdoff" in v["why"]


def test_verdict_branch_4_INDETERMINE_REPLICATION_when_the_full_credit_no_longer_erodes():
    v = R.credit_ablation_verdict(_rows(S_full=33.0))
    assert v["verdict"] == "INDETERMINE_REPLICATION"


def test_verdict_mecanisme_PAS_OU_BRUIT_when_the_zero_signal_arm_erodes():
    v = R.credit_ablation_verdict(_rows(S_zero=9.0, S_neg=35.0))
    assert v["verdict"] == "LU" and v["mecanisme"] == "PAS_OU_BRUIT" and v["arm_zero"] == "ERODE"


def test_verdict_mecanisme_SIGNAL_QUELCONQUE_when_zero_is_neutral_but_negated_signal_erodes():
    v = R.credit_ablation_verdict(_rows(S_zero=35.0, S_neg=8.0))
    assert v["mecanisme"] == "SIGNAL_QUELCONQUE" and v["arm_zero"] == "NEUTRE" and v["arm_neg"] == "ERODE"


def test_verdict_mecanisme_SIGNE_NEGATIF_when_neither_zero_nor_negated_signal_erodes():
    v = R.credit_ablation_verdict(_rows(S_zero=34.0, S_neg=35.0))
    assert v["mecanisme"] == "SIGNE_NEGATIF" and v["neg_etend"] is False
    v = R.credit_ablation_verdict(_rows(S_zero=34.0, S_neg=[47.0] * 11 + [30.0]))   # signe inversé ÉTEND
    assert v["mecanisme"] == "SIGNE_NEGATIF" and v["arm_neg"] == "ETENDU" and v["neg_etend"] is True


def test_verdict_secondary_readings_td_pathway_and_step():
    v = R.credit_ablation_verdict(_rows(S_tdoff=8.0, S_lr=8.0))
    assert v["voie_td"] == "EPISODIQUE_SUFFIT" and v["pas"] == "DESTRUCTEUR_A_PETIT_PAS"
    v = R.credit_ablation_verdict(_rows(S_tdoff=35.0, S_lr=34.0))
    assert v["voie_td"] == "TD_NECESSAIRE" and v["pas"] == "ATTENUE_A_PETIT_PAS"
    assert v["dW_ratio_median"]["lr"] == pytest.approx(0.1) and v["dW_ratio_median"]["zero"] == pytest.approx(0.5)


def test_verdict_arm_classification_needs_sign_10_of_12_AND_median_5_ticks():
    v = R.credit_ablation_verdict(_rows(S_zero=[8.0] * 9 + [40.0] * 3))     # −28 mais 9/12
    assert v["arm_zero"] == "NEUTRE"
    v = R.credit_ablation_verdict(_rows(S_zero=[33.0] * 12))                # 12/12 mais −3
    assert v["arm_zero"] == "NEUTRE"


def test_verdict_publishes_the_full_reading_and_the_thresholds():
    v = R.credit_ablation_verdict(_rows())
    for k in ("verdict", "mecanisme", "voie_td", "pas", "neg_etend", "n", "S_a_median", "S_full_median",
              "S_zero_median", "S_neg_median", "S_lr_median", "S_tdoff_median", "d_full_median", "d_zero_median",
              "d_neg_median", "d_lr_median", "d_tdoff_median", "arm_full", "arm_zero", "arm_neg", "arm_lr",
              "arm_tdoff", "d_zero_negative", "d_neg_positive", "dose_full_median", "dose_tdoff_median",
              "dW_ratio_median", "thresholds", "why"):
        assert k in v, k
    assert v["thresholds"] == {"harness_min": 20.0, "dose_min": 1000, "dose_episodic_min": 100,
                               "sign_min": 10, "delta_min": 5.0, "n_min": 12}


# --------------------------------------------------------------------------------------------------
# 3. Les gardes du runner.
# --------------------------------------------------------------------------------------------------


def test_run_arm_refuses_degenerate_args_before_any_world():
    import time
    t0 = time.time()
    for bad in (dict(num_agents=0), dict(ticks_learn=0), dict(ticks_test=0), dict(arm="zzz"), dict(arm="b_energy")):
        kw = dict(seed=2026, arm="b_zero", num_agents=12, ticks_learn=10, ticks_test=10)
        kw.update(bad)
        with pytest.raises(ValueError):
            R.run_arm(**kw)
    assert time.time() - t0 < 0.5


def test_replication_and_import_are_the_P48_instruments():
    """Le bras complet se réplique et s'importe avec les MÊMES fonctions que P4.8 (pas de copie)."""
    from tools.evo_runs import s2_reward_ablation as RA
    assert R.replication_check is RA.replication_check and R.p44_full_rows is RA.p44_full_rows
    p44 = json.load(open(os.path.join(R._ROOT, RA.P44_RESULTS), encoding="utf-8"))
    row = copy.deepcopy(p44["arms"]["b_warm_credit"]["2026"])
    assert R.replication_check(row, seed=2026)["identical"] is True
