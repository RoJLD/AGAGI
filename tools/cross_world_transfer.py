"""Transfert ZÉRO-SHOT cross-world (north-star G1). Un champion évolué dans le monde A, lâché TEL QUEL
(sans ré-évolution) dans le monde B jamais vu, survit-il mieux que tabula-rasa, à budget d'évaluation
égal ? KPI `transfer_ratio` = survie(champ A dans B) / survie(tabula dans B), appariée par seed d'éval,
test de signe. Distinct d'EDR-116 (transfert DÉVELOPPEMENTAL à compute égal : ré-évolution sur la cible).

Spec du KPI : SDR-G1. Réutilise la primitive de mesure cohorte-fixe (s2_demand.run_condition) mais au
SWEET-SPOT métabolique (EDR 085) — sans lui, la survie est au plancher létal, insensible au monde ET au
génome, et tout ratio vaut ~1 par artefact (le monde ne pèse plus sur la survie)."""
import os
import sys
import json
import statistics
from typing import List, Dict, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.agents.mamba_agent import MambaAgent
from src.environments.config import WorldConfig
from src.seed_ai.harness import seed_at
import src.seed_ai.persistence as persistence
from tools.curriculum_transfer import compute_transfer_verdict
from tools.s2_demand import WORLDS

# Sweet spot énergie (EDR 085) : survie ×4, gradient champion/tabula ~4-5×. Sans lui : plancher létal.
SWEET_METAB = 0.25
SWEET_PAYOFF = 3.0

# Plancher sous lequel un bras est tenu pour ÉTEINT sur un seed d'éval (même epsilon que le plancher
# de division de `paired_ratios` : une survie médiane ≤ 1e-6 est un zéro, pas une petite mesure).
EPS_SURVIE = 1e-6

# n MINIMAL pour que le test de signe bilatéral EXACT puisse un jour franchir 0.05 : sa p-value
# PLANCHER vaut 2/2**n (tous les seeds du même côté). En dessous, l'instrument est STRUCTURELLEMENT
# incapable de rendre autre chose que NEUTRE — quelle que soit la dose. C'est l'argument (classe E1)
# qui justifie déjà le refus d'une baseline trop courte ; il vaut à l'identique quand c'est l'ÉCART
# des paires éteintes qui fait tomber le n. CALCULÉ, jamais écrit en dur : si le seuil bougeait, le
# plancher suivrait.
N_MIN_SIGNE = next(n for n in range(1, 64) if 2.0 / 2 ** n < 0.05)     # -> 6


def _bras_valide(nom: str, valeurs) -> List[float]:
    """Garde de DOMAINE d'un bras de survie -> liste de floats, ou LÈVE. PURE, sans effet de bord.

    Une survie médiane est une médiane d'âges ENTIERS ≥ 0 : elle est finie et non négative. `nan`,
    `±inf` et les négatifs ne sont donc pas des mesures, ce sont des entrées CORROMPUES (baseline
    resérialisée, mesure perdue, bug d'appelant) — et sans cette garde chacune produisait une
    affirmation de FOND, mesurée le 2026-09-08 sur `run_direction` :

      * `tabula = +inf`  -> ratio = x/inf = 0.0, **fini** : `compute_transfer_verdict` ne peut PAS le
        détecter (il ne filtre que les ratios non finis) -> verdict **NEUTRE** publié à côté d'un
        `tabula_median=inf` ;
      * `tabula < 0`     -> `max(-5, 1e-6)` ramène au plancher epsilon -> ratio 2e7 sur tous les
        seeds -> verdict **TRANSFERE** (p<0.001), le résultat le plus fort de l'instrument, produit
        par une survie NÉGATIVE ;
      * `nan`            -> attrapé en aval, mais après coup, et le rapport publiait quand même un
        `median_ratio` calculé sur les seuls seeds finis.

    ⚠️ `0.0` est LÉGAL et doit passer : c'est une extinction MESURÉE (tout le monde meurt au premier
    tick), traitée par `paires_informatives`. Une garde qui refuserait le zéro rendrait l'instrument
    aveugle au régime létal — cf. le cas négatif apparié `..._ACCEPTS_a_measured_zero`."""
    out: List[float] = []
    for i, v in enumerate(valeurs):
        try:
            x = float(v)
        except (TypeError, ValueError):
            raise ValueError(
                f"run_direction : argument degenere ({nom}[{i}]={v!r} n'est pas un nombre) -- une "
                "survie mediane est une mediane d'ages ; ne pas confondre avec une survie nulle.")
        if not np.isfinite(x) or x < 0.0:
            raise ValueError(
                f"run_direction : argument degenere ({nom}[{i}]={x}) -- une survie mediane est "
                "FINIE et >= 0 (mediane d'ages entiers). Un nan/inf/negatif n'est pas une mesure "
                "mais une entree CORROMPUE, et sans ce refus elle PRODUISAIT un verdict : +inf -> "
                "'NEUTRE', negatif -> 'TRANSFERE' a ratio 2e7. Le zero, lui, reste LEGAL "
                "(extinction MESUREE).")
        out.append(x)
    return out


