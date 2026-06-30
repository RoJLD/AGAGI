# Design — Curriculum compositionnel (suite EDR 120, crédit H2 vs découverte H3)

Date : 2026-06-30

## Question scientifique

EDR 119 a écarté la TAILLE, EDR 120 a écarté la MÉMOIRE : `did_x` est décodable de l'état qui produit
`move2` (AUC~0.90), donc l'information est **disponible** mais la règle ne l'**exploite** pas. Restent
deux hypothèses sur l'échec compositionnel means→ends :

- **Crédit (H2)** : même avec X maîtrisé ET la mémoire présente, la règle (hebbien legacy / autograd
  TD(0) torch) ne sait pas binder `move2` sur `did_x`.
- **Découverte (H3)** : la règle *pourrait* binder, mais la récompense jointe trop rare (~+1 seulement
  si X *et* Y, quasi jamais par hasard) ne donne jamais de signal d'amorçage.

Le curriculum sépare les deux : **enseigner X d'abord (dense), puis tester Y|X**. Si une fois X
maîtrisé la composition se débloque → c'était la découverte (sparse reward) ; sinon → c'est le crédit.

## Hypothèse — 3 issues

- **DISCOVERY (H3)** : le warmup monte `did_x` (X maîtrisé) ET la phase B `hit_end` décolle du plancher
  (>~0.3) vs baseline (warmup=0) planché → le verrou était la découverte ; une fois X fiable, Y|X
  s'apprend → **shaping du craft actionnable en prod**.
- **CREDIT (H2)** : le warmup monte `did_x` MAIS la phase B reste au plancher (~0–0.15) → même avec X
  maîtrisé + mémoire (EDR 120) + chemin dense, la règle ne binde pas Y sur did_x → **mécanisme de
  crédit plus profond requis** (TD(λ)/éligibilité, mémoire explicite entraînée).
- **WARMUP_FAILED (garde-fou)** : `did_x` ne monte pas en phase A → curriculum invalide (on ne sait
  même pas enseigner X ici) → re-spec (le test ne mesure rien).

## Architecture — `tools/substrate_ab_compositional.py::run_curriculum` (notre banc)

### Deux phases, bascule dure

`run_curriculum(backend, seed, warmup_trials, compo_trials, n_agents, target_x, target_y) -> dict` :

- **Phase A (warmup, dense sur X)** : `warmup_trials` itérations de :
  `forward(obs_a)` → `move1` → `did_x = (move1 == target_x)` →
  `learn(reward = +1 si did_x sinon −1, [{"move": move1, ...}])`.
  Enseigne X sur `obs_a` FIXE (mono-contingence directe, apprenable cf. EDR 115). Pas de S2.
  Trace la trajectoire `did_x` (taux par quart) → `warmup_didx_start` / `warmup_didx_end`.
- **Phase B (compositionnel, bascule DURE)** : `compo_trials` itérations du corps compositionnel
  d'EDR 117 : `forward(obs_a)` → `move1`/`did_x`, `learn(0, [S1])` (différé), `forward(obs_b)` →
  `move2`, `learn(compositional_reward(move2, target_y, did_x), [S2])`. `obs_b` FIXE, n'encode pas
  `did_x`. Trace `hit` (X-puis-Y pleinement correct) ET `did_x` (rétention de X sans renfort direct).
- `obs_a` est le MÊME vecteur fixe dans les deux phases (le X appris en A se réutilise en B).
- Renvoie : `warmup_didx_start`/`warmup_didx_end` (efficacité), `hit_start`/`hit_end` (sur la phase B),
  `compo_didx_start`/`compo_didx_end` (rétention X en B), `delta = hit_end − hit_start`.

### Comparaison A/B + baseline

`compare_curriculum(seeds, warmup_trials, compo_trials, n_agents) -> dict` :
- A/B apparié `legacy` vs `torch` par seed (réutilise `compute_ab_verdict` pour le contraste de
  learnabilité torch↔legacy, comme EDR 117/119).
- **Baseline `warmup_trials=0`** : `run_curriculum` avec warmup=0 ≡ `run_compositional` (phase A vide)
  → doit reproduire le plancher EDR 117/119 (cohérence) ; le curriculum (warmup>0) doit BATTRE ce
  plancher pour conclure DISCOVERY.
