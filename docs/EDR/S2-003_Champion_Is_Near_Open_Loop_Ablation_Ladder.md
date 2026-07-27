---
id: EDR-S2-003
type: EDR
title: "La SURVIE du champion HoF est PERCEPTION-NEUTRE (son comportement, lui, ne l'est pas) — échelle d'ablation"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
S2-002 a montré `INWORLD_PERCEPTION_DECOY` sur 5 mondes (`within ≈ 1.0` : permuter la perception du
champion ne dégrade pas sa survie), avec une ambiguïté : **(a)** le champion IGNORE son entrée
(open-loop), ou **(b)** il l'utilise mais de façon SURVIE-NEUTRE. Trancher interroge G0.

## Méthode
`tools/s2_openloop_probe.py` : échelle d'ablations within-subject de sévérité CROISSANTE (world-agnostic,
via le seam `batch_model_cls` de `s2_demand.run_condition`, importé sans le modifier) —
intact / permuted (`PerceptionAblatedMamba`, obs d'un pair) / noise (`NoiseObsMamba`, bruit gaussien
apparié) / zero (`ZeroObsMamba`, obs nulle). Ratio par barreau = `ablation_verdict(intact.era_survival,
barreau.era_survival)["ratio"]` (apparié par ère). 3 mondes, seed=2026, K=12, agents=12, ticks=200.

**Portée du témoin — CRUCIALE :** ce ladder mesure la **SURVIE**. Il établit donc l'(in)dépendance de la
survie vis-à-vis de l'obs, PAS l'(in)dépendance COMPORTEMENTALE (est-ce que l'obs change l'action). Un
résultat « survie plate » ne peut PAS, seul, conclure « open-loop ».

## Résultats

| monde | intact_med | permuted | noise | zero | verdict outil |
|---|---|---|---|---|---|
| soup | 29.2 | 1.00 | 0.98 | 1.07 | OPEN_LOOP |
| stoneage | 27.5 | 0.99 | 1.22 | 1.28 | OPEN_LOOP |
| famine | 27.5 | 1.07 | 1.26 | 1.34 | MIXED |

**Aucun barreau, sur aucun monde, n'atteint le seuil d'effondrement (1.5×) — même l'obs NULLE.** Un
gradient monotone faible existe (permuted < noise < zero) et croît avec la dureté (famine → MIXED).
Note : le verdict `OPEN_LOOP` de l'OUTIL est un label sur la survie (« tous barreaux leurres ») ; il ne
faut PAS le lire comme un verdict comportemental (voir Réconciliation).

## Réconciliation avec l'effort parallèle (DÉCISIVE — tranche (a) vs (b))
Une session parallèle (`chantier/s2-ablation`, PR #165 mergée en main ; `ObsAblatedMambaBatchModel` câblé
DANS `s2_demand`) a mesuré, elle, le **COMPORTEMENT** via un contrefactuel par-tick (486 tick-mesures,
snapshot/restore du modèle + de l'état `np.random` autour d'un 2ᵉ forward sur obs décalée) :
**décorréler l'obs change ~29 % des mouvements du champion (argmax flip 0.294 ; logits rel-distance
0.357).** ⇒ Le champion **UTILISE l'obs, il ne l'ignore PAS — option (b), pas (a).** Ce n'est pas un
réflexe obs-aveugle : ~29 % d'influence perceptive + un socle ~71 % obs-indépendant.

Mon ladder de survie et leur contrefactuel comportemental **convergent et se complètent** :
- Survie (ce ladder) : perception-NEUTRE — même l'obs NULLE ne coûte pas de survie.
- Comportement (parallèle) : perception-DÉPENDANT à ~29 %.

## Verdict
**`PERCEPTION_SURVIVAL_NEUTRAL` (PAS open-loop).** Le champion perçoit et agit sur sa perception
(~29 % de ses mouvements en dépendent), mais **cet usage perceptif ne cash-out PAS en survie** : le
priver de toute information (obs nulle) ne l'effondre pas. Sa survie vient d'ailleurs — corps /
métabolisme / réflexe d'endurance (régime dur, cf. l'edge 4× métabolique du fil S2). Il « a l'air
intelligent » (traite l'obs) sans que la perception paie.

Conséquence pour G0 : le verdict between (« le monde exige l'intelligence », champion 4.7-5.2× le
réflexe) confond « survit bien » avec « sa perception est causalement porteuse de la survie ». Deux
témoins within-subject indépendants (survie ici, comportement en //) montrent que le second est faux.
Corrobore le fil « in-world NEUTRE » et la thèse substrat/crédit : ces mondes n'exigent pas de boucle
perception→survie au niveau où opère le champion.

## Portée & limites
- Labels de l'outil CORRIGÉS (`OPEN_LOOP`→`SURVIVAL_NEUTRAL`, `INPUT_SENSITIVE`→`SURVIVAL_SENSITIVE`) pour
  ne pas suggérer un verdict comportemental : le témoin mesure la SURVIE, pas le comportement. Chiffres
  inchangés.
- Claim sur le champion HoF COURANT, pas une preuve qu'aucun agent ne pourrait faire payer la perception.
- Ablation du flux égocentrique COMPLET (perception + proprioception) ; corroborant |W| indisponible (HoF).
- **Duplication assumée** : `chantier/s2-ablation` (câblé dans `s2_demand`, mono-monde + régime sweet +
  contrefactuel) et cette lignée (`demand_marker` + ladder standalone, 3 mondes, rung zéro) sont deux
  implémentations DISTINCTES et convergentes du même pont. Réconciliation au merge = affaire robla.

## Suite
Reco G0 : câbler une DEMANDE perceptive survivable (obs porte l'action nourricière/le danger) puis
re-mesurer survie + comportement — si le champion reste survie-neutre là, le verrou est le crédit, pas le
monde. Converge `REF-DEMAND-MARKER`, S2-001, S2-002, et l'arm câblé de `chantier/s2-ablation`.
