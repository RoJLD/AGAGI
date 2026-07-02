"""Probe VERTICALITÉ : un champion évolué en 2D exploite-t-il l'affordance verticale quand
on active use_3d ? Compare 2 bras (2D/3D) sur une cohorte fixe de clones d'un champion HoF.
Métrique de DÉCISION = utilisation de Z dans le bras 3D (z-range + fraction Up/Down chez les
survivants) ; survie = interprétatif (le cube 3D est plus creux). Détecteur de POSITIF bon
marché avant tout investissement de visualisation 3D. Voir spec 2026-06-30-vertical-world-probe."""
import os
import sys
import json
import statistics
from typing import Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.agents.mamba_agent import MambaAgent
from src.worlds.world_1_stoneage import Biosphere3D
from src.environments.config import WorldConfig
from src.seed_ai.harness import seed_at


def classify_vertical_signal(z_range_3d: float, updown_frac_3d: float,
                             updown_floor: float = 0.25, margin: float = 1.2,
                             z_eps: float = 0.5,
                             survival_2d: Optional[float] = None,
                             survival_3d: Optional[float] = None) -> Dict:
    """PUR. Verdict d'utilisation de Z dans le bras 3D.
    Z_UTILISE si z_range_3d > z_eps ET updown_frac_3d > updown_floor*margin ; sinon Z_INERTE.
    updown_floor = 2/8 (Up+Down sur 8 actions argmax) ; margin = marge au-dessus du hasard ;
    z_eps = au moins une transition de couche. survival_ratio interprétatif (epsilon anti /0)."""
    threshold = updown_floor * margin
    z_used = z_range_3d > z_eps
    updown_used = updown_frac_3d > threshold
    verdict = "Z_UTILISE" if (z_used and updown_used) else "Z_INERTE"
    survival_ratio: Optional[float] = None
    if survival_2d is not None and survival_3d is not None:
        survival_ratio = survival_3d / max(survival_2d, 1e-6)
    return {"verdict": verdict, "z_range_3d": z_range_3d, "updown_frac_3d": updown_frac_3d,
            "threshold": threshold, "survival_ratio": survival_ratio}


def measure_arm(genome, use_3d: bool, seed: int, n_eras: int = 2,
                n_agents: int = 12, max_ticks: int = 600) -> Dict:
    """Fait tourner une cohorte fixe de clones du génome dans Biosphere3D (2D ou 3D).
    Instrumente l'usage de Z depuis la boucle (zéro modif src/). Retourne survie médiane
    (médiane de médianes par ère) + z_range/updown_frac moyens chez les survivants (steps >=
    médiane des steps de l'ère)."""
    surv_per_era: List[float] = []
    z_ranges: List[float] = []
    updown_fracs: List[float] = []
    for era in range(max(1, n_eras)):
        seed_at(seed, era)
        cfg = WorldConfig()
        cfg.use_3d = use_3d
        w = Biosphere3D(cfg)
        if hasattr(w, "memory_retriever") and w.memory_retriever is not None:
            w.memory_retriever.stop()
            w.memory_retriever.clear()
        w.benchmark_mode = True
        for _ in range(n_agents):
            a = MambaAgent()
            a.from_genome(genome)
            w.add_agent(a, energy=80.0)
        tracker: Dict = {}  # id -> {z_min,z_max,ups,downs,steps}
        t = 0
        while w.agents and t < max_ticks:
            w.step()
            for a in w.agents:
                aid = a["id"]
                z = int(a.get("z", 0))
                la = int(a.get("last_action", -1))
                tr = tracker.setdefault(aid, {"z_min": z, "z_max": z, "ups": 0, "downs": 0, "steps": 0})
                tr["z_min"] = min(tr["z_min"], z)
                tr["z_max"] = max(tr["z_max"], z)
                if la == 4:
                    tr["ups"] += 1
                elif la == 5:
                    tr["downs"] += 1
                tr["steps"] += 1
            t += 1
        ages = [int(a["age"]) for a in w.agents + list(getattr(w, "dead_agents", []))]
        surv_per_era.append(float(np.median(ages)) if ages else 0.0)
        # Survivors = agents ayant vécu >= médiane des steps de l'ère (proxy survie).
        steps_list = [tr["steps"] for tr in tracker.values() if tr["steps"] > 0]
        if steps_list:
            med_steps = float(np.median(steps_list))
            for tr in tracker.values():
                if tr["steps"] >= med_steps and tr["steps"] > 0:
                    z_ranges.append(float(tr["z_max"] - tr["z_min"]))
                    updown_fracs.append((tr["ups"] + tr["downs"]) / tr["steps"])
    return {
        "survival": float(statistics.median(surv_per_era)) if surv_per_era else 0.0,
        "z_range": float(np.mean(z_ranges)) if z_ranges else 0.0,
        "updown_frac": float(np.mean(updown_fracs)) if updown_fracs else 0.0,
    }


def run_probe(genome, seeds: List[int], n_eras: int = 2, n_agents: int = 12,
              max_ticks: int = 600) -> Dict:
    """2 bras (2D/3D) sur K seeds appariés. Agrège (médiane survie, moyenne z-usage) et classifie."""
    a2d = [measure_arm(genome, False, s, n_eras, n_agents, max_ticks) for s in seeds]
    a3d = [measure_arm(genome, True, s, n_eras, n_agents, max_ticks) for s in seeds]
    surv_2d = float(statistics.median([r["survival"] for r in a2d]))
    surv_3d = float(statistics.median([r["survival"] for r in a3d]))
    z_range_3d = float(np.mean([r["z_range"] for r in a3d]))
    updown_frac_3d = float(np.mean([r["updown_frac"] for r in a3d]))
    verdict = classify_vertical_signal(z_range_3d, updown_frac_3d,
                                       survival_2d=surv_2d, survival_3d=surv_3d)
    return {"seeds": list(seeds), "arm_2d": a2d, "arm_3d": a3d,
            "survival_2d": surv_2d, "survival_3d": surv_3d, **verdict}


def main():
    import importlib
    import src.seed_ai.persistence as P
    hof = os.environ.get("HOF_PATH", "data/hall_of_fame.pkl")
    os.environ["HOF_PATH"] = hof
    importlib.reload(P)
    entries = P.load_hall_of_fame()[1]
    if not entries:
        print(f"ERREUR: Hall of Fame vide/absent à HOF_PATH={hof}. "
              f"Pointe HOF_PATH sur un HoF stoneage évolué.")
        return None
    genome = entries[0].genome
    seeds = [int(x) for x in os.environ.get("VWP_SEEDS", "42,43,44,45,46").split(",") if x.strip()]
    n_eras = int(os.environ.get("VWP_ERAS", "2"))
    n_agents = int(os.environ.get("VWP_AGENTS", "12"))
    max_ticks = int(os.environ.get("VWP_TICKS", "600"))
    r = run_probe(genome, seeds, n_eras=n_eras, n_agents=n_agents, max_ticks=max_ticks)
    print(f"seeds={r['seeds']}")
    print(f"survie   2D={r['survival_2d']:.1f}  3D={r['survival_3d']:.1f}  "
          f"ratio={r['survival_ratio']:.2f}" if r['survival_ratio'] is not None else "")
    print(f"z_range_3d={r['z_range_3d']:.2f}  updown_frac_3d={r['updown_frac_3d']:.3f}  "
          f"seuil={r['threshold']:.3f}")
    print(f"VERDICT: {r['verdict']}")
    print("VWP_JSON", json.dumps(r))
    return r


if __name__ == "__main__":
    main()
