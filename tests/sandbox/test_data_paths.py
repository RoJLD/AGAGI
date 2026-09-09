# -*- coding: utf-8 -*-
"""Calibration du cliquet des CHEMINS DE DONNÉES (`tools/check_data_paths.py`).

⚠️ Un cliquet doit pouvoir ÉCHOUER, et se calibrer comme un instrument : les deux cliquets livrés le
2026-09-01 ont rendu 5 puis 2 faux positifs avant d'être corrigés.

Les branches NÉGATIVES comptent ici autant que les positives, et pour une raison précise : ce cliquet
existe pour ENCOURAGER une migration. S'il criait quand un site est migré, ou quand un chemin est
cité dans un commentaire, il serait du bruit — et une garde bruyante se fait désarmer.

EXEMPTION DÉCLARÉE de la garde de bail : aucun monde n'est construit.
"""
import json
import os

import pytest

from tools.check_data_paths import nouveaux, scan_literals

_LEASE_GUARD_EXEMPT = True


# --------------------------------------------------------------------------------------------------
# 1. Ce que le scan VOIT, et ce qu'il ne voit pas
# --------------------------------------------------------------------------------------------------

_AVEC = '''
CHEMIN = "data/hall_of_fame.pkl"
def f():
    return open("results/mesure.json")
'''

_COMMENTAIRE = '''
"""On pourrait ecrire data/hall_of_fame.pkl ici, mais on ne le fait pas."""
# et results/mesure.json en commentaire non plus
def f():
    from src.paths import hall_of_fame
    return open(hall_of_fame())
'''

_HORS_SUJET = '''
DOC = "docs/EDR/x.md"
RE = r"^(\\d{3})_(.+)\\.md$"
URL = "https://exemple/data/x.json"
DYNAMIQUE = os.path.join(racine, "hall_of_fame.pkl")
'''


def test_le_scan_voit_les_litteraux_de_DONNEES():
    assert scan_literals([("tools/x.py", _AVEC)]) == {
        "tools/x.py": ["data/hall_of_fame.pkl", "results/mesure.json"]}


def test_le_scan_IGNORE_les_chemins_cites_en_COMMENTAIRE_ou_docstring():
    """C'est la raison d'être de l'analyse AST. Un cliquet qui crierait sur de la prose serait du
    bruit, et le code MIGRÉ cite justement son ancien chemin pour expliquer la migration — le punir
    reviendrait à décourager exactement ce qu'on veut."""
    assert scan_literals([("tools/x.py", _COMMENTAIRE)]) == {}


def test_le_scan_IGNORE_ce_qui_n_est_PAS_une_donnee():
    """Un chemin de documentation, une regex, une URL, et surtout un chemin CONSTRUIT dynamiquement
    (déjà indirect, donc hors sujet) ne doivent rien déclencher."""
    assert scan_literals([("tools/x.py", _HORS_SUJET)]) == {}


def test_un_fichier_ILLISIBLE_ou_INVALIDE_ne_fabrique_pas_de_verdict():
    """Un source qui ne parse pas est ignoré, pas compté comme propre : le cliquet ne doit pas
    afficher un vert qu'il n'a pas mesuré."""
    assert scan_literals([("tools/casse.py", "def f( :\n")]) == {}


# --------------------------------------------------------------------------------------------------
# 2. Le VERDICT : bloquer le NOUVEAU, laisser passer le MIGRÉ
# --------------------------------------------------------------------------------------------------

def test_un_NOUVEAU_litteral_dans_un_fichier_deja_connu_est_ATTRAPE():
    base = {"tools/x.py": ["data/hall_of_fame.pkl"]}
    cour = {"tools/x.py": ["data/hall_of_fame.pkl", "data/kuzu_graph.db"]}
    assert nouveaux(base, cour) == [{"chemin": "tools/x.py", "litteral": "data/kuzu_graph.db"}]


def test_un_NOUVEAU_FICHIER_entier_est_ATTRAPE():
    assert nouveaux({}, {"tools/neuf.py": ["data/x.pkl"]}) == \
           [{"chemin": "tools/neuf.py", "litteral": "data/x.pkl"}]


