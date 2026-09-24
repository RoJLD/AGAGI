"""Témoins gelés du Réfutateur : extraction ANONYME à leur SHA, et barème À DEUX ÉTAGES.

Le Réfutateur (`docs/REF/REF-REVUE-ADVERSARIALE.md`, `.claude/workflows/refutateur.js`) est un
INSTRUMENT : il produit une affirmation (« ce record a tel défaut », ou « rien à signaler »). Comme
tout instrument du dépôt, il se calibre contre une réponse CONNUE avant d'être cru. Les témoins gelés
sont cette réponse connue : trois records dont un défaut RÉEL a été gravé APRÈS coup (E8, E26, E19),
figés au SHA qui porte le défaut NU, et un record SAIN qui donne le plancher de fausses critiques.

⚠️ **LE MOTIF `attendu` N'EST PLUS LE BARÈME** (re-revue du 2026-09-23, trois faits reproduits) :

1. une seule phrase vague, identique pour les quatre témoins, écrite sans ouvrir un fichier, passait
   **4/4** — le plancher de fausses retrouvailles valait le signal MAXIMAL ;
2. recopier UNE ligne du témoin extrait passait deux des trois défauts (`forage_payoff` est dans le
   texte relu, `lr` aussi) ;
3. **le signe était inversé** : la critique JUSTE du défaut E26, avec sa sonde et son `fichier:ligne`,
   rendait `revue NULLE` faute du mot « corps ».

C'est la leçon `run_ablation_map` du dépôt : un instrument de contraste dont le no-op vaut le signal
ne voit rien. « Cette revue a-t-elle trouvé le défaut ? » n'est pas décidable par une expression
régulière, et la règle du dépôt est de ne pas proxifier ce qu'on ne sait pas mesurer. D'où deux
étages, chacun à deux issues mesurées :

* **Étage 1 — plancher MÉCANIQUE**, sans aucun agent (`recevabilite`) : une critique n'est recevable
  que si son verdict commence par `confirm`, qu'elle porte une **preuve de FORME** (`fichier:ligne`,
  ou une commande avec sa sortie, ou une valeur opposée à une autre) et que son constat n'est pas une
  **RECOPIE** du fichier relu (fenêtre de `mots_recopie` mots consécutifs, seuil MESURÉ).
* **Étage 2 — le JUGE** (`.claude/workflows/refutateur.js`, phase `Juge`) : un agent à prompt figé
  reçoit le défaut DÉCLARÉ du témoin et les critiques RECEVABLES, et répond `OUI` / `NON` /
  `INDECIDABLE` — **sans jamais voir le motif `attendu`**. Il est lui-même calibré sur cinq textes
  gelés à réponse connue (`tools/refutateur_juge_temoins.json`) ; s'il rate ses propres témoins,
  l'instrument rend INDÉCIDABLE au lieu de juger.

Le motif `attendu` SURVIT en **signal rapporté** (« le token apparaît / n'apparaît pas »), jamais
comme verdict.

**Étage 3 — le plancher se publie.** `plancher()` mesure, le jour même, combien de témoins à défaut
une revue SANS CONTENU peut faire retrouver. Tout score de phase témoins se publie à côté de ce
chiffre : un « 4/4 » sans son plancher est interdit, comme tout ratio du dépôt.

Ce module ne construit AUCUN monde, ne tient AUCUN bail (`kuzu`) et ne lance aucune simulation.

Usage :
    python tools/refutateur_temoins.py --extraire <dir>
    python tools/refutateur_temoins.py --verifier <nom> <critiques.json> --extrait <dir>/<fichier>.md
                                       [--jugement OUI|NON|INDECIDABLE]
    python tools/refutateur_temoins.py --plancher <dir>      # plancher de fausses retrouvailles
    python tools/refutateur_temoins.py --cas-du-juge         # calibration de l'etage 2, REDIGEE
    python tools/refutateur_temoins.py --cas-du-juge-avec-reponses   # VERIFICATEUR seulement
    python tools/refutateur_temoins.py --lister
"""
import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_JSON = os.path.join(_ROOT, "tools", "refutateur_temoins.json")
_JUGE = os.path.join(_ROOT, "tools", "refutateur_juge_temoins.json")

#: Champs d'une critique sur lesquels le JUGE et l'anti-recopie travaillent. `sonde` en est exclue :
#: recopier la commande qui nomme un paramètre n'est pas une découverte.
_CHAMPS_JUGES = ("constat", "preuve")

#: Texte neutre servant à détecter un `attendu` DÉGÉNÉRÉ (un motif qui matche tout, comme `.`).
_TEXTE_NEUTRE = "le record est clair, bien ecrit, et sa conclusion est prudente"

