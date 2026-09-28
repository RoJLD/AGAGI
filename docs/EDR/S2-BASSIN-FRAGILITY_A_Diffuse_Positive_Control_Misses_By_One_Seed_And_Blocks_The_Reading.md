---
id: EDR-S2-BASSIN-FRAGILITY
type: EDR
title: "P4.18 — verdict scellé INDETERMINE_INSTRUMENT (branche 7) : le contrôle positif de l'issue FRAGILE, un bruit gaussien DIFFUS sur toute la matrice W (1,0 × ‖W_bassin‖₁, dont un tiers dans des colonnes inertes), érode la survie de −8,75 ticks en médiane — hors de sa bande de tirage — mais sur 10 seeds sur 12, un de moins que le seuil. La lecture qu'il bloque est publiée comme un CONTREFACTUEL, sans valeur de verdict, et « crête fragile ou direction du crédit ? » reste OUVERTE. Leçon : un contrôle positif doit vivre dans le RÉGIME du sham qu'il protège, et sa puissance se calibre avant le sceau"
status: active
verdict: INDETERMINE_INSTRUMENT
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
review: docs/reviews/2026-09-28-S2-BASSIN-FRAGILITY_The_Positive_Control_Of_FRAGILE_Misses_B.md
extends: [EDR-S2-CREDIT-ABLATION-2, EDR-S2-CREDIT-ABLATION, EDR-S2-CREDIT-RETENTION, EDR-WARM-003]
---

> **Le harnais porte des défauts connus, rejoués À L'IDENTIQUE parce que ce sont eux qui ont produit les poids
> publiés ; leur effet sur ces mesures est INCONNU.** (1) **E34** (P2.132) : dans la cohorte immortelle de phase 1,
> la résurrection intra-tick remet le corps en fin de liste sans reconstruire la population torch, donc après une
> mort jusqu'à 12 − p slots de W pilotent un autre corps (les douze quand le premier corps meurt) — le ΔW testé ici
> est celui du crédit TEL QU'IL A TOURNÉ, brassage compris ; `S_c`, la constante publiée de P4.4 qui sert à la
> saturation, porte le même brassage. (2) **E5** ([[EDR-INFRA-001]], P2.64 épinglé, correction P2.138) :
> `TorchPopulationModel.forward` rend une VUE de l'état récurrent H, dans laquelle le MONDE écrit (−0,1 sur le
> logit de la dernière action, et le vote social qui réécrit la ligne entière). (3) Un troisième écrivain de H,
> nommé par la règle : chaque mort de phase 2 reconstruit la population torch et remet H à zéro pour tous les
> survivants ; médiane de 10 reconstructions sous `noop` comme sous `pos` (revue, P10.d) — pas différentiel entre les
> deux bras de la branche 7.
>
> **La lecture bloquée publiée plus bas est CONTREFACTUELLE et n'a AUCUNE valeur de verdict** : elle est obtenue
> en rejouant la fonction scellée sur des lignes MODIFIÉES à la main (deux valeurs de `pos` forcées), jamais sur le
> run ; elle ne se cite pas hors de la phrase qui le dit (section « La lecture que la branche 7 bloque »).
>
> **NON DÉFENDU contre le pas** (exigé en tête par la règle, clause_E19) : la garde E19 de la paire b_tdoff / b_eplr
> est ILLISIBLE, comme la règle le savait avant le sceau (b_tdoff saturé, médiane 1,017). Sans objet pour le verdict,
> mais aucune dépendance au pas n'est tranchée par ce run.

## Question et règle

[[EDR-S2-CREDIT-ABLATION-2]] a laissé une question : aucun bras de P4.16 ne fait varier la DIRECTION des pas du
crédit à amplitude appariée. Le bassin DAgger de [[EDR-WARM-003]] est-il une **crête fragile** à toute perturbation
de W de l'amplitude NETTE du crédit — le crédit n'a alors rien de spécial —, ou est-ce la **direction** des pas du
crédit qui le détruit ?

