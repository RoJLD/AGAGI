#!/usr/bin/env python
"""S6 -- TAUX DE FAUX POSITIFS du marqueur within-subject sous init NON NULLE.

CONTEXTE (S2-006, verifie en forme close). Dans `tools/cognitive_demand_world_probe.py` la moitie
NECESSITE du theoreme 3-conditions est DEFINITIONNELLE, pas empirique :

  * `survive` fait `E += gain - metab` puis `if E <= 0: return t+1` sinon `return ticks` -> la survie
    ne depend que du SIGNE du gain net moyen : metrique-SEUIL, pas metrique graduee.
  * `fit_policy` part de `W=zeros, b=zeros` avec acceptation STRICTE `sc > best`. Dans toute cellule
    a corps suffisant (body_gain > metab), la politique INITIALE survit deja au plafond 300/300,
    AUCUNE candidate n'est acceptee, `|W|=0.0000` est l'INIT, et l'ablation est un no-op LITTERAL
    (classe E1).

CE QUE CE RUNNER MESURE. Sous une init NON nulle (sigma > 0), le NEUTRE des cellules a corps
suffisant est-il ROBUSTE ?

    k(sigma) = nombre de seeds (sur 12) ou l'ablation MORD (ratio intact/able > 1.3) ALORS QUE
               le corps suffit deja a survivre au plafond.

  * k ~ 0  -> marqueur SPECIFIQUE sous indifference (faux positifs <= 1/12) ; la lecture
              "ratio 1.0-1.3 = non demande" garde son sens.
  * k >= 2 -> les NEUTRE de S2-004/005/007/008 etaient ceux de sigma=0 SEULEMENT, et
              REF-DEMAND-MARKER doit publier un taux de faux positifs PAR SIGMA.

DESIGN.
  * PUR NUMPY. Aucun import de monde, aucun bail kuzu (`assert_no_world`).
  * Le MESUREUR n'est PAS re-implemente : `survive`, `_obs`, `_ablate` sont IMPORTES du probe.
    Seul l'ENTRAINEUR est copie (`fit_policy_sigma`) : l'init EST la variable independante.
  * ANCRE : a sigma=0 le RNG d'init (separe) n'est pas consomme -> trajectoire BIT-IDENTIQUE a
    `fit_policy`. VERIFIE par `np.array_equal` dans les DEUX cellules, dont c1-P ou le hill-climb
    accepte reellement (n_accepted>0) -- tester l'identite uniquement la ou la boucle n'accepte
    RIEN ne prouve rien sur la boucle.
  * PLANCHER MESURE, pas devine : la politique "privee de X seulement" = corps seul (W=0, b=e_0),
    passee dans le MEME mesureur sur les MEMES RandomState, AVANT tout entrainement.
  * Unite de replication = le SEED (12). La DV d'un seed = MEDIANE de ses 24 vies par bras ;
    `ablation_verdict` recoit 12 paires, jamais 288 vies.
  * GATE D'ADMISSIBILITE : le run REFUSE de conclure si l'ancre ou le controle positif echouent.

------------------------------------------------------------------------------------------------
QUATRE DEFAUTS DE LA VERSION PRECEDENTE DE CE RUNNER, MESURES ET CORRIGES ICI.

(1) LE BARREAU DV ETAIT `zero`, ET `zero` PRODUIT DES FAUX NEGATIFS. Obs mise a zero -> la
    politique devient CONSTANTE = argmax(b). Si ce defaut tombe sur l'action CORPS, le sujet
    survit au plafond et le barreau lit ratio=1.00 -- MEME QUAND la politique lit massivement
    l'obs. Mesure sur les 60 points : 5 seeds ou `permuted` effondre 2.9x a 7.1x pendant que
    `zero` annonce 1.00. Le DV est desormais `permuted` (obs REELLE d'un autre tick : meme
    distribution, information detruite), et `b_argmax` est enregistre pour NOMMER la cause.
(2) LA CLE DE CACHE OMETTAIT iters/episodes/n_eval. Un `--smoke --iters 50` (qui ecrit en
    `force=True`) empoisonnait silencieusement le point seed=0 d'un `--run` a iters=300. La cle
    porte desormais les parametres, ET `load_or_run` REFUSE un record dont les parametres
    different au lieu de le servir.
(3) AUCUN GATE SUR LE CONTROLE POSITIF. La table s'imprimait et le process rendait 0 meme si
    c1-P ne mordait pas -- c'est-a-dire meme si l'instrument etait aveugle (E1/E2), auquel cas
    k(c1-N) est mesure sur un instrument qui ne peut rendre QUE 0. Le gate est explicite,
    pre-enregistre (`GATE_*`), et le process rend 2 en NO-GO.
(4) LA PROJECTION DE COUT extrapolait UNE cellule a toutes en s'annoncant "borne haute".
    Corrige : elle dit ce qu'elle est, et `--smoke --all-cells` chronometre CHAQUE cellule.

CE QUE SIGMA BALAYE VRAIMENT (defaut du DESIGN, pas du code -- epingle par un cas de calibration).
L'action est `argmax(W @ o + b)`, invariante par multiplication par un scalaire POSITIF : a seed
fixe, sigma=0.1, 0.3 et 1.0 donnent la MEME politique initiale, donc le MEME init_score (mesure :
67.4 pour le seed 1 aux trois sigmas). Sigma balaye le RAPPORT entre l'echelle de l'init et le pas
du hill-climb (step=0.5), i.e. la facilite avec laquelle la recherche EFFACE l'init. Seule
discontinuite reelle : sigma=0 vs sigma>0. Lire k(0.1) vs k(1.0) comme une dose-reponse en "force
de lecture" serait FAUX.

CE QUE LA CELLULE c1-N NE PEUT PAS RENDRE. En corps suffisant le plancher MESURE (corps seul) vaut
300 = le PLAFOND. `ablation_verdict` y est structurellement incapable d'emettre `X_DECOY` : tout
ratio ~1 devient (a juste titre) `INCONCLUSIVE_DEGENERATE`. Le "NEUTRE" de S2-004 n'est donc pas
seulement l'artefact de sigma=0 : il est ILLISIBLE a tout sigma avec ce mesureur-SEUIL. D'ou k,
compte PAR SEED et HORS du verdict : une morsure n'exige que la DESCENTE du bras ablate, ce que la
saturation par le haut n'empeche pas.

Usage :
    python s2_fallback_rate_probe.py --smoke [--all-cells]   # chronometrage + projection
    python s2_fallback_rate_probe.py --anchor                # sigma=0, 12 seeds
    python s2_fallback_rate_probe.py --run                   # plan complet, resumable, gate
    python s2_fallback_rate_probe.py --aggregate-only        # relit le JSON, ne simule rien
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time

import numpy as np

_DEFAULT_ROOT = r"c:/Users/robla/VScode_Project/AGAGI"
_ROOT = os.environ.get("AGAGI_ROOT", _DEFAULT_ROOT)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# LE MESUREUR EST IMPORTE, JAMAIS RE-IMPLEMENTE.
from tools.cognitive_demand_world_probe import survive, _obs, _ablate      # noqa: E402
from tools.cognitive_demand_world_probe import PLANCHER_AVEUGLE            # noqa: E402
from tools.demand_marker import ablation_verdict                           # noqa: E402

# ---------------------------------------------------------------------------- constantes du design
SCHEMA = 2                # bump = les records d'un autre protocole ne sont plus servis
BODY_ACTION = 0
MODES = ("true", "permuted", "noise", "zero")
ABL_MODES = ("permuted", "noise", "zero")

# DV = `permuted` : obs REELLE d'un AUTRE tick. Meme distribution marginale, information detruite.
# C'est le seul barreau qui isole l'INFORMATION ; `zero` detruit aussi la VARIABILITE de l'entree et
# fait tomber la politique sur une constante -> faux negatifs mesures (cf. defaut (1) en tete).
DV_MODE = "permuted"
CRN_EXACT_MODE = "zero"   # seul barreau a CRN exact -- invariant verifie par assert_crn_exactness

BITE = 1.3                # "mord" = ratio > 1.3 (borne haute du leurre dans demand_marker)
BITE_STRICT = 1.5         # seuil `collapse_factor` de demand_marker -- rapporte en parallele
N_EVAL = 24               # vies par bras et par seed
N_SEEDS = 12              # unite de replication = le SEED

# ---- GATE D'ADMISSIBILITE, PRE-ENREGISTRE (les DEUX issues doivent etre atteignables) ----------
GATE_POS_CELL, GATE_POS_SIGMA = "c1-P", 0.3
GATE_POS_MIN_K = 10       # le CONTROLE POSITIF doit mordre sur >= 10 seeds / 12
GATE_ANCHOR_CELL, GATE_ANCHOR_SIGMA = "c1-N", 0.0
GATE_ANCHOR_MAX_K = 0     # l'ANCRE (sigma=0) doit mordre sur 0 seed

CELLS = {
    # c1-N : corps SUFFISANT (body_gain > metab) -> la cellule NEUTRE de S2-004. EXPERIMENTALE.
    "c1-N": {"body_gain": 1.2, "cog_gain": 2.0, "currency": "energy", "K": 5, "ticks": 300,
             "sigmas": [0.0, 0.1, 0.3, 1.0],
             "role": "corps SUFFISANT -- cellule testee (neutre attendu)"},
    # c1-P : corps INSUFFISANT -> CONTROLE POSITIF. Si l'ablation n'y mord pas, l'instrument est
    # aveugle et AUCUNE lecture de c1-N n'est recevable (E1/E2). Gate dur, pas commentaire.
    "c1-P": {"body_gain": 0.5, "cog_gain": 2.0, "currency": "energy", "K": 5, "ticks": 300,
             "sigmas": [0.3],
             "role": "corps INSUFFISANT -- CONTROLE POSITIF (l'ablation DOIT mordre)"},
}


# ------------------------------------------------------------------------------------- garde-fous
def assert_no_world():
    """Le runner ne doit JAMAIS importer le monde ni prendre un bail exclusif (kuzu).

    ⚠️ CORRIGE le 2026-09-07 : la premiere version inspectait `sys.modules` -- l'etat GLOBAL du
    processus. Elle a mordu en integration sur `tools.jobs`, charge par le `conftest.py` du depot
    (la garde de bail, E10 occ. 7), c'est-a-dire par QUELQU'UN D'AUTRE. Une garde qui accuse le
    runner de ce qu'un tiers a importe mesure la mauvaise chose : elle rend un verdict sur le
    processus, pas sur le sujet. La verification est donc STATIQUE -- les imports du fichier
    lui-meme, seule chose dont le runner reponde -- et elle reste vraie quel que soit l'appelant."""
    import ast
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    interdits = ("kuzu", "core.world", "tools.jobs", "src.worlds", "src.environments")
    vus = []
    for node in ast.walk(ast.parse(src)):
        noms = []
        if isinstance(node, ast.Import):
            noms = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            noms = [node.module]
        for n in noms:
            if any(n == i or n.startswith(i + ".") for i in interdits):
                vus.append(n)
    if vus:
        raise AssertionError("le runner S6 IMPORTE des modules interdits : %s" % sorted(set(vus)))
    return True


