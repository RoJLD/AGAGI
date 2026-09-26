"""P4.18 — `S2-BASSIN-FRAGILITY` : le bassin DAgger est-il une CRÊTE fragile à TOUTE perturbation de W, ou est-ce
la DIRECTION des pas du crédit qui le détruit ?

[[EDR-S2-CREDIT-ABLATION-2]] § Portée : l'érosion y est monotone croissante en mouvement — mesuré en LONGUEUR DE
CHEMIN ; en déplacement net, la sonde de conception l'inverse déjà à une paire (const bouge plus qu'eplr et érode
moins, seed 2026) — et aucun bras ne fait varier la DIRECTION à amplitude appariée. Ce run le fait, SANS apprentissage
nouveau : il
REJOUE la phase 1 des bras de crédit (réplication bit-identique exigée contre les JSON publiés, W appris PERSISTÉ),
puis mesure la phase 2 MORTELLE sur des clones FRAIS du bassin portant :

    transplant   W_bassin + ΔW_crédit                 référence (doit rendre les âges des objets appris, au bit)
    sign         W_bassin + s ⊙ |ΔW_crédit|, s = ±1   sham PRIMAIRE : même support, mêmes normes L1/L2/L∞, signes tirés
    iso          W_bassin + g · ‖ΔW‖₁/‖g‖₁, g gaussien sham SECONDAIRE (le design littéral du backlog), L1 apparié
    sign_x2/x4   sham sign à 2× / 4× l'amplitude       ÉCHELLE (hors verdict) : à quelle amplitude un tirage érode-t-il ?
    eps          sham sign du ΔW de b_full à 1e-3       contrôle POSITIF de DIRECTION (doit être nettement moins érodé
                 (sur le SUPPORT du crédit)            que le crédit) ; s'il ÉRODE : CRETE_A_TOUTE_ECHELLE
    pos          gaussien à 1,0 × ‖W_bassin‖₁           contrôle POSITIF de FRAGILE (limite dite : 24-718× l'amplitude)
    noop         W_bassin                              doit rendre `a_frozen` publié au bit près

⚠️ L'appariement se fait sur le DÉPLACEMENT NET ‖W_final − W_bassin‖₁ PAR AGENT, jamais sur `dW_abs_sum` : ce dernier
cumule |ΔW| à CHAQUE mise à jour (tools/learning_events.py:173,187), c'est une LONGUEUR DE CHEMIN. Un bruit tiré d'un
coup a net = chemin ; un bras de crédit, non. Apparier sur le chemin biaiserait vers FRAGILE par construction
(décision Master 2 du 2026-09-26, sonde de conception : results/s2_bassin_fragility_sonde_conception.json). Le chemin
est publié à côté.

Six bras rejoués : b_full, b_tdonly, b_const, b_eplr (P4.16), b_zero et b_tdoff (P4.9). b_tdoff et b_eplr sont la MÊME
voie (épisodique seul) à deux pas ×10 : la paire de la garde E19 (`_garde_e19`, clause_E19 de la règle), qui rend la
lecture de ces bras DIRECTION_DEPEND_DU_REGLAGE si l'écart sham − crédit se referme de plus de 2/3 d'un pas à l'autre
(revue v3 P1.1 / P7.2 : la paire ne sépare pas le pas de la LÉTALITÉ de phase 1 qui l'accompagne, b_eplr mourant
×4,7 plus que b_tdoff sur 12/12 seeds, et son chemin ne varie que ×1,36 en médiane — d'où « réglage », pas « pas »).

⚠️ Corps (E26) : le monde lit le corps sur les attributs du modèle (`phenotype_*`), dérivés de W[0:10] UNE fois à
`from_genome` ; l'apprentissage écrit `genome.W` sans jamais appeler `update_phenotype` (backend_torch.py:510-513).
Les bras de crédit gardent donc le corps du bassin ; ici aussi : W est remplacé APRÈS `from_genome`, sans
recalcul, et les attributs sont confrontés au corps du bassin calculé INDÉPENDAMMENT (`phenotype_of`), avant et après
chaque phase 2 — une garde qui peut échouer (témoin gelé : un `update_phenotype` sur le W posé la fait lever).

⚠️ RNG : chaque tirage de sham vient d'un flux DÉDIÉ `np.random.SeedSequence([SHAM_ENTROPY, seed, bras, sham,
tirage])`, publié ; aucun tirage ne touche l'état global (numpy / random / torch), vérifié au pré-vol.

Règle SCELLÉE avant toute cellule : docs/preregistrations/S2-BASSIN-FRAGILITY.json.
Usage : python -m tools.evo_runs.s2_bassin_fragility   (env : SBF_SEEDS=12 SBF_OUT=results/s2_bassin_fragility.json
        SBF_BUDGET_S=<sceau> SBF_SMOKE=1 -> 1 seed, 200/100 ticks, fichier _smoke)
"""
import datetime as _dt
import hashlib
import platform
import json
import os
import sys
import time

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.evo_runs.s2_credit_ablation import LR_LOW  # noqa: E402
from tools.evo_runs.s2_credit_ablation_2 import credit_variant  # noqa: E402
from tools.evo_runs.s2_credit_retention import (  # noqa: E402
    REGIME as REGIME_P44, SEEDS_DEFAULT, _finite, _save, load_bassin, phase1_learn_immortal, phase2_survive_mortal)
from tools.evo_runs.s2_reward_ablation import _bassin_cohort  # noqa: E402

PREREG = "S2-BASSIN-FRAGILITY"
ARMS = ("b_full", "b_tdonly", "b_const", "b_eplr", "b_zero", "b_tdoff")
_BASE = {"reward_scale": 1.0, "td_enabled": True, "lr": None, "episode_enabled": True, "reward_const": None}
ARM_CREDIT = {
    "b_full": dict(_BASE),                                     # chemin PUBLIÉ (P4.4 / P4.16)
    "b_tdonly": dict(_BASE, episode_enabled=False),            # P4.16
    "b_const": dict(_BASE, reward_const=1.0),                  # P4.16
    "b_eplr": dict(_BASE, td_enabled=False, lr=LR_LOW),        # P4.16 : épisodique seul, pas 0,004
    "b_zero": dict(_BASE, reward_scale=0.0),                   # P4.9 (NEUTRE : contrôle à faible amplitude)
    "b_tdoff": dict(_BASE, td_enabled=False),                  # P4.9 : épisodique seul, pas 0,04 (paire E19 de b_eplr)
}
P416 = os.path.join("results", "s2_credit_ablation_2.json")
P49 = os.path.join("results", "s2_credit_ablation.json")
P44 = os.path.join("results", "s2_credit_retention.json")
ARM_SOURCE = {"b_full": P416, "b_tdonly": P416, "b_const": P416, "b_eplr": P416, "b_zero": P49, "b_tdoff": P49}
# Garde E19 (porte 23) : la MÊME voie (épisodique seul, TD coupé) à deux pas distincts ×10. L'écart sham − crédit
# (medianes S_sign − S_tr) doit survivre au pas : une fermeture > 2/3 rend la lecture de ces deux bras
# DIRECTION_DEPEND_DU_REGLAGE (clause_E19 de la règle scellée : pas et létalité de phase 1 NON séparés).
E19_PAIRE = {"tdoff": 0.04, "eplr": LR_LOW}
E19_CLOSURE_MAX = 2.0 / 3.0
FAMILLE = 15                              # contrastes NEUFS lus : pos, eps (classe + contraste), 6 classes sign, 5 contrastes
#                                           MOINS des bras érodés + 1 contraste PLUS de b_zero (revue v7 P4.1)
WORKERS_MAX = 6                           # borne des processus ouvriers sur batcave (plafond de contention scellé)
SHAMS = ("sign", "iso")                   # sign = PRIMAIRE (lu par le verdict) ; iso = SECONDAIRE (publié, hors famille)
CONTROLS = ("eps", "pos")
KINDS = SHAMS + CONTROLS + ("sign_x2", "sign_x4", "sign_commun")   # flux dédiés : indices des 6 premiers inchangés
R_DRAWS = 5                               # tirages indépendants par (seed, bras, sham) ; la valeur du seed = médiane
EPS_SCALE = 1e-3                          # eps : sham sign du ΔW de b_full à 1/1000 de son amplitude, SUR SON SUPPORT
ECHELLES = (2.0, 4.0)                     # échelle du sham sign (hors verdict) : amplitude de bascule
POS_REL = 1.0                             # contrôle positif : L1 par agent = POS_REL × ‖W_bassin‖₁
SHAM_ENTROPY = 418                        # racine publiée des flux dédiés
MATCH_TOL = 0.01                          # appariement L1 vérifié à 1 % par agent (exact par construction)
# Seuils de la règle scellée (recopiés pour l'exécutable ; le sceau fait foi, le test les confronte).
SIGN_MIN = 11                             # 11/12 : binomial unilatéral 0,00317 <= 0,05/15 (famille déclarée, E23)
DELTA_MIN = 5.0
N_MIN = 12
HARNESS_MIN = 20.0
SATURATION_HIGH = 0.9
# Bande de TIRAGE. Revue v5 P6.a : la bande de demi-tirages de la v5 laissait un contraste NUL connu HORS de sa bande
# 14-31 % du temps -- elle fabriquait du signal. Revue v6 P6.a : le bootstrap v6 ne rééchantillonnait que les tirages et
# tenait la RÉFÉRENCE (greffe, no-op) pour exacte ; sous le nul ÉCHANGEABLE -- la référence est une réalisation de plus de
# la même loi, ce qu'affirme l'hypothèse FRAGILE -- il ne couvrait plus que 0,95 / 0,89 / 0,88 / 0,87 (σ 1 / 2 / 4 / 8).
# v7 : par seed, le POOL = tirages + référence ; chaque réplicat tire R valeurs du pool (médiane) et UNE valeur du pool pour
# la référence ; bande = quantile BANDE_Q de |m_b| (centre 0 sous le nul). Couverture MESURÉE sur CETTE fonction par
# `mesurer_couverture_bande` (commande « calibrer-bande »), avec son erreur Monte-Carlo, σ homogène et hétérogène :
# results/s2_bassin_fragility_calibration_bande.json (revue v7 P6.2, P6.3).
BANDE_B = 2000
BANDE_Q = 0.975
BANDE_ENTROPY = 4181
# Sorties écrites par le SEUL TD (index dans le bloc de sorties) : grab, rub, tête de valeur -- les constantes
# _GRAB_NODE, _RUB_NODE, _VALUE_NODE de src/agents/backend_torch.py (témoin gelé qui les confronte, sous torch).
TD_SEUL_SORTIES = (24, 25, 28)
GENOMES_DIR = "s2_bassin_fragility_genomes"   # sous results/ (ignoré par git ; sha256 publié dans le JSON)


# --------------------------------------------------------------------------------------------------
# Shams — PURS (aucun monde), testés à réponse connue.
# --------------------------------------------------------------------------------------------------


def sham_rng(seed, arm, kind, draw):
    """Flux DÉDIÉ d'un tirage : jamais l'état global. `arm` peut valoir None (contrôles eps/pos, un par seed)."""
    a = -1 if arm is None else ARMS.index(arm)
    return np.random.default_rng(np.random.SeedSequence([SHAM_ENTROPY, int(seed), a + 1, KINDS.index(kind), int(draw)]))


def l1_per_agent(dW):
    dW = np.asarray(dW, dtype=np.float64)
    return np.abs(dW).reshape(dW.shape[0], -1).sum(axis=1)


def sham_delta(dW, kind, rng, l1_target=None):
    """Le déplacement d'un sham, en float64, forme (B, N, N).

    sign : s ⊙ |dW|, s ∈ {−1, +1} tiré par entrée — support, L1, L2 et L∞ de dW EXACTEMENT conservés, seule la
           direction (le signe) est tirée. Une entrée nulle de dW reste nulle.
    sign_commun : idem, mais la matrice de signes s (N, N) est tirée UNE fois et PARTAGÉE par les B agents (revue v8
           P8.1 : le vote social moyenne les sorties des clones co-localisés ; des signes indépendants par agent sont
           quasi orthogonaux entre agents (cos ≈ 0) quand le crédit est cohérent (cos 0,30-0,77), si bien que le vote
           atténue le tirage plus que le crédit -- biais vers DIRECTION ; les signes partagés le rendent PLUS cohérent
           que le crédit : les deux tirages ENCADRENT la cohérence du crédit). Normes par agent exactement conservées.
    iso  : g gaussien normalisé par agent à `l1_target` (défaut : la L1 de dW, agent par agent).
    Refuse une forme autre que (B, N, N) et une cible négative ou non finie."""
    dW = np.asarray(dW, dtype=np.float64)
    if dW.ndim != 3 or dW.shape[1] != dW.shape[2]:
        raise ValueError(f"sham_delta : dW de forme {dW.shape}, attendu (B, N, N)")
    if kind == "sign":
        s = rng.integers(0, 2, size=dW.shape).astype(np.float64) * 2.0 - 1.0
        return s * np.abs(dW)
    if kind == "sign_commun":
        s = rng.integers(0, 2, size=dW.shape[1:]).astype(np.float64) * 2.0 - 1.0
        return s[None] * np.abs(dW)
    if kind == "iso":
        tgt = l1_per_agent(dW) if l1_target is None else np.broadcast_to(
            np.asarray(l1_target, dtype=np.float64), (dW.shape[0],)).copy()
        if not np.all(np.isfinite(tgt)) or np.any(tgt < 0):
            raise ValueError(f"sham_delta : cible L1 invalide {tgt}")
        g = rng.standard_normal(size=dW.shape)
        norm = np.abs(g).reshape(dW.shape[0], -1).sum(axis=1)
        return g * (tgt / norm)[:, None, None]
    raise ValueError(f"sham_delta : sham inconnu {kind!r} (attendu {SHAMS + ('sign_commun',)})")


