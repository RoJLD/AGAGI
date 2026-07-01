---
id: EDR-116
type: EDR
title: Transfert soup->stoneage NEUTRE sous puissance (G1 north-star) — la competence ne generalise pas
status: refuted
gate: G1
tests: [SDR-G1]
verdict: NEUTRE
---

# EDR 116 : Le transfert soup→stoneage est NEUTRE sous puissance (G1, north-star)

## Contexte

Porte **G1** du fil directeur AGI (`SDR-G1`, north-star = généralisation zéro-shot). G0 (EDR 112) a
validé que stoneage et soup EXIGENT l'intelligence ; G0 a aussi révélé que le répertoire-monde du
curriculum est dégénéré (agricultural VOID, industrial = stoneage-déguisé) → **soup et stoneage sont les
seuls mondes réels distincts**. Question : évoluer en soup d'abord améliore-t-il la compétence finale en
stoneage vs tabula-rasa-stoneage, à BUDGET COMPUTE ÉGAL ? Si oui, la compétence **généralise** à travers
l'écart d'abstraction (sensorimoteur → outils).

## Méthode

Instrument préexistant `tools/curriculum_transfer.py` (inchangé), soup câblé dans `WORLD_FACTORY`
(commit d62021d, test de compatibilité d'interface vert). Deux bras appariés par seed, budget égal :
curriculum `[soup, stoneage]` (graduation soup → import champion → stoneage) vs tabula-rasa `[stoneage]`
sur le même `total_eras`. `metric=survival` (médiane des âges, EDR 085), `deterministic=True` (mémoire
ambiante stoppée avant la boucle → reproductible). `ratio = C_curr / C_tabula`. Échelle : 20 agents,
150 ticks, max_eras=8. **n=8 seeds** (étendu de 3 après que le signal initial se soit révélé non
significatif — Commandement 15, powerer avant de conclure).

## Constat — NEUTRE (le signal de 3 seeds s'évapore sous puissance)

| n | médiane ratio | favorables | sign_p | verdict |
|---|---|---|---|---|
| 3 seeds (initial) | 1.262 | 2/3 | 1.000 | (label brut « TRANSFERE », trompeur) |
| **8 seeds (powered)** | **1.026** | **4/8** | **1.000** | **NEUTRE** |

Ratios par seed (n=8) : **1.50, 1.26, 0.55, 1.08, 1.24, 0.93, 0.66, 0.98** (moyenne 1.023). Dispersés
autour de 1.0, aucune direction consistante. **Le curriculum soup-first ne bat PAS le tabula-rasa
stoneage à budget égal : la compétence ne généralise pas de soup vers stoneage.**

> ⚠️ Le label brut de `compute_transfer_verdict` à 3 seeds était « TRANSFERE » (médiane > bande neutre,
> en IGNORANT `sign_p`). 6ᵉ occurrence du motif « signal qui s'évapore sous puissance » du projet
> (EDR 057/075/077/082/083). Jugé sur `sign_p`, pas sur le label.

## Caveats (honnêteté)

1. **Moteur partagé** : `SoupWorld` hérite de `Biosphere3D` (soup = stoneage avec craft/gros-gibier OFF).
   Le transfert traverse un écart de *features* (simple→complexe), pas deux moteurs indépendants — mais
   G0 a prouvé des dynamiques distinctes (soup δ=0.97 vs stoneage δ=0.92). Un NEUTRE *ici* (mondes
   pourtant proches, même moteur) est un signal **fort** : si la compétence ne transfère même pas entre
   deux configs du même moteur, elle ne transférera pas entre mondes plus éloignés.
2. **Échelle modérée** : 20 agents, 150 ticks, n=8 (contrainte compute, garde-fou SCIENCE.md). sign_p=1.0
   (4/8) est franchement non significatif — pas un cas limite — donc robuste à l'échelle.
3. **Métrique survie** : `survival_competence` (le signal autel/outil étant nul, EDR 014/096).

## Conséquences

- **G1 (north-star) NON franchie** : `SDR-G1` reste `open`. La compétence ne généralise pas entre les 2
  seuls mondes réels.
- **Mesure de transfert DIRECTE** (et non plus inférée comme EDR 105/108/110/113) confirmant le verrou :
  **le répertoire-monde / substrat est le goulot**. Convergence désormais surdéterminée par 6 chemins
  indépendants (sélection, dose diversité, capacité réseau, horizon de crédit, sélection diverse, ET
  transfert direct).
- **Pivot justifié** : la prochaine piste à plus fort levier n'est PAS un meilleur curriculum ni un
  meilleur apprentissage, mais **enrichir une affordance du monde** (créer un 2ᵉ monde genuinement
  distinct, pas une config du même moteur) — puis re-mesurer le transfert. Rejoint l'axe gradient/torch
  (ADR-003) comme *second* levier d'apprentissage, mais le substrat reste premier.
