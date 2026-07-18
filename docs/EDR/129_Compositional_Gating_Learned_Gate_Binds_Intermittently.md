---
id: EDR-129
type: EDR
title: "Levier 2 (gating archi did_x→logits Y) : un gate explicite entraînable DÉBLOQUE le binding compositionnel (7/10 seeds, gap 0.37-0.68) là où le substrat de base ne binde JAMAIS — mais uniquement quand conditionner est incité (pénalité + ¬X fréquent) et de façon intermittente (3/10 collapse en always-Y) ; le verrou est SUBSTANTIELLEMENT la structure de routage (actionnable migration), l'optimisation reste un co-facteur"
status: validated
gate: null
verdict: "Levier 2 d'EDR 126 (le binding est-il un problème de ROUTAGE ?). On ajoute un GATE sur le logit Y en phase B, 3 modes : none (baseline), oracle (biais câblé ±selon did_x VRAI = plafond), learned (readout linéaire entraînable de H_S2 → biais Y, REINFORCE sur reward2). ORACLE → gap 1.000 (5/5) : router did_x→Y RÉSOUT la tâche (plafond, valide l'instrument). NONE → gap ~0.09 (jamais >0.2) : le substrat de base ne binde pas (reproduit 126/128). LEARNED sous récompense NON-incitative (fade1.0, pen0) → collapse en always-Y (P(Y)=1.0, gap 0) car always-Y y est optimal (X fait ~92% → confond, pas un échec de routage). LEARNED sous récompense INCITATIVE (fade0.0 → ¬X fréquent ; penalty=2 → silence −1 > Y-sans-X −3) → BINDING sur 7/10 seeds (gap 0.37-0.68, P(Y|X)~1.0 / P(Y|¬X)~0.3-0.6), 3/10 collapse. Conclusion : le verrou du conditionnement est SUBSTANTIELLEMENT la STRUCTURE DE ROUTAGE — donner au substrat un mécanisme explicite qui lit H_S2 (did_x décodable, EDR 120) et module le logit Y DÉBLOQUE un binding que le head de base n'atteint jamais. ACTIONNABLE pour la migration. Les 3/10 collapses → l'optimisation/crédit (levier 3) reste un co-facteur. Recette = gate structurel (levier 2) + régime où conditionner est optimal (insight levier 1/EDR 128)."
---

# EDR 129 : Levier 2 (gating) — un gate appris débloque le binding (7/10), le verrou est la structure de routage

## Question

EDR 126 a isolé le verrou de la composition : binding conditionnel absent (Y ⊥ did_x). EDR 128 a
éliminé le **levier 1 (signal)** : punir Y-sans-X ne force pas un binding robuste. Reste le **levier 2** :
le verrou est-il un problème de **ROUTAGE** ? Si on donne au substrat une structure explicite pour router
did_x → logit Y, le binding émerge-t-il ?

## Méthode

`run_curriculum_fade_gated` : curriculum à fade + GATE sur le logit Y en phase B. Action Y échantillonnée
d'un softmax (règle commune aux 3 modes). Modes :
- **none** : biais Y = 0 (baseline, contrôle négatif).
- **oracle** : biais CÂBLÉ ±`oracle_bias` selon did_x VRAI → force le conditionnement à la décision
  (CONTRÔLE POSITIF = plafond ; valide que l'instrument détecte le binding).
- **learned** : gate LINÉAIRE entraînable `biais_Y = w·H_S2 + b`, entraîné par **REINFORCE** sur reward2
  (avantage = reward − baseline glissant). Teste si le substrat APPREND à router did_x (décodable de
  H_S2, EDR 120) quand on lui donne la STRUCTURE.

Instrument = `binding_gap = P(Y|X) − P(Y|¬X)` (EDR 128). Backend torch, warmup=150/compo=250.

## Résultats

**Contrôles (régime plain, fade1.0/pen0), médianes 5 seeds :**

| mode | P(Y\|X) | P(Y\|¬X) | gap | y_rate |
|------|--------:|---------:|-----:|-------:|
| none | 0.279 | 0.258 | 0.009 | 0.282 |
| oracle | 1.000 | 0.000 | **1.000** | 0.893 |
| learned | 1.000 | 1.000 | **0.000** | 1.000 |

- **oracle → gap 1.000** : router did_x→Y RÉSOUT la tâche (plafond, instrument validé).
- **none → gap ~0** : le substrat de base ne binde pas (reproduit 126/128).
- **learned → gap 0 MAIS P(Y)=1.0 partout** : collapse en **always-Y**. CONFOND identifié : sous
  `compositional_reward` (¬Y=−1) + fade (X fait ~92%), always-Y est OPTIMAL (0.92·(+1)+0.08·(−1)=+0.84 ;
  et sur ¬X, jouer Y ou se taire = −1 → aucune incitation à conditionner). Le gate ne « rate » pas le
  routage — router n'est **pas incité**.

**Condition décisive (régime INCITATIF : fade0.0 → ¬X fréquent ; penalty=2 → silence −1 > Y-sans-X −3),
gate appris, 10 seeds :**

| seeds | gap | verdict |
|-------|-----|---------|
| 1, 2, 5, 6, 7, 8, 9 (**7/10**) | **0.37 – 0.68** | BINDING (P(Y\|X)~1.0, P(Y\|¬X)~0.3-0.6) |
| 0, 3, 4 (3/10) | ~0.00 | collapse always-Y (P(Y)~1.0) |

**7/10 seeds atteignent un binding RÉEL** (gap 0.37-0.68), que le substrat de base (none, gap ~0.09)
n'atteint JAMAIS. Le gate est **bimodal** : il binde ou collapse en always-Y (la médiane brute masque le
signal → on rapporte le PER-SEED).

