"""P4.16 — `S2-CREDIT-ABLATION-2` : [[EDR-S2-CREDIT-ABLATION]] a établi que l'érosion du bassin DAgger par le
crédit publié exige un signal non nul, ignore son signe, n'est pas proportionnelle au mouvement, et que la voie
ÉPISODIQUE seule suffit. Seconde passe : (b_tdonly) épisodique COUPÉ, TD seul ; (b_const) retour CONSTANT +1
(signal non nul, contenu nul) ; (b_eplr) épisodique seul à pas 0,004.

Ce fichier calibre : (1) les deux seams NEUFS (`episode_enabled`, `reward_const`) portés par `credit_variant`
dans le runner (pas dans tools/learning_events.py, en cours d'édition par une autre session) — à réponse connue
sur ce qui ATTEINT le learner d'ORIGINE, et no-op EXACT par défaut contre `_learning_trace` de P4.9 ;
(2) le VERDICT (pur, lignes synthétiques, branches ordonnées) ; (3) les gardes du runner. Les tests (1)
simulent un monde (≤ 32 ticks, 2 agents, immortel) : sautés par conftest quand un run tient `kuzu`.
"""
import copy
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.evo_runs import s2_credit_ablation as R1  # noqa: E402
from tools.evo_runs import s2_credit_ablation_2 as R  # noqa: E402

# --------------------------------------------------------------------------------------------------
# 0. La table des bras.
# --------------------------------------------------------------------------------------------------


def test_arm_table_declares_the_frozen_control_the_full_credit_and_three_credit_variants():
    assert R.ARMS == ("a_frozen", "b_full", "b_tdonly", "b_const", "b_eplr")
    assert R.LEARNING_ARMS == ("b_full", "b_tdonly", "b_const", "b_eplr")
    base = {"reward_scale": 1.0, "td_enabled": True, "lr": None, "episode_enabled": True, "reward_const": None}
    assert R.ARM_CREDIT["b_full"] == base                                    # chemin PUBLIÉ, bit-identique
    assert R.ARM_CREDIT["b_tdonly"] == dict(base, episode_enabled=False)
    assert R.ARM_CREDIT["b_const"] == dict(base, reward_const=1.0)
    assert R.ARM_CREDIT["b_eplr"] == dict(base, td_enabled=False, lr=R1.LR_LOW) and R1.LR_LOW == 0.004
    assert "a_frozen" not in R.ARM_CREDIT


# --------------------------------------------------------------------------------------------------
# 1. Les seams — ce qui atteint le learner d'ORIGINE.
# --------------------------------------------------------------------------------------------------


def test_credit_variant_defaults_are_a_bit_exact_noop_against_the_P49_trace():
    """No-op EXACT : sous `credit_variant()` par défaut, la trace du learner d'origine est identique à celle de
    `_learning_trace` (P4.9, sans credit_variant) au même seed — premier tick et Σ|ΔW| bit-égaux."""
    ref = R1._learning_trace(2026, num_agents=2, ticks=16)
    got = R._learning_trace_2(2026, num_agents=2, ticks=16)
    assert got["first_td_rewards"] == ref["first_td_rewards"]
    assert got["summary"]["dW_abs_sum"] == ref["summary"]["dW_abs_sum"]
    assert got["summary"]["td_updates"] == ref["summary"]["td_updates"] >= 1
    assert got["summary"]["episode_updates"] == ref["summary"]["episode_updates"] >= 1


def test_episode_disabled_never_reaches_the_original_learn_episode_but_td_does():
    t = R._learning_trace_2(2026, num_agents=2, ticks=17, episode_enabled=False)
    assert t["episode_rewards"] == [] and t["summary"]["episode_updates"] == 0
    assert t["summary"]["episode_calls"] >= 1                     # appelé par le monde, coupé par le seam
    assert t["summary"]["td_updates"] >= 1 and len(t["td_rewards"]) >= 1
    assert t["summary"]["dW_abs_sum"] > 0.0                       # le TD seul bouge les poids


def test_reward_const_passes_only_the_constant_to_both_paths_and_still_updates():
    t = R._learning_trace_2(2026, num_agents=2, ticks=17, reward_const=1.0)
    assert len(t["td_rewards"]) >= 1 and all(r == 1.0 for r in t["td_rewards"])
    assert len(t["episode_rewards"]) >= 1 and all(r == 1.0 for r in t["episode_rewards"])
    assert t["summary"]["td_updates"] >= 1 and t["summary"]["episode_updates"] >= 1
    assert t["summary"]["dW_abs_sum"] > 0.0


