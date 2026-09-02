"""EVO-027 -- la CONVERSION d'un tirage reussi depend-elle de sa POSITION dans l'historique ?

MODELE A (rarete combinatoire) : un hit delivre convertit pareil tot ou tard -> LATE ~ EARLY.
MODELE B (non-accumulation ; EVO-012 : |logit| des elites gele a 9-12.5 vs w~N(0,1)) : un hit tardif
est phenotypiquement neutre, detruit par la coupe top-7/30 -> LATE << EARLY.

Design du panel 2026-09-02 (3 juges + refutateur) apres l'abandon PROUVE de D2-bis (identite
1-(1-p)^N : la largeur ne discrimine rien). Le levier est le biais d'EVO-009 -- le seul qui ait jamais
deplace le taux (12/12, Fisher p=9.6e-6) -- actif dans une FENETRE de 15 eres dont on varie la position :
  EARLY : biais eres 1-15, run jusqu'a 30.   LATE : propre 1-20, biais 21-35, run jusqu'a 50.
Horizon post-fenetre APPARIE (15 eres sans biais chacun) : la retention non assistee s'annule.

⚠️ Ecrit EXPLICITEMENT, pas derive d'un runner precedent (registre E4 occ.4).
⚠️ Croissance de noeuds COUPEE dans les deux bras (N constant, lecon EVO-026) + preserve_io_blocks=True.
Regle scellee : docs/preregistrations/EVO-027.json (lecture CONTINUE, Fisher calcule ici).

    PYTHONPATH=. python -u tools/evo_runs/evo027_run.py
"""
import os
import statistics
import time
from math import comb

import numpy as np
from tools.jobs.run import hold

N_SEEDS = 24
TICKS = 120
POP = 30
W_COG = 5000.0
FEN = 15                                  # largeur de la fenetre de biais
BRAS = {"EARLY": {"bias": range(1, 16), "eras": 30, "marque_logit": 5},
        "LATE":  {"bias": range(21, 36), "eras": 50, "marque_logit": 25}}
TICKS_PER_ERA_BUDGET = 60_000 / 35        # meme generosite par ere (E13, anti-censure differentielle)

