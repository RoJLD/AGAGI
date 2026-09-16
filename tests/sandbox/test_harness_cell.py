# tests/sandbox/test_harness_cell.py
"""Runner de cellule testé par INJECTION (P2.56) : un learner jouet, une règle scellée dans un dossier temporaire,
une sentinelle qui LÈVE si le corps est atteint avant les gardes, une horloge factice pour l'abandon.

Décision contrôleur (tâche 6, 2026-09-16) : le learner jouet `CounterLearner` du brief est LINÉAIRE et ne peut
pas apprendre la parité/XOR -- il n'acquerrait jamais. Le cas de succès complet utilise donc
`TabularLearner(honest=True)` (vérité-terrain, tools/harness/learners/tabular.py), avec `piece="table"` ;
les ablations de `ToyParity` (tests/sandbox/test_harness_task.py) sont nommées `permute_a` (must_bite) et
`inject_noise` (must_bite=False) -- pas `permute_nothing` (nom du brief d'origine, renommé à la tâche 3).

Revue contrôleur, fix round 1 (2026-09-16) : trois cas ajoutés pour les refus DÉCIDABLES qui ne tombaient
qu'au verdict avant ce fix (ablation inconnue, lrs dupliqués, n_floor > seeds), deux pour les minors (seeds
dupliqués, episodes < 2) ; le seuil de l'horloge factice de `test_abandoned_seed_is_counted_and_yields_
INCONCLUSIVE_N` est corrigé (`< 5` -> `< 0.5`) pour rester calibré après le retrait du gonfleur d'appels de
`_tick` (un seul `guard.tick()` par lot/épisode, plus un par agent) -- c'est le TEST qui porte cette
constante, pas le runner."""
import json
import os
import sys

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


def _rule_with_unknown_ablation():
    r = _rule()
    r["ablations"] = list(r["ablations"]) + [{"name": "bogus_ablation", "site": "input", "must_bite": False}]
    return r


@pytest.fixture
def sealed_bad_ablation(tmp_path):
    preregister("HARNESS-TOY-BAD-ABLATION", _rule_with_unknown_ablation(), _dir=str(tmp_path))
    return str(tmp_path)


def _rule_with_duplicate_lrs():
    r = _rule()
    r["sweep"] = [{"lr": 1.0}, {"lr": 1.0}]
    return r


@pytest.fixture
def sealed_dup_lrs(tmp_path):
    preregister("HARNESS-TOY-DUP-LRS", _rule_with_duplicate_lrs(), _dir=str(tmp_path))
    return str(tmp_path)


def _rule_with_n_floor_too_high():
    r = _rule()
    r["n_floor"] = 99
    return r


@pytest.fixture
def sealed_n_floor_too_high(tmp_path):
    preregister("HARNESS-TOY-NFLOOR", _rule_with_n_floor_too_high(), _dir=str(tmp_path))
    return str(tmp_path)


class _Sentinel(CounterLearner):
    def build(self, *a, **k):
        raise AssertionError("CORPS ATTEINT : build appelé avant les gardes")


def test_task_contract_refuses_before_any_build(sealed, tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "res"))
    # Les DEUX ablations restent NOMMÉES comme la règle scellée (sinon le nouveau garde-fou "ablation de
    # la règle absente de la tâche", ajouté au fix round 1, refuserait AVANT même d'atteindre le contrat de
    # tâche visé par CE test) -- seul `must_bite` de `inject_noise` passe à True, pour que la tâche ne
    # déclare plus AUCUNE ablation must_bite=False (condition (a) de assert_task_contract).
    task = ToyParity()
    task.demand = DemandDeclaration("parity", (
        Ablation("permute_a", "input", True, apply=task._permute_a, bayes_floor=0.5),
        Ablation("inject_noise", "input", True, apply=task._inject_noise)))
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
    with pytest.raises(KeyError, match="nope"):
        run_harness_cell(ToyParity(), _Sentinel(), "HARNESS-TOY-WHOLE", seeds=SEEDS, episodes=5,
                         out_name="toy_rp_bad", prereg_dir=sealed_whole, rule_path=["cellules", "nope"])
    out = run_harness_cell(ToyParity(), TabularLearner(honest=True), "HARNESS-TOY-WHOLE", seeds=SEEDS, episodes=40,
                           out_name="toy_rp", prereg_dir=sealed_whole, rule_path=["cellules", "X"],
                           n_agents=8, eval_batches=10)
    assert out["verdict"]["verdict"] == "DEMANDED_ACQUIRED_NECESSARY"
    assert out["path"] and json.load(open(out["path"], encoding="utf-8"))["data"]["preregistration"]["rule_path"] \
        == ["cellules", "X"]


