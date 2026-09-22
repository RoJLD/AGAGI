"""S2-002-PAIRED-R1 (P2.41 b, décision robla déléguée, 2026-09-22) — la carte d'ablation-perception within-subject du
champion HoF ([[EDR-S2-002]] / [[EDR-S2-013]] : `PERCEPTION_DECOY` sur les 5 mondes, within ≈ 1,00 à bande RNG NUE dont
le bruit est ±6-8 %) tient-elle à bande APPARIÉE (`run_ablation_map(paired_band=True)`, no-op attendu 1,000 exact) — et
que vaut le within du champion une fois le bruit effacé ?

Règle scellée AVANT toute cellule : `docs/preregistrations/S2-002-PAIRED-R1.json`. Régime GRAVÉ (12 agents, 200 ticks,
K = 12 ères appariées), 5 mondes × 3 seeds (2026 publié, 3026, 3027), sujet = champion, between = réflexe sur génome
frais (comme publié). Par cellule : `within_ratio` apparié, `noop` (ratio), `verdict` de l'instrument, `intact_median`
face au plancher. Lecture (`s2_paired_lecture`, calibrée) : INCOMPLET ; HARNAIS par monde (no-op ≠ 1,000 sur ≥ 2/3
seeds → monde non lu) ; CARTE_INCHANGEE ; CARTE_MODIFIEE ; MIXTE. Fait post-hoc publié hors verdict : le SIGNE de
(within_median − 1) par monde. Résultats : `results/s2_002_paired_r1.json` (reprenable, tampon de provenance, `_cout_s`
ET `_cout_cpu_s`). Usage : python -m tools.evo_runs.s2_002_paired [--lecture]   (bail `kuzu`)
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.cost_guard import Stopwatch  # noqa: E402

PREREG = "S2-002-PAIRED-R1"
WORLDS_ORDER = ("soup", "stoneage", "agricultural", "industrial", "famine")
SEEDS = (2026, 3026, 3027)
REGIME = {"num_agents": 12, "max_ticks": 200}      # = PLANCHER_REGIME : les planchers s'appliquent
K = 12
PUBLIE = {w: "PERCEPTION_DECOY" for w in WORLDS_ORDER}    # EDR-S2-002 / EDR-S2-013 : DECOY sur les cinq mondes


def _cle(world, seed):
    return f"{world}|seed={seed}"


def s2_paired_lecture(cells, regle, publie=PUBLIE):
    """Branche scellée, ORDRE IMPOSÉ. `cells` : {"<monde>|seed=<s>": {within_ratio, noop: {ratio}, verdict, intact_median,
    floor}}. Ne lit que des cellules présentes ; un monde HARNAIS est nommé et non lu."""
    c, s = regle["cellule"], regle["seuils"]
    worlds, seeds = c["worlds"], c["seeds"]
    manquantes = [_cle(w, sd) for w in worlds for sd in seeds if _cle(w, sd) not in cells]
    if manquantes:
        return {"branche": "INCOMPLET", "manquantes": len(manquantes)}
    out = {"par_monde": {}, "harnais": [], "inchanges": [], "modifies": {}, "mixtes": []}
    for w in worlds:
        rows = [cells[_cle(w, sd)] for sd in seeds]
        noop_ok = sum(1 for r in rows if abs(float((r.get("noop") or {}).get("ratio", float("nan"))) - 1.0) <= s["noop_tol"])
        within = [float(r["within_ratio"]) for r in rows]
        verdicts = [r["verdict"] for r in rows]
        med = statistics.median(within)
        row = {"within": within, "within_median": med, "verdicts": verdicts, "noop_exact": f"{noop_ok}/{len(seeds)}",
               "intact_median": [r.get("intact_median") for r in rows], "floor": rows[0].get("floor"),
               "signe_post_hoc": ("survit PLUS derange" if med < 1.0 - s["marge"] else
                                  "survit MOINS derange" if med > 1.0 + s["marge"] else "dans la marge")}
        out["par_monde"][w] = row
        if len(seeds) - noop_ok >= s["seeds_accord"]:
            row["lecture"] = "HARNAIS"
            out["harnais"].append(w)
            continue
        n_pub = sum(1 for v in verdicts if v == publie[w])
        if n_pub >= s["seeds_accord"]:
            row["lecture"] = "INCHANGE"
            out["inchanges"].append(w)
            continue
        autres = {v: verdicts.count(v) for v in set(verdicts) if v != publie[w]}
        v_maj = max(autres, key=autres.get) if autres else None
        if v_maj is not None and autres[v_maj] >= s["seeds_accord"]:
            row["lecture"] = "MODIFIE -> " + v_maj
            out["modifies"][w] = v_maj
        else:
            row["lecture"] = "MIXTE"
            out["mixtes"].append(w)
    lus = [w for w in worlds if w not in out["harnais"]]
    if not lus:
        out["branche"] = "HARNAIS"
    elif out["modifies"]:
        out["branche"] = "CARTE_MODIFIEE"
    elif out["mixtes"]:
        out["branche"] = "MIXTE"
    else:
        out["branche"] = "CARTE_INCHANGEE"
    return out


def run_s2_paired(seeds=SEEDS, worlds=WORLDS_ORDER, k=K, regime=None, map_fn=None, db=None, save=None, verbose=True):
    """Une cellule par (monde, seed) via `run_ablation_map(paired_band=True, noop_control=True)`. Garde en tête ;
    reprenable (`db` déjà rempli est respecté) ; `save(db)` après chaque cellule."""
    regime = dict(regime or REGIME)
    seeds, worlds = list(seeds or []), list(worlds or [])
    if not seeds or not worlds or int(k) <= 0 or int(regime.get("num_agents", 0)) <= 0 or int(regime.get("max_ticks", 0)) <= 0:
        raise ValueError(f"run_s2_paired : argument degenere (seeds={seeds}, worlds={worlds}, K={k}, regime={regime})")
    if map_fn is None:
        from tools.s2_demand_ablation import run_ablation_map as map_fn
    db = {} if db is None else db
    for w in worlds:
        for sd in seeds:
            key = _cle(w, sd)
            if key in db:
                continue
            tc = time.time()
            m = map_fn(worlds=[w], seed=sd, K=k, paired_band=True, noop_control=True, **regime)[w]
            db[key] = {"within_ratio": m["within_ratio"], "between_ratio": m.get("between_ratio"), "verdict": m["verdict"],
                       "noop": m.get("noop"), "intact_median": m.get("intact_median"), "floor": m.get("floor"),
                       "reference": m.get("reference"), "policy": m.get("policy"), "n": m.get("n"), "t_s": time.time() - tc}
            if save is not None:
                save(db)
            if verbose:
                print(f"  {key}: within={m['within_ratio']:.4f} noop={(m.get('noop') or {}).get('ratio', float('nan')):.4f} "
                      f"{m['verdict']} intact={m.get('intact_median')} ({time.time() - tc:.0f} s)", flush=True)
    return db


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    from src.paths import results_file
    from tools.experiment_preflight import assert_control_family, declare_design
    from tools.jobs.run import hold
    from tools.preregister import stamp, verify
    regle = verify(PREREG)
    c = regle["cellule"]
    out_path = str(results_file("s2_002_paired_r1.json"))
    db = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    cells = {k: v for k, v in db.items() if not k.startswith("_")}
    if "--lecture" in argv:
        print(json.dumps(s2_paired_lecture(cells, regle), indent=1, ensure_ascii=False))
        return db
    design = declare_design(
        question=regle["question"],
        replication_unit="ère (K=12 ères appariées par cellule) ; 3 seeds de monde par monde, 5 mondes",
        n_independent=len(c["seeds"]),
        links={"within_apparie": "measured", "noop_apparie": "measured", "verdict_instrument": "measured",
               "intact_median_vs_plancher": "measured"},
        cost_estimate=regle["cout"],
        control_family=assert_control_family(cells=len(c["worlds"]) * len(c["seeds"]), alpha_family=0.05))
    db.setdefault("_design", design)
    db.setdefault("_regime", {k: v for k, v in c.items() if k != "seeds"} | {"seeds": list(c["seeds"]), "reference": "paired_band",
                                                                            "noop_control": True, "publie": PUBLIE})

    def _save(cells_):
        db.update(cells_)
        json.dump(stamp(db, PREREG), open(out_path, "w", encoding="utf-8"), indent=1)
    sw = Stopwatch()
    with hold("kuzu", owner="s2-002-paired", ttl_s=5400):
        run_s2_paired(seeds=c["seeds"], worlds=c["worlds"], k=c["K"], regime={"num_agents": c["num_agents"], "max_ticks": c["max_ticks"]},
                      db=cells, save=_save)
    el = sw.elapsed()
    db["_cout_s"] = db.get("_cout_s", 0.0) + el["elapsed_s"]
    db["_cout_cpu_s"] = db.get("_cout_cpu_s", 0.0) + el["elapsed_cpu_s"]
    db["_lecture"] = s2_paired_lecture(cells, regle)
    json.dump(stamp(db, PREREG), open(out_path, "w", encoding="utf-8"), indent=1)
    print(json.dumps(db["_lecture"], indent=1, ensure_ascii=False))
    print("->", out_path)
    return db


if __name__ == "__main__":
    main()
