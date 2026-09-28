"""E34 (P2.132) — `E34-IDENTITY-CELL` v4 : calibration du runner de la sonde (tools/evo_runs/e34_identity_cell.py).

À réponse CONNUE : (1) le VERDICT (pur, lignes synthétiques, branches dans l'ordre scellé) : bande = les 12 shams de
RÉÉTIQUETAGE (revues v2 P5.a, v3 P1.a), bords DANS la bande sur la grille 0,5 ; témoin rompu lu AVANT l'absence des autres cellules
(P10.d) ; audit aveugle -> INCOMPLET, jamais SANS_OBJET (v1 P7.a) ; commits mêlés -> PROVENANCE_MIXTE (P10.e) ; lieux
mêlés -> LIEU_MIXTE ; bande inerte -> BANDE_INERTE (P1.b/P5.b) ; contrôle positif non vu -> NON_TRANCHE (P5.c) ;
harnais qui ment -> LÈVE ; fausse alarme avec ex-aequo calculée (P5.d) ; doses par bras (P7.d) ; (2) S_a et la
dispersion ENTRE seeds (descriptive) LUES dans le JSON suivi de P4.16 ; (3) le témoin du code contre la cellule
publiée de P4.4 ; (4) `run_identity_cell` : garde en tête, traitement TRANSMIS, appel réel minuscule (monde, torch).
"""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.evo_runs import e34_identity_cell as R  # noqa: E402
# Épinglé à l'IMPORT (P2.142) : `tools` est un paquet-espace-de-noms ; mesuré le 2026-09-28, une session qui lance
# test_instrument_calibration.py avant ce fichier voit la racine de l'arbre PRINCIPAL en tête de sys.path, et un import
# PARESSEUX de tools.slot_identity y prend alors la version de l'arbre principal, pas celle de ce worktree.
import tools.slot_identity  # noqa: E402,F401

TL = 2000
T1 = 57
LIEU = {"platform": "Windows-11", "python": "3.13.12", "torch": "2.6.0+cu124", "torch_threads": 16,
        "AGAGI_CPU_LIMIT": None, "AGAGI_IMAGE": None}
PROV = {"git_sha": "abc123", "dirty": False}
AGES_OFF = [5, 6, 6, 7, 7, 7, 7, 8, 8, 9, 9, 11]
DW_OFF = 18242.03954219818
RELAB_S = (7.0, 7.5, 8.0, 6.5, 7.0, 7.5, 8.0, 7.0, 7.5, 7.0, 8.5, 7.5)         # bande [6,5 ; 8,5], S_off 7,0 dedans


def _row(s, arm, switches=0, mis=0, known=TL, unknown=0, order_changes=12, first_order=T1, reindex=False,
         reindex_tick=None, relab=0, relab_tick=None, cut_tick=None, td=TL - 1, dw=12000.0, ages=None, lieu=LIEU, prov=PROV,
         reordered=0):
    ident = {"ticks_known": known, "ticks_unknown": unknown, "slot_switches": switches, "slot_ticks_misaligned": mis,
             "order_changes": order_changes, "first_order_change_tick": first_order, "ticks_body_reordered": reordered,
             "positions_moved": 40, "reindex_events": 12 if reindex else 0, "rows_reindexed": 30 if reindex else 0,
             "first_reindex_tick": reindex_tick, "sham_relabel": relab, "relabel_events": 12 if relab else 0,
             "rows_relabeled": 25 if relab else 0, "first_relabel_tick": relab_tick, "credit_cut_tick": cut_tick,
             "relabel_draws": 30 if relab else 0,
             "slot_order_fix": False, "slot_reindex": reindex}
    return {"arm": arm, "num_agents": 12, "lieu": dict(lieu), "provenance": dict(prov),
            "learning": {"td_updates": td, "episode_updates": 250, "resurrections": 12, "dW_abs_sum": dw,
                         "slot_identity": ident},
            "consensus_phase1": {"ticks_avec_reecriture": 5, "lignes_reecrites": 9}, "plafond_famine_ticks": 7.2,
            "consensus_phase2": {"ticks_avec_reecriture": 2, "lignes_reecrites": 3},
            "reconstructions_phase2": {"constructions": 6, "B": [12, 11, 9, 7, 4, 1]},
            "survival": {"survival_median": s, "ages": list(ages or [int(s)] * 12)}}


