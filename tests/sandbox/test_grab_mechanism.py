"""Calibration de la sonde de MECANISME du grab (P4.1-mecanisme, `tools/grab_mechanism_probe.py`).

Cette sonde refait la boucle de `run_condition` pour pouvoir observer le monde que celle-ci jette.
Une boucle refaite est un INSTRUMENT NEUF, et un instrument neuf ne se contente pas d'echouer : il
PRODUIT un bilan energetique parfaitement coherent, qui decrirait alors un autre monde que le record.
D'ou la forme de ces cas -- l'ancrage d'abord, la lecture ensuite.

La plupart ne construisent AUCUN monde : les gardes sont posees en TETE de fonction, et le compteur se
calibre par injection a dose connue. Seuls les deux cas marques `slow` simulent.
"""
import time

import numpy as np
import pytest

from tools.grab_mechanism_probe import (GrabCensusMamba, GrabCensusWorld, _trace_config,
                                        calibrate_census, run_census_arm)


# --- gardes d'ARGUMENTS : le refus doit etre instantane, donc pose AVANT le monde -----------------

@pytest.mark.parametrize("kw", [dict(num_agents=0), dict(max_ticks=0), dict(n_eras=0)])
def test_a_degenerate_argument_RAISES_instead_of_returning_a_measure(kw):
    """Un argument degenere est une erreur d'APPEL, pas un fait sur le monde. Sans cette garde, une
    cohorte vide rendrait `0.0` -- que l'aval lirait comme « les agents meurent immediatement ».
    C'est le biais systematique de ce depot : donnee absente -> affirmation NEGATIVE de fond."""
    base = dict(num_agents=4, max_ticks=10, n_eras=1)
    base.update(kw)
    with pytest.raises(ValueError, match="degenere"):
        run_census_arm(None, None, 0, **base)


def test_the_guard_sits_BEFORE_the_world_is_built():
    """On ne teste pas QUE la garde leve, on teste OU elle est posee. Une garde placee apres la
    construction du monde leverait aussi -- en quelques secondes de simulation. Le refus doit etre
    instantane : c'est la seule mesure qui distingue les deux emplacements."""
    t0 = time.time()
    with pytest.raises(ValueError):
        run_census_arm(None, None, 0, num_agents=0, max_ticks=400, n_eras=10)
    assert time.time() - t0 < 0.5, "la garde n'est pas en tete : un monde a ete construit avant le refus"


# --- le COMPTEUR de tentatives : dose connue, et une absence n'est PAS un zero --------------------

@pytest.mark.parametrize("dose", [0.0, 0.5, 1.0])
def test_the_attempt_counter_recovers_a_KNOWN_dose(dose):
    """Injection a DOSE CONNUE -- la technique qui rend la calibration d'un orchestrateur gratuite.
    Elle teste la couche qui transforme des observations en TAUX (accumulation, remise a zero, unite
    de comptage), sans simuler un seul monde. Trois doses, dont les deux bornes : une seule dose
    passerait sur un compteur qui renvoie une constante."""
    mesure, attendu = calibrate_census(taux_impose=dose)
    assert mesure == attendu == dose


def test_an_EMPTY_census_returns_None_and_NOT_zero():
    """⚠️ LE CAS QUI COMPTE. Sur zero observation, `attempt_rate` doit rendre `None`. Un `0.0` serait
    lu comme « le champion ne grabbe JAMAIS » -- une affirmation de fond fabriquee a partir d'une
    absence de donnee. C'est la forme (a) des trois formes que la dette de calibration a revelees, et
    la direction constante de la trentaine de defauts trouves alors : negative."""
    GrabCensusMamba.reset_census()
    assert GrabCensusMamba.attempt_rate() is None
    GrabCensusMamba._n_ticks_agents, GrabCensusMamba._n_attempts = 4, 0
    assert GrabCensusMamba.attempt_rate() == 0.0, (
        "un taux REELLEMENT nul, lui, doit se lire 0.0 -- sinon la garde efface un vrai resultat")
    GrabCensusMamba.reset_census()


