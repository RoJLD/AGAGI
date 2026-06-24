"""Cap de capacité de charge des AGENTS (opt-in) — empêche le runaway O(N²) de la reproduction
intra-épisode. Découvert post-EDR090 : sur les longs épisodes, des génomes évolués prolifiques font
exploser la population (HGT + repro sociale ajoutent des agents dans step() sans plafond), et
`_apply_hgt_breeding` est O(N²)/tick → runaway compute+mémoire. `max_population=None` (défaut) =
comportement historique inchangé (rétro-compatible)."""
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent


def _world(max_pop):
    cfg = WorldConfig()
    cfg.max_population = max_pop
    env = Biosphere3D(cfg)
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    env.agents = []                                   # contrôle exact de la population
    for _ in range(5):
        env.add_agent(MambaAgent(), x=1, y=1, energy=50.0)
    return env


def _offspring(n):
    return [(MambaAgent(), 1, 1, 40.0) for _ in range(n)]


def test_offspring_capped_at_max_population():
    env = _world(max_pop=5)
    assert len(env.agents) == 5
    env._add_offspring(_offspring(10))                # demande +10 ; déjà au cap
    assert len(env.agents) == 5                       # aucun ajout au-delà du cap


def test_offspring_partial_fill_to_cap():
    env = _world(max_pop=8)
    env._add_offspring(_offspring(10))                # 5 + 10 demandés, cap 8 -> +3 seulement
    assert len(env.agents) == 8


def test_offspring_uncapped_when_none():
    env = _world(max_pop=None)                         # défaut : pas de cap (rétro-compatible)
    env._add_offspring(_offspring(10))
    assert len(env.agents) == 15                       # tous ajoutés (comportement historique)
