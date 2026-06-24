# tools/metabolic_cost_sweep.py
"""tools/metabolic_cost_sweep.py — Mesure X2 de D1 (coût métabolique d'activation, NAS Axe D-1).
Le coût métabolique sélectionne-t-il des connectomes efficients sans effondrer la compétence ?
Trajectoires évolutives appariées multi-seed, banc stoneage survivable (sweet-spot EDR 085).
Spec : docs/superpowers/specs/2026-06-24-NAS-D1-Measurement-design.md
Usage : MCS_SEEDS=0,1,2 MCS_SWEEP=0,0.001,0.01 python tools/metabolic_cost_sweep.py"""
import copy
import os
import sys
import math
import logging
import statistics
from typing import List, Dict, Optional, Callable

import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.harness import SeedManager

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

log = logging.getLogger("AGIseed.MetabolicCostSweep")


def _sign_test_p(k: int, n: int) -> float:
    """p-value binomiale exacte BILATÉRALE sous H0 p=0.5 (test de signe)."""
    if n <= 0:
        return 1.0
    k_hi = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(k_hi, n + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def compute_sweep_verdict(per_coef: List[Dict], eff_band: float = 0.05,
                          collapse_frac: float = 0.90) -> Dict:
    """per_coef[i] = {coef, eff_ratios:[par seed], surv_ratios:[par seed]} -> verdict par coef. PUR."""
    out = []
    for entry in per_coef:
        eff = list(entry.get("eff_ratios", []))
        surv = list(entry.get("surv_ratios", []))
        n = len(eff)
        if n == 0:
            out.append({"coef": entry.get("coef"), "median_eff": 0.0, "n": 0,
                        "n_favorable": 0, "sign_p": 1.0, "collapsed": False, "verdict": "NEUTRE"})
            continue
        median_eff = float(statistics.median(eff))
        n_fav = sum(1 for r in eff if r > 1.0)
        effective = [r for r in eff if r != 1.0]
        sign_p = _sign_test_p(sum(1 for r in effective if r > 1.0), len(effective))
        collapsed = bool(surv) and statistics.median(surv) < collapse_frac
        if collapsed:
            verdict = "NUIT"
        elif median_eff > 1.0 + eff_band and 2 * n_fav > n:
            verdict = "EFFICACE"
        else:
            verdict = "NEUTRE"
        out.append({"coef": entry.get("coef"), "median_eff": median_eff, "n": n,
                    "n_favorable": n_fav, "sign_p": sign_p, "collapsed": collapsed, "verdict": verdict})
    return {"per_coef": out}


SWEET_METAB = 0.25      # sweet-spot EDR 085 (survie ×4)
SWEET_PAYOFF = 3.0


def _make_cfg(coef: float) -> WorldConfig:
    cfg = WorldConfig()
    cfg.base_metabolism = SWEET_METAB
    cfg.forage_payoff = SWEET_PAYOFF
    cfg.metabolic_cost_coef = coef
    return cfg


def _reproduce(champ_genomes, num_agents):
    """ÉLITE intacte + enfants mutés + fraction heavy (EDR 024), comme evolve_competence.
    Fallback : si les génomes ne sont pas des Genome réels (ex : test injectant un faux runner),
    on renvoie des copies brutes — le faux runner ignore les génomes de toute façon."""
    from src.seed_ai.mutation import apply_mutations, MutationConfig, Genome
    from src.seed_ai.repopulation import build_population
    mc = MutationConfig(weight_init_std=2.0)
    heavy = copy.deepcopy(mc)
    heavy.weight_mutate_rate = min(1.0, mc.weight_mutate_rate * 2.0)
    heavy.weight_mutate_power = mc.weight_mutate_power * 1.5
    # Si les génomes sont de vrais Genome, on utilise build_population avec mutations.
    # Sinon (tests avec faux runner), on renvoie des copies simples.
    if champ_genomes and isinstance(champ_genomes[0], Genome):
        return build_population(champ_genomes, num_agents, mc, apply_mutations,
                                heavy_config=heavy, heavy_frac=0.3)
    # Fallback : copies brutes pour les tests avec faux runner
    if not champ_genomes:
        return []
    pop = []
    while len(pop) < num_agents:
        pop.append(copy.deepcopy(champ_genomes[len(pop) % len(champ_genomes)]))
    return pop


def run_lineage(seed: int, coef: float, eras: int = 15, num_agents: int = 30,
                max_ticks: int = 400, run_era_fn: Optional[Callable] = None) -> Dict:
    """Une trajectoire évolutive (E ères + cliquet) à coef fixe, seed apparié.
    KPIs sur 5 dernières ères."""
    if run_era_fn is None:
        run_era_fn = run_era_metab  # défini en Task 3 dans ce même module
    SeedManager(seed).seed_boundary(0)
    cfg = _make_cfg(coef)
    from src.agents.mamba_agent import MambaAgent
    champions = [MambaAgent().genome for _ in range(5)]
    best_ever = [(0.0, g) for g in champions]
    window: List[Dict] = []
    for _era in range(1, eras + 1):
        champ_genomes = [g for (_s, g) in best_ever]
        genomes = _reproduce(champ_genomes, num_agents)
        scored, m = run_era_fn(cfg, genomes, max_ticks)
        best_ever = sorted(best_ever + scored, key=lambda sg: sg[0], reverse=True)[:5]
        window.append(m)
    tail = window[-5:] if len(window) >= 5 else window
    competence = float(np.mean([m["score"] for m in tail]))
    survival = float(np.mean([m["ticks"] for m in tail]))
    mean_active = float(np.mean([m["mean_active"] for m in tail]))
    efficiency = competence / max(mean_active, 1e-6)
    return {"seed": int(seed), "coef": float(coef), "competence": competence,
            "survival": survival, "mean_active": mean_active, "efficiency": efficiency}


def run_sweep(seeds, coefs, eras: int = 15, num_agents: int = 30, max_ticks: int = 400,
              run_era_fn: Optional[Callable] = None) -> Dict:
    """Sweep apparié : pour chaque seed, chaque coef -> run_lineage.
    Ratios vs coef=0 -> verdict."""
    coefs = list(coefs)
    if 0.0 not in coefs:
        coefs = [0.0] + coefs
    per_lineage = []
    by_seed: Dict[int, Dict[float, Dict]] = {}
    for seed in seeds:
        by_seed[seed] = {}
        for coef in coefs:
            r = run_lineage(seed, coef, eras, num_agents, max_ticks, run_era_fn)
            by_seed[seed][coef] = r
            per_lineage.append(r)
    per_coef = []
    for coef in coefs:
        if coef == 0.0:
            continue
        eff_ratios, surv_ratios = [], []
        for seed in seeds:
            base, cur = by_seed[seed][0.0], by_seed[seed][coef]
            eff_ratios.append(cur["efficiency"] / max(base["efficiency"], 1e-6))
            surv_ratios.append(cur["survival"] / max(base["survival"], 1e-6))
        per_coef.append({"coef": coef, "eff_ratios": eff_ratios, "surv_ratios": surv_ratios})
    verdict = compute_sweep_verdict(per_coef)
    return {**verdict, "per_lineage": per_lineage,
            "config": {"seeds": [int(s) for s in seeds], "coefs": coefs, "eras": eras,
                       "num_agents": num_agents, "max_ticks": max_ticks}}