_RE_FICHIER_LIGNE = re.compile(r"[\w./\\-]+\.(?:py|md|json|js|txt|ya?ml|npz):\d+(?:-\d+)?")
_RE_COMMANDE = re.compile(r"(?:^|[\s`])(?:python|grep|rg|git|pytest|sed|awk|cat|ls|jq)\b")
_RE_NOMBRE = re.compile(r"\d")
_RE_MOT = re.compile(r"[0-9a-z_]+")


class FormatInvalide(ValueError):
    """Le texte des critiques n'est pas jugeable — ni NULLE, ni RETROUVÉ : indécidable.

    Distinguer ce cas d'une revue NULLE est le point : un texte illisible est une absence de mesure,
    pas un résultat. Le confondre avec un échec ferait d'un bug de sérialisation un verdict de fond.
    """


# --------------------------------------------------------------------------------------------- #
# Le roster gelé
# --------------------------------------------------------------------------------------------- #


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
    SHA gelé. Les deux champs existent déjà : le nom est donc **dérivé, jamais déclaré**.

    ⚠️ **Pourquoi une FORME POSITIVE et non une liste de mots interdits.** La question qui compte est
    « ce nom divulgue-t-il le genre du témoin ? ». Une liste noire n'y répond jamais : elle répond
    « ce nom contient-il l'un de ces mots ». Mesuré le 2026-09-23 : la liste a attrapé `LOCK-002-sain`
    et LAISSÉ PASSER `RETAIN-COMPOSE-pre-retractation` — qui annonce qu'une rétractation a suivi, donc
    qu'un défaut est à trouver ; il n'a été vu qu'À L'ŒIL. Un nom dérivé de l'IDENTITÉ (quel record, à
    quel SHA) ne peut structurellement rien dire de la QUALITÉ de ce qu'il nomme.

    ⚠️ **Ce que cette garde NE VOIT PAS** : la FORME DU NOM, jamais le CONTENU du fichier extrait. Un
    record peut, à son SHA gelé, annoncer sa propre faiblesse dans son titre et dire ainsi au
    relecteur ce qu'il doit trouver. Seule l'`antisignature` couvre un cas voisin et un seul (la
    marque de la CORRECTION est absente). Cela reste à la charge de qui gèle un témoin.
    """
    identifiant = os.path.basename(temoin["chemin"]).split("_")[0]
    return f"{identifiant}-{temoin['sha'][:7]}"


def attendu_est_degenere(motif):
    """Un `attendu` qui matche un texte NEUTRE ne discrimine rien (`.`, `.*`, `a|`)."""
    if not motif:
        return True
    try:
        return re.search(motif, _TEXTE_NEUTRE, re.I) is not None
    except re.error:
        return True


def roster_conforme(temoins=None):
    """(ok, raison) — 3 témoins à défaut + 1 no-op, noms à la FORME, seuils et motifs non dégénérés.

    ⚠️ Depuis la re-revue du 2026-09-23, `attendu` n'est plus le barème mais un **signal rapporté** :
    l'affaiblir ne change plus aucun verdict. La garde de dégénérescence reste, parce qu'un signal
    rapporté faux est encore un signal faux.
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
        voulu = nom_attendu(t)
        if t["nom"] != voulu:
            return False, (
                f"nom de témoin hors FORME : {t['nom']!r}, attendu {voulu!r} "
                "(<identifiant du record>-<sha7>, recomputé depuis `chemin` et `sha`)")
        if t["genre"] == "defaut" and attendu_est_degenere(t.get("attendu")):
            return False, f"signal `attendu` DÉGÉNÉRÉ (matche un texte neutre) : {t['nom']}"
        if t["genre"] == "noop" and not isinstance(t.get("seuil_critiques"), int):
            return False, f"témoin no-op sans `seuil_critiques` entier : {t['nom']}"
    return True, "ok"


# --------------------------------------------------------------------------------------------- #
# Extraction ANONYME
# --------------------------------------------------------------------------------------------- #


