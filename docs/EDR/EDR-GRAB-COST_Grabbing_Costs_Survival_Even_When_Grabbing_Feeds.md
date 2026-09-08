---
id: EDR-GRAB-COST
type: EDR
title: "Le GRAB coûte la survie même quand grabber NOURRIT : retirer l'action améliore la survie médiane de 39 % (28+/2−, sign p = 8.7e-07, n = 30 ères, 3/3 seeds) — sur un instrument dont le plancher de bruit est mesuré EXACTEMENT NUL"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
---

## Question

P4.1, seule question restée ouverte sur quatre records : **le grab nuit-il quand grabber NOURRIT ?**
Le régime de famine dure porte `forage_payoff = 3.0` — ramasser un fruit RAPPORTE. Si le grab coûtait
malgré cela, ce serait la taxe de PORTAGE, pas la collecte, qui domine.

## Résultat

Quatre bras, champion à génome INTACT, `FamineWorld`, 3 champions (s42/s43/s44) × 10 ères = **30 ères**,
20 agents, 400 ticks. Unité de réplication = l'**ÈRE**, déclarée au pré-vol. Les ères sont APPARIÉES :
`run_condition` fait `seed_at(seed, i)`, donc l'ère *i* de chaque bras voit le MÊME monde.

| bras | n | médiane | moyenne | vs intact |
|---|---|---|---|---|
| intact | 30 | 29.25 | 31.73 | — |
| `NullGrabOffMamba` (no-op) | 30 | **29.25** | **31.73** | **bit-identique** |
| `GrabOffMamba` | 30 | **40.75** | 44.30 | **+39 %** |
| `GrabForcedMamba` (inverse) | 30 | 28.75 | 29.40 | −1.7 % |

**Apparié par ère :**
* `grab_off` vs intact : **28+ / 2−**, médiane des différences **+10.75**, sign **p = 8.7e-07**
* `grab_off` vs `grab_force` : 29+ / 1−, **p = 5.8e-08**
* `grab_force` vs intact : 10+ / 18−, médiane −0.75, **p = 0.185 — NON significatif**

Cohérent sur les **3 seeds** : ratios `grab_off`/intact de **1.29, 1.39, 1.50**. Aucune distribution
dégénérée (`assert_not_degenerate` passe sur les trois bras).

## Ce qui est ÉTABLI, et ce qui ne l'est PAS

**ÉTABLI — retirer le grab AMÉLIORE la survie**, largement, sur les 30 ères appariées et les 3 seeds.
Dans un régime où ramasser NOURRIT, l'action de ramasser coûte donc plus qu'elle ne rapporte.

**NON ÉTABLI — la dose-réponse.** La manipulation INVERSE (forcer le grab à chaque tick) va dans le bon
sens mais **n'est pas significative** (p = 0.185). Le contraste est asymétrique : retirer change
beaucoup, forcer change peu. L'explication naturelle — le champion grabbe déjà souvent, donc forcer
n'ajoute presque rien — est **plausible et NON MESURÉE** ; elle demande le taux de grab in situ, qui
n'est pas relevé ici.

⚠️ **Ce que le bras inverse établit QUAND MÊME, et c'est ce pour quoi il existait** : il RÉFUTE
« toute perturbation de la colonne 24 améliore la survie ». `grab_force` perturbe exactement la même
sortie et n'améliore rien (10+ / 18−). Sans lui, l'effet de `grab_off` resterait compatible avec un
artefact d'ablation.

## Pourquoi cet instrument est lisible — le plancher de bruit est mesuré NUL

`NullGrabOffMamba` fait EXACTEMENT le même travail que l'ablation (copie du tableau de sortie, garde
d'aliasing, écriture dans la colonne 24) mais **réécrit la valeur qu'il vient de lire**. Résultat :
**bit-identique au bras intact sur les 30 ères**.

C'est la différence structurelle avec la sonde sœur, et elle est décisive :
`PerceptionAblatedMamba` appelle `derange_rows`, qui **consomme des tirages** du flux global et déplace
la bande aléatoire — d'où sa bande de bruit mesurée **[0.92 ; 1.06]**, dans laquelle son propre résultat
publié (0.991) tombe. Ici, écrire une constante dans une sortie ne consomme AUCUN tirage.

L'effet mesuré (+39 %) est donc lu contre un plancher de **zéro**, pas contre ±8 %.

⚠️ **Aliasing**. Écrire dans une sortie de `forward` peut muter l'état récurrent quand cette sortie est
une VUE — le bug d'EDR-WARM-007, qui avait produit dose-réponse, corrélations et contrôle négatif
cohérents pendant une passe entière. Vérifié ici avant d'écrire (backend legacy : `preds.base is None`,
aucun partage mémoire avec les 16 tableaux internes) ET `assert_no_aliasing` tourne à CHAQUE appel des
trois classes.

## Portée, et ce qu'elle exclut

* **Régime** : famine dure uniquement (`FamineWorld`, défauts du module), `night_enabled = False` et
  `benchmark_mode = True` comme tout `run_condition` — donc PAS le régime nocturne où la taxe de
  portage joue différemment.
* **Réplication** : l'ÈRE. ⚠️ Déclaré, pas caché : les 10 ères d'un même champion sont SÉRIELLEMENT
  dépendantes. La lecture conservatrice (n = 3 seeds) laisserait le signe intact — 3/3 dans le même
  sens — mais sous le `n_floor = 12` du marqueur de demande.
* **Ce qui n'est PAS mesuré** : le taux de grab in situ, le bilan énergétique (`trace_energy_sinks`),
  et l'effet à `forage_payoff` variable. Le MÉCANISME reste donc ouvert : on sait que le grab coûte, on
  ne sait pas encore par quel canal.

## Matériel

30 champions vérifiés (`data/hof_famine_harsh_s{42,43,44}.pkl`, 10 par seed, 0 fichier d'état
manquant sur 30 références). Classes : `tools/s2_demand_ablation.py::{GrabOffMamba, NullGrabOffMamba,
GrabForcedMamba}`. Mesures brutes : `results/p41_grab_famine.json`. Sous bail `kuzu`, 184 s de calcul.
