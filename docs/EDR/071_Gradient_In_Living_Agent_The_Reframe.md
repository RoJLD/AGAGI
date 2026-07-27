---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-071
type: EDR
title: "Gradient dans l'agent vivant — BPTT-RL validé, et une correction importante"
status: legacy
gate: foundational
---

# EDR 071 : Gradient dans l'agent vivant — BPTT-RL validé, et une correction importante

## Contexte

Grand chantier : intégrer le gradient (067-070) dans la biosphère vivante (RL). 1er pas de
dé-risquage : valider que le **BPTT marche en RL** sur une tâche foraging-mémoire (indice transitoire
au pas 0 → retenir → naviguer), via REINFORCE à travers le temps. Comparaison BPTT vs one-step.

## Résultat

| Épisode | BPTT (gradient à travers le temps) | ONE-STEP (gradient coupé) |
|---|---|---|
| K=8 | 0.984 | 0.987 |
| K=20 | 1.000 | 1.000 |
| K=30 | 1.000 | 1.000 |

- **BPTT-RL marche** (implémentation validée : l'agent apprend la mémoire-foraging par gradient RL).
- **MAIS le one-step suffit AUSSI** — partout. La tâche ne *nécessite* pas de crédit à travers le
  temps : la récompense terminale est *diffusée* à tous les pas, et la mémoire de l'indice vit dans
  la **récurrence avant** (forward). BPTT n'est nécessaire que pour des tâches à *crédit temporel non
  trivial* (distracteurs, timing précis) — pas le foraging.

## La correction (le vrai apport)

> **La biosphère a DÉJÀ du gradient.** L'Actor-Critic (EDR 020/023) *est* une méthode de gradient
> (one-step). L'écart spectaculaire « gradient ≫ mutation » d'EDR 067 était un artefact du **banc** :
> une tâche en **mutation PURE**, *sans* apprentissage intra-vie. La biosphère, elle, apprend déjà par
> gradient à chaque vie.

**Donc les murs (langage barren, NAS bloat) ne venaient PAS de l'absence de gradient intra-vie** —
ils venaient de l'**ÉVOLUTION (mutation) des *architectures* et des *conventions de population***, là
où le gradient *n'agit pas* (le gradient intra-vie ajuste les poids d'UN agent ; il n'évolue pas
l'architecture ni ne coordonne une convention multi-agents).

## Re-cadrage de l'intégration

L'objectif n'est pas « ajouter du gradient » (il y en a déjà) mais **mieux répartir le travail** :

| Ce que fait… | …le gradient intra-vie (Actor-Critic) | …l'évolution (mutation) |
|---|---|---|
| poids d'un agent | ✅ (déjà) — à renforcer (A2C/BPTT pour mémoire profonde) | — |
| architecture | — | faible (064 : bloat) |
| convention multi-agents | — | loterie (053) ; **le gradient MULTI-AGENT (jeu référentiel, 070) la crack** |

> **Le vrai levier biosphère** : (1) renforcer le gradient intra-vie existant (Actor-Critic → A2C,
> BPTT pour les compétences-mémoire profondes) ; (2) porter le gradient **multi-agent** (jeu
> référentiel, 070) dans la biosphère pour le langage ; (3) garder l'évolution pour ce qu'elle fait
> bien (explorer, Baldwin 068), pas pour ce que le gradient fait mieux.

## Honnêteté

- BPTT-RL *fonctionne* mais n'était pas *nécessaire* sur ce banc → la valeur est la **clarification**
  (la biosphère a déjà du gradient), pas un gain de perf.
- C'est un résultat *corrigeant* : essayer d'intégrer a révélé que le diagnostic « biosphère limitée
  par la mutation » était trop simple. Mieux vaut le savoir avant une grosse refonte.

## Statut

- `grad_forage.py` : BPTT-RL validé (auto-contenu). Découverte clé : la biosphère apprend déjà par
  gradient (Actor-Critic) ; le chantier est la *répartition* évolution/gradient, pas l'ajout du gradient.

## Variables d'expérience

Tâche RL (foraging vs crédit-temporel dur), Actor-Critic one-step vs A2C vs BPTT, gradient multi-agent
dans la biosphère, répartition evolution/gradient.
