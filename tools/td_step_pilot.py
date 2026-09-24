"""TD-STEP-PILOT-R0 (P4.11, ADR-005 item 1, 2026-09-16) — le crédit TD PAR PAS (`forward` + `learn` à chaque pas,
récompense 0 puis ±1 au dernier pas, `TorchPopulationModel._td_update`) apprend-il la composition DIFFÉRÉE
`(q+key)%K` à D=1 (key au pas 0, q au pas 1) — et la trace d'éligibilité TD(λ) (`CREDIT_TRACE_LAMBDA`) change-t-elle
la réponse ? C'est le LIEU correct de l'issue positive de P4.11 : `_td_update` ne tourne aujourd'hui qu'in-world
(tâche same-tick), et la voie épisodique (`learn_episode`, LOCK-002) ne passe jamais par lui.

Réponses connues à MESURER, pas à raisonner : (1) TD(0) par pas à D=1 — la récompense du pas 1 ne peut pas façonner
l'ÉCRITURE de key au pas 0 sans BPTT (H_in est détaché dans `_td_update`), mais la LECTURE de l'état porté (H1 =
projection aléatoire de key par W) reste apprenable : les deux issues sont ouvertes ; (2) trace λ = 0,9 (traces remises
à zéro à chaque épisode, publié) ; (3) contrôle positif APPARIÉ sur la même tâche et le même substrat : BPTT supervisé
2 pas (`_train_eval_one(bilinear=True, same_tick=False, credit_mode="supervised")`, 0,923 publié à lr 0,002 dans
`results/retain_compose_lr_replication.json`) — le substrat est BILINÉAIRE pour les quatre bras : la fumée seed 0 a
mesuré que le plain n'atteint pas 0,5 en BPTT 2 pas à ce budget (0,21 / 0,27), donc un bras TD plain ne pourrait pas
réussir (E1) ; la trace couvre W, U, V, W_bl ; (4) référence lr=0 du même dispositif
(barre = référence + 0,05, jamais « chance + marge »). Deux pas par bras (E19). Aucun monde, aucun bail, CPU pur.
Résultats : `results/td_step_pilot_r0.json`. Usage : python tools/td_step_pilot.py [--lecture]
"""
import copy
import json
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.bilinear_composition_probe import _make_seq, _sample, _train_eval_one
from tools.experiment_preflight import assert_control_family, declare_design
from tools.preregister import stamp, verify
from tools.cost_guard import Stopwatch          # P2.78 : mur ET CPU
from tools.cost_guard import (COEURS_EXTERIEURS_LIBRE_MAX, CostTooHighToStart, LoadWindow,  # P2.110 : main_r2 seul
                              classify_cut_nature, cost_per_arm, cut_geometry, cut_record, margin_to_budget,
                              project_cost)
from src.paths import results_file   # noqa: E402  (porte 12)

RULE = "TD-STEP-PILOT-R0"


def _flush_terminal(agent, n):
    """Fin d'épisode : la dernière transition n'a pas d'état suivant, V(s') = 0. `learn` n'a pas de drapeau
    terminal (signature intacte, cond. ii) : on applique la mise à jour différée avec un bootstrap NUL, par le
    MÊME chemin (`_td_update`, donc la trace si λ > 0), puis on efface la transition. Explicite, jamais un
    bootstrap silencieux sur l'épisode suivant."""
    import torch
    if agent._prev is not None:
        agent._td_update(agent._prev, torch.zeros(n, device=agent.device))
        agent._prev = None


_N_AGENTS_GRILLE = 16   # `cellule.n_agents` des trois regles scellees R0/R1/R2
_N_GRILLE = 40 * _N_AGENTS_GRILLE      # 640 evaluations : le pas de la grille est 1/640
_EVAL_BATCHES = 40      # défaut de `_train_eval_td_step`, jamais surchargé -> grille = 40 × n_agents = 640


def _cmp_grille(x, y, marge, n_grille, sens=1):
    """`x > y + marge` (sens=+1) ou `x < y − marge` (sens=−1), comparé en UNITÉS DE GRILLE (2026-09-24, E14 :
    rétro-application le jour même du correctif de `bilinear_sham_run::_sous_barre`).

    L'accuracy est un COMPTE sur `n_grille` = `eval_batches × n_agents` = 640 évaluations : ses valeurs sont des
    multiples exacts de 1/640, la marge scellée 0,05 vaut EXACTEMENT 32 pas, et float32 les rend décalées de
    ~2e-6 (0,184375 revient 0,18437500298023224). Un critère à seuil comme « ≥ 10/12 » peut donc basculer sur une
    seule ÉGALITÉ perdue — et elle se perd TOUJOURS du côté qui refuse. Vérifié par la revue d'agagi-52 : les
    17 comptes publiés de R0/R1/R2 sont IDENTIQUES dans les deux arithmétiques et aucune égalité exacte n'est
    survenue jusqu'ici ; le défaut était LATENT, et les 48 cellules neuves de la reprise pouvaient le réaliser.
    Repli DÉCLARÉ (comparaison ordinaire) si une valeur ou la marge n'est pas commensurable au pas."""
    a, b, m = x * n_grille, y * n_grille, marge * n_grille
    ra, rb, rm = round(a), round(b), round(m)
    if max(abs(ra - a), abs(rb - b), abs(rm - m)) > 1e-3:
        return (x > y + marge) if sens > 0 else (x < y - marge)
    return (ra > rb + rm) if sens > 0 else (ra < rb - rm)


