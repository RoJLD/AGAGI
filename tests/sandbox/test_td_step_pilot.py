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
    pytest.importorskip("torch")  # P2.121 famille 1 : exige torch, absent du runner CI -> SAUTÉ et dit
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
    pytest.importorskip("torch")  # P2.121 famille 1 : exige torch, absent du runner CI -> SAUTÉ et dit
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


_PUB2 = os.path.join(os.path.dirname(__file__), "..", "..", "results", "td_step_pilot_r2.json")


def _publie2():
    if not os.path.exists(_PUB2):
        return None
    db = json.load(open(_PUB2, encoding="utf-8"))
    return db if "_lecture" in db else None


@pytest.mark.skipif(_publie2() is None, reason="run TD-STEP-PILOT-R2 non encore publié (ou en cours)")
def test_r2_published_result_rereads_to_its_sealed_branch():
    """P2.110 (M-M11, E14) : R0 et R1 avaient leur témoin de relecture, R2 n'en avait AUCUN — la garde n'avait pas été
    rétro-appliquée. Posé AVANT de toucher `main_r2` : la refonte du cliquet de coût ne doit changer NI la lecture
    scellée NI les cellules importées (branche AIDE_A_UN_POINT, lr 1,0 seul coupé, relue à l'identique)."""
    from tools.td_step_pilot import _import_r2
    db = _publie2()
    imp = _import_r2(RULE2)
    assert all(db[k] == v for k, v in imp.items()), "les cellules importees ne sont plus celles de R0/R1"
    db.update(imp)
    lec = _lecture_r2(db, RULE2)
    assert lec == db["_lecture"] and lec["branche"] == "AIDE_A_UN_POINT" != "INCOMPLET"
    assert lec["lr_coupes"] == ["1.0"] and lec["lr_aide09"] == [4.0]


# ---- P2.110 : le cliquet de coût de R2, extrait en fonctions PURES et calibré sur son histoire ----------------------
# Constantes FIGÉES en littéraux (M-M10), jamais relues depuis results/ (dont la racine dépend d'AGAGI_RESULTS_ROOT) :
#   passe 1 -- commit f2d017fd : unité 217.44147491455078 s, projection acceptée 3587.784336090088 s ;
#   reprise -- commit 3d7c22b3 : unité 196.35169649124146 s, projection acceptée 10308.464065790176 s.
import copy  # noqa: E402

from tools.td_step_pilot import _decider_coupes_r2, _relever_coupe, _requalifier_r2  # noqa: E402

S2 = RULE2["seuils"]
U_PASSE1, P_PASSE1 = 217.44147491455078, 3587.784336090088
U_REPRISE, P_REPRISE = 196.35169649124146, 10308.464065790176
RAISON_PASSE1 = ("TD-STEP-PILOT-R2: 107 unités × 217.4s × marge 1.5 = 582 min > budget 240 min. Réduire n, réduire "
                 "l'unité, ou relever le budget EXPLICITEMENT — mais ne pas lancer en espérant que ça passe.")
# les cellules de la grille IMPORTÉES de R0/R1 (`_import_r2`, hors références) -- reconstruites depuis la STRUCTURE
_IMPORTEES_R2 = ({f"{b}|lr=4.0|seed={sd}" for b in ("lam0", "lam05", "lam09", "td0_d0") for sd in C2["seeds"]}
                 | {f"{b}|lr=2.0|seed={sd}" for b in ("lam0", "lam09") for sd in C2["seeds"]})


def _restantes(passe):
    """(cellule d'unité, restantes) comme `main_r2` les construisait : passe 1 = la grille moins les importées ;
    reprise = idem moins la ligne lr 4,0, mesurée entière à la passe 1."""
    r = [k for k in _cellules_r2(RULE2) if k not in _IMPORTEES_R2 and (passe == 1 or "|lr=4.0|" not in k)]
    return r[0], r[1:]


def _cles(lignes):
    return sorted(k for l in lignes for k in l["cles"])