def apply_delta(W0, dW):
    """W0 (N, N) float32 + dW (B, N, N) -> (B, N, N) float32, calculé en float64. Bit-exact : apply_delta(W0,
    Wf − W0) rend Wf quand Wf et W0 sont float32 (la différence de deux float32 est exacte en float64)."""
    W0 = np.asarray(W0, dtype=np.float32).astype(np.float64)
    return (W0[None] + np.asarray(dW, dtype=np.float64)).astype(np.float32)


def matching(dW_ref, dW_sham):
    """Écart RELATIF de L1 par agent (sham vs référence) et rapport des L2 — publiés, le premier vérifié à 1 %."""
    l1r, l1s = l1_per_agent(dW_ref), l1_per_agent(dW_sham)
    b = dW_ref.shape[0]
    l2r = np.sqrt((np.asarray(dW_ref, dtype=np.float64).reshape(b, -1) ** 2).sum(1))
    l2s = np.sqrt((np.asarray(dW_sham, dtype=np.float64).reshape(b, -1) ** 2).sum(1))
    rel = np.where(l1r > 0, np.abs(l1s - l1r) / np.where(l1r > 0, l1r, 1.0), np.where(l1s > 0, np.inf, 0.0))
    # revue v3 P1.4 : L1, L2 et L∞ ne disent rien de la norme d'OPÉRATEUR (plus grande valeur singulière), qui borne
    # l'effet de ΔW sur l'activité ; le crédit la dépasse de ×1,07-1,50 au pré-scellement. Publiée, jamais lue.
    opr = np.array([np.linalg.norm(np.asarray(dW_ref[i], dtype=np.float64), 2) for i in range(b)])
    ops = np.array([np.linalg.norm(np.asarray(dW_sham[i], dtype=np.float64), 2) for i in range(b)])
    return {"l1_rel_err_max": float(np.max(rel)),
            "l2_ratio_median": (float(np.median(l2s / l2r)) if np.all(l2r > 0) else None),
            "op_ratio_median": (float(np.median(ops / opr)) if np.all(opr > 0) else None)}


def delta_structure(dW):
    """Où va le déplacement : diagonale (δ = σ(W_jj)), colonnes vers les nœuds d'ENTRÉE (écrasés par l'observation
    à chaque pas, backend_torch.py `_step` : inertes pour la politique), lignes 0:10 (corps, jamais recalculé)."""
    dW = np.asarray(dW, dtype=np.float64)
    a = np.abs(dW)
    tot = float(a.sum())
    if tot == 0.0:
        return {"net_l1_total": 0.0, "diag_share": None, "input_cols_share": None, "body_rows_share": None,
                "td_seul_cols_share": None}
    ni = int(load_bassin().num_inputs)
    diag = float(sum(np.abs(np.diagonal(dW[i])).sum() for i in range(dW.shape[0])))
    b = load_bassin()
    first_out = int(b.W.shape[0]) - int(b.num_outputs)
    td_seul = [first_out + j for j in TD_SEUL_SORTIES]
    return {"net_l1_total": tot, "diag_share": diag / tot, "input_cols_share": float(a[:, :, :ni].sum()) / tot,
            "body_rows_share": float(a[:, 0:10, :].sum()) / tot,
            # revue v8 P7.1 : colonnes grab, rub, valeur -- la perte épisodique ne lit que les logits de déplacement
            "td_seul_cols_share": float(a[:, :, td_seul].sum()) / tot}


# --------------------------------------------------------------------------------------------------
# Monde — rejeu de la phase 1, phase 2 sur W imposés.
# --------------------------------------------------------------------------------------------------


def phase2_with_W(seed, Ws, ticks_test=200):
    """Phase 2 MORTELLE sur des clones FRAIS du bassin portant les W donnés (un par agent, ordre conservé). Le corps
    (attributs `phenotype_*` lus par le monde) doit être celui du BASSIN, calculé indépendamment par `phenotype_of`
    sur le génome du bassin — vérifié AVANT et APRÈS la phase 2 : un recalcul du corps sur le W posé (from_genome,
    add_agent, update_phenotype) ferait lever (revue P10.c : l'ancienne assertion comparait avant/après une simple
    affectation et ne pouvait pas échouer)."""
    from tools.experiment_preflight import phenotype_of
    Ws = np.asarray(Ws, dtype=np.float32)
    want = phenotype_of(load_bassin())
    agents = _bassin_cohort(seed, Ws.shape[0])
    for a, w in zip(agents, Ws):
        a.genome.W = np.array(w, dtype=np.float32, copy=True)
    _assert_body_is_bassin(agents, want, "avant la phase 2")
    with compter_consensus() as cons, compter_reconstructions() as reco:
        surv = phase2_survive_mortal(agents, seed, ticks_test)
    _assert_body_is_bassin(agents, want, "après la phase 2")
    surv["consensus"] = dict(cons)
    surv["reconstructions"] = {"constructions": int(reco["constructions"]),            # initiale COMPRISE
                               "reconstructions": max(int(reco["constructions"]) - 1, 0),  # revue v7 P10.2
                               "B": list(reco["B"])}
    return surv


class compter_consensus:
    """Compte les réécritures de logits par le VOTE SOCIAL du monde (`Biosphere3D._apply_social_consensus`,
    world_1_stoneage.py:947-976) : les logits du modèle torch sont une VUE de son état récurrent H, que ce vote réécrit
    EN ENTIER (sorties 64-171, y compris les nœuds où vit ΔW) quand les logits 13-14 franchissent leurs seuils : la ligne
    de CHAQUE agent de la case, votant ou non, devient la moyenne pondérée (softmax des fitness) des logits des VOTANTS,
    chacun calculé sous son propre ΔW — ΔW n'y est pas masqué mais MOYENNÉ entre clones et, par la vue, réinjecté dans
    l'état récurrent des non-votants (revue v5 P10.c) ; sa fréquence dépend de la condition (revues v3 P8.1, v4 P10.1). Un SECOND écrivain existe et n'est pas compté ici : le monde retranche 0,1 au logit de la dernière action,
    en place, à chaque tick (world_1_stoneage.py:1340), commun à toutes les conditions (revue v4 P8.1).
    ⚠️ Revues v6 P10.b, v7 P10.1 : ce compteur compte les ticks où une ligne a CHANGÉ AU BIT. La moyenne pondérée du
    vote (softmax float32, src/swarm/consensus.py:51, :55) décale la ligne d'environ 1e-7 dès trois votants ou dès deux
    fitness distinctes : il compte donc presque tous les votes, sauf ceux de deux votants à fitness ÉGALES. Le champ
    s'appelle `ticks_avec_reecriture` ; sa fréquence in situ n'est pas mesurée avant le run. Enveloppe de CLASSE, restaurée en `finally` ; elle copie et compare, ne modifie rien
    (neutralité vérifiée par la branche 2 : le no-op doit rendre a_frozen au bit)."""

    def __enter__(self):
        from src.worlds.world_1_stoneage import Biosphere3D
        self._cls, self._orig = Biosphere3D, Biosphere3D._apply_social_consensus
        self.c = {"ticks_avec_reecriture": 0, "lignes_reecrites": 0}
        orig, c = self._orig, self.c

        def wrapped(world, batch_logits):
            before = np.array(batch_logits, copy=True)
            out = orig(world, batch_logits)
            if before.size:
                n = int(np.sum(np.any(np.asarray(out) != before, axis=1)))
                if n:
                    c["ticks_avec_reecriture"] += 1
                    c["lignes_reecrites"] += n
            return out
        Biosphere3D._apply_social_consensus = wrapped
        return self.c

    def __exit__(self, *exc):
        self._cls._apply_social_consensus = self._orig
        return False


class compter_reconstructions:
    """Revue v6 P8.a : un TROISIÈME écrivain de l'état récurrent. En phase 2 MORTELLE, chaque tick qui tue fait tomber B,
    et le monde RECONSTRUIT alors la population torch (world_1_stoneage.py:1060-1066), dont le constructeur pose H à
    zéro pour TOUS les survivants (backend_torch.py:111) -- une mort précoce efface la mémoire récurrente des autres
    clones, à une fréquence qui dépend de la condition. Compte les constructions torch et publie la suite des B.
    Enveloppe de `src.agents.backend.make_population` (importée à l'appel par le monde), restaurée en `finally` ; elle
    ne modifie rien (branche 2 : le no-op rend a_frozen au bit)."""

    def __enter__(self):
        import src.agents.backend as _backend
        self._mod, self._orig = _backend, _backend.make_population
        self.c = {"constructions": 0, "B": []}
        orig, c = self._orig, self.c

        def wrapped(agents, backend="legacy", world_model=None):
            if backend == "torch":
                c["constructions"] += 1
                c["B"].append(len(agents))
            return orig(agents, backend=backend, world_model=world_model)
        _backend.make_population = wrapped
        return self.c

    def __exit__(self, *exc):
        self._mod.make_population = self._orig
        return False


class mesurer_pas_optimiseur:
    """Revues v6 P10.c, v7 P1.4, v8 P10.2 : P4.9 publie `regime.lr_published` = 0,04, le pas MESURÉ sur la trace b_full
    de son pré-vol ; celui de b_tdoff (lr None) s'en DÉDUIT par le défaut partagé, sans avoir été conservé, et le
    compteur ne publie `lr_effective_per_agent` que sur la voie TD. Le
    pas EFFECTIVEMENT posé sur l'optimiseur est lu ici, à chaque construction de la population torch (enveloppe de
    `TorchPopulationModel.__init__`, restaurée en `finally`, qui ne fait que lire)."""

    def __enter__(self):
        from src.agents.backend_torch import TorchPopulationModel as T
        self._T, self._orig = T, T.__init__
        self.pas = []
        orig, pas = self._orig, self.pas

        def __init__(obj, *a, **k):
            orig(obj, *a, **k)
            opt = getattr(obj, "opt", None)
            if opt is not None:
                pas.append(float(opt.param_groups[0]["lr"]))
        T.__init__ = __init__
        return self.pas

    def __exit__(self, *exc):
        self._T.__init__ = self._orig
        return False


def _assert_body_is_bassin(agents, want, moment):
    # Tolérance RELATIVE 1e-6 : l'agent somme W en float32, phenotype_of en float64 (écart mesuré 2e-8 relatif) ;
    # un recalcul sur un W modifié s'écarte de plusieurs ordres de grandeur plus (témoin gelé : ~430 sur hp_bonus).
    rel = lambda x, y: abs(float(x) - float(y)) / max(abs(float(y)), 1e-12)  # noqa: E731
    for a in agents:
        if (rel(a.phenotype_hp_bonus, want["hp_bonus"]) > 1e-6
                or int(a.phenotype_inv_capacity) != int(want["inv_capacity"])
                or rel(a.phenotype_energy_drain, want["energy_drain"]) > 1e-6):
            raise AssertionError(f"phase2_with_W : corps ≠ corps du bassin {moment} (E26) -- "
                                 f"{a.phenotype_hp_bonus}, {a.phenotype_inv_capacity}, {a.phenotype_energy_drain} "
                                 f"contre {want}")


def replay_arm(seed, arm, num_agents=12, ticks_learn=2000, ticks_test=200):
    """Rejoue la phase 1 du bras (même code que P4.16 / P4.9 : credit_variant SOUS count_learning_events), puis la
    phase 2 sur les OBJETS appris (c'est la mesure publiée). Rend W appris (B, N, N) float32 et les deux mesures."""
    if arm not in ARM_CREDIT or int(num_agents) <= 0 or int(ticks_learn) <= 0 or int(ticks_test) <= 0:
        raise ValueError(f"replay_arm : argument dégénéré (arm={arm!r}, num_agents={num_agents}, "
                         f"ticks_learn={ticks_learn}, ticks_test={ticks_test}) -- aucune mesure possible")
    cr = ARM_CREDIT[arm]
    agents = _bassin_cohort(seed, num_agents)
    t0, c0 = time.time(), time.process_time()
    with credit_variant(episode_enabled=cr["episode_enabled"], reward_const=cr["reward_const"]), \
            mesurer_pas_optimiseur() as pas:
        learning = phase1_learn_immortal(agents, seed, ticks_learn, lr=cr["lr"], reward_scale=cr["reward_scale"],
                                         td_enabled=cr["td_enabled"])
    learning = dict(learning, pas_optimiseur_mesure=sorted(set(pas)))   # revue v6 P10.c : le pas se MESURE
    Wf = np.stack([np.asarray(a.genome.W, dtype=np.float32) for a in agents])
    survival = phase2_survive_mortal(agents, seed, ticks_test)
    return {"W_final": Wf, "learning": learning, "survival": survival,
            "wall_s": time.time() - t0, "cpu_s": time.process_time() - c0}


