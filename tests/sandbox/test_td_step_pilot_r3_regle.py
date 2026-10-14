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
    assert digests == {DIGEST_IMAGE} and len(tau["cellules"]) == 24
    assert REGLE["cellule"]["image_digest"] == DIGEST_IMAGE
    cal = REGLE["seuils"]["calibration"]
    assert cal["mu_pas"] == round(tau["tau"]["moyenne_pas"], 2) and cal["tau_pas"] == round(tau["tau"]["tau_pas"], 2)


def test_the_prose_follows_the_margin_and_the_code_finds_every_key_it_reads():
    s = REGLE["seuils"]
    assert f"{len(REGLE['cellule']['seeds']) * s['marge_pas']} pas" in REGLE["dv_primaire"]
    for k in ("mu_pas", "tau_pas", "sigmas_e_pas", "f", "n_rep", "graine"):
        assert k in s["calibration"]
    for k in ("budget_etape_s", "safety", "unite_reference_s", "fraction_cout_apparie_max", "seeds_effet",
              "seeds_chemin", "seeds_appariement", "appariement_bornes", "garde_dose_sham", "f_transporte_max",
              "f_pas_plus_gros_min", "bootstrap_B", "bootstrap_graine"):
        assert k in s
    assert len(REGLE["questions_ouvertes"]) == 3 and "TROIS USAGES" in REGLE["questions_ouvertes"][0]


def test_the_draft_is_written_outside_the_preregistrations_and_round_trips(tmp_path):
    p = brouillon(str(tmp_path / "TD-STEP-PILOT-R3.v2.json"))
    assert json.load(open(p, encoding="utf-8")) == json.loads(json.dumps(REGLE))
    assert not os.path.exists(os.path.join(_RACINE, "docs", "preregistrations", "TD-STEP-PILOT-R3.json"))
