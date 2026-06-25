# Design — La sélection diversité-préservante lève-t-elle / stabilise-t-elle l'apex ?

Date : 2026-06-25

## Question scientifique

EDR 105 : le carry élitiste top-3 dans la boucle évolutive monoculturise → la diversité s'érode → l'apex
DÉCLINE (ère0 0.228 → ères6-11 0.082), dans les deux bras preserve_dims. **Le déclin/plafond apex est-il
un artefact de SÉLECTION (élitisme étroit) ou un vrai mur de répertoire-monde ?** Une sélection
diversité-préservante (tournoi sur toute la population) stoppe-t-elle le déclin — voire lève l'apex
au-delà de ~0.21 — ou plafonne-t-elle quand même ?

C'est le corollaire mécanistique nommé par EDR 105, et il GÂTE la suite : il faut innocenter ou condamner
la sélection AVANT d'investir dans l'enrichissement du monde (option a, coûteuse + risque de collision
avec les sessions parallèles qui travaillent le substrat Lewis).

## Contexte (vérité terrain vérifiée)

- `tools/evolve_ceiling_probe.py` : harnais évolutif multi-ères, carry top-3 par `calculate_life_score`
  EN MÉMOIRE entre ères → `build_population(carried, ...)`. `run_evolution(target, k_eras, num_agents,
  max_ticks, shared_db, preserve_dims, node_cap, experiment_seed=0)`.
- `build_population(champions, num_agents, mut_config, mutate_fn, heavy_config, heavy_frac)`
  (`src/seed_ai/repopulation.py:15`) est **structurellement élitiste** : champions intacts + enfants
  round-robin des mêmes champions. Carry top-3 → 3 lignées → monoculturisation.
- `tournament_selection(population, fitnesses, tournament_size=3)` → index (`src/seed_ai/evolution.py:153`).
  Échantillonne `tournament_size` au hasard, renvoie le meilleur → biais fitness MAIS stochastique → tire
  aussi des individus moins bons → préserve l'étalement vs top-3 déterministe.
- **Cap de population EXISTE** : `config.max_population` (`config.py:46`, défaut None) consommé par
  `world_1_stoneage.py:1552-1554` (`if cap and len(self.agents) >= cap : pas de repro`). EDR 105 a explosé
  car le harnais ne le posait pas → il suffit de le RÉGLER (pas de cap à construire).
- `genome_diversity` proxy (façon `main_biosphere.py:334`) : `np.std([a["model"].genome.W.mean() for a in
  agents])`.

## Hypothèse (3 issues)

1. **`diverse` préserve plus de diversité (vérifié) ET apex cesse de décliner / monte** → la sélection
   était (en partie) le coupable, le « plafond » est partiellement un artefact de sélection élitiste →
   **reframe : levier sélection trouvé**.
2. **`diverse` préserve la diversité MAIS apex décline/plateau quand même** → sélection INNOCENTÉE →
   **répertoire-monde confirmé comme verrou** → motive l'enrichissement du monde (option a).
3. (Garde-fou mécanisme) **`diverse` ne préserve PAS plus de diversité que `elitist`** → le knob ne mord
   pas → re-designer la sélection avant toute conclusion (ni 1 ni 2 valides).

## Architecture — 3 ajouts à `tools/evolve_ceiling_probe.py` (DRY)

### Unité 1 — knob de sélection `EVP_SELECT` (build)

