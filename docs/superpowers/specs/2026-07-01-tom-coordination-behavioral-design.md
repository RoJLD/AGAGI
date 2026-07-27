# ToM comportementale : la chasse coop est-elle COORDONNÉE ou INDÉPENDANTE ? (P4 audit mémoire, chantier #2)

> **Spec de conception** — 2026-07-01. Chantier P4-ToM #2 (comportemental). TOOLING pur, read-only, zéro `src/`.
> Zéro fichier de la session // (substrate_ab/torch/famine/gate-mlp). Doc = `docs/EDR/` (>= 135).
> Tranche le **caveat #2 d'EDR 132** (décode latent +0.12 = contexte partagé vs vraie modélisation).

## 1. Question & contexte

EDR 132 a mesuré la ToM représentationnelle → TOM_INERT (tête inerte) + un décode latent FAIBLE (+0.12)
dont l'origine est **ambiguë** : vraie modélisation de l'autre, ou simple **contexte partagé** (agents
co-localisés partageant les mêmes stimuli) ? Ce chantier tranche au niveau COMPORTEMENTAL.

**Mécanique de la coop (EDR 028).** Attaquer = **être sur la cellule d'une proie**
(`world_1_stoneage.py:692` : `attacked_prey = next(p for p in self.preys if agent.x==p.x and agent.y==p.y)`,
puis dégâts). Le mammouth (`hp=100`, barehanded 10/lance 50) est tué par **dégâts cumulés du pack** ; à la
mort, tous les `attackers` sont crédités (`:726-736`). La coop peut donc être soit **COORDONNÉE** (l'agent
conditionne son attaque à la présence d'autres = recrutement, ToM comportementale), soit **INDÉPENDANTE**
(chaque agent attaque le gros gibier quel que soit l'entourage → la « coop » = convergence fortuite).

**Question falsifiable.** Parmi les agents proches d'un mammouth FRAIS, la probabilité d'attaquer (être sur
sa cellule) est-elle PLUS ÉLEVÉE quand d'autres agents sont proches (recrutement) qu'en solo ?

## 2. Architecture (zéro-collision, read-only)

Nouveau `tools/tom_coordination.py`. **Réutilise** (imports, zéro modif) : `_evolve_champions`
(competence_profile — champions par défaut, coop ON), `_measure_profile` PATTERN (cohorte fixe
benchmark_mode + memory neutralisée), `_make_cfg`, `_seed_genome`, `_reproduce`, `run_era_pool`,
`PRESERVE_DIMS` (map_elites_compare). LECTURE SEULE de `env.agents` (x,y) et `env.preys` (x,y,type,hp).
AUCUN `src/` modifié. Un SEUL bras (la coop est le comportement par défaut, pas de gate).

## 3. Méthode (cohorte fixe de champions, R=3)

Par seed `base+r` :
1. **Évolution** : `_evolve_champions(s, ...)` (cliquet top-5, coop par défaut) → champions qui chassent.
2. **Collecte** (cohorte FIXE, `benchmark_mode` + memory neutralisée) : à chaque tick APRÈS `env.step()`,
   pour chaque **mammouth FRAIS** (`type=="Mammouth"` ET `hp >= 0.5*mammoth_hp` → première moitié de vie,
   exclut le pile-on d'agonie SANS le paradoxe « frais=personne dessus »), pour chaque agent à distance
   Manhattan **≤ 2** du mammouth : enregistrer
   `{attacking: dist==0, others_near: nb d'AUTRES agents à dist ≤ 2 du mammouth}`.
3. **Signal de recrutement** : `p_with = P(attacking | others_near>=1)`, `p_alone = P(attacking |
   others_near==0)`, `delta = p_with - p_alone`.

**Confond neutralisé** : en fixant « proche d'un mammouth frais » (même stimulus, même fraîcheur), la seule
variable est la **présence de congénères** → isole « conditionner sur l'autre » de « le mammouth est là / il
va mourir ». Caveat résiduel : contexte partagé pur (le lieu du mammouth attire le clustering) — voir §6.

## 4. Composants & interfaces

### 4.1 `_hunt_samples_from_state(agents, preys, mammoth_hp) -> list[dict]`
Pour chaque `m in preys` avec `m["type"]=="Mammouth"` ET `m["hp"] >= 0.5*mammoth_hp` : soit `near = [a for a
in agents if _manhattan(a, m) <= 2]` ; pour chaque `a in near` : `others = len(near) - 1` (autres à ≤2) ;
emit `{"attacking": _manhattan(a, m) == 0, "others_near": others}`. `_manhattan(a,m) = abs(a["x"]-m["x"]) +
abs(a["y"]-m["y"])`.

### 4.2 `_collect_hunt_decisions(cfg, genomes, max_ticks=400) -> list[dict]`
Mirror `_measure_profile` (env.benchmark_mode=True ; memory_retriever stop()+clear() AVANT boucle ;
`from_genome(preserve_dims=PRESERVE_DIMS)`). `mammoth_hp = getattr(cfg, "mammoth_hp", 100.0)`. À chaque
tick : `env.step()` puis `samples += _hunt_samples_from_state(env.agents, env.preys, mammoth_hp)`. Renvoie
tous les samples.

### 4.3 `_recruitment_signal(samples) -> dict`
`with_ = [s for s in samples if s["others_near"] >= 1]` ; `alone = [s for s in samples if s["others_near"]
== 0]`. `p_with = mean(attacking sur with_)` (0.0 si vide), `p_alone = mean(attacking sur alone)`.
Renvoie `{"p_with", "p_alone", "delta": p_with-p_alone, "n_with": len(with_), "n_alone": len(alone)}`.

### 4.4 `_verdict_coordination(sig) -> str`
- **INDETERMINE** si `n_with < 20` OU `n_alone < 20` (trop peu d'observations).
- **COORDINATED** si `delta >= 0.10`.
- **INDEPENDENT** sinon (la présence d'autrui ne change pas la proba d'attaque → coop = convergence, pas ToM).

### 4.5 `_report_coordination(h, per_seed, R, _return)`
`per_seed` = liste de dicts `_recruitment_signal` par seed. Agrège : moyennes pondérées OU moyenne simple
des deltas ; verdict sur le delta moyen + garde min(n_with, n_alone) sur l'ensemble. Table ASCII (1
ligne/seed : p_with, p_alone, delta, n_with, n_alone) + moyenne + verdict. Save JSON
(`name="tom_coordination"`). Tout ASCII (cp1252).

### 4.6 `main_tom_coordination(R=3, eras=12, num_agents=30, max_ticks=400, seed=1300, _return=False)`
`async_logger.start()/stop()`. Par seed : `champs = _evolve_champions(s, ...)` ; répliquer à num_agents ;
`samples = _collect_hunt_decisions(_make_cfg(), reps, ...)` ; `per_seed.append({**_recruitment_signal(
samples), "seed": s})`. Puis `_report_coordination`. Smoke :
`main_tom_coordination(R=1, eras=2, num_agents=16, max_ticks=120, seed=99300, _return=True)`.

## 5. Verdict attendu & falsifiabilité

Attendu = **INDEPENDENT** (arc substrat : EDR 132 tête inerte, décode latent = contexte partagé ; l'apex par
coop = convergence fortuite sur le gros gibier, pas coordination). Falsifiable : si `delta >= 0.10` de façon
robuste → COORDINATED (recrutement réel, la ToM comportementale existe SANS émerger dans la tête). Un
COORDINATED rétro-éclairerait le décode latent +0.12 comme fonctionnel.

## 6. Caveats

- **Contexte partagé résiduel** : `delta > 0` pourrait venir de ce que les bons spots (accessibles) attirent
  À LA FOIS le clustering et l'attaque, sans conditionnement mutuel. La fraîcheur + la distance fixe le
  réduisent mais ne l'éliminent pas. Un INDEPENDENT est propre (pas de conditionnement) ; un COORDINATED
  porte ce caveat (à approfondir : appariement par spot).
- **Freshness** : `hp >= 0.5*mammoth_hp` inclut 1-5 hits barehanded (capture les attaquants) et exclut
  l'agonie. Si `mammoth_hp` reconfiguré (tool-gate EDR 111), le seuil suit (proportionnel).
- **Corrélationnel, pas causal** : mesure snapshot (pas de tracking de transition dist1→dist0), donc
  « attaque » et « autres proches » sont co-observés. Suffisant pour un INDEPENDENT falsifiable.
- **Non-vacuité** : si peu d'encontres mammouth (`n < 20`) → INDETERMINE. Repli : `num_agents=40`,
  `max_ticks=500`, ou near-range ≤ 3.

## 7. Provenance, déterminisme, non-régression

- `Harness(name="tom_coordination")` → JSON distinct ; seed 1300, smoke 99300 distinct.
- Déterminisme : `SeedManager.seed_boundary` + `benchmark_mode` + memory neutralisée → 2 runs byte-identiques
  (vérifié au run). **RUN avec `MEC_PRESERVE_DIMS=1`** (substrat non aplati, [[from-genome-flattens-architecture]]).
- Non-régression : `competence_profile`/`map_elites_compare` IMPORTÉS seulement (zéro modif). `src/` VIDE.
- ASCII-only dans tout `print` exécuté (cp1252).

## 8. Tests (TDD, `tests/sandbox/test_tom_coordination.py`)

1. **`_hunt_samples_from_state`** : agents/preys synthétiques (1 mammouth frais hp=80, 3 agents : 1 dessus,
   1 à dist 1, 1 à dist 5 ; 1 mammouth agonie hp=10 ignoré ; 1 lapin ignoré) → samples attendus (2 agents à
   ≤2 : l'un attacking others_near=1, l'autre non attacking others_near=1 ; le lointain exclu).
2. **`_recruitment_signal`** : samples synthétiques → p_with/p_alone/delta/n corrects.
3. **`_verdict_coordination` 3 branches** : COORDINATED (delta 0.15, n≥20) / INDEPENDENT (delta 0.02, n≥20) /
   INDETERMINE (n_with 5).
4. **Smoke** `main_tom_coordination(R=1, eras=2, num_agents=16, max_ticks=120, seed=99300, _return=True)` :
   renvoie un verdict valide (∈ {COORDINATED, INDEPENDENT, INDETERMINE}), table écrite, JSON écrit.

## 9. Coût & repli

Évolution `eras=12` × R=3 + collecte cohorte fixe → ~1× EDR 125 (un seul bras, pas de 2e évolution). Repli :
`eras=8`, R=2 ; si INDETERMINE, élargir `num_agents`/`max_ticks`/near-range. Run réel APRÈS revue,
`MEC_PRESERVE_DIMS=1`.

## 10. Doc & mémoire

- **Doc** : `docs/EDR/` (>= 135, confirmé à la rédaction). Coordonnée vs indépendante + tranche le caveat
  décode-latent d'EDR 132.
- **Mémoire** : MAJ `intelligence-typing-flat-connectome` (ToM comportementale mesurée) + éventuellement
  `world-floor-survivability-gate` (l'apex-coop est-il coordonné ?).

## 11. Coordination (sessions parallèles)

Tooling-only read-only : `git diff src/` VIDE. N'utilise NI substrate_ab/torch/famine/gate-mlp/
cross_world_transfer (session // active, fil compositionnel EDR 128-134). Réutilise competence_profile/
map_elites_compare (non possédés par la session //). Worktree off origin/main (HEAD 36d5b59). EDR 135
(133 pris + 134 réservé par leur draft feat/d1).
