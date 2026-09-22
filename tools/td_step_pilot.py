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
        return sum(1 for sd in seeds if db[f"{b}|lr{i}|seed={sd}"] > db[f"{ref}|lr{i}|seed={sd}"] + marge)

    def n_inf(b, ref, i, marge):
        return sum(1 for sd in seeds if db[f"{b}|lr{i}|seed={sd}"] < db[f"{ref}|lr{i}|seed={sd}"] - marge)
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
    t0 = time.time()
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
    db["_cout_s"] = db.get("_cout_s", 0.0) + (time.time() - t0)
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
    t0 = time.time()
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
    db["_cout_s"] = db.get("_cout_s", 0.0) + (time.time() - t0)
    db["_lecture"] = _lecture_r1(db, regle)
    json.dump(stamp(db, RULE_R1), open(out_path, "w", encoding="utf-8"), indent=1)
    print(json.dumps(db["_lecture"], indent=1, ensure_ascii=False))
    print("->", out_path)
    return db


if __name__ == "__main__":
    main_r1() if "--r1" in sys.argv else main()
