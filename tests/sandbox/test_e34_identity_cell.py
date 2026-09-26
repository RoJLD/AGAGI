"""E34 (P2.132) — `E34-IDENTITY-CELL` : calibration du runner de la sonde (tools/evo_runs/e34_identity_cell.py).

À réponse CONNUE : (1) le VERDICT (pur, lignes synthétiques, branches dans l'ordre scellé, égalités sur la grille
0,5 aux deux bords de la bande) ; (2) la bande et S_a LUS dans le JSON SUIVI de P4.16 (une prémisse est une mesure) ;
(3) le témoin du code contre la cellule publiée de P4.4 — identique à elle-même, rompu par UN ulp de Σ|ΔW| ou UN
âge ; (4) `run_identity_cell` : garde en tête, drapeau et audit TRANSMIS à la phase 1 (injection, sans torch), et un
appel réel minuscule (monde, torch, 2 agents, 3 + 2 ticks : sauté par conftest quand un run tient `kuzu`).
"""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.evo_runs import e34_identity_cell as R  # noqa: E402

BAND = {"min": 7.0, "max": 9.5, "values": [7.0] * 6 + [9.5] * 6, "n": 12}


def _row(s, td=1999, mis=40, total=24000, fix="off", moved=None, res=12, dw=18242.0):
    ident = {"slot_ticks_misaligned": mis, "slot_ticks_total": total, "slot_order_fix": fix == "on",
             "positions_reordered": moved}
    return {"arm": fix, "learning": {"td_updates": td, "resurrections": res, "dW_abs_sum": dw, "slot_identity": ident},
            "survival": {"survival_median": s}}


OK = {"identical": True, "reason": "bit-identique"}


def _v(s_on, s_off=7.0, witness=OK, **kw):
    return R.identity_cell_verdict(_row(s_off), _row(s_on, mis=0, fix="on", moved=30, **kw), witness, BAND, 31.5)


# --------------------------------------------------------------------------------------------------
# 1. Le verdict — branches dans l'ordre scellé.
# --------------------------------------------------------------------------------------------------


def test_verdict_INCOMPLET_when_a_cell_or_the_witness_is_missing():
    assert R.identity_cell_verdict(None, _row(8.0, mis=0, fix="on"), OK, BAND, 31.5)["verdict"] == "INCOMPLET"
    assert R.identity_cell_verdict(_row(7.0), None, OK, BAND, 31.5)["verdict"] == "INCOMPLET"
    assert R.identity_cell_verdict(_row(7.0), _row(8.0, mis=0, fix="on"), None, BAND, 31.5)["verdict"] == "INCOMPLET"


def test_verdict_refuses_non_finite_inputs_and_a_missing_audit():
    with pytest.raises(ValueError):
        _v(float("nan"))
    bad = _row(7.0)
    del bad["learning"]["slot_identity"]
    with pytest.raises(ValueError):
        R.identity_cell_verdict(bad, _row(8.0, mis=0, fix="on"), OK, BAND, 31.5)
    with pytest.raises(ValueError):
        R.identity_cell_verdict(_row(7.0), _row(8.0, mis=0, fix="on"), OK, dict(BAND, n=11), 31.5)
    with pytest.raises(ValueError):
        R.identity_cell_verdict(_row(7.0), _row(8.0, mis=0, fix="on"), OK, BAND, float("nan"))


def test_verdict_refuses_an_on_arm_that_did_not_hold_the_invariant():
    with pytest.raises(ValueError):
        R.identity_cell_verdict(_row(7.0), _row(8.0, mis=3, fix="on"), OK, BAND, 31.5)
    with pytest.raises(ValueError):                                     # « allumé » qui ne l'est pas
        R.identity_cell_verdict(_row(7.0), _row(8.0, mis=0, fix="off"), OK, BAND, 31.5)


def test_verdict_TEMOIN_ROMPU_before_any_reading():
    v = _v(20.0, witness={"identical": False, "reason": "Σ|ΔW| différent"})
    assert v["verdict"] == "TEMOIN_ROMPU" and "fort" not in v


