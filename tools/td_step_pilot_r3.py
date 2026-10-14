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

Lecture sur la grille EXHAUSTIVE (B·K² = 576 ; marges PAR USAGE -- effet, chemin, barre de l'ADR -- lues dans la
règle, `_marges`) : d = lam09 − lam0 et e = sham09 − lam0 par seed,
f̂ = Σe/Σd (fraction du gain que le sham CONSERVE) avec IC90 par bootstrap apparié sur les seeds, à graine déclarée.
Exécution CELLULE PAR CELLULE (déport nexus, une commande par Job) puis agrégat sur la batcave -- voir `main_r3`.
Résultats : results/td_step_pilot_r3/<cellule>.json (par cellule, hors git), results/td_step_pilot_r3.json,
_prevol.json et _calibration_lecture.json (suivis).
"""
import argparse
import glob
import hashlib
import json
import math
import os
import platform
import re
import statistics
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.cost_guard import cost_per_arm, project_cost_per_arm
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


def _marges(s):
    """Marges PAR USAGE, en pas (décision de robla du 2026-10-14, direction B : 20 pour l'effet, 29 pour le chemin et
    la barre, à confirmer sur la mesure de μ et τ aux deux pas) : `marge_effet_pas` (lam09 contre lam0, seuil de f̂,
    descripteurs du sham et du bras apparié), `marge_chemin_pas` (td0_d0 contre sa référence), `marge_barre_pas` (comptes
    littéraux de l'ADR contre lr0_reference). Une règle qui n'a que `marge_pas` (v1, v2) l'applique aux trois. Une marge
    absente LÈVE, jamais un défaut."""
    out = {u: s.get(f"marge_{u}_pas", s.get("marge_pas")) for u in ("effet", "chemin", "barre")}
    manque = [u for u, v in out.items() if v is None]
    if manque:
        raise ValueError(f"marge(s) {manque} absente(s) de la règle")
    return out


def classify_pas(db, regle, pas):
    """Lecture d'UN pas, ORDRE IMPOSÉ (`BRANCHES_PAS`). Ne lit que des cellules présentes ; publie les comptes
    littéraux de l'ADR, la dose et le bras apparié HORS branche."""
    c, s = regle["cellule"], regle["seuils"]
    seeds, n = c["seeds"], _n_grille(c)
    mg = _marges(s)
    me, mc, mb = mg["effet"] / n, mg["chemin"] / n, mg["barre"] / n
    bras, pourquoi = _bras_lus(db, c)
    if pourquoi is not None:
        return {"branche": "INCOMPLET", "raison": pourquoi}
    attendu = [_cle(b, pas, sd) for b in bras for sd in seeds] + [_cle_ref(r, sd) for r in REFERENCES for sd in seeds]
    manquantes = [k for k in attendu if k not in db]
    if manquantes:
        return {"branche": "INCOMPLET", "manquantes": len(manquantes), "exemple": manquantes[:3]}
    dose = db.get("_dose", {})
    out = {"marges_pas": {u: marge_en_pas(m / n, n) for u, m in mg.items()}, "n_grille": n}

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
        "td0_d0_sup_ref_d0": n_sup(col["td0_d0"], rf["lr0_reference_d0"], mc),
        "lam09_sup_lam0": n_sup(col["lam09"], col["lam0"], me),
        # comptes LITTÉRAUX de l'ADR (barre = référence lr 0 + marge de barre, décision 4)
        "lam09_sup_barre": n_sup(col["lam09"], rf["lr0_reference"], mb),
        "sham09_sup_barre": n_sup(col["sham09"], rf["lr0_reference"], mb),
        "lam0_sup_barre": n_sup(col["lam0"], rf["lr0_reference"], mb),
        "sham09_sup_lam0": n_sup(col["sham09"], col["lam0"], me),
        "lam09_sup_sham09_marge0": n_sup(col["lam09"], col["sham09"], 0.0)}
    ns = len(seeds)
    out["adr"] = {"lam09_franchit_la_barre": out["comptes"]["lam09_sup_barre"] >= s["seeds_effet"],
                  "sham_reste_sous_la_barre": out["comptes"]["sham09_sup_barre"] < s["seeds_effet"]}
    out["dose"] = _descripteurs_dose(dose, pas, seeds)
    # P7.a (revue v2) : la dose de CHAQUE bras, contrôle du chemin compris -- td0_d0 n'a qu'un pas par épisode, donc la
    # moitié des mises à jour des bras D=1 ; un CONTROLE_CHEMIN_ECHOUE se lit à côté de sa dose.
    out["dose"]["updates_par_bras"] = {b: sorted({(dose.get(_cle(b, pas, sd)) or {}).get("updates")
                                                  for sd in seeds} - {None}) for b in bras}
    if BRAS_APPARIE in bras:
        out["apparie"] = _lecture_apparie(db, dose, pas, seeds, col, rf, me, n, s)    # DESCRIPTIF (décision 5)

    # 2. le chemin, 3. l'effet
    if out["comptes"]["td0_d0_sup_ref_d0"] < s["seeds_chemin"]:
        return dict(out, branche="CONTROLE_CHEMIN_ECHOUE")
    if out["comptes"]["lam09_sup_lam0"] < s["seeds_effet"]:
        return dict(out, branche="PAS_D_EFFET")
    # 4. f̂ (en PAS entiers) et son IC
    d = [_entier(db, _cle("lam09", pas, sd), n) - _entier(db, _cle("lam0", pas, sd), n) for sd in seeds]
    e = [_entier(db, _cle("sham09", pas, sd), n) - _entier(db, _cle("lam0", pas, sd), n) for sd in seeds]
    fh = f_hat(d, e, mg["effet"] * ns, s["bootstrap_B"], s["bootstrap_graine"])
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
    marge = _marges(s)["effet"] / _n_grille(c)
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
        dessous) ;
      * ATTEND sinon, avec les manques NOMMÉS.
    Décisions de robla du 2026-10-14 : (5) le bras apparié est DESCRIPTIF -- son TD(0) tourne jusqu'à un pas de 7,5
    (et ≈ 10,6 à 4√2), régime où TD(0) se dégrade, donc « bat TD(0) à dose égale » serait confondu ; (6) la garde E19 est
    appelée et PUBLIÉE, sans branche -- à deux pas séparés de √2, elle refusait pour une mauvaise raison."""
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
    publie = {"garde_e19": e19, "apparie": {p: (L or {}).get("apparie") for p, L in ((p1, L1), (p2, L2))}}
    if manques:
        return dict(publie, issue="ATTEND", manques=manques)
    return dict(publie, issue="ENTRE")


def lecture_r3(db, regle):
    """Les deux pas, puis la synthèse ; la garde E19 est appelée si TRANSPORTE aux deux pas et PUBLIÉE (sans branche,
    décision 6)."""
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


# ---------------------------------------------------------------------------------------------------- calibration v2


def base_injection_v2(regle, mu, tau, sigma_e, f, rng, base=110, chemin_rate=False):
    """Modèle de bruit DÉCLARÉ v2 (règle v2, après la mesure de τ sur les seeds tenues à l'écart) : AUCUN bruit d'éval
    (éval exhaustive, entraînement déterministe par seed) ; d_s ~ N(μ, τ) ; lam0 = base ; lam09 = base + d_s ;
    sham09 = base + f·d_s + σ_e·z ; bras apparié = lam0 (sans avantage). Le reste (références, chemin, instrument) comme
    `base_injection`. Pure, sans simulation."""
    c = regle["cellule"]
    n = _n_grille(c)
    p = c["pas_primaire"]
    db = base_injection(regle, [0.0] * len(c["seeds"]), 0.0, 0.0, rng, base=base)

    def put(k, x):
        db[k] = int(min(max(round(x), 0), n)) / n
    for sd in c["seeds"]:
        d = mu + tau * rng.standard_normal()
        put(_cle("lam0", p, sd), base)
        put(_cle("lam09", p, sd), base + d)
        put(_cle("sham09", p, sd), base + f * d + sigma_e * rng.standard_normal())
        if c.get("bras_apparie", False):
            put(_cle(BRAS_APPARIE, p, sd), base)
        if chemin_rate:                                 # décision 9 : le contrôle du chemin RATÉ (aucun gain sans délai)
            db[_cle("td0_d0", p, sd)] = db[_cle_ref("lr0_reference_d0", sd)]
    return db


def calibrer_lecture_v2(regle, mu, tau, sigmas_e, fs, n_rep, graine):
    """Calibration de la lecture d'UN pas sous le modèle v2 (0 simulation) : par σ_e et par f, la fréquence de chaque
    branche de la VRAIE lecture. Exigé avant le sceau (règle v2) : P(TRANSPORTE | f = 0) et P(PAS_PLUS_GROS | f = 1)
    ≥ 0,8 à σ_e = τ ; fausses lectures publiées."""
    rng = np.random.default_rng(int(graine))
    p = regle["cellule"]["pas_primaire"]
    out = {"modele": "v2 : sans bruit d'éval ; d ~ N(mu, tau) ; sham09 = lam0 + f·d + sigma_e·z", "mu_pas": float(mu),
           "tau_pas": float(tau), "graine": int(graine), "n_rep": int(n_rep), "par_sigma_e": {}}
    for se in sigmas_e:
        par_f = {}
        for f in fs:
            comptes = {b: 0 for b in BRANCHES_PAS}
            for _ in range(int(n_rep)):
                comptes[classify_pas(base_injection_v2(regle, mu, tau, se, f, rng), regle, p)["branche"]] += 1
            par_f[str(f)] = {b: comptes[b] / n_rep for b in BRANCHES_PAS if comptes[b]}
        out["par_sigma_e"][str(se)] = par_f
    # Décision 9 (2026-10-14) : la branche CONTROLE_CHEMIN_ECHOUE est VISITÉE -- un chemin raté doit l'emporter sur
    # toute lecture d'effet, quel que soit f (ordre imposé).
    comptes = {b: 0 for b in BRANCHES_PAS}
    for _ in range(int(n_rep)):
        comptes[classify_pas(base_injection_v2(regle, mu, tau, sigmas_e[0], 0.0, rng, chemin_rate=True), regle,
                             p)["branche"]] += 1
    out["chemin_rate"] = {b: comptes[b] / n_rep for b in BRANCHES_PAS if comptes[b]}
    return out


# ---------------------------------------------------------------------------------------------------- le run (déport)
# Lieu = nexus (décision 5). Le déport exécute UNE commande par Job, au sha, dans un pod qui ne voit que les fichiers
# SUIVIS (REF-DEPORT-NEXUS) : d'où une cellule par commande, un fichier par cellule, et les ρ du bras apparié passés en
# ARGUMENT -- calculés sur la batcave depuis les cellules lam0 et lam09 RAPATRIÉES (`rho`), relus et revérifiés à
# l'agrégat. L'agrégat (batcave, aucune simulation) relie chaque fichier au MANIFEST du Job qui l'a produit par son
# sha256, et EXCLUT en le nommant toute cellule sans MANIFEST, d'un autre lieu, d'une autre image, d'un code non nul ou
# d'un arbre sale -- jamais lue. Le pré-vol est une décision FIGÉE dans son propre fichier, prise avant toute autre
# cellule et jamais réécrite.

DOSSIER = "td_step_pilot_r3"
_IP = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")


def _chemin_cellule(nom):
    return str(results_file(DOSSIER, f"{nom}.json"))


def _nom_cellule(bras, pas, sd):
    return f"{bras}_{pas}_seed{sd}"


def _n_blocs(c):
    return int(c["episodes_td"]) // int(c["bloc_episodes"])


def _refus_cellule(bras, pas, sd, c, rho):
    """Refus EN TÊTE d'une cellule entraînée (aucune construction, aucun import de torch)."""
    if bras not in BRAS_ENTRAINES + (BRAS_APPARIE,):
        raise ValueError(f"bras {bras!r} inconnu de R3 : {list(BRAS_ENTRAINES) + [BRAS_APPARIE]}")
    if bras == BRAS_APPARIE and not c.get("bras_apparie", False):
        raise ValueError("bras apparié absent de la règle")
    if pas not in (c["pas_primaire"], c["pas_secondaire"]):
        raise ValueError(f"pas {pas!r} hors règle ({c['pas_primaire']}, {c['pas_secondaire']})")
    if sd not in c["seeds"]:
        raise ValueError(f"seed {sd} hors des seeds scellées {c['seeds'][0]}-{c['seeds'][-1]}")
    if bras == BRAS_APPARIE:
        if rho is None or len(rho) != _n_blocs(c):
            raise ValueError(f"bras apparié : {_n_blocs(c)} multiplicateurs ρ exigés (--rho, calculés par la commande "
                             f"`rho` depuis lam0 et lam09 rapatriés), reçu {None if rho is None else len(rho)}")
        if not all(math.isfinite(x) and x > 0.0 for x in rho):
            raise ValueError(f"ρ non fini ou non positif : {rho}")
    elif rho is not None:
        raise ValueError("--rho n'appartient qu'au bras apparié")


def cellule_r3(bras, pas, sd, regle, rho=None, entraine=None):
    """UNE cellule entraînée, instrumentée, évaluée exhaustivement ; écrit son fichier. `entraine` injectable."""
    c = regle["cellule"]
    _refus_cellule(bras, pas, sd, c, rho)
    from tools.preregister import provenance
    if entraine is None:
        entraine = _train_eval_td_step
    lam, sham, same_tick = _spec(bras, c)
    t0, c0 = time.time(), time.process_time()
    acc640, dose = entraine(sd, lam, c["episodes_td"], c["n_agents"], c["K"], float(c["pas"][pas]),
                            trace_reset_per_episode=c["trace_reset_per_episode"], same_tick=same_tick, sham=sham,
                            mesure_dose=True, eval_exhaustive=True, bloc_dose=c["bloc_episodes"],
                            lr_blocs=(list(rho) if rho is not None else None), controle_delta=(sham is not None))
    ex = dose["eval_exhaustive"]
    if ex["n"] != _n_grille(c):
        raise ValueError(f"grille {ex['n']} ≠ {_n_grille(c)} : la cellule ne mesure pas le dispositif de R3")
    rec = {"bras": bras, "pas": pas, "seed": sd, "acc": ex["succes"] / ex["n"], "succes": int(ex["succes"]),
           "n": int(ex["n"]), "acc640": acc640, "rho": (list(rho) if rho is not None else None), "dose": dose,
           "mur_s": time.time() - t0, "cpu_s": time.process_time() - c0, "environnement": _environnement(c),
           "provenance": provenance()}
    p = _chemin_cellule(_nom_cellule(bras, pas, sd))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(rec, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{bras} {pas} seed {sd} : {rec['succes']}/{rec['n']} ({rec['mur_s']:.0f} s mur) -> {p}", flush=True)
    return rec


def reference_r3(ref, sd, regle, entraine=None):
    """Référence lr 0 : AUCUN entraînement (à lr 0 les paramètres ne bougent pas -- témoin dans les tests), éval
    exhaustive seule sur le substrat construit au même seed ; écrit son fichier."""
    c = regle["cellule"]
    if ref not in REFERENCES:
        raise ValueError(f"référence {ref!r} inconnue : {list(REFERENCES)}")
    if sd not in c["seeds"]:
        raise ValueError(f"seed {sd} hors des seeds scellées")
    from tools.preregister import provenance
    if entraine is None:
        entraine = _train_eval_td_step
    t0, c0 = time.time(), time.process_time()
    _, dose = entraine(sd, 0.0, 0, c["n_agents"], c["K"], 0.0, eval_batches=0,
                       trace_reset_per_episode=c["trace_reset_per_episode"], same_tick=(ref == "lr0_reference_d0"),
                       eval_exhaustive=True)
    ex = dose["eval_exhaustive"]
    rec = {"ref": ref, "seed": sd, "acc": ex["succes"] / ex["n"], "succes": int(ex["succes"]), "n": int(ex["n"]),
           "dose": dose, "mur_s": time.time() - t0, "cpu_s": time.process_time() - c0,
           "environnement": _environnement(c), "provenance": provenance()}
    p = _chemin_cellule(f"{ref}_seed{sd}")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(rec, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return rec


def rho_argument(pas, sd, regle):
    """L'argument --rho du bras apparié (batcave, aucune simulation) : ρ_b depuis les cellules lam09 et lam0 RAPATRIÉES
    du même seed et du même pas, écrits en repr exacte (un flottant relu dans le pod est le même au bit)."""
    lire = lambda b: json.load(open(_chemin_cellule(_nom_cellule(b, pas, sd)), encoding="utf-8"))["dose"]  # noqa: E731
    rho = rho_blocs(lire("lam09"), lire("lam0"), _n_blocs(regle["cellule"]))
    return ",".join(repr(float(x)) for x in rho)


def _sha256(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _index_manifestes(deport):
    """{(« dossier/fichier » de sortie, sha256): résumé du MANIFEST} -- l'image par son DIGEST seulement (dépôt
    public)."""
    out = {}
    for p in glob.glob(os.path.join(deport, "*", "MANIFEST.json")):
        try:
            m = json.load(open(p, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if "tools.td_step_pilot_r3" not in (m.get("commande") or []):
            continue
        dig = re.search(r"@(sha256:[0-9a-f]{64})", m.get("image") or "")
        cpu = m.get("cpu") or {}
        resume = {"job": m.get("job"), "lieu": m.get("lieu"), "sha": m.get("sha"), "returncode": m.get("returncode"),
                  "image_digest": dig.group(1) if dig else None, "limite_cpu": cpu.get("limite_cpu"),
                  "threads_poses": cpu.get("threads_poses"), "debut_utc": m.get("debut_utc"),
                  "fin_utc": m.get("fin_utc"), "duree_mur_s": m.get("duree_mur_s"),
                  "cpu_user_s": m.get("cpu_user_s")}
        for rel, info in (m.get("fichiers") or {}).items():
            fin = rel.replace("\\", "/").split("/")[-2:]      # dossier/fichier : la racine est celle du déploiement
            if len(fin) == 2 and fin[0] == DOSSIER and isinstance(info, dict) and info.get("sha256"):
                out[("/".join(fin), info["sha256"])] = resume
    return out


def prevol_r3(regle, deport=os.path.join("runs", "deport")):
    """Pré-vol FIGÉ (batcave, aucune simulation), depuis les cellules du seed 1 au pas primaire : unité CPU PAR BRAS,
    décision d'inclure le bras apparié sur son COÛT seul (fraction STRICTEMENT sous le seuil), projection par étape
    (refus `CostTooHighToStart` au-delà du budget). Écrit results/td_step_pilot_r3_prevol.json UNE fois : une décision
    prise ne se réécrit pas (refus si le fichier existe avec un autre contenu).
    P1.b (revue v2) : sur le pilote τ, le temps CPU d'un même bras à dose identique a varié ×5,2 avec la contention
    entre pods (28 à 146 s) -- les cellules du pré-vol doivent donc avoir tourné SEULES : chacune reliée à son MANIFEST,
    et REFUS si deux fenêtres d'exécution se chevauchent."""
    c, s = regle["cellule"], regle["seuils"]
    sd, p = c["seeds"][0], c["pas_primaire"]
    bras = list(BRAS_ENTRAINES) + ([BRAS_APPARIE] if c.get("bras_apparie", False) else [])
    u = {}
    for b in bras:
        q = _chemin_cellule(_nom_cellule(b, p, sd))
        if not os.path.exists(q):
            raise ValueError(f"pré-vol : cellule {os.path.basename(q)} absente -- l'unité est MESURÉE, jamais supposée")
        u[b] = float(json.load(open(q, encoding="utf-8"))["cpu_s"])
    index = _index_manifestes(deport)
    fenetres = {}
    for b in bras:
        q = _chemin_cellule(_nom_cellule(b, p, sd))
        m = index.get((f"{DOSSIER}/{os.path.basename(q)}", _sha256(q)))
        if m is None:
            raise ValueError(f"pré-vol : {os.path.basename(q)} sans MANIFEST -- l'unité doit venir d'un Job tracé")
        fenetres[b] = [m["debut_utc"], m["fin_utc"]]
    simultanees = [(a, b) for i, a in enumerate(bras) for b in bras[i + 1:]
                   if fenetres[a][0] < fenetres[b][1] and fenetres[b][0] < fenetres[a][1]]
    if simultanees:
        raise ValueError(f"pré-vol : cellules SIMULTANÉES {simultanees} -- le temps CPU varie avec la contention entre "
                         "pods (×5,2 sur le pilote τ) : soumettre les cellules du pré-vol UNE À UNE")
    autres = sum(u[b] for b in BRAS_ENTRAINES)
    frac = (u[BRAS_APPARIE] / autres) if (BRAS_APPARIE in u and autres > 0) else None
    retenu = bool(frac is not None and frac < s["fraction_cout_apparie_max"])
    bras_run = list(BRAS_ENTRAINES) + ([BRAS_APPARIE] if retenu else [])
    n_par_bras = {b: len(c["seeds"]) for b in bras_run}
    n_par_bras.update({r: len(c["seeds"]) for r in REFERENCES})
    unites = dict(u)
    unites.update({r: s["unite_reference_s"] for r in REFERENCES})
    pv = {"unites_cpu_par_bras_s": u, "fraction_cout_apparie": frac, "seuil_fraction": s["fraction_cout_apparie_max"],
          "apparie_retenu": retenu, "fenetres_utc": fenetres,
          "projection_etape_s": project_cost_per_arm(unites, n_par_bras, s["budget_etape_s"], safety=s["safety"],
                                                     label="TD-STEP-PILOT-R3 étape"),
          "par_bras": cost_per_arm(unites, n_par_bras, safety=s["safety"])["par_bras"]}
    dest = str(results_file("td_step_pilot_r3_prevol.json"))
    texte = json.dumps(pv, indent=1, ensure_ascii=False, sort_keys=True)
    if os.path.exists(dest) and open(dest, encoding="utf-8").read() != texte:
        raise ValueError("pré-vol déjà FIGÉ avec un autre contenu : une décision prise ne se réécrit pas")
    open(dest, "w", encoding="utf-8").write(texte)
    return pv


def agreger_r3(regle, deport=os.path.join("runs", "deport")):
    """Agrégat (batcave, aucune simulation) : relit les cellules, les relie à leur MANIFEST par sha256, EXCLUT et nomme
    toute cellule hors lieu / hors image / code non nul / arbre sale / sans MANIFEST, revérifie les ρ du bras apparié,
    refuse de mêler deux sha de code, puis lit (`lecture_r3`) et publie results/td_step_pilot_r3.json."""
    c = regle["cellule"]
    index = _index_manifestes(deport)
    db = {"_dose": {}, "_g640": {}, "_temps_s": {}}
    exclues, manifestes, shas = [], {}, set()
    for q in sorted(glob.glob(os.path.join(str(results_file(DOSSIER)), "*.json"))):
        nom = os.path.basename(q)[:-5]
        rec = json.load(open(q, encoding="utf-8"))
        m = index.get((f"{DOSSIER}/{nom}.json", _sha256(q)))
        raison = None
        if m is None:
            raison = "aucun MANIFEST ne porte ce fichier (sha256)"
        elif m["lieu"] != c["lieu"]:
            raison = f"lieu {m['lieu']!r} ≠ {c['lieu']!r}"
        elif c.get("image_digest") and m["image_digest"] != c["image_digest"]:
            raison = f"image {m['image_digest']} ≠ {c['image_digest']}"
        elif m["returncode"] != 0:
            raison = f"code {m['returncode']}"
        elif (rec.get("provenance") or {}).get("dirty") is not False:
            raison = "arbre sale ou provenance absente"
        elif (m.get("limite_cpu") != float(c.get("threads", 1))
              or (m.get("threads_poses") or {}).get("OMP_NUM_THREADS") != str(c.get("threads", 1))):
            raison = (f"fils : limite {m.get('limite_cpu')}, OMP {(m.get('threads_poses') or {}).get('OMP_NUM_THREADS')}"
                      f" ≠ {c.get('threads', 1)} (règle : un fil par cellule)")
        if raison:
            exclues.append({"cellule": nom, "raison": raison})
            continue
        shas.add(m["sha"])
        k = _cle_ref(rec["ref"], rec["seed"]) if "ref" in rec else _cle(rec["bras"], rec["pas"], rec["seed"])
        db[k], db["_dose"][k] = rec["acc"], rec["dose"]
        if rec.get("acc640") is not None:
            db["_g640"][k] = rec["acc640"]
        db["_temps_s"][k] = {"mur_s": rec["mur_s"], "cpu_s": rec["cpu_s"]}
        manifestes[k] = m
    if len(shas) > 1:
        raise ValueError(f"cellules de {len(shas)} sha de code différents : refus d'agréger -- {sorted(shas)}")
    for k in [k for k in list(db) if k.startswith(BRAS_APPARIE + "|")]:          # ρ revérifiés au bit
        _, p, sd = k.split("|")
        p, sd = p[4:], int(sd[5:])
        k9, k0 = _cle("lam09", p, sd), _cle("lam0", p, sd)
        attendu = (rho_blocs(db["_dose"][k9], db["_dose"][k0], _n_blocs(c))
                   if k9 in db["_dose"] and k0 in db["_dose"] else None)
        recu = json.load(open(_chemin_cellule(_nom_cellule(BRAS_APPARIE, p, sd)), encoding="utf-8"))["rho"]
        if attendu is None or [float(x) for x in recu] != [float(x) for x in attendu]:
            exclues.append({"cellule": _nom_cellule(BRAS_APPARIE, p, sd),
                            "raison": "ρ reçu ≠ ρ recalculé depuis lam0 et lam09 de l'agrégat"})
            for champ in (db, db["_dose"], db["_g640"], db["_temps_s"], manifestes):
                champ.pop(k, None)
    pv_path = str(results_file("td_step_pilot_r3_prevol.json"))
    debuts = {k: m["debut_utc"] for k, m in manifestes.items()}
    p1, p2 = c["pas_primaire"], c["pas_secondaire"]
    fins_p1 = [manifestes[k]["fin_utc"] for k in manifestes            # étape 1 = pas primaire ET références
               if f"|pas={p1}|" in k or k.split("|")[0] in REFERENCES]
    debs_p2 = [debuts[k] for k in debuts if f"|pas={p2}|" in k]
    db["_regime"] = {k: v for k, v in c.items() if k != "seeds"}
    db["_regime"].update({
        "pre_vol": json.load(open(pv_path, encoding="utf-8")) if os.path.exists(pv_path) else None,
        "exclues": exclues, "sha_code": sorted(shas), "manifestes": manifestes,
        "etape2_apres_etape1": (min(debs_p2) > max(fins_p1)) if (debs_p2 and fins_p1) else None})
    db["_regime"]["lien_r0"] = _lien_r0(db, c)
    n = _n_grille(c)                                   # d de l'étape 1 : DESCRIPTIF, ne change aucun seuil
    d1 = [int(round((db[_cle("lam09", p1, sd)] - db[_cle("lam0", p1, sd)]) * n)) for sd in c["seeds"]
          if _cle("lam09", p1, sd) in db and _cle("lam0", p1, sd) in db]
    db["_regime"]["d_etape1"] = {"d_pas": d1, "moyenne_pas": statistics.mean(d1) if d1 else None,
                                 "et_pas": statistics.stdev(d1) if len(d1) >= 2 else None,
                                 "tenues_a_l_ecart": {k: (regle["seuils"].get("calibration") or {}).get(k)
                                                      for k in ("mu_pas", "tau_pas")}}
    pv = db["_regime"]["pre_vol"]
    apparie = bool(pv["apparie_retenu"]) if pv else bool(c.get("bras_apparie"))     # pré-vol absent : prudent
    n_cellules = len(c["seeds"]) * 2 * (len(BRAS_ENTRAINES) + int(apparie)) + \
        len(c["seeds"]) * len(REFERENCES)
    db["_design"] = declare_design(
        question=regle["question"],
        replication_unit="seed (une population de %d agents par cellule ; bras appariés par seed)" % c["n_agents"],
        n_independent=len(c["seeds"]),
        links={"accuracy_exhaustive_par_bras": "measured", "dose_chemin_et_net_par_agent": "measured",
               "controle_chemin_td0_d0": "measured", "references_lr0": "measured", "f_hat": "measured"},
        cost_estimate=regle["cout"], control_family=assert_control_family(cells=n_cellules, alpha_family=0.05))
    db["_lecture"] = lecture_r3(db, regle)
    texte = json.dumps(stamp(db, RULE_R3), indent=1, ensure_ascii=False)
    if _IP.search(texte):
        raise ValueError("adresse de type IP dans l'agrégat (dépôt public) : refus d'écrire")
    dest = str(results_file("td_step_pilot_r3.json"))
    open(dest, "w", encoding="utf-8").write(texte)
    return db


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
            "threads_env": {v: os.environ.get(v) for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                                                           "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
            "coeurs_logiques": os.cpu_count()}


def _profil_d_r0(c):
    """Le profil d'effet de R0 au pas 4,0 (lam09 − lam0 par seed, grille 640), ramené en pas de la grille exhaustive :
    base de la calibration par injection AVANT l'étape 1 (après l'étape 1, le profil mesuré le remplace)."""
    verify(RULE_R0)
    r0 = json.load(open(str(results_file("td_step_pilot_r0.json")), encoding="utf-8"))
    n = _n_grille(c)
    return [(r0[f"tdlam|lr0|seed={sd}"] - r0[f"td0|lr0|seed={sd}"]) * n for sd in c["seeds"]]


def main_r3(argv=None):
    """CLI. Dans un pod (une commande par Job) : `cellule --bras B --pas P --seed S [--rho r1,…]`, `reference --ref R
    --seed S`. Sur la batcave, sans simulation : `rho --pas P --seed S` (l'argument du bras apparié), `prevol`,
    `agreger [--deport DIR]`, `calibrer-lecture` (modèle v2 déclaré par la règle), `lecture`."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("cellule")
    a.add_argument("--bras", required=True)
    a.add_argument("--pas", required=True)
    a.add_argument("--seed", type=int, required=True)
    a.add_argument("--rho", default=None)
    r = sp.add_parser("reference")
    r.add_argument("--ref", required=True)
    r.add_argument("--seed", type=int, required=True)
    h = sp.add_parser("rho")
    h.add_argument("--pas", required=True)
    h.add_argument("--seed", type=int, required=True)
    sp.add_parser("prevol")
    g = sp.add_parser("agreger")
    g.add_argument("--deport", default=os.path.join("runs", "deport"))
    sp.add_parser("calibrer-lecture")
    sp.add_parser("lecture")
    x = ap.parse_args(argv)
    regle = verify(RULE_R3)
    if x.cmd == "cellule":
        rho = [float(v) for v in x.rho.split(",")] if x.rho else None
        return cellule_r3(x.bras, x.pas, x.seed, regle, rho=rho)
    if x.cmd == "reference":
        return reference_r3(x.ref, x.seed, regle)
    if x.cmd == "rho":
        arg = rho_argument(x.pas, x.seed, regle)
        print(arg)
        return arg
    if x.cmd == "prevol":
        pv = prevol_r3(regle)
        print(json.dumps(pv, indent=1, ensure_ascii=False))
        return pv
    if x.cmd == "agreger":
        db = agreger_r3(regle, x.deport)
        print(json.dumps(db["_lecture"], indent=1, ensure_ascii=False))
        return db
    if x.cmd == "calibrer-lecture":
        cal = regle["seuils"]["calibration"]
        out = calibrer_lecture_v2(regle, cal["mu_pas"], cal["tau_pas"], cal["sigmas_e_pas"], cal["f"], cal["n_rep"],
                                  cal["graine"])
        dest = str(results_file("td_step_pilot_r3_calibration_lecture.json"))
        json.dump(stamp(out, RULE_R3), open(dest, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(json.dumps(out["par_sigma_e"], indent=1), "\n->", dest)
        return out
    db = json.load(open(str(results_file("td_step_pilot_r3.json")), encoding="utf-8"))
    print(json.dumps(lecture_r3(db, regle), indent=1, ensure_ascii=False))
    return db


if __name__ == "__main__":
    main_r3()
