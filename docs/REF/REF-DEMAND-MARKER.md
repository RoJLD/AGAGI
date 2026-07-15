---
id: REF-DEMAND-MARKER
type: REF
title: "Témoin causal de demande — ablation within-subject de la capacité X"
status: active
adopt_for: [S2-001, LANG-006, G1-001, MEM-001, EDR-S2-002]
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
| communication | LANG-006 | canal coupé | MI 1.04 vs 0.000 |
| généralisation | G1-001 | θ ablaté | Δ0.83 causal |
| mémoire | MEM-001 | mémoire remise à 0 | effondre 6-8× |
