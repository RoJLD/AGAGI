# Design — Évolution pipeline-complet sur FamineWorld (le test propre de l'évolvabilité du stockage)

> **Date** : 2026-06-30 · **Statut** : design validé (cadrage), avant plan.
> **Suite directe** d'EDR-121 (évolvabilité INCONCLUSIVE : GA léger = meltdown ; il faut le pipeline complet).
> **Sert** : `SDR-G1`. Pré-scopé en backlog par EDR-121 §Conséquences.

---

## 1. Problème (ce qu'EDR-121 a laissé ouvert)

EDR-121 n'a pas pu trancher l'évolvabilité du stockage : (1) les champions famine mouraient avant la
famine (`delta_famine=0`), (2) le GA léger (`evolve_in_famine` : mono-champion, mutation forte, pas
d'élitisme HoF ni de fitness moyennée) subissait un **meltdown** sous fitness famine bruitée — il érodait
même un warm-start compétent. Conclusion : un test propre exige le **pipeline biosphère complet**
(`main_biosphere` : élitisme HoF, reproduction in-world, reseed depuis le HoF chaque ère) qui a produit
les champions stoneage compétents.

## 2. Le piège (HoF global) et son isolation

`main_biosphere` lit/écrit le **HoF global** `data/hall_of_fame.pkl` (top-10 par score, chaque ère).
Évoluer en famine y déposerait des champions famine qui **écraseraient le champion stoneage** — or ce
champion est le **contrôle** de l'ablation ET une ressource partagée (runs G0 d'autres sessions). 

**Décision (cadrage) : HoF dédié famine via chemin séparé.** Seam minimal :
`persistence.py:7` → `HALL_OF_FAME_PATH = os.environ.get("HOF_PATH", "data/hall_of_fame.pkl")`. Process-global
(toutes les fonctions lisent la constante), non-breaking (défaut inchangé). Le run famine s'exécute avec
`HOF_PATH=data/hall_of_fame_famine.pkl` → le HoF stoneage global reste **intact**.

## 3. Architecture — seams minimaux + run

1. **Seam HoF configurable** (`src/seed_ai/persistence.py`) : `HALL_OF_FAME_PATH` lu via env-var `HOF_PATH`.
2. **Câblage famine** (`main_biosphere.py`) : ajouter `elif world_type == "famine": from src.worlds.world_famine import FamineWorld; env = FamineWorld(config)` au switch (~ligne 224-231).
3. **Échelle configurable** (`main_biosphere.py`) : `MAX_ERAS` (hardcodé 30, ligne 213) lu via env-var `MAX_ERAS` (défaut 30, non-régressif).
4. **Run smoke** : `WORLD_TYPE=famine HOF_PATH=data/hall_of_fame_famine.pkl MAX_ERAS=60 HEADLESS=1 EXPERIMENT_SEED=42 py -3 main_biosphere.py`.
5. **Extraction + compétence** : `load_hall_of_fame()` (HoF famine) → `entries[0].genome` → `measure_genome` (probe existant) → le champion **atteint-il la famine** et survit-il clairement dedans ?

## 4. Critère de succès du SMOKE (décision cadrage : modérée d'abord)

Le smoke réussit si le pipeline complet produit un champion famine **compétent** : survie médiane
**nettement > cycle_abundance** (il atteint la famine, tick 30) — idéalement comparable au champion
stoneage (53-200 ticks selon seed). Contraste vs EDR-121 (GA léger : 7-12 ticks, meurt avant la famine).
- **SI compétent** → procéder à l'ablation (cache ON/OFF sur ce champion vs stoneage) + décider du powered.
- **SI toujours incompétent** (meurt avant la famine même avec le pipeline complet) → **finding majeur** :
  ce n'est PAS le GA, c'est le monde/substrat — la famine est trop dure à bootstrapper, OU le substrat ne
  peut pas (convergence forte verrou substrat, lève le confond GA d'EDR-121).

## 5. Validation (ablation, si champion compétent)

Réutilise le probe (`measure_genome`, `cache_enabled` ON/OFF, `compute_emergence_verdict`). Δ_famine
(champion famine pipeline-complet, cache ON−OFF) vs Δ_stoneage (contrôle). Le champion famine est chargé
du HoF famine (`HOF_PATH`) ; le stoneage du HoF global (chemin par défaut) — attention à l'env-var
process-global au moment du chargement (charger chacun avec le bon `HOF_PATH`).

## 6. Garde-fous anti-théâtre

1. **HoF stoneage global INTACT** (vérifier avant/après que `data/hall_of_fame.pkl` n'a pas changé).
2. **Smoke avant powered** : ne pas brûler du compute si le pipeline ne converge pas non plus.
3. **Honnêteté du SI-incompétent** : un champion qui meurt avant la famine MÊME avec le pipeline complet
   est un résultat majeur (pas un échec à cacher) — il lève le confond GA d'EDR-121.
4. **Repro** : `EXPERIMENT_SEED` fixé ; noter que `main_biosphere` ne `clear()` pas le memory_retriever
   entre ères (non-déterminisme résiduel) — caveat, pas bloquant pour un smoke de compétence.
5. **Contention KuzuDB** (machine multi-sessions) : run lourd → fenêtre calme ; si hang, ne tuer aucun
   process.

## 7. Périmètre & non-buts

- **Dans le périmètre** : 2-3 seams (HoF env-var, famine wiring, MAX_ERAS env-var) + smoke + assessment.
- **Hors périmètre (selon résultat smoke)** : run powered multi-seed + ablation + EDR = phase suivante,
  décidée APRÈS le smoke.

## 8. Composants

- **Modify** `src/seed_ai/persistence.py` — `HALL_OF_FAME_PATH` via `HOF_PATH` env-var.
- **Modify** `main_biosphere.py` — switch famine + `MAX_ERAS` env-var.
- **Test** `tests/test_famine_pipeline_wiring.py` — `WORLD_TYPE=famine` instancie `FamineWorld` ; `HOF_PATH` redirige le chemin ; `MAX_ERAS` lu (non-régressif défaut 30).
- **Run + assessment** : smoke main_biosphere famine → compétence du champion.
