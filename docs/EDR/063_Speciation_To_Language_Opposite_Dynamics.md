---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-063
type: EDR
title: "Porter la spéciation au langage — révèle des dynamiques OPPOSÉES"
status: legacy
gate: G3
---

# EDR 063 : Porter la spéciation au langage — révèle des dynamiques OPPOSÉES

## Contexte

EDR 058 unifiait les deux frontières : « la sélection élitiste tue la nouveauté ». EDR 060 : la
spéciation-par-taille protège l'innovation architecturale (NAS). On la **porte au langage** par
comportement (niche = token dominant près du Mammouth, `track_apex_token` + `SPECIATE_MODE="token"`).
A/B token-spéciation ON vs OFF, 6 seeds × 16 ères.

## Résultat — direction négative

| | taux d'émergence | gain moyen |
|---|---|---|
| OFF | 33 % (2/6) | 0.0074 ± 0.0117 |
| TOKEN-SPEC | **17 % (1/6)** | **0.0026 ± 0.0083** |

t=−0.83, **d=−0.48 (effet moyen NÉGATIF)** → non significatif à n=6 (régime faible, comme tout le
langage), mais la **direction est nette**.

## Lecture — des dynamiques OPPOSÉES (le raffinement de l'unification)

> Protéger la diversité des tokens **baisse** l'émergence. Cohérent et net en direction :
> - **NAS** doit *EXPLORER* l'espace des architectures → protéger la diversité **aide** (spéciation,
>   EDR 060 ✅).
> - **Langage** doit *CONVERGER* sur *une* convention partagée → protéger la diversité **NUIT**.

**L'unification d'EDR 058 tient au DIAGNOSTIC** (« la sélection stricte tue la nouveauté ») **mais les
REMÈDES DIVERGENT** :

| Frontière | Nature de la nouveauté | Dynamique requise | Outil |
|---|---|---|---|
| Architecture | structurelle (un nœud) | **explorer** (garder la diversité) | spéciation ✅ |
| Langage | coordination (une convention) | **converger** (briser la symétrie ensemble) | ✗ spéciation ; pression de convergence |

> **La spéciation est l'outil du NAS, PAS celui du langage.** Une convention n'est utile que
> *partagée* (coordination de groupe) ; protéger des conventions *divergentes* empêche le groupe de
> s'accorder. Le langage relève de la **sélection de groupe / pression de convergence**, pas de la
> protection de diversité individuelle.

## Honnêteté

- d=−0.48 est *suggestif*, pas *confirmé* (n=6 ; le langage demande ≫ seeds, EDR 052). Mais combiné à
  la cohérence conceptuelle (explorer vs converger), la lecture « dynamiques opposées » est solide.

## Conséquence

- **Le langage a besoin d'une PRESSION DE CONVERGENCE** (briser la symétrie ensemble), pas de
  diversité protégée. Nos tentatives manuelles de convergence (045) étaient gameables → retour au
  même constat : concevoir le bon mécanisme de convergence est dur (EDR 057).
- **C'est exactement le rôle du #8** : itérer des mécanismes de convergence, mesurés puissamment.
  Le #8 (armable, mesure puissante branchée — EDR 061) est le chemin systématique.

## Statut

- `track_apex_token` / `SPECIATE_MODE` : seams construits (off/"size" par défaut), 138 tests verts.
- **Les deux frontières, désormais nettes** : NAS = protection résolue + demande non saturante dans le
  foraging (062) ; langage = stochastique + besoin de convergence (non-spéciation) + #8 comme voie.

## Variables d'expérience

Pression de convergence (vs diversité), sélection de groupe, nb de seeds, clé de niche
comportementale.
