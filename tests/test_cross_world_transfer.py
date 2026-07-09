"""Tests de la sonde de transfert zéro-shot cross-world (tools/cross_world_transfer.py).

On teste la LOGIQUE PURE (appariement -> ratios, forme du rapport) sans lancer la biosphère ;
la mesure elle-même (measure_in_world) est un smoke d'intégration séparé, marqué lourd."""
import math
import os
import statistics

import pytest

from tools.cross_world_transfer import paired_ratios, measure_in_world, _load_genome


def test_paired_ratios_apparie_par_index():
    # champ 2x meilleur que tabula seed a seed -> ratios = 2.0
    assert paired_ratios([40.0, 60.0], [20.0, 30.0]) == [2.0, 2.0]


def test_paired_ratios_tronque_a_la_longueur_min():
    # bras de longueurs differentes -> apparie sur le prefixe commun
    assert paired_ratios([40.0, 60.0, 80.0], [20.0, 30.0]) == [2.0, 2.0]


def test_paired_ratios_tabula_zero_ne_divise_pas_par_zero():
    # tabula=0 (mort immediate) -> pas de ZeroDivision, ratio fini et grand
    r = paired_ratios([50.0], [0.0])
    assert len(r) == 1
    assert math.isfinite(r[0]) and r[0] > 100.0


def test_paired_ratios_vide():
    assert paired_ratios([], []) == []


@pytest.mark.slow
def test_measure_in_world_contrat_et_condition_necessaire():
    """Smoke d'intégration : measure_in_world retourne k_eval médianes finies, ET la condition
    nécessaire à toute mesure de transfert tient — un champion dans SON monde >> tabula-rasa (sinon
    la survie serait au plancher, insensible au génome, et le ratio de transfert serait un artefact)."""
    if not os.path.exists("data/hall_of_fame_famine.pkl"):
        pytest.skip("HoF famine absent")
    k = 2
    champ = _load_genome("data/hall_of_fame_famine.pkl")
    champ_meds = measure_in_world("famine", champ, seed=42, k_eval=k, num_agents=6, max_ticks=120)
    tabula_meds = measure_in_world("famine", None, seed=42, k_eval=k, num_agents=6, max_ticks=120)
    assert len(champ_meds) == k and len(tabula_meds) == k
    assert all(math.isfinite(x) for x in champ_meds + tabula_meds)
    assert statistics.median(champ_meds) > statistics.median(tabula_meds)