Règle `docs/preregistrations/S2-BASSIN-FRAGILITY.json`, **sceau `d29d7934b3a252b10c9e3bb4e6b459d538a9fb30440515db4bc092d183ff5bd4`**,
`reviewed_by` `docs/reviews/2026-09-26-S2-BASSIN-FRAGILITY.v9.md`, scellée sous une règle d'arrêt déposée d'avance
(`docs/reviews/2026-09-26-S2-BASSIN-FRAGILITY.regle-d-arret.md`) après neuf revues adversariales. Code : **sha
`afa4dac6f759d55439653573129a896480f4f52c`** (`tools/evo_runs/s2_bassin_fragility.py`).

Dispositif, en bref :
- **Phase 1 rejouée** pour six bras de crédit de P4.9/P4.16 (b_full, b_tdonly, b_const, b_eplr, b_zero, b_tdoff),
  sur les douze seeds 2026-2037 : cohorte immortelle de 12 clones du bassin, 2000 ticks sous crédit. Le rejeu doit
  égaler le publié AU BIT (chemin `dW_abs_sum`, 12 âges, dose). Les poids appris sont persistés.
- **Phase 2 mortelle** (200 ticks, poids gelés) sur 12 clones FRAIS du bassin, sous : `noop` (W_bassin), `transplant`
  (W_bassin + ΔW), `sign` (W_bassin + s ⊙ |ΔW|, signes tirés sur le SUPPORT du crédit : même L1, L2, L∞ coordonnée
  par coordonnée — c'est le sham que lit la branche 10), `iso` (gaussien apparié en L1 par agent, secondaire),
  l'échelle `sign_x2` / `sign_x4` et `sign_commun` (descriptifs, hors famille), et deux contrôles : `eps` (le sham sign
  du ΔW de b_full à 1e-3 de son amplitude) et `pos` (un gaussien à 1,0 × ‖W_bassin‖₁ par agent, sur TOUTE la
  matrice). Cinq tirages par (seed, bras, sham).
- **Famille de 15 contrastes**, seuil 11/12 (queue binomiale 0,00317 ≤ 0,05/15) et δmin 5 ticks — un seuil ABSOLU
  hérité de P4.4, où il valait ≈ 15 % du bassin (règle). Branches dans l'ordre imposé 1 → 8, 9a → 9b, 10, 10bis, 11.

## Verdict scellé : INDETERMINE_INSTRUMENT (branche 7)

Les branches 1 à 6 sont passées : n = 12 seeds complets ; le no-op rend les 12 âges publiés au bit sur les douze
seeds ; les 72 rejeux de phase 1 sont bit-identiques au publié (`repl_*` vrai partout) ; chaque transplant rend les
âges des objets appris (`transplant_ok_*` vrai partout) ; l'appariement L1 tient (erreur relative maximale 2,1e-5
sur tous les tirages, tolérance 1 %) ; `pos` a reçu exactement sa dose (L1 par agent = ‖W_bassin‖₁ sur ses 60
tirages, revue P5.d).

**La branche 7 arrête la lecture.** Le contrôle positif de l'issue FRAGILE, `pos`, doit être ERODE contre `S_a` :
négatif sur ≥ 11/12 seeds ET médiane ≤ −5. Mesuré :

| seed | 2026 | 2027 | 2028 | 2029 | 2030 | 2031 | 2032 | 2033 | 2034 | 2035 | 2036 | 2037 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S_a | 31,5 | 35,5 | 44,5 | 39,0 | 42,5 | 35,5 | 36,0 | 36,0 | 50,0 | 42,0 | 17,0 | 26,5 |
| S_pos | 22,0 | 31,5 | 26,5 | 33,0 | 27,5 | 32,5 | 23,0 | 28,0 | 36,0 | 25,0 | 23,5 | 32,0 |
| S_pos − S_a | −9,5 | −4,0 | −18,0 | −6,0 | −15,0 | −3,0 | −13,0 | −8,0 | −14,0 | −17,0 | **+6,5** | **+5,5** |
| S_tr full | 7,0 | 7,5 | 8,0 | 7,0 | 9,5 | 8,0 | 8,0 | 7,5 | 9,0 | 8,5 | 8,0 | 9,5 |
| S_c (P4.4) | 8,0 | 7,5 | 8,5 | 8,5 | 7,0 | 7,0 | 7,5 | 7,0 | 8,0 | 7,0 | 7,0 | 8,0 |

