"""Sonde de Dreaming (barreau 0, attaque du goulot d'exploration EDR 014, approche A).
L'organe MCTS (+0.5 drain) est-il (Q1) survivable au sweet spot vs létal, et (Q2) payant quand
présent ? Spec : docs/superpowers/specs/2026-06-23-Dreaming-Organ-Revival-design.md.
Diagnostic SEUL : observe, ne répare pas le moteur."""
import os
import sys
import logging
import statistics
from typing import List, Dict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.curriculum.competence import survival_competence
import numpy as np
from src.environments.config import WorldConfig
from src.seed_ai.harness import SeedManager, Harness
from src.graph_rag.async_logger import logger as async_logger
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from main_curriculum import _prepare_world, _acquire_shared_db

log = logging.getLogger("AGIseed.DreamingProbe")


def _has_organ(agent: Dict) -> bool:
    """True si l'agent porte l'organe MCTS (organ_genes[0]). Robuste aux champs manquants."""
    model = agent.get("model")
    genome = getattr(model, "genome", None)
    og = getattr(genome, "organ_genes", None)
    return bool(og is not None and len(og) > 0 and og[0])


def organ_prevalence(agents: List[Dict]) -> float:
    """Fraction des agents portant l'organe MCTS. Liste vide -> 0.0."""
    if not agents:
        return 0.0
    return sum(1 for a in agents if _has_organ(a)) / len(agents)


def q2_split(stats: List[Dict]) -> Dict:
    """Sépare les agents par rêve (total_dreams>0) et compare leur compétence-survie.
    Groupe vide -> compétence 0.0 (convention survival_competence)."""
    dreamers = [s for s in stats if s.get("total_dreams", 0) > 0]
    nondreamers = [s for s in stats if s.get("total_dreams", 0) == 0]
    c_d = survival_competence(dreamers)
    c_n = survival_competence(nondreamers)
    return {"dreamers_competence": c_d, "nondreamers_competence": c_n,
            "delta": c_d - c_n, "n_dreamers": len(dreamers), "n_nondreamers": len(nondreamers)}


def dreaming_verdict(delta_prev_sweet: float, delta_prev_lethal: float,
                     q2a_delta: float, q2b_ratio: float,
                     surv_eps: float = 0.05, pay_eps: float = 0.02) -> str:
    """Gate 4-cas. SURVIT = organe toléré au sweet spot (Δprev > -eps) ET moins purgé qu'au létal
    (pression nette > 0). PAYE = bénéfice intra-pop (q2a_delta > pay_eps) OU population on>off
    (q2b_ratio > 1+pay_eps)."""
    survives = (delta_prev_sweet > -surv_eps) and ((delta_prev_sweet - delta_prev_lethal) > 0)
    pays = (q2a_delta > pay_eps) or (q2b_ratio > 1.0 + pay_eps)
    if survives and pays:
        return "SURVIT_ET_PAYE"
    if survives and not pays:
        return "SURVIT_PAS_PAYE"
    if (not survives) and pays:
        return "PAYE_PAS_SURVIT"
    return "MORT"


def _set_organ(genome, on: bool) -> None:
    """Force organ_genes[0] (MCTS) sur un génome LOCAL. Préserve les autres organes."""
    og = np.array(genome.organ_genes, dtype=bool) if getattr(genome, "organ_genes", None) is not None \
        else np.array([False, False], dtype=bool)
    og[0] = bool(on)
    genome.organ_genes = og


def run_era_organ(target: str, seed: int, organ_fraction: float, metab: float, payoff: float,
                  num_agents: int, max_ticks: int, shared_db) -> List[Dict]:
    """UNE ère sur `target`, avec une fraction `organ_fraction` de la population portant l'organe
    MCTS (les `int(round(organ_fraction*len(genomes)))` premiers). Renvoie par agent (TOUS :
    vivants + morts, cf. EDR 092 — la population s'éteint à 100 %) : {age, total_dreams, has_organ}.
    Déterministe (memory_retriever neutralisé)."""
    SeedManager(seed).seed_boundary(0)
    config = WorldConfig()
    config.base_metabolism = metab
    config.forage_payoff = payoff
    env = _prepare_world(target, config, deterministic=True)

    genomes, _ntm = init_primordial_soup(num_agents=num_agents, import_agent_id=None,
                                         keep_memory=False, shared_db=shared_db, config=config)
    n_on = int(round(organ_fraction * len(genomes)))
    for i, g in enumerate(genomes):
        a = MambaAgent()
        a.from_genome(g)
        _set_organ(a.genome, i < n_on)  # FIX B (EDR 092) : semer sur le génome PROPRE de l'agent
        env.add_agent(a, energy=50.0)   # (after_genome deepcopy) -> évite l'aliasing d'init_primordial_soup

    env.current_era = 1
    t = 0
    while len(env.agents) > 0 and t < max_ticks:
        env.step()
        t += 1

    # FIX A (EDR 092) : la population s'éteint à 100 % (0 survivant) -> mesurer TOUS les agents
    # (vivants + morts). Le signal de sélection est la prévalence de l'organe parmi tous (reproduction
    # différentielle) + l'âge-à-la-mort ; PAS la prévalence des survivants (vide sous extinction).
    all_agents = list(env.agents) + list(getattr(env, "dead_agents", []))
    out = [{"age": a.get("age", 0), "total_dreams": a.get("total_dreams", 0),
            "has_organ": _has_organ(a)} for a in all_agents]
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    return out


