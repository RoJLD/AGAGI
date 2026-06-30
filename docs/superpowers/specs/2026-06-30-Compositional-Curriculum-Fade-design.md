# Design — Curriculum à fade + mesure P(Y|X) directe (suite EDR 122)

Date : 2026-06-30

## Question scientifique

EDR 122 : torch = DISCOVERY (le curriculum lève la composition Y|X, hit_end 0.03→0.30, ×10). Nuance
BORNÉE par la revue : le joint 0.30 est proche du plafond de rétention de X (~0.38) car X DÉCLINE en
phase B (compo_didx ~0.9→0.4, bascule dure, S1 reward 0). Deux questions restent :

1. **Le plafond de torch (0.30) était-il la rétention de X ou le binding ?** Si on MAINTIENT X (fade),
   torch dépasse-t-il 0.30 (→ le cap était la rétention, binding résolu) ou stagne-t-il (→ binding
   partiel) ?
2. **L'instrument ne mesurait que le JOINT** `mean((move2==Y) ET did_x)`, jamais `move2==Y`
   inconditionnel → P(Y|X) était INFÉRÉ (ratio de médianes), pas mesuré. Ce chantier le MESURE.

## Hypothèse — issues

Lues sur `hit_end` (joint), `compo_didx_end` (rétention X) et **`p_y_given_x_end`** (binding direct) :