def _rows(s_on=8.0, s_pos=20.0, relab_s=RELAB_S, **over):
    rows = {"off": _row(7.0, "off", switches=40, mis=24000, ages=AGES_OFF, dw=DW_OFF),
            "on": _row(s_on, "on", reindex=True, reindex_tick=T1),
            "pos": _row(s_pos, "pos", switches=40, mis=24000, cut_tick=T1, td=T1 + 1)}
    for k, v in enumerate(relab_s, 1):
        rows[f"relab_{k:02d}"] = _row(v, f"relab_{k:02d}", switches=38, mis=20000, relab=k, relab_tick=T1, dw=11000.0 + k)
    rows.update(over)
    return rows


def _witness(off, identical=True):
    return {"identical": identical, "reason": "bit-identique" if identical else "Σ|ΔW| différent",
            "measured_ages": list(off["survival"]["ages"]), "measured_dW_abs_sum": off["learning"]["dW_abs_sum"]}


def _v(rows=None, witness=None, **kw):
    rows = rows or _rows(**kw)
    return R.identity_cell_verdict(rows, _witness(rows["off"]) if witness is None else witness, 31.5, TL)


# --------------------------------------------------------------------------------------------------
# 1. Le verdict — branches dans l'ordre scellé.
# --------------------------------------------------------------------------------------------------


def test_arm_table_off_on_pos_and_twelve_relabels():
    assert R.ARMS[:3] == ("off", "on", "pos") and len(R.RELABS) == 12 and len(R.ARMS) == 15
    base = {"slot_reindex": False, "sham_relabel": 0, "cut_credit_at_t1": False}
    assert R.arm_config("off") == base
    assert R.arm_config("on") == dict(base, slot_reindex=True)
    assert R.arm_config("pos") == dict(base, cut_credit_at_t1=True)
    assert R.arm_config("relab_07") == dict(base, sham_relabel=7)
    with pytest.raises(ValueError):
        R.arm_config("relab_13")


def test_verdict_INCOMPLET_when_the_off_cell_or_its_witness_is_missing():
    rows = _rows()
    rows["off"] = None
    assert R.identity_cell_verdict(rows, None, 31.5, TL)["verdict"] == "INCOMPLET"
    rows = _rows()
    assert R.identity_cell_verdict(rows, None, 31.5, TL)["verdict"] == "INCOMPLET"


def test_verdict_TEMOIN_ROMPU_is_read_before_the_other_missing_cells():
    """Revue v2, P10.d : un témoin rompu arrête le run après la phase A -- le verdict doit le DIRE, pas « INCOMPLET »."""
    rows = {a: None for a in R.ARMS}
    rows["off"] = _rows()["off"]
    v = R.identity_cell_verdict(rows, _witness(rows["off"], identical=False), 31.5, TL)
    assert v["verdict"] == "TEMOIN_ROMPU"


def test_verdict_refuses_a_witness_from_another_run():
    rows = _rows()
    w = _witness(rows["off"])
    w["measured_dW_abs_sum"] = 17000.0
    with pytest.raises(ValueError):
        R.identity_cell_verdict(rows, w, 31.5, TL)


def test_verdict_INCOMPLET_when_a_cell_is_missing_or_an_audit_is_blind():
    rows = _rows()
    rows["relab_05"] = None
    v = _v(rows)
    assert v["verdict"] == "INCOMPLET" and v["manquants"] == ["relab_05"]
    v = _v(_rows(off=_row(7.0, "off", switches=0, known=0, ages=AGES_OFF, dw=DW_OFF)))
    assert v["verdict"] == "INCOMPLET" and v["audit_incomplet"] == ["off"]


def test_verdict_refuses_non_finite_inputs():
    with pytest.raises(ValueError):
        _v(s_on=float("nan"))
    with pytest.raises(ValueError):
        R.identity_cell_verdict(_rows(), _witness(_rows()["off"]), float("nan"), TL)


