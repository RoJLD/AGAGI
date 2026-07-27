---
id: EDR-171
type: EDR
title: "Gate binaire, test HELD-OUT sans confond (cran 2, Brique B1) : le mécanisme de routage d'une action BINAIRE (throw) sur un contexte PRÉSENT-PROPRE est INTACT et GÉNÉRALISE. Corrige les 3 causes du confond de mémorisation d'EDR-169 (obs VARIABLES par épisode, S1 stochastique, did_craft encodé dans obs_b[:,0]) + HELD-OUT (readout gelé, obs fraîches) + contrôle SHUFFLE (label de récompense permuté). Verdict POSITIF PROPRE : gap_ON 0.72-0.75 vs gap_SHUFFLE ~−0.02 (PLAT), diff médian +0.759, 4/4 seeds, BINDING_REEL_HELDOUT. Revue adversariale VALIDE (held-out réel 0/100 overlap, ablation w[0] → gap 0.74→0.001 = tout le gap dans le canal contexte, scramble canal → gap ~0). BORNE : le décodage est TRIVIAL (readout lit un canal d'obs propre injecté verbatim dans H) — ce n'est PAS 'binding résolu' ; la difficulté de représentation distribuée reste B2 (biosphère)"
status: accepted
gate: null
verdict: BINARY_GATE_ROUTES_PRESENT_CONTEXT_HELDOUT_PASSES_SHUFFLE
---

# EDR 171 : le gate binaire route un contexte présent-propre (held-out, passe le shuffle) — corrige EDR-169

## Contexte

EDR-169 : le harnais gate-binaire à obs FIXES CONFOND binding et mémorisation (readout 172-dim ≫ 64
agents mémorise n'importe quel label fixe ; le contrôle shuffle bindait autant). Brique B1 corrige les
3 causes et re-teste EN ISOLATION, avant tout câblage biosphère (B2). Harnais
`tools/torch_binary_gate_heldout_probe.py` (fichiers neufs). Cf. [[torch-inworld-integration-plan]].

## Méthode — les 3 corrections + held-out + shuffle

Monde 2-pas binaire, avec les corrections mandatées par EDR-169 :
1. **Obs VARIABLES par épisode** (re-tirées) → aucune identité fixe à mémoriser (cause racine).
2. **S1 stochastique** (`rng.choice`, pas argmax) → `did_craft` = événement variable.
3. **did_craft encodé dans `obs_b[:,0] = did*signal_amp`** → le contexte est dans l'état.

Tête throw (readout PARTAGÉ population, `w_throw` N-dim + `b_throw` scalaire, ZÉRO param par agent).
**HELD-OUT** : phase TRAIN (readout entraîné par REINFORCE binaire + anti-sat), puis phase TEST (readout
GELÉ, obs FRAÎCHES). **SHUFFLE** : permute le label de RÉCOMPENSE (permutation fixe) ; le gap est mesuré
sur le VRAI did_craft dans les deux bras. W gelé (H détaché). `train_ep=1200` (400 sous-entraîne :
held-out gap 0.02 vs 0.74). 4 seeds.

## Constat

| seed | gap_ON (held-out) | gap_SHUFFLE (held-out) | diff |
|---|---|---|---|
| 0 | +0.744 | −0.018 | +0.762 |
| 1 | +0.733 | −0.023 | +0.756 |
| 2 | +0.719 | −0.020 | +0.739 |
| 3 | +0.751 | −0.020 | +0.771 |

median diff +0.759, 4/4, `VERDICT = BINDING_REEL_HELDOUT` (`BINARY_GATE_ROUTES_PRESENT_CONTEXT`).

## Lecture

- **Le mécanisme de routage est INTACT et GÉNÉRALISE.** ON binde fort (0.72-0.75) sur des obs held-out
  (fraîches) ; SHUFFLE est plat (~−0.02). Le contraste écarte proprement la mémorisation d'EDR-169 :
  obs variables (pas d'identité) + readout partagé (zéro param/agent) + held-out (obs neuves) → seule une
  RÈGLE stable est exploitable, et le shuffle décorrèle la récompense de cette règle → gap plat.
- **Pourquoi shuffle+held-out suffit** (vs EDR-169) : EDR-169 mémorisait des labels fixes par agent ;
  ici les 3 verrous ferment ce mode. Revue adversariale (contrôles reproduits) : held-out réel (0/100
  overlap train/test), ablation `w_throw[0]` → gap 0.744→0.001, scramble du canal au test → gap ~0.
- **BORNE FORTE (ne pas sur-vendre)** : le décodage est TRIVIAL. `backend_torch` injecte l'obs verbatim
  dans `H[:, :I]` → `H_S2[:,0] ≈ did_craft*amp`, et 100 % du gap tient dans le seul poids `w_throw[0]`.
  Le « binding » se réduit ici à « un readout linéaire lit un canal d'obs propre ». Ce n'est PAS un
  confond (il s'annulerait sous shuffle), mais ce N'EST PAS « binding résolu » — c'est la preuve que le
  MÉCANISME (router une action binaire sur un contexte présent, sous crédit épisodique) fonctionne et
  généralise. La difficulté de représentation (contexte distribué via récurrence + obs riche) reste B2.

## Conséquences

- **Feu vert pour B2 (câblage biosphère)** : le mécanisme de gate binaire est sain → câbler dans
  `world_1_stoneage.py` (gate sur `logits[8]`=throw conditionné sur spear-en-inventaire, crédit throw
  in-world) est justifié. Dans la biosphère, did_craft (spear en inventaire) entre naturellement dans
  l'obs — comme `obs_b[:,0]` ici, mais via la vraie dynamique.
- **1er résultat POSITIF VALIDÉ de la session** (survie 163 NEUTRE, gate-persist 166 NEUTRE, gate binaire
  169 CONFOND) : le contrôle shuffle + held-out font la différence entre un vrai positif et un artefact.
- **Nuance conservée** : comp_ON ~0.09 (craft 1/8 rare) — dans la biosphère le craft devra aussi émerger
  (W entraîné/incité), pas seulement le routage.

## Caveats

1. **Décodage trivial** (canal propre injecté verbatim) : B1 teste le MÉCANISME, pas la difficulté de
   représentation biosphère (= B2). Le positif ne prouve pas le binding sur représentation distribuée.
2. **4 seeds** : magnitude énorme (diff ~38× la bande) + 4/4 + shuffle plat = convaincant, mais sign_p
   plafonne à 0.125 (n=4). L'effet-taille est le juge, pas la p-value.
3. Monde synthétique 2-pas. N stable. W gelé (isole la tête). REINFORCE binaire + anti-sat validés
   (EDR-136/159).
