# Design — WARM-001 / WARM-002 : deux optimiseurs contre le verrou crédit in-world

Date : 2026-07-18
Statut : design approuvé (structure A + évolution W-only)
Records visés : EDR-WARM-001 (BPTT-imitation), EDR-WARM-002 (évolution in-world), `gate: G0`, `adopts: [REF-DEMAND-MARKER]`

## Contexte et question

S2-009 a RÉALISÉ la recette de demande cognitive in-world : dans le monde stoneage `cognitive_demand`,
un oracle codé-à-la-main (lecteur du signal per-agent bit_a/bit_b → direction nourricière) survit ~200
ticks, alors que l'ablation-perception within-subject l'effondre au plancher ~7 (ratio 21×). La sonde
crédit intra-vie (REINFORCE à froid, `run_credit_probe`) reste PLATE au plancher : **le monde est résolu,
le crédit ne l'apprend pas à froid.** Le bilan warm-start (mémoire `within-subject-demand-marker`) a montré
que le behavioral cloning single-step échoue à transférer (4 variantes, cause = shift de distribution).

Il reste **deux vrais leviers non-essayés**, chacun un OPTIMISEUR différent du gradient-REINFORCE froid :

1. **WARM-001 — Imitation récurrente par BPTT** : matcher le forward RÉCURRENT du monde (pas `_step`
   isolé comme le BC échoué), sur la distribution d'obs RÉELLE (59-dim), via rétropropagation à travers
   le temps. Teste : le crédit gradient échoue-t-il à cause du chemin de crédit récurrent absent, ou plus
   profondément ?
2. **WARM-002 — Évolution in-world** : hill-climb sur `genome.W` pour la survie = l'optimiseur que le SIM
   AGAGI utilise (mutation + sélection), appliqué au monde `cognitive_demand`. Teste : un optimiseur
   NON-gradient, sur le MÊME espace de recherche (W seul), franchit-il là où le gradient échoue ?

