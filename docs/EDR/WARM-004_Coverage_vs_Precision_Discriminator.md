---
id: EDR-WARM-004
type: EDR
title: "Le plateau du DAgger n'est ni couverture ni précision : la décision se dégrade avec la PROFONDEUR RÉCURRENTE, sur UNE classe — et l'axe énergie est colinéaire au tick (un seul effet compté deux fois)"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
EDR-WARM-003 laissait ouvert : pourquoi DAgger plafonne-t-il à ~35 ticks malgré `acc_on-policy=0.99` ?
(a) COUVERTURE (états tardifs jamais visités, donc jamais appris) ou (b) PRÉCISION (erreurs résiduelles
aux états critiques basse-énergie) ?

## Méthode
`_collect_diag_trajectory` (trajectoire PLEINE LONGUEUR, masquée, alignée par `id(model)`, énergie lue à
l'instant de la décision) + `accuracy_binned` (replay torch `no_grad`, W gelé, sans monde) +
`bins_by_tick` / `bins_by_energy`. Génome DAgger (6 rounds, seed 2026) PERSISTÉ
(`results/warm003_dagger_genome.npz`) → re-diagnostic ~2 min.
- **(A)** accuracy sur les états de l'**ORACLE**, binnée par TICK (bins >35 = jamais visités par le learner).
- **(B)** accuracy sur **son propre** rollout, binnée par ÉNERGIE.

## Résultats bruts

**(A) états de l'ORACLE, par tick** — 0.931 (0-35, n=420) / 0.795 (35-70, n=385) / 0.734 (70-120, n=512) /
**0.713** (120+, n=734) → écart brut **0.218**.
**(B) son rollout, par énergie** — 0.844 (0-20, n=160) / 0.762 (20-40, n=193) / 0.973 (40-60, n=110) /
0.992 (60-80, n=126) / 1.000 (80+, n=17) → écart brut **0.230**.

**La lecture naïve « les deux effets contribuent, magnitudes comparables » est FAUSSE.** Quatre probes
adversariaux (revue finale) la démontent :

### 1. L'axe ÉNERGIE est COLINÉAIRE à l'axe TICK — un seul effet compté deux fois
Avec `forage_payoff=0`, l'énergie est une **horloge** : `corr(tick, énergie) = −0.735` (ticks médians par
bin d'énergie : 80+→0, 60-80→7, 40-60→19, 20-40→41, 0-20→52). Le **même rollout binné par TICK** donne
1.000 / 0.963 / 0.874 / 0.787 → écart **0.213**, soit exactement les « deux » effets. **À tick contrôlé,
l'effet d'énergie s'évanouit et change de signe** : Δ(haute−basse énergie) = +0.012 / +0.125 / +0.032 /
**−0.089**. → La concordance des magnitudes n'était pas une corroboration mais la **signature d'une
double comptabilisation**. **Verdict « LES_DEUX » RÉFUTÉ.**

### 2. Un quart de l'écart (A) est un ARTEFACT DU REPLAY (profondeur récurrente)
In-world, le pop torch est **reconstruit (H→0) à chaque changement de B, donc à chaque MORT**
(`world_1_stoneage.py` ~l.1041-1059 ; `backend_torch.py` l.82) ; le replay, lui, fait tourner H en continu
sur 200 ticks — condition qui **n'existe jamais in-world**. Remettre H à 0 en début de bin récupère
l'essentiel : bin1 0.795→**0.904**, bin3 0.713→**0.771**. Écart résiduel réel : 0.931→0.771 = **0.160**
(l'écart brut 0.218 le **surestimait de ~27 %**).

### 3. Ce n'est PAS de la « couverture d'états »
La cible est une **fonction pure de deux bits EXOGÈNES** (`bit_a`/`bit_b`, re-randomisés chaque tick),
dont la distribution est **uniforme dans TOUS les bins** (p(classe) ≈ 0.25 partout — donc pas non plus
d'artefact de composition). « Ne jamais avoir visité ces états » n'a donc pas de contenu pour CETTE
décision : rien n'y est spécifique à apprendre. La vraie signature est **MONO-CLASSE** : classe 3 →
0.74 / 0.24 / 0.19 / **0.09** tandis que les classes 1 et 2 restent à **1.00** et la classe 0 à
1.00/0.93/0.74/0.69 ; les prédictions s'effondrent vers la classe 2 (966/2051 pour 25 % de base). C'est
un **défaut de FRONTIÈRE DE DÉCISION qui croît avec la profondeur récurrente**, pas un mur de données.

### 4. Le corollaire « acc 0.99 était tronquée » est FAUX
Même génome, même seed, **mêmes états** : `_inworld_accuracy` = **0.988** vs `accuracy_binned` = **0.876**
(n=606) → **Δ0.112 d'artefact pur** (H continu vs H remis à 0 aux morts). Sur l'horizon complet de son
PROPRE rollout, l'accuracy in-world **est bien 0.988**. Le passage 0.99→0.71 mélangeait trois choses
(états différents, régime de H différent, plage de ticks différente) dont une seule est la troncature.

### Ce qui EST solide
La dégradation avec la profondeur est **robuste au garde-fou within-subject du projet** : bin0 vs bin3
**par agent** → **10/10 positifs, sign_p = 0.0010, Δ médian +0.211**. C'est ce chiffre (et non un écart
de moyennes) qui fait foi.

## Verdict
**`DEGRADATION_WITH_RECURRENT_DEPTH_NOT_COVERAGE_ENERGY_AXIS_COLLINEAR`** — la dichotomie
couverture/précision posée par WARM-003 était **mal posée** ; les deux mesures proposées ne sont pas deux
mécanismes mais **un seul effet vu sous deux angles corrélés**. Ce qui est établi :
1. **La décision se dégrade fortement hors de la fenêtre entraînée** (10/10 agents, sign_p=0.001,
   Δ médian 0.21 ; résidu 0.160 après correction du confond de replay).
2. **Le mécanisme n'est PAS la couverture d'états** (cible = fonction pure de bits exogènes uniformément
   distribués) mais un **défaut de frontière de décision concentré sur UNE classe, croissant avec la
   profondeur récurrente**.
3. **L'axe énergie n'ajoute rien** (colinéaire au tick ; effet nul/inversé à tick contrôlé).

**Réconciliation avec [[EDR-WARM-001]]** : ce résultat **CONFIRME et PRÉCISE** le mécanisme que WARM-001
avait déjà rétracté-vers après revue — « pas un covariate-shift des OBSERVATIONS (signal exogène) mais la
dérive de l'état RÉCURRENT H ». WARM-004 le localise : la dérive de H dégrade **une classe de décision en
particulier**, proportionnellement à la profondeur. Il n'y avait donc pas de mécanisme nouveau à inventer.

## Portée & limites
- **Correction majeure post-revue** : la 1ʳᵉ version de ce record concluait « LES_DEUX / plateau
  sur-déterminé » avec un corollaire « acc 0.99 tronquée ». Les deux sont RÉFUTÉS ci-dessus (probes de la
  revue finale, ~5 min depuis le génome persisté, sans ré-entraînement). Conservé ici pour la traçabilité :
  le piège était de lire une **concordance de magnitudes** comme une corroboration alors que les deux axes
  étaient colinéaires.
- Une seule seed (2026), un seul génome. Le sign-test within-subject (10/10) porte sur les agents, pas sur
  des seeds indépendantes.
- `accuracy_binned` expose désormais `reset_h_every` (borne la profondeur récurrente) — c'est le paramètre
  qui rend l'instrument DISCRIMINANT ; tout usage futur doit rapporter les deux régimes (continu ET
  réinitialisé), sinon la mesure re-mélange états et profondeur.
- L'axe énergie devrait être abandonné pour ce monde tant que `forage_payoff=0` (énergie ≡ horloge).
- `results/` est gitignoré → le génome persisté n'est pas versionné (reproductible localement, pas depuis
  le dépôt nu).

## Levier suivant (re-motivé par le mécanisme CORRIGÉ)
Puisque le défaut est une frontière de décision qui se dégrade avec la profondeur récurrente, et non un
manque de données : (1) **borner/réinitialiser la profondeur récurrente** au service (l'in-world le fait
déjà aux morts — l'exploiter délibérément) ; (2) **entraîner à profondeur variée** (l'imitation BPTT part
toujours de H=0 avec `truncate_window` fixe → sur-apprend un régime de profondeur) ; (3) cibler la
**classe défaillante** (classe 3) plutôt que « les états basse-énergie ».

Converge [[EDR-WARM-003]] (dont il corrige l'hypothèse), [[EDR-WARM-001]] (dont il confirme le mécanisme),
[[EDR-WARM-002]], [[within-subject-demand-marker]], [[power-evaporation-guardrail]] (sign-test), REF-DEMAND-MARKER.
