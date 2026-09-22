---
id: EDR-TD-STEP-PILOT-R0
type: EDR
title: "Le crédit TD PAR PAS n'apprend pas la composition DIFFÉRÉE à D=1 (TD(0) : 0,190 vs référence 0,163, 1/12) alors qu'il apprend la même tâche SANS délai (0,503, 12/12) — et la trace d'éligibilité TD(λ=0,9) transporte du crédit vers le pas encode : 0,253, 12/12 seeds, séparation totale, à un seul des deux pas (E19)"
status: active
verdict: TD0_INERTE|TRACE_AIDE
gate: G2
tests: [SDR-G2]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-BILINEAR, EDR-LOCK-002, EDR-CALIB-LEARNER]
---

> ⚠️ **BORNE le 2026-09-16, quelques heures après — règle scellée `TD-STEP-PILOT-R1` (`docs/preregistrations/TD-STEP-PILOT-R1.json`, `results/td_step_pilot_r1.json`, 48 cellules neuves + 36 importées de R0 sceau vérifié, 45 min) : lecture `AIDE_NON_INVARIANTE|DOSE_LAMBDA_ABSENTE`.** Le `TRACE_AIDE` ci-dessous est une observation à UN POINT (lr 4,0, λ 0,9). (1) **Pas d'invariance au pas** : à lr 2,0 (0,125/agent) `tdlam` 0,190 [0,170-0,211] contre `td0` 0,187 [0,155-0,200] — 0/12 seeds au-dessus de la marge (référence lr=0 0,163 [0,130-0,195], `td0` au-dessus sur 1/12 : TD(0) reste inerte à D=1, comme à 4,0 et 8,0). (2) **Pas de dose en λ au sens scellé** : à lr 4,0, λ = 0,5 donne 0,208 [0,175-0,237] contre `td0` 0,190 [0,164-0,203] — 0/12 au-dessus de la marge 0,05 ; fait post-hoc, hors verdict : l'ordre 0 < 0,5 < 0,9 tient sur 12/12 seeds (0,190 → 0,208 → 0,253), compatible avec un transport proportionnel à γλ (0,45 / 0,81) mais sous la résolution de la règle. Ce que ce record ÉTABLIT reste : TD(0) par pas inerte à D=1 avec ses deux contrôles (trois pas mesurés : 2,0, 4,0, 8,0) ; et une trace qui déplace de +0,063 à un seul point de fonctionnement — à ne pas citer comme « la trace transporte » sans ce point. Le billet à deux issues de la ligne `eligibility_trace_credit` (ADR-005) n'est donc acquis qu'à ce point ; il faut un balayage (lr × λ) scellé avant d'en faire une pièce.

## Question et règle scellée

P4.11 (ADR-005, item 1) demandait une trace d'éligibilité TD(λ) dans `TorchPopulationModel._td_update` — le
crédit local SANS BPTT — « calibrée à 0 simulation, puis mesurée là où elle peut agir ». La correction (A) de la
revue (agagi-52) a déplacé le lieu de l'issue positive : le proxy D=2 de [[EDR-LOCK-002]] apprend par
`learn_episode` (REINFORCE épisodique) et ne passe **jamais** par `_td_update` ; `_td_update` ne tourne aujourd'hui
qu'in-world, sur une tâche same-tick. Le seul lieu où une trace de `_td_update` peut agir est un **pilote TD PAR
PAS** : `forward` + `learn` à chaque pas, récompense 0 puis ±1 au dernier pas, sur la composition `(q+key)%K`
**différée** (key au pas 0, q au pas 1 : `CompositionTask(same_tick=False)`, D=1).