from tools.curriculum_transfer import _sign_test_p

RATIO_CAP = 5.0


def _prevalence_from_stats(stats: List[Dict]) -> float:
    """Prévalence d'organe à partir des stats run_era_organ (clé has_organ)."""
    if not stats:
        return 0.0
    return sum(1 for s in stats if s["has_organ"]) / len(stats)


def run_q1(seeds, target, num_agents, max_ticks, shared_db) -> Dict:
    """Q1 : organe semé à 50%, prévalence de l'organe parmi TOUS les agents (reproduction
    différentielle = sélection) sweet vs létal -> pression énergétique nette sur l'organe (EDR 092)."""
    sweet, lethal = [], []
    for seed in seeds:
        s = run_era_organ(target, seed, 0.5, 0.25, 3.0, num_agents, max_ticks, shared_db)
        l = run_era_organ(target, seed, 0.5, 1.0, 1.0, num_agents, max_ticks, shared_db)
        sweet.append(_prevalence_from_stats(s) - 0.5)
        lethal.append(_prevalence_from_stats(l) - 0.5)
    dps = float(statistics.median(sweet)) if sweet else 0.0
    dpl = float(statistics.median(lethal)) if lethal else 0.0
    return {"delta_prev_sweet": dps, "delta_prev_lethal": dpl, "pressure": dps - dpl,
            "per_seed_sweet": sweet, "per_seed_lethal": lethal}


def run_q2(seeds, target, num_agents, max_ticks, shared_db) -> Dict:
    """Q2 : forcé-ON au sweet spot. (a) rêveurs vs non-rêveurs ; (b) apparié ON vs OFF (ratio survie)."""
    deltas, ratios, dreams_seen = [], [], 0
    for seed in seeds:
        on = run_era_organ(target, seed, 1.0, 0.25, 3.0, num_agents, max_ticks, shared_db)
        off = run_era_organ(target, seed, 0.0, 0.25, 3.0, num_agents, max_ticks, shared_db)
        split = q2_split(on)
        deltas.append(split["delta"])
        dreams_seen += sum(s["total_dreams"] for s in on)
        c_on, c_off = survival_competence(on), survival_competence(off)
        if c_on <= 1e-6 and c_off <= 1e-6:
            ratio = 1.0
        else:
            ratio = min(c_on / max(c_off, 1e-6), RATIO_CAP)
        ratios.append(ratio)
    q2a_delta = float(statistics.median(deltas)) if deltas else 0.0
    q2b_ratio = float(statistics.median(ratios)) if ratios else 1.0
    effective = [r for r in ratios if r != 1.0]
    sign_p = _sign_test_p(sum(1 for r in effective if r > 1.0), len(effective))
    n_fav = sum(1 for r in ratios if r > 1.0)
    return {"q2a_delta": q2a_delta, "q2b_ratio": q2b_ratio, "n_favorable": n_fav,
            "n": len(ratios), "sign_p": sign_p, "total_dreams_seen": dreams_seen,
            "per_seed_delta": deltas, "per_seed_ratio": ratios}


def main() -> Dict:
    os.environ["AGISEED_QUIET_LOG"] = "1"     # anti-segfault + vitesse (EDR 091), AVANT start()
    target = os.environ.get("DP_TARGET", "stoneage")
    seeds = [int(s) for s in os.environ.get("DP_SEEDS", "0,1,2").split(",") if s.strip()]
    num_agents = int(os.environ.get("DP_NUM_AGENTS", "40"))
    max_ticks = int(os.environ.get("DP_MAX_TICKS", "400"))
    mode = os.environ.get("DP_MODE", "both")

    async_logger.start()
    try:
        shared_db = _acquire_shared_db()
        q1 = run_q1(seeds, target, num_agents, max_ticks, shared_db) if mode in ("q1", "both") else {}
        q2 = run_q2(seeds, target, num_agents, max_ticks, shared_db) if mode in ("q2", "both") else {}
    finally:
        async_logger.stop()

    verdict = dreaming_verdict(q1.get("delta_prev_sweet", -1.0), q1.get("delta_prev_lethal", -1.0),
                               q2.get("q2a_delta", 0.0), q2.get("q2b_ratio", 1.0)) if mode == "both" \
        else "PARTIEL"
    result = {"verdict": verdict, "q1": q1, "q2": q2,
              "config": {"target": target, "seeds": seeds, "num_agents": num_agents,
                         "max_ticks": max_ticks, "mode": mode}}
    h = Harness(seed=min(seeds) if seeds else 0, name="dreaming_probe", with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    log.info("VERDICT=%s | Q1 pressure=%.3f (sweet=%.3f letal=%.3f) | Q2 q2a=%.3f q2b=%.3f dreams=%d -> %s",
             verdict, q1.get("pressure", 0.0), q1.get("delta_prev_sweet", 0.0),
             q1.get("delta_prev_lethal", 0.0), q2.get("q2a_delta", 0.0), q2.get("q2b_ratio", 1.0),
             q2.get("total_dreams_seen", 0), path)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
