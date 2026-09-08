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


def _fmt_mediane(v) -> str:
    """Rend une médiane de cellule pour le LOG. `None` = cohorte vide, donc médiane INEXISTANTE :
    elle s'affiche `NON-MESURE` et jamais `0.0` — un journal qui écrit `0.0` là où rien n'a été
    mesuré fabrique la même affirmation négative que l'artefact, à l'endroit où un humain la lit."""
    return "NON-MESURE" if v is None else f"{float(v):.1f}"


_ALPHA_DEFAUT = 0.1


def _sign_p_plancher(n_paires: int) -> float:
    """p-valeur la PLUS BASSE que le test de signe bilatéral PEUT rendre avec `n_paires` paires
    (toutes tombant du même côté). C'est une propriété du **DESIGN** : elle ne dépend d'AUCUNE donnée.

    Vaut `2 / 2**n`, donc **1.0 à n ≤ 1** (le test n'a alors AUCUNE résolution : il rend 1.0 pour
    toute donnée possible), 0.5 à n=2, **0.25 à n=3** (le défaut `DC_SEEDS=0,1,2`), 0.125 à n=4,
    0.0625 à n=5. Si ce plancher est déjà ≥ α, aucune configuration des mesures ne peut trancher :
    un NEUTRE rendu là n'est pas une absence d'effet MESURÉE, c'est une absence de PUISSANCE."""
    return _sign_test_p(n_paires, n_paires) if n_paires > 0 else 1.0


