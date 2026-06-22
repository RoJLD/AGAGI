"""tools/lethality_curriculum.py — EDR 090 : un curriculum de létalité casse-t-il le chicken-and-egg
d'EDR 089 ? Variable unique = curriculum (rampe leurre_frac 0.17→0.83, porté par la maîtrise via
has_graduated dormant) vs flat (cold start à 0.83), apparié par seed, budget d'ères égal. Pure
survie/évitement (PAS de langage : têtes/decode_act/FIABLE-BRUITÉ → EDR 091).
Pré-enregistrement : docs/superpowers/specs/2026-06-22-EDR090-Lethality-Curriculum-design.md
"""
import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.persistence import calculate_life_score
from src.seed_ai.harness import Harness, seed_at
from src.seed_ai import exp_stats as st
from src.curriculum.runner import GraduationConfig, has_graduated
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from tools.evolve_competence import _reproduce
from tools.robust_eval import _load_champions
from tools.lewis_critical import _setup_critical

METAB, PAYOFF = 0.25, 3.0          # sweet spot survie longue (EDR 085)
PREY_COUNT = 15                    # forage food ; respawn n'ajoute JAMAIS Leurre/Ours -> n'altère pas
                                   # leurre_frac (= défaut WorldConfig ; explicite par robustesse).
LEVELS = (0.17, 0.33, 0.50, 0.67, 0.83)   # rampe de létalité (terminal = niveau décisif d'088)
N_APEX = 12
MAX_TICKS = 300
GATE = 120.0                       # survie médiane terminale minimale (gate de validité, comme 089)


def _grad_cfg():
    """Porte de maîtrise gelée (pré-enreg §5). Réutilise GraduationConfig dormant."""
    return GraduationConfig(window=4, eps_plateau=0.02, c_floor=0.5, patience=2, max_eras=10)


def _lethal_cfg():
    cfg = WorldConfig()
    cfg.base_metabolism = METAB
    cfg.forage_payoff = PAYOFF
    return cfg


def _survival_competence(ticks_list, max_ticks=MAX_TICKS):
    """Compétence ∈[0,1] = survie médiane normalisée. À leurre_frac élevé, survivre EXIGE d'éviter les
    Leurres -> proxy d'évitement consommable par has_graduated (qui attend une compétence bornée)."""
    if len(ticks_list) == 0:
        return 0.0
    return float(np.clip(np.median(ticks_list) / max_ticks, 0.0, 1.0))


def _verdict(sc_med, wilcoxon_p, med, lo):
    """Règle de verdict pré-enregistrée (§4). sc_med = survie médiane curriculum au terminal."""
    if sc_med <= GATE:
        return "NEGATIF PROFOND"
    if wilcoxon_p < 0.05 and med > 0 and lo > 0:
        return "CASSE LE BOOTSTRAP"
    return "PAS LE GOULOT"
