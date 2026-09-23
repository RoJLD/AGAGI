"""BILINEAR-SHAM-R1 (P4.12, ADR-005 item 2, 2026-09-16) — la pièce `bilinear` doit-elle son effet (plain 0,271 vs
bilinéaire 0,932, EDR-BILINEAR) à la MULTIPLICATION ((H·U)⊙(H·V))·W_bl ou à la CAPACITÉ ajoutée (U, V, W_bl) ?

Trois bras appariés par seed : `plain` (BILINEAR off), `bilinear` (produit de Hadamard), `sham` (SOMME (H·U)+(H·V),
MÊMES tenseurs U/V/W_bl, même init, même optimiseur — `TorchPopulationModel.BILINEAR_SHAM`). Règle scellée AVANT
toute cellule de mesure : `docs/preregistrations/BILINEAR-SHAM-R1.json` — le seed 0 a servi de fumée (sham 0,309,
VU avant scellement, déclaré dans la règle) et est EXCLU : seeds 1-12. Même régime que le bras décisif publié
(`results/bilinear_composition.json` : 300 épisodes, 16 agents, K=6, rank 16, same_tick, supervisé), deux pas
(`lr` 0,02 publié + 0,002, clause E19). Contrôles : bit-identité des bras plain/bilinéaire seeds 1-11 contre le
JSON publié (RE-MESURÉS ici, jamais importés) ; compte de paramètres des trois bras ASSERTÉ (sham == bilinéaire
> plain) et publié dans `_regime`. Résultats : `results/bilinear_sham_r1.json`. Pur torch CPU, aucun bail.
Usage : python tools/bilinear_sham_run.py [--lecture]
"""
import json
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.bilinear_composition_probe import _train_eval_one
from tools.experiment_preflight import assert_control_family, declare_design
from tools.preregister import stamp, verify
from tools.cost_guard import Stopwatch          # P2.78 : mur ET CPU
from src.paths import results_file   # noqa: E402  (porte 12)

RULE = "BILINEAR-SHAM-R1"
BRAS = (("plain", False, False), ("bilinear", True, False), ("sham", True, True))   # (nom, bilinear, bilinear_sham)


def _n_params(bilinear, sham, n_agents, rank):
    """Compte des paramètres ENTRAÎNÉS d'un bras, par agent — les tenseurs que `_train_eval_one` donne à Adam
    (W, plus U/V/W_bl si bilinéaire), construits avec les mêmes drapeaux puis restaurés. Compté, jamais lu."""
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel as T
    saved = (T.CONDITION_GATE, T.GATE_TARGET, T.BILINEAR, T.BILINEAR_RANK, T.BILINEAR_SHAM)
    T.CONDITION_GATE, T.GATE_TARGET = False, None
    T.BILINEAR = bool(bilinear)                     # épinglé AVANT la construction (porte check_substrate_pinning)
    T.BILINEAR_RANK = int(rank)
    T.BILINEAR_SHAM = bool(sham) and bool(bilinear)
    try:
        np.random.seed(0)
        torch.manual_seed(0)
        pop = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        tenseurs = [pop.W] + ([pop.U, pop.V, pop.W_bl] if bilinear else [])
        total = int(sum(t.numel() for t in tenseurs))
        assert total % n_agents == 0
        return total // n_agents
    finally:
        T.CONDITION_GATE, T.GATE_TARGET, T.BILINEAR, T.BILINEAR_RANK, T.BILINEAR_SHAM = saved


def _bit_identite(db, regle, reference):
    """Contrôle scellé : plain/bilinéaire au pas publié, seeds 1-11, doivent ÉGALER le JSON d'EDR-BILINEAR
    (indexé seed 0..11). Rend le compte d'égalités et les écarts ; ne décide rien."""
    lr_pub = regle["cellule"]["lr"][0]
    ecarts, n_attendu = [], 0
    for sub in ("plain", "bilinear"):
        ref = reference["decisive_same_tick_supervised"]["per_seed"][sub]
        for s in regle["cellule"]["seeds"]:
            if s >= len(ref):
                continue                                    # seed 12 : hors du JSON publié (12 seeds : 0..11)
            n_attendu += 1
            k = f"{sub}|lr={lr_pub}|seed={s}"
            if db.get(k) != ref[s]:                         # ABSENTE = écart (mesure None), jamais « égale »
                ecarts.append({"cellule": k, "mesure": db.get(k), "publie": ref[s]})
    return {"n_egal": n_attendu - len(ecarts), "n_attendu": n_attendu, "ecarts": ecarts}


