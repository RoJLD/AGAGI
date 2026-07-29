# Fil directeur AGI — les 5 portes G0→G4

> Stratégie qui chapeaute SCIENCE/NAS/BACKEND/FRONTEND. Continue (ne remplace pas)
> `../FIL_CONDUCTEUR.md`. État auto-généré : `tools/consolidate_records.py` → `results/records_graph.json`.
> Design : `../superpowers/specs/2026-06-29-Roadmap-AGI-Gates-design.md`.

## Thèse réconciliée
« Le bon est trouvé si le monde l'EXIGE (010/012) ET si l'agent l'APPREND (067) » — les deux se
mesurent en un point : la **généralisation zéro-shot** (`transfer_ratio`, north-star).

## Moteur (ADR-001, ADR-002)
GA (recherche de substrat) + gradient (apprentissage intra-vie) + Baldwin. Évolution topologique active.

## Les 5 portes (bottom-up par dépendance, capacités stratifiées EDR 075)
| Porte | Question | KPI | Outil | Record |
|---|---|---|---|---|
| **G0** | Le monde exige ? | survival_ratio champion/dummy | à créer | SDR-G0 |
| **G1** | Ça généralise ? ★ | transfer_ratio | `tools/curriculum_transfer.py` | SDR-G1 |
| **G2** | Ça compose ? | émergence chaîne non récompensée | à créer | SDR-G2 |
| **G3** | Le langage paye ? | mammoth_kills ON/OFF | `tools/wire_ref_head.py` | SDR-G3 |
| **G4** | Ça anticipe ? | anticipation_bench | `tools/anticipation_bench.py` | SDR-G4 |

> On ne franchit une porte que si la précédente est mesurée (verdict EDR powered).
> Méthode : Commandement 15 (1 variable, powered, valide-ou-revert). Négatifs = livrables.

## État courant : le verrou convergent (2026-07)

Une décennie d'EDR converge sur un même diagnostic, ré-confirmé territoire par territoire : **le substrat
REPRÉSENTE ce qu'il faut, mais ne CONVERTIT pas la représentation en comportement — faute de crédit/signal,
pas de capacité ni d'architecture.** Ce n'est pas une intuition : c'est un faisceau de négatifs contrôlés.

| Territoire | La représentation EST là | …mais le comportement échoue | Le levier = crédit/signal |
|---|---|---|---|
| **NAV** | H décode la direction 0.81 (EDR-NAV-001) | émise==correct 0.03 (READOUT_GAP) | readout RL-récupérable si signal per-pas dense (EDR-NAV-003) |
| **NAV/énergie** | détresse énergétique dans H 0.90 (EDR-NAV-002) | forage non conditionné (endogène) | encodeur riche → readout, pas encodeur |
| **COG** | têtes décodables du tronc partagé | disjoint n'aide pas par l'archi | crédit sur le **tronc**, pas les readouts (EDR-COG-001 ; lr-par-tête réfuté) |
| **BIND** | did_x décodable de H (AUC 0.90) | Y ⊥ did_x (pas de liaison) | gate + **crédit épisodique** (EDR 129/136/158/159) |
| **CRAFT** | tier2 atteint (craft possible) | ne re-crafte pas | rétention POLICY-LOCKED, aucun levier-monde (EDR-CRAFT-001) |

