# tools/lewis_survival_sweep.py
"""tools/lewis_survival_sweep.py — EDR 093 : un premier barreau survivable en Lewis existe-t-il ?
Balaye forage_payoff (revenu/kill) et mesure la survie mediane des champions stoneage en Lewis a
letalite 0 (isole l'energie). PAS d'evolution, PAS de langage. Fonde sur le diagnostic post-090 :
mort par FAMINE (actions -10 x densite apex >> forage), pas letalite.
Pre-enregistrement : docs/superpowers/specs/2026-06-24-EDR093-Lewis-Survival-Sweep-design.md
"""
import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.harness import Harness, seed_at
from src.seed_ai import exp_stats as st
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from tools.evolve_competence import _reproduce
from tools.robust_eval import _load_champions
from tools.lewis_critical import _setup_critical
from tools.lethality_curriculum import _disable_kuzu

METAB = 0.25                       # sweet-spot energie 085 (fixe)
LEVELS = (3, 6, 12, 24, 48)        # forage_payoff balaye : de 085 vers x16
N_APEX = 12                        # densite d'apex (fixe, comme 088/090)
PREY_COUNT = 15                    # forage food non-rare (= defaut WorldConfig)
MAX_TICKS = 300
NUM_AGENTS = 24
GATE = 120.0                       # survie mediane minimale d'un barreau survivable (089/090)
CHEAP_MAX = 24                     # forage_payoff <= 24 (x8) = barreau "acceptable" ; 48 (x16) = trop cher


def _cfg(forage_payoff):
    cfg = WorldConfig()
    cfg.base_metabolism = METAB
    cfg.forage_payoff = float(forage_payoff)
    cfg.max_population = 150        # defensif (PR #29) ; jamais atteint ici
    return cfg


def _verdict(levels, medians, gate=GATE):
    """Mappe (medianes de survie par niveau) -> 3 branches pre-enregistrees. Le 1er niveau qui franchit
    le gate determine le verdict : <=CHEAP_MAX -> barreau trouve ; sinon (seulement 48) -> trop cher ;
    aucun -> pas de rung (la depense est le mur)."""
    crossed = [lv for lv, m in zip(levels, medians) if m > gate]
    if not crossed:
        return "PAS DE RUNG"
    return "BARREAU TROUVE" if min(crossed) <= CHEAP_MAX else "BARREAU TROP CHER"
