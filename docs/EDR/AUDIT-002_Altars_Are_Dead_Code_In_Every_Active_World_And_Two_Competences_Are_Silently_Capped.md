---
id: EDR-AUDIT-002
type: EDR
title: "`altars_solved` est du code mort dans les CINQ mondes actifs : `gym_competence` vaut identiquement 0, `industrial_competence` est plafonnée à 0.4, et le barreau 2 du design dreaming était un faux positif armé"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-REGISTRE-ERREURS]
corrects: [EDR-DREAM-002]
---

## Question
[[EDR-DREAM-002]] a mesuré `altars_solved` = 0.0 dans les trois bras, 0/12 seeds, et conclu que la
thèse d'exploration d'EDR-014 était **intestable dans ce régime**, en renvoyant à un indice connu du
dépôt (« l'autel stoneage est du code mort pondéré 0.6 »). Question restante, et c'était le fil
ouvert : **existe-t-il un monde ou un régime où les autels sont résolubles ?**

## Résultat — non, aucun. Et la portée est bien plus large que stoneage.

La condition de résolution est un **XOR à 2 bits** : émettre un scalaire dont le signe encode
`bit_a XOR bit_b`, en étant co-localisé avec l'autel. Aucune ressource, aucun craft. Elle n'existe
qu'à **trois endroits, tous hors des mondes actifs** :

| Fichier | Statut |
|---|---|
| `src/worlds/world_0_soup.py:541-553` | classe `SoupWorldLegacyV13`, marquée « NE PLUS UTILISER » (L38) |
| `src/environments/biosphere.py:510-522` | moteur **pré-refactor** |
| `src/environments/spaceworld.py:127-139` | env gym mono-agent — n'incrémente même pas la stat |

Les **cinq** mondes de `src/worlds/` héritent du même moteur `Biosphere3D`
(`world_1_stoneage.py:24`, et `world_0_soup` / `world_2_agricultural` / `world_3_industrial` /
`world_famine` en dérivent). **Aucun ne contient de bloc de résolution.** Dans stoneage, tout le reste
de la chaîne est pourtant présent : `num_altars = 3` (`config.py:43`), autels spawnés
(`world_1_stoneage.py:204-211`), **observables** et injectés dans le vecteur d'observation (L486-493,
L613), stat initialisée à 0 (L377). La seule chose absente est **l'incrémentation**.

Ce n'est donc ni un flag, ni une action manquante, ni un objet non spawné : c'est une **absence pure de
code**. Le bloc n'a jamais été porté lors du refactor vers le moteur canonique. Deux indices que
l'abandon fut délibéré plutôt qu'oublié : les autels de stoneage sont créés **sans clé `z`** alors que
la boucle legacy teste `altar["z"] == agent["z"]` (un portage naïf lèverait `KeyError`), et le canal
d'observation `bit_a/bit_b` a été **réaffecté** au mécanisme `cognitive_demand` (L495-499, commentaire
explicite « signal PAR-AGENT […] pas altar-gated »).

## Ce que cela casse en aval — vérifié ligne à ligne

`_median_norm` d'une liste de zéros vaut 0.0 (`competence.py:15-19`). Donc :

* **`gym_competence` ≡ 0.0 exactement** (`competence.py:102`) — elle ne lit *que* `altars_solved`.
* **`industrial_competence` ≤ 0.4** (`competence.py:97`) : `0.6 * compose + 0.4 * persist`, où
  `compose` est identiquement nul. **Le terme dominant est mort.**

Recoupement : le fil `transfer_ratio` est clos sur le constat « métrique dégénérée, les mondes
plafonnent bien sous `c_floor = 0.6` ». En voici un mécanisme concret et suffisant pour `industrial`,
qui ne peut structurellement **jamais** atteindre 0.6.

## Le faux positif qui attendait
Le barreau 2 du design de l'organe dreaming
(`docs/superpowers/specs/2026-06-23-Dreaming-Organ-Revival-design.md:33`) est :

> **La compétence-autels quitte le plancher** (`industrial_competence > 0.15`).

