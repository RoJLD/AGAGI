"""Tests de la fonction pure energy_verdict (verdict ENCODEUR ; sans le sim).

NB : le test comportemental (d_forage) est CONFONDU (energie endogene au forage) -> pas dans le verdict.
Le banc etablit la moitie ENCODEUR : la detresse energetique est-elle representee dans H ?
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.energy_readout_probe import energy_verdict


def test_invalid_when_obs_at_chance():
    # l'energie ne decode meme pas de l'obs -> cible mal definie
    assert energy_verdict(acc_obs=0.52, acc_H=0.51, chance=0.5) == "INVALID_TARGET"


def test_encoder_rich_when_H_matches_or_beats_obs():
    # H represente l'energie au moins aussi bien que l'obs -> encodeur riche
    assert energy_verdict(acc_obs=0.83, acc_H=0.89, chance=0.5) == "ENCODER_RICH"


def test_encoder_rich_when_H_equals_obs():
    # exactement au seuil (preserve_frac=1.0 : H >= obs) -> riche
    assert energy_verdict(acc_obs=0.80, acc_H=0.80, chance=0.5) == "ENCODER_RICH"


def test_encoder_gap_when_H_below_obs():
    # H porte MOINS que l'obs -> la dynamique perd le signal energie
    assert energy_verdict(acc_obs=0.90, acc_H=0.65, chance=0.5) == "ENCODER_GAP"
