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


def _run_curriculum_arm(cfg, mc, levels, grad_cfg, base, num_agents, max_ticks=MAX_TICKS):
    """Enchaîne les paliers de létalité (ordre croissant) en PORTANT les génomes d'un palier au
    suivant. base = rb + 10000 ; palier idx seedé sur base + idx*1000 (plages disjointes). Renvoie
    (final_genomes, total_eras, transcript) ; transcript = diagnostic 'où ça bloque' (une entrée/palier)."""
    genomes = _load_champions()
    transcript, total_eras = [], 0
    for idx, lf in enumerate(levels):
        genomes, eras, history, graduated = _coevolve_at(
            cfg, mc, lf, genomes, grad_cfg, base + idx * 1000, num_agents, max_ticks,
        )
        total_eras += eras
        transcript.append({
            "level": lf,
            "eras": eras,
            "competence": history[-1] if history else 0.0,
            "graduated": graduated,
        })
    return genomes, total_eras, transcript


def _run_flat_arm(cfg, mc, terminal_frac, budget_eras, base, num_agents, max_ticks=MAX_TICKS):
    """CONTRÔLE : cold start directement au palier terminal pour EXACTEMENT budget_eras ères
    (= total curriculum de la même répétition -> budget égal). base = rb + 20000 ; seed_at(base, era).
    Pas de porte de maîtrise : on tourne tout le budget au terminal."""
    seed_at(base, 0)          # seed_at avant _load_champions pour que le fallback MambaAgent() soit reproductible
    best = [(0.0, g) for g in _load_champions()]
    for era in range(1, budget_eras + 1):
        seed_at(base, era)
        genomes = _reproduce([g for _s, g in best], num_agents, mc)
        r = _run_era_clean(cfg, genomes, terminal_frac, max_ticks=max_ticks)
        best = sorted(best + r["scored"], key=lambda sg: sg[0], reverse=True)[:5]
    return [g for _s, g in best]


def _measure_terminal(cfg, mc, genomes, leurre_frac, base, num_agents, n_eval, max_ticks=MAX_TICKS):
    """Mesure n_eval ères propres au palier terminal sur la population évoluée. base = rb + 30000,
    IDENTIQUE entre curriculum et flat -> mesure appariée (mêmes mondes). net = kills − leurre_hits
    (qualité de discrimination) ; surv = ticks (survie de l'ère, gate >120 comme 089)."""
    nets, survs = [], []
    for i in range(n_eval):
        seed_at(base, i)
        gen = _reproduce(genomes, num_agents, mc)
        r = _run_era_clean(cfg, gen, leurre_frac, max_ticks=max_ticks)
        nets.append(int(r["kills"]) - int(r["leurre_hits"]))
        survs.append(int(r["ticks"]))
    return {"nets": nets, "survs": survs}
