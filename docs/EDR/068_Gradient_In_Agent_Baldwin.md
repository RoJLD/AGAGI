# EDR 068 : Le gradient DANS l'agent + évolution = effet Baldwin (#1 + #2)

## Contexte

EDR 067 : le gradient (BPTT) débloque l'apprentissage. (#1) On l'intègre comme l'apprentissage de
l'AGENT — chaque agent apprend par gradient dans sa "vie". (#2) On le combine avec l'évolution =
**Baldwin** : l'évolution sélectionne l'agent *apprenable*, pas l'agent fini. Banc mémoire, auto-contenu.

## Dispositif (`tools/baldwin.py`)

- `life_train(W, …, steps)` : une **VIE** = `steps` pas de gradient (SGD+momentum) depuis W → perf.
- `baldwin_evolve` : évolue l'**INIT** W (mutation de l'init), fitness = perf APRÈS la vie.
  **Darwinien** : les poids *appris* ne s'héritent pas — c'est la *capacité à apprendre* qui évolue.
- Clé : **vie COURTE** (10 pas) → l'init compte (une vie longue suffirait à n'importe quelle init).

## Résultat — effet Baldwin net

| | acc (K=6, 10 pas de gradient) |
|---|---|
| init **aléatoire** + vie | 0.645 |
| **Baldwin** (init évoluée) + vie | **0.847** (+0.202) |
| *(repères : mutation pure ~0.78 [064] ; gradient long ~1.00 [067])* | |

> **L'évolution façonne des initialisations APPRENABLES** : des points de départ d'où le gradient
> atteint en 10 pas ce qu'une init aléatoire ne touche pas. Les deux moteurs se complètent —
> évolution (globale, lente) prépare ; gradient (local, rapide) exploite.

## Lecture

- **#1 (gradient dans l'agent)** : l'agent *apprend* vraiment (gradient), au-delà de la mutation +
  l'Actor-Critic rustre. Démontré : une vie de gradient >> la mutation.
- **#2 (Baldwin)** : évolution + gradient battent chaque moteur seul *dans le régime à compute limité*
  (0.847 > mutation 0.78 > init-aléatoire+gradient 0.645). L'évolution de la *learnabilité* est réelle.
- C'est le pont conceptuel entre les 60 premiers EDR (évolution) et la percée 067 (gradient) :
  **on n'a pas à choisir — on les compose.**

## Implications

- Le bon paradigme d'AGIseed n'est ni « pure évolution » (trop faible, EDR 064/067) ni « pur gradient »
  (perd l'exploration globale) mais **évolution-de-l'apprenable + apprentissage par gradient** (Baldwin).
- Suite : pointer le #8 sur des tâches dures que le gradient rend abordables (#3) ; puis la convergence
  du langage *sous gradient* (#4).

## Statut

- `baldwin.py` : auto-contenu, effet Baldwin démontré (+0.20). Gradient intégré comme apprentissage
  d'agent ; composé avec l'évolution.

## Variables d'expérience

Longueur de la vie (pas de gradient), darwinien vs lamarckien (hériter les poids appris), évolution de
l'architecture aussi (add_node), coût de l'apprentissage, tâche.