def published(arm_or_frozen, seed, root=_ROOT):
    """Ce que P4.16 / P4.9 ont PUBLIÉ pour ce bras et ce seed : chemin, âges, et la DOSE (mises à jour TD et
    épisodiques, résurrections) — la réplication les exige toutes. `a_frozen` : la ligne de P4.16."""
    src = P416 if arm_or_frozen == "a_frozen" else ARM_SOURCE[arm_or_frozen]
    d = json.load(open(os.path.join(root, src), encoding="utf-8"))
    r = d["arms"][arm_or_frozen][str(int(seed))]
    lrn = r.get("learning") or {}
    return {"source": src, "ages": list(r["survival"]["ages"]), "S": float(r["survival"]["survival_median"]),
            "dW_abs_sum": lrn.get("dW_abs_sum"), "td_updates": lrn.get("td_updates"),
            "episode_updates": lrn.get("episode_updates"), "resurrections": lrn.get("resurrections"),
            "ticks": lrn.get("ticks"), "imported_from": r.get("imported_from")}


def cold_floor(seed, root=_ROOT):
    """`S_c` de P4.4 (cohorte FRAÎCHE sous crédit, mêmes seeds). HÉRITÉ, pas mesuré ici, et PAS un plancher de ce
    dispositif (revue v5 P1.b) : les greffes publiées passent dessous (b_tdoff 7/12 seeds, b_full 3/12, b_tdonly
    1/12) — la saturation |S_tr − S_a| / (S_a − S_c) est un indice RELATIF, qui peut dépasser 1."""
    d = json.load(open(os.path.join(root, P44), encoding="utf-8"))
    return float(d["arms"]["c_cold_credit"][str(int(seed))]["survival"]["survival_median"])


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cells_dir(root=None):
    """Répertoire des cellules (W persistés + JSON de cellule + JSON de seed) : results/<GENOMES_DIR>/, ignoré par git
    (≈80 Mo) ; chaque sha256 est recopié dans le JSON agrégé, qui est SUIVI."""
    name = GENOMES_DIR + os.environ.get("SBF_CELLS_SUFFIX", "")      # « _smoke » : jamais mêlé aux cellules du run
    if root is not None:
        return os.path.join(root, "results", name)
    from src.paths import results_file
    return str(results_file(name))


def _rel(p):
    try:
        return os.path.relpath(p, _ROOT).replace(os.sep, "/")
    except ValueError:                                    # autre disque (Windows) : chemin absolu, jamais inventé
        return p


def _save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def cellule(seed, arm, num_agents=12, ticks_learn=2000, ticks_test=200, root=None, _replay=None):
    """UNE cellule (bras, seed) : rejeu de la phase 1 + phase 2 sur les objets appris, W appris PERSISTÉS (dette de
    P4.9/P4.16) — IDEMPOTENTE : si `<bras>_<seed>.json` et `.npz` existent et que le sha256 du npz est celui écrit dans
    le JSON, la cellule est RELUE, pas recalculée ; un sha256 discordant LÈVE (fichier corrompu ou remplacé), jamais
    une relecture silencieuse. C'est l'unité d'un Job nexus (une commande = une cellule) et d'un processus batcave.
    Rend le dict de `replay_arm` (W_final, learning, survival, wall_s, cpu_s) + `genomes` + `load` + `reloaded`."""
    if arm not in ARM_CREDIT or int(num_agents) <= 0 or int(ticks_learn) <= 0 or int(ticks_test) <= 0:
        raise ValueError(f"cellule : argument dégénéré (arm={arm!r}, num_agents={num_agents}, "
                         f"ticks_learn={ticks_learn}, ticks_test={ticks_test}) -- aucune mesure possible")
    d = cells_dir(root)
    pj, pn = os.path.join(d, f"{arm}_{int(seed)}.json"), os.path.join(d, f"{arm}_{int(seed)}.npz")
    if os.path.exists(pj) and os.path.exists(pn):
        rec = json.load(open(pj, encoding="utf-8"))
        sha = _sha256(pn)
        if sha != rec["genomes"]["sha256"]:
            raise RuntimeError(f"cellule {arm}/{seed} : sha256 du npz {sha[:12]} ≠ celui du JSON "
                               f"{rec['genomes']['sha256'][:12]} -- fichier corrompu ou remplacé, rien n'est relu")
        if (rec["num_agents"], rec["ticks_learn"], rec["ticks_test"]) != (int(num_agents), int(ticks_learn), int(ticks_test)):
            raise RuntimeError(f"cellule {arm}/{seed} : relue avec d'autres paramètres ({rec['num_agents']}, "
                               f"{rec['ticks_learn']}, {rec['ticks_test']}) -- refus")
        rec["W_final"] = np.load(pn)["W_final"]
        rec["reloaded"] = True
        return rec
    start = _charge()
    rp = (_replay or replay_arm)(seed, arm, num_agents=num_agents, ticks_learn=ticks_learn, ticks_test=ticks_test)
    bassin = load_bassin()
    os.makedirs(d, exist_ok=True)
    np.savez_compressed(pn, W_final=np.asarray(rp["W_final"], dtype=np.float32), num_inputs=int(bassin.num_inputs),
                        num_outputs=int(bassin.num_outputs))
    rec = {"seed": int(seed), "arm": arm, "credit": dict(ARM_CREDIT[arm]), "num_agents": int(num_agents),
           "ticks_learn": int(ticks_learn), "ticks_test": int(ticks_test), "learning": rp["learning"],
           "survival": rp["survival"], "wall_s": rp["wall_s"], "cpu_s": rp["cpu_s"], "pid": os.getpid(),
           "load": {"start": start, "end": _charge()}, "genomes": {"path": _rel(pn), "sha256": _sha256(pn)},
           "hote": platform.node()}
    _save_json(pj, rec)
    return dict(rec, W_final=np.asarray(rp["W_final"], dtype=np.float32), reloaded=False)


def _cond_record(surv, dW_ref=None, dW=None):
    out = {"S": float(surv["survival_median"]), "ages": list(surv["ages"]), "censored": int(surv["censored"]),
           "consensus": surv.get("consensus"), "reconstructions": surv.get("reconstructions")}
    if dW_ref is not None and dW is not None:
        out["matching"] = matching(dW_ref, dW)
    return out


def _sign_draws(seed, arm, kind, dW, scale, W0, r_draws, ticks_test, phase2, dW_ref=None, sham="sign"):
    """R tirages du sham `sham` (sign ou sign_commun : support et magnitudes de dW, signes tirés) à l'échelle `scale`,
    flux `kind`."""
    draws = []
    for r in range(int(r_draws)):
        Ws = apply_delta(W0, scale * sham_delta(dW, sham, sham_rng(seed, arm, kind, r)))
        d_eff = Ws.astype(np.float64) - W0.astype(np.float64)[None]            # EFFECTIF : après arrondi float32
        draws.append(_cond_record(phase2(seed, Ws, ticks_test), scale * dW if dW_ref is None else dW_ref, d_eff))
    return {"scale": float(scale), "draws": draws, "S": float(np.median([x["S"] for x in draws])),
            "l1_rel_err_max": float(max(x["matching"]["l1_rel_err_max"] for x in draws))}


def run_fragility_seed(seed, arms=ARMS, r_draws=R_DRAWS, num_agents=12, ticks_learn=2000, ticks_test=200,
                       _replay=None, _phase2=None):
    """Toutes les conditions de phase 2 d'UN seed (l'unité de réplication), sur les W appris des cellules (relues si
    déjà calculées — `cellule` est idempotente). `_replay` / `_phase2` : injection pour les tests d'orchestration
    (jamais passés par main). Garde EN TÊTE : un argument dégénéré lève avant tout monde. Ordre : noop ; par bras
    (transplant, sign, iso, échelle sign ×2 et ×4) ; contrôles (eps = sham sign du ΔW de b_full — ou du premier bras
    — à EPS_SCALE, SUR LE SUPPORT du crédit ; pos = gaussien à POS_REL × ‖W_bassin‖₁). `cpu_s` / `wall_s` : ce
    processus ; `cells_cpu_s` : la somme publiée par les cellules (calculées ailleurs ou ici)."""
    if (int(num_agents) <= 0 or int(ticks_learn) <= 0 or int(ticks_test) <= 0 or int(r_draws) <= 0
            or not arms or any(a not in ARM_CREDIT for a in arms)):
        raise ValueError(f"run_fragility_seed : argument dégénéré (arms={arms}, r_draws={r_draws}, "
                         f"num_agents={num_agents}, ticks_learn={ticks_learn}, ticks_test={ticks_test}) -- aucune "
                         "mesure possible")
    replay = _replay or cellule
    phase2 = _phase2 or phase2_with_W
    bassin = load_bassin()
    W0 = np.asarray(bassin.W, dtype=np.float32)
    l1_W0 = float(np.abs(W0.astype(np.float64)).sum())
    B = int(num_agents)
    out = {"seed": int(seed), "arms": {}, "controls": {}}
    t0, c0 = time.time(), time.process_time()
    zero = np.zeros((B,) + W0.shape, dtype=np.float64)
    out["noop"] = _cond_record(phase2(seed, apply_delta(W0, zero), ticks_test))
    deltas = {}
    for arm in arms:
        rp = replay(seed, arm, num_agents=B, ticks_learn=ticks_learn, ticks_test=ticks_test)
        Wf = np.asarray(rp["W_final"], dtype=np.float32)
        dW = Wf.astype(np.float64) - W0.astype(np.float64)[None]
        deltas[arm] = dW
        rec = {"learning": rp["learning"], "learned_objects": _cond_record(rp["survival"]),
               "replay_wall_s": rp.get("wall_s"), "replay_cpu_s": rp.get("cpu_s"),
               "net_l1_per_agent": l1_per_agent(dW).tolist(), "structure": delta_structure(dW)}
        rec["net_l1_median_agent"] = float(np.median(rec["net_l1_per_agent"]))
        path = float((rp["learning"] or {}).get("dW_abs_sum") or 0.0)
        rec["path_total"] = path
        rec["net_over_path"] = (float(np.sum(rec["net_l1_per_agent"])) / path) if path > 0 else None
        rec["genomes"] = rp.get("genomes")
        rec["cell_reloaded"] = rp.get("reloaded")
        rec["cell_load"] = rp.get("load")
        tr = phase2(seed, apply_delta(W0, dW), ticks_test)
        rec["transplant"] = _cond_record(tr)
        rec["transplant"]["bit_exact_W"] = bool(np.array_equal(apply_delta(W0, dW), Wf))
        rec["transplant"]["ages_identical_to_learned_objects"] = list(tr["ages"]) == list(rp["survival"]["ages"])
        rec["sign"] = _sign_draws(seed, arm, "sign", dW, 1.0, W0, r_draws, ticks_test, phase2, dW_ref=dW)
        draws = []
        for r in range(int(r_draws)):
            Ws = apply_delta(W0, sham_delta(dW, "iso", sham_rng(seed, arm, "iso", r)))
            d_eff = Ws.astype(np.float64) - W0.astype(np.float64)[None]
            draws.append(_cond_record(phase2(seed, Ws, ticks_test), dW, d_eff))
        rec["iso"] = {"draws": draws, "S": float(np.median([x["S"] for x in draws])),
                      "l1_rel_err_max": float(max(x["matching"]["l1_rel_err_max"] for x in draws))}
        for sc in ECHELLES:
            rec[f"sign_x{int(sc)}"] = _sign_draws(seed, arm, f"sign_x{int(sc)}", dW, sc, W0, r_draws, ticks_test, phase2)
        # revue v8 P8.1 : le même tirage de signes, PARTAGÉ par les agents (hors verdict, publié)
        rec["sign_commun"] = _sign_draws(seed, arm, "sign_commun", dW, 1.0, W0, r_draws, ticks_test, phase2, dW_ref=dW,
                                         sham="sign_commun")
        out["arms"][arm] = rec
    ref = "b_full" if "b_full" in deltas else arms[0]
    eps = _sign_draws(seed, None, "eps", deltas[ref], EPS_SCALE, W0, r_draws, ticks_test, phase2)
    out["controls"]["eps"] = dict(eps, reference=ref, scale=float(EPS_SCALE))
    draws = []
    for r in range(int(r_draws)):
        Ws = apply_delta(W0, sham_delta(zero + 1.0, "iso", sham_rng(seed, None, "pos", r), l1_target=POS_REL * l1_W0))
        rec = _cond_record(phase2(seed, Ws, ticks_test))
        rec["l1_per_agent_median"] = float(np.median(l1_per_agent(Ws.astype(np.float64) - W0.astype(np.float64)[None])))
        draws.append(rec)
    out["controls"]["pos"] = {"rel_l1": POS_REL, "draws": draws, "S": float(np.median([x["S"] for x in draws]))}
    out["wall_s"] = time.time() - t0
    out["cpu_s"] = time.process_time() - c0
    out["cells_cpu_s"] = float(sum(float(r["replay_cpu_s"] or 0.0) for r in out["arms"].values()))
    return out


# --------------------------------------------------------------------------------------------------
# Lignes et verdict — PURS.
# --------------------------------------------------------------------------------------------------