- **CEILING_WAS_RETENTION** : sous fade (X maintenu plus haut qu'en bascule dure), torch `hit_end` MONTE
  au-dessus de 0.30 ET `p_y_given_x` reste haut (~>0.7) → le cap de 122 était la rétention de X ; le
  binding Y|X est résolu (confirme la nuance bornée d'EDR 122).
- **CEILING_WAS_BINDING** : le fade maintient X (`compo_didx_end` ↑ vs 122) MAIS `hit_end` stagne ~0.30
  ET `p_y_given_x` modéré (~0.5–0.7) → le binding est PARTIEL, la rétention n'était pas le seul cap.
- (legacy reste CREDIT : le fade ne le fera pas binder — `hit_end`/`p_y_given_x` restent au plancher ;
  lancé en contraste.)

## Architecture — `tools/substrate_ab_compositional.py::run_curriculum_fade` (notre banc)

`run_curriculum` (bascule dure, EDR 122) reste INTACT comme baseline/instrument. On AJOUTE une fonction
de fade séparée.

### Phase A (warmup) — identique à `run_curriculum`
`warmup_trials` × [`forward(obs_a)` → `did_x` → `learn(_warmup_reward(move1, target_x))`]. Enseigne X.

### Phase B à fade LINÉAIRE
Pour le trial t (0-indexé, sur T = `compo_trials`) :
- **`fade_w = fade_w0 · (1 − t / T)`** (décroît de `fade_w0` à ~0 ; helper pur `_fade_weight(t, T, w0)`).
- `forward(obs_a)` → `move1`/`did_x`. **S1 reward = `fade_w · _warmup_reward(move1, target_x)`**
  (au lieu de 0 dur en bascule dure) → maintient X tôt, s'éteint à la fin. `learn(S1_reward, [S1])`.
- `forward(obs_b)` → `move2`. S2 reward = `compositional_reward(move2, target_y, did_x)` (INCHANGÉ).
  `learn(S2_reward, [S2])`.
- **`fade_w0 = 0` ⟹ fade_w ≡ 0 ⟹ S1 reward 0 ⟹ identique à la bascule dure** (baseline cohérence).
  Défaut `fade_w0 = 1.0`.

### Mesure P(Y|X) DIRECTE (comble le gap EDR 122)
Par trial de phase B, tracer DEUX vecteurs : `did_x` ET `y_correct = (move2 == target_y)`
(inconditionnel). Helper pur `_p_y_given_x(y_correct_list, did_x_list) -> float | None` = fraction de
`y_correct` PARMI les trials où `did_x` est vrai (None si aucun did_x dans la fenêtre). Sur le dernier
quart → `p_y_given_x_end` = MESURE propre du binding (P(Y correct | X fait)), plus d'inférence. On garde
aussi le joint `hit`, le `compo_didx` (rétention) et `y_rate` (Y inconditionnel) pour la lecture
complète.

### Retour de `run_curriculum_fade`
`{backend, seed, warmup_trials, compo_trials, fade_w0, n_agents, warmup_didx_end,
hit_start, hit_end, compo_didx_start, compo_didx_end, p_y_given_x_start, p_y_given_x_end,
y_rate_end, delta}`.

### Comparaison
`compare_curriculum_fade(seeds, warmup_trials, compo_trials, n_agents, fade_w0) -> dict` :
A/B apparié legacy/torch (réutilise `compute_ab_verdict`). Verdict heuristique :
- CEILING_WAS_RETENTION si torch `hit_end` médian > 0.35 (au-dessus du 0.30 de 122) ET
  `p_y_given_x_end` médian > 0.7.
- CEILING_WAS_BINDING si torch `compo_didx_end` médian est maintenu HAUT (> 0.6, le fade marche) MAIS
  `hit_end` ≤ 0.35 / `p_y_given_x_end` ≤ 0.7.
- FADE_INEFFECTIVE (garde-fou) si `compo_didx_end` n'est PAS maintenu plus haut que ~0.4 (le fade n'a
  pas fait son travail) → re-spec.
- sinon AMBIGU. Seuils heuristiques ; verdict final lu par l'humain sur les chiffres bruts.
`main_curriculum_fade()` : flag `--curriculum-fade`, knobs `SABC_CF_*`, dump JSON `SABC_CF_OUT`.

## Garde-fous anti-théâtre

1. **Efficacité phase A** (héros, inchangé) : `warmup_didx_end` ≫ base-rate 0.125 sur les deux bras.
2. **Maintien de X = le nouveau contrôle** : le fade DOIT garder `compo_didx_end` plus haut que la
   bascule dure (~0.4 en EDR 122) — sinon le fade n'a pas maintenu X, le test ne mesure rien
   (FADE_INEFFECTIVE). On le vérifie AVANT de lire le verdict de plafond.
3. **Cohérence** : `fade_w0 = 0` reproduit EDR 122 (torch `hit_end` ~0.30, X décline) — même banc.
4. **P(Y|X) DIRECT** : mesure du binding, plus de ratio-de-médianes (comble le gap EDR 122).
5. A/B apparié, déterminisme (`np.random.seed` + `torch.manual_seed`), jamais de scalaire nu.
6. Détection de succès par EXIT CODE (pas de grep sur log).

## Tests

- **Pur — `_fade_weight`** : `_fade_weight(0, 100, 1.0)==1.0` ; `_fade_weight(100, 100, 1.0)==0.0` ;
  `_fade_weight(50, 100, 1.0)==0.5` ; `_fade_weight(t, T, 0.0)==0.0` ∀t (≡ bascule dure).
- **Pur — `_p_y_given_x`** : sur `y_correct`/`did_x` synthétiques connus → fraction conditionnelle
  correcte (ex. did_x=[T,T,F,F], y=[T,F,T,T] → 0.5) ; None si aucun did_x.
- **Smoke `slow`** (`importorskip("torch")`) : `compare_curriculum_fade(seeds=(0,), warmup_trials=40,
  compo_trials=40, n_agents=4)` renvoie `verdict_fade` ∈ {CEILING_WAS_RETENTION, CEILING_WAS_BINDING,
  FADE_INEFFECTIVE, AMBIGU} + `per_seed` avec `p_y_given_x_end`/`hit_end`/`compo_didx_end`.
- **Non-régression** : `run_curriculum` (bascule dure) et la suite existante restent verts.

## Hors périmètre (YAGNI)

- Pas de schedule palier/constant (linéaire validé).
- Pas de modif `backend.py`/`backend_torch.py`/`substrate_ab.py` ni de `run_curriculum` (intact).
- Pas de torch-en-prod (chantier séparé) ; pas de sweep `fade_w0` (1 valeur, knob dispo).

## Suite (selon issue)

- **CEILING_WAS_RETENTION** : binding résolu pour torch → la voie apex = torch-en-prod + shaping du
  craft qui maintient le means ; passer au gros chantier torch-en-prod.
- **CEILING_WAS_BINDING** : le binding torch est partiel même avec X maintenu → creuser le mécanisme
  (TD(λ)/éligibilité, plus de trials, représentation) avant prod.
- **FADE_INEFFECTIVE** : re-spécifier le fade (w0/schedule) — il ne maintient pas X.

## Livrable & contraintes

- EDR cible = **123** (vérifier libre — tree partagé).
- Commits **path-scoped** (sessions parallèles sur `feat/d1-prod-pairing`).
- **Pas de PR-off-main** (même dépendance backend qu'EDR 117/119/120/122).

## Variables d'expérience

`backend` (legacy/torch), `fade_w0` (0 = bascule dure baseline / >0 = fade), `warmup_trials`,
`compo_trials`, `seed`, `n_agents`. Tâche X-gate-Y inchangée (`obs_a`/`obs_b` fixes). `target_x=0`,
`target_y=4`.