Médiane −8,75, **hors de sa bande de tirage** (4,5 ticks, bootstrap échangeable publié par le JSON), mais **10/12
négatifs** : il manque UN seed au compte. L'échec tient au compte des signes, pas au bruit de tirage. `pos` est
classé NEUTRE, et le verdict scellé est **INDETERMINE_INSTRUMENT** : la règle ne rend aucune lecture, **la question de
P4.18 n'est pas tranchée.**

**Ce que ce verdict ne dit PAS.** La règle écrivait, avant le run, qu'un `pos` non érodé « prouve que cet instrument
ne sait pas voir une érosion par perturbation ». Les données de ce même run démentent cette glose (revue P1.a,
P5.a) : le sham `sign` — un tirage aléatoire lui aussi — érode sous le critère scellé (ERODE contre `S_a`) sur cinq
bras sur six (full, tdonly, tdoff 12/12, médianes −26,25 / −24,5 / −26,0 ; const et eplr 11/12, −10,75 / −14,5 ; b_zero
NEUTRE). L'instrument voit donc une érosion par perturbation. Ce qui a manqué est UN contrôle, dont la géométrie
n'est pas celle du sham qu'il protège : `pos` est un gaussien diffus sur toute la matrice, alors que la branche 10 lit
un tirage de signes restreint au support de ΔW ; et le gaussien est justement la géométrie qui érode le moins dans ce
run (`iso`, à la dose des bras : médiane 0,0, 1 à 4 seeds négatifs sur 12 selon le bras). En outre, 34 % de la masse
de `pos` tombe dans les colonnes des 59 nœuds d'ENTRÉE, que l'observation réécrit à chaque pas (0,343-0,344 sur les
tirages rejoués ; le crédit n'y met RIEN) : la dose ACTIVE de `pos` vaut ≈ 0,66 × ‖W_bassin‖₁, pas 1,0 (revue P8.a).

**La lecture que la branche 7 bloque, publiée pour ce qu'elle est.** Rejouée par injection sur les lignes publiées
(fonction scellée `fragility_verdict`, aucun monde), la même règle rend INDETERMINE_INSTRUMENT à l'identique ; si l'on
force seulement `S_pos` à `S_a` − 5 aux seeds 2036 et 2037, elle rend — lecture CONTREFACTUELLE, sans valeur de verdict — LU / FRAGILE : FRAGILE sur
full, tdonly, const, eplr, tdoff, INOFFENSIF sur b_zero (revue P5.b, re-mesuré par l'auteur). Les lectures par bras
que le JSON publie (`par_bras.<bras>.sign.lecture`) sont les mêmes. **Elles n'ont AUCUNE valeur de verdict** : la règle
s'arrête à la branche 7, et ce record ne les lit pas. Elles sont dites pour que le lecteur sache que l'issue bloquée
est exactement celle que le contrôle défaillant protégeait — et pour la conception de toute règle suivante.

Ce n'est **pas** un quasi-positif : avec une probabilité de 10/12 par seed (la fréquence observée), `pos` franchirait
11/12 environ 38 fois sur 100 (revue P4.c) — le contrôle avait plus de chances d'échouer que de passer, et personne ne
l'avait chiffré avant le sceau ; aucune survie sous `pos` n'avait été observée au pré-scellement (règle,
`prevol_obligatoire` (2)). Voir « Leçon ».

**Plancher ou resserrement ?** Les deux seeds positifs sont les deux plus bas en `S_a` (17,0 et 26,5). Un PLANCHER
(un bassin déjà bas ne peut plus baisser, classe E14) changerait la leçon. Données, sans conclusion : (i) sur ces deux
seeds, la survie PEUT descendre bien plus bas — les greffes y tombent à 6,0-9,5 (b_full 8,0 et 9,5 ; S_c 7,0 et 8,0) ;
(ii) leurs écarts +6,5 et +5,5 restent DANS la bande de tirage propre à chaque seed (7,5 et 8,0 ; même au seed 2026,
−9,5 est dans sa bande de 9,5 — revue P6.c) : un signe lu seed par seed ne départage rien ; (iii) sur les douze seeds,
`S_pos` varie de 22,0 à 36,0 (écart-type 4,4) quand `S_a` varie de 17,0 à 50,0 (écart-type 8,3), et suit à peine
`S_a` (corrélation de rang 0,28) ; l'écart S_pos − S_a a une corrélation de rang −0,85 avec `S_a`, un chiffre qui
mêle l'effet et l'artefact de toute différence Y − X rapportée à X. La forme d'ensemble ressemble plus à un
RESSERREMENT des survies sous le bruit qu'à un blocage au plancher — observation à douze points, hors règle, non lue.

## Ce qui est publié hors verdict (descriptif, aucune lecture)

La règle publie toutes les grandeurs « quel que soit le verdict » (`regle_de_lecture_continue`). Elles sont
reproduites ici **sans être lues**. Médianes sur les 12 seeds, recalculées depuis les lignes du JSON (jamais
recopiées du bloc `verdict`) ; la bande du contraste `c` est celle que le JSON publie (quantile 0,975 du bootstrap
échangeable) :

| bras | S_tr | S_tr − S_a | S_sign | c = sign − tr | bande de c | S_iso | S_sign_x2 | S_sign_x4 | net / agent | résurrections |
|---|---|---|---|---|---|---|---|---|---|---|
| full | 8,00 | −28,25 (12/12 < 0) | 10,75 | +2,50 (12/12 > 0) | 1,50 (hors) | 36,00 | 10,00 | 9,25 | 95,78 | 10,0 |
| tdonly | 8,50 | −27,75 (12/12) | 12,25 | +3,50 (12/12) | 1,75 (hors) | 35,50 | 10,00 | 9,50 | 63,30 | 8,0 |
| const | 23,25 | −12,25 (11/12) | 25,50 | +2,50 (8/12) | 3,75 (DEDANS) | 36,00 | 20,25 | 17,00 | 28,51 | 65,5 |
| eplr | 17,00 | −19,00 (11/12) | 21,00 | +3,50 (12/12) | 3,51 (DEDANS) | 35,75 | 15,25 | 13,50 | 14,48 | 16,5 |
| zero | 33,25 | −0,75 (8/12) | 35,50 | +1,25 (8/12) | 1,75 (DEDANS) | 35,75 | 35,00 | 25,75 | 2,95 | 179,0 |
| tdoff | 7,50 | −29,00 (12/12) | 11,00 | +3,50 (12/12) | 1,25 (hors) | 36,00 | 10,00 | 9,00 | 38,77 | 3,5 |

`S_a` médiane 36,0 ; `S_c` (constante héritée de P4.4) 7,5. La bande est de niveau NOMINAL, pas conservatrice : sa
couverture d'un contraste nul, mesurée sur la bande exécutée, tombe sous 0,975 dans 8 des 10 régimes échangeables
calibrés, jusqu'à 0,926 (`results/s2_bassin_fragility_calibration_bande.json`) — un « hors bande » y est faux 4 à 7 %
du temps. Contrôle `eps` : `S_eps` = `S_a` sur 12/12 seeds (inerte ; le contrôle de DIRECTION 9b reste NON ÉPROUVÉ par
construction, comme la règle le disait). Garde E19 : exécutée, ILLISIBLE (saturation de b_tdoff 1,017), fermeture
0,417 publiée sans lecture. Pas effectif : les deux bras épisodiques seuls (b_eplr, b_tdoff) publient leur pas
nominal mesuré sur l'optimiseur (0,004 et 0,04) mais laissent `lr_effective_per_agent` vide ; le pas réel par agent
(lr/B, SGD à perte moyennée sur B = 12) vaut 0,00033 et 0,0033 (revue P7.c ; rapport ×10 inchangé, dette inscrite).
**Vote social** : sur 2004 phases 2, 4 ticks avec réécriture de logits, TOUS sous `pos` (2 phases sur 60 : seed 2030,
1 tick ; seed 2034, 3 ticks), AUCUN dans les 1944 autres phases (revue P10.b, re-compté par l'auteur). C'est le chemin
que la règle attribuait en propre à `pos` (il verse de la masse sur les nœuds 77-78 qui déclenchent le vote, ΔW n'y
touche pas) ; il n'a pas tiré aux seeds 2036 et 2037.

**Hypothèse, hors famille, NON TESTÉE.** Sur les cinq bras dont le transplant érode, le sham `sign` reproduit une
grande part de la perte de la greffe rapportée à `S_a` (médiane par seed du rapport des pertes : 0,93 full, 0,87
tdonly, 0,84 const, 0,79 eplr, 0,89 tdoff), tandis que le gaussien apparié en L1 (`iso`) n'érode pas (médiane 35,5 à
36,0 pour S_a 36,0). Cela évoquerait une érosion portée par le SUPPORT et l'amplitude par coordonnée de ΔW — les
colonnes de W que la perte écrit — plutôt que par son signe. Rien de cela n'est établi : (i) la branche 10 n'a pas
été atteinte ; (ii) lu à l'autre échelle, le sham survit nettement PLUS que la greffe sur les bras au plancher (c/S_tr
médian 0,30 full, 0,44 tdonly, 0,47 tdoff, 12/12 positifs) — δmin (5 ticks, hérité de P4.4) y vaut 59 à 67 % de la
survie sous greffe (revue P4.d), et « presque autant » dépend de l'échelle choisie ; les contrastes de const, eplr et
zero sont DANS leur bande ; (iii) `iso` place 94-95 % de sa masse hors de ces colonnes (règle,
`ecarts_au_design_du_backlog` (3)), si bien que « iso n'érode pas » confond support et amplitude par coordonnée ; (iv)
entre les six bras, l'érosion de la greffe suit le nombre de morts de phase 1 (corrélation de rang 0,943) plus
fidèlement que l'amplitude nette (−0,771) — six points non indépendants, mais la LÉTALITÉ, qui fait aussi le brassage
d'E34, est confondue avec toute lecture par bras (revue P7.b, classe E15) ; (v) E34 et E5 (en tête) pèsent sur ΔW et
sur la phase 2. Une telle hypothèse ne se teste que par une NOUVELLE règle scellée.

## Grandeurs de la DV scellée : où chacune est publiée

Toutes les grandeurs que nomme `dv_primaire` sont mesurées et publiées PAR SEED dans les lignes du JSON (`rows`, clés `<grandeur>_<bras>` pour <bras> ∈ {full, tdonly, const, eplr, zero, tdoff}) ; ce record en donne les médianes, sans les lire :
- `S_a`, `S_pos`, `S_eps` : tableau du verdict et contrôles ; `S_c` (héritée de P4.4) : même tableau.
- `S_tr_<bras>`, `S_sign_<bras>`, `S_iso_<bras>`, `S_sign_x2_<bras>`, `S_sign_x4_<bras>`, `c_<bras>` (= `S_sign_<bras>` − `S_tr_<bras>` apparié par seed), `net_<bras>` (net par agent), `resur_<bras>` : tableau « Ce qui est publié hors verdict ».
- `S_sign_commun_<bras>` (descriptif, hors famille), médianes : full 11,25 ; tdonly 12,00 ; const 27,75 ; eplr 21,00 ; zero 35,75 ; tdoff 11,25.
- `path_<bras>` (chemin `dW_abs_sum`, SOMME sur les 12 agents — ≈ 101 par agent pour b_tdoff), médianes : full 15 011,7 ; tdonly 11 034,2 ; const 847,6 ; eplr 915,6 ; zero 376,8 ; tdoff 1 215,2.
- `verifier_seed` (branches 2, 4, 5 et 6 vérifiées à CHAQUE seed dès qu'il est calculé, écrit sa mesure puis lève en nommant chaque échec) : `cells/<seed>/verification_en_cours` vaut une liste VIDE sur les 12 seeds — aucun échec nommé, ce que l'agrégat confirme (branches 1 à 6 passées).

## Prédictions écrites avant le run, confrontées

| prédiction (règle, `predictions_avant_le_run`) | observé |
|---|---|
| `pos` : ERODE attendu | **NEUTRE** (10/12, médiane −8,75 hors bande) — la prédiction ÉCHOUE sur le compte, et c'est elle qui porte le verdict |
| `eps` : ni ERODE ni CRÊTE | inerte, 12/12 égal au no-op |
| `iso` moins érodé que `sign` sur tous les bras | vrai sur les six bras (descriptif) |
| DIRECTION le plus probable ; FRAGILE possible aux grands nets | non lu (voir « La lecture que la branche 7 bloque » : contrefactuelle, sans valeur de verdict) |
| b_zero INOFFENSIF attendu | non lu (même renvoi) |
| garde E19 : illisible de façon CERTAINE | illisible |

## Déroulé, coût et charge

**Première tentative, 2026-09-26 (« coupe 1 »).** Lancée à 19:55 sur batcave, 6 processus ouvriers (la reprise en a
pris 3, décision robla), elle a été COUPÉE par la garde de coût au départ : unité du premier seed 2052,6 s CPU, contre
un seuil de 2000 s (72 000 s / 12 seeds / marge 3). Charge relevée pendant la cellule d'unité, plusieurs sources :
tests INFRA-NEXUS (3 min 31 s) puis commit 42f5768e (20:05:35) et fusion 0a73a0b2 (20:07:01) ; crochet de la session
E34 de 20:07:03 à 20:13:36 (porte 15, 8 pytest de mutation) ; export OpenAPI du frontend 19:57-20:00 ; synchro
episodic-memory née à 20:15:09 (environ 14 cœurs) ; Bitdefender et moteurs de rendu de VS Code. Charge par cellule :
39 % au départ, 58 à 99 % à la fin. Agrégat de cette tentative : `results/s2_bassin_fragility_coupe1.json`.

**Transparence du lecteur** : l'agrégat de la coupe 1 contenait les survies du seed 2026 (écrit AVANT la garde, par
conception). L'auteur de ce record les a vues avant la reprise. La reprise ne pouvait rien changer : règle scellée,
règle d'arrêt, reprise DÉCLARÉE (même sceau, même budget, même marge, décision robla via Master 2), et le seed 2026
est ressorti identique (ci-dessous).

**Reprise, 2026-09-28.** Lancée par robla depuis science-prep (`runs/p418/p418_reprise.py`, hors git) : elle refuse de
partir si HEAD ≠ afa4dac6, si l'arbre suivi est sale, ou si des artefacts de reprise existent. Elle attend 120 s de
calme continu. Seuil initial CPU < 15 % ; relevé à 30 % à 15:39 (même jour), parce que 15 % était sous le plancher
d'une machine au repos (4,9 à 6,9 cœurs sur 22, soit 22 à 31 %, provenance de `COEURS_EXTERIEURS_LIBRE_MAX` = 8,0 cœurs
dans `tools/cost_guard.py` — une valeur PROVISOIRE, non calibrée comme certificat). **Départ à 16:50:12** (CPU 14,7 %,
10 processus python), fin à 18:38:05, **6470 s de mur**, rc 0.

