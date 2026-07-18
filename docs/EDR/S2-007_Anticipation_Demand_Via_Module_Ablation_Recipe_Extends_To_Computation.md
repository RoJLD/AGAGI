---
id: EDR-S2-007
type: EDR
title: "Demand-marker par ablation de MODULE : l'anticipation (G4) — la recette s'étend aux capacités-calcul"
status: active
gate: G4
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
EDR-S2-006 posait la frontière : le demand-marker (ablation d'INPUT) couvre perception/mémoire/comm, mais
les capacités-CALCUL (anticipation, composition) exigent une ablation de MODULE. Cet EDR RÉALISE le 1er
jalon de l'arc module-ablation : l'anticipation (G4).

## Méthode
`tools/anticipation_demand_world_probe.py` (pur numpy). Mini-sim survie : CORPS (réflexe a=0 → +body_gain)
+ ANTICIPATION (la nourriture visée paie = shift(état courant s_t) ; l'agent OBSERVE s_t — donc ni demande
perceptive ni mémoire — mais doit APPLIQUER un forward-model M = la dynamique connue s→shift(s) pour viser
le FUTUR). Module INTACT : pred = M·obs ≈ one-hot(shift(s_t)) ; **ablation de MODULE** : pred = obs
(identité, réactif) → vise s_t ≠ shift(s_t) → rate. Politique entraînée (hill-climb, module intact) à
maximiser la survie ; témoin = ablation du module (M→identité, within-subject, demand_marker). Grille
(corps × dynamique × devise), metab=1.0, cog_gain=2.0, 8 seeds, K=5, ticks=300. Contrôle shift=0
(statique) : le réactif suffit → ablation inerte.

## Résultats

| cellule | ratio | verdict |
|---|---|---|
| corps SUFFISANT (1.2) + dynamique (shift1) + énergie | 1.00 | SURVIVAL_NEUTRAL |
| **corps INSUFFISANT (0.5) + dynamique (shift1) + énergie** | **16.23** | **SURVIVAL_ANTICIPATION_SENSITIVE** |
| corps INSUFFISANT (0.5) + STATIQUE (shift0) + énergie | 1.00 | SURVIVAL_NEUTRAL |
| corps INSUFFISANT (0.5) + dynamique (shift1) + devise séparée | 1.00 | SURVIVAL_NEUTRAL |

Une SEULE cellule est anticipation-SENSIBLE : corps INSUFFISANT + dynamique + énergie (effondrement ~16×).

## Verdict
**`ANTICIPATION_DEMAND_VIA_MODULE_ABLATION`** — la survie in-world exige l'ANTICIPATION (application d'un
forward-model) SSI (1) corps INSUFFISANT, (2) dynamique NON-triviale (la conséquence survie est dans le
FUTUR, shift≠0 — l'analogue « demande structurée » de S2-006 pour le calcul), (3) devise de survie. **La
recette générale (EDR-S2-006) tient donc AUSSI pour les capacités-CALCUL** ; seul l'instrument change
(ablation de MODULE au lieu d'INPUT). L'anticipation (G4) est causalement instrumentée : couper le
forward-model effondre la survie 16× quand la tâche l'exige, est inerte sinon.

## Portée & limites
Forward-model = ORACLE (dynamique vraie donnée) — teste la DEMANDE d'anticipation (la tâche exige-t-elle
un modèle), pas l'APPRENABILITÉ du modèle (couverte par PLAN-002). Sim fidèle au mécanisme (application de
transition sur l'obs courante), pas la biosphère. La COMPOSITION (G2, chaînage) est le prochain jalon
module-ablation, mais = territoire COS //. Converge S2-004/005/006, la tétralogie PLAN (G4),
REF-DEMAND-MARKER, [[fil-directeur-agi-gates]].
