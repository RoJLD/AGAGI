# -*- coding: utf-8 -*-
"""Calibration du cliquet d'ANÉANTISSEMENT — `tools/check_amputation.py` (porte 16).

Les trois occurrences d'E22 sont REJOUÉES telles quelles, et chacune est appariée à son no-op : une
garde qui refuserait TOUT passerait les cas positifs tout en étant inutilisable, et serait désarmée
dans la semaine.
"""
import io
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import check_amputation as A  # noqa: E402

_ROOT = A._ROOT


# ==================================================================================================
# 1. LE COMPTE D'ENTITE — a reponse connue, par famille de fichier
# ==================================================================================================

def test_le_compte_python_est_la_DECLARATION_a_toute_indentation():
    src = ("import os\n\n"
           "def a():\n    pass\n\n"
           "class B:\n"
           "    def c(self):\n        pass\n"
           "    async def d(self):\n        pass\n")
    assert A.compter("x.py", src) == 4, "2 def module + 1 class + 2 methodes = 4 declarations"


def test_le_compte_markdown_est_la_LIGNE_NON_VIDE():
    assert A.compter("x.md", "# titre\n\n\ncorps\n   \n- item\n") == 3


def test_le_compte_json_est_la_TAILLE_du_conteneur():
    assert A.compter("x.json", '{"a": 1, "b": 2}') == 2
    assert A.compter("x.json", "[1, 2, 3]") == 3


def test_un_fichier_INCOMPTABLE_rend_None_et_JAMAIS_zero():
    """⚠️ `None` et 0 sont des affirmations OPPOSEES. Les confondre ferait de chaque binaire, de
    chaque JSON illisible et de chaque `.png` une amputation totale -- un cliquet qui crie sur tout
    est un cliquet qu'on desactive, et c'est la forme (a) du biais du depot appliquee a l'envers."""
    assert A.compter("x.png", "\x00\x01") is None
    assert A.compter("x.json", "{ceci n'est pas du json") is None
    assert A.compter("x.py", "") == 0, "un .py SANS declaration est comptable, et vaut zero"


# ==================================================================================================
# 2. LES TROIS OCCURRENCES D'E22, REJOUEES — et leurs no-op apparies
# ==================================================================================================

def test_CONTRE_EXEMPLE_le_backlog_vide_du_2026_09_09_est_ATTRAPE(tmp_path, monkeypatch):
    """OCCURRENCE (2) : `PRIORITES_ET_DETTES.md`, 2352 lignes -> 0, COMMITTE, douze portes au vert.
    C'est le cas qui a motive la porte -- et qu'aucune des douze n'a vu."""
    cible = tmp_path / "PRIORITES_ET_DETTES.md"
    cible.write_text("", encoding="utf-8")
    monkeypatch.setattr(A, "_ROOT", str(tmp_path))
    monkeypatch.setattr(A, "_version_head", lambda c: "## P1\ntexte\n" * 1176)
    pertes, _hors, examines = A.etat(["PRIORITES_ET_DETTES.md"])
    assert examines == 1
    assert [p["genre"] for p in pertes] == ["aneantissement"], pertes
    assert A.bloquantes(pertes), "l'aneantissement doit BLOQUER"


def test_le_backlog_INTACT_ne_declenche_RIEN(tmp_path, monkeypatch):
    """NO-OP EXACT, apparie au precedent : meme fichier, meme chemin de code, contenu preserve."""
    contenu = "## P1\ntexte\n" * 1176
    cible = tmp_path / "PRIORITES_ET_DETTES.md"
    cible.write_text(contenu, encoding="utf-8")
    monkeypatch.setattr(A, "_ROOT", str(tmp_path))
    monkeypatch.setattr(A, "_version_head", lambda c: contenu)
    pertes, _hors, examines = A.etat(["PRIORITES_ET_DETTES.md"])
    assert examines == 1 and pertes == []


