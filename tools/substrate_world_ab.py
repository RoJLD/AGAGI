"""A/B de learnabilité IN-WORLD du substrat — ADR-003, Axe 1 (aligné EDR-129).

Question : dans un VRAI monde (biosphère), le substrat GRADIENT (torch, Actor-Critic TD
par autograd) fait-il survivre une cohorte mieux que le hebbien (legacy numpy) ? Étend le
barreau-0 EDR-115 (contingence jouet) à la survie in-world. L'apprentissage intra-vie
(`compute_policy_gradient`) tourne à CHAQUE tick même en `benchmark_mode` (vérifié
world_1_stoneage.py:1447 — benchmark_mode ne coupe que la reproduction) → la règle
d'apprentissage change la survie.

Réutilise le harnais anti-contention de `cross_world_transfer` (cohorte fixe, sweet-spot
métabolique EDR-085, `memory_retriever` neutralisé) en injectant `env.batch_model_cls`
(seam S2, world_1_stoneage.py:42). CE N'EST PAS un transfer_ratio : EDR-129 montre que le
transfert est trivialement parfait (une seule compétence partagée) ; on mesure la CAPACITÉ
D'APPRENTISSAGE du substrat en monde, la vraie question ouverte.

Imports lourds (mondes) PARESSEUX → importer ce module reste léger (tests purs sans biosphère).
Usage : python tools/substrate_world_ab.py   (env: SWA_WORLD, SWA_SEED, SWA_KEVAL, SWA_AGENTS, SWA_TICKS)
"""
import os
import sys
import statistics

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.substrate_ab import compute_ab_verdict  # léger (MambaAgent + backend, pas de biosphère)

# Sweet spot énergie (EDR 085) : sans lui la survie est au plancher létal, insensible au génome.
SWEET_METAB = 0.25
SWEET_PAYOFF = 3.0


def _sweet_config():
    from src.environments.config import WorldConfig
    cfg = WorldConfig()
    cfg.base_metabolism = SWEET_METAB
    cfg.forage_payoff = SWEET_PAYOFF
    return cfg


def _ab_from_meds(legacy_meds, torch_meds, band: float = 2.0) -> dict:
    """Médianes de survie appariées legacy vs torch -> verdict. PUR (testable sans biosphère).
    band en TICKS (survie) : écart de médiane sous la bande = NEUTRE."""
    n = min(len(legacy_meds), len(torch_meds))
    rows = [{"i": i, "legacy": float(legacy_meds[i]), "torch": float(torch_meds[i]),
             "diff": float(torch_meds[i] - legacy_meds[i])} for i in range(n)]
    return {**compute_ab_verdict(rows, band=band), "per_seed": rows}


def measure_survival(world_key: str, seed: int, backend_cls, genome=None, k_eval: int = 12,
                     num_agents: int = 12, max_ticks: int = 300):
    """Survie médiane par seed d'éval d'une cohorte sous le substrat `backend_cls`.
    genome=None -> cohorte FRAÎCHE (tabula : mesure la learnabilité pure du substrat).
    Cohorte fixe (benchmark), sweet-spot, `memory_retriever` neutralisé (repro + anti-contention).
    L'injection `env.batch_model_cls = backend_cls` fait tourner tout le monde sur ce substrat."""
    import numpy as np
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.harness import seed_at
    from tools.s2_demand import WORLDS

    world_cls = WORLDS[world_key]
    meds = []
    for i in range(max(1, k_eval)):
        seed_at(seed, i)
        env = world_cls(_sweet_config())
        env.benchmark_mode = True        # cohorte fixe : pas de repro/mutation/HGT (on mesure LE substrat)
        env.night_enabled = False        # régime cohérent (isole le substrat)
        env.current_era = 10_000         # scaffolds annelés -> 0
        env.batch_model_cls = backend_cls        # <-- injection du substrat (seam S2)
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
            env.memory_retriever.clear()
        for _ in range(num_agents):
            a = MambaAgent()
            if genome is not None:
                a.from_genome(genome)
            env.add_agent(a, energy=80.0)
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
        ages = [int(a["age"]) for a in env.agents + list(getattr(env, "dead_agents", []))]
        meds.append(float(np.median(ages)) if ages else 0.0)
    return meds


def compare_backends(world_key: str = "stoneage", seed: int = 42, k_eval: int = 12,
                     num_agents: int = 12, max_ticks: int = 300, genome=None, band: float = 2.0) -> dict:
    """A/B apparié legacy (MambaBatchModel) vs torch (TorchBatchModel) dans un monde -> verdict
    de learnabilité in-world (GRADIENT_GAGNE si torch survit mieux)."""
    from src.agents.mamba_agent import MambaBatchModel
    from src.agents.torch_batch_model import TorchBatchModel

    legacy = measure_survival(world_key, seed, MambaBatchModel, genome, k_eval, num_agents, max_ticks)
    torch_meds = measure_survival(world_key, seed, TorchBatchModel, genome, k_eval, num_agents, max_ticks)
    res = _ab_from_meds(legacy, torch_meds, band)
    res["world"] = world_key
    res["legacy_median"] = float(statistics.median(legacy)) if legacy else 0.0
    res["torch_median"] = float(statistics.median(torch_meds)) if torch_meds else 0.0
    return res


def main():
    world = os.environ.get("SWA_WORLD", "stoneage")
    seed = int(os.environ.get("SWA_SEED", "42"))
    k_eval = int(os.environ.get("SWA_KEVAL", "10"))
    num_agents = int(os.environ.get("SWA_AGENTS", "12"))
    max_ticks = int(os.environ.get("SWA_TICKS", "300"))
    res = compare_backends(world, seed, k_eval, num_agents, max_ticks)
    print(f"VERDICT={res['verdict']} world={res['world']} median_diff={res['median_diff']:+.2f} "
          f"(grad_fav={res['n_gradient_favorable']}/{res['n']}, sign_p={res['sign_p']:.4f}) "
          f"| legacy={res['legacy_median']:.1f} torch={res['torch_median']:.1f}")
    for r in res["per_seed"]:
        print(f"  seed_i={r['i']} legacy={r['legacy']:.1f} torch={r['torch']:.1f} diff={r['diff']:+.1f}")
    return res


if __name__ == "__main__":
    main()
