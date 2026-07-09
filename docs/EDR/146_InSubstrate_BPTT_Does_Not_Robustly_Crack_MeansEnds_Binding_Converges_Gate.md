---
id: EDR-146
type: EDR
title: "BPTT fenêtré in-substrat sur means→ends : la capacité BPTT (numpy-impossible) NE craque PAS de façon fiable le binding (binding_gap médian ~0, bptt −0.02 ≈ tronqué −0.03, forte variance seed) → CONVERGE avec le fil compositional // (le verrou binding est le ROUTAGE/gate, pas la portée du crédit à travers le temps)"
status: accepted
gate: null
verdict: BPTT_DOES_NOT_ROBUSTLY_CRACK_BINDING_CONVERGES_GATE
---

# EDR 146 : BPTT in-substrat ne craque pas le binding means→ends (converge fil compositional //)

## Contexte

EDR-145 : la capacité BPTT (crédit à travers le temps) est réelle et numpy-impossible (tâche mémoire
copie-à-T-pas, 1.00 vs 0.61). Item backlog : l'intégrer IN-SUBSTRAT sur le vrai test de valeur
(means→ends), en COORDONNANT avec le fil compositional // (qui teste torch vs hebbien sur cette tâche,
EDR-122/126/136-compo).

## Coordination (constat préalable)

Lecture de `substrate_ab_compositional.py` (fil //) + `backend_torch.py` (mien) : leur torch appelle
`forward(S1)` puis `forward(S2)`, or **`TorchPopulationModel.forward` DÉTACHE H** chaque pas → leur
torch est AUSSI **tronqué** (le crédit S2→S1 ne passe pas la récurrence). Leur « torch craque le
binding » (EDR-136-compo) passe donc par un **gate within-tick**, PAS par du crédit à travers le
temps. Un apprenant BPTT est donc **complémentaire** (mécanisme distinct), non dupliqué.

## Méthode

`TorchPopulationModel.learn_episode_bptt` (ADDITIF : ne touche ni `forward` ni `learn` → banc // intact) :
rejoue l'épisode en RETENANT le graphe récurrent, crédite les actions prises (REINFORCE, retour
épisodique + baseline), backprop UNE fois à travers la fenêtre. `tools/torch_bptt_meansends.py` oppose
le MÊME substrat torch en **bptt** vs **truncated** (H détaché entre S1/S2) sur means→ends (S1→X, S2→Y
récompensé SSI X ; `obs_b` n'encode pas did_x). Métrique de binding (EDR-128) :
`binding_gap = P(Y|X) − P(Y|¬X)`. 3 seeds, 1000 époques, 128 agents.

## Constat

| régime | binding_gap médian | par seed | hit_end médian |
|---|---|---|---|
| **bptt** | **−0.02** | [−0.11, +0.03, −0.02] | 0.055 |
| truncated | −0.03 | [−0.03, +0.16, −0.16] | 0.070 |

`VERDICT=NEUTRE`. Pas d'avantage BPTT robuste. (À 1 seed on peut voir bptt +0.18 — mais NON
reproductible : forte variance seed-à-seed dans les deux régimes.) `p_x ≈ 0.24-0.25` (>chance 0.125 :
X est un peu appris) ; `hit_end ≈ 0.06` (binding proche du hasard).

## Lecture

- **La capacité BPTT ≠ le chaînon manquant du binding.** Le crédit à travers le temps (réel,
  EDR-145) n'ouvre PAS de façon fiable le conditionnement means→ends (binding_gap ~0, ≈ tronqué).
- **CONVERGENCE forte avec le fil compositional //** : la variance seed-à-seed énorme = la
  **path-dependence / bassin d'optim** identifiée par EDR-131/133-compo (le verrou résiduel = bassin,
  pas le mécanisme de crédit ni la représentation). Le binding se débloque par un **GATE de
  routage/conditionnement** (EDR-129-compo), PAS par la portée du crédit (ni 1-pas, ni BPTT).
- **Valeur de torch cadrée** : sa frontière paie sur les tâches à **mémoire/crédit multi-pas**
  (EDR-145), pas (seule) sur le binding compositionnel, dont le levier est le routage (fil //).

## Conséquences

- **Migration — carte de valeur affinée** : torch débloque (a) la faisabilité/parité (140/141), (b)
  la mémoire à travers le temps (BPTT, 145). Le binding means→ends reste un verrou de **structure de
  routage** (gate, fil //), orthogonal à BPTT.
- **Prochain build coordonné** : combiner **gate (mécanisme du fil //) + BPTT (ma capacité)** — le gate
  route le conditionnement, BPTT façonne la mémoire qui l'alimente. À faire AVEC la session
  compositional (leur `substrate_ab_compositional.py` + mon `learn_episode_bptt`), pas en solo.
- Le harnais BPTT (`learn_episode_bptt`, `tools/torch_bptt_meansends.py`, `tools/torch_bptt_probe.py`)
  est réutilisable pour ça. Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-146`.

## Caveats

1. **Apprentissage absolu FAIBLE** (hit_end ~0.06, substrat 172-nœuds dégénéré I/O-chevauchants, REINFORCE
   nu) : c'est une tâche DURE (tout le fil compositional le confirme). Le résultat ROBUSTE est la
   COMPARAISON contrôlée bptt-vs-truncated (même substrat, tout égal) = NULLE, pas l'absolu.
2. 3 seeds ; forte variance (path-dependence) → un n plus grand préciserait, mais le signal (pas
   d'avantage BPTT net) est cohérent avec EDR-131/133.
3. BPTT SEUL testé (pas BPTT+gate) ; la combinaison (prochain build coordonné) n'est pas évaluée ici.
4. REINFORCE épisodique 2-pas + baseline ; un actor-critic BPTT plus riche pourrait différer (borné).
