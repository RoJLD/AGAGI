"""Porte 19 -- REGIME CITE <-> REGIME MESURE (classe E8 occ. 4, spec PM S3.5).

  python tools/check_regime_claims.py                    # cliquet : exit 1 sur tout NOUVEAU/REGRESSE
  python tools/check_regime_claims.py --report           # etat complet, exit 0
  python tools/check_regime_claims.py --update-baseline  # gele l'etat courant PAR STATUT (dette legataire)
  python tools/check_regime_claims.py --only docs/EDR/X.md

Un record qui cite `forage_payoff = 3.0` doit citer un `results/*.json` SUIVI par git dont la valeur est
PUBLIEE -- soit dans un bloc `regime` (a N'IMPORTE QUELLE profondeur : racine, cellule, ou plus bas),
soit AILLEURS dans le fichier (ex. `arms/<bras>/<seed>/learning/reward_scale`). Un parametre publie HORS
du bloc `regime` est une INFORMATION (CONCORDE_HORS_REGIME), pas une absence : confondre les deux fabrique
un DISCORDE la ou le runner a simplement publie ailleurs -- c'est la classe E8 elle-meme (absence de
DONNEES REGARDEES -> affirmation negative de fond) appliquee a l'INSTRUMENT qui traque E8.

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

CE QU'IL NE VOIT PAS (la section que les portes 20 et 22 ont et qui manquait ici) :
  * `DISCORDE` FOND CINQ SITUATIONS sous un seul mot, avec la meme chaine de detail au caractere pres,
    et ce mot affirme la pire : (a) premisse reellement FAUSSE -- le cas fondateur EDR-GRAB-COST ;
    (b) cle jamais publiee ; (c) cle PUBLIEE mais illisible par le lecteur a clefs ; (d) cle publiee
    QUALIFIEE (`frozen_phase2_lr` pour `lr`) ; (e) faux positif de l'EXTRACTEUR -- `reward_scale = 0`
    cite a l'interieur d'une PREDICTION dans S2-REWARD-ABLATION. Un statut nomme `NON_PUBLIE` serait un
    SECOND negatif fabrique par-dessus le premier : cet instrument ne peut pas etablir ce que le runner
    a PUBLIE, seulement ce que LUI a LU.
  * il ne lit que `docs/EDR/*.md`. Le graphe compte 26 records non-EDR (ADR, SDR, REF), dont 3 citent
    des `results/` : leurs affirmations de parametre ne sont vues par aucune porte. Perimetre DECLARE,
    jamais mesure comme une absence de defaut.
  * il apparie par INTERSECTION D'ENSEMBLES : une valeur citee dans la prose et publiee ailleurs sous
    un autre NOM reste invisible, et il ne nomme jamais la valeur qu'il a pourtant LUE.
  * un E8 REEL peut sortir sous ce meme mot sans etre distingue : `docs/EDR/107_...md:21` annonce une
    trajectoire de 20 generations quand son seul results publie `generations: 2`.

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
OK = ("SANS_PARAMETRE", "CONCORDE", "CONCORDE_HORS_REGIME")
# Ordre de gravite (pour le gel PAR STATUT, finding 2) : une dette legataire ne bloque que si son statut
# COURANT est PIRE (rang superieur) que celui gele. SANS_RESULTS et SANS_REGIME sont a rang EGAL (deux
# formes symetriques de « je n'ai rien pu confronter ») ; DISCORDE est toujours le pire, meme depuis l'un
# ou l'autre.
_RANG = {"CONCORDE": 0, "CONCORDE_HORS_REGIME": 1, "SANS_RESULTS": 2, "SANS_REGIME": 2, "DISCORDE": 3}


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
    regime_par_fichier, hors_par_fichier, raisons = {}, {}, []
    for c in cites:
        data = lecteur(c)
        if isinstance(data, dict):
            regime_par_fichier[c] = regime_values(data)
            hors_par_fichier[c] = valeurs_hors_regime(data)
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
    pire = 0    # 0 CONCORDE, 1 CONCORDE_HORS_REGIME, 3 DISCORDE (rang du pire parametre du record)
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
            detail.append(f"{p} cite {sorted(vals)} : introuvable dans les results cites")
            pire = max(pire, 3)
    statut = "DISCORDE" if pire >= 3 else ("CONCORDE_HORS_REGIME" if pire >= 1 else "CONCORDE")
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--root", default=_ROOT)
    args = ap.parse_args(argv)
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
    n = {s: sum(1 for v in a["records"].values() if v["statut"] == s)
         for s in ("SANS_PARAMETRE", "CONCORDE", "CONCORDE_HORS_REGIME", "SANS_RESULTS", "SANS_REGIME", "DISCORDE")}
    print(f"records : {len(a['records'])} | {n}")
    if args.report:
        for f, v in sorted(a["records"].items()):
            if v["statut"] == "SANS_PARAMETRE":
                continue
            print(f"  [{v['statut']}] {f} : {'; '.join(v['detail'])}")
        return 0
    base = _load_baseline()
    only = None if args.only is None else {o.replace("\\", "/") for o in args.only}

    def _regresse(f):
        if f not in base:
            return True
        return _RANG.get(a["records"][f]["statut"], 3) > _RANG.get(base[f], 0)

    nouveaux = [f for f in fautifs if _regresse(f) and (only is None or f in only)]
    nouveaux += [i for i in a["illisibles"] if only is None or i in only]     # illisible BLOQUE : jamais gelable
    if nouveaux:
        print("ECHEC : un record cite un parametre introuvable dans les results cites (regime OU ailleurs) "
              "-- E8 occ. 4 -- ou une dette legataire a REGRESSE vers un statut pire :")
        for f in nouveaux:
            v = a["records"].get(f, {"statut": "ILLISIBLE", "detail": []})
            print(f"  [NOUVEAU/REGRESSE {v['statut']}] {f} : {'; '.join(v['detail'])}")
        print("-> citer le results/*.json SUIVI qui porte la valeur (regime ou ailleurs), ou corriger la valeur.")
        return 1
    print(f"OK : {len(fautifs)} record(s) sans regime concordant, tous legataires a un statut AU MOINS AUSSI BON "
          "qu'au gel. Aucun nouveau, aucune regression.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
