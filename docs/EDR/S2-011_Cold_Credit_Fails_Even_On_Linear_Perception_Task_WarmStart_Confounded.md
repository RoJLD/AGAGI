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

> ⚠️ **TABLEAU RE-MESURÉ le 2026-07-21 (dette P2.8, ouverte par [[EDR-AUDIT-001]]).** Deux de ces cinq
> lignes n'avaient **aucun chemin d'exécution committé** : `LinearCognitiveOracle` était du **code mort**
> (aucun appelant) et `run_credit_linear` codait `use_torch_inworld = True` **en dur**, donc le bras
> « sans crédit » n'existait pas. Les chemins sont livrés (`run_linear_sanity`, `use_credit=`), les
> chiffres mesurés ci-dessous, et 5 tests posés dont deux régressions anti-code-mort.

| condition | publié | **RE-MESURÉ (K=12)** | lecture |
|---|---|---|---|
| oracle linéaire (sanity) | 200 (cap) | **200.0** ✅ | **CONFIRMÉ** — ratio 14.81 vs son ablation, `X_DEMANDED`, n=12, censuré. La tâche est résoluble et le monde exige bien la perception : le contrôle positif du finding (1) est désormais RÉEL. |
| plancher no-perception | ~7-8 | **13.5** ❌ | **FAUX — importé du régime 4-directions (classe E8).** Avec `dir ∈ {0,1}` on tombe juste **une fois sur deux** par accident, pas une sur quatre : le plancher de CETTE variante est structurellement plus haut. |
| **COLD** (crédit, fraîche) | 8 | **7.5** ✅ | reproduit |
| WARM (BC acc=1.00) + crédit | 9 | **8.0** ✅ | reproduit |
| **WARM (BC acc=1.00) SANS crédit** | 8 | **7.5** ✅ | reproduit (bras désormais exécutable) |

> **Ce que le plancher corrigé change.** Les trois bras de crédit (7.5 / 7.5 / 8.0) ne sont pas « au
> plancher » : ils sont **45 % SOUS le plancher aveugle (13.5)**. Une cohorte qui apprend survit donc
> *moins bien* qu'un oracle privé de son signal.
> ⚠️ **Ne PAS en conclure « le crédit est nuisible »** : l'oracle est un `BaselineBatchModel`, les bras
> de crédit sont des `MambaAgent` sous `use_torch_inworld` — **substrats différents, comparaison
> BETWEEN-subject**, précisément le faux ami documenté par S2-001.
>
> ✅ **TRANCHÉ le 2026-07-21 (P2.9) — l'hypothèse « coût propre du substrat torch » est RÉFUTÉE.**
> Contraste within-subject sur le SEUL axe substrat (même cohorte fraîche, même monde, même seed, on
> bascule `use_torch_inworld`) : **ON = 7.2, OFF = 7.0** (ratio 0.97, 6 ères). Basculer le chemin torch
> ne change rien. L'écart avec le plancher oracle-ablé (13.5) est donc une différence de **POLITIQUE**,
> pas de substrat : un oracle au signal brouillé émet quand même une direction DÉCISIVE à chaque tick
> (juste une fois sur deux par construction en 1-bit), là où un `MambaAgent` à poids aléatoires fait
> moins bien. **« Aveugle mais décidé » bat « aléatoire ».**
> **Conséquence : le finding (1) en sort RENFORCÉ** — la cohorte froide n'apprend réellement pas, et
> aucun artefact de substrat ne vient l'excuser. Formulation correcte : « COLD est sous le repère
> oracle-ablé », et non « COLD est sous le plancher », qui suggérait un défaut de banc.

## Verdict — un finding VALIDE, un test CONFONDU
**(1) VALIDE, et RENFORCÉ par la re-mesure — `COLD_CREDIT_FAILS_ON_LINEAR_TASK`** : sur une tâche où un
suiveur-de-signal survit trivialement (**oracle 200, désormais MESURÉ** : ratio 14.81, `X_DEMANDED`,
n=12) ET dont le mapping est linéairement représentable (BC acc 1.00 le prouve), le crédit in-world à
froid **échoue toujours** (7.5). **Ça RETIRE le confound représentationnel de S2-010** : le verrou crédit
n'est PAS un simple manque de capacité de décodage — même la perception linéaire n'est pas apprise par
REINFORCE in-world à froid. Durcit le fil « verrou = crédit means→ends ».

> ⚠️ **Une formulation à ne plus employer** : « ~8, **plancher** ». Le plancher réel de cette variante est
> **13.5** (mesuré), pas 7-8 (importé). COLD n'atteint donc pas le plancher — il est **dessous**. Le
> finding tient (le crédit n'apprend pas), mais son repère était faux, et l'écart pointe vers une
> question NEUVE, non tranchée ici : le substrat torch in-world a-t-il un coût propre ? Cf. le bandeau
> du tableau (comparaison between-subject — piste, pas causalité).

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
