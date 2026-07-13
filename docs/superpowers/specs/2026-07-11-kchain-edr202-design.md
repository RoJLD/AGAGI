# EDR 202 — KCHAIN : la loi crédit-horizon × curriculum généralise-t-elle à la profondeur de composition ?

## Contexte

COS Phase B (#155) → **[2] CRÉDIT-ATTRIBUÉ** ; EDR 201 (#159) → **BOTH-NECESSARY** (crédit-horizon tick-return ET
bootstrap curriculum tous deux requis, aucun suffisant) + **[2]-ROBUSTE** sur E0. La loi transversale (4 fils) dit
« verrou = crédit/optim pas capacité ; warm-start franchit le bootstrap ». Mais tout ça est mesuré sur la composition
**2-pas** craft→consume de COS. EDR 202 teste si le levier (crédit-horizon × curriculum, sur un petit substrat numpy
fixe) est le débloqueur **GÉNÉRIQUE** du bootstrap de composition, ou est spécifique à K=2.

## Objectif

Nouvelle écologie standalone `tools/kchain_edr.py` (pur numpy, ZÉRO `src/`, collision-safe) à **chaîne de profondeur
K** paramétrable. Deux résultats gelés :
- **Composant A — courbe de généralité** : K ∈ {2,3,4,5}, entraînement avec le levier COMPLET (fenêtre-crédit large +
  curriculum progressif-K) → binding + survie par K. **GÉNÉRIQUE** (binde à tous les K) vs **COS-SPÉCIFIQUE** (rupture
  à un K*).
- **Composant B — BOTH-NECESSARY à K=3** : 2×2 `fenêtre{courte, large} × curriculum{off, on}` → les deux leviers
  restent-ils nécessaires au-delà de K=2 ?

## Contraintes globales

