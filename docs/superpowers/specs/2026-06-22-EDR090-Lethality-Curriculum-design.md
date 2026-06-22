# EDR 090 — Un curriculum de létalité casse-t-il le chicken-and-egg d'EDR 089 ?

**Statut :** pré-enregistrement (gelé avant données).
**Date :** 2026-06-22.
**Lignée :** EDR 087 (le contenu ne paye pas) → 088 (le bénéfice du contenu monte avec la criticalité, tendance non robuste) → 089 (tension structurelle : létalité ⊥ survie longue) → **090 (le curriculum de létalité)**.

## 1. Motivation

EDR 089 a diagnostiqué une **contradiction de demandes** qui explique toute la série négative 082→088 :

- **088** : le contenu du langage ne paye que si la distinction est *décisionnellement coûteuse* → il faut des **Leurres mortels** (`leurre_frac` élevé, dmg=50).
- **083/089** : les agents doivent **survivre assez longtemps** pour co-évoluer l'écoute/l'évitement.

Ces deux exigences se contredisent : Leurres mortels → survie courte (~37 ticks) → pas le temps d'évoluer l'évitement → l'usage du langage ne peut pas être sélectionné. **Chicken-and-egg** : survivre pour évoluer l'évitement, et l'évitement pour survivre. Le point de départ (champions *stoneage*) n'évite pas les Leurres.

089 désigne le levier : un **curriculum de létalité** (douce → dure, par paliers) pour fabriquer un substrat survivable AU DÉPART qui durcit une fois l'évitement acquis. **EDR 090 teste ce levier — et lui seul.**

## 2. La prétention (1 variable — Commandement 15)

> Sur le monde de Lewis au sweet-spot énergie (085), faire **ramper la létalité** (`leurre_frac` de douce à dure, promotion portée par la maîtrise) produit, au palier terminal `0.83`, une population qui **survit ET évite les Leurres mortels** — là où un **départ à froid** directement à `0.83`, à budget d'ères égal, s'effondre.

**Variable manipulée :** schéma d'entraînement — **curriculum** (rampe `0.17→0.33→0.50→0.67→0.83`) **vs flat** (cold start direct à `0.83`).

**Tout le reste identique, apparié par seed** (`seed_at(base, ·)` → même monde, mêmes champions de départ, même budget d'ères entre les deux bras d'une même répétition).

**Hors-périmètre (explicitement) :** le langage. Aucune tête référentielle, `decode_act=False`, pas de contraste FIABLE/BRUITÉ. Le test mécanisme évolue de la **pure survie/évitement**. Le contraste langage sur le substrat produit ici sera **EDR 091** (conditionnel à un succès 090).

## 3. Mécanisme

### 3.1 Le bouton de létalité

`leurre_frac` = fraction des `N_APEX=12` apex qui sont des **Leurres-pièges** (`hp=100, dmg=50`) ; le reste réparti Mammouth/Ours (positifs). Paramétré par `_setup_critical(env, leurre_frac, n_apex)` (réutilisé de `tools/lewis_critical.py`, EDR 088). Nuit OFF (correctif audit 086).

### 3.2 Réutilisation chirurgicale du code dormant

On réutilise les **prédicats purs et déjà testés** de `src/curriculum/runner.py` :
- `has_graduated(history, cfg)` — `|pente OLS sur W| < eps_plateau` ∧ `médiane(W derniers) ≥ c_floor`.
- `GraduationConfig` — `window, eps_plateau, c_floor, patience, max_eras`.
- `plateau_slope(history, window)`.

On **n'utilise PAS** `CurriculumRunner.run` : sa promotion passe par `champion_agent_id` + snapshot KuzuDB synchrone, ce qui (a) matérialise un champion en base à chaque palier (lourd, lent) et (b) ré-introduit le hazard de mémoire ambiante non-reproductible d'089. Notre promotion porte des **génomes en mémoire**.

> **Frontière de design :** on prend la *logique de décision* (la porte de maîtrise, pure/testable) et on laisse l'*orchestration couplée* (le plumbing de snapshot). C'est le bon découpage de réutilisation.

### 3.3 Boucle (par répétition, appariée par seed)

