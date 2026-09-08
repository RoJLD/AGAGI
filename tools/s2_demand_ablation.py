"""S2-002 — Pont proxy→in-world du demand-marker : bras d'ablation-perception WITHIN-subject sur les
5 mondes réels. Le champion HoF joue INTACT vs perception PERMUTÉE (chaque agent reçoit l'obs d'un
pair -> décorrélée de SA réalité, mais dans-distribution). Si la survie s'effondre, la perception est
causalement porteuse (PERCEPTION_DEMANDED) ; sinon c'est un leurre pour CE champion (PERCEPTION_DECOY).
Contraste avec le between (champion vs réflexe) = rend visible in-world le faux-positif de S2-001.

N'importe PAS en modifiant s2_demand (benchmark pré-enregistré) : réutilise run_condition/WORLDS/
load_champion_genome. Ablation injectée via le seam batch_model_cls.

Usage : python tools/s2_demand_ablation.py   (env: S2ABL_SEED, S2ABL_K, S2ABL_AGENTS, S2ABL_TICKS,
S2ABL_WORLDS="soup,stoneage,...").
"""
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.agents.mamba_agent import MambaBatchModel
from tools.demand_marker import ablation_verdict
from tools.s2_demand import run_condition, WORLDS, load_champion_genome
from tools.experiment_preflight import assert_no_aliasing
from src.agents.baseline_models import ReflexBatchModel


def derange_rows(batch_obs, rng=None):
    """Permute les LIGNES de batch_obs entre agents. B>=2 : dérangement (aucun point fixe) -> chaque
    agent voit l'obs d'un PAIR (décorrélée de sa réalité, dans-distribution). B<2 : copie inchangée
    (near-death ; fuite négligeable et CONSERVATRICE). Ne mute jamais l'entrée. RNG = flux global
    np.random par défaut (seedé aux frontières par le Harness -> appariement préservé)."""
    B = batch_obs.shape[0]
    if B < 2:
        return batch_obs.copy()
    draw = (rng or np.random)
    perm = np.arange(B)
    while np.any(perm == np.arange(B)):        # rejet jusqu'à obtenir un dérangement
        perm = draw.permutation(B)
    return batch_obs[perm].copy()


class PerceptionAblatedMamba(MambaBatchModel):
    """Champion à génome INTACT mais perception décorrélée : permute batch_obs avant le forward normal.
    Sous-classe MambaBatchModel -> réutilise entièrement le moteur/poids ; seule l'ENTRÉE change."""

    def forward(self, batch_obs, env_surprise_batch=None):
        return super().forward(derange_rows(batch_obs), env_surprise_batch)


class NullAblatedMamba(MambaBatchModel):
    """NO-OP EXACT de `PerceptionAblatedMamba` — le contrôle négatif qui manquait à cet instrument.

    Il appelle `derange_rows` (donc consomme EXACTEMENT les mêmes tirages du flux global, boucle de
    rejet comprise) puis **jette** le résultat : la perception reste INTACTE, seule la bande RNG du
    monde est déplacée. Ce que son `within_ratio` mesure est donc le **plancher de bruit de
    l'instrument**, et rien d'autre.

    ⚠️ MESURÉ le 2026-09-08, `stoneage`, régime gravé (12 agents, 200 ticks, K=12, seed 2026) :
    **1,058 sur le champion et 0,922 sur un champion aveuglé**, soit ±6-8 % alors qu'aucune
    information perceptive n'a bougé. Le commentaire « l'ablation consomme des tirages RNG en plus ->
    tape intra-ère non identique » existait depuis le début ; personne ne l'avait CHIFFRÉ.

    Conséquence pour la lecture de cet instrument, à écrire dans tout record qui s'en sert : un
    `within_ratio` dans la bande [0,92 ; 1,06] n'est PAS distinguable de zéro effet. Le champion
    publié est à **0,991** — donc à l'intérieur. Cela ne fabrique pas de faux `DEMANDED` (le bruit ne
    crée pas de demande), mais cela MASQUE toute demande inférieure à ~8 % : `PERCEPTION_DECOY` doit
    se lire « aucun effet DÉTECTABLE au-dessus d'un plancher de bruit de 8 % », jamais « aucun effet ».
    """

    def forward(self, batch_obs, env_surprise_batch=None):
        derange_rows(batch_obs)                # consomme la bande ; le résultat est délibérément jeté
        return super().forward(batch_obs, env_surprise_batch)


