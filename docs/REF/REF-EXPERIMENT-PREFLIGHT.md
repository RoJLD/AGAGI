---
id: REF-EXPERIMENT-PREFLIGHT
type: REF
title: "Pré-vol expérimental — les 4 générateurs d'erreur, dont 2 automatisables"
status: active
---

## Origine
Session WARM-005→009 (2026-07-20) : **7 revues adversariales, 7 erreurs réelles trouvées**, dont un bug
d'aliasing mémoire, une fausse alerte transversale propagée puis rétractée, une inférence déclarée
prudemment mais fausse, et une vérification de non-régression qui ne testait rien.

Les 11 symptômes se ramènent à **4 générateurs**. C'est la distinction utile : une checklist de
11 items ne sera pas lue ; 4 questions le sont.

| # | Question non posée | Symptômes de la session |
|---|---|---|
| **A** | L'instrument peut-il produire **les deux** issues ? | contrôle tautologique (ne pouvait pas échouer) ; filtre `-k` vide (ne pouvait pas échouer) ; bras sans `Fruit` (ne pouvait pas réussir) |
| **B** | Quelle est l'**unité de réplication** ? | `agents[0]` ×2 ; `sign_p` pseudo-répliqué ; « 3 cas » érigés en propriété de l'instrument |
| **C** | La grandeur **mesurée** est-elle celle qui **agit** ? | `logits` aliasé sur `H` ; sonde oracle ≠ comportement in-world ; flag ≠ régime de revenu |
| **D** | Est-ce que je **raisonne au lieu de mesurer** ? | extrapolation depuis un préfixe de 200 epochs ; maillon final inféré |

## Ce qui est automatisable, et ce qui ne l'est pas
**A et C sont automatisables** — et doivent l'être, parce que la conviction d'avoir vérifié résiste à la
prose : l'ablation buguée avait été « vérifiée » en contrôlant l'argmax et l'ε-greedy, deux hypothèses
justes, mais pas l'aliasing. Une assertion exécutable ne se laisse pas convaincre.

**B et D ne le sont qu'à moitié.** Aucun code ne peut choisir l'unité de réplication ni décider qu'un
maillon mérite d'être mesuré. Mais les **déclarer par écrit avant le run** suffit souvent : personne
n'écrit « unité = agent » juste à côté de « les agents partagent l'entraînement » sans voir le conflit.

## Usage
`tools/experiment_preflight.py` — chaque fonction cite l'erreur concrète qu'elle aurait attrapée.

```python
from tools.experiment_preflight import (assert_ablation_changes_something, assert_positive_control,
                                        assert_not_degenerate, assert_selection_nonempty,
                                        assert_no_aliasing, assert_predictor_measured_in_situ,
                                        declare_design)

spec = declare_design(                       # B + D : à joindre au record
    question="l'ablation X améliore-t-elle la survie ?",
    replication_unit="ère",                  # PAS « agent » si les agents partagent entraînement/monde
    n_independent=12,
    links={"X change le comportement": "measured", "gain de survie": "measured"})
assert spec["warning"] is None               # un maillon 'inferred' lève un avertissement explicite

assert_no_aliasing(logits, pop.H)            # C : la sortie ne partage pas la mémoire de l'état
assert_positive_control(lambda: gain_oracle(), expect_better_than=0.0)   # A : le banc PEUT réussir
assert_not_degenerate(surv_intact)           # A : pas de plancher/plafond
assert_ablation_changes_something(intact, ablated)                       # A : pas de no-op analytique
```

## Règles non négociables qui en découlent
1. **Un contrôle négatif qui ne peut pas échouer n'est pas un contrôle.** Si l'ablation porte sur une
   action que le sujet n'exécute pas, le no-op est analytique. Le contrôle informatif est la
   manipulation **INVERSE** (forcer l'action chez ceux qui ne la font pas).
2. **Un sham doit reproduire la VOIE de l'artefact suspecté**, pas seulement « ne rien faire » : c'est en
   clampant un nœud *non lu* via la même vue aliasée qu'on a prouvé qu'un bug était inerte.
3. **Réduire le n, jamais supprimer le maillon.** Une chaîne causale transporte son **signe**, pas son
   **amplitude** (55 % de la marge sur une population, 2-10 % sur une autre).
4. **Lire le nombre d'unités EXÉCUTÉES**, pas seulement l'absence d'échec.
5. **Ne pas généraliser depuis un échantillon saillant** — `agents[0]`, trois cas, une population.
   Erreur commise **trois fois** dans la session, y compris par le record qui la dénonçait.
6. **Avant de déclarer un défaut « transversal », lire comment le n est constitué** dans ≥2 bancs
   indépendants (un `grep` de 2 min a suffi à rétracter une alerte qui aurait lancé un audit inutile).

## Portée
Complète [[REF-DEMAND-MARKER]] (l'instrument : ablation within-subject) en amont : REF-DEMAND-MARKER dit
*quoi mesurer*, ce REF dit *à quelles conditions la mesure veut dire quelque chose*.
Le garde-fou n≥12 du projet porte sur la **taille** ; le générateur B porte sur l'**indépendance**.

Instancié par [[EDR-WARM-006]], [[EDR-WARM-007]], [[EDR-WARM-008]].
