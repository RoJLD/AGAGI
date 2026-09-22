"""P2.56 (b), seconde fournée — trois orchestrateurs MUETS reçoivent une injection à dose connue, 0 monde :

* `tools/s2_regime_diagnostic.py::run_diagnostic` — grille 2 régimes × 3 agents : le maillon `run_condition` est
  remplacé par une sentinelle qui JOURNALISE ce qu'on lui passe (politique, génome, config, K, seed) ; la couche
  jugée est l'orchestration (grille complète, config du régime, génome frais ou champion, arguments transmis).
* `tools/substrate_attractor_probe.py::probe_substrate_attractor` — `_drive` rend des trajectoires CONNUES
  (constantes = convergent ; marche aléatoire = n'converge pas ; off et action bit-identiques), l'instrument
  `measure_convergence` reste RÉEL (déjà calibré) : P1/P2/P3 doivent tomber sur les valeurs attendues.
* `tools/vertical_world_probe.py::run_probe` — `measure_arm` rend des survies et un usage de Z connus : médianes,
  `survival_ratio` et le verdict PUR `classify_vertical_signal` (Z_UTILISE / Z_INERTE) sont prédits exactement.

EXEMPTION DÉCLARÉE de la garde de bail : aucun test ici ne simule un monde."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

_LEASE_GUARD_EXEMPT = True

import tools.s2_regime_diagnostic as D  # noqa: E402
import tools.substrate_attractor_probe as A  # noqa: E402
import tools.vertical_world_probe as V  # noqa: E402


# ---- run_diagnostic ---------------------------------------------------------------------------------------------
def test_run_diagnostic_builds_the_full_grid_with_the_regime_config_and_the_right_genome_per_agent(monkeypatch):
    import tools.s2_demand as S2
    seen = []

    def _rc(world_cls, cls, genome, seed, num_agents=20, max_ticks=400, n_eras=1, config=None):
        seen.append({"cls": None if cls is None else cls.__name__, "genome": genome, "seed": seed, "K": n_eras,
                     "bm": getattr(config, "base_metabolism", None), "fp": getattr(config, "forage_payoff", None),
                     "agents": num_agents, "ticks": max_ticks})
        return {"era_survival": [10.0] * n_eras, "survival": [10.0] * n_eras}
    monkeypatch.setattr(S2, "run_condition", _rc)            # importé LOCALEMENT par run_diagnostic : lu à l'appel
    monkeypatch.setattr(D, "load_champion_genome", lambda: "CHAMPION")
    cells = D.run_diagnostic(seed=7, K=3, num_agents=5, max_ticks=11)
    assert set(cells) == set(D.REGIMES) and all(set(cells[r]) == set(D.AGENTS) for r in cells)
    assert len(seen) == len(D.REGIMES) * len(D.AGENTS)
    for r, (bm, fp) in D.REGIMES.items():
        for name in D.AGENTS:
            assert cells[r][name]["era_survival"] == [10.0] * 3
    par_regime = {(s["bm"], s["fp"]) for s in seen}
    assert par_regime == set(D.REGIMES.values()), "la config de CHAQUE régime est celle de la grille (E8)"
    champ = [s for s in seen if s["cls"] is None]
    frais = [s for s in seen if s["cls"] is not None]
    assert champ and all(s["genome"] == "CHAMPION" for s in champ), "le bras champion porte le génome du champion"
    assert frais and all(s["genome"] is None for s in frais), "les bras câblés partent d'un génome frais"
    assert {s["cls"] for s in frais} == {"ReflexBatchModel", "RandomActionBatchModel"}
    assert all(s["seed"] == 7 and s["K"] == 3 and s["agents"] == 5 and s["ticks"] == 11 for s in seen)


def test_run_diagnostic_refuses_degenerate_arguments_BEFORE_loading_anything(monkeypatch):
    monkeypatch.setattr(D, "load_champion_genome", lambda: (_ for _ in ()).throw(AssertionError("chargé")))
    with pytest.raises(ValueError):
        D.run_diagnostic(K=0)


# ---- probe_substrate_attractor -----------------------------------------------------------------------------------
def _traj_const(T, dim=3, value=0.5):
    return [np.full(dim, value, dtype=np.float32) for _ in range(T)]


def _traj_walk(T, dim=3, seed=0):
    r = np.random.RandomState(seed)
    h, out = np.zeros(dim, dtype=np.float32), []
    for _ in range(T):
        h = h + r.normal(0.0, 1.0, dim).astype(np.float32)
        out.append(h.copy())
    return out


def test_attractor_probe_reads_known_trajectories_into_P1_P2_P3(monkeypatch):
    n, T = 4, 20

    def _drive(mode, n_, T_, seed, sigma_H, sigma_a, obs_mode):
        assert (n_, T_) == (n, T)
        if mode in ("off", "action"):
            return [_traj_const(T) for _ in range(n_)], [[0] * T_ for _ in range(n_)]
        return [_traj_walk(T, seed=i) for i in range(n_)], [list(range(T_)) for _ in range(n_)]
    monkeypatch.setattr(A, "_drive", _drive)
    out = A.probe_substrate_attractor(n=n, T=T, seed=0)
    assert out["P1_converge"] == {"off": n, "action": n, "H": 0}
    assert out["P2_bit_identical_off_action"] == n and out["div_action"] == 0.0 and out["div_H"] > 1.0
    assert out["P3_action_diversity"] == {"off": 1.0, "action": 1.0, "H": float(T // 2)}
    assert out["n"] == n and out["obs_mode"] == "zero"


def test_attractor_probe_refuses_degenerate_arguments_before_driving_anything(monkeypatch):
    monkeypatch.setattr(A, "_drive", lambda *a, **k: (_ for _ in ()).throw(AssertionError("monde lancé")))
    with pytest.raises(ValueError):
        A.probe_substrate_attractor(n=0, T=10)


# ---- vertical run_probe ------------------------------------------------------------------------------------------
def _fake_measure_arm(z_range_3d, updown_3d, surv_2d=100.0, surv_3d=120.0):
    def measure_arm(genome, use_3d, seed, n_eras=2, n_agents=12, max_ticks=600):
        assert genome == "G"
        return {"survival": surv_3d if use_3d else surv_2d, "z_range": z_range_3d if use_3d else 0.0,
                "updown_frac": updown_3d if use_3d else 0.0, "seed": seed}
    return measure_arm


def test_vertical_run_probe_aggregates_arms_and_classifies_Z_USED_from_a_known_dose(monkeypatch):
    monkeypatch.setattr(V, "measure_arm", _fake_measure_arm(z_range_3d=2.0, updown_3d=0.5))
    out = V.run_probe("G", seeds=[1, 2, 3], n_eras=2, n_agents=4, max_ticks=10)
    assert out["seeds"] == [1, 2, 3] and len(out["arm_2d"]) == 3 and len(out["arm_3d"]) == 3
    assert out["survival_2d"] == 100.0 and out["survival_3d"] == 120.0 and out["survival_ratio"] == pytest.approx(1.2)
    assert out["verdict"] == "Z_UTILISE" and out["z_range_3d"] == 2.0 and out["updown_frac_3d"] == 0.5
    assert out["threshold"] == pytest.approx(0.25 * 1.2)


def test_vertical_run_probe_reads_an_inert_Z_and_refuses_an_empty_plan(monkeypatch):
    monkeypatch.setattr(V, "measure_arm", _fake_measure_arm(z_range_3d=0.1, updown_3d=0.5))
    assert V.run_probe("G", seeds=[1, 2, 3], n_eras=2, n_agents=4, max_ticks=10)["verdict"] == "Z_INERTE"
    monkeypatch.setattr(V, "measure_arm", _fake_measure_arm(z_range_3d=2.0, updown_3d=0.2))   # z bouge, pas les actions
    assert V.run_probe("G", seeds=[1, 2, 3], n_eras=2, n_agents=4, max_ticks=10)["verdict"] == "Z_INERTE"
    monkeypatch.setattr(V, "measure_arm", lambda *a, **k: (_ for _ in ()).throw(AssertionError("monde lancé")))
    with pytest.raises(ValueError):
        V.run_probe("G", seeds=[], n_eras=2, n_agents=4, max_ticks=10)
