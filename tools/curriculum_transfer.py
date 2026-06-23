"""Harnais Ratio de Transfert (Dev #3, mesure). Le curriculum développemental transfère-t-il mieux
que tabula-rasa ? Expérience appariée multi-seed à BUDGET COMPUTE ÉGAL, verdict + provenance ledger.
Spec : docs/superpowers/specs/2026-06-23-Curriculum-Transfer-design.md"""
import os
import sys
import math
import logging
import statistics
from typing import List, Dict, Optional, Callable

# Lançable directement (`python tools/curriculum_transfer.py`) : met la racine projet sur le path
# (sinon sys.path[0]=tools/ et `src` est introuvable). No-op quand importé (racine déjà sur le path).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.curriculum.runner import CurriculumRunner, WorldStage, GraduationConfig
from src.environments.config import WorldConfig
from src.seed_ai.harness import SeedManager, Harness
from src.graph_rag.async_logger import logger as async_logger
from main_curriculum import make_run_era_fn, _acquire_shared_db, DEFAULT_LADDER

log = logging.getLogger("AGIseed.CurriculumTransfer")


def _sign_test_p(k: int, n: int) -> float:
    """p-value binomiale exacte BILATÉRALE sous H0 p=0.5 (test de signe). Sans dépendance (math.comb)."""
    if n <= 0:
        return 1.0
    k_hi = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(k_hi, n + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def compute_transfer_verdict(ratios: List[float], neutral_band: float = 0.05) -> Dict:
    """ratio par seed -> {n, median_ratio, n_favorable, sign_p, verdict}. PUR (testable sans biosphère)."""
    n = len(ratios)
    if n == 0:
        return {"n": 0, "median_ratio": 0.0, "n_favorable": 0, "sign_p": 1.0, "verdict": "NEUTRE"}
    med = float(statistics.median(ratios))
    n_fav = sum(1 for r in ratios if r > 1.0)
    effective = [r for r in ratios if r != 1.0]
    sign_p = _sign_test_p(sum(1 for r in effective if r > 1.0), len(effective))
    if med > 1.0 + neutral_band and 2 * n_fav > n:
        verdict = "TRANSFERE"
    elif med < 1.0 - neutral_band and 2 * n_fav < n:
        verdict = "NUIT"
    else:
        verdict = "NEUTRE"
    return {"n": n, "median_ratio": med, "n_favorable": n_fav, "sign_p": sign_p, "verdict": verdict}


def _competence_on_target(transcript) -> float:
    return float(transcript[-1]["final_competence"]) if transcript else 0.0


def run_transfer_experiment(seeds, ladder: Optional[List[str]] = None, target: Optional[str] = None,
                            num_agents: int = 40, max_ticks: int = 300,
                            grad_cfg: Optional[GraduationConfig] = None,
                            run_era_fn: Optional[Callable] = None, manage_logger: bool = True) -> Dict:
    """Deux bras par seed (curriculum vs cible seule à BUDGET ÉGAL), apparié, -> verdict.
    run_era_fn injecté -> orchestration testable sans biosphère (sinon construit via make_run_era_fn)."""
    ladder = list(ladder) if ladder else list(DEFAULT_LADDER)
    target = target or ladder[-1]
    grad_cfg = grad_cfg or GraduationConfig(max_eras=12)

    owns_engine = run_era_fn is None
    if owns_engine and manage_logger:
        async_logger.start()
    try:
        if owns_engine:
            shared_db = _acquire_shared_db()
            # deterministic=True : memory_retriever neutralise avant la boucle -> bras appaires
            # exactement reproductibles (verrou repro Dev #3 ; sans ca, mesure non publiable).
            run_era_fn = make_run_era_fn(shared_db, WorldConfig(), num_agents=num_agents,
                                         max_ticks=max_ticks, deterministic=True)

        per_seed = []
        for seed in seeds:
            SeedManager(seed).seed_boundary(0)                              # bras curriculum
            tc = CurriculumRunner([WorldStage(w) for w in ladder], run_era_fn, grad_cfg).run()
            c_curr = _competence_on_target(tc)
            total_eras = sum(int(row["eras"]) for row in tc)

            SeedManager(seed).seed_boundary(0)                              # bras tabula-rasa (même seed)
            no_grad = GraduationConfig(window=grad_cfg.window, eps_plateau=grad_cfg.eps_plateau,
                                       c_floor=1.1, patience=grad_cfg.patience,
                                       max_eras=max(1, total_eras))         # ne diplôme jamais -> T ères
            tt = CurriculumRunner([WorldStage(target)], run_era_fn, no_grad).run()
            c_tabula = _competence_on_target(tt)

            ratio = c_curr / max(c_tabula, 1e-6)
            per_seed.append({"seed": int(seed), "C_curr": c_curr, "C_tabula": c_tabula,
                             "total_eras": total_eras, "ratio": ratio})
            log.info("seed=%s C_curr=%.3f C_tabula=%.3f T=%d ratio=%.3f",
                     seed, c_curr, c_tabula, total_eras, ratio)

        verdict = compute_transfer_verdict([p["ratio"] for p in per_seed])
        return {**verdict, "per_seed": per_seed,
                "config": {"ladder": ladder, "target": target, "seeds": [int(s) for s in seeds],
                           "num_agents": num_agents, "max_ticks": max_ticks, "max_eras": grad_cfg.max_eras}}
    finally:
        if owns_engine and manage_logger:
            async_logger.stop()


def main():
    seeds = [int(s) for s in os.environ.get("CT_SEEDS", "0,1,2,3,4").split(",") if s.strip()]
    ladder = [w for w in os.environ.get("CT_LADDER", ",".join(DEFAULT_LADDER)).split(",") if w.strip()]
    target = os.environ.get("CT_TARGET") or (ladder[-1] if ladder else None)
    num_agents = int(os.environ.get("CT_NUM_AGENTS", "40"))
    max_ticks = int(os.environ.get("CT_MAX_TICKS", "300"))
    grad_cfg = GraduationConfig(max_eras=int(os.environ.get("CT_MAX_ERAS", "12")))

    result = run_transfer_experiment(seeds, ladder=ladder, target=target,
                                     num_agents=num_agents, max_ticks=max_ticks, grad_cfg=grad_cfg)

    meta_seed = min(seeds) if seeds else 0
    h = Harness(seed=meta_seed, name="curriculum_transfer", with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    log.info("VERDICT=%s median_ratio=%.3f (n_fav=%d/%d, sign_p=%.3f) -> %s",
             result["verdict"], result["median_ratio"], result["n_favorable"], result["n"],
             result["sign_p"], path)
    return path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
