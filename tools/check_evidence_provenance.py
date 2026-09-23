"""Porte 20 -- PROVENANCE DE L'EVIDENCE : tout `results/*.json` cite par un record EDR doit EXISTER sur
disque ET etre SUIVI par git, ou etre publie par son hash (`sha256 <hex>` a cote de la citation).

  python tools/check_evidence_provenance.py                    # cliquet : exit 1 sur toute NOUVELLE paire
  python tools/check_evidence_provenance.py --report           # etat complet, exit 0
  python tools/check_evidence_provenance.py --update-baseline  # gele l'etat courant PAR (record, chemin, cause)
  python tools/check_evidence_provenance.py --only docs/EDR/X.md

Classe E27 : une conclusion dont l'evidence n'est plus rouvrable n'est pas refutable -- mesure DEUX FOIS
cette semaine sur des clones/worktrees neufs : un record citant un `results/*.json` absent du depot (ou
present seulement sur le disque d'une session) ne peut etre confronte par personne d'autre.

Reutilise `cited_results` / `_developper` de la tache 1 (`tools/check_regime_claims.py`) plutot que de
re-parser les citations.

Une absence n'est JAMAIS affirmee sans etre nommee -- trois causes distinctes, jamais fondues sous une
etiquette unique (lecon de revue de la tache 1) :
  * `absent`     -- le chemin n'existe nulle part sur le disque ;
  * `non_suivi`  -- il existe mais `git` ne le suit pas (recuperable par `git add`) ;
  * `glob_vide`  -- un motif a joker (`results/x_*.json`) qui ne developpe vers AUCUN fichier. Sans ce
    troisieme cas, `_developper` rend une liste VIDE pour un tel motif et la citation disparaitrait du
    compte sans laisser de trace -- exactement la forme (a) documentee dans CLAUDE.md (donnee absente ->
    silence, jamais une affirmation qui dit qu'on ne sait pas).
`ABSENT` est REGARDE PIRE que `NON_SUIVI` (rang 2 > 1) : un fichier non suivi reste recuperable par
`git add`, un fichier absent ne l'est pas sans savoir ou il est parti. Un legataire gele `non_suivi`
qui REGRESSE vers `absent` (ou `glob_vide`) bloque ; l'inverse (une paire qui s'ameliore) ne bloque pas.

⚠️ Defaut trouve en implementant le brief de cette porte, corrige ici (documente dans le rapport de
tache) : la fenetre de 120 caracteres qui cherche un `sha256 <hex>` APRES une citation ne s'arretait pas
a la PROCHAINE citation `results/...` -- un hash place apres une deuxieme citation « bleedait » en
arriere sur la premiere, la faisant compter comme publiee par hash alors qu'aucun hash ne lui etait
associe. `publie_par_hash` borne desormais la fenetre a la prochaine occurrence de `results/` si elle
survient avant les 120 caracteres.

Un record illisible est RAPPORTE et BLOQUE, jamais compte OK ni gelable par --update-baseline.

Mesure le 2026-09-23 (--report) : voir la sortie de la commande -- aucun chiffre n'est recopie ici, il
se perimerait (cf. la meme lecon dans check_regime_claims.py, ligne "300 records... 74 citent...").
"""
import argparse
import json
import os
import re
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.check_regime_claims import _developper, cited_results  # noqa: E402
_BASELINE = os.path.join(_ROOT, "tools", "evidence_provenance_baseline.json")
_HASH = re.compile(r"sha256[:\s]+([0-9a-f]{12,64})")
_NEXT_RESULTS = re.compile(r"\bresults/")
FENETRE = 120
# Severite : ABSENT (rien de reouvrable) est PIRE que NON_SUIVI (recuperable par `git add`) ; un motif
# a glob mort (aucune preuve nulle part) est aussi severe qu'un fichier absent.
_RANG = {"non_suivi": 1, "absent": 2, "glob_vide": 2}


def publie_par_hash(texte, chemin):
    """`sha256 <12-64 hex>` a moins de FENETRE caracteres APRES `chemin`, et avant la PROCHAINE citation
    `results/` si elle survient plus tot -- sinon un hash place a cote d'une citation VOISINE compterait
    aussi pour celle-ci (defaut reel du brief, corrige ; cf. docstring du module)."""
    i = texte.find(chemin)
    while i != -1:
        fin = i + len(chemin)
        fenetre = texte[fin: fin + FENETRE]
        prochain = _NEXT_RESULTS.search(fenetre)
        borne = prochain.start() if prochain else len(fenetre)
        if _HASH.search(fenetre[:borne]):
            return True
        i = texte.find(chemin, i + 1)
    return False


def evaluer(texte, existe, suivi, root):
    """`existe(rel) -> bool`, `suivi(rel) -> bool` injectes (le disque et git sont resolus par
    l'appelant -- `analyze` en production, un double en test)."""
    cites, glob_vides = [], set()
    for motif in cited_results(texte):
        dev = _developper(root, motif)
        if dev:
            cites.extend(dev)
        else:
            # Un motif a joker qui ne developpe vers RIEN ne doit pas disparaitre : c'est une absence
            # de preuve, pas une absence de citation.
            cites.append(motif)
            glob_vides.add(motif)
    cites = sorted(set(cites))
    par_hash = [c for c in cites if publie_par_hash(texte, c)]
    absents, non_suivis, causes = [], [], {}
    for c in cites:
        if c in par_hash:
            continue
        if c in glob_vides:
            absents.append(c)
            causes[c] = "glob_vide"
        elif not existe(c):
            absents.append(c)
            causes[c] = "absent"
        elif not suivi(c):
            non_suivis.append(c)
            causes[c] = "non_suivi"
    statut = "ABSENT" if absents else ("NON_SUIVI" if non_suivis else "OK")
    return {"cites": cites, "absents": absents, "non_suivis": non_suivis, "par_hash": par_hash,
            "statut": statut, "causes": causes}


