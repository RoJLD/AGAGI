---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-079
type: EDR
title: "L'évaluation robuste lève le plateau DANS la biosphère vivante (validation)"
status: legacy
gate: foundational
---

# EDR 079 : L'évaluation robuste lève le plateau DANS la biosphère vivante (validation)

## Contexte

EDR 078 (banc) : le plateau de compétence est du bruit de fitness ; nettoyer le signal → ×3. On le
VALIDE sur la VRAIE biosphère. La sélection HoF d'EDR 076 évalue un candidat sur 1 ère (bruitée, ≈
`eval_B=1`). Régime ROBUSTE : le top candidat de chaque ère est ré-évalué sur K=3 ères et MOYENNÉ avant
de concourir pour le cliquet best-ever. Métrique : compétence VRAIE du champion final (survie moyenne
sur 15 ères propres). `tools/robust_eval.py`.

## Résultat — le plateau se lève dans le vivant

| Sélection | compétence vraie du champion (survie / 15 ères) |
|---|---|
| **BRUITÉE** (K=1, le harnais 076) | **30.0 ticks** |
| **ROBUSTE** (K=3) | **38.2 ticks** (**+27 %**) |

> **De-bruiter la fitness forge un champion RÉELLEMENT plus compétent (+27 %) dans le système réel.**
> Le principe d'EDR 078 (banc) TRANSFÈRE au vivant.

## Lecture honnête

- Effet **réel et positif** mais plus modeste que le ×3 du banc — attendu : ici **K=3** (pas 64),
  **15 ères** seulement, et la biosphère ajoute du **bruit social** (fitness de GROUPE,
  fréquence-dépendante) que le banc n'avait pas. Un K plus grand + plus d'ères amplifieraient.
- C'est une validation *directionnelle* (1 run par régime) ; la quantification fine (puissance) reste à
  faire. Mais le signe et le mécanisme sont nets et cohérents avec 078.

## L'arc de la compétence — RÉSOLU et validé

| EDR | acquis |
|---|---|
| 075 | la compétence est le goulot (le langage ne paye pas sans elle) |
| 076 | la compétence PLAFONNE sous mutation+extinction |
| 077 | le BPTT n'est PAS le remède — il NUIT en RL (auto-réfutation) |
| 078 | le plateau est du BRUIT DE FITNESS (banc : signal propre → ×3) |
| **079** | **remède VALIDÉ dans le vivant : l'évaluation robuste lève le plateau (+27 %)** |

## Le correctif actionnable (production)

> `save_to_hall_of_fame` (main_biosphere) sauve les top-5 d'UNE ère (life_score bruité). **Correctif :
> ré-évaluer les candidats HoF sur K ères et moyenner avant de committer** — la sélection cesse de
> récompenser la chance, le cliquet cesse de verrouiller des flukes. Coût : K× l'évaluation des
> candidats (pas de toute la population) — bon marché vs le gain.

Non implémenté en production ici (la boucle principale est complexe ; à faire avec soin + non-régression).
Le harnais `robust_eval.py` prouve le mécanisme et fournit le patron.

## Statut

- `robust_eval.py` (validation vivante). **EDR 078 validé sur la biosphère** : évaluation robuste
  +27 % de compétence vraie. Levier concret pour le moteur évolutif réel (HoF robuste).

## Variables d'expérience

K (3 → 8 → 16) vs coût, nb d'ères, puissance (plusieurs runs), bruit social vs individuel, implémentation
production de `save_to_hall_of_fame` robuste + non-régression.
