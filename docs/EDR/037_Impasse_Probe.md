# EDR 037 : Sondeur d'impasse — le plateau est atteint, le langage n'émerge pas (Vague 3 / pré-#8)

## Contexte

L'utilisateur a défini l'**impasse / bottleneck** comme le déclencheur du #8 (vraie RSI). Plutôt
que de *scripter* l'émergence avancée (Vague 3), on **sonde** : évolution longue (40 ères) sur la
chaîne sociale robuste (coopération, EDR 028) à rareté survivable (12), **canal de langage latent
activé** (non-scripté), et on mesure où ça plafonne — via notre propre `compute_trend` (superviseur
réflexif EDR 036, qui mange sa propre nourriture).

## Résultat — impasse confirmée, langage non émergent

Tendance sur la 2ᵉ moitié (régime mûr) :

| Métrique | Direction | Pente | Moyenne |
|---|---|---|---|
| `proies_moy` | **plateau** | −0.002 | 1.01 |
| `mammouth` | **déclin** | −0.048 | 0.90 |
| `crafts` | **déclin** | −0.029 | 0.95 |
| `parleurs` | ~tous (33-45/45) | — | — |

**(1) Impasse atteinte.** À rareté survivable, sur 40 ères, la chaîne **plafonne (~1.0 proies) et
l'apex-hunting/craft érode** légèrement. Le système a atteint son **plafond** à cette
configuration — l'impasse, par définition de l'utilisateur, est le feu vert du #8.

**(2) Le langage n'émerge pas.** Le canal est *actif* (tous les agents émettent un token chaque
tick) mais **non-instrumental** : crafts/mammouth ne montent pas → c'est du **bruit**, pas de la
communication référentielle. Cohérent avec l'EDR 032 : un mécanisme non-utile **distrait** — le
canal langage est une dimension d'action supplémentaire où les mutations dérivent, ce qui contribue
probablement à l'**érosion** de la chaîne spécialisée. **Activer le canal ≠ faire émerger le sens.**

## Conséquences — le jalon de décision

On a atteint, par la mesure, le point que la roadmap réserve au **#8** :

- La chaîne moyens→fins est **dominante mais ne progresse plus** par simple évolution + curriculum
  + leviers actuels. Le générateur (mutation aléatoire) ne franchit pas ce plafond.
- Le langage ne s'auto-amorce pas : il faut soit une **raison structurelle** (portée/recrutement,
  récompense jointe du signal — risque de *scripter*), soit un **meilleur générateur** (#8 : un LLM
  qui propose des mécanismes/architectures, réinjectés via le sandbox sécurisé EDR 035).

> **C'est l'impasse. Le prochain mouvement principiel est le #8** (vraie RSI), désormais *sûr*
> (sandbox EDR 035) et *piloté* (le superviseur réflexif EDR 036 sait dire « plateau → famine »).
> Alternative plus douce avant d'armer le LLM : un levier structurel sur la coopération/portée du
> signal — mais c'est de l'addition, pas de l'expression.

## Limites

- Un seul réglage (rareté 12, 40 ères, scaffolds non-annelés ici) ; l'impasse pourrait être
  déplacée par un curriculum différent — mais le *type* de plateau (chaîne dominante non
  progressante) est robuste à travers nos runs.
- « parleurs » est un proxy grossier (émission non nulle) ; l'alignement référentiel
  (`LANGUAGE_ALIGNMENT`) n'a pas été mesuré finement — inutile vu l'absence d'effet instrumental.

## Variables d'expérience

Rareté, nb d'ères, schedule de sevrage, portée/coût du signal, présence du #8 (générateur LLM).
