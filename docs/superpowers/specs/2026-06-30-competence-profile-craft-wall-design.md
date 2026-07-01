# Profil de competence par tier — « le mur du craft » (P3a audit memoire)

> **Spec de conception** — 2026-06-30. Chantier P3 (sous-item SUR) de l'audit memoire
> (`docs/AUDIT_MEMOIRE_INTELLIGENCE.md`). TOOLING pur. Zero fichier de la session // (FamineWorld/
> torch/substrate_ab). Doc = `docs/EDR/` (numero confirme a la redaction, >= 124).

## 1. Question & contexte

`life_score` est le SEUL signal de selection (poids : mammoth 400 > spears 300 > preys 50 > altars 20 >
age 0.1). On n'instrumente JAMAIS la competence ventilee par type : `stoneage_competence` calcule bien
`frac_hunt`/`frac_apex`/`frac_tool` (via `_frac_reaching`, `src/curriculum/competence.py:22`) mais les
ECRASE en un scalaire. Le descripteur MAP-Elites 4-tiers `{survie,forage,craft,apex}`
(`src/seed_ai/map_elites.py`) existe mais n'est pas surface.

**Question falsifiable** : dans l'echelle moyens->ends {survie < forage < craft < apex}, le tier
**CRAFT** (spears) est-il un goulot ANORMAL que l'apex CONTOURNE ? Prediction non-triviale (issue de
`world-floor-survivability-gate` : apex 21.7% par COOPERATION, lance 1.6%, altars = code mort) =
**INVERSION DE L'ECHELLE** : la fraction qui atteint l'apex est >= celle qui crafte (les agents
chassent le mammouth PLUS qu'ils ne fabriquent la lance). Si vrai -> le pathway outil est une branche
quasi-morte, et le poids 300 de `spears_crafted` dans `life_score` est largement INERTE (levier
« reparer la metrique »). Indices deja dans le code (commentaire `competence.py:66` : apex 21.7% /
lance 1.6%) ; cet instrument le MESURE proprement (cohorte fixe) et PRE-ENREGISTRE le verdict.

## 2. Architecture (zero-collision)

Nouveau `tools/competence_profile.py`. **Reutilise** (DRY, imports) les helpers stoneage de
`tools/map_elites_compare.py` : `_make_cfg` (sweet metab 0.25 / payoff 3.0), `_seed_genome`,
`_reproduce`, `run_era_pool` (evolution d'une ere). **Reutilise** `_frac_reaching`
(`src/curriculum/competence.py`). AUCUN `src/` modifie, AUCUN fichier de la session // touche.

## 3. Mesure (lecons EDR 114b + P0)

Deux phases, par seed :
1. **Evolution** (repro ON) : faire evoluer une lignee stoneage `eras` eres (cliquet top-5, comme
   `run_lineage_hof`) pour obtenir des champions COMPETENTS (best_ever top-5).
2. **Mesure profil** (cohorte FIXE) : repliquer les champions en cohorte de `num_agents`, mesurer sur
   un episode a **`benchmark_mode=True`** (pas de reproduction -> pas de dilution par nouveau-nes
   tardifs, confond du pooling EDR 114b). Collecter par agent `{age, preys_eaten, spears_crafted,
   mammoth_kills}`.

⚠️ **P0** : `_measure_profile` doit `stop()` + `clear()` le `memory_retriever` AVANT la boucle (pas
apres, contrairement a `run_era_pool` qui a le bug repro) -> mesure reproductible.

## 4. Composants & interfaces

### 4.1 `_evolve_champions(seed, eras=12, num_agents=30, max_ticks=400) -> list[Genome]`
- Cliquet top-5 (boucle de `run_lineage_hof`), `SeedManager(seed).seed_boundary(0)`, `_make_cfg`,
  `_reproduce`, `run_era_pool`. Renvoie les genomes `best_ever` (top-5).

### 4.2 `_measure_profile(cfg, genomes, max_ticks=400, disable_repro=True) -> list[dict]`
- Mirror `run_era_pool` MAIS : pose `env.benchmark_mode = True` si `disable_repro` ; `stop()`+`clear()`
  du `memory_retriever` AVANT la boucle ; renvoie la liste des dicts stats par agent du pool
  `{age, preys_eaten, spears_crafted, mammoth_kills}` (pas les tuples score/genome).

### 4.3 `_tier_fractions(stats_list) -> dict`
- `{"frac_forage": _frac_reaching(stats_list, "preys_eaten"), "frac_craft": _frac_reaching(stats_list,
  "spears_crafted"), "frac_apex": _frac_reaching(stats_list, "mammoth_kills"), "n": len(stats_list)}`.

### 4.4 `_verdict_craft_wall(fracs) -> str`
- `fracs` = dict agrege (moyennes sur R seeds) avec `frac_forage/frac_craft/frac_apex`.
- **CRAFT_WALL CONFIRME** si `frac_craft < frac_forage` ET `frac_apex >= frac_craft` (echelle inversee
  au craft) ET `frac_craft <= 0.10` (craft quasi-mort en absolu).
- **ECHELLE MONOTONE** (refute) si `frac_apex < frac_craft` (apex plus rare que craft -> outil sur le
  chemin de l'apex) OU `frac_craft >= frac_forage`.
- **INDETERMINE** si `frac_forage < 0.10` (cohorte trop incompetente pour discriminer).

### 4.5 `_report_profile(h, per_seed, R, _return)`
- `per_seed` = liste de dicts `_tier_fractions` par seed. Agrege (moyenne) -> `fracs`. Table ASCII
  (1 ligne/seed : seed, frac_forage, frac_craft, frac_apex, n) + ligne MOYENNE + verdict. Save JSON
  (`name="competence_profile"`). Tout ASCII (cp1252).

### 4.6 `main_competence_profile(R=3, eras=12, num_agents=30, max_ticks=400, seed=1240, _return=False)`
- `async_logger.start()/stop()` autour de l'evolution (comme map_elites_compare). Pour chaque seed
  `base+r` : `champs = _evolve_champions(...)` ; `stats = _measure_profile(_make_cfg(), champs * (num_agents//5+1), ...)` ;
  `per_seed.append(_tier_fractions(stats))`. Puis `_report_profile`. Smoke : `main_competence_profile(R=1, eras=2, num_agents=10, max_ticks=80, seed=99240, _return=True)`.

## 5. Re-base attendue (d'apres world-floor)

| tier | fraction attendue | source |
|---|---|---|
| forage (preys) | elevee (>0.5) | competent |
| craft (spears) | ~0.016 (1.6%) | `competence.py:66` |
| apex (mammoth) | ~0.217 (21.7%) | world-floor / `competence.py:66` |

Verdict attendu : **CRAFT_WALL CONFIRME** (frac_apex 0.22 >> frac_craft 0.02 = echelle inversee ;
craft <= 0.10). Falsifiable : si les champions evolues craftent plus que prevu (frac_craft > frac_apex),
ECHELLE MONOTONE.

## 6. Provenance, determinisme, non-regression

- `Harness(name="competence_profile")` -> JSON distinct ; seed reel 1240, smoke 99240 distinct.
- Determinisme : `SeedManager.seed_boundary` + `benchmark_mode` (cohorte fixe) + memory_retriever
  neutralise -> 2 runs byte-identiques. Run reel APRES revue ; AUCUN test relance apres (EDR 107).
- Non-regression : `map_elites_compare.py` et `competence.py` IMPORTES seulement (zero modif) ; tous
  les appelants existants inchanges.
- ASCII-only dans tout `print` execute (cp1252).

## 7. Tests (TDD, `tests/sandbox/test_competence_profile.py`)

1. **`_tier_fractions`** : stats synthetiques -> fractions correctes (`_frac_reaching` binaire par
   agent ; ex 2/4 preys -> 0.5).
2. **`_verdict_craft_wall` 3 branches** : fracs synthetiques -> CRAFT_WALL CONFIRME (forage 0.8, craft
   0.02, apex 0.22) / ECHELLE MONOTONE (forage 0.8, craft 0.3, apex 0.1) / INDETERMINE (forage 0.05).
3. **`_measure_profile` cohorte fixe** : a `disable_repro=True`, le pool reste petit (= cohorte
   initiale, pas d'explosion) ET contient les cles attendues ; verif que `benchmark_mode` est pose.
4. **Smoke** `main_competence_profile(R=1, eras=2, num_agents=10, max_ticks=80, seed=99240, _return=True)` :
   renvoie un verdict valide, table 1 ligne, JSON ecrit. Seed distinct du run reel.

## 8. Cout & repli

Evolution `eras=12` x `R=3` seeds (Biosphere3D stoneage, sweet metab) + mesure cohorte fixe ->
modere (minutes, comme map_elites_compare ; pas le numpy instantane de P1). Repli : `eras=8`, `R=2`.
Run reel APRES revue.

## 9. Doc & memoire

- **Doc** : `docs/EDR/` (>= 124, confirme a la redaction). Le profil par tier + verdict + l'indictement
  de la metrique (poids spears inerte si craft mort).
- **Memoire** : MAJ `world-floor-survivability-gate` (mesure population du mur du craft) +
  `intelligence-typing-flat-connectome` (1er instrument per-type livre).

## 10. Coordination (sessions paralleles)

Tooling-only : `git diff src/` VIDE. N'utilise NI `make_population`/torch NI FamineWorld NI
`substrate_ab*` (fichiers actifs de la session //). Reutilise `map_elites_compare`/`competence.py`
(non possedes par la session //). Commits path-scoped. Worktree off origin/main (a jour avec P0/P1
merges + s2_stats de la session //).
