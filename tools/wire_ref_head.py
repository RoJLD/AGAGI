"""
tools/wire_ref_head.py — Le langage fiable RÉELLEMENT dans l'agent vivant (EDR 074).

On branche la tête référentielle dédiée (EDR 072/073) dans le VRAI Biosphere3D : on co-entraîne les
têtes des agents (jeu de population, 072), puis on lance le monde de Lewis avec `use_ref_head=True` et
on mesure MI(token; apex) LIVE. ON (têtes co-entraînées) vs OFF (connectome 1-tick), multi-seed.
Le langage émerge-t-il FIABLEMENT dans l'agent vivant (vs 25 % loterie mutation, EDR 053) ?

Usage : HEADLESS=1 python -m tools.wire_ref_head
"""
import time

import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from src.graph_rag.async_logger import logger as async_logger
from src.seed_ai.referential_head import new_head, train_population, cross_decode_accuracy
from tools.lexicon import _setup as _setup3            # monde de Lewis 3 référents (Mammouth/Ours/Leurre)
from tools.arc5_alignment import _mutual_info


def run_seed(config, db, seed, use_head, num_agents=24, max_ticks=200):
    env = Biosphere3D(config)
    _setup3(env)
    env.use_ref_head = use_head
    genomes, _ = init_primordial_soup(num_agents=num_agents, shared_db=db, config=config)
    rng = np.random.RandomState(seed)
    heads = None
    if use_head:
        heads = [new_head(M=3, V=4, H=12, rng=rng) for _ in range(len(genomes))]
        train_population(heads, steps=5000, seed=seed)   # CO-ÉVOLUTION par gradient -> code partagé
    for k, g in enumerate(genomes):
        a = MambaAgent()
        a.from_genome(g)
        if heads is not None:
            a.ref_head = heads[k]
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    toks, apex = [], []
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        t += 1
        for ag in env.agents:
            ai = env._apex_idx(ag)                       # apex perçu (0/1/2) ou None
            if ai is None:
                continue
            ls = ag.get("last_spoken", [0.0] * 4)
            if any(abs(v) > 0.01 for v in ls):
                toks.append(int(np.argmax(ls)))
                apex.append(ai)
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    if len(toks) < 5:
        return 0.0, len(toks)
    mi = _mutual_info(toks, apex)
    base = float(np.mean([_mutual_info(toks, np.random.permutation(np.array(apex)).tolist()) for _ in range(5)]))
    return mi - base, len(toks)


def main(seeds=range(6)):
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
    seeds = list(seeds)

    print(f"LANGAGE DANS L'AGENT VIVANT : tete referentielle dediee dans Biosphere3D. {len(seeds)} seeds.")
    on, off = [], []
    for s in seeds:
        gain_on, n_on = run_seed(config, db, s, True)
        gain_off, n_off = run_seed(config, db, s, False)
        on.append(gain_on)
        off.append(gain_off)
        print(f"  seed {s}: MI_gain TETE={gain_on:+.4f} (n={n_on})  vs  CONNECTOME={gain_off:+.4f} (n={n_off})")

    rate = np.mean([g > 0.1 for g in on])
    print("\n=== VERDICT (langage referentiel LIVE) ===")
    print(f"  TETE dediee : MI_gain moyen = {np.mean(on):.4f} ; fiabilite(>0.1) = {rate*100:.0f}%")
    print(f"  CONNECTOME  : MI_gain moyen = {np.mean(off):.4f}")
    print(f"  (repere : sous mutation, ~25% loterie de signaux faibles -- EDR 053)")
    if np.mean(on) > 0.3 and rate >= 0.8:
        print("  -> LANGAGE REFERENTIEL FIABLE dans l'agent vivant ! La tete dediee transforme la loterie")
        print("     en convention partagee mesurable dans le vrai Biosphere3D. Cablage REUSSI.")
    elif np.mean(on) > np.mean(off) + 0.1:
        print("  -> la tete ameliore nettement le referentiel live (vs connectome) ; fiabilite a confirmer.")
    else:
        print("  -> la tete ne se traduit pas en MI live (interference biosphere / gate de parole).")

    async_logger.stop()


if __name__ == "__main__":
    main()