def dose_response_verdict(per_arm: Dict, eps: float = 0.02, alpha: float = _ALPHA_DEFAUT) -> Dict:
    """Verdict ancré sur le bras le plus profond (max K) vs off, apparié par seed. Renvoie aussi la
    courbe dose-réponse complète (ratio apparié médian de chaque bras-K vs off).

    ⚠️ TROIS CORRECTIFS le 2026-09-08, tous la MÊME famille : une **absence de mesure** ressortait
    avec la valeur qui signifie « mesure nulle » — le biais négatif systématique du dépôt.

    **(a) ENTRÉE VIDE → LÈVE** (avant : `{'verdict': 'NEUTRE', 'ratio': 1.0, 'sign_p': 1.0, 'n': 0}`).
    Un `per_arm` sans bras `off`, sans bras K, ou dont l'`off` est vide n'est pas une égalité
    observée : c'est un appel invalide. La branche NEUTRE fabriquait l'affirmation de FOND « le rêve
    n'a aucun effet causal » **sans qu'aucune ère n'ait été comparée** — c'est exactement ce que
    rendait `run_causal` quand sa garde consommait des itérateurs `seeds`/`ks`.

    **(b) BRAS SANS PAIRE INFORMATIVE → `ratios_par_K[k] = None`, PAS 1.0.** 1.0 est la valeur qui
    signifie « aucun effet » : la publier pour un bras dont TOUTES les paires sont doublement
    éteintes mélangeait « mesure nulle » et « pas de mesure » dans la MÊME courbe. `n_par_K` et
    `n_ecartees_par_K` rendent la distinction vérifiable bras par bras, et `None` (≠ `nan`) reste
    sérialisable en JSON — l'artefact de provenance est écrit par `Harness.save`.

    **(c) SOUS-PUISSANCE STRUCTURELLE NOMMÉE.** Le verdict causal exige `sign_p < alpha` ; le
    plancher du test de signe vaut `2/2**n`, donc **sous 5 paires le verdict ne PEUT pas être autre
    chose que NEUTRE**, quelle que soit l'amplitude (question A du pré-vol : l'instrument ne produit
    alors qu'UNE des deux issues). `underpowered` porte cette propriété du DESIGN — calculée sur le
    NOMBRE DE PAIRES, jamais sur les valeurs — et `sign_p_plancher` la chiffre.
    À **n < 2** le test n'a même aucune RÉSOLUTION (il rend 1.0 pour toute donnée imaginable) : le
    verdict devient `INCONCLUSIVE_UNDERPOWERED`, parce qu'un NEUTRE tiré d'une seule paire ne mesure
    rien, alors qu'un NEUTRE tiré de 10 paires appariées est un vrai nul mesuré. La frontière du
    VERDICT est posée là — et pas à n<5 — parce qu'à partir de 2 paires la p-valeur VARIE avec les
    données : le NEUTRE y est une lecture réelle, seulement sous-puissante, et le drapeau
    `underpowered` (True jusqu'à n=4 inclus) suffit à l'annoncer sans écraser la lecture.

    ⚠️ **DEUX CORRECTIFS DE RÉFUTATION le 2026-09-08** (sondes du réfutateur, pas relecture).

    **(d) LE DÉNOMINATEUR DU TEST N'ÉTAIT PAS CELUI QUI ÉTAIT PUBLIÉ.** Le test de signe JETTE les
    ex æquo (`effective = [r for r in pr if r != 1.0]`), mais `n`, `underpowered` et
    `sign_p_plancher` étaient tous calculés sur `len(pr)`. Ils décrivaient donc un test qui n'a PAS
    tourné. Réponse connue : `off=[0.10]*6` contre `[0.10,0.10,0.10,0.20,0.20,0.20]` rendait
    `NEUTRE, ratio 1.5, sign_p 0.25, n=6, underpowered=False, sign_p_plancher=0.031` — alors que le
    test de signe a tourné sur **3** paires, dont le plancher vaut 0.25, soit **≥ α** : ce NEUTRE ne
    POUVAIT pas être autre chose, et le drapeau censé le dire affirmait le contraire. Les ex æquo ne
    sont pas exotiques ici : `survival_competence` est une médiane d'âges ENTIERS / 200, donc une
    grille discrète — en régime plancher, **13.9 %** des paires sont ex æquo sous H0, et à n=5 (le
    premier n déclaré « puissant ») le drapeau ment dans **52.8 %** des tirages (2000 tirages/point).
    Sont donc publiés : `n_effectif` (le VRAI dénominateur de `sign_p`), `n_ex_aequo`,
    `sign_p_plancher_effectif` et `sans_resolution`. Le VERDICT ne bouge pas — il reste ancré sur
    `len(pr)`, contrainte gelée par `test_run_causal_at_its_DEFAULT_seed_count...` et par
    `..._READS_the_dose_response_it_claims` (bras identiques sur 10 seeds = NEUTRE mesuré).

    **(e) BRAS DE LONGUEURS DIFFÉRENTES → LÈVE** au lieu d'être TRONQUÉS par le `min()` de
    `_paired_ratios`. L'appariement est POSITIONNEL (aucun seed n'est porté par `per_arm`) : deux
    bras de longueurs différentes ne se contentent pas de perdre des paires, ils comparent
    **arm[i] au off d'un AUTRE seed**. Mesuré : `run_causal(seeds=[0,1,2], ks=(8,8))` remplissait le
    bras 8 avec 6 valeurs contre 3 en `off` et rendait `ratio 3.0` sur un appariement décalé."""
    off = list(per_arm.get("off", []))
    ks = sorted(k for k in per_arm if k != "off")
    if not off or not ks:
        raise ValueError(
            f"dose_response_verdict : argument degenere (n_off={len(off)} n_bras_K={len(ks)}) -- "
            "aucune paire ne peut etre formee, donc AUCUNE comparaison n'a eu lieu ; ne pas "
            "confondre avec une egalite OBSERVEE entre les bras.")
    dents = {str(k): len(per_arm[k]) for k in ks if len(per_arm[k]) != len(off)}
    if dents:
        raise ValueError(
            f"dose_response_verdict : argument degenere -- bras de longueur != off ({len(off)}) : "
            f"{dents}. L'appariement est POSITIONNEL : tronquer par min() comparerait arm[i] au off "
            "d'un AUTRE seed. Ni une egalite OBSERVEE, ni une simple perte de paires.")
    ratios_par_K, n_par_K, n_ecartees_par_K = {}, {}, {}
    for k in ks:
        pr_k, ec_k = _paired_ratios(per_arm[k], off)
        ratios_par_K[str(k)] = float(statistics.median(pr_k)) if pr_k else None
        n_par_K[str(k)] = len(pr_k)
        n_ecartees_par_K[str(k)] = ec_k
    profond = per_arm[ks[-1]]                            # bras le plus profond
    pr, ecartees = _paired_ratios(profond, off)
    courbe = {"ratios_par_K": ratios_par_K, "n_par_K": n_par_K,
              "n_ecartees_par_K": n_ecartees_par_K}
    plancher = _sign_p_plancher(len(pr))
    underpowered = bool(plancher >= alpha)
    effective = [r for r in pr if r != 1.0]              # le test de signe JETTE les ex aequo
    plancher_eff = _sign_p_plancher(len(effective))      # plancher du test qui a REELLEMENT tourne
    resolution = {"n_effectif": len(effective), "n_ex_aequo": len(pr) - len(effective),
                  "sign_p_plancher_effectif": plancher_eff,
                  "sans_resolution": bool(plancher_eff >= alpha)}
    if not pr:                                           # TOUTES les paires non informatives
        return {"ratio": 1.0, "sign_p": 1.0, "n_favorable": 0, "n": 0, "n_ecartees": ecartees,
                "verdict": "INCONCLUSIVE_DEGENERATE", "underpowered": underpowered,
                "sign_p_plancher": plancher, "alpha": alpha,
                "why": f"les {ecartees} paires ont les DEUX bras éteints : aucune information",
                **resolution, **courbe}
    ratio = float(statistics.median(pr))
    sign_p = _sign_test_p(sum(1 for r in effective if r > 1.0), len(effective))
    n_fav = sum(1 for r in pr if r > 1.0)
    if ratio > 1.0 + eps and sign_p < alpha:
        verdict = "CAUSE_BENEFIQUE"
    elif ratio < 1.0 - eps and sign_p < alpha:
        verdict = "CAUSE_NUISIBLE"
    elif len(pr) < 2:                                    # AUCUNE resolution : sign_p ≡ 1.0
        verdict = "INCONCLUSIVE_UNDERPOWERED"
    else:
        verdict = "NEUTRE"
    out = {"ratio": ratio, "sign_p": sign_p, "n_favorable": n_fav, "n": len(pr),
           "n_ecartees": ecartees, "verdict": verdict, "underpowered": underpowered,
           "sign_p_plancher": plancher, "alpha": alpha, **resolution, **courbe}
    if underpowered:
        out["why"] = (
            f"design SOUS-PUISSANT : {len(pr)} paire(s) appariees, le test de signe ne peut pas "
            f"descendre sous {plancher:.6g} (seuil {alpha}) quelles que soient les valeurs -- ce "
            f"verdict '{verdict}' ne distingue PAS « pas d'effet » de « pas assez de seeds ».")
    if resolution["sans_resolution"]:
        out["why_resolution"] = (
            f"le sign_p publie ({sign_p:.6g}) a ete calcule sur {len(effective)} paire(s) et non "
            f"sur les {len(pr)} annoncees par 'n' ({resolution['n_ex_aequo']} ex aequo exacts sont "
            f"JETES par le test de signe) : son plancher reel est {plancher_eff:.6g} >= {alpha}, "
            "donc AUCUNE valeur n'aurait pu le faire trancher. Fait sur le test, PAS un verdict : "
            "un ratio strictement egal a 1.0 sur des paires toutes ex aequo reste un nul MESURE.")
    return out


