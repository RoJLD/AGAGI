# Revue adversariale — E34-IDENTITY-CELL (v3)

- **Cible** : C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/E34-IDENTITY-CELL.v3.json (pré-inscription)
- **Date** : 2026-09-28
- **SHA** : 5ac488fbbd29cb6decc1d4af9a7a2766f153eff6 (worktree .worktrees/e34)
- **Résultat des TÉMOINS** (commandes rejouables : `PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier <témoin> <scratchpad>/refutateur_v3/critiques-<témoin>.json --extrait <scratchpad>/temoins_v3/temoin-N.md [--jugement OUI]`) :
  - S2-BLIND-CHAMPION-42e9357 : RETROUVE, code 0, 7 recevables (temoin-1.md, jugement OUI)
  - EDR-GRAB-COST-1828371 : RETROUVE, code 0, 6 recevables (temoin-3.md, jugement OUI)
  - EDR-RETAIN-COMPOSE-4204f8f : RETROUVE, code 0, 7 recevables (temoin-4.md, jugement OUI)
  - LOCK-002-286f244 (cru sain) : MESURE, code 0, 6 recevables (temoin-2.md)
  - PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5
  - plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1)
  - ⚠ INDISCRIMINANT : le record cru sain rend autant de critiques recevables que les defectueux

Critiques confirmées : **14** sur 32.

## P1

### P1.a — échangeabilité de S_on non mesurée
- **Sonde** : python scratchpad/p1_exch_probe.py (vrais immortal_after_step et _identity_counters du runner, cohorte factice de 12, une mort en p=0/3/10, aucun monde ni tirage global)
- **Constat** : La prémisse qui porte MATERIEL, et la borne de fausse alarme 2/13, suppose que sous H0 la valeur S_on se tire comme n'importe quel S_perm_k. Rien ne la mesure : elle est posée. Or, dans le code même, le bras allumé est le SEUL des treize dont l'ordre de service revient à celui d'avant t1 (0 position déplacée), alors que chaque permutation en déplace 8 à 12. Le texte cite pourtant un effet de position (qui est servi d'abord ramasse). Un ordre stable contre un ordre re-tiré peut donc à lui seul sortir S_on de la bande sans que l'identité joue. Pour que la borne tienne, il faut que ni l'identité ni l'ordre n'aient d'effet, et le run ne teste que le premier des deux.
- **Preuve** : E34-IDENTITY-CELL.v3.json:6 et :12 ; tools/evo_runs/s2_credit_retention.py:132-133 ; bras allumé = 0 position changée pour p=0, 3, 10 ; perm_1..12 à p=0 = [12,12,9,11,11,8,11,12,9,12,11,11] (moyenne 10,75), 11,17 à p=10
- **Classe** : E8
- **Verdict** : confirmé

### P1.b — la bande ne reçoit pas la dose de la cellule
- **Sonde** : même sonde (scratchpad/p1_exch_probe.py) : commutations au premier changement d'ordre, bras éteint contre perm_k
- **Constat** : La bande ne reçoit pas la dose de la cellule publiée. À chaque changement d'ordre, une permutation fait commuter environ 11 tranches, contre B-p pour le bras éteint (2 quand la mort tombe en p=10). Sous H1, les permutations peuvent donc tomber SOUS S_off et laisser S_on au-dessus de leur maximum avec dS = 0. Aucune ligne de la discrimination n'exige S_on différent de S_off. La branche 9a pose alors des bandeaux candidats sur un arc dont la cellule, qui est la ligne éteinte, n'a pas bougé. slot_switches est publié pour chaque bras mais ne compte pas dans le verdict.
- **Preuve** : E34-IDENTITY-CELL.v3.json:22 (9a) et :28 (dS descriptif) ; p=10 éteint=2 contre 11,17 ; p=3 éteint=9 contre 10,75 ; p=0 éteint=12 contre 10,75
- **Classe** : E8
- **Verdict** : confirmé

