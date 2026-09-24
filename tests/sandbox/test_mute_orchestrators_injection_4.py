"""P2.56 (b), dixième fournée — les six déclarations que le cliquet de portée comptait « déclaratives » par un SEUL
appel sous `pytest.raises` (corps jamais atteint ; corrigé le 2026-09-23 dans `check_calibration_reach`) reçoivent un
témoin qui atteint le CORPS, à dose connue, 0 monde réel : les quatre `run_arm` de l'arc crédit (seams
`_bassin_cohort` / `load_bassin`, `phase1_learn_immortal`, `phase2_survive_mortal`, `credit_variant`,
`effective_reward` remplacés par des enregistreurs), `run_curriculum` (quatre maillons remplacés, chemin de sortie en dur
capturé par un `chdir` temporaire) et `run_world_era` (classe de monde factice). Ce qui est jugé : la variante de crédit
PUBLIÉE et transmise à la phase 1 (E8 : ce que le bras dit appliquer est appliqué), l'ordre des maillons (variante
posée AVANT la phase 1 ; échelle effective résolue AVANT le seed), le bras gelé qui n'apprend pas, la cohorte froide
qui ne charge pas le bassin, les copies (la variante publiée n'aliasse pas la table), l'échelle réelle et le tri.

EXEMPTION DÉCLARÉE de la garde de bail : aucun test ici ne simule un monde."""
import contextlib
import json
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

_LEASE_GUARD_EXEMPT = True

import tools.evo_runs.s2_credit_ablation as CA  # noqa: E402
import tools.evo_runs.s2_credit_ablation_2 as CA2  # noqa: E402
import tools.evo_runs.s2_credit_retention as CR  # noqa: E402
import tools.evo_runs.s2_reward_ablation as RA  # noqa: E402
import main_curriculum as MC  # noqa: E402
import multiverse_runner as MV  # noqa: E402
from src.agents.mamba_agent import MambaAgent  # noqa: E402


def _phases(mod, monkeypatch, calls):
    monkeypatch.setattr(mod, "phase1_learn_immortal",
                        lambda agents, seed, ticks, **kw: calls.append(("phase1", len(agents), seed, ticks, kw)) or {"td_updates": 5, "episode_updates": 2})
    monkeypatch.setattr(mod, "phase2_survive_mortal",
                        lambda agents, seed, ticks: calls.append(("phase2", len(agents), seed, ticks)) or {"ages": [3.0, 4.0]})


def test_credit_ablation_run_arm_publishes_the_arm_variant_and_passes_it_to_phase_1(monkeypatch):
    calls = []
    monkeypatch.setattr(CA, "_bassin_cohort", lambda seed, n: calls.append(("bassin", seed, n)) or ["ag"] * n)
    _phases(CA, monkeypatch, calls)
    out = CA.run_arm(7, "b_zero", num_agents=3, ticks_learn=10, ticks_test=4)
    assert out["credit"] == {"reward_scale": 0.0, "td_enabled": True, "lr": None} and out["lr"] is None
    assert calls == [("bassin", 7, 3), ("phase1", 3, 7, 10, {"lr": None, "reward_scale": 0.0, "td_enabled": True}), ("phase2", 3, 7, 4)]
    assert out["learning"] == {"td_updates": 5, "episode_updates": 2} and out["survival"] == {"ages": [3.0, 4.0]} and out["elapsed_s"] >= 0.0
    out["credit"]["reward_scale"] = 99.0
    assert CA.ARM_CREDIT["b_zero"]["reward_scale"] == 0.0, "la variante publiee est une COPIE, jamais la table"
    calls.clear()
    out = CA.run_arm(7, "a_frozen", num_agents=3, ticks_learn=10, ticks_test=4)
    assert out["learning"] is None and out["credit"] is None and [c[0] for c in calls] == ["bassin", "phase2"], "le bras gele n'apprend pas"
    with pytest.raises(ValueError):
        CA.run_arm(7, "inconnu", num_agents=3, ticks_learn=10, ticks_test=4)