Règle scellée AVANT toute cellule : `docs/preregistrations/TD-STEP-PILOT-R0.json` (`tools/td_step_pilot.py`, tampon
de provenance `72ce45ac`, sceau `ea2c8d856dc8…`). Six bras appariés par seed, seeds 1-12, deux pas
(E19) : `td0` (λ=0), `tdlam` (λ=0,9, traces remises à zéro à chaque épisode — publié), `lr0_reference` (même
dispositif, pas nul : la barre est **référence + 0,05**, jamais « chance + marge »), `td0_d0` (**contrôle positif
du CHEMIN de crédit** : même TD par pas, même dose, SANS délai), `lr0_reference_d0`, `bptt` (**contrôle positif du
SUBSTRAT** : BPTT supervisé 2 pas, Adam, le 0,923 publié par [[EDR-RETAIN-COMPOSE-LR]]). Substrat bilinéaire rang 16
pour les six bras, W/U/V/W_bl tracés. Pas TD : `lr` {4,0 ; 8,0} SGD, soit **0,25 / 0,5 par agent** (lr/B, E19 occ.
lr/B) ; 3000 épisodes ; BPTT : Adam {0,002 ; 0,02}, 600 épisodes. Branches en ordre imposé : INCOMPLET,
CONTROLE_SUBSTRAT_ECHOUE, CONTROLE_CHEMIN_ECHOUE, puis `TD0_{APPREND|INERTE}|TRACE_{AIDE|NUIT|NEUTRE}` (AIDE
testée avant NUIT ; « à l'un des deux pas » pour chaque clause, 10/12 seeds, marge 0,05).

**Ce que la fumée seed 0 a mesuré AVANT le scellement, déclaré dans la règle et exclu du n** — deux corrections
de design qui valent plus que le verdict : (a) le contrôle positif « BPTT 0,923 » est BILINÉAIRE ; en plain, le
BPTT 2 pas rend 0,21 / 0,27 à 600 épisodes → un bras TD plain **ne pourrait pas réussir** (E1), d'où le substrat
bilinéaire et la trace étendue à tous les paramètres ; (b) il manquait un contrôle positif du **chemin** : TD par
pas SANS délai n'apprend rien sous `lr` 0,04-0,4 même à 4000 épisodes (0,18 vs 0,17) — il apprend à `lr` 4,0
(0,30 à 1500 épisodes, 0,52 à 3000 ; 8,0 → 0,38 ; 40 → diverge). Sans (b), un nul à D=1 aurait été lu comme
« le délai » alors qu'il aurait été « la dose ».

## Résultats

`results/td_step_pilot_r0.json`, 144 cellules, 76 min CPU (machine partagée avec quatre commits et leurs
portes : MAJORANT). Médiane [min-max] sur 12 seeds :

| bras | lr 4,0 (0,25/agent) | lr 8,0 (0,5/agent) |
|---|---|---|
| `td0` (TD(0) par pas, D=1) | **0,190 [0,164-0,203]** | 0,172 [0,138-0,200] |
| `tdlam` (λ=0,9, D=1) | **0,253 [0,220-0,298]** | 0,174 [0,145-0,213] |
| `lr0_reference` (D=1) | 0,163 [0,130-0,195] | 0,163 [0,130-0,195] |
| `td0_d0` (contrôle CHEMIN, D=0) | **0,503 [0,453-0,542]** | 0,232 [0,191-0,261] |
| `lr0_reference_d0` | 0,168 [0,133-0,192] | 0,168 [0,133-0,192] |
| `bptt` (contrôle SUBSTRAT, Adam 0,002 / 0,02) | **0,807 [0,766-0,848]** | 0,182 [0,145-0,197] |

Comptes scellés : `td0 > lr0_reference + 0,05` : **1/12 / 0/12** ;
`td0_d0 > lr0_reference_d0 + 0,05` : **12/12 / 7/12** ;
`tdlam > td0 + 0,05` : **12/12 / 0/12** ; `tdlam < td0 − 0,05` :
0/12 / 0/12. À `lr` 4,0 la séparation `tdlam` / `td0` est **totale** : le plus
faible `tdlam` (0,220) dépasse le plus fort `td0` (0,203) de 0,017 —
0/144 paires croisées. Gain médian **+0,063**. Dose publiée par cellule : 6000 mises à jour TD
par agent (deux transitions par épisode, bootstrap V(s₁) puis 0 terminal), 6000 mises à jour tracées et
3000 remises à zéro pour `tdlam`, `lr_effective_per_agent` 0.25.

Au pas 8,0 **tout le dispositif est inerte** — y compris les deux contrôles (`td0_d0` 7/12, `bptt` Adam 0,02 =
0,182, le même effondrement 2 pas à 0,02 que [[EDR-RETAIN-COMPOSE-LR]]) : ce pas est hors du
régime de fonctionnement, il ne contredit pas le pas 4,0, il ne le corrobore pas non plus.

## Verdict

**`TD0_INERTE|TRACE_AIDE`**, lu par la règle scellée, dans l'ordre imposé, les deux contrôles ayant passé au pas 4,0.

1. **TD(0) par pas n'apprend pas la composition différée à D=1** (0,190 vs référence
   0,163, 1/12) **alors qu'il apprend la même tâche sans délai** (0,503,
   12/12) : la réponse connue négative de l'ADR-005 est MESURÉE, avec son contrôle. Ce que TD(0) ne fait pas, c'est
   transporter la récompense du pas 1 vers l'ÉCRITURE de key au pas 0 — `H_in` est détaché dans `_td_update`, le
   gradient s'arrête à la lecture de l'état porté ; la lecture d'une projection aléatoire de key ne suffit pas à
   cette dose.
