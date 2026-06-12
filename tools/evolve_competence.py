"""
tools/evolve_competence.py — La compétence de foraging ÉVOLUE-t-elle ? (EDR 076)

EDR 075 : le bénéfice du langage est gaté par la compétence du substrat. Diagnostic : les ères sont
bornées par l'EXTINCTION (~50 ticks) ; la compétence s'accumule sur de NOMBREUSES ères via le HoF, pas
en une. Question fondamentale : sur 30 ères d'évolution, la compétence (survie + chasse au Mammouth)
MONTE-t-elle, ou plafonne-t-elle ?

Harnais ISOLÉ (population propre, sélection par life_score, mutation) -> trajectoire de compétence.
Usage : HEADLESS=1 python -m tools.evolve_competence
"""
import copy
import time

import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from src.seed_ai.mutation import apply_mutations, MutationConfig
from src.seed_ai.repopulation import build_population
from src.seed_ai.persistence import calculate_life_score, load_hall_of_fame
from src.graph_rag.async_logger import logger as async_logger
from tools.progress import Progress


def _reproduce(champions, num_agents, mc):
    """Réplique la reproduction de init_primordial_soup : ÉLITE intacte + enfants mutés +
    fraction à mutation forte (EDR 024). Sans élitisme, l'évolution s'effondre (bug harnais)."""
    heavy = copy.deepcopy(mc)
    heavy.weight_mutate_rate = min(1.0, mc.weight_mutate_rate * 2.0)
    heavy.weight_mutate_power = mc.weight_mutate_power * 1.5
    return build_population(champions, num_agents, mc, apply_mutations, heavy_config=heavy, heavy_frac=0.3)


def run_era(cfg, genomes, max_ticks=400):
    env = Biosphere3D(cfg)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        t += 1
    pool = env.agents + list(getattr(env, "dead_agents", []))
    eaten = sum(ag.get("preys_eaten", 0) for ag in pool)
    mam = int(getattr(env, "big_kills", 0))
    ranked = sorted(pool, key=calculate_life_score, reverse=True)
    best_score = calculate_life_score(ranked[0]) if ranked else 0.0
    scored = []                                          # (score, genome) pour le cliquet best-ever
    for ag in ranked[:5]:
        g = ag["model"].genome if "model" in ag else ag.get("genome")
        if g is not None:
            scored.append((float(calculate_life_score(ag)), g))
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    return scored, {"ticks": t, "eaten": eaten, "mam": mam, "score": float(best_score)}


def main(eras=30, num_agents=30):
    async_logger.start()
    for _ in range(50):
        if async_logger.get_db():
            break
        time.sleep(0.1)
    cfg = WorldConfig()
    mc = MutationConfig(weight_init_std=2.0)         # comme init_primordial_soup

    # Champions initiaux : le HoF (compétence accumulée), sinon frais. Les entrées HoF sont des
    # tuples (score, genome, stats) ou des objets .genome -- PAS des dicts (cf. init_primordial_soup).
    champions = []
    try:
        _, hof = load_hall_of_fame()
        for entry in hof:
            if isinstance(entry, tuple):
                champions.append(entry[1])
            elif hasattr(entry, "genome"):
                champions.append(entry.genome)
        champions = [g for g in champions if g is not None][:5]
    except Exception:
        champions = []
    seeded = "HoF" if champions else "frais"
    if not champions:
        champions = [MambaAgent().genome for _ in range(5)]
    print(f"EVOLUTION de la COMPETENCE : {eras} eres, {num_agents} agents. Depart : {len(champions)} champions ({seeded}).")

    best_ever = [(0.0, g) for g in champions]            # CLIQUET : meilleurs de tous les temps (comme le HoF réel)
    hist = []
    prog = Progress(eras, label="eres")                  # barre de progression + ETA (demande user)
    for era in range(1, eras + 1):
        champ_genomes = [g for (_s, g) in best_ever]
        genomes = _reproduce(champ_genomes, num_agents, mc)   # reproduit depuis les MEILLEURS DE TOUS LES TEMPS
        scored, m = run_era(cfg, genomes)
        # cliquet : fusionne le top de cette ère avec le best-ever, garde le top-5 GLOBAL (anti-perte)
        merged = best_ever + scored
        best_ever = sorted(merged, key=lambda sg: sg[0], reverse=True)[:5]
        hist.append(m)
        prog.update()
        if era % 3 == 0 or era <= 3:
            print(f"  ere {era:2d}: survie_ticks={m['ticks']:3d}  proies={m['eaten']:3d}  mammouths={m['mam']}  best_score={m['score']:.1f}")

    def avg(key, sl):
        return float(np.mean([h[key] for h in sl]))
    first, last = hist[:5], hist[-5:]
    print("\n=== TRAJECTOIRE (5 premieres vs 5 dernieres eres) ===")
    for key, label in [("ticks", "survie_ticks"), ("eaten", "proies"), ("mam", "mammouths"), ("score", "life_score")]:
        f, l = avg(key, first), avg(key, last)
        arrow = "MONTE" if l > f * 1.1 else ("PLAFONNE" if abs(l - f) <= f * 0.1 else "BAISSE")
        print(f"  {label:13s}: {f:6.1f} -> {l:6.1f}   [{arrow}]")
    print("\n=== VERDICT ===")
    tf, tl = avg("ticks", first), avg("ticks", last)
    mf, ml = avg("mam", first), avg("mam", last)
    if tl > tf * 1.15 or ml > mf * 1.15:
        print("  -> la COMPETENCE EVOLUE : survie et/ou chasse au Mammouth montent. Un substrat comp  ")
        print("     petent est atteignable (plus d'eres) -> le langage pourra ensuite le demultiplier.")
    else:
        print("  -> la competence PLAFONNE sur 30 eres. L'evolution par mutation/extinction ne suffit")
        print("     pas a forger le substrat -> levier = gradient intra-vie (cf. 067) ou monde re-calibre.")
    async_logger.stop()


if __name__ == "__main__":
    main()
