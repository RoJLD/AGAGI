"""Harnais Ratio de Transfert (Dev #3, mesure). Le curriculum développemental transfère-t-il mieux
que tabula-rasa ? Expérience appariée multi-seed à BUDGET COMPUTE ÉGAL, verdict + provenance ledger.
Spec : docs/superpowers/specs/2026-06-23-Curriculum-Transfer-design.md"""
import os
import sys
import math
import logging
import statistics
from typing import List, Dict, Optional, Callable, Tuple

# Lançable directement (`python tools/curriculum_transfer.py`) : met la racine projet sur le path
# (sinon sys.path[0]=tools/ et `src` est introuvable). No-op quand importé (racine déjà sur le path).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.curriculum.runner import CurriculumRunner, WorldStage, GraduationConfig
from src.curriculum.competence import survival_competence, competence_for
from src.environments.config import WorldConfig
from src.seed_ai.harness import SeedManager, Harness
from src.graph_rag.async_logger import logger as async_logger
from main_curriculum import make_run_era_fn, _acquire_shared_db, DEFAULT_LADDER

# Économie d'énergie (EDR 085) : sweet spot = survie ×4, gradient champion/frais ~5×. SANS ça,
# survie au plancher létal (~50 ticks) -> métrique survie aussi au plancher. Défaut = sweet spot.
SWEET_METAB = 0.25
SWEET_PAYOFF = 3.0

log = logging.getLogger("AGIseed.CurriculumTransfer")


