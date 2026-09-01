---
id: EDR-EVO-024
type: EDR
title: "Migration VALIDÉE : le correctif d'indices ne change aucune conclusion — et il reste désactivé par défaut"
status: active
verdict: MIGRATION_VALIDATED_READY_NOT_IMPOSED
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-023]
---

## Question

La dette de production ouverte par [[EDR-EVO-021]] : `add_node` **et** `add_meso_gated_unit` insèrent des
lignes/colonnes **sans jamais mettre à jour `num_inputs`/`num_outputs`**. Insérer dans le bloc de sortie
re-mappe quelle décision chaque nœud pilote — 56 % de désalignement mesuré.

> **Corriger change-t-il les conclusions de l'arc ?**

Règle scellée : `EVO-024.json`, avec la **prédiction posée avant le run** : [[EDR-EVO-023]] ayant montré
que supprimer *toute* croissance donne 0/12, le correctif ne devrait rien changer.

## Le correctif — flag-gated, off = bit-identique

`MutationConfig.preserve_io_blocks` (**défaut : `False`**). Quand il est actif, l'insertion est contrainte
à la région cachée `[num_inputs, N − num_outputs]`, et `i`/`j` sont décalés correctement après insertion —
ce qui règle du même coup l'off-by-one pour `i ≥ p` signalé par la revue adversariale.

**Pourquoi off par défaut, et pas « corriger et basculer »** : `src/seed_ai/mutation.py` est partagé avec
des sessions parallèles. Corriger en place changerait le comportement **sous les pieds** d'un run en cours
— la contamination que le bail `kuzu` empêche pour les mondes, entrant par la porte du code. Le dépôt a
déjà son idiome (le terme bilinéaire, livré flag-gated, off = bit-identique). La migration devient une
**bascule datée** au lieu d'un effet de bord.

## Pré-vol — le contrôle de manipulation scellé

| opérateur | bloc de sortie DÉCALÉ |
|---|---|
| historique (`off`) | **38/200** |
| corrigé (`on`) | **0/200** |

Discriminateur : un décalage déplace **tous** les marqueurs d'identité des sorties, une scission légitime
n'en touche qu'**un**. ⚠️ Le run a dû être **tué et relancé** : une transformation de texte avait laissé en
place le pré-vol d'[[EDR-EVO-023]] (croissance on/off) tout en annonçant celui-ci. Le dispositif tournait
sans vérifier ce qu'il prétendait — classe **E4**, dans sa forme silencieuse.

## Résultats

DV primaire telle que scellée : `measure_decision_saliency` sur `obs[5] → logits[8]`, seuil 0.5.

| bras | **lecteurs** | sal max | `raw` méd | `N` méd | abandons |
|---|---|---|---|---|---|
| historique | **0/12** | 0.013 | 0.485 | 178 | 0 |
| **corrigé** | **0/12** | 0.003 | 0.509 | 179 | 0 |

**Fisher exact bilatéral : p = 1.000.** La prédiction déclarée avant le run est confirmée.

## Verdict

**`MIGRATION_VALIDATED_READY_NOT_IMPOSED`**

1. **Le correctif ne change aucune conclusion.** Les records [[EDR-EVO-005]]→[[EDR-EVO-023]] restent
   valides et comparables entre eux ; il n'y a pas de re-mesure à faire.
2. **Le flag reste `False` par défaut.** Basculer est une **décision**, pas un effet de bord de cette
   session : d'autres sessions partagent le fichier. Critère de bascule proposé : quand aucun run n'est
   en vol et que le propriétaire du dépôt le décide explicitement.
3. **La dette est réglée sans être imposée** — le correctif existe, il est testé, il est validé comme
   neutre, et il attend une bascule datée.

⚠️ **Ça ne rend pas le défaut inoffensif.** Il redeviendra contraignant dès qu'un levier fera monter le
taux de création d'arêtes — exactement le régime où l'on voudrait qu'il ne nuise pas. C'est pourquoi le
correctif est livré maintenant plutôt qu'au moment où il deviendra urgent.

## L'automatisation qui empêche la récidive

`tests/sandbox/test_mutation_block_invariants.py` **ne teste pas une liste d'opérateurs : il la DÉCOUVRE.**
Toute fonction publique de `mutation.py` qui fait grandir `num_nodes` est balayée et soumise au contrat de
bloc. Un opérateur ajouté demain est couvert sans que personne y pense.

C'était nécessaire, et le dossier le prouve : le défaut avait **deux** porteurs, je n'en avais vu qu'un, et
c'est le pré-vol d'EVO-023 qui m'a appris l'existence du second. Une liste écrite à la main aurait
reproduit exactement cet angle mort. Le fichier porte aussi une **garde de la garde** : si la découverte
rend une liste vide, tous les tests passeraient sans rien vérifier (classe E4).

## Portée (hedges)

* **n=12 par bras, puissance déclarée AVANT** : 40 % contre 0 % est détectable (p≈0.04), 17 % ne l'est pas
  (p≈0.48). **Un nul ici ne PROUVE pas l'équivalence — il borne l'écart.** Un effet faible du correctif
  resterait invisible.
* Validé sur la sous-tâche `throw`, `hazard=15`, `W=0`. Les autres régimes de l'arc (`move`, objectif
  cognitif pondéré) ne sont pas re-mesurés — la prédiction d'[[EDR-EVO-023]] les couvre par argument, pas
  par mesure.
* Le correctif contraint l'insertion à la région cachée. Si un génome n'a **pas** de région cachée
  (`num_inputs + num_outputs == N`), l'insertion retombe sur le comportement historique — cas non
  rencontré ici, non testé.

Converge [[EDR-EVO-021]], [[EDR-EVO-022]], [[EDR-EVO-023]], REF-EXPERIMENT-PREFLIGHT.
