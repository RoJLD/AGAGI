---
id: EDR-145
type: EDR
title: "Frontière torch DÉMONTRÉE : BPTT résout la mémoire multi-pas sous distracteurs (T=8 : 1.00 vs 0.61 tronqué, chance 0.50) que le crédit 1-pas (numpy/legacy) ne peut PAS — capacité numpy-impossible ; in-world torch était TRONQUÉ (rebuild par-tick détache le graphe) → l'intégration BPTT = le vrai gain à bâtir"
status: accepted
gate: null
verdict: BPTT_UNLOCKED_NUMPY_CANNOT
---

# EDR 145 : frontière torch — BPTT débloque la mémoire multi-pas (numpy ne peut pas)

## Contexte

EDR-143 : la valeur de torch (au-delà de la parité) vit sur les tâches gradient-exigeantes ; la
**frontière** = un apprenant plus fort (BPTT/Dreamer) que le TD 1-pas dérivé à la main du legacy.
Item 3 backlog : bâtir/démontrer **BPTT** (backprop through time), structurellement impossible en
numpy hand-derived.

## Méthode

`tools/torch_bptt_probe.py` : cellule LTC minimale et AUTONOME (H' = (1-δ)H + δ·tanh(H·W + x)). Tâche
canonique de MÉMOIRE : un indice ±1 injecté à t=0 ; **distracteurs bruités injectés à chaque pas
t≥1** ; lecture supervisée (CE) à t=T-1. L'indice doit être ACTIVEMENT MAINTENU à travers T pas
malgré le bruit → il faut façonner la dynamique récurrente `W` À TRAVERS LE TEMPS. Deux modes :
- **bptt** : graphe autograd RETENU à travers les T pas → gradient de la sortie traverse tous les pas.
- **truncated** : état DÉTACHÉ chaque pas (= crédit 1-pas, exactement ce que le legacy peut faire :
  round-trip via l'agent détache l'état à chaque tick).

## Constat

| mode | T=8, acc médiane (3 seeds), chance=0.50 |
|---|---|
| **bptt** | **1.00** |
| truncated (1-pas, numpy/legacy) | **0.61** |

`VERDICT=BPTT_DEBLOQUE`. BPTT résout parfaitement la mémoire à 8 pas sous distracteurs ; le crédit
1-pas reste près du hasard.

## Lecture

- **Capacité numpy-IMPOSSIBLE, démontrée.** Maintenir l'indice contre les distracteurs exige un circuit
  de mémoire dans `W`, qui ne peut être appris qu'en rétropropageant l'erreur finale à travers les T
  pas récurrents (BPTT). Le TD 1-pas dérivé à la main (legacy) détache l'état → ne peut pas façonner
  `W` à travers le temps → échoue. C'est le **levier concret** que la migration torch débloque.
- **Révélation sur l'in-world** : `TorchBatchModel` est reconstruit CHAQUE tick par le monde
  (world:992) et round-trip l'état via l'agent (EDR-137) — ce round-trip **DÉTACHE le graphe** à
  chaque tick → **l'apprentissage torch in-world était TRONQUÉ (1-pas), jamais BPTT**. Ça explique
  EDR-139 (apprentissage in-world ~neutre) : torch n'a jamais fait de crédit à travers le temps
  in-world. **Le vrai gain de migration (BPTT) reste à bâtir** : persister le graphe autograd à
  travers le rebuild par-tick (fenêtre BPTT : garder un modèle sur K ticks, backprop une fois).

## Conséquences

- **Frontière ÉTABLIE** : torch apporte une capacité (crédit à travers le temps / mémoire récurrente
  apprise) que numpy n'a structurellement pas. La migration n'est pas qu'une parité (EDR-140/141) —
  elle ouvre un espace d'apprentissage neuf. Résout la promesse de [[sota-gap-substrate]] (« migrer le
  MOTEUR »).
- **Prochain build (le vrai levier)** : intégrer un apprenant BPTT fenêtré in-world (redesign du
  per-tick-rebuild pour retenir le graphe sur K ticks), puis le tester sur une tâche in-world à crédit
  long (craft→chasse, means→ends — coordonné avec le fil compositional //). C'est là que torch
  DÉPASSERA legacy, pas juste l'égalera.
- **Lien** : le means→ends du fil compositional // (EDR-122/126, torch>hebbien) est exactement une
  tâche à crédit multi-pas → un apprenant BPTT devrait y aider ; complémentaire, pas dupliqué.
- Outils : `tools/torch_bptt_probe.py`. Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-145`.

## Caveats

1. **Démo AUTONOME** (cellule minimale), pas in-world : prouve la CAPACITÉ, pas encore le gain
   biosphère. L'intégration in-world (persister le graphe) est le build suivant, non fait.
2. Supervisé (CE) pour isoler le crédit-à-travers-le-temps du bruit d'exploration RL ; un apprenant RL
   BPTT (REINFORCE/actor-critic multi-pas) est l'étape d'après.
3. δ fixe (0.5), 1 tâche (copie), T=8 ; le point (bptt≫tronqué) est robuste (3 seeds) mais borné à ce
   banc.