def test_credit_ablation_2_run_arm_enters_the_credit_variant_BEFORE_phase_1(monkeypatch):
    calls = []
    monkeypatch.setattr(CA2, "_bassin_cohort", lambda seed, n: ["ag"] * n)
    _phases(CA2, monkeypatch, calls)

    @contextlib.contextmanager
    def _variant(episode_enabled=True, reward_const=None):
        calls.append(("variant-in", episode_enabled, reward_const))
        yield
        calls.append(("variant-out",))
    monkeypatch.setattr(CA2, "credit_variant", _variant)
    out = CA2.run_arm(1, "b_const", num_agents=2, ticks_learn=6, ticks_test=3)
    assert [c[0] for c in calls] == ["variant-in", "phase1", "variant-out", "phase2"], "la variante enveloppe la phase 1 seule"
    assert calls[0] == ("variant-in", True, 1.0) and out["credit"]["reward_const"] == 1.0
    calls.clear()
    CA2.run_arm(1, "b_tdonly", num_agents=2, ticks_learn=6, ticks_test=3)
    assert calls[0] == ("variant-in", False, None)
    calls.clear()
    out = CA2.run_arm(1, "a_frozen", num_agents=2, ticks_learn=6, ticks_test=3)
    assert out["learning"] is None and [c[0] for c in calls] == ["phase2"], "gele : ni variante ni phase 1"
    with pytest.raises(ValueError):
        CA2.run_arm(1, "b_const", num_agents=0)


def test_credit_retention_run_arm_builds_a_cold_cohort_without_the_bassin_and_passes_lr(monkeypatch):
    calls = []
    genome = MambaAgent().genome
    monkeypatch.setattr(CR, "load_bassin", lambda: calls.append(("bassin",)) or genome)
    monkeypatch.setattr(CR, "phase1_learn_immortal",
                        lambda agents, seed, ticks, lr=None: calls.append(("phase1", len(agents), seed, ticks, lr)) or {"td_updates": 1})
    monkeypatch.setattr(CR, "phase2_survive_mortal", lambda agents, seed, ticks: calls.append(("phase2", len(agents))) or {"ages": [2.0]})
    out = CR.run_arm(3, "c_cold_credit", num_agents=2, ticks_learn=5, ticks_test=2, lr=0.01)
    assert calls == [("phase1", 2, 3, 5, 0.01), ("phase2", 2)] and out["lr"] == 0.01, "cohorte FROIDE : le bassin n'est jamais charge"
    calls.clear()
    out = CR.run_arm(3, "b_warm_credit", num_agents=2, ticks_learn=5, ticks_test=2)
    assert calls == [("bassin",), ("phase1", 2, 3, 5, None), ("phase2", 2)], "cohorte CHAUDE : un seul chargement du bassin, clone x2"
    calls.clear()
    out = CR.run_arm(3, "a_warm_frozen", num_agents=2, ticks_learn=5, ticks_test=2)
    assert out["learning"] is None and [c[0] for c in calls] == ["bassin", "phase2"]
    with pytest.raises(ValueError):
        CR.run_arm(3, "b_warm_credit", ticks_test=0)


def test_reward_ablation_run_arm_resolves_the_effective_reward_BEFORE_the_seed_and_publishes_both(monkeypatch):
    calls = []
    monkeypatch.setattr(RA, "effective_reward", lambda arm: calls.append(("reward", arm)) or {"curiosity_scale": 0.7, "novelty_scale": 0.3})
    monkeypatch.setattr(RA, "_bassin_cohort", lambda seed, n: calls.append(("bassin", seed, n)) or ["ag"] * n)
    _phases(RA, monkeypatch, calls)
    out = RA.run_arm(5, "b_energy", num_agents=2, ticks_learn=8, ticks_test=3)
    assert [c[0] for c in calls] == ["reward", "bassin", "phase1", "phase2"], "l'echelle effective (construit un monde) est resolue AVANT le seed"
    assert calls[2] == ("phase1", 2, 5, 8, {"curiosity_scale": 0.0, "novelty_scale": 0.0}), "b_energy : les deux echelles a ZERO transmises"
    assert out["reward"] == {"curiosity_scale": 0.7, "novelty_scale": 0.3} and out["reward_declared"] == [0.0, 0.0] and out["lr"] is None
    calls.clear()
    out = RA.run_arm(5, "a_frozen", num_agents=2, ticks_learn=8, ticks_test=3)
    assert out["reward"] is None and out["reward_declared"] is None and out["learning"] is None
    assert [c[0] for c in calls] == ["bassin", "phase2"], "gele : aucune echelle resolue, aucune phase 1"
    with pytest.raises(ValueError):
        RA.run_arm(5, "b_full", ticks_learn=0)


