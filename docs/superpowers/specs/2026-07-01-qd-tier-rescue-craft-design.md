# QD sauve-t-il le tier CRAFT mort ? — sélection par niches vs life_score (P3 audit mémoire)

> **Spec de conception** — 2026-07-01. Chantier P3 (sous-item SÛR) de l'audit mémoire
> (`docs/AUDIT_MEMOIRE_INTELLIGENCE.md`). TOOLING pur. Zéro fichier de la session // (FamineWorld/
> torch/substrate_ab). Doc = `docs/EDR/` (numéro confirmé à la rédaction, >= 126).

## 1. Question & contexte

EDR 125 a MESURÉ le mur du craft au niveau population (cohorte fixe) : forage 0.600, **craft 0.011**,
apex 0.156 — l'échelle moyens→ends {survie<forage<craft<apex} est INVERSÉE au craft, et le poids
`spears_crafted`×300 de `life_score` est **inerte** (1.1% craftent). Le levier de l'audit est
« réparer la métrique / sélectionner sur des niches diverses ».

`tools/map_elites_compare.py` compare DÉJÀ QD (MAP-Elites) vs HoF (mono-objectif `life_score`), mais sa
métrique `_competence` **réécrase tout sur le scalaire `life_score`** (moyenne des 5 dernières ères) —
exactement le défaut que l'audit dénonce. Résultat historique : QD≈HoF (couverture ↑ mais QD≯HoF sur
l'apex ; mémoire [[nas-bottleneck-is-substrate-not-search]], pré-`preserve_dims`).

**Question falsifiable (neuve).** La sélection QD — reproduire depuis des niches comportementales
diverses — **sauve-t-elle le tier CRAFT mort** que `life_score` ne propage pas, ou le mur du craft
est-il du **substrat / atteignabilité** (réfute, cohérent EDR 111 : forcer le monde à EXIGER l'outil
n'a pas fait émerger le craft) ?

**Mécanisme testé (non-trivial).** Le HoF top-5 par `life_score` **droppe** structurellement un génome
craft-pur (spears×300 < forager+apex-coop combinés), donc ne le propage jamais. L'archive QD garde une
élite dans la **cellule tier=2** (`descriptor` de `map_elites.py`) et reproduit depuis elle. Si le craft
est atteignable par mutation, QD le propage → `frac_craft_QD` ↑ ; sinon QD n'a rien à préserver (cellule
tier=2 vide) → le verrou est l'atteignabilité, pas la sélection.

## 2. Architecture (zéro-collision)