def assert_intervention_perturbs_input(K=5, seed=0):
    """Question 1 du pre-vol : l'ablation perturbe-t-elle bien l'ENTREE (pas la sortie) ?

    ATTENTION A CE QUE CE CONTROLE NE DIT PAS. Il etablit que `_ablate` modifie le vecteur d'obs.
    Il n'etablit PAS que la politique LIT cette obs. Or `demand_marker.intervention_verified`
    demande exactement la premiere chose pour debloquer un nul sur bras identiques -- alors que le
    cas que sa propre docstring nomme comme "a bloquer" (S2-004 : politique constante, W gele)
    SATISFAIT la premiere et pas la seconde. On ne passe donc JAMAIS `intervention_verified=True`
    ici. (Defaut de CONTRAT de `demand_marker`, consigne dans les notes.)"""
    rng = np.random.RandomState(seed)
    o = _obs(2, K, rng)
    out = {}
    for mode in ABL_MODES:
        alt = _ablate(o.copy(), mode, K, np.random.RandomState(seed + 1))
        if np.allclose(alt, o):
            raise AssertionError("le barreau %r ne perturbe PAS l'entree" % mode)
        out[mode] = True
    if not np.allclose(_ablate(o.copy(), "true", K, np.random.RandomState(seed + 1)), o):
        raise AssertionError("le barreau 'true' ALTERE l'entree -- specificite cassee")
    return out