def test_verdict_PROVENANCE_MIXTE_on_two_commits_or_a_dirty_tree():
    """Revue v2, P10.e : une cellule d'un autre commit (ou d'un arbre sale) comblerait un trou sans trace."""
    assert _v(_rows(relab_03=_row(8.0, "relab_03", switches=38, relab=3, relab_tick=T1,
                                  prov={"git_sha": "zzz", "dirty": False})))["verdict"] == "PROVENANCE_MIXTE"
    assert _v(_rows(pos=_row(20.0, "pos", switches=40, cut_tick=T1, td=T1 + 1,
                             prov={"git_sha": "abc123", "dirty": True})))["verdict"] == "PROVENANCE_MIXTE"


def test_verdict_LIEU_MIXTE_when_the_cells_come_from_two_places():
    assert _v(_rows(relab_03=_row(8.0, "relab_03", switches=38, relab=3, relab_tick=T1,
                                  lieu=dict(LIEU, torch_threads=2))))["verdict"] == "LIEU_MIXTE"


def test_verdict_SANS_OBJET_only_when_no_brain_switched_body():
    v = _v(_rows(off=_row(7.0, "off", switches=0, ages=AGES_OFF, dw=DW_OFF)))
    assert v["verdict"] == "SANS_OBJET"


def test_verdict_INCOMPLET_names_a_persisted_cost_refusal():
    """Revue v4, P10.d : un refus de la garde de coût avant la phase B est PERSISTÉ et le verdict le nomme."""
    rows = {a: None for a in R.ARMS}
    rows["off"] = _rows()["off"]
    v = R.identity_cell_verdict(rows, _witness(rows["off"]), 31.5, TL, refus_cout={"refus": "trop cher", "unit_s": 900})
    assert v["verdict"] == "INCOMPLET" and "garde de coût" in v["why"] and v["refus_cout"]["unit_s"] == 900


def test_verdict_refuses_a_harness_that_lies():
    with pytest.raises(ValueError):                                     # des CORPS réordonnés, MESURÉ
        _v(_rows(relab_02=_row(8.0, "relab_02", switches=38, relab=2, relab_tick=T1, reordered=3)))
    with pytest.raises(ValueError):                                     # réindexation qui commute
        _v(_rows(on=_row(8.0, "on", switches=3, reindex=True, reindex_tick=T1)))
    with pytest.raises(ValueError):                                     # PREMIÈRE réindexation hors de t1
        _v(_rows(on=_row(8.0, "on", reindex=True, reindex_tick=T1 + 1)))
    with pytest.raises(ValueError):                                     # réétiquetage hors de t1
        _v(_rows(relab_02=_row(8.0, "relab_02", switches=38, relab=2, relab_tick=T1 + 3)))
    with pytest.raises(ValueError):                                     # réétiquetage au mauvais RNG privé
        _v(_rows(relab_02=_row(8.0, "relab_02", switches=38, relab=9, relab_tick=T1)))
    with pytest.raises(ValueError):                                     # contrôle positif sans effet sur la dose
        _v(_rows(pos=_row(20.0, "pos", switches=40, cut_tick=T1, td=TL - 1)))
    with pytest.raises(ValueError):                                     # contrôle positif coupé hors de t1
        _v(_rows(pos=_row(20.0, "pos", switches=40, cut_tick=T1 + 2, td=T1 + 1)))


def test_verdict_BANDE_INERTE_when_the_thirteen_members_did_not_diverge():
    rows = _rows()
    for a in R.RELABS:
        rows[a]["learning"]["dW_abs_sum"] = DW_OFF
    v = _v(rows)
    assert v["verdict"] == "BANDE_INERTE" and v["band_dW_distincts"] == 1


def test_verdict_band_is_S_off_plus_the_relabels_and_its_edges_belong_to_it():
    """Revue v4, P4.a : S_off n'est plus un second test contre la bande, il EN FAIT PARTIE -- treize valeurs ; un S_off
    loin des réétiquetages élargit la bande au lieu de rendre un run illisible. Bords DANS la bande."""
    assert _v(s_on=8.5)["verdict"] == "NON_MATERIEL" and _v(s_on=6.5)["verdict"] == "NON_MATERIEL"
    assert _v(s_on=9.0)["verdict"] == "MATERIEL_HAUSSE" and _v(s_on=6.0)["verdict"] == "MATERIEL_BAISSE"
    v = _v()
    assert (v["band_min"], v["band_max"]) == (6.5, 8.5) and len(v["band_values"]) == 13 and v["band_values"][0] == 7.0
    v = _v(_rows(s_on=8.5, relab_s=(8.0, 8.5, 9.0) * 4))              # S_off 7,0 sous les réétiquetages : bande [7 ; 9]
    assert v["band_min"] == 7.0 and v["verdict"] == "NON_MATERIEL"


