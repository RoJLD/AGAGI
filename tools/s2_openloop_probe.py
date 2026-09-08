"""S2-003 — Sonde ladder : localise la compétence de SURVIE du champion au-dessus de S2-002.
S2-002 tranche "la perception est-elle causalement porteuse de la survie ?" via UNE ablation
(permutation inter-agents). Cette sonde ajoute une ÉCHELLE de sévérité within-subject : permuted
(dans-distribution, décorrélée) -> noise (hors-distribution, échelle appariée) -> zero (hors-
distribution, dégénérée). Si les 3 barreaux sont plats (decoy), la survie est SURVIVAL_NEUTRAL
(indépendante de l'obs, même nulle) ; si un barreau s'effondre, elle est SURVIVAL_SENSITIVE.

ATTENTION : ce témoin mesure la SURVIE, donc l'(in)dépendance de la survie vis-à-vis de l'obs — PAS
l'(in)dépendance COMPORTEMENTALE. SURVIVAL_NEUTRAL n'implique PAS "open-loop" : le champion peut
utiliser l'obs pour agir sans que ça change sa survie (cf. contrefactuel par-tick de chantier/
s2-ablation : ~29% des mouvements dépendent de l'obs). Pour trancher le comportement, croiser avec un
contrefactuel d'action.

N'importe PAS en modifiant s2_demand/s2_demand_ablation/demand_marker (déjà livrés, réutilisés
tels quels via le seam batch_model_cls). Ajoute deux nouvelles classes d'ablation (bruit gaussien
à échelle appariée, obs zéro) et une échelle world-agnostic au-dessus.

Usage : python tools/s2_openloop_probe.py   (env: S2OL_SEED, S2OL_K, S2OL_AGENTS, S2OL_TICKS,
S2OL_WORLDS="soup,stoneage,...").
"""
import math
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.agents.mamba_agent import MambaBatchModel
from tools.demand_marker import ablation_verdict
from tools.s2_demand import run_condition, WORLDS, load_champion_genome
from tools.s2_demand_ablation import PerceptionAblatedMamba, _floor_for


class NoiseObsMamba(MambaBatchModel):
    """Champion à génome INTACT mais perception remplacée par du bruit gaussien à échelle
    APPARIÉE (même moyenne/écart-type que l'obs réelle) : hors-distribution mais pas dégénérée.
    Tire du flux GLOBAL np.random (pairing Harness) ; ne mute jamais batch_obs."""

    def forward(self, batch_obs, env_surprise_batch=None):
        scale = float(batch_obs.std()) + 1e-9
        noise = (np.random.randn(*batch_obs.shape) * scale + float(batch_obs.mean())).astype(batch_obs.dtype)
        return super().forward(noise, env_surprise_batch)


class ZeroObsMamba(MambaBatchModel):
    """Champion à génome INTACT mais perception ZÉRO (obs dégénérée) : barreau le plus sévère
    de la ladder. Ne mute jamais batch_obs."""

    def forward(self, batch_obs, env_surprise_batch=None):
        return super().forward(np.zeros_like(batch_obs), env_surprise_batch)


N_FLOOR = 12
"""Garde-fou de PUISSANCE (nombre d'eres appariees minimum) d'`ablation_verdict`, DECLARE ici parce
que l'orchestrateur DOIT lire le meme nombre que les barreaux. Defaut expose le 2026-09-07 par
injection a dose connue, corrige le 2026-09-08 : l'agregation lisait les booleens BRUTS
`decoy`/`collapse`, qui sont vrais
quel que soit `n` -- a K=3 eres les trois barreaux rendaient `INCONCLUSIVE` (sous-puissants) et le
monde recevait quand meme SURVIVAL_NEUTRAL, c.-a-d. l'affirmation negative de fond (« la survie est
indifferente a l'obs ») que `n_floor` existe precisement pour bloquer."""


