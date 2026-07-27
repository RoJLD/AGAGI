---
id: LANG-002
type: EDR
title: "La ROTATION DE PARTENAIRES transforme des codes PRIVÉS en un PROTOCOLE PARTAGÉ (Arc 4 langage, clôt le caveat #2 de LANG-001 : coordination appariée ≠ langage). Un batch torch = N politiques DISTINCTES (W (B,N,N), bmm par agent) : sous appariement FIGÉ chaque paire sender_i↔receiver_i invente un code PRIVÉ (within 0.80 vs cross ≈ chance 0.17, MI≈0 à toutes tailles 8/16/32/128 = aucune intelligibilité mutuelle). Sous ROTATION (partenaire aléatoire par épisode) un protocole PARTAGÉ émerge (M=8 : within 0.58 / cross 0.54 / MI 0.94 ; M=16 : 0.43/0.44/1.06) : ~tout le skill within transfère à un partenaire JAMAIS co-entraîné. Loi de consensus : la précision partagée décroît avec M (0.58→0.43→0.31→0.19) mais MI reste ≈1 -> l'échec à M=128 = goulot de CONVENTIONNALISATION, pas incapacité du substrat. La rotation CAUSE le protocole partagé"
status: accepted
gate: null
verdict: PARTNER_ROTATION_YIELDS_SHARED_PROTOCOL
---

# LANG-002 : la rotation de partenaires transforme des codes privés en un protocole partagé (Arc 4)

## Contexte

LANG-001 a établi que le substrat torch développe une signalisation référentielle porteuse (FIABLE 0.77
vs chance/BROUILLÉ 0.17), mais avec un **caveat #2 explicite** : les 128 paires étaient APPARIÉES
(sender_i↔receiver_i figé) → c'est un test de *coordination*, pas de *langage*. Un vrai langage est un
protocole **partagé** (mutuellement intelligible dans une communauté), pas un code privé propre à une paire.

Fait d'architecture clé : un batch torch n'est PAS une politique répliquée — `self.W` est `(B,N,N)` et
`_step` fait un `torch.bmm` **par agent**, chaque `MambaAgent()` étant initialisé avec des poids aléatoires
distincts (`randn·0.1`). Les 128 « agents » sont donc 128 politiques DISTINCTES entraînées en parallèle.
LANG-001 apprenait ainsi 128 protocoles sender_i↔receiver_i potentiellement **privés**. LANG-002 le teste.

## Méthode

`tools/referential_community_probe.py`. Même jeu de Lewis que LANG-001 (crédit épisodique, sans gate), mais
l'appariement de l'épisode est un **décalage cyclique** s : sender_i ↔ receiver_{(i+s) mod M} (implémenté
par `np.roll` du signal et de la cible ; la reward du sender est ré-alignée par `roll(-s)`).

- **FIXED** (rotate=False) : s=0 toujours → paires figées (réplique LANG-001).
- **ROTATION** (rotate=True) : s aléatoire non-nul par épisode → chaque sender parle à des receivers variés
  → pression de conventionnalisation (effet communauté).

