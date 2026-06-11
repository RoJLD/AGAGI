# EDR 056 : Lever fort (fitness alignée) — backfire par métrique bruitée (5ᵉ défaut de design)

## Contexte

EDR 055 : la sélection alignée en *énergie* primait la distinction référentielle — prometteuse mais
faible. EDR 054 : ce qui se *propage* (le HoF) restait classé par `life_score`, aveugle au langage.
Lever fort (056) : faire entrer la distinction AUSSI dans la **fitness** (`calculate_life_score`),
pour que le HoF propage les communicants. Énergie + fitness alignées → effet visé *large*.

## Résultat — backfire

A/B 8 seeds × 16 ères (align 5.0 + fitness ×400) via le harnais :

| | taux d'émergence | gain moyen |
|---|---|---|
| OFF | 38 % (3/8) | 0.0071 |
| **FORT** | **12 % (1/8)** | 0.0037 |

t=−0.65, d=−0.33 → **sens négatif**. Le lever « fort » a **empiré** l'émergence.

## Pourquoi — métrique de distinction non fiable à faible compte

- Seuil de mesure : `m.sum() ≥ 1 et l.sum() ≥ 1`. Un agent qui a parlé **une seule fois** près du
  Mammouth et **une fois** près du Leurre, avec des tokens différents *par hasard*, obtient
  distinction = **1.0** — **fortuit, pas une convention**.
- Mis dans la **fitness** (×400 ≈ un mammouth tué), ça **propage des agents à distinction fortuite**
  au détriment des compétents → la population se dégrade → **moins** d'émergence.
- Confond : le lever fort a aussi monté l'énergie (3→5). Mais la cause dominante est la métrique
  bruitée *dans la fitness* (l'énergie de 055 était gentille car accumulée sur du comportement réel).

> **On ne peut pas récompenser un trait qu'on ne mesure pas de façon fiable PAR AGENT.** La
> distinction référentielle par agent demande beaucoup d'échantillons ; à faible n elle est du bruit,
> et l'amplifier (fitness ×400) propage le bruit.

## Le pattern (désormais écrasant)

| EDR | Mécanisme de langage conçu à la main | Défaut (trouvé par la mesure) |
|---|---|---|
| 045 | pression de convergence | gameable (token constant) |
| 048 | 3 référents | silence (altruisme) |
| 050 | réciprocité locuteur | crédit temporel |
| 055 | align énergie | OK mais faible/sous-puissant |
| **056** | align fitness | **backfire (métrique bruitée)** |

> **5 mécanismes, ~4 défauts subtils — chacun révélé *par la mesure*, jamais supposé.** Ce n'est plus
> une intuition : c'est une **démonstration empirique** que concevoir le bon mécanisme est une
> recherche difficile, et que la mesure est non négociable. C'est l'argument du #8 — *prouvé*.

## Décision — réversion + pivot recommandé

- **Réversion propre** : `REF_FITNESS_WEIGHT = 0` (le terme fitness est désactivé ; 055 énergie reste
  disponible). 133 tests verts.
- **La frontière du langage est thoroughly caractérisée** : réelle, stochastique (~25 %, EDR 053),
  sélection-aveugle (054), align-énergie prometteur-mais-faible (055), align-fitness backfire (056).
  Pousser un 6ᵉ mécanisme à la main est en rendements décroissants.
- **Recommandation** : **banker** le langage (acquis honnête + caractérisé) et **pivoter** vers (2)
  NAS-mémoire et (3) #8 — qui ont peut-être des effets plus francs, et que le harnais évalue
  désormais proprement. Le langage reviendra soit avec une *mesure par-agent fiable* (beaucoup
  d'échantillons), soit via le #8 itérant.

## Variables d'expérience

Seuil de comptage de la distinction (n min), poids fitness, isoler énergie vs fitness, par-agent vs
populationnel.
