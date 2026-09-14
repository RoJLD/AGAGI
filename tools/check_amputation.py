# -*- coding: utf-8 -*-
"""Cliquet d'ANÉANTISSEMENT — un fichier CONSERVÉ ne peut pas perdre TOUT son contenu en silence.

LA CLASSE VISÉE, E22 : une réécriture programmatique ampute un artefact SANS lever, et le signal
habituel s'améliore. Trois occurrences mesurées, et les trois par des mécanismes DIFFÉRENTS :

  1. (2026-09-07) une regex non ancrée efface QUATRE tests — la suite passe de « 28 passés, 15 xfail »
     à « 32 / 7 », donc PLUS VERTE qu'avant ;
  2. (2026-09-09) `io.open(p, "w").write(io.open(p).read()...)` — Python évalue de GAUCHE à DROITE,
     donc `"w"` TRONQUE avant que le `read()` interne ne lise. `PRIORITES_ET_DETTES.md` passe de
     **2352 lignes à 0**, et le vide est COMMITTÉ. Les douze portes du hook sont passées dessus ;
  3. (2026-09-09, trois heures plus tard) `s = s[:i] + NOUVEAU` — un découpage par INDEX, qui
     respecte pourtant la règle écrite le matin même. Quatre tests disparus, suite VERTE à 77.

Le dépôt a répondu à (1) par la porte 10 (recensement des TESTS) et à (2) par le plancher d'entrées
de la porte 4 (le BACKLOG). Les deux sont excellentes et TOUTES DEUX SPÉCIFIQUES À UN ARTEFACT.
Le même accident sur `tools/ablation.py`, sur un record d'EDR, sur `ci.yml` ou sur une baseline JSON
n'était couvert par RIEN — alors que le mécanisme, lui, est indifférent au fichier qu'il détruit.

CE QUE CE CLIQUET BLOQUE, et c'est étroit À DESSEIN : l'ANÉANTISSEMENT. Un fichier encore présent
dans l'index (statut `M`) dont le COMPTE D'ENTITÉ tombe à ZÉRO alors que `HEAD` en portait. Aucun
commit légitime ne fait ça : vider un fichier qu'on garde n'est pas une opération qu'on veut, et
supprimer un fichier pour de bon se fait avec `git rm` (statut `D`, hors périmètre ici).

CE QU'IL NE BLOQUE PAS, et pourquoi il faut le dire. Une baisse PARTIELLE est SIGNALÉE, jamais
bloquée. Retirer du code mort est un acte légitime et fréquent — sept branches mortes ont été
retirées le 2026-09-09 même — et « un cliquet qui bloque sur l'irréparable ou sur le légitime est un
cliquet qu'on désactive » (doctrine du hook, porte 7). Ce que le signalement apporte est exactement
ce qui a sauvé l'occurrence (2) : le chiffre de suppressions SOUS LES YEUX au moment du commit, sans
avoir à y penser. L'amputation partielle reste couverte, elle, par les cliquets d'entité DÉDIÉS
(porte 10 pour les tests, porte 4 pour le backlog), qui savent ce qu'ils comptent.

LE COMPTE D'ENTITÉ, et pas la taille. La leçon de l'occurrence (3) est précisément là : un découpage
par index peut retirer quatre tests sans changer notablement la TAILLE. On compte donc des entités,
par famille de fichier, et le compte d'AVANT est pris HORS de l'artefact modifié (`git show HEAD:`).

⚠️ Un fichier dont l'entité n'est pas comptable est RAPPORTÉ hors périmètre, jamais avalé : une liste
blanche silencieuse transforme son ignorance en succès (trois trouvées dans ce dépôt en deux jours).

Usage :
  python tools/check_amputation.py                      # sur l'INDEX (fichiers stagés M)
  python tools/check_amputation.py --fichiers a.py b.md # restreint (usage du hook)
  python tools/check_amputation.py --report             # état complet, exit 0
"""
import argparse
import json
import os
import re
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# `def foo(` / `class Foo` — la déclaration, à n'importe quelle indentation (méthodes comprises).
_DECL_PY = re.compile(r"^[ \t]*(?:async[ \t]+)?(?:def|class)[ \t]+\w+", re.M)

_TEXTE = (".md", ".yml", ".yaml", ".txt", ".sh", ".cfg", ".ini", ".toml")


def compter(chemin, src):
    """Compte d'ENTITÉ d'une source, ou `None` si le fichier n'est pas comptable.

    ⚠️ `None` et non 0 : « je ne sais pas compter ce fichier » et « ce fichier est vide » sont deux
    affirmations opposées, et les confondre ferait de chaque binaire une amputation."""
    ext = os.path.splitext(chemin)[1].lower()
    if ext == ".py":
        return len(_DECL_PY.findall(src))
    if ext == ".json":
        try:
            charge = json.loads(src)
        except (ValueError, TypeError):
            return None
        return len(charge) if isinstance(charge, (dict, list)) else None
    if ext in _TEXTE:
        return sum(1 for ligne in src.splitlines() if ligne.strip())
    return None