def seed_row(cell, seed, root=_ROOT):
    """La ligne du verdict pour un seed : mesures de `run_fragility_seed` + ce que P4.16 / P4.9 / P4.4 ont publié.
    La réplication exige chemin, âges, mises à jour TD et épisodiques, résurrections et ticks ÉGAUX au publié (revue
    P7.a, v5 P10.d)."""
    pub_a = published("a_frozen", seed, root)
    row = {"seed": int(seed), "S_a": cell["noop"]["S"], "noop_identical": cell["noop"]["ages"] == pub_a["ages"],
           "S_c": cold_floor(seed, root), "S_eps": cell["controls"]["eps"]["S"], "S_pos": cell["controls"]["pos"]["S"],
           "S_eps_draws": [x["S"] for x in cell["controls"]["eps"]["draws"]],
           "S_pos_draws": [x["S"] for x in cell["controls"]["pos"]["draws"]],
           "match_eps": cell["controls"]["eps"]["l1_rel_err_max"]}
    for arm, rec in cell["arms"].items():
        pub = published(arm, seed, root)
        lrn = rec["learning"] or {}
        k = arm[2:]
        row[f"S_tr_{k}"] = rec["transplant"]["S"]
        row[f"repl_{k}"] = bool(lrn.get("dW_abs_sum") == pub["dW_abs_sum"]
                                and rec["learned_objects"]["ages"] == pub["ages"]
                                and lrn.get("td_updates") == pub["td_updates"]
                                and lrn.get("episode_updates") == pub["episode_updates"]
                                and lrn.get("resurrections") == pub["resurrections"]
                                and lrn.get("ticks") == pub["ticks"])          # revue v5 P10.d
        row[f"transplant_ok_{k}"] = bool(rec["transplant"]["ages_identical_to_learned_objects"])
        row[f"net_{k}"] = rec["net_l1_median_agent"]
        row[f"net_total_{k}"] = float(np.sum(rec["net_l1_per_agent"]))
        row[f"path_{k}"] = rec["path_total"]
        row[f"resur_{k}"] = float(lrn.get("resurrections") if lrn.get("resurrections") is not None else np.nan)
        for sham in SHAMS + tuple(f"sign_x{int(sc)}" for sc in ECHELLES) + ("sign_commun",):
            row[f"S_{sham}_{k}"] = rec[sham]["S"]
            row[f"S_{sham}_{k}_draws"] = [x["S"] for x in rec[sham]["draws"]]
            row[f"match_{sham}_{k}"] = rec[sham]["l1_rel_err_max"]
        # revue v5 P1.a : norme d'OPÉRATEUR du tirage sur celle du crédit (médiane des 5 tirages ; à ×2, le double)
        row[f"op_sign_{k}"] = float(np.median([x["matching"]["op_ratio_median"] for x in rec["sign"]["draws"]]))
    return row


def seuil_tient(sign_min=SIGN_MIN, n=N_MIN, famille=FAMILLE, alpha_family=0.05):
    """Queue binomiale unilatérale P(X >= sign_min | n, 1/2) contre alpha_family / famille (Bonferroni, la règle
    scellée). Revue v3 P4.3 : la taille de la famille et le seuil n'étaient reliés que par un commentaire — une famille
    de 16 aurait laissé passer 11/12 (0,00317 > 0,003125). Rend (tient, queue, alpha_cellule)."""
    from math import comb
    queue = sum(comb(int(n), k) for k in range(int(sign_min), int(n) + 1)) / 2.0 ** int(n)
    alpha = float(alpha_family) / int(famille)
    return queue <= alpha, queue, alpha


def _bande_contraste(draws_par_seed, refs, b=BANDE_B, q=BANDE_Q):
    """Plancher de BRUIT DE TIRAGE d'un contraste médian apparié m = médiane_seeds(médiane(tirages) − ref), sous le nul
    ÉCHANGEABLE (revue v6 P6.a) : par seed, pool = tirages + référence ; chaque réplicat (`b`, flux PRIVÉ BANDE_ENTROPY,
    jamais l'état global) tire R valeurs du pool pour la médiane et UNE pour la référence ; bande = quantile `q` de |m_b|.
    Un contraste dont |m| <= bande n'est pas distinguable de zéro par le bruit de tirage, référence comprise. Couverture
    MESURÉE par `mesurer_couverture_bande` sur CETTE fonction (revue v7 P6.2, P6.3 : les chiffres de la v7 venaient d'un
    script qui calculait une autre bande), publiée avec son erreur Monte-Carlo dans
    results/s2_bassin_fragility_calibration_bande.json. None si un seed a moins de 2 tirages ou si les longueurs
    diffèrent (jamais inventé)."""
    if (not draws_par_seed or any(len(d) < 2 for d in draws_par_seed) or len(set(len(d) for d in draws_par_seed)) != 1
            or len(refs) != len(draws_par_seed)):
        return None
    d = np.asarray(draws_par_seed, dtype=np.float64)
    ref = np.asarray(refs, dtype=np.float64)
    pool = np.concatenate([d, ref[:, None]], axis=1)                                  # (seeds, R + 1)
    rng = np.random.default_rng(np.random.SeedSequence([BANDE_ENTROPY, d.shape[0], d.shape[1]]))
    idx = rng.integers(0, pool.shape[1], size=(int(b), pool.shape[0], pool.shape[1]))
    rs = np.take_along_axis(np.broadcast_to(pool, (int(b),) + pool.shape), idx, axis=2)
    mb = np.median(np.median(rs[:, :, :-1], axis=2) - rs[:, :, -1], axis=1)
    return float(np.quantile(np.abs(mb), float(q)))


def mesurer_couverture_bande(bande=None, reps=1000, sigmas=(0.5, 1.0, 2.0, 4.0, 8.0), effets=(2.0, 4.0), seed=7,
                             n_seeds=N_MIN, r_draws=R_DRAWS):
    """Couverture d'un contraste NUL connu et puissance à effet connu de la bande `bande` (défaut : _bande_contraste,
    celle qu'exécute le runner). Modèle : n_seeds, référence au centre tiré, r_draws tirages = centre + N(0, σ) arrondis
    au demi-tick ; nul EXACT (référence = centre) et nul ÉCHANGEABLE (référence = une réalisation de plus) ; σ homogène
    et hétérogène (σ × U(0,5 ; 3) par seed). Erreur Monte-Carlo publiée (√(p(1−p)/reps)). Aucun monde, flux privé."""
    bande = bande or _bande_contraste
    rng = np.random.default_rng(np.random.SeedSequence([BANDE_ENTROPY, 7, int(seed)]))

    def _un(sig_par_seed, effet, echangeable):
        c = np.round(rng.uniform(7, 45, size=n_seeds) * 2) / 2
        draws = [list(np.round((x + effet + rng.normal(0, s, size=r_draws)) * 2) / 2) for x, s in zip(c, sig_par_seed)]
        refs = list(np.round((c + rng.normal(0, 1, size=n_seeds) * sig_par_seed) * 2) / 2) if echangeable else list(c)
        m = float(np.median([np.median(d) - r for d, r in zip(draws, refs)]))
        return bool(_dans_la_bande(m, bande(draws, refs)))       # le MÊME critère que le drapeau du verdict

    def _taux(p):
        return {"taux": p, "erreur_mc": float(np.sqrt(max(p * (1 - p), 0.0) / reps)), "reps": int(reps)}

    out = {"reps": int(reps), "n_seeds": int(n_seeds), "r_draws": int(r_draws), "couverture": {}, "puissance": {}}
    for nom, ech in (("exacte", False), ("echangeable", True)):
        for sg in sigmas:
            homog = sum(_un(np.full(n_seeds, sg), 0.0, ech) for _ in range(reps)) / reps
            hetero = sum(_un(sg * rng.uniform(0.5, 3.0, size=n_seeds), 0.0, ech) for _ in range(reps)) / reps
            out["couverture"][f"{nom}_sigma_{sg}"] = {"homogene": _taux(homog), "heterogene": _taux(hetero)}
    for ef in effets:
        p = sum(not _un(np.full(n_seeds, 2.0), ef, False) for _ in range(reps)) / reps
        out["puissance"][f"effet_{ef}_sigma_2"] = _taux(p)
        # revue v8 P6.2 : la puissance aussi sous référence BRUITÉE (le nul de FRAGILE pose la greffe comme une
        # réalisation de plus) -- sans elle, 0,81 à un effet de 2 surestimait la puissance réelle
        p = sum(not _un(np.full(n_seeds, 2.0), ef, True) for _ in range(reps)) / reps
        out["puissance"][f"effet_{ef}_sigma_2_reference_echangeable"] = _taux(p)
    return out


def _dans_la_bande(med, bande):
    """|médiane| <= bande -> True ; bande inconnue -> None (jamais « hors de la bande » par défaut)."""
    return bool(abs(float(med)) <= float(bande)) if bande is not None else None


def _classer(d, sign_min, delta_min):
    """ERODE si < 0 sur >= sign_min ET médiane <= −delta_min ; ETENDU symétrique ; NEUTRE sinon (égalités contre)."""
    pos, neg = sum(1 for x in d if x > 0), sum(1 for x in d if x < 0)
    med = float(np.median(d))
    if neg >= sign_min and med <= -delta_min:
        return "ERODE", pos, neg, med
    if pos >= sign_min and med >= delta_min:
        return "ETENDU", pos, neg, med
    return "NEUTRE", pos, neg, med


def _lecture_bras(tr_cls, sh_cls, moins, cmed, delta_min=DELTA_MIN, plus=False):
    """Lecture d'UN bras (branche 10 de la règle). FRAGILE EXIGE que le sham ÉRODE (revue P5.a) ET que le contraste
    médian sham − crédit reste SOUS delta_min (revue v4 P1.1 : un sham qui ne reproduisait que 29 % de la perte, au
    contraste médian +20 sur 10/12 seeds, sortait FRAGILE par la seule voie du COMPTAGE) ; un sham qui érode sans être
    ni « autant » ni nettement « moins », ou qui n'érode pas sans être nettement moins érodé : NON_TRANCHE. Greffe
    NEUTRE : PROTECTRICE (« le crédit abîme MOINS que son tirage ») EXIGE le contraste PLUS — sham − crédit < 0 sur
    >= sign_min seeds ET médiane <= −delta_min (revue v7 P4.1 : sans lui, un tirage à 4,5 ticks sous la greffe sortait
    PROTECTRICE, et le même écart sur une greffe érodée était lu FRAGILE) ; sham ERODE sans PLUS : NON_TRANCHE."""
    if tr_cls == "ERODE":
        if sh_cls == "ERODE":
            if moins:
                return "PARTIEL"
            return "FRAGILE" if float(cmed) < float(delta_min) else "NON_TRANCHE"
        return "DIRECTION" if moins else "NON_TRANCHE"
    if tr_cls == "NEUTRE":
        if sh_cls == "ERODE":
            return "PROTECTRICE" if plus else "NON_TRANCHE"
        return "INOFFENSIF"
    return "CREDIT_ETEND"


def _garde_e19(par_bras, paire=None, closure_max=E19_CLOSURE_MAX, S_a_median=None, saturation_high=SATURATION_HIGH):
    """Appel RÉEL de `assert_verdict_invariant_to_optimizer` sur la paire de même voie à deux pas (clause_E19), TOUJOURS
    exécuté et publié. Revue v4 : (P5.2) l'écart est NORMALISÉ par la perte de greffe — measure(lr) = (0, f) avec
    f = (méd S_sign − méd S_tr) / (méd S_a − méd S_tr), la part de la perte que le sham ÉPARGNE : un sham inerte vaut 1
    aux deux pas, fermeture 0 (en ticks bruts, la seule différence d'amplitude du crédit consommait déjà 0,33) ;
    (P1.2/P10.2) si un bras de la paire a une saturation médiane >= saturation_high, l'écart y est écrasé par le
    plancher : la garde est ILLISIBLE et ne réétiquette rien ; (P6.1) sans bras DIRECTION/PARTIEL dans la paire, il n'y
    a rien à défendre ; (P4.4) une fermeture EXACTEMENT égale à 2/3 est gardée invariante (seuil + 1e-12, déclaré).
    Rend {lisible, a_defendre, invariant, fractions, closure, raison}."""
    from tools.experiment_preflight import PreflightError, assert_verdict_invariant_to_optimizer
    paire = paire or E19_PAIRE
    frac = {}
    for k, lr in paire.items():
        perte = float(S_a_median) - float(par_bras[k]["S_tr_median"])
        frac[float(lr)] = ((float(par_bras[k]["sign"]["S_median"]) - float(par_bras[k]["S_tr_median"])) / perte
                           if perte > 0 else None)
    sat = {k: par_bras[k]["saturation_transplant_median"] for k in paire}
    satures = [k for k, v in sat.items() if v is not None and v >= float(saturation_high)]
    a_defendre = any(par_bras[k]["sign"]["lecture"] in ("DIRECTION", "PARTIEL") for k in paire)
    out = {"paire": dict(paire), "fractions_epargnees": {str(lr): f for lr, f in frac.items()},
           "saturations": sat, "a_defendre": bool(a_defendre), "closure_max": float(closure_max)}
    if any(f is None for f in frac.values()):
        out.update(lisible=False, invariant=None, closure=None,
                   raison="perte de greffe nulle ou négative sur un bras de la paire : fraction indéfinie")
        return out
    g = sorted(frac.values())
    out["closure"] = (1.0 - g[0] / g[-1]) if g[-1] > 0 else None
    try:
        assert_verdict_invariant_to_optimizer(lambda lr: (0.0, frac[float(lr)]), lrs=tuple(frac),
                                              max_gap_closure=float(closure_max) + 1e-12,
                                              label="P4.18 part de la perte épargnée par le sham, voie épisodique")
        out.update(invariant=True, raison=None)
    except PreflightError as exc:
        out.update(invariant=False, raison=str(exc))
    out["lisible"] = bool(not satures and a_defendre)
    if satures:
        out["raison_illisible"] = f"plancher : saturation >= {saturation_high} sur {satures}"
    elif not a_defendre:
        out["raison_illisible"] = "rien à défendre : aucun bras de la paire n'est DIRECTION ni PARTIEL"
    return out