Coût, depuis le bloc `cost` et les cellules du JSON :

| seed | CPU cellules + phases 2 | seed | CPU cellules + phases 2 |
|---|---|---|---|
| 2026 | 1863,4 + 63,6 = **1927,0** | 2032 | 1168,5 + 83,7 = 1252,2 |
| 2027 | 1666,2 + 94,3 = 1760,4 | 2033 | 1310,3 + 111,7 = 1422,0 |
| 2028 | 1545,3 + 96,6 = 1641,9 | 2034 | 1214,7 + 117,3 = 1332,0 |
| 2029 | 1119,4 + 111,3 = 1230,7 | 2035 | 1121,9 + 100,4 = 1222,3 |
| 2030 | 1806,8 + 99,0 = 1905,8 | 2036 | 1523,2 + 79,7 = 1603,0 |
| 2031 | 1194,0 + 96,2 = 1290,2 | 2037 | 1440,0 + 85,2 = 1525,2 |

Unité du premier seed : **1927,0 s**, sous le seuil de 3,7 % ; projection 69 372 s pour un budget de 72 000 s.
Médiane par seed 1473,6 s (min 1222,3, max 1927,0). **Le premier seed est le plus cher des douze.** Total 18 112,6 s
CPU, soit 25 % du budget ; la garde PENDANT le run (CPU cumulé contre 72 000 s, sans la marge ×3) n'a jamais été près
de couper. Charge parent : 15,8 % au départ, 45,2 % à la fin. Charge par seed publiée dans le JSON.

