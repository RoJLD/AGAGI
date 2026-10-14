"""TD-STEP-PILOT-R3 (P4.19) — la couche qui transforme des mesures en affirmation, confrontée à des réponses CONNUES :
f̂ et son IC, la lecture d'un pas dans l'ordre imposé (injection à dose CONNUE, 0 simulation), la synthèse vers
l'ADR (le pas secondaire ne refuse jamais seul), l'appariement par bloc (refus au lieu d'un ρ fabriqué) ; puis,
sous torch, les ajouts à `_train_eval_td_step` : défauts neutres au bit, instrument de dose (lr 0 -> 0 exact, attrape
le flush), éval exhaustive sans tirage, référence lr 0 sans entraînement = référence entraînée à lr 0.
"""
import copy
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import tools.td_step_pilot_r3 as r3  # noqa: E402

# EXEMPTION DÉCLARÉE de la garde de bail (tests/conftest.py) : ce fichier MENTIONNE `MambaAgent` (des génomes du pilote,
# construits en mémoire) mais ne simule AUCUN monde et n'ouvre jamais KuzuDB. Mesuré le 2026-10-13 sous le bail « kuzu »
# d'E34 : la garde sautait les 49 cas, dont 37 sans torch ni agent ; une cellule courte du pilote tourne avec
# `sys.modules["kuzu"] = None`, sans importer ni `src.graph_rag` ni un monde (seul `src.agents.world_model`, le
# modèle interne de l'agent).
_LEASE_GUARD_EXEMPT = True

N = 576


def _regle(apparie=True):
    return {"question": "test", "cout": "test",
            "cellule": {"K": 6, "n_agents": 16, "episodes_td": 3000, "lambda": 0.9, "trace_reset_per_episode": True,
                        "seeds": list(range(1, 13)), "pas": {"p1": 4.0, "p2": 5.656854249492381},
                        "pas_primaire": "p1", "pas_secondaire": "p2", "bloc_episodes": 500,
                        "bras_apparie": apparie, "lieu": "nexus", "threads": 1},
            "seuils": {"marge_pas": 29, "seeds_effet": 11, "seeds_chemin": 10, "seeds_appariement": 10,
                       "appariement_bornes": [0.8, 1.25], "garde_dose_sham": [0.9, 1.1],
                       "f_transporte_max": 0.25, "f_pas_plus_gros_min": 0.75, "bootstrap_B": 2000,
                       "bootstrap_graine": 419, "fraction_cout_apparie_max": 1 / 3}}


def _db(f, d=40, sigma=0.0, graine=0, apparie=True, pas="p1"):
    """Un pas à réponse connue, par la MÊME fabrique que la calibration (σ = 0 : sans bruit)."""
    regle = _regle(apparie)
    db = r3.base_injection(regle, [d] * 12, sigma, f, np.random.default_rng(graine))
    if pas != "p1":                                   # le même contenu, rangé sous l'autre pas
        db = {(k.replace("|pas=p1|", f"|pas={pas}|") if isinstance(k, str) else k): v for k, v in db.items()}
        db["_dose"] = {k.replace("|pas=p1|", f"|pas={pas}|"): v for k, v in db["_dose"].items()}
    return regle, db


def _set(db, bras, pas, sd, pas_grille):
    db[r3._cle(bras, pas, sd)] = pas_grille / N


# ---------------------------------------------------------------------------------------------------- f̂


def test_f_hat_known_answers_zero_one_and_the_undefined_small_gain():
    fh = r3.f_hat([40] * 12, [0] * 12, 348, 2000, 1)
    assert fh["f"] == 0.0 and fh["ic90"] == [0.0, 0.0]
    fh = r3.f_hat([40] * 12, [40] * 12, 348, 2000, 1)
    assert fh["f"] == 1.0 and fh["ic90"] == [1.0, 1.0]
    fh = r3.f_hat([29] * 12, [0] * 12, 348, 2000, 1)             # Σd = 348 = seuil : pas de fraction (porte 14)
    assert fh["f"] is None and fh["ic90"] is None and "348" in fh["raison"]