### P1.c — prémisses chiffrées
- **Sonde** : python -c chargeant results/s2_credit_retention.json (arms/b_warm_credit/2026) et results/s2_credit_ablation_2.json ; grep -n FLOOR tools/evo_runs/s2_credit_retention.py à 5ac488fb et via git show f1d6a987
- **Constat** : Les chiffres de prémisse repris dans la pré-inscription sont bien lus dans les JSON suivis et concordent. Témoin : 1999 mises à jour TD, 12 résurrections, somme |dW| exacte, âges de 5 à 11, médiane 7,0. Référence gelée : S_a = 31,5. Dispersion de b_full sur 12 seeds : de 7,0 à 9,5. Plancher : 9,0. Avec 250 mises à jour épisodiques, la borne de 144 commutations donne bien 0,6 % et 4,8 %. Aucune prémisse recopiée de mémoire.
- **Preuve** : td_updates 1999, resurrections 12, dW_abs_sum 18242.03954219818, episode_updates 250, survival_median 7.0 ; a_frozen[2026] = 31.5, b_full 7.0–9.5 ; s2_credit_retention.py:45 FLOOR = 9.0
- **Classe** : aucune
- **Verdict** : non confirmé

## P2 (DÉLÉGUÉ) — régime

- **Sonde** : `python tools/check_regime_claims.py --only <cible> ; echo exit=$? ; ls docs/EDR | grep -iE 'e34|identity'`
- **Constat** : Verdict recopié de la porte : REFUS, code 2. La cible est une pré-inscription JSON du scratchpad, pas un record EDR ; la porte 19 ne juge que les .md de docs/EDR et n'a rien pu confronter. Aucun paramètre n'a été vérifié par P2 : ce refus n'est ni un OK ni une discorde. Enquête non rouverte ; la question redevient jugeable quand le record et results/e34_identity_cell.json existeront.
- **Preuve** : « REFUS : --only designe 1 chemin(s) INCONNU(S) de cette porte », exit=2 ; grep docs/EDR : 0 fichier ; tools/check_regime_claims.py:361-363
- **Classe** : aucune
- **Verdict** : hors périmètre

## P3 (DÉLÉGUÉ) — balayage du pas

- **Sonde** : `python tools/check_e19_optimizer_sweep.py --only tools/evo_runs/e34_identity_cell.py; echo EXIT=$? ; ls docs/preregistrations | grep -i e34`
- **Constat** : La porte 23 classe le runner e34 en regle_absente (NOUVEAU, non bloquant) et sort OK : elle ne peut pas dire s'il tourne sous gradient, faute de règle scellée à lire (docs/preregistrations/E34-IDENTITY-CELL.json absent au sha 5ac488fb). Verdict recopié, enquête non rouverte.
- **Preuve** : runners scellés 35 | règle absente : 1 | [regle_absente] tools/evo_runs/e34_identity_cell.py | OK, EXIT=0 ; ls vide ; e34_identity_cell.py:39 et :322
- **Classe** : aucune
- **Verdict** : hors périmètre

## P4

### P4.a — DELTA_MIN transplanté
- **Sonde** : `grep -n 'delta_min' tools/evo_runs/s2_credit_ablation.py tools/evo_runs/s2_credit_retention.py tools/evo_runs/e34_identity_cell.py ; sed -n 181,190p tools/evo_runs/s2_credit_ablation.py`
- **Constat** : DELTA_MIN (5 ticks) vient de P4.4/P4.16, où il borne la MÉDIANE de 12 différences appariées avec un signe >= 10/12. La v3 l'applique à UNE différence intra-seed (|dS|, |dS_k|) et présente son origine comme un seuil par bras : même nom, autre objet, autre dispersion. Impact borné : FORT n'entre dans aucune branche du verdict (lignes 236-274) et perms_fort le recalibre sur la bande. Corriger la phrase d'origine, ou prendre la bande des |dS_k| comme seul étalon de FORT.
- **Preuve** : s2_credit_ablation.py:184 ; s2_credit_retention.py:372 ; e34_identity_cell.py:230 et :233
- **Classe** : E8
- **Verdict** : confirmé

### P4.b — compte des cellules
- **Sonde** : python scratchpad/p4_v3_sonde.py ; python tools/check_control_family.py --report
- **Constat** : 15 bras, 15 configurations distinctes, 12 en bande ; borne 2/13 = 0,1538 sur deux queues. control_family = None, n_independent = 1 : E23 n'exige rien. La borne figure dans le verdict (ligne 172), pas dans le bloc design.
- **Preuve** : ARMS 15, K_PERMS 12, borne FA 0.1538 ; porte : 33 runners scellés, 0 sans design ; e34_identity_cell.py:41-43, :172
- **Classe** : aucune
- **Verdict** : non confirmé

