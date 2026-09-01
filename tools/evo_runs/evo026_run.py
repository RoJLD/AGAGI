"""EVO-026 -- D2 : « le verrou est le TIRAGE » veut-il dire RARETE ou NON-ACCUMULATION ?

Deux modeles incompatibles expliquent toute la cloture de l'arc et predisent l'inverse a horizon long :
  MODELE A (rarete combinatoire) : les tirages sont INDEPENDANTS -> 21x l'horizon donne ~10/12 lecteurs.
  MODELE B (non-accumulation, EVO-010) : les tirages ne se composent pas -> ~1/12 dans les deux bras.

⚠️ Ecrit EXPLICITEMENT, pas derive d'un runner precedent (registre E4 occ.4 : une derivation par regex
   avait laisse un pre-vol qui ne verifiait PAS ce qu'il annoncait, run tue).
⚠️ LES DEUX BRAS avec preserve_io_blocks=True (EDR-EVO-024) : a 735 eres le genome grossit bien plus,
   le defaut d'indices penaliserait donc le bras long DIFFERENTIELLEMENT.

Regle scellee : docs/preregistrations/EVO-026.json (lecture CONTINUE, Fisher calcule ici).

    PYTHONPATH=. python -u tools/evo_runs/evo026_run.py
"""
import statistics
import time
from math import comb

import numpy as np
from tools.jobs.run import hold

HAZARD = 15.0
N_SEEDS = 12
TICKS = 120
POP = 30
ELITE = 7
ERAS_STD = 35
ERAS_LONG = 735                       # 21x -- l'horizon nomme par D2
TICKS_PER_ERA_BUDGET = 60_000 / 35    # meme generosite par ere dans les deux bras (E13, anti-censure)

