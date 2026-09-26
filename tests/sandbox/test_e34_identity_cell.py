"""E34 (P2.132) — `E34-IDENTITY-CELL` v2 : calibration du runner de la sonde (tools/evo_runs/e34_identity_cell.py).

À réponse CONNUE : (1) le VERDICT (pur, lignes synthétiques, branches dans l'ordre scellé) : bande = {S_off, 11 shams}
du MÊME seed, bords DANS la bande sur la grille 0,5, S_off n'est plus un bord imposé ; audit incomplet -> INCOMPLET
(jamais SANS_OBJET, revue v1 P7.a) ; lieux mêlés -> LIEU_MIXTE ; témoin d'une autre exécution -> LÈVE (P5.b) ; dose =
COMMUTATIONS (P8.a) ; harnais qui ment -> LÈVE ; (2) S_a et la dispersion ENTRE seeds (descriptive) LUES dans le
JSON suivi de P4.16 ; (3) le témoin du code contre la cellule publiée de P4.4 — identique à elle-même, rompu par UN
ulp de Σ|ΔW| ou UN âge ; (4) `run_identity_cell` : garde en tête, traitement du bras TRANSMIS à la phase 1
(injection, sans torch), et un appel réel minuscule (monde, torch, 2 agents : sauté par conftest quand un run tient
`kuzu`).
"""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.evo_runs import e34_identity_cell as R  # noqa: E402

TL = 2000
LIEU = {"platform": "Windows-11", "python": "3.13.12", "torch": "2.6.0+cu124", "torch_threads": 16,
        "AGAGI_CPU_LIMIT": None, "AGAGI_IMAGE": None}
AGES_OFF = [5, 6, 6, 7, 7, 7, 7, 8, 8, 9, 9, 11]
DW_OFF = 18242.03954219818


def _row(s, arm="off", switches=40, mis=24000, known=TL, unknown=0, t1=57, reorder_tick=None, sham_tick=None,
         draws=0, fix=False, lieu=LIEU, ages=None, dw=12000.0):
    ident = {"ticks_known": known, "ticks_unknown": unknown, "slot_switches": switches, "slot_ticks_misaligned": mis,
             "first_switch_tick": t1 if switches else None, "first_reorder_tick": reorder_tick,
             "positions_reordered": 30 if fix else 0, "sham_tick": sham_tick, "sham_draws": draws, "slot_order_fix": fix}
    return {"arm": arm, "num_agents": 12, "lieu": dict(lieu),
            "learning": {"td_updates": TL - 1, "resurrections": 12, "dW_abs_sum": dw, "slot_identity": ident},
            "survival": {"survival_median": s, "ages": list(ages or [int(s)] * 12)}}


def _off(s=7.0, **kw):
    return _row(s, ages=AGES_OFF, dw=DW_OFF, **kw)


def _on(s, **kw):
    kw.setdefault("reorder_tick", 57)
    return _row(s, arm="on", switches=0, mis=0, fix=True, **kw)


def _shams(values=(7.0, 7.5, 8.0, 6.5, 7.0, 7.5, 8.0, 7.0, 7.5, 7.0, 8.5), t1=57):
    return [_row(v, arm=f"sham_{k:02d}", sham_tick=t1, draws=k) for k, v in enumerate(values, 1)]


def _witness(off=None, identical=True):
    off = off or _off()
    return {"identical": identical, "reason": "bit-identique" if identical else "Σ|ΔW| différent",
            "measured_ages": list(off["survival"]["ages"]), "measured_dW_abs_sum": off["learning"]["dW_abs_sum"]}


def _v(s_on, off=None, shams=None, witness=None, **kw):
    off = off or _off()
    return R.identity_cell_verdict(off, _on(s_on, **kw), _shams() if shams is None else shams,
                                   _witness(off) if witness is None else witness, 31.5, TL)


# --------------------------------------------------------------------------------------------------
# 1. Le verdict — branches dans l'ordre scellé.
# --------------------------------------------------------------------------------------------------


