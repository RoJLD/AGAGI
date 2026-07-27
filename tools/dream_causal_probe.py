"""Sonde d'intervention causale du dreaming (Phase 2). Le dreaming CAUSE-t-il un meilleur sort, ou
corrèle-t-il à la détresse (EDR 093/094) ? Force l'acte + la profondeur du rêve via le hook gated
MambaBatchModel.FORCE_DREAM ; balaye {off,1,4,8} -> courbe dose-réponse de la survie.
Spec : docs/superpowers/specs/2026-06-24-Dream-Causal-Intervention-design.md. Diagnostic causal."""
import os
import sys
import logging
import statistics
from typing import List, Dict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.curriculum_transfer import _sign_test_p
from tools.dreaming_probe import run_era_organ
from src.curriculum.competence import survival_competence
from src.agents.mamba_agent import MambaBatchModel
from src.environments.config import WorldConfig
from src.seed_ai.harness import Harness
from src.graph_rag.async_logger import logger as async_logger
from main_curriculum import _acquire_shared_db

log = logging.getLogger("AGIseed.DreamCausal")


def _paired_ratios(arm: List[float], off: List[float], eps: float = 1e-6):
    """Ratios appariés, **paires non informatives EXCLUES**. Renvoie (ratios, n_ecartees).

    ⚠️ CORRIGÉ le 2026-07-21 (calibration P2.2). L'implémentation précédente faisait
    `arm[i] / max(off[i], 1e-6)` sans condition : une paire **doublement ÉTEINTE** (les deux bras à
    compétence 0, donc AUCUNE différence) rendait `0 / 1e-6 = 0.0`. Or `0.0 != 1.0`, donc elle
    survivait au filtre `r != 1.0` et était comptée comme **DÉFAVORABLE au rêve**.

    Mesuré : deux bras **strictement identiques et éteints** sur 10 seeds rendaient
    `CAUSE_NUISIBLE, ratio 0.0, sign_p 0.00195`. Un contrôle qui ne peut pas rendre NEUTRE — classe E1,
    dans l'instrument qui a produit le verdict d'EDR-095. Le défaut agit dans les DEUX sens : sur un jeu
    où le rêve aide dans 4 paires informatives sur 4, six paires éteintes empoisonnaient la médiane et
    gonflaient le dénominateur du test de signe -> verdict NEUTRE au lieu de bénéfique.

    ✅ **EDR-095 n'est PAS affecté** : ses bras publient `off ∈ [0.113, 0.165]` et forcés
    `∈ [0.055, 0.090]` — séparation parfaite, **aucun zéro**, donc aucune paire éteinte. Sa conclusion
    tient. On ne peut le dire que parce qu'il a publié ses VALEURS ABSOLUES."""
    m = min(len(arm), len(off))
    out, ecartees = [], 0
    for i in range(m):
        a, o = float(arm[i]), float(off[i])
        if a <= eps and o <= eps:
            ecartees += 1                      # les deux éteints : aucune information, pas un "contre"
            continue
        out.append(a / max(o, eps))
    return out, ecartees