def test_f_hat_counts_degenerate_resamples_and_withholds_the_interval_beyond_the_cap():
    d = [400] + [-30] * 11                                        # Σd = 70 > 0, mais la plupart des Σd* sont ≤ 0
    fh = r3.f_hat(d, [0] * 12, 0, 2000, 3)
    assert fh["f"] == 0.0 and fh["ic90"] is None and fh["bootstrap_degeneres"] > 100


def test_f_hat_is_deterministic_under_its_declared_seed_and_refuses_bad_shapes():
    rng = np.random.default_rng(0)
    d, e = rng.integers(20, 60, 12), rng.integers(-10, 30, 12)
    assert r3.f_hat(d, e, 348, 2000, 7) == r3.f_hat(d, e, 348, 2000, 7)
    with pytest.raises(ValueError):
        r3.f_hat([1, 2], [1], 0, 10, 0)


# ---------------------------------------------------------------------------------------------------- lecture


@pytest.mark.parametrize("f,branche", [(0.0, "TRANSPORTE"), (0.3, "SHAM_PARTIEL"), (0.5, "SHAM_PARTIEL"),
                                       (0.6, "SHAM_PARTIEL"), (0.8, "PAS_PLUS_GROS"), (1.0, "PAS_PLUS_GROS"),
                                       (-0.5, "SHAM_NUIT")])
def test_noiseless_injection_at_known_fractions_gives_the_named_branch(f, branche):
    regle, db = _db(f)
    L = r3.classify_pas(db, regle, "p1")
    assert L["branche"] == branche, L
    assert L["f_hat"]["f"] == pytest.approx(f)


@pytest.mark.parametrize("f", [0.0, 1.0])
def test_a_WIDE_interval_is_SHAM_PARTIEL_the_HIGH_bound_decides_TRANSPORTE_and_the_LOW_bound_PAS_PLUS_GROS(f):
    """f̂ exactement 0 (ou 1), mais e alterne ±40 pas d'un seed à l'autre : l'IC90 déborde des deux seuils. La branche
    doit rester SHAM_PARTIEL -- TRANSPORTE se décide sur la borne HAUTE, PAS_PLUS_GROS sur la borne BASSE (une lecture
    sur l'autre borne rendrait un verdict que l'intervalle ne soutient pas : mutant tué par la passe du 2026-10-13)."""
    regle, db = _db(f)
    for i, sd in enumerate(regle["cellule"]["seeds"]):
        base = r3._entier(db, r3._cle("lam0", "p1", sd), N)
        _set(db, "sham09", "p1", sd, base + f * 40 + (40 if i % 2 == 0 else -40))
    L = r3.classify_pas(db, regle, "p1")
    assert L["f_hat"]["f"] == pytest.approx(f)
    lo, hi = L["f_hat"]["ic90"]
    assert lo < 0.75 and hi > 0.25 and L["branche"] == "SHAM_PARTIEL", (lo, hi, L["branche"])


def test_a_missing_cell_or_an_absent_preflight_gives_INCOMPLET_never_a_verdict():
    regle, db = _db(0.0)
    del db[r3._cle("sham09", "p1", 7)]
    assert r3.classify_pas(db, regle, "p1")["branche"] == "INCOMPLET"
    regle, db = _db(0.0)
    del db["_regime"]
    L = r3.classify_pas(db, regle, "p1")
    assert L["branche"] == "INCOMPLET" and "pré-vol" in L["raison"]


def test_the_paired_arm_is_read_only_if_the_preflight_retained_it():
    regle, db = _db(0.0)
    for sd in regle["cellule"]["seeds"]:
        del db[r3._cle("td0_app", "p1", sd)]
    assert r3.classify_pas(db, regle, "p1")["branche"] == "INCOMPLET"
    db["_regime"]["pre_vol"]["apparie_retenu"] = False               # retiré sur son COÛT, déclaré
    L = r3.classify_pas(db, regle, "p1")
    assert L["branche"] == "TRANSPORTE" and "apparie" not in L


