# Design — Sweep taille cachée sur le banc compositionnel (suite EDR 117)

Date : 2026-06-30

## Question scientifique

EDR 117 a conclu **Issue 2 (TAILLE_REQUISE)** : à la taille de production (~5 cachés), *les deux*
substrats échouent le means→ends compositionnel (legacy Δ médian −0.007, torch Δ médian +0.010 ;
hit_end ≤ 0.155). Mais la taille cachée n'a PAS été variée → on ne sait pas si **plus de cachés**
débloque la composition, ni pour quel substrat. Ce sweep tranche le verrou conjoint *taille × règle*.

Mécanisme (vérité terrain) : `MambaAgent(num_inputs=59, num_outputs=108, num_nodes=172)` → hidden =
`num_nodes − 167` = 5 par défaut. Les DEUX backends lisent N dynamiquement
(`MambaBatchModel.max_H = num_nodes − I − O` ; `recurrent_forward: N = genome.num_nodes` ;
`TorchPopulationModel` lit `genome.num_nodes`/`num_inputs`/`num_outputs`) → l'A/B legacy↔torch tient à
toute taille. Augmenter `num_nodes` en gardant I/O fixes (59/108) grossit UNIQUEMENT la couche cachée
(canal de mémoire récurrente où vit la composition « se souvenir d'avoir fait X »).

## Hypothèse — 3 issues décisives

Lues sur la **COURBE hit_end vs taille cachée, par backend** (pas un scalaire par cellule) :

- **A — la taille lève LES DEUX** (hit_end monte avec hidden pour legacy ET torch) → verrou =
  capacité/représentation ; l'autograd n'est pas spécialement requis → *grossir le substrat suffit*,
  la règle est secondaire.
- **B — la taille lève TORCH seul** (torch monte, legacy reste au plancher) → verrou conjoint
  **gradient × taille** ; le hebbien ne sait pas exploiter la capacité même fournie → *torch-prod
  justifié ET doit être gros* (cas le plus fort pour la migration moteur SOTA).
- **C — la taille ne lève NI l'un NI l'autre** (plancher 0–0.15 jusqu'à hidden=100, sous les deux
  inits) → ce n'est PAS la taille ; verrou plus profond (structure de tâche / crédit différé /
  encodage obs) → re-spec (curriculum progressif, k>2 étapes) ; l'« Issue 2 » d'EDR 117 est elle-même
  raffinée (ce n'était pas la taille seule).

## Architecture — extension de `tools/substrate_ab_compositional.py` (NOTRE fichier, commit `fbec167`)

### Paramètres ajoutés à `run_compositional`

`run_compositional(backend, seed, trials, n_agents, target_x, target_y, num_nodes=172, init_scale="prod")` :

- `num_nodes` : taille du connectome (hidden = `num_nodes − 167`). Construit
  `MambaAgent(num_nodes=num_nodes)` (I/O par défaut 59/108).
- `init_scale ∈ {"prod", "normalized"}` :
  - `"prod"` : init par défaut de `MambaAgent` (`W = randn × 0.1`) — NON touché.
  - `"normalized"` : après construction, `genome.W *= sqrt(171 / (N − 1))` (N = num_nodes), AU NIVEAU
    GÉNOME → contrôle backend-agnostique (legacy et torch lisent le même W). Hold l'excitation
    `Σ_{k≠j} H_k W_kj` (variance ∝ (N−1)·Var(W)) ≈ invariante à N, calibrée sur N_ref=172.
  - À N=172 le facteur vaut 1 → **`normalized` ≡ `prod` au point d'ancrage** (déduplication).
- L'init normalisé rescale aussi la diagonale (δ = sigmoid(diag W)) ; diag init ~N(0, 0.01), facteur
  ∈ [0.80, 1.0] → δ reste ≈ 0.5 (effet sur la constante de temps négligeable, documenté en caveat).

### Nouvelle fonction `sweep`

`sweep(hiddens, inits, seeds, trials, n_agents) -> dict` :
- Pour chaque `(hidden, init)` (en dédupliquant `normalized@5 == prod@5`), exécute l'A/B apparié
  legacy↔torch par seed via `run_compositional`, agrège par `compute_ab_verdict` (réutilisé).
- Renvoie `{"cells": [...], "curve": {...}}` :
  - `cells` : un dict par `(hidden, init)` = `{hidden, init, verdict, median_diff, n_gradient_favorable,
    n, sign_p, per_seed}` (per_seed = liste {seed, legacy_delta, torch_delta, diff, legacy, torch}).
  - `curve` : `{"legacy": [(hidden, init, median_hit_end, median_delta), ...], "torch": [...]}` — la
    lecture maîtresse (hit_end médian par taille et par backend).
- `main()` : env `SABC_HIDDENS` (def "5,20,50,100"), `SABC_INITS` (def "prod,normalized"),
  `SABC_SEEDS` (def "0,1,2,3,4"), `SABC_TRIALS` (def "250"), `SABC_AGENTS` (def "8"). Imprime la
  table-courbe (hidden × init × backend → hit_end médian, delta médian) + verdict par cellule.

### Réutilisations (sans modification)

`make_population` (ADR-003), `MambaAgent`, `compute_ab_verdict` + `_MOVE` (de `tools/substrate_ab`).
NE PAS modifier `backend.py` / `backend_torch.py` / `substrate_ab.py` (propriété session //).

## Grille & instrument

- Hidden **{5, 20, 50, 100}** (5 = ancrage EDR 117) ↔ num_nodes {172, 187, 217, 267}.
- Init **{prod, normalized}** (normalized@5 dédupliqué = prod@5).
- Backends {legacy, torch}. Seeds **{0,1,2,3,4}**.
- → **7 cellules** (hidden,init) × 2 backends × 5 seeds = **70 runs**. `trials=250`.
- **Jamais de scalaire nu** : par cellule, hit_start/hit_end/delta PAR seed + médianes ; verdict
  apparié par cellule ; **+ la courbe** hit_end(hidden) par backend = lecture décisive A/B/C.

## Garde-fous anti-théâtre

1. **Ancrage de cohérence** : hidden=5 (init prod) doit reproduire EDR 117 (legacy Δ ≈ −0.007,
   torch Δ ≈ +0.010, hit_end torch ≤ ~0.16) — sinon le banc a dérivé, verdict suspendu.
2. **Contrôle d'init** : le bras `normalized` confirme qu'un éventuel null à grande taille n'est PAS
   un artefact d'échelle d'activation (si prod montre un null mais normalized lève, c'était l'init ;
   si les deux montrent le même plancher, le null est réel).
3. **Lecture en valeur absolue** : hit_end sort-il du plancher (0–0.15) vers du sens (>0.3) ? — pas
   seulement le sign-test apparié (n=5 plafonné à p≈0.062, pas de puissance par cellule ; la COURBE
   inter-tailles agrège l'évidence).
4. **Anti-sous-entraînement** : `trials=250` (vs 150 en EDR 117) — ne pas fausser un null en
   sous-entraînant les gros réseaux (biais artificiel vers Issue C).
5. **Déterminisme** : `np.random.seed` + `torch.manual_seed` par run.
6. **Détection de succès par EXIT CODE python** (piège EDR 108 : `2>/dev/null` avale la sortie TRAJ →
   faux échec). Jamais de grep sur log redirigé.

## Tests

- **Pur — init normalisé** : `run_compositional` avec `init_scale="normalized"` produit un génome dont
  `W == prod_W × sqrt(171/(N−1))` (vérifié sur un agent reconstruit déterministe, seed fixe) ;
  `init_scale="prod"` laisse W identique à `MambaAgent(num_nodes=N)` brut (même seed).
- **Pur — mapping taille** : `num_nodes=N` donne hidden = N−167 et `genome.num_nodes == N`,
  `num_inputs==59`, `num_outputs==108`.
- **Pur — dédup ancrage** : à hidden=5, le facteur normalized = 1.0 (W normalized == W prod).
- **Smoke `slow`** (`pytest.importorskip("torch")`) : `sweep(hiddens=(5,20), inits=("prod",),
  seeds=(0,), trials=20, n_agents=4)` renvoie `cells` non vide avec verdict ∈
  {GRADIENT_GAGNE, HEBBIEN_GAGNE, NEUTRE} par cellule + `curve["legacy"]`/`curve["torch"]` non vides.
- **Non-régression** : `test_compositional_reward_truth_table` + `test_compositional_ab_smoke`
  restent verts (ajout de params à signature par défaut rétro-compatible).

## Hors périmètre (YAGNI)

- Pas de curriculum progressif / k>2 étapes (suite SI Issue C).
- Pas de torch-en-prod (contrat forward complet = gros chantier multi-sessions séparé).
- Pas de modif de `backend.py` / `backend_torch.py` / `substrate_ab.py`.
- Pas de sweep `n_agents` ni de re-test apex réel (bloqué hors torch-prod).

## Suite (selon issue)

- **A (taille lève les deux)** : dimensionner le substrat cible ; la règle est secondaire.
- **B (taille lève torch seul)** : feu vert renforcé torch-en-prod, dimensionné gros.
- **C (taille ne lève rien)** : durcir/re-spécifier la tâche (curriculum, mémoire k-étapes) avant tout
  investissement substrat.

## Livrable & contraintes

- EDR cible = **118** (vérifier libre à l'écriture — tree partagé, collisions possibles).
- Commits **path-scoped** (sessions parallèles sur `feat/d1-prod-pairing`).
- **Pas de PR-off-main** (même contrainte qu'EDR 117 : le banc importe `backend.py`/`substrate_ab.py`
  absents de `origin/main` → vit sur `feat` où les dépendances existent).

## Variables d'expérience

`num_nodes` (172/187/217/267), `init_scale` (prod/normalized), `backend` (legacy/torch),
`trials`/`seeds`/`n_agents`. Tâche compositionnelle X-gate-Y inchangée (EDR 117).
