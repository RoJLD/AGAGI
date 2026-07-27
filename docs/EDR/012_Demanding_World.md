---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-012
type: EDR
title: "Monde Exigeant (Step 2) & Premier Verdict de Falsifiabilité"
status: legacy
gate: G0
---

# EDR 012 : Monde Exigeant (Step 2) & Premier Verdict de Falsifiabilité

## Contexte

Levier 2 de l'audit (EDR 010), seconde moitié de la **Vague 0** (couplée au World Model, EDR 011). Le scan avait établi que le monde *n'exige pas* l'intelligence : nourriture infinie (+50 plat par proie, respawn instantané), récompenses gratuites, dégâts plats. L'optimum était « farmer le Lapin le plus proche » — aucune tâche ne récompensait la planification ou l'outil.

Cet EDR fige les mécaniques de Step 2 **et** le résultat du premier vrai run (30 ères) qui les a mesurées — car le résultat est le livrable principal.

## Décision (V18.0) — la chaîne moyens→fins

Rendre l'intelligence *instrumentale* via quatre mécaniques (`src/environments/stone_economy.py`, câblées dans `world_1_stoneage.py`) :

| Mécanique | Avant | Après |
|---|---|---|
| Récompense de chasse | +50 plat (Lapin = Mammouth) | ∝ difficulté : `prey_reward(hp)` — Lapin ~9.8, Mammouth ~89 |
| Rareté | respawn instantané + refill total/step | régénération lente plafonnée (`prey_regen_rate`) → capacité de charge |
| Dégâts | 10 plat | `weapon_damage(has_spear)` : 10 mains nues, 50 à la lance |
| Outil | aucun | recette `rock + stick → Spear` (physique-driven) sur `do_rub` |

Logique : nourriture facile rare → le gros gibier devient le gain → mais il faut une lance → donc grab + grab + craft + traquer. La première tâche du repo qui *exige* la cognition.

## Résultats empiriques — Run V18_V0 (30 ères, stoneage, 100 agents)

| Signal | Mesure | Lecture |
|---|---|---|
| Chasse | **900 proies tuées** / 1133 attaques | Les agents mangent — pas de famine par incapacité |
| **Craft** | **1 lance** sur **4272 naissances** | La boucle moyens→fins n'émerge **essentiellement jamais** |
| Survie | extinction à **50-60 ticks à chaque ère** | **Zéro adaptation** sur 30 ères |
| Énergie moyenne | **~25, plate** (23-29) | Aucune tendance d'apprentissage évolutif |
| Surprise (World Model) | ~0.04, vivante mais plate | Step 1 confirmé en prod ; dynamique de base apprise |

## Diagnostic

Le monde **fonctionne et exige** (rareté, chasse, surprise vivante, reproduction : 4272 naissances). Mais l'émergence visée échoue, pour deux raisons cumulées :

1. **Crash malthusien** : 100 agents dans un monde 10×10 avec ~9 proies à régen 0.30 → capacité de charge réelle ~10-15. ~85 agents meurent de faim instantanément, avant toute exploration.
2. **Chaîne trop profonde pour un cold-start** : la lance exige une séquence longue (`grab rocher → grab stick → rub → trouver Mammouth → frapper ×2`) **sans récompense intermédiaire**. La mutation aléatoire ne la franchit pas (1/4272) ; un monde dur à vies courtes ne laisse pas le temps d'explorer. Problème classique de *reward sparse / deep exploration*.

## Verdict de falsifiabilité

> **L'hypothèse « un monde dur seul → l'intelligence émerge » est RÉFUTÉE à cette calibration.**

Ce n'est pas un échec : c'est le harnais de falsifiabilité (EDR 008/009) qui livre son verdict, et il **valide empiriquement** l'EDR 010 et la roadmap. Un monde exigeant est **nécessaire mais pas suffisant** — il faut rendre le comportement profond *apprenable*. Exactement ce que prévoyaient :
- le **scaffold de récompense** (axe 5 / le « cheatcode » mis de côté) — récompenses intermédiaires pour amorcer une chaîne profonde ;
- le **curriculum de difficulté** (staging via `CurriculumRunner`).

On a *prouvé pourquoi* ces briques sont nécessaires, au lieu de le supposer.

## Conséquences — prochains leviers (combinables)

- **(A) Scaffold de récompense** : récompenses intermédiaires *annelées* le long de la chaîne (grab +ε, craft +δ, coup sur gros gibier +γ), retirées une fois le comportement acquis.
- **(B) Curriculum de difficulté** : démarrer apprivoisé, durcir à mesure que la compétence monte (CurriculumRunner appliqué à la difficulté, pas qu'aux mondes).
- **(C) Recalibrage écologique** : matcher la capacité de charge (moins d'agents / régen+ / monde+) pour qu'une population persiste assez pour explorer.

## Variables d'expérience (Commandement 15)

`PREY_REWARD_BASE`, `PREY_REWARD_SCALE`, `SPEAR_DAMAGE`, `BASE_DAMAGE` (stone_economy) ; `prey_regen_rate`, `target_prey_count`, taille du monde, nombre d'agents (config/world). Toutes à mesurer en ablation.

## Notes d'outillage

- `main_biosphere.py` : ajout d'un garde-temps `MAX_TICKS_PER_ERA=1200` et d'un mode `HEADLESS` (opt-in, ne change pas le comportement interactif) pour les runs en arrière-plan.
- Mesures : `results/metacognition_logs.csv` (trajectoire) + comptage `LogEvent` dans KuzuDB (PREY_KILLED, SPEAR_CRAFTED).
