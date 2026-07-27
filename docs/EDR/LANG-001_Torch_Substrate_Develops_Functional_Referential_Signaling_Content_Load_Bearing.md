---
id: LANG-001
type: EDR
title: "Le substrat torch DÉVELOPPE une signalisation référentielle FONCTIONNELLE (Arc 4 langage, roadmap #1) — proxy de capacité en amont de l'in-world 087. Jeu de Lewis 2-pops (sender→signal→receiver) sous crédit épisodique : FIABLE 0.77 vs chance 0.17 (K=6, 3 seeds, 4.6× chance, tous seeds) → signalisation ÉMERGE ; BROUILLÉ (signal aléatoire) = 0.17 chance exacte → CONTENU PORTEUR (le succès dépend du signal encodant la cible = FIABLE vs BROUILLÉ synthétique de 087). Sweep K : quasi-parfait à K=4 (0.96), dégradation gracieuse (K=8 0.57) mais toujours >>chance et content-dépendant. Dé-risque l'axe langage in-world"
status: accepted
gate: null
verdict: FUNCTIONAL_REFERENTIAL_SIGNALING_WITH_LOAD_BEARING_CONTENT
---

# LANG-001 : le substrat torch développe une signalisation référentielle fonctionnelle (Arc 4)

## Contexte

Roadmap SCIENCE #1 : « clore le bénéfice fonctionnel du langage (Arc 4) — re-test 087 (FIABLE vs BROUILLÉ)
+ power ». Le re-test 087 est IN-WORLD (biosphère). Ici : proxy synthétique de CAPACITÉ en amont (même
méthode que les proxies H-unif torch : teste hors biosphère, sans toucher le code monde partagé). Deux
questions : (1) le substrat torch développe-t-il une signalisation référentielle ? (2) le CONTENU
du signal paie-t-il (analogue synthétique de FIABLE vs BROUILLÉ) ? Nouvel axe -> ID préfixé `LANG-` pour
éviter la collision numérique (space EDR-NNN contesté par sessions //).

## Méthode

Jeu de Lewis référentiel, 2 populations torch APPARIÉES (`tools/referential_game_probe.py`) : SENDER voit
une cible (one-hot parmi K) → émet un SIGNAL (parmi V=8) ; RECEIVER voit le SIGNAL (pas la cible) →
devine le référent (parmi K) ; récompense partagée +1 si devine==cible. Crédit ÉPISODIQUE (`learn_episode`,
EDR-158), sans gate (politiques standard). Éval greedy FIABLE (vrai signal) vs BROUILLÉ (signal
ALÉATOIRE décorrélé de la cible). 3 seeds × 1500 ép (K=6) + sweep K∈{4,6,8}.

## Constat

**Headline (K=6, 3 seeds, chance=0.167) :** FIABLE **0.767** (per-seed [0.73, 0.78, 0.77]) vs BROUILLÉ
**0.167** (chance exacte). `VERDICT = FUNCTIONAL_REFERENTIAL_SIGNALING_WITH_LOAD_BEARING_CONTENT`.

**Sweep K (2 seeds) — capacité :**

| K | chance | FIABLE | BROUILLÉ | FIABLE/chance |
|---|---|---|---|---|
| 4 | 0.25 | 0.956 | 0.249 | 3.8× |
| 6 | 0.17 | 0.754 | 0.172 | 4.5× |
| 8 | 0.12 | 0.571 | 0.117 | 4.6× |

## Lecture

- **La signalisation référentielle ÉMERGE, robustement** : FIABLE 0.77 = 4.6× la chance à K=6, sur les 3
  seeds (0.73-0.78) — pas de dépendance de graine. Le substrat torch, sous crédit épisodique, développe un
  protocole sender→receiver fonctionnel.
- **Le CONTENU est ENTIÈREMENT porteur** : brouiller le signal (le remplacer par un aléatoire décorrélé de
  la cible) ramène l'accuracy à la chance EXACTE (0.167, 0.249, 0.117) pour tous les K → le succès DÉPEND
  du signal encodant la cible, pas d'un biais du receiver. C'est l'analogue synthétique du FIABLE vs
  BROUILLÉ d'EDR-087 : **le contenu référentiel paie**.
- **Capacité graduée** : quasi-parfait à faible charge (K=4 : 0.96 ≈ protocole complet, V≥K le permet),
  dégradation GRACIEUSE quand la charge monte (K=8 : 0.57) mais le ratio sur chance MONTE (3.8→4.6×) →
  le protocole porte une quantité ~fixe d'information ; plus de référents la répartissent plus finement
  (limite de capacité du substrat, pas un échec).

## Conséquences

- **Dé-risque l'axe 4 langage in-world** : la CAPACITÉ de signalisation référentielle fonctionnelle est
  présente dans le substrat torch (sous crédit épisodique) ET le contenu fiable paie — les prérequis de
  benefit-of-language sont réunis. Le re-test in-world 087 (FIABLE vs BROUILLÉ) n'a donc pas à prouver la
  capacité, seulement son BÉNÉFICE de survie in-world. Parallèle direct aux proxies H-unif (capacité
  d'abord, in-world ensuite).
- **Recette langage torch** : crédit épisodique (`learn_episode`) suffit pour un jeu de Lewis 2-pops ;
  pas de gate requis (le receiver conditionne sa politique sur le signal nativement). Le gate multi-cible
  (165) pourrait aider à K élevé (routage conditionnel sur le symbole) — non testé, backlog.
- Relié : `REF-LTC -A_ADOPTER_POUR-> LANG-001` (le substrat = LTC torch). Recoupe la SOTA `langage→EGG`
  (Emergence of Language in Games) de [[sota-gap-substrate]].

## Caveats

1. FIABLE < 1.0 à K≥6 (protocole imparfait) : convergence incomplète à 1500 ép et/ou limite de capacité
   du substrat 172-nœuds ; plus d'épisodes / substrat plus riche pousseraient plus haut (non sweepé).
2. Populations APPARIÉES fixes (sender_i↔receiver_i) : pas de rotation de partenaires (qui teste la
   COMPOSITIONNALITÉ / généralisation d'un protocole partagé) ; bornage — c'est un test de capacité de
   coordination, pas de compositionnalité.
3. 2-3 seeds ; le ROBUSTE = FIABLE≫chance sur tous seeds + BROUILLÉ=chance exacte pour tous K, pas les
   décimales. Proxy synthétique ; le vrai bénéfice = in-world (087).
4. Pas de coût de signalisation ni de pression de sélection sur l'écoute (EDR-083) : le jeu récompense
   directement la coordination ; in-world le langage doit ÉMERGER sous pression de survie (plus dur).
