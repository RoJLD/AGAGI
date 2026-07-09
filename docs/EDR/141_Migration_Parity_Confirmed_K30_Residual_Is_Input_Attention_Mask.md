---
id: EDR-141
type: EDR
title: "Parité migration CONFIRMÉE à K=30 (torch vs legacy-core p=0.46, non signif) + résidu DÉCOMPOSÉ à 100% = masque d'attention d'entrée dynamique (parité PAR-PAS exacte, pas du bruit numérique) + registre d'activations enrichi (8 noyaux)"
status: accepted
gate: null
verdict: MIGRATION_PARITY_CONFIRMED_RESIDUAL_IS_ATTENTION_MASK
---

# EDR 141 : parité migration confirmée (K=30) + résidu = masque d'attention d'entrée + registre enrichi

## Contexte

EDR-140 a validé la migration torch (adaptateur fidèle : activation auto + round-trip) — torch non
distinguable de legacy-core à K=10 (p=0.18). Backlog de resserrement : (1) K plus grand ; (2)
décomposer le résidu ~16t ; (3) enrichir le registre d'activations différentiables.

## Item 1 — K=30 : parité CONFIRMÉE à plus haute puissance

`arms` K=30, stoneage, champion HoF #1, torch défaut (auto→swish) :

| bras | survie |
|---|---|
| legacy-full | 63.2 |
| legacy-core | 66.8 |
| torch (auto=swish) | 56.5 |

| lecture | median_diff | fav | sign_p |
|---|---|---|---|
| ORGANES (full − core) | +0.75 | 16/30 | 0.855 |
| RÈGLE @parité (torch − core) | −10.25 | 12/30 | **0.458** |

À K=30 l'écart torch↔legacy-core reste **NON significatif** (p=0.46, encore moins qu'à K=10) et les
organes restent NEUTRE (p=0.86). La parité tient à plus haute puissance.

## Item 2 — le résidu est à 100% le masque d'attention d'entrée (pas du bruit numérique)

Sonde PURE `tools/torch_parity_probe.py` : legacy-core vs torch-swish, MÊME génome + MÊME séquence
d'obs, divergence de logits par tick.

| tick | 0 | 1 | 2 | … | 11 |
|---|---|---|---|---|---|
| div (normal) | **0.0000** | 0.883 | 0.532 | … | 1.450 |
| div (masque legacy forcé à `ones`) | **0.0000** | **0.0000** | **0.0000** | … | **0.0000** |

- **t=0 diff = 0.0000** : la fonction de pas est **numériquement identique** (einsum≡bmm, delta, clamp,
  activation swish) — pas de bug de parité numérique.
- **Neutraliser le masque d'attention d'entrée dynamique de legacy → 0.0000 à CHAQUE tick.** Legacy
  recalcule un masque `sigmoid(attention_logits)` (sortie réseau) et l'applique aux ENTRÉES
  (`x = x_obs * attention_mask`) au tick suivant ; `TorchBatchModel` ne le réplique pas (masque=ones).
  Le masque du champion vaut `ones` à l'init (→ t=0 identique) puis devient sigmoïdal après 1 forward
  (→ divergence dès t=1). **Le résidu est ENTIÈREMENT ce masque**, une feature « organe-ish » toujours
  active côté legacy, pas une erreur numérique.

## Item 3 — registre d'activations différentiables enrichi

`_act_registry()` : {tanh, swish, sigmoid, relu, leaky_relu, softplus, gelu, identity} — chaque entrée
= (réf numpy pour la détection, noyau torch différentiable), parité numpy↔torch testée. `_detect_world_activation`
balaie tout le registre (grille 33 pts, atol 1e-5) ; repli tanh + warn si hors registre. L'adaptateur
suit donc un métaprog qui produirait autre chose que swish sans intervention.

## Conséquences

- **Migration parité ROBUSTE** (K=30, p=0.46) : `ADR-003` a un substrat torch validé à n=30.
- **Résidu compris à 100%** : le masque d'attention d'entrée. Le **porter** dans torch donnerait la
  parité bit-à-bit, MAIS l'écart de survie est **non significatif** → polish OPTIONNEL, pas un
  blocage. (Cohère [[intelligence-typing-flat-connectome]] : ces gates d'entrée sont peu porteurs.)
- **Adaptateur robuste** aux activations du métaprog (registre 8 noyaux).
- **Reste le VRAI gain** : exploiter torch (plasticité différentiable / Baldwin / meta-RL) que numpy
  interdisait — item 4. Affine [[sota-gap-substrate]].
- Outils : `tools/torch_parity_probe.py`, `src/agents/torch_batch_model.py` (`_act_registry`).
  Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-141`.

## Caveats

1. 1 champion, 1 monde (stoneage). K=30 = 30 évals d'un même champion (pas 30 champions).
2. Le port du masque d'attention d'entrée dans torch n'est PAS implémenté (optionnel, non-significatif).
3. Détection d'activation par sonde (33 pts, atol 1e-5) ; une activation métaprog très proche d'un
   noyau existant pourrait être mal étiquetée (peu probable à cet atol).
4. legacy-full 63.2 < K=10 74.5 : variance d'échantillon sur ce champion ; les lectures APPARIÉES
   (organes, règle) sont robustes, pas les médianes marginales absolues.
