---
id: EDR-NAV-001
type: EDR
title: Le mur de navigation Lewis est un READOUT_GAP — H représente la direction-cible, la tête d'action ne l'exploite pas
status: accepted
gate: G0
verdict: READOUT_GAP
---

# EDR-NAV-001 : Le mur de navigation est un déficit de READOUT, pas d'encodage

> ID préfixé (convention `SPECIALITES.md`). Territoire NAV. Localise DANS le substrat le mur clos côté
> monde par EDR 090-114b. Banc `tools/nav_localization_probe.py` (tooling-only, `git diff src/` VIDE).

## Question

Le mur de navigation de Lewis est **clos côté MONDE** (EDR 090→114b : énergie, cinématique, sélection,
capacité-réseau, demande, affordance-reward — tous éliminés) : la politique apprise atteint la proie
~0.52 (figées) / ~0.69 (mobiles) contre un oracle glouton 0.875 → le verrou est la **politique/substrat**
(EDR 114). Mais *où* dans le substrat ? La direction-cible est-elle **détruite** par la dynamique
récurrente (encodeur défaillant) ou **présente mais ignorée** par la tête d'action (readout défaillant) ?

## Méthode

**Probe linéaire** (méthodo maison, cf. EDR 120 mémoire AUC~0.90 / EDR 150 ToM). Pendant le forage Lewis
(cohorte fixe de clones du champion — `benchmark_mode` : de-confond `p_reach` d'EDR 114b ET garantit un
H de dimension constante ; n_apex=0, metab=0, conditions maximales d'EDR 107/114), on capture par
(agent, tick) : l'état caché **H** (`a["model"].H_prev`, réécrit par le batch post-forward), l'**obs**
(qui contient dn/ds/de/dw = direction-proie), l'action **correcte** (`env._reach_oracle_action` = l'oracle
glouton d'EDR 114, calculé AVANT le step = positions pré-mouvement), et l'action **émise** (politique
apprise, `explore_eps=0`). On ne garde que les décisions de **navigation** (correct ∈ {N,S,E,O}).

Décodeurs ridge (argmax 4 classes, z-score train-only, split déterministe) : `obs→correct` (sanity),
`H→correct` (encodeur), `H→émise` (sanity readout), et le taux `émise==correct` (comportement).

## Résultat : READOUT_GAP ×2 (figées ET mobiles)

| mesure | figées (n=17411) | mobiles (n=15339) | lecture |
|---|---|---|---|
| obs → correct | 0.968 | 0.949 | SANITY ✓ (la direction est bien dans l'obs) |
| **H → correct** | **0.814** | **0.805** | **l'encodeur PRÉSERVE la direction** (≈ plafond obs) |
| H → émise | 0.906 | 0.877 | H pilote bien le readout |
| émise == correct | 0.022 | 0.031 | l'agent fait le bon pas ~2-3% |
| — dont émise=move | 0.30 | 0.25 | il n'émet un déplacement que 25-30% du temps |
| — correct si move | 0.072 | 0.125 | même en bougeant, direction ≈ hasard (biais anti-aligné) |
| **verdict** | **READOUT_GAP** | **READOUT_GAP** | |

## Lecture (FAIT vs INTERPRÉTATION)

- **FAIT** : la direction-cible est **linéairement décodable de H à ~0.81** (proche du plafond obs 0.95-0.97,
  très au-dessus du hasard ~0.39-0.48). L'état caché **représente où aller**.
- **FAIT** : la politique **n'émet un déplacement que 25-30% du temps** (elle choisit soin/lance/grab 70-75%),
  et même en bougeant la direction est correcte 7-12% (**sous le hasard** → biais moteur non aligné sur la cible).
- **INTERPRÉTATION** : **READOUT_GAP**. Le signal de navigation est *présent et disponible* dans H, mais la
  tête d'action évoluée du champion ne l'exploite pas — un readout linéaire *frais* extrait la direction (0.81)
  là où le readout *évolué* (lui-même linéaire : les logits sont une lecture linéaire des nœuds de sortie)
  mappe H vers des actions non-navigantes ou mal orientées. **Le mur n'est PAS l'encodeur** (la dynamique
  récurrente préserve l'essentiel du signal, atténuation mineure 0.97→0.81) **mais la POLITIQUE/tête d'action**.

- **Cible de migration PRÉCISE** : entraîner par gradient la **tête d'action** (H→action) — la représentation
  est déjà là, pas besoin de refondre l'encodeur récurrent. Un readout différentiable ajusté au signal
  linéairement présent devrait fermer le gap 0.52→0.875.

- **Pont inter-murs** : ce READOUT_GAP relie le mur de navigation au **mur d'énergie** (EDR 094 : soin −10
  compulsif émis même sans menace → famine tick ~5). Même défaut : la politique émet des actions chères
  **non-navigantes** au lieu de foraging. Les deux murs sont possiblement le **même** déficit de readout.

## Caveats / Bornage

1. **Argument linéaire** : « H décode la direction » signifie *linéairement*. La force du finding est que le
   readout du champion EST linéaire et pourrait donc, avec les mêmes features, décoder — mais ne le fait pas.
2. **Composante encodeur mineure non nulle** : H→correct (0.81) < obs (0.96) → ~0.15 de signal perdu dans la
   dynamique. Le déficit est *dominamment* readout, avec une atténuation d'encodeur mineure.
3. **Substrat numpy** (MambaAgent). La localisation vaut pour CE substrat ; l'actionnable (tête d'action par
   gradient) est un *handoff* à la session torch/plasticité — non exécuté ici (coordination `src/`).
4. **R=1 par condition** mais n énorme (17k/15k décisions) → accuracies stables ; figées vs mobiles = 2
   réplications indépendantes concordantes. `p_reach` de la cohorte non re-mesuré ici (repris de 114b).
5. Le taux `correct si move` **sous le hasard** suggère un biais moteur fixe (ex. direction dominante)
   anti-aligné à la cible ; non décomposé par direction (hors périmètre).

## Suite

- **Handoff torch** (pont SUB) : entraîner la tête d'action par gradient sur le signal de navigation déjà
  présent dans H ; cible chiffrée = 0.52→~0.875. À coordonner avec le fil torch (backlog C1-C3).
- Tester si le même probe sur le **mur d'énergie** (émission d'actions chères vs H) montre le même READOUT_GAP
  → unifierait les deux murs.

Lignée : 090 (pas de barreau) → 105/106 (approche=politique) → 107 (substrat bloqué) → 110/113 (capacité/
affordance inertes) → 114/114b (oracle ferme p_reach, mur=substrat) → **NAV-001 (le mur = READOUT)**.
Outil `tools/nav_localization_probe.py`. Étend [[lewis-energy-economy-wall]] + [[sota-gap-substrate]].