def test_verdict_SANS_OBJET_when_the_published_cell_had_no_misalignment():
    v = R.identity_cell_verdict(_row(7.0, mis=0), _row(20.0, mis=0, fix="on"), OK, BAND, 31.5)
    assert v["verdict"] == "SANS_OBJET"


def test_verdict_INDETERMINE_DOSE_when_the_on_arm_got_no_credit():
    assert _v(20.0, td=999)["verdict"] == "INDETERMINE_DOSE"
    assert _v(20.0, td=1000)["verdict"] == "MATERIEL_HAUSSE"


def test_verdict_band_edges_on_the_half_tick_grid():
    """Les bords APPARTIENNENT à la bande (une égalité n'est pas un dépassement) : 9,5 et 7,0 NON_MATERIEL,
    10,0 et 6,5 MATERIEL."""
    assert _v(9.5)["verdict"] == "NON_MATERIEL"
    assert _v(7.0)["verdict"] == "NON_MATERIEL"
    assert _v(10.0)["verdict"] == "MATERIEL_HAUSSE"
    assert _v(6.5)["verdict"] == "MATERIEL_BAISSE"


def test_verdict_FORT_is_descriptive_and_never_a_second_road_to_MATERIEL():
    """H0 = « le drapeau n'est qu'une trajectoire de plus » : S_on est lu contre la dispersion ENTRE SEEDS ; |dS|
    >= DELTA_MIN n'est qu'une étiquette. Un S_off hors bande avec un grand |dS| et S_on dans la bande reste
    NON_MATERIEL."""
    assert _v(12.0)["fort"] is True and _v(12.0)["verdict"] == "MATERIEL_HAUSSE"          # |dS| = 5,0 : égalité
    assert _v(11.5)["fort"] is False and _v(11.5)["verdict"] == "MATERIEL_HAUSSE"
    v = R.identity_cell_verdict(_row(2.0), _row(8.0, mis=0, fix="on", moved=3), OK, BAND, 31.5)
    assert v["verdict"] == "NON_MATERIEL" and v["fort"] is True


def test_verdict_publishes_the_reading_the_thresholds_and_the_h0_false_alarm():
    v = _v(13.0)
    assert v["S_off"] == 7.0 and v["S_on"] == 13.0 and v["dS"] == 6.0 and v["S_a"] == 31.5
    assert v["erosion_off"] == 24.5 and v["part_erosion_levee"] == pytest.approx(6.0 / 24.5)
    assert v["thresholds"] == {"band_min": 7.0, "band_max": 9.5, "band_n": 12, "dose_min": 1000, "delta_min": 5.0,
                               "n_grille": 2}
    assert v["fausse_alarme_h0"] == pytest.approx(2.0 / 13.0)
    assert v["misaligned_off"] == 40 and v["slot_ticks_off"] == 24000 and v["positions_reordered_on"] == 30


def test_verdict_part_erosion_is_None_not_a_number_without_erosion():
    v = R.identity_cell_verdict(_row(40.0), _row(8.0, mis=0, fix="on"), OK, BAND, 31.5)
    assert v["part_erosion_levee"] is None


# --------------------------------------------------------------------------------------------------
# 2. Bande et S_a : LUS dans le JSON suivi de P4.16.
# --------------------------------------------------------------------------------------------------


def test_published_band_and_frozen_are_read_from_the_tracked_P416_results():
    b = R.published_band()
    assert (b["min"], b["max"], b["n"]) == (7.0, 9.5, 12)
    assert R.published_frozen(2026) == 31.5


def test_published_band_refuses_a_missing_seed(tmp_path):
    rows = {str(2026 + i): {"survival": {"survival_median": 8.0}} for i in range(11)}
    p = tmp_path / "p416.json"
    p.write_text(json.dumps({"arms": {"b_full": rows, "a_frozen": {}}}), encoding="utf-8")
    with pytest.raises(ValueError):
        R.published_band(str(p))
    rows["2037"] = {"survival": {"survival_median": None}}
    p.write_text(json.dumps({"arms": {"b_full": rows, "a_frozen": {}}}), encoding="utf-8")
    with pytest.raises(ValueError):
        R.published_band(str(p))
    with pytest.raises(ValueError):
        R.published_frozen(2026, str(p))


