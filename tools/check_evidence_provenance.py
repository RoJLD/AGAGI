"""Porte 20 -- PROVENANCE DE L'EVIDENCE : tout `results/*.json` cite par un record EDR doit EXISTER sur
disque ET etre SUIVI par git, ou etre publie par son hash (`sha256 <hex>` a cote de la citation).

  python tools/check_evidence_provenance.py                    # cliquet : exit 1 sur toute NOUVELLE paire
  python tools/check_evidence_provenance.py --report           # etat complet + comptes par HEAD, exit 0
  python tools/check_evidence_provenance.py --update-baseline  # gele l'etat courant PAR (record, chemin, cause)
  python tools/check_evidence_provenance.py --only docs/EDR/X.md

Classe E27 : une conclusion dont l'evidence n'est plus rouvrable n'est pas refutable -- mesure DEUX FOIS
cette semaine sur des clones/worktrees neufs : un record citant un `results/*.json` absent du depot (ou
present seulement sur le disque d'une session) ne peut etre confronte par personne d'autre.

Reutilise `cited_results` / `_developper` de la tache 1 (`tools/check_regime_claims.py`) plutot que de
re-parser les citations -- donc le hook re-tourne cette porte aussi quand CE module change (E4 occ. 5).
⚠️ Seules les citations ENTRE BACKTICKS sont vues (le motif de `cited_results` l'exige) : une citation
nue (sans backtick) est invisible. Mesure le 2026-09-23 : 0 citation nue dans docs/EDR -- angle mort
INACTIF aujourd'hui, pas garanti de le rester.

Une absence n'est JAMAIS affirmee sans etre nommee -- QUATRE causes distinctes, jamais fondues sous une
etiquette unique (lecon de revue de la tache 1, puis de la revue architecte de CETTE porte) :
  * `absent`     -- le chemin n'existe nulle part sur le disque ;
  * `non_suivi`  -- il existe mais `git` ne le suit pas dans l'INDEX (recuperable par `git add`) ;
  * `glob_vide`  -- un motif a joker (`results/x_*.json`) qui ne developpe vers AUCUN fichier. Sans ce
    troisieme cas, `_developper` rend une liste VIDE pour un tel motif et la citation disparaitrait du
    compte sans laisser de trace -- exactement la forme (a) documentee dans CLAUDE.md (donnee absente ->
    silence, jamais une affirmation qui dit qu'on ne sait pas).
  * `par_hash`   -- ⚠️ une DECLARATION, pas une VERIFICATION : `publie_par_hash` confronte le TEXTE (un
    `sha256 <hex>` ecrit a cote de la citation) a rien d'autre -- ni le fichier (qui peut avoir disparu),
    ni son contenu reel. Longtemps un angle mort total (rien ne gelait ces chemins, donc leur disparition
    -- l'auteur retire discretement le hash sans que le fichier redevienne suivi -- ne se voyait pas) :
    desormais gele dans la baseline comme les trois autres, donc AUDITABLE et sa regression vers une
    cause pire (le hash disparait, le fichier reste absent/non-suivi) BLOQUE comme les autres.
`ABSENT`/`GLOB_VIDE` sont REGARDES PIRES que `NON_SUIVI` (rang 2 > 1), lui-meme PIRE que `PAR_HASH`
(rang 1 > 0, un chemin non suivi reste recuperable par `git add`, un hash declare ne demande rien de
plus). Un legataire gele qui REGRESSE vers une cause de rang PIRE bloque ; l'inverse (une paire qui
s'ameliore) ne bloque pas.

⚠️ Un chemin ISSU D'UNE EXPANSION (`results/b_r{1,2}.json` -> `results/b_r1.json`) ne peut JAMAIS etre
marque `par_hash` : `publie_par_hash` cherche le CHEMIN DEVELOPPE tel quel dans le texte brut, qui ne
contient que le MOTIF non developpe -- `texte.find("results/b_r1.json")` echoue silencieusement. Rendre
`False` sans le dire serait la meme faute que le defaut (2) ci-dessous (silence plutot qu'affirmation) ;
`evaluer` le signale desormais dans `expansions`, et `--report` l'annote dans le detail plutot que de
laisser croire que la publication par hash a ete tentee et a echoue pour une autre raison.

⚠️ Deux defauts trouves en implementant le brief de la tache 2, corriges avant le premier commit :
  (1) la fenetre de 120 caracteres qui cherche un `sha256 <hex>` APRES une citation ne s'arretait pas a
      la PROCHAINE citation `results/...` -- un hash place apres une deuxieme citation « bleedait » en
      arriere sur la premiere. `publie_par_hash` borne desormais la fenetre a la prochaine occurrence de
      `results/` si elle survient avant les 120 caracteres.
  (2) un motif a joker qui developpe vers RIEN disparaissait du compte (cf. `glob_vide` ci-dessus).
Et un troisieme, trouve par la revue architecte APRES le premier commit (voir le rapport de correction
dans task-2-report.md) : `_tracked` n'avait AUCUN temoin qui exerce le VRAI oracle git -- les cinq tests
`non_suivi` du premier tir injectaient tous `suivi=lambda: False`, donc `_tracked` pouvait etre remplace
par `return True` sans qu'un seul test ne rougisse. `test_p6_*` construit desormais un depot git JETABLE
reel (aucun monkeypatch de `_tracked`/`_dans_head`) pour fermer ce trou -- ce qui a REVELE un quatrieme
defaut (le premier essai de commit de cette meme correction a echoue dessus), CORRIGE par `_env_pour` :
isoler `GIT_*` INCONDITIONNELLEMENT est FAUX -- ca marche pour un depot TIERS (le jetable de test) mais
c'est une REGRESSION sur le depot COURANT pendant un commit, ou `GIT_INDEX_FILE` DOIT au contraire etre
HERITE (voir `_env_pour` pour le mecanisme complet et l'experience qui l'a prouve).

`_tracked` teste l'INDEX (`git ls-files`) : c'est le bon oracle POUR LE HOOK, ou un fichier ajoute dans
LE MEME commit doit compter comme suivi -- et ou un fichier seulement STAGE par une AUTRE session sur
l'arbre PARTAGE doit rester non_suivi (l'INDEX AMBIANT le confondrait avec suivi ; `_env_pour` heritant
`GIT_INDEX_FILE` sur le depot courant juge le BON index, celui du commit, pas celui de l'arbre). `_dans_
head` teste HEAD (`git cat-file -e HEAD:<chemin>`) : un chemin peut etre `suivi` (dans l'index) sans
etre `dans_head` (juste stage, pas encore committe) -- c'est PUREMENT diagnostique (publie en `--report`
uniquement, ne bloque rien) : un clone qui ne recupere que les commits (jamais l'index de qui que ce
soit) ne voit que HEAD.

⚠️ « Combien de chemins cites ? » n'a PAS UNE reponse : un motif a accolade/joker (`results/lock_001_
pred2_r{2,3,4}.json`) est UN motif brut qui developpe vers PLUSIEURS chemins. Trois comptes distincts,
tous publies, jamais fondus (E8 applique au RAPPORT lui-meme, trouve par la revue architecte) :
  * motifs cites          -- citations BRUTES distinctes (avant expansion), dedupliquees sur tout le corpus ;
  * chemins distincts      -- chemins APRES expansion, dedupliques sur tout le corpus (un meme chemin peut
    etre cite par plusieurs records, ou par plusieurs motifs du meme record) ;
  * paires record x chemin -- somme, par record, du nombre de chemins developpes cites CE record (c'est
    l'unite de la baseline : deux records qui citent le meme chemin comptent pour DEUX paires).
Un grep litteral sur `results/` compte quelque chose de plus proche de « motifs » que de « chemins » ou
« paires », car les motifs a accolade/joker s'y developpent en plusieurs fichiers PRESENTS sur le disque.

Un record illisible est RAPPORTE et BLOQUE, jamais compte OK ni gelable par --update-baseline.

Mesure le 2026-09-23 (--report) : voir la sortie de la commande -- aucun chiffre n'est recopie ici, il
se perimerait (cf. la meme lecon dans check_regime_claims.py, ligne "300 records... 74 citent...").

CE QU'IL NE VOIT PAS (perimetre DECLARE, 2026-09-24) : cette porte ne lit que `docs/EDR/*.md`. Le graphe
compte 26 records non-EDR (ADR, SDR, REF), dont 3 citent des `results/` : leur evidence n'est
verifiee par AUCUNE porte. Meme perimetre que la porte 19, et il n'etait declare nulle part --
un perimetre tu se lit comme une absence de defaut.
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
_HASH = re.compile(r"sha256[:\s]+([0-9a-f]{12,64})", re.I)
_NEXT_RESULTS = re.compile(r"\bresults/")
FENETRE = 120
# Severite : PAR_HASH (declare, rien a faire de plus) < NON_SUIVI (recuperable par `git add`) <
# ABSENT/GLOB_VIDE (aucune preuve nulle part, rang egal -- deux formes symetriques de "rien a lire").
_RANG = {"par_hash": 0, "non_suivi": 1, "absent": 2, "glob_vide": 2}


def publie_par_hash(texte, chemin):
    """`sha256 <12-64 hex>` a moins de FENETRE caracteres APRES `chemin`, et avant la PROCHAINE citation
    `results/` si elle survient plus tot -- sinon un hash place a cote d'une citation VOISINE compterait
    aussi pour celle-ci (defaut (1) du module, corrige).

    ⚠️ DECLARATION, pas VERIFICATION : ne confronte le hash a RIEN d'autre que le texte lui-meme -- ni
    l'existence du fichier, ni son contenu. Et ne peut JAMAIS matcher un `chemin` ISSU D'UNE EXPANSION
    (`results/b_r{1,2}.json` -> `results/b_r1.json`) : `texte.find(chemin)` ne trouve que le chemin
    LITTERAL, or seul le motif NON developpe apparait dans le texte brut. `evaluer` le signale via
    `expansions` plutot que de laisser ce `False` silencieux se confondre avec « pas de hash cite »."""
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
    """`existe(rel) -> bool`, `suivi(rel) -> bool` injectes (le disque et l'INDEX git sont resolus par
    l'appelant -- `analyze` en production via `_tracked`, un double en test).

    Rend `motifs` (citations BRUTES, avant expansion), `cites` (chemins APRES expansion), `expansions`
    (le sous-ensemble de `cites` qui n'a PAS de forme litterale dans le texte -- cf. `publie_par_hash`),
    et `causes` qui couvre desormais LES QUATRE causes, y compris `par_hash` (pour l'audit/le gel -- voir
    docstring du module)."""
    motifs = sorted(set(cited_results(texte)))
    cites, glob_vides, expansions = [], set(), set()
    for motif in motifs:
        dev = _developper(root, motif)
        if dev:
            cites.extend(dev)
            if dev != [motif]:
                expansions.update(dev)
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
            causes[c] = "par_hash"
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
    return {"motifs": motifs, "cites": cites, "absents": absents, "non_suivis": non_suivis,
            "par_hash": par_hash, "statut": statut, "causes": causes, "expansions": sorted(expansions)}


# Le helper vit dans `tools/_git_env.py` (partage avec la porte 15 ; sa docstring dit quand isoler,
# quand heriter). Le nom `_env_isole` reste pour les temoins, qui visent un depot JETABLE (tiers).
# Dans CE module, la decision isoler/heriter selon le depot vise appartient a `_env_pour`.
from tools._git_env import env_isole as _env_isole  # noqa: E402


def _env_pour(root):
    """LA decision d'isolation, rendue OBSERVABLE (testee directement, sans mocker subprocess) --
    corrige une REGRESSION trouvee en re-revue le 2026-09-23 : `_tracked` isolait INCONDITIONNELLEMENT,
    y compris quand `root` EST le depot courant pendant un commit.

    `root == _ROOT` (le depot COURANT, celui du commit en cours) -> `None`, pour HERITER l'environnement
    ambiant -- notamment `GIT_INDEX_FILE`, que git fixe pour ses hooks pendant un `git commit --
    <pathspec>` et qui pointe l'index TEMPORAIRE de CE commit. C'est exactement ce qu'il faut juger
    (lecon de la porte 4, deja dans CLAUDE.md : « la porte juge ce qui SERA committe, pas le disque » --
    et ici, pas l'index AMBIANT non plus). RETIRER la variable ferait retomber sur `.git/index` AMBIANT,
    qui peut porter le travail STAGE-MAIS-PAS-COMMITTE d'une AUTRE session sur l'arbre PARTAGE --
    experience reproduite par le re-reviewer : session B stage `results/y.json` sans committer ; session
    A commite `docs/EDR/X.md` qui le cite ; avec l'INDEX AMBIANT (isolation inconditionnelle, le bug),
    `y.json` ressort SUIVI alors qu'aucun clone du commit de A ne le verra -- un FAUX PASS silencieux.

    `root != _ROOT` (un depot TIERS -- jetable de test, clone, submodule) -> `_env_isole()`
    (`tools/_git_env.env_isole` ; 2026-09-23 : un `git commit` jetable y echouait en « invalid
    object »), car ce depot n'a RIEN a voir avec le commit en cours : HERITER `GIT_INDEX_FILE` lui
    ferait lire/ecrire l'index d'un AUTRE depot (le defaut ORIGINAL, trouve au premier essai de
    commit de cette correction).

    `os.path.normcase` en plus de `realpath` : ce depot tourne sous Windows, ou la casse du lecteur
    (`C:` vs `c:`) ne doit pas faire passer le depot courant pour un depot tiers."""
    ici = os.path.normcase(os.path.realpath(root))
    courant = os.path.normcase(os.path.realpath(_ROOT))
    return None if ici == courant else _env_isole()


def _tracked(root, rel):
    """Oracle INDEX : `git ls-files` voit un fichier `git add`-e, meme pas encore committe -- c'est le
    bon oracle POUR LE HOOK (un fichier ajoute dans LE MEME commit doit compter comme suivi). Temoin
    REEL (pas de monkeypatch) : `test_p6_tracked_a_un_temoin_REEL_sur_un_depot_git_jetable`. La decision
    d'environnement (heriter sur le depot courant, isoler sur un depot tiers) est dans `_env_pour`."""
    return subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=root,
                           capture_output=True, env=_env_pour(root)).returncode == 0


def _dans_head(root, rel):
    """Oracle HEAD : `git cat-file -e HEAD:<rel>` -- distinct de `_tracked` (l'INDEX). Un chemin peut
    etre `suivi` (ajoute a l'index) sans etre `dans_head` (juste stage, pas encore committe) : un clone
    qui ne recupere que les commits ne voit que HEAD. PUREMENT diagnostique -- publie en `--report`
    uniquement, ne participe a AUCUN statut ni AUCUNE decision de blocage.

    `HEAD:<rel>` lit directement l'objet ARBRE au commit HEAD (base d'objets), jamais l'INDEX -- donc
    INSENSIBLE a `GIT_INDEX_FILE` : que `_env_pour` isole ou herite ne changerait rien au resultat ICI.
    On l'applique quand meme, par UNIFORMITE avec `_tracked` (meme regle pour tout appel git visant
    `root` dans ce module) et en DEFENSE contre un `GIT_DIR` heritee sur un depot TIERS -- meme si ce
    n'est pas le mecanisme du defaut reproduit."""
    return subprocess.run(["git", "cat-file", "-e", f"HEAD:{rel}"], cwd=root,
                           capture_output=True, env=_env_pour(root)).returncode == 0


def analyze(root=_ROOT, suivi=None):
    """`suivi(root, rel) -> bool` injectable (les tests tournent hors depot git, ou veulent forcer un
    scenario precis). Defaut : `_tracked`, resolu a l'appel (comme check_regime_claims.analyze) -- un
    appel SANS `suivi=` exerce le VRAI oracle git."""
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
    l'une des deux (lecon de revue de la tache 1). Inclut desormais la cause `par_hash` (revue
    architecte, point 6) : un chemin declare par hash est gele et auditable comme les trois autres."""
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

    # a_geler : TOUTES les paires causees (y compris par_hash) -- c'est ce que la baseline gele, pour
    # que la disparition d'une declaration par hash soit AUDITABLE (point 6 de la revue).
    a_geler = {f: dict(v["causes"]) for f, v in a["records"].items() if v["causes"]}
    # fautes : seulement les paires qui rendent le record BLOQUANT (par_hash ne bloque jamais seul).
    fautes = {f: {c: v["causes"][c] for c in (v["absents"] + v["non_suivis"])}
              for f, v in a["records"].items() if v["statut"] != "OK"}

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
            json.dump({"_comment": "Paires (record, chemin results/ cite) ABSENT/NON_SUIVI/GLOB_VIDE/PAR_HASH, "
                                   "gelees PAR CAUSE comme dette legataire ou declaration auditable (E27). Un "
                                   "legataire ne bloque que s'il REGRESSE vers une cause de rang PIRE qu'au gel "
                                   "(tools/check_evidence_provenance.py, _RANG). Aucune NOUVELLE paire absente/"
                                   "non suivie/a glob vide.",
                       "legataires": a_geler}, fh, ensure_ascii=False, indent=2, sort_keys=True)
        n_chemins = sum(len(v) for v in a_geler.values())
        n_hash_geles = sum(1 for v in a_geler.values() for c in v.values() if c == "par_hash")
        print(f"baseline gelee : {n_chemins} chemin(s) dans {len(a_geler)} record(s) "
              f"(dont {n_hash_geles} publie(s) par hash)")
        return 0

    # Comptes par UNITE (point 2 de la revue) : motifs BRUTS != chemins developpes DISTINCTS != paires
    # record x chemin (l'unite de la baseline). Et comptes par CAUSE (point 3) : `absents` fondait
    # `absent` et `glob_vide` sous une seule etiquette -- E8 applique au rapport lui-meme.
    tous_motifs, tous_chemins, n_paires = set(), set(), 0
    n_absent = n_glob_vide = n_non_suivi = n_hash = 0
    for v in a["records"].values():
        tous_motifs.update(v["motifs"])
        tous_chemins.update(v["cites"])
        n_paires += len(v["cites"])
        for c, cause in v["causes"].items():
            if cause == "absent":
                n_absent += 1
            elif cause == "glob_vide":
                n_glob_vide += 1
            elif cause == "non_suivi":
                n_non_suivi += 1
            elif cause == "par_hash":
                n_hash += 1
    print(f"records : {len(a['records'])} | motifs cites : {len(tous_motifs)} | "
          f"chemins distincts : {len(tous_chemins)} | paires record×chemin : {n_paires} | "
          f"absents : {n_absent} | non suivis : {n_non_suivi} | glob vides : {n_glob_vide} | "
          f"publies par hash : {n_hash} | records fautifs : {len(fautes)}")

    if args.report:
        # Point 4 de la revue : "0 non suivis" mesure contre l'INDEX (git add suffit) peut masquer un
        # arbre ou une douzaine de results/*.json sont STAGES mais jamais COMMITES -- un clone qui ne
        # recupere que HEAD ne les voit pas. Diagnostique seulement : ne participe a AUCUN blocage.
        n_head_absent = sum(1 for v in a["records"].values() for c in v["cites"]
                             if not _dans_head(args.root, c))
        print(f"contre HEAD : {n_head_absent} chemin(s) cite(s) absent(s) du dernier commit "
              "(git cat-file -e HEAD:<chemin> ; distinct de 'suivi', qui teste l'INDEX -- un chemin "
              "stage dans CE commit est suivi mais peut ne pas encore etre dans HEAD)")
        for f, ch in sorted(fautes.items()):
            detail = ", ".join(
                f"{c} [{cause}]" + (" [issu d'une expansion -- hash inapplicable sur ce chemin]"
                                     if c in a["records"][f]["expansions"] else "")
                for c, cause in sorted(ch.items()))
            print(f"  [{a['records'][f]['statut']}] {f} : {detail}")
        if n_hash:
            print(f"  publies par hash (GELES, DECLARATIFS -- non verifies contre le fichier reel) : {n_hash}")
            for f, v in sorted(a["records"].items()):
                if v["par_hash"]:
                    print(f"    {f} : {', '.join(v['par_hash'])}")
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
        print("   Un sha256 declare est GELE dans la baseline et reste auditable (cause par_hash) -- ce")
        print("   n'est PAS une verification (le fichier peut avoir disparu), seulement une declaration.")
        print("   OU declarer la dette : python tools/check_evidence_provenance.py --update-baseline")
        return 1

    n_geles = sum(len(v) for v in fautes.values())
    print(f"OK : {n_geles} chemin(s) legataire(s) gele(s). Aucun nouveau, aucune regression.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
