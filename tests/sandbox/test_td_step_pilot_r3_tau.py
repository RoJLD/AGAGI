"""Mesure de τ avant le sceau de R3 (tools/td_step_pilot_r3_tau.py) : refus EN TÊTE (seeds du verdict, sham) testés par
leur EMPLACEMENT (aucun entraînement appelé, aucun fichier écrit), `measure_tau` sur des réponses CONNUES, agrégat qui
refuse des lieux mêlés et ne publie jamais une adresse de registre. Aucune simulation."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import tools.td_step_pilot_r3_tau as tau  # noqa: E402

# P2.169 (2026-10-13) — GARDE TORCH, par test (jamais un importorskip de MODULE : il ferait sauter les cas PURS).
import importlib.util  # noqa: E402
_TORCH = importlib.util.find_spec("torch") is not None
requires_torch = pytest.mark.skipif(not _TORCH, reason="torch absent : le test construit le backend torch ou lit "
                                                       "l'environnement torch")


def _jamais(*a, **k):
    raise AssertionError("entraînement appelé alors que la cellule devait être refusée EN TÊTE")


@pytest.fixture
def racine(monkeypatch, tmp_path):
    monkeypatch.setattr(tau, "results_file", lambda *parties: tmp_path.joinpath(*parties))
    return tmp_path


@pytest.mark.parametrize("bras,seed,motif", [("lam09", 5, "VERDICT"), ("lam0", 12, "VERDICT"), ("lam0", 1, "VERDICT"),
                                             ("sham09", 13, "JAMAIS le sham"), ("td0_d0", 20, "refusé"),
                                             ("lam0", 25, "hors des seeds")])
def test_a_verdict_seed_or_another_arm_is_REFUSED_before_any_training_and_writes_nothing(racine, bras, seed, motif):
    with pytest.raises(ValueError, match=motif):
        tau.cellule(bras, seed, entraine=_jamais)
    assert not any(racine.rglob("*.json"))


def _faux_entraine(succes_par_bras):
    def entraine(seed, lam, episodes, n_agents, K, lr, **kw):
        assert (episodes, n_agents, K, lr, kw["trace_reset_per_episode"], kw["eval_exhaustive"]) == (
            3000, 16, 6, 4.0, True, True)
        s = succes_par_bras[lam](seed)
        return 0.2, {"updates": 6000, "eval_exhaustive": {"succes": s, "n": 576, "succes_par_agent": [s // 16] * 16}}
    return entraine


@requires_torch
def test_a_cell_writes_its_own_file_with_the_R3_setup(racine):
    rec = tau.cellule("lam09", 13, entraine=_faux_entraine({0.9: lambda sd: 150, 0.0: lambda sd: 110}))
    p = racine / "td_step_pilot_r3_tau" / "lam09_seed13.json"
    assert p.exists() and json.loads(p.read_text(encoding="utf-8"))["succes"] == 150
    assert rec["lambda"] == 0.9 and rec["n"] == 576 and "eval_exhaustive" not in rec["dose"]


def test_measure_tau_known_answers():
    plat = {(b, sd): (150 if b == "lam09" else 110) for sd in tau.SEEDS_TENUES for b in tau.BRAS}
    t = tau.measure_tau(plat)
    assert t["d_pas"] == [40] * 12 and t["moyenne_pas"] == 40 and t["tau_pas"] == 0.0 and t["d_sup_marge"] == 12
    alt = {("lam0", sd): 110 for sd in tau.SEEDS_TENUES}
    alt.update({("lam09", sd): 110 + (30 if i % 2 else 50) for i, sd in enumerate(tau.SEEDS_TENUES)})
    t = tau.measure_tau(alt)
    assert t["moyenne_pas"] == 40 and t["tau_pas"] == pytest.approx(10.4446, abs=1e-4)
    assert t["d_sup_marge"] == 12                                     # 30 > 29 : strictement au-dessus
    alt[("lam09", 13)] = 110 + 29                                     # exactement la marge : PAS au-dessus
    assert tau.measure_tau(alt)["d_sup_marge"] == 11


def test_measure_tau_incomplete_gives_None_never_a_fabricated_zero_and_refuses_a_verdict_seed():
    t = tau.measure_tau({("lam0", 13): 110, ("lam09", 13): 150, ("lam0", 14): 110})
    assert t["tau_pas"] is None and t["moyenne_pas"] == 40.0 and t["d_sup_marge"] is None
    assert "lam09|seed=14" in t["manquantes"] and len(t["manquantes"]) == 21
    with pytest.raises(ValueError, match="VERDICT"):
        tau.measure_tau({("lam0", 3): 110, ("lam09", 3): 150})


def _cellule_fichier(racine, bras, seed, succes, systeme="Linux-7.0.0-x86_64", torch_v="2.6.0+cpu"):
    d = racine / "td_step_pilot_r3_tau"
    d.mkdir(exist_ok=True)
    rec = {"bras": bras, "seed": seed, "succes": succes, "n": 576, "succes_par_agent": [0] * 16, "acc640_tiree": 0.2,
           "mur_s": 1.0, "cpu_s": 1.0, "dose": {"updates": 6000}, "provenance": {"git_sha": "x"},
           "environnement": {"systeme": systeme, "torch": torch_v}}
    (d / f"{bras}_seed{seed}.json").write_text(json.dumps(rec), encoding="utf-8")


def test_aggregate_refuses_mixed_places_and_never_publishes_a_registry_address(racine, tmp_path):
    for sd in tau.SEEDS_TENUES:
        _cellule_fichier(racine, "lam0", sd, 110)
        _cellule_fichier(racine, "lam09", sd, 150)
    dep = tmp_path / "deport" / "job-a"
    dep.mkdir(parents=True)
    (dep / "MANIFEST.json").write_text(json.dumps({
        "job": "job-a", "lieu": "nexus", "sha": "abc", "returncode": 0, "duree_mur_s": 9.0,
        "commande": ["-m", "tools.td_step_pilot_r3_tau", "cellule", "--bras", "lam0", "--seed", "13"],
        "image": "10.0.0.1:5443/x/runner:tag@sha256:" + "a" * 64,
        "cpu": {"limite_cpu": 1.0, "threads_poses": {"OMP_NUM_THREADS": "1"}, "threads_source": "cgroup"}}),
        encoding="utf-8")
    db = tau.agreger(str(tmp_path / "deport"))
    texte = (racine / "td_step_pilot_r3_tau.json").read_text(encoding="utf-8")
    assert "10.0.0.1" not in texte and "5443" not in texte
    assert db["cellules"]["lam0|seed=13"]["manifeste"]["image_digest"] == "sha256:" + "a" * 64
    assert db["tau"]["tau_pas"] == 0.0
    _cellule_fichier(racine, "lam0", 13, 110, systeme="Windows-11-10.0.26200", torch_v="2.6.0+cu124")
    with pytest.raises(ValueError, match="lieux mêlés"):
        tau.agreger(str(tmp_path / "deport"))


# ---------------------------------------------------------------- séance du 2026-10-14 (décisions de robla 4, 7, 8)


@pytest.mark.parametrize("bras,seed,pas,rep,motif", [
    ("lam0", 13, "p3", 0, "hors règle"), ("sham_dose", 13, "p1", 1, "réplique"), ("lam09", 13, "p1", -1, "réplique"),
    ("sham_identite", 4, "p1", 0, "VERDICT"), ("sham_decale", 13, "p1", 0, "JAMAIS le sham décalé")])
def test_the_new_kinds_are_REFUSED_before_any_training(racine, bras, seed, pas, rep, motif):
    with pytest.raises(ValueError, match=motif):
        tau.cellule(bras, seed, entraine=_jamais, pas=pas, replique=rep)
    assert not any(racine.rglob("*.json"))


def _dose_sham(applique, contrefactuel):
    return {"updates": 6000, "sham": {"mode": "decale", "sham_omis": 16, "chemin_porte_applique": applique,
                                      "chemin_porte_contrefactuel": contrefactuel, "chemin_td0": 1.0}}


def test_a_DOSE_ONLY_sham_that_comes_back_with_an_accuracy_is_REFUSED_and_writes_nothing(racine):
    """Décision 7 : le sham décalé ne tourne qu'en dose seule ; une accuracy rendue serait un f vu avant le sceau."""
    with pytest.raises(ValueError, match="aucun f"):
        tau.cellule("sham_dose", 13, entraine=lambda *a, **k: (0.2, _dose_sham(1.0, 1.0)))
    with pytest.raises(ValueError, match="aucun f"):
        tau.cellule("sham_dose", 13, entraine=lambda *a, **k: (None, dict(_dose_sham(1.0, 1.0),
                                                                          eval_exhaustive={"n": 576})))
    assert not any(racine.rglob("*.json"))