**Ce que la reprise corrige dans le récit de la coupe 1.** L'unité du seed 2026 vaut 1927,0 s machine calme au
départ, contre 2052,6 s sous forte charge : la charge ajoutait ≈ 6,5 %. La coupe du 26 ne venait donc pas d'une
contention seule : la marge de queue ×3 de `project_cost` (voulue, documentée pour une unité mesurée sur un smoke)
était appliquée à une unité mesurée sur un seed COMPLET du vrai run, intrinsèquement à 96 % du seuil — et, on le voit
maintenant, sur le seed le plus cher des douze. La charge l'a fait basculer. Le « +45 % » cité le 26 portait sur la
seule cellule b_full sous forte contention (551 s contre 381 s), pas sur un seed. Registre : E12, amendée.

**Seed 2026, reprise contre coupe 1.** Les six génomes `.npz` sont IDENTIQUES au bit (sha256). Dans les JSON de
cellule et de seed, seules diffèrent des feuilles de temps, de charge et de pid (`cpu_percent_1s`, `python_procs`,
`t`, `cpu_s`, `wall_s`, `pid`, `replay_cpu_s`, `replay_wall_s`, `cells_cpu_s`) ; toutes les valeurs scientifiques sont
identiques. Le CPU par cellule a baissé d'environ 7 % (b_tdonly 499,0 → 464,8 s, b_zero 154,5 → 144,1 s).