### P4.c — seuils importés
- **Sonde** : python -c lisant results/s2_credit_retention.json et results/s2_credit_ablation_2.json
- **Constat** : Aucun autre seuil importé. Bande et contrôle positif : même seed, même t1. FLOOR = 9,0 ne sert qu'au descriptif sous_plancher_off. Valeurs d'appui concordantes.
- **Preuve** : S_b 7.0, âges 5–11, dW 18242.03954219818 ; P4.16 n 12, 7.0–9.5, S_a 31.5 ; e34_identity_cell.py:221
- **Classe** : aucune
- **Verdict** : non confirmé

### P4.d — échangeabilité de l'étiquette « on »
- **Sonde** : `grep -n 'permutation(' tools/evo_runs/s2_credit_retention.py ; grep -n 'def restore_slot_order' -A12 tools/slot_identity.py`
- **Constat** : La borne 2/13 exige que « on » soit tiré parmi 13 ordres échangeables ; or on suit l'ordre de construction, les témoins un ordre uniforme. La règle le nomme LIMITE mais écrit la borne « par construction ». Relève de P5, pas de P4.
- **Preuve** : s2_credit_retention.py:193 ; slot_identity.py:44-45
- **Classe** : aucune
- **Verdict** : hors périmètre

## P5 (JUGÉ)

### P5.a — gardes de pré-vol
- **Sonde** : `grep -n "assert_positive_control\|assert_not_degenerate\|assert_ablation_changes_something" tools/evo_runs/e34_identity_cell.py tools/evo_runs/s2_credit_retention.py` (motif validé sur tools/evo_runs/)
- **Constat** : Aucune des trois gardes n'est appelée, mais chacune a son équivalent dans la lecture (cellule sans commutation, contrôle positif dont la dose TD ne baisse pas, bande aux Σ|ΔW| égaux). Pas de trou à elle seule.
- **Preuve** : 0 ligne ; motif trouvé dans evo011_preflight.py, s2_bassin_fragility.py, s2_reward_ablation.py ; e34_identity_cell.py:236, :248-250, :255-257
- **Classe** : aucune
- **Verdict** : hors périmètre

### P5.b — le contrôle positif peut-il échouer ?
- **Sonde** : Read tools/evo_runs/e34_identity_cell.py:58-59 et :196-274 ; `grep -n credit_cut_tick tools/evo_runs/s2_credit_retention.py`
- **Constat** : Le bras pos peut rater (S_pos dans la bande → NON_TRANCHE). Même seed, lieu, commit et t1 que la bande.
- **Preuve** : e34_identity_cell.py:266, :272, :196-204 ; s2_credit_retention.py:199-201
- **Classe** : aucune
- **Verdict** : non confirmé

### P5.c — cellule posée sur le plancher empirique
- **Sonde** : python heredoc : médianes par seed de results/s2_credit_retention.json et results/s2_credit_ablation_2.json
- **Constat** : Sur 72 cellules sous crédit, aucune médiane sous 7,0, qui est S_off. Une sortie par le bas exige S_on sous une valeur jamais vue. Le contrôle positif ne prouve la visibilité que vers le haut, et le sens attendu du correctif n'est écrit nulle part. Si réparer l'identité rend le crédit plus érosif, l'effet reste invisible et la lecture écrit NON_MATERIEL parce que pos est sorti par le haut. Le champ plancher ne ferme E3 que d'un côté. Parade : contrôle vers le bas, ou restreindre NON_MATERIEL à « aucun effet vers le haut ».
- **Preuve** : médiane minimale 7.0, atteinte 9 fois, 0 en dessous ; seed 2026 b_full 7.0 contre a_frozen 31.5 ; e34_identity_cell.py:266 (sens=+1) ; cible ligne 11
- **Classe** : E3
- **Verdict** : confirmé

