---
id: EDR-S2-CREDIT-ABLATION-2
type: EDR
title: "Chacune des DEUX voies du crédit publié suffit seule à mettre le bassin DAgger au PLANCHER de la politique sans perception (TD par tick sans épisode : 8,5 ; épisodique sans TD : 7,5 en P4.9 ; plancher froid mesuré 7,5) ; un retour CONSTANT POSITIF érode à mi-chemin (23,25, 11/12) en ne déplaçant les poids que de 5 %. Le PAS reste la seule dépendance quantitative établie (−29,0 → −19,0 à voie et dose égales, 12/12), et il INTERAGIT avec la voie. Direction contre amplitude n'est pas tranché : c'est P4.18"
status: active
verdict: DEUX_VOIES_SUFFISANTES_AU_PLANCHER_RETOUR_CONSTANT_POSITIF_ERODE_A_MI_CHEMIN_LE_PAS_MODULE_DIRECTION_NON_TRANCHEE
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-S2-CREDIT-ABLATION, EDR-S2-REWARD-ABLATION, EDR-S2-CREDIT-RETENTION, EDR-CALIB-LEARNER]
---

> **Ce record a été réécrit le 2026-09-24 après une revue adversariale à trois lentilles** (chiffres recalculés
> depuis le JSON sans faire confiance au bloc `verdict` ; méthode et seams contre la règle scellée ; lecture et
> portée), chaque grief étant re-mesuré par un second agent avant d'être retenu : 21 griefs confirmés sur 22.
> **Les trois verdicts scellés n'ont pas bougé** ; ce qui a été corrigé est la PROSE, qui débordait les branches
> sur cinq points (« sans contenu », « ni du pas », « érosion par unité de mouvement », « crête », « censures 0 »).
> Le détail est dans le commit de clôture.

## Question (backlog P4.16, rang 4 quater ; règle scellée AVANT toute cellule)

[[EDR-S2-CREDIT-ABLATION]] a établi que l'érosion du bassin DAgger de [[EDR-WARM-003]] par le crédit publié
(Actor-Critic TD(0) par tick + REINFORCE épisodique k = 8, lr 0,04) exige un signal NON NUL, ignore son signe, et
que la voie ÉPISODIQUE seule suffit. Trois questions restaient, une par bras : **(1)** le TD par tick SEUL
(épisodique coupé) détruit-il aussi ? **(2)** l'opérateur détruit-il quel que soit le CONTENU du signal — un
retour constant +1 substitué aux récompenses des deux voies ? **(3)** la voie épisodique détruit-elle encore à pas
10× plus petit ? Règle : `docs/preregistrations/S2-CREDIT-ABLATION-2.json` (12 branches ordonnées, budget
57 600 s dérivé des coûts mesurés de P4.9, charge déclarée).

## Pré-vol — ce qui ATTEINT le learner d'origine (réponse connue, publié dans le JSON)

