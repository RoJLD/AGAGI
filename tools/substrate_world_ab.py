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


def evolve_native(world_key: str, seed: int, backend_cls, max_ticks: int = 1500,
                  num_agents: int = 24, start_energy: float = 80.0, pop_cap: int = 120):
    """ÉVOLUTION NATIVE sur un substrat (EDR-137 suite, #2 Baldwin). benchmark_mode=False -> la
    reproduction/mutation/HGT façonnent le connectome SOUS ce substrat (les descendants héritent du
    W appris par le substrat + mutation = Baldwin/Lamarckien). Sépare « moteur » de « mismatch » :
    un champion évolué NATIVEMENT sur torch évite-t-il la déstabilisation du transplant (33.0) ?

    Retourne le génome du plus vieux agent observé (proxy de champion natif) + stats de population
    (extinction / pic). `pop_cap` borne le coût (torch forward sur B grand est lent)."""
    import copy
    import numpy as np
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.harness import seed_at
    from tools.s2_demand import WORLDS

    world_cls = WORLDS[world_key]
    seed_at(seed, 0)
    env = world_cls(_sweet_config())
    env.benchmark_mode = False       # <-- ÉVOLUTION active (repro/mutation/HGT)
    env.night_enabled = False
    env.current_era = 10_000
    env.batch_model_cls = backend_cls
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
        env.memory_retriever.clear()
    for _ in range(num_agents):
        env.add_agent(MambaAgent(), energy=start_energy)

    best_age, best_genome, peak_pop, births = -1, None, num_agents, 0
    t = 0
    while env.agents and t < max_ticks:
        n_before = len(env.agents)
        env.step()
        t += 1
        n_after = len(env.agents)
        if n_after > n_before:
            births += (n_after - n_before)
        peak_pop = max(peak_pop, n_after)
        for a in env.agents:
            age = int(a["age"])
            if age > best_age:
                best_age = age
                best_genome = copy.deepcopy(a["model"].genome)
        # garde-fou coût : si la population explose, on stoppe (le probe a son signal)
        if n_after > pop_cap:
            break
    return {"world": world_key, "seed": seed, "ticks": t, "best_age": best_age,
            "best_genome": best_genome, "final_pop": len(env.agents), "peak_pop": peak_pop,
            "births": births, "extinct": not env.agents}


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


def _load_champion(hof_path: str):
    """Génome du #1 d'un HoF (seam EDR-126, réutilise le loader de cross_world_transfer)."""
    import importlib
    from src.seed_ai import persistence
    os.environ["HOF_PATH"] = hof_path
    importlib.reload(persistence)
    _v, entries = persistence.load_hall_of_fame()
    if not entries:
        raise RuntimeError(f"HoF vide : {hof_path}")
    return entries[0].genome


def compare_arms(world_key: str = "stoneage", seed: int = 42, k_eval: int = 12,
                 num_agents: int = 12, max_ticks: int = 300, genome=None, band: float = 2.0) -> dict:
    """A/B à TROIS bras (EDR-134 suite, contrôle du confound d'organes) :

      - legacy-full : MambaBatchModel        (organes ON, règle numpy)
      - legacy-core : MambaCoreBatchModel     (organes ABLÉS, règle numpy)  <-- nouveau
      - torch-core  : TorchBatchModel         (organes absents, règle autograd)

    Lectures décisives :
      * legacy-full vs legacy-core = APPORT DES ORGANES (si le champion chute -> organes porteurs).
      * legacy-core vs torch-core  = RÈGLE D'APPRENTISSAGE À PARITÉ D'ORGANES (la question PROPRE
        qu'EDR-134 ne pouvait pas trancher).
    """
    from src.agents.mamba_agent import MambaBatchModel, MambaCoreBatchModel
    from src.agents.torch_batch_model import TorchBatchModel

    legacy = measure_survival(world_key, seed, MambaBatchModel, genome, k_eval, num_agents, max_ticks)
    core = measure_survival(world_key, seed, MambaCoreBatchModel, genome, k_eval, num_agents, max_ticks)
    torch_meds = measure_survival(world_key, seed, TorchBatchModel, genome, k_eval, num_agents, max_ticks)

    med = lambda xs: float(statistics.median(xs)) if xs else 0.0
    return {
        "world": world_key,
        "legacy_median": med(legacy), "core_median": med(core), "torch_median": med(torch_meds),
        "organs_contribution": _ab_from_meds(core, legacy, band),   # "torch"=legacy_full : diff>0 => organes AIDENT
        "rule_at_parity": _ab_from_meds(core, torch_meds, band),    # torch vs core : GRADIENT_GAGNE => la règle torch gagne À PARITÉ
        "full_confound": _ab_from_meds(legacy, torch_meds, band),   # reproduit la mesure EDR-134
    }


