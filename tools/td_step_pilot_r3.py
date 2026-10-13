"""TD-STEP-PILOT-R3 (P4.19, ADR-005 ligne `eligibility_trace_credit`, décisions de robla datées du 2026-09-28) — la
trace d'éligibilité TRANSPORTE-t-elle du crédit, ou ne fait-elle qu'un pas plus gros ?

Même dispositif que R0-R2 (`tools/td_step_pilot.py` : composition (q+key)%K à D=1, substrat bilinéaire rang 16,
3000 épisodes, SGD, traces remises à zéro à chaque épisode). Quatre bras rejoués et INSTRUMENTÉS par pas :
`lam0` (TD(0)), `lam09` (trace λ 0,9), `sham09` (même trace, δ DÉCALÉ d'un épisode dans le seul terme porté —
`CREDIT_TRACE_DELTA_SHAM = "decale"`), `td0_d0` (contrôle du CHEMIN sans délai) ; un cinquième, `td0_app` (TD(0) au
pas multiplié PAR BLOC pour égaler le déplacement NET de `lam09`), entre si son coût MESURÉ au pré-vol reste sous un
tiers du coût des quatre autres (décision 3). Références lr 0 du MÊME dispositif, recalculées à l'éval exhaustive.

Deux pas : 4,0 PRIMAIRE, 4√2 ≈ 5,657 SECONDAIRE (choisi après avoir vu 2,0 et 8,0 : un échec y rend « attend »,
jamais « refusée » ; l'ENTRÉE exige les deux). Barre = référence lr 0 + marge. Lieu = nexus, threads fixés et
publiés ; le lien au bit avec R0/R2 est publié, jamais exigé (décision 5).

Lecture sur la grille EXHAUSTIVE (B·K² = 576, marge 29 pas) : d = lam09 − lam0 et e = sham09 − lam0 par seed,
f̂ = Σe/Σd (fraction du gain que le sham CONSERVE) avec IC90 par bootstrap apparié sur les seeds, à graine déclarée.
Usage : python tools/td_step_pilot_r3.py [--pre-vol | --etape 1 | --etape 2 | --lecture | --calibrer-lecture]
Résultats : results/td_step_pilot_r3.json (et _calibration_lecture.json).
"""
import json
import os
import platform
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.cost_guard import (COEURS_EXTERIEURS_LIBRE_MAX, CostGuard, LoadWindow, Stopwatch, cost_per_arm,
                              project_cost_per_arm)
from tools.experiment_preflight import (PreflightError, ReferenceCollapsedError, assert_control_family,
                                        assert_verdict_invariant_to_optimizer, declare_design)
from tools.grid_compare import cmp_continu, cmp_grille, marge_en_pas, sur_grille
from tools.preregister import stamp, verify
from tools.td_step_pilot import RULE as RULE_R0
from tools.td_step_pilot import _train_eval_td_step
from src.paths import results_file   # noqa: E402  (porte 12)

RULE_R3 = "TD-STEP-PILOT-R3"
BRAS_ENTRAINES = ("lam0", "lam09", "sham09", "td0_d0")
BRAS_APPARIE = "td0_app"
REFERENCES = ("lr0_reference", "lr0_reference_d0")
BRANCHES_PAS = ("INCOMPLET", "INSTRUMENT_ROMPU", "CONTROLE_CHEMIN_ECHOUE", "PAS_D_EFFET", "F_INDEFINI",
                "SHAM_NUIT", "TRANSPORTE", "PAS_PLUS_GROS", "SHAM_PARTIEL")


def _cle(bras, pas, sd):
    return f"{bras}|pas={pas}|seed={sd}"


def _cle_ref(ref, sd):
    return f"{ref}|seed={sd}"


def _bras_du_pas(c):
    """Les bras que la RÈGLE prévoit (le bras apparié y est CONDITIONNEL : voir `_bras_lus`)."""
    return list(BRAS_ENTRAINES) + ([BRAS_APPARIE] if c.get("bras_apparie", False) else [])


def _bras_lus(db, c):
    """Les bras que la LECTURE attend : le bras apparié n'y entre que si le pré-vol l'a RETENU sur son coût (décision
    déclarée d'avance, jamais prise après un verdict). Rend (bras, raison) ; raison non None = pré-vol absent alors
    que la règle prévoit le bras -- la lecture le dit (INCOMPLET), elle ne devine pas."""
    if not c.get("bras_apparie", False):
        return list(BRAS_ENTRAINES), None
    pv = (db.get("_regime") or {}).get("pre_vol")
    if not pv or "apparie_retenu" not in pv:
        return list(BRAS_ENTRAINES), "pré-vol absent : inclusion du bras apparié non décidée"
    return list(BRAS_ENTRAINES) + ([BRAS_APPARIE] if pv["apparie_retenu"] else []), None


def _n_grille(c):
    return int(c["n_agents"]) * int(c["K"]) ** 2


