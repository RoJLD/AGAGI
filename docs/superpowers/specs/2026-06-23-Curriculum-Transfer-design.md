# Design — Harnais Ratio de Transfert (Dev #3, mesure)

> Spec de conception. Chantier moteur #1 (priorité audit 2026-06-23). Mesure le cœur scientifique du
> CurriculumRunner : *le curriculum développemental transfère-t-il mieux que tabula-rasa ?* Forme S2
> (expérience appariée multi-seed + provenance). Brainstorm 2026-06-23.

## 1. Problème

L'audit a montré que le CurriculumRunner n'est pas vraiment « dormant » : `main_curriculum.py` le câble
(`run_curriculum()` → transcript), la boucle intra-monde est déjà extraite (`make_run_era_fn`), et un
hook explicite (`run_curriculum(manage_logger=False)`) annonce *« utile pour le harnais Ratio de Transfert »*.
**Ce harnais n'a jamais été écrit.** Sans lui, brancher le curriculum serait du théâtre : on le ferait
tourner sans savoir s'il *aide*. Le livrable, c'est l'**expérience falsifiable** que l'infra attendait.

## 2. Décisions (figées)

| # | Fork | Choix |
|---|---|---|
| 1 | Périmètre | **Harnais de transfert seul** (réutilise `run_curriculum`/`make_run_era_fn`) ; *pas* d'opt-in main_biosphere |
| 2 | Mesure | **Option A — budget compute égal** : T ères développementales vs T ères toutes sur la cible |
| 3 | Symétrie | Bras tabula-rasa = `CurriculumRunner` à **un seul stage** (`c_floor=1.1` → ne diplôme jamais → exactement T ères) |
| 4 | Stat | Apparié multi-seed : `ratio` par seed → **médian + test de signe** (binomial exact, sans dépendance) |
| 5 | Provenance | `Harness.save` → `results/curriculum_transfer_<seed>.json` → dashboard via le ledger C1 |

## 3. Architecture

```
tools/curriculum_transfer.py  (NOUVEAU)
  compute_transfer_verdict(ratios, neutral_band=0.05) -> dict     # PUR (testable sans biosphère)
    -> {n, median_ratio, n_favorable, sign_p, verdict ∈ {TRANSFERE, NEUTRE, NUIT}}
  run_transfer_experiment(seeds, ladder, target, num_agents, max_ticks, grad_cfg) -> dict
    -> orchestration des 2 bras par seed, calcule les ratios, appelle compute_transfer_verdict
  main()                                                          # CLI : defauts modestes, save provenance

Réutilisé (zéro réécriture moteur) :
  main_curriculum.make_run_era_fn, _acquire_shared_db, DEFAULT_LADDER
  src.curriculum.runner: CurriculumRunner, WorldStage, GraduationConfig
  src.seed_ai.harness: Harness, SeedManager
  async_logger (géré UNE fois pour tout le harnais — pattern manage_logger=False)
```

## 4. Les deux bras (par seed)

```
shared_db = _acquire_shared_db()                       # async_logger démarré une fois
run_era_fn = make_run_era_fn(shared_db, config, num_agents, max_ticks)

pour chaque seed :
  SeedManager(seed).seed_boundary(0)                    # bras 1
  tc = CurriculumRunner([WorldStage(w) for w in ladder], run_era_fn, grad_cfg).run()
  C_curr = tc[-1]["final_competence"]                   # compétence sur la cible (dernier stage)
  T = sum(row["eras"] for row in tc)                    # budget total dépensé

  SeedManager(seed).seed_boundary(0)                    # bras 2 (même seed -> appariement)
  no_grad = GraduationConfig(c_floor=1.1, max_eras=T)   # ne diplôme jamais -> tourne exactement T eres
  tt = CurriculumRunner([WorldStage(target)], run_era_fn, no_grad).run()
  C_tabula = tt[-1]["final_competence"]

  ratio = C_curr / max(C_tabula, 1e-6)
```

- **`target`** = dernier monde de `ladder` (défaut `"industrial"`).
- **Budget égal** : tabula-rasa tourne **exactement T ères** (le total du curriculum pour ce seed) → pas de
  confond compute. Test *conservateur* : tabula-rasa voit la cible bien plus longtemps ; un ratio > 1
  malgré ça = transfert *réel*.
- **Appariement** : `seed_boundary(seed)` avant chaque bras → même seed, runs séquentiels (pas de
  concurrence → pas le piège RNG-global de C2). Caveat D1 connu : les bras divergent dans la consommation
  RNG après le 1ᵉʳ tirage dépendant du génome ; l'appariement réduit la variance inter-seed, pas intra.

## 5. La mesure (`compute_transfer_verdict`)

```python
def compute_transfer_verdict(ratios, neutral_band=0.05):
    n = len(ratios)
    med = median(ratios)
    n_fav = sum(1 for r in ratios if r > 1.0)
    effective = [r for r in ratios if r != 1.0]
    sign_p = _sign_test_p(sum(1 for r in effective if r > 1.0), len(effective))  # binomial exact 2-sided
    if med > 1.0 + neutral_band and 2 * n_fav > n:
        verdict = "TRANSFERE"
    elif med < 1.0 - neutral_band and 2 * n_fav < n:
        verdict = "NUIT"
    else:
        verdict = "NEUTRE"
    return {"n": n, "median_ratio": med, "n_favorable": n_fav, "sign_p": sign_p, "verdict": verdict}
```

