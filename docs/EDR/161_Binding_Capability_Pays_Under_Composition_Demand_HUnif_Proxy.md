---
id: EDR-161
type: EDR
title: "Le binding LIVRÉ (158/159) PAIE quand un monde EXIGE la composition : probe standalone craft→consomme, sweep de demande d. L'avantage capacité(gate+learn_episode) vs plain(TD) CROÎT avec la demande (adv +0.009 à d=0 → +0.212 à d=1) via un comp_rate ON qui monte (0.01→0.17) là où OFF reste plat (~0.03). Proxy amont du pari H-unif (crédit épisodique rachète le crédit conditionnel) → dé-risque l'intégration in-world (axe 1). La capacité ATTÉNUE la demande sans la conquérir (payoff d=1 : ON −0.043 vs OFF −0.255). Méthodo : un monde qui laisse une abstention-à-0 sûre ne bootstrappe PAS la composition (v1 réfutée)"
status: accepted
gate: null
verdict: CAPABILITY_PAYS_UNDER_COMPOSITION_DEMAND
---

# EDR 161 : le binding livré PAIE sous demande de composition (proxy du pari H-unif)

## Contexte

Le fil torch 158/159 a LIVRÉ une capacité de binding means→ends dans le substrat prod (gate additif +
`learn_episode` à crédit épisodique). Question de VALEUR (motif S2/EDR-130 appliqué à la composition, et
proxy amont du **pari H-unif** de [[torch-inworld-integration-plan]] : le crédit épisodique rachèterait
craft/spécialisation/binding, même verrou de crédit conditionnel) : **cette capacité laisse-t-elle un
agent EXPLOITER un monde qui exige la composition, là où le substrat plain (learn TD 1-pas, EDR-148) ne
le peut pas ?** EDR-130 avait montré que le substrat plain ne répond PAS à la demande (le stockage
n'émerge pas même quand le monde l'exige) ; on teste si la capacité binding renverse ça pour la
composition — en STANDALONE (`tools/compositional_world_probe.py`, ne touche AUCUN code monde partagé).

## Méthode

Monde « craft→consomme » 2 pas : S1 l'agent peut CRAFT (X) ; S2 il CHOISIT USE (paie SSI craft = 2-pas)
ou FREE (nourriture 1-pas). Coût de FAIM constant (−0.3, l'abstention COÛTE) ; FREE vaut (1−d) ;
composer vaut (0.5+d). Le **levier de demande** d ∈ [0,1] : d=0 FREE suffit, d=1 composer est la seule
voie viable. On compare, sur un sweep de d, capacité ON (gate additif task-agnostique uniforme +
`learn_episode`, EDR-159) vs OFF (`pop.learn` TD 1-pas sans gate). Métrique = énergie moy/épisode
(PAYOFF) + comp_rate (USE&craft). 3 demandes × 2 seeds × 800 ép.

## Constat

| demande d | payoff ON | payoff OFF | avantage | comp_rate ON / OFF |
|---|---|---|---|---|
| 0.00 | +0.056 | +0.048 | +0.009 | 0.01 / 0.01 |
| 0.50 | −0.063 | −0.133 | +0.070 | 0.12 / 0.02 |
| 1.00 | −0.043 | −0.255 | **+0.212** | **0.17 / 0.03** |

`VERDICT = CAPABILITY_PAYS_UNDER_COMPOSITION_DEMAND`. L'avantage capacité−plain CROÎT monotone avec la
demande (+0.009 → +0.070 → +0.212), porté par un comp_rate ON qui monte (0.01 → 0.17) là où OFF reste
plat (~0.03).

## Lecture

- **La capacité PAIE proportionnellement à la demande de composition.** Le substrat binding-capable
  exploite le monde compositionnel (comp_rate ↑ avec d) ; le substrat plain ne compose pas (comp_rate
  ~0.03 partout) et son payoff s'effondre quand la demande monte (−0.255 à d=1).
- **Support en proxy du pari H-unif** : le crédit épisodique confère un avantage QUAND le crédit
  conditionnel est demandé. C'est le comportement attendu si binding/craft/spécialisation partagent ce
  verrou — dé-risque l'intégration in-world (axe 1 du plan) AVANT de toucher `world_1_stoneage.py`.
- **Contraste avec EDR-130** : là où durcir la demande de STOCKAGE ne faisait rien émerger (substrat
  plain), la demande de COMPOSITION fait émerger la composition — mais SEULEMENT avec la capacité. Le
  levier était bien le substrat/moteur (crédit épisodique), pas le monde. Converge le diagnostic 130.
- **La capacité ATTÉNUE sans conquérir** : à d=1, ON reste à −0.043 (comp_rate 0.17, encore bas) — mieux
  que OFF (−0.255) mais pas thriving. Sur ce substrat 172-nœuds dégénéré, la capacité réduit fortement
  le coût de la demande sans la résoudre pleinement.

## Conséquences

- **Feu vert de valeur pour l'intégration in-world (axe 1)** : la capacité livrée n'est pas qu'un
  artefact de banc — elle confère un avantage de survie proportionnel à la demande de composition. Le
  pari H-unif tient en proxy ; le porter in-world devrait racheter craft(127)/spéc(156/157).
- **Méthodo de monde compositionnel** (réutilisable, réfute la v1) : un monde qui laisse une
  **abstention-à-0 sûre** ne bootstrappe PAS la composition (v1 : comp_rate 0.00 partout, pénalité −1
  pour USE-sans-craft écrasait l'exploration AVANT que le craft soit fiable). Il faut un coût de faim
  (l'abstention coûte) + une pénalité DOUCE d'exploration. Cf. EDR-090 (curriculum de létalité).
- Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-161`.

## Caveats

1. **Proxy synthétique 2-pas**, pas la vraie biosphère (cohorte, obs riches, épisodes longs) : indicatif,
   pas conclusif pour l'in-world. Le test réel = axe 1 (replay sous crédit épisodique, [[torch-inworld-integration-plan]]).
2. 2 seeds, comp_rate absolu bas (0.17 à d=1) ; le ROBUSTE est la MONOTONIE de l'avantage avec d + la
   divergence comp_rate ON vs OFF, pas l'absolu.
3. Capacité ON = recette task-agnostique uniforme (159, additif) ; le régime scopé (meilleur
   accomplissement) donnerait un avantage supérieur — borne BASSE de la valeur.
4. `_energy` v2 (faim −0.3, FREE=1−d, comp=0.5+d) est un choix de design ; la MONOTONIE tient, mais les
   valeurs absolues dépendent du barème (bornage : un seul barème testé).