**Conséquence stratégique** : le franchissement des portes est bloqué en aval de la représentation, sur le
**mécanisme de crédit**. D'où la migration **moteur** (numpy hebbien → torch différentiable) comme frontière
opérante — `HANDOFF_TORCH_READOUT_CREDIT.md`. Cibles dé-risquées par jalon offline : **T1** (readout NAV —
brief + M1 `EDR-NAV-003` : fourche résolue), **T2** (crédit multi-tête — brief + M1 `EDR-COG-001` : porter
l'échelle-de-loss, pas lr-par-tête), **T3** (recette BIND en prod — en cours, `learn_episode` in-world). La
représentation n'est plus le sujet ; le **crédit différentiable** l'est.

## ⚠️ MISE À JOUR 2026-07-29 — la thèse ci-dessus a été TESTÉE IN-WORLD, et elle n'y tient pas

> Ce qui précède datait du 2026-07-10 et n'a jamais intégré l'arc **EVO-001→010** (22-28 juillet). Le
> tableau reste valide **hors-monde** ; sa conséquence stratégique ne l'est plus in-world.

**Le tableau ci-dessus repose entièrement sur de la DÉCODABILITÉ** (H décode la direction 0.81, `did_x`
AUC 0.90, têtes décodables du tronc) — d'où « la représentation EST là ». L'arc EVO a mesuré autre chose :
l'**usage causal**. Les deux ne coïncident pas.

- [[EDR-EVO-004]] : la politique in-world évoluée ne LIT pas son observation — saillance action/canal au
  plancher sur tous les canaux (médiane ≈ 0.004) contre 0.99 pour un génome-lecteur synthétique.
- [[EDR-EVO-010]] : **4 champions sur 4 PORTENT l'arête lectrice et aucun ne lit** (1 concurrent sur la
  sortie → saillance 1.000 ; 64-75 concurrents → 0.000-0.021).

« Décodable depuis H » et « causalement lu par la politique » sont donc **deux propriétés distinctes**.
Là où la seconde échoue, il n'y a pas d'échec de CONVERSION en aval d'une représentation : il n'y a rien
qui lise en amont. La prescription « migrer vers le crédit différentiable comme frontière opérante » perd
son fondement in-world.

**Le crédit a été testé directement, et il ne produit pas la lecture** : [[EDR-EVO-007]] — crédit partiel,
sous-tâches à difficulté APPARIÉE, règle scellée, n=12 → **0/12**, identique au bras sans crédit partiel.
Converge [[EDR-S2-010]] (le crédit in-world ne bootstrappe pas la perception, même sous curriculum).

### Ce que l'arc EVO établit à la place

| levier manipulé | record | issue |
|---|---|---|
| rien (survie seule) | EVO-004 | ne lit rien |
| **poids** de l'objectif cognitif | EVO-005 | plafond non-cognitif, rien au-delà |
| **granularité** de l'objectif | EVO-007 | 0/12 |
| **opérateur de variation** | **EVO-009** | **12/12**, Fisher p = 9.6e-6, sans coût de survie |

Pivot = [[EDR-EVO-008]] : la lecture apparaît d'un **saut** (0.00 → 1.00 en une ère, aucune valeur
intermédiaire) puis se maintient **28 ères sur 29**. L'objectif fait déjà la RÉTENTION ; ce qu'il ne sait
pas faire, c'est CRÉER. Le crédit partiel servait à gravir un gradient qui n'existe pas.

⚠️ **EVO-009 est un DIAGNOSTIC, pas un algorithme** — son biais connaît les arêtes qui comptent.
[[EDR-EVO-010]] a réfuté le substitut agnostique évident (254 117 réveils → **zéro** lecteur) et montré que
créer l'arête ne SUFFIT pas. Le mécanisme qui distingue un lecteur d'un porteur d'arête **n'est pas établi**.

### Conséquence stratégique révisée

La frontière in-world n'est ni l'objectif ni le crédit : c'est la **structure de la variation** (ciblage,
pas volume). Pistes non adossées à un mécanisme établi : normaliser le fan-in par sortie, élaguer PENDANT
l'évolution, faire porter la variation sur des sous-espaces. Les jalons T1/T2/T3 gardent leur valeur
**offline** (NAV-003 : le readout EST RL-récupérable à signal dense) ; ils ne sont plus la voie in-world.

## Consolidation (SDR→EDR→ADR)
`docs/{SDR,ADR,EDR}/` + frontmatter `motivates`/`triggers`/`tests`. `tools/consolidate_records.py`
construit le graphe, échoue sur lien cassé (anti-théâtre). Niveau actuel : index statique (pas de LLM).
