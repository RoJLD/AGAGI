---
id: EDR-S2-005
type: EDR
title: "Recette d'un monde in-world à demande de MÉMOIRE : corps insuffisant + rappel différé + devise de survie"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
S2-004 a donné la recette pour que la survie in-world exige la PERCEPTION. Généralisation : à quelles
conditions un objectif de survie in-world exige-t-il la MÉMOIRE (rappel différé) ? Pendant constructif de
MEM-001 (proxy : la mémoire paie SSI rappel différé) dans le cadre corps+devise de S2-004.

## Méthode
`tools/memory_demand_world_probe.py` (pur numpy). Mini-sim survie : CORPS (réflexe a=0 → +body_gain,
sans mémoire) + MÉMOIRE (la bonne action nourricière = l'indice vu au tick PRÉCÉDENT ; l'agent porte un
intégrateur à fuite des indices passés = substrat FIXE, cf. MEM-001). Entrée politique = concat(obs, m)
(dim 2K). Politique entraînée (hill-climb) à maximiser la survie ; témoin = **ablation de la MÉMOIRE**
(m→0, within-subject, demand_marker). Grille (corps × mode-de-rappel × devise), metab=1.0, cog_gain=2.0,
8 seeds, K=5, ticks=300. `delayed` : obs courante = zéros (info survie seulement dans le passé → mémoire
requise) ; `present` : obs montre l'action correcte COURANTE (mémoire = seulement le passé, inutile).

## Résultats

| cellule | ratio | \|W\|mém | verdict |
|---|---|---|---|
| corps SUFFISANT (1.2) + rappel différé + énergie | 1.00 | 0.000 | SURVIVAL_NEUTRAL |
| **corps INSUFFISANT (0.5) + rappel différé + énergie** | **10.34** | **0.999** | **SURVIVAL_MEMORY_SENSITIVE** |
| corps INSUFFISANT (0.5) + rappel PRÉSENT + énergie | 1.00 | 0.909 | SURVIVAL_NEUTRAL |
| corps INSUFFISANT (0.5) + rappel différé + devise séparée | 1.00 | 0.000 | SURVIVAL_NEUTRAL |

Une SEULE cellule est mémoire-SENSIBLE : corps INSUFFISANT + rappel DIFFÉRÉ + énergie (effondrement ~10×).

## Verdict
**`MEMORY_DEMAND_REQUIRES_THREE_CONDITIONS`** — la survie in-world exige la MÉMOIRE SSI : (1) le corps est
INSUFFISANT seul (sinon plafond corps → NEUTRE) ; (2) RAPPEL DIFFÉRÉ (l'info survie n'est QUE dans le
passé, pas l'obs courante) ; (3) le succès payé dans la DEVISE de survie (énergie). Généralise la recette
S2-004 (perception) à la mémoire ; converge MEM-001.

## Bonus méthodologique — le poids |W| peut FAUX-POSITIVER
Cellule « rappel présent » : la politique PÈSE la mémoire (|W|mém = 0.909) MAIS l'ablation est INERTE
(ratio 1.00, NEUTRE) — l'obs seule suffit. Donc le corroborant de POIDS |W| n'est PAS fiable seul (ici
0.909 alors que la mémoire n'est pas porteuse) ; **le ratio d'ablation within-subject est le test causal
gold-standard**, le poids appris est nécessaire mais PAS suffisant. Recoupe S2-003 (le champion traite
l'obs à ~29 % sans que ça paie en survie). Renforce [[within-subject-demand-marker]] : préférer l'ablation
au poids.

## Portée & limites
Existence-proof + recette de design (rappel différé délai=1, intégrateur à fuite), pas la biosphère.
Portage in-world = même chantier que S2-004 (nouveau monde biosphère où corps insuffisant + canal
mémoire-food payé en énergie). Converge S2-001/002/003/004, MEM-001, REF-DEMAND-MARKER.
