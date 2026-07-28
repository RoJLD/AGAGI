---
id: EDR-MEM-PERCEPTION
type: EDR
title: "Deuxième arête candidate du graphe AGI-Taxonomy : la mémoire APPRISE demande la perception au rappel (DELAYED X_DEMANDED, ratio 3.93, n=12) — mais NON gravée : le contrôle de spécificité ÉCHOUE (l'ablation d'entrée à l'encodage n'est PAS inerte quand la réponse est présente au test, ratio 4.33 sur PRESENT aussi). Null honnête."
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER, REF-AGI-TAXONOMY]
---

## Question
SP-2 a gravé la 1ère arête (`language→perception`). Deuxième arête candidate : « memory demands perception » ?
La rétention APPRISE route-t-elle causalement par la perception ? On l'établit sur un proxy torch de rappel
différé (delayed-match-to-sample, sonde Task 1 `tools/memory_perception_demand_probe.py`), par ablation
d'ENTRÉE within-subject à l'ENCODAGE (`derange_rows` sur le one-hot d'indice, in-distribution).

## Méthode
Delayed-match torch (MambaAgent, mémoire = état récurrent PORTÉ ; `learn_episode`, crédit du rappel).
Deux conditions : DELAYED (obs de test = zéros → il faut la rétention) ; PRESENT (contrôle de demande VIVANT,
obs de test = vue directe BRUITÉE de l'indice, `flip_p`). `ablation_verdict` (floor=1/K), n=12 seeds,
`intervention_verified=True`. Sonde calibrée en Task 1 (memory oracle → effondre ; aléatoire → inerte).

**Bornage du coût** : smoke à 3 seeds (K=6, D∈{0,1,2}, episodes 300→3000, lr∈{0.02,0.05,0.1,0.2,0.3},
flip_p∈{0,0.02,0.1,0.15,0.2,0.3}) pour mesurer débit et TRAJECTOIRE des deux bras (DELAYED **et** PRESENT,
pas seulement DELAYED comme anticipé par Task 1) avant d'engager le run n=12. Retenu : K=6, D=2 (D du défaut
de la sonde, tâche non triviale conservée), lr=0.02 (convergence nettement meilleure que le défaut 0.05,
observé sur PRESENT : intact 0.39→0.68 à ep=800), episodes=1200, n_agents=16. Run n=12 exécuté en FOREGROUND,
provenance réelle (`run_memory_perception_demand_probe`, pas un pilote maison) : **372.5 s** (<9 min),
accuracies persistées `results/mem_perception_edge_accuracies.json`.

## Résultat

**DELAYED : X_DEMANDED**, ratio **3.934**, n=12. `delayed_intact` médiane **0.6547** (>> seuil vivant
1/K+0.15≈0.3167), `delayed_ablated` médiane **0.1664** (≈ hasard 1/K=0.1667). Séparation **12/12 seeds**
(intacte > ablée sur chaque seed, aucun recouvrement) — la rétention apprise EST démontrée sans ambiguïté,
et l'exploration de tuning (ci-dessus) confirme qu'elle n'est PAS un artefact de sous-entraînement : le
signal est robuste sur toute la plage explorée (ratio 1.87→5.59 selon D/lr/episodes, toujours croissant
avec l'entraînement).

**PRESENT (contrôle de spécificité) : ÉCHOUE.** `present_alive`=True (médiane intacte 0.7609, dans la
fenêtre vivante ]0.3667, 0.9[ — pas un plancher/plafond dégénéré) MAIS le verdict d'ablation sur PRESENT est
lui aussi **X_DEMANDED** (pas X_DECOY) : ratio **4.329**, `present_intact` médiane 0.7609, `present_ablated`
médiane 0.1758 — séparation **12/12 seeds** également. `specificity_control = "fail"`.

**L'ablation à l'encodage n'est donc PAS spécifique au besoin de mémoire** : elle démolit la performance
même quand la réponse est directement observable au tick de test (PRESENT), à un ratio du même ordre de
grandeur que DELAYED (4.33 vs 3.93). Impossible de distinguer « la mémoire porte causalement la perception
au rappel » de « perturber l'état récurrent nuit à la lecture de N'IMPORTE QUEL tick suivant, y compris
quand ce tick n'a pas besoin de mémoire » — exactement le confond que `specificity_control` est construit
pour attraper, et il l'attrape.

**Exploration mécaniste (pour caractériser, pas pour forcer un passage)** : le contrôle PRESENT a été
sondé directement via `_train_and_eval("present", ...)` sur 15 configurations (D∈{0,1,2} ; flip_p de 0 à
0.3 ; lr de 0.02 à 0.3 ; episodes de 300 à 3000). Dans TOUTES les configurations, le ratio PRESENT reste
entre 2.40 et 7.36 — jamais proche du seuil `decoy_ceiling=1.3`. Même à `flip_p=0` (vue de test PARFAITE,
aucune raison théorique de préférer la mémoire), `present_ablated` reste au plancher (0.15) pendant que
`present_intact` grimpe à 0.92-0.95. Deux explications structurelles cohérentes avec le code de la sonde
(non modifié, cf. Task 1) :
1. **Incitatif d'entraînement** : l'encodage est TOUJOURS intact pendant l'entraînement (l'ablation n'existe
   qu'à l'éval) — le gradient n'a donc jamais de raison de ne pas router via la mémoire (source parfaite),
   même quand la perception au test est elle aussi fiable.
2. **Substrat partagé** : l'intégrateur récurrent de `MambaAgent` (`(1-δ)·H + δ·tanh(H·W_offdiag)`) mélange
   l'ancien état (contaminé à l'encodage) avec la nouvelle observation à CHAQUE tick, y compris au tick de
   test — un seul tick de lecture ne suffit pas à « rincer » la contamination portée depuis l'encodage,
   quel que soit D. `CONDITION_GATE` (qui permettrait au réseau d'apprendre à ignorer l'état périmé) est
   désactivé par construction dans la sonde et n'est pas exposé par `run_memory_perception_demand_probe`
   (donc hors de portée du tuning autorisé pour cette tâche — ne pas modifier `tools/memory_perception_demand_probe.py`).

