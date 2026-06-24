# EDR 100 — Sous-décomposer la phase biologie : métabolisme, terrain ou carry ?

**Statut :** pré-enregistrement (gelé avant données).
**Date :** 2026-06-24.
**Lignée :** 090→093→094→098→099 (drain = phase **biologie**, 90%) → **100**.
**Numéro :** 100 vérifié libre (aucune session parallèle).

## 1. Motivation

EDR 099 a décomposé le drain intrinsèque de Lewis (~12/tick, famine au tick 5, à `N_APEX=0`) en 4 phases et a
nommé le coupable : la phase **biologie** (`_resolve_biology`) porte **90%** du drain (10.81/tick). EDR 100
**sous-décompose** cette phase pour isoler le sous-poste dominant et **cibler** le rééquilibrage — première
intervention chirurgicale de la chaîne, après cinq diagnostics.

Sous-postes de `_resolve_biology` (à `N_APEX=0` : nuit OFF, heal gardé OFF car hp=100) :

- **métabolisme** (`world_1_stoneage.py:637`) : `base_metabolism(0.25) × phenotype_energy_drain`. NB : le terme
  d'activation de compute (`metabolic_cost_coef × last_activation_cost`, l.621-623) a `coef=0.0` par défaut et a
  été **réfuté** par la session NAS — ici c'est le métabolisme de **base phenotype-scalé** qui est suspect, **non
  testé**. `phenotype_energy_drain` est un **trait évolué du génome** ;
