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
| **G0** | Le monde exige ? | ablation within-subject (perception / corps) — le `survival_ratio` between est RÉFUTÉ comme marqueur (S2-001) | `s2_demand_ablation.py`, `s2_cognition_body.py` | SDR-G0 — **verdict : la survie vient du CORPS** (S2-012, BODY 4/5) ; le monde n'exige la cognition que sous la recette S2-006, réalisée in-world (S2-009, ≥ 22× = cap/plancher) |
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
> ⚠️ **Re-scellée le 2026-09-15** — ce que « mesurée » exige est fixé dans la sous-section
> « Règle des portes — re-scellée » ci-dessous ; cette formule seule était satisfaite à la lettre et vide.

## Direction courante (décidée le 2026-09-14) — où nous allons, et dans quel ordre

La direction opérationnelle, la liste priorisée (20 rangs) et les paris tranchés vivent dans
[`PRIORITES_ET_DETTES.md`](PRIORITES_ET_DETTES.md), bloc **« 🧭 2026-09-14 — AUDIT GLOBAL +
BRAINSTORM »** en tête du fichier. Résumé : **A** — calibrer l'APPRENANT in-world (aucun contrôle
positif à ce jour ; les nuls « le crédit n'apprend pas à froid » valent < 50 mises à jour par agent) et
le CORPS (dérivé des lignes 0-9 de `W` : tout édit de `W` est aussi une intervention métabolique), PUIS
un seul run scellé dans le monde S2-009 qui dit ce qu'il ne tranche pas ; **B**, en parallèle sans
bail — la prédiction falsifiable de [[EDR-LOCK-001]] en proxy mémoire D = 2 ; **C** (porte IW-1 /
IW-2, le north-star en forme minimale) en réserve conditionnelle. Axe cognitif primaire des trois
mois : **mémoire / écriture**. Le champion prod stoneage n'est plus un sujet pour mesurer la
cognition (survie = corps, logits = observation, plancher de bruit 8 %).
[`SPECIFICATION_10ANS.md`](SPECIFICATION_10ANS.md) est archivé de fait : ses quatre paris sont
tranchés dans le bloc 🧭.

### Règle des portes — re-scellée le 2026-09-15 (P3.5 f)

