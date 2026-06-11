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
- ⚠️ Langage : émergence sous demande **réelle en moyenne mais faible et bruitée** (047 recalibré
  par 052 : ~0.013 ± 0.009 MI, un seed à 0.002) — *à re-confirmer sous puissance, pas une pierre
  angulaire acquise*.
- ✅ Harnais d'évaluation puissant **construit** (052) — la mesure rend désormais des verdicts *avec
  confiance*.
- ⏳ NAS : croissance jamais sélectionnée (046/049) — il manque une **tâche-mémoire survivable**.

## Les prochaines cibles (nettes, fondées sur la mesure)

1. ✅ **Harnais d'évaluation PUISSANT** (052) — *fait*. Désormais utilisé par défaut.
2. **Re-confirmer 047 sous puissance** (≥ 8 seeds) avant d'en faire une fondation — la priorité
   honnête révélée par 052.
3. **NAS** — une **tâche-mémoire survivable**, évaluée *via le harnais* (sinon bruit).
4. **Langage** — incitation du locuteur **au tick du signal** (trace d'éligibilité, pas prime au
   kill — EDR 050) + **affordances distinctes**, évalué *via le harnais*.
5. **#8** — une fois la mesure fiable + budgétée : LLM en conteneur, propose des demandes
   `world_demand`, lit les échecs via l'ontologie, **itère** sous évaluation puissante.

## Comment lire les preuves

Chaque affirmation ci-dessus pointe vers son EDR (`docs/EDR/NNN_*.md`), qui contient le protocole, les
chiffres, l'honnêteté (limites) et les *variables d'expérience*. Le `roadmap.md` est la planification ;
**ce document est la mémoire de ce qu'on a appris.**
