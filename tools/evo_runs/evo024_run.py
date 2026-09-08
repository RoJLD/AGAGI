"""EVO-024 -- MIGRATION : activer le correctif d'indices change-t-il les conclusions de l'arc ?

EVO-021 a mesure que `add_node` DESALIGNE 56 % des aretes cablees : il n'ajuste ni `num_inputs` ni
`num_outputs`, donc inserer dans le bloc de sortie re-mappe quelle decision chaque noeud pilote. Le
taux de decouverte observe dans tout l'arc est donc un PRODUIT : creation de l'arete x survie a add_node.

Levier (celui de la regle SCELLEE EVO-024, et celui que le code applique) : le flag `preserve_io_blocks`,
DESACTIVE par defaut (off = bit-identique aux runs historiques). Les deux bras gardent
`add_node_rate = 0.4` -- la croissance N'EST PAS coupee ici, c'est EVO-023 qui la coupait. Seul le
correctif d'indices bouge : historique (off) vs corrige (on), 2 bras x 12 seeds.

⚠️ Le pre-vol est le controle de manipulation SCELLE : le taux de DECALAGE du bloc de sortie doit etre
NON NUL en historique et NUL en corrige. Ses deux assertions sont APPARIEES et de sens oppose (E1) :
si `off` ne reproduit plus le defaut, les records EVO-005..023 sont incomparables et il faut les
RE-MESURER, pas continuer.

Regle scellee : docs/preregistrations/EVO-024.json (lecture CONTINUE, Fisher calcule ici).
Plafond de cout DETERMINISTE en agent-ticks (E13) -- surtout pas budget_s.

    PYTHONPATH=. python -u tools/evo_runs/evo024_run.py
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

    # ---- GARDE E23 (porte 11) : la FAMILLE de controles est DECLAREE, avant la premiere mesure ----
    # COMBIEN de cellules ? DEUX seuils de controle, tous deux dans le PRE-VOL ci-dessous, chacun
    # applique UNE SEULE FOIS a un compte agrege sur 200 tirages a graines FIXES (0..199) :
    #   (a) bras corrige  : `flag and shifted != 0`  -> ARRET (le correctif supprime-t-il le decalage ?)
    #   (b) bras temoin   : `not flag and shifted == 0` -> ARRET (le defaut historique est-il reproduit ?)
    # Ces deux cellules sont APPARIEES et de SENS OPPOSE (une garde qui ne sait pas se taire est aussi
    # inutilisable qu'une garde qui ne sait pas crier, classe E1). Aucun autre seuil de controle n'est
    # applique apres le run : le Fisher exact bilateral est la DV, unique, hors famille.
    from tools.experiment_preflight import assert_control_family, declare_design

    FAMILLE_CELLULES = 2
    _famille = assert_control_family(
        cells=FAMILLE_CELLULES, alpha_family=0.05, method="none",
        reason="Multiplicite SANS OBJET ici : les 2 cellules sont des assertions DETERMINISTES "
               "(compte de decalages sur 200 tirages a graines FIXES 0..199, donc REPRODUCTIBLE bit "
               "a bit) evaluees UNE FOIS chacune, sur des donnees agregees et hors du monde simule. "
               "Aucun alpha n'est applique a une cellule de controle : il n'y a rien a corriger, et "
               "une Bonferroni serait DECORATIVE. La forme d'E23 (bande fixe appliquee a CHAQUE "
               "replicat, 24 cellules -> 0.216 de fausse alarme sur un harnais parfait) est absente "
               "par construction. Le seul test a p-value du run est la DV (Fisher exact), unique.")
    design = declare_design(
        question=rule["question"],
        replication_unit=f"seed ({N_SEEDS} seeds par bras ; une lignee evolutive par seed -- les 30 "
                         "genomes d'une lignee partagent monde, elite et tirages)",
        n_independent=N_SEEDS,
        links={"preserve_io_blocks -> le bloc de sortie n'est plus DECALE par add_node (pre-vol)": "measured",
               "stabilite des indices -> seed LECTEUR (measure_decision_saliency > 0.5)": "measured"},
        control_family=_famille,
        cost_estimate=rule.get("garde_cout") or rule.get("cout"))
    print(f"[design] unite = {design['replication_unit']} | famille = {_famille['cells']} cellules, "
          f"method={_famille['method']} (raison publiee dans le design)\n")

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
