# Revue adversariale — TD-STEP-PILOT-R3 v2 (brouillon de pré-inscription)

- **Cible** : `C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/revue_r3v2/TD-STEP-PILOT-R3.v2.json`
- **Date** : 2026-10-14
- **SHA** : `d4ca9de95679b3bb58f8b3dea906e30e4484ff08` (worktree p419)
- **Résultat des TÉMOINS** (avec les planchers, sur les mêmes lignes) :
  - S2-BLIND-CHAMPION-42e9357 : RETROUVE, code 0, 9 recevables — PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 — plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1) — ⚠ INDISCRIMINANT : le record cru sain rend autant de critiques recevables que les defectueux
  - LOCK-002-286f244 (cru sain) : MESURE, code 0, 6 recevables — PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 — plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1) — ⚠ INDISCRIMINANT : le record cru sain rend autant de critiques recevables que les defectueux
  - EDR-GRAB-COST-1828371 : RETROUVE, code 0, 7 recevables — PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 — plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1) — ⚠ INDISCRIMINANT : le record cru sain rend autant de critiques recevables que les defectueux
  - EDR-RETAIN-COMPOSE-4204f8f : RETROUVE, code 0, 4 recevables — PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 — plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1) — ⚠ INDISCRIMINANT : le record cru sain rend autant de critiques recevables que les defectueux
- **Commandes de vérification** (rejouables) :
  - `PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/p419/tools/refutateur_temoins.py --verifier S2-BLIND-CHAMPION-42e9357 <scratchpad>/revue_r3v2/travail/critiques-S2-BLIND-CHAMPION-42e9357.json --extrait <scratchpad>/revue_r3v2/temoins/temoin-1.md --jugement OUI`
  - `PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/p419/tools/refutateur_temoins.py --verifier LOCK-002-286f244 <scratchpad>/revue_r3v2/travail/critiques-LOCK-002-286f244.json --extrait <scratchpad>/revue_r3v2/temoins/temoin-2.md`
  - `PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/p419/tools/refutateur_temoins.py --verifier EDR-GRAB-COST-1828371 <scratchpad>/revue_r3v2/travail/critiques-EDR-GRAB-COST-1828371.json --extrait <scratchpad>/revue_r3v2/temoins/temoin-3.md --jugement OUI`
  - `PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/p419/tools/refutateur_temoins.py --verifier EDR-RETAIN-COMPOSE-4204f8f <scratchpad>/revue_r3v2/travail/critiques-EDR-RETAIN-COMPOSE-4204f8f.json --extrait <scratchpad>/revue_r3v2/temoins/temoin-4.md --jugement OUI`

  (`<scratchpad>` = `C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad`)

---

## P1

### P1.a — puissance au seul pas 4,0
- **Sonde** : `python -I scratchpad/p1_cles.py results/td_step_pilot_r3_tau/lam09_seed14.json 1` (pas : 4.0) ; `git ls-files results/td_step_pilot_r3_tau | wc -l` ; comptage de `"pas` et `"lr` dans `results/td_step_pilot_r3_tau.json` ; `grep -n pas_primaire tools/td_step_pilot_r3.py` ; python -c lisant `results/td_step_pilot_r2.json['_lecture']['par_lr']`
- **Constat** : La puissance qui justifie la marge de 20 n'existe qu'au pas 4,0 : les 24 cellules tenues à l'écart ont toutes tourné à ce pas, et calibrer_lecture_v2 n'injecte que des clés du pas primaire. Or la synthèse ADR exige la branche TRANSPORTE AUSSI à 4√2, où μ, τ et la puissance sont absents. L'effet de la trace dépend du pas au point de passer de 12/12 à 0/12 entre lr 4,0 et 2,0 (R2) : si μ à 4√2 tombe vers la marge, ce pas rend PAS_D_EFFET et l'entrée devient impossible, sans qu'aucune calibration l'ait chiffré. La probabilité jointe des deux pas n'est calculée nulle part. Sous indépendance, même à distribution identique, elle vaut 0,895² ≈ 0,80 à σ_e = τ et 0,855² ≈ 0,73 à 9,3, donc au seuil exigé ou en dessous. Le pas de la mesure de τ n'est d'ailleurs publié que dans les fichiers par cellule, non suivis : l'agrégat suivi n'a aucune clé pas ni lr.
- **Preuve** : tools/td_step_pilot_r3.py:464 (calibrer_lecture_v2 : p = pas_primaire) et :444 (base_injection_v2) ; tools/td_step_pilot_r3.py:333 (ENTRE aux deux pas) ; R2 _lecture.par_lr : aide09 12/12 à 4.0 contre 0/12 à 2.0 ; cellule tau 'pas': 4.0 ; git ls-files results/td_step_pilot_r3_tau -> 0 ; '"pas' et '"lr' -> 0 occurrence dans l'agrégat suivi ; puissance marge=20|compte=11 f=0 TRANSPORTE 0.895 (σ_e 6.7) / 0.855 (9.3)
- **Classe** : E6
- **Verdict** : confirmé

