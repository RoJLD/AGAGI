"""Sonde de Dreaming (barreau 0, attaque du goulot d'exploration EDR 014, approche A).
L'organe MCTS (+0.5 drain) est-il (Q1) survivable au sweet spot vs létal, et (Q2) payant quand
présent ? Spec : docs/superpowers/specs/2026-06-23-Dreaming-Organ-Revival-design.md.
Diagnostic SEUL : observe, ne répare pas le moteur."""
import os
import sys
import math
import logging
import statistics
from typing import List, Dict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.curriculum.competence import survival_competence
import numpy as np
from src.environments.config import WorldConfig
from src.seed_ai.harness import SeedManager, Harness
from src.graph_rag.async_logger import logger as async_logger
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from main_curriculum import _prepare_world, _acquire_shared_db

log = logging.getLogger("AGIseed.DreamingProbe")


def _has_organ(agent: Dict) -> bool:
    """True si l'agent porte l'organe MCTS (organ_genes[0]). Robuste aux champs manquants."""
    model = agent.get("model")
    genome = getattr(model, "genome", None)
    og = getattr(genome, "organ_genes", None)
    return bool(og is not None and len(og) > 0 and og[0])


def organ_prevalence(agents: List[Dict]) -> float:
    """Fraction des agents portant l'organe MCTS.

    Cohorte VIDE -> **nan** (INDETERMINE explicite), JAMAIS 0.0 -- REFUTATION 2026-09-08. C'est le
    JUMEAU PUBLIC de `_prevalence_from_stats` : le correctif du 2026-09-08 avait redresse la version
    PRIVEE et laisse celle-ci sur la convention 0.0, alors qu'elle porte le meme piege a l'identique
    (`organ_prevalence(env.agents)` apres extinction rend « organe integralement purge » sans qu'un
    seul agent ait ete mesure). Pire : la convention fautive etait GELEE par un test vert
    (`test_organ_prevalence_known_fractions`), l'etat le plus dangereux pour un defaut.
    ⚠️ Une cohorte NON VIDE sans aucun porteur rend toujours 0.0 : c'est une purge OBSERVEE, une
    mesure reelle, et elle doit continuer a passer (sans quoi le correctif serait un baillon, E1).
    """
    if not agents:
        return float("nan")
    return sum(1 for a in agents if _has_organ(a)) / len(agents)


def q2_split(stats: List[Dict]) -> Dict:
    """Sépare les agents par rêve (total_dreams>0) et compare leur compétence-survie.

    ⚠️ **GROUPE VIDE -> `nan` (INDETERMINE explicite), JAMAIS 0.0** — correctif 2026-09-08,
    défaut exposé par `tests/sandbox/test_inj_run_q2.py` (injection à dose connue). `run_q2`
    lance le bras ON à `organ_fraction=1.0` : quand TOUS les agents rêvent, `nondreamers` est
    vide et `survival_competence([])` valait 0.0 par convention (`_median_norm` :
    `if not values: return 0.0`). `delta` cessait alors d'être un CONTRASTE pour devenir la
    compétence ABSOLUE des rêveurs — un artefact PROPORTIONNEL à la survie, donc d'autant plus
    grand que le monde va bien. Mesuré : deux bras STRICTEMENT identiques (effet réel de
    l'organe = zéro, ratio apparié 1.0) sortaient `q2a_delta = 0.5` à l'âge 100 (25× le seuil
    `pay_eps=0.02`) et `dreaming_verdict` prononçait SURVIT_ET_PAYE. Forme (a) du biais
    systématique du dépôt : entrée vide -> affirmation de FOND, ici POSITIVE.

    ⚠️ Un groupe NON VIDE dont tous les agents meurent à la naissance rend toujours 0.0 : c'est
    une survie OBSERVÉE de zéro, une mesure réelle, et elle doit continuer à passer (sans quoi
    le correctif serait un bâillon — classe E1).

    Le seuil du split reste `total_dreams > 0`, STRICTEMENT. La partition est écrite `> 0` /
    `<= 0` (et non `> 0` / `== 0`) pour qu'aucun agent ne puisse tomber HORS des deux groupes :
    une valeur négative — impossible sur un compteur, mais rien ne l'interdisait — disparaissait
    silencieusement des DEUX médianes (forme (c) du biais : troncature muette)."""
    dreamers = [s for s in stats if s.get("total_dreams", 0) > 0]
    nondreamers = [s for s in stats if s.get("total_dreams", 0) <= 0]
    c_d = survival_competence(dreamers) if dreamers else float("nan")
    c_n = survival_competence(nondreamers) if nondreamers else float("nan")
    return {"dreamers_competence": c_d, "nondreamers_competence": c_n,
            "delta": c_d - c_n, "n_dreamers": len(dreamers), "n_nondreamers": len(nondreamers)}


