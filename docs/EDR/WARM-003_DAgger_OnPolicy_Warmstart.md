---
id: EDR-WARM-003
type: EDR
title: "DAgger on-policy monte l'acc_on-policy (métrique) 0.73→0.99 et DOUBLE la survie (marqueur 5.04, le plus fort de l'arc), mais plafonne loin de l'oracle : gap résiduel = COUVERTURE (hypothèse principale) vs précision, non départagé"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
WARM-001 a MESURÉ que le mur de l'imitation-enseignant est le TRANSFERT : `acc_on-policy` plafonne à 0.734
(le génome pilotant ses propres états) malgré `acc_enseignant=1.000`, à cause de la dérive de l'état
récurrent. Le levier canonique = **DAgger** : entraîner sur les états que le LEARNER visite lui-même
(réétiquetés par l'oracle). Casse-t-il le 0.734, et la survie décolle-t-elle vers l'oracle (200) ?

## Méthode
`tools/warmstart_evolution_inworld.py::run_dagger_warmstart` (torch). Round 0 = bootstrap sur la
trajectoire-ENSEIGNANT (= WARM-001). Rounds suivants : `_collect_onpolicy_trajectory` (rollout du learner
sous torch W gelé ; séquences fixed-B MASQUÉES alignées par `id(model)` à travers les morts) → réétiquetage
oracle `2*(bit_a>0)+(bit_b>0)` → AGRÉGATION au dataset → réentraînement BPTT récurrent MASQUÉ
(`imitate_episode_bptt(mask_seq=…)`, round-robin borné epochs×rounds). Mesure par round : `_inworld_accuracy`
(acc on-policy) + survie médiane. Verdict marqueur within-subject final (forward torch, K=12). Régime S2-009
(metab=0.75, cog=12). seed=2026, rounds=6, epochs_per_round=3000, num_agents=12.

## Résultats

| round | 0 (bootstrap) | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| **acc_on-policy** | 0.66 | 0.954 | 0.972 | 0.967 | 0.979 | **0.988** |
| **survie médiane** | 10.0 | 26.8 | 28.0 | 30.8 | 33.2 | **35.2** |

Verdict final : **ratio=5.04, intact=35.2, ablé=7.0 → PERCEPTION_DEMANDED (n=12)**.
Repères : WARM-001 (départ) acc_on-policy≈0.73 / survie≈15 / ratio 2.14 ; plancher≈7 ; oracle≈200/ratio≈21.

**Trois faits (dont un à interprétation OUVERTE) :**
1. **DAgger monte la MÉTRIQUE `acc_on-policy`** : ~0.66-0.73 (bootstrap enseignant) → **0.988**. Entraîner
   sur les états auto-visités améliore fortement la décision sur la fenêtre survivable → le plafond mesuré
   par WARM-001 (0.734) est bien franchi EN TANT QUE MÉTRIQUE. (Glose causale « le mur ÉTAIT le transfert,
   réparé on-policy » : à nuancer — voir fait 3, la survie reste 35/200 donc le transfert n'est démontré
   résolu que SUR LA FENÊTRE ≤35, pas sur les 200 ticks.)
2. **La survie DOUBLE et le marqueur se renforce** : survie 15→35 (×2.3, 5× le plancher), marqueur ratio
   2.14→**5.04** (×2.4). C'est le **suiveur-de-signal in-world le plus fort de tout l'arc** — un génome
   APPRIS (pas codé main) dont l'ablation-perception effondre la survie 35→7. Résultat SOLIDE (instrument validé).
3. **MAIS la survie plafonne loin de l'oracle** (~35 vs 200), le trend montant lentement (~+2/round).
   ⚠️ **Interprétation OUVERTE, NON départagée par ce banc** : (a) **hypothèse COUVERTURE** (principale, plus
   parcimonieuse, anticipée par le spec) — le learner meurt à ~35 → ne VISITE jamais les états tardifs
   basse-énergie → DAgger ne peut ni les collecter ni les apprendre ; le plateau de survie et la fenêtre où
   l'accuracy est mesurée sont **LE MÊME HORIZON (≤35)**, pas deux faits qui « découplent » ; le cercle
   vertueux DAgger (survivre plus → couvrir plus) est LENT. (b) hypothèse précision — erreurs résiduelles aux
   états critiques. **Biais de mesure clé** : `_inworld_accuracy` est TRONQUÉE (n'accumule que tant qu'un
   agent vit, ~ticks 0-35) et à BIAIS-SURVIVANT (sous-ensemble vivant) → `acc=0.99` = « 0.99 sur la fenêtre
   survivable courte », PAS l'accuracy sur l'horizon-oracle 200. Corroborant arithmétique : à 1% d'erreur iid
   la survie attendue ≈ 100 (pas 35) → le taux d'erreur pertinent-survie dépasse le 0.99 mesuré (symptôme de
   sur-estimation par troncature OU d'erreurs fatales CONCENTRÉES = couverture). **Départager exige une mesure
   conditionnée (acc par bin de tick/énergie, ou acc du génome sur les états TARDIFS de l'oracle) — non faite.**

## Verdict
**`DAGGER_LIFTS_ONPOLICY_METRIC_AND_DOUBLES_SURVIVAL_RESIDUAL_MECHANISM_OPEN`** — POSITIF PARTIEL (le plus
fort in-world de l'arc). PASS sur le MARQUEUR (PERCEPTION_DEMANDED fort, ratio 5.04) ; FAIL sur la barre de
survie (35 < mi-chemin oracle 100). **Établi (mesuré)** : la correction on-policy lève la métrique
`acc_on-policy` (0.73→0.99 sur la fenêtre survivable) et DOUBLE la survie (15→35), renforçant le marqueur
×2.4 — un vrai suiveur-de-signal APPRIS. **NON établi (à ne pas sur-interpréter, leçon WARM-001)** : le
MÉCANISME du gap résiduel (~35 vs 200). L'hypothèse principale (parcimonieuse) est un **mur de COUVERTURE**
(le learner ne visite/n'apprend jamais les états tardifs qu'il faudrait pour survivre, le cercle vertueux
DAgger étant lent), PAS forcément une « précision aux états critiques » — le banc ne les départage pas
(`_inworld_accuracy` est tronquée à la fenêtre pré-mortem). Le mécanisme reste une HYPOTHÈSE ouverte jusqu'à
une mesure conditionnée.

## Synthèse d'arc (WARM-001→003) — le verrou in-world est un mur EN COUCHES
Chaque couche pelée révèle la suivante, toutes contournées par l'oracle (perfection codée) :
- **Crédit à froid** ne bootstrappe pas (S2-009/010/011).
- **Imitation-enseignant** n'installe pas de survivant : le substrat imite 1.000 mais l'acc on-policy
  plafonne 0.73 = **transfert** (WARM-001). L'**évolution W-only** échoue en parallèle : **paysage plat**
  (WARM-002).
- **DAgger on-policy** lève la métrique acc_on-policy (→0.99 sur fenêtre survivable) et double la survie
  (35, marqueur 5.04) MAIS plafonne loin de l'oracle — mécanisme résiduel OUVERT (couverture principale vs
  précision), non départagé (WARM-003).
Levier suivant motivé : soit pousser DAgger (budget agressif — la survie montait encore, non plateau net à
6 rounds ; l'extension 12 rounds caractérise plateau vs montée lente = test direct de l'hypothèse couverture),
soit une mesure discriminante (acc conditionnée tick/énergie) avant de conclure sur le mécanisme.

## Portée & limites
- **Biais de la métrique acc_on-policy (important)** : `_inworld_accuracy` n'accumule que pendant que des
  agents vivent (~ticks 0-35) et sur le sous-ensemble vivant → TRONCATURE + BIAIS-SURVIVANT. « acc=0.99 » =
  accuracy sur la fenêtre pré-mortem courte, PAS sur l'horizon-oracle 200 ticks. Ne pas lire « 0.99 » comme
  « maîtrise de la tâche ». Discriminateur couverture-vs-précision non implémenté (acc par bin tick/énergie,
  ou acc sur états tardifs de l'oracle).
- Budget modéré (6 rounds, epochs_per_round=3000). Trend de survie NON plateau à 6 rounds (+2/round) →
  l'extension 12 rounds teste directement l'hypothèse couverture (monte encore = couverture lente / plateau
  dur = mur plus profond). Un NÉGATIF de survie = « pas atteint 100 à budget modéré », pas « impossible ».
- « Round 0 = WARM-001 » lâche : round 0 ici (3000 ep) donne acc 0.66 ; le 0.734 de WARM-001 était à budget
  supérieur (20000 ep). La comparaison de baseline est indicative, pas iso-budget.
- Verdict K=12 (garde-fou n≥12) forward torch W gelé. Seed-monde 0 partagé entre collecte/acc/survie-ère-0 :
  corrélation légère, PAS de fuite train/test (génomes différents, `_inworld_accuracy` = rollout indépendant).
  acc = moyenne pop ; verdict = agent 0 cloné.
- Réétiquetage oracle = fonction pure f(bit_a,bit_b) → étiquette exacte sur tout état visité (propre à cette
  tâche réactive ; un DAgger général exigerait un expert requêtable).

Converge [[EDR-WARM-001]] (le 0.734 cassé ici), [[EDR-WARM-002]] (l'autre mur), [[decisive-substrate-thesis-test]],
[[warm-start-transversal-law]], [[within-subject-demand-marker]], REF-DEMAND-MARKER, S2-009.
