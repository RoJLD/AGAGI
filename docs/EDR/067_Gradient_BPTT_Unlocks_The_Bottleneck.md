---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-067
type: EDR
title: "Le gradient (BPTT) débloque le goulot — la découverte mécaniste centrale"
status: legacy
gate: foundational
---

# EDR 067 : Le gradient (BPTT) débloque le goulot — la découverte mécaniste centrale

## Contexte

EDR 064 : la mutation seule ne sait pas exploiter la capacité (K=6 plafonne à ~0.78 ; croissance =
bloat). Hypothèse : le **gradient (BPTT)** est le levier. On l'implémente *à la main* (numpy) et on le
teste sur le banc mémoire (rappel de K bits — auto-contenu, hors DB).

## Implémentation + validation

`tools/grad_mem.py` : forward déroulé de la dynamique récurrente (`H=(1-dt)*Hc+dt*tanh(Hc@Wnd)`,
entrées clampées) + **rétropropagation manuelle** à travers tous les ticks. Subtilité clé : le clamp
d'entrée (`Hc[:, :I]=obs`) coupe le gradient vers les nœuds d'entrée (ce sont des entrées), mais leur
valeur contribue à `dW`. Validé : **gradient check** (analytique = numérique) + **K=2 → acc 1.000**
(le gradient résout parfaitement → BPTT correct).

## Résultat 1 — le gradient DÉBLOQUE la tâche

| K (bits à retenir) | mutation (064) | **gradient** |
|---|---|---|
| 2 | — | 1.000 |
| 4 | — | 1.000 |
| **6** | **0.78** (plateau) | **1.000** |

> **Même petite architecture (N=19, 3 cachés)** : la mutation plafonne à 0.78, le gradient atteint
> **1.000**. **EDR 064 CONFIRMÉ : le goulot était la MUTATION, pas l'architecture.**

## Résultat 2 — la capacité est NON-BINDANTE

| K=8, hidden | acc gradient |
|---|---|
| 1 (N=25) | **0.998** |
| 8 (N=32) | 1.000 |
| 16 (N=40) | 1.000 |

> Même **hidden=1** résout K=8 (0.998). Les nœuds de SORTIE (récurrents, non clampés) stockent déjà
> les bits → la capacité cachée ne *binde* pas. **Le NAS était un faux problème** : on n'avait jamais
> besoin de *grandir* l'architecture, seulement de l'*optimiser* avec le bon algorithme.

## La conclusion qui UNIFIE tout (la découverte centrale)

> **La cause profonde commune des deux murs était la faiblesse de la RECHERCHE (mutation seule).**
> - Langage *barren* (057) : la mutation ne trouve pas de convention fiable.
> - NAS *bloat* (064) : la mutation n'exploite pas la capacité — et la capacité n'était même pas le
>   problème (les sorties stockent ; le gradient résout avec ce qu'il y a).
> - #8 sans frontière franche (066) : *sous mutation*, il n'y avait rien à trouver.
>
> **Le gradient est LA clé.** On a passé 60 EDR à durcir des mondes (la demande) et protéger des
> innovations (la spéciation) — alors que le vrai levier était **COMMENT L'AGENT APPREND.** C'est, de
> loin, le résultat mécaniste le plus important du projet.

## Implications

1. **Intégrer le gradient (BPTT) dans l'agent** — au-delà de la mutation + l'Actor-Critic rustre.
   C'est une refonte d'apprentissage, mais le gain est démontré (0.78→1.00, et la perfection sur des
   tâches que la mutation ne touchait pas).
2. **Le NAS devient secondaire** : avec gradient, l'architecture existante suffit largement (capacité
   non-bindante). Pas besoin de faire grandir le cerveau ; il faut l'*entraîner*.
3. **Le #8 retrouve un espace** : *sous gradient*, des tâches plus dures (où la capacité/structure
   pourraient compter) deviennent abordables — un vrai terrain où l'amélioration EXISTE.

## Statut

- `grad_mem.py` : BPTT validé, auto-contenu. Gradient = levier démontré.
- **Tournant du projet** : le goulot identifié (la recherche/apprentissage), et la clé prouvée (le
  gradient). Les 60 EDR précédents ont *cartographié honnêtement* ce qui ne marchait pas ; celui-ci
  trouve ce qui marche.

## Variables d'expérience

Algorithme (mutation vs gradient vs hybride), tâche (mémoire vs computation où la capacité binde),
intégration BPTT dans le connectome vivant, combinaison gradient + évolution (Baldwin), framework
(numpy manuel vs jax/torch).
