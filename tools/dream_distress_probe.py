"""Sonde de signature de détresse du dreaming (Phase 1-A, corrélationnel). Les rêves se concentrent-
ils chez les agents proches de la mort ? Spec : docs/superpowers/specs/2026-06-24-Dream-Distress-
Signature-design.md. ORIENTANT, pas définitif (la Phase 2 causale tranche). Diagnostic seul."""
import os
import sys
import math
import logging
import statistics
from typing import List, Dict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.curriculum_transfer import _sign_test_p


# ---------------------------------------------------------------------------------------------------
# VOCABULAIRE D'INDETERMINATION (2026-09-08, INJ6). Une mesure ABSENTE se NOMME ; elle ne se convertit
# JAMAIS en zero. Les trois causes cote-ere sont distinctes parce qu'elles appellent des suites
# differentes : l'ere n'a rendu aucun agent mesurable / le contraste n'a qu'un seul cote / l'organe
# n'a produit aucun reve (panne d'INTERVENTION, pas fait sur la detresse).
MESURE_OK = "OK"
INDET_AUCUN_AGENT = "INDETERMINE_AUCUN_AGENT_MESURABLE"
INDET_GROUPE_VIDE = "INDETERMINE_GROUPE_VIDE"
INDET_AUCUN_REVE = "INDETERMINE_AUCUN_REVE"
INDET_AUCUN_SEED = "INDETERMINE_AUCUN_SEED"
INDET_AUCUNE_MESURE = "INDETERMINE_AUCUNE_MESURE"
INDET_PARTIEL = "INDETERMINE_MESURES_PARTIELLES"
INDET_NON_FINIE = "INDETERMINE_MESURE_NON_FINIE"

# REGIME de la sonde, nomme UNE fois et cable PARTOUT -- l'appel ET la provenance archivee lisent ces
# constantes. Le verdict n'a de sens qu'ici : organe porte par TOUTE la cohorte (`organ_fraction=1.0`),
# sweet spot metabolique d'EDR 092, plancher d'age qui ecarte l'artefact petit-age. Recopier ces
# valeurs a la main dans le bloc `config` laisserait la provenance MENTIR le jour ou l'appel change ;
# le rapport archive ne pouvait alors PAS dire a quel regime le verdict avait ete obtenu.
ORGAN_FRACTION = 1.0
SWEET_METAB = 0.25
SWEET_PAYOFF = 3.0
AGE_FLOOR = 10


def _sans_mesure(x) -> bool:
    """True si `x` n'est PAS une mesure : `None` (indetermination NOMMEE, la convention de ce module)
    ou une valeur flottante NON FINIE -- `nan` (indetermination ACCIDENTELLE, p.ex. un `total_dreams`
    deja nan chez l'appelant) comme `±inf` (`inf > 0` est True EN SILENCE : un delta infini ressortait
    en DETRESSE avec `median_delta=inf` publie a cote).

    ⚠️ POURQUOI `None` ET PAS `nan` COMME CONVENTION. `nan > 0` rend False EN SILENCE : une non-mesure
    qui traverse `distress_verdict` y tomberait dans la branche `else` et ressortirait en NEUTRE --
    exactement le defaut qu'on corrige, deplace d'un cran (c'est le raisonnement deja ecrit dans
    `tools/dreaming_probe.py::run_q1`, qui REFUSE de propager son nan). `None > 0` leve TypeError :
    un aval qui oublierait de traiter le cas casse au lieu de fabriquer un verdict de fond. `None` est
    en outre serialisable en JSON (`null`) -- le resultat est archive par `Harness.save`."""
    return x is None or (isinstance(x, float) and not math.isfinite(x))


def _f3(x) -> str:
    """Format de log qui NE MENT PAS sur une non-mesure : `None` s'affiche `None`, jamais `0.000`."""
    return "None" if x is None else (f"{x:.3f}" if isinstance(x, (int, float)) else str(x))


def dream_rate(agent: Dict) -> float:
    """Taux de rêve ajusté à l'exposition : total_dreams / max(age, 1) (age 0 -> dénominateur 1)."""
    return agent.get("total_dreams", 0) / max(agent.get("age", 0), 1)