def test_run_curriculum_orchestrates_stages_runner_and_transcript_file_under_cwd(monkeypatch, tmp_path):
    calls = {}
    monkeypatch.chdir(tmp_path)                                  # results/curriculum_transcript.json est EN DUR
    monkeypatch.setattr(MC, "async_logger", SimpleNamespace(start=lambda: calls.__setitem__("start", calls.get("start", 0) + 1),
                                                            stop=lambda: calls.__setitem__("stop", calls.get("stop", 0) + 1)))
    monkeypatch.setattr(MC, "_acquire_shared_db", lambda: "db")
    monkeypatch.setattr(MC, "make_run_era_fn", lambda db, cfg, **kw: calls.__setitem__("era", (db, type(cfg).__name__, kw)) or "fn")
    monkeypatch.setattr(MC, "WorldStage", lambda w: ("stage", w))
    transcript = [{"world": "a", "champion_promoted": "cA"}, {"world": "b", "champion_promoted": "cB"}]

    class _Runner:
        def __init__(self, stages, run_era_fn, grad_cfg=None, keep_memory=False):
            calls["runner"] = (stages, run_era_fn, grad_cfg, keep_memory)

        def run(self):
            return transcript
    monkeypatch.setattr(MC, "CurriculumRunner", _Runner)
    monkeypatch.setenv("KEEP_MEMORY", "1")
    out = MC.run_curriculum(["a", "b"], num_agents=5, max_ticks=7)
    assert out == transcript and json.load(open(tmp_path / "results" / "curriculum_transcript.json", encoding="utf-8")) == transcript
    assert calls["runner"] == ([("stage", "a"), ("stage", "b")], "fn", None, True), "etages dans l'ordre de l'echelle ; keep_memory lu dans l'environnement quand None"
    assert calls["era"] == ("db", "WorldConfig", {"num_agents": 5, "max_ticks": 7}) and (calls["start"], calls["stop"]) == (1, 1)
    MC.run_curriculum(None, keep_memory=False, num_agents=5, max_ticks=7, manage_logger=False)
    assert calls["runner"][0] == [("stage", w) for w in MC.DEFAULT_LADDER] and calls["runner"][3] is False
    assert (calls["start"], calls["stop"]) == (1, 1), "manage_logger False : le logger n'est ni demarre ni arrete"
    monkeypatch.setattr(MC, "_acquire_shared_db", lambda: None)
    assert MC.run_curriculum(["a"], num_agents=5, max_ticks=7) == [] and calls["stop"] == 2, "db absente : liste VIDE publiee (porte 14 legataire, documentee) et logger arrete"
    with pytest.raises(ValueError):
        MC.run_curriculum([], num_agents=5, max_ticks=7)
    with pytest.raises(ValueError):
        MC.run_curriculum(["a"], num_agents=0)


def test_run_world_era_seeds_the_world_with_every_genome_and_returns_results_sorted_by_score(monkeypatch):
    made = []

    class _W:
        def __init__(self, size=10):
            self.size, self.agents, self.ticks = size, [], None
            made.append(self)

        def add_agent(self, agent, energy=80.0):
            self.agents.append((agent, energy))

        def run_era(self, num_ticks):
            self.ticks = num_ticks
            scores = [1.0, 3.0, 2.0]
            return [{"score": scores[i], "model": ag, "age": 10 + i, "preys": i, "energy": e} for i, (ag, e) in enumerate(self.agents)]
    monkeypatch.setattr(MV, "Biosphere3D", _W)
    genomes = [MambaAgent().genome for _ in range(3)]
    world_id, results = MV.run_world_era((4, genomes, 25))
    w = made[-1]
    assert world_id == 4 and w.size == 10 and w.ticks == 25 and [e for _, e in w.agents] == [100.0] * 3
    assert [r["score"] for r in results] == [3.0, 2.0, 1.0] and [r["age"] for r in results] == [11, 12, 10], "tri par score decroissant"
    assert all(set(r) == {"score", "genome", "age", "preys", "energy"} for r in results)
    assert all(np.array_equal(r["genome"].W, genomes[r["preys"]].W) for r in results), "genome transfere par COPIE profonde, contenu identique"
    assert all(r["genome"] is not w.agents[r["preys"]][0].genome for r in results)
    with pytest.raises(ValueError):
        MV.run_world_era((4, [], 25))
    with pytest.raises(ValueError):
        MV.run_world_era((4, genomes, 0))
