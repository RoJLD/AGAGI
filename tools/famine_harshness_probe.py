"""Sonde de DURETÉ famine (durcir-la-famine, EDR-157). Calibre le régime où le buffer d'énergie naturel
ÉCHOUE mais où une réserve suffirait — c.-à-d. où le monde EXIGE le stockage (corrige le « redondant »
d'EDR-155, valable seulement à famine courte). Compare 3 conditions sur un génome donné :
  - buffer seul  : cache OFF (aucun stockage possible)     -> survie sur le tank d'énergie uniquement
  - réel         : cache ON  (banking auto si energy>90)    -> ce que la politique exploite vraiment
  - oracle       : cache ON + réserve pré-remplie injectée  -> borne haute du bénéfice du stockage
Si oracle >> buffer (ratio >= min_ratio), le stockage est LOAD-BEARING -> régime cible pour ré-évoluer."""
import os
import sys
import json
import statistics
from typing import Dict, List

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.agents.mamba_agent import MambaAgent
from src.worlds.world_famine import FamineWorld, RESERVE_CAP
from src.environments.config import WorldConfig
from src.seed_ai.harness import seed_at

SWEET_METAB = 0.25   # sweet spot énergie (EDR 085) — sans lui, plancher létal, régime non calibrable
SWEET_PAYOFF = 3.0


def classify_storage_regime(buffer_survival: float, oracle_survival: float,
                            min_ratio: float = 1.5) -> Dict:
    """PUR. Le stockage est-il load-bearing ? ratio = oracle / buffer. >= min_ratio -> STORAGE_REQUIRED
    (le buffer naturel ne suffit pas, une réserve sauverait) ; sinon STORAGE_REDUNDANT (buffer suffit,
    cas EDR-155 à famine courte). buffer=0 -> epsilon (pas de division par zéro)."""
    ratio = oracle_survival / max(buffer_survival, 1e-6)
    verdict = "STORAGE_REQUIRED" if ratio >= min_ratio else "STORAGE_REDUNDANT"
    return {"verdict": verdict, "ratio": ratio,
            "buffer_survival": buffer_survival, "oracle_survival": oracle_survival}


def _sweet() -> WorldConfig:
    c = WorldConfig()
    c.base_metabolism = SWEET_METAB
    c.forage_payoff = SWEET_PAYOFF
    return c


def measure_regime(genome, cache: bool, cyc_ab: int, cyc_fam: int, inject_reserve: float = 0.0,
                   seed: int = 42, n_eras: int = 3, n_agents: int = 12, max_ticks: int = 600) -> float:
    """Survie médiane (médiane de médianes par ère) d'une cohorte fixe de clones du génome, régime dur.
    inject_reserve>0 -> chaque agent démarre avec cette réserve (oracle-storer). Cohorte fixe (benchmark),
    nuit OFF, scaffolds OFF, memory_retriever neutralisé (repro + anti-contention)."""
    meds: List[float] = []
    for i in range(max(1, n_eras)):
        seed_at(seed, i)
        w = FamineWorld(_sweet())
        if hasattr(w, "memory_retriever"):
            w.memory_retriever.stop()
            w.memory_retriever.clear()
        w.benchmark_mode = True
        w.night_enabled = False
        w.current_era = 10_000
        w.cache_enabled = cache
        w.cycle_abundance, w.cycle_famine = cyc_ab, cyc_fam
        for _ in range(n_agents):
            a = MambaAgent()
            a.from_genome(genome)
            w.add_agent(a, energy=80.0)
            if inject_reserve > 0:
                w.agents[-1]["reserve"] = min(RESERVE_CAP, inject_reserve)
        t = 0
        while w.agents and t < max_ticks:
            w.step()
            t += 1
        ages = [int(a["age"]) for a in w.agents + list(getattr(w, "dead_agents", []))]
        meds.append(float(np.median(ages)) if ages else 0.0)
    return float(statistics.median(meds))


def run_harshness_sweep(genome, cycles_famine: List[int], cyc_ab: int = 30, reserve: float = 150.0,
                        min_ratio: float = 1.5, **kw) -> Dict:
    """Pour chaque cyc_fam : mesure buffer/réel/oracle -> classifie le régime. Renvoie la table + le
    plus petit cyc_fam où STORAGE_REQUIRED (le régime cible pour la ré-évolution)."""
    rows = []
    for cf in cycles_famine:
        buf = measure_regime(genome, False, cyc_ab, cf, 0.0, **kw)
        real = measure_regime(genome, True, cyc_ab, cf, 0.0, **kw)
        orc = measure_regime(genome, True, cyc_ab, cf, reserve, **kw)
        cls = classify_storage_regime(buf, orc, min_ratio)
        rows.append({"cycle_famine": cf, "buffer": buf, "real": real, "oracle": orc, **cls})
    required = [r["cycle_famine"] for r in rows if r["verdict"] == "STORAGE_REQUIRED"]
    return {"cyc_abundance": cyc_ab, "reserve": reserve, "min_ratio": min_ratio, "rows": rows,
            "smallest_required_cycle_famine": min(required) if required else None}


def main():
    import importlib
    import src.seed_ai.persistence as P
    hof = os.environ.get("HOF_PATH", "data/hall_of_fame_famine.pkl")
    os.environ["HOF_PATH"] = hof
    importlib.reload(P)
    genome = P.load_hall_of_fame()[1][0].genome
    cfs = [int(x) for x in os.environ.get("FHP_CYCLES_FAMINE", "40,120,300").split(",") if x.strip()]
    cyc_ab = int(os.environ.get("FHP_CYCLE_ABUNDANCE", "30"))
    r = run_harshness_sweep(genome, cfs, cyc_ab=cyc_ab, n_eras=int(os.environ.get("FHP_ERAS", "2")))
    print(f"{'cyc_fam':>8} {'buffer':>8} {'real':>8} {'oracle':>8} {'ratio':>6} verdict")
    for row in r["rows"]:
        print(f"{row['cycle_famine']:>8} {row['buffer']:>8.1f} {row['real']:>8.1f} {row['oracle']:>8.1f} "
              f"{row['ratio']:>6.2f} {row['verdict']}")
    print("smallest_required_cycle_famine =", r["smallest_required_cycle_famine"])
    print("FHP_JSON", json.dumps(r))
    return r


if __name__ == "__main__":
    main()