def run_causal(seeds, target, num_agents, max_ticks, shared_db, ks=(1, 4, 8)) -> Dict:
    """Par seed, balaye les bras ["off", *ks] à organe ON (100%) + sweet spot. Pose FORCE_DREAM
    AVANT l'ère, le REMET à None en finally (anti-pollution). Survie appariée par seed -> verdict.

    ⚠️ Le nombre de SEEDS est le nombre de paires : il fixe la puissance. `dose_response_verdict`
    renvoie `underpowered` / `sign_p_plancher`, propagés tels quels ici — sous 5 seeds le verdict ne
    peut être que NEUTRE, quelle que soit l'amplitude (`DC_SEEDS=0,1,2` par défaut est dans ce cas)."""
    # GARDE D'ARGUMENTS, EN TETE (2026-09-06). Orchestrateur : il n'entraine pas lui-meme mais
    # AGREGE en verdict -- une cohorte/liste de seeds vide produit une agregation VIDE que l'aval
    # lit comme une mesure (biais negatif systematique). Refus instantane, avant tout appel de run.
    # ⚠️ MATERIALISER AVANT DE TESTER (corrige le 2026-09-08). L'ecriture precedente
    # `if not list(seeds) or not list(ks)` CONSOMMAIT ses deux entrees : passees en iterateur
    # (map/zip/generateur de seeds calcules), la garde passait, puis la boucle tournait a VIDE
    # (seeds) ou n'ouvrait que le bras `off` (ks) -- et `dose_response_verdict` rendait
    # {'verdict': 'NEUTRE', 'n': 0}, l'affirmation de FOND « le reve n'a aucun effet causal » sans
    # qu'aucune ere n'ait ete comparee. Aggravant sur `ks` : les eres `off` etaient REELLEMENT
    # simulees (cout paye) avant que le nul ne soit fabrique. La garde ECRITE POUR empecher un
    # negatif fabrique le fabriquait donc elle-meme. Meme classe que `evo_memory_inworld.run_contrast`.
    # ⚠️ DUPLICATS : REFUS (ajout du refutateur, 2026-09-08). Mesure, injection a dose connue :
    #   * `run_causal([0,0,0,0,0], ks=(8,))` rendait **CAUSE_BENEFIQUE, sign_p=0.0625, n=5** a partir
    #     d'UN SEUL tirage -- le seed determine entierement l'ere, donc 5 copies ne sont pas 5
    #     replicats. Et 5 est exactement le n a partir duquel cette sonde s'autorise un verdict
    #     causal : le duplicat ne gonfle pas le n, il FRANCHIT la frontiere du verdict.
    #   * `ks=(8,8)` lancait 9 eres au lieu de 6 (cout double) et remplissait le bras 8 avec 6
    #     valeurs contre 3 en `off` -> `_paired_ratios` tronquait par min() et appariait le bras du
    #     seed 0 au `off` du seed 1.
    # Meme classe que le refus de seeds dupliques deja en place dans `run_contrast` -- jamais
    # retro-applique ici (classe E14). Refus et pas dedup silencieux : le n demande ne serait pas
    # celui qui est mesure.
    seeds = list(seeds)
    ks = list(ks)
    if not seeds or not ks or int(num_agents) <= 0 or int(max_ticks) <= 0:
        raise ValueError(
            f"run_causal : argument degenere (n_seeds={len(seeds)} n_ks={len(ks)} num_agents={num_agents} max_ticks={max_ticks}) -- aucune mesure possible ; "
            "ne pas confondre avec une mesure nulle OBSERVEE.")
    dbl_s = [s for s in dict.fromkeys(seeds) if seeds.count(s) > 1]
    dbl_k = [k for k in dict.fromkeys(int(x) for x in ks) if [int(x) for x in ks].count(k) > 1]
    if dbl_s or dbl_k:
        raise ValueError(
            f"run_causal : argument degenere -- seeds dupliques {dbl_s} / ks dupliques {dbl_k}. "
            "Le seed determine ENTIEREMENT l'ere : un seed repete est le MEME tirage, pas un "
            "replicat (il ferait franchir la frontiere n>=5 du verdict causal a un n=1 reel), et "
            "un K repete desapparie le bras (2x plus de valeurs que `off`, tronquees par min()).")
    arms = ["off", *[int(k) for k in ks]]
    per_arm = {arm: [] for arm in arms}
    for seed in seeds:
        for arm in arms:
            MambaBatchModel.FORCE_DREAM = arm if arm == "off" else int(arm)
            try:
                stats = run_era_organ(target, seed, 1.0, 0.25, 3.0, num_agents, max_ticks, shared_db)
            finally:
                MambaBatchModel.FORCE_DREAM = None      # OBLIGATOIRE : etat global de classe
            # ⚠️ ERE QUI NE REND RIEN -> REFUS (ajout du 2e refutateur, 2026-09-08). Le meme defaut
            # que celui corrige un etage plus bas dans `run_founder_matched`, jamais retro-applique
            # ici (classe E14) : `survival_competence([])` vaut 0.0 (`src/curriculum/competence.py:18`,
            # `_median_norm` : `if not values or ref <= 0: return 0.0`), et `run_causal` JETTE
            # `len(stats)` pour ne garder que le scalaire. Une ere qui n'a RIEN rendu devenait donc
            # une competence 0.0 STRICTEMENT indiscernable d'une competence 0.0 MESUREE, et
            # `_paired_ratios` n'ecarte une paire que si les DEUX bras sont <= eps -- un seul bras
            # vide passe. Mesure par injection a dose connue, sans monde (bras K=8 rendant [] sur 10
            # seeds, les autres a 40 ticks) : `{'verdict': 'CAUSE_NUISIBLE', 'ratio': 0.0,
            # 'sign_p': 0.001953125, 'n': 10, 'n_ecartees': 0, 'underpowered': False,
            # 'sans_resolution': False}` -- le negatif MAXIMAL et SIGNIFICATIF, sans un seul age lu,
            # et sans qu'aucun des trois drapeaux poses le meme jour ne s'allume.
            # POURQUOI LEVER ET PAS EXCLURE (a l'inverse de `_pair_rows`) : `run_era_organ` rend
            # TOUS les agents, vivants ET morts (FIX A d'EDR-092, `tools/dreaming_probe.py`), donc
            # au MINIMUM les `num_agents` fondateurs. Zero agent est un compte IMPOSSIBLE, pas un
            # petit compte : c'est un etat invalide, pas une mesure manquante. Et `run_causal` ne
            # persiste AUCUNE trace par seed (pas de `rows`), donc exclure retrancherait du `n`
            # publie en silence, sans laisser de quoi diagnostiquer.
            # CAS NEGATIF APPARIE (classe E1) : une cohorte NON VIDE dont tous les agents sont a
            # `age = 0` passe cette garde et rend bien `CAUSE_NUISIBLE` -- l'effondrement MESURE
            # reste prononcable. Gele par
            # `test_run_causal_STILL_says_HARMFUL_on_a_MEASURED_collapse`.
            if not stats:
                raise ValueError(
                    f"run_causal : l'ere n'a rendu AUCUN agent (seed={seed} bras={arm!r}) -- "
                    "`run_era_organ` rend tous les agents, morts compris, donc au minimum les "
                    f"{num_agents} fondateurs. Zero agent est une MESURE ABSENTE, pas une "
                    "extinction OBSERVEE ; `survival_competence([])` vaut 0.0 et fabriquerait "
                    "un effondrement significatif (mesure : CAUSE_NUISIBLE ratio 0.0 "
                    "sign_p 0.00195 sur un bras ou aucun age n'existe).")
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
    # L'aval ne peut pas ignorer la sous-puissance : le defaut `DC_SEEDS=0,1,2` la declenche
    # TOUJOURS (plancher 0.25 > alpha 0.1), donc son NEUTRE n'est pas « pas d'effet causal ».
    if result.get("underpowered"):
        log.warning("ATTENTION -- ce verdict est SOUS-PUISSANT PAR CONSTRUCTION : %s",
                    result.get("why", f"n={result.get('n')} paires, plancher du test de signe "
                                      f"{result.get('sign_p_plancher')}"))
    # Le `n` publie n'est PAS le denominateur du test de signe des qu'il y a des ex aequo (grille
    # discrete de survival_competence) : l'aval doit voir le n REEL, pas seulement le n annonce.
    if result.get("sans_resolution"):
        log.warning("ATTENTION -- sign_p sans RESOLUTION : %s",
                    result.get("why_resolution",
                               f"n_effectif={result.get('n_effectif')} sur n={result.get('n')} "
                               f"(plancher reel {result.get('sign_p_plancher_effectif')})"))
    return result