def test_CONTRE_EXEMPLE_la_perte_de_QUATRE_tests_est_SIGNALEE_sans_bloquer(tmp_path, monkeypatch):
    """OCCURRENCES (1) et (3) : quatre tests effaces, suite plus verte. Ici la porte SIGNALE mais ne
    bloque pas -- c'est la porte 10, qui sait qu'elle compte des TESTS, qui bloque. Deux cliquets, le
    general et le specifique, et le general ne doit pas usurper le verdict du specifique."""
    avant = "".join(f"def test_{i}():\n    assert True\n\n" for i in range(8))
    apres = "".join(f"def test_{i}():\n    assert True\n\n" for i in range(4))
    (tmp_path / "test_x.py").write_text(apres, encoding="utf-8")
    monkeypatch.setattr(A, "_ROOT", str(tmp_path))
    monkeypatch.setattr(A, "_version_head", lambda c: avant)
    pertes, _hors, _ex = A.etat(["test_x.py"])
    assert [(p["genre"], p["avant"], p["apres"]) for p in pertes] == [("baisse", 8, 4)]
    assert not A.bloquantes(pertes), "une baisse PARTIELLE est signalee, jamais bloquante"


def test_une_AUGMENTATION_ne_declenche_RIEN(tmp_path, monkeypatch):
    """La suite croit de facon monotone : un cliquet qui se plaindrait d'un ajout travaillerait
    contre son propre but."""
    (tmp_path / "m.py").write_text("def a():\n    pass\ndef b():\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(A, "_ROOT", str(tmp_path))
    monkeypatch.setattr(A, "_version_head", lambda c: "def a():\n    pass\n")
    pertes, _hors, _ex = A.etat(["m.py"])
    assert pertes == []


def test_un_fichier_NOUVEAU_n_a_pas_d_AVANT_et_ne_declenche_RIEN(tmp_path, monkeypatch):
    """⚠️ Sans ce cas, tout fichier ajoute serait vu comme une chute depuis rien -- ou pire, une
    comparaison contre `None` fabriquerait un verdict."""
    (tmp_path / "neuf.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(A, "_ROOT", str(tmp_path))
    monkeypatch.setattr(A, "_version_head", lambda c: None)
    pertes, _hors, examines = A.etat(["neuf.py"])
    assert pertes == [] and examines == 0


def test_le_HORS_PERIMETRE_est_RAPPORTE_et_jamais_avale(tmp_path, monkeypatch):
    """Une liste blanche qui ne rapporte pas ce qu'elle ecarte transforme son ignorance en succes --
    trois trouvees dans ce depot en deux jours."""
    (tmp_path / "i.png").write_text("nimporte", encoding="utf-8")
    monkeypatch.setattr(A, "_ROOT", str(tmp_path))
    monkeypatch.setattr(A, "_version_head", lambda c: "autre chose")
    pertes, hors, examines = A.etat(["i.png"])
    assert pertes == [] and hors == ["i.png"] and examines == 0


# ==================================================================================================
# 3. LE CLIQUET SAIT SORTIR EN ERREUR — et se taire
# ==================================================================================================

def test_le_CLIQUET_sort_en_ERREUR_sur_un_aneantissement(monkeypatch, capsys):
    monkeypatch.setattr(A, "etat", lambda ch=None: (
        [{"chemin": "a.md", "avant": 2352, "apres": 0, "genre": "aneantissement"}], [], 1))
    assert A.main(["--fichiers", "a.md"]) == 1
    assert "TOTALITE" in capsys.readouterr().out


def test_le_CLIQUET_se_TAIT_sur_une_baisse_mais_l_AFFICHE(monkeypatch, capsys):
    """NO-OP APPARIE : exit 0, et pourtant le chiffre EST imprime. C'est tout l'interet -- le chiffre
    de suppressions sous les yeux au moment du commit est ce qui a revele l'occurrence (2)."""
    monkeypatch.setattr(A, "etat", lambda ch=None: (
        [{"chemin": "a.py", "avant": 8, "apres": 4, "genre": "baisse"}], [], 1))
    assert A.main(["--fichiers", "a.py"]) == 0
    sortie = capsys.readouterr().out
    assert "baisse" in sortie and "8 -> 4" in sortie


def test_le_CLIQUET_est_BRANCHE_sur_le_hook():
    """E10 : une regle executable non branchee est violee. Mesure trois fois dans ce depot."""
    hook = io.open(os.path.join(_ROOT, "tools", "hooks", "pre-commit"), encoding="utf-8").read()
    assert "check_amputation" in hook


def test_l_arbre_REEL_ne_porte_aucun_aneantissement():
    """Ancrage sur le reel : l'index courant doit etre propre. Ce test est le seul qui touche git."""
    pertes, _hors, _ex = A.etat()
    assert A.bloquantes(pertes) == [], A.bloquantes(pertes)
