"""Mondes à VÉRITÉ-TERRAIN : systèmes jouets dont la réponse est calculable ANALYTIQUEMENT, servant à
CALIBRER les instruments de mesure avant de les appliquer à l'inconnu.

Motivation (REF-EXPERIMENT-PREFLIGHT) : le déficit de rigueur de l'arc WARM-005→009 n'était pas
l'honnêteté du compte-rendu — négatifs consignés, auto-réfutations écrites, portées bornées. Il était en
AMONT : on mesurait beaucoup, sur un système sans vérité-terrain, avec des instruments jamais calibrés.
Conséquence concrète : un bug d'aliasing mémoire a PRODUIT un résultat (dose-réponse, corrélations,
contrôle négatif) qui a tenu une passe entière, parce qu'aucune mesure n'était confrontée à une réponse
connue. Sur un monde comme celui-ci, il aurait sauté en dix minutes : le ratio attendu est un rapport de
deux drains, et l'aliasing le fait dévier.

Le projet possédait déjà ce patron — S2-001 a validé le marqueur de demande sur un monde à vérité-terrain.
WARM ne l'a jamais fait. Ce module généralise la pratique.

⚠️ Un monde de vérité-terrain n'est PAS un monde réaliste : c'est un étalon. Il doit être aussi SIMPLE
que possible pour que la réponse reste calculable à la main.
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.worlds.world_1_stoneage import Biosphere3D


class GroundTruthCarryWorld(Biosphere3D):
    """Étalon pour l'instrument d'ablation `grab_off` (EDR-WARM-005/007).

    ÉCONOMIE IMPOSÉE, donc connue : chaque tick, un agent perd
        `gt_metab`                      s'il porte un inventaire VIDE
        `gt_metab + gt_carry`           s'il porte quoi que ce soit
    et RIEN d'autre — aucun revenu, aucun autre puits (`_resolve_biology` est entièrement remplacé).
    La mécanique de GRAB elle-même reste celle du monde réel : c'est l'instrument qu'on calibre, pas le
    geste. Un item est déposé sous chaque agent à chaque tick, pour qu'un grabber remplisse son
    inventaire dès le tick 1 et que la survie ne dépende pas de la chance spatiale.

    ⚠️ LEÇON DE CONSTRUCTION (l'étalon s'est trompé avant l'instrument) : remplacer `_resolve_biology`
    ne suffit PAS à contrôler le bilan énergétique. Mesuré via `trace_energy_sinks` : la phase
    `biologie` vaut bien 1.50/tick comme imposé, mais la phase **`action` en vaut 7.41** — hors de
    `_resolve_biology`, donc hors de portée de cette surcharge (plus `mouvement` 0.33, `brain` 0.01).
    Une vérité-terrain ABSOLUE exigerait de réécrire `step()` entièrement. On calibre donc par
    **PRÉDICTION** plutôt que par valeur absolue, ce qui est plus robuste et n'exige aucune hypothèse
    sur les puits non contrôlés :

        Soit D le drain « autre » (actions, mouvement, brain), inconnu mais FIXE pour un comportement
        donné et un monde déterministe. Alors, avec E l'énergie initiale :
            survie(gt_carry=0) = E / D              -> permet d'IDENTIFIER D = E / survie(0)
            survie(gt_carry=c) = E / (D + c)        -> PRÉDICTION vérifiable, sans paramètre libre restant

    L'instrument est calibré s'il retrouve la prédiction après identification en un seul point.
    Et le contrôle qui compte reste le **no-op EXACT** : sur un agent qui ne grabbe pas, l'ablation doit
    rendre des survies identiques ère par ère. Toute dérive y signale que l'ablation agit par un canal
    autre que le geste — c'est précisément la signature qu'avait le bug d'aliasing, passée pour un résultat."""

    gt_metab = 1.0
    gt_carry = 0.5

    @classmethod
    def identify_other_drain(cls, survival_at_zero_carry, energy0=80.0):
        """D = E / survie(gt_carry=0) — le drain non contrôlé (actions/mouvement/brain), identifié
        empiriquement en UN point. Aucune hypothèse sur sa composition."""
        return float(energy0) / max(float(survival_at_zero_carry), 1e-9)

    @classmethod
    def predict_survival(cls, other_drain, carry, energy0=80.0):
        """Prédiction SANS paramètre libre une fois D identifié : survie = E / (D + carry)."""
        return float(energy0) / (float(other_drain) + float(carry))

    def _resolve_biology(self, agent, action, logits):        # noqa: D102 (remplace tout le bilan)
        carry = 1.0 if agent.get("inventory") else 0.0
        agent["energy"] -= self.gt_metab + self.gt_carry * carry

    def step(self):
        for a in self.agents:                                  # item garanti sous chaque agent
            self.items.append({"x": a["x"], "y": a["y"], "z": a.get("z", 0),
                               "type": "rock", "weight": 1.0, "ttl": 10 ** 6})
        return super().step()

    @classmethod
    def expected_ablation_ratio_for_non_grabber(cls):
        """Sur un agent qui ne grabbe pas, l'ablation doit être un no-op EXACT."""
        return 1.0


def make_carry_world(carry):
    """Fabrique une sous-classe d'étalon à `gt_carry` imposé — permet de balayer le coût de portage
    pour identifier D puis vérifier la prédiction (cf. docstring de GroundTruthCarryWorld)."""
    return type(f"GroundTruthCarryWorld_c{carry}", (GroundTruthCarryWorld,), {"gt_carry": float(carry)})


# ------------------------------------------------------------------------------------------------
# POLITIQUES à vérité-terrain — l'étalon n'est pas toujours un monde : c'est parfois une POLITIQUE de
# compétence connue, qu'on injecte dans le banc réel pour vérifier qu'il sait rendre la bonne réponse.
# ------------------------------------------------------------------------------------------------

def partial_oracle(p, seed=1234):
    """Suiveur-de-signal S2-009 à FIDÉLITÉ IMPOSÉE `p` — étalon de compétence GRADUÉE.

    Avec probabilité `p` l'agent émet la direction correcte décodée de (BIT_A, BIT_B) ; sinon une des 4
    au hasard. `p=1` reproduit `CognitiveOracleBatchModel` ; `p=0` est le plancher STOCHASTIQUE (1 chance
    sur 4 de tomber juste par accident), pas un agent inerte.

    POURQUOI : sans compétence graduée, on ne peut pas distinguer « le monde n'offre aucun gradient » de
    « notre optimiseur n'en trouve pas ». WARM-002 a conclu la première à partir d'un ratio lu sur un bras
    déjà au plancher ; mesuré avec cet étalon, la fitness récompense la compétence PARTIELLE de façon
    strictement monotone (9.0 → 200.0 pour p = 0 → 1, sans chevauchement d'ères).

    ⚠️ PORTÉE : gradient dans l'espace des COMPORTEMENTS. Ne dit rien de son ATTEIGNABILITÉ par mutation
    de `genome.W` — c'est une question distincte, et ouverte."""
    import numpy as np
    from src.agents.baseline_models import BaselineBatchModel

    BIT_A, BIT_B = 12, 13                  # miroir de tools.cognitive_demand_inworld (import circulaire)

    class _PartialOracle(BaselineBatchModel):
        _rng = np.random.default_rng(seed)
        fidelity = float(p)

        def _logits(self, batch_obs):
            logits = np.zeros((self.B, self.O), dtype=np.float32)
            a = batch_obs[:, BIT_A] if batch_obs.shape[1] > BIT_A else np.ones(self.B)
            b = batch_obs[:, BIT_B] if batch_obs.shape[1] > BIT_B else np.ones(self.B)
            good = (2 * (a > 0) + (b > 0)).astype(int)
            rand = self._rng.integers(0, 4, size=self.B)
            dirs = np.where(self._rng.random(self.B) < self.fidelity, good, rand)
            for i in range(self.B):
                logits[i, int(dirs[i])] = 1.0
            return logits

    return _PartialOracle


class GroundTruthPerceptionWorld(Biosphere3D):
    """Étalon pour la branche `ablate_kind="perception"` de `_torch_survival_eras` (P2.1).

    C'est la branche qui porte les ratios PUBLIÉS de WARM-001 (1.6→2.1) et WARM-003 (5.04), et elle
    n'avait AUCUN cas de calibration — le trou le plus ancien du cliquet.

    PRINCIPE : la DOSE est `cog_gain`, c'est-à-dire ce que rapporte suivre le signal. Elle est déjà un
    bouton du monde réel, donc on ne simule rien — on impose seulement l'amplitude du payoff perceptif.
      * dose 0   -> la perception ne paie RIEN -> l'ablation doit être INERTE (spécificité) ;
      * dose forte -> l'ablation doit EFFONDRER la survie (contrôle positif) ;
      * entre les deux -> monotone (direction).

    ⚠️ LE PIÈGE QU'IL FALLAIT ÉVITER, et qui a produit quatre records défectueux (EDR-AUDIT-001) : en
    régime `cognitive_demand`, tous les revenus corporels sont gatés OFF, donc à dose 0 **tout le monde
    meurt au plancher** et le ratio 1.0 serait DÉGÉNÉRÉ, pas inerte. Un no-op ne se démontre que sur une
    métrique VIVANTE. D'où `gt_income` : un revenu corporel plat, obs-INDÉPENDANT, qui maintient la
    survie au-dessus du plancher sans jamais récompenser la perception. Le bras de spécificité mesure
    alors vraiment « l'ablation ne fait rien », et non « rien ne fait rien ».

    ⚠️ On n'impose PAS le bilan absolu : la phase `action` draine ~7.41/tick HORS de `_resolve_biology`
    (leçon de `GroundTruthCarryWorld`). On appelle donc `super()` et on n'ajoute qu'un revenu — la
    calibration est RELATIVE (inertie / effondrement / monotonie), jamais en valeur absolue."""

    gt_income = 6.0        # revenu corporel plat par tick (obs-indépendant) : garde la métrique VIVANTE

    def _resolve_biology(self, agent, action, logits):        # noqa: D102
        super()._resolve_biology(agent, action, logits)       # conserve le payoff cognitif réel (cog_gain)
        agent["energy"] = min(self.config.agent.energy_max, agent["energy"] + self.gt_income)


def make_perception_world(cog_gain, income=6.0, metab=0.75):
    """Fabrique un étalon perceptif à DOSE imposée. `cog_gain=0` = la perception ne paie rien."""
    def _make():
        e = GroundTruthPerceptionWorld()
        e.config.cognitive_demand = True
        e.config.cog_gain = float(cog_gain)
        e.config.base_metabolism = float(metab)
        e.config.forage_payoff = 0.0
        return e
    _make.gt_income = float(income)
    return type(f"GTPerception_g{cog_gain}_i{income}", (GroundTruthPerceptionWorld,),
                {"gt_income": float(income), "_gt_cog": float(cog_gain), "_gt_metab": float(metab),
                 "__init__": _gt_perception_init})


def _gt_perception_init(self, *a, **kw):
    GroundTruthPerceptionWorld.__init__(self, *a, **kw)
    self.config.cognitive_demand = True
    self.config.cog_gain = self._gt_cog
    self.config.base_metabolism = self._gt_metab
    self.config.forage_payoff = 0.0


# ------------------------------------------------------------------------------------------------
# SP-3 — MONDE-JOUET À GATE IMPOSÉ (étalon pour la sonde de récupération de prérequis).
# Pur numpy, aucune sous-classe Biosphere3D — même esprit que `partial_oracle` : une réponse CONNUE
# PAR CONSTRUCTION. L'acquisition d'un topic B est gatée sur ses prérequis ; un transfert d'ancêtre
# fabrique la CORRÉLATION entre un vrai prérequis et un non-prérequis, pour tester la spécificité.
# ------------------------------------------------------------------------------------------------

def fixture_world():
    """Overlay du monde-jouet SP-3 (compétences/ancêtres imposés) — SOURCE UNIQUE, importée par les
    tests, le cliquet de calibration et le CLI. Les compétences sont des paramètres IMPOSÉS, distincts
    des données os-taxonomy (qui ne portent que la structure d'arêtes)."""
    return {
        "income": 0.1, "hard_w": 0.4, "soft_w": 0.2,
        "own": {"B_matter_movement": 1.0, "Ah_food_chains": 0.1, "As_biodiversity": 1.0,
                "Aprime_rainforest_web": 0.1, "Z_producers": 1.0},
        "ancestor": {"Ah_food_chains": "Z_producers", "Aprime_rainforest_web": "Z_producers"},
        "transfer": {"Ah_food_chains": 0.9, "Aprime_rainforest_web": 0.9},
    }


def effective_competence(node_id, world, zeroed=()):
    """Compétence effective d'un nœud, avec UN niveau de transfert d'ancêtre.

    `zeroed` : ensemble de nœuds ABLATÉS chirurgicalement -> compétence forcée à 0.0. C'est le canal
    de l'ablation within-subject : retirer la compétence à un nœud, sans toucher aux autres."""
    if node_id in zeroed:
        return 0.0
    own = float(world["own"].get(node_id, 1.0))
    anc = world.get("ancestor", {}).get(node_id)
    if anc is not None:
        own += float(world.get("transfer", {}).get(node_id, 0.0)) * effective_competence(anc, world, zeroed)
    return max(0.0, min(1.0, own))


def acquisition_prob(subgraph, world, zeroed=()):
    """Probabilité par pas d'acquérir le topic cible, GATÉE par construction sur ses prérequis :
    income (revenu plat obs-indépendant, garde la métrique VIVANTE) + hard_w*moyenne(eff des prérequis
    DURS) + soft_w*moyenne(eff des prérequis MOUS). Bornée [0,1]."""
    def _mean(ids):
        return sum(effective_competence(i, world, zeroed) for i in ids) / len(ids) if ids else 0.0
    p = (float(world["income"])
         + float(world["hard_w"]) * _mean(subgraph["hard"])
         + float(world["soft_w"]) * _mean(subgraph["soft"]))
    return max(0.0, min(1.0, p))


def acquisition_scores(subgraph, world, seeds, zeroed=(), T=200):
    """Score d'acquisition par seed = Binomial(T, p) — T pas, chacun réussit avec proba p. La variance
    inter-seeds rend la métrique NON dégénérée ; `p` est fixe pour un `zeroed` donné (déterministe)."""
    import numpy as np
    p = acquisition_prob(subgraph, world, zeroed)
    return [int(np.random.RandomState(int(s)).binomial(int(T), p)) for s in seeds]


# ------------------------------------------------------------------------------------------------
# CALIB-ALIAS — GÉNOME-ÉTALON D'ALIASING FONCTIONNEL. Câblé à la main, injecté dans le VRAI
# recurrent_forward (même esprit que partial_oracle). Deux capacités : X (in 0 -> hA -> out_X) et
# Y (in 1 -> hB -> out_Y). `alpha` dose une FUITE de X vers out_Y (in 0 -> hS -> alpha*out_Y). À
# alpha=0 les capacités sont DISJOINTES : ablater X est un no-op EXACT sur out_Y. Réponse connue par
# construction. Layout : [0:I] entrées, [I:N-O] cachés, [N-O:N] sorties ; W[i,j] = source i -> cible j.
# ------------------------------------------------------------------------------------------------

def make_aliasing_genome(alpha):
    """Génome-étalon à DOSE de partage `alpha` (I=2, O=2, N=7). Voir en-tête de section pour le câblage.
    Diagonale = 0 (forget-gate δ=0.5). Reflex (MCTS off) -> 1 micro-tick par appel de recurrent_forward."""
    import numpy as np
    from src.seed_ai.mutation import Genome
    I, O, N = 2, 2, 7
    W = np.zeros((N, N), dtype=np.float32)
    W[0, 2] = 1.0          # X -> hA
    W[2, 5] = 1.0          # hA -> out_X
    W[1, 3] = 1.0          # Y -> hB
    W[3, 6] = 1.0          # hB -> out_Y
    W[0, 4] = 1.0          # X -> hS
    W[4, 6] = float(alpha)  # hS -> out_Y (dose de fuite : 0 = disjoint)
    return Genome(W, I, O)