_GRAB_LOGIT = 24          # `do_grab = float(logits[24])`, seuille a `> 0` (world_1_stoneage.py:1523)


class GrabOffMamba(MambaBatchModel):
    """Champion a genome INTACT dont l'action GRAB est neutralisee : le logit 24 est force negatif.

    P4.1 -- « le grab NUIT-il quand grabber NOURRIT ? » (famine dure, `forage_payoff = 3.0`).

    ⚠️ DIFFERENCE ESSENTIELLE avec `PerceptionAblatedMamba`, et c'est ce qui rend l'instrument
    utilisable : cette ablation est **RNG-NEUTRE**. `derange_rows` consomme des tirages du flux global
    (boucle de rejet comprise) et DEPLACE la bande aleatoire -- d'ou le plancher de bruit mesure a
    +-6-8 % par `NullAblatedMamba`, dans lequel le resultat publie (0,991) tombe. Ici on ecrit une
    constante dans une sortie : AUCUN tirage n'est consomme.

    ⚠️ COPIE DEFENSIVE OBLIGATOIRE. Ecrire dans une sortie de `forward` peut muter l'etat recurrent
    quand cette sortie est une VUE -- c'est le bug d'aliasing d'EDR-WARM-007, qui avait produit
    dose-reponse, correlations et controle negatif coherents pendant une passe entiere. Mesure ici
    (backend legacy, 2026-09-08) : `preds.base is None` et aucun partage memoire avec les 16 tableaux
    internes du modele. On copie quand meme, et `assert_no_aliasing` le VERIFIE a chaque appel."""

    def forward(self, batch_obs, env_surprise_batch=None):
        preds, spent = super().forward(batch_obs, env_surprise_batch)
        arr = np.asarray(preds)
        if arr.size and arr.ndim == 2 and arr.shape[1] > _GRAB_LOGIT:
            arr = arr.copy()
            assert_no_aliasing(arr, preds, label="sortie de GrabOffMamba")
            arr[:, _GRAB_LOGIT] = -1.0          # do_grab <= 0 -> grab DESACTIVE
            return arr, spent
        return preds, spent


class NullGrabOffMamba(MambaBatchModel):
    """NO-OP EXACT de `GrabOffMamba` -- le controle negatif apparie, et il doit etre BIT-IDENTIQUE.

    Il fait EXACTEMENT le meme travail (copie, garde d'aliasing, ecriture dans la colonne 24) mais
    REECRIT LA VALEUR QU'IL VIENT DE LIRE. Ce que sa comparaison au bras intact mesure est donc le
    plancher de bruit de l'INSTRUMENT, et rien d'autre.

    ⚠️ Attendu : **zero** ecart, exactement -- contrairement a `NullAblatedMamba`, dont la bande
    [0,92 ; 1,06] vient de tirages RNG consommes. Si un ecart apparaissait ici, il faudrait le
    comprendre AVANT de lire quoi que ce soit du bras ablate."""

    def forward(self, batch_obs, env_surprise_batch=None):
        preds, spent = super().forward(batch_obs, env_surprise_batch)
        arr = np.asarray(preds)
        if arr.size and arr.ndim == 2 and arr.shape[1] > _GRAB_LOGIT:
            arr = arr.copy()
            assert_no_aliasing(arr, preds, label="sortie de NullGrabOffMamba")
            arr[:, _GRAB_LOGIT] = arr[:, _GRAB_LOGIT]      # meme ecriture, valeur INCHANGEE
            return arr, spent
        return preds, spent


