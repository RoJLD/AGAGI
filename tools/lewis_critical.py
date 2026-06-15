"""tools/lewis_critical.py — EDR 088 : le CONTENU paye-t-il quand la distinction devient décisive ?

Sweep dose-réponse de la fraction de Leurres-pièges (le levier explicite d'EDR 087). Réutilise les
briques feuilles de relang_sweet/referential_head MAIS écrira son propre moteur 3-bras (Task 5) pour
NE PAS altérer l'artefact 087. Pré-enregistrement :
docs/superpowers/specs/2026-06-15-EDR088-Lewis-Critical-Content-design.md
"""
import numpy as np

from src.environments.config import WorldConfig, PreyConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.persistence import calculate_life_score
from src.seed_ai.referential_head import new_head, train_population
from src.seed_ai.harness import Harness, seed_at
from src.seed_ai import exp_stats as st
from tools.evolve_competence import _reproduce
from tools.robust_eval import _load_champions

METAB, PAYOFF = 0.25, 3.0          # sweet spot (EDR 085)
LEURRE_FRACS = (0.33, 0.50, 0.67, 0.83)
N_APEX = 12


def _sweet_cfg():
    cfg = WorldConfig()
    cfg.base_metabolism = METAB
    cfg.forage_payoff = PAYOFF
    return cfg


def _setup_critical(env, leurre_frac, n_apex=N_APEX):
    """Monde de Lewis à criticalité réglable : n_apex apex au total, dont round(leurre_frac*n_apex)
    Leurres-pièges ; le reste réparti Mammouth/Ours (positifs). Nuit OFF (correctif audit 086)."""
    env.config.active_exp_variable = "LANGUAGE"
    env.hear_radius = 3
    env.night_enabled = False
    env.config.preys["Leurre"] = PreyConfig(hp=100.0, damage=50.0, moves_per_tick=0.2)
    env.config.preys["Ours"] = PreyConfig(hp=60.0, damage=30.0, moves_per_tick=0.3)
    # Purger les apex spawned by __init__ pour avoir un contrôle exact du ratio
    env.preys = [p for p in env.preys if p.get("type") not in ("Mammouth", "Ours", "Leurre")]
    n_leurre = int(round(leurre_frac * n_apex))
    n_pos = n_apex - n_leurre
    positifs = [("Mammouth" if i % 2 == 0 else "Ours") for i in range(n_pos)]  # alterne les 2 food
    for ref in positifs:
        env._spawn_prey_instance(ref)
    for _ in range(n_leurre):
        env._spawn_prey_instance("Leurre")
