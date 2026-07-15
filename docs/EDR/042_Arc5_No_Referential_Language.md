---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-042
type: EDR
title: "Arc 5 — pas de langage référentiel (l'agrégation n'est pas la communication)"
status: legacy
gate: G3
---

# EDR 042 : Arc 5 — pas de langage référentiel (l'agrégation n'est pas la communication)

## Contexte

L'EDR 040 a confirmé que la portée du signal double la chasse coopérative. Mais le signal
**signifie**-t-il quelque chose ? On mesure l'**information mutuelle** `I(token ; near_Mammouth)`
(le token encode-t-il « apex ici » ?), et on ajoute un **coût + porte** au signal (EDR 042) pour
le rendre sélectif donc — en théorie — informatif (costly signaling).

## Résultat — le langage n'émerge pas

| Régime (LANGUAGE + portée 3) | MI(token ; Mammouth) | baseline (perm.) | silence |
|---|---|---|---|
| signal gratuit | 0.0010 bits | 0.0003 | 88 % |
| signal coûteux + porte | **0.0000 bits** | 0.0001 | **99 %** |

**(1) Aucun alignement référentiel.** MI ≈ 0 (0.001 bit = bruit) : le token **ne porte pas
d'information** sur la présence de l'apex.

**(2) Le coût tue le signal** (silence 99 %) au lieu de l'informer — l'**œuf et la poule** du costly
signaling : un coût ne se rentabilise que si le signal aide *déjà*, mais il ne peut aider qu'une
fois *informatif*. Sans amorçage référentiel, le coût ne fait que supprimer le signal.

## Réinterprétation de l'EDR 040 (le plus important)

La portée a aidé la chasse (mammouth +1.00, A/B confirmé) **mais pas par la communication** :
vraisemblablement par **détection de présence** — entendre qu'un *voisin* est proche (peu importe
le token) → se regrouper → meilleure coopération. **On a de l'agrégation instrumentale, pas du
langage.** B « marche », mais pas pour la raison supposée.

> Distinction d'honnêteté : *coordination par proximité* ≠ *communication référentielle*. La
> première a émergé (utile) ; la seconde non.

## Conséquences

- **Le vrai langage (Arc 5) est une émergence plus dure** que l'activation + portée + coût ne
  suffisent à produire. C'est une **frontière** — candidate au #8 (un générateur LLM proposant des
  pressions/architectures référentielles), ou à une pression structurée plus forte.
- L'agrégation par présence est un **acquis réel** (elle améliore la coopération) — à conserver,
  distinct du langage.

## Test de confirmation (suite proposée)

Brouiller le *contenu* du token (présence conservée, sens détruit) : si la portée aide *encore*,
c'est bien la **présence** (et non le token) qui porte le bénéfice. Confirmerait la réinterprétation.

## Limites

- Population mûre mais qui n'a pas évolué *longtemps* avec un besoin référentiel ; une pression plus
  longue/structurée pourrait changer la donne (non démontré).
- MI sur 4 tokens, contexte binaire (near/not) ; mesure grossière mais suffisante pour « ≈ bruit ».

## Variables d'expérience

`signal_cost`, `speak_threshold`, durée d'évolution, pression référentielle, token brouillé (test).
