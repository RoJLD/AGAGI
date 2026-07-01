"""Transfert ZÉRO-SHOT cross-world (north-star G1). Un champion évolué dans le monde A, lâché TEL QUEL
(sans ré-évolution) dans le monde B jamais vu, survit-il mieux que tabula-rasa, à budget d'évaluation
égal ? KPI `transfer_ratio` = survie(champ A dans B) / survie(tabula dans B), appariée par seed d'éval,
test de signe. Distinct d'EDR-116 (transfert DÉVELOPPEMENTAL à compute égal : ré-évolution sur la cible).

Spec du KPI : SDR-G1. Réutilise la primitive de mesure cohorte-fixe (s2_demand.run_condition) mais au
SWEET-SPOT métabolique (EDR 085) — sans lui, la survie est au plancher létal, insensible au monde ET au
génome, et tout ratio vaut ~1 par artefact (le monde ne pèse plus sur la survie)."""
import os
import sys
import json
import statistics
from typing import List, Dict, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.agents.mamba_agent import MambaAgent
from src.environments.config import WorldConfig
from src.seed_ai.harness import seed_at
import src.seed_ai.persistence as persistence
from tools.curriculum_transfer import compute_transfer_verdict
from tools.s2_demand import WORLDS

# Sweet spot énergie (EDR 085) : survie ×4, gradient champion/tabula ~4-5×. Sans lui : plancher létal.
SWEET_METAB = 0.25
SWEET_PAYOFF = 3.0


def paired_ratios(champ_meds: List[float], tabula_meds: List[float]) -> List[float]:
    """Ratios de transfert appariés par index (seed d'éval) : champ / tabula, tronqué à la longueur
    commune. PUR (testable sans biosphère). tabula=0 -> plancher epsilon (pas de division par zéro)."""
    n = min(len(champ_meds), len(tabula_meds))
    return [champ_meds[i] / max(tabula_meds[i], 1e-6) for i in range(n)]


def _sweet_config() -> WorldConfig:
    cfg = WorldConfig()
    cfg.base_metabolism = SWEET_METAB
    cfg.forage_payoff = SWEET_PAYOFF
    return cfg


def measure_in_world(world_key: str, genome, seed: int, k_eval: int = 12,
                     num_agents: int = 12, max_ticks: int = 300) -> List[float]:
    """Survie médiane d'une cohorte fixe dans le monde `world_key`, sur k_eval seeds d'éval appariables
    (seed base + i). genome=None -> tabula-rasa (MambaAgent init aléatoire). Cohorte fixe (benchmark),
    nuit OFF, scaffolds OFF (régime S2/EDR-118), memory_retriever neutralisé (repro + anti-contention).
    Retourne une médiane de survie PAR seed d'éval (unité d'appariement)."""
    world_cls = WORLDS[world_key]
    meds: List[float] = []
    for i in range(max(1, k_eval)):
        seed_at(seed, i)
        env = world_cls(_sweet_config())
        env.benchmark_mode = True        # cohorte fixe : pas de repro/mutation/HGT (on mesure LE génome)
        env.night_enabled = False        # régime cohérent EDR-118 (isole le monde)
        env.current_era = 10_000         # scaffolds annelés -> 0
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
            env.memory_retriever.clear()
        for _ in range(num_agents):
            a = MambaAgent()
            if genome is not None:
                a.from_genome(genome)    # dims hétérogènes gérées par padding dynamique du batch model
            env.add_agent(a, energy=80.0)
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
        ages = [int(a["age"]) for a in env.agents + list(getattr(env, "dead_agents", []))]
        meds.append(float(np.median(ages)) if ages else 0.0)
    return meds


def _load_genome(hof_path: str):
    """Génome du #1 d'un HoF donné (via override HOF_PATH, seam EDR-126)."""
    import importlib
    os.environ["HOF_PATH"] = hof_path
    importlib.reload(persistence)
    _v, entries = persistence.load_hall_of_fame()
    if not entries:
        raise RuntimeError(f"HoF vide : {hof_path}")
    return entries[0].genome


def run_direction(source_label: str, source_hof: str, target_world: str,
                  seed: int = 42, k_eval: int = 12, num_agents: int = 12,
                  max_ticks: int = 300, tabula_meds: Optional[List[float]] = None) -> Dict:
    """Un bras de transfert : champion de `source_hof` (évolué dans source_label) lâché dans
    `target_world`, vs tabula-rasa dans le même monde (appariés seed à seed). tabula_meds réutilisable
    (indépendant du champion source) pour ne pas re-mesurer la baseline à chaque champion."""
    champ = _load_genome(source_hof)
    champ_meds = measure_in_world(target_world, champ, seed, k_eval, num_agents, max_ticks)
    if tabula_meds is None:
        tabula_meds = measure_in_world(target_world, None, seed, k_eval, num_agents, max_ticks)
    ratios = paired_ratios(champ_meds, tabula_meds)
    verdict = compute_transfer_verdict(ratios)
    return {**verdict, "source": source_label, "target": target_world,
            "champ_median": float(statistics.median(champ_meds)) if champ_meds else 0.0,
            "tabula_median": float(statistics.median(tabula_meds)) if tabula_meds else 0.0,
            "champ_meds": champ_meds, "tabula_meds": tabula_meds, "ratios": ratios,
            "_tabula_meds": tabula_meds}


def main():
    seed = int(os.environ.get("CWT_SEED", "42"))
    k_eval = int(os.environ.get("CWT_KEVAL", "12"))
    num_agents = int(os.environ.get("CWT_NUM_AGENTS", "12"))
    max_ticks = int(os.environ.get("CWT_MAX_TICKS", "300"))
    famine_hofs = os.environ.get("CWT_FAMINE_HOFS",
                                 "data/hall_of_fame_famine.pkl,data/hall_of_fame_famine_s43.pkl,"
                                 "data/hall_of_fame_famine_s44.pkl").split(",")
    stone_hof = os.environ.get("CWT_STONE_HOF", "data/hall_of_fame.pkl")

    results = []
    # famine -> stoneage : 3 champions famine, baseline tabula-stoneage mesurée une seule fois
    tabula_stone = measure_in_world("stoneage", None, seed, k_eval, num_agents, max_ticks)
    for i, hof in enumerate(famine_hofs):
        hof = hof.strip()
        if not hof:
            continue
        r = run_direction(f"famine[{os.path.basename(hof)}]", hof, "stoneage", seed, k_eval,
                          num_agents, max_ticks, tabula_meds=tabula_stone)
        results.append(r)
    # stoneage -> famine : champion stoneage global
    results.append(run_direction("stoneage", stone_hof, "famine", seed, k_eval,
                                 num_agents, max_ticks))

    for r in results:
        r.pop("_tabula_meds", None)
        print(f"{r['source']:32s} -> {r['target']:9s} | {r['verdict']:10s} "
              f"| ratio_med={r['median_ratio']:.2f} (n_fav={r['n_favorable']}/{r['n']}, "
              f"sign_p={r['sign_p']:.4f}) | champ={r['champ_median']:.1f} tabula={r['tabula_median']:.1f}")
    print("CWT_JSON", json.dumps([{k: v for k, v in r.items()
                                   if k not in ("champ_meds", "tabula_meds", "ratios")} for r in results]))
    return results


if __name__ == "__main__":
    main()
