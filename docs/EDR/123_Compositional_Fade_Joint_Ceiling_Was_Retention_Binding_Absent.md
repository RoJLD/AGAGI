---
id: EDR-123
type: EDR
title: Curriculum à fade — le plafond JOINT était la rétention de X (hit_end 0.30→0.59 ×2 quand X est maintenu), MAIS la mesure DIRECTE de P(Y|X) révèle que le binding conditionnel est ABSENT (Y ⊥ did_x) ; torch résout le joint en montant les marginales, pas en conditionnant Y sur X
status: validated
gate: null
verdict: "Le fade maintient X (compo_didx 0.38→0.865, 5/5, le contrôle PASSE). Sous X maintenu, torch hit_end DOUBLE (0.30→0.59) → le plafond joint d'EDR 122 était LARGEMENT la rétention de X. MAIS la mesure DIRECTE P(Y|X) (le gap d'EDR 122, comblé ici) montre P(Y|X) ≈ P(Y) inconditionnel sur 5/5 seeds (Y INDÉPENDANT de did_x ; P(Y|X) même légèrement ≤ P(Y)) → torch NE binde PAS Y sur did_x, il monte les DEUX marginales. Le means→ends conditionnel n'est PAS cracké même par torch+curriculum+fade ; le binding est le verrou résiduel irréductible (legacy ne monte même pas les marginales : hit 0.000). Nuance/correction d'EDR 122 : la « DISCOVERY torch » est du marginal-raising, pas du binding."
---

# EDR 123 : Curriculum à fade — plafond joint = rétention de X ; binding conditionnel ABSENT

## Contexte

EDR 122 : torch = DISCOVERY (le curriculum lève le joint Y∧X, hit_end 0.03→0.30, ×10) ; legacy =
CREDIT (0.000). Mais la revue a borné le résultat sur DEUX points laissés ouverts :

1. **Le plafond joint de torch (0.30) était-il la rétention de X ou le binding ?** En bascule dure
   (S1 reward 0 en phase B), X DÉCLINE (compo_didx ~0.9→0.38), donc le joint était peut-être étranglé
   par la perte de X, pas par le binding.
2. **L'instrument ne mesurait que le JOINT** `mean((move2==Y) ET did_x)`, jamais `move2==Y`
   inconditionnel → `P(Y|X)` était INFÉRÉ (ratio de médianes), pas mesuré.

Ce chantier (a) MAINTIENT X via un bonus décroissant (fade) et (b) MESURE `P(Y|X)` directement.

## Méthode

- **Script** : `tools/substrate_ab_compositional.py::compare_curriculum_fade` (commit `3d4d3bd`).
  `run_curriculum` (bascule dure, EDR 122) reste l'INSTRUMENT intact ; le fade est ajouté à côté.
- **Phase A (warmup, dense sur X)** : identique à EDR 122 (`forward(obs_a)`→`learn(+1 si did_x sinon −1)`,
  S1 seul). `warmup=150`. Enseigne X.
- **Phase B à FADE LINÉAIRE** : pour le trial `t` sur `T=compo` :
  - `fade_w = fade_w0·(1 − t/T)` (décroît de `fade_w0` à 0).
  - S1 reward = `fade_w · _warmup_reward(move1, X)` (au lieu de 0 dur) → **maintient X tôt, s'éteint**.
  - S2 reward = `compositional_reward(move2, Y, did_x)` (INCHANGÉ : +1 ssi Y ET did_x).
  - `compo=250`, A/B legacy vs torch, **5 seeds**, 8 agents. `fade_w0=1.0`.
- **Mesure DIRECTE P(Y|X)** : on trace par trial `did_x` ET `y_correct=(move2==Y)` INCONDITIONNEL ;
  `p_y_given_x_end` = fraction de `y_correct` PARMI les `did_x` du dernier quart (None si aucun did_x).
  On garde aussi `y_rate_end` = `mean(y_correct)` INCONDITIONNEL pour tester l'indépendance.
- **Baseline `fade_w0=0`** (3 seeds) : ≡ bascule dure → doit reproduire EDR 122.

## Contrôle de maintien de X (le nouveau héros) — PASSE

Avant de lire le plafond : le fade DOIT garder X plus haut que la bascule dure (~0.38 en EDR 122),
sinon il ne maintient rien et le test ne mesure rien.
**torch `compo_didx_end` médian = 0.865** (par seed : 0.821, 0.722, 0.865, 0.970, 0.950 — **5/5 >> 0.6**).
→ Le fade MAINTIENT X (0.38 → 0.865). Le contrôle passe : le test de plafond est lisible, et la mesure
P(Y|X) est PROPRE (conditionnel sur un subset stable ~87%, pas le subset déclinant de la bascule dure).

## Résultats

Per-seed phase B (fade w0=1.0) :

