# EDR 090 — NEGATIF PROFOND : le curriculum de létalité n'a pas de premier barreau survivable

## Contexte

EDR 089 a diagnostiqué une tension structurelle (létalité ⊥ survie longue) et désigné **le** levier pour la
casser : un **curriculum de létalité** — ramper `leurre_frac` de douce à dure, porté par la maîtrise, pour
fabriquer un substrat survivable au départ qui durcit une fois l'évitement acquis. EDR 090 teste ce levier,
et lui seul (pré-enregistrement `docs/superpowers/specs/2026-06-22-EDR090-Lethality-Curriculum-design.md`).

Design (gelé avant données) : variable unique = **curriculum** (rampe `0.17→0.33→0.50→0.67→0.83`, promotion
des génomes portée par `has_graduated`) **vs flat** (cold start direct à `0.83`), apparié par seed, budget
d'ères égal. **Pas de langage** (pure survie/évitement ; le contraste FIABLE−BRUITÉ aurait été EDR 091).
Métrique terminale `net = kills − leurre_hits` ; **gate de validité : survie médiane > 120 ticks** (comme 089).
Compétence de graduation = survie médiane normalisée `clip(median(ticks)/300, 0, 1)`.

## Le verdict : NEGATIF PROFOND au gate

Le curriculum **échoue le gate** : survie médiane au terminal `0.83` = **42 ticks** (≪ 120). Le contraste net
CURRICULUM−FLAT est nul et non significatif (médiane −0.67, Wilcoxon p=1.0), mais **non interprétable** : le
substrat est VOID au sens du gate. Le finding n'est pas dans le contraste — il est dans **les transcripts**.

> **Le curriculum ne diplôme AUCUN palier.** Et la compétence-survie **décroît** avec la létalité, dès le bas :
>
> | palier `leurre_frac` | 0.17 | 0.33 | 0.50 | 0.67 | 0.83 | gradué ? |
> |---|---|---|---|---|---|---|
> | compétence rep0 | 0.27 | 0.22 | 0.16 | 0.19 | 0.11 | non × 5 |
> | compétence rep1 | 0.60 | 0.31 | 0.39 | 0.21 | 0.13 | non × 5 |
>
> (compétence = survie médiane / 300 ; plancher de graduation = 0.50.)

## Le mécanisme : pas de premier barreau survivable

> **Les champions stoneage ne transfèrent pas leur survie au monde de Lewis — même à létalité MINIMALE.**

À `leurre_frac = 0.17` (10 apex positifs, 2 Leurres mortels seulement), les champions survivent ~80-180 ticks
sur 300 (compétence 0.27-0.60), **sous le plancher de graduation (0.50 = 150 ticks)**. Le curriculum n'a donc
**pas de barreau d'où démarrer** : son premier palier, déjà le plus doux possible, n'est pas maîtrisable.
10 générations d'évolution par palier (params gelés) ne le déverrouillent pas — la compétence reste plate-basse
puis décroît à mesure qu'on monte la létalité.

C'est **plus profond** que la tension d'089. 089 disait : « létalité haute → survie courte → pas le temps
d'évoluer l'évitement ». 090 montre que **même sans létalité élevée**, le substrat de départ ne survit pas au
monde référentiel de Lewis. Le problème n'est pas la pente du curriculum (paliers trop espacés) ni l'énergie
(sweet-spot 085 appliqué) : c'est que **le point de départ est inadapté au monde-cible**. Les champions ont
été forgés en *stoneage* (chasse, craft) ; transplantés dans Lewis (apex qui ripostent, signal référentiel),
ils n'ont pas le répertoire pour durer, et la mutation ne le forge pas en quelques générations (cohérent
EDR 076 : « la mutation est un forgeron faible »).

## Ce que dit le contraste (sur substrat VOID — pas la réponse)

net CURRICULUM−FLAT = −0.67 (médiane), IC95 bootstrap [−2.67, +1.33], Wilcoxon p=1.0. **Non interprétable**
(gate échoué). Cohérent avec « aucun avantage » : ni le curriculum ni le flat ne produisent d'agents qui
survivent ET discriminent à `0.83` (net_curr [−1.67, −1.0], net_flat [+1.0, −2.33]). Sans survie, l'évitement
ne peut pas être sélectionné.

## Le vrai levier (re-pointé) : adapter le substrat AVANT de durcir

