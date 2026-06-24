"""Sonde de signature de détresse du dreaming (Phase 1-A, corrélationnel). Les rêves se concentrent-
ils chez les agents proches de la mort ? Spec : docs/superpowers/specs/2026-06-24-Dream-Distress-
Signature-design.md. ORIENTANT, pas définitif (la Phase 2 causale tranche). Diagnostic seul."""
import os
import sys
import logging
import statistics
from typing import List, Dict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.curriculum_transfer import _sign_test_p


def dream_rate(agent: Dict) -> float:
    """Taux de rêve ajusté à l'exposition : total_dreams / max(age, 1) (age 0 -> dénominateur 1)."""
    return agent.get("total_dreams", 0) / max(agent.get("age", 0), 1)


def distress_split(stats: List[Dict], age_floor: int = 10) -> Dict:
    """Filtre age >= age_floor (écarte l'artefact petit-âge), split par âge médian, compare le taux
    de rêve médian des court-vivants vs long-vivants. delta = rate_short - rate_long (>0 = détresse)."""
    kept = [s for s in stats if s.get("age", 0) >= age_floor]
    if not kept:
        return {"rate_short": 0.0, "rate_long": 0.0, "delta": 0.0, "n_short": 0, "n_long": 0}
    med_age = statistics.median([s["age"] for s in kept])
    short = [s for s in kept if s["age"] < med_age]
    long = [s for s in kept if s["age"] >= med_age]
    r_short = float(statistics.median([dream_rate(s) for s in short])) if short else 0.0
    r_long = float(statistics.median([dream_rate(s) for s in long])) if long else 0.0
    return {"rate_short": r_short, "rate_long": r_long, "delta": r_short - r_long,
            "n_short": len(short), "n_long": len(long)}


def distress_verdict(deltas: List[float], delta_eps: float = 0.0) -> Dict:
    """Agrège les delta par seed. DETRESSE = court-vivants rêvent plus (median > eps ET sign_p<0.1) ;
    BENEFIQUE = long-vivants rêvent plus (median < -eps ET sign_p<0.1) ; NEUTRE sinon. sign_p calculé
    sur les deltas EFFECTIFS (≠0) -> évite k>n (pattern compute_transfer_verdict)."""
    if not deltas:
        return {"median_delta": 0.0, "n_favorable": 0, "sign_p": 1.0, "verdict": "NEUTRE"}
    med = float(statistics.median(deltas))
    n_fav = sum(1 for d in deltas if d > 0.0)
    effective = [d for d in deltas if d != 0.0]
    sign_p = _sign_test_p(sum(1 for d in effective if d > 0.0), len(effective))
    if med > delta_eps and sign_p < 0.1:
        verdict = "DETRESSE"
    elif med < -delta_eps and sign_p < 0.1:
        verdict = "BENEFIQUE"
    else:
        verdict = "NEUTRE"
    return {"median_delta": med, "n_favorable": n_fav, "sign_p": sign_p, "verdict": verdict}


from src.environments.config import WorldConfig
from src.seed_ai.harness import Harness
from src.graph_rag.async_logger import logger as async_logger
from main_curriculum import _acquire_shared_db
from tools.dreaming_probe import run_era_organ

log = logging.getLogger("AGIseed.DreamDistress")


def run_distress(seeds, target, num_agents, max_ticks, shared_db) -> Dict:
    """Par seed : une ère organe-ON (organ_fraction=1.0) au sweet spot -> distress_split -> delta.
    Agrège en verdict. Le signal : les court-vivants rêvent-ils plus (détresse) ?"""
    per_seed = []
    for seed in seeds:
        stats = run_era_organ(target, seed, 1.0, 0.25, 3.0, num_agents, max_ticks, shared_db)
        split = distress_split(stats)
        per_seed.append({"seed": int(seed), **split})
        log.info("  seed=%s rate_short=%.3f rate_long=%.3f delta=%.3f (n_short=%d n_long=%d)",
                 seed, split["rate_short"], split["rate_long"], split["delta"],
                 split["n_short"], split["n_long"])
    verdict = distress_verdict([p["delta"] for p in per_seed])
    return {**verdict, "per_seed": per_seed,
            "config": {"target": target, "seeds": [int(s) for s in seeds],
                       "num_agents": num_agents, "max_ticks": max_ticks}}


def main() -> Dict:
    os.environ["AGISEED_QUIET_LOG"] = "1"     # anti-segfault + vitesse (EDR 091/092), AVANT start()
    target = os.environ.get("DD_TARGET", "stoneage")
    seeds = [int(s) for s in os.environ.get("DD_SEEDS", "0,1,2").split(",") if s.strip()]
    num_agents = int(os.environ.get("DD_NUM_AGENTS", "40"))
    max_ticks = int(os.environ.get("DD_MAX_TICKS", "400"))

    async_logger.start()
    try:
        shared_db = _acquire_shared_db()
        log.info("=== Sonde detresse : cible=%s seeds=%s agents=%d ticks=%d ===",
                 target, seeds, num_agents, max_ticks)
        result = run_distress(seeds, target, num_agents, max_ticks, shared_db)
    finally:
        async_logger.stop()

    h = Harness(seed=min(seeds) if seeds else 0, name="dream_distress", with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    log.info("VERDICT=%s median_delta=%.3f (n_fav=%d/%d, sign_p=%.3f) -> %s",
             result["verdict"], result["median_delta"], result["n_favorable"],
             len(result["per_seed"]), result["sign_p"], path)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
