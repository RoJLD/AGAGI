"""EVO-023 -- la conclusion centrale de l'arc est-elle en partie un ARTEFACT d'un defaut du code ?

EVO-021 a mesure que `add_node` DESALIGNE 56 % des aretes cablees : il n'ajuste pas `num_outputs`, donc
inserer dans le bloc de sortie re-mappe quelle decision chaque noeud pilote. Le taux de decouverte observe
dans tout l'arc est donc un PRODUIT : creation de l'arete x survie a add_node.

Levier : desactiver add_node (`add_node_rate = 0`). Si les lecteurs deviennent nettement plus frequents,
une part du verrou etait la DESTRUCTION par un bug, pas la rarete du tirage.

⚠️ CONFOND DECLARE AVANT LE RUN (regle scellee) : desactiver add_node retire AUSSI la croissance
architecturale. Un positif ne trancherait donc pas entre "stabilite des indices" et "absence de
croissance" -- il appellerait un second test.

Regle scellee : docs/preregistrations/EVO-023.json (lecture CONTINUE, Fisher calcule ici).
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

with hold("kuzu", owner="evo023-no-addnode", ttl_s=14400):
    from tools.preregister import verify
    import tools.evo_cognitive_objective as M
    from src.seed_ai.mutation import MutationConfig, apply_mutations
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.persistence import calculate_life_score
    from tools.lewis_world import _setup_lewis

    rule = verify("EVO-023")
    print("regle SCELLEE verifiee |", rule["dv_primaire"], "\n")

    # ---- GARDE E23 (porte 11) : la FAMILLE de controles est DECLAREE, avant la premiere mesure ----
    # COMBIEN de cellules ? DEUX seuils de controle, tous deux dans le PRE-VOL ci-dessous, chacun
    # applique UNE SEULE FOIS a une lignee de 200 mutations a graine FIXE (np.random.seed(0)) :
    #   (a) bras sans croissance : `rate == 0.0 and g0.num_nodes != n0`  -> ARRET (desactivation prise ?)
    #   (b) bras temoin          : `rate == 0.4 and g0.num_nodes == n0`  -> ARRET (contraste present ?)
    # Deux cellules APPARIEES et de SENS OPPOSE (classe E1 : une garde qui ne sait pas se taire est
    # aussi inutilisable qu'une garde qui ne sait pas crier). Aucun autre seuil de controle apres le
    # run : le Fisher exact bilateral est la DV, unique, hors famille.
    from tools.experiment_preflight import assert_control_family, declare_design

    FAMILLE_CELLULES = 2
    _famille = assert_control_family(
        cells=FAMILLE_CELLULES, alpha_family=0.05, method="none",
        reason="Multiplicite SANS OBJET ici : les 2 cellules sont des assertions DETERMINISTES "
               "(num_nodes apres 200 mutations a graine FIXE, donc REPRODUCTIBLE bit a bit) evaluees "
               "UNE FOIS chacune, hors du monde simule. Aucun alpha n'est applique a une cellule de "
               "controle : il n'y a rien a corriger, et une Bonferroni serait DECORATIVE. La forme "
               "d'E23 (bande fixe appliquee a CHAQUE replicat, 24 cellules -> 0.216 de fausse alarme "
               "sur un harnais parfait) est absente par construction. Le seul test a p-value du run "
               "est la DV (Fisher exact), unique.")
    design = declare_design(
        question=rule["question"],
        replication_unit=f"seed ({N_SEEDS} seeds par bras ; une lignee evolutive par seed -- les 30 "
                         "genomes d'une lignee partagent monde, elite et tirages)",
        n_independent=N_SEEDS,
        links={"add_node_rate=0 (+ meso) -> num_nodes CONSTANT, aucune croissance (pre-vol)": "measured",
               "absence de croissance -> seed LECTEUR (measure_decision_saliency > 0.5)": "measured"},
        control_family=_famille,
        cost_estimate=rule.get("garde_cout"))
    print(f"[design] unite = {design['replication_unit']} | famille = {_famille['cells']} cellules, "
          f"method={_famille['method']} (raison publiee dans le design)\n")

    SIG = M.SIG_COLS[0]

    # ---- PRE-VOL : controle de manipulation OBLIGATOIRE ------------------------------------------
    # Le bras sans add_node doit garder num_nodes CONSTANT ; le temoin doit grandir.
    print("  PRE-VOL -- la desactivation de TOUTE croissance prend-elle ?")
    for lbl, rate in (("temoin (0.4)", 0.4), ("sans croissance (0.0)", 0.0)):
        np.random.seed(0)
        g0 = M._fresh_soup(1, M._cfg(), 0.4)[0]
        mc0 = MutationConfig()
        mc0.add_node_rate = rate
        if rate == 0.0:
            # ⚠️ add_node n'est PAS la seule voie de croissance : `add_meso_gated_unit`
            # (mutation.py:188) fait DEUX np.insert de plus. Mesure : add_node_rate=0 seul
            # laissait encore 172 -> 198 noeuds. Le pre-vol l'a intercepte.
            mc0.meso_gate_rate = 0.0
            mc0.meso_skip_rate = 0.0
        n0 = g0.num_nodes
        for _ in range(200):
            g0 = apply_mutations(g0, mc0)
        print(f"    {lbl:>20} : num_nodes {n0} -> {g0.num_nodes}")
        if rate == 0.0 and g0.num_nodes != n0:
            print("\n  ARRET : add_node n'est PAS desactive -> le bras ne teste rien (clause scellee).")
            raise SystemExit(1)
        if rate == 0.4 and g0.num_nodes == n0:
            print("\n  ARRET : le temoin ne grandit pas -> pas de contraste, le bras ne teste rien.")
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

    def evolve(seed, add_rate, eras=35, ticks=120, n=30):
        np.random.seed(seed)
        cfg = M._cfg()
        mc = MutationConfig()
        mc.add_node_rate = add_rate
        if add_rate == 0.0:
            mc.meso_gate_rate = 0.0     # 2e voie de croissance (add_meso_gated_unit)
            mc.meso_skip_rate = 0.0
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
    for label, add_rate in (("temoin_0.4", 0.4), ("sans_addnode", 0.0)):
        print(f"--- bras {label} (add_node_rate={add_rate}) ---")
        rows = []
        for s in range(N_SEEDS):
            g, ab = evolve(s, add_rate)
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

    print("\n=== EVO-023 ===")
    print(f"{'bras':>13} | {'LECTEURS':>9} | {'sal max':>8} | {'raw med':>8} | {'N med':>6} | abandons")
    for label in ("temoin_0.4", "sans_addnode"):
        rr = out[label]
        nab = N_SEEDS - len(rr)
        if not rr:
            print(f"{label:>13} | tous abandonnes")
            continue
        rd = [r for r in rr if r["sal"] > 0.5]
        print(f"{label:>13} | {len(rd):>4}/{len(rr):<4} | {max(r['sal'] for r in rr):>8.3f} | "
              f"{statistics.median([r['raw'] for r in rr]):>8.3f} | "
              f"{statistics.median([r['N'] for r in rr]):>6.0f} | {nab}")

    a = sum(1 for r in out["sans_addnode"] if r["sal"] > 0.5)
    b_ = len(out["sans_addnode"]) - a
    c_ = sum(1 for r in out["temoin_0.4"] if r["sal"] > 0.5)
    d = len(out["temoin_0.4"]) - c_
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
    print(f"  Fisher exact bilateral sans_addnode({a}/{a+b_}) vs temoin({c_}/{c_+d}) : p = {p:.3f}")
    verdict = ("une PART du verrou etait la DESTRUCTION, pas le tirage" if p < 0.05
               else "AUCUN effet demontre")
    statut = "effet" if p < 0.05 else "OBSERVATIONS ISOLEES, NON elevees"
    print(f"  -> {verdict} ; lecteurs bruts = {statut}")
    print("  CONFOND declare AVANT le run :", rule["confond_declare_AVANT"][:150])