class GrabForcedMamba(MambaBatchModel):
    """MANIPULATION INVERSE de `GrabOffMamba` -- le controle negatif exige par le design de P4.1.

    Si retirer le grab AMELIORE la survie, alors le FORCER doit la degrader : c'est la dose-reponse, et
    c'est ce qui distingue un effet CAUSAL d'un artefact d'ablation. Sans ce bras, « grab-off survit
    mieux » resterait compatible avec « toute perturbation de la sortie 24 aide », qui est une tout
    autre affirmation.

    Meme forme, meme copie, meme garde d'aliasing, meme neutralite RNG : seule la CONSTANTE change."""

    def forward(self, batch_obs, env_surprise_batch=None):
        preds, spent = super().forward(batch_obs, env_surprise_batch)
        arr = np.asarray(preds)
        if arr.size and arr.ndim == 2 and arr.shape[1] > _GRAB_LOGIT:
            arr = arr.copy()
            assert_no_aliasing(arr, preds, label="sortie de GrabForcedMamba")
            arr[:, _GRAB_LOGIT] = 1.0           # do_grab > 0 -> grab FORCE a chaque tick
            return arr, spent
        return preds, spent


def _median_survival(cond):
    """Survie médiane globale d'une condition run_condition (liste 'survival')."""
    s = cond.get("survival") or []
    return float(np.median(s)) if s else 0.0



# PLANCHER NO-PERCEPTION par monde (2026-09-02), mesure sous bail kuzu par tools/measure_noperc_floors.py
# au REGIME GRAVE des records S2-002/S2-003 (12 agents, 200 ticks, K=12, seed 3026 decouple).
# Construction : max(zero_obs, random_action), les DEUX sur CLONES DU CHAMPION (S2-003 : son edge est
# corps/metabolisme -- des agents frais sous-garderaient). Les deux constructions CONCORDENT partout
# (ecart max 1.2x, controle de coherence WARM-010).
PLANCHER_REGIME = {"num_agents": 12, "max_ticks": 200}
PLANCHER_NOPERC = {"soup": 32.0, "stoneage": 24.0, "agricultural": 25.25,
                   "industrial": 24.0, "famine": 21.75}


def _floor_for(world, num_agents, max_ticks):
    """Garde E8 : JAMAIS un plancher d'un AUTRE regime. Hors du point de mesure (12 agents/200 ticks),
    rendre None -- un plancher importe d'ailleurs fabriquerait la degenerescence qu'il doit detecter."""
    ok = (int(num_agents) == PLANCHER_REGIME["num_agents"]
          and int(max_ticks) == PLANCHER_REGIME["max_ticks"])
    return PLANCHER_NOPERC.get(world) if ok else None


