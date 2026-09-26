# Revue adversariale — S2-BASSIN-FRAGILITY (v3)

- **Cible** : `C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/S2-BASSIN-FRAGILITY.v3.json` (pré-inscription, brouillon non scellé ; `_seal(v3)` = `9b5f045e4d0eca5059ceb7944e3c32bbba710055743ae1c3793286e61e5ba0c1`)
- **Date** : 2026-09-26
- **SHA** : `82927108f6244537bee0a35d44fa06dcf36cea03` (worktree `.worktrees/science`)

## Résultat des TÉMOINS (avec les deux planchers)

| témoin | statut | code | critiques recevables |
|---|---|---|---|
| S2-BLIND-CHAMPION-42e9357 | RETROUVE | 0 | 7 |
| EDR-GRAB-COST-1828371 | RETROUVE | 0 | 6 |
| EDR-RETAIN-COMPOSE-4204f8f | RETROUVE | 0 | 8 |
| LOCK-002-286f244 (cru sain) | MESURE | 0 | 5 |

- PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5
- plancher mesure sur LOCK-002-286f244 : 5 critiques recevables (seuil historique 1) -- S n'est pas imprime par --verifier : lu par verdict_temoin du meme script (seuil=1, depasse_le_seuil=True)

Commandes rejouables (fichiers de critiques sous `scratchpad/refutateur_v3/`, témoins sous `scratchpad/temoins/`) :

    PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier S2-BLIND-CHAMPION-42e9357 <scratchpad>/refutateur_v3/critiques-S2-BLIND-CHAMPION-42e9357.json --extrait <scratchpad>/temoins/temoin-1.md --jugement OUI
    PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier EDR-GRAB-COST-1828371 <scratchpad>/refutateur_v3/critiques-EDR-GRAB-COST-1828371.json --extrait <scratchpad>/temoins/temoin-3.md --jugement OUI
    PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier EDR-RETAIN-COMPOSE-4204f8f <scratchpad>/refutateur_v3/critiques-EDR-RETAIN-COMPOSE-4204f8f.json --extrait <scratchpad>/temoins/temoin-4.md --jugement OUI
    PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier LOCK-002-286f244 <scratchpad>/refutateur_v3/critiques-LOCK-002-286f244.json --extrait <scratchpad>/temoins/temoin-2.md

⚠️ Le témoin cru sain dépasse son seuil historique (5 contre 1) : l'instrument ne sépare pas nettement un texte sain d'un défectueux sur ce passage ; ce compte est publié, il n'annule rien.

Bilan : 40 critiques, **26 confirmées**, 11 non confirmées, 3 hors périmètre.

---

## P1

### P1.1
- **Sonde** : `python -c "import json,statistics as st;a=json.load(open('results/s2_credit_ablation.json',encoding='utf-8'))['rows'];b=json.load(open('results/s2_credit_ablation_2.json',encoding='utf-8'))['rows'];r=[x['dW_tdoff']/y['dW_eplr'] for x,y in zip(a,b)];print(st.median(r),min(r),max(r),st.median(x['dW_full']/x['dW_lr'] for x in a))"` — sortie : 1.363 0.828 2.838 8.276 ; seed 2027 dW_tdoff 1139.1 < dW_eplr 1376.2 ; doses épisodiques égales (250/250) ; clause_E19 ligne 4 et 10bis ligne 8 de la cible.
- **Constat** : La garde 10bis attribue au pas un éventuel refermement de l'écart sham-crédit, en prenant pour acquis que 0,04 contre 0,004 décale de dix fois le déplacement sur la voie épisodique. Or les JSON publiés montrent que ce réglage déplace à peine le chemin sur cette voie : tdoff/eplr = 1,36 en médiane (0,83 à 2,84 ; au seed 2027 le petit pas fait le chemin le PLUS long), contre 8,3 pour la paire TD+épisodique full/lr au même facteur. Le rapport vient de la config ; le déplacement effectif n'a jamais été mesuré comme prémisse. Une invariance rendue par 10bis ne dirait rien d'un pas dix fois plus petit, et un refermement lu DIRECTION_DEPEND_DU_PAS (qui envoie en 11d) opposerait deux bras de dose presque égale.
- **Classe** : E19
- **Verdict** : confirmé — prémisse porteuse de 10bis tirée de la config, contredite par la dose publiée

### P1.2
- **Sonde** : python -c (lignes de results/s2_credit_ablation.json) : median(dW_tdoff)/12 ; numpy : np.abs(W0).sum() sur scratchpad/p418_W_p416_b_full_2026.npz ; net_over_path lu dans results/s2_bassin_fragility_sonde_conception.json — sortie : chemin tdoff 101.27 par agent ; L1(W0) 2442.8 -> 4 % = 97.7 ; net/chemin mesurés 0.072 / 0.081 / 0.358 / 0.201 / 0.112 ; ligne 29 de la cible.
- **Constat** : La prédiction range b_tdoff avec les bras à plus grand déplacement net, vers 4 % de la norme L1 du bassin. Ce bras n'a pas été rejoué, donc ce chiffre n'a pas été mesuré. Il est de plus borné par les données publiées : le net ne peut pas dépasser le chemin, qui vaut 101 par agent en médiane pour tdoff, et 4 % de 2442,8 font 97,7. Il faudrait donc net/chemin ≈ 0,97, alors que les cinq bras sondés éliminent 64 à 93 % de leur chemin. Au rapport de eplr (même voie, 0,201), tdoff tomberait vers 20 par agent (≈ 0,8 %) : parmi les PLUS PETITS, à côté de eplr (18,6). La paire E19 aurait alors deux amplitudes quasi égales, et l'ordre sur lequel 11c s'appuie serait mal anticipé.
- **Classe** : E8
- **Verdict** : confirmé — valeur supposée, non mesurée, et bornée loin sous ce qui est annoncé

### P1.3
- **Sonde** : python -c : median(S_const-S_a) et median(S_a)-median(S_const) sur results/s2_credit_ablation_2.json rows, et verdict['d_const_median'], verdict['d_eplr_median'] — sortie : -12.25 contre 12.75 ; d_eplr_median -19.0 -> 12.25/19.0 = 0.64 ; lignes 3 et 29 de la cible.
- **Constat** : Pour const, le 12,75 cité est une différence de médianes (36,0 - 23,25). La règle ERODE lit pourtant une médiane APPARIÉE par seed, qui vaut -12,25 dans le JSON. Et l'écart const/eplr, présenté comme un facteur deux, vaut 1,55 en statistique appariée (-12,25 contre -19,0). La non-monotonie invoquée tient toujours, puisque const bouge plus qu'eplr et érode moins. Aucune branche ne se renverse : le défaut est une statistique mal nommée dans la prose de la règle.
- **Classe** : E8
- **Verdict** : confirmé — hors verdict (prose et prédiction seulement)