### P5.d — dose de la bande contre bras éteint
- **Sonde** : python scratchpad/p5_v3_dose_perm.py puis python scratchpad/p5_v3_injection.py (injection dans identity_cell_verdict, aucun monde)
- **Constat** : Chaque changement d'ordre produit ~1,5× plus de commutations dans la bande que dans le bras éteint, zéro dans le bras allumé. Si l'identité compte, la bande est déplacée par sa propre dose et S_on peut en sortir en restant égal à S_off : MATERIEL et bandeaux sur l'arc publié pour un effet que le harnais n'a pas produit. Parade : exiger S_off dans la bande avant tout MATERIEL, ou lire dS contre la distribution des dS_k.
- **Preuve** : off 7.0 en moyenne, perm_k 9.27–11.91 (moy. 10.92), ratio 1.56, on 0 ; injection S_on = S_off = 7.0 → « verdict: MATERIEL_BAISSE | dS: 0.0 » ; e34_identity_cell.py:212, :251-265
- **Classe** : E6
- **Verdict** : confirmé

### P5.e — référence à pas nul
- **Sonde** : `grep -n "lr_override\|lr_effective" tools/evo_runs/e34_identity_cell.py`
- **Constat** : Aucun bras à pas nul ou différent : question sans objet.
- **Preuve** : e34_identity_cell.py:306, :338 ; cible ligne 29
- **Classe** : aucune
- **Verdict** : hors périmètre

## P6

