"""Garde-fou de CALIBRATION DES INSTRUMENTS — règle à cliquet, calquée sur `check_record_links.py`.

Problème visé (REF-EXPERIMENT-PREFLIGHT) : ce dépôt mesure beaucoup, sur un système sans vérité-terrain,
avec des instruments jamais calibrés. Conséquence vécue : un bug d'aliasing mémoire a PRODUIT un résultat
complet (dose-réponse, corrélations, contrôle négatif) qui a tenu une passe entière — aucune mesure
n'était confrontée à une réponse connue.

RÈGLE À CLIQUET : les instruments LÉGATAIRES non calibrés sont tolérés via un baseline gelé, mais
AUCUN NOUVEL instrument non calibré ne doit apparaître. C'est le même mécanisme qui a fait tenir
l'hygiène du graphe de records — dette existante gelée, dette nouvelle bloquée.

BOUCLE D'AUTO-AMÉLIORATION : chaque bug d'instrument trouvé en revue devient un cas de calibration
(`tests/sandbox/test_instrument_calibration.py`). La suite croît de façon MONOTONE avec les erreurs
découvertes -> un bug corrigé ne peut plus repasser silencieusement.

Ce qu'est un « instrument » ici : une fonction qui produit une AFFIRMATION SCIENTIFIQUE (un verdict, un
ratio, une survie, un taux) à partir d'un monde ou d'un génome. Détection par HEURISTIQUE de nommage
(documentée et faillible — elle ratisse large exprès, un faux positif se déclare dans le baseline).

Usage :
  python tools/check_instrument_calibration.py                    # cliquet : exit 1 sur tout NOUVEL instrument non calibré
  python tools/check_instrument_calibration.py --report           # état complet, exit 0
  python tools/check_instrument_calibration.py --update-baseline  # gèle l'état courant comme dette légataire
"""
import argparse
import ast
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_ROOT, "tools")
_BASELINE = os.path.join(_ROOT, "tools", "instrument_calibration_baseline.json")
_CALIB_TESTS = os.path.join(_ROOT, "tests", "sandbox", "test_instrument_calibration.py")

# Heuristique de nommage : formes qui produisent une affirmation scientifique.
_INSTRUMENT_PATTERNS = (
    re.compile(r"^def\s+(\w*verdict\w*)\s*\(", re.M),
    re.compile(r"^def\s+(measure_\w+)\s*\(", re.M),
    re.compile(r"^def\s+(\w+_survival_eras)\s*\(", re.M),
    re.compile(r"^def\s+(run_\w*(?:probe|diagnostic|ablation|validation)\w*)\s*\(", re.M),
    # Élargi le 2026-07-21 : le motif précédent ratissait moins large que sa docstring ne le promettait.
    # Trouvé en y tombant moi-même — `run_linear_sanity` (qui produit oracle/plancher/ratio/verdict) est
    # entré dans le dépôt SANS que le cliquet bronche. Le pire angle mort était `run_cog_demand_map` :
    # c'est la sonde qui a produit le ratio 21.05 publié par EDR-S2-009, invisible depuis le début.
    re.compile(r"^def\s+(run_\w*(?:sanity|control|oracle|floor|map|sweep)\w*)\s*\(", re.M),
)


# Répertoires balayés. ⚠️ `src/seed_ai` ajouté le 2026-07-21 : le scan ne regardait QUE `tools/`, donc
# les fonctions de verdict vivant dans `src/` étaient invisibles — ni calibrées, ni comptées comme dette.
# Le cas qui l'a révélé : `verdict_cognition_body` (`src/seed_ai/s2_stats.py`), qui produit le verdict
# FONDATEUR `champion_body` sur lequel repose la §2 de SPECIFICATION_10ANS. Second angle mort du cliquet
# trouvé le même jour (le premier était le motif de nommage) — l'heuristique est faillible sur DEUX axes :
# ce qu'elle cherche, et OÙ elle le cherche.
_SCAN_DIRS = ("tools", os.path.join("src", "seed_ai"))


def scan_instruments():
    """{nom_instrument: chemin_relatif} sur les répertoires de `_SCAN_DIRS`."""
    found = {}
    for rel in _SCAN_DIRS:
        d = os.path.join(_ROOT, rel)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".py") or fn.startswith("check_"):
                continue
            try:
                src = open(os.path.join(d, fn), encoding="utf-8").read()
            except OSError:
                continue
            for pat in _INSTRUMENT_PATTERNS:
                for name in pat.findall(src):
                    found.setdefault(name, os.path.join(rel, fn).replace("\\", "/"))
    return found


