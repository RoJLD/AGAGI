# Design D1 — RNG appariement + BaseHarness (`Harness`)

> Spec de conception. Issu du **scan global** (`docs/SCAN_GLOBAL.md`, item Dev D1, « le plus
> critique — socle de validité »). Brainstorm du 2026-06-13. Méthode : Commandement 15.

## Problème

Les comparaisons d'expériences ne sont **pas appariées** et ne sont **pas reproductibles** :

- `main_biosphere.py` ne pose **aucun** `np.random.seed` au boot.
- `robust_hof.robust_evaluate` (prod) et `tools/robust_eval.py` bouclent K ères **sans seed**
  incrémental → chaque condition comparée tire une séquence PRNG différente → **comparaison non
  appariée** → variance entre-conditions gonflée.
- `eval_harness.py` (couche statistique : `powered_eval`/`welch`/`verdict`) *suppose* que chaque tool
  pose son propre seed (`run_seed_fn ... doit poser np.random.seed`) — contrat honoré nulle part dans
  les runners.

Conséquence mesurée par le projet : **5 signaux à peu de seeds se sont évaporés sous puissance**
(EDR 057/075/077/082/083). L'appariement reproductible est le **socle de validité** de toute mesure
science à venir (S2 dummy-vs-champion, 087 langage).

Vérifié sur le code (2026-06-13) : les 3 claims dev D1/D2/D3 du scan sont **réels** ; `async_logger`
n'utilise **aucun** RNG (seul thread concurrent) → seeder le RNG global aux frontières est
**déterministe et sûr**.

## Décisions (brainstorm)

| # | Fork | Choix |
|---|---|---|
| 1 | Périmètre | **RNG appariement + BaseHarness complet + migration des ~60 tools** (migration incrémentale, vérifiée tool par tool) |
| 2 | Archi RNG | **Seed global aux frontières via `SeedManager`** (≈0 réécriture des 168 sites `np.random.X`) ; Generator `default_rng` exposé pour le code NEUF |
| 3 | Forme d'API | **Composition** — un objet `Harness` qu'on instancie (`with Harness(...) as h:`), pas d'héritage |

## Architecture

Nouveau module **`src/seed_ai/harness.py`**. `eval_harness.py` (stat) reste inchangé et devient
collaborateur. Séparation des rôles : `eval_harness` = *comment on mesure le bruit* ;
`harness` = *comment on pose le déterminisme + l'exécution (seed, async_logger, I/O)*.

```
src/seed_ai/harness.py
├── SeedManager(base_seed)
│     .seed_boundary(i)      # np.random.seed(base_seed + i) — déterministe, aux frontières
│     .rng                   # np.random.default_rng(base_seed) — pour code NEUF qui veut l'isolation
│     .resolve(seed|None)    # None → tire une graine d'entropie ET la logge (repro a posteriori)
│
└── Harness(seed=None, name="exp", robust_K=3, with_db=True)   # objet de composition (context manager)
      __enter__ : résout+logge le seed, seed boot, démarre async_logger, attend la DB
      __exit__  : stop/flush async_logger (même en cas d'exception)
      .eval_robust(config, genome, run_era_fn, K=None, num_agents=20) → float APPARIÉ (seed base+i/ère)
      .powered(conditions, run_seed_fn, seeds)  → wrap eval_harness.powered_eval, seed injecté
      .progress(total, label)                   → wrap tools/progress.Progress
      .save(data)                               → results/<name>_<seed>.json (+ seed + commit court)
```

**Frontières (hors périmètre, volontaire — YAGNI) :**
- Pas de réécriture des 168 sites `np.random.X` vers `Generator` (le seed global aux frontières
  suffit pour l'appariement ; le rewrite résoudrait un problème qu'on n'a pas — l'isolation par
  tirage).
- Pas de versioning config-hash complet (roadmap Dev item 7, séparé) — on logge seulement seed +
  commit court dans le JSON.
