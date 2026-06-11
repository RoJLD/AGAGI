# EDR 069 : Le #8 trouve une VRAIE amélioration de l'agent (sur frontière gradient)

## Contexte

EDR 066 : sous mutation + tâche facile, tanh est optimal → le #8 n'a rien à trouver. EDR 067 : le
gradient rend des tâches dures abordables. (#3) On donne enfin au #8 une **frontière fertile** : il
propose des activations, chacune **entraînée par BPTT** sur une mémoire à **LONG DÉLAI** (D=16 →
gradient évanescent sur 18 ticks, où tanh plafonne à 0.840). Sûreté : sandbox EDR 035.

## Résultat — le #8 BAT tanh

| Activation (qwen2.5-coder) | accuracy (D=16) |
|---|---|
| **ELU** (Exponential Linear Unit) | **0.946** (+0.106) |
| PReLU | 0.849 |
| tanh (baseline) | 0.840 |
| Leaky Tanh / SELU / LELU | 0.74–0.78 |
| (un SELU bugué) | **REJETÉ par la sandbox** |

> **Le #8 a trouvé ELU, qui bat tanh de +0.106** — et c'est *scientifiquement juste* : qwen a raisonné
> sur le flux de gradient long et proposé ELU, qui ne sature pas en positif → meilleur flux sur 18
> ticks. La sandbox a *rejeté* une proposition buguée (la cage fonctionne).

## Lecture — le #8 est désormais PRODUCTIF

- **Sur une frontière fertile, le #8 améliore réellement l'agent.** Sous mutation+facile (066) : rien
  à trouver. Sous gradient+dur (069) : une vraie amélioration. **L'auto-amélioration au sens fort.**
- **L'ordre 1→2→3 était essentiel** : il fallait le **gradient** (067) pour créer un terrain où
  l'amélioration EXISTE, et alors le **#8** l'exploite (en sécurité, sandbox 035).
- La boucle complète a tourné : LLM propose code → sandbox valide (rejette le bugué) → BPTT entraîne →
  mesure → classe → itère.

## Honnêteté

- **ELU est une activation CONNUE** : qwen l'a *bien appariée* au régime (vanishing gradient), ce n'est
  pas une *découverte* novatrice. Mais matcher la bonne solution au problème *est* utile.
- **n=2 seeds** (démonstration) ; +0.106 est sizable mais une confirmation multi-seed renforcerait.
- Un modèle plus fort / un prompt poussant à la nouveauté pourrait proposer des formes inédites.

## La synthèse de la journée (067→069)

> **Le gradient était la clé manquante — et il déverrouille tout l'écosystème :**
> 1. **067** : le gradient résout ce que la mutation ne pouvait pas (mémoire 0.78→1.00 ; NAS = faux
>    problème).
> 2. **068 (Baldwin)** : gradient *dans* l'agent + évolution = inits apprenables (les deux moteurs se
>    composent).
> 3. **069** : le #8, *sur une frontière rendue fertile par le gradient*, trouve une vraie amélioration
>    de l'agent (ELU > tanh).
>
> La graine **apprend** (gradient), **évolue ce qui s'apprend** (Baldwin), et **se ré-améliore**
> (#8 productif). Ce qui manquait depuis 60 EDR n'était ni le monde ni l'architecture — c'était
> l'apprentissage.

## Statut

- `arm_act_grad.py` : #8 + gradient, frontière fertile, **amélioration trouvée** (ELU +0.106).
- Suite (#4) : la convergence du LANGAGE — barren sous mutation (057), mais le gradient (jeu
  référentiel speaker/listener entraîné par gradient) est *l'approche moderne* qui pourrait la cracker.

## Variables d'expérience

Difficulté (D), modèle LLM, nouveauté du prompt, nb de seeds, dérivée d'activation (numérique vs
fournie), tâche (mémoire vs computation).
