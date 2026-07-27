---
id: CALIB-SP3
type: EDR
title: "Le demand-marker récupère un DAG de prérequis imposé et garde sa spécificité sous confond corrélé (os-taxonomy comme clé de réponse) — GO pour SP-2"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER]
---

## Question
SP-2 (peupler un graphe de capacités par ablation) suppose que l'ablation within-subject récupère un DAG
de prérequis. Cet instrument, calibré (P2.4) sur un monde à UN canal sans confond, tient-il sur un DAG
avec structure de CORRÉLATION (prérequis partageant un ancêtre) ? os-taxonomy fournit la forme ; on l'impose
dans un monde-jouet analytique (A1) dont la réponse est connue par construction.

## Méthode
Sous-graphe au format os-taxonomy : B a un prérequis DUR (Ah) et MOU (As) ; Aprime est un NON-prérequis
corrélé à Ah via l'ancêtre partagé Z. Monde-jouet : acquisition de B gatée (`income + hard_w·eff(Ah) +
soft_w·eff(As)`), transfert d'ancêtre pour fabriquer la corrélation. Ablation within-subject chirurgicale
de chaque prérequis candidat → `ablation_verdict` (n=12 seeds, métrique VIVANTE, `intervention_verified`).

## Résultat
GO. Prérequis dur récupéré (X_DEMANDED, ratio 2.42) ; non-prérequis corrélé INERTE (X_DECOY, ratio 1.00) ;
monotonie dur > mou > non-arête ; précision=rappel=1.0. Contraste gravé : une ablation par l'ANCÊTRE Z
faux-positive (X_DEMANDED) — la spécificité n'est PAS automatique, elle exige d'ablater le bon canal.

## Portée (bornée)
A1 démontre que la CORRÉLATION seule ne fait pas faux-positiver une ablation chirurgicale. L'aliasing de
SUBSTRAT (représentation partagée) est HORS de portée de A1 (pas de substrat partagé) → reste à vérifier en
SP-2 sur le substrat réel. Le contraste ancêtre montre le mode d'échec à éviter.

## Ce que ça débloque
SP-2 peut peupler le graphe de capacités par ablation within-subject, à condition d'ablater chirurgicalement
(pas par un ancêtre partagé). Cf. `docs/superpowers/specs/2026-07-23-sp3-prerequisite-recovery-calibration-design.md`.