def test_episodic_only_at_low_step_publishes_the_step_and_never_calls_td():
    t = R._learning_trace_2(2026, num_agents=2, ticks=17, td_enabled=False, lr=0.004)
    assert t["td_rewards"] == [] and t["summary"]["td_updates"] == 0
    assert t["summary"]["episode_updates"] >= 1 and t["lr_effective"] == pytest.approx(0.004)


def test_preflight_credit_seams_2_publishes_the_four_traces():
    out = R.preflight_credit_seams_2(2026, num_agents=2, ticks=17)
    for k in ("seed", "num_agents", "ticks", "noop_exact_vs_P49", "tdonly_episode_never_called", "tdonly_td_alive",
              "const_all_rewards_one", "const_both_paths_update", "eplr_td_never_called", "eplr_lr_effective",
              "dW_abs_sum", "td_updates", "episode_updates"):
        assert k in out, k
    assert out["noop_exact_vs_P49"] is True and out["tdonly_episode_never_called"] is True
    assert out["const_all_rewards_one"] is True and out["eplr_td_never_called"] is True
    assert out["eplr_lr_effective"] == pytest.approx(0.004)
    assert set(out["dW_abs_sum"]) == {"full", "tdonly", "const", "eplr"}


def test_preflight_credit_seams_2_refuses_a_leaking_const_seam(monkeypatch):
    from tools.experiment_preflight import PreflightError
    real = R._learning_trace_2

    def leaking(seed, num_agents=4, ticks=32, **kw):
        t = real(seed, num_agents=num_agents, ticks=ticks, **kw)
        if kw.get("reward_const") is not None:
            t["td_rewards"] = [1.0] * (len(t["td_rewards"]) - 1) + [0.25]
        return t
    monkeypatch.setattr(R, "_learning_trace_2", leaking)
    with pytest.raises(PreflightError):
        R.preflight_credit_seams_2(2026, num_agents=2, ticks=9)


# --------------------------------------------------------------------------------------------------
# 2. Le verdict — branches scellées, dans l'ordre imposé.
# --------------------------------------------------------------------------------------------------


def _col(v, i, default):
    if v is None:
        return default
    return v[i] if isinstance(v, (list, tuple)) else v


def _rows(n=12, S_a=36.0, S_full=8.0, S_tdonly=8.0, S_const=8.0, S_eplr=8.0, dose_td=1999, dose_ep=250,
          dose_tdonly=None, dose_const_ep=None, dose_eplr=None, dW_full=18000.0, dW_tdonly=6000.0,
          dW_const=9000.0, dW_eplr=1200.0):
    rows = []
    for i in range(n):
        rows.append({"seed": 2026 + i, "S_a": float(_col(S_a, i, 36.0)), "S_full": float(_col(S_full, i, 8.0)),
                     "S_tdonly": float(_col(S_tdonly, i, 8.0)), "S_const": float(_col(S_const, i, 8.0)),
                     "S_eplr": float(_col(S_eplr, i, 8.0)),
                     "dose_full": int(dose_td), "dose_tdonly": int(dose_td if dose_tdonly is None else dose_tdonly),
                     "dose_const_td": int(dose_td), "dose_const_ep": int(dose_ep if dose_const_ep is None else dose_const_ep),
                     "dose_eplr": int(dose_ep if dose_eplr is None else dose_eplr),
                     "dW_full": float(dW_full), "dW_tdonly": float(dW_tdonly), "dW_const": float(dW_const),
                     "dW_eplr": float(dW_eplr)})
    return rows


def test_verdict_refuses_missing_or_non_finite_inputs():
    rows = _rows()
    rows[4]["S_const"] = float("nan")
    with pytest.raises(ValueError):
        R.credit_ablation_2_verdict(rows)
    rows = _rows()
    del rows[1]["dW_eplr"]
    with pytest.raises(ValueError):
        R.credit_ablation_2_verdict(rows)
    with pytest.raises(ValueError):
        R.credit_ablation_2_verdict([])


def test_verdict_branch_1_INCOMPLET_wins_over_everything():
    v = R.credit_ablation_2_verdict(_rows(n=6, S_a=3.0))
    assert v["verdict"] == "INCOMPLET" and v["n"] == 6


