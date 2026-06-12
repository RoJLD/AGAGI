"""
tools/func_benefit.py — Le BÉNÉFICE FONCTIONNEL du langage fiable (EDR 075).

Question climax de l'arc du langage : un code fiable (074) confère-t-il un AVANTAGE de survie ? À
distance, Mammouth (gain de groupe) et Leurre (piège) sont indistinguables — seul le signal tranche.
On compare 3 conditions, MÊME comportement « décode-et-agis », seule la QUALITÉ du signal change :
  - FIABLE  : têtes co-entraînées (code partagé) + décode-et-agis -> coordination correcte.
  - BRUITÉ  : tokens connectome (loterie) + décode-et-agis -> agir sur du bruit.
  - SOLO    : pas de décode-et-agis -> ligne de base (ignorer les signaux).
FIABLE vs SOLO = « agir sur le langage aide-t-il ? » ; FIABLE vs BRUITÉ = « la fiabilité compte-t-elle ? »
Mesure : Mammouths tués (gain), Leurres frappés (piège, à minimiser), survie.

Usage : HEADLESS=1 python -m tools.func_benefit
"""
import time

import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from src.graph_rag.async_logger import logger as async_logger
from src.seed_ai.referential_head import new_head, train_population
from tools.lexicon import _setup as _setup3


def run_seed(config, db, seed, use_head, decode_act, num_agents=24, max_ticks=300):
    env = Biosphere3D(config)
    _setup3(env)
    env.use_ref_head = use_head
    env.decode_act = decode_act
    genomes, _ = init_primordial_soup(num_agents=num_agents, shared_db=db, config=config)
    rng = np.random.RandomState(seed)
    heads = [new_head(M=3, V=4, H=12, rng=rng) for _ in range(len(genomes))]
    train_population(heads, steps=5000, seed=seed)        # code partagé fiable (072)
    for k, g in enumerate(genomes):
        a = MambaAgent()
        a.from_genome(g)
        a.ref_head = heads[k]
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    n0 = len(env.agents)
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        t += 1
    mammoth = sum(ag.get("mammoth_kills", 0) for ag in env.agents)
    survivors = len(env.agents)
    energy = float(np.mean([ag["energy"] for ag in env.agents])) if env.agents else 0.0
    leurre = env.leurre_hits
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    return {"mammoth": mammoth, "leurre": leurre, "survivors": survivors, "energy": energy, "n0": n0}


CONDITIONS = [
    ("FIABLE", True, True),     # code partagé + décode-et-agis
    ("BRUITE", False, True),    # tokens connectome + décode-et-agis
    ("SOLO", True, False),      # code partagé mais on n'agit pas dessus
]


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
    print(f"BENEFICE FONCTIONNEL du langage fiable : {len(seeds)} seeds, 3 conditions.")
    agg = {name: {"mammoth": [], "leurre": [], "survivors": []} for name, _, _ in CONDITIONS}
    for s in seeds:
        line = f"  seed {s}: "
        for name, uh, da in CONDITIONS:
            r = run_seed(config, db, s, uh, da)
            for k in ("mammoth", "leurre", "survivors"):
                agg[name][k].append(r[k])
            line += f"{name}(mam={r['mammoth']},leu={r['leurre']},surv={r['survivors']})  "
        print(line)

    print("\n=== VERDICT (bénéfice fonctionnel) ===")
    for name, _, _ in CONDITIONS:
        m = np.mean(agg[name]["mammoth"])
        le = np.mean(agg[name]["leurre"])
        su = np.mean(agg[name]["survivors"])
        print(f"  {name:7s}: Mammouths={m:.2f}  Leurres={le:.2f}  survivants={su:.2f}")
    mf, ms = np.mean(agg["FIABLE"]["mammoth"]), np.mean(agg["SOLO"]["mammoth"])
    lf, ls_ = np.mean(agg["FIABLE"]["leurre"]), np.mean(agg["SOLO"]["leurre"])
    lb = np.mean(agg["BRUITE"]["leurre"])
    print()
    if mf > ms * 1.15 or lf < ls_ * 0.85:
        print(f"  -> le langage FIABLE PAYE : plus de Mammouths ({mf:.1f} vs {ms:.1f} solo) et/ou moins")
        print(f"     de Leurres ({lf:.1f} vs {ls_:.1f} solo). Le code fiable confere un AVANTAGE.")
        if lf < lb * 0.85:
            print(f"     Et la FIABILITE compte : {lf:.1f} Leurres (fiable) < {lb:.1f} (bruite).")
    else:
        print(f"  -> pas d'avantage fonctionnel net (Mam {mf:.1f}/{ms:.1f}, Leu {lf:.1f}/{ls_:.1f}).")
        print(f"     Le langage est fiable mais ne se traduit pas (encore) en survie -- resultat honnete.")
    async_logger.stop()


if __name__ == "__main__":
    main()
