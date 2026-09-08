# -*- coding: utf-8 -*-
"""Calibration du cliquet de RECENSEMENT DES TESTS (`tools/check_test_census.py`, porte 10).

⚠️ Un cliquet doit pouvoir ÉCHOUER, et se calibrer comme un instrument (CLAUDE.md) : les deux cliquets
livrés le 2026-09-01 ont rendu 5 puis 2 faux positifs avant d'être corrigés. Ici, le CONTRE-EXEMPLE
GELÉ est le défaut RÉEL qui a motivé la garde — la réécriture regex du 2026-09-07, rejouée telle
quelle sur un fichier jouet : elle supprime quatre tests sans lever, et le cliquet doit le voir.

Les branches NÉGATIVES sont exigées au même titre (classe E1) : un cliquet qui bloquerait aussi sur
une AUGMENTATION ou sur un fichier NOUVEAU serait inutilisable, et un cliquet qui ne bloque jamais est
indiscernable d'une garde absente.
"""
import re

from tools.check_test_census import census, count_tests, regressions

# --------------------------------------------------------------------------------------------------
# 1. count_tests -- réponses connues, y compris les formes qui font rater un comptage naïf
# --------------------------------------------------------------------------------------------------

def test_count_tests_reponse_connue_sur_les_quatre_formes():
    src = ("import pytest\n\n"
           "def test_un(): pass\n"
           "async def test_deux(): pass\n"
           "class TestTrois:\n"
           "    def test_methode(self): pass\n"
           "def pas_un_test(): pass\n"
           "# def test_en_commentaire(): pass\n")
    # 1 def + 1 async def + 1 methode = 3. NI `pas_un_test` NI le `def` COMMENTE ne comptent
    # (le motif exige `def test_` en tete de ligne, aux blancs pres).
    # ⚠️ Ce compte a ete pose DEUX FOIS de tete (5, puis 4) avant d'etre MESURE -- classe E8,
    # dans le test meme qui existe pour ne pas croire un compte sur parole.
    assert count_tests(src) == 3


def test_count_tests_DEDOUBLONNE_les_homonymes():
    """Deux `def` homonymes ne font qu'UN test exécuté (le second écrase le premier). Les compter
    deux fois laisserait passer une suppression compensée par un doublon -- le cliquet resterait
    vert alors qu'une vérification a disparu."""
    assert count_tests("def test_a(): pass\ndef test_a(): pass\ndef test_b(): pass\n") == 2


def test_count_tests_sur_un_fichier_SANS_test_rend_zero():
    """Branche négative : sans elle, un comptage qui rendrait toujours >= 1 passerait ces tests."""
    assert count_tests("def helper(): pass\nTESTS = ['test_faux']\n") == 0


# --------------------------------------------------------------------------------------------------
# 2. regressions -- le VERDICT du cliquet, ses deux genres de perte et ses trois non-pertes
# --------------------------------------------------------------------------------------------------

def test_regressions_voit_un_fichier_DISPARU():
    p = regressions({"tests/a.py": 3}, {})
    assert [(x["genre"], x["chemin"], x["avant"], x["apres"]) for x in p] == \
           [("fichier_disparu", "tests/a.py", 3, None)]


def test_regressions_voit_des_tests_SUPPRIMES():
    p = regressions({"tests/a.py": 10}, {"tests/a.py": 8})
    assert [(x["genre"], x["avant"], x["apres"]) for x in p] == [("tests_supprimes", 10, 8)]


def test_regressions_LAISSE_PASSER_une_augmentation():
    """Branche négative n°1 : la suite croît de façon monotone -- bloquer ici rendrait le cliquet
    inutilisable, et il serait désarmé par la première personne qui ajoute un test."""
    assert regressions({"tests/a.py": 3}, {"tests/a.py": 9}) == []


def test_regressions_LAISSE_PASSER_un_fichier_NOUVEAU():
    """Branche négative n°2 : un fichier absent de la baseline n'est pas une perte."""
    assert regressions({"tests/a.py": 3}, {"tests/a.py": 3, "tests/neuf.py": 40}) == []


def test_regressions_sur_un_arbre_INCHANGE_ne_rend_RIEN():
    """Spécificité (no-op EXACT) : sans ce cas, un cliquet qui crierait toujours passerait les autres."""
    etat = {"tests/a.py": 3, "tests/b.py": 7}
    assert regressions(etat, dict(etat)) == []


# --------------------------------------------------------------------------------------------------
# 3. CONTRE-EXEMPLE GELÉ -- le défaut RÉEL du 2026-09-07, rejoué
# --------------------------------------------------------------------------------------------------

_FICHIER_JOUET = '''import pytest


def test_a(): assert True


@pytest.mark.xfail(strict=True, reason=(
    "defaut 1"))
def test_b(): assert False


@pytest.mark.xfail(strict=True, reason=(
    "defaut 2"))
def test_c(): assert False


@pytest.mark.xfail(strict=True, reason=(
    "defaut 3"))
def test_cible(): assert False
'''


