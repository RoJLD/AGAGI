"""Tests du banc means→ends BPTT (EDR-146). Pur (pas de biosphère). Skip si torch absent."""
import sys, os, inspect
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pytest
pytest.importorskip("torch")

from tools.torch_bptt_meansends import run_meansends
from src.agents.mamba_agent import MambaAgent
from src.agents.backend_torch import TorchPopulationModel


def test_learn_episode_bptt_exists_and_additive():
    # capacité BPTT ADDITIVE : ne remplace pas forward/learn (banc compositional // intact).
    assert hasattr(TorchPopulationModel, "learn_episode_bptt")
    assert hasattr(TorchPopulationModel, "forward") and hasattr(TorchPopulationModel, "learn")


def test_learn_episode_bptt_runs_and_updates_W():
    import numpy as np
    agents = [MambaAgent() for _ in range(4)]
    pop = TorchPopulationModel(agents, lr=0.05)
    W0 = pop.W.detach().cpu().numpy().copy()
    obs = (np.random.RandomState(0).randn(4, pop.I) * 0.5).astype(np.float32)   # signal non nul
    acts = [[{"move": 1}] * 4, [{"move": 2}] * 4]
    loss = pop.learn_episode_bptt([obs, obs], acts, np.array([1.0, -1.0, 1.0, -1.0], np.float32))
    assert loss is not None
    assert not np.allclose(W0, pop.W.detach().cpu().numpy())   # a bien rétropropagé/updaté


def test_run_meansends_smoke():
    r = run_meansends("bptt", epochs=20, n_agents=16, seed=0)
    assert set(r) >= {"hit_end", "p_x", "binding_gap"}


def test_signature():
    assert "truncate" in inspect.signature(TorchPopulationModel.learn_episode_bptt).parameters
