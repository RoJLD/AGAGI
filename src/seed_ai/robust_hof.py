"""
src/seed_ai/robust_hof.py — Évaluation ROBUSTE du Hall of Fame (EDR 078/079).

La sélection HoF historique évalue un candidat sur UNE ère (extinction ~30-60 ticks) -> fitness
ULTRA-BRUITÉE -> sélectionne les génomes CHANCEUX, pas les BONS (plateau de compétence, EDR 076). Banc
(078) : nettoyer le signal forge ×3 ; vivant (079) : +27 %. Remède : ré-évaluer un génome sur K ères
indépendantes (clones) et moyenner le life_score avant de committer. Gated par `config.robust_hof_K`.

Imports paresseux (Biosphere3D/MambaAgent) pour éviter toute circularité avec le monde.
"""
import numpy as np
from src.seed_ai.harness import seed_at


def robust_evaluate(config, genome, K=3, num_agents=20, max_ticks=400, seed=None):
    """Compétence robuste d'un génome : moyenne du meilleur life_score sur K ères de clones.
    De-bruite la sélection HoF. seed fourni -> ères seedées base+i (reproductible + apparié).
    Renvoie 0.0 si aucune ère scorable."""
    from src.worlds.world_1_stoneage import Biosphere3D
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.persistence import calculate_life_score

    scores = []
    for i in range(max(1, int(K))):
        if seed is not None:
            seed_at(seed, i)
        env = Biosphere3D(config)
        for _ in range(num_agents):
            a = MambaAgent()
            a.from_genome(genome)
            env.add_agent(a, energy=80.0)
        env.current_era = 1
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
        pool = list(env.agents) + list(getattr(env, "dead_agents", []))
        if pool:
            scores.append(max(calculate_life_score(a) for a in pool))
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
    return float(np.mean(scores)) if scores else 0.0


def robust_rank(config, candidates, K, num_agents=20, seed=None):
    """Trie des candidats (dicts agent avec 'model'.genome ou 'genome') par compétence ROBUSTE.
    seed fourni -> TOUS les candidats sont évalués sur les MÊMES K mondes (appariement) -> ranking
    de-bruité et reproductible. seed=None -> comportement historique (mondes non appariés).
    Renvoie [(robust_score, candidate)] décroissant. Utilisé avant save_to_hall_of_fame."""
    out = []
    for c in candidates:
        g = c["model"].genome if "model" in c else c.get("genome")
        if g is None:
            continue
        out.append((robust_evaluate(config, g, K, num_agents, seed=seed), c))
    out.sort(key=lambda x: x[0], reverse=True)
    return out
