# Revue adversariale n° 1 de `2026-09-16-harness-contracts-design.md` — à sondes propres, lecture seule

*2026-09-16, session parallèle. Aucun fichier de `tools/harness/` ni de la spec n'est modifié : ce document est une
liste de trouvailles, chacune avec la SONDE qui l'a produite (rejouable) et une correction proposée. Règle CLAUDE.md :
une revue lance ses propres sondes ; 7/7 revues WARM ont trouvé une erreur réelle.*

## R1 — le contrôle de SPÉCIFICITÉ de la cellule A ne peut pas échouer (classe E1)

**Spec** (§2.1, §2.4) : ablation `permute_distractor_slot` avec `must_bite=False`, attendue `DECOY`, et le contrat (c)
exige `score(oracle, apply(ep)) > 0,9` pour toute ablation non mordante.

**Sonde** : `_make_seq(key, q, "composition", K=6, I=59, n, same_tick=True)` — les colonnes non nulles de l'observation
sont exactement `[0..11]` (slots key et q) ; **les colonnes 12..58 sont toutes nulles**. Permuter les lignes d'un « slot
distracteur » permute des zéros : l'`Episode` ablaté est bit-identique à l'intact. `DECOY` est alors obtenu par
construction, `> 0,9` aussi — le contrôle négatif de la demande est un no-op analytique présenté comme contrôle, la
définition d'E1 (occurrences : WARM, S2-BLIND-CHAMPION).

**Correction proposée** : `CompositionTask.episodes()` remplit un slot distracteur `[2K:3K]` avec un one-hot tiré du
`rng` (distribution conservée, information nulle pour la cible) ; `permute_distractor_slot` permute CE slot. Le contrat
(c) doit en outre vérifier que l'ablation non mordante **change l'observation** (`not np.array_equal(apply(ep).obs, ep.obs)`)
— sinon (c) est vacueux pour toute Task générée dont l'ablation « no-bite » viserait une zone vide, et c'est précisément
le genre de Task qu'un proposeur LLM produira pour passer le contrat.

## R2 — après `Ablation.apply`, qui porte `meta` ? (lacune de spécification)

**Spec** : `meta` = opérandes bruts « lus par ablate/oracle/plafond Bayes, JAMAIS par le Learner » ; (c) exige
`score(oracle, apply(ep)) ∈ [1/K ± 2 se]` pour une ablation mordante ; `apply` rend un NOUVEL Episode.

**Sonde (raisonnement, à confirmer sur le code)** : si `apply` permute `obs` mais laisse `meta.key` d'origine, l'oracle
(qui lit `meta`) répond juste et `score = 1,0` : la clause (c) refuserait TOUTE Task — visible, donc pas silencieux, mais
la spec ne dit pas laquelle des deux conventions est la bonne. Si `apply` réécrit `meta.key` avec la clé permutée et laisse
`target` intact, l'oracle rend `(q + key')%K` contre `(q + key)%K` : juste ssi `key' ≡ key`, soit ≈ 1/K sur un
dérangement — c'est la convention qui fait tenir (c).

**Correction proposée** : l'écrire dans le contrat — `apply` rend un Episode dont `meta` décrit l'observation ABLATÉE et
dont `target` est celui de l'observation INTACTE ; ajouter au contrat (d) `apply(ep).target is ep.target` (même cible) et
`apply(ep).meta != ep.meta` pour une ablation mordante.

## R3 — la bande de bruit de (i) dépend du NIVEAU, et à la chance elle est large (chiffré)

**Spec** (§2.3 étape 5) : « ≈ ±2 % attendus à n_eval = 640, à MESURER ».

**Sonde** : deux estimations indépendantes d'une même proportion p sur 640 tirages ; 2 se du ratio ≈
2·√(2p(1−p)/640)/p → **±3,1 % à p = 0,93 ; ±12,4 % à 0,45 ; ±18,4 % à 0,27 ; ±24,7 % à 0,17**. Le « ±2 % » ne vaut que
près de 1. Conséquence : sur le bras D (plain, 0,271) et sur tout learner faible, une ablation à ratio 1,5 est encore
DANS la bande — `DEMAND_WITHIN_NOISE` sera la lecture fréquente de (i) sur les variantes « sans pièce », et c'est
correct, mais la règle scellée doit le prévoir (le seuil 1,5 est-il hors bande à p = 0,27 ? 1,5 > 1 + 0,184 : oui, de
peu). La spec le mesure déjà par seed ; il manque la phrase « la bande est publiée PAR BRAS, pas une seule fois ».

