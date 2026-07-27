---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-021
type: EDR
title: "Affordance Matérielle — la Boucle d'Émergence Complète Tourne"
status: legacy
gate: G2
---

# EDR 021 : Affordance Matérielle — la Boucle d'Émergence Complète Tourne

## Contexte

L'EDR 020 a réparé l'apprentissage (l'Actor-Critic encode le geste `grab` ; phase 1 = 752
crafts, tenu à ε=0.01). Mais le **transfert** au monde dur restait à ~1-2. Diagnostics :
1. *Domain gap* : les génomes grab-entraînés grabent peu dans le monde dur (obs différentes).
2. Tentative de **ramp de difficulté** (items 60→5) : quand les items deviennent rares, le
   craft tombe à ~1 **même en entraînement** → ce n'est pas un problème d'apprentissage.

> **Cause réelle** : une **limite physique**. Le monde dur ne spawnait que ~8-13 matériaux ;
> avec 5 rochers + 5 sticks pour 30 agents qui doivent survivre, il n'y a tout simplement pas
> assez de matière pour collecter un couple rock+stick. Même une politique de grab parfaite ne
> peut crafter ce qui n'existe pas. Fix ni cognitif ni d'apprentissage : **écologique**.

## Décision (V18.8)

Donner au monde normal assez de matériaux pour que le craft soit une stratégie **viable** :
- Spawn initial de rochers 5 → **18**.
- **Régénération de matériaux** dans `step` (off en entraînement) : maintenir ~24 rock+stick,
  régén ~0.5/tick.

## Résultat — la boucle complète tourne

Curriculum (entraînement item-riche pour l'encodage, ε annelé ; puis monde dur **pourvu**) :

- Phase 1 (entraînement) : **678** lances (encodage fort).
- **Phase 2 (monde dur, ε=0) : 21 lances** (vs 0-2 auparavant), ET **croissante** :

| ère normale | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| crafts | 1 | 1 | 1 | 0 | 0 | 4 | 2 | 2 | 2 | **6** | 2 | 0 |

> **Le craft transfère au monde dur ET grandit d'ère en ère** (1→6). Les trois fixes de la
> session **composent** : ε-greedy *produit* le geste → Actor-Critic l'*encode* → le monde
> pourvu le rend *viable* → HoF + craft-fitness *sélectionnent* les crafteurs → *propagation*
> → le craft *évolue*.

## Conclusion — objectif de session atteint

```
exploration (ε)  →  encodage (Actor-Critic, EDR 020)  →  monde qui afford (matériaux, EDR 021)
   →  sélection (HoF sauvé EDR 016 + craft-fitness)  →  propagation  →  ÉVOLUTION du craft
```

**Premier comportement composé (collecter→crafter) appris, encodé, transféré ET en évolution
du projet.** L'objectif initial — faire émerger le craft — est atteint, sur des fondations
réparées (moteur évolutif + apprentissage), pas sur des béquilles.

## Limites & suites

- 21 lances reste **modeste** (monde dur, vies courtes) — mais c'est transférant *et* croissant,
  vs ~1 historique. Consolider : plus d'ères normales, tuning de la régén matériaux.
- Maintenant que la **boucle d'émergence est prouvée** sur le craft L0, on peut la rejouer sur
  les axes développementaux : **ramper `craft_level`** (axe Craft : L0→L1→…) et la **difficulté
  du monde** (axe Monde), chaque palier maîtrisé puis durci — le programme de la roadmap.

## Variables d'expérience

Cible de matériaux (24), taux de régén, spawn initial de rochers, nombre d'ères normales.
