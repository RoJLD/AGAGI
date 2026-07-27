---
id: EDR-140
type: EDR
title: "Reco migration LIVRÉE : adaptateur torch fidèle (activation auto-détectée du monde + round-trip état) — à parité d'organes, torch n'est PLUS distinguable de legacy (52.5 vs 68.2, p=0.18, était 33.0/p=0.004) → migration VIABLE"
status: accepted
gate: null
verdict: MIGRATION_VIABLE_FAITHFUL_ADAPTER
---

# EDR 140 : reco migration livrée — adaptateur torch fidèle, torch à parité avec legacy

## Contexte

EDR-139 a identifié le confond dominant du « torch pire » : un **mismatch d'activation** (le champion
a évolué sous Swish, `TorchBatchModel` tournait en tanh). Reco de migration en 2 parties : (1) matcher
l'activation LIVE du monde ; (2) round-tripper l'état (déjà livré EDR-137). Cet EDR **implémente et
valide** la partie 1.

## Méthode

`torch_batch_model.py` :
- `_detect_world_activation()` : sonde `_get_activation_function()` du monde (activation évoluée par le
  métaprog, opaque) sur une grille et la mappe à un noyau torch **différentiable** (registre
  {swish, tanh}) ; repli tanh + warn si inconnue (on ne peut pas autograd du numpy arbitraire).
- `ACTIVATION = "auto"` (nouveau défaut) : résolu une fois par instance → adaptateur **fidèle** qui
  suit le métaprog. "tanh"/"swish" forcent (repro EDR-134..139).

Validation : bras `arms` (K=10, stoneage, champion HoF #1) avec `TorchBatchModel` défaut (auto).

## Constat

Détection : `_detect_world_activation()` = **swish** (= l'activation live du monde).

| bras | survie |
|---|---|
| legacy-full | 74.5 |
| legacy-core | 68.2 |
| **torch (auto=swish)** | **52.5** |

| Règle @parité (torch − core) | median_diff | verdict | fav | sign_p |
|---|---|---|---|---|
| torch **tanh** (EDR-139) | −24.75 | HEBBIEN_GAGNE | 0/10 | **0.0039** |
| torch **auto=swish** (ici) | **−10.25** | HEBBIEN_GAGNE | 2/10 | **0.1797** |

(ORGANES legacy_full−core inchangé : NEUTRE, p=1.0.)

## Lecture

- **L'adaptateur fidèle ferme l'écart significatif** : le gap torch↔legacy-core passe de −24.75
  (p=0.004, significatif) à −10.25 (**p=0.18, NON significatif**), −58%. À parité d'organes, **torch
  n'est plus statistiquement distinguable de legacy** — et c'est **automatique** (auto-détection).
- **Migration VIABLE** : un substrat torch qui (1) matche l'activation évoluée + (2) round-trip l'état
  (EDR-137) atteint la compétence legacy sans pénalité significative. Tout le « torch pire »
  (EDR-134/135/137) était un empilement d'artefacts : non-apprentissage (137), puis mismatch
  d'activation (139) — jamais les organes (135) ni le gradient (139).
- Le résidu −10.25 est dans le bruit (n=10) ; l'écart restant à legacy-**full** (74.5) = les organes,
  déjà montrés non-porteurs (EDR-135).

## Conséquences

- **ADR-003 (backend abstraction) a désormais un substrat torch VALIDÉ** : chemin de prod =
  `ACTIVATION="auto"` + round-trip. Le verrou « migrer le moteur » de [[sota-gap-substrate]] est levé
  côté FAISABILITÉ (torch ≈ legacy) ; reste l'intérêt SCIENTIFIQUE (gradient/plasticité diff, meta-RL,
  Dreamer) que le numpy ne permet pas.
- **Baldwin warm-start / evolve natif = OPTIONNELS** pour la parité (le transplant y est déjà). Ils
  redeviennent utiles pour EXPLOITER torch (entraîner ce que numpy ne peut pas).
- **Suite** : (a) K plus grand pour resserrer le résidu (n=10 → « non distinguable » ≠ « identique ») ;
  (b) décomposer le résidu ~16t (parité numérique) ; (c) enrichir le registre d'activations
  différentiables (si le métaprog produit autre chose que swish/tanh, repli tanh non-fidèle + warn).
- Outils : `src/agents/torch_batch_model.py` (`_detect_world_activation`, `ACTIVATION="auto"`).
  Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-140`.

## Caveats

1. Registre d'activations limité à {swish, tanh} ; une activation métaprog nouvelle → repli tanh
   (non-différentiable-fidèle) + warn. La détection est par sonde (17 points, atol 1e-5).
2. 1 champion, 1 monde (stoneage), 1 seed (42), K=10. p=0.18 = « non distinguable », PAS « identique » ;
   un K plus grand tranchera le résidu.
3. Défaut basculé "tanh"→"auto" : change le comportement torch par défaut (voulu = fidélité) ; les
   EDR 134..139 restent reproductibles via `ACTIVATION="tanh"`.
4. Détection par instance (le monde reconstruit par tick) : coût négligeable (`_get_activation_function`
   est mtime-caché), et fidèle à une évolution en cours de run.