def test_verdict_branch_2_INDETERMINE_HARNAIS():
    assert R.credit_ablation_2_verdict(_rows(S_a=12.0))["verdict"] == "INDETERMINE_HARNAIS"


def test_verdict_branch_3_INDETERMINE_DOSE_on_each_pathway():
    v = R.credit_ablation_2_verdict(_rows(dose_tdonly=40))
    assert v["verdict"] == "INDETERMINE_DOSE" and "dose_tdonly" in v["why"]
    v = R.credit_ablation_2_verdict(_rows(dose_const_ep=20))
    assert v["verdict"] == "INDETERMINE_DOSE" and "dose_const_ep" in v["why"]
    v = R.credit_ablation_2_verdict(_rows(dose_eplr=30))
    assert v["verdict"] == "INDETERMINE_DOSE" and "dose_eplr" in v["why"]


def test_verdict_branch_4_INDETERMINE_REPLICATION():
    assert R.credit_ablation_2_verdict(_rows(S_full=33.0))["verdict"] == "INDETERMINE_REPLICATION"


def test_verdict_contenu_INDIFFERENT_when_the_constant_return_erodes():
    v = R.credit_ablation_2_verdict(_rows(S_const=8.5))
    assert v["verdict"] == "LU" and v["contenu"] == "CONTENU_INDIFFERENT" and v["arm_const"] == "ERODE"


def test_verdict_contenu_COMPTE_when_the_constant_return_does_not_erode():
    v = R.credit_ablation_2_verdict(_rows(S_const=34.0))
    assert v["contenu"] == "CONTENU_COMPTE" and v["arm_const"] == "NEUTRE"
    v = R.credit_ablation_2_verdict(_rows(S_const=[46.0] * 11 + [30.0]))
    assert v["contenu"] == "CONTENU_COMPTE" and v["arm_const"] == "ETENDU"


def test_verdict_voie_TD_SUFFIT_AUSSI_or_EPISODIQUE_SEUL_DESTRUCTEUR():
    assert R.credit_ablation_2_verdict(_rows(S_tdonly=7.0))["voie"] == "TD_SUFFIT_AUSSI"
    assert R.credit_ablation_2_verdict(_rows(S_tdonly=35.0))["voie"] == "EPISODIQUE_SEUL_DESTRUCTEUR"


def test_verdict_pas_episodique():
    assert R.credit_ablation_2_verdict(_rows(S_eplr=7.5))["pas_episodique"] == "EPISODIQUE_DESTRUCTEUR_A_PETIT_PAS"
    assert R.credit_ablation_2_verdict(_rows(S_eplr=33.0))["pas_episodique"] == "EPISODIQUE_ATTENUE_A_PETIT_PAS"   # −3 : bande neutre
    assert R.credit_ablation_2_verdict(_rows(S_eplr=30.0))["arm_eplr"] == "ERODE"                                  # −6 : érode (seuil ±5)


def test_verdict_arm_classification_needs_sign_10_of_12_AND_median_5_ticks():
    v = R.credit_ablation_2_verdict(_rows(S_const=[8.0] * 9 + [40.0] * 3))       # −28 mais 9/12
    assert v["arm_const"] == "NEUTRE"
    v = R.credit_ablation_2_verdict(_rows(S_const=[33.0] * 12))                  # 12/12 mais −3
    assert v["arm_const"] == "NEUTRE"


def test_verdict_publishes_the_full_reading_the_ratios_and_the_thresholds():
    v = R.credit_ablation_2_verdict(_rows())
    for k in ("verdict", "contenu", "voie", "pas_episodique", "n", "S_a_median", "S_full_median", "S_tdonly_median",
              "S_const_median", "S_eplr_median", "d_full_median", "d_tdonly_median", "d_const_median", "d_eplr_median",
              "arm_full", "arm_tdonly", "arm_const", "arm_eplr", "d_const_negative", "d_const_positive",
              "dose_full_median", "dose_tdonly_median", "dose_const_td_median", "dose_const_ep_median",
              "dose_eplr_median", "dW_ratio_median", "thresholds", "why"):
        assert k in v, k
    assert v["dW_ratio_median"]["eplr"] == pytest.approx(1200.0 / 18000.0)
    assert v["thresholds"] == {"harness_min": 20.0, "dose_min": 1000, "dose_episodic_min": 100,
                               "sign_min": 10, "delta_min": 5.0, "n_min": 12}