def assert_crn_exactness():
    """QUEL barreau est-il APPARIE EXACTEMENT ? On le MESURE, on ne le suppose pas.

    Methode : la politique CORPS ignore l'obs, donc sa duree de vie est la MEME sous tous les
    barreaux ; toute difference d'ETAT du RandomState apres la vie est alors PUREMENT la
    consommation de tirages par l'ablation. Resultat mesure :
        zero     -> etat IDENTIQUE  : CRN EXACT (l'ablation ne tire rien).
        permuted -> etat DIFFERENT  : `_obs(1+rng.randint(K-1), K, rng)` consomme 1 randint + K
                    randn sur LE MEME rng que le monde -> le flux decale ; les vies comparees
                    partagent la graine de depart, pas le monde tick par tick.
        noise    -> etat DIFFERENT  : `rng.randn(K)`.
    Consequence ASSUMEE : le DV (`permuted`) est apparie AU SEED, pas a la vie. Effet mesure de ce
    decalage : sur 5 seeds x 3 jeux de 24 graines DISJOINTS, la decision mord / mord-pas n'a JAMAIS
    bascule (ratios stables a +-0.6, seuil 1.3, effets de 1.7x a 7.7x). L'invariant DUR verifie ici
    est que `zero` reste exact : s'il cassait, le mesureur aurait change sous nos pieds."""
    W, b = body_only_policy(5)
    out, ref = {}, None
    for mode in MODES:
        rng = np.random.RandomState(12345)
        survive(W, b, mode, 1.2, 2.0, "energy", 5, rng, 300)
        st = rng.get_state()
        key = (st[1].tobytes(), st[2])
        if mode == "true":
            ref = key
        else:
            out[mode] = bool(key == ref)
    if not out[CRN_EXACT_MODE]:
        raise AssertionError("le barreau %r n'est PLUS a CRN exact : le mesureur a change"
                             % CRN_EXACT_MODE)
    return out


# --------------------------------------------------------------------------------- l'entraineur
def body_only_policy(K):
    """La politique "privee de X seulement" : elle joue l'action CORPS quoi qu'elle percoive.

    W = 0 -> l'obs n'entre pas dans la decision ; b = e_0 -> argmax = BODY_ACTION a chaque tick.
    C'est aussi la MEILLEURE politique aveugle du regime : sans information, l'esperance de gain
    d'une action fixe vaut max(body_gain, cog_gain/(K-1)) et le corps la realise. Le plancher se
    MESURE dans le meme mesureur ; il ne se devine pas, et il ne s'IMPORTE pas."""
    W = np.zeros((K, K))
    b = np.zeros(K)
    b[BODY_ACTION] = 1.0
    return W, b


def fit_policy_sigma(sigma, body_gain, cog_gain, currency, K, seed,
                     iters=300, episodes=5, ticks=300):
    """`fit_policy` du probe, a UNE difference : l'init (W0, b0) est tiree a l'echelle sigma.

    Le RNG d'init est SEPARE (`RandomState(seed+999)`) et n'est TIRE QUE si sigma>0. Consequence
    voulue : a sigma=0 le RNG principal `RandomState(seed)` n'a rien consomme de plus, la suite de
    candidates est la meme, la trajectoire est BIT-IDENTIQUE a l'originale -> c'est l'ANCRE.

    Renvoie (W, b, n_accepted, best_score, init_score). `n_accepted` NOMME la cause : a sigma=0 en
    corps suffisant il vaut 0, donc |W|=0.0000 est l'INIT et jamais un poids appris."""
    rng = np.random.RandomState(seed)
    if sigma > 0:
        rng_init = np.random.RandomState(seed + 999)
        W = sigma * rng_init.randn(K, K)
        b = sigma * rng_init.randn(K)
    else:
        W = np.zeros((K, K))
        b = np.zeros(K)

    def score(W, b):
        return float(np.mean([survive(W, b, "true", body_gain, cog_gain, currency, K,
                                      np.random.RandomState(seed + 100 + e), ticks)
                              for e in range(episodes)]))

    best, step = score(W, b), 0.5
    init_score, n_accepted = best, 0
    for i in range(iters):
        Wc, bc = W + step * rng.randn(K, K), b + step * rng.randn(K)
        sc = score(Wc, bc)
        if sc > best:
            W, b, best = Wc, bc, sc
            n_accepted += 1
        elif i % 50 == 49:
            step *= 0.85
    return W, b, n_accepted, float(best), float(init_score)


