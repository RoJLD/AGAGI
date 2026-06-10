# EDR 030 : Sevrage de la prime + Curriculum développemental unifié (fin Vague 0quinquies)

## Contexte

L'EDR 029 a rendu la chaîne dominante (sélection apex). Restait à **consolider** : (1) sevrer la
**prime de groupe** — comme le crit, pour qu'elle n'entretienne pas l'acquis ; (2) **unifier** les
drivers expérimentaux (grab/craft/world/2d/persistence) en un **programme de référence**.

## Décision (V18.17)

1. **Prime de groupe annealée** : la prise d'apex passe de « pleine récompense à chacun »
   (scaffold) à « partagée entre le pack » (`share = scaffold·1 + (1−scaffold)·1/n`), via
   `group_reward_eras` et l'ère globale. L'économie réaliste (festin partagé) reste *avantageuse*
   (105/2 = 52 ≫ Lapin 25, et la coop survit la riposte).
2. **`tools/curriculum_developmental.py`** : un seul driver. À mesure que l'ère **globale** monte,
   le monde **durcit** (rareté 16→10) ET les **deux scaffolds se sèvrent** (crit 0.6→0, prime
   pleine→partagée). Pilote tous les annealings par l'ère globale (corrige « chaque ère = ère 1 »).

## Résultat — la chaîne est auto-suffisante

| Phase | crit | prime | Mammouth/ère | proies_moy |
|---|---|---|---|---|
| Scaffold (ères 0-19, rareté 16→12) | 0.6→0 | plein→partagé | 0–3 | ~1.2 |
| **SEVRÉ (ères 20-29, rareté 11→10)** | **0** | **1/n (partagé)** | **0.70** | **0.87** |

> Sans crit ni prime pleine, la chasse coopérative à l'apex **persiste** (0.70/ère). Le
> `proies_moy` 0.87 est sous le seuil de dominance, mais à rareté 10-11 (la phase sevrée est la
> plus dure) c'est **près de la capacité de charge** (cohérent EDR 029 : robuste partout,
> dominante quand le monde peut nourrir). **Ni la chance ni la générosité ne portent la chaîne —
> seules la coopération encodée et la sélection.**

## Conclusion — Vague 0quinquies & programme développemental bouclés

La chaîne moyens→fins est désormais : **émergente** (027) + **robuste** (028) + **dominante**
(029) + **auto-suffisante / sans béquille** (030), le tout dans **un curriculum de référence
unique**, piloté par l'ère globale. C'est le programme développemental de la Vague 0, complet et
rejouable.

## Suites

- Brancher ce driver de référence sur le `CurriculumRunner` formel (mastery gates) si l'on veut
  l'orchestration adaptative plutôt qu'un schedule fixe.
- Passer aux vagues différées (hygiène : gènes fantômes / ablation ; puis RSI ; puis Arc 5 Tribu —
  dont la coopération émergée est déjà le germe).

## Variables d'expérience

`group_reward_eras`, `wean_eras`, schedule de rareté, poids de fitness, taille/durée de population.