### P6.a — contrôle positif sans écart à S_off
- **Sonde** : python scratchpad/p6_v3_sonde.py ; `grep -rnE "S_pos.*S_off|S_off.*S_pos" tests/ tools/evo_runs/e34_identity_cell.py`
- **Constat** : pos diffère de off par la seule coupe, mais des permutations par deux choses (coupe et absence de permutation). Son no-op exact est S_off, et on ne le confronte qu'à la bande. Si les permutations déplacent seules la survie, le contrôle est déclaré vu sans effet de la coupe (cas A : NON_MATERIEL) et aveugle quand elle agit (cas C : NON_TRANCHE). S_pos − S_off n'est ni calculé, ni publié, ni gardé : le canal de priorité de service relevé en v2 ressort par le contrôle positif.
- **Preuve** : e34_identity_cell.py:266, :219, :229-234 ; (A) S_off 9.0 = S_pos 9.0, bande [6.0, 8.0] → NON_MATERIEL ; (B) 7.0 = 7.0 → NON_TRANCHE ; (C) +2.0 → NON_TRANCHE ; grep : 1 co-occurrence (:218, dict littéral)
- **Classe** : aucune (voisine d'E1 : un contrôle positif qui peut réussir sans son effet)
- **Verdict** : confirmé

### P6.b — position par rapport au no-op
- **Sonde** : `grep -niEc "no.?op" <cible>` ; idem sur CLAUDE.md ; `ls results/e34_identity_cell.json ; git ls-files results/e34_identity_cell.json | wc -l`
- **Constat** : Aucune cellule mesurée ; la position du contraste dans sa bande ne peut pas être dite. Motif validé sur cas positif, rien dans la pré-inscription.
- **Preuve** : cible 0 ; CLAUDE.md 5 ; fichier absent ; git ls-files 0
- **Classe** : aucune
- **Verdict** : hors périmètre (pré-inscription sans résultat)

### P6.c — ratios de la v2
- **Sonde** : `grep -nE "perms_part_erosion|perms_fort|perms_dS" tools/evo_runs/e34_identity_cell.py ; grep -nE "def test_.*noop" tests/sandbox/test_e34_slot_identity.py`
- **Constat** : Les ratios sans plancher de la v2 portent désormais leur équivalent par permutation, et un no-op exact existe en test : P6.a/P6.b de la v2 ne se reproduisent pas.
- **Preuve** : e34_identity_cell.py:231-234 ; test_e34_slot_identity.py:377
- **Classe** : aucune
- **Verdict** : non confirmé

## P7

### P7.a — dose de défaut des témoins
- **Sonde** : python scratchpad/p7_v3_dose_perm.py (combinatoire pure d'immortal_after_step, RandomState(k) réels, aucun monde)
- **Constat** : À chaque changement d'ordre, la permutation privée s'ajoute au décalage de recharge : ~11 tranches changent de corps, contre 12 − p (7 en moyenne) sur le bras éteint ; sur 12 morts, 121 contre 77. Sous H1 la bande représente un défaut 1,56× plus lourd. Un MATERIEL opposerait 0 à ~1,6 N ; les bandeaux sur l'arc P4.4 → P4.16 transporteraient une ampleur qui n'est pas la sienne. Les fractions de dose ne portent que sur le bras éteint ; l'écart de dose n'est ni prédit ni publié.
- **Preuve** : éteint [12, 11, …, 2], moy. 7,0 ; shams 10,92 (9,27–11,91) ; ratio 1,56 ; 77,4 contre 121,1 ; s2_credit_retention.py:190-194, :229 ; e34_identity_cell.py:223-226
- **Classe** : E6
- **Verdict** : confirmé

### P7.b — sens du contrôle positif à la dose t1
- **Sonde** : python -c listant survival_median, td_updates, episode_updates par bras au seed 2026 de results/s2_credit_ablation_2.json
- **Constat** : Avant la coupe, pos a déjà reçu t1 mises à jour. Son sens n'est mesuré qu'aux extrémités (gelé 31,5 ; complet 7,0). Les doses partielles publiées conservent déjà 92 % (TD seul, 9,0) et 82 % (épisodique seul, 11,5) de l'érosion. Si l'érosion s'installe tôt, S_pos reste dans la bande et NON_TRANCHE est l'issue attendue avant mesure. Rien ne publie la dose de coupe à partir de laquelle S_pos sortirait.
- **Preuve** : a_frozen 31,5 ; b_full 7,0 ; b_tdonly 9,0 ; b_eplr 11,5 ; 0,918 et 0,816 ; s2_credit_ablation_2.py:52-54 ; s2_credit_ablation.py:48 ; s2_credit_retention.py:199-201
- **Classe** : E8
- **Verdict** : confirmé

### P7.c — coupe effacée par reconstruction ?
- **Sonde** : `grep -n need_rebuild src/worlds/world_1_stoneage.py` ; lecture de s2_credit_retention.py:107-113 et :152-155
- **Constat** : Non : la reconstruction exige un B différent et la recharge rend douze agents avant chaque pas. La coupe tient.
- **Preuve** : world_1_stoneage.py:1060-1066 ; s2_credit_retention.py:107-113 ; skips {}, episode_updates 250
- **Classe** : aucune
- **Verdict** : non confirmé

## P8 (JUGÉ)

### P8.a — second écrivain dans l'état récurrent (vote social)
- **Sonde** : `grep -n 'batch_logits\[.*\] = \|logits\[.*\] -=' src/worlds/world_1_stoneage.py` ; `grep -ci consensus` sur les trois fichiers E34 ; python scratchpad/p8_probe.py ; python scratchpad/p8_probe2.py (sha 5ac488fb)
- **Constat** : Le texte n'annonce qu'un écrivain (:1340). Or le vote social (:973) remplace la ligne de sorties de chaque agent de la case par une moyenne des logits des votants, écrivant d'un corps dans l'état d'un autre, colonne de valeur (92, nœud 28) comprise, dans les quinze bras. INFRA-001 nomme les deux sites ; ni le runner E34 ni s2_credit_retention ne compte celui-ci, alors que S2-BASSIN-FRAGILITY l'instrumente sur le même bassin. Fréquence inconnue (0/240 hors monde). Dose déclarée complète sans l'être. Remède : compter_consensus sur les quinze cellules, publier ticks_avec_reecriture par bras.
- **Preuve** : world_1_stoneage.py:973, :1340 ; INFRA-001:21-22 ; grep consensus 0/0/0 ; s2_bassin_fragility.py:239 ; shares_memory=True, lignes [0, 2], colonne 92 modifiée ; 0/240 ; cible ligne 10
- **Classe** : E5
- **Verdict** : confirmé

### P8.b — plafond mécanique de famine
- **Sonde** : python scratchpad/p8_probe.py ; python -c lisant results/s2_credit_retention.json (regime, b_warm_credit.2026.survival)
- **Constat** : Corps lu dans W[0:10] : bonus PV 688,8, capacité 70, drain 14,888 ; avec métabolisme 0,75, 11,17 d'énergie par tick, extinction vers 7,2 ticks depuis 80. S_off = 7,0, quatre âges sur douze valent 7 : l'agent médian meurt à l'âge de famine. La section plancher ne nomme pas ce plafond fixé par W. MATERIEL_BAISSE ne peut venir que de morts avant famine : lecture de fait unilatérale. Publier 80 / (base_metabolism × drain) à côté de S_off.
- **Preuve** : mamba_agent.py:77-80 ; world_1_stoneage.py:702 ; phénotypes {(688.83, 70, 14.888)} ; 80/(0.75 × 14.888) = 7.164 ; âges [5,6,6,7,7,7,7,8,8,9,9,11]
- **Classe** : E3
- **Verdict** : confirmé

### P8.c — l'intervention réécrit-elle le corps ?
- **Sonde** : `grep -rn update_phenotype src/ tools/evo_runs/s2_credit_retention.py tools/evo_runs/e34_identity_cell.py` ; python scratchpad/p8_probe.py
- **Constat** : Non : aucun traitement ne recalcule le phénotype ; mêmes objets en phase 2 ; les quinze bras ont le même corps.
- **Preuve** : mamba_agent.py:140,152,177,198 ; world_1_stoneage.py:990, :375 ; s2_credit_retention.py:276-285 ; 1 seul triplet
- **Classe** : E26
- **Verdict** : non confirmé

### P8.d — chevauchement entrée/sortie
- **Sonde** : python tools/check_io_overlap.py ; python scratchpad/p8_probe.py
- **Constat** : Pas de recouvrement (5 nœuds de marge) ; load_bassin le refuse ; porte 17 sans nouveau ni aggravé.
- **Preuve** : 358 génomes, 10 chevauchants connus, 0 nouveau, EXIT=0 ; I,O,N = 59,108,172 ; s2_credit_retention.py:61
- **Classe** : E24
- **Verdict** : non confirmé

## P9 (DÉLÉGUÉ)

### P9.a — provenance, porte 20
- **Sonde** : `python tools/check_evidence_provenance.py --only <cible> ; echo exit=$?`
- **Constat** : La porte 20 ne juge que docs/EDR/*.md ; refus avant analyse. Verdict recopié : REFUS, code 2. Aucune provenance rendue sur s2_credit_retention.json ni s2_credit_ablation_2.json.
- **Preuve** : « REFUS : --only designe 1 chemin(s) INCONNU(S) de cette porte » ; exit=2 (HEAD 5ac488fb)
- **Classe** : aucune
- **Verdict** : hors périmètre

### P9.b — sceau (tools.preregister.verify)
- **Sonde** : `python -c "from tools.preregister import verify; verify('E34-IDENTITY-CELL')"; echo exit=$?` ; `ls docs/preregistrations | grep -ic e34` ; contrôle positif verify('S2-BASSIN-FRAGILITY')
- **Constat** : Sceau absent, état attendu pour une v3 en revue (scellée après revue avec reviewed_by). Le runner appelle verify avant tout run non-smoke : aucune cellule ne peut tourner sans sceau.
- **Preuve** : FileNotFoundError à preregister.py:196, exit=1 ; 0 fichier e34 ; contrôle positif 17 clés, exit=0 ; e34_identity_cell.py:39, :322, :427
- **Classe** : aucune
- **Verdict** : hors périmètre

## P10

### P10.a — consensus social hors dose
- **Sonde** : python scratchpad/p10_sonde_vue.py ; `sed -n '962,975p;1260,1270p' src/worlds/world_1_stoneage.py` ; `grep -n 'CONDITION_GATE\s*=\|^_VALUE_NODE' src/agents/backend_torch.py` ; grep consensus dans les deux results cités
- **Constat** : Le consensus remplace la ligne ENTIÈRE de logits (V(s') comprise, index 28) des corps d'une même case ; écriture inter-corps indépendante de l'ordre des tranches, que le drapeau ne peut couper. Le paragraphe dose ne compte que :1340 ; la partition « croisé = coupé / non croisé = commun » est fausse. Après t1, pos ne consomme plus V(s') : exposition inégale entre bras. Activité non mesurée dans cette cellule.
- **Preuve** : world_1_stoneage.py:973, :1269 ; backend_torch.py:48, :202-203, :200, :210, :35, :220 ; H[1, sortie 5] 0.8844 → 7.0, shares_memory True ; N,I,O = 172, 59, 108 ; grep consensus 0 ligne
- **Classe** : E5
- **Verdict** : confirmé — le mécanisme est lu et rejoué sur tenseur ; sa fréquence dans la cellule n'est pas mesurée

### P10.b — sha du code scellé
- **Sonde** : `git show f1d6a987:tools/evo_runs/s2_credit_retention.py | grep -c sham_perm` (et cut_credit_at_t1) ; idem à HEAD ; `git diff --stat f1d6a987 5ac488fb`
- **Constat** : f1d6a987 ne contient aucun instrument v3 (sham de permutation, coupe, perm_k) ; le runner v3 n'existe qu'à partir de 5ac488fb. Les lignes citées tiennent, mais « lancer au sha du sceau » ne peut pas désigner f1d6a987.
- **Preuve** : sham_perm 0 contre 14 ; cut_credit_at_t1 0 contre 11 ; runner e34 à f1d6a987 : 0 ; diff touche e34_identity_cell.py (+380) et s2_credit_retention.py (91 lignes), pas src/
- **Classe** : aucune
- **Verdict** : confirmé

### P10.c — ticks de traitement après t1
- **Sonde** : `sed -n '180,236p' tools/evo_runs/s2_credit_retention.py ; grep -n 'perm_events\|ticks_reordered\|first_perm_tick\|first_reorder_tick' tools/evo_runs/e34_identity_cell.py`
- **Constat** : Les permutations coïncident avec le correctif qu'à t1 ; ensuite chaque bras agit sur ses propres changements d'ordre, sur une trajectoire divergée. Le lecteur ne contrôle que le PREMIER événement ; perm_events/ticks_reordered ne sont confrontés nulle part. Le commentaire « exactement les ticks » est faux après t1.
- **Preuve** : s2_credit_retention.py:186, :182, :236, :130 ; e34_identity_cell.py:240, :245 ; 0 ligne perm_events/ticks_reordered
- **Classe** : aucune
- **Verdict** : confirmé

### P10.d — morts simultanées
- **Sonde** : python scratchpad/p10_sonde_suffixe.py (vraie immortal_refill sur listes-talons)
- **Constat** : Plusieurs morts au même tick ne désalignent pas B − p tranches (en queue : 0 ; non contiguës : moins). Le lecteur mesure l'ordre réel : verdict non faussé, borne de 144 tient. La prose de t1 et de la dose décrit mal le mécanisme.
- **Preuve** : B=12, morts [10, 11] : 0 contre 2 ; B=4, morts [1, 3] : 2 contre 3 ; B=12, mort [0] : 12
- **Classe** : aucune
- **Verdict** : confirmé — impact faible, porte sur la prose et non sur le lecteur

### P10.e — absence de tirage des traitements
- **Sonde** : `grep -c 'get_rng_state\|np.random.random() == ' tests/sandbox/test_e34_slot_identity.py ; grep -n 'random\|randn\|multinomial' src/agents/backend_torch.py tools/slot_identity.py`
- **Constat** : Le test cité ne vérifie les états RNG que pour le sham de permutation ; à la lecture, ni restore_slot_order, ni _cut_credit, ni learn/learn_episode ne tirent. Affirmation vraie, vérification citée partielle.
- **Preuve** : 3 lignes (test 203-233) ; backend_torch.py:137-139 seuls tirages ; slot_identity.py 0 ; s2_credit_retention.py:152-155
- **Classe** : E4
- **Verdict** : non confirmé — le mécanisme tient

### P10.f — références relues
- **Sonde** : grep -n à f1d6a987, 14f9a3da, fe12f42d (git show) ; python chargeant les deux results ; `sed -n '58,68p' tools/grid_compare.py ; sed -n '160,176p' tools/learning_events.py`
- **Constat** : Ancres de ligne aux deux commits, décalage dans d1, valeurs du témoin, S_a, dispersion, k = 8, comparaison stricte sur la grille et source du pas publié : tout tient.
- **Preuve** : FLOOR :45 ; append :111 ; need_rebuild :1060 ; pénalité :1340 ; stack :109, write-back :512 (127 et 608 à fe12f42d) ; 1999 / 12 / 18242.03954219818 ; a_frozen 31.5 ; b_full 7.0–9.5 ; torch_episode_k = 8 ; grid_compare.py:68 ; learning_events.py:174
- **Classe** : aucune
- **Verdict** : non confirmé — aucune divergence
