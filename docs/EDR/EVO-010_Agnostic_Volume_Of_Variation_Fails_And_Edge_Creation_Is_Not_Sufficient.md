---
id: EDR-EVO-010
type: EDR
title: "Un biais de variation AGNOSTIQUE par le VOLUME échoue — et créer l'arête ne suffit pas : 254 000 réveils achètent zéro lecteur"
status: active
verdict: AGNOSTIC_VOLUME_FAILS_EDGE_CREATION_INSUFFICIENT
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-009]
---

## Question

[[EDR-EVO-009]] a levé le verrou de la découverte (lecture 1/12 → 12/12) mais avec un biais qui **connaît
les arêtes qui comptent** — un diagnostic, pas un algorithme. Le record posait lui-même la suite : existe-t-il
un biais **AGNOSTIQUE à la tâche** qui produise le même effet ?

Candidat le plus net, et purement structurel : `mutate_weights` ne perturbe que les entrées **non nulles**
de `W`, donc toute la création de structure repose sur le seul `add_connection` (1 arête parmi ~11 000).
Lui laisser **réveiller** quelques entrées nulles au hasard n'utilise aucune connaissance de la tâche.

Règle de lecture scellée avant le run : `docs/preregistrations/EVO-010.json`.

## Méthode

3 bras × 12 seeds × 35 ères, jeu MIXTE, `W=5000`, mêmes graines. **Seul `mutate_weights` change**
(monkeypatch LOCAL ; le module de prod n'est jamais modifié). `wake5` / `wake20` = 5 ou 20 réveils
d'entrées nulles par mutation. Dimensionnement par l'arithmétique : ~800 mutations × `n_wake` sur ~11 000
candidates dont 3 lectrices → `n_wake=5` donne une espérance de ~1 découverte par lignée.

## Résultats

| bras | **lecteurs** | `raw` méd | âge méd | proies méd | échecs numériques |
|---|---|---|---|---|---|
| baseline | 1/12 | 0.453 | 13 | 8 | 0 |
| **wake5** | **0/12** | 0.471 | 14 | 9 | 1 |
| **wake20** | **1/11** | 0.441 | 12 | 7 | 0 |

**RÉFUTÉ** (branche pré-enregistrée « écart < 3 seeds ») : augmenter le VOLUME de variation ne reproduit
pas l'effet d'EVO-009. Et la survie est **préservée** dans les trois bras (âge 12-14) — ce n'est pas un
coût de viabilité, la variation ne trouve simplement rien.

Le chiffre qui rend ce nul parlant : le bras `wake20` a effectué **254 117 réveils**, soit une espérance
de ~69 arêtes lectrices créées (~6 par lignée), pour **1 lecteur sur 11**.

## Créer l'arête ne SUFFIT pas — mesuré, pas calculé

| champion `wake20` | arête `throw` | entrées concurrentes sur la sortie | saillance |
|---|---|---|---|
| seed 0 | −0.12 | 65 | 0.006 |
| seed 2 | −0.45 | 67 | 0.010 |
| seed 3 | −0.66 | 75 | 0.000 |
| seed 5 | −0.21 | 65 | 0.000 |

**4 champions sur 4 PORTENT l'arête lectrice, et aucun ne lit.** Ça nuance directement le récit
d'[[EDR-EVO-008]]/[[EDR-EVO-009]] : la « découverte » n'est pas la création de l'arête.

Le contraste au baseline est plus net encore :

| champion baseline | arête `throw` | concurrents | saillance |
|---|---|---|---|
| **seed 0** | **+0.144** (le plus FAIBLE) | **1** | **1.000** |
| seed 1 | +1.090 (7× plus fort) | 74 | 0.000 |
| seed 2 | +0.971 | 69 | 0.000 |
| seed 3 | +0.018 | 64 | 0.021 |

Sur 8 génomes issus de 2 bras indépendants, la séparation est franche : **1 concurrent → 1.000 ;
64-75 concurrents → 0.000-0.021**. Ce n'est donc pas le POIDS de l'arête qui décide — le lecteur a la plus
faible du lot.

## ⚠️ Et l'explication qui vient ensuite est FAUSSE — testée, avec son contrôle

L'« exclusivité de la sortie » explique rétrospectivement EVO-008 (le saut se fait sur une sortie propre),
EVO-009 (le ciblage ajoute l'arête SANS concurrents) et le nul ci-dessus (le volume ajoute l'arête ET
70 concurrents). Tout y était pour en faire un mécanisme. **L'intervention en récupère 8 %** :

| non-lecteur | intact | concurrents ÉLAGUÉS sur `throw` | contrôle : élagués sur une AUTRE sortie |
|---|---|---|---|
| seed 1 | 0.000 | **0.084** | 0.000 |
| seed 2 | 0.000 | **0.074** | 0.000 |
| seed 3 | 0.001 | **0.045** | 0.001 |

L'effet est **spécifique** (nul sur la sortie témoin) mais **minuscule** : élaguer jusqu'à la quasi-exclusivité
donne 0.08, pas 1.00. **L'exclusivité accompagne la lecture sans la causer.** Le lecteur du seed 0 est une
configuration **co-adaptée** — le reste du réseau a évolué AVEC cette sortie — et on ne la fabrique pas en
coupant des arêtes après coup.

## Verdict

**`AGNOSTIC_VOLUME_FAILS_EDGE_CREATION_INSUFFICIENT`** — trois énoncés, par ordre de solidité :

1. **Un biais agnostique par le VOLUME est réfuté** (pré-enregistré, n=12 × 3 bras) : 254 000 réveils
   achètent zéro lecteur. L'ingrédient actif d'EVO-009 était le **CIBLAGE**, pas le nombre de tirages.
2. **Créer l'arête n'est pas suffisant** (mesuré, 4/4 la portent sans lire) : « découverte » ≠ « création
   d'arête ». C'est une correction directe du récit d'EVO-008/009, qui restait ambigu sur ce point.
3. **Le mécanisme reste INEXPLIQUÉ.** L'exclusivité de la sortie corrèle fortement mais son intervention
   ne récupère que 8 % de l'effet. Ce qui distingue le lecteur d'un porteur d'arête n'est pas établi.

**Conséquence pour la suite** : un levier agnostique ne s'obtiendra pas en versant plus de variation
aléatoire. Les pistes qui restent visent la STRUCTURE et non le volume — normaliser le fan-in par sortie,
élaguer pendant l'évolution (et non après coup), ou faire porter la variation sur des sous-espaces plutôt
que sur des arêtes isolées. Aucune n'est adossée à un mécanisme établi : ce record ferme une voie, il n'en
ouvre pas une.

## Portée (hedges)

* Le contraste fan-in / saillance porte sur **8 génomes** et il est **observationnel**. Le seul volet causal
  (élagage) donne 8 % — donc ce contraste ne doit **pas** être cité comme mécanisme.
* Les seeds ne sont **PAS appariés entre bras** : changer l'opérateur change tout le flux aléatoire en aval,
  donc « seed 0 lit au baseline et pas en wake5 » ne signifie rien. Seuls les taux par bras sont comparables.
* `wake5` = 0/12 et `wake20` = 1/11 : la non-monotonie est dans le bruit à ce n, elle n'établit pas d'optimum.
* 1 échec numérique (`surprise` → NaN) en `wake5`, compté et rapporté ; 1 seed abandonné sur budget en
  `wake20`. Aucun n'est silencieusement absent.
* Le test d'élagage est une intervention **post-hoc sur un génome figé** ; il ne simule pas une évolution
  sous contrainte de fan-in, qui reste à faire.

## ⚠️ Deux fautes de protocole dans cette passe, à consigner

1. **Run lancé SANS pré-vol** — la règle était scellée et le dimensionnement calculé, mais la question
   « le bras traité est-il seulement VIABLE ? » n'a pas été posée. Le run a planté au 15ᵉ seed
   (`surprise` → NaN). Le pré-vol fait après coup montrait pourtant la densité passer de 0.3 % à 5.0 %.
2. C'est le **2ᵉ run perdu de la journée** faute d'une garde que j'avais moi-même écrite le matin
   (`cost_guard.py` pour le premier, le protocole de pré-vol pour celui-ci). **Une garde disponible et
   non déclenchée vaut zéro** — classe **E10** du registre, vue de l'intérieur.

Converge [[EDR-EVO-008]], [[EDR-EVO-009]], REF-EXPERIMENT-PREFLIGHT.