def dreaming_verdict(delta_prev_sweet: float, delta_prev_lethal: float,
                     q2a_delta: float, q2b_ratio: float,
                     surv_eps: float = 0.05, pay_eps: float = 0.02) -> str:
    """Gate 4-cas. SURVIT = organe toléré au sweet spot (Δprev > -eps) ET moins purgé qu'au létal
    (pression nette > 0). PAYE = bénéfice intra-pop (q2a_delta > pay_eps) OU population on>off
    (q2b_ratio > 1+pay_eps).

    ⚠️ **CÔTÉ PAYE : un `nan` N'EST PLUS AVALÉ** (2026-09-08). Toute comparaison à `nan` vaut
    False : un `q2a_delta` / `q2b_ratio` INDETERMINE (groupe de référence vide, dénominateur
    éteint, aucune cellule informative — cf. `q2_split` et `run_q2`) faisait donc `pays=False`
    et la porte prononçait « PAS PAYE », c.-à-d. l'affirmation de FOND « le rêve ne paye pas »
    sur ZÉRO observation. Rendre `nan` depuis `run_q2` sans toucher la porte aurait DÉPLACÉ le
    défaut d'un cran au lieu de le corriger. La porte nomme désormais l'indécidable :
    `SURVIT_PAYE_INDETERMINE` / `PAS_SURVIT_PAYE_INDETERMINE`.

    ⚠️ Deux garde-fous appariés (classe E1), tous deux figés par des tests :
    * un `nan` du côté PAYE n'empêche PAS de conclure quand l'AUTRE moitié du `or` tranche
      POSITIVEMENT (`q2b_ratio=2.0` avec `q2a_delta=nan` reste PAYE : la mesure existante suffit) ;
    * le côté SURVIT n'est PAS touché. `dreaming_verdict(nan, nan, 0.0, 1.0)` rend toujours MORT
      — c'est précisément POURQUOI `run_q1` doit REFUSER une cohorte vide plutôt que propager
      (cf. `test_run_q1_never_lets_a_nan_reach_the_gate`), et affaiblir ça ici retirerait sa
      raison d'être à ce refus."""
    survives = (delta_prev_sweet > -surv_eps) and ((delta_prev_sweet - delta_prev_lethal) > 0)
    pays = (q2a_delta > pay_eps) or (q2b_ratio > 1.0 + pay_eps)
    if not pays and (math.isnan(q2a_delta) or math.isnan(q2b_ratio)):
        return "SURVIT_PAYE_INDETERMINE" if survives else "PAS_SURVIT_PAYE_INDETERMINE"
    if survives and pays:
        return "SURVIT_ET_PAYE"
    if survives and not pays:
        return "SURVIT_PAS_PAYE"
    if (not survives) and pays:
        return "PAYE_PAS_SURVIT"
    return "MORT"


def _set_organ(genome, on: bool) -> None:
    """Force organ_genes[0] (MCTS) sur un génome LOCAL. Préserve les autres organes."""
    og = np.array(genome.organ_genes, dtype=bool) if getattr(genome, "organ_genes", None) is not None \
        else np.array([False, False], dtype=bool)
    og[0] = bool(on)
    genome.organ_genes = og


