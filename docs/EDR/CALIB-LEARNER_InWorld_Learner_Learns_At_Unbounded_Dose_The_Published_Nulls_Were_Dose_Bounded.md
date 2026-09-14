---
id: EDR-CALIB-LEARNER
type: EDR
title: "L'apprenant in-world tel que publié APPREND quand la dose de crédit n'est plus bornée par la mort (12/12 seeds au-dessus de la référence lr=0 appariée, +0,156) — les nuls « le crédit n'apprend pas à froid » de S2-010/S2-011 étaient des nuls de DOSE ; et les apprenants meurent 100× plus que les non-apprenants"
status: active
verdict: LEARNER_LEARNS_AT_UNBOUNDED_DOSE_PUBLISHED_NULLS_WERE_DOSE_BOUNDED
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-S2-009, EDR-S2-010, EDR-S2-011]
corrects: [EDR-S2-010, EDR-S2-011]
---

## Question (backlog, bloc « 🧭 2026-09-14 », rang 1 — P1.6)

Trois records ont publié « le crédit in-world n'apprend pas à froid » ([[EDR-S2-009]] §crédit,
[[EDR-S2-010]] même sous curriculum, [[EDR-S2-011]] même sur une tâche LINÉAIRE) et toute la chaîne
« verrou = crédit » du dépôt repose dessus. Aucun de ces nuls ne compte la DOSE de crédit reçue, et
aucun n'a de contrôle positif de l'APPRENANT lui-même : le chemin réel est un Actor-Critic TD(0) appelé à
chaque tick (`src/worlds/world_1_stoneage.py:1717`) plus un crédit épisodique tous les
`torch_episode_k = 8` ticks, sur des agents qui meurent à 7-9 ticks. Question calibrable : **l'apprenant
tel que le monde le construit apprend-il la tâche linéaire 1-bit de S2-011 quand la mort ne borne plus
sa dose ?** Les deux issues étaient nommées d'avance (P1.6) : une variante apprend → S2-010/S2-011 sont
ROUVERTS ; aucune n'apprend à n = 12 → ils sont RENFORCÉS.

## Méthode

* Instrument : `tools/cognitive_demand_inworld.py::run_learner_probe` — cohorte IMMORTELLE (énergie
  remise à 80 sous 30, hp remis au plafond sous 50, et tout agent mort DANS le tick ressuscité : même
  objet, même génome), DV = **taux de coups** `move == int(bit_a > 0)` par bloc de 400 ticks, dose
  comptée par `tools/learning_events.py::count_learning_events` (patch de classe restauré en `finally`,
  bit-identique par défaut : `tests/sandbox/test_learning_events.py`).
* Six bras APPARIÉS par seed (mêmes génomes initiaux : `seed_at` précède la création des agents) :
  `oracle` (`LinearCognitiveOracle` câblé, contrôle positif de la DV), `lr0_reference` (apprenant à
  `lr = 0` : le plafond de l'incapable mesuré DANS le dispositif), `natural` (tel que publié : `lr = 0,04`,
  TD par tick, récompenses ×1), `lr_low` (`lr = 0,004`, balayage E19), `td_off` (chemin épisodique
  seul), `x0.05` (récompenses ×0,05 : le critic vit sur un nœud `tanh` face à r ≈ −18/tick).
* n = **12 seeds** (2026-2037), 12 agents, 2000 ticks ; unité de réplication = le seed ;
  `declare_design` avec famille de contrôles 2n ; coût borné par `project_cost` sur une unité MESURÉE
  (`results/learner_calibration_v2.json`, `cost`). Verdict : `learner_verdict` — la barre est
  `référence lr=0 + 0,05`, jamais « chance + marge » (P2.15) ; `INDETERMINE_HARNAIS` si l'oracle
  < 0,9 ou la référence > 0,5.
* Régime PUBLIÉ par le runner (bloc `regime` du JSON, jamais recopié — E8 occ. 4) :
  `cognitive_demand=True, cog_linear=True, cog_gain=12.0, base_metabolism=0.75, forage_payoff=0.0,
  benchmark_mode=True, night_enabled=False, immortal=True, refill_below=30.0, refill_to=80.0,
  hp_refill_below=50.0, energy_start=80.0, torch_episode_k=8`. Provenance `3cf5568a`, arbre sale.