def main():
    world = os.environ.get("SWA_WORLD", "stoneage")
    seed = int(os.environ.get("SWA_SEED", "42"))
    k_eval = int(os.environ.get("SWA_KEVAL", "10"))
    num_agents = int(os.environ.get("SWA_AGENTS", "12"))
    max_ticks = int(os.environ.get("SWA_TICKS", "300"))

    if os.environ.get("SWA_MODE") == "evolve":
        # #2 Baldwin : évolue NATIVEMENT sur torch, puis mesure le champion natif sous torch
        # (comparer à transplant legacy sous torch ~33.0, et legacy-natif ~74.5).
        from src.agents.torch_batch_model import TorchBatchModel
        from src.agents.mamba_agent import MambaBatchModel
        ev_ticks = int(os.environ.get("SWA_EVOTICKS", "1500"))
        r = evolve_native(world, seed, TorchBatchModel, max_ticks=ev_ticks,
                          num_agents=num_agents, pop_cap=int(os.environ.get("SWA_POPCAP", "120")))
        print(f"EVOLVE-NATIVE-TORCH world={world} seed={seed} ticks={r['ticks']} "
              f"best_age={r['best_age']} births={r['births']} peak_pop={r['peak_pop']} "
              f"final_pop={r['final_pop']} extinct={r['extinct']}")
        if r["best_genome"] is not None:
            g = r["best_genome"]
            t_meds = measure_survival(world, seed, TorchBatchModel, g, k_eval, num_agents, max_ticks)
            l_meds = measure_survival(world, seed, MambaBatchModel, g, k_eval, num_agents, max_ticks)
            print(f"  champion NATIF-torch sous torch  : med={float(statistics.median(t_meds)):.1f} "
                  f"(vs transplant legacy sous torch ~33.0)")
            print(f"  champion NATIF-torch sous legacy : med={float(statistics.median(l_meds)):.1f} "
                  f"(vs legacy-natif sous legacy ~74.5)")
        return r

    if os.environ.get("SWA_MODE") == "arms":
        hof = os.environ.get("SWA_HOF", "data/hall_of_fame.pkl")
        genome = _load_champion(hof)
        r = compare_arms(world, seed, k_eval, num_agents, max_ticks, genome=genome)
        print(f"ARMS world={r['world']} legacy={r['legacy_median']:.1f} core={r['core_median']:.1f} "
              f"torch={r['torch_median']:.1f}")
        oc, rp = r["organs_contribution"], r["rule_at_parity"]
        print(f"  ORGANES (legacy_full - core) : median_diff={oc['median_diff']:+.2f} "
              f"verdict={oc['verdict']} (fav={oc['n_gradient_favorable']}/{oc['n']}, p={oc['sign_p']:.4f})")
        print(f"  REGLE @parite (torch - core) : median_diff={rp['median_diff']:+.2f} "
              f"verdict={rp['verdict']} (fav={rp['n_gradient_favorable']}/{rp['n']}, p={rp['sign_p']:.4f})")
        return r

    res = compare_backends(world, seed, k_eval, num_agents, max_ticks)
    print(f"VERDICT={res['verdict']} world={res['world']} median_diff={res['median_diff']:+.2f} "
          f"(grad_fav={res['n_gradient_favorable']}/{res['n']}, sign_p={res['sign_p']:.4f}) "
          f"| legacy={res['legacy_median']:.1f} torch={res['torch_median']:.1f}")
    for r in res["per_seed"]:
        print(f"  seed_i={r['i']} legacy={r['legacy']:.1f} torch={r['torch']:.1f} diff={r['diff']:+.1f}")
    return res


if __name__ == "__main__":
    main()