# ------------------------------------------------------------------------------------ la mesure
def life_seeds(seed, n_eval=N_EVAL):
    """Les graines de vie -- PARTAGEES par tous les bras (CRN par vie, exact pour `zero`)."""
    ev = np.random.RandomState(seed + 777)
    return [int(ev.randint(1 << 30)) for _ in range(n_eval)]


def run_arms(W, b, cell, seed, n_eval=N_EVAL, modes=MODES):
    """Les MEMES RandomState pour chaque bras : la difference entre bras est l'ABLATION, pas l'alea
    (exactement pour `zero` ; a la graine de depart pres pour `permuted`/`noise` -- ce que
    `assert_crn_exactness` MESURE au lieu de l'affirmer)."""
    seeds = life_seeds(seed, n_eval)
    return {m: [int(survive(W, b, m, cell["body_gain"], cell["cog_gain"], cell["currency"],
                            cell["K"], np.random.RandomState(ls), cell["ticks"]))
                for ls in seeds]
            for m in modes}


def measured_floor(cell, seed, n_eval=N_EVAL):
    """Plancher MESURE : la politique corps-seul, meme mesureur, memes RandomState, AVANT training.
    Renvoie (mediane, les 24 vies) -- les vies servent a PROUVER que le plancher est deterministe,
    pas a l'affirmer."""
    W0, b0 = body_only_policy(cell["K"])
    lives = [int(survive(W0, b0, "true", cell["body_gain"], cell["cog_gain"], cell["currency"],
                         cell["K"], np.random.RandomState(ls), cell["ticks"]))
             for ls in life_seeds(seed, n_eval)]
    return float(statistics.median(lives)), lives


def blind_floor_scan(cell, seed, n_eval=N_EVAL):
    """Le plancher declare est-il vraiment la MEILLEURE politique aveugle ? On SCANNE.

    DEFAUT MESURE DU PLANCHER DU DEPOT (petit, mais reel -- consigne en passant). `PLANCHER_AVEUGLE
    = 30.0` est la forme close de la politique CORPS (a=0), deterministe. Or en corps INSUFFISANT
    une action cognitive CONSTANTE a la MEME esperance de gain (cog_gain/(K-1) = 2.0/4 = 0.5 =
    body_gain) mais une VARIANCE non nulle : la mediane du temps d'atteinte d'une marche bruitee
    est legerement au-dessus de celle de la derive deterministe. Mesure (24 vies, seed 0) :
        corps a=0 -> 30 EXACT [30..30]   |   a=1 -> 31   a=2 -> 26   a=3 -> 29   a=4 -> 31
    La MEILLEURE aveugle vaut donc 31, soit +1 tick (+3 %) au-dessus du plancher declare : le
    plancher du depot SOUS-ESTIME, ce qui rend la garde de degenerescence marginalement MOINS
    conservatrice que ce qu'elle annonce. En corps SUFFISANT l'ecart est nul (le corps EST la
    meilleure aveugle, 300 vs 26-31).

    IMMATERIEL ICI, et on le dit plutot que de le corriger en douce : dans les deux cellules le
    bras intact vaut 300, donc `med_i <= floor` se decide pareil a 30 ou a 31. `measured_floor`
    continue de rendre la politique CORPS -- la meme quantite que le probe d'origine passe en
    `floor=` -- pour que la comparaison avec S2-004 reste a protocole egal."""
    import numpy as _np
    out = {}
    for a in range(cell["K"]):
        W = _np.zeros((cell["K"], cell["K"]))
        b = _np.zeros(cell["K"])
        b[a] = 1.0
        lives = [int(survive(W, b, "true", cell["body_gain"], cell["cog_gain"], cell["currency"],
                             cell["K"], np.random.RandomState(ls), cell["ticks"]))
                 for ls in life_seeds(seed, n_eval)]
        out[a] = float(statistics.median(lives))
    return out


def bites(ratio, thresh=BITE):
    """"L'ablation MORD" -- decision PAR SEED, hors ablation_verdict (qui agrege les 12 seeds)."""
    return bool(ratio > thresh)


def win_frac(intact, ablated):
    """Fraction des vies APPARIEES ou intact > ablate. Exact pour `zero` (CRN exact) ; apparie a la
    graine de depart seulement pour `permuted`/`noise`. Gratuit : lu dans les vies deja stockees."""
    n = min(len(intact), len(ablated))
    if n == 0:
        return None
    return float(sum(1 for i in range(n) if intact[i] > ablated[i]) / n)


def original_ladder_verdict(rec):
    """LE VERDICT QUE LE PROBE D'ORIGINE AURAIT PUBLIE sur ces memes donnees.

    Reproduit `cognitive_demand_world_probe.ladder` a l'identique, y compris ses deux choix qui ne
    sont PAS les notres, pour que la comparaison avec S2-004 soit directe et non une re-lecture :
      * n = les 24 VIES (pseudo-replication : l'unite de replication du depot est le seed) ;
      * `floor=PLANCHER_AVEUGLE` UNIQUEMENT si body_gain < 1.0 -- donc floor=None dans la cellule a
        corps SUFFISANT, ou la garde de degenerescence ne peut alors se declencher que par
        l'identite des bras.
    C'est cette combinaison qui fait basculer la cellule "corps SUFFISANT + energie" de
    SURVIVAL_NEUTRAL (sigma=0) a SURVIVAL_SENSITIVE (sigma>0)."""
    floor = PLANCHER_AVEUGLE if rec["body_gain"] < 1.0 else None
    ticks = float(rec["ticks"])
    intact = rec["lives"]["true"]
    vs = {m: ablation_verdict(intact, rec["lives"][m], floor=floor, ceiling=ticks)
          for m in ABL_MODES}
    rungs = {m: v["ratio"] for m, v in vs.items()}
    if any(v.get("degenerate") for v in vs.values()):
        return "INDETERMINE_DEGENERATE"
    if any(r >= 1.5 for r in rungs.values()):
        return "SURVIVAL_SENSITIVE"
    if all(r <= 1.3 for r in rungs.values()):
        return "SURVIVAL_NEUTRAL"
    return "MIXED"