def run_era_organ(target: str, seed: int, organ_fraction: float, metab: float, payoff: float,
                  num_agents: int, max_ticks: int, shared_db) -> List[Dict]:
    """UNE ère sur `target`, avec une fraction `organ_fraction` de la population portant l'organe
    MCTS (les `int(round(organ_fraction*len(genomes)))` premiers). Renvoie par agent (TOUS :
    vivants + morts, cf. EDR 092 — la population s'éteint à 100 %) : {age, total_dreams, has_organ}.
    Déterministe (memory_retriever neutralisé)."""
    # GARDE D'ARGUMENTS, EN TETE (2026-09-06, famille run_* -- 7e elargissement du cliquet). Un
    # argument degenere est une erreur d'APPEL, pas un fait sur le monde : sans elle, une cohorte
    # vide / un horizon nul rend 0.0 ou nan comme une MESURE que l'aval lit comme un resultat
    # (biais negatif systematique du depot). Posee AVANT toute construction -> refus < 0.5 s.
    if int(num_agents) <= 0 or int(max_ticks) <= 0 or not (0.0 <= float(organ_fraction) <= 1.0):
        raise ValueError(
            f"run_era_organ : argument degenere (num_agents={num_agents} max_ticks={max_ticks} organ_fraction={organ_fraction}) -- aucune mesure possible ; "
            "ne pas confondre avec une mesure nulle OBSERVEE.")
    SeedManager(seed).seed_boundary(0)
    config = WorldConfig()
    config.base_metabolism = metab
    config.forage_payoff = payoff
    env = _prepare_world(target, config, deterministic=True)

    genomes, _ntm = init_primordial_soup(num_agents=num_agents, import_agent_id=None,
                                         keep_memory=False, shared_db=shared_db, config=config)
    n_on = int(round(organ_fraction * len(genomes)))
    for i, g in enumerate(genomes):
        a = MambaAgent()
        a.from_genome(g)
        _set_organ(a.genome, i < n_on)  # FIX B (EDR 092) : semer sur le génome PROPRE de l'agent
        env.add_agent(a, energy=50.0)   # (after_genome deepcopy) -> évite l'aliasing d'init_primordial_soup
        # Marque la COHORTE FONDATRICE (P2.12). Nécessaire parce que le rêve forcé déclenche une
        # explosion reproductive (n_lived ×20 mesuré) : une médiane d'âge sur TOUS les agents compare
        # alors deux populations de tailles incomparables, dont la plupart des membres sont nés tard et
        # ont donc un âge mécaniquement faible. Sélectionner les « N plus vieux » ne corrige RIEN — c'est
        # une sélection sur la variable de sortie, à des quantiles différents (top 26 % vs top 1.6 %).
        # Seule l'identité permet un appariement honnête.
        env.agents[-1]["_founder"] = True

    env.current_era = 1
    t = 0
    while len(env.agents) > 0 and t < max_ticks:
        env.step()
        t += 1

    # FIX A (EDR 092) : la population s'éteint à 100 % (0 survivant) -> mesurer TOUS les agents
    # (vivants + morts). Le signal de sélection est la prévalence de l'organe parmi tous (reproduction
    # différentielle) + l'âge-à-la-mort ; PAS la prévalence des survivants (vide sous extinction).
    all_agents = list(env.agents) + list(getattr(env, "dead_agents", []))
    # `altars_solved` / `spears_crafted` = les métriques d'EXPLORATION d'EDR-014 (couche 2), exposées
    # ici pour tester directement la thèse dont EDR-095 rejetait le levier — un rejet lui-même réfuté
    # par EDR-DREAM-001. Elles étaient déjà portées par l'agent, jamais remontées par cette sonde.
    out = [{"age": a.get("age", 0), "total_dreams": a.get("total_dreams", 0),
            "has_organ": _has_organ(a), "founder": bool(a.get("_founder", False)),
            "altars_solved": int(a.get("altars_solved", 0) or 0),
            "spears_crafted": int(a.get("spears_crafted", 0) or 0),
            "preys_eaten": int(a.get("preys_eaten", 0) or 0)}
           for a in all_agents]
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    return out


from tools.curriculum_transfer import _sign_test_p

RATIO_CAP = 5.0
EPS_COMPETENCE = 1e-6   # plancher SOUS lequel une compétence-survie n'est plus un dénominateur


