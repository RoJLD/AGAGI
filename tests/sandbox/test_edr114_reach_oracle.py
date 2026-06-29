from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.seed_ai.harness import seed_at
from src.agents.mamba_agent import MambaAgent
from tools.lewis_survival_sweep import _cfg, _verdict_reach, main_reach_oracle


def _cfg_oracle(reach_oracle=False, prey_speed_scale=0.0):
    cfg = WorldConfig()
    cfg.size = 20                  # grille suffisamment grande pour les tests directionnels (a=10)
    cfg.base_metabolism = 0.0
    cfg.forage_payoff = 3.0
    cfg.prey_speed_scale = prey_speed_scale
    cfg.trace_forage = True
    cfg.reach_oracle = reach_oracle
    return cfg


def test_config_has_reach_oracle_default_false():
    assert WorldConfig().reach_oracle is False


def test_world_reads_reach_oracle():
    assert Biosphere3D(_cfg_oracle(reach_oracle=False)).reach_oracle is False
    assert Biosphere3D(_cfg_oracle(reach_oracle=True)).reach_oracle is True


def _oracle_action_with_prey_at(env, ax, ay, px, py):
    env.geometry[:] = 0
    env.preys = [{"x": px, "y": py, "z": 0, "type": "Lapin", "hp": 1}]
    return env._reach_oracle_action({"x": ax, "y": ay, "z": 0})


def test_reach_oracle_action_direction_and_sidestep():
    env = Biosphere3D(_cfg_oracle(reach_oracle=True))
    a = 10
    # (a) directions pures (grille libre)
    assert _oracle_action_with_prey_at(env, a, a, a + 3, a) == 2      # proie EST
    assert _oracle_action_with_prey_at(env, a, a, a - 3, a) == 3      # proie OUEST
    assert _oracle_action_with_prey_at(env, a, a, a, a + 3) == 1      # proie SUD
    assert _oracle_action_with_prey_at(env, a, a, a, a - 3) == 0      # proie NORD
    assert _oracle_action_with_prey_at(env, a, a, a, a) == 6          # meme cellule
    # (b) evitement : proie au NORD-EST (prefere EST=2), mais EST bloque -> axe secondaire NORD=0
    env.geometry[:] = 0
    env.geometry[0, a, a + 1] = 1                                     # bloque la cellule EST
    env.preys = [{"x": a + 3, "y": a - 1, "z": 0, "type": "Lapin", "hp": 1}]
    assert env._reach_oracle_action({"x": a, "y": a, "z": 0}) == 0    # sidestep vers NORD


def _run_min(env, steps):
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop(); env.memory_retriever.clear()
    for _ in range(steps):
        if not env.agents:
            break
        env.step()


def test_non_regression_determinism_at_false():
    # reach_oracle=False -> deux runs memes graines = energie totale identique (defaut inerte).
    def run():
        seed_at(555, 0)
        env = Biosphere3D(_cfg_oracle(reach_oracle=False))
        env.preys = [p for p in env.preys if p["type"] not in ("Mammouth", "Ours", "Leurre")]
        env.current_era = 1
        env.add_agent(MambaAgent(), energy=80.0)
        _run_min(env, 20)
        pool = list(env.agents) + list(getattr(env, "dead_agents", []))
        return sum(p["energy"] for p in pool)
    assert run() == run()


def test_oracle_reaches_frozen_prey():
    # Verification directe que la primitive FONCTIONNE : oracle + proie figee + grille libre ->
    # l'agent atteint la proie (forage_min_dist <= 0) en ~distance Manhattan ticks.
    seed_at(606, 0)
    env = Biosphere3D(_cfg_oracle(reach_oracle=True, prey_speed_scale=0.0))
    env.geometry[:] = 0
    env.preys = []                                  # vider toutes les proies generees
    env.current_era = 1
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop(); env.memory_retriever.clear()
    env.add_agent(MambaAgent(), energy=80.0)
    ag = env.agents[0]
    ax, ay = ag["x"], ag["y"]
    px, py = min(ax + 8, env.size - 1), ay         # proie figee a ~8 cases a l'est, chemin libre
    env.preys = [{"x": px, "y": py, "z": 0, "type": "Lapin", "hp": 1}]
    dist = abs(px - ax) + abs(py - ay)
    for _ in range(dist + 10):
        if not env.agents:
            break
        env.step()
        pool = list(env.agents) + list(getattr(env, "dead_agents", []))
        if any(p.get("_forage_min_dist", 9999) <= 0 for p in pool):
            break
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    assert any(p.get("_forage_min_dist", 9999) <= 0 for p in pool), "l'oracle doit atteindre la proie figee"


def test_cfg_reach_oracle_param():
    assert _cfg(3).reach_oracle is False
    assert _cfg(3, reach_oracle=True).reach_oracle is True


def _agg(oracle, speed, p_reach):
    return (oracle, speed, {"p_reach": p_reach, "p_cap": 1.0, "mean_captures": 0.0,
                            "cap_lapin": 0.0, "cap_cerf": 0.0, "cap_sanglier": 0.0,
                            "mean_min_dist": 0.0, "n_agents": 100, "reached_raw": [1, 0]})


def test_verdict_reach_branches():
    # cellule decisive = (oracle=True, speed=0.0)
    ferme = [_agg(False, 1.0, 0.36), _agg(False, 0.0, 0.21), _agg(True, 1.0, 0.40), _agg(True, 0.0, 0.95)]
    assert _verdict_reach(ferme) == "PRIMITIVE FERME"
    bloc = [_agg(False, 1.0, 0.36), _agg(False, 0.0, 0.21), _agg(True, 1.0, 0.30), _agg(True, 0.0, 0.30)]
    assert _verdict_reach(bloc) == "PRIMITIVE NE FERME PAS"
    part = [_agg(False, 1.0, 0.36), _agg(False, 0.0, 0.21), _agg(True, 1.0, 0.60), _agg(True, 0.0, 0.70)]
    assert _verdict_reach(part) == "PRIMITIVE PARTIELLE"


def test_main_reach_oracle_smoke_and_determinism():
    r1 = main_reach_oracle(speeds=(1.0, 0.0), n_eval=2, R=1, seed=88114, _return=True)
    assert r1["verdict"] in ("PRIMITIVE FERME", "PRIMITIVE NE FERME PAS", "PRIMITIVE PARTIELLE", "INDETERMINE")
    assert len(r1["table"]) == 4
    r2 = main_reach_oracle(speeds=(1.0, 0.0), n_eval=2, R=1, seed=88114, _return=True)
    assert r1["table"] == r2["table"]
