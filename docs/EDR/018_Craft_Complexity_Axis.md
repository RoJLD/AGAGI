# EDR 018 : Axe Craft — un 2ᵉ Axe Développemental (complexité de la mécanique)

## Contexte

L'EDR 017 a prouvé que la mécanique de craft empile trop de gates durs *en même temps*
(capacité, grab×2, navigation, positions, rub) → inémergeable. L'idée (utilisateur) :
**décomposer** cette complexité en un curriculum sur la mécanique *elle-même*, orthogonal
au curriculum du monde. On ajoute un gate à la fois, chacun maîtrisé avant le suivant.

## Décision (V18.5) — l'axe Craft

Deux axes de complexité **orthogonaux** le long desquels l'agent se développe :

```
            AXE CRAFT (profondeur de la mécanique) →
            L0 auto-craft → L1 +action → L2 +position → L3 multi-étapes → … → LN craft 3D physique
AXE MONDE ┌─────────────────────────────────────────────────────────────────────────
(écologie)│ soup / stoneage / agricultural / industrial
```

Mécanique paramétrée par `world.craft_level` (`stone_economy.try_craft_spear`) :
- **L0 (auto)** : tenir un tranchant + un manche n'importe où → lance, **sans action**.
- **L1 (action)** : idem, mais exige le geste `do_rub`.
- **L2 (position)** : exige `do_rub` ET ingrédients en positions 0 et 1 (recette positionnelle).
- **L3+ (futur)** : recettes multi-étapes (rock→sharp_rock→spear), … jusqu'au **craft 3D**
  avec forces/orientation (très loin).

Le curriculum **rampe `craft_level` par maîtrise** (taux de craft > seuil), via les mastery
gates déjà construits (EDR 008/009). Rendu possible par le fix du HoF (EDR 016) : la maîtrise
d'un niveau **s'accumule** et se transfère au suivant.

## Résultat — L0 valide mécaniquement, mais le mur descend d'un cran

- ✅ **L0 auto-craft fonctionne** : 10 agents tenant rock+stick → 10 lances en 1 tick, sans action.
- ❌ **Le curriculum donne toujours 0 craft** — et l'instrumentation révèle pourquoi :
  en grab-training (monde sûr, items partout, collecte récompensée), les agents tiennent
  **0 item** (`inv moy=0`, jamais de grab). Ils survivent sur l'énergie de départ puis meurent.

> Le craft n'est **plus** le goulot (L0 le rend trivial). Le mur est descendu au **geste `grab`** :
> les agents n'exécutent jamais l'action de collecte. Une action qui ne se déclenche jamais
> n'est jamais récompensée, donc jamais apprise — l'exploration à la racine de l'espace d'action.

On a foré la pile complète : **craft → collecte (grab×2) → action `grab` non explorée**.

## Conséquences

- L'axe Craft est le **bon cadre** et L0 est un acquis correct (réutilisable dès que la
  collecte sera résolue). Il s'assoit sur un sous-problème non résolu : **l'exploration de
  l'action `grab`**.
- Le « barreau le plus bas » doit être **encore plus bas** : enseigner le *geste* `grab`
  lui-même. Voies possibles :
  - **Exploration ε-greedy** en entraînement : injecter des actions aléatoires (dont grab)
    pour qu'il se déclenche → soit récompensé → renforcé. Standard RL pour l'action jamais tirée.
  - **Niveau L(-1)** : lances déjà présentes dans le monde, l'agent les *ramasse* (1 action) —
    apprendre « lance = bien (tue le Mammouth) » avant d'apprendre à la faire.
- Le `craft_level` par défaut est **0** (auto-craft) : le monde est désormais *learnable* côté
  mécanique — le craft émergera dès que la collecte le sera.

## Variables d'expérience

`craft_level` (0→N), seuil de maîtrise pour ramper, mécanisme d'exploration de l'action grab
(ε-greedy, action-novelty), barreau L(-1) (ramasser une lance pré-faite).