def scan_calibrated():
    """Instruments DÉCLARÉS calibrés par la suite, via un dict `CALIBRATED` explicite.

    ⚠️ CORRIGÉ le 2026-07-21 — l'implémentation précédente comptait un instrument calibré dès que son
    NOM apparaissait en SUBSTRING dans le fichier de tests. Défaut vérifié : `_torch_survival_eras`
    passait pour calibré alors que **seule sa branche `ablate_kind='grab_off'`** l'était (les 4 cas
    passent par un helper qui hardcode ce mode) ; la branche `'perception'`, qui produit les ratios
    publiés de WARM-001 (1.6→2.1) et WARM-003 (5.04), n'avait AUCUN cas. C'est la classe **E4** du
    registre — une vérification qui ne peut pas échouer — dans l'outil écrit pour l'empêcher.

    La clé de calibration est donc **(fonction, branche)**, DÉCLARÉE par le test, jamais déduite du nom.
    Un instrument à branches doit lister celles qui sont couvertes ; `["*"]` = pas de branche."""
    if not os.path.exists(_CALIB_TESTS):
        return set()
    src = open(_CALIB_TESTS, encoding="utf-8").read()
    m = re.search(r"^CALIBRATED\s*=\s*(\{.*?^\})", src, re.M | re.S)
    if not m:
        return set()
    try:
        declared = ast.literal_eval(m.group(1))
    except (ValueError, SyntaxError):
        return set()
    known = scan_instruments()
    out = set()
    for name, branches in (declared or {}).items():
        if name not in known:
            continue                                  # déclaration périmée : ignorée, pas de faux vert
        if isinstance(branches, (list, tuple, set)) and branches:
            out.add(name)
    return out


def scan_declared_branches():
    """{instrument: [branches déclarées]} — pour le rapport, afin de rendre visible une couverture
    PARTIELLE (ex. `grab_off` couvert, `perception` non)."""
    if not os.path.exists(_CALIB_TESTS):
        return {}
    src = open(_CALIB_TESTS, encoding="utf-8").read()
    m = re.search(r"^CALIBRATED\s*=\s*(\{.*?^\})", src, re.M | re.S)
    if not m:
        return {}
    try:
        return ast.literal_eval(m.group(1)) or {}
    except (ValueError, SyntaxError):
        return {}


def _load_baseline():
    if os.path.exists(_BASELINE):
        with open(_BASELINE, encoding="utf-8") as fh:
            return json.load(fh)
    return {"uncalibrated": []}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true", help="État complet, exit 0.")
    ap.add_argument("--update-baseline", action="store_true", help="Gèle l'état courant.")
    args = ap.parse_args(argv)

    instruments = scan_instruments()
    calibrated = scan_calibrated()
    uncalibrated = sorted(set(instruments) - calibrated)

    if args.update_baseline:
        os.makedirs(os.path.dirname(_BASELINE), exist_ok=True)
        with open(_BASELINE, "w", encoding="utf-8") as fh:
            json.dump({"uncalibrated": uncalibrated}, fh, indent=2, ensure_ascii=False)
        print(f"baseline gelé : {len(uncalibrated)} instruments non calibrés -> {_BASELINE}")
        return 0

    known = set(_load_baseline().get("uncalibrated", []))
    nouveaux = [n for n in uncalibrated if n not in known]

    print(f"instruments détectés : {len(instruments)} | calibrés : {len(calibrated)} | "
          f"non calibrés : {len(uncalibrated)} (dont {len(nouveaux)} NOUVEAUX)")
    if args.report:
        br = scan_declared_branches()
        for n in sorted(instruments):
            mark = "OK " if n in calibrated else "-- "
            suffix = f"  [branches: {', '.join(br[n])}]" if n in br else ""
            print(f"  {mark} {n}  ({instruments[n]}){suffix}")
        return 0

    for n in nouveaux:
        print(f"  [NOUVEL INSTRUMENT NON CALIBRÉ] {n}  ({instruments[n]})"
              f"  -> ajouter un cas dans tests/sandbox/test_instrument_calibration.py")
    if nouveaux:
        print("\nUn instrument non calibré peut PRODUIRE un résultat (cf. aliasing, EDR-WARM-007).")
        print("Calibrer sur vérité-terrain (tools/ground_truth_worlds.py) OU déclarer la dette :")
        print("  python tools/check_instrument_calibration.py --update-baseline")
        return 1
    print("OK : aucun nouvel instrument non calibré.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
