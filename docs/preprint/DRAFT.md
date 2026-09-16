---
status: draft-v0
date: 2026-09-16
figures: docs/preprint/figures/ (générées par tools/preprint/figures.py — aucune valeur en dur)
---

# Un dépôt de recherche qui se contredit lui-même : calibration des instruments, cliquets exécutables et pré-inscription scellée pour une biosphère artificielle

*Brouillon v0 — chaque chiffre porte sa source ; relire chaque chiffre contre sa commande de recompute (`PLAN.md`) le jour
de la soumission.*

## Résumé

Nous décrivons la méthode d'un programme empirique de longue durée sur une biosphère artificielle (agents à connectome
évolué, apprentissage intra-vie, mondes à survie) : 297 records typés dont 2 rétractés et 39 verdicts négatifs ou
indéterminés (`ls docs/EDR`, `grep "^verdict:"`). La plupart des résultats de ce programme sont négatifs, et nous montrons
que le risque dominant n'y est pas l'erreur de calcul mais **l'affirmation produite en l'absence de mesure** — avec une
direction : le négatif. Sur ~40 instruments examinés en fermant la dette de calibration, ~30 défauts réels, tous de la
même forme (donnée absente ou incomplète → affirmation négative de fond). Nous présentons trois mécanismes exécutables qui
rendent ces erreurs visibles et non reproductibles : (1) la calibration de chaque instrument sur une réponse connue
(no-op exact, prédiction, monotonie), tenue par un cliquet à baseline gelée — 234 instruments détectés, 226 calibrés ;
(2) un jeu de 17 cliquets sur le hook de commit, eux-mêmes soumis à un test de mutation en mémoire — 22/22 mutants tués,
4 défauts réels du premier tir ; (3) la pré-inscription scellée par hash avec lecture calibrée avant toute cellule et
familles de contrôles déclarées — 58 règles. Cinq cas illustrent ce que ces mécanismes ont attrapé, dont deux qui ont
renversé des conclusions publiées : un « mur » qui était un pas d'apprentissage, et une « létalité » qui était
`max(0.0, nan)`.

## 1. Contexte

AGAGI est un dépôt de recherche empirique (2026) : des agents dont le connectome est évolué et qui apprennent intra-vie,
placés dans des mondes à survie, pour tester si un monde peut *exiger* une capacité cognitive. Le programme a produit
297 records (EDR) reliés en graphe, 58 règles pré-inscrites, ~2 600 tests. Sa conclusion scientifique principale est
négative — la demande cognitive du monde tel que construit est conçue, pas exigée (ADR-004) — et c'est précisément ce
qui rend la MÉTHODE intéressante : quand la plupart des résultats sont négatifs, un négatif fabriqué ressemble à tous
les autres.

## 2. Trois mécanismes

### 2.1 Calibration à réponse connue

Un *instrument* est toute fonction qui produit une affirmation scientifique (verdict, ratio, survie, taux). Chaque
instrument doit avoir au moins un cas où la réponse est connue d'avance : un **no-op exact** (spécificité — l'instrument
rend zéro effet quand rien n'a changé), une **prédiction** (linéarité en une dose imposée), une **monotonie** (direction).
Le cliquet `check_instrument_calibration.py` détecte les instruments par motif lexical et refuse tout NOUVEL instrument
sans déclaration ; sa baseline gelée ne peut que décroître (Figure F1 : 75 gelés le 2026-07-21, 0 le 2026-09-01, 2 le
2026-09-16). Le cliquet est faillible sur cinq axes mesurés (motif, périmètre, identification des collisions de noms,
verbes, profondeur d'indentation) ; chaque élargissement a révélé de la dette réelle.

Deux techniques rendent la calibration presque gratuite : la **garde en tête de fonction**, testée sur *où* elle est
posée (un refus doit être instantané, avant toute construction de monde) ; l'**injection** pour les orchestrateurs (une
mesure factice à dose connue teste la couche qui transforme des mesures en affirmation, à coût nul).

### 2.2 Cliquets à baseline gelée, et le cliquet des cliquets

