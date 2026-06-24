"""tools/map_elites_compare.py — A2 : MAP-Elites bat-il le HoF mono-objectif ? Deux bras évolutifs
appariés par seed à BUDGET ÉGAL (HoF top-5 ratchet vs archive QD), verdict + provenance.
Spec : docs/superpowers/specs/2026-06-24-NAS-A2-MapElites-design.md
Usage : MEC_SEEDS=0,1,2 MEC_ERAS=15 python tools/map_elites_compare.py"""
import os
import sys
import copy
import logging
from typing import List, Dict, Optional, Callable

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.harness import SeedManager, Harness
from src.seed_ai.map_elites import MapElitesArchive
from src.seed_ai.mutation import apply_mutations, MutationConfig
from src.seed_ai.repopulation import build_population
from src.agents.mamba_agent import MambaAgent
from src.worlds.world_1_stoneage import Biosphere3D
from src.seed_ai.persistence import calculate_life_score
from src.graph_rag.async_logger import logger as async_logger
from tools.curriculum_transfer import compute_transfer_verdict

SWEET_METAB = 0.25
SWEET_PAYOFF = 3.0
log = logging.getLogger("AGIseed.MapElitesCompare")


def _qd_label(v: str) -> str:
    return {"TRANSFERE": "QD_GAGNE", "NUIT": "QD_PERD", "NEUTRE": "NEUTRE"}.get(v, v)


# NAS substrat : preserve l'archi du génome (fix from_genome) + seed un connectome enrichi.
PRESERVE_DIMS = os.environ.get("MEC_PRESERVE_DIMS", "") == "1"
_snn = os.environ.get("MEC_SEED_NODES", "").strip()
SEED_NODES = int(_snn) if _snn else None
# A2 v2 : graines de tailles VARIÉES pour étaler l'axe taille des descripteurs MAP-Elites.
# Sans ça, toutes les graines tombent dans le même size_bin ((num_nodes-150)//15) -> coverage plafonnée
# (4/32 mesuré). Liste de num_nodes parcourue cycliquement par index de graine. Prioritaire sur SEED_NODES.
_spread = os.environ.get("MEC_SEED_SPREAD", "").strip()
SEED_SPREAD = [int(x) for x in _spread.split(",") if x.strip()] if _spread else None


def _seed_genome(idx: int = 0):
    """Génome de graine. MEC_SEED_SPREAD (liste) -> taille cyclée par idx pour étaler l'axe taille ;
    sinon MEC_SEED_NODES (taille fixe) ; sinon défaut bare MambaAgent."""
    if SEED_SPREAD:
        return MambaAgent(num_nodes=SEED_SPREAD[idx % len(SEED_SPREAD)]).genome
    if SEED_NODES is None:
        return MambaAgent().genome
    return MambaAgent(num_nodes=SEED_NODES).genome


def _make_cfg():
    cfg = WorldConfig()
    cfg.base_metabolism = SWEET_METAB
    cfg.forage_payoff = SWEET_PAYOFF
    return cfg


def _reproduce(champ_genomes, num_agents):
    """ÉLITE intacte + enfants mutés + fraction heavy (EDR 024), comme evolve_competence.
    Fallback : si les génomes ne sont pas des Genome réels (ex : test injectant un faux runner),
    on renvoie des copies brutes — le faux runner ignore les génomes de toute façon."""
    from src.seed_ai.mutation import Genome
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


def run_era_pool(cfg, genomes, max_ticks=400):
    """Mirror run_era_metab mais renvoie le POOL COMPLET avec stats (pour MAP-Elites)."""
    env = Biosphere3D(cfg)
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
    pool = []
    for ag in pool_agents:
        g = ag["model"].genome if "model" in ag else ag.get("genome")
        if g is None:
            continue
        score = float(calculate_life_score(ag))
        stats = {"num_nodes": g.num_nodes, "preys_eaten": ag.get("preys_eaten", 0),
                 "spears_crafted": ag.get("spears_crafted", 0), "mammoth_kills": ag.get("mammoth_kills", 0)}
        pool.append((score, g, stats))
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    best = max((p[0] for p in pool), default=0.0)
    return pool, {"score": best, "ticks": float(t)}