def test_verdict_NON_TRANCHE_when_the_positive_control_is_not_seen_above_the_band_and_S_off():
    """Revues v2 P5.c et v3 P6.a : NON_MATERIEL exige S_pos au-dessus de la bande ET de S_off ; sinon NON_TRANCHE."""
    assert _v(s_on=8.0, s_pos=8.5)["verdict"] == "NON_TRANCHE"
    assert _v(s_on=8.0, s_pos=5.0)["verdict"] == "NON_TRANCHE"          # sortie par le BAS : sens inverse, non vu
    assert _v(s_on=8.0, s_pos=9.0)["verdict"] == "NON_MATERIEL"
    assert _v(s_on=9.0, s_pos=8.0)["verdict"] == "MATERIEL_HAUSSE"       # un effet VU se lit, contrôle ou non


def test_verdict_false_alarm_is_computed_with_ties():
    """Revue v2, P5.d : 2/13 est une BORNE ; sur les valeurs observées, les ex-aequo la réduisent."""
    v = _v(s_on=8.0)
    assert v["fausse_alarme_h0_borne"] == pytest.approx(2.0 / 14.0)
    assert v["fausse_alarme_h0_ex_aequo"] == pytest.approx(2.0 / 14.0)   # max 8,5 et min 6,5 uniques
    rows = _rows(relab_s=(7.0,) * 12)
    v = _v(rows)
    assert v["fausse_alarme_h0_ex_aequo"] == pytest.approx(1.0 / 14.0)   # S_on 8,0 seul au max, min à 13 ex-aequo


def test_verdict_publishes_doses_per_arm_the_positive_contrast_the_floor_and_the_starvation_ceiling():
    v = _v(s_on=13.0)
    assert v["verdict"] == "MATERIEL_HAUSSE" and v["switches_off"] == 40 and v["t1"] == T1
    assert v["fraction_transitions_td_a_cheval"] == pytest.approx(40 / (12 * (TL - 1)))
    assert v["fraction_fenetres_episodiques_a_cheval_max"] == pytest.approx(40 / (12 * 250))
    assert set(v["dose"]) == set(R.ARMS) and v["dose"]["pos"]["td_updates"] == T1 + 1
    assert v["dose"]["relab_03"]["slot_switches"] == 38 and v["dose"]["on"]["slot_switches"] == 0
    assert v["dose"]["off"]["consensus_ticks_avec_reecriture"] == 5 and v["dose"]["on"]["rows_reindexed"] == 30
    assert v["dose"]["off"]["consensus_phase2_ticks"] == 2 and v["dose"]["pos"]["reconstructions_phase2"] == 6
    assert len(v["switches_band"]) == 13 and v["switches_band"]["off"] == 40 and v["switches_band"]["relab_01"] == 38
    assert v["relabs_part_erosion"]["relab_11"] == pytest.approx(1.5 / 24.5)
    assert v["S_a"] == 31.5 and v["erosion_off"] == 24.5 and v["part_erosion_levee"] == pytest.approx(6.0 / 24.5)
    assert v["dS_pos"] == 13.0 and len(v["relabs_dS"]) == 12 and v["relabs_dS"]["relab_11"] == 1.5
    assert v["sous_plancher_off"] is True and v["thresholds"]["floor"] == 9.0 and v["plafond_famine_ticks"] == 7.2
    assert v["levier_apres_t1"] == pytest.approx((TL - T1) / TL) and v["git_sha"] == "abc123" and "fort" not in v


def test_verdict_NON_MATERIEL_is_upward_only_and_cites_the_cell_and_both_doses():
    v = _v(s_on=7.5, s_pos=20.0)
    assert v["verdict"] == "NON_MATERIEL" and "CETTE cellule" in v["why"] and "vers le HAUT" in v["why"]
    assert "40 commutations" in v["why"] and "30 lignes réindexées" in v["why"] and "vers le BAS, non éprouvé" in v["why"]