Les deux seams neufs (`episode_enabled`, `reward_const`) vivent dans le runner (`credit_variant`, empilé SOUS
`count_learning_events`, dont le fichier était en cours d'édition par une autre session) et sont vérifiés sur ce
qui atteint les originaux `learn` / `learn_episode` : épisodique coupé → `learn_episode` d'origine JAMAIS appelé,
TD vivant (`td_updates` 1999 sur les 12 cellules) ; constante → toutes les récompenses reçues par les DEUX voies
valent exactement 1,0 et les deux voies mettent à jour ; épisodique seul à 0,004 → `learn` jamais appelé
(`td_updates` 0 sur les 12), pas LU sur l'optimiseur = 0,004. Un seam qui fuit fait LEVER le pré-vol
(contre-exemple gelé). Les seams sont en outre vérifiés IN SITU sur les 60 cellules du run, pas seulement au
pré-vol : `episode_updates` ∈ {0} pour `b_tdonly`, `td_updates` ∈ {0} pour `b_eplr`.

⚠️ **Le contrôle « no-op EXACT contre la trace de P4.9 » est STRUCTUREL, pas une calibration de seam** (revue
adversariale) : `ARM_CREDIT['b_full']` vaut `_BASE` et `credit_variant` sort par un `yield` nu sur ces défauts
(`if episode_enabled and reward_const is None: yield; return`), donc aucun patch n'est traversé et un seam fautif
ne pourrait pas faire tomber cette bit-identité. Ce que ce contrôle mesure réellement, et qui vaut d'être publié :
la reproductibilité bit-à-bit du harnais entre deux appels du même processus (pas de désynchronisation de bande
RNG) et une dose TD non nulle. Les trois seams réellement calibrés à réponse connue sont ceux qui patchent.

## Méthode

* `tools/evo_runs/s2_credit_ablation_2.py`, dispositif de P4.4/P4.8/P4.9. Par seed (2026-2037, n = 12, LES MÊMES
  seeds, unité = le seed), cinq bras APPARIÉS sur le bassin DAgger cloné ×12 : **(a)** `a_frozen`, W gelé,
  re-mesuré ; **(b_full)** crédit publié complet ; **(b_tdonly)** épisodique coupé, TD seul ; **(b_const)** retour
  constant +1 sur les deux voies ; **(b_eplr)** TD coupé, épisodique seul, lr 0,004.
* Phase 1 IMMORTELLE 2000 ticks pour les QUATRE bras à crédit (dose comptée, `resurrections` publiées) ; **le bras
  gelé (a) ne traverse QUE la phase 2** — il n'a donc ni dose, ni `Σ|ΔW|`, ni `resurrections`. Phase 2 MORTELLE
  200 ticks à poids GELÉS (`Σ|ΔW| = 0` asserté). Régime publié (bloc `regime`, `lr_published` 0,04 lu sur
  l'optimiseur).
* **Réplication** : `b_full` mesuré sur le seed 2026 est BIT-IDENTIQUE à P4.4 (âges, dose 1999, 12 résurrections,
  `Σ|ΔW|` 18242,04) ; les 11 autres seeds de `b_full` sont IMPORTÉS de `results/s2_credit_retention.json`
  (`imported_from`), comme le prévoyait la règle. C'est la **troisième** réplication de cette cellule (P4.4 est
  l'original, il ne se réplique pas lui-même), et les trois portent sur le SEUL seed 2026 : les 11 autres lignes
  de `b_full` sont la même mesure du 2026-09-14, recopiée, valeurs inchangées.
* `declare_design` (unité = seed, n = 12, famille 12). Provenance : run lancé le 2026-09-22 à 21:48 depuis l'arbre
  à `16163f30` (sale), runner identique à celui committé en `b90a509d`.

## Résultat (`results/s2_credit_ablation_2.json`)

Le **plancher froid** mesuré par [[EDR-WARM-010]] et scellé dans la règle de P4.4 vaut 9,0 ; le plancher
effectivement atteint par une cohorte fraîche sous crédit dans ce dispositif (`S_c` de P4.4, mêmes seeds) vaut
**7,5** en médiane. La saturation ci-dessous est `|d| / (S_a − S_c)` du même seed : c'est ce que l'instrument peut
au maximum mesurer avant de buter sur le plancher.

| bras | survie médiane (phase 2) | écart au bassin (médiane ; signe −/+ sur 12) | classe | saturation | dose | `Σ|ΔW|` / complet | `resurrections` |
|---|---|---|---|---|---|---|---|
| (a) `S_a` bassin gelé | **36,0** (17,0–50,0) | — | — | — | — | — | — (pas de phase 1) |
| (b_full) `S_full` | **8,0** | `d_full` **−28,25** ; 12/0 | ERODE | **0,979** | `dose_full` 1999 | `dW_full` 1,00 | 10 |
| (b_tdonly) `S_tdonly` TD seul | **8,5** | `d_tdonly` **−27,75** ; 12/0 | ERODE | **0,961** | `dose_tdonly` 1999 | `dW_tdonly` **0,71** | 8 |
| (b_const) `S_const` retour constant +1 | **23,25** (13,0–39,5) | `d_const` **−12,25** ; 11/1 | ERODE | **0,568** | `dose_const_td` 1999 · `dose_const_ep` 250 | `dW_const` **0,054** | 65,5 (5–328) |
| (b_eplr) `S_eplr` épisodique seul, 0,004 | **17,0** (11,5–32,0) | `d_eplr` **−19,0** ; 11/0 (un 0) | ERODE | **0,649** | `dose_eplr` 250 | `dW_eplr` **0,064** | 16,5 |

`d_const` par seed : −10,5 · −20,0 · −28,0 · −10,5 · −14,0 · −10,0 · −22,5 · −20,0 · −11,0 · −2,5 · **+10,5**
(seed 2036, le bassin le plus bas, 17,0) · −13,5. `d_eplr` : −20,0 · −21,5 · −29,0 · −7,0 · −23,5 · −18,5 · −14,0
· −16,5 · −38,0 · −19,5 · **0** · −12,0.

**Censures : 1 sur 60 cellules.** `b_const` / seed 2034 : un clone sur 12 atteint l'horizon de 200 ticks sans
mourir — le seul survivant à horizon complet des 720 clones du run, et il est dans le bras à retour constant. Le
vecteur d'âges y est censuré à droite, mais la DV ne l'est pas : la médiane de 12 âges est la moyenne des 6ᵉ et
7ᵉ valeurs (33 et 45), le clone censuré étant le 12ᵉ — `S_const(2034) = 39,0` et `d_const(2034) = −11,0` sont
EXACTS, et aucune branche du verdict n'en dépend.

## Verdict (branches scellées, lues dans l'ordre)

1. n = 12. 2. `S_a` 36,0 ≥ 20. 3. doses TD 1999 sur trois bras, épisodiques 250 sur deux. 4. `d_full` ERODE
(12/12, −28,25) : la prémisse se reproduit. 5. `d_tdonly`, `d_const`, `d_eplr` : ERODE, ERODE, ERODE.
**6a. CONTENU_INDIFFERENT** (`d_const` ERODE). **7a. TD_SUFFIT_AUSSI** (`d_tdonly` ERODE).
**8a. EPISODIQUE_DESTRUCTEUR_A_PETIT_PAS** (`d_eplr` ERODE).

**Chacune des deux voies SUFFIT seule à amener le bassin au plancher.** Le TD par tick sans un seul épisode rend
8,5, le crédit complet 8,0, l'épisodique seul de P4.9 7,5 — contre un plancher froid mesuré à 7,5 et une
saturation de 96-98 %. L'étendue inter-seed tombe de 33,0 ticks (bassin) à 2,5. **Ce que le run établit est une
SUFFISANCE, pas un ordre** : à ce point de fonctionnement la DV est saturée, et le run ne peut PAS classer les
deux destructeurs entre eux (contraste apparié 8,5 contre 8,0 : 7/3/2 seeds, binomial bilatéral p = 0,344).
Ni l'une ni l'autre voie n'est un accessoire.

**Un retour constant +1 érode déjà** (−12,25 ; 11/12 ; 5,4 % du mouvement du complet) — **mais ce bras n'est PAS
« un signal sans contenu »**, et c'est la correction la plus importante que la revue a produite. Les deux voies y
reçoivent un avantage uniformément POSITIF, c'est-à-dire l'ordre « renforce toutes les actions que tu viens de
prendre » : (i) `learn_episode` reçoit du monde un avantage DÉJÀ centré (`ep_return − mean(ep_return)`,
`world_1_stoneage.py:1096`) et la seam agit EN AVAL, remplaçant une moyenne nulle par une constante — mesuré sur
le vrai `learn_episode`, la même constante injectée en AMONT donne `Σ|ΔW| = 0,000` quand la seam donne 1,195,
soit plus que le vrai signal centré (0,836), et fait monter le log-prob des actions prises ; (ii) côté TD,
δ = r + γV′ − V avec |V| < 1 (borne tanh) et γ = 0,9 : le point fixe V* = 10 est structurellement inatteignable,
δ ≈ +1 dès le premier pas (médiane 0,99, positif sur 99 % de 400 pas). **Ce bras mesure donc l'érosion sous un
OFFSET POSITIF de l'avantage — auto-renforcement de la politique par ses propres échantillons — pas sous une
absence de contenu.** Le token scellé `CONTENU_INDIFFERENT` reste correctement lu (la branche 6a dit « un signal
sans contenu DÉTRUIT », et il détruit) ; c'est son interprétation mécaniste qui était fausse.

**Le PAS n'est pas indifférent : c'est la seule dépendance quantitative établie de l'arc, et il INTERAGIT avec la
voie.** À voie et dose ÉGALES (épisodique seul, 250 épisodes des deux côtés), diviser le pas par 10 fait passer
l'écart de **−29,0** (`b_tdoff` de P4.9) à **−19,0** : gain apparié positif sur **12/12 seeds**, médiane
+10,75 tick, sign p = 2,4e−4. Sur les deux voies, P4.9 avait mesuré +13,75 sur 12/12. Ce que le petit pas ne fait
pas, c'est PROTÉGER : le bras reste ERODE, il ne repasse jamais la barre scellée. Et l'interaction est réelle : à
pas identique 0,004, couper le TD AGGRAVE l'érosion (P4.9 `b_lr`, les deux voies : −14,0, 9/12, NEUTRE ; ici
`b_eplr`, épisodique seul : −19,0, 11/12, ERODE) alors que le mouvement DIMINUE de moitié (0,121× contre 0,064×).
Fait non expliqué, publié.

⚠️ **Ce que le run ne dit PAS, et que la première rédaction affirmait à tort.** L'érosion n'est PAS « maximale par
unité de mouvement chez les plus petits pas » : ce rapport n'est pas interprétable ici, son numérateur étant
plafonné par `S_a − plancher` alors que son dénominateur varie de 20×. Sur la mesure NON normalisée, l'érosion est
monotone CROISSANTE en mouvement sur les quatre bras (5,4 % → −12,25 ; 6,4 % → −19,0 ; 71 % → −27,75 ;
100 % → −28,25 ; Spearman −1,000 sur les médianes, 64/72 paires appariées concordantes), et elle SATURE — 20×
moins de mouvement ne divise l'érosion que par 2,3. **Direction contre amplitude n'est donc pas tranché par ce
run**, qui ne fait varier la direction à amplitude appariée dans aucun bras : c'est P4.18.

## Portée (hedges)

* **HYPOTHÈSE, non testée ici** : la politique DAgger tiendrait sur une crête que la DIRECTION des pas de ce
  crédit lui fait quitter. Le run est également compatible avec « le bassin est fragile à toute perturbation de
  cette amplitude ». Le contrôle qui tranche est bon marché et nommé : **P4.18**, perturbation ALÉATOIRE de W
  appariée en `Σ|ΔW|` à chaque bras (5,4 %, 6,4 %, 71 %, 100 %), sans aucun apprentissage, phase 2 seule,
  ~15 min. Si le bruit apparié érode autant, « le crédit détruit » devient « toute mise à jour de cette amplitude
  détruit », et un remède d'ancrage (P4.19) répondrait à la mauvaise question.
* **Le contraste `b_const` contre `b_zero` de P4.9 n'est pas conclu.** Il est appariable (mêmes 12 seeds, `S_a`
  identique) mais il n'était PAS dans la règle scellée : calculé après coup, la différence appariée vaut −12,75
  sur 10/12, sign p unilatéral 0,019 — au-dessus de l'alpha par cellule que ce run s'impose (0,00417, Bonferroni
  sur 12 cellules). Il est en outre confondu sur deux axes mesurés : à `reward_scale = 0` la perte épisodique vaut
  exactement zéro (les 2,5 % de `b_zero` sont du TD pur, quand les 5,4 % de `b_const` mélangent les deux voies),
  et les amplitudes ne sont pas appariées (facteur 2,15× sur chacun des 12 seeds).
