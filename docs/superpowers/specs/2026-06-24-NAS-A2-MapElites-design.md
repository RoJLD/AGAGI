# Spec — A2 MAP-Elites (archive Quality-Diversity) + comparaison vs HoF

> **Statut** : design validé (2026-06-24), prêt pour plan.
> **Valide** : `docs/roadmap/NAS.md` §2 Axe A — A2. Pivot après clôture de l'axe sparsité (D1+D2).
> **Discipline** : on MESURE A2 (QD vs HoF) AVANT de câbler en prod. Câblage `main_biosphere` = différé.

## 1. Question falsifiable

Reproduire depuis une **archive de niches diverses** (MAP-Elites) bat-il le **HoF top-10 mono-objectif**
en compétence finale, à budget compute égal, apparié multi-seed ? (Hypothèse : la diversité échappe au
plateau de bruit de fitness, EDR 075-081.)

## 2. Descripteurs (validés) — grille 2D

- **Axe 1 — taille réseau** : `genome.num_nodes`. Binning : `size_bin = clamp((num_nodes - 150) // 15, 0, 7)` → 8 bins (couvre ~150-280, range réaliste avec add_node).
- **Axe 2 — palier comportemental** (moyens→ends) : depuis les stats agent :
  `tier = 3 if mammoth_kills>0 elif 2 if spears_crafted>0 elif 1 if preys_eaten>0 else 0`. 4 paliers.
- Cellule = `(size_bin, tier)` ; grille 8×4 = 32 niches. Non-dégénérée (tier 0 toujours peuplé).

## 3. `MapElitesArchive` (`src/seed_ai/map_elites.py`)

Classe pure (testable sans biosphère) :
```
descriptor(num_nodes, stats) -> (size_bin, tier)      # binning ci-dessus, stats = dict
class MapElitesArchive:
    cells: Dict[Tuple[int,int], Tuple[float, Genome, dict]]   # cell -> (score, genome, stats)
    upsert(score, genome, stats) -> bool   # garde le max par cellule ; True si inséré/amélioré
    sample(n, rng) -> List[Genome]         # n génomes tirés (avec remise) parmi les élites
    elites() -> List[Tuple[float, Genome, dict]]
    coverage() -> int                      # nb de cellules occupées (métrique QD)
    best_score() -> float
```
- `sample` : si archive vide → lève/retourne []. Tirage uniforme sur les cellules occupées (diversité).
- `rng` injecté (repro). Pas d'I/O dans la classe (persistance gérée par l'appelant si besoin).

## 4. Gating

`WorldConfig.use_map_elites: bool = False` (défaut → HoF legacy intact ; non-régression). Utilisé par
le câblage prod **différé** ; pour la mesure, les deux bras sont pilotés explicitement par le tool.

## 5. Mesure — `tools/map_elites_compare.py` (calqué sur `curriculum_transfer.py`)

Par seed, deux bras à **budget égal** (E ères, même `num_agents`/`max_ticks`), **appariés** (même
`SeedManager(seed).seed_boundary(0)` au départ de chaque bras) :
- **Bras HoF** : boucle évolutive top-5 ratchet (`best_ever` + `_reproduce`, comme `evolve_competence`).
- **Bras QD** : `MapElitesArchive` ; à chaque ère : upsert tout le pool, puis `sample(num_agents-élite)`
  + élites des cellules pour la génération suivante via `_reproduce`.

**Era-runner riche** (`run_era_pool(cfg, genomes, max_ticks) -> (pool, metrics)`) où
`pool = [(life_score, genome, stats), ...]` pour TOUS les agents (stats = {num_nodes, preys_eaten,
spears_crafted, mammoth_kills}). Réutilise le pattern `run_era_metab` (Biosphere3D, step loop,
`memory_retriever.stop()`), mais renvoie le pool complet + stats au lieu du top-5.

**KPI** : `competence` = compétence finale (moy. 5 dernières ères du meilleur life_score) ; `coverage`
(QD seulement, diagnostic). **Verdict** (par seed : ratio `C_qd / C_hof`) via
`compute_transfer_verdict` (réutilisé) : **QD_GAGNE / NEUTRE / QD_PERD** + sign test binomial.
`Harness.save`. Params env : `MEC_SEEDS`, `MEC_ERAS`, `MEC_NUM_AGENTS`, `MEC_TICKS`.

> Note budget : QD à budget ÉGAL = même nb d'ères/agents/ticks que HoF (pas d'avantage compute).

## 6. Tests (TDD)

**Archive (pur, sans biosphère)** :
1. `descriptor` : `(num_nodes=172, {mammoth_kills:1})` → `(1, 3)` ; `(150, {})` → `(0, 0)` ;
   `num_nodes=400` → size_bin clampé à 7.
2. `upsert` garde le max par cellule : insérer score 10 puis 5 dans la même cellule → l'élite reste 10 ;
   score 20 → remplace.
3. `upsert` cellules distinctes coexistent (diversité préservée) : 2 génomes de paliers différents → 2 cellules.
4. `sample(n)` retourne n génomes parmi les élites ; archive vide → `[]`.
5. `coverage` = nb de cellules occupées.

**Comparaison (faux runner, sans biosphère)** :
6. `run_lineage_arm` HoF vs QD avec un faux `run_era_pool` déterministe → structure correcte, apparié reproductible.
7. `compare` : faux runner où QD (diversité) atteint une compétence > HoF → verdict `QD_GAGNE` ; runner neutre → `NEUTRE`.

**Smoke opt-in** (`MEC_SMOKE=1`, non-CI) : 1 seed, 2 ères réelles, les deux bras tournent sans crash.

## 7. Non-régression / garde-fous

- `use_map_elites=False` par défaut ⇒ aucun chemin prod modifié (le câblage est différé, donc même
  `main_biosphere` n'est PAS touché cette itération).
- Aucune modification du HoF/`persistence.py` existant.
- Budget égal entre bras (pas de triche compute).

## 8. Hors-périmètre (différé jusqu'à verdict positif)

- **Câblage `main_biosphere`** (seam fin-d'ère ↔ repop, gated `use_map_elites`) — APRÈS que la mesure
  valide QD > HoF.
- Persistance disque de l'archive (`data/map_elites.pkl`).
- Descripteurs additionnels / grille adaptative.
- Le run à l'échelle + EDR de verdict.