**Correction proposée** : `noise_floor` par bras (A, A0, D…) dans le JSON ; le seuil 1,5 de (i)/(iii) confronté à la
bande DU BRAS comparé.

## R4 — vérifié, rien à corriger : la référence lr = 0 de la cellule A

**Spec** : « référence lr=0 ≈ 0,167 (à mesurer) ». **Sonde** : `_train_eval_one(bilinear=True, episodes=0, same_tick=True,
K=6)` sur 4 seeds → 0,148 / 0,180 / 0,161 / 0,161, médiane **0,161** ≈ 1/K. (Le plafond « non entraîné » de 0,203 mesuré
par `retain_compose_diagnostic_probe` est un autre dispositif — ne pas l'importer, la spec ne le fait pas.) La barre de
(ii) vaudra ≈ 0,21-0,23 ; le plain à 0,271 la franchit → `PIECE_PARTIAL` en (iii), exactement ce que la spec annonce.

## R5 — `PRIOR_SOLVES` tel qu'écrit ne peut jamais se déclencher (classe E4)

**Spec** (§2.3 étape 6 (ii)) : « barre = référence + 0,05 ; PRIOR_SOLVES si référence > barre ». Avec barre définie
comme référence + 0,05, `référence > référence + 0,05` est impossible : la branche est morte — une vérification vide, la
définition d'E4. Le tabular `oracle_init` (§2.1) est censé rendre PRIOR_SOLVES : il ne le pourra pas.

**Correction proposée** : `PRIOR_SOLVES` ssi `reference_last > incapable_ceiling.value + 2 se` (la référence à
apprentissage coupé dépasse ce que la forme atteint sans apprendre : contamination, ou tâche triviale) — et si
`incapable_ceiling` est `None`, ssi `reference_last > 1/K + 0,15` avec le statut `UNVALIDATED` publié. Ajouter le cas
au test de `harness_verdict_lecture` (db factice avec référence haute → PRIOR_SOLVES).

## R6 — vérifié : la cellule A rend PARTIAL et la spec le dit

Le plain apprend un peu à 300 épisodes (0,271 contre ≈ 0,16 non entraîné) : la variante « sans bilinéaire » ne retombe pas
à la référence → `PIECE_PARTIAL`, annoncé dans la table §2.4 comme « le résultat honnête ». Rien à corriger ; noter que la
nécessité d'ACQUISITION se lit alors sur la PENTE (D/2 → D) autant que sur le niveau — la spec publie `saturation`, c'est
suffisant.

## Ce que cette revue ne couvre pas

Le code de `tools/harness/` (non lu : il est en cours d'écriture dans l'autre session) ; les contrats L0-L7 du Learner
sur un cas réel ; le sandbox (`validate_code`) — à revoir quand un premier module généré existera.

## Addendum (07:00) — lu contre le plan `plans/2026-09-16-harness-r1-weeks-1-3.md` (non versionné, lecture seule)

* **R1 est CODÉ tel quel dans le plan** (Task 3, `CompositionTask._permute_distractor`) : le slot `[2K:3K]` est permuté
  avec le commentaire *« le slot distracteur est vide : rien n'est détruit »* — l'ablation non mordante est un no-op
  par construction, et le test (c) « > 0,9 » passera sans rien mesurer. À corriger AVANT la Task 3 : remplir le slot
  (one-hot tiré du `rng`, indépendant de la cible) et exiger dans `assert_task_contract` que l'obs ablatée diffère de
  l'intacte.
* **R2 est réglé par le plan** : « `meta` porte les opérandes OBSERVABLES ; sous ablation `meta` reflète ce qui reste,
  `target` porte la VÉRITÉ » ; `_permute_key` reconstruit avec la clé permutée et `target=ep.target`.
* **R5 est réglé par l'amendement 5** : `PRIOR_SOLVES` = référence médiane > `prior_max` (0,5), composé dans
  `harness_verdict_lecture` avant `learner_verdict` — plus la tautologie « référence > référence + 0,05 ».
* **R3** : `measure_noise_floor` rend min/max des ratios appariés (test `test_noise_floor_band_is_min_max_of_paired_ratios`)
  — reste à vérifier qu'elle est mesurée PAR BRAS (A, D) et non une fois sur A seulement.
