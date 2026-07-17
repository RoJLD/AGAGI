---
id: EDR-149
type: EDR
title: "La recette de fiabilité 10/10 (gate + anti-saturation, EDR 136) est ROBUSTE au SUR-ENTRAÎNEMENT en régime stationnaire (fade0.0, comparaison PROPRE : reste 10/10 de 250 à 1000 trials, gap ET y_rate stables 0.86-0.90 / 0.625) → sur ce banc STATIONNAIRE le gradient intra-vie N'ÉRODE PAS la liaison acquise (érode juste marginalement le hit, −3%) ; la déstabilisation du champion torch IN-WORLD (fil parallèle : apprendre nuit) ne se reproduit donc PAS ici — mais mon banc diffère sur ≥4 axes (stationnarité, TD-bootstrap vs REINFORCE, champion transplanté vs from-scratch, tâche) : au moins un est nécessaire, NON DÉPARTAGÉS ; la seule érosion intra-vie ici est celle du MOYEN X non maintenu, que la recette atténue ; à UN point (fade0.3, schedule-confondu) l'anti-saturation semble réconcilier maintien-de-X et binding (tension EDR 126)"
status: validated
gate: null
verdict: "Test à l'intersection du fil in-world (le gradient intra-vie TD-autograd DÉSTABILISE un champion transplanté : torch-avec 33.0 < sans 38.8) et de la recette d'EDR 136 : le gradient continu ÉRODE-t-il une liaison ACQUISE sur mon banc, et la recette protège-t-elle ? `sweep_overtraining_stability` : recette (gate+anti-saturation pen6) vs brut (pen0), 10 seeds, compo_trials {250,500,1000}, 2 régimes fade_w0 {0.0, 0.3}. RÉSULTAT (fade0.0, comparaison PROPRE car fade≡0 → ct = vraie prolongation identique) : RECIPE_ROBUST — la recette reste 10/10 de 250 à 1000, gap STABLE 0.855→0.899, y_rate STABLE 0.626 (donc la stabilité du gap n'est pas un artefact de dérive de P(Y)), hit_end quasi-stable 0.623→0.603 (érosion MARGINALE −3%). Le gradient continu N'ÉRODE PAS la liaison en régime stationnaire ; le brut érode le MOYEN (hit 0.618→0.561, didx 0.659→0.573), la recette le protège mieux. SCOPING du fil in-world — PRUDENT : la déstabilisation in-world ne se reproduit PAS ici, mais mon banc diffère de l'in-world sur ≥4 axes SIMULTANÉS (stationnaire vs non ; REINFORCE/gate linéaire vs TD-autograd qui bootstrappe une valeur pouvant diverger ; pop from-scratch vs champion legacy transplanté ; tâche abstraite vs survie) → « banc stationnaire n'érode pas » implique AU PLUS qu'AU MOINS UN de ces facteurs est nécessaire, PAS que la non-stationnarité seule est la cause (absence de preuve ≠ preuve d'absence ; explications rivales TD-bootstrap/transplant non éliminées). SYNERGIE (à UN point, schedule-confondu) : fade0.3 SEUL tue le binding (brut 3-4/10, gap 0.000 ; y_rate SATURE 0.94→1.00 — ¬X trop rare, EDR 126/128) mais fade0.3 + recette = 9-10/10 avec rétention (didx 0.79-0.88, hit_end 0.75) → l'anti-saturation semble réconcilier maintien-de-X et binding (tension EDR 126) ; MAIS ct-croissant en fade>0 DILATE le schedule de fade (×4), confondant durée et schedule → un point encourageant, pas une résolution. CONCLUSION : la recette d'EDR 136 est durable en stationnaire ; le gradient n'y est pas un déstabilisateur ; pour le fil in-world, le bon cadrage n'est pas 'dompter le gradient en général' mais isoler lequel des ≥4 facteurs porte l'instabilité (piste : TD-bootstrap et/ou non-stationnarité). Bornage : banc STATIONNAIRE (le point) ; robustesse jusqu'à 4× pas ∞ ; verdict conservateur ; fade0.3 = 1 point confondu."
---

# EDR 149 : La recette 10/10 est robuste au sur-entraînement (stationnaire) — l'écart avec l'in-world n'est pas attribué à un seul facteur

## Question

