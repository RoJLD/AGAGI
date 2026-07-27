---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-046
type: EDR
title: "Arming dirigé du #8 sur le NAS — et la leçon unifiée des deux frontières"
status: legacy
gate: foundational
---

# EDR 046 : Arming dirigé du #8 sur le NAS — et la leçon unifiée des deux frontières

## Contexte

2ᵉ frontière de l'arming dirigé (après le langage, EDR 045) : l'**architecture** (axe C7, seul à
0 EDR, EDR 034). Constat préalable : tous les champions du HoF font **172 nœuds** (figé), alors que
`add_node` fonctionne (172→173 forcé) et que `add_node_rate=0.2` par défaut. Donc la croissance *se
déclenche* — mais le HoF ne grandit pas.

## Arming + résultat

`init_primordial_soup(..., add_node_rate)` (EDR 046) permet de forcer la croissance. A/B même HoF
de départ, 18 ères/lignée :

| add_node_rate | HoF nodes (moy / max) | proies_moy | mammouth |
|---|---|---|---|
| **0.6** (forcé ×3) | **172 / 172** (figé) | 1.10 | 1.22 |
| 0.2 (défaut) | 172 / 172 | 1.04 | 0.56 |

> Même en **triplant** le taux, l'architecture **ne grandit pas** : les connectomes plus gros (créés
> dans les enfants) ne sont **jamais sélectionnés**, et la perf ne s'améliore pas. **La capacité
> n'est PAS le goulot — le monde n'exige pas plus de cerveau.**

## La leçon UNIFIÉE (le vrai résultat de l'armement)

Les deux frontières armées convergent vers une seule vérité :

| Frontière | Arming dirigé | Pourquoi ça ne franchit pas |
|---|---|---|
| **Langage** (045) | pression référentielle | le monde n'a qu'un référent binaire → la *présence* suffit, le token n'a rien à dire |
| **Architecture** (046) | croissance forcée | la tâche ne sature pas 172 nœuds → la capacité en plus est neutre, non sélectionnée |

> **On ne fait pas émerger une capacité en *ajoutant le mécanisme* — il faut que le MONDE
> l'*exige*.** C'est la thèse fondatrice du projet (EDR 010/012 : « un monde qui exige la
> cognition »), redécouverte *empiriquement, au bord des deux frontières*.

## Implication pour le #8 (profonde)

Le coup le plus précieux d'un générateur intelligent (LLM) ne serait **pas** « ajoute une récompense
référentielle » ni « fais grandir l'architecture » (on vient de montrer que ça ne suffit pas). Ce
serait **« rends le monde plus EXIGEANT »** :
- multi-référent (signaler *quel* gibier) → crée le besoin de langage ;
- tâche saturant la mémoire/capacité (séquences longues, planification) → crée le besoin
  d'architecture.

**Le #8 devrait agir sur la *demande du monde*, pas seulement sur le mécanisme de l'agent.** Cela
recadre le périmètre du Proposer (EDR 044) : à terme, `kind="world_demand"` autant que `"activation"`.

## Conséquences

- **L'arming dirigé a « échoué » à franchir les frontières — et c'est un succès de méthode** : il a
  dit *pourquoi* (pas de demande) et *où chercher* (durcir le monde), sans risque ni LLM live.
- `referential_scale` / `add_node_rate` restent des leviers off/défaut ; 126 tests verts.
- Avant tout re-arming : concevoir un **monde multi-référent + capacité-saturant**, puis re-tester
  langage et NAS — éventuellement avec le #8 qui *proposerait ce durcissement*.

## Variables d'expérience

`add_node_rate`, demande du monde (nb référents, profondeur de planification), périmètre du Proposer
(`world_demand`), durée d'évolution.
