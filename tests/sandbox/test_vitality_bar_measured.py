"""Calibration de la barre de VITALITE MESUREE des deux sondes qui ont grave des aretes (P2.15).

Ces deux sondes portent `language->perception` et `memory->perception` dans le graphe AGI-Taxonomy. Leur
`specificity_control` -- le SEUL bras dont l'issue negative est reellement atteignable, donc le seul qui
porte le contenu empirique de l'arete -- exige que le bras LEURRE soit VIVANT. Cette vitalite se jugeait
contre `1/K + 0.05 = 0.2167`, un seuil pose a l'estime.

MESURE du 2026-09-08, agent NON ENTRAINE (zero episode, meme monde, meme eval, 12 seeds) :
  * MEM-PERCEPTION, bras leurre PRESENT  -> max 0.2172  (au-DESSUS de la barre : 1 seed sur 12 aurait
    ete declaree « vivante » sans avoir rien appris) ;
  * LANG-PERCEPTION, bras leurre NO-COORD -> max 0.2039 (0.013 SOUS la barre, soit MOINS d'une
    erreur-type d'echantillonnage, 0.016).
La barre ne separait donc rien de facon DEMONTREE, dans aucun des deux sens.

⚠️ CE QUE CA NE FAIT PAS TOMBER, et c'est le point : les valeurs PUBLIEES valent 0.4844 et ~0.74, soit
DEUX A TROIS FOIS le plafond de l'incapable. La vitalite des deux aretes est etablie PAR LA MESURE, et
l'etait deja. Ce qui manquait etait la preuve que la barre separait quelque chose.
"""
import numpy as np
import pytest

from tools.experiment_preflight import PreflightError, assert_bar_separates_the_incapable
from tools.memory_perception_demand_probe import _untrained_ceiling

_K = 6
_ANCIENNE_BARRE = 1.0 / _K + 0.05


# --- le maillon lui-meme, sur reponses connues ------------------------------------------------------

def test_the_ceiling_is_a_MAXIMUM_not_a_median():
    """Un plafond est un MAX. Prendre la mediane sous-estimerait de moitie ce que l'incapable atteint,
    et c'est exactement le geste qui rend une barre trop basse."""
    plafond, _se, bruts = _untrained_ceiling([0, 1, 2, 3], lambda s: [0.10, 0.15, 0.30, 0.12][s], 640)
    assert plafond == 0.30, plafond
    assert bruts == [0.10, 0.15, 0.30, 0.12]
    assert plafond > float(np.median(bruts)), "le MAX doit dominer la mediane"


def test_the_standard_error_is_BINOMIAL_and_scales_with_n_eval():
    """La marge ajoutee au plafond est l'erreur-type d'echantillonnage, meme convention que
    `assert_bar_is_reachable`. Elle doit DECROITRE quand le nombre d'essais grandit -- sinon ce n'est
    pas une erreur-type mais une constante deguisee."""
    _p, se_petit, _ = _untrained_ceiling([0], lambda s: 0.25, 100)
    _p, se_grand, _ = _untrained_ceiling([0], lambda s: 0.25, 10000)
    assert se_petit > se_grand > 0.0, (se_petit, se_grand)
    assert abs(se_petit - np.sqrt(0.25 * 0.75 / 100)) < 1e-12


def test_the_derived_bar_ALWAYS_passes_the_guard():
    """Le couple (plafond, barre) doit etre coherent PAR CONSTRUCTION : `barre = plafond + se` avec
    `se > 0` franchit toujours la garde. Sans ce test, un plafond a 0 ou a 1 (ou `se = 0`) ferait lever
    la sonde EN PLEIN RUN au lieu d'etre attrape ici."""
    for val in (0.05, 0.2172, 0.5, 0.95):
        plafond, se, _ = _untrained_ceiling([0], lambda s: val, 640)
        assert se > 0.0, (val, se)
        assert assert_bar_separates_the_incapable(
            plafond + se, plafond, "plafond mesure d un agent non entraine, dispositif identique") is True


def test_the_OLD_bar_is_REFUSED_against_the_measured_ceiling():
    """⚠️ CONTRE-EXEMPLE GELE. La barre historique `1/K + 0.05` confrontee au plafond MESURE du bras
    leurre de MEM-PERCEPTION (0.2172) : la garde REFUSE. C'est le fait qui motive tout ce fichier."""
    with pytest.raises(PreflightError):
        assert_bar_separates_the_incapable(
            _ANCIENNE_BARRE, 0.2172,
            "plafond mesure d un agent NON ENTRAINE sur le bras leurre PRESENT, 12 seeds, zero episode")