**Pourquoi re-sceller.** « On ne franchit une porte que si la précédente est mesurée » était satisfaite à
la lettre et vide (bloc 🧭 du backlog) : G0 est `validated` dans `SDR-G0` sur le KPI
`survival_ratio(champion)/survival_ratio(dummy)` — un marqueur BETWEEN-subject que [[S2-001]] a RÉFUTÉ
depuis (faux positif 5-7× sur un monde TRIVIAL à vérité-terrain, où l'observation est un leurre), et
G1-G4 ont été tentées in-world sur un sujet sans contenu cognitif ([[EDR-S2-012]]). Une porte « mesurée »
par un instrument réfuté n'est pas mesurée. Quatre clauses, chacune fondée sur un record ; **une porte ne
se dit « mesurée » que si son verdict les satisfait toutes.**

1. **Le marqueur de demande est l'ablation WITHIN-subject de la capacité — jamais « un survivant
   existe ».** [[S2-001]] : sur TRIVIAL (obs inutile), BETWEEN rend 5,1-7,1× et WITHIN 1,0× ; sur DEMANDING
   les deux rendent ~5×. Le gabarit est [[REF-DEMAND-MARKER]] (`ablation_verdict`, barreau `permuted`
   de préférence à `zero`, plancher `floor=` DÉCLARÉ du régime — sous le plancher, `INCONCLUSIVE_DEGENERATE`
   et non « pas de demande », [[EDR-AUDIT-001]]). Ce que le marqueur mesure est une propriété du SUJET
   (a-t-il un repli survivable sans X ?), pas du monde ([[EDR-S6-FALLBACK-RATE]] : 8/12 vs 0/12 selon la
   seule init) : publier l'init ou la provenance du sujet fait partie du verdict.

2. **Contrôle positif CO-EXÉCUTÉ, dans le même dispositif et le même régime que le nul.** Un nul sans
   contrôle positif est ininterprétable : WARM-002 et S2-006 n'en avaient pas ; [[EDR-S2-012]] en a un
   (oracle sur génomes FRAIS dans le régime `cognitive_demand` : 200,0 vs 7,0, verdict `COGNITION`), et
   c'est ce qui rend son nul lisible — « on aurait vu s'il y avait eu ». In-world, la recette S2-006
   réalisée par [[EDR-S2-009]] est le seul contrôle positif de G0 (ON : 200,0 → 9,0 en médianes
   re-mesurées par [[EDR-AUDIT-001]], ratio 22,22 = cap/plancher, à lire **≥ 22×** — les deux bras sont
   AUX BORNES de l'instrument : intact censuré à max_ticks, ablé au plancher no-perception ; le run
   d'origine rendait 21,05, d'où le « 21× » du verdict du record — 12/12 ères) ; son bras OFF
   (7,0 = 7,0) est un no-op LITTÉRAL — métrique morte — et ne
   prouve PAS la spécificité, établie ailleurs (S2-001, LANG-006, MEM-001 ; [[EDR-AUDIT-001]]).

3. **Plancher de bruit PUBLIÉ à côté de chaque ratio.** [[EDR-S2-BLIND-CHAMPION]] (2026-09-08) : le
   no-op EXACT de `run_ablation_map` — aucune observation changée, seule la bande RNG bouge — rend
   **1,058** sur le champion et **0,922** sur le champion aveuglé ; le `within_ratio` publié du champion
   vaut **0,991**, donc DEDANS. Conséquences opératoires : un ratio dans la bande [0,922 ; 1,058] n'est pas
   distinguable de zéro et le record le dit ; `PERCEPTION_DECOY` se lit « rien de détectable au-dessus de
   ~8 % », jamais « rien » ; `noop_control=True` publie ce plancher ; l'appariement de bande le divise par
   6 (~1 %). CLAUDE.md §Calibration en fait une règle générale : un instrument de contraste sans plancher
   de bruit mesuré ne sait pas ce qu'il ne peut pas voir.

4. **Statut RÉEL de G0.** `SDR-G0 : validated` par [[EDR-112]] / [[EDR-118]] (champion vs dummy,
   3,7-4,7×) : la porte a été franchie sur le marqueur BETWEEN, réfuté depuis par S2-001 ; ce statut est
   l'état HISTORIQUE du SDR, pas un franchissement au sens de cette règle. Ce que le dépôt sait depuis :
   la survie du champion prod vient du CORPS ([[EDR-S2-012]] — BODY sur 4 mondes et non 5, `industrial`
   étant un clone de `stoneage` ; `champion_body` bat le champion complet ; le bras `body` est lui-même
   between, n effectif 1 sur le génome) ; [[EDR-124]] (EXIGE ×4 en survie) est `legacy`,
   `corrected_by: EDR-S2-012`, et ses verdicts d'ablation sont bornés par le plancher de 8 % ; le
   champion n'est plus un sujet pour mesurer la cognition (18 de ses logits d'action SONT l'observation).
   G0 est donc **mesurée in-world uniquement sous la recette S2-006** ([[EDR-S2-009]]), sur un sujet
   (l'oracle) qui n'est pas le champion prod — et c'est la ligne du tableau ci-dessus qui fait foi.

Pour les portes G1-G4 : aucun verdict « franchi » sans (1) within-subject, (2) contrôle positif
co-exécuté, (3) plancher de bruit publié — la ligne « proxy FRANCHI » de G2 ([[EDR-136]]) et les
arêtes taxonomy en satisfont (1) ; (2) et (3) restent à publier record par record, ce que P3.6
(bandeaux de portée) fait APRÈS le verdict de P1.6, jamais avant (E8).

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