with hold("kuzu", owner="evo026-horizon", ttl_s=21600):
    from tools.preregister import verify
    import tools.evo_cognitive_objective as M
    import src.seed_ai.mutation as MUT
    from src.seed_ai.mutation import MutationConfig, apply_mutations
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.persistence import calculate_life_score
    from tools.lewis_world import _setup_lewis

    rule = verify("EVO-026")
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
        mc = MutationConfig()
        mc.preserve_io_blocks = True      # cf. EDR-EVO-024 -- l'horizon doit etre la SEULE difference
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

    # ---- PRE-VOL : le compteur MORD-il ? (clause scellee, volet 2) ----------------------------------
    # ⚠️ Le volet 1 (ratio 21x) n'est PAS teste par une sonde : il est mesure sur les tirages REELS
    #    comptes pendant le run, par seed, et il conditionne le verdict a la fin. Une sonde serait un
    #    PROXY du dispositif ; les compteurs in-situ sont le dispositif lui-meme.
    #    (Premiere version de ce pre-vol : 16 905 mutations CUMULATIVES sur un seul genome -- un regime
    #     que le run ne visite jamais, puisque `apply_mutations` CLONE et que la lignee n'accumule qu'une
    #     mutation par ere. Non representatif ET pathologiquement lent ; run tue et sonde retiree.)
    print("  PRE-VOL -- l'instrumentation du TIRAGE mord-elle ? (classe E4)")
    d0 = _draws["n"]
    np.random.seed(999)
    base = M._fresh_soup(1, M._cfg(), 0.4)[0]
    mc_probe = _mc()
    for _ in range(ERAS_STD):
        kids = [apply_mutations(base, mc_probe) for _ in range(POP - ELITE)]
        base = kids[0]                      # la lignee n'accumule qu'UNE mutation par ere, comme l'elite
    probe_std = _draws["n"] - d0
    print(f"    lignee de {ERAS_STD} eres : {probe_std} appels a add_connection")
    if probe_std == 0:
        print("\n  ARRET : compteur a ZERO -- l'instrumentation n'a pas mordu (classe E4).")
        raise SystemExit(1)
    print("")

    # ---- RUN ---------------------------------------------------------------------------------------
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
            # sante de lignee : age median sur le DERNIER dixieme des eres (dv_sante_lignee)
            tail = ages[-max(1, len(ages) // 10):] if ages else [0.0]
            age_fin = statistics.median(tail)
            rows.append({"seed": s, "sal": sal, "raw": b["raw"], "age": b["med_age"], "N": g.num_nodes,
                         "reached": reached, "extinct": extinct, "draws": draws, "age_fin": age_fin})
            flag = "   <<< LECTEUR" if sal > 0.5 else ""
            ext = " EXTINCTION" if extinct else ""
            print(f"  seed {s:>2}: sal={sal:.3f} raw={b['raw']:.3f} age_fin={age_fin:.1f} "
                  f"N={g.num_nodes} eres={reached} tirages={draws} [{time.time()-t0:.0f}s]{ext}{flag}")
        out[label] = [r for r in rows if not r.get("aborted")]

    print("\n=== EVO-026 ===")
    print(f"{'bras':>9} | {'LECTEURS':>9} | {'sal max':>8} | {'raw med':>8} | {'age_fin med':>11} | "
          f"{'tirages med':>11} | {'extinct':>7} | abandons")
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
              f"{statistics.median([r['draws'] for r in rr]):>11.0f} | "
              f"{sum(1 for r in rr if r['extinct']):>7} | {nab}")

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

    # ---- CONTROLE DE MANIPULATION, volet 1 : sur les tirages REELS du run ---------------------------
    # Mesure in-situ, pas une sonde. Si l'horizon n'a pas delivre ~21x les tirages (extinction precoce,
    # abandon budgetaire), le bras long n'a pas teste ce qu'il pretend et AUCUN verdict n'est lisible.
    ds = statistics.median([r["draws"] for r in out["standard"]]) if out["standard"] else 0
    dl = statistics.median([r["draws"] for r in out["long"]]) if out["long"] else 0
    ratio = dl / max(ds, 1e-9)
    print(f"  CONTROLE : tirages reels {ds:.0f} (standard) vs {dl:.0f} (long) -> ratio {ratio:.1f}x "
          f"(clause scellee : [15, 27])")
    if not (15.0 <= ratio <= 27.0):
        print("  -> RUN NON LISIBLE : l'horizon n'a PAS delivre les tirages annonces ; le bras long "
              "ne pouvait pas tester le modele A. Aucun verdict n'est tire (clause de manipulation).")
        raise SystemExit(0)

    # ---- lecture SCELLEE, dans l'ordre impose par la regle ------------------------------------------
    if p < 0.05 and a / max(a + b_, 1) > c_ / max(c_ + d, 1):
        print("  -> MODELE A : le verrou est une RARETE combinatoire, franchissable par l'ECHELLE.")
    elif p < 0.05:
        print("  -> INATTENDU : l'horizon DETRUIT (long < standard). A rapporter tel quel.")
    else:
        # la sante de lignee ne se lit QUE dans cette branche (clause scellee)
        hs = statistics.median([r["age_fin"] for r in out["standard"]]) if out["standard"] else 0.0
        hl = statistics.median([r["age_fin"] for r in out["long"]]) if out["long"] else 0.0
        print(f"  aucun effet demontre -> lecture de la dv_sante_lignee : "
              f"standard {hs:.1f} vs long {hl:.1f} (ratio {hl/max(hs,1e-9):.2f}x)")
        if hl >= 0.7 * hs:
            print("  -> MODELE B CONFIRME : les tirages ne s'ACCUMULENT pas (lignee saine, horizon inutile).")
        else:
            print("  -> NON CONCLUANT par DEGRADATION : le bras long ne pouvait pas reussir (classe E2) ; "
                  "aucun modele n'est departage.")
    print("  CONFOND declare AVANT le run :", rule["confond_declare_AVANT"][:160])