def test_CONTRE_EXEMPLE_la_reecriture_regex_du_2026_09_07_est_ATTRAPEE():
    """RÉPONSE CONNUE. La réécriture visait à retirer le SEUL décorateur de `test_cible`. Ancrée sur
    `@pytest.mark.xfail` sans ancrage de DÉBUT, `re.search` démarre au PREMIER décorateur du fichier :
    le non-greedy ne rattrape rien, et tout ce qui sépare les deux est effacé -- `test_b` et `test_c`
    partent avec. Aucune exception n'est levée, et la suite en devient PLUS VERTE (deux xfail de moins).

    Le cliquet doit voir la perte, et la voir comme `tests_supprimes` : 4 -> 2."""
    mutile = re.sub(
        r'@pytest\.mark\.xfail\(strict=True, reason=\((?:.|\n)*?\)\)\n(?=def test_cible\()',
        "", _FICHIER_JOUET)
    # ⚠️ tester `"def test_c"` NU serait un faux négatif : c'est un SOUS-TEXTE de `def test_cible`,
    # qui survit toujours. On teste la parenthèse ouvrante -- le nom complet.
    assert "def test_b(" not in mutile and "def test_c(" not in mutile, (
        "le contre-exemple ne reproduit plus le défaut : il ne prouve donc plus rien")

    avant, apres = count_tests(_FICHIER_JOUET), count_tests(mutile)
    assert (avant, apres) == (4, 2)
    p = regressions({"tests/jouet.py": avant}, {"tests/jouet.py": apres})
    assert len(p) == 1 and p[0]["genre"] == "tests_supprimes" and p[0]["apres"] == 2


def test_CONTRE_EXEMPLE_la_reecriture_ANCREE_ne_declenche_RIEN():
    """Le no-op EXACT du contre-exemple : la MÊME intention, correctement ancrée (le DERNIER décorateur
    avant la cible), ne perd aucun test -- donc le cliquet ne crie pas. Sans ce cas apparié, le test
    précédent ne distinguerait pas « la garde voit la perte » de « la garde crie toujours »."""
    d = re.search(r'^def test_cible\(', _FICHIER_JOUET, re.M)
    deb = [m.start() for m in re.finditer(r'^@pytest\.mark', _FICHIER_JOUET[:d.start()], re.M)][-1]
    ancre = _FICHIER_JOUET[:deb] + _FICHIER_JOUET[d.start():]

    assert "def test_b" in ancre and "def test_c" in ancre
    assert count_tests(ancre) == 4
    assert regressions({"tests/jouet.py": 4}, {"tests/jouet.py": count_tests(ancre)}) == []


# --------------------------------------------------------------------------------------------------
# 4. Garde de la garde -- le recensement porte bien sur l'arbre RÉEL
# --------------------------------------------------------------------------------------------------

def test_census_voit_CE_fichier_et_ses_tests():
    """Périmètre : un cliquet qui recenserait un arbre VIDE passerait tout (classe E4, « vérification
    vide »). On exige qu'il se voie LUI-MÊME, avec le bon compte."""
    c = census()
    moi = "tests/sandbox/test_test_census.py"
    assert moi in c, f"le recensement ne voit pas {moi} : son périmètre est faux"
    assert c[moi] >= 10
    assert sum(c.values()) > 1000, "arbre de tests quasi vide : le périmètre a glissé"


def test_census_IGNORE_les_arbres_de_travail_des_autres_sessions():
    """L'arbre est PARTAGÉ entre sessions (CLAUDE.md) : recenser `.worktrees/` ferait échouer le
    cliquet sur du travail qui n'est pas le nôtre, et une baseline gelée depuis un worktree
    bloquerait tout le monde."""
    assert not [p for p in census() if p.startswith((".worktrees/", ".claude/"))]


def test_le_CLIQUET_lui_meme_sait_SORTIR_EN_ERREUR(monkeypatch, capsys):
    """Garde de la garde, bout en bout : les fonctions pures ci-dessus peuvent être justes pendant que
    la CLI, elle, ne bloque jamais (c'est la forme du faux vert mesuré le 2026-09-01 : une baseline
    lue au mauvais endroit). On gonfle la baseline d'un fichier réel -> `main` doit rendre 1 et NOMMER
    le fichier."""
    from tools import check_test_census as ctc

    reel = "tests/sandbox/test_test_census.py"
    monkeypatch.setattr(ctc, "_load_baseline", lambda: {reel: 9999})
    assert ctc.main([]) == 1
    sortie = capsys.readouterr().out
    assert "tests_supprimes" in sortie and reel in sortie


def test_le_CLIQUET_ne_bloque_PAS_sur_l_arbre_REEL(capsys):
    """Branche négative appariée : sur la baseline gelée du dépôt, le cliquet doit passer. Sans elle,
    un cliquet qui échouerait TOUJOURS satisferait le test précédent."""
    from tools import check_test_census as ctc

    assert ctc.main([]) == 0
    assert "aucun test disparu" in capsys.readouterr().out


def test_le_CLIQUET_restreint_son_BLOCAGE_avec_only(monkeypatch):
    """`--only` : l'arbre est PARTAGÉ entre sessions, une perte dans le travail d'une AUTRE session ne
    doit pas bloquer mon commit (même principe que les portes 1 et 2 du hook). L'état complet reste
    imprimé ; seul le blocage est restreint."""
    from tools import check_test_census as ctc

    autre = "tests/sandbox/test_test_census.py"
    monkeypatch.setattr(ctc, "_load_baseline", lambda: {autre: 9999})
    assert ctc.main(["--only", "tests/sandbox/test_instrument_calibration.py"]) == 0
    assert ctc.main(["--only", autre]) == 1
