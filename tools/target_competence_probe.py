"""Sonde de plancher (prérequis Dev #3, AVANT le run de transfert à l'échelle).

Question : la cible produit-elle une compétence NON-PLANCHER ? Sinon le ratio de transfert
compare bruit/bruit (cf. pilote micro-échelle, verdict NEUTRE forcé).

Méthode : on échantillonne la grandeur EXACTE que le harnais de transfert utilisera comme
dénominateur — `final_competence` d'une ère tabula-rasa (soupe fraîche, import=None) sur la
cible, à l'échelle réelle de l'expérience (num_agents, max_ticks). On le fait K fois (ères i.i.d.,
car le bras tabula-rasa ne transfère rien entre ères) et on DÉCOMPOSE en signaux bruts
(altars_solved, age, preys, dreams) -> on sait non seulement SI mais POURQUOI c'est au plancher.

Repro : memory_retriever neutralisé (stop+clear) avant la boucle (verrou Dev #3).

Usage :
    CT_TARGET=industrial CT_K=8 CT_NUM_AGENTS=40 CT_MAX_TICKS=400 python tools/target_competence_probe.py
"""
import os
import sys
import logging
import statistics

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.environments.config import WorldConfig
from src.curriculum.competence import competence_for
from src.seed_ai.harness import SeedManager, Harness
from src.seed_ai.persistence import calculate_life_score, load_hall_of_fame
from src.graph_rag.async_logger import logger as async_logger
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from main_curriculum import _prepare_world, _acquire_shared_db

log = logging.getLogger("AGIseed.TargetProbe")

# Seuils de décision (À AJUSTER après lecture des chiffres bruts — c'est un jugement scientifique).
# "Non-plancher" = la métrique a de la marge pour discriminer deux bras.
MEDIAN_FLOOR = 0.15   # compétence médiane sur K ères au-dessus de ça -> signal franc
MAX_FLOOR = 0.25      # OU au moins une ère dépasse ça -> il EXISTE un régime discriminant


def _median(xs):
    return float(statistics.median(xs)) if xs else 0.0


def _champion_genome():
    """Génome du #1 du HoF (plafond : un connectome RÉELLEMENT évolué, pas de la soupe fraîche)."""
    _v, entries = load_hall_of_fame()
    if not entries:
        raise RuntimeError("HoF vide : mode champion impossible.")
    return entries[0].genome


def run_probe(target, k, num_agents, max_ticks, shared_db, mode="tabula"):
    """K ères sur la cible -> par ère : compétence + médianes des signaux bruts.
    mode='tabula' : soupe fraîche (dénominateur réel C_tabula). mode='champion' : clones du
    champion HoF (plafond : le contraste tabula<champion EST le signal de transfert mesurable)."""
    comp_fn = competence_for(target)
    config = WorldConfig()
    champ_g = _champion_genome() if mode == "champion" else None
    per_era = []

    for i in range(k):
        SeedManager(i).seed_boundary(0)                       # appariable / reproductible
        env = _prepare_world(target, config, deterministic=True)

        if mode == "champion":
            for _ in range(num_agents):
                a = MambaAgent()
                a.from_genome(champ_g)
                env.add_agent(a, energy=50.0)
        else:
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

        all_agents = env.agents + env.dead_agents
        stats = [{"age": a.get("age", 0), "energy": a.get("energy", 0.0),
                  "preys_eaten": a.get("preys_eaten", 0), "altars_solved": a.get("altars_solved", 0),
                  "total_dreams": a.get("total_dreams", 0)} for a in all_agents]
        competence = comp_fn(stats)

        row = {
            "era": i, "competence": round(competence, 4), "n": len(all_agents), "ticks": t,
            "med_age": _median([s["age"] for s in stats]),
            "med_altars": _median([s["altars_solved"] for s in stats]),
            "med_preys": _median([s["preys_eaten"] for s in stats]),
            "med_dreams": _median([s["total_dreams"] for s in stats]),
            "max_altars": max((s["altars_solved"] for s in stats), default=0),
            "max_age": max((s["age"] for s in stats), default=0),
        }
        per_era.append(row)
        log.info("  era=%d C=%.3f | med(age=%.0f altars=%.1f preys=%.1f dreams=%.1f) | "
                 "max(altars=%d age=%d) n=%d t=%d", i, competence, row["med_age"], row["med_altars"],
                 row["med_preys"], row["med_dreams"], row["max_altars"], row["max_age"], row["n"], t)

        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()

    comps = [r["competence"] for r in per_era]
    med_c, max_c = _median(comps), (max(comps) if comps else 0.0)
    floor = not (med_c > MEDIAN_FLOOR or max_c > MAX_FLOOR)
    return {"target": target, "mode": mode, "k": k, "num_agents": num_agents, "max_ticks": max_ticks,
            "median_competence": med_c, "max_competence": max_c,
            "verdict": "PLANCHER" if floor else "SIGNAL", "per_era": per_era}


def main():
    target = os.environ.get("CT_TARGET", "industrial")
    mode = os.environ.get("CT_MODE", "tabula")
    k = int(os.environ.get("CT_K", "8"))
    num_agents = int(os.environ.get("CT_NUM_AGENTS", "40"))
    max_ticks = int(os.environ.get("CT_MAX_TICKS", "400"))

    async_logger.start()
    try:
        shared_db = _acquire_shared_db()
        log.info("=== Sonde plancher : cible=%s mode=%s K=%d agents=%d ticks=%d ===",
                 target, mode, k, num_agents, max_ticks)
        result = run_probe(target, k, num_agents, max_ticks, shared_db, mode=mode)
    finally:
        async_logger.stop()

    h = Harness(seed=0, name="target_competence_probe", with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    log.info("VERDICT=%s | median_C=%.3f max_C=%.3f (seuils med>%.2f ou max>%.2f) -> %s",
             result["verdict"], result["median_competence"], result["max_competence"],
             MEDIAN_FLOOR, MAX_FLOOR, path)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
