# -*- coding: utf-8 -*-
"""Calibration de `_gaps_pour_verdict` -- trois exemplaires IDENTIQUES (craft_or_starve_edr, kchain_edr,
torch_binary_gate_probe), chacun teste a reponse connue, car une copie qui diverge divergera en silence.

Ce qu'il fait : appliquer EXPLICITEMENT la regle de l'auteur (kchain L386, « masque vide -> ne compose
pas ») a des gaps dont certains sont INDEFINIS (None), et COMPTER combien l'ont ete. Le compte est la
raison d'etre : une mediane de gaps dont la moitie sont des zeros de convention ne dit pas la meme chose
qu'une mediane de gaps mesures (P2.52, 2026-09-14).
"""
import pytest

from tools import craft_or_starve_edr, kchain_edr, torch_binary_gate_probe

_EXEMPLAIRES = [craft_or_starve_edr._gaps_pour_verdict, kchain_edr._gaps_pour_verdict,
                torch_binary_gate_probe._gaps_pour_verdict]


@pytest.mark.parametrize("f", _EXEMPLAIRES)
def test_un_gap_INDEFINI_compte_zero_ET_est_compte(f):
    """Dose connue : deux indefinis sur quatre -> deux zeros, compte 2, les mesures INTACTES."""
    nums, n_ind = f([0.7, None, -0.2, None])
    assert nums == [0.7, 0.0, -0.2, 0.0] and n_ind == 2


@pytest.mark.parametrize("f", _EXEMPLAIRES)
def test_sans_indefini_RIEN_ne_change_et_le_compte_est_zero(f):
    """NO-OP EXACT : des gaps tous mesures ressortent identiques, compte 0."""
    gaps = [0.61, 0.02, -0.3, 1.0]
    assert f(gaps) == (gaps, 0)


@pytest.mark.parametrize("f", _EXEMPLAIRES)
def test_TOUS_indefinis_rend_des_zeros_ET_le_dit(f):
    """Le cas du metronome nul mort a T = 200 : la mediane vaudra 0, et `n_indefini == n` le DIT --
    c'est exactement l'information qui manquait quand ce 0 passait pour une mesure."""
    assert f([None, None, None]) == ([0.0, 0.0, 0.0], 3)


@pytest.mark.parametrize("f", _EXEMPLAIRES)
def test_un_gap_a_ZERO_mesure_n_est_PAS_compte_comme_indefini(f):
    """Specificite : 0.0 MESURE (p1 == p0) et None ne se confondent pas. Sans ce cas, une version
    ecrite `if not g` compterait les vrais zeros comme des absences."""
    assert f([0.0, None]) == ([0.0, 0.0], 1)


def test_les_trois_exemplaires_sont_IDENTIQUES_sur_le_meme_jeu():
    """Une copie qui divergerait divergerait en silence ; ce cas le rend visible."""
    jeu = [0.5, None, 0.0, -0.1, None]
    assert len({f(jeu) == _EXEMPLAIRES[0](jeu) for f in _EXEMPLAIRES}) == 1
    assert all(f(jeu) == _EXEMPLAIRES[0](jeu) for f in _EXEMPLAIRES)