Métrique = **intelligibilité mutuelle**. Éval greedy : accuracy WITHIN (s=0, paire d'origine) vs CROSS
(moyenne sur décalages s>0 = partenaires JAMAIS appariés directement). `MI = (cross−chance)/(within−chance)`
= fraction du skill within qui transfère à un partenaire neuf (code privé → MI≈0 ; partagé → MI≈1). Sweep
de taille de communauté M∈{8,16,32,128}, K=6, V=8, 2 seeds, 3000 ép (2000 pour M=128).

## Constat

| M | FIXED within | FIXED cross | FIXED MI | ROTATION within | ROTATION cross | ROTATION MI |
|---|---|---|---|---|---|---|
| 8 | 0.804 | 0.186 | 0.03 | 0.583 | 0.544 | **0.94** |
| 16 | 0.811 | 0.170 | 0.01 | 0.425 | 0.438 | **1.06** |
| 32 | 0.830 | 0.164 | −0.00 | 0.312 | 0.306 | **0.96** |
| 128 | 0.797 | 0.163 | −0.01 | 0.195 | 0.186 | nan (non-convergé) |

(chance = 0.167 ; `VERDICT = PARTNER_ROTATION_YIELDS_SHARED_PROTOCOL`.)

## Lecture

- **FIXED = codes PRIVÉS, robustement, à toutes les tailles.** within ~0.80 (reproduit LANG-001 0.77) mais
  cross = chance (0.16–0.19), MI ≈ 0. Chaque paire i a inventé un mapping cible→symbole ARBITRAIRE qu'aucun
  autre receiver ne sait décoder. C'est le caveat #2 de LANG-001, désormais **mesuré** : la coordination
  appariée n'est pas un langage.
- **ROTATION = protocole PARTAGÉ.** cross ≫ chance et MI ≈ 0.94–1.06 : **quasiment tout** le skill within
  transfère à un partenaire jamais co-entraîné. La rotation force une CONVENTION commune. Le substrat torch,
  sous crédit épisodique, sait donc conventionnaliser — pas seulement coordonner par paire.
- **Loi de consensus (scaling).** Sous rotation, la précision partagée DÉCROÎT avec M (0.58→0.43→0.31→0.19)
  alors que MI reste ≈1 : *ce qui est appris est intégralement partagé*, mais atteindre UNE convention
  globale dans un budget d'épisodes fixe devient plus dur quand la communauté grandit. La non-convergence à
  M=128 (≈chance) n'est donc PAS une incapacité du substrat — c'est le **goulot de conventionnalisation**,
  cohérent avec l'extrapolation du trend. MI et absolu se dissocient : le substrat partage tout ce qu'il
  parvient à conventionnaliser, la limite est le *temps de consensus*, pas la partageabilité.

## Conséquences

- **Clôt le caveat #2 de LANG-001** : le substrat ne fait pas que coordonner par paire, il développe un
  protocole PARTAGÉ **quand la structure d'entraînement l'exige** (rotation). Le marqueur « langage »
  (mutuelle intelligibilité) est atteint. Prérequis renforcé pour l'in-world 087.
- **Recette langage torch, complétée** : crédit épisodique (`learn_episode`) suffit pour la signalisation
  (LANG-001) ; **la rotation de partenaires est le levier qui la rend PARTAGÉE** (LANG-002). In-world, cela
  prédit qu'un langage commun émerge si les agents interagissent avec des partenaires VARIÉS (pas des dyades
  figées) — une contrainte de design du monde, pas du substrat.
- **Levier ouvert pour le scaling** : le goulot de consensus (précision partagée ↓ avec M) est le prochain
  verrou langage. Pistes non testées : curriculum de taille de communauté, rotation partielle (pool de
  partenaires), ou un canal partagé (readout commun). Le gate multi-cible (LANG backlog / EDR-165) pourrait
  aider au routage sur symbole à K élevé.
- Relié : `REF-LTC -A_ADOPTER_POUR-> LANG-002`. Prolonge [[lang-referential-capability]] (LANG-001). Recoupe
  la SOTA `langage→EGG` (community effect / conventionnalisation) de [[sota-gap-substrate]].

## Caveats

1. La compositionnalité STRUCTURELLE (systématicité : référents attribut×valeur, messages multi-symboles,
   généralisation zéro-shot à des combinaisons inédites) n'est PAS testée — LANG-002 teste la
   *conventionnalisation / intelligibilité mutuelle* (protocole partagé vs privé), pas la structure interne
   du code. Symboles atomiques (V≤8), un symbole par référent. C'est le prochain axe langage (LANG-003).
2. 2 seeds ; le ROBUSTE = le CONTRASTE qualitatif (FIXED MI≈0 vs ROTATION MI≈1) + la monotonie du scaling,
   pas les décimales. À M=128 la rotation ne converge pas dans le budget (2000 ép) — cohérent avec la loi,
   mais non poussé à convergence (plus d'épisodes / curriculum non sweepés).
3. Proxy synthétique hors biosphère (même bornage que LANG-001) : le vrai bénéfice = in-world (087). La
   rotation y correspond à des interactions multi-partenaires ; à vérifier que le monde l'offre.
4. MI est ininterprétable quand un régime n'apprend pas (within≈chance → dénominateur ~0) ; marqué `nan` et
   exclu (cf. M=128 ROTATION). Le discriminant robuste reste le CROSS absolu (au-dessus de la chance ou non).
