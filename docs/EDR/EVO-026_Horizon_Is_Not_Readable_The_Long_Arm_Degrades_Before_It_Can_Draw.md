---
id: EDR-EVO-026
type: EDR
title: "D2 — l'horizon n'est PAS lisible : le bras long se dégrade avant d'avoir assez tiré"
status: active
verdict: INCONCLUSIVE_BY_DEGRADATION_THE_SEAL_HELD
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-023]
---

## Question

La clôture de l'arc dit « le verrou est le TIRAGE ». **TIRAGE est ambigu**, et deux modèles expliquent
également bien *tout* l'arc en prédisant l'inverse à horizon long :

| modèle | énoncé | prédiction à 21× |
|---|---|---|
| **A — rareté combinatoire** | les tirages sont INDÉPENDANTS, l'échelle suffit | ~8/24 lecteurs |
| **B — non-accumulation** ([[EDR-EVO-010]]) | les tirages ne se composent pas | ~0-1/24, inchangé |

Règle scellée : `EVO-026-bis.json`, prédictions posées **avant** le run.

## Deux runs, dont un non lisible

**[[EDR-EVO-026]] première version — NON LISIBLE, et le crash valait mieux que le résultat.** Son bras
long a planté sur `LIMIT_N = 256` (`src/agents/mamba_agent.py:405`), le génome passant de 172 à ~300
nœuds en 735 ères. Le plantage a révélé un défaut **plus grave que lui** : les arêtes possibles vont en
**N²** (29 584 à N=172 → 65 536 à N=256), donc le bras long **accumulait des tirages tout en diluant
chacun d'eux ~2,2×**. La prédiction `1−(1−p)²¹` suppose *p* constant ; l'appareil ne le tenait pas. Sans
le crash, un nul aurait été lu « modèle B » alors qu'une part venait de la dilution — **classe E2**.
Son bras standard, lui, a terminé et vaut comme mesure : 0/12, saillance max 0.013.

**Version `-bis`, corrigée sur quatre points** : croissance de nœuds coupée dans les deux bras (N
constant → dénominateur fixe, plafond jamais atteint) ; *n* porté de 12 à 24 ; base de prédiction
**poolée sur tout l'arc** (~2-3 lecteurs / ~130 lignées → p ≈ 0.02) au lieu du seul « 1/12 » d'un run,
qui était une estimation sur l'observation la plus saillante (**classe E9**) ; trois contrôles de
manipulation mesurés **in situ** qui bloquent le verdict s'ils échouent.

## Résultats

DV primaire **telle que scellée** : `measure_decision_saliency` sur `obs[5] → logits[8]`, seuil 0.5 — la colonne « sal max » ci-dessous en est le maximum par bras, la colonne « lecteurs » le compte des seeds au-dessus du seuil. Le contrôle de manipulation compte les appels réels à `add_connection` (le TIRAGE étudié), instrumenté **dans les deux bras** : un compteur qui ne peut lire que zéro est la classe E4.

| bras | **lecteurs** | sal max | `raw` méd | **`age_fin` méd** | `N` méd | **tirages méd** | extinctions | abandons |
|---|---|---|---|---|---|---|---|---|
| standard (35 ères) | **0/24** | 0.000 | 0.501 | **7.0** | 172 | 447 | 0 | 0 |
| long (735 ères) | **0/24** | 0.000 | 0.504 | **4.0** | 172 | **9 508** | 0 | 0 |

**Les trois contrôles de manipulation PASSENT** : compteurs d'`add_connection` non nuls dans les deux bras (447 et 9 508) · ratio des tirages **21,3×**
(clause : [15, 27]) · `N` médian identique (172 contre 172, clause : écart ≤ 2). Le dispositif a fait
exactement ce qu'il annonçait. **Fisher exact bilatéral : p = 1.000.**

## Verdict

**`INCONCLUSIVE_BY_DEGRADATION_THE_SEAL_HELD`**