def _version_head(chemin):
    """Contenu du fichier dans HEAD, ou `None` s'il n'y est pas (fichier NOUVEAU : rien à comparer)."""
    p = subprocess.run(["git", "show", f"HEAD:{chemin}"], cwd=_ROOT, capture_output=True,
                       encoding="utf-8", errors="replace")
    return p.stdout if p.returncode == 0 else None


def _stages():
    """Chemins MODIFIÉS dans l'index. `A` est exclu (rien à comparer), `D` aussi : supprimer un
    fichier pour de bon est un acte EXPLICITE et lisible en revue, pas une amputation silencieuse."""
    p = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=M"],
                       cwd=_ROOT, capture_output=True, encoding="utf-8", errors="replace")
    return [c for c in p.stdout.splitlines() if c.strip()]


def etat(chemins=None):
    """-> (pertes, hors_perimetre, n_examines).

    `pertes` = [{chemin, avant, apres, genre}] avec `genre` dans {`aneantissement`, `baisse`}."""
    cibles = list(chemins) if chemins is not None else _stages()
    pertes, hors, examines = [], [], 0
    for rel in cibles:
        rel = rel.replace("\\", "/")
        plein = os.path.join(_ROOT, rel)
        if not os.path.isfile(plein):
            continue
        avant_src = _version_head(rel)
        if avant_src is None:
            continue                      # nouveau fichier : aucun « avant » n'existe
        try:
            with open(plein, encoding="utf-8") as f:
                apres_src = f.read()
        except (OSError, UnicodeDecodeError):
            hors.append(rel)
            continue
        avant, apres = compter(rel, avant_src), compter(rel, apres_src)
        if avant is None or apres is None:
            hors.append(rel)
            continue
        examines += 1
        if avant > 0 and apres == 0:
            pertes.append({"chemin": rel, "avant": avant, "apres": apres, "genre": "aneantissement"})
        elif apres < avant:
            pertes.append({"chemin": rel, "avant": avant, "apres": apres, "genre": "baisse"})
    return pertes, hors, examines


def bloquantes(pertes):
    """VERDICT du cliquet : les pertes qui BLOQUENT, jamais un booléen. Seul l'anéantissement bloque."""
    return [p for p in pertes if p["genre"] == "aneantissement"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fichiers", nargs="*", default=None, help="chemins à examiner (défaut : l'index)")
    ap.add_argument("--report", action="store_true", help="état complet, exit 0")
    args = ap.parse_args(argv)

    pertes, hors, examines = etat(args.fichiers)
    dures = bloquantes(pertes)
    douces = [p for p in pertes if p["genre"] == "baisse"]

    if args.report:
        print(f"amputation : {examines} fichier(s) examine(s), {len(hors)} hors perimetre (rapportes), "
              f"{len(dures)} aneantissement(s), {len(douces)} baisse(s)")
        for p in pertes:
            print(f"  [{p['genre']:15s}] {p['chemin']} : {p['avant']} -> {p['apres']} entites")
        if hors:
            print(f"  hors perimetre : {', '.join(hors[:8])}{' ...' if len(hors) > 8 else ''}")
        return 0

    # ⚠️ SIGNALEMENT D'ABORD, y compris quand rien ne bloque : c'est le chiffre sous les yeux au
    # moment du commit qui a sauve l'occurrence (2) d'E22, lu par reflexe dans la sortie de git.
    for p in douces:
        print(f"  (baisse) {p['chemin']} : {p['avant']} -> {p['apres']} entites "
              f"(-{p['avant'] - p['apres']}) — legitime si voulu, VERIFIER si ce n'est pas voulu")

    if dures:
        print("\nECHEC : un fichier CONSERVE a perdu la TOTALITE de son contenu.\n")
        for p in dures:
            print(f"  {p['chemin']} : {p['avant']} entites dans HEAD -> 0 dans l'arbre")
        print("\nAucun commit legitime ne vide un fichier qu'il garde (E22 : `PRIORITES_ET_DETTES.md`")
        print("est passe de 2352 lignes a 0 et a ete committe, les 12 portes du hook au vert).")
        print("Restaurer depuis HEAD, ou supprimer le fichier POUR DE BON avec `git rm`.")
        return 1

    print(f"OK : {examines} fichier(s) examine(s), aucun aneantissement "
          f"({len(douces)} baisse(s) signalee(s), {len(hors)} hors perimetre).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
