# Design — Le plafond apex se lève-t-il sous croissance topologique accumulée ?

Date : 2026-06-25

## Question scientifique

Toute la story du plafond apex (~0.16-0.21, EDR 097/102/103/104) a été mesurée sur des populations
**non-évolutives** (la sonde charge des génomes et tourne une ère). On n'a JAMAIS mesuré si le plafond se
lève quand la croissance topologique s'ACCUMULE entre générations. Le bug `from_genome` (qui ré-aplatissait
le champion à 172 à chaque ré-import, [[from-genome-flattens-architecture]]) empêchait cette accumulation ;
il est corrigé dans main (`preserve_dims=True` par défaut, PR #58). **Quand la croissance s'accumule
(`preserve_dims=True`), les réseaux grossissent-ils ET l'apex monte-t-il au-delà de ~0.21 — ou plafonne-t-il
quand même (→ verrou = répertoire-monde, pas le substrat réseau) ?**

## Contexte (vérité terrain vérifiée 2026-06-25)

- `MambaAgent.from_genome(genome, preserve_dims=False)` sur la branche `feat/d1-prod-pairing`
  (`mamba_agent.py:136`) ; **main a `preserve_dims=True`** (PR #58, commit 26d0eea, PAS encore mergé dans
  cette branche — la branche est 18 commits derrière main).
- **La SEULE différence de machinerie évolutive entre cette branche et main est ce défaut** (`git diff
  HEAD...main` sur `src/{agents,seed_ai,evolution,worlds}/` = uniquement `mamba_agent.py`, 6 ins/4 del = le
  flip + docstring). Donc régler `preserve_dims=True` sur cette branche **réplique prod exactement** : pas
  besoin de merger main pour la validité.
- L'aplatissement mord SEULEMENT au chargement initial et au ré-import inter-ère (`from_genome`) ; la
  reproduction INTRA-ère clone le modèle vivant (pas via `from_genome`) → la croissance persiste DANS une
  ère quel que soit le flag. `preserve_dims` est donc décisif sur l'axe **inter-générationnel** : False
  re-aplatit le champion à 172 à chaque ère (croissance RESET) ; True le préserve (croissance ACCUMULE).
- `add_node_rate=0.2` par défaut (`mutation.py:8`), `add_node` (`:54`) grossit `num_nodes` de +1 en
  splittant une connexion non-nulle. PAS de cap dur → W en `num_nodes²` → risque compute à borner.
- `main_biosphere.main()` est la boucle N-ères avec HoF mais trop lourde/non-repro (rendu, Skinner Box,
  Supervisor LangGraph, GOD MODE, mémoire ambiante) → inutilisable pour une mesure propre. On construit un
  harnais évolutif PROPRE qui réutilise les helpers du probe.

## Hypothèse (3 issues nettes, mutuellement exclusives)

1. **Réseaux grossissent (True) ET apex monte** → le plafond ÉTAIT le bug substrat ; il se lève quand la
   croissance accumule. Le fix prod change le jeu.
2. **Réseaux grossissent mais apex plateau ~0.21** → croissance ≠ compétence → **répertoire-monde
   confirmé** comme verrou résiduel (cohérent EDR 104 + NAS A2) → motive l'enrichissement du monde.
3. **Réseaux ne grossissent PAS même sous True** → la croissance n'est pas réellement active dans ce
   harnais (à diagnostiquer : taux, W non-nul, cap).

Le bras `preserve_dims=False` est le CONTRÔLE : taille plate (~172, re-aplatie chaque ère) + apex plat
(~0.16-0.21) attendus.

## Architecture — petit build + run A/B

### Unité 1 — tool `tools/evolve_ceiling_probe.py` (build)

Harnais évolutif déterministe, réutilise : `competence_for`/`_frac_reaching` (`src/curriculum/competence`),
`init_primordial_soup` (ère 1), `build_population`/`apply_mutations`/`MutationConfig`
(`src/seed_ai/{repopulation,mutation}`), `calculate_life_score` (`src/seed_ai/persistence`), `MambaAgent`,
`_prepare_world`/`_acquire_shared_db` (`main_curriculum`).

Fonction `run_evolution(target, k_eras, num_agents, max_ticks, shared_db, preserve_dims, node_cap)` :
- **Carry EN MÉMOIRE** (pas de HoF global → reproductible, pas de contamination // sessions) : une liste
  `carried` de génomes champions, persistée entre ères.
- Pour `era in range(k_eras)` :
  - **Graine appariée ET variable** : à `main()`, parser `EXPERIMENT_SEED` (défaut 0) et
    `SeedManager(experiment_seed).seed_boundary(0)` au boot (comme `main_biosphere:208`). Par ère :
    `SeedManager(experiment_seed + era * 1_000_000).seed_boundary(0)` (dérivé de la graine de run →
    appariement inter-bras True/False pour une même graine, ET variation entre graines).
  - `env = _prepare_world(target, config, deterministic=True)`.
  - **Population de l'ère** :
    - era 0 : `genomes, _ = init_primordial_soup(num_agents, import_agent_id=None, keep_memory=False,
      shared_db, config)`.
    - era > 0 : `genomes = build_population(carried, num_agents, mut_config, apply_mutations,
      heavy_config=heavy, heavy_frac=0.3)` (même recette que `init_primordial_soup`, mais à partir des
      champions PORTÉS en mémoire, pas du HoF global).
  - **Instanciation** : `for g in genomes: a = MambaAgent(); a.from_genome(g, preserve_dims=preserve_dims);
    env.add_agent(a, energy=50.0)`. ← C'EST ICI que `preserve_dims` mord (ré-import inter-ère).
  - **Garde-fou cap** (anti-théâtre, pas silencieux) : avant instanciation, si `g.num_nodes > node_cap`,
    NE PAS grossir au-delà (laisser tel quel ; `add_node` ne s'applique qu'en repro intra-ère) et
    incrémenter un compteur `cap_hits` rapporté dans le résultat + log. `node_cap` borne le compute.
  - Boucle sim : `while len(env.agents) > 0 and t < max_ticks: env.step(); t += 1`.
  - **Mesures de l'ère** : `all_agents = env.agents + env.dead_agents` ; `frac_apex =
    _frac_reaching(stats, "mammoth_kills")` (stats = mêmes champs que le probe) ; `competence =
    competence_for(target)(stats)` ; `nodes = [a["model"].genome.num_nodes for a in all_agents]` →
    `mean_nodes`, `max_nodes`. Décompo par ère : `{era, frac_apex, frac_tool, median_competence,
    mean_nodes, max_nodes, n, ticks, cap_hits}`.
  - **Sélection → carry** : `top = sorted(all_agents, key=calculate_life_score, reverse=True)[:3]` ;
    `carried = [copy.deepcopy(a["model"].genome) for a in top]` (génomes VIVANTS évolués, avec leur taille
    grossie). C'est le proxy fidèle de la sélection générationnelle (top-k champions seedent l'ère
    suivante), reproductible et isolé du HoF global.
  - `if hasattr(env, "memory_retriever"): env.memory_retriever.stop()`.
- Retourne `{target, preserve_dims, k_eras, per_era:[...], node_cap}`.
- `main()` lit l'env : `EVP_PRESERVE_DIMS` (=="1"), `EVP_TARGET` (stoneage), `EVP_K` (12),
  `EVP_NUM_AGENTS` (40), `EVP_MAX_TICKS` (300), `EVP_NODE_CAP` (512), `CT_METAB`/`CT_PAYOFF` (sweet spot,
  réutilise les noms du probe). Sauve via `Harness.save` (résultat = `results/evolve_ceiling_probe_0.json`).

### Unité 2 — run A/B apparié (pas de code)

Deux bras × 3 seeds. Comme le carry est déterministe par seed, on apparie au niveau de la TRAJECTOIRE :
```
AGISEED_QUIET_LOG=1 EVP_PRESERVE_DIMS={1,0} EVP_TARGET=stoneage EVP_K=12 \
  EVP_NUM_AGENTS=40 EVP_MAX_TICKS=300 EVP_NODE_CAP=512 CT_METAB=0.25 CT_PAYOFF=3.0 \
  EXPERIMENT_SEED=<s> python -u tools/evolve_ceiling_probe.py
```
pour `s ∈ {0, 1, 2}` (ou 3 graines au choix) × `preserve_dims ∈ {1,0}` = 6 trajectoires. Sauver chaque
JSON (ils s'écrasent). Tracer `mean_nodes(era)` et `frac_apex(era)` par bras ; comparer la pente de taille
(True vs False) et la trajectoire d'apex. Appariement : pour une même `EXPERIMENT_SEED`, les bras True/False
voient les MÊMES graines d'ère (dérivées `experiment_seed + era·1e6`) → contraste apparié par (graine, ère).

## Garde-fous anti-théâtre

- **Trajectoire par ère, jamais le scalaire nu** : la COURBE `frac_apex(era)` et `mean_nodes(era)` EST le
  résultat (3 issues distinguées par la forme conjointe taille×apex).
- **Régime absolu rapporté** : taille ET apex en valeurs brutes (pas que l'écart inter-bras).
- **A/B apparié** : bras False = contrôle (taille re-aplatie ~172, apex plat) ; le contraste True−False
  isole l'effet de l'accumulation.
- **Cap NON silencieux** : `cap_hits` rapporté ; si le cap mord souvent, le signaler (la croissance est
  forte → bon signe pour issue 1/2, mais borne le compute).
- **Risque compute borné** : `node_cap` + `max_ticks` + extinction. Si une trajectoire hang/explose, le
  signaler (piège multiprocess/explosion connu).
- Réutilise la métrique réparée (`frac_apex`), le sweet spot, la neutralisation mémoire (repro).

## Tests

- Smoke `slow` (`tests/sandbox/test_evolve_ceiling_probe.py`) :
  `run_evolution("stoneage", k_eras=2, num_agents=12, max_ticks=60, shared_db, preserve_dims=True,
  node_cap=512)` avec `CT_METAB=0.25`/`CT_PAYOFF=3.0` → tourne SANS erreur ; `len(per_era)==2` ;
  `per_era[0]` a `frac_apex`/`mean_nodes`/`max_nodes`/`cap_hits` ; `median_competence ∈ [0,1]` ; le carry
  ère 0→1 ne crashe pas (`build_population` sur champions vivants OK).
- Smoke contrôle : même appel `preserve_dims=False` → tourne ; `mean_nodes` de l'ère 1 ≈ aplati (≤172+ε)
  vs True (peut dépasser) — valide que le flag a un effet observable sur la taille.
- Non-régression : `test_diversity_dose_probe.py` / `test_mono_fresh.py` (le nouveau tool n'importe/altère
  pas le probe existant).

## Hors périmètre (YAGNI)

- Pas de HoF global (carry en mémoire, reproductible).
- Pas de merge de main (le knob `preserve_dims=True` suffit pour la validité — seule diff machinerie).
- Pas d'enrichissement du monde (c'est l'issue 2 → chantier suivant SI apex plafonne).
- Pas de curriculum multi-mondes (stoneage seul).
- Pas de réglage de `add_node_rate` (prod = 0.2, on mesure prod).

## Suite (selon issue)

- **Issue 1 (apex monte)** : le substrat était le verrou ; quantifier le gain, étendre K, envisager la
  bascule `preserve_dims` par défaut sur cette branche (déjà verte en non-rég, NAS.md).
- **Issue 2 (taille monte, apex plateau)** : verrou = répertoire-monde → chantier d'enrichissement
  d'affordance (la seule piste restante en amont), avec diagnostic du répertoire d'abord.
- **Issue 3 (pas de croissance)** : diagnostiquer pourquoi (W non-nul ? taux ? cap ?) avant tout.

## Variables d'expérience

`preserve_dims` (AXE, accumulation ON/OFF), K ères (profondeur de la trajectoire ; ici 12), seeds
(réplicats), `node_cap` (compute), `add_node_rate` (prod 0.2 ; un sweep serait un chantier distinct),
`coop_reward`. Métrique-reine secondaire : `mean_nodes(era)` (la croissance accumule-t-elle ?) jointe à
`frac_apex(era)`.
