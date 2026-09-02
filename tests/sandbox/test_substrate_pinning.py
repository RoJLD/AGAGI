"""Calibration du cliquet `check_substrate_pinning` (P2.27).

Un cliquet doit pouvoir ÉCHOUER, et se confronter à une réponse CONNUE avant qu'on le croie : les deux
cliquets livrés le 2026-09-01 ont rendu 5 puis 2 faux positifs avant correction. Chaque cas ci-dessous
a donc une réponse connue AVANT la mesure, et il y a autant de cas `spares` (réponse NON) que de cas
`fires` (réponse OUI) — une garde qui refuse tout passerait les seconds seule.
"""
import pytest

from tools.check_substrate_pinning import _defects, scan

# --- sources SYNTHÉTIQUES à réponse connue -----------------------------------------------------

_PIN = "TorchPopulationModel.BILINEAR = bool(bilinear)\n"
_MAKE = "pop = make_population(agents, backend='torch')\n"
_ADAM_NU = "pop.opt = torch.optim.Adam([pop.W], lr=lr)\n"
_ADAM_PLEIN = ("params = [pop.W] + [p for p in (pop.U, pop.V, pop.W_bl) if p is not None]\n"
               "pop.opt = torch.optim.Adam(params, lr=lr)\n")


def test_the_ratchet_FIRES_on_an_unpinned_substrate():
    """Défaut A, réponse connue OUI : construit une population, n'épingle JAMAIS `BILINEAR`.
    C'est le cas des 16 sondes de l'audit du 2026-09-02, dont les DEUX qui ont gravé les arêtes."""
    assert _defects(_MAKE + _ADAM_PLEIN) == {"A"}


def test_the_ratchet_FIRES_on_an_incomplete_optimizer():
    """Défaut B, réponse connue OUI : épingle bien le substrat, mais `Adam([pop.W])` laisse
    `U/V/W_bl` GELÉS à leur init. Piège ARMÉ — latent tant que le flag est faux, il rend un nul qui
    ne mesure que l'initialisation dès qu'on l'active."""
    assert _defects(_PIN + _MAKE + _ADAM_NU) == {"B"}


def test_the_ratchet_FIRES_on_BOTH_at_once():
    """Les deux défauts sont INDÉPENDANTS et se cumulent — 11 des 16 sondes en dette portent les deux."""
    assert _defects(_MAKE + _ADAM_NU) == {"A", "B"}


def test_the_ratchet_SPARES_a_correct_probe():
    """POSITIF APPARIÉ, réponse connue NON. Sans lui, un cliquet qui crierait sur TOUTE sonde
    passerait les trois tests ci-dessus."""
    assert _defects(_PIN + _MAKE + _ADAM_PLEIN) == set()


def test_a_file_without_a_population_is_OUT_OF_SCOPE_not_CLEAN():
    """⚠️ La distinction qui compte : `None` (hors périmètre) n'est PAS `set()` (examiné, sans défaut).

    Les confondre ferait compter 191 fichiers sans rapport comme autant de succès, et le cliquet
    annoncerait une couverture de 210 là où il en examine 19. C'est le défaut « un cliquet qui annonce
    100 % quand il en fait 35 » que ce dépôt a déjà mesuré sur lui-même."""
    assert _defects("x = 1\nprint('rien a voir')\n") is None
    assert _defects(_PIN + _MAKE + _ADAM_PLEIN) is not None


# --- confrontation aux FICHIERS RÉELS ----------------------------------------------------------

def test_the_two_reconciled_probes_are_NOT_in_debt():
    """Ancrage sur le réel : les deux sondes corrigées le 2026-09-02 — par DEUX sessions
    indépendantes, `481117e` et `3b5554a` — doivent sortir SANS défaut. Si l'une régresse, ce test
    tombe avant que le cliquet ne l'absorbe dans sa baseline."""
    corriges = ["tools/delayed_coordination_demand_probe.py",
                "tools/language_memory_demand_probe.py"]
    en_defaut, hors, examines = scan(only=corriges)
    assert examines == 2, f"les deux sondes doivent être DANS le périmètre (hors={hors})"
    assert en_defaut == {}, f"régression d'épinglage : {en_defaut}"


def test_the_audit_count_is_STILL_REAL():
    """La dette gelée doit rester une DETTE, pas un commentaire. Si l'arbre entier passait sans
    défaut, la baseline ne protégerait plus rien et il faudrait la vider — même exigence que
    `test_the_legacy_declaration_is_STILL_REAL` pour la dette de pré-enregistrement."""
    en_defaut, hors, examines = scan()
    assert examines >= 19, f"le périmètre s'est effondré : {examines} sondes examinées"
    assert len(en_defaut) >= 1, "plus aucune dette : vider la baseline au lieu de la garder"
    assert len(hors) > examines, "le hors-périmètre doit être RAPPORTÉ, pas avalé"


@pytest.mark.parametrize("legataire", ["tools/memory_perception_demand_probe.py",
                                       "tools/perception_coordination_demand_probe.py"])
def test_the_two_edge_graving_probes_ARE_the_frozen_debt(legataire):
    """⚠️ CONTRE-EXEMPLE GELÉ le plus coûteux de l'audit : les deux sondes qui ont gravé les DEUX
    arêtes du graphe AGI-Taxonomy portent les deux défauts. Leurs résultats ne sont pas invalidés
    — l'ambiant était vraisemblablement `False`, donc substrat plain, ce qui est publié — mais RIEN
    dans le record ne permet de le VÉRIFIER. Ce test gèle le fait, pour qu'il ne se perde pas dans un
    compteur."""
    en_defaut, _hors, examines = scan(only=[legataire])
    assert examines == 1
    assert en_defaut.get(legataire) == ["A", "B"], en_defaut
