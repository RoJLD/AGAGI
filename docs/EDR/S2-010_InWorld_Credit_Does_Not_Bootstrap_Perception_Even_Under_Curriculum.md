---
id: EDR-S2-010
type: EDR
title: "Le crédit in-world ne bootstrappe PAS la perception, même sous curriculum — le verrou isolé de bout en bout"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
S2-009 a RÉALISÉ la recette in-world : l'oracle prouve que le monde `cognitive_demand` EXIGE la perception
(survie 21× sous ablation), et la sonde crédit à froid montre que le crédit in-world ne l'apprend pas
(cohorte `use_torch_inworld` plate ~7). Suite naturelle : un WARM-START / CURRICULUM franchit-il le
bootstrap, comme le prédit la loi warm-start ?

## Méthode
`tools/cognitive_demand_inworld.py::run_warmstart_credit_probe` : UNE cohorte PERSISTÉE (mêmes objets
MambaAgent → `genome.W` accumule l'apprentissage, sync world_1) traverse un `schedule` de
(base_metabolism, cog_gain) du FACILE au DUR, avec `use_torch_inworld` (REINFORCE intra-vie) à chaque
étape. Deux curricula : **CURRICULUM_COG** (cog annelé 40→12, metab dur 0.75 fixe) et **CURRICULUM_METAB**
(metab 0.25→0.75, cog 12 fixe). Franchi ssi la survie à l'étape finale (dure) ≫ plancher froid (~7).

## Résultats

| protocole | trajectoire survie médiane | survie finale (dure) | franchi ? |
|---|---|---|---|
| FROID (S2-009, rappel) | plate ~7 sur 6 ères | 7 | NON |
| CURRICULUM_COG (cog 40→12) | 12, 8, 8, 8, 8, 8 | 8 | **NON** |
| CURRICULUM_METAB (metab 0.25→0.75) | 21, 13, 11, 8, 7, 7 | 7 | **NON** |

Même à cog=40 (récompense énorme) ou metab=0.25 (facile), la cohorte fraîche ne dépasse pas ~12-21 (elle
ne suit PAS le signal) et ne l'apprend pas : la survie décroît vers le plancher (~7) dès que le régime
durcit. AUCUN curriculum ne franchit le bootstrap.

## Verdict
**`INWORLD_CREDIT_DOES_NOT_BOOTSTRAP_PERCEPTION`** — le crédit in-world (REINFORCE intra-vie via
`use_torch_inworld`) ne découvre PAS la carte signal→action depuis zéro, ni à froid ni sous curriculum
(cog-annelé OU metab-rampe). Combiné à S2-009 (l'oracle prouve que le monde EXIGE la perception, 21×), ça
**isole le verrou de bout en bout, IN-WORLD** : ce n'est ni le monde (résolu par la recette), ni le
substrat (l'oracle montre qu'une politique lisant le signal survit trivialement) — c'est le **CRÉDIT** qui
ne convertit pas la structure de tâche en comportement. Réalisation in-world directe du fil directeur
« verrou = crédit means→ends » ([[decisive-substrate-thesis-test]]).

## Portée & limites — et le prochain test décisif
Les curricula testés sont des SCHEDULES de tâche (varier metab/cog), PAS un bassin de POIDS pré-formé. La
loi warm-start ([[warm-start-transversal-law]]) prédit qu'un **warm-start des POIDS** (initialiser `genome.W`
vers une politique signal-suiveuse, p.ex. copier l'oracle, puis laisser le crédit RETENIR/affiner) —
franchirait là où le schedule échoue. C'est le prochain test décisif, désormais outillé : injecter un
génome oracle-like comme init, mesurer si le crédit le retient sous ablation. Autres pistes : épisodes plus
longs à faible metab pour accumuler des pas d'apprentissage ; crédit dense (shaping visée) comme le
throw-gate EDR-173. Borné : REINFORCE 1-pas `learn_episode`, cohorte 12, 200 ticks/étape.
Converge S2-009, REF-DEMAND-MARKER, [[warm-start-transversal-law]], [[fil-directeur-agi-gates]].
