---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-073
type: EDR
title: "Jeu référentiel sur le VRAI connectome — l'écart banc→biosphère est architectural"
status: legacy
gate: G3
---

# EDR 073 : Jeu référentiel sur le VRAI connectome — l'écart banc→biosphère est architectural

## Contexte

EDR 072 : le jeu référentiel de population converge à 100 % (MLP). 1ʳᵉ étape du câblage biosphère : le
porter sur le **connectome RÉEL** de l'agent, aux positions E/S exactes — apex à l'**entrée 4**
(`on_apex_type`), token aux **sorties 19:23** (`logits[19:23]`). Locuteur = le connectome (1 tick) ;
auditeur = tête de décode apprise ; population, gradient (BPTT + straight-through).

## Résultat — le mécanisme ne transfère pas trivialement

| Substrat | decode croisé | convergence |
|---|---|---|
| MLP propre (072) | **1.00** | 100 % |
| **vrai connectome, apex SCALAIRE** | **0.52** | 0 % |
| **vrai connectome, apex ONE-HOT** | **0.49** | 0 % |
| (biosphère sous mutation) | ~0.25-0.33 | loterie |

- **Au-dessus du hasard (0.33) mais loin de 1.00, et pas fiable.**
- **L'encodage n'est PAS le goulot** : scalaire (0.52) ≈ one-hot (0.49). Ce n'est pas la
  représentation de l'apex.

## Diagnostic — l'écart est ARCHITECTURAL

> Le connectome de la biosphère est un **map 1-tick (réflexe)** : *une seule couche* entre l'apex
> (entrée 4) et le token (sorties 19:23), sans traitement caché intermédiaire. Le MLP avait une couche
> cachée (M→H→V) ; le connectome, non. → moins expressif pour le référentiel → convergence partielle.

> **Le mécanisme prouvé sur le banc (072) ne transfère pas trivialement à l'agent vivant. L'écart
> banc→biosphère est réel, et il est architectural.** On ne le savait pas avant d'essayer — c'est
> *exactement* ce que « câbler dans le vivant » devait révéler.

## Prescription d'intégration (concrète)

Pour un langage fiable dans l'agent vivant, donner à la voie référentielle une **capacité cachée** :
1. une **tête référentielle dédiée** (un petit MLP apex→hidden→token) entraînée par le jeu de
   population (072), branchée sur la perception d'apex + l'émission de token ; ou
2. un **connectome multi-tick** pour la langue (laisser la récurrence faire le traitement caché) ; ou
3. enrichir la perception d'apex + élargir le bloc token.

L'option (1) est la plus sûre : elle isole le langage du foraging, garde le mécanisme 072 (qui marche),
et se branche proprement (perte référentielle par gradient sur la tête + token).

## Honnêteté

- C'est un résultat *corrigeant et précieux* : l'intégration n'est pas « copier 072 dans la biosphère »
  mais « donner à l'agent vivant la *capacité architecturale* qu'avait le banc ». La tentative a
  localisé l'obstacle réel (le connectome 1-tick comme substrat référentiel faible).
- ~0.5 peut aussi tenir au setup (1 tick, listener linéaire, training) ; l'option (1) le trancherait.

## Statut

- `refgame_bio.py` : jeu référentiel sur le vrai connectome (positions E/S réelles). Convergence
  partielle (~0.5) → l'écart architectural est identifié.
- Câblage vivant re-cadré : **tête référentielle dédiée + capacité cachée**, pas une copie directe.

## Variables d'expérience

Voie référentielle (connectome brut 1-tick vs tête MLP dédiée vs multi-tick), capacité cachée, listener
linéaire vs MLP, nb de ticks, intégration dans la boucle vivante.