def _puissance(n_paires: int, n_effectif: int, alpha: float) -> Dict:
    """Propriété du DESIGN d'un test de signe apparié — calculée sur des COMPTES DE PAIRES, jamais
    sur des valeurs. Rendue par `_pair_rows` comme `dose_response_verdict` la rend déjà.

    ⚠️ RÉTRO-APPLICATION (classe E14, mesurée par le 2e réfutateur le 2026-09-08). Le correctif
    (c) du matin avait doté `dose_response_verdict` de `underpowered` / `sign_p_plancher` /
    `sans_resolution`, avec cette justification : « sous 5 paires le verdict ne PEUT pas être
    autre chose que NEUTRE, quelle que soit l'amplitude ». Sa fonction SŒUR du même fichier, qui
    fait EXACTEMENT le même test de signe sur les mêmes grandeurs, n'a rien reçu.

    Ce n'était pas latent : c'est le correctif d'EXCLUSION de l'après-midi qui a rendu le régime
    ATTEIGNABLE. Avant lui, `n` valait toujours `len(rows)` (12 ou 20, largement puissant) ; depuis,
    toute paire non mesurable est retranchée et `n` peut tomber à 1. Mesuré par injection, sans
    monde, sur 11 paires non mesurables sur 12 :

    * 12ᵉ paire FAVORABLE (10 → 20)   → `{ratio 2.0, n 1, sign_p 1.0, wilcoxon_p 1.0,
      statut MESURE_PARTIEL}` ;
    * 12ᵉ paire DÉFAVORABLE (20 → 1)  → `{ratio 0.05, n 1, sign_p 1.0, ...}` — « le rêve divise
      la survie par 20 », accompagné de la p-valeur qui rassure ;
    * 2 paires mesurables, les deux favorables → `sign_p 0.5`, plancher `2/2**2` = 0.5.

    Dans les trois cas, `sign_p` ne POUVAIT valoir que ce qu'il vaut : à n=1 le test rend 1.0 pour
    toute donnée imaginable. Un `sign_p = 1.0` publié nu se lit « pas d'effet » ; c'est le NEUTRE
    fabriqué, par le chemin qu'a ouvert le correctif précédent.

    Deux planchers, parce que deux dénominateurs : `sign_p_plancher` sur les paires APPARIÉES,
    `sign_p_plancher_effectif` sur celles qui ont réellement compté (le test de signe JETTE les
    ex æquo, et `med_*` est une médiane d'âges sur une grille discrète — les ex æquo y sont la
    règle, pas l'exception).

    ⚠️ Ces drapeaux ne touchent NI `statut`, NI `ratio`, NI `sign_p` : la MESURABILITÉ et la
    PUISSANCE sont deux axes orthogonaux, et déplacer un seuil dans le `statut` changerait le
    contrat de toutes les fixtures existantes (classe E14, dans l'autre sens). Même choix que
    `dose_response_verdict`, dont le verdict reste ancré sur `len(pr)`."""
    plancher = _sign_p_plancher(n_paires)
    plancher_eff = _sign_p_plancher(n_effectif)
    return {"alpha": alpha,
            "sign_p_plancher": plancher, "underpowered": bool(plancher >= alpha),
            "sign_p_plancher_effectif": plancher_eff,
            "sans_resolution": bool(plancher_eff >= alpha)}


