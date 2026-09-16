# tests/sandbox/test_harness_verdict.py
"""Lecture pure du harnais : chaque branche de l'ORDRE 2.3-b est atteinte par UNE db factice, et rien d'autre.
Aucune constante sur collection vide : listes vides et nan LÈVENT."""
import copy
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai.harness_verdict import (  # noqa: E402
    BRANCHES, harness_verdict_lecture, measure_ablated_bayes_ceiling, measure_noise_floor)

SEEDS = list(range(12))


def _col(values):
    return {str(s): float(v) for s, v in zip(SEEDS, values)}


def _dose(updates):
    return {str(s): {"calls": 300, "updates": updates, "dparam_abs_sum": float(updates), "episodes_seen": 4800,
                     "unit": "gradient_updates"} for s in SEEDS}


def _rule(piece="bilinear"):
    return {"n_floor": 12, "piece": piece, "sweep": [{"lr": 0.02}, {"lr": 0.002}],
            "ablations": [{"name": "permute_key", "site": "input", "must_bite": True},
                          {"name": "inject_distractor_slot", "site": "input", "must_bite": False}],
            "bayes_floors": {"permute_key": 1 / 6},
            "incapable_ceiling": {"value": 34 / 36, "provenance": "forme close plain 34/36, MINORANT (plain_substrate_ceiling.py)", "proven": False},
            "min_sep": 0.05, "prior_max": 0.5, "oracle_min": 0.9, "collapse_factor": 1.5, "alive_margin": 0.05,
            "matched_sham": None}


def _db(A=0.93, A0=0.17, A2=0.90, D=0.27, D2=0.30, noop=None, abl_key=0.17, abl_dist=None, oracle=1.0, first=0.20):
    rng = np.random.RandomState(0)
    j = lambda v, w=0.01: [v + w * x for x in rng.uniform(-1, 1, 12)]   # noqa: E731
    noop = j(A) if noop is None else noop
    abl_dist = j(A) if abl_dist is None else abl_dist
    return {"seeds": SEEDS,
            "arms": {"A": {"first": _col(j(first)), "mid": _col(j((first + A) / 2)), "last": _col(j(A)), "dose": _dose(300)},
                     "A0": {"last": _col(j(A0)), "dose": _dose(0)},
                     "A2": {"last": _col(j(A2)), "dose": _dose(300)},
                     "D": {"last": _col(j(D)), "dose": _dose(300)},
                     "D2": {"last": _col(j(D2)), "dose": _dose(300)}},
            "eval": {"noop": {"A": _col(noop), "A0": _col(j(A0)), "A2": _col(j(A2)), "D": _col(j(D)), "D2": _col(j(D2))},
                     "oracle": _col([oracle] * 12),
                     "ablated": {"permute_key": _col(j(abl_key)), "inject_distractor_slot": _col(abl_dist)},
                     "control": {}},
            "abandoned": {k: [] for k in ("A", "A0", "A2", "D", "D2")}}


def test_branch_order_is_the_sealed_one():
    assert BRANCHES == ("INCOMPLET", "INCONCLUSIVE_N", "INDETERMINE_HARNAIS", "LR_ARTIFACT", "NOT_DEMANDED",
                        "DEMAND_WITHIN_NOISE", "INCONCLUSIVE_SPECIFICITY", "INCONCLUSIVE_ALIAS", "NOT_ACQUIRED",
                        "PIECE_NOT_NECESSARY", "PIECE_INCONCLUSIVE", "PIECE_PARTIAL", "DEMANDED_ACQUIRED_NECESSARY", "AUTRE")


def test_cell_A_known_answer_is_PARTIAL_with_ceiling_above_bar():
    out = harness_verdict_lecture(_db(), _rule())
    assert out["verdict"] == "PIECE_PARTIAL"
    assert out["demand"]["permute_key"]["verdict"] == "X_DEMANDED"
    assert out["demand"]["inject_distractor_slot"]["verdict"] == "X_DECOY"
    assert out["acquisition"]["verdict"] == "ACQUIRED" and out["acquisition"]["per_seed_above_ref"] == "12/12"
    assert out["acquisition"]["representational_ceiling_above_bar"] is True
    assert out["acquisition"]["bar_status"] == "CEILING_ABOVE_BAR"
    assert out["necessity"]["bilinear"]["verdict"] == "PIECE_PARTIAL"
    assert out["necessity"]["bilinear"]["sham"] == "PARAMS_NON_APPARIES"
    assert 0.0 <= out["e19"]["closure"] <= 2 / 3


