---
id: EDR-S2-002
type: EDR
title: "Ablation-perception within-subject in-world : le demand-marker franchit le pont proxy→in-world"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
Le témoin within-subject (S2-001, proxy) tient-il sur le VRAI monde ? La perception du champion HoF
est-elle causalement porteuse de sa survie, ou un survivant compétent masque-t-il un leurre (le
faux-positif between du benchmark s2_demand) ?

## Méthode
`tools/s2_demand_ablation.py` : champion HoF INTACT vs perception PERMUTÉE (PerceptionAblatedMamba,
dérangement de batch_obs, within-subject) sur les 5 mondes ; contraste avec between (champion vs réflexe).
n = 12 ères appariées. Garde-fou n<12 (demand_marker). K=12, seed=2026, agents=12, ticks=200.

## Résultats
| monde | within | between | verdict |
|---|---|---|---|
| soup | 1.00 | 4.92 | PERCEPTION_DECOY |
| stoneage | 0.99 | 4.67 | PERCEPTION_DECOY |
| agricultural | 1.19 | 5.17 | PERCEPTION_DECOY |
| industrial | 0.99 | 4.67 | PERCEPTION_DECOY |
| famine | 1.07 | 4.67 | PERCEPTION_DECOY |

Désaccords between/within (between crie demande, within dit leurre) : **les 5 mondes** (soup, stoneage,
agricultural, industrial, famine) — unanime.

## Verdict
`INWORLD_PERCEPTION_DECOY` — sur les 5 mondes réels, l'ablation within-subject de la perception (permutation
des observations du champion avec celles d'un pair) laisse la survie quasi inchangée (within ≈ 1.0) alors que
le champion survit très largement au réflexe (between 4.67-5.17×) : désaccord unanime entre les deux marqueurs
sur 5/5 mondes. Le signal between — base du verdict « le monde exige l'intelligence » de `s2_demand` — est un
FAUX-POSITIF perceptuel dans chaque monde testé : le champion est un survivant réellement compétent, mais sa
compétence n'est pas causalement médiée par la perception (politique quasi-open-loop). C'est la confirmation
in-world la plus nette de la prédiction du proxy S2-001, et elle corrobore le fil « in-world NEUTRE ». Le
design était falsifiable dans les deux sens — ce résultat négatif-pour-la-demande est un résultat valide et
informatif, pas un échec.

## Portée & limites
Ablation du flux sensori-égocentrique COMPLET (perception + proprioception), pas la perception isolée
(affinage per-monde = follow-up B, externe-seul). Le résultat dit donc que la survie ne dépend pas
causalement de l'entrée égocentrique PRISE EN BLOC ; il ne dissèque pas quel sous-canal (si aucun) porterait
un signal marginal. Corroborant |W| non disponible sur champion HoF (poids non exposés). Cohérent avec le fil
« in-world NEUTRE » : le champion gagne par un canal autre que la perception (corps/comportement quasi
open-loop), pas par une cognition perceptuellement fondée.
