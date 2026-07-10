"""tools/agricultural_demand_probe.py — World 2 (agricole) EXIGE-t-il un type cognitif DISTINCT, ou est-ce
du stoneage deguise ? (instrument de demande, analogue au mur du craft EDR 125/CRAFT-001).

World 2 offre une chaine agricole : l'agent ramasse une Seed, la LACHE (action DROP=8) -> Planted_Seed ->
(printemps) Plant -> (ete/automne) Fruit (nourriture). + hiver rude (-0.2 energie/tick sauf pres d'un Fire).
C'est un type cognitif distinct de stoneage : PREVOYANCE SAISONNIERE / gratification differee.

Question : le champion (evolue en STONEAGE, sans agriculture) EXPLOITE-t-il cette chaine, ou reste-t-elle
inerte (comme le craft, atteint mais non retenu) ? Piege temporel : au regime dur (metab 1.0) les agents
meurent en ~20 ticks < 1 saison (50) -> demande INATTEIGNABLE (plancher). On NEUTRALISE la famine
(base_metabolism=0.0) pour donner tout le temps voulu -> si le champion ne plante TOUJOURS pas, verdict net.

Fait statique (world 3 industriel) : 18 lignes, sous-classe de Biosphere3D, `pollution` incrementee mais
JAMAIS lue -> world 3 = stoneage deguise (aucune demande). Verifie par assertion (cf. test).

Cle : Planted_Seed n'existe QUE si un agent a ramasse PUIS lache une Seed (world_2 `_apply_action` action 8)
-> max(Planted_Seed)>0 = PREUVE de comportement agricole. Tooling-only. Usage :
  python -m tools.agricultural_demand_probe
"""
import os

import numpy as np

from src.seed_ai.harness import Harness, seed_at
from tools.lethality_curriculum import _disable_kuzu
from tools.lewis_survival_sweep import _cfg
from tools.robust_eval import _load_champions
from src.worlds.world_2_agricultural import AgriculturalWorld

_SEASON_LEN = 50   # AgriculturalWorld.season_duration (defaut)
_ITEM_KEYS = ("Seed", "Planted_Seed", "Plant", "Fruit", "Fire", "Wood")


# ----------------------------------------------------------------------------- verdict (pur)
def agri_verdict(max_planted, max_fruit, planted_thresh=1):
    """La chaine agricole est-elle EXPLOITEE par le champion ?

    - max_planted : plus grand nombre de Planted_Seed vus (>0 => un agent a ramasse+lache une Seed).
    - max_fruit   : plus grand nombre de Fruit vus (>0 => la chaine atteint le PAYOFF).

    AGRICULTURE_COSMETIC : max_planted < seuil -> aucune plantation -> world 2 = stoneage + hiver.
    CHAIN_INCOMPLETE     : plantation mais aucun Fruit -> chaine amorcee, jamais recoltable.
    AGRICULTURE_ACTIVE   : Fruit produit -> la chaine s'exerce de bout en bout (n'implique pas
                           l'INTENTIONNALITE : voir bornage saisonnier).
    """
    if max_planted < planted_thresh:
        return "AGRICULTURE_COSMETIC"
    if max_fruit <= 0:
        return "CHAIN_INCOMPLETE"
    return "AGRICULTURE_ACTIVE"


def _season_of_tick(t):
    seasons = ("spring", "summer", "autumn", "winter")
    return seasons[((t - 1) // _SEASON_LEN) % 4]


# ----------------------------------------------------------------------------- run (impur)
def run_agricultural(genome, seed, num_agents=20, max_ticks=250, config=None):
    """Cohorte-champion dans AgriculturalWorld. Capture par tick : saison, comptes d'items, agents vivants."""
    from src.agents.mamba_agent import MambaAgent
    seed_at(seed, 0)
    env = AgriculturalWorld(config) if config is not None else AgriculturalWorld()
    env.benchmark_mode = True
    env.night_enabled = False
    env.current_era = 10_000
    for _ in range(num_agents):
        a = MambaAgent()
        if genome is not None:
            a.from_genome(genome)
        env.add_agent(a, energy=80.0)
    traj = []
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        t += 1
        c = {k: 0 for k in _ITEM_KEYS}
        for it in env.items:
            ty = it.get("type")
            if ty in c:
                c[ty] += 1
        traj.append({"t": t, "season": env.season, "n_agents": len(env.agents), **c})
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    return traj


def analyze(trajs):
    """Agrege les trajectoires : exploitation de la chaine + demande hivernale."""
    flat = [row for tr in trajs for row in tr]
    max_planted = max((r["Planted_Seed"] for r in flat), default=0)
    max_plant = max((r["Plant"] for r in flat), default=0)
    max_fruit = max((r["Fruit"] for r in flat), default=0)
    max_seed = max((r["Seed"] for r in flat), default=0)
    # demande hivernale : survie a travers le 1er hiver (ticks 151-200) vs debut d'hiver
    def winter_survival(tr):
        winters = [r for r in tr if r["season"] == "winter"]
        if not winters:
            return None, None
        n0, n1 = winters[0]["n_agents"], winters[-1]["n_agents"]
        fire = max((r["Fire"] for r in winters), default=0)
        return (n1 / n0 if n0 else None), fire
    ws = [winter_survival(tr) for tr in trajs]
    surv = [s for s, _ in ws if s is not None]
    fires = [f for _, f in ws if f is not None]
    verdict = agri_verdict(max_planted, max_fruit)
    return {"max_seed": max_seed, "max_planted": max_planted, "max_plant": max_plant,
            "max_fruit": max_fruit,
            "winter_survival": float(np.mean(surv)) if surv else float("nan"),
            "winter_fire_max": float(np.mean(fires)) if fires else float("nan"),
            "reached_winter": len(surv), "verdict": verdict}


def _report(res, n_seeds):
    print("\n=== World 2 agricole : la chaine agricole est-elle EXPLOITEE (ou cosmetique) ? ===")
    print(f"  seeds={n_seeds}  (base_metabolism=0.0 -> famine neutralisee, saisons atteignables)")
    print(f"  chaine  : max Seed={res['max_seed']}  Planted_Seed={res['max_planted']}  "
          f"Plant={res['max_plant']}  Fruit={res['max_fruit']}")
    print(f"  hiver   : survie 1er hiver={res['winter_survival']:.3f}  fire(max)={res['winter_fire_max']:.2f}  "
          f"(ont atteint l'hiver : {res['reached_winter']}/{n_seeds})")
    print("=== VERDICT ===")
    print(f"  -> {res['verdict']}")
    print("     (Planted_Seed>0 EXIGE qu'un agent ramasse+lache une Seed -> preuve de comportement agricole)")
    return res


def main(seed=1140, n_eval=5, num_agents=20, max_ticks=250, _return=False):
    with Harness(seed=seed, name="agricultural_demand", with_db=False) as h:
        _disable_kuzu()
        base = h.seed
        champ = _load_champions()[0]                        # deja un Genome (cf. robust_eval._load_champions)
        cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=False)
        trajs = [run_agricultural(champ, base + i, num_agents=num_agents,
                                  max_ticks=max_ticks, config=cfg) for i in range(n_eval)]
        res = analyze(trajs)
        h.save({"seed": base, "n_eval": n_eval, "max_ticks": max_ticks, **res})
        return _report(res, n_eval) if not _return else res


if __name__ == "__main__":
    main(seed=int(os.getenv("EXPERIMENT_SEED", "1140")),
         n_eval=int(os.getenv("AGRI_NEVAL", "5")),
         max_ticks=int(os.getenv("AGRI_TICKS", "250")))
