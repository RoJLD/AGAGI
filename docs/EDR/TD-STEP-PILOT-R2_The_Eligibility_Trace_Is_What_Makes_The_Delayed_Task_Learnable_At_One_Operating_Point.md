---
id: EDR-TD-STEP-PILOT-R2
type: EDR
title: "Balayage lr × λ du crédit TD PAR PAS : à lr 4,0 la trace d'éligibilité n'est pas un bonus, elle est CE QUI REND la tâche différée apprenable (λ 0,9 et 0,99 franchissent la barre de la référence sur 11/12 seeds, λ 0 et 0,5 sur 1/12 et 3/12) ; au pas moitié AUCUN bras à délai n'apprend, donc l'invariance au pas reste OUVERTE et non réfutée ; lecture scellée `AIDE_A_UN_POINT`"
status: active
verdict: AIDE_A_UN_POINT
gate: G4
tests: [SDR-G4]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-TD-STEP-PILOT-R0, EDR-LOCK-003]
---

> **Règle scellée AVANT toute cellule** : `TD-STEP-PILOT-R2` (`docs/preregistrations/TD-STEP-PILOT-R2.json`),
> runner `tools/td_step_pilot.py --r2`, résultats `results/td_step_pilot_r2.json`. Lecture : **`AIDE_A_UN_POINT`**.
> 96 cellules IMPORTÉES de R0/R1 (jamais re-mesurées), 48 cellules neuves.

## La question

[[EDR-TD-STEP-PILOT-R0]] avait mesuré, à un seul pas (lr 4,0), que la trace d'éligibilité TD(λ=0,9) déplace la
composition différée `(q+key)%K` de +0,063 sur 12/12 seeds — et R1 avait ajouté qu'à lr 2,0 il ne se passait rien.
Un effet à UN point de fonctionnement n'est pas une pièce : R2 balaie la grille `lr {4,0 ; 2,0 ; 1,0}` ×
`λ {0 ; 0,5 ; 0,9 ; 0,99}`, avec à chaque pas le contrôle de CHEMIN `td0_d0` (même crédit, SANS délai) et les
références `lr = 0` (avec et sans délai). La barre n'est jamais « chance + marge » : c'est la référence lr = 0 du
MÊME dispositif, + 0,05.

## Ce que la grille rend

| bras (médiane, 12 seeds) | lr 4,0 | lr 2,0 |
|---|---|---|
| `lr0_reference` (délai, lr = 0) | 0,1625 — barre **0,2125** | idem |
| `lam0` (TD(0), délai) | 0,1898 — **1/12** au-dessus de la barre | 0,1867 — **1/12** |
| `lam05` (λ = 0,5) | 0,2078 — **3/12** | 0,1836 — **0/12** |
| `lam09` (λ = 0,9) | **0,2531 — 11/12** | 0,1898 — **1/12** |
| `lam099` (λ = 0,99) | **0,2563 — 11/12** | 0,1953 — **2/12** |
| `td0_d0` (contrôle de CHEMIN, sans délai) | 0,5031 — lisible **12/12** | 0,3203 — lisible **12/12** |

Comptes scellés, aux noms de la règle (`aide09@lr`, `aide05@lr`, `aide099@lr` = λ bat `lam0` de + 0,05, par
seed ; `meilleur_lambda@lr` = λ de médiane maximale) : à lr 4,0 `aide09@lr` **12/12**, `aide099@lr` **11/12**,
`aide05@lr` **0/12**, `meilleur_lambda@lr` = **`lam099`** ; à lr 2,0 les trois comptes valent **0/12** et
`meilleur_lambda@lr` vaut encore **`lam099`** — sur des médianes toutes sous la barre, donc sans porter de lecture. `lr 1,0` est **coupée** (voir Coût). Branche :
**`AIDE_A_UN_POINT`**.

## La lecture, et ce qu'elle ajoute à R0

R0 disait « la trace aide ». La grille dit plus, et c'est le résultat de cette passe : **à lr 4,0, la trace n'est
pas un bonus sur une tâche déjà apprise — elle est la condition pour qu'elle soit apprise du tout.** TD(0) à délai
(`lam0`) et λ = 0,5 ne franchissent PAS la barre de leur propre référence (1/12 et 3/12) ; λ = 0,9 et λ = 0,99 la
franchissent sur **11/12 seeds**. Le contraste `aide09` = 12/12 de R0 opposait deux bras dont un seul apprend ;
on peut désormais le dire dans ce sens-là.

⚠️ **Ce que le `0/12` de lr 2,0 ne dit PAS, et le dispositif l'établit lui-même.** À ce pas, AUCUN bras à délai ne
franchit sa barre : `lam0` 1/12, `lam05` 0/12, `lam09` 1/12, `lam099` 2/12. Le contraste y oppose donc **deux bras
qui n'apprennent ni l'un ni l'autre**, et « pas d'aide à lr 2,0 » se lit « rien n'apprend à délai à lr 2,0 », pas
« la trace n'aide pas à lr 2,0 ». La règle mesure `lisible@lr` sur la paire SANS DÉLAI (`td0_d0` contre
`lr0_reference_d0`) — qui passe bien, 12/12 — et l'aide sur la paire AVEC délai : les deux paires sont publiées
côte à côte ci-dessus précisément pour que ce glissement ne puisse pas se faire. **L'invariance au pas est donc
OUVERTE : ni tenue, ni réfutée.** (Cette tension a été nommée par la session `agagi-52` avant la lecture, sur les
chiffres de R1 — un « 0/12 » à lr 2,0 y opposait déjà deux bras sous leur barre ; sa clôture de P4.11 est amendée
de « invariance RÉFUTÉE » en « NON ÉTABLIE » pour la même raison.)

