---
id: EDR-EVO-019
type: EDR
title: "La cellule vide (volume × fan-in) : un lecteur ISOLÉ à 1/12, non élevé — la clôture tient, mais l'issue tombe ENTRE les branches scellées"
status: active
verdict: ISOLATED_READER_NOT_ELEVATED_CLOSURE_HOLDS
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-018]
---

## Question

L'analyse à deux régimes d'[[EDR-EVO-013]] désignait une **cellule vide** : [[EDR-EVO-010]] a testé le
VOLUME seul (0/12 — sature le dénominateur), [[EDR-EVO-014]] le FAN-IN seul (0/11 — inerte, fan-in
baseline < 1). **Jamais les deux ensemble.** Règle scellée : `EVO-019.json`.

3 bras × 12 seeds sur la sous-tâche `throw` (la plus facile, [[EDR-EVO-018]]), `hazard=15`, `W=0`.

## ⛔ Contrôles de manipulation — la condition (b) SCELLÉE n'a PAS été mesurée (corrigé 2026-08-04)

⚠️ Le compteur du runner rend des valeurs **négatives** (−12 624, −458 752) : il compare `W[:I, N-O:]`
avant et après, or `add_node` **change N** et décale le bloc des sorties. **6ᵉ défaut de mesure de la
semaine, et c'est le même décalage d'indices que j'avais attrapé en traçant l'ère 7 d'[[EDR-EVO-008]].**

Re-mesuré séparément avec des indices RELATIFS (invariants au changement de N), chaîne de mutations pure :

| bras | arêtes E→S créées (cumul) | présentes à la fin | fan-in moyen |
|---|---|---|---|
| baseline | 783 | 29 | 0.64 |
| volume | **5 085** (×6.5) | 334 | **10.05** |
| volume+cap | 3 632 (×4.6) | 86 | **2.92** |

⚠️ **CORRECTION (2026-08-04, revue adversariale — critique CONFIRMÉE).** La version initiale de ce record
écrivait « les deux conditions exigées sont satisfaites ». **C'est faux.** La règle scellée exige
littéralement : *« (b) le plafond doit RÉDUIRE `|logit|` médian par rapport au bras volume-seul »* — et
ajoute *« si l'un des deux échoue, ce bras ne teste rien : ne pas lire le taux de lecteurs »*. Le sceau du
JSON a été recalculé : il est INTACT, la règle n'a pas été éditée.

