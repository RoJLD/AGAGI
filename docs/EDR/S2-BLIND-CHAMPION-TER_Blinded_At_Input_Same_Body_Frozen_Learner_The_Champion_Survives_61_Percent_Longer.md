---
id: EDR-S2-BLIND-CHAMPION-TER
type: EDR
title: "Le champion HoF survit 61 % PLUS LONGTEMPS quand il ne voit plus — à corps identique, W identique, apprenant gelé, chemin d'identité coupé, bande RNG appariée : r = 1,614 [1,511-1,679], 7/7 seeds neufs, p = 0,016 ; les deux contrôles sont EXACTS (within aveugle = 1,000, no-op = 1,000) et le champion intact est SOUS le plancher no-perception 24,0 sur 7/7"
status: active
verdict: AVEUGLE_SURVIT_MIEUX
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER, REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-S2-BLIND-CHAMPION, EDR-124, EDR-S2-002]
---

> ⚠️ **DÉCOMPOSÉ le 2026-09-22 — règle scellée `S2-BLIND-CHAMPION-DECOMP-R1` (`docs/preregistrations/S2-BLIND-CHAMPION-DECOMP-R1.json`, `results/s2_blind_champion_decomp_r1.json`, mêmes 7 seeds que le `-ter`, références intact / aveugle IMPORTÉES du `-ter`) : lecture **`NI_L_UN_NI_L_AUTRE`**.** Le +61 % n'est porté NI par l'entrée du réseau seule NI par les 18 identités seules. Bras `except_identity` (46 entrées coupées, 18 identités gardées) : `r_ex` = **0,864** [0,864-0,905], `lo_ex` 7/7, `hi_ex` 0/7 — le champion survit **MOINS** que l'intact sur 7/7 seeds (19,0 ticks, exactement, sur 7/7 : une mort déterministe). Bras `identity_zeroed` (18 identités coupées, 46 entrées gardées) : `r_id` = **0,989** [0,989-1,024], `lo_id` 7/7, `hi_id` 0/7 — rien. Contrôles : `noop` apparié = 1,000 sur 14/14 (exact), `w_ok` 14/14. L'effet est donc une **INTERACTION** : couper les deux (aveugle total, 33,2-35,5 contre 21,0-22,0) fait ce qu'aucune coupure seule ne fait — et l'une des deux fait pire. Lecture : quand le réseau récurrent ne voit plus rien mais que 18 logits d'action lisent encore l'observation, la politique tue ; quand plus rien n'entre, la politique constante survit. « Sédation » vs « identités » est remplacé par « interaction » ; le mécanisme reste à nommer (un bras à entrée BROUILLÉE, même excitation, information détruite, est l'étape suivante). Coût : `_cout_s` du JSON est de l'horloge murale à travers une veille machine de six jours (note dans le JSON) — le coût CPU n'est pas mesuré ; référence `-ter`, mêmes 14 cellules, 1039 s. Ce record n'est pas modifié : « survit mieux SANS ENTRÉE » tient.

## Question et règles scellées