def _partition_letale(par_bras, fr, di):
    """Revue v5 P7.1 : la répartition FRAGILE / DIRECTION est-elle AUSSI une partition par la létalité de phase 1
    (résurrections médianes sans chevauchement, dans un sens ou l'autre) ? Si oui, amplitude et létalité ne sont
    pas séparées et l'étiquette MIXTE_PAR_AMPLITUDE serait une attribution que ce run ne peut pas faire."""
    rf = [par_bras[k]["resurrections_phase1_median"] for k in fr]
    rd = [par_bras[k]["resurrections_phase1_median"] for k in di]
    return bool(rf and rd and (max(rf) < min(rd) or max(rd) < min(rf)))


def fragility_verdict(rows, arms=ARMS, sign_min=SIGN_MIN, delta_min=DELTA_MIN, n_min=N_MIN, harness_min=HARNESS_MIN,
                      match_tol=MATCH_TOL, saturation_high=SATURATION_HIGH):
    """Lecture de la règle scellée S2-BASSIN-FRAGILITY, branches dans l'ORDRE IMPOSÉ :
    1 INCOMPLET -> 2 INDETERMINE_NOOP (no-op ≠ a_frozen publié) -> 3 INDETERMINE_HARNAIS (S_a < 20 ou dégénéré) ->
    4 INDETERMINE_REPLICATION (rejeu ≠ publié : chemin, âges, dose, résurrections) -> 5 INDETERMINE_TRANSPLANT ->
    6 INDETERMINE_APPARIEMENT (L1 hors 1 %) -> 7 INDETERMINE_INSTRUMENT (`pos` n'érode pas : FRAGILE inatteignable) ->
    8 INDETERMINE_PREMISSE (le transplant de b_full n'érode pas) -> 9a CRETE_A_TOUTE_ECHELLE (`eps` érode) / 9b
    INDETERMINE_INSTRUMENT (`eps` n'est pas nettement moins érodé que le crédit complet : DIRECTION inatteignable) ->
    10 lecture par bras (sham `sign`) -> 10bis garde E19 -> 11 globale.
    Toute entrée absente ou non finie LÈVE ; une collection vide LÈVE (aucun verdict fabriqué)."""
    from tools.experiment_preflight import PreflightError, assert_not_degenerate
    if not rows:
        raise ValueError("fragility_verdict : aucune ligne -- aucun verdict n'est fabriqué")
    tient, queue, alpha = seuil_tient(sign_min, n_min, FAMILLE)
    if not tient:
        raise ValueError(f"fragility_verdict : seuil {sign_min}/{n_min} (queue {queue:.5f}) au-dessus de 0,05/{FAMILLE} = "
                         f"{alpha:.5f} -- la famille déclarée ne tolère pas ce seuil (E23)")
    ks = [a[2:] for a in arms]
    echelles = [f"sign_x{int(sc)}" for sc in ECHELLES]
    need = ["S_a", "S_c", "S_eps", "S_pos", "match_eps"] + [
        f"{p}_{k}" for k in ks for p in ("S_tr", "S_sign", "S_iso", "net", "net_total", "path", "resur", "match_sign",
                                         "match_iso", "op_sign", "S_sign_commun", "match_sign_commun")] + [f"{p}_{e}_{k}" for k in ks for e in echelles
                                                          for p in ("S", "match")]
    for r in rows:
        for key in need:
            if key not in r or not _finite(r[key]):
                raise ValueError(f"fragility_verdict : {key} absent ou non fini pour le seed {r.get('seed')}")
        for key in ["noop_identical"] + [f"{p}_{k}" for k in ks for p in ("repl", "transplant_ok")]:
            if not isinstance(r.get(key), bool):
                raise ValueError(f"fragility_verdict : {key} absent (booléen attendu) pour le seed {r.get('seed')}")
    n = len(rows)
    S_a = [float(r["S_a"]) for r in rows]
    out = {"n": n, "S_a_median": float(np.median(S_a)), "S_c_median": float(np.median([r["S_c"] for r in rows])),
           "par_bras": {}, "secondaire_iso": {}, "secondaire_commun": {}, "controles": {}, "verdict": None, "lecture_globale": None,
           "famille": int(FAMILLE),
           "thresholds": {"sign_min": int(sign_min), "delta_min": float(delta_min), "n_min": int(n_min),
                          "harness_min": float(harness_min), "match_tol": float(match_tol),
                          "saturation_high": float(saturation_high), "e19_closure_max": float(E19_CLOSURE_MAX)}}

    def _moins(xs, refs):
        c = [x - y for x, y in zip(xs, refs)]
        cpos, cmed = sum(1 for x in c if x > 0), float(np.median(c))
        return cpos >= sign_min and cmed >= delta_min, cpos, cmed

    def _plus(xs, refs):                          # revue v7 P4.1 : le sens inverse, pour PROTECTRICE
        c = [x - y for x, y in zip(xs, refs)]
        cneg, cmed = sum(1 for x in c if x < 0), float(np.median(c))
        return cneg >= sign_min and cmed <= -delta_min, cneg

    # Publié quel que soit le verdict : contrôles (eps = contrôle positif de DIRECTION, pos = de FRAGILE).
    for c in ("eps", "pos"):
        cls, pos, neg, med = _classer([float(r[f"S_{c}"]) - a for r, a in zip(rows, S_a)], sign_min, delta_min)
        bs = _bande_contraste([r.get(f"S_{c}_draws") or [] for r in rows], S_a)      # revue v5 P6.b
        out["controles"][c] = {"classe": cls, "mediane": med, "positifs": f"{pos}/{n}", "negatifs": f"{neg}/{n}",
                               "bande_vs_S_a": bs, "dans_la_bande_vs_S_a": _dans_la_bande(med, bs)}
    if "full" in ks:
        m, cpos, cmed = _moins([float(r["S_eps"]) for r in rows], [float(r["S_tr_full"]) for r in rows])
        bc = _bande_contraste([r.get("S_eps_draws") or [] for r in rows], [float(r["S_tr_full"]) for r in rows])
        out["controles"]["eps"].update({"moins_erode_que_le_credit_complet": bool(m), "contraste_positifs": f"{cpos}/{n}",
                                        "contraste_mediane": cmed, "bande_contraste": bc,
                                        "dans_la_bande": _dans_la_bande(cmed, bc)})
    # revue v3 P5.1 : sur un seed où S_eps = S_a au bit, 9b ne teste rien de plus que la branche 8 — compté et publié.
    n_eq = sum(1 for r in rows if float(r["S_eps"]) == float(r["S_a"]))
    out["controles"]["eps"]["seeds_eps_egal_noop"] = f"{n_eq}/{n}"
    # revue v7 P5.1 : une fois la branche 8 passée (greffe complète érodée) et 9a écartée (eps n'érode pas), 9b vaut
    # l'écart de la branche 8 augmenté du petit écart d'eps au no-op -- il n'échoue que si eps perd > 17 ticks sur deux
    # seeds en gardant une médiane > −5 (3 mondes sur 6400 au balayage de la revue). Le contrôle positif de DIRECTION
    # n'est donc PAS ÉPROUVÉ, PAR CONSTRUCTION, quel que soit eps ; l'inertie d'eps reste publiée (revues v4-v6).
    inerte_bande = out["controles"]["eps"].get("dans_la_bande_vs_S_a") is True
    out["controles"]["eps"]["eps_inerte_par_la_bande"] = inerte_bande
    out["controles"]["eps"]["eps_inerte"] = bool(n_eq >= int(sign_min) or inerte_bande)
    out["controles"]["eps"]["controle_direction_non_eprouve"] = True
    out["controles"]["eps"]["pourquoi_non_eprouve"] = ("par construction : 9b = écart de la branche 8 + écart d'eps au "
                                                       "no-op ; aucune issue négative propre (revue v7 P5.1)")
    for k in ks:
        tr = [float(r[f"S_tr_{k}"]) for r in rows]
        sat = [abs(t - a) / (a - float(r["S_c"])) if a > float(r["S_c"]) else None for r, t, a in zip(rows, tr, S_a)]
        sat_ok = [s for s in sat if s is not None]
        ratios = [float(r[f"net_total_{k}"]) / float(r[f"path_{k}"]) for r in rows if float(r[f"path_{k}"]) > 0]
        b = {"net_l1_median_agent": float(np.median([float(r[f"net_{k}"]) for r in rows])),
             "net_over_path_median": float(np.median(ratios)) if ratios else None,
             "saturation_transplant_median": float(np.median(sat_ok)) if sat_ok else None,
             "resurrections_phase1_median": float(np.median([float(r[f"resur_{k}"]) for r in rows])),
             "S_tr_median": float(np.median(tr))}
        tc = _classer([t - a for t, a in zip(tr, S_a)], sign_min, delta_min)
        b["transplant"] = {"classe": tc[0], "mediane": tc[3], "negatifs": f"{tc[2]}/{n}"}
        opm = float(np.median([float(r[f"op_sign_{k}"]) for r in rows]))
        for sham in SHAMS:
            sh = [float(r[f"S_{sham}_{k}"]) for r in rows]
            sc = _classer([s - a for s, a in zip(sh, S_a)], sign_min, delta_min)
            moins, cpos, cmed = _moins(sh, tr)
            plus, cneg = _plus(sh, tr)
            d01 = [float(r[f"S_{sham}_{k}_draws"][0]) - float(r[f"S_{sham}_{k}_draws"][1]) for r in rows
                   if len(r.get(f"S_{sham}_{k}_draws") or []) >= 2]
            bande = ({"mediane": float(np.median(d01)), "abs_mediane": float(np.median(np.abs(d01))), "n": len(d01)}
                     if d01 else None)
            bande_c = _bande_contraste([r.get(f"S_{sham}_{k}_draws") or [] for r in rows], tr)
            bande_a = _bande_contraste([r.get(f"S_{sham}_{k}_draws") or [] for r in rows], S_a)   # revue v5 P6.b
            try:                                   # revue v5 P5.3 : un contraste sans dispersion est un plancher
                assert_not_degenerate([s - t for s, t in zip(sh, tr)], min_spread=1e-9,
                                      label=f"contraste {sham} − greffe, {k}")
                degen = None
            except PreflightError as exc:
                degen = str(exc)
            rec = {"S_median": float(np.median(sh)), "classe_vs_S_a": sc[0], "mediane_vs_S_a": sc[3],
                   "negatifs_vs_S_a": f"{sc[2]}/{n}", "bande_vs_S_a": bande_a,
                   "dans_la_bande_vs_S_a": _dans_la_bande(sc[3], bande_a),
                   "contraste_degenere": degen, "contraste_vs_transplant_mediane": cmed,
                   "contraste_positifs": f"{cpos}/{n}", "moins_erode_que_le_credit": bool(moins),
                   "bande_tirage0_moins_tirage1": bande,         # dispersion PAR SEED (publiée, pas le plancher)
                   # revues v5 P6.a, v6 P6.a : plancher de BRUIT DE TIRAGE de ce contraste, bootstrap ÉCHANGEABLE
                   # (couverture MESURÉE dans results/s2_bassin_fragility_calibration_bande.json)
                   "bande_contraste": bande_c,
                   "dans_la_bande": _dans_la_bande(cmed, bande_c),
                   "contraste_negatifs": f"{cneg}/{n}", "plus_erode_que_le_credit": bool(plus),
                   "lecture": _lecture_bras(tc[0], sc[0], moins, cmed, delta_min, plus=plus)}
            if sham == "sign":
                # revue v5 P1.a : le tirage a les normes COORDONNÉE par coordonnée du crédit, pas sa norme d'OPÉRATEUR ;
                # à ×2 il la dépasse (2 × rapport >= 1). Revue v6 P4.a : le contraste ×2 − greffe n'a AUCUN critère
                # exécutable et ne tranche RIEN (ni la part de la norme d'opérateur, ni le remède) : publié, descriptif
                rec["op_ratio_tirage_sur_credit_median"] = opm
                rec["op_ratio_tirage_x2_sur_credit_median"] = 2.0 * opm
                b["sign"] = rec                                   # PRIMAIRE : lu par le verdict
            else:                                                 # SECONDAIRE : publié, jamais lu comme verdict
                rec["lecture_hors_famille"] = rec.pop("lecture")  # revue v3 P4.4 : jamais citable comme un verdict
                rec["hors_famille"] = True
                out["secondaire_iso"][k] = rec
        # revue v8 P8.1 : tirage à signes PARTAGÉS -- publié, hors famille, ne tranche rien ; il dit si l'issue du sham
        # sign dépend de la cohérence inter-agents du tirage, que le vote social traite différemment du crédit
        shc = [float(r[f"S_sign_commun_{k}"]) for r in rows]
        scc = _classer([x - a for x, a in zip(shc, S_a)], sign_min, delta_min)
        mc, cpc, cmc = _moins(shc, tr)
        bcc = _bande_contraste([r.get(f"S_sign_commun_{k}_draws") or [] for r in rows], tr)
        out["secondaire_commun"][k] = {
            "S_median": float(np.median(shc)), "classe_vs_S_a": scc[0], "mediane_vs_S_a": scc[3],
            "contraste_vs_transplant_mediane": cmc, "contraste_positifs": f"{cpc}/{n}",
            "moins_erode_que_le_credit": bool(mc), "bande_contraste": bcc, "dans_la_bande": _dans_la_bande(cmc, bcc),
            "meme_issue_que_sign": bool(scc[0] == b["sign"]["classe_vs_S_a"]
                                        and bool(mc) == b["sign"]["moins_erode_que_le_credit"]),
            "hors_famille": True, "descriptif_ne_tranche_rien": True}
        # Échelle du sham sign (hors verdict, publiée) : à quelle amplitude un tirage de signes se met-il à éroder ?
        b["echelle_sign"] = {}
        bascule = 1.0 if b["sign"]["classe_vs_S_a"] == "ERODE" else None
        for e, scv in zip(echelles, ECHELLES):
            xs = [float(r[f"S_{e}_{k}"]) for r in rows]
            ec = _classer([x - a for x, a in zip(xs, S_a)], sign_min, delta_min)
            b["echelle_sign"][e] = {"S_median": float(np.median(xs)), "classe_vs_S_a": ec[0], "mediane_vs_S_a": ec[3],
                                    "contraste_vs_transplant_mediane": float(np.median([x - t for x, t in zip(xs, tr)])),
                                    "contraste_positifs": f"{sum(1 for x, t in zip(xs, tr) if x - t > 0)}/{n}",
                                    "hors_famille": True, "descriptif_ne_tranche_rien": True}
            if bascule is None and ec[0] == "ERODE":
                bascule = float(scv)
        b["echelle_sign"]["premiere_echelle_qui_erode"] = bascule
        # Qualificatifs PUBLIÉS, hors famille, jamais un changement de lecture (revue v3) :
        gap = float(np.median([a - t for a, t in zip(S_a, tr)]))
        eps_d = float(np.median([float(r[f"S_sign_{k}"]) - float(r["S_eps"]) for r in rows]))
        pos_max = sum(1 for a, t in zip(S_a, tr) if a - t > 0)
        b["qualificatifs"] = {
            # revue v4 P5.1 : même un sham parfaitement INERTE ne rend MOINS que sur les seeds où la greffe érode
            "moins_max_atteignable": f"{pos_max}/{n}", "moins_atteignable_avec_marge": bool(pos_max > int(sign_min)),
            # P5.3 : un seuil ABSOLU de 5 ticks rend FRAGILE plus exigeant aux grands écarts
            "ecart_greffe_mediane": gap,
            "fraction_de_perte_requise_pour_FRAGILE": (1.0 - float(delta_min) / gap) if gap > 0 else None,
            # P6.1 : le sham érode-t-il au-delà du plancher eps ?
            "sign_moins_eps_mediane": eps_d, "au_dela_du_plancher_eps": bool(eps_d <= -float(delta_min)),
            # P6.2 : à saturation >= seuil, FRAGILE n'établit qu'une SUFFISANCE
            "suffisance_seulement": bool(b["sign"]["lecture"] == "FRAGILE" and b["saturation_transplant_median"] is not None
                                         and b["saturation_transplant_median"] >= float(saturation_high))}
        out["par_bras"][k] = b
    out["e19"] = (_garde_e19(out["par_bras"], S_a_median=out["S_a_median"], saturation_high=saturation_high)
                  if all(k in ks for k in E19_PAIRE) else None)
    if out["e19"] is not None:                    # revue v3 P1.1 / P7.2 : ce que la paire ne sépare PAS, mesuré
        t, e = list(E19_PAIRE)
        out["e19"]["chemin_ratio_median"] = float(np.median([float(r[f"path_{t}"]) / float(r[f"path_{e}"])
                                                             for r in rows if float(r[f"path_{e}"]) > 0]))
        out["e19"]["net_ratio_median"] = float(np.median([float(r[f"net_{t}"]) / float(r[f"net_{e}"])
                                                          for r in rows if float(r[f"net_{e}"]) > 0]))
        out["e19"]["resurrections_medianes"] = {k: out["par_bras"][k]["resurrections_phase1_median"] for k in (t, e)}
        # revue v4 P7.2 : le pas EFFECTIF se calcule (SGD, perte moyennée sur B = 12 constant en phase 1) ; la masse de
        # gradient (chemin / pas) varie en sens CONTRAIRE — les deux facteurs de dose sont publiés.
        lr_t, lr_e = float(E19_PAIRE[t]), float(E19_PAIRE[e])
        out["e19"]["pas_effectif_par_agent"] = {t: lr_t / 12.0, e: lr_e / 12.0}
        out["e19"]["masse_gradient_ratio_median"] = float(np.median(
            [(float(r[f"path_{e}"]) / lr_e) / (float(r[f"path_{t}"]) / lr_t) for r in rows if float(r[f"path_{t}"]) > 0]))
        out["e19"]["etiquette"] = "DIRECTION_DEPEND_DU_REGLAGE (pas et létalité de phase 1 non séparés)"
        # revue v5 P5.1, v7 P1.2 : la lisibilité ne dépend que de S_a et S_tr, imposés au bit par les branches 2 et 4, et
        # de S_c, constante PUBLIÉE de P4.4 lue telle quelle (cold_floor) -- aucune branche ne le recalcule --
        # ILLISIBLE ici est connu d'AVANCE (saturation de b_tdoff >= 0,9 sur 12/12 seeds publiés) ; toute lecture
        # DIRECTION/PARTIEL d'un bras de la paire sort alors NON DÉFENDUE contre le pas, et le verdict le dit.
        for k in (t, e):
            if k in out["par_bras"]:
                out["par_bras"][k]["sign"]["defendu_contre_le_pas"] = bool(out["e19"]["lisible"])
    # Branches dans l'ordre imposé.
    if n < n_min:
        out.update(verdict="INCOMPLET", why=f"{n} seeds < {n_min} : reprise, aucune lecture")
        return out
    if not all(r["noop_identical"] for r in rows):
        bad = [r["seed"] for r in rows if not r["noop_identical"]]
        out.update(verdict="INDETERMINE_NOOP", why=f"no-op ≠ a_frozen publié sur {bad} : la phase 2 n'est pas "
                                                   "reproductible, aucun contraste n'est lisible")
        return out
    try:
        assert_not_degenerate(S_a, min_spread=1.0, label="S_a (bassin gelé, 12 seeds)")
        degenere = None
    except PreflightError as exc:
        degenere = str(exc)
    if out["S_a_median"] < harness_min or degenere:
        out.update(verdict="INDETERMINE_HARNAIS",
                   why=f"S_a médiane {out['S_a_median']:.1f} (seuil {harness_min}) ; dégénérescence : {degenere}")
        return out
    bad = [(r["seed"], k) for r in rows for k in ks if not r[f"repl_{k}"]]
    if bad:
        out.update(verdict="INDETERMINE_REPLICATION",
                   why=f"rejeu ≠ publié (chemin, âges, dose ou résurrections) : {bad[:6]}")
        return out
    bad = [(r["seed"], k) for r in rows for k in ks if not r[f"transplant_ok_{k}"]]
    if bad:
        out.update(verdict="INDETERMINE_TRANSPLANT",
                   why=f"W greffé dans des clones frais ≠ objets appris : {bad[:6]} -- W n'est pas le seul porteur")
        return out
    worst = max([float(r["match_eps"]) for r in rows] + [float(r[f"match_{s}_{k}"]) for r in rows for k in ks
                                                          for s in SHAMS + tuple(echelles) + ("sign_commun",)])
    if worst > match_tol:
        out.update(verdict="INDETERMINE_APPARIEMENT", why=f"écart L1 max {worst:.3g} > {match_tol}")
        return out
    if out["controles"]["pos"]["classe"] != "ERODE":
        out.update(verdict="INDETERMINE_INSTRUMENT",
                   why=f"contrôle positif de FRAGILE : bruit à {POS_REL} × ‖W_bassin‖₁ -> "
                       f"{out['controles']['pos']['classe']} ; l'instrument ne sait pas voir une érosion par "
                       "perturbation, FRAGILE est inatteignable")
        return out
    if "full" in ks and out["par_bras"]["full"]["transplant"]["classe"] != "ERODE":
        out.update(verdict="INDETERMINE_PREMISSE", why="le transplant de b_full n'érode pas : rien à contraster")
        return out
    if out["controles"]["eps"]["classe"] == "ERODE":
        out.update(verdict="LU", lecture_globale="CRETE_A_TOUTE_ECHELLE",
                   why=f"eps (signes tirés sur le support du crédit à {EPS_SCALE} de son amplitude) ÉRODE : "
                       f"{out['controles']['eps']['mediane']:+.1f} — le bassin perd sa survie sous une perturbation "
                       "infime ; lectures par bras publiées, aucune lecture d'amplitude")
        return out
    if "full" in ks and not out["controles"]["eps"].get("moins_erode_que_le_credit_complet"):
        out.update(verdict="INDETERMINE_INSTRUMENT",
                   why="contrôle positif de DIRECTION : eps n'est pas nettement moins érodé que le crédit complet "
                       f"({out['controles']['eps'].get('contraste_positifs')}, médiane "
                       f"{out['controles']['eps'].get('contraste_mediane'):+.1f}) ; le contraste apparié ne sait pas "
                       "voir un écart connu, DIRECTION est inatteignable")
        return out
    lect = {k: out["par_bras"][k]["sign"]["lecture"] for k in ks}
    erod = [k for k in ks if out["par_bras"][k]["transplant"]["classe"] == "ERODE"]
    # 10bis. Garde E19 : l'écart sham − crédit de la voie épisodique ne survit pas au pas ×10 -> ses bras érodés
    # sont DIRECTION_DEPEND_DU_REGLAGE (la lecture d'avant est publiée à côté).
    if out["e19"] is not None and out["e19"]["lisible"] and not out["e19"]["invariant"]:
        for k in E19_PAIRE:
            if k in erod:
                out["par_bras"][k]["sign"]["lecture_avant_E19"] = lect[k]
                out["par_bras"][k]["sign"]["lecture"] = lect[k] = "DIRECTION_DEPEND_DU_REGLAGE"
    dep = [k for k in erod if lect[k] == "DIRECTION_DEPEND_DU_REGLAGE"]
    nt = [k for k in erod if lect[k] == "NON_TRANCHE"]
    fr = [k for k in erod if lect[k] == "FRAGILE"]
    di = [k for k in erod if lect[k] in ("DIRECTION", "PARTIEL")]
    if erod and len(fr) == len(erod):
        glob = "FRAGILE"
    elif erod and len(di) == len(erod):
        glob = "DIRECTION"
    elif fr and di and not dep and not nt and max(out["par_bras"][k]["net_l1_median_agent"] for k in di) < \
            min(out["par_bras"][k]["net_l1_median_agent"] for k in fr):
        # revue v5 P7.1 : la même partition peut être celle de la LÉTALITÉ de phase 1 -- alors rien n'est attribué
        glob = "MIXTE_AMPLITUDE_OU_LETALITE" if _partition_letale(out["par_bras"], fr, di) else "MIXTE_PAR_AMPLITUDE"
    else:
        glob = "MIXTE"
    out["partition_par_letalite"] = (_partition_letale(out["par_bras"], fr, di) if fr and di else None)
    bandes = [k for k in ks if out["par_bras"][k]["sign"].get("dans_la_bande")]
    bandes_a = [k for k in ks if out["par_bras"][k]["sign"].get("dans_la_bande_vs_S_a")]
    satur = [k for k in ks if out["par_bras"][k]["qualificatifs"]["suffisance_seulement"]]
    plancher = [k for k in ks if lect[k] == "FRAGILE" and not out["par_bras"][k]["qualificatifs"]["au_dela_du_plancher_eps"]]
    nondef = [k for k in ks if out["par_bras"][k]["sign"].get("defendu_contre_le_pas") is False
              and lect[k] in ("DIRECTION", "PARTIEL")]
    degen = [k for k in ks if out["par_bras"][k]["sign"].get("contraste_degenere")]
    sensibles = [k for k in ks if not out["secondaire_commun"][k]["meme_issue_que_sign"]]
    ctl = out["controles"]["eps"]
    ctl_bandes = [c for c in ("eps", "pos") if out["controles"][c].get("dans_la_bande_vs_S_a")]
    # Master 2 : une lecture de la paire E19 non défendue contre le pas se lit AVANT les lectures, jamais après
    tete = (f"NON DÉFENDU contre le pas (garde E19 illisible par construction : b_tdoff saturé) — lectures "
            f"DIRECTION/PARTIEL de la paire : {nondef} ; " if nondef else "")
    # revue v8 P8.1 (Master 2) : le vote social moyenne les sorties des clones co-localisés ; des signes tirés
    # indépendamment par agent y sont atténués plus que le crédit, cohérent entre clones -- un biais VERS DIRECTION,
    # dit en TÊTE du motif de toute lecture DIRECTION/PARTIEL, avec le tirage à signes partagés qui l'encadre
    dirs = [k for k in ks if lect[k] in ("DIRECTION", "PARTIEL")]
    out["biais_vote_vers_direction"] = dirs
    tete += (f"BIAIS POSSIBLE du vote social VERS DIRECTION (tirages indépendants par agent atténués par la moyenne du "
             f"vote plus que le crédit cohérent ; encadré par le tirage à signes partagés, `secondaire_commun`) — lectures "
             f"DIRECTION/PARTIEL : {dirs} ; " if dirs else "")
    out.update(verdict="LU", lecture_globale=glob,
               why=tete + "; ".join(f"{k} {lect[k]} (net {out['par_bras'][k]['net_l1_median_agent']:.1f}/agent, "
                             f"résurrections {out['par_bras'][k]['resurrections_phase1_median']:.1f}, "
                             f"sign−tr {out['par_bras'][k]['sign']['contraste_vs_transplant_mediane']:+.1f} "
                             f"{out['par_bras'][k]['sign']['contraste_positifs']})" for k in ks)
               + (" ; partition FRAGILE/DIRECTION identique à celle de la LÉTALITÉ de phase 1 : amplitude et létalité "
                  "non séparées" if out["partition_par_letalite"] else "")
               + (" ; contrôle de DIRECTION NON ÉPROUVÉ par construction (9b = écart de la branche 8 + écart d'eps au "
                  f"no-op ; eps inerte : {ctl.get('eps_inerte')})" if ctl["controle_direction_non_eprouve"] else "")
               + (f" ; contrôles contre S_a DANS leur bande de tirage : {ctl_bandes}" if ctl_bandes else "")
               + (" ; contraste 9b (eps − greffe complète) DANS sa bande de tirage" if ctl.get("dans_la_bande") else "")
               + (f" ; contraste sign−greffe DANS sa bande de tirage : {bandes}" if bandes else "")
               + (f" ; sham sign contre S_a DANS sa bande de tirage : {bandes_a}" if bandes_a else "")
               + (f" ; contraste sign−greffe DÉGÉNÉRÉ (aucune dispersion) : {degen}" if degen else "")
               + (f" ; issue du tirage SENSIBLE à la cohérence inter-agents (signes partagés : autre classe ou autre "
                  f"MOINS) : {sensibles}" if sensibles else "")
               + (f" ; FRAGILE à saturation (SUFFISANCE seulement) : {satur}" if satur else "")
               + (f" ; FRAGILE sans érosion au-delà du plancher eps : {plancher}" if plancher else ""))
    return out


