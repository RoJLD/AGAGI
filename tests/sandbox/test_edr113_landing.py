import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from tools.lewis_survival_sweep import _cfg, _landing_arm


def _cfg_land(scaffold_land):
    cfg = WorldConfig()
    cfg.base_metabolism = 0.0
    cfg.forage_payoff = 3.0
    cfg.prey_speed_scale = 0.0      # proies figees (deterministe, EDR106)
    cfg.trace_forage = True         # pour lire _forage_contacts
    cfg.scaffold_land = float(scaffold_land)
    return cfg


def test_config_has_scaffold_land_default_zero():
    assert WorldConfig().scaffold_land == 0.0


def test_world_reads_scaffold_land():
    assert Biosphere3D(_cfg_land(0.0)).scaffold_land == 0.0
    assert Biosphere3D(_cfg_land(10.0)).scaffold_land == 10.0


def _run_with_prey_on_agent(scaffold_land, steps=40, seed=4242):
    """Place UN agent et UNE proie figee a la meme cellule ; renvoie (energie_totale, contacts)."""
    from src.seed_ai.harness import seed_at
    from src.agents.mamba_agent import MambaAgent
    seed_at(seed, 0)
    env = Biosphere3D(_cfg_land(scaffold_land))
    env.preys = [p for p in env.preys if p["type"] not in ("Mammouth", "Ours", "Leurre")]  # Lewis vide d'apex
    env.current_era = 1
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop(); env.memory_retriever.clear()
    a = MambaAgent()
    env.add_agent(a, energy=80.0)
    ag = env.agents[0]
    # forcer une proie petite (damage=0) sur la cellule de l'agent
    env.preys.append({"x": ag["x"], "y": ag["y"], "z": 0, "type": "Lapin", "hp": 1})
    contacts = 0
    for _ in range(steps):
        if not env.agents:
            break
        env.step()
        pool = list(env.agents) + list(getattr(env, "dead_agents", []))
        contacts = max(contacts, max((p.get("_forage_contacts", 0) for p in pool), default=0))
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    total_energy = sum(p["energy"] for p in pool)
    return total_energy, contacts


def test_landing_reward_is_paid_monotone():
    # scaffold_land n'AJOUTE que de l'energie sur atterrissage -> env riche >= env pauvre,
    # strictement > si au moins un contact a eu lieu. Cible le PAS FINAL.
    e0, c0 = _run_with_prey_on_agent(0.0)
    eL, cL = _run_with_prey_on_agent(10.0)
    assert cL >= 1, "le scenario doit produire au moins un atterrissage (contact)"
    assert eL > e0, f"scaffold_land=10 doit enrichir vs 0 (eL={eL} e0={e0})"


def test_non_regression_byte_identical_at_zero():
    # Deux runs scaffold_land=0 -> energie totale identique (le defaut ne change rien).
    e0a, _ = _run_with_prey_on_agent(0.0, seed=777)
    e0b, _ = _run_with_prey_on_agent(0.0, seed=777)
    assert e0a == e0b


def test_cfg_scaffold_land_param():
    assert _cfg(3).scaffold_land == 0.0
    assert _cfg(3, scaffold_land=5.0).scaffold_land == 5.0


def test_landing_arm_smoke_returns_expected_keys():
    cfg = _cfg(3, base_metabolism=0.0, trace_forage=True, scaffold_land=5.0)
    arm = _landing_arm(cfg, generations=2, num_agents=6, max_ticks=40, base_seed=99113)
    assert arm["scaffold_land"] == 5.0
    assert len(arm["traj"]) == 2
    assert 0.0 <= arm["plateau"] <= 1.0
    assert 0.0 <= arm["gen0"] <= 1.0
    assert len(arm["stats"]) == 2


from tools.lewis_survival_sweep import _verdict_landing, main_landing_nav


def _arm(land, plateau):
    return {"scaffold_land": land, "plateau": plateau, "gen0": plateau,
            "first": plateau, "traj": [plateau], "stats": []}


def test_verdict_leve_on_rising_plateaus():
    arms = [_arm(0, 0.36), _arm(2, 0.42), _arm(5, 0.50), _arm(10, 0.58)]
    assert _verdict_landing(arms) == "AFFORDANCE LEVE"


def test_verdict_inerte_on_flat_plateaus():
    arms = [_arm(0, 0.36), _arm(2, 0.35), _arm(5, 0.37), _arm(10, 0.36)]
    assert _verdict_landing(arms) == "AFFORDANCE INERTE"


def test_verdict_ambigue_on_descending_plateaus():
    arms = [_arm(0, 0.55), _arm(2, 0.40), _arm(5, 0.30), _arm(10, 0.20)]
    assert _verdict_landing(arms) == "AFFORDANCE AMBIGUE"


def test_main_landing_nav_smoke_and_determinism():
    r1 = main_landing_nav(land_levels=(0.0, 5.0), generations=2, num_agents=6,
                          max_ticks=40, seed=88113, _return=True)
    assert r1["verdict"] in ("AFFORDANCE LEVE", "AFFORDANCE INERTE", "AFFORDANCE AMBIGUE")
    assert len(r1["arms"]) == 2
    r2 = main_landing_nav(land_levels=(0.0, 5.0), generations=2, num_agents=6,
                          max_ticks=40, seed=88113, _return=True)
    assert [a["traj"] for a in r1["arms"]] == [a["traj"] for a in r2["arms"]]