Deux fils convergent. **In-world** (session parallèle, EDR 134/135/137) : le gradient intra-vie
(TD-autograd) DÉSTABILISE un champion transplanté (apprendre NUIT : torch-avec 33.0 < torch-sans 38.8).
**Compositionnel** (EDR 136) : recette gate + anti-saturation → 10/10. À l'intersection : le gradient
intra-vie ÉRODE-t-il une liaison ACQUISE sur mon banc, et la recette / le maintien de X protègent-ils ?

## Méthode

`sweep_overtraining_stability` : recette (gate learned + `y_saturation_penalty=6`) vs brut (pen=0),
10 seeds, `compo_trials` ∈ {250, 500, 1000} (jusqu'à 4×), sur `fade_w0` ∈ {0.0, 0.3}. Métriques par
cellule : n_bind, gap médian, hit_end (accomplissement), compo_didx (rétention de X), **y_rate**
(anti-artefact : un gap stable pourrait cacher une dérive de P(Y)).

**Caveat méthodo capital.** `_fade_weight = w0·(1 − t/compo_trials)` : à ct plus grand, le fade décroît
plus lentement. En **fade0.0** (fade≡0), ct croissant = **vraie prolongation identique** → comparaison
PROPRE. En **fade0.3**, ct croissant DILATE le schedule (×4) → confond durée et schedule ; les cellules
fade0.3 ne sont donc PAS une prolongation à schedule constant. **L'évidence porteuse est fade0.0.**

## Résultats

**fade0.0 (X non maintenu, comparaison PROPRE) — RECIPE_ROBUST.**

| régime | ct | n_bind | gap | hit_end | did_x | y_rate |
|--------|:--:|:------:|:---:|:-------:|:-----:|:------:|
| brut | 250 | 7/10 | 0.370 | 0.618 | 0.659 | 0.812 |
| brut | 1000 | 9/10 | 0.586 | 0.561 | 0.573 | 0.750 |
| **RECETTE** | 250 | **10/10** | 0.855 | 0.623 | 0.726 | 0.626 |
| **RECETTE** | 500 | **10/10** | 0.917 | 0.606 | 0.613 | 0.626 |
| **RECETTE** | 1000 | **10/10** | 0.899 | 0.603 | 0.624 | 0.625 |

La recette reste **10/10** sous 4×, gap STABLE (0.855→0.899) ET y_rate STABLE (0.626) → la stabilité du
gap n'est PAS un artefact de dérive de P(Y). hit_end érode MARGINALEMENT (0.623→0.603, −3%). Le brut érode
davantage le MOYEN (hit 0.618→0.561, did_x 0.659→0.573) ; la recette le protège mieux.

**fade0.3 (X maintenu) — schedule-confondu, à lire comme UN point.**

| régime | ct | n_bind | gap | hit_end | did_x | y_rate |
|--------|:--:|:------:|:---:|:-------:|:-----:|:------:|
| brut | 250 | 4/10 | 0.000 | 0.740 | 0.768 | 0.938 |
| brut | 1000 | 3/10 | 0.000 | 0.766 | 0.766 | **1.000** |
| **RECETTE** | 500 | 10/10 | 0.806 | 0.726 | 0.790 | 0.748 |
| **RECETTE** | 1000 | 9/10 | 0.778 | 0.749 | 0.877 | 0.750 |

Maintenir X SEUL (brut) TUE le binding (3-4/10, gap 0.000 ; y_rate SATURE →1.000 = always-Y, ¬X trop
rare, EDR 126/128). AVEC la recette : 9-10/10, y_rate tenu ~0.75, ET rétention (did_x 0.79-0.88, hit 0.75).

## Interprétation

**En régime STATIONNAIRE, le gradient intra-vie n'érode PAS la liaison.** La recette d'EDR 136 est
DURABLE (fade0.0, comparaison propre) : 10/10 stable sous 4×, gap et y_rate stables. La seule érosion est
MARGINALE sur le hit (−3%) et, surtout côté brut, sur le MOYEN X non maintenu — un phénomène de rétention
(EDR 126), pas une déstabilisation du conditionnement.

**L'écart avec l'in-world n'est PAS attribuable à un seul facteur (prudence).** Le fil parallèle observe
qu'apprendre NUIT au champion in-world ; mon banc ne reproduit PAS cette érosion. Mais mon banc diffère de
l'in-world sur ≥4 axes SIMULTANÉS : (1) stationnaire vs non-stationnaire ; (2) REINFORCE sur gate linéaire
vs TD-autograd (qui bootstrappe une cible-valeur pouvant diverger) ; (3) pop from-scratch vs champion
legacy TRANSPLANTÉ ; (4) tâche abstraite vs survie. « Un banc stationnaire n'érode pas » implique donc AU
PLUS qu'AU MOINS UN de ces facteurs est nécessaire à l'instabilité — PAS que la non-stationnarité seule en
est la cause. Les explications rivales (TD-bootstrap, transplant) ne sont PAS éliminées. Pour le fil
in-world, le cadrage utile n'est pas « dompter le gradient en général » mais ISOLER lequel des ≥4 facteurs
porte l'instabilité (les plus suspects : TD-bootstrap et/ou non-stationnarité).

**Synergie rétention×binding — encourageante à UN point, pas une résolution.** Sous maintien de X
(fade0.3), le brut ne binde pas (¬X trop rare, y_rate→1.0) mais l'anti-saturation restaure le binding
(9-10/10) SANS sacrifier la rétention (did_x 0.88, hit 0.75). Cela SUGGÈRE que la pénalité homéostatique
lève la tension d'EDR 126 (retenir le moyen ⊥ apprendre le conditionnement). MAIS ce n'est qu'UN fade_w0,
et la comparaison ct y est schedule-confondue → observation prometteuse, pas « résolution ».

## Bornage / honnêteté

- **Attribution in-world PRUDENTE** : ne pas lire « la déstabilisation in-world est causée par la
  non-stationnarité ». Le résultat SCOPE l'écart à ≥1 de {non-stationnarité, TD-bootstrap, transplant,
  tâche}, non départagés. Absence de reproduction ≠ preuve que le gradient est inoffensif in-world.