def run_seed(cell_name, sigma, seed, iters=300, episodes=5, n_eval=N_EVAL):
    """Un point du plan : plancher mesure -> entrainement -> 4 bras en CRN -> DV medianes."""
    cell = CELLS[cell_name]
    t0 = time.time()
    floor, floor_lives = measured_floor(cell, seed, n_eval)
    W, b, n_accepted, best, init_score = fit_policy_sigma(
        sigma, cell["body_gain"], cell["cog_gain"], cell["currency"], cell["K"], seed,
        iters=iters, episodes=episodes, ticks=cell["ticks"])
    lives = run_arms(W, b, cell, seed, n_eval)
    dv = {m: float(statistics.median(v)) for m, v in lives.items()}
    ratios = {m: float(dv["true"] / max(dv[m], 1e-9)) for m in ABL_MODES}
    rec = {
        "schema": SCHEMA,
        "cell": cell_name, "sigma": float(sigma), "seed": int(seed),
        "body_gain": cell["body_gain"], "cog_gain": cell["cog_gain"],
        "currency": cell["currency"], "K": cell["K"], "ticks": cell["ticks"],
        "iters": iters, "episodes": episodes, "n_eval": n_eval,
        "floor": floor, "floor_lives": floor_lives,
        "floor_deterministic": bool(len(set(floor_lives)) == 1),
        "n_accepted": int(n_accepted), "best_score": best, "init_score": init_score,
        "obs_weight": float(np.mean(np.abs(W))),
        # b_argmax = l'action jouee quand l'obs est mise a ZERO. NOMME la cause des faux negatifs
        # du barreau `zero` : si c'est l'action CORPS, le sujet survit au plafond meme s'il lit.
        "b_argmax": int(np.argmax(b)),
        "lives": lives, "dv": dv, "ratios": ratios,
        "bites": {m: bites(r) for m, r in ratios.items()},
        "bites_strict": {m: bool(r >= BITE_STRICT) for m, r in ratios.items()},
        "win_frac": {m: win_frac(lives["true"], lives[m]) for m in ABL_MODES},
        "arms_identical": {m: bool(lives["true"] == lives[m]) for m in ABL_MODES},
        "secs": float(time.time() - t0),
    }
    rec["original_ladder_verdict"] = original_ladder_verdict(rec)
    return rec


# ------------------------------------------------------------------ agregation (couche separee)
def _majority(verds):
    """Majorite DETERMINISTE. Voir la note dans `aggregate` : la majorite du probe d'origine
    depend de PYTHONHASHSEED sur une egalite. Ici l'ordre est total (compte decroissant, puis
    alphabetique), donc reproductible d'un process a l'autre."""
    if not verds or not all(verds):
        return None
    return sorted(set(verds), key=lambda v: (-verds.count(v), v))[0]


def _is_tie(verds):
    """Y a-t-il EGALITE en tete ? Une majorite tiree d'une egalite n'est pas une majorite -- on la
    signale au lieu de la publier telle quelle."""
    if not verds or not all(verds):
        return None
    counts = sorted((verds.count(v) for v in set(verds)), reverse=True)
    return bool(len(counts) > 1 and counts[0] == counts[1])


