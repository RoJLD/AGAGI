---
id: EDR-169
type: EDR
title: "Gate de conditionnement sur action BINAIRE (cran 2, Brique A) : la machinerie (tête throw + REINFORCE épisodique + anti-saturation) est ENTRAÎNABLE, mais le monde jouet 2-pas CONFOND binding et MÉMORISATION. Un premier verdict gap_ON 0.53-0.99 vs gap_OFF ~0 (GATE_BINAIRE_BINDE, 4/4) a été RÉFUTÉ par la revue adversariale : un CONTRÔLE SHUFFLE (did_craft permuté par une permutation fixe) donne gap_shuffle ~= gap_ON (diff médian −0.02, verdict_vs_shuffle HEBBIEN_GAGNE) → le label FAUX binde autant que le vrai. Cause : readout 172-dim ≫ 64 agents (séparabilité triviale) + did_craft déterministe (argmax S1 + W gelé → label FIXE par agent, pas un événement) + l'action craft n'entre pas dans H. Contrôle shuffle intégré au harnais. Leçon Brique B : did_craft doit ENTRER dans l'état (inventaire), contrôle shuffle + held-out, n_agents ≫ N, S1 stochastique"
status: accepted
gate: null
verdict: BINARY_GATE_TRAINABLE_TOY_WORLD_CONFOUNDS_BINDING_WITH_MEMORIZATION
---

# EDR 169 : gate binaire entraînable, mais le monde jouet confond binding et mémorisation

> ⚠️ Renuméroté 168→169 : collision de numéro avec l'EDR-168 (hystérésis rétention) d'une session // (tree partagé).

## Contexte

Le cran 2 in-world (gate de binding sur l'action offensive craft→throw) bute sur un mécanisme manquant :
le gate livré (EDR-159/165) biaise une politique CATÉGORIELLE (8 moves), mais l'action « ends » biosphère
est `do_throw = logits[8] > 0`, BINAIRE. Brique A = tester EN ISOLATION si un readout de H apprend à
conditionner une action binaire sur un contexte (did_craft) sous crédit épisodique, avant tout câblage
biosphère. Harnais `tools/torch_binary_gate_probe.py` (fichiers neufs, ne touche ni backend_torch ni la
biosphère). Cf. [[torch-inworld-integration-plan]].

## Méthode

Monde 2-pas binaire : S1 move (`did_craft = argmax==CRAFT`) ; S2 décision `throw ~ Bernoulli(σ(z))`.
Tête throw dans le harnais : `z = H·w_throw + b` (ON, lit H) vs `z = b` (OFF, marginal). Crédit épisodique
REINFORCE binaire + anti-saturation (empêche always-throw). W GELÉ (H détaché) pour isoler la tête. KPI =
`binding_gap = P(throw|did_craft) − P(throw|¬did_craft)`. A/B apparié 4 seeds × 800 ép.

## Constat

**Premier verdict (naïf) :** gap_ON 0.529 / 0.995 / 0.854 / 0.749 ; gap_OFF ~0.003 ; median diff +0.798,
4/4 → `GATE_BINAIRE_BINDE`. Semblait fort.

**Réfuté par contrôle SHUFFLE** (revue adversariale) — did_craft remplacé par une permutation FIXE
(décorrélée du contexte, même taux de base) :

| seed | gap_ON | gap_OFF | gap_shuffle | diff (ON − shuffle) |
|---|---|---|---|---|
| 0 | +0.529 | +0.003 | +0.576 | −0.047 |
| 1 | +0.995 | +0.003 | +0.747 | +0.248 |
| 2 | +0.854 | −0.002 | +0.850 | +0.004 |
| 3 | +0.749 | +0.008 | +0.996 | −0.248 |

`verdict_vs_shuffle` = **HEBBIEN_GAGNE** (median −0.022, sign_p 1.0) : gap sur un label FAUX ≈ gap sur le
vrai craft. `VERDICT = BINARY_GATE_TRAINABLE_TOY_WORLD_CONFOUNDS_BINDING_WITH_MEMORIZATION`.

## Lecture

- **Le gap élevé N'EST PAS du binding — c'est de la mémorisation.** Un readout de dim `pop.N=172` sur
  `n_agents=64` sépare TRIVIALEMENT n'importe quel étiquetage binaire (64 points en dim 172 sont
  génériquement indépendants → gap→1 garanti, quel que soit le contenu de H).
- **`did_craft` est aliasé à l'identité fixe de l'agent** : obs fixes + W gelé + `argmax` déterministe en
  S1 → did_craft est CONSTANT par agent, pas un événement within-épisode. De plus l'action craft
  N'ENTRE PAS dans H (le move est un readout, pas une entrée) → H ne PORTE pas l'événement craft ; le
  readout décode l'identité, pas le contexte.
- **Le contrôle OFF était trop faible** : `b` scalaire partagé → gap_OFF≈0 garanti par construction (aucun
  degré de liberté par-agent), pas parce qu'il « ne lit pas H ». Le vrai plancher = shuffle (même capacité,
  label faux) — qui binde autant.
- **La machinerie est SAINE** (vérifié) : tête throw entraînable, REINFORCE Bernoulli correct, anti-sat,
  W bien gelé, RNG apparié entre bras. Le défaut est le DESIGN EXPÉRIMENTAL, pas le code.

## Conséquences

- **Instrument LIVRÉ avec contrôle shuffle intégré** : tout futur test de binding sur ce harnais compare
  désormais ON au SHUFFLE (pas à OFF). Le confond ne peut plus passer inaperçu.
- **Leçon pour la Brique B (câblage biosphère)** — pour un VRAI test du binding craft→throw :
  1. `did_craft` doit ENTRER dans l'état (dans la biosphère : le spear est dans l'inventaire, encodé
     dans l'obs → H le porte réellement) — pas un label externe fixe.
  2. **S1 stochastique** (craft = événement réalisé variable), pas argmax déterministe.
  3. `n_agents ≫ N` (ou un readout bas-dim / régularisé) pour éviter la séparabilité triviale.
  4. **Contrôle shuffle + held-out** obligatoires (mesurer le gap sur des agents non vus).
- **4e résultat de la session à s'évaporer sous contrôle/puissance** (après survie NEUTRE EDR-163,
  gate-persist NEUTRE EDR-166) : la revue adversariale et les contrôles sont l'actif méthodologique clé.

## Caveats

1. Le monde jouet à obs fixes + W gelé est un mauvais banc pour le binding (c'est le constat) ; il reste
   valide pour prouver que la MACHINERIE (tête binaire + crédit épisodique) tourne et s'entraîne.
2. La sur-paramétrisation (172 ≫ 64) suffit seule à produire le confond ; corriger un seul facteur
   (sampling S1) ne suffirait pas sans corriger aussi la dimension/held-out.
3. Bornage : négatif sur substrat/monde dégénéré. Un test bien conçu (Brique B, did_craft dans l'état)
   pourrait établir ou réfuter le binding réel — non tranché ici.
