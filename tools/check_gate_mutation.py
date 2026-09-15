# -*- coding: utf-8 -*-
"""Cliquet DES CLIQUETS — chaque porte du hook doit avoir un contre-exemple qui DISCRIMINE.

LE TROU QUE CECI FERME, et il est écrit noir sur blanc dans le dépôt depuis deux mois.
`check_guard_negative_cases.py` vérifie qu'une garde `exécutable` NOMME son contre-exemple, et sa
docstring dit pourquoi elle s'arrête là :

    « Ce test discrimine-t-il ? » n'est pas une propriété lexicale ; la mesurer demanderait du test
    de mutation (casser la garde, vérifier qu'un test rougit). Plutôt que de proxifier une grandeur
    qu'on ne sait pas mesurer — l'erreur que ce dépôt paie le plus cher — le cliquet exige que
    l'AUTEUR pointe son contre-exemple.

`check_test_census.py` écrit exactement la même phrase pour sa propre limite. C'était la bonne
décision : ne pas proxifier. Mais « on ne sait pas le mesurer » était faux — on ne l'avait pas
mesuré. Ce module le mesure.

CE QU'IL VÉRIFIE, pour chaque porte du hook pre-commit — trois propriétés, toutes décidables :

1. **CONTRÔLE INTACT** — les témoins de la porte passent AU VERT sans mutation. Sans lui, une suite
   déjà rouge « tuerait » tous les mutants et le harnais annoncerait une couverture parfaite en ne
   mesurant rien. C'est le no-op apparié, à la lettre de la doctrine du dépôt.
2. **MUTANT TUÉ** — la porte, privée de son discernement par une substitution d'UNE ligne, fait
   ROUGIR au moins un témoin. Si les témoins restent verts, le contre-exemple est DÉCORATIF : il
   existe, il est nommé, il ne discrimine pas.
3. **MUTATION APPLICABLE** — le motif se trouve exactement une fois. Un motif ambigu muterait autre
   chose que ce que l'auteur croit, et le verdict porterait sur une mutation inconnue : c'est un
   ÉCHEC, jamais un succès silencieux.

POURQUOI C'ÉTAIT LA DETTE DOMINANTE. Trois fois dans la seule journée du 2026-09-09, un cliquet a
rendu un verdict FAUX-VERT : `check_backlog_freshness` a rendu `exit 0` sur un backlog VIDE puis a
invité à figer l'amputation ; la garde d'amputation écrite pour ça était elle-même INERTE (elle
lisait le mauvais dictionnaire, son plancher valait toujours 0) et a passé son propre contre-exemple ;
et neuf tests rouges dormaient dans des fichiers qu'aucun job de CI ne lançait. Le point commun des
trois : **une garde qui ne peut plus rien refuser est indiscernable, depuis ses sorties, d'une garde
qui n'a rien à refuser.** Aucune relecture ne les a vus ; seule une mutation les distingue.

⚠️ CE QU'IL NE MESURE PAS, et la limite est structurelle (cf. `tools/_mutation_plugin.py`). La
mutation vit EN MÉMOIRE — obligatoire, l'arbre est partagé — donc un témoin qui lit le SOURCE SUR
DISQUE (« le cliquet est-il branché dans le hook ? ») ne peut pas la voir, ni donc tuer le mutant.
Les mutations déclarées ici visent le COMPORTEMENT D'EXÉCUTION. Une porte dont tous les témoins
seraient textuels sortirait SURVIVANTE : le harnais crie au lieu de se taire, ce qui est le bon sens
de l'erreur, mais il faut le lire ainsi.

⚠️ ET IL NE MESURE PAS NON PLUS « toutes les mutations possibles ». Une porte est couverte par les
mutations DÉCLARÉES ici, pas par une exploration exhaustive de son espace de sabotage. Le compte
publié est donc « portes ayant au moins une mutation tuée », jamais « portes prouvées correctes ».

Usage :
  python tools/check_gate_mutation.py                  # cliquet : exit 1 si un mutant SURVIT
  python tools/check_gate_mutation.py --report         # état complet, exit 0
  python tools/check_gate_mutation.py --only 10 12     # restreint aux portes indiquées
  python tools/check_gate_mutation.py --pour-fichiers tools/check_test_census.py   # usage du hook
"""
import argparse
import io
import json
import os
import subprocess
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ------------------------------------------------------------------------------------------------
# LES MUTATIONS DÉCLARÉES. Une par comportement décisif de la porte — celui qui, s'il disparaît,
# rend la porte incapable de refuser quoi que ce soit. Le champ `motif` dit ce que la mutation
# SUPPRIME, en une phrase, pour que la lecture du rapport n'exige pas d'ouvrir le cliquet.
# ------------------------------------------------------------------------------------------------
PORTES = {
    "1": {
        "module": "tools.check_record_links",
        "titre": "graphe de records (orphelins, collisions)",
        "temoins": ["tests/sandbox/test_record_graph_completeness.py"],
        "mutations": [{
            "nom": "un record SANS porte ni arête n'est plus un orphelin",
            "avant": "        if not has_gate and not has_edge:",
            "apres": "        if False:",
            "motif": "la détection d'orphelin — tout record non raccordé passerait",
        }],
    },
    "2": {
        "module": "tools.check_instrument_calibration",
        "titre": "calibration des instruments",
        "temoins": ["tests/sandbox/test_check_instrument_calibration_collisions.py",
                    "tests/sandbox/test_check_instrument_calibration_learners.py"],
        "mutations": [
            {
                "nom": "les COLLISIONS de noms redeviennent invisibles",
                "avant": "    return {n: sorted(p) for n, p in seen.items() if len(p) > 1}",
                "apres": "    return {}",
                "motif": ("la détection des noms définis dans PLUSIEURS fichiers — déclarer calibré "
                          "`run_probe` verdirait alors deux instruments jamais testés (angle mort du "
                          "2026-09-01)"),
            },
            # P2.62 (2026-09-15) : les deux motifs du 11e élargissement, retirés UN PAR UN. Ce sont les
            # seuls motifs tolérants à l'indentation : les retirer rend les MÉTHODES d'apprentissage
            # invisibles, exactement l'état du cliquet avant P2.62 (« 0 non calibré » sur un dépôt dont
            # les quatre fonctions qui apprennent n'avaient jamais été comptées).
            {
                "nom": "les APPRENANTS redeviennent invisibles (motif learn* retiré)",
                "avant": r'    re.compile(r"^[ \t]*def\s+(learn\w*)\s*\(", re.M),',
                "apres": "    # (motif learn* retiré par la mutation)",
                "motif": ("le motif `learn*` du 11e élargissement — `learn`, `learn_episode` et "
                          "`learn_episode_bptt` du backend torch, l'apprenant que P1.6 a calibré, "
                          "sortiraient du périmètre sans qu'aucun compteur ne bouge"),
            },
            {
                "nom": "le legacy compute_policy_gradient redevient invisible",
                "avant": r'    re.compile(r"^[ \t]*def\s+(compute_policy_gradient)\s*\(", re.M),',
                "apres": "    # (motif compute_policy_gradient retiré par la mutation)",
                "motif": ("le motif `compute_policy_gradient` — l'apprenant legacy de MambaBatchModel, "
                          "actif pendant tout l'arc EVO, ne serait plus ni calibré ni compté comme dette"),
            },
        ],
    },
    "3": {
        "module": "tools.check_guard_negative_cases",
        "titre": "gardes du registre (chacune nomme son contre-exemple)",
        "temoins": ["tests/sandbox/test_guard_negative_cases.py"],
        "mutations": [{
            "nom": "plus aucune classe n'est jugée `exécutable`",
            "avant": '        if "exécutable" not in statut:',
            "apres": "        if True:",
            "motif": "le périmètre entier du cliquet — il ne regarderait plus une seule ligne",
        }],
    },
    "4": {
        "module": "tools.check_backlog_freshness",
        "titre": "fraîcheur du backlog + plancher d'amputation",
        "temoins": ["tests/sandbox/test_backlog_freshness.py"],
        "mutations": [
            {
                "nom": "LE BUG HISTORIQUE REJOUÉ : le plancher d'entrées revient à zéro",
                "avant": '        return int(json.load(f).get("plancher_entrees", 0))',
                "apres": "        return 0",
                "motif": ("exactement la première version INERTE de la garde d'amputation "
                          "(2026-09-09) : elle lisait le sous-dictionnaire `legataires`, donc le "
                          "plancher valait TOUJOURS 0 et le backlog vide passait"),
            },
            {
                "nom": "l'amputation n'est plus comparée au plancher",
                "avant": "    if n_entrees < plancher:",
                "apres": "    if False:",
                "motif": "la comparaison elle-même — un backlog passé de 2652 à 0 entrées sortirait OK",
            },
        ],
    },
    "5": {
        "module": "tools.check_preregistration_applied",
        "titre": "DV scellées effectivement mesurées",
        "temoins": ["tests/sandbox/test_preregistration_applied.py"],
        "mutations": [{
            "nom": "une grandeur scellée ABSENTE du record ne remonte plus",
            "avant": "        if missing:",
            "apres": "        if False:",
            "motif": ("la confrontation règle scellée -> record : une DV substituée après coup "
                      "(E11 occ. 4) redeviendrait invisible"),
        }],
    },
    "6": {
        "module": "tools.check_substrate_pinning",
        "titre": "épinglage du substrat",
        "temoins": ["tests/sandbox/test_substrate_pinning.py"],
        "mutations": [{
            "nom": "une sonde en défaut n'est plus rapportée",
            "avant": "        if d:\n            en_defaut[key] = sorted(d)",
            "apres": "        if False:\n            en_defaut[key] = sorted(d)",
            "motif": ("le report des défauts A/B — une sonde héritant du substrat AMBIANT, ou dont "
                      "l'optimiseur laisse U/V/W_bl gelés, passerait"),
        }],
    },
    "8": {
        "module": "tools.check_synthesis_counts",
        "titre": "comptes publiés dans les synthèses",
        "temoins": ["tests/sandbox/test_synthesis_counts.py"],
        "mutations": [{
            "nom": "un chiffre PÉRIMÉ n'est plus détecté",
            "avant": "                if attendu != reel:",
            "apres": "                if False:",
            "motif": ("la comparaison balise/recompute — « 19 classes sur 19 » resterait publiable "
                      "le jour où la 20e arrive"),
        }],
    },
    "9": {
        "module": "tools.check_bar_separation",
        "titre": "séparation de la barre (plafond de l'incapable)",
        "temoins": ["tests/sandbox/test_bar_separation.py"],
        "mutations": [{
            "nom": "une barre SANS aucune garde devient « propre »",
            "avant": '    return {"S"}',
            "apres": "    return set()",
            "motif": ("le cas fondateur lui-même : `1/K + 0.15`, jamais confronté au plafond de "
                      "l'incapable, ne serait plus signalé"),
        }],
    },
    "10": {
        "module": "tools.check_test_census",
        "titre": "recensement des tests",
        "temoins": ["tests/sandbox/test_test_census.py"],
        "mutations": [
            {
                "nom": "des tests SUPPRIMÉS ne sont plus une régression",
                "avant": "        elif current[chemin] < avant:",
                "apres": "        elif False:",
                "motif": ("le cœur d'E22 : une réécriture qui efface quatre tests rendrait la suite "
                          "plus verte, et le cliquet se tairait"),
            },
            {
                "nom": "le compte de tests devient une CONSTANTE",
                "avant": "    return len(set(_DEF_TEST.findall(src)))",
                "apres": "    return 10 ** 6",
                "motif": "la mesure elle-même — un compte constant ne peut jamais baisser",
            },
        ],
    },
    "11": {
        "module": "tools.check_control_family",
        "titre": "famille de contrôles déclarée",
        "temoins": ["tests/sandbox/test_control_family.py"],
        "mutations": [{
            "nom": "un runner SCELLÉ sans design n'est plus nu",
            "avant": '    return sorted(p for p, v in etat.items() if v["scelle"] and not v["declare"])',
            "apres": "    return []",
            "motif": ("le verdict du cliquet — les 9 runners scellés sur 12 qui ne déclaraient aucun "
                      "design repasseraient, dont celui de la 3e arête établie"),
        }],
    },
    "12": {
        "module": "tools.check_data_paths",
        "titre": "chemins de données en dur",
        "temoins": ["tests/sandbox/test_data_paths.py"],
        "mutations": [{
            "nom": "un littéral NON GELÉ n'est plus nouveau",
            "avant": "            if lit not in gelés:",
            "apres": "            if False:",
            "motif": "la comparaison à la baseline — la dette des 57 littéraux pourrait se reformer",
        }],
    },
    "13": {
        "module": "tools.check_agi_taxonomy",
        "titre": "AGI-Taxonomy (preuve complète d'une arête)",
        "temoins": ["tests/sandbox/test_agi_taxonomy_gate.py"],
        "mutations": [
            {
                "nom": "une barre SOUS le plafond de l'incapable est acceptée",
                "avant": "            elif float(bar) <= float(ceil):",
                "apres": "            elif False:",
                "motif": ("P2.15 dans le graphe : une arête déclarant `emergence_bar: 0.3167` sous "
                          "un plafond d'incapable à 0.3889 serait gravée"),
            },
            {
                "nom": "un bras intact SOUS sa propre barre est accepté",
                "avant": "        elif float(ci) < float(bar):",
                "apres": "        elif False:",
                "motif": ("M4 : la demande mesurée serait celle d'une compétence ABSENTE — un intact "
                          "au plancher repasserait la porte"),
            },
        ],
    },
    "14": {
        "module": "tools.check_fabricated_defaults",
        "titre": "défauts fabriqués (collection vide -> constante)",
        "temoins": ["tests/sandbox/test_fabricated_defaults.py"],
        "mutations": [{
            "nom": "plus aucun site n'est de la dette",
            "avant": "    return {k: v for k, v in scan(only).items() if k not in NOT_A_MEASURE}",
            "apres": "    return {}",
            "motif": ("la source unique de vérité du cliquet — le défaut à 1.0 sur un RATIO, où "
                      "l'absence prend la valeur du résultat nul, redeviendrait committable"),
        }],
    },
    "16": {
        "module": "tools.check_amputation",
        "titre": "anéantissement d'un fichier conservé (E22 généralisée)",
        "temoins": ["tests/sandbox/test_amputation.py"],
        "mutations": [{
            "nom": "l'anéantissement redevient une simple baisse",
            "avant": "        if avant > 0 and apres == 0:",
            "apres": "        if False:",
            "motif": ("la distinction ANEANTISSEMENT / baisse — un fichier vidé retomberait dans la "
                      "branche « signalé mais non bloquant », donc `PRIORITES_ET_DETTES.md` à zéro "
                      "serait de nouveau committable"),
        }],
    },
}

