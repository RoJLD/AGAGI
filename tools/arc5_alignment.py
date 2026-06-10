"""
tools/arc5_alignment.py — Alignement référentiel émergent (EDR 042, Arc 5 / Tribu).

Question : le signal qu'on a rendu utile (portée, EDR 038/040) **signifie**-t-il quelque chose ?
On mesure l'**information mutuelle** I(token ; near_Mammouth) — le token émis corrèle-t-il avec la
présence de l'apex ? MI ≈ 0 = bruit (EDR 037) ; MI > baseline-permutation = référentiel émergent.

On compare deux régimes : signal GRATUIT (legacy, tout le monde parle = bruit) vs signal COÛTEUX +
porté (porte « parler/se taire » + coût -> signal sélectif donc potentiellement informatif).

Usage : HEADLESS=1 python -m tools.arc5_alignment
"""
import time

import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
from src.graph_rag.async_logger import logger as async_logger


def _near_mammoth(env, ag, radius=3):
    for p in env.preys:
        cfg = env.config.preys.get(p["type"])
        if cfg and cfg.hp >= 50 and abs(ag["x"] - p["x"]) + abs(ag["y"] - p["y"]) <= radius:
            return True
    return False


def _mutual_info(tokens, ctxs):
    """I(token ; ctx) en bits, depuis deux listes alignées."""
    tokens, ctxs = np.array(tokens), np.array(ctxs)
    n = len(tokens)
    if n == 0:
        return 0.0
    mi = 0.0
    for tok in np.unique(tokens):
        px = np.mean(tokens == tok)
        for c in np.unique(ctxs):
            py = np.mean(ctxs == c)
            pxy = np.mean((tokens == tok) & (ctxs == c))
            if pxy > 0:
                mi += pxy * np.log2(pxy / (px * py))
    return float(mi)


def collect(config, db, signal_cost, speak_threshold, eras=8, num_agents=30, max_ticks=200):
    toks, ctxs = [], []
    for _ in range(eras):
        env = Biosphere3D(config)
        env.config.target_prey_count = 12
        env.night_enabled = False
        env.explore_eps = 0.15
        env.craft_level = 0
        env.config.active_exp_variable = "LANGUAGE"
        env.hear_radius = 3
        env.signal_cost = signal_cost
        env.speak_threshold = speak_threshold
        genomes, _ = init_primordial_soup(num_agents=num_agents, shared_db=db, config=config)
        for g in genomes:
            a = MambaAgent()
            a.from_genome(g)
            env.add_agent(a, energy=80.0)
        env.current_era = 1
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
            for ag in env.agents:
                ls = ag.get("last_spoken", [0.0] * 4)
                tok = int(np.argmax(ls)) if any(abs(v) > 0.01 for v in ls) else 4  # 4 = silence
                toks.append(tok)
                ctxs.append(1 if _near_mammoth(env, ag) else 0)
        for cand in sorted(env.agents + env.dead_agents, key=calculate_life_score, reverse=True)[:5]:
            save_to_hall_of_fame(cand)
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
    return toks, ctxs


def _verdict(config, db, label, signal_cost, speak_threshold):
    toks, ctxs = collect(config, db, signal_cost, speak_threshold)
    mi = _mutual_info(toks, ctxs)
    # Baseline par permutation : MI si token et contexte étaient indépendants (bruit).
    shuffles = []
    for _ in range(5):
        perm = np.array(ctxs); np.random.shuffle(perm)
        shuffles.append(_mutual_info(toks, perm.tolist()))
    base = float(np.mean(shuffles))
    silence = np.mean(np.array(toks) == 4)
    print(f"  {label:22s}: MI={mi:.4f} bits | baseline(perm)={base:.4f} | "
          f"silence={silence*100:.0f}% | ratio={mi/(base+1e-6):.1f}x")
    return mi, base


def main():
    async_logger.start()
    db = None
    for _ in range(50):
        db = async_logger.get_db()
        if db:
            break
        time.sleep(0.1)
    if db is None:
        print("KuzuDB indisponible.")
        return
    config = WorldConfig()
    print("ALIGNEMENT REFERENTIEL : I(token ; near_Mammouth). MI >> baseline = referentiel emergent.")
    _verdict(config, db, "signal GRATUIT (legacy)", signal_cost=0.0, speak_threshold=0.0)
    _verdict(config, db, "signal COUTEUX+porte", signal_cost=0.5, speak_threshold=0.3)
    print("\n  -> MI couteux >> MI gratuit et >> baseline = le cout fait emerger un signal informatif.")
    async_logger.stop()


if __name__ == "__main__":
    main()
