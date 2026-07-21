import os
import numpy as np
import pytest
from tools.cognitive_demand_inworld import CognitiveOracleBatchModel, CognitiveOracleAblated


class _Ag:
    def __init__(self, O=120):
        self.genome = type("G", (), {"num_outputs": O})()
        self.surprise = 0.0; self.surprise_momentum = 0.0


def test_oracle_picks_signal_direction():
    agents = [_Ag(), _Ag()]
    m = CognitiveOracleBatchModel(agents)
    obs = np.zeros((2, 20), dtype=np.float32)
    obs[0, 12] = 1.0;  obs[0, 13] = 1.0     # dir = 3
    obs[1, 12] = -1.0; obs[1, 13] = 1.0     # dir = 1
    logits, _ = m.forward(obs)
    assert int(np.argmax(logits[0, :8])) == 3
    assert int(np.argmax(logits[1, :8])) == 1


def test_oracle_ablated_decorrelates():
    np.random.seed(0)
    agents = [_Ag() for _ in range(4)]
    obs = np.zeros((4, 20), dtype=np.float32)
    combos = [(-1.0, -1.0), (-1.0, 1.0), (1.0, -1.0), (1.0, 1.0)]   # dirs 0,1,2,3 (distincts)
    for i, (a, b) in enumerate(combos):
        obs[i, 12] = a; obs[i, 13] = b
    intact, _ = CognitiveOracleBatchModel(agents).forward(obs)
    ablated, _ = CognitiveOracleAblated(agents).forward(obs)
    intact_dirs = np.argmax(intact[:, :8], 1)
    ablated_dirs = np.argmax(ablated[:, :8], 1)
    # tous distincts intact (0,1,2,3) ; un dérangement (aucun point fixe) change CHAQUE direction
    assert sorted(intact_dirs.tolist()) == [0, 1, 2, 3]
    assert not np.any(intact_dirs == ablated_dirs)   # aucun agent ne garde sa direction


@pytest.mark.skipif(os.environ.get("RUN_SLOW") != "1", reason="run in-world lourd")
def test_cog_demand_map_smoke():
    from tools.cognitive_demand_inworld import run_cog_demand_map
    m = run_cog_demand_map(seed=2026, K=2, num_agents=6, max_ticks=60, base_metabolism=4.0, cog_gain=6.0)
    assert set(m) == {"on", "off"}
    for mode in ("on", "off"):
        # sur-ensemble, pas égalité : `_run_mode` expose désormais `censored`/`why` (garde de
        # dégénérescence, EDR-AUDIT-001). Une égalité stricte casse à chaque champ ajouté — et comme ce
        # test est `skipif RUN_SLOW`, elle aurait cassé EN SILENCE.
        assert {"ratio", "verdict", "n"} <= set(m[mode])
        assert m[mode]["ratio"] > 0.0


# ---------------------------------------------------------------------------------------------------
# Dette P2.8 (ouverte par EDR-AUDIT-001) : `LinearCognitiveOracle` était du CODE MORT — aucun appelant,
# aucun test — alors que S2-011 publiait « oracle linéaire 200 » comme contrôle positif de son finding
# VALIDE. Un contrôle positif jamais exécuté ne prouve rien.
# ---------------------------------------------------------------------------------------------------

def test_linear_oracle_decodes_the_one_bit_signal():
    from tools.cognitive_demand_inworld import LinearCognitiveOracle
    agents = [_Ag(), _Ag()]
    obs = np.zeros((2, 20), dtype=np.float32)
    obs[0, 12] = 1.0                                   # bit_a > 0  -> dir 1
    obs[1, 12] = -1.0                                  # bit_a <= 0 -> dir 0
    logits, _ = LinearCognitiveOracle(agents).forward(obs)
    assert int(np.argmax(logits[0, :8])) == 1
    assert int(np.argmax(logits[1, :8])) == 0


def test_linear_oracle_has_a_live_execution_path():
    """RÉGRESSION ANTI-CODE-MORT. `LinearCognitiveOracle` et `LinearOracleAblated` doivent rester
    ATTEIGNABLES depuis une fonction publique — c'est leur absence d'appelant qui a permis à S2-011 de
    publier un chiffre d'oracle que personne n'avait produit."""
    import inspect
    from tools import cognitive_demand_inworld as C
    src = inspect.getsource(C.run_linear_sanity)
    assert "LinearCognitiveOracle" in src and "LinearOracleAblated" in src


def test_credit_linear_exposes_a_no_credit_arm():
    """RÉGRESSION. S2-011 publiait une ligne « WARM SANS crédit » alors que `use_torch_inworld` était
    codé EN DUR à True : la ligne n'avait aucun chemin d'exécution."""
    import inspect
    from tools.cognitive_demand_inworld import run_credit_linear
    assert "use_credit" in inspect.signature(run_credit_linear).parameters
    assert "use_torch_inworld = bool(use_credit)" in inspect.getsource(run_credit_linear)


@pytest.mark.skipif(os.environ.get("RUN_SLOW") != "1", reason="run in-world lourd")
def test_linear_sanity_smoke():
    from tools.cognitive_demand_inworld import run_linear_sanity
    r = run_linear_sanity(seed=2026, K=2, num_agents=6, max_ticks=60)
    assert {"oracle_median", "floor_median", "ratio", "verdict"} <= set(r)
    assert r["oracle_median"] > r["floor_median"], "l'oracle doit battre son ablation"


@pytest.mark.skipif(os.environ.get("RUN_SLOW") != "1", reason="run in-world lourd")
def test_credit_linear_smoke_both_arms():
    from tools.cognitive_demand_inworld import run_credit_linear
    for use_credit in (True, False):
        r = run_credit_linear(seed=2026, warmstart=False, eras=1, num_agents=6, max_ticks=40,
                              use_credit=use_credit)
        assert len(r["trend"]) == 1 and r["final"] >= 0.0