def _spec(bras, c):
    """(λ, sham, same_tick) d'un bras entraîné."""
    lam = float(c["lambda"])
    return {"lam0": (0.0, None, False), "lam09": (lam, None, False), "sham09": (lam, "decale", False),
            "td0_d0": (0.0, None, True), BRAS_APPARIE: (0.0, None, False)}[bras]


# ---------------------------------------------------------------------------------------------------- la dose


def _net_bloc_total(bloc):
    return float(sum(sum(v) for v in bloc.values()))


def rho_blocs(dose_lam09, dose_lam0, n_blocs):
    """Multiplicateurs du pas PAR BLOC pour `td0_app` : ρ_b = net(lam09, bloc b) / net(lam0, bloc b), sommés sur les
    agents et les paramètres (le pas de l'optimiseur est commun à la population). Appariement en BOUCLE OUVERTE : ρ
    vient des bras DÉJÀ mesurés du même seed et du même pas, jamais du bras apparié lui-même ; le net ATTEINT par
    `td0_app` est publié et contrôlé (`_controle_appariement`). REFUS (jamais un ρ fabriqué) : un nombre de blocs
    différent de `n_blocs` des deux côtés (un `zip` tronquerait EN SILENCE), un net lam0 nul (ρ infini)."""
    b9 = dose_lam09["dose_instrument"]["net_blocs"]
    b0 = dose_lam0["dose_instrument"]["net_blocs"]
    if len(b9) != n_blocs or len(b0) != n_blocs:
        raise ValueError(f"rho_blocs : {len(b9)} blocs lam09 et {len(b0)} blocs lam0 pour {n_blocs} attendus -- "
                         "refus : un appariement sur des blocs tronqués serait faux sans le dire")
    out = []
    for i, (x9, x0) in enumerate(zip(b9, b0)):
        n9, n0 = _net_bloc_total(x9), _net_bloc_total(x0)
        if not n0 > 0.0:
            raise ValueError(f"rho_blocs : net lam0 nul au bloc {i} -- ρ indéfini, jamais remplacé par une constante")
        out.append(n9 / n0)
    return out


def _controle_appariement(dose_app, dose_lam09, bornes):
    """Contrôle de MANIPULATION du bras apparié : net total atteint / net total visé ∈ `bornes`. Rend (rapport, ok)."""
    n_app = float(dose_app["dose_instrument"]["net_total"])
    n9 = float(dose_lam09["dose_instrument"]["net_total"])
    if not n9 > 0.0:
        return None, False
    r = n_app / n9
    return r, bool(bornes[0] <= r <= bornes[1])


# ---------------------------------------------------------------------------------------------------- f̂


def f_hat(d, e, seuil_pas, B, graine, q=(0.05, 0.95), max_degeneres=0.05):
    """f̂ = Σe / Σd (entiers, en PAS de la grille exhaustive, par seed), IC par bootstrap APPARIÉ sur les seeds
    (`default_rng(graine)` PRIVÉ, hors simulation). Porte 14 : Σd ≤ `seuil_pas` -> f̂ None (un gain trop petit ne se
    divise pas), jamais 0 ni 1 fabriqués. Un rééchantillon à Σd* ≤ 0 n'a pas de rapport : il est COMPTÉ et écarté ;
    au-delà de `max_degeneres` × B, l'IC est None (dit, jamais lissé)."""
    d, e = np.asarray(d, dtype=np.int64), np.asarray(e, dtype=np.int64)
    if d.shape != e.shape or d.ndim != 1 or d.size == 0:
        raise ValueError(f"f_hat : d {d.shape} et e {e.shape} doivent être deux vecteurs non vides de même taille")
    sd, se = int(d.sum()), int(e.sum())
    out = {"somme_d": sd, "somme_e": se, "seuil_pas": int(seuil_pas), "B": int(B), "graine": int(graine),
           "quantiles": list(q)}
    if not sd > int(seuil_pas):
        return dict(out, f=None, ic90=None, bootstrap_degeneres=None,
                    raison=f"Σd = {sd} ≤ {seuil_pas} pas : gain trop petit pour une fraction")
    rng = np.random.default_rng(int(graine))
    idx = rng.integers(0, d.size, size=(int(B), d.size))
    Sd, Se = d[idx].sum(axis=1), e[idx].sum(axis=1)
    ok = Sd > 0
    n_deg = int((~ok).sum())
    f = se / sd
    if n_deg > max_degeneres * B:
        return dict(out, f=f, ic90=None, bootstrap_degeneres=n_deg,
                    raison=f"{n_deg}/{B} rééchantillons à Σd* ≤ 0 (> {max_degeneres:.0%}) : IC non publié")
    fb = Se[ok] / Sd[ok]
    lo, hi = (float(x) for x in np.quantile(fb, q))
    return dict(out, f=f, ic90=[lo, hi], bootstrap_degeneres=n_deg, raison=None)


# ---------------------------------------------------------------------------------------------------- la lecture


def _entier(db, k, n):
    x = sur_grille(db[k], n)
    if x is None:
        raise ValueError(f"{k} = {db[k]!r} n'est pas sur la grille 1/{n} : une accuracy exhaustive l'est toujours")
    return x


