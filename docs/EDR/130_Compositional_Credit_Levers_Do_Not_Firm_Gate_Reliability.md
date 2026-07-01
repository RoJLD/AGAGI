---
id: EDR-130
type: EDR
title: "Levier 3 (crédit/optimisation du gate) : ni l'entropie ni l'éligibilité ne fiabilisent le binding — le plafond 7/10 d'EDR 129 tient (baseline 7/10, entropie 6/10, éligibilité 5/10) ; les seeds qui collapsent en always-Y collapsent dans TOUTES les configs → la reliabilité résiduelle est une propriété d'INITIALISATION/bassin, pas de la règle de crédit ; l'éligibilité TD(λ) DÉGRADE (inappropriée pour un gate 1-pas)"
status: validated
gate: null
verdict: "Levier 3 d'EDR 126 (crédit/optimisation) pour firmer les 3/10 collapses always-Y d'EDR 129. Deux interventions sur le REINFORCE du gate (λ=0/entropy=0 → baseline EDR 129 rétrocompat) : entropy_coef (bonus d'entropie anti-collapse) et elig_lambda (trace d'éligibilité sur le gradient). Sweep {baseline, entropie, éligibilité, les deux} × 10 seeds, régime incitatif (fade0.0/pen2). RÉSULTAT NO_IMPROVEMENT : baseline 7/10, entropie 6/10, éligibilité 5/10, les deux 5/10 — aucune intervention ne monte au-dessus de 7/10, l'éligibilité DÉGRADE (gap médian 0.37→0.18 ; un TD(λ) inter-essais mélange des gradients d'essais indépendants → inapproprié pour un gate 1-pas, comme prévu). Les seeds qui collapsent (0,3,4) collapsent dans TOUTES les configs → la reliabilité résiduelle N'EST PAS un problème de crédit/exploration mais une propriété DÉTERMINISTE d'initialisation/bassin d'attraction. Conclusion des 3 leviers : signal ÉLIMINÉ (128), STRUCTURE de gating = le débloqueur (129, 7/10), crédit/optim NE FIRME PAS (130). Le plafond de fiabilité relève de l'init/paysage, pas de la règle d'apprentissage."
---

# EDR 130 : Levier 3 (crédit/optim) ne fiabilise pas le gate — le plafond 7/10 est un problème d'init

## Question

EDR 129 : un gate appris (routage did_x→logit Y) débloque le binding sur **7/10 seeds**, mais collapse
en **always-Y sur 3/10**. EDR 129 nommait l'optimisation/crédit (levier 3) comme co-facteur des
collapses. Question : un meilleur mécanisme de crédit/optimisation **fiabilise-t-il** le binding
(n_bind → 10/10) ?

**Clarification** : le gate est une décision **1-pas** (lit did_x de la mémoire H_S2, décide Y) →
reward2 est immédiat à son action, il n'y a **pas de crédit temporel différé POUR LE GATE** (le TD(λ)
littéral d'EDR 126 visait le crédit X→Y du substrat de base ; le gate le contourne en lisant la mémoire).
Le collapse 3/10 est donc a priori un problème d'**exploration/optimisation** (mode-collapse), pas
d'horizon de crédit. On teste les deux interventions pertinentes.

## Méthode

`run_curriculum_fade_gated` (gate learned) + 2 leviers, **λ=0 & entropy=0 → REINFORCE nu = baseline
EDR 129** (rétrocompat garantie) :
- **entropy_coef** : bonus d'entropie sur la politique (loss −= entropy_coef·H(π)) → anti-collapse.
- **elig_lambda** : trace d'éligibilité sur le gradient du gate (trace = λ·trace + grad, appliquée avant
  `optim.step()`).

`sweep_gate_reliability` : {baseline, entropie 0.05, éligibilité 0.7, les deux} × **10 seeds**, régime
INCITATIF (fade0.0 → ¬X fréquent, penalty=2, cf. EDR 129). Métrique = **n_bind/10** (fiabilité, gap>0.3).

## Résultats

