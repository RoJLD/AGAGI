# -*- coding: utf-8 -*-
"""Calibration du chargement du Hall of Fame — la chaîne à TROIS maillons mesurée le 2026-09-08.

Le HoF décide QUEL SUJET toute mesure S2 utilise. Trois défauts s'enchaînaient :
 1. `tools/evo_memory_inworld` repointe `HOF_PATH` vers un HoF VIDE **à l'import**, pour tout le
    processus (intention légitime — EVO-003 veut une tabula rasa — effet global et silencieux) ;
 2. `load_hall_of_fame` avalait TOUTE exception et rendait « vide » : fichier ABSENT, fichier
    CORROMPU et HoF réellement vide devenaient indiscernables ;
 3. `tools/arm_nas` transformait « vide » en **(0, 0)** — une taille de génome moyenne MESURÉE à zéro.

Chaîne complète vérifiée le jour même : une sonde de saillance annonçait « HoF vide : évoluer
d'abord » alors que `data/hall_of_fame.pkl` contenait ses 10 entrées, intactes depuis juillet.

EXEMPTION DÉCLARÉE de la garde de bail : aucun monde n'est construit ici.
"""
import os
import pickle

import pytest

_LEASE_GUARD_EXEMPT = True


def _recharge(monkeypatch, chemin):
    """Recharge `persistence` avec un HOF_PATH imposé : la constante est lue à l'IMPORT du module,
    donc on la remplace sur le module déjà chargé — c'est le seul point où elle agit."""
    from src.seed_ai import persistence

    monkeypatch.setattr(persistence, "HALL_OF_FAME_PATH", str(chemin))
    return persistence


# --------------------------------------------------------------------------------------------------
# 1. ABSENT n'est pas ILLISIBLE
# --------------------------------------------------------------------------------------------------

def test_un_HoF_ABSENT_rend_vide_SILENCIEUSEMENT(monkeypatch, tmp_path):
    """Cas nominal du dépôt neuf : pas encore d'évolution, pas de fichier. C'est la branche NÉGATIVE
    appariée — sans elle, durcir le chargement casserait tout premier démarrage."""
    P = _recharge(monkeypatch, tmp_path / "jamais_ecrit.pkl")
    assert P.load_hall_of_fame() == (1, [])


def test_un_HoF_ILLISIBLE_LEVE_au_lieu_de_se_faire_passer_pour_VIDE(monkeypatch, tmp_path):
    """LE défaut. Un fichier présent mais corrompu rendait `(1, [])` : indiscernable d'un HoF vide.
    Le message doit NOMMER le chemin ET `HOF_PATH`, sinon il envoie chercher la cause à l'opposé."""
    p = tmp_path / "corrompu.pkl"
    p.write_bytes(b"ceci n'est pas un pickle")
    P = _recharge(monkeypatch, p)
    with pytest.raises(RuntimeError) as e:
        P.load_hall_of_fame()
    m = str(e.value)
    assert "ILLISIBLE" in m and str(p) in m and "HOF_PATH" in m


def test_un_HoF_de_FORME_INATTENDUE_LEVE(monkeypatch, tmp_path):
    """Un pickle valide mais qui n'est ni dict versionné ni liste : rendre « vide » masquerait une
    corruption silencieuse."""
    p = tmp_path / "forme.pkl"
    p.write_bytes(pickle.dumps({"pas_de_version": 1}))
    P = _recharge(monkeypatch, p)
    with pytest.raises(RuntimeError, match="INATTENDUE"):
        P.load_hall_of_fame()


def test_les_DEUX_formes_LEGITIMES_passent(monkeypatch, tmp_path):
    """Spécificité : le durcissement ne doit refuser AUCUN des deux formats réellement écrits par le
    dépôt (dict versionné, et liste nue pour la version 1)."""
    p = tmp_path / "ok.pkl"
    p.write_bytes(pickle.dumps({"version": 2, "entries": ["a", "b"]}))
    P = _recharge(monkeypatch, p)
    assert P.load_hall_of_fame() == (2, ["a", "b"])

    p.write_bytes(pickle.dumps(["x"]))
    assert P.load_hall_of_fame() == (1, ["x"])


def test_le_VRAI_HoF_du_depot_se_charge_encore(monkeypatch):
    """GARDE DE LA GARDE : le durcissement ne doit pas casser l'artefact réel. 10 entrées attendues,
    et toutes doivent porter un génome — c'est ce que `load_champion_genome` lit."""
    from src.seed_ai import persistence

    if not os.path.exists(persistence.HALL_OF_FAME_PATH):
        pytest.skip("pas de Hall of Fame dans cet arbre")
    version, entries = persistence.load_hall_of_fame()
    assert version >= 1 and entries, "le HoF réel ne se charge plus"
    assert all(hasattr(e, "genome") for e in entries)


# --------------------------------------------------------------------------------------------------
# 2. Le maillon aval : « vide » n'est pas une mesure
# --------------------------------------------------------------------------------------------------

def test_arm_nas_REFUSE_de_mesurer_une_taille_de_genome_sur_un_HoF_VIDE(monkeypatch):
    """`(0, 0)` était rendu comme une MESURE : « taille moyenne des génomes = 0 ». Forme (a) du biais
    systématique du dépôt. Doit lever, et nommer `HOF_PATH` — la cause réelle du vide, mesurée."""
    import tools.arm_nas as A

    monkeypatch.setattr(A, "load_hall_of_fame", lambda: (1, []))
    with pytest.raises(RuntimeError) as e:
        A.hof_stats()
    assert "HOF_PATH" in str(e.value)


def test_arm_nas_MESURE_quand_il_y_a_de_quoi_mesurer(monkeypatch):
    """Branche NÉGATIVE appariée : sur un HoF non vide, la mesure sort — sinon le durcissement aurait
    remplacé un faux chiffre par un refus permanent."""
    import tools.arm_nas as A

    class _E:
        def __init__(self, n):
            self.genome = type("G", (), {"num_nodes": n})()

    monkeypatch.setattr(A, "load_hall_of_fame", lambda: (1, [_E(10), _E(20)]))
    assert A.hof_stats() == (15.0, 20)