Or **`|logit|` n'a jamais été mesuré** ; une réduction de **fan-in** lui a été substituée. Fan-in ≠ `|logit|` :
tout l'appareil d'[[EDR-EVO-012]] définit `R = |w_signal| / |logit|`, et un plafond sur le NOMBRE d'arêtes
entrantes peut en réduire le compte sans réduire la somme pondérée (moins d'arêtes, mais plus grosses).
**La DV du contrôle de manipulation a été substituée APRÈS le scellement** — une forme d'E11 que le sceau
ne peut pas détecter, puisqu'il prouve la non-modification de la RÈGLE, pas la fidélité de son APPLICATION.

Deux conséquences, appliquées ici :
* le bras `volume+cap` est déclaré **NON LU**, conformément à la clause scellée. Son 0/7 ne figure plus
  dans aucun raisonnement ;
* la condition (a) elle-même n'est satisfaite **que par PROXY hors-run** : la re-mesure est une *chaîne de
  mutations pure*, **sans sélection**, alors que l'expérience est une évolution où la sélection élague les
  arêtes ([[EDR-EVO-001]]). Le ×6.5 est donc **inféré, pas mesuré sur les génomes du run** — et un
  contrôle de manipulation inféré ne peut pas soutenir un NÉGATIF (« on a densifié et rien n'a bougé »
  reste indistinguable de « on n'a jamais densifié dans le run »). Violation d'`assert_predictor_measured_in_situ`.

## Résultats

| bras | **lecteurs** | sal max | abandons |
|---|---|---|---|
| baseline | **0/12** | 0.013 | 0 |
| **volume** | **1/12** | **0.982** | 0 |
| volume+cap | **0/7** | 0.000 | **5/12** |

## Verdict

**`ISOLATED_READER_NOT_ELEVATED_CLOSURE_HOLDS`**

**1. Un lecteur AUTHENTIQUE, et rien à en conclure.** Le bras `volume` produit une saillance de **0.982**
— indiscernable d'un câblage manuel. Mais **1/12 contre 0/12 donne Fisher exact bilatéral p = 1.000**.
C'est trait pour trait la configuration qui a fait **rétracter [[EDR-EVO-006]]** : un lecteur bien réel à
1/12, élevé en mécanisme, puis retiré. La leçon **E9** s'applique telle quelle et l'observation reste une
**observation**.

**2. L'issue tombe ENTRE les branches scellées.** La règle prévoyait « ≥ 3/12 » ou « 0/12 » ; 1/12 n'est
couvert par aucune. Je le signale plutôt que de la ranger dans la branche qui m'arrange — c'est
exactement la latitude que le pré-enregistrement existe pour supprimer, et il faut constater qu'il ne l'a
pas fait ici. **Correction de méthode à retenir : une règle de lecture doit couvrir le CONTINUUM, pas
seulement les issues franches.**

**3. Le bras `volume+cap` est AMPUTÉ** : 5 abandons sur 12, cause directe du coût du plafond (tri de 108
colonnes par enfant). Son 0/7 pèse peu et ne permet pas de conclure sur la combinaison. **La cellule vide
reste donc partiellement vide.**

**4. La clôture d'[[EDR-EVO-018]] tient — mais sur 24 lignées, pas 31.** ⚠️ **Corrigé** : la version
initiale réinjectait les 7 survivants du bras `volume+cap` dans le décompte, c'est-à-dire utilisait comme
preuve un bras qu'elle venait de déclarer non-informatif. Pire, **la censure y est INFORMATIVE** : le
budget est en SECONDES par seed et le coût suit le succès évolutif (`CLAUDE.md` §Coût des runs), donc les
5 seeds tombés sont biaisés vers ceux où l'évolution est allée le PLUS LOIN — là où un lecteur est le plus
probable. Un tel bras ne peut pas renforcer un négatif ; il le fragilise.

L'attribution des abandons était elle aussi incohérente : un « tri de 108 colonnes par enfant » est un
surcoût FIXE, qui ralentirait les 12 seeds de façon homogène. Il ne peut en tuer exactement 5 que via un
nombre d'enfants dépendant du seed — c'est-à-dire via la survie. **Cause proximale réelle : le budget en
SECONDES**, que la clôture d'E13 proscrit explicitement au profit d'un plafond en NOMBRE D'AGENTS.

## Ce qui distingue ce « volume » de celui d'EVO-010 — et pourquoi ça mérite un test propre

[[EDR-EVO-010]] densifiait via `mutate_weights` en réveillant des poids NULS **uniformément**, y compris
hidden→hidden. Ici le volume passe par `add_connection`, qui respecte la contrainte de source
(`i < N − O`) et ne tire que parmi les arêtes ABSENTES. Ce sont deux opérateurs différents, et le second
est le seul des deux à avoir jamais produit un lecteur sous survie seule.

**C'est la piste la plus concrète que l'arc ait laissée**, et elle demande un n suffisant pour trancher :
`volume` seul, n ≥ 24, sans plafond (qui coûte trop). Si le taux se confirme au-dessus du baseline, la
clôture devra être qualifiée ; s'il retombe à 0, l'observation rejoint celle d'EVO-006.

## Portée (hedges)

* **1/12 n'est pas un résultat** (Fisher p = 1.000). Il n'est rapporté que parce qu'un négatif silencieux
  sur un lecteur à 0.982 serait une omission, pas une prudence.
* Le bras `volume+cap` (0/7, 5 abandons) **ne teste pas la combinaison** — il en mesure surtout le coût.
* Le compteur d'arêtes du runner est **invalide** ; toutes les affirmations de manipulation reposent sur la
  re-mesure séparée ci-dessus, pas sur la colonne du tableau.
* n=12 borne une fréquence (borne sup ~22 %), pas une impossibilité.

Converge [[EDR-EVO-010]], [[EDR-EVO-013]], [[EDR-EVO-014]], [[EDR-EVO-018]], REF-EXPERIMENT-PREFLIGHT.