def paired_ratios(champ_meds: List[float], tabula_meds: List[float]) -> List[float]:
    """Ratios de transfert appariés par index (seed d'éval) : champ / tabula, tronqué à la longueur
    commune. PUR (testable sans biosphère). tabula=0 -> plancher epsilon (pas de division par zéro).

    ⚠️ PRIMITIVE BRUTE — deux pièges que l'APPELANT doit traiter AVANT d'agréger, et que
    `run_direction` traite depuis le 2026-09-08 (les deux comportements ci-dessous sont le contrat
    PUBLIÉ de la primitive, figé par `tests/test_cross_world_transfer.py` ; on ne les change pas ici,
    on les garde là où un VERDICT se publie) :

    * **paire doublement ÉTEINTE** : les deux bras à 0 rendent `0 / 1e-6 = 0.0`, un ratio qui a l'air
      DÉFAVORABLE alors qu'aucun contraste n'a été mesuré (et qui survit au filtre `r != 1.0` du test
      de signe). Filtrer par `paires_informatives` avant d'agréger.
    * **troncature `min()` SILENCIEUSE** : deux bras de longueurs différentes ne sont pas une simple
      perte de paires — l'appariement est positionnel, et le `n` s'effondre sans aucun signal.
      Vérifier les longueurs chez l'appelant."""
    n = min(len(champ_meds), len(tabula_meds))
    return [champ_meds[i] / max(tabula_meds[i], 1e-6) for i in range(n)]


def paires_informatives(champ_meds: List[float], tabula_meds: List[float],
                        eps: float = EPS_SURVIE):
    """Indices des paires (seeds d'éval) qui portent une information de transfert, et COMPTE des
    écartées. Renvoie `(retenus, n_ecartees)`. PUR.

    Une paire dont les DEUX bras ont une survie médiane nulle ne porte NI signe NI amplitude : le
    plancher epsilon de `paired_ratios` en fait `0.0`, donc une paire « défavorable au champion »
    tirée d'une absence totale de mesure. Une paire dont UN SEUL bras est éteint reste informative
    (le SIGNE est défini : l'un survit, l'autre non) et n'est PAS écartée — sinon l'instrument
    deviendrait aveugle au cas le plus tranché.

    Même idiome, même défaut, que `dream_causal_probe._paired_ratios` (corrigé le 2026-07-21 :
    « deux bras identiques et éteints rendaient CAUSE_NUISIBLE, ratio 0.0, sign_p 0.00195 ») et
    jamais rétro-appliqué ici — classe E14."""
    n = min(len(champ_meds), len(tabula_meds))
    retenus = [i for i in range(n)
               if not (float(champ_meds[i]) <= eps and float(tabula_meds[i]) <= eps)]
    return retenus, n - len(retenus)


def _sweet_config() -> WorldConfig:
    cfg = WorldConfig()
    cfg.base_metabolism = SWEET_METAB
    cfg.forage_payoff = SWEET_PAYOFF
    return cfg