def classify_pas(db, regle, pas):
    """Lecture d'UN pas, ORDRE IMPOSÉ (`BRANCHES_PAS`). Ne lit que des cellules présentes ; publie les comptes
    littéraux de l'ADR, la dose et le bras apparié HORS branche."""
    c, s = regle["cellule"], regle["seuils"]
    seeds, n = c["seeds"], _n_grille(c)
    marge = s["marge_pas"] / n
    bras, pourquoi = _bras_lus(db, c)
    if pourquoi is not None:
        return {"branche": "INCOMPLET", "raison": pourquoi}
    attendu = [_cle(b, pas, sd) for b in bras for sd in seeds] + [_cle_ref(r, sd) for r in REFERENCES for sd in seeds]
    manquantes = [k for k in attendu if k not in db]
    if manquantes:
        return {"branche": "INCOMPLET", "manquantes": len(manquantes), "exemple": manquantes[:3]}
    dose = db.get("_dose", {})
    out = {"marge_pas": marge_en_pas(marge, n), "n_grille": n}

    # 1. l'instrument : sham_omis, terme porté au rang 0, garde de dose EXOGÈNE (appliqué / contrefactuel)
    rompus = []
    for sd in seeds:
        k = _cle("sham09", pas, sd)
        sh = (dose.get(k) or {}).get("sham")
        di = (dose.get(k) or {}).get("dose_instrument")
        if sh is None or di is None:
            rompus.append(f"{k} : dose du sham non publiée")
            continue
        if sh["sham_omis"] != c["n_agents"]:
            rompus.append(f"{k} : sham_omis {sh['sham_omis']} ≠ {c['n_agents']}")
        if di["porte_rang0_non_nul"] != 0:
            rompus.append(f"{k} : terme porté non nul au rang 0 ({di['porte_rang0_non_nul']})")
        cf = sh["chemin_porte_contrefactuel"]
        r = (sh["chemin_porte_applique"] / cf) if cf > 0 else None
        lo, hi = s["garde_dose_sham"]
        if r is None or not (lo <= r <= hi):
            rompus.append(f"{k} : appliqué/contrefactuel {r} hors [{lo} ; {hi}]")
    if rompus:
        return dict(out, branche="INSTRUMENT_ROMPU", rompus=rompus)

    def v(b, sd):
        return db[_cle(b, pas, sd)]

    def ref(r, sd):
        return db[_cle_ref(r, sd)]

    def n_sup(xs, ys, m):
        return sum(1 for x, y in zip(xs, ys) if cmp_grille(x, y, m, n))

    col = {b: [v(b, sd) for sd in seeds] for b in bras}
    rf = {r: [ref(r, sd) for sd in seeds] for r in REFERENCES}
    out["medianes"] = {b: float(np.median(col[b])) for b in bras}
    out["medianes"].update({r: float(np.median(rf[r])) for r in REFERENCES})
    out["comptes"] = {
        "td0_d0_sup_ref_d0": n_sup(col["td0_d0"], rf["lr0_reference_d0"], marge),
        "lam09_sup_lam0": n_sup(col["lam09"], col["lam0"], marge),
        # comptes LITTÉRAUX de l'ADR (barre = référence lr 0 + marge, décision 4)
        "lam09_sup_barre": n_sup(col["lam09"], rf["lr0_reference"], marge),
        "sham09_sup_barre": n_sup(col["sham09"], rf["lr0_reference"], marge),
        "lam0_sup_barre": n_sup(col["lam0"], rf["lr0_reference"], marge),
        "sham09_sup_lam0": n_sup(col["sham09"], col["lam0"], marge),
        "lam09_sup_sham09_marge0": n_sup(col["lam09"], col["sham09"], 0.0)}
    ns = len(seeds)
    out["adr"] = {"lam09_franchit_la_barre": out["comptes"]["lam09_sup_barre"] >= s["seeds_effet"],
                  "sham_reste_sous_la_barre": out["comptes"]["sham09_sup_barre"] < s["seeds_effet"]}
    out["dose"] = _descripteurs_dose(dose, pas, seeds)
    if BRAS_APPARIE in bras:
        out["apparie"] = _lecture_apparie(db, dose, pas, seeds, col, rf, marge, n, s)

    # 2. le chemin, 3. l'effet
    if out["comptes"]["td0_d0_sup_ref_d0"] < s["seeds_chemin"]:
        return dict(out, branche="CONTROLE_CHEMIN_ECHOUE")
    if out["comptes"]["lam09_sup_lam0"] < s["seeds_effet"]:
        return dict(out, branche="PAS_D_EFFET")
    # 4. f̂ (en PAS entiers) et son IC
    d = [_entier(db, _cle("lam09", pas, sd), n) - _entier(db, _cle("lam0", pas, sd), n) for sd in seeds]
    e = [_entier(db, _cle("sham09", pas, sd), n) - _entier(db, _cle("lam0", pas, sd), n) for sd in seeds]
    fh = f_hat(d, e, s["marge_pas"] * ns, s["bootstrap_B"], s["bootstrap_graine"])
    out["f_hat"] = fh
    out["d_pas"], out["e_pas"] = d, e
    if fh["f"] is None or fh["ic90"] is None:
        return dict(out, branche="F_INDEFINI")
    lo, hi = fh["ic90"]
    if cmp_continu(0.0, hi, 0.0):                      # borne haute < 0 : le sham NUIT (confondant du critique)
        return dict(out, branche="SHAM_NUIT")
    if not cmp_continu(hi, s["f_transporte_max"], 0.0):
        return dict(out, branche="TRANSPORTE")
    if not cmp_continu(s["f_pas_plus_gros_min"], lo, 0.0):
        return dict(out, branche="PAS_PLUS_GROS")
    return dict(out, branche="SHAM_PARTIEL")