def test_exact_equality_at_the_margin_counts_as_a_failure():
    regle, db = _db(0.0)
    for sd in regle["cellule"]["seeds"]:
        base = r3._entier(db, r3._cle("lam0", "p1", sd), N)
        _set(db, "lam09", "p1", sd, base + 29)                        # exactement la marge : PAS au-dessus
    L = r3.classify_pas(db, regle, "p1")
    assert L["comptes"]["lam09_sup_lam0"] == 0 and L["branche"] == "PAS_D_EFFET"


@pytest.mark.parametrize("champ,valeur", [("sham_omis", 15), ("porte_rang0_non_nul", 1),
                                           ("chemin_porte_applique", 1.2)])
def test_a_broken_instrument_blocks_every_reading(champ, valeur):
    regle, db = _db(0.0)
    d = db["_dose"][r3._cle("sham09", "p1", 5)]
    d = copy.deepcopy(d)
    if champ == "porte_rang0_non_nul":
        d["dose_instrument"][champ] = valeur
    else:
        d["sham"][champ] = valeur
    db["_dose"][r3._cle("sham09", "p1", 5)] = d
    L = r3.classify_pas(db, regle, "p1")
    assert L["branche"] == "INSTRUMENT_ROMPU" and len(L["rompus"]) == 1


def test_the_path_control_is_read_before_the_effect():
    regle, db = _db(0.0)
    for sd in regle["cellule"]["seeds"]:
        db[r3._cle("td0_d0", "p1", sd)] = db[r3._cle_ref("lr0_reference_d0", sd)]
        db[r3._cle("lam09", "p1", sd)] = db[r3._cle("lam0", "p1", sd)]   # et pas d'effet non plus
    assert r3.classify_pas(db, regle, "p1")["branche"] == "CONTROLE_CHEMIN_ECHOUE"


def test_a_small_total_gain_leaves_f_undefined_even_when_the_effect_count_passes():
    regle, db = _db(0.0, d=30)                                       # 12 × 30 = 360 > 348 : défini
    assert r3.classify_pas(db, regle, "p1")["branche"] == "TRANSPORTE"
    regle, db = _db(0.0, d=30)
    _set(db, "lam09", "p1", 12, r3._entier(db, r3._cle("lam0", "p1", 12), N) - 20)   # 11 × 30 − 20 = 310 ≤ 348
    L = r3.classify_pas(db, regle, "p1")
    assert L["comptes"]["lam09_sup_lam0"] == 11 and L["branche"] == "F_INDEFINI"


def test_the_literal_ADR_counts_are_published_against_the_lr0_bar():
    regle, db = _db(0.0)
    L = r3.classify_pas(db, regle, "p1")
    assert L["adr"] == {"lam09_franchit_la_barre": True, "sham_reste_sous_la_barre": True}
    assert L["comptes"]["lam0_sup_barre"] == 0                          # base − réf = 20 pas < 29


# ---------------------------------------------------------------------------------------------------- synthèse


def _deux_pas(f1, f2, apparie=True):
    regle, db1 = _db(f1, apparie=apparie)
    _, db2 = _db(f2, apparie=apparie, pas="p2")
    db = dict(db1)
    db.update({k: v for k, v in db2.items() if k not in ("_dose", "_regime")})
    db["_dose"] = dict(db1["_dose"], **db2["_dose"])
    return regle, db


def test_ENTRE_needs_TRANSPORTE_at_both_steps_and_the_E19_guard():
    regle, db = _deux_pas(0.0, 0.0)
    out = r3.lecture_r3(db, regle)
    assert out["garde_e19"]["issue"] == "PASSE" and out["synthese"]["issue"] == "ENTRE"
    L = {p: out["par_pas"][p] for p in ("p1", "p2")}
    assert r3.verdict_synthese(L, regle, None)["issue"] == "ATTEND"            # garde non appelée : jamais ENTRE


def test_the_secondary_step_never_refuses_alone_but_the_primary_does():
    regle, db = _deux_pas(0.0, 1.0)
    out = r3.lecture_r3(db, regle)
    assert out["par_pas"]["p2"]["branche"] == "PAS_PLUS_GROS" and out["synthese"]["issue"] == "ATTEND"
    regle, db = _deux_pas(1.0, 0.0)
    assert r3.lecture_r3(db, regle)["synthese"]["issue"] == "REFUSEE"


