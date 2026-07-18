---
id: EDR-WARM-001
type: EDR
title: "Imitation récurrente BPTT : le substrat imite PARFAITEMENT l'oracle mais la survie plafonne — le mur est le SHIFT DE COVARIABLES, pas le substrat"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
Le behavioral cloning single-step avait échoué à transférer (bilan warm-start : shift de distribution). Une
IMITATION RÉCURRENTE par BPTT — matcher le forward récurrent du monde sur la distribution d'obs RÉELLE
59-dim, pas `_step` isolé — installe-t-elle un suiveur-de-signal in-world ? Et si oui, la survie décolle-t-elle
vers l'oracle (200) ? On dispose d'un enseignant PARFAIT (l'oracle S2-009) : un échec malgré teacher parfait
localiserait le verrou au-delà de la découverte.

## Méthode
`tools/warmstart_evolution_inworld.py` : (1) `imitate_episode_bptt` (backend torch, additive) rejoue une
trajectoire en RETENANT le graphe récurrent, perte = cross-entropy des move-logits vs l'action-oracle par pas,
backprop unique à travers la fenêtre ; (2) `_collect_oracle_trajectory` collecte la trajectoire-enseignant
(cohorte oracle, préfixe à B constant = 35 ticks, 420 échantillons équilibrés sur les 4 directions) ;
(3) entraînement d'une cohorte torch (12 génomes) par imitation, puis `verdict_demand_marker` (forward
**torch**, W gelé, ablation within-subject `derange_rows`, K=12 ères) sur le génome imité. Balayage
lr × epochs × fenêtre pour cartographier accuracy(imitation) → survie in-world. Régime S2-009.

## Résultats

**L'imitation converge sur la trajectoire-enseignant.** Le run à budget standard (lr=0.04, 200 ep) donnait
acc=0.312 (≈ hasard 4-voies) → **sous-entraînement**, pas plafond de capacité. En poussant lr/epochs, la
cohorte SUR-APPREND la trajectoire de l'oracle (acc_enseignant → 1.000). Mesure DÉCISIVE du mécanisme :
l'accuracy ON-POLICY, le génome pilotant SES PROPRES états in-world (`_inworld_accuracy`, argmax(dir) vs
bits courants sur les états auto-visités) :

| budget imitation | acc_enseignant (traj oracle) | acc **ON-POLICY** (états auto-visités) | intact | ablé | ratio | verdict marqueur |
|---|---|---|---|---|---|---|
| lr0.5 / 1500 ep | 0.717 | 0.597 | 9.8 | 6.8 | 1.44 | INCONCLUSIVE |
| lr0.6 / 10000 ep | 0.995 | 0.695 | 12.8 | 7.0 | 1.82 | **PERCEPTION_DEMANDED** |
| lr0.6 / 20000 ep | **1.000** | **0.734** | 15.0 | 7.0 | 2.14 | **PERCEPTION_DEMANDED** |

Repères : plancher ≈ 7 ; oracle intact ≈ 200 / ablé ≈ 9 / ratio ≈ 21, oracle acc ≡ 1.0 (S2-009).