def test_verdict_part_erosion_is_None_without_erosion():
    rows = _rows(relab_s=(40.0,) * 11 + (40.5,))
    rows["off"]["survival"]["survival_median"] = 40.0
    assert _v(rows)["part_erosion_levee"] is None


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
               {"arm": "relab_03", "ticks_test": -1}):
        with pytest.raises(ValueError):
            R.run_identity_cell(2026, **kw)


def test_run_identity_cell_passes_the_arm_treatment_to_phase_1(monkeypatch):
    seen = []
    monkeypatch.setattr(R, "_bassin_cohort", lambda seed, n: ["cohorte", seed, n])
    monkeypatch.setattr(R, "phase1_learn_immortal",
                        lambda agents, seed, ticks, **kw: seen.append((agents, seed, ticks, kw)) or {"td_updates": 1})
    monkeypatch.setattr(R, "phase2_survive_mortal", lambda agents, seed, ticks: {"survival_median": 4.0, "ticks": ticks})
    on = R.run_identity_cell(2026, "on", num_agents=3, ticks_learn=5, ticks_test=2)
    R.run_identity_cell(2026, "pos", num_agents=3, ticks_learn=5, ticks_test=2)
    rl = R.run_identity_cell(2026, "relab_04", num_agents=3, ticks_learn=5, ticks_test=2)
    base = {"identity_audit": True, "slot_reindex": False, "sham_relabel": 0, "cut_credit_at_t1": False}
    assert seen[0] == (["cohorte", 2026, 3], 2026, 5, dict(base, slot_reindex=True))
    assert seen[1][3] == dict(base, cut_credit_at_t1=True)
    assert seen[2][3] == dict(base, sham_relabel=4)
    assert on["treatment"]["slot_reindex"] is True and rl["arm"] == "relab_04"
    assert on["lr"] is None and on["num_agents"] == 3 and on["survival"]["survival_median"] == 4.0
    assert on["cpu_s"] >= 0.0 and on["elapsed_s"] >= 0.0
    assert on["consensus_phase1"] == {"ticks_avec_reecriture": 0, "lignes_reecrites": 0}   # aucun monde : aucun vote
    assert on["consensus_phase2"] == {"ticks_avec_reecriture": 0, "lignes_reecrites": 0}
    assert on["reconstructions_phase2"] == {"constructions": 0, "B": []}
    assert on["plafond_famine_ticks"] is None                           # cohorte factice : drain illisible -> None


def test_starvation_ceiling_is_start_energy_over_metabolic_drain():
    class _A:
        phenotype_energy_drain = 14.888
    assert R.starvation_ceiling(_A(), base_metabolism=0.75) == pytest.approx(80.0 / (0.75 * 14.888))
    _A.phenotype_energy_drain = float("nan")
    assert R.starvation_ceiling(_A(), base_metabolism=0.75) is None


def test_lieu_publishes_the_torch_threads_or_None():
    lv = R.lieu()
    assert set(lv) == {"platform", "python", "torch", "torch_threads", "AGAGI_CPU_LIMIT", "AGAGI_IMAGE"}
    assert lv["torch_threads"] is None or lv["torch_threads"] >= 1


def test_run_identity_cell_real_world_minimal_publishes_the_invariant_and_switch_audit():
    pytest.importorskip("torch")
    on = R.run_identity_cell(2026, "on", num_agents=2, ticks_learn=3, ticks_test=2)
    off = R.run_identity_cell(2026, "off", num_agents=2, ticks_learn=3, ticks_test=2)
    assert on["learning"]["slot_identity"]["slot_reindex"] is True
    assert on["learning"]["slot_identity"]["slot_switches"] == 0
    assert off["learning"]["slot_identity"]["slot_reindex"] is False
    ident = off["learning"]["slot_identity"]
    assert ident["ticks_known"] == 3 and not any(k.startswith("_") for k in ident)
    assert np.isfinite(on["survival"]["survival_median"]) and len(on["survival"]["ages"]) == 2