def test_the_paired_arm_blocks_ENTRE_when_TD0_at_equal_net_dose_does_as_well():
    regle, db = _deux_pas(0.0, 0.0)
    for p in ("p1", "p2"):
        for sd in regle["cellule"]["seeds"]:
            db[r3._cle("td0_app", p, sd)] = db[r3._cle("lam09", p, sd)]
    out = r3.lecture_r3(db, regle)
    assert out["synthese"]["issue"] == "ATTEND"
    assert any("DOSE" in m for m in out["synthese"]["manques"])


def test_an_unmatched_paired_arm_is_named_not_read():
    regle, db = _deux_pas(0.0, 0.0)
    for k, d in db["_dose"].items():
        if k.startswith("td0_app|"):
            db["_dose"][k] = {"dose_instrument": {"net_total": 3.0, "chemin_total": 6.0, "porte_rang0_non_nul": 0}}
    out = r3.lecture_r3(db, regle)
    assert out["synthese"]["issue"] == "ATTEND"
    assert any("non lisible" in m for m in out["synthese"]["manques"])


# ---------------------------------------------------------------------------------------------------- appariement


def _dose_blocs(nets):
    return {"dose_instrument": {"net_blocs": [{"W": [x / 2, x / 2]} for x in nets]}}


def test_rho_per_block_known_answer_and_refusals_instead_of_a_fabricated_rho():
    assert r3.rho_blocs(_dose_blocs([2.0, 6.0]), _dose_blocs([1.0, 3.0]), 2) == [2.0, 2.0]
    with pytest.raises(ValueError, match="tronqu"):
        r3.rho_blocs(_dose_blocs([2.0, 6.0, 1.0]), _dose_blocs([1.0, 3.0]), 2)
    with pytest.raises(ValueError, match="tronqu"):
        r3.rho_blocs(_dose_blocs([2.0]), _dose_blocs([1.0]), 2)
    with pytest.raises(ValueError, match="nul"):
        r3.rho_blocs(_dose_blocs([2.0, 6.0]), _dose_blocs([0.0, 3.0]), 2)


def test_calibration_by_injection_is_deterministic_and_its_frequencies_sum_to_one():
    regle = _regle()
    a = r3.calibrer_lecture(regle, [36.0] * 12, [9.3], [0.0, 1.0], 20, 5)
    b = r3.calibrer_lecture(regle, [36.0] * 12, [9.3], [0.0, 1.0], 20, 5)
    assert a == b
    for f in ("0.0", "1.0"):
        assert sum(a["par_sigma"]["9.3"][f].values()) == pytest.approx(1.0)


# ---------------------------------------------------------------------------------------------------- run par cellule


import hashlib  # noqa: E402
import json  # noqa: E402

DIGEST = "sha256:" + "d" * 64


def _regle_run():
    r = _regle()
    r["cellule"]["image_digest"] = DIGEST
    r["seuils"].update({"budget_etape_s": 14400, "safety": 1.5, "unite_reference_s": 5.0})
    return r


@pytest.fixture
def depot(monkeypatch, tmp_path):
    """Racine jetable : cellules, pré-vol et agrégat sous tmp_path ; sceau et provenance neutralisés."""
    monkeypatch.setattr(r3, "results_file", lambda *parties: tmp_path.joinpath(*parties))
    monkeypatch.setattr(r3, "stamp", lambda db, name: db)
    monkeypatch.setattr(r3, "verify", lambda name: (_ for _ in ()).throw(FileNotFoundError(name)))
    return tmp_path


def _jamais(*a, **k):
    raise AssertionError("entraînement appelé alors que la cellule devait être refusée EN TÊTE")


@pytest.mark.parametrize("bras,pas,seed,rho,motif", [
    ("sham_x", "p1", 3, None, "inconnu"), ("lam0", "p3", 3, None, "hors règle"), ("lam0", "p1", 13, None, "hors des"),
    ("td0_app", "p1", 3, None, "ρ exigés"), ("td0_app", "p1", 3, [1.0] * 5, "ρ exigés"),
    ("td0_app", "p1", 3, [1.0] * 5 + [0.0], "non positif"), ("lam09", "p1", 3, [1.0] * 6, "n'appartient")])