def distress_split(stats: List[Dict], age_floor: int = AGE_FLOOR) -> Dict:
    """Filtre age >= age_floor (écarte l'artefact petit-âge), split par âge médian, compare le taux
    de rêve médian des court-vivants vs long-vivants. delta = rate_short - rate_long (>0 = détresse).

    Rend TOUJOURS `status`. `delta` n'est un nombre QUE si le contraste a ete MESURE ; sinon il vaut
    `None` et `status` NOMME la cause. Trois defauts reels corriges le 2026-09-08 (INJ6), tous de la
    forme (a) du biais du depot -- entree absente -> affirmation de FOND :

    * `if not kept: ... delta 0.0` rendait un delta NUL comme une MESURE quand l'ere ne rend AUCUN
      agent (extinction totale) ou quand TOUS meurent sous `age_floor` -- ce que le plancher est
      justement la pour signaler. Agrege, ca publiait NEUTRE : « les reves ne se concentrent pas chez
      les mourants », le negatif recherche, obtenu sans une seule mesure.
    * `r_short = median(...) if short else 0.0` posait le taux d'un groupe ABSENT a 0.0. Quand tous
      les agents meurent au MEME age (extinction a `max_ticks`), la mediane d'age EGALE cet age, le
      groupe court-vivant est VIDE, et delta = 0.0 - rate_long publiait BENEFIQUE (« le reve
      protege ») a partir d'un split dont un cote n'existe pas.
    * aucune garde d'AMPLITUDE : une cohorte entierement porteuse de l'organe qui ne reve pas une
      seule fois rendait delta = 0.0 - 0.0 -> NEUTRE, lisible comme un negatif solide. Zero reve est
      une panne d'INTERVENTION ; la question « les reves se concentrent-ils ? » n'a alors pas d'objet.

    Un QUATRIEME, de la forme (b) cette fois (l'instrument SAIT et ne le dit pas), trouve par la revue
    adversariale le meme jour : un taux NON FINI ressortait estampille `OK` avec `delta = nan` -- donc
    un indetermine ANONYME (`raisons` vide) en amont, et un `NaN` nu dans l'archive JSON. Cf. la garde
    `INDET_NON_FINIE` ci-dessous.

    ⚠️ Contre-exemples apparies (classe E1) -- ce que la garde doit continuer a MESURER :
    un contraste nul ENTRE DEUX GROUPES PEUPLES QUI ONT REVE reste `OK` avec delta = 0.0 (c'est une
    mesure), et des taux medians nuls chez une cohorte qui a reve restent `OK` : le lavage par la
    mediane (EDR-094) est un defaut d'AGREGAT, distinct, non traite ici -- cf. le test qui le gele."""
    kept = [s for s in stats if s.get("age", 0) >= age_floor]
    if not kept:
        return {"rate_short": None, "rate_long": None, "delta": None,
                "n_short": 0, "n_long": 0, "status": INDET_AUCUN_AGENT}
    med_age = statistics.median([s["age"] for s in kept])
    short = [s for s in kept if s["age"] < med_age]
    long = [s for s in kept if s["age"] >= med_age]
    # Le taux d'un groupe ABSENT est None (indetermine), jamais 0.0 : personne n'y a ete mesure.
    r_short = float(statistics.median([dream_rate(s) for s in short])) if short else None
    r_long = float(statistics.median([dream_rate(s) for s in long])) if long else None
    out = {"rate_short": r_short, "rate_long": r_long, "delta": None,
           "n_short": len(short), "n_long": len(long), "status": MESURE_OK}
    if not short or not long:
        out["status"] = INDET_GROUPE_VIDE
        return out
    # 4e defaut, trouve par le REFUTATEUR le 2026-09-08 -- forme (b) du biais du depot (l'instrument
    # SAIT et ne le dit pas), sur le chemin meme que ce module venait de durcir. Un taux NON FINI
    # (`total_dreams` deja nan chez l'appelant) traversait ici et ressortait estampille `OK` avec
    # `delta = nan`. Deux consequences MESUREES : (i) `run_distress` ne comptait donc AUCUNE raison
    # (`raisons == {}`) alors que `distress_verdict` comptait bien un indetermine -- l'indetermination
    # devenait ANONYME, exactement ce que le bloc `raisons` existe pour empecher ; (ii) `Harness.save`
    # archivait un `NaN` nu, qui n'est PAS du JSON valide (`json.loads(..., parse_constant=raise)`
    # leve) -- la propriete « JSON strict » que ce module revendique ne tenait que sur ses branches
    # `None`. Le cote FINI reste publie ; seul le cote casse passe a None.
    if _sans_mesure(r_short) or _sans_mesure(r_long):
        out["rate_short"] = None if _sans_mesure(r_short) else r_short
        out["rate_long"] = None if _sans_mesure(r_long) else r_long
        out["status"] = INDET_NON_FINIE
        return out
    # Garde d'AMPLITUDE, sur la cohorte RETENUE (celle qui entre dans la mesure) : sans un seul reve,
    # les deux taux sont mesures a 0.0 mais leur DIFFERENCE ne dit rien de la detresse.
    if sum(float(s.get("total_dreams", 0) or 0) for s in kept) <= 0.0:
        out["status"] = INDET_AUCUN_REVE
        return out
    out["delta"] = r_short - r_long
    return out


