---
id: EDR-S2-010
type: EDR
title: "Le crédit in-world ne bootstrappe PAS la perception, même sous curriculum — le verrou isolé de bout en bout"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
corrected_by: [EDR-CALIB-LEARNER]
---

> ⚠️ **PORTÉE CORRIGÉE le 2026-09-14, APRÈS mesure ([[EDR-CALIB-LEARNER]], n = 12).** Le nul de ce
> record est un nul de **DOSE** : ses agents meurent à 7-9 ticks, soit quelques dizaines de mises à
> jour de crédit — jamais comptées ici (le TD(0) par tick, `world_1_stoneage.py:1717`, n'est pas nommé
> dans la §Portée). À dose non bornée par la mort (≈ 2000 TD + 250 épisodes par agent, cohorte
> immortelle), l'apprenant tel que publié APPREND la tâche linéaire de S2-011 (12/12 seeds au-dessus de
> la référence lr=0 appariée, +0,156), lentement (0,28 vs oracle 1,0 à 2000 ticks). Les mesures de ce
> record restent vraies à leur dose ; sa conclusion « le verrou isolé de bout en bout » ne l'est plus :
> le verrou est d'abord que **l'apprenant meurt en apprenant** (126 morts par seed contre 1 pour lr=0),
> donc n'accumule jamais la dose. Classes E2 (bras qui ne peut pas réussir) et E19 (réglage validé sur le
> cas facile) — la dose est un réglage.
>
> ⚠️ **PORTÉE BORNÉE le 2026-09-15 (P3.6), APRÈS les mesures de [[EDR-S2-CREDIT-RETENTION]] et de
> [[EDR-S2-REWARD-ABLATION]] (n = 12 seeds chacune).** Le « prochain test décisif » de la §Portée —
> warm-start des POIDS, « puis laisser le crédit RETENIR/affiner » — a été exécuté : le bassin DAgger de
> [[EDR-WARM-003]] TRANSFÈRE (survie 36,0 à poids gelés, min 17,0, max 50,0 ; WARM-003 publiait 35,2 —
> même chiffre, deux harnais : [[EDR-S2-CREDIT-RETENTION]], bras a) et le crédit publié, à dose 1999 TD
> par agent, l'EFFACE : 36,0 → 8,0, 12/12 seeds, écart apparié médian −28,25 (`ERODE`), sans rien
> construire à froid (7,5 < plancher 9,0, `PAS_APPRIS_FROID`). L'érosion ne tient pas à la récompense :
> Δénergie seule érode autant (−28,5 vs −28,25, différence appariée médiane 0,0, `CREDIT_ERODE_SEUL` —
> [[EDR-S2-REWARD-ABLATION]]), et le terme de curiosité de la récompense in-world est MORT sous le
> backend torch (surprise jamais écrite ; récompense effective = Δénergie + nouveauté depuis S2-009).
> Lecture qui reste : à la dose que la mort permet (≈ 48 mises à jour par agent,
> [[EDR-S2-CREDIT-RETENTION]]), le crédit n'apprend rien ; à dose non bornée, il apprend
> ([[EDR-CALIB-LEARNER]]) quelque chose qui n'est pas la survie ([[EDR-S2-CREDIT-RETENTION]]).

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
> ⚠️ **Bandeau de portée du 2026-09-15 (P3.6) — le TD par tick n'était pas nommé, la dose n'était pas
> comptée.** L'apprenant de ce record n'est pas « REINFORCE 1-pas `learn_episode` » seul : le chemin
> réel est un Actor-Critic **TD par tick** (`src/worlds/world_1_stoneage.py:1717`) PLUS le crédit
> épisodique tous les `torch_episode_k = 8` ticks ([[EDR-CALIB-LEARNER]], § Question). Ce TD par tick
> CONTRIBUE : le couper donne la PIRE variante (2/12 seeds au-dessus de l'apprenant publié, −0,046 —
> [[EDR-CALIB-LEARNER]]). La dose de crédit reçue par les cohortes de ce record n'a jamais été comptée :
> agents morts à 7-9 ticks, soit **≈ 48 mises à jour par agent** ([[EDR-S2-CREDIT-RETENTION]], § Verdict :
> « 1999 mises à jour, contre ~48 dans S2-010/S2-011 »), contre ≈ 2000 TD + 250 épisodes là où le MÊME
> apprenant apprend la tâche linéaire (12/12 seeds, +0,156, [[EDR-CALIB-LEARNER]]). Les trois pistes
> ci-dessous ont un statut MESURÉ : warm-start des poids → bassin transféré (36,0) puis ÉRODÉ par le
> crédit (8,0, 12/12 — [[EDR-S2-CREDIT-RETENTION]]) ; épisodes plus longs pour accumuler des pas →
> c'est la dose, et elle n'est pas le verrou ([[EDR-CALIB-LEARNER]]) ; crédit dense (shaping) → non
> mesuré, mais l'ablation de la RÉCOMPENSE dit que le levier n'est pas la récompense
> ([[EDR-S2-REWARD-ABLATION]] : Δénergie seule érode autant que la récompense complète).

Les curricula testés sont des SCHEDULES de tâche (varier metab/cog), PAS un bassin de POIDS pré-formé. La
loi warm-start ([[warm-start-transversal-law]]) prédit qu'un **warm-start des POIDS** (initialiser `genome.W`
vers une politique signal-suiveuse, p.ex. copier l'oracle, puis laisser le crédit RETENIR/affiner) —
franchirait là où le schedule échoue. C'est le prochain test décisif, désormais outillé : injecter un
génome oracle-like comme init, mesurer si le crédit le retient sous ablation. Autres pistes : épisodes plus
longs à faible metab pour accumuler des pas d'apprentissage ; crédit dense (shaping visée) comme le
throw-gate EDR-173. Borné : REINFORCE 1-pas `learn_episode`, cohorte 12, 200 ticks/étape.
Converge S2-009, REF-DEMAND-MARKER, [[warm-start-transversal-law]], [[fil-directeur-agi-gates]].
