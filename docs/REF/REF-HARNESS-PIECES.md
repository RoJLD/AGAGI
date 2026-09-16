---
id: REF-HARNESS-PIECES
type: REF
title: "Registre de pièces du harnais — analogues biologiques, variantes « sans », statuts"
status: active
adopt_for: [ADR-004, ADR-005]
---

## Énoncé

Le registre publié par `src/seed_ai/harness_pieces.py::PIECES` (13 lignes) — jamais recopié : ce fichier
est la vue lisible des MÊMES données, et `tests/sandbox/test_harness_pieces.py` vérifie que chaque nom et
chaque statut publiés ici existent dans le code, pour que doc et registre ne puissent pas diverger.

Une **Pièce** est une composante d'une architecture (`Learner`) avec sa variante « sans » (`without`,
kwargs de `build()`, DOIT changer au moins un logit après apprentissage — sinon `VACUOUS_PIECE`, clause
(L4) de `assert_learner_contract`), son analogue biologique noté en solidité, sa prédiction de lésion
(maillon `inferred`, jamais `measured` — aucun sujet organique n'est mesuré ici), et ce qui est déjà
mesuré dans le dépôt à son sujet.

## Table

| pièce | forme artificielle | analogue biologique (solidité) | variante « sans » | capacité servie | déjà mesuré dans le dépôt | statut |
|---|---|---|---|---|---|---|
| `bilinear` | `((H·U)⊙(H·V))·W_bl` rang 16 dans `_step` (`backend_torch.py:111-131`), flag `BILINEAR` | intégration dendritique multiplicative / coïncidence NMDA (**moyenne** ; rang et U/V sans correspondant). Lésion prédite : blocage des spikes NMDA abolit les conjonctions, pas la détection de traits | `without={"bilinear": False}` ; sham linéaire apparié `matched_sham={"bilinear_sham": True}` (`TorchPopulationModel.BILINEAR_SHAM`, `(H·U + H·V)·W_bl`, mêmes tenseurs, même init, comptage de paramètres asserté égal 37 840) | composition (q+key)%K | plain 0,271 vs bilinéaire 0,932, 0/144, n=12, 300 ép. (`results/bilinear_composition.json`) ; forme close plain 34/36 = 0,944 > 0,932 (`plain_substrate_ceiling.py:155`) : nécessité d'ACQUISITION à dose, pas de représentation. **P4.12** (`results/bilinear_sham_r1.json`, `docs/preregistrations/BILINEAR-SHAM-R1.json`) : plain 0,270 / sham 0,315 / bilinéaire 0,934 à lr 0,02 ; 0,180 / 0,189 / 0,413 à 0,002 ; lecture scellée **SHAM_PARTIEL (8/12)** — le sham est AFFINE ; la nécessité de la MULTIPLICATION n'est PAS ÉTABLIE par la lecture scellée | **R1** |
| `recurrent_state` | H porté : `H' = (1−δ)H + δ·tanh(H·W_off)`, δ = σ(diag W) (`:119-132`) | activité persistante préfrontale, mémoire de travail (**solide** fonctionnellement, aucune au mécanisme). Lésion : dlPFC abolit le rappel différé, pas l'immédiat | `without={"feedforward": True}` (H=0 à chaque pas) ; ablation d'éval `state_reset` | rétention D ≥ 1 | LOCK-002 : 0,814/0,168 = 4,85x, n=12, SURGICAL fuite 0,028 (REINFORCE D=2, 14 400 ép.) ; 2-pas supervisé : 0,923 à lr 0,002/600 ép. (`retain_compose_lr_replication.json`) | **R1** |
| `bptt_credit` | graphe retenu à travers les pas (`imitate_episode_bptt :263`, `learn_episode_bptt truncate=False :230`) | traces d'éligibilité / synaptic tagging (**moyenne** ; BPTT lui-même : aucune) | `without={"truncate": True}` (H détaché à chaque pas) | écriture apprise dans la mémoire (verrou LOCK-001) | RETAIN-COMPOSE-LR : 0,173 → 0,923 au seul lr (E19) ; nécessité NON établie | **R2** |
| `td_critic` | value head nœud 28, δ = r + γV(s') − V(s) (`:174-229`) | erreur de prédiction de récompense dopaminergique (**solide**, Schultz). Lésion : VTA/SNc abolit l'apprentissage instrumental, pas l'exécution | `without={"td_enabled": False}` | crédit temporel dense | CALIB-LEARNER : td_off -0,046 (2/12) ; P4.9 en cours | **attend** (Task à récompense scalaire) |
| `condition_gate` | readout de H biaisant le logit cible (`:48-53, 134-149`) | gating go/no-go ganglions de la base (**moyenne**) | `without={"CONDITION_GATE": False}` (bit-identique) | binding means→ends | EDR-129/136/148 : suffisant en proxy ; nécessité à dose appariée jamais mesurée | **attend** |
| `warm_start_prior` | init depuis bassin DAgger / HoF vs `0.1·randn` (`:113-115`) | pré-câblage génomique, périodes critiques (**solide** conceptuellement, Zador 2019) | `without={"init": "random"}` même seed ; « warm gelé » = référence | bootstrap ; rétention du bassin | loi warm-start (6 fils) ; S2-CREDIT-RETENTION : le crédit érode 36 → 8, 12/12 | **attend** |
| `neuromod_plasticity` | règle à 3 facteurs ΔW = η·m(t)·pre⊗post, m(t) readout appris de H (Miconi 2018) — à écrire (hypothèse de robla) | plasticité hebbienne gatée par DA/ACh (**solide** comme phénomène, **moyenne** comme règle). Lésion : nucleus basalis → déficit sous NOUVEAUTÉ, ancien préservé | `without={"modulator": "constant"}` (m≡1, teste la MODULATION) puis `plasticity=0` (teste la PLASTICITÉ) ; contrôle m(t) permuté dans le temps | rétention sous changement de distribution (split `"shift"`) | absent : hebbien legacy numpy = no-op sous torch (ADR-003) ; entre avec son billet : une Task à shift que Hebb pur échoue et que 3-facteurs réussit | **attend** |
| `frozen_llm_backbone` | LLM gelé + adaptateur apprenant (tête / LoRA) | cortex mature + plasticité locale, CLS (**faible**) | `without={"adapter": False, "backbone": "random_features"}` (zéro-shot) ; référence = « LLM sans module » | a priori symbolique | absent : rien n'existe encore ; seul `llm_fn(str)->str` existe | **attend** (clé par seed, PRIOR_SOLVES obligatoires ; non CPU-pur) |
| `state_noise_regulator` | bruit sur l'état récurrent porté (organe dreaming) | homéostasie du sommeil (**faible** ; DREAM-007 : pas du rejeu) | `without={"organ": "off"}` | régulation de bruit d'état (+77% survie) | arc DREAM-001→007, in-world seulement | **hors_v1** |
| `curiosity_intrinsic` | surprise du modèle du monde → bonus | dopamine de nouveauté (**moyenne**) | `without={"intrinsic_scale": 0}` | exploration | MORTE sous torch (surprise jamais écrite, P4.8) — cas gelé de (L3) DEAD_LEARNER | **hors_registre** |
| `targeted_variation` | `add_connection` biaisé entrée→sortie | biais développementaux de connectivité (**faible**) | `without={"variation": "uniform"}` (EVO-010 : 254 117 réveils → 0) | découverte d'arête | EVO-009 : 1/12 → 12/12, p = 9,6e-6 ; dose en `generations` | **attend** (famille évoluée : `reference()` = variation coupée) |
| `eligibility_trace_credit` | trace d'éligibilité sur W dans `TorchPopulationModel._td_update` (drapeau de classe `CREDIT_TRACE_LAMBDA`, défaut 0.0 = chemin d'origine bit-identique ; P4.11) | traces d'éligibilité synaptiques / synaptic tagging (**moyenne**, Gerstner 2018). Lésion : blocage du tagging synaptique abolit l'association à délai, pas l'immédiate (maillon inferred) | `without={"trace_lambda": 0.0}` | crédit temporel par pas à délai D≥1 | attend : réponse connue NÉGATIVE ÉTABLIE — TD(0) par pas n'apprend pas la composition différée (td0 0,190, 1/12 au-dessus de réf+0,05 ; réf lr=0 0,163), inerte aux trois pas (2,0 / 4,0 / 8,0), avec ses deux contrôles (chemin td0_d0 0,503, substrat bptt 0,807) ; réponse POSITIVE observée à UN SEUL point de fonctionnement (lr 4,0, lambda 0,9 : 0,253 > td0 sur 12/12, R0) et NON INVARIANTE (R1 : lr 2,0 → 0/12 ; lambda 0,5 → 0/12) — classe E19 ; billet PAYABLE par un balayage lr x lambda SCELLÉ (EDR-TD-STEP-PILOT-R0 avec bandeau, R1). Réserves : effet faible, un substrat, un délai, traces remises à zéro par épisode, aucune extrapolation in-world | **attend** (entre en R2 avec E19) |
| `time_constant_modulation` | facteur par nœud sur delta_j = sigmoid(W_jj) dans `_step` — à écrire | neuromodulation de la constante de temps ACh/NE (**faible**) | `without={"tau_modulation": False}` | rétention sous changement de distribution | absent : P4.13 (a), `results/delta_distribution_hof.json` — la diagonale de W est EXACTEMENT nulle sur 161/172 nœuds des 30 génomes HoF (delta = 0,5 GELÉ) ; agent frais 172/172 non nulles ; l'évolution n'a AUCUN écrivain sur tau (sparsification + mutate_weights ne réveille pas un zéro, EVO-009). La pièce n'a de sens que sur un substrat où delta est ÉCRIT (connectome torch frais) ; sur un champion évolué un facteur sur delta est un bouton GLOBAL. Billet à payer : Task à split shift | **attend** |

## Statuts

**R1** = porte la première cellule de contrôle positif du harnais (spec §2.4 : `HARNESS-R1`, trois
cellules). **R2** = pièce candidate aux semaines 6-8 (nécessité de `bptt_credit` sur LOCK-001, encore
NON établie à ce jour). **attend** = la pièce n'entre dans une cellule de NÉCESSITÉ (condition (iii))
qu'avec son billet d'entrée payé — une Task à réponse connue que la variante « sans » échoue et que la
pièce réussit (règle E2). **hors_v1** = mécanisme mesuré et vivant in-world, mais hors du périmètre
CPU-pur du harnais v1 (pas de monde, pas de bail `kuzu`). **hors_registre** = chemin de crédit mesuré
INERTE sous le backend courant (cas gelé de la clause (L3) DEAD_LEARNER d'`assert_learner_contract`) —
il n'entre dans aucune cellule tant que ce statut n'a pas changé.

## Règles d'entrée

- **Billet d'entrée à deux issues (E2)** : une pièce marquée `attend` n'entre en cellule de nécessité
  qu'avec une Task à réponse connue où LES DEUX issues sont productibles — la variante « sans » la pièce
  ÉCHOUE, et une forme portant la pièce (ou son verrou proche, cf. `eligibility_trace_credit` /
  `bptt_credit`) RÉUSSIT. Un billet qui ne peut réussir que d'un côté ne prouve rien (classe E2 : un bras
  qui ne peut pas réussir, ou un contrôle qui ne peut pas échouer).
- **« Pièce du puzzle » ssi nécessaire dans ≥ 2 familles.** Une pièce nécessaire dans une seule
  architecture (`connectome_torch` par exemple) est un artefact de RÉGIME, pas une brique candidate du
  puzzle biologique → artificiel (spec §2.6) : la candidature exige une réplication de la nécessité dans
  une seconde famille (p. ex. `gru_bptt`).
- **La nécessité s'énonce « à l'ACQUISITION à dose D, sweep {…} », jamais nue.** Un verdict `NECESSARY`
  décrit une architecture, une dose et un couple de pas de sweep précis (garde E19,
  `assert_verdict_invariant_to_optimizer`) — jamais une propriété intrinsèque de la pièce hors de ce
  contexte.