- `main_curriculum_probe()` (ou flag `--curriculum`) : knobs env `SABC_CU_*`, dump JSON `SABC_CU_OUT`.

### Verdict (lecture, jamais le scalaire nu)

Par bras et par seed : `warmup_didx_end`, `hit_end` (phase B), `compo_didx_end`, `delta`. Agrégats
médians par backend. Logique :
- WARMUP_FAILED si `warmup_didx_end` ne monte pas nettement au-dessus du base-rate (~1/8) sur un bras
  → le curriculum n'a pas décollé.
- DISCOVERY si warmup réussit (did_x haut) ET `hit_end` médian décolle (>~0.3) sur au moins un bras.
- CREDIT si warmup réussit MAIS `hit_end` reste au plancher (≤~0.15) sur les deux bras.
  (Seuils = heuristiques de cadrage ; le verdict final est lu par l'humain sur les chiffres bruts.)

## Garde-fous anti-théâtre

1. **Efficacité phase A = le héros** : `did_x` DOIT monter en warmup (`warmup_didx_end` ≫
   `warmup_didx_start`/base-rate), sinon le curriculum n'a pas décollé → verdict SUSPENDU. X
   mono-contingence est apprenable (EDR 115) mais on le VÉRIFIE sur ce banc.
2. **Contraste baseline** : `warmup=0` reproduit le plancher EDR 117/119 (cohérence) ; le curriculum
   doit le BATTRE pour conclure DISCOVERY (sinon CREDIT).
3. **Rétention X en phase B** : suivre `did_x` à travers B (`compo_didx_start`→`compo_didx_end`) — s'il
   DÉCLINE (S1 reward 0, rien ne renforce X directement), c'est informatif : le crédit différé ne
   maintient même pas le means. À reporter.
4. **A/B apparié**, déterminisme (`np.random.seed` + `torch.manual_seed`), trajectoires conservées.
5. Détection de succès **par EXIT CODE** (pas de grep sur log).

## Tests

- **Pur** : la logique de récompense warmup est `+1 si did_x sinon −1` (testable sur `move1`
  synthétiques) ; la phase B réutilise `compositional_reward` (déjà testé). Vérifier qu'un
  `run_curriculum(warmup_trials=0)` exécute la phase B seule (équivalent compositionnel).
- **Smoke `slow`** (`importorskip("torch")`) : `compare_curriculum(seeds=(0,), warmup_trials=40,
  compo_trials=40, n_agents=4)` renvoie `verdict` ∈ {DISCOVERY, CREDIT, WARMUP_FAILED} + `per_seed`
  non vide avec `warmup_didx_end`/`hit_end`/`compo_didx_end`.
- **Non-régression** : la suite existante de `test_substrate_ab_compositional.py` reste verte.

## Hors périmètre (YAGNI)

- Pas de shaping décroissant (bascule dure validée ; le shaping confondrait le verdict crédit).
- Pas de modif `backend.py` / `backend_torch.py` / `substrate_ab.py`.
- Pas de torch-en-prod ; pas de k>2 étapes ; pas de sweep taille (clos EDR 119).

## Suite (selon issue)

- **DISCOVERY** : le shaping du craft (récompense dense intermédiaire) est la voie en prod pour lever
  l'apex means→ends ; valider sur le monde réel (chantier séparé).
- **CREDIT** : changer le mécanisme de crédit (TD(λ)/éligibilité, mémoire explicite entraînée) — le
  dernier verrou identifié de la chaîne 104-120.
- **WARMUP_FAILED** : durcir/re-spécifier le warmup (l'apprentissage de X échoue même en dense).

## Livrable & contraintes

- EDR cible = **121** (vérifier libre — tree partagé).
- Commits **path-scoped** (sessions parallèles sur `feat/d1-prod-pairing`).
- **Pas de PR-off-main** (même dépendance backend qu'EDR 117/119/120).

## Variables d'expérience

`backend` (legacy/torch), `warmup_trials` (0 = baseline / >0 = curriculum), `compo_trials`, `seed`,
`n_agents`. Tâche X-gate-Y inchangée (`obs_a`/`obs_b` fixes). `target_x=0`, `target_y=4`.