def peremption_du_roster(aujourdhui=None):
    """L'ÂGE des gels et de la dernière revue du roster. **RAPPORTÉ, jamais bloquant.**

    ⚠️ **Un témoin gelé a une durée de vie.** Mesuré le 2026-09-24 : le témoin cru sain, figé le
    2026-09-16, porte un phénomène — « le bras ablaté fait mieux que l'intact » — qui est la forme
    EXACTE d'un résultat établi DEPUIS dans le dépôt (P2.42 : le champion aveuglé à l'entrée survit
    61 % plus longtemps, 7/7 seeds, à corps identique). Le témoin n'a pas été mal choisi : il était
    sain **au regard de ce qu'on savait au gel**. Ce qui était propre le devient moins à mesure que le
    dépôt apprend, et cela vaut pour les QUATRE témoins.

    **Ce qui est calculable et ce qui ne l'est pas.** L'âge d'un gel est un nombre ; la péremption
    SCIENTIFIQUE d'un témoin ne l'est pas — aucun motif ne décide si un record paru depuis change ce
    qu'un témoin mesure. On calcule donc la moitié calculable et on **déclare** l'autre
    (`_peremption` du roster). Et on ne BLOQUE pas : refuser un roster sur un calendrier casserait un
    instrument qui marche pour une raison qui n'est pas un fait sur ses témoins. Le chiffre est
    imprimé par `--lister` et `--plancher`, à côté de tout ce que l'instrument rend.
    """
    import datetime  # noqa: PLC0415

    with open(_JSON, encoding="utf-8") as fh:
        brut = json.load(fh)
    jour = datetime.date.fromisoformat(aujourdhui) if aujourdhui else datetime.date.today()
    revu = datetime.date.fromisoformat(brut["revu_le"])
    intervalle = int(brut["intervalle_de_revue_jours"])
    gels = [{"temoin": t["nom"], "gele_le": t["gele_le"],
             "age_jours": (jour - datetime.date.fromisoformat(t["gele_le"])).days}
            for t in brut["temoins"]]
    depuis_revue = (jour - revu).days
    return {"revu_le": brut["revu_le"], "jours_depuis_la_revue": depuis_revue,
            "intervalle_declare_jours": intervalle,
            "revue_due": depuis_revue > intervalle,
            "gel_le_plus_ancien": max(gels, key=lambda g: g["age_jours"]),
            "gels": sorted(gels, key=lambda g: -g["age_jours"])}


def _imprimer_peremption(p):
    etat = "REVUE DUE" if p["revue_due"] else "à jour"
    print(f"roster revu le {p['revu_le']} ({p['jours_depuis_la_revue']} j, intervalle déclaré "
          f"{p['intervalle_declare_jours']} j) : {etat} · gel le plus ancien "
          f"{p['gel_le_plus_ancien']['temoin']} ({p['gel_le_plus_ancien']['gele_le']}, "
          f"{p['gel_le_plus_ancien']['age_jours']} j)")
    print("  Un témoin gelé mesure ce qu'on savait AU GEL : relire chaque `defaut` contre les records "
          "parus depuis. Rapporté, jamais bloquant.")


def racine_valide(racine):
    """(ok, raison) — ce répertoire est-il une racine du dépôt où le Réfutateur est utilisable ?

    ⚠️ **Un instrument dont la correction dépend d'un état ambiant non déclaré échoue de façon
    imprévisible.** Mesuré le 2026-09-24 : tous les prompts du workflow emploient des chemins
    RELATIFS ; un agent qui héritait d'un répertoire courant différent a lancé le CLI là où le module
    n'existe pas, et n'a rapporté qu'`EXIT=2`. Sans la sortie brute rendue par l'aiguillage, la cause
    aurait été cherchée une troisième fois à l'aveugle. Le workflow annonce désormais une racine
    ABSOLUE et la fait valider ici avant toute autre phase.
    """
    for relatif in ("tools/refutateur_temoins.py", "tools/refutateur_temoins.json",
                    "tools/refutateur_juge_temoins.json"):
        chemin = os.path.join(racine, *relatif.split("/"))
        if not os.path.isfile(chemin):
            return False, f"racine {racine!r} : {relatif} introuvable"
    return True, f"racine {racine!r} : module et roster présents"


def extraire(temoin, dest):
    """Écrit la version GELÉE du record sous son nom NEUTRE dans `dest` et rend le chemin écrit."""
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
    """{nom: chemin écrit} — rendu à l'APPELANT seulement ; rien dans `dest` ne trahit la paire."""
    return {t["nom"]: extraire(t, dest) for t in charger()}


# --------------------------------------------------------------------------------------------- #
# ÉTAGE 1 — le plancher MÉCANIQUE
# --------------------------------------------------------------------------------------------- #


def _mots(texte):
    """Mots normalisés : minuscules, ponctuation et mise en forme Markdown jetées."""
    return _RE_MOT.findall(str(texte).lower())


def plus_longue_fenetre_commune(constat, texte):
    """Longueur de la plus longue suite de mots de `constat` présente MOT POUR MOT dans `texte`.

    Sert à distinguer une DÉCOUVERTE d'une RECOPIE. Mesuré le 2026-09-23 : recopier une seule ligne
    du témoin extrait suffisait à le « retrouver » sous l'ancien barème.
    """
    a, b = _mots(constat), _mots(texte)
    if not a or not b:
        return 0
    index = {}
    for i in range(len(b)):
        index.setdefault(b[i], []).append(i)
    meilleur = 0
    for debut in range(len(a)):
        for i in index.get(a[debut], ()):
            k = 0
            while debut + k < len(a) and i + k < len(b) and a[debut + k] == b[i + k]:
                k += 1
            meilleur = max(meilleur, k)
    return meilleur


def mots_recopie():
    """Le seuil N, gelé dans `refutateur_juge_temoins.json` et JUSTIFIÉ par mesure."""
    with open(_JUGE, encoding="utf-8") as fh:
        return int(json.load(fh)["mots_recopie"])