**Dissociation + mécanisme MESURÉ (pas supposé).** (a) Le marqueur within-subject **BASCULE PERCEPTION_DEMANDED**
dès acc_enseignant≈0.99 : le génome imité utilise CAUSALEMENT la perception (l'ablation l'effondre 12–15 → 7).
(b) MAIS la survie plafonne à ~15 (oracle 200). **Cause mesurée** : l'accuracy PARFAITE (1.000) est IN-SAMPLE
sur la trajectoire de l'oracle ; l'accuracy ON-POLICY, quand le génome pilote ses propres états, **plafonne à
0.734 et ne monte PLUS** (0.597 → 0.695 → 0.734) alors même que l'accuracy-enseignant atteint 1.000 →
**plafond de TRANSFERT, pas sous-entraînement**. À ~27% d'erreurs on-policy, l'énergie s'érode → mort à ~15.
**Étiquette précise** (correction post-revue) : ce n'est PAS un shift de covariables des OBSERVATIONS — le
signal bit_a/bit_b est EXOGÈNE (re-randomisé chaque tick, indépendant de l'état) ; c'est la **dérive de l'état
RÉCURRENT H + le sur-apprentissage d'une trajectoire UNIQUE (35 ticks, 1 seed)** : la lecture apprise sur la
distribution d'états de l'oracle ne tient pas sur les états (H, position, voisinage — dims policy-dépendantes)
que le génome visite en s'auto-pilotant 200 ticks.

## Verdict
**`TEACHER_IMITATION_DOES_NOT_TRANSFER_ONPOLICY`** — PASS partiel : l'imitation récurrente BPTT installe un
utilisateur-de-perception CAUSAL (marqueur PERCEPTION_DEMANDED dès acc_enseignant≈0.99) mais PAS un survivant
(survie ~15 vs oracle 200 = FAIL sur « survie ≥ mi-chemin oracle »). **Ce qui est réfuté** : (1) ce n'est PAS
un plafond de découverte (l'enseignant est parfait) ; (2) ce n'est PAS du sous-entraînement (acc_enseignant
atteint 1.000 ; l'acc on-policy plafonne à 0.73 SANS monter avec plus d'epochs). **Ce qui est établi (MESURÉ,
`_inworld_accuracy`)** : le mur est le TRANSFERT ON-POLICY — la lecture apprise atteint 0.73 d'accuracy sur les
états que le génome auto-visite, à cause de la **dérive de l'état récurrent H + du sur-apprentissage d'une
trajectoire unique**. ⚠️ Nuance de capacité : « le substrat imite jusqu'à 1.000 » prouve qu'il peut SUR-APPRENDRE
35 ticks d'une trajectoire, PAS qu'il représente l'invariant réactif général ni qu'il le SOUTIENT sur 200 ticks
auto-pilotés (l'acc on-policy 0.73 le nuance explicitement). Levier suivant MOTIVÉ par la mesure (plus spéculatif) :
correction **ON-POLICY** (DAgger : relabel de la distribution de l'apprenant par l'oracle — attaque directement
le 0.73) OU crédit in-world visitant les propres états de l'agent.

## Portée & limites
- Trajectoire-enseignant à B constant = 35 ticks (un agent oracle meurt à t≈35 → préfixe tronqué) ; 420
  échantillons équilibrés. `acc_enseignant=1.000` = SUR-APPRENTISSAGE de CETTE trajectoire (1 seed), pas une
  généralisation prouvée. Le signal `_cog_sig` est re-randomisé chaque tick → tâche RÉACTIVE (cible = f(obs
  courante)), pas de mémoire ; le shift n'est donc PAS sur le signal (exogène) mais sur l'état récurrent/obs
  policy-dépendantes.
- `_inworld_accuracy` lit les logits BRUTS du forward (décision INTRINSÈQUE du génome, avant pénalité
  anti-répétition/consensus appliquées par le monde) — c'est la borne HAUTE de la décision on-policy.
- Reproductibilité : `lr` EXPOSÉ (`run_bptt_imitation_warmstart(lr=)` / env `WARM_LR`) car le défaut lr=0.04
  sous-entraîne ; la table ci-dessus se reproduit via `WARM_LR`/`WARM_EPOCHS`. Verdict forward torch, W gelé,
  K=12 (garde-fou n≥12).
- Complémentaire de WARM-002 (évolution : paysage plat). Deux murs distincts mais issus de la même propriété :
  la survie ne récompense la cognition qu'au-delà d'une accuracy très élevée (~99%+), gradient de sélection
  quasi-nul en deçà → converge le fil S2.

Converge [[EDR-WARM-002]], [[decisive-substrate-thesis-test]], [[warm-start-transversal-law]],
[[within-subject-demand-marker]], [[s2-world-demand-thread]], REF-DEMAND-MARKER, S2-009.
