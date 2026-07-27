---
id: EDR-139
type: EDR
title: "Sweep lr NEUTRE (0.0→0.04 : 32→33) → le gradient n'est PAS le coupable ; le gap torch était surtout un MISMATCH D'ACTIVATION (champion évolué sous Swish, torch tournait en tanh) — torch-swish récupère 33→52.5 (~55% du gap)"
status: accepted
gate: null
verdict: ACTIVATION_MISMATCH_DOMINANT_LR_NEUTRAL
---

# EDR 139 : sweep lr neutre + le vrai confond était l'activation (swish vs tanh)

## Contexte

EDR-137 (après bugfix round-trip) attribuait le collapse torch (torch-core 33.0 vs legacy-core 68.2,
0/10) à la « règle d'apprentissage » (le TD autograd déstabiliserait le champion transplanté). Pivot
choisi : **sweep lr/gating** — apprivoiser le gradient (lr↓, voire lr=0) annule-t-il la
déstabilisation ? Sinon, qu'est-ce qui reste ?

## Méthode

`tools/substrate_world_ab.py` : `sweep_lr_torch` (sous-classe par lr, pas de mutation globale) balaye
lr ∈ {0.0, 0.001, 0.005, 0.02, 0.04} ; `ACTIVATION` configurable sur `TorchBatchModel` (`tanh` défaut
| `swish` = `custom_activation` de `generated_ops`, x·sigmoid(x)). Champion HoF #1, K=10, 12 agents,
300 ticks, stoneage sweet-spot. Repères legacy-core / legacy-full sur le MÊME génome.

## Constat

**Sweep lr (torch, activation tanh) :**

| lr | 0.0 | 0.001 | 0.005 | 0.02 | 0.04 |
|---|---|---|---|---|---|
| survie | 32.0 | 32.5 | 32.5 | 33.0 | 33.0 |

→ **PLAT** (±1 tick sur tout l'intervalle). Même lr=0 (zéro apprentissage, récurrence conservée) = 32.

**Activation (champion, K=10) :**

| arm | survie |
|---|---|
| torch-tanh | 33.0 |
| **torch-swish** (= activation évoluée du champion) | **52.5** |
| legacy-core | 68.2 |
| legacy-full | 74.5 |

## Lecture

1. **Le lr / le gradient n'est PAS le coupable** : lr=0 ≈ lr=0.04 (32 vs 33). Ça **réfute la lecture
   secondaire d'EDR-137** (« autograd déstabilise »). L'apprentissage torch est ~neutre (aide même de
   ~1 tick).
2. **Correction d'EDR-137** : l'écart « torch-avec 33 < torch-sans 38.8 » que j'attribuais à
   l'apprentissage était en fait la **RÉCURRENCE** (le fix H de 137) — lr=0-AVEC-récurrence = 32 <
   pré-fix-SANS-récurrence = 38.8. L'apprentissage n'était pas en cause ; comparaison confondue par la
   récurrence.
3. **Le vrai confond dominant = l'ACTIVATION.** Le champion a évolué son W sous **Swish** (non-bornée,
   `custom_activation` produite par le métaprog) ; `TorchBatchModel` tournait en **tanh** (bornée
   [-1,1]) → dynamiques LTC différentes → politique cassée. Matcher l'activation (torch-swish)
   récupère **33 → 52.5**, soit **~55% du gap** vers legacy-core (68.2).
4. **Résidu ~16 ticks** (52.5 vs 68.2) = numérique/structurel torch↔numpy (ordre des opérations, float,
   détails du round-trip) — mineur, à caractériser.

## Conséquences

- **Reco migration POSITIVE et concrète** : un substrat torch qui (a) **matche l'activation évoluée**
  (câbler torch sur `_get_activation_function` du monde, pas un `tanh` codé en dur) + (b) round-trip
  l'état (EDR-137) **récupère l'essentiel** de la compétence legacy. Le « torch est pire »
  (EDR-134/135/137) était largement un **apples-to-oranges** : d'abord non-apprentissage (137), puis
  mismatch d'activation (ici). Ni organes (135), ni gradient (ici) n'étaient le verrou. Affine
  [[sota-gap-substrate]].
- **Baldwin natif (warm-start) devient OPTIONNEL** pour ce champion : le transplant récupère déjà
  ~beaucoup rien qu'en matchant l'activation. Le natif reste utile pour le résidu / un test propre du
  moteur seul.
- **Suite** : (a) câbler torch sur l'activation live du monde (adaptateur fidèle) ; (b) décomposer le
  résidu 16t (parité numérique) ; (c) sign-test sur le bras activation (ici médianes seules).
- Outils : `tools/substrate_world_ab.py` (`sweep_lr`, arms), `src/agents/torch_batch_model.py`
  (`LR`, `ACTIVATION`). Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-139`.

## Caveats

1. 1 champion, 1 monde (stoneage), 1 seed (42), médianes K=10 ; le bras activation n'a pas de sign-test
   (contrairement au bras arms), mais l'effet (+19.5 ticks) est GROS et cohérent avec la théorie.
2. Défaut `ACTIVATION="tanh"` NON basculé (non-régressif pour les tests/expériences torch existants) ;
   la reco est de câbler dynamiquement sur l'activation du monde.
3. Résidu 16t non décomposé (numérique vs structurel).
4. `custom_activation` = Swish AUJOURD'HUI ; le métaprog peut l'évoluer → un adaptateur fidèle doit lire
   l'activation courante, pas coder « swish » en dur.