**Conclusion : arête `memory → perception` NON gravée.** Le seuil `delayed_intact` est franchi et DELAYED
est robustement X_DEMANDED, mais `specificity_control` échoue de façon reproductible et non marginale
(ratio ~4x le seuil de decoy sur 15 configurations) — c'est un NULL HONNÊTE sur l'axe spécificité, pas un
signal faible sur l'axe DELAYED. `data/agi_taxonomy/demands.json` reste à UNE seule arête (SP-2,
`language→perception`).

## Portée (bornée)
Proxy hors-monde (delayed-match), pas la biosphère. Mémoire = état récurrent APPRIS (pas la mémoire
tautologique de l'intégrateur numpy MEM-001, écartée à dessein). Coût borné (smoke exploratoire + run n=12
plafonné FOREGROUND 372.5 s, accuracies persistées `results/mem_perception_edge_accuracies.json`). N'a PAS
modifié `tools/memory_perception_demand_probe.py` ni `tools/check_agi_taxonomy.py` (contrainte de tâche) —
la contamination substrat-partagé documentée ci-dessus n'a donc pas pu être testée avec une ablation
alternative (ex. reset de `agent.H` entre délai et test au lieu de déranger l'encodage) ; c'est une piste
pour une itération future de la sonde, hors périmètre de cette mesure.

## Ce que ça débloque
Documente une LIMITE du pipeline SP-2 (ablation d'entrée + garde de spécificité → arête valide) quand
l'ablation touche un substrat récurrent PARTAGÉ entre le tick ablaté et TOUS les ticks suivants (contrairement
au jeu de Lewis de SP-2, à un seul tick sender→receiver sans état porté à travers un délai). Le résultat
négatif est gravé au même titre qu'un positif (cf. CLAUDE.md, section Records) : une arête `memory→perception`
mesurée exigerait soit un site d'ablation qui ne fuit pas vers le bras de contrôle (ex. reset d'état plutôt
que perturbation d'entrée), soit d'exposer `CONDITION_GATE` au tuning — les deux hors périmètre de Task 2.
Cf. `docs/superpowers/specs/2026-07-28-memory-perception-demand-edge-design.md`.