def test_the_counter_RESETS_between_arms():
    """Le compteur est un attribut de CLASSE (le moteur reconstruit le modele a chaque tick), donc un
    etat PARTAGE -- la classe E5. Sans remise a zero verifiee, le taux du second bras contiendrait
    celui du premier, et rien ne le dirait."""
    calibrate_census(taux_impose=1.0)
    assert GrabCensusMamba._n_attempts == 0 and GrabCensusMamba._n_ticks_agents == 0


# --- le REGIME publie doit etre celui qui a cours -------------------------------------------------

def test_the_probe_reproduces_the_MEASURED_regime_not_the_ANNOUNCED_one():
    """CONTRE-EXEMPLE GELE, et c'est le defaut qui a motive cette passe. `EDR-GRAB-COST` s'ouvrait sur
    « le regime de famine dure porte `forage_payoff = 3.0` ». Or `run_condition` construit le monde
    avec `config=None`, donc le DEFAUT : 1.0. La sonde doit reproduire le regime MESURE.

    ⚠️ Et le second defaut est structurel, pas numerique : `forage_payoff` ne multiplie que la
    recompense de mise a mort d'une proie (`world_1_stoneage.py:800`). Il ne touche JAMAIS `do_grab`.
    Meme a 3.0 il n'aurait rien dit sur le grab -- la premisse etait un non-sequitur."""
    cfg = _trace_config()
    assert cfg.forage_payoff == 1.0, "le regime reproduit n'est plus celui du run publie"
    assert cfg.trace_energy_sinks is True
    import inspect

    from src.worlds import world_1_stoneage
    src = inspect.getsource(world_1_stoneage.Biosphere3D)
    lignes = [ln.strip() for ln in src.splitlines() if "forage_payoff" in ln]
    assert lignes, "`forage_payoff` a disparu du moteur : le referent de la premisse n'existe plus"
    assert all("prey_reward" in ln for ln in lignes), (
        f"`forage_payoff` ne multiplie plus SEULEMENT la recompense de mise a mort : {lignes}")


def test_the_grab_income_path_is_CHOKED_by_the_famine_masking():
    """LE MECANISME, verifie sur le CODE et non sur une simulation -- donc non refutable par un run
    malchanceux. Le moteur rend `+20` a `inventory[0]` SI son type est `Fruit`. `FamineWorld.step()`
    rebaptise tout Fruit d'inventaire en `_FruitReserve` AVANT `super().step()`. Un fruit detenu
    depuis un tick anterieur est donc invisible a ce revenu : seul un fruit ramasse dans le tick
    courant, et pose en position 0, peut nourrir. Si l'un ou l'autre disparaissait du code, la lecture
    du mecanisme deviendrait fausse en silence -- ce test l'interdit."""
    import inspect

    from src.worlds import world_1_stoneage, world_famine
    bio = inspect.getsource(world_1_stoneage.Biosphere3D._resolve_biology)
    assert 'item_type == "Fruit"' in bio and "energy\"] < 80" in bio, (
        "le revenu-fruit du moteur a change de forme")
    step = inspect.getsource(world_famine.FamineWorld.step)
    # ⚠️ On compare des lignes de CODE, jamais des sous-chaines : la premiere version de ce test
    # cherchait `super().step()` par `.index()` et trouvait sa mention dans un COMMENTAIRE, 1179
    # caracteres avant l'appel reel -- le test echouait sur du texte. C'est la meme faute que le grep
    # de verification non valide sur un cas positif connu, commise sur un test.
    code = [ln.strip() for ln in step.splitlines() if not ln.strip().startswith("#")]
    i_masque = next(i for i, ln in enumerate(code) if ln == 'it["type"] = "_FruitReserve"')
    i_step = next(i for i, ln in enumerate(code) if ln == "super().step()")
    assert i_masque < i_step, (
        "le masquage doit preceder le step moteur -- sinon le revenu-fruit n'est plus etrangle")


def test_the_census_is_taken_BEFORE_the_masking():
    """Le recensement doit lire l'inventaire dans l'etat que le moteur va voir. Pris apres le
    masquage, `tete_fruit` serait toujours nul -- un zero d'INSTRUMENT indiscernable d'un zero de
    MONDE, et celui-ci aurait confirme l'hypothese qu'il devait tester."""
    import inspect
    src = inspect.getsource(GrabCensusWorld.step)
    assert src.index('c["agent_ticks"] += 1') < src.index("super().step()")