def _tracked(root, rel):
    return subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=root,
                           capture_output=True).returncode == 0


def analyze(root=_ROOT, suivi=None):
    """`suivi(root, rel) -> bool` injectable (les tests tournent hors depot git). Defaut : `_tracked`,
    resolu a l'appel (comme check_regime_claims.analyze)."""
    suivi = _tracked if suivi is None else suivi
    out, illisibles = {}, []
    d = os.path.join(root, "docs", "EDR")
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
        out[rel] = evaluer(texte, lambda c: os.path.exists(os.path.join(root, c)),
                            lambda c: suivi(root, c), root)
    return {"records": out, "illisibles": illisibles}


def _load_baseline():
    """Rend `{fichier: {chemin: cause}}` -- une paire (record, chemin), pas un fichier entier : deux
    citations du meme record peuvent avoir des causes differentes, et geler par fichier aurait masque
    l'une des deux (lecon de revue de la tache 1)."""
    if not os.path.exists(_BASELINE):
        return {}
    with open(_BASELINE, encoding="utf-8") as fh:
        return json.load(fh).get("legataires", {})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--root", default=_ROOT)
    args = ap.parse_args(argv)
    a = analyze(args.root)
    fautes = {f: dict(v["causes"]) for f, v in a["records"].items() if v["statut"] != "OK"}
    for f in a["illisibles"]:
        print(f"  [ILLISIBLE -- BLOQUE, non gelable par --update-baseline] {f}")

    if args.update_baseline:
        # Garde de compte (lecon de la tache 1) : un scan quasi-vide (mauvais --root, arbre partiel)
        # ecrirait une baseline VIDE ou tronquee qui desarmerait la porte EN SILENCE.
        if len(a["records"]) < 50:
            print(f"REFUS : seulement {len(a['records'])} record(s) scanne(s) (< 50) -- --root pointe-t-il "
                  "vers un arbre vide ou partiel ? Baseline NON ecrite (elle desarmerait la porte en silence).")
            return 1
        with open(_BASELINE, "w", encoding="utf-8") as fh:
            json.dump({"_comment": "Paires (record, chemin results/ cite) ABSENT/NON_SUIVI/GLOB_VIDE, "
                                   "gelees PAR CAUSE comme dette legataire (E27). Un legataire ne bloque "
                                   "que s'il REGRESSE vers une cause PIRE qu'au gel "
                                   "(tools/check_evidence_provenance.py, _RANG). Aucune NOUVELLE paire.",
                       "legataires": fautes}, fh, ensure_ascii=False, indent=2, sort_keys=True)
        n_chemins = sum(len(v) for v in fautes.values())
        print(f"baseline gelee : {n_chemins} chemin(s) dans {len(fautes)} record(s)")
        return 0

    n_cites = sum(len(v["cites"]) for v in a["records"].values())
    n_absents = sum(len(v["absents"]) for v in a["records"].values())
    n_non_suivis = sum(len(v["non_suivis"]) for v in a["records"].values())
    n_hash = sum(len(v["par_hash"]) for v in a["records"].values())
    print(f"records : {len(a['records'])} | chemins cites : {n_cites} | absents : {n_absents} | "
          f"non suivis : {n_non_suivis} | publies par hash : {n_hash} | records fautifs : {len(fautes)}")

    if args.report:
        for f, ch in sorted(fautes.items()):
            detail = ", ".join(f"{c} [{cause}]" for c, cause in sorted(ch.items()))
            print(f"  [{a['records'][f]['statut']}] {f} : {detail}")
        return 0

    base = _load_baseline()
    only = None if args.only is None else {o.replace("\\", "/") for o in args.only}

    def _regresse(f, c, cause):
        gele = base.get(f, {})
        if c not in gele:
            return True
        return _RANG.get(cause, 2) > _RANG.get(gele[c], 0)

    nouveaux = {}
    for f, ch in fautes.items():
        if only is not None and f not in only:
            continue
        pires = {c: cause for c, cause in ch.items() if _regresse(f, c, cause)}
        if pires:
            nouveaux[f] = pires
    for i in a["illisibles"]:
        if only is None or i in only:
            nouveaux[i] = {"(record illisible)": "illisible"}

    if nouveaux:
        print("ECHEC : un record cite une evidence absente ou non suivie par git, ou a REGRESSE vers une "
              "cause pire qu'au gel -- personne ne pourra la rouvrir (E27) :")
        for f, ch in sorted(nouveaux.items()):
            detail = ", ".join(f"{c} [{cause}]" for c, cause in sorted(ch.items()))
            print(f"  [NOUVEAU/REGRESSE] {f} : {detail}")
        print("-> git add le results/*.json, publier son sha256 a cote de la citation, ou corriger le chemin.")
        print("   OU declarer la dette : python tools/check_evidence_provenance.py --update-baseline")
        return 1

    n_geles = sum(len(v) for v in fautes.values())
    print(f"OK : {n_geles} chemin(s) legataire(s) gele(s). Aucun nouveau, aucune regression.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