def _descripteurs_dose(dose, pas, seeds):
    """Publiés, jamais une branche : ρ_td = chemin(lam09)/chemin(lam0), rapports sham/trace en CHEMIN (prédit ≈ 0,82
    sous transport, ≈ 1 sinon) et en NET, et le rapport de COHÉRENCE (net_S/net_T)/(chemin_S/chemin_T) (< 1 prédit
    sous transport, ≈ 1 sinon ; direction seulement, ADR-005 3 bis). Un bras sans instrument rend None."""
    def tot(b, sd, champ):
        di = (dose.get(_cle(b, pas, sd)) or {}).get("dose_instrument")
        return None if di is None else float(di[champ])

    def rapport(a, b):
        return (a / b) if (a is not None and b is not None and b > 0) else None
    par_seed = []
    for sd in seeds:
        ch = {b: tot(b, sd, "chemin_total") for b in ("lam0", "lam09", "sham09")}
        ne = {b: tot(b, sd, "net_total") for b in ("lam0", "lam09", "sham09")}
        rc, rn = rapport(ch["sham09"], ch["lam09"]), rapport(ne["sham09"], ne["lam09"])
        par_seed.append({"seed": sd, "rho_td_chemin": rapport(ch["lam09"], ch["lam0"]),
                         "rho_td_net": rapport(ne["lam09"], ne["lam0"]),
                         "sham_sur_trace_chemin": rc, "sham_sur_trace_net": rn,
                         "coherence": rapport(rn, rc)})

    def med(champ):
        xs = [p[champ] for p in par_seed if p[champ] is not None]
        return {"mediane": float(np.median(xs)) if xs else None, "n": len(xs)}
    return {"par_seed": par_seed, **{k: med(k) for k in ("rho_td_chemin", "rho_td_net", "sham_sur_trace_chemin",
                                                          "sham_sur_trace_net", "coherence")}}


def _lecture_apparie(db, dose, pas, seeds, col, rf, marge, n, s):
    """Le bras TD(0) apparié en NET : contrôle de manipulation par seed, puis (s'il tient) la trace bat-elle TD(0) à
    dose nette égale ? Publié ; entre dans la synthèse comme condition d'ENTRÉE (décision 3)."""
    rapports, ok = [], 0
    for sd in seeds:
        da, d9 = dose.get(_cle(BRAS_APPARIE, pas, sd)), dose.get(_cle("lam09", pas, sd))
        if not da or not d9 or "dose_instrument" not in da or "dose_instrument" not in d9:
            rapports.append(None)
            continue
        r, bon = _controle_appariement(da, d9, s["appariement_bornes"])
        rapports.append(r)
        ok += int(bon)
    lisible = ok >= s["seeds_appariement"]
    col_a = col[BRAS_APPARIE]
    sup = sum(1 for x, y in zip(col["lam09"], col_a) if cmp_grille(x, y, marge, n))
    return {"net_atteint_sur_vise": rapports, "seeds_apparies": ok, "lisible": lisible,
            "lam09_sup_app": sup, "app_sup_barre": sum(1 for x, y in zip(col_a, rf["lr0_reference"])
                                                       if cmp_grille(x, y, marge, n)),
            "trace_bat_td0_a_dose_nette_egale": bool(lisible and sup >= s["seeds_effet"])}


def garde_e19(db, regle, par_pas):
    """Garde E19, appelée SEULEMENT si TRANSPORTE aux deux pas : `measure(lr)` = (médiane sham09, médiane lam09) au
    MÊME pas ; `reference_floor` SCALAIRE = max sur les pas de (médiane lam0) + marge. Rend PASSE,
    VERDICT_DEPEND_DU_PAS (PreflightError) ou INCONCLUSIF (ReferenceCollapsedError)."""
    c, s = regle["cellule"], regle["seuils"]
    marge = s["marge_pas"] / _n_grille(c)
    pas_lr = {float(c["pas"][p]): p for p in (c["pas_primaire"], c["pas_secondaire"])}

    def measure(lr):
        m = par_pas[pas_lr[float(lr)]]["medianes"]
        return m["sham09"], m["lam09"]
    plancher = max(par_pas[p]["medianes"]["lam0"] for p in pas_lr.values()) + marge
    try:
        assert_verdict_invariant_to_optimizer(measure, lrs=tuple(pas_lr), reference_floor=plancher,
                                              label="TD-STEP-PILOT-R3 : sham contre trace")
        return {"issue": "PASSE", "plancher_reference": plancher}
    except ReferenceCollapsedError as exc:
        return {"issue": "INCONCLUSIF", "plancher_reference": plancher, "raison": str(exc)}
    except PreflightError as exc:
        return {"issue": "VERDICT_DEPEND_DU_PAS", "plancher_reference": plancher, "raison": str(exc)}