- Pas de correction multi-comparaisons (Bonferroni/Holm — garde-fou stat, séparé).
- Le `Harness` absorbe le **boilerplate** (seed, cycle async_logger, attente DB, Progress), pas la
  logique métier des tools.

## L'appariement (le cœur de D1)

`eval_robust` seede `base_seed + i` **avant** de construire l'ère `i`. Deux conditions (ex. FIABLE vs
SOLO) lancées avec le **même `base_seed`** voient l'ère `i` partir du **même monde initial** (placement
ressources, init agents) → différence appariée → variance entre-conditions effondrée. C'est le
*paired t-test* transposé : comparer A et B sur les mêmes unités (seeds-mondes) retire la variance
inter-unités de l'erreur.

**Limite assumée (honnêteté) :** avec un RNG global *unique*, l'appariement est un **block-pairing des
conditions initiales**, pas un appariement parfait de trajectoire. Dès que des génomes distincts
agissent, ils consomment le flux PRNG à des rythmes différents → divergence après le 1er tirage
genome-dépendant. On apparie la **plus grosse source de variance** (le monde de départ), pas toute.
L'appariement parfait (flux RNG séparés monde/agents) = chemin `Generator`, **différé** (non requis
pour le gain D1).

## Seed par défaut : provenance sans changement de comportement

Gated comme `robust_hof_K` : `seed=None` → tire une graine d'entropie, la **logge**
(`[HARNESS] seed=1234567`) et la sauve dans le JSON → tout run "aléatoire" de prod devient
**rejouable a posteriori**. `seed=<int>` fixe → run pleinement reproductible (tests, benchmarks
appariés).

- `main_biosphere` : ajout `config.experiment_seed` (défaut `None`), seed boot + log.
- `robust_hof.robust_evaluate` : accepte un kwarg `seed`, seede par ère (`seed + i`).
- **Aucune régression de comportement** par défaut : sans seed explicite, la prod reste stochastique,
  mais traçable.

## Migration des tools (incrémentale, vérifiée)

Migration « complet d'un bloc » mais **par tool, chacune vérifiée** (tests verts + smoke) avant la
suivante, en commits atomiques. Si un tool résiste (structure exotique) → noté, on continue (pas de
big-bang).

1. **Pilotes (preuve du pattern)** : `tools/robust_eval.py` + `src/seed_ai/robust_hof.py` (prod) — les
   2 cœurs de l'appariement.
2. **Vague comparative** (l'appariement y paye le plus) : `coevolve_language`, `lang_on_competent`,
   `func_benefit`, `refgame_bio`, `fiabiliser`, `aligned_selection`, …
3. **Reste** (~50) : mécaniquement — remplacer le boilerplate `async_logger.start()/wait/stop` + ajout
   du seed.

## Tests & non-régression

- **Reproductibilité** : `eval_robust(seed=42)` deux fois → résultat identique (au flottant près).
- **Appariement** : même `base_seed`, deux génomes → même monde initial (assert placement ressources /
  init identiques au tick 0).
- **Indépendance** : `seed_boundary(i)` pour `i` différents → ères différentes (anti-bug « tout
  identique »).
- **Cycle async_logger** : `with Harness()` démarre/arrête proprement ; **dégradation gracieuse** si DB
  absente (`with_db=False` ou timeout → warn, pas de crash).
- **Non-régression** : les 146+ tests existants restent verts ; les tools pilotes produisent un verdict
  cohérent avant/après migration.

## Critères de succès

1. `Harness` + `SeedManager` livrés, testés isolément.
2. `robust_hof` (prod) et `robust_eval` (tool) appariés et reproductibles — un même `seed` rejoue à
   l'identique.
3. `main_biosphere` logge sa graine à chaque run (provenance).
4. Vague comparative migrée ; reste des tools migrable mécaniquement.
5. Suite de tests verte, +5 tests harness ciblés.