def _eras(cell, world, arm):
    """Survies PAR ERE d'un bras, ou LEVE. Une cellule SANS ere n'est pas une survie nulle OBSERVEE :
    c'est une ABSENCE de mesure. La rendre a 0.0 (`float(np.median(era)) if era else 0.0`) fabriquait
    un `intact_med` de fond ; cote ablate, un `med_a` a 0.0 fabrique pire encore -- ratio geant, donc
    `collapse`, donc SURVIVAL_SENSITIVE (« la perception PORTE la survie ») depuis RIEN.

    DEUXIEME PORTE, trouvee en REFUTATION le 2026-09-08 : une ere NON FINIE passait la garde de
    vacuite et ressortait en verdict de FOND. Mesure (sonde d'injection, K=12, 13 agents) : intact
    [40]x11 + [nan] -> `statistics.median` (celle qui calcule le RATIO) rend 40.0 et prononce
    SURVIVAL_NEUTRAL, tandis que `np.median` (celle qui PUBLIE `intact_med`) rend nan -- le nombre
    publie n'est donc meme pas la grandeur qui a agi. Pires doses : intact tout-nan -> MIXED ;
    intact +inf -> SURVIVAL_SENSITIVE, c.-a-d. le POSITIF « la perception porte la survie » fabrique
    depuis une non-mesure. Un nan/inf est une ABSENCE de mesure, exactement comme une ere manquante :
    meme traitement. (0.0 reste une survie OBSERVEE et passe : cf. le cas negatif apparie.)"""
    era = list((cell or {}).get("era_survival") or [])
    if not era:
        raise ValueError(
            f"run_openloop_ladder : le bras '{arm}' du monde '{world}' n'a rendu AUCUNE ere "
            "(era_survival vide) -- aucune mesure possible ; ne pas confondre avec une survie nulle "
            "OBSERVEE.")
    vals = [float(x) for x in era]
    mauvaises = [i for i, v in enumerate(vals) if not math.isfinite(v)]
    if mauvaises:
        raise ValueError(
            f"run_openloop_ladder : le bras '{arm}' du monde '{world}' porte {len(mauvaises)} ere(s) "
            f"NON FINIE(S) (nan/inf) aux rangs {mauvaises[:5]} -- aucune mesure possible ; ne pas "
            "confondre avec une survie nulle OBSERVEE.")
    return vals