1. **Bras curriculum.** Champions HoF de départ (`_load_champions`). Pour chaque palier `lf ∈ levels` (ordre croissant) :
   - co-évolue (runner *clean*, `memory_retriever` stoppé avant la boucle) à létalité `lf` ;
   - à chaque ère, calcule la **compétence-survie** et l'ajoute à l'historique du palier ; teste `has_graduated` + compteur de patience (streak) ;
   - **monte** d'un palier quand `streak ≥ patience` **OU** `max_eras` (du palier) atteint ;
   - les **meilleurs génomes** (top-5 par `life_score`, comme le `best[:5]` d'089) sont **portés** au palier suivant comme population de départ ;
   - enregistre `{palier, ères_tenues, compétence_finale, gradué}` dans le **transcript** (le diagnostic « où ça bloque »).
   - `total_eras` = somme des ères tenues sur tous les paliers.
2. **Bras flat (contrôle).** Mêmes champions de départ, même seed. Co-évolue **directement à `0.83`** pour exactement `total_eras` ères (matché *par seed* → budget égal exact).
3. **Mesure terminale.** Sur la population évoluée de chaque bras, `n_eval` ères propres à `leurre_frac=0.83` → `net` et survie.

### 3.4 Compétence de graduation

`competence = clip(median(survival_ticks) / max_ticks, 0, 1)`.

Justification : à `leurre_frac` élevé, survivre longtemps **exige** d'éviter les Leurres mortels (sinon mort à ~37 ticks). La survie normalisée est donc un proxy fidèle de l'évitement acquis, **et** un scalaire ∈[0,1] directement consommable par `has_graduated` (qui attend une compétence bornée).

## 4. Métriques & règle de verdict (gelées)

- **Compétence de graduation** (drive la rampe) : `clip(median(ticks)/max_ticks, 0, 1)`.
- **Métrique terminale primaire** (verdict) : `net = kills − leurre_hits` au palier `0.83`, apparié **curriculum − flat** (Wilcoxon signed-rank + bootstrap IC95 + médiane).
- **Gate de validité** : survie médiane curriculum à `0.83` **> 120 ticks** (le gate d'089).

| Condition | Verdict |
|---|---|
| survie_curr > 120 **ET** (net_curr − net_flat) : Wilcoxon p<0.05 **ET** médiane>0 **ET** bootstrap IC_inf>0 | **CURRICULUM CASSE LE BOOTSTRAP** — substrat valide fabriqué → EDR 091 (langage) sur ce substrat. |
| survie_curr ≤ 120 (le curriculum lui-même n'atteint jamais le gate, même rampé) | **NÉGATIF PROFOND** — durcir graduellement ne suffit pas ; l'évitement n'est pas apprenable par ce connectome (le verrou n'est pas le bootstrap mais la capacité d'apprentissage). |
| survie_curr > 120 mais net_curr ≈ net_flat (médiane non>0 ou IC_inf≤0) | **PAS LE GOULOT** — le flat y arrivait aussi ; le chicken-and-egg n'était pas le verrou. |

Le design a donc **trois branches informatives** : le succès fabrique le substrat manquant ; chaque échec *discrimine une cause* (capacité d'apprentissage vs goulot mal identifié).

## 5. Paramètres pré-enregistrés (gelés)

| Paramètre | Valeur | Note |
|---|---|---|
| `N_APEX` | 12 | comme 088 |
| `levels` | `[0.17, 0.33, 0.50, 0.67, 0.83]` | terminal = niveau décisif d'088 |
| compétence | `clip(median(ticks)/max_ticks, 0, 1)` | proxy d'évitement |
| `GraduationConfig.window` (W) | 4 | fenêtre glissante |
| `GraduationConfig.eps_plateau` | 0.02 | pente OLS max/ère pour plateau |
| `GraduationConfig.c_floor` | 0.5 | plancher de graduation : survie ≥ 50% de max_ticks (=150 ticks). Volontairement > gate de validité (120) : graduer un palier est plus exigeant que le passer. |
| `GraduationConfig.patience` (K) | 2 | ères consécutives remplissant la condition |
| `GraduationConfig.max_eras` | 10 | garde-temps par palier (promotion forcée) |
| `max_ticks` | 300 | comme 089 |
| `num_agents` | 24 | comme 089 |
| `K_robust` | 4 | robust eval du champion (comme 089) |
| `R` | 8 | répétitions appariées |
| `n_eval` | 8 | ères de mesure terminale par bras |
| `METAB, PAYOFF` | 0.25, 3.0 | sweet spot énergie (085) |

**Sweet-spot énergie + nourriture** : `target_prey_count = 15` (substrat non food-scarce, comme l'addendum 089 — neutre au contraste, isole la létalité comme seule cause de mortalité).

## 6. Outillage & architecture

- **Nouveau fichier** `tools/lethality_curriculum.py` (EDR 090). Aucune modification des artefacts 087/088/089.
- **Briques réutilisées** :
  - `_setup_critical` (bouton `leurre_frac`) — depuis `tools/lewis_critical.py`.
  - `_run_era_clean`-style (runner déparasité : `memory_retriever.stop()` avant la boucle) — patron d'089.
  - `has_graduated`, `GraduationConfig`, `plateau_slope` — `src/curriculum/runner.py`.
  - `exp_stats` (Wilcoxon, bootstrap, médiane) — `src/seed_ai/exp_stats.py`.
  - `Harness`, `seed_at` — `src/seed_ai/harness.py`.
  - `_reproduce` (`tools/evolve_competence.py`), `_load_champions` (`tools/robust_eval.py`).
- **Runner multiprocess** (`ProcessPoolExecutor` sur les répétitions, `_one_rep` module-level, `os.chdir` + `np.random.seed(rb)` par process) → **`mp == seq` vérifié** (déterminisme), comme 089.
- **Structure** (esquisse, détail laissé au plan) :
  - `_lethal_cfg()` → `WorldConfig` sweet-spot.
  - `_run_era_clean(cfg, genomes, leurre_frac, max_ticks, measure)` → mesure {ticks, kills, leurre_hits, survivors} ou {scored}.
  - `_survival_competence(survs, max_ticks)` → `clip(median/max_ticks, 0, 1)`.
  - `_coevolve_at(cfg, mc, leurre_frac, start_genomes, grad_cfg, base, level_idx)` → co-évolue un palier jusqu'à graduation/plafond ; renvoie `(best_genomes, eras_held, history)`.
  - `_run_curriculum_arm(...)` → enchaîne les paliers, porte les génomes, renvoie `(final_genomes, total_eras, transcript)`.
  - `_run_flat_arm(..., budget_eras)` → co-évolue à `0.83` pour `budget_eras`.
  - `_measure_terminal(...)`, `_report(...)` (stats + verdict + `h.save`), `main`, `_one_rep`, `main_mp`.

## 7. Plan d'exécution

1. **Pilote R=3 (gate-check survie)** d'abord — vérifier que le bras curriculum atteint survie>120 au terminal AVANT le run complet (comme 089, qui a évité des heures de calcul à l'aveugle).
2. Si le pilote passe le gate → **run complet R=8 mp**, verdict pré-enregistré, EDR 090 écrit, PR.
3. Si le pilote échoue le gate → **NÉGATIF PROFOND** documenté (le curriculum lui-même ne fabrique pas l'évitement) — finding majeur, EDR 090 écrit en conséquence.

## 8. Garde-fous & reproductibilité

- `memory_retriever.stop()` **avant** la boucle de simulation (hazard mémoire ambiante KuzuDB, dette core-engine notée par 089).
- `seed_at(base, ·)` appariement strict curriculum/flat.
- `mp == seq` testé.
- Instabilité connectome (086 redux : `NaN value_pred`) attendue sous co-évolution longue — bénigne pour `life_score`, à noter.
- Développement **sub-agent-driven** (implémenteur → revue spec → revue qualité), commits path-scopés (sessions parallèles), worktree `worktree-edr090-lethality-curriculum` sur `main`.

## 9. Tests

- `_survival_competence` → mapping correct vers [0,1] (bornes, médiane).
- Forme du transcript (une entrée/palier, champs attendus).
- **Budget flat == total curriculum** (invariant d'appariement du contrôle).
- `has_graduated`/`plateau_slope` : déjà couverts par `tests/sandbox/test_curriculum_runner.py`.
- Déterminisme `mp == seq` (réutilise le patron de `tests/sandbox/test_coevolve_use_long.py`).

## 10. Provenance attendue

`results/lethality_curriculum_<seed>.json` : `R, levels, grad_cfg, transcripts (par rep), d_nets, survie_curr, summary, ci, verdict`. Outils : `tools/lethality_curriculum.py`, `src/seed_ai/exp_stats.py`, `src/curriculum/runner.py`.
