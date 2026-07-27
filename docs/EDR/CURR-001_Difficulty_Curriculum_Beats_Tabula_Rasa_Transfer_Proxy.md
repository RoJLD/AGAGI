---
id: CURR-001
type: EDR
title: "Un CURRICULUM de difficulté (facile->plein) BAT le tabula-rasa à budget égal — proxy standalone de transfer_ratio (Dev #3), non-collidant (la vraie mesure in-world tourne la biosphère partagée). Jeu compositionnel dims FIXES (A=4) : TABULA entraîne 12000 ép sur la tâche pleine (valeurs {0,1,2,3}) ; CURRICULUM = 6000 ép sous-monde facile ({0,1,2}) + 6000 plein. À budget égal, CURRICULUM > TABULA : within 0.432 vs 0.398 (ratio au-dessus chance 1.41), zeroshot 0.547 vs 0.438 (ratio 1.84). Transfert RÉEL (le bras curriculum ne voit le plein que 6000 ép mais finit plus haut). Bénéfice plus fort en GÉNÉRALISATION (1.84) qu'en maîtrise (1.41) = cohérent LANG-005 (curriculum façonne la systématicité). 4e instance de la loi warm-start transversale (après social 004, rétention 167/168/170, craft-or-starve EDR-200)"
status: accepted
gate: null
verdict: CURRICULUM_TRANSFERS_ON_DIFFICULTY
---

# CURR-001 : un curriculum de difficulté bat le tabula-rasa (proxy de transfer_ratio)

## Contexte

`tools/curriculum_transfer.py` (Dev #3) mesure IN-WORLD si un curriculum développemental (échelle de mondes)
transfère mieux que le tabula-rasa — mais il tourne la VRAIE biosphère (KuzuDB partagée → collision avec la
session // in-world + run lourd > 1 h). Ici : PROXY standalone, même question, sur l'axe DIFFICULTÉ DE TÂCHE
du jeu compositionnel (LANG-003) — non-collidant, méthode des proxies. Complète l'arc de la loi
warm-start/curriculum, montrée sur l'axe SOCIAL par LANG-004 : le curriculum aide-t-il aussi sur la
difficulté ? Prédiction : oui, si le curriculum aide à échapper à l'équilibre partiel diagnostiqué (LANG-005).

## Méthode

`tools/compositional_transfer_probe.py`. Dims FIXES (A=4 toujours alloué ; seule la plage de valeurs
échantillonnée en entraînement change → poids transférables) :
- **TABULA** : entraîne directement sur la tâche PLEINE (valeurs {0,1,2,3}) pendant E=12000 ép.
- **CURRICULUM** : phase 1 sur le sous-monde FACILE (valeurs {0,1,2}, 6 combos) 6000 ép, phase 2 PLEINE
  6000 ép → BUDGET TOTAL ÉGAL (12000).

Métriques (greedy) : within (combos entraînés) + zeroshot (diagonale held-out, inclut (3,3) dont la valeur 3
n'apparaît qu'en phase 2). Ratio par seed `(curr−chance)/(tab−chance)`, médiane. M=8, V=6, 2 seeds.

## Constat

| Bras | within | zeroshot |
|---|---|---|
| TABULA (12000 plein) | 0.398 | 0.438 |
| CURRICULUM (6000 facile + 6000 plein) | 0.432 | 0.547 |
| **ratio curr/tab (au-dessus chance)** | **1.41** | **1.84** |

(chance = 0.25 ; `VERDICT = CURRICULUM_TRANSFERS_ON_DIFFICULTY`.)

## Lecture

- **Le curriculum de difficulté BAT le tabula-rasa à budget égal.** Ratio > 1 sur les deux métriques
  (within 1.41, zeroshot 1.84). C'est un TRANSFERT RÉEL, pas un artefact de compute : le bras curriculum ne
  voit la tâche PLEINE que 6000 ép (vs 12000 pour tabula) et finit pourtant plus haut → **6000 facile + 6000
  plein > 12000 plein**. Le sous-monde facile bootstrap une structure compositionnelle réutilisable.
- **Le bénéfice est plus fort en GÉNÉRALISATION (1.84) qu'en maîtrise (1.41).** Écho direct de LANG-005 : les
  leviers curriculum/warm-start façonnent la SYSTÉMATICITÉ plus que l'accuracy brute. Le zeroshot inclut
  (3,3), valeur 3 introduite seulement en phase 2 : le code appris sur {0,1,2} s'ÉTEND à la valeur 3 avec
  moins d'entraînement → transfert systématique (la compositionnalité acquise sur le sous-monde généralise).
- **4e instance de la loi warm-start transversale.** Le curriculum débloque/améliore sur l'axe DIFFICULTÉ DE
  TÂCHE — après l'axe SOCIAL (LANG-004, partage), la RÉTENTION (167/168/170), et le CRAFT-OR-STARVE (EDR-200
  Phase B, binding sous curriculum). Même mécanisme : un bassin pré-formé sur un sous-problème franchit une
  barrière que l'attaque directe ne franchit pas aussi bien.

## Conséquences

- **Proxy POSITIF de `transfer_ratio` (Dev #3)** : au niveau proxy, le curriculum développemental TRANSFÈRE
  (bat le tabula-rasa) → dé-risque l'expérience in-world (le re-test `curriculum_transfer.py` n'a plus à
  établir l'existence de l'effet, seulement sa magnitude in-world). Même schéma que les proxies langage/H-unif.
- **Recette générique** : face à une tâche dure sous crédit épisodique, un **curriculum de sous-problèmes**
  (facile→plein) est un levier bon marché (budget égal, gain net) — surtout pour la GÉNÉRALISATION. In-world :
  échelle de mondes / curriculum de difficulté croissante (cf. `CurriculumRunner`, `main_curriculum`).
- Relié : `REF-LTC -A_ADOPTER_POUR-> CURR-001`. Étend la **loi warm-start transversale** (`docs/roadmap/SCIENCE.md`,
  callout 🔑) à 4 instances. Recoupe [[lang-referential-capability]] (LANG-004/005), le fil rétention de
  [[sota-gap-substrate]] (167/168/170), et [[decisive-substrate-thesis-test]] (EDR-200). ID préfixé `CURR-`
  (nouvel axe curriculum/transfert ; espace EDR-NNN contesté par sessions //).

## Caveats

1. 2 seeds : le ROBUSTE = ratio > 1 sur within ET zeroshot + le transfert réel (6000+6000 > 12000). Décimales
   bruitées ; plus de seeds affineraient la magnitude.
2. Proxy standalone (jeu compositionnel), PAS l'in-world : le vrai `transfer_ratio` (survie cross-world) reste
   à lancer (biosphère ; collision-aware avec la session //). Le proxy établit l'EFFET, pas sa magnitude
   in-world (où le plancher de survie, EDR-085/090, peut dominer).
3. Sous-monde facile = SOUS-ENSEMBLE strict de valeurs (curriculum « emboîté ») ; un curriculum de tâches
   disjointes (transfert lointain) serait plus dur — non testé.
4. Le gain absolu reste borné par le plafond « régime d'optim » (LANG-005) : le curriculum aide à mieux
   converger DANS ce régime, il ne change pas le plafond fondamental (within reste < 0.5).