def _fondateurs(stats: List[Dict], seed, bras: str) -> List[Dict]:
    """Sous-cohorte FONDATRICE d'une ère (drapeau `founder`, posé à t=0 par `run_era_organ`).

    POURQUOI (2026-09-08, défaut #2 exposé par injection à dose connue) : `run_era_organ`
    MARQUE la cohorte fondatrice et la REMONTE depuis EDR-DREAM-001, précisément parce que le
    rêve forcé déclenche une explosion reproductive (n_lived ×13-20 MESURÉ) ; une médiane d'âge
    sur TOUS les agents compare alors deux populations de compositions incomparables, dont la
    plupart des membres sont nés tard et ont un âge MÉCANIQUEMENT faible. `run_q2` produisait ce
    drapeau et ne le lisait JAMAIS. Dose connue : à cohortes FONDATRICES strictement identiques
    (12 fondateurs d'âge 100 des deux côtés), le seul fait que le bras ON se reproduise faisait
    sortir `q2b_ratio` à **0.05** — « l'organe divise la survie par 20 » — alors qu'il n'avait
    changé la survie de personne. Le correctif était déjà écrit dans le fichier voisin
    (`tools/dream_causal_probe.py::run_founder_matched`, qui filtre sur `a.get('founder')`) et
    n'avait jamais été rétro-appliqué ici : classe E14.

    ⚠️ Restreindre aux « N plus vieux » NE CORRIGE RIEN — c'est une sélection sur la variable de
    SORTIE à des quantiles incomparables. Seule l'IDENTITÉ permet un appariement honnête.

    Cohorte sans AUCUN fondateur -> **LÈVE**, en nommant le seed et le bras. Ce n'est pas une
    survie nulle observée : `run_era_organ` marque tous les agents semés à t=0 et rend vivants
    + morts, donc une cohorte sans fondateur est une ère qui n'a rien produit du tout. Refuser
    au PREMIER seed fautif (et non après la boucle) évite de brûler les ères suivantes."""
    fond = [a for a in stats if a.get("founder")]
    if not fond:
        raise ValueError(
            f"run_q2 : l'ere {bras} du seed {seed} ne rend AUCUN agent fondateur (cohorte de "
            f"{len(stats)} agent(s)) -- la competence-survie appariee est INDETERMINEE, pas "
            "nulle. `run_era_organ` marque a t=0 TOUS les agents semes et remonte vivants + "
            "morts : une cohorte sans fondateur est une ere qui n'a rien produit, jamais une "
            "survie OBSERVEE de zero.")
    return fond


def _prevalence_from_stats(stats: List[Dict]) -> float:
    """Prévalence d'organe à partir des stats run_era_organ (clé has_organ).

    Cohorte VIDE -> **nan** (INDETERMINE explicite), JAMAIS 0.0. La convention 0.0 faisait lire
    à `run_q1` un delta de `0.0 - 0.5 = -0.5`, c.-à-d. l'affirmation MAXIMALE « l'organe a été
    INTÉGRALEMENT purgé », que `dreaming_verdict` transformait en MORT : une absence de mesure
    y devenait le négatif le plus fort que l'instrument sache prononcer (biais systématique du
    dépôt, forme (a) : entrée vide -> verdict de FOND).
    ⚠️ Une cohorte NON VIDE dont AUCUN agent ne porte l'organe rend toujours 0.0 : c'est une
    purge OBSERVÉE, une mesure réelle, et elle doit continuer à passer (sans quoi le correctif
    rendrait l'instrument incapable de rapporter une vraie purge -- classe E1).
    """
    if not stats:
        return float("nan")
    return sum(1 for s in stats if s["has_organ"]) / len(stats)


