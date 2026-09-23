"""Lecture scellée de `TD-STEP-PILOT-R0` (`tools/td_step_pilot.py::_lecture`) — chaque branche atteinte par une base
synthétique, dans l'ORDRE IMPOSÉ (les deux contrôles AVANT toute lecture des bras TD) ; la fin d'épisode
(`_flush_terminal`) confrontée à une réponse connue ; le résultat publié relu contre la règle. Aucun entraînement
long ici."""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

_LEASE_GUARD_EXEMPT = True          # torch pur, aucun monde : la garde de bail n'a rien a proteger ici

from tools.preregister import verify  # noqa: E402
from tools.td_step_pilot import _flush_terminal, _lecture, _train_eval_td_step  # noqa: E402

RULE = verify("TD-STEP-PILOT-R0")
C = RULE["cellule"]
S = RULE["seuils"]
BRAS = C["bras"]


def _db(td0=0.18, tdlam=0.18, ref=0.15, d0=0.52, ref_d0=0.17, bptt=0.80, per_seed=None):
    db = {}
    for sd in C["seeds"]:
        v = {"td0": td0, "tdlam": tdlam, "lr0_reference": ref, "td0_d0": d0, "lr0_reference_d0": ref_d0, "bptt": bptt}
        if per_seed:
            v.update(per_seed(sd))
        for i in range(2):
            for b in BRAS:
                db[f"{b}|lr{i}|seed={sd}"] = v[b]
    return db


def test_the_rule_declares_the_seed_0_smokes_and_excludes_seed_0():
    assert 0 not in C["seeds"] and len(C["seeds"]) == 12
    assert "seed 0 SEUL" in RULE["provenance"] and "0,798" in RULE["provenance"] and "0,52" in RULE["provenance"]
    assert C["lr_td_par_agent"] == [lr / C["n_agents"] for lr in C["lr_td"]]


def test_incomplete_gives_no_reading():
    db = _db()
    del db["bptt|lr1|seed=12"]
    assert _lecture(db, RULE) == {"branche": "INCOMPLET", "manquantes": 1}


def test_substrate_control_failing_blocks_every_reading_even_when_td0_would_learn():
    lec = _lecture(_db(td0=0.9, bptt=0.30), RULE)
    assert lec["branche"] == "CONTROLE_SUBSTRAT_ECHOUE"


def test_credit_path_control_failing_blocks_the_D1_reading_even_when_td0_would_learn():
    lec = _lecture(_db(td0=0.9, d0=0.18, ref_d0=0.17), RULE)
    assert lec["branche"] == "CONTROLE_CHEMIN_ECHOUE" and lec["td0_d0_sup_ref_d0"] == ["0/12", "0/12"]


def test_known_negative_TD0_inert_and_trace_neutral():
    lec = _lecture(_db(), RULE)
    assert lec["branche"] == "TD0_INERTE|TRACE_NEUTRE" and lec["td0_sup_ref"] == ["0/12", "0/12"]


def test_TD0_learns_needs_ten_seeds_not_a_median():
    # 9/12 seeds au-dessus de la référence + marge : médiane au-dessus, mais < 10/12 -> INERTE
    db = _db(per_seed=lambda sd: {"td0": 0.40 if sd <= 9 else 0.15})
    lec = _lecture(db, RULE)
    assert lec["td0_sup_ref"] == ["9/12", "9/12"] and lec["branche"].startswith("TD0_INERTE")
    db = _db(per_seed=lambda sd: {"td0": 0.40 if sd <= 10 else 0.15})
    assert _lecture(db, RULE)["branche"].startswith("TD0_APPREND")


def test_trace_helps_is_tested_before_trace_hurts_and_at_either_step():
    assert _lecture(_db(tdlam=0.30), RULE)["branche"] == "TD0_INERTE|TRACE_AIDE"
    assert _lecture(_db(td0=0.30, tdlam=0.18), RULE)["branche"] == "TD0_APPREND|TRACE_NUIT"   # td0 0,30 > réf 0,15
    # aide au seul pas 1 (E19 : l'un des deux pas suffit pour AIDE, la règle le dit)
    db = _db()
    for sd in C["seeds"]:
        db[f"tdlam|lr1|seed={sd}"] = 0.30
    assert _lecture(db, RULE)["branche"] == "TD0_INERTE|TRACE_AIDE"