def test_cell_B_known_answer_is_NECESSARY():
    out = harness_verdict_lecture(_db(D=0.18, D2=0.19), _rule("recurrent_state"))
    assert out["verdict"] == "DEMANDED_ACQUIRED_NECESSARY"
    assert out["necessity"]["recurrent_state"]["verdict"] == "NECESSARY"


def test_ablated_equal_to_intact_is_NOT_DEMANDED():
    # abl_key=0.93 (== A) tombe DANS la bande de bruit mesurée (ratio ~1,0 +- le même bruit que le noop
    # de A) : la branche atteinte est alors DEMAND_WITHIN_NOISE, plus sévère dans l'ORDRE 2.3-b -- ce
    # n'est pas le cas visé ici. 0,80 rend un ratio ~1,15, hors bande mais toujours dans la zone DECOY
    # (< 1,3) : un vrai « n'a pas mordu », distinct du cas « indiscernable du bruit ».
    assert harness_verdict_lecture(_db(abl_key=0.80), _rule())["verdict"] == "NOT_DEMANDED"


def test_ratio_inside_the_measured_noise_band_is_DEMAND_WITHIN_NOISE_never_decoy():
    db = _db(abl_key=0.88, noop=[0.93 / r for r in np.linspace(0.92, 1.08, 12)])   # bande [0.92 ; 1.08] mesurée
    out = harness_verdict_lecture(db, _rule())
    assert out["verdict"] == "DEMAND_WITHIN_NOISE"
    assert out["demand"]["permute_key"]["in_noise_band"] is True


def test_a_biting_control_is_INCONCLUSIVE_SPECIFICITY():
    assert harness_verdict_lecture(_db(abl_dist=[0.40] * 12), _rule())["verdict"] == "INCONCLUSIVE_SPECIFICITY"


def test_learner_at_reference_is_NOT_ACQUIRED_with_dose_and_saturation():
    out = harness_verdict_lecture(_db(A=0.18, A2=0.18, D=0.17, D2=0.17, abl_key=0.10, first=0.17), _rule())
    assert out["verdict"] == "NOT_ACQUIRED"
    # `dose` est publié PAR SEED (db["arms"][arm]["dose"] est déjà indexé seed -> dose.as_dict(), jamais
    # aplati par harness_verdict_lecture) : indexer par un seed pour lire le champ, pas directement.
    assert out["acquisition"]["dose"]["A"]["0"]["updates"] == 300
    assert out["acquisition"]["saturation"] in ("TENDANCE", "PLATEAU")


def test_reference_above_prior_max_is_INDETERMINE_HARNAIS_PRIOR_SOLVES():
    out = harness_verdict_lecture(_db(A0=0.60), _rule())
    assert out["verdict"] == "INDETERMINE_HARNAIS" and "PRIOR_SOLVES" in out["why"]


def test_oracle_below_min_is_INDETERMINE_HARNAIS():
    assert harness_verdict_lecture(_db(oracle=0.85), _rule())["verdict"] == "INDETERMINE_HARNAIS"


def test_piece_gap_that_closes_at_the_second_lr_is_LR_ARTIFACT():
    assert harness_verdict_lecture(_db(D=0.27, D2=0.88, A2=0.90), _rule())["verdict"] == "LR_ARTIFACT"


def test_intact_collapsed_at_the_second_lr_is_INDETERMINE_HARNAIS():
    # acquis à sweep[0] (0,93) mais l'intact tombe SOUS la barre au second pas (0,18) : la closure E19 n'a plus de référence
    assert harness_verdict_lecture(_db(A2=0.18, D2=0.17), _rule())["verdict"] == "INDETERMINE_HARNAIS"


def test_acquisition_null_that_vanishes_at_the_second_lr_is_LR_ARTIFACT():
    # inerte à sweep[0] (0,18 ~ référence) mais acquiert au second pas (0,90 sur 12/12) : nul d'acquisition NON robuste au pas
    assert harness_verdict_lecture(_db(A=0.18, A2=0.90, D=0.17, D2=0.30, first=0.17), _rule())["verdict"] == "LR_ARTIFACT"