Un lecteur pressé conclurait « 0/24 contre 0/24 → **modèle B confirmé**, les tirages ne s'accumulent
pas ». **Ce serait une conclusion fabriquée.** La règle scellée impose de lire la santé de lignée avant
tout verdict nul : **7,0 → 4,0, soit 0,57× — sous le seuil de 0,70 posé d'avance**. Le bras long ne
pouvait pas réussir (**classe E2**) ; aucun modèle n'est départagé.

**Ce que ce run établit malgré tout**, et qui n'est pas rien :

1. **L'horizon délivre bien les tirages** — 21,3×, à dénominateur strictement constant. Le levier n'est
   pas en cause.
2. **Un horizon long DÉGRADE la lignée dans ce substrat.** La survie médiane de fin tombe de 43 % alors
   que la croissance de nœuds est coupée : ce sont donc `mutate_weights` et `prune` seuls qui érodent la
   lignée sur 735 ères. C'est un fait mesuré, et il contraint tout futur design : **on ne peut pas
   accumuler des tirages en profondeur dans ce substrat.**
3. La voie qui reste pour trancher A contre B : accumuler des tirages **en largeur** (beaucoup de
   lignées courtes) plutôt qu'en profondeur — la charge mutationnelle ne s'accumule alors pas.

## Ce qui a sauvé ce record

La DV de santé de lignée n'a pas été ajoutée par prudence rédactionnelle : elle a été déclarée parce que
le **smoke de débit** (`tools/evo_runs/evo025_throughput_smoke.py`) avait mesuré un coût par ère qui
**BAISSE** (×0,73 sur 60 ères, ticks-agent 319 → 158). Dans ce dépôt le coût suit le succès — un coût
qui baisse signale une lignée qui survit de moins en moins bien. Le confond a donc été écrit dans le
sceau *avant* le run, avec son seuil.

**Sans ce dimensionnement préalable, ce record affirmerait aujourd'hui « les tirages ne s'accumulent
pas ».**

## Portée (hedges)

* **n=24 par bras, puissance déclarée AVANT** : 8/24 contre 0/24 serait détectable (p≈0.002), 3/24 contre
  0/24 ne le serait pas (p≈0.23). Ce run ne peut pas réfuter une accumulation faible.
* La limite est posée dans le sceau : si la base réelle est plus proche de 0.005 que de 0.02, le modèle A
  ne prédit que ~2,5/24 et le run serait non concluant **même sans dégradation**.
* Mesuré sur la sous-tâche `throw`, `hazard=15`, `W=0`. Les deux bras tournent avec
  `preserve_io_blocks=True` ([[EDR-EVO-024]]) — sans effet ici puisque rien ne s'insère, conservé pour
  que la config soit identique en tout point sauf l'horizon.
* La dégradation est mesurée sur `age_fin` (médiane du dernier dixième des ères). Sa **cause** n'est pas
  établie : `mutate_weights` et `prune` sont les seuls opérateurs actifs, mais lequel érode n'a pas été
  isolé.

## Occurrences consignées au registre pendant ce run

* **E2** — le bras long de la première version ne pouvait pas réussir (dilution en N²).
* **E4 (forme silencieuse)** — un runner dérivé par regex a gardé le pré-vol d'[[EDR-EVO-023]] tout en
  annonçant celui d'EVO-024 ; il tournait et ne vérifiait pas ce qu'il prétendait.
* **E6 étendue aux CONTRÔLES** — un pré-vol appliquait 16 905 mutations cumulatives à un seul génome, un
  régime que le run ne visite jamais (`apply_mutations` clone). Un contrôle de manipulation doit
  s'exécuter dans le régime du dispositif ; les trois contrôles finaux sont donc mesurés **in situ**.
* **E10** — la suite de tests a été lancée pendant que ce run tenait le bail `kuzu`, faisant échouer
  4 tests monde. Vérifié après libération du bail : **les 4 repassent**, c'était bien la contention.
  Garde écrite dans la foulée (`tests/conftest.py`).

Converge [[EDR-EVO-010]], [[EDR-EVO-018]], [[EDR-EVO-023]], [[EDR-EVO-024]], REF-EXPERIMENT-PREFLIGHT.