## Coût, coupes, et pourquoi leurs natures diffèrent

`_cout_s` **7 417 s** (2 h 04), `_cout_cpu_s` **6 977 s** — ici les deux horloges coïncident (processus unique,
pas de pool, contrairement à S2-002-PAIRED-R1 où le parent d'un pool rend un CPU proche de zéro).

Les DEUX coupes de cette expérience sont marquées `coupe=True` dans le JSON et n'ont pourtant pas la même nature —
c'est la chose à retenir de la passe :

* **lr 2,0 — coupée par CONTENTION, RÉCUPÉRÉE.** La première passe (2026-09-22) a mesuré son unité à **217,4 s**
  sur une machine chargée et a coupé deux lignes. La reprise déclarée (`--relever-coupe`, machine LIBRE vérifiée à
  0 bail / 0 processus, MÊME budget scellé, marge jamais relevée) a re-mesuré l'unité à **196,4 s** et n'a coupé
  qu'une ligne : les 48 cellules de lr 2,0 sont revenues. Chiffré : à 107 unités restantes, budget 240 min et marge
  1,5, il reste 255 min après la coupe de lr 1,0 avec l'unité contaminée (donc une SECONDE coupe) contre 231 min
  avec l'unité libre (donc une seule). **La contention a coûté exactement une ligne de grille, et elle ne l'a
  coûtée que parce que la projection était déjà à 6 % du seuil.**
* **lr 1,0 — coupée par STRUCTURE, elle tient.** Elle est re-coupée machine libre : la grille telle que scellée ne
  tient pas dans son budget. Ce n'est pas un accident de machine, c'est une sous-estimation au SCELLEMENT.

⚠️ **Et la prémisse de coût scellée est FAUSSE, mesurée ici.** La règle justifie sa projection par « cellules
uniformes : mêmes épisodes, mêmes agents — la queue est la contention machine, pas le seed ». Mesuré sur les
28 cellules chronométrées de la reprise : `lam05` médiane **161,9 s**, `lam099` **157,6 s**, `td0_d0` **56,2 s** —
le contrôle de chemin est **2,8× plus rapide** que les bras à trace (pas de tenue de trace, pas de délai). L'unité
est donc mesurée sur la PREMIÈRE cellule neuve, qui appartient à la famille lente, et appliquée à une grille
hétérogène : la projection sur-estime. Elle ne change pas la coupe de lr 1,0 (qui tient même à l'unité médiane
toutes familles, ~150 s), mais elle rend le cliquet de coût plus mordant qu'il ne devrait. C'est E8 appliqué au
modèle de coût — une prémisse posée en décor et jamais mesurée — et je l'avais scellée moi-même.

**Deux fenêtres de RAFALE déclarées** : la grille a tourné pendant deux de mes propres passes de commit (le hook
lance un `pytest` par mutation). Effet mesuré sur la même cellule à deux seeds voisins : `lam099` 163 s hors
rafale contre **968 s** pendant, `td0_d0` 27,6 s contre 340 s. Le temps MUR publié ci-dessus les inclut donc. La
DÉCISION du garde, elle, n'est pas touchée : depuis P2.78 elle est gouvernée par le temps CPU du processus, que la
charge extérieure ne gonfle pas — c'est la première fois que cette garde sert à quelque chose de mesurable.

## Contrôle d'arithmétique, rétro-appliqué le jour même

L'accuracy de ce banc est un COMPTE sur `n_grille` = 40 × 16 = **640** évaluations, et la marge scellée 0,05 vaut
EXACTEMENT 32 pas de grille : un critère à seuil peut basculer sur une ÉGALITÉ perdue en flottants (c'est ce qui
est arrivé à P4.12, rectifié le même jour). Le correctif a été **rétro-appliqué aux trois lectures** du pilote
(`_cmp_grille`, avec repli déclaré si la marge n'est pas commensurable) AVANT de lire R2 — E14 exige qu'une garde
écrite soit pointée sur l'existant, pas seulement sur la suite. Résultat : **aucun compte ne bouge**, ni les 17 de
R0/R1 (vérifiés par `agagi-52`) ni les 6 de R2 (vérifiés ici, ligne par ligne, avant/après). Le défaut était
LATENT et ne s'est pas réalisé — ce qui ne se saurait pas s'il n'avait pas été cherché.

## Suite

La pièce `eligibility_trace_credit` d'ADR-005 reste **à UN point de fonctionnement** : acquise là où elle rend la
tâche apprenable, non transportée ailleurs. Deux questions nommées et non répondues ici : (1) l'invariance au pas,
qui demande un pas où les bras à délai apprennent (lr 1,0 est coupée, lr 2,0 est sous la barre — le balayage utile
est donc vers le HAUT, pas vers le bas) ; (2) le passage in-world, qui se mesurera contre **TD seul** (−27,75 de
[[EDR-S2-CREDIT-ABLATION-2]]) et jamais contre le crédit complet, à épisodique coupé et à deux pas dont un haut.