def dose_response_verdict(per_arm: Dict, eps: float = 0.02) -> Dict:
    """Verdict ancré sur le bras le plus profond (max K) vs off, apparié par seed. Renvoie aussi la
    courbe dose-réponse complète (ratio apparié médian de chaque bras-K vs off)."""
    off = per_arm.get("off", [])
    ks = sorted(k for k in per_arm if k != "off")
    if not off or not ks:
        return {"ratio": 1.0, "sign_p": 1.0, "n_favorable": 0, "n": 0, "n_ecartees": 0,
                "verdict": "NEUTRE", "ratios_par_K": {}}
    ratios_par_K = {}
    for k in ks:
        pr, _ = _paired_ratios(per_arm[k], off)
        ratios_par_K[str(k)] = float(statistics.median(pr)) if pr else 1.0
    pr, ecartees = _paired_ratios(per_arm[ks[-1]], off)   # bras le plus profond
    if not pr:                                           # TOUTES les paires non informatives
        return {"ratio": 1.0, "sign_p": 1.0, "n_favorable": 0, "n": 0, "n_ecartees": ecartees,
                "verdict": "INCONCLUSIVE_DEGENERATE", "ratios_par_K": ratios_par_K,
                "why": f"les {ecartees} paires ont les DEUX bras éteints : aucune information"}
    ratio = float(statistics.median(pr))
    effective = [r for r in pr if r != 1.0]
    sign_p = _sign_test_p(sum(1 for r in effective if r > 1.0), len(effective))
    n_fav = sum(1 for r in pr if r > 1.0)
    if ratio > 1.0 + eps and sign_p < 0.1:
        verdict = "CAUSE_BENEFIQUE"
    elif ratio < 1.0 - eps and sign_p < 0.1:
        verdict = "CAUSE_NUISIBLE"
    else:
        verdict = "NEUTRE"
    return {"ratio": ratio, "sign_p": sign_p, "n_favorable": n_fav, "n": len(pr),
            "n_ecartees": ecartees, "verdict": verdict, "ratios_par_K": ratios_par_K}


def run_causal(seeds, target, num_agents, max_ticks, shared_db, ks=(1, 4, 8)) -> Dict:
    """Par seed, balaye les bras ["off", *ks] à organe ON (100%) + sweet spot. Pose FORCE_DREAM
    AVANT l'ère, le REMET à None en finally (anti-pollution). Survie appariée par seed -> verdict."""
    arms = ["off", *[int(k) for k in ks]]
    per_arm = {arm: [] for arm in arms}
    for seed in seeds:
        for arm in arms:
            MambaBatchModel.FORCE_DREAM = arm if arm == "off" else int(arm)
            try:
                stats = run_era_organ(target, seed, 1.0, 0.25, 3.0, num_agents, max_ticks, shared_db)
            finally:
                MambaBatchModel.FORCE_DREAM = None      # OBLIGATOIRE : etat global de classe
            per_arm[arm].append(survival_competence(stats))
        log.info("  seed=%s survie %s", seed,
                 {str(a): round(per_arm[a][-1], 3) for a in arms})
    verdict = dose_response_verdict(per_arm)
    return {**verdict, "per_arm": {str(a): v for a, v in per_arm.items()},
            "config": {"target": target, "seeds": [int(s) for s in seeds], "ks": list(ks),
                       "num_agents": num_agents, "max_ticks": max_ticks}}