# --- ANCRAGE et no-op : les deux cas qui simulent -------------------------------------------------

@pytest.mark.slow
@pytest.mark.timeout(900)
def test_the_rebuilt_loop_REPRODUCES_run_condition_EXACTLY():
    """⚠️ LE CAS SANS LEQUEL RIEN N'EST LISIBLE (E19 occ. 6 : un instrument de replication doit
    atteindre une reponse EXACTE connue avant de rapporter). La boucle refaite doit rendre la MEME
    survie que `run_condition`, l'instrument deja audite qui a produit le record. Un ecart d'un seul
    tick signifierait que le monde recense n'est pas le monde mesure.

    Il etablit aussi, en passant, que `trace_energy_sinks=True` est un NO-OP sur la dynamique : les
    deux bras ne different que par lui."""
    import pickle

    from tools.grab_mechanism_probe import anchor_against_run_condition
    from tools.jobs.run import hold
    # `pickle` : HoF produits LOCALEMENT par les runs d'evolution de ce depot (juillet 2026), charges
    # de la meme facon par `tools/s2_demand.py`. Aucune donnee non fiable n'est deserialisee.
    with open("data/hof_famine_harsh_s42.pkl", "rb") as fh:
        genome = pickle.load(fh)["entries"][0].genome
    with hold("kuzu", owner="test-grab-mechanism"):
        ok, mien, ref = anchor_against_run_condition(genome, 42, num_agents=8, max_ticks=120)
    assert ok, f"la boucle recensee n'est pas celle du record\n  mien={mien}\n  ref ={ref}"
    assert len(ref) == 8 and len(set(ref)) > 1, "ancrage sur une reponse DEGENEREE : il ne prouve rien"


@pytest.mark.slow
@pytest.mark.timeout(900)
def test_the_census_observer_is_BIT_IDENTICAL_to_the_bare_engine():
    """`GrabCensusMamba` lit la colonne 24 et y REECRIT la valeur lue : son plancher de bruit doit
    etre EXACTEMENT nul, comme `NullGrabOffMamba`. C'est ce qui autorise a lire son taux de grab comme
    celui du champion INTACT. Un observateur qui perturbe ne mesure plus le sujet qu'il observe."""
    import pickle

    from tools.jobs.run import hold
    with open("data/hof_famine_harsh_s42.pkl", "rb") as fh:
        genome = pickle.load(fh)["entries"][0].genome
    kw = dict(num_agents=8, max_ticks=120, n_eras=1)
    with hold("kuzu", owner="test-grab-census-noop"):
        GrabCensusMamba.reset_census()
        recense = run_census_arm(GrabCensusMamba, genome, 42, **kw)
        taux = GrabCensusMamba.attempt_rate()
        nu = run_census_arm(None, genome, 42, **kw)
    assert recense["survival"] == nu["survival"], "l'observateur PERTURBE : son taux n'est pas celui de l'intact"
    assert taux is not None and 0.0 <= taux <= 1.0, taux
    assert recense["agent_ticks"] > 0 and np.isfinite(recense["inv_taille_moy"])
    # ⚠️ IDENTITE COMPTABLE -- la calibration du recensement contre le MOTEUR, et le contre-exemple
    # de ce module. La premiere version recensait l'inventaire en tete de `step()`, donc AVANT le
    # grab : le poste `carry` impliquait un poids porte de 1,28 quand le recensement en annoncait
    # 0,35 -- facteur 3,7. Le bilan etait parfaitement coherent avec lui-meme et decrivait un autre
    # instant que celui ou le moteur facture. Seule cette identite le dit.
    assert recense["bouclage_carry"] < 1e-9, (
        f"le recensement ne reproduit pas le poste `carry` du moteur : ecart {recense['bouclage_carry']:.3e}")
    assert recense["carry_poids_moy"] == pytest.approx(
        recense["sinks_total"]["carry"] / max(1, recense["bio_ticks"]) / 0.5, rel=1e-9)