def verdict_synthese(par_pas, regle, e19=None):
    """Vers l'ADR (critère amendé du 2026-09-24 + décisions du 2026-09-28) :
      * REFUSÉE ssi PAS_PLUS_GROS au pas PRIMAIRE (l'effet y tient : branche au-delà de PAS_D_EFFET) -- le pas
        secondaire ne produit JAMAIS à lui seul un verdict négatif (décision 2, E11) ;
      * ENTRE ssi, aux DEUX pas : TRANSPORTE ET comptes littéraux de l'ADR (lam09 franchit la barre, le sham reste
        dessous) ET, si le bras apparié est au design, la trace bat TD(0) à dose nette égale -- puis la garde E19 PASSE ;
      * ATTEND sinon, avec les manques NOMMÉS."""
    c = regle["cellule"]
    p1, p2 = c["pas_primaire"], c["pas_secondaire"]
    L1, L2 = par_pas.get(p1), par_pas.get(p2)
    manques = []
    if L1 is None or L1["branche"] in ("INCOMPLET", "INSTRUMENT_ROMPU"):
        return {"issue": "ATTEND", "manques": [f"pas primaire {p1} : {None if L1 is None else L1['branche']}"]}
    if L1["branche"] == "PAS_PLUS_GROS":
        return {"issue": "REFUSEE", "raison": f"PAS_PLUS_GROS au pas primaire {p1} : le sham garde l'aide -- l'effet "
                                              "est le PAS, pas le transport"}
    for p, L in ((p1, L1), (p2, L2)):
        if L is None:
            manques.append(f"pas {p} non joué")
            continue
        if L["branche"] != "TRANSPORTE":
            manques.append(f"pas {p} : {L['branche']}")
            continue
        if not L["adr"]["lam09_franchit_la_barre"]:
            manques.append(f"pas {p} : lam09 ne franchit pas la barre ({L['comptes']['lam09_sup_barre']}/"
                           f"{len(c['seeds'])})")
        if not L["adr"]["sham_reste_sous_la_barre"]:
            manques.append(f"pas {p} : le sham franchit la barre ({L['comptes']['sham09_sup_barre']}/"
                           f"{len(c['seeds'])})")
        if "apparie" in L:                     # le bras apparié a été RETENU au pré-vol : sa condition s'applique
            a = L["apparie"]
            if not a.get("lisible"):
                manques.append(f"pas {p} : bras apparié non lisible (net atteint hors bornes)")
            elif not a.get("trace_bat_td0_a_dose_nette_egale"):
                manques.append(f"pas {p} : TD(0) à dose nette égale fait jeu égal -- l'aide peut être la DOSE")
    if manques:
        return {"issue": "ATTEND", "manques": manques}
    if e19 is None or e19.get("issue") != "PASSE":
        return {"issue": "ATTEND", "manques": [f"garde E19 : {None if e19 is None else e19.get('issue')}"],
                "garde_e19": e19}
    return {"issue": "ENTRE", "garde_e19": e19}


def lecture_r3(db, regle):
    """Les deux pas, puis la synthèse ; la garde E19 n'est appelée que si TRANSPORTE aux deux pas."""
    c = regle["cellule"]
    par_pas = {p: classify_pas(db, regle, p) for p in (c["pas_primaire"], c["pas_secondaire"])}
    deux = all(par_pas[p]["branche"] == "TRANSPORTE" for p in par_pas)
    e19 = garde_e19(db, regle, par_pas) if deux else None
    return {"par_pas": par_pas, "garde_e19": e19, "synthese": verdict_synthese(par_pas, regle, e19)}


# ---------------------------------------------------------------------------------------------------- calibration