**Cadrage décisif** : REINFORCE et BPTT-return n'optimisent que `W`. Pour que l'évolution soit une
comparaison propre — *même substrat, même espace de recherche, seul l'optimiseur change* — WARM-002
n'optimise QUE `W` (`mutate_weights`, pas add_node/bytecode/organs).
- Évolution RÉUSSIT là où gradient échoue (même W-space) → le verrou est le **chemin de crédit gradient**.
- Évolution ÉCHOUE aussi → le verrou est plus profond (gradient de sélection du monde faible même pour
  l'évolution).

## Critère de succès (DÉCISIF) — marqueur + survie

Le verrou est franchi SSI le génome résultant (meilleur évolué / warm-starté) :
1. **PASSE le témoin within-subject** (REF-DEMAND-MARKER) : cloné en **K ≥ 12** agents, run intact vs
   `derange_rows` (obs dérangée par-ligne) sur K ≥ 12 ères → `ablation_verdict` renvoie `PERCEPTION_DEMANDED`
   (ratio ≫ 1, collapse). **ET**
2. **survit ≫ plancher** : survie médiane intacte nettement au-dessus du plancher no-perception (~7),
   idéalement vers l'oracle (~200).

Justification : en `cognitive_demand`, `forage_payoff=0` + revenus corporels gatés (ver/trésor/alignment) →
la SEULE source d'énergie est de suivre le signal. Un survivant DOIT donc être un suiveur-de-signal ; le
marqueur le confirme causalement et exclut le faux-positif between-subject (corps/chance) documenté (S2).

**Garde-fou petit-n (mémoire `power-evaporation-guardrail`)** : pas de verdict POSITIF sous n = 12 ;
préférer `sign_p` / le test de signe intégré à `ablation_verdict`. K ≥ 12 respecte ce plancher.

## Régime monde partagé (invariant des deux expériences)

Reproduit exactement le régime S2-009 validé :
- `Biosphere3D`, `config.cognitive_demand = True`
- `config.base_metabolism = 0.75`, `config.cog_gain = 12.0`, `config.forage_payoff = 0.0`
- `benchmark_mode = True`, `night_enabled = False`, `current_era = 10_000` (comme `run_credit_probe`)
- signal per-agent `_cog_sig` (câblé lignes ~1088-1090 de `world_1_stoneage.py`), lu en obs cols
  bit_a=12 / bit_b=13 (dans la fenêtre `num_inputs=59` → injecté par le forward)
- `correct_dir = 2*(a>0)+(b>0)` (world_1_stoneage.py ~l.827) — 2-bits, 4 directions
- Repères : plancher no-perception ≈ 7 ; oracle intact ≈ 200 (S2-009)
- **Anti-non-repro** (mémoire `biosphere-ambient-memory-nonrepro`) : `memory_retriever.stop()` avant/après
  la boucle sim de chaque épisode (déjà fait dans `run_credit_probe`).

## Architecture (structure A — un outil, deux expériences)

Nouveau fichier `tools/warmstart_evolution_inworld.py` ; méthode BPTT additive dans `backend_torch.py`.
Réutilise sans les modifier : `s2_demand.run_condition`, `s2_demand_ablation.derange_rows`,
`demand_marker.ablation_verdict`, `mutation.mutate_weights`, `world_1_stoneage.Biosphere3D`.

### Composant 1 — `backend_torch.TorchPopulationModel.imitate_episode_bptt` (additif)

```
def imitate_episode_bptt(self, obs_seq, target_moves_seq, truncate_window=None):
    """IMITATION récurrente (BPTT) — distincte de learn_episode_bptt (REINFORCE par le retour).
    Rejoue obs_seq depuis H=0 en RETENANT le graphe récurrent ; perte = cross-entropy des move-logits
    (out[:, :8]) vs l'action-oracle par pas ; backprop unique à travers la fenêtre -> _write_back.
    Matcher le forward RÉCURRENT du monde (pas _step isolé) sur la distribution d'obs RÉELLE.
    truncate_window=W : détache H tous les W pas (stabilité gradient longue fenêtre). ADDITIF :
    ne touche NI forward NI learn NI learn_episode NI learn_episode_bptt."""
```
- Contrat : `obs_seq` = liste de (B, ≥I) ; `target_moves_seq` = liste (par pas) de (B,) int (dir oracle).
- Perte = moyenne sur pas et batch de `F.cross_entropy(move_logits_t, target_moves_t)`.
- Clip de gradient optionnel + `truncate_window` pour la stabilité (fenêtre 200 sinon vanishing/exploding).
- Test sandbox : sur une séquence jouet, la perte décroît et un signal séparable est appris (acc ↑).

### Composant 2 — `run_bptt_imitation_warmstart` (WARM-001, imitation sur trajectoire-enseignant)

**Finding de planification** : le signal `_cog_sig` est re-randomisé CHAQUE tick (world_1_stoneage.py
~l.1088-1091) → la tâche est RÉACTIVE (cible = f(obs du tick courant)), pas de mémorisation. L'oracle
intact survit à 200 avec cohorte PLEINE (S2-009) → sa trajectoire a un **B constant** (aucun mort dans la
fenêtre) → séquence BPTT à B fixe, propre, sans masquage. C'est le test primaire le plus robuste du
« BPTT récurrent installe-t-il un suiveur-de-signal », et il évite le confound d'un DAgger à B variable.

1. **Collecte trajectoire-enseignant** : rollout d'une cohorte oracle (B=12) en `cognitive_demand` via un
   `RecordingOracleBatchModel` (sous-classe de `CognitiveOracleBatchModel`) injecté par
   `env.batch_model_cls` (seam de `run_condition`) — enregistre par tick l'obs (B,59) présentée + le label
   `correct_dir = 2*(bit_a>0)+(bit_b>0)` (B,). Oracle → tous survivent → obs_seq/target_seq à B constant.
2. **Entraînement** : cohorte torch fraîche (`make_population(agents, backend="torch")`) portant un génome
   apprenant ; ~quelques centaines de pas de gradient = N_epochs passages de `imitate_episode_bptt(obs_seq,
   target_moves_seq, truncate_window)` sur la trajectoire collectée → `_write_back`. `truncate_window`
   borne la profondeur BPTT (stabilité ; la tâche réactive n'exige pas le crédit 200-pas).
3. Sortie : génome warm-starté + trace perte/acc d'imitation par epoch.
4. → Verdict commun (marqueur + survie) sur le génome résultant, sous forward **torch**.

Follow-up documenté (non lancé par défaut) : DAgger on-policy sous torch (distribution de l'apprenant) si
le marqueur est LIMITE — l'étiquette oracle étant f(obs), elle est disponible sur toute distribution.

### Composant 3 — `run_inworld_evolution` (WARM-002, hill-climb W-only)

1. Population de `pop=24` `MambaAgent` (W aléatoire), même régime `cognitive_demand`.
2. Génération = UN épisode : tous les agents vivent dans le même monde, fitness = âge à la mort/fin.
   (1 épisode évalue toute la population — le signal étant per-agent, la population partage un rollout.)
3. Sélection top-k (ex. `survival_rate=0.25`) → refill : cloner un survivant + `mutate_weights` (W-only,
   pas `apply_mutations` → isole l'espace W, comparable au gradient). Élitisme sur le meilleur.
4. ~40-60 générations. Trace : survie médiane du top-k et max par génération.
5. → Verdict commun sur le meilleur génome final.
6. Variante de robustesse (optionnelle, notée non-lancée par défaut) : `apply_mutations` complet
   (topologie) comme contrôle « et si W seul ne suffit pas ».

### Composant 4 — `verdict_demand_marker(genome, backend, seed, K=12, ...)` (partagé)

Prend un génome, le clone en K ≥ 12 `MambaAgent`, exécute intact vs `derange_rows`, applique
`ablation_verdict`. Renvoie `{ratio, verdict, n, survie_intacte_médiane}`.
PASS = `verdict == PERCEPTION_DEMANDED` ET survie_intacte ≫ plancher.

**Consistance du forward (correctness, anti-confound)** : le génome DOIT être évalué sous le MÊME
forward que celui qui l'a produit — sinon un W appris sous la dynamique LTC torch, rejoué sous le
forward mamba (ou l'inverse), donnerait un verdict trompeur. Donc `backend="torch"` pour WARM-001
(dynamique LTC différentiable qui a servi à l'imitation), `backend="mamba"/"legacy"` pour WARM-002
(le forward que la sélection a réellement optimisé via la survie in-world). L'ablation `derange_rows`
et le régime monde sont identiques dans les deux cas ; seul le forward suit son expérience.
Sanity : l'oracle (S2-009) sert de contrôle POSITIF de la mécanique de verdict (doit rester
`PERCEPTION_DEMANDED`), un génome aléatoire de contrôle NÉGATIF (`NEUTRAL`).

### `main()`

Exécute WARM-001 puis WARM-002, imprime pour chacun : trace d'apprentissage + verdict marqueur+survie,
et une ligne de synthèse comparant les deux optimiseurs au REINFORCE froid (plat) et à l'oracle (200).

## Flux de données

```
WARM-001 : cohorte torch --rollout--> obs_seq --oracle label--> target_moves
           --imitate_episode_bptt(BPTT)--> genome.W --_write_back--> genome
           --verdict_demand_marker--> {ratio, survie} --> PASS/FAIL
WARM-002 : pop MambaAgent --episode--> ages(fitness) --select+mutate_weights--> pop'
           (×G générations) --> best genome --verdict_demand_marker--> PASS/FAIL
```

## Gestion d'erreurs / pièges connus

- torch absent → `imitate_episode_bptt` inaccessible ; WARM-001 skip proprement avec message
  (`requirements-torch.txt`). WARM-002 (numpy pur) reste exécutable.
- BPTT longue fenêtre instable → `truncate_window` + clip de gradient.
- non-repro KuzuDB ambiant → `memory_retriever.stop()` systématique (déjà pattern `run_credit_probe`).
- multiprocess non utilisé ici (mono-processus) → évite les pièges ProcessPool (mémoire dédiée).
- `results/` doit exister si on écrit des traces (créer avant écriture) — piège rencontré en worktree.
- éval acc : batchs de taille B (piège 512-vs-B rencontré au bilan précédent).

## Tests (non-régression + unités)

- `tests/sandbox/test_warmstart_evolution_inworld.py` :
  - `imitate_episode_bptt` : perte décroît, acc ↑ sur tâche jouet séparable ; additivité (forward/learn
    inchangés → un forward de contrôle donne le même résultat qu'avant l'appel).
  - `run_inworld_evolution` : tourne sur mini-budget (pop 6, 3 gén, 30 ticks) sans exception ; renvoie
    une trace croissante ou plate bien formée.
  - `verdict_demand_marker` : sur l'oracle (réf), renvoie `PERCEPTION_DEMANDED` (sanity, réutilise
    S2-009) ; sur un génome aléatoire, NEUTRAL.
- Non-régression : flag monde OFF par défaut (déjà couvert S2-009 3/3 + 10/10) ; `mutate_weights`
  non modifié ; `backend_torch` : suite torch existante toujours verte.

## Portée / limites (à graver dans les EDR)

- cog food = direction-signalée per-agent (proxy fidèle obs→action→énergie), pas une écologie riche.
- Budget modéré : un NÉGATIF sous ce budget = « pas franchi à budget modéré », pas « impossible » ;
  la variante agressive (curriculum létalité + centaines de gén) reste un cran au-dessus si ambigu.
- WARM-001 imite un ORACLE (teacher parfait) : un échec de transfert malgré teacher parfait = résultat
  fort (le problème n'est pas la découverte mais l'installation dans le substrat par gradient récurrent).

Converge : S2-009 (recette in-world), [[warm-start-transversal-law]], [[decisive-substrate-thesis-test]],
[[within-subject-demand-marker]], REF-DEMAND-MARKER.