def run_openloop_ladder(worlds=None, seed=2026, K=12, num_agents=12, max_ticks=200):
    """Pour chaque monde : champion INTACT vs 3 barreaux d'ablation croissante (permuted -> noise
    -> zero), toutes within-subject, appariées par ère (n_eras=K). Renvoie
    {world: {intact_med, permuted, noise, zero, verdict}} où chaque barreau porte le dict complet
    ablation_verdict (ratio/n/collapse/decoy/verdict) et verdict = lecture world-level (SURVIE).
    DEUX verdicts de FOND -- SURVIVAL_NEUTRAL (les 3 barreaux sont des leurres) / SURVIVAL_SENSITIVE
    (au moins un s'effondre) -- plus MIXED (ni l'un ni l'autre : au moins un barreau inverse ou en
    zone grise) ; et DEUX REFUS, qui ne sont PAS des resultats : INDETERMINE_DEGENERATE (un barreau
    illisible -- bras intact au plancher declare ou SANS amplitude, bras identiques) et
    INDETERMINE_UNDERPOWERED (moins de N_FLOOR eres appariees). NB : verdict sur la SURVIE, ne
    conclut pas sur le comportement (voir docstring module)."""
    # GARDE D'ARGUMENTS, EN TETE (2026-09-06). Orchestrateur : il n'entraine pas lui-meme mais
    # AGREGE en verdict -- une cohorte/liste de seeds vide produit une agregation VIDE que l'aval
    # lit comme une mesure (biais negatif systematique). Refus instantane, avant tout appel de run.
    if int(K) <= 0 or int(num_agents) <= 0 or int(max_ticks) <= 0:
        raise ValueError(
            f"run_openloop_ladder : argument degenere (K={K} num_agents={num_agents} max_ticks={max_ticks}) -- aucune mesure possible ; "
            "ne pas confondre avec une mesure nulle OBSERVEE.")
    # ⚠️ Corrige le 2026-09-07 (injection a dose connue) : une famille VIDE rendait `{}` SANS lever,
    # et `main()` en tirait deux affirmations de FOND (« aucun monde NEUTRE », « aucun SENSIBLE ») a
    # partir de zero mesure -- la forme (a) du biais negatif du depot, dans la sonde meme qui sert a
    # lire l'echelle d'ablation. `None` = defaut ; `[]` = erreur d'appel.
    if worlds is None:
        worlds = ["soup", "stoneage", "famine"]
    worlds = list(worlds)
    if not worlds:
        raise ValueError(
            "run_openloop_ladder : argument degenere (famille de mondes VIDE) -- aucune mesure "
            "possible ; ne pas confondre avec une mesure nulle OBSERVEE.")
    champion = load_champion_genome()
    out = {}
    for w in worlds:
        wcls = WORLDS[w]
        intact = run_condition(wcls, None, champion, seed, num_agents=num_agents,
                               max_ticks=max_ticks, n_eras=K)
        permuted = run_condition(wcls, PerceptionAblatedMamba, champion, seed, num_agents=num_agents,
                                 max_ticks=max_ticks, n_eras=K)
        noise = run_condition(wcls, NoiseObsMamba, champion, seed, num_agents=num_agents,
                              max_ticks=max_ticks, n_eras=K)
        zero = run_condition(wcls, ZeroObsMamba, champion, seed, num_agents=num_agents,
                             max_ticks=max_ticks, n_eras=K)

        # Une cellule sans AUCUNE ere n'est pas une mesure : refus explicite, cf. `_eras`.
        i_era = _eras(intact, w, "intact")
        p_era = _eras(permuted, w, "permuted")
        n_era = _eras(noise, w, "noise")
        z_era = _eras(zero, w, "zero")

        # 2026-09-02 : floor MESURE (PLANCHER_NOPERC, regime-gate) + ceiling. Un intact au plancher
        # rend les TROIS barreaux illisibles, pas seulement `zero`.
        floor_w = _floor_for(w, num_agents, max_ticks)
        if floor_w is None:
            # ⚠️ Corrige le 2026-09-08 (defaut expose par injection a dose connue). HORS du regime
            # ou un plancher est MESURE, `_floor_for` rend None (garde E8 : jamais un plancher
            # d'ailleurs) -- et une echelle SANS AUCUNE AMPLITUDE (survie mediane nulle sur les 4
            # conditions) rendait alors ratio = 0/eps = 0.0 sur les 3 barreaux, donc `inverted`,
            # donc ni `decoy` ni `collapse`, donc le verdict de FOND MIXED (mesure : intact_med 0.00,
            # verdict MIXED). 0.0 n'est PAS un plancher importe d'un autre regime :
            # c'est la borne INFERIEURE du support de la metrique (une survie en ticks ne peut pas
            # etre negative), donc une mediane intacte nulle = zero amplitude, rien a ablater.
            floor_w = 0.0
        permuted_v = ablation_verdict(i_era, p_era, n_floor=N_FLOOR,
                                      floor=floor_w, ceiling=float(max_ticks))
        noise_v = ablation_verdict(i_era, n_era, n_floor=N_FLOOR,
                                   floor=floor_w, ceiling=float(max_ticks))
        zero_v = ablation_verdict(i_era, z_era, n_floor=N_FLOOR,
                                  floor=floor_w, ceiling=float(max_ticks))
        rungs = (permuted_v, noise_v, zero_v)

        # On consomme le VERDICT GARDE de chaque barreau, PAS les booleens bruts `decoy`/`collapse`
        # (meme bascule que `_verdict_from` des sondes de demande, 2026-09-02) : les DEUX garde-fous
        # d'`ablation_verdict` -- degenerescence et puissance -- ne modifient que `verdict` /
        # `degenerate`, jamais `decoy` / `collapse`. Les lire bruts les rendait inertes.
        if any(r.get("degenerate") for r in rungs):
            verdict = "INDETERMINE_DEGENERATE"
        elif any(r["n"] < N_FLOOR for r in rungs):
            verdict = "INDETERMINE_UNDERPOWERED"       # sous-puissant : ni neutre, ni sensible
        elif all(r["verdict"] == "X_DECOY" for r in rungs):
            verdict = "SURVIVAL_NEUTRAL"
        elif any(r["verdict"] == "X_DEMANDED" for r in rungs):
            verdict = "SURVIVAL_SENSITIVE"
        else:
            verdict = "MIXED"

        out[w] = {
            "intact_med": float(np.median(i_era)),     # i_era est NON VIDE (garde `_eras`)
            "permuted": permuted_v,
            "noise": noise_v,
            "zero": zero_v,
            "verdict": verdict,
        }
    return out


