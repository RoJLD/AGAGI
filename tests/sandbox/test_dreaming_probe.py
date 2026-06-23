import numpy as np
from types import SimpleNamespace
from tools.dreaming_probe import organ_prevalence, _has_organ


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
