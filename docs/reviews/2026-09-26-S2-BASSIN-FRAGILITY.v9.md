# Revue adversariale — S2-BASSIN-FRAGILITY (pré-inscription v9)

- **Cible** : `C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/S2-BASSIN-FRAGILITY.v9.json` (kind : pré-inscription, relue AVANT scellement)
- **Date** : 2026-09-26
- **SHA** : `836117ce5a40d279ce02a5e40fe52fbf2e00aed7` (worktree science-prep)

## Témoins

| témoin | statut | code | critiques recevables | commande |
|---|---|---|---|---|
| S2-BLIND-CHAMPION-42e9357 | RETROUVE | 0 | 9 | `PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier S2-BLIND-CHAMPION-42e9357 <scratchpad>/refutateur_v9/critiques-S2-BLIND-CHAMPION-42e9357.json --extrait <scratchpad>/temoins/temoin-1.md --jugement OUI` |
| LOCK-002-286f244 (cru sain) | MESURE | 0 | 7 | `PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier LOCK-002-286f244 <scratchpad>/refutateur_v9/critiques-LOCK-002-286f244.json --extrait <scratchpad>/temoins/temoin-2.md` |
| EDR-GRAB-COST-1828371 | RETROUVE | 0 | 8 | `PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier EDR-GRAB-COST-1828371 <scratchpad>/refutateur_v9/critiques-EDR-GRAB-COST-1828371.json --extrait <scratchpad>/temoins/temoin-3.md --jugement OUI` |
| EDR-RETAIN-COMPOSE-4204f8f | RETROUVE | 0 | 6 | `PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier EDR-RETAIN-COMPOSE-4204f8f <scratchpad>/refutateur_v9/critiques-EDR-RETAIN-COMPOSE-4204f8f.json --extrait <scratchpad>/temoins/temoin-4.md --jugement OUI` |

(`<scratchpad>` = `C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad`)

**Score : 3/3 défauts connus RETROUVÉS** — PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 — plancher mesure sur LOCK-002-286f244 : 7 critiques recevables (seuil historique 1) [S n'est pas imprimé par --verifier : lu dans le champ seuil_critiques du roster tools/refutateur_temoins.json, le même que celui qu'utilise le script (refutateur_temoins.py:504)]

⚠ INDISCRIMINANT : le record cru sain rend autant de critiques recevables que les defectueux

**Critiques confirmées : 13** (P1 : 1, P5 : 3, P6 : 3, P7 : 1, P10 : 5).

---

## P1

### P1.a — provenance de la référence de b_full
- **Sonde** : `python -c "import json;d1=json.load(open('results/s2_credit_ablation.json'));d2=json.load(open('results/s2_credit_ablation_2.json'));d4=json.load(open('results/s2_credit_retention.json'));S=[str(s) for s in range(2026,2038)];print(sum(bool(d2['arms']['b_full'][s].get('imported_from')) for s in S),sum(bool(d1['arms']['b_full'][s].get('imported_from')) for s in S),d2['arms']['b_full']['2027']['imported_from'],sum(d1['arms']['b_full'][s]['learning']['dW_abs_sum']==d4['arms']['b_warm_credit'][s]['learning']['dW_abs_sum'] and d1['arms']['b_full'][s]['survival']['ages']==d4['arms']['b_warm_credit'][s]['survival']['ages'] for s in S),d4['provenance'])"`
- **Constat** : La branche 4 exige que le rejeu de b_full égale au bit une référence publiée sur douze seeds ; la règle situe cette référence chez P4.9 (arbre 9de2b3b) pour onze d'entre eux. Les JSON disent autre chose : sur 2027-2037, P4.16 comme P4.9 portent imported_from = s2_credit_retention.json, et leurs chemins et âges coïncident au bit avec b_warm_credit de P4.4, calculé sur l'arbre 05cf8888, lui aussi dirty. Aucun des deux runners n'a donc calculé b_full ailleurs qu'en 2026, et le docstring du runner de P4.16 le dit déjà. La provenance de la référence que doit reproduire le rejeu a été déduite, pas lue dans le champ publié : l'arbre sale à reproduire n'est pas celui que la règle nomme. Si le code de 05cf8888 diverge du code actuel, le run sort INDETERMINE_REPLICATION.
- **Preuve** : P4.16 a 11/12 seeds importés et P4.9 11/12, imported_from = results\s2_credit_retention.json ; égalité chemin+âges avec P4.4 b_warm_credit 12/12 ; P4.4 provenance {git_sha 05cf8888, dirty True}. Selon la règle (v9.json:27, champ mesure), la source est P4.9 9de2b3b. Or tools/evo_runs/s2_credit_ablation_2.py:13 dit : b_full importé de P4.4.
- **Classe** : E8
- **Verdict** : confirmé

### P1.b — prémisses de famille et de lisibilité E19
- **Sonde** : `python p1_sonde.py` (scratchpad) : charge les trois JSON publiés, reclasse les greffes contre a_frozen (seuils 11/12 et 5 ticks) et recalcule la saturation avec S_c de P4.4 c_cold_credit
- **Constat** : Pour les autres prémisses qui fixent la famille et la lisibilité E19, la sonde a vérifié qu'elles sont publiées et rejouées au bit, sans rien d'hérité de caché. Cinq greffes ÉRODENT et b_zero est NEUTRE, d'où les 15 cellules. b_const et b_eplr ont 11/12 exactement, avec l'égalité au seed 2036 comme la règle l'annonce. b_tdoff est saturé sur 12/12 seeds. S_c vient bien de P4.4, et c'est déclaré.
- **Preuve** : S_a médiane 36,0 (17-50). Greffes, avec (nombre de seeds < 0, médiane) : full ERODE (12, -28,25) ; tdonly (12, -27,75) ; const (11, -12,25) ; eplr (11, -19,0) ; tdoff (12, -29,0) ; zero NEUTRE (8, -0,75). Saturation de b_tdoff : 12/12 >= 0,9, min 0,946, médiane 1,017. Spearman inter-bras 0,943 retrouvé.
- **Classe** : aucune
- **Verdict** : non confirmé

