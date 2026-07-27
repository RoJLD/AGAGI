---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-029
type: EDR
title: "Rendre la chaîne DOMINANTE — sélection pour l'apex + capacité de charge"
status: legacy
gate: G2
---

# EDR 029 : Rendre la chaîne DOMINANTE — sélection pour l'apex + capacité de charge

## Contexte — Vague 0quinquies

L'EDR 028 a rendu la chaîne moyens→fins **robuste** (coopération, non crit-dépendante) mais pas
encore **dominante** : à rareté extrême, `proies_moy ≈ 0.6` — elle tient sans nourrir toute la
population.

## Décision (V18.16) — sélectionner pour le bout de la chaîne

Tracer `mammoth_kills` par agent (incrémenté pour **chaque membre du pack** à la mort de l'apex)
et le peser fort dans la fitness : `life_score += mammoth_kills · 400`. → la sélection saisit le
**chasseur-coopératif**, pas seulement le crafteur, pour que la chaîne complète domine le HoF.

## Résultat — dominante quand le monde peut la nourrir

Test long (rareté 6, crit sevré 0.6→0) : pics renforcés (ère 32 : **7 crafts + 3 Mammouths +
proies_moy 1.17**), mais moyenne ~0.7. Soupçon : plafond *physique*. Sonde (sevré, crit=0,
sélection apex) :

| rareté (capacité proies) | proies_moy | Mammouths/ère |
|---|---|---|
| 6 (extrême) | 0.70 | 0.4 |
| 10 | 0.94 | 0.6 |
| **15 (survivable)** | **1.55** | **1.4** |

> **La chaîne est DOMINANTE dès que le monde peut la nourrir.** À rareté 15, *sans crit* et avec
> sélection apex, la population **prospère** sur la chaîne complète (proies_moy 1.55 ≫ seuil, 1.4
> Mammouths/ère) — la chasse coopérative outillée est la **stratégie primaire**. Le plateau à
> rareté 6 n'était **pas un échec de stratégie** mais la **capacité de charge** du monde (6 proies
> ne nourrissent pas 30 agents, même avec une chasse parfaite).

## Conclusion — thèse pleinement réalisée

La chaîne moyens→fins (petit gibier rare → crafter une lance → chasse coopérative de l'apex) est
désormais **émergente** (`EDR 027`) + **robuste** (`EDR 028`, sans crit) + **dominante**
(`EDR 029`, stratégie primaire quand le monde le permet). Le projet tient une **boucle complète,
sociale et sans béquille**, du premier geste à la prospérité de la population.

## Limites & suites

- À rareté extrême (6), la chaîne reste robuste mais bornée par le **stock de nourriture** (limite
  du monde, pas de la stratégie) — c'est cohérent (un monde sur-peuplé/sous-doté plafonne).
- **Anneler la prime de groupe** (étape 10) pour qu'elle n'entretienne pas l'acquis, une fois la
  coopération fixée.
- Brancher tout cela dans un **curriculum 2D unique** (rareté × craft_level × sevrage crit/prime)
  via le `CurriculumRunner`, comme programme développemental de référence.

## Variables d'expérience

Poids `mammoth_kills` dans la fitness, capacité de charge, taille de population, durée de vie.
