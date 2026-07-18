---
id: EDR-128
type: EDR
title: "Punir Y-sans-X ne force PAS un binding robuste — signal FAIBLE et régime-dépendant : insuffisant sous maintien de X (¬X rare, gap plat même à 5×), et au mieux gap +0.18 saturant avec ¬X fréquent ; le verrou du conditionnement est un MÉCANISME (gating/crédit), pas le signal de tâche"
status: validated
gate: null
verdict: "Levier 1 (signal) d'EDR 126 testé sur le banc compo. On rend Y-sans-X strictement plus punitif que le silence (Y&¬X = −1−p vs ¬Y = −1 ; p=0 ≡ EDR 126). Instrument = binding_gap = P(Y|X) − P(Y|¬X) mesuré DIRECT (p=0 reproduit l'indépendance d'EDR 126). RÉSULTAT régime-dépendant : (1) sous maintien de X (fade1.0, ¬X rare ~6-13%), la pénalité échoue MÊME à 5× (gap plat ~−0.04 à −0.26, y_rate GELÉ 0.722 aux 4 doses) — l'agent fait X PLUS (évite la punition) au lieu de conditionner. (2) Avec ¬X fréquent (fade0.0, ~38%), un gap POSITIF FAIBLE émerge (0.068→0.184 à p=1) mais SATURE (~0.14 à p≥2, jamais fort >0.5) et se dégrade en SUPPRESSION (y_rate 0.73→0.39 à p=5, P(Y|¬X) tombe mais P(Y|X) aussi). Punir Y-sans-X ne force PAS un binding robuste : effets dominants = monter P(X) + supprimer Y, pas conditionner Y sur did_x. Le verrou est un MÉCANISME (gating did_x→logits Y / routage de crédit), pas le signal de tâche. Legacy s'effondre en suppression, ne binde jamais. Élimine le levier 1 comme suffisant → leviers 2 (archi) / 3 (crédit)."
---

# EDR 128 : Punir Y-sans-X ne force pas un binding robuste — signal FAIBLE, le verrou est un mécanisme

## Question

EDR 126 a isolé le verrou résiduel de la composition means→ends : le **binding conditionnel est
absent** (Y ⊥ did_x ; torch monte les marginales, ne conditionne pas Y sur X). EDR 126 nommait trois
leviers pour forcer le conditionnement. Ce chantier teste le **levier 1, le plus simple** : un **signal
de tâche** qui punit Y-sans-X suffit-il à forcer le binding, sans toucher l'archi ni la règle de crédit ?

## Méthode

Banc `tools/substrate_ab_compositional.py` (tâche X-gate-Y, obs_b sans did_x → mémoire récurrente
obligatoire, EDR 117-126). Extension **rétrocompatible** :

- `compositional_reward_penalized(move2, target_y, did_x, y_without_x_penalty)` : Y&X → +1 ;
  **Y&¬X → −1 − penalty** (surcoût) ; ¬Y → −1. À `penalty=0` ≡ `compositional_reward` EXACTEMENT.
  **Motivation** : le baseline donne le MÊME −1 à « Y-sans-X » et au silence → aucune pression
  DIFFÉRENTIELLE pour conditionner. `penalty>0` rend le silence strictement préférable à Y-sans-X.
- Instrument de binding : `binding_gap = P(Y|X) − P(Y|¬X)`, les deux conditionnels mesurés DIRECT
  (`_p_y_given_x` / `_p_y_given_not_x`). Distingue **binding** (gap>0), **marginal-raising**
  (gap≈0, EDR 126) et **suppression triviale** (les deux → 0).
- `sweep_binding_penalty` : dose-réponse penalty × backend × seed. warmup=150/compo=250, 5 seeds.

## Résultats

**(1) Sous maintien de X (fade1.0, ¬X rare) — SIGNAL INSUFFISANT.** torch, médianes 5 seeds :

| penalty | P(Y\|X) | P(Y\|¬X) | gap | y_rate | ¬X freq |
|--------:|--------:|---------:|------:|-------:|--------:|
| 0.0 | 0.678 | 0.843 | −0.258 | 0.722 | 0.135 |
| 0.5 | 0.683 | 0.825 | −0.258 | 0.722 | 0.121 |
| 1.0 | 0.688 | 0.806 | −0.244 | 0.722 | 0.109 |
| 2.0 | 0.693 | 0.767 | −0.257 | 0.722 | 0.095 |
| 5.0 | 0.703 | 0.750 | −0.039 | 0.716 | 0.065 |

Le gap reste **plat et négatif** ; `y_rate` **gelé à 0.722** aux 4 premières doses. Sur les trials ¬X,
l'agent joue ENCORE Y ~77-84% du temps malgré la punition. Effet secondaire : la pénalité fait
**monter P(X)** (compo_didx 0.865→0.935) — l'agent évite la punition en faisant X plus, PAS en
conditionnant Y. Le gap négatif au baseline est COHÉRENT avec EDR 126 (P(Y|X) ≤ y_rate).

