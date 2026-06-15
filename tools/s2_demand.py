"""
tools/s2_demand.py — Benchmark S2 : "Le monde EXIGE-t-il l'intelligence ?" (cause-racine B).
Champion HoF + 3 baselines (RandomAction, RandomGenome, Reflex) x 4 mondes, survie INDIVIDUELLE
censurée + life_score (cohérence), appariement seedé (Harness D1), verdict IUT+Holm 3 issues.
Pré-enregistrement : docs/superpowers/specs/2026-06-14-S2-World-Demands-Intelligence-design.md.
"""
import numpy as np
from src.seed_ai.harness import seed_at
from src.seed_ai.persistence import calculate_life_score, load_hall_of_fame
from src.agents.baseline_models import RandomActionBatchModel, ReflexBatchModel


def run_condition(world_cls, batch_model_cls, genome, seed, num_agents=20, max_ticks=400, n_eras=1):
    """K=n_eras ères seedées base+i d'UN monde sous UNE condition. batch_model_cls=None -> moteur
    normal (MambaBatchModel, pour champion/RandomGenome) ; sinon baseline injecté (RandomAction/Reflex).
    genome=None -> agents frais (RandomGenome) ; sinon clones du génome (champion). Renvoie la survie
    INDIVIDUELLE (âge de chaque agent, mort OU survivant-censuré) + life_score, agrégée sur les ères."""
    from src.agents.mamba_agent import MambaAgent
    survival, life, censored = [], [], 0
    for i in range(max(1, int(n_eras))):
        seed_at(seed, i)
        env = world_cls()
        env.benchmark_mode = True              # cohorte fixe (pas de reproduction/mutation/HGT)
        env.night_enabled = False              # nuit OFF (irrésoluble dans Soup)
        env.current_era = 10_000               # scaffolds OFF (anneal -> 0)
        if batch_model_cls is not None:
            env.batch_model_cls = batch_model_cls
        for _ in range(num_agents):
            a = MambaAgent()
            if genome is not None:
                a.from_genome(genome)
            env.add_agent(a, energy=80.0)
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
        survivors = list(env.agents)           # encore vivants à max_ticks -> CENSURÉS
        dead = list(getattr(env, "dead_agents", []))
        for a in survivors + dead:
            survival.append(int(a["age"]))
            life.append(float(calculate_life_score(a)))
        censored += len(survivors)
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
    n = max(1, len(survival))
    return {"survival": survival, "life_score": life, "censored_frac": censored / n}


def load_champion_genome():
    """Génome du #1 du HoF. Lève si le HoF est vide (pas de `except: pass` silencieux, blocker panel)."""
    _version, entries = load_hall_of_fame()
    if not entries:
        raise RuntimeError("HoF vide : impossible de lancer S2 sans champion. Évoluer d'abord (main_biosphere).")
    return entries[0].genome


# Les 5 conditions par monde. (batch_model_cls, fresh_genome) :
#  - champion / random_genome -> moteur normal (None) ; genome fourni ou frais.
#  - random_action / reflex -> baseline injecté.
def _reflex_prudent(agents, world_model=None):
    return ReflexBatchModel(agents, world_model, prudent=True)


CONDITIONS = {
    "champion":        {"batch_model_cls": None,                    "fresh_genome": False},
    "random_genome":   {"batch_model_cls": None,                    "fresh_genome": True},
    "random_action":   {"batch_model_cls": RandomActionBatchModel,  "fresh_genome": True},
    "reflex_naive":    {"batch_model_cls": ReflexBatchModel,        "fresh_genome": True},
    "reflex_prudent":  {"batch_model_cls": _reflex_prudent,         "fresh_genome": True},
}
