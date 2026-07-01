# Design — Évolvabilité du stockage dans FamineWorld (la gratification différée est-elle apprise par le substrat ?)

> **Date** : 2026-06-30 · **Statut** : design validé (brainstorming), avant plan.
> **Suite directe** d'EDR-118 (FamineWorld EXIGE l'intelligence — mais via TRANSFERT de compétence
> générale, pas via le stockage : la mécanique de stockage est réelle mais INERTE dans S2).
> **Sert** : `SDR-G1` (north-star généralisation) — étape préalable à la re-mesure du transfert.

---

## 1. Question (problème)

EDR-118 a établi que `FamineWorld` est un 2ᵉ monde réel qui EXIGE l'intelligence, mais avec un caveat
central : le champion testé est **stoneage-évolué**, donc son avantage de survie (~4×) reflète le
**transfert d'une compétence générale** (forage, gestion d'énergie), **pas** l'usage de la mécanique de
**stockage** (cache d'inventaire auto-consommé). Le stockage est prouvé causalement distinct en test
unitaire (stockeur 55 ticks vs non-stockeur 24) mais reste **inerte** dans le banc S2 (aucune condition
ne stocke délibérément + `benchmark_mode` interdit l'évolution).

**La question AGI-critique** : si on **évolue** une population *dans* FamineWorld, le substrat
**apprend-il** la gratification différée (stocker en abondance pour survivre la famine) ? C'est un test
direct de l'évolvabilité d'une compétence à horizon temporel — la classe de problème où le substrat a
échoué jusqu'ici (EDR 105/108/110/113/116/117).

## 2. Le défi de mesure (le cœur)

« Le champion famine survit mieux » NE prouve PAS le stockage (c'est le caveat ⭐ d'EDR-118 : la survie
peut venir de la compétence générale). Il faut **isoler causalement** la contribution du stockage. Choix
validé : **ablation + corroboration comportementale**.

- **Ablation (preuve causale)** : évoluer avec le cache actif, puis mesurer la survie **cache ON vs cache
  OFF** sur la population évoluée. Si la survie **s'effondre** cache OFF → les agents en **dépendent** →
  le stockage porte la survie. **Contrôle** : la même ablation sur le champion **stoneage** (qui ne doit
  PAS dépendre du cache) neutralise « le cache aide n'importe qui ».
- **Comportement (corroboration)** : compter les fruits portés (`type in {"Fruit","_FruitReserve"}`) à la
  transition abondance→famine. L'évolué-en-famine en porte-t-il plus que le stoneage ?

## 3. Architecture — héritage + outil dédié

Trois pièces ; aucune réécriture du moteur ; aucun nouveau slot I/O ; aucune touche au HoF.

### 3.1 Seam d'ablation (`src/worlds/world_famine.py`)
`self.cache_enabled = True` dans `__init__` (après `starve_threshold`), conditionnant les **deux** appels
`_auto_consume_cache` (pré-step et post-step). Défaut `True` = non-régressif (EDR-118/G0 inchangés). À
`False` : le cache ne se consomme plus → les fruits portés deviennent du poids mort (le coût de portage
`carry_weight×0.5/tick` reste facturé, c'est voulu : l'ablation retire le bénéfice, pas le coût).

### 3.2 Probe `tools/famine_storage_probe.py`
1. **Évolution tabula-rasa dans famine** : réutilise la machinerie d'ères (`make_run_era_fn` /
   `CurriculumRunner` avec `WorldStage("famine")`, `c_floor` impossible → tourne `max_eras`), `metric=
   survival`, `deterministic=True`. **Retient le génome du champion en mémoire** (le champion est un agent
   de `env.agents` sélectionné par `life_score` ; on capture son génome — évite le rechargement KuzuDB).
   On évolue pour la **SURVIE**, **jamais** en récompensant le stockage (sinon on *enseigne* au lieu de
   *tester l'émergence*).
2. **Ablation A/B** : clone le champion famine dans `FamineWorld` (cohorte fixe, `benchmark_mode=True`),
   mesure la survie médiane avec `cache_enabled=True` vs `False`.
3. **Contrôle stoneage** : même ablation A/B sur le champion stoneage (HoF, `load_champion_genome`).
4. **Comportement** : pendant les runs cache-ON, compte les fruits portés à la transition
   abondance→famine (inspection directe de `agent["inventory"]`, pas de logging lourd).

### 3.3 Verdict (logique)
Métrique centrale = **delta d'ablation** par seed : `Δ = médiane_survie(cache ON) − médiane_survie(cache OFF)`.
- **ÉMERGE** si `Δ_famine` significativement > `Δ_stoneage` (apparié par seed, test de signe, n≥8) ET
  `Δ_famine` substantiellement > 0 → le stockage est une compétence **évoluée**, load-bearing.
- **N'ÉMERGE PAS** si `Δ_famine ≈ Δ_stoneage ≈ 0` → la survie vient de la compétence générale, pas du
  stockage → **finding substrat** (la gratification différée n'est pas évolvable à bon marché ;
  convergence EDR 105/108/110/113/116/117).
- Corroboration : fruits-portés(évolué) > fruits-portés(stoneage) attendu si ÉMERGE ; incohérence
  comportement↔ablation = caveat explicite.

## 4. Plan de run (smoke → power)

1. **Smoke** : 1-2 seeds, ~15-20 ères. Valide le pipeline (évolution famine + extraction génome +
   ablation + compte-fruits tournent ; signal plausible). Pas un verdict.
2. **Power** : si le pipeline tient, **n≥8 seeds appariés** → verdict (leçon EDR-116 : le signal
   s'évapore sous puissance).
3. **EDR NNN** (`gate: G1`, `tests: [SDR-G1]`) : protocole, `Δ_famine` vs `Δ_stoneage`, comportement,
   verdict ÉMERGE / N'ÉMERGE PAS, caveats.

## 5. Composants

- **Modify** `src/worlds/world_famine.py` — seam `cache_enabled` (2 lignes conditionnant les appels).
- **Create** `tools/famine_storage_probe.py` — évolution famine + extraction champion + ablation A/B +
  contrôle stoneage + compte-fruits + verdict.
- **Create** `tests/test_famine_storage_probe.py` — seam d'ablation (cache OFF → pas de consommation) ;
  pureté du calcul de verdict (delta, test de signe) ; compte-fruits déterministe.
- **Runs + EDR** : smoke puis power → EDR `tests:[SDR-G1]`.

## 6. Garde-fous anti-théâtre

1. **Évoluer pour la survie, jamais récompenser le stockage** — sinon on enseigne au lieu de tester
   l'émergence.
2. **Ablation = inférence causale** (pas corrélationnelle) ; le contrôle stoneage neutralise l'effet
   « cache aide tout le monde ».
3. **`deterministic=True`** (mémoire ambiante stoppée avant la boucle, [[biosphere-ambient-memory-nonrepro]]).
4. **n≥8 pour le verdict** (leçon EDR-116).
5. **Seam défaut `True`** = G0/EDR-118 byte-inchangés (non-régression).
6. **Honnêteté du N'ÉMERGE PAS** : c'est un résultat majeur (finding substrat), pas un échec — à consigner
   avec la même rigueur qu'un ÉMERGE.

## 7. Tests (TDD)

- **Seam ablation** : `FamineWorld` avec `cache_enabled=False` ne consomme PAS le cache (un agent affamé
  portant un fruit ne voit pas son énergie remonter ; le fruit reste / devient poids mort). Avec `True`
  (défaut), comportement EDR-118 inchangé.
- **Verdict pur** : fonction `compute_emergence_verdict(deltas_famine, deltas_stoneage)` → test de signe
  apparié, labels ÉMERGE / N'ÉMERGE PAS / NEUTRE selon seuils ; déterministe, sans I/O.
- **Compte-fruits** : helper de comptage des fruits/réserves dans un inventaire donné = exact.
- **Non-régression** : `tests/test_world_famine.py` (8 tests) reste vert (seam additif défaut True).

## 8. Périmètre & non-buts

- **Dans le périmètre** : seam d'ablation + probe + tests + smoke + (si pipeline OK) power + EDR.
- **Hors périmètre** : re-mesure G1 transfert stoneage/soup→famine (**sous-chantier suivant**, après ce
  verdict) ; récompense de stockage ; nouveau slot I/O ; persistance du champion famine au HoF.

## 9. Interprétation (quel que soit le verdict)

- **ÉMERGE** : le substrat APPREND la gratification différée quand le monde l'exige → FamineWorld débloque
  une vraie mesure G1 (transfert d'une compétence que stoneage n'enseigne pas) ; contredit partiellement
  le verrou substrat → piste forte.
- **N'ÉMERGE PAS** : le substrat ne sait pas apprendre l'horizon temporel même sous demande directe →
  finding substrat fondamental, convergeant avec EDR 105/108/110/113/116/117 et l'axe gradient/torch
  (ADR-003, EDR-117) → oriente vers un substrat à mémoire/horizon explicite ou différentiable.

## 10. Critères de succès du chantier

1. Seam `cache_enabled` livré, tests verts (ablation + non-régression des 8 tests famine).
2. Probe livré : évolue en famine, extrait le champion, lance l'ablation A/B + contrôle stoneage +
   compte-fruits, calcule le verdict. Tests purs verts.
3. Smoke réel : le pipeline tourne, signal plausible.
4. (Si pipeline OK) Power n≥8 → EDR consigné (`tests:[SDR-G1]`), graphe vert.