### P1.4
- **Sonde** : python scratchpad/p1_opnorm.py (lecture des npz p418_W_*_2026, aucun monde) — sortie : op(dW)/op(sign) médianes 1.33 / 1.50 / 1.28 / 1.13 / 1.07 ; rapport L1 1.000000-1.000000 sur les cinq bras ; ligne 10 de la cible.
- **Constat** : En 11b, la règle dit que crédit et sham partagent toutes leurs normes. Pour L1, L2 et L∞, c'est vrai au bit, puisque les deux ont le même module entrée par entrée. Ce n'est pas vrai pour la norme opérateur, celle qui borne l'effet de ΔW sur l'activité qu'il transforme : sur les W persistés du seed 2026, crédit/sham vaut 1,33 (full), 1,50 (tdonly), 1,28 (const), 1,13 (eplr) et 1,07 (zero) en médiane sur 12 agents et 5 tirages. Une lecture DIRECTION confond donc en partie l'orientation avec un excès d'amplitude effective d'un tiers à la moitié. C'est plus étroit que la réserve sur la cohérence déjà déclarée, et la règle doit l'écrire.
- **Classe** : aucune
- **Verdict** : confirmé — l'identité des normes ne vaut que pour les normes coordonnée par coordonnée

### P1.5
- **Sonde** : python -c : verdict d_*_negative de results/s2_credit_ablation{,_2}.json ; numpy : colonnes non nulles de W_final-W0 et masse de dW[:, [77,78]] sur les npz full/eplr/const — sortie : d_const_negative 11/12, d_eplr_negative 11/12, d_zero_negative 8/12 (médiane -0.75) ; colonnes [64..71, 88, 89, 92] et [64..71] ; masse col 77-78 = 0.0.
- **Constat** : Les prémisses qui renverseraient réellement la lecture sont re-mesurées dans ce run ou vérifiées au bit. Harnais : S_a médiane 36, étendue 17-50. Classes de transplant : const et eplr sont EXACTEMENT à 11 seeds négatifs sur 12, sur la barre, mais les branches 4 et 5 imposent l'identité au bit avec le publié. zero est NEUTRE (8/12, -0,75). Le support du crédit est bien celui annoncé (colonnes 64-71, 88, 89, 92 ; seulement 64-71 pour eplr), et la masse est nulle sur les colonnes 77-78, ce qui confirme la réserve P8.a. Aucune de ces prémisses n'est héritée sans vérification.
- **Classe** : aucune
- **Verdict** : non confirmé — prémisses porteuses mesurées ; seuil 11/12 atteint au ras pour const et eplr

## P2 (DÉLÉGUÉ) — Régime : chaque paramètre cité est-il publié par l'evidence ?

- **Sonde** : cd .worktrees/science (HEAD 82927108) ; python tools/check_regime_claims.py --only <scratchpad>/S2-BASSIN-FRAGILITY.v3.json ; puis python -c qui appelle analyze() et liste les clés contenant FRAGILITY et les clés .json — sortie de la porte : records 304 | SANS_PARAMETRE 227, CONCORDE 6, CONCORDE_HORS_REGIME 7, SANS_RESULTS 52, SANS_REGIME 3, SANS_VALEUR_LUE 6, DISCORDE 3 ; OK : 64 legataires, EXIT=0. Sonde de périmètre : cible_fragility_dans_scan [] ; json_dans_scan 0 ; hors_EDR 0. Périmètre code : tools/check_regime_claims.py:347 (répertoire docs/EDR seul), :355 (suffixe .md seul), :432 (le filtre only ne retient que des chemins déjà scannés).
- **Constat** : Verdict de la porte recopié : OK, exit 0, aucun nouveau fautif ni aucune régression. Ce OK est VIDE pour cette cible : la porte 19 ne balaie que les Markdown du répertoire des records EDR, et la pré-inscription relue est un JSON du scratchpad ; le filtre --only ne retient donc aucun chemin évalué. Les valeurs de régime qu'elle cite (pas 0,04 et 0,004, 2000 ticks immortels, 200 ticks mortels, flux SeedSequence 418) ne sont confrontées à aucun results/ par ce passage. La porte n'est pas fausse : la cible sort de son périmètre, et le contrôle s'appliquera au futur record EDR qui citera le results/ du run. Aucune enquête rouverte (règle DÉLÉGUÉ).
- **Classe** : aucune
- **Verdict** : hors périmètre — porte OK recopiée, mais la cible (pré-inscription JSON hors docs/EDR) n'est pas évaluée par la porte 19 ; le OK ne certifie aucun paramètre de cette règle

## P3 (DÉLÉGUÉ) — Balayage du pas : garde E19 appelée par le runner scellé ?

- **Sonde** : cd .worktrees/science && python tools/check_e19_optimizer_sweep.py --only tools/evo_runs/s2_bassin_fragility.py; echo EXIT=$? (au sha 82927108) — EXIT=0 ; en-tête : runners scellés : 34 | sous gradient (PLANCHER) : 12 | nus : 9 | indéterminés : 4 | non résolus : 6 | règle absente : 1 | illisibles : 0 | appelants de la garde : 3 | gelés : 19 ; ligne [regle_absente] tools/evo_runs/s2_bassin_fragility.py ; appel réel de la garde en tools/evo_runs/s2_bassin_fragility.py:509 (import à :501), verify(PREREG) en :960.
- **Constat** : Verdict de la porte 23 recopié : OK, sortie 0. Le runner de P4.18 appelle lui-même assert_verdict_invariant_to_optimizer, il est donc compté parmi les 3 appelants réels de la garde. La porte le range pourtant en [regle_absente], signalé comme NOUVEAU et non bloquant : docs/preregistrations/S2-BASSIN-FRAGILITY.json n'existe pas encore dans l'arbre, puisque la cible relue est un brouillon v3 du scratchpad et n'est pas encore scellée. Tant que la règle JSON est absente, la porte ne peut pas juger si elle est sous gradient ; son OK repose sur l'appel direct. Il faudra relancer la même commande après le sceau, avant le premier run. Hors du champ de P3, et renvoyé à P5 : savoir si la paire de référence (b_tdoff à 0,04, b_eplr à 0,004) sort du même dispositif. Aucun défaut d'appel de la garde n'est constaté.
- **Classe** : E19
- **Verdict** : non confirmé

## P4 (JUGE) — Famille de contrôles

### P4.1 — taille réelle
- **Sonde** : python scratchpad/p4_famille.py (importe published, _classer, SIGN_MIN, FAMILLE du runner ; seeds 2026-2037) ; python tools/check_control_family.py --report — sortie : b_full ERODE 0 pos/12, méd −28,25 ; b_tdonly −27,75 ; b_const 11/12 nég, −12,25 ; b_eplr 11/12 nég, −19,0 ; b_tdoff −29,0 ; b_zero NEUTRE 8/12 nég, −0,75 → 3+6+5 = 14 = FAMILLE (tools/evo_runs/s2_bassin_fragility.py:82). _lecture_bras (l.487-493) ne consulte moins que si la greffe est ERODE, donc c_zero n'entre pas dans la lecture. Porte : 32 runners scellés, 0 sans design.
- **Constat** : Recompte fait en lisant fragility_verdict : trois tests de contrôle (pos contre S_a, eps contre S_a, eps contre la greffe de b_full), six classes du sham sign et un contraste c pour chaque bras dont la greffe érode. Les classes de greffe se calculent AVANT le run, depuis les JSON publiés et avec le classeur du runner : cinq bras érodent et b_zero reste neutre. Total 14, identique au nombre déclaré.
- **Classe** : aucune
- **Verdict** : non confirmé — famille déclarée = famille réelle (14)