def preuve_de_forme(critique):
    """(ok, raison) — la critique porte-t-elle une preuve dont la FORME est vérifiable ?

    Trois formes acceptées, et elles seules :
    A. un `fichier:ligne` (ou `fichier:ligne-ligne`) ;
    B. une COMMANDE (dans la sonde) accompagnée d'une SORTIE chiffrée (dans la preuve) ;
    C. une VALEUR opposée à une autre — au moins deux nombres dans la preuve.

    L'attaque universelle du 2026-09-23 (`preuve: "aucune"`, `sonde: "lecture du record"`) échoue les
    trois : c'est ce seul fait qui la tue, sans qu'aucun agent n'ait à la lire.
    """
    preuve = str(critique.get("preuve", ""))
    sonde = str(critique.get("sonde", ""))
    if _RE_FICHIER_LIGNE.search(preuve):
        return True, "fichier:ligne"
    if _RE_COMMANDE.search(sonde) and _RE_NOMBRE.search(preuve):
        return True, "commande + sortie chiffrée"
    if len(re.findall(r"\d[\d\s., ]*", preuve)) >= 2:
        return True, "valeur opposée à une autre"
    return False, f"aucune preuve de forme (preuve={preuve[:40]!r})"


def recevabilite(temoin, critiques, texte_extrait, seuil=None):
    """Étage 1, PUR : sépare les critiques recevables des rejets, avec la raison de chaque rejet."""
    n = mots_recopie() if seuil is None else seuil
    recevables, rejets = [], []
    for c in critiques:
        verdict = str(c.get("verdict", "")).strip().lower()
        if not verdict.startswith("confirm"):
            rejets.append({"critique": c, "raison": f"verdict non confirmé ({verdict or 'vide'})"})
            continue
        ok, raison = preuve_de_forme(c)
        if not ok:
            rejets.append({"critique": c, "raison": raison})
            continue
        fenetre = plus_longue_fenetre_commune(c.get("constat", ""), texte_extrait or "")
        if fenetre >= n:
            rejets.append({"critique": c,
                           "raison": f"RECOPIE : {fenetre} mots consécutifs du fichier relu (seuil {n})"})
            continue
        recevables.append(c)
    return {"recevables": recevables, "rejets": rejets, "mots_recopie": n}


# --------------------------------------------------------------------------------------------- #
# Lecture des critiques
# --------------------------------------------------------------------------------------------- #


def charger_critiques(texte):
    """La liste des critiques, ou FormatInvalide.

    Deux formes d'entrée acceptées : une LISTE nue, ou l'objet `{"critiques": [...]}` que rendent les
    agents du workflow. Ne pas accepter la seconde aurait rendu NULLE le premier lancement réel, pour
    une raison de sérialisation.
    """
    try:
        charge = json.loads(texte)
    except ValueError as exc:
        raise FormatInvalide(f"critiques illisibles (JSON attendu) : {exc}") from exc
    if isinstance(charge, dict) and isinstance(charge.get("critiques"), list):
        charge = charge["critiques"]
    if not isinstance(charge, list):
        raise FormatInvalide(
            f"critiques attendues sous forme de LISTE (ou d'objet {{critiques: [...]}}), "
            f"reçu {type(charge).__name__}")
    for i, c in enumerate(charge):
        if not isinstance(c, dict):
            raise FormatInvalide(f"critique {i} : objet attendu, reçu {type(c).__name__}")
        if "verdict" not in c:
            raise FormatInvalide(
                f"critique {i} sans `verdict` : indécidable. Un comptage PARTIEL (certaines critiques "
                "jugées, d'autres non) rendait un barème différent de chaque côté.")
    return charge


def signal_attendu(temoin, critiques):
    """SIGNAL RAPPORTÉ, jamais un verdict : le token `attendu` apparaît-il dans un constat/preuve ?

    Conservé parce qu'il est informatif quand il est POSITIF ; retiré du barème parce qu'il ne l'est
    pas quand il est négatif (la critique juste d'E26 ne contient pas le mot « corps »).
    """
    motif = temoin.get("attendu")
    if not motif:
        return None
    rx = re.compile(motif, re.I)
    return any(rx.search(str(c.get(champ, ""))) for c in critiques for champ in _CHAMPS_JUGES)


# --------------------------------------------------------------------------------------------- #
# ÉTAGE 2 — la calibration du JUGE
# --------------------------------------------------------------------------------------------- #


#: Champs d'un cas de calibration qui sont la RÉPONSE, et non la question. ⚠️ `nom` en fait partie :
#: `attaque-universelle`, `recopie-une-ligne-…`, `E26-juste-sans-le-mot-corps` annoncent tous leur
#: verdict. Rédiger les trois autres champs en laissant le nom n'aurait rien fermé.
_REPONSES_DU_JUGE = ("juge", "pourquoi", "etage1", "nom")


