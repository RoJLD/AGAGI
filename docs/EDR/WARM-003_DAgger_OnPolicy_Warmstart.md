---
id: EDR-WARM-003
type: EDR
title: "DAgger on-policy CASSE le plafond de transfert 0.734 (acc→0.99) et DOUBLE la survie, mais un gap résiduel à l'oracle demeure : le dernier mille est la précision aux états critiques"
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

**Trois faits :**
1. **DAgger CASSE le plafond de transfert** : `acc_on-policy` 0.73 → **0.988**. Entraîner sur les états
   auto-visités lève la dérive de distribution → **confirme causalement le diagnostic WARM-001** (le mur
   ÉTAIT le transfert, fixable on-policy).
2. **La survie DOUBLE et le marqueur se renforce** : survie 15→35 (×2.3, 5× le plancher), marqueur ratio
   2.14→**5.04** (×2.4). C'est le **suiveur-de-signal in-world le plus fort de tout l'arc** — un génome
   appris (pas codé main) dont l'ablation-perception effondre la survie 35→7.
3. **MAIS un GAP RÉSIDUEL demeure** : `acc_on-policy` est ~MAXÉE à 0.99 (rounds 3-6 plats) tandis que la
   survie ne fait que **grimper lentement (~+2/round)** vers 35, loin de l'oracle (200). À ~99% de décisions
   correctes, **la survie DÉCOUPLE de l'accuracy moyenne** : la survie-à-200 est limitée par les ~1%
   d'erreurs résiduelles AUX ÉTATS CRITIQUES (basse énergie, une erreur = mort), pas par l'accuracy moyenne.

## Verdict
**`DAGGER_BREAKS_TRANSFER_CEILING_SURVIVAL_DOUBLES_RESIDUAL_PRECISION_GAP`** — POSITIF PARTIEL (le plus fort
in-world de l'arc). PASS sur le MARQUEUR (PERCEPTION_DEMANDED fort, ratio 5.04) ; FAIL sur la barre de survie
(35 < mi-chemin oracle 100). DAgger **confirme et répare partiellement** le mur WARM-001 : la correction
on-policy lève le plafond d'accuracy (0.73→0.99) et double la survie — donc le verrou WARM-001 ÉTAIT bien le
transfert de distribution. **Mais il révèle un mur de SECOND ORDRE** : même à ~99% d'accuracy on-policy, la
survie plafonne ~35 car la survie-à-200 exige la dernière fraction de précision aux états à haut risque, que
l'imitation agrégée n'instille pas à budget modéré. Le dernier mille n'est plus le transfert mais la
**PRÉCISION quasi-parfaite aux états critiques** — exactement ce que l'oracle codé-à-la-main possède par
construction.

## Synthèse d'arc (WARM-001→003) — le verrou in-world est un mur EN COUCHES
Chaque couche pelée révèle la suivante, toutes contournées par l'oracle (perfection codée) :
- **Crédit à froid** ne bootstrappe pas (S2-009/010/011).
- **Imitation-enseignant** n'installe pas de survivant : le substrat imite 1.000 mais l'acc on-policy
  plafonne 0.73 = **transfert** (WARM-001). L'**évolution W-only** échoue en parallèle : **paysage plat**
  (WARM-002).
- **DAgger on-policy** casse le transfert (acc→0.99) et double la survie (35, marqueur 5.04) MAIS bute sur
  la **précision aux états critiques** (WARM-003).
Levier suivant motivé : soit pousser DAgger (budget agressif — la survie montait encore, non plateau net à
6 rounds ; l'extension 12 rounds caractérise plateau vs montée lente), soit un signal de crédit qui pénalise
spécifiquement l'erreur aux états à haut risque (asymétrie de coût survie).

## Portée & limites
- Budget modéré (6 rounds, epochs_per_round=3000). Le trend de survie n'est PAS nettement plateau à 6 rounds
  (+2/round) ; un NÉGATIF de survie ici = « pas atteint 100 à budget modéré », pas « impossible ».
- Verdict K=12 (garde-fou n≥12) forward torch W gelé. acc = moyenne pop sur rollout ; verdict = agent 0 cloné.
- Réétiquetage oracle = fonction pure f(bit_a,bit_b) → étiquette exacte sur tout état visité (propre à cette
  tâche réactive ; un DAgger général exigerait un expert requêtable).

Converge [[EDR-WARM-001]] (le 0.734 cassé ici), [[EDR-WARM-002]] (l'autre mur), [[decisive-substrate-thesis-test]],
[[warm-start-transversal-law]], [[within-subject-demand-marker]], REF-DEMAND-MARKER, S2-009.
