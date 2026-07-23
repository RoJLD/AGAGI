---
id: CALIB-ALIAS
type: EDR
title: "L'ablation within-subject est chirurgicale sur un substrat DISJOINT (no-op exact) mais fuit sur un substrat PARTAGÉ — nouveau garde assert_no_functional_aliasing, aveugle-point de np.shares_memory comblé"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
---

## Question
CALIB-SP3 (GO) a validé l'ablation within-subject en A1 SANS substrat partagé, et a différé l'aliasing de
substrat à SP-2. Sur le vrai chemin récurrent où deux capacités partagent des neurones, ablater X pour
mesurer « Y demande X ? » peut effondrer Y par la représentation partagée — un faux positif. Le garde
existant `assert_no_aliasing` (np.shares_memory) n'attrape que l'aliasing de mémoire-vue (EDR-WARM-007),
pas l'aliasing FONCTIONNEL.

## Méthode
Génome câblé à la main injecté dans le VRAI `recurrent_forward` : X (in0→hA→out_X), Y (in1→hB→out_Y), fuite
dosée X→hS→α·out_Y. Ablation chirurgicale mono-canal (colonne d'entrée → 0), K=4 ticks de stabilisation.
Déterministe → no-op EXACT (bit-identique), pas statistique.

## Résultat
GO. Disjoint (α=0) : leakage 0.0000 EXACT (out_Y bit-identique) — SURGICAL — pendant que out_X chute (0.466,
ablation non vacuse). Partagé (α=1) : leakage 0.2532 — FUNCTIONAL_LEAK. Monotone en α (0 / 0.099 / 0.177 /
0.253). **Contraste gravé** : sur le partagé, np.shares_memory est False → `assert_no_aliasing` PASSE
(aveugle) alors que le nouveau `assert_no_functional_aliasing` TIRE. Le point-aveugle structurel est comblé.

## Portée (bornée)
Établit que l'ablation within-subject EST fonctionnellement isolable QUAND les capacités sont séparables, et
qu'un contrôle comportemental sur une capacité indépendante détecte la non-séparabilité. L'APPLICATION à un
MambaAgent ÉVOLUÉ réel (câblage appris, non contrôlable) reste SP-2. La correction du `.clone()` conditionnel
par défaut de `TorchPopulationModel.forward` (aliasing mémoire-vue encore actif) = dette séparée.

## Ce que ça débloque
SP-2 mesuré dispose d'un garde de spécificité opposable : avant de conclure « Y demande X » d'une ablation,
`assert_no_functional_aliasing` sur une capacité de contrôle indépendante. Cf.
`docs/superpowers/specs/2026-07-23-substrate-functional-aliasing-calibration-design.md`.