def test_a_cell_is_REFUSED_before_any_training_and_writes_nothing(depot, bras, pas, seed, rho, motif):
    with pytest.raises(ValueError, match=motif):
        r3.cellule_r3(bras, pas, seed, _regle_run(), rho=rho, entraine=_jamais)
    assert not any(depot.rglob("*.json"))


def _ecrire_cellule(racine, nom, rec):
    d = racine / "td_step_pilot_r3"
    d.mkdir(exist_ok=True)
    (d / f"{nom}.json").write_text(json.dumps(rec), encoding="utf-8")
    return d / f"{nom}.json"


def _blocs(nets):
    return {"dose_instrument": {"net_blocs": [{"W": [x]} for x in nets], "net_total": float(sum(nets)),
                                "chemin_total": 2.0 * sum(nets), "porte_rang0_non_nul": 0}}


def test_the_rho_argument_round_trips_EXACTLY_through_the_command_line(depot):
    regle = _regle_run()
    n9, n0 = [0.3, 0.7, 1.1, 0.9, 0.5, 0.2], [0.1, 0.35, 0.55, 0.3, 0.5, 0.15]
    _ecrire_cellule(depot, "lam09_p1_seed3", {"dose": _blocs(n9)})
    _ecrire_cellule(depot, "lam0_p1_seed3", {"dose": _blocs(n0)})
    arg = r3.rho_argument("p1", 3, regle)
    relu = [float(v) for v in arg.split(",")]
    assert relu == r3.rho_blocs(_blocs(n9), _blocs(n0), 6)                # au bit, comme dans le pod


@pytest.mark.parametrize("cpu_app,retenu", [(70.0, True), (100.0, False), (84.0, False)])
def test_the_preflight_decides_the_paired_arm_on_its_CPU_cost_only_and_is_FROZEN(depot, cpu_app, retenu):
    regle = _regle_run()
    for b, u in (("lam0", 70.0), ("lam09", 73.0), ("sham09", 73.0), ("td0_d0", 36.0), ("td0_app", cpu_app)):
        _ecrire_cellule(depot, f"{b}_p1_seed1", {"cpu_s": u})
    pv = r3.prevol_r3(regle)
    assert pv["fraction_cout_apparie"] == pytest.approx(cpu_app / 252.0) and pv["apparie_retenu"] is retenu
    assert r3.prevol_r3(regle) == pv                                        # même contenu : accepté
    _ecrire_cellule(depot, "lam0_p1_seed1", {"cpu_s": 71.0})
    with pytest.raises(ValueError, match="FIGÉ"):
        r3.prevol_r3(regle)


def test_the_preflight_REFUSES_without_its_measured_cells(depot):
    with pytest.raises(ValueError, match="MESURÉE"):
        r3.prevol_r3(_regle_run())


def _cellule_complete(racine, deport, nom, rec, lieu="nexus", image=DIGEST, rc=0, sha="abc", job=None):
    rec = dict(rec, provenance=rec.get("provenance", {"dirty": False, "git_sha": sha}), mur_s=1.0, cpu_s=1.0)
    q = _ecrire_cellule(racine, nom, rec)
    h = hashlib.sha256(q.read_bytes()).hexdigest()
    j = deport / (job or f"job-{nom}")
    j.mkdir(parents=True, exist_ok=True)
    (j / "MANIFEST.json").write_text(json.dumps({
        "job": j.name, "lieu": lieu, "sha": sha, "returncode": rc, "commande": ["-m", "tools.td_step_pilot_r3"],
        "image": f"10.1.2.3:5443/x/runner:t@{image}", "cpu": {"limite_cpu": 1.0, "threads_poses": {}},
        "debut_utc": "2026-10-14T08:00:00", "fin_utc": "2026-10-14T08:02:00",
        "fichiers": {f"results/td_step_pilot_r3/{nom}.json": {"sha256": h}}}), encoding="utf-8")