def test_un_litteral_MIGRE_ne_declenche_RIEN():
    """LA branche négative qui donne son sens au cliquet : migrer un site vers `src/paths.py` fait
    DISPARAÎTRE son littéral. Si cela criait, le cliquet travaillerait contre son propre but."""
    base = {"tools/x.py": ["data/hall_of_fame.pkl", "data/kuzu_graph.db"]}
    assert nouveaux(base, {"tools/x.py": ["data/kuzu_graph.db"]}) == []
    assert nouveaux(base, {}) == []


def test_un_etat_INCHANGE_ne_rend_RIEN():
    """No-op EXACT : sans ce cas, un cliquet qui crierait toujours passerait tous les précédents."""
    etat = {"tools/x.py": ["data/a.pkl"], "src/y.py": ["results/b.json"]}
    assert nouveaux(etat, dict(etat)) == []


# --------------------------------------------------------------------------------------------------
# 3. Garde de la garde : la CLI, le périmètre, et la réalité de la dette
# --------------------------------------------------------------------------------------------------

def test_le_CLIQUET_sait_SORTIR_EN_ERREUR_et_se_TAIRE(monkeypatch, capsys):
    """Les fonctions pures peuvent être justes pendant que la CLI ne bloque jamais — c'est la forme
    du faux vert mesuré le 2026-09-01 (classe E4 occ. 5)."""
    from tools import check_data_paths as C

    monkeypatch.setattr(C, "scan_literals", lambda *a, **k: {"tools/neuf.py": ["data/neuf.pkl"]})
    monkeypatch.setattr(C, "_load_baseline", lambda: {})
    assert C.main([]) == 1
    sortie = capsys.readouterr().out
    assert "tools/neuf.py" in sortie and "src/paths.py" in sortie

    monkeypatch.setattr(C, "_load_baseline", lambda: {"tools/neuf.py": ["data/neuf.pkl"]})
    assert C.main([]) == 0
    assert "aucun nouveau chemin" in capsys.readouterr().out


def test_le_CLIQUET_restreint_son_blocage_avec_only(monkeypatch):
    """L'arbre est PARTAGÉ entre sessions : un littéral écrit par une AUTRE session ne doit pas
    bloquer mon commit (même principe que les portes 1, 2, 10 et 11 du hook)."""
    from tools import check_data_paths as C

    monkeypatch.setattr(C, "scan_literals", lambda *a, **k: {"tools/autrui.py": ["data/x.pkl"]})
    monkeypatch.setattr(C, "_load_baseline", lambda: {})
    assert C.main(["--only", "tools/a_moi.py"]) == 0
    assert C.main(["--only", "tools/autrui.py"]) == 1


def test_le_module_d_indirection_est_HORS_PERIMETRE():
    """`src/paths.py` DOIT contenir les défauts : le juger reviendrait à s'interdire d'avoir un point
    d'indirection. Vérifié sur l'arbre RÉEL, car c'est là que l'exclusion agit."""
    assert "src/paths.py" not in scan_literals()


def test_la_dette_gelee_est_REELLE_et_pas_un_commentaire():
    """Une dette qui ne peut plus être invalidée n'est plus une dette (leçon EVO-009, retiré de la
    dette prereg le 2026-09-02). On vérifie que les fichiers gelés existent ENCORE et portent ENCORE
    au moins un des littéraux gelés."""
    from tools.check_data_paths import _BASELINE

    if not os.path.exists(_BASELINE):
        pytest.skip("baseline pas encore gelée")
    gelés = json.load(open(_BASELINE, encoding="utf-8"))["fichiers"]
    courant = scan_literals()
    perimes = [p for p, lits in gelés.items()
               if p not in courant or not (set(lits) & set(courant[p]))]
    assert not perimes, f"dette périmée (migrée sans re-geler) : {perimes[:5]}"


def test_l_arbre_REEL_est_au_vert_contre_sa_baseline():
    """Garde de la garde, bout en bout : le cliquet doit passer sur l'état committé. S'il échoue,
    c'est qu'un littéral a été ajouté sans passer par `src/paths.py`."""
    from tools.check_data_paths import _load_baseline

    assert nouveaux(_load_baseline(), scan_literals()) == []