- `_sign_test_p(k, n)` : p-value binomiale exacte bilatérale sous H0 p=0.5, via `math.comb` (zéro dépendance ;
  `scipy` n'est pas garanti). `n==0` → `sign_p=1.0`.
- **`neutral_band`** : un effet médian dans [0.95, 1.05] → `NEUTRE` (honnêteté : un ratio à peine > 1 n'est
  pas un transfert). La p-value du signe est *rapportée* (significativité), le verdict reste descriptif.

## 6. Provenance & sortie

`Harness(seed=meta_seed, name="curriculum_transfer", with_db=False).save(result, config=config)` écrit
`results/curriculum_transfer_<meta_seed>.json` au format ledger (seed+commit+config_hash+git_dirty+data).
`result` = `{verdict, median_ratio, n_favorable, sign_p, per_seed:[{seed, C_curr, C_tabula, T, ratio}],
config:{ladder, target, seeds, num_agents, max_ticks, grad_cfg}}`. `with_db=False` car le harnais gère
lui-même l'`async_logger` (ne pas cycler la DB sous les pieds des runs). **Le verdict apparaît au dashboard
via `/api/provenance` (ledger C1), comme S2.**

## 7. Compute & paramétrage

Chaque ère = un run biosphère complet (≤ `max_ticks` ticks, `num_agents` agents). Le curriculum ≈ 3 stages
× ≤ `max_eras` ères → coûteux. **Défauts modestes** (garde-fou « budget compute » de la roadmap), tout
paramétrable par env :
- `CT_SEEDS` (défaut ex. 5), `CT_LADDER` (défaut `stoneage,agricultural,industrial`), `CT_MAX_ERAS`
  (défaut ex. 12), `CT_NUM_AGENTS` (défaut ex. 40), `CT_MAX_TICKS` (défaut ex. 300).
- Le verdict tient à toute échelle ; on peut dialer pour un signal rapide puis monter en rigueur.

## 8. Gestion d'erreurs

- `_acquire_shared_db()` renvoie `None` (KuzuDB indispo) → le harnais log une erreur et sort proprement
  (pas de crash) ; le bras peut tourner sans DB (le snapshot champion échoue → promotion sans transfert,
  déjà géré dans `make_run_era_fn`).
- `C_tabula` ~ 0 → `max(C_tabula, 1e-6)` évite la division par zéro (ratio borné, pas d'inf).
- `compute_transfer_verdict([])` → `NEUTRE`, `sign_p=1.0` (jamais d'exception).
- `async_logger` démarré/arrêté **une fois** (try/finally) même si un seed lève.

## 9. Tests

- **`tests/sandbox/test_curriculum_transfer.py`** :
  - `compute_transfer_verdict` (PUR, synthétique) : ratios tous > 1 → `TRANSFERE` + `2*n_fav>n` ; tous < 1
    → `NUIT` ; autour de 1 (band) → `NEUTRE` ; `[]` → `NEUTRE`/`sign_p=1.0` ; `sign_p` ∈ [0,1].
  - `_sign_test_p` : k=n → p faible (significatif) ; k=n/2 → p≈1 ; n=0 → 1.0.
  - **Smoke tiny** (1 run biosphère minimal) : `run_transfer_experiment(seeds=[0], ladder=["stoneage"],
    target="stoneage", num_agents=4, max_ticks=5, grad_cfg=GraduationConfig(max_eras=1))` → renvoie un dict
    avec `verdict`/`per_seed` (1 entrée), sans crash. *(Marqué lent ; un seul, comme le smoke S2.)*
- **Non-régression** : suite `tests/sandbox` + backend vertes.

## 10. Critères de succès

1. `tools/curriculum_transfer.py` produit un verdict {TRANSFERE/NEUTRE/NUIT} apparié multi-seed avec
   budget compute égal entre bras.
2. `compute_transfer_verdict` pur, testé, honnête (band neutre + p-value de signe rapportée).
3. Provenance écrite (`results/curriculum_transfer_<seed>.json`) → visible au dashboard via le ledger C1.
4. Réutilise la machinerie existante (zéro réécriture du moteur curriculum). Suites vertes.

## 11. Hors périmètre (YAGNI)

- **Opt-in `USE_CURRICULUM` dans main_biosphere** — `main_curriculum.py` exécute déjà le curriculum ; suivi optionnel.
- **Option B (head-start, temps-cible égal)** — alternative de mesure ; A (budget égal) d'abord.
- **Compétence robuste (médiane des W dernières ères)** au lieu de la compétence finale — raffinement anti-bruit ; v1 = finale.
- **Probe d'oubli catastrophique** (`retention.py`) — coûteux (K² ères), expérience séparée.
- **Statistiques avancées** (Wilcoxon, taille d'effet bornée) — le test de signe suffit pour un premier verdict falsifiable.

## 12. Dépendances

- `main_curriculum.py` (`make_run_era_fn`, `_acquire_shared_db`, `DEFAULT_LADDER`), `src/curriculum/runner.py`
  (`CurriculumRunner`/`WorldStage`/`GraduationConfig`), `src/curriculum/competence.py` (`competence_for`) — existants.
- `src/seed_ai/harness.py` (`Harness`, `SeedManager`, provenance) — D1, livré.
- `async_logger` — existant. Aucune dépendance nouvelle (`math`/`statistics` stdlib pour la stat).