def ref_du_cas(nom):
    """Identifiant OPAQUE et STABLE d'un cas : il sert de clé au juge sans rien dire de la réponse."""
    return hashlib.sha1(nom.encode("utf-8")).hexdigest()[:8]


def cas_du_juge(nom_temoin=None, avec_reponses=False):
    """Les cinq textes RÉELS de la re-revue. **RÉDIGÉS par défaut** : la question, pas la réponse.

    ⚠️ **Une consigne de « ne pas regarder » n'est pas une garde.** Mesuré le 2026-09-24, troisième
    occurrence de la même loi en une soirée : *dès qu'un instrument s'auto-administre, sa clé de
    réponse voyage avec lui*. Le juge était sommé de lire le JSON de calibration « sans regarder le
    champ `juge` » — or ce fichier donne la réponse **trois fois** : `juge` (OUI/NON), `pourquoi` (en
    clair : « une revue JUSTE échouait là où une revue VIDE passait » dit l'attendu sans ambiguïté) et
    `etage1` (`rejete`/`recevable`). Un juge qui passe sa calibration dans ces conditions ne prouve
    rien, et `juge_est_calibre` ne peut jamais rougir. La parade est structurelle, pas rédactionnelle :
    **servir la question sans la réponse.**

    La vue rédigée rend `ref`, `temoins`, `critiques`. `avec_reponses=True` est réservé au
    VÉRIFICATEUR et aux tests — jamais au juge.

    ⚠️ **Le NOM du cas était lui-même une réponse** — trouvé en relisant la première sortie rédigée :
    `attaque-universelle`, `recopie-une-ligne-du-temoin-GRAB`, `E26-juste-sans-le-mot-corps` annoncent
    tous leur verdict. Rédiger `juge`, `pourquoi` et `etage1` en laissant le nom n'aurait rien fermé.
    Le juge reçoit donc une `ref` OPAQUE et STABLE (sha1 du nom, 8 hex) qui lui sert de clé ; le
    vérificateur la remappe. De même, `temoins: ["*"]` disait « ce cas vise TOUS les témoins », donc
    « attaque universelle » : la vue rédigée le résout en la liste concrète.

    ⚠️ **Ce que la rédaction NE GARANTIT PAS**, et qu'il faut savoir : elle empêche de LIRE la réponse,
    jamais qu'un juge RECONNAISSE un cas déjà vu (rien ne le protège d'avoir été entraîné dessus, ni
    d'avoir croisé ces textes dans un commit du dépôt) ; elle ne dit rien non plus de ce que le juge
    infère du contenu même des critiques. L'ORDRE, lui, portait de l'information (les attaques
    d'abord, les critiques justes ensuite) : la vue rédigée le mélange, c'était gratuit.
    """
    with open(_JUGE, encoding="utf-8") as fh:
        cas = [dict(c, ref=ref_du_cas(c["nom"])) for c in json.load(fh)["cas"]]
    if nom_temoin is not None:
        cas = [c for c in cas if "*" in c["temoins"] or nom_temoin in c["temoins"]]
    if avec_reponses:
        return cas
    # `*` est lui-même un indice (« ce cas vise TOUS les témoins » = attaque universelle) : on le
    # résout en la liste concrète des témoins à défaut.
    defauts = [t["nom"] for t in charger() if t["genre"] == "defaut"]
    redige = [{**{k: v for k, v in c.items() if k not in _REPONSES_DU_JUGE},
               "temoins": defauts if "*" in c["temoins"] else c["temoins"]} for c in cas]
    random.shuffle(redige)
    return redige


def questions_du_juge():
    """Ce que le JUGE doit juger : {fichier neutre, defaut déclaré} — **le no-op est OMIS**.

    ⚠️ Lui demander un jugement sur le témoin sain lui APPRENDRAIT qu'il existe un témoin sain : le
    champ `defaut` du roster y dit « AUCUN — record sain ». C'est la même loi que les quatre
    occurrences précédentes — dès qu'un instrument s'auto-administre, sa clé de réponse voyage avec
    lui. Et ce jugement ne servait à rien : `verdict_temoin` ne consulte le champ que pour un témoin
    de genre `defaut`.

    ⚠️ **Ce que cette omission ne ferme PAS** : le juge ne doit pas non plus RECEVOIR la relecture du
    témoin qu'on ne lui soumet pas, sinon il l'identifie par différence. C'est le rôle de la phase
    `Aiguillage` du workflow, qui filtre les relectures AVANT de les lui passer.
    """
    q = [{"fichier": t["fichier"], "defaut": t["defaut"]}
         for t in charger() if t["genre"] == "defaut"]
    random.shuffle(q)
    return q


