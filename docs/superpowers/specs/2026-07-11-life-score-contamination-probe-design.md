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

Réutilise le pattern éprouvé du banc B2 ([tools/torch_throw_gate_inworld_ab.py](../../../tools/torch_throw_gate_inworld_ab.py)) et de `competence_profile.py`, **en legacy** (pas besoin de torch) :

```python
w = Biosphere3D(WorldConfig(base_metabolism=bm, forage_payoff=fp))
for _ in range(n_agents):
    w.add_agent(MambaAgent(), energy=80.0)
if hasattr(w, "memory_retriever"):
    w.memory_retriever.stop()        # repro : couper la mémoire KuzuDB ambiante
w.current_era = 1
w.benchmark_mode = True               # cohorte fixe : repro figée, la population ne fait que rétrécir
```

- Régime **sweet 0.25/3.0 par défaut** (EDR-085 : population diverse et vivante ~140, laisse apparaître les events rares craft/mammouth qu'il s'agit de mesurer) ; **défaut 1.0/1.0 en option** (env `LSC_BM`/`LSC_FP`).
- `n_agents=40` (prod-like), `ticks=300` par défaut (env `LSC_TICKS`), `K=12` seeds par défaut (env `LSC_SEEDS`).
- **Seed CRN** : `np.random.seed(seed)` avant chaque run.

### Roster (capture des composants)

`benchmark_mode=True` fige la reproduction → la cohorte initiale de `n_agents` est **stable** (elle rétrécit par mortalité, ne grandit jamais). On capture la cohorte initiale et on **snapshot chaque tick** les composants de chaque membre encore vivant, en conservant la dernière valeur vue (les membres morts gardent leur snapshot final — sinon on sous-échantillonne exactement les agents à event rare qui meurent ensuite).

```python
cohort = list(w.agents)                       # n_agents membres, identités stables (repro figée)
roster = [None] * len(cohort)
# ... par tick, après w.step() :
for i, a in enumerate(cohort):
    if a in living_set:                       # a['energy'] > 0 / présent dans w.agents
        roster[i] = _components(a)            # écrase avec la valeur la plus récente
```

Composants extraits par `_components(agent)` :
```python
{"age": agent["age"], "preys_eaten": agent["preys_eaten"],
 "altars_solved": agent["altars_solved"], "spears_crafted": agent.get("spears_crafted", 0),
 "mammoth_kills": agent.get("mammoth_kills", 0), "ref_distinction": agent.get("_ref_distinction", 0.0)}
```
Membres jamais vus vivants après tick 0 gardent leur snapshot de tick 0 (jamais `None` : on snapshot une fois avant la boucle).

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

- La cohorte est **fraîche** (soupe non évoluée), pas le HoF de prod → mesure la contamination sur la *distribution de population* que la sélection voit, pas sur les champions déjà filtrés. Le corroborant HoF couvre le second angle.
- `benchmark_mode` fige la repro (leçon 114b) : la politique ne fait qu'agir, pas apprendre — cohérent avec une mesure de *composition de fitness*, pas d'apprentissage.
- Sweet 0.25/3.0 maximise la diversité d'events : un `INERTE` au sweet est **conservateur** (si le terme ne bouge pas la sélection même quand les events sont les plus fréquents, il ne la bouge pas au régime dur non plus).
- `n=40` cohorte, `K=12` seeds : respecte le seuil du garde-fou pour tout verdict positif.
```
