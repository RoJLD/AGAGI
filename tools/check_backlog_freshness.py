"""Cliquet de FRAÎCHEUR du backlog — un backlog qui ment sur son état fait refaire ce qui est fait.

Problème visé, mesuré le 2026-09-01. `docs/roadmap/PRIORITES_ET_DETTES.md` est le document que CLAUDE.md
désigne comme « à consulter avant de choisir quoi faire ». Un audit systématique y a trouvé **douze**
péremptions, dont :

* une direction présentée comme « à faire » que le dépôt avait déjà tranchée (D1 = EDR-EVO-019) — trouvée
  en allant y chercher quoi faire, c'est-à-dire au pire moment ;
* une piste listée « reste ouvert » que [[EDR-EVO-010]] a RÉFUTÉE, en contradiction avec le bloc de
  clôture situé 65 lignes plus haut dans le même fichier ;
* une classe d'erreur déclarée « la SEULE sans aucune garde » alors qu'elle est close depuis un mois ;
* un chiffre-phare faux d'un facteur 3 (« 71 instruments, 1 calibré » contre 101 / 32) ;
* quatre numéros de tâche (P2.0-bis, P2.1, P2.2, P2.3) présents DEUX fois avec des contenus différents.

Le coût de cette dette n'est pas cosmétique : c'est du temps de calcul dépensé à relancer une expérience
déjà faite, exactement ce que le protocole de pré-vol cherche à éviter.

CE QUE CE CLIQUET VÉRIFIE — trois propriétés DÉCIDABLES, et rien d'autre :

1. **Liens morts** — un `[[EDR-XXX]]` cité dans le backlog dont aucun record ne porte l'id.
2. **Numéros dupliqués** — un même `P<n>.<m>` en tête de deux entrées : l'une des deux est forcément
   périmée, et rien ne dit laquelle.
3. **Chemins morts** — un `chemin/fichier.py` cité entre backticks qui n'existe plus.

CE QU'IL NE VÉRIFIE PAS. Il ne juge pas si une entrée « ouverte » a été tranchée par un record : ça
demande de lire et de comprendre les deux, et aucune heuristique lexicale ne le fait honnêtement. C'est
le travail d'un audit — ce cliquet attrape seulement la dérive MÉCANIQUE, celle qui s'accumule sans que
personne décide rien.

RÈGLE À CLIQUET, comme `check_record_links.py` : la dette LÉGATAIRE est gelée, aucune NOUVELLE.

Usage :
  python tools/check_backlog_freshness.py                    # cliquet : exit 1 sur toute NOUVELLE péremption
  python tools/check_backlog_freshness.py --report           # état complet, exit 0
  python tools/check_backlog_freshness.py --update-baseline  # gèle l'état courant
"""
import argparse
import collections
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKLOG = os.path.join(_ROOT, "docs", "roadmap", "PRIORITES_ET_DETTES.md")
_BASELINE = os.path.join(_ROOT, "tools", "backlog_freshness_baseline.json")
_DOCS = os.path.join(_ROOT, "docs")

_WIKILINK = re.compile(r"\[\[([A-Za-z0-9_.\-]+)\]\]")
_TASKNUM = re.compile(r"^\*\*(P\d+\.\d+(?:-bis)?)\b", re.M)
_BACKTICK_PATH = re.compile(r"`([\w][\w./-]*\.(?:py|md|json|yml|yaml))`")


def _known_ids():
    """Tous les identifiants de records déclarés en frontmatter, plus les noms de fichiers."""
    ids = set()
    for root, _, files in os.walk(_DOCS):
        for f in files:
            if not f.endswith(".md"):
                continue
            ids.add(f[:-3])
            try:
                head = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read(2000)
            except OSError:
                continue
            m = re.search(r"^id:\s*(\S+)", head, re.M)
            if m:
                ids.add(m.group(1).strip())
            # `EVO-021_Titre.md` porte l'id `EDR-EVO-021` : indexer aussi le préfixe du nom de fichier.
            ids.add(f.split("_")[0])
    return ids