def run_q1(seeds, target, num_agents, max_ticks, shared_db) -> Dict:
    """Q1 : organe semé à 50%, prévalence de l'organe parmi TOUS les agents (reproduction
    différentielle = sélection) sweet vs létal -> pression énergétique nette sur l'organe (EDR 092)."""
    # GARDE D'ARGUMENTS, EN TETE (2026-09-06). Orchestrateur : il n'entraine pas lui-meme mais
    # AGREGE en verdict -- une cohorte/liste de seeds vide produit une agregation VIDE que l'aval
    # lit comme une mesure (biais negatif systematique). Refus instantane, avant tout appel de run.
    # MATERIALISATION AVANT LA GARDE (2026-09-08). `not list(seeds)` CONSOMMAIT l'iterable : avec un
    # generateur / map / zip -- forme naturelle pour des seeds calcules -- la garde passait puis la
    # boucle `for seed in seeds` ne tournait ZERO fois, `sweet`/`lethal` restaient vides et les
    # defauts `else 0.0` rendaient pressure=0.0 comme une MESURE (verdict MORT fabrique). Le `list()`
    # est donc DEVANT la garde, et la garde lit la liste MATERIALISEE -- pas une seconde consommation.
    seeds = list(seeds)
    if not seeds or int(num_agents) <= 0 or int(max_ticks) <= 0:
        raise ValueError(
            f"run_q1 : argument degenere (n_seeds={len(seeds)} num_agents={num_agents} max_ticks={max_ticks}) -- aucune mesure possible ; "
            "ne pas confondre avec une mesure nulle OBSERVEE.")
    sweet, lethal = [], []
    for seed in seeds:
        s = run_era_organ(target, seed, 0.5, 0.25, 3.0, num_agents, max_ticks, shared_db)
        l = run_era_organ(target, seed, 0.5, 1.0, 1.0, num_agents, max_ticks, shared_db)
        p_s, p_l = _prevalence_from_stats(s), _prevalence_from_stats(l)
        # REFUS EXPLICITE d'un INDETERMINE (cohorte vide), au plus tot -- des le seed fautif, pas
        # apres avoir brule les suivants. On ne PROPAGE pas le nan : `dreaming_verdict` compare avec
        # `>`, et toute comparaison a nan vaut False -> il prononcerait MORT. Rendre nan deplacerait
        # donc le defaut d'un cran au lieu de le corriger.
        for nom, p in (("sweet", p_s), ("letal", p_l)):
            if math.isnan(p):
                raise ValueError(
                    f"run_q1 : l'ere {nom} du seed {seed} rend une cohorte VIDE (aucun agent mesure) -- "
                    "la prevalence d'organe est INDETERMINEE, pas nulle. La convention 0.0 en faisait un "
                    "delta de -0.5, c.-a-d. « organe INTEGRALEMENT purge », et la porte prononcait MORT : "
                    "une absence de mesure n'est pas une purge OBSERVEE.")
        sweet.append(p_s - 0.5)
        lethal.append(p_l - 0.5)
    # Plus de defaut `else 0.0` : il ne peut plus etre atteint (seeds materialise et non vide), et
    # s'il l'etait, `statistics.median([])` leve StatisticsError (sous-classe de ValueError) -- un
    # refus, pas un zero de fond.
    dps = float(statistics.median(sweet))
    dpl = float(statistics.median(lethal))
    return {"delta_prev_sweet": dps, "delta_prev_lethal": dpl, "pressure": dps - dpl,
            "per_seed_sweet": sweet, "per_seed_lethal": lethal}


