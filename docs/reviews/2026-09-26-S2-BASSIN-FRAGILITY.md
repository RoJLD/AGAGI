# Revue adversariale — S2-BASSIN-FRAGILITY (pré-inscription)

- **Cible** : `C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/S2-BASSIN-FRAGILITY.json`
- **Date** : 2026-09-26
- **SHA** : `da09f7a12c265fa5e4a710227a7123aeeff4a45e` (worktree `.worktrees/science`)
- **Résultat des TÉMOINS** :
  - `EDR-GRAB-COST-1828371` : RETROUVE, code 0, 6 recevables — `PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/science/tools/refutateur_temoins.py --verifier EDR-GRAB-COST-1828371 C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/refutateur/critiques-EDR-GRAB-COST-1828371.json --extrait C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/temoins/temoin-3.md --jugement OUI`
  - `S2-BLIND-CHAMPION-42e9357` : RETROUVE, code 0, 7 recevables — `PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/science/tools/refutateur_temoins.py --verifier S2-BLIND-CHAMPION-42e9357 C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/refutateur/critiques-S2-BLIND-CHAMPION-42e9357.json --extrait C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/temoins/temoin-1.md --jugement OUI`
  - `EDR-RETAIN-COMPOSE-4204f8f` : RETROUVE, code 0, 7 recevables — `PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/science/tools/refutateur_temoins.py --verifier EDR-RETAIN-COMPOSE-4204f8f C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/refutateur/critiques-EDR-RETAIN-COMPOSE-4204f8f.json --extrait C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/temoins/temoin-4.md --jugement OUI`
  - `LOCK-002-286f244` (cru sain) : MESURE, code 0, 6 recevables — `PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/science/tools/refutateur_temoins.py --verifier LOCK-002-286f244 C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/refutateur/critiques-LOCK-002-286f244.json --extrait C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/temoins/temoin-2.md`
- **Planchers** : PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 · plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1) -- S n'est pas imprime par --verifier : lu par verdict_temoin du meme script (seuil=1, depasse_le_seuil=True)
- ⚠ INDISCRIMINANT : le record cru sain rend autant de critiques recevables que les defectueux

---

## P1

