"""Porte 19 -- REGIME CITE <-> REGIME MESURE (classe E8 occ. 4, spec PM S3.5).

  python tools/check_regime_claims.py                    # cliquet : exit 1 sur tout NOUVEAU/REGRESSE
  python tools/check_regime_claims.py --report           # etat complet, exit 0
  python tools/check_regime_claims.py --update-baseline  # gele l'etat courant PAR STATUT (dette legataire)
  python tools/check_regime_claims.py --only docs/EDR/X.md
      (P2.128, E4 : un chemin qui n'est ni un record docs/EDR/<nom>.md present ni un record SUPPRIME par le
       commit en cours est REFUSE, sortie 2, AVANT toute analyse -- un --only VIDE aussi. Il rendait « OK »,
       sortie 0, sans avoir juge un seul record.)

Un record qui cite `forage_payoff = 3.0` doit citer un `results/*.json` SUIVI par git dont la valeur est
PUBLIEE -- soit dans un bloc `regime` (a N'IMPORTE QUELLE profondeur : racine, cellule, ou plus bas),
soit AILLEURS dans le fichier (ex. `arms/<bras>/<seed>/learning/reward_scale`). Un parametre publie HORS
du bloc `regime` est une INFORMATION (CONCORDE_HORS_REGIME), pas une absence : confondre les deux fabrique
un DISCORDE la ou le runner a simplement publie ailleurs -- c'est la classe E8 elle-meme (absence de
DONNEES REGARDEES -> affirmation negative de fond) appliquee a l'INSTRUMENT qui traque E8.

LE BAREME (corrige le 2026-09-24 ; rang = gravite, le PIRE parametre porte le statut du record) :

  rang 0  CONCORDE              une valeur citee est lue dans un bloc `regime`
  rang 1  CONCORDE_HORS_REGIME  elle est lue ailleurs dans le fichier -- une information, pas une absence
  rang 2  SANS_VALEUR_LUE       AUCUNE valeur n'a ete lue pour ce parametre. Le detail publie LE NOMBRE
                                de results/ lus et les CLES VOISINES qui portent le nom du parametre :
                                « voici ou j'ai regarde et ce que j'y ai vu a cote ». HORS de `OK` -- un
                                inconnu ne devient pas un vert, il cesse seulement d'affirmer. A rang
                                EGAL avec SANS_RESULTS / SANS_REGIME, les deux autres non-lectures.
  rang 3  DISCORDE              DEUX valeurs LUES et DIFFERENTES. Le mot est desormais EXACT, et le
                                detail NOMME les deux valeurs et le fichier.

Pourquoi ce bareme, et pourquoi ce n'est pas `NON_PUBLIE` : cette porte ne peut pas etablir ce que le
runner a PUBLIE, seulement ce que LUI a LU. Nommer « jamais publie » une valeur qu'il n'a pas su lire
serait un SECOND negatif fabrique par-dessus le premier. Le nom du statut dit ce que l'instrument
mesure, et rien de plus.

Mesure le 2026-09-23 (`--report`, apres correctif revue -- recherche en profondeur + hors-regime) : 300
records dans docs/EDR/, 74 citent un parametre, **10 concordent** (5 CONCORDE + 5 CONCORDE_HORS_REGIME --
double du chiffre d'avant le correctif, qui ne cherchait qu'a la racine et au 1er niveau de cellule) --
64 restent dette legataire geles PAR STATUT (53 SANS_RESULTS, 3 SANS_REGIME, 8 DISCORDE).

⚠️ RECTIFICATION (2026-09-24, P2.88). Cette docstring a affirme que les 8 DISCORDE etaient « 7 verifies
un par un contre le JSON reel, AUCUN ARTEFACT D'INSTRUMENT ». C'est FAUX, et mesurable. Reclassees
contre les JSON reels avec trois categories, les 10 lignes fautives de ces 8 DISCORDE donnent
`{'ABSENCE_CLE': 4, 'CONTRADICTION': 2, 'ILLISIBLE_PAR_L_INSTRUMENT': 4}` : **la moitie des
« absences » sont des valeurs BIEN PRESENTES**, que le lecteur a clefs n'a pas su lire --
`results/retain_compose_lr_replication.json` porte `/lr_0.02` et `/_params/lrs` (`_CELL_LR` n'accepte
que `lr=0.02|`), `results/lang_memory_diagnostic.json` porte `D1_lr0.02_ep1200`,
`results/s2_credit_retention.json` porte `/regime/frozen_phase2_lr = 0.0` (le record cite `lr = 0`
pour des poids geles : la valeur EST publiee, sous une cle QUALIFIEE), `results/td_step_pilot_r0.json`
porte `/_regime/lr_td` (une LISTE). Le correctif etait monte jusqu'au backlog et JAMAIS jusqu'ici --
or la docstring est la seule chose qu'un lecteur du module voit.

CORRECTIF DU 2026-09-24 (P2.88, tache 2b) -- CE QUI VIENT D'ETRE FERME, et comment il a ete trouve :
en faisant tourner la porte sur SON PROPRE CAS FONDATEUR, pas en la relisant. « cite 3.0, publie 1.0 »
et « cite base_metabolism, jamais lu » rendaient la MEME chaine au caractere pres -- `<p> cite [...] :
introuvable dans les results cites` -- sous le MEME mot `DISCORDE`, qui AFFIRME un desaccord. Des cinq
situations fondues, trois sont desormais separees : la contradiction reste DISCORDE et NOMME la valeur
lue ; les non-lectures (cle jamais publiee, cle publiee mais illisible, cle QUALIFIEE) passent
SANS_VALEUR_LUE en publiant ou l'instrument a regarde. Les deux restantes ne sont pas decidables ici et
sont DECLAREES ci-dessous. Mesure de la migration : les 8 DISCORDE geles se relisent 2 DISCORDE
(contradictions reelles) + 6 SANS_VALEUR_LUE -- rang 2, donc une amelioration, aucun faux rouge.

CE QU'IL NE VOIT PAS (la section que les portes 20 et 23 ont et qui manquait ici). Elle n'est plus
seulement ECRITE ICI : `CECITES` est IMPRIMEE par `--report` et par tout ECHEC, parce que le lecteur
d'une sortie n'ouvre jamais la docstring -- c'est exactement par la que le defaut ci-dessus a survecu.
  * une CITATION n'est pas forcement une PREMISSE, et `claims()` ne sait pas les distinguer : une
    PREDICTION sur un bras deliberement non couru (S2-REWARD-ABLATION, `reward_scale = 0`), un
    contrefactuel, ou le regime d'un AUTRE record cite en bloc-citation (EDR-LANG-MEMORY cite le `lr`
    de RETAIN-COMPOSE-LR) sortent comme des affirmations du record. Un DISCORDE peut donc etre un faux
    positif de l'EXTRACTEUR. Corriger `claims()` est un autre chantier ; la porte doit au moins le DIRE.
  * il ne lit que `docs/EDR/*.md`. Le graphe compte 26 records non-EDR (ADR, SDR, REF), dont 3 citent
    des `results/` : leurs affirmations de parametre ne sont vues par aucune porte. Perimetre DECLARE,
    jamais mesure comme une absence de defaut.
  * il apparie par INTERSECTION D'ENSEMBLES sur des cles EXACTES : une valeur publiee sous un autre NOM
    reste invisible. C'est maintenant RAPPORTE (les cles voisines sont nommees), jamais corrige.
  * un E8 REEL reste a traiter et il est GELE, pas resolu : `docs/EDR/107_...md` ecrit `max_ticks=80`
    quand son propre `results/lewis_evolve_nav_107.json` publie **12** (`data/max_ticks`), et son
    verdict « SUBSTRAT BLOQUE » porte sur un `p_reach` que le budget de pas borne mecaniquement. Le
    meme record annonce une trajectoire de 20 generations quand son seul results publie `generations: 2`.
    Affaire de SCIENCE, propriete du fil -- la porte le nomme desormais au lieu de le fondre.

Un record illisible est RAPPORTE et BLOQUE, jamais compte CONCORDE ni gelable par `--update-baseline`.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BASELINE = os.path.join(_ROOT, "tools", "regime_claims_baseline.json")
PARAMS = ("forage_payoff", "flip_p", "reward_scale", "lr", "n_agents", "num_agents", "max_ticks", "ticks",
          "cog_gain", "base_metabolism", "torch_episode_k")
ALIAS = {"n_agents": "num_agents", "ticks": "max_ticks"}
_NUM = r"([0-9]+(?:[.,][0-9]+)?)"
_CLAIM = re.compile(r"(?<![\w.])(" + "|".join(PARAMS) + r")\s*=\s*" + _NUM + r"(?!\w)(?!\.[0-9])")
_RESULTS = re.compile(r"`[^`]*?(results/[A-Za-z0-9_./*{},\-]+\.json)`")
_CELL_LR = re.compile(r"(?:^|\|)lr=" + _NUM + r"(?:\||$)")
# `SANS_VALEUR_LUE` reste HORS de `OK` : un inconnu ne devient pas un vert, il cesse seulement
# d'AFFIRMER un desaccord qui n'a pas ete mesure.
OK = ("SANS_PARAMETRE", "CONCORDE", "CONCORDE_HORS_REGIME")
# Ordre de gravite (pour le gel PAR STATUT, finding 2) : une dette legataire ne bloque que si son statut
# COURANT est PIRE (rang superieur) que celui gele. SANS_RESULTS, SANS_REGIME et SANS_VALEUR_LUE sont a
# rang EGAL (trois formes de « je n'ai rien pu confronter ») ; DISCORDE -- deux valeurs LUES et
# DIFFERENTES -- est toujours le pire, meme depuis l'un ou l'autre.
_RANG = {"CONCORDE": 0, "CONCORDE_HORS_REGIME": 1, "SANS_RESULTS": 2, "SANS_REGIME": 2,
         "SANS_VALEUR_LUE": 2, "DISCORDE": 3}
# Statut porte par le PIRE parametre du record. SANS_RESULTS / SANS_REGIME sont rendus EN AMONT (aucun
# fichier lisible / aucun parametre connu publie) : parvenu ici, le rang 2 est toujours SANS_VALEUR_LUE.
_STATUT_DU_RANG = {0: "CONCORDE", 1: "CONCORDE_HORS_REGIME", 2: "SANS_VALEUR_LUE", 3: "DISCORDE"}
assert all(_RANG[s] == r for r, s in _STATUT_DU_RANG.items()), "table de rangs incoherente"
STATUTS = ("SANS_PARAMETRE", "CONCORDE", "CONCORDE_HORS_REGIME", "SANS_RESULTS", "SANS_REGIME",
           "SANS_VALEUR_LUE", "DISCORDE")

# Ce que cette porte NE SAIT PAS voir, publie a cote de chaque verdict (--report et ECHEC) : un
# detecteur qui ne dit pas sa cecite laisse lire ses sorties comme si elles couvraient tout.
CECITES = (
    "une CITATION n'est pas forcement une PREMISSE. `claims()` racle la prose : il ne distingue pas la "
    "valeur du regime COURU d'une PREDICTION sur un bras deliberement NON couru (S2-REWARD-ABLATION "
    "annonce `reward_scale = 0` pour un bras jamais lance), d'un contrefactuel, ni du regime d'un AUTRE "
    "record cite en bloc-citation (EDR-LANG-MEMORY cite le `lr` de RETAIN-COMPOSE-LR). Un DISCORDE peut "
    "donc etre un faux positif de l'EXTRACTEUR et non un defaut du record : le verifier avant d'accuser.",
    "le lecteur est un lecteur A CLEFS EXACTES. Une valeur publiee sous une cle QUALIFIEE "
    "(`frozen_phase2_lr` pour `lr`), dans un NOM DE CELLULE (`D1_lr0.02_ep1200`) ou comme LISTE "
    "(`_regime/lr_td`) n'est pas lue -- d'ou `SANS_VALEUR_LUE`, qui dit « je n'ai pas lu », jamais "
    "« le runner n'a pas publie » : cette porte ne peut pas etablir la seconde affirmation.",
    "le perimetre est `docs/EDR/*.md` seul. Les 26 records non-EDR (ADR, SDR, REF) du graphe, dont 3 "
    "citent des `results/`, ne sont vus par aucune porte -- perimetre DECLARE, jamais mesure comme une "
    "absence de defaut.",
)


def _f(s):
    return float(str(s).replace(",", "."))


def _canon(p):
    return ALIAS.get(p, p)


def claims(texte):
    out = {}
    for p, v in _CLAIM.findall(texte.replace("`", "")):
        out.setdefault(_canon(p), set()).add(_f(v))
    return out


def cited_results(texte):
    return sorted(set(_RESULTS.findall(texte)))


def _developper(root, motif):
    """`{2,3,4}` et `*` -> fichiers existants ; un motif sans joker rend lui-meme (existant ou non)."""
    if not any(c in motif for c in "*{"):
        return [motif]
    m = re.search(r"\{([^{}]*)\}", motif)
    variantes = [motif.replace(m.group(0), x, 1) for x in m.group(1).split(",")] if m else [motif]
    out = []
    for v in variantes:
        if "{" in v:
            out += _developper(root, v)
        elif "*" in v:
            out += sorted(os.path.relpath(p, root).replace("\\", "/") for p in glob.glob(os.path.join(root, v)))
        else:
            out.append(v)
    return out


def _absorber(dst, regime):
    for k, v in (regime or {}).items():
        if isinstance(v, (int, float)) and not isinstance(v, bool) and k in PARAMS:
            dst.setdefault(_canon(k), set()).add(float(v))


def _sous_noeuds(node):
    """Genere `node` puis tout sous-dict/element de liste, a TOUTE profondeur -- un bloc `regime` peut
    vivre sous `arms/<bras>/<seed>/regime`, pas seulement a la racine ou dans une cellule de 1er niveau
    (trouvaille de revue : le lecteur etait aveugle en profondeur, ce qui transformait « je n'ai pas
    regarde la » en « le runner ne l'a pas publie »)."""
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _sous_noeuds(v)
    elif isinstance(node, list):
        for v in node:
            yield from _sous_noeuds(v)


def regime_values(data):
    """Union des PARAMS trouves dans tout sous-dict nomme `regime`, a N'IMPORTE QUELLE profondeur, plus
    les cles de cellule `lr=0.001|seed=2026` rencontrees a n'importe quel niveau."""
    out = {}
    if not isinstance(data, dict):
        return out
    for node in _sous_noeuds(data):
        r = node.get("regime")
        if isinstance(r, dict):
            _absorber(out, r)
        for k in node:
            if isinstance(k, str):
                m = _CELL_LR.search(k)
                if m:
                    out.setdefault("lr", set()).add(_f(m.group(1)))
    return out


def valeurs_hors_regime(data, params=PARAMS):
    """Cherche PARAMS (alias canonicalises) PARTOUT dans `data` SAUF a l'interieur d'un bloc nomme
    `regime` (deja couvert par `regime_values`) -- recursion sur dicts ET listes, cle == nom du
    parametre ou son alias. Un parametre publie ICI (ex. `arms/b_full/2026/learning/reward_scale`)
    est une INFORMATION mesuree, pas une absence : `evaluer` le classe CONCORDE_HORS_REGIME, jamais
    DISCORDE, quand la valeur citee y est retrouvee."""
    noms = set(params)
    out = {}

    def _rec(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "regime":
                    continue
                if isinstance(v, (int, float)) and not isinstance(v, bool) and k in noms:
                    out.setdefault(_canon(k), set()).add(float(v))
                _rec(v)
        elif isinstance(node, list):
            for v in node:
                _rec(v)
    _rec(data)
    return out


def cles_voisines(data, p, limite=6):
    """Les cles PUBLIEES qui portent le nom du parametre sans l'etre exactement : `frozen_phase2_lr` et
    `lr_td` pour `lr`, `base_metabolism_initial` pour `base_metabolism`, `D1_lr0.02_ep1200` pour `lr`.

    Le lecteur a clefs exactes ne sait pas les lire. Les NOMMER est ce qui transforme « je n'ai rien
    trouve » -- une affirmation de fond deguisee -- en « voici ou j'ai regarde et ce que j'y ai vu a
    cote ». Cout nul : `_sous_noeuds` parcourt deja l'arbre. L'alias INVERSE est cherche aussi (un
    record qui cite `n_agents` doit voir `num_agents_max`). Rend une liste VIDE quand il n'y en a pas :
    une absence de voisine n'est pas un verdict, c'est une absence."""
    noms = {p} | {k for k, v in ALIAS.items() if v == p}
    out = set()
    for node in _sous_noeuds(data):
        for k in node:
            if isinstance(k, str) and k not in noms and any(n in k.lower() for n in noms):
                out.add(k)
    return sorted(out)[:limite]


def evaluer(texte, lecteur, root=_ROOT):
    """`lecteur(chemin) -> dict | str | None` : un dict est le JSON lu ; une chaine ou `None` signale un
    echec de lecture (la chaine, quand elle est fournie par le lecteur reel de `analyze`, NOMME la cause
    -- « fichier absent », « JSON invalide », « non suivi par git » -- minor (iii) de la revue)."""
    cl = claims(texte)
    cites = [c for motif in cited_results(texte) for c in _developper(root, motif)]
    if not cl:
        return {"params": {}, "cites": cites, "statut": "SANS_PARAMETRE", "detail": []}
    params = {p: sorted(v) for p, v in cl.items()}
    if not cites:
        return {"params": params, "cites": cites, "statut": "SANS_RESULTS",
                "detail": ["aucun chemin results/*.json cite"]}
    regime_par_fichier, hors_par_fichier, voisines_par_fichier, raisons = {}, {}, {}, []
    for c in cites:
        data = lecteur(c)
        if isinstance(data, dict):
            regime_par_fichier[c] = regime_values(data)
            hors_par_fichier[c] = valeurs_hors_regime(data)
            voisines_par_fichier[c] = {p: cles_voisines(data, p) for p in cl}
        else:
            raisons.append(f"{c} : {data if isinstance(data, str) else 'illisible'}")
    lus = len(regime_par_fichier)
    if lus == 0:
        return {"params": params, "cites": cites, "statut": "SANS_RESULTS",
                "detail": ["aucun results/ cite n'est lisible (" + "; ".join(raisons) + ")"]}
    if not any(regime_par_fichier.values()) and not any(hors_par_fichier.values()):
        return {"params": params, "cites": cites, "statut": "SANS_REGIME",
                "detail": ["aucun bloc regime ni parametre connu publie dans les results cites"]}
    detail = []
    pire = 0    # rang du PIRE parametre du record, cf. _RANG / _STATUT_DU_RANG
    for p, vals in cl.items():
        trouve = False
        for c in cites:
            m = vals & regime_par_fichier.get(c, {}).get(p, set())
            if m:
                valeur = ",".join(str(v) for v in sorted(m))
                detail.append(f"{p}={valeur} <- {c}")
                trouve = True
                break
        if not trouve:
            for c in cites:
                m = vals & hors_par_fichier.get(c, {}).get(p, set())
                if m:
                    valeur = ",".join(str(v) for v in sorted(m))
                    detail.append(f"{p} cite {sorted(vals)} : hors du bloc regime, publie {valeur} dans {c}")
                    pire = max(pire, 1)
                    trouve = True
                    break
        if not trouve:
            # L'intersection est VIDE -- mais un ensemble vide ne dit pas POURQUOI il est vide, et
            # l'instrument tient pourtant la reponse dans `regime_par_fichier` / `hors_par_fichier`.
            # Deux situations s'y cachaient sous le meme mot et la meme chaine, au caractere pres :
            # une valeur LUE et DIFFERENTE (le cas fondateur E8 occ. 4 -- cite 3.0, publie 1.0) et une
            # valeur JAMAIS LUE. Le premier est un desaccord ; le second est une non-lecture, et la
            # nommer « discordance » etait l'erreur meme que cette porte existe pour policer.
            lu = None
            for bloc, source in (("bloc regime", regime_par_fichier), ("hors du bloc regime", hors_par_fichier)):
                for c in cites:
                    publiees = source.get(c, {}).get(p, set())
                    if publiees:
                        lu = (c, bloc, ",".join(str(v) for v in sorted(publiees)))
                        break
                if lu:
                    break
            if lu:
                c, bloc, publiees = lu
                detail.append(f"{p} cite {sorted(vals)} : les results cites publient {publiees} dans {c} ({bloc})")
                pire = max(pire, 3)
            else:
                vois = sorted({k for c in cites for k in voisines_par_fichier.get(c, {}).get(p, [])})
                ou = ("cles voisines publiees : " + ", ".join(vois[:6])) if vois else "aucune cle voisine publiee"
                detail.append(f"{p} cite {sorted(vals)} : aucune valeur lue dans {lus} results/ lu(s) ; {ou}")
                pire = max(pire, 2)
    statut = _STATUT_DU_RANG[pire]
    return {"params": params, "cites": cites, "statut": statut, "detail": detail}


def _lecteur(root):
    def lire(rel):
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            return "fichier absent"
        try:
            with open(p, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return "JSON invalide"
    return lire


def _tracked(root, rel):
    p = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=root, capture_output=True)
    return p.returncode == 0


def _dans_head(root, rel):
    """Oracle HEAD (`git cat-file -e HEAD:<rel>`), pour un seul usage : reconnaître, dans `--only`, un record
    SUPPRIMÉ par le commit en cours. Lire l'arbre de HEAD ne dépend pas de `GIT_INDEX_FILE` : hériter
    l'environnement, comme `_tracked`, est sans effet sur ce résultat."""
    return subprocess.run(["git", "cat-file", "-e", f"HEAD:{rel}"], cwd=root, capture_output=True).returncode == 0


def _est_record(rel):
    """La forme que `analyze` lit : `docs/EDR/<nom>.md`, sans sous-dossier."""
    nom = rel[len("docs/EDR/"):] if rel.startswith("docs/EDR/") else ""
    return nom.endswith(".md") and "/" not in nom and len(nom) > len(".md")


def _trier_only(only, root, dans_head=None):
    """P2.128 (E4) — `--only` confronté à ce que la porte peut JUGER, AVANT toute analyse. Mesuré le 2026-09-26
    (revue du brouillon P4.18 par agagi-40, reproduit par agagi-32) : `--only docs/EDR/N_EXISTE_PAS.md` et un
    `--only` vide rendaient « OK », sortie 0 — le filtre ne vérifiait jamais qu'il désignait un record balayé.

    Rend (désignés, supprimés, inconnus). Désigné : un record que `analyze` lit (`docs/EDR/<nom>.md`, présent
    sur le disque). Supprimé : même forme, absent du disque mais présent dans HEAD — retiré par le commit en
    cours, que le crochet passe à `--only` (filtre AMD) : ce n'est pas une faute de frappe, et un record
    supprimé n'affirme plus rien ; le refuser bloquerait toute suppression de record. Inconnu : tout le reste
    — faute de frappe, chemin hors de docs/EDR, record supprimé AVANT ce commit. `dans_head` est injectable :
    la porte 20 passe le sien, qui isole l'environnement git sur un dépôt tiers."""
    dans_head = dans_head or _dans_head
    designes, supprimes, inconnus = [], [], []
    for o in sorted(only):
        chemin = os.path.join(root, o)
        if _est_record(o) and os.path.isfile(chemin):
            designes.append(o)
        elif _est_record(o) and not os.path.exists(chemin) and dans_head(root, o):
            supprimes.append(o)
        else:
            inconnus.append(o)
    return designes, supprimes, inconnus


def _refus_only(only, inconnus):
    """Le message de refus de `--only` — commun aux portes 19 et 20."""
    if not only:
        return ("REFUS : --only VIDE -- il ne designe aucun record, et rendre OK sur un perimetre vide serait un "
                "vert qui ne mesure RIEN (E4, P2.128). Omettre --only pour juger tous les records.")
    return (f"REFUS : --only designe {len(inconnus)} chemin(s) INCONNU(S) de cette porte -- ni record "
            f"docs/EDR/<nom>.md present, ni record supprime par le commit en cours : {', '.join(inconnus)}. "
            "Corriger le chemin : un filtre qui ne designe rien rendait OK (E4, P2.128).")


def _perimetre_only(only, root, dans_head=None):
    """Applique `--only` AVANT l'analyse. Rend None pour continuer (et publie le périmètre jugé), sinon le
    code de sortie : 2 = refus nommé ; 0 = rien à juger, DIT comme tel (seulement des records supprimés)."""
    designes, supprimes, inconnus = _trier_only(only, root, dans_head)
    if not only or inconnus:
        print(_refus_only(only, inconnus))
        return 2
    if supprimes:
        print(f"--only : {len(supprimes)} record(s) SUPPRIME(S) par le commit en cours, rien a y juger : "
              f"{', '.join(supprimes)}")
    if not designes:
        print("rien a juger : --only ne designe que des records supprimes -- 0 record juge. Ce n'est pas un OK : "
              "il n'y avait rien a verifier.")
        return 0
    print(f"--only : {len(designes)} record(s) juge(s) : {', '.join(designes)}")
    return None


def analyze(root=_ROOT, suivi=None):
    """`suivi(root, rel) -> bool` injectable (les tests tournent hors depot git) ; defaut : `_tracked`,
    resolu a l'appel."""
    suivi = _tracked if suivi is None else suivi
    out, illisibles = {}, []
    d = os.path.join(root, "docs", "EDR")
    lecteur = _lecteur(root)

    def lecteur_suivi(rel):
        if not suivi(root, rel):
            return "non suivi par git"
        return lecteur(rel)
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not name.endswith(".md"):
            continue
        rel = f"docs/EDR/{name}"
        try:
            with open(os.path.join(d, name), encoding="utf-8") as fh:
                texte = fh.read()
        except (OSError, UnicodeDecodeError):
            illisibles.append(rel)
            continue
        out[rel] = evaluer(texte, lecteur_suivi, root)
    return {"records": out, "illisibles": illisibles}


def _load_baseline():
    """Rend `{fichier: statut}`. Compat ascendante : l'ancien format (liste de noms, avant le correctif
    de revue « la baseline gele un NOM, pas un STATUT ») est relu comme si tout y etait DISCORDE (le pire
    rang), donc strictement PROTECTEUR le temps d'un `--update-baseline` de rattrapage."""
    if not os.path.exists(_BASELINE):
        return {}
    with open(_BASELINE, encoding="utf-8") as fh:
        leg = json.load(fh).get("legataires", {})
    if isinstance(leg, list):
        leg = {f: "DISCORDE" for f in leg}
    return leg


def _publier_cecites():
    """Ce que la porte ne voit PAS, imprime a cote de ses verdicts -- pas seulement dans la docstring,
    que le lecteur d'une SORTIE n'ouvre jamais."""
    print("CE QUE CETTE PORTE NE VOIT PAS :")
    for c in CECITES:
        print(f"  - {c}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--root", default=_ROOT)
    args = ap.parse_args(argv)
    only = None if args.only is None else {o.replace("\\", "/") for o in args.only}
    if only is not None:                  # AVANT l'analyse : un refus est instantane et ne depend de rien d'autre
        code = _perimetre_only(only, args.root)
        if code is not None:
            return code
    a = analyze(args.root)
    fautifs = sorted(f for f, v in a["records"].items() if v["statut"] not in OK)
    for f in a["illisibles"]:
        print(f"  [ILLISIBLE -- BLOQUE, non gelable par --update-baseline] {f}")
    if args.update_baseline:
        # Garde minor (i) : un scan quasi-vide (mauvais --root, arbre partiel) ecrirait une baseline VIDE
        # qui desarmerait la porte EN SILENCE -- refuser plutot que de geler une mesure degeneree.
        if len(a["records"]) < 50:
            print(f"REFUS : seulement {len(a['records'])} record(s) scanne(s) (< 50) -- --root pointe-t-il "
                  "vers un arbre vide ou partiel ? Baseline NON ecrite (elle desarmerait la porte en silence).")
            return 1
        legataires = {f: a["records"][f]["statut"] for f in fautifs}
        with open(_BASELINE, "w", encoding="utf-8") as fh:
            json.dump({"_comment": "Records dont le statut n'est pas CONCORDE/CONCORDE_HORS_REGIME, geles PAR "
                                   "STATUT comme dette legataire (E8 occ. 4). Un legataire ne bloque que s'il "
                                   "REGRESSE vers un statut PIRE qu'au gel (tools/check_regime_claims.py, _RANG).",
                       "legataires": legataires}, fh, ensure_ascii=False, indent=2)
        print(f"baseline gelee : {len(legataires)} record(s) sur {len(a['records'])}")
        return 0
    n = {s: sum(1 for v in a["records"].values() if v["statut"] == s) for s in STATUTS}
    print(f"records : {len(a['records'])} | {n}")
    if args.report:
        for f, v in sorted(a["records"].items()):
            if v["statut"] == "SANS_PARAMETRE":
                continue
            print(f"  [{v['statut']}] {f} : {'; '.join(v['detail'])}")
        _publier_cecites()
        return 0
    base = _load_baseline()

    def _regresse(f):
        if f not in base:
            return True
        return _RANG.get(a["records"][f]["statut"], 3) > _RANG.get(base[f], 0)

    nouveaux = [f for f in fautifs if _regresse(f) and (only is None or f in only)]
    nouveaux += [i for i in a["illisibles"] if only is None or i in only]     # illisible BLOQUE : jamais gelable
    if nouveaux:
        print("ECHEC : un record cite une valeur de parametre que les results cites CONTREDISENT (DISCORDE) "
              "ou qu'aucun d'eux ne publie sous une cle lisible (SANS_VALEUR_LUE) -- E8 occ. 4 -- ou une "
              "dette legataire a REGRESSE vers un statut pire :")
        for f in nouveaux:
            v = a["records"].get(f, {"statut": "ILLISIBLE", "detail": []})
            print(f"  [NOUVEAU/REGRESSE {v['statut']}] {f} : {'; '.join(v['detail'])}")
        print("-> DISCORDE : la valeur lue est NOMMEE ci-dessus -- corriger le record, ou citer le results/ "
              "qui porte vraiment la valeur.")
        print("-> SANS_VALEUR_LUE : rien n'est affirme contre le record ; citer un results/*.json SUIVI qui "
              "publie la valeur sous une cle exacte (les cles VOISINES vues sont listees ci-dessus).")
        _publier_cecites()
        return 1
    print(f"OK : {len(fautifs)} record(s) sans regime concordant, tous legataires a un statut AU MOINS AUSSI BON "
          "qu'au gel. Aucun nouveau, aucune regression.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
