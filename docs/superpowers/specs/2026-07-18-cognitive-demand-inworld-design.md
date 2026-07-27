# Design — Monde à demande cognitive in-world (flag `cognitive_demand` sur stoneage)

**Date** : 2026-07-18
**Auteur** : session Claude (poste robla) — pas de sessions parallèles ; règles git robla (pas de commit hors demande, pas de merge main sans aval).
**Portée** : G0 (rendre la demande perceptive causale IN-WORLD) — réalise la recette S2-006 dans la vraie biosphère.
**Records visés** : EDR-S2-009 (`gate: G0`, `tests: [SDR-G0]`, `adopts: REF-DEMAND-MARKER`).

---

## 1. Problème & objectif
S2-002/003 : la survie du champion est perception-NEUTRE in-world (corps-driven). S2-004→008 : recette
prouvée en SIM (corps insuffisant + demande structurée + devise de survie → survie perception/anticipation/
composition-SENSIBLE). **Objectif** : réaliser cette recette DANS la biosphère (stoneage) derrière un flag,
et montrer que le bras d'ablation-perception in-world (`s2_demand_ablation.PerceptionAblatedMamba`)
**effondre la survie (SENSIBLE)** en mode ON — vs NEUTRE en mode OFF (reproduit S2-003). C'est la preuve
in-world que la recette rend G0 causalement perceptif, et le prérequis pour que G1-G4 in-world aient un
gradient de sélection non-nul.

**Non-objectifs (YAGNI)** : pas de nouveau monde ; pas d'évolution complète (main_biosphere) ; pas de modif
de `s2_demand.py` ; le mode est OFF par défaut (strictement non-régressif) ; un seul monde (stoneage).

## 2. La mécanique (mode `cognitive_demand`, guardé, défaut OFF)
Trois conditions de S2-006, réalisées avec des leviers/canaux existants :

1. **Corps INSUFFISANT** — `base_metabolism` relevé (levier natif, world_1:649) ET, en mode ON, les gains
   d'énergie standard (proie/fruit) **suppressés** (bloc guardé) → aucun raccourci corporel/réflexe ne
   survit. Le seul canal d'énergie est la nourriture cognitive.
