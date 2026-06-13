"""tools/lang_on_competent.py — Le langage paye-t-il sur un substrat COMPÉTENT ? (EDR 082)

Boucle bouclée. EDR 075 : le langage ne paye pas car les agents (frais) ne savent ni survivre ni
chasser. EDR 076-081 : on a forgé un substrat COMPÉTENT et croissant (HoF robuste). On re-teste ici le
bénéfice du langage sur ce substrat : évoluer des champions compétents DANS le monde de Lewis (robuste
K=4), leur donner des têtes référentielles co-entraînées (074), puis comparer FIABLE (tête + décode-et-
agis) vs SOLO (ignore les signaux). Le décode-et-agis fait approcher Mammouth/Ours et fuir Leurre.

Usage : HEADLESS=1 python -m tools.lang_on_competent
"""
import time
import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.persistence import calculate_life_score
from src.seed_ai.referential_head import new_head, train_population
from src.graph_rag.async_logger import logger as async_logger
from tools.evolve_competence import _reproduce
from tools.robust_eval import _load_champions
from tools.lexicon import _setup as _setup3
from tools.progress import Progress


def _run_era_lewis(cfg, genomes, use_head=False, decode_act=False, heads=None, max_ticks=300, measure=False):
    env = Biosphere3D(cfg)
    _setup3(env)
    env.use_ref_head = use_head
    env.decode_act = decode_act
    for k, g in enumerate(genomes):
        a = MambaAgent()
        a.from_genome(g)
        if heads is not None:
            a.ref_head = heads[k]
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        t += 1
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    out = {"ticks": t}
    if measure:
        out["mammoth"] = sum(ag.get("mammoth_kills", 0) for ag in pool)
        out["leurre"] = int(getattr(env, "leurre_hits", 0))
        out["survivors"] = len(env.agents)
    else:
        out["scored"] = sorted([(calculate_life_score(a),
                                 a["model"].genome if "model" in a else a.get("genome")) for a in pool],
                               key=lambda sg: sg[0], reverse=True)[:5]
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    return out


def evolve_lewis(cfg, mc, gens, num_agents, K, prog):
    """Évolution ROBUSTE dans le monde de Lewis -> champions compétents pour CE monde."""
    best_ever = [(0.0, g) for g in _load_champions()]
    for _ in range(gens):
        genomes = _reproduce([g for _s, g in best_ever], num_agents, mc)
        scored = _run_era_lewis(cfg, genomes)["scored"]
        if scored and K > 1:                            # ré-éval robuste du top candidat
            g0 = scored[0][1]
            vals = [_run_era_lewis(cfg, [g0] * num_agents)["scored"][0][0] for _ in range(K)]
            scored[0] = (float(np.mean(vals)), g0)
        best_ever = sorted(best_ever + scored, key=lambda sg: sg[0], reverse=True)[:5]
        prog.update()
    return [g for _s, g in best_ever]


def main(gens=12, num_agents=24, K=4, seeds=range(4)):
    async_logger.start()
    for _ in range(50):
        if async_logger.get_db():
            break
        time.sleep(0.1)
    cfg = WorldConfig()
    mc = MutationConfig(weight_init_std=2.0)
    print(f"LANGAGE SUR SUBSTRAT COMPETENT : evolution robuste (K={K}) dans Lewis, puis FIABLE vs SOLO.")

    champions = evolve_lewis(cfg, mc, gens, num_agents, K, Progress(gens, label="evolution Lewis robuste"))

    fia, solo, diffs = {"mammoth": [], "leurre": []}, {"mammoth": [], "leurre": []}, []
    seeds = list(seeds)
    pf = Progress(len(seeds) * 2, label="FIABLE vs SOLO")
    for s in seeds:
        rng = np.random.RandomState(s)
        genomes = _reproduce(champions, num_agents, mc)
        heads = [new_head(M=3, V=4, H=12, rng=rng) for _ in range(len(genomes))]
        train_population(heads, steps=5000, seed=s)
        rf = _run_era_lewis(cfg, genomes, use_head=True, decode_act=True, heads=heads, measure=True); pf.update()
        rs = _run_era_lewis(cfg, genomes, use_head=True, decode_act=False, heads=heads, measure=True); pf.update()
        for k in ("mammoth", "leurre"):
            fia[k].append(rf[k]); solo[k].append(rs[k])
        diffs.append(rf["mammoth"] - rs["mammoth"])      # comparaison APPARIÉE (mêmes agents)

    print(f"\n=== LANGAGE PAYE-T-IL sur agents competents ? FIABLE vs SOLO, {len(seeds)} seeds (apparié) ===")
    mf, ms = np.mean(fia["mammoth"]), np.mean(solo["mammoth"])
    print(f"  FIABLE : Mammouths={mf:.2f} +/- {np.std(fia['mammoth']):.2f}  Leurres={np.mean(fia['leurre']):.2f}")
    print(f"  SOLO   : Mammouths={ms:.2f} +/- {np.std(solo['mammoth']):.2f}  Leurres={np.mean(solo['leurre']):.2f}")
    d = np.array(diffs, dtype=float)
    win = float(np.mean(d > 0))
    se = d.std(ddof=1) / np.sqrt(len(d)) if len(d) > 1 else float("inf")
    print(f"  diff appariee Mammouths (FIABLE-SOLO) = {d.mean():+.2f} +/- {se:.2f} (SE) ; FIABLE>SOLO dans {win*100:.0f}% des seeds")
    print("\n=== VERDICT ===")
    if d.mean() > 0 and d.mean() > 2 * se and win >= 0.7:
        print(f"  -> sur substrat COMPETENT, le langage PAYE de facon ROBUSTE : +{d.mean():.1f} Mammouths/run (>2 SE).")
        print(f"     La boucle se referme : EDR 075 (gate competence) leve -> le langage confere un avantage mesurable.")
    elif d.mean() > 0 and win >= 0.6:
        print(f"  -> tendance positive ({d.mean():+.1f} Mammouths, {win*100:.0f}% des seeds) mais sous le seuil de robustesse (>2 SE).")
    else:
        print(f"  -> pas d'avantage robuste (diff {d.mean():+.1f}, {win*100:.0f}% des seeds) : competence necessaire, pas suffisante.")
    async_logger.stop()


if __name__ == "__main__":
    main()
