---
id: EDR-172
type: EDR
title: "Throw-gate câblé in-world (cran 2, Brique B2) : le mécanisme de gate binaire validé isolé par EDR-171 (B1) est correctement câblé dans la vraie boucle biosphère (world_1_stoneage.py, sous use_torch_inworld AND torch_throw_gate, non-régressif prouvé, 10 tests, revue adversariale opus = PRÊT À MERGER) — MAIS il ne binde PAS in-world : le binding_gap = P(throw|spear) − P(throw|¬spear) reste du BRUIT, le témoin shuffle binde autant (SHUFFLE_BINDE_PLUS). Le verrou est le SUBSTRAT, à DEUX couches, PAS le mécanisme : (1) la cohorte FRAÎCHE s'éteint avant l'horizon d'apprentissage du gate — NON rescuable par le régime énergétique (alive=0 jusqu'au régime extrême bm=0.1/fp=5.0, sur 3 régimes défaut/sweet/extrême) ; (2) même avec survie prolongée (~920 échantillons), la récompense kill-avec-outil est trop RARE (0-6/300 ticks) pour piloter le REINFORCE. Le monde refuse au throw-gate À LA FOIS la survie de cohorte ET la densité de crédit que le monde-jouet de B1 fournissait. Confirme la thèse substrat-pas-mécanisme (163 survie NEUTRE, 166 gate-persist NEUTRE, famille H-unif)"
status: accepted
gate: null
verdict: THROW_GATE_WIRED_INWORLD_BUT_SUBSTRATE_BLOCKS_LEARNING
---

# EDR 172 : le throw-gate est câblé in-world mais le substrat bloque l'apprentissage (NEUTRE) — suite d'EDR-171 (B1)

## Contexte

