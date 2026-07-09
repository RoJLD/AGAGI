---
id: EDR-144
type: EDR
title: "Port du masque d'attention d'entrée : donne la parité FORWARD bit-à-bit (probe 0.000000) MAIS DÉGRADE la survie in-world (52.5→38, plat sur lr) → parité forward ≠ parité comportementale ; masque OFF par défaut ; corrige l'attribution 'résidu=masque' d'EDR-141"
status: accepted
gate: null
verdict: FORWARD_PARITY_NE_SURVIVAL_PARITY_MASK_KEPT_OFF
---

# EDR 144 : le masque d'attention d'entrée donne la parité forward mais dégrade la survie (gardé OFF)

## Contexte

EDR-141 a décomposé le résidu torch↔legacy-core (~16t) et l'a attribué au **masque d'attention
d'entrée dynamique** de legacy (parité PAR-PAS exacte sans lui). Item 1 backlog : le **porter** dans
torch pour la parité bit-à-bit. Fait — mais le résultat CORRIGE l'attribution.

## Méthode

`TorchBatchModel` : masque d'entrée dynamique répliqué EXACTEMENT comme legacy (`x = x_obs * mask` ;
`mask = sigmoid(logits[O-I:O])` recalculé chaque tick ; round-trippé via `a.attention_mask`), sous flag
`INPUT_ATTENTION`. Vérif forward : `tools/torch_parity_probe.py` (legacy-core vs torch-swish, même
génome+obs). Vérif survie : `arms` + `sweep_lr` K=10 stoneage, champion.

## Constat

- **Parité FORWARD atteinte** : avec `INPUT_ATTENTION=True`, divergence torch-swish ↔ legacy-core =
  **0.000000 à CHAQUE tick** (12/12). Le port est correct.
- **MAIS la survie in-world DÉGRADE** :

| torch (swish) | survie |
|---|---|
| SANS masque (EDR-140/141) | **52.5** |
| AVEC masque, lr=0.0 | 37.2 |
| AVEC masque, lr=0.04 | 39.0 |
| legacy-core (avec masque) | 68.2 |

  Avec le masque, torch tombe à ~37-39 (plat sur lr 0→0.04) — **−14 ticks vs sans masque**.

## Lecture

- **Parité FORWARD ≠ parité COMPORTEMENTALE.** Le probe teste le forward (learning-off, 1 agent) ;
  le monde tourne 12 agents × 300 ticks AVEC apprentissage. Un forward bit-identique ne garantit pas
  la même survie.
- **CORRECTION d'EDR-141** : le masque expliquait la divergence FORWARD, mais l'attribuer au résidu de
  SURVIE était FAUX — l'ajouter ne remonte pas torch vers 68.2, il le fait **CHUTER** à 38. Le masque
  n'est donc PAS le résidu de survie ; c'est une feature **net-négative** pour torch.
- **Énigme résiduelle (bornée)** : sous masque, torch (37-39, plat lr) reste très en-deçà de legacy-core
  (68.2) malgré un forward bit-identique → la seule différence restante = l'apprentissage numpy de
  legacy (le sien tourne, celui de torch est plat). Dans CE régime masqué, l'apprentissage legacy
  semble load-bearing là où torch ne réplique pas — mais sur 1 champion à connectome dégénéré (I/O qui
  se chevauchent, hidden négatif) et K=10, on ne sur-interprète pas. Le fait ROBUSTE : masque = net
  négatif pour torch.

## Conséquences

- **Masque OFF par défaut** (`INPUT_ATTENTION=False`) : torch garde sa meilleure survie (52.5) et le
  défaut EDR-140 reste non-régressif. La parité de migration (EDR-140/141 : torch≈legacy-core, p=0.46
  à K=30) tient **sans** le masque — le porter serait contre-productif.
- Le mode masque reste dispo (flag) pour les études de parité forward, pas pour la prod.
- **Item 1 clos** : le port est faisable (parité forward) mais NON souhaitable (survie). Leçon
  méthodologique : valider une migration sur la métrique de TÂCHE (survie), pas seulement le forward.
- Outils : `src/agents/torch_batch_model.py` (`INPUT_ATTENTION`), `tools/torch_parity_probe.py`.
  Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-144`.

## Caveats

1. 1 champion (connectome dégénéré I=64/O=126/N=172, hidden<0, I/O chevauchants), 1 monde, seed 42,
   K=10. L'énigme « masque+torch << legacy » n'est pas tranchée (rabbit-hole non prioritaire).
2. La parité forward est prouvée sur 1 agent + obs aléatoires ; le monde (12 agents, obs structurées)
   peut exercer des régimes non couverts par le probe — c'est justement le point (forward≠comportement).
3. Décision pragmatique (OFF) fondée sur la survie ; un autre champion/monde pourrait différer.