### P4.2 — le seuil est-il hérité ?
- **Sonde** : `python -c "print(13/4096, 0.05/14, 0.05/15, 0.05/16)"` ; regex des seuils dans docs/preregistrations/S2-CREDIT-ABLATION-2.json — 0.003173828125 contre 0.00357 (14), 0.00333 (15), 0.003125 (16 : refus) ; la règle P4.16 contient '10/12' et '>= +5'.
- **Constat** : Le seuil de signe ne vient pas de P4.16, qui lisait à 10/12 : il est recalculé pour 14 cellules. La queue binomiale 13/4096 passe sous 0,05/14. La marge est mince : le seuil tient jusqu'à 15 cellules et tombe à 16. Seul le plancher d'effet de 5 ticks est repris de P4.16, où la valeur par seed était une médiane simple ; ici c'est une médiane de cinq tirages. Ce plancher n'est pas un niveau de test, il ne change donc pas la taille de la famille.
- **Classe** : aucune
- **Verdict** : non confirmé — seuil dérivé, pas hérité ; marge d'une seule cellule

### P4.3 — lien exécutable entre famille et seuil
- **Sonde** : grep -c alpha_cell tools/evo_runs/s2_bassin_fragility.py ; grep -n 'family = assert_control_family' tools/evo_runs/s2_bassin_fragility.py ; sed -n 403,405p tests/sandbox/test_s2_bassin_fragility.py — 0 occurrence de alpha_cell ; s2_bassin_fragility.py:841, family est seulement transmis à declare_design (l.849) ; :93 SIGN_MIN = 11 écrit en dur ; test_s2_bassin_fragility.py:403-405 compare sign_min à 11 et famille à 14, jamais l'un à l'autre.
- **Constat** : La taille de la famille et le seuil ne sont reliés que par un commentaire. Le runner appelle la garde de famille, qui rend un alpha par cellule, puis n'utilise pas ce retour : aucune assertion ne vérifie que la queue binomiale de SIGN_MIN sur n seeds reste sous 0,05/FAMILLE. Le test fige chaque constante sur un littéral séparé. Si deux contrastes lus s'ajoutaient (famille de 16), 11/12 passerait toutes les gardes alors qu'il n'est plus valide.
- **Classe** : E23
- **Verdict** : confirmé — mineur : valeurs cohérentes aujourd'hui (0,00317 <= 0,00357), invariant non gardé

