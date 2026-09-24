"""Balayeur de BACKTICKS NUS dans les littéraux gabarits d'un script de workflow.

⚠️ **Pourquoi cette garde existe, et pourquoi `node --check` ne suffit pas.** Le 2026-09-24, le
harnais a REFUSÉ de charger `.claude/workflows/refutateur.js` :

    Invalid workflow script: Script parse error: Unexpected token (116:62)
    ere ligne, TELLE QUELLE, dans le champ `plancher`. Un score sans son plancher es
                                            ^

Un backtick destiné à être de la PROSE, à l'intérieur d'un littéral gabarit : il ferme le gabarit au
lieu d'être du texte. Mesuré, avec contrôle positif validé :

    casse.js       -> node --check exit 1   (fichier volontairement invalide : la sonde fonctionne)
    sain.js        -> exit 0
    refutateur.js  -> exit 0                 <-- node le déclare SAIN, le harnais le REFUSE

Une garde « lance `node --check` » serait donc **décorative** — classe E4, une vérification qui ne
peut pas échouer sur le défaut qu'elle vise. C'est la même famille que la règle du dépôt « pas de
backtick dans une chaîne qui traverse un interpréteur », payée trois fois : *le canal transforme la
chaîne*, et ici le canal est le parseur du harnais.

**La propriété réellement décidable** est locale et syntaxique : dans un littéral gabarit, tout
backtick non échappé FERME le gabarit. On la détecte par deux signatures, chacune suffisante :

1. **en texte de gabarit**, un backtick suivi d'un caractère de mot : un vrai backtick de fermeture
   est suivi de `)`, `,`, `;`, `.`, `}` ou d'une fin de ligne — jamais d'une lettre. C'est la
   première moitié de `` `plancher` `` ;
2. **hors gabarit**, un backtick précédé d'un caractère de mot, de `)` ou de `]` : en JavaScript
   c'est un *tagged template*, que ces scripts n'emploient jamais. C'est la seconde moitié.

⚠️ **CE QUE CETTE GARDE NE VOIT PAS.** Elle vérifie une propriété **syntaxique locale**, jamais que le
harnais ACCEPTERA le script : les deux parseurs diffèrent — `node --check` accepte le fichier que le
harnais refuse, et rien ne garantit l'inverse. Un script qui passe cette garde peut donc encore être
refusé au chargement. Elle ne lit pas non plus les *regex literals* comme tels (aucun n'en contient
dans ces scripts), et ne dit rien des backticks présents dans les fichiers que les prompts citent.

Usage :
    python tools/workflow_lint.py <fichier.js> [...]      # exit 1 si un backtick nu est trouvé
"""
import argparse
import os
import sys

_MOT = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_$"


def backticks_nus(source):
    """[(ligne, colonne, signature, extrait)] — les backticks qui ne délimitent pas ce qu'on croit.

    Ligne et colonne sont 1-indexées, comme les rapporte le harnais.
    """
    trouves = []
    i, n = 0, len(source)
    ligne, colonne = 1, 1
    # états : "code" (hors gabarit) · "gabarit" (texte) · profondeur des `${ }` imbriqués
    etat, piles = "code", []

    def avance(k=1):
        nonlocal i, ligne, colonne
        for _ in range(k):
            if i < n and source[i] == "\n":
                ligne += 1
                colonne = 1
            else:
                colonne += 1
            i += 1

    while i < n:
        c = source[i]
        suivant = source[i + 1] if i + 1 < n else ""
        if etat == "code":
            if c == "/" and suivant == "/":
                while i < n and source[i] != "\n":
                    avance()
                continue
            if c == "/" and suivant == "*":
                avance(2)
                while i < n and not (source[i] == "*" and source[i + 1: i + 2] == "/"):
                    avance()
                avance(2)
                continue
            if c in "'\"":
                fermeture = c
                avance()
                while i < n and source[i] != fermeture:
                    avance(2 if source[i] == "\\" else 1)
                avance()
                continue
            if c == "`":
                precedent = source[i - 1] if i > 0 else ""
                if precedent in _MOT or precedent in ")]":
                    trouves.append((ligne, colonne, "tagged-template",
                                    _extrait(source, i)))
                piles.append(0)
                etat = "gabarit"
                avance()
                continue
            if c == "}" and piles and etat == "code":
                # retour dans le gabarit qui contenait ce `${ }`
                if piles[-1] == 0:
                    etat = "gabarit"
                    avance()
                    continue
                piles[-1] -= 1
            elif c == "{" and piles:
                piles[-1] += 1
            avance()
            continue
        # etat == "gabarit"
        if c == "\\":
            avance(2)
            continue
        if c == "$" and suivant == "{":
            etat = "code"
            avance(2)
            continue
        if c == "`":
            if suivant in _MOT:
                trouves.append((ligne, colonne, "backtick-en-texte", _extrait(source, i)))
            if piles:
                piles.pop()
            etat = "code"
            avance()
            continue
        avance()
    if etat == "gabarit":
        trouves.append((ligne, colonne, "gabarit-non-ferme", "(fin de fichier)"))
    return trouves


def _extrait(source, i, largeur=38):
    debut = max(0, i - largeur)
    fin = min(len(source), i + largeur)
    return source[debut:fin].replace("\n", " ")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("fichiers", nargs="+")
    args = ap.parse_args(argv)
    total = 0
    for chemin in args.fichiers:
        with open(chemin, encoding="utf-8") as fh:
            source = fh.read()
        for ligne, colonne, signature, extrait in backticks_nus(source):
            total += 1
            print(f"{os.path.basename(chemin)}:{ligne}:{colonne}  [{signature}]")
            print(f"    …{extrait.strip()}…")
    if total:
        print(f"\n{total} backtick(s) NU(S) : le harnais refusera le script. Échapper en \\` .")
        print("⚠️ Cette garde est LOCALE : la passer ne garantit pas que le harnais accepte le script.")
        return 1
    print(f"OK : aucun backtick nu dans {len(args.fichiers)} script(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
