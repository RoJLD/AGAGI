---
id: G1-001
type: EDR
title: "Le « transfert = noyau de survie partagé » du fil directeur est un ARTEFACT de l'entraînement MONO-monde, pas une limite de généralisation (porte G1). Instrument within-subject ([[within-subject-demand-marker]]) appliqué à la généralisation : agent 2 têtes (noyau θ-indépendant + skill world-spécifique = θ), ablation de l'entrée θ. Entraînement MONO (θ fixe) : le noyau transfère (1.00) mais le spécifique est mémorisé et échoue au transfert (0.00≈hasard), ablation-θ INERTE (Δ0.00, poids_θ 0.10) -> transfert = noyau seul. Entraînement MULTI (θ varie) : noyau ET spécifique transfèrent zéro-shot (1.00/1.00), ablation-θ EFFONDRE le spécifique (Δ0.83 -> hasard, poids_θ 1.36) -> généralisation CAUSALE. Le substrat SAIT généraliser un skill world-spécifique ; le levier = varier le monde à l'entraînement (converge CURR-001/warm-start)"
status: accepted
gate: G1
tests: [SDR-G1]
verdict: GENERALIZATION_IS_CAUSAL_SKILL_ONLY_UNDER_VARIED_TRAINING
---

# G1-001 : la généralisation est un skill causal, seulement sous entraînement varié (porte G1)

## Contexte

Le fil directeur ([[fil-directeur-agi-gates]]) : le transfert cross-world est POSITIF (champion survit 3-5× un
monde jamais vu) MAIS = **noyau de survie PARTAGÉ**, pas de compétence world-spécifique (« généralisation
parfaite ⟺ absence de spécialisation ») ; durcir la famine ne fait pas émerger de spécialisation → conclusion
« le substrat ne généralise pas de skill spécifique ». On TESTE causalement cette affirmation avec l'instrument
within-subject (S2-001/LANG-006) : le transfert positif tient-il au noyau partagé, ou à un skill spécifique
réellement réutilisé ? Et le régime d'entraînement (mono vs multi-mondes) change-t-il la réponse ?

## Méthode

`tools/generalization_transfer_probe.py` (pur numpy, standalone). Agent à DEUX têtes (softmax) sur les mêmes
entrées (contexte `c`, paramètre-monde `θ`, + biais) :
- **NOYAU** : `a_core* = c` (θ-INDÉPENDANT, identique dans tout monde) → transfère trivialement.
- **SPÉCIFIQUE** : `a_spec* = θ` (dépend du monde) → ne transfère que si l'agent LIT θ.

