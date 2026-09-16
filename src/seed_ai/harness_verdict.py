"""
src/seed_ai/harness_verdict.py — Lecture PURE du harnais (ADR-004, spec §2.3-6) : trois conditions, branches
dans un ORDRE imposé, aucune constante fabriquée sur collection vide (nan et vide LÈVENT). Compose les instruments
déjà calibrés : ablation_verdict (demande, nécessité), alias_guard_verdict (ablation d'état), learner_verdict
(acquisition, import paresseux : son module charge les mondes), assert_verdict_invariant_to_optimizer (E19).
La garde de barre est appelée sur le plafond de REPRÉSENTATION déclaré et son issue est PUBLIÉE (bar_status),
jamais levée : sur la cellule A, 0,944 > 0,217 est exactement ce que le harnais doit savoir DIRE.
"""
import statistics
from typing import Optional

import numpy as np

BRANCHES = ("INCOMPLET", "INCONCLUSIVE_N", "INDETERMINE_HARNAIS", "LR_ARTIFACT", "NOT_DEMANDED",
            "DEMAND_WITHIN_NOISE", "INCONCLUSIVE_SPECIFICITY", "INCONCLUSIVE_ALIAS", "NOT_ACQUIRED",
            "PIECE_NOT_NECESSARY", "PIECE_INCONCLUSIVE", "PIECE_PARTIAL", "DEMANDED_ACQUIRED_NECESSARY", "AUTRE")

_ARMS = ("A", "A0", "A2", "D", "D2")


def _series(col: dict, seeds, label) -> list:
    """dict seed->valeur -> liste alignée sur `seeds` ; LÈVE sur absence, vide ou non fini (jamais 0.0)."""
    if not col:
        raise ValueError(f"{label} : série vide")
    out = []
    for s in seeds:
        v = col.get(str(s), col.get(s))
        if v is None:
            raise KeyError(f"{label} : seed {s} absent")
        v = float(v)
        if not np.isfinite(v):
            raise ValueError(f"{label} : seed {s} vaut nan/inf")
        out.append(v)
    return out


def _med(xs):
    if not xs:
        raise ValueError("médiane d'une liste vide")
    return float(statistics.median(xs))


def measure_noise_floor(intact: dict, noop: dict) -> dict:
    """Plancher de bruit MESURÉ : ratios intact/noop appariés par seed (même politique, second rng d'éval).
    Rend {"band": [min, max], "per_seed": {seed: ratio}}. Un no-op à l'argmax sur le MÊME lot rendrait 1,0 par
    construction : c'est le second rng qui fait la bande."""
    if not intact or not noop:
        raise ValueError("measure_noise_floor : série vide")
    seeds = sorted(intact, key=lambda k: int(k))
    i, n = _series(intact, seeds, "intact"), _series(noop, seeds, "noop")
    ratios = {str(s): (a / b if b > 0 else float("inf")) for s, a, b in zip(seeds, i, n)}
    vals = list(ratios.values())
    if any(not np.isfinite(r) for r in vals):
        raise ValueError("measure_noise_floor : un bras noop est à 0 (ratio infini)")
    return {"band": [min(vals), max(vals)], "per_seed": ratios}


def measure_ablated_bayes_ceiling(task, ablation, n=4096, seed=0) -> dict:
    """Plafond de Bayes du flux ABLATÉ : accuracy de l'oracle sous l'ablation sur n tirages, confrontée au
    `bayes_floor` DÉCLARÉ. certified ssi déclaré, dans ± 2 se, et espace d'états énumérable."""
    ep = task.episodes(np.random.RandomState(seed), n, "train")
    ep_a = ablation.apply(ep, np.random.RandomState(seed + 1))
    measured = float(np.mean(task.score(np.asarray(task.oracle(ep_a)), ep_a)))
    declared = None if ablation.bayes_floor is None else float(ablation.bayes_floor)
    p = measured if declared is None else declared
    se = float(np.sqrt(max(p * (1.0 - p), 1e-12) / n))
    certified = declared is not None and abs(measured - declared) <= 2.0 * se and task.enumerate_states() is not None
    return {"declared": declared, "measured": measured, "se": se, "certified": bool(certified)}