def test_D_equal_to_A_is_PIECE_NOT_NECESSARY_and_both_at_ceiling_is_not_degenerate():
    db = _db(A=1.0, A2=1.0, D=1.0, D2=1.0, noop=[1.0] * 12, abl_dist=[1.0] * 12)
    db["eval"]["noop"]["D"] = _col([1.0] * 12)
    # `j()` tire un bruit INDÉPENDANT à chaque appel : A et D, mêmes 1.0 nominal, portent donc deux
    # bruits ~1e-3 distincts. Au plafond, cette différence est sans substance -- mais elle suffit à faire
    # fluctuer le petit écart(lr) de l'E19 de nécessité au point de le refermer « par hasard » de >2/3
    # (LR_ARTIFACT au lieu de PIECE_NOT_NECESSARY) : bruit de READING, pas un artefact de PAS. "D égal à
    # A" est le cas nominal du test -- le rendre bit-identique (jamais juste proche) retire ce faux
    # signal sans changer ce qui est mesuré : l'effet réel voulu ici est ZÉRO.
    db["arms"]["D"]["last"] = dict(db["arms"]["A"]["last"])
    db["arms"]["D2"]["last"] = dict(db["arms"]["A2"]["last"])
    out = harness_verdict_lecture(db, _rule())
    assert out["verdict"] == "PIECE_NOT_NECESSARY"


def test_missing_arm_is_INCOMPLET_and_n11_is_INCONCLUSIVE_N():
    db = _db()
    del db["arms"]["D2"]
    assert harness_verdict_lecture(db, _rule())["verdict"] == "INCOMPLET"
    db = _db()
    db["abandoned"]["D"] = [3]
    del db["arms"]["D"]["last"]["3"]
    assert harness_verdict_lecture(db, _rule())["verdict"] == "INCONCLUSIVE_N"


def test_nan_and_empty_raise_instead_of_fabricating():
    db = _db()
    db["arms"]["A"]["last"]["0"] = float("nan")
    with pytest.raises(ValueError, match="nan"):
        harness_verdict_lecture(db, _rule())
    with pytest.raises(ValueError, match="vide"):
        measure_noise_floor({}, {})


def test_noise_floor_band_is_min_max_of_paired_ratios():
    out = measure_noise_floor(_col([0.93] * 12), _col([0.93 / r for r in np.linspace(0.95, 1.05, 12)]))
    assert out["band"][0] == pytest.approx(0.95, abs=1e-6) and out["band"][1] == pytest.approx(1.05, abs=1e-6)


def test_necessity_uses_the_band_of_the_WEAK_arm_not_only_A():
    """R3 : a p = 0,27 la bande du bras D est large (+-18 %) ; un ratio A/D de 1,5 DANS la bande de D est WITHIN_NOISE."""
    db = _db(D=0.62, D2=0.62)                                  # ratio A/D = 1,5 : hors bande de A (+-1 %)...
    db["eval"]["noop"]["D"] = _col([0.62 / r for r in np.linspace(0.6, 1.6, 12)])   # ...mais DANS la bande de D
    out = harness_verdict_lecture(db, _rule())
    assert out["noise_floor"]["D"]["band"][1] > 1.5
    assert out["necessity"]["bilinear"]["in_noise_band"] is True and out["verdict"] == "PIECE_NOT_NECESSARY"


def test_mutating_necessity_threshold_to_strict_flips_the_boundary_case():
    """Porte 15 en miniature : med(D) == référence + min_sep exactement ; la règle dit <= -> NECESSARY."""
    db = _db(D=0.22, D2=0.22, A0=0.17)
    for s in SEEDS:
        db["arms"]["D"]["last"][str(s)] = 0.17 + 0.05
        db["arms"]["A0"]["last"][str(s)] = 0.17
    assert harness_verdict_lecture(db, _rule())["verdict"] == "DEMANDED_ACQUIRED_NECESSARY"


def test_measure_ablated_bayes_ceiling_certifies_the_declared_floor():
    """Décision 6 (task-5-brief §Gate 2) : la certification du Bayes-ceiling ABLATÉ sur une tâche RÉELLE
    (pas une db factice) — l'oracle sous `permute_key` doit noter ~1/K, dans la bande [declared ± 2 se],
    avec un espace d'états énumérable (CompositionTask.enumerate_states() = K*K)."""
    from tools.harness.tasks.composition import CompositionTask
    task = CompositionTask(K=6)
    ablation = next(a for a in task.demand.ablations if a.name == "permute_key")
    out = measure_ablated_bayes_ceiling(task, ablation, n=4096, seed=0)
    assert out["certified"] is True
    assert out["declared"] == pytest.approx(1 / 6)
    assert abs(out["measured"] - 1 / 6) <= 2.0 * out["se"]
