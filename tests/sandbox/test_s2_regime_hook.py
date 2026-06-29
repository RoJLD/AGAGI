import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.environments.config import WorldConfig
from tools.s2_demand import run_condition


class _FakeEnv:
    """Env minimal qui ENREGISTRE le config reçu et ne simule rien (agents vide -> boucle no-op)."""
    last_config = "UNSET"

    def __init__(self, config=None):
        _FakeEnv.last_config = config
        self.agents = []
        self.dead_agents = []
        self.benchmark_mode = False
        self.night_enabled = True
        self.current_era = 0

    def add_agent(self, agent, energy=0.0):
        pass

    def step(self):
        pass


def test_run_condition_default_passes_no_config():
    _FakeEnv.last_config = "UNSET"
    run_condition(_FakeEnv, None, None, seed=1, num_agents=1, max_ticks=1, n_eras=1)
    assert _FakeEnv.last_config is None        # défaut -> world_cls() -> config None


def test_run_condition_forwards_regime_config():
    cfg = WorldConfig(base_metabolism=0.25, forage_payoff=3.0)
    run_condition(_FakeEnv, None, None, seed=1, num_agents=1, max_ticks=1, n_eras=1, config=cfg)
    assert _FakeEnv.last_config is cfg          # config fourni -> world_cls(config)
    assert _FakeEnv.last_config.base_metabolism == 0.25