# --------------------------------------------------------------------------------------------------
# Pré-vol à réponse connue (sans monde, sauf la ligne marquée).
# --------------------------------------------------------------------------------------------------


def _rng_state_digest():
    import random
    import torch
    h = hashlib.sha256()
    h.update(repr(random.getstate()).encode())
    st = np.random.get_state()
    h.update(st[1].tobytes())
    h.update(repr(st[2:]).encode())
    h.update(torch.get_rng_state().numpy().tobytes())
    return h.hexdigest()


def preflight_shams(seed=2026, B=3, N=8):
    """Machinerie des shams à RÉPONSE CONNUE, sans monde : (a) signes forcés à +1 -> ΔW rendu au bit ; (b) L1, L2
    et L∞ du sham `sign` égaux à ceux de ΔW ; (c) `iso` à la L1 cible à 1e-12 près ; (d) apply_delta(W0, Wf − W0) ==
    Wf au bit ; (e) aucun tirage ne touche l'état global (numpy / random / torch) ; (f) flux reproductible et
    distinct par tirage. Lève PreflightError si un point ment ; rend la mesure publiée."""
    from tools.experiment_preflight import PreflightError
    rng0 = np.random.default_rng(12345)                                   # données de test, flux privé
    W0 = rng0.standard_normal((N, N)).astype(np.float32)
    Wf = (W0[None] + 0.1 * rng0.standard_normal((B, N, N))).astype(np.float32)
    dW = Wf.astype(np.float64) - W0.astype(np.float64)[None]
    before = _rng_state_digest()

    class _SignesDuCredit:
        """Flux truqué qui rend les signes de ΔW lui-même : le sham `sign` doit alors rendre ΔW au bit."""
        def integers(self, lo, hi, size):
            return (dW >= 0.0).astype(np.int64)

    ident = sham_delta(dW, "sign", _SignesDuCredit())
    s = sham_delta(dW, "sign", sham_rng(seed, "b_full", "sign", 0))
    i = sham_delta(dW, "iso", sham_rng(seed, "b_full", "iso", 0))
    s_again = sham_delta(dW, "sign", sham_rng(seed, "b_full", "sign", 0))
    s_other = sham_delta(dW, "sign", sham_rng(seed, "b_full", "sign", 1))
    after = _rng_state_digest()
    checks = {
        "sign_identity_returns_dW": bool(np.array_equal(ident, dW) and np.array_equal(apply_delta(W0, ident), Wf)),
        "sign_norms_exact": bool(np.allclose(l1_per_agent(s), l1_per_agent(dW), rtol=0, atol=1e-9)
                                 and np.allclose(np.abs(s), np.abs(dW), rtol=0, atol=0)),
        "iso_l1_matched": bool(np.allclose(l1_per_agent(i), l1_per_agent(dW), rtol=1e-12, atol=0)),
        "apply_delta_bit_exact": bool(np.array_equal(apply_delta(W0, dW), Wf)),
        "global_rng_untouched": before == after,
        "stream_reproducible": bool(np.array_equal(s, s_again)),
        "streams_distinct": bool(not np.array_equal(s, s_other)),
    }
    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        raise PreflightError(f"preflight_shams : machinerie en défaut {failed} -- aucune cellule ne doit être lancée")
    return checks