def test_arm_table_off_on_and_eleven_shams():
    assert R.ARMS[:2] == ("off", "on") and len(R.SHAMS) == 11 and R.SHAMS[0] == "sham_01"
    assert R.arm_config("off") == {"slot_order_fix": False, "sham_draws": 0}
    assert R.arm_config("on") == {"slot_order_fix": True, "sham_draws": 0}
    assert R.arm_config("sham_07") == {"slot_order_fix": False, "sham_draws": 7}
    with pytest.raises(ValueError):
        R.arm_config("sham_12")


def test_verdict_INCOMPLET_when_a_cell_a_sham_or_the_witness_is_missing():
    off = _off()
    assert R.identity_cell_verdict(None, _on(8.0), _shams(), _witness(off), 31.5, TL)["verdict"] == "INCOMPLET"
    sh = _shams()
    sh[4] = None
    v = R.identity_cell_verdict(off, _on(8.0), sh, _witness(off), 31.5, TL)
    assert v["verdict"] == "INCOMPLET" and v["manquants"] == ["sham_05"]
    assert R.identity_cell_verdict(off, _on(8.0), _shams()[:10], _witness(off), 31.5, TL)["verdict"] == "INCOMPLET"
    assert R.identity_cell_verdict(off, _on(8.0), _shams(), None, 31.5, TL)["verdict"] == "INCOMPLET"


def test_verdict_blind_audit_is_INCOMPLET_never_SANS_OBJET():
    """Revue v1 P7.a : un audit qui n'a apparié aucun tick laisse les compteurs à 0 PAR ABSENCE -- INCOMPLET."""
    off = _off(switches=0, known=0)
    v = R.identity_cell_verdict(off, _on(8.0), _shams(), _witness(off), 31.5, TL)
    assert v["verdict"] == "INCOMPLET" and v["audit_incomplet"] == ["off"]
    v = R.identity_cell_verdict(_off(), _on(8.0, unknown=1), _shams(), _witness(), 31.5, TL)
    assert v["verdict"] == "INCOMPLET" and v["audit_incomplet"] == ["on"]


def test_verdict_refuses_non_finite_inputs_and_a_missing_audit():
    with pytest.raises(ValueError):
        _v(float("nan"))
    bad = _off()
    del bad["learning"]["slot_identity"]
    with pytest.raises(ValueError):
        R.identity_cell_verdict(bad, _on(8.0), _shams(), _witness(), 31.5, TL)
    with pytest.raises(ValueError):
        R.identity_cell_verdict(_off(), _on(8.0), _shams(), _witness(), float("nan"), TL)


def test_verdict_LIEU_MIXTE_when_the_cells_come_from_two_places():
    sh = _shams()
    sh[2] = _row(8.0, arm="sham_03", sham_tick=57, draws=3, lieu=dict(LIEU, torch_threads=2))
    assert R.identity_cell_verdict(_off(), _on(8.0), sh, _witness(), 31.5, TL)["verdict"] == "LIEU_MIXTE"


def test_verdict_refuses_a_witness_from_another_run():
    """Revue v1 P5.b : le témoin doit certifier la ligne éteinte LUE (mêmes âges, même Σ|ΔW|)."""
    w = _witness()
    w["measured_dW_abs_sum"] = 17000.0
    with pytest.raises(ValueError):
        _v(8.0, witness=w)


def test_verdict_TEMOIN_ROMPU_before_any_reading():
    off = _off()
    assert _v(20.0, witness=_witness(off, identical=False))["verdict"] == "TEMOIN_ROMPU"


def test_verdict_SANS_OBJET_only_when_no_slot_switched_body():
    off = _off(switches=0)
    v = R.identity_cell_verdict(off, _on(20.0), _shams(), _witness(off), 31.5, TL)
    assert v["verdict"] == "SANS_OBJET"