* **`resurrections` : un ordre de grandeur entre bras, PAS une régularité.** const 65,5 (5–328) · eplr 16,5 ·
  full 10 · tdonly 8 ; P4.9, bassin quasi intact sous crédit nul : 179. L'ordre suit grossièrement l'érosion
  (ρ = 0,80 sur 4 points, p = 0,200) mais il est déjà inversé à sa paire basse (`tdonly`, moins érodé, a MOINS de
  morts que `full`), tombe à ρ = 0,597 en poolant les neuf bras de P4.9 et P4.16, et **ne se réplique pas à
  l'unité DÉCLARÉE** : à travers les 12 seeds, la corrélation est négative sous S brut dans les quatre bras
  (−0,02 à −0,49) et de signe mixte sous l'écart apparié. Ne pas en tirer de mécanisme. Le bassin DAgger reste
  une politique de survie MORTELLE (200 ticks) qui se fait tuer dans une arène de 12 clones immortels ;
  non expliqué, publié.
* Vu en mesurant, non exploité : `b_const` produit les queues les plus longues du run (151, 150, 151, 186, 200)
  alors que le bassin gelé plafonne à 129 — il baisse la médiane tout en ÉPAISSISSANT la queue haute.
* Réserve E6 héritée (phase d'apprentissage immortelle, test mortel) ; une lignée de bassin, un monde, un régime,
  200 ticks de test ; `b_full` importé pour 11/12 seeds.

## Coût — le temps MUR n'est pas le coût (mesuré, P2.78)

Unité mesurée sur le seed 2026 sous charge DÉCLARÉE (deux agents en worktrees, sessions parallèles) : gelé 1 s,
complète **815 s** (713 s en P4.9, 283 s en P4.8 pour la MÊME cellule bit-identique — la charge est mesurée par la
réplication elle-même), TD seul 645 s, constante 188 s, épisodique 0,004 435 s. Projeté 45 684 s (12,7 h,
`b_full` importé, marge ×3, sur 48 cellules).

Réel : **70 223 s de mur = 19,5 h**, contre **15 540 s de temps CPU du processus = 4,3 h**. Les dénominateurs sont
recomputés par le runner (`cost_cells`, calibré à réponse connue) et non reconstruits à la main : 60 cellules
déclarées, dont **11 importées** (leur `elapsed_s` est une durée recopiée de P4.4, non dépensée ici — sommer les
60 donne 22,2 h, soit plus que le mur total) ; **49 réellement calculées**, dont **2 hors échelle**
(`b_tdonly`/2031 : 31 842 s ; `b_eplr`/2036 : 18 099 s, machine suspendue ou contention). Les **47 cellules
restantes** coûtent 20 268 s, soit **431 s par cellule**, DANS la projection. Début 2026-09-22 21:48, fin
2026-09-23 17:19 — ⚠️ pour CE run, ces deux horodatages sont DÉRIVÉS (de `elapsed_total_s` et de la date d'écriture
du fichier, cohérents à 0,3 s) et non publiés par le runner ; le champ a été ajouté au runner dans le commit de
clôture, les runs suivants les publient. C'est cette dissymétrie mur/CPU qui justifie de faire porter la garde de
queue sur le CPU (P2.78) : un budget en temps mur est franchi par une machine qui dort, pas par un calcul.

## Ce que ça change

* **L'érosion EXIGE un signal non nul** (P4.9 `b_zero` : 1999 mises à jour TD, 2,5 % du mouvement, NEUTRE, −0,75
  sur 8/12). Ce signal une fois non nul, ni son SIGNE (P4.9 `b_neg`), ni son contenu informatif (ici `b_const`,
  sous la réserve d'interprétation ci-dessus), ni la VOIE (ici `b_tdonly`, P4.9 `b_tdoff`) ne changent la CLASSE.
  **Le PAS, lui, module, et il interagit avec la voie** — c'est la seule dépendance quantitative établie de l'arc,
  et elle n'est pas un levier suffisant (le bras reste ERODE).
* **Le prochain run n'est pas un remède, c'est un contrôle** : P4.18, bruit apparié en mouvement, ~15 min. Il
  décide entre « mauvaise direction » et « crête fragile », et l'ancre au bassin (P4.19 : imitation / KL vers la
  politique DAgger pendant le crédit) ne se scelle qu'après lui.
* Pour P4.11 / P4.17 (trace TD(λ), session b0) : le TD par tick seul suffit à amener le bassin au plancher à
  lr 0,04 ; mais le pas module, donc une trace évaluée à un pas où l'érosion est moindre n'est pas évaluée dans le
  même régime.
* Le pari C ([[EDR-S2-CREDIT-RETENTION]]) se précise une troisième fois : warm-start + ce crédit n'est pas un
  régime, quelle que soit la voie ou le contenu du signal.

Converge [[EDR-S2-CREDIT-ABLATION]] (signal quelconque), [[EDR-CALIB-LEARNER]] (le même apprenant apprend une
tâche linéaire à cette dose : il n'est pas inerte, il pousse), [[EDR-175]] (érosion sous r·P : ici l'érosion ne
dépend plus du contenu de r), REF-EXPERIMENT-PREFLIGHT (question 1 : le contrôle qui manque est nommé avant
d'être lancé ; et un contraste lu à 96-98 % de saturation ne peut pas classer ce qu'il compare).