## P2 (DÉLÉGUÉ) — Régime
- **Sonde** : `python tools/check_regime_claims.py --only <cible v9> ; echo EXIT=$?` (puis Glob `docs/EDR/*BASSIN*`)
- **Constat** : La porte 19 ne sait juger que des records Markdown sous docs/EDR ; une pre-inscription JSON posee dans le scratchpad lui est etrangere, elle la rejette avant analyse. Aucun verdict de regime n'est donc rendu sur cette regle, et aucun record EDR portant le motif BASSIN n'existe encore a qui l'appliquer.
- **Preuve** : sortie de la porte : REFUS, 1 chemin INCONNU (ni record docs/EDR/<nom>.md present, ni record supprime), EXIT=2 ; Glob docs/EDR/*BASSIN* = 0 fichier ; filtre defini tools/check_regime_claims.py:461
- **Classe** : aucune
- **Verdict** : hors périmètre

## P3 (DÉLÉGUÉ) — balayage du pas, garde E19 appelée par le runner scellé
- **Sonde** : `cd .worktrees/science-prep (HEAD 836117ce) && python tools/check_e19_optimizer_sweep.py --only tools/evo_runs/s2_bassin_fragility.py ; echo EXIT=$? ; ls docs/preregistrations/S2-BASSIN-FRAGILITY.json ; git ls-files docs/preregistrations | grep -c -i bassin`
- **Constat** : La porte 23 rend OK (exit 0) : le runner P4.18 invoque lui-même la garde d'invariance à l'optimiseur, donc aucun nul comparatif sous gradient n'échappe au balayage du pas. Elle le range néanmoins en regle_absente, rang 3, faute de pouvoir joindre le runner à une règle scellée dans le dépôt : la v9 relue ne vit que dans le scratchpad. C'est une limite de l'analyse de la porte, pas un défaut E19. Le sceau relève de P9, et savoir si la référence à pas nul sort du même dispositif relève de P5.
- **Preuve** : Sortie de la porte : 'runners scellés : 34 | sous gradient (PLANCHER) : 12 | nus (PLANCHER) : 9 | indéterminés : 4 | non résolus : 6 | règle absente : 1 | illisibles : 0 | appelants de la garde : 3 | gelés : 19' ; ligne NOUVEAU '[regle_absente] tools/evo_runs/s2_bassin_fragility.py : appelle assert_verdict_invariant_to_optimizer(...) directement' ; 'OK : aucun nouveau runner sous gradient sans garde E19' ; EXIT=0. Règle attendue par le runner (tools/evo_runs/s2_bassin_fragility.py:41, PREREG ligne 65) : ls rend 'No such file or directory', git ls-files compte 0.
- **Classe** : aucune
- **Verdict** : non confirmé — verdict de la porte recopié : garde E19 appelée directement, OK exit 0. Le statut regle_absente (règle non scellée dans le dépôt) est hors du périmètre de P3 et relève de P9.

## P4 (JUGÉ)

### P4.a — taille réelle de la famille
- **Sonde** : `python scratchpad/p4_probe.py` (qui charge published() et _classer du runner sur les JSON P4.16/P4.9)
- **Constat** : J'ai compté à la lecture de fragility_verdict les tests de signe 11/12 qui peuvent changer une étiquette. Chaque bras en consulte au plus deux : sa classe de tirage face au no-op, puis un seul contraste (MOINS si la greffe érode, PLUS si elle est neutre, aucun si elle étend). S'y ajoutent trois contrôles (pos, eps face au no-op, eps face à la greffe complète). Avec les classes de greffe publiées (cinq qui érodent, b_zero neutre), le total fait 6+6+3 = 15, soit exactement le nombre déclaré. Aucune configuration des greffes ne peut le dépasser.
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:678-688 (_lecture_bras : moins lu seulement pour ERODE, plus seulement pour NEUTRE) et :826-857. Sortie de la sonde : full ERODE 12/12, tdonly 12/12, const 11/12, eplr 11/12, tdoff 12/12, zero NEUTRE 8/12, puis « 6 ; + 6 classes sign + 3 controles = 15 ». FAMILLE = 15 (:85).
- **Classe** : E23
- **Verdict** : non confirmé

### P4.b — le seuil de signe tient-il à cette famille ?
- **Sonde** : `python scratchpad/p4_probe.py` (seuil_tient pour 15 et 16, verifier_seuils sur la v9)
- **Constat** : Le seuil de signe tient pour 15 cellules et casse dès la seizième. La marge est donc d'une seule cellule, ce que la règle déclare déjà. Le runner impose ce lien au moment du verdict et confronte au bit ses seuils à ceux de la v9.
- **Preuve** : Sortie : seuil_tient 15 → (True, 0.003174, 0.003333) ; 16 → (False, 0.003174, 0.003125) ; verifier_seuils(v9) : True. Voir s2_bassin_fragility.py:755-758.
- **Classe** : E23
- **Verdict** : non confirmé

### P4.c — le seuil est-il hérité d'un autre dispositif ?
- **Sonde** : `python -c` qui calcule la médiane de S_tr par bras depuis published() ; `grep -n DELTA_MIN/SIGN_MIN tools/evo_runs/s2_credit_retention.py` ; lecture de verdict.thresholds dans results/s2_credit_ablation{,_2}.json
- **Constat** : delta_min = 5 vient de P4.4. Là-bas, il valait environ 14 % d'une référence de 36 ticks. Ici, il s'applique à un contraste dont la référence, pour les trois bras au plancher, est de 7,5 à 8,5 ticks. Il y pèse donc 59 à 67 % de cette référence. La note sur les seuils déclare « ≈60-67 % » : le chiffre est exact. Quant au seuil 11/12, il n'est pas repris de P4.9/P4.16, qui utilisaient 10/12 : il est dérivé de la famille de 15.
- **Preuve** : s2_credit_retention.py:48-49 (SIGN_MIN 10, DELTA_MIN 5.0). Médianes de S_tr : full 8,0 (0,625), tdonly 8,5 (0,588), tdoff 7,5 (0,667), contre 5/36 = 0,139. Les deux JSON publiés portent sign_min 10.
- **Classe** : aucune
- **Verdict** : non confirmé

### P4.d — nombre de cellules et de conditions du dispositif
- **Sonde** : `python scratchpad/p4_probe2.py` (run_fragility_seed avec _replay/_phase2 factices qui comptent les appels)
- **Constat** : J'ai compté par injection d'un monde factice, sans aucune simulation réelle. Chaque seed exécute bien 167 phases 2 (un no-op, 26 conditions par bras, cinq tirages pour chaque contrôle), et le rejeu couvre 6 bras × 12 seeds = 72 cellules. Le plafond de coût repose donc sur le bon compte.
- **Preuve** : Sortie : « phases 2 par seed (6 bras, R=5): 167 ; declare plafond: 167 » et « 6 x 12 = 72 ». Voir s2_bassin_fragility.py:496-540.
- **Classe** : aucune
- **Verdict** : non confirmé

### P4.e — seuil de fermeture E19 (2/3)
- **Sonde** : `grep -n 'max_gap_closure *=' tools/experiment_preflight.py`
- **Constat** : Le seuil de fermeture de la garde E19 n'est pas dérivé pour ce dispositif : c'est la valeur par défaut de la garde, et la règle le dit. Ce seuil ne décide rien ici, parce que la garde est illisible dès que b_tdoff est saturé.
- **Preuve** : tools/experiment_preflight.py:303 max_gap_closure=2.0/3.0, contre E19_CLOSURE_MAX = 2.0/3.0 dans s2_bassin_fragility.py:84
- **Classe** : E19
- **Verdict** : non confirmé

### P4.f — sonde d'entrée : porte 11 (check_control_family)
- **Sonde** : `python tools/check_control_family.py --only tools/evo_runs/s2_bassin_fragility.py ; ls docs/preregistrations | grep -ci fragil`
- **Constat** : La porte 11 répond OK pour ce runner, mais cet OK ne dit rien. Tant qu'aucun fichier de préinscription ne porte ce nom, le runner n'entre pas dans le périmètre des runners scellés. La porte n'a donc rien vérifié sur la cible. C'est normal avant le sceau ; son verdict ne pourra être recopié qu'après.
- **Preuve** : Sortie : « runners scellés : 32 | sans design : 0 », OK, exit=0 ; le grep rend 0. Le runner reste A (stagé, non committé) selon git status.
- **Classe** : aucune
- **Verdict** : hors périmètre

## P5

### P5.a — référence du contrôle de direction
- **Sonde** : `python -c "import json;from collections import Counter;d=json.load(open('results/s2_credit_ablation_2.json',encoding='utf-8'));e=json.load(open('results/s2_credit_ablation.json',encoding='utf-8'));f=json.load(open('results/s2_credit_retention.json',encoding='utf-8'));S=[str(s) for s in range(2026,2038)];print(Counter(str(d['arms']['b_full'][s].get('imported_from')) for s in S),Counter(str(e['arms']['b_full'][s].get('imported_from')) for s in S),f.get('git'),d['arms']['b_full']['2026']['learning']['dW_abs_sum'],f['arms']['b_warm_credit']['2026']['learning']['dW_abs_sum'])"`
- **Constat** : Le contrôle positif de DIRECTION (eps, tiré sur le ΔW de b_full) et la prémisse de la branche 8 reposent tous deux sur b_full. Sur 11 seeds sur 12, sa référence publiée n'a été calculée ni par P4.16 ni par P4.9 : les deux fichiers renvoient vers s2_credit_retention.json, c'est-à-dire le runner de P4.4 (sha 05cf8888, arbre sale). La règle attribue ces données à P4.9 et cite le sha 9de2b3b : elle se trompe donc de dispositif pour la référence du contrôle. Un point atténue le défaut, et la règle ne le cite pas : au seed 2026, le recalcul fait par P4.16 retombe au bit sur P4.4. C'est déjà un témoin entre runners.
- **Preuve** : imported_from = results\s2_credit_retention.json sur 11/12 seeds dans P4.16 comme dans P4.9 (None au seed 2026 seulement) ; P4.4 : git_sha 05cf8888, dirty True ; seed 2026 : dW_abs_sum 18242.0395 dans P4.16 = 18242.0395 dans P4.4, âges égaux sur 12/12. La règle v9, S2-BASSIN-FRAGILITY.v9.json:27, écrit « IMPORTÉ de P4.9 » avec le sha 9de2b3b.
- **Classe** : E8
- **Verdict** : confirmé

### P5.b — branche 8 incapable d'échouer
- **Sonde** : `python -c "import json,numpy as np;d=json.load(open('results/s2_credit_ablation_2.json',encoding='utf-8'));S=[str(s) for s in range(2026,2038)];x=[d['arms']['b_full'][s]['survival']['survival_median']-d['arms']['a_frozen'][s]['survival']['survival_median'] for s in S];print(sum(v<0 for v in x),np.median(x),max(x))"`
- **Constat** : La branche 8 ne peut plus rendre INDETERMINE_PREMISSE une fois les branches 2, 4 et 5 passées. La 2 fixe S_a au no-op publié. Les 4 et 5 fixent S_tr_full aux âges publiés de b_full. Or ces âges sont sous le no-op sur les douze seeds. La règle déclare la branche 3 inerte pour cette même raison, mais présente la branche 8 comme un contrôle actif, qui pourrait échouer. C'est un contrôle incapable d'échouer : il faut le déclarer comme la branche 3.
- **Preuve** : Écarts S_tr_full − S_a : négatifs sur 12/12, médiane −28.25, plus petit en valeur absolue −9.0, donc classe ERODE fixée d'avance (runner s2_bassin_fragility.py:973). Règle v9 : ligne :14 (branche 3, déclarée jouée d'avance) contre ligne :19 (branche 8, sans déclaration équivalente).
- **Classe** : E1
- **Verdict** : confirmé

### P5.c — condition d'échec de 9b mal énoncée
- **Sonde** : `python -c "import json;d=json.load(open('results/s2_credit_ablation_2.json',encoding='utf-8'));S=[str(s) for s in range(2026,2038)];print(sorted(d['arms']['a_frozen'][s]['survival']['survival_median']-d['arms']['b_full'][s]['survival']['survival_median'] for s in S))"` ; Read tools/evo_runs/s2_bassin_fragility.py:783
- **Constat** : La règle donne une condition d'échec de 9b trop forte : une perte d'eps au-delà de 17 ticks sur deux seeds. Or le compte des contrastes positifs est strict, et les deux plus petits écarts de la branche 8 valent 9,0 (seed 2036, S_a 17) et 17,0 (seed 2037). Il suffit donc qu'eps coûte 9 ticks au premier seed et 17 au second pour que 9b tombe à 10/12 et échoue. Le « seulement si » de la règle est faux. La conclusion reste juste (contrôle de DIRECTION non éprouvé), mais la zone d'échec est plus large que ce qui est écrit.
- **Preuve** : Écarts triés [9.0, 17.0, 24.5, 27.5, 28.0, ...] ; s2_bassin_fragility.py:783 compte « x > 0 » (strict), donc c = 0 n'est pas compté positif ; règle v9 :21 : seuil énoncé à 17 ticks sur les deux seeds, alors qu'il vaut 9 sur l'un.
- **Classe** : aucune
- **Verdict** : confirmé

### P5.d — la paire E19 mélange-t-elle deux dispositifs ?
- **Sonde** : `python -c "import json;d=json.load(open('results/s2_credit_ablation_2.json',encoding='utf-8'));e=json.load(open('results/s2_credit_ablation.json',encoding='utf-8'));S=[str(s) for s in range(2026,2038)];print(sum(d['arms']['a_frozen'][s]['survival']['ages']==e['arms']['a_frozen'][s]['survival']['ages'] for s in S),[k for k in d['regime'] if d['regime'][k]!=e['regime'].get(k)])"`
- **Constat** : Question : la paire E19 mélange-t-elle deux dispositifs ? b_tdoff est publié par P4.9, b_eplr par P4.16. Réponse : non. Les deux fichiers ont le même no-op, au bit, sur tous les seeds, et leurs blocs de régime ne diffèrent que par la liste des bras. La paire ne varie que par le pas (runner :73-74). Aucun défaut.
- **Preuve** : a_frozen identique 12/12 ; seule clé de régime différente : arms_credit ; ARM_CREDIT b_eplr et b_tdoff (s2_bassin_fragility.py:73-74) ne diffèrent que par lr.
- **Classe** : aucune
- **Verdict** : non confirmé

### P5.e — greffon sans effet (contraste tautologique)
- **Sonde** : `grep -n "assert_positive_control\|assert_not_degenerate\|assert_ablation_changes_something" tools/evo_runs/s2_bassin_fragility.py` ; `python -c` comparant les âges publiés de b_zero, b_eplr et b_const à ceux de a_frozen, seed par seed
- **Constat** : Le runner n'appelle ni assert_positive_control ni assert_ablation_changes_something : les contrôles sont codés à la main (pos en :967, 9b en :982). J'ai vérifié le risque d'un greffon sans aucun effet sur le comportement, donc d'un contraste tautologique. Aucun bras à petit ΔW ne reproduit les âges du no-op au bit, sur aucun seed. Aucun défaut.
- **Preuve** : grep : 0 appel aux deux premières gardes, assert_not_degenerate aux lignes :841 et :944 ; âges égaux à a_frozen : b_zero 0/12, b_eplr 0/12, b_const 0/12.
- **Classe** : aucune
- **Verdict** : non confirmé

## P6

### P6.a — couverture de la bande tenue par la graine du témoin
- **Sonde** : `python <scratchpad>/p6_temoin_couverture.py` (rejoue _couverture_du_nul_echangeable de tests/sandbox/test_s2_bassin_fragility.py, reps=150, graines 1..20 en plus de 7 ; sans monde)
- **Constat** : La couverture >= 0,95 de la bande sous le nul échangeable n'est établie par le témoin gelé que grâce à sa graine. À 150 répétitions, l'erreur Monte-Carlo (0,0175) vaut près de neuf fois la marge réelle mesurée à 1000 répétitions (0,952 - 0,95), et le même témoin échoue sur à peu près une graine sur deux. Le côté refus discrimine (contre-exemple v6), le côté acceptation ne discrimine pas : le plancher de bruit de l'instrument qui mesure le plancher de bruit n'est ni publié ni tenu.
- **Preuve** : tests/sandbox/test_s2_bassin_fragility.py:566 (assert >= 0.95, reps=150, seed=7). Sortie : seed 7 = 0,980 aux deux sigma ; sur 20 autres graines, 7/20 (sigma=2) et 9/20 (sigma=4) sous 0,95, min 0,927. v6 : 0/20 au-dessus de 0,93. results/s2_bassin_fragility_calibration_bande.json : echangeable_sigma_2.0 homogene 0,952, erreur_mc 0,0068. Cible ligne 30 (2bis) : présente ce témoin comme garantie de couverture.
- **Classe** : E9
- **Verdict** : confirmé

### P6.b — non-monotonie const/eplr dans le bruit
- **Sonde** : `python -c "import json,numpy as np; d=json.load(open('results/s2_credit_ablation_2.json',encoding='utf-8'))['rows']; Sa=np.array([r['S_a'] for r in d]); c=np.array([r['S_const'] for r in d])-Sa; e=np.array([r['S_eplr'] for r in d])-Sa; ...bootstrap 10000 sur les graines"`
- **Constat** : Pour affirmer que l'érosion ne suit pas l'amplitude nette, la règle oppose b_const et b_eplr. Or l'écart apparié de leurs érosions reste dans le bruit inter-graines, et l'amplitude nette n'a été mesurée que sur une graine. Le facteur 1,55 est publié sans plancher, alors que son IC couvre 1. La prudence qui en découle (11c classé hypothèse) reste saine ; en revanche, le constat de non-monotonie donné comme mesuré ne l'est pas.
- **Preuve** : Sortie : médianes -12,25 / -19,0 (rapport 1,551) ; différence const-eplr par graine = [9.5,1.5,1,-3.5,9.5,8.5,-8.5,-3.5,27,17,10.5,-1.5] -> 8 positifs contre 4, signe bilatéral p = 0,388 ; IC95 bootstrap du rapport [0,85 ; 1,95], P(rapport <= 1) = 0,091 ; IC95 de la médiane des différences [-2,5 ; 10]. Cible lignes 3 et 29 (non-monotonie affirmée), ligne 30 (net au seul seed 2026).
- **Classe** : E9
- **Verdict** : confirmé

### P6.c — étalon de bruit emprunté (3,84 ticks)
- **Sonde** : `python -c "import json,numpy as np; d=json.load(open('results/s2_credit_ablation.json',encoding='utf-8'))['rows']; Sa=np.array([x['S_a'] for x in d]); z=np.array([x['S_zero'] for x in d])-Sa; print(z.tolist(), z.std(ddof=1), (z<=-5).sum(), (abs(z)<=2).sum())"`
- **Constat** : Comme étalon du bruit d'une réalisation unique, la règle prend l'écart-type de 3,84 ticks, calculé sur la dispersion inter-graines de l'effet d'un autre bras appris (b_zero). Cette distribution est bimodale : c'est un effet présent sur certaines graines seulement, pas le no-op de ce contraste. Le plancher propre au pipeline (tirages eps) n'est pas mesuré avant le sceau. Deux phrases placent pourtant une marge « sous le bruit » : la marge de saturation et celle du seed 2035 de b_const. Elles reposent sur cet étalon emprunté.
- **Preuve** : Sortie : [0.5,-5,-7,-7.5,-0.5,-8.5,-0.5,0,2,-7.5,0,-1], sd 3,84 ; 5/12 graines <= -5, 7/12 dans +-2, aucune entre -5 et -1. Cible ligne 54 (seuils_note, 3,84 donné pour une réalisation unique) et ligne 7 (marge de 2,5 ticks du seed 2035 jugée sous le bruit d'après b_zero) ; ligne 30 : aucune survie eps mesurée avant le sceau.
- **Classe** : E8
- **Verdict** : confirmé

### P6.d — chiffres de couverture et de puissance confrontés au JSON
- **Sonde** : `cat results/s2_bassin_fragility_calibration_bande.json ; grep -niE 'no.?op|_bande_contraste\(|dans_la_bande' tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : J'ai confronté au JSON de calibration les chiffres de couverture et de puissance publiés par la règle : ils concordent. Le no-op des shams est bien celui de ces contrastes, puisqu'il passe par la même fonction de phase 2, avec delta nul et monde réensemencé. Le drapeau de bande est calculé pour chaque contraste lu, et il est dit même lorsque le contraste tombe dedans.
- **Preuve** : JSON : échangeable homogène 0,952-0,993, hétérogène 0,926-0,983, exacte >= 0,997 ; puissance 1,0 / 0,808 / 0,997 / 0,674 — identiques aux lignes 7 et 54 de la cible. tools/evo_runs/s2_bassin_fragility.py:496 (noop = phase2(apply_delta(W0, zero))), :794, :799, :838-839, :874 (bande par contraste) ; s2_credit_retention.py:70 (seed_at à chaque monde).
- **Classe** : aucune
- **Verdict** : non confirmé

### P6.e — JSON dits suivis mais seulement stagés
- **Sonde** : `git cat-file -e HEAD:results/s2_bassin_fragility_calibration_bande.json ; git cat-file -e HEAD:results/s2_bassin_fragility_sonde_conception.json ; git ls-files --stage`
- **Constat** : La règle dit suivis les deux JSON qui portent la calibration de la bande et la sonde de conception. Ils sont seulement stagés : HEAD ne les contient pas. Cela touche à la provenance (P9, délégué à la porte 20), pas au plancher de bruit.
- **Preuve** : Sortie : les deux ABSENTS de HEAD 836117ce, présents dans l'index (blobs 53e097d1, bf903dea). Cible lignes 7 et 30 (« suivi »).
- **Classe** : E27
- **Verdict** : hors périmètre

## P7 (JUGÉ) — Dose

### P7.1 — d'où vient la dose de référence de b_full
- **Sonde** : `python -c "import json;d16=json.load(open('results/s2_credit_ablation_2.json',encoding='utf-8'));d9=json.load(open('results/s2_credit_ablation.json',encoding='utf-8'));d4=json.load(open('results/s2_credit_retention.json',encoding='utf-8'));print([d16['arms']['b_full'][str(s)].get('imported_from') for s in range(2026,2038)]);print(set(str(d9['arms']['b_full'][str(s)].get('imported_from')) for s in range(2026,2038)));print(d4['provenance']['git_sha'],d4['provenance']['dirty']);print(sum(d4['arms']['b_warm_credit'][str(s)]['learning']['dW_abs_sum']==d16['arms']['b_full'][str(s)]['learning']['dW_abs_sum'] and d4['arms']['b_warm_credit'][str(s)]['survival']['ages']==d16['arms']['b_full'][str(s)]['survival']['ages'] for s in range(2026,2038)))"`
- **Constat** : La règle fait venir de P4.9 les onze seeds importés de b_full et cite les commits de P4.9 et de P4.16. Ce n'est pas ce que disent les lignes publiées : de 2027 à 2037, P4.16 déclare les avoir importés de s2_credit_retention.json, c'est-à-dire de P4.4 (commit 05cf8888, arbre sale), et P4.9 les tire du même fichier. La dose attendue par la branche 4 sur ces onze seeds (chemin, mises à jour, résurrections) a donc été mesurée par le runner de P4.4. Autre fait que la règle ne cite pas : P4.4 et P4.16 concordent au bit sur 12/12 seeds, y compris 2026, que P4.16 a recalculé. Deux runners se sont donc déjà répliqués l'un l'autre sur ce seed. Rien ne change dans une branche, puisque la branche 4 exige l'identité sur tout. C'est une erreur de provenance, qui relève de l'addendum.
- **Preuve** : Cible, ligne 27 (clé mesure) : « IMPORTÉ de P4.9 … (P4.9 9de2b3b, P4.16 16163f3) ». Côté JSON : P4.16 b_full, imported_from = results\s2_credit_retention.json sur 2027-2037 et None en 2026 ; P4.9 b_full, imported_from dans {None, results\s2_credit_retention.json} ; provenance de P4.4 : 05cf8888, dirty True ; P4.4 b_warm_credit == P4.16 b_full au bit (dW, âges, résurrections) sur 12/12 seeds.
- **Classe** : E8
- **Verdict** : confirmé

### P7.2 — dose, cohorte et gel de phase 2 confrontés aux JSON publiés
- **Sonde** : `python <scratchpad>/p7v9_dose.py` (lecture des blocs learning de s2_credit_ablation.json et de s2_credit_ablation_2.json) ; `python -c` qui recalcule le rapport des chemins b_tdoff/b_eplr par seed ; `sed -n 144,166p tools/evo_runs/s2_credit_retention.py`
- **Constat** : J'ai recompté les six bras sur les douze seeds. Le chemin, les mises à jour TD et épisodiques, les résurrections et les ticks sont tous présents ; aucun trou ne permettrait à la branche 4 de conclure sur une valeur nulle. La taille de cohorte (12) est publiée au niveau de la ligne et non dans le bloc d'apprentissage. Les seuls sauts sont ceux des deux bras sans TD (td_disabled 2000). La phase 2 est gelée par un pas nul et par une assertion qui lève si W bouge. Les rapports de la paire E19 recalculés donnent les valeurs écrites dans la règle. Je n'ai trouvé aucun défaut de dose.
- **Preuve** : Valeurs manquantes : 0 sur 6 bras × 12 seeds (num_agents absent du bloc learning, 12 au niveau de la ligne). td_updates dans {1999, 0}, episode_updates dans {250, 0}, ticks {2000}. Résurrections médianes : 10 / 8 / 65,5 / 16,5 / 179 / 3,5. Rapport des chemins tdoff/eplr : médiane 1,363, min 0,828, max 2,838, sous 1 seulement en 2027 ; masse de gradient 7,34. Gel de phase 2 : s2_credit_retention.py:148 (lr=0.0, td_enabled=False) et :163 (assert dW_abs_sum == 0.0).
- **Classe** : aucune
- **Verdict** : non confirmé

### P7.3 — pas effectif publié par le compteur
- **Sonde** : `grep -n lr_effective tools/learning_events.py` ; `python -c` qui imprime lr_effective_per_agent de b_full, b_tdonly, b_const et b_eplr (seed 2026) dans results/s2_credit_ablation_2.json
- **Constat** : Pour b_full, b_tdonly et b_const, le compteur publie un pas effectif par agent de 0,00333, soit 0,04/12. Pour b_eplr il vaut None, et il n'existe pas du tout dans P4.9, donc pour b_tdoff. La cause est que le champ n'est rempli que dans l'enveloppe TD : un bras sans TD ne l'a jamais. La règle dit bien que le pas de la voie épisodique n'est publié par aucun compteur, et le runner le mesure lui-même sur l'optimiseur. La règle n'a donc rien à corriger ; le trou est dans le compteur, et c'est une dette de learning_events à ouvrir.
- **Preuve** : learning_events.py:174 : champ rempli uniquement dans learn (TD), rien dans learn_episode (:180-188). Valeurs : b_full, b_tdonly, b_const = 0.0033333 ; b_eplr = None ; b_tdoff = clé absente. La compensation est dans s2_bassin_fragility.py:355 (pas_optimiseur_mesure).
- **Classe** : aucune
- **Verdict** : non confirmé

## P8 (JUGÉ)

### P8.a — corps E26
- **Sonde** : `grep -n phenotype src/agents/mamba_agent.py ; grep -n 'benchmark_mode' src/worlds/world_1_stoneage.py` ; lecture de results/s2_bassin_fragility_sonde_conception.json (clé structure/body_rows_0_10_share)
- **Constat** : Le support du crédit (3 à 5 % de sa masse) et les tirages pos/iso écrivent dans les lignes 0-9, d'où le monde tire hp, capacité et drain. Mais en phase 2, rien ne recalcule ce corps : add_agent garde le même objet, le mode benchmark coupe toute naissance, et la garde confronte les trois grandeurs avant et après. Aucun trou trouvé.
- **Preuve** : mamba_agent.py:83-88 (corps = f(W[0:10])) ; from_genome:174 deepcopy ; world_1_stoneage.py:372 (même objet), :1657 et :1878-1879 (pas de naissance) ; s2_bassin_fragility.py:329-340 (3 grandeurs) ; body_rows_0_10_share = 0,034 full, 0,048 const, 0,031 zero
- **Classe** : E26
- **Verdict** : non confirmé

### P8.b — chevauchement E24
- **Sonde** : `python tools/check_io_overlap.py` ; `python -c` qui charge results/warm003_dagger_genome.npz et imprime N, I, O
- **Constat** : Le bassin sépare ses entrées (0-58), 5 nœuds cachés (59-63) et ses sorties (64-171). Aucun chevauchement, et load_bassin le vérifie avant tout usage. Les W persistés reprennent les dimensions du bassin.
- **Preuve** : porte : 358 génomes, 10 chevauchants (10 connus, 0 nouveau) ; bassin N=172, I=59, O=108, première sortie 64, overlap 0 ; s2_credit_retention.py:61 appelle assert_no_io_overlap ; s2_bassin_fragility.py:443-444
- **Classe** : E24
- **Verdict** : non confirmé

### P8.c — vue de l'état récurrent
- **Sonde** : `python scratchpad/p8_sonde.py` (TorchPopulationModel sur le bassin, sans monde) ; `grep -n batch_logits src/worlds/world_1_stoneage.py ; sed -n 1300,1345p`
- **Constat** : J'ai vérifié que la vue existe bien sur CPU : écrire dans les logits rendus modifie H. Le monde y écrit à deux endroits (le vote et le retrait de 0,1), et la reconstruction remet H à zéro. La règle déclare ces trois écritures. Le compteur du vote travaille sur une copie. Aucune écriture non déclarée n'a été trouvée.
- **Preuve** : shares_memory True ; H[0,64+3] passe de -0,98769 à -1,08769 après logits -= 0,1 ; backend_torch.py:198-200 ; world_1_stoneage.py:973, :1340, :1060-1066 ; backend_torch.py:111 ; s2_bassin_fragility.py:260 (copie)
- **Classe** : aucune
- **Verdict** : non confirmé

### P8.d — inertie des colonnes d'entrée (écart 3 de la règle)
- **Sonde** : `python scratchpad/p8_sonde.py`
- **Constat** : La règle affirme que la masse d'iso/pos posée sur les colonnes des nœuds capteurs n'agit pas. C'est vrai : l'observation écrase H[:, :59] avant toute lecture, et les logits ne lisent que les sorties. En perturbant ces colonnes et leur diagonale, les logits restent identiques au bit sur 6 pas. En perturbant les colonnes cachées, ils bougent.
- **Preuve** : max |Δ logits| = 0,0 (W[:, :59] + diagonale des entrées perturbées) contre 0,4708 (colonnes cachées 59-63) ; backend_torch.py:159, :170, :200 ; gate désactivé par défaut backend_torch.py:48
- **Classe** : aucune
- **Verdict** : non confirmé

### P8.e — colonnes 77-78 du vote sous pos
- **Sonde** : `python -c` : L1(W_bassin)/172 comparé à L1 des colonnes 77 et 78
- **Constat** : J'ai recalculé la masse que pos met sur les deux colonnes qui déclenchent le vote. En espérance, elle vaut 1,083 et 1,026 fois celle du bassin, ce qui concorde avec les ×1,10 et ×1,03 déclarés (écart de l'ordre du bruit d'une réalisation, environ 6 %).
- **Preuve** : colonne 77 : 13,114 contre 14,202 attendu (1,083) ; colonne 78 : 13,847 contre 14,202 (1,026) ; règle branche 7 : ×1,10 et ×1,03
- **Classe** : aucune
- **Verdict** : non confirmé

### P8.f — diagonale de W (renvoyé à P10)
- **Sonde** : `sed -n 155,170p src/agents/backend_torch.py` ; `python -c` comptant 'diag' dans la règle JSON ; lecture de diag_share dans sonde_conception.json
- **Constat** : La diagonale de W ne porte pas de synapse : elle fixe la constante de temps de chaque nœud. Le tirage de signes, qui inverse aussi ces entrées, déplace donc une fuite et non un poids. La règle ne le dit nulle part. La part concernée est inférieure à 1 %. Ce n'est ni le corps, ni un chevauchement, ni une vue : cela relève de P10.
- **Preuve** : backend_torch.py:160-162 (δ = σ(diag W), W_off hors diagonale) ; 0 occurrence de 'diag' dans la règle v9 ; diag_share 0,0091 full, 0,0051 const, 0,0011 zero
- **Classe** : aucune
- **Verdict** : hors périmètre

## P9 (DÉLÉGUÉ)

### P9.a — provenance, porte 20
- **Sonde** : `python tools/check_evidence_provenance.py --only <cible v9>` ; `python -c 'from tools.check_regime_claims import cited_results; print(cited_results(open(cible).read()))'` ; `git ls-files results/s2_bassin_fragility_sonde_conception.json results/s2_bassin_fragility_calibration_bande.json`
- **Constat** : La porte 20 refuse la cible : elle ne juge que des records docs/EDR/<nom>.md, et un brouillon JSON de pre-inscription pose dans le scratchpad n'y entre pas. Aucun verdict de provenance n'est donc rendu. Note, sans rouvrir l'enquete : son extracteur applique au texte v9 rend 0 chemin quand deux results/ y sont cites sans backtick (limite deja inscrite, P2.129) -- la porte donnerait un vert vide sur ce texte ; c'est une dette existante, pas une critique. Les deux JSON cites sont suivis par git (2/2).
- **Preuve** : EXIT=2, 'REFUS : --only designe 1 chemin(s) INCONNU(S) de cette porte' (tools/check_evidence_provenance.py:279, _perimetre_only) ; extracteur_porte = [] contre grep_brut = 2 fichiers .json cites ; git ls-files rend 2 lignes sur 2 ; limite = docs/roadmap/PRIORITES_ET_DETTES.md:1441 (P2.129)
- **Classe** : aucune (limite de porte deja au backlog, P2.129)
- **Verdict** : hors périmètre

### P9.b — sceau de la pré-inscription
- **Sonde** : `python -c "from tools.preregister import verify; verify('S2-BASSIN-FRAGILITY')"` ; `ls docs/preregistrations | grep -ic fragil`
- **Constat** : Aucune regle S2-BASSIN-FRAGILITY n'existe dans docs/preregistrations : la v9 est relue AVANT scellement, donc le sceau ne peut etre ni intact ni rompu. Le controle d'integrite est a rejouer apres scellement, en confrontant la regle scellee au texte v9 relu ici (tout ecart entre les deux serait une edition posterieure a la revue).
- **Preuve** : FileNotFoundError leve a tools/preregister.py:196 (EXIT=1) ; ls docs/preregistrations | grep -ic fragil rend 0
- **Classe** : aucune
- **Verdict** : hors périmètre

## P10

### P10.a — reprise d'un seed dont le contrôle en cours a échoué
- **Sonde** : `python scratchpad/p10_v9_reprise.py` (seed_2026.json factice portant verification_en_cours non vide, run_fragility_seed interdit)
- **Constat** : À la reprise, un seed dont le contrôle en cours de run a échoué est relu et rendu sans lever : la tâche seed ne consulte jamais la liste d'échecs qu'elle a elle-même écrite. Le parent enchaîne alors sur les onze autres seeds (environ 4 h CPU) avec un harnais cassé. Le verdict final reste juste, puisque les branches 2 et 4 sont relues à l'agrégation. En revanche, l'arrêt promis au premier échec ne tient que si le run n'est jamais interrompu.
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:1195-1196 (return json.load sans lire verification_en_cours, dont le seul lecteur est :1206) ; sortie : LEVE: non ; run_fragility_seed appelé 0 fois
- **Classe** : E13
- **Verdict** : confirmé

### P10.b — arbre de la référence du rejeu
- **Sonde** : `python -c` sur results/s2_credit_ablation_2.json et s2_credit_ablation.json : Counter des imported_from de b_full ; provenance.git_sha des trois JSON ; `grep -n p44_full_rows`
- **Constat** : Selon la règle, les valeurs contre lesquelles on rejoue b_full sur onze seeds viennent de P4.9 (commit 9de2b3b). Le champ publié contredit cette attribution : P4.16 a copié ces lignes depuis le JSON de P4.4, via p44_full_rows, et P4.9 les avait lui-même reprises de P4.4. Le risque de réplication non éprouvé avant le sceau repose donc sur l'arbre sale de P4.4 (05cf8888, 255 commits avant HEAD), et non sur l'arbre nommé.
- **Preuve** : imported_from = results\s2_credit_retention.json sur 11/12 seeds, dans P4.16 comme dans P4.9 ; git_sha de P4.4 = 05cf8888, contre 9de2b3b cité ; tools/evo_runs/s2_credit_ablation_2.py:383 appelle p44_full_rows (s2_reward_ablation.py:314)
- **Classe** : E8
- **Verdict** : confirmé

### P10.c — tirage à signes partagés dit sans effet sur le verdict
- **Sonde** : `python scratchpad/p10_v9_commun.py` (lignes synthétiques _rows du fichier de tests, où seul match_sign_commun_full ou S_sign_commun_full est modifié)
- **Constat** : La règle présente le tirage à signes partagés comme sans effet sur le verdict, puis l'inscrit elle-même dans la branche 6, et le code applique la branche 6. Un seul tirage sign_commun apparié à 2 %, toutes les autres cellules restant intactes, fait basculer la lecture de FRAGILE à INDETERMINE_APPARIEMENT. Pendant le run, le même écart arrête la tâche seed. Une survie non finie de ce tirage fait lever le verdict.
- **Preuve** : sortie : intact LU FRAGILE ; sign_commun à 2 % -> INDETERMINE_APPARIEMENT ; nan -> LEVE ; s2_bassin_fragility.py:962-963 (worst inclut sign_commun), :763 (need), :1181 (verifier_seed)
- **Classe** : aucune
- **Verdict** : confirmé

### P10.d — exception du compteur de réécritures du vote
- **Sonde** : `python scratchpad/p10_v9_vote.py` (vrai WeightedConsensus.vote, fitness 0,6 et 0,6)
- **Constat** : L'exception que la règle accorde au compteur de réécritures (deux votants de même fitness) suppose des logits identiques au bit. Or, dans toutes les conditions sauf le no-op, chaque clone porte son propre dW ou un H différent. Dans ces conditions, deux votants de même fitness sont bien comptés, et le déplacement vaut l'écart entre leurs logits, pas 1e-7. Le compteur est descriptif et hors verdict.
- **Preuve** : logits identiques : 0/2 lignes changées ; logits distincts : 2/2, écart max 0,125 ; 3 votants identiques : 3/3, écart 1,19e-07 ; src/swarm/consensus.py:55
- **Classe** : aucune
- **Verdict** : confirmé

### P10.e — formule 12 − p du brassage
- **Sonde** : `python -c` qui rejoue la permutation pour p = 0..11 (survivants dans l'ordre, s2_credit_retention.py:111 append, world_1_stoneage.py:1784)
- **Constat** : La formule 12 − p du brassage est fausse à la dernière position de la liste : le corps qui y meurt y revient, donc aucun slot ne change de corps, alors que la formule en annonce un. Les onze autres positions sont exactes. L'écart est descriptif et hors verdict.
- **Preuve** : mesure [12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 0] contre formule [12, ..., 2, 1]
- **Classe** : aucune
- **Verdict** : confirmé

### P10.f — autres références de code
- **Sonde** : `sed -n` / `grep -n` des lignes citées ; `grep GATE_TARGET` hors backend (0 activation)
- **Constat** : Les autres références de code se vérifient à la lecture : résurrection en queue, reconstruction quand B change, fenêtre réalignée par identité, ordre apprentissage puis mort, vote qui écrase toute la case, retrait de 0,1 en place, remise à zéro de H, logits vus comme une vue de H (gate inactif partout), dW_abs_sum cumulé, lr_published lu sur b_full, flux dédiés, fermeture E19, seuil 11/12, seuils confrontés après verify, borne sur les workers, témoin no-op en monde réel.
- **Preuve** : retention:111 ; world:1060-1066, :1079-1096, :965-973, :1269, :1340, :1765/:1778/:1784 ; backend_torch:111, :200, :210 ; learning_events:173,187 ; ablation:309 ; .gitignore:18 ; experiment_preflight:312
- **Classe** : aucune
- **Verdict** : non confirmé

---

## Addendum de l'auteur (session SCIENCE-HARNAIS, 2026-09-26) — jugement sous la RÈGLE D'ARRÊT : la v9 est SCELLÉE

La règle d'arrêt a été déposée avant la revue v8 et vaut pour celle-ci :
`docs/reviews/2026-09-26-S2-BASSIN-FRAGILITY.regle-d-arret.md`, sha256 `599e0074…`, stagé à 18:16:41 (+0200).

**Déroulement de la revue.** Un premier passage est sorti NUL : le vérificateur avait écrit `refus = "(aucun refus)
Roster conforme…"`, 4ᵉ forme de P2.133. Le même run a été repris, avec une copie locale qui tient cette forme pour une
absence de refus ; les agents déjà passés ont été rejoués depuis le cache. Ce passage est INDISCRIMINANT : le témoin cru
sain rend 7 critiques recevables, les défectueux 6 à 9.

**Re-vérification.** Les 13 critiques confirmées ont été re-vérifiées par l'auteur, sondes relancées. Toutes tiennent :
- provenance de b_full : `imported_from` = s2_credit_retention.json sur 11/12 seeds, dans P4.16 comme dans P4.9 ;
  P4.4 à 05cf8888, arbre sale ; P4.4 et P4.16 égaux au bit sur 12/12 seeds ;
- S_tr_full − S_a : négatif sur 12/12 seeds, médiane −28,25 ;
- écarts de la branche 8 triés : 9,0, 17,0, 24,5, 27,5, … ;
- const − eplr : 8/12 seeds, signe bilatéral p = 0,388 ;
- b_zero − S_a : sd 3,84, distribution bimodale ;
- témoin de couverture sur 8 graines : 0,927 à 0,98 (bande exécutée) contre 0,807 à 0,90 (bootstrap v6) ;
- la reprise d'un seed échoué ne relevait pas ;
- sign_commun est gardé par la branche 6 ;
- la formule 12 − p donne 0 à la dernière position, pas 1.

**Classement dans la liste fermée (a)-(g) : AUCUNE des 13 n'en relève. La v9 est scellée telle qu'elle a été relue.**
Le cas limite était **P5.b**. La branche 8 (INDETERMINE_PREMISSE) ne peut plus échouer une fois les branches 2, 4 et 5
passées. Elle a été soumise à Master 2 AVANT le sceau et classée en addendum, pour la raison suivante. La branche 8 n'est
pas un contrôle qui n'éprouve rien : c'est une garde LOGIQUEMENT IMPLIQUÉE. Si les branches 2, 4 et 5 passent, la
phase 1 est le publié au bit ; or au publié, S_tr_full − S_a est négatif sur 12/12 seeds (médiane −28,25). La prémisse
est donc établie par une MESURE déjà publiée, pas par ce run. Déclarer « jouée d'avance » une garde impliquée ne change
ni le code, ni la sortie, ni un statut publié, ni une lecture : c'est du texte, comme la branche 3 en v7. La différence
avec 9b, classée de fond en v7, est réelle : 9b était un contrôle positif dont l'issue négative manquait, donc sa
LECTURE changeait ; ici, rien n'est lu.

**Corrections portées par cet addendum.** Elles ne figurent pas dans la règle scellée : c'est la règle d'arrêt.
- **P1.a, P5.a, P7.1, P10.b** : la référence de rejeu de b_full sur 2027-2037 a été calculée par P4.4
  (`tools/evo_runs/s2_credit_retention.py`, sha 05cf8888, arbre sale) et IMPORTÉE telle quelle par P4.9 et P4.16. La
  règle nomme P4.9 (9de2b3b) : c'est faux. Le seed 2026, recalculé par P4.16, retombe au bit sur P4.4 : c'est déjà un
  témoin de réplication entre deux runners. Le risque de la branche 4 porte donc sur l'arbre de P4.4, 255 commits en
  arrière.
- **P5.b** : la branche 8 est jouée d'avance (garde logiquement impliquée, voir plus haut).
- **P5.c** : 9b échoue dès qu'eps coûte 9 ticks au seed 2036 ET 17 au seed 2037, pas seulement au-delà de 17 sur
  deux seeds. La conclusion tient : le contrôle de DIRECTION est non éprouvé.
- **P6.a** : le témoin gelé de couverture est un témoin de RÉGRESSION à graine fixe (seuil ramené à 0,92, qui tient sur
  toutes les graines rejouées), pas une garantie. La couverture qui fait foi est celle MESURÉE à 1000 répétitions dans
  `results/s2_bassin_fragility_calibration_bande.json`.
- **P6.b** : la non-monotonie const/eplr n'est PAS distinguée du bruit : 8/12 seeds, p = 0,39, IC95 du rapport
  [0,85 ; 1,95]. Elle reste un argument de prudence, pas un constat mesuré.
- **P6.c** : l'« écart-type de 3,84 ticks d'une réalisation unique » est un étalon EMPRUNTÉ : la dispersion
  inter-graines de b_zero, bimodale. Le plancher propre du pipeline n'est pas mesuré avant le sceau. Les deux phrases qui
  jugent une marge « sous le bruit » (saturation, seed 2035 de b_const) sont donc des ordres de grandeur, pas des tests.
- **P10.a** : une REPRISE relit l'échec écrit par le contrôle en cours de run et LÈVE. Code corrigé, témoin gelé.
- **P10.c** : la déclaration du tirage à signes partagés est précisée. Sa LECTURE (classe, contraste) ne change aucune
  branche ; son appariement est gardé par la branche 6, comme celui de tout tirage, et un tirage mal apparié rend le
  run INDÉTERMINÉ.
- **P10.d** : le compteur de consensus compte toute ligne changée au bit. L'exception « deux votants à fitness égales »
  ne vaut que si leurs logits sont égaux, soit en pratique le seul no-op.
- **P10.e** : une mort en position p déplace 12 − p slots pour p < 11, et 0 pour la dernière position.

Et, apporté par la session E34 (P2.132) : l'argument « clones identiques » vaut pour les bras issus du bassin, pas pour
c_cold_credit de P4.4, dont les cerveaux sont DISTINCTS. S_c, lu pour l'indice de saturation, porte donc ce brassage ;
aucune lecture n'en dépend.
