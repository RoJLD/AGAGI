---
id: EDR-S2-002-PAIRED-R1
type: EDR
title: "À bande RNG APPARIÉE le no-op de l'instrument de perception est EXACT (1,0000 sur 15/15 cellules, contre ±6-8 % à bande nue) : la carte d'ablation-perception du champion HoF BOUGE sur 2 des 4 mondes distincts — soup et agricultural passent DECOY → INCONCLUSIVE_DEGENERATE parce que leur bras INTACT est au plancher ; la duplication `industrial` ≡ `stoneage`, déjà consignée, est confirmée BIT-POUR-BIT et sert de contrôle de déterminisme"
status: active
verdict: CARTE_MODIFIEE
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER, REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-S2-002, EDR-S2-013, EDR-S2-BLIND-CHAMPION-TER]
---

> **Règle scellée AVANT toute cellule** : `S2-002-PAIRED-R1` (`docs/preregistrations/S2-002-PAIRED-R1.json`), lue par
> `tools/evo_runs/s2_002_paired.py`, résultats `results/s2_002_paired_r1.json`. Lecture : **`CARTE_MODIFIEE`**.

## Ce qui est mesuré, et pourquoi il fallait le re-mesurer

[[EDR-S2-002]] et [[EDR-S2-013]] portent la carte « le monde exige-t-il la PERCEPTION ? » : ablation-perception
**within-subject** du champion HoF sur 5 clés de monde, verdict `PERCEPTION_DECOY` partout, `within_ratio` ≈ 1,00.
Le 2026-09-08, le no-op EXACT de l'instrument (aucune observation changée) a rendu **1,058** et **0,922** : un
plancher de bruit de **±6-8 %** produit par la désynchronisation de la bande RNG — l'ablation consomme des tirages
du flux global. Tous les `within` publiés étaient DEDANS. « DECOY » ne pouvait donc signifier que « rien au-dessus
de 8 % », et la carte n'était pas lue, elle était **indistinguable de zéro**.

Cette passe rejoue la carte à **bande APPARIÉE** (P2.41 b) : le bras de référence est `perception_null_variant`,
qui consomme EXACTEMENT les mêmes tirages que le bras ablaté sans changer une seule observation. Régime GRAVE
scellé : 12 agents, 200 ticks, K = 12 ères appariées, 3 seeds de monde (2026 publié, 3026, 3027 neufs), sujet =
champion HoF, contrôle no-op sur chaque cellule. 60 cellules de mesure (5 mondes × 3 seeds × 4 conditions).

## Résultat 1 — le contrôle : le plancher de bruit tombe à ZÉRO

**`noop` = 1,0000 EXACT sur 15/15 cellules** (`noop_exact` = **3/3** sur chacun des cinq mondes), tous mondes et tous seeds confondus. Ce n'est pas « réduit » (le
`-bis` de P2.41 donnait 1,012) : c'est **exact**. Le bruit de ±6-8 % qui rendait la carte illisible était
entièrement imputable à la bande RNG non appariée, et l'appariement le supprime — pas le diminue. Tout écart
mesuré ci-dessous est donc réel au chiffre près, et non plus « dans la bande ».

## Résultat 2 — la carte BOUGE sur deux mondes

| monde | `within_median` (3 seeds) | `noop_exact` | plancher | lecture appariée | post-hoc (hors verdict) |
|---|---|---|---|---|---|
| soup | **1,073** | 3/3 | 32,00 | **MODIFIÉ → INCONCLUSIVE_DEGENERATE** | survit MOINS dérangé |
| stoneage | 0,937 | 3/3 | 24,00 | INCHANGÉ (`PERCEPTION_DECOY`) | survit PLUS dérangé |
| agricultural | **0,969** | 3/3 | 25,25 | **MODIFIÉ → INCONCLUSIVE_DEGENERATE** | dans la marge |
| industrial | 0,937 | 3/3 | 24,00 | INCHANGÉ (`PERCEPTION_DECOY`) | survit PLUS dérangé |
| famine | 1,030 | 3/3 | 21,75 | INCHANGÉ (`PERCEPTION_DECOY`) | dans la marge |

