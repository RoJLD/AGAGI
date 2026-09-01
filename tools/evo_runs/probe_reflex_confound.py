"""CONTROLE MANQUANT : l'avantage de survie vient-il de la LECTURE ou de la DIAGONALE REFLEXE ?

Tous les controles positifs d'EVO-016/018 utilisent un lecteur cable AVEC diag=+10 (substrat sans
memoire). Les agents evolues n'ont pas ca. Le gain 9.0 -> 22.0 pourrait donc venir en partie de
l'absence de derive d'etat (classe E6) plutot que de la lecture. Le controle manquant : un NON-LECTEUR
AVEC reflexe.
"""
import statistics
import numpy as np
from tools.jobs.run import hold

with hold("kuzu", owner="evo021-confond", ttl_s=3600):
    import tools.evo_cognitive_objective as M
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.mutation import Genome
    from tools.lewis_world import _setup_lewis

    I, O, N = 59, 108, 172
    SIG = M.SIG_COLS[0]
    HAZARD = 15.0

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
                    a["_hz_hits"] = int(a.get("_hz_hits", 0)) + 1

    def geno(w, reflex):
        W = np.zeros((N, N), dtype=np.float32)
        if reflex:
            np.fill_diagonal(W, 10.0)
        if w:
            W[SIG, N - O + M.THROW_IDX] = float(w)
        return Genome(W, I, O)

    def run(g, seed, agents=24, ticks=200):
        np.random.seed(seed)
        env = HazardWorld(M._cfg())
        env.hazard = HAZARD; env.tasks = (1,); env.inject = True
        _setup_lewis(env, n_each=M.N_APEX)
        env.benchmark_mode = True; env.night_enabled = False; env.current_era = 10_000
        for _ in range(agents):
            a = MambaAgent(); a.from_genome(g); env.add_agent(a, energy=80.0)
        t = 0
        while env.agents and t < ticks:
            env.step(); t += 1
        pool = list(env.agents) + list(env.dead_agents)
        hits = sum(int(a.get("_hz_hits", 0)) for a in pool)
        tk = sum(int(a.get("_cog_ticks", 0)) for a in pool)
        return (statistics.median([a["age"] for a in pool] or [0]), hits / tk if tk else float("nan"))

    print(f"  {'genome':>28} | {'age med':>8} | {'taux erreur':>12}")
    res = {}
    for label, w, refl in (("non-lecteur SANS reflexe", 0.0, False),
                           ("non-lecteur AVEC reflexe", 0.0, True),
                           ("LECTEUR    AVEC reflexe", 3.0, True),
                           ("LECTEUR    SANS reflexe", 3.0, False)):
        rows = [run(geno(w, refl), 100 + s) for s in range(5)]
        age = statistics.median([r[0] for r in rows]); err = statistics.median([r[1] for r in rows])
        res[label.strip()] = age
        print(f"  {label:>28} | {age:>8.1f} | {err:>12.3f}")
    a = res["non-lecteur SANS reflexe"]; b = res["non-lecteur AVEC reflexe"]
    c = res["LECTEUR    AVEC reflexe"]
    print(f"\n  part du REFLEXE seul : {b - a:+.1f} ans | part de la LECTURE (a reflexe egal) : {c - b:+.1f} ans")
    tot = c - a
    if tot > 0:
        print(f"  -> le reflexe explique {100*(b-a)/tot:.0f} % de l'ecart total, la lecture {100*(c-b)/tot:.0f} %")