def test_verdict_refuses_a_harness_that_lies():
    with pytest.raises(ValueError):                                     # allumé qui commute
        R.identity_cell_verdict(_off(), _row(8.0, arm="on", switches=3, mis=0, fix=True, reorder_tick=57),
                                _shams(), _witness(), 31.5, TL)
    with pytest.raises(ValueError):                                     # allumé qui a divergé à un autre tick
        _v(8.0, reorder_tick=58)
    with pytest.raises(ValueError):                                     # sham tiré ailleurs qu'au tick de divergence
        R.identity_cell_verdict(_off(), _on(8.0), _shams(t1=58), _witness(), 31.5, TL)
    sh = _shams()
    sh[0] = _row(7.0, arm="sham_01", sham_tick=57, draws=2)               # sham_01 qui a tiré 2 valeurs
    with pytest.raises(ValueError):
        R.identity_cell_verdict(_off(), _on(8.0), sh, _witness(), 31.5, TL)


def test_verdict_band_is_the_same_seed_trajectories_and_its_edges_belong_to_it():
    """Bande = {S_off} ∪ 11 shams = [6,5 ; 8,5] ici : S_off (7,0) n'en est PLUS le bord. Bords DANS la bande."""
    assert _v(8.5)["verdict"] == "NON_MATERIEL" and _v(6.5)["verdict"] == "NON_MATERIEL"
    assert _v(9.0)["verdict"] == "MATERIEL_HAUSSE"
    assert _v(6.0)["verdict"] == "MATERIEL_BAISSE"
    v = _v(8.0)
    assert (v["band_min"], v["band_max"]) == (6.5, 8.5) and len(v["band_values"]) == 12 and v["band_values"][0] == 7.0


def test_verdict_FORT_is_descriptive_and_never_a_second_road_to_MATERIEL():
    assert _v(12.0)["fort"] is True and _v(12.0)["verdict"] == "MATERIEL_HAUSSE"          # |dS| = 5,0 : égalité
    assert _v(11.5)["fort"] is False and _v(11.5)["verdict"] == "MATERIEL_HAUSSE"
    off = _off(s=2.0)
    shams = _shams(values=(2.0, 12.0) + (7.0,) * 9)                    # bande [2,0 ; 12,0]
    v = R.identity_cell_verdict(off, _on(8.0), shams, _witness(off), 31.5, TL)
    assert v["verdict"] == "NON_MATERIEL" and v["fort"] is True


def test_verdict_publishes_the_dose_in_switches_the_band_and_the_h0_false_alarm():
    v = _v(13.0)
    assert v["switches_off"] == 40 and v["first_switch_tick_off"] == 57
    assert v["fraction_transitions_td_a_cheval"] == pytest.approx(40 / (12 * (TL - 1)))
    assert v["S_off"] == 7.0 and v["S_on"] == 13.0 and v["dS"] == 6.0 and v["S_a"] == 31.5
    assert v["erosion_off"] == 24.5 and v["part_erosion_levee"] == pytest.approx(6.0 / 24.5)
    assert v["fausse_alarme_h0"] == pytest.approx(2.0 / 13.0) and v["thresholds"]["n_band"] == 12
    assert v["positions_reordered_on"] == 30 and v["lieu"] == LIEU and v["verdict"] == "MATERIEL_HAUSSE"


def test_verdict_NON_MATERIEL_is_bounded_to_this_cell_and_its_dose():
    v = _v(7.5)
    assert v["verdict"] == "NON_MATERIEL" and "CETTE cellule" in v["why"] and "40 commutations" in v["why"]


def test_verdict_part_erosion_is_None_not_a_number_without_erosion():
    off = _off(s=40.0)
    v = R.identity_cell_verdict(off, _on(40.0), _shams(values=(40.0,) * 11), _witness(off), 31.5, TL)
    assert v["part_erosion_levee"] is None


