# Dreaming → Planificateur (latent Dreamer-lite) — Design

**Date** : 2026-06-25
**Axe roadmap** : NAS §4, Axe 3 (plasticité/organes) — activation d'infra stubbée.
**Statut** : design validé (brainstorm), prêt pour plan d'implémentation.

## Objectif

Remplacer le mécanisme « dreaming » actuel — une **escalade aléatoire en espace latent** jugée
*nuisible* (EDR 095) — par une **anticipation model-based conditionnée par l'action** qui *oriente* la
politique actor-critic sans la remplacer. Tout est **gaté, défaut OFF (non-régressif)**.

## Contexte (état réel du code)

- **Dreaming actuel** (`src/agents/mamba_agent.py`, bloc ~547-577) : perturbe `H` avec du bruit gaussien
  (0.05), refait un pas de récurrence (sans nouvelle obs), score par le logit de valeur (28), garde le
  meilleur `H` sur K tirages, l'injecte. Pas d'action, pas de modèle, pas de prédiction → coûte sans anticiper.
- **« World Model »** (`src/agents/world_model.py`) : estimateur de nouveauté façon **RND**
  (`pred = obs@Wp ≈ projection_aléatoire_fixe(obs')`), **NON conditionné par l'action**, ne reconstruit pas
  l'obs (8 dims pour la surprise). → **inutilisable tel quel pour planifier**.
- **Boucle vivante** : récurrence Liquid-Mamba → logits politique (0-7) + value (28) ; Actor-Critic TD(0)
  en ligne (`compute_policy_gradient`) ; `Wp` appris en ligne par agent. Espace d'actions = 8 logits discrets.

**Conséquence** : planifier exige une pièce neuve = un modèle de transition **conditionné par l'action**
`g(H, a) → H'`. Bonne nouvelle : 8 actions → évaluer chacune est trivial ; `g` peut démarrer linéaire,
par agent, appris en ligne (comme `Wp`).

## Décisions de conception (validées)

1. **Substrat de plan** : latent Dreamer-lite — dérouler dans l'espace caché `H`, scoré par la `value_head` existante.
2. **Apprentissage de `g`** : **en ligne par agent** (gradient sur transitions vécues), init 0, `lr_g`/évolution règlent.
3. **Intégration** : **biais** sur les logits de politique (pas override) — la politique TD reste la vérité, crédit sur l'action exécutée.
4. **Validation** : **banc d'anticipation dédié** (prouve le mécanisme en isolation) **puis** ablation gatée powered en stoneage.

## Architecture

Insérée dans `MambaBatchModel.forward`, **en remplacement du bloc dreaming** quand le planificateur est actif :

```
H_rec = recurrence(H)                          # pas normal (déjà calculé), sans action
pour a in 0..A-1 (A=8) :
    H'_a       = H_rec + G[a]                   # g : transition conditionnée par l'action
    Q_plan[a]  = value_at(H'_a)                 # logit de valeur (28) lu sur H'_a
logits'(a) = logits(a) + β · normalise(Q_plan)[a]   # BIAIS sur les logits de politique
action ~ softmax(logits')                       # action exécutée -> TD inchangé
```

## Composants (responsabilité unique, testables isolément)

### C1 — `g` : transition latente conditionnée par l'action
- **Forme (1er barreau)** : `H'_a = H_rec + G[a]`, où `G` est une matrice **par agent** de forme `(A, N)`
  (≈ 8×172). `G[a]` = effet latent appris de l'action `a`.
- **État** : `G_batch` de forme `(B, A, N)`, persisté en round-trip comme `Wp_batch`/`ntm_memory`.
- **Init** : zéros → `H'_a == H_rec` → **aucun effet au départ** (non-régressif, pas de plan sur modèle nul).
- **Interface** : `plan_rollout(H_rec, G_batch, value_idx) -> Q_plan (B, A)` (pure, testable).

### C2 — Apprentissage en ligne de `g`
- À chaque tick on dispose de `H_rec_t` (latent post-récurrence avant action), `a_t` (action exécutée),
  `H_rec_{t+1}` (latent du tick suivant). Cible = `(H_rec_{t+1} − H_rec_t)`.
- MAJ : `G[a_t] += lr_g · (cible − G[a_t])` (par agent). Mirroir conceptuel de `WorldModel.observe_batch`.
- **Interface** : `update_transition(G_batch, prev_H_rec, action, next_H_rec, lr_g) -> G_batch` (pure).
- `lr_g` : constante de classe au départ (ex. 0.05), évolvable plus tard (gène).