def base_injection(regle, profil_d, sigma, f, rng, base=110):
    """Un db SYNTHÉTIQUE d'UN pas (le primaire), à réponse connue, passé à la VRAIE lecture : lam0 = base + ε,
    lam09 = base + d_s + ε, sham09 = base + f·d_s + ε (ε ~ N(0, σ) en pas, arrondis) ; références, chemin et
    instrument conformes, bras apparié à dose atteinte ET sans avantage (lam0 + ε). Pure, sans simulation."""
    c = regle["cellule"]
    n = _n_grille(c)
    p = c["pas_primaire"]
    db, dose = {}, {}

    def put(k, x):
        db[k] = int(min(max(round(x), 0), n)) / n
    for i, sd in enumerate(c["seeds"]):
        dd = float(profil_d[i % len(profil_d)])
        put(_cle("lam0", p, sd), base + rng.normal(0, sigma))
        put(_cle("lam09", p, sd), base + dd + rng.normal(0, sigma))
        put(_cle("sham09", p, sd), base + f * dd + rng.normal(0, sigma))
        put(_cle("td0_d0", p, sd), 400 + rng.normal(0, sigma))
        put(_cle_ref("lr0_reference", sd), base - 20)
        put(_cle_ref("lr0_reference_d0", sd), 100)
        di = {"net_total": 1.0, "chemin_total": 2.0, "porte_rang0_non_nul": 0}
        dose[_cle("sham09", p, sd)] = {"sham": {"sham_omis": c["n_agents"], "chemin_porte_applique": 1.0,
                                                "chemin_porte_contrefactuel": 1.0},
                                       "dose_instrument": di}
        dose[_cle("lam09", p, sd)] = {"dose_instrument": di}
        if c.get("bras_apparie", False):
            put(_cle(BRAS_APPARIE, p, sd), base + rng.normal(0, sigma))
            dose[_cle(BRAS_APPARIE, p, sd)] = {"dose_instrument": di}
    db["_dose"] = dose
    db["_regime"] = {"pre_vol": {"apparie_retenu": bool(c.get("bras_apparie", False))}}
    return db


def calibrer_lecture(regle, profil_d, sigmas, fs, n_rep, graine):
    """Puissance et spécificité de la lecture d'UN pas, par INJECTION BRUITÉE (0 simulation). Rend, par σ et par f,
    la fréquence de chaque branche. Exigé avant le sceau : P(TRANSPORTE | f = 0) et P(PAS_PLUS_GROS | f = 1) ≥ 0,8 ;
    publiés : P(TRANSPORTE | f = 0,5 et 0,6), les faux TRANSPORTE."""
    rng = np.random.default_rng(int(graine))
    p = regle["cellule"]["pas_primaire"]
    out = {"graine": int(graine), "n_rep": int(n_rep), "profil_d_pas": [float(x) for x in profil_d], "par_sigma": {}}
    for sigma in sigmas:
        par_f = {}
        for f in fs:
            comptes = {b: 0 for b in BRANCHES_PAS}
            for _ in range(int(n_rep)):
                comptes[classify_pas(base_injection(regle, profil_d, sigma, f, rng), regle, p)["branche"]] += 1
            par_f[str(f)] = {b: comptes[b] / n_rep for b in BRANCHES_PAS if comptes[b]}
        out["par_sigma"][str(sigma)] = par_f
    return out


# ---------------------------------------------------------------------------------------------------- le run


def _cellule(bras, pas, sd, c, db):
    """(accuracy exhaustive, accuracy tirée 640, dose) d'un bras entraîné, instrumenté."""
    lr = float(c["pas"][pas])
    lam, sham, same_tick = _spec(bras, c)
    lr_blocs = None
    if bras == BRAS_APPARIE:
        n_blocs = int(c["episodes_td"]) // int(c["bloc_episodes"])
        lr_blocs = rho_blocs(db["_dose"][_cle("lam09", pas, sd)], db["_dose"][_cle("lam0", pas, sd)], n_blocs)
    acc640, dose = _train_eval_td_step(sd, lam, c["episodes_td"], c["n_agents"], c["K"], lr,
                                       trace_reset_per_episode=c["trace_reset_per_episode"], same_tick=same_tick,
                                       sham=sham, mesure_dose=True, eval_exhaustive=True,
                                       bloc_dose=c["bloc_episodes"], lr_blocs=lr_blocs,
                                       controle_delta=(sham is not None))
    ex = dose["eval_exhaustive"]
    return ex["succes"] / ex["n"], acc640, dose


def _reference(ref, sd, c):
    """Référence lr 0 : AUCUN entraînement (à lr 0 les paramètres ne bougent pas -- témoin dans les tests), éval
    exhaustive seule sur le substrat construit au même seed."""
    _, dose = _train_eval_td_step(sd, 0.0, 0, c["n_agents"], c["K"], 0.0, eval_batches=0,
                                  trace_reset_per_episode=c["trace_reset_per_episode"],
                                  same_tick=(ref == "lr0_reference_d0"), eval_exhaustive=True)
    ex = dose["eval_exhaustive"]
    return ex["succes"] / ex["n"], dose


