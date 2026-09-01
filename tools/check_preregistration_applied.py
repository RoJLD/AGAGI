"""Cliquet : un record MESURE-t-il les grandeurs que sa règle scellée EXIGE ?

⚠️ Né d'un échec, trouvé en revue adversariale le 2026-08-04 (classe E11, occurrence 4).

`tools/preregister.py` scelle la RÈGLE par un hash : il prouve qu'elle n'a pas été réécrite après coup.
Il ne prouve RIEN sur la fidélité de son APPLICATION. EDR-EVO-019 en est la démonstration : sa règle
exigeait littéralement « le plafond doit RÉDUIRE `|logit|` médian », le record a substitué une réduction
de FAN-IN, et a écrit « les deux conditions sont satisfaites ». Le sceau était intact. Le mot « logit »
n'apparaissait pas une seule fois dans le record.

Ce cliquet ferme cet angle mort par une intersection de vocabulaire : les GRANDEURS NOMMÉES dans les
clauses de mesure d'une règle scellée doivent apparaître dans le record qui s'en réclame. Une DV
substituée en silence ne passe plus.

⚠️ Portée honnête : c'est une vérification LEXICALE, pas sémantique. Elle attrape l'omission (le record
ne parle jamais de la grandeur) — pas le cas où le record nomme la grandeur tout en mesurant autre chose.
Elle est donc nécessaire, pas suffisante ; la revue adversariale reste la garde de dernier recours.
"""
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PREREG = os.path.join(_ROOT, "docs", "preregistrations")
_EDR = os.path.join(_ROOT, "docs", "EDR")

# Champs d'une règle qui DÉCRIVENT une mesure à faire (par opposition au contexte narratif).
_MEASURE_FIELDS = ("dv_primaire", "dv", "dv_mecaniste", "dv_survie", "dv_primaire_corrigee",
                   "controle_de_manipulation_OBLIGATOIRE", "prevol_decisif", "regle_de_lecture_continue",
                   "regle_existence", "regle_frequence")

# Tokens trop génériques pour porter une exigence de mesure.
_STOP = {"raw", "sal", "n", "p", "seed", "seeds", "bras", "age", "med", "max", "min", "w", "k"}


def _quantities(rule: dict):
    """Grandeurs NOMMÉES dans les clauses de mesure : `token` entre backticks, ou motif |token|."""
    out = set()
    for f in _MEASURE_FIELDS:
        v = rule.get(f)
        if not isinstance(v, str):
            continue
        for m in re.findall(r"`([^`]{2,40})`", v):
            out.add(m.strip())
        for m in re.findall(r"\|([A-Za-z_][A-Za-z0-9_]{1,30})\|", v):
            out.add(m.strip())
    # normalise : on ne garde que le coeur identifiant, et on jette les termes generiques
    keep = set()
    for t in out:
        core = re.sub(r"[^A-Za-z0-9_\[\]]", "", t.split("(")[0]).strip()
        if len(core) >= 3 and core.lower() not in _STOP:
            keep.add(core)
    return keep


def _record_text_for(name: str):
    """Le record qui se reclame de cette pre-inscription (par son nom, ex. EVO-019)."""
    base = name.split("-bis")[0]
    hits = []
    for fn in sorted(os.listdir(_EDR)):
        if not fn.endswith(".md"):
            continue
        if fn.startswith(base + "_") or fn.startswith(base.replace("EVO-", "EVO-") + "_"):
            hits.append(os.path.join(_EDR, fn))
    return hits


def scan():
    problems = []
    if not os.path.isdir(_PREREG):
        return problems
    for fn in sorted(os.listdir(_PREREG)):
        if not fn.endswith(".json"):
            continue
        name = fn[:-5]
        with open(os.path.join(_PREREG, fn), encoding="utf-8") as f:
            rule = json.load(f).get("rule", {})
        qty = _quantities(rule)
        if not qty:
            continue
        recs = _record_text_for(name)
        if not recs:
            continue                      # regle scellee sans record encore ecrit : rien a verifier
        text = "\n".join(open(r, encoding="utf-8").read() for r in recs)
        missing = sorted(q for q in qty if q.lower() not in text.lower())
        if missing:
            problems.append((name, os.path.basename(recs[0]), missing))
    return problems


def main():
    problems = scan()
    total = len([f for f in os.listdir(_PREREG) if f.endswith(".json")]) if os.path.isdir(_PREREG) else 0
    if not problems:
        print(f"OK : {total} regles scellees, chacune mesuree dans son record.")
        return 0
    for name, rec, missing in problems:
        print(f"[DV SCELLEE NON MESUREE] {name} -> {rec}")
        print(f"    grandeurs exigees par la regle et ABSENTES du record : {missing}")
    print("\nUne regle scellee nomme une grandeur que le record ne mentionne jamais : soit elle n'a pas ete")
    print("mesuree (classe E11 occ.4, cf. EDR-EVO-019), soit le record doit dire POURQUOI elle est omise.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