def measure_in_world(world_key: str, genome, seed: int, k_eval: int = 12,
                     num_agents: int = 12, max_ticks: int = 300) -> List[float]:
    """Survie médiane d'une cohorte fixe dans le monde `world_key`, sur k_eval seeds d'éval appariables
    (seed base + i). genome=None -> tabula-rasa (MambaAgent init aléatoire). Cohorte fixe (benchmark),
    nuit OFF, scaffolds OFF (régime S2/EDR-118), memory_retriever neutralisé (repro + anti-contention).
    Retourne une médiane de survie PAR seed d'éval (unité d'appariement)."""
    # ⚠️ GARDE D'ARGUMENTS, EN TETE (2026-09-01). Sans elle, une cohorte vide ou un horizon nul
    # produisait une MESURE : 0.0 rendu comme survie observee, puis lu par un verdict comme
    # « reste au plancher ». Un argument degenere n'est pas un resultat scientifique, c'est une
    # erreur d'appel -> on LEVE, on ne rend pas de sentinelle qui entrerait dans une moyenne.
    # Posee AVANT la construction du monde : le refus ne coute aucune simulation.
    if int(k_eval) <= 0 or int(num_agents) <= 0 or int(max_ticks) <= 0:
        raise ValueError(
            f"measure_in_world : argument degenere (k_eval={k_eval}, num_agents={num_agents}, max_ticks={max_ticks}) -- "
            "aucune mesure possible ; ne pas confondre avec une survie nulle MESUREE.")
    world_cls = WORLDS[world_key]
    meds: List[float] = []
    for i in range(max(1, k_eval)):
        seed_at(seed, i)
        env = world_cls(_sweet_config())
        env.benchmark_mode = True        # cohorte fixe : pas de repro/mutation/HGT (on mesure LE génome)
        env.night_enabled = False        # régime cohérent EDR-118 (isole le monde)
        env.current_era = 10_000         # scaffolds annelés -> 0
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
            env.memory_retriever.clear()
        for _ in range(num_agents):
            a = MambaAgent()
            if genome is not None:
                a.from_genome(genome)    # dims hétérogènes gérées par padding dynamique du batch model
            env.add_agent(a, energy=80.0)
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
        ages = [int(a["age"]) for a in env.agents + list(getattr(env, "dead_agents", []))]
        meds.append(float(np.median(ages)) if ages else 0.0)
    return meds


def _load_genome(hof_path: str):
    """Génome du #1 d'un HoF donné (via override HOF_PATH, seam EDR-155)."""
    import importlib
    os.environ["HOF_PATH"] = hof_path
    importlib.reload(persistence)
    _v, entries = persistence.load_hall_of_fame()
    if not entries:
        raise RuntimeError(f"HoF vide : {hof_path}")
    return entries[0].genome


