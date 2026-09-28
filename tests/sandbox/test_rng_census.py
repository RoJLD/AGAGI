"""Calibration de `tools/rng_census.py` (E34 v6) à réponse CONNUE, sans monde :
  (1) dose connue : 3 + 2 tirages avant la marque sur 2 sites, 4 après sur 1 site -> exactement ces comptes ;
  (2) no-op EXACT : la suite des tirages est la même avec et sans recensement ;
  (3) périmètre DÉCLARÉ : un générateur privé n'est pas compté ; une fenêtre jamais ouverte rend None, jamais 0 ;
  (4) réensemencements comptés à part, par fenêtre ; torch comparé par état (changé / inchangé) ;
  (5) gardes : seconde marque, marque hors bloc, réentrance ; restauration des fonctions à la sortie.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.rng_census import RecensementTirages, fonctions_globales  # noqa: E402


def _dose_connue():
    for _ in range(3):
        np.random.rand()                                       # site A
    for _ in range(2):
        np.random.choice([1, 2, 3])                            # site B


def test_known_dose_is_counted_per_site_and_per_window():
    np.random.seed(0)
    with RecensementTirages() as rec:
        _dose_connue()
        rec.marquer("t1=0")
        for _ in range(4):
            np.random.randint(0, 5)                            # site C
    r = rec.resume()
    assert r["tirages_avant"] == 5 and r["n_sites_avant"] == 2
    assert r["tirages_apres"] == 4 and r["n_sites_apres"] == 1
    (site, n), = r["sites_apres"].items()
    assert n == 4 and site.startswith("tests/sandbox/test_rng_census.py:")
    assert r["marque"] == "t1=0" and r["reensemencements_avant"] == 0 and r["reensemencements_apres"] == 0


def test_the_census_is_a_bit_exact_noop_on_the_draw_sequence():
    def suite():
        np.random.seed(123)
        v = [float(np.random.rand()), int(np.random.randint(0, 100)), float(np.random.normal()),
             int(np.random.choice([3, 5, 7])), float(np.random.uniform(1, 2))]
        a = np.arange(6)
        np.random.shuffle(a)
        return v + a.tolist() + np.random.permutation(5).tolist() + [float(np.random.random_sample())]
    sans = suite()
    with RecensementTirages() as rec:
        avec = suite()
    assert avec == sans and rec.resume()["tirages_avant"] == 8


def test_private_generators_are_outside_the_declared_perimeter_and_an_unopened_window_is_None():
    with RecensementTirages() as rec:
        np.random.RandomState(1).rand()                        # PRIVÉ : non vu, et c'est déclaré
        np.random.default_rng(1).random()
    r = rec.resume()
    assert r["tirages_avant"] == 0
    assert r["marque"] is None and r["tirages_apres"] is None and r["n_sites_apres"] is None
    assert r["sites_apres"] is None and r["reensemencements_apres"] is None and r["torch_rng_change_apres"] is None


def test_reseeds_are_counted_apart_and_per_window():
    with RecensementTirages() as rec:
        np.random.seed(4)
        rec.marquer("m")
        np.random.seed(5)
        np.random.set_state(np.random.get_state())
    r = rec.resume()
    assert r["reensemencements_avant"] == 1 and r["reensemencements_apres"] == 2 and r["tirages_apres"] == 0


def test_torch_rng_is_compared_by_state_after_the_mark():
    torch = pytest.importorskip("torch")
    with RecensementTirages() as rec:
        rec.marquer("m")
    assert rec.resume()["torch_rng_change_apres"] is False
    with RecensementTirages() as rec:
        rec.marquer("m")
        torch.rand(1)
    assert rec.resume()["torch_rng_change_apres"] is True


def test_guards_and_restoration():
    originaux = {n: getattr(np.random, n) for n in fonctions_globales()[0] + fonctions_globales()[1]}
    rec = RecensementTirages()
    with pytest.raises(RuntimeError):
        rec.marquer("hors bloc")
    with rec:
        assert np.random.rand is not originaux["rand"]
        rec.marquer("a")
        with pytest.raises(RuntimeError):
            rec.marquer("b")                                   # la fenêtre ne se déplace pas en silence
        with pytest.raises(RuntimeError):
            rec.__enter__()                                    # pas réentrant
    assert all(getattr(np.random, n) is f for n, f in originaux.items())


def test_the_wrapped_perimeter_covers_the_world_calls():
    """Les fonctions que le monde appelle (grep de world_1_stoneage.py le 2026-09-29 : rand, choice, randint, uniform)
    sont DANS le périmètre enveloppé ; `seed` et `set_state` sont comptés comme réensemencements."""
    tirages, ecritures = fonctions_globales()
    assert {"rand", "choice", "randint", "uniform", "random", "normal", "shuffle", "permutation", "ranf",
            "sample"} <= set(tirages)
    assert {"seed", "set_state"} <= set(ecritures) and "get_state" not in tirages + ecritures