def scan():
    """Renvoie {clef: description} pour chaque péremption MÉCANIQUE trouvée."""
    txt = open(_BACKLOG, encoding="utf-8").read()
    trouve = {}

    connus = _known_ids()
    for cible in sorted(set(_WIKILINK.findall(txt))):
        # ⚠️ Deux espaces de noms cohabitent dans ces `[[...]]` : les RECORDS (`EDR-`, `REF-`, `SDR-`,
        # `ADR-`, majuscules) et les slugs de MÉMOIRE de session (kebab minuscule), qui vivent hors du
        # dépôt. Ne juger que les premiers : signaler les seconds serait exiger qu'un fichier existe
        # là où la convention dit qu'il n'existe pas.
        if not re.match(r"^(EDR|REF|SDR|ADR)-", cible):
            continue
        court = cible[4:] if cible.startswith("EDR-") else cible
        if cible in connus or court in connus:
            continue
        trouve[f"lien-mort:{cible}"] = (
            f"le backlog cite [[{cible}]] mais aucun record ne porte cet identifiant")

    compte = collections.Counter(_TASKNUM.findall(txt))
    for num, n in sorted(compte.items()):
        if n > 1:
            trouve[f"numero-double:{num}"] = (
                f"{num} apparaît {n} fois en tête d'entrée : l'une des versions est périmée et rien "
                f"ne dit laquelle")

    for chemin in sorted(set(_BACKTICK_PATH.findall(txt))):
        if "/" not in chemin:
            continue                      # nom nu : trop ambigu pour conclure
        if not os.path.exists(os.path.join(_ROOT, chemin)):
            trouve[f"chemin-mort:{chemin}"] = (
                f"le backlog cite `{chemin}`, qui n'existe plus")

    return trouve


def _load_baseline():
    if not os.path.exists(_BASELINE):
        return {}
    with open(_BASELINE, encoding="utf-8") as f:
        return json.load(f).get("legataires", {})


def main():
    ap = argparse.ArgumentParser(description="Cliquet de fraicheur du backlog.")
    ap.add_argument("--report", action="store_true", help="état complet, exit 0")
    ap.add_argument("--update-baseline", action="store_true", help="gèle l'état courant")
    args = ap.parse_args()

    trouve = scan()

    if args.update_baseline:
        with open(_BASELINE, "w", encoding="utf-8") as f:
            json.dump({
                "_comment": ("Peremptions MECANIQUES legataires du backlog, gelees. Le cliquet refuse "
                             "toute NOUVELLE entree. Retirer une ligne quand elle est corrigee -- "
                             "jamais en ajouter pour faire passer le hook."),
                "legataires": trouve,
            }, f, ensure_ascii=False, indent=2, sort_keys=True)
        print(f"baseline gelé : {len(trouve)} péremption(s) mécanique(s) légataire(s)")
        return 0

    base = _load_baseline()
    nouvelles = {k: v for k, v in trouve.items() if k not in base}
    resorbees = [k for k in base if k not in trouve]

    if args.report:
        print(f"péremptions mécaniques : {len(trouve)} "
              f"(dont {len(base)} légataires, {len(nouvelles)} NOUVELLES)")
        for k, v in sorted(trouve.items()):
            print(f"  [{'LÉGATAIRE' if k in base else 'NOUVELLE '}] {v}")
        if resorbees:
            print(f"\n  résorbées : {len(resorbees)} -> `--update-baseline` pour resserrer")
        return 0

    if nouvelles:
        print("ÉCHEC : le backlog a de NOUVELLES péremptions mécaniques.\n")
        for k, v in sorted(nouvelles.items()):
            print(f"  {v}")
        print("\nUn backlog qui ment sur son état fait relancer ce qui est déjà tranché.")
        return 1

    print(f"OK : {len(trouve)} péremption(s) mécanique(s), toutes légataires (baseline). Aucune nouvelle.")
    if resorbees:
        print(f"  ({len(resorbees)} résorbée(s) — `--update-baseline` pour resserrer le cliquet)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
