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

## Consolidation (SDR→EDR→ADR)
`docs/{SDR,ADR,EDR}/` + frontmatter `motivates`/`triggers`/`tests`. `tools/consolidate_records.py`
construit le graphe, échoue sur lien cassé (anti-théâtre). Niveau actuel : index statique (pas de LLM).
