"""Cliquet : tout appel à `ablation_verdict` doit DÉCLARER une borne (`floor` et/ou `ceiling`).

POURQUOI. `ablation_verdict` est un ratio de médianes. Le dépôt a mesuré ce que produit un ratio non
borné : **tout bras collé à une borne donne mécaniquement ratio ≈ 1.0, donc « X est un leurre »** — un
verdict NUL fabriqué par la borne et non par l'absence d'effet. Trois conclusions gravées en sont
sorties, dont EDR-WARM-002 (« le paysage de fitness est PLAT », réfuté depuis par EDR-WARM-010).

⚠️ La garde EXISTE (`_degeneracy`, armée le 2026-07-21) mais elle ne s'active QUE si l'appelant DÉCLARE
`floor=` / `ceiling=` — parce qu'un plancher n'est pas déductible de deux tableaux. Or au 2026-09-01,
sur les appels du dépôt, plusieurs ne déclaraient AUCUNE borne. C'est la classe **E14** dans sa forme
littérale : une garde armée chez certains appelants et jamais rétro-appliquée aux autres.

CE QUE CE CLIQUET NE FAIT PAS, et pourquoi. Il n'ajoute pas les bornes manquantes. Un `floor` est une
**déclaration scientifique** : `PLANCHER_COG = 9.0` est « mesuré au régime cognitive_demand ». Inventer
un plancher pour un régime qu'on n'a pas mesuré fabriquerait le genre de chiffre que ce dépôt traque.
La dette est donc GELÉE avec ses fichiers nommés, et le cliquet refuse tout NOUVEL appel non borné.
"""
import ast
import io
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_SCAN = (os.path.join(_ROOT, "tools"), os.path.join(_ROOT, "src"))

# Dette LÉGATAIRE gelée au 2026-09-01 : appels sans AUCUNE borne déclarée. Chaque ligne attend qu'un
# plancher soit MESURÉ pour son régime — pas inventé. Retirer une entrée quand c'est fait.
# 4 fichiers RESORBES le 2026-09-02 : planchers MESURES (30.0 regime partage, 54.0 composition,
# mesureur calibre sur forme close E0/(metab-body_gain)=30 exact) et declares aux appels, avec bascule
# de la consommation sur v["verdict"] -- sans quoi floor= etait inerte.
# DETTE VIDEE le 2026-09-02 : les 9 appels des 7 fichiers portent desormais une borne MESUREE
# (planchers mini-mondes par forme close/enumeration ; table PLANCHER_NOPERC par monde sous bail,
# regime-gate _floor_for -- jamais un plancher d'un autre regime, E8). Le cliquet est STRICT :
# tout nouvel appel non borne bloque.
_SANS_BORNE_LEGATAIRE = frozenset()

_BORNES = {"floor", "ceiling"}


def _appels_sans_borne():
    """[(fichier, ligne)] pour chaque appel à `ablation_verdict` sans `floor=` ni `ceiling=`."""
    trouve = []
    for racine in _SCAN:
        for dossier, _, fichiers in os.walk(racine):
            if "__pycache__" in dossier:
                continue
            for f in sorted(fichiers):
                if not f.endswith(".py"):
                    continue
                chemin = os.path.join(dossier, f)
                try:
                    arbre = ast.parse(io.open(chemin, encoding="utf-8", errors="ignore").read())
                except SyntaxError:
                    continue
                rel = os.path.relpath(chemin, _ROOT).replace(os.sep, "/")
                for n in ast.walk(arbre):
                    if not isinstance(n, ast.Call):
                        continue
                    nom = getattr(n.func, "attr", None) or getattr(n.func, "id", None)
                    if nom != "ablation_verdict":
                        continue
                    if not any(k.arg in _BORNES for k in n.keywords):
                        trouve.append((rel, n.lineno))
    return trouve


def test_no_NEW_unbounded_ablation_verdict_call():
    """⚠️ LE cliquet. Un nouvel appel non borné peut fabriquer un verdict NUL — c'est déjà arrivé, et
    la conclusion a tenu jusqu'à sa réfutation par un autre record."""
    nouveaux = [(f, l) for f, l in _appels_sans_borne() if f not in _SANS_BORNE_LEGATAIRE]
    assert not nouveaux, (
        "appel(s) à `ablation_verdict` sans `floor=` ni `ceiling=` :\n"
        + "\n".join(f"    {f}:{l}" for f, l in nouveaux)
        + "\n  Déclarer la borne MESURÉE du régime (cf. PLANCHER_COG = 9.0, mesuré à EDR-WARM-010).\n"
          "  Ne pas l'inventer : sans mesure, ouvrir une entrée de dette plutôt qu'un chiffre faux.")


def test_the_frozen_debt_is_STILL_REAL():
    """L'inverse du cliquet : si un fichier gelé a reçu sa borne, il faut le RETIRER de la dette.
    Une dette qui ne peut plus être invalidée n'est plus une dette, c'est un commentaire."""
    sans_borne = {f for f, _ in _appels_sans_borne()}
    resorbees = sorted(_SANS_BORNE_LEGATAIRE - sans_borne)
    assert not resorbees, (
        f"{resorbees} ne contient plus d'appel non borné -> le retirer de `_SANS_BORNE_LEGATAIRE` "
        f"et vérifier quelle borne y a été déclarée.")


def test_the_detector_SEES_an_unbounded_call(tmp_path, monkeypatch):
    """⚠️ Garde de la garde. Un détecteur cassé rendrait une liste vide et le cliquet passerait au vert
    en ne vérifiant plus rien (classe E4)."""
    d = tmp_path / "tools"
    d.mkdir()
    (d / "faux.py").write_text("v = ablation_verdict(a, b)\n", encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "_ROOT", str(tmp_path))
    monkeypatch.setattr(sys.modules[__name__], "_SCAN", (str(d),))
    assert any(f.endswith("faux.py") for f, _ in _appels_sans_borne())


def test_the_detector_SPARES_a_bounded_call(tmp_path, monkeypatch):
    """⚠️ SPÉCIFICITÉ : un appel qui DÉCLARE sa borne ne doit pas être signalé, sinon le cliquet
    reproche l'exact comportement qu'il demande."""
    d = tmp_path / "tools"
    d.mkdir()
    (d / "bon.py").write_text("v = ablation_verdict(a, b, floor=9.0)\n"
                              "w = ablation_verdict(a, b, ceiling=400.0)\n", encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "_ROOT", str(tmp_path))
    monkeypatch.setattr(sys.modules[__name__], "_SCAN", (str(d),))
    assert _appels_sans_borne() == []