# --------------------------------------------------------------------------------------------------
# 2. S_a et la dispersion ENTRE seeds : LUES dans le JSON suivi de P4.16 (descriptive, ne décide rien).
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
    row["learning"]["slot_identity"] = {"slot_switches": 1, "ticks_known": 2000}
    return row


def test_witness_is_identical_to_the_published_cell_itself():
    w = R.witness_check(_published_row(), 2026)
    assert w["identical"] is True and w["reason"] == "bit-identique" and w["same_dW_abs_sum"] is True
    assert w["p44_dW_abs_sum"] == 18242.03954219818 and w["measured_ages"] == AGES_OFF


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
# 4. `run_identity_cell` : garde en tête, traitement transmis, appel réel minuscule.
# --------------------------------------------------------------------------------------------------


def test_run_identity_cell_refuses_degenerate_args_before_any_world(monkeypatch):
    def _boom(*a, **k):
        raise AssertionError("un monde a été construit avant la garde")
    monkeypatch.setattr(R, "_bassin_cohort", _boom)
    for kw in ({"arm": "maybe"}, {"arm": "on", "num_agents": 0}, {"arm": "off", "ticks_learn": 0},
               {"arm": "sham_03", "ticks_test": -1}):
        with pytest.raises(ValueError):
            R.run_identity_cell(2026, **kw)


def test_run_identity_cell_passes_the_arm_treatment_to_phase_1(monkeypatch):
    seen = []
    monkeypatch.setattr(R, "_bassin_cohort", lambda seed, n: ["cohorte", seed, n])
    monkeypatch.setattr(R, "phase1_learn_immortal",
                        lambda agents, seed, ticks, **kw: seen.append((agents, seed, ticks, kw)) or {"td_updates": 1})
    monkeypatch.setattr(R, "phase2_survive_mortal", lambda agents, seed, ticks: {"survival_median": 4.0, "ticks": ticks})
    on = R.run_identity_cell(2026, "on", num_agents=3, ticks_learn=5, ticks_test=2)
    R.run_identity_cell(2026, "off", num_agents=3, ticks_learn=5, ticks_test=2)
    sh = R.run_identity_cell(2026, "sham_04", num_agents=3, ticks_learn=5, ticks_test=2)
    assert seen[0] == (["cohorte", 2026, 3], 2026, 5, {"slot_order_fix": True, "identity_audit": True, "sham_draws": 0})
    assert seen[1][3] == {"slot_order_fix": False, "identity_audit": True, "sham_draws": 0}
    assert seen[2][3] == {"slot_order_fix": False, "identity_audit": True, "sham_draws": 4}
    assert on["treatment"] == {"slot_order_fix": True, "sham_draws": 0} and sh["arm"] == "sham_04"
    assert on["lr"] is None and on["num_agents"] == 3 and on["survival"]["survival_median"] == 4.0
    assert on["cpu_s"] >= 0.0 and on["elapsed_s"] >= 0.0


def test_lieu_publishes_the_torch_threads_or_None():
    lv = R.lieu()
    assert set(lv) == {"platform", "python", "torch", "torch_threads", "AGAGI_CPU_LIMIT", "AGAGI_IMAGE"}
    assert lv["torch_threads"] is None or lv["torch_threads"] >= 1


def test_run_identity_cell_real_world_minimal_publishes_the_invariant_and_switch_audit():
    pytest.importorskip("torch")
    on = R.run_identity_cell(2026, "on", num_agents=2, ticks_learn=3, ticks_test=2)
    off = R.run_identity_cell(2026, "off", num_agents=2, ticks_learn=3, ticks_test=2)
    assert on["learning"]["slot_identity"]["slot_order_fix"] is True
    assert on["learning"]["slot_identity"]["slot_switches"] == 0
    assert off["learning"]["slot_identity"]["slot_order_fix"] is False
    assert off["learning"]["slot_identity"]["ticks_known"] == 3 and "_pairing" not in off["learning"]["slot_identity"]
    assert np.isfinite(on["survival"]["survival_median"]) and len(on["survival"]["ages"]) == 2
