"""EVO-025 -- SMOKE DE DEBIT, pas une experience. Combien coute VRAIMENT une ere ?

D2 (backlog) demande un horizon ~21x plus long. Avant d'engager des heures, mesurer le cout d'une ere
et verifier deux choses que l'arithmetique ne dit pas :
  1. le cout par ere est-il CONSTANT, ou croit-il (la survie augmente -> les episodes s'allongent) ?
  2. les tirages s'accumulent-ils vraiment (la lignee survit-elle a horizon long) ?

⚠️ Ecrit EXPLICITEMENT, pas derive d'un runner precedent (registre E4 occ.4).
⚠️ Aucune conclusion scientifique ne sort d'ici -- c'est du dimensionnement.

    PYTHONPATH=. python -u tools/evo_runs/evo025_throughput_smoke.py
"""
import time

import numpy as np
from tools.jobs.run import hold

HAZARD = 15.0
ERAS = 60          # assez pour voir une TENDANCE, pas juste un transitoire
TICKS = 120
POP = 30
ELITE = 7

with hold("kuzu", owner="evo025-throughput-smoke", ttl_s=3600):
    import tools.evo_cognitive_objective as M
    from src.seed_ai.mutation import MutationConfig, apply_mutations
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.persistence import calculate_life_score
    from tools.lewis_world import _setup_lewis

    class HazardWorld(M.CognitiveSignalBiosphere):
        hazard = HAZARD

        def step(self):
            before = {id(a): (int(a.get("_cog_ticks", 0)), int(a.get("_cog_hits", 0)))
                      for a in self.agents}
            super().step()
            for a in self.agents:
                bt, bh = before.get(id(a), (0, 0))
                if int(a.get("_cog_ticks", 0)) - bt > 0 and int(a.get("_cog_hits", 0)) - bh == 0:
                    a["energy"] -= self.hazard

    np.random.seed(0)
    cfg = M._cfg()
    mc = MutationConfig()
    genomes = M._fresh_soup(POP, cfg, 0.4)

    print(f"  ere | s/ere | ticks-agent | tirages cumules | survivants | N med")
    t_all = time.time()
    draws = 0
    per_era = []
    for era in range(ERAS):
        t0 = time.time()
        env = HazardWorld(cfg)
        env.hazard = HAZARD
        env.tasks = (1,)
        env.inject = True
        _setup_lewis(env, n_each=M.N_APEX)
        env.current_era = 1
        for g in genomes:
            a = MambaAgent()
            a.from_genome(g)
            env.add_agent(a, energy=80.0)
        t = 0
        while env.agents and t < TICKS:
            env.step()
            t += 1
            if len(env.agents) > M.MAX_AGENTS:
                break
        pool = list(env.agents) + list(env.dead_agents)
        ticks_agent = sum(int(a.get("age", 0)) for a in pool)
        if not pool:
            print(f"  ARRET ere {era}: population ETEINTE -> l'horizon long n'accumule PAS de tirages")
            break
        pool.sort(key=calculate_life_score, reverse=True)
        el = [a["model"].genome.clone() for a in pool[:ELITE]]
        ch = []
        while len(ch) < POP - len(el):
            ch.append(apply_mutations(el[np.random.randint(len(el))], mc))
            draws += 1
        genomes = el + ch
        dt = time.time() - t0
        per_era.append(dt)
        if era % 6 == 0 or era == ERAS - 1:
            nmed = int(np.median([g.num_nodes for g in genomes]))
            print(f"  {era:>4} | {dt:>5.2f} | {ticks_agent:>11} | {draws:>15} | "
                  f"{len(env.agents):>10} | {nmed:>5}")

    total = time.time() - t_all
    if per_era:
        n = len(per_era)
        prem, dern = np.mean(per_era[: n // 3]), np.mean(per_era[-n // 3:])
        print(f"\n  {n} eres en {total/60:.1f} min | moyenne {np.mean(per_era):.2f} s/ere")
        print(f"  DERIVE du cout : premier tiers {prem:.2f} s/ere -> dernier tiers {dern:.2f} s/ere "
              f"({dern/max(prem,1e-9):.2f}x)")
        print(f"  tirages : {draws} en {n} eres -> {draws/n:.1f}/ere")
        for mult, lbl in ((21, "D2 complet (~90 %)"), (7, "D2 reduit"), (3, "D2 minimal")):
            eras_needed = 35 * mult
            # borne HAUTE : on suppose que la derive se poursuit
            s_seed = eras_needed * dern
            print(f"  {lbl:>20} = {eras_needed:>4} eres -> {s_seed/60:>6.1f} min/seed "
                  f"| 8 seeds = {8*s_seed/3600:>5.2f} h")
