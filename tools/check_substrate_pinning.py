"""Cliquet : une sonde qui construit une population torch ÉPINGLE-t-elle le substrat qu'elle mesure,
et son optimiseur couvre-t-il ce substrat en ENTIER ?

⚠️ Né d'un audit du 2026-09-02 (P2.27), lui-même né de la rencontre de DEUX correctifs INDÉPENDANTS
le même jour — `481117e` sur `language_memory_demand_probe` et `3b5554a` sur
`delayed_coordination_demand_probe`. Deux sessions ont corrigé le même défaut sur deux sondes sœurs
sans le savoir ; l'audit qui a suivi a trouvé **16 sondes sur 19 en défaut A et 11 sur 19 en défaut B**,
dont les DEUX qui ont gravé les deux arêtes du graphe AGI-Taxonomy.

DEUX DÉFAUTS, et ils sont indépendants :

  [A] SUBSTRAT NON ÉPINGLÉ — `TorchPopulationModel.BILINEAR` est un attribut de CLASSE, lu par
      `__init__` (`backend_torch.py:111`) ET par `_step` (`:128`). Une sonde qui ne le POSE pas hérite
      de l'ambiant du processus. Deux sondes tournant dans le même interpréteur peuvent donc mesurer
      des SUBSTRATS DIFFÉRENTS sans qu'aucun `_params` ne l'indique — et le record devient
      ininterprétable a posteriori.

  [B] OPTIMISEUR INCOMPLET — `Adam([pop.W])` laisse `U/V/W_bl` GELÉS À LEUR INIT même quand BILINEAR
      est actif. Le terme qui débloque la composition n'apprend jamais. C'est LATENT tant que le flag
      est faux, mais c'est un piège ARMÉ : il rend un nul dès que quelqu'un l'active, et ce nul ne
      mesure que l'initialisation. Un nul artefactuel ressemble à tous les autres nuls du dépôt.

⚠️ PORTÉE HONNÊTE — c'est une vérification LEXICALE, pas sémantique, et elle est faillible dans les
DEUX sens. Elle ne voit pas un épinglage fait via un helper, et elle peut crier sur un `Adam([...])`
sans rapport avec une population. C'est pourquoi elle fonctionne en CLIQUET : la dette légataire est
GELÉE dans une baseline, et seul un NOUVEAU défaut bloque. Même mécanisme que
`check_instrument_calibration.py`.

Usage :
    python tools/check_substrate_pinning.py                 # arbre entier
    python tools/check_substrate_pinning.py --only a.py b.py # scopé (hook : fichiers STAGÉS)
    python tools/check_substrate_pinning.py --update-baseline
"""
import argparse
import io
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BASELINE = os.path.join(_ROOT, "tools", "substrate_pinning_baseline.json")
_SCAN_DIRS = ("tools", os.path.join("src", "seed_ai"))

_MAKES_POP = re.compile(r"make_population\s*\(")
# ⚠️ Ne d'un FAUX POSITIF de ce cliquet, 2026-09-02 : `retain_compose_diagnostic_probe`
# EPINGLE bien le substrat, mais via un ALIAS d'import (`TPM.BILINEAR = ...`). Exiger le nom
# COMPLET de la classe faisait crier sur du code CORRECT. On accepte donc l'assignation
# d'ATTRIBUT quel que soit le porteur ; le `(?!=)` evite de confondre `==` avec `=`.
_PINS = re.compile(r"\.BILINEAR\s*=(?!=)")
_ADAM_CALL = re.compile(r"optim\.Adam\(")
# les paramètres du terme bilinéaire, tels que nommés dans `backend_torch.py:113-115`
_BILINEAR_PARAMS = re.compile(r"\bW_bl\b|\bU\b|\bV\b")
# Le poids d'une POPULATION (au minimum `pop.W`). Sensible a la casse : `pop.w_gate` n'en est pas.
_POP_WEIGHT = re.compile(r"\.W\b")


def _adam_args(src: str):
    """Texte des ARGUMENTS de chaque `optim.Adam(...)`, à parenthèses ÉQUILIBRÉES.

    ⚠️ Né d'un FAUX POSITIF de ce cliquet même, le 2026-09-02, sur un correctif CORRECT. La version
    d'origine lisait `optim\\.Adam\\(\\s*\\[([^\\]]*)\\]` — donc le PREMIER crochet SEUL — et criait sur
    l'idiome pourtant juste `Adam([pop.W] + [p for p in (pop.U, pop.V, pop.W_bl) if p is not None])`,
    dont les paramètres bilinéaires vivent dans le SECOND crochet. Un cliquet qui crie à tort est pire
    qu'absent : on apprend à l'ignorer. Cas de calibration gelé :
    `test_the_ratchet_SPARES_the_inline_concatenation_idiom`."""
    out = []
    for m in _ADAM_CALL.finditer(src):
        i, depth = m.end(), 1
        start = i
        while i < len(src) and depth:
            c = src[i]
            if c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            i += 1
        out.append(src[start:i - 1])
    return out


