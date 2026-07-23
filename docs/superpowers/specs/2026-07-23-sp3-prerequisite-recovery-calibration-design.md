# SP-3 — Calibrer le demand-marker sur un DAG de prérequis (os-taxonomy comme clé de réponse)

**Date** : 2026-07-23
**Statut** : design validé, prêt pour plan d'implémentation
**Vision parente** : AGI-Taxonomy (backlog `docs/roadmap/PRIORITES_ET_DETTES.md`, P4.3)

---

## 1. Contexte et vision parente

`withmarbleapp/os-taxonomy` (Marble Skill Taxonomy) est un graphe de prérequis de l'apprentissage
primaire : 1 590 micro-topics, 3 221 arêtes `topicId → prerequisiteId` taggées `strength ∈ {hard, soft}`
avec une `reason`, en JSON, double licence ODbL 1.0 + CC BY-SA 4.0.

La vision **AGI-Taxonomy** (parquée en backlog, hors scope de ce spec) est de construire, *dans ce format*,
un graphe de prérequis dont les nœuds sont des **capacités-demandes in-world** vers un world-model — chaque
arête une claim falsifiable, chaque nœud un critère d'évidence **within-subject** (`REF-DEMAND-MARKER`),
plus rigoureux que les critères d'évidence humains de os-taxonomy. Elle se décompose en quatre
sous-projets : SP-1 schéma, SP-2 peupler depuis les records, **SP-3 calibrer (ce spec)**, SP-4 forker/publier.

**SP-3 est le maillon discriminant** : avant d'investir dans SP-1/SP-2, on mesure si l'instrument sur lequel
tout repose — l'ablation within-subject — sait récupérer un DAG de prérequis *connu*. Réflexe du dépôt :
ne pas raisonner au lieu de mesurer, et calibrer l'instrument avant de l'appliquer à l'inconnu.

## 2. Objectif et question

**Question** : le demand-marker (`tools/demand_marker.py::ablation_verdict`, via ablation within-subject
d'un prérequis) récupère-t-il les arêtes d'un DAG de prérequis **imposé**, tout en no-opant sur les
non-arêtes — **y compris un non-prérequis corrélé** ?

**Go / no-go** :

- **PASS** → l'ablation within-subject garde sa spécificité sous confond corrélé → SP-2 (peupler le graphe
  AGI par ablation) est sain.
- **FAIL** → le marqueur faux-positive sur les non-prérequis corrélés → l'ablation *seule* ne récupère pas
  un DAG ; SP-2 exigera une ablation **conditionnelle** (contrôler les ancêtres). Appris à coût quasi nul.

## 3. Le payload scientifique (ce qui rend SP-3 non-tautologique)

`ablation_verdict` est **déjà** calibré (P2.4) — mais sur `world_demand_marker_probe.py`, un monde à **un
seul canal, sans confond**. Un vrai DAG a de la **structure de corrélation** : prérequis partageant des
ancêtres, clusters, mélange hard/soft. Le mode d'échec inconnu : un non-prérequis A′ corrélé à un vrai
prérequis A pourrait faux-positiver. Un DAG jouet inventé ne sait pas fabriquer cette corrélation
honnêtement ; le graphe os-taxonomy, si — **c'est l'argument pour la clé de réponse externe**. La
non-tautologie est portée par le contrôle de spécificité sur A′ corrélé, exactement comme
`test_decomposition_is_not_a_tautology_on_a_linear_ground_truth` pour le verdict bilinéaire.

## 4. Approche retenue : A1 (score imposé, analytique)

| Approche | Principe | Coût | Décision |
| --- | --- | --- | --- |
| **A1 Score imposé** | Compétences INJECTÉES (façon `partial_oracle`) ; score d'acquisition de B *gaté par construction* sur ses prérequis. Pas d'apprentissage. | pur numpy, aucun bail, aucune sim | **RETENUE** |
| A2 Learner qui ajuste | Hill-climb une politique pour acquérir B (façon `fit_policy`) | + confond d'optimiseur, + lent | rejetée |
| A3 Monde de survie réel | Topics = actions gatées dans `Biosphere3D` | lourd, **bail kuzu** | rejetée (overkill pour calibrer) |