Ce critère, nommé pour les autels, **ne contient aucun signal d'autel**. Il ne peut bouger que par
`persist`, c'est-à-dire par la survie pure. Or [[EDR-DREAM-001]] vient de mesurer que le rêve forcé
**augmente la survie de 77 %**. Si l'arc était monté au barreau 2, il l'aurait franchi — et le
franchissement aurait été attribué aux autels.

C'est le **générateur C** du pré-vol dans sa forme la plus pure : la grandeur mesurée n'est pas celle
qui agit. Le critère ne pouvait pas produire les deux issues *pour la raison annoncée* ; il pouvait en
produire une pour une **autre** raison.

## Attribution — la cause inscrite dans le code est fausse
`competence.py:106-107` explique le plancher ainsi :

> « Le signal d'autel/outil est nul **tant que le goulot d'exploration (EDR 014) tient** »

L'attribution désigne une **incapacité des agents**. La cause réelle est qu'aucune ligne ne peut
résoudre un autel. Même motif que [[EDR-AUDIT-001]] : un nul **fabriqué par l'instrument**, lu comme
une réponse du monde — et qui a ensuite servi de motif à un rejet.

Correction apportée à [[EDR-DREAM-002]] : la thèse d'EDR-014 n'est pas « intestable **dans ce
régime** » mais **intestable partout dans le moteur actuel**, et pour une raison différente de celle
avancée (absence de code, pas difficulté de la tâche). La thèse elle-même reste **ni confirmée ni
réfutée**.

## Garde livrée (classe E16, `exécutable`)
`tests/sandbox/test_competence_stats_are_live.py` — cliquet statique : toute stat lue par une fonction
de compétence doit être **écrite** par `src/worlds/` ailleurs que dans son initialisation à 0, hors
classes `Legacy`. Dette gelée = `{altars_solved}` ; seule une **nouvelle** stat morte échoue.

Trois tests, calibrés **dans les deux sens** — le contrôle positif du détecteur est indispensable :
sans lui, un motif regex cassé déclarerait toutes les stats mortes, ou aucune, en passant au vert.

| stat lue par une compétence | verdict du détecteur |
|---|---|
| `age`, `preys_eaten`, `mammoth_kills`, `spears_crafted`, `total_dreams` | VIVANTE |
| `altars_solved` | **MORTE** |

Un troisième test interdit à la dette de s'endormir : si une stat gelée redevient vivante, il faut la
retirer de la liste. *Une dette qui ne peut plus être invalidée n'est plus une dette, c'est un
commentaire.*

## Pourquoi une classe d'erreur NEUVE (E16)
Aucune des 15 classes du registre ne couvre ce cas.

* **Pas E3 (métrique dégénérée)** : `industrial_competence` n'est ni au plancher ni au plafond, elle
  **varie normalement**. Une garde de borne ne voit rien.
* **Pas E15 (population confondue)** : aucune comparaison entre populations n'est en cause.

Le défaut est **compositionnel** : une métrique agrégée dont un terme est structurellement nul continue
de varier par ses autres termes, et cette variation se lit **sous le nom du terme mort**. Détectable
statiquement, pas dynamiquement — d'où une garde de scan de source plutôt qu'une assertion de run.

## Ce qui n'est PAS fait (dette ouverte, demande arbitrage)
Ni `competence.py` ni le mécanisme d'autel ne sont **réparés**. Re-pondérer `industrial_competence`
ou porter le bloc de résolution changerait des métriques que des records actifs ont déjà utilisées :
la portée dépasse cette passe. Consigné, non corrigé.

Note de méthode : `spears_crafted` est vivante mais, à `craft_level = 0` (en dur,
`world_1_stoneage.py:86`), le craft **n'exige aucune action délibérée** — ramasser deux objets
compatibles suffit (`stone_economy.py:110-117`). Comme proxy d'exploration elle mesure donc surtout
une propension à collecter. Sa lecture au plancher dans [[EDR-DREAM-002]] est à relire sous cet angle.

Converge [[EDR-DREAM-001]], [[EDR-DREAM-002]], [[EDR-AUDIT-001]], REF-EXPERIMENT-PREFLIGHT,
REF-REGISTRE-ERREURS.