with hold("kuzu", owner="evo027-position", ttl_s=14400):
    from tools.preregister import verify
    import tools.evo_cognitive_objective as M
    import src.seed_ai.mutation as MUT
    from src.seed_ai.mutation import MutationConfig, apply_mutations
    from tools.evo_mech_dv import logit_median_at_outputs

    rule = verify("EVO-027")
    print("regle SCELLEE verifiee |", rule["dv_primaire"][:90], "\n")

    TASKS = M.TASKS_EVO006
    # Paires cibles = cablage canonique de synthetic_reader pour (move, throw, accept) :
    # SIG_COLS[0]=5 -> {ACT_POS, ACT_NEG} (move exige de gagner l'argmax), SIG_COLS[1]=10 -> THROW_IDX,
    # SIG_COLS[2]=23 -> ACCEPT_IDX. Sorties en indice RELATIF au bloc (o = N - num_outputs), lecon du
    # compteur negatif d'EVO-019.
    PAIRES_REL = ((M.SIG_COLS[0], M.ACT_POS), (M.SIG_COLS[0], M.ACT_NEG),
                  (M.SIG_COLS[1], M.THROW_IDX), (M.SIG_COLS[2], M.ACCEPT_IDX))

    # ---- l'operateur biaise d'EVO-009, fenetre pilotee par un drapeau -----------------------------
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
        mc.preserve_io_blocks = True      # EDR-EVO-024
        mc.add_node_rate = 0.0            # N constant (lecon EVO-026 : denominateur fixe)
        mc.meso_gate_rate = 0.0
        mc.meso_skip_rate = 0.0
        return mc

    def _porte_arete(genome):
        """L'arete cible est-elle PRESENTE ? Lecture numpy pure, indices relatifs."""
        o = genome.num_nodes - genome.num_outputs
        return any(genome.W[c, o + out] != 0 for c, out in PAIRES_REL
                   if c < genome.num_nodes and o + out < genome.num_nodes)

    # |logit| : DV mecaniste REPAREE (2026-09-02) -> tools/evo_mech_dv.py, calibree.
    # L'ancien helper in-run passait H_prev=None a recurrent_forward (None.copy() leve) et
    # AVALAIT l'echec (except: continue) -> nan muet sur TOUT le run d'EVO-027. Forme (b) du
    # biais negatif systematique. Le bug est devenu un cas de calibration.

    def evolve(seed, bras):
        np.random.seed(seed)
        cfg = M._cfg()
        mc = _mc()
        eras, fen = BRAS[bras]["eras"], BRAS[bras]["bias"]
        budget = eras * TICKS_PER_ERA_BUDGET
        genomes = M._fresh_soup(POP, cfg, 0.0)
        n_elite = max(3, POP // 4)
        best_g, best_fit = genomes[0].clone(), -1e18
        h0 = _etat["hits"]
        ages, spent, logit_med, portage_fin = [], 0, float("nan"), None
        for era in range(1, eras + 1):
            if spent > budget:
                return {"aborted": True, "reached": era}
            _etat["on"] = era in fen
            _, pool = M._run_era(genomes, cfg, TICKS, era, inject=True, K=1, tasks=TASKS)
            _etat["on"] = False
            spent += sum(int(a.get("age", 0)) for a in pool)
            if not pool:
                return {"aborted": False, "extinct": True, "reached": era, "genome": best_g,
                        "hits": _etat["hits"] - h0, "ages": ages, "logit_med": logit_med,
                        "portage_fin": portage_fin, "N": best_g.num_nodes}
            ages.append(statistics.median([int(a.get("age", 0)) for a in pool]))
            pool.sort(key=lambda ag: M.cognitive_fitness(ag, W_COG), reverse=True)
            if M.cognitive_fitness(pool[0], W_COG) > best_fit:
                best_fit = M.cognitive_fitness(pool[0], W_COG)
                best_g = pool[0]["model"].genome.clone()
            elites = [ag["model"].genome.clone() for ag in pool[:n_elite]]
            if era == BRAS[bras]["marque_logit"]:
                lm = logit_median_at_outputs(elites, PAIRES_REL)   # DV mecaniste reparee, calibree
                if lm["n_failed"]:
                    print(f"    ! |logit| : {lm['n_failed']} forward(s) en echec : {lm['failures']}")
                logit_med = lm["median"]
            if era == max(fen):
                portage_fin = sum(_porte_arete(g) for g in elites)   # controle (2) : fin de fenetre
            children = []
            while len(children) < POP - len(elites):
                children.append(apply_mutations(elites[np.random.randint(len(elites))], mc))
            genomes = elites + children
        return {"aborted": False, "extinct": False, "reached": eras, "genome": best_g,
                "hits": _etat["hits"] - h0, "ages": ages, "logit_med": logit_med,
                "portage_fin": portage_fin, "N": best_g.num_nodes}

    def saillance_max(genome, seed):
        """DV primaire : max de saillance sur les paires cibles (la « sous-tache la plus haute »)."""
        best = 0.0
        for c, rel in PAIRES_REL:
            s = M.measure_decision_saliency(genome, seed, channel=c, out_idx=rel, tasks=TASKS)
            best = max(best, float(s))
        return best

    PERSIST_DIR = os.path.join("data", "genomes", "evo027")

    def _persist_champion(bras, seed, g):
        """Dette recurrente « persister les genomes entraines » (CLAUDE.md) : la DV d'injection
        d'EVO-027 a ete PERDUE faute de champions persistes. W + dimensions suffisent a un forward pur."""
        os.makedirs(PERSIST_DIR, exist_ok=True)
        np.savez_compressed(os.path.join(PERSIST_DIR, f"{bras.lower()}_seed{seed}.npz"),
                            W=g.W, num_inputs=g.num_inputs, num_outputs=g.num_outputs,
                            num_nodes=g.num_nodes)

    # ---- RUN ---------------------------------------------------------------------------------------
    out = {}
    try:
        for bras in ("EARLY", "LATE"):
            print(f"--- bras {bras} (biais eres {min(BRAS[bras]['bias'])}-{max(BRAS[bras]['bias'])}, "
                  f"run {BRAS[bras]['eras']} eres) ---")
            rows = []
            for s in range(N_SEEDS):
                t0 = time.time()
                r = evolve(s, bras)
                if r.get("aborted"):
                    print(f"  seed {s:>2}: ABANDONNE (budget) apres {r['reached']} eres")
                    rows.append({"aborted": True})
                    continue
                sal = saillance_max(r["genome"], 2000 + s)
                _persist_champion(bras, s, r["genome"])    # plus jamais un run sans ses champions
                queue = r["ages"][-max(1, len(r["ages"]) // 10):] if r["ages"] else [0.0]
                rows.append({"seed": s, "sal": sal, "hits": r["hits"], "N": r["N"],
                             "age_fin": statistics.median(queue), "extinct": r["extinct"],
                             "logit_med": r["logit_med"], "portage_fin": r["portage_fin"]})
                flag = "   <<< LECTEUR" if sal > 0.5 else ""
                print(f"  seed {s:>2}: sal={sal:.3f} hits={r['hits']:>3} portage_fin={r['portage_fin']}"
                      f"/7 |logit|={r['logit_med']:.2f} age_fin={statistics.median(queue):.1f} "
                      f"N={r['N']} [{time.time()-t0:.0f}s]{flag}")
            out[bras] = [r for r in rows if not r.get("aborted")]
    finally:
        MUT.add_connection = _orig_add_connection          # l'operateur d'origine est TOUJOURS restaure

    print("\n=== EVO-027 ===")
    print(f"{'bras':>6} | {'LECTEURS':>9} | {'sal med':>8} | {'hits med':>8} | {'portage':>8} | "
          f"{'|logit| med':>11} | {'age_fin':>8} | {'N med':>6} | abandons")
    for bras in ("EARLY", "LATE"):
        rr = out[bras]
        if not rr:
            print(f"{bras:>6} | tous abandonnes")
            continue
        rd = [r for r in rr if r["sal"] > 0.5]
        print(f"{bras:>6} | {len(rd):>4}/{len(rr):<4} | {statistics.median([r['sal'] for r in rr]):>8.3f} | "
              f"{statistics.median([r['hits'] for r in rr]):>8.0f} | "
              f"{statistics.median([r['portage_fin'] or 0 for r in rr]):>6.0f}/7 | "
              f"{statistics.median([r['logit_med'] for r in rr]):>11.2f} | "
              f"{statistics.median([r['age_fin'] for r in rr]):>8.1f} | "
              f"{statistics.median([r['N'] for r in rr]):>6.0f} | {N_SEEDS - len(rr)}")

    if not out["EARLY"] or not out["LATE"]:
        print("\n  RUN NON LISIBLE : un bras est vide.")
        raise SystemExit(0)

    # ---- CONTROLES DE MANIPULATION (clause scellee), AVANT tout verdict -----------------------------
    he = statistics.median([r["hits"] for r in out["EARLY"]])
    hl = statistics.median([r["hits"] for r in out["LATE"]])
    ne_, nl = statistics.median([r["N"] for r in out["EARLY"]]), statistics.median([r["N"] for r in out["LATE"]])
    ae, al = statistics.median([r["age_fin"] for r in out["EARLY"]]), statistics.median([r["age_fin"] for r in out["LATE"]])
    print("\n  CONTROLES (in situ) :")
    ok = True
    print(f"    (1) hits delivres : EARLY={he:.0f} LATE={hl:.0f} ratio={hl/max(he,1e-9):.2f} (clause [0.7,1.4])")
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
    if not ok:
        print("\n  -> AUCUN VERDICT : le dispositif n'a pas fait ce qu'il annonce.")
        raise SystemExit(0)

    a = sum(1 for r in out["EARLY"] if r["sal"] > 0.5)
    b_ = len(out["EARLY"]) - a
    c_ = sum(1 for r in out["LATE"] if r["sal"] > 0.5)
    d = len(out["LATE"]) - c_
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
    print(f"\n  Fisher exact bilateral EARLY({a}/{a+b_}) vs LATE({c_}/{c_+d}) : p = {p:.4f}")

    # ---- lecture SCELLEE, dans l'ordre impose -------------------------------------------------------
    if a < 8:
        print("  -> (0b) EARLY < 8/24 : le HARNAIS echoue son controle positif interne "
              "(la config croissance-coupee n'est pas celle d'EVO-009). AUCUN verdict A/B.")
    elif p < 0.05 and a > c_:
        if sante_ok:
            print("  -> MODELE B : la valeur d'un tirage DEPEND de l'historique de la recherche. "
                  "« Le verrou est le tirage » = NON-COMPOSITION ; l'echelle ne suffit pas.")
        else:
            print("  -> LATE < EARLY mais sante < 0.70 : ATTRIBUE A LA DEGRADATION, aucun modele departage.")
    elif p < 0.05:
        print("  -> INATTENDU : LATE > EARLY. A rapporter tel quel.")
    else:
        if a >= 12:
            print("  -> MODELE A (dependance FORTE refutee) : un hit tardif convertit comme un hit "
                  "precoce ; la cloture se relit « le verrou est le NOMBRE de tirages » -- l'echec des "
                  "designs a taux naturels (EVO-019/020) reste attribue a la DILUTION.")
        else:
            print("  -> EARLY dans [8,11]/24 : puissance insuffisante (limite scellee), pas de verdict.")
    print("\n  PUISSANCE declaree :", rule["puissance_declaree"][:150])