def test_r2_imported_cells_reconstructed_from_structure_match_the_sealed_counts():
    assert len(_IMPORTEES_R2) + len(C2["references"]) * len(C2["seeds"]) == C2["cellules_importees"] == 96
    assert len(_cellules_r2(RULE2)) - len(_IMPORTEES_R2) == C2["cellules_neuves"] == 108


def test_r2_decider_reproduces_the_first_pass_BIT_FOR_BIT_and_the_reason_that_was_never_published():
    """Non-régression de l'extraction (M-M10, nommée comme telle) ET prédiction : depuis la seule structure et l'unité
    committée, la fonction rend les 96 clés et la projection au bit près, la raison de la ligne lr 1,0 au CARACTÈRE près
    (celle que publie coupes_precedentes[0]) -- et celle de lr 2,0, jamais publiée (le setdefault ne gardait que la
    première), que le record cite pourtant (255 min)."""
    k_u, rest = _restantes(1)
    assert k_u == "lam099|lr=4.0|seed=1" and len(rest) == 107
    gardees, lignes, proj = _decider_coupes_r2(rest, U_PASSE1, S2["budget_s"], S2["safety"])
    assert proj == P_PASSE1 and len(gardees) == 11 and all("|lr=4.0|" in k for k in gardees)
    assert [l["lr"] for l in lignes] == [1.0, 2.0] and [l["n_unites"] for l in lignes] == [107, 47]
    assert len(_cles(lignes)) == 96 and _cles(lignes) == sorted(k for k in rest if "|lr=4.0|" not in k)
    assert lignes[0]["raison"] == RAISON_PASSE1
    assert "47 unités × 217.4s" in lignes[1]["raison"] and "= 255 min > budget 240 min" in lignes[1]["raison"]


def test_r2_decider_reproduces_the_reprise_BIT_FOR_BIT():
    k_u, rest = _restantes(2)
    assert k_u == "lam05|lr=2.0|seed=1" and len(rest) == 95
    gardees, lignes, proj = _decider_coupes_r2(rest, U_REPRISE, S2["budget_s"], S2["safety"])
    assert proj == P_REPRISE and len(gardees) == 35 and [l["lr"] for l in lignes] == [1.0]
    assert len(lignes[0]["cles"]) == 60 and all("|lr=1.0|" in k for k in lignes[0]["cles"])
    assert "95 unités × 196.4s" in lignes[0]["raison"] and "= 466 min > budget 240 min" in lignes[0]["raison"]


@pytest.mark.skipif(_publie2() is None, reason="run TD-STEP-PILOT-R2 non encore publié (ou en cours)")
def test_r2_decider_matches_the_PUBLISHED_cuts():
    r = _publie2()["_regime"]
    h = r["coupes_precedentes"][0]
    assert (h["unite_s"], h["projection_s"], r["unite_s"], r["projection_s"]) == (U_PASSE1, P_PASSE1, U_REPRISE, P_REPRISE)
    _, l1, _ = _decider_coupes_r2(_restantes(1)[1], U_PASSE1, S2["budget_s"], S2["safety"])
    _, l2, _ = _decider_coupes_r2(_restantes(2)[1], U_REPRISE, S2["budget_s"], S2["safety"])
    assert _cles(l1) == sorted(h["coupe"]["cles"]) and l1[0]["raison"] == h["coupe"]["raison"]
    assert _cles(l2) == sorted(r["coupe"]["cles"])
    # la raison PUBLIÉE de la coupe courante est celle de la LEVÉE (P2.110 (i)) -- la vraie est rendue par la fonction
    assert "relevee" in r["coupe"]["raison"] and "95 unités" in l2[0]["raison"]


def test_r2_decider_has_BOTH_outcomes_on_the_real_geometry():
    """L'instrument peut produire les deux issues sur la géométrie RÉELLE : les 107 unités de la passe 1 à l'unité de la
    reprise ne coupent QUE lr 1,0 (230,7 min) ; à l'unité de la passe 1, lr 1,0 ET lr 2,0."""
    _, rest = _restantes(1)
    assert [l["lr"] for l in _decider_coupes_r2(rest, U_REPRISE, S2["budget_s"], S2["safety"])[1]] == [1.0]
    assert [l["lr"] for l in _decider_coupes_r2(rest, U_PASSE1, S2["budget_s"], S2["safety"])[1]] == [1.0, 2.0]