# --------------------------------------------------------------------------------------------------
# 3. Les gardes du runner.
# --------------------------------------------------------------------------------------------------


def test_run_arm_refuses_degenerate_args_before_any_world():
    import time
    t0 = time.time()
    for bad in (dict(num_agents=0), dict(ticks_learn=0), dict(ticks_test=0), dict(arm="zzz"), dict(arm="b_zero")):
        kw = dict(seed=2026, arm="b_const", num_agents=12, ticks_learn=10, ticks_test=10)
        kw.update(bad)
        with pytest.raises(ValueError):
            R.run_arm(**kw)
    assert time.time() - t0 < 0.5


def test_replication_and_import_are_the_P48_instruments():
    from tools.evo_runs import s2_reward_ablation as RA
    assert R.replication_check is RA.replication_check and R.p44_full_rows is RA.p44_full_rows
    p44 = json.load(open(os.path.join(R._ROOT, RA.P44_RESULTS), encoding="utf-8"))
    row = copy.deepcopy(p44["arms"]["b_warm_credit"]["2026"])
    assert R.replication_check(row, seed=2026)["identical"] is True


# --------------------------------------------------------------------------------------------------
# 4. Le bloc COÛT se recompute (P2.78 + revue adversariale du 2026-09-24 : un dénominateur de coût
#    reconstruit à la main par le lecteur est une prémisse recopiée, classe E8).
# --------------------------------------------------------------------------------------------------


def _arms(cells):
    """cells : {(bras, seed): (elapsed_s, importe)} -> la structure `arms` du JSON."""
    out = {}
    for (a, s), (e, imp) in cells.items():
        rec = {"elapsed_s": float(e)}
        if imp:
            rec["imported_from"] = "results/ailleurs.json"
        out.setdefault(a, {})[str(s)] = rec
    return out


def test_cost_cells_separates_MEASURED_from_IMPORTED_and_publishes_the_rate():
    """Le coût par cellule se calcule sur les cellules RÉELLEMENT calculées : une cellule importée
    porte l'`elapsed_s` du run d'origine, qui n'a pas été dépensé ici."""
    arms = _arms({("a", 1): (10.0, False), ("b", 1): (90.0, False), ("b", 2): (1000.0, True)})
    c = R.cost_cells(arms)
    assert c["cells_declared"] == 3 and c["cells_measured"] == 2 and c["cells_imported"] == 1
    assert c["elapsed_measured_s"] == pytest.approx(100.0)
    assert c["s_per_measured_cell"] == pytest.approx(50.0)


def test_cost_cells_excludes_the_long_cells_from_the_rate_without_losing_them():
    """Les cellules hors échelle (machine suspendue) sont EXCLUES du débit et PUBLIÉES à part, avec
    leur propre dénominateur — jamais soustraites du numérateur en gardant le dénominateur complet."""
    arms = _arms({("a", 1): (100.0, False), ("a", 2): (200.0, False), ("a", 3): (9000.0, False)})
    c = R.cost_cells(arms, long_cell_s=5000.0)
    assert c["cells_long"] == 1 and c["cells_short"] == 2
    assert c["elapsed_short_s"] == pytest.approx(300.0)
    assert c["s_per_short_cell"] == pytest.approx(150.0)
    assert c["cells_over_long_s"] == {"a/3": 9000}


def test_cost_cells_returns_None_rather_than_a_fabricated_rate_on_an_empty_arm_set():
    """Porte 14 : une collection vide rend None, jamais 0.0 (un débit de 0 s/cellule serait une
    affirmation de gratuité)."""
    c = R.cost_cells({})
    assert c["cells_measured"] == 0
    assert c["s_per_measured_cell"] is None and c["s_per_short_cell"] is None


def test_cost_cells_matches_the_real_run_and_its_published_wall_time():
    """Réponse connue sur l'artefact publié : les cellules mesurées expliquent le temps mur à 1 %."""
    d = json.load(open(os.path.join(R._ROOT, "results", "s2_credit_ablation_2.json"), encoding="utf-8"))
    c = R.cost_cells(d["arms"])
    assert c["cells_declared"] == 60 and c["cells_imported"] == 11 and c["cells_measured"] == 49
    assert abs(c["elapsed_measured_s"] - d["cost"]["elapsed_total_s"]) / d["cost"]["elapsed_total_s"] < 0.01
    assert c["cells_long"] == 2 and c["cells_short"] == 47
