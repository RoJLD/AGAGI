---
id: EDR-S2-011
type: EDR
title: "Le crédit à froid échoue MÊME sur une tâche de perception LINÉAIRE (confound représentation retiré) ; test warm-start confondu"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
S2-010 : le crédit in-world n'apprend pas la nourriture cognitive (tâche 2-bits). Mais le décode 2-bits
(`2*(a>0)+(b>0)`) est difficile à représenter/apprendre (croisé, tanh) → S2-010 confond REPRÉSENTATION et
CRÉDIT. Deux questions propres : (1) sur une tâche LINÉAIREMENT représentable, le crédit apprend-il ?
(2) un bassin de POIDS pré-formé (warm-start) est-il retenu ? (test de la loi warm-start).

## Méthode
Variante `cog_linear` (config + world_1 guardé, défaut OFF) : signal 1-bit `dir = int(bit_a>0) ∈ {0,1}`,
LINÉAIREMENT décodable (chaque direction = un poids signé sur bit_a). Régime dur (metab=0.75, cog_gain=12).
`tools/cognitive_demand_inworld.py` : `LinearCognitiveOracle` (dir=int(obs[:,12]>0)), `_bc_clone_linear`
(behavioral cloning de l'oracle dans la politique torch via `_step`, sync → genome.W), `run_credit_linear`
(cohorte fraîche COLD vs BC-warmstartée, use_torch_inworld, 6 ères persistées).

## Résultats

| condition | survie médiane | lecture |
|---|---|---|
| oracle linéaire (sanity) | **200** (cap) | régime correct, tâche résoluble, mapping linéairement représentable |
| plancher no-perception | ~7-8 | référence |
| **COLD** (crédit, fraîche) | **8** (plate /6 ères) | le crédit à froid n'apprend PAS la tâche linéaire |
| WARM (BC acc=1.00) + crédit | 9 | plancher |
| **WARM (BC acc=1.00) SANS crédit** | **8** (diagnostic) | **le bassin BC ne transfère PAS au forward du monde** |

## Verdict — un finding VALIDE, un test CONFONDU
**(1) VALIDE — `COLD_CREDIT_FAILS_ON_LINEAR_TASK`** : sur une tâche où un suiveur-de-signal survit
trivialement (oracle 200) ET dont le mapping est linéairement représentable (BC acc 1.00 le prouve), le
crédit in-world à froid **échoue toujours** (~8, plancher). **Ça RETIRE le confound représentationnel de
S2-010** : le verrou crédit n'est PAS un simple manque de capacité de décodage — même la perception
linéaire n'est pas apprise par REINFORCE in-world à froid. Durcit le fil « verrou = crédit means→ends ».

**(2) CONFONDU — le warm-start n'a PAS testé la rétention** : le BC atteint acc 1.00 sur `_step(obs, H=0)`
(single-step) mais la cohorte warm-startée survit seulement 8 **même SANS crédit** → le bassin BC ne
transfère pas au forward RÉCURRENT du monde (H accumulé sur les ticks + gate + pipeline). Le bras « warm »
ne mesure donc PAS « le crédit retient-il un bassin ». Question OUVERTE.

## Prochain pas précis (le vrai test warm-start)
Warm-starter avec un BC qui MATCHE le forward récurrent : cloner l'oracle sur des ROLLOUTS réels (séquences
(obs_t, H_t, action_t) générées par l'oracle in-world), pas sur `_step` à H=0. Vérifier d'abord que le
warm-start transfère (survit SANS crédit ~200), PUIS activer le crédit → retient/dégrade ? Alt : warm-start
par évolution courte in-world (optimiseur capable), ou init directe de genome.W validée in-world.

## Portée
`cog_linear` = infra réutilisable (isole crédit vs représentation). Le finding (1) est solide ; (2)
documenté comme confondu (ne pas citer de verdict de rétention). Converge S2-009/010, REF-DEMAND-MARKER,
[[decisive-substrate-thesis-test]] (verrou=crédit), [[warm-start-transversal-law]] (test à finir).