def _demand(db, rule, seeds, last_A, band):
    from tools.demand_marker import ablation_verdict
    from tools.language_memory_demand_probe import alias_guard_verdict
    out, worst = {}, None
    for a in rule["ablations"]:
        name, must = a["name"], bool(a["must_bite"])
        col = db["eval"]["ablated"].get(name)
        if col is None:
            raise KeyError(f"ablated:{name}")
        ablated = _series(col, seeds, f"ablated:{name}")
        floor = rule["bayes_floors"].get(name)
        # ceiling=None : deux bras au plafond = « n'a pas mordu » (spécificité SATISFAITE), pas « dégénéré » —
        # le contrat de tâche a déjà prouvé sur l'oracle que chaque must_bite mord.
        raw = ablation_verdict(last_A, ablated, floor=(floor if must else None), ceiling=None, n_floor=int(rule["n_floor"]),
                               collapse_factor=float(rule["collapse_factor"]), intervention_verified=True)
        in_band = bool(band[0] <= raw["ratio"] <= band[1])
        entry = {"must_bite": must, "verdict": raw["verdict"], "ratio": raw["ratio"], "in_noise_band": in_band,
                 "raw": raw, "alias": None}
        if a["site"] == "state":
            ctrl = db["eval"]["control"].get(name)
            if ctrl is None:
                raise KeyError(f"control:{name}")
            ci, ca = _series(ctrl["intact"], seeds, "ctrl_intact"), _series(ctrl["ablated"], seeds, "ctrl_ablated")
            x_resp = abs(_med(last_A) - _med(ablated))
            entry["alias"] = alias_guard_verdict(ci, ca, x_resp, floor=(floor if floor is not None else 0.0),
                                                 ceiling=1.0, alive_margin=float(rule["alive_margin"]))
        out[name] = entry
        # branche la plus sévère parmi les ablations (ordre : NOT_DEMANDED < WITHIN_NOISE < SPECIFICITY < ALIAS)
        if must:
            if raw["verdict"] != "X_DEMANDED":
                b = "DEMAND_WITHIN_NOISE" if in_band else "NOT_DEMANDED"
                worst = _worse(worst, b)
            elif in_band:
                worst = _worse(worst, "DEMAND_WITHIN_NOISE")
            if entry["alias"] is not None and entry["alias"]["alias_verdict"] != "SURGICAL":
                worst = _worse(worst, "INCONCLUSIVE_ALIAS")
        elif raw["verdict"] != "X_DECOY":
            worst = _worse(worst, "INCONCLUSIVE_SPECIFICITY")
    return out, worst


def _worse(current, candidate):
    if current is None:
        return candidate
    return current if BRANCHES.index(current) <= BRANCHES.index(candidate) else candidate


def _acquisition(db, rule, seeds, first_A, mid_A, last_A, last_A0, oracle):
    from tools.cognitive_demand_inworld import learner_verdict          # paresseux : le module charge les mondes
    from tools.experiment_preflight import PreflightError, assert_bar_separates_the_incapable
    min_sep = float(rule["min_sep"])
    ref, med_A = _med(last_A0), _med(last_A)
    bar = ref + min_sep
    above = sum(1 for a, r in zip(last_A, last_A0) if a > r + min_sep)
    ceil = rule.get("incapable_ceiling")
    bar_status, ceiling_above = "CEILING_UNVALIDATED", None
    if ceil is not None:
        try:
            assert_bar_separates_the_incapable(bar, float(ceil["value"]), str(ceil["provenance"]), label="barre d'acquisition")
            bar_status, ceiling_above = "SEPARATES", False
        except PreflightError:
            bar_status, ceiling_above = "CEILING_ABOVE_BAR", True
    saturation = "PLATEAU" if (med_A - _med(mid_A)) <= min_sep else "TENDANCE"
    entry = {"bar": bar, "reference_last": ref, "learner_last": med_A, "learner_first": _med(first_A),
             "per_seed_above_ref": f"{above}/{len(seeds)}", "saturation": saturation, "bar_status": bar_status,
             "representational_ceiling_above_bar": ceiling_above,
             "dose": {arm: db["arms"][arm]["dose"] for arm in ("A", "A0")}}
    if _med(oracle) < float(rule["oracle_min"]):
        entry.update(verdict="INDETERMINE_HARNAIS", why=f"oracle {_med(oracle):.3f} < {rule['oracle_min']} : le contrôle positif de la DV échoue")
        return entry
    if ref > float(rule["prior_max"]):
        entry.update(verdict="INDETERMINE_HARNAIS", why=f"PRIOR_SOLVES : la référence lr=0 note {ref:.3f} > {rule['prior_max']} (contamination ou tâche triviale, jamais « acquis »)")
        return entry
    raw = learner_verdict(_med(first_A), med_A, ref, _med(oracle), min_sep=min_sep, min_gain=min_sep,
                          oracle_min=float(rule["oracle_min"]), reference_max=float(rule["prior_max"]))
    entry["raw"] = raw
    if raw["verdict"] == "LEARNER_LEARNS" and above == len(seeds):
        entry.update(verdict="ACQUIRED", why=None)
    elif raw["verdict"] == "INDETERMINE_HARNAIS":
        entry.update(verdict="INDETERMINE_HARNAIS", why=raw["why"])
    else:
        entry.update(verdict="NOT_ACQUIRED", why=raw.get("why") or f"{above}/{len(seeds)} seeds au-dessus de leur référence appariée")
    return entry