Régimes : **MONO** (θ fixé `θ_A` à l'entraînement → la tête spécifique peut MÉMORISER `a=θ_A` via le biais) vs
**MULTI** (θ varie → la tête spécifique DOIT lire θ). Transfert zéro-shot vers un monde `θ_B ≠ θ_A`. Marqueur
causal = **ablation de l'entrée θ** (randomisée ; `a*` reste calculé sur le vrai `θ_B`) : effondrement ⇒ skill
causalement réutilisé. Corroborant = poids de la tête spécifique sur l'entrée θ. K∈{6,8}, 8 seeds.

## Constat

| régime (K=6) | noyau | spéc. θ-vrai | spéc. θ-ablé | poids_θ | Δ ablation |
|---|---|---|---|---|---|
| MONO | 1.00 | 0.00 | 0.00 | 0.16 | 0.00 (inerte) |
| MULTI | 1.00 | 1.00 | 0.17 | 1.36 | 0.83 (effondre) |

(K=8 identique : MULTI spéc 1.00, Δ0.87 ; MONO spéc 0.00 inerte.) `VERDICT =
GENERALIZATION_IS_CAUSAL_SKILL_ONLY_UNDER_VARIED_TRAINING`.

## Lecture

- **Le noyau partagé transfère dans les deux régimes (1.00)** — c'est le « noyau de survie » du fil directeur,
  réel et θ-indépendant.
- **En entraînement MONO-monde, le transfert n'est CAUSALEMENT que le noyau.** La tête spécifique a MÉMORISÉ
  `θ_A` (via le biais) : elle échoue au transfert (spéc 0.00 ≈ hasard sur `θ_B`), et l'ablation de θ est
  **INERTE** (Δ0.00, poids_θ 0.16) → la performance de transfert ne dépend PAS de θ. C'est exactement le
  finding du fil directeur — mais l'instrument montre que c'est un **ARTEFACT du régime d'entraînement**, pas
  une incapacité du substrat.
- **En entraînement MULTI-mondes, une VRAIE généralisation émerge.** La tête spécifique lit θ : elle transfère
  zéro-shot (spéc 1.00 sur `θ_B`), et l'ablation de θ l'**EFFONDRE** au hasard (Δ0.83, poids_θ 1.36) → le skill
  world-spécifique est **causalement réutilisé**. Le substrat SAIT généraliser une compétence spécifique.
- **Le levier est le régime d'entraînement, pas la capacité.** Le même substrat mémorise (mono) ou généralise
  (multi) selon qu'il a vu ou non varier le monde. Récurrence exacte de la loi transversale
  ([[warm-start-transversal-law]], CURR-001) : le verrou est en aval de la capacité (ici : la diversité de
  l'entraînement), pas la capacité elle-même.

## Conséquences

- **Réinterprète la porte G1** : « transfert = noyau partagé » n'est PAS « le substrat ne généralise pas de
  spécialisation » — c'est « les champions étaient entraînés en MONO-monde ». La généralisation d'un skill
  world-spécifique EST atteignable sous entraînement multi-mondes. Corrige la conclusion déflationniste du fil
  directeur (155/156/157).
- **Reco in-world** : pour obtenir un transfert de compétence SPÉCIFIQUE (pas juste la survie), évoluer/
  entraîner la cohorte sur une DIVERSITÉ de mondes (curriculum multi-θ), pas un monde unique — et TESTER si le
  transfert est genuine via l'**ablation de l'entrée world-spécifique** (perception du paramètre-monde), pas
  via champion-vs-baseline. Converge la reco curriculum de CURR-001 et le transfer_ratio (axe 2 du backlog).
- **Troisième modalité de l'instrument within-subject** : perception (S2-001), communication (LANG-006),
  **généralisation (G1-001)**. Même témoin causal (ablation de l'entrée porteuse) + même corroborant (poids →
  0 quand la capacité n'est pas utilisée). L'instrument est désormais validé sur 3 portes.
- Relié : `tests: SDR-G1`. Recoupe [[within-subject-demand-marker]] + [[warm-start-transversal-law]] +
  [[fil-directeur-agi-gates]]. ID préfixé `G1-`.

## Caveats

1. Proxy SYNTHÉTIQUE et IDÉALISÉ (têtes découplées, `a_spec*=θ`, séparation nette mono/multi) : établit le
   PRINCIPE (mono mémorise / multi généralise, ablation tranche), pas des magnitudes in-world.
2. `θ_B` est dans la plage vue par MULTI (généralisation à un monde du même type, pas extrapolation à un θ
   structurellement inédit — l'encodage one-hot de θ empêche l'extrapolation à une valeur jamais vue). Le
   résultat porte sur « compétence world-conditionnelle » vs « mémorisation », pas sur l'extrapolation.
3. Têtes DÉCOUPLÉES (noyau/spécifique séparés) pour éviter le conflit additif d'une politique unique (« ignorer
   θ pour le noyau » vs « suivre θ pour le spécifique » se disputent l'argmax) ; un substrat réel à politique
   partagée devrait résoudre ce routage conditionnel (recoupe le verrou de routage/crédit, 129/136).
4. Le biais est essentiel au propre du résultat (MONO produit θ_A via le biais → poids_θ→0 → ablation vraiment
   inerte) ; sans lui, « sortie constante » passerait par la colonne-θ et brouillerait le corroborant. 8 seeds.
