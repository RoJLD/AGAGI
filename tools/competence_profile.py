"""tools/competence_profile.py — Profil de competence par tier (P3a audit memoire).

Mesure la competence stoneage ventilee par tier {forage/craft/apex} sur une COHORTE FIXE (benchmark_mode,
EDR 114b) au lieu d'ecraser sur le scalaire life_score. Tranche le verdict gele « mur du craft » :
l'echelle moyens->ends {survie<forage<craft<apex} s'inverse-t-elle au craft (apex atteint PLUS que la
lance -> pathway outil quasi-mort, poids spears de life_score inerte) ? Indices code (competence.py:66 :
apex 21.7% / lance 1.6%) ; ici on le MESURE proprement et on PRE-ENREGISTRE le verdict.

Tooling pur (pas de src/ modifie ; map_elites_compare/competence importes). Usage : python -m tools.competence_profile
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.harness import Harness, SeedManager
from src.agents.mamba_agent import MambaAgent
from src.worlds.world_1_stoneage import Biosphere3D
from src.curriculum.competence import _frac_reaching
from src.graph_rag.async_logger import logger as async_logger
from tools.map_elites_compare import _make_cfg, _seed_genome, _reproduce, run_era_pool, PRESERVE_DIMS


def _tier_fractions(stats_list):
    """Fractions « a deja atteint » par tier (binaire par agent, _frac_reaching seuil >=1)."""
    return {"frac_forage": _frac_reaching(stats_list, "preys_eaten"),
            "frac_craft": _frac_reaching(stats_list, "spears_crafted"),
            "frac_apex": _frac_reaching(stats_list, "mammoth_kills"),
            "n": len(stats_list)}


def _verdict_craft_wall(fracs):
    """INDETERMINE si forage < 0.10 (cohorte trop incompetente) ; CRAFT_WALL CONFIRME si craft < forage
    ET apex >= craft (echelle inversee) ET craft <= 0.10 (quasi-mort) ; sinon ECHELLE MONOTONE."""
    ff, fc, fa = fracs["frac_forage"], fracs["frac_craft"], fracs["frac_apex"]
    if ff < 0.10:
        return "INDETERMINE"
    if fc < ff and fa >= fc and fc <= 0.10:
        return "CRAFT_WALL CONFIRME"
    return "ECHELLE MONOTONE"


def _report_profile(h, per_seed, R, _return):
    """Table ASCII (1 ligne/seed : forage, craft, apex, n) + moyenne + verdict. Save JSON."""
    keys = ("frac_forage", "frac_craft", "frac_apex")
    fracs = {k: float(np.mean([p[k] for p in per_seed])) for k in keys}
    verdict = _verdict_craft_wall(fracs)
    print("\n=== Profil de competence par tier (cohorte fixe) ===")
    print("  seed | forage  craft   apex  |   n")
    for p in per_seed:
        print(f"  {p['seed']:4d} | {p['frac_forage']:6.3f} {p['frac_craft']:6.3f} {p['frac_apex']:6.3f} | {p['n']:4d}")
    print(f"  MOYEN| {fracs['frac_forage']:6.3f} {fracs['frac_craft']:6.3f} {fracs['frac_apex']:6.3f}")
    print("=== VERDICT (mur du craft) ===")
    print(f"  -> {verdict}")
    h.save({"R": R, "verdict": verdict, "mean_fracs": fracs, "per_seed": per_seed})
    if _return:
        return {"verdict": verdict, "mean_fracs": fracs, "per_seed": per_seed, "R": R}


def _measure_profile(cfg, genomes, max_ticks=400, disable_repro=True):
    """Mesure profil sur COHORTE FIXE. Mirror run_era_pool MAIS : benchmark_mode si disable_repro (pas
    de repro -> pas de dilution pooling, EDR 114b) ; memory_retriever stop()+clear() AVANT la boucle
    (repro, P0) ; renvoie la liste des stats par agent {age, preys_eaten, spears_crafted, mammoth_kills}."""
    env = Biosphere3D(cfg)
    if disable_repro:
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
    pool_agents = env.agents + list(getattr(env, "dead_agents", []))
    return [{"age": ag.get("age", 0), "preys_eaten": ag.get("preys_eaten", 0),
             "spears_crafted": ag.get("spears_crafted", 0), "mammoth_kills": ag.get("mammoth_kills", 0)}
            for ag in pool_agents]


def _evolve_champions(seed, eras=12, num_agents=30, max_ticks=400):
    """Cliquet top-5 (boucle de run_lineage_hof, repro ON) -> renvoie les genomes best_ever (top-5)."""
    SeedManager(seed).seed_boundary(0)
    cfg = _make_cfg()
    best_ever = [(0.0, g) for g in [_seed_genome(i) for i in range(5)]]
    for _ in range(eras):
        genomes = _reproduce([g for _s, g in best_ever], num_agents)
        pool, _m = run_era_pool(cfg, genomes, max_ticks)
        scored = sorted([(s, g) for s, g, _st in pool], key=lambda x: x[0], reverse=True)[:5]
        best_ever = sorted(best_ever + scored, key=lambda x: x[0], reverse=True)[:5]
    return [g for _s, g in best_ever]


def main_competence_profile(R=3, eras=12, num_agents=30, max_ticks=400, seed=1240, _return=False):
    """Pour chaque seed base+r : evolue des champions stoneage (repro ON) puis mesure leur profil par
    tier sur cohorte fixe (benchmark_mode). Agrege R seeds, verdict mur du craft."""
    base = seed
    async_logger.start()
    try:
        per_seed = []
        for r in range(R):
            s = base + r
            champs = _evolve_champions(s, eras=eras, num_agents=num_agents, max_ticks=max_ticks)
            reps = (champs * (num_agents // len(champs) + 1))[:num_agents] if champs else []
            stats = _measure_profile(_make_cfg(), reps, max_ticks=max_ticks, disable_repro=True)
            per_seed.append({**_tier_fractions(stats), "seed": int(s)})
    finally:
        async_logger.stop()
    h = Harness(seed=base, name="competence_profile", with_db=False, config=WorldConfig())
    return _report_profile(h, per_seed, R, _return)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    main_competence_profile()