**Provenance** : le JSON publie `git_sha` afa4dac6 et `dirty = true`. La saleté vient des fichiers NON SUIVIS
produits par le run lui-même (`results/s2_bassin_fragility.json`, écrit après le premier seed, et l'agrégat de la
coupe 1) : `git status --porcelain --untracked-files=no` était vide au départ (contrôle de la reprise) et l'est encore.
`provenance()` compte l'untracked comme sale : un run qui écrit son agrégat en cours de route se déclare donc toujours
sale — dette inscrite au backlog.

## Lieu : batcave, et pourquoi

La règle exige que chaque rejeu égale le publié AU BIT (branche 4). Témoin de lieu, 2026-09-26, cellule b_zero seed
2026, même sha afa4dac6 : sur nexus (image `sha256:7c860b30fbd45348f937c13af278d57f1bd0a90633866004a01eeafc6d0e3de8`,
torch 2.6.0+cpu, Linux) à 2 et à 16 threads, les W sont identiques entre eux au bit mais diffèrent de batcave (torch
2.6.0+cu124, Windows) au dernier bit (écart max 2,4e-7) ; le chemin `dW_abs_sum` y diffère du publié (sommes réduites
dans un autre ordre), les 12 âges et la dose sont identiques. En `remote local` sur batcave, tout égale le publié au
bit. Le run a donc tourné sur batcave. Évidence : `results/s2_bassin_fragility_temoin_lieu.json` (comparaisons,
sha256 des génomes et des MANIFEST ; l'image n'y figure que par son digest).