def _train_eval_td_step(seed, lam, episodes, n_agents, K, lr, eval_batches=40, trace_reset_per_episode=True,
                        same_tick=False):
    """Entraîne la composition (différée 2 pas ; ou same-tick 1 pas = contrôle positif du CHEMIN de crédit : sans
    délai, TD par pas doit pouvoir apprendre à cette dose, sinon un nul à D=1 ne dit rien du délai) par crédit TD
    PAR PAS ; rend (accuracy éval argmax, dose)."""
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend_torch import TorchPopulationModel as T
    saved = (T.CONDITION_GATE, T.GATE_TARGET, T.BILINEAR, T.BILINEAR_RANK, T.CREDIT_TRACE_LAMBDA,
             T.CREDIT_TRACE_BYPASS_OPTIMIZER)
    T.CONDITION_GATE, T.GATE_TARGET = False, None
    T.BILINEAR = True                                    # épinglé : substrat du contrôle positif ; W, U, V, W_bl tracés
    T.BILINEAR_RANK = 16
    T.CREDIT_TRACE_LAMBDA = float(lam)
    T.CREDIT_TRACE_BYPASS_OPTIMIZER = False              # SGD pur : rien à contourner
    try:
        np.random.seed(seed)
        torch.manual_seed(seed)
        agent = T([MambaAgent() for _ in range(n_agents)], lr=lr)
        I = agent.I
        rng = np.random.RandomState(seed + 1)
        updates = 0
        for _ in range(episodes):
            key = rng.randint(0, K, size=n_agents)
            q = rng.randint(0, K, size=n_agents)
            seq, _ = _make_seq(key, q, "composition", K, I, n_agents, same_tick=same_tick)
            tgt = (q + key) % K
            agent.H = torch.zeros((n_agents, agent.N))       # nouvelle vie : état et transition à zéro
            agent._prev = None
            if trace_reset_per_episode:
                agent.reset_traces()
            for t, x in enumerate(seq):
                logits, _ = agent.forward(x)
                a = _sample(logits, K, rng, n_agents)        # pas encode : action de nuisance, récompense 0
                dernier = t == len(seq) - 1
                r = np.where(a == tgt, 1.0, -1.0).astype(np.float32) if dernier else np.zeros(n_agents, np.float32)
                if agent.learn(r, [{"move": int(g)} for g in a]) is not None:
                    updates += 1                            # transition t-1, bootstrap V(s_t)
            _flush_terminal(agent, n_agents)                # dernière transition, bootstrap 0
            updates += 1
        hits = []
        for _ in range(eval_batches):
            key = rng.randint(0, K, size=n_agents)
            q = rng.randint(0, K, size=n_agents)
            seq, _ = _make_seq(key, q, "composition", K, I, n_agents, same_tick=same_tick)
            agent.H = torch.zeros((n_agents, agent.N))
            logits = None
            for x in seq:
                logits, _ = agent.forward(x)
            hits.append((np.asarray(logits)[:, :K].argmax(axis=1) == (q + key) % K).astype(np.float32))
        dose = {"updates": int(updates), "trace_updates": int(agent.trace_updates),
                "trace_resets": int(agent.trace_resets), "lr_effective_per_agent": agent.effective_lr_per_agent}
        return float(np.mean(np.concatenate(hits))), dose
    finally:
        (T.CONDITION_GATE, T.GATE_TARGET, T.BILINEAR, T.BILINEAR_RANK, T.CREDIT_TRACE_LAMBDA,
         T.CREDIT_TRACE_BYPASS_OPTIMIZER) = saved


def _cell(bras, seed, c, lr_idx):
    """Une cellule : (accuracy, dose). Les bras TD partagent le régime ; `bptt` est le contrôle positif apparié."""
    if bras == "bptt":
        acc = _train_eval_one(seed=seed, bilinear=True, task="composition", episodes=c["episodes_bptt"],
                              n_agents=c["n_agents"], K=c["K"], lr=c["lr_bptt"][lr_idx], rank=16,
                              same_tick=False, credit_mode="supervised")
        return float(acc), {"updates": int(c["episodes_bptt"]), "optimiseur": "Adam"}
    lam = c["lambda"] if bras == "tdlam" else 0.0
    lr = 0.0 if bras.startswith("lr0_reference") else c["lr_td"][lr_idx]
    acc, dose = _train_eval_td_step(seed, lam, c["episodes_td"], c["n_agents"], c["K"], lr,
                                    trace_reset_per_episode=c["trace_reset_per_episode"],
                                    same_tick=bras.endswith("_d0"))
    dose["optimiseur"] = "SGD"
    return acc, dose