# ⚠️ Clé = NOM DE MODULE, et non numéro de porte : c'est ce qui permet à
# `tests/sandbox/test_gate_mutation.py` de RECOMPUTER la couverture depuis le hook lui-même. Une
# exemption indexée autrement obligerait le test à recopier une liste — et une liste recopiée se
# périme (mesuré trois fois sur des chiffres publiés de ce dépôt).
HORS_PERIMETRE = {
    "check_staged_authorship":
        "porte 7 — AVERTISSEMENT seul, non bloquante PAR DÉCISION écrite dans le hook (« un cliquet "
        "qui bloque sur l'irréparable est un cliquet qu'on désactive »). Muter une garde qui ne "
        "refuse rien ne mesure rien.",
    "check_gate_mutation":
        "porte 15 — le harnais LUI-MÊME. Ses témoins sont `tests/sandbox/test_gate_mutation.py`, dont "
        "la paire TUEE/SURVECUE le calibre directement ; et le muter EN MÉMOIRE ne l'atteindrait pas, "
        "puisqu'il mesure en lançant des SOUS-PROCESSUS qui relisent le fichier INTACT sur disque.",
}


def _ordre(pid):
    """Tri des portes : numerique quand c'est un numero, alphabetique sinon.

    ⚠️ DEFAUT REEL, trouve le jour meme par le contre-exemple gele de ce module (une porte factice
    nommee « X », fabriquee pour produire des temoins ROUGES) : `sorted(..., key=lambda kv: int(kv[0]))`
    faisait LEVER `echecs`, c.-a-d. la fonction de VERDICT elle-meme. Un harnais qui plante au lieu de
    rendre son verdict ne dit rien -- et un rien, dans un hook, se lit comme un succes."""
    return (0, int(pid), "") if pid.isdigit() else (1, 0, pid)