def test_r2_decider_noop_and_monotone_in_the_unit():
    _, rest = _restantes(1)
    gardees, lignes, proj = _decider_coupes_r2(rest, U_PASSE1, float("inf"), S2["safety"])
    assert gardees == rest and lignes == [] and proj == U_PASSE1 * 107 * S2["safety"]     # budget infini : no-op EXACT
    n_lignes = [len(_decider_coupes_r2(rest, u, S2["budget_s"], S2["safety"])[1])
                for u in (10.0, 89.0, 90.0, 150.0, 204.2, 204.3, U_PASSE1, 1000.0, 1e9)]
    assert n_lignes == sorted(n_lignes) and n_lignes[0] == 0 and n_lignes[-1] == 3
    gardees, lignes, proj = _decider_coupes_r2(rest, 1e9, S2["budget_s"], S2["safety"])
    assert gardees == [] and proj is None and [l["lr"] for l in lignes] == [1.0, 2.0, 4.0]      # tout coupé : pas de projection


def test_r2_lifting_a_cut_moves_it_to_history_as_a_DEEP_copy_and_writes_the_lift_reason_there_only():
    """M-M13 / I-RAISON-PAR-LIGNE : fonction PURE ; l'historique ne partage aucun objet avec le régime vivant ; la raison
    de la LEVÉE va dans l'historique, jamais dans `coupe` (une reprise sans coupe laissait une raison et zéro clé)."""
    regime = {"K": 6, "unite_s": U_PASSE1, "projection_s": P_PASSE1, "unite_cle": "lam099|lr=4.0|seed=1",
              "coupe": {"cles": ["a|lr=1.0|seed=1"], "raison": RAISON_PASSE1}, "coupes_precedentes": [{"ancienne": 1}]}
    avant = copy.deepcopy(regime)
    r = _relever_coupe(regime, relevee_a="2026-09-24 11:29", replique={"cle": "lam099|lr=4.0|seed=1", "mur_s": 1.0})
    assert regime == avant                                                    # l'entrée n'est pas touchée
    assert not {"coupe", "unite_s", "projection_s", "unite_cle"} & set(r) and r["K"] == 6
    assert r["coupes_precedentes"][0] == {"ancienne": 1} and len(r["coupes_precedentes"]) == 2
    h = r["coupes_precedentes"][-1]
    assert (h["coupe"], h["unite_s"], h["projection_s"], h["relevee_a"]) == (avant["coupe"], U_PASSE1, P_PASSE1, "2026-09-24 11:29")
    assert h["unite_cle"] == "lam099|lr=4.0|seed=1" and h["replique_unite"]["mur_s"] == 1.0
    assert "relever-coupe" in h["raison_levee"]
    h["coupe"]["cles"].append("MUTE")
    assert regime["coupe"]["cles"] == ["a|lr=1.0|seed=1"]                     # aucun alias


def test_r2_requalifying_the_PUBLISHED_history_publishes_the_issue_but_NOT_a_cause():
    """M-M6 / M-M2 : l'historique publié de R2 n'a ni lignes, ni cellule d'unité, ni charge ; les deux unités viennent de
    deux cellules DIFFÉRENTES. L'issue (re-coupée / récupérée) est un fait ; la cause reste `indeterminee`."""
    _, l1, _ = _decider_coupes_r2(_restantes(1)[1], U_PASSE1, S2["budget_s"], S2["safety"])
    _, l2, _ = _decider_coupes_r2(_restantes(2)[1], U_REPRISE, S2["budget_s"], S2["safety"])
    entree = {"unite_s": U_PASSE1, "projection_s": P_PASSE1, "coupe": {"cles": _cles(l1), "raison": RAISON_PASSE1}}
    q = _requalifier_r2(entree, _cles(l2), budget_s=S2["budget_s"], safety=S2["safety"])
    assert {lr: (v["issue"], v["nature"]) for lr, v in q.items()} == \
        {"1.0": ("confirmee", "indeterminee"), "2.0": ("recuperee", "indeterminee")}