@requires_torch
def test_a_DOSE_ONLY_sham_cell_carries_its_ratio_and_no_accuracy_and_p2_runs_at_four_root_two(racine):
    vus = {}

    def entraine(seed, lam, episodes, n_agents, K, lr, **kw):
        vus.update(kw, lam=lam, lr=lr)
        return None, _dose_sham(1.05, 1.0)
    rec = tau.cellule("sham_dose", 14, entraine=entraine, pas="p2")
    assert vus["sham"] == "decale" and vus["eval_batches"] == 0 and vus["eval_exhaustive"] is False
    assert vus["lr"] == pytest.approx(4.0 * 2 ** 0.5) and rec["ratio_applique_contrefactuel"] == pytest.approx(1.05)
    assert "succes" not in rec and (racine / "td_step_pilot_r3_tau" / "sham_dose_p2_seed14.json").exists()
    rec = tau.cellule("lam0", 13, entraine=_faux_entraine({0.0: lambda sd: 110}), pas="p1", replique=1)
    assert (racine / "td_step_pilot_r3_tau" / "lam0_seed13_rep1.json").exists() and rec["replique"] == 1


def test_measure_dispersion_dose_known_answers_with_inclusive_bounds_and_undefined_ratios_counted():
    t = tau.measure_dispersion_dose({13: 1.0, 14: 0.9, 15: 1.1, 16: 1.12, 17: None})
    assert t["n"] == 4 and t["hors_bande"] == 1 and t["indefinis"] == [17]
    assert t["min"] == 0.9 and t["max"] == 1.12 and t["mediane"] == pytest.approx(1.05)
    assert tau.measure_dispersion_dose({})["hors_bande"] is None
    with pytest.raises(ValueError, match="VERDICT"):
        tau.measure_dispersion_dose({3: 1.0})


