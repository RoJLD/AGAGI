"""Cliquet des SYNTHÈSES — un chiffre publié dans une doc doit se RECOMPUTER.

⚠️ Né d'un défaut MESURÉ, trois fois (gap M5 de la cartographie du 2026-09-02) :
  * `REGISTRE_ERREURS.md` annonçait « 19 classes sur 19 » **le jour même** où E20 était ajoutée ;
  * `CLAUDE.md` §Cliquets disait « 5 cliquets, tous branchés » alors que le hook en portait 6 ;
  * `CLAUDE.md` §Calibration disait « 105 détectés, 104 calibrés » quand le cliquet en comptait 143.

Les ATOMES du dépôt sont gardés (records, instruments, gardes, backlog, pré-inscriptions). Les
SYNTHÈSES — c'est-à-dire précisément ce qu'une session future LIT et CITE — ne l'étaient pas. Un
résumé faux est plus corrosif qu'un record faux : il est lu en premier et sert de prémisse.

CONVENTION (déclarative, minimale) : la phrase qui publie un compte porte une balise HTML

    Inventaire : **196 détectés**, 192 calibrés. <!-- count:instruments_detectes=196 -->

Le cliquet (1) RECOMPUTE la grandeur, (2) la compare à la valeur de la balise, (3) vérifie que cette
valeur figure bien dans le TEXTE VISIBLE de la ligne. Les trois vérifications échouent séparément :
un chiffre périmé, une balise désynchronisée de sa phrase, et un compteur inconnu ne sont pas la même
faute — et « balise absente du texte » attrape le cas où l'on met à jour la balise en oubliant la
phrase, qui est le mode d'échec le plus probable.

⚠️ CE QUE CE CLIQUET NE FAIT PAS. Il ne découvre pas les chiffres non balisés : il vérifie ce qu'on
lui a DÉCLARÉ. C'est délibéré et c'est la même règle que partout ici (« ne pas proxifier ce qu'on ne
sait pas mesurer ») — deviner quels nombres d'une prose sont des comptes vérifiables produirait des
faux positifs sur toute date, tout ratio et tout chiffre historique. La couverture croît par
annotation ; le compteur de balises `syntheses_balisees` est lui-même publié ET BALISÉ
(`PRIORITES_ET_DETTES.md`), de sorte qu'une régression de couverture se voit. ⚠️ Cette propriété a
été AFFIRMÉE ici avant d'être tenue (la balise n'existait pas) : auto-audit du 2026-09-07, corrigé
le jour même — une affirmation non vérifiée dans l'outil qui les traque.

⚠️ UN CHIFFRE HISTORIQUE NE SE BALISE PAS. « 105 au 2026-09-01 » est vrai pour toujours : le baliser
le rendrait faux demain. La balise dit « ce nombre décrit l'état COURANT ».

Usage :
    python tools/check_synthesis_counts.py            # exit 1 si un compte publié est faux
    python tools/check_synthesis_counts.py --report   # liste tout, exit 0
    python tools/check_synthesis_counts.py --list     # les compteurs disponibles
"""
import argparse
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Fichiers balayés : la couche de LECTURE (ce qu'une session cite), pas les records (déjà gardés).
_DOCS = (
    "CLAUDE.md",
    os.path.join("docs", "REF", "REGISTRE_ERREURS.md"),
    os.path.join("docs", "roadmap", "PRIORITES_ET_DETTES.md"),
    os.path.join("docs", "EDR", "README.md"),
    os.path.join("docs", "SDR", "G2_agent_composes.md"),
    # Élargi le 2026-09-07 (T3) : ces trois-là sont la carte que toute session lit AVANT les records.
    os.path.join("docs", "REF", "REF-DEMAND-MARKER.md"),
    os.path.join("docs", "roadmap", "FIL_DIRECTEUR_AGI.md"),
    os.path.join("docs", "roadmap", "SCIENCE.md"),
    os.path.join("docs", "roadmap", "ROLES.md"),
)

_TAG = re.compile(r"<!--\s*count:([a-z0-9_]+)\s*=\s*(-?\d+)\s*-->")


# --------------------------------------------------------------------------------------------------
# REGISTRE DES COMPTEURS. Chacun rend un int et n'a le droit de RIEN simuler : ce sont des lectures
# de l'arbre ou des appels aux cliquets existants. Un compteur qui lèverait rendrait le cliquet
# ininterprétable — on le laisse lever : « je ne sais pas » ne doit jamais devenir « c'est faux ».
# --------------------------------------------------------------------------------------------------

def _calib():
    import tools.check_instrument_calibration as C
    instruments = C.scan_instruments()
    calibrated = C.scan_calibrated()
    coll = C.scan_collisions()
    nai = {}
    for n, _r in C.scan_not_instruments().items():
        nu = n.split("::")[-1]
        if nu in instruments and ("::" in n or nu not in coll):
            nai.setdefault(nu, set()).add(n.split("::")[0].replace("\\", "/"))
    couv = C.collision_coverage(coll, getattr(C.scan_calibrated, "qualified_paths", {}), nai)
    cal = set(calibrated) | {nu for nu, (ok, _) in couv.items() if ok and nu in instruments}
    faux = {nu for nu in nai if nu not in coll}
    return instruments, cal, faux


def _graphe():
    import tools.check_record_links as R
    return R.analyze()


_STATUTS = ("exécutable", "documenté", "non automatisable")
# Un code-span Markdown : une course de N backticks, un contenu, la MÊME course de N backticks (non adjacente à
# d'autres). Un « | » qui y vit n'est pas un séparateur de cellule.
_CODE_SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")
_LIGNE_CLASSE = re.compile(r"\s*\|\s*\*\*E\d+\*\*\s*\|")


def _cellules(ligne):
    """Cellules d'une ligne de tableau Markdown, bords retirés : un « | » dans un code-span ou échappé (\\|) ne
    sépare PAS. Mesuré le 2026-09-26 : un split naïf sur « | » désaligne 6 lignes sur 33 du registre. PURE."""
    s = ligne.rstrip("\r\n")
    p = _CODE_SPAN.sub(lambda m: m.group(0).replace("|", "\x00"), s).replace("\\|", "\x00")
    c = [x.replace("\x00", "|").strip() for x in p.split("|")]
    if c and c[0] == "":
        c = c[1:]
    if c and c[-1] == "":
        c = c[:-1]
    return c


def _statut_cellule(cellule):
    """Le statut d'une cellule de la colonne « Statut », DÉPOUILLÉ de sa mise en forme : backticks, gras et italique,
    puis tout commentaire qui SUIT le vocable (« `exécutable` **(promu le 2026-09-02 — …)** »). Rend le vocable, ou
    la cellule nettoyée telle quelle quand elle n'en est pas un (le compteur `classes_statut_inconnu` la publie). PURE."""
    nu = re.sub(r"[`*]", "", cellule).strip()
    return re.sub(r"\s*\(.*$", "", nu, flags=re.S).strip()


def _statuts_registre(texte=None):
    """[(classe, statut)] des lignes `| **Exx** |`, statut lu dans la colonne dont l'EN-TÊTE est « Statut ».

    ⚠️ P2.117 (2026-09-26) : le compteur lisait le statut par sa FORME (« `exécutable` » entre backticks juste après
    un « | »), pas par sa COLONNE. E28 et E29, statut `exécutable` écrit NU, n'étaient comptées nulle part : le
    registre publiait « 24 exécutables » quand la colonne en portait 26, et la porte 8 rendait OK parce que la
    prose recopiait le même chiffre que l'instrument — E8 appliquée à l'instrument qui traque E8. Une classe que
    le compteur ne voit pas n'est jamais promue. En-tête introuvable : LÈVE (un compteur qui rendrait 0 ferait
    d'une source illisible un registre vide, le biais négatif du dépôt)."""
    if texte is None:
        texte = _lire(os.path.join("docs", "REF", "REGISTRE_ERREURS.md"))
    lignes = texte.splitlines()
    entete = next((l for l in lignes if l.lstrip().startswith("|") and "Statut" in _cellules(l)), None)
    if entete is None:
        raise ValueError("registre des erreurs : aucune ligne d'en-tête ne porte la colonne « Statut »")
    idx = _cellules(entete).index("Statut")
    out = []
    for l in lignes:
        if _LIGNE_CLASSE.match(l):
            c = _cellules(l)
            classe = re.match(r"\s*\|\s*\*\*(E\d+)\*\*", l).group(1)
            out.append((classe, _statut_cellule(c[idx]) if len(c) > idx else ""))
    return out


def _classes_registre(statut, texte=None):
    """Compte les LIGNES `| **Exx** |` dont la colonne « Statut » vaut `statut` (une classe peut citer un statut
    dans sa prose, comme E1 : seule la colonne compte)."""
    return sum(1 for _c, s in _statuts_registre(texte) if s == statut)


def _classes_statut_inconnu(texte=None):
    """Lignes dont le statut n'est AUCUN des trois vocables : une faute de rédaction, jamais une quatrième catégorie.
    Publié à 0 dans le registre : une ligne mal écrite fait rougir la porte 8 au commit qui l'écrit."""
    return sum(1 for _c, s in _statuts_registre(texte) if s not in _STATUTS)


def _portes_hook():
    """Nombre de gardes réellement branchées dans le hook (chaque bloc numéroté qui lance un check)."""
    p = os.path.join(_ROOT, "tools", "hooks", "pre-commit")
    with open(p, encoding="utf-8") as fh:
        src = fh.read()
    return len(set(re.findall(r"python\s+tools/(check_\w+)\.py", src)))


def _aretes_taxonomy():
    p = os.path.join(_ROOT, "data", "agi_taxonomy", "demands.json")
    with open(p, encoding="utf-8") as fh:
        return len(json.load(fh))


def _regles_scellees():
    d = os.path.join(_ROOT, "docs", "preregistrations")
    return len([f for f in os.listdir(d) if f.endswith(".json")]) if os.path.isdir(d) else 0


def _roles(statut):
    from tools.check_roles_registry import lignes
    return sum(1 for l in lignes(_lire(os.path.join("docs", "roadmap", "ROLES.md"))) if l["statut"] == statut)


COMPTEURS = {
    "instruments_detectes": lambda: len(_calib()[0]),
    "instruments_calibres": lambda: len(_calib()[1]),
    "instruments_non_calibres": lambda: len(set(_calib()[0]) - _calib()[1] - _calib()[2]),
    "records_orphelins": lambda: len(_graphe()["orphans"]),
    "records_collisions": lambda: len(_graphe()["collisions"]),
    "records_gate_unlinked": lambda: len(_graphe()["gate_unlinked"]),
    "records_mismatches": lambda: len(_graphe()["gate_tests_mismatch"]),
    "records_total": lambda: _graphe()["n_records"],
    "classes_executables": lambda: _classes_registre("exécutable"),
    "classes_documentees": lambda: _classes_registre("documenté"),
    "classes_statut_inconnu": _classes_statut_inconnu,
    "portes_hook": _portes_hook,
    "aretes_taxonomy": _aretes_taxonomy,
    "regles_scellees": _regles_scellees,
    "roles_instancies": lambda: _roles("instancié"),
    "roles_candidats": lambda: _roles("candidat"),
    "syntheses_balisees": lambda: sum(len(_TAG.findall(_lire(d))) for d in _DOCS),
}


def _lire(rel):
    p = os.path.join(_ROOT, rel)
    if not os.path.isfile(p):
        return ""
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def scan(docs=_DOCS, compteurs=None):
    """Renvoie (problemes, n_balises). `problemes` = [(doc, ligne, nom, attendu, reel, genre)].

    Trois genres, distincts par construction :
      * `compteur_inconnu` : la balise nomme une grandeur qui n'existe pas au registre ;
      * `chiffre_perime`   : la valeur de la balise ne vaut plus la grandeur recomputée ;
      * `texte_desynchro`  : la valeur de la balise n'apparaît pas dans le texte visible de la ligne
        (on a mis à jour la balise en oubliant la phrase — le mode d'échec le plus probable).
    """
    compteurs = COMPTEURS if compteurs is None else compteurs
    cache, problemes, n = {}, [], 0
    for rel in docs:
        for i, ligne in enumerate(_lire(rel).splitlines(), start=1):
            for nom, val in _TAG.findall(ligne):
                n += 1
                attendu = int(val)
                if nom not in compteurs:
                    problemes.append((rel, i, nom, attendu, None, "compteur_inconnu"))
                    continue
                if nom not in cache:
                    cache[nom] = int(compteurs[nom]())
                reel = cache[nom]
                if attendu != reel:
                    problemes.append((rel, i, nom, attendu, reel, "chiffre_perime"))
                    continue
                visible = _TAG.sub("", ligne)
                if not re.search(r"(?<!\d)" + re.escape(str(attendu)) + r"(?!\d)", visible):
                    problemes.append((rel, i, nom, attendu, reel, "texte_desynchro"))
    return problemes, n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true", help="Liste tout et sort (exit 0).")
    ap.add_argument("--list", action="store_true", help="Affiche les compteurs disponibles.")
    args = ap.parse_args(argv)

    if args.list:
        for nom, fn in sorted(COMPTEURS.items()):
            print(f"  {nom:26s} = {fn()}")
        return 0

    problemes, n = scan()
    print(f"syntheses : {n} compte(s) publié(s) et vérifié(s) dans {len(_DOCS)} documents")
    if args.report:
        for nom, fn in sorted(COMPTEURS.items()):
            print(f"  {nom:26s} = {fn()}")
    if not problemes:
        print("OK : aucun compte publié n'est périmé.")
        return 0
    for rel, i, nom, attendu, reel, genre in problemes:
        if genre == "compteur_inconnu":
            print(f"  [COMPTEUR INCONNU] {rel}:{i} « {nom} » — compteurs connus : "
                  f"{', '.join(sorted(COMPTEURS))}")
        elif genre == "chiffre_perime":
            print(f"  [CHIFFRE PÉRIMÉ] {rel}:{i} {nom} publié={attendu} RÉEL={reel}")
        else:
            print(f"  [TEXTE DÉSYNCHRONISÉ] {rel}:{i} {nom}={attendu} — la balise est à jour mais le "
                  f"nombre n'apparaît pas dans la phrase")
    print("\nUn résumé faux est lu AVANT les records et sert de prémisse : mettre la phrase à jour, "
          "ou retirer la balise si le chiffre est HISTORIQUE (« 105 au 2026-09-01 » est vrai pour "
          "toujours ; le baliser le rendrait faux demain).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