**(2) Avec ¬X fréquent (fade0.0) — un gap POSITIF FAIBLE émerge mais SATURE.** torch, **médianes 5 seeds**
(mêmes seeds 0-4 ; le run de désambiguïsation fade0.0/p=2 reproduit ces médianes à l'identique — déterminisme, pas mono-seed) :

| penalty | P(Y\|X) | P(Y\|¬X) | gap | y_rate | ¬X freq |
|--------:|--------:|---------:|------:|-------:|--------:|
| 0.0 | 0.695 | 0.744 | 0.068 | 0.734 | 0.623 |
| 1.0 | 0.749 | 0.603 | **0.184** | 0.665 | 0.478 |
| 2.0 | 0.624 | 0.471 | 0.138 | 0.597 | 0.377 |
| 5.0 | 0.441 | 0.224 | 0.139 | 0.389 | 0.270 |

Le gap monte 0.068 → **0.184** (p=1) puis **sature ~0.14** — jamais fort (binding solide exigerait
>0.5 ; P(Y|¬X) ne descend jamais sous 0.22). À forte pénalité, **suppression** : y_rate 0.73→0.39,
les DEUX conditionnels chutent. Le « conditionnement » de p=5 est en partie de la suppression.

**Legacy** : décline vers la suppression à toute pénalité (P(Y|X) 0.46→0.21, y_rate 0.40→0.16),
gap ≈0, hit 0.14→0.09 — ne binde jamais (crédit-limité, cohérent 122/126).

## Interprétation

**Punir Y-sans-X ne force PAS un binding robuste.** Le signal a une **tension structurelle** : forcer le
conditionnement exige des trials ¬X FRÉQUENTS pour que le gradient différentiel morde, MAIS maintenir X
(nécessaire au joint, EDR 126) rend ¬X rare. Et même dans le régime le plus favorable (¬X ~38%), le
signal n'induit qu'un conditionnement **faible et saturant** (gap ≤0.18), avec deux effets parasites
dominants : monter P(X) et, à forte dose, supprimer Y. Le substrat ne **route** pas la mémoire did_x
(présente, décodable AUC~0.90 EDR 120) vers le logit Y ; un signal de tâche ne l'y contraint pas.

→ **Le verrou du conditionnement est un MÉCANISME** (gating explicite did_x→logits Y, ou routage de
crédit type éligibilité/TD(λ)), **pas le signal de tâche**. Le levier 1 est **éliminé comme suffisant** ;
restent les leviers **2 (archi/gating)** et **3 (crédit)** d'EDR 126.

## Bornage / honnêteté

- **n=5, micro-tâche proxy, médianes** (puissance plancher). Pas de transfert apex.
- Le gap NÉGATIF au baseline (P(Y|¬X) > P(Y|X)) est cohérent avec EDR 126 (P(Y|X) ≤ y_rate) mais son
  signe est secondaire ; c'est la **platitude vs dose** (régime maintien-X) et la **saturation faible**
  (régime ¬X-fréquent) qui portent le verdict.
- **P(Y|¬X) est un estimateur À HAUTE VARIANCE dans le régime maintien-X** : ¬X y est rare (6-14% →
  dénominateur ~15-35 trials/fin de phase), et P(Y|¬X)=1.000 exact sur certains seeds → le GAP y est
  bruité. C'est justement pourquoi le point PORTEUR du verdict dans ce régime est la **platitude du
  y_rate marginal** (gelé 0.722, robuste), PAS le gap. Le gap ne devient un instrument fiable que dans
  le régime ¬X-fréquent (fade0.0), où il porte la conclusion « faible et saturant ».
- « **Suppression** » est employé au sens PROSE (chute du y_rate marginal, ex. fade0.0/p=5 : 0.73→0.39),
  distinct du seuil-machine `SUPPRESSION` de `sweep_binding_penalty` (déclenché sur P(Y|X)<0.20).
  fade0.0 n'est PAS passé par le verdict auto (runs manuels) → pas de contradiction, juste deux
  acceptions du mot.
- Confonds ASSUMÉS et mesurés : la pénalité monte P(X) et supprime Y — c'est justement pourquoi elle
  ne « binde » pas (elle contourne le conditionnement). ¬X-fréquence obtenue via fade0.0 = X non
  maintenu (compo_didx plus bas) : régime favorable au signal MAIS défavorable au joint.
- `penalty=0` reproduit EDR 126 (garanti structurellement : `compositional_reward_penalized(...,0)`
  ≡ `compositional_reward`). Instrument `binding_gap` = extension directe de la mesure P(Y|X) d'EDR 126.
- Verdict `sweep_binding_penalty` = SIGNAL_INSUFFICIENT sur son régime par défaut (fade1.0) ; la nuance
  « faible mais non nul avec ¬X fréquent » vient des runs de désambiguïsation (fade0.0).

Outils : `tools/substrate_ab_compositional.py` (`compositional_reward_penalized`, `_p_y_given_not_x`,
`run_curriculum_fade(y_without_x_penalty=)`, `sweep_binding_penalty`). Tests
`tests/sandbox/test_substrate_ab_compositional.py`. Étend EDR 126 (binding absent) ; oriente vers
leviers archi/crédit. Cf. EDR 120 (mémoire présente non utilisée), EDR 122 (split torch/legacy).
