"""tools/craft_retention_probe.py — Rétention du craft (P1 backlog cartographe).

EDR 127 : le craft est ATTEINT en évolution (élite tier-2 de l'archive QD) mais NON RE-CRAFTÉ en
cohorte fixe (frac_craft ~0.011). Question ouverte du backlog : quel LEVIER fait re-crafter une
cohorte fixe (mémoire de recette ? incitation ?).

On source les crafteurs EXACTEMENT comme EDR 127 (`_evolve_qd_champions`, archive MAP-Elites) puis on
mesure, sur COHORTE FIXE (benchmark_mode, mêmes génomes rejoués), le craft sous 4 conditions :
  - baseline           : aucun levier (reproduit EDR 127, frac attendu ~0)
  - incitation_flat    : récompense craft PERMANENTE (scaffold_craft on, scaffold_eras=0 -> anneal 1.0)
  - incitation_recraft : bonus d'énergie CIBLÉ quand `spears_crafted` augmente (récompense le RE-craft)
  - memoire_recette    : flag « déjà crafté » injecté dans `explicit_memory` après le 1er craft

Métriques par agent : frac_craft (>=1), frac_recraft (>=2, = re-craft stable), total_spears.

BORNAGE MÉCANIQUE (axe d'interprétation) : en cohorte fixe le GÉNOME est figé et il n'y a pas
d'évolution intra-ère. Les leviers n'agissent donc que via l'OBSERVATION (énergie/état perçus, canal
mémoire injecté), pas par apprentissage. Si AUCUN levier ne restaure le craft -> le verrou de rétention
est dans la POLITIQUE FIGÉE (substrat), ce qui NUANCE l'« pas substrat » d'EDR 127. Le levier
`memoire_recette` est le plus borné : `explicit_memory` est un canal que l'agent évolué n'a PAS appris
à lire comme « flag craft » -> un null n'y réfute que « un flag brut dans un canal non interprété n'aide
pas », pas « la mémoire de recette n'aiderait jamais ».

Tooling pur (aucun src/ modifié). Usage : python -m tools.craft_retention_probe
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
from src.curriculum.competence import _frac_reaching
from src.graph_rag.async_logger import logger as async_logger
from tools.map_elites_compare import _make_cfg, PRESERVE_DIMS
from tools.qd_tier_rescue import _evolve_qd_champions

CONDITIONS = ("baseline", "incitation_flat", "incitation_recraft", "memoire_recette")
FLAT_REWARD = float(os.environ.get("CR_FLAT", "5.0"))        # scaffold_craft permanent
RECRAFT_BONUS = float(os.environ.get("CR_RECRAFT_BONUS", "8.0"))  # énergie / re-craft détecté
MEM_SLOT = int(os.environ.get("CR_MEM_SLOT", "0"))           # slot explicit_memory à flagger


def _measure_retention(cfg, genomes, max_ticks, condition):
    """Cohorte fixe (benchmark_mode) sous un LEVIER. Mirror de competence_profile._measure_profile
    + hook par-tick selon `condition`. Renvoie les stats par agent {spears_crafted, age}."""
    env = Biosphere3D(cfg)
    env.benchmark_mode = True
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
        env.memory_retriever.clear()
    if condition == "incitation_flat":
        # récompense de craft permanente : anneal(era, eras<=0) == 1.0 -> scaffold jamais annelé
        env.scaffold_craft = FLAT_REWARD
        env.scaffold_eras = 0
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g, preserve_dims=PRESERVE_DIMS)
        env.add_agent(a, energy=80.0)
    env.current_era = 1

    prev = {id(ag): int(ag.get("spears_crafted", 0)) for ag in env.agents}
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        if condition == "incitation_recraft":
            for ag in env.agents:
                cur = int(ag.get("spears_crafted", 0))
                if cur > prev.get(id(ag), 0):
                    ag["energy"] = ag.get("energy", 0.0) + RECRAFT_BONUS
                prev[id(ag)] = cur
        elif condition == "memoire_recette":
            for ag in env.agents:
                if ag.get("spears_crafted", 0) >= 1:
                    mdl = ag.get("model", None)
                    mem = getattr(mdl, "explicit_memory", None)
                    if mem is not None and len(mem) > MEM_SLOT:
                        mem[MEM_SLOT] = 1.0
        t += 1

    pool = env.agents + list(getattr(env, "dead_agents", []))
    return [{"spears_crafted": int(ag.get("spears_crafted", 0)), "age": ag.get("age", 0)}
            for ag in pool]


def _craft_elites(archive):
    """Génomes des élites de l'archive QD qui ONT crafté en évolution (spears_crafted>0),
    tous size_bins/tiers confondus. C'est le crafteur d'EDR 127 sourcé DIRECTEMENT (≠ sample(5)
    uniforme qui le rate presque toujours). Vide -> le crafteur n'a pas émergé ce seed."""
    return [g for (_score, g, st) in archive.elites() if st.get("spears_crafted", 0) > 0]


