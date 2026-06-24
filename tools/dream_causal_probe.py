"""Sonde d'intervention causale du dreaming (Phase 2). Le dreaming CAUSE-t-il un meilleur sort, ou
corrèle-t-il à la détresse (EDR 093/094) ? Force l'acte + la profondeur du rêve via le hook gated
MambaBatchModel.FORCE_DREAM ; balaye {off,1,4,8} -> courbe dose-réponse de la survie.
Spec : docs/superpowers/specs/2026-06-24-Dream-Causal-Intervention-design.md. Diagnostic causal."""
import os
import sys
import logging
import statistics
from typing import List, Dict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.curriculum_transfer import _sign_test_p
from tools.dreaming_probe import run_era_organ
from src.curriculum.competence import survival_competence
from src.agents.mamba_agent import MambaBatchModel
from src.environments.config import WorldConfig
from src.seed_ai.harness import Harness
from src.graph_rag.async_logger import logger as async_logger
from main_curriculum import _acquire_shared_db

log = logging.getLogger("AGIseed.DreamCausal")


def _paired_ratios(arm: List[float], off: List[float]) -> List[float]:
    m = min(len(arm), len(off))
    return [arm[i] / max(off[i], 1e-6) for i in range(m)]


def dose_response_verdict(per_arm: Dict, eps: float = 0.02) -> Dict:
    """Verdict ancré sur le bras le plus profond (max K) vs off, apparié par seed. Renvoie aussi la
    courbe dose-réponse complète (ratio apparié médian de chaque bras-K vs off)."""
    off = per_arm.get("off", [])
    ks = sorted(k for k in per_arm if k != "off")
    if not off or not ks:
        return {"ratio": 1.0, "sign_p": 1.0, "n_favorable": 0, "n": 0,
                "verdict": "NEUTRE", "ratios_par_K": {}}
    ratios_par_K = {}
    for k in ks:
        pr = _paired_ratios(per_arm[k], off)
        ratios_par_K[str(k)] = float(statistics.median(pr)) if pr else 1.0
    pr = _paired_ratios(per_arm[ks[-1]], off)            # bras le plus profond
    ratio = float(statistics.median(pr)) if pr else 1.0
    effective = [r for r in pr if r != 1.0]
    sign_p = _sign_test_p(sum(1 for r in effective if r > 1.0), len(effective))
    n_fav = sum(1 for r in pr if r > 1.0)
    if ratio > 1.0 + eps and sign_p < 0.1:
        verdict = "CAUSE_BENEFIQUE"
    elif ratio < 1.0 - eps and sign_p < 0.1:
        verdict = "CAUSE_NUISIBLE"
    else:
        verdict = "NEUTRE"
    return {"ratio": ratio, "sign_p": sign_p, "n_favorable": n_fav, "n": len(pr),
            "verdict": verdict, "ratios_par_K": ratios_par_K}


def run_causal(seeds, target, num_agents, max_ticks, shared_db, ks=(1, 4, 8)) -> Dict:
    """Par seed, balaye les bras ["off", *ks] à organe ON (100%) + sweet spot. Pose FORCE_DREAM
    AVANT l'ère, le REMET à None en finally (anti-pollution). Survie appariée par seed -> verdict."""
    arms = ["off", *[int(k) for k in ks]]
    per_arm = {arm: [] for arm in arms}
    for seed in seeds:
        for arm in arms:
            MambaBatchModel.FORCE_DREAM = arm if arm == "off" else int(arm)
            try:
                stats = run_era_organ(target, seed, 1.0, 0.25, 3.0, num_agents, max_ticks, shared_db)
            finally:
                MambaBatchModel.FORCE_DREAM = None      # OBLIGATOIRE : etat global de classe
            per_arm[arm].append(survival_competence(stats))
        log.info("  seed=%s survie %s", seed,
                 {str(a): round(per_arm[a][-1], 3) for a in arms})
    verdict = dose_response_verdict(per_arm)
    return {**verdict, "per_arm": {str(a): v for a, v in per_arm.items()},
            "config": {"target": target, "seeds": [int(s) for s in seeds], "ks": list(ks),
                       "num_agents": num_agents, "max_ticks": max_ticks}}


def main() -> Dict:
    os.environ["AGISEED_QUIET_LOG"] = "1"     # anti-segfault + vitesse, AVANT start()
    target = os.environ.get("DC_TARGET", "stoneage")
    seeds = [int(s) for s in os.environ.get("DC_SEEDS", "0,1,2").split(",") if s.strip()]
    ks = tuple(int(k) for k in os.environ.get("DC_KS", "1,4,8").split(",") if k.strip())
    num_agents = int(os.environ.get("DC_NUM_AGENTS", "40"))
    max_ticks = int(os.environ.get("DC_MAX_TICKS", "400"))

    async_logger.start()
    try:
        shared_db = _acquire_shared_db()
        log.info("=== Sonde causale : cible=%s seeds=%s ks=%s agents=%d ticks=%d ===",
                 target, seeds, ks, num_agents, max_ticks)
        result = run_causal(seeds, target, num_agents, max_ticks, shared_db, ks=ks)
    finally:
        async_logger.stop()

    h = Harness(seed=min(seeds) if seeds else 0, name="dream_causal", with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    log.info("VERDICT=%s ratio(Kmax/off)=%.3f sign_p=%.3f | courbe=%s -> %s",
             result["verdict"], result["ratio"], result["sign_p"], result["ratios_par_K"], path)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