def _horodatage(t=None):
    return (_dt.datetime.fromtimestamp(t) if t is not None else _dt.datetime.now()).isoformat(timespec="seconds")


def _charge():
    """Charge machine au moment de l'appel (E12 sur le coût) : CPU total et processus python vivants."""
    try:
        import psutil
        n = sum(1 for p in psutil.process_iter(["name"]) if "python" in (p.info["name"] or "").lower())
        return {"cpu_percent_1s": psutil.cpu_percent(interval=1.0), "python_procs": n, "t": _horodatage()}
    except Exception as exc:                                  # noqa: BLE001 -- charge inconnue, jamais inventée
        return {"cpu_percent_1s": None, "python_procs": None, "error": str(exc), "t": _horodatage()}


def _neutraliser_kuzu():
    """Processus OUVRIER : l'async_logger et le memory_retriever ne démarrent jamais (motif de
    tools/lethality_curriculum.py:36 et tools/evo_memory_inworld.py:80) — KuzuDB n'admet qu'un écrivain par
    fichier. Aucune mesure n'en dépend SI le rejeu reste bit-identique au publié : c'est la branche 4 de la règle
    qui le vérifie sur chaque cellule, jamais cette docstring."""
    from src.graph_rag.async_logger import logger as al
    from src.graph_rag.memory_retriever import AsyncMemoryRetriever
    al._running = False
    al.start = lambda *a, **k: None
    al.emit = lambda *a, **k: None
    al.emit_sync = lambda *a, **k: False
    AsyncMemoryRetriever.start = lambda self: None


def _ouvrier_init():
    _neutraliser_kuzu()


def _tache_cellule(seed, arm, ticks_learn, ticks_test):
    """Processus OUVRIER : une cellule (bras, seed). Rend le JSON de cellule SANS W (le parent ne lit que des mesures)."""
    rec = cellule(seed, arm, ticks_learn=ticks_learn, ticks_test=ticks_test)
    return {k: v for k, v in rec.items() if k != "W_final"}


def _seed_path(seed, root=None):
    return os.path.join(cells_dir(root), f"seed_{int(seed)}.json")


def cellules_manquantes(seed, arms=ARMS, root=None):
    """Les (bras) dont la cellule de ce seed n'est PAS sur le disque (JSON ou npz absent)."""
    d = cells_dir(root)
    return [a for a in arms if not (os.path.exists(os.path.join(d, f"{a}_{int(seed)}.json"))
                                    and os.path.exists(os.path.join(d, f"{a}_{int(seed)}.npz")))]


def _cellule_relue(seed, arm, num_agents=12, ticks_learn=2000, ticks_test=200):
    """`cellule` en RELECTURE SEULE : une cellule absente LÈVE au lieu d'être rejouée (revue v5 P10.b)."""
    def _refus(*_a, **_k):
        raise RuntimeError(f"seed {seed} : cellule {arm} absente -- la commande seed ne rejoue JAMAIS une phase 1 "
                           "(sur nexus, un pod ne voit que les fichiers SUIVIS : lancer les Jobs cellule, rapatrier, puis "
                           "les seeds sur la machine qui porte les cellules)")
    return cellule(seed, arm, num_agents=num_agents, ticks_learn=ticks_learn, ticks_test=ticks_test, _replay=_refus)


def verifier_seed(cell, seed, root=_ROOT, match_tol=MATCH_TOL):
    """Revue v8 P10.1 : les contrôles que la règle promet EN COURS de run -- branches 2 (no-op = a_frozen au bit), 4
    (rejeu = publié), 5 (greffe = objets appris), 6 (appariement L1) -- sur UN seed, dès qu'il est calculé. Rend la
    liste des échecs NOMMÉS (vide = conforme) ; jamais un booléen silencieux."""
    row = seed_row(cell, seed, root)
    echecs = [] if row["noop_identical"] else [f"branche 2 : no-op ≠ a_frozen (seed {seed})"]
    for a in cell["arms"]:
        k = a[2:]
        if not row[f"repl_{k}"]:
            echecs.append(f"branche 4 : rejeu ≠ publié ({a}, seed {seed})")
        if not row[f"transplant_ok_{k}"]:
            echecs.append(f"branche 5 : greffe ≠ objets appris ({a}, seed {seed})")
        for sh in SHAMS + tuple(f"sign_x{int(sc)}" for sc in ECHELLES) + ("sign_commun",):
            if not float(row[f"match_{sh}_{k}"]) <= match_tol:
                echecs.append(f"branche 6 : appariement {sh} {a} = {row[f'match_{sh}_{k}']:.3g}")
    if not float(row["match_eps"]) <= match_tol:
        echecs.append(f"branche 6 : appariement eps = {row['match_eps']:.3g}")
    return echecs


def _tache_seed(seed, ticks_learn, ticks_test):
    """Processus OUVRIER : les 167 phases 2 d'un seed, sur ses six cellules DÉJÀ calculées (RELUES, jamais rejouées :
    revue v5 P10.b — sur nexus un Job seed ne voit aucune cellule, rejouait les six phases 1 en silence, comptait
    leur coût deux fois et réécrivait des JSON de cellule en conflit au rapatriement). Refus AVANT tout monde si une
    cellule manque. Idempotente : un seed déjà écrit est relu. Le JSON de seed porte la charge au début et à la fin."""
    p = _seed_path(seed)
    if os.path.exists(p):
        rec = json.load(open(p, encoding="utf-8"))
        if rec.get("verification_en_cours"):             # revue v9 P10.a : une REPRISE relit l'échec, elle ne l'avale pas
            raise RuntimeError(f"seed {seed} : contrôle en cours de run ÉCHOUÉ à la passe précédente -- "
                               f"{rec['verification_en_cours'][:4]} ; la reprise s'arrête ici")
        return rec
    manque = cellules_manquantes(seed)
    if manque:
        raise RuntimeError(f"seed {seed} : cellules absentes {manque} -- refus avant tout monde (revue v5 P10.b)")
    start = _charge()
    out = run_fragility_seed(seed, ticks_learn=ticks_learn, ticks_test=ticks_test, _replay=_cellule_relue)
    out["load"] = {"start": start, "end": _charge()}
    out["pid"] = os.getpid()
    out["verification_en_cours"] = verifier_seed(out, seed)
    _save_json(p, out)                                        # la mesure est gardée AVANT le refus
    if out["verification_en_cours"]:
        raise RuntimeError(f"seed {seed} : contrôle en cours de run ÉCHOUÉ -- {out['verification_en_cours'][:4]} ; "
                           "le run s'arrête ici (revue v8 P10.1 : un harnais cassé ne fait pas tourner les autres seeds)")
    return out


def seuils_du_runner():
    """Les seuils EXÉCUTÉS, à confronter au bloc `seuils` de la règle scellée (revue v4 P4.2)."""
    return {"sign_min": SIGN_MIN, "n_min": N_MIN, "delta_min": DELTA_MIN, "famille": FAMILLE, "harness_min": HARNESS_MIN,
            "match_tol": MATCH_TOL, "saturation_high": SATURATION_HIGH, "e19_closure_max": E19_CLOSURE_MAX,
            "r_draws": R_DRAWS, "eps_scale": EPS_SCALE, "pos_rel": POS_REL, "echelles": list(ECHELLES),
            "workers_max": WORKERS_MAX, "bande_b": BANDE_B, "bande_q": BANDE_Q}


def verifier_seuils(rule):
    """LÈVE si un seuil exécuté diffère du bloc `seuils` de la règle scellée — jamais un commentaire."""
    scelles = rule.get("seuils")
    if not isinstance(scelles, dict):
        raise ValueError("verifier_seuils : la règle ne porte pas de bloc `seuils` -- rien ne relie le code au sceau")
    ici = seuils_du_runner()
    ecarts = {k: (scelles.get(k), v) for k, v in ici.items() if scelles.get(k) != v}
    if ecarts or set(scelles) != set(ici):
        raise ValueError(f"verifier_seuils : seuils exécutés ≠ scellés {ecarts} ; clés en trop/manquantes "
                         f"{sorted(set(scelles) ^ set(ici))}")
    return True