def _chemin_module(modname):
    return os.path.join(_ROOT, *modname.split(".")) + ".py"


def _pytest(temoins, spec=None, timeout=900):
    """Lance les témoins, avec ou sans mutation. Rend (code_de_sortie, sortie_texte).

    `-x` : une seule rougeur suffit à tuer un mutant, inutile de payer la suite du fichier."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = _ROOT + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, "-m", "pytest", "-q", "-x", "--timeout=300",
           "-p", "no:cacheprovider"]
    tmp = None
    if spec is not None:
        fd, tmp = tempfile.mkstemp(suffix=".json", prefix="agagi_mut_")
        with io.open(fd, "w", encoding="utf-8") as f:
            json.dump(spec, f, ensure_ascii=False)
        env["AGAGI_MUTATION_SPEC"] = tmp
        cmd += ["-p", "tools._mutation_plugin"]
    else:
        env.pop("AGAGI_MUTATION_SPEC", None)
    cmd += list(temoins)
    try:
        p = subprocess.run(cmd, cwd=_ROOT, env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"TIMEOUT apres {timeout}s"
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)


def etat_une_porte(pid, porte):
    """{intact: 'VERT'|'ROUGE', mutations: [{nom, verdict, code}]} pour une porte.

    Verdicts possibles d'une mutation :
      * `TUEE`      — au moins un témoin rougit : le contre-exemple DISCRIMINE ;
      * `SURVECUE`  — tous les témoins restent verts : le contre-exemple est DÉCORATIF ;
      * `INVALIDE`  — la mutation ne s'applique pas (motif absent ou ambigu), ou pytest a planté.
    ⚠️ `INVALIDE` n'est PAS un succès : une mutation qu'on ne sait pas appliquer ne mesure rien, et
    la laisser passer reproduirait exactement le défaut que ce module ferme."""
    code, sortie = _pytest(porte["temoins"])
    if code != 0:
        return {"intact": "ROUGE", "code_intact": code, "sortie": sortie[-1500:], "mutations": []}

    res = []
    for m in porte["mutations"]:
        spec = {"module": porte["module"], "chemin": _chemin_module(porte["module"]),
                "avant": m["avant"], "apres": m["apres"]}
        c, out = _pytest(porte["temoins"], spec=spec)
        if c == 1:
            verdict = "TUEE"
        elif c == 0:
            verdict = "SURVECUE"
        else:
            verdict = "INVALIDE"
        res.append({"nom": m["nom"], "motif": m["motif"], "verdict": verdict, "code": c,
                    "sortie": out[-1200:] if verdict != "TUEE" else ""})
    return {"intact": "VERT", "code_intact": 0, "sortie": "", "mutations": res}


def scan(only=None):
    """{pid: etat} sur les portes demandées (toutes par défaut)."""
    cibles = [p for p in PORTES if (only is None or p in only)]
    return {pid: etat_une_porte(pid, PORTES[pid]) for pid in sorted(cibles, key=_ordre)}


def echecs(etats):
    """VERDICT du cliquet : la liste des problèmes, jamais un booléen.

    Trois genres, et les trois bloquent : `temoins_rouges` (la mesure est nulle), `survecue` (le
    contre-exemple ne discrimine pas), `invalide` (la mutation ne s'applique pas)."""
    out = []
    for pid, e in sorted(etats.items(), key=lambda kv: _ordre(kv[0])):
        if e["intact"] == "ROUGE":
            out.append({"porte": pid, "genre": "temoins_rouges",
                        "detail": f"les temoins de la porte {pid} sont ROUGES sans aucune mutation "
                                  f"(code {e['code_intact']}) : aucun verdict de mutation n'est "
                                  f"interpretable tant qu'ils ne passent pas"})
            continue
        for m in e["mutations"]:
            if m["verdict"] == "SURVECUE":
                out.append({"porte": pid, "genre": "survecue", "mutation": m["nom"],
                            "detail": f"mutation SURVIVANTE : {m['motif']} — les temoins restent "
                                      f"VERTS alors que la porte a perdu ce discernement"})
            elif m["verdict"] == "INVALIDE":
                out.append({"porte": pid, "genre": "invalide", "mutation": m["nom"],
                            "detail": f"mutation INAPPLICABLE (code {m['code']}) : motif absent ou "
                                      f"ambigu apres refonte du cliquet — la re-declarer"})
    return out


def portes_pour_fichiers(chemins):
    """Portes concernées par des chemins stagés — pour le hook, qui ne doit payer que l'affecté."""
    voulu = set()
    for c in chemins:
        rel = c.replace("\\", "/").lstrip("./")
        for pid, p in PORTES.items():
            if rel == "/".join(p["module"].split(".")) + ".py" or rel in p["temoins"]:
                voulu.add(pid)
    return sorted(voulu, key=_ordre)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true", help="état complet, exit 0")
    ap.add_argument("--only", nargs="*", default=None, help="numéros de portes à examiner")
    ap.add_argument("--pour-fichiers", nargs="*", default=None,
                    help="chemins stagés -> ne teste que les portes concernées (usage du hook)")
    args = ap.parse_args(argv)

    only = args.only
    if args.pour_fichiers is not None:
        only = portes_pour_fichiers(args.pour_fichiers)
        if not only:
            print("aucune porte concernee par ces fichiers — rien a muter")
            return 0

    etats = scan(only)
    problemes = echecs(etats)
    n_mut = sum(len(e["mutations"]) for e in etats.values())
    n_tuees = sum(1 for e in etats.values() for m in e["mutations"] if m["verdict"] == "TUEE")

    if args.report:
        print(f"portes examinees : {len(etats)} / {len(PORTES)} declarees "
              f"({len(HORS_PERIMETRE)} hors perimetre) | mutations : {n_tuees}/{n_mut} TUEES")
        for pid, e in sorted(etats.items(), key=lambda kv: _ordre(kv[0])):
            print(f"\n  porte {pid} — {PORTES[pid]['titre']}  [temoins {e['intact']}]")
            for m in e["mutations"]:
                print(f"    [{m['verdict']:9s}] {m['nom']}")
                if m["verdict"] != "TUEE":
                    print(f"                 supprime : {m['motif']}")
        for mod, why in sorted(HORS_PERIMETRE.items()):
            print(f"\n  {mod} — HORS PERIMETRE : {why}")
        return 0

    if problemes:
        print("ECHEC : une porte du hook ne prouve pas qu'elle sait encore refuser.\n")
        for p in problemes:
            print(f"  porte {p['porte']} [{p['genre']}] {p.get('mutation', '')}")
            print(f"      {p['detail']}")
        print("\nUn contre-exemple qui ne rougit pas quand la garde est cassee est DECORATIF :")
        print("il est nomme, il existe, et il ne distingue rien. Ajouter le test qui tue la mutation.")
        return 1

    print(f"OK : {len(etats)} porte(s), {n_tuees}/{n_mut} mutation(s) TUEE(S), temoins intacts VERTS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
