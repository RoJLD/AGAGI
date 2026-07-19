---
id: EDR-WARM-004
type: EDR
title: "Le plateau de survie du DAgger est SUR-DÉTERMINÉ : couverture (−0.22 hors du vécu) ET précision aux états critiques (−0.23 en basse énergie) contribuent, aucun ne domine"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
EDR-WARM-003 a laissé une hypothèse OUVERTE : DAgger monte `acc_on-policy` à 0.99 et double la survie
(15→35, marqueur 5.04) mais plafonne loin de l'oracle (200). Pourquoi ?
- **(a) COUVERTURE** : le learner meurt à ~35 → ne visite jamais les états tardifs → ne les apprend pas
  (et l'`acc_on-policy` mesurée est tronquée à la fenêtre pré-mortem, donc quasi-tautologique).
- **(b) PRÉCISION** : il « sait » partout, mais ses erreurs résiduelles tombent aux états critiques
  (basse énergie, où une erreur est fatale).

## Méthode
Deux mesures aux comparaisons INTERNES à chaque test (`tools/warmstart_evolution_inworld.py`) :
- **Instrument** : `_collect_diag_trajectory` (trajectoire PLEINE LONGUEUR — aucune troncature à la 1ʳᵉ
  mort, contrairement à `_collect_oracle_trajectory` —, MASQUÉE, alignée à travers les morts par
  `id(model)`, avec l'ÉNERGIE lue au moment de la DÉCISION) + `accuracy_binned` (replay PUR torch,
  `no_grad`, W gelé, sans monde) + `bins_by_tick` / `bins_by_energy`.
- **(A) COUVERTURE** : accuracy du génome DAgger sur les états de l'**ORACLE**, binnée par TICK. Les bins
  > 35 sont des états que le learner **ne visite jamais**. Test PROPRE : mêmes états imposés pour tous,
  aucune sélection par le comportement du génome.
- **(B) PRÉCISION** : accuracy sur **son propre** rollout, binnée par ÉNERGIE (comparaison interne
  basse vs haute énergie).
Génome DAgger reproduit (6 rounds, seed 2026) puis **PERSISTÉ** (`results/warm003_dagger_genome.npz`) —
il n'avait pas été sauvé en WARM-003, ce qui avait coûté une reproduction de 40 min ; le re-diagnostic
ne coûte plus que ~2 min.

## Résultats

**(A) COUVERTURE — acc sur les états de l'ORACLE, par bin de tick**

| ticks | 0-35 (son vécu) | 35-70 | 70-120 | 120+ |
|---|---|---|---|---|
| **acc** | **0.931** | 0.795 | 0.734 | **0.713** |
| n | 420 | 385 | 512 | 734 |

**(B) PRÉCISION — acc sur son propre rollout, par bin d'énergie**

| énergie | 0-20 | 20-40 | 40-60 | 60-80 | 80+ |
|---|---|---|---|---|---|
| **acc** | 0.844 | **0.762** | 0.973 | **0.992** | 1.000 |
| n | 160 | 193 | 110 | 126 | 17 |

- **Écart COUVERTURE** : 0.931 → 0.713 = **0.218**. Dégradation MONOTONE, bien alimentée (n ≥ 385/bin).
  Ce n'est PAS un effondrement (0.713 ≫ hasard 0.25) : le génome généralise PARTIELLEMENT hors de son
  vécu, mais perd 22 points.
- **Écart PRÉCISION** : 0.992 → 0.762 = **0.230**, sur des bins bien alimentés (n=160/193 en bas).

## Verdict
**`SURVIVAL_PLATEAU_IS_OVERDETERMINED_COVERAGE_AND_PRECISION_BOTH_CONTRIBUTE`** — l'hypothèse ouverte de
WARM-003 est TRANCHÉE : **ce n'est ni l'un NI l'autre exclusivement, ce sont LES DEUX**, avec des
magnitudes comparables (0.218 vs 0.230). Le plateau à ~35 est **sur-déterminé** :
1. plus le learner survit, plus il entre dans des états dont il a MOINS de couverture (acc −0.22) ;
2. et il passe plus de temps en basse énergie, là où son accuracy est la PIRE (−0.23) — précisément où
   une erreur est fatale.
Les deux se COUPLENT en spirale (moins de couverture → erreurs → énergie plus basse → zone de moindre
accuracy → mort), ce qui explique pourquoi DAgger améliore réellement (chaque round étend la couverture)
mais LENTEMENT (la généralisation hors-couverture est faible, et le régime basse-énergie reste mal maîtrisé).

**Corollaire pour WARM-003** : sa métrique `acc_on-policy=0.99` était bien TRONQUÉE — l'accuracy vraie
sur l'horizon complet de la tâche est ~0.71-0.79, pas 0.99. Le diagnostic de la revue finale (« 0.99 =
fenêtre survivable, pas maîtrise ») est CONFIRMÉ quantitativement.

## ⚠️ Asymétrie de rigueur entre les deux tests (à ne pas gommer)
- **Test (A) est causalement PROPRE** : les états sont imposés par l'oracle, identiques quel que soit le
  comportement du génome → l'écart mesure bien une généralisation défaillante.
- **Test (B) est CORRÉLATIONNEL** : les états basse-énergie sont peuplés par des agents qui ont DÉJÀ
  commis des erreurs → **la causalité inverse n'est pas exclue** (les erreurs causent la basse énergie
  plutôt que l'inverse), et elle est même parcimonieuse. Donc « précision aux états critiques » est
  ÉTABLI comme CORRÉLATION, pas comme cause. Trancher exigerait une intervention (p.ex. imposer une
  énergie basse à énergie-initiale variée et mesurer l'accuracy à comportement passé égal).
Le verdict « LES_DEUX » repose donc sur un pied solide (A) et un pied corrélationnel (B).

## Portée & limites
- Seuils de verdict (écart ≥ 0.10) arbitraires mais explicites ; tous les bins et leurs `n` sont imprimés
  → conclusion auditable, pas de boîte noire. Le bin énergie 80+ (n=17) est trop peu alimenté pour peser
  (le comparateur haute-énergie applique un plancher n≥30).
- Un seul génome / une seule seed (2026) : l'écart est net et monotone mais non répliqué sur seeds.
- Le test (A) rejoue le génome sur la trajectoire de l'ORACLE : son H suit l'historique de l'oracle. C'est
  le contrefactuel voulu (« s'il se trouvait là, déciderait-il juste ? »), pas « y arriver par lui-même ».
- **Correction de conception en cours de route** : la 1ʳᵉ règle de verdict comparait low-énergie (test B)
  à late (test A) — deux trajectoires DIFFÉRENTES ; corrigée en comparaisons internes à chaque test
  (commit `1c54301`). Le run initial affichait `NI_COUVERTURE_NI_PRECISION` par cet artefact de seuils.

## Levier suivant (motivé par CE résultat)
La spirale couverture↔énergie suggère deux attaques complémentaires : (1) **amorcer la couverture tardive
sans avoir à survivre** (démarrer des rollouts DAgger à des états tardifs/basse-énergie de l'oracle —
« reset distribué » plutôt que toujours depuis t=0) ; (2) **pondérer l'imitation par la criticité**
(sur-échantillonner les états basse-énergie dans le dataset agrégé). La (1) attaque le pied SOLIDE du
verdict, la (2) le pied corrélationnel — à privilégier dans cet ordre.

Converge [[EDR-WARM-003]] (ferme son hypothèse ouverte), [[EDR-WARM-001]], [[EDR-WARM-002]],
[[within-subject-demand-marker]], REF-DEMAND-MARKER, S2-009.
