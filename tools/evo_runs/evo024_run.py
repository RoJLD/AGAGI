"""EVO-024 -- la conclusion centrale de l'arc est-elle en partie un ARTEFACT d'un defaut du code ?

EVO-021 a mesure que `add_node` DESALIGNE 56 % des aretes cablees : il n'ajuste pas `num_outputs`, donc
inserer dans le bloc de sortie re-mappe quelle decision chaque noeud pilote. Le taux de decouverte observe
dans tout l'arc est donc un PRODUIT : creation de l'arete x survie a add_node.

Levier : desactiver add_node (`add_node_rate = 0`). Si les lecteurs deviennent nettement plus frequents,
une part du verrou etait la DESTRUCTION par un bug, pas la rarete du tirage.

⚠️ CONFOND DECLARE AVANT LE RUN (regle scellee) : desactiver add_node retire AUSSI la croissance
architecturale. Un positif ne trancherait donc pas entre "stabilite des indices" et "absence de
croissance" -- il appellerait un second test.

Regle scellee : docs/preregistrations/EVO-024.json (lecture CONTINUE, Fisher calcule ici).
Plafond de cout DETERMINISTE en agent-ticks (E13) -- surtout pas budget_s.

    PYTHONPATH=. python -u tools/evo_runs/evo023_run.py
"""
import statistics
from math import comb

import numpy as np
from tools.jobs.run import hold

BUDGET_TICKS = 60_000
HAZARD = 15.0
N_SEEDS = 12

with hold("kuzu", owner="evo024-migration", ttl_s=14400):
    from tools.preregister import verify
    import tools.evo_cognitive_objective as M
    from src.seed_ai.mutation import MutationConfig, apply_mutations
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.persistence import calculate_life_score
    from tools.lewis_world import _setup_lewis

    rule = verify("EVO-024")
    print("regle SCELLEE verifiee |", rule["dv_primaire"], "\n")

    SIG = M.SIG_COLS[0]

    # ---- PRE-VOL : controle de manipulation OBLIGATOIRE (clause scellee) ---------------------------
    # Le flag change-t-il REELLEMENT l'operateur ? Marqueurs d'identite sur les diagonales de sortie :
    # un DECALAGE du bloc les deplace TOUS, une scission legitime n'en touche qu'UN (discriminateur).
    from src.seed_ai.mutation import add_node as _add_node, Genome as _G

    _I, _O, _N = 12, 8, 40

    def _marked():
        w = np.zeros((_N, _N), dtype=np.float32)
        np.fill_diagonal(w, 1.0)
        for k in range(_O):
            w[_N - _O + k, _N - _O + k] = 100.0 + k
        return _G(w, _I, _O)

    print("  PRE-VOL -- le flag change-t-il l'operateur ?")
    for lbl, flag in (("historique (off)", False), ("corrige (on)", True)):
        mc0 = MutationConfig()
        mc0.preserve_io_blocks = flag
        shifted = 0
        for s in range(200):
            g0 = _marked()
            np.random.seed(s)
            _add_node(g0, mc0)
            base = g0.num_nodes - g0.num_outputs
            faux = sum(1 for k in range(g0.num_outputs)
                       if float(g0.W[base + k, base + k]) != 100.0 + k)
            if faux > 1:
                shifted += 1
        print(f"    {lbl:>18} : bloc de sortie DECALE {shifted}/200")
        if flag and shifted != 0:
            print("")
            print("  ARRET : le correctif ne supprime pas le decalage -> le bras ne teste rien.")
            raise SystemExit(1)
        if not flag and shifted == 0:
            print("")
            print("  ARRET : `off` ne reproduit plus le defaut historique -> les records EVO-005..023")
            print("  sont incomparables ; il faut les RE-MESURER, pas continuer.")
            raise SystemExit(1)
    print("")

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

    def evolve(seed, preserve, eras=35, ticks=120, n=30):
        np.random.seed(seed)
        cfg = M._cfg()
        mc = MutationConfig()
        mc.add_node_rate = 0.4
        mc.preserve_io_blocks = preserve
        genomes = M._fresh_soup(n, cfg, 0.4)
        best, best_fit, spent = genomes[0].clone(), -1e18, 0
        for _ in range(eras):
            if spent > BUDGET_TICKS:
                return best, True
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
    for label, preserve in (("historique", False), ("corrige", True)):
        print(f"--- bras {label} (preserve_io_blocks={preserve}) ---")
        rows = []
        for s in range(N_SEEDS):
            g, ab = evolve(s, preserve)
            if ab:
                print(f"  seed {s:>2}: ABANDONNE (budget deterministe)")
                rows.append({"aborted": True})
                continue
            sal = M.measure_decision_saliency(g, 2000 + s, channel=SIG, out_idx=M.THROW_IDX, tasks=(1,))
            b = M.benchmark_cognitive(g, 1000 + s, tasks=(1,))
            rows.append({"seed": s, "sal": sal, "raw": b["raw"], "age": b["med_age"],
                         "N": g.num_nodes})
            flag = "   <<< LECTEUR" if sal > 0.5 else ""
            print(f"  seed {s:>2}: sal={sal:.3f} raw={b['raw']:.3f} age={b['med_age']:.0f} "
                  f"N={g.num_nodes}{flag}")
        out[label] = [r for r in rows if not r.get("aborted")]

    print("\n=== EVO-024 ===")
    print(f"{'bras':>13} | {'LECTEURS':>9} | {'sal max':>8} | {'raw med':>8} | {'N med':>6} | abandons")
    for label in ("historique", "corrige"):
        rr = out[label]
        nab = N_SEEDS - len(rr)
        if not rr:
            print(f"{label:>13} | tous abandonnes")
            continue
        rd = [r for r in rr if r["sal"] > 0.5]
        print(f"{label:>13} | {len(rd):>4}/{len(rr):<4} | {max(r['sal'] for r in rr):>8.3f} | "
              f"{statistics.median([r['raw'] for r in rr]):>8.3f} | "
              f"{statistics.median([r['N'] for r in rr]):>6.0f} | {nab}")

    a = sum(1 for r in out["corrige"] if r["sal"] > 0.5)
    b_ = len(out["corrige"]) - a
    c_ = sum(1 for r in out["historique"] if r["sal"] > 0.5)
    d = len(out["historique"]) - c_
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
    print(f"  Fisher exact bilateral corrige({a}/{a+b_}) vs historique({c_}/{c_+d}) : p = {p:.3f}")
    verdict = ("le correctif CHANGE les conclusions -> RE-MESURER EVO-005..023" if p < 0.05
               else "AUCUN effet demontre")
    statut = "effet" if p < 0.05 else "OBSERVATIONS ISOLEES, NON elevees"
    print(f"  -> {verdict} ; lecteurs bruts = {statut}")
    print("  PREDICTION declaree AVANT le run :", rule["prediction_declaree_AVANT"][:170])
