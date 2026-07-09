---
id: EDR-147
type: EDR
title: "Gate + BPTT combinés sur means→ends : le GATE craque le binding (réplique EDR-136), le no-gate jamais (réplique EDR-146), et BPTT N'AJOUTE RIEN — il DÉGRADE le gate (gap médian +0.307 tronqué → +0.005 bptt ; le crédit à travers le temps gonfle les MARGINALES au lieu de conditionner, hit_end MAXIMAL mais gap≈0). Converge avec « autograd-à-travers-la-récurrence déstabilise » (EDR-137/144 in-world) : gate + substrat TRONQUÉ = la recette de binding ; BPTT réservé aux tâches mémoire multi-pas (EDR-145)"
status: accepted
gate: null
verdict: GATE_BINDS_BPTT_DEGRADES_THE_GATE
---

# EDR 147 : Gate + BPTT — le gate binde, BPTT dégrade le gate (build coordonné annoncé en EDR-146)

## Contexte

Fin de trilogie de la migration torch côté binding. Deux résultats indépendants convergeaient :
- **EDR-146 (mien)** : BPTT SEUL (crédit à travers le temps, numpy-impossible) NE craque PAS le binding
  means→ends (binding_gap ≈ 0).
- **EDR-129/136 (fil compositional //)** : un GATE (readout de H_S2 → biais sur le logit Y, REINFORCE)
  + ANTI-SATURATION de la marginale de la politique de base craque le binding — MAIS sur leur substrat
  TRONQUÉ (leur `forward` détache H).

Reste la conjonction annoncée en EDR-146 : **BPTT apporte-t-il quelque chose AU gate** ? Hypothèse : BPTT
façonne par gradient la mémoire S1 qui alimente le gate → le gate route mieux. Test décisif.

## Méthode

`tools/torch_gate_bptt_meansends.py` — 2×2 propre, MÊME substrat torch, tout égal par ailleurs :

    {no-gate, gate} × {truncated (H détaché S1→S2), bptt (graphe récurrent retenu)}

Boucle manuelle sur `pop._step` (graphe retenu) insérant le gate DANS le graphe autograd. Gate = biais
additif sur le SEUL logit Y (`logits_Y += H_S2·w_gate + b`, one-hot → pas d'in-place). Anti-saturation
(EDR-136) = pénalité homéostatique `antisat·mean(P_base(Y))²` sur la marginale de la politique de BASE
(garde la base loin d'always-Y → préserve le gradient différentiel ; le gate soulève Y *conditionnellement*).
Métrique de binding (EDR-128) : `binding_gap = P(Y|X) − P(Y|¬X)`. 3 seeds, 1000 époques, 128 agents,
antisat=6. Point clé du contraste : en `truncated`, la VALEUR de H_S2 contient toujours did_x (propagée
en forward), seul le GRADIENT vers S1 est coupé → le gate lit la valeur et peut conditionner ; BPTT
n'ajoute que la mise en forme PAR GRADIENT de la mémoire S1.

## Constat

| cellule | binding_gap médian | par seed [s0, s1, s2] | hit_end médian |
|---|---|---|---|
| nogate+truncated | −0.004 | [−0.00, +0.06, −0.14] | 0.078 |
| nogate+bptt | −0.009 | [−0.11, +0.15, −0.01] | 0.055 |
| **gate+truncated** | **+0.295** | [+0.28, +0.30, +0.30] | 0.273 |
| gate+bptt | +0.000 | [+0.00, +0.04, −0.02] | **0.367** |

`VERDICT = GATE_BINDS_BPTT_DEGRADES`. Le no-gate ne binde JAMAIS (réplique 146). Le gate+tronqué BINDE
sur les 3 seeds (~+0.30 ; réplique 136). **BPTT DÉTRUIT le binding du gate** : les 3 seeds qui bindent
en tronqué s'effondrent tous à ≈0 en bptt (médiane +0.295 → +0.000), avec le hit_end MAXIMAL (0.367).

**Reproduit deux fois** (2 runs indépendants 3 seeds/1000ep) : verdict `GATE_BINDS_BPTT_DEGRADES`
STABLE (run A : gate+trunc médiane +0.307 vs gate+bptt +0.005 ; run B ci-dessus +0.295 vs +0.000). Le
per-seed varie entre runs (path-dependence / bassin, cf. EDR-131/133 — le substrat CPU n'est pas
bit-déterministe malgré le seed), mais le SIGNE et l'ampleur du delta gate-vs-bptt sont robustes.

## Lecture

- **Le gate est le binder, pas BPTT.** Ce banc reproduit les DEUX fils indépendants (146 no-gate ≈ 0,
  136 gate binde) dans un seul contrôle, puis tranche la conjonction : BPTT n'ajoute rien.
- **BPTT est ACTIVEMENT nuisible au conditionnement du gate.** Signature nette : gate+bptt a le hit_end
  le PLUS HAUT (0.328) MAIS gap ≈ 0 → le crédit à travers le temps pousse l'agent à gonfler les
  **marginales** (P(X) et P(Y) hauts → accomplit X-puis-Y par co-occurrence) au lieu de **conditionner**
  Y sur did_x. BPTT ouvre plus de chemins de gradient pour saturer P(Y), ce que l'anti-saturation du
  régime tronqué contient mieux (crédit 1-pas = surface d'optim plus contrainte).
- **CONVERGENCE** avec « l'autograd à travers la récurrence DÉSTABILISE » (EDR-137/144 in-world : le
  gradient BPTT érode un champion transplanté) et avec EDR-146 (BPTT ≠ chaînon du binding). Le binding
  est un problème de **ROUTAGE within-tick** (gate), orthogonal — voire antagoniste — à la portée du
  crédit à travers le temps.

## Conséquences

- **Recette de binding pour la migration** : **gate (routage) + anti-saturation sur substrat TRONQUÉ**.
  Ne PAS ajouter BPTT au chemin de binding.
- **Carte de valeur de torch, FERMÉE côté binding** : (a) faisabilité/parité (140/141), (b) mémoire
  multi-pas via BPTT (145, capacité UNIQUE), (c) binding via gate within-tick (129/136 + ce banc). Les
  capacités (b) et (c) sont **séparées** : BPTT pour les tâches à mémoire/crédit multi-pas, gate pour le
  conditionnement compositionnel — les mélanger sur la tâche de binding NUIT.
- Clôt la question ouverte en EDR-146 (« prochain build coordonné = gate + BPTT »). Le harnais
  (`run_cell`, 2×2) est réutilisable. Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-147`.

## Caveats

1. **antisat=6, lr=0.05, target_y=5** calibrés sur CE banc (pas les mêmes que le fil compositional) :
   le gate+tronqué binde 2/3 seeds ici (s0 collapse à +0.00), pas 10/10 — l'absolu diffère du 136.
   Le résultat ROBUSTE est la COMPARAISON contrôlée (gate>>no-gate ; bptt<tronqué au sein du gate), pas
   la fiabilité absolue.
2. 3 seeds, forte variance (path-dependence / bassin, cf. EDR-131/133) : s2 binde encore en bptt (+0.25)
   → « DÉGRADE » est une TENDANCE nette (médiane) pas une destruction universelle ; un n plus grand
   préciserait l'ampleur, mais le SIGNE (BPTT n'aide pas, tend à casser) est cohérent avec 137/144/146.
3. Gate ADDITIF linéaire sur un seul logit + anti-saturation quadratique ; gates multiplicatifs/attention
   ou anti-saturation non-quadratique non testés (bornage).
4. REINFORCE épisodique 2-pas + baseline ; un actor-critic BPTT plus riche pourrait différer (borné).
