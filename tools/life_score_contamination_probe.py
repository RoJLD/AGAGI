# tools/life_score_contamination_probe.py
"""EDR-WLD-002 : probe d'impact de contamination life_score. Mesure si les termes
morts/inertes de calculate_life_score (altars_solved.20, spears_crafted.300) changent
le classement top-K de la selection sur une cohorte EVOLUEE realiste (memes conditions
qu'EDR 125). NE MUTE JAMAIS la fitness de prod : les variantes sont des copies locales.
Verdict par variante : METRIQUE_INERTE / METRIQUE_CONTAMINEE / AMBIGU. Garde-fou K>=12.

Usage : python tools/life_score_contamination_probe.py
  (env: LSC_SEEDS, LSC_ERAS, LSC_AGENTS, LSC_TICKS)
"""
import math
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def score(components, weights):
    """Somme ponderee des composants par le jeu de poids."""
    return sum(components[k] * weights[k] for k in weights)


def kendall_tau(a, b):
    """tau-a manuel (sans scipy). a, b : listes paralleles de scores. Paires a egalite
    (sur a ou b) comptees ni concordantes ni discordantes."""
    n = len(a)
    if n < 2:
        return 1.0
    concordant = discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            s = (a[i] - a[j]) * (b[i] - b[j])
            if s > 0:
                concordant += 1
            elif s < 0:
                discordant += 1
    total = n * (n - 1) // 2
    return (concordant - discordant) / total if total else 1.0


def _topk_indices(scores, k):
    """Indices du top-k par score decroissant ; egalites departagees par indice croissant."""
    order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
    return set(order[:k])


def topk_jaccard(scores_full, scores_var, k):
    """Jaccard des ensembles top-k entre le classement full et le classement variante."""
    a = _topk_indices(scores_full, k)
    b = _topk_indices(scores_var, k)
    union = a | b
    return len(a & b) / len(union) if union else 1.0


def term_mass_share(roster, weights):
    """Part de la masse totale de life_score venant de chaque terme (magnitude de contamination)."""
    terms = {k: sum(c[k] * weights[k] for c in roster) for k in weights}
    total = sum(terms.values())
    return {k: (terms[k] / total if total else 0.0) for k in terms}


from src.seed_ai.persistence import REF_FITNESS_WEIGHT

WEIGHTS_FULL = {
    "age": 0.1, "preys_eaten": 50.0, "altars_solved": 20.0,
    "spears_crafted": 300.0, "mammoth_kills": 400.0, "ref_distinction": REF_FITNESS_WEIGHT,
}


def variants():
    """full + une variante par terme suspect annule (copies locales, jamais la prod)."""
    v = {"full": dict(WEIGHTS_FULL)}
    for name, zeroed in (("drop_altars", ("altars_solved",)),
                         ("drop_spears", ("spears_crafted",)),
                         ("drop_both", ("altars_solved", "spears_crafted"))):
        w = dict(WEIGHTS_FULL)
        for key in zeroed:
            w[key] = 0.0
        v[name] = w
    return v


def analyze_roster(roster, frac_topk=0.25):
    """Compare chaque variante a full sur ce roster. Retourne metriques + comptes d'events."""
    W = variants()
    n = len(roster)
    full_scores = [score(c, W["full"]) for c in roster]
    k = max(1, math.ceil(frac_topk * n)) if n else 1
    out = {
        "n": n,
        "n_crafters": sum(1 for c in roster if c["spears_crafted"] > 0),
        "n_altar_solvers": sum(1 for c in roster if c["altars_solved"] > 0),
        "term_mass_share": term_mass_share(roster, W["full"]) if n else {},
        "variants": {},
    }
    for name, w in W.items():
        if name == "full":
            continue
        var_scores = [score(c, w) for c in roster]
        out["variants"][name] = {
            "kendall_tau": kendall_tau(full_scores, var_scores),
            "topk_jaccard": topk_jaccard(full_scores, var_scores, k),
        }
    return out
