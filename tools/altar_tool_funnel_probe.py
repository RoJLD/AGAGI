"""Sonde funnel autel/outil (barreau 0 de l'EDR 014). Au sweet spot sur stoneage : l'autel est-il
structurellement mort (altars_solved jamais >0) et où les agents décrochent-ils dans le pathway outil
(craft -> usage mammouth) ? Observationnel, pure-lecture des champs d'agent (vivants+morts, EDR 092).
Spec : docs/superpowers/specs/2026-06-24-Altar-Tool-Funnel-Probe-design.md."""
import os
import sys
import logging
from typing import List, Dict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.environments.config import WorldConfig
from src.seed_ai.harness import SeedManager, Harness
from src.graph_rag.async_logger import logger as async_logger
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from main_curriculum import _prepare_world, _acquire_shared_db

log = logging.getLogger("AGIseed.AltarToolFunnel")


def _frac(agents: List[Dict], key: str) -> float:
    """Fraction des agents avec champ `key` >= 1 (rare-event-aware). Liste vide -> 0.0."""
    if not agents:
        return 0.0
    return sum(1 for a in agents if a.get(key, 0) >= 1) / len(agents)


def _seed_summary(agents: List[Dict]) -> Dict:
    return {"n": len(agents),
            "frac_hunt": _frac(agents, "preys_eaten"),
            "frac_craft": _frac(agents, "spears_crafted"),
            "frac_apex": _frac(agents, "mammoth_kills"),
            "total_spears": sum(a.get("spears_crafted", 0) for a in agents),
            "total_mammoth_kills": sum(a.get("mammoth_kills", 0) for a in agents),
            "altars_solved_max": max((a.get("altars_solved", 0) for a in agents), default=0)}


def funnel_verdict(per_seed_agents: Dict, eps: float = 0.02) -> Dict:
    """Verdicts décomposés (autel + funnel outil) sur TOUS les agents poolés, fractions (pas médianes).
    Le verdict funnel localise le 1er étage qui s'effondre sous eps. par_seed = courbe complète.

    CAVEAT (EDR 096) : `verdict_funnel` n'est PAS fiable comme proxy d'usage d'OUTIL. `mammoth_kills`
    est crédité au GROUPE (chasse coopérative à mains nues, EDR 028, world_1_stoneage.py:715-718) →
    `frac_apex` peut dépasser `frac_craft` (apex atteint SANS lance). Lire la décomposition brute
    (`frac_craft` vs `frac_apex`, par_seed), jamais le label nu."""
    all_agents = [a for agents in per_seed_agents.values() for a in agents]
    frac_hunt = _frac(all_agents, "preys_eaten")
    frac_craft = _frac(all_agents, "spears_crafted")
    frac_apex = _frac(all_agents, "mammoth_kills")
    altars_solved_max = max((a.get("altars_solved", 0) for a in all_agents), default=0)
    verdict_autel = "AUTEL_MORT" if altars_solved_max == 0 else "AUTEL_VIVANT"
    if frac_craft < eps:
        verdict_funnel = "GAP_ACQUISITION"
    elif frac_apex < eps:
        verdict_funnel = "GAP_USAGE"
    else:
        verdict_funnel = "PATHWAY_VIVANT"
    return {"verdict_autel": verdict_autel, "verdict_funnel": verdict_funnel,
            "frac_hunt": frac_hunt, "frac_craft": frac_craft, "frac_apex": frac_apex,
            "total_spears": sum(a.get("spears_crafted", 0) for a in all_agents),
            "total_mammoth_kills": sum(a.get("mammoth_kills", 0) for a in all_agents),
            "altars_solved_max": altars_solved_max, "n_agents": len(all_agents),
            "par_seed": {str(s): _seed_summary(agents) for s, agents in per_seed_agents.items()}}


def run_era_funnel(seed, metab, payoff, num_agents, max_ticks, shared_db) -> List[Dict]:
    """UNE ère stoneage (sweet spot). Renvoie par agent TOUS (vivants + morts, env.agents +
    env.dead_agents, EDR 092) : {age, preys_eaten, spears_crafted, mammoth_kills, altars_solved}.
    Modelé sur run_era_organ (tools/dreaming_probe.py) mais SANS semis d'organe. Déterministe."""
    SeedManager(seed).seed_boundary(0)
    config = WorldConfig()
    config.base_metabolism = metab
    config.forage_payoff = payoff
    env = _prepare_world("stoneage", config, deterministic=True)

    genomes, _ntm = init_primordial_soup(num_agents=num_agents, import_agent_id=None,
                                         keep_memory=False, shared_db=shared_db, config=config)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=50.0)

    env.current_era = 1
    t = 0
    while len(env.agents) > 0 and t < max_ticks:
        env.step()
        t += 1

    all_agents = list(env.agents) + list(getattr(env, "dead_agents", []))
    out = [{"age": a.get("age", 0), "preys_eaten": a.get("preys_eaten", 0),
            "spears_crafted": a.get("spears_crafted", 0), "mammoth_kills": a.get("mammoth_kills", 0),
            "altars_solved": a.get("altars_solved", 0)} for a in all_agents]
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    return out


def main() -> Dict:
    os.environ["AGISEED_QUIET_LOG"] = "1"     # anti-segfault + vitesse, AVANT start()
    seeds = [int(s) for s in os.environ.get("AF_SEEDS", "0,1,2").split(",") if s.strip()]
    num_agents = int(os.environ.get("AF_NUM_AGENTS", "40"))
    max_ticks = int(os.environ.get("AF_MAX_TICKS", "300"))

    async_logger.start()
    try:
        shared_db = _acquire_shared_db()
        log.info("=== Sonde funnel autel/outil : seeds=%s agents=%d ticks=%d (sweet 0.25/3.0) ===",
                 seeds, num_agents, max_ticks)
        per_seed = {seed: run_era_funnel(seed, 0.25, 3.0, num_agents, max_ticks, shared_db)
                    for seed in seeds}
        result = funnel_verdict(per_seed)
    finally:
        async_logger.stop()

    result["config"] = {"seeds": [int(s) for s in seeds], "num_agents": num_agents,
                        "max_ticks": max_ticks, "metab": 0.25, "payoff": 3.0}
    h = Harness(seed=min(seeds) if seeds else 0, name="altar_tool_funnel", with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    log.info("VERDICT autel=%s funnel=%s | hunt=%.3f craft=%.3f apex=%.3f | spears=%d mammoth=%d altar_max=%d -> %s",
             result["verdict_autel"], result["verdict_funnel"], result["frac_hunt"],
             result["frac_craft"], result["frac_apex"], result["total_spears"],
             result["total_mammoth_kills"], result["altars_solved_max"], path)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