def juge_est_calibre(reponses):
    """(ok, details) — le juge a-t-il rendu la réponse CONNUE sur ses cinq témoins ?

    `reponses` : {nom du cas: "OUI"|"NON"|"INDECIDABLE"}. Un juge qui rate ses propres témoins ne
    juge pas : l'instrument rend INDÉCIDABLE. Les deux issues sont testées sans aucun agent.
    """
    details, ok = [], True
    for cas in cas_du_juge(avec_reponses=True):
        # Le juge répond par la REF opaque qu'il a reçue ; le nom est accepté aussi (tests, CLI).
        rendu = str(reponses.get(cas["ref"], reponses.get(cas["nom"], ""))).strip().upper()
        juste = rendu == cas["juge"]
        ok = ok and juste
        details.append({"cas": cas["nom"], "ref": cas["ref"], "attendu": cas["juge"],
                        "rendu": rendu or "(absent)", "juste": juste})
    return ok, details


# --------------------------------------------------------------------------------------------- #
# Verdict par témoin, et ÉTAGE 3 — le plancher
# --------------------------------------------------------------------------------------------- #


def verdict_temoin(temoin, critiques, texte_extrait, jugement=None):
    """Le verdict complet d'un témoin : étage 1, puis étage 2 pour les témoins à défaut.

    Rend {statut: RETROUVE|NULLE|INDECIDABLE, code: 0|1|2, ...}. Le `jugement` vient du JUGE ; sans
    lui, un témoin à défaut est INDÉCIDABLE — l'étage 1 seul ne dit jamais qu'un défaut a été trouvé,
    il dit seulement qu'une critique est RECEVABLE.
    """
    et1 = recevabilite(temoin, critiques, texte_extrait)
    base = {"temoin": temoin["nom"], "genre": temoin["genre"],
            "n_recevables": len(et1["recevables"]), "n_rejets": len(et1["rejets"]),
            "rejets": [r["raison"] for r in et1["rejets"]],
            "signal_attendu": signal_attendu(temoin, et1["recevables"])}
    if temoin["genre"] == "noop":
        # ⚠️ LE NO-OP MESURE, IL NE FAIT PAS BARRAGE (2026-09-24, 1er Step 4 complet). Il rendait NULLE
        # toute la revue quand son compte dépassait le seuil — donc une revue qui venait de retrouver
        # TROIS défauts réels était jetée parce que le plancher était haut. C'est supprimer la mesure au
        # lieu de la publier, l'inverse exact de la doctrine du dépôt : un plancher de bruit se publie À
        # CÔTÉ du ratio, il ne l'annule pas. Il rend donc un NOMBRE, qui voyage avec le score.
        return dict(base, statut="MESURE", code=0, seuil=temoin["seuil_critiques"],
                    depasse_le_seuil=len(et1["recevables"]) > temoin["seuil_critiques"])
    if not et1["recevables"]:
        return dict(base, statut="NULLE", code=1, raison="aucune critique RECEVABLE (étage 1)")
    verdict_juge = str(jugement or "").strip().upper()
    if verdict_juge not in ("OUI", "NON"):
        return dict(base, statut="INDECIDABLE", code=2,
                    raison=f"jugement de l'étage 2 absent ou indécidable ({verdict_juge or 'aucun'})")
    return dict(base, jugement=verdict_juge, statut="RETROUVE" if verdict_juge == "OUI" else "NULLE",
                code=0 if verdict_juge == "OUI" else 1)


def plancher(dest):
    """ÉTAGE 3 — le plancher de fausses retrouvailles, MESURÉ, à publier à côté de tout score.

    Pour chaque texte d'attaque gelé, combien de témoins à DÉFAUT pourraient encore être retrouvés ?
    On mesure l'étage 1 seul : le juge ne peut que RESSERRER (un `NON` retire une retrouvaille), donc
    ce chiffre est un **MAJORANT** — exactement ce qu'on veut d'un plancher de bruit.

    Le témoin no-op est rapporté à part : une revue sans contenu le « passe », et c'est la BONNE
    réponse (se taire sur un record sain). Le compter comme une fausse retrouvaille était l'erreur de
    lecture qui faisait dire « 4/4 » là où le majorant réel des défauts est ce que rend cette fonction.
    """
    chemins = extraire_tous(dest)
    defauts = [t for t in charger() if t["genre"] == "defaut"]
    noop = [t for t in charger() if t["genre"] == "noop"][0]
    lignes = []
    for cas in cas_du_juge(avec_reponses=True):
        vises = [t for t in defauts if "*" in cas["temoins"] or t["nom"] in cas["temoins"]]
        passes = []
        for t in vises:
            with open(chemins[t["nom"]], encoding="utf-8") as fh:
                texte = fh.read()
            if recevabilite(t, cas["critiques"], texte)["recevables"]:
                passes.append(t["nom"])
        with open(chemins[noop["nom"]], encoding="utf-8") as fh:
            texte_noop = fh.read()
        noop_passe = (len(recevabilite(noop, cas["critiques"], texte_noop)["recevables"])
                      <= noop["seuil_critiques"])
        lignes.append({"cas": cas["nom"], "etage1": cas["etage1"], "juge_attendu": cas["juge"],
                       "defauts_vises": len(vises), "defauts_retrouvables": len(passes),
                       "noms": passes, "noop_passe": noop_passe})
    attaques = [l for l in lignes if l["juge_attendu"] == "NON"]
    return {"majorant_fausses_retrouvailles": sum(l["defauts_retrouvables"] for l in attaques),
            "defauts_vises_par_les_attaques": sum(l["defauts_vises"] for l in attaques),
            "cas": lignes, "mots_recopie": mots_recopie()}


