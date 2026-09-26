# Revue adversariale — S2-BASSIN-FRAGILITY v8

- **Cible** : `C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/S2-BASSIN-FRAGILITY.v8.json` (pré-inscription, brouillon non scellé)
- **Date** : 2026-09-26
- **SHA** : `75582d6d05a588ce345f3a72d6226b8ea4a5468b` (worktree science-prep)

## Résultat des TÉMOINS

| témoin | statut | code | critiques recevables | fichier de critiques |
|---|---|---|---|---|
| EDR-GRAB-COST-1828371 | RETROUVE | 0 | 6 | `scratchpad/refutateur_v8/critiques-EDR-GRAB-COST-1828371.json` |
| S2-BLIND-CHAMPION-42e9357 | RETROUVE | 0 | 7 | `scratchpad/refutateur_v8/critiques-S2-BLIND-CHAMPION-42e9357.json` |
| EDR-RETAIN-COMPOSE-4204f8f | RETROUVE | 0 | 7 | `scratchpad/refutateur_v8/critiques-EDR-RETAIN-COMPOSE-4204f8f.json` |
| LOCK-002-286f244 (cru sain) | MESURE | 0 | 7 | `scratchpad/refutateur_v8/critiques-LOCK-002-286f244.json` |

Commandes rejouables (depuis le worktree science-prep, `<S>` = scratchpad de session) :

    PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier EDR-GRAB-COST-1828371 <S>/refutateur_v8/critiques-EDR-GRAB-COST-1828371.json --extrait <S>/temoins/temoin-3.md --jugement OUI
    PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier S2-BLIND-CHAMPION-42e9357 <S>/refutateur_v8/critiques-S2-BLIND-CHAMPION-42e9357.json --extrait <S>/temoins/temoin-1.md --jugement OUI
    PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier EDR-RETAIN-COMPOSE-4204f8f <S>/refutateur_v8/critiques-EDR-RETAIN-COMPOSE-4204f8f.json --extrait <S>/temoins/temoin-4.md --jugement OUI
    PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier LOCK-002-286f244 <S>/refutateur_v8/critiques-LOCK-002-286f244.json --extrait <S>/temoins/temoin-2.md

**PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5**
**plancher mesure sur LOCK-002-286f244 : 7 critiques recevables (seuil historique 1)**
**⚠ INDISCRIMINANT : le record cru sain rend autant de critiques recevables que les defectueux**

Critiques confirmées dans cette revue : **12**.

## P1 (JUGE)

### P1.1 — prémisse porteuse n°1 : illisibilité de la garde du pas
- **Sonde** : `python <S>/p1_sonde.py` ; `python -c` (marge au seuil 0,9 sur results/s2_credit_ablation.json + s2_credit_retention.json)
- **Constat** : C'est la prémisse qui pèse le plus sur l'issue : si b_tdoff n'était pas au plancher, la paire tdoff/eplr pourrait réétiqueter des bras en DIRECTION_DEPEND_DU_REGLAGE. Recalculée avec la formule du runner (rapport par seed, S_c par seed, médiane), elle tient : 12/12 seeds au-dessus de 0,9, minimum 0,946, médiane 1,017, marge médiane au seuil 2,95 ticks (min 0,85). Ce run ne la mesure pas : S_a et S_tr sont imposés au bit par les branches 2 et 4, S_c vient de la cohorte froide de P4.4. Prémisse héritée, déclarée par la règle. Pas de défaut.
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:792 ; sortie « tdoff S_tr med 7.5 | greffe<S_a 12 /12 med diff -29.0 | sat/seed min 0.946 med 1.017 n>=0.9: 12 » ; « marge au seuil 0,9 med 2.95 min 0.85 » ; S_c par seed [8.0, 7.5, 8.5, 8.5, 7.0, 7.0, 7.5, 7.0, 8.0, 7.0, 7.0, 8.0].
- **Classe** : aucune
- **Verdict** : non confirmé

### P1.2 — prémisse porteuse n°2 : classes des greffes, famille de 15, seuil 11/12
- **Sonde** : `python -c` comptant par bras des results/s2_credit_ablation*.json les seeds publiant ages(12), dW_abs_sum, td/episode_updates, resurrections, ticks ; p1_sonde.py pour les classes
- **Constat** : Relues dans P4.9 et P4.16, les classes tombent comme annoncé. Érodées : full 12/12 (−28,25), tdonly 12/12 (−27,75), tdoff 12/12 (−29,0), const 11/12 (−12,25), eplr 11/12 (−19,0). Neutre : zero 8/12 (−0,75). Queue binomiale 13/4096 = 0,00317 < 0,05/15. Héritées, mais rendues exactes par la réplication au bit. Toutes les références de la branche 4 existent sur 12 seeds pour les neuf blocs de bras. Pas de défaut.
- **Preuve** : « b_tdoff seeds 12 ages12 12 path 12 resur 12 td 12 ep 12 ticks 12 » (idem huit autres blocs) ; « zero ... 8 /12 med diff -0.75 » ; « const ... 11 /12 med diff -12.25 ».
- **Classe** : aucune
- **Verdict** : non confirmé