## Interprétation

**Le verrou du conditionnement est SUBSTANTIELLEMENT la STRUCTURE DE ROUTAGE.** Donner au substrat un
mécanisme explicite qui lit l'état récurrent H_S2 (où did_x est décodable, EDR 120) et module le logit Y
**DÉBLOQUE** un binding que le head de base ne produit jamais — 7/10 seeds, approchant le plafond oracle.
C'est le premier levier POSITIF de la chaîne 104-129 : ni capacité, ni taille, ni sélection, ni signal ne
débloquaient ; **une structure de gating oui**.

**Recette complète = gate structurel (levier 2) + régime où conditionner est optimal (insight EDR 128).**
Sans l'incitation (récompense plain), même le gate collapse en always-Y. Les deux sont nécessaires.

**Conséquence migration** : le substrat torch-en-prod devrait embarquer un **mécanisme de conditionnement
explicite** (gate did_x→action), pas seulement plus de capacité/optimiseur. Les 3/10 collapses → l'
**optimisation/crédit (levier 3) reste un co-facteur** : le gate tombe parfois dans l'optimum facile
always-Y ; une réduction de variance / meilleur crédit (éligibilité) firmerait la fiabilité.

## Bornage / honnêteté

- **n=10** (condition décisive), n=5 (contrôles) ; micro-tâche proxy ; pas de transfert apex.
- **Taux 7/10 hétérogène par bloc de seeds** : seeds 0-4 → 2/5 bindent, seeds 5-9 → 5/5. Le « 7/10 »
  agrège deux sous-ensembles très différents → le taux de succès n'est PAS stable ; la conclusion
  robuste est QUALITATIVE (« le gate PEUT binder, là où le base ne peut jamais »), pas le taux exact.
- **oracle = force à la DÉCISION** (biais ±8 sur le logit) : plafond quasi-tautologique, sert de
  validation d'instrument (« le binding est détectable et la tâche solvable par routage »), pas de preuve
  d'apprentissage.
- Le gate learned = **readout LINÉAIRE** de H_S2 + **REINFORCE** (action échantillonnée, baseline
  glissant) : c'est la structure la plus simple ; sa réussite (7/10) montre que la linéarité suffit
  (cohérent EDR 120 : did_x linéairement décodable). Un gate multiplicatif/non-linéaire n'a pas été testé.
- Régime décisif fade0.0 = X NON maintenu (compo_didx ~0.5-0.7) : favorable au conditionnement (¬X
  fréquent) mais bas sur P(X) — c'est un régime de MESURE du binding, pas de maximisation du joint.
- `none` sous échantillonnage reproduit le baseline (gap ~0.09 ≈ EDR 128 fade0.0/pen2 +0.14, léger écart
  dû à l'exploration softmax).
- Le seuil `bind_thresh=0.3` (gap fort) est heuristique ; la distribution per-seed est bimodale et nette
  (7 seeds >0.36, 3 seeds ~0), robuste au seuil.

Outils : `tools/substrate_ab_compositional.py` (`run_curriculum_fade_gated`, `compare_gate_modes`).
Tests `tests/sandbox/test_substrate_ab_compositional.py` (dont contrôle positif oracle). Étend EDR 126
(binding absent), 128 (signal insuffisant), 120 (did_x décodable de H_S2). Pointe vers levier 3 (crédit)
pour firmer les 3/10 collapses.