| seed | backend | compo_didx_end | **hit_end** | **P(Y\|X)_end** | y_rate_end (incond.) |
|------|---------|----------------|-------------|-----------------|----------------------|
| 0 | legacy | 0.750 | **0.000** | 0.000 | 0.125 |
| 0 | torch  | 0.821 | **0.635** | **0.774** | 0.786 |
| 1 | legacy | 0.500 | **0.000** | 0.000 | 0.125 |
| 1 | torch  | 0.722 | **0.367** | **0.508** | 0.536 |
| 2 | legacy | 0.875 | **0.000** | 0.000 | 0.000 |
| 2 | torch  | 0.865 | **0.587** | **0.678** | 0.722 |
| 3 | legacy | 0.466 | **0.000** | 0.000 | 0.000 |
| 3 | torch  | 0.970 | **0.720** | **0.742** | 0.750 |
| 4 | legacy | 0.250 | **0.000** | 0.000 | 0.125 |
| 4 | torch  | 0.950 | **0.397** | **0.418** | 0.433 |
| **médiane** | **torch** | **0.865** | **0.587** | **0.678** | **0.722** |
| **médiane** | **legacy** | — | **0.000** | **0.000** | — |

**Baseline `fade_w0=0` (cohérence, 3 seeds)** : torch `hit_end` médian **0.306**, `compo_didx_end`
médian **0.377** (X décline) → **reproduit EDR 122 à l'identique** (fade_w0=0 ≡ bascule dure). ✓
Le code y donne `FADE_INEFFECTIVE` (compo_didx 0.38 ≤ 0.40 = le garde-fou se déclenche, correctement :
w0=0 ne maintient PAS X). Confirme que le banc fade=0 est cohérent avec l'instrument 122.

## Lecture : deux constats, le second étant l'information décisive

### (1) Le plafond JOINT était largement la rétention de X
Sous X maintenu (fade), torch `hit_end` passe de **0.30 (baseline/EDR 122) à 0.59 (fade), ~×2**, paire
à paire sur les seeds 0/1/2 (0.635>0.306, 0.367>0.204, 0.587>0.312, 3/3). → le plafond de 0.30 d'EDR 122
n'était PAS un mur du binding : maintenir X relève le joint proportionnellement.