def aggregate(records, expect_n=None):
    """Couche d'AGREGATION, testable par INJECTION : ne simule rien, ne prend que des records.

    - unite de replication = le seed ; `ablation_verdict` recoit len(records) paires de MEDIANES.
    - `floor=` = mediane des planchers MESURES ; `ceiling=` = le plafond de ticks.
    - k est compte PAR SEED, HORS `ablation_verdict`.
    - `intervention_verified` reste False : cf. `assert_intervention_perturbs_input`.
    - une entree VIDE rend une ERREUR explicite, jamais un verdict de fond (biais du depot vers le
      negatif fabrique) ; une entree PARTIELLE est servie mais DRAPEAUTEE (`partial`)."""
    if not records:
        return {"error": "aucun record -- rien a agreger (PAS de verdict de fond sur entree vide)"}
    cell, sigma = records[0]["cell"], records[0]["sigma"]
    if any(r["cell"] != cell or r["sigma"] != sigma for r in records):
        raise ValueError("aggregate() attend des records d'UNE seule (cellule, sigma)")
    if len({(r["iters"], r["episodes"], r["n_eval"]) for r in records}) > 1:
        raise ValueError("aggregate() melange des records a PARAMETRES differents")
    ticks = float(records[0]["ticks"])
    floor = float(statistics.median(r["floor"] for r in records))
    intact = [r["dv"]["true"] for r in records]
    n = len(records)
    verds = [r.get("original_ladder_verdict") for r in records]
    out = {"cell": cell, "sigma": sigma, "n_seeds": n, "floor_measured": floor, "ceiling": ticks,
           "partial": bool(expect_n is not None and n != expect_n), "expect_n": expect_n,
           "dv_mode": DV_MODE,
           "median_intact": float(statistics.median(intact)),
           "median_obs_weight": float(statistics.median(r["obs_weight"] for r in records)),
           "median_n_accepted": float(statistics.median(r["n_accepted"] for r in records)),
           "n_seeds_n_accepted_zero": sum(1 for r in records if r["n_accepted"] == 0),
           "n_seeds_arms_identical": sum(1 for r in records if r["arms_identical"][DV_MODE]),
           "n_seeds_body_default": sum(1 for r in records if r["b_argmax"] == BODY_ACTION),
           "secs_total": float(sum(r.get("secs", 0.0) for r in records)),
           # verdict du PROTOCOLE D'ORIGINE (majorite, n=24 VIES) : ce que S2-004 aurait publie.
           # /!\ La majorite du probe d'origine s'ecrit `max(set(verdicts), key=verdicts.count)`
           # (cognitive_demand_world_probe.py:156). Sur une EGALITE, `set` decide -- et l'ordre
           # d'iteration d'un set de CHAINES depend de PYTHONHASHSEED : le verdict PUBLIE de la
           # cellule n'est alors PAS REPRODUCTIBLE. Mesure : sur l'egalite 6/6 que rendent nos
           # sigma=0.3 et sigma=1.0, 8 valeurs de PYTHONHASHSEED donnent 5 fois
           # INDETERMINE_DEGENERATE et 3 fois SURVIVAL_SENSITIVE. On ne reproduit donc PAS ce
           # tirage : on trie (deterministe) ET on DRAPEAUTE l'egalite au lieu de trancher en
           # silence -- c'est la seule facon de ne pas publier un verdict qui depend du process.
           "original_ladder_majority": _majority(verds),
           "original_ladder_tie": _is_tie(verds),
           "original_ladder_counts": {v: verds.count(v) for v in set(verds) if v},
           "verdicts": {}, "k": {}, "k_strict": {}, "median_ratio": {}, "median_win_frac": {}}
    for m in ABL_MODES:
        abl = [r["dv"][m] for r in records]
        out["verdicts"][m] = ablation_verdict(intact, abl, floor=floor, ceiling=ticks)
        out["k"][m] = sum(1 for r in records if r["bites"][m])
        out["k_strict"][m] = sum(1 for r in records if r["bites_strict"][m])
        out["median_ratio"][m] = float(statistics.median(r["ratios"][m] for r in records))
        wf = [r["win_frac"][m] for r in records if r["win_frac"][m] is not None]
        out["median_win_frac"][m] = float(statistics.median(wf)) if wf else None
    out["k_dv"] = out["k"][DV_MODE]
    out["k_any"] = sum(1 for r in records if any(r["bites"].values()))
    return out


def admissibility(aggs):
    """GATE : les DEUX issues sont-elles atteignables ? Pre-enregistre, pas post-hoc.

    Sans ce gate, k(c1-N) peut etre mesure sur un instrument qui ne peut rendre QUE 0 (E1/E2) et la
    table s'imprime quand meme. Renvoie (go: bool, lignes: list[str])."""
    idx = {(a["cell"], a["sigma"]): a for a in aggs if "error" not in a}
    lines, go = [], True
    pos = idx.get((GATE_POS_CELL, GATE_POS_SIGMA))
    if pos is None:
        lines.append("  [NO-GO] CONTROLE POSITIF %s sigma=%g ABSENT du plan execute"
                     % (GATE_POS_CELL, GATE_POS_SIGMA))
        go = False
    else:
        ok = pos["k_dv"] >= GATE_POS_MIN_K and not pos["partial"]
        go = go and ok
        lines.append("  [%s] CONTROLE POSITIF %s sigma=%g : k(%s)=%d/%d (exige >=%d) ratio=%.2f"
                     % ("GO " if ok else "NO-GO", pos["cell"], pos["sigma"], DV_MODE,
                        pos["k_dv"], pos["n_seeds"], GATE_POS_MIN_K,
                        pos["verdicts"][DV_MODE]["ratio"]))
    anc = idx.get((GATE_ANCHOR_CELL, GATE_ANCHOR_SIGMA))
    if anc is None:
        lines.append("  [NO-GO] ANCRE %s sigma=%g ABSENTE du plan execute"
                     % (GATE_ANCHOR_CELL, GATE_ANCHOR_SIGMA))
        go = False
    else:
        ok = (anc["k_dv"] <= GATE_ANCHOR_MAX_K and anc["median_obs_weight"] == 0.0
              and anc["n_seeds_n_accepted_zero"] == anc["n_seeds"] and not anc["partial"])
        go = go and ok
        lines.append("  [%s] ANCRE %s sigma=0 : k=%d (exige <=%d) |W|=%.4f n_accepted=0 sur %d/%d"
                     % ("GO " if ok else "NO-GO", anc["cell"], anc["k_dv"], GATE_ANCHOR_MAX_K,
                        anc["median_obs_weight"], anc["n_seeds_n_accepted_zero"], anc["n_seeds"]))
    lines.append("  => %s" % ("GO : l'instrument produit LES DEUX issues, k(c1-N) est lisible."
                              if go else
                              "NO-GO : instrument non calibre -- AUCUNE lecture de c1-N recevable."))
    return go, lines


# ---------------------------------------------------------------------------------- persistance
def record_path(outdir, cell, sigma, seed, iters=300, episodes=5, n_eval=N_EVAL):
    """La cle porte les PARAMETRES : un `--smoke --iters 50` ne peut plus empoisonner un `--run`."""
    return os.path.join(outdir, "%s__sigma%g__it%d_ep%d_ev%d__seed%d.json"
                        % (cell, sigma, iters, episodes, n_eval, seed))