def _lien_r0(db, c):
    """Lien au bit avec R0 au pas primaire (grille tirée de 640) : PUBLIÉ, jamais exigé (décision 5 : sur nexus, le
    rejeu au bit de valeurs produites sous Windows n'est pas attendu)."""
    try:
        verify(RULE_R0)
        r0 = json.load(open(str(results_file("td_step_pilot_r0.json")), encoding="utf-8"))
    except Exception as exc:                       # noqa: BLE001 -- l'absence se DIT, elle ne fabrique rien
        return {"statut": "ILLISIBLE", "raison": repr(exc)}
    p = c["pas_primaire"]
    if float(r0["_regime"]["lr_td"][0]) != float(c["pas"][p]):
        return {"statut": "NON_APPLICABLE", "raison": "le pas primaire de R3 n'est pas le lr 0 de R0"}
    paires = {"lam0": "td0", "lam09": "tdlam", "td0_d0": "td0_d0"}
    egaux, compares = 0, 0
    for sd in c["seeds"]:
        for b, b0 in paires.items():
            k = _cle(b, p, sd)
            if k in db.get("_g640", {}) and f"{b0}|lr0|seed={sd}" in r0:
                compares += 1
                egaux += int(db["_g640"][k] == r0[f"{b0}|lr0|seed={sd}"])
    if compares == 0:
        return {"statut": "NON_MESURE", "compares": 0}
    return {"statut": "IDENTIQUE" if egaux == compares else "DIFFERENT", "egaux": egaux, "compares": compares}


def _environnement(c):
    import torch
    return {"torch": torch.__version__, "numpy": np.__version__, "python": platform.python_version(),
            "hote": platform.node(), "systeme": platform.platform(), "threads_torch": torch.get_num_threads(),
            "lieu_declare": os.environ.get("R3_LIEU"), "coeurs_logiques": os.cpu_count()}


def _profil_d_r0(c):
    """Le profil d'effet de R0 au pas 4,0 (lam09 − lam0 par seed, grille 640), ramené en pas de la grille exhaustive :
    base de la calibration par injection AVANT l'étape 1 (après l'étape 1, le profil mesuré le remplace)."""
    verify(RULE_R0)
    r0 = json.load(open(str(results_file("td_step_pilot_r0.json")), encoding="utf-8"))
    n = _n_grille(c)
    return [(r0[f"tdlam|lr0|seed={sd}"] - r0[f"td0|lr0|seed={sd}"]) * n for sd in c["seeds"]]