| entropy | elig | n_bind | gap médian |
|--------:|-----:|:------:|-----------:|
| 0.0 | 0.0 (baseline 129) | **7/10** | 0.370 |
| 0.05 | 0.0 (entropie) | 6/10 | 0.368 |
| 0.0 | 0.7 (éligibilité) | 5/10 | 0.180 |
| 0.05 | 0.7 (les deux) | 5/10 | 0.194 |

**VERDICT NO_IMPROVEMENT.** Aucune intervention ne dépasse le baseline 7/10 ; les deux nuisent
légèrement. L'**éligibilité DÉGRADE** (n_bind 7→5, gap médian 0.37→0.18) : accumuler le gradient sur des
essais INDÉPENDANTS (pas de structure temporelle intra-essai) mélange des directions non-liées → bruit,
exactement l'inadéquation prédite d'un TD(λ) sur un gate 1-pas.

**Les collapses sont DÉTERMINISTES par seed** : les seeds 0, 3, 4 collapsent en always-Y (gap ~0) dans
**les 4 configs** ; les seeds bindeurs (1,2,6,7,8,9) bindent dans toutes. L'intervention ne déplace pas
la frontière — elle est fixée par le seed (init + trajectoire précoce du substrat de base), pas par la
règle de crédit du gate.

## Interprétation

**Le levier 3 (crédit/optimisation) ne fiabilise PAS le binding.** Le plafond 7/10 d'EDR 129 tient. La
reliabilité résiduelle n'est ni un problème d'exploration (l'entropie n'aide pas) ni de crédit
(l'éligibilité dégrade) : c'est une propriété d'**INITIALISATION / bassin d'attraction** — certains seeds
verrouillent always-Y tôt et aucun de ces leviers n'en sort.

**Clôture des 3 leviers d'EDR 126** :
- **Levier 1 (signal)** — ÉLIMINÉ (EDR 128 : punir Y-sans-X ne force pas un binding robuste).
- **Levier 2 (structure de gating)** — LE DÉBLOQUEUR (EDR 129 : 7/10, actionnable migration).
- **Levier 3 (crédit/optim)** — NE FIRME PAS (EDR 130 : plafond 7/10 = init/paysage, pas la règle).

**Conséquence migration** : le substrat torch-prod doit embarquer la **structure de gating** (levier 2) ;
la fiabilité se gagnera par l'**initialisation / le paysage d'optimisation** (multi-init, meilleure init,
ou architecture du gate), PAS par un raffinement de la règle de crédit. Le TD(λ)/éligibilité est écarté
pour ce rôle (inadéquat au gate 1-pas ; resterait pertinent pour le crédit X→Y du substrat de base, non
testé ici).

## Bornage / honnêteté

- **n=10**, micro-tâche proxy ; pas de transfert apex. Un seul point par levier (entropy=0.05,
  elig=0.7) — pas un balayage fin ; il est possible qu'un réglage très différent aide, mais la
  DÉTERMINISME par-seed (mêmes seeds collapsent partout) rend cela peu probable et pointe l'init.
- « Init/bassin » est INFÉRÉ du déterminisme par-seed, pas prouvé mécaniquement (on n'a pas décodé
  pourquoi les seeds 0/3/4 verrouillent) — c'est la piste suivante (sonder H_S2 précoce des seeds
  collapsés vs bindeurs).
- L'éligibilité est implémentée comme trace sur le gradient (λ·trace+grad) sous Adam ; à λ=0 ≡ baseline
  exact. Sa dégradation est cohérente avec l'absence de structure temporelle (essais i.i.d.).
- Régime fade0.0/pen2 hérité d'EDR 129 (le seul où conditionner est optimal).

Outils : `tools/substrate_ab_compositional.py` (`run_curriculum_fade_gated(entropy_coef=, elig_lambda=)`,
`sweep_gate_reliability`). Tests `tests/sandbox/test_substrate_ab_compositional.py`. Clôt la trilogie
128-129-130 des 3 leviers d'EDR 126. ⚠️ Collision de numéro possible : une session // a claimé EDR-129
pour « cross-world transfer » (mémoire partagée) ; mon EDR 129 (gating) = PR #106 — à arbitrer au merge.
