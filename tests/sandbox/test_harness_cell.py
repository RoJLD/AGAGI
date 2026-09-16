# tests/sandbox/test_harness_cell.py
"""Runner de cellule testé par INJECTION (P2.56) : un learner jouet, une règle scellée dans un dossier temporaire,
une sentinelle qui LÈVE si le corps est atteint avant les gardes, une horloge factice pour l'abandon.

Décision contrôleur (tâche 6, 2026-09-16) : le learner jouet `CounterLearner` du brief est LINÉAIRE et ne peut
pas apprendre la parité/XOR -- il n'acquerrait jamais. Le cas de succès complet utilise donc
`TabularLearner(honest=True)` (vérité-terrain, tools/harness/learners/tabular.py), avec `piece="table"` ;
les ablations de `ToyParity` (tests/sandbox/test_harness_task.py) sont nommées `permute_a` (must_bite) et
`inject_noise` (must_bite=False) -- pas `permute_nothing` (nom du brief d'origine, renommé à la tâche 3)."""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai.harness_task import Ablation, DemandDeclaration  # noqa: E402
from tools.cost_guard import CostTooHighToStart  # noqa: E402
from tools.experiment_preflight import PreflightError  # noqa: E402
from tools.harness.cell import run_harness_cell  # noqa: E402
from tools.harness.learners.tabular import TabularLearner  # noqa: E402
from tools.preregister import PreregistrationTampered, preregister  # noqa: E402
from tests.sandbox.test_harness_learner import CounterLearner  # noqa: E402
from tests.sandbox.test_harness_task import ToyParity  # noqa: E402

SEEDS = list(range(12))


def _rule():
    return {"question": "cellule jouet", "n_floor": 12, "piece": "table", "sweep": [{"lr": 1.0}, {"lr": 0.5}],
            "ablations": [{"name": "permute_a", "site": "input", "must_bite": True},
                          {"name": "inject_noise", "site": "input", "must_bite": False}],
            "bayes_floors": {"permute_a": 0.5}, "incapable_ceiling": None,
            "min_sep": 0.05, "prior_max": 0.6, "oracle_min": 0.9, "collapse_factor": 1.5, "alive_margin": 0.05,
            "matched_sham": None, "budget_s": 600.0,
            "dv_primaire": "`hits` par seed ; `ratio_within` ; `sep_ref` ; `dose.updates`",
            "discrimination": {k: "…" for k in ("INCOMPLET", "NOT_ACQUIRED", "DEMANDED_ACQUIRED_NECESSARY", "AUTRE")}}


@pytest.fixture
def sealed(tmp_path):
    preregister("HARNESS-TOY", _rule(), _dir=str(tmp_path))
    return str(tmp_path)


def _whole_rule():
    """Décision 3 (contrôleur) : `rule_path` sélectionne un sous-dict d'une règle scellée qui en porte
    plusieurs (`{"cellules": {"X": <rule>, ...}}`)."""
    return {"cellules": {"X": _rule()}, "meta": "conteneur multi-cellules, jamais lu comme une regle"}


@pytest.fixture
def sealed_whole(tmp_path):
    preregister("HARNESS-TOY-WHOLE", _whole_rule(), _dir=str(tmp_path))
    return str(tmp_path)


class _Sentinel(CounterLearner):
    def build(self, *a, **k):
        raise AssertionError("CORPS ATTEINT : build appelé avant les gardes")


def test_task_contract_refuses_before_any_build(sealed, tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "res"))
    task = ToyParity(with_nobite=False)
    with pytest.raises(PreflightError, match="must_bite=False"):
        run_harness_cell(task, _Sentinel(), "HARNESS-TOY", seeds=SEEDS, episodes=5, out_name="toy", prereg_dir=sealed)


def test_tampered_rule_refuses_before_any_build(sealed, tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "res"))
    p = os.path.join(sealed, "HARNESS-TOY.json")
    payload = json.load(open(p, encoding="utf-8"))
    payload["rule"]["n_floor"] = 3
    json.dump(payload, open(p, "w", encoding="utf-8"))
    with pytest.raises(PreregistrationTampered):
        run_harness_cell(ToyParity(), _Sentinel(), "HARNESS-TOY", seeds=SEEDS, episodes=5, out_name="toy", prereg_dir=sealed)


def test_cost_projection_refuses_before_any_build(sealed, tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "res"))
    with pytest.raises(CostTooHighToStart):
        run_harness_cell(ToyParity(), _Sentinel(), "HARNESS-TOY", seeds=SEEDS, episodes=5, out_name="toy",
                         prereg_dir=sealed, budget_s=1.0, unit_s=10.0)


def test_rule_path_selects_a_sub_rule_and_missing_key_raises_before_any_build(sealed_whole, tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "res"))
    with pytest.raises(KeyError):
        run_harness_cell(ToyParity(), _Sentinel(), "HARNESS-TOY-WHOLE", seeds=SEEDS, episodes=5,
                         out_name="toy_rp_bad", prereg_dir=sealed_whole, rule_path=["cellules", "nope"])
    out = run_harness_cell(ToyParity(), TabularLearner(honest=True), "HARNESS-TOY-WHOLE", seeds=SEEDS, episodes=40,
                           out_name="toy_rp", prereg_dir=sealed_whole, rule_path=["cellules", "X"],
                           n_agents=8, eval_batches=10)
    assert out["verdict"]["verdict"] == "DEMANDED_ACQUIRED_NECESSARY"


def test_unit_is_the_seed_and_reference_is_dose_matched(sealed, tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "res"))
    out = run_harness_cell(ToyParity(), TabularLearner(honest=True), "HARNESS-TOY", seeds=SEEDS, episodes=40,
                           out_name="toy", prereg_dir=sealed, n_agents=8, eval_batches=10)
    db = out["db"]
    assert sorted(int(s) for s in db["arms"]["A"]["last"]) == SEEDS
    for s in SEEDS:
        assert db["arms"]["A0"]["dose"][str(s)]["calls"] == db["arms"]["A"]["dose"][str(s)]["calls"] == 40
        assert db["arms"]["A0"]["dose"][str(s)]["updates"] == 0
    assert set(db["eval"]["ablated"]) == {"permute_a", "inject_noise"}
    assert out["verdict"]["verdict"] == "DEMANDED_ACQUIRED_NECESSARY"       # la table est nécessaire par construction
    assert os.path.exists(out["path"])
    saved = json.load(open(out["path"], encoding="utf-8"))
    assert saved["data"]["regime"]["episodes"] == 40 and saved["data"]["preregistration"]["name"] == "HARNESS-TOY"
    assert saved["data"]["design"]["replication_unit"] == "seed" and saved["data"]["design"]["n_independent"] == 12


def test_abandoned_seed_is_counted_and_yields_INCONCLUSIVE_N(sealed, tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "res"))
    t = {"now": 0.0}

    def clock():
        t["now"] += 0.0 if t["now"] < 5 else 1000.0     # les premiers appels sont gratuits, puis le temps saute
        t["now"] += 0.001
        return t["now"]

    out = run_harness_cell(ToyParity(), CounterLearner(), "HARNESS-TOY", seeds=SEEDS, episodes=5, out_name="toy",
                           prereg_dir=sealed, n_agents=8, eval_batches=5, budget_s=3600.0, unit_s=0.001, clock=clock)
    assert out["verdict"]["verdict"] == "INCONCLUSIVE_N"
    assert any(out["db"]["abandoned"][arm] for arm in out["db"]["abandoned"])