def test_flush_terminal_applies_the_deferred_update_with_a_zero_bootstrap_and_clears_the_transition():
    import torch
    from src.agents.backend_torch import TorchPopulationModel as T
    from src.agents.mamba_agent import MambaAgent
    saved = (T.BILINEAR, T.CREDIT_TRACE_LAMBDA)
    T.BILINEAR, T.CREDIT_TRACE_LAMBDA = False, 0.0
    try:
        np.random.seed(0)
        torch.manual_seed(0)
        pop = T([MambaAgent() for _ in range(2)], lr=0.04)
        obs = np.random.RandomState(1).uniform(-1, 1, (2, pop.I)).astype(np.float32)
        pop.forward(obs)
        assert pop.learn(np.ones(2, np.float32), [{"move": 1}, {"move": 2}]) is None    # différé
        W0 = pop.W.detach().clone()
        _flush_terminal(pop, 2)
        assert pop._prev is None and not torch.equal(pop.W, W0)                       # la mise à jour a eu lieu
        W1 = pop.W.detach().clone()
        _flush_terminal(pop, 2)                                                        # rien à vider : no-op exact
        assert torch.equal(pop.W, W1)
    finally:
        T.BILINEAR, T.CREDIT_TRACE_LAMBDA = saved


def test_td_step_trainer_publishes_its_dose_and_lr0_moves_no_weight():
    acc, dose = _train_eval_td_step(0, 0.9, 3, 4, 4, 0.0, eval_batches=2, same_tick=False)
    assert 0.0 <= acc <= 1.0 and dose["updates"] == 6 and dose["trace_updates"] == 6 and dose["trace_resets"] == 3
    assert dose["lr_effective_per_agent"] == 0.0


_PUB = os.path.join(os.path.dirname(__file__), "..", "..", "results", "td_step_pilot_r0.json")


def _publie():
    if not os.path.exists(_PUB):
        return None
    db = json.load(open(_PUB, encoding="utf-8"))
    return db if "_lecture" in db else None


@pytest.mark.skipif(_publie() is None, reason="run TD-STEP-PILOT-R0 non encore publié (ou en cours)")
def test_published_result_rereads_to_its_sealed_branch():
    db = _publie()
    lec = _lecture(db, RULE)
    assert lec["branche"] == db["_lecture"]["branche"] != "INCOMPLET"
    assert all(db["_dose"][k]["updates"] > 0 for k in db["_dose"])


# ---- R1 : invariance au pas + dose en lambda -------------------------------------------------------------------
from tools.td_step_pilot import _lecture_r1  # noqa: E402

RULE1 = verify("TD-STEP-PILOT-R1")
C1 = RULE1["cellule"]


def _db1(td0_2=0.18, tl_2=0.25, ref_2=0.16, tl05_4=0.245, td0_4=0.19, tl09_4=0.25, ref_4=0.16, per_seed=None):
    db = {}
    for sd in C1["seeds"]:
        v = {"td0@2": td0_2, "tdlam09@2": tl_2, "lr0_reference@2": ref_2, "tdlam05@4": tl05_4,
             "td0@4": td0_4, "tdlam09@4": tl09_4, "lr0_reference@4": ref_4}
        if per_seed:
            v.update(per_seed(sd))
        for b, x in v.items():
            db[f"{b}|seed={sd}"] = x
    return db


def test_r1_rule_declares_the_import_from_R0_and_never_measured_cells():
    assert "IMPORTEES de R0" in RULE1["provenance"] and "JAMAIS ete mesures" in RULE1["provenance"]
    assert C1["lr_nouveau_par_agent"] == C1["lr_nouveau"] / C1["n_agents"]


def test_r1_incomplete_when_an_imported_cell_is_missing():
    db = _db1()
    del db["td0@4|seed=3"]
    assert _lecture_r1(db, RULE1) == {"branche": "INCOMPLET", "manquantes": 1}


def test_r1_invariant_and_monotone():
    assert _lecture_r1(_db1(), RULE1)["branche"] == "AIDE_INVARIANTE|DOSE_LAMBDA_MONOTONE"


def test_r1_non_invariant_is_read_independently_of_the_lambda_dose():
    assert _lecture_r1(_db1(tl_2=0.19), RULE1)["branche"] == "AIDE_NON_INVARIANTE|DOSE_LAMBDA_MONOTONE"


def test_r1_lambda_saturated_and_absent():
    assert _lecture_r1(_db1(tl05_4=0.26), RULE1)["branche"] == "AIDE_INVARIANTE|DOSE_LAMBDA_SATUREE"   # 0,5 >= 0,9
    assert _lecture_r1(_db1(tl05_4=0.20), RULE1)["branche"] == "AIDE_INVARIANTE|DOSE_LAMBDA_ABSENTE"


def test_r1_ten_seeds_convention_on_the_invariance_clause():
    db = _db1(per_seed=lambda sd: {"tdlam09@2": 0.25 if sd <= 9 else 0.19})
    assert _lecture_r1(db, RULE1)["tdlam09@2_sup_td0@2"] == "9/12" and _lecture_r1(db, RULE1)["branche"].startswith("AIDE_NON")


_PUB1 = os.path.join(os.path.dirname(__file__), "..", "..", "results", "td_step_pilot_r1.json")


def _publie1():
    if not os.path.exists(_PUB1):
        return None
    db = json.load(open(_PUB1, encoding="utf-8"))
    return db if "_lecture" in db else None