2. **La trace d'éligibilité transporte du crédit vers le pas encode** : +0,063, 12/12 seeds, séparation totale.
   Le mécanisme est celui de la formule : `e_a` porte ∂logπ(a₀|s₀)/∂θ et `e_v` porte ∂V(s₀)/∂θ jusqu'à la mise à
   jour du pas 1 ; comme W est partagé entre la lecture au pas 0 et l'écriture de H₁, une récompense au pas 1
   modifie l'encodage de key. C'est un crédit de type REINFORCE vers la représentation, sans BPTT — faible
   (0,253 contre 0,807 pour le BPTT et 0,503 pour la même
   tâche sans délai), mais non nul, et mesuré contre sa référence appariée.

Pour le registre de pièces (ADR-005, ligne `eligibility_trace_credit`, `without: λ=0`) : la ligne obtient son
**billet à deux issues mesurées** — TD(0) échoue ET λ>0 fait mieux — sur `CompositionTask(same_tick=False)`.

## Portée — ce que ce record N'ÉTABLIT PAS

- **Pas d'invariance au pas (E19)** : l'effet n'est visible qu'à `lr` 4,0 ; à 8,0 les contrôles eux-mêmes tombent.
  La clause scellée dit « à l'un des deux pas » ; le lecteur doit savoir que l'autre pas est hors régime, pas
  contradictoire. Un troisième pas (2,0) et un balayage de λ sont le R1 naturel.
- **Pas de composition** : 0,253 est loin de 0,5 et de la barre de [[EDR-BILINEAR]] ; la trace
  déplace, elle ne débloque pas. Aucune extrapolation au monde (P1.6 reste la QUALIFICATION in-world : no-op exact,
  non inerte, non dégradante, E19 — pas le lieu d'une issue positive).
- **Traces remises à zéro à chaque épisode** (épisodique) : le régime continu (pas de reset, « immortel veut dire
  immortel ») n'est pas mesuré ici ; `reset_traces` est une option comptée, jamais un défaut.
- **Un seul substrat** (bilinéaire rang 16) et **un seul délai** (D=1). Le plain ne peut pas servir à ce budget (E1,
  mesuré).
- Le contournement d'Adam n'a pas été exercé (SGD pur) ; `_td_update_trace` REFUSE sous gate/ANTISAT et sous un
  optimiseur à état sauf demande explicite.

## Registre

- **E1** (un bras qui ne peut pas réussir) : évitée deux fois par la fumée — substrat plain incapable à ce budget ;
  chemin TD inerte sous `lr` 0,4. La règle qui en sort : **un contrôle positif par MAILLON** (substrat ET chemin de
  crédit), pas un seul contrôle positif « la tâche est apprenable ».
- **E11** : toutes les fumées seed 0 sont déclarées dans la règle et exclues du n.
- **E19** : les deux pas sont mesurés et publiés ; l'un est hors régime — dit, pas avalé.

Converge [[EDR-CALIB-LEARNER]] (la dose se publie à côté de tout nul), [[EDR-LOCK-002]], [[EDR-RETAIN-COMPOSE-LR]],
[[EDR-BILINEAR]].