def _lecture(db, regle):
    """Branche scellée, dans l'ORDRE IMPOSÉ (INCOMPLET, SHAM_INERTE, SHAM_COMPOSE, SHAM_PARTIEL). Ne lit que des
    cellules présentes ; jamais une inférence."""
    c = regle["cellule"]
    seeds, lrs = c["seeds"], c["lr"]
    attendu = [f"{sub}|lr={lr}|seed={s}" for sub in c["bras"] for lr in lrs for s in seeds]
    manquantes = [k for k in attendu if k not in db]
    if manquantes:
        return {"branche": "INCOMPLET", "manquantes": len(manquantes)}
    s = regle["seuils"]
    lr_pub, lr_bas = lrs[0], lrs[1]

    def med(sub, lr):
        return float(np.median([db[f"{sub}|lr={lr}|seed={sd}"] for sd in seeds]))
    mp, mb, ms = med("plain", lr_pub), med("bilinear", lr_pub), med("sham", lr_pub)
    mp2, mb2, ms2 = med("plain", lr_bas), med("bilinear", lr_bas), med("sham", lr_bas)
    sous = sum(1 for sd in seeds
               if db[f"sham|lr={lr_pub}|seed={sd}"] <= db[f"plain|lr={lr_pub}|seed={sd}"] + s["marge"])
    out = {"mediane_plain_002": mp, "mediane_bilineaire_002": mb, "mediane_sham_002": ms,
           "mediane_plain_0002": mp2, "mediane_bilineaire_0002": mb2, "mediane_sham_0002": ms2,
           "sham_sous_plain_plus_marge": f"{sous}/{len(seeds)}"}
    ctrl = db.get("_controles", {}).get("bit_identite")
    if ctrl:
        out["bit_identite"] = f"{ctrl['n_egal']}/{ctrl['n_attendu']}"
    if ms <= mp + s["marge"] and sous >= s["seeds_min"] and ms2 < s["barre"]:
        out["branche"] = "SHAM_INERTE"
    elif ms >= s["barre"] or ms2 >= s["barre"]:
        out["branche"] = "SHAM_COMPOSE"
    else:
        out["branche"] = "SHAM_PARTIEL"
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    regle = verify(RULE)
    out_path = str(results_file("bilinear_sham_r1.json"))
    c = regle["cellule"]
    db = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    if "--lecture" in argv:
        print(json.dumps(_lecture(db, regle), indent=1, ensure_ascii=False))
        return db
    design = declare_design(
        question=regle["question"],
        replication_unit="seed (une population de %d agents par cellule ; 3 bras x 2 pas appariés par seed)" % c["n_agents"],
        n_independent=len(c["seeds"]),
        links={"accuracy_plain": "measured", "accuracy_bilineaire": "measured", "accuracy_sham": "measured",
               "bit_identite_plain_bilineaire": "measured", "compte_de_parametres": "measured",
               "plafond_plain_forme_close": "inferred"},   # 0,3889 = MINORANT importé, ne sert qu'à justifier la barre
        cost_estimate=regle["cout"],
        allow_inferred_reason=("le plafond 0,3889 du plain (tools/plain_substrate_ceiling.py) n'entre dans aucune "
                               "branche : il justifie seulement la barre scellee 0,5 (milieu entre ce plafond et 1) ; "
                               "les trois bras sont MESURES ici, et plain/bilineaire sont confrontes bit a bit au JSON publie"),
        control_family=assert_control_family(cells=len(c["bras"]) * len(c["lr"]) * len(c["seeds"]), alpha_family=0.05))
    db.setdefault("_design", design)
    regime = {k: v for k, v in c.items() if k != "seeds"}
    if "_regime" not in db:
        n = {nom: _n_params(bil, sham, c["n_agents"], c["rank"]) for nom, bil, sham in BRAS}
        assert n["sham"] == n["bilinear"] > n["plain"], n      # contrôle à paramètres APPARIÉS, asserté puis publié
        regime["n_params_par_agent"] = n
        db["_regime"] = regime
    sw = Stopwatch()
    for lr in c["lr"]:
        for s in c["seeds"]:
            for sub, bil, sham in BRAS:
                k = f"{sub}|lr={lr}|seed={s}"
                if k in db:
                    continue
                tc = time.time()
                acc = _train_eval_one(seed=s, bilinear=bil, task="composition", episodes=c["episodes"],
                                      n_agents=c["n_agents"], K=c["K"], lr=lr, rank=c["rank"],
                                      same_tick=c["same_tick"], credit_mode=c["credit_mode"], bilinear_sham=sham)
                db[k] = float(acc)
                json.dump(stamp(db, RULE), open(out_path, "w", encoding="utf-8"), indent=1)
                print(f"  {k}: {acc:.3f} ({time.time() - tc:.1f} s)", flush=True)
    el = sw.elapsed()                                        # P2.78 : mur et CPU, accumules (run reprenable)
    db["_cout_s"] = db.get("_cout_s", 0.0) + el["elapsed_s"]
    db["_cout_cpu_s"] = db.get("_cout_cpu_s", 0.0) + el["elapsed_cpu_s"]
    ref_path = str(results_file("bilinear_composition.json"))
    reference = json.load(open(ref_path, encoding="utf-8"))
    db["_controles"] = {"bit_identite": _bit_identite(db, regle, reference), "reference": os.path.basename(ref_path)}
    db["_lecture"] = _lecture(db, regle)
    json.dump(stamp(db, RULE), open(out_path, "w", encoding="utf-8"), indent=1)
    print(json.dumps(db["_lecture"], indent=1, ensure_ascii=False))
    print("controles :", json.dumps(db["_controles"], ensure_ascii=False)[:400])
    print("->", out_path)
    return db


if __name__ == "__main__":
    main()