def _pair_rows(rows: List[Dict], key: str, alpha: float = _ALPHA_DEFAUT) -> Dict:
    """Couche « mesures -> affirmation » de `run_founder_matched` : apparie SEED À SEED les deux
    bras sur la grandeur `key` (`med_all`, `med_founder`, `n_lived`) et rend le bloc publié.

    ⚠️ SORTIE de la fermeture de `run_founder_matched` le 2026-09-08 : elle était une closure sur
    `rows`, donc **aucun artefact publié n'était re-dérivable** de ses propres lignes — on ne
    pouvait vérifier un chiffre qu'en relançant le monde. Fonction PURE de `rows`, elle se calibre
    maintenant par injection directe, et `results/dream_founder_matched_n20.json` se recompute
    depuis son propre `rows` (vérifié : les 7 champs publiés de ses 3 blocs sont identiques).

    ⚠️ DEUX CORRECTIFS DE RÉFUTATION (2026-09-08), la garde de `_paired_ratios` n'ayant JAMAIS
    été rétro-appliquée ici (classe E14) — mesurés par injection, sans monde :

    * **`ratio = 0.0` fabriqué à partir de RIEN.** Sur des ères qui rendent une cohorte VIDE, ou
      sans aucun fondateur, ou deux bras strictement identiques et éteints, les deux médianes
      valent 0.0 et `0.0 / max(0.0, 1e-9)` rendait **0.0** — soit « le rêve ANNULE la survie des
      fondateurs », le négatif maximal, sans qu'aucun âge n'ait été mesuré. C'est mot pour mot le
      défaut corrigé le 2026-07-21 dans `_paired_ratios` (« deux bras identiques et éteints
      rendaient CAUSE_NUISIBLE, ratio 0.0 »), dans la fonction voisine du MÊME fichier.
      Désormais : `ratio = None` + `why`, et le compte de cellules non mesurables est publié.
    * **le `n` publié n'était pas le dénominateur de `sign_p`** (les ex æquo sont jetés) :
      `n_effectif` / `n_ex_aequo` le rendent lisible, comme dans `dose_response_verdict`.

    ✅ Aucun chiffre publié ne bouge : `results/dream_founder_matched_n20.json` n'a AUCUNE
    cellule à zéro ni aucun ex æquo (vérifié) — les deux défauts étaient LATENTS.

    ⚠️ **TROISIÈME CORRECTIF (2026-09-08) : une PAIRE NON MESURABLE n'est plus une paire.**
    Le correctif précédent n'avait bouché qu'UNE des deux portes — le `ratio`, et seulement
    quand c'est le DÉNOMINATEUR qui manque. Les DEUX tests continuaient de tourner sur les
    `0.0` fabriqués par la couche du dessus, donc l'affirmation de fond survivait au correctif
    en changeant simplement de véhicule. Mesuré par injection à dose connue, sans monde :

    * **bras `on` vide sur les 12 seeds** → `{med_off 10.0, med_on 0.0, ratio 0.0,
      n_favorable 0, n 12, sign_p 0.00048828125, wilcoxon_p 0.00252617}` : « le rêve ANNULE la
      survie des fondateurs, p < 0.001 » lu sur un bras où AUCUN âge n'existe.
    * **bras `off` vide sur les 12 seeds** → le `ratio` valait bien `None`, mais
      `n_favorable 12, sign_p 0.00048828125, wilcoxon_p 0.00252617` étaient publiés : le
      négatif fabriqué était devenu un POSITIF fabriqué, au même seuil.
    * **1 seed non mesurable sur 12** (le cas réaliste, et le plus insidieux) → la paire
      absente était comptée comme DÉFAVORABLE : `n_favorable 11, n 12, n_effectif 12,
      sign_p 0.00634765625` au lieu de `11/11, n 11, sign_p 0.0009765625` sur les paires
      réellement mesurées. Numérateur ET dénominateur faux, dans le sens du négatif.
    * **cohortes pleines mais AUCUN fondateur** → `n_cellules_doublement_nulles = 12`, soit
      « les deux bras sont ÉTEINTS », alors que 5 agents par bras avaient vécu : l'échec du
      MARQUAGE `founder` se lisait comme une extinction du monde.

    Règle appliquée : une paire dont un côté n'est pas mesurable est **EXCLUE et NOMMÉE**
    (`n_non_mesurables`, `seeds_non_mesurables_off/on`), jamais lue comme un zéro. `n` est
    désormais le nombre de paires RÉELLEMENT appariées — `n + n_non_mesurables == len(rows)`,
    donc le compte reste recomputable. S'il n'en reste AUCUNE, rien n'est affirmé : `statut =
    INDETERMINE_AUCUNE_PAIRE_MESURABLE`, et `ratio`/`sign_p`/`wilcoxon_p`/`med_*`/`n_favorable`
    valent `None` — surtout pas `1.0`, qui est la valeur signifiant « aucun effet », ni `0.0`,
    qui est le négatif maximal.

    POURQUOI EXCLURE ET NOMMER PLUTÔT QUE LEVER : lever détruirait les paires qui, elles, ONT
    été mesurées (11 seeds sur 12 dans le cas réaliste) et l'artefact `rows` qui est la seule
    trace diagnostique de ce qui a échoué — or la persistance est la raison d'être déclarée de
    cette fonction. La garde qui REFUSE est déjà posée en tête, sur les ARGUMENTS ; ici l'entrée
    est une mesure manquante, pas un appel invalide."""
    # GARDE D'ARGUMENTS, EN TETE, avant toute lecture de cellule. `rows` vide n'est PAS un
    # INDETERMINE (il n'y a rien a ne pas savoir) : c'est un appel invalide, et le distinguer
    # importe -- sans cette garde, `_pair_rows([], 'med_founder')` rendrait le bloc
    # INDETERMINE_AUCUNE_PAIRE_MESURABLE, c.-a-d. « 0 paire sur 0 mesurable », qui se lit comme un
    # constat sur des donnees alors qu'aucune donnee n'a ete fournie. Meme famille que la garde en
    # tete de `dose_response_verdict`. `key` est ferme : une faute de frappe leverait sinon un
    # KeyError au fond d'une comprehension, sans nommer ni la cause ni les valeurs admises.
    from src.seed_ai.s2_stats import wilcoxon_signed_rank
    _CLES = ("med_all", "med_founder", "n_lived")
    if not rows or key not in _CLES:
        raise ValueError(
            f"_pair_rows : argument degenere (n_rows={len(rows)} key={key!r}, attendu parmi "
            f"{_CLES}) -- aucune paire ne peut etre formee, donc AUCUNE comparaison n'a eu lieu ; "
            "ne pas confondre avec une absence de mesure OBSERVEE (statut INDETERMINE).")
    # ⚠️ `seed` FAIT PARTIE des champs exiges (ajout du 2e refuteur, 2026-09-08). Il ne l'etait pas,
    # et il est pourtant lu DEUX lignes plus bas (`seeds_l`) puis republie dans
    # `seeds_non_mesurables_off/on` : une ligne sans `seed` traversait la garde et levait un
    # `KeyError: 'seed'` NU au fond de la fonction -- mesure. Ce n'est pas cosmetique : la garde
    # existe pour qu'un appel invalide soit refuse EN TETE avec sa cause nommee, et c'est
    # precisement l'identifiant qui sert a DIAGNOSTIQUER quelles cellules ont ete exclues qui
    # echappait au controle. Meme famille que les champs de mesurabilite ci-dessous.
    manquants = sorted({champ for r in rows for champ in ("seed",) if champ not in r}
                       | {f"{bras}_{champ}" for r in rows for bras in ("off", "on")
                          for champ in (key, "n_lived", "n_founder") if f"{bras}_{champ}" not in r})
    if manquants:
        raise ValueError(
            f"_pair_rows : lignes incompletes, champs absents {manquants} -- la MESURABILITE se "
            "lit sur `n_lived`/`n_founder` ; sans eux, une cellule non mesuree serait indistinguable "
            "d'une cellule mesuree a zero, ce qui est exactement le defaut corrige le 2026-09-08.")
    seeds_l = [r["seed"] for r in rows]
    o_brut = [r[f"off_{key}"] for r in rows]
    n_brut = [r[f"on_{key}"] for r in rows]
    # MESURABILITE, declaree par grandeur et pas devinee :
    #   * `med_founder` exige au moins UN fondateur dans la cellule (`n_founder > 0`) ;
    #   * `med_all` et `n_lived` exigent au moins UN agent rendu par l'ere (`n_lived > 0`).
    # ⚠️ `n_lived == 0` n'est PAS une extinction OBSERVEE : `run_era_organ` rend TOUS les agents,
    # morts compris (FIX A d'EDR-092, `tools/dreaming_probe.py`), donc au MINIMUM les
    # `num_agents` fondateurs, chacun porteur d'un `age`. Une ere qui rend zero agent est donc
    # une ere qui N'A RIEN RENDU. Sans cette clause, la MEME dose (bras `on` vide sur 12 seeds)
    # que celle qui rend `med_founder` INDETERMINE publiait encore, sur `n_lived`,
    # `ratio 0.0, sign_p 0.00048828125` -- le negatif fabrique aurait simplement change de
    # colonne. Zero agent est un compte IMPOSSIBLE ici, pas un petit compte.
    garde = "n_founder" if key == "med_founder" else "n_lived"

    def _mesuree(i, bras):
        valeur = (o_brut if bras == "off" else n_brut)[i]
        return int(rows[i][f"{bras}_{garde}"]) > 0 and valeur is not None

    # Une paire n'est appariable que si les DEUX cotes sont mesures. L'appariement est
    # POSITIONNEL (seed a seed) : garder le cote mesure d'une paire boiteuse comparerait le
    # bras `off` d'un seed au bras `on` d'un AUTRE -- exactement le defaut (e) corrige dans
    # `dose_response_verdict`.
    idx = [i for i in range(len(rows)) if _mesuree(i, "off") and _mesuree(i, "on")]
    non_mes_off = [seeds_l[i] for i in range(len(rows)) if not _mesuree(i, "off")]
    non_mes_on = [seeds_l[i] for i in range(len(rows)) if not _mesuree(i, "on")]
    provenance = {"n_non_mesurables": len(rows) - len(idx),
                  "seeds_non_mesurables_off": non_mes_off,
                  "seeds_non_mesurables_on": non_mes_on}
    if not idx:
        return {"med_off": None, "med_on": None, "ratio": None, "n_favorable": None,
                "n": 0, "n_effectif": 0, "n_ex_aequo": 0, "n_cellules_doublement_nulles": 0,
                "sign_p": None, "wilcoxon_p": None,
                **_puissance(0, 0, alpha),
                "statut": "INDETERMINE_AUCUNE_PAIRE_MESURABLE",
                "why": (
                    f"AUCUNE des {len(rows)} paires n'est mesurable sur `{key}` "
                    f"(off manquant sur les seeds {non_mes_off}, on manquant sur "
                    f"{non_mes_on}) : aucune comparaison n'a eu lieu. Ce n'est ni un effet nul "
                    "OBSERVE (qui vaudrait 1.0) ni un effondrement (qui vaudrait 0.0) -- c'est "
                    "une ABSENCE DE MESURE. Diagnostic dans `rows` : `n_lived`/`n_founder` "
                    "disent si l'ere n'a rien rendu ou si le marquage `founder` a echoue."),
                **provenance}
    o = [float(o_brut[i]) for i in idx]
    n = [float(n_brut[i]) for i in idx]
    diffs = [a - b for a, b in zip(n, o)]
    n_fav = sum(1 for d in diffs if d > 0)
    eff = [d for d in diffs if d != 0]
    _w, p_wil = wilcoxon_signed_rank(diffs)
    med_o, med_n = float(statistics.median(o)), float(statistics.median(n))
    n_nulles = sum(1 for a, b in zip(o, n) if a <= 0.0 and b <= 0.0)
    out = {"med_off": med_o, "med_on": med_n,
           "ratio": (med_n / med_o) if med_o > 0.0 else None,
           "n_favorable": n_fav, "n": len(diffs), "n_effectif": len(eff),
           "n_ex_aequo": len(diffs) - len(eff), "n_cellules_doublement_nulles": n_nulles,
           "sign_p": _sign_test_p(n_fav, len(eff)), "wilcoxon_p": float(p_wil),
           **_puissance(len(diffs), len(eff), alpha),
           "statut": "MESURE" if not provenance["n_non_mesurables"] else "MESURE_PARTIEL",
           **provenance}
    if out["underpowered"]:
        out["why_puissance"] = (
            f"design SOUS-PUISSANT sur `{key}` : {len(diffs)} paire(s) REELLEMENT appariees "
            f"({provenance['n_non_mesurables']} exclue(s) faute de mesure), le test de signe ne "
            f"peut pas descendre sous {out['sign_p_plancher']:.6g} (seuil {alpha}) quelles que "
            f"soient les valeurs -- le sign_p={out['sign_p']:.6g} publie ici ne distingue PAS "
            "« pas d'effet » de « pas assez de paires mesurables ».")
    if out["sans_resolution"] and not out["underpowered"]:
        out["why_resolution"] = (
            f"le sign_p publie ({out['sign_p']:.6g}) a ete calcule sur {len(eff)} paire(s) et non "
            f"sur les {len(diffs)} annoncees par `n` ({out['n_ex_aequo']} ex aequo exacts sont "
            f"JETES par le test de signe) : son plancher reel est "
            f"{out['sign_p_plancher_effectif']:.6g} >= {alpha}, donc AUCUNE valeur n'aurait pu le "
            "faire trancher. Fait sur le TEST, pas un verdict : des paires toutes ex aequo restent "
            "un nul MESURE.")
    if out["ratio"] is None:
        out["why"] = (
            f"ratio INDEFINI : le bras de reference `off` a une mediane de {med_o} sur les "
            f"{len(o)} paires MESUREES ({n_nulles} paire(s) ou les deux bras mesures sont a "
            "zero) -- aucune division n'a de sens ; ne pas lire 0.0 comme « le reve annule la "
            "survie ».")
    if provenance["n_non_mesurables"]:
        out["why_non_mesurables"] = (
            f"{provenance['n_non_mesurables']} paire(s) sur {len(rows)} EXCLUES du test : "
            f"cohorte non mesurable cote off aux seeds {non_mes_off}, cote on aux seeds "
            f"{non_mes_on}. `n`={len(diffs)} est le nombre de paires REELLEMENT appariees ; "
            "les paires absentes ne sont PAS comptees comme defavorables (elles l'etaient "
            "avant le 2026-09-08, ce qui biaisait numerateur ET denominateur vers le negatif).")
    return out


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
    le défaut relevé sur `champion_body` (EDR-S2-012).

    CE QUE LIT L'AVAL. Chacun des trois blocs (`med_all`, `med_founder`, `n_lived`) porte un
    `statut` : `MESURE` · `MESURE_PARTIEL` (des paires ont été exclues, `why_non_mesurables` dit
    lesquelles et pourquoi) · `INDETERMINE_AUCUNE_PAIRE_MESURABLE` (rien n'a pu être apparié —
    `ratio`, `sign_p`, `wilcoxon_p`, `med_*` et `n_favorable` valent alors `None`, et non `0.0`
    ou `1.0`, qui sont des affirmations). `n` est le nombre de paires RÉELLEMENT appariées et
    `n + n_non_mesurables == len(rows)`, donc le compte se recompute. Les WARNING du logger disent
    la même chose à qui lit la sortie plutôt que l'artefact. Le détail cellule par cellule reste
    dans `rows` : `n_lived`/`n_founder` distinguent « l'ère n'a rien rendu » de « le marquage
    `founder` a échoué ».

    ⚠️ **PUISSANCE, axe SÉPARÉ de la mesurabilité** (rétro-application E14, 2026-09-08 — cf.
    `_puissance`). Chaque bloc porte aussi `underpowered` / `sign_p_plancher` /
    `sans_resolution` / `sign_p_plancher_effectif`, comme `dose_response_verdict`. C'est
    l'exclusion elle-même qui rend le régime atteignable : `n` n'est plus `len(rows)`, il peut
    tomber à 1, et un `sign_p = 1.0` y est le seul résultat POSSIBLE, pas un nul observé. Un
    bloc `MESURE_PARTIEL` dont `underpowered` est vrai n'a pas mesuré une absence d'effet — il
    a manqué de paires. Les deux cris sont émis séparément, pour la même raison."""
    # GARDE D'ARGUMENTS, EN TETE (2026-09-06). Orchestrateur : il n'entraine pas lui-meme mais
    # AGREGE en verdict -- une cohorte/liste de seeds vide produit une agregation VIDE que l'aval
    # lit comme une mesure (biais negatif systematique). Refus instantane, avant tout appel de run.
    # ⚠️ MEME correctif que `run_causal` (2026-09-08) : `list(seeds)` dans la CONDITION consommait
    # l'iterateur, la boucle tournait ensuite a vide et `rows` restait vide -> medianes sur liste
    # vide. On materialise AVANT de tester.
    seeds = list(seeds)
    if not seeds or int(num_agents) <= 0 or int(max_ticks) <= 0 or int(k) <= 0:
        raise ValueError(
            f"run_founder_matched : argument degenere (n_seeds={len(seeds)} num_agents={num_agents} max_ticks={max_ticks} k={k}) -- aucune mesure possible ; "
            "ne pas confondre avec une mesure nulle OBSERVEE.")
    dbl = [s for s in dict.fromkeys(seeds) if seeds.count(s) > 1]
    if dbl:                                  # MEME refus que run_causal : un seed repete n'est pas
        raise ValueError(                    # un replicat (np.random.seed) mais il gonfle le n.
            f"run_founder_matched : argument degenere -- seeds dupliques {dbl}. Le seed determine "
            "ENTIEREMENT l'ere : des lignes identiques gonflent le n du test de signe et du "
            "Wilcoxon sans ajouter un seul tirage.")
    import json

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
            # ⚠️ COHORTE VIDE -> None, JAMAIS 0.0 (correctif du 2026-09-08, biais negatif #1 du
            # depot). La mediane d'un ensemble VIDE n'est pas nulle : elle n'existe pas. Ecrire 0.0
            # revient a affirmer « les agents de ce bras ont vecu ZERO tick », l'affirmation
            # NEGATIVE MAXIMALE, alors qu'aucun age n'a ete lu. Mesure par injection avant
            # correctif : bras `on` sans aucun agent sur 12 seeds -> `med_founder {med_off 10.0,
            # med_on 0.0, ratio 0.0, sign_p 0.00048828125, wilcoxon_p 0.00252617}`, soit « le reve
            # force ANNULE la survie des fondateurs, p<0.001 » prononce sur un bras ou RIEN n'a ete
            # mesure. La convention est celle que `dreaming_probe._prevalence_from_stats` s'etait
            # deja donnee (cohorte vide -> INDETERMINE explicite) et qui n'avait jamais ete
            # retro-appliquee ici (classe E14). `None` et pas `nan` : l'artefact est ecrit par
            # `json.dump`, et `nan` produirait un JSON INVALIDE (litteral `NaN`).
            # ⚠️ Le cas n'est PAS folklorique et il est DISCRIMINANT : `run_era_organ` rend TOUS les
            # agents, vivants ET morts (`tools/dreaming_probe.py`, FIX A d'EDR-092), et pose
            # `_founder` sur chacun des `num_agents` fondateurs. Une cohorte vide ou sans fondateur
            # ne peut donc PAS etre une extinction observee : c'est une ere qui n'a rien rendu,
            # c.-a-d. une MESURE ABSENTE. Les deux causes sont distinguees en aval par `n_lived` et
            # `n_founder`, qui restent des COMPTES (zero y est une vraie observation).
            cell[f"{key}_med_all"] = float(statistics.median(ages)) if ages else None
            cell[f"{key}_med_founder"] = float(statistics.median(fond)) if fond else None
            cell[f"{key}_n_founder"] = len(fond)
        rows.append(cell)
        log.info("  seed=%s n_lived %s->%s | fondateurs %s->%s", seed,
                 cell["off_n_lived"], cell["on_n_lived"],
                 _fmt_mediane(cell["off_med_founder"]), _fmt_mediane(cell["on_med_founder"]))
        for key in ("off", "on"):
            if cell[f"{key}_med_founder"] is None or cell[f"{key}_med_all"] is None:
                log.warning(
                    "  seed=%s bras %s : cohorte NON MESURABLE (n_lived=%d n_founder=%d) -- la "
                    "paire sera EXCLUE, pas lue comme un zero", seed, key,
                    cell[f"{key}_n_lived"], cell[f"{key}_n_founder"])

    out = {"rows": rows, "config": {"target": target, "seeds": [int(s) for s in seeds], "k": int(k),
                                    "num_agents": num_agents, "max_ticks": max_ticks},
           "med_all": _pair_rows(rows, "med_all"), "med_founder": _pair_rows(rows, "med_founder"),
           "n_lived": _pair_rows(rows, "n_lived")}
    # L'aval ne peut pas ignorer une absence de mesure : elle est CRIEE, pas seulement ecrite dans
    # l'artefact. Sans ce cri, le seul signe d'un bras non mesure serait un `None` au milieu d'un
    # bloc de nombres -- et un lecteur presse le lit comme « pas de resultat pour ce champ ».
    for bloc in ("med_all", "med_founder", "n_lived"):
        statut = out[bloc].get("statut")
        if statut == "INDETERMINE_AUCUNE_PAIRE_MESURABLE":
            log.warning("ATTENTION -- %s : %s", bloc, out[bloc]["why"])
        elif statut == "MESURE_PARTIEL":
            log.warning("ATTENTION -- %s : %s", bloc, out[bloc]["why_non_mesurables"])
        # La MESURABILITE et la PUISSANCE sont deux axes : un bloc peut etre `MESURE` (rien
        # d'exclu) et rester incapable de trancher, et surtout un bloc `MESURE_PARTIEL` peut avoir
        # perdu assez de paires pour que son sign_p ne PUISSE plus valoir autre chose que 1.0. Ce
        # second cri est donc pose HORS du if/elif ci-dessus, et pas dedans.
        if out[bloc].get("why_puissance"):
            log.warning("ATTENTION -- %s SOUS-PUISSANT : %s", bloc, out[bloc]["why_puissance"])
        elif out[bloc].get("why_resolution"):
            log.warning("ATTENTION -- %s sans RESOLUTION : %s", bloc, out[bloc]["why_resolution"])
    if out_path:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2)
        log.info("artefact persiste -> %s", out_path)
    return out

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
