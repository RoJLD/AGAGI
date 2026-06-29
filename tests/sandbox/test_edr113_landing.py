import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D


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
