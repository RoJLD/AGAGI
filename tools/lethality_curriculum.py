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


def _run_era_clean(cfg, genomes, leurre_frac, max_ticks=MAX_TICKS):
    """Une ère DÉTERMINISTE à létalité leurre_frac. _setup_critical pose les apex (Leurre dmg=50) ;
    memory_retriever stoppé AVANT la boucle (hazard mémoire ambiante KuzuDB, dette core d'089) ;
    forage food = PREY_COUNT. PAS de langage (use_ref_head/decode_act = False). Renvoie toujours
    {ticks,kills,leurre_hits,survivors,scored} (scored = top-5 (life_score, genome) pour la sélection)."""
    env = Biosphere3D(cfg)
    _setup_critical(env, leurre_frac, n_apex=N_APEX)
    env.config.target_prey_count = PREY_COUNT
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    env.use_ref_head = False
    env.decode_act = False
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        t += 1
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    scored = sorted(
        [(calculate_life_score(a), a["model"].genome if "model" in a else a.get("genome")) for a in pool],
        key=lambda sg: sg[0], reverse=True,
    )[:5]
    return {
        "ticks": t,
        "kills": int(sum(ag.get("mammoth_kills", 0) for ag in pool)),
        "leurre_hits": int(getattr(env, "leurre_hits", 0)),
        "survivors": len(env.agents),
        "scored": scored,
    }


def _coevolve_at(cfg, mc, leurre_frac, start_genomes, grad_cfg, base, num_agents, max_ticks=MAX_TICKS):
    """Co-évolue UN palier de létalité jusqu'à graduation (has_graduated + patience K) ou max_eras
    (garde-temps). seed_at(base, era) -> reproductible. Compétence par ère = survie normalisée.
    Renvoie (best_genomes_top5, eras_held, history, graduated)."""
    best = [(0.0, g) for g in start_genomes]
    history, streak, graduated, era = [], 0, False, 0
    while era < grad_cfg.max_eras:
        era += 1
        seed_at(base, era)
        genomes = _reproduce([g for _s, g in best], num_agents, mc)
        r = _run_era_clean(cfg, genomes, leurre_frac, max_ticks=max_ticks)
        history.append(_survival_competence([r["ticks"]], max_ticks))
        best = sorted(best + r["scored"], key=lambda sg: sg[0], reverse=True)[:5]
        if has_graduated(history, grad_cfg):
            streak += 1
            if streak >= grad_cfg.patience:
                graduated = True
                break
        else:
            streak = 0
    return [g for _s, g in best], era, history, graduated