Le curriculum de létalité présuppose un barreau bas survivable. Il n'existe pas ici. Le levier en amont :
**fabriquer d'abord un substrat qui survit au monde de Lewis à létalité ~0** (transfert/adaptation des
champions au répertoire de Lewis — éviter les apex, exploiter les positifs), *puis* seulement appliquer la
rampe de létalité. Tester « le langage paye » exige une chaîne plus longue qu'on ne croyait : survivre-en-Lewis
→ rampe de létalité → évitement → écoute du signal. EDR 090 montre que la **première marche** (survivre-en-Lewis)
n'est pas franchie par les champions stoneage seuls.

## Honnêteté & méthode

- **NEGATIF PROFOND, pas un négatif sur l'hypothèse langage** : le gate pré-enregistré a fait son travail — il
  a empêché de conclure sur un substrat où la prémisse (un barreau survivable) est fausse.
- **Provenance & puissance.** Résultat de gate : pilote `results/lethality_curriculum_190.json` (R=2,
  num_agents=8, max_eras=4, **max_ticks=300**) → surv_med 42, NEGATIF PROFOND. Le pilote est **sous-puissant**
  (8 agents, 4 générations/palier) ; mais le pattern — compétence plate-basse à 0.17, déclin avec la létalité,
  **zéro graduation** — est **reproduit aux params gelés** (24 agents, max_eras=10, max_ticks=300) dans les
  diagnostics de cette session (compétence 0.27-0.60 à 0.17, survie 80-180 ticks ; ≈40 ticks à 0.83). Le verdict
  est **surdéterminé** : il ne dépend pas du nombre d'agents/générations, parce que rien ne diplôme jamais.
- **Confound du gate écarté** : le gate « >120 ticks » n'a de sens qu'à `max_ticks=300` (sinon « survivre 120 »
  est trivial ou impossible). Tous les chiffres cités sont à max_ticks=300 → directement comparables aux 37
  ticks d'089.

## Dette d'infrastructure découverte (le vrai coût de cette session)

- **Contention KuzuDB multiprocess (RÉELLE, corrigée).** `Biosphere3D.__init__` ouvre KuzuDB
  inconditionnellement ; en multiprocess, N workers ouvrent le même fichier `data/` → KuzuDB n'autorise qu'un
  writer → les perdants échouent, leur worker meurt mais `_running` reste True → `emit()` empile sans
  consommateur (queue → 5 GB) et `emit_sync` bloque. Les ères longues d'EDR 090 saturent ce chemin (089 ne
  l'a pas vu : ères mortelles courtes ~37 ticks). Corrigé par `_disable_kuzu()` (neutralise logger.start/emit
  avant toute création de monde) — triple bénéfice : pas de contention, pas de fuite, substrat 100% reproductible
  (in_mem=zéros, = runner clean d'089 sans même ouvrir KuzuDB).
- **PAS de fuite mémoire générale.** Reproductions contrôlées : RSS plate 55-60 MB sur 12+ ères / 8 générations,
  génome constant 118 KB. Les « explosions » 1,5 GB observées venaient de (a) **sessions Claude parallèles** sur
  le tree partagé (jobs concurrents à 1,4-1,6 GB) starvant les pilotes, et (b) **workers ProcessPoolExecutor
  orphelins** laissés par des kills mid-run (tuer le parent orpheline les enfants ; ils ont tourné 19h en volant
  le CPU). Leçon process : tuer l'**arbre entier**, jamais le parent seul.
- **Runaway connectome récurrent (086-class, NON résolu).** ~1 rep sur 3 (plusieurs seeds testés : rb=200190,
  et un seed=7) part en runaway compute+mémoire à **onset tardif** (820 MB-1,6 GB, dizaines de min CPU). Ni
  explosion de poids (clampés à 5.0) ni NaN précoce — onset après plusieurs générations sur des trajectoires à
  survie longue. **Empêche un run frozen R≥3 propre** et constitue une dette core-engine à part entière (à
  guarder par un budget-temps/itérations par ère avant tout run à haute puissance).

## Variables d'expérience

Échelle de paliers `leurre_frac`, `max_eras` par palier, plancher de graduation, **substrat de départ**
(stoneage vs adapté-Lewis — le vrai goulot), sweet-spot énergie (085). Outils : `tools/lethality_curriculum.py`
(mp, `_disable_kuzu`), `src/curriculum/runner.py` (porte `has_graduated` réutilisée), `src/seed_ai/exp_stats.py`.
Provenance : `results/lethality_curriculum_190.json` (gate NEGATIF PROFOND). Lignée : 087→088→**089**→090.