### P1.a
- **Sonde** : `python -c "import json;c=json.load(open('results/s2_bassin_fragility_sonde_conception.json',encoding='utf-8'))['sonde_net_chemin']['cells'];print('noop',c['noop']['survival']['survival_median']);[print(k,round(v['structure']['net_l1_median_agent'],2),v['transplant']['S'],round(v['path_total'],1)) for k,v in c.items() if k!='noop']" ; sed -n '124,136p' docs/EDR/S2-CREDIT-ABLATION-2_*.md`
- **Constat** : Prémisse qui fonde la question : l'érosion croîtrait avec la quantité de mouvement des poids. Elle vient de P4.16, où le mouvement est la longueur de CHEMIN. La règle adopte pourtant le déplacement NET comme amplitude, et sur cette grandeur sa propre sonde de conception (seed 2026) inverse l'ordre de deux bras : b_const bouge plus en net que b_eplr (27,96 contre 18,60) mais érode deux fois moins (S_tr 21,0 contre 11,5, noop 31,5). La monotonie n'a donc jamais été mesurée sur l'échelle choisie, et le seul seed disponible la contredit. Elle porte le cadrage FRAGILE (l'amplitude seule détruit) et l'ordonnancement par net de la branche 10c. L'inversion n'est déclarée ni dans les prédictions ni dans ce que le run ne tranche pas.
- **Preuve** : Sortie : b_const net 27.96, S_tr 21.0, chemin 941.5 ; b_eplr net 18.6, S_tr 11.5, chemin 1168.2 ; noop 31.5. Donc net const > eplr, mais érosion const -10,5 < eplr -20,0. Opposé à docs/EDR/S2-CREDIT-ABLATION-2_Each_Credit_Pathway_Alone_Floors_The_Bassin_And_A_Positive_Constant_Return_Erodes_Halfway.md:130 (en chemin, 5,4 % -> -12,25 puis 6,4 % -> -19,0, soit une monotonie tenue parce que l'échelle est le chemin).
- **Classe** : E8
- **Verdict** : confirmé — la prémisse est héritée d'une autre grandeur (le chemin), et sur la grandeur adoptée elle est contredite par la mesure de pré-scellement (n = 1 seed)

### P1.b
- **Sonde** : `python -c "import numpy as np;z=np.load('<scratchpad>/p418_W_p416_b_eplr_2026.npz');D=np.abs(z['W_final'].astype(float)-z['W0'].astype(float)[None]);print(np.nonzero(D.sum(axis=(0,1))>0)[0].tolist())"` ; sha256sum du même npz ; même lecture pour les quatre autres bras
- **Constat** : Le texte présente le support de ΔW comme un fait mesuré : onze colonnes identiques pour chacun des cinq bras. C'est faux pour b_eplr, dont le ΔW n'occupe que 8 colonnes (64 à 71) ; 88, 89 et 92 ne bougent pas. Le JSON de conception le montrait déjà : fraction d'entrées déplacées 0,04137 = 8x153/29584, contre 0,05689 = 11x153/29584 pour full, tdonly et const. Son top-10 de colonnes se termine par 0 et 1, des égalités à masse nulle. Les chiffres qui justifient le sham primaire et le biais attribué à iso (6,4 % des entrées, 94 % de la masse hors support) valent 4,7 % et 95,3 % sur ce bras. Le sham sign est tiré sur le support propre à chaque bras, donc la mécanique du verdict n'est pas touchée. En revanche, la description de l'intervention publiée au sceau est fausse, et elle est incorrigible une fois scellée.
- **Preuve** : Sortie : b_eplr ncols 8 [64..71] ; full, tdonly, const et zero ncols 11 [64..71, 88, 89, 92], 153 lignes par colonne. Le sha256 du npz vaut 80628299...36736, identique à W_sonde_sha256 du JSON. Dans results/s2_bassin_fragility_sonde_conception.json, b_eplr porte frac_entries_moved_median 0.041373715521903734 et col_mass_top10_nodes [66,65,67,64,69,71,68,70,0,1].
- **Classe** : E8
- **Verdict** : confirmé — une clause qui décrit la structure a été généralisée à cinq bras sans être vérifiée ; la mesure publiée la dément

### P1.c
- **Sonde** : `git status --short results/s2_bassin_fragility_sonde_conception.json tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : Les mesures de pré-scellement sur lesquelles reposent les deux critiques ci-dessus, ainsi que le runner, sont aujourd'hui non suivis par git. Le texte les annonce pourtant comme suivies. Un clone ne peut donc pas rouvrir ces prémisses.
- **Preuve** : Sortie : '?? results/s2_bassin_fragility_sonde_conception.json' et '?? tools/evo_runs/s2_bassin_fragility.py'. git ls-files ne rend aucune correspondance.
- **Classe** : E27
- **Verdict** : hors périmètre — c'est de la provenance, déléguée à P9 (check_evidence_provenance) ; le sceau n'est pas encore committé et le fichier doit partir dans le même commit

## P2 (DELEGUE) Regime : chaque parametre cite est-il publie par l'evidence ?

- **Sonde** : `python tools/check_regime_claims.py --only C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/S2-BASSIN-FRAGILITY.json` ; puis `ls docs/EDR/*.md | wc -l` ; puis `sed -n 345,360p tools/check_regime_claims.py`
- **Constat** : La porte 19 a rendu OK, mais ce OK ne dit rien sur la cible. Elle ne lit que les .md de docs/EDR (304 records au sha da09f7a1), et son filtre --only ne s'applique qu'a ces chemins. La cible est une regle JSON de pre-inscription rangee dans le scratchpad : aucun record n'a donc ete juge. Verdict recopie : OK, code de sortie 0. Il vaut pour le depot, pas pour S2-BASSIN-FRAGILITY. La question de P2 se posera pour de bon sur le record EDR qui citera le results/*.json de ce run.
- **Preuve** : La sortie compte 304 records : 227 SANS_PARAMETRE, 6 CONCORDE, 7 CONCORDE_HORS_REGIME, 52 SANS_RESULTS, 3 SANS_REGIME, 6 SANS_VALEUR_LUE, 3 DISCORDE ; puis OK, 64 legataires, aucun nouveau, exit 0. ls docs/EDR/*.md en compte aussi 304. tools/check_regime_claims.py:347 fixe le repertoire lu a docs/EDR, et la ligne 432 filtre les fautifs par appartenance a only : la cible, hors de ce repertoire, ne peut en faire partie.
- **Classe** : aucune
- **Verdict** : hors perimetre

## P3

### P3.a (DELEGUE) : balayage du pas, porte 23
- **Sonde** : `cd .worktrees/science (HEAD da09f7a1) && python tools/check_e19_optimizer_sweep.py --only tools/evo_runs/s2_bassin_fragility.py ; echo EXIT=$? ; ls docs/preregistrations/S2-BASSIN-FRAGILITY*`
- **Constat** : La porte 23 rend OK (exit 0) : pas de nouveau runner nu sous gradient, pas de régression, aucun appelant de la garde perdu. Le runner est rangé regle_absente, non bloquant et à geler plus tard. Il appelle la garde E19 directement, mais aucun docs/preregistrations/S2-BASSIN-FRAGILITY.json n'existe encore : la cible relue n'est qu'un brouillon non scellé, dans le scratchpad. Verdict de la porte recopié, sans rouvrir l'enquête.
- **Preuve** : Sortie de la porte : 34 runners scellés | 12 sous gradient | 9 nus | 4 indéterminés | 6 non résolus | 1 règle absente | 3 appelants de la garde | 19 gelés ; '[regle_absente] tools/evo_runs/s2_bassin_fragility.py : appelle assert_verdict_invariant_to_optimizer(...) directement' ; 'OK : aucun nouveau runner sous gradient sans garde E19' ; EXIT=0. Le ls rend 'No such file or directory'. tools/evo_runs/s2_bassin_fragility.py:33 annonce pourtant cette règle comme déjà scellée.
- **Classe** : aucune
- **Verdict** : non confirmé

### P3.b : signalement transmis à P5, où se juge le reste d'E19
- **Sonde** : `grep -n 'E19_PAIRE\|E19_CLOSURE_MAX\|^ARMS\|e19' tools/evo_runs/s2_bassin_fragility.py` ; `grep -o 'tdoff' <cible> | wc -l` ; `grep -o 'clause_E19' <cible> | wc -l` ; ls -la des deux fichiers
- **Constat** : Le runner de 13:25 et la règle relue de 13:16 ne décrivent pas le même dispositif. Le code rejoue six bras, dont b_tdoff, qui forme la paire E19 avec b_eplr (pas 0,04 contre LR_LOW). Il ajoute aussi une branche 9bis qui relit les bras érodés en DIRECTION_DEPEND_DU_PAS quand la garde conclut à la non-invariance, avec un seuil de fermeture de 2/3. La règle n'en dit rien : 5 bras, 66 phases 2, branches 1 à 10, et aucune occurrence de tdoff ni de clause_E19. Si on scelle ce JSON tel quel, le code lit une clause que la règle ne porte pas, et le seuil qui peut changer la lecture de deux bras reste hors du sceau.
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:57 (ARMS : 6 bras, dont b_tdoff), :74 (E19_PAIRE = {tdoff: 0.04, eplr: LR_LOW}), :75 (E19_CLOSURE_MAX = 2/3), :499 (garde appelée seulement si tdoff et eplr sont dans les bras), :535-540 (branche 9bis qui modifie la lecture). Dans la cible : tdoff apparaît 0 fois, clause_E19 0 fois. Horodatage : cible 13:16, runner 13:25.
- **Classe** : E8 (la règle ne publie pas le régime que le runner applique), à confirmer en P5
- **Verdict** : hors périmètre

## P4

### P4.a
- **Sonde** : `python tools/check_control_family.py --report` ; `python -c "from tools.check_control_family import scan_runners; import tools.evo_runs.s2_bassin_fragility as m; print(scan_runners()['tools/evo_runs/s2_bassin_fragility.py'], len(m.ARMS), m.FAMILLE)"` ; `grep -c tdoff <cible>`
- **Constat** : La cible et son runner ne décrivent pas le même dispositif. La cible compte 11 contrastes sur cinq bras de crédit et ne nomme jamais b_tdoff. Le runner qui l'exécutera en compte six (b_tdoff ajouté ligne 57), fixe FAMILLE = 13 (ligne 76) et fait tourner 77 phases 2 par seed, contre 66 annoncées. FAMILLE est une constante Python que rien ne confronte au texte scellé (agreger, ligne 707). Sceller cette version publierait donc un design à 13 cellules sous une règle qui en déclare 11, et le verdict lirait un bras absent de la règle. La porte 11 rend declare: True : elle voit que la déclaration existe, pas sa valeur. Le seuil 11/12 tient aux deux tailles (0,00317 <= 0,00385), le défaut porte donc sur l'objet déclaré, pas sur le seuil.
- **Preuve** : porte : runners scellés 32, sans design 0, bassin_fragility {scelle: True, declare: True} ; runner ARMS = 6 et FAMILLE = 13 (tools/evo_runs/s2_bassin_fragility.py:57 et :76) ; tests/sandbox/test_s2_bassin_fragility.py:448 fige cells == 13 ; cible famille_de_controles = 11 ; grep -c tdoff sur la cible = 0 ; P(X>=11/12) = 0,00317, 0,05/11 = 0,00455, 0,05/13 = 0,00385
- **Classe** : E23
- **Verdict** : confirmé

### P4.b
- **Sonde** : `python -c` comparant les clés de la cible et de S2-BASSIN-FRAGILITY.v2.json ; `grep -n` de _garde_e19 et de e19 dans le runner
- **Constat** : Le runner contient une décision que la cible ne déclare ni ne compte. Quand la fermeture dépasse 2/3, la garde de pas (_garde_e19) réécrit la lecture des bras tdoff et eplr en DIRECTION_DEPEND_DU_PAS. La version cible n'a aucune clause E19 : c'est la seule clé ajoutée par la v2. Le sens est prudent (elle retire des lectures, elle n'en crée pas), mais le verdict exécuté ne sera pas celui que décrit le texte qu'on scellerait.
- **Preuve** : clés présentes en v2 seulement : ['clause_E19'] ; sha256 cible = v1-revue = 9791ebbb... ; tools/evo_runs/s2_bassin_fragility.py:411 (définition), :499 (appel), :537 (réécriture de la lecture)
- **Classe** : E23
- **Verdict** : confirmé

### P4.c
- **Sonde** : `python -c` lisant results/s2_credit_ablation.json['verdict'] : d_zero_negative, S_zero_median, S_a_median ; `grep -n` de moins = cpos et de _lecture_bras dans le runner
- **Constat** : La famille déclarée compte une cellule que le verdict ne lit jamais. Le test MOINS n'intervient que pour un transplant ERODE. Or le transplant de b_zero est publié NEUTRE (8/12 négatifs) et la branche 4 exige qu'il soit rejoué au bit. Le contraste c_zero est donc compté sans être lu. Il est même quasi inatteignable : l'écart S_a − S_tr vaut 2,75 < 5, donc il faudrait un sham qui dépasse le bassin. On lit réellement 10 cellules, pas 11. Le surcompte est conservateur, mais le nombre déclaré n'est pas le nombre lu.
- **Preuve** : zero 8/12, S_zero 33.25 contre S_a 36.0 ; MOINS est calculé ligne 483 et consulté seulement sous tr_cls == ERODE (tools/evo_runs/s2_bassin_fragility.py:402)
- **Classe** : E23
- **Verdict** : confirmé

### P4.d
- **Sonde** : `python -c` imprimant thresholds.sign_min et d_*_negative de results/s2_credit_ablation_2.json et results/s2_credit_ablation.json
- **Constat** : Les classes de transplant sont recalculées au seuil de 11/12, alors que P4.16 et P4.9 les publiaient à 10/12 : ce seuil n'est donc pas hérité tel quel. Mais les survies sont rejouées au bit, et les négatifs publiés (12, 12, 11, 11, puis 8 pour zero) tombent du même côté aux deux seuils. b_const et b_eplr sont pile sur la borne, sans basculer.
- **Preuve** : sign_min publié = 10 dans les deux JSON, runner SIGN_MIN = 11 ; const 11/12, eplr 11/12, full et tdonly 12/12, zero 8/12
- **Classe** : aucune
- **Verdict** : non confirmé

### P4.e
- **Sonde** : `python -c` calculant S_a − S_tr_median par bras depuis les deux results publiés
- **Constat** : Le seuil de ±5 ticks vient des classes bras − S_a de P4.4. Il est réappliqué au contraste sham − transplant, une autre grandeur. Pour chacun des quatre bras érodés, il reste atteignable sans qu'aucun sham ne dépasse le bassin.
- **Preuve** : écart maximal atteignable : full 28,0 ; tdonly 27,5 ; const 12,75 ; eplr 19,0 ; tous > 5
- **Classe** : aucune
- **Verdict** : non confirmé

## P5

### P5.a
- **Sonde** : `python scratchpad/p5_sonde.py` : lignes synthetiques passees a fragility_verdict(rows, arms=ARMS[:5]), sans monde. S_a=30, S_tr=20 sur 12/12, S_sign=30 sur 10 seeds et 19 sur 2, S_pos=10
- **Constat** : L'issue FRAGILE ne demande aucune erosion par le sham : elle tombe des que le contraste sham-moins-greffe rate la barre 11/12. Un sham qui laisse la survie au niveau du no-op sur 10 seeds sur 12 fait lire au verdict « toute perturbation detruit ». FRAGILE est donc le complement d'un test peu puissant, et DIRECTION, l'issue concurrente, n'a aucun controle positif dans le dispositif (b_zero, NEUTRE, n'exerce jamais la branche MOINS).
- **Preuve** : sortie : « verdict LU FRAGILE » ; b_full : sign classe_vs_S_a NEUTRE 2/12, contraste 10/12 mediane +10.0, lecture FRAGILE. Code : tools/evo_runs/s2_bassin_fragility.py:400-405 (_lecture_bras rend FRAGILE si not moins, quel que soit sh_cls)
- **Classe** : E2
- **Verdict** : confirmé

### P5.b
- **Sonde** : `python scratchpad/p5_sonde.py` (load_bassin : lecture du npz, aucun monde)
- **Constat** : Le controle positif (branche 7) est un bruit gaussien isotrope a 100 % de la norme L1 du bassin, soit 24 a 718 fois le deplacement net des bras qu'il est cense calibrer. Qu'il erode ne dit rien de la capacite de l'instrument a voir une erosion a 0,14-4 % de la norme : c'est une garde posee sur le regime facile. En plus, il protege FRAGILE, que la lecture atteint sans erosion (critique precedente).
- **Preuve** : sortie : L1(W_bassin) 2442.8 ; pos/full = 24.3x (net/L1 4.11 %), pos/eplr = 131.3x (0.76 %), pos/zero = 718.5x (0.14 %) ; POS_REL = 1.0 a tools/evo_runs/s2_bassin_fragility.py:82 ; branche 7 a :525
- **Classe** : E19
- **Verdict** : confirmé

### P5.c
- **Sonde** : `grep -ciE 'E19|tdoff|clause' <cible>` ; `grep -nE '^FAMILLE|^ARMS|^E19_PAIRE|clause_E19' tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : La reference de pas (moitie P3 de la question) n'existe que dans le runner. La cible scellable n'a ni sixieme bras, ni paire de pas, ni clause E19, alors que b_eplr tourne a un pas dix fois plus bas que les quatre autres bras. Le runner, lui, lit une clause_E19 « de la regle scellee », ajoute b_tdoff et compte 13 contrastes. Le texte qu'on scellerait ne couvre donc pas la lecture effectivement executee : les 11 contrastes declares s'opposent aux 13 codes.
- **Preuve** : cible : 0 occurrence de E19/tdoff/clause, 2 occurrences de « 11 contrastes » ; runner :57 ARMS a 6 bras dont b_tdoff, :74 E19_PAIRE {tdoff 0.04, eplr LR_LOW}, :76 FAMILLE = 13, :73 cite une clause_E19 absente de la cible
- **Classe** : E23
- **Verdict** : confirmé

### P5.d
- **Sonde** : `grep -c 'assert_positive_control\|assert_not_degenerate\|assert_ablation_changes_something' tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : Aucune des gardes executables des deux issues n'est appelee par le runner. Le controle positif est recode a la main dans la branche 7 du verdict, et les assertions calibrees du depot ne sont jamais invoquees : ni controle positif, ni non-degenerescence, ni ablation qui change quelque chose. La branche 7 n'est donc confrontee a aucun cas de calibration du depot.
- **Preuve** : sortie : 0 ; seules assert_control_family et declare_design sont importees (tools/evo_runs/s2_bassin_fragility.py:705-708) ; controle positif recode a :525-529
- **Classe** : E1
- **Verdict** : confirmé

## P6

### P6.a (JUGE) plancher de bruit
- **Sonde** : `grep -nE "abs_mediane|bande" tools/evo_runs/s2_bassin_fragility.py` ; `grep -nE "eps|bande"` du même fichier filtré sur les lignes 500-560 (branches du verdict)
- **Constat** : La règle promet d'énoncer quand un écart sham moins greffe tombe dans la dispersion entre deux tirages. Le runner calcule cette dispersion (d01) et la range dans le JSON, mais aucune ligne ne la confronte à l'écart lu (cmed) et aucun drapeau n'est produit. La promesse n'a donc pas d'exécutable, et un écart noyé dans le bruit sortirait sans mention.
- **Preuve** : cible S2-BASSIN-FRAGILITY.json:29 (clause « se DIT ») contre tools/evo_runs/s2_bassin_fragility.py:491, seule occurrence de abs_mediane (6 lignes au total : 12, 81, 461, 490, 491, 714) ; 0 occurrence dans les lignes 500-560, où cmed (l.482) est comparé au seul delta_min (l.483)
- **Classe** : E10
- **Verdict** : confirmé

### P6.b (JUGE) no-op de CE contraste
- **Sonde** : `sed -n 318,327p tools/evo_runs/s2_bassin_fragility.py` ; `grep -noiE "bande[^.;]{0,120}"` sur la cible
- **Constat** : La référence S_a (noop) est exacte par construction, donc son bruit est nul : ce n'est pas un plancher, c'est une reproductibilité. Le seul plancher de perturbation prévu, eps, tire un bruit isotrope sur les 172×172 entrées. Or le sham lu (sign) n'agit que sur 11 colonnes. La pré-inscription montre elle-même qu'une masse isotrope tombe à 94 % hors de ce support, dont un tiers sur des colonnes inertes. eps mesure donc la sensibilité à une perturbation surtout inerte, et il sous-estime le plancher chaotique du bras lu.
- **Preuve** : s2_bassin_fragility.py:323 : sham_delta(zero + 1.0, "iso", …) avec un support entier ; cible:20, point (3) : 94 % hors des 11 colonnes, 34 % sur les colonnes d'entrée « inertes » ; cible:26 : aucune survie sous eps n'est mesurée avant le sceau
- **Classe** : E6
- **Verdict** : confirmé

### P6.c (JUGE) le plancher peut-il changer la lecture
- **Sonde** : `grep -nE "eps|bande" tools/evo_runs/s2_bassin_fragility.py` filtré sur les lignes 500-560 ; `grep -rnE "bande|abs_mediane|S_eps" tests/sandbox/test_s2_bassin_fragility.py`
- **Constat** : Le contrôle eps est classé (l.462-464), mais aucune des branches 1 à 10 ne le consulte. L'unique fixture de test fixe S_eps égal à S_a, donc la voie « eps érode » n'est jamais exercée. Si une perturbation 10⁴ fois plus petite érodait autant que le crédit, la lecture FRAGILE, qui porte sur l'amplitude, sortirait quand même intacte. Ce contrôle d'amplitude ne peut pas faire échouer le verdict.
- **Preuve** : 0 référence à eps dans s2_bassin_fragility.py:500-560 ; tests/sandbox/test_s2_bassin_fragility.py:155 : _rows(S_a=36.0, …, S_eps=36.0) ; S_eps_draws recopie S_eps (l.162)
- **Classe** : E1
- **Verdict** : confirmé

### P6.d (JUGE) échelle de la bande
- **Sonde** : `python -c` : Monte-Carlo normal, 200 000 × 5 tirages ; std de d01, std de la médiane de 5, médiane |d01|, médiane signée de d01 sur 12 seeds (20 000 répétitions)
- **Constat** : Hypothèse testée : une bande tirée de deux tirages isolés serait à la mauvaise échelle pour une médiane de 5. L'écart-type est bien 2,65 fois plus grand. Mais la valeur absolue médiane publiée (0,956σ) se trouve à l'échelle d'un intervalle à 95 % de la médiane de 5 (1,049σ). Pas de défaut ici. Seule réserve mineure : le champ signé « mediane » de d01 vaut zéro par symétrie et n'apporte rien.
- **Preuve** : std d01 = 1,418 contre std médiane5 = 0,535 (×2,65) ; médiane |d01| = 0,956 contre 1,96 × 0,535 = 1,049 ; médiane signée moyenne = 0,0
- **Classe** : aucune
- **Verdict** : non confirmé

### P6.e, hors objet (relève de P4/P3)
- **Sonde** : `grep -cE "tdoff|E19|clause_E19"` sur la cible ; `grep -nE "^ARMS|FAMILLE|SIGN_MIN" tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : La cible et le runner n'ont pas le même dispositif. La cible ne compte que cinq bras et onze contrastes, sans clause de balayage du pas. Le runner exécute six bras (b_tdoff en plus), une famille de 13 et une garde E19 qui peut réécrire la lecture de deux bras. Le runner n'exécute donc pas la règle qui serait scellée.
- **Preuve** : cible : 0 occurrence ; famille déclarée « 11 » (cible:21) contre s2_bassin_fragility.py:57 (6 bras), :76 FAMILLE = 13, :86 « 0,05/13 », :535-541 réécriture DIRECTION_DEPEND_DU_PAS
- **Classe** : E23
- **Verdict** : hors périmètre

## P7

### P7.a (JUGE) - Dose : le compte de mises a jour recues est-il publie ?
- **Sonde** : `grep -o <motif>` sur la cible pour td_updates, episode_updates, resurrection, n_agents ; `grep -n` dans tools/evo_runs/s2_bassin_fragility.py ; script p7_dose.py (scratchpad) sur results/s2_credit_ablation_2.json et s2_credit_ablation.json
- **Constat** : Le texte scelle n'engage la publication d'aucun compte d'evenements d'apprentissage (appels TD, credits episodiques, resurrections) : sa seule mesure de dose est la longueur de chemin et le deplacement net, et la branche de replication ne confronte au publie que ce chemin et les ages. La dose sera bien ecrite, mais par l'executable (bloc learning recopie par cellule dans l'agregat suivi), pas par le sceau : le runner pourrait la retirer sans violer la regle.
- **Preuve** : cible : td_updates=0, episode_updates=0, resurrection=0, n_agents=0 occurrences (dW_abs_sum=4) ; tools/evo_runs/s2_bassin_fragility.py:332 (rec learning) et :729 (data cells) ; publie anterieur : td_updates 1999, episode_updates 250, ticks 2000 sur 72/72 cellules (bras x seed), 0 absent
- **Classe** : E10
- **Verdict** : confirme

### P7.b (JUGE) - Cohorte de phase 1 : resurrections constantes entre bras ?
- **Sonde** : `python -c` qui imprime median/max de learning.resurrections par bras sur results/s2_credit_ablation_2.json et results/s2_credit_ablation.json
- **Constat** : La letalite pendant l'apprentissage immortel varie d'un facteur ~18 entre bras et aucune branche ne la lit ni ne la publie. Elle est fortement anti-ordonnee avec le deplacement net : les bras a plus faible net sont ceux qui meurent le plus. La branche 10c attribue la partition FRAGILE / DIRECTION a l'amplitude seule ; la letalite de phase 1 est une covariable confondue que la regle ne nomme pas. La dose, elle, n'est pas bornee par la mort (resurrection dans le meme tick : au plus ~1,6 % de ticks perdus par agent en moyenne sur le pire seed).
- **Preuve** : medianes (n=12 chacune) : b_tdonly 8, b_full 10, b_eplr 16,5, b_const 65,5, b_zero 179 (max 380) ; net sonde seed 2026 : full 100,5 / tdonly 73,0 / const 28,0 / eplr 18,6 / zero 3,4 ; tools/evo_runs/s2_credit_retention.py:133-134 (step puis refill dans le meme tick) ; 380/12/2000 = 1,6 %
- **Classe** : aucune
- **Verdict** : confirme

### P7.c (JUGE) - Nul d'apprentissage ou nul de letalite ?
- **Sonde** : `grep -n count_learning_events tools/evo_runs/s2_credit_retention.py` puis Read 144-164 ; script p7_dose.py (ticks par cellule publiee)
- **Constat** : Aucune issue nulle de la regle (NEUTRE, INOFFENSIF, sham non ERODE) n'est un nul d'apprentissage : l'apprentissage se fait en phase immortelle complete, et la DV de survie est mesuree ensuite a poids geles, gel asserte. La confusion documentee en P1.6 (survie qui mele apprendre et mourir) ne s'applique pas a ce dispositif.
- **Preuve** : tools/evo_runs/s2_credit_retention.py:148 (lr=0.0, td_enabled=False) et :163 (assert dW_abs_sum == 0.0) ; ticks min=max=2000 sur les 6 bras x 12 seeds publies
- **Classe** : E2
- **Verdict** : non confirme

### P7.d (JUGE) - Cohorte de phase 2 constante (12 ages par condition) ?
- **Sonde** : `grep -n dead_agents src/worlds/*.py` ; `sed -n 1640,1700p src/worlds/world_1_stoneage.py` ; `sed -n 60,95p tools/evo_runs/s2_credit_retention.py`
- **Constat** : Les tirages de sham ne controlent pas le nombre d'ages (seul le no-op est compare au publie), mais le monde du run ne peut ni ajouter ni perdre d'agent hors de la liste des morts : la reproduction est coupee en mode benchmark et la seule sortie des vivants alimente dead_agents. Douze ages par condition par construction ; une assertion de longueur coute zero et fermerait la porte.
- **Preuve** : src/worlds/world_1_stoneage.py:1657 (clone seulement si not self.benchmark_mode) et :1681 (unique append a dead_agents) ; tools/evo_runs/s2_credit_retention.py:73 (benchmark_mode = True) ; tools/evo_runs/s2_bassin_fragility.py:292-296 (_cond_record sans controle de longueur)
- **Classe** : aucune
- **Verdict** : non confirme

### P7.e - constat de passage (releve de P4/P3)
- **Sonde** : `grep -n 'ARMS = \|FAMILLE = \|SIGN_MIN = ' tools/evo_runs/s2_bassin_fragility.py` ; `ls docs/preregistrations/S2-BASSIN-FRAGILITY*`
- **Constat** : La cible et l'executable ne decrivent pas le meme dispositif : le runner rejoue six bras (b_tdoff ajoute comme paire E19 de b_eplr) avec une famille de 13 contrastes, la cible en declare cinq, 11 contrastes et 66 phases 2 par seed ; la dose de b_tdoff (0 TD, 250 episodes, pas 0,04) n'y figure pas. A realigner avant sceau ; la regle scellee citee par le runner n'existe pas encore dans docs/preregistrations.
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:57 (six bras), :76 (FAMILLE = 13), :86 (0,05/13) contre cible famille_de_controles (11) et mesure (cinq bras) ; ls : No such file or directory ; runner non suivi (git status ??)
- **Classe** : E23
- **Verdict** : hors perimetre

## P8

### P8.a (JUGE) — Corps et aliasing : VUE de l'état récurrent
- **Sonde** : `python scratchpad/p8_alias_probe.py` (TorchPopulationModel sur 2 clones du bassin sous _pinned_substrate, un forward, AUCUN monde) ; `sed -n 1263,1269p` et `960,973p src/worlds/world_1_stoneage.py` ; `grep -c consensus|alias|E5` sur la cible et le runner
- **Constat** : En phase 2, le modèle torch rend des logits qui partagent la mémoire de son état récurrent H (le gate est inactif sur ce substrat). Le monde écrit dans ce tableau : quand plusieurs agents sur la même case dépassent les seuils partage/acceptation, le vote social remplace leurs logits. Il réécrit donc les 108 nœuds de sortie de H avant le pas suivant, et cette réécriture n'est coupée par aucune garde benchmark. Les deux nœuds qui déclenchent ce vote (77 et 78, logits 13 et 14) sont hors des 11 colonnes où vit ΔW. Ils sont en revanche dans le support de iso, eps et pos. Ces tirages peuvent donc agir par une seconde intervention, qui porte sur l'état et non sur les poids ; transplant et sign ne l'atteignent qu'indirectement. Le contrôle positif pos peut ainsi éroder par ce canal. La pré-inscription ne nomme pas ce canal et ne publie aucun compte de consensus par bras. Sa fréquence n'est pas mesurée : la mesurer demande une simulation, donc c'est une dette et non une sonde de revue.
- **Preuve** : sortie de la sonde : CONDITION_GATE False ; shares_memory(logits, H) = True ; écrire 123.0 dans logits[0] fait passer H[0, noeud 77] de 0.055519 à 123.0, 108/108 noeuds de sortie écrasés. src/agents/backend_torch.py:200 et :210 (logits = H_new[:, N-O:N] ; return logits.cpu().numpy()). src/worlds/world_1_stoneage.py:1269 (_apply_social_consensus appelé sans condition), :963-964 (seuils sur logits[13], logits[14]), :973 (batch_logits[idx] = consensus_logits) ; :1878 ne coupe que la reproduction sociale et HGT. grep consensus / alias / E5 : cible 0/0/0, runner 0/0/0 (motif validé sur un positif : consensus = 4 dans le monde).
- **Classe** : E5
- **Verdict** : confirmé

### P8.b (JUGE) — Corps (E26)
- **Sonde** : `grep -n update_phenotype|phenotype_ src/` ; `sed -n 171,185p tools/evo_runs/s2_bassin_fragility.py` ; `sed -n 1874,1881p src/worlds/world_1_stoneage.py` ; lecture de results/s2_bassin_fragility_sonde_conception.json (structure/body_rows_0_10_share)
- **Constat** : ΔW et les tirages touchent bien les lignes 0 à 9, d'où le monde dérive hp et inventaire. Selon la sonde de conception, c'est 3,1 à 5,7 % de la masse de ΔW selon le bras, et environ 10/172 pour iso et pos par construction. Pourtant le corps ne bouge pas. Il est calculé une fois au clonage, puis comparé après la pose de W. Le monde ne lit que les attributs phenotype_*. Enfin, les seuls recalculs possibles en cours de vie (enfant HGT, absorption, mitose) sont coupés en benchmark_mode. E26 est donc neutralisé pour les 12 clones de chaque bras.
- **Preuve** : s2_bassin_fragility.py:180-184 (corps capturé, W posé, AssertionError si différent) ; mamba_agent.py:174-177 (deepcopy puis update_phenotype une fois) ; world_1_stoneage.py:375,388,702,1652 ne lisent que phenotype_* ; recalculs :990 (HGT) et :1657 (mitose) coupés par benchmark_mode (:1878, :1657) ; body_rows_0_10_share = 0.034 (b_full), 0.031 (b_zero), 0.048 (b_const), 0.057 (b_eplr), 0.035 (b_tdonly) ; phenotype_unchanged_by_learning True sur les 5 bras
- **Classe** : E26
- **Verdict** : non confirmé

### P8.c (JUGE) — Chevauchement entrée/sortie (E24)
- **Sonde** : `python tools/check_io_overlap.py` ; `python -c` qui charge results/warm003_dagger_genome.npz et imprime num_inputs, num_outputs, N ; `sed -n 155,170p src/agents/backend_torch.py`
- **Constat** : Le bassin WARM-003 a 59 entrées et 108 sorties dans 172 nœuds, donc 5 nœuds cachés et aucun slot partagé. load_bassin appelle la garde de chevauchement avant toute cohorte. La porte 17 ne signale aucun nouveau génome chevauchant. L'affirmation selon laquelle les colonnes d'entrée sont inertes se vérifie : l'observation écrase ces nœuds à chaque pas, avant le produit par W.
- **Preuve** : porte 17 : 358 génomes persistés, 10 chevauchants (connus 10, nouveaux 0, aggravés 0), exit 0 ; npz : shape (172,172), ni 59, no 108, max_H 5, début des sorties 64 ; tools/evo_runs/s2_credit_retention.py:61 (assert_no_io_overlap) ; backend_torch.py:159 (H[:, :self.I] = obs_t avant le bmm de :163)
- **Classe** : E24
- **Verdict** : non confirmé

### P8.d (JUGE) — ce qu'alimentent les entrées touchées : la diagonale
- **Sonde** : `sed -n 160,162p src/agents/backend_torch.py` ; lecture de structure/diag_share dans results/s2_bassin_fragility_sonde_conception.json
- **Constat** : Les entrées diagonales de W n'alimentent pas l'excitation, mais la constante de fuite δ = σ(W_jj). Le signe tiré de sign inverse donc, sur ces entrées, le sens du changement de constante de temps, et pas celui d'un poids. Cela concerne 0,1 à 0,9 % de la masse de ΔW. C'est une question de mécanisme qui relève de P10 : elle ne porte ni sur le corps ni sur un aliasing.
- **Preuve** : backend_torch.py:160-162 (delta = sigmoid(diag) ; W_off = W * (1 - eye)) ; diag_share = 0.0091 (b_full), 0.0011 (b_zero), 0.0051 (b_const), 0.0044 (b_eplr), 0.0063 (b_tdonly)
- **Classe** : aucune
- **Verdict** : hors périmètre

## P9

### P9.a (DELEGUE) -- porte 20 sur la cible
- **Sonde** : `python tools/check_evidence_provenance.py --only C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/S2-BASSIN-FRAGILITY.json` ; `grep -n only tools/check_evidence_provenance.py`
- **Constat** : Verdict recopie : OK, exit 0. Mais cet OK ne porte pas sur la cible. La porte 20 ne parcourt que les records markdown de docs/EDR, et un --only qui ne designe aucun de ces fichiers ecarte tout le scan sans refuser : la sortie compte 304 records et 18 legataires, et zero ligne concerne la pre-inscription examinee. Le vert est vide, pas une verification de provenance. Dette de la porte : refuser un --only qui ne correspond a aucun record scanne (les portes 23 et 24 refusent deja un --only vide).
- **Preuve** : sortie : 'records : 304 | ... absents : 18 | non suivis : 0' puis 'OK : 18 chemin(s) legataire(s) gele(s)', exit=0 ; tools/check_evidence_provenance.py:240 (ne lit que docs/EDR), :86 (perimetre declare : docs/EDR/*.md), :362 (filtre --only sans refus quand rien ne correspond)
- **Classe** : E4
- **Verdict** : confirme

### P9.b -- provenance du results/ cite (question que la porte n'a pas pu trancher)
- **Sonde** : `git ls-files --error-unmatch results/s2_bassin_fragility_sonde_conception.json` ; `git cat-file -e HEAD:results/s2_bassin_fragility_sonde_conception.json` ; ls -la ce fichier ; `git ls-files --error-unmatch tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : La pre-inscription s'appuie sur un fichier de sondes de conception qu'elle dit versionne. Ce fichier est bien sur le disque, mais git ne le suit pas : il est absent de l'index et de HEAD. Un clone ne pourrait pas rouvrir les mesures de pre-scellement (rapports net/chemin, no-op, temoin de parallelisme). Meme chose pour le runner nomme dans les instruments autorises. Correctif : committer ces deux fichiers dans le MEME commit que le sceau. Les autres instruments cites sont suivis (5/5 plus NAISSANCES).
- **Preuve** : ls-files exit=1 ('did not match any file(s) known to git') ; cat-file exit=128 ('exists on disk, but not in HEAD') ; 34761 octets sur disque, 13:11 ; runner : NONSUIVI (git status '??') ; cible scratchpad/S2-BASSIN-FRAGILITY.json:26 (prevol_obligatoire) le declare suivi
- **Classe** : E27
- **Verdict** : confirme

### P9.c (DELEGUE) -- integrite du sceau
- **Sonde** : `python -c "from tools.preregister import verify; verify('S2-BASSIN-FRAGILITY')"` ; `python -c` calculant sha256(json.dumps(regle, sort_keys=True, ensure_ascii=False)) sur le fichier du scratchpad
- **Constat** : Verdict recopie : la verification leve FileNotFoundError, car aucune regle de ce nom n'existe dans docs/preregistrations. C'est l'etat attendu pour une revue qui doit preceder le sceau (reviewed_by exige parce que la regle declare un budget). On ne peut donc pas dire si le sceau est intact : il n'existe pas encore. Hash que produira le sceau pour ce contenu exact (formule _seal : sha256 du JSON trie, ensure_ascii=False) : 32f0c7701288e04cf226d8e0204a98ce3a1d6b52605193a4ae96c48ec495d972. Toute retouche avant le sceau changera ce hash, et la revue devra alors etre rejouee.
- **Preuve** : FileNotFoundError: aucune pre-inscription S2-BASSIN-FRAGILITY, exit=1 (tools/preregister.py:196) ; sceau projete 32f0c770...d972
- **Classe** : aucune
- **Verdict** : hors perimetre

## P10

### P10.a
- **Sonde** : `python -c` qui charge scratchpad/p418_W_*_2026.npz et imprime np.nonzero(|W_final-W0|.sum(axis=(0,1))) ; lecture de structure.col_mass_top10_nodes dans results/s2_bassin_fragility_sonde_conception.json ; `grep -n _MOVE_LOGITS src/agents/backend_torch.py`
- **Constat** : Le texte étend aux cinq bras un support de ΔW à onze colonnes. Le bras épisodique seul n'en déplace que huit, les logits de mouvement : sa perte ne lit que les huit premières sorties, et les colonnes 88, 89 et 92 (92 = tête de valeur, sortie 28) ne reçoivent du gradient que par le TD, coupé dans ce bras. La mesure de pré-scellement suivie contredit donc la phrase qui la cite. Le sham sign reste juste, puisqu'il suit le support réel, mais l'argument (3) et le rapport L1/L2 de 24 ne valent pas pour b_eplr (18,3 mesuré).
- **Preuve** : b_eplr : colonnes [64..71], soit 8 ; full, tdonly, const et zero : 11 (64-71, 88, 89, 92). Dans le JSON suivi, le top 10 de b_eplr finit par les nœuds 0 et 1, de masse nulle. backend_torch.py:478 base_move = out[:, :_MOVE_LOGITS] ; backend_torch.py:32 _MOVE_LOGITS = 8 ; backend_torch.py:35 _VALUE_NODE = 28 ; s2_bassin_fragility.py:63 b_eplr = td_enabled=False
- **Classe** : E9
- **Verdict** : confirmé

### P10.b
- **Sonde** : `grep -n 'ARMS = \|FAMILLE = \|assert_control_family\|_garde_e19(' tools/evo_runs/s2_bassin_fragility.py` ; sha256sum scratchpad/S2-BASSIN-FRAGILITY*.json ; `grep -o` comptant tdoff / DIRECTION_DEPEND_DU_PAS / cells=11 / cells=13 dans la cible et dans la v2
- **Constat** : La cible est octet pour octet la version v1 déjà revue. L'instrument qu'elle autorise a changé depuis : le runner sur disque compte six bras, une famille de 13 et une clause E19. Si on scelle ce texte tel quel, il déclare un alpha par cellule de 0,05/11, alors que fragility_verdict applique 0,05/13 et peut rendre une issue que la discrimination ne prévoit pas. De plus, les 66 phases 2 par seed et l'unité CPU de 1270 s ne comptent pas le rejeu de b_tdoff : avec six bras, c'est 77 phases 2. Le texte à revoir et à sceller est la v2, pas cette cible.
- **Preuve** : s2_bassin_fragility.py:55 : ARMS contient 6 bras, dont b_tdoff ; :76 FAMILLE = 13 ; :707 assert_control_family(cells=FAMILLE) ; :499 out['e19'] = _garde_e19(...). La cible a le sha256 9791ebbb…, identique à v1-revue ; on y compte tdoff 0, DIRECTION_DEPEND_DU_PAS 0, cells=11 1. La v2 (400e8f23…) donne tdoff 9, DIRECTION_DEPEND_DU_PAS 4, cells=13 1
- **Classe** : E23
- **Verdict** : confirmé

### P10.c
- **Sonde** : `sed -n 175,186p tools/evo_runs/s2_bassin_fragility.py` ; `grep -rn update_phenotype src tools` ; `grep -rn 'def W(self\|@W.setter' src` (0 ligne) ; `grep -n phenotype` dans world_1_stoneage.py add_agent
- **Constat** : Le corps reste bien celui du bassin, mais cela tient à la structure du code et non à l'assertion. En mode benchmark, le monde n'a ni HGT ni mitose, et aucun update_phenotype n'est appelé sur ce chemin. L'assertion, elle, compare le corps avant et après une simple affectation d'attribut, sans appel entre les deux : elle ne peut pas lever. Si add_agent ou from_genome recalculait un jour le corps, elle ne le verrait pas. Aucun effet sur le verdict aujourd'hui, mais le mot asserté surévalue la garde.
- **Preuve** : s2_bassin_fragility.py : le corps est capturé en :180 et comparé en :183, et entre les deux il n'y a que l'affectation de :182 (a.genome.W = ...). Le monde lit phenotype_* dans add_agent (world_1_stoneage.py:375, 388), appelé par phase2_survive_mortal, donc APRÈS l'assertion. world_1_stoneage.py:1878-1879 et :1657 : benchmark_mode coupe la reproduction
- **Classe** : E1
- **Verdict** : confirmé

### P10.d
- **Sonde** : `grep -n 'H\[:, :self.I\]\|CONDITION_GATE = \|H = H.detach' src/agents/backend_torch.py` ; `python -c load_bassin()` : N 172, I 59, O 108 ; `sed -n 160,200p tools/learning_events.py` ; `grep -n net_over_path tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : Trois affirmations sur le mécanisme tiennent à la lecture des lignes. Les 59 premiers nœuds, écrasés par les capteurs, pèsent bien 34 % de 172. Les logits 64 à 171 ne chevauchent pas les entrées, et le gate est éteint par défaut. Les deux crédits sont à un pas : H est détaché entre les pas. Enfin, le chemin est bien cumulé à chaque mise à jour, et le rapport net/chemin est un total divisé par un total.
- **Preuve** : backend_torch.py:159 (injection des capteurs), :200 (logits = H_new[:, N-O:N], soit 64:172), :48 (CONDITION_GATE = False), :475 (détachement dans learn_episode) ; learning_events.py:124 (somme de |ΔW| sur B×N×N), :173 et :187 (cumul) ; s2_bassin_fragility.py:338 (somme du net / chemin) ; 59/172 = 0,343
- **Classe** : aucune
- **Verdict** : non confirmé

---

## Addendum de l'auteur (session SCIENCE-HARNAIS, 2026-09-26) — suites données, brouillon relu → version v3

La revue ci-dessus porte sur le brouillon v1 (`S2-BASSIN-FRAGILITY.json` du scratchpad de session, sceau de brouillon
`32f0c770…`, cinq bras). La version soumise au sceau est la **v3**, qui traite chaque critique confirmée ci-dessous ; elle
est **relue à son tour** (`docs/reviews/2026-09-26-S2-BASSIN-FRAGILITY.v3.md`) avant tout sceau — P9.c avait raison : toute
retouche change le hash, la revue se rejoue.

**Exécution de cette revue (deux défauts de l'outil, contournés sans toucher aux prompts, corrigés depuis dans d1).**
(1) `.claude/workflows/refutateur.js` portait six U+FE0F invisibles : l'outil Workflow refusait de le lancer. Revue
exécutée depuis une copie identique à ces six caractères près (sha256 source `cb816d88…`, copie `d1d282f4…`) ; corrigé
dans d1 (`c0274ea9`). (2) Premier passage rendu NUL alors que les trois témoins à défaut étaient RETROUVÉS : le
vérificateur avait écrit `"refus": "\"\""` et `refutateur.js:222` lisait toute chaîne non vide comme un refus. Vérifié à
la main avant de reprendre : les quatre `--verifier` relancés rendent RETROUVÉ ×3 et MESURE ; `--plancher` rend 0/5 ; les
cinq réponses de calibration du juge concordent avec `--cas-du-juge-avec-reponses`. Seul le post-traitement de la copie a
été corrigé, puis le run repris sur cache (huit agents non relancés) ; corrigé dans d1 (`bfaea9c6`).

**Suites données aux critiques confirmées.**
- **P1.a (E8)** — monotonie érosion/amplitude héritée du chemin, contredite en net au pré-scellement : dite dans la
  question, les prédictions (« aucune monotonie n'est supposée ») et « ne tranche pas » ; la branche MIXTE_PAR_AMPLITUDE
  (11c) est déclarée HYPOTHÈSE testée, pas prémisse.
- **P1.b / P10.a (E8/E9)** — « 11 colonnes sur les cinq bras » faux pour b_eplr (8 colonnes, épisodique seul, sans la tête
  de valeur 92 ni 88/89) : corrigé dans la règle, le backlog et le runner ; L1/L2 publié par bras (24 full, 18,3 eplr).
- **P1.c / P9.b (E27)** — runner et mesures de conception non suivis : committés dans le MÊME commit que le sceau.
- **P3.b, P4.a, P4.b, P5.c, P6.e, P7.e, P10.b (E23/E8)** — règle v1 ≠ runner (six bras, E19, famille 13) : la v3 porte
  b_tdoff, `clause_E19`, la branche 10bis et la famille recomptée.
- **P4.c (E23)** — `c_zero` compté mais jamais lu : la famille compte désormais ce qui est LU — 14 contrastes (pos ; eps
  classe et contraste ; six classes sign ; cinq contrastes pour les bras dont le transplant érode, b_zero étant NEUTRE
  par réplication au bit de P4.9). Alpha par cellule 0,00357 ; 11/12 (0,0032) tient.
- **P5.a (E2)** — FRAGILE était le complément d'un test peu puissant : FRAGILE EXIGE maintenant que le sham ÉRODE ;
  « sham non ERODE et pas MOINS » devient NON_TRANCHE. Le scénario exact de la sonde p5 est gelé en test.
- **P5.b (E19)** — `pos` à 24-718× l'amplitude testée : sa limite est écrite dans la branche 7, et une ÉCHELLE du sham
  sign (×2, ×4, cinq tirages chacun) est publiée hors verdict, avec la première échelle qui érode par bras.
- **P5.d (E1)** — gardes calibrées du dépôt non appelées : `assert_not_degenerate` sur S_a (branche 3) ; la garde E19
  réelle ; le contrôle positif de DIRECTION (branche 9b) — plus la calibration propre du verdict (tests à réponse connue).
- **P6.a (E10)** — la bande de tirage n'était jamais confrontée au contraste : drapeau `dans_la_bande` par bras, et le
  verdict le DIT.
- **P6.b (E6) / P6.c (E1)** — `eps` isotrope, surtout inerte, jamais lu : `eps` est désormais le sham sign du ΔW de b_full
  à 1e-3, SUR SON SUPPORT ; il est le CONTRÔLE POSITIF de DIRECTION (9b : il doit être nettement moins érodé que le
  crédit complet) et, s'il érode, le verdict est CRETE_A_TOUTE_ECHELLE (9a).
- **P7.a (E10)** — la dose n'était pas engagée par le sceau : td_updates, episode_updates et resurrections sont
  PUBLIÉS par cellule et font partie de la réplication au bit (branche 4).
- **P7.b** — létalité de phase 1 (×18 entre bras, anticorrélée au net) : publiée par bras dans le verdict et nommée comme
  covariable confondue dans « ne tranche pas ».
- **P8.a (E5)** — canal de consensus social (logits = vue de H réécrite par le vote, nœuds 77-78 hors support) : nommé dans
  « ne tranche pas », et MESURÉ au lieu d'être laissé en dette — chaque phase 2 publie ses réécritures de logits par le
  vote (`compter_consensus`, enveloppe de classe neutre, vérifiée par le no-op au bit en test sur monde réel).
- **P9.a (E4)** — portes 19 et 20 : un `--only` qui ne désigne aucun record rend OK sans rien juger ; dette d'outillage,
  remontée à Master 2 (hors du gel méthodologique de cette session).
- **P10.c (E1)** — l'assertion de corps ne pouvait pas échouer : le corps est désormais confronté, avant ET après chaque
  phase 2, au corps du bassin calculé indépendamment (`phenotype_of`) ; un témoin gelé la fait lever par un
  `update_phenotype` sur le W posé.

Critiques non confirmées ou hors périmètre : sans suite (P2, P3.a, P4.d, P4.e, P6.d, P7.c, P7.d, P8.b, P8.c, P8.d,
P9.c, P10.d).

**⚠ À lire avec le score** : le témoin cru sain rend 6 critiques recevables, autant que le moins retrouvé des défauts —
l'instrument est INDISCRIMINANT sur ce passage : il ne sépare pas un record sain d'un défectueux. Les 20 critiques
confirmées ont été vérifiées une à une contre le code et les JSON avant d'être suivies ; aucune n'a été acceptée sur la
seule foi de la revue.
