"""Brouillon v2 de la règle TD-STEP-PILOT-R3 (tools/td_step_pilot_r3_regle.py) confronté au CODE qui la lira et à la
MESURE qu'il cite : la vraie lecture tourne sur ses seuils et rend les branches attendues sur des réponses connues, le
digest exigé est celui des 24 MANIFEST du pilote τ (fichier suivi), les nombres de la prose suivent la marge, et le
brouillon s'écrit sans toucher aux pré-inscriptions. Aucune simulation."""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import tools.td_step_pilot_r3 as r3  # noqa: E402
from tools.td_step_pilot_r3_regle import DIGEST_IMAGE, REGLE, brouillon  # noqa: E402

_RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@pytest.mark.parametrize("f,branche", [(0.0, "TRANSPORTE"), (1.0, "PAS_PLUS_GROS"), (0.5, "SHAM_PARTIEL")])
def test_the_draft_drives_the_REAL_reading_on_known_answers(f, branche):
    c = REGLE["cellule"]
    mu = REGLE["seuils"]["calibration"]["mu_pas"]
    db = r3.base_injection_v2(REGLE, mu, 0.0, 0.0, f, np.random.default_rng(0))
    assert r3.classify_pas(db, REGLE, c["pas_primaire"])["branche"] == branche


def test_the_required_image_is_the_one_tau_was_measured_on():
    tau = json.load(open(os.path.join(_RACINE, "results", "td_step_pilot_r3_tau.json"), encoding="utf-8"))
    digests = {v["manifeste"]["image_digest"] for v in tau["cellules"].values()}
    tau_p1 = [k for k in tau["cellules"] if k.split("|")[0] in ("lam0", "lam09") and "|pas=" not in k and "|rep=" not in k]
    assert digests == {DIGEST_IMAGE} and len(tau_p1) == 24
    assert REGLE["cellule"]["image_digest"] == DIGEST_IMAGE
    cal = REGLE["seuils"]["calibration"]
    assert cal["mu_pas"] == round(tau["tau"]["moyenne_pas"], 2) and cal["tau_pas"] == round(tau["tau"]["tau_pas"], 2)


def test_the_prose_follows_the_margin_and_the_code_finds_every_key_it_reads():
    s = REGLE["seuils"]
    assert f"{len(REGLE['cellule']['seeds']) * s['marge_effet_pas']} pas" in REGLE["dv_primaire"]
    assert (s["marge_effet_pas"], s["marge_chemin_pas"], s["marge_barre_pas"]) == (20, 29, 29)    # direction B
    for k in ("mu_pas", "tau_pas", "sigmas_e_pas", "f", "n_rep", "graine"):
        assert k in s["calibration"]
    for k in ("budget_etape_s", "safety", "unite_reference_s", "fraction_cout_apparie_max", "seeds_effet",
              "seeds_chemin", "seeds_appariement", "appariement_bornes", "garde_dose_sham", "f_transporte_max",
              "f_pas_plus_gros_min", "bootstrap_B", "bootstrap_graine"):
        assert k in s
    q = REGLE["questions_ouvertes"]               # 3 au v2, 9 après la revue, 4 après les décisions de robla
    assert [x[:3] for x in q] == ["(1)", "(4)", "(7)", "(8)"] and "TROIS USAGES" in q[0]
    assert [x[:3] for x in REGLE["decisions_robla_2026_10_14"]][:5] == ["(2)", "(3)", "(5)", "(6)", "(9)"]


def test_the_draft_is_written_outside_the_preregistrations_and_round_trips(tmp_path):
    p = brouillon(str(tmp_path / "TD-STEP-PILOT-R3.v2.json"))
    assert json.load(open(p, encoding="utf-8")) == json.loads(json.dumps(REGLE))
    assert not os.path.exists(os.path.join(_RACINE, "docs", "preregistrations", "TD-STEP-PILOT-R3.json"))


import tools.td_step_pilot_r3_regle as regle_mod  # noqa: E402


def test_calibration_before_the_seal_carries_the_fingerprint_of_the_calibrated_rule(tmp_path):
    out = regle_mod.calibrer(dest=str(tmp_path / "cal.json"), n_rep=4)
    relu = json.load(open(tmp_path / "cal.json", encoding="utf-8"))
    assert relu["_provenance"]["regle_empreinte"] == regle_mod.empreinte() and out["n_rep"] == 4
    assert set(relu["par_sigma_e"]) == {str(x) for x in REGLE["seuils"]["calibration"]["sigmas_e_pas"]}


def test_the_seal_REFUSES_open_questions_missing_or_foreign_calibration_and_an_unmet_requirement(monkeypatch, tmp_path):
    scelles = []
    with pytest.raises(ValueError, match="question"):
        regle_mod.sceller("docs/reviews/x.md", calibration=str(tmp_path / "absente.json"),
                          _preregister=lambda *a, **k: scelles.append(a))
    monkeypatch.setitem(regle_mod.REGLE, "questions_ouvertes", [])
    with pytest.raises(ValueError, match="absente"):
        regle_mod.sceller("docs/reviews/x.md", calibration=str(tmp_path / "absente.json"),
                          _preregister=lambda *a, **k: scelles.append(a))
    tau = str(REGLE["seuils"]["calibration"]["tau_pas"])

    def cal(empreinte, t, g):
        p = tmp_path / f"cal_{t}_{g}.json"
        p.write_text(json.dumps({"_provenance": {"regle_empreinte": empreinte},
                                 "par_sigma_e": {tau: {"0.0": {"TRANSPORTE": t}, "1.0": {"PAS_PLUS_GROS": g}}},
                                 "chemin_rate": {"CONTROLE_CHEMIN_ECHOUE": 1.0 if g != 0.81 else 0.9}}),
                     encoding="utf-8")
        return str(p)
    with pytest.raises(ValueError, match="AUTRE"):
        regle_mod.sceller("docs/reviews/x.md", calibration=cal("0" * 64, 0.9, 0.9),
                          _preregister=lambda *a, **k: scelles.append(a))
    with pytest.raises(ValueError, match="NON tenue"):
        regle_mod.sceller("docs/reviews/x.md", calibration=cal(regle_mod.empreinte(), 0.79, 0.9),
                          _preregister=lambda *a, **k: scelles.append(a))
    with pytest.raises(ValueError, match="NON tenue"):                     # décision 9 : chemin raté non visité
        regle_mod.sceller("docs/reviews/x.md", calibration=cal(regle_mod.empreinte(), 0.9, 0.81),
                          _preregister=lambda *a, **k: scelles.append(a))
    assert scelles == []
    regle_mod.sceller("docs/reviews/x.md", calibration=cal(regle_mod.empreinte(), 0.8, 0.95),
                      _preregister=lambda *a, **k: scelles.append((a, k)))
    assert len(scelles) == 1 and scelles[0][0][0] == "TD-STEP-PILOT-R3" and scelles[0][1]["reviewed_by"] == \
        "docs/reviews/x.md"