def main():
    seed = int(os.environ.get("S2OL_SEED", "2026"))
    K = int(os.environ.get("S2OL_K", "12"))
    num_agents = int(os.environ.get("S2OL_AGENTS", "12"))
    max_ticks = int(os.environ.get("S2OL_TICKS", "200"))
    worlds_env = os.environ.get("S2OL_WORLDS")
    worlds = worlds_env.split(",") if worlds_env else None

    m = run_openloop_ladder(worlds, seed=seed, K=K, num_agents=num_agents, max_ticks=max_ticks)
    print(f"\n=== S2-003 — ladder open-loop within-subject (seed={seed}, K={K}) ===")
    print(f"{'monde':12s} {'intact_med':>10s} {'permuted':>9s} {'noise':>9s} {'zero':>9s}  verdict")
    for w, r in m.items():
        print(f"{w:12s} {r['intact_med']:10.1f} {r['permuted']['ratio']:9.2f} "
              f"{r['noise']['ratio']:9.2f} {r['zero']['ratio']:9.2f}  {r['verdict']}")
    surv_neutral = [w for w, r in m.items() if r["verdict"] == "SURVIVAL_NEUTRAL"]
    surv_sensitive = [w for w, r in m.items() if r["verdict"] == "SURVIVAL_SENSITIVE"]
    # ⚠️ Un monde INDÉTERMINÉ n'est ni neutre ni sensible : il ne compte donc dans AUCUNE des deux
    # listes, et sans dénominateur explicite « aucun » se lit comme une affirmation de FOND
    # (« aucun monde n'est neutre » / « aucun n'est sensible ») tirée de zéro mesure LISIBLE.
    indetermines = {w: r["verdict"] for w, r in m.items() if r["verdict"].startswith("INDETERMINE")}
    lisibles = [w for w in m if w not in indetermines]
    vide = f"aucun PARMI {len(lisibles)} monde(s) LISIBLE(s) sur {len(m)} mesuré(s)"
    print(f"\nSURVIVAL_NEUTRAL (survie indifférente à l'obs, même nulle ; PAS 'open-loop') : {surv_neutral or vide}")
    print(f"SURVIVAL_SENSITIVE (au moins un barreau effondre la survie) : {surv_sensitive or vide}")
    if indetermines:
        print(f"INDÉTERMINÉS (échelle ILLISIBLE — refus, PAS un résultat ; hors des deux listes ci-dessus) : {indetermines}")
    if not lisibles:
        print("⚠️ AUCUN monde LISIBLE : les deux lignes ci-dessus ne disent RIEN sur la survie — "
              "ne pas rédiger d'EDR à partir de cette échelle.")
    else:
        print("-> Rédiger EDR-S2-003 à partir de cette échelle.")
    return m


if __name__ == "__main__":
    main()