def _lecture(db, regle):
    """Branche scellée, ORDRE IMPOSÉ. Ne lit que des cellules présentes."""
    c, s = regle["cellule"], regle["seuils"]
    seeds = c["seeds"]
    attendu = [f"{b}|lr{i}|seed={sd}" for b in c["bras"] for i in range(2) for sd in seeds]
    manquantes = [k for k in attendu if k not in db]
    if manquantes:
        return {"branche": "INCOMPLET", "manquantes": len(manquantes)}

    def med(b, i):
        return float(np.median([db[f"{b}|lr{i}|seed={sd}"] for sd in seeds]))

    def n_sup(b, ref, i, marge):
        return sum(1 for sd in seeds
                   if _cmp_grille(db[f"{b}|lr{i}|seed={sd}"], db[f"{ref}|lr{i}|seed={sd}"], marge, _N_GRILLE))

    def n_inf(b, ref, i, marge):
        return sum(1 for sd in seeds
                   if _cmp_grille(db[f"{b}|lr{i}|seed={sd}"], db[f"{ref}|lr{i}|seed={sd}"], marge, _N_GRILLE, sens=-1))
    out = {f"mediane_{b}_lr{i}": med(b, i) for b in c["bras"] for i in range(2)}
    out["td0_sup_ref"] = [f"{n_sup('td0', 'lr0_reference', i, s['marge'])}/{len(seeds)}" for i in range(2)]
    out["td0_d0_sup_ref_d0"] = [f"{n_sup('td0_d0', 'lr0_reference_d0', i, s['marge'])}/{len(seeds)}" for i in range(2)]
    out["tdlam_sup_td0"] = [f"{n_sup('tdlam', 'td0', i, s['marge'])}/{len(seeds)}" for i in range(2)]
    out["tdlam_inf_td0"] = [f"{n_inf('tdlam', 'td0', i, s['marge'])}/{len(seeds)}" for i in range(2)]
    if max(med("bptt", 0), med("bptt", 1)) < s["barre_controle_positif"]:
        out["branche"] = "CONTROLE_SUBSTRAT_ECHOUE"
        return out
    if all(n_sup("td0_d0", "lr0_reference_d0", i, s["marge"]) < s["seeds_min"] for i in range(2)):
        out["branche"] = "CONTROLE_CHEMIN_ECHOUE"
        return out
    td0 = "TD0_APPREND" if any(n_sup("td0", "lr0_reference", i, s["marge"]) >= s["seeds_min"]
                               for i in range(2)) else "TD0_INERTE"
    if any(n_sup("tdlam", "td0", i, s["marge"]) >= s["seeds_min"] for i in range(2)):
        tr = "TRACE_AIDE"
    elif any(n_inf("tdlam", "td0", i, s["marge"]) >= s["seeds_min"] for i in range(2)):
        tr = "TRACE_NUIT"
    else:
        tr = "TRACE_NEUTRE"
    out["branche"] = f"{td0}|{tr}"
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    regle = verify(RULE)
    out_path = str(results_file("td_step_pilot_r0.json"))
    c = regle["cellule"]
    db = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    if "--lecture" in argv:
        print(json.dumps(_lecture(db, regle), indent=1, ensure_ascii=False))
        return db
    design = declare_design(
        question=regle["question"],
        replication_unit="seed (une population de %d agents par cellule ; 6 bras x 2 pas appariés par seed)" % c["n_agents"],
        n_independent=len(c["seeds"]),
        links={"accuracy_td0": "measured", "accuracy_tdlam": "measured", "accuracy_lr0_reference": "measured",
               "accuracy_td0_d0_controle_chemin": "measured", "accuracy_lr0_reference_d0": "measured",
               "accuracy_bptt_controle_substrat": "measured", "dose_par_bras": "measured"},
        cost_estimate=regle["cout"],
        control_family=assert_control_family(cells=len(c["bras"]) * 2 * len(c["seeds"]), alpha_family=0.05))
    db.setdefault("_design", design)
    db.setdefault("_regime", {k: v for k, v in c.items() if k != "seeds"})
    db.setdefault("_dose", {})
    sw = Stopwatch()
    for i in range(2):
        for sd in c["seeds"]:
            for b in c["bras"]:
                k = f"{b}|lr{i}|seed={sd}"
                if k in db:
                    continue
                tc = time.time()
                acc, dose = _cell(b, sd, c, i)
                db[k] = acc
                db["_dose"][k] = dose
                json.dump(stamp(db, RULE), open(out_path, "w", encoding="utf-8"), indent=1)
                print(f"  {k}: {acc:.3f} ({time.time() - tc:.1f} s) {dose}", flush=True)
    el = sw.elapsed()                                        # P2.78 : mur et CPU, accumules (run reprenable)
    db["_cout_s"] = db.get("_cout_s", 0.0) + el["elapsed_s"]
    db["_cout_cpu_s"] = db.get("_cout_cpu_s", 0.0) + el["elapsed_cpu_s"]
    db["_lecture"] = _lecture(db, regle)
    json.dump(stamp(db, RULE), open(out_path, "w", encoding="utf-8"), indent=1)
    print(json.dumps(db["_lecture"], indent=1, ensure_ascii=False))
    print("->", out_path)
    return db


# ----------------------------------------------------------------------------------------------------------------------
# R1 (TD-STEP-PILOT-R1) : invariance du TRACE_AIDE a un troisieme pas (lr 2,0) et dose-reponse en lambda (0,5) au pas 4,0.
# Les cellules du pas 4,0 (td0, tdlam 0,9, lr0_reference) sont IMPORTEES de R0 -- relues, jamais re-mesurees --
# et le sceau de R0 est verifie AVANT lecture. Declare dans la regle (E11).
RULE_R1 = "TD-STEP-PILOT-R1"


def _import_r0(regle):
    """Les cellules importees, relues depuis results/td_step_pilot_r0.json (sceau R0 verifie). Rend {cle R1: valeur}."""
    verify(RULE)                                                   # la regle R0 n'a pas ete retouchee
    r0 = json.load(open(str(results_file("td_step_pilot_r0.json")), encoding="utf-8"))
    out = {}
    for sd in regle["cellule"]["seeds"]:
        out[f"td0@4|seed={sd}"] = r0[f"td0|lr0|seed={sd}"]
        out[f"tdlam09@4|seed={sd}"] = r0[f"tdlam|lr0|seed={sd}"]
        out[f"lr0_reference@4|seed={sd}"] = r0[f"lr0_reference|lr0|seed={sd}"]
    assert r0["_regime"]["lr_td"][0] == regle["cellule"]["lr_importe"] and r0["_regime"]["lambda"] == regle["cellule"]["lambda_importe"]
    return out


