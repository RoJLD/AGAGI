import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from src.seed_ai.harness import seed_at


def _mk_env(prey_speed_scale=None, trace_forage=False):
    cfg = WorldConfig()
    cfg.base_metabolism = 0.25
    cfg.trace_forage = trace_forage
    if prey_speed_scale is not None:
        cfg.prey_speed_scale = prey_speed_scale
    env = Biosphere3D(cfg)
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    env.use_ref_head = False
    env.decode_act = False
    for _ in range(6):
        env.add_agent(MambaAgent(), energy=80.0)
    env.current_era = 1
    return env


def _prey_positions(env):
    return sorted((p["x"], p["y"], p["type"]) for p in env.preys)


def test_config_default_prey_speed_scale_one():
    assert WorldConfig().prey_speed_scale == 1.0


def test_scale_one_is_inert_vs_field_absent():
    # Ajout du champ a 1.0 == comportement sans le champ (getattr defaut 1.0) -> non-regression.
    seed_at(424242, 0)
    env_a = _mk_env(prey_speed_scale=1.0)
    seed_at(424242, 0)
    env_b = _mk_env(prey_speed_scale=None)
    delattr(env_b.config, "prey_speed_scale")   # simule l'absence du champ
    for _ in range(5):
        env_a.step()
        env_b.step()
    assert _prey_positions(env_a) == _prey_positions(env_b)


def test_scale_zero_freezes_preys():
    env = _mk_env(prey_speed_scale=0.0)
    env.config.target_prey_count = 0    # desactive le respawn (sinon positions aleatoires != deplacement)
    before = _prey_positions(env)
    for _ in range(5):
        env.step()
    after = _prey_positions(env)
    # aucune proie n'a BOUGE : sans respawn, les seules positions presentes en 'after' sont un
    # sous-ensemble de 'before' (un kill retire une position ; un deplacement creerait une position
    # nouvelle absente de 'before' -> ferait echouer l'assertion).
    assert after == [pos for pos in before if pos in after]


def test_species_counter_records_kill():
    # Force un kill regulier : un agent et un Lapin (hp=1) sur la meme case, l'attaque auto le tue.
    env = _mk_env(prey_speed_scale=0.0, trace_forage=True)
    env.preys.clear()
    ag = env.agents[0]
    env.preys.append({"x": ag["x"], "y": ag["y"], "type": "Lapin", "stunned": 0, "hp": 1.0})
    env.step()
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    species = {}
    for a in pool:
        for k, v in a.get("_forage_species", {}).items():
            species[k] = species.get(k, 0) + v
    assert species.get("Lapin", 0) >= 1


def test_species_counter_inert_when_trace_off():
    env = _mk_env(prey_speed_scale=0.0, trace_forage=False)
    env.preys.clear()
    ag = env.agents[0]
    env.preys.append({"x": ag["x"], "y": ag["y"], "type": "Lapin", "stunned": 0, "hp": 1.0})
    env.step()
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    assert all("_forage_species" not in a for a in pool)
