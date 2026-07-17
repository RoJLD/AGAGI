---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-017
type: EDR
title: "Curriculum de Collecte & la Preuve que la Mécanique de Craft est Inémergeable"
status: legacy
gate: G2
---

# EDR 017 : Curriculum de Collecte & la Preuve que la Mécanique de Craft est Inémergeable

## Contexte

Dernier levier choisi pour le craft : un **curriculum de sous-compétences** (enseigner la
collecte en isolation, puis transférer), maintenant viable car le moteur évolutif est
réparé (EDR 016, le HoF persiste enfin).

## Décision (V18.4) — l'infrastructure de curriculum

- `world_1` : flag `training_mode` ; en mode `"grab"`, la **nuit** et la **régénération de
  proies** (donc le danger) sont désactivées → monde sûr pour apprendre.
- `tools/curriculum_grab.py` : Phase 1 (grab) = monde sûr, inondé de rock+stick, collecte/
  craft sur-récompensés ; Phase 2 (normal) = monde dur, charge le HoF grab-entraîné.

## Résultats — 0 craft, et un empilement de gates

| Run | Phase grab | Phase normale |
|---|---|---|
| Curriculum v1 | **0 lance** | **0 lance** |
| Curriculum v2 (après fix `inv_capacity` 1→3) | **0 lance** | **0 lance** |

Diagnostic des gates, par la mesure :

1. **Capacité d'inventaire** : **88% des agents ont `inv_capacity == 1`** → physiquement
   incapables de tenir rock+stick. Corrigé (min 1→3). → **toujours 0 craft.**
2. **Exécution de la séquence** : même monde sûr, items partout, capacité OK, fortement
   récompensé, les agents **n'exécutent pas** `grab→naviguer→grab→rub`. Ils survivent en
   grabant (énergie de collecte) mais ne composent pas la séquence.
3. **Recette dépendante de la position** : `do_rub` ne crafte que si `inventory[0]` ET
   `inventory[1]` sont *précisément* le couple tranchant+manche. Un inventaire
   `[rock, rock, stick]` ne crafte pas.

Le diagnostic « rub isolé » (+10 lances) ne marchait que parce qu'il **pré-remplissait**
l'inventaire avec rock+stick et le re-dotait — court-circuitant toute la collecte.

## Conclusion — définitive et multi-angle

> **Aucune machinerie d'apprentissage ne fait émerger ce craft.** Au fil de la session, on a
> falsifié, mesures à l'appui : reward-shaping, curiosité (partagée, par-agent), nouveauté
> count-based, boost, craft-dans-la-fitness, **et** curriculum de collecte (+ fix capacité).
> Toutes échouent sur le **même mur structurel** : la mécanique de craft empile trop de gates
> durs (capacité ≥2, grab×2, navigation, positions d'inventaire exactes, rub).

> Le problème **n'est pas l'apprentissage — c'est la mécanique**. Un comportement compositionnel
> profond ne peut pas émerger d'une recette aussi fragile et sur-contrainte, quel que soit le
> signal d'incitation ou le curriculum.

## Conséquences — la seule voie restante

- **Simplifier la mécanique de craft (auto-craft)** : la lance se forme dès que l'agent
  **tient** un tranchant + un manche (n'importe où dans l'inventaire), sans action `rub`
  ni contrainte de position. Effondre la chaîne `grab→grab→rub` (+ positions) en
  `grab→grab`. C'est la seule voie validée par la donnée — recommandée 3 fois, désormais
  incontournable.
- L'infrastructure de curriculum (`training_mode`, `tools/curriculum_grab.py`) reste valable
  et réutilisable **une fois la mécanique simplifiée** (le curriculum enseignera alors une
  collecte qui débouche réellement sur un craft).

## Acquis conservés

- `inv_capacity` min 3 (sensé : un agent peut porter quelques objets).
- Le moteur évolutif réparé (EDR 016) reste le grand acquis de la session : l'élite évolue
  (preys 6→15), indépendamment du craft.

## Variables d'expérience

Mécanique de craft (recette positionnelle vs « tenir les ingrédients »), `inv_capacity` min,
durée des phases de curriculum.
