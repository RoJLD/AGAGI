# Revue adversariale — S2-BASSIN-FRAGILITY (v6)

- **Cible** : `C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/S2-BASSIN-FRAGILITY.v6.json` (pré-inscription, brouillon non scellé)
- **Date** : 2026-09-26
- **SHA** : `82927108f6244537bee0a35d44fa06dcf36cea03` (worktree `.worktrees/science`, branche tmp/science)

## Résultat des TÉMOINS

Planchers, sur les mêmes lignes que le score :
- PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5
- plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1)

| témoin | statut | code | recevables | planchers |
|---|---|---|---|---|
| S2-BLIND-CHAMPION-42e9357 | RETROUVE | 0 | 7 | fausses retrouvailles 0/5 ; LOCK-002 : 6 recevables (seuil historique 1) |
| EDR-GRAB-COST-1828371 | RETROUVE | 0 | 7 | fausses retrouvailles 0/5 ; LOCK-002 : 6 recevables (seuil historique 1) |
| EDR-RETAIN-COMPOSE-4204f8f | RETROUVE | 0 | 9 | fausses retrouvailles 0/5 ; LOCK-002 : 6 recevables (seuil historique 1) |
| LOCK-002-286f244 (cru sain) | MESURE | 0 | 6 | fausses retrouvailles 0/5 ; LOCK-002 : 6 recevables (seuil historique 1) |

Commandes de vérification (fichiers de critiques dans `<scratchpad>/refutateur_v6b/`) :

    PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/science/tools/refutateur_temoins.py --verifier S2-BLIND-CHAMPION-42e9357 C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/refutateur_v6b/critiques-S2-BLIND-CHAMPION-42e9357.json --extrait C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/temoins/temoin-1.md --jugement OUI
    PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/science/tools/refutateur_temoins.py --verifier EDR-GRAB-COST-1828371 C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/refutateur_v6b/critiques-EDR-GRAB-COST-1828371.json --extrait C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/temoins/temoin-3.md --jugement OUI
    PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/science/tools/refutateur_temoins.py --verifier EDR-RETAIN-COMPOSE-4204f8f C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/refutateur_v6b/critiques-EDR-RETAIN-COMPOSE-4204f8f.json --extrait C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/temoins/temoin-4.md --jugement OUI
    PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/science/tools/refutateur_temoins.py --verifier LOCK-002-286f244 C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/refutateur_v6b/critiques-LOCK-002-286f244.json --extrait C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/temoins/temoin-2.md

Bilan : 30 critiques, **13 confirmées**.

---

## P1 (JUGE) — prémisse porteuse

### P1.a — motif de l'illisibilité E19
- **Sonde** : `python -c "import json;d=json.load(open('results/s2_credit_ablation_2.json',encoding='utf-8'));[print(a,d['regime']['arms_credit'][a]['episode_enabled'],d['arms'][a]['2026']['learning']['episode_updates'],d['verdict']['arm_'+a[2:]]) for a in ('b_tdonly','b_const')]"` ; `python <scratchpad>/p1_sonde.py` (saturation |S_tr-S_a|/(S_a-S_c) par seed, S_c de s2_credit_retention.json)
- **Preuve** : S2-BASSIN-FRAGILITY.v6.json:4 (clause_E19, liste des bras au plancher « full 8,0, tdonly 8,5, tdoff 7,5 »), à comparer à la sortie de la sonde : « b_tdonly False 0 ERODE » / « b_const True 250 ERODE ». p1_sonde.py : const S_tr méd 23.25, saturation par seed méd 0.568 (min 0.071), alors que tdoff est à 1.017 (min 0.946).
- **Constat** : La clause E19 annonce la garde illisible d'avance, et elle le justifie par un fait faux. Pour dire qu'aucune paire de pas n'est lisible, elle compte b_tdonly parmi les bras qui ont le crédit épisodique au pas publié, et elle ne cite pas b_const. Or le JSON publié montre que b_tdonly a l'épisodique désactivé (zéro mise à jour épisodique). b_const, lui, l'a : 250 mises à jour à 0,04, et son transplant est ERODE. Il reste loin du plancher : saturation médiane par seed 0,568, S_tr médiane 23,25. Le seul bras saturé est celui qu'on a choisi pour la paire (b_tdoff). L'illisibilité vient donc d'un choix de conception, pas d'une contrainte du dispositif. Une paire lisible était possible : b_const rejoué à 0,004. Il aurait fallu une phase 1 neuve, sans référence publiée à répliquer au bit. La conclusion reste vraie, puisqu'aucun bras de même voie à un autre pas n'existe dans les données publiées. Mais le motif écrit est faux. On scelle une garde incapable de lever en la présentant comme imposée par le dispositif.
- **Classe** : E8
- **Verdict** : confirmé

### P1.b — chiffres hérités de 10bis
- **Sonde** : `python <scratchpad>/p1_sonde.py`
- **Preuve** : sortie : tdoff sat méd 1.017 min 0.946 ; S_c méd 7.5 ; const 2036 +10.5, eplr 2036 0.0 ; const 2035 42.0/39.5 ; chemin tdoff/eplr méd 1.363 (0.828-2.838, argmin 2027) ; eplr>tdoff résurrections 12/12 ; spearman tdonly 0.750 ; S_tr<S_c 7/3/1 ; zero d -8.5..2.0
- **Constat** : J'ai recalculé depuis les JSON P4.4/P4.9/P4.16 les chiffres dont dépendent la lecture et la certitude d'illisibilité de 10bis. Tous sont retrouvés à l'identique : saturation de b_tdoff, S_c, marges MOINS de const et eplr, marge de 2035, rapport de chemin de la paire, létalité de la paire, Spearman de b_tdonly, greffes passées sous S_c. Aucune prémisse chiffrée héritée n'est contredite.
- **Classe** : aucune
- **Verdict** : non confirmé

### P1.c — tolérance L1 de eps après arrondi float32
- **Sonde** : `python <scratchpad>/p1_eps.py` (somme des ulp/2 de W_bassin sur les colonnes 64-71, 88, 89, 92)
- **Preuve** : borne pire cas 9.463e-06 contre une cible L1 eps de 0.1005 : rapport 9.4e-05, pour une tolérance de 0.01 ; modèle lognormal : écart max 1.0e-05
- **Constat** : La branche 6 rendrait tout le run INDETERMINE si un seul tirage eps s'écartait de plus de 1 % en L1 effective après arrondi float32. Or preflight_shams ne teste pas cette échelle. J'ai borné le pire cas sur les colonnes du support dans W_bassin : l'écart maximal reste environ 100 fois sous la tolérance. La prémisse tient.
- **Classe** : aucune
- **Verdict** : non confirmé