Dix-sept gardes sont branchées sur le hook pre-commit (graphe de records, calibration, pré-inscription appliquée,
contre-exemples des gardes, fraîcheur du backlog par clause déclarée, comptes de synthèse recomputés, épinglage du
substrat, séparation des barres, recensement des tests, chemins de données, familles de contrôles, défauts fabriqués,
mutation des portes, anéantissement d'un fichier, chevauchement entrée/sortie des génomes). La règle : un cliquet doit
pouvoir échouer, et se calibre comme un instrument — son contre-exemple gelé s'écrit dans la même passe. Le test de
mutation (`check_gate_mutation.py`) casse chaque porte d'une ligne EN MÉMOIRE et exige qu'un témoin rougisse ; un
contrôle intact précède chaque mutation, sans quoi des témoins déjà rouges « tueraient » tout mutant. Premier tir : quatre
défauts réels — trois verdicts de porte sans contre-exemple, un test qui punissait son propre correctif (Figure F6).

### 2.3 Pré-inscription scellée à lecture calibrée

Toute règle de lecture est scellée par hash AVANT la première cellule ; elle nomme ses branches dans un ordre imposé
(`INCOMPLET` d'abord, `AUTRE` en dernier — jamais une inférence), ses grandeurs (qui doivent apparaître dans le record,
porte 3), sa famille de contrôles (porte 11 : à seuil unique, une famille de 24 cellules donnait 0,216 de fausse
alarme sur un harnais parfait), et une clause E19 (un second pas d'apprentissage sur tout nul). La fonction de lecture
est calibrée sur des bases factices couvrant chaque branche avant de voir une donnée. Un run coûteux passe un pré-vol
(les deux issues possibles ? la grandeur mesurée est-elle celle qui agit ? unité de réplication ? raisonne-t-on au lieu
de mesurer ?) et un coût projeté sur une unité mesurée.

## 3. Le registre des erreurs comme objet

Vingt-huit classes (E1–E28), chacune avec ses occurrences datées et un statut de garde ; 23 sont `exécutables` et
nomment leur contre-exemple (Figure F2). Une erreur qui repasse deux fois en `documenté` est promue. Les classes les
plus fréquentes ne sont pas des erreurs de calcul : contrôle qui ne peut pas échouer (E1), vérification vide (E4),
inférence substituée à la mesure (E8), règle documentée sans application exécutable (E10, la plus récidiviste), garde
jamais rétro-appliquée (E14).

## 4. Cinq cas

**4.1 Le biais a une direction.** En fermant la dette de calibration (2026-09-01) : ~30 défauts sur ~40 instruments,
direction constante — `PAS DE RUNG`, `AUTEL MORT`, `N_EMERGE_PAS` produits par une entrée vide, un `nan` détecté puis
avalé, un `zip`/`min`/`[-1]` qui tronque. Un instrument non calibré ne se contente pas d'échouer : il PRODUIT un
résultat (l'aliasing d'EDR-WARM-007 a généré dose-réponse, corrélations et contrôle négatif cohérents pendant une passe
entière).

**4.2 Un nul de capacité qui était un réglage (E19).** `EDR-RETAIN-COMPOSE-LR` : à protocole identique, seul `lr`
change — 0,02 → 0,173 (verdict `RETENTION`, rétracté), 0,002 → 0,923, 0/144 de recouvrement par seed (Figure F3).
Cause : n agents n'est pas un minibatch (batch effectif 1) et les contrôles étaient calibrés sur le régime facile. La
même classe a été rejouée deux fois : le « mur D = 2 » (`EDR-LOCK-002` : 0,178 → 0,784 en changeant le pas) et le
pas publié de l'apprenant legacy (`EDR-CALIB-LEGACY-LEARNER` : 0,04 → 0,197 ; 0,001 → 0,449, 12/12).

**4.3 Une dose non comptée fabrique un nul.** `EDR-CALIB-LEARNER` : trois records affirmaient « le crédit in-world
n'apprend pas à froid » sur des agents morts à 7-9 ticks — quelques dizaines de mises à jour, jamais comptées. À dose non
bornée par la mort (cohorte immortelle), 12/12 seeds apprennent (+0,156 sur la référence lr = 0 appariée ; Figure F4).
Garde : la dose de tout apprenant est publiée à côté de tout nul.

**4.4 L'instrument tue le sujet (E28).** Le World Model par agent (SGD brut sur l'observation) diverge ; son erreur
devient `nan`, la surprise `nan`, le coût cérébral `nan`, et le monde fait `energy = max(0.0, energy − nan)` — qui vaut
0 en Python. Une mort par tick : 18 265 résurrections par seed, lues comme « les apprenants meurent 100× plus ». Garder
les poids finis ne changeait rien (ratio 1,00) ; la garde à la source ramène à 139 (Figure F5). Le record a reçu un
bandeau correctif le jour même ; l'arc évolutif n'était pas touché (0 reset à son régime).

**4.5 Une partie des sorties est l'entrée (E24).** Le champion de production déclare 64 entrées + 126 sorties dans
172 nœuds : 18 logits d'action SONT l'observation, sans traverser un poids. Annuler `W[:num_inputs]` ne l'aveugle pas.
La garde chiffre le chevauchement sur tout sujet, et une porte balaie le dépôt de génomes (378 sujets, 0,5 s).

## 5. Coût et rendement

Depuis le 2026-09-01 : 26 commits de science pour 78 de méthode ; 7 revues adversariales à sondes propres, 7 erreurs
réelles ; suite complète de 2 589 tests en 36 min (à charge non contrôlée). Le débit méthode/science est le prix ; le
rendement est que deux conclusions publiées ont été renversées par des mécanismes, pas par la chance.

## 6. Limites

Un seul cas d'étude, écrit par ceux qui l'ont commis. Les cliquets sont lexicaux et faillibles (cinq axes mesurés). Un
cliquet livré sans qu'un run le demande est un coût (la porte 17 en est un exemple avoué, ADR-004 (iii)). Rien ici ne
dit que la méthode généralise ; elle dit ce qu'elle a attrapé et ce qu'elle a coûté.

## 7. Suite

Le dépôt se réoriente en harnais (spec 2026-09-16) : tâches et apprenants sous contrat, demande générée par un LLM sous
sandbox et revue humaine, mesure à trois conditions (ablation hors bande de bruit, acquisition au-dessus de la référence
lr = 0, nécessité d'une pièce). Les mécanismes décrits ici en sont les gardes.

---
*Annexe prévue : le registre des erreurs (28 classes, occurrences datées, gardes) ; les 58 règles scellées ; le hook.*