def main() -> Dict:
    os.environ["AGISEED_QUIET_LOG"] = "1"     # anti-segfault + vitesse, AVANT start()
    target = os.environ.get("DC_TARGET", "stoneage")
    seeds = [int(s) for s in os.environ.get("DC_SEEDS", "0,1,2").split(",") if s.strip()]
    ks = tuple(int(k) for k in os.environ.get("DC_KS", "1,4,8").split(",") if k.strip())
    num_agents = int(os.environ.get("DC_NUM_AGENTS", "40"))
    max_ticks = int(os.environ.get("DC_MAX_TICKS", "400"))

    async_logger.start()
    try:
        shared_db = _acquire_shared_db()
        log.info("=== Sonde causale : cible=%s seeds=%s ks=%s agents=%d ticks=%d ===",
                 target, seeds, ks, num_agents, max_ticks)
        result = run_causal(seeds, target, num_agents, max_ticks, shared_db, ks=ks)
    finally:
        async_logger.stop()

    h = Harness(seed=min(seeds) if seeds else 0, name="dream_causal", with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    log.info("VERDICT=%s ratio(Kmax/off)=%.3f sign_p=%.3f | courbe=%s -> %s",
             result["verdict"], result["ratio"], result["sign_p"], result["ratios_par_K"], path)
    return result


def run_founder_matched(seeds, target="stoneage", num_agents=25, max_ticks=80, k=8,
                        organ_fraction=1.0, metab=0.25, payoff=3.0, out_path=None) -> Dict:
    """Compare `off` vs `FORCE_DREAM=k` sur la COHORTE FONDATRICE seule (EDR-DREAM-001).

    POURQUOI CE BRAS EXISTE : `survival_competence` est la médiane des âges sur TOUS les agents de
    l'ère, donc une **statistique de POPULATION**. Or le rêve forcé multiplie `n_lived` par ~13-16
    (mesuré) : la métrique compare alors deux populations de compositions incomparables, dont la
    plupart des membres sont nés tard et ont un âge mécaniquement faible. C'est ce qui a produit le
    verdict `CAUSE_NUISIBLE` d'EDR-095, réfuté par ce bras.

    ⚠️ Restreindre aux « N plus vieux » NE CORRIGE RIEN — c'est une sélection sur la variable de
    SORTIE à des quantiles incomparables (top 26 % d'un côté, top 1.6 % de l'autre). Seule l'identité
    (`founder`, posé à t=0 dans `run_era_organ`) permet un appariement honnête.

    Deux tests : SIGNE (robuste, jette l'amplitude) et WILCOXON signé (utilise les magnitudes, donc
    plus puissant quand les écarts sont larges — c'est le test qu'utilise `_compare` pour le fil S2).

    PERSISTE le résultat : sans artefact, des chiffres publiés ne sont re-dérivables d'aucun fichier —
    le défaut relevé sur `champion_body` (EDR-S2-012)."""
    import json
    from src.seed_ai.s2_stats import wilcoxon_signed_rank

    rows = []
    for seed in seeds:
        cell = {"seed": int(seed)}
        for arm in ("off", int(k)):
            MambaBatchModel.FORCE_DREAM = arm if arm == "off" else int(arm)
            try:
                stats = run_era_organ(target, seed, organ_fraction, metab, payoff,
                                      num_agents, max_ticks, shared_db=None)
            finally:
                MambaBatchModel.FORCE_DREAM = None
            ages = [a["age"] for a in stats]
            fond = [a["age"] for a in stats if a.get("founder")]
            key = "off" if arm == "off" else "on"
            cell[f"{key}_n_lived"] = len(ages)
            cell[f"{key}_med_all"] = float(statistics.median(ages)) if ages else 0.0
            cell[f"{key}_med_founder"] = float(statistics.median(fond)) if fond else 0.0
            cell[f"{key}_n_founder"] = len(fond)
        rows.append(cell)
        log.info("  seed=%s n_lived %s->%s | fondateurs %.1f->%.1f", seed,
                 cell["off_n_lived"], cell["on_n_lived"],
                 cell["off_med_founder"], cell["on_med_founder"])

    def _pair(key):
        o = [r[f"off_{key}"] for r in rows]
        n = [r[f"on_{key}"] for r in rows]
        diffs = [a - b for a, b in zip(n, o)]
        n_fav = sum(1 for d in diffs if d > 0)
        eff = [d for d in diffs if d != 0]
        _w, p_wil = wilcoxon_signed_rank(diffs)
        return {"med_off": float(statistics.median(o)), "med_on": float(statistics.median(n)),
                "ratio": float(statistics.median(n)) / max(float(statistics.median(o)), 1e-9),
                "n_favorable": n_fav, "n": len(diffs),
                "sign_p": _sign_test_p(n_fav, len(eff)), "wilcoxon_p": float(p_wil)}

    out = {"rows": rows, "config": {"target": target, "seeds": [int(s) for s in seeds], "k": int(k),
                                    "num_agents": num_agents, "max_ticks": max_ticks},
           "med_all": _pair("med_all"), "med_founder": _pair("med_founder"),
           "n_lived": _pair("n_lived")}
    if out_path:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2)
        log.info("artefact persiste -> %s", out_path)
    return out

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
