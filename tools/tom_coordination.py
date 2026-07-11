"""tools/tom_coordination.py — ToM comportementale : la chasse coop est-elle COORDONNEE ? (P4 audit memoire, #2).

Tranche le caveat #2 d'EDR 132 (decode latent = contexte partage vs modelisation). Mecanique (EDR 028) :
attaquer = etre sur la cellule d'une proie (world_1_stoneage:692) ; le mammouth (hp 100) meurt des degats
cumules du pack. Question : parmi les agents proches d'un mammouth FRAIS, la proba d'attaquer est-elle plus
haute quand d'AUTRES agents sont proches (recrutement) ou inchangee (convergence fortuite) ?

Tooling pur READ-ONLY (pas de src/ modifie ; competence_profile/map_elites_compare importes).
Usage : MEC_PRESERVE_DIMS=1 python -m tools.tom_coordination
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.harness import Harness
from src.agents.mamba_agent import MambaAgent
from src.worlds.world_1_stoneage import Biosphere3D
from src.graph_rag.async_logger import logger as async_logger
from tools.map_elites_compare import _make_cfg, PRESERVE_DIMS
from tools.competence_profile import _evolve_champions


def _manhattan(a, m):
    return abs(a["x"] - m["x"]) + abs(a["y"] - m["y"])


def _hunt_samples_from_state(agents, preys, mammoth_hp):
    """Pour chaque mammouth FRAIS (hp >= 0.5*mammoth_hp), pour chaque agent a distance Manhattan <= 2 :
    {attacking: dist==0, others_near: nb d'AUTRES agents a <= 2 du mammouth}."""
    samples = []
    thresh = 0.5 * mammoth_hp
    for m in preys:
        if m.get("type") != "Mammouth" or m.get("hp", 0.0) < thresh:
            continue
        near = [a for a in agents if _manhattan(a, m) <= 2]
        for a in near:
            samples.append({"attacking": _manhattan(a, m) == 0, "others_near": len(near) - 1})
    return samples


def _recruitment_signal(samples):
    """p_with = P(attaque | others_near>=1), p_alone = P(attaque | others_near==0), delta = with - alone."""
    with_ = [s for s in samples if s["others_near"] >= 1]
    alone = [s for s in samples if s["others_near"] == 0]

    def _rate(xs):
        return float(np.mean([1.0 if s["attacking"] else 0.0 for s in xs])) if xs else 0.0

    p_with, p_alone = _rate(with_), _rate(alone)
    return {"p_with": p_with, "p_alone": p_alone, "delta": p_with - p_alone,
            "n_with": len(with_), "n_alone": len(alone)}


def _verdict_coordination(sig):
    """INDETERMINE si trop peu d'obs ; COORDINATED si delta >= 0.10 (recrutement) ; sinon INDEPENDENT."""
    if sig["n_with"] < 20 or sig["n_alone"] < 20:
        return "INDETERMINE"
    if sig["delta"] >= 0.10:
        return "COORDINATED"
    return "INDEPENDENT"


def _collect_hunt_decisions(cfg, genomes, max_ticks=400):
    """Cohorte fixe (benchmark_mode + memory neutralisee AVANT boucle, lecons 114b/P0). A chaque tick,
    collecte les samples de chasse (mammouths frais, agents proches). Renvoie tous les samples."""
    env = Biosphere3D(cfg)
    env.benchmark_mode = True
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
        env.memory_retriever.clear()
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g, preserve_dims=PRESERVE_DIMS)
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    mammoth_hp = getattr(cfg, "mammoth_hp", 100.0)
    samples = []
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        samples += _hunt_samples_from_state(env.agents, env.preys, mammoth_hp)
        t += 1
    return samples


def _report_coordination(h, per_seed, R, _return):
    """Table ASCII (par seed : p_with, p_alone, delta, nW, nA) + moyenne + verdict (delta moyen, garde min n)."""
    delta = float(np.mean([p["delta"] for p in per_seed]))
    p_with = float(np.mean([p["p_with"] for p in per_seed]))
    p_alone = float(np.mean([p["p_alone"] for p in per_seed]))
    n_with = int(min(p["n_with"] for p in per_seed))
    n_alone = int(min(p["n_alone"] for p in per_seed))
    verdict = _verdict_coordination({"delta": delta, "n_with": n_with, "n_alone": n_alone})
    print("\n=== ToM comportementale : chasse coop coordonnee ? (cohorte fixe) ===")
    print("  seed | p_with p_alone  delta   nW    nA")
    for p in per_seed:
        print(f"  {p['seed']:4d} | {p['p_with']:.3f}  {p['p_alone']:.3f}  {p['delta']:+.3f} {p['n_with']:5d} {p['n_alone']:5d}")
    print(f"  MOYEN| {p_with:.3f}  {p_alone:.3f}  {delta:+.3f}")
    print("=== VERDICT (recrutement) ===")
    print(f"  -> {verdict}  (garde min nW={n_with} nA={n_alone})")
    h.save({"R": R, "verdict": verdict, "delta": delta, "p_with": p_with, "p_alone": p_alone,
            "n_with_min": n_with, "n_alone_min": n_alone, "per_seed": per_seed})
    if _return:
        return {"verdict": verdict, "delta": delta, "p_with": p_with, "p_alone": p_alone,
                "n_with_min": n_with, "n_alone_min": n_alone, "per_seed": per_seed, "R": R}


def main_tom_coordination(R=3, eras=12, num_agents=30, max_ticks=400, seed=1300, _return=False):
    """Par seed base+r : evolue des champions (coop par defaut), mesure les decisions de chasse sur cohorte
    fixe, agrege R seeds, verdict recrutement."""
    base = seed
    h = Harness(seed=base, name="tom_coordination", with_db=False, config=WorldConfig())
    async_logger.start()
    try:
        per_seed = []
        for r in range(R):
            s = base + r
            champs = _evolve_champions(s, eras=eras, num_agents=num_agents, max_ticks=max_ticks)
            reps = (champs * (num_agents // len(champs) + 1))[:num_agents] if champs else []
            samples = _collect_hunt_decisions(_make_cfg(), reps, max_ticks=max_ticks)
            per_seed.append({**_recruitment_signal(samples), "seed": int(s)})
    finally:
        async_logger.stop()
    return _report_coordination(h, per_seed, R, _return)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    main_tom_coordination()