def _sign_test_p(k: int, n: int) -> float:
    """p-value binomiale exacte BILATÉRALE sous H0 p=0.5 (test de signe). Sans dépendance (math.comb)."""
    if n <= 0:
        return 1.0
    k_hi = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(k_hi, n + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


INDETERMINE = "INDETERMINE"          # verdict NOMME : « aucune mesure interpretable », pas « pas d'effet »
METRIQUES = ("survival", "world")    # vocabulaire FERME de `metric` (cf. garde d'arguments)


def compute_transfer_verdict(ratios: List[float], neutral_band: float = 0.05,
                             n_indetermine: int = 0) -> Dict:
    """ratio par seed -> {n, median_ratio, n_favorable, sign_p, n_indetermine, verdict}. PUR.

    `n_indetermine` (2026-09-08) : nombre de seeds dont le ratio N'EST PAS DEFINI (bras tabula
    éteint, compétence non finie). Ils comptent dans `n` mais AUCUN nombre ne peut les remplacer :
    dès qu'il y en a un, le verdict est INDETERMINE. Un ratio non fini qui arriverait quand même ici
    est traité pareil et n'est plus AVALÉ par la branche `else` — `nan > 1.0` et `nan < 1.0` sont
    tous deux faux, donc un `nan` sortait en « NEUTRE » (= « pas d'effet ») avec `median_ratio=nan`
    publié à côté. C'est la forme (b) du catalogue : l'instrument SAIT que la mesure est cassée et
    affirme quand même quelque chose.

    ⚠️ La cohorte VIDE reste 'NEUTRE' — c'est un DÉFAUT connu, laissé OUVERT à dessein : il est le
    sujet d'un xfail strict d'un AUTRE fichier (tests/sandbox/test_inj_run_direction.py:325, défaut
    de `tools/cross_world_transfer.py`). Le corriger ici fermerait cette dette-là à son insu et
    rendrait ce xfail rouge. `run_transfer_experiment` ne peut plus l'atteindre (sa garde refuse la
    cohorte vide et `n >= 1` par construction).
    """
    n_indetermine = int(n_indetermine)
    # Un COMPTE d'indeterminations negatif n'est pas une mesure, c'est un appel invalide -- et il
    # FABRIQUE un verdict : `compute_transfer_verdict([1.5]*8, n_indetermine=-4)` publiait
    # 'TRANSFERE' avec n=4 alors que HUIT ratios avaient ete lus (le `n` publie ne decrit plus la
    # cohorte, et la majorite `2*n_fav > n` devient trivialement vraie). Refus en tete.
    if n_indetermine < 0:
        raise ValueError(
            f"compute_transfer_verdict : n_indetermine={n_indetermine} negatif -- un compte de "
            "mesures MANQUANTES ne peut pas etre negatif ; le `n` publie ne decrirait plus la "
            "cohorte et la condition de majorite deviendrait trivialement vraie.")
    n = len(ratios) + n_indetermine
    if n == 0:
        return {"n": 0, "median_ratio": 0.0, "n_favorable": 0, "sign_p": 1.0,
                "n_indetermine": 0, "verdict": "NEUTRE"}
    finis = [float(r) for r in ratios if math.isfinite(r)]
    n_indetermine += len(ratios) - len(finis)
    med = float(statistics.median(finis)) if finis else float("nan")
    n_fav = sum(1 for r in finis if r > 1.0)
    effective = [r for r in finis if r != 1.0]
    sign_p = _sign_test_p(sum(1 for r in effective if r > 1.0), len(effective))
    # ⚠️ E14 (2026-09-01) — `sign_p` etait CALCULE puis JETE : le verdict ne le lisait pas. La garde
    # de puissance avait ete cablee dans `compute_ab_verdict` et JAMAIS retro-appliquee a ses trois
    # homologues. C'est la definition meme de la classe E14 (garde jamais retro-appliquee).
    if n_indetermine:
        verdict = INDETERMINE
    elif med > 1.0 + neutral_band and 2 * n_fav > n and sign_p < 0.05:
        verdict = "TRANSFERE"
    elif med < 1.0 - neutral_band and 2 * n_fav < n and sign_p < 0.05:
        verdict = "NUIT"
    else:
        verdict = "NEUTRE"
    return {"n": n, "median_ratio": med, "n_favorable": n_fav, "sign_p": sign_p,
            "n_indetermine": n_indetermine, "verdict": verdict}


def _ratio_apparie(c_curr: float, c_tabula: float) -> Tuple[Optional[float], Optional[str]]:
    """Ratio apparié d'UN seed -> (ratio, motif_d_indetermination). Rend `(None, motif)` quand le
    rapport n'est PAS défini — jamais un nombre fabriqué.

    Remplace `c_curr / max(c_tabula, 1e-6)`, qui traitait l'EXTINCTION comme une mesure et
    produisait, dans les deux sens, un verdict de fond à partir d'une absence de donnée :
      * bras tabula éteint ET bras curriculum éteint (0/0) -> ratio 0.0 -> médiane 0.0, sign_p 0.031
        sur 6 seeds -> 'NUIT' : le curriculum déclaré NUISIBLE par une mesure NULLE ;
      * bras tabula éteint SEUL (0.5/0) -> 500000 -> 'TRANSFERE' : le verdict ne naît pas d'un
        transfert mais d'une division par le plancher epsilon.
    Le plancher n'a plus lieu d'être : `c_tabula > 0` est la condition d'existence du rapport, et
    `survival_competence` ne peut rendre un positif arbitrairement petit (médiane d'âge ENTIÈRE
    divisée par AGE_REF), donc le ratio défini reste borné.
    """
    if not math.isfinite(c_curr) or not math.isfinite(c_tabula):
        return None, "competence_non_finie"
    if c_tabula <= 0.0:
        return None, "bras_tabula_eteint"
    return c_curr / c_tabula, None


def _competence_on_target(transcript, target: str) -> float:
    """Compétence finale SUR LA CIBLE. On LIT le monde de la ligne au lieu de prendre `[-1]` en
    aveugle : sinon un bras qui ne se termine pas sur la cible rend la compétence du DERNIER barreau
    parcouru, et le « ratio de transfert » divise la compétence sur le monde A par celle sur B.
    Invariant structurel (la garde d'arguments impose `target == ladder[-1]`) -> une violation est un
    BUG, pas une mesure : on lève. Un transcript vide levait autrefois 0.0 — un zéro fabriqué."""
    if not transcript:
        raise ValueError(
            "transcript de bras VIDE : aucune ere n'a tourne -- aucune competence a lire ; "
            "ne pas confondre avec une competence nulle OBSERVEE.")
    for row in reversed(transcript):
        if row.get("world") == target:
            # ⚠️ DEUXIEME garde, INDEPENDANTE de celle du budget d'eres posee en tete de
            # `run_transfer_experiment` (2026-09-08, refutateur). `CurriculumRunner.run`
            # (src/curriculum/runner.py:154) ecrit `final_competence = history[-1] if history else
            # 0.0` : un barreau qui n'a tenu AUCUNE ere publie donc un ZERO FABRIQUE, indiscernable
            # d'une extinction MESUREE. Un barreau qui declare `eras <= 0` n'a rien mesure : on
            # leve, on ne lit pas le zero. Le `.get` avec defaut 1 vaut pour les transcripts qui ne
            # portent pas la cle (appelants hors `CurriculumRunner`) : on ne fabrique pas un refus
            # depuis une cle ABSENTE, on se borne a ce qui est DECLARE.
            if int(row.get("eras", 1)) <= 0:
                raise ValueError(
                    f"le barreau {target!r} declare eras={row.get('eras')!r} : AUCUNE ere n'y a "
                    "tourne, donc `final_competence` est le zero de repli du runner et non une "
                    "competence OBSERVEE -- ne pas confondre avec une extinction mesuree.")
            return float(row["final_competence"])
    raise ValueError(
        f"le bras ne s'est jamais arrete sur la cible {target!r} (mondes parcourus : "
        f"{[r.get('world') for r in transcript]}) -- un ratio calcule ici comparerait DEUX MONDES.")


def run_transfer_experiment(seeds, ladder: Optional[List[str]] = None, target: Optional[str] = None,
                            num_agents: int = 40, max_ticks: int = 300,
                            grad_cfg: Optional[GraduationConfig] = None,
                            run_era_fn: Optional[Callable] = None, manage_logger: bool = True,
                            metric: str = "survival", base_metabolism: float = SWEET_METAB,
                            forage_payoff: float = SWEET_PAYOFF) -> Dict:
    """Deux bras par seed (curriculum vs cible seule à BUDGET ÉGAL), apparié, -> verdict.
    run_era_fn injecté -> orchestration testable sans biosphère (sinon construit via make_run_era_fn).
    metric='survival' (défaut) : compétence = survie (gradient réel au sweet spot, EDR 085) ; le
    signal d'autel/outil étant nul tant que le goulot d'exploration (EDR 014) tient. metric='world' :
    métrique par-monde historique (restera au plancher jusqu'à ce que les autels émergent)."""
    # GARDE D'ARGUMENTS, EN TETE (2026-09-06 ; elargie le 2026-09-08). Orchestrateur : il n'entraine
    # pas lui-meme mais AGREGE en verdict -- une cohorte/liste de seeds vide produit une agregation
    # VIDE que l'aval lit comme une mesure (biais negatif systematique). Refus instantane, avant tout
    # appel de run.
    # ⚠️ `seeds` est MATERIALISE ici, UNE seule fois, et c'est CETTE liste qui est ensuite mesuree.
    # La version precedente faisait `list(seeds)` DANS la garde et JETAIT le resultat : un iterateur
    # etait donc consomme par sa propre garde, la boucle `for seed in seeds` ne voyait plus rien, et
    # n=0 / per_seed=[] / config.seeds=[] sortaient en verdict 'NEUTRE' -- une affirmation de fond
    # produite par ZERO mesure, exactement ce que la garde etait censee interdire.
    # ⚠️ TROISIEME AXE DU BUDGET, ajoute le 2026-09-08 par le refutateur. La garde couvrait la
    # cohorte (n_seeds), la population (num_agents) et l'horizon (max_ticks) -- pas le BUDGET
    # D'ERES, alors qu'il entre en prod par la MEME porte que CT_LADDER/CT_TARGET : `main()` lit
    # `CT_MAX_ERAS`. Avec max_eras <= 0, `CurriculumRunner.run` ne tourne AUCUNE ere et publie
    # `final_competence = 0.0` (son zero de repli, src/curriculum/runner.py:154) sur chaque barreau
    # du bras curriculum -- pendant que le bras tabula, lui, est protege par `max(1, total_eras)` et
    # mesure VRAIMENT. L'asymetrie transforme l'absence de mesure en affirmation NEGATIVE de fond :
    # mesure a dose connue (bras curriculum reellement MEILLEUR, 0.8 vs 0.4, 6 seeds) ->
    #   max_eras=1  -> TRANSFERE median=2.0 sign_p=0.031   (la bonne reponse)
    #   max_eras=0  -> NUIT      median=0.0 sign_p=0.031   (le curriculum declare NUISIBLE)
    # C'est la direction constante du biais du depot, et elle survivait au correctif du matin.
    seeds = [int(s) for s in seeds]
    grad_cfg = grad_cfg or GraduationConfig(max_eras=12)
    max_eras = int(grad_cfg.max_eras)
    if not seeds or int(num_agents) <= 0 or int(max_ticks) <= 0 or max_eras <= 0:
        raise ValueError(
            f"run_transfer_experiment : argument degenere (n_seeds={len(seeds)} num_agents={num_agents} max_ticks={max_ticks} max_eras={max_eras}) -- aucune mesure possible ; "
            "ne pas confondre avec une mesure nulle OBSERVEE.")
    # PSEUDO-REPLICATION. L'unite de replication du depot est le seed, et les DEUX bras sont
    # deterministes a seed fixe (`SeedManager(seed).seed_boundary(0)`) : repeter un seed ne cree
    # aucun replicat, mais gonflait `n` et faisait passer `sign_p` sous 0.05 depuis UN seul
    # replicat (6x le meme seed -> n=6, sign_p=0.03125 -> 'TRANSFERE'). On de-duplique en gardant
    # l'ordre, et c'est la liste DE-DUPLIQUEE qui est mesuree ET publiee dans `config.seeds`.
    uniques = list(dict.fromkeys(seeds))
    if len(uniques) != len(seeds):
        log.warning("run_transfer_experiment : %d seed(s) REPETE(S) ignore(s) -- n=%d replicat(s) "
                    "independant(s) ; repeter un seed n'en cree pas.",
                    len(seeds) - len(uniques), len(uniques))
        seeds = uniques
    # VOCABULAIRE FERME. `metric` n'etait compare qu'a 'survival' : toute autre valeur (une faute de
    # frappe comprise) retombait EN SILENCE sur la metrique par-monde, tandis que le ledger de
    # provenance republiait la valeur DEMANDEE -- la grandeur publiee n'etait pas celle qui a agi.
    if metric not in METRIQUES:
        raise ValueError(
            f"run_transfer_experiment : metric={metric!r} inconnue (attendu {list(METRIQUES)}) -- "
            "une valeur hors vocabulaire retombait en silence sur la metrique par-monde alors que "
            "le ledger republiait la valeur demandee.")
    ladder = list(ladder) if ladder else list(DEFAULT_LADDER)
    if not ladder:
        raise ValueError("run_transfer_experiment : echelle VIDE -- aucun monde a parcourir.")
    target = target or ladder[-1]
    # CIBLE vs ECHELLE. `target` n'etait jamais confronte a `ladder` : quand la cible n'est pas le
    # DERNIER barreau, le bras curriculum ne s'y arrete jamais et `_competence_on_target` rendait la
    # competence du dernier barreau parcouru -> le « ratio de transfert » divisait la competence sur
    # le monde A par celle sur le monde B (mesure : ladder=[a,b], target=gym -> 0.9/0.3 = 3.0
    # publie). Atteignable en prod par CT_LADDER / CT_TARGET. Deux lectures legitimes existent
    # (prolonger l'echelle jusqu'a la cible / evaluer la cible en zero-shot) et le code n'en
    # implemente aucune : on fait DECLARER l'appelant plutot que de deviner.
    if target != ladder[-1]:
        raise ValueError(
            f"run_transfer_experiment : cible {target!r} != dernier barreau {ladder[-1]!r} de "
            f"l'echelle {ladder} -- le bras curriculum ne se terminerait PAS sur la cible et le "
            "ratio publie comparerait DEUX MONDES DIFFERENTS. Declarer l'echelle qui MENE a la "
            f"cible (ladder=[..., {target!r}]).")
    competence_fn = survival_competence if metric == "survival" else None

    owns_engine = run_era_fn is None
    if owns_engine and manage_logger:
        async_logger.start()
    try:
        if owns_engine:
            shared_db = _acquire_shared_db()
            # Le retour de `_acquire_shared_db` n'etait PAS teste, alors que `run_curriculum` traite
            # le meme None comme FATAL (main_curriculum.py:181-185). Avec shared_db=None,
            # `init_primordial_soup` saute l'import du champion (main_biosphere.py:40,
            # `if import_agent_id and shared_db`) : le canal de PROMOTION -- l'objet meme de
            # l'experience -- est mort, les deux bras deviennent structurellement identiques, et le
            # « pas de transfert » publie ne mesure que l'absence de base.
            if shared_db is None:
                raise RuntimeError(
                    "run_transfer_experiment : KuzuDB indisponible (_acquire_shared_db a expire) -- "
                    "sans base, le canal de PROMOTION du champion est mort et les deux bras "
                    "deviennent identiques ; le verdict ne mesurerait que l'absence de base.")
            cfg = WorldConfig()
            cfg.base_metabolism = base_metabolism      # sweet spot énergie (EDR 085) -> survie ×4
            cfg.forage_payoff = forage_payoff
            # deterministic=True : memory_retriever neutralise avant la boucle -> bras appaires
            # exactement reproductibles (verrou repro Dev #3 ; sans ca, mesure non publiable).
            run_era_fn = make_run_era_fn(shared_db, cfg, num_agents=num_agents, max_ticks=max_ticks,
                                         deterministic=True, competence_fn=competence_fn)

        per_seed = []
        for seed in seeds:
            SeedManager(seed).seed_boundary(0)                              # bras curriculum
            tc = CurriculumRunner([WorldStage(w) for w in ladder], run_era_fn, grad_cfg).run()
            c_curr = _competence_on_target(tc, target)
            total_eras = sum(int(row["eras"]) for row in tc)

            SeedManager(seed).seed_boundary(0)                              # bras tabula-rasa (même seed)
            no_grad = GraduationConfig(window=grad_cfg.window, eps_plateau=grad_cfg.eps_plateau,
                                       c_floor=1.1, patience=grad_cfg.patience,
                                       max_eras=max(1, total_eras))         # ne diplôme jamais -> T ères
            tt = CurriculumRunner([WorldStage(target)], run_era_fn, no_grad).run()
            c_tabula = _competence_on_target(tt, target)

            ratio, motif = _ratio_apparie(c_curr, c_tabula)
            per_seed.append({"seed": int(seed), "C_curr": c_curr, "C_tabula": c_tabula,
                             "total_eras": total_eras, "ratio": ratio,
                             "ratio_indetermine": motif})
            if motif is None:
                log.info("seed=%s C_curr=%.3f C_tabula=%.3f T=%d ratio=%.3f",
                         seed, c_curr, c_tabula, total_eras, ratio)
            else:
                log.warning("seed=%s C_curr=%.3f C_tabula=%.3f T=%d ratio=INDETERMINE (%s)",
                            seed, c_curr, c_tabula, total_eras, motif)

        definis = [p["ratio"] for p in per_seed if p["ratio"] is not None]
        verdict = compute_transfer_verdict(definis, n_indetermine=len(per_seed) - len(definis))
        return {**verdict, "per_seed": per_seed,
                "config": {"ladder": ladder, "target": target, "seeds": [int(s) for s in seeds],
                           "num_agents": num_agents, "max_ticks": max_ticks, "max_eras": grad_cfg.max_eras,
                           "metric": metric, "base_metabolism": base_metabolism,
                           "forage_payoff": forage_payoff}}
    finally:
        if owns_engine and manage_logger:
            async_logger.stop()


def main():
    seeds = [int(s) for s in os.environ.get("CT_SEEDS", "0,1,2,3,4").split(",") if s.strip()]
    ladder = [w for w in os.environ.get("CT_LADDER", ",".join(DEFAULT_LADDER)).split(",") if w.strip()]
    target = os.environ.get("CT_TARGET") or (ladder[-1] if ladder else None)
    num_agents = int(os.environ.get("CT_NUM_AGENTS", "40"))
    max_ticks = int(os.environ.get("CT_MAX_TICKS", "300"))
    grad_cfg = GraduationConfig(max_eras=int(os.environ.get("CT_MAX_ERAS", "12")))
    metric = os.environ.get("CT_METRIC", "survival")
    base_metabolism = float(os.environ.get("CT_METAB", str(SWEET_METAB)))
    forage_payoff = float(os.environ.get("CT_PAYOFF", str(SWEET_PAYOFF)))

    result = run_transfer_experiment(seeds, ladder=ladder, target=target,
                                     num_agents=num_agents, max_ticks=max_ticks, grad_cfg=grad_cfg,
                                     metric=metric, base_metabolism=base_metabolism,
                                     forage_payoff=forage_payoff)

    meta_seed = min(seeds) if seeds else 0
    h = Harness(seed=meta_seed, name="curriculum_transfer", with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    # ⚠️ LA LIGNE PUBLIEE DOIT DECRIRE CE QU'ELLE COMPTE (2026-09-08, refutateur). Le format
    # d'origine imprimait `n_fav=%d/%d` avec `result["n"]` au denominateur -- or `n` compte AUSSI
    # les seeds dont le ratio n'existe pas. Sur 11 seeds unanimes + 1 indetermine, la ligne disait
    # « INDETERMINE median_ratio=2.000 (n_fav=11/12, sign_p=0.001) » : le 11/12 se relit « un seed a
    # DEFAVORISE le curriculum » alors qu'aucune comparaison n'y a eu lieu, et le sign_p affiche est
    # celui des 11 SEULS seeds mesures. C'est le defaut que l'instrument frere a ferme le meme jour
    # (`_absent` de tools/cross_world_transfer.py:330 : « n_favorable = 0 sur un INDETERMINE se
    # relisait comme une mesure »). Le dict publie, lui, porte `n_indetermine` : il est
    # auto-descriptif ; c'est la ligne imprimee qui masquait la distinction.
    n_ind = int(result.get("n_indetermine", 0))
    n_mesures = int(result["n"]) - n_ind
    suffixe = ""
    if n_ind:
        suffixe = (f" | {n_ind}/{result['n']} seed(s) INDETERMINE(S) -- median_ratio, n_fav et "
                   f"sign_p ci-dessus portent sur les {n_mesures} seed(s) MESURE(S), pas sur la "
                   "cohorte ; ce n'est PAS un effet nul observe")
    log.info("VERDICT=%s median_ratio=%.3f (n_fav=%d/%d mesures, sign_p=%.3f)%s -> %s",
             result["verdict"], result["median_ratio"], result["n_favorable"], n_mesures,
             result["sign_p"], suffixe, path)
    return path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