def run_q2(seeds, target, num_agents, max_ticks, shared_db) -> Dict:
    """Q2 : forcé-ON au sweet spot. (a) rêveurs vs non-rêveurs ; (b) apparié ON vs OFF (ratio survie)."""
    # GARDE D'ARGUMENTS, EN TETE (2026-09-06). Orchestrateur : il n'entraine pas lui-meme mais
    # AGREGE en verdict -- une cohorte/liste de seeds vide produit une agregation VIDE que l'aval
    # lit comme une mesure (biais negatif systematique). Refus instantane, avant tout appel de run.
    # MATERIALISATION AVANT LA GARDE (REFUTATION 2026-09-08). `run_q2` portait le defaut d'iterateur
    # que le correctif du meme jour avait redresse chez `run_q1`, MOT POUR MOT et dans le meme fichier :
    # `not list(seeds)` CONSOMME l'iterable, la garde passe, la boucle tourne ZERO fois, et les defauts
    # `else 0.0` / `else 1.0` publient `q2a_delta=0.0, q2b_ratio=1.0, sign_p=1.0, n=0` -- l'affirmation
    # de FOND « le reve NE PAYE PAS », que `dreaming_verdict` transforme en SURVIT_PAS_PAYE, sans
    # qu'une seule ere ait ete simulee. Mesure : `run_q2(iter([0,1,2]), ...)` -> 0 appel a run_era_organ.
    # SECOND defaut, dans le MESSAGE : `len(list(seeds))` etait une DEUXIEME consommation, donc sur un
    # iterateur NON vide refuse pour une autre raison (num_agents<=0) le refus annoncait `n_seeds=0`,
    # c.-a-d. accusait le mauvais argument. Mesure avant : « n_seeds=0 num_agents=0 » pour 3 seeds reels.
    seeds = list(seeds)
    if not seeds or int(num_agents) <= 0 or int(max_ticks) <= 0:
        raise ValueError(
            f"run_q2 : argument degenere (n_seeds={len(seeds)} num_agents={num_agents} max_ticks={max_ticks}) -- aucune mesure possible ; "
            "ne pas confondre avec une mesure nulle OBSERVEE.")
    deltas, ratios, dreams_seen = [], [], 0
    cellules, seeds_ecartes, seeds_sans_reference = [], [], []
    for seed in seeds:
        on = run_era_organ(target, seed, 1.0, 0.25, 3.0, num_agents, max_ticks, shared_db)
        off = run_era_organ(target, seed, 0.0, 0.25, 3.0, num_agents, max_ticks, shared_db)
        split = q2_split(on)
        deltas.append(split["delta"])
        if math.isnan(split["delta"]):
            seeds_sans_reference.append(seed)
        # `total_dreams_seen` est le CONTROLE POSITIF de la sonde (« le reve a-t-il seulement eu
        # lieu ? ») : il se compte sur TOUTE la population du bras ON, fondateurs ou non, et
        # seulement sur le bras ON (le bras OFF ne porte pas l'organe).
        dreams_seen += sum(s["total_dreams"] for s in on)
        # APPARIEMENT SUR LA COHORTE FONDATRICE (cf. `_fondateurs`) : la competence-survie est une
        # statistique de POPULATION, elle ne peut pas comparer deux bras dont l'un s'est reproduit
        # x20. Les competences « tous agents » restent PUBLIEES cellule par cellule -- elles sont la
        # base des chiffres deja graves (EDR-093 : q2b 1.087, q2a -0.040), qui ne seraient sinon
        # re-derivables d'aucun artefact.
        f_on, f_off = _fondateurs(on, seed, "ON"), _fondateurs(off, seed, "OFF")
        c_on, c_off = survival_competence(f_on), survival_competence(f_off)
        cellules.append({"seed": seed, "c_on_founder": c_on, "c_off_founder": c_off,
                         "n_founder_on": len(f_on), "n_founder_off": len(f_off),
                         "c_on_tous": survival_competence(on), "c_off_tous": survival_competence(off),
                         "n_tous_on": len(on), "n_tous_off": len(off),
                         "n_dreamers": split["n_dreamers"], "n_nondreamers": split["n_nondreamers"]})
        # DEGENERESCENCE : ECARTEE, PLUS AVALEE (2026-09-08, defauts #3 et #4).
        # AVANT : `if c_on <= 1e-6 and c_off <= 1e-6: ratio = 1.0` -- l'instrument RECONNAISSAIT le
        # cas « rien n'a survecu » et lui affectait EXACTEMENT la valeur qui signifie « aucun effet »
        # (forme (b) du biais du depot : il SAIT et ne le dit pas). La cellule sortait ensuite de
        # `effective` : le dict publie annoncait n=3, q2b_ratio=1.0, sign_p=1.0 -- indiscernable
        # d'une egalite reellement MESUREE, et la porte prononcait SURVIT_PAS_PAYE sur zero
        # observation. Et la garde etait posee sur un `and` : quand le SEUL denominateur etait
        # eteint, `max(c_off, 1e-6)` faisait exploser le ratio brut (5000 pour UN tick d'ecart entre
        # deux populations qui s'eteignent toutes les deux) avant ecretage a RATIO_CAP -> le ratio
        # MAXIMAL 5.0 et SURVIT_ET_PAYE.
        # APRES : la cellule est ECARTEE des que le DENOMINATEUR est eteint (`c_off <= eps`, ce qui
        # englobe le cas « les deux eteints »), et le compte est PUBLIE. Meme regle que
        # `run_founder_matched._pair` (`ratio None si med_off <= 0`) et que `_paired_ratios`.
        # ⚠️ La condition porte sur le SEUL denominateur, PAS sur les deux bras (classe E1) : un
        # bras ON eteint face a un OFF vivant reste une cellule INFORMATIVE (ratio 0.0), et
        # l'instrument doit rester capable de rapporter ce prejudice-la.
        if c_off <= EPS_COMPETENCE:
            seeds_ecartes.append(seed)
            continue
        ratios.append(min(c_on / c_off, RATIO_CAP))
    # Plus de defaut `else 0.0` / `else 1.0` : ils ne peuvent plus etre atteints (seeds materialise et
    # non vide -> au moins un append par bras), et s'ils l'etaient, `statistics.median([])` leve
    # StatisticsError (sous-classe de ValueError) -- un refus, pas un « ne paye pas » de fond. Les
    # laisser en place, c'est garder arme le pistolet que la materialisation vient de desamorcer.
    # Les medianes sont prises sur les cellules MESUREES seulement ; ZERO cellule mesuree ->
    # **nan** (INDETERMINE nomme), jamais la valeur « aucun effet ».
    mesures_a = [d for d in deltas if not math.isnan(d)]
    q2a_delta = float(statistics.median(mesures_a)) if mesures_a else float("nan")
    q2b_ratio = float(statistics.median(ratios)) if ratios else float("nan")
    effective = [r for r in ratios if r != 1.0]
    sign_p = _sign_test_p(sum(1 for r in effective if r > 1.0), len(effective))
    n_fav = sum(1 for r in ratios if r > 1.0)
    out = {"q2a_delta": q2a_delta, "q2b_ratio": q2b_ratio, "n_favorable": n_fav,
           "n": len(ratios), "sign_p": sign_p, "total_dreams_seen": dreams_seen,
           # `None` (et non `nan`) dans les listes publiees : JSON-serialisable, comme
           # `ratios_par_K` dans `dose_response_verdict`. Le scalaire, lui, reste `nan` --
           # c'est celui que la porte lit, et `math.isnan` est le test que fait la porte.
           "per_seed_delta": [None if math.isnan(d) else d for d in deltas],
           "per_seed_ratio": ratios,
           "n_seeds": len(seeds), "n_ecartees": len(seeds_ecartes),
           "seeds_ecartes": seeds_ecartes,
           "n_sans_reference": len(seeds_sans_reference),
           "seeds_sans_reference": seeds_sans_reference,
           # Le test de signe JETTE les ex aequo : le `n` publie N'EST PAS son denominateur.
           # Meme correctif que `dose_response_verdict` (d), jamais retro-applique ici (E14).
           "n_effectif": len(effective), "n_ex_aequo": len(ratios) - len(effective),
           "per_seed_cellules": cellules}
    if not ratios:
        out["why_q2b"] = (
            f"q2b_ratio INDETERMINE : les {len(seeds)} cellule(s) ont toutes un denominateur "
            f"eteint (competence-survie du bras OFF <= {EPS_COMPETENCE}) -- seeds {seeds_ecartes}. "
            "Aucune division n'a de sens ; ne pas lire 1.0 comme « l'organe n'a aucun effet », ni "
            "5.0 comme un benefice : rien n'a ete mesure.")
    if not mesures_a:
        out["why_q2a"] = (
            f"q2a_delta INDETERMINE : sur les {len(seeds)} cellule(s), le bras ON n'a JAMAIS eu "
            f"les DEUX groupes du split (reveurs / non-reveurs) -- seeds {seeds_sans_reference}. "
            "Sans groupe de reference, le contraste devient la competence ABSOLUE des reveurs ; "
            "ne pas le lire comme un benefice de l'organe.")
    return out


