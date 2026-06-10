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

**Leçon IV (la recette)** : « la demande crée la capacité » est **vraie mais exigeante**. La demande
doit :
1. **CIBLER** la capacité précise (référentielle→langage ; mémorielle/computationnelle→architecture) ;
2. être **SURVIVABLE** (sinon pas de sélection).
Un « monde plus dur » générique ne suffit pas. **Concevoir la bonne demande est *le* travail** — et
c'est le rôle recadré du **#8** (proposer+itérer des demandes ciblées).

---

## Où on en est (au 2026-06-11)

- ✅ Chaîne moyens→fins émergente, robuste, dominante, auto-suffisante.
- ✅ Infrastructure RSI (#8) **câblée mais NON armée** : cage (035), yeux (036), mémoire (032/034),
  juge (041), boucle (044). Le seam LLM attend un conteneur jetable.
- ✅ Langage : **émergence prouvée sous demande** (047), mais **naissante/fragile** (048) — bloquée
  par l'**altruisme du signal**.
- ⏳ NAS : croissance jamais sélectionnée (046/049) — il manque une **tâche-mémoire survivable**.

## Les 3 prochaines cibles (nettes, fondées sur la mesure)

1. **NAS** — une **tâche-mémoire survivable** (se souvenir du type d'apex après s'en éloigner) →
   saturer le connectome récurrent (la *bonne* demande pour l'architecture).
2. **Langage** — **aligner l'incitation du locuteur** (que parler *paie* pour le parleur : réciprocité)
   + **affordances distinctes** (3 réponses, pas 3 types) → vaincre le silence (048).
3. **#8** — l'**armer pour itérer ces demandes** (Proposer `kind="world_demand"`) : proposer une
   demande ciblée, mesurer, raffiner — des centaines de fois là où on en a fait quelques-unes à la main.

## Comment lire les preuves

Chaque affirmation ci-dessus pointe vers son EDR (`docs/EDR/NNN_*.md`), qui contient le protocole, les
chiffres, l'honnêteté (limites) et les *variables d'expérience*. Le `roadmap.md` est la planification ;
**ce document est la mémoire de ce qu'on a appris.**
