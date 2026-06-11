# Fil conducteur — ce qu'AGIseed a appris (EDR 010→049)

> **But de ce document** : le *récit* de notre compréhension, synthétisé. Les EDR sont les preuves
> granulaires ; ceci est l'histoire qui les relie. À relire avant toute nouvelle vague.

## La thèse (le fil rouge)

> **« Le bon n'est pas dit mais trouvé — et il n'est trouvé que si le monde l'EXIGE. »**

Tout le projet teste cette idée (EDR 010/012). On n'*ajoute* pas l'intelligence : on construit un
monde dont la **demande** sélectionne l'intelligence. Chaque vague est une mise à l'épreuve, de plus
en plus dure, de cette thèse — jusqu'à la prouver (047) puis la raffiner (048/049).

---

## Acte I — Faire émerger une chaîne moyens→fins (EDR 010→030)

| EDR | Acquis |
|---|---|
| 010 | **Audit réel vs théâtre** : distinguer ce qui émerge vraiment de ce qu'on a scripté. |
| 011/012 | **World Model (curiosité)** + **monde exigeant** : la rareté force l'apprentissage. |
| 018/021 | **Axe craft** : rock+stick→spear→Mammouth (la chaîne d'outils). |
| 020/023 | **Vrai Actor-Critic TD** (on remplace le hebbien rustre par du RL avec crédit d'action). |
| 022/028 | **Coup critique** puis **récompense de groupe** : la coopération rend la chaîne robuste *sans* dépendre du crit chanceux. |
| 027/029/030 | Chaîne **intégrée 2D**, **dominante**, **auto-suffisante** (scaffolds sevrés). |

**Leçon I** : une chaîne sociale complexe (chasser l'apex en pack) *émerge* sous une demande de
rareté + coopération. La thèse tient à petite échelle.

## Acte II — Honnêteté + l'infrastructure de la « graine » (EDR 031→036)

| EDR | Acquis |
|---|---|
| 031 | **Câbler les gènes fantômes** (thresholds, W_router) au lieu de les tuer — fidèle à l'émergence. |
| 032/034 | **Ablation** + **ontologie KuzuDB** (Hypothesis/Fact) + graphe projet. |
| 033 | **Unifier le moteur des mondes** (l'axe Monde). |
| 035 | **Sandbox sécurisée** (gate AST + subprocess isolé) — *la cage*. |
| 036 | **Superviseur réflexif** (tendance multi-ères) — *les yeux* + le seam LLM. |

**Leçon II** : avant d'ouvrir les mains de la graine (auto-réécriture), on bâtit la **cage**, les
**yeux** et la **mémoire**. Sécurité *avant* puissance.

## Acte III — L'enquête du langage (EDR 037→047) — le cœur

Le récit le plus serré du projet. Une frontière (le langage référentiel) qui résiste, puis cède.

| EDR | Intervention | Le token… |
|---|---|---|
| 037 | activer le canal de signal | **bruit** (impasse) |
| 038/040 | **portée** du signal | aide — mais via la **présence** |
| 042/043 | brouillage (sens détruit, présence gardée) | **présence confirmée, PAS le contenu** (MI≈0) |
| 045 | pression référentielle **scriptée** | **échec** (gameable) |
| 044 | architecture de la boucle RSI (#8) **câblée, non armée** | — |
| 046 | arming dirigé **NAS** + **leçon unifiée** | (voir Acte IV) |
| **047** | **demande réelle (monde de Lewis)** | **RÉFÉRENTIEL — émerge** (MI 0.0006→0.033, ×55) |

**Leçon III (le sommet)** : le langage ne s'*ajoute* pas (037/045 échouent). Il **émerge** quand le
monde le rend *nécessaire* — le monde de Lewis (Mammouth nourricier vs Leurre piège,
indistinguables à distance → il *faut* le signal). **La thèse est prouvée au bord le plus dur.**

## Acte IV — La leçon unifiée + la recette raffinée (EDR 046, 048→049)

| EDR | Test | Résultat |
|---|---|---|
| 046 | forcer la croissance NAS (monde de base) | architecture **figée à 172** — le monde n'exige pas plus de cerveau |
| 048 | renforcer le langage (3 référents) | **pas de lexique** — silence (altruisme du signal) |
| 049 | NAS dans le monde exigeant (Lewis-3) | architecture **toujours figée** (mauvaise demande + collapse) |
| 050 | incitation du locuteur (réciprocité) | **pire** — crédit temporel (prime au kill, pas au signal) |

**Leçon IV (la recette)** : « la demande crée la capacité » est **vraie mais exigeante**. La demande
doit :
1. **CIBLER** la capacité précise (référentielle→langage ; mémorielle/computationnelle→architecture) ;
2. être **SURVIVABLE** (sinon pas de sélection).
Un « monde plus dur » générique ne suffit pas. **Concevoir la bonne demande est *le* travail** — et
c'est le rôle recadré du **#8** (proposer+itérer des demandes ciblées).

## Acte V — Armer l'itérateur (#8), et son vrai goulot (EDR 050→051)

Les designs manuels ratent (045/048/049/050 : **4 tentatives, 3+ échecs**, chacune par un défaut
subtil *trouvé par la mesure*). Ce pattern *est* l'argument du #8 : un générateur qui itère sur des
centaines de designs en mesurant chacun battrait la conception à la main.

| EDR | Pas | Acquis |
|---|---|---|
| 051 | étendre le #8 au périmètre **`world_demand`** + boucle propose→mesure→classe | **construite, testée** (rsi_loop) ; la démo classe les demandes |
| 052 | **harnais d'évaluation puissant** (multi-seeds + signification) | construit, testé ; **recalibre nos verdicts à 1 run** |

**Leçon V (le goulot, puis la recalibration)** : la boucle #8 marche mécaniquement, mais la démo
(12 ères) a **classé par le bruit**. Le harnais (052, 3 seeds × 18 ères) tranche enfin… en refusant de
conclure : **les 3 demandes ne se séparent pas** (t=0.24). Pire — il révèle que **nos verdicts à 1 run
étaient non fiables** : `lewis_2ref` (047) fait 0.019 / **0.002** / 0.017 selon le seed (les 0.033 de
047 étaient un *tirage favorable* ; vraie moyenne ~0.013 ± 0.009), et `referential_pressure` (045
« échec ») a un seed à 0.039. **Le succès 047 ET l'échec 045 étaient en partie du bruit.** Un itérateur
ne vaut QUE ce que vaut sa mesure — et une mesure fiable, à cet effet (~0.01 MI, σ≈0.01), coûte **≫ 3
seeds**. La discipline de mesure (039/041) devient une **contrainte d'architecture chiffrée**.

---

## Où on en est (au 2026-06-11)

- ✅ Chaîne moyens→fins émergente, robuste, dominante, auto-suffisante.
- ✅ Infrastructure RSI (#8) **câblée mais NON armée** : cage (035), yeux (036), mémoire (032/034),
  juge (041), boucle (044), **périmètre `world_demand` + boucle propose→mesure→classe (051)**. Le
  seam LLM attend (a) un harnais d'évaluation puissant, (b) un conteneur jetable.
- 🎲 Langage : émergence sous demande **réelle mais STOCHASTIQUE** (053, 8 seeds) — une *loterie* qui
  se cristallise dans ~25 % des runs (2/8 forts à MI 0.03-0.05, 6/8 au bruit). La thèse tient
  *probabilistiquement* ; 047 (0.033) était un tirage chanceux mais pas un artefact. **Brisure de
  symétrie** (coordonner une convention).
- ⛔ Fiabiliser (054-057) : **CLOS sur un négatif propre.** Align-énergie (055) semblait prometteur
  (33→50 %) mais à **40 seeds (057) = NUL** (28 % vs 32 %, le n=6 était du bruit) ; align-fitness (056)
  backfire. **6 mécanismes à la main (045-057), zéro qui fiabilise.** La loterie ~25-32 % tient. Le
  harnais **vindiqué** (il a refusé de nous laisser croire à 055). → l'approche manuelle du langage est
  *exhaustée* ; pivot **forcé** vers NAS/#8 ; l'argument du #8 devient un *résultat empirique*.
- ✅ Harnais d'évaluation puissant **construit + utilisé** (052/053) — verdicts *avec confiance*.
- 🧠 NAS (058) : même une **demande de mémoire** (apex transitoire) ne grandit pas l'archi (172/172,
  comme 046/049). Vrai obstacle découvert : `add_node` est *neutre* (split NEAT), mais le HoF
  élitiste strict **bat l'innovation immature** avant qu'elle mûrisse → croissance jamais retenue.
- 🔓 #8 (059) : `LLMProposer` rendu **armable** (LLM injecté comme `llm_fn`, gardé, testé au mock).
  Armable en 1 ligne ; reste **désarmé** (besoin conteneur + harnais en `measure_fn`).

## ⚡ L'unification (le mur commun des deux frontières — EDR 054 ⊕ 058 ⊕ 060)

> **Une sélection élitiste stricte par une fitness établie TUE la nouveauté avant maturité.** Langage
> (054 : convention faible, sélection aveugle) et architecture (058 : nœud immature, battu par les
> rodés) échouent pour la **même** raison : *rien ne protège l'immature*. Défaut de **dynamique de
> sélection**, pas de demande. Lever : **protéger la nouveauté** (spéciation NEAT).
>
> **Testé (060)** : la spéciation-par-taille **protège bien** (des archis 173-174 *persistent* enfin,
> vs 172 verrouillé) — mais **ne suffit pas** seule.
>
> **Le grand raffinement (062-063) — les remèdes DIVERGENT :**
> - **NAS (062)** : même avec 3 bits + 36 ères + spéciation, l'archi ne prolifère pas. **Le
>   foraging ne sature fondamentalement pas 172 nœuds** (tâche réactive, mémoire peu profonde).
>   Protection *résolue* (spéciation) ; demande *non réparable dans ce substrat* → il faut une
>   **tâche-mémoire dédiée** (hors foraging).
> - **Langage (063)** : porter la spéciation par token **BAISSE** l'émergence (33→17 %, d=−0.48).
>   **NAS doit EXPLORER (diversité protégée = bien) ; langage doit CONVERGER (diversité protégée =
>   mal).** Dynamiques **OPPOSÉES**. La spéciation est l'outil du NAS, *pas* du langage (qui relève de
>   la **pression de convergence / sélection de groupe**).
>
> **Bilan** : l'unification d'EDR 058 tient au *diagnostic* (la sélection stricte tue la nouveauté)
> mais les *remèdes* sont frontière-spécifiques.
>
> **NAS — CLOS (064)** : sur un banc cognitif dédié (rappel de K bits, hors foraging), la croissance
> *marche* (après correction d'un bug de driver) mais est du **BLOAT NEUTRE** : le trivial (K1, acc
> 1.00) gonfle *plus* (35 nœuds) que le dur (K6, 26 nœuds) — la croissance suit le *mou*, pas la
> demande ; et plus de capacité **n'aide pas** (K6 acc 0.78 à 19 ou 26 nœuds). **La croissance UTILE
> d'architecture n'a pas lieu** dans AGIseed — goulot mécanique : `add_node` neutre/disruptif +
> recherche par *mutation seule* incapable d'exploiter la capacité. Vrai NAS = opérateur de croissance
> *utile* + apprentissage par *gradient* (changement fondamental ; candidat #8).

## Le #8 — ARMÉ, LIVE, SÛR (EDR 059+061+065)

Cage (035) · yeux (036) · ontologie (032/034) · catalogue `world_demand` (051) · proposer LLM
injectable (059) · mesure PUISSANTE (harnais en `measure_fn`, 061) · **frontière de sûreté**
(`sanitize_demand_params`, allow-list bornée) · **connecteur LLM local** (`local_llm_fn`, LM Studio/
Ollama).

> **ARMÉ POUR DE VRAI (065)** : Gemma-12B local dans la boucle — il lit les résultats mesurés,
> *raisonne* sur les échecs, propose des demandes NEUVES, le harnais les mesure (multi-seed), ça
> itère. **La boucle d'auto-amélioration est vivante.** SÛR sans conteneur car `world_demand` = params
> *bornés* (aucun code exécuté) + LLM *local* (aucun appel externe) + *sanitizer* strict ; le conteneur
> (EDR 044) ne reste requis que pour le kind `activation`/code.
>
> **Espace d'action élargi (066)** : le #8 est aussi armé sur le kind **`activation`** (le LLM propose
> des fonctions d'activation = CODE, validé par la sandbox EDR 035, exécuté). Il améliore donc l'**agent**,
> pas que le monde. qwen-coder a proposé 6 activations, toutes sandbox-validées ; **aucune ne bat tanh**
> (0.799) — et c'est la *bonne* réponse (tanh est quasi-optimal pour la mémoire récurrente). Le #8 ne se
> ment pas.
>
> **Limite honnête (065+066)** : le #8 *fonctionne et est sûr* (monde + agent), mais n'a pas trouvé de
> *breakthrough* — non par défaut de mécanisme, mais parce que ses frontières cibles sont **barren**
> (langage, 057) ou **déjà optimales** (tanh, 066). Il lui faut un espace où l'amélioration EXISTE.
> **Cette frontière, c'est le GRADIENT (BPTT)** : il donnerait un substrat où l'architecture/l'activation
> *paient* (débloquant le NAS, 064) — le gros morceau de fond restant.

## Les prochaines cibles (nettes, fondées sur la mesure)

1. ✅ **Harnais d'évaluation PUISSANT** (052) + **047 re-confirmé sous puissance** (053) — *faits*.
2. **Fiabiliser l'émergence** (054) : **aligner la sélection sur la convention** — un terme de fitness
   référentiel (faible, annealé), car `life_score` est aveugle au langage. Métrique = **taux
   d'émergence** *via le harnais* (multi-seed), pas la moyenne d'un run.
3. **NAS** — une **tâche-mémoire survivable**, évaluée *via le harnais* (sinon bruit).
4. **Langage** — incitation du locuteur **au tick du signal** (trace d'éligibilité — EDR 050) +
   **affordances distinctes**, évalué *via le harnais*.
5. **#8** — une fois la mesure fiable + budgétée : LLM en conteneur, propose des demandes
   `world_demand`, lit les échecs via l'ontologie, **itère** sous évaluation puissante (≫ 3 seeds).

## Comment lire les preuves

Chaque affirmation ci-dessus pointe vers son EDR (`docs/EDR/NNN_*.md`), qui contient le protocole, les
chiffres, l'honnêteté (limites) et les *variables d'expérience*. Le `roadmap.md` est la planification ;
**ce document est la mémoire de ce qu'on a appris.**
