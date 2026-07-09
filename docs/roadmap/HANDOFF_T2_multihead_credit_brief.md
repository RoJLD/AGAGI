# Brief T2 — Crédit multi-tête par équilibrage (lr-par-tête / GradNorm-lite), PAS l'architecture

> Élabore la cible **T2** de [`HANDOFF_TORCH_READOUT_CREDIT.md`](HANDOFF_TORCH_READOUT_CREDIT.md).
> Vérifié 2026-07-02 : aucune session parallèle sur lr-par-tête/GradNorm (arc disjoint CLOS, PR #136).
> **Priorité 3** (après T1 NAV, T3 BIND). Honnêteté : le jalon décisif est le PROXY ; le port prod est
> un HEDGE à payoff incertain — voir §Payoff.

## Objectif (une ligne)

Si le bénéfice multi-tête doit exister en prod, l'obtenir par **équilibrage de crédit** (lr-par-tête ou
GradNorm-lite loss-scale) dans le connectome PLAT — **PAS** par split architectural (#5, réfuté).

## Preuve (ce que l'arc disjoint a établi)

- **EDR 152** : DISJOINT aide, mais cos-conflit ≈ 0 → interférence RÉFUTÉE ; le gain = conditionnement
  d'optim par-tête, pas l'isolation architecturale.
- **EDR 153** : FLAT_NORM (plat, 1 Adam, **équilibrage d'échelle de loss GradNorm-lite**) recouvre **79 %**
  du gain disjoint → borne l'archi ≤ 21 %. **Migration #5 réfutée comme levier.**
- **EDR 154** : FLAT_PERHEAD (plat, **3 Adam = moments séparés**, sans échelle) recouvre **73 %** ≈ échelle
  → le résidu n'est pas proprement les moments. **lr-par-tête N'A PAS été testé isolément** (le caveat).
- **EDR 191** : sous pression de capacité (H petit), le crédit plat **DÉPASSE** disjoint (recovery > 1) ;
  l'avantage disjoint d'origine était de la **sur-capacité** (à H=6, disjoint NUIT). → « crédit pas archi »
  robuste à l'interférence, ET le payoff multi-tête lui-même dépend du régime de capacité.

## Jalon M1 — PROXY : fermer le caveat lr-par-tête ✅ FAIT (EDR-COG-001)

Bras **FLAT_PERHEAD_LR** livré (`tools/disjoint_heads_v4.py`) : 1 Adam à groupes, lr propre par **readout**
(trunc au lr de base), moments uniques, sans échelle. Comparé à FLAT_NORM (153) et FLAT_PERHEAD (154) sur
mêmes seeds/init/données. **RÉSULTAT (K=5, déterministe) : lr-par-tête recouvre −0.16 → LR_INSUFFICIENT**
(échelle 0.79 / moments 0.73 reproduits). → **NÉGATIF INFORMATIF** : rééchelonner les lr des readouts NE
recouvre PAS (nuit même). L'équilibrage qui recouvre (153/154) agit sur le **gradient du TRONC partagé**,
pas les têtes de lecture → le « crédit pas archi » se précise en **« crédit sur le tronc partagé »**.
**Conséquence pour M2 : NE PAS porter lr-par-tête** ; porter l'échelle de loss (GradNorm-lite, 153).

## Jalon M2 — PORT PROD : GradNorm-lite dans `backend_torch` *(hedge, flag OFF)*

Mécanisme prouvé le plus simple (EDR 153, 79 %) = **équilibrer les magnitudes des composantes de loss
par tête**. Dans `TorchPopulationModel._td_update` :
```
# têtes prod : actor-move (log_softmax), grab (BCE), rub (BCE), critic-value (MSE)
# loss actuelle : actor_loss + 0.5*critic_loss
# GradNorm-lite (flag OFF) : normaliser chaque composante à une échelle unité (ou par ||grad|| par tête)
if self.gradnorm_lite:                      # défaut False -> byte-identique
    comps = [actor_move, grab_bce, rub_bce, critic]
    loss = sum(c / (c.detach().abs() + eps) * w_head for c, w_head in zip(comps, weights))
else:
    loss = actor_loss + 0.5 * critic_loss   # inchangé
```
~~Alternative (lr-par-tête)~~ : **RÉFUTÉE par M1/EDR-COG-001** (lr-par-readout recouvre −0.16, nuit).
GradNorm-lite sur l'échelle de loss est le mécanisme à porter (agit sur le tronc partagé, prouvé 79 %).
NB : `critic` (value) ici lit le tronc partagé — l'équilibrer via l'échelle de loss touche bien le
gradient du tronc, conforme au mécanisme validé (COG-001).

## Payoff (honnêteté)

Le bénéfice prod est **incertain** : EDR 191 montre que l'avantage multi-tête était de la sur-capacité
(à faible capacité, disjoint NUIT). **Avant d'investir M2, définir un métrique prod multi-tête** (ex.
compétence per-type : action + référentiel EDR 074 + value, sur un banc où les têtes se font concurrence).
Sans ce métrique, M2 est un hedge non mesurable → **ne pas prioriser M2 tant que le métrique n'existe pas**.
M1 (proxy) reste valable seul : il ferme proprement l'arc disjoint.

## Critères de succès

1. **M1** : `recovery(FLAT_PERHEAD_LR)` ≈ 0.73-0.79 (± comme échelle/moments) sur K≥5 seeds → CREDIT_ROBUST.
2. **M2** (si métrique défini) : le métrique multi-tête prod sous `gradnorm_lite=True` ≥ baseline flat
   1-optimiseur ; non-régression `gradnorm_lite=False` byte-identique.

## Coordination & garde-fous

- **Ownership** : M1 = tooling (`tools/disjoint_heads_v3.py`, ownable seul). M2 = `backend_torch` (session
  torch), flag OFF. **Ne PAS** ré-introduire le split archi #5 (réfuté 153) ni toucher l'encodeur.
- **Non-collision** : distinct de T1 (readout NAV) et T3 (crédit épisodique BIND in-world, en cours sur
  `feat/d1-prod-pairing`). T2 = équilibrage de crédit MULTI-TÊTE sur le pas d'apprentissage.

Lignée : EDR 152→154 (crédit pas archi) + 190-191 (robuste sous interférence) → ce brief.