def load_or_run(outdir, cell, sigma, seed, iters=300, episodes=5, n_eval=N_EVAL, force=False):
    """Resumable : un point deja calcule n'est JAMAIS recalcule -- ET jamais servi si ses parametres
    ou son schema different de ceux demandes (on LEVE plutot que de servir un resultat obtenu sous
    un AUTRE protocole)."""
    os.makedirs(outdir, exist_ok=True)
    p = record_path(outdir, cell, sigma, seed, iters, episodes, n_eval)
    if os.path.exists(p) and not force:
        with open(p, "r", encoding="utf-8") as fh:
            rec = json.load(fh)
        got = (rec.get("schema"), rec.get("cell"), rec.get("sigma"), rec.get("seed"),
               rec.get("iters"), rec.get("episodes"), rec.get("n_eval"))
        want = (SCHEMA, cell, float(sigma), int(seed), iters, episodes, n_eval)
        if got != want:
            raise ValueError("record en cache INCOMPATIBLE (%s)\n  attendu %s\n  trouve  %s"
                             % (p, want, got))
        rec["_from_cache"] = True
        return rec
    rec = run_seed(cell, sigma, seed, iters=iters, episodes=episodes, n_eval=n_eval)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(rec, fh)
    rec["_from_cache"] = False
    return rec


def plan(cells=None, seeds=N_SEEDS):
    cells = cells or list(CELLS)
    return [(c, s, seed) for c in cells for s in CELLS[c]["sigmas"] for seed in range(seeds)]


# ---------------------------------------------------------------------------------------- CLI
def _fmt_agg(a):
    """DEUX ratios, et ils ne sont PAS le meme nombre -- les afficher sous un seul intitule "ratio"
    a failli passer. `med(r)` = MEDIANE DES RATIOS par seed (ce qui fonde k) ; `r(med)` = RATIO DES
    MEDIANES, celui que `ablation_verdict` calcule et sur lequel il tranche. Le verdict de cellule
    est un seuil-couteau a 50 % de seeds mordants ; c'est k qui est la grandeur robuste ici."""
    if "error" in a:
        return "  (agregat en erreur : %s)" % a["error"]
    v = a["verdicts"][DV_MODE]
    return ("%-5s s=%-4g n=%2d%s | k(%s)=%2d/%d [strict %2d] k_any=%2d | med(r)=%5.2f r(med)=%5.2f "
            "| |W|=%.3f n_acc=%.0f floor=%3.0f | orig=%-22s | %s%s" %
            (a["cell"], a["sigma"], a["n_seeds"], "*" if a["partial"] else " ", DV_MODE,
             a["k_dv"], a["n_seeds"], a["k_strict"][DV_MODE], a["k_any"],
             a["median_ratio"][DV_MODE], v["ratio"], a["median_obs_weight"],
             a["median_n_accepted"], a["floor_measured"], a["original_ladder_majority"],
             v["verdict"], " [CENSURE]" if v["censored"] else ""))


def _print_table(aggs, crn):
    ordered = sorted(aggs, key=lambda a: (a.get("cell", ""), a.get("sigma", 0)))
    print("\n=== S6 : k(sigma) = seeds ou l'ablation MORD (ratio > %.1f), DV = barreau %r ==="
          % (BITE, DV_MODE))
    print("    CRN exact par barreau : %s  (seul %r est apparie VIE par VIE)"
          % (crn, CRN_EXACT_MODE))
    for a in ordered:
        print(_fmt_agg(a))
    print("\n  k par BARREAU (le choix du DV est une DECISION -- on l'expose au lieu de la cacher) :")
    for a in ordered:
        if "error" in a:
            continue
        print("    %-5s s=%-4g  " % (a["cell"], a["sigma"])
              + "  ".join("%-8s k=%2d med(r)=%5.2f win=%s"
                          % (m, a["k"][m], a["median_ratio"][m],
                             ("%.2f" % a["median_win_frac"][m])
                             if a["median_win_frac"][m] is not None else "n/a")
                          for m in ABL_MODES))
    print("\n  verdict du PROTOCOLE D'ORIGINE (ladder, n=24 VIES) -- ce que S2-004 aurait publie "
          "sur CES memes donnees.")
    print("  Lire la colonne SENSIBLE/n (nombre de SEEDS ou le protocole d'origine conclut "
          "SURVIVAL_SENSITIVE) : la majorite,")
    print("  elle, est une EGALITE des que ce compte vaut n/2 -- et la majorite du probe "
          "d'origine depend alors de PYTHONHASHSEED.")
    for a in ordered:
        if "error" in a:
            continue
        c = a["original_ladder_counts"]
        print("    %-5s s=%-4g  SENSIBLE %2d/%-2d | majorite=%-24s%s | %s"
              % (a["cell"], a["sigma"], c.get("SURVIVAL_SENSITIVE", 0), a["n_seeds"],
                 a["original_ladder_majority"],
                 "  <<< EGALITE : majorite NON REPRODUCTIBLE chez l'original"
                 if a["original_ladder_tie"] else "", c))