def test_the_aggregate_EXCLUDES_and_names_off_place_off_image_failed_dirty_or_unlinked_cells(depot):
    regle, dep = _regle_run(), depot / "deport"
    base = {"acc": 0.2, "dose": {}, "acc640": 0.2}
    _cellule_complete(depot, dep, "lam0_p1_seed1", dict(base, bras="lam0", pas="p1", seed=1))
    _cellule_complete(depot, dep, "lam0_p1_seed2", dict(base, bras="lam0", pas="p1", seed=2), lieu="batcave")
    _cellule_complete(depot, dep, "lam0_p1_seed3", dict(base, bras="lam0", pas="p1", seed=3), image="sha256:" + "e" * 64)
    _cellule_complete(depot, dep, "lam0_p1_seed4", dict(base, bras="lam0", pas="p1", seed=4), rc=1)
    _cellule_complete(depot, dep, "lam0_p1_seed5", dict(base, bras="lam0", pas="p1", seed=5,
                                                        provenance={"dirty": True}))
    _ecrire_cellule(depot, "lam0_p1_seed6", dict(base, bras="lam0", pas="p1", seed=6, provenance={"dirty": False},
                                                 mur_s=1.0, cpu_s=1.0))     # sans MANIFEST
    db = r3.agreger_r3(regle, str(dep))
    raisons = {e["cellule"]: e["raison"] for e in db["_regime"]["exclues"]}
    assert set(raisons) == {f"lam0_p1_seed{i}" for i in (2, 3, 4, 5, 6)}
    assert "lieu" in raisons["lam0_p1_seed2"] and "image" in raisons["lam0_p1_seed3"]
    assert "code" in raisons["lam0_p1_seed4"] and "sale" in raisons["lam0_p1_seed5"]
    assert "MANIFEST" in raisons["lam0_p1_seed6"]
    assert r3._cle("lam0", "p1", 1) in db and r3._cle("lam0", "p1", 2) not in db
    texte = (depot / "td_step_pilot_r3.json").read_text(encoding="utf-8")
    assert "10.1.2.3" not in texte and db["_lecture"]["par_pas"]["p1"]["branche"] == "INCOMPLET"


def test_the_aggregate_REFUSES_two_code_shas_and_rechecks_the_paired_rho_at_the_bit(depot):
    regle, dep = _regle_run(), depot / "deport"
    n9, n0 = [0.3, 0.7, 1.1, 0.9, 0.5, 0.2], [0.1, 0.35, 0.55, 0.3, 0.5, 0.15]
    for b, nets in (("lam09", n9), ("lam0", n0)):
        _cellule_complete(depot, dep, f"{b}_p1_seed3", {"bras": b, "pas": "p1", "seed": 3, "acc": 0.2,
                                                        "dose": _blocs(nets), "acc640": 0.2})
    bon = r3.rho_blocs(_blocs(n9), _blocs(n0), 6)
    _cellule_complete(depot, dep, "td0_app_p1_seed3", {"bras": "td0_app", "pas": "p1", "seed": 3, "acc": 0.2,
                                                       "dose": _blocs(n9), "acc640": 0.2,
                                                       "rho": [x * 1.0000001 for x in bon]})
    db = r3.agreger_r3(regle, str(dep))
    assert {"cellule": "td0_app_p1_seed3", "raison": "ρ reçu ≠ ρ recalculé depuis lam0 et lam09 de l'agrégat"} in \
        db["_regime"]["exclues"]
    assert r3._cle("td0_app", "p1", 3) not in db
    _cellule_complete(depot, dep, "lam0_p1_seed4", {"bras": "lam0", "pas": "p1", "seed": 4, "acc": 0.2,
                                                    "dose": {}, "acc640": 0.2}, sha="autre")
    with pytest.raises(ValueError, match="sha de code"):
        r3.agreger_r3(regle, str(dep))


def test_the_v2_calibration_reads_the_known_answers_without_noise():
    regle = _regle()
    a = r3.calibrer_lecture_v2(regle, 40.0, 0.0, [0.0], [0.0, 1.0], 5, 7)
    assert a["par_sigma_e"]["0.0"]["0.0"] == {"TRANSPORTE": 1.0}
    assert a["par_sigma_e"]["0.0"]["1.0"] == {"PAS_PLUS_GROS": 1.0}
    assert a == r3.calibrer_lecture_v2(regle, 40.0, 0.0, [0.0], [0.0, 1.0], 5, 7)


