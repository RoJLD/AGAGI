---
id: EDR-115
type: EDR
title: Le substrat gradient (autograd) bat le hebbien sur la learnabilité — barreau-0 de l'Axe 1
status: validated
gate: null
verdict: GRADIENT_GAGNE (barreau-0 ; PAS un transfer_ratio)
---

# EDR 115 : Substrat gradient > hebbien sur la learnabilité (Axe 1, barreau-0)

## Contexte

Les EDR 104-111 ont convergé : le verrou de l'apprentissage n'est ni le monde, ni la sélection,
ni la taille du réseau, mais le **SUBSTRAT** (capacité d'apprentissage). L'audit SOTA (mémoire
`sota-gap-substrate`) a montré que le moteur « neuronal » est du numpy pur (gradient dérivé à la
main, connectome ~172 nœuds dont ~5 cachés), et que le « Mamba » est un Liquid Time-Constant
network réimplémenté (REF-LTC-2021) **privé de l'entraînement par gradient** qui le rend SOTA.
ADR-003 a posé l'abstraction de backend (frontière population, framework différé, numpy gardé).
Cet EDR mesure le **1er barreau** : sur ce substrat, le gradient (autograd) apprend-il mieux que
le hebbien/TD dérivé à la main ?

## Méthode

A/B apparié `tools/substrate_ab.py` via l'interface `PopulationModel` (`make_population(backend=)`).
**1 variable = la règle d'apprentissage**, substrat IDENTIQUE :
- `legacy` = `MambaBatchModel` numpy (Actor-Critic TD / hebbien dérivé main) ;
- `torch` = même dynamique LTC + **même Actor-Critic TD, gradient par AUTOGRAD**.
Tâche : contingence contrôlée (obs fixe → action cible `move`), récompense ±1 sur argmax. Métrique
= Δ taux de bonne action (fin − début). Verdict par **test de signe** apparié, multi-seed.

## Constat — GRADIENT_GAGNE, robuste à la puissance

| n seeds | verdict | médiane diff (torch−legacy) | seeds favorables | sign_p |
|---|---|---|---|---|
| 5 | GRADIENT_GAGNE | +0.358 | 5/5 | 0.062 (plancher n=5) |
| **10** | **GRADIENT_GAGNE** | **+0.429** | **10/10** | **0.002** |

torch apprend la contingence sur **tous** les seeds (Δ +0.20 à +0.64) ; legacy est incohérent
(4/10 Δ négatifs, max +0.26). Le signal **se renforce sous puissance** (0.062 → 0.002) — au
contraire des 5 signaux qui s'étaient évaporés dans l'historique du projet (057/075/077/082/083).
**Sur ce substrat, l'apprentissage par gradient a une capacité que le hebbien dérivé main n'a pas**,
cohérent avec le diagnostic SUBSTRAT des EDR 104-111.

## Caveats (honnêteté — PORTÉE LIMITÉE)

1. **CE N'EST PAS un `transfer_ratio`** (north-star G1). C'est une **micro-tâche mono-contingence,
   obs fixe** : une mesure de *learnabilité*, pas une preuve de transfert ni que le verrou est cassé.
2. **legacy non tuné** : les taux d'apprentissage hebbien/TD numpy sont ceux de prod, pas optimisés
   pour cette tâche. L'écart mesure « tel quel », pas un plafond théorique du hebbien.
3. **Goulot pour l'A/B réel** : c'est `env.step()` (le monde) qui possède le batching → faire vivre
   un substrat torch en prod exige le **contrat forward COMPLET** (NTM/attention/world-model/108
   sorties), gros chantier multi-sessions. Ce barreau-0 est la **porte de décision** qui le justifie.
4. **Substrat torch = MVP** : cœur LTC + Actor-Critic TD (move/grab/rub), pas d'organes (NTM/router/
   TTC), dimensions homogènes.

## Conséquences

- **Porte de décision VERTE** : investir dans l'intégration monde complète (torch dans `env.step()`)
  est désormais justifié par une mesure, pas une intuition. Si le gradient avait perdu ici, on
  s'épargnait le chantier.
- Adoption REF-LTC-2021 / ADR-003 confirmée au niveau learnabilité (`REF-LTC -A_ADOPTER_POUR-> EDR-115`).
- Suite : (a) compléter le contrat forward torch ; (b) threader `backend=` dans le moteur-monde ;
  (c) **A/B `transfer_ratio` réel** torch vs legacy (north-star G1, powered, budget compute pensé).
- Outils : `src/agents/backend.py` + `backend_torch.py` ; `tools/substrate_ab.py`. Commits
  21c5625→e23ba73 (branche `feat/d1-prod-pairing`).