def _harnais_main_r2(monkeypatch, tmp_path):
    """`main_r2` de bout en bout SANS entraînement ni vraie lecture de charge (recette I-TEST-MAIN-R2) : horloge FACTICE
    avancée de `conf["duree"]` par cellule, charge extérieure injectée à dose CONNUE `conf["ext"]` (None = illisible),
    capteur LENT de `conf["lent"]` s par lecture (M-M5), sceaux et imports de R0/R1 remplacés, résultats sous tmp_path."""
    import tools.td_step_pilot as tsp
    from tools.cost_guard import LoadWindow, Stopwatch
    conf = {"t": 0.0, "duree": U_PASSE1, "ext": 12.0, "lent": 0.0, "acc": 0.2}
    mur, cpu = (lambda: conf["t"]), (lambda: 0.9 * conf["t"])

    def occupation():
        conf["t"] += conf["lent"]
        return None if conf["ext"] is None else (conf["ext"] + 0.9) * conf["t"]

    def entraine(seed, lam, episodes, n_agents, K, lr, eval_batches=40, trace_reset_per_episode=True, same_tick=False):
        conf["t"] += conf["duree"]
        return conf["acc"], {"updates": 1}
    imports = {k: 0.2 for k in _IMPORTEES_R2}
    imports.update({f"{r}|seed={sd}": 0.15 for r in C2["references"] for sd in C2["seeds"]})
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path))
    monkeypatch.setattr(tsp, "_import_r2", lambda regle: dict(imports))
    monkeypatch.setattr(tsp, "_train_eval_td_step", entraine)
    monkeypatch.setattr(tsp, "stamp", lambda db, name: db)
    monkeypatch.setattr(tsp, "Stopwatch", lambda: Stopwatch(wall_clock=mur, cpu_clock=cpu))
    monkeypatch.setattr(tsp, "LoadWindow", lambda: LoadWindow(busy_reader=occupation, cpu_clock=cpu, wall_clock=mur))
    return tsp, conf


