# EDR 020 : Vrai Actor-Critic (crédit d'action) — le verrou de l'apprentissage est levé

## Contexte

L'EDR 019 a identifié le **goulot ultime** par élimination : le mécanisme d'apprentissage.
Le Hebbien rustre (`dW ∝ advantage·h·hᵀ`) renforçait tout le connectome sans savoir QUELLE
action avait été bonne → aucun geste ne pouvait être *encodé* (l'ε-greedy produisait du craft,
mais 100% forcé : ε→0 ⇒ craft→0, transfert=0).

## Décision (V18.7)

Remplacer le Hebbien par un vrai **Actor-Critic avec crédit d'action** :

- **Actor** (`src/seed_ai/policy_gradient.py::reinforce_action_update`) : pour l'action choisie
  `a`, `∂log π(a)/∂W[:,node_a] = (1{k=a} − π(k))·h`. Renforce *spécifiquement* le logit de
  l'action récompensée (softmax pour le mouvement, Bernoulli pour grab/rub), affaiblit les autres.
- **Critic** : la value head (sortie 28) est entraînée vers le reward (`dW[:,v]+=lr·(r−v)·h`),
  rendant l'avantage `r−v` enfin significatif.
- Câblage : `MambaBatchModel.compute_policy_gradient(rewards, actions_batch)` ; le monde
  **enregistre l'action prise** (`agent["_pg"]`, ε-forcée incluse) et la passe.

Rétro-compat : sans `actions_batch`, l'ancien Hebbien est conservé.

## Résultat — encodage ET transfert (une première)

Curriculum ε-greedy (ε annelé 0.35→0.02 sur 15 ères), avec le vrai Actor-Critic :

| | Hebbien rustre | Actor-Critic |
|---|---|---|
| Phase 1 — craft à **ε=0.02** (quasi sans forçage) | **0** (s'effondre) | **18** (tient) |
| Phase 1 — total | 107 | **382** |
| **Phase 2 — monde dur (ε=0)** | **0** | **2** |

> **La preuve de l'encodage est dans la phase 1** : avec le Hebbien, le craft s'effondrait à 0
> dès que ε baissait (comportement forcé, jamais appris). Avec le crédit d'action, il **tient à
> 18 même à ε=0.02** — la politique elle-même produit grab→collecte→craft. **Le geste est encodé
> dans le génome.** Et il **transfère** : 2 lances dans le monde dur (ε=0), là où c'était
> toujours 0. **Premier comportement appris, encodé et transféré du projet.**

## Conclusion

Le verrou de l'EDR 019 est levé : l'agent peut enfin **acquérir une action nouvelle**. C'est le
prérequis de toute émergence comportementale — il débloque, rétroactivement, *toutes* les briques
de la session (monde exigeant, scaffold, curiosité, nouveauté, HoF sauvé, craft-fitness, axe Craft,
ε-greedy), qui attendaient un apprentissage capable de créditer une action.

## Limites & suites

- **Transfert encore petit** (2 lances en monde dur) : l'encodage est prouvé mais faible. Le
  monde normal est dur (items rares, danger) ; il faut consolider.
- **Leviers de consolidation** : plus d'ères d'entraînement ; tuning `lr_actor`/`lr_critic` ;
  ramper la **difficulté** du monde entre grab-training et normal (curriculum de difficulté,
  axe Monde) ; ramper `craft_level` (axe Craft) une fois la collecte solide.
- **Critic encore simple** (régression MC sur le reward immédiat) : un vrai bootstrap TD (avec
  retour à horizon) renforcerait le crédit temporel.

## Variables d'expérience

`lr_actor`, `lr_critic`, ensemble d'actions créditées (mouvement+grab+rub vs plus), schedule ε,
durée d'entraînement, critic MC vs TD.