- **Confond durée/schedule en fade>0** : ct-croissant dilate le fade (×4) ; les claims de robustesse et de
  synergie en fade0.3 confondent durée et schedule. SEUL fade0.0 est une prolongation propre (fade≡0).
  L'instrument correct pour « érosion intra-run » (lire gap/hit à t=250/500/1000 du MÊME run, schedule
  fixe) n'existe pas dans le banc — non fait.
- **hit_end recette fade0.0 érode −3%** (monotone) : donc « n'érode pas » vaut pour la LIAISON (gap) et
  y_rate, pas strictement pour le hit (micro-érosion réelle mais faible).
- **Synergie = 1 point** (fade0.3 non balayé ; « réconcilie », pas « résout »).
- **Verdict RECIPE_ROBUST conservateur/peu sensible** : barre gap>0.3 vs gap réel ~0.9 + n_bind saturé →
  confirmerait robuste avant une érosion sérieuse ; le contraste recette-vs-brut est lu par l'humain, pas
  encodé dans le verdict. Robustesse observée jusqu'à 4×, pas ∞.
- `sweep_overtraining_stability` = orchestration de `run_curriculum_fade_gated` (testé) ; test ajouté =
  smoke de structure. n=10, n_agents=8, médianes de population grossières ; régime proxy hérité 129-136.

Outils : `tools/substrate_ab_compositional.py` (`sweep_overtraining_stability`). Tests
`tests/sandbox/test_substrate_ab_compositional.py`. Étend EDR 136 (durabilité en stationnaire) ; SCOPE
prudemment l'écart avec le fil in-world (EDR 134/135/137, [[sota-gap-substrate]]) sans attribution
mono-causale ; réconcilie à un point la tension d'EDR 126. Revue double-lens appliquée (attribution
in-world rétrogradée mono→multi-facteur ; confond schedule fade0.3 explicité ; y_rate ajouté).
**Renuméroté 140→149** : le fil in-world parallèle traite EDR-140 comme un jalon LIVRÉ (reco migration
torch, ADR-003, avec 141/143 dépendants) ; comme cet EDR-ci est une FEUILLE terminale, je cède le numéro
et prends 149 (haut de la bande // 120-149) pour éviter le doublon d'id — cf. [[parallel-sessions-shared-tree]].
Étend [[nas-bottleneck-is-substrate-not-search]], [[sota-gap-substrate]].