# --------------------------------------------------------------------------------------------------
# 3. Le témoin du code, contre la cellule PUBLIÉE de P4.4.
# --------------------------------------------------------------------------------------------------


def _published_row():
    from tools.evo_runs.s2_reward_ablation import P44_FULL_ARM, _load_p44
    ref = _load_p44()["arms"][P44_FULL_ARM]["2026"]
    row = {k: json.loads(json.dumps(ref[k])) for k in ("num_agents", "ticks_learn", "ticks_test", "learning",
                                                        "survival")}
    row["learning"]["slot_identity"] = {"slot_ticks_misaligned": 1, "slot_ticks_total": 24000}
    return row


def test_witness_is_identical_to_the_published_cell_itself():
    w = R.witness_check(_published_row(), 2026)
    assert w["identical"] is True and w["reason"] == "bit-identique" and w["same_dW_abs_sum"] is True
    assert w["p44_dW_abs_sum"] == 18242.03954219818


def test_witness_breaks_on_one_ulp_of_dW_or_one_age():
    row = _published_row()
    row["learning"]["dW_abs_sum"] = float(np.nextafter(row["learning"]["dW_abs_sum"], np.inf))
    w = R.witness_check(row, 2026)
    assert w["identical"] is False and w["reason"] == "Σ|ΔW| différent"
    row = _published_row()
    row["survival"]["ages"][0] += 1
    w = R.witness_check(row, 2026)
    assert w["identical"] is False and w["reason"] == "ages differents"


# --------------------------------------------------------------------------------------------------
# 4. `run_identity_cell` : garde en tête, transmission du drapeau, appel réel minuscule.
# --------------------------------------------------------------------------------------------------


def test_run_identity_cell_refuses_degenerate_args_before_any_world(monkeypatch):
    def _boom(*a, **k):
        raise AssertionError("un monde a été construit avant la garde")
    monkeypatch.setattr(R, "_bassin_cohort", _boom)
    for kw in ({"fix": "maybe"}, {"fix": "on", "num_agents": 0}, {"fix": "off", "ticks_learn": 0},
               {"fix": "off", "ticks_test": -1}):
        with pytest.raises(ValueError):
            R.run_identity_cell(2026, **kw)


def test_run_identity_cell_passes_the_flag_and_the_audit_to_phase_1(monkeypatch):
    seen = []
    monkeypatch.setattr(R, "_bassin_cohort", lambda seed, n: ["cohorte", seed, n])
    monkeypatch.setattr(R, "phase1_learn_immortal",
                        lambda agents, seed, ticks, **kw: seen.append((agents, seed, ticks, kw)) or {"td_updates": 1})
    monkeypatch.setattr(R, "phase2_survive_mortal", lambda agents, seed, ticks: {"survival_median": 4.0, "ticks": ticks})
    on = R.run_identity_cell(2026, "on", num_agents=3, ticks_learn=5, ticks_test=2)
    off = R.run_identity_cell(2026, "off", num_agents=3, ticks_learn=5, ticks_test=2)
    assert seen[0] == (["cohorte", 2026, 3], 2026, 5, {"slot_order_fix": True, "identity_audit": True})
    assert seen[1][3] == {"slot_order_fix": False, "identity_audit": True}
    assert on["arm"] == "on" and off["arm"] == "off" and on["survival"]["survival_median"] == 4.0
    assert on["lr"] is None and on["num_agents"] == 3 and on["ticks_learn"] == 5 and on["ticks_test"] == 2


def test_run_identity_cell_real_world_minimal_publishes_the_invariant_audit():
    pytest.importorskip("torch")
    on = R.run_identity_cell(2026, "on", num_agents=2, ticks_learn=3, ticks_test=2)
    off = R.run_identity_cell(2026, "off", num_agents=2, ticks_learn=3, ticks_test=2)
    assert on["learning"]["slot_identity"]["slot_order_fix"] is True
    assert on["learning"]["slot_identity"]["slot_ticks_misaligned"] == 0
    assert off["learning"]["slot_identity"]["slot_order_fix"] is False
    assert off["learning"]["slot_identity"]["ticks_known"] == 3
    assert np.isfinite(on["survival"]["survival_median"]) and len(on["survival"]["ages"]) == 2
