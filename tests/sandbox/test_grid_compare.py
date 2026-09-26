"""Calibration de `tools/grid_compare.py` (classe E30, P2.105) sur réponses CONNUES — et le CONTRE-EXEMPLE GELÉ
de la porte 24.

Le défaut : une accuracy est un COMPTE k/N (640 évaluations), une marge scellée à 0,05 vaut EXACTEMENT 32 pas, et
float32 décale k/640 de ~2e-6 — une ÉGALITÉ exacte comparée en flottants devient un dépassement ou un échec, toujours
du côté qui refuse (BILINEAR-SHAM-R1, seed 3 : 8/12 publié pour 9/12 exact). Ces cas ne construisent aucun monde :
des entiers connus, passés par float32 comme un runner les publie.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.grid_compare import cmp_continu, cmp_grille, marge_en_pas, sur_grille  # noqa: E402

N = 640


def _f32(k, n=N):
    """k/n tel qu'un runner le publie : passé par float32 (torch), donc décalé de ~2e-6."""
    return float(np.float32(k / n))


def test_CAS_FONDATEUR_E30_l_egalite_210_contre_178_plus_32_est_perdue_en_flottants_et_tenue_sur_la_grille():
    sham, plain = _f32(210), _f32(178)
    assert sham > plain + 0.05, "le défaut : en float32 l'égalité devient un dépassement (de 1,19e-08)"
    assert cmp_grille(sham, plain, 0.05, N) is False          # 210 > 178 + 32 est FAUX : c'est une égalité
    assert cmp_grille(sham, plain, 0.05, N, sens=-1) is False
    assert not cmp_grille(sham, plain, 0.05, N), "le critère scellé « sham <= plain + marge » est VRAI"


def test_CONTRE_EXEMPLE_GELE_126_contre_94_plus_32_est_une_egalite_que_float32_lit_comme_un_depassement():
    """L'égalité naturelle de P2.105 (126/640 contre 94/640 + 32 pas), portée sur une comparaison que le code
    effectue vraiment. GELÉ : c'est le témoin de la porte 24."""
    a, b = _f32(126), _f32(94)
    assert a > b + 0.05                                         # flottants : « dépassement » (FAUX)
    assert cmp_grille(a, b, 0.05, N) is False                  # grille : égalité, donc PAS de dépassement strict
    assert sur_grille(a, N) == 126 and sur_grille(b, N) == 94 and marge_en_pas(0.05, N) == 32


def test_marge_en_pas_publie_un_ENTIER_ou_None_jamais_un_arrondi():
    assert marge_en_pas(0.05, 640) == 32
    assert marge_en_pas(0.05, 1280) == 64
    assert marge_en_pas(0.0, 640) == 0
    assert marge_en_pas(0.5, 640) == 320
    assert marge_en_pas(0.03, 640) is None                      # 19,2 pas : PAS un multiple -> dit, jamais arrondi


def test_l_etage_des_MEDIANES_vit_sur_2N():
    """La médiane de 12 comptes est un demi-entier sur N : hors grille sur N (dit), entière sur 2N."""
    med_a = (_f32(126) + _f32(127)) / 2
    med_b = (_f32(94) + _f32(95)) / 2
    assert sur_grille(med_a, N) is None and sur_grille(med_a, 2 * N) == 253
    assert cmp_grille(med_a, med_b, 0.05, 2 * N) is False      # 253 > 189 + 64 : FAUX, égalité exacte
    assert cmp_grille(med_a + 1 / (2 * N), med_b, 0.05, 2 * N) is True


def test_la_marge_ZERO_est_commensurable_et_une_egalite_n_est_ni_dessus_ni_dessous():
    x = _f32(300)
    assert cmp_grille(x, x, 0.0, N) is False and cmp_grille(x, x, 0.0, N, sens=-1) is False
    assert cmp_grille(_f32(301), x, 0.0, N) is True and cmp_grille(_f32(299), x, 0.0, N, sens=-1) is True


def test_le_repli_DECLARE_hors_grille_est_la_comparaison_ordinaire():
    assert sur_grille(0.1234, N) is None
    assert cmp_grille(0.1234, 0.1, 0.05, N) is cmp_continu(0.1234, 0.1, 0.05) is False
    assert cmp_grille(0.1734, 0.1, 0.05, N) is cmp_continu(0.1734, 0.1, 0.05) is True


def test_cmp_continu_est_l_ecriture_DECLAREE_de_la_comparaison_ordinaire_dans_les_deux_sens():
    assert cmp_continu(0.3, 0.2, 0.05) is True and cmp_continu(0.25, 0.2, 0.05) is False
    assert cmp_continu(0.1, 0.2, 0.05, sens=-1) is True and cmp_continu(0.16, 0.2, 0.05, sens=-1) is False


def test_le_controle_positif_de_R0_barre_0_5_sur_2N():
    """`max(médianes) < 0,5` (TD-STEP-PILOT-R0) : la barre 0,5 vaut 640 pas sur 2N ; une médiane EXACTEMENT à 0,5
    n'est pas en dessous, une médiane à 639/1280 l'est."""
    assert cmp_grille(0.5, 0.5, 0.0, 2 * N, sens=-1) is False
    assert cmp_grille((_f32(319) + _f32(320)) / 2, 0.5, 0.0, 2 * N, sens=-1) is True
