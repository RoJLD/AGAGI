"""Témoins gelés du Réfutateur : extraction ANONYME à leur SHA, et barème UNIQUE de la phase témoins.

Le Réfutateur (`docs/REF/REF-REVUE-ADVERSARIALE.md`, `.claude/workflows/refutateur.js`) est un
INSTRUMENT : il produit une affirmation (« ce record a tel défaut », ou « rien à signaler »). Comme tout
instrument du dépôt, il se calibre contre une réponse CONNUE avant d'être cru. Les témoins gelés sont
cette réponse connue :

* trois records dont un défaut RÉEL a été trouvé et gravé APRÈS coup (E8, E26, E19), figés au SHA qui
  porte le défaut NU — pas sa rectification ;
* un record SAIN, qui donne le plancher de fausses critiques. Sans lui, un Réfutateur qui crie sur tout
  passerait les trois premiers et paraîtrait parfait.

Une revue dont la phase témoins échoue est NULLE : rien ne s'écrit dans `docs/reviews/`.

⚠️ **Ce module est la CLÉ DE RÉPONSE, et elle ne se republie nulle part.** Trois propriétés la protègent,
chacune contre une façon MESURÉE de franchir l'instrument sans rien mesurer :

1. **Extraction ANONYME.** `extraire` écrit sous le nom NEUTRE déclaré au roster (`temoin-N.md`), délié de
   l'ordre du roster. Un agent qui lit `temoin-3.md` ne sait ni que c'est un témoin à défaut, ni lequel.
   Publier « ce que la revue doit produire » à côté du témoin mesurerait sa capacité à lire un tableau ;
   et un plancher de fausses critiques mesuré sous l'instruction « ce record est sain, tais-toi » n'est
   plus un plancher.
2. **Seule une critique CONFIRMÉE retrouve un témoin**, et la regex est cherchée dans son CONSTAT et sa
   PREUVE — jamais dans sa SONDE. Mesuré : le token attendu apparaît dans le texte des témoins eux-mêmes
   (section « ce qui n'est pas mesuré ») ; une revue qui recopie la commande, ou qui ne confirme rien,
   franchissait les quatre témoins.
3. **Le barème vit ICI et nulle part ailleurs.** Le workflow ne juge pas : il fait lancer ce CLI. Deux
   implémentations du même barème divergent — elles avaient déjà divergé sur trois points (dialecte de
   regex, comptage partiel, `attendu` vide).

Ce module ne construit AUCUN monde, ne tient AUCUN bail (`kuzu`) et ne lance aucune simulation : il ne
fait que lire l'histoire git et apparier des expressions régulières.

Usage :
    python tools/refutateur_temoins.py --extraire <dir>        # écrit <dir>/temoin-N.md, imprime nom -> fichier
    python tools/refutateur_temoins.py --verifier <nom> <fic>  # 0 = défaut retrouvé, 1 = revue NULLE, 2 = indécidable
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

#: Champs d'une critique sur lesquels la regex d'un témoin à défaut est cherchée. `sonde` en est
#: EXCLUE : recopier la commande qui nomme le paramètre n'est pas une découverte.
_CHAMPS_JUGES = ("constat", "preuve")


class FormatInvalide(ValueError):
    """Le texte des critiques n'est pas jugeable — ni verdict NULLE, ni verdict RETROUVÉ : indécidable.

    Distinguer ce cas de « revue NULLE » est le point : un texte illisible est une absence de mesure,
    pas un résultat. Le confondre avec un échec ferait d'un bug de sérialisation un verdict de fond.
    """


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


def nom_attendu(temoin):
    """Le nom que ce témoin DOIT porter : `<identifiant du record>-<sha7>`, RECOMPUTÉ.

    L'identifiant du record est la tête de son nom de fichier (avant le premier `_`) ; le sha7 est le
    SHA gelé. Les deux champs existent déjà : le nom n'est donc **dérivé, jamais déclaré**.

    ⚠️ **Pourquoi une FORME POSITIVE et non une liste de mots interdits.** La question qui compte est
    « ce nom divulgue-t-il le genre du témoin ? ». Une liste noire (`sain`, `noop`, `defaut`…) ne
    répond jamais à celle-là : elle répond « ce nom contient-il l'un de ces mots ». Mesuré le
    2026-09-23 : `LOCK-002-sain` a été attrapé par la liste, mais `RETAIN-COMPOSE-pre-retractation`
    — qui annonce qu'une rétractation a suivi, donc qu'un défaut est à trouver — est passé à travers,
    et n'a été vu qu'À L'ŒIL. Ajouter `retract*` aurait déplacé le trou d'un cran. Une forme dérivée
    de l'identité (quel record, à quel SHA) ne PEUT structurellement rien dire de la qualité de ce
    qu'elle nomme : elle tue la classe au lieu d'énumérer ses membres. Elle est aussi plus exacte —
    un témoin EST un record à un SHA.

    ⚠️ **Ce que cette garde NE VOIT PAS, et qu'il faut savoir avant la prochaine passe** : elle vérifie
    la FORME DU NOM, jamais le CONTENU du fichier extrait. Un record peut, à son SHA gelé, annoncer sa
    propre faiblesse dans son titre ou sa prose et dire ainsi au relecteur ce qu'il doit trouver —
    rien ici ne l'attrape. Seule l'`antisignature` couvre un cas voisin et un seul : que la marque de
    la CORRECTION soit absente. « Le texte gelé n'annonce pas son propre défaut » n'est ni mesuré, ni
    décidable par motif ; il reste à la charge de qui gèle un témoin.
    """
    identifiant = os.path.basename(temoin["chemin"]).split("_")[0]
    return f"{identifiant}-{temoin['sha'][:7]}"


def roster_conforme(temoins=None):
    """(ok, raison) — le roster est-il exactement 3 témoins à défaut et 1 no-op, noms et fichiers uniques ?

    Le gel n'est contraignant que s'il est VÉRIFIÉ : sans cela un appelant peut affaiblir un `attendu`,
    ne passer que le no-op, ou pointer ailleurs.
    """
    tem = charger() if temoins is None else temoins
    genres = [t.get("genre") for t in tem]
    if genres.count("defaut") != 3 or genres.count("noop") != 1 or len(tem) != 4:
        return False, f"roster non conforme : {genres!r} (attendu 3 'defaut' + 1 'noop')"
    if len({t["nom"] for t in tem}) != len(tem):
        return False, "noms de témoins en collision"
    if len({t["fichier"] for t in tem}) != len(tem):
        return False, "noms de fichiers d'extraction en collision"
    for t in tem:
        if t["genre"] == "defaut" and not t.get("attendu"):
            return False, f"témoin à défaut sans regex `attendu` : {t['nom']}"
        voulu = nom_attendu(t)
        if t["nom"] != voulu:
            return False, (
                f"nom de témoin hors FORME : {t['nom']!r}, attendu {voulu!r} "
                "(<identifiant du record>-<sha7>, recomputé depuis `chemin` et `sha`). Un nom libre "
                "peut annoncer le GENRE du témoin, et le REF publie les noms.")
    return True, "ok"


def extraire(temoin, dest):
    """Écrit la version GELÉE du record sous son nom NEUTRE dans `dest` et rend le chemin écrit.

    Le nom du témoin n'apparaît NULLE PART dans le chemin écrit : la revue doit être aveugle à ce
    qu'elle relit. Lève si le couple (sha, chemin) n'existe pas — un témoin introuvable est RAPPORTÉ,
    jamais remplacé.
    """
    os.makedirs(dest, exist_ok=True)
    p = subprocess.run(["git", "show", f"{temoin['sha']}:{temoin['chemin']}"], cwd=_ROOT,
                       capture_output=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(
            f"témoin {temoin['nom']} introuvable : {temoin['sha']}:{temoin['chemin']}\n{p.stderr.strip()}")
    out = os.path.join(dest, temoin["fichier"])
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(p.stdout)
    return out


def extraire_tous(dest):
    """Extrait les quatre témoins et rend la correspondance {nom: chemin écrit} — à l'APPELANT seulement.

    Rien n'est écrit dans `dest` qui trahisse cette correspondance : l'agent de revue reçoit un chemin,
    le vérificateur relit le roster.
    """
    return {t["nom"]: extraire(t, dest) for t in charger()}


def _charger_critiques(texte):
    """La liste des critiques, ou FormatInvalide. Chaque critique est un objet portant un `verdict`."""
    try:
        charge = json.loads(texte)
    except ValueError as exc:
        raise FormatInvalide(f"critiques illisibles (JSON attendu) : {exc}") from exc
    if not isinstance(charge, list):
        raise FormatInvalide(f"critiques attendues sous forme de LISTE, reçu {type(charge).__name__}")
    for i, c in enumerate(charge):
        if not isinstance(c, dict):
            raise FormatInvalide(f"critique {i} : objet attendu, reçu {type(c).__name__}")
        if "verdict" not in c:
            raise FormatInvalide(
                f"critique {i} sans `verdict` : indécidable. Un comptage PARTIEL (certaines critiques "
                "jugées, d'autres non) rendait un barème différent de chaque côté.")
    return charge


def _confirmees(critiques):
    return [c for c in critiques if str(c.get("verdict", "")).strip().lower().startswith("confirm")]


def verifier(temoin, texte_critiques):
    """La revue a-t-elle retrouvé ce que ce témoin exige ? (True = revue recevable sur ce témoin.)

    * `genre = "defaut"` : la regex `attendu` doit apparaître dans le CONSTAT ou la PREUVE d'au moins une
      critique **CONFIRMÉE**. Ni la sonde, ni une critique non confirmée ne comptent.
    * `genre = "noop"`   : au plus UNE critique confirmée.

    ⚠️ Un texte VIDE rend False dans les deux genres. Le silence d'un agent qui n'a rien rendu et le
    silence d'une revue qui n'a rien trouvé se ressemblent ; les confondre ferait passer le témoin no-op
    sur une absence de mesure — exactement la forme « entrée vide -> affirmation de fond » que ce dépôt
    traque chez ses instruments. Une liste JSON vide (`[]`) est une RÉPONSE, elle passe le no-op.
    Un texte ILLISIBLE lève `FormatInvalide` : indécidable n'est pas NULLE.
    """
    if not texte_critiques.strip():
        return False
    confirmees = _confirmees(_charger_critiques(texte_critiques))
    if temoin["genre"] == "noop":
        return len(confirmees) <= 1
    if not temoin.get("attendu"):
        raise ValueError(f"témoin {temoin['nom']} de genre 'defaut' sans regex `attendu`")
    motif = re.compile(temoin["attendu"], re.I)
    return any(motif.search(str(c.get(champ, ""))) for c in confirmees for champ in _CHAMPS_JUGES)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--extraire", metavar="DIR", help="écrit chaque témoin à son SHA, sous un nom neutre")
    ap.add_argument("--verifier", nargs=2, metavar=("NOM", "FICHIER"),
                    help="confronte le texte des critiques (JSON) au témoin NOM")
    ap.add_argument("--lister", action="store_true", help="inventaire des témoins gelés")
    args = ap.parse_args(argv)
    ok, raison = roster_conforme()
    if not ok:
        print(f"roster GELÉ invalide : {raison}")
        return 2
    if args.extraire:
        for nom, chemin in extraire_tous(args.extraire).items():
            print(f"{nom} -> {chemin}")
        return 0
    if args.verifier:
        try:
            t = par_nom(args.verifier[0])
        except KeyError as exc:
            print(exc)
            return 2
        with open(args.verifier[1], encoding="utf-8") as fh:
            texte = fh.read()
        try:
            retrouve = verifier(t, texte)
        except FormatInvalide as exc:
            print(f"{t['nom']} : INDÉCIDABLE (format non reconnu) — {exc}")
            return 2
        print(f"{t['nom']} ({t['genre']}) : {'RETROUVÉ' if retrouve else 'NON RETROUVÉ -> revue NULLE'}")
        if not retrouve:
            print(f"  défaut attendu : {t['defaut']}")
        return 0 if retrouve else 1
    if args.lister:
        for t in charger():
            print(f"{t['nom']:34s} {t['genre']:7s} {t['sha'][:9]}  {t['fichier']}  {t['chemin']}")
            print(f"  {t['defaut']}")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