def _defects(src: str):
    """Renvoie l'ensemble des défauts d'un source : sous-ensemble de {'A', 'B'}.
    Vide si le fichier ne construit pas de population (hors périmètre)."""
    if not _MAKES_POP.search(src):
        return None                                    # hors périmètre — PAS « sans défaut »
    out = set()
    if not _PINS.search(src):
        out.add("A")
    # Seuls les appels dont les arguments contiennent une LISTE LITTÉRALE sont jugés : `Adam(params)`
    # ou `Adam(_full_params(pop))` construisent leur liste ailleurs, et deviner ce qu'elle contient
    # serait proxifier ce qu'on ne sait pas mesurer.
    # ⚠️ Deuxieme FAUX POSITIF corrige le meme jour : `Adam([w_throw, b_throw])` d'une sonde
    # de gate n'optimise AUCUNE population -- la juger etait hors sujet. On n'examine donc que
    # les appels dont la liste porte un POIDS DE POPULATION, seuls concernes par `U/V/W_bl`.
    if any("[" in a and _POP_WEIGHT.search(a) and not _BILINEAR_PARAMS.search(a)
           for a in _adam_args(src)):
        out.add("B")
    return out


def scan(only=None):
    """(en_defaut, hors_perimetre, examines) — `en_defaut` = {chemin relatif: ['A','B']}.

    ⚠️ `hors_perimetre` est RENDU, pas avalé : une liste blanche qui ne rapporte pas ce qu'elle écarte
    transforme son ignorance en succès. C'est la leçon des trois listes blanches silencieuses trouvées
    dans ce dépôt en deux jours."""
    en_defaut, hors, examines = {}, [], 0
    cibles = []
    if only:
        cibles = [os.path.normpath(p) for p in only if p.endswith(".py")]
    else:
        for d in _SCAN_DIRS:
            full = os.path.join(_ROOT, d)
            if not os.path.isdir(full):
                continue
            cibles += [os.path.join(d, f) for f in sorted(os.listdir(full)) if f.endswith(".py")]
    for rel in cibles:
        p = rel if os.path.isabs(rel) else os.path.join(_ROOT, rel)
        if not os.path.isfile(p):
            continue
        src = io.open(p, encoding="utf-8", errors="replace").read()
        d = _defects(src)
        key = os.path.relpath(p, _ROOT).replace("\\", "/")
        if d is None:
            hors.append(key)
            continue
        examines += 1
        if d:
            en_defaut[key] = sorted(d)
    return en_defaut, hors, examines


def _load_baseline():
    if not os.path.exists(_BASELINE):
        return {}
    with io.open(_BASELINE, encoding="utf-8") as f:
        return json.load(f).get("legataires", {})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--update-baseline", action="store_true")
    args = ap.parse_args(argv)

    if args.update_baseline:
        en_defaut, hors, examines = scan(None)          # la baseline se gèle sur l'ARBRE ENTIER
        with io.open(_BASELINE, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"_comment": "Dette LÉGATAIRE gelée (P2.27). Tout NOUVEAU défaut bloque.",
                       "legataires": en_defaut}, f, ensure_ascii=False, indent=2, sort_keys=True)
        print(f"baseline écrite : {len(en_defaut)} fichier(s) en dette, sur {examines} examiné(s)")
        return 0

    en_defaut, hors, examines = scan(args.only)
    base = _load_baseline()
    # ⚠️ On compare par DIFFÉRENCE D'ENSEMBLES, pas par égalité. Une égalité stricte crierait aussi
    # quand une sonde s'AMÉLIORE partiellement (défauts {A,B} -> {A}) : le cliquet punirait le
    # correctif. Un cliquet bloque la dette NOUVELLE, jamais la dette RÉDUITE. Cas de calibration
    # gelé : `test_the_ratchet_SPARES_a_PARTIAL_fix`.
    nouveaux = {k: sorted(set(v) - set(base.get(k, []))) for k, v in en_defaut.items()}
    nouveaux = {k: v for k, v in nouveaux.items() if v}
    a = sum(1 for v in en_defaut.values() if "A" in v)
    b = sum(1 for v in en_defaut.values() if "B" in v)
    print(f"sondes examinées : {examines} | en dette : {len(en_defaut)} "
          f"(A substrat non épinglé : {a} · B optimiseur incomplet : {b}) | "
          f"hors périmètre (ne construit pas de population) : {len(hors)}")
    if not nouveaux:
        print("OK : aucun NOUVEAU défaut d'épinglage de substrat.")
        return 0
    for k, v in sorted(nouveaux.items()):
        quoi = " + ".join({"A": "substrat NON ÉPINGLÉ (BILINEAR hérité de l'ambiant)",
                           "B": "optimiseur INCOMPLET (U/V/W_bl gelés à l'init)"}[x] for x in v)
        print(f"  [NOUVEAU] {k} -> {quoi}")
    print("\nUn substrat non épinglé rend le record ININTERPRÉTABLE a posteriori ; un optimiseur")
    print("incomplet rend un nul qui ne mesure que l'initialisation. Corriger :")
    print("  * poser `TorchPopulationModel.BILINEAR = bool(bilinear)` AVANT `make_population`,")
    print("    dans un try/finally qui le restaure, et le publier dans `_params[\"substrate\"]` ;")
    print("  * donner à l'optimiseur `[pop.W] + [p for p in (pop.U, pop.V, pop.W_bl) if p is not None]`.")
    print("OU déclarer la dette : python tools/check_substrate_pinning.py --update-baseline")
    return 1


if __name__ == "__main__":
    sys.exit(main())
