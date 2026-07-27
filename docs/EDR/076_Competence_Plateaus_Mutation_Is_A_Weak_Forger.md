---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-076
type: EDR
title: "La compétence PLAFONNE — la mutation est un forgeron faible (la boucle se referme)"
status: legacy
gate: foundational
---

# EDR 076 : La compétence PLAFONNE — la mutation est un forgeron faible (la boucle se referme)

## Contexte

EDR 075 : le bénéfice du langage est gaté par la COMPÉTENCE du substrat (agents qui survivent + chassent
le Mammouth). Question fondamentale : la compétence ÉVOLUE-t-elle sous le moteur historique du projet
(mutation + sélection par extinction + cliquet HoF) ? Harnais isolé (`evolve_competence.py`) :
population propre, reproduction `build_population` (élite + enfants mutés), sélection par `life_score`,
30 ères. **Le step lance l'Actor-Critic intra-vie** (`world_1_stoneage:1379`) — gradient présent.

## Rigueur : deux bugs de harnais débusqués avant toute conclusion

Un harnais qui contredit la référence (1 ère ≈ 58 ticks via `init_primordial_soup`) est suspect, pas une
découverte (discipline EDR 054) :
1. **Sans élitisme** (mutation de tous les agents) → effondrement à 1 tick. `build_population` garde
   l'élite intacte (EDR 024).
2. **Chargement HoF faux** (`h["genome"]` sur des tuples/objets) → fallback sur génomes FRAIS → testait
   « frais → effondrement », pas « HoF → évolution ».
Corrigé : 1 ère depuis le HoF = **54-62 ticks** = la référence. Harnais validé.

## Résultat (harnais validé)

| Régime | survie ères 1-5 → 26-30 | Mammouths | life_score | lecture |
|---|---|---|---|---|
| **SANS cliquet** | 46 → **5** | 1.8 → 0 | 553 → 140 | **EFFONDREMENT** |
| **AVEC cliquet** (HoF réel) | 40 → 29 | ~0.6 → 0.8 | 402 → 442 | **PLATEAU** |

- **Sans cliquet** : la compétence s'effondre — mutation + bruit de sélection (ères courtes,
  extinction) érodent les ancêtres compétents.
- **Avec cliquet best-ever** (comme le vrai HoF) : plus d'effondrement, mais **PLATEAU** — la compétence
  se tasse même sous la base (59 → ~30 ticks) puis stagne ; `life_score` plat (402→442, variance
  101-653) ; Mammouths sporadiques (bruit). Le verdict auto a sur-lu un « MONTE » sur le tic Mammouth ;
  la lecture honnête est un plateau.
- **Et ce, MALGRÉ l'Actor-Critic intra-vie** (gradient one-step, EDR 020). Lui non plus ne forge pas la
  compétence ici (ères trop courtes 5-60 ticks pour que le RL compose ; gradient one-step faible, 071).

## Le vrai enseignement — LA BOUCLE DU PROJET SE REFERME

> **La mutation est un forgeron FAIBLE — partout.** Trois fois la même vérité, maintenant sur le levier
> le plus fondamental (la compétence elle-même) :
> - **Mémoire (067)** : mutation plafonne 0.78 → gradient (BPTT) 1.00.
> - **Langage (072)** : mutation = loterie 25 % → gradient 100 %.
> - **Compétence (076)** : mutation + extinction *maintient* (via cliquet) mais ne *forge* pas — plateau.

> Le **cliquet HoF best-ever** explique pourquoi la biosphère ne s'effondre pas (il empêche la perte) —
> mais **empêcher la perte n'est pas créer la compétence**. Le levier universel reste le **gradient FORT**
> (classe BPTT, 067) avec assez d'horizon temporel — *pas* plus d'ères de mutation, *pas* l'Actor-Critic
> one-step (insuffisant ici).

## Honnêteté

- Le harnais isole le **cœur** du moteur (mutation + extinction + élite + cliquet + Actor-Critic) ; la
  vraie biosphère a des extras (tuner, superviseur, curriculum annelé) non répliqués. Mais le cœur est
  fidèle (validé à l'ère 1) et il plafonne — cohérent avec 067/072.
- Plateau = « pas d'amélioration nette sur 30 ères », pas « zéro compétence » (la base ~30-59 ticks +
  Mammouths sporadiques existe, maintenue par le cliquet). Elle est juste **insuffisante** (EDR 075) et
  ne progresse pas.

## Suite (re-cadrée par cette synthèse)

> Pour forger la compétence (et donc, ensuite, rendre le langage utile, 075) : **gradient FORT à horizon
> long DANS l'agent** — un apprentissage RL par gradient à travers le temps (BPTT-RL, la classe d'outil
> validée en 067/071), pas la mutation+extinction ni l'Actor-Critic one-step. C'est le grand chantier
> cohérent : intégrer le gradient fort dans la vie de l'agent, là où la mutation a montré ses limites
> sur mémoire, langage, ET compétence.

## Statut

- `evolve_competence.py` (harnais validé, cliquet). **Compétence : plateau sous mutation+extinction**
  (maintenue, non forgée), malgré l'Actor-Critic. Confirme sur le levier fondamental le verdict de
  067/072 : la mutation maintient, le gradient fort forge.

## Variables d'expérience

Horizon des ères, force du gradient intra-vie (one-step vs BPTT), diversité du cliquet, métrique de
sélection (life_score vs compétence-coordination), monde re-calibré (survie + apex), nb d'ères (≥30).