### (2) MAIS le binding conditionnel est ABSENT — Y est INDÉPENDANT de did_x (le constat décisif)
La mesure DIRECTE de P(Y|X) (le gap d'EDR 122, comblé ici) montre :
**`P(Y|X)_end` ≈ `y_rate_end` inconditionnel sur les 5/5 seeds**. Écarts `P(Y|X) − y_rate` :
**[−0.012, −0.028, −0.043, −0.008, −0.015]** — quasi nuls et **systématiquement ≤ 0** (5/5).

→ Conditionner sur `did_x` **n'augmente PAS** l'émission de Y (si quoi que ce soit, marginalement
anti-corrélé). Par l'algèbre `P(Y) = P(Y|X)·P(X) + P(Y|¬X)·P(¬X)`, on déduit **P(Y|¬X) ≈ P(Y|X)**
(seed 0 : P(Y|¬X) ≈ 0.84 ≥ P(Y|X) = 0.77). **Y ⊥ did_x (au plus marginalement anti-corrélé, jamais
positivement).** Ce qui est établi par les données, c'est l'**absence de binding POSITIF** (X n'augmente
pas Y) ; le signe systématiquement ≤ 0 pourrait être une stricte indépendance OU un léger trade-off
comportemental (l'action S1 sur X corrélant à une politique S2 marginalement différente) — la conclusion
« pas de binding » est identique dans les deux lectures. Torch résout le joint en **montant les DEUX
marginales** P(X) (0.87) et P(Y) (~0.72), PAS en **conditionnant** Y sur X. Le joint élevé (0.59) est le
PRODUIT de deux marginales hautes, pas un binding.

| régime (torch) | P(X)=didx_end | P(Y)=y_rate | P(Y\|X) | hit (joint) | lecture |
|----------------|---------------|-------------|---------|-------------|---------|
| bascule dure (122, w0=0) | 0.38 | ~0.70 | ~0.70 | 0.30 | X décline → joint bas |
| **fade (w0=1.0)** | **0.87** | **0.72** | **0.68** | **0.59** | **X maintenu → joint ↑ ; P(Y\|X)=P(Y) : pas de binding** |

→ La hausse 0.30→0.59 s'explique ENTIÈREMENT par P(X) 0.38→0.87 × un P(Y)≈P(Y|X) constant.
**Le means→ends conditionnel (émettre Y *parce que* X a été fait) n'est PAS cracké, même par
torch + curriculum + fade.** Le binding reste le verrou résiduel.

## Verdict

- **Code** : `verdict_fade = CEILING_WAS_BINDING` (P(Y|X) médian 0.678 ≤ 0.70). Directionnellement juste
  (le binding EST le résidu), mais la lecture humaine est plus nette grâce à P(Y|X)≈y_rate :
- **Humain** : **CEILING_WAS_RETENTION pour le JOINT** (maintenir X double hit_end) **+ binding ABSENT**
  (Y ⊥ did_x ; P(Y|X) ≈ P(Y), pas de conditionnement). Le gain joint de torch — l'apparente
  « DISCOVERY » d'EDR 122 (×10) et le ×2 supplémentaire ici — est du **marginal-raising**, PAS du
  binding compositionnel. legacy ne monte même pas les marginales (hit 0.000, P(Y|X)=0.000, 5/5) →
  reste CREDIT, en contraste.

## Conséquences

- **Correction/nuance d'EDR 122** : la mesure DIRECTE (que 122 ne pouvait qu'inférer) montre que la
  « DISCOVERY torch » n'est pas un binding conditionnel mais une montée des deux marginales. Le verrou
  identifié par la chaîne 104-122 — **l'assignation de crédit compositionnel (binding Y|did_x)** — n'est
  **PAS levé** par gradient+curriculum+fade ; il est seulement CONTOURNÉ par le marginal-raising tant que
  la tâche récompense le joint de deux comportements co-activables.
- **Thèse de migration** : nuancée mais pas réfutée. Le gradient FAIT mieux que le hebbien (torch monte
  les marginales et gagne le joint, hit 0.59 vs 0.000, `sign_p=0.0625` 5/5 ; legacy ne décolle pas).
  MAIS « torch en prod » seul ne suffira pas au means→ends si le binding conditionnel reste absent : il
  faudra un signal/architecture qui FORCE le conditionnement (tâche où Y sans X est puni, gating explicite
  did_x→logits Y, ou éligibilité/TD(λ) sur le crédit différé) — pas seulement un meilleur optimiseur.
- **Le P(Y|X) direct devient l'instrument de binding** pour la suite : tout test de composition doit
  mesurer le CONDITIONNEL, pas le joint (le joint confond binding et marginal-raising).

## Caveats

1. **Seuils heuristiques** : le `verdict_fade` du code (0.40/0.60 didx, 0.35 hit, 0.70 P(Y|X)) cadre ;
   le verdict scientifique est lu sur les chiffres bruts (P(Y|X)≈y_rate, pas sur le franchissement de 0.70).
2. **Puissance** : n=5. `sign_p=0.0625` (5/5 torch>legacy = 1/16, plancher de puissance à n=5, juste
   au-dessus de 0.05). La robustesse repose sur la **consistance 5/5** (P(Y|X)≈y_rate sur TOUS les seeds ;
   écarts tous ≤ 0) + l'algèbre d'indépendance, plus que sur le p-value.
3. **P(Y|X) sur le dernier quart** : le fade maintient X (didx 0.87) donc le subset conditionnel est
   stable et large — mesure propre (c'est précisément ce que la bascule dure ne permettait pas).
4. **Indépendance ≠ preuve d'incapacité absolue** : la mémoire de did_x est présente (EDR 120, décodable
   AUC~0.90), donc l'info EST là ; torch ne l'UTILISE pas pour gater Y sous ce shaping. Un shaping qui
   punit Y-sans-X testerait si le conditionnement peut être forcé (suite).
5. **Micro-tâche proxy** : X-gate-Y, PAS une preuve d'apex en prod (bornage 115/117/119/120/122).
6. **Asymétrie de seeds baseline** : le bras fade (w0=1.0) tourne sur 5 seeds, la baseline de cohérence
   (w0=0) sur 3 seeds seulement. Non bloquant car l'équivalence w0=0 ≡ bascule dure est garantie
   STRUCTURELLEMENT (`_fade_weight` retourne 0.0 si w0=0), pas par hasard de seed ; mais l'asymétrie est
   notée pour honnêteté (un re-run baseline 5 seeds la lèverait).

## Liens

- `[[coop-competence-is-population-property]]` — chaîne des leviers ; binding = verrou résiduel, confirmé
- `[[sota-gap-substrate]]` — migration moteur : gradient gagne le joint mais ne binde pas seul ; nuance
- EDR 122 — DISCOVERY/CREDIT ; ici CORRIGÉ : la « DISCOVERY torch » = marginal-raising, pas binding
- EDR 120 — mémoire présente (l'info did_x est là ; torch ne la gate pas sur Y)
- EDR 119 — taille pas le verrou ; EDR 117 — les deux échouent nu
- Outils : `tools/substrate_ab_compositional.py` (`run_curriculum_fade`/`compare_curriculum_fade`)
- Données : `results/sab_curriculum_fade.json`
