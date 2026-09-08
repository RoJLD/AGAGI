# Fil directeur AGI — les 5 portes G0→G4

> Stratégie qui chapeaute SCIENCE/NAS/BACKEND/FRONTEND. Continue (ne remplace pas)
> `../FIL_CONDUCTEUR.md`. État auto-généré : `tools/consolidate_records.py` → `results/records_graph.json`.
> Design : `../superpowers/specs/2026-06-29-Roadmap-AGI-Gates-design.md`.

## Thèse réconciliée
« Le bon est trouvé si le monde l'EXIGE (010/012) ET si l'agent l'APPREND (067) » — les deux se
mesurent en un point : la **généralisation zéro-shot**, jugée par **ablation within-subject de la
compétence transférée** (G1-001), et NON par `transfer_ratio` : ce fil est CLOS sur le constat
« métrique dégénérée » ([[EDR-AUDIT-002]]). État G1 : le NOYAU de survie transfère ([[EDR-156]],
12/12) mais la compétence world-spécifique n'ÉMERGE pas ([[EDR-157]]) — c'est l'un des trois noms du
mur [[EDR-LOCK-001]].

## Moteur (ADR-001, ADR-002)
GA (recherche de substrat) + gradient (apprentissage intra-vie) + Baldwin. Évolution topologique active.

## Les 5 portes (bottom-up par dépendance, capacités stratifiées EDR 075)
| Porte | Question | KPI | Outil | Record |
|---|---|---|---|---|
| **G0** | Le monde exige ? | ablation within-subject (perception / corps) — le `survival_ratio` between est RÉFUTÉ comme marqueur (S2-001) | `s2_demand_ablation.py`, `s2_cognition_body.py` | SDR-G0 — **verdict : la survie vient du CORPS** (S2-012, BODY 4/5) ; le monde n'exige la cognition que sous la recette S2-006, réalisée in-world (S2-009, 21×) |
| **G1** | Ça généralise ? ★ | ablation within de la compétence transférée | `cross_world_transfer.py`, G1-001 | SDR-G1 — noyau OUI (156), émergence world-spécifique NON (157) |
| **G2** | Ça compose ? | N1 proxy `binding_gap > 0.30` + `hit_end` ; N2 fort `comp_rate` du bras NU sous demande | `substrate_ab_compositional.py`, `compositional_world_probe.py` | SDR-G2 (re-scellée 2026-09-02) — **proxy FRANCHI** (EDR-136, 10/10) ; **fort NON FRANCHI = mur [[EDR-LOCK-001]]** |
| **G3** | Le langage paye ? | ablation du canal + MI(m;a), sous asymétrie d'information | `language_payoff_probe.py` | SDR-G3 — proxy CLOS : paie SSI coordination-demand (LANG-006) ; in-world 087 NÉGATIF |
| **G4** | Ça anticipe ? | ablation de MODULE forward-model (S2-007) ; fidélité du `g` bilinéaire | `anticipation_demand_world_probe.py`, PLAN-001→004 | SDR-G4 — proxy dé-risqué (bilinéaire) ; in-world DORMANT (EDR-142 : fix de persistance, gap S5) |

## État courant (2026-09-07) : le mur a TROIS NOMS ([[EDR-LOCK-001]])

Le diagnostic de juillet (« représentation OK, conversion en comportement KO, levier = crédit ») est
DÉPASSÉ par trois faits mesurés : (1) la migration torch est faite et **ne franchit rien seule**
(163 : survie A/B neutre) ; (2) le mur « rétention 2-pas » était un **artefact de learning-rate**
([[EDR-RETAIN-COMPOSE-LR]], classe E19) ; (3) ~~le verrou représentationnel est LEVÉ par le terme
bilinéaire~~ ([[EDR-BILINEAR]], 0/144) — ⛔ **RECTIFIÉ le 2026-09-08 : il n'y avait PAS de verrou
représentationnel.** La forme close du substrat plain compose PARFAITEMENT (9/9 à K=3, 16/16 à
K=4, vérifiés en Python pur ET in situ dans un vrai `TorchPopulationModel` ; témoins gelés dans
`results/plain_ceiling_witness_K{3,4}.json`). Ce que le terme bilinéaire lève est un verrou
d'**APPRENABILITÉ à budget fixe** (0.271 vs 0.932, 0/144), pas de représentation — la séparation
de CAPACITÉ annoncée par ce record est FAUSSE. Cf. son encart de réfutation. Ce qui reste est UN seul mur sous trois noms : « l'écriture
APPRISE dans le report » (taxonomy), « l'émergence d'une compétence COMPOSÉE » (G1/G2), « le RÉGIME
DE RECHERCHE » ([[EDR-EVO-016]]) — créer une dépendance nouvelle état-interne→sortie que ni le
gradient épisodique ni la sélection ne récompensent avant qu'elle soit fonctionnelle. Prédiction
falsifiable : un levier qui perce l'un doit percer les autres.

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
