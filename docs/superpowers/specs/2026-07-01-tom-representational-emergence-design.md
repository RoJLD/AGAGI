# ToM représentationnel : décode + émergence — la Theory of Mind émerge-t-elle sous sa propre pression ? (P4 audit mémoire, chantier 1)

> **Spec de conception** — 2026-07-01. Chantier P4-ToM #1 (représentationnel). TOOLING pur, zéro `src/`.
> Zéro fichier de la session // (substrate_ab/torch/famine/binding-probe). Doc = `docs/EDR/` (>= 131).
> Suite prévue : chantier P4-ToM #2 (comportemental : coordination/recrutement), séparé.

## 1. Contexte & correction de mémoire

**La mémoire dit « ToM MORTE (1 commentaire) » — c'est FAUX.** Il existe un circuit ToM complet, **gaté
OFF** :
- Sortie connectome `predictor_head` = **8 dims** (`mamba_agent.py:71,699,731`), calculée à chaque forward
  (numpy batch, moteur par défaut — PAS le torch de la session //).
- Récompense ToM (`world_1_stoneage.py:817-826`, dans `_resolve_social`) : pour deux agents **au même
  cellule** (`a.x==b.x, a.y==b.y, même z` ; `:789`), si `argmax(predictor_head_A) == last_action_B` →
  A gagne **+2 énergie** (`THEORY_OF_MIND_SUCCESS`). Gaté derrière `active_exp_variable in
  ["INTRINSIC","TOM"]` ; défaut config = `"LANGUAGE"` → **jamais actif**, `predictor_head` non entraînée,
  aucune pression de sélection.
- `active_exp_variable="TOM"` déclenche **UNIQUEMENT** ce bloc (vérifié : autres gates = RAG `:524`,
  LANGUAGE `:797,1075,1369`, INTRINSIC-seul `:1017` ; TOM n'en touche aucun). Isolation 1-variable propre.

C'est le **même motif** que le craft (EDR 125/127) ou le tool-gate (EDR 111) : une faculté câblée, jamais
sous sélection. Question falsifiable analogue.

## 2. Questions (2 lectures, 1 EDR, ordre de priorité cheap→causal)

**(a) DÉCODE (readout, sur le bras CONTROL).** La représentation encode-t-elle DÉJÀ l'action des congénères
par défaut (sans récompense ToM) ? Deux sondes : (a1) accuracy de la `predictor_head` désignée vs shuffle ;
(a2) sonde linéaire depuis le **latent exposé** (predictor_head+goal_vector+explicit_memory+ntm) → action
du congénère, held-out vs shuffle (est-ce qu'une AUTRE partie de la représentation encode l'autre, même si
la tête ne le fait pas ?).

**(b) ÉMERGENCE (verdict PRIMAIRE gelé).** Activer la récompense ToM (`active_exp_variable="TOM"`) pendant
l'évolution fait-il **émerger** une prédiction réelle des congénères (accuracy de `predictor_head` au-dessus
du hasard ET au-dessus du bras CONTROL), ou reste-t-elle **inerte** (comme spears/altar/craft) ?

## 3. Architecture (zéro-collision)

Nouveau `tools/tom_probe.py`. **Réutilise** (imports, zéro modif) : `_make_cfg`, `_seed_genome`,
`_reproduce`, `run_era_pool`, `PRESERVE_DIMS` (map_elites_compare) ; `_measure_profile` **PATTERN** (cohorte
fixe benchmark_mode + memory neutralisée) — on écrit `_collect_tom_pairs` sur le même modèle mais lisant
`predictor_head`/`last_action`/`x,y,z` au lieu des stats. AUCUN `src/` modifié.

## 4. Méthode (2 bras appariés par seed, R=3)

Par seed `base+r` :
1. **Évolution CONTROL** = `_evolve_champions_tom(s, "NONE", ...)` (aucune récompense expérimentale).
2. **Évolution TOM** = `_evolve_champions_tom(s, "TOM", ...)` (récompense ToM active → pression de sélection).
3. **Mesure** : pour CHAQUE bras, cohorte fixe de champions répliqués, épisode à `benchmark_mode=True`
   (leçon 114b) + memory_retriever neutralisé (P0), **cfg de mesure = `_make_cfg_tom("NONE")` pour les DEUX
   bras** (dynamique de mesure neutre et identique ; on ne LIT que `predictor_head`, la récompense ToM ne
   doit pas perturber différemment la mesure). À chaque tick, pour chaque paire **same-cell** (a,b) :
   enregistrer les 2 échantillons dirigés `{pred=argmax(predictor_head_A), act=last_action_B, latent_A}` et
   symétrique. Ignorer si `last_action == -1` ou `predictor_head is None`.

**Pairing = same-cell** (réplique exacte de `:789`). `pred ∈ {0..7}` (argmax de 8), `act ∈ {0..28}`.

## 5. Composants & interfaces

### 5.1 `_make_cfg_tom(exp_var) -> WorldConfig`
`cfg = _make_cfg()` ; `cfg.active_exp_variable = exp_var` ; return. (`exp_var ∈ {"NONE","TOM"}`).

### 5.2 `_evolve_champions_tom(seed, exp_var, eras=12, num_agents=30, max_ticks=400) -> list`
Mirror `competence_profile._evolve_champions` (cliquet top-5), MAIS `cfg = _make_cfg_tom(exp_var)`. Renvoie
top-5 best_ever. (Duplication nécessaire : `_evolve_champions` hardcode `_make_cfg()`, non paramétrable.)

### 5.3 `_collect_tom_pairs(cfg, genomes, max_ticks=400) -> list[dict]`
Cohorte fixe (`env.benchmark_mode=True`, memory neutralisé AVANT boucle). Réplique `_measure_profile` mais,
à chaque `env.step()`, collecte les paires same-cell. Chaque record = `{"pred": int, "act": int,
"latent": np.ndarray(68,)}`. `latent = concat(predictor_head[8], goal_vector[5], explicit_memory[5],
ntm_memory.flatten()[50])` (guards None → zéros). Renvoie la liste des records.

### 5.4 `_head_accuracy(records) -> float` et `_shuffle_accuracy(records) -> float`
`_head_accuracy` = `mean(r["pred"] == r["act"])`. `_shuffle_accuracy` = permute les `act` (via
`np.random.permutation`, RNG global seedé) puis même moyenne → taux de base (contrôle base-rate). Liste
vide → 0.0.

### 5.5 `_latent_probe(records, split=0.7) -> (acc_true, acc_shuffle)`
Sonde linéaire (readout décode a2). `X = stack(latent)`, `y = act`. Split déterministe par ORDRE (premiers
`split` = train). One-hot `Y` sur les classes observées ; `W = np.linalg.lstsq(X_train, Y_train, rcond=None)[0]` ;
predict `argmax(X_test @ W)` ; `acc_true = mean(pred==y_test)`. `acc_shuffle` = idem avec `y` permuté avant
split (RNG global). < 20 records → (0.0, 0.0) (trop peu).

### 5.6 `_verdict_tom_emergence(acc_head_tom, acc_head_ctrl, acc_shuffle_tom) -> str`
- **TOM_EMERGES** si `acc_head_tom >= acc_shuffle_tom + 0.10` ET `acc_head_tom >= acc_head_ctrl + 0.10`.
- **TOM_INERT** (réfute, attendu) sinon.

### 5.7 `_report_tom(h, per_seed, R, _return)`
`per_seed` = liste de dicts `{seed, ctrl:{acc_head,acc_shuffle,probe_true,probe_shuffle,n},
tom:{acc_head,acc_shuffle,n}}`. Agrège (moyenne). Table ASCII (1 ligne/seed) + moyennes + **lecture décode**
(ctrl acc_head vs shuffle ; ctrl probe_true vs probe_shuffle) + **verdict émergence**. Save JSON
(`name="tom_probe"`). Tout ASCII (cp1252).

### 5.8 `main_tom_probe(R=3, eras=12, num_agents=30, max_ticks=400, seed=1280, _return=False)`
`async_logger.start()/stop()`. Par seed : évolue CONTROL + TOM ; `meas = _make_cfg_tom("NONE")` ;
`rc = _collect_tom_pairs(meas, ctrl_champs_répliqués, ...)` ; `rt = _collect_tom_pairs(meas,
tom_champs_répliqués, ...)` ; calcule accuracies + probe (probe sur CONTROL). Puis `_report_tom`. Smoke :
`main_tom_probe(R=1, eras=2, num_agents=12, max_ticks=80, seed=99280, _return=True)`.

## 6. Verdict attendu & falsifiabilité

Attendu = **TOM_INERT** (substrat plat : 5 cachés sans circuit ToM dédié → la tête reste ~hasard même sous
récompense, comme EDR 111 tool-gate). Falsifiable : si `acc_head_tom` monte nettement au-dessus du CONTROL
et du shuffle → TOM_EMERGES. Le shuffle garde contre un faux positif par base-rate (ex : tout le monde
prédit l'action dominante). La sonde latente (a2) désambiguïse « tête inerte mais représentation informative »
de « rien n'encode l'autre ».

## 7. Provenance, déterminisme, non-régression

- `Harness(name="tom_probe")` → JSON distinct ; seed 1280, smoke 99280 distinct.
- Déterminisme : `SeedManager.seed_boundary` + `benchmark_mode` (mesure) + memory neutralisée + split de sonde
  par ORDRE (pas de RNG) + shuffle via RNG global seedé → 2 runs byte-identiques (vérifié au run).
- Non-régression : `map_elites_compare`/`competence_profile` IMPORTÉS seulement (zéro modif). `src/` VIDE.
- ASCII-only dans tout `print` exécuté (cp1252).

## 8. Tests (TDD, `tests/sandbox/test_tom_probe.py`)

1. **`_make_cfg_tom`** : pose bien `active_exp_variable` ("NONE"/"TOM") + garde metab/payoff sweet.
2. **`_head_accuracy` / `_shuffle_accuracy`** : records synthétiques (ex 3/4 match → 0.75 ; shuffle ~ base
   rate).
3. **`_latent_probe`** : records synthétiques SÉPARABLES (latent corrélé à act) → acc_true > acc_shuffle ;
   records aléatoires → acc_true ≈ acc_shuffle.
4. **`_verdict_tom_emergence` 2 branches** : TOM_EMERGES (tom 0.45, ctrl 0.20, shuffle 0.22) / TOM_INERT
   (tom 0.22, ctrl 0.20, shuffle 0.21).
5. **`_collect_tom_pairs` (fake env)** : env factice à 2 agents same-cell avec `predictor_head`/`last_action`
   fixés → records attendus (pred/act corrects, latent shape 68) ; vérifie `benchmark_mode` posé.
6. **Smoke** `main_tom_probe(R=1, eras=2, num_agents=12, max_ticks=80, seed=99280, _return=True)` : renvoie
   un verdict valide (∈ {TOM_EMERGES, TOM_INERT}), table écrite, JSON écrit.

## 9. Coût & repli

2 bras évolutifs (`eras=12`) × R=3 + 2 collectes cohorte fixe/seed → ~2× EDR 127. Repli : `eras=8`, `R=2`.
Run réel APRÈS revue.

## 10. Doc & mémoire

- **Doc** : `docs/EDR/` (>= 131). Décode (latent ToM par défaut) + émergence (la récompense ToM lève-t-elle
  la prédiction ?) + correction « ToM morte » → « ToM gatée, mesurée ».
- **Mémoire** : MAJ `intelligence-typing-flat-connectome` (ToM n'est PAS morte : circuit gaté `predictor_head`
  + récompense ; verdict mesuré). Selon résultat, lien [[nas-bottleneck-is-substrate-not-search]].

## 11. Coordination (sessions parallèles)

Tooling-only : `git diff src/` VIDE. N'utilise NI substrate_ab/torch/famine/binding-probe (session // active,
EDR 128/130). Réutilise map_elites_compare/competence_profile (non possédés par la session //). `TOM` est un
flag config lu, jamais modifié dans `src/`. Commits path-scoped. Worktree off origin/main (HEAD f2d33c5).
