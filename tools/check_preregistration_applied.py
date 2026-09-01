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
# ⚠️ LISTE BLANCHE ELARGIE le 2026-09-02 -- elle SAUTAIT EN SILENCE. Mesure : sur 23 regles scellees,
# seules 8 etaient REELLEMENT inspectees ; 14 etaient sautees parce qu'aucune grandeur n'en sortait,
# faute de connaitre leurs champs. Le plus coûteux : `discrimination`, present dans 17 regles, porte la
# regle de lecture de la plupart des regles EVO. Et `instruments_autorises` est le champ que la cloture
# d'E11 avait INVENTE -- le cliquet ne le lisait pas.
# C'est la TROISIEME liste blanche silencieuse trouvee en deux jours (apres `_LIST_KEYS` du frontmatter
# et `_INSTRUMENT_PATTERNS` du nommage). Regle qui en sort : une liste blanche doit RAPPORTER ce qu'elle
# ecarte, sinon elle transforme son ignorance en succes.
_MEASURE_FIELDS = ("dv_primaire", "dv", "dv_mecaniste", "dv_survie", "dv_primaire_corrigee",
                   "dv_secondaire", "dv_sante_lignee",
                   "controle_de_manipulation_OBLIGATOIRE", "controle", "prevol_decisif",
                   "prevol_mesure", "prevol_obligatoire",
                   "regle_de_lecture_continue", "regle_existence", "regle_frequence",
                   "discrimination", "instruments_autorises", "garde_puissance",
                   "predictions_chiffrees_AVANT_le_run", "seuil")

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


# Regles scellees AVANT l'adoption de la convention « backticker les grandeurs » : leurs clauses de
# mesure sont en prose (« raw = succes/essais du champion »), donc AUCUNE grandeur n'en est extractible.
# Elles sont declarees NON INSPECTABLES -- pas « verifiees ». Deviner des identifiants nus produirait des
# faux positifs ; on ne proxifie pas ce qu'on ne sait pas mesurer, on le declare.
_LEGATAIRES_SANS_BACKTICK = frozenset({
    "EVO-006-REPLICATION", "EVO-007", "EVO-007-bis", "EVO-007-bis2", "EVO-008",
    "EVO-010", "EVO-011", "EVO-012", "EVO-015", "EVO-016", "EVO-017", "EVO-017-bis", "EVO-020",
})
# ⚠️ EVO-009 a ete RETIRE de cette dette le 2026-09-02 : l'elargissement des champs de mesure a rendu
# sa grandeur extractible. C'est le test `test_the_legacy_declaration_is_STILL_REAL` qui l'a impose --
# une dette qui ne peut plus etre invalidee n'est plus une dette, c'est un commentaire.


def couverture():
    """(inspectees, sans_grandeur, sans_record, total) -- ce que le cliquet VERIFIE reellement."""
    insp = sans_qty = sans_rec = total = 0
    if not os.path.isdir(_PREREG):
        return (0, 0, 0, 0)
    for fn in sorted(os.listdir(_PREREG)):
        if not fn.endswith(".json"):
            continue
        total += 1
        name = fn[:-5]
        with open(os.path.join(_PREREG, fn), encoding="utf-8") as f:
            rule = json.load(f).get("rule", {})
        if not _quantities(rule):
            sans_qty += 1
        elif not _record_text_for(name):
            sans_rec += 1
        else:
            insp += 1
    return (insp, sans_qty, sans_rec, total)


def nouvelles_sans_grandeur():
    """Regles NON legataires dont aucune grandeur n'est extractible : la convention n'a pas ete suivie."""
    out = []
    if not os.path.isdir(_PREREG):
        return out
    for fn in sorted(os.listdir(_PREREG)):
        if not fn.endswith(".json"):
            continue
        name = fn[:-5]
        if name in _LEGATAIRES_SANS_BACKTICK:
            continue
        with open(os.path.join(_PREREG, fn), encoding="utf-8") as f:
            rule = json.load(f).get("rule", {})
        if not _quantities(rule):
            out.append(name)
    return out


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
    insp, sans_qty, sans_rec, total = couverture()
    orphelines = nouvelles_sans_grandeur()
    # ⚠️ NE PAS SURDECLARER SA PROPRE COUVERTURE. Le message disait « {total} regles scellees, chacune
    # mesuree » alors que 8 sur 23 seulement etaient REELLEMENT inspectees : un cliquet qui annonce
    # 100 % quand il en fait 35 est un faux vert sur lui-meme.
    print(f"couverture : {insp}/{total} regles REELLEMENT inspectees "
          f"({sans_qty} sans grandeur nommee, {sans_rec} sans record ecrit)")
    if orphelines:
        print("ECHEC : regle(s) scellee(s) recente(s) dont AUCUNE grandeur n'est extractible :")
        for n in orphelines:
            print(f"  {n}  -> backticker les grandeurs dans les clauses de mesure, sinon la regle "
                  f"n'est pas verifiable")
        return 1
    if not problems:
        print(f"OK : aucune DV scellee absente de son record (sur les {insp} regles inspectables).")
        return 0
    for name, rec, missing in problems:
        print(f"[DV SCELLEE NON MESUREE] {name} -> {rec}")
        print(f"    grandeurs exigees par la regle et ABSENTES du record : {missing}")
    print("\nUne regle scellee nomme une grandeur que le record ne mentionne jamais : soit elle n'a pas ete")
    print("mesuree (classe E11 occ.4, cf. EDR-EVO-019), soit le record doit dire POURQUOI elle est omise.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
