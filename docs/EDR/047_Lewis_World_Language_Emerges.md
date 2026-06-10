# EDR 047 : Monde de Lewis — le langage référentiel ÉMERGE sous demande (thèse confirmée)

## Contexte

EDR 046 : on ne fait pas émerger une capacité en l'ajoutant — il faut que le **monde l'exige**. On
teste la prescription au langage en **durcissant le monde** : un vrai besoin référentiel.

## Le monde de Lewis (la demande, non scriptée)

Deux gros gibiers **indistinguables à distance** : **Mammouth** (récompense de groupe, appeler le
pack) et **Leurre** (piège : dangereux comme le Mammouth, **zéro récompense**). Un agent **adjacent**
perçoit le type (un indice de proximité, `on_apex_type`) ; les agents distants ne voient que « gros
gibier, direction X ». → Pour décider d'approcher (Mammouth) ou d'éviter (Leurre), il **faut le
token**. Un token *constant* ne distingue pas → aucun bénéfice : **seul un token référentiel paie.**
Pas de pression scriptée — la *demande* est la pression.

## Résultat — émergence

`I(token ; type_apex)` chez les agents adjacents à un gros gibier, avant/après 24 ères d'évolution
*sous demande* :

| | MI | baseline (perm.) | n |
|---|---|---|---|
| AVANT évolution | 0.0006 | 0.0042 | 783 |
| **APRÈS évolution** | **0.0330** | 0.0035 | 895 |

> Le token, **bruit sans demande** (MI≈0, toutes les expériences précédentes), devient
> **référentiel sous demande** : MI **×55 au-dessus du bruit**. Le langage référentiel **émerge** —
> le token se met à encoder « Mammouth » vs « Leurre ».

## La séquence complète (le récit de l'enquête langage)

| EDR | Intervention | Token |
|---|---|---|
| 037 | activer le canal | bruit |
| 042/043 | portée du signal | **présence**, pas sens |
| 045 | pression référentielle *scriptée* | échec (gameable) |
| **047** | **demande réelle (Lewis)** | **référentiel (émerge)** |

> **On ne fabrique pas une capacité en l'ajoutant — il faut que le monde l'exige.** Thèse du projet
> (EDR 010/012/046) **prouvée au bord le plus dur** (le langage), même agents, même mécanique, seule
> la *demande* changée.

## Honnêteté

- **MI = 0.033 bit reste modeste** (un langage binaire parfait ferait ~1 bit) : signal **naissant
  mais net** (×55 le bruit, n=895), qui se renforcerait avec plus d'évolution / une demande plus
  riche. La *direction* est prouvée ; l'*ampleur* est précoce.
- Mesuré sur 2 référents binaires ; un lexique plus riche demanderait plus de référents.

## Conséquences

- **Le langage n'est plus une frontière théorique** : on sait le faire émerger (créer la demande).
  L'arming dirigé (045) avait raison de cibler le monde, pas le mécanisme — il avait juste la
  *mauvaise intervention* (pression vs demande structurelle).
- **Recadre définitivement le #8** : le générateur (LLM) devrait proposer des **demandes de monde**
  (`kind="world_demand"`, EDR 046) — c'est là qu'est le levier, et on vient de le démontrer à la main.
- Suite naturelle : renforcer (plus d'ères, multi-référents > 2) ; appliquer la même recette au NAS
  (tâche saturant la capacité → l'architecture devrait grandir).

## Variables d'expérience

Nb de référents, durée d'évolution, distinguabilité à distance, force de la demande (coût du Leurre),
`hear_radius`.