def run_direction(source_label: str, source_hof: str, target_world: str,
                  seed: int = 42, k_eval: int = 12, num_agents: int = 12,
                  max_ticks: int = 300, tabula_meds: Optional[List[float]] = None) -> Dict:
    """Un bras de transfert : champion de `source_hof` (évolué dans source_label) lâché dans
    `target_world`, vs tabula-rasa dans le même monde (appariés seed à seed). tabula_meds réutilisable
    (indépendant du champion source) pour ne pas re-mesurer la baseline à chaque champion.

    ⚠️ TROIS DÉFAUTS CORRIGÉS le 2026-09-08, exposés par injection à dose connue
    (`tests/sandbox/test_inj_run_direction.py`). Les trois PUBLIAIENT une affirmation de FOND sur le
    KPI `transfer_ratio` (spec SDR-G1, EDR-156/129) à partir d'une entrée vide, absente ou tronquée
    — le biais systématique n°1 du dépôt, et dans un dépôt où « pas de transfert » est le résultat
    attendu, un négatif fabriqué ressemble à tous les autres.

    1. **baseline VIDE -> LÈVE.** `tabula_meds=[]` faisait tronquer `paired_ratios` à n=0, et
       `compute_transfer_verdict([])` rend `{'n': 0, 'median_ratio': 0.0, 'verdict': 'NEUTRE'}` :
       la ligne publiée était `NEUTRE | ratio_med=0.00 (n_fav=0/0, sign_p=1.0000) | tabula=0.0`,
       sans qu'AUCUNE comparaison ait eu lieu. Une baseline vide n'est pas une égalité observée,
       c'est un appel invalide.
    2. **longueur de baseline != k_eval -> LÈVE.** La troncature par `min()` était SILENCIEUSE, dans
       les deux sens : (a) baseline plus COURTE — n tombait à 2 pour k_eval=12, or sous 6 paires le
       test de signe ne peut JAMAIS descendre sous 0.05 (plancher 2/2^n), donc l'instrument devenait
       STRUCTURELLEMENT incapable de rendre autre chose que NEUTRE quelle que soit la dose (classe
       E1, un contrôle qui ne peut plus se déclencher) ; (b) baseline plus LONGUE — le rapport
       publiait `tabula_median` sur les valeurs FOURNIES pendant que le verdict portait sur les
       valeurs UTILISÉES (`TRANSFERE | ratio_med=2.00 | champ=2.0 tabula=500.5`). L'appelant DÉCLARE
       son k_eval ; on ne devine pas.
    3. **EXTINCTION TOTALE -> INDETERMINE NOMMÉ, jamais NUIT.** Quand les deux bras mesurent une
       survie médiane nulle (plancher létal, ou `ages` vide -> `meds.append(0.0)`), chaque ratio
       valait `0 / 1e-6 = 0.0` : médiane 0.0, 0/12 favorables, sign_p = 0.00049 -> **« NUIT »
       (p<0.001) alors que rien n'a été mesuré des deux côtés**. Les paires doublement éteintes sont
       désormais ÉCARTÉES et COMPTÉES (`n_ecartees`) ; si elles le sont toutes, le verdict est
       `INDETERMINE_EXTINCTION_TOTALE`. Le défaut agissait dans les DEUX sens : une extinction
       PARTIELLE empoisonnait aussi la médiane et gonflait le dénominateur du test de signe (6 paires
       éteintes + 6 paires à 2.0 rendaient NEUTRE au lieu de TRANSFERE).

    ⚠️ TROIS DÉFAUTS DE PLUS, trouvés par le RÉFUTATEUR le même jour, sur le correctif lui-même.
    Les trois étaient des affirmations de FOND, et les deux premiers ont été OUVERTS par la
    correction ci-dessus (une garde qui déplace un défaut ne le ferme pas) :

    4. **Le rapport re-publiait des médianes que le verdict ne décrivait pas.** L'écart des paires
       doublement éteintes a rouvert, par sa propre porte, le défaut (b) que le point 2 fermait :
       `champ_median` / `tabula_median` portaient sur les k_eval paires, le verdict sur les seules
       retenues. Dose mesurée : 8 paires éteintes + 6 paires à 10 vs 5 imprimait
       `TRANSFERE | ratio_med=2.00 (n_fav=6/6, ecartees=8) | champ=0.0 tabula=0.0` — un transfert
       POSITIF publié à côté d'un champion de survie NULLE. 950 cas sur 4000 doses tirées au sort
       en extinction partielle, dont 54 à `champ_median=0.0`. Les médianes publiées portent
       désormais sur les paires RETENUES ; les brutes restent, sous `*_toutes_paires`.
    5. **`INDETERMINE_PUISSANCE_DETRUITE`.** L'écart pouvait faire tomber le n sous les
       `N_MIN_SIGNE` paires en deçà desquelles le test de signe ne peut JAMAIS franchir 0.05 — donc
       NEUTRE par construction. C'est MOT POUR MOT l'argument de classe E1 qui fait lever au point 2
       sur une baseline trop courte, et il rentrait ici par la porte de derrière : 11 paires
       éteintes + 1 paire à 10 vs 5 publiaient `NEUTRE (n_fav=1/1, ecartees=11, sign_p=1.0000)`.
    6. **Aucune garde de DOMAINE sur la baseline.** `nan`, `±inf` et les négatifs passaient la garde
       de longueur et PRODUISAIENT un verdict : `+inf` -> ratio 0.0 (fini ! donc invisible pour le
       filtre de non-finitude de `compute_transfer_verdict`) -> **NEUTRE** ; négatif -> ramené au
       plancher epsilon -> ratio 2e7 sur tous les seeds -> **TRANSFERE (p<0.001)**, le résultat le
       plus fort de l'instrument produit par une survie NÉGATIVE. Cf. `_bras_valide`, posée en tête
       ET en post-condition des bras MESURÉS (la post-condition était DÉCORATIVE : la mutation qui
       la supprimait ne faisait rougir aucun test).

    ⚠️ CE QUE CES GARDES NE FONT PAS (cas négatifs appariés, classe E1 — une garde increvable serait
    pire que le défaut) : un champion qui MEURT contre une baseline vivante rend toujours NUIT ; une
    baseline qui meurt contre un champion vivant rend toujours TRANSFERE ; une extinction partielle
    laisse le verdict se prononcer sur les paires informatives restantes, à puissance réduite et
    ANNONCÉE, TANT QU'IL EN RESTE ASSEZ ; un `0.0` MESURÉ reste une mesure légale ; et un appelant
    qui DÉCLARE k_eval=5 garde son NEUTRE sous-puissant (c'est son plan d'expérience, pas une perte
    silencieuse). Cf. les tests `..._KNOWS_HOW_TO_STAY_DOWN_...` et `..._ACCEPTS_...`.

    ✅ EDR-156/129 n'est PAS affecté : ses quatre bras publient tabula 17.8-18.0 et champ 36-136 —
    aucun zéro, donc aucune paire écartée, et les baselines y ont exactement k_eval=12 valeurs
    (mesurées par `measure_in_world` avec le même k_eval). Les trois défauts étaient LATENTS.
    """
    # GARDE D'ARGUMENTS, EN TETE (2026-09-06, elargie le 2026-09-08). Orchestrateur : il n'entraine
    # pas lui-meme mais AGREGE en verdict -- une cohorte/liste de seeds vide produit une agregation
    # VIDE que l'aval lit comme une mesure (biais negatif systematique). Refus instantane, AVANT
    # `_load_genome` (qui ecrit os.environ et RECHARGE `src.seed_ai.persistence` : effet de bord
    # global) et donc avant toute mesure.
    if int(k_eval) <= 0 or int(num_agents) <= 0 or int(max_ticks) <= 0:
        raise ValueError(
            f"run_direction : argument degenere (k_eval={k_eval} num_agents={num_agents} max_ticks={max_ticks}) -- aucune mesure possible ; "
            "ne pas confondre avec une mesure nulle OBSERVEE.")
    if tabula_meds is not None:
        # DOMAINE avant tout le reste : nan / inf / negatif ne sont pas des survies (cf. _bras_valide).
        tabula_meds = _bras_valide("tabula_meds", tabula_meds)
        if not tabula_meds:
            raise ValueError(
                "run_direction : argument degenere (tabula_meds=[]) -- une baseline VIDE ne donne "
                "AUCUNE paire a comparer. Le verdict NEUTRE qui en sortait etait une affirmation de "
                "FOND fabriquee a partir d'une absence de mesure ; ne pas confondre avec une "
                "egalite OBSERVEE entre le champion et tabula-rasa.")
        if len(tabula_meds) != int(k_eval):
            raise ValueError(
                f"run_direction : argument degenere (len(tabula_meds)={len(tabula_meds)} != "
                f"k_eval={int(k_eval)}) -- l'appariement est POSITIONNEL (l'index i designe le seed "
                "d'eval `seed_at(seed, i)`) et la troncature par min() est SILENCIEUSE : elle jette "
                "des seeds (le n s'effondre, et sous 6 paires le test de signe ne peut plus "
                "franchir 0.05 quelle que soit la dose) ou publie la mediane de valeurs INUTILISEES. "
                "L'appelant DECLARE son k_eval, on ne le devine pas.")
    champ = _load_genome(source_hof)
    champ_meds = measure_in_world(target_world, champ, seed, k_eval, num_agents, max_ticks)
    if tabula_meds is None:
        tabula_meds = measure_in_world(target_world, None, seed, k_eval, num_agents, max_ticks)
    # POST-CONDITION appariee a la garde ci-dessus : un bras MESURE qui ne couvrirait pas les k_eval
    # seeds re-ouvrirait la troncature silencieuse par la porte de derriere. Le DOMAINE y est
    # verifie aussi : `measure_in_world` ne peut pas rendre de nan aujourd'hui, mais la garde de
    # tete ne protege que la baseline FOURNIE -- laisser le bras MESURE sans garde, c'est laisser
    # une porte que le refactoring suivant ouvrira (les deux branches sont exercees par
    # `..._REFUSES_a_MEASURED_arm_that_is_degenerate`, sinon la post-condition serait DECORATIVE :
    # la mutation qui la supprime ne faisait rougir AUCUN test le 2026-09-08).
    if len(champ_meds) != int(k_eval) or len(tabula_meds) != int(k_eval):
        raise ValueError(
            f"run_direction : mesure degeneree (champ={len(champ_meds)} valeurs, "
            f"tabula={len(tabula_meds)}) pour k_eval={int(k_eval)} -- les deux bras doivent couvrir "
            "les MEMES seeds d'eval ; des longueurs inegales seraient tronquees en silence.")
    champ_meds = _bras_valide("champ_meds (MESURE)", champ_meds)
    tabula_meds = _bras_valide("tabula_meds (MESURE)", tabula_meds)

    retenus, n_ecartees = paires_informatives(champ_meds, tabula_meds)
    champ_ret = [champ_meds[i] for i in retenus]
    tabula_ret = [tabula_meds[i] for i in retenus]
    ratios = paired_ratios(champ_ret, tabula_ret)
    # PLANCHER DE BRUIT DE L'ESTIMATEUR, publie a cote du ratio. Une paire retenue dont le SEUL
    # denominateur est eteint (tabula 0, champion vivant) porte un SIGNE reel -- c'est le contraste
    # le plus tranche qui soit -- mais son AMPLITUDE est fabriquee par le plancher epsilon
    # (20 / 1e-6 = 2e7). Le verdict, qui ne lit qu'un SEUIL et un test de SIGNE, reste valide ;
    # `median_ratio`, lui, ne veut plus rien dire. On ne le corrige pas en silence, on l'ANNONCE.
    n_denominateurs_eteints = sum(1 for i in retenus if tabula_meds[i] <= EPS_SURVIE)
    # ⚠️ LES MEDIANES PUBLIEES PORTENT SUR LES PAIRES RETENUES -- celles dont le verdict parle.
    # Corrige le 2026-09-08 (refutateur) : l'ecart des paires doublement eteintes RE-OUVRAIT, par sa
    # propre porte, le defaut (b) que la garde de longueur venait de fermer (« le rapport publiait
    # tabula_median sur les valeurs FOURNIES pendant que le verdict portait sur les valeurs
    # UTILISEES »). Mesure : 8 paires eteintes + 6 paires a 10 vs 5 rendait la ligne
    # `TRANSFERE | ratio_med=2.00 (n_fav=6/6, ecartees=8) | champ=0.0 tabula=0.0` -- un verdict de
    # transfert POSITIF publie a cote d'un champion a survie NULLE. Sur 4000 doses tirees au sort en
    # regime d'extinction partielle, 950 verdicts de fond etaient dans ce cas, dont 54 avec
    # champ_median=0.0. Les medianes BRUTES restent publiees, sous un nom qui dit ce qu'elles sont.
    rapport = {"source": source_label, "target": target_world,
               "champ_median": float(statistics.median(champ_ret)) if retenus else None,
               "tabula_median": float(statistics.median(tabula_ret)) if retenus else None,
               "champ_median_toutes_paires": float(statistics.median(champ_meds)),
               "tabula_median_toutes_paires": float(statistics.median(tabula_meds)),
               "n_paires": int(k_eval), "n_ecartees": n_ecartees,
               "n_denominateurs_eteints": n_denominateurs_eteints,
               "champ_meds": champ_meds, "tabula_meds": tabula_meds, "ratios": ratios,
               "_tabula_meds": tabula_meds}
    # `None` et pas `nan`/`0` pour TOUTE grandeur qui n'existe pas : serialisable en JSON, et une
    # arithmetique faite dessus par megarde LEVE au lieu de se propager en silence (le nan avale, le
    # None crie). `n_favorable` en fait partie : « 0 favorable sur 0 » se relit comme une mesure
    # (aucun seed n'a favorise le champion), alors qu'aucun seed n'a ete compare.
    _absent = {"median_ratio": None, "n_favorable": None, "sign_p": None}
    if not retenus:
        return {**rapport, **_absent, "verdict": "INDETERMINE_EXTINCTION_TOTALE", "n": 0,
                "n_indetermine": n_ecartees,
                "why": (f"les {n_ecartees} paires ont les DEUX bras a survie mediane nulle : aucun "
                        "contraste de transfert n'est mesurable dans ce regime. Ce n'est PAS "
                        "'le transfert nuit', c'est 'rien n'a ete mesure' -- les deux etaient "
                        "indiscernables dans CWT_JSON avant le 2026-09-08.")}
    if n_ecartees and len(retenus) < N_MIN_SIGNE:
        # PUISSANCE DETRUITE PAR L'ECART. Le meme argument qui fait LEVER sur une baseline trop
        # courte : sous N_MIN_SIGNE paires, la p-value plancher du test de signe (2/2**n) ne peut
        # JAMAIS franchir 0.05, donc le verdict est NEUTRE par construction -- un controle qui ne
        # peut plus se declencher (classe E1). Avant ce correctif, 11 paires eteintes + 1 paire a
        # 10 vs 5 publiaient `NEUTRE | ratio_med=2.00 (n_fav=1/1, ecartees=11, sign_p=1.0000)` :
        # sur un KPI dont « pas de transfert » est le resultat ATTENDU, ce negatif fabrique
        # ressemble a tous les autres. On NE leve PAS (les mesures, elles, sont valides et le
        # regime letal est un fait a publier) : on NOMME l'indetermination.
        # ⚠️ Portee VOLONTAIREMENT limitee a `n_ecartees > 0`. Un appelant qui DECLARE k_eval=5
        # garde son NEUTRE sous-puissant : c'est SON plan d'experience, pas une perte silencieuse
        # (cf. `..._READS_sign_p_and_refuses_the_SAME_dose_under_power`, laisse intact -- E14).
        return {**rapport, **_absent, "verdict": "INDETERMINE_PUISSANCE_DETRUITE",
                "n": len(retenus), "n_indetermine": n_ecartees,
                "why": (f"{n_ecartees} paire(s) sur {int(k_eval)} ECARTEE(S) (les DEUX bras "
                        f"eteints) : il reste {len(retenus)} paire(s) informative(s), sous les "
                        f"{N_MIN_SIGNE} qu'exige le test de signe pour pouvoir franchir 0.05. "
                        "L'instrument ne peut plus rendre que 'NEUTRE' QUELLE QUE SOIT la dose : "
                        "ce n'est pas 'pas de transfert', c'est 'plus assez de paires pour le "
                        "dire'. Refaire la mesure hors du regime letal (cf. sweet spot EDR 085).")}
    verdict = compute_transfer_verdict(ratios)
    out = {**verdict, **rapport}
    notes = []
    if n_ecartees:
        notes.append(
            f"{n_ecartees} paire(s) sur {int(k_eval)} ECARTEE(S) : les DEUX bras y sont eteints "
            f"(survie mediane nulle), donc aucune information de transfert. Le verdict "
            f"'{verdict['verdict']}' porte sur les {verdict['n']} paires informatives restantes, et "
            "le sign_p publie est celui de ce n REDUIT -- pas celui de k_eval. Les medianes "
            f"publiees (champ={rapport['champ_median']:.4g}, tabula={rapport['tabula_median']:.4g}) "
            "portent sur ces MEMES paires retenues ; les brutes sont sous "
            "champ_median_toutes_paires / tabula_median_toutes_paires.")
    if n_denominateurs_eteints:
        notes.append(
            f"{n_denominateurs_eteints} paire(s) retenue(s) ont un DENOMINATEUR eteint (tabula a "
            f"survie nulle, champion vivant) : le SIGNE y est reel, mais l'AMPLITUDE du ratio est "
            f"fabriquee par le plancher epsilon {EPS_SURVIE:g} de paired_ratios. Lire le VERDICT "
            "(seuil + test de signe), pas le median_ratio.")
    if notes:
        out["why"] = " | ".join(notes)
    return out


