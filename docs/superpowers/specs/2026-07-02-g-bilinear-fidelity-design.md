# EDR 193 (REFORMULÉ) — La g-fidélité sur env-grille est-elle une anticipation LATENTE ou un artefact de ré-encodage d'ENTRÉE ? (design)

> **Date** : 2026-07-02. **Fil** : G4 / anticipation (RE-EXAMINE EDR 135). **Bloc** : 193 (190+). **Statut** : design
> RÉVISÉ après revue finale opus (voir §0). À implémenter en subagent-driven.

## 0. Correction de prémisse (revue finale opus, vérifiée empiriquement)

Le design **initial** posait : « le g LINÉAIRE d'EDR 135 était NEUTRE sur env-grille (obs riches) ; un g bilinéaire
craque-t-il là ? ». **Cette prémisse est FAUSSE** (vérifié en relançant le tool d'EDR 135) :
- env-grille (obs riches causal) : **G_FIDELE** (median ~0.75, sign_p 0.000) — le g linéaire anticipe DÉJÀ.
- synthétique (obs gaussiennes, pas de couplage action→obs) : **NEUTRE** (median ~1.04) — c'est LÀ le « neutre » d'EDR 135.

Donc « le bilinéaire craque-t-il là où le linéaire échouait ? » est **moot** sur env-grille (le linéaire n'échoue pas),
et un `bilin < learned` y serait un **artefact de ré-encodage** (opus, Q5 confirmé) : la position est un one-hot dans
les nœuds d'ENTRÉE, `pos_t = clip(pos_{t-1}+move−1)` en fait un **opérateur de décalage déterministe par action** →
trivialement récupérable par une carte linéaire état-dépendante, SANS aucune anticipation de dynamique cachée.

**Reformulation** : la vraie question G4, et un RE-EXAMEN d'EDR 135, est **où** vit cette fidélité — dans le
ré-encodage d'entrée (trivial) ou dans le latent CACHÉ (anticipation réelle) ?

## 1. Question

> **La g-fidélité mesurée sur env-grille (linéaire ET bilinéaire) SURVIT-elle quand on restreint la métrique aux
> nœuds CACHÉS (hors blocs one-hot d'entrée/sortie), ou s'effondre-t-elle vers NEUTRE — révélant que le G_FIDELE
> d'EDR 135 était un artefact de ré-encodage de position, pas une anticipation latente ?**

Et, conditionnellement : si une anticipation latente CACHÉE existe, le g bilinéaire (état-dépendant) la capte-t-il
mieux que le linéaire ?

## 2. Layout des nœuds (vérifié dans `src/agents/mamba_agent.py:356-376`)

`H_rec` est indexé en ordre agent-local par `map_idx` : **entrées** `[0, I)`, **cachés** `[I, N−O)`, **sorties**
`[N−O, N)`. Pour l'agent env-grille : `I = _OBS_DIM = 14`, `O = 108`, `N = 172` → **cachés = [14, 64)** (50 nœuds ;
le one-hot(pos)++one-hot(danger) vit dans les entrées `[0,14)`).

## 3. Substrat et collecte (inchangés)

Rollout env-grille 1-D déterministe (miroir de `collect_ratios_env`, EDR 135), triplets `(H_prev, move, H_next,
g_learned)` en dims PLEINES (N=172). `g_learned = m.G_batch[0][:, map_idx][prev_move]` (le g linéaire appris = la
mesure exacte d'EDR 135). Auto-contenu, déterministe, pas de Biosphere/HoF/KuzuDB.

## 4. Prédicteurs (fit offline PAR SEED, split temporel 70/30 par action) — INCHANGÉS

- **learned-linéaire** (référence EDR 135) : `ΔH = g_learned`.
- **linéaire-offline** (contrôle) : `ΔH = c_a` (moyenne train de ΔH par action).
- **bilinéaire** : `ΔH = H_prev @ W_a`, `W_a` ridge par action (`λ=1.0`, convention ligne).

## 5. Métrique décomposée — le CONTRÔLE DÉCISIF (nouveau)

Pour chaque prédicteur, calculer le ratio `pred_err/base_err` sur le test-set de DEUX façons :
- **FULL** : sur les N=172 dims (reproduit EDR 135 / la mesure initiale).
- **HIDDEN** : sur les seules dims cachées `[I, N−O) = [14, 64)` (exclut le ré-encodage one-hot entrée/sortie).

`transition_error` est réutilisé mais appliqué à un **sous-vecteur** (via un masque d'indices). Filtre
`base_err_subset > base_thresh` (1e-4).

## 6. Verdict pré-enregistré (gelé), agrégé sur K seeds

Réutilise `fidelity_verdict` (FIDELE si median<0.95 & majorité ; sinon NEUTRE/G_INUTILE). Verdicts calculés sur les
ratios test-set poolés, séparément FULL et HIDDEN.

- **ENCODING_ARTIFACT** si (learned-FULL = G_FIDELE ET bilin-FULL = G_FIDELE) MAIS (learned-HIDDEN NON-FIDELE ET
  bilin-HIDDEN NON-FIDELE, median ≥ 0.95) → la fidélité env-grille est un **artefact de ré-encodage** ; le latent
  caché N'EST PAS anticipé. **Corrige EDR 135** (son G_FIDELE env était I/O, pas latent).
- **LATENT_BILINEAR** si `bilin-HIDDEN` = G_FIDELE (median < 0.95) ET `median(bilin-HIDDEN) < median(learned-HIDDEN)`
  → une anticipation latente CACHÉE existe ET le bilinéaire la capte mieux → **la forme état-dépendante est le levier**
  (découverte G4 positive).
- **LATENT_LINEAR** si `learned-HIDDEN` = G_FIDELE ET `bilin-HIDDEN` ne bat pas (`median(bilin-HIDDEN) ≥
  median(learned-HIDDEN)`) → anticipation cachée réelle mais le linéaire suffit (la forme n'est pas le levier).
- **PARTIAL** sinon.

## 7. Interprétation (les issues)

- **ENCODING_ARTIFACT** (prédiction opus la plus probable) : le « g anticipe » d'EDR 135 sur env-grille était un
  ré-encodage de position, pas une anticipation de conséquences latentes → **le fil G4 « forme/fidélité de g » n'a
  toujours pas de levier réel** ; converge avec l'arc substrat (le latent caché ~5 effectifs ne porte pas de dynamique
  prédictible état-dépendante). Résultat de correction, honnête.
- **LATENT_BILINEAR** : le seul cas « découverte » — embarquer un g bilinéaire. (Peu probable au vu du latent pauvre.)
- **LATENT_LINEAR** : anticipation cachée réelle mais linéaire suffit → la forme n'est pas le verrou (le modèle
  actuel, linéaire, la capterait déjà).

## 8. Caveats (à graver)

- **(a) [C1 opus] Correction de prémisse** : le linéaire est FIDELE sur env-grille (pas neutre) ; le neutre est le
  synthétique. Le cadrage « craquer le neutre » est abandonné (§0).
- **(b) [C2/Q5 opus] Artefact de décalage d'encodage** : sur les ENTRÉES, `pos` est un one-hot dont la transition est
  un shift déterministe par action → une fidélité FULL peut être 100 % ce shift. **C'est précisément pourquoi le
  contrôle HIDDEN est décisif** ; l'interprétation ne repose QUE sur le verdict HIDDEN.
- **(c) Fit offline = oracle optimiste** (borne haute) : un HIDDEN non-fidèle même en oracle de fit est un signal
  FORT (le latent caché n'est pas prédictible état-dépendant).
- **(d) Sorties incluses dans le masque exclu** : `[N−O, N)` = moteurs, potentiellement aussi structurés ; on
  restreint aux CACHÉS purs `[I, N−O)`. **(e) Substrat synthétique non inclus** (I2 opus) : le régime où le linéaire
  est vraiment neutre ; différé au backlog (le contrôle HIDDEN sur env-grille tranche déjà l'artefact). **(f)** float64
  (fit) vs float32 (135) : divergence numérique mineure. Hérite des caveats d'EDR 135.

## 9. Périmètre / tooling additif

- **Modifié (dans le chantier, branche non mergée)** : `tools/g_bilinear_probe.py` — ajout d'un masque de nœuds au
  calcul de ratio + verdict de décomposition + rework de `main`. **Ne modifie NI** `tools/g_fidelity_probe.py` (mergé
  EDR-135) **NI** `src/` (import read-only) ni le substrat torch (fil //).
- **Test** : `tests/sandbox/test_g_bilinear_probe.py` (étendu : masque + verdict décomposition + smoke).
- **Prints ASCII-only** (cp1252) ; accents seulement en docstrings. **Déterminisme** : numpy pur pour le fit ; rollout
  seedé ; **2 passes byte-identiques**.

## 10. Interfaces produites (delta vs code existant)

- Conservées (Task 1/2 existantes) : `_split_temporal`, `_fit_bilinear`, `_fit_linear_offline`,
  `_collect_transitions_env`.
- **Modifiée** : `_ratios_for_predictor(test, predictor_fn, idx=None, base_thresh=1e-4)` — `idx=None` → dims pleines ;
  `idx` (array d'indices) → ratio restreint à ces dims.
- **Nouvelle** : `_hidden_idx(N, n_in, n_out) -> np.ndarray` (= `arange(n_in, N - n_out)`).
- **Remplacée** : `_verdict_bilinear` → `_verdict_decomposition(learned_full, bilin_full, learned_hidden,
  bilin_hidden) -> str` (§6, gelé).
- **Reworkée** : `main_bilinear_check(...)` calcule les 4 jeux de ratios (learned/bilin × full/hidden) et le verdict
  de décomposition ; retour `{verdict, med_learned_full, med_bilin_full, med_learned_hidden, med_bilin_hidden, n}`.

## 11. Numérotation

**EDR 193** — bloc **190+**. Re-examen isolé d'EDR 135 (G4/anticipation).