A1 est le plus fidèle à `ground_truth_worlds.py` : la réponse est connue *par construction*, et le seul
confond mesuré (corrélation du graphe) est **imposé explicitement**, non mélangé à un bruit d'optimiseur.

## 5. Architecture

Trois unités à responsabilité unique, testables indépendamment.

### 5.1 Adaptateur os-taxonomy → sous-graphe

- **Entrée** : un sous-ensemble vendu de `topics.json` / `dependencies.json` sous `data/os_taxonomy/`
  (attribution ODbL/CC BY-SA dans un `NOTICE`). **Pas** les 1 590 nœuds pour v0 — un cluster.
- **Sortie** : `{nodes: [...], edges: [{topic, prereq, strength}], non_edges: [...]}` — un dict pur.
- **Dépend de** : rien (lecture JSON). Testable sur une fixture minuscule.

### 5.2 Monde-jouet à gate imposé (dans `tools/ground_truth_worlds.py`)

- Pur numpy, à côté de `partial_oracle` (pas de sous-classe `Biosphere3D`).
- Impose : acquisition-score(B) = f(compétences des prérequis de B). `strength="hard"` → gate PLEIN
  (ablation de A effondre B) ; `"soft"` → gate PARTIEL (ratio > 1 mais < hard).
- **Métrique VIVANTE** : un revenu plat obs-indépendant façon `gt_income`, pour que le no-op sur non-arête
  se démontre hors plancher/plafond (le piège de WARM-002 / EDR-AUDIT-001).
- **Corrélation imposée** : un non-prérequis A′ partageant un ancêtre avec A ; la force de corrélation est
  réglable — c'est la **dose** du test de spécificité.
- **Dépend de** : le sous-graphe (5.1). Réponse connue analytiquement.

### 5.3 Instrument de récupération (`tools/prerequisite_recovery_probe.py`)

- `run_prerequisite_recovery_probe(subgraph, seeds≥12, ...)` — le nom trippe **volontairement**
  l'heuristique `run_\w*probe` du cliquet (sinon il entrerait non-calibré, cf. `run_linear_sanity`).
- Pour chaque arête candidate `(B, A)` : bras intact (compétence A intacte) vs ablaté (A retirée), score
  d'acquisition de B → `ablation_verdict(intact, ablated, intervention_verified=True, floor=…, ceiling=…)`.
- `prerequisite_recovery_verdict(...)` (`*verdict*` → détecté → calibré aussi) : agrège en **recouvrement
  de graphe** — précision / rappel des arêtes récupérées vs imposées.
- **Dépend de** : 5.2 + `ablation_verdict`.

## 6. Flux de données

```text
data/os_taxonomy/*.json ──(5.1 adaptateur)──▶ subgraph {edges, non_edges, strength}
                                                     │
                                          (5.2 monde-jouet imposé)
                                                     │  score d'acquisition gaté
        pour chaque arête candidate (B, A) ─────────┤
                                                     ▼
     intact = score(B | A intacte)   ablated = score(B | A retirée)   [×≥12 seeds]
                                                     │
                                    ablation_verdict(intact, ablated, …)
                                                     ▼
              verdict par arête ──(5.3 agrégation)──▶ précision / rappel du recouvrement
```

## 7. Les trois formes de test canoniques (dette de calibration)

Dans `tests/sandbox/test_instrument_calibration.py` + entrée dans le dict `CALIBRATED` (clé =
`(fonction, branches)`), pour les DEUX instruments détectés :

1. **no-op EXACT (spécificité)** : ablater un non-prérequis → ratio ≈ 1, `X_DECOY` — **y compris le
   non-prérequis corrélé** (le test qui décide le go/no-go).
2. **prédiction / linéarité** : le ratio récupéré suit la force de gate imposée.
3. **monotonie (direction)** : hard > soft > non-arête ≈ 1, sans chevauchement d'ères.