def _competence(window):
    tail = window[-5:] if len(window) >= 5 else window
    return float(np.mean([m["score"] for m in tail])) if tail else 0.0


def run_lineage_hof(seed, eras=15, num_agents=30, max_ticks=400, run_era_fn=None):
    """Bras HoF : cliquet top-5 (comme evolve_competence)."""
    if run_era_fn is None:
        run_era_fn = run_era_pool
    SeedManager(seed).seed_boundary(0)
    cfg = _make_cfg()
    best_ever = [(0.0, g) for g in [_seed_genome(i) for i in range(5)]]
    window = []
    for _ in range(eras):
        genomes = _reproduce([g for _s, g in best_ever], num_agents)
        pool, m = run_era_fn(cfg, genomes, max_ticks)
        scored = sorted([(s, g) for s, g, _st in pool], key=lambda x: x[0], reverse=True)[:5]
        best_ever = sorted(best_ever + scored, key=lambda x: x[0], reverse=True)[:5]
        window.append(m)
    return _competence(window)


def run_lineage_qd(seed, eras=15, num_agents=30, max_ticks=400, run_era_fn=None):
    """Bras QD : archive MAP-Elites, reproduit depuis des niches diverses."""
    if run_era_fn is None:
        run_era_fn = run_era_pool
    SeedManager(seed).seed_boundary(0)
    cfg = _make_cfg()
    archive = MapElitesArchive()
    genomes = [_seed_genome(i) for i in range(num_agents)]
    window = []
    for _ in range(eras):
        pool, m = run_era_fn(cfg, genomes, max_ticks)
        for s, g, st in pool:
            archive.upsert(s, g, st)
        champ = archive.sample(5)
        genomes = _reproduce(champ, num_agents) if champ else [MambaAgent().genome for _ in range(num_agents)]
        window.append(m)
    return _competence(window), archive.coverage()


def compare(seeds, eras=15, num_agents=30, max_ticks=400, run_era_fn=None) -> Dict:
    per_seed = []
    for seed in seeds:
        c_hof = run_lineage_hof(seed, eras, num_agents, max_ticks, run_era_fn)
        c_qd, cov = run_lineage_qd(seed, eras, num_agents, max_ticks, run_era_fn)
        ratio = c_qd / max(c_hof, 1e-6)
        per_seed.append({"seed": int(seed), "C_hof": c_hof, "C_qd": c_qd, "coverage": cov, "ratio": ratio})
        log.info("seed=%s C_hof=%.2f C_qd=%.2f cov=%d ratio=%.3f", seed, c_hof, c_qd, cov, ratio)
    verdict = compute_transfer_verdict([p["ratio"] for p in per_seed])
    return {**verdict, "verdict": _qd_label(verdict["verdict"]), "per_seed": per_seed,
            "config": {"seeds": [int(s) for s in seeds], "eras": eras,
                       "num_agents": num_agents, "max_ticks": max_ticks}}


def main():
    seeds = [int(s) for s in os.environ.get("MEC_SEEDS", "0,1,2").split(",") if s.strip()]
    eras = int(os.environ.get("MEC_ERAS", "15"))
    num_agents = int(os.environ.get("MEC_NUM_AGENTS", "30"))
    max_ticks = int(os.environ.get("MEC_TICKS", "400"))
    log.info("MapElitesCompare : seeds=%s eras=%d (2 bras/seed)", seeds, eras)
    async_logger.start()
    try:
        result = compare(seeds, eras=eras, num_agents=num_agents, max_ticks=max_ticks)
    finally:
        async_logger.stop()
    h = Harness(seed=min(seeds) if seeds else 0, name="map_elites_compare", with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    log.info("VERDICT=%s median_ratio=%.3f (n_fav=%d/%d, sign_p=%.3f) -> %s",
             result["verdict"], result["median_ratio"], result["n_favorable"], result["n"],
             result["sign_p"], path)
    return path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