def verdict_phase_temoins(dest, critiques_par_temoin, jugements=None):
    """LA sortie de la phase témoins — et le PLANCHER y voyage, dans la même structure.

    ⚠️ Il n'existe pas de chemin qui rende un score SANS son plancher. Deux appels indépendants
    auraient fini par être publiés séparément : le dépôt exige que tout ratio porte son plancher de
    bruit, et un « 4/4 » nu est précisément ce qui a tenu une passe entière le 2026-09-23.

    `critiques_par_temoin` : {nom: liste de critiques} · `jugements` : {nom: OUI|NON|INDECIDABLE}.
    """
    jugements = jugements or {}
    chemins = extraire_tous(dest)
    detail = []
    for t in charger():
        with open(chemins[t["nom"]], encoding="utf-8") as fh:
            texte = fh.read()
        detail.append(verdict_temoin(t, critiques_par_temoin.get(t["nom"], []), texte,
                                     jugements.get(t["nom"])))
    defauts = [d for d in detail if d["genre"] == "defaut"]
    mesures = [d for d in detail if d["genre"] == "noop"]
    retrouves = [d for d in defauts if d["statut"] == "RETROUVE"]
    indecidables = [d for d in defauts if d["statut"] == "INDECIDABLE"]
    # Seuls les témoins à DÉFAUT font barrière : un défaut connu non retrouvé veut dire que le
    # relecteur était aveugle, et son travail ne vaut rien. Le no-op, lui, MESURE.
    if indecidables:
        statut = "INDECIDABLE"
    elif len(retrouves) == len(defauts):
        statut = "PASSEE"
    else:
        statut = "NULLE"
    n_noop = mesures[0]["n_recevables"] if mesures else None
    # ⚠️ On compare aux témoins à défaut RETROUVÉS, pas à tous : un défaut que la revue a manqué a 0
    # critique recevable, et l'inclure ferait dire « indiscriminant » à toute revue incomplète — un
    # verdict fabriqué à partir d'une absence de mesure, exactement ce que ce dépôt traque.
    n_defauts = [d["n_recevables"] for d in defauts if d["statut"] == "RETROUVE"]
    # DISCRIMINATION : si le record cru sain produit autant de critiques recevables que les records
    # défectueux, l'instrument ne les distingue pas — et ça, c'est un verdict, pas un détail.
    if n_noop is None or not n_defauts:
        discrimine = None
    else:
        discrimine = n_noop < min(n_defauts)
    return {"score": f"{len(retrouves)}/{len(defauts)}",
            "statut": statut,
            "detail": detail,
            # Le plancher de fausses retrouvailles ET le plancher MESURÉ sur le témoin cru sain
            # voyagent tous deux avec le score : aucun chemin ne rend l'un sans les autres.
            "plancher_noop": {"temoin": mesures[0]["temoin"] if mesures else None,
                              "n_recevables": n_noop,
                              "n_recevables_par_defaut": n_defauts,
                              "discrimine": discrimine,
                              "verdict": ("NON MESURE" if discrimine is None else
                                          ("DISCRIMINE" if discrimine else "INDISCRIMINANT : le record "
                                           "cru sain produit autant de critiques recevables que les "
                                           "records défectueux"))},
            "plancher": plancher(dest)}


def _imprimer_plancher(p):
    print(f"PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie "
          f"{p['mots_recopie']} mots) : "
          f"{p['majorant_fausses_retrouvailles']}/{p['defauts_vises_par_les_attaques']}")
    for l in p["cas"]:
        marque = "attaque" if l["juge_attendu"] == "NON" else "critique JUSTE"
        print(f"  [{marque:14s}] {l['cas']:34s} défauts retrouvables {l['defauts_retrouvables']}"
              f"/{l['defauts_vises']} · no-op passé {l['noop_passe']}"
              + (f" · {l['noms']}" if l["noms"] else ""))
    print("Tout score de phase témoins se publie à côté de ce chiffre (règle du dépôt sur les ratios).")