### C3 — Intégration biais
- `logits'(a) = logits(a) + β · z(Q_plan)[a]`, `z` = normalisation (centrage/échelle robuste) pour que
  `β` ait un sens stable indépendamment de l'échelle de la value head.
- `β` : **constante de classe `PLAN_BIAS` (défaut 0.0 = OFF)**, puis gène évolvable (`organ`/gène dédié).
- L'action échantillonnée reste enregistrée pour le crédit TD → **actor-critic inchangé**.

### C4 — Gate & coût
- Actif ssi `PLAN_BIAS > 0` **et** `organ_genes[0]` (réutilise le gène organe du dreaming).
- **Coût = calcul réel** (8 évals latentes), **PAS** le drain forfaitaire +0.5 qui a tué le dreaming (EDR 095).
- Le bloc dreaming aléatoire actuel est **désactivé quand le planificateur est actif** (mutuellement exclusifs).

### C5 — Garde-fou off-distribution
- La value head est entraînée (TD) sur des latents *réels* ; scorer des `H'_a` *imaginés* peut être hors-distribution.
- Mitigations : profondeur 1 + deltas petits (H'_a proche du réel) ; **biais seulement** (un mauvais score
  ne hijacke pas) ; `β` faible au départ. Métrique à surveiller : corrélation `Q_plan` vs valeur réalisée.

## Banc d'anticipation (validation en isolation)

Env minimal, **déterministe, séparé de stoneage** (pas de `graph_rag` → reproductible, évite la mémoire ambiante).
- **Tâche A — danger télégraphié (profondeur 1)** : un signal dans l'obs annonce un coup au tick suivant ;
  l'agent réactif (β=0) ne relie pas signal→conséquence, le planificateur prédit « rester → valeur basse »
  → s'écarte. Métrique = survie/retour.
- **Tâche B — récompense engagée (profondeur k, v2)** : récompense conditionnée à une séquence d'actions ;
  la réaction gloutonne la rate. **Notée pour v2** (profondeur 1 insuffisante).
- **Outil** : `tools/anticipation_bench.py` (env jouet + runner). Verdict = planificateur ON bat OFF **et** bat
  un baseline réactif, seeds appariés + test de signe.

## Protocole de mesure (go/no-go)

1. **Banc d'abord** (décisif, peu coûteux) : ON vs OFF vs réactif. *Échec ici = mécanisme cassé → stop.*
2. **Stoneage ensuite** : ablation gatée (`PLAN_BIAS=0` défaut), powered multi-seed apparié, sweet-spot
   énergie (`base_metabolism=0.25`, `forage_payoff=3.0`), verdict compétence/survie via `Harness.save` + sign test.
3. **Diagnostic par-item** (le planificateur seul ; pas mélangé à d'autres activations). `memory_retriever.stop()`
   avant boucle (reproductibilité).
4. **Outil** : `tools/planner_compare.py` (sur le modèle de `metabolic_cost_sweep.py` / `map_elites_compare.py`).

## Tests / non-régression

- **Unitaires** :
  - C2 : `update_transition` réduit l'erreur de prédiction latente 1-pas sur transitions synthétiques.
  - C1 : `plan_rollout` choisit la meilleure action sur un jouet où une action mène à une valeur plus haute.
  - C3 : `β=0` → logits **bit-identiques** (non-régression).
  - Gate : `PLAN_BIAS=0` (défaut) → sortie `forward` **identique au comportement courant**.
- **Non-régression** : le chemin par défaut (OFF) reproduit exactement le forward actuel.

## Risques

1. **Sélection** (piège récurrent) : si stoneage ne récompense pas l'anticipation, verdict neutre — d'où le
   **banc dédié** qui découple « le plan marche » de « le monde le récompense ».
2. **Off-distribution value head** (C5) : mitigé par profondeur 1 + biais + β faible.
3. **Coût latent** : 8 évals/tick si actif — borné, gaté, et bien moindre que le drain dreaming.

## Backlog v2 (hors premier barreau)

- Profondeur k (réappliquer `g` sur l'action planifiée, accumuler valeur/récompense prédite).
- `g` bilinéaire state-dépendante : `H'_a = H_rec + W_a·H` (low-rank).
- `lr_g`/`β` évolvables (gènes) ; récompense prédite explicite en plus de la value head.

## Hors-périmètre

- Réparer le répertoire du monde (Axe « monde/sélection ») — traité ailleurs.
- Autres activations (NTM, RAG) — backlog NAS §4, sous-projets séparés.
