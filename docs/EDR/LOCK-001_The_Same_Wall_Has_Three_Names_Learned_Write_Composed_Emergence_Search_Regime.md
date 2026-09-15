---
id: EDR-LOCK-001
type: EDR
title: "Le même mur porte trois noms — écriture APPRISE dans le report, émergence d'une compétence COMPOSÉE, régime de RECHERCHE : trois fils creusent le même verrou sans se citer"
status: active
verdict: SYNTHESIS_ONE_WALL_THREE_NAMES
gate: G1
tests: [SDR-G1]
extends: [EDR-EVO-016, EDR-DELAYED-COORD, EDR-156, EDR-157]
corrected_by: [EDR-LOCK-002]
---

> ⚠️ **QUATRIÈME MANIFESTATION RETIRÉE le 2026-09-14 — [[EDR-LOCK-002]] (verdict à n=12, règle scellée
> avant le run).** Elle était un **nul à pas fixe** (E19) : à `lr=0.002`, D=2 reste à la chance quel que
> soit le nombre d'épisodes (3 600, 7 200, 14 400) et son contrôle est dégradé ; à **`lr=0.0005`**,
> 12/12 seeds apprennent la rétention à deux délais (0,814 intact / 0,168 ablaté, ratio **4,85**,
> spécificité X_DECOY, garde d'alias SURGICAL). « Ni la capacité, ni le pas ne suffisent » était faux
> sur le pas — il n'avait pas été balayé. **Ce qui TIENT** : les trois premières manifestations et
> l'identité de structure qu'elles suggèrent — ce record n'y touche pas. **Ce qui change** : la
> prédiction n° 2 devient testable — le PAS perce le fil mémoire ; perce-t-il DELAYED-COORD à
> `lr=0.0005` ? S'il ne perce que celui-ci, l'identité est réfutée par sa propre clause.
> ✅ **TESTÉ le 2026-09-15 — [[EDR-LOCK-003]], n=12 : le même levier (pas bas ET durée) perce AUSSI le
> fil coordination** (RETAIN 0,284 → **0,420**, 12/12 seeds, ablation à la chance). La clause n° 2 ne
> s'applique pas : l'identité survit à son premier test falsifiable (deux fils sur trois). Nuance
> mesurée : le substrat favorable diffère (bilinéaire pour la mémoire, plain pour la coordination) —
> une identité de *levier*, pas de *réglage*.

## Pourquoi ce record existe

Constat de la cartographie des taxonomies (2026-09-02,
`docs/superpowers/specs/2026-09-02-cartographie-taxonomies.md`, convergence n°1) : trois fils du
dépôt butent sur ce qui a toutes les apparences du MÊME verrou, chacun l'a nommé dans son
vocabulaire, et aucun document ne les articule. Ce record est une SYNTHÈSE : il ne mesure rien de
neuf, il rend citable une identité de structure — et la transforme en prédiction falsifiable.

## Les trois noms

| fil | nom du mur | record-pivot | énoncé |
|---|---|---|---|
| taxonomy / langage | **« l'ÉCRITURE APPRISE dans le report ne marche pas »** | [[EDR-DELAYED-COORD]] | le report PASSIF d'information fonctionne (0,564 à D=2 par canal oracle), mais APPRENDRE à écrire dans le canal porté échoue |
| porte G1 | **« la compétence world-specifique n'ÉMERGE pas »** | [[EDR-156]]/[[EDR-157]] | le transfert zéro-shot est réel mais c'est le NOYAU PARTAGÉ qui transfère ; durcir le monde jusqu'à rendre le stockage load-bearing ne le fait PAS émerger — l'évolution dégrade au lieu de spécialiser |
| arc EVO | **« le verrou est le RÉGIME DE RECHERCHE »** | [[EDR-EVO-016]] | une lecture qui DOUBLE la durée de vie et tient en un fil n'est pas trouvée par la sélection par la survie (0/12) — la recherche s'arrête à la politique fixe |

## L'identité de structure

Dans les trois cas : **une capacité dont la valeur est établie (le monde la paie, ou l'oracle la
démontre) n'est pas ATTEINTE par le processus d'optimisation disponible** — et l'échec n'est pas un
échec de substrat (le substrat PORTE la solution quand on la lui donne : oracle 0,564, noyau
transféré 12/12, lecteur câblé qui double la survie) mais un échec du CHEMIN : écrire, composer,
découvrir sont la même opération vue de trois postes — créer une dépendance NOUVELLE entre un état
interne et une sortie, que ni le gradient épisodique ni la sélection ne récompensent avant qu'elle
soit déjà fonctionnelle. C'est la forme générale du résultat S2 (« le gradient de sélection pour la
cognition est nul ») et la raison structurale du « proxy 9 / in-world 0 ».

## Quatrième manifestation (2026-09-02, EXPLORATOIRE — n=3, pas un verdict) — ⛔ RETIRÉE le 2026-09-14 par [[EDR-LOCK-002]] : artefact de pas (E19), voir le bandeau

Le bandeau de rétro-audit de [[EDR-DELAYED-COORD]] bornait son mur à `lr=0.05` (mauvais côté de la
bascule E19). Le balayage S1 du point-référence (`results/lang_memory_sweep.json`) fournit la
première mesure du même mur du BON côté : au point où la référence D=0 apprend (bilinéaire,
`lr=0.002`, 3600 épisodes, médiane 0,744), la MÊME tâche à **D=2 reste 3/3 à la chance**
(0,211/0,183/0,170) avec le contrôle dégradé (~0,55). Ni la capacité (bilinéaire), ni le pas
(0,002) ne suffisent : sous crédit REINFORCE, la rétention 2-délais ne s'apprend pas là où la
rétention 1-tick s'apprend. Indication convergente, à confronter au balayage prescrit par la spec
de DELAYED-COORD avant toute citation comme propriété de substrat.

## Ce que l'identité PRÉDIT (falsifiable)

Si les trois noms désignent un seul mur, **un levier qui perce l'un doit percer les autres** :

1. le warm-start ([[REF]] loi transversale : un bassin pré-formé franchit ce que le froid ne
   franchit pas) devrait débloquer l'écriture apprise SI on amorce le canal d'écriture — testable
   sur la tâche D=2 ci-dessus (amorçage supervisé court, puis REINFORCE) ;
2. symétriquement, un levier qui perce UN fil sans effet sur les autres RÉFUTE l'identité — le
   résultat serait aussi précieux : trois murs distincts exigent trois attaques distinctes ;
3. EVO-028 contraint déjà l'attaque côté évolution : la conversion d'un tirage décroît faiblement
   avec la position (0,65-0,77) — le chemin par la sélection paie plus tôt que tard.

## Portée

* Synthèse : aucune mesure nouvelle n'y est gravée ; chaque énoncé cité garde ses hedges d'origine
  (notamment le bandeau `lr` de DELAYED-COORD et le caveat E19 sur tout nul 2-pas).
* La 4ᵉ manifestation est exploratoire (n=3, tâche `(q+key)%K` ≠ coordination référentielle,
  protocole différent) — elle ORIENTE, elle ne tranche pas.
* Porte G1 : c'est le mur nommé par [[EDR-157]] qui bloque « G1 fort » ; percer ce mur EST le
  critère de la prochaine porte (cf. gap T1 : sceller SDR-G2 sur cette matière).