- **Standalone** : nouveau fichier `tools/kchain_edr.py`, pur numpy, AUCUN import de `src/`/`world_1_stoneage.py`/
  `backend_torch.py`/`craft_or_starve_edr.py` (auto-contenu ; l'obs diffère de COS). Additif (nouveau fichier + tests).
- **Substrat à capacité FIXE** : réseau récurrent numpy `N_H=16` cachés **constant sur TOUS les K** → disculpe la
  capacité (16 cachés ≫ compteur à ≤5 états).
- **Verdicts gelés pré-enregistrés** ; **déterminisme** (`np.random.default_rng(seed)`, 2 runs même seed byte-identiques).
- **Tree partagé** : chemins ABSOLUS worktree pour tous les handoffs sous-agent ; commits path-scopés ; pytest/git
  préfixés `cd` worktree.

## Monde KCHAIN(K) — accumulateur à progression persistante

Généralise COS : composer = accumuler K−1 pas puis consommer. Le compteur `prog` est **CACHÉ** → binding = le réseau
récurrent doit compter ses propres pas dans H et consommer au bon compte.

- **Actions** : `NOOP=0, STEP=1, CONSUME=2, FORAGE=3` + `N_NOISE=4` leurres → `N_ACTIONS=8`. `OBS_DIM = 2 + N_NOISE`
  (`[material, bias=1, noise×4]` — PAS de `prog` observable).
- **État** : `prog ∈ {0,…,K−1}` (persistant, PAS de reset par cycle). `E` énergie. Matériau `mat ~ Bernoulli(p_mat)`
  par sous-pas.
- **Dynamique par sous-pas** (mort ABSORBANTE à `E≤0`, vérifiée 1×/sous-pas en fin) :
  - `STEP` & alive & `mat` & `prog<K−1` → `prog += 1`, coût `c_step`.
  - `STEP` & alive & (`¬mat` OU `prog==K−1`) → coût `c_step_bad` (gaspillé).
  - `CONSUME` & alive & `prog==K−1` → `E += R`, `prog = 0`, coût `c_consume`.
  - `CONSUME` & alive & `prog<K−1` → coût `c_consume_empty` (mis-émission, LA feature d'inescapabilité).
  - hunger : `E -= h` chaque sous-pas.
  - Bras `absent` (témoin) : `FORAGE` → livraison inconditionnelle `f_forage` au sous-pas SUIVANT (délai apparié).
- **K=2 = COS structurel** : 1 STEP (prog 0→1) puis CONSUME (à prog==1) = craft→consume.
- **Params gelés** : `p_mat=0.8` (stochastique → défait l'horloge ; assez haut pour viabilité linéaire en K),
  `c_step=0.5, c_step_bad=2.0, c_consume=0.2, c_consume_empty=6.0, h=1.0, f_forage=4.0, T=1000`. **`R` calibré par K**
  (voir viabilité) pour garder l'oracle viable ; `E0` calibré par K (borne inférieure, cf COS I1).

## Politiques de référence + gate de viabilité par-K

- `oracle_chain_policy` : STEP si (`mat` & `prog<K−1`), CONSUME si `prog==K−1`, sinon NOOP (porte `prog` en mem).
- `metronome_policy(K)` : STEP,STEP,…(K−1),CONSUME open-loop (ne lit ni mat ni prog).
- `random_policy(seed)`, `oracle_forage_policy` (bras absent).
- **`calibrate_K(K)`** : balaie `(R, E0)` et vérifie les gates (mediane sur seeds pilotes) : **oracle-chain survie ≥ 0.90 ;
  métronome ≤ 0.40 ; random ≤ 0.20** (bras inesc) ; oracle-forage ≥ 0.90 & random ≤ 0.20 (bras absent). Retourne le
  `(R_K, E0_K)` minimal viable (borne inférieure — la Phase apprenant re-calibre `E0` contre le headroom apprenant).
  GATE DUR : si aucun `(R,E0)` viable pour un K → STOP (le monde K n'exige/permet pas le conditionnement).
- `survival_auc(alive_matrix)` = médiane-par-agent de la fraction vivante sur le dernier quart (défense anti-immortels).
- `binding_gap` = `P(CONSUME | prog==K−1) − P(CONSUME | prog<K−1)` au niveau sous-pas, agents vivants, dernier quart.

## Apprenant + les deux leviers

- **`NpChainLearner(seed, arm)`** : cœur récurrent `H_t = tanh(W_ih·obs + W_hh·H_{t−1} + b_h)` → readout → softmax,
  `N_H=16`, `LR=0.02`, `TEMP=1.0`, baseline EMA(0.99). Poids persistants. REINFORCE, **pas de BPTT** (H_prev détaché).
  Auto-contenu (n'importe pas COS).
- **Levier 1 — fenêtre de crédit W (retour n-pas bufferisé)** : on bufferise TOUS les acts d'un épisode `(ctx_t, δ_t)`
  (δ = delta d'énergie du sous-pas), puis pour chaque act on crédite `advantage_t = (Σ δ_{t..t+W−1}) − baseline` et on
  applique REINFORCE à `ctx_t` (H_prev constante → pas de BPTT). **`W=2`** = analogue tick-return de COS (insuffisant
  dès que la chaîne dépasse 2 sous-pas) ; **`W=W_long`** (= `2*K`, borne haute couvrant la chaîne) = fenêtre-chaîne.
  *Prédiction : W=2 échoue à K≥3 ; W_long réussit (avec curriculum).*
- **Levier 2 — curriculum progressif-K** : warm-start en entraînant successivement sur les mondes K′=2,3,…,K (même
  apprenant, poids persistants ; chaque cran `n_stage` épisodes ; `(R,E0)` = calibrés par K′). « off » = froid
  directement au K cible (mêmes épisodes totaux, budget apparié). Analogue easy→hard de CURR-001/004.
- **`rollout_learn_window(learner, arm, K, params_K, seed, M, n_episodes, W)`** : boucle d'entraînement fenêtre-W.
- **`rollout_learn_progressive(learner, arm, K, calib, seed, M, n_stage, W)`** : curriculum 2→…→K (appelle
  `rollout_learn_window` par cran avec le `(R,E0)` du cran).
- **`evaluate_chain(learner, arm, K, params_K, seed, M)`** → `{survival, binding_gap, consume_rate}` (poids GELÉS,
  éval GREEDY argmax).

## Composant A — courbe de généralité

`generality_curve(seeds, K_grid=(2,3,4,5), M, n_stage, W_long_factor=2) -> {"grid":[{K, binding, survival, composes}],
"verdict"}`. Pour chaque K : calibrer `(R_K,E0_K)`, entraîner le levier COMPLET (`rollout_learn_progressive` avec
`W=W_long_factor*K`), évaluer. `composes = binding≥0.5 ET survie≥0.5`. **Verdict gelé** : `"GENERIQUE"` si `composes`
à TOUS les K du grid ; `"COS-SPECIFIQUE(K*)"` si la 1ʳᵉ rupture est à K* (rapporte la courbe complète).

## Composant B — BOTH-NECESSARY à K=3

`decompose_2x2_chain(seeds, K=3, M, n_stage, n_episodes)` : 2×2 `W{2, W_long} × curriculum{off, on}` (bras inesc).
Cellules : (W2,off)=court/froid, (W2,on)=court/curriculum, (Wlong,off)=chaîne/froid, (Wlong,on)=chaîne/curriculum.
Dispatcher `_train_cell_chain(W_mode, curriculum, …)`. **Verdict gelé** (arbre gaté sur (Wlong,on) = la cellule
attendue-composante, sinon INCOHERENT) : `CURRICULUM-SUFFISANT` si (W2,on) compose ; `CREDIT-SUFFISANT` si (Wlong,off)
compose ; sinon `BOTH-NECESSARY`. (Réplique EDR 201 à K=3 ; on ne préjuge PAS.)

## CLI + rapports

`--kchain` lance : `calibrate_K` par K (rapport viabilité) → `generality_curve` (courbe + verdict) →
`decompose_2x2_chain` K=3 (2×2 + verdict). Rapports `_report_*`.

## Tests (`tests/sandbox/test_kchain_edr.py`, APPEND/CREATE)

Contrat/déterminisme/sanité UNIQUEMENT (jamais préjuger la courbe ni la cellule ouverte) :
- `test_world_k2_matches_cos_structure` : à K=2, oracle-chain survit (viable) et métronome meurt (config calibrée
  réduite) — le monde K=2 EXIGE le conditionnement (réplique la structure COS).
- `test_chain_learner_determinism` : 2 `rollout_learn_window` au même seed → poids byte-identiques.
- `test_window_credit_shapes` : `rollout_learn_window` retourne un learner ; `evaluate_chain` a les bonnes clés,
  `binding_gap ∈ [−1,1]`.
- `test_generality_curve_contract` : `generality_curve(seeds=(1000,), K_grid=(2,3), config minuscule)` → grid長=2,
  clés `{K,binding,survival,composes}`, verdict ∈ ensemble gelé.
- `test_decompose_2x2_chain_contract` : 4 cellules, verdict ∈ ensemble gelé.
- `test_progressive_reaches_target_K` : le curriculum progressif à K=3 s'entraîne sans erreur et produit un learner
  évaluable (contrat, pas verdict).

## Run décisif (contrôleur, hors tests)

`python -m tools.kchain_edr --kchain` (1 pass ; déterminisme prouvé par tests). Résultats :
- **Courbe** : GÉNÉRIQUE (le levier binde à K=2..5) → la loi crédit-horizon×curriculum est le débloqueur générique du
  bootstrap de composition, pas un artefact de K=2 ; COS-SPÉCIFIQUE(K*) → la loi a une limite de profondeur (rapporte-la).
- **2×2 @ K=3** : BOTH-NECESSARY attendu (réplique 201 à profondeur supérieure) ; CURRICULUM-SUFFISANT / CREDIT-SUFFISANT
  raffineraient.
- Un `INCOHERENT`, une viabilité `calibrate_K` qui ÉCHOUE à un K, ou W=2 qui composerait à K≥3 = signal à investiguer
  AVANT consolidation.

## Staging (Phase A puis Phase B, comme COS)

- **Phase A** (ce cycle) : monde `KCHAIN(K)` + politiques de référence + `calibrate_K` + gates de viabilité par-K +
  `survival_auc`/`binding_gap` (mesure). **GATE DUR** : pour chaque K ∈ {2,3,4,5}, un `(R_K,E0_K)` doit rendre le monde
  viable (oracle-chain ≥ 0.90 ; métronome ≤ 0.40 ; random ≤ 0.20 ; oracle-forage/absent OK). Si un K échoue → on le
  sait AVANT de construire l'apprenant (évite le piège I1 de COS) → on rapporte la fenêtre viable et on borne le K_grid
  de Phase B. Pur numpy, aucune machinerie d'apprentissage.
- **Phase B** (contingente au gate A) : `NpChainLearner` + fenêtre-crédit W + curriculum progressif-K +
  `generality_curve` + `decompose_2x2_chain` + verdicts gelés. `E0_K` re-calibré contre le headroom apprenant (I1).

## Compute

Lourd : K=5 (cycles longs) + curriculum 4 crans + courbe 4 K + 2×2. 3 seeds, `n_stage`/`n_episodes` tunés, 1 pass.
Cible pragmatique : privilégier la clarté du verdict sur l'exhaustivité ; `log` tout budget tronqué. Estimation
plusieurs dizaines de minutes → ~1-2 h ; run en arrière-plan. Phase A (réfs, sans apprentissage) est rapide.