### P1.b — maintien du bras apparié décidé sur un temps CPU sous charge
- **Sonde** : `python -I -X utf8 -c` (cpu_s min/max par bras, rapport cpu_s/mur_s, fractions recomputées) sur `results/td_step_pilot_r3_tau.json` ; Read tools/td_step_pilot_r3.py:612-641
- **Constat** : Le maintien du bras apparié se décide sur le temps CPU d'UNE seule cellule par bras du seed 1. Or une condition d'entrée en dépend : lam09 contre td0_app + marge. La règle suppose ce temps insensible à la contention entre pods, et les 24 cellules de τ réfutent cette hypothèse. Le rapport CPU/mur vaut 0,965 à 1,000. Un même bras, à dose identique (6000 mises à jour), coûte de 28,0 à 146,0 s CPU, soit ×5,2. td0_app tourne forcément dans une vague postérieure, puisqu'il attend les ρ. À charge homogène, sa fraction vaut 0,23 ; avec les extrêmes mesurés, elle va de 0,06 à 0,59, de part et d'autre du seuil 1/3. Le pré-vol mesure donc la charge du moment et non le coût, et c'est cette charge qui fixe la règle de lecture.
- **Preuve** : tools/td_step_pilot_r3.py:625-628 (u[b] = cpu_s d'une cellule ; retenu ssi frac < seuil) ; tau lam0|seed=13 cpu_s 28.0 contre lam0|seed=15 cpu_s 146.0, dose_updates 6000 pour les deux ; cpu/mur 0.965-1.000 ; fraction 0.226 à charge homogène, 0.059 (apparié seul) contre 0.592 (apparié sous charge) face au seuil 0.333
- **Classe** : E12
- **Verdict** : confirmé

### P1.c — σ_e dit « mesuré »
- **Sonde** : `python -I scratchpad/p1_cles.py results/td_step_pilot_r3_puissance_apres_tau.json 4`
- **Constat** : La règle qualifie σ_e de mesuré, alors que le fichier de puissance qu'elle cite dit le contraire : σ_e y est posé égal à τ, jamais mesuré, puisque le sham n'a pas tourné sur les seeds 13-24. Et τ mesure la dispersion ENTRE seeds de d, pas le résidu d'un troisième bras autour de f·d. Cette prémisse ne renverse pourtant pas la lecture dans la plage testée : à σ_e 9,3, P(TRANSPORTE | f=0) reste à 0,855.
- **Preuve** : results/td_step_pilot_r3_puissance_apres_tau.json:2 (σ_e jamais mesuré avant le sceau) contre la règle, ligne 74 (mesuré) ; marge=20|compte=11|sigma_e=9.3 f=0 TRANSPORTE 0.855 >= 0.8
- **Classe** : E8
- **Verdict** : non confirmé (pas de renversement dans la plage de sensibilité)

### P1.d — prémisse centrale
- **Sonde** : `python -I scratchpad/p1_tau.py` (depuis la racine du worktree p419)
- **Constat** : La prémisse centrale est bien mesurée dans CE run : μ 34,5, τ 6,68, trois effets à 26 pas et 9/12 au-dessus de 29. Le d recomputé depuis les 24 cellules est identique au bit à la liste publiée. Les 24 manifestes portent l'image d5341acf, rc 0, arbre propre, et les coûts médians de 106,8 s et 158,1 s sont retrouvés.
- **Preuve** : d recomputé == d_pas publié : True ; moyenne 34.5, écart-type n-1 6.681 ; d==26 : 3 ; d>29 : 9 ; médiane mur lam0 106.8, lam09 158.1
- **Classe** : aucune
- **Verdict** : non confirmé (prémisse mesurée)

## P2 (DÉLÈGUE, régime)
- **Sonde** : `cd C:/Users/robla/VScode_Project/AGAGI/.worktrees/p419 (HEAD d4ca9de9) && python tools/check_regime_claims.py --only <scratchpad>/revue_r3v2/TD-STEP-PILOT-R3.v2.json ; echo EXIT=$?`
- **Constat** : La porte 19 refuse de juger la cible : un brouillon de pre-inscription JSON hors de docs/EDR n'entre pas dans son perimetre, qui ne couvre que les records Markdown. Aucun verdict de regime (CONCORDE, SANS_VALEUR_LUE, DISCORDE) n'est rendu. Conformement a la regle DELEGUE, l'enquete n'est pas rouverte a la main et la porte n'est pas jugee fausse : elle signale correctement que le chemin ne designe aucun record. P2 ne s'appliquera qu'au record R3 a venir, une fois ecrit sous docs/EDR et citant ses results/ suivis.
- **Preuve** : Sortie de la porte : 'REFUS : --only designe 1 chemin(s) INCONNU(S) de cette porte -- ni record docs/EDR/<nom>.md present, ni record supprime par le commit en cours', EXIT=2. Contrat de la porte : tools/check_regime_claims.py:6-8 (--only n'accepte qu'un record docs/EDR/X.md, sinon sortie 2 avant toute analyse). ls docs/EDR | grep R3 rend 0 record TD-STEP-PILOT-R3 (seuls R0 et R2 existent).
- **Classe** : aucune
- **Verdict** : hors périmètre

## P3 (DÉLÈGUE)

### P3.a — balayage du pas : la garde E19 est-elle appelée par le runner de la règle ?
- **Sonde** : `cd C:/Users/robla/VScode_Project/AGAGI/.worktrees/p419 && python tools/check_e19_optimizer_sweep.py --only tools/td_step_pilot_r3.py ; echo EXIT=$?`
- **Constat** : La porte 23 rend OK (code 0) : aucun runner sous gradient sans garde E19, aucune regression, aucun appelant perdu. Le runner R3 est classe NOUVEAU, non bloquant, en categorie regle_absente : il invoque lui-meme la garde, mais la regle qu'il nomme n'est pas encore scellee (la v2 relue est un brouillon), donc la porte ne peut pas lire la grille de pas depuis la regle. Verdict de la porte recopie tel quel ; l'enquete n'est pas rouverte.
- **Preuve** : Sortie : runners scelles 36 | sous gradient 13 | nus 9 | indetermines 5 | non resolus 7 | regle absente 1 | illisibles 0 | appelants de la garde 4 | geles 20 ; [regle_absente] tools/td_step_pilot_r3.py ; OK ; EXIT=0. Appel present en tools/td_step_pilot_r3.py:320 (RULE_R3 = TD-STEP-PILOT-R3 en :48, aucun fichier suivi par git sous ce nom).
- **Classe** : E19
- **Verdict** : non confirmé

### P3.b — reste d'E19, hors du périmètre de la porte
- **Sonde** : `grep -n assert_verdict_invariant_to_optimizer tools/td_step_pilot_r3.py`
- **Constat** : Deux questions ne relevent pas de P3 et passent en P5 sans etre jugees ici : (a) l'appel a la garde n'a lieu que sur une seule branche de la lecture (TRANSPORTE aux deux pas), la porte constate seulement qu'il existe dans le code ; (b) la reference a pas nul vient-elle du meme dispositif et du meme regime. Le statut regle_absente disparaitra au scellement ; il faudra relancer la porte a ce moment-la, apres le gel.
- **Preuve** : tools/td_step_pilot_r3.py:41 (import), :320 (appel unique pour la lecture), :637 (label de l'etape) ; JSON relu, cle controles.e19 (ligne 126) : appel conditionnel
- **Classe** : aucune
- **Verdict** : hors périmètre

## P4

### P4.a — la famille de 144 n'agit sur rien
- **Sonde** : `grep -n "alpha_cell\|control_family" tools/td_step_pilot_r3.py` ; `python3.13 travail/p4_sonde.py TD-STEP-PILOT-R3.v2.json`
- **Constat** : Le nombre 144 n'agit sur rien. L'agrégat le passe à la garde E23 et obtient un seuil par cellule de 0,000347 (Bonferroni), mais aucune branche de classify_pas ne relit ce seuil : toutes les décisions se prennent sur des comptes fixes (10/12, 11/12) et des bandes fixes. Les 144 additionnent aussi des cellules de simulation, dont 24 références qui ne testent rien, au lieu de compter les tests de contrôle réellement appliqués.
- **Preuve** : tools/td_step_pilot_r3.py:720 est la seule occurrence (l'appel lui-même) ; la sonde affiche « famille declaree 144 alpha_cell 0.000347 » ; classify_pas (tools/td_step_pilot_r3.py:170) ne prend aucun alpha en argument
- **Classe** : E23
- **Verdict** : confirmé

### P4.b — garde de dose du sham : 24 tests à bande fixe sans correction
- **Sonde** : `python3.13 travail/p4_sonde.py TD-STEP-PILOT-R3.v2.json` ; `grep -rlF "1,002" tools results docs/ADR docs/EDR docs/roadmap tests/sandbox`
- **Constat** : La famille de contrôles qui peut réellement rompre un pas sur une seule cellule, c'est la garde de dose du sham : 12 cellules par pas × 2 pas = 24 tests, chacun contre une bande fixe [0,9 ; 1,1] de test unique, sans correction de multiplicité. Il suffit d'un rapport hors bande sur les 12 pour que tout le pas bascule en INSTRUMENT_ROMPU. C'est la forme exacte d'EVO-011 (24 cellules, bande fixe : 0,216 de fausse alarme sur un harnais parfait). La bande vient de l'ADR-005:177, une décision, et n'a jamais été confrontée à la dispersion de ce rapport d'un seed à l'autre. La valeur de référence 1,002 n'apparaît dans aucun results/ suivi.
- **Preuve** : tools/td_step_pilot_r3.py:202-204 : une seule entrée dans rompus suffit à rendre la branche INSTRUMENT_ROMPU. Sortie de la sonde : « cellules sham testees par pas 12 x 2 pas = 24 », puis « 12 ratios = 1.0 : TRANSPORTE » contre « 1 ratio = 1.11 sur 12 : INSTRUMENT_ROMPU ». Le grep ne renvoie que tools/td_step_pilot_r3_regle.py et DEPORT-NEXUS-TEMOIN:85, une bande de chronométrage sans rapport
- **Classe** : E23
- **Verdict** : confirmé

### P4.c — puissance mesurée sur des contrôles qui ne peuvent pas échouer
- **Sonde** : `python3.13 travail/p4_sonde.py TD-STEP-PILOT-R3.v2.json`
- **Constat** : La puissance exigée avant le sceau (P(TRANSPORTE | f=0) ≥ 0,8) se mesure sur des injections où aucun contrôle ne peut échouer. Le rapport appliqué/contrefactuel y vaut exactement 1,0 sur les 12 cellules sham. Le contrôle du chemin y est réglé à 400 pas contre 100 pour la référence, sans bruit en v2 (σ = 0). La puissance publiée est donc conditionnelle à des contrôles qui passent avec probabilité 1 : la fausse alarme de la famille n'est pas comptée dans la calibration.
- **Preuve** : tools/td_step_pilot_r3.py:404 (chemin_porte_applique 1.0, contrefactuel 1.0) et :400 (td0_d0 = 400 + N(0, sigma), avec sigma = 0.0 passé par base_injection_v2) ; la sonde affiche « ratios injectes en calibration {1.0} »
- **Classe** : E1
- **Verdict** : confirmé

### P4.d — compte publié à 144 même sans le bras apparié
- **Sonde** : `python3.13 travail/p4_sonde.py TD-STEP-PILOT-R3.v2.json`
- **Constat** : Le compte publié dans le design reste à 144 même quand le pré-vol écarte le bras apparié pour raison de coût. Dans ce cas la lecture n'attend plus que 120 cellules. La raison : l'agrégat calcule ce compte à partir de l'indicateur de la règle, toujours vrai, et non à partir de la décision du pré-vol que suit _bras_lus. Effet nul sur les seuils, puisque l'alpha n'est pas lu, mais le design publié serait faux dans ce cas.
- **Preuve** : tools/td_step_pilot_r3.py:712 utilise c.get("bras_apparie") alors que tools/td_step_pilot_r3.py:78 utilise pv["apparie_retenu"] ; la sonde affiche « bras lus sans apparie [...4 bras] -> cellules 120 contre declarees 144 »
- **Classe** : aucune
- **Verdict** : confirmé

### P4.e — seuil 10/12 hérité de R0-R2
- **Sonde** : python -c sur `results/td_step_pilot_r0.json` : (td0_d0|lr0|seed=s - lr0_reference_d0|lr0|seed=s)*640 pour s=1..12
- **Constat** : Le seuil de 10/12 sur le contrôle du chemin vient de R0-R2 (grille tirée de 640). Au pas primaire, cet héritage ne change rien : dans R0 à lr 4,0, td0_d0 dépasse lr0_reference_d0 d'au moins 172 pas, soit environ 8 fois la marge de 20. Au pas secondaire 4√2, il n'existe aucune mesure (R2 à lr 8 donnait 7/12), donc la question reste ouverte. Je ne la compte pas comme un défaut.
- **Preuve** : écarts mesurés [238, 229, 219, 224, 210, 210, 172, 193, 230, 194, 203, 260], minimum 172 pour n=12, avec _regime.lr_td = [4.0, 8.0]
- **Classe** : aucune
- **Verdict** : non confirmé

## P5

### P5.a — garde E19 consultée seulement après TRANSPORTE aux deux pas
- **Sonde** : `py313 scratchpad/revue_r3v2/travail/p5_sonde_e19.py <v2.json> 300` ; puis `p5_sonde_e19_f2.py <v2.json>` (injection base_injection_v2 sur deux pas, VRAIE lecture_r3, 0 monde)
- **Constat** : La garde E19 n'est consultée qu'après une lecture TRANSPORTE aux deux pas. Le cas qu'elle doit détecter (au second pas, le sham rattrape lam09) aboutit déjà à ATTEND par la lecture pas à pas, sans jamais l'appeler. Elle ne bloque que lorsque les deux pas transportent mais que l'effet est environ trois fois plus grand à l'un d'eux. L'écart sham/trace tient alors aux deux pas : c'est un refus pour une mauvaise raison. Avec deux pas séparés d'un facteur 1,41 seulement (contre 10 dans le cas fondateur de la garde), elle n'apporte rien comme contrôle.
- **Preuve** : Avec f=0 aux deux pas : à mu2 = 34,5, 50 et 70, la garde rend PASSE 238/238, 241/241 et 259/260 ; elle refuse (VERDICT_DEPEND_DU_PAS) 121/255 fois à mu2 = 100 et 262/262 à mu2 = 140. Avec f2 = 1,0 ou 0,5 : la garde n'est jamais appelée (300/300 None pour chaque f2) et la synthèse rend ATTEND (300/300). Sources : td_step_pilot_r3.py:376-377 et experiment_preflight.py:323-325.
- **Classe** : E19
- **Verdict** : confirmé

### P5.b — contrôle positif du chemin confiné à D=0
- **Sonde** : `grep -n 'assert_positive_control|assert_not_degenerate|assert_ablation_changes_something' tools/td_step_pilot_r3.py tools/td_step_pilot.py` ; médianes par bras de `results/td_step_pilot_r0.json` via python -c ; `grep -c CONTROLE_CHEMIN_ECHOUE results/td_step_pilot_r3_*.json`
- **Constat** : Le seul contrôle positif du chemin joué en run (td0_d0) se situe en D=0 : une mise à jour par épisode, opérandes présents en même temps. Il dépasse la marge d'environ dix fois au pas primaire, alors que TD(0) en D=1, le régime du verdict, reste sous la marge face à sa référence. La calibration fixe ce contrôle à +300 pas et ne visite donc jamais sa branche d'échec. Le runner n'appelle aucune des trois gardes d'issues imposées par P5. C'est la pathologie fondatrice d'E19 : un contrôle confiné au régime à un pas ne peut pas voir le régime à deux pas.
- **Preuve** : grep : 0 appel des trois gardes. R0 à lr 4,0 : td0_d0 0,503 contre lr0_reference_d0 0,168, soit ≈193 pas sur 576 contre une marge de 20 ; td0 0,190 contre lr0_reference 0,1625, soit ≈16 pas < 20. Code : td_step_pilot_r3.py:400-402 (td0_d0 fixé à 400, référence à 100). CONTROLE_CHEMIN_ECHOUE : 0 occurrence dans chacun des 3 JSON de calibration. Doctrine : experiment_preflight.py:329-331.
- **Classe** : E19
- **Verdict** : confirmé

### P5.c — td0_app : pas multiplié par rho sans plafond
- **Sonde** : lire tools/td_step_pilot_r3.py:513-518 et 532-535 ; python -c sur `results/td_step_pilot_r0.json` (médianes lr0 / lr1) ; `grep -o 'net|chemin|rho' results/td_step_pilot_r3_tau.json`
- **Constat** : Le bras apparié td0_app multiplie le pas par rho_b sans plafond. Au pas secondaire, un rho au moins égal à racine de 2 l'amène à 8,0 ou plus, valeur où R0 a mesuré la dégradation de TD(0). La condition d'entrée « la trace bat TD(0) à dose nette égale » peut alors être remplie parce que ce bras est plus dur à optimiser, pas parce que la trace transporte. Le contrôle de manipulation ne vérifie que le net atteint, pas le régime du pas. Rho n'a été mesuré nulle part (le pilote tau ne publie que dose_updates).
- **Preuve** : td_step_pilot_r3.py:517 n'exige qu'un rho fini et positif : aucune borne. R0, lr 4,0 contre 8,0 : td0 0,190 contre 0,172, td0_d0 0,503 contre 0,232. JSON v2 ligne 25 : p2 = 5,657 ; 5,657 × 1,414 = 8,0. Le pilote tau ne contient aucun champ net/chemin/rho : seulement 24 occurrences de dose_updates.
- **Classe** : E19
- **Verdict** : confirmé

### P5.d — référence lr 0
- **Sonde** : lire tools/td_step_pilot_r3.py:550-572 ; python -c sur `results/td_step_pilot_r0.json` (lr0_reference|lr0 et |lr1 identiques)
- **Constat** : La référence lr 0 est construite au même seed, sans aucun épisode, et évaluée exhaustivement par argmax. Elle relève donc du même dispositif que les bras entraînés, à leur état initial. Aucun défaut retenu.
- **Preuve** : r3.py:562 : entraine(sd, 0.0, 0, ..., 0.0, eval_exhaustive=True). R0 : lr0_reference vaut 0,1625 aux deux pas et lr0_reference_d0 0,168 aux deux pas.
- **Classe** : aucune
- **Verdict** : non confirmé

## P6

### P6.a — f-chapeau sans no-op mesuré
- **Sonde** : `grep -niE "no.?op" scratchpad/revue_r3v2/TD-STEP-PILOT-R3.v2.json` ; `sed -n 115,118p tests/sandbox/test_credit_trace_delta_sham.py`
- **Constat** : Le ratio qui porte le verdict, f-chapeau = somme des e sur somme des d, n'a aucun no-op mesure a cote de lui : parmi les cinq bras de chaque pas, aucun sham en mode identite (delta-tilde egal a delta), seul dispositif dont la valeur attendue est connue (f = 1) et qui donnerait la bande de f-chapeau. Ce no-op n'existe qu'en test unitaire, compare sur W en tolerance 1e-5 apres 3 episodes, et declare lui-meme non exact au bit ; ce que devient cet ecart apres 3000 episodes, lu en succes sur 576 couples, n'est mesure nulle part (cf. run_ablation_map, 1,058 et 0,922 sur un no-op). Aucune cellule des seeds 1-12 n'existe : comparer le contraste a une bande est impossible aujourd'hui, et le restera au sceau faute de bande.
- **Preuve** : grep no.?op : 1 occurrence, cible:121 (no-op de l'instrument de dose, tests/sandbox/test_td_step_pilot_r3.py:424-430, pas du contraste) ; cible:33-39 cinq bras, aucun identite ; tests/sandbox/test_credit_trace_delta_sham.py:115-118 atol=1e-5 sur 3 episodes, test nomme ..._allclose_not_bit_exact
- **Classe** : E8
- **Verdict** : confirmé

### P6.b — σ_e emprunté à un autre contraste
- **Sonde** : `python -I -c "import json,statistics as st; c=json.load(open('results/td_step_pilot_r3_tau.json',encoding='utf-8'))['cellules']; print(sorted({k.split('|')[0] for k in c}),len(c),len(set(c))); d=[c[f'lam09|seed={s}']['succes']-c[f'lam0|seed={s}']['succes'] for s in range(13,25)]; print(d,st.mean(d),st.stdev(d))"`
- **Constat** : La bande qui calibre la lecture de f-chapeau (sigma_e) est empruntee a un AUTRE contraste : elle vaut tau, ecart-type entre seeds de lam09 moins lam0, que je retrouve a 6,681 sur un fichier qui ne contient QUE ces deux bras (24 cellules, 0 sham, 0 replicat d'une meme cellule). Tau decrit l'heterogeneite de l'effet d'un seed a l'autre, pas l'ecart d'un no-op du sham ; le residu du sham autour de f fois d n'a jamais ete observe.
- **Preuve** : sortie : bras ['lam0','lam09'], 24 cellules, 24 cles uniques ; d=[44,26,41,26,37,43,33,26,41,32,34,31], moyenne 34,5, ecart-type 6,681 ; cible:74 pose sigma_e = tau et precise que le sham n'a jamais tourne sur 13-24
- **Classe** : E6
- **Verdict** : confirmé

### P6.c — déterminisme par seed déclaré, non mesuré
- **Sonde** : même commande python sur `results/td_step_pilot_r3_tau.json` (len(c) contre len(set(c)), puis sum(x>20), sum(x>29) sur d)
- **Constat** : Le modele v2 retire tout bruit de replication (deux executions d'une meme cellule supposees identiques) en invoquant le determinisme par seed, et c'est ce retrait qui autorise la marge a passer de 29 a 20 pas. Ce determinisme n'est verifie par aucune mesure sur nexus pour ce substrat torch : 24 cles uniques sur 24 dans tau.json, aucun double, et le lien au bit avec R0 est publie sans etre exige. Doubler une cellule (29 a 158 s) fournirait le no-op exact qui manque.
- **Preuve** : 24 cellules / 24 cles uniques (0 replicat) ; d>20 : 12/12, d>29 : 9/12 ; cible:74 (determinisme declare, pas mesure) ; cible:98 (marge 29 -> 20 justifiee par ce modele) ; cible:113 lien au bit avec R0 non exige
- **Classe** : E8
- **Verdict** : confirmé

### P6.d — 1,002 sans évidence
- **Sonde** : `git grep -nE "1[.,]002"` ; `git grep -c "1\.002" -- results` ; `git log --oneline -S "1,002" -- tools/ docs/`
- **Constat** : La seule valeur de bruit accrochee a la garde de dose du sham, 1,002, ne renvoie a aucune evidence : aucun fichier de results suivi ne la porte, et sa seule autre occurrence au depot est la bande d'un rapport de COUT (duree du runner) dans DEPORT-NEXUS-TEMOIN, un contraste sans rapport avec le ratio applique sur contrefactuel. Soit c'est cet emprunt, et ce n'est pas le no-op de cette garde ; soit c'est une autre mesure, a citer avec son fichier.
- **Preuve** : 3 occurrences : tools/td_step_pilot_r3_regle.py:94, docs/EDR/DEPORT-NEXUS-TEMOIN_Meme_Seed_Batcave_Contre_Nexus.md:85 (nexus 1,002 runner, rapport de cout), docs/reviews/2026-09-26-DEPORT-NEXUS-TEMOIN_Meme_Seed_Batcave_Contre_Nexus.md:145 ; results : 0 fichier ; dans la regle, introduit par d4ca9de9 seul ; cible:98
- **Classe** : E8
- **Verdict** : confirmé

### P6.e — ratios descriptifs sans bande
- **Sonde** : `grep -niE "no.?op" scratchpad/revue_r3v2/TD-STEP-PILOT-R3.v2.json` ; `sed -n 111p` de la cible
- **Constat** : Deux ratios descriptifs annoncent une direction sans aucune bande : chemin du sham rapporte a celui de la trace (0,82 attendu contre 1) et cohérence net sur chemin (sous 1 contre 1 environ). Ils comparent deux cellules distinctes dont les trajectoires divergent, donc leur dispersion sous un no-op est inconnue et l'ecart de 0,18 n'est pas lisible ; aucun no-op n'est declare pour eux.
- **Preuve** : cible:111 (0,82 contre 1 ; < 1 contre environ 1, aucune bande) ; grep no.?op : 1 seule occurrence, cible:121, qui vise l'instrument de dose
- **Classe** : aucune
- **Verdict** : confirmé

### P6.f — fichiers cités absents
- **Sonde** : `ls results/td_step_pilot_r3*` ; `git ls-files results | grep -cE "td_step_pilot_r3_(calibration_lecture|prevol)\.json"`
- **Constat** : Deux fichiers cites comme pieces du dispositif (calibration de la lecture, publiee avant sceau ; pre-vol fige) sont absents du disque et de l'index : brouillon non scelle, question de provenance (P9), pas de plancher de bruit.
- **Preuve** : 4 fichiers r3 suivis (calibration_lecture_brouillon_v1, puissance_apres_tau, sonde_puissance_v2, tau) ; grep -c : 0 ; cible:54 et cible:123 les citent
- **Classe** : aucune
- **Verdict** : hors périmètre

## P7

### P7.a — dose du contrôle positif non déclarée
- **Sonde** : `python -I -c "import json,collections; [print(f, sorted(collections.Counter((k.split('|')[0],v['updates'],v.get('trace_updates')) for k,v in json.load(open(f,encoding='utf-8'))['_dose'].items() if isinstance(v,dict) and 'updates' in v).items())) for f in ['results/td_step_pilot_r0.json','results/td_step_pilot_r2.json']]"` ; `grep -c -i 'updates|mises à jour|appels' TD-STEP-PILOT-R3.v2.json` ; `grep -n 'def _spec' -A4 tools/td_step_pilot_r3.py`
- **Constat** : Le contrôle positif du chemin (bras sans délai) reçoit DEUX FOIS MOINS de mises à jour TD que les bras D=1 qu'il calibre : sa séquence n'a qu'un pas, donc seul le flush terminal met à jour. La règle ne déclare ce compte nulle part. Le résumé de dose de l'agrégat ne couvre que lam0, lam09 et sham09 : une issue CONTROLE_CHEMIN_ECHOUE sortirait sans afficher à côté d'elle la dose du bras qui échoue (le compte brut n'existe que dans le dict de chaque cellule). Le docstring dit que le contrôle apprend « à cette dose ». La mesure donne la moitié des mises à jour totales ; l'égalité ne vaut que pour les mises à jour récompensées (une par épisode). Conséquence limitée : un échec du contrôle mène à ATTEND, jamais à un verdict négatif.
- **Preuve** : R0 : td0_d0 updates=3000 (24 cellules) contre td0 6000 (24) et tdlam 6000 (24) ; R2 : td0_d0 3000 (12) contre lam099 6000 (24). Le grep dans la règle rend 0. Positions : tools/td_step_pilot_r3.py:89 (td0_d0 = same_tick True), tools/bilinear_composition_probe.py:76-81 (séquence à un seul pas), tools/td_step_pilot.py:222-223 (le flush est la seule mise à jour), tools/td_step_pilot_r3.py:271 (descripteurs limités à 3 bras), tools/td_step_pilot.py:165-166 (« à cette dose »), TD-STEP-PILOT-R3.v2.json:120 (contrôle positif décrit sans sa dose).
- **Classe** : E8
- **Verdict** : confirmé

### P7.b — dose des bras testés publiée
- **Sonde** : `python -I -c "import json,glob,collections; c=collections.Counter(); [c.update([(d.get('bras'),d['dose'].get('updates'),d['dose'].get('trace_updates'),d['dose']['dose_instrument'].get('appels_td_update'))]) for d in (json.load(open(f,encoding='utf-8')) for f in glob.glob('results/td_step_pilot_r3_tau/*.json'))]; print(c)"`
- **Constat** : Pour les bras testés, le compte de mises à jour reçues est bien publié, par le code et non par la règle. Chaque cellule écrit updates, trace_updates et appels_td_update, et l'agrégat recopie le dict de dose entier. Rien ne manque à la publication.
- **Preuve** : Cellules τ : lam0 (6000, 0, 6000) ×12 et lam09 (6000, 6000, 6000) ×12. tools/td_step_pilot_r3.py:675 recopie le dict entier (db['_dose'][k] = rec['dose']). tools/td_step_pilot.py:246-247.
- **Classe** : aucune
- **Verdict** : non confirmé

### P7.c — létalité
- **Sonde** : `grep -c -i 'resurrect|mort\b|death|alive' tools/td_step_pilot.py tools/td_step_pilot_r3.py` ; comptage de n_agents dans `results/td_step_pilot_r3_tau/*.json`
- **Constat** : Aucune mort ni résurrection n'est possible : le pilote n'a pas de monde, et la population de 16 têtes est construite une fois puis ne change plus. Un nul ne peut donc pas être un nul de létalité.
- **Preuve** : 0 et 0 occurrence ; n_agents = 16 dans 24 cellules τ sur 24 ; tools/td_step_pilot.py:196 (population construite une seule fois).
- **Classe** : aucune
- **Verdict** : non confirmé

### P7.d — références à pas nul non entraînées
- **Sonde** : `python -I -c "import json; d=json.load(open('results/td_step_pilot_r0.json',encoding='utf-8')); print([(k,v['updates'],v['trace_updates']) for k,v in d['_dose'].items() if k.startswith('lr0_reference|')][:2])"` ; `grep -n 'lr 0' tests/sandbox/test_td_step_pilot_r3.py`
- **Constat** : Les références à pas nul de R3 ne s'entraînent pas (0 mise à jour), alors que celles de R0 en recevaient 6000 à pas nul. Un témoin garantit l'équivalence, et à pas nul la dose en paramètres est nulle des deux côtés.
- **Preuve** : R0 : lr0_reference seed 1 et 2 à (6000, 0) ; R3 : tools/td_step_pilot_r3.py:562, avec 0 épisode. Témoins : tests/sandbox/test_td_step_pilot_r3.py:5 et :434.
- **Classe** : aucune
- **Verdict** : non confirmé

## P8 (JUGE)

### P8.a — corps (E26)
- **Sonde** : `grep -c phenotype tools/td_step_pilot.py tools/td_step_pilot_r3.py tools/bilinear_composition_probe.py` ; `grep -n 'phenotype_hp_bonus = ' src/agents/mamba_agent.py` ; `Python313 scratchpad/revue_r3v2/travail/p8_sonde.py` (un seul forward, aucun monde)
- **Constat** : Les mises a jour TD, trace et sham ecrivent sur toutes les lignes sources de W, y compris 0..10 d'ou mamba_agent tire hp_bonus et inv_capacity (l'observation est non nulle jusqu'au slot 10, donc ces lignes recoivent du gradient). Mais aucun monde ne consomme ce phenotype : il est calcule une seule fois au constructeur et aucun des trois modules du pilote ne le lit. Tache proxy sans corps : la question E26 ne s'applique pas a cette regle.
- **Preuve** : grep -> 0 / 0 / 0 ; src/agents/mamba_agent.py:77 et :83 (phenotype pose au __init__/reset, jamais relu par le pilote) ; sonde : slots obs non nuls max = 10 ; grep kuzu|world_1|make_world dans les deux runners -> 0 / 0
- **Classe** : E26
- **Verdict** : hors périmètre

### P8.b — chevauchement entrée/sortie (E24)
- **Sonde** : `Python313 tools/check_io_overlap.py` ; `Python313 p8_sonde.py` ; `grep -n '^_VALUE_NODE|^_MOVE_LOGITS|^_GRAB_NODE|^_RUB_NODE' src/agents/backend_torch.py`
- **Constat** : Le sujet n'est pas un genome du HoF mais seize MambaAgent neufs aux dimensions par defaut : la somme entrees + sorties reste sous le nombre de noeuds (5 caches), la lecture d'action commence au noeud 64 et les noeuds lus par l'eval (logits 0..5), la valeur (28) et grab/rub (24/25) sont hors du bloc d'entree. La porte 17 ne juge que les genomes persistes et ne couvre donc pas ce sujet : la sonde directe tranche a sa place.
- **Preuve** : check_io_overlap : 358 genomes, 10 chevauchants connus, 0 nouveau, exit 0 ; sonde : I O N = 59 108 172, I+O = 167 < 172, debut lecture N-O = 64 ; src/agents/backend_torch.py:32-35 (8 / 24 / 25 / 28)
- **Classe** : E24
- **Verdict** : non confirmé

### P8.c — vue de l'état récurrent (aliasing)
- **Sonde** : `Python313 p8_sonde.py` ; `grep -n assert_no_aliasing tools/td_step_pilot.py tools/td_step_pilot_r3.py tools/td_step_pilot_r3_regle.py` ; `grep -n 'd.clone()|theta0 = ' src/agents/backend_torch.py tools/td_step_pilot.py`
- **Constat** : forward rend effectivement une VUE de agent.H (le tableau numpy partage sa memoire) ; le pilote ne fait que la lire (softmax qui recopie, argmax) et l'etat ressort bit-identique apres echantillonnage ; le tampon delta-tilde et theta_0 de l'instrument de dose sont des clones. Innocuite reelle mais NON GARDEE : aucun appel a assert_no_aliasing, elle repose sur l'absence d'ecriture. Risque latent (dette eventuelle), pas un defaut du dispositif.
- **Preuve** : shares_memory(logits, H) = True oppose a 'H inchange apres _sample+argmax = True' ; src/agents/backend_torch.py:223-235 (logits = H_new[:, N-O:N] puis .cpu().numpy()) ; backend_torch.py:409 (d.clone()) ; td_step_pilot.py:86 (theta0 clone) ; assert_no_aliasing : 0 appel dans les trois runners
- **Classe** : E5
- **Verdict** : non confirmé

## P9

### P9.a (DÉLÈGUE) — porte 20, provenance
- **Sonde** : `python tools/check_evidence_provenance.py --only <scratchpad>/revue_r3v2/TD-STEP-PILOT-R3.v2.json` (worktree p419, HEAD d4ca9de9)
- **Constat** : La porte refuse la cible avec le code 2. Un brouillon JSON posé hors du dépôt n'est pas un record docs/EDR, donc elle ne rend aucun verdict de provenance sur ce texte. Recopie du verdict, arrêt.
- **Preuve** : sortie : « REFUS : --only designe 1 chemin(s) INCONNU(S) de cette porte » ; EXIT=2 ; périmètre déclaré à tools/check_evidence_provenance.py:90 (ne lit que docs/EDR/*.md)
- **Classe** : aucune
- **Verdict** : hors périmètre

### P9.b (DÉLÈGUE) — sceau de la pré-inscription
- **Sonde** : `python -c "from tools.preregister import verify; verify('TD-STEP-PILOT-R3')"` ; `ls docs/preregistrations | grep TD-STEP-PILOT` ; `python -I -c` qui applique declare_un_cout, _assert_exhaustive et _seal à la cible
- **Constat** : Aucune règle TD-STEP-PILOT-R3 n'est scellée (seules R0, R1, R1-bis et R2 existent). C'est cohérent avec le statut de brouillon annoncé par d4ca9de9 : il n'y a pas de sceau à confronter. Au scellage, reviewed_by sera exigé (la clé cout est présente). L'exhaustivité des branches passe déjà. Empreinte provisoire : 85a1be73.
- **Preuve** : FileNotFoundError levée à tools/preregister.py:196, EXIT=1 ; 4 fichiers TD-STEP-PILOT (R0, R1, R1-bis, R2) ; declare_un_cout=True ; seal 85a1be738ce3c392
- **Classe** : aucune
- **Verdict** : hors périmètre

### P9.c — l'oracle de la porte 20 appliqué au brouillon (la porte elle-même refusait la cible)
- **Sonde** : `python <scratchpad>/revue_r3v2/travail/p9_evaluer.py <cible>` ; `git log --all --oneline -- results/td_step_pilot_r3_calibration_lecture.json`
- **Constat** : Avec les fonctions de la porte elle-même (evaluer, _tracked, _dans_head), le texte cite 5 chemins. Trois sont suivis et présents dans HEAD : tau, puissance_apres_tau et brouillon_v1. Deux sont absents. Le pré-vol est un produit du run, donc son absence est normale. En revanche, le fichier de calibration de la lecture v2, promis comme publié avant le scellage, n'existe nulle part : ni sur le disque, ni dans l'index, ni dans aucun commit. La marge 20 ne s'appuie donc que sur la mesure préliminaire à 400 répétitions, que la règle classe elle-même hors règle. Sceller en l'état ferait citer une évidence inexistante.
- **Preuve** : statut ABSENT ; td_step_pilot_r3_calibration_lecture.json : existe False, index False, HEAD False ; git log --all : 0 ligne ; citation à TD-STEP-PILOT-R3.v2.json:123 (le prevol.json absent est cité à la ligne :54)
- **Classe** : E27 au sens de CLAUDE.md (porte 20). Discordance à consigner : REGISTRE_ERREURS.md:62 définit E27 autrement (la vérification réécrit l'évidence).
- **Verdict** : confirmé

### P9.d — vu en passant ; relève aussi de P10
- **Sonde** : grep -n de 'verify(RULE_R3' et de 'calibration_lecture' dans tools/td_step_pilot_r3.py ; Read de tools/td_step_pilot_r3.py:772-820 et de tools/preregister.py:115-149 ; lecture du bloc _provenance de results/td_step_pilot_r3_calibration_lecture_brouillon_v1.json
- **Constat** : Dans le runner, un seul chemin écrit ce fichier : la sous-commande calibrer-lecture. Or elle ne s'exécute qu'après verify(RULE_R3), qui lève tant que rien n'est scellé. La voie que nomme la règle ne peut donc produire la calibration qu'APRÈS le sceau, et stamp() y inscrirait ce sceau. De plus, preregister() ne contrôle pas l'existence de la calibration : l'ordre promis n'a aucune application exécutable. La v1 avait été produite par un chemin ad hoc (sa provenance porte brouillon_regle_sha256 ec1a30c6).
- **Preuve** : tools/td_step_pilot_r3.py:795 (regle = verify(RULE_R3)) s'exécute avant les lignes :813-818 (calibrer-lecture, qui écrit td_step_pilot_r3_calibration_lecture.json) ; tools/preregister.py:196 lève si la règle n'est pas scellée ; tools/preregister.py:115-149 ne contient aucun contrôle de calibration
- **Classe** : E10
- **Verdict** : confirmé

## P10

### P10.a — un fil par cellule non imposé
- **Sonde** : `grep -n 'def soumettre\|add_argument("--cpu"' tools/jobs/remote.py` ; `grep -n 'n = str(max(1, int(lim)))' tools/jobs/remote_entry.py` ; `sed -n 655,679p tools/td_step_pilot_r3.py | grep -c 'threads\|limite_cpu'` ; `python -I -c` (compteur des cellules de results/td_step_pilot_r3_tau.json par image, sha, fils posés, limite_cpu) ; `git ls-files runs/p419 | wc -l`
- **Constat** : Le régime fixe un seul fil par cellule, mais rien dans le code de R3 ne l'impose. Le déport soumet par défaut avec une limite de deux processeurs, donc deux fils. L'agrégat n'écarte aucune cellule sur ce critère : il ne lit ni la limite cgroup ni les fils posés. Or tau a été mesuré à un fil, sur 24 cellules sur 24, et le seul script qui passait --cpu 1 (celui de tau) n'est pas suivi par git. Une cellule soumise sans l'option serait donc acceptée et lue, avec une unité CPU de pré-vol (qui décide du bras apparié) et une arithmétique float32 éventuellement différentes.
- **Preuve** : tools/jobs/remote.py:748 (soumettre cpu=2.0) et :1436 (--cpu default=2.0) ; tools/jobs/remote_entry.py:322 (fils = int(limite)) ; tools/td_step_pilot_r3.py:660-669 : 0 occurrence de threads/limite_cpu dans le bloc d'exclusion ; tau : 24/24 cellules à limite_cpu 1.0, OMP=1, sha 67888a3a ; runs/p419 : 0 fichier suivi (vague_tau.sh:20 portait --cpu 1)
- **Classe** : E10
- **Verdict** : confirmé

### P10.b — INSTRUMENT_ROMPU sur terme reporté en tête d'épisode : impossible par construction
- **Sonde** : `grep -n 'e.zero_()' src/agents/backend_torch.py` ; `sed -n 211,214p tools/td_step_pilot.py` ; lecture de tools/td_step_pilot.py:107-114
- **Constat** : La condition INSTRUMENT_ROMPU sur un terme reporté non nul en tête d'épisode ne peut pas se déclencher. Le compteur inspecte les traces juste après que la remise à zéro les a vidées en place, et non la mise à jour appliquée au rang 0. Il vaut donc 0 par construction. Dans ce bloc, seuls le compte des omissions et le rapport des chemins peuvent réellement faire échouer l'instrument.
- **Preuve** : src/agents/backend_torch.py:431-434 (zero_ sur tous les e_a/e_v quand le masque vaut None) ; tools/td_step_pilot.py:212-214 (apres_reset appelé juste après reset_traces) ; tools/td_step_pilot.py:112-114 (compte les e non nuls, donc 0)
- **Classe** : E1
- **Verdict** : confirmé

### P10.c — indicateur d'ordre aveugle aux références
- **Sonde** : `py -3.13 -c "from tools.td_step_pilot_r3 import _cle_ref,_cle; print('|pas=p1|' in _cle_ref('lr0_reference',1), '|pas=p1|' in _cle('lam0','p1',1))"`
- **Constat** : L'indicateur d'ordre entre les deux étapes ne retient que les cellules dont la clé contient le pas. Les références lr 0, que la règle range dans la première étape, ont une clé sans pas : elles n'entrent jamais dans le maximum des fins. Une référence lancée après le début de la seconde étape laisserait donc l'indicateur à vrai. Il est seulement publié, aucune branche ne le lit.
- **Preuve** : sortie : référence False, bras lam0 True ; tools/td_step_pilot_r3.py:61 (_cle_ref sans pas) et :697 (filtre f'|pas={p1}|')
- **Classe** : E32
- **Verdict** : confirmé

### P10.d — taille de famille selon le drapeau
- **Sonde** : `sed -n 712,713p tools/td_step_pilot_r3.py` ; `sed -n 628,629p tools/td_step_pilot_r3.py`
- **Constat** : La taille de famille passée à assert_control_family suit le drapeau de la règle, et non la décision du pré-vol. Si le bras apparié est écarté pour son coût, 120 cellules tournent alors que 144 sont déclarées (erreur dans le sens conservateur). C'est le comptage réel des cellules, donc du ressort de P4.
- **Preuve** : tools/td_step_pilot_r3.py:712 (int(bool(c.get('bras_apparie')))) contre :628 (retenu = frac < seuil)
- **Classe** : aucune
- **Verdict** : hors périmètre

### P10.e — autres affirmations sur le mécanisme
- **Sonde** : Read de src/agents/backend_torch.py:159-178 et :370-434, de tools/td_step_pilot.py:162-265 et de tools/td_step_pilot_r3.py:132-157, 244 et 598 ; grep image_ref dans tools/jobs/remote.py ; python -I -c sur results/td_step_pilot_r3_tau.json
- **Constat** : Les autres affirmations sur le mécanisme résistent à la lecture du code. Le compteur d'omissions vaut B une seule fois (épisode 1, rang 1), donc 16. Le pas par agent est nominal/B, soit 0,25 et 0,354. Le seuil de f̂ vaut marge × 12. La regex d'image retrouve le digest que le déport écrit après @. Le multiplicateur par bloc agit sur l'unique groupe SGD. Le sham décale bien δ d'un épisode dans le seul terme reporté. L'évaluation exhaustive ne fait aucun tirage. Enfin, mu = 34,5 et tau = 6,68 se recalculent depuis le JSON de tau.
- **Preuve** : backend_torch.py:388-389 et :178 ; td_step_pilot.py:204 ; remote.py:413 (f'...@{digest}') ; tau : moyenne_pas 34.5, tau_pas 6.681, 3 seeds à 26 pas
- **Classe** : aucune
- **Verdict** : non confirmé

---

**Bilan** : 38 critiques, dont 20 confirmées, 11 non confirmées, 7 hors périmètre.

---

## Addendum de l'auteur (2026-10-14)

**Passage INDISCRIMINANT** (le témoin cru sain LOCK-002 rend 6 critiques recevables) : une critique confirmée n'est
retenue qu'une fois RE-MESURÉE par l'auteur. Les vingt l'ont été, par lecture du code à la ligne et par une sonde pure
(`runs/p419/reverif_revue_v2.py`, hors git : agrégat τ, cellules τ, R0, aucun monde). **Les vingt sont retenues.**
Coût de la revue : 19 agents, 2 383 960 jetons, 45 min de mur.

**Corrigé sans décision (code, tests, texte de la règle -- règle v2.1) :**
- **P4.d / P10.d** : la famille déclarée suit la décision du PRÉ-VOL (120 si le bras apparié est écarté), plus le drapeau.
- **P7.a** : la dose (mises à jour) de CHAQUE bras est publiée à côté de la lecture, `td0_d0` compris -- re-mesuré : 3000
  contre 6000 en R0 ; la règle le déclare.
- **P10.a** : l'agrégat EXCLUT et nomme une cellule dont la limite CPU ou les fils posés ≠ 1 (re-mesuré : le déport
  soumet à 2,0 CPU par défaut) ; la procédure des vagues, désormais dans git (`tools/td_step_pilot_r3_vague.py`),
  fige `--cpu 1`.
- **P10.b** : la condition « terme porté non nul au rang 0 » ne pouvait pas échouer (re-mesuré : `apres_reset` lit les
  traces juste après `reset_traces`, qui les met à zéro en place) -- retirée d'INSTRUMENT_ROMPU, publiée seulement ;
  le test qui la faisait « échouer » par injection est remplacé par un test qui dit pourquoi elle ne l'est plus.
- **P10.c** : les références comptent dans l'étape 1 de l'indicateur d'ordre (témoin : une référence finie après le
  début de l'étape 2 rend l'indicateur faux).
- **P1.b** : le pré-vol relie chaque cellule à son MANIFEST et REFUSE des fenêtres d'exécution qui se chevauchent --
  re-mesuré : sur le pilote τ, le temps CPU d'un même bras à dose identique va de 28,0 à 146,0 s (×5,2) ; les 5
  cellules du pré-vol se soumettent UNE À UNE.
- **P1.a (en partie)** : l'agrégat τ publie désormais son dispositif (pas 4,0, λ, épisodes, agents, K, grille, bras,
  seeds) ; τ et les cellules inchangés au bit à la ré-agrégation.
- **P6.b** : σ_e est écrit SUPPOSÉ égal à τ, jamais mesuré.
- **P6.d** : le « 1,002 » est retiré (re-mesuré : aucune évidence suivie, ses deux autres occurrences sont un rapport
  de COÛT de DEPORT-NEXUS-TEMOIN) ; la bande [0,9 ; 1,1] est dite une décision de l'ADR jamais confrontée à la
  dispersion du rapport.
- **P6.e** : les rapports descriptifs (chemin sham/trace, cohérence) sont dits SANS bande.
- **P9.c / P9.d** : `tools/td_step_pilot_r3_regle.calibrer()` calibre la lecture AVANT le sceau, sur le brouillon, et
  inscrit l'empreinte de la règle calibrée ; `sceller()` est le seul chemin vers le sceau et REFUSE tant qu'une
  question reste ouverte, que la calibration manque, qu'elle porte l'empreinte d'une autre règle ou que son exigence
  n'est pas tenue (témoins à réponse connue).

**À décider par robla (règle v2.1, questions ouvertes 4 à 9, en plus des 1 à 3 du v2) :**
- **(4) P1.a** -- puissance au pas 4√2 inconnue ; la jointe sous indépendance vaut ≈ 0,80 / 0,73. Proposition : μ et τ
  au pas 4√2 sur les mêmes seeds tenues à l'écart (24 cellules nexus, lam0 et lam09).
- **(5) P5.c** -- re-mesuré sur les cellules τ : ρ_b va de 1,03 (bloc 1) à 1,49-1,88 (bloc 6), donc le TD(0) apparié
  tourne jusqu'à 7,5 au pas 4,0 et ≈ 10,6 au pas 4√2, régime où R0 mesure TD(0) dégradé.
- **(6) P5.a** -- rôle de la garde E19 à deux pas séparés de √2.
- **(7) P4.a-c** -- famille réellement lue, multiplicité de la garde de dose du sham, contrôles injectés qui ne
  peuvent pas échouer.
- **(8) P6.a / P6.c** -- no-op de f̂ (bras « sham identité ») ; déterminisme par seed à mesurer (2 cellules dupliquées).
- **(9) P5.b** -- contrôle positif au régime D=1 (re-mesuré : TD(0) à D=1 reste à une médiane de 13,9 pas au-dessus de
  sa référence en R0, sous la marge).

**Hors périmètre, suite donnée** : P2, P9.a (portes 19 et 20 hors périmètre d'un brouillon) -- elles jugeront le record ;
P3.b -- porte 23 à relancer au sceau ; P6.f, P9.b -- fichiers et sceau propres au run, attendus ; P8.a, P10.d -- traités
ou sans objet. **Discordance relevée par P9.c, à consigner au registre** : la revue cite E27 au sens de CLAUDE.md (porte
20), alors que `REGISTRE_ERREURS.md` définit E27 autrement.
