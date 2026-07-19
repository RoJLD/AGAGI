---
id: REF-DEMAND-MARKER
type: REF
title: "Témoin causal de demande — ablation within-subject de la capacité X"
status: active
adopt_for: [S2-001, LANG-006, G1-001, MEM-001, EDR-S2-002, EDR-S2-003, EDR-S2-004, EDR-S2-005, EDR-S2-006, EDR-S2-007, EDR-S2-008, EDR-S2-009, EDR-S2-010, EDR-S2-011, EDR-WARM-001, EDR-WARM-002, EDR-WARM-003, EDR-WARM-004]
---

## Énoncé
Le témoin CAUSAL de « la capacité X est-elle exigée / paie-t-elle » = **ablation WITHIN-subject de X**
sur le MÊME sujet (intact vs X neutralisé), PAS « un agent équipé de X réussit » (between-subject, qui
FAUX-POSITIVE : un survivant compétent peut exister dans un monde qui n'exige pas X).

## Prédiction validée (vérité-terrain)
- BETWEEN faux-positive sur les mondes TRIVIAUX (un survivant existe sans que X soit porteur).
- WITHIN tranche juste : effondrement SSI X est causalement porteur.
- Corroborant : le poids |W| que la politique met sur X → 0.000 exact quand X ne paie pas.

## Implémentation de référence
`tools/demand_marker.py::ablation_verdict` (ratio d'effondrement + garde-fou n<12 + verdict).

## Modalités couvertes
| Modalité | Record | Ablation | Résultat |
|---|---|---|---|
| perception (proxy) | S2-001 | obs décorrélée | within tranche, between faux-positif |
| perception (in-world) | EDR-S2-002 | permutation batch_obs, 5 mondes | within plat (1.0×) tous mondes, between 4.7-5.2× → PERCEPTION_DECOY unanime |
| perception (ladder) | EDR-S2-003 | échelle permuted/noise/zero, 3 mondes | survie PERCEPTION-NEUTRE (même obs NULLE < 1.5×) ; PAS open-loop (comportement obs-dépendant 29% via contrefactuel //) |
| recette cognitive | EDR-S2-004 | grille corps×devise, sim survie | SENSIBLE SSI corps INSUFFISANT ET cognition payée en énergie (ratio ~10×, \|W\|0.93) ; sinon NEUTRE (\|W\|0.000) |
| recette mémoire | EDR-S2-005 | ablation mémoire, grille corps×rappel×devise | SENSIBLE SSI corps INSUFFISANT ET rappel DIFFÉRÉ ET énergie (ratio ~10×) ; **\|W\| faux-positive (0.909 neutre) → préférer l'ablation** |
| anticipation (MODULE) | EDR-S2-007 | ablation de MODULE (forward-model→identité) | SENSIBLE SSI corps INSUFFISANT ET dynamique (shift≠0) ET énergie (ratio ~16×) ; 1er jalon ablation-CALCUL (G4) |
| composition (MODULE) | EDR-S2-008 | ablation de MODULE (plan means→0), chaîne means→ends | SENSIBLE SSI corps INSUFFISANT ET chaîne≥2 ET énergie (ratio ~8×) ; 2e jalon ablation-CALCUL (G2) |
| **recette IN-WORLD** | EDR-S2-009 | flag cognitive_demand stoneage, oracle intact/ablé (par-agent) | **ON=PERCEPTION_DEMANDED (ratio 21×), OFF=NEUTRE → recette S2-006 RÉALISÉE in-world, flip S2-003.** ⚠️ signal GLOBAL défait l'ablation-permutation → canal PAR-AGENT requis |
| optim. imitation (in-world) | EDR-WARM-001 | génome imité par BPTT (forward torch), intact/ablé K=12 | **marqueur BASCULE PERCEPTION_DEMANDED dès acc_enseignant≈0.99 (ratio 1.6→2.1) MAIS survie plafonne 15 (oracle 200) à acc_enseignant 1.000 → dissociation : perception causale ✓, survie ✗. Mécanisme MESURÉ : acc on-policy plafonne 0.73 = transfert (dérive état récurrent), PAS covariate-shift des obs.** Usage : le marqueur mesure « utilise X », PAS « survit grâce à X » |
| optim. évolution (in-world) | EDR-WARM-002 | meilleur génome évolué W-only (forward mamba), intact/ablé K=12 | ratio ≈ 1.0 NEUTRAL sur 3 régimes de mutation → paysage de fitness PLAT, aucun gradient cognitif |
| diagnostic couverture/précision | EDR-WARM-004 | accuracy BINNÉE (tick sur états de l'oracle ; énergie sur son rollout), replay pur torch | **plateau SUR-DÉTERMINÉ : couverture 0.931→0.713 (écart 0.218, test PROPRE) ET précision 0.992→0.762 (écart 0.230, test CORRÉLATIONNEL)**. ⚠️ Leçon d'instrument : une accuracy mesurée sur la fenêtre PRÉ-MORTEM est tronquée (0.99 affiché vs ~0.71-0.79 réel sur l'horizon) — binner par tick/énergie révèle ce que l'agrégat cache |
| optim. DAgger (in-world) | EDR-WARM-003 | génome DAgger on-policy (forward torch), intact/ablé K=12 | **ratio 5.04 PERCEPTION_DEMANDED (le plus fort de l'arc)** : DAgger lève la métrique acc_on-policy 0.73→0.99 (fenêtre survivable), survie 15→35 (×2.3), marqueur ×2.4 — MAIS survie < oracle, mécanisme résiduel OUVERT (couverture vs précision, `_inworld_accuracy` tronquée). ⚠️ Usage : cette acc est pré-mortem, pas l'horizon-tâche |
| communication | LANG-006 | canal coupé | MI 1.04 vs 0.000 |
| généralisation | G1-001 | θ ablaté | Δ0.83 causal |
| mémoire | MEM-001 | mémoire remise à 0 | effondre 6-8× |