## Leçon (conception)

1. **Un contrôle positif doit vivre dans le RÉGIME du sham qu'il protège, et sa puissance se calibre avant le sceau.**
   Deux défauts, que ce run sépare. (a) RÉGIME (revue P5.a, P8.a) : `pos` est un gaussien diffus sur toute la
   matrice, dont un tiers tombe dans des colonnes inertes, alors que la branche 10 lit un tirage de signes sur le
   support de ΔW ; le même run montre que le gaussien est la géométrie qui érode le moins, et que le tirage sur le
   support érode — un contrôle positif hors du régime lu protège une autre question que celle posée. (b) PUISSANCE
   (revue P4.c) : jugé sous le critère de la famille (11/12, δmin 5), sans qu'une seule survie sous `pos` ait été
   mesurée ; à la fréquence observée (10/12 par seed) il passait ≈ 38 fois sur 100. La bande de tirage, elle, avait
   été calibrée par injection ; le contrôle positif ne l'a pas été. Son amplitude était décrite par un chiffre de
   conception (« 24 à 718 fois le déplacement des bras », seed 2026 au pré-scellement) : mesurée sur ce run, elle va
   de 25,5 à 826,7 fois (médianes par bras, ‖W_bassin‖₁ = 2442,8) et ≈ 17 à 545 fois en dose ACTIVE (revue P5.c,
   P10.a). Toute règle suivante calibre son contrôle positif dans le régime du sham lu, sur la dose active, par
   injection, AVANT le sceau.