def _lecture_r1(db, regle):
    """Deux lectures INDEPENDANTES, publiees ensemble : invariance au pas, dose en lambda. ORDRE IMPOSE."""
    c, s = regle["cellule"], regle["seuils"]
    seeds = c["seeds"]
    attendu = [f"{b}|seed={sd}" for b in c["bras_nouveaux"] + c["bras_importes"] for sd in seeds]
    manquantes = [k for k in attendu if k not in db]
    if manquantes:
        return {"branche": "INCOMPLET", "manquantes": len(manquantes)}

    def med(b):
        return float(np.median([db[f"{b}|seed={sd}"] for sd in seeds]))

    def n_sup(b, ref, marge):
        return sum(1 for sd in seeds if db[f"{b}|seed={sd}"] > db[f"{ref}|seed={sd}"] + marge)
    out = {f"mediane_{b}": med(b) for b in c["bras_nouveaux"] + c["bras_importes"]}
    out["tdlam09@2_sup_td0@2"] = f"{n_sup('tdlam09@2', 'td0@2', s['marge'])}/{len(seeds)}"
    out["td0@2_sup_ref@2"] = f"{n_sup('td0@2', 'lr0_reference@2', s['marge'])}/{len(seeds)}"
    out["tdlam05@4_sup_td0@4"] = f"{n_sup('tdlam05@4', 'td0@4', s['marge'])}/{len(seeds)}"
    out["tdlam09@4_sup_tdlam05@4"] = f"{n_sup('tdlam09@4', 'tdlam05@4', 0.0)}/{len(seeds)}"
    inv = "AIDE_INVARIANTE" if n_sup("tdlam09@2", "td0@2", s["marge"]) >= s["seeds_min"] else "AIDE_NON_INVARIANTE"
    if n_sup("tdlam05@4", "td0@4", s["marge"]) >= s["seeds_min"]:
        dose = "DOSE_LAMBDA_MONOTONE" if n_sup("tdlam09@4", "tdlam05@4", 0.0) >= s["seeds_min"] else "DOSE_LAMBDA_SATUREE"
    else:
        dose = "DOSE_LAMBDA_ABSENTE"
    out["branche"] = f"{inv}|{dose}"
    return out