EDR-171 (B1) a prouvé EN ISOLATION que le mécanisme de gate binaire route une action « ends »
(throw) sur un contexte présent, généralise (held-out), et passe le témoin shuffle — mais avec une
BORNE : décodage trivial (canal d'obs propre), monde-jouet 2-pas, récompense dense équilibrée,
~1200 épisodes d'entraînement. B2 câble ce mécanisme dans la VRAIE boucle biosphère et demande :
tient-il quand le contexte passe par la dynamique réelle, la récompense est l'outcome balistique
réel (kill-avec-outil), et la cohorte vit sous la létalité du monde ? Cf. [[torch-inworld-integration-plan]].

## Méthode

Câblage path-scopé dans `world_1_stoneage.py` (ZÉRO modif `backend_torch.py`), gardé par
`use_torch_inworld AND torch_throw_gate` (défaut OFF, legacy strictement non-régressif prouvé) :
tête apprise au niveau MONDE (`_throw_w` N-dim partagé + `_throw_b`, W gelé via `H.detach()`) qui
biaise `logits[8]` (throw) ; décision throw stochastique sous le gate ; REINFORCE immédiat 1-pas sur
l'outcome (kill-avec-outil +1, autre throw −0.5, pas de throw 0), anti-sat homéostatique (EDR-136).
Spears SEMÉS par le banc (découplage du mur du craft EDR-125/127) + re-semis probabiliste (mélange
dynamique spear/¬spear). Banc `tools/torch_throw_gate_inworld_ab.py` : A/B apparié ON vs SHUFFLE
(récompense permutée par-tick sur le set vivant), KPI `binding_gap = P(throw|spear) − P(throw|¬spear)`
mesuré sur la VRAIE présence dans les deux bras, verdict `compute_ab_verdict`. Testé sur 3 régimes
énergétiques (`base_metabolism`/`forage_payoff` : défaut 1.0/1.0, sweet EDR-085 0.25/3.0, extrême 0.1/5.0).

## Constat

| Régime | ticks / warmup | binding_gap | throw_rate | échantillons (spear_n) | alive fin | verdict |
|---|---|---|---|---|---|---|
| défaut 1.0/1.0 | 400 / 200 | +0.000 EXACT (4 seeds) | 0.000 | 0 (fenêtre VIDE) | 0 | NEUTRE |
| défaut 1.0/1.0 | 80 / 0 | bruit (médiane −0.085) | ~0.20 | ~120 | 0 | HEBBIEN (shuffle ≥) |
| sweet 0.25/3.0 | 200 / 100 | +0.000 (fenêtre vide) | 0.000 | 0 | 0 | NEUTRE |
| extrême 0.1/5.0 | 300 / 0 | bruit (médiane −0.029) | ~0.03 | ~920 | 0 | HEBBIEN (shuffle ≥) |

`kills_avec_outil` = 0-6 par run de 300 ticks (32 agents). Dans TOUS les régimes : `diff = gap_ON −
gap_SHUFFLE` ≈ 0 ou négatif → le témoin shuffle binde autant ou plus → **AUCUN routage réel**.

## Lecture

- **Le mécanisme est correctement câblé et ACTIF in-world** : à warmup=0 le gate TIRE (throw_rate
  0.03-0.20), le contexte spear est échantillonné (spear_n > 0). Le code est sain (10 tests verts,
  non-régression prouvée, revue adversariale opus = PRÊT À MERGER).
- **Mais il ne BINDE pas** : le binding_gap est du bruit, non distinguable du shuffle. Le témoin
  shuffle fait exactement son travail (leçon 169→171) : il REFUSE de confirmer un binding absent.
- **Le verrou est le SUBSTRAT, à DEUX couches, PAS le mécanisme** :
  1. **Plancher de survie non-rescuable.** La cohorte FRAÎCHE (agents à init randn·0.1, qui ne
     foragent pas) s'éteint bien avant l'horizon d'apprentissage du gate (~1200 pas en B1).
     `alive=0` sur les 3 régimes, jusqu'à l'extrême (bm=0.1/fp=5.0). Le régime sweet EDR-085 sauvait
     des CHAMPIONS entraînés, pas des agents frais — et `benchmark_mode` (obligatoire pour les dims
     torch homogènes, cohorte fixe) INTERDIT la reproduction/évolution qui construirait la compétence
     de forage. Mismatch structurel : horizon de survie (dizaines de ticks) ≪ horizon d'apprentissage.
  2. **Rareté du crédit.** Même quand le régime extrême prolonge la survie (~920 échantillons vs
     ~120), le gate n'apprend TOUJOURS PAS : les kills-avec-outil sont trop rares (0-6/300 ticks) pour
     piloter le REINFORCE, et l'anti-sat (calibré pour la récompense DENSE de B1) supprime le throw
     (throw_rate tombe à 0.03). gap_ON même négatif (throw LÉGÈREMENT moins fréquent avec spear).
- **Le monde-jouet de B1 fournissait DEUX choses que la biosphère refuse** : la survie (pas de
  mortalité, ~1200 épisodes garantis) ET la densité de récompense (kill à chaque épisode). B2 démontre
  que le succès de B1 dépendait de ces deux affordances — retirées in-world, le mécanisme ne paie pas.

## Conséquences

- **Câblage LIVRÉ et sûr** : la Brique B2 est mergeable (path-scopé, non-régressif, testé, revu). Elle
  fournit l'instrument in-world (tête throw + crédit + KPI + témoin) pour toute reprise future.
- **Le verrou in-world est le SUBSTRAT, confirmé causalement par un rescue qui échoue** : le levier
  énergétique (régime survivable) est RÉFUTÉ comme rescue (alive=0 partout). Résonne fortement avec
  [[edr090-no-survivable-first-rung]] (pas de premier barreau survivable pour agents frais),
  [[coop-competence-is-population-property]] (verrou = crédit means→ends) et le fil torch (163 survie
  NEUTRE, 166 gate-persist NEUTRE) : **les mécanismes qui paient en isolation ne paient pas in-world
  faute de survie de cohorte ET de densité de crédit — c'est le substrat, pas le mécanisme.**
- **Leviers pour une reprise future** (non poursuivis ici, hors scope B2) : (a) cohorte PRÉ-ENTRAÎNÉE
  (champions qui survivent) plutôt que fraîche ; (b) lever la contrainte cohorte-fixe (permettre
  l'évolution pendant l'apprentissage du gate — exige des dims torch dynamiques) ; (c) densifier le
  crédit throw (scaffold sur throw-avec-spear, pas seulement sur kill) ; (d) anti-sat recalibré pour
  la rareté in-world.

## Caveats

1. **Contexte quasi-verbatim** (revue Important #1) : le spear semé en index 0 rend la présence
   quasi-directement lisible de l'obs (`in_slot1_weight≈2.0`), comme le canal propre de B1 — donc B2
   ne teste PAS un contexte « distribué/récurrent » riche. Mais ce raccourci favorise le binding ; que
   le gap reste NUL malgré lui renforce le constat (le verrou n'est pas la difficulté de représentation).
2. **REINFORCE biaisé-mais-consistant-en-signe** : la décision échantillonne `σ(logits[8]+z)`, le
   `logp` utilise `σ(z)` (recette B1). Biais identique dans les deux bras → annulé par le contraste.
3. **Diagnostics 1-2 seeds par régime** : l'effet n'est PAS marginal (`alive=0` est robuste et binaire ;
   le gap est du bruit sur les 3 régimes) — l'effet-taille tranche, comme EDR-171.
4. **Cohorte FRAÎCHE** (pas champions) : le plancher de survie serait différent avec des génomes
   pré-entraînés — c'est précisément le levier (a) ci-dessus.
5. Le null n'est PAS « pas de capacité de binding » (B1 prouve la capacité isolée) mais « le substrat
   in-world ne fournit pas les conditions d'apprentissage ».