def test_r2_main_end_to_end_cut_then_declared_reprise_with_SAME_CELL_replica(monkeypatch, tmp_path):
    """L'histoire de R2 rejouée à dose CONNUE : passe 1 à 217,4 s sous 12 cœurs extérieurs (chargée) -> deux lignes,
    `contention` provisoire ; reprise déclarée à 196,4 s sous 3 cœurs (libre) : la cellule d'unité de la passe 1 est
    RÉPLIQUÉE d'abord (même échauffement, exactitude bit-identique, rien de re-persisté), puis la décision rend lr 1,0
    seule, avec SA raison (jamais celle de la levée) ; l'historique est intact et re-qualifié par la réplique :
    lr 1,0 re-coupée -> `structure`, lr 2,0 récupérée -> `contention` ÉTABLIE."""
    tsp, conf = _harnais_main_r2(monkeypatch, tmp_path)
    db = tsp.main_r2([])
    r = db["_regime"]
    assert (r["unite_s"], r["unite_cle"], r["projection_s"]) == (U_PASSE1, "lam099|lr=4.0|seed=1", P_PASSE1)
    assert r["unite_cpu_s"] == pytest.approx(0.9 * U_PASSE1) and r["charge_unite"]["coeurs_exterieurs"] == pytest.approx(12.0)
    assert r["marge_au_seuil"] == pytest.approx(0.7508, abs=1e-4)
    cp = r["coupe"]
    assert len(cp["cles"]) == 96 and [l["lr"] for l in cp["lignes"]] == [1.0, 2.0]
    assert cp["lignes"][0]["raison"] == RAISON_PASSE1 and "47 unités" in cp["lignes"][1]["raison"]
    assert [l["nature"] for l in cp["lignes"]] == ["contention", "contention"]
    assert [round(l["depassement"], 3) for l in cp["lignes"]] == [2.424, 1.065]          # les DEUX distances au seuil
    assert len(db["_temps_s"]) == 12 and all(set(t) >= {"mur_s", "cpu_s", "coeurs_exterieurs"} for t in db["_temps_s"].values())
    assert tsp._lecture_r2(db, RULE2)["lr_coupes"] == ["1.0", "2.0"]
    conf.update(t=0.0, duree=U_REPRISE, ext=3.0)
    db2 = tsp.main_r2(["--relever-coupe"])
    r2 = db2["_regime"]
    assert (r2["unite_s"], r2["unite_cle"], r2["projection_s"]) == (U_REPRISE, "lam05|lr=2.0|seed=1", P_REPRISE)
    assert len(r2["coupe"]["cles"]) == 60 and [l["lr"] for l in r2["coupe"]["lignes"]] == [1.0]
    assert "95 unités" in r2["coupe"]["raison"] and "relevee" not in r2["coupe"]["raison"]
    assert "--relever-coupe" not in r2["coupe"]["raison"]
    assert r2["coupe"]["lignes"][0]["nature"] == "structure"                            # fenêtre libre
    h = r2["coupes_precedentes"][-1]
    assert sorted(h["coupe"]["cles"]) == cp["cles"] and h["coupe"]["lignes"][0]["raison"] == RAISON_PASSE1
    assert h["unite_s"] == U_PASSE1 and "relever-coupe" in h["raison_levee"]
    rep = h["replique_unite"]
    assert rep["cle"] == "lam099|lr=4.0|seed=1" and rep["exactitude_identique"] is True and rep["mur_s"] == U_REPRISE
    assert rep["facteur_charge"] == pytest.approx(U_PASSE1 / U_REPRISE)
    assert db2["_temps_s"]["lam099|lr=4.0|seed=1"]["mur_s"] == U_PASSE1                  # la réplique n'écrase RIEN
    assert {lr: (v["issue"], v["nature"]) for lr, v in h["requalification"].items()} == \
        {"1.0": ("confirmee", "structure"), "2.0": ("recuperee", "contention")}
    assert tsp._lecture_r2(db2, RULE2)["lr_coupes"] == ["1.0"]
    cpb = r2["cout_par_bras_a_posteriori"]
    assert cpb["projection_par_bras_s"] is None and cpb["bras_sans_unite"] == ["lam0", "lam09"]   # jamais fabriquée
    assert cpb["unite_sur_mediane_du_bras"] == pytest.approx(1.0)


def test_r2_main_a_slow_load_sensor_never_enters_the_sealed_unit(monkeypatch, tmp_path):
    """M-M5 (E11) : `doctor.project_processes()` coûte 7 à 25 s ; posé DANS la fenêtre chronométrée, un capteur gonflait
    l'unité scellée de 4 à 6 % -- l'écart qui a coupé lr 2,0. Capteur lent de 10 s par lecture : unité IDENTIQUE."""
    tsp, conf = _harnais_main_r2(monkeypatch, tmp_path)
    conf["lent"] = 10.0
    r = tsp.main_r2([])["_regime"]
    assert r["unite_s"] == U_PASSE1 and r["projection_s"] == P_PASSE1 and len(r["coupe"]["cles"]) == 96


def test_r2_main_a_reprise_without_new_cut_leaves_neither_reason_nor_empty_cut(monkeypatch, tmp_path):
    """I-RAISON-PAR-LIGNE : l'ancienne levée écrivait `coupe = {cles: [], raison: "relevee..."}` ; une reprise qui ne
    coupe plus rien laissait donc une raison et zéro clé. Ici : pas de `coupe` du tout, et une réplique dont la charge
    est ILLISIBLE ne prouve rien -- la nature re-qualifiée retombe sur la charge d'origine (chargée -> contention)."""
    tsp, conf = _harnais_main_r2(monkeypatch, tmp_path)
    tsp.main_r2([])
    conf.update(t=0.0, duree=50.0, ext=None)
    r = tsp.main_r2(["--relever-coupe"])["_regime"]
    assert "coupe" not in r and r["charge_unite"]["coeurs_exterieurs"] is None
    q = r["coupes_precedentes"][-1]["requalification"]
    assert {lr: (v["issue"], v["nature"]) for lr, v in q.items()} == \
        {"1.0": ("recuperee", "contention"), "2.0": ("recuperee", "contention")}