### P1.3 — l'argument de létalité en 11c repose sur un net jamais mesuré
- **Sonde** : `python <S>/p1_net_order.py`
- **Constat** : En 11c, la règle soutient que l'ordre des résurrections suit l'érosion de plus près que l'ordre du déplacement net. Or le net n'est publié que pour cinq bras, au seul seed 2026 ; b_tdoff n'en a aucun. Sur ces cinq bras, les deux classements donnent le même coefficient (0,900 contre 0,900). L'avantage n'apparaît qu'en ajoutant b_tdoff avec un net supposé, et tient si ce net reste sous ≈120 ; avec le net que la règle prédit (≈20), le coefficient tombe à 0,543. Affirmation reprise du constat v6 P7.2 sans calcul : inférence présentée comme mesure. Descriptive, ne fait basculer aucune branche, mais appuie le refus d'attribution à l'amplitude.
- **Preuve** : S2-BASSIN-FRAGILITY.v8.json:11 ; « bras avec net publie (seed 2026 seul): [const, eplr, full, tdonly, zero] | tdoff present: False » ; « rho(erosion, resur) 0.900 | rho(erosion, -net) 0.900 » ; « net tdoff suppose 20 -> 0.543 » ; « 120 -> 0.943 ».
- **Classe** : E8
- **Verdict** : confirmé

### P1.4 — chiffres hérités cités comme prémisses
- **Sonde** : `python <S>/p1_sonde.py` ; `python <S>/p1_sonde2.py` ; `python -c` (results/s2_bassin_fragility_calibration_bande.json et sonde de conception)
- **Constat** : Chaque valeur recalculée depuis les JSON suivis concorde : S_a médiane 36,0 (17 à 50) dans P4.4, P4.9, P4.16 ; seed 2035 S_a 42,0 / const 39,5 ; seed 2036 +10,5 et 0,0 ; greffes sous S_c 7, 3, 1 sur 12 ; écarts branche 8 : 9, 17, médiane 28,25 ; résurrections médianes 3,5 / 8 / 10 / 16,5 / 65,5 / 179 ; chemin tdoff/eplr ×1,36 (0,83 à 2,84), masse ×7,34 ; Spearman inter-bras 0,943, six intra-bras concordants ; zero de −8,5 à +2 ; couverture 0,926 à 0,993, puissance 0,808 ; pas publié de P4.9 0,04 (s2_credit_ablation.py:309). Aucun défaut de recopie.
- **Preuve** : « seed 2035 const: S_a 42.0 S_const 39.5 » ; « ecart branche 8 ... [9.0, 17.0, ...] med 28.25 » ; « chemin eplr/tdoff med 0.734 min 0.352 max 1.208 argmax seed 2027 » ; « tdonly spearman intra 0.750 p 0.0050 » ; « regime P4.9 lr_published: 0.04 » ; echangeable_sigma_8.0 heterogene taux 0.926.
- **Classe** : aucune
- **Verdict** : non confirmé

