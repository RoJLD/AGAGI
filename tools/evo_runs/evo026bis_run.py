"""EVO-026-bis -- D2 : « le verrou est le TIRAGE » veut-il dire RARETE ou NON-ACCUMULATION ?

  MODELE A (rarete combinatoire) : les tirages sont INDEPENDANTS -> 21x l'horizon donne ~8/24 lecteurs.
  MODELE B (non-accumulation, EVO-010) : les tirages ne se composent pas -> ~0-1/24 dans les deux bras.

POURQUOI -bis. EVO-026 est NON LISIBLE : son bras long a plante sur LIMIT_N=256 (mamba_agent.py:405),
le genome passant de 172 a ~300 noeuds en 735 eres. Le crash a revele un defaut PLUS GRAVE que le
plantage : le nombre d'aretes possibles va en N^2 (29 584 a N=172 -> 65 536 a N=256), donc le bras long
ACCUMULAIT des tirages tout en DILUANT chacun d'eux ~2.2x. La prediction 1-(1-p)^21 suppose p CONSTANT ;
l'appareil ne le tenait pas. Un nul aurait ete lu « modele B » alors qu'une part venait de la dilution
-- un bras qui ne peut pas reussir, classe E2.

CORRECTIF : croissance de noeuds DESACTIVEE dans LES DEUX bras. N reste a 172, le denominateur est
constant, LIMIT_N n'est jamais atteint. `add_connection` -- le tirage etudie -- est inchange puisqu'il
cable des noeuds EXISTANTS. EDR-EVO-023 a mesure qu'a horizon standard, sans croissance, on obtient
0/12 comme le temoin : le bras standard reste donc comparable a la baseline de l'arc.

⚠️ Ecrit EXPLICITEMENT, pas derive par regex d'evo026_run.py (registre E4 occ.4).

Regle scellee : docs/preregistrations/EVO-026-bis.json (lecture CONTINUE, Fisher calcule ici).

    PYTHONPATH=. python -u tools/evo_runs/evo026bis_run.py
"""
import statistics
import time
from math import comb

import numpy as np
from tools.jobs.run import hold

HAZARD = 15.0
N_SEEDS = 24
TICKS = 120
POP = 30
ELITE = 7
ERAS_STD = 35
ERAS_LONG = 735                       # 21x -- l'horizon nomme par D2
TICKS_PER_ERA_BUDGET = 60_000 / 35    # meme generosite par ere dans les deux bras (E13, anti-censure)