def main_r3(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    regle = verify(RULE_R3)
    c, s = regle["cellule"], regle["seuils"]
    out_path = str(results_file("td_step_pilot_r3.json"))
    db = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    if "--lecture" in argv:
        print(json.dumps(lecture_r3(db, regle), indent=1, ensure_ascii=False))
        return db
    if "--calibrer-lecture" in argv:
        cal = calibrer_lecture(regle, _profil_d_r0(c), s["calibration"]["sigmas_pas"], s["calibration"]["f"],
                               s["calibration"]["n_rep"], s["calibration"]["graine"])
        cal_path = str(results_file("td_step_pilot_r3_calibration_lecture.json"))
        json.dump(stamp(cal, RULE_R3), open(cal_path, "w", encoding="utf-8"), indent=1)
        print(json.dumps(cal["par_sigma"], indent=1), "\n->", cal_path)
        return cal
    lieu = os.environ.get("R3_LIEU")
    if lieu != c["lieu"]:
        raise ValueError(f"TD-STEP-PILOT-R3 : lieu scellé {c['lieu']!r}, déclaré {lieu!r} (R3_LIEU) -- refus avant "
                         "toute cellule (décision 5)")
    import torch
    torch.set_num_threads(int(c["threads"]))
    etape = "pre-vol" if "--pre-vol" in argv else ("2" if "--etape" in argv and argv[argv.index("--etape") + 1] == "2"
                                                   else "1")
    bras = _bras_du_pas(c)
    cellules = ([_cle(b, p, sd) for p in (c["pas_primaire"], c["pas_secondaire"]) for sd in c["seeds"] for b in bras]
                + [_cle_ref(r, sd) for r in REFERENCES for sd in c["seeds"]])
    design = declare_design(
        question=regle["question"],
        replication_unit="seed (une population de %d agents par cellule ; bras appariés par seed)" % c["n_agents"],
        n_independent=len(c["seeds"]),
        links={"accuracy_exhaustive_par_bras": "measured", "dose_chemin_et_net_par_agent": "measured",
               "controle_chemin_td0_d0": "measured", "references_lr0": "measured", "f_hat": "measured"},
        cost_estimate=regle["cout"],
        control_family=assert_control_family(cells=len(cellules), alpha_family=0.05))
    db.setdefault("_design", design)
    db.setdefault("_regime", {k: v for k, v in c.items() if k != "seeds"})
    db["_regime"].setdefault("environnement", _environnement(c))
    for champ in ("_dose", "_g640", "_temps_s"):
        db.setdefault(champ, {})

    def persister():
        json.dump(stamp(db, RULE_R3), open(out_path, "w", encoding="utf-8"), indent=1)

    def mesurer(k):
        fen, chrono = LoadWindow(), Stopwatch()
        if k.split("|")[0] in REFERENCES:
            ref, sd = k.split("|")[0], int(k.split("|")[1][5:])
            acc, dose = _reference(ref, sd, c)
            acc640 = None
        else:
            b, p, sd = k.split("|")[0], k.split("|")[1][4:], int(k.split("|")[2][5:])
            acc, acc640, dose = _cellule(b, p, sd, c, db)
        el = chrono.elapsed()
        charge = fen.close()
        db[k], db["_dose"][k] = acc, dose
        if acc640 is not None:
            db["_g640"][k] = acc640
        db["_temps_s"][k] = {"mur_s": el["elapsed_s"], "cpu_s": el["elapsed_cpu_s"],
                             "coeurs_exterieurs": charge["coeurs_exterieurs"]}
        persister()
        print(f"  {k}: {acc:.4f} ({el['elapsed_s']:.1f} s mur, {el['elapsed_cpu_s']:.1f} s cpu)", flush=True)
        return db["_temps_s"][k]

    if etape == "pre-vol":
        # Un seed complet au pas primaire, bras par bras, chronométré machine NOTÉE : l'unité PAR BRAS scellée par la
        # règle, puis la décision (déclarée d'avance, sur le COÛT seul) d'inclure ou non le bras apparié.
        sd = c["seeds"][0]
        for b in list(BRAS_ENTRAINES) + ([BRAS_APPARIE] if c.get("bras_apparie", False) else []):
            k = _cle(b, c["pas_primaire"], sd)
            if k not in db:
                mesurer(k)
        u = {b: db["_temps_s"][_cle(b, c["pas_primaire"], sd)]["mur_s"] for b in _bras_du_pas(c)}
        autres = sum(u[b] for b in BRAS_ENTRAINES)
        frac = (u[BRAS_APPARIE] / autres) if (BRAS_APPARIE in u and autres > 0) else None
        db["_regime"]["pre_vol"] = {"unites_par_bras_s": u, "fraction_cout_apparie": frac,
                                    "seuil_fraction": s["fraction_cout_apparie_max"],
                                    "apparie_retenu": bool(frac is not None
                                                           and frac < s["fraction_cout_apparie_max"]),
                                    "charge_seuil_coeurs_libre": COEURS_EXTERIEURS_LIBRE_MAX,
                                    "lien_r0": _lien_r0(db, c)}
        persister()
        print(json.dumps(db["_regime"]["pre_vol"], indent=1, ensure_ascii=False))
        return db
    pv = db["_regime"].get("pre_vol")
    if not pv:
        raise ValueError("TD-STEP-PILOT-R3 : --pre-vol d'abord -- l'unité par bras est MESURÉE, jamais supposée")
    p = c["pas_primaire"] if etape == "1" else c["pas_secondaire"]
    if etape == "2":
        manq = [k for k in cellules if f"|pas={c['pas_primaire']}|" in k and k not in db]
        if manq:
            raise ValueError(f"TD-STEP-PILOT-R3 : étape 2 avant la fin de l'étape 1 ({len(manq)} cellules manquent)")
        if "puissance_etape2" not in db["_regime"]:
            L1 = classify_pas(db, regle, c["pas_primaire"])
            prof = L1.get("d_pas") or _profil_d_r0(c)
            db["_regime"]["puissance_etape2"] = calibrer_lecture(regle, prof, s["calibration"]["sigmas_pas"],
                                                                 s["calibration"]["f"], s["calibration"]["n_rep"],
                                                                 s["calibration"]["graine"] + 1)
            persister()
    bras_run = [b for b in _bras_du_pas(c) if b != BRAS_APPARIE or pv["apparie_retenu"]]
    a_faire = [_cle(b, p, sd) for sd in c["seeds"] for b in bras_run if _cle(b, p, sd) not in db]
    if etape == "1":
        a_faire += [_cle_ref(r, sd) for r in REFERENCES for sd in c["seeds"] if _cle_ref(r, sd) not in db]
    n_par_bras = {}
    for k in a_faire:
        n_par_bras[k.split("|")[0]] = n_par_bras.get(k.split("|")[0], 0) + 1
    unites = dict(pv["unites_par_bras_s"])
    unites.update({r: s["unite_reference_s"] for r in REFERENCES})
    db["_regime"].setdefault("projections", {})[f"etape_{etape}"] = {
        "projection_s": project_cost_per_arm(unites, n_par_bras, s["budget_etape_s"], safety=s["safety"],
                                             label=f"TD-STEP-PILOT-R3 étape {etape}"),
        "par_bras": cost_per_arm(unites, n_par_bras, safety=s["safety"])["par_bras"], "n_par_bras": n_par_bras}
    persister()
    garde = CostGuard(s["budget_etape_s"], label=f"TD-STEP-PILOT-R3 étape {etape}", clock=time.monotonic)
    for k in a_faire:                                       # ordre : lam0, lam09 AVANT td0_app (ρ en dépend)
        mesurer(k)
        garde.tick()
    if etape == "1":
        db["_regime"]["lien_r0"] = _lien_r0(db, c)        # publié, jamais exigé (décision 5)
    db["_lecture"] = lecture_r3(db, regle)
    persister()
    print(json.dumps(db["_lecture"], indent=1, ensure_ascii=False))
    print("->", out_path)
    return db


if __name__ == "__main__":
    main_r3()
