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
