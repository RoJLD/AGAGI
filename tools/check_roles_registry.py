"""Porte 21 — registre des rôles : toute ligne de docs/roadmap/ROLES.md porte ses cinq colonnes.

  python tools/check_roles_registry.py            # cliquet : exit 1 si une ligne est creuse
  python tools/check_roles_registry.py --report   # état, exit 0

Un rôle `instancié` sans instrument, contrôle positif, coût, compteurs ou critère de dissolution est une règle
DOCUMENTÉE (classe E10) ; un `candidat` porte au moins son critère de naissance. Pas de baseline : aucune
dette tolérée, le registre naît complet (spec 2026-09-16 §3.6).
"""
import argparse
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REGISTRE = os.path.join(_ROOT, "docs", "roadmap", "ROLES.md")
_ROW = re.compile(r"^\|\s*\*\*([^*|]+)\*\*\s*\|(.*)$")
COLONNES = ("Rôle", "Statut", "Instrument", "Contrôle positif", "Coût mesuré", "Compteurs", "Dissolution / naissance")
STATUTS = ("instancié", "candidat", "dissous")
_VIDE = ("", "—", "-")


def _est_separateur(cellules):
    """La ligne `| --- | --- | ... |` sous l'en-tête markdown : chaque cellule faite de tirets, et
    rien d'autre."""
    return bool(cellules) and all(cel and set(cel) == {"-"} for cel in cellules)


def lignes(txt):
    out = []
    for i, ligne in enumerate(txt.splitlines(), start=1):
        s = ligne.strip()
        m = _ROW.match(s)
        if m:
            cellules = [c.strip() for c in s.strip("|").split(" | ")]
            out.append({"role": m.group(1).strip(), "statut": cellules[1].strip() if len(cellules) > 1 else "",
                        "cellules": cellules, "ligne": i})
            continue
        if not s.startswith("|"):
            continue
        cellules = [c.strip() for c in s.strip("|").split(" | ")]
        premiere = cellules[0] if cellules else ""
        if premiere == COLONNES[0] or _est_separateur(cellules):
            continue  # en-tête ou ligne de séparation markdown : pas une ligne de rôle
        # ⚠️ Une ligne de tableau qui n'est ni l'en-tête, ni le séparateur, ni un `| **Nom** | …` ne
        # doit PAS disparaître en silence (elle passait inaperçue avant ce correctif — E10 : ni
        # vérifiée, ni comptée). Un nom qui n'est pas en GRAS n'est pas un rôle déclaré.
        out.append({"role": "?", "statut": "non_reconnu", "cellules": cellules, "ligne": i})
    return out


def defauts(L):
    out = []
    for l in L:
        c = l["cellules"]
        if l["statut"] == "non_reconnu":
            out.append({"role": l["role"], "ligne": l["ligne"],
                        "raison": "ligne de tableau non reconnue (nom en gras attendu)"})
            continue
        if len(c) != len(COLONNES):
            out.append({"role": l["role"], "ligne": l["ligne"], "raison": f"{len(c)} cellules au lieu de {len(COLONNES)}"})
            continue
        if l["statut"] not in STATUTS:
            out.append({"role": l["role"], "ligne": l["ligne"], "raison": f"statut {l['statut']!r} hors vocabulaire {STATUTS}"})
            continue
        if l["statut"] == "instancié":
            creuses = [COLONNES[i] for i in range(2, 7) if c[i] in _VIDE]
            if creuses:
                out.append({"role": l["role"], "ligne": l["ligne"], "raison": "colonnes creuses : " + ", ".join(creuses)})
        elif l["statut"] == "candidat" and c[6] in _VIDE:
            out.append({"role": l["role"], "ligne": l["ligne"], "raison": "candidat sans critère de naissance (7e colonne)"})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true", help="état complet, exit 0")
    args = ap.parse_args(argv)
    with open(_REGISTRE, encoding="utf-8") as fh:
        L = lignes(fh.read())
    d = defauts(L)
    print(f"rôles : {len(L)} | instanciés : {sum(1 for l in L if l['statut'] == 'instancié')} | "
          f"candidats : {sum(1 for l in L if l['statut'] == 'candidat')} | lignes creuses : {len(d)}")
    for x in d:
        print(f"  [CREUSE] {x['role']} (l.{x['ligne']}) : {x['raison']}")
    if args.report:
        return 0
    if d:
        print("Un rôle sans ses cinq colonnes est une règle documentée (E10), pas un rôle. Compléter la ligne.")
        return 1
    print("OK : toutes les lignes de ROLES.md portent leurs cinq colonnes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
