---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-025
type: EDR
title: "Curriculum sur l'Axe Craft — la complexité se grimpe palier par palier"
status: legacy
gate: G2
---

# EDR 025 : Curriculum sur l'Axe Craft — la complexité se grimpe palier par palier

## Contexte — étape 4 de la Vague 0ter

La boucle d'émergence est prouvée au craft **L0** (auto-craft, EDR 021/024). L'axe Craft
(EDR 018) prévoit de complexifier la *mécanique* de craft orthogonalement au monde, **un cran
à la fois**, chaque palier maîtrisé avant le suivant (mastery gate). Étape 4 : le démontrer.

  - **L0 (auto)**     : tenir tranchant + manche → lance (aucune action).
  - **L1 (action)**   : idem, mais exige le geste `rub`.
  - **L2 (position)** : idem, mais exige `rub` ET ingrédients en positions 0 et 1.

## Décision (V18.12)

- **ε-greedy étendu** (`world_1`) : en entraînement, force aussi le geste `rub` dès
  `craft_level >= 1` (comme `grab` à L0) → le nouveau geste requis est exploré, crédité par le
  policy gradient (le `_pg` enregistre déjà `rub`), propagé par le HoF.
- **`run_one_era(..., craft_level)`** : règle `env.craft_level`.
- **`tools/curriculum_craft.py`** : rampe L0→L1→L2 ; avance quand `crafts/ère ≥ mastery (5)`
  pendant `patience (2)` ères consécutives. HoF persistant → l'évolution capitalise d'un palier
  à l'autre.

## Résultat — chaque palier maîtrisé

| Palier | Gate ajouté | Crafts/ère | Statut |
|---|---|---|---|
| **L0** (auto) | — | 28, 30 | ✅ maîtrisé (2 ères) |
| **L1** (rub) | geste `rub` | 24, 22 | ✅ maîtrisé (2 ères) |
| **L2** (position) | `rub` + positions 0,1 | 16, 18 | ✅ maîtrisé (2 ères) |

> La boucle prouvée à L0 **rejoue à chaque palier** : un gate ajouté (un geste, puis une
> contrainte positionnelle) → exploré (ε-greedy), encodé (policy gradient), propagé (HoF) →
> maîtrisé. Le craft décroît doucement (28→24→16) avec la complexité, mais reste loin au-dessus
> du seuil. **La même machinerie franchit chaque cran** — validation de l'axe développemental
> (EDR 018) : on empile la complexité un cran à la fois.

## Limites & suites

- Mesuré **avec ε-greedy actif** (exploration des gestes) : démontre que le curriculum *grimpe*
  l'axe. Le **transfert sans ε** au monde dur à L1/L2 (comme les 28 lances de L0, EDR 021) reste
  une consolidation à venir.
- Mastery atteinte vite (2 ères = minimum) : seuil/patience à durcir pour exiger un vrai plateau.
- (Test `test_metaprog_closed_loop` flaky — dépend de l'état du fichier HoF partagé ; passe en
  isolation ; sans rapport avec ce changement.)

## Variables d'expérience

`mastery`, `patience`, `eps`, schedule d'ε par palier, gating de `force_rub`, paliers L3+ (multi-étapes).