## Résultat (v2, `results/learner_calibration_v2.json` — cohorte complète 12/12 dans TOUS les blocs)

| bras | hit bloc 1 | hit bloc 5 | TD / agent | épisodes | Σ‖ΔW‖ | résurrections (médiane/seed) | sep. vs lr0 apparié (médiane, min) | seeds > lr0 + 0,05 |
|---|---|---|---|---|---|---|---|---|
| oracle | 1,000 | **1,000** | 0 | 0 | 0 | 0 | — | — |
| lr0_reference | 0,122 | **0,126** | 1999 | 250 | 0 | 1 | — | — |
| natural | 0,227 | **0,277** | 1999 | 250 | 14 010 | 126 | **+0,156** (min +0,068) | **12/12** |
| lr_low | 0,258 | 0,283 | 1999 | 250 | 4 786 | 240 | +0,159 (min +0,105) | 12/12 |
| td_off | 0,189 | 0,222 | 0 | 250 | 804 | 151 | +0,096 (min +0,054) | 12/12 |
| x0.05 | 0,241 | 0,264 | 1999 | 250 | 2 609 | 252 | +0,139 (min +0,073) | 12/12 |

Blocs successifs (médiane sur seeds) — `natural` : 0,227 · 0,251 · 0,269 · 0,277 · 0,277 ;
`lr0_reference` : 0,122 · 0,121 · 0,124 · 0,126 · 0,126 (= chance 1/8). Contrastes entre variantes,
appariés par seed sur le bloc 5 : `lr_low − natural` +0,028 (10/12 positifs), `x0.05 − natural` +0,024
(8/12), `td_off − natural` **−0,046 (2/12)**.

**Garde E19** (`assert_verdict_invariant_to_optimizer`, `natural` @0,04 contre `lr_low` @0,004,
référence = oracle, `reference_floor = 0,9`) : **INVARIANT AU PAS** — l'écart à l'oracle (0,72 vs 0,72)
ne se referme pas quand le pas change. Ce qui reste est un apprenant LENT et PARTIEL, pas un nul de
réglage.

## Verdict

**`LEARNER_LEARNS`, `onset = during_run`, pour l'apprenant tel que publié.** À dose non bornée par la
mort (≈ 2000 mises à jour TD + 250 épisodes par agent), l'apprenant in-world de [[EDR-S2-011]] apprend
la tâche linéaire : 12/12 seeds au-dessus de leur référence lr=0 appariée, séparation médiane +0,156,
minimum +0,068, courbe monotone sur cinq blocs. Les trois nuls publiés sont donc des **nuls de DOSE** :
à la dose que la mort permet (agents morts à 7-9 ticks, soit quelques dizaines de mises à jour), le
crédit n'apprend pas ; à 2000, il apprend — lentement (0,28 contre 1,0 pour l'oracle à 2000 ticks), et
sans que le pas d'apprentissage explique l'écart résiduel (E19).

**Ce que la calibration réfute chez le panel du 2026-09-14** (mesures n = 1, non versionnées) :
« l'apprenant publié est PLAT là où TD coupé et ×0,05 apprennent ». À n = 12 et cohorte complète,
c'est l'inverse : `natural` n'est pas plat, **`td_off` est la PIRE variante** (2/12 seeds au-dessus de
`natural` — le TD par tick CONTRIBUE), et `x0.05` n'apporte rien de fiable (8/12). L'hypothèse
« critic tanh saturé » n'a pas d'effet mesurable sur l'apprentissage.

**Fait neuf, mesuré, mécanisme NON établi : les apprenants MEURENT ~100× plus que les non-apprenants.**
Résurrections par seed : `lr0_reference` 1, `oracle` 0, `natural` 126, `td_off` 151, `lr_low` 240,
`x0.05` 252. Ce n'est pas « se déplacer vers la récompense » qui tue (l'oracle le fait parfaitement et
ne meurt jamais) : c'est quelque chose que fait un apprenant EN COURS d'apprentissage. Le monde tue à
l'intérieur d'un tick (un projectile lancé par un pair retire `energy_spent × poids` d'un coup ;
`world_1_stoneage.py`, phase de lancer ; riposte du gibier sur la case). Candidats : les canaux
`grab`/`rub` que `learn` met à jour par BCE et qui déclenchent la taxe de portage ([[EDR-WARM-007]]),
les lancers entre pairs, le gibier. À mesurer avant toute citation comme mécanisme. **Conséquence
opératoire** : dans le monde MORTEL, la dose de l'apprenant est bornée par sa propre létalité — un run
qui mesure la survie d'un apprenant confond « apprend » et « meurt en apprenant ».