- **terrain** (l.640) : drain de biome (`plains/forest/water/desert_drain`) ;
- **carry** (l.651) : `carry_weight × 0.5` (poids d'inventaire) ;
- **autres** : gains (approach_reward l.647, forage Fruit +20 l.657) + jump/duck (l.669) + heal (off).

## 2. La prétention (mesure, pas de variable manipulée)

> À `N_APEX=0`, le drain de la phase biologie (~10.8/tick) est porté **majoritairement par un sous-poste
> identifiable** de `_resolve_biology`. On mesure la sous-décomposition et on nomme le coupable.

Pas de variable manipulée (Commandement 15 trivialement satisfait) : observation instrumentée de la condition
gelée Lewis-vide. Tout fixe (`N_APEX=0`, `forage_payoff=3`, `base_metabolism=0.25`, `leurre_frac=0`,
`PREY_COUNT=15`, `num_agents=24`, `max_ticks=300`), champions répliqués, pas d'évolution/langage.

## 3. Métriques & règle de verdict (gelées)

- **Métrique primaire :** énergie moyenne drainée **par tick et par agent** par sous-poste de la phase biologie
  (`metab`, `terrain`, `carry`, `autres`), agrégée sur les ticks de vie × agents × R×n_eval ères.
- **Sous-décomposition (les 4 sous-deltas télescopent vers le delta biologie par construction) :**
  - `metab = s0 − s1` (avant/après l.637) ;
  - `terrain = s1 − s2` (avant/après l.640) ;
  - `carry = s3 − s4` (avant/après l.651) ;
  - `autres = (s2 − s3) + (s4 − s5)` = approach_reward + forage + jump + heal (le reste de `_resolve_biology`).
  - `s0` = entrée de `_resolve_biology` ; `s5` = sortie. `metab+terrain+carry+autres = s0 − s5` = delta biologie.
- **Sous-produit :** part (%) de chaque sous-poste dans le drain biologie (`bio_net = somme des 4`).

| Condition | Verdict |
|---|---|
| **metab** porte > 50% du drain biologie | **TARIF=METABOLISME** — `base_metabolism × phenotype_energy_drain` ; levier = `phenotype_energy_drain` (trait évolué : phénotype trop gourmand pour Lewis) ou `base_metabolism`. |
| **terrain** porte > 50% | **TARIF=TERRAIN** — drains de biome de Lewis ; géographie trop coûteuse. |
| **carry** porte > 50% | **TARIF=CARRY** — poids d'inventaire ; les champions traînent trop. |
| aucun (metab/terrain/carry) > 50% | **DRAIN BIO DIFFUS** — réparti ; lever exige plusieurs ajustements. |

`autres` n'est pas une cible de tarif (il contient des **gains**, deltas négatifs) : le verdict porte sur les 3
sous-sinks {metab, terrain, carry}. Seuil **50% du drain biologie** gelé.

## 4. Paramètres pré-enregistrés (gelés)

| Paramètre | Valeur | Note |
|---|---|---|
| `N_APEX` | 0 | monde vide (isole le drain intrinsèque) |
| `forage_payoff` | 3 | 085 (fixe) |
| `base_metabolism` | 0.25 | sweet-spot 085 (fixe) |
| `leurre_frac` | 0 | létalité 0 |
| `PREY_COUNT` | 15 | forage régulier |
| `max_ticks` | 300 | (mort ~tick 5 ; borne large) |
| `num_agents` | 24 | comme 099 |
| `n_eval` | 8 | ères par répétition |
| `R` | 4 | répétitions appariées |
| seuil de sous-poste dominant | 50% (du drain biologie) | gelé |
| `trace_energy_sinks` | `True` (mesure) | défaut `False` partout ailleurs |

## 5. Outillage & architecture

- **Code de production (extension opt-in de l'instrumentation 099, défaut OFF → inerte) :**
  - `src/worlds/world_1_stoneage.py` : **6 sous-captures** dans `_resolve_biology`, gardées par
    `if getattr(self.config, "trace_energy_sinks", False):` :
    - entrée (`s0`), après l.637 (`s1`), après l.640 (`s2`), avant l.651 (`s3`), après l.651 (`s4`), sortie
      (`s5`) ; puis **enregistrer** `agent["_e_bio"]` cumulatif `{metab, terrain, carry, autres}` (4 deltas).
  - **Inertie garantie :** sans `trace_energy_sinks=True`, ces lignes ne s'exécutent pas → `_resolve_biology`
    byte-identique → non-régression (les 18 tests 099 restent verts).
  - **Réutilise** le flag `trace_energy_sinks` existant (099) — aucun nouveau champ config.
- **Harnais — extension DRY de `tools/lewis_survival_sweep.py`** (mergé) :
  - `_measure_drain(...)` : agrège AUSSI `agent["_e_bio"]` (normalisé par âge), renvoie en plus
    `{"bio_metab", "bio_terrain", "bio_carry", "bio_autres"}` (moyennes/tick) — rétro-compatible (clés ajoutées).
  - `_verdict_bio(bio) -> str` (pur) : 4 branches §3 selon la part > 50% du `bio_net = metab+terrain+carry+autres`.
  - `_report_drain(...)` : ajoute une **sous-table biologie** (4 sous-postes + %) et le verdict biologie.
  - `main_decompose(...)` : inchangé dans sa signature ; affiche désormais les 4 phases ET la sous-table biologie.
- **Réutilisé inchangé :** `_setup_critical` (`n_apex=0`), `_disable_kuzu`, `Harness`, `seed_at`, hooks 099.
- **Reproductibilité :** `_disable_kuzu()` + `Harness(with_db=False)` ; `seed_at` par ère ; lecture read-only.

## 6. Tests (TDD)

- **Inertie (non-régression) :** une ère avec `trace=False` ne pose pas `_e_bio` ; les 18 tests 099 restent verts.
- **Traçage :** avec `trace=True`, les agents portent `_e_bio` avec les 4 clés (`metab, terrain, carry, autres`) ;
  les 4 sous-deltas somment au delta biologie de `_e_phases["biologie"]` (à epsilon près) ; `autres` peut être
  négatif (gains) → pas d'assertion de non-négativité.
- `_verdict_bio` (pur) : 4 branches exactes (metab>50 / terrain>50 / carry>50 / diffus).
- `_measure_drain` : renvoie les clés `bio_*` en plus, reproductible (seedé).
- `main_decompose` : sortie inclut la sous-table biologie + un `bio_verdict` ∈ 4 valeurs, reproductible.

## 7. Plan d'exécution

1. Implémenter + tester (sub-agent-driven, TDD) : sous-captures `_resolve_biology` → harnais.
2. **Run direct** : smoke réduit, puis `main_decompose(seed=<S>)` → 4 phases + sous-table biologie + verdict bio.
3. Écrire l'EDR 100 selon la branche (TARIF=METABOLISME / TERRAIN / CARRY / DIFFUS) et amorcer l'EDR 101.

## 8. Garde-fous

- Sous-captures **strictement gardées** par `trace_energy_sinks` (défaut False) → inertes pour 087-099 et
  sessions parallèles ; non-régression testée.
- `N_APEX=0` → correctif `_setup_critical` (monde vide) déjà validé 094.
- **Cohérence inter-niveaux :** vérifier au run que `bio_metab+terrain+carry+autres ≈ phase biologie` d'EDR 099
  (~10.8/tick) — sinon les sous-captures ratent un poste.
- `_disable_kuzu()` + `seed_at` ; lecture `_e_bio` post-ère read-only ; normalisation par âge.
- Worktree `worktree-edr100-biology-decompose` sur `main` (inclut #48) ; commits path-scopés (fichier prod
  partagé + harnais + tests — `git -C add` exact, jamais `git add -A`).

## 9. Provenance attendue

`results/lewis_drain_decompose_<seed>.json` (étendu) : phases (4) + sous-postes biologie (metab/terrain/carry/
autres valeur+%) + `bio_verdict`. Outils : `tools/lewis_survival_sweep.py` (étendu), `src/worlds/world_1_stoneage.py`
(sous-hooks opt-in). Lignée : 090→093→094→098→099→**100**.