@pytest.mark.skipif(_publie1() is None, reason="run TD-STEP-PILOT-R1 non encore publié (ou en cours)")
def test_r1_published_result_rereads_to_its_sealed_branch_with_imported_cells_equal_to_R0():
    from tools.td_step_pilot import _import_r0
    db = _publie1()
    imp = _import_r0(RULE1)
    assert all(db[k] == v for k, v in imp.items()), "les cellules importees ne sont plus celles de R0"
    assert _lecture_r1(db, RULE1)["branche"] == db["_lecture"]["branche"] != "INCOMPLET"


# ---- R2 (P4.17) : grille lr x lambda ---------------------------------------------------------------------------
from tools.td_step_pilot import _cellules_r2, _lecture_r2  # noqa: E402

RULE2 = verify("TD-STEP-PILOT-R2")
C2 = RULE2["cellule"]


def _db2(aide_at=(), lisible_at=None, per=None, coupe=()):
    """Base synthetique : par lr, lam0 0,19 ; lam09 = 0,26 si lr in aide_at sinon 0,19 ; td0_d0 0,52 si lisible sinon 0,18."""
    lisible_at = C2["lr"] if lisible_at is None else lisible_at
    db = {"_regime": {"coupe": {"cles": [k for k in _cellules_r2(RULE2) if any(f"|lr={lr}|" in k for lr in coupe)]}}}
    for sd in C2["seeds"]:
        db[f"lr0_reference|seed={sd}"] = 0.16
        db[f"lr0_reference_d0|seed={sd}"] = 0.17
        for lr in C2["lr"]:
            if lr in coupe:
                continue
            v = {"lam0": 0.19, "lam05": 0.20, "lam09": 0.26 if lr in aide_at else 0.19, "lam099": 0.21,
                 "td0_d0": 0.52 if lr in lisible_at else 0.18}
            if per:
                v.update(per(lr, sd))
            for b_, x in v.items():
                db[f"{b_}|lr={lr}|seed={sd}"] = x
    return db


def test_r2_rule_declares_the_imports_and_the_dropped_lrs():
    assert "IMPORTEES" in RULE2["provenance"] and "ECARTE" in RULE2["provenance"] and 0.5 not in C2["lr"] and 8.0 not in C2["lr"]
    assert len(_cellules_r2(RULE2)) == 5 * 3 * 12


def test_r2_incomplete_then_branches_in_the_imposed_order():
    db = _db2(aide_at=(4.0, 2.0))
    del db["lam099|lr=1.0|seed=5"]
    assert _lecture_r2(db, RULE2) == {"branche": "INCOMPLET", "manquantes": 1}
    assert _lecture_r2(_db2(aide_at=(4.0, 2.0)), RULE2)["branche"] == "AIDE_INVARIANTE"          # deux lr adjacents
    assert _lecture_r2(_db2(aide_at=(4.0,)), RULE2)["branche"] == "AIDE_A_UN_POINT"
    assert _lecture_r2(_db2(aide_at=(4.0, 1.0)), RULE2)["branche"] == "AIDE_A_UN_POINT"          # non adjacents
    assert _lecture_r2(_db2(aide_at=()), RULE2)["branche"] == "PAS_D_AIDE"
    lec = _lecture_r2(_db2(aide_at=(4.0, 2.0), lisible_at=()), RULE2)
    assert lec["branche"] == "CONTROLE_CHEMIN_ECHOUE" and lec["lr_lisibles"] == []


def test_r2_an_unreadable_lr_does_not_count_even_if_the_trace_helps_there():
    lec = _lecture_r2(_db2(aide_at=(4.0, 2.0), lisible_at=(4.0,)), RULE2)
    assert lec["branche"] == "AIDE_A_UN_POINT" and lec["lr_aide09"] == [4.0] and lec["par_lr"]["2.0"]["lisible"] is False


def test_r2_eleven_seeds_convention_and_published_lambda_facts():
    db = _db2(aide_at=(4.0, 2.0), per=lambda lr, sd: ({"lam09": 0.19} if (lr == 2.0 and sd in (1, 2)) else {}))
    lec = _lecture_r2(db, RULE2)
    assert lec["par_lr"]["2.0"]["aide09"] == "10/12" and lec["branche"] == "AIDE_A_UN_POINT"
    assert lec["par_lr"]["4.0"]["meilleur_lambda"] == "lam09" and lec["par_lr"]["4.0"]["aide099"] == "0/12"


def test_r2_a_cut_lr_line_is_neither_missing_nor_readable_and_is_published():
    lec = _lecture_r2(_db2(aide_at=(4.0, 2.0), coupe=(1.0,)), RULE2)
    assert lec["branche"] == "AIDE_INVARIANTE" and lec["lr_coupes"] == ["1.0"] and lec["par_lr"]["1.0"] == {"coupe": True}