def test_measure_noop_identite_known_answers():
    s = {}
    for i, sd in enumerate(tau.SEEDS_TENUES):
        s[("lam0", sd)], s[("lam09", sd)] = 110, 150 + (i % 3)
        s[("sham_identite", sd)] = s[("lam09", sd)]
    t = tau.measure_noop_identite(s)
    assert t["identiques_au_bit"] == 12 and t["ecart_max_abs_pas"] == 0 and t["f_hat"]["f"] == 1.0
    assert t["f_hat"]["ic90"] == [1.0, 1.0]
    s[("sham_identite", 13)] += 2
    s[("sham_identite", 14)] -= 2
    t = tau.measure_noop_identite(s)
    assert t["identiques_au_bit"] == 10 and t["ecart_max_abs_pas"] == 2 and t["ecart_type_pas"] > 0


def test_measure_replication_is_bit_strict():
    a = {"bras": "lam0", "seed": 13, "succes": 111, "succes_par_agent": [7] * 16, "acc640_tiree": 0.2,
         "dose": {"dose_instrument": {"net_total": 1.5}}}
    b = json.loads(json.dumps(a))
    c = json.loads(json.dumps(a))
    c["dose"]["dose_instrument"]["net_total"] = 1.5000000001
    r = tau.measure_replication([(a, b), (a, c)])
    assert r["paires"] == 2 and r["identiques"] == 1 and r["detail"][1]["champs"]["net_total"] is False


def test_the_aggregate_publishes_tau_PER_STEP_the_dose_dispersion_the_noop_and_the_replication(racine, tmp_path):
    for i, sd in enumerate(tau.SEEDS_TENUES):
        _cellule_fichier(racine, "lam0", sd, 110)
        _cellule_fichier(racine, "lam09", sd, 150)
        for b, nom, extra in (("lam0", f"lam0_p2_seed{sd}", {"succes": 110}),
                              ("lam09", f"lam09_p2_seed{sd}", {"succes": 140 + (i % 2) * 10}),
                              ("sham_identite", f"sham_identite_seed{sd}", {"succes": 150}),
                              ("sham_dose", f"sham_dose_seed{sd}", {"ratio_applique_contrefactuel": 1.0 + i / 100})):
            d = racine / "td_step_pilot_r3_tau"
            rec = {"bras": b, "seed": sd, "pas_cle": "p2" if "_p2_" in nom else "p1", "n": 576, "acc640_tiree": None,
                   "succes_par_agent": None, "mur_s": 1.0, "cpu_s": 1.0, "dose": {"updates": 6000},
                   "provenance": {"git_sha": "x"}, "environnement": {"systeme": "Linux-7.0.0-x86_64",
                                                                      "torch": "2.6.0+cpu"}, **extra}
            (d / f"{nom}.json").write_text(json.dumps(rec), encoding="utf-8")
    (racine / "td_step_pilot_r3_tau" / "lam0_seed13_rep1.json").write_text(json.dumps(
        {"bras": "lam0", "seed": 13, "replique": 1, "succes": 110, "n": 576, "succes_par_agent": [0] * 16,
         "acc640_tiree": 0.2, "mur_s": 1.0, "cpu_s": 1.0, "dose": {"updates": 6000}, "provenance": {"git_sha": "x"},
         "environnement": {"systeme": "Linux-7.0.0-x86_64", "torch": "2.6.0+cpu"}}), encoding="utf-8")
    db = tau.agreger(str(tmp_path / "deport_absent"))
    assert db["tau"]["tau_pas"] == 0.0 and db["tau_par_pas"]["p2"]["moyenne_pas"] == 35.0
    assert db["dispersion_dose_sham"]["p1"]["n"] == 12 and db["dispersion_dose_sham"]["p1"]["hors_bande"] == 1
    assert db["noop_identite"]["p1"]["identiques_au_bit"] == 12
    assert db["replication"] == {"paires": 1, "identiques": 1, "detail": db["replication"]["detail"]}
    assert "lam0|seed=13" in db["cellules"] and "lam0|pas=p2|seed=13" in db["cellules"] and \
        "lam0|seed=13|rep=1" in db["cellules"]
