---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-019
type: EDR
title: "Exploration de l'Action `grab` — et le Mur Ultime : l'Encodage (Apprentissage)"
status: legacy
gate: foundational
---

# EDR 019 : Exploration de l'Action `grab` — et le Mur Ultime : l'Encodage (Apprentissage)

## Contexte

L'EDR 018 a foré jusqu'au socle : les agents n'exécutent jamais le geste `grab` (et un
connectome tabula rasa = zéros est totalement inerte). On a appliqué l'**ε-greedy** : en
entraînement, forcer des actions aléatoires (mouvement + grab) pour que le geste se
déclenche, soit récompensé, et — espérait-on — évolue.

## Décision (V18.6)

- `world_1` : `self.explore_eps` ; en `training_mode`, avec proba ε, `action` = aléatoire et
  `force_grab` (injecté sur `do_grab`).
- `tools/curriculum_grab.py` : ε **annelé** sur les ères d'entraînement (0.35 → 0), pour
  amorcer tôt puis laisser les grabbers *naturels* être sélectionnés tard.

## Résultat — production réelle, mais zéro encodage

Phase 1 (grab-training) : **l'ε-greedy PRODUIT du craft** — 87 puis 107 lances au total. **La
première production fiable de craft du projet.** ✅

Mais le craft est **100% dépendant de ε** :

| ε (annelé) | 0.35 | 0.26 | 0.19 | 0.12 | 0.07 | 0.05 | 0.02 |
|---|---|---|---|---|---|---|---|
| crafts/ère | 16 | 8 | 11 | 6 | 2 | **0** | **0** |

Et **Phase 2 (monde normal, ε=0) : 0 lance.** Aucun transfert.

> Quand on retire le forçage, le craft **disparaît**. Le génome n'a **jamais encodé** le geste,
> malgré 15 ères de forçage + craft dans la fitness + HoF persisté. Ni l'apprentissage
> intra-vie ni l'évolution n'ont capturé « faire grab ».

## Conclusion — le mur ultime, et la pile entièrement cartographiée

On a foré toute la pile, chaque couche mesurée et franchie, jusqu'à la racine :

```
craft sur-gaté (EDR 017)
 → simplifié L0 auto-craft (EDR 018) ✅ marche mécaniquement
   → collecte : 0 item tenu → action grab jamais tirée (EDR 018)
     → ε-greedy : le geste se déclenche, le craft est PRODUIT (107 lances) ✅
       → mais 100% forcé : ε→0 ⇒ craft→0, transfert=0
         → RACINE : le mécanisme d'APPRENTISSAGE n'encode pas l'action
```

> **Le goulot ultime n'est ni le monde, ni l'incitation, ni l'exploration, ni le moteur
> évolutif (réparé). C'est le mécanisme d'apprentissage lui-même** : l'agent ne peut pas
> *acquérir* une action nouvelle, même forcée et récompensée, car il n'y a **pas de crédit
> d'action** — le policy gradient est un Hebbien rustre (`dW ∝ advantage·h·hᵀ`, non lié à
> l'action choisie), et l'évolution ne découvre pas une politique d'action ciblée par
> mutation du connectome.

C'est exactement le levier « cœur cognitif » identifié à l'EDR 010 : **solidifier la boucle
intra-vie en un vrai Actor-Critic** (crédit d'action propre, value head entraînée comme
critic). Tant que ce n'est pas fait, **aucun comportement nouveau ne peut être acquis**,
quel que soit le monde, l'incitation, l'exploration ou le curriculum.

## Conséquences — la priorité absolue, recadrée par toute la session

- **Réparer le mécanisme d'apprentissage** (vrai policy gradient avec crédit d'action) devient
  le **levier n°1**, en amont de tout. C'est le prérequis de l'émergence de *n'importe quel*
  comportement composé.
- Tous les acquis de la session (monde exigeant, scaffold, curiosité, nouveauté, HoF sauvé,
  craft-fitness, axe Craft/L0, ε-greedy) sont des briques **correctes et en place** qui
  s'activeront dès que l'apprentissage saura encoder une action.
- L'ε-greedy reste utile (il *produit* le comportement à encoder) — il alimentera un vrai
  apprentissage.

## Variables d'expérience

Mécanisme d'apprentissage intra-vie (Hebbien actuel vs Actor-Critic avec crédit d'action vs
REINFORCE), schedule d'annealing de ε, durée d'entraînement.
