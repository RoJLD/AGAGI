import numpy as np
from types import SimpleNamespace
from tools.dreaming_probe import organ_prevalence, _has_organ, q2_split
from src.curriculum.competence import AGE_REF


def _agent(organ_on):
    g = SimpleNamespace(organ_genes=np.array([organ_on, False], dtype=bool))
    return {"model": SimpleNamespace(genome=g)}


def test_organ_prevalence_known_fractions():
    assert organ_prevalence([]) == 0.0
    assert organ_prevalence([_agent(True), _agent(True)]) == 1.0
    assert organ_prevalence([_agent(False), _agent(False)]) == 0.0
    assert organ_prevalence([_agent(True), _agent(False)]) == 0.5


def test_has_organ_robust_to_missing():
    assert _has_organ({"model": SimpleNamespace(genome=SimpleNamespace(organ_genes=None))}) is False
    assert _has_organ({"model": None}) is False
    assert _has_organ(_agent(True)) is True


def test_q2_split_separates_dreamers():
    stats = [
        {"age": int(AGE_REF), "total_dreams": 3},      # rêveur, compétence haute
        {"age": int(AGE_REF), "total_dreams": 1},      # rêveur
        {"age": 10, "total_dreams": 0},                # non-rêveur, basse
        {"age": 10, "total_dreams": 0},                # non-rêveur
    ]
    out = q2_split(stats)
    assert out["n_dreamers"] == 2 and out["n_nondreamers"] == 2
    assert out["dreamers_competence"] == 1.0           # médiane âge = AGE_REF
    assert out["delta"] > 0                             # rêveurs > non-rêveurs


def test_q2_split_handles_zero_dreamers():
    out = q2_split([{"age": 10, "total_dreams": 0}])
    assert out["n_dreamers"] == 0
    assert out["dreamers_competence"] == 0.0            # groupe vide -> 0.0


from tools.dreaming_probe import dreaming_verdict


def test_verdict_four_cases():
    # survit (sweet toléré ET pression>0) ET paye (q2a delta>pay_eps OU q2b ratio>1+pay_eps)
    assert dreaming_verdict(0.0, -0.3, 0.10, 1.20) == "SURVIT_ET_PAYE"
    assert dreaming_verdict(0.0, -0.3, 0.00, 1.00) == "SURVIT_PAS_PAYE"
    # ne survit pas (sweet purgé) mais paye
    assert dreaming_verdict(-0.4, -0.45, 0.10, 1.20) == "PAYE_PAS_SURVIT"
    assert dreaming_verdict(-0.4, -0.45, 0.00, 1.00) == "MORT"


import os
import pytest


@pytest.mark.slow
def test_run_era_organ_smoke_seeds_organ():
    """Smoke biosphère : une ère courte, ~50% organe semé -> renvoie des stats avec has_organ booléen."""
    os.environ["AGISEED_QUIET_LOG"] = "1"
    from src.graph_rag.async_logger import logger as async_logger
    from tools.dreaming_probe import run_era_organ, _acquire_shared_db
    async_logger.start()
    try:
        db = _acquire_shared_db()
        stats = run_era_organ("stoneage", seed=0, organ_fraction=0.5, metab=0.25, payoff=3.0,
                              num_agents=20, max_ticks=40, shared_db=db)
    finally:
        async_logger.stop()
    assert isinstance(stats, list)
    for s in stats:
        assert set(s) == {"age", "total_dreams", "has_organ"}
        assert isinstance(s["has_organ"], bool)
