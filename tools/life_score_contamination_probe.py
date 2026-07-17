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
    """tau-b manuel (sans scipy) : corrige les ex-aequo -> kendall_tau(a, a) == 1.0 meme
    quand plusieurs elements partagent le meme score (cas courant : cohorte de clones-
    champions aux stats identiques). tau = (C - D) / sqrt((C+D+Tx)(C+D+Ty)) ou Tx/Ty
    comptent les paires a egalite dans UN SEUL vecteur ; les paires egales dans les deux
    sont exclues. a, b : listes paralleles de scores."""
    n = len(a)
    if n < 2:
        return 1.0
    C = D = Tx = Ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            da = a[i] - a[j]
            db = b[i] - b[j]
            if da == 0 and db == 0:
                continue                      # egalite dans les deux -> exclue
            if da == 0:
                Ty += 1                       # egalite seulement dans a
            elif db == 0:
                Tx += 1                       # egalite seulement dans b
            elif da * db > 0:
                C += 1
            else:
                D += 1
    denom = math.sqrt((C + D + Tx) * (C + D + Ty))
    return (C - D) / denom if denom else 1.0


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


from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from src.seed_ai.harness import SeedManager
from tools.competence_profile import _evolve_champions
from tools.map_elites_compare import _make_cfg, PRESERVE_DIMS


def _components(agent):
    """Extrait les 6 termes de life_score (dont altars_solved, pour MESURER qu'il est 0)."""
    return {"age": agent.get("age", 0), "preys_eaten": agent.get("preys_eaten", 0),
            "altars_solved": agent.get("altars_solved", 0),
            "spears_crafted": agent.get("spears_crafted", 0),
            "mammoth_kills": agent.get("mammoth_kills", 0),
            "ref_distinction": agent.get("_ref_distinction", 0.0)}


def _measure_roster(cfg, genomes, max_ticks, seed=0):
    """Mesure sur COHORTE FIXE (benchmark_mode) ; roster = env.agents + dead_agents
    (mirror competence_profile._measure_profile : inclut les morts avec stats finales).
    Re-seede le RNG (SeedManager) et clear la memoire ambiante AVANT la boucle -> deux
    appels sur les MEMES genomes produisent un roster byte-identique (repro de mesure)."""
    SeedManager(seed).seed_boundary(0)
    env = Biosphere3D(cfg)
    env.benchmark_mode = True
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
        env.memory_retriever.clear()
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g, preserve_dims=PRESERVE_DIMS)
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        t += 1
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    return [_components(a) for a in pool]