def distress_verdict(deltas: List[float], delta_eps: float = 0.0) -> Dict:
    """Agrège les delta par seed. DETRESSE = court-vivants rêvent plus (median > eps ET sign_p<0.1) ;
    BENEFIQUE = long-vivants rêvent plus (median < -eps ET sign_p<0.1) ; NEUTRE sinon. sign_p calculé
    sur les deltas EFFECTIFS (≠0) -> évite k>n (pattern compute_transfer_verdict)."""
    # ⚠️ ZERO SEED = ZERO VERDICT (classes E18/E4, 2026-09-01). Le cas vide etait code
    # EXPLICITEMENT et rendait une affirmation de FOND, toujours NEGATIVE. Rendre un verdict
    # neutre/negatif sans donnee, c'est recompenser l'absence de preuve.
    if not deltas:
        return {"median_delta": None, "n_favorable": 0, "sign_p": None,
                "n_mesurable": 0, "n_indetermine": 0, "verdict": INDET_AUCUN_SEED}
    # ⚠️ 2026-09-08 (INJ6) : un seed peut desormais rendre `delta = None` (contraste NON mesure, cf.
    # `distress_split`). Un tel seed n'est PAS un delta nul -- l'agreger comme tel referait, un cran
    # plus haut, le defaut qu'on vient de corriger. Il est donc SORTI de la mediane et du test de
    # signe, et son existence est PUBLIEE (`n_indetermine`) au lieu d'etre absorbee.
    mesures = [float(d) for d in deltas if not _sans_mesure(d)]
    n_ind = len(deltas) - len(mesures)
    if not mesures:
        return {"median_delta": None, "n_favorable": 0, "sign_p": None,
                "n_mesurable": 0, "n_indetermine": n_ind, "verdict": INDET_AUCUNE_MESURE}
    med = float(statistics.median(mesures))
    n_fav = sum(1 for d in mesures if d > 0.0)
    effective = [d for d in mesures if d != 0.0]
    sign_p = _sign_test_p(sum(1 for d in effective if d > 0.0), len(effective))
    if n_ind:
        # PARTIEL, pas « verdict sur les seeds qui restent ». L'unite de replication est le SEED :
        # laisser tomber ceux qui n'ont rien rendu changerait n en silence, et ce sont precisement
        # les seeds eteints -- correles au phenomene mesure -- qui disparaitraient. La mediane des
        # seeds MESURES reste publiee a cote du compte, mais elle n'est pas un verdict.
        verdict = INDET_PARTIEL
    elif med > delta_eps and sign_p < 0.1:
        verdict = "DETRESSE"
    elif med < -delta_eps and sign_p < 0.1:
        verdict = "BENEFIQUE"
    else:
        verdict = "NEUTRE"
    return {"median_delta": med, "n_favorable": n_fav, "sign_p": sign_p,
            "n_mesurable": len(mesures), "n_indetermine": n_ind, "verdict": verdict}


from src.environments.config import WorldConfig
from src.seed_ai.harness import Harness
from src.graph_rag.async_logger import logger as async_logger
from main_curriculum import _acquire_shared_db
from tools.dreaming_probe import run_era_organ

log = logging.getLogger("AGIseed.DreamDistress")


