# tests/sandbox/test_baseline_models.py
import numpy as np
from src.agents.mamba_agent import MambaAgent
from src.agents.baseline_models import RandomActionBatchModel


def _agents(n=4):
    out = []
    for _ in range(n):
        a = MambaAgent()
        a.surprise = 9.9            # valeur "sale" à écraser
        a.surprise_momentum = 9.9
        out.append(a)
    return out


def test_random_action_forward_shape_matches_outputs():
    agents = _agents()
    bm = RandomActionBatchModel(agents)
    O = max(a.genome.num_outputs for a in agents)
    logits, spent = bm.forward(np.zeros((len(agents), agents[0].genome.num_inputs), dtype=np.float32))
    assert logits.shape == (len(agents), O)
    assert spent.shape == (len(agents),)
    assert np.all(spent == 0.0)         # pas de rêve


def test_random_action_writes_zero_surprise():
    agents = _agents()
    bm = RandomActionBatchModel(agents)
    bm.forward(np.zeros((len(agents), agents[0].genome.num_inputs), dtype=np.float32))
    assert all(a.surprise == 0.0 and a.surprise_momentum == 0.0 for a in agents)


def test_random_action_compute_policy_gradient_is_noop():
    agents = _agents()
    bm = RandomActionBatchModel(agents)
    bm.compute_policy_gradient(np.zeros(len(agents)), None)     # ne lève pas


def test_random_action_is_seeded():
    agents = _agents()
    obs = np.zeros((len(agents), agents[0].genome.num_inputs), dtype=np.float32)
    np.random.seed(123); a1, _ = RandomActionBatchModel(agents).forward(obs)
    np.random.seed(123); a2, _ = RandomActionBatchModel(agents).forward(obs)
    assert np.allclose(a1, a2)          # tire du flux global seedé (appariement)


from src.agents.baseline_models import ReflexBatchModel
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D


def test_reflex_logits_point_toward_prey_direction():
    # obs col 0..3 = dn,ds,de,dw. Proie à l'EST -> de (col 2) dominant -> argmax(logits[:8]) == 2.
    agents = [MambaAgent() for _ in range(1)]
    bm = ReflexBatchModel(agents)
    obs = np.zeros((1, agents[0].genome.num_inputs), dtype=np.float32)
    obs[0, 2] = 0.9          # de : proie à l'est
    logits, _ = bm.forward(obs)
    assert int(np.argmax(logits[0, :8])) == 2     # action East (world_1:1248)


def test_reflex_always_attempts_grab():
    agents = [MambaAgent() for _ in range(1)]
    bm = ReflexBatchModel(agents)
    logits, _ = bm.forward(np.zeros((1, agents[0].genome.num_inputs), dtype=np.float32))
    assert logits[0, 24] > 0.0                    # do_grab (world_1:1205)


def test_reflex_pursues_in_real_world():
    # intégration : un agent réflexe finit par bouger (x ou y change) en présence de proies.
    np.random.seed(0)
    env = Biosphere3D(WorldConfig())
    env.benchmark_mode = True
    env.night_enabled = False
    env.current_era = 10_000
    env.batch_model_cls = ReflexBatchModel
    a = MambaAgent()
    env.add_agent(a, energy=80.0)
    start = (env.agents[0]["x"], env.agents[0]["y"])
    moved = False
    for _ in range(20):
        env.step()
        if not env.agents:
            break
        if (env.agents[0]["x"], env.agents[0]["y"]) != start:
            moved = True
            break
    assert moved
