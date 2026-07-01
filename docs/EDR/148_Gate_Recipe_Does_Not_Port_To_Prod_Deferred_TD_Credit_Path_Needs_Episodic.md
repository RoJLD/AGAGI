---
id: EDR-148
type: EDR
title: "Port PROD de la recette gate+anti-saturation (129/136/147) : la recette NE TIENT PAS dans le vrai chemin de production (Actor-Critic TD(0) DIFFÉRÉ) — gate +0.000 vs nogate +0.052 (les deux ≈0), alors que le MÊME substrat sous REINFORCE épisodique binde à +0.30 (EDR-147). Diagnostic : ni le gate, ni l'exploration (stochastique RÉFUTÉ), ni la contamination S1 (S2-only échoue) ; le verrou est le MÉCANISME DE CRÉDIT (TD 1-pas différé + critique faible n'apprend pas la contingence 2-pas). Reco migration : porter le binding via un crédit ÉPISODIQUE/multi-pas (learn_episode_bptt tronqué), PAS le learn() TD différé. Head de gate LIVRÉ dans backend_torch (flag-gated OFF, prod-safe)"
status: accepted
gate: null
verdict: GATE_RECIPE_DOES_NOT_PORT_TO_PROD_TD_CREDIT_NEEDS_EPISODIC
---

# EDR 148 : la recette de binding NE se porte PAS dans le chemin prod (crédit TD différé) — il faut un crédit épisodique

## Contexte

EDR-147 a fermé la recette de binding means→ends : **gate (readout de H → biais sur l'action cible) +
anti-saturation de la marginale de base** craque le conditionnement (+0.30), BPTT le dégrade. Étape de
MIGRATION : porter cette recette dans le VRAI substrat de production `TorchPopulationModel`
(`make_population` + `forward`/`learn`) et vérifier qu'elle binde à travers le chemin prod réel — celui
qu'utilise le banc compositional //. Révélation en cours de route : **toute** la recette (129/136/147) a
été validée sous **REINFORCE épisodique**, JAMAIS dans le `learn()` prod, qui est un **Actor-Critic
TD(0) à crédit DIFFÉRÉ d'un tick** (bootstrap critique). EDR-148 est le premier test dans ce chemin.

## Méthode

Head de gate porté dans `backend_torch.py` (ADDITIF, flag-gated OFF par défaut → prod-safe, banc //
intact) : `CONDITION_GATE`/`ANTISAT`/`GATE_TARGET` ; readout linéaire population-partagé `_gate_bias(H)`
appliqué dans `forward` (action échantillonnée) ET `_td_update` (crédit) ; anti-saturation de la
marginale de base ajoutée à la perte A-C. Le substrat étant task-agnostique, le gate est appliqué
UNIFORMÉMENT (il doit apprendre QUAND se déclencher depuis H). `tools/torch_prod_gate_meansends.py`
oppose, tâche means→ends de `run_compositional` (fil //), le chemin prod gate OFF vs ON, métrique
`binding_gap = P(Y|X) − P(Y|¬X)` poolée sur (agent × épisode) du dernier quart. Sondes de diagnostic :
`stochastic` (échantillonnage vs argmax) et `gate_s2_only` (désactive le gate au forward de S1).

## Constat

**Headline (3 seeds, 1000 ép, argmax = défaut prod) :**

| condition | binding_gap médian | par seed | hit_end |
|---|---|---|---|
| nogate | +0.052 | [+0.05, +0.02, +0.11] | 0.034 |
| gate | **+0.000** | [+0.00, −0.33, +0.05] | 0.008 |

`VERDICT = GATE_DOES_NOT_BIND_IN_PROD`. Les DEUX ≈0 (le gate légèrement PIRE). Référence : le MÊME
substrat `_step` sous REINFORCE épisodique + gate (EDR-147) binde à **+0.30**.

**Sondes de diagnostic (400 ép, 1 seed) — élimination des causes :**

| sonde | binding_gap | p_x | lecture |
|---|---|---|---|
| gate stochastique | −0.219 | 0.028 | exploration RÉFUTÉE (pire ; le gate uniforme supprime X) |
| gate S2-only argmax | −0.286 | 0.070 | scoping-S1 ne sauve pas |
| gate S2-only stochastique | −0.006 | 0.127 | p_x récupéré mais TOUJOURS pas de binding |

## Lecture

- **La recette ne se porte PAS dans le chemin prod.** Aucune variante du gate ne binde ; le nogate prod
  non plus (~0 partout, hit ~0.03). Le contraste décisif : substrat IDENTIQUE, seul le crédit change —
  REINFORCE épisodique (147) binde, TD(0) différé (148) échoue.
- **Le verrou est le MÉCANISME DE CRÉDIT, pas le gate.** Éliminations : (a) exploration RÉFUTÉE
  (stochastique pire) ; (b) contamination S1 par le gate uniforme = réelle mais PAS la cause racine
  (S2-only récupère p_x sans débloquer le binding) ; (c) reste le crédit : le TD 1-pas différé +
  critique faible (nœud valeur 28 d'un substrat dégénéré) n'apprend pas la contingence 2-pas ; le gate
  ne peut RIEN soulever sans signal de crédit exploitable.
- **Découverte structurante** : la recette de binding vit en « REINFORCE-land » (129/136/147, retour
  épisodique 2-pas), le substrat prod apprend en TD différé — deux mondes de crédit distincts. La
  migration doit réconcilier les deux, ce n'est pas un simple portage de head.

## Conséquences

- **Reco migration (actionnable)** : porter le binding via un chemin de crédit **ÉPISODIQUE/multi-pas**
  dans torch-prod (`learn_episode_bptt` tronqué, EDR-146 — crédit épisodique SANS BPTT, cf. 147) plutôt
  que le `learn()` TD(0) 1-pas. Le head de gate est LIVRÉ et prêt (flag-gated OFF) ; il lui manque le
  bon véhicule de crédit, pas le mécanisme.
- **Carte de valeur torch — nuance de migration** : parité (140/141) OK ; mémoire multi-pas BPTT (145)
  OK ; binding gate (147) OK **mais UNIQUEMENT sous crédit épisodique** — le chemin prod par défaut
  (TD différé) ne le supporte pas. Le binding en prod = crédit épisodique + gate + anti-saturation,
  sur substrat tronqué.
- Head de gate + sondes réutilisables. Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-148`.

## Caveats

1. **Tâche DURE** (hit absolu ~0.03 partout, substrat 172-nœuds dégénéré I/O-chevauchants) : le résultat
   ROBUSTE est la COMPARAISON contrôlée crédit-épisodique(147, +0.30) vs crédit-TD-différé(148, ~0), MÊME
   substrat/gate — pas l'absolu.
2. 3 seeds headline + sondes 1 seed ; le SIGNE (le gate ne débloque pas le prod TD, contrairement au
   REINFORCE) est net et cohérent avec le mécanisme.
3. Le contrôle positif « crédit épisodique + gate » n'est PAS re-couru dans CE banc (il EST EDR-147, même
   substrat `_step`) : cité, pas re-mesuré ici (bornage).
4. Gate additif linéaire + anti-sat quadratique ; optimiseur Adam forcé (SGD prod trop lent pour le gate).
   Le TD différé n'a pas été « réparé » (critique meilleur, TD(λ)) — écarté comme hors-scope : la reco
   est de changer de véhicule de crédit, pas de sauver le TD 1-pas (converge EDR-130 : le crédit ne
   firme pas le gate).