def run_distress(seeds, target, num_agents, max_ticks, shared_db) -> Dict:
    """Par seed : une ère organe-ON (organ_fraction=1.0) au sweet spot -> distress_split -> delta.
    Agrège en verdict. Le signal : les court-vivants rêvent-ils plus (détresse) ?"""
    # GARDE D'ARGUMENTS, EN TETE (2026-09-06). Orchestrateur : il n'entraine pas lui-meme mais
    # AGREGE en verdict -- une cohorte/liste de seeds vide produit une agregation VIDE que l'aval
    # lit comme une mesure (biais negatif systematique). Refus instantane, avant tout appel de run.
    # MATERIALISATION AVANT LA GARDE (2026-09-08, INJ6). `not list(seeds)` CONSOMMAIT l'iterable :
    # passe un generateur / `map` / `zip` -- la forme meme que produit un `(int(s) for s in ...)`
    # d'appelant -- la garde le vidait, la boucle ne tournait ZERO fois, `per_seed` restait vide et
    # l'orchestrateur publiait INDETERMINE_AUCUN_SEED avec `config.seeds=[]` : le rapport ARCHIVE
    # niait les seeds demandes, sans qu'aucune erreur ne soit levee. Meme defaut que
    # `run_s2(worlds=<iterateur>)` (corrige le 2026-09-07) et que `run_q1` (tools/dreaming_probe.py).
    # Le `list()` est DEVANT la garde, et la garde lit la liste MATERIALISEE.
    seeds = list(seeds)
    if not seeds or int(num_agents) <= 0 or int(max_ticks) <= 0:
        raise ValueError(
            f"run_distress : argument degenere (n_seeds={len(seeds)} num_agents={num_agents} max_ticks={max_ticks}) -- aucune mesure possible ; "
            "ne pas confondre avec une mesure nulle OBSERVEE.")
    per_seed = []
    for seed in seeds:
        stats = run_era_organ(target, seed, ORGAN_FRACTION, SWEET_METAB, SWEET_PAYOFF,
                              num_agents, max_ticks, shared_db)
        split = distress_split(stats, AGE_FLOOR)
        per_seed.append({"seed": int(seed), **split})
        # `%s` + `_f3` : `%.3f` levait TypeError sur les non-mesures desormais possibles, et
        # affichait surtout `0.000` la ou rien n'avait ete mesure.
        log.info("  seed=%s rate_short=%s rate_long=%s delta=%s (n_short=%d n_long=%d) [%s]",
                 seed, _f3(split["rate_short"]), _f3(split["rate_long"]), _f3(split["delta"]),
                 split["n_short"], split["n_long"], split["status"])
    verdict = distress_verdict([p["delta"] for p in per_seed])
    # Le POURQUOI de l'indetermination voyage avec elle : un INDETERMINE anonyme se relit comme un
    # incident d'outil, alors qu'il nomme ici un regime du monde (extinction, plancher d'age, organe
    # muet) sur lequel se decide la suite de l'experience.
    raisons: Dict[str, int] = {}
    for p in per_seed:
        if p["status"] != MESURE_OK:
            raisons[p["status"]] = raisons.get(p["status"], 0) + 1
    # Le REGIME voyage avec le verdict (refutateur, 2026-09-08). Le bloc archive disait target /
    # seeds / num_agents / max_ticks et TAISAIT ce dont le verdict depend : organe a 100 %, sweet
    # spot (metab, payoff), plancher d'age. Un rapport relu six mois plus tard ne pouvait pas dire
    # a quel regime il avait ete obtenu -- ni detecter qu'on l'avait change. Les valeurs viennent des
    # MEMES constantes que l'appel ci-dessus : la provenance ne peut plus diverger de ce qui a tourne.
    return {**verdict, "raisons": raisons, "per_seed": per_seed,
            "config": {"target": target, "seeds": [int(s) for s in seeds],
                       "num_agents": num_agents, "max_ticks": max_ticks,
                       "organ_fraction": ORGAN_FRACTION, "metab": SWEET_METAB,
                       "payoff": SWEET_PAYOFF, "age_floor": AGE_FLOOR}}


def main() -> Dict:
    os.environ["AGISEED_QUIET_LOG"] = "1"     # anti-segfault + vitesse (EDR 091/092), AVANT start()
    target = os.environ.get("DD_TARGET", "stoneage")
    seeds = [int(s) for s in os.environ.get("DD_SEEDS", "0,1,2").split(",") if s.strip()]
    num_agents = int(os.environ.get("DD_NUM_AGENTS", "40"))
    max_ticks = int(os.environ.get("DD_MAX_TICKS", "400"))

    async_logger.start()
    try:
        shared_db = _acquire_shared_db()
        log.info("=== Sonde detresse : cible=%s seeds=%s agents=%d ticks=%d ===",
                 target, seeds, num_agents, max_ticks)
        result = run_distress(seeds, target, num_agents, max_ticks, shared_db)
    finally:
        async_logger.stop()

    h = Harness(seed=min(seeds) if seeds else 0, name="dream_distress", with_db=False, config=WorldConfig())
    path = h.save(result, config=WorldConfig())
    # `%s` + `_f3` : les branches d'indetermination rendent `median_delta`/`sign_p` a None, et
    # `%.3f` levait dessus -- l'unique verdict d'indetermination de la chaine ne pouvait meme pas
    # s'afficher (aggravant releve par INJ6, 2026-09-08).
    # Denominateur = les seeds REELLEMENT MESURES (`n_favorable` ne compte que ceux-la depuis INJ6) :
    # ecrire `n_fav/len(per_seed)` melangerait mesures et non-mesures dans un meme rapport.
    log.info("VERDICT=%s median_delta=%s (n_fav=%d/%d mesures sur %d seeds, sign_p=%s) raisons=%s -> %s",
             result["verdict"], _f3(result["median_delta"]), result["n_favorable"],
             result.get("n_mesurable", len(result["per_seed"])), len(result["per_seed"]),
             _f3(result["sign_p"]), result.get("raisons", {}), path)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