`run_evolution` reçoit un nouveau param `select="elitist"` (défaut → comportement actuel, non-régressif).
À l'étape carry (actuellement `top = sorted(all_agents, key=calculate_life_score, reverse=True)[:3]`) :
- `select == "elitist"` : inchangé (top-3 par `calculate_life_score`).
- `select == "diverse"` : tirer `n_carry` parents par tournoi sur TOUTE la population de l'ère
  (`all_agents` = vivants + morts, même pool que le ranking élitiste, `calculate_life_score` marche sur les
  morts) :
  ```python
  pool = [a for a in all_agents if a.get("model") is not None]
  fits = [calculate_life_score(a) for a in pool]
  genomes_pool = [a["model"].genome for a in pool]
  idxs = [tournament_selection(genomes_pool, fits, tournament_size) for _ in range(n_carry)]
  carried = [copy.deepcopy(genomes_pool[i]) for i in idxs]
  ```
  `n_carry` (défaut 12, > 3 pour multiplier les lignées) et `tournament_size` (défaut 3) lus via env.
  Garde-fou : si `pool` vide → `carried = []` (comme l'élitiste).

### Unité 2 — cap de population (build, réutilise l'existant)

Dans `run_evolution`, après `config = WorldConfig()` : `config.max_population = pop_cap` (param, défaut
None = historique). Le monde consomme déjà ce champ (`world_1_stoneage.py:1552`). Borne le runaway qui a
fait timeouter EDR 105. `main()` lit `EVP_POP_CAP` (défaut "" → None ; sinon int).

### Unité 3 — métrique diversité par ère (build, garde-fou anti-théâtre)

Ajouter au `row` par ère : `genome_diversity = round(float(np.std([a["model"].genome.W.mean() for a in
all_agents if a.get("model") is not None])), 4)` (0.0 si <2 agents). VÉRIFIE que le bras `diverse` est
réellement plus divers — sans ça le contraste apex est ininterprétable.

`main()` lit en plus : `EVP_SELECT` (elitist), `EVP_N_CARRY` (12), `EVP_TOURNAMENT` (3), `EVP_POP_CAP`.
Le résultat inclut `select`, `n_carry`, `pop_cap`.

## Unité 4 — run A/B apparié (pas de code)

`EVP_SELECT ∈ {elitist, diverse}` × 3 seeds (EXPERIMENT_SEED 0/1/2), **`preserve_dims=True`** (prod ;
moot pour l'apex per EDR 105 mais évite l'explosion qu'avait False), K=12, 40 agents, 300 ticks, sweet
spot, `EVP_POP_CAP=200` (les deux bras, comparable). Tracer `frac_apex(era)`, `genome_diversity(era)`,
`mean_nodes(era)` par bras.

```
AGISEED_QUIET_LOG=1 EVP_SELECT={elitist,diverse} EVP_PRESERVE_DIMS=1 EVP_TARGET=stoneage \
  EVP_K=12 EVP_NUM_AGENTS=40 EVP_MAX_TICKS=300 EVP_POP_CAP=200 EVP_N_CARRY=12 EVP_TOURNAMENT=3 \
  CT_METAB=0.25 CT_PAYOFF=3.0 EXPERIMENT_SEED=<s> python -u tools/evolve_ceiling_probe.py
```

## Garde-fous anti-théâtre

- **Vérifier le mécanisme AVANT le verdict** : `genome_diversity(era)` doit être PLUS HAUTE sous `diverse`
  que sous `elitist` ; sinon issue 3 (knob ne mord pas), pas de conclusion apex.
- **Trajectoire par ère, jamais scalaire nu** ; A/B apparié par seed ; régime absolu (apex ET diversité
  ET taille).
- **Cap pop posé et rapporté** (`pop_cap` dans le résultat) ; les deux bras au même cap pour comparabilité.
- **Contraste élitiste = baseline EDR 105** : le bras `elitist` doit reproduire le déclin d'EDR 105
  (0.228→0.082) → contrôle de cohérence inter-run.
- Réutilise `frac_apex` (métrique réparée EDR 096), sweet spot, neutralisation mémoire (repro).

## Tests

- Smoke `slow` (`tests/sandbox/test_diverse_selection.py`) :
  `run_evolution("stoneage", k_eras=2, num_agents=12, max_ticks=60, shared_db, preserve_dims=True,
  node_cap=512, select="diverse", n_carry=6, tournament_size=3, pop_cap=40)` avec sweet spot →
  tourne sans erreur ; `len(per_era)==2` ; `per_era[0]` a `genome_diversity` ; `res["select"]=="diverse"` ;
  carry tournoi ère0→1 OK ; `median_competence ∈ [0,1]`.
- Smoke élitiste : `select="elitist"` (défaut) → tourne, `genome_diversity` présent, non-régression du
  carry top-3.
- Non-régression : `test_evolve_ceiling_probe.py` (les 2 smokes existants, défaut `select="elitist"`,
  `pop_cap=None`) restent verts — les nouveaux params défaut ne changent pas le comportement EDR 105.

## Hors périmètre (YAGNI)

- Pas de modif du monde (c'est l'option a / issue 2, chantier suivant SI sélection innocentée).
- Pas de MAP-Elites complet (le tournoi suffit pour un premier contraste élite-étroit vs distribution).
- Pas de crossover (build_population clone+mute ; le crossover serait un autre axe).
- Stoneage seul (zéro collision avec Lewis / sessions parallèles substrat).

## Suite (selon issue)

- **Issue 1 (apex stabilisé/levé par diverse)** : la sélection était un levier → quantifier, étendre K,
  envisager la sélection diverse en prod (`main_biosphere` HoF robuste). Reframe partiel du « plafond ».
- **Issue 2 (apex plafonne malgré diversité préservée)** : sélection innocentée → **répertoire-monde =
  verrou** confirmé de bout en bout → passer à l'enrichissement d'affordance (diagnostic coverage
  `map_elites_compare` d'abord).
- **Issue 3 (knob inerte)** : re-designer la sélection diverse (n_carry plus grand, tournament_size plus
  petit, ou MAP-Elites) avant de conclure.

## Variables d'expérience

`select` (AXE : elitist vs diverse), `n_carry` (largeur du carry diverse ; 12), `tournament_size`
(pression de sélection ; 3 — plus petit = plus diversifiant), `pop_cap` (compute + dynamique), K ères,
seeds. Métrique-garde : `genome_diversity(era)` (le knob mord-il ?). `preserve_dims` fixé True (moot apex
per EDR 105, évite l'explosion de False).