2. **Une unité de coût mesurée sur un seed COMPLET n'appelle pas la marge de queue d'une unité de smoke**, et le
   premier seed n'est pas un seed typique (ici le plus cher). Leçon reprise dans le brouillon de TD-STEP-PILOT-R3
   (P4.19) : marge 1,5 sur des unités par bras mesurées sur de vraies cellules, seuil à ≈ 2,5 × l'attendu.

## Suite

Aucune reprise, aucun `-bis` : le verdict est gravé tel quel. Retester la fragilité du bassin demande une NOUVELLE
règle scellée, dont le contrôle positif vit dans le régime du sham lu et a sa puissance calibrée par injection AVANT
le sceau (comme la lecture de TD-STEP-PILOT-R3). La lecture bloquée ci-dessus et l'hypothèse descriptive y seraient
des questions neuves, jamais une relecture de ce run. **La décision d'une telle suite revient à robla**, après la
revue de ce record.

## Évidence

Tous les chemins `results/` ci-dessous sont suivis par git dans le commit qui porte ce record.

- `results/s2_bassin_fragility.json` — agrégat de la reprise (lignes, cellules, verdict, coût, provenance).
- `results/s2_bassin_fragility_coupe1.json` — agrégat de la première tentative, coupée.
- `results/s2_bassin_fragility_temoin_lieu.json` — témoin de lieu.
- `results/s2_bassin_fragility_calibration_bande.json` — calibration de la bande de tirage.
- `results/s2_bassin_fragility_sonde_conception.json` — mesures de pré-scellement.
- Génomes appris : `results/s2_bassin_fragility_genomes/` (72 fichiers `.npz`, HORS git, `results/*` ignoré) ; le
  sha256 de chacun est publié dans le JSON agrégé, à `cells/<seed>/arms/<bras>/genomes`.
- Journal de la reprise : `runs/p418/p418_reprise.log` (hors git ; départ et fin cités ci-dessus).
- Revue adversariale : `docs/reviews/2026-09-28-S2-BASSIN-FRAGILITY_The_Positive_Control_Of_FRAGILE_Misses_B.md`
  (38 critiques, 15 confirmées — passage INDISCRIMINANT, toutes re-mesurées par l'auteur ; voir son addendum).
