"""EVO-022 -- preserver le caractere temporel d'un chemin lors d'une insertion leve-t-il le verrou ?

EVO-021 : `add_node` DETRUIT un lecteur cable 6 fois sur 10 en une insertion, parce qu'il insere un noeud
a diagonale NULLE (delta=0.5, noeud a MEMOIRE) au milieu d'un chemin reactif -> derive (E6) -> signal noye.
Les six leviers refutes de l'arc attaquaient tous la DECOUVERTE ; aucun n'a touche la FRAGILITE.

Levier : le noeud INSERE herite de la diagonale de sa DESTINATION. Purement structurel, aucune
connaissance de la tache. Patch LOCAL -- src/seed_ai/mutation.py n'est JAMAIS modifie.

Regle scellee : docs/preregistrations/EVO-022.json (lecture CONTINUE, Fisher calcule par ce script).
Plafond de cout DETERMINISTE (budget en agent-ticks, E13) -- surtout PAS budget_s.

    PYTHONPATH=. python -u tools/evo_runs/evo022_run.py
"""
import statistics
from math import comb

import numpy as np
from tools.jobs.run import hold

BUDGET_TICKS = 60_000       # DETERMINISTE : meme seed -> meme troncature, partout
HAZARD = 15.0
N_SEEDS = 12

