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


def _prey_positions_after(prey_speed_scale, seed, steps):
    seed_at(seed, 0)
    env = _mk_env(prey_speed_scale=prey_speed_scale)
    env.config.target_prey_count = 0    # pas de respawn -> comparaison deterministe propre
    for _ in range(steps):
        env.step()
    return _prey_positions(env)


def test_scale_one_deterministic_and_mobile():
    # Determinisme : meme seed -> memes positions (aucune source de non-determinisme introduite a 1.0).
    a = _prey_positions_after(1.0, 424242, 5)
    b = _prey_positions_after(1.0, 424242, 5)
    assert a == b
    # Mobilite : a scale=1.0 au moins une proie s'est DEPLACEE (position nouvelle absente du depart) ->
    # on n'a pas gele les proies par accident. (Un kill ne fait que retirer une position, jamais en creer.)
    seed_at(424242, 0)
    env = _mk_env(prey_speed_scale=1.0)
    env.config.target_prey_count = 0
    start = _prey_positions(env)
    for _ in range(5):
        env.step()
    moved = _prey_positions(env)
    assert any(pos not in start for pos in moved), "au moins une proie doit s'etre deplacee a scale=1.0"


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


from tools.lewis_survival_sweep import _cfg, _measure_forage


def test_cfg_prey_speed_scale_param():
    cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True, prey_speed_scale=0.0)
    assert cfg.prey_speed_scale == 0.0
    assert cfg.trace_forage is True


def test_measure_forage_has_species_and_reached_raw():
    cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True, prey_speed_scale=0.0)
    agg = _measure_forage(cfg, [106, 107], n_apex=0, max_ticks=20)
    for k in ("cap_lapin", "cap_cerf", "cap_sanglier", "reached_raw"):
        assert k in agg
    assert 0.0 <= agg["p_reach"] <= 1.0
    assert isinstance(agg["reached_raw"], list)
    assert len(agg["reached_raw"]) == agg["n_agents"]
    assert all(v in (0.0, 1.0) for v in agg["reached_raw"])
