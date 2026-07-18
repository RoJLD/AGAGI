---
id: EDR-WARM-001
type: EDR
title: "Imitation récurrente BPTT : le substrat imite PARFAITEMENT l'oracle mais la survie plafonne — le mur est le SHIFT DE COVARIABLES, pas le substrat"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
Le behavioral cloning single-step avait échoué à transférer (bilan warm-start : shift de distribution). Une
IMITATION RÉCURRENTE par BPTT — matcher le forward récurrent du monde sur la distribution d'obs RÉELLE
59-dim, pas `_step` isolé — installe-t-elle un suiveur-de-signal in-world ? Et si oui, la survie décolle-t-elle
vers l'oracle (200) ? On dispose d'un enseignant PARFAIT (l'oracle S2-009) : un échec malgré teacher parfait
localiserait le verrou au-delà de la découverte.

## Méthode
`tools/warmstart_evolution_inworld.py` : (1) `imitate_episode_bptt` (backend torch, additive) rejoue une
trajectoire en RETENANT le graphe récurrent, perte = cross-entropy des move-logits vs l'action-oracle par pas,
backprop unique à travers la fenêtre ; (2) `_collect_oracle_trajectory` collecte la trajectoire-enseignant
(cohorte oracle, préfixe à B constant = 35 ticks, 420 échantillons équilibrés sur les 4 directions) ;
(3) entraînement d'une cohorte torch (12 génomes) par imitation, puis `verdict_demand_marker` (forward
**torch**, W gelé, ablation within-subject `derange_rows`, K=12 ères) sur le génome imité. Balayage
lr × epochs × fenêtre pour cartographier accuracy(imitation) → survie in-world. Régime S2-009.

## Résultats

**L'imitation converge (le substrat est CAPABLE).** Le run à budget standard (lr=0.04, 200 ep) donnait
acc=0.312 (≈ hasard 4-voies) → **sous-entraînement**, pas plafond. En poussant (lr=0.5–0.7) :

| budget imitation | acc (sur la traj. oracle) | intact | ablé | ratio | verdict marqueur |
|---|---|---|---|---|---|
| lr0.5 / 1500 ep | 0.717 | 9.8 | 6.8 | 1.44 | INCONCLUSIVE |
| lr0.5 / 4000 ep | 0.931 | 11.2 | 7.0 | 1.61 | **PERCEPTION_DEMANDED** |
| lr0.7 / 10000 ep | 0.995 | 15.0 | 7.0 | 2.14 | **PERCEPTION_DEMANDED** |
| lr0.6 / 20000 ep | **1.000** | **15.0** | 7.0 | 2.14 | **PERCEPTION_DEMANDED** |

Repères : plancher ≈ 7 ; oracle intact ≈ 200 / ablé ≈ 9 / ratio ≈ 21 (S2-009).

**Dissociation nette.** (a) Le marqueur within-subject **BASCULE en PERCEPTION_DEMANDED** dès acc≈0.93 :
le génome imité utilise CAUSALEMENT la perception (l'ablation l'effondre 11–15 → 7). (b) MAIS la survie
intacte **plafonne à 15** même à acc=**1.000**, à des années-lumière de l'oracle (200).

**La preuve du shift de covariables.** À acc=1.000, l'espérance d'erreur sur 15 ticks ≈ 0 → l'accumulation
multiplicative ne peut PAS expliquer la mort à ~15. Donc les 99–100% sont mesurés SUR LA DISTRIBUTION D'OBS
DE L'ORACLE (in-distribution) ; dès que le génome imité PILOTE SES PROPRES états, il dérive hors de cette
distribution, son accuracy réelle s'effondre, il erre et meurt. C'est le mode d'échec canonique du behavioral
cloning (que DAgger corrige), démontré ici avec une trajectoire-enseignant PARFAITE.

## Verdict
**`RECURRENT_IMITATION_SUBSTRATE_CAPABLE_BUT_COVARIATE_SHIFT_CAPS_SURVIVAL`** — PASS partiel : l'imitation
récurrente BPTT installe un utilisateur-de-perception CAUSAL (marqueur PERCEPTION_DEMANDED) mais PAS un
survivant (survie ≫ plancher = FAIL, plafond ~15 vs 200). **Réfute deux hypothèses** : (1) le substrat LTC
est CAPABLE (imite jusqu'à acc 1.000 la carte réactive sur obs réelles 59-dim → ce n'est ni un plafond de
représentation ni de capacité) ; (2) ce n'est pas la DÉCOUVERTE qui manque (l'enseignant est parfait). Le mur
restant est le **SHIFT DE COVARIABLES** : l'accuracy sur la distribution de l'enseignant ne transfère pas à
la survie on-policy. Le levier suivant est donc MOTIVÉ par preuve directe (plus une spéculation) : correction
**on-policy** (DAgger : relabel de la distribution de l'apprenant par l'oracle) ou crédit in-world qui visite
les propres états de l'agent.

## Portée & limites
- Trajectoire-enseignant à B constant = 35 ticks (un agent oracle meurt à t≈35 → préfixe tronqué) ; 420
  échantillons équilibrés, suffisants pour la carte réactive (acc atteint 1.000). Le signal `_cog_sig` est
  re-randomisé chaque tick → tâche RÉACTIVE (cible = f(obs courante)), pas de mémoire.
- Verdict sous forward torch (consistance avec l'entraînement, anti-confound), W gelé, K=12 (garde-fou n≥12).
- `acc` = moyenne de population sur la traj. oracle ; le verdict clone `agents[0].genome` en 12. Léger écart
  possible (génome individuel vs moyenne), sans effet sur la conclusion (le plafond de survie tient à acc 1.0).
- Complémentaire de WARM-002 (évolution : paysage plat). Même cause profonde : la survie ne récompense la
  cognition qu'au-delà de ~99% d'accuracy (seuil dur, gradient quasi-nul) → converge le fil S2.

Converge [[EDR-WARM-002]], [[decisive-substrate-thesis-test]], [[warm-start-transversal-law]],
[[within-subject-demand-marker]], [[s2-world-demand-thread]], REF-DEMAND-MARKER, S2-009.