def _necessity(db, rule, seeds, last_A, last_D, ref, band):
    from tools.demand_marker import ablation_verdict
    min_sep = float(rule["min_sep"])
    raw = ablation_verdict(last_A, last_D, floor=None, ceiling=None, n_floor=int(rule["n_floor"]),
                           collapse_factor=float(rule["collapse_factor"]), intervention_verified=True)
    med_D = _med(last_D)
    in_band = bool(band[0] <= raw["ratio"] <= band[1])
    if raw["verdict"] == "X_DEMANDED" and not in_band:
        verdict = "NECESSARY" if med_D <= ref + min_sep else "PIECE_PARTIAL"
    elif raw["verdict"] in ("X_DECOY", "INCONCLUSIVE_INVERTED") or in_band:
        verdict = "NOT_NECESSARY"
    else:
        verdict = "INCONCLUSIVE"
    return {"verdict": verdict, "ratio": raw["ratio"], "in_noise_band": in_band, "med_without": med_D,
            "per_seed_diff": [a - d for a, d in zip(last_A, last_D)], "raw": raw,
            "sham": ("DECLARED" if rule.get("matched_sham") else "PARAMS_NON_APPARIES")}


def _e19(rule, last_A, last_A2, last_D, last_D2, bar):
    from tools.experiment_preflight import PreflightError, ReferenceCollapsedError, assert_verdict_invariant_to_optimizer
    lrs = [float(h["lr"]) for h in rule["sweep"]]
    table = {lrs[0]: (_med(last_D), _med(last_A)), lrs[1]: (_med(last_D2), _med(last_A2))}
    gaps = {str(lr): ref - tested for lr, (tested, ref) in table.items()}
    g = list(gaps.values())
    closure = None if max(g) <= 0 else 1.0 - min(g) / max(g)
    out = {"lrs": lrs, "gaps_by_lr": gaps, "closure": closure, "status": "ROBUST"}
    try:
        assert_verdict_invariant_to_optimizer(lambda lr: table[lr], lrs=lrs, reference_floor=bar, label="nécessité de la pièce")
    except ReferenceCollapsedError as e:
        out.update(status="REFERENCE_COLLAPSED", why=str(e))
    except PreflightError as e:
        out.update(status="LR_ARTIFACT", why=str(e))
    return out


