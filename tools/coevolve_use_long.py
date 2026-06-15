"""tools/coevolve_use_long.py — EDR 089 : l'usage co-évolué du langage paye-t-il sur substrat à survie
LONGUE ? Power EDR 083 sur son levier #1 (la survie). Réutilise le moteur d'083 (coevolve + _run_era_lewis ;
_setup met déjà night OFF) avec un cfg SWEET-SPOT (085) ; ajoute mesure à composantes + boucle R appariée
+ stats rigoureuses. N'altère pas coevolve_language.py.
Pré-enregistrement : docs/superpowers/specs/2026-06-15-EDR089-Coevolve-Use-Long-design.md
"""
import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.referential_head import new_head, train_population
from src.seed_ai.harness import Harness, seed_at
from src.seed_ai import exp_stats as st
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from tools.evolve_competence import _reproduce
from tools.robust_eval import _load_champions
from tools.lang_on_competent import _run_era_lewis
from tools.coevolve_language import coevolve
from tools.lexicon import _setup as _setup3

METAB, PAYOFF = 0.25, 3.0          # sweet spot survie longue (EDR 085)


def _sweet_cfg():
    cfg = WorldConfig()
    cfg.base_metabolism = METAB
    cfg.forage_payoff = PAYOFF
    return cfg


class _NullProg:
    """Progress no-op : la boucle R a sa propre barre ; coevolve ne doit pas en empiler."""
    def update(self, n=1):
        pass


def _run_era_clean(cfg, genomes, use_head=False, decode_act=False, heads=None, max_ticks=300):
    """Variante déterministe de _run_era_lewis(measure=True) : stoppe le memory_retriever
    (thread KuzuDB) avant la boucle de simulation pour garantir le déterminisme np.random
    (le retriever est une source de non-déterminisme temporel via in_mem dans step())."""
    env = Biosphere3D(cfg)
    _setup3(env)
    # Stoppe le thread memory_retriever AVANT la boucle : il lirait KuzuDB en arrière-plan
    # et polluerait in_mem[] de façon timing-dépendante (race condition).
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
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
    return {
        "ticks": t,
        "mammoth": sum(ag.get("mammoth_kills", 0) for ag in pool),
        "leurre": int(getattr(env, "leurre_hits", 0)),
        "survivors": len(env.agents),
    }


def _measure_full(cfg, champions, mc, use_head, heads, num_agents, n, base):
    """Mesure sur n ères propres (seedées, plage 1000+ disjointe de coevolve) : kills (primaire),
    net (kills − leurre_hits), survie (ticks). decode_act=False (l'usage émerge, n'est pas imposé)."""
    out = {"kills": [], "nets": [], "survs": []}
    for i in range(n):
        seed_at(base, 1000 + i)
        genomes = _reproduce(champions, num_agents, mc)
        hd = heads[:len(genomes)] if heads else None
        r = _run_era_clean(cfg, genomes, use_head=use_head, decode_act=False, heads=hd)
        k = int(r["mammoth"]); le = int(r["leurre"])
        out["kills"].append(k)
        out["nets"].append(k - le)
        out["survs"].append(int(r["ticks"]))
    return out
