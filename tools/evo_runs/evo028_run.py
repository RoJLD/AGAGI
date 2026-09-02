"""EVO-028 -- la dependance FAIBLE a la position (LATE/EARLY dans [0.5 ; 0.818]) : EVO-027 verbatim, GROSSI.

Design du panel 3 juges + refutateur du 2026-09-02
(docs/superpowers/specs/2026-09-02-evo028-weak-position-design.md). Les 3 designs within-seed sont
MORTS sur preuve d'identite (classe E20 : dans un crossover a ordre fixe, l'ordre EST la position ->
l'estimand est le produit position x carry-over). La seule structure identifiante est celle
d'EVO-027 : deux lignees par graine, jamais deux fenetres dans une lignee. Seule modification
scientifique : n. La bande (0.818 ; 1.0) est fermee d'avance sur preuve de cout (divergence (1-r)^-2).

Ecrit EXPLICITEMENT (registre E4 occ.4 : jamais deriver un runner par regex). Ajouts vs evo027_run :
  * lecture SECONDAIRE sans poids : saillance du top-1 de l'elite a la DERNIERE ere, a cote du
    best-ever (sur EARLY les deux doivent coincider -- c'est son no-op de calibration) ;
  * taux rapportes PAR paire cible (EVO-027 n'en a publie aucun -> ancre externe incommensurable) ;
  * persistance best + last (data/genomes/evo028*/) ;
  * garde de cout E13 PENDANT (CostGuard par seed, abandons comptes par bras).

Modes :
  EVO028_SMOKE=1 PYTHONPATH=. python -u tools/evo_runs/evo028_run.py
      1 seed COMPLET par bras, chronometre PAR ERE ; lit les seuils scelles EVO-028-SMOKE.
  EVO028_TPAIR_S=<mesure du smoke> PYTHONPATH=. python -u tools/evo_runs/evo028_run.py
      run principal (EVO028_SEEDS, defaut 86/bras) ; exige la regle scellee EVO-028.
"""
import os
import statistics
import time
from math import comb

import numpy as np
from tools.jobs.run import hold

SMOKE = os.environ.get("EVO028_SMOKE") == "1"
N_SEEDS = 1 if SMOKE else int(os.environ.get("EVO028_SEEDS", "86"))
TICKS = 120
POP = 30
W_COG = 5000.0
FEN = 15
BRAS = {"EARLY": {"bias": range(1, 16), "eras": 30, "marque_logit": 5},
        "LATE":  {"bias": range(21, 36), "eras": 50, "marque_logit": 25}}
TICKS_PER_ERA_BUDGET = 60_000 / 35            # meme generosite par ere qu'EVO-027 (E13)
PLAFOND_TOTAL_S = 11_520.0                    # 80 % du bail 4 h (scelle dans EVO-028-SMOKE)
SEED_BUDGET_S = float(os.environ.get("EVO028_SEED_BUDGET_S", "600"))