def _fmt(x, spec: str = "{:.2f}") -> str:
    """Formate une grandeur PUBLIÉE, ou `n/a` quand elle n'existe pas (verdict INDETERMINE).
    Sans ça, l'impression planterait sur un `None` — ou pire, un `0.0` de remplacement se lirait
    comme une mesure, ce qui est exactement le défaut qu'on vient de fermer."""
    return spec.format(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else "n/a"


def main():
    seed = int(os.environ.get("CWT_SEED", "42"))
    k_eval = int(os.environ.get("CWT_KEVAL", "12"))
    num_agents = int(os.environ.get("CWT_NUM_AGENTS", "12"))
    max_ticks = int(os.environ.get("CWT_MAX_TICKS", "300"))
    famine_hofs = os.environ.get("CWT_FAMINE_HOFS",
                                 "data/hall_of_fame_famine.pkl,data/hall_of_fame_famine_s43.pkl,"
                                 "data/hall_of_fame_famine_s44.pkl").split(",")
    stone_hof = os.environ.get("CWT_STONE_HOF", "data/hall_of_fame.pkl")

    results = []
    # famine -> stoneage : 3 champions famine, baseline tabula-stoneage mesurée une seule fois
    tabula_stone = measure_in_world("stoneage", None, seed, k_eval, num_agents, max_ticks)
    for i, hof in enumerate(famine_hofs):
        hof = hof.strip()
        if not hof:
            continue
        r = run_direction(f"famine[{os.path.basename(hof)}]", hof, "stoneage", seed, k_eval,
                          num_agents, max_ticks, tabula_meds=tabula_stone)
        results.append(r)
    # stoneage -> famine : champion stoneage global
    results.append(run_direction("stoneage", stone_hof, "famine", seed, k_eval,
                                 num_agents, max_ticks))

    for r in results:
        r.pop("_tabula_meds", None)
        ecart = ", ecartees={}".format(r["n_ecartees"]) if r.get("n_ecartees") else ""
        # `n_favorable` passe par `_fmt` comme les autres : sur un verdict INDETERMINE il vaut None,
        # et un `n_fav=0/0` imprime se relirait comme « aucun seed n'a favorise le champion ».
        print(f"{r['source']:32s} -> {r['target']:9s} | {r['verdict']:31s} "
              f"| ratio_med={_fmt(r['median_ratio'])} "
              f"(n_fav={_fmt(r['n_favorable'], '{:d}')}/{r['n']}{ecart}, "
              f"sign_p={_fmt(r['sign_p'], '{:.4f}')}) | champ={_fmt(r['champ_median'], '{:.1f}')} "
              f"tabula={_fmt(r['tabula_median'], '{:.1f}')}")
        if r.get("why"):
            print(f"{'':32s}    /!\\ {r['why']}")
    print("CWT_JSON", json.dumps([{k: v for k, v in r.items()
                                   if k not in ("champ_meds", "tabula_meds", "ratios")} for r in results]))
    return results


if __name__ == "__main__":
    main()
