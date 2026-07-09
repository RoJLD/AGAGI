---
id: EDR-166
type: EDR
title: "Persister le gate de binding à travers le rebuild du pop (prérequis cran 2 identifié par le review d'EDR-163) — VERDICT NEUTRE (4 seeds, monde compositionnel EDR-161, PERSIST vs RESET du gate au rebuild) : median_diff +0.009 <bande, 2/4, sign_p 1.0. L'instrument est VALIDÉ mécaniquement (mini-test d'asymétrie : RESET met w_gate à ~0, PERSIST le porte, W survit via génome) donc le null n'est PAS un bug d'inherit_gate. Lecture : le KPI stationnaire (dernier quart) démarre AU rebuild → RESET a ~200 ép pour RÉ-APPRENDRE le gate avant mesure → le NEUTRE = probable RÉ-APPRENTISSAGE RAPIDE du gate, PAS 'perdre le gate est sans effet'. Conséquence cran 2 : persister le gate au rebuild n'est probablement PAS nécessaire (le gate se reforme vite). SUIVI = métrique de décrochage IMMÉDIAT post-rebuild pour trancher"
status: accepted
gate: null
verdict: GATE_PERSIST_NEUTRAL_LIKELY_FAST_RELEARNING
---

# EDR 166 : persister le gate au rebuild — NEUTRE (probable ré-apprentissage rapide)

## Contexte

Le review final d'EDR-163 (intégration torch in-world crans 0-1) a identifié un bloqueur pour le cran 2
(allumer le gate de binding in-world) : le rebuild du pop torch sur mortalité RÉINITIALISE `w_gate`/
`b_gate` (le gate est population-partagé, PAS dans le génome) → chaque décès effacerait le binding
means→ends accumulé. Le probe compositionnel d'EDR-161 (CAPABILITY_PAYS) n'avait jamais rencontré ce
régime (pop fixe, jetable). **Question : porter le gate à travers le rebuild (fix `inherit_gate`)
maintient-il le binding, et la persistance du gate est-elle le levier du cran 2 ?**

## Méthode

Harnais `tools/torch_gate_persist_ab.py` (fichiers neufs, ne touche pas le monde partagé). Réutilise le
monde 2-pas craft→USE d'EDR-161 (`compositional_world_probe`, import DRY). Pop torch PERSISTANT sur 800
épisodes, REBUILD tous les 200 ép (nouveau pop depuis les MÊMES agents → W relu du génome, mis à jour
par `_write_back` ; gate neuf). A/B apparié par seed (common-random-numbers) :
- **PERSIST** : `inherit_gate(new, old)` au rebuild (le gate survit).
- **RESET** : gate réinitialisé (le bloqueur actuel).

1 variable = le sort du gate au rebuild. KPI = `comp_rate` (dernier quart). Verdict `compute_ab_verdict`.
Instrument VALIDÉ par un mini-test d'asymétrie : après un `learn_episode`, RESET donne `w_gate`≈0
(gate perdu), PERSIST donne `w_gate`==ancien (gate porté), et `genome.W` a changé (W survit).

## Constat

| seed | comp_rate PERSIST | comp_rate RESET | diff |
|---|---|---|---|
| 0 | 0.204 | 0.225 | −0.021 |
| 1 | 0.161 | 0.124 | +0.038 |
| 2 | 0.145 | 0.164 | −0.019 |
| 3 | 0.223 | 0.092 | **+0.131** |

`median_diff = +0.009` (< bande 0.02), 2/4 favorables PERSIST, `sign_p = 1.0` → **VERDICT = NEUTRE**.
Bruité (seed 3 fort +0.131, variance élevée).

## Lecture

- **Le NEUTRE n'est PAS un artefact d'instrument.** Le mini-test d'asymétrie prouve que RESET perd bien
  le gate (w_gate→0) et PERSIST le porte. `inherit_gate` fonctionne. Le null est réel.
- **Le KPI stationnaire masque le décrochage.** La fenêtre de mesure (dernier quart = ép. 600-800)
  démarre PILE au rebuild de l'ép. 600 → le bras RESET a ~200 épisodes pour RÉ-APPRENDRE le gate avant
  qu'on mesure. Donc « PERSIST ≈ RESET en régime établi » ne dit PAS « perdre le gate est sans effet » —
  il dit probablement « le gate se **RÉ-APPREND vite** après un rebuild ».
- **Deux lectures, conséquences opposées** : (a) ré-apprentissage rapide → persister le gate au rebuild
  n'est PAS nécessaire pour le cran 2 (le gate se reforme) ; (b) décrochage réel mais compensé →
  persister aiderait le tail. Le KPI actuel ne les distingue pas.

## Conséquences

- **Pour le cran 2 (gate in-world)** : la persistance du gate au rebuild n'est probablement PAS le
  bloqueur critique qu'on craignait — le gate paraît se ré-apprendre vite. On peut tenter le cran 2 SANS
  d'abord résoudre la persistance, et mesurer directement le comp_rate in-world.
- **SUIVI = métrique de décrochage IMMÉDIAT** : comparer `comp_rate` sur les épisodes juste APRÈS un
  rebuild vs juste AVANT, pour chaque bras. Tranche entre ré-apprentissage rapide (a) et décrochage (b).
  C'est le prochain incrément propre sur cet instrument.
- **Instrument RÉUTILISABLE livré** : `inherit_gate` (helper) + harnais A/B PERSIST/RESET + mini-test
  d'asymétrie. Promotion d'`inherit_gate` en méthode de `TorchPopulationModel` reportée au cran 2 réel
  (YAGNI). Cf. [[torch-inworld-integration-plan]].

## Caveats

1. **4 seeds** : sous-puissant (le résultat robuste est que le signal de bande n'atteint pas le seuil ;
   seed 3 fort suggère de la variance, pas un effet établi). Powerer confirmerait le NEUTRE stationnaire.
2. **KPI stationnaire** (dernier quart) : par construction insensible au décrochage transitoire post-
   rebuild — c'est la limite centrale, adressée par le suivi « décrochage immédiat ».
3. **Monde synthétique 2-pas** (proxy EDR-161), pas la biosphère : indicatif. N stable (cohorte fixe) ;
   `add_node` casserait le transfert de `w_gate` taille N. Optimiseur Adam réinitialisé au rebuild des 2
   côtés (symétrique, pas un confond inter-bras).
4. `rebuild_every=200` fixé ; la fréquence de rebuild (mortalité) est un knob non balayé.