## Ce que le v1 a appris (cohorte à recharge d'ÉNERGIE seule — `results/learner_calibration_v1_energy_only.json`)

Le premier run, lancé avec une recharge d'énergie seule, perdait jusqu'à la moitié des cohortes
apprenantes dès le premier bloc (seed 2027 : 12 → 9 à 400 ticks, 3 à 800) contre 11/12 pour lr=0 et
l'oracle : le taux de coups des blocs tardifs portait un **biais de survivants corrélé au bras**. Il
donnait `x0.05` à 0,390 et `lr_low` à 0,334 ; à cohorte complète ils tombent à 0,264 et 0,283, tandis
que `natural` ne bouge pas (0,272 → 0,277). **Tout l'avantage apparent des variantes en v1 était de la
sélection.** La cellule qui l'a révélé est gelée en test
(`test_run_learner_probe_immortal_cohort_stays_complete_under_learning`, seed 2027), et `resurrections`
est publié pour que ce biais ne puisse plus passer.

## Portée (hedges)

* Un banc (stoneage `cog_linear`), une tâche (1 bit, 8 logits de déplacement, chance 1/8), un régime,
  2000 ticks. La séparation est établie ; la VITESSE d'apprentissage et le plafond (0,28 à 2000 ticks)
  ne sont pas expliqués (E19 exclut le pas ; reste la dose, l'architecture du crédit, la létalité).
* La règle de lecture a été corrigée après le seed 1/12 du v1 (le gain intra-run ne décide plus, il
  date : `onset`) — déclaré dans `learner_verdict`, pas caché. Le critère principal (séparation à la
  référence appariée) est celui posé avant le run.
* Le `summary` du JSON a été RECALCULÉ hors processus avec la règle corrigée (note dans le fichier).
* Un seul régime de recharge testé pour l'immortalité ; `resurrections` publie ce que le monde a tué.
* Le coût publié (`unit_s = 41 s`) a été mesuré PENDANT que la suite de tests tournait : c'est un
  majorant (E12 appliquée au coût, dans le bon sens).
* Rien ici ne dit que le crédit apprend la tâche 2-bits XOR de S2-009/S2-010, ni la rétention à
  D ≥ 1 ([[EDR-LOCK-001]]) : c'est la tâche LINÉAIRE de S2-011, choisie parce qu'elle isole le crédit
  de la représentation.

## Ce que ça change

* [[EDR-S2-010]] et [[EDR-S2-011]] : bandeau de portée (« nul à dose bornée par la mort »), posé le
  2026-09-14 APRÈS cette mesure (P3.6, jamais avant : E8).
* Le run P4.4 (`S2-CREDIT-RETENTION`) : la variante à sceller est **l'apprenant tel que publié**
  (`natural`) — aucune variante n'est fiablement meilleure, et il est bit-identique aux records ;
  `lr_low` en bras de sensibilité si le budget le permet. Le design doit PUBLIER la dose et TRAITER la
  létalité des apprenants (126 morts par seed) : une phase d'apprentissage immortelle puis un test de
  survie mortel, ou une DV qui ne confond pas « apprend » et « meurt en apprenant ».
* Le chiffre « in-world 0 » : ce record n'est pas un franchissement de porte (un taux de coups n'est
  pas une survie), mais il retire au mur son premier nom faux — « le crédit ne peut pas apprendre
  in-world ». Il peut. Il apprend lentement, et il meurt en apprenant.

Converge [[EDR-S2-009]] (le monde exige ; l'oracle à 1,0 le confirme ici), [[EDR-WARM-010]] (le
paysage récompense la compétence partielle), [[EDR-EVO-011]] (l'acte débloqué coûte la survie — même
direction que la létalité mesurée ici), REF-EXPERIMENT-PREFLIGHT (question 1 : les deux issues ;
question 3 : unité = seed).