## P2 (DÉLÉGUÉ) — Régime
- **Sonde** : `python tools/check_regime_claims.py --only <S>/S2-BASSIN-FRAGILITY.v8.json ; echo EXIT=$?` puis Glob `docs/EDR/*BASSIN*`
- **Constat** : La porte 19 refuse de juger la cible : elle ne balaie que des records docs/EDR/*.md, et la cible est une règle pré-inscrite JSON. Aucun record BASSIN n'existe encore (aucun run). Verdict de porte recopié tel quel. Le régime n'est tranché par aucune porte à ce stade.
- **Preuve** : « REFUS : --only designe 1 chemin(s) INCONNU(S) de cette porte -- ni record docs/EDR/<nom>.md present, ni record supprime par le commit en cours », EXIT=2 ; Glob → 0 fichier.
- **Classe** : aucune
- **Verdict** : hors périmètre

## P3 (DÉLÉGUÉ) — balayage du pas : garde E19
- **Sonde** : `python tools/check_e19_optimizer_sweep.py --only tools/evo_runs/s2_bassin_fragility.py; echo EXIT=$?` (HEAD 75582d6d) ; `grep -n 'verify(|assert_verdict_invariant_to_optimizer' tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : Verdict porte 23 recopié : OK, sortie 0. Le runner appelle la garde directement (:693 dans _garde_e19, import :674). Classé regle_absente, NOUVEAU et non bloquant, à geler au prochain --update-baseline ; ce classement vient de verify(PREREG) (:1326) visant une règle pas encore scellée. Attendu avant sceau, pas un défaut. La question de fond (référence à pas nul issue du MÊME dispositif) relève de P5. Après le sceau, rejouer la porte : le chemin devrait passer en couvert.
- **Preuve** : « runners scelles : 34 | sous gradient (PLANCHER) : 12 | nus (PLANCHER) : 9 | indetermines : 4 | non resolus : 6 | regle absente : 1 | illisibles : 0 | appelants de la garde : 3 | geles : 19 » ; « [regle_absente] tools/evo_runs/s2_bassin_fragility.py : appelle assert_verdict_invariant_to_optimizer(...) directement » ; « OK : aucun nouveau runner sous gradient sans garde E19, aucune regression, aucune perte d'appelant. » ; EXIT=0.
- **Classe** : E19
- **Verdict** : non confirmé

## P4 (JUGE)

### P4.1 — taille RÉELLE de la famille
- **Sonde** : `python <S>/p4_sonde.py` (verifier_seuils sur la v8, comptage AST des appels _classer/_moins/_plus dans fragility_verdict, queue binomiale, _classer sur published()) ; `python tools/check_control_family.py --report`
- **Constat** : Le dispositif lit bien quinze tests de signe neufs : deux classes de contrôle (eps, pos), le contraste 9b, six classes du sham sign contre S_a, un contraste par bras (MOINS ou PLUS selon la classe de greffe). Cinq ERODE et b_zero NEUTRE confirment 5+1. Bloc seuils identique au runner ; 11/12 tient à 15 cellules, tomberait à 16.
- **Preuve** : verifier_seuils: True ; FAMILLE runner 15 = seuils.famille 15 ; _classer l.767/800/805/848, _moins l.772/806, _plus l.807 ; queue 11/12 = 0,003174 contre 0,05/15 = 0,003333 et 0,05/16 = 0,003125 ; porte 11 : 32 runners scellés, 0 sans design.
- **Classe** : E23
- **Verdict** : non confirmé — le nombre déclaré (15) est le nombre exécuté

### P4.2 — seuil hérité
- **Sonde** : même script : 5/médiane(S_tr) par bras sur published()
- **Constat** : delta_min = 5 vient de P4.4, déclaré. Il représente 59 à 67 % de la survie greffée médiane des trois bras au plancher : chiffre de la note des seuils exact, héritage dit.
- **Preuve** : 5/S_tr : tdonly 0,59 (8,50), full 0,62 (8,00), tdoff 0,67 (7,50) ; const 0,22, eplr 0,29, zero 0,15.
- **Classe** : aucune
- **Verdict** : non confirmé — héritage déclaré et chiffre vérifié

### P4.3 — commentaire de seuil périmé
- **Sonde** : `grep -n -E "/14|famille.*14" tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : Le commentaire qui justifie SIGN_MIN divise encore alpha par 14 alors que FAMILLE vaut 15 treize lignes plus haut — reste de la v7, non mis à jour à l'entrée du contraste PLUS de b_zero. Sans effet à l'exécution (seuil_tient et verifier_seuils lisent FAMILLE), mais c'est le lien texte-seuil jugé fragile en revue v3 P4.3, et le texte est faux.
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:98 « 0,05/14 (famille déclarée, E23) » contre :85 FAMILLE = 15 ; 0,05/14 = 0,003571, non 0,003333.
- **Classe** : aucune (commentaire sans effet exécutable)
- **Verdict** : confirmé

### P4.4 — conclusion 11c adossée à des cellules hors famille
- **Sonde** : `python -c` (recherche de « bascule » et « ancre » dans famille_de_controles et la branche 11c ; 0.05/27) ; `grep -n premiere_echelle_qui_erode tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : La conclusion pré-inscrite de MIXTE_PAR_AMPLITUDE limite l'usage du remède d'ancrage par le niveau d'échelle où un tirage commence à éroder. Ce niveau résulte de douze classements au critère 11/12 (deux échelles × six bras), tous hors famille. Le code du verdict ne le lit pas (l.967-970) : seule la prose en tire une conclusion. Lue comme résultat, la famille passe à 27 cellules et 11/12 ne tient plus — même cas que le contraste ×2 refusé en revue v6 P4.a.
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:848 (_classer à sign_min sur sign_x2/sign_x4), :855 (premiere_echelle_qui_erode) ; famille_de_controles : « bascule » False, « ancre » False ; branche 11c : « l'ancre ne répond qu'en-dessous de l'amplitude de bascule » ; 0,05/27 = 0,001852 < 0,003174.
- **Classe** : E23
- **Verdict** : confirmé

### P4.5 — contraste lu dans le motif, absent de l'inventaire
- **Sonde** : `grep -n au_dela_du_plancher_eps tools/evo_runs/s2_bassin_fragility.py` ; `python -c` (« plancher » dans famille_de_controles)
- **Constat** : Le motif déclare un FRAGILE « sans érosion au-delà du plancher eps » à partir de six contrastes sign − eps jugés sur leur seule médiane, sans compte de signes ni bande. L'inventaire famille_de_controles liste tout ce qui est hors famille (iso, échelles, bandes) et les omet : le lecteur ne peut savoir que le verdict affirme une absence d'érosion sans contrôle d'erreur.
- **Preuve** : :867 (critère médiane <= −5, aucun compte), :977 (liste plancher), :1001 (écrit dans why) ; famille_de_controles : « plancher » False.
- **Classe** : E23
- **Verdict** : confirmé

### P4.6 — hors champ, consigné en passant
- **Sonde** : `grep -n "bootstrap des tirages dans chaque seed" tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : Le bloc regime publié décrit encore la bande comme un bootstrap sur les seuls tirages (méthode v6) ; depuis la v7 la référence est dans le pool. Relève de P2/P10, pas de P4.
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:1208 contre :589 (pool = tirages + référence).
- **Classe** : E8
- **Verdict** : hors périmètre

## P5

### P5.1 — plancher eps tiré sur le support de b_full pour tous les bras
- **Sonde** : `python <S>/p5_v8_support.py` (W persistés de la sonde de conception, seed 2026, sha256 404b4c0a... et 004f34dd... revérifiés contre W_sonde_sha256 ; aucun monde) ; Read tools/evo_runs/s2_bassin_fragility.py:509-510, :858, :867, :977
- **Constat** : Le plancher eps est tiré une fois par seed sur le ΔW de b_full, puis sert de référence à TOUS les bras : il qualifie chacun (drapeau au_dela_du_plancher_eps, repris dans le motif d'un bras FRAGILE) et sert de contrôle de DIRECTION en 9b. Or b_eplr (et b_tdoff, même voie épisodique, non sondé) n'écrit que dans les huit colonnes de déplacement ; près d'un quart de la masse d'eps tombe sur grab, rub et tête de valeur, jamais touchées par leur sham. Plancher et contrôle positif viennent donc d'une autre perturbation que celle testée. Si eps est inerte, la lecture ne change pas ; drapeau et motif, si. Remède : un eps par bras sur son propre support, ou déclarer l'écart.
- **Preuve** : :509-510 (ref = b_full) ; :858 (eps_d = S_sign_k − S_eps pour tout k) ; :977 (liste plancher dans le motif). Colonnes non nulles dW b_full [64-71, 88, 89, 92], b_eplr [64-71] ; part de la masse d'eps hors support de b_eplr = 0,234.
- **Classe** : E6
- **Verdict** : confirmé

### P5.2 — contrôle positif de FRAGILE
- **Sonde** : `python -c` chargeant load_bassin() et le W persisté de b_full (seed 2026), imprimant ||W_bassin||1 / net ; Read :512-518, :928
- **Constat** : Il peut échouer (branche 7 exécutable) et son écart de régime se vérifie : 24,3 fois le net de b_full, 716 fois celui de b_zero, conforme à la fourchette publiée. Gaussien sur toute la matrice, autre dispositif que le sham à signes, mais déclaré (limite de 7 : amplitude, colonnes 77-78, complément hors verdict par échelle x2/x4).
- **Preuve** : L1 W_bassin 2442,8 ; /100,54 = 24,3 ; /3,41 = 716,4 ; :514 (sham iso sur zero + 1.0, toute la matrice).
- **Classe** : aucune
- **Verdict** : non confirmé

### P5.3 — garde d'appariement (branche 6)
- **Sonde** : `python <S>/p5_eps_match.py` puis `python -c` rejouant les 5 tirages eps (sham_rng(2026, None, 'eps', r)) avec matching()
- **Constat** : Ne peut lever que sur faute de code : erreur après arrondi float32 six ordres sous la tolérance, sham sign comme eps. Voulu (« exact par construction »), contre-exemple gelé au pré-vol (iso à 2 % de trop lève). Pas un contrôle tautologique présenté comme test de fond.
- **Preuve** : l1_rel_err_max sign x1 <= 1,25e-08 sur 5 bras ; eps 3,61e-06 sur 5 tirages ; tolérance 0,01 (:96).
- **Classe** : aucune
- **Verdict** : non confirmé

### P5.4 — atteignabilité des issues
- **Sonde** : `python <S>/p5_sonde.py` ; `python -c` (saturation |S_tr−S_a|/(S_a−S_c) par bras via published() et cold_floor())
- **Constat** : Tout concorde avec la règle : MOINS plafonne à 11/12 pour const et eplr, atteint 12/12 pour les trois bras au plancher ; garde E19 illisible d'avance (b_tdoff saturé 12/12). Aucune limite tue. La paire E19 ne diffère que par le pas (runner:72, :74).
- **Preuve** : S_a−S_tr > 0 : b_const 11/12 (−10,5 ; 2,5 aux deux plus bas), b_eplr 11/12 (un écart 0,0), full/tdonly/tdoff 12/12 ; saturation b_tdoff min 0,946, médiane 1,017 ; b_full médiane 0,979, min 0,900.
- **Classe** : aucune
- **Verdict** : non confirmé

### P5.5 — garde de dégénérescence du contraste
- **Sonde** : `python -c` calculant c = S_tr_full − S_tr_tdoff et appelant assert_not_degenerate(c, min_spread=1e-9) ; `grep -n 'assert_positive_control|assert_not_degenerate|assert_ablation_changes_something' tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : Seuil 1e-9 sur grille au demi-tick : ne se déclenche que si les douze contrastes sont identiques au bit, muette dans le cas où elle servirait (deux bras au plancher). Le qualificatif de saturation signale déjà ce plancher pour les trois bras : garde redondante, aucun plancher tu.
- **Preuve** : c : étendue 3,0, médiane 0,5, garde True ; assert_not_degenerate :726, :815, :905 ; 0 appel d'assert_positive_control / assert_ablation_changes_something (contrôles en ligne :928, :943) ; saturation médiane full 0,979, tdonly 0,961, tdoff 1,017.
- **Classe** : aucune
- **Verdict** : non confirmé

## P6

### P6.1 — le plancher eps n'est pas le no-op du contraste de chaque bras
- **Sonde** : `python <S>/p6_v8_eps_support.py` (W de sonde, sha256 conformes à results/s2_bassin_fragility_sonde_conception.json) ; `grep -n 'eps_d\|ref = "b_full"\|plancher = ' tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : Le qualificatif de plancher confronte le sham de chaque bras à UN seul eps tiré par seed sur le ΔW de b_full. Pour b_eplr (b_tdoff non sondé), ce plancher place 23 % de sa masse L1 sur les colonnes 88, 89, 92 où le crédit du bras ne met rien. L'échelle dérive : 1/1000 du crédit pour b_full, 1/185 pour b_eplr, 1/34 pour b_zero. La différence sham − eps ne porte aucune bande de tirage, contrairement aux contrastes voisins.
- **Preuve** : b_full part L1 colonnes 88,89,92 = 0.234 ; b_eplr 0.000 (64-71 : 1.000) ; eps/net_full 0.00100, eps/net_eplr 0.00540, eps/net_zero 0.02948. :509-510 ; :858 et :867 (même S_eps, aucun appel à _bande_contraste) ; :977, :1001.
- **Classe** : E6
- **Verdict** : confirmé

### P6.2 — puissance de la bande calculée avec une référence sans bruit
- **Sonde** : `python <S>/p6_v8_puissance_echangeable.py 1000` (importe _bande_contraste et _dans_la_bande du runner, aucun monde)
- **Constat** : La règle annonce 0,81 à un effet de 2 et 1,00 à un effet de 4 (sigma 2) sans dire que la référence est supposée sans bruit, alors qu'elle pose la greffe comme une réalisation de plus sous le nul de FRAGILE. Rejouée avec référence bruitée, la puissance tombe à 0,69 à effet 2 : un effet réel de 2 ticks passe pour indiscernable dans 31 % des cas, pas 19 %. Le motif écrit aussi « eps inerte » dès qu'eps tombe dans sa bande.
- **Preuve** : effet 2.0 réf EXACTE 0.818 (± 0.012) contre ECHANGEABLE 0.693 (± 0.015) ; effet 4.0 : 1.000 contre 0.998. :623 (echangeable=False) ; calibration_bande puissance effet_2.0_sigma_2 = 0.808 ; :784-786.
- **Classe** : E6
- **Verdict** : confirmé

### P6.3 — sonde imposée du no-op
- **Sonde** : `grep -oiE 'no.?op'` sur la cible v8, results/s2_bassin_fragility_sonde_conception.json et results/s2_bassin_fragility_calibration_bande.json ; `python -c` imprimant couverture et puissance
- **Constat** : Toutes les mentions du no-op désignent S_a ou la branche 2 (reproduction au bit de a_frozen), témoin à bruit nul. Aucun contraste de sham n'est encore mesuré : le situer dans sa bande n'est pas faisable avant le run. La calibration concorde au chiffre près avec la règle.
- **Preuve** : cible 10 occurrences (5 no-op, 4 noop, 1 NOOP) ; sonde 10 (toutes run_noop) ; calibration 0. Exacte >= 0.997, échangeable homogène 0.952-0.993, hétérogène 0.926-0.983, puissance 0.808 / 1.0.
- **Classe** : aucune
- **Verdict** : hors périmètre

## P7 (JUGE)

### P7.1 — part du ΔW par voie : la borne de brassage couvre une fraction non publiée
- **Sonde** : `python <S>/p7v8_voies.py` (W_final et W0 de la sonde, seed 2026, aucun monde) ; grep sur _MOVE_LOGITS, _GRAB_NODE, _VALUE_NODE et les pertes dans src/agents/backend_torch.py ; `grep -n 'def delta_structure' -A30 tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : La v8 borne le brassage voie par voie sans dire quelle fraction du déplacement net chaque voie porte. La perte épisodique ne lit que les huit logits de déplacement ; grab, rub et tête de valeur ne reçoivent que le TD. Ces trois colonnes portent 23 % du net de b_full, 35 % de b_const, 0 % de b_eplr. Pour b_const (plafond épisodique le plus haut, 0,262), au moins un tiers de ΔW relève d'une voie sans borne, et les quatre chiffres comparent des parts différentes (tout le ΔW pour eplr/tdoff, au plus 65 à 77 % pour const/full). delta_structure ne publie aucune part par voie. Remède : publier par bras la part des colonnes écrites par le seul TD à côté de chaque borne.
- **Preuve** : full TD-seul (88, 89, 92) 0.234 / move 0.766 ; const 0.354 / 0.646 ; tdonly 0.288 ; zero 0.470 ; eplr 0.000. backend_torch.py:478, :502 (perte épisodique sur out[:, :_MOVE_LOGITS]) contre :256, :263 (TD) ; s2_bassin_fragility.py:190-191 ; col_mass_top10_nodes de b_const commence par 92.
- **Classe** : E8
- **Verdict** : confirmé

### P7.2 — dose, létalité, cohorte contre les JSON publiés
- **Sonde** : `python <S>/p7v8_dose.py` ; `python <S>/p7v8_letal.py` ; `python -c` recomptant les reconstructions depuis ages/censored/ticks
- **Constat** : Médianes de résurrections, ordre b_eplr > b_tdoff seed par seed, corrélations intra et inter-bras avec p exact, quatre bornes par voie et reconstructions de phase 2 tombent sur les valeurs écrites. Cohorte 12, 2000 ticks, dose TD 1999 ou 0, épisodique 250 ou 0.
- **Preuve** : résurrections médianes tdoff 3.5, tdonly 8, full 10, eplr 16.5, const 65.5, zero 179 ; eplr > tdoff 12/12 ; rho intra +0.286, +0.750 (p 0.005), −0.256, −0.056, +0.362, +0.401 ; inter +0.943, p exact 12/720 = 0.0167 ; reconstructions 10, 5, 5, 10, 9, 10, 5.5 ; td_updates {1999, 0}, episode_updates {250, 0}, num_agents {12}.
- **Classe** : aucune
- **Verdict** : non confirmé

### P7.3 — apprenant de phase 1 hors compteur (tête throw, World Model)
- **Sonde** : `grep -n torch_throw_gate src/worlds/world_1_stoneage.py tools/evo_runs/s2_credit_retention.py tools/evo_runs/s2_bassin_fragility.py` ; `sed -n 191,210p src/agents/backend_torch.py`
- **Constat** : Aucun : la tête throw n'apprend que si le monde l'active, ce que ni _world ni le runner ne font ; le forward torch ignore le World Model stocké. Le compteur voit toutes les écritures de W.
- **Preuve** : world_1_stoneage.py:59 (torch_throw_gate = False), 0 occurrence dans les deux runners ; backend_torch.py:191-210.
- **Classe** : aucune
- **Verdict** : non confirmé

## P8 (JUGE)

### P8.1 — le vote moyenne des shams indépendants par agent
- **Sonde** : `python <S>/p8_v8_vote_coherence.py` (numpy pur) : ΔW_i des 5 W de sonde p418_W_*_2026.npz ; sham = sham_delta(dW, 'sign', sham_rng(2026, bras, 'sign', 0)) ; cos moyen par paire, coh12 = ||moyenne_i d_i|| / moyenne_i ||d_i|| sur la matrice et sur H·d_i[64:] ; variante à signes partagés. Lecture s2_bassin_fragility.py:144, world_1_stoneage.py:965-973. Recherche de « indépendam », « atténu », « corrél » près de vote dans la cible : aucune (motif validé : « indépendamment » trouvé 1 fois ailleurs).
- **Constat** : Le vote remplace la sortie du groupe co-localisé par la moyenne des votants. Le runner tire les signes du sham indépendamment par agent, alors que le déplacement appris est cohérent d'un clone à l'autre. Moyenné sur douze agents, le sham perd environ trois quarts de sa norme, le crédit bien moins : le monde atténue le sham plus que la greffe, ce qui pousse le contraste vers MOINS, donc vers DIRECTION. La règle ne dit pas que cette moyenne traite différemment les deux bras ; la cohérence inter-agents du sham est un paramètre libre non apparié, qu'un tirage partagé inverserait. Amplitude in situ inconnue sans monde : à mesurer avant lecture, dette.
- **Preuve** : :144 tire s de forme (B,N,N) ; world_1_stoneage.py:973 écrase chaque ligne de la case. cos crédit/sham : full +0,296/+0,012 ; tdonly +0,343/−0,010 ; const +0,622/+0,017 ; eplr +0,540/−0,019 ; zero +0,774/−0,004. coh12 matrice : 0,583/0,310 ; 0,604/0,273 ; 0,810/0,318 ; 0,770/0,250 ; 0,900/0,283 (1/√12 = 0,289). Sortie : 0,370/0,217 ; 0,835/0,240 ; 0,737/0,426 ; 0,818/0,142 ; 0,979/0,186. À signes partagés le sham devient plus cohérent que le crédit (0,849 à 0,925).
- **Classe** : aucune (voisine de E15 : population de composition différente entre bras, confondue par l'interaction)
- **Verdict** : confirmé

### P8.2 — chevauchement entrée/sortie (E24)
- **Sonde** : `python tools/check_io_overlap.py` ; `python -c` chargeant results/warm003_dagger_genome.npz ; grep du périmètre dans tools/check_io_overlap.py
- **Constat** : Aucun recouvrement : 59 capteurs, 108 sorties à partir du nœud 64 ; porte 17 sans génome nouveau ni aggravé. Les matrices persistées sous results/ sortent de son périmètre mais héritent des dimensions du bassin, vérifiées au chargement.
- **Preuve** : porte 17 : 358 persistés, 10 chevauchants (connus 10, nouveaux 0, aggravés 0), EXIT 0 ; bassin I 59, O 108, N 172, recouvrement 0 ; check_io_overlap.py:13-14 ; assert_no_io_overlap dans load_bassin (s2_credit_retention.py:61).
- **Classe** : E24
- **Verdict** : non confirmé

### P8.3 — corps (E26)
- **Sonde** : `grep -n "W\[" tools/evo_runs/s2_bassin_fragility.py` ; lecture src/agents/mamba_agent.py:77-80, :174 ; runner :210-214 ; grep absorb_knowledge|mutate|update_phenotype|benchmark_mode dans world_1_stoneage.py ; body_rows_0_10_share de la sonde de conception
- **Constat** : Les rangées 0 à 9 reçoivent 3 à 6 % du déplacement appris (iso et pos en chargent autant), mais le corps n'est jamais recalculé en phase 2 : attributs figés à la construction, W posé par copie, vérification avant et après, transferts génétiques coupés par benchmark_mode.
- **Preuve** : body_rows_0_10_share 0,031 (zero) à 0,057 (eplr) ; mamba_agent.py:77-80, :174 (deepcopy) ; runner :210, :211, :214 ; écrivains monde world_1_stoneage.py:934, :1019, :989 coupés par :1878-1879.
- **Classe** : E26
- **Verdict** : non confirmé

### P8.4 — vue de l'état récurrent dans le vote
- **Sonde** : lecture src/worlds/world_1_stoneage.py:947-976 et src/swarm/consensus.py:32-55 ; `grep -n "np.stack" src/swarm/consensus.py`
- **Constat** : Les lignes de logits passées au vote sont des vues, mais empilées dans une copie avant la réécriture en place ; aucun votant ne lit une ligne déjà réécrite.
- **Preuve** : world_1_stoneage.py:964 vue batch_logits[idx] ; consensus.py:47 np.stack (copie) ; réécriture à :973.
- **Classe** : E5
- **Verdict** : non confirmé

## P9 (DÉLÉGUÉ)

### P9.1 — provenance : porte 20 sur la cible
- **Sonde** : `python tools/check_evidence_provenance.py --only <S>/S2-BASSIN-FRAGILITY.v8.json ; echo exit=$?` ; `python tools/check_evidence_provenance.py --only S2-BASSIN-FRAGILITY ; echo exit=$?` ; `grep -n 'P2\.129\|P2\.128' docs/roadmap/PRIORITES_ET_DETTES.md`
- **Constat** : Verdict recopié de la porte 20 (HEAD 75582d6d) : REFUS, exit 2, par nom comme par chemin. La porte ne lit que les records EDR. Aucune réponse de porte sur la provenance de la v8 ; dette P2.129 ouverte, qui dépend de P2.128 désormais close.
- **Preuve** : « REFUS : --only designe 1 chemin(s) INCONNU(S) de cette porte -- ni record docs/EDR/<nom>.md present » exit=2 (deux appels) ; PRIORITES_ET_DETTES.md:1429, :1443, :1621.
- **Classe** : aucune
- **Verdict** : hors périmètre

### P9.2 — provenance : sceau de la pré-inscription
- **Sonde** : `python -c "from tools.preregister import verify; verify('S2-BASSIN-FRAGILITY')" ; echo exit=$?` ; `python -c` listant docs/preregistrations
- **Constat** : Verdict recopié : FileNotFoundError, exit 1, rien de scellé sous ce nom (0 fichier BASSIN parmi 71). État normal d'un brouillon avant sceau. À rejouer après preregister avec reviewed_by.
- **Preuve** : tools/preregister.py:196 (« aucune pre-inscription S2-BASSIN-FRAGILITY »), exit=1 ; 71 fichiers, BASSIN = [].
- **Classe** : aucune
- **Verdict** : non confirmé

## P10

### P10.1 — contrôle en cours de run promis, absent
- **Sonde** : `python <S>/p10_v8_inrun.py` (verdict pur : ligne injectée noop_identical=False, repl_*=False, transplant_ok_*=False, appariement 0,5) ; `grep -n "noop_identical\|repl_" tools/evo_runs/s2_bassin_fragility.py` ; Read :896-913, :1259, :1270-1288
- **Constat** : La pré-inscription promet un contrôle en cours d'exécution, seed par seed, du no-op, de la réplication, de la greffe et de l'appariement. Le runner ne le fait pas : ces drapeaux ne sont lus que par fragility_verdict via agreger ; après le premier seed ce verdict s'arrête à la branche 1 (INCOMPLET, n = 1 < 12). Un harnais non reproductible dès 2026 fait tourner les 66 cellules et 11 seeds restants avant d'être lu INDETERMINE. Seule la garde de corps lève pendant chaque phase 2.
- **Preuve** : 1 seed → INCOMPLET (« 1 seeds < 12 ») malgré quatre branches violées ; 12 seeds → INDETERMINE_NOOP. noop_identical/repl_ seulement en :535, :545 (seed_row) et :743, :899, :913 ; agreger en :1259 et :1297 ; boucle :1270-1288 ne teste que le CPU cumulé. Promesse : S2-BASSIN-FRAGILITY.v8.json:30, prevol (3).
- **Classe** : E10
- **Verdict** : confirmé — le verdict final reste juste (la branche 2 rattrape à 12 seeds), mais le contrôle annoncé en cours de run n'existe pas : rien ne borne le coût d'un harnais cassé (lien E13). Correctif : dans _commande_tout, appeler seed_row et les branches 2/4/5/6 après chaque seed, et lever en cas d'échec.

### P10.2 — pas de b_tdoff présenté comme publié
- **Sonde** : `python -c "import json;d=json.load(open('results/s2_credit_ablation.json',encoding='utf-8'));print(d['regime']['lr_published'],d['preflight']['lr_effective'],d['arms']['b_tdoff']['2026']['learning'].get('lr'))"` ; `sed -n '120,124p;145p;309p' tools/evo_runs/s2_credit_ablation.py` ; `sed -n '286,290p' tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : La v8 rétracte la v7 en affirmant que P4.9 publie le pas de b_tdoff. La ligne citée recopie le pas mesuré sur la trace b_full du pré-vol (4 agents, 32 ticks) ; la trace tdoff a tourné mais son pas n'a pas été conservé. Le 0,04 de b_tdoff reste une déduction du défaut partagé (lr = None). La docstring du runner affirme le contraire : règle et code divergent.
- **Preuve** : sortie 0.04 {'full': 0.04, 'lr': 0.004} None ; s2_credit_ablation.py:309, :124, :145 ; s2_bassin_fragility.py:287-288 contre S2-BASSIN-FRAGILITY.v8.json:4.
- **Classe** : E8
- **Verdict** : confirmé — sans effet sur le verdict (même défaut lr=None, garde E19 illisible, pas_optimiseur_mesure au rejeu), mais la correction v8 fait passer une inférence pour une publication. Écrire « défaut partagé, mesuré sur b_full » et aligner la docstring.

### P10.3 — borne du brassage
- **Sonde** : `python -c "for p in range(12): L=list(range(12)); d=L.pop(p); L.append(d); print(p, sum(L[j]!=j for j in range(12)))"` ; Read tools/evo_runs/s2_credit_retention.py:107-111, src/worlds/world_1_stoneage.py:1060-1066, :1784
- **Constat** : La règle plafonne à onze les lignes W qui changent de corps après une mort. Le mécanisme en donne 12 − p pour une mort en position p (survivants en ordre, ressuscité en queue, lot non reconstruit tant que B ne change pas) : douze quand le premier corps meurt, aucune pour le dernier. Borne juste : douze.
- **Preuve** : 0:12, 1:11, ..., 10:2, 11:0 ; s2_credit_retention.py:111 ; world_1_stoneage.py:1062, :1784 ; S2-BASSIN-FRAGILITY.v8.json:27 « jusqu'à 11 ».
- **Classe** : aucune
- **Verdict** : confirmé — mineur et descriptif (brassage hors verdict) : écrire « jusqu'à 12 ».

### P10.4 — relecture des autres affirmations de code
- **Sonde** : `sed -n` des lignes citées (backend_torch.py, world_1_stoneage.py, consensus.py, learning_events.py) ; `python -c` load_bassin ; `python -c` recomptant les reconstructions depuis P4.16/P4.9
- **Constat** : Vue des logits sur H et ses deux écrivains, vote réécrivant toutes les lignes, reconstruction remettant H à zéro, pas épisodiques nuls de b_zero, SGD à perte moyennée sur B, compteur épisodique, médianes de reconstructions, couplage des blocs vers 77-78 : tout concorde.
- **Preuve** : backend_torch.py:48, :111, :141, :200, :210, :502 ; world_1_stoneage.py:965, :972-973, :1340 ; consensus.py:8 ; learning_events.py:185-187 ; I 59, O 108, N 172 ; blocs vers 77/78 : 0,727/0,929 (8,7 %/9,7 %) ; reconstructions a_frozen 10, full 5, tdonly 5, const 10, eplr 9, zero 10, tdoff 5,5.
- **Classe** : aucune
- **Verdict** : non confirmé

---

## Addendum de l'auteur (session SCIENCE-HARNAIS, 2026-09-26) — jugement sous la RÈGLE D'ARRÊT, v8 → v9

La règle d'arrêt a été déposée AVANT le retour de cette revue :
`docs/reviews/2026-09-26-S2-BASSIN-FRAGILITY.regle-d-arret.md` (sha256 `599e0074…`, staging 18:16:41 +0200 ; horodatages
mesurés dans `….regle-d-arret.horodatages.md`). Ce passage est INDISCRIMINANT : le témoin cru sain rend 7 critiques
recevables, les défectueux 6 à 7. Chaque critique confirmée ne compte donc que par la RE-VÉRIFICATION de l'auteur, faite
une à une, sondes relancées (`p418_verif_v8.py`) :
- **P1.3** : à cinq bras, le coefficient vaut 0,900 dans les deux ordres, et 0,543 avec un b_tdoff à net 20.
- **P4.3** : il reste une ligne en 0,05/14.
- **P4.4** : 11c porte bien « amplitude de bascule ».
- **P4.5** : « plancher » est absent de l'inventaire.
- **P5.1 / P6.1** : les colonnes de b_eplr sont [64..71], et 23 % de la masse d'eps tombe hors de ce support.
- **P6.2** : la puissance à référence bruitée vaut 0,6625 (rejeu 400) et 0,674 (1000).
- **P7.1** : les colonnes TD seules portent 0,234 / 0,288 / 0,354 / 0,470 / 0,000 du net.
- **P8.1** : le cos inter-agents vaut, crédit contre sham, +0,30 / +0,01, +0,34 / −0,01, +0,62 / +0,02,
  +0,54 / −0,02 et +0,77 / −0,00.
- **P10.1** : `_commande_tout` ne lit ni `noop_identical` ni `repl_`.
- **P10.2** : `lr_published` recopie le pas de la trace b_full.
- **P10.3** : [12, 11, …, 2, 0] lignes changent de corps selon la position de la mort.

Les douze sont tenues.

**Classement dans la liste fermée (a)-(g).** UNE seule critique en relève : **P4.4**, au titre de (g), le sens attendu
d'une issue. MIXTE_PAR_AMPLITUDE affirmait que « l'ancre ne répond qu'en-dessous de l'amplitude de bascule ». Or cette
bascule se déduit de 12 classements d'échelle HORS famille ; les lire comme un résultat porterait la famille à 27, et
11/12 ne tiendrait plus. Retirer cette affirmation change ce que l'issue affirme : d'où la **v9**, qui RESTREINT. Elle
est relue sous la même règle, qui ne se desserre pas. Les onze autres relèvent de l'addendum. Puisqu'une v9 existe,
elles sont aussi corrigées dans la règle elle-même :
- **P1.3** : 11c ne prétend plus que l'ordre des résurrections l'emporte sur celui du net, qui n'est pas mesuré.
- **P4.3** : le commentaire de SIGN_MIN passe à 0,05/15.
- **P4.5** : le qualificatif « plancher eps » est déclaré dans l'inventaire, sans contrôle d'erreur.
- **P5.1, P6.1** : la portée de eps (support de b_full, échelle relative) est déclarée.
- **P6.2** : la puissance à référence bruitée est MESURÉE sur la bande exécutée : 0,674 à un effet de 2, 0,997 à 4. Elle
  est ajoutée à `results/s2_bassin_fragility_calibration_bande.json` et citée.
- **P7.1** : la part des colonnes écrites par le seul TD est publiée par bras (`td_seul_cols_share`) et citée.
- **P8.1** : le biais du vote vers DIRECTION est dit EN TÊTE du motif de toute lecture DIRECTION ou PARTIEL (exigence
  de Master 2), et un tirage à signes PARTAGÉS (`sign_commun`) l'encadre. Ce tirage est pré-classé AVANT la revue v9 :
  descriptif, hors verdict, hors famille. Aucune lecture de ce tirage ne peut changer une branche, et toute critique qui
  le vise relève de l'addendum.
- **P10.1** : `verifier_seed` vérifie les branches 2, 4, 5 et 6 à CHAQUE seed. La tâche seed écrit sa mesure, puis lève
  en nommant chaque échec. Témoin gelé.
- **P10.2** : le pas de b_tdoff est dit DÉDUIT du défaut partagé, et la docstring est alignée.
- **P10.3** : jusqu'à 12 slots, pas 11.

Non confirmées ou hors périmètre : sans suite.