[[EDR-S2-BLIND-CHAMPION]] s'était arrêté au contrôle (`INDETERMINE-HARNAIS`) : l'aveugle « voyait encore » de 6 à
10 % — et la cause mesurée était le **plancher de bruit RNG de l'instrument** (±6-8 %, no-op non apparié). La revue
(P2.42) avait de plus établi que l'intervention n'était pas celle que le sceau décrivait (E8) : annuler
`W[:num_inputs, :]` laissait l'observation entrer par `H[:, :max_I] = x` — dont 18 logits d'action SONT
l'observation ([[EDR-HOF-IO-OVERLAP]], E24) — et faisait tomber le drain de 2,40 à 1,30 (E26, P1.7). L'observation
de départ (« l'aveugle survit 39 % de plus », 7/7) restait donc **non lue**.

Deux règles scellées, chacune AVANT sa première cellule :

* **`-bis`** (`docs/preregistrations/S2-BLIND-CHAMPION-bis.json`, sceau `928fb3256e09…`) — l'aveuglement passe
  **à l'ENTRÉE** : la politique reçoit une observation NULLE (`InputBlindFrozenMamba`), le génome, le corps, les biais
  et la récurrence sont ceux du champion, bit-identiques, et le chemin d'identité est coupé lui aussi ; l'apprenant
  legacy est **gelé dans les deux bras** (`compute_policy_gradient` no-op ; les écritures NTM de `forward` ne le sont
  pas, identiques dans les deux bras) ; bande RNG **appariée** (`run_ablation_map(paired_band=True)`, P2.41 b) et
  no-op mesuré par bras. Contrôles avant la DV : (i) intervention réelle et minimale (la politique aveugle ignore
  l'observation — prouvé à 0 monde, `tests/sandbox/test_s2_blind_champion_bis.py` — et le génome est le même objet) ;
  (ii) l'aveuglement mord : `within_ratio` du bras aveugle attendu **exactement 1,000** (un zéro dérangé est un zéro,
  mêmes tirages), tolérance 0,05 ; (iii) plancher 24,0 ; (iv) non-dégénérescence ; (v) famille de 7. Barres
  d'origine : `r_blind` ≥ 1,20 et `sign_p` < 0,05 → `AVEUGLE_SURVIT_MIEUX` ; ≤ 1,05 → `PAS_DE_COUT`.
* **`-ter`** (`docs/preregistrations/S2-BLIND-CHAMPION-ter.json`, sceau `dd7641b30cea…`) — même design, **seeds
  NEUFS** (3032-3038), écrit en déclarant TOUT le `-bis` : sa clause (iii) écartait tout seed dont le bras INTACT est
  sous le plancher, et le champion à crédit gelé survit 20,5-22,5 ticks — **l'intact sous le plancher était le
  phénomène**. La clause (iii)-ter n'écarte un seed que si les DEUX bras sont au plancher ou dessous ; un intact sous
  le plancher est publié (`intact_sous_plancher`). Verdict `blind_champion_verdict_ter` (8 cas ; à n=7 l'unanimité est
  requise : 6/7 donne p = 0,125, dit d'avance).

## Résultats

**`-bis`** (`results/s2_blind_champion_bis.json`, 599 s, seeds 2026, 3026-3031) — lecture scellée
**`INDETERMINE-DEGENERE`** : 7/7 seeds écartés par (iii). Contrôles (i) 7/7, (ii) within aveugle = 1,000 **exact** 7/7,
no-op apparié = 1,000 **exact** sur les deux bras 7/7 — la bande appariée efface entièrement les ±6-8 % de
[[EDR-S2-BLIND-CHAMPION]] dans ce régime. Post-hoc, NON LU : intact 20,5-22,5, aveugle
33,0-35,5, r 1,467-1,732 sur 7/7.

| seed | intact (survie méd.) | within intact (apparié) | no-op intact | aveugle (survie méd.) | within aveugle | no-op aveugle | r = aveugle / intact |
|---|---|---|---|---|---|---|---|
| 2026 | 22,5 | 0,989 | 1,000 | 33,0 | 1,000 | 1,000 | **1,467** |
| 3026 | 20,5 | 0,988 | 1,000 | 35,2 | 1,000 | 1,000 | **1,720** |
| 3027 | 20,5 | 1,000 | 1,000 | 35,5 | 1,000 | 1,000 | **1,732** |
| 3028 | 20,5 | 1,000 | 1,000 | 35,2 | 1,000 | 1,000 | **1,720** |
| 3029 | 20,5 | 1,000 | 1,000 | 35,2 | 1,000 | 1,000 | **1,720** |
| 3030 | 20,5 | 1,000 | 1,000 | 33,0 | 1,000 | 1,000 | **1,610** |
| 3031 | 20,5 | 0,988 | 1,000 | 33,0 | 1,000 | 1,000 | **1,610** |

**`-ter`** (`results/s2_blind_champion_ter.json`, 1039 s, seeds 3032-3038, population neuve) — lecture
scellée **`AVEUGLE_SURVIT_MIEUX`** : `r_blind` = **1,614** [1,511-1,679], n = 7, `sign_p` = **0,016**
(7/7 dans le même sens), aucun échec de contrôle, aucun seed écarté, `intact_sous_plancher` = 7/7.

| seed | intact (survie méd.) | within intact (apparié) | no-op intact | aveugle (survie méd.) | within aveugle | no-op aveugle | r = aveugle / intact |
|---|---|---|---|---|---|---|---|
| 3032 | 21,0 | 0,977 | 1,000 | 35,2 | 1,000 | 1,000 | **1,679** |
| 3033 | 22,0 | 1,035 | 1,000 | 33,2 | 1,000 | 1,000 | **1,511** |
| 3034 | 22,0 | 0,978 | 1,000 | 34,8 | 1,000 | 1,000 | **1,580** |
| 3035 | 22,0 | 0,978 | 1,000 | 35,5 | 1,000 | 1,000 | **1,614** |
| 3036 | 22,0 | 0,978 | 1,000 | 35,5 | 1,000 | 1,000 | **1,614** |
| 3037 | 21,5 | 0,977 | 1,000 | 35,5 | 1,000 | 1,000 | **1,651** |
| 3038 | 22,0 | 1,000 | 1,000 | 34,8 | 1,000 | 1,000 | **1,580** |

Résolution de l'instrument : within intact apparié 0,977-1,035 (déranger la perception du champion
intact ne change sa survie que de ±2-3 %, DANS le no-op de 1,000 ± rien : le champion intact est `PERCEPTION_DECOY`
à bande appariée, comme [[EDR-124]] à bande nue) ; within aveugle exactement 1,000 (7/7) ;
no-op exactement 1,000 (14/14).

**Ce que chaque cellule porte, et ce qu'elle ne porte pas.** La DV lue par bras est `intact_median` — la survie médiane
sur les K ères du bras, telle que `run_ablation_map` la publie (colonnes « survie méd. » des tables ; `r` = `intact_median`
aveugle / `intact_median` intact). Chaque cellule porte AUSSI le champ `verdict` de `run_ablation_map` : `INCONCLUSIVE_DEGENERATE` sur 14/14 (`-bis`), 14/14 (`-ter`) et 14/14 (DECOMP). C'est le verdict du **marqueur de demande** (ablation de perception within-subject DU SUJET, clause de plancher 24,0 — E14) sur des
sujets dont la survie est sous ce plancher : il dit que le marqueur ne peut pas lire une demande de perception sur eux. Il ne
porte **pas** sur la DV de ce record (`r_blind`, puis `r_ex` / `r_id`), qui a ses propres contrôles (i)-(v) et sa propre règle.
Un lecteur qui verrait `INCONCLUSIVE_DEGENERATE` dans les `rows` du JSON et conclurait « run nul » lirait le mauvais champ.

## Verdict

**`AVEUGLE_SURVIT_MIEUX`.** Sur le même génome, le même corps, les mêmes biais et la même récurrence, sans aucun
apprentissage, le champion HoF de `stoneage` survit **33,2-35,5 ticks** quand son observation est
remplacée par des zéros, contre **21,0-22,0 ticks** quand il la lit — et ces derniers sont SOUS le
plancher no-perception 24,0 mesuré pour ce monde. L'observation d'origine (+39 %, confondue par le corps et par le
chemin d'identité) est **remplacée** par une mesure à corps apparié : +61 %.

Ce que cela dit du fil S2 : ce que le champion fait de son observation lui **coûte** ; il n'y a pas seulement
« aucune demande de perception détectable » ([[EDR-S2-002]], `DECOY`), il y a un **contenu perceptif net-négatif**
dans la politique évoluée. Cela converge avec [[EDR-EVO-011]] (lire le canal de type coûte la survie parce que l'acte
débloqué est net-négatif) et avec la synthèse du fil ([[EDR-S2-012]] : le gradient de sélection de la cognition est
nul — ici, il est de signe contraire à la lecture).

## Portée — ce que ce record N'ÉTABLIT PAS

- **Le confond SÉDATION reste non séparé**, comme au sceau d'origine : une observation nulle change aussi le niveau
  d'excitation du réseau. « Ne pas voir » et « être moins excité » ne sont pas distingués ici ; le bras à entrée
  BROUILLÉE (même niveau, information détruite) est l'étape suivante — le `within_ratio` apparié du champion
  intact (≈ 1,0, perception DÉRANGÉE, excitation conservée) est un premier indice que la sédation compte plus que
  l'information : déranger ne fait rien, éteindre fait +61 %.
- **L'INFORMATION seule n'explique pas l'effet — c'est déjà mesuré ici.** Le bras intact à perception DÉRANGÉE (obs d'un pair,
  même distribution, information détruite, bande appariée) survit comme l'intact : within 0,977-1,035. Ce qui fait +61 %,
  c'est la suppression de l'ENTRÉE, pas la destruction de son contenu. Et « obs = 0 » n'est pas seulement moins
  d'excitation : par le chemin d'identité ([[EDR-HOF-IO-OVERLAP]]), **18 logits d'action du champion SONT l'observation** —
  le bras aveugle met donc aussi 18 logits d'action à zéro, directement. Deux mécanismes restent confondus (moins
  d'excitation récurrente ; 18 actions changées) ; les séparer demande un bras qui coupe l'entrée du réseau en
  conservant les 18 logits d'identité, ou l'inverse. Lire « le champion survit mieux SANS ENTRÉE », pas « sans voir ».
- **Un monde, un sujet, un régime** (stoneage, 12 agents, 200 ticks, K=12). Rien sur les autres mondes ni sur
  d'autres génomes.
- **Apprenant gelé** : le résultat ne dit rien de ce que le crédit in-world ferait de la cécité.
- Les écritures NTM de `forward` ne sont pas gelées (identiques dans les deux bras).

## Registre

- **E8** (sceau décrivant une autre intervention) : corrigée par le `-bis` ; la règle : « décrire l'intervention
  par le CHEMIN qu'elle coupe, et prouver à 0 monde qu'elle le coupe » (test de forward invariant).
- **E14** (clause de plancher qui exclut le phénomène) : la clause (iii) du sceau d'origine et du `-bis` écartait un
  intact sous le plancher — ce qui est ici le résultat. Corrigée par le `-ter` sur seeds NEUFS ; le `-bis` reste
  gravé `INDETERMINE-DEGENERE` et n'est pas relu.
- **E11** : le `-ter` déclare le `-bis` en entier et n'en réutilise aucun seed.
- Résolution : la bande appariée (P2.41 b) rend le no-op EXACT dans ce régime — la référence `paired_band` devrait
  devenir le défaut de tout NOUVEAU contraste d'ablation (les records existants gardent la bande nue, annoncée).

Converge [[EDR-S2-BLIND-CHAMPION]], [[EDR-124]], [[EDR-S2-002]], [[EDR-EVO-011]], [[EDR-HOF-IO-OVERLAP]].