def main() -> Dict:
    os.environ["AGISEED_QUIET_LOG"] = "1"     # anti-segfault + vitesse (EDR 091), AVANT start()
    target = os.environ.get("DP_TARGET", "stoneage")
    seeds = [int(s) for s in os.environ.get("DP_SEEDS", "0,1,2").split(",") if s.strip()]
    num_agents = int(os.environ.get("DP_NUM_AGENTS", "40"))
    max_ticks = int(os.environ.get("DP_MAX_TICKS", "400"))
    mode = os.environ.get("DP_MODE", "both")

    async_logger.start()
    try:
        shared_db = _acquire_shared_db()
        q1 = run_q1(seeds, target, num_agents, max_ticks, shared_db) if mode in ("q1", "both") else {}
        q2 = run_q2(seeds, target, num_agents, max_ticks, shared_db) if mode in ("q2", "both") else {}
    finally:
        async_logger.stop()

    verdict = dreaming_verdict(q1.get("delta_prev_sweet", -1.0), q1.get("delta_prev_lethal", -1.0),
                               q2.get("q2a_delta", 0.0), q2.get("q2b_ratio", 1.0)) if mode == "both" \
        else "PARTIEL"
    result = {"verdict": verdict, "q1": q1, "q2": q2,
              "config": {"target": target, "seeds": seeds, "num_agents": num_agents,
                         "max_ticks": max_ticks, "mode": mode}}
    h = Harness(seed=min(seeds) if seeds else 0, name="dreaming_probe", with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    log.info("VERDICT=%s | Q1 pressure=%.3f (sweet=%.3f letal=%.3f) | Q2 q2a=%.3f q2b=%.3f dreams=%d -> %s",
             verdict, q1.get("pressure", 0.0), q1.get("delta_prev_sweet", 0.0),
             q1.get("delta_prev_lethal", 0.0), q2.get("q2a_delta", 0.0), q2.get("q2b_ratio", 1.0),
             q2.get("total_dreams_seen", 0), path)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