def _evolve_for(seed, eras, num_agents, max_ticks):
    """Evolue des champions (cliquet top-5, repro ON, regime sweet) puis les replique pour
    remplir une cohorte de num_agents. Retourne la liste des genomes ([] si echec)."""
    champs = _evolve_champions(seed, eras=eras, num_agents=num_agents, max_ticks=max_ticks)
    if not champs:
        return []
    return (champs * (num_agents // len(champs) + 1))[:num_agents]


def run_arm(seed=0, eras=8, num_agents=30, max_ticks=300):
    """Evolue des champions puis mesure leur cohorte fixe. Retourne le roster (liste de
    composants). CRN : evolution seedee par _evolve_champions, mesure re-seedee par seed."""
    reps = _evolve_for(seed, eras, num_agents, max_ticks)
    return _measure_roster(_make_cfg(), reps, max_ticks, seed=seed) if reps else []


def _median(xs):
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    m = n // 2
    return s[m] if n % 2 else (s[m - 1] + s[m]) / 2.0


_RANK = {"METRIQUE_CONTAMINEE": 2, "AMBIGU": 1, "METRIQUE_INERTE": 0}


def aggregate(per_seed, k_seeds, effect_thresh=0.10):
    """Agrege les metriques par variante sur les seeds et rend un verdict. Garde-fou :
    aucun METRIQUE_CONTAMINEE sous k_seeds=12."""
    names = list(per_seed[0]["variants"]) if per_seed else []
    per_variant = {}
    for name in names:
        jac = [s["variants"][name]["topk_jaccard"] for s in per_seed]
        tau = [s["variants"][name]["kendall_tau"] for s in per_seed]
        med_j = _median(jac)
        med_t = _median(tau)
        n_changed = sum(1 for x in jac if x < 1.0)
        effect = 1.0 - med_j
        if med_j == 1.0 and med_t == 1.0:
            verdict = "METRIQUE_INERTE"
        elif k_seeds >= 12 and effect >= effect_thresh and n_changed >= math.ceil(k_seeds / 2):
            verdict = "METRIQUE_CONTAMINEE"
        else:
            verdict = "AMBIGU"
        per_variant[name] = {"median_jaccard": med_j, "median_tau": med_t,
                             "n_changed": n_changed, "effect": effect, "verdict": verdict}
    global_verdict = max((v["verdict"] for v in per_variant.values()),
                         key=lambda x: _RANK[x], default="METRIQUE_INERTE")
    return {"per_variant": per_variant, "global_verdict": global_verdict}


def hof_decomposition():
    """Corroborant non-bloquant : decompose le HoF de prod (si present) en part-de-masse
    par terme (moyenne sur les champions). Retourne None sur toute absence/erreur."""
    try:
        from src.seed_ai.persistence import load_hall_of_fame
        _version, hof = load_hall_of_fame()
        if not hof:
            return None
        shares = []
        for entry in hof:
            stats = getattr(entry, "stats", None)
            if stats is None and isinstance(entry, dict):
                stats = entry.get("stats")
            if not stats:
                continue
            comp = {"age": stats.get("age", 0), "preys_eaten": stats.get("preys_eaten", 0),
                    "altars_solved": stats.get("altars_solved", 0),
                    "spears_crafted": stats.get("spears_crafted", 0),
                    "mammoth_kills": stats.get("mammoth_kills", 0), "ref_distinction": 0.0}
            shares.append(term_mass_share([comp], WEIGHTS_FULL))
        if not shares:
            return None
        keys = list(shares[0])
        return {"n_champions": len(shares),
                "mean_share": {k: sum(s[k] for s in shares) / len(shares) for k in keys}}
    except Exception:
        return None


def compare(seeds=(0,), eras=8, num_agents=30, max_ticks=300, frac_topk=0.25):
    """Evolue+mesure chaque seed, analyse, agrege, verdict. Garde repro FAIL-SOFT (flag
    repro_ok, jamais fatale) : re-mesure les MEMES genomes de seed[0] et verifie l'egalite
    byte-identique. On ne re-EVOLUE PAS pour la garde : l'evolution tourne sous memoire
    KuzuDB ambiante cumulative (non byte-reproductible, cf. hazard connu) ; la MESURE, elle,
    re-seede + clear la memoire donc est deterministe. Un assert dur ici tuerait un run de
    plusieurs heures pour un artefact d'ambient memory -> on enregistre le statut a la place."""
    rosters = {}
    per_seed = []
    reps0 = None
    for s in seeds:
        reps = _evolve_for(s, eras, num_agents, max_ticks)
        if s == seeds[0]:
            reps0 = reps
        roster = _measure_roster(_make_cfg(), reps, max_ticks, seed=s) if reps else []
        rosters[s] = roster
        per_seed.append(analyze_roster(roster, frac_topk=frac_topk))
    repro_ok = True
    if reps0:
        roster_repro = _measure_roster(_make_cfg(), reps0, max_ticks, seed=seeds[0])
        repro_ok = (roster_repro == rosters[seeds[0]])
    agg = aggregate(per_seed, k_seeds=len(seeds))
    return {"config": {"seeds": list(seeds), "eras": eras, "num_agents": num_agents,
                       "max_ticks": max_ticks, "frac_topk": frac_topk},
            "per_seed": per_seed, "per_variant": agg["per_variant"],
            "global_verdict": agg["global_verdict"], "repro_ok": repro_ok,
            "hof_decomposition": hof_decomposition()}


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    import json
    from src.graph_rag.async_logger import logger as async_logger
    seeds = tuple(int(x) for x in os.environ.get("LSC_SEEDS", ",".join(str(i) for i in range(12))).split(","))
    eras = int(os.environ.get("LSC_ERAS", "8"))
    n_agents = int(os.environ.get("LSC_AGENTS", "30"))
    ticks = int(os.environ.get("LSC_TICKS", "300"))
    async_logger.start()
    try:
        out = compare(seeds=seeds, eras=eras, num_agents=n_agents, max_ticks=ticks)
    finally:
        async_logger.stop()
    for i, ps in enumerate(out["per_seed"]):
        da = ps["variants"]["drop_altars"]
        ds = ps["variants"]["drop_spears"]
        print(f"seed={seeds[i]} n={ps['n']} crafters={ps['n_crafters']} altar={ps['n_altar_solvers']} "
              f"| drop_altars tau={da['kendall_tau']:+.3f} jac={da['topk_jaccard']:.3f} "
              f"| drop_spears tau={ds['kendall_tau']:+.3f} jac={ds['topk_jaccard']:.3f}")
    print("--- verdict par variante ---")
    for name, v in out["per_variant"].items():
        print(f"{name:12s} med_jac={v['median_jaccard']:.3f} med_tau={v['median_tau']:+.3f} "
              f"effect={v['effect']:.3f} n_changed={v['n_changed']} -> {v['verdict']}")
    print("VERDICT GLOBAL:", out["global_verdict"])
    if not out.get("repro_ok", True):
        print("WARNING: repro de mesure NON byte-identique (verifier la memoire ambiante).")
    if out["hof_decomposition"]:
        print("HoF mean_share:", out["hof_decomposition"]["mean_share"])
    os.makedirs("results", exist_ok=True)
    path = f"results/life_score_contamination_{seeds[0]}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("RESULT ->", path)