Aucun monde en `HARNAIS`, aucun `MIXTE`. Le mouvement n'est pas un changement de signe : il vient du **plancher**.
Sur soup et agricultural, le bras INTACT est au niveau ou en dessous du plancher no-perception du monde
(soup : intact 32,00 / 29,25 / 28,50 contre un plancher à 32,00 ; agricultural : 28,00 / 23,25 / 22,75 contre
25,25) — l'instrument refuse alors de conclure, et il a raison : **on ne lit pas un ratio entre deux bras qui sont
tous deux au plancher** (classe E3, et c'est exactement la faute qu'[[EDR-WARM-002]] avait payée). Ce que la carte
gagne ici n'est pas un verdict de plus, c'est un verdict de MOINS, mais honnête.

Corroboration de méthode, publiée sans être un verdict : le `between_ratio` des mêmes cellules vaut **3,57 à 5,42**
quand le `within` vaut ~1,00. Le contraste between-subject (« un survivant compétent existe ») continue donc de
crier `DEMANDED` là où le within ne voit rien — le faux positif que [[REF-DEMAND-MARKER]] existe pour interdire,
reproduit ici sur 15 cellules à bruit nul.

## Résultat 3 — la duplication `industrial` ≡ `stoneage`, cette fois BIT-POUR-BIT

⚠️ **Ce n'est PAS une découverte, et le dire autrement serait faux** : [[EDR-S2-002]] porte depuis
[[EDR-S2-012]] un bandeau « COMPTE DES MONDES CORRIGÉ » qui énonce exactement cela (« `IndustrialWorld` est
`class IndustrialWorld(Biosphere3D)` — clone, compteur `pollution` jamais lu — les lignes stoneage et industrial
du tableau, identiques au chiffre près, sont la même simulation comptée deux fois »), et [[EDR-S2-013]] le répète
dans ses réserves de lecture (« les 4 mondes au-dessus en valent au plus 3 indépendants »). La carte publiée
n'est donc pas sur-comptée : elle porte sa correction. *(Cette section a failli affirmer le contraire : j'avais
cherché `industrial` dans le code et l'outillage, pas dans les records que j'allais bander — une absence de
correspondance n'est pas une preuve d'absence tant que le motif n'a pas été validé sur un cas positif connu.)*

Ce que cette passe AJOUTE est une gradation de la preuve : les records disaient « identiques au chiffre près »
sur une ligne de tableau ; ici l'identité est **bit-pour-bit sur 3 seeds et sur TOUS les champs mesurés** —
`within_ratio`, `between_ratio`, `noop`, `intact_median`, `floor`, `verdict`, `n` — le seul champ qui diffère
étant `t_s`, le temps mur. Confirmé dans le code : `src/worlds/world_3_industrial.py` fait 18 lignes, sous-classe
`Biosphere3D`, incrémente `self.pollution` tous les 10 ticks sans qu'aucun consommateur hors du fichier ne la
lise, et son `step()` appelle `super().step()`.

Emploi : cette ligne est publiée comme **contrôle de déterminisme** du harnais complet — même pipeline, clé de
monde différente, résultats bit-identiques, ce qui est un contrôle positif gratuit de l'appariement et de la
reproductibilité de bout en bout. Elle ne compte pas comme réplication, et les « 5 mondes » de cette table valent
**4 dynamiques distinctes**, comme déjà écrit ailleurs.

## Ce que ce record NE dit pas

Il ne rétracte aucun verdict de [[EDR-S2-002]] ni de [[EDR-S2-013]] : sur les mondes où la lecture est INCHANGÉE,
le `DECOY` tient, et il tient désormais à bruit NUL au lieu de ±8 %. Il ne dit pas non plus que le monde n'exige
pas la perception : il dit que sur deux des quatre mondes distincts, le dispositif actuel ne peut pas répondre
parce que le champion y meurt au plancher. Le régime GRAVE (12 agents, 200 ticks) est ce qui met soup et
agricultural au plancher ; un régime où le champion vit nettement au-dessus du plancher est le prérequis de toute
re-lecture de ces deux mondes.

## Coût

Mur **3 216 s** (54 min) pour 15 cellules, CPU du processus parent 604 s — l'écart est attendu et documenté
(`tools/cost_guard.py`, limite (a) : le parent d'un pool a un CPU proche de zéro, le temps mur est la bonne
horloge ici). Machine mesurée LIBRE au départ (0 bail, 0 processus python du projet).
