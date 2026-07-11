# Probe d'impact de contamination `life_score` — Design (EDR-WLD-002)

**Date :** 2026-07-11
**Territoire :** WLD (Demande d'intelligence & plancher) — question phare « le monde exige-t-il l'intelligence (métrique life_score) »
**Statut amont :** gate de cohérence S2 RÉPARÉ (#132, vérifié end-to-end 2026-07-10) ; EDR-WLD-001 (agri) livré.

## Motivation

`calculate_life_score` ([src/seed_ai/persistence.py:36-47](../../../src/seed_ai/persistence.py)) est la **fitness de sélection de production** (appelée par `save_to_hall_of_fame` et `robust_hof`). Elle somme des termes pondérés :

```
age·0.1 + preys_eaten·50 + altars_solved·20 + spears_crafted·300 + mammoth_kills·400 + _ref_distinction·REF_FITNESS_WEIGHT
```

Deux EDR ont **asserté** que certains termes sont morts/inertes, sans jamais le mesurer au niveau **sélection** :
- **EDR 096** : `altars_solved` ≡ 0 en stoneage (autel = code mort, jamais incrémenté sur 882 agents) → le terme `altars_solved·20` serait un no-op.
- **EDR 125** : seulement ~1.1 % des agents craftent → `spears_crafted·300` serait « largement inerte » malgré son poids élevé.

Le lever proposé par ces EDR (« réparer la métrique ») consisterait à **muter** cette fonction partagée. Mais personne n'a vérifié si ces termes **changent réellement quels agents la sélection favorise**, ou s'ils sont des zéros inoffensifs. Muter la fitness de sélection a un **blast-radius élevé** (change l'évolution de toutes les sessions parallèles, invalide les comparaisons HoF historiques, contesté par la thèse crédit canonique de `FIL_DIRECTEUR_AGI.md`).

**Ce probe mesure le blast-radius AVANT de toucher le cœur partagé.** Il transforme une assertion en test falsifiable : si retirer un terme ne change pas le classement top-K de la sélection, « réparer » est cosmétique ; s'il le change, c'est un vrai levier qui vaut la coordination.

## Question et échelle de verdict

**Question :** pour chaque terme suspect (`altars_solved·20`, `spears_crafted·300`), le retirer change-t-il **quels agents la sélection favorise** sur une cohorte réaliste ?

**Échelle de verdict (par variante de poids) :**
- `MÉTRIQUE_INERTE` — le terme ne déplace jamais la sélection (médiane `topk_jaccard`=1.0 ET médiane `kendall_tau`=1.0 sur tous les seeds). « Réparer » est cosmétique pour la sélection → priorité basse. Pour `altars`, ce verdict serait la **première preuve** (pas juste une observation) que le terme est un no-op de sélection en stoneage.
- `MÉTRIQUE_CONTAMINÉE` — le terme déplace le top-K sélectionné de façon non-triviale et robuste : effet-taille `1 − médiane(topk_jaccard) ≥ 0.10` ET au moins ⌈K/2⌉ seeds montrent un déplacement, avec **K ≥ 12** (garde-fou anti-évaporation). → vrai levier, coordination requise avant mutation.
- `AMBIGU` — déplacement présent mais faible / non-majoritaire (entre les deux).

## Architecture

Deux fichiers, **additif pur, zéro modification `src/`, path-scopé** :

- **Créer** `tools/life_score_contamination_probe.py` — le probe.
- **Créer** `tests/sandbox/test_life_score_contamination_probe.py` — tests.
- **Sortie** `results/life_score_contamination_<seed0>.json` (écrite à l'exécution, non versionnée).

Non-goals stricts (ce probe NE fait PAS) :
- Ne modifie **pas** `calculate_life_score` ni aucun fichier `src/`.
- Ne **sème pas** de spears/autels (contrairement au banc B2) — mesure les taux **naturels** pour ne pas surestimer la contamination.
- Ne rend **pas** de verdict `CONTAMINÉE` sous K=12 seeds.

## Harness de cohorte

**Cohorte = champions ÉVOLUÉS, pas soupe fraîche.** Décision critique (validée par exploration) : sur de la soupe non-évoluée le craft n'émerge jamais (EDR 014/111) et l'apex est rare → 0 event → toutes les variantes seraient trivialement INERTE *par absence d'events* (résultat dégénéré, non-informatif). Le test de contamination n'a de sens que sur une cohorte aux **taux réalistes** (craft ~1.1 %, apex ~15-21 % — EDR 125). Comme **aucun HoF n'existe** en prod à mesurer, la cohorte doit être produite par évolution.

**Réutilise le harness canonique de `competence_profile.py`** (DRY, prouvé, revu) plutôt que de dupliquer l'évolution :

```python
from tools.competence_profile import _evolve_champions      # cliquet top-5, repro ON, SeedManager(seed)
from tools.map_elites_compare import _make_cfg, PRESERVE_DIMS  # régime sweet canonique
from src.seed_ai.harness import SeedManager                  # re-seed déterministe de la mesure
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
```

- **Régime = `_make_cfg()`** (= `SWEET_METAB`/`SWEET_PAYOFF` = 0.25/3.0, EDR-085) — **les mêmes conditions qu'EDR 125**, donc la contamination mesurée est directement comparable au mur du craft. Pas de knobs de régime (une variable en moins).
- Seeding **déterministe** via `_evolve_champions` (`SeedManager(seed).seed_boundary(0)` en interne, CRN).
- `eras=8`, `num_agents=30`, `max_ticks=300` par défaut (env `LSC_ERAS`/`LSC_AGENTS`/`LSC_TICKS`) ; `K=12` seeds (env `LSC_SEEDS`).

### Roster (capture des composants)

`run_arm(seed)` évolue des champions puis les mesure sur **cohorte fixe** (`benchmark_mode=True`, repro figée). Le roster = pool canonique `env.agents + env.dead_agents` (mirror exact de `competence_profile._measure_profile:84` — inclut les morts avec leurs stats finales, donc capture les agents à event rare qui meurent ensuite ; pas de snapshot par-tick nécessaire) :

```python
def _measure_roster(cfg, genomes, max_ticks):
    env = Biosphere3D(cfg)
    env.benchmark_mode = True
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop(); env.memory_retriever.clear()   # repro P0
    for g in genomes:
        a = MambaAgent(); a.from_genome(g, preserve_dims=PRESERVE_DIMS); env.add_agent(a, energy=80.0)
    env.current_era = 1
    t = 0
    while env.agents and t < max_ticks:
        env.step(); t += 1
    pool = env.agents + list(getattr(env, "dead_agents", []))
    return [_components(a) for a in pool]
```

Composants extraits par `_components(agent)` — capture **les 6 termes**, dont `altars_solved` (pour MESURER, pas assumer, qu'il est ≡0) :
```python
{"age": agent.get("age", 0), "preys_eaten": agent.get("preys_eaten", 0),
 "altars_solved": agent.get("altars_solved", 0), "spears_crafted": agent.get("spears_crafted", 0),
 "mammoth_kills": agent.get("mammoth_kills", 0), "ref_distinction": agent.get("_ref_distinction", 0.0)}
```

> Note DRY/coupling : `_evolve_champions`, `_make_cfg`, `_reproduce`, `PRESERVE_DIMS` sont importés de tools existants (competence_profile / map_elites_compare). Le reviewer vérifie que ces symboles existent et gardent leur signature.

## Variantes de poids

Un jeu de poids = dict des 6 coefficients. `full` = les poids de production lus/copiés depuis `calculate_life_score`. Variantes = `full` avec un coefficient forcé à 0 :

| variante        | altars | spears | (autres = full) |
|-----------------|--------|--------|-----------------|
| `full`          | 20     | 300    | —               |
| `drop_altars`   | **0**  | 300    | —               |
| `drop_spears`   | 20     | **0**  | —               |
| `drop_both`     | **0**  | **0**  | —               |

`REF_FITNESS_WEIGHT` est importé de `persistence` (vaut 0 en prod, EDR 056) et gardé identique dans toutes les variantes.

## Métriques (par seed)

Fonctions pures, sans dépendance externe (pas de scipy), testées en isolation :

- `score(components, weights) -> float` — somme pondérée.
- `kendall_tau(a, b) -> float` — tau-a manuel : `(concordant − discordant) / (n·(n−1)/2)` sur toutes les paires (n=40 → 780 paires, trivial). Paires à égalité (sur a ou b) comptées ni concordantes ni discordantes.
- `topk_jaccard(scores_full, scores_var, k) -> float` — ensembles des indices du top-k par score (égalités départagées par indice croissant pour déterminisme), Jaccard `|∩| / |∪|`. `k = max(1, ceil(frac_topk · n_roster))`, `frac_topk=0.25` (le tier qui repro/entre au HoF).
- `term_mass_share(roster, weights) -> dict` — pour chaque terme, `Σ_i weight·composant_i` divisé par la masse totale ; expose la magnitude de contamination.
- `n_crafters`, `n_altar_solvers` — comptes roster avec `spears_crafted>0` / `altars_solved>0` (explique le *pourquoi* : 0 crafteur ⇒ `drop_spears` trivialement τ=1).

Par seed, pour chaque variante ≠ `full` : `{kendall_tau, topk_jaccard, term_mass_share_full, n_crafters, n_altar_solvers}`.

## Agrégation et verdict

Par variante, sur les K seeds : `median(topk_jaccard)`, `median(kendall_tau)`, `n_changed = #{seeds : topk_jaccard < 1.0}`, `effect = 1 − median(topk_jaccard)`.

```
si median_jaccard == 1.0 et median_tau == 1.0        -> MÉTRIQUE_INERTE
sinon si K >= 12 et effect >= 0.10 et n_changed >= ceil(K/2) -> MÉTRIQUE_CONTAMINÉE
sinon                                                 -> AMBIGU
```

Verdict global = la variante la plus actionnable (`CONTAMINÉE` > `AMBIGU` > `INERTE`), mais **chaque variante est rapportée séparément** (prédiction : `drop_altars` = INERTE-exact τ=1.0 tous seeds ; `drop_spears` = l'inconnue).

## Garde repro et corroborant

- **Repro** : R=2 passes byte-identiques sur `seed[0]` (compare les dicts de résultats) ; lève `AssertionError` sinon.
- **Corroborant secondaire non-bloquant** : si un fichier HoF existe (`persistence.HALL_OF_FAME_PATH`), décomposer chaque champion stocké (dict `stats`) en part-de-masse par terme et agréger (moyenne) → montre la composition **réalisée** des champions de prod. Purement informatif (comme `life_p` dans S2) ; absent proprement si pas de HoF.

## Sortie

- JSON `results/life_score_contamination_<seed0>.json` : `{config, per_seed: [...], per_variant_verdict: {...}, global_verdict, hof_decomposition}`.
- stdout ASCII-safe (`sys.stdout.reconfigure(encoding="utf-8", errors="replace")` dans `__main__` — leçon cp1252 PR #150/#151) : une ligne par seed + tableau par variante + verdict + interprétation.

## Bornage / caveats (à consigner dans l'EDR)

- La cohorte est **évoluée** (champions cliquetés, mêmes conditions qu'EDR 125), pas le HoF de prod (absent) ni de la soupe fraîche (dégénérée). Mesure la contamination sur la distribution qu'une sélection en cours de course voit. Le corroborant HoF (si présent un jour) couvre l'angle « champions déjà filtrés ».
- `benchmark_mode` fige la repro dans la phase de MESURE (leçon 114b) : la politique agit sans apprendre — cohérent avec une mesure de *composition de fitness*. L'évolution (phase amont) utilise la repro ON canonique.
- Régime sweet (`_make_cfg`) maximise la diversité d'events : un `INERTE` au sweet est **conservateur** (si le terme ne bouge pas la sélection quand les events sont les plus fréquents, il ne la bouge pas au régime dur non plus).
- `num_agents=30` × 5 clones-champions, `K=12` seeds : respecte le seuil du garde-fou pour tout verdict positif. Coût : 12 × (évolution 8 ères + mesure) → run de recherche à lancer en tâche de fond, pas interactif.
```