def main(argv=None):
    ap = argparse.ArgumentParser(description="S6 -- taux de faux positifs du marqueur sous sigma>0")
    ap.add_argument("--outdir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                     "runs"))
    ap.add_argument("--cells", nargs="*", default=None)
    ap.add_argument("--sigmas", nargs="*", type=float, default=None)
    ap.add_argument("--seeds", type=int, default=N_SEEDS)
    ap.add_argument("--iters", type=int, default=300)
    ap.add_argument("--episodes", type=int, default=5)
    ap.add_argument("--n-eval", type=int, default=N_EVAL)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="1 seed chronometre + projection du cout")
    ap.add_argument("--all-cells", action="store_true", help="--smoke : chronometrer CHAQUE cellule")
    ap.add_argument("--anchor", action="store_true", help="sigma=0 sur c1-N, 12 seeds")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--aggregate-only", action="store_true")
    args = ap.parse_args(argv)

    assert_no_world()
    assert_intervention_perturbs_input()
    crn = assert_crn_exactness()

    if args.smoke:
        pts = ([(c, s) for c in CELLS for s in CELLS[c]["sigmas"]] if args.all_cells
               else [((args.cells or ["c1-N"])[0], (args.sigmas or [0.3])[0])])
        per = []
        for cell, sigma in pts:
            t0 = time.time()
            rec = load_or_run(args.outdir, cell, sigma, 0, iters=args.iters,
                              episodes=args.episodes, n_eval=args.n_eval, force=True)
            dt = time.time() - t0
            per.append((cell, sigma, dt))
            print("SMOKE %-5s sigma=%-4g seed=0 : %6.2f s | floor=%5.1f init=%5.1f best=%5.1f "
                  "n_acc=%2d |W|=%.4f b_argmax=%d"
                  % (cell, sigma, dt, rec["floor"], rec["init_score"], rec["best_score"],
                     rec["n_accepted"], rec["obs_weight"], rec["b_argmax"]))
            print("   medianes : " + "  ".join("%s=%.1f" % (m, rec["dv"][m]) for m in MODES)
                  + " | ratios : " + "  ".join("%s=%.2f" % (m, rec["ratios"][m])
                                               for m in ABL_MODES))
        # Une extrapolation d'UNE cellule aux autres n'est NI une borne haute NI une borne basse :
        # le cout/seed depend de la cellule (une vie qui meurt tot coute moins qu'une vie au
        # plafond). Avec --all-cells la projection est une SOMME DE MESURES, pas une extrapolation.
        if args.all_cells:
            total = sum(dt * args.seeds for _, _, dt in per)
            print("PROJECTION (SOMME des mesures par cellule x %d seeds) : %.0f s = %.1f min"
                  % (args.seeds, total, total / 60.0))
        else:
            n = len(plan(seeds=args.seeds))
            dt = per[0][2]
            print("PROJECTION (extrapolation de CETTE cellule aux %d points, %d seeds) : %.0f s = "
                  "%.1f min -- PAS une borne (le cout/seed varie par cellule) ; utiliser "
                  "--smoke --all-cells pour une projection par MESURE."
                  % (n, args.seeds, dt * n, dt * n / 60.0))
        return 0

    if args.anchor:
        recs = [load_or_run(args.outdir, GATE_ANCHOR_CELL, GATE_ANCHOR_SIGMA, s, iters=args.iters,
                            episodes=args.episodes, n_eval=args.n_eval, force=args.force)
                for s in range(args.seeds)]
        print("ANCRE sigma=0 sur %s (doit reproduire S2-004 : |W|=0.0000 et 300/300)"
              % GATE_ANCHOR_CELL)
        for r in recs:
            print("  seed %2d : |W|=%.4f n_accepted=%d intact=%.0f/%d %s=%.0f identiques=%s "
                  "floor=%.0f orig=%s"
                  % (r["seed"], r["obs_weight"], r["n_accepted"], r["dv"]["true"], r["ticks"],
                     DV_MODE, r["dv"][DV_MODE], r["arms_identical"][DV_MODE], r["floor"],
                     r["original_ladder_verdict"]))
        n = len(recs)
        ok_w = all(r["obs_weight"] == 0.0 for r in recs)
        ok_s = all(r["dv"]["true"] == float(r["ticks"]) for r in recs)
        ok_a = all(r["n_accepted"] == 0 for r in recs)
        ok_i = all(all(r["arms_identical"].values()) for r in recs)
        print("  |W|=0.0000 EXACT %d/%d : %s | 300/300 %d/%d : %s | n_accepted=0 %d/%d : %s | "
              "tous bras identiques : %s" % (n, n, ok_w, n, n, ok_s, n, n, ok_a, ok_i))
        return 0 if (ok_w and ok_s and ok_a and ok_i) else 1

    pts = plan(args.cells, args.seeds)
    if args.sigmas is not None:
        pts = [p for p in pts if p[1] in args.sigmas]
    by, t0 = {}, time.time()
    for i, (c, s, seed) in enumerate(pts):
        if args.aggregate_only:
            p = record_path(args.outdir, c, s, seed, args.iters, args.episodes, args.n_eval)
            if not os.path.exists(p):
                continue
            with open(p, "r", encoding="utf-8") as fh:
                rec = json.load(fh)
        else:
            rec = load_or_run(args.outdir, c, s, seed, iters=args.iters, episodes=args.episodes,
                              n_eval=args.n_eval, force=args.force)
            if not rec.get("_from_cache"):
                print("  [%3d/%3d] %-5s sigma=%-4g seed=%2d  %5.1fs  ratio_%s=%5.2f  n_acc=%d"
                      % (i + 1, len(pts), c, s, seed, rec["secs"], DV_MODE,
                         rec["ratios"][DV_MODE], rec["n_accepted"]), flush=True)
        by.setdefault((c, s), []).append(rec)

    if not by:
        # Biais du depot : une table VIDE se lit comme "rien ne mord". On LEVE au lieu de publier
        # du vide -- une entree absente n'est pas un resultat negatif.
        print("AUCUN record : rien a agreger. (Ce n'est PAS un resultat negatif.)", file=sys.stderr)
        return 3

    aggs = [aggregate(v, expect_n=args.seeds) for v in by.values()]
    _print_table(aggs, crn)
    go, lines = admissibility(aggs)
    print("\n=== GATE D'ADMISSIBILITE (pre-enregistre) ===")
    for ln in lines:
        print(ln)
    outp = os.path.join(args.outdir, "aggregate.json")
    os.makedirs(args.outdir, exist_ok=True)
    with open(outp, "w", encoding="utf-8") as fh:
        json.dump({"go": go, "dv_mode": DV_MODE, "crn_exact": crn, "aggregates": aggs}, fh, indent=1)
    print("\nagregat -> %s   (%.1f s)" % (outp, time.time() - t0))
    return 0 if go else 2


if __name__ == "__main__":
    sys.exit(main())