def test_rule_naming_an_unknown_ablation_refuses_before_any_build(sealed_bad_ablation, tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "res"))
    with pytest.raises(KeyError, match="bogus_ablation"):
        run_harness_cell(ToyParity(), _Sentinel(), "HARNESS-TOY-BAD-ABLATION", seeds=SEEDS, episodes=5,
                         out_name="toy_bad_abl", prereg_dir=sealed_bad_ablation)


def test_rule_with_duplicate_lrs_refuses_before_any_build(sealed_dup_lrs, tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "res"))
    with pytest.raises(ValueError, match="deux pas"):
        run_harness_cell(ToyParity(), _Sentinel(), "HARNESS-TOY-DUP-LRS", seeds=SEEDS, episodes=5,
                         out_name="toy_dup_lrs", prereg_dir=sealed_dup_lrs)


def test_rule_with_n_floor_above_seeds_refuses_before_any_build(sealed_n_floor_too_high, tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "res"))
    with pytest.raises(ValueError, match="n_floor"):
        run_harness_cell(ToyParity(), _Sentinel(), "HARNESS-TOY-NFLOOR", seeds=SEEDS, episodes=5,
                         out_name="toy_nfloor", prereg_dir=sealed_n_floor_too_high)


def test_duplicate_seeds_refuse_before_any_build(sealed, tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "res"))
    with pytest.raises(ValueError, match="doublons"):
        run_harness_cell(ToyParity(), _Sentinel(), "HARNESS-TOY", seeds=SEEDS + [SEEDS[0]], episodes=5,
                         out_name="toy_dup_seeds", prereg_dir=sealed)


def test_episodes_below_two_refuses_before_any_build(sealed, tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "res"))
    with pytest.raises(ValueError, match="episodes"):
        run_harness_cell(ToyParity(), _Sentinel(), "HARNESS-TOY", seeds=SEEDS, episodes=1,
                         out_name="toy_ep1", prereg_dir=sealed)


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
    # décision 3 (revue) : le coût de la mesure NON fournie doit être publié comme MESURÉ, jamais comme donné.
    assert saved["data"]["cost"]["unit_s_given"] is None and saved["data"]["cost"]["unit_s_measured"] > 0.0
    assert saved["data"]["design"]["cost_estimate"] == saved["data"]["cost"]["projected_s"]


def test_abandoned_seed_is_counted_and_yields_INCONCLUSIVE_N(sealed, tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "res"))
    t = {"now": 0.0}

    def clock():
        # seuil recalibré (revue, fix round 1) : `_tick` ne tique plus qu'UNE fois par lot/épisode (plus
        # de gonfleur par agent) -- à ~1160 appels sur cette cellule jouet, un seuil `< 5` (5000 appels
        # nécessaires) ne serait JAMAIS franchi. `< 0.5` (500 appels) franchit vers le milieu du run.
        t["now"] += 0.0 if t["now"] < 0.5 else 1000.0    # les premiers appels sont gratuits, puis le temps saute
        t["now"] += 0.001
        return t["now"]

    out = run_harness_cell(ToyParity(), CounterLearner(), "HARNESS-TOY", seeds=SEEDS, episodes=5, out_name="toy",
                           prereg_dir=sealed, n_agents=8, eval_batches=5, budget_s=3600.0, unit_s=0.001, clock=clock)
    assert out["verdict"]["verdict"] == "INCONCLUSIVE_N"
    assert any(out["db"]["abandoned"][arm] for arm in out["db"]["abandoned"])
    # gel (revue, fix round 1) : un (bras, seed) ABANDONNÉ n'a jamais de valeur "last" -- l'abandon est un
    # VRAI saut, jamais une fabrication silencieuse à côté d'une entrée déjà écrite.
    for arm, abandoned_seeds in out["db"]["abandoned"].items():
        for s in abandoned_seeds:
            assert str(s) not in out["db"]["arms"][arm]["last"]