def bail_du_parent(owner, _read=None, _ppid=None):
    """Lancé par `tools.jobs.run.run(..., resources=["kuzu"])`, le PARENT tient déjà le bail : le re-prendre lèverait
    ResourceBusy. On ne le SUPPOSE pas : le bail `kuzu` doit exister, porter `owner`, et appartenir au processus
    PARENT (pid). Sinon LÈVE — un run ne tourne jamais sans bail. Rend le bail lu."""
    from tools.jobs import lease as _lease
    lz = (_read or _lease.read)("kuzu")
    ppid = os.getppid() if _ppid is None else _ppid
    if lz is None or lz.owner != owner or int(lz.pid) != int(ppid):
        raise RuntimeError(f"bail_du_parent : bail kuzu attendu au nom de {owner!r} tenu par le parent (pid {ppid}) ; "
                           f"lu : {lz!r} -- aucun monde ne tourne sans bail")
    return lz


def _bail(owner, budget_s):
    """Le bail kuzu de CE processus : celui du parent s'il est déclaré (SBF_BAIL_PARENT, vérifié), sinon pris ici."""
    import contextlib
    from tools.jobs.run import hold
    parent = os.environ.get("SBF_BAIL_PARENT")
    if parent:
        lz = bail_du_parent(parent)
        return contextlib.nullcontext(), {"tenu_par": "parent (tools.jobs.run)", "owner": parent, "pid": int(lz.pid)}
    return hold("kuzu", owner=owner, ttl_s=max(3600.0, budget_s * 2)), {"tenu_par": "ce processus", "owner": owner,
                                                                         "pid": os.getpid()}


def _ticks(smoke):
    return (200, 100) if smoke else (2000, 200)


def agreger(seeds, out, budget_s, rule, extra=None):
    """Lit les JSON de seed écrits (aucun calcul de monde), construit les lignes, applique le verdict scellé, et écrit
    le JSON agrégé SUIVI (cellules sans W, sha256 des W, coûts par cellule et par seed, charge, verdict)."""
    from tools.experiment_preflight import assert_control_family, declare_design
    from tools.preregister import provenance
    family = assert_control_family(cells=FAMILLE, alpha_family=0.05)
    design = declare_design(
        question=rule["question"],
        replication_unit="seed (12 clones du bassin par condition, un monde par seed ; toutes conditions appariées)",
        n_independent=len(seeds),
        links={"deplacement_net_credit": "measured", "replication_phase1": "measured", "transplant_W_seul": "measured",
               "appariement_L1": "measured", "noop_exact": "measured", "controle_positif_fragile": "measured",
               "bande_de_tirage_bootstrap": "measured", "plancher_eps": "measured",
               "survie_mortelle_poids_geles": "measured"},
        cost_estimate=rule["plafond"], control_family=family)
    data = json.load(open(out, encoding="utf-8")) if os.path.exists(out) else {}
    data.update({"preregistration": [PREREG], "design": design, "provenance_agregation": provenance(PREREG),
                 "regime": dict(REGIME_P44, arms_credit=ARM_CREDIT, arm_source=ARM_SOURCE, shams=list(SHAMS),
                                controls={"eps_scale": EPS_SCALE, "pos": POS_REL}, echelles=list(ECHELLES), r_draws=R_DRAWS, sham_entropy=SHAM_ENTROPY,
                                match_tol=MATCH_TOL, lr_low=LR_LOW, appariement="deplacement NET L1 par agent",
                                bande={"methode": "bootstrap des tirages dans chaque seed", "b": BANDE_B, "q": BANDE_Q,
                                       "entropie": BANDE_ENTROPY},
                                sham_primaire="sign", sham_secondaire_hors_verdict="iso"),
                 "seeds_declares": [int(s) for s in seeds]})
    data.update(extra or {})
    cells = {}
    for s in seeds:
        p = _seed_path(s)
        if os.path.exists(p):
            cells[str(s)] = json.load(open(p, encoding="utf-8"))
    data["cells"] = cells
    rows = [seed_row(cells[str(s)], s) for s in seeds if str(s) in cells]
    data["rows"] = rows
    data["verdict"] = fragility_verdict(rows) if rows else {"verdict": "INCOMPLET", "n": 0}
    cost = data.setdefault("cost", {})
    cost["cells_cpu_s"] = float(sum(c["cells_cpu_s"] for c in cells.values()))
    cost["seeds_phase2_cpu_s"] = float(sum(c["cpu_s"] for c in cells.values()))
    cost["cpu_total_s"] = cost["cells_cpu_s"] + cost["seeds_phase2_cpu_s"]
    cost["budget_s"] = float(budget_s)
    _save_json(out, data)
    return data


def _commande_tout(args, rule, budget_s, out):
    """Orchestration batcave : pré-vol, premier seed (6 cellules puis ses phases 2) -> unité CPU -> garde E13 ->
    66 cellules et 11 seeds en `workers` processus (un par tâche, kuzu neutralisé), plafond CPU PENDANT, agrégation."""
    from concurrent.futures import ProcessPoolExecutor, as_completed
    from tools.cost_guard import CostExceeded, project_cost
    if not 1 <= int(args.workers) <= WORKERS_MAX:
        raise ValueError(f"tout : --workers {args.workers} hors [1, {WORKERS_MAX}] -- borne scellée (plafond de contention)")
    tl, tt = _ticks(args.smoke)
    seeds = list(SEEDS_DEFAULT[:(1 if args.smoke else args.seeds)])
    owner = "s2-bassin-fragility" + ("-smoke" if args.smoke else "")
    bail, bail_info = _bail(owner, budget_s)
    execution = {"mode": "parallele" if args.workers > 1 else "serie", "workers": int(args.workers),
                 "lieu": os.environ.get("SBF_LIEU", "batcave"), "kuzu": "neutralise dans chaque processus ouvrier",
                 "bail": bail_info, "started_at": _horodatage()}
    t_start, cpu_start = time.time(), time.process_time()
    extra = {"execution": execution, "preflight": preflight_shams()}          # lève si la machinerie ment
    cost = {"load_parent_start": _charge()}
    with bail, ProcessPoolExecutor(max_workers=max(1, int(args.workers)), initializer=_ouvrier_init) as ex:
        first = seeds[0]
        cells_first = [f.result() for f in [ex.submit(_tache_cellule, first, a, tl, tt) for a in ARMS]]
        seed_first = ex.submit(_tache_seed, first, tl, tt).result()
        if not all(r["arms"][a]["cell_reloaded"] for r in [seed_first] for a in ARMS):
            raise RuntimeError("tout : les phases 2 du premier seed ont recalculé une cellule -- unité CPU faussée")
        cost["unit_cpu_s"] = float(sum(c["cpu_s"] for c in cells_first)) + float(seed_first["cpu_s"])
        cost["unit_wall_s_premier_seed"] = float(max(c["wall_s"] for c in cells_first)) + float(seed_first["wall_s"])
        cost["unit_basis"] = ("temps CPU des 6 cellules + des 167 phases 2 du premier seed, mesuré dans les processus "
                              "ouvriers (décision robla via Master 2 : projection sur le CPU)")
        extra["cost"] = cost
        agreger(seeds[:1], out, budget_s, rule, extra)       # AVANT la garde : un run REFUSÉ garde sa mesure
        cost["projected_s"] = project_cost(cost["unit_cpu_s"], n_units=len(seeds), budget_s=budget_s,
                                           label="s2-bassin-fragility (unité CPU = un seed complet)")
        print(f"[unité] {cost['unit_cpu_s']:.0f} s CPU ; projeté ×3 : {cost['projected_s'] / 3600:.2f} h CPU "
              f"(budget {budget_s / 3600:.1f} h)", flush=True)
        rest = seeds[1:]
        futs = {ex.submit(_tache_cellule, s, a, tl, tt): (s, a) for s in rest for a in ARMS}
        done_by_seed = {s: 0 for s in rest}
        seed_futs = {}
        spent = cost["unit_cpu_s"]
        try:
            for f in as_completed(list(futs)):
                s, a = futs[f]
                rec = f.result()
                spent += float(rec["cpu_s"])
                print(f"[cellule {a} {s}] S {rec['survival']['survival_median']} cpu {rec['cpu_s']:.0f}s "
                      f"| CPU cumulé {spent / 3600:.2f} h", flush=True)
                if spent > budget_s:
                    raise CostExceeded("s2-bassin-fragility (CPU cumulé)", spent, budget_s, time.time() - t_start, "cpu")
                done_by_seed[s] += 1
                if done_by_seed[s] == len(ARMS):
                    seed_futs[ex.submit(_tache_seed, s, tl, tt)] = s
            for f in as_completed(list(seed_futs)):
                r = f.result()
                spent += float(r["cpu_s"])
                print(f"[seed {seed_futs[f]}] noop {r['noop']['S']} | " + " ; ".join(
                    f"{a[2:]} tr {v['transplant']['S']} sign {v['sign']['S']} iso {v['iso']['S']}"
                    for a, v in r["arms"].items()) + f" | cpu {r['cpu_s']:.0f}s", flush=True)
                if spent > budget_s:
                    raise CostExceeded("s2-bassin-fragility (CPU cumulé)", spent, budget_s, time.time() - t_start, "cpu")
        except BaseException:
            for f in list(futs) + list(seed_futs):
                f.cancel()
            raise
    cost.update({"load_parent_end": _charge(), "elapsed_total_s": time.time() - t_start,
                 "elapsed_cpu_parent_s": time.process_time() - cpu_start, "started_at": _horodatage(t_start),
                 "finished_at": _horodatage()})
    execution["finished_at"] = _horodatage()
    return agreger(seeds, out, budget_s, rule, extra)


def main(argv=None):
    import argparse
    from src.paths import results_file
    from tools.preregister import verify

    ap = argparse.ArgumentParser(description="P4.18 S2-BASSIN-FRAGILITY")
    ap.add_argument("commande", nargs="?", default="tout", choices=("tout", "cellule", "seed", "agreger",
                                                                     "calibrer-bande"))
    ap.add_argument("--bras", choices=ARMS)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--seeds", type=int, default=int(os.environ.get("SBF_SEEDS", "12")))
    ap.add_argument("--workers", type=int, default=int(os.environ.get("SBF_WORKERS", "1")))
    ap.add_argument("--smoke", action="store_true", default=os.environ.get("SBF_SMOKE") == "1")
    args = ap.parse_args(argv)
    if args.smoke:
        os.environ["SBF_CELLS_SUFFIX"] = "_smoke"               # hérité par les processus ouvriers
    if args.commande == "calibrer-bande":                         # aucun monde, aucun sceau requis : une mesure d'outil
        mes = mesurer_couverture_bande()
        mes.update({"bande": {"methode": "bootstrap echangeable", "b": BANDE_B, "q": BANDE_Q, "entropie": BANDE_ENTROPY},
                    "provenance": {"module": "tools/evo_runs/s2_bassin_fragility.py", "fonction": "mesurer_couverture_bande"}})
        p = str(results_file("s2_bassin_fragility_calibration_bande.json"))
        _save_json(p, mes)
        print(json.dumps(mes["couverture"], ensure_ascii=False)[:600], "->", p)
        return mes
    out = os.environ.get("SBF_OUT") or str(results_file("s2_bassin_fragility" + ("_smoke" if args.smoke else "") + ".json"))
    out = out if os.path.isabs(out) else os.path.join(_ROOT, out)
    rule = verify(PREREG)                                        # AVANT toute cellule, dans CHAQUE commande
    verifier_seuils(rule)                                        # les seuils exécutés SONT ceux du sceau
    budget_s = float(os.environ.get("SBF_BUDGET_S") or rule["budget_s"])
    tl, tt = _ticks(args.smoke)
    if args.commande == "tout":
        data = _commande_tout(args, rule, budget_s, out)
        v = data["verdict"]
        print(f"\n=== P4.18 {PREREG} — n={v.get('n')} : {v.get('verdict')} | {v.get('lecture_globale')}\n"
              f"{v.get('why', '')}\n-> {out}")
        return data
    if args.commande == "agreger":
        seeds = list(SEEDS_DEFAULT[:(1 if args.smoke else args.seeds)])
        return agreger(seeds, out, budget_s, rule)
    if args.seed is None or (args.commande == "cellule" and args.bras is None):
        ap.error("cellule exige --bras et --seed ; seed exige --seed")
    preflight_shams()                                            # lève si la machinerie ment
    _neutraliser_kuzu()
    bail, _ = _bail("s2-bassin-fragility-" + args.commande, budget_s)
    with bail:
        if args.commande == "cellule":
            rec = _tache_cellule(args.seed, args.bras, tl, tt)
            print(json.dumps({k: rec[k] for k in ("seed", "arm", "cpu_s", "wall_s", "genomes")}, ensure_ascii=False))
            return rec
        r = _tache_seed(args.seed, tl, tt)
        print(json.dumps({"seed": r["seed"], "noop": r["noop"]["S"], "cpu_s": r["cpu_s"]}, ensure_ascii=False))
        return r


if __name__ == "__main__":
    main()