def main_r1(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    regle = verify(RULE_R1)
    out_path = str(results_file("td_step_pilot_r1.json"))
    c = regle["cellule"]
    db = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    db.update(_import_r0(regle))                                   # relues a chaque appel : jamais figees dans R1
    if "--lecture" in argv:
        print(json.dumps(_lecture_r1(db, regle), indent=1, ensure_ascii=False))
        return db
    design = declare_design(
        question=regle["question"],
        replication_unit="seed (une population de %d agents par cellule ; bras appariés par seed)" % c["n_agents"],
        n_independent=len(c["seeds"]),
        links={"accuracy_td0@2": "measured", "accuracy_tdlam09@2": "measured", "accuracy_lr0_reference@2": "measured",
               "accuracy_tdlam05@4": "measured", "cellules_pas_4_importees_de_R0": "measured"},
        cost_estimate=regle["cout"],
        control_family=assert_control_family(cells=(len(c["bras_nouveaux"]) + len(c["bras_importes"])) * len(c["seeds"]),
                                             alpha_family=0.05))
    db.setdefault("_design", design)
    db.setdefault("_regime", {k: v for k, v in c.items() if k != "seeds"})
    db.setdefault("_dose", {})
    spec = {"td0@2": (0.0, c["lr_nouveau"]), "tdlam09@2": (c["lambda_importe"], c["lr_nouveau"]),
            "lr0_reference@2": (0.0, 0.0), "tdlam05@4": (c["lambda_nouveau"], c["lr_importe"])}
    sw = Stopwatch()
    for sd in c["seeds"]:
        for b in c["bras_nouveaux"]:
            k = f"{b}|seed={sd}"
            if k in db:
                continue
            lam, lr = spec[b]
            tc = time.time()
            acc, dose = _train_eval_td_step(sd, lam, c["episodes_td"], c["n_agents"], c["K"], lr,
                                            trace_reset_per_episode=c["trace_reset_per_episode"])
            db[k], db["_dose"][k] = acc, dose
            json.dump(stamp(db, RULE_R1), open(out_path, "w", encoding="utf-8"), indent=1)
            print(f"  {k}: {acc:.3f} ({time.time() - tc:.1f} s)", flush=True)
    el = sw.elapsed()                                        # P2.78 : mur et CPU, accumules (run reprenable)
    db["_cout_s"] = db.get("_cout_s", 0.0) + el["elapsed_s"]
    db["_cout_cpu_s"] = db.get("_cout_cpu_s", 0.0) + el["elapsed_cpu_s"]
    db["_lecture"] = _lecture_r1(db, regle)
    json.dump(stamp(db, RULE_R1), open(out_path, "w", encoding="utf-8"), indent=1)
    print(json.dumps(db["_lecture"], indent=1, ensure_ascii=False))
    print("->", out_path)
    return db


# ----------------------------------------------------------------------------------------------------------------------
# R2 (TD-STEP-PILOT-R2, P4.17) : grille lr x lambda sur le meme dispositif. Les cellules deja mesurees par R0/R1 sont
# IMPORTEES (relues, jamais re-mesurees, sceaux verifies) ; le garde de cout mesure l'unite sur la premiere cellule
# neuve et COUPE la ligne lr la plus basse si la projection depasse le budget scelle (coupe publiee dans _regime).
RULE_R2 = "TD-STEP-PILOT-R2"
_BRAS_R2 = ("lam0", "lam05", "lam09", "lam099", "td0_d0")


def _import_r2(regle):
    """Cellules importees de R0/R1 sous les cles de R2 (`<bras>|lr=<lr>|seed=<sd>` ; references sans lr)."""
    verify(RULE)
    verify(RULE_R1)
    r0 = json.load(open(str(results_file("td_step_pilot_r0.json")), encoding="utf-8"))
    r1 = json.load(open(str(results_file("td_step_pilot_r1.json")), encoding="utf-8"))
    assert r0["_regime"]["lr_td"][0] == 4.0 and r0["_regime"]["lambda"] == 0.9 and r1["_regime"]["lr_nouveau"] == 2.0
    out = {}
    for sd in regle["cellule"]["seeds"]:
        out[f"lam0|lr=4.0|seed={sd}"] = r0[f"td0|lr0|seed={sd}"]
        out[f"lam05|lr=4.0|seed={sd}"] = r1[f"tdlam05@4|seed={sd}"]
        out[f"lam09|lr=4.0|seed={sd}"] = r0[f"tdlam|lr0|seed={sd}"]
        out[f"td0_d0|lr=4.0|seed={sd}"] = r0[f"td0_d0|lr0|seed={sd}"]
        out[f"lam0|lr=2.0|seed={sd}"] = r1[f"td0@2|seed={sd}"]
        out[f"lam09|lr=2.0|seed={sd}"] = r1[f"tdlam09@2|seed={sd}"]
        out[f"lr0_reference|seed={sd}"] = r0[f"lr0_reference|lr0|seed={sd}"]
        out[f"lr0_reference_d0|seed={sd}"] = r0[f"lr0_reference_d0|lr0|seed={sd}"]
    return out


def _cellules_r2(regle):
    """Toutes les cles de la grille (bras x lr x seed), dans l'ordre de mesure : lr HAUTS d'abord."""
    c = regle["cellule"]
    return [f"{b}|lr={lr}|seed={sd}" for lr in c["lr"] for sd in c["seeds"] for b in _BRAS_R2]


def _lecture_r2(db, regle):
    """Par lr : lisible (chemin), aide09/05/099 (comptes /12), medianes, meilleur lambda ; puis la branche, ORDRE IMPOSE."""
    c, s = regle["cellule"], regle["seuils"]
    seeds, lrs = c["seeds"], c["lr"]
    attendu = _cellules_r2(regle) + [f"{r}|seed={sd}" for r in c["references"] for sd in seeds]
    coupe = set(db.get("_regime", {}).get("coupe", {}).get("cles", []))
    manquantes = [k for k in attendu if k not in db and k not in coupe]
    if manquantes:
        return {"branche": "INCOMPLET", "manquantes": len(manquantes)}

    def med(k):
        return float(np.median([db[f"{k}|seed={sd}"] for sd in seeds]))

    def n_sup(a, b, marge):
        return sum(1 for sd in seeds
                   if _cmp_grille(db[f"{a}|seed={sd}"], db[f"{b}|seed={sd}"], marge, _N_GRILLE))
    out, lisibles, aides = {"par_lr": {}, "lr_coupes": sorted({k.split("|")[1][3:] for k in coupe})}, [], []
    for lr in lrs:
        if any(k in coupe for k in _cellules_r2(regle) if f"|lr={lr}|" in k):
            out["par_lr"][str(lr)] = {"coupe": True}
            continue
        t = f"lr={lr}"
        lisible = n_sup(f"td0_d0|{t}", "lr0_reference_d0", s["marge"]) >= s["seeds_chemin"]
        meds = {lam: med(f"{lam}|{t}") for lam in ("lam0", "lam05", "lam09", "lam099")}
        row = {"lisible": lisible, "td0_d0_sup_ref_d0": f"{n_sup(f'td0_d0|{t}', 'lr0_reference_d0', s['marge'])}/{len(seeds)}",
               "aide09": f"{n_sup(f'lam09|{t}', f'lam0|{t}', s['marge'])}/{len(seeds)}",
               "aide05": f"{n_sup(f'lam05|{t}', f'lam0|{t}', s['marge'])}/{len(seeds)}",
               "aide099": f"{n_sup(f'lam099|{t}', f'lam0|{t}', s['marge'])}/{len(seeds)}",
               "lam0_sup_ref": f"{n_sup(f'lam0|{t}', 'lr0_reference', s['marge'])}/{len(seeds)}",
               "medianes": meds, "meilleur_lambda": max(meds, key=meds.get)}
        out["par_lr"][str(lr)] = row
        if lisible:
            lisibles.append(lr)
            if n_sup(f"lam09|{t}", f"lam0|{t}", s["marge"]) >= s["seeds_aide"]:
                aides.append(lr)
    out["lr_lisibles"], out["lr_aide09"] = lisibles, aides
    if not lisibles:
        out["branche"] = "CONTROLE_CHEMIN_ECHOUE"
        return out
    ordre = [lr for lr in lrs if lr in lisibles]
    adjacents = any(ordre[i] in aides and ordre[i + 1] in aides for i in range(len(ordre) - 1))
    if adjacents:
        out["branche"] = "AIDE_INVARIANTE"
    elif aides:
        out["branche"] = "AIDE_A_UN_POINT"
    else:
        out["branche"] = "PAS_D_AIDE"
    return out


# ---- P2.110 (2026-09-24) : le cliquet de cout de R2 en fonctions PURES ------------------------------------------------
# Trois defauts mesures sur ce runner : (i) `setdefault("coupe", ...)` gardait le dict ecrit par --relever-coupe, donc la
# raison publiee de la coupe COURANTE (60 cles, lr 1,0) etait celle de la LEVEE -- et dans une meme passe seule la raison de
# la PREMIERE ligne etait ecrite ; (ii) l'unite d'une seule cellule appliquee a une grille heterogene (2,8x entre
# familles) ; (iii) une unite MUR non qualifiee (aucune charge publiee). La DECISION scellee ne change pas (E11) : unite
# = mur de la premiere cellule neuve, `project_cost`, coupe du lr le plus bas. Ce qui change : POURQUOI est publie, par
# ligne, avec la charge mesuree et les deux cotes du seuil.
_CLES_UNITE_R2 = ("unite_cpu_s", "unite_cle", "charge_unite", "marge_au_seuil", "unite_de_bascule_acceptee_s")


def _lr_de(k):
    return float(k.split("|")[1][3:])


def _decider_coupes_r2(restantes, unite_s, budget_s, safety, label=RULE_R2):
    """Decision E13 de R2, extraite en fonction PURE -- semantique IDENTIQUE a la boucle scellee (E11 sinon) : tant que
    `project_cost` leve, couper la ligne du lr le plus BAS ; si plus rien ne reste, pas de projection (None).

    Rend (restantes gardees, lignes coupees, projection_s | None). Chaque ligne = {lr, cles, n_unites, raison} : SA raison
    (la boucle d'origine ne publiait que celle de la premiere) et `n_unites` = le compte projete qui l'a fait couper, dont
    depend sa geometrie (`cut_geometry`). Calibree par PREDICTION sur l'histoire committee : passe 1 -> 96 cles et
    3587.784336090088 au bit pres ; reprise -> 60 cles et 10308.464065790176 (tests/sandbox/test_td_step_pilot.py)."""
    restantes, lignes = list(restantes), []
    while True:
        try:
            return restantes, lignes, project_cost(unit_s=unite_s, n_units=len(restantes), budget_s=budget_s,
                                                   safety=safety, label=label)
        except CostTooHighToStart as exc:
            lr_bas = min(_lr_de(k) for k in restantes)
            coupees = [k for k in restantes if _lr_de(k) == lr_bas]
            lignes.append({"lr": lr_bas, "cles": coupees, "n_unites": len(restantes), "raison": str(exc)})
            restantes = [k for k in restantes if _lr_de(k) != lr_bas]
            if not restantes:
                return restantes, lignes, None


def _coupe_r2(lignes, *, unite_s, unite_cpu_s, charge, budget_s, safety):
    """PURE : le dict `coupe` d'UNE passe, RECONSTRUIT -- jamais `setdefault`. `cles` = union triee (le seul champ lu par
    `_lecture_r2`, inchangee) ; `lignes` = un `cut_record` par ligne, nature classee PAR LIGNE (`classify_cut_nature`) sur
    la charge integree de la cellule d'unite, sans bande de contamination : aucune n'est mesuree pour cette machine,
    donc la voie par la marge est fermee et le depassement publie laisse le lecteur appliquer la sienne ; `raison` =
    celles de TOUTES les lignes, dans l'ordre de coupe."""
    x = (charge or {}).get("coeurs_exterieurs")
    recs = []
    for ligne in lignes:
        g = cut_geometry(unite_s, ligne["n_unites"], budget_s, safety)
        recs.append(cut_record(nature=classify_cut_nature(g["depassement"], coeurs_exterieurs=x), raison=ligne["raison"],
                               lr=ligne["lr"], cles=ligne["cles"], unit_s=unite_s, n_units=ligne["n_unites"],
                               budget_s=budget_s, safety=safety, unite_cpu_s=unite_cpu_s, charge=copy.deepcopy(charge)))
    return {"cles": sorted({k for ligne in lignes for k in ligne["cles"]}),
            "raison": " ; ".join(f"lr={r['lr']} : {r['raison']}" for r in recs), "lignes": recs}


def _relever_coupe(regime, *, relevee_a, replique=None):
    """PURE : rend un NOUVEAU `_regime` ou la coupe courante passe a l'historique par COPIE PROFONDE (l'ancienne levee y
    rangeait une REFERENCE au dict de coupe, protegee seulement parce que la cle etait re-liee ensuite -- revue M-M13).
    Retire l'unite levee et tout ce qui la decrit ; la raison de la LEVEE va dans l'historique (`raison_levee`), jamais
    dans `coupe` : une reprise sans nouvelle coupe ne laisse ni raison ni cle vide. `replique` = la cellule d'unite
    re-chronometree (M-M6), rangee avec la coupe qu'elle sert a re-qualifier. Les historiques anterieurs sont gardes."""
    r = copy.deepcopy(regime)
    entree = {"unite_s": r.pop("unite_s", None), "projection_s": r.pop("projection_s", None), "coupe": r.pop("coupe"),
              "relevee_a": relevee_a,
              "raison_levee": "--relever-coupe : reprise DECLAREE (E13) -- unite re-mesuree, coupe re-projetee"}
    for cle in _CLES_UNITE_R2:
        if cle in r:
            entree[cle] = r.pop(cle)
    if replique is not None:
        entree["replique_unite"] = copy.deepcopy(replique)
    r.setdefault("coupes_precedentes", []).append(entree)
    return r


def _requalifier_r2(entree, cles_coupees_maintenant, *, budget_s, safety):
    """PURE : re-qualifie chaque ligne d'une coupe LEVEE, apres la nouvelle decision. `issue` est un FAIT (re-coupee ->
    `confirmee`, sinon `recuperee`) ; `nature` n'est ETABLIE que par la replique LIBRE de la MEME cellule
    (`classify_cut_nature`, regle 1). « Recuperee -> contention etablie » en comparant deux cellules DIFFERENTES serait une
    inference deguisee en mesure (E8, revue M-M6 / I-REQUALIF) : l'ecart 217,4 / 196,4 s de R2 (+10,7 %) est plus petit
    que l'exces de la premiere cellule sur la mediane de son propre bras (+21 % a +38 %). Sans replique valide (absente,
    exactitude differente, charge illisible), la nature retombe sur la charge de la mesure d'origine ; sur l'ancien format
    (R2 publie : ni lignes, ni cellule d'unite, ni charge) elle est `indeterminee`, cause non qualifiee."""
    maintenant = set(cles_coupees_maintenant)
    coupe = entree.get("coupe") or {}
    rep = entree.get("replique_unite") or {}
    mur_rep = rep.get("mur_s")
    rep_ok = (rep.get("exactitude_identique") is True and isinstance(mur_rep, (int, float))
              and not isinstance(mur_rep, bool) and mur_rep > 0)
    out = {}
    if not coupe.get("lignes"):
        for lr in sorted({_lr_de(k) for k in coupe.get("cles", [])}):
            cles = [k for k in coupe["cles"] if _lr_de(k) == lr]
            out[str(lr)] = {"issue": "confirmee" if maintenant.intersection(cles) else "recuperee",
                            "nature": "indeterminee",
                            "raison": "ancien format : ni lignes, ni cellule d'unite, ni charge publiees -- cause non "
                                      "qualifiee (les deux unites viennent de deux cellules differentes)"}
        return out
    for ligne in coupe["lignes"]:
        d_rep = cut_geometry(mur_rep, ligne["n_unites"], budget_s, safety)["depassement"] if rep_ok else None
        nature = classify_cut_nature(ligne["depassement"], coeurs_exterieurs=(ligne.get("charge") or {}).get("coeurs_exterieurs"),
                                     depassement_replique=d_rep,
                                     coeurs_exterieurs_replique=rep.get("coeurs_exterieurs") if rep_ok else None)
        out[str(ligne["lr"])] = {"issue": "confirmee" if maintenant.intersection(ligne["cles"]) else "recuperee",
                                 "nature": nature, "depassement_replique": d_rep,
                                 "facteur_charge": rep.get("facteur_charge") if rep_ok else None}
    return out


def _cout_par_bras_r2(temps, neuves, *, unite_s, unite_cle, safety):
    """PURE, non levante (revue M-M9) : la projection a posteriori PAR BRAS, publiee A COTE de la decision, jamais a sa
    place -- la regle scellee fixe « unite MESUREE sur la premiere cellule neuve » (E11 sinon). Medianes du mur des
    cellules chronometrees (`_temps_s`, persiste depuis P2.110 : les 108 cellules de R2 n'ont que la sortie standard).
    Un bras neuf sans cellule chronometree n'a PAS d'unite : la projection par bras est alors None, jamais partielle ni
    completee par une unite par defaut (porte 14). `unite_sur_mediane_du_bras` dit de combien la cellule d'unite depasse
    son propre bras (premiere cellule du processus : import de torch, echauffement)."""
    par_bras, n = {}, {}
    for k, t in temps.items():
        par_bras.setdefault(k.split("|")[0], []).append(t["mur_s"])
    for k in neuves:
        n[k.split("|")[0]] = n.get(k.split("|")[0], 0) + 1
    med = {b: float(np.median(v)) for b, v in par_bras.items()}
    manquants = sorted(b for b in n if b not in med)
    bras_u = unite_cle.split("|")[0] if unite_cle else None
    return {"unite_mediane_par_bras_s": med, "n_neuves_par_bras": n, "bras_sans_unite": manquants,
            "projection_par_bras_s": None if (manquants or not n) else cost_per_arm(med, n, safety=safety)["projection_s"],
            "projection_unite_unique_s": (unite_s * len(neuves) * safety) if unite_s is not None else None,
            "unite_sur_mediane_du_bras": (unite_s / med[bras_u]) if (unite_s is not None and bras_u in med) else None}


def main_r2(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    regle = verify(RULE_R2)
    out_path = str(results_file("td_step_pilot_r2.json"))
    c, s = regle["cellule"], regle["seuils"]
    db = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    imp = _import_r2(regle)
    db.update(imp)                                                 # relues a chaque appel
    if "--lecture" in argv:
        print(json.dumps(_lecture_r2(db, regle), indent=1, ensure_ascii=False))
        return db
    n_neuves = sum(1 for k in _cellules_r2(regle) if k not in db)
    design = declare_design(
        question=regle["question"],
        replication_unit="seed (une population de %d agents par cellule ; 5 bras x 3 lr appariés par seed)" % c["n_agents"],
        n_independent=len(c["seeds"]),
        links={"accuracy_par_lambda_et_lr": "measured", "controle_chemin_td0_d0_par_lr": "measured",
               "cellules_importees_R0_R1": "measured", "cout_unite": "measured"},
        cost_estimate=regle["cout"],
        control_family=assert_control_family(cells=len(_cellules_r2(regle)) + 2 * len(c["seeds"]), alpha_family=0.05))
    db.setdefault("_design", design)
    db.setdefault("_regime", {k: v for k, v in c.items() if k != "seeds"})
    db.setdefault("_dose", {})
    db.setdefault("_temps_s", {})
    sw = Stopwatch()

    def _chronometrer(k):
        """(accuracy, dose, temps) d'une cellule, SANS rien persister. La fenetre de charge s'ouvre AVANT le chronometre et
        se ferme APRES son arret (revue M-M5, E11) : aucune lecture de capteur n'entre dans l'unite scellee. L'unite reste
        le MUR (`budget_s` est du mur ; un run torch multi-thread rend un CPU > mur) ; le CPU est publie A COTE."""
        bras, lr_s, sd_s = k.split("|")
        lr, sd = float(lr_s[3:]), int(sd_s[5:])
        lam = {"lam0": 0.0, "lam05": 0.5, "lam09": 0.9, "lam099": 0.99, "td0_d0": 0.0}[bras]
        fenetre = LoadWindow()
        chrono = Stopwatch()
        acc, dose = _train_eval_td_step(sd, lam, c["episodes_td"], c["n_agents"], c["K"], lr,
                                        trace_reset_per_episode=c["trace_reset_per_episode"], same_tick=(bras == "td0_d0"))
        el = chrono.elapsed()
        charge = fenetre.close()
        mur, cpu = el["elapsed_s"], el["elapsed_cpu_s"]
        return acc, dose, {"mur_s": mur, "cpu_s": cpu, "coeurs_propres": (cpu / mur) if mur > 0 else None,
                           "coeurs_exterieurs": charge["coeurs_exterieurs"]}

    def _mesure(k):
        acc, dose, t = _chronometrer(k)
        db[k], db["_dose"][k] = acc, dose
        db["_temps_s"][k] = t          # P2.110 (ii) : le temps de CHAQUE cellule est persiste, plus seulement imprime
        json.dump(stamp(db, RULE_R2), open(out_path, "w", encoding="utf-8"), indent=1)
        ext = "illisible" if t["coeurs_exterieurs"] is None else f"{t['coeurs_exterieurs']:.1f} coeurs ext."
        print(f"  {k}: {acc:.3f} ({t['mur_s']:.1f} s mur, {t['cpu_s']:.1f} s cpu, {ext})", flush=True)
        return t
    if "--relever-coupe" in argv and db["_regime"].get("coupe"):
        # E13, reprise DECLAREE : on releve la coupe, on garde son historique, et on re-mesure l'unite AVANT de
        # re-projeter. P2.110 (revue M-M6) : d'abord, la cellule d'unite de la coupe levee est RE-CHRONOMETREE -- premiere
        # du processus, comme a l'origine (meme echauffement : import de torch) --, jamais re-persistee ; son exactitude
        # doit ressortir bit-identique (determinisme controle au passage). C'est la seule mesure qui ETABLIT une
        # contention (CLAUDE.md : la charge se mesure par la replication d'une cellule bit-identique). Cout declare : une
        # cellule. Contrepartie DECLAREE : la nouvelle unite est alors prise dans un processus CHAUD (torch deja importe,
        # 2,7 a 7,6 s mesures en revue), donc un peu plus basse qu'une premiere cellule -- publiee telle quelle. Absente de
        # l'ancien format (unite_cle non publiee) : pas de replique, cause non qualifiee.
        replique = None
        k_u, u0 = db["_regime"].get("unite_cle"), db["_regime"].get("unite_s")
        if k_u is not None and k_u in db:
            acc_r, _, t_r = _chronometrer(k_u)
            identique = acc_r == db[k_u]
            replique = dict(t_r, cle=k_u, exactitude_identique=identique,
                            facteur_charge=(u0 / t_r["mur_s"]) if (identique and u0 and t_r["mur_s"] > 0) else None)
            print(f"  REPLIQUE de l'unite {k_u} : {t_r['mur_s']:.1f} s (origine {u0}) -- exactitude "
                  f"{'IDENTIQUE' if identique else 'DIFFERENTE : replique ecartee'}", flush=True)
        db["_regime"] = _relever_coupe(db["_regime"], relevee_a=time.strftime("%Y-%m-%d %H:%M"), replique=replique)
    restantes = [k for k in _cellules_r2(regle) if k not in db and k not in set(db["_regime"].get("coupe", {}).get("cles", []))]
    if restantes and "unite_s" not in db["_regime"]:
        # garde de cout E13 : l'unite est MESUREE sur la premiere cellule neuve, jamais supposee
        if db["_regime"].get("coupe"):
            raise ValueError("TD-STEP-PILOT-R2 : etat incoherent -- une coupe sans unite_s ; la decision la remplacerait "
                             "en silence. Relancer avec --relever-coupe (qui la range dans l'historique).")
        k0 = restantes.pop(0)
        t = _mesure(k0)
        regime = db["_regime"]
        regime["unite_s"], regime["unite_cpu_s"], regime["unite_cle"] = t["mur_s"], t["cpu_s"], k0
        regime["charge_unite"] = {"coeurs_exterieurs": t["coeurs_exterieurs"], "coeurs_propres": t["coeurs_propres"],
                                  "coeurs_logiques": os.cpu_count(), "seuil_coeurs_libre": COEURS_EXTERIEURS_LIBRE_MAX,
                                  "bande_contamination": None,
                                  "fenetre": "integree sur la cellule d'unite, lectures HORS du chronometre"}
        restantes, lignes, proj = _decider_coupes_r2(restantes, t["mur_s"], s["budget_s"], s["safety"])
        if lignes:
            regime["coupe"] = _coupe_r2(lignes, unite_s=t["mur_s"], unite_cpu_s=t["cpu_s"],
                                        charge=regime["charge_unite"], budget_s=s["budget_s"], safety=s["safety"])
            for rec in regime["coupe"]["lignes"]:
                print(f"  COUPE (E13) : ligne lr={rec['lr']} ({len(rec['cles'])} cellules, {rec['depassement']:.3f} x le "
                      f"budget, bascule {rec['unite_de_bascule_s']:.1f} s, nature {rec['nature']}) -- {rec['raison']}", flush=True)
        if proj is not None:
            # P2.110 : les DEUX cotes du seuil -- la marge de la projection ACCEPTEE ici, celle (negative) de chaque ligne
            # refusee dans coupe.lignes ; la fragilite se lit dans la seconde, pas dans la premiere.
            regime["projection_s"] = proj
            regime["marge_au_seuil"] = margin_to_budget(proj, s["budget_s"])
            regime["unite_de_bascule_acceptee_s"] = (s["budget_s"] / (len(restantes) * s["safety"])) if restantes else None
        hist = regime.get("coupes_precedentes") or []
        if hist and "requalification" not in hist[-1]:
            hist[-1]["requalification"] = _requalifier_r2(hist[-1], regime.get("coupe", {}).get("cles", []),
                                                          budget_s=s["budget_s"], safety=s["safety"])
        json.dump(stamp(db, RULE_R2), open(out_path, "w", encoding="utf-8"), indent=1)
    for k in restantes:
        _mesure(k)
    el = sw.elapsed()
    db["_cout_s"] = db.get("_cout_s", 0.0) + el["elapsed_s"]
    db["_cout_cpu_s"] = db.get("_cout_cpu_s", 0.0) + el["elapsed_cpu_s"]
    db["_regime"]["cout_par_bras_a_posteriori"] = _cout_par_bras_r2(
        db["_temps_s"], [k for k in _cellules_r2(regle) if k not in imp], unite_s=db["_regime"].get("unite_s"),
        unite_cle=db["_regime"].get("unite_cle"), safety=s["safety"])
    db["_lecture"] = _lecture_r2(db, regle)
    json.dump(stamp(db, RULE_R2), open(out_path, "w", encoding="utf-8"), indent=1)
    print(json.dumps(db["_lecture"], indent=1, ensure_ascii=False))
    print("->", out_path)
    return db


if __name__ == "__main__":
    if "--r2" in sys.argv:
        main_r2()
    elif "--r1" in sys.argv:
        main_r1()
    else:
        main()