2. **Demande STRUCTURÉE par la perception** — chaque tick, un **signal** de 2 bits (réutilise `bit_a/bit_b`,
   rendus GLOBAUX dans l'obs en mode ON, world_1:449-455,569) décode une **direction nourricière correcte**
   ∈ {N,S,E,O} = actions de déplacement 0-3. L'agent doit LIRE le signal et se déplacer dans la direction
   signalée. Une politique à direction fixe ne matche que 1/4 des ticks.
3. **Devise de SURVIE** — matcher la direction signalée paie `cog_gain` en ÉNERGIE (`agent["energy"] +=
   cog_gain`, cog_gain > drain net d'un tick). C'est la devise sélectionnée (survie), pas une devise séparée.

**Emplacement** : (a) `src/environments/config.py` — ajouter `cognitive_demand: bool = False` + `cog_gain:
float = 6.0` à `WorldConfig` (défauts non-régressifs). (b) `src/worlds/world_1_stoneage.py` — un bloc
guardé `if getattr(self.config, "cognitive_demand", False):` dans `step()` (récompense signal-matchée +
suppression des gains standard) et dans `get_batch_observations` (signal global dans bit_a/bit_b). Décodage
signal→direction : `dir = 2*(bit_a>0) + (bit_b>0)` ∈ {0,1,2,3}. Défaut OFF → aucun chemin modifié.

## 3. L'agent qui démontre le flip
Deux arms, exécutés par un NOUVEL outil `tools/cognitive_demand_inworld.py` (importe `run_condition`/`WORLDS`
de `s2_demand`, `PerceptionAblatedMamba` de `s2_demand_ablation`, `ablation_verdict` de `demand_marker`) :

- **ORACLE (preuve décisive du monde)** — `CognitiveOracleBatchModel` (nouveau, dans l'outil ; drop-in
  comme `ReflexBatchModel`) : décode `bit_a/bit_b` de l'obs → sort la direction correcte. INTACT : survit
  (matche chaque tick). Sous ablation (obs shuffled) : reçoit le signal d'un pair → rate → s'effondre.
  → prouve que **le monde EXIGE la perception**, indépendamment du crédit.
- **INTRA-VIE (sonde crédit)** — cohorte `use_torch_inworld=True` (`benchmark_mode`) qui APPREND le
  signal→direction via REINFORCE (`_torch_pop.learn_episode`). Rapporte si le crédit in-world l'apprend
  (survie ↑ sur les eras) ; si oui, rejouer l'ablation → SENSIBLE. Issue négative = « le monde demande mais
  le crédit n'apprend pas » = pinpointe le crédit (finding fort, cohérent avec la thèse projet).

## 4. Le test (demand-marker in-world)
Pour ORACLE et (si vivant) INTRA-VIE, comparer survie INTACTE vs ABLATÉE (`PerceptionAblatedMamba`, qui
shuffle l'obs entière → y compris le signal) via `ablation_verdict`, sur stoneage, mode ON. **Contraste
OFF** : le même en mode OFF doit rester NEUTRE (reproduit S2-003). Grille minimale :

| condition | mode | attendu |
|---|---|---|
| oracle intact vs ablé | ON | ratio ≫ 1 → PERCEPTION_DEMANDED (le monde exige) |
| oracle intact vs ablé | OFF | ratio ≈ 1 → NEUTRE (contrôle : la mécanique OFF ne change rien) |
| intra-vie intact vs ablé | ON | SENSIBLE si le crédit a appris ; sinon rapporté honnêtement |

K=12 ères appariées (garde-fou n≥12 de `demand_marker`). Seed fixe, RAG-off (`_disable_kuzu`, repro).

## 5. Tests unitaires (`tests/`)
- `test_cognitive_demand_world.py` : (a) mode OFF → `step`/obs identiques au legacy (non-régression : un
  agent survit/meurt comme avant, gains standard intacts) ; (b) mode ON → un agent à direction FIXE meurt
  (corps insuffisant), un agent qui suit le signal (oracle) survit ; (c) le signal est bien dans l'obs en
  ON et le décodage `bit→dir` est correct ; (d) suppression des gains standard active en ON seulement.
- `test_cognitive_demand_inworld.py` (opt-in `RUN_SLOW`) : smoke — l'outil tourne 1 monde K=2, renvoie un
  dict {within_ratio, verdict} bien formé pour l'oracle.

## 6. Ancrage records & hygiène
EDR-S2-009 (gate G0, tests SDR-G0, adopts REF-DEMAND-MARKER) : le verdict in-world (oracle SENSIBLE en ON /
NEUTRE en OFF ; intra-vie = crédit apprend ou non). `consolidate_records.py` problemes=0 ; `check_record_links`
0 nouvel orphelin. Mettre à jour mémoire `s2-world-demand-thread` + `within-subject-demand-marker`.

## 7. Plan de commits (path-scopés)
1. **World+config** : `config.py` (flag) + `world_1_stoneage.py` (bloc guardé) + `test_cognitive_demand_world.py`.
2. **Outil+run** : `tools/cognitive_demand_inworld.py` (oracle + arms) + `test_cognitive_demand_inworld.py`.
3. **Records** : EDR-S2-009 + REF maj + mémoire (le verdict depuis le run).

## 8. Risques & mitigations
- **Le REINFORCE n'apprend pas la nourriture cognitive** → cohorte meurt, ablation intra-vie sans objet.
  MITIGÉ : l'ORACLE est la preuve décisive du monde ; l'intra-vie est une sonde, pas un bloqueur.
- **Régression non-régressive** : tout est guardé `if cognitive_demand` (défaut False). Test (a) le vérifie.
- **La suppression des gains standard casse un invariant du monde** : la faire uniquement dans le bloc guardé,
  après les gains standard (les remettre à `_s*_bio` snapshot ou soustraire) — préciser dans le plan.
- **Le signal global (bit_a/bit_b) écrase l'usage autel legacy** : uniquement en mode ON ; OFF = legacy.

## 9. Critères de succès
- Mode OFF strictement non-régressif (test (a) vert, suite existante inchangée).
- Mode ON : agent direction-fixe meurt, oracle survit (test (b)).
- Run : oracle **SENSIBLE en ON** (ratio ≫1) et **NEUTRE en OFF** → la recette flip la survie in-world,
  G0 rendu causalement perceptif. Intra-vie : verdict honnête (crédit apprend ou non).
- EDR-S2-009 raccordé, graphe propre.
