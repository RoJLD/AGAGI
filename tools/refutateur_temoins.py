"""Témoins gelés du Réfutateur : extraction à leur SHA, vérification qu'une revue retrouve le défaut connu.

Le Réfutateur (`docs/REF/REF-REVUE-ADVERSARIALE.md`, `.claude/workflows/refutateur.js`) est un
INSTRUMENT : il produit une affirmation (« ce record a tel défaut », ou « rien à signaler »). Comme tout
instrument du dépôt, il se calibre contre une réponse CONNUE avant d'être cru. Les témoins gelés sont
cette réponse connue :

* trois records dont un défaut RÉEL a été trouvé et gravé APRÈS coup (E8, E26, E19), figés au SHA qui
  porte le défaut NU — pas sa rectification ;
* un record SAIN, qui donne le plancher de fausses critiques. Sans lui, un Réfutateur qui crie sur tout
  passerait les trois premiers et paraîtrait parfait.

Une revue dont la phase témoins échoue est NULLE : rien ne s'écrit dans `docs/reviews/`.

Ce module ne construit AUCUN monde, ne tient AUCUN bail (`kuzu`) et ne lance aucune simulation : il ne
fait que lire l'histoire git et apparier des expressions régulières.

Usage :
    python tools/refutateur_temoins.py --extraire <dir>        # écrit <dir>/<nom>.md pour chaque témoin
    python tools/refutateur_temoins.py --verifier <nom> <fic>  # exit 0 si le défaut est retrouvé, 1 sinon
    python tools/refutateur_temoins.py --lister                # inventaire (nom, genre, sha court, défaut)
"""
import argparse
import json
import os
import re
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_JSON = os.path.join(_ROOT, "tools", "refutateur_temoins.json")


def charger():
    """Les témoins déclarés, dans l'ordre du fichier gelé."""
    with open(_JSON, encoding="utf-8") as fh:
        return json.load(fh)["temoins"]


def par_nom(nom):
    """Le témoin `nom`, ou KeyError — jamais un témoin approximatif."""
    for t in charger():
        if t["nom"] == nom:
            return t
    raise KeyError(f"témoin inconnu : {nom!r} (connus : {[t['nom'] for t in charger()]})")


def extraire(temoin, dest):
    """Écrit la version GELÉE du record dans `dest/<nom>.md` et rend le chemin écrit.

    Lève si le couple (sha, chemin) n'existe pas : un témoin introuvable est RAPPORTÉ, jamais remplacé.
    """
    os.makedirs(dest, exist_ok=True)
    p = subprocess.run(["git", "show", f"{temoin['sha']}:{temoin['chemin']}"], cwd=_ROOT,
                       capture_output=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(
            f"témoin {temoin['nom']} introuvable : {temoin['sha']}:{temoin['chemin']}\n{p.stderr.strip()}")
    out = os.path.join(dest, f"{temoin['nom']}.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(p.stdout)
    return out


def _critiques_confirmees(texte):
    """Nombre de critiques à compter dans `texte`, ou None si ce n'est pas une liste JSON.

    Quand les critiques portent un `verdict` (forme rendue par le workflow), seules les CONFIRMÉES
    comptent — même règle des deux côtés, sinon le même témoin serait jugé par deux barèmes.
    """
    try:
        charge = json.loads(texte)
    except ValueError:
        return None
    if not isinstance(charge, list):
        return None
    avec_verdict = [c for c in charge if isinstance(c, dict) and "verdict" in c]
    if avec_verdict and len(avec_verdict) == len(charge):
        return sum(1 for c in charge if str(c["verdict"]).lower().startswith("confirm"))
    return len(charge)


def verifier(temoin, texte_critiques):
    """La revue a-t-elle retrouvé ce que ce témoin exige ? (True = revue recevable sur ce témoin.)

    * `genre = "defaut"` : la regex `attendu` doit apparaître dans le texte des critiques.
    * `genre = "noop"`   : au plus UNE critique (confirmée, si les verdicts sont présents).

    ⚠️ Un texte VIDE rend False dans les DEUX genres. Le silence d'un agent qui n'a rien rendu et le
    silence d'une revue qui n'a rien trouvé se ressemblent ; les confondre ferait passer le témoin no-op
    sur une absence de mesure — exactement la forme « entrée vide -> affirmation de fond » que ce dépôt
    traque chez ses instruments. Une liste JSON vide (`[]`) est une RÉPONSE, elle passe.
    """
    if not texte_critiques.strip():
        return False
    if temoin["genre"] == "noop":
        n = _critiques_confirmees(texte_critiques)
        if n is None:
            return texte_critiques.strip() == "[]"
        return n <= 1
    if not temoin["attendu"]:
        raise ValueError(f"témoin {temoin['nom']} de genre 'defaut' sans regex `attendu`")
    return re.search(temoin["attendu"], texte_critiques, re.I) is not None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--extraire", metavar="DIR", help="écrit chaque témoin à son SHA dans DIR")
    ap.add_argument("--verifier", nargs=2, metavar=("NOM", "FICHIER"),
                    help="confronte le texte des critiques au témoin NOM")
    ap.add_argument("--lister", action="store_true", help="inventaire des témoins gelés")
    args = ap.parse_args(argv)
    tem = charger()
    if args.extraire:
        for t in tem:
            print(extraire(t, args.extraire))
        return 0
    if args.verifier:
        try:
            t = par_nom(args.verifier[0])
        except KeyError as exc:
            print(exc)
            return 2
        with open(args.verifier[1], encoding="utf-8") as fh:
            ok = verifier(t, fh.read())
        print(f"{t['nom']} ({t['genre']}) : {'RETROUVÉ' if ok else 'NON RETROUVÉ -> revue NULLE'}")
        if not ok:
            print(f"  défaut attendu : {t['defaut']}")
        return 0 if ok else 1
    if args.lister:
        for t in tem:
            print(f"{t['nom']:34s} {t['genre']:7s} {t['sha'][:9]}  {t['chemin']}")
            print(f"  {t['defaut']}")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