# --------------------------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------------------------- #


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--extraire", metavar="DIR", help="écrit chaque témoin à son SHA, sous un nom neutre")
    ap.add_argument("--verifier", nargs=2, metavar=("NOM", "CRITIQUES"),
                    help="confronte les critiques (JSON) au témoin NOM")
    ap.add_argument("--extrait", metavar="FICHIER", help="le fichier relu, pour la garde anti-recopie")
    ap.add_argument("--jugement", choices=["OUI", "NON", "INDECIDABLE"],
                    help="verdict de l'étage 2 (le JUGE) pour un témoin à défaut")
    ap.add_argument("--plancher", metavar="DIR", help="mesure le plancher de fausses retrouvailles")
    ap.add_argument("--cas-du-juge", action="store_true",
                    help="les cas de calibration de l'étage 2, RÉDIGÉS : la question, pas la réponse")
    ap.add_argument("--cas-du-juge-avec-reponses", action="store_true",
                    help="les MÊMES cas avec leurs réponses — pour le VÉRIFICATEUR, jamais pour le juge")
    ap.add_argument("--questions-du-juge", action="store_true",
                    help="fichier neutre + défaut déclaré, pour les témoins à DÉFAUT seulement")
    ap.add_argument("--lister", action="store_true", help="inventaire des témoins gelés")
    ap.add_argument("--racine-valide", metavar="DIR",
                    help="le Réfutateur est-il utilisable depuis cette racine ? exit 0 ou 2")
    args = ap.parse_args(argv)
    if args.racine_valide:
        ok_racine, raison_racine = racine_valide(args.racine_valide)
        print(raison_racine)
        return 0 if ok_racine else 2
    ok, raison = roster_conforme()
    if not ok:
        print(f"roster GELÉ invalide : {raison}")
        return 2
    if args.extraire:
        for nom, chemin in extraire_tous(args.extraire).items():
            print(f"{nom} -> {chemin}")
        return 0
    if args.plancher:
        _imprimer_plancher(plancher(args.plancher))
        _imprimer_peremption(peremption_du_roster())
        return 0
    if args.cas_du_juge:
        print("Cas de calibration — RÉDIGÉS. Aucune réponse n'est publiée ici : ni le verdict attendu,")
        print("ni son explication, ni le sort de l'étage 1. Réponds à partir des critiques seules.")
        for cas in cas_du_juge():
            print(f"\ncas {cas['ref']}  témoins={cas['temoins']}")
            for c in cas["critiques"]:
                print(f"  [{c.get('prompt', '?')}] verdict={c.get('verdict', '')!r} "
                      f"preuve={c.get('preuve', '')!r}")
                print(f"      constat : {c.get('constat', '')}")
        return 0
    if args.questions_du_juge:
        for q in questions_du_juge():
            print(f"\nfichier : {q['fichier']}")
            print(f"  défaut à reconnaître : {q['defaut']}")
        return 0
    if args.cas_du_juge_avec_reponses:
        for cas in cas_du_juge(avec_reponses=True):
            print(f"{cas['ref']}  {cas['nom']:34s} étage1={cas['etage1']:10s} "
                  f"juge={cas['juge']:3s} témoins={cas['temoins']}")
            print(f"  {cas['pourquoi']}")
        return 0
    if args.verifier:
        try:
            t = par_nom(args.verifier[0])
        except KeyError as exc:
            print(exc)
            return 2
        with open(args.verifier[1], encoding="utf-8") as fh:
            texte = fh.read()
        if not texte.strip():
            print(f"{t['nom']} : NON RETROUVÉ -> revue NULLE (texte de critiques VIDE : une absence "
                  "de mesure n'est pas un silence de revue)")
            return 1
        try:
            critiques = charger_critiques(texte)
        except FormatInvalide as exc:
            print(f"{t['nom']} : INDÉCIDABLE (format non reconnu) — {exc}")
            return 2
        if args.extrait is None:
            print(f"{t['nom']} : INDÉCIDABLE — --extrait manquant, la garde anti-recopie ne peut pas "
                  "s'exécuter, et sans elle recopier une ligne du témoin suffit à le retrouver")
            return 2
        with open(args.extrait, encoding="utf-8") as fh:
            extrait = fh.read()
        r = verdict_temoin(t, critiques, extrait, args.jugement)
        print(f"{r['temoin']} ({r['genre']}) : {r['statut']} — recevables {r['n_recevables']}, "
              f"rejets {r['n_rejets']}, signal `attendu` {r['signal_attendu']} (RAPPORTÉ, hors barème)")
        # Le plancher voyage AVEC le score, jamais a cote : un verdict nu serait republiable seul.
        _imprimer_plancher(plancher(os.path.dirname(os.path.abspath(args.extrait))))
        for raison_rejet in r["rejets"]:
            print(f"  [rejet étage 1] {raison_rejet}")
        if r.get("raison"):
            print(f"  {r['raison']}")
        if r["statut"] != "RETROUVE" and t["genre"] == "defaut":
            print(f"  défaut attendu : {t['defaut']}")
        return r["code"]
    if args.lister:
        for t in charger():
            print(f"{t['nom']:34s} {t['genre']:7s} {t['sha'][:9]} gele {t['gele_le']}  "
                  f"{t['fichier']}  {t['chemin']}")
            print(f"  {t['defaut']}")
        _imprimer_peremption(peremption_du_roster())
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
