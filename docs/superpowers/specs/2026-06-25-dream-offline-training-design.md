# Rêve = entraînement offline (Dyna value-augmentation) — Design

**Date** : 2026-06-25
**Axe roadmap** : NAS §4, Axe 3 (plasticité/organes) — séparation des modes cognitifs.
**Statut** : design validé (brainstorm), prêt pour plan.
**Précédent** : le planificateur depth-1 (`PLAN_BIAS`, biais sur l'action en direct) a été RÉFUTÉ (PLAN_PERD) car il MÉLANGEAIT rêve et pensée — voir `2026-06-25-dreaming-planner-design.md` et mémoire `planner-depth1-refuted`.

## Principe directeur

Garder les modes cognitifs **séparés** :
- **Pensée** (en ligne, couplée au monde) : `forward` récurrent → action, actor-critic TD. INCHANGÉE.
- **Rêve** (hors-ligne, découplé) : utiliser le modèle de transition `g(H,a)→H'` (déjà existant, appris en ligne) pour **entraîner la value head hors-ligne** (Dyna). Le rêve n'agit JAMAIS en direct.

C'est l'inverse du planificateur réfuté : au lieu de biaiser l'action en temps réel (qui sabote une politique réactive qui marche), on améliore le critic hors-ligne. Au pire, un `g` imprécis ajoute du bruit récupérable à l'apprentissage — il ne sabote pas l'action.

## Acquis réutilisés (dans `main`, PR #66)

- `src/agents/planner.py` : `plan_rollout`, `update_transition` (g appris en ligne), `normalize_q`.
- `MambaBatchModel` : `G_batch (B,A,N)` (modèle de transition, round-trip ordre nœud), `H_rec_batch`, value head logit 28, flags de classe gatés.
- `tools/anticipation_bench.py` : banc d'anticipation équitable (réutilisable).
- `predictor_head` (logits extraits mais INUTILISÉS, cf. audit) → candidat pour la reward head.

## Garde-fou méthodologique (discipline projet)

Avant de bâtir la machinerie Dyna sur un `g` rudimentaire (qui vient d'échouer comme biais), **mesurer d'abord si `g` est assez fidèle pour un usage model-based**. Sinon on reconstruit le même échec en plus gros. → **Sonde A en go/no-go.**

## Composants (chacun gaté, défaut OFF, non-régressif)

### A — Sonde de fidélité de `g` (go/no-go, AUCUN changement cœur)
- **But** : `g` prédit-il les transitions latentes mieux qu'une baseline naïve ?
- **Méthode** : sur des transitions RÉELLES collectées en simulation (états `H_rec` successifs + action exécutée), comparer l'erreur `||(H_rec_t + G[a_t]) − H_rec_{t+1}||²` (g) vs `||H_rec_t − H_rec_{t+1}||²` (baseline « pas de changement »). Ratio médian multi-seed.
- **Outil** : `tools/g_fidelity_probe.py` (lance des lignées courtes avec `PLAN_BIAS>0` pour que `g` apprenne, mesure le ratio). Fonctions pures pour le calcul du ratio (testables).
- **Verdict** : `g` doit battre la baseline (ratio < 1, médiane, sign test). **Sinon → STOP** : escalader vers `g` bilinéaire (`H'=H_rec+W_a·H`) AVANT B-E. C'est le gate du projet.

### B — Reward head `r̂(H)`
- **But** : un TD imaginé a besoin d'une récompense imaginée (sans modèle de récompense, la value-TD imaginée dégénère vers 0).
- **Forme** : readout linéaire par agent `r̂ = H · w_r` (petit, init 0), appris EN LIGNE par régression sur la récompense réelle (`r̂(H_t) → reward_t`), même patron que la value head. Réutiliser les logits `predictor_head` (extraits, inutilisés) comme source, OU un vecteur `r_head_batch (B,N)` dédié.
- **Interface** : `update_reward_head(w_r, H_node, reward, lr) -> w_r` (pure) ; lecture `reward_pred(w_r, H) -> r̂`.

### C — Replay buffer per-agent
- **But** : états de départ de l'imagination, gardés près de la distribution d'entraînement de `g`.
- **Forme** : ring buffer par agent des `H_rec` réels récents (taille ≈8), round-trip ordre nœud (comme `G`). `a.dyna_buffer`.

### D — Boucle Dyna offline (value head seule)
- **Quand** : périodiquement (ex. tous les `DYNA_PERIOD` ticks) OU en fin de tick, hors de la sélection d'action.
- **Quoi** : échantillonner `K` états `H_b` du buffer ; pour chaque, choisir une action `a` (argmax politique sur `H_b`, ou échantillon) ; imaginer `H' = H_b + G[a]` ; cible `y = r̂(H_b) + γ·V(H')` ; update TD de la **value head uniquement** vers `y` (gradient sur le bloc de poids de la value head, comme le critic réel). **AUCUN update de politique, AUCUN biais d'action.**
- **Interface** : `dyna_value_update(W_value_block, H_b, target, lr) -> dW` (réutiliser/mirror `compute_policy_gradient` critic).

### E — Gate `PLAN_DYNA` (défaut 0.0 = OFF)
- À OFF : pas de buffer, pas de reward head, pas d'updates imaginés → `forward` et `compute_policy_gradient` **bit-identiques** au comportement actuel.
- Flags de classe : `MambaBatchModel.PLAN_DYNA = 0.0`, `DYNA_K = 4`, `DYNA_PERIOD = 8`, `DYNA_LR = 0.02`.

**Séparation des modes (clé) : D ne touche QUE la value head, jamais l'action en temps réel.** C'est la différence avec le planificateur réfuté.

## Validation (par étapes, chacune gate la suivante)

1. **Sonde A d'abord** (décisive, peu coûteuse). `g` ne bat pas la baseline → STOP, escalader `g` bilinéaire.
2. **`g` fidèle → bench Dyna** : étendre `tools/anticipation_bench.py` (ou un comparateur dédié) — bras Dyna (`PLAN_DYNA>0`) vs réactif (0.0), apparié multi-seed + sign test. La value head mieux entraînée → meilleur comportement ?
3. **Bench positif → ablation stoneage** powered, gatée OFF, verdict compétence/survie (`Harness.save`, sweet-spot 0.25/3).
4. Diagnostic par-item ; `memory_retriever.stop()` avant boucle.

## Tests / non-régression

- **Unitaires** : `update_reward_head` réduit l'erreur de régression (synthétique) ; `dyna_value_update` pousse la value head vers la cible imaginée (jouet) ; ring buffer (ordre, capacité) ; sonde A calcule le bon ratio (jouet).
- **Non-régression** : `PLAN_DYNA=0.0` → `forward` + `compute_policy_gradient` bit-identiques (test déterministe + suite mamba existante).

## Risques

1. **`g` trop faible** (probable vu le depth-1) → la sonde A le tranche AVANT le build → escalade `g` bilinéaire. C'est le but du de-risquage.
2. **Reward head imprécise** → cibles imaginées bruitées → updates Dyna nuisibles. Mitigation : value-head seule (pas la politique), `DYNA_LR` faible, gate.
3. **Off-distribution** : imaginer depuis le buffer de vécu réel limite la dérive.

## Backlog différé → roadmap NAS §4 (consigné avec ce spec)

- **Dreamer complet** : actor-critic en imagination (entraîner aussi la politique) — après fiabilisation de `g`.
- **Dyna+ / organe méditation-consolidation** : mixer le replay du vécu RÉEL (consolidation) avec l'imagination — fusionne deux directions.
- **depth-k planificateur** + **`g` bilinéaire** (aussi cible d'escalade si sonde A échoue).
- **Outil EDR multi-lentilles** : interprétations anthropo/étho/bio/neuro en fin de run (cycle d'outillage séparé).

## Hors-périmètre

- Modifier la politique via le rêve (réservé au Dreamer complet, différé).
- Biais d'action en direct (réfuté, abandonné).