### P1.d — norme d'opérateur à ×2
- **Sonde** : `python <scratchpad>/p1_opnorm.py` ; np.nonzero de la masse par colonne de ΔW sur les npz p418_W_*_2026
- **Preuve** : op(dW)/op(sign) max par agent : 1.51 full, 1.69 tdonly, 1.55 const, 1.31 eplr, 1.26 zero, tous < 2 ; colonnes non nulles [64..71,88,89,92], eplr [64..71] ; L1 W_bassin 2442.8
- **Constat** : Le qualificatif de DIRECTION suppose qu'à ×2 la norme d'opérateur du tirage dépasse celle du crédit. Sur les W de la sonde (seed 2026), c'est vrai pour chaque agent de chaque bras. Le support est bien de 11 colonnes, et de 8 pour eplr. La L1 du bassin donne un contrôle pos à 24,3× et 716× le déplacement des bras (le texte dit 718, écart d'arrondi).
- **Classe** : aucune
- **Verdict** : non confirmé

## P2 (DÉLÉGUÉ) — Régime : porte 19 lancée sur la cible v6

- **Sonde** : `cd .worktrees/science && python tools/check_regime_claims.py --only <scratchpad>/S2-BASSIN-FRAGILITY.v6.json ; echo EXIT=$? ; python -c "from tools.check_regime_claims import analyze; a=analyze('.'); print(len(a['records']), [f for f in a['records'] if 'S2-BASSIN-FRAGILITY' in f], sorted({'/'.join(f.split('/')[:2]) for f in a['records']}))" ; git merge-base --is-ancestor 3c9414f6 HEAD; echo $?`
- **Preuve** : Sortie de la porte : 'OK : 64 record(s) sans regime concordant [...]', EXIT=0 ; analyze : records_scannes 304, records_contenant_cible [], prefixes ['docs/EDR'] ; tools/check_regime_claims.py:67 et :125 (périmètre docs/EDR/*.md seul), :425 et :432 (le --only filtre les fautifs sans refuser un argument hors périmètre) ; merge-base --is-ancestor 3c9414f6 HEAD -> 1 (non ancêtre ; 3c9414f6 est sur feat/d1-prod-pairing, tmp/p2-105, tmp/nexus, tmp/fusion-nexus).
- **Constat** : Verdict recopié de la porte 19 : OK, sortie 0. Mais ce OK ne dit rien de la pré-inscription. La porte ne parcourt que les Markdown du dossier docs/EDR (304 records scannés, aucun ne correspond à la cible). Sa copie dans ce worktree écarte en silence un --only qui ne vise aucun record, au lieu de le refuser. Résultat : aucun paramètre chiffré de la règle (pas 0,04 et 0,004, 2000 ticks immortels, 200 ticks mortels, 5 tirages) n'a été confronté à un results/ par cette porte. Le correctif qui fait refuser ce cas existe (3c9414f6, P2.128) mais il n'est pas un ancêtre du HEAD 82927108 où la porte a été lancée. Comme le veut la règle de partage, c'est une dette de porte, déjà ouverte (P2.128) : je ne rouvre pas le balayage ici.
- **Classe** : E4
- **Verdict** : hors périmètre — la porte 19 ne lit pas une pré-inscription JSON : son OK est vide pour cette cible, pas une concordance. Dette de porte déjà ouverte : P2.128.

## P3 (DÉLÉGUÉ) — balayage du pas, garde E19 appelée par le runner scellé

- **Sonde** : `cd C:/Users/robla/VScode_Project/AGAGI/.worktrees/science && python tools/check_e19_optimizer_sweep.py --only tools/evo_runs/s2_bassin_fragility.py; echo EXIT=$?` (HEAD 82927108)
- **Preuve** : Sortie de la porte : 'runners scelles : 34 | sous gradient (PLANCHER) : 12 | nus (PLANCHER) : 9 | ... | regle absente : 1 | appelants de la garde : 3 | geles : 19' puis '[regle_absente] tools/evo_runs/s2_bassin_fragility.py : appelle assert_verdict_invariant_to_optimizer(...) directement' puis 'OK : aucun nouveau runner sous gradient sans garde E19', EXIT=0. Appel réel dans tools/evo_runs/s2_bassin_fragility.py:591 (import à :572, PREREG à :65).
- **Constat** : Porte 23 lancée sur le runner de la cible : verdict OK, sortie 0, rien de bloquant. Le runner est reconnu comme appelant direct de la garde E19 (3 appelants au total). Il est rangé en regle_absente, NOUVEAU non bloquant : la pré-inscription S2-BASSIN-FRAGILITY n'est pas encore scellée sous docs/preregistrations (la v6 relue vit dans le scratchpad). C'est l'état attendu avant sceau, pas un défaut de la cible. La question de savoir si la référence à pas nul vient du même dispositif relève de P5 et n'est pas rouverte ici.
- **Classe** : E19
- **Verdict** : non confirmé

## P4 — famille de contrôles et seuils

### P4.a — contraste sign x2 moins greffe hors famille
- **Sonde** : `python tools/check_control_family.py --report` (point de départ : 32 scellés, 0 sans design, runner non encore scellé) ; `grep -n nettement tools/evo_runs/s2_bassin_fragility.py` ; `sed -n 728,738p tools/evo_runs/s2_bassin_fragility.py` ; `python -c "from tools.evo_runs.s2_bassin_fragility import seuil_tient; print(seuil_tient(11,12,16)); print(0.05/19, 13/4096)"`
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:733-735 : echelle_sign ne publie que contraste_vs_transplant_mediane (hors_famille True), aucun appel à _moins (défini :653-656, seul critère MOINS) ; 'nettement' dans le runner : lignes 15, 551, 621, 827, toutes pour eps/sign, aucune pour sign_x2 ; 0.05/19 = 0.00263 < 13/4096 = 0.00317, et seuil_tient(11,12,16) = (False, 0.00317, 0.003125)
- **Constat** : La règle tire deux conclusions d'un contraste qu'elle déclare hors famille : quel remède sceller ensuite (ancre ou clip spectral) et si la surnorme spectrale du crédit rend compte d'une lecture DIRECTION. Ce contraste (tirage x2 moins greffe) n'a aucun critère exécutable : le runner n'en publie qu'une médiane, sans compte de signes ni test MOINS, et le mot qui le qualifie n'est défini nulle part pour lui. La famille des contrastes qui PORTENT une conclusion vaut donc 14 + 5 bras érodés = 19 ; à 19, la queue de 11/12 dépasse alpha par cellule et seuil_tient lèverait. Il faut soit l'intégrer (et relever sign_min), soit retirer la conclusion sur le remède.
- **Classe** : E23
- **Verdict** : confirmé

### P4.b — seuil de saturation 0,9 sans provenance
- **Sonde** : `grep -rn "SATURATION_HIGH\s*=" tools/ docs/preregistrations/` ; python -c (json.load de la v6 : 'saturation' in seuils_note, count('HÉRITÉ')) ; `grep -n "def cold_floor" -A12 tools/evo_runs/s2_bassin_fragility.py`
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:101 SATURATION_HIGH = 0.9, unique occurrence sous tools/ ; seuils_note : 'saturation' absent (False), 'HÉRITÉ' = 2 occurrences (delta_min, harness_min) ; :293-298 cold_floor lit S_c dans results/s2_credit_retention.json (P4.4) et la docstring le dit NON plancher (b_tdoff sous S_c 7/12)
- **Constat** : Le seuil de saturation 0,9, qui décide la lisibilité de la garde E19 et le qualificatif de suffisance, est le seul seuil numérique du bloc sans origine dite : la note des seuils justifie l'héritage de delta_min et de harness_min et reste muette sur lui, et il n'existe dans tools/ que dans ce runner. Il s'applique à un indice normalisé par S_c, emprunté à la cohorte froide de P4.4, que le runner lui-même dit ne pas être un plancher de ce dispositif. Un seuil sans provenance sur un dénominateur importé : sa valeur n'est ni dérivée ni déclarée héritée.
- **Classe** : E8
- **Verdict** : confirmé

### P4.c — recompte des tests de signe
- **Sonde** : python -c : _classer(S_<bras> - S_a, 11, 5.0) sur results/s2_credit_ablation_2.json et results/s2_credit_ablation.json (rows), puis seuil_tient(11,12,f) pour f = 14, 15, 16
- **Preuve** : zero NEUTRE (2 pos, 8 neg, médiane -0,75) ; full 12/12 -28,25, tdonly 12/12 -27,75, tdoff 12/12 -29,0, const 11/12 -12,25, eplr 11/12 -19,0 : ERODE ; seuil_tient 14 -> (True, 0.00317, 0.00357), 15 -> True (0.00333), 16 -> False (0.003125) ; lectures en tools/evo_runs/s2_bassin_fragility.py:659-715 et :832-844
- **Constat** : Recompte indépendant : le verdict évalue 15 tests de signe hors qualificatifs (classes de pos et eps, contraste eps moins greffe complète, 6 classes du tirage de signes, 6 contrastes tirage moins greffe) ; celui de b_zero n'est jamais lu car sa greffe sort NEUTRE sur les données publiées. 14 lus = 14 déclarés ; la marge de 11/12 tient jusqu'à 15 et casse à 16. Pas de défaut de taille sur les tests de signe.
- **Classe** : aucune
- **Verdict** : non confirmé

## P5 — les deux issues sont-elles possibles ?

### P5.a — inertie de eps jugée par égalité exacte
- **Sonde** : `python C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/p5_v6_miroir.py` (le fragility_verdict du runner sur les S_a/S_tr publiés, aucun monde construit) ; `grep -n controle_direction_non_eprouve tools/evo_runs/s2_bassin_fragility.py`
- **Preuve** : Avec eps = S_a + 0,5 sur les 12 seeds, 9b passe 12/12 avec une médiane de +28,8, contre +28,2 pour S_a − S_tr_full (branche 8). Seeds où eps = noop : 0/12, drapeau False, « NON ÉPROUVÉ » absent du why. Avec eps inerte plus un bruit σ = 1 : 400 verdicts LU sur 400, 9b passé et drapeau False à chaque fois. Code : tools/evo_runs/s2_bassin_fragility.py:671 (test par ==), :675, :874-875.
- **Constat** : Le correctif de la v5 déclare eps inerte seulement si les survies sont EXACTEMENT égales. Or une perturbation de 1e-3 qui ne détruit rien peut quand même décaler une trajectoire d'un demi-tick, par le seul chaos. Dans ce cas eps reste neutre et 9b reproduit le contraste de la branche 8 à 0,6 tick près, mais le drapeau reste faux et le motif du verdict n'en dit rien. Le témoin positif de DIRECTION n'est donc signalé « non éprouvé » que si la dynamique est reproductible au bit sous 1e-3, ce que personne n'a mesuré : aucune survie eps n'existe avant le sceau. Il faut juger l'inertie par la bande déjà calculée (eps dans_la_bande_vs_S_a) ou par un écart à S_a inférieur à delta_min, pas par ==
- **Classe** : E1
- **Verdict** : confirmé

### P5.b — garde de létalité et sixième bras b_tdoff
- **Sonde** : `python C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/p5_v6_letalite.py` (fragility_verdict ; nets de la sonde de pré-scellement, b_tdoff à 20, 50 et 101 ; résurrections médianes publiées ; lectures imposées)
- **Preuve** : Lectures imposées : full et tdonly FRAGILE, const et eplr DIRECTION. b_tdoff DIRECTION à net 20 -> MIXTE_PAR_AMPLITUDE, partition_letale False. b_tdoff FRAGILE à net 20 -> MIXTE. MIXTE_AMPLITUDE_OU_LETALITE ne sort que pour b_tdoff FRAGILE à net 50 ou 101, au-dessus des 28 de b_const : 2 configurations sur 6, et aucune au net d'environ 20 que prédit la règle (v6.json:29, predictions_avant_le_run ; v6.json:11, branche 11c).
- **Constat** : La règle annonce qu'un partage des quatre bras full/tdonly/const/eplr serait mis au compte de la létalité. Ce raisonnement oublie b_tdoff, le sixième bras, qui érode sur tous les seeds et doit donc se ranger d'un côté. Au net que la règle lui prête (environ 20, sous b_const), la garde de létalité ne peut pas produire son issue. Si b_tdoff est lu DIRECTION, il est le moins létal de tous (3,5) et rejoint b_const (65,5) : la séparation par la létalité disparaît et le code attribue le partage à l'amplitude. S'il est lu FRAGILE, il casse l'ordre des nets et le code rend MIXTE. La protection annoncée n'existe que dans une configuration que la prédiction du même texte exclut. Il faut corriger la prédiction en jouant le verdict sur les six bras
- **Classe** : E8
- **Verdict** : confirmé

### P5.c — puissance symétrique des deux issues
- **Sonde** : `python C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/p5_v6_puissance.py` (monde D : sham = S_a + bruit ; monde F : sham = S_tr + bruit ; 400 tirages par σ, verdict du runner, S_a et S_tr publiés)
- **Preuve** : À σ = 2 : monde D -> DIRECTION 343/400, monde F -> FRAGILE 350/400. À σ = 4 : 279 contre 267. b_const NON_TRANCHE : 115 (D) contre 126 (F). À σ = 0, les deux issues sortent.
- **Constat** : Aucune des deux issues n'est structurellement plus dure à obtenir. À bruit égal, l'issue vraie sort avec une puissance comparable dans les deux mondes. La perte de puissance vient de b_const, et elle est la même dans les deux mondes.
- **Classe** : E2
- **Verdict** : non confirmé

### P5.d — contrôles positifs jugeables seulement après le run
- **Sonde** : python -c qui charge results/s2_bassin_fragility_sonde_conception.json et compte pos / eps / S_pos / S_eps ; grep -n des trois gardes dans tools/evo_runs/s2_bassin_fragility.py
- **Preuve** : Clés du JSON : W_sonde_sha256, _comment, sonde_net_chemin, sources, temoin_parallelisme ; 0 occurrence de pos, eps, S_pos ou S_eps. Gardes : assert_not_degenerate seule (:624, :700, :787) ; 0 appel à assert_positive_control et 0 à assert_ablation_changes_something. Les branches 7 et 9b sont testées à part (tests/sandbox/test_s2_bassin_fragility.py:259, :397).
- **Constat** : Les valeurs des deux contrôles positifs ne pourront être jugées qu'après le run. L'écart de régime de pos (24 à 718 fois l'amplitude des bras) est déjà déclaré dans la règle.
- **Classe** : aucune
- **Verdict** : hors périmètre

## P6 — plancher de bruit

### P6.a — bande de tirage avec référence S_tr traitée comme exacte
- **Sonde** : `python scratchpad/p6_band_null.py` (appelle tools.evo_runs.s2_bassin_fragility._bande_contraste, 300 reps, 12 seeds x 5 tirages, référence exacte vs référence = un tirage de plus) ; python -c sur results/s2_credit_ablation.json (b_zero) et s2_credit_ablation_2.json (a_frozen) : écart par seed
- **Preuve** : Sortie : sigma=1 couverture ref EXACTE 0.997 / ref ECHANGEABLE 0.940 ; sigma=2 0.997 / 0.880 ; sigma=4 0.983 / 0.870. b_zero - a_frozen par seed = [0.5,-5,-7,-7.5,-0.5,-8.5,-0.5,0,2,-7.5,0,-1], écart-type 3.84. Témoin à référence sans bruit : tests/sandbox/test_s2_bassin_fragility.py:517-518 ; bootstrap sur les seuls tirages : tools/evo_runs/s2_bassin_fragility.py:525-527 ; bande nulle pour tirages identiques : test_s2_bassin_fragility.py:491 ; couverture >= 0,98 affirmée : cible v6 lignes 7 et 54.
- **Constat** : La bande de tirage traite la référence S_tr comme exacte : seuls les 5 tirages du sham sont rééchantillonnés, et le témoin de couverture simule un nul où la greffe n'a aucun bruit. Or sous l'hypothèse FRAGILE le crédit n'est qu'une réalisation de plus parmi les tirages de signes ; sur ce nul échangeable la bande couvre 0,94 / 0,88 / 0,87 (sigma 1/2/4) et non les >= 0,98 annoncés. Le bruit d'une réalisation unique n'est pas petit : un DeltaW minuscule (b_zero) déplace la survie d'un écart-type de 3,84 ticks d'un seed à l'autre. Cas extrême : des tirages eps identiques rendent une bande de largeur 0, contre laquelle tout écart au crédit complet sortira hors bande. La lecture par signe (11/12 + médiane) reste valide sous ce nul, symétrique ; c'est le drapeau de bande et la couverture publiée qui sont faux, 6 à 13 % de faux hors-bande.
- **Classe** : E6
- **Verdict** : confirmé

### P6.b — indice de saturation sans plancher de bruit
- **Sonde** : python -c : saturation et marge |S_tr-S_a| - 0,9(S_a-S_c) par seed depuis results/s2_credit_ablation{,_2}.json et results/s2_credit_retention.json (c_cold_credit)
- **Preuve** : Sortie : b_tdoff sat med 1.017 min 0.946, marge med 2.95 min 0.85 tick ; b_full sat med 0.979 min 0.9, marge med 2.37 min 0.0 ; b_eplr sat med 0.649. Aucune bande sur la saturation : tools/evo_runs/s2_bassin_fragility.py:579-580 (comparaison nue à saturation_high).
- **Constat** : L'indice de saturation |S_tr - S_a|/(S_a - S_c), qui décide la lisibilité de la garde E19 et le qualificatif de suffisance, est un ratio comparé à 0,9 sans aucun plancher de bruit. Sur les données publiées, la marge au seuil ne vaut que 2,95 ticks en médiane pour b_tdoff (minimum 0,85) et 2,37 pour b_full (minimum 0,0 : un seed pile sur le seuil), sous l'écart-type de 3,84 ticks d'une réalisation unique. Le caractère CERTAIN tient au rejeu au bit ; l'interprétation physique (bras collé au plancher) ne tient qu'à environ deux erreurs-types sur la médiane.
- **Classe** : aucune
- **Verdict** : confirmé

### P6.c — fraction épargnée et fermeture E19 sans bande
- **Sonde** : Read tools/evo_runs/s2_bassin_fragility.py:563-602 ; `grep -n "_bande_contraste" tools/evo_runs/s2_bassin_fragility.py`
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:576-589 calcule frac et closure à partir de médianes ; les appels à _bande_contraste sont aux lignes 661, 666, 697, 698 seulement, aucun dans _garde_e19.
- **Constat** : La fraction épargnée f et la fermeture de la garde E19 sont des ratios de médianes publiés sans bande : _garde_e19 ne passe jamais par _bande_contraste. Sans effet sur CE run (la garde est illisible d'avance), mais le jour où une paire lisible la fera réétiqueter, une fermeture > 2/3 pourra sortir du seul bruit de tirage.
- **Classe** : aucune
- **Verdict** : confirmé

### P6.d — ratio publié contre bande du no-op
- **Sonde** : grep -noiE "no.?op" sur la cible v6 et sur results/s2_bassin_fragility_sonde_conception.json
- **Preuve** : Cible : 7 occurrences (lignes 13, 23, 27, 28, 30), toutes S_a ou branche 2 ; JSON de sonde : 4 lignes (2, 5, 6, 964), toutes run_noop / ages_identical_to_a_frozen ; aucun results/s2_bassin_fragility.json.
- **Constat** : Aucun ratio n'est encore publié (pré-inscription, run non lancé) : la comparaison ratio publié contre bande du no-op exigée par P6 n'est pas faisable ici. Le seul no-op du dispositif (noop contre a_frozen) est un témoin de réplication, pas un plancher de contraste.
- **Classe** : aucune
- **Verdict** : hors périmètre

## P7 — dose, létalité

### P7.1 (JUGE) — dose par ligne de W
- **Sonde** : `python <scratchpad>/p7v6_slot.py` (depuis .worktrees/science) ; lecture de src/worlds/world_1_stoneage.py:1062,1082,1765,1778,1784 et src/agents/backend_torch.py:262,502
- **Preuve** : 72 cellules publiées : td_calls=2000 et td_updates=1999 sur full, tdonly, const, zero pour des résurrections de 2 à 380 ; episode_calls=250 partout, skips sans pop_desync ni id_missing. world_1_stoneage.py:1765 (TD) et :1778 (épisodique) précèdent :1784 (retrait des morts) ; :1062 reconstruction seulement si B change ; :1082 saut si B désynchronisé. backend_torch.py:262 et :502 : moyenne sur B, aucun masque. Borne haute médiane min(res,250)/250 des fenêtres croisées : zero 0,716 ; const 0,262 ; eplr 0,066 ; full 0,040 ; tdoff 0,014.
- **Constat** : La réserve de la règle (ligne 3) dit que le compteur rejoué ne rend pas la dose reçue par chaque agent. Le code dit le contraire. En phase 1 le lot torch garde ses 12 lignes à chaque appel : un corps qui meurt ne quitte la liste qu'après les deux appels d'apprentissage du tick, la recharge le remet avant le tick suivant, et la population n'est reconstruite que si B change. Les deux pertes font une moyenne sur B sans masque, donc chaque ligne de W reçoit chaque mise à jour : sa dose est exactement le compteur publié (1999 TD ; 250 ou 0 épisodiques), que la branche 4 exige déjà au bit. La critique v3 P7.3 était un faux positif, et la règle en garde une limite qui n'existe pas. La limite réelle est le brassage, déclaré dans « mesure » mais sans sa borne : la part des mises à jour dont la fenêtre enjambe un changement ligne→corps. Elle se calcule depuis les résurrections publiées et écarte encore la paire E19 d'un facteur 4,7 (eplr contre tdoff).
- **Classe** : E8
- **Verdict** : confirmé

### P7.2 (JUGE) — la létalité agit-elle seed par seed ?
- **Sonde** : `python <scratchpad>/p7v6_intra.py` ; `python <scratchpad>/p7v6_letal.py` (depuis .worktrees/science, sur results/s2_credit_ablation_2.json et results/s2_credit_ablation.json)
- **Preuve** : Spearman(résurrections, S_tr − S_a) par bras, n=12 : tdonly +0,750 (p 0,005) ; full +0,286 (p 0,37) ; const −0,256 (p 0,42) ; eplr −0,056 (p 0,86) ; zero +0,362 (p 0,25) ; tdoff +0,401 (p 0,20). Entre les six bras : Spearman(résurrections médianes, érosion médiane) = +0,943 (p 0,0048) — tdoff 3,5/−29,0 ; tdonly 8/−27,75 ; full 10/−28,25 ; eplr 16,5/−19,0 ; const 65,5/−12,25 ; zero 179/−0,75. Texte visé : ligne 11 du JSON v6 (branche 11c).
- **Constat** : Pour appuyer que la mortalité de phase 1 pèse sur l'issue, la branche 11c ne cite qu'un bras, b_tdonly, où les seeds qui meurent le plus sont ceux dont la greffe érode le moins. C'est le seul sur six. Rejoué sur les douze seeds publiés de chaque bras, le lien intra-bras est faible et de signe changeant ailleurs, jamais significatif. Entre bras au contraire, les six érosions médianes suivent presque exactement l'ordre des résurrections médianes, mieux que l'ordre du net que la règle reconnaît non monotone. La létalité se comporte donc comme une marque du variant de crédit, pas comme un mécanisme établi seed par seed. L'étiquette qui refuse d'attribuer à l'amplitude reste fondée, mais sa justification publiée repose sur l'échantillon saillant : il faut publier les six coefficients, pas celui qui sort.
- **Classe** : E9
- **Verdict** : confirmé

### P7.3 (JUGE) — dose publiée, cohorte constante, chiffres de létalité
- **Sonde** : `python <scratchpad>/p7v6_dose.py` ; `sed -n 476,491p tools/evo_runs/s2_bassin_fragility.py`
- **Preuve** : s2_bassin_fragility.py:481-486 ; s2_credit_retention.py:73 (benchmark_mode) ; âges publiés de longueur 12 partout ; facteur 51,14 ; eplr > tdoff 12/12 ; chemin tdoff/eplr 1,36 [0,83 ; 2,84], min au seed 2027 ; masse ×7,34 ; tdoff 101,3/agent ; 2035 S_a 42,0 contre 39,5 ; zero −8,5 à +2,0.
- **Constat** : Rien à reprocher sur ce point. Le rejeu exige au bit chemin, âges, TD, épisodique, résurrections et ticks ; le lot fait 12 en phase 1 comme en phase 2, sans naissance possible ; le gel de phase 2 est asserté. Tous les chiffres de dose et de létalité de la règle se recalculent à l'identique depuis les JSON suivis.
- **Classe** : aucune
- **Verdict** : non confirmé

## P8 — aliasing, chevauchement, corps

### P8.a — troisième écrivain de H (reconstruction de population)
- **Sonde** : `python C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/p8_v6_vue_reset.py` (sans monde : make_population à B puis à B-1) ; `python .../scratchpad/p8_v6_reset_H.py` (âges publiés de results/s2_credit_ablation_2.json et s2_credit_ablation.json) ; grep -o sur la v6 de 'zéro', 'réinitialis', 'rebuild', 'SECOND écrivain' (contrôle positif : 'sans reconstruire la population torch' = 1)
- **Preuve** : src/worlds/world_1_stoneage.py:1060-1066 (reconstruction ssi B != len(models)) ; src/agents/backend_torch.py:111 (self.H = torch.zeros) ; sonde : |H| des 2 survivants 175.511 -> 0.000 après reconstruction à B-1 ; remises par seed médiane 10.0 (a_frozen) contre 5.0 (b_full), 1re remise tick 7.5 contre 4.0 (b_tdoff) ; v6 : 'zéro' 0, 'réinitialis' 0, 'rebuild' 0, 'SECOND écrivain' 1 (ligne 3). Recevabilité mécanique vérifiée : tools/refutateur_temoins.recevabilite -> 1 recevable, 0 rejet, seuil 8 mots.
- **Constat** : Troisième écrivain de H, non inventorié. En phase 2 (mortelle), chaque tick qui tue fait tomber B d'une unité ou plus ; le monde refait alors l'objet population torch, dont le constructeur pose H à zéro pour TOUS les survivants. La règle n'énumère que deux écrivains (vote social compté, retrait de 0,1 non compté) et le runner ne compte pas celui-ci. Sa dose dépend de la condition : sur les âges publiés, les survivants subissent en médiane 10 remises à zéro (a_frozen, b_const, b_zero), 9 (b_eplr), 5 à 5,5 (b_full, b_tdonly, b_tdoff), et la première arrive plus tôt dans les bras qui érodent (tick médian 4,0 à 5,5 contre 7,5 sous le no-op). Une mort précoce efface donc la mémoire récurrente des onze autres clones : couplage entre agents porté par l'issue même qu'on mesure, capable d'amplifier une érosion en cascade, et dont la fréquence différera entre transplant, sign, iso et pos. Remède : compter les reconstructions par phase 2 à côté de compter_consensus, publier par condition, le déclarer.
- **Classe** : E5
- **Verdict** : confirmé

### P8.b — chevauchement entrée/sortie (E24)
- **Sonde** : `python tools/check_io_overlap.py` ; python -c qui charge results/warm003_dagger_genome.npz et imprime N, num_inputs, num_outputs
- **Preuve** : porte 17 : 358 génomes persistés, 10 chevauchants connus, 0 nouveau, exit 0 ; bassin N 172, ni 59, no 108, début des sorties 64, chevauchement 0 ; tools/evo_runs/s2_credit_retention.py:61 (assert_no_io_overlap dans load_bassin)
- **Constat** : Chevauchement entrée/sortie (E24) : absent. Le bassin a 59 entrées, 108 sorties et 172 nœuds, donc les sorties commencent au nœud 64 et ne recouvrent aucune entrée. load_bassin refuse un chevauchement à chaque chargement, et les W persistés par cellule héritent de ces dimensions.
- **Classe** : E24
- **Verdict** : non confirmé

### P8.c — corps (E26)
- **Sonde** : `grep -n 'W\[' tools/evo_runs/s2_bassin_fragility.py` ; `pytest tests/sandbox/test_s2_bassin_fragility.py::test_body_guard_can_FAIL_when_the_body_is_recomputed_on_the_posed_W__review_P10c` ; `grep -n update_phenotype src/worlds/world_1_stoneage.py` ; python -c comptant len(ages) sur 36 lignes publiées
- **Preuve** : s2_bassin_fragility.py:32 et :185 (seules occurrences de W[) ; src/agents/mamba_agent.py:83-84 (corps sur W[0:5], W[5:10]) et :174-178 (from_genome puis update_phenotype) ; témoin : 1 passed en 3.71 s ; world_1_stoneage.py:990 (update_phenotype dans _apply_hgt_breeding seulement) ; longueurs des âges publiés {12} sur n = 36
- **Constat** : Corps (E26) : les shams iso et pos touchent les lignes 0:10 dont le monde tire le corps, mais le corps reste celui du bassin : from_genome le calcule, W est posé ensuite sans recalcul, et la garde compare avant et après chaque phase 2 à phenotype_of. Son témoin gelé lève bien sur un recalcul. Le seul autre appel à update_phenotype du monde est la reproduction HGT, et les âges publiés comptent toujours 12 agents : aucune naissance.
- **Classe** : E26
- **Verdict** : non confirmé

### P8.d — vue de l'état récurrent
- **Sonde** : `python C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/p8_v6_vue_reset.py` ; `grep -n CONDITION_GATE src/agents/backend_torch.py`
- **Preuve** : sonde : np.shares_memory(logits, pop.H) = True ; logits[0,0] -= 0.1 visible dans H[0, N-O] = True ; src/agents/backend_torch.py:48 (CONDITION_GATE = False) et :200 (logits = H_new[:, N-O:N]) ; world_1_stoneage.py:1340 (retrait de 0,1 en place)
- **Constat** : Vue de l'état récurrent : vérifiée comme vraie, mais déjà déclarée. Les logits renvoyés par forward partagent la mémoire de H, et une écriture dans les logits se retrouve dans H. Aucun porte-logits ne clone la sortie ici, puisque le gate de conditionnement est éteint par défaut. Le vote social est compté, le retrait de 0,1 est déclaré sans être compté : pas de défaut nouveau sur ce point.
- **Classe** : E5
- **Verdict** : non confirmé

## P9 (DÉLÉGUÉ) — provenance et sceau

### P9.a — porte 20
- **Sonde** : `cd .worktrees/science && python tools/check_evidence_provenance.py --only <cible v6.json> ; echo exit=$? ; git merge-base --is-ancestor 3c9414f6 HEAD`
- **Preuve** : sortie de la porte : 'records : 304 | ... | absents : 18 | non suivis : 0 ... OK : 18 chemin(s) légataire(s) gelé(s). Aucun nouveau, aucune régression.' exit=0 ; comptes IDENTIQUES avec --only S2-BASSIN-FRAGILITY ; tools/check_evidence_provenance.py:362 ne garde que les fautes des records EDR balayés ; merge-base -> 'fix P2.128 ABSENT' de HEAD 82927108 (tmp/science)
- **Constat** : Verdict de la porte recopié : OK, sortie 0. Il ne dit rien de la cible : un brouillon JSON de pré-inscription posé dans le scratchpad n'entre pas dans les 304 records scannés, et le filtre --only ne retient que des records EDR, donc un --only qui ne désigne aucun record rend vert par construction. Le correctif qui refuse ce cas (3c9414f6, P2.128) n'est pas dans la branche tmp/science. Dette, pas critique : fusionner 3c9414f6 avant de rejouer P9 sur le futur record.
- **Classe** : E4
- **Verdict** : hors périmètre

### P9.b — équivalent manuel de la porte 20 pour les chemins cités
- **Sonde** : `grep -oE 'results/[A-Za-z0-9_./*-]+' <cible> | sort | uniq -c ; git ls-files --error-unmatch results/s2_bassin_fragility_sonde_conception.json ; sed -n 18p .gitignore ; git ls-files results/s2_bassin_fragility_genomes | wc -l`
- **Preuve** : 3 motifs cités : results/s2_bassin_fragility_sonde_conception.json (2 fois) -> SUIVI ; results/s2_bassin_fragility_genomes/ -> 0 fichier suivi et répertoire absent du disque ; .gitignore:18 = 'results/*'
- **Constat** : La seule évidence mesurée avant le sceau (la sonde de conception) existe et est suivie par git. Le répertoire des génomes n'existe pas encore : c'est une sortie du run à venir, annoncée hors git avec son sha256 dans l'agrégat. Aucun défaut de provenance aujourd'hui ; à noter pour le record : l'agrégat tombera sous le motif ignoré de .gitignore:18 et devra être ajouté de force pour satisfaire la porte 20.
- **Classe** : aucune
- **Verdict** : non confirmé

### P9.c — sceau de la pré-inscription
- **Sonde** : `python -c "from tools.preregister import verify; verify('S2-BASSIN-FRAGILITY')" ; echo exit=$? ; ls docs/preregistrations | grep -i -c bassin`
- **Preuve** : FileNotFoundError: aucune pré-inscription << S2-BASSIN-FRAGILITY >> -- la règle n'a pas été scellée avant le run ; exit=1 ; 0 fichier 'bassin' dans docs/preregistrations (tools/preregister.py:195-196)
- **Constat** : Verdict recopié : aucun sceau n'existe, donc son intégrité ne se teste pas. C'est cohérent avec l'état déclaré de la cible (brouillon v6 en revue, champ provenance ligne 31) : rien à signaler tant que register n'a pas été appelé. À rejouer tel quel juste après le scellement, puis avant toute lecture des résultats.
- **Classe** : aucune
- **Verdict** : hors périmètre

## P10 (JUGE) — mécanismes cités

### P10.a — qualificatifs déclarés écrits dans le motif du verdict
- **Sonde** : `sed -n 856,880p tools/evo_runs/s2_bassin_fragility.py | grep -c 'dans_la_bande\|bandes'` ; `sed -n 867,880p tools/evo_runs/s2_bassin_fragility.py | grep -c 'op_ratio\|sign_x2\|fraction\|bande_vs_S_a'` ; `grep -o 'qualificatif dit' S2-BASSIN-FRAGILITY.v6.json | wc -l`
- **Preuve** : grep : 4 occurrences de bande dans why, toutes issues du seul sham sign (lignes 856-857) ; 0 occurrence de op_ratio, sign_x2, fraction ou bande_vs_S_a dans why (867-880). Ces grandeurs sont publiées seulement aux lignes 661-663 et 666-669 (bandes eps et pos), 720-721 (rapport d'opérateur) et 748 (fraction). La règle, v6.json:7 (branche 10), exige qu'elles soient dites dans le motif ; le grep de 'qualificatif dit' y rend 1.
- **Constat** : La v6 promet que plusieurs qualificatifs apparaissent en toutes lettres dans le texte why du verdict. Le runner les calcule et les range dans le JSON, mais ne les écrit jamais dans why. Sont concernés : la bande de tirage des contrôles eps et pos contre S_a, la bande du contraste 9b, le rapport de norme d'opérateur et le contraste sign x2 moins greffe, et la fraction de perte exigée pour lire FRAGILE. Seuls atteignent le motif : les bandes du sham sign, la dégénérescence, la saturation, le plancher eps, la partition létale, le contrôle de direction non éprouvé et la paire E19 non défendue. verifier_seuils ne relie au code que le bloc seuils : ce décalage passerait le sceau.
- **Classe** : E10
- **Verdict** : confirmé — avant le sceau, soit écrire ces qualificatifs dans why, soit remplacer « DIT » par « publié » dans la branche 10

### P10.b — ce que compte compter_consensus
- **Sonde** : `python scratchpad/p10_consensus_counter.py` — appelle Biosphere3D._apply_social_consensus sur un objet minimal (deux agents sur la même case, logits 13 et 14 au-dessus des seuils) sous l'enveloppe du runner, sans construire de monde
- **Preuve** : Sortie de la sonde. Lignes égales : SOCIAL_CONSENSUS émis 1 fois, compteur {ticks_avec_vote: 0, lignes_reecrites: 0}. Lignes différentes : 1 vote, compteur {1, 2}. s2_bassin_fragility.py:236-239 ne compte que si out != before ; world_1_stoneage.py:970-974 vote et émet sans condition de changement ; la règle nomme ce champ « ticks avec vote » en v6.json:27.
- **Constat** : Le champ ticks_avec_vote ne compte pas les votes. Il ne retient un tick que si au moins une ligne de logits a changé de valeur. Si les votants portent des lignes égales (clones du no-op au même état et devant la même observation), le monde vote et le compteur rend zéro. Le même vote est compté dès que les lignes diffèrent, par exemple quand chaque clone porte son propre ΔW. La fréquence de vote que la règle dit mesurer par condition est donc biaisée par l'hétérogénéité des lignes, et le no-op est sous-compté. Portée descriptive : cette mesure n'entre pas dans le verdict.
- **Classe** : aucune
- **Verdict** : confirmé — portée limitée : compter les appels où plus d'un agent vote, ou renommer le champ en ticks avec réécriture

### P10.c — autres mécanismes cités, relus un par un
- **Sonde** : `grep -nE 'logits\[.*\] *(\+|-)?= ' world_1_stoneage.py` (step) ; python -c (npz du bassin : dims, blocs vers les nœuds 77-78, L1) ; python -c (JSON P4.16, P4.9, P4.4 : saturation, résurrections) ; python -c verifier_seuils(v6), seuil_tient() ; `python scratchpad/p10_band_replay.py`
- **Preuve** : 1 seule écriture en place, world:1340. Bassin : I=59, O=108, blocs 0,727 et 0,929, soit 8,9 % et 9,8 %. Saturation de b_tdoff : min 0,946, médiane 1,017, ≥ 0,9 sur 12/12 seeds. pos vaut 24,3 à 718,5 fois le déplacement. verifier_seuils rend True ; seuil_tient rend 0,00317 ≤ 0,00357. Bande rejouée : couverture du nul 0,978 à 1,000 pour σ de 0,5 à 8 ; puissance 0,978 pour un effet de 2 sous σ = 2. Lignes lues : backend_torch.py:84, :141, :198-200, :502, :510-513 ; backend.py:65 ; learning_events.py:173, :187, :242-243 ; s2_credit_retention.py:111 ; world:1060-1062.
- **Constat** : Contrôle de couverture, aucune affirmation fausse. Le gate est inactif : aucun CONDITION_GATE n'est posé sur le chemin, donc les logits sont une vue de H. La seule autre écriture en place est le retrait de 0,1. TD touche 11 colonnes et l'épisodique 8. Le pas est lr/12 sous SGD avec une perte moyennée sur B. Le 0,04 par défaut atteint bien la voie épisodique par l'optimiseur partagé. La résurrection ne reconstruit pas la population. Le chemin dW_abs_sum se cumule à chaque mise à jour. Les chiffres dérivés du code et des JSON se retrouvent, et la bande de tirage rejouée tient sa couverture et sa puissance.
- **Classe** : aucune
- **Verdict** : non confirmé — les mécanismes sont exacts à la lecture. Hors périmètre, relève de P2 / porte 19 : le pas 0,04 de b_tdoff n'est publié nulle part (lr et lr_effective valent None sur 12/12 seeds de P4.9).

---

## Addendum de l'auteur (session SCIENCE-HARNAIS, 2026-09-26) — suites données, v6 → v7

Deux passages NULS ont précédé cette revue, et aucun ne met la règle en cause. Au premier (`wf_b7cd5fdc-d98`), le juge
a rendu INDÉCIDABLE sur un témoin, alors qu'il était calibré 5/5 : c'est un nul légitime de l'instrument. Au second
(`wf_c3134d3f-8dd`), les trois témoins ont été retrouvés, mais le vérificateur a écrit « aucun » dans le champ `refus`.
C'est une récidive du nul de transport de `bfaea9c6`, inscrite comme P2.133. Elle a été contournée par une copie locale
qui tient « aucun » pour une absence de refus, puis par une REPRISE du même run : les huit agents ont été rejoués depuis
le cache, seule la revue a tourné. La revue DISCRIMINE : le témoin cru sain rend 6 critiques recevables, les défectueux
au moins 7.

Chacune des 13 critiques confirmées a été revérifiée contre le code et les JSON. Les chiffres relayés ont été recalculés
de ce côté : coefficients de Spearman, borne des fenêtres croisées, reconstructions médianes, couverture de la bande.
Quatre critiques touchent le fond : P6.a (la bande fabriquait encore du signal sous le nul de FRAGILE), P8.a (un
écrivain de H non inventorié), P5.a (le contrôle de DIRECTION n'était signalé « non éprouvé » qu'à l'égalité au bit) et
P4.a (le remède tiré d'un contraste hors famille). La version soumise au sceau est donc la **v7**, relue à son tour.

**Suites données aux critiques confirmées.**
- **P6.a (E6)** — critique REPRODUITE : sous le nul échangeable, le bootstrap v6 couvre 0,95 / 0,89 / 0,88 / 0,87 à
  σ = 1 / 2 / 4 / 8. La bande devient un bootstrap ÉCHANGEABLE : par seed, le pool réunit les tirages et la référence,
  et chaque réplicat tire la médiane ET la référence dans ce pool. Quantile 0,975, scellé. Couverture mesurée : >= 0,967
  sous le nul échangeable, >= 0,997 à référence exacte ; puissance 0,99 à un effet de 4 sous σ = 2. Nouveau témoin gelé :
  il exige >= 0,95 sous le nul échangeable et REFUSE le bootstrap v6 (0,90 à σ = 4). Le contre-exemple à réponse connue
  est conservé.
- **P8.a (E5)** — `compter_reconstructions` compte, par phase 2, les constructions de la population torch et la suite
  des B. Il enveloppe `make_population`, n'y change rien et est restauré en `finally`. Chaque reconstruction remet H à
  zéro pour tous les survivants. Le compte est publié par condition et déclaré dans « ce que ce run ne tranche pas »,
  avec les médianes recalculées sur les âges publiés : 10 sous le no-op, 5 à 5,5 pour les bras qui érodent le plus. Deux
  témoins gelés : réponse connue sans monde, et monde réel sur le no-op.
- **P5.a (E1)** — eps est déclaré INERTE s'il vaut le no-op au bit sur au moins 11 seeds, OU s'il tombe dans sa bande
  contre S_a. Témoins gelés : un eps décalé d'un demi-tick et bruité est inerte, donc le contrôle est non éprouvé ; un eps
  qui s'écarte de 4 ticks sans éroder éprouve 9b.
- **P4.a (E23)** — le contraste ×2 − greffe devient DESCRIPTIF (drapeau `descriptif_ne_tranche_rien`, compte des signes
  publié). La lecture 11b ne tranche plus le remède : l'ancre et le clip spectral restent deux candidats, à départager
  dans leur propre règle. Témoin gelé : un ×2 qui érode ne change rien au verdict.
- **P1.a (E8)** — le motif de l'illisibilité E19 est corrigé. La v6 rangeait b_tdonly, dont l'épisodique est coupé,
  parmi les bras épisodiques saturés, et taisait b_const. La paire est de même voie (épisodique seul) ; b_tdoff est le
  seul bras publié de cette voie au pas 0,04. L'illisibilité est déclarée comme un CHOIX de conception (réplication au
  bit du publié), pas comme une contrainte du dispositif.
- **P5.b (E8)** — la prédiction est rejouée sur les SIX bras. Si b_tdoff est lu DIRECTION : MIXTE_PAR_AMPLITUDE, et
  l'attribution à l'amplitude est soutenue, puisque le bras le moins létal se range avec le plus létal. Si b_tdoff est
  lu FRAGILE à net ≈ 20 : MIXTE. MIXTE_AMPLITUDE_OU_LETALITE ne sort que si b_tdoff est FRAGILE avec un net > 28.
- **P7.1 (E8)** — la limite « td_updates ne rend pas la dose par agent » est retirée : c'était un faux positif de la
  revue v3. La dose par ligne de W est exactement le compteur. La limite réelle, le brassage, reçoit sa borne recalculée :
  zero 0,716, const 0,262, eplr 0,066, full 0,040, tdonly 0,032, tdoff 0,014.
- **P7.2 (E9)** — 11c publie les six coefficients intra-bras et le coefficient entre bras (+0,943), plus le seul
  coefficient saillant. Il en tire que la létalité est une marque du variant, pas un mécanisme établi seed par seed.
- **P4.b (E8), P6.b** — saturation_high est déclaré posé à la conception, sans dérivation. Aucune lecture n'en dépend ici
  (la garde est illisible pour tout seuil <= 1,017). Le sens physique de la saturation est borné à environ deux
  erreurs-types.
- **P6.c** — la fraction épargnée et la fermeture sont déclarées sans bande. C'est sans effet ici ; elles devront en
  avoir une avant tout run à paire lisible.
- **P10.a (E10)** — le motif du verdict DIT désormais les bandes de eps, de pos et de 9b. La règle distingue ce qui est
  DIT (sham sign, contrôles, suffisance, plancher eps) de ce qui est seulement PUBLIÉ (iso, fraction requise, ×2, norme
  d'opérateur). Témoin gelé.
- **P10.b** — le champ du compteur de consensus est renommé `ticks_avec_reecriture` : il compte des réécritures, pas
  des votes. Dit dans la règle et dans le code.
- **P10.c (hors périmètre, suivi quand même, E8)** — le pas de b_tdoff n'est publié par aucun JSON de P4.9.
  `mesurer_pas_optimiseur` le lit sur l'optimiseur à chaque construction de la population rejouée
  (`pas_optimiseur_mesure`). Témoin gelé (0,04 par défaut, 0,004 passé), sauté sans torch.

Non confirmées ou hors périmètre : sans suite (P1.b, P1.c, P1.d, P2, P3, P4.c, P5.c, P5.d, P6.d, P7.3, P8.b, P8.c, P8.d,
P9.a, P9.b, P9.c, P10.c pour sa partie « mécanismes exacts »).
