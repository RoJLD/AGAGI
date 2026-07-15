---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-022
type: EDR
title: "Le Payoff Moyens→Fins — Vérifié (cassé), puis Réparé par le Coup Critique Annealé"
status: legacy
gate: G2
---

# EDR 022 : Le Payoff Moyens→Fins — Vérifié (cassé), puis Réparé par le Coup Critique Annealé

## Contexte — étape 1 de la Vague 0bis : vérifier que la lance *paie*

La boucle d'émergence (EDR 021) produit des lances. Mais une lance **sert-elle** vraiment, ou
n'est-ce qu'un réflexe creux payé par le scaffold ? On a mesuré l'**économie pure du combat**
(ordre fidèle : riposte au `_move_preys` *puis* attaque au `_resolve_biology`).

### Constat : le payoff était CASSÉ

Tout le combat est « même case » (pas d'attaque à distance) → attaquer un gros gibier *implique*
de prendre sa riposte (sur le **hp**, létale à 100). Le seul gibier qui *requiert* une lance est le
**Mammouth** (hp 100 ; tout le reste meurt en 1 coup à mains nues). Or :

| vs Mammouth (hp100, riposte50) | issue |
|---|---|
| Mains nues (10 dmg) | meurt au tick 2, sans tuer |
| **Lance (50 dmg)** | **tue le Mammouth MAIS meurt aussi** (2 coups = 2 ripostes = 100 = sa vie) |

> La seule utilité de la lance est un **échange suicide** : tu tues l'apex mais tu meurs (le +105
> d'énergie est gâché, l'agent ne se reproduit pas). **Rien dans la survie/fitness ne récompensait
> le craft** — seul le scaffold. Aucun gradient → l'évolution ne pouvait *jamais* découvrir la
> chaîne lance→apex.

## Décision (V18.9) — coup critique annealé (« forcer le destin »)

Idée de l'utilisateur : la lance seule ne suffit pas (le Mammouth reste dangereux), **sauf un coup
critique** qui délivre le coup décisif. La proba de crit **décroît par monde** (scaffold annealé,
comme ε-greedy / approach / big-hit) : amorcer la découverte tôt, **sevrer** ensuite — sans
*entretenir* un acquis.

- `stone_economy.crit_chance(base, era, n_eras) = base · anneal(era, n_eras)` (pur).
- `stone_economy.attack_damage(weapon_dmg, is_crit, crit_mult=3.0)` (pur ; lance 50 → 150 = one-shot).
- `world.crit_base=0.6, crit_eras=20, crit_mult=3.0`. Dans `_resolve_biology` : crit roulé
  **uniquement avec une lance contre un gibier qui riposte** (`cfg.damage>0`).

## Résultat — le payoff existe tôt, se sèvre tard

Chasse au Mammouth, % qui **tuent ET survivent** (400 essais) :

| ère | crit | mains nues | avec LANCE |
|---|---|---|---|
| 0 | 0.60 | 0 % | **57 %** |
| 10 | 0.30 | 0 % | 30 % |
| 20 | 0.00 | 0 % | **0 %** |

> **Un gradient de fitness apparaît là où il n'y en avait aucun.** La lance vaut 57 % de
> victoires-survie tôt (avantage sélectif énorme pour les crafteurs-chasseurs) ; mains nues reste à
> 0 % (la lance est *requise*, jamais subventionnée) ; et le crit s'**auto-retire** (0 % à l'ère 20).

## Conséquences & question ouverte (à concevoir)

- Le crit donne le **foothold** évolutif : la sélection peut désormais gravir le lien craft→apex.
- **Persistance** (soulevée par l'utilisateur) : à crit→0, le payoff disparaît (0 %) → le
  comportement *décline* sauf si une **stratégie durable** prend le relais. Candidats déjà présents :
  le **feu** fait fuir le gibier (`_move_preys`), le **stun** existe. Combiner lance + feu/retraite
  /coopération = la voie auto-suffisante. **À concevoir** (et `crit_eras` à régler assez long pour
  laisser cette stratégie émerger avant le sevrage complet).
- Pré-requis désormais réuni pour l'**étape 2** (critic TD) : la chaîne moyens→fins a un payoff
  réel, mais **différé** (crafter → chercher → engager → tuer) → exige un crédit temporel.

## Variables d'expérience

`crit_base`, `crit_eras` (horizon de sevrage), `crit_mult`, gating du crit (lance+apex vs général),
+ futures mécaniques de persistance (feu/stun/retraite).
