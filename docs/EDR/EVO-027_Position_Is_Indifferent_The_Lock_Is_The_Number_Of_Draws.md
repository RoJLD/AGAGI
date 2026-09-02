---
id: EDR-EVO-027
type: EDR
title: "La POSITION d'un tirage réussi est indifférente — le verrou est le NOMBRE de tirages, pas leur non-composition"
status: active
verdict: POSITION_IS_INDIFFERENT_THE_LOCK_IS_THE_NUMBER_OF_DRAWS
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-026]
---

## Question — lever l'ambiguïté que D2/D2-bis ne pouvaient pas toucher

« Le verrou est le TIRAGE » ([[EDR-EVO-018]]) admettait deux lectures incompatibles :

| modèle | énoncé | prédiction ici |
|---|---|---|
| **A — rareté combinatoire** | les tirages sont indépendants, l'arrangement est indifférent | LATE ~ EARLY |
| **B — non-accumulation** ([[EDR-EVO-010]]/[[EDR-EVO-012]]) | un hit tardif est phénotypiquement neutre (|logit| des élites gelé à 9-12,5 vs w~N(0,1)), détruit par la coupe top-7/30 | LATE ≪ EARLY |

**D2-bis (largeur) a été abandonné sur preuve avant ce run** : à horizon fixe, N lignées indépendantes
donnent `P(≥1) = 1−(1−p)^N` sous A **et** sous B — puissance discriminante exactement nulle (panel
3 juges + réfutateur, unanimité). La profondeur est interdite par [[EDR-EVO-026]] (dégradation). La seule
clause encore discriminante : **la CONVERSION d'un tirage réussi dépend-elle de sa POSITION dans
l'historique de la lignée ?** Règle scellée AVANT le run : `EVO-027.json`, prédictions chiffrées des
deux modèles posées d'avance.

## Méthode

Le biais d'[[EDR-EVO-009]] — le seul levier de l'arc qui ait jamais déplacé le taux (12/12,
p=9,6×10⁻⁶) — actif dans une **fenêtre de 15 ères dont seule la position varie** :
**EARLY** = biais ères 1-15, run 30 ; **LATE** = évolution propre 1-20, biais 21-35, run 50.
Horizon post-fenêtre APPARIÉ (15 ères sans biais chacun : la rétention non assistée s'annule).
2 × 24 seeds, jeu mixte `TASKS_EVO006`, `W=5000`, croissance de nœuds coupée (N constant,
leçon EVO-026), `preserve_io_blocks=True`, budget agent-ticks déterministe (E13). Le levier fournit le
tirage : le design ne dépend **pas** de la base 0,005-0,02 qui plombait tous les designs à taux.

## Résultats

DV primaire telle que scellée : max de `measure_decision_saliency` sur les paires cibles
(canal-signal → sortie notée), seuil 0,5. Contrôle de manipulation : compteur de hits **délivrés**
instrumenté dans les deux bras, indices relatifs aux blocs.

| bras | **lecteurs** | sal méd | hits méd | portage fin | `age_fin` | `N` méd | abandons |
|---|---|---|---|---|---|---|---|
| **EARLY** | **22/24** | 1.000 | 9 | **7/7** | 13.0 | 172 | 0 |
| **LATE** | **18/24** | 1.000 | 10 | **7/7** | 10.0 | 172 | 0 |

**Les quatre contrôles scellés passent** : hits EARLY=9 / LATE=10 (ratio 1,11 ∈ [0,7 ; 1,4]) · portage
7/7 dans les deux bras · N médian 172 = 172 · santé LATE/EARLY = **0,77 ≥ 0,70**.
**Contrôle positif interne** : EARLY = 22/24, bien au-dessus du seuil scellé (≥ 8/24) et de la
prédiction (~14/24) — le harnais reproduit EVO-009 en config croissance-coupée.

**Fisher exact bilatéral EARLY vs LATE : p = 0,2448.**

## Verdict

**`POSITION_IS_INDIFFERENT_THE_LOCK_IS_THE_NUMBER_OF_DRAWS`** — par la branche scellée
« p ≥ 0,05 ET EARLY ≥ 12/24 » :

1. **La clause discriminante du modèle B (« un hit tardif vaut moins ») est RÉFUTÉE en dépendance
   FORTE.** Un tirage réussi livré à l'ère 21-35, après 20 ères d'évolution et leur charge, convertit
   en lecteur comme un tirage livré à l'ère 1-15 (18/24 vs 22/24, indistinguable).
2. **La clôture de l'arc se relit** : « le verrou est le tirage » signifie « le verrou est le **NOMBRE**
   de tirages » — les tirages restent efficaces tout au long de la recherche ; ce qui manque est leur
   quantité sur les bonnes paires, pas leur composition.
3. **L'échec des designs à taux naturels ([[EDR-EVO-019]]/[[EDR-EVO-020]]) reste attribué à la
   DILUTION** (fan-in 0,64 → 10,05 mesuré), pas à une non-composition : monter le taux brut noie
   l'arête cible dans les arêtes parasites, il ne la rend pas moins convertible.

## Observation NON élevée (discipline E9)

6 seeds LATE contre 2 EARLY **portent l'arête sans la lire** (portage 7/7, saillance 0,000-0,275) — la
direction serait compatible avec une dépendance de position **faible**, mais 18/22 = 0,82 est dans la
zone que la puissance scellée déclare illisible (12 vs 6 → p=0,135). C'est une observation, pas un
résultat ; le design qui la testerait devrait viser spécifiquement LATE/EARLY ∈ [0,5 ; 1,0] à n bien
plus grand.

## Portée (hedges)

* **Seule la dépendance FORTE est réfutée** (limite scellée AVANT : 12/24 vs 6/24 → p=0,135
  indétectable). Une atténuation faible (LATE/EARLY ≥ 0,5) reste possible et non testée.
* **Diagnostic, pas algorithme** — même statut qu'EVO-009 : le biais fournit la réponse (où tirer).
  Ce record dit que la conversion ne se dégrade pas avec l'historique ; il ne dit rien du taux de
  découverte NATUREL, qui reste ~2,7×10⁻⁴ par tirage.
* **DV mécanistes partiellement indisponibles, cause diagnostiquée** : `|logit|` in situ a rendu `nan`
  (le helper passait `None` à `recurrent_forward`, qui exige de vrais tableaux `H` — `None.copy()`
  lève) ; et l'injection post-run n'a pas pu être faite, les champions n'étant pas persistés (récidive
  de la dette « persister les génomes » de CLAUDE.md). Les deux étaient scellées **sans poids sur le
  verdict** ; la question mécaniste interne à B (troncature du neutre vs porte gelée) reste ouverte.
* La santé LATE (0,77) passe la clause mais confirme l'érosion d'EVO-026 : 50 ères coûtent ~23 % de
  survie finale même sans croissance.
* Mesuré avec le biais à 0,5 sur les paires (SIG_COLS → sorties notées) du jeu mixte ; autres jeux et
  fenêtres non testés.

Converge [[EDR-EVO-009]], [[EDR-EVO-010]], [[EDR-EVO-016]], [[EDR-EVO-026]],
REF-EXPERIMENT-PREFLIGHT.