Nouveau `tools/qd_tier_rescue.py`. **Réutilise** (imports, zéro modif) :
- `tools/competence_profile.py` (mergé PR #101) : `_evolve_champions` (bras HoF), `_measure_profile`
  (cohorte fixe, leçons 114b + P0), `_tier_fractions`.
- `tools/map_elites_compare.py` : `_make_cfg`, `_seed_genome`, `_reproduce`, `run_era_pool`,
  `PRESERVE_DIMS`.
- `src/seed_ai/map_elites.py` : `MapElitesArchive` (lecture).

AUCUN `src/` modifié ; NI FamineWorld NI torch NI `substrate_ab*` (fichiers actifs de la session //).

## 3. Méthode (2 bras appariés par seed, R=3)

Par seed `base+r` :
1. **Bras HoF** = `_evolve_champions(s, eras, num_agents, max_ticks)` (cliquet top-5 `life_score`,
   repro ON) → 5 génomes best_ever. **Réutilisé verbatim** (EDR 125).
2. **Bras QD** = nouveau `_evolve_qd_champions(s, eras, num_agents, max_ticks)` (archive MAP-Elites,
   reproduit depuis `archive.sample(5)`, repro ON) → `(champions=archive.sample(5), archive)`. Mirror
   de `run_lineage_qd` (`map_elites_compare.py:138`) mais renvoie les champions + l'archive.
3. **Mesure per-type** pour CHAQUE bras sur **cohorte FIXE** via
   `_measure_profile(_make_cfg(), champs_répliqués_à_num_agents, disable_repro=True)` puis
   `_tier_fractions(stats)`. `benchmark_mode` neutralise la repro (leçon 114b) ; memory_retriever
   `stop()`+`clear()` AVANT la boucle (leçon P0). Fractions binaires par agent (`_frac_reaching`).

**Symétrie de détermination** : les DEUX bras évoluent avec `run_era_pool` (memory NON neutralisée en
évolution — comme EDR 125, empiriquement déterministe sur 2 passes) et se MESURENT avec
`_measure_profile` (memory neutralisée + `benchmark_mode` → déterminisme strict). Comparaison
apples-to-apples.

**Champions QD mesurés = `archive.sample(5)`** (l'opérateur de sélection PROPRE au bras QD, ce qu'il
carry-forward chaque ère), PAS le top-5 `life_score` (qui collapse QD sur HoF et rendrait le test
tautologique). Déterministe : RNG global seedé par `SeedManager(s).seed_boundary(0)`, état avancé
identiquement à travers une évolution identique.

## 4. Composants & interfaces

### 4.1 `_evolve_qd_champions(seed, eras=12, num_agents=30, max_ticks=400, run_era_fn=None) -> (list, MapElitesArchive)`
Mirror de `run_lineage_qd` (repro ON) MAIS renvoie `(champions, archive)` au lieu du scalaire.
`run_era_fn` injectable (défaut `run_era_pool`) pour les tests. `SeedManager(seed).seed_boundary(0)`,
archive `MapElitesArchive()`, graines `[_seed_genome(i) for i in range(num_agents)]`. À chaque ère :
`pool, _ = run_era_fn(cfg, genomes, max_ticks)` ; `archive.upsert(s,g,st)` pour tout `(s,g,st)` du pool ;
`champ = archive.sample(5)` ; `genomes = _reproduce(champ, num_agents)` (fallback
`[MambaAgent().genome for _ in range(num_agents)]` si archive vide). Renvoie
`(archive.sample(5), archive)` — ou `([], archive)` si archive vide.

### 4.2 `_tier_coverage(archive) -> dict`
Ventilation des cellules occupées par tier (readout mécanistique « le craft existe-t-il dans l'archive ? »).
```python
def _tier_coverage(archive):
    tiers = [cell[1] for cell in archive.cells.keys()]
    return {f"cells_tier{t}": sum(1 for x in tiers if x == t) for t in range(4)}
```

### 4.3 `_verdict_qd_rescue(fracs_hof, fracs_qd) -> str`
Primaire = `frac_craft`. `d = fracs_qd["frac_craft"] - fracs_hof["frac_craft"]`.
- **QD_RESCUE_CRAFT CONFIRME** si `d >= 0.10` ET `fracs_qd["frac_craft"] >= 0.10` (QD lève le craft ET le
  sort du plancher).
- **QD_NUIT** si `d <= -0.10`.
- **QD_NEUTRE** (réfute) sinon → le mur du craft = substrat/atteignabilité, pas sélection.

### 4.4 `_report_qd_rescue(h, per_seed, R, _return)`
`per_seed` = liste de dicts par seed : `{seed, hof:{frac_forage,frac_craft,frac_apex,n},
qd:{...}, coverage:{cells_tier0..3}}`. Agrège (moyenne) les fractions des deux bras. Table ASCII
(1 ligne/seed : hof_forage/craft/apex | qd_forage/craft/apex | qd craft-cells) + ligne MOYEN + Δcraft +
verdict. Save JSON (`name="qd_tier_rescue"`). Tout ASCII (cp1252).

### 4.5 `main_qd_tier_rescue(R=3, eras=12, num_agents=30, max_ticks=400, seed=1260, _return=False)`
`async_logger.start()/stop()` autour de l'évolution. Pour chaque seed `base+r` :
`hof_champs = _evolve_champions(s, ...)` ; `qd_champs, archive = _evolve_qd_champions(s, ...)` ;
mesure per-tier des deux bras (répliquer champions à `num_agents` via
`(champs * (num_agents//len(champs)+1))[:num_agents]`, fallback `[]` si vide) ;
`per_seed.append({seed, hof:_tier_fractions(hof_stats), qd:_tier_fractions(qd_stats),
coverage:_tier_coverage(archive)})`. Puis `_report_qd_rescue`. Smoke :
`main_qd_tier_rescue(R=1, eras=2, num_agents=10, max_ticks=80, seed=99260, _return=True)`.

## 5. Verdict attendu & falsifiabilité

| issue | signification |
|---|---|
| **QD_RESCUE_CRAFT CONFIRME** | La sélection par niches propage le craft que `life_score` droppe → levier = QD/métrique. |
| **QD_NEUTRE** (attendu le + probable) | QD ne sauve pas le craft → le mur est substrat/atteignabilité (EDR 111), pas la sélection ; renforce [[nas-bottleneck-is-substrate-not-search]]. Lire `_tier_coverage` : cellules tier2 vides → le craft n'est jamais atteint (rien à sauver). |
| **QD_NUIT** | QD dégrade le craft (peu plausible). |

Falsifiable des deux côtés. Si `_tier_coverage` montre des cellules tier2 occupées MAIS
`frac_craft_QD ≈ frac_craft_HOF`, c'est un résultat riche : le craft est atteint mais NON propagé/retenu
en cohorte fixe (branche mémoire/rétention, cf. EDR 120/125).

## 6. Provenance, déterminisme, non-régression

- `Harness(name="qd_tier_rescue")` → JSON distinct ; seed réel 1260, smoke 99260 distinct.
- Déterminisme : `SeedManager.seed_boundary` + `benchmark_mode` (mesure) + memory neutralisée (mesure)
  → 2 runs byte-identiques (comme EDR 125 ; vérifié au run). L'évolution (`run_era_pool`) est
  empiriquement déterministe (leçon EDR 125 §5). Run réel APRÈS revue ; AUCUN test relancé après (EDR 107).
- Non-régression : `competence_profile.py`, `map_elites_compare.py`, `map_elites.py` IMPORTÉS seulement
  (zéro modif) ; appelants existants inchangés.
- ASCII-only dans tout `print` exécuté (cp1252).

## 7. Tests (TDD, `tests/sandbox/test_qd_tier_rescue.py`)

1. **`_tier_coverage`** : archive synthétique (cellules injectées aux tiers {0,1,2,2,3}) →
   `{cells_tier0:1, cells_tier1:1, cells_tier2:2, cells_tier3:1}`.
2. **`_verdict_qd_rescue` 3 branches** : CONFIRME (hof craft 0.01, qd 0.15 → d=0.14, qd≥0.10) /
   QD_NEUTRE (hof 0.01, qd 0.05 → d=0.04) / QD_NUIT (hof 0.20, qd 0.05 → d=−0.15).
3. **`_evolve_qd_champions` (fake runner)** : `run_era_fn` factice renvoyant un pool avec un génome
   crafteur (stats `spears_crafted>0`, `num_nodes` fixé) dans une cellule distincte → l'archive peuple
   la cellule tier=2 (`_tier_coverage(archive)["cells_tier2"] >= 1`), renvoie `(list, archive)` avec
   `archive.coverage() > 0`.
4. **Smoke** `main_qd_tier_rescue(R=1, eras=2, num_agents=10, max_ticks=80, seed=99260, _return=True)` :
   renvoie un verdict valide (∈ {CONFIRME, NEUTRE, NUIT}), table écrite, JSON écrit. Seed distinct du réel.

## 8. Coût & repli

2 bras évolutifs (`eras=12`) × R=3 seeds (Biosphere3D stoneage, sweet metab) + 2 mesures cohorte fixe/seed
→ ~2× EDR 125 (quelques minutes). Repli : `eras=8`, `R=2`. Run réel APRÈS revue.

## 9. Doc & mémoire

- **Doc** : `docs/EDR/` (>= 126, confirmé à la rédaction). QD sauve/ne sauve pas le craft + lecture
  couverture par tier (atteignabilité vs sélection).
- **Mémoire** : MAJ `world-floor-survivability-gate` (ou `nas-bottleneck-is-substrate-not-search` selon
  le verdict) + `intelligence-typing-flat-connectome` (2e instrument per-type : sélection).

## 10. Coordination (sessions parallèles)

Tooling-only : `git diff src/` VIDE. N'utilise NI `make_population`/torch NI FamineWorld NI
`substrate_ab*` (fichiers actifs de la session //). Réutilise `competence_profile`/`map_elites_compare`/
`map_elites` (non possédés par la session //). Commits path-scoped. Worktree off origin/main (HEAD
ef33b71, à jour avec P0/P1/P3a + FamineWorld G0-G1 + s2_stats de la session //).