with hold("kuzu", owner="evo022-inherit-diag", ttl_s=14400):
    from tools.preregister import verify
    import tools.evo_cognitive_objective as M
    import src.seed_ai.mutation as MUT
    from src.seed_ai.mutation import MutationConfig, Genome, apply_mutations
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.persistence import calculate_life_score
    from tools.lewis_world import _setup_lewis

    rule = verify("EVO-022")
    print("regle SCELLEE verifiee |", rule["dv_primaire"], "\n")

    _orig_add_node = MUT.add_node

    def inherit_add_node(genome, config):
        """Le noeud INSERE herite de la diagonale de sa DESTINATION -> le chemin garde son caractere."""
        W = genome.W
        nzi, nzj = np.nonzero(W)
        if len(nzi) == 0:
            return
        idx = np.random.randint(len(nzi))
        i, j = int(nzi[idx]), int(nzj[idx])
        diag_dst = float(W[j, j])                 # <-- la SEULE difference avec l'original
        old_w = float(W[i, j])
        W[i, j] = 0.0
        new_W = np.insert(W, j, 0, axis=0)
        new_W = np.insert(new_W, j, 0, axis=1)
        new_W[i, j] = 1.0
        new_W[j, j + 1] = old_w
        new_W[j, j] = diag_dst                    # le noeud insere n'est plus un noeud a MEMOIRE
        genome.W = new_W

    # ---- PRE-VOL : controle de manipulation OBLIGATOIRE (clause scellee) ---------------------------
    I, O, N = 59, 108, 172
    SIG = M.SIG_COLS[0]

    def wired_reader():
        W = np.zeros((N, N), dtype=np.float32)
        np.fill_diagonal(W, 10.0)
        W[SIG, N - O + M.THROW_IDX] = 3.0
        return Genome(W, I, O)

    cfg = MutationConfig()
    print("  PRE-VOL -- UN add_node applique a un lecteur cable, 20 seeds :")
    prevol = {}
    for label, fn in (("origine", _orig_add_node), ("diag heritee", inherit_add_node)):
        lost = 0
        for s in range(20):
            np.random.seed(300 + s)
            g = wired_reader().clone()
            fn(g, cfg)
            sal = M.measure_decision_saliency(g, 700 + s, channel=SIG, out_idx=M.THROW_IDX,
                                              num_agents=6, ticks=20, tasks=(1,))
            lost += int(sal < 0.5)
        prevol[label] = lost
        print(f"    {label:>13} : lecteur DETRUIT {lost}/20")
    if prevol["diag heritee"] >= prevol["origine"]:
        print("\n  ARRET : le patch ne REDUIT PAS la destruction -> le bras ne teste rien (clause scellee).")
        raise SystemExit(1)
    print(f"    -> destruction {prevol['origine']}/20 -> {prevol['diag heritee']}/20, le patch MORD\n")

    # ---- RUN ---------------------------------------------------------------------------------------
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

    def evolve(seed, eras=35, ticks=120, n=30):
        np.random.seed(seed)
        c = M._cfg()
        mc = MutationConfig()
        mc.add_node_rate = 0.4
        genomes = M._fresh_soup(n, c, 0.4)
        best, best_fit, spent = genomes[0].clone(), -1e18, 0
        for _ in range(eras):
            if spent > BUDGET_TICKS:
                return best, True
            env = HazardWorld(c)
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
            while env.agents and t < ticks:
                env.step()
                t += 1
                if len(env.agents) > M.MAX_AGENTS:
                    break
            pool = list(env.agents) + list(env.dead_agents)
            spent += sum(int(a.get("age", 0)) for a in pool)
            if not pool:
                break
            pool.sort(key=calculate_life_score, reverse=True)
            if calculate_life_score(pool[0]) > best_fit:
                best_fit = calculate_life_score(pool[0])
                best = pool[0]["model"].genome.clone()
            el = [a["model"].genome.clone() for a in pool[:7]]
            ch = []
            while len(ch) < n - len(el):
                ch.append(apply_mutations(el[np.random.randint(len(el))], mc))
            genomes = el + ch
        return best, False

    out = {}
    for label, fn in (("baseline", _orig_add_node), ("diag_heritee", inherit_add_node)):
        MUT.add_node = fn
        print(f"--- bras {label} ---")
        rows = []
        for s in range(N_SEEDS):
            g, ab = evolve(s)
            if ab:
                print(f"  seed {s:>2}: ABANDONNE (budget deterministe)")
                rows.append({"aborted": True})
                continue
            sal = M.measure_decision_saliency(g, 2000 + s, channel=SIG, out_idx=M.THROW_IDX, tasks=(1,))
            b = M.benchmark_cognitive(g, 1000 + s, tasks=(1,))
            rows.append({"seed": s, "sal": sal, "raw": b["raw"], "age": b["med_age"]})
            flag = "   <<< LECTEUR" if sal > 0.5 else ""
            print(f"  seed {s:>2}: sal={sal:.3f} raw={b['raw']:.3f} age={b['med_age']:.0f}{flag}")
        out[label] = [r for r in rows if not r.get("aborted")]
    MUT.add_node = _orig_add_node

    print("\n=== EVO-022 ===")
    print(f"{'bras':>13} | {'LECTEURS':>9} | {'sal max':>8} | {'raw med':>8} | {'age med':>8} | abandons")
    for label in ("baseline", "diag_heritee"):
        rr = out[label]
        nab = N_SEEDS - len(rr)
        if not rr:
            print(f"{label:>13} | tous abandonnes")
            continue
        rd = [r for r in rr if r["sal"] > 0.5]
        print(f"{label:>13} | {len(rd):>4}/{len(rr):<4} | {max(r['sal'] for r in rr):>8.3f} | "
              f"{statistics.median([r['raw'] for r in rr]):>8.3f} | "
              f"{statistics.median([r['age'] for r in rr]):>8.0f} | {nab}")

    a = sum(1 for r in out["diag_heritee"] if r["sal"] > 0.5)
    b_ = len(out["diag_heritee"]) - a
    c_ = sum(1 for r in out["baseline"] if r["sal"] > 0.5)
    d = len(out["baseline"]) - c_
    n_tot = a + b_ + c_ + d

    def pf(x1, x2, x3, x4):
        return comb(x1 + x2, x1) * comb(x3 + x4, x3) / comb(n_tot, x1 + x3)

    obs = pf(a, b_, c_, d)
    tot = a + c_
    p = 0.0
    for x in range(0, min(a + b_, tot) + 1):
        y = tot - x
        if 0 <= y <= c_ + d:
            pr = pf(x, a + b_ - x, y, c_ + d - y)
            if pr <= obs + 1e-12:
                p += pr
    print("")
    print(f"  Fisher exact bilateral diag_heritee({a}/{a+b_}) vs baseline({c_}/{c_+d}) : p = {p:.3f}")
    verdict = "FRAGILITE = composante REELLE du verrou" if p < 0.05 else "AUCUN effet demontre"
    statut = "effet" if p < 0.05 else "OBSERVATIONS ISOLEES, NON elevees"
    print(f"  -> {verdict} ; lecteurs bruts = {statut}")
    print("  PUISSANCE :", rule["puissance_declaree"])