def test_the_PUBLISHED_values_clear_the_measured_ceiling_by_a_WIDE_margin():
    """POSITIF APPARIE, et c'est ce qui empeche de lire ce dossier comme « les aretes tombent ». Les
    deux valeurs publiees dominent le plafond de l'incapable d'un facteur 2 a 3. Sans ce test, corriger
    la barre ressemblerait a une remise en cause des aretes -- elle n'en est pas une."""
    for nom, publie, plafond in (("MEM-PERCEPTION present_intact", 0.4844, 0.2172),
                                 ("LANG-PERCEPTION nocoord_intact", 0.74, 0.2039)):
        se = float(np.sqrt(plafond * (1 - plafond) / 640))
        assert publie > plafond + se, nom
        assert publie / plafond > 2.0, f"{nom} : marge attendue d'un facteur > 2, obtenu {publie / plafond:.2f}"


# --- confrontation au REEL ---------------------------------------------------------------------------

@pytest.mark.slow
@pytest.mark.timeout(900)
def test_the_untrained_ceiling_REPRODUCES_on_the_real_probes():
    """VALEUR GELEE, mesuree sans aucun entrainement. Si un de ces plafonds MONTAIT au-dessus de la
    valeur publiee du bras leurre, le `specificity_control` de l'arete correspondante deviendrait
    ininterpretable -- c'est la seule facon dont ce dossier pourrait faire tomber une arete."""
    from tools.memory_perception_demand_probe import _train_and_eval as mp
    from tools.perception_coordination_demand_probe import _train_and_eval as pc
    seeds = list(range(6))
    p_mp, _se, _ = _untrained_ceiling(
        seeds, lambda s: mp(s, "present", 0, 16, _K, 2, 0.02, 0.0, "learned")[0], 640)
    p_pc, _se, _ = _untrained_ceiling(
        seeds, lambda s: pc(s, True, 0, 32, _K, 8, 0.02, 0.0, "learned")[0], 640)
    assert p_mp < 0.30 and p_pc < 0.30, (p_mp, p_pc)
    assert p_mp < 0.4844 and p_pc < 0.74, (
        "le plafond de l'incapable doit rester SOUS la valeur publiee du bras leurre", p_mp, p_pc)


# --- RETAIN-COMPOSE : une barre PAR CONDITION, parce que l'incapable n'est pas le meme ---------------

def test_the_per_condition_ceilings_DIFFER_and_that_is_the_point():
    """VALEURS GELEES (12 seeds, zero episode, substrat BILINEAIRE) : same_tick 0.2031, oracle 0.1922,
    learned 0.1859, oracle_decorrelated 0.2016. Elles DIFFERENT -- une barre unique posee a l'estime ne
    pouvait pas en rendre compte, et surtout ne disait pas ce qu'elle separait."""
    plafonds = {"same_tick": 0.2031, "oracle": 0.1922, "learned": 0.1859, "oracle_decorrelated": 0.2016}
    assert len(set(plafonds.values())) == len(plafonds), "des plafonds identiques rendraient le decoupage vain"
    assert max(plafonds.values()) - min(plafonds.values()) > 0.01, plafonds
    for c, p in plafonds.items():
        assert p > 1.0 / _K, f"{c}: {p} au niveau de chance -> ce ne serait pas un plafond mesure"


def test_the_PUBLISHED_verdicts_are_UNCHANGED_by_the_measured_bars():
    """⚠️ CE QUI COMPTE LE PLUS ICI : recabler la barre ne devait PAS reecrire le passe. Les chiffres
    publies rendent les MEMES verdicts contre les barres mesurees -- la bascule E19 (RETENTION a
    lr=0.02, INCONCLUSIVE a lr=0.002) est intacte. Seule leur JUSTIFICATION change, et elle se renforce :
    « learned 0.173 » ne veut plus dire « sous 0.3167 » mais « pas mieux qu'un agent non entraine »."""
    bars = {"same_tick": 0.2031 + 0.0159, "oracle": 0.1922 + 0.0156, "learned": 0.1859 + 0.0154}
    lo = {"same_tick": 0.969, "oracle": 0.971, "learned": 0.173}     # lr=0.02, publie
    hi = {"same_tick": 0.937, "oracle": 0.945, "learned": 0.923}     # lr=0.002, publie
    assert lo["same_tick"] > bars["same_tick"] and lo["oracle"] > bars["oracle"]
    assert lo["learned"] <= bars["learned"], "lr=0.02 doit rester RETENTION"
    assert hi["learned"] > bars["learned"], "lr=0.002 doit rester INCONCLUSIVE -- la bascule est le resultat"


def test_the_decorrelated_control_is_BELOW_its_own_measured_ceiling():
    """Le controle NEGATIF de la sonde (key ALEATOIRE injecte en etat) mesure 0.162 contre un plafond
    d'incapable de 0.2016 pour SA condition : il est bien AU PLANCHER, et desormais contre un plancher
    MESURE au lieu d'un seuil importe."""
    assert 0.162 <= 0.2016 + 0.0159

