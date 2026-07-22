---
id: EDR-DREAM-003
type: EDR
title: "L'AMPLITUDE du bruit sur l'état récurrent est le levier : dose-réponse en CLOCHE (optimum intérieur σ≈0.2), et la récurrence supplémentaire SEULE (σ=0) est quasi-nulle — confirme DREAM-002 contre sa propre décomposition"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-DREAM-002]
---

## Question
[[EDR-DREAM-002]] a montré que le bénéfice du « rêve » est du BRUIT et non de la planification (le bras
factice reproduit 100 % de l'effet). Mais l'intervention faisait ENCORE deux choses non séparées :

  (i)  elle injecte du bruit K fois sur l'état caché `H` ;
  (ii) elle applique K mises à jour récurrentes SUPPLÉMENTAIRES — la boucle **mute** `H` à chaque pas
       (`mamba_agent.py` ~L618 : `H[active_mask] = H_branch[active_mask]`), donc les « K branches »
       sont une MARCHE à K pas, du temps de calcul sans perception mêlé au bruit.

Et si le bénéfice venait de la récurrence, pas du bruit ? Et quelle est la FORME de la dose-réponse en
amplitude — monotone (plus de bruit vaut mieux) ou en cloche (optimum, signature d'un compromis
exploration/destruction de l'état) ?

## Méthode
Seam `MambaBatchModel.DREAM_NOISE` (défaut `0.05` = valeur historique en dur → **prod inchangée**),
**calibré sur réponse connue** avant tout run (`tests/sandbox/test_dream_noise_seam.py`, 4/4 : no-op
EXACT à σ=0, stochastique à σ>0, divergence monotone en σ, défaut = valeur historique).

Échelle σ ∈ {0, 0.0125, 0.05, 0.2, 0.8} + `off`, sélection factice (DREAM-002 : inerte), K=8,
`stoneage`, 25 agents, 80 ticks, **12 seeds**. À K fixé, tous les bras paient le **même**
`compute_spent` donc le même `brain_cost` (`world_1_stoneage.py:1240`) : l'échelle d'amplitude est
coût-appariée **par construction**. Endpoint PRIMAIRE = `n_lived` (non borné) ; `med_founder_age` est
CENSURÉ à droite (rapporté comme borne inférieure). Artefact : `results/dream_noise_ladder.json`.
`declare_design(replication_unit="ère", n=12)` — `warning: None`.

## Résultats — `n_lived` (endpoint primaire)

| σ | ratio vs `off` | favorables | wilcoxon_p |
|---|---|---|---|
| **0.0** (récurrence pure) | **1.73×** | 12/12 | 0.0025 |
| 0.0125 | 15.17× | 12/12 | 0.0025 |
| 0.05 *(historique)* | 18.71× | 12/12 | 0.0025 |
| **0.2** | **22.30×** ← pic | 12/12 | 0.0025 |
| 0.8 | 15.05× | 12/12 | 0.0025 |

`med_founder_age` (borne inférieure, ~38 % censuré au pic) : σ=0 **0.73×** (3/12) — la récurrence pure
fait mourir les fondateurs plus JEUNES ; σ=0.05 **1.56×** (10/12, p=0.014), σ=0.2 1.55× (9/12), σ=0.8
0.94× (n.s.). `preys` suit `n_lived` (pic σ=0.2, 4.22×, 12/12).

## Verdict
**`NOISE_AMPLITUDE_IS_THE_LEVER__INVERTED_U__RECURRENCE_ALONE_NEAR_NULL`**

**1. Le bruit est le levier, confirmé contre le contrôle le plus dur.** σ=0 (récurrence supplémentaire
SANS bruit) donne 1.73× ; la moindre dose de bruit saute à 15-22×. La conclusion « c'est le bruit » de
DREAM-002 survit à sa propre décomposition — le bras qui apparie tout SAUF le bruit ne reproduit pas
l'effet.

**2. Mais la récurrence n'est PAS nulle.** σ=0 vaut 1.73× (12/12, p=0.0025), effet **homogène**
(positif dans les 12 seeds, médiane +35.5). DREAM-002 ne pouvait pas le voir. « Dominé » n'est pas
« inexistant » : la récurrence supplémentaire fait un peu plus de descendants — au prix de fondateurs
plus jeunes (age 0.73×).

**3. Dose-réponse en CLOCHE, pas monotone.** Optimum intérieur à σ≈0.2 (22.3×), déclin à σ=0.8
(15.0×). Le pic par seed est LARGE (0.0125:3, 0.05:3, 0.2:4, 0.8:2 seeds ; aucun à σ=0) → plateau à
optimum intérieur, pas une pointe. Signature d'un compromis **exploration vs destruction de l'état** :
trop de bruit détruit `H` plus vite qu'il ne l'explore.

**4. La valeur historique 0.05 est quasi-optimale pour la survie, sous-optimale pour la reproduction.**
σ=0.2 dépasse σ=0.05 de ~19 % sur `n_lived`. Marge disponible, modeste.

## Contrôles internes qui valident l'instrument
* **Contrôle positif intégré, reproduit à la décimale.** σ=0.05 donne 18.71× / médiane 1057 —
  *exactement* le bras `sham8` de [[EDR-DREAM-002]] (mêmes seeds, même config). Le seam ne perturbe pas
  la trajectoire historique ; les deux runs sont reproductibles. Un barreau qui n'aurait pas retrouvé
  sa propre dose historique aurait accusé l'instrument, pas la nature.
* **Le confondant déclaré avant le run est sans objet.** Règle posée : ajouter un bras `σ=0 + argmax`
  (déterministe) SI σ=0 reproduisait le bénéfice, pour départager récurrence et choix-de-pas aléatoire.
  σ=0 ne reproduit pas (1.73× vs 15-22×) → le résidu ne vaut pas 12 ères de plus. Séquencer le maillon,
  ne pas le supprimer — et ne pas non plus l'ajouter dans la branche où il ne tranche rien.

## Leçons (registre)
* **Un seul seed aurait égaré le design (E12).** Le seed 0 plaçait le pic à σ=0.0125 (ma dose la plus
  basse) ; la n=12 le place à σ=0.2. Refuser de recentrer l'échelle sur un préfixe a évité de raffiner
  la mauvaise région.
* **La censure a dicté l'endpoint, pas la prudence rédactionnelle.** `med_founder_age` est ~38 %
  collé à `max_ticks` au pic ; l'avoir choisi comme primaire aurait comprimé l'amplitude là où l'effet
  est le plus fort. `n_lived` (non borné) était nécessaire, pas cosmétique.

## Piste ouverte
Le levier est le bruit d'amplitude ~0.2 sur l'état récurrent. Reste le SCHÉMA : est-ce de
l'échappement d'attracteur (le bruit décoince un point fixe) ou du recuit (un schéma décroissant
battrait-il une amplitude constante) ? La cloche suggère un optimum ; un recuit σ_t → 0 le testerait
directement. Non engagé.

Converge [[EDR-DREAM-002]], [[EDR-DREAM-001]], [[planner-depth1-refuted]], REF-EXPERIMENT-PREFLIGHT.
