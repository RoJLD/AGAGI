---
id: EDR-S2-002
type: EDR
title: "Ablation-perception within-subject in-world : le demand-marker franchit le pont proxy→in-world"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

> ⚠️ **RÉSOLUTION DE L'INSTRUMENT, mention posée le 2026-09-16 (P2.41 a) — [[EDR-S2-BLIND-CHAMPION]].** `run_ablation_map`, qui porte les verdicts de ce record, a un **plancher de bruit RNG de ±6-8 %**, mesuré le 2026-09-08 par no-op EXACT (aucune observation changée, within-subject : même génome, même corps) : `within_ratio` **1,058** sur le champion, **0,922** sur un champion aveuglé — l'ablation consomme des tirages du flux global (`derange_rows`, boucle de rejet) et désynchronise la bande RNG du bras ablaté. Conséquence de lecture : tout `within_ratio` compris entre 0,92 et 1,06 n'est **pas distinguable de zéro**, et `PERCEPTION_DECOY` se lit « aucun effet détectable au-dessus de 8 % », pas « aucun effet ». À bande APPARIÉE (`NullAblatedMamba` en référence, P2.41 b) le no-op tombe à 1,012 (bruit ÷ 6). Les `within` ≈ 1,00 de la table sont À L'INTÉRIEUR de cette bande. Les verdicts ci-dessous ne sont pas modifiés.

> ⚠️ **E24, mention posée le 2026-09-15 (P2.46 rang 7) — [[EDR-HOF-IO-OVERLAP]].** Le sujet de ce record, le champion HoF, a **18 logits d'action qui SONT l'observation** (64 + 126 dans 172 nœuds). **Le verdict `PERCEPTION_DECOY` TIENT** : `PerceptionAblatedMamba` permute à l'ENTRÉE, donc ablate les deux chemins (identité et poids). **Sa lecture est précisée** : ce champion LIT l'observation — bascule de décision 0,51 sur les canaux partagés 46-53 et 0,50-0,83 sur `lidar_n`, `adj_energy`, `ax`, `terrain_4`, `in_surprise`, `age` (mesure 2026-09-15, n = 1 seed) — et *DECOY* signifie « lire ne paie pas la survie », non « ne lit pas » (P2.59 : aucune lecture câblée n'est net-positive sur stoneage ; EVO-011 : lire coûte). `run_ablation_map` publie désormais `io_overlap`.

> ⚠️ COMPTE DES MONDES CORRIGÉ — [[EDR-S2-012]]. « Désaccord unanime sur les 5 mondes » en vaut AU PLUS 4 : `IndustrialWorld` est `class IndustrialWorld(Biosphere3D)` (clone — compteur `pollution` jamais lu par la biologie) et `stoneage` EST `Biosphere3D` ; les lignes stoneage et industrial du tableau (0.99 / 4.67, identiques au chiffre près) sont la même simulation comptée deux fois. Le verdict `INWORLD_PERCEPTION_DECOY` tient par ailleurs : le bras intact vit ~22-29 ticks sur 200 (médianes de S2-003 et S2-012, même champion/config) — loin du plancher no-perception 9.0 (EDR-WARM-010) et du cap — le nul within n'est donc pas fabriqué par une borne. Deux réserves de lecture : (1) ce record ne publie aucune valeur absolue de survie, seulement des ratios (défaut épinglé sur S2-009 par [[EDR-AUDIT-001]]) — les absolus vivent dans S2-003/S2-012 ; (2) le bras between compare à un réflexe au plancher de métrique (~6 ticks, cf. S2-012 : `random_* = 6` constant sur des mondes hétérogènes) — contraste positif, au pire sous-estimé, mais mesuré contre un sol.

> ⚠️ LISIBILITÉ SOUP RÉVISÉE — [[EDR-S2-013]] (2026-09-02, pronostic scellé AVANT run). Contre le plancher no-perception mesuré sur les CLONES DU CHAMPION (32.0, `PLANCHER_NOPERC`), le bras intact soup est DESSOUS (29.25) : la ligne soup est INCONCLUSIVE_DEGENERATE à ce régime — son `within = 1.00` peut être fabriqué par la borne. L'argument de lisibilité ci-dessus (plancher 9.0 de WARM-010, agents frais) sous-gardait. Les 4 autres lignes tiennent AU-DESSUS de leur plancher (+3.50 à +6.00) : le verdict DECOY y sort RENFORCÉ.

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