with hold("kuzu", owner="evo026bis-horizon", ttl_s=28800):
    from tools.preregister import verify
    import tools.evo_cognitive_objective as M
    import src.seed_ai.mutation as MUT
    from src.seed_ai.mutation import MutationConfig, apply_mutations
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.persistence import calculate_life_score
    from tools.lewis_world import _setup_lewis

    rule = verify("EVO-026-bis")
    print("regle SCELLEE verifiee |", rule["dv_primaire"], "\n")

    SIG = M.SIG_COLS[0]

    # --- instrumentation du TIRAGE : compter les appels reels a add_connection -----------------------
    # apply_mutations appelle add_connection par nom de module -> patcher MUT.add_connection mord.
    _draws = {"n": 0}
    _real_add_connection = MUT.add_connection

    def _counting_add_connection(genome, config):
        _draws["n"] += 1
        return _real_add_connection(genome, config)

    MUT.add_connection = _counting_add_connection

    def _mc():
        """Config IDENTIQUE dans les deux bras -- l'horizon est la SEULE difference."""
        mc = MutationConfig()
        mc.preserve_io_blocks = True     # EDR-EVO-024 (sans effet ici : rien ne s'insere)
        mc.add_node_rate = 0.0           # ⚠️ denominateur CONSTANT : N reste a 172
        mc.meso_gate_rate = 0.0          # 2e voie de croissance (EVO-023 : add_node ne suffit pas)
        mc.meso_skip_rate = 0.0
        return mc

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

    def evolve(seed, eras):
        """Renvoie (meilleur genome, abandon?, eres atteintes, extinction?, tirages, ages medians)."""
        np.random.seed(seed)
        cfg = M._cfg()
        mc = _mc()
        budget = eras * TICKS_PER_ERA_BUDGET
        genomes = M._fresh_soup(POP, cfg, 0.4)
        best, best_fit, spent = genomes[0].clone(), -1e18, 0
        d0 = _draws["n"]
        ages, reached, extinct = [], 0, False
        for era in range(eras):
            if spent > budget:
                return best, True, reached, extinct, _draws["n"] - d0, ages
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
            spent += sum(int(a.get("age", 0)) for a in pool)
            reached = era + 1
            if not pool:
                extinct = True
                break
            ages.append(statistics.median([int(a.get("age", 0)) for a in pool]))
            pool.sort(key=calculate_life_score, reverse=True)
            if calculate_life_score(pool[0]) > best_fit:
                best_fit = calculate_life_score(pool[0])
                best = pool[0]["model"].genome.clone()
            el = [a["model"].genome.clone() for a in pool[:ELITE]]
            ch = []
            while len(ch) < POP - len(el):
                ch.append(apply_mutations(el[np.random.randint(len(el))], mc))
            genomes = el + ch
        return best, False, reached, extinct, _draws["n"] - d0, ages

    # ---- RUN ---------------------------------------------------------------------------------------
    # Aucun pre-vol par SONDE : les trois controles de manipulation sont mesures IN SITU sur le run
    # lui-meme et lus APRES (classe E6 -- une sonde mesurerait un regime que le run ne visite pas).
    out = {}
    for label, eras in (("standard", ERAS_STD), ("long", ERAS_LONG)):
        print(f"--- bras {label} ({eras} eres) ---")
        rows = []
        for s in range(N_SEEDS):
            t0 = time.time()
            g, ab, reached, extinct, draws, ages = evolve(s, eras)
            if ab:
                print(f"  seed {s:>2}: ABANDONNE (budget deterministe) apres {reached} eres")
                rows.append({"aborted": True})
                continue
            sal = M.measure_decision_saliency(g, 2000 + s, channel=SIG, out_idx=M.THROW_IDX, tasks=(1,))
            b = M.benchmark_cognitive(g, 1000 + s, tasks=(1,))
            tail = ages[-max(1, len(ages) // 10):] if ages else [0.0]
            age_fin = statistics.median(tail)
            rows.append({"seed": s, "sal": sal, "raw": b["raw"], "age": b["med_age"], "N": g.num_nodes,
                         "reached": reached, "extinct": extinct, "draws": draws, "age_fin": age_fin})
            flag = "   <<< LECTEUR" if sal > 0.5 else ""
            ext = " EXTINCTION" if extinct else ""
            print(f"  seed {s:>2}: sal={sal:.3f} raw={b['raw']:.3f} age_fin={age_fin:.1f} "
                  f"N={g.num_nodes} eres={reached} tirages={draws} [{time.time()-t0:.0f}s]{ext}{flag}")
        out[label] = [r for r in rows if not r.get("aborted")]

    print("\n=== EVO-026-bis ===")
    print(f"{'bras':>9} | {'LECTEURS':>9} | {'sal max':>8} | {'raw med':>8} | {'age_fin med':>11} | "
          f"{'N med':>6} | {'tirages med':>11} | {'extinct':>7} | abandons")
    for label in ("standard", "long"):
        rr = out[label]
        nab = N_SEEDS - len(rr)
        if not rr:
            print(f"{label:>9} | tous abandonnes")
            continue
        rd = [r for r in rr if r["sal"] > 0.5]
        print(f"{label:>9} | {len(rd):>4}/{len(rr):<4} | {max(r['sal'] for r in rr):>8.3f} | "
              f"{statistics.median([r['raw'] for r in rr]):>8.3f} | "
              f"{statistics.median([r['age_fin'] for r in rr]):>11.1f} | "
              f"{statistics.median([r['N'] for r in rr]):>6.0f} | "
              f"{statistics.median([r['draws'] for r in rr]):>11.0f} | "
              f"{sum(1 for r in rr if r['extinct']):>7} | {nab}")

    if not out["standard"] or not out["long"]:
        print("\n  RUN NON LISIBLE : un bras entier est vide.")
        raise SystemExit(0)

    # ---- LES TROIS CONTROLES DE MANIPULATION (clause scellee), lus AVANT tout verdict ---------------
    ds = statistics.median([r["draws"] for r in out["standard"]])
    dl = statistics.median([r["draws"] for r in out["long"]])
    ns = statistics.median([r["N"] for r in out["standard"]])
    nl = statistics.median([r["N"] for r in out["long"]])
    print("\n  CONTROLES DE MANIPULATION (in situ) :")
    ok = True
    print(f"    (1) compteur de tirages > 0 : standard={ds:.0f} long={dl:.0f}")
    if ds <= 0 or dl <= 0:
        print("        ECHEC -- l'instrumentation n'a pas mordu (classe E4).")
        ok = False
    ratio = dl / max(ds, 1e-9)
    print(f"    (2) ratio des tirages = {ratio:.1f}x (clause : [15, 27])")
    if not (15.0 <= ratio <= 27.0):
        print("        ECHEC -- l'horizon n'a PAS delivre les tirages annonces.")
        ok = False
    print(f"    (3) N median identique : standard={ns:.0f} long={nl:.0f} (clause : |ecart| <= 2)")
    if abs(ns - nl) > 2:
        print("        ECHEC -- la croissance n'est pas desactivee, le denominateur a bouge "
              "(c'est le defaut qui a rendu EVO-026 illisible).")
        ok = False
    if not ok:
        print("\n  -> AUCUN VERDICT n'est tire : le dispositif n'a pas fait ce qu'il annonce.")
        raise SystemExit(0)

    a = sum(1 for r in out["long"] if r["sal"] > 0.5)
    b_ = len(out["long"]) - a
    c_ = sum(1 for r in out["standard"] if r["sal"] > 0.5)
    d = len(out["standard"]) - c_
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
    print(f"\n  Fisher exact bilateral long({a}/{a+b_}) vs standard({c_}/{c_+d}) : p = {p:.4f}")

    # ---- lecture SCELLEE, dans l'ordre impose par la regle ------------------------------------------
    if p < 0.05 and a / max(a + b_, 1) > c_ / max(c_ + d, 1):
        print("  -> MODELE A : le verrou est une RARETE combinatoire, franchissable par l'ECHELLE.")
        print("     « le verrou est le tirage » devient « le verrou est le NOMBRE de tirages ».")
    elif p < 0.05:
        print("  -> INATTENDU : l'horizon DETRUIT (long < standard). A rapporter tel quel.")
    else:
        hs = statistics.median([r["age_fin"] for r in out["standard"]])
        hl = statistics.median([r["age_fin"] for r in out["long"]])
        print(f"  aucun effet demontre -> lecture de la dv_sante_lignee : "
              f"standard {hs:.1f} vs long {hl:.1f} (ratio {hl/max(hs,1e-9):.2f}x, seuil 0.70)")
        if hl >= 0.7 * hs:
            print("  -> MODELE B CONFIRME : les tirages ne s'ACCUMULENT pas (lignee saine, horizon inutile).")
        else:
            print("  -> NON CONCLUANT par DEGRADATION : le bras long ne pouvait pas reussir (classe E2) ; "
                  "aucun modele n'est departage.")
    print("\n  PUISSANCE declaree AVANT :", rule["puissance_declaree"][:200])
