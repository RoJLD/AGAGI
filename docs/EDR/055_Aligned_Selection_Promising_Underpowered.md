---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-055
type: EDR
title: "Sélection alignée — le lever le plus prometteur, mais sous-puissant"
status: legacy
gate: G3
---

# EDR 055 : Sélection alignée — le lever le plus prometteur, mais sous-puissant

## Contexte

EDR 054 : la convention érode car la sélection (`life_score`) est aveugle au langage. Remède :
`world.align_selection` prime la **distinction référentielle** par agent — tokens *distincts* près du
Mammouth vs du Leurre (distance de variation totale entre les deux histogrammes). **Anti-piège 045** :
un token constant → distinction nulle → zéro prime (non gameable). La *convention* (quel token) reste
émergente ; on ne récompense que le *fait de distinguer*.

## Résultat — bon sens, non confirmé

A/B 6 seeds × 16 ères, mesure du gain MI (réel − permuté) via le harnais (EDR 052) :

| | taux d'émergence | gain moyen | seeds émergés |
|---|---|---|---|
| OFF (base) | 33 % | 0.0074 ± 0.0117 | 2/6 |
| **ALIGN (3.0)** | **50 %** | **0.0111 ± 0.0099** | 3/6 |

Verdict : t=0.59, d=0.34 → **non significatif**.

## Lecture honnête

- **Première intervention qui pousse dans le bon sens sur les DEUX axes** : taux (33→50 %) *et*
  moyenne (0.0074→0.0111) montent ensemble. Contrairement à 045 (gameable) et 050 (pire), la
  sélection alignée *nudge réellement* vers le langage — design anti-gameable qui tient.
- **Mais sous-puissant** : à n=6, 33 % vs 50 % = 2/6 vs 3/6 (un seul seed d'écart), dans le bruit
  binomial. Départager 0.33 de 0.50 demanderait **~40-50 seeds**. Le harnais refuse de confirmer —
  comme il se doit.

## Le mur récurrent (EDR 052, ré-confirmé)

> Les effets sur le langage sont **réels mais faibles** (~0.01-0.05 MI), et la **variance entre seeds
> domine**. Toute intervention incrémentale est donc *coûteuse à confirmer* (≫ 10 seeds). C'est le
> régime fondamental de cette frontière dans ce système.

## Décision stratégique (à prendre)

Trois voies honnêtes :
1. **Dépenser les seeds** (≥ 40) pour confirmer/infirmer la sélection alignée — la plus prometteuse,
   mais ~1-2 h de compute.
2. **Un lever plus FORT** : viser un effet *large* (résolvable à faible n) plutôt qu'incrémental —
   p.ex. sélection alignée *forte + propagation explicite* des lignées distinctives, ou une demande
   bien plus saturante.
3. **Acter le régime** : la frontière du langage est faible/stochastique ici ; passer à (2) NAS et
   (3) #8 — qui ont peut-être des effets plus francs — en gardant la sélection alignée comme acquis
   « prometteur non confirmé ».

## Statut

- `align_selection` : mécanisme **construit, testé, anti-gameable** (off par défaut, 133 tests verts).
- Effet : **prometteur, non confirmé** (le verdict honnête).

## Variables d'expérience

Force `align_selection`, nombre de seeds (puissance), propagation des lignées distinctives, durée,
métrique (taux vs moyenne).