def _metrics(stats):
    """frac_craft (>=1), frac_recraft (>=2 = re-craft stable), total_spears, n."""
    return {"frac_craft": round(_frac_reaching(stats, "spears_crafted", 1), 4),
            "frac_recraft": round(_frac_reaching(stats, "spears_crafted", 2), 4),
            "total_spears": int(sum(s["spears_crafted"] for s in stats)),
            "n": len(stats)}


def _verdict_retention(base, best_cond, best_metrics):
    """RETENTION_LEVER si un levier lève frac_craft de >=0.10 au-dessus du baseline ET le sort du
    plancher (>=0.10) ; POLICY_LOCKED si aucun levier ne bouge le craft (verrou = politique figée
    = substrat, nuance EDR 127) ; sinon PARTIEL."""
    d = best_metrics["frac_craft"] - base["frac_craft"]
    if d >= 0.10 and best_metrics["frac_craft"] >= 0.10:
        return f"RETENTION_LEVER ({best_cond})"
    if d < 0.03:
        return "POLICY_LOCKED"
    return "PARTIEL"


def _report(h, per_seed, R, _return):
    """Table (1 ligne/seed × condition) + moyenne par condition + verdict."""
    # Seeds où le crafteur a émergé (sinon rien à mesurer : n'entrent pas dans la moyenne)
    seeds_ok = [p for p in per_seed if p.get("n_craft_elites", 0) > 0]
    pool = seeds_ok if seeds_ok else per_seed
    means = {c: {k: float(np.mean([p[c][k] for p in pool]))
                 for k in ("frac_craft", "frac_recraft", "total_spears")}
             for c in CONDITIONS}
    base = means["baseline"]
    non_base = [c for c in CONDITIONS if c != "baseline"]
    best_cond = max(non_base, key=lambda c: means[c]["frac_craft"])
    if not seeds_ok:
        verdict = "INCONCLUSIF (aucun crafteur émergé — augmenter eras/seeds)"
    else:
        verdict = _verdict_retention(base, best_cond, means[best_cond])

    print("\n=== Rétention du craft (cohorte fixe, crafteur tier-2 QD sourcé direct, EDR 127) ===")
    print(f"  seeds avec crafteur émergé = {len(seeds_ok)}/{len(per_seed)} "
          f"(n_craft_elites: {[p.get('n_craft_elites', 0) for p in per_seed]})")
    print("  cond               | frac_craft frac_recraft tot_spears")
    for c in CONDITIONS:
        m = means[c]
        print(f"  {c:18s} |   {m['frac_craft']:6.3f}     {m['frac_recraft']:6.3f}    {m['total_spears']:6.1f}")
    print(f"  d(frac_craft) meilleur levier vs baseline = {means[best_cond]['frac_craft'] - base['frac_craft']:+.3f} ({best_cond})")
    print("=== VERDICT (levier de rétention ?) ===")
    print(f"  -> {verdict}")
    h.save({"R": R, "verdict": verdict, "best_cond": best_cond, "means": means, "per_seed": per_seed})
    if _return:
        return {"verdict": verdict, "best_cond": best_cond, "means": means, "per_seed": per_seed, "R": R}


def main_craft_retention(R=3, eras=12, num_agents=30, max_ticks=400, seed=1260, _return=False):
    """Pour chaque seed : évolue les crafteurs QD (EDR 127), puis mesure le craft sur cohorte fixe
    sous chaque condition (mêmes champions réutilisés). Agrège R seeds, verdict levier de rétention."""
    base = seed
    async_logger.start()
    try:
        per_seed = []
        for r in range(R):
            s = base + r
            _sample, archive = _evolve_qd_champions(s, eras=eras, num_agents=num_agents,
                                                    max_ticks=max_ticks)
            elites = _craft_elites(archive)   # crafteur sourcé DIRECTEMENT (tier-2, EDR 127)
            reps = (elites * (num_agents // max(len(elites), 1) + 1))[:num_agents] if elites else []
            row = {"seed": int(s), "n_craft_elites": len(elites)}
            for c in CONDITIONS:
                stats = _measure_retention(_make_cfg(), reps, max_ticks, c)
                row[c] = _metrics(stats)
            per_seed.append(row)
    finally:
        async_logger.stop()
    h = Harness(seed=base, name="craft_retention_probe", with_db=False, config=WorldConfig())
    return _report(h, per_seed, R, _return)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main_craft_retention(
        R=int(os.environ.get("CR_R", "3")),
        eras=int(os.environ.get("CR_ERAS", "12")),
        num_agents=int(os.environ.get("CR_AGENTS", "30")),
        max_ticks=int(os.environ.get("CR_TICKS", "400")),
        seed=int(os.environ.get("CR_SEED", "1260")),
    )