# ---------------------------------------------------------------------------------------------------- sous torch


# P2.169 (2026-10-13) — GARDE TORCH, par test (jamais un importorskip de MODULE : il ferait sauter les cas PURS).
import importlib.util  # noqa: E402
_TORCH = importlib.util.find_spec("torch") is not None
requires_torch = pytest.mark.skipif(not _TORCH, reason="torch absent : le test construit le backend torch ou lit "
                                                       "l'environnement torch")
torch = importlib.import_module("torch") if _TORCH else None
from tools.td_step_pilot import _eval_exhaustive, _train_eval_td_step  # noqa: E402
from src.agents.backend_torch import TorchPopulationModel as T  # noqa: E402

_FLAGS = ("CREDIT_TRACE_LAMBDA", "CREDIT_TRACE_BYPASS_OPTIMIZER", "CREDIT_TRACE_DELTA_SHAM", "CONDITION_GATE",
          "GATE_TARGET", "ANTISAT", "BILINEAR", "BILINEAR_RANK")


@pytest.fixture
def flags():
    saved = {k: getattr(T, k) for k in _FLAGS}
    yield
    for k, v in saved.items():
        setattr(T, k, v)


def _run(**kw):
    base = dict(seed=3, lam=0.9, episodes=4, n_agents=4, K=4, lr=0.5, eval_batches=2)
    base.update(kw)
    return _train_eval_td_step(base.pop("seed"), base.pop("lam"), base.pop("episodes"), base.pop("n_agents"),
                               base.pop("K"), base.pop("lr"), **base)


@requires_torch
def test_new_kwargs_default_to_the_R0_R2_path_and_the_instrument_is_a_no_op(flags):
    acc0, dose0 = _run()
    acc1, dose1 = _run(mesure_dose=True, eval_exhaustive=True)
    assert acc1 == acc0                                                # instrument + éval exhaustive : rien ne bouge
    assert {k: dose1[k] for k in dose0} == dose0
    _, dose2 = _run(eval_exhaustive=True)
    assert dose2["eval_exhaustive"] == dose1["eval_exhaustive"]        # même état final avec ou sans instrument


@requires_torch
def test_the_dose_instrument_is_exactly_zero_at_lr0_and_catches_the_terminal_flush(flags):
    _, d0 = _run(lr=0.0, mesure_dose=True, bloc_dose=2)
    di = d0["dose_instrument"]
    assert di["chemin_total"] == 0.0 and di["net_total"] == 0.0 and di["net_sur_chemin"] is None
    _, d = _run(mesure_dose=True, bloc_dose=2)
    di = d["dose_instrument"]
    assert di["appels_td_update"] == d["updates"] == 2 * 4             # learn au pas 1 ET le flush, à chaque épisode
    assert di["chemin_total"] >= di["net_total"] > 0.0
    assert len(di["net_blocs"]) == 2 and len(di["chemin_par_agent"]) == 4


@requires_torch
def test_per_block_steps_are_applied_published_and_require_the_instrument(flags):
    _, d1 = _run(lam=0.0, mesure_dose=True, bloc_dose=2)
    _, d2 = _run(lam=0.0, mesure_dose=True, bloc_dose=2, lr_blocs=[1.0, 3.0])
    assert d2["lr_blocs"] == [0.5, 1.5] and d2["dose_instrument"]["net_total"] != d1["dose_instrument"]["net_total"]
    _, d3 = _run(lam=0.0, mesure_dose=True, bloc_dose=2, lr_blocs=[1.0, 1.0])
    assert d3["dose_instrument"] == d1["dose_instrument"]            # ρ = 1 partout : le bras nu, au bit
    avant = {k: getattr(T, k) for k in _FLAGS}
    T.CREDIT_TRACE_LAMBDA = 0.123                                     # une valeur qu'un refus ne doit pas écraser
    with pytest.raises(ValueError, match="mesure_dose"):
        _run(lam=0.0, lr_blocs=[1.0, 1.0])
    with pytest.raises(ValueError, match="sham"):
        _run(controle_delta=True)
    assert T.CREDIT_TRACE_LAMBDA == 0.123                             # refus EN TÊTE : aucun drapeau posé ni laissé
    assert {k: getattr(T, k) for k in _FLAGS if k != "CREDIT_TRACE_LAMBDA"} == {
        k: v for k, v in avant.items() if k != "CREDIT_TRACE_LAMBDA"}


