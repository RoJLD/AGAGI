---
id: REF-DEMAND-MARKER
type: REF
title: "Témoin causal de demande — ablation within-subject de la capacité X"
status: active
adopt_for: [S2-001, LANG-006, G1-001, MEM-001, EDR-S2-002, EDR-S2-003, EDR-S2-004, EDR-S2-005]
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
| communication | LANG-006 | canal coupé | MI 1.04 vs 0.000 |
| généralisation | G1-001 | θ ablaté | Δ0.83 causal |
| mémoire | MEM-001 | mémoire remise à 0 | effondre 6-8× |
