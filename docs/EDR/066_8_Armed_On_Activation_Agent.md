# EDR 066 : Le #8 armé sur le kind `activation` — il améliore l'AGENT (et confirme tanh)

## Contexte

EDR 065 : le #8 armé sur `world_demand` (améliore le *monde*). On élargit son espace d'action au kind
**`activation`** : le LLM propose des fonctions d'activation (CODE), la **sandbox EDR 035** les valide,
et on mesure si elles battent `tanh` sur le banc mémoire (mem_nas). Le #8 améliore alors l'**agent**.

## Sûreté — la cage EDR 035 (le code est exécuté, donc le conteneur redevient pertinent)

`compile_activation` : (1) `validate_code` (gate AST : `{numpy, math}` seulement, dunder/I/O/imports
dangereux interdits) ; (2) `run_sandboxed` (test shape/nan dans un subprocess `python -I` isolé,
timeout) ; (3) `exec` en-process du code **déjà AST-validé** (pure maths) pour l'utiliser vite.

> **Démontré live** : un `os.system(...)` proposé est **REJETÉ** (« import interdit: os »). Pour un LLM
> LOCAL proposant des maths, la sandbox EDR 035 est la cage adéquate ; un conteneur OS jetable reste la
> défense-en-profondeur recommandée pour un LLM cloud/non-fiable.

## Résultat (qwen2.5-coder, 6 propositions)

| Activation | accuracy mémoire |
|---|---|
| **tanh (baseline)** | **0.799** |
| Squash | 0.785 (proche) |
| Leaky ReLU / Leaky Squash | 0.715 |
| Sigmoid / Softmax | 0.653 |

**Aucune ne bat tanh** — et c'est la **bonne réponse**.

## Lecture — honnête et correcte

- Le #8-activation **fonctionne de bout en bout** : le LLM propose du code, la sandbox valide *toutes*
  les propositions (aucune rejetée ici — c'étaient des maths pures), le harnais mesure, on classe.
- **tanh est déjà quasi-optimal** pour la mémoire récurrente (bornée, lisse, centrée). Les standards
  proposés (sigmoid non-centrée, relu non-bornée, softmax élémentaire) sont *réellement* moins bons.
- **Le #8 n'a pas fabriqué de fausse amélioration** : la mesure a dit « tanh gagne ». C'est *la* valeur
  du harnais — un générateur qui ne se trompe pas lui-même (cf. faux positif attrapé en EDR 057).

## Bilan du #8 (065 + 066)

> Le #8 améliore désormais **le monde** (`world_demand`, 065) **ET l'agent** (`activation`, 066) — les
> deux **fonctionnels et sûrs**. Il *lit la mesure, propose, itère*, sans se mentir. Ce qui lui manque
> n'est **pas le mécanisme** — c'est une **frontière où l'amélioration EXISTE** : le langage est barren
> (057), tanh est déjà bon (066). Le #8 est un bon chercheur ; il lui faut un espace où il y a quelque
> chose à trouver.

## La frontière qui reste : le GRADIENT

EDR 064 : la mutation seule ne sait pas exploiter la capacité (croissance = bloat). Le **gradient
(BPTT)** est la clé commune : il donnerait (a) un substrat où l'architecture *paie* (débloquant le NAS),
(b) une tâche où une meilleure activation/structure *mesurablement* aide (un vrai espace pour le #8).
C'est le gros morceau de fond — un changement d'algorithme d'apprentissage, pas un réglage.

## Statut

- `arm_activation` : kind `activation` du #8 **armé, sûr, fonctionnel** (qwen-coder + sandbox EDR 035 +
  banc mémoire). tanh confirmé quasi-optimal.
- #8 complet (monde + agent) ; prochaine frontière = **gradient**.

## Variables d'expérience

Modèle (coder vs raisonnement), créativité du prompt (activations novatrices vs standard), banc de
mesure (mémoire vs tâche où tanh n'est pas optimal), algorithme d'apprentissage (mutation vs gradient).