**Levée d'ambiguïté (soft)** : une arête `soft` est évaluée par le **ratio** (monotonie §7.3), PAS par la
catégorie de verdict. Un gate soft peut légitimement produire un ratio dans la bande `INCONCLUSIVE` de
`ablation_verdict` (entre `decoy_ceiling=1.3` et `collapse_factor=1.5`) — ce n'est **pas** un échec. Seuls
`hard` (attendu `X_DEMANDED`) et non-arête (attendu `X_DECOY`) portent une attente de catégorie ; le go/no-go
repose sur la spécificité (§7.1), pas sur la classification des soft.

Contrôle anti-tautologie explicite (générateur A du pré-vol) : l'instrument doit pouvoir rendre **les deux
issues** — récupérer un vrai prérequis ET rejeter un non-prérequis.

## 8. Intégration aux rituels obligatoires

- **Pré-vol** (`tools/experiment_preflight.py`) : `declare_design(unité=seed)` ; générateur A (les deux
  issues) ; contrôle positif ; no-op ; `assert_no_aliasing` — l'ablation de A ne doit **pas** muter le
  canal de B par un état partagé (la signature du bug EDR-WARM-007).
- **Cliquet de calibration** : les deux instruments s'ajoutent à `CALIBRATED` avec leur cas de test **dans
  la même passe** — sinon le hook pre-commit `check_instrument_calibration.py` bloque (et c'est le
  comportement voulu).
- **Licence** : sous-graphe vendu avec attribution ODbL 1.0 + CC BY-SA 4.0 (`NOTICE` dans
  `data/os_taxonomy/`). Usage commercial permis avec attribution ; toute base dérivée reste ouverte.
- **Record** final (EDR/CALIB) avec frontmatter `gate:` / `tests:[…]` / `adopts:` ou `foundational`,
  sinon `check_record_links.py` le signale orphelin. Les issues NÉGATIVES (FAIL du go/no-go) se gravent au
  même titre que PASS.

## 9. Unité de réplication et bornes de coût

- **Unité = seed** (pas l'arête, pas l'agent). Chaque verdict d'arête agrège ≥12 seeds (le `n_floor` de
  `ablation_verdict`).
- **Métrique VIVANTE obligatoire** : score d'acquisition entre plancher et plafond déclarés (`floor=` /
  `ceiling=` passés à `ablation_verdict`).
- **Coût borné DANS le design** : pur numpy, aucun bail, aucun run long. Smoke à petit n d'abord (débit),
  puis n=12+ pour le verdict. Pas d'extrapolation depuis un préfixe court.

## 10. Portée v0 (YAGNI)

Un seul topic B avec **1 hard + 1 soft + 1 non-prérequis corrélé**, tiré d'un vrai cluster os-taxonomy.
Suffit à exercer les trois formes de test et le contrôle de spécificité corrélée. Multi-saut, chaînes
longues, graphe complet → itérations ultérieures, hors v0.

## 11. Critères de succès

Le spec est **livré** quand :

1. Les deux instruments existent, détectés par le cliquet, avec leur cas dans `CALIBRATED`.
2. Les trois formes de test passent, dont le no-op sur non-prérequis **corrélé**.
3. Le pré-vol passe (design déclaré, générateur A, no-op, no-aliasing).
4. Un record grave le verdict go/no-go (PASS ou FAIL), frontmatter conforme.

## 12. Hors scope (backlog)

SP-1 (schéma capability-demand graph), SP-2 (peupler depuis gates/EDR/tétralogie), SP-4 (forker/publier
`agi-taxonomy`, contribuer les critères within-subject). Chacun son cycle spec → plan → run.

## 13. Risques et pièges déjà connus du dépôt

- **Métrique morte** → no-op dégénéré pris pour inertie (WARM-002 / EDR-AUDIT-001) : garde `gt_income`
  + assertion `floor < médiane < ceiling`.
- **Aliasing d'état** (EDR-WARM-007) : l'ablation d'un prérequis doit perturber l'ENTRÉE, pas une vue de
  sortie partagée. `intervention_verified=True` seulement après vérification, `assert_no_aliasing` armé.
- **Tautologie** : sans le contrôle de spécificité corrélée, l'instrument « récupère » tout — le test
  §7.1 est ce qui l'empêche.
- **n < 12** : aucun verdict, ni positif ni nul (garde `n_floor` de `ablation_verdict`).