with hold("kuzu", owner="evo028-smoke" if SMOKE else "evo028-position-faible", ttl_s=14400):
    from tools.preregister import verify
    import tools.evo_cognitive_objective as M
    import src.seed_ai.mutation as MUT
    from src.seed_ai.mutation import MutationConfig, apply_mutations
    from tools.evo_mech_dv import logit_median_at_outputs
    from tools.cost_guard import project_cost, CostGuard, CostExceeded

    rule = verify("EVO-028-SMOKE" if SMOKE else "EVO-028")
    print(f"regle SCELLEE verifiee ({'EVO-028-SMOKE' if SMOKE else 'EVO-028'}) |",
          str(rule.get("dv_primaire") or rule.get("mesure"))[:90], "\n")

    if not SMOKE:
        # E13 AVANT : la projection utilise le t_pair MESURE par le smoke (jamais extrapole d'un prefixe).
        t_pair = float(os.environ["EVO028_TPAIR_S"])   # KeyError volontaire : pas de smoke, pas de run
        project_cost(unit_s=t_pair, n_units=N_SEEDS, budget_s=PLAFOND_TOTAL_S, safety=1.0,
                     label="EVO-028 principal")         # le plafond scelle porte le TOTAL, marge incluse

    TASKS = M.TASKS_EVO006
    PAIRES_REL = ((M.SIG_COLS[0], M.ACT_POS), (M.SIG_COLS[0], M.ACT_NEG),
                  (M.SIG_COLS[1], M.THROW_IDX), (M.SIG_COLS[2], M.ACCEPT_IDX))

    # ---- l'operateur biaise d'EVO-009, fenetre pilotee par un drapeau (verbatim EVO-027) ----------
    _orig_add_connection = MUT.add_connection
    _etat = {"on": False, "hits": 0}

    def _biased_add_connection(genome, config):
        """Une fois sur deux quand la fenetre est ouverte : candidats restreints aux paires cibles
        LIBRES (W==0). Sinon, ou si aucune paire n'est libre, comportement d'origine."""
        if _etat["on"] and np.random.rand() < 0.5:
            o = genome.num_nodes - genome.num_outputs
            libres = [(c, o + out) for c, out in PAIRES_REL
                      if c < genome.num_nodes and o + out < genome.num_nodes
                      and genome.W[c, o + out] == 0]
            if libres:
                i, j = libres[np.random.randint(len(libres))]
                genome.W[i, j] = np.random.normal(config.weight_init_mean, config.weight_init_std)
                _etat["hits"] += 1
                return
        return _orig_add_connection(genome, config)

    MUT.add_connection = _biased_add_connection

    def _mc():
        mc = MutationConfig()
        mc.preserve_io_blocks = True          # EDR-EVO-024
        mc.add_node_rate = 0.0                # N constant (lecon EVO-026)
        mc.meso_gate_rate = 0.0
        mc.meso_skip_rate = 0.0
        return mc

    def _porte_arete(genome):
        o = genome.num_nodes - genome.num_outputs
        return any(genome.W[c, o + out] != 0 for c, out in PAIRES_REL
                   if c < genome.num_nodes and o + out < genome.num_nodes)

    PERSIST_DIR = os.path.join("data", "genomes", "evo028_smoke" if SMOKE else "evo028")

    def _persist(bras, seed, tag, g):
        os.makedirs(PERSIST_DIR, exist_ok=True)
        np.savez_compressed(os.path.join(PERSIST_DIR, f"{bras.lower()}_seed{seed}_{tag}.npz"),
                            W=g.W, num_inputs=g.num_inputs, num_outputs=g.num_outputs,
                            num_nodes=g.num_nodes)

    def evolve(seed, bras):
        np.random.seed(seed)
        cfg = M._cfg()
        mc = _mc()
        eras, fen = BRAS[bras]["eras"], BRAS[bras]["bias"]
        budget = eras * TICKS_PER_ERA_BUDGET
        genomes = M._fresh_soup(POP, cfg, 0.0)
        n_elite = max(3, POP // 4)
        best_g, best_fit = genomes[0].clone(), -1e18
        last_top1 = None
        h0 = _etat["hits"]
        ages, spent, logit_med, portage_fin = [], 0, float("nan"), None
        garde = CostGuard(budget_s=SEED_BUDGET_S, label=f"{bras} seed {seed}")
        t_eres = []
        for era in range(1, eras + 1):
            garde.tick()                       # E13 PENDANT : un seed pathologique ne tue pas le run
            if spent > budget:
                return {"aborted": True, "reached": era}
            t0 = time.time()
            _etat["on"] = era in fen
            _, pool = M._run_era(genomes, cfg, TICKS, era, inject=True, K=1, tasks=TASKS)
            _etat["on"] = False
            spent += sum(int(a.get("age", 0)) for a in pool)
            t_eres.append(time.time() - t0)
            if not pool:
                return {"aborted": False, "extinct": True, "reached": era, "genome": best_g,
                        "last_top1": last_top1, "hits": _etat["hits"] - h0, "ages": ages,
                        "logit_med": logit_med, "portage_fin": portage_fin,
                        "N": best_g.num_nodes, "t_eres": t_eres}
            ages.append(statistics.median([int(a.get("age", 0)) for a in pool]))
            pool.sort(key=lambda ag: M.cognitive_fitness(ag, W_COG), reverse=True)
            if M.cognitive_fitness(pool[0], W_COG) > best_fit:
                best_fit = M.cognitive_fitness(pool[0], W_COG)
                best_g = pool[0]["model"].genome.clone()
            elites = [ag["model"].genome.clone() for ag in pool[:n_elite]]
            if era == BRAS[bras]["marque_logit"]:
                lm = logit_median_at_outputs(elites, PAIRES_REL)     # DV mecaniste calibree
                if lm["n_failed"]:
                    print(f"    ! |logit| : {lm['n_failed']} echec(s) : {lm['failures']}")
                logit_med = lm["median"]
            if era == max(fen):
                portage_fin = sum(_porte_arete(g) for g in elites)
            if era == eras:
                last_top1 = pool[0]["model"].genome.clone()          # lecture SECONDAIRE (panel, faille a)
            children = []
            while len(children) < POP - len(elites):
                children.append(apply_mutations(elites[np.random.randint(len(elites))], mc))
            genomes = elites + children
        return {"aborted": False, "extinct": False, "reached": eras, "genome": best_g,
                "last_top1": last_top1, "hits": _etat["hits"] - h0, "ages": ages,
                "logit_med": logit_med, "portage_fin": portage_fin,
                "N": best_g.num_nodes, "t_eres": t_eres}

    def sal_par_paire(genome, seed):
        """Saillance PAR paire cible (taux per-paire publies -- dette d'ancre d'EVO-027)."""
        return {f"{c}->{rel}": float(M.measure_decision_saliency(genome, seed, channel=c,
                                                                 out_idx=rel, tasks=TASKS))
                for c, rel in PAIRES_REL}

    # ---- RUN --------------------------------------------------------------------------------------
    out, t_bras = {}, {}
    try:
        for bras in ("EARLY", "LATE"):
            print(f"--- bras {bras} (biais {min(BRAS[bras]['bias'])}-{max(BRAS[bras]['bias'])}, "
                  f"run {BRAS[bras]['eras']} eres, n={N_SEEDS}) ---")
            rows, t0b = [], time.time()
            for s in range(N_SEEDS):
                t0 = time.time()
                try:
                    r = evolve(s, bras)
                except CostExceeded as e:
                    print(f"  seed {s:>2}: ABANDONNE (cout wall-clock) : {e}")
                    rows.append({"aborted": True, "why": "cost"})
                    continue
                if r.get("aborted"):
                    print(f"  seed {s:>2}: ABANDONNE (budget agent-ticks) apres {r['reached']} eres")
                    rows.append({"aborted": True, "why": "ticks"})
                    continue
                pp = sal_par_paire(r["genome"], 2000 + s)
                sal = max(pp.values())
                sal_last = (max(sal_par_paire(r["last_top1"], 2000 + s).values())
                            if r["last_top1"] is not None else float("nan"))
                _persist(bras, s, "best", r["genome"])
                if r["last_top1"] is not None:
                    _persist(bras, s, "last", r["last_top1"])
                queue = r["ages"][-max(1, len(r["ages"]) // 10):] if r["ages"] else [0.0]
                rows.append({"seed": s, "sal": sal, "sal_last": sal_last, "paires": pp,
                             "hits": r["hits"], "N": r["N"], "age_fin": statistics.median(queue),
                             "extinct": r["extinct"], "logit_med": r["logit_med"],
                             "portage_fin": r["portage_fin"]})
                flag = "   <<< LECTEUR" if sal > 0.5 else ""
                print(f"  seed {s:>2}: sal={sal:.3f} sal_last={sal_last:.3f} hits={r['hits']:>3} "
                      f"portage_fin={r['portage_fin']}/7 |logit|={r['logit_med']:.2f} "
                      f"age_fin={statistics.median(queue):.1f} N={r['N']} [{time.time()-t0:.0f}s]{flag}")
                if SMOKE:
                    te = r["t_eres"]
                    print(f"    chrono/ere : min={min(te):.2f}s med={statistics.median(te):.2f}s "
                          f"max={max(te):.2f}s total={sum(te):.1f}s "
                          f"(15 premieres : {' '.join(f'{t:.1f}' for t in te[:15])})")
            t_bras[bras] = time.time() - t0b
            out[bras] = [r for r in rows if not r.get("aborted")]
            print(f"  abandons {bras} : {sum(1 for r in rows if r.get('aborted'))} "
                  f"(comptes, jamais silencieux)")
    finally:
        MUT.add_connection = _orig_add_connection      # l'operateur d'origine est TOUJOURS restaure

    if SMOKE:
        tp = t_bras["EARLY"] + t_bras["LATE"]
        print(f"\n=== EVO-028-SMOKE === t_EARLY={t_bras['EARLY']:.1f}s t_LATE={t_bras['LATE']:.1f}s "
              f"t_pair={tp:.1f}s")
        n86, n74 = tp * 86, tp * 74
        print(f"projection totale : n=86 -> {n86:.0f}s ({n86/3600:.2f}h) | n=74 -> {n74:.0f}s | "
              f"plafond scelle {PLAFOND_TOTAL_S:.0f}s")
        if tp <= 134:
            print("-> branche scellee « t_pair <= 134 s » : GO run principal n=86/bras.")
        elif tp <= 155:
            print("-> branche scellee « 134 < t_pair <= 155 s » : REPLI n=74/bras "
                  "(reecrire la regle sur 0.800/0.729 AVANT le run).")
        else:
            print("-> branche scellee « t_pair > 155 s » : dernier barreau h=5 calibre, sinon NO-GO cout.")
        raise SystemExit(0)

    # ---- LECTURE (run principal ; ordre scelle par EVO-028.json) ----------------------------------
    print("\n=== EVO-028 ===")
    print(f"{'bras':>6} | {'LECTEURS':>9} | {'sal med':>8} | {'hits med':>8} | {'portage':>8} | "
          f"{'age_fin':>8} | {'N med':>6} | abandons")
    for bras in ("EARLY", "LATE"):
        rr = out[bras]
        if not rr:
            print(f"{bras:>6} | tous abandonnes")
            continue
        rd = [r for r in rr if r["sal"] > 0.5]
        print(f"{bras:>6} | {len(rd):>4}/{len(rr):<4} | "
              f"{statistics.median([r['sal'] for r in rr]):>8.3f} | "
              f"{statistics.median([r['hits'] for r in rr]):>8.0f} | "
              f"{statistics.median([r['portage_fin'] or 0 for r in rr]):>6.0f}/7 | "
              f"{statistics.median([r['age_fin'] for r in rr]):>8.1f} | "
              f"{statistics.median([r['N'] for r in rr]):>6.0f} | {N_SEEDS - len(rr)}")
        # taux PER-PAIRE (la dette d'ancre d'EVO-027 ne se recree pas)
        for c, rel in PAIRES_REL:
            k = f"{c}->{rel}"
            n_lu = sum(1 for r in rr if r["paires"][k] > 0.5)
            print(f"         paire {k:>7} : {n_lu}/{len(rr)}")
        div = sum(1 for r in rr if (r["sal"] > 0.5) != (r["sal_last"] > 0.5))
        print(f"         lecture secondaire (top-1 derniere ere) : {div} divergence(s) best-ever/last "
              f"{'-- ANOMALIE INSTRUMENT (>3, a signaler)' if div > 3 else ''}")

    if not out["EARLY"] or not out["LATE"]:
        print("\n  RUN NON LISIBLE : un bras est vide.")
        raise SystemExit(0)

    # ---- CONTROLES DE MANIPULATION (clause scellee), AVANT tout verdict ---------------------------
    he = statistics.median([r["hits"] for r in out["EARLY"]])
    hl = statistics.median([r["hits"] for r in out["LATE"]])
    ne_ = statistics.median([r["N"] for r in out["EARLY"]])
    nl = statistics.median([r["N"] for r in out["LATE"]])
    ae = statistics.median([r["age_fin"] for r in out["EARLY"]])
    al = statistics.median([r["age_fin"] for r in out["LATE"]])
    print("\n  CONTROLES (in situ) :")
    ok = True
    print(f"    (1) hits : EARLY={he:.0f} LATE={hl:.0f} ratio={hl/max(he,1e-9):.2f} (clause [0.7,1.4])")
    if he <= 0 or hl <= 0 or not (0.7 <= hl / max(he, 1e-9) <= 1.4):
        print("        ECHEC"); ok = False
    pe = statistics.median([r["portage_fin"] or 0 for r in out["EARLY"]])
    pl = statistics.median([r["portage_fin"] or 0 for r in out["LATE"]])
    print(f"    (2) portage fin de fenetre : EARLY={pe:.0f}/7 LATE={pl:.0f}/7 (rapporte)")
    print(f"    (3) N median : {ne_:.0f} vs {nl:.0f} (clause |ecart|<=2)")
    if abs(ne_ - nl) > 2:
        print("        ECHEC"); ok = False
    print(f"    (4) sante : age_fin LATE/EARLY = {al/max(ae,1e-9):.2f} (clause >= 0.70)")
    sante_ok = al >= 0.70 * ae
    a = sum(1 for r in out["EARLY"] if r["sal"] > 0.5)
    seuil_pos = max(1, round(29 / 86 * N_SEEDS))       # transposition du 8/24 d'EVO-027
    print(f"    (5) controle positif interne : EARLY = {a}/{len(out['EARLY'])} (clause >= {seuil_pos})")
    if a < seuil_pos:
        print("        ECHEC harnais"); ok = False
    if not ok:
        print("\n  -> AUCUN VERDICT : le dispositif n'a pas fait ce qu'il annonce.")
        raise SystemExit(0)

    b_ = len(out["EARLY"]) - a
    c_ = sum(1 for r in out["LATE"] if r["sal"] > 0.5)
    d = len(out["LATE"]) - c_
    n_tot = a + b_ + c_ + d

    def pf(x1, x2, x3, x4):
        return comb(x1 + x2, x1) * comb(x3 + x4, x3) / comb(n_tot, x1 + x3)

    obs = pf(a, b_, c_, d)
    p = sum(pf(x, a + b_ - x, a + c_ - x, d - a + x)
            for x in range(max(0, a + c_ - (c_ + d)), min(a + b_, a + c_) + 1)
            if pf(x, a + b_ - x, a + c_ - x, d - a + x) <= obs + 1e-12)
    print(f"\n  Fisher exact bilateral EARLY {a}/{a+b_} vs LATE {c_}/{c_+d} : p = {p:.4f}")
    if p < 0.05 and a / max(a + b_, 1) > c_ / max(c_ + d, 1):
        if sante_ok:
            print("  -> branche scellee : DEPENDANCE FAIBLE ETABLIE (rapporter ratio + IC exact ; "
                  "mecanisme B-M1/M2 dans les DV mecanistes, sans poids).")
        else:
            print("  -> branche scellee : attribue a la DEGRADATION (sante < 0.70), aucun modele departage.")
    elif p < 0.05:
        print("  -> branche scellee : LATE > EARLY, inattendu -- rapporter tel quel.")
    else:
        print("  -> branche scellee : p >= 0.05 -> r <= 0.818 REFUTE (beta=0.196 ; r<=0.75 a 0.037). "
              "Combine a la cloture (0.818;1.0) sur cout : question FERMEE definitivement.")