def run_ablation_map(worlds=None, seed=2026, K=12, num_agents=20, max_ticks=400,
                     subject=None, noop_control=False):
    """Pour chaque monde : champion INTACT vs champion ABLATÉ (within) + réflexe (between). Renvoie
    {world: {within_ratio, between_ratio, verdict, n}}. n = K ères (unité d'appariement)."""
    # ⚠️ GARDE D'ARGUMENTS, EN TETE (2026-09-01). Meme raison que pour les autres mesures : sans
    # elle, une cohorte vide ou un horizon nul produit une MESURE (0.0 rendu comme observation),
    # que l'aval lit comme un resultat. On LEVE : un argument degenere est une erreur d'appel, pas
    # un fait sur le monde. Posee avant la construction du monde -> le refus ne coute rien.
    if int(K) <= 0 or int(num_agents) <= 0 or int(max_ticks) <= 0:
        raise ValueError(
            f"run_ablation_map : argument degenere (K={K}, num_agents={num_agents}, max_ticks={max_ticks}) -- "
            "aucune mesure possible ; ne pas confondre avec une mesure nulle OBSERVEE.")
    # Corrige le 2026-09-07 (retro-application du correctif de `run_s2`) : une famille VIDE lancait
    # la grille COMPLETE. `None` = pas de choix ; `[]` = un choix vide, donc une erreur d'appel.
    if worlds is None:
        worlds = list(WORLDS)
    worlds = list(worlds)
    if not worlds:
        raise ValueError(
            "run_ablation_map : argument degenere (famille de mondes VIDE) -- aucune mesure "
            "possible ; ne pas confondre avec une mesure nulle OBSERVEE. (worlds=None pour tout.)")
    # `subject` (2026-09-07) : le SUJET dont on mesure la demande. None = le champion publie, donc
    # bit-identique pour tous les appelants existants. Rendu injectable parce que S6 a montre que le
    # verdict du marqueur est une propriete du SUJET, pas du monde -- et qu'on ne peut pas le tester
    # avec un instrument qui ne sait mesurer qu'UN sujet.
    champion = load_champion_genome() if subject is None else subject
    out = {}
    for w in worlds:
        wcls = WORLDS[w]
        intact = run_condition(wcls, None, champion, seed, num_agents=num_agents,
                               max_ticks=max_ticks, n_eras=K)
        ablated = run_condition(wcls, PerceptionAblatedMamba, champion, seed, num_agents=num_agents,
                                max_ticks=max_ticks, n_eras=K)
        reflex = run_condition(wcls, ReflexBatchModel, None, seed, num_agents=num_agents,
                               max_ticks=max_ticks, n_eras=K)
        # appariement par ère (seed_at par ère) ; l'ablation consomme des tirages RNG en plus ->
        # tape intra-ère non identique, mais le contraste porte sur la perception
        wv = ablation_verdict(intact["era_survival"], ablated["era_survival"],
                              floor=_floor_for(w, num_agents, max_ticks),
                              ceiling=float(max_ticks))
        between_ratio = _median_survival(intact) / max(_median_survival(reflex), 1e-9)
        # NO-OP EXACT (2026-09-08), optionnel : mesure le PLANCHER DE BRUIT de cet instrument sur CE
        # sujet et CE seed, au lieu de le supposer nul. `False` par defaut -> bit-identique pour tous
        # les appelants existants ; aucun record ne bouge.
        noop = None
        if noop_control:
            nul = run_condition(wcls, NullAblatedMamba, champion, seed, num_agents=num_agents,
                                max_ticks=max_ticks, n_eras=K)
            nv = ablation_verdict(intact["era_survival"], nul["era_survival"],
                                  floor=_floor_for(w, num_agents, max_ticks),
                                  ceiling=float(max_ticks))
            noop = {"ratio": nv["ratio"], "verdict": nv["verdict"].replace("X_", "PERCEPTION_"),
                    "median": float(np.median(nul["era_survival"]))}
        verdict = wv["verdict"].replace("X_", "PERCEPTION_")
        out[w] = {"within_ratio": wv["ratio"], "between_ratio": between_ratio,
                  "verdict": verdict, "n": wv["n"],
                  # 2026-09-02 : absolus publies (defaut AUDIT-001 epingle sur S2-009 -- un record
                  # qui ne publie que des ratios cache la proximite au plancher) + le plancher consomme
                  "intact_median": float(np.median(intact["era_survival"])),
                  "floor": _floor_for(w, num_agents, max_ticks),
                  "noop": noop}
    return out


def main():
    seed = int(os.environ.get("S2ABL_SEED", "2026"))
    K = int(os.environ.get("S2ABL_K", "12"))
    num_agents = int(os.environ.get("S2ABL_AGENTS", "20"))
    max_ticks = int(os.environ.get("S2ABL_TICKS", "400"))
    worlds_env = os.environ.get("S2ABL_WORLDS")
    worlds = worlds_env.split(",") if worlds_env else None

    m = run_ablation_map(worlds, seed=seed, K=K, num_agents=num_agents, max_ticks=max_ticks)
    print(f"\n=== S2-002 — ablation-perception within-subject in-world (seed={seed}, K={K}) ===")
    print(f"{'monde':12s} {'within':>8s} {'between':>8s}  verdict")
    for w, r in m.items():
        print(f"{w:12s} {r['within_ratio']:8.2f} {r['between_ratio']:8.2f}  {r['verdict']} (n={r['n']})")
    # lecture : within>>1 = perception causalement porteuse ; within~1 & between>>1 = between
    # FAUX-POSITIVE (survivant existe mais perception = leurre) -> le finding S2-001 rendu in-world.
    disagree = [w for w, r in m.items() if r["between_ratio"] >= 1.5 and r["within_ratio"] <= 1.3]
    print(f"\nDésaccords between/within (between crie demande, within dit leurre) : {disagree or 'aucun'}")
    print("-> Rédiger EDR-S2-002 à partir de cette carte.")
    return m


if __name__ == "__main__":
    main()