@requires_torch
def test_the_sham_arm_publishes_its_counters_and_its_key_control(flags):
    _, d = _run(sham="decale", mesure_dose=True, controle_delta=True, bloc_dose=2)
    assert d["sham"]["sham_omis"] == 4 and d["dose_instrument"]["porte_rang0_non_nul"] == 0
    assert sum(d["controle_delta"]["d1"]["n_par_cle"]) == 4 * 4        # δ1 à chaque épisode
    assert sum(d["controle_delta"]["dtilde"]["n_par_cle"]) == 4 * 3    # δ̃ absent au 1er épisode
    r = d["sham"]["chemin_porte_applique"] / d["sham"]["chemin_porte_contrefactuel"]
    assert r > 0.0


@requires_torch
def test_exhaustive_eval_draws_nothing_and_counts_on_the_K2_grid(flags):
    T.BILINEAR, T.BILINEAR_RANK = True, 16
    T.CREDIT_TRACE_LAMBDA, T.CREDIT_TRACE_DELTA_SHAM = 0.0, None
    T.CONDITION_GATE, T.GATE_TARGET = False, None
    from src.agents.mamba_agent import MambaAgent
    np.random.seed(1)
    torch.manual_seed(1)
    agent = T([MambaAgent() for _ in range(4)], lr=0.0)
    etat_np, etat_t = np.random.get_state(), torch.get_rng_state()
    s1 = _eval_exhaustive(agent, 4, False)
    s2 = _eval_exhaustive(agent, 4, False)
    assert np.array_equal(s1, s2) and s1.dtype == np.int64 and s1.min() >= 0 and s1.max() <= 16
    new_np = np.random.get_state()
    assert new_np[0] == etat_np[0] and np.array_equal(new_np[1], etat_np[1]) and new_np[2] == etat_np[2]
    assert torch.equal(torch.get_rng_state(), etat_t)


@requires_torch
def test_the_lr0_reference_without_training_equals_the_lr0_reference_trained(flags):
    acc, entraine = _run(lam=0.0, lr=0.0, episodes=5, eval_exhaustive=True)
    rien, nu = _run(lam=0.0, lr=0.0, episodes=0, eval_batches=0, eval_exhaustive=True)
    assert rien is None and acc is not None
    assert nu["eval_exhaustive"] == entraine["eval_exhaustive"]


@requires_torch
def test_a_cell_writes_its_own_file_with_the_rule_setup_and_publishes_rho(depot):
    vus = {}

    def entraine(seed, lam, episodes, n_agents, K, lr, **kw):
        vus.update(kw, lam=lam, lr=lr, episodes=episodes)
        return 0.2, {"updates": 6000, "eval_exhaustive": {"succes": 150, "n": 576, "succes_par_agent": [9] * 16}}
    rho = [1.5, 1.4, 1.3, 1.2, 1.1, 1.0]
    rec = r3.cellule_r3("td0_app", "p1", 3, _regle_run(), rho=rho, entraine=entraine)
    assert (depot / "td_step_pilot_r3" / "td0_app_p1_seed3.json").exists()
    assert rec["rho"] == rho and vus["lr_blocs"] == rho and vus["lam"] == 0.0 and vus["lr"] == 4.0
    assert vus["mesure_dose"] and vus["eval_exhaustive"] and vus["episodes"] == 3000 and rec["succes"] == 150
    rec = r3.cellule_r3("sham09", "p2", 3, _regle_run(), entraine=entraine)
    assert vus["sham"] == "decale" and vus["controle_delta"] and vus["lr_blocs"] is None and rec["rho"] is None