def harness_verdict_lecture(db: dict, rule: dict) -> dict:
    """Verdict global dans l'ORDRE 2.3-b (BRANCHES). LÈVE sur nan ou série vide ; INCOMPLET sur bras/éval absent ;
    INCONCLUSIVE_N si un bras a moins de n_floor seeds ; rend toujours `branch` ∈ BRANCHES."""
    seeds = [int(s) for s in db.get("seeds", [])]
    n_floor = int(rule["n_floor"])
    out = {"verdict": None, "branch": None, "why": None, "demand": None, "noise_floor": None,
           "acquisition": None, "necessity": None, "e19": None}

    def _done(branch, why=None):
        out.update(verdict=branch, branch=branch, why=why)
        return out

    for arm in _ARMS:
        if arm not in db.get("arms", {}) or "last" not in db["arms"][arm]:
            return _done("INCOMPLET", f"bras {arm} absent")
    for k in ("noop", "oracle", "ablated"):
        if k not in db.get("eval", {}):
            return _done("INCOMPLET", f"éval {k} absente")
    for arm in _ARMS:
        if arm not in db["eval"]["noop"]:
            return _done("INCOMPLET", f"noop du bras {arm} absent (bande de bruit PAR BRAS, REVIEW-01 R3)")
    if not seeds:
        raise ValueError("db.seeds vide")
    abandoned = {arm: set(int(s) for s in db.get("abandoned", {}).get(arm, [])) for arm in _ARMS}
    kept = [s for s in seeds if not any(s in abandoned[a] for a in _ARMS)]
    if len(kept) < n_floor:
        return _done("INCONCLUSIVE_N", f"{len(kept)} seeds complets < n_floor={n_floor} (abandons : { {a: sorted(v) for a, v in abandoned.items() if v} })")
    last = {arm: _series(db["arms"][arm]["last"], kept, f"{arm}.last") for arm in _ARMS}
    first_A = _series(db["arms"]["A"]["first"], kept, "A.first")
    mid_A = _series(db["arms"]["A"]["mid"], kept, "A.mid")
    oracle = _series(db["eval"]["oracle"], kept, "oracle")
    out["noise_floor"] = {arm: measure_noise_floor({str(s): v for s, v in zip(kept, last[arm])},
                                                   {str(s): db["eval"]["noop"][arm][str(s)] for s in kept})
                          for arm in _ARMS}
    band = out["noise_floor"]["A"]["band"]                       # (i) : le sujet A contre ses ablations
    band_AD = [min(band[0], out["noise_floor"]["D"]["band"][0]),   # (iii) : union des bandes des DEUX bras compares
               max(band[1], out["noise_floor"]["D"]["band"][1])]
    out["acquisition"] = _acquisition(db, rule, kept, first_A, mid_A, last["A"], last["A0"], oracle)
    if out["acquisition"]["verdict"] == "INDETERMINE_HARNAIS":
        return _done("INDETERMINE_HARNAIS", out["acquisition"]["why"])
    bar = out["acquisition"]["bar"]
    min_sep = float(rule["min_sep"])
    if out["acquisition"]["verdict"] != "ACQUIRED":
        # E19 sur l'ACQUISITION : le nul tient-il au pas ? (l'intact acquiert-il au second pas du sweep ?)
        above2 = sum(1 for a, r in zip(last["A2"], last["A0"]) if a > r + min_sep)
        out["e19"] = {"lrs": [float(h["lr"]) for h in rule["sweep"]], "gaps_by_lr": None, "closure": None,
                      "status": ("LR_ARTIFACT" if (_med(last["A2"]) > bar and above2 == len(kept)) else "ACQUISITION_NULL_ROBUST"),
                      "why": f"A2 (second pas) médiane {_med(last['A2']):.3f}, {above2}/{len(kept)} seeds au-dessus de la référence"}
        if out["e19"]["status"] == "LR_ARTIFACT":
            return _done("LR_ARTIFACT", "le nul d'acquisition disparaît au second pas du sweep (E19) : " + out["e19"]["why"])
        out["demand"], worst = _demand(db, rule, kept, last["A"], band)
        if worst is not None:
            return _done(worst, "au moins une ablation ne rend pas l'issue exigée (voir demand)")
        return _done("NOT_ACQUIRED", out["acquisition"]["why"])
    # E19 sur la NÉCESSITÉ : l'écart intact / sans-pièce tient-il aux deux pas ? (référence = l'intact, jamais sous la barre)
    out["e19"] = _e19(rule, last["A"], last["A2"], last["D"], last["D2"], bar)
    if out["e19"]["status"] == "REFERENCE_COLLAPSED":
        return _done("INDETERMINE_HARNAIS", out["e19"]["why"])
    if out["e19"]["status"] == "LR_ARTIFACT":
        return _done("LR_ARTIFACT", out["e19"]["why"])
    out["demand"], worst = _demand(db, rule, kept, last["A"], band)
    if worst is not None:
        return _done(worst, "au moins une ablation ne rend pas l'issue exigée (voir demand)")
    piece = rule["piece"]
    nec = _necessity(db, rule, kept, last["A"], last["D"], out["acquisition"]["reference_last"], band_AD)
    out["necessity"] = {piece: nec}
    if nec["verdict"] == "NOT_NECESSARY":
        return _done("PIECE_NOT_NECESSARY")
    if nec["verdict"] == "INCONCLUSIVE":
        return _done("PIECE_INCONCLUSIVE", "ratio A/D dans la zone grise [1,3 ; 1,5[")
    if nec["verdict"] == "PIECE_PARTIAL":
        return _done("PIECE_PARTIAL", f"la variante sans {piece} chute ({nec['ratio']:.2f}x) mais franchit la barre d'acquisition ({nec['med_without']:.3f} > {bar:.3f})")
    if nec["verdict"] == "NECESSARY":
        return _done("DEMANDED_ACQUIRED_NECESSARY")
    return _done("AUTRE", f"nécessité inattendue : {nec['verdict']}")