### P4.4 — tests calculés hors famille
- **Sonde** : lecture de fragility_verdict ; grep -n de _classer et de _lecture_bras dans tools/evo_runs/s2_bassin_fragility.py ; `python -c "print(25*13/4096)"` — s2_bassin_fragility.py:576 (greffe), :580 (classe sham, boucle sur sign ET iso), :592 (lecture étiquetée pour chaque sham), :596 (iso rangé en secondaire avec l'étiquette), :602 (échelles x2/x4) ; 6 bras × 7 + 3 = 45 classements, dont 14 lus ; 25 × 0,003174 = 0,0793.
- **Constat** : En plus des 14 tests qui décident, le verdict passe 31 autres classements par le même classeur. Six sont des greffes déjà déterminées par le publié. Restent 25 tests neufs non corrigés : c_zero, classe et contraste iso sur les six bras, échelles x2 et x4. Les lectures iso sont publiées avec le vocabulaire du verdict (FRAGILE, DIRECTION…), si bien qu'un record pourrait en citer une comme résultat sans correction. Borne de fausse alarme de cet ensemble : environ 0,079.
- **Classe** : E23
- **Verdict** : confirmé — mineur : proposer une étiquette hors_famille sur les lectures iso et les échelles

## P5

### P5.1
- **Sonde** : python scratchpad/p5_sonde_9b.py (appelle le vrai fragility_verdict sur 4000 jeux synthétiques de 12 seeds par condition, aucun monde) ; grep -n assert_positive_control|assert_not_degenerate|assert_ablation_changes_something tools/evo_runs/s2_bassin_fragility.py — sortie : eps = S_a exact -> 2068 jeux franchissent la branche 8, 0 échec en 9b ; eps = S_a + N(0,6) -> 644 échecs 9b sur 2126. Code : tools/evo_runs/s2_bassin_fragility.py:648-663 (branche 8 puis 9b), :473-480 (_classer), :553-556 (_moins). grep : 0 appel de assert_positive_control ni de assert_ablation_changes_something, assert_not_degenerate seul à :619.
- **Constat** : La branche 9b doit servir de témoin positif pour l'issue DIRECTION. Or elle ne peut plus échouer une fois la branche 8 franchie, si eps se comporte en no-op, ce que la règle prédit. Avec S_eps = S_a, la différence S_eps − S_tr_full se réduit à S_a − S_tr_full. L'exigence « > 0 sur 11/12, médiane ≥ 5 » devient alors le miroir exact du critère d'érosion déjà testé en 8. 9b ne dit donc rien de la sensibilité du contraste sign − transplant, qui porte pourtant la lecture. Il ne tombe que si eps s'écarte du no-op par chaos, donc sur du bruit. Le trou signalé en P5.a par la première revue reste ouvert sous un autre nom.
- **Classe** : E1
- **Verdict** : confirmé

### P5.2
- **Sonde** : python -c qui lit results/s2_bassin_fragility_sonde_conception.json (sonde_net_chemin/cells) et imprime S_tr et S_a − S_tr par bras — sortie : noop 31,5 ; S_tr full 7,0 (écart 24,5), tdonly 9,0 (22,5), eplr 11,5 (20,0), const 21,0 (10,5), zero 32,0 (-0,5) ; eps tiré sur deltas[ref] avec ref = b_full, tools/evo_runs/s2_bassin_fragility.py:422.
- **Constat** : Le témoin de DIRECTION est ancré sur b_full, le bras dont la greffe coûte le plus de survie. Au mieux, il montre que le contraste apparié perçoit l'écart le plus large du dispositif, jamais les écarts étroits des autres bras lus. Sur le seed 2026 de la sonde de conception, b_full perd 24,5 ticks contre 10,5 pour b_const. Le témoin repose donc sur un écart 2,3 fois plus grand que celui du bras le plus serré, et aucun témoin n'existe à l'échelle de b_const ni de b_eplr.
- **Classe** : E19
- **Verdict** : confirmé

### P5.3
- **Sonde** : python -c sur results/s2_bassin_fragility_sonde_conception.json : 1 − DELTA_MIN/écart par bras ; grep -n ^DELTA_MIN tools/evo_runs/s2_bassin_fragility.py — sortie : fraction 0,796 (full), 0,778 (tdonly), 0,75 (eplr), 0,524 (const) ; DELTA_MIN = 5.0 à tools/evo_runs/s2_bassin_fragility.py:94 ; lecture par bras :483-493 ; 11c exige FRAGILE au plus grand net :681-683.
- **Constat** : Avec un seuil absolu de 5 ticks, l'issue FRAGILE n'est pas également accessible à tous les bras. En médianes, un bras ne sort FRAGILE que si le tirage de signes reproduit plus de 1 − 5/écart de la perte due à la greffe. Cela fait environ 80 % pour b_full, 78 % pour b_tdonly et 75 % pour b_eplr, mais 52 % pour b_const (61 % à l'écart médian de 12,75 que cite la règle). Les bras qui bougent le plus sont donc structurellement les plus durs à classer FRAGILE. Cela défavorise d'avance l'ordre que teste 11c (FRAGILE en haut de l'échelle d'amplitude) et pousse la lecture globale vers MIXTE. C'est une approximation en médianes sur un seul seed, à laquelle s'ajoute le critère de signe 11/12.
- **Classe** : E2
- **Verdict** : confirmé

### P5.4
- **Sonde** : grep -n ^ARMS|^E19_PAIRE|b_tdoff|b_eplr|b_zero tools/evo_runs/s2_bassin_fragility.py — tools/evo_runs/s2_bassin_fragility.py:69 dict(_BASE, td_enabled=False, lr=LR_LOW) contre :71 dict(_BASE, td_enabled=False) ; :70 b_zero = reward_scale 0.0 ; :80 E19_PAIRE.
- **Constat** : La paire de pas de la garde E19 sort bien du même dispositif. b_tdoff et b_eplr partagent la même base de crédit, TD coupé, et ne diffèrent que par le pas. Les deux sont rejoués dans ce harnais sous la même exigence de réplication au bit. Aucune référence à pas nul n'entre dans la lecture : b_zero annule la récompense, pas le pas. La question du pas nul est donc sans objet ici.
- **Classe** : aucune
- **Verdict** : non confirmé

## P6 (JUGE) — Plancher de bruit

### P6.1 — le plancher eps n'est jamais confronté à l'érosion des bras
- **Sonde** : python scratchpad/p6_v3_probe_a2.py (injection dans R.fragility_verdict via tests/sandbox/test_s2_bassin_fragility._rows, aucun monde : S_eps = S_a - 8 sur 10/12 seeds, S_tr = S_sign = S_a - 9 pour const et eplr) ; grep -nE 'eps.*classe.*ERODE|moins_erode_que_le_credit_complet|bandes = ' tools/evo_runs/s2_bassin_fragility.py — sortie : 'eps NEUTRE -8.0 10/12 | 9b moins: True' ; 'verdict LU FRAGILE' ; 'const FRAGILE sign vs S_a -9.0 12/12 | ecart au plancher eps -1.0' (idem eplr) ; 'eps cite dans why: False'. tools/evo_runs/s2_bassin_fragility.py:651 (eps lu seulement comme classe ERODE 11/12) et :657 (seulement contre S_tr_full) ; :686 le drapeau de bande ne porte que sur c, jamais sur les classes contre S_a.
- **Constat** : La perturbation à un millième mesure le bruit chaotique du bassin, mais le verdict ne s'en sert que comme porte binaire au seuil de famille. Si eps perd 8 ticks sur 10 seeds, il passe pour muet ; deux bras sortent alors FRAGILE à un seul tick au-delà de ce plancher, et la conclusion « visons l'amplitude » tombe puisqu'un tirage mille fois plus petit nuit presque autant. Aucun écart sham moins eps n'est calculé, publié ou signalé.
- **Classe** : E10
- **Verdict** : confirmé

### P6.2 — le seuil de saturation 0,9 déclaré n'est appliqué nulle part
- **Sonde** : grep -n 'SATURATION_HIGH\|saturation_high' tools/evo_runs/s2_bassin_fragility.py ; python scratchpad/p6_v3_probe.py (sonde B : _rows() par défaut, S_c 7,5, S_tr_full 8,0, S_a médiane 36) — 3 occurrences seulement : s2_bassin_fragility.py:97 (définition), :519 (signature), :551 (publication dans thresholds), 0 dans les branches 610-692. Sortie : 'B verdict LU FRAGILE | saturation full 0.982 | seuil publie 0.9' ; 0 occurrence de 'suffisance' dans la sortie JSON du verdict. Cible ligne 7 : la réserve de saturation est promise dans la branche 10.
- **Constat** : Quand la greffe ramène déjà la survie au niveau de la cohorte froide, le sham ne peut pas faire pire : l'égalité des deux bras vient du plancher, pas du mécanisme. La règle annonce une réserve dans ce cas ; l'exécutable publie le rapport et le seuil 0,9 mais n'en tire aucune conséquence, et la fixture même du test rend FRAGILE à 0,98 de saturation sans réserve.
- **Classe** : E10
- **Verdict** : confirmé

### P6.3 — échelle de la bande tirage0-tirage1 face au contraste médian inter-seeds
- **Sonde** : python scratchpad/p6_v3_probe.py (sonde C : Monte-Carlo 20 000 x 12 seeds x 6 tirages normaux ; c = médiane de 5 tirages - 1 tirage ; bande = médiane sur seeds de |tirage1 - tirage2|, comme s2_bassin_fragility.py:582-591) — P(|cmed| <= bande) = 0,9603 sous le nul ; sd(cmed) = 0,391 contre bande médiane 0,959 (2,45 sd) ; P(11/12 ET dans_la_bande) = 0,091 / 0,070 / 0,017 pour un effet de 1 / 1,5 / 2 sd (P(11/12) = 0,301 / 0,691 / 0,922).
- **Constat** : Hypothèse testée : bâtie sur l'écart entre deux tirages isolés, la bande serait à la mauvaise échelle pour une médiane sur douze seeds. Sous le nul où la greffe vaut un tirage de plus, elle couvre 96 % des contrastes médians : échelle juste. Le drapeau peut encore s'allumer quand le test de signe passe (10 à 30 % des cas à effet modéré), ce qui est attendu d'une bande à 4 % face à un test à 0,3 %.
- **Classe** : aucune
- **Verdict** : non confirmé

### P6.4 — le no-op publié est-il celui de CE contraste ?
- **Sonde** : grep -noiE 'no.?op[^,;.]{0,60}' S2-BASSIN-FRAGILITY.v3.json ; grep -nE 'truqu' tools/evo_runs/s2_bassin_fragility.py — 7 correspondances no-op dans la cible (lignes 13 x2, 23, 27, 28 x2, 30), toutes sur noop/a_frozen/S_a ; s2_bassin_fragility.py:725 flux truqué qui rend les signes de ΔW -> sham sign = ΔW au bit ; :389 noop = phase 2 sur apply_delta(W0, zero), exigé égal au bit à a_frozen (:446).
- **Constat** : Toutes les mentions du no-op dans la règle portent sur la référence gelée (reproductibilité de S_a), aucune sur le contraste c. Mais le zéro exact de c découle de deux faits mesurés : le flux truqué rend ΔW au bit, et la phase 2 est déterministe en W (branche 2 au bit). Le plancher de c à bruit nul est donc établi par construction, sans survie dédiée.
- **Classe** : aucune
- **Verdict** : non confirmé

## P7 (JUGE) — Dose

### P7.1 — covariable de létalité de phase 1 citée par la règle
- **Sonde** : python <scratchpad>/p7_dose2.py (lit learning.resurrections dans results/s2_credit_ablation_2.json et results/s2_credit_ablation.json) — medians {full 10, tdonly 8, const 65.5, eplr 16.5, zero 179, tdoff 3.5} ; max/min sur les six bras = 51.14, contre 22.4 sans tdoff ; la cible S2-BASSIN-FRAGILITY.v3.json:3 ne cite que cinq médianes et omet b_tdoff.
- **Constat** : Le facteur de létalité annoncé (≈18) a été calculé sur cinq bras, avant l'ajout du sixième. Or b_tdoff est le bras le MOINS létal (médiane 3,5 résurrections), donc l'écart réel sur les six bras scellés vaut ≈51 (179 / 3,5) et non ≈18. Le chiffre de la règle n'a pas été recalculé sur le dispositif qu'elle scelle.
- **Classe** : E8
- **Verdict** : confirmé

### P7.2 — paire de la garde E19 confondue par la létalité
- **Sonde** : python <scratchpad>/p7_dose2.py (résurrections par seed de b_tdoff et de b_eplr) ; grep -n clause_E19 dans la cible — b_tdoff par seed [25,26,2,4,2,3,12,5,3,5,3,3] contre b_eplr [29,30,17,6,24,5,16,12,10,15,20,37] : eplr > tdoff sur 12/12 ; cible S2-BASSIN-FRAGILITY.v3.json:4 (clause_E19 : les exclusions portent sur b_full, const, tdonly et zero, jamais sur la létalité).
- **Constat** : La paire censée isoler le pas (b_tdoff à 0,04 contre b_eplr à 0,004, même voie épisodique) diffère aussi par la létalité de phase 1, et toujours dans le même sens : b_eplr meurt plus que b_tdoff sur 12 seeds sur 12 (médianes 16,5 contre 3,5, soit ×4,7). Une fermeture de l'écart sham − crédit entre les deux pas peut donc venir de la létalité et pas du pas. La lecture DIRECTION_DEPEND_DU_PAS ne sépare pas ces deux causes, et la liste des limites de la garde dans clause_E19 ne parle pas de la létalité.
- **Classe** : E19
- **Verdict** : confirmé

### P7.3 — le compteur répliqué ne voit pas la dose reçue par agent
- **Sonde** : python <scratchpad>/p7_dose.py (min/max de td_updates par bras) ; Read tools/learning_events.py:164-178 — td_updates min = max = 1999 sur b_full, b_tdonly, b_const, b_zero (b_zero : résurrections 5 à 380) ; tools/learning_events.py:172 (ev.td_updates += 1 à chaque appel) et :174 (lr_effective_per_agent réécrit à chaque appel) ; tools/evo_runs/s2_bassin_fragility.py:457-459 (réplication comparée sur ce compteur).
- **Constat** : td_updates compte les appels au modèle de population (+1 par appel à learn qui rend une sortie), pas les mises à jour reçues par chaque agent. Il est donc constant quel que soit le nombre de morts : 1999 pour chaque seed des bras avec TD, que les résurrections valent 2 ou 380. La branche 4 vérifie au bit un compteur qui, par construction, ne peut pas refléter la létalité. Le nombre d'agents du lot à chaque appel n'est pas publié ; or le pas effectif vaut lr/B et seule la valeur du dernier appel est gardée.
- **Classe** : E3
- **Verdict** : confirmé

### P7.4 — pas effectif de la voie épisodique jamais publié
- **Sonde** : python <scratchpad>/p7_dose2.py (lr_effective_per_agent par seed) ; python -c qui teste la présence de la clé dans b_tdoff de results/s2_credit_ablation.json — b_eplr : None sur 12/12 seeds ; b_full : None sur 11/12 (lignes reprises de s2_credit_retention.json) ; b_tdoff : clé absente (False) ; tools/learning_events.py:180-188 (learn_episode n'écrit pas lr_effective_per_agent).
- **Constat** : Aucun JSON source ne publie le pas effectif des deux bras de la paire E19, qui n'ont que la voie épisodique. Le chemin learn_episode ne remplit jamais lr_effective_per_agent. Le rapport ×10 sur lequel raisonne la garde est donc le pas NOMINAL, pas un pas mesuré. Le run publiera le déplacement net par agent, pas le pas reçu.
- **Classe** : E8
- **Verdict** : confirmé

### P7.5 — gel de la phase 2 (nul d'apprentissage possible en phase mortelle ?)
- **Sonde** : grep -n 'dW_abs_sum\|count_learning_events' tools/evo_runs/s2_credit_retention.py — tools/evo_runs/s2_credit_retention.py:148 (count_learning_events(lr=0.0, td_enabled=False)) et :163 (assert dW_abs_sum == 0.0) ; :164 publie censored.
- **Constat** : Pas de défaut. La phase 2 tourne sous un compteur réglé à pas nul avec TD désactivé, puis vérifie que la somme des |ΔW| est exactement nulle : sinon elle lève. Aucune survie de phase 2 ne peut donc contenir d'apprentissage caché, et la cohorte de 12 clones y est comptée avec ses censurés.
- **Classe** : aucune
- **Verdict** : non confirmé

## P8

### P8.1
- **Sonde** : python <scratchpad>/p8_sonde.py (lit seulement le npz du bassin, ne construit aucun monde) ; grep -n 'batch_logits\[idx\] = consensus_logits' src/worlds/world_1_stoneage.py ; sed -n 155,170p src/agents/backend_torch.py — la sonde imprime 'W_bassin[src dW -> 77,78] non nuls 22 / 22 somme|.| 1.6561'. world_1_stoneage.py:963 lit logits[13] (et [14] à la ligne suivante), puis world_1_stoneage.py:973 écrase toute la ligne de l'agent. backend_torch.py:163 calcule excitation = H·W_off, donc W[i,j] va du nœud i vers le nœud j. backend_torch.py:200 fait de logits une vue de H_new[:, 64:172]. Tout cela contredit S2-BASSIN-FRAGILITY.v3.json:3, selon lequel ces nœuds sont atteints par iso et pos mais pas par sign, eps ni transplant.
- **Constat** : Le texte scellé présente le vote social comme un canal que seuls les deux gaussiens (iso, pos) peuvent toucher. La récurrence le dément : les 11 nœuds qui portent ΔW (64-71, 88, 89, 92) alimentent les nœuds 77-78 du vote au tick suivant par W_bassin, avec 22 poids non nuls sur 22. Le vote remplace en plus la ligne de logits TOUT ENTIÈRE, dont les logits 64-71 où agit le crédit. Ce canal d'état est donc commun à transplant, sign, eps, iso et pos : il ne distingue pas les bras, et la réserve « une érosion d'iso ou de pos peut passer par là » vaut aussi pour le contraste sign contre transplant qui porte la lecture.
- **Classe** : E8
- **Verdict** : confirmé

### P8.2
- **Sonde** : grep -n consensus tools/evo_runs/s2_bassin_fragility.py ; grep -o -i consensus <scratchpad>/S2-BASSIN-FRAGILITY.v3.json | wc -l ; grep -n '"mesure"' <scratchpad>/S2-BASSIN-FRAGILITY.v3.json | grep -ci consensus — le runner contient 8 occurrences de 'consensus' : s2_bassin_fragility.py:191-194 compte les réécritures (with compter_consensus, puis surv['consensus']), et s2_bassin_fragility.py:350 les écrit dans _cond_record. Dans la règle, le mot n'apparaît qu'une fois, à v3.json:3 (« sa fréquence n'est pas mesurée »), et 0 fois dans le champ 'mesure' (v3.json:27).
- **Constat** : La règle range la fréquence du vote parmi les dettes, comme une grandeur non mesurée. Or le runner la compte déjà pour chaque phase 2, en enveloppant la méthode de vote du monde, et l'écrit dans chaque enregistrement de condition. Ni le champ de mesure ni la règle de lecture ne nomment ce compteur. On aurait donc une grandeur publiée hors du sceau et une phrase scellée démentie dès le premier seed. Il faut trancher avant le sceau : soit déclarer le compteur (publié, hors verdict), soit retirer la mention de dette.
- **Classe** : aucune
- **Verdict** : confirmé

### P8.3
- **Sonde** : grep -n 'absorb_knowledge\|update_phenotype()\|mutate()' src/worlds/world_1_stoneage.py ; sed -n 1874,1885p src/worlds/world_1_stoneage.py ; grep -n update_phenotype tests/sandbox/test_s2_bassin_fragility*.py ; python <scratchpad>/p8_sonde.py — world_1_stoneage.py:1878-1879 : en benchmark_mode, social_new_agents et hgt_new_agents valent [] et _apply_surprise_hgt n'est pas appelé. world_1_stoneage.py:1657 pose la condition « not self.benchmark_mode ». Le monde de la phase 2 met benchmark_mode = True (s2_credit_retention.py:73). Le témoin est à test_s2_bassin_fragility:389 (a.update_phenotype() sur le W posé). La sonde imprime 'hp_bonus 688.8267' pour le bassin et 'pos: hp_bonus recalcule 1004.33'.
- **Constat** : Pour le corps (E26) : les gaussiens iso et pos, ainsi que le support du crédit, touchent les lignes 0:10 de W, d'où le monde dériverait le corps s'il le recalculait. Ce recalcul n'a pas lieu. Le corps est confronté à phenotype_of avant et après chaque phase 2, et un témoin gelé montre que la garde peut échouer. Aucun enfant ne naît en phase 2 : reproduction sociale, HGT et absorb_knowledge sont coupés en benchmark_mode. Recalculé, pos ferait passer hp_bonus de 689 à environ 1004 : c'est exactement l'écart que la garde attraperait. Aucun défaut trouvé.
- **Classe** : E26
- **Verdict** : non confirmé

### P8.4
- **Sonde** : python tools/check_io_overlap.py ; python <scratchpad>/p8_sonde.py ; sed -n 158,160p src/agents/backend_torch.py — la porte rend 'génomes persistés : 358 | chevauchants : 10 (connus 10, nouveaux 0, aggravés 0)'. La sonde imprime 'N 172 I 59 O 108 premier_logit_noeud 64 chevauchement 0' et 'part L1 colonnes d'entree 0.332'. backend_torch.py:159 fait H[:, :self.I] = obs_t avant l'excitation. s2_credit_retention.py:61 appelle assert_no_io_overlap.
- **Constat** : Pour le chevauchement entrée/sortie (E24) : le bassin a 59 entrées, et son premier logit est le nœud 64. Les deux blocs sont donc disjoints, et load_bassin lève une erreur en cas de chevauchement. Les colonnes 0:58, qui reçoivent le tiers de la masse d'un gaussien, sont bien écrasées par l'observation avant chaque pas : les tenir pour inertes est juste. Aucun défaut trouvé.
- **Classe** : E24
- **Verdict** : non confirmé

## P9 (DÉLÉGUÉ) — Sceau et provenance

### P9.1 — sceau
- **Sonde** : `python -c "from tools.preregister import verify; verify('S2-BASSIN-FRAGILITY')"` ; ls docs/preregistrations | grep -ic bassin ; `python -c "import json;from tools.preregister import _seal;print(_seal(json.load(open(CIBLE,encoding='utf-8'))))"` — verify lève FileNotFoundError (tools/preregister.py:196), exit=1 ; grep -ic bassin = 0 ; _seal(v3) = 9b5f045e...ba0c1.
- **Constat** : Aucune règle de ce nom n'est scellée dans le worktree science : la question du sceau intact n'a pas d'objet, la porte rend une absence. Le texte relu est une copie de scratchpad hors dépôt ; le seul lien entre ce texte et la future règle est l'empreinte calculée ici, _seal(v3) = 9b5f045e4d0eca5059ceb7944e3c32bbba710055743ae1c3793286e61e5ba0c1 (sha256 du fichier 46ab79c0...c872c40). Une règle scellée dont le champ seal diffère de cette valeur n'est pas couverte par cette revue et doit repasser.
- **Classe** : E11
- **Verdict** : confirmé

### P9.2 — provenance, verdict de la porte 20
- **Sonde** : python tools/check_evidence_provenance.py --only <cible v3> ; echo exit=$? — sortie 'OK : 18 chemin(s) legataire(s) gele(s). Aucun nouveau, aucune regression.' exit=0 ; tools/check_evidence_provenance.py:240-241 (seul docs/EDR/*.md) et :362 (if only is not None and f not in only: continue).
- **Constat** : Le vert rendu par la porte ne porte pas sur la cible : l'analyse ne parcourt que les .md de docs/EDR, et le filtre --only saute tout record absent de la liste ; un chemin de scratchpad ne désigne aucun record, donc zéro évaluation et sortie OK. La porte 23 refuse un --only qui filtre tout ; la porte 20 l'accepte en silence. Le verdict délégué à recopier est donc VIDE, pas positif.
- **Classe** : E4
- **Verdict** : confirmé

### P9.3 — provenance, logique de la porte appliquée au texte
- **Sonde** : python - : evaluer(texte_v3, exists, _tracked, root) ; grep -o 'results/[A-Za-z0-9_./-]*' <cible> | sort | uniq -c — evaluer -> statut OK, cites=[] ; grep : 2 x results/s2_bassin_fragility_sonde_conception.json, 1 x results/s2_bassin_fragility_genomes/ ; regex tools/check_regime_claims.py:95 exige une backtick juste après .json.
- **Constat** : En donnant directement le texte v3 à evaluer(), la porte trouve zéro citation alors que le fichier en porte trois (deux vers le JSON de sonde de conception, une vers le répertoire des génomes) : l'extracteur ne reconnaît qu'un chemin entouré de backticks, forme que ce JSON n'emploie pas. Absence de détection convertie en statut OK : même sur la bonne entrée, la porte ne sait pas juger une pré-inscription.
- **Classe** : E4
- **Verdict** : confirmé

### P9.4 — provenance, artefact de pré-scellement
- **Sonde** : git ls-files --stage results/s2_bassin_fragility_sonde_conception.json ; git cat-file -e HEAD:results/s2_bassin_fragility_sonde_conception.json ; echo $? — index : 100644 bf903dea3ac02ac4191561fe9a5831c4cc470f66 0 ; HEAD : 'fatal: path ... exists on disk, but not in HEAD', exit=128.
- **Constat** : Le JSON des mesures faites avant le sceau est dans l'index (suivi au sens de la porte) mais absent du dernier commit 82927108 : un clone de HEAD ne peut pas rouvrir les chiffres (no-op au bit, net/chemin, colonnes de dW) sur lesquels la règle s'appuie. Il doit partir dans le MÊME commit que la règle scellée, sinon la citation précède son artefact.
- **Classe** : E27
- **Verdict** : confirmé

### P9.5 — provenance, génomes persistés
- **Sonde** : git check-ignore -v results/s2_bassin_fragility_genomes/x.npz ; echo $? ; grep -n genomes tools/evo_runs/s2_bassin_fragility.py ; grep -ciE 'ignor|\bgit\b' <cible> — .gitignore:18:results/* ... exit=0 ; tools/evo_runs/s2_bassin_fragility.py:98 (commentaire 'ignore par git ; sha256 publie dans le JSON') ; 0 mention d'exclusion git dans la cible.
- **Constat** : Les matrices W rejouées, seules capables de refaire greffes et shams, tombent sous la règle d'exclusion globale de results/ : elles ne seront jamais suivies, leur provenance sera un hash déclaratif (cause par_hash, rang le plus faible de la porte 20, jamais confronté au fichier). La règle ne dit ni qu'elles sont hors git ni où elles résident si le lieu retenu est nexus ; seul un commentaire du runner le dit.
- **Classe** : E27
- **Verdict** : confirmé

## P10 (JUGE) — Mécanisme

### P10.1 — canal du vote social
- **Sonde** : `python -c "import numpy as np;z=np.load('results/warm003_dagger_genome.npz');W=z['W'].astype(float);S=[*range(64,72),88,89,92];print(int(z['num_inputs']),W.shape[0]-int(z['num_outputs']),int((W[S,77]!=0).sum()),int((W[S,78]!=0).sum()),round(abs(W[S,77]).sum(),3),round(abs(W[S,78]).sum(),3))"` -> 59 64 11 11 0.727 0.929 ; sed -n 947,976p src/worlds/world_1_stoneage.py ; sed -n 155,200p src/agents/backend_torch.py — backend_torch.py:195 (H_in = état complet du tick précédent) et :163 (excitation = H·W_off : le nœud 77 somme H[i]·W[i,77] sur tous les i) ; world_1_stoneage.py:963-964 lit logits[13] et [14], :973 réécrit la ligne ; bassin : W[S,77] et W[S,78] ont 11 entrées non nulles sur 11 (L1 0,727 et 0,929, soit environ 9-10 % de la L1 non-entrée de ces colonnes, 8,171 et 9,459).
- **Constat** : La réserve sur le consensus affirme que seuls iso et pos peuvent toucher les logits 13-14, sous prétexte que leurs colonnes ne portent pas ΔW. C'est un raisonnement sur le support direct qui oublie la récurrence. Les nœuds 64-71, 88, 89 et 92, déplacés au tick t, alimentent les nœuds 77-78 au tick t+1 par des poids du bassin non nuls. Transplant, sign et eps atteignent donc ce canal d'état autant que les shams gaussiens. L'asymétrie annoncée n'existe pas, et le contraste primaire sign − transplant n'est pas à l'abri de ce canal.
- **Classe** : E8
- **Verdict** : confirmé

### P10.2 — étiquette des colonnes TD
- **Sonde** : sed -n 32,36p src/agents/backend_torch.py ; sed -n 233,257p src/agents/backend_torch.py ; même python -c que ci-dessus (N−O = 64) — backend_torch.py:33-35 : _GRAB_NODE = 24, _RUB_NODE = 25, _VALUE_NODE = 28 ; :256-257 : grab et rub entrent dans logp (perte de l'acteur) ; N−O = 64 mesuré, d'où 64+24 = 88 (grab), 64+25 = 89 (rub), 64+28 = 92 (valeur).
- **Constat** : La règle range 88 et 89 dans la tête de valeur. Dans le code, seul le nœud 92 (sortie 28) est le critique. 88 et 89 sont les logits binaires grab et rub (sorties 24 et 25) de l'acteur. Le compte de onze colonnes est juste, mais la répartition réelle est de dix colonnes d'acteur (8 de déplacement, grab, rub) pour une seule de valeur. Le motif invoqué pour placer ΔW (colonnes lues par la perte) tient toujours ; c'est la description du mécanisme qui est fausse.
- **Classe** : aucune
- **Verdict** : confirmé

### P10.3 — référent de l'unité de coût publiée
- **Sonde** : grep -n "unit_basis\|cells_first = \|^ARMS" tools/evo_runs/s2_bassin_fragility.py ; grep -n "66 phases\|55 cellules\|5 cellules" tools/evo_runs/s2_bassin_fragility.py — s2_bassin_fragility.py:899 (chaîne publiée « 5 cellules ») contre :893 (somme sur ARMS) et :63 (6 bras) ; :794 « 66 phases 2 … cinq cellules », :877-878 « 5 cellules … 55 cellules » ; compte réel 1 + 6×(1 + 5×4) + 5 + 5 = 137 phases 2 ; 11 seeds × 6 = 66 cellules restantes.
- **Constat** : Le JSON agrégé va décrire l'unité projetée comme cinq cellules plus les phases 2, alors que la somme calculée porte sur les six bras. Les docstrings des tâches ouvrières annoncent encore 66 phases 2 par seed et 55 cellules restantes. La règle et la boucle donnent 137 et 66. Le libellé publié de l'unité qui arme la garde E13 est donc faux dès le premier seed, alors que le calcul est juste.
- **Classe** : E8
- **Verdict** : confirmé

### P10.4 — compteur de consensus absent de la règle
- **Sonde** : grep -n "consensus" tools/evo_runs/s2_bassin_fragility.py -> 8 lignes ; sed -n 178,225p tools/evo_runs/s2_bassin_fragility.py — s2_bassin_fragility.py:191-194 (compter_consensus autour de phase2_survive_mortal, surv["consensus"] publié) et :198-225 (compteur de lignes réécrites) ; la règle, champ ce_que_ce_run_ne_tranche_pas, déclare cette fréquence non mesurée ; aucune branche 1-11 ne lit consensus.
- **Constat** : La règle scellée présente la fréquence du vote social comme une dette non mesurée. Le runner la compte pourtant à chaque phase 2 sur clones et la publie par condition, sans qu'aucune clause scellée dise comment la lire. Une grandeur publiée sans lecture déclarée ne peut être interprétée qu'après coup. La réserve de la règle invite justement à imputer au consensus une érosion d'iso ou de pos, imputation que la critique précédente montre injustifiée.
- **Classe** : E11
- **Verdict** : confirmé

### P10.5 — relève de P7 : covariable de létalité
- **Sonde** : python -c sur results/s2_credit_ablation_2.json et results/s2_credit_ablation.json : médiane par bras de arms[b][seed].learning.resurrections, seeds 2026-2037 — tdonly 8,0 ; full 10,0 ; eplr 16,5 ; const 65,5 ; zero 179,0 ; tdoff 3,5 ; 179/8 = 22,4 ; 179/3,5 = 51,1.
- **Constat** : L'écart de résurrections entre bras est sous-évalué. Avec les cinq médianes citées, le rapport max/min vaut 22 et non 18. Le sixième bras b_tdoff, absent de la liste, a une médiane de 3,5, ce qui porte le rapport à 51. La covariable confondue avec l'amplitude est donc plus étalée qu'écrit.
- **Classe** : aucune
- **Verdict** : hors périmètre

### P10.6 — relève de P1 : faiblesse L2 du sham iso
- **Sonde** : lecture de results/s2_bassin_fragility_sonde_conception.json, sonde_net_chemin.cells.*.structure.l1_over_l2_median ; 172·sqrt(2/pi) = 137,2 — l1_over_l2_median : full 24,44 ; eplr 18,27 ; zero 14,70 -> 137,2/24,44 = 5,6 ; /18,27 = 7,5 ; /14,70 = 9,3.
- **Constat** : Le rapport « iso plus faible en L2 » n'est pas de 5 à 6 sur tous les bras. Il vaut 5,6 sur b_full mais 7,5 sur b_eplr et 9,3 sur b_zero, avec les L1/L2 de la sonde et 137,2 pour un gaussien 172×172. Le biais annoncé va dans le sens écrit, mais il est plus fort qu'écrit.
- **Classe** : aucune
- **Verdict** : hors périmètre

### P10.7 — affirmations sur le code vérifiées et trouvées exactes
- **Sonde** : sed -n 164,192p tools/learning_events.py ; sed -n 84,141p src/agents/backend_torch.py ; sed -n 383,401p tools/experiment_preflight.py ; sed -n 74,90p tools/experiment_preflight.py ; sed -n 78,95p tools/jobs/run.py — learning_events.py:173,187 (+= |ΔW| à chaque mise à jour), :190-192 et :242-243 (lr injecté à __init__) ; backend_torch.py:141, :267, :505 (même self.opt) ; experiment_preflight.py:303 (2/3), :388-394 (gap = référence − testé), :400-401 ; :86 (spread <= min_spread) ; lease.py:169 et run.py:91 (pid du bail = appelant de Popen).
- **Constat** : Plusieurs affirmations sur le code tiennent à la lecture. Le pas injecté est celui du SGD partagé par learn et learn_episode : b_eplr et b_tdoff ne diffèrent donc que par le pas. La garde E19 reçoit bien le couple (testé, référence) = (S_tr, S_sign), son défaut est 2/3 et elle se tait si l'écart est négatif ou nul. La dégénérescence est jugée à étendue inférieure ou égale au seuil. Le chemin dW est bien cumulatif. Les colonnes d'entrée pèsent 59/172 = 34,3 %. Le bail du parent correspond au pid de l'appelant de run().
- **Classe** : aucune
- **Verdict** : non confirmé

---

## Addendum de l'auteur (session SCIENCE-HARNAIS, 2026-09-26) — suites données, v3 → v4

Cette revue porte sur la v3 (sceau de brouillon `9b5f045e…`). La version soumise au sceau est la **v4**, qui traite
chaque critique confirmée ci-dessous ; elle est relue à son tour (`docs/reviews/2026-09-26-S2-BASSIN-FRAGILITY.v4.md`)
avant tout sceau (P9.1). Exécution : script du dépôt tel que committé (blob `d327d685…`, extrait en LF — l'extraction
Windows en CRLF était encore refusée par l'outil Workflow ; corrigé dans d1 par `82927108`).

**Suites données aux critiques confirmées.**
- **P1.1, P7.2, P7.4 (E19/E8)** — la paire b_tdoff / b_eplr ne varie le chemin que ×1,36 (pas ×10), le pas est NOMINAL et
  b_eplr meurt ×4,7 plus en phase 1 sur 12/12 seeds : l'étiquette devient `DIRECTION_DEPEND_DU_REGLAGE` (pas OU létalité,
  non séparés), `clause_E19` le dit, et le verdict publie à côté de la garde les rapports de chemin et de net et les
  résurrections de la paire. La garde reste appelée (porte 23), sa portée est bornée par écrit.
- **P1.2 (E8)** — b_tdoff n'est plus rangé parmi les grands déplacements : net non mesuré, borné par son chemin (101 par
  agent), vraisemblablement petit (≈20).
- **P1.3 (E8)** — l'écart b_const est écrit en médiane APPARIÉE (−12,25), le facteur const/eplr 1,55 (et non 2).
- **P1.4** — les normes identiques sont les normes coordonnée par coordonnée ; la norme d'OPÉRATEUR du crédit dépasse
  celle du sham de ×1,07 à ×1,50 au pré-scellement : écrit, et le rapport est publié par tirage (`matching`).
- **P4.3 (E23)** — le lien famille-seuil est ASSERTÉ (`seuil_tient` : 11/12 tient à 14 et 15, tombe à 16, témoin gelé).
- **P4.4 (E23)** — lectures iso renommées `lecture_hors_famille` et marquées `hors_famille`, échelle sign de même.
- **P5.1 (E1)** — la limite de 9b est écrite (miroir de 8 sur un seed où S_eps = S_a au bit) et le compte de ces seeds est
  publié ; aucun contrôle positif plus fort de DIRECTION n'a été trouvé qui tienne sous la famille (un eps par bras
  porterait la famille à 18-22 contrastes et ferait tomber 11/12) — dit, pas masqué.
- **P5.2 (E19)** — 9b n'éprouve le contraste qu'à l'écart de b_full : écrit dans la branche.
- **P5.3 (E2)** — l'asymétrie du seuil absolu est écrite (fraction de perte requise ≈80 % pour b_full contre ≈60 % pour
  b_const) et publiée par bras ; elle pousse la lecture vers MIXTE, ce que la règle dit.
- **P6.1 (E10)** — qualificatif `au_dela_du_plancher_eps` (médiane S_sign − S_eps <= −5) publié et dit dans le verdict.
- **P6.2 (E10)** — qualificatif `suffisance_seulement` (FRAGILE à saturation >= 0,9) appliqué, publié et dit.
- **P7.1 (E8)** — facteur de létalité recalculé sur les SIX bras : ≈51 (tdoff 3,5 … zero 179).
- **P7.3 (E3)** — écrit : `td_updates` compte les appels de la population, pas les mises à jour par agent.
- **P8.1, P10.1 (E8)** — ma phrase « canal de consensus atteint seulement par iso/pos » était FAUSSE : par la récurrence
  (22 poids du bassin non nuls sur 22 des colonnes de ΔW vers les nœuds 77-78), il est commun à toutes les conditions ;
  réécrit.
- **P8.2, P10.4 (E11)** — le compteur de consensus est DÉCLARÉ dans `mesure` (publié par condition, hors verdict).
- **P9.1 (E11)** — revue rejouée sur la v4 avant sceau.
- **P9.2, P9.3 (E4)** — portes 19/20 : `--only` hors périmètre → P2.128 (agagi-32) ; extracteur à backtick → P2.129.
- **P9.4, P9.5 (E27)** — sonde de conception dans le MÊME commit que la règle ; génomes hors git déclarés dans `mesure`.
- **P10.2** — 88 et 89 sont les logits grab et rub de l'ACTEUR ; seul 92 est la tête de valeur : corrigé.
- **P10.3 (E8)** — libellés de l'unité et des tâches corrigés (6 cellules, 137 phases 2, 66 cellules restantes).

Non confirmées ou hors périmètre : sans suite (P1.5, P2, P3, P4.1, P4.2, P5.4, P6.3, P6.4, P7.5, P8.3, P8.4, P10.5,
P10.6, P10.7).
