# Revue adversariale : S2-BASSIN-FRAGILITY v5 (pré-inscription, avant sceau)

- **Cible** : `C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/S2-BASSIN-FRAGILITY.v5.json`
- **Date** : 2026-09-26
- **SHA** : `82927108f6244537bee0a35d44fa06dcf36cea03` (worktree `.worktrees/science`, branche tmp/science)
- **Résultat des TÉMOINS** (avec les deux planchers, sur les mêmes lignes) :
  - S2-BLIND-CHAMPION-42e9357 : RETROUVE, code 0, 9 recevables — PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 ; plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1)
  - EDR-GRAB-COST-1828371 : RETROUVE, code 0, 7 recevables — PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 ; plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1)
  - EDR-RETAIN-COMPOSE-4204f8f : RETROUVE, code 0, 7 recevables — PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 ; plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1)
  - LOCK-002-286f244 (témoin cru sain) : MESURE, code 0, 6 recevables — PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 ; plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1)
  - Fichiers de critiques : `.../scratchpad/refutateur_v5/critiques-<témoin>.json`. Commande de vérification :
    `PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier <témoin> <critiques.json> --extrait <scratchpad>/temoins/temoin-N.md [--jugement OUI]`
    (témoin-1 : S2-BLIND-CHAMPION, témoin-3 : EDR-GRAB-COST, témoin-4 : EDR-RETAIN-COMPOSE avec `--jugement OUI` ; témoin-2 : LOCK-002 sans jugement).

**Bilan** : 36 critiques, dont **17 confirmées**.

---

## P1 — prémisses

### P1.a (JUGE) — prémisse porteuse de la lecture DIRECTION (11b) et de son remède
- **Sonde** : `grep -n -o "normes et support IDENTIQUES" S2-BASSIN-FRAGILITY.v5.json ; grep -n -o "pas la même norme d'OPÉRATEUR" S2-BASSIN-FRAGILITY.v5.json ; grep -n op_ratio tools/evo_runs/s2_bassin_fragility.py ; grep -o -iE '"[a-z_]*(op|spectral|norm|operat)[a-z_]*"' results/s2_bassin_fragility_sonde_conception.json | sort | uniq -c`
- **Constat** : le remède associé à DIRECTION (ancrer le crédit au bassin) suppose que crédit et tirage de signes ne diffèrent que par l'orientation. Or l'écart n° 3 de la même règle admet que la norme spectrale du crédit dépasse celle du tirage de 7 à 50 %. Ce chiffre ne figure dans aucun fichier suivi : il vient d'une sonde de revue lancée sur des npz du scratchpad. Pendant le run, le rapport sera calculé mais aucune branche ne le lira. Un simple excès d'amplitude effective peut donc produire DIRECTION, et le remède devrait alors être celui de 11a (le pas, le clip), pas l'ancre. La correction v3 P1.4 est entrée dans l'écart (3), mais le libellé de 11b n'a pas été amendé.
- **Preuve** : S2-BASSIN-FRAGILITY.v5.json:10 (normes « IDENTIQUES ») opposé à v5.json:24 (norme d'opérateur ×1,07 à ×1,50) ; seule source : docs/reviews/2026-09-26-S2-BASSIN-FRAGILITY.v3.md:53 (python scratchpad/p1_opnorm.py, npz non suivis ; 1,33/1,50/1,28/1,13/1,07) ; tools/evo_runs/s2_bassin_fragility.py:164, unique occurrence de op_ratio (calculé, jamais lu par fragility_verdict) ; sonde de conception : 0 clé de norme d'opérateur (seules correspondances : noop ×2, trace_bypass_optimizer ×5).
- **Classe** : E8
- **Verdict** : confirmé

### P1.b (JUGE) — le plancher S_c qui entre dans la saturation
- **Sonde** : `python -c` (charge results/s2_credit_retention.json, s2_credit_ablation.json, s2_credit_ablation_2.json ; compte S_tr < S_c par bras ; recalcule la saturation contre min(S_c, S_full, S_tdoff, S_neg, S_tdonly) par seed) ; `grep -n "S_c\|cold_floor" tools/evo_runs/s2_bassin_fragility.py` ; `grep -n floor tools/evo_runs/s2_credit_retention.py`
- **Constat** : S_c n'est pas mesuré par ce run : cold_floor le relit dans P4.4, une cohorte froide sans bassin. Les JSON publiés contredisent son rôle de plancher. La greffe de b_tdoff tombe sous S_c sur 7 seeds sur 12, celle de b_full sur 3, celle de b_tdonly sur 1. P4.4 déclarait d'ailleurs son propre plancher à 9,0, au-dessus de la médiane de S_c (7,5). Avec comme plancher le minimum par seed des bras publiés, la saturation médiane vaut 0,993 pour b_tdoff et 0,635 pour b_eplr : la garde E19 reste illisible et aucune lecture ne bascule. La prémisse est héritée et mal nommée, mais elle ne porte pas le verdict.
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:283-284 (cold_floor = S_c de P4.4) ; tools/evo_runs/s2_credit_retention.py:45 (FLOOR = 9.0) contre S_c_median 7,5 ; sortie : tdoff S_tr<S_c 7/12, full 3/12, tdonly 1/12, saturation > 1 sur 7/12 (tdoff) ; saturation au plancher empirique : tdoff 0,993, eplr 0,635.
- **Classe** : E8
- **Verdict** : confirmé

### P1.c (JUGE) — b_const peut-il atteindre MOINS ? (départage 11b / 11d)
- **Sonde** : `python -c` (d = S_bras − S_a trié par seed pour const, eplr, tdonly, full, tdoff ; d_zero par seed ; ligne du seed 2035) ; `grep -c 2035 S2-BASSIN-FRAGILITY.v5.json` ; `grep -n 2035 docs/reviews/2026-09-26-S2-BASSIN-FRAGILITY*.md`
- **Constat** : pour sortir 11b, il faut MOINS sur b_const, donc un contraste positif au seed 2035. Sur ce seed, la greffe ne coûte que 2,5 ticks au no-op (42,0 contre 39,5). La revue v4 avait chiffré cette marge ; la v5 l'a perdue et ne cite plus que le seed 2036. Aucune survie de tirage n'a été mesurée avant le sceau. Le seul ordre de grandeur publié est b_zero : un ΔW net de 3,4 par agent au seed 2026, huit fois moins que b_const (28,0), qui déplace pourtant la survie de −8,5 à +2 ticks, et d'au moins 5 ticks sur 5 seeds. L'issue globale prédite comme la plus probable se joue donc sur un seul seed, avec une marge plus étroite que ce bruit publié, et le texte n'en dit rien.
- **Preuve** : sortie : d_const trié [−28,0 … −10,0, −2,5, +10,5], seed 2035 S_a 42,0 / S_const 39,5 ; d_zero [−8,5, −7,5, −7,5, −7,0, −5,0, −1,0, −0,5, −0,5, 0, 0, +0,5, +2,0] ; grep -c 2035 sur la v5 = 0 ; docs/reviews/2026-09-26-S2-BASSIN-FRAGILITY.v4.md:121 (marge de 2,5 ticks déjà mesurée).
- **Classe** : E2
- **Verdict** : confirmé

### P1.d (JUGE) — prémisses chiffrées héritées de P4.4/P4.9/P4.16 et de la sonde de conception
- **Sonde** : `python -c` sur les rows et verdicts de s2_credit_retention.json, s2_credit_ablation.json, s2_credit_ablation_2.json, et sur les cellules de s2_bassin_fragility_sonde_conception.json
- **Constat** : toutes les valeurs héritées vérifiées se recalculent à l'identique depuis les JSON suivis. Aucun défaut ici.
- **Preuve** : S_a médiane 36,0 (étendue 17-50). Résurrections médianes : tdoff 3,5, tdonly 8, full 10, eplr 16,5, const 65,5, zero 179. Chemin tdoff/eplr : médiane 1,363 (0,828 à 2,838 ; seed 2027 à 0,828). Masse ×7,34. Saturation tdoff 1,017. Seed 2036 : const +10,5, eplr 0,0. eplr > tdoff en résurrections sur 12/12. Chemin tdoff 101,3 par agent. Classes de greffe : zero NEUTRE (8/12, −0,75), const et eplr ERODE à 11/12 exactement. Déplacement net médian : full 100,5, tdonly 73,0, const 28,0, eplr 18,6, zero 3,4. Réplications, greffes et corps inchangés : vrai sur les 5 bras.
- **Classe** : aucune
- **Verdict** : non confirmé

## P2 — régime (DÉLÉGUÉ, porte 19)
- **Sonde** : `python tools/check_regime_claims.py --only <scratchpad>/S2-BASSIN-FRAGILITY.v5.json` ; puis `python -c 'from tools.check_regime_claims import analyze; ...'` (clés du périmètre) ; `git merge-base --is-ancestor 3c9414f6 HEAD` ; `git show 3c9414f6:tools/check_regime_claims.py` rejoué avec `--root .` sur la même cible (sans pipe, pour lire le vrai code de sortie)
- **Constat** : la porte 19, telle qu'elle existe sur tmp/science, a rendu OK avec sortie 0, mais ce OK ne porte pas sur la pré-inscription. La porte ne lit que les records docs/EDR/*.md : sur les 304 records balayés, aucune clé ne contient S2-BASSIN-FRAGILITY. Le filtre --only n'a donc désigné aucun record, et recopier ce OK comme réponse de P2 reviendrait à donner pour valide une vérification qui n'a pas eu lieu. Le correctif P2.128 (3c9414f6) fait refuser ce cas, mais il n'est pas un ancêtre de HEAD (82927108). Rejouée depuis ce commit, la même commande sort en REFUS, code 2. Conséquence : P2 n'a pas de réponse sur cette cible. Les valeurs de régime que cite la pré-inscription ne sont confrontées à aucun results par cette porte, et ne le seront qu'une fois le record EDR écrit. Aucune DISCORDE n'est affirmée contre la cible.
- **Preuve** : sortie de la porte sur tmp/science : 'records : 304 | {SANS_PARAMETRE: 227, CONCORDE: 6, CONCORDE_HORS_REGIME: 7, SANS_RESULTS: 52, SANS_REGIME: 3, SANS_VALEUR_LUE: 6, DISCORDE: 3}', puis 'OK : 64 record(s) ... Aucun nouveau, aucune regression.', exit=0. Balayage du périmètre : 304 records, préfixes ['docs/EDR'], 0 clé contenant la cible. Ancestry : 3c9414f6 ABSENT de HEAD 82927108. Porte rejouée depuis 3c9414f6 : 'REFUS : --only designe 1 chemin(s) INCONNU(S) de cette porte', exit=2.
- **Classe** : E4 (vérification vide : un OK que rien ne distingue d'un succès)
- **Verdict** : confirmé

## P3 — balayage du pas (DÉLÉGUÉ, porte 23)
- **Sonde** : `python tools/check_e19_optimizer_sweep.py --only tools/evo_runs/s2_bassin_fragility.py ; echo EXIT=$?` ; puis `python -c "from tools.preregister import path_for; import os; print(os.path.exists(path_for('S2-BASSIN-FRAGILITY')))"`
- **Constat** : porte 23 verte sur le runner de P4.18 : il invoque lui-même la garde d'invariance au pas (appel réel dans _garde_e19), donc aucun nul comparatif sous gradient n'échappe au balayage. Le classement [regle_absente], nouveau et non bloquant, vient seulement de ce que la règle n'est pas encore scellée dans docs/preregistrations (la v5 vit dans le scratchpad) : c'est la pire des deux étiquettes cumulées (couvert + règle absente), pas un défaut. Après le sceau, relancer la porte : le runner doit passer à couvert et entrer dans la liste gelée des appelants au prochain --update-baseline. La question de la référence à pas nul du MÊME dispositif relève de P5, pas d'ici.
- **Preuve** : EXIT=0, 'OK : aucun nouveau runner sous gradient sans garde E19, aucune regression, aucune perte d'appelant' ; compteurs 34 scellés / 12 sous gradient / 9 nus / 4 indéterminés / 6 non résolus / 1 règle absente / 3 appelants de la garde / 19 gelés ; runner listé NOUVEAU [regle_absente]. Appel réel : tools/evo_runs/s2_bassin_fragility.py:558 (import :539, verify(PREREG) :1088, PREREG :64). Sceau absent : docs/preregistrations/S2-BASSIN-FRAGILITY.json, exists False. Runner stagé (git status : A).
- **Classe** : E19
- **Verdict** : non confirmé

## P4 — famille de contrôles et seuils

### P4.a (JUGE) — taille réelle de la famille
- **Sonde** : `python tools/check_control_family.py --only tools/evo_runs/s2_bassin_fragility.py` ; `python -c "from tools.evo_runs.s2_bassin_fragility import published,_classer,ARMS; ..."` (classes des greffes publiées contre a_frozen, sign_min=11, delta_min=5)
- **Constat** : décompte fait dans fragility_verdict : pos (1), eps en classe (1) et en contraste contre la greffe complète (1), classes du sham sign sur les six bras (6), contrastes sham−greffe lus seulement pour les bras dont la greffe érode (5). Total 14, égal à la constante codée en dur. Le nombre de contrastes lus dépend des données, mais il est fixé d'avance, car la réplication au bit impose les survies publiées : full 12/12, tdonly 12/12, const 11/12, eplr 11/12, tdoff 12/12 érodent ; zero reste NEUTRE (8 négatifs, médiane −0,75). iso, échelles ×2/×4 et qualificatifs ne changent aucune lecture.
- **Preuve** : porte : scelle=True declare=True, exit 0 ; tools/evo_runs/s2_bassin_fragility.py:84 (FAMILLE = 14), :617-660 (lectures), :519-527 (c lu seulement si greffe ERODE) ; sortie : b_zero ('NEUTRE', 2, 8, -0.75), les cinq autres ERODE.
- **Classe** : E23
- **Verdict** : non confirmé

### P4.b (JUGE) — sensibilité du seuil au compte
- **Sonde** : `python -c "from tools.evo_runs.s2_bassin_fragility import seuil_tient; [print(f, seuil_tient(10,12,f)[0], seuil_tient(11,12,f)[0]) for f in (1,2,3,14,15,16)]"`
- **Constat** : une erreur de une ou deux cellules dans le compte ne changerait pas la barre. 11/12 tient pour toute famille de 3 à 15 et ne tombe qu'à partir de 16. 10/12 ne serait admissible que jusqu'à 2 cellules. Le lien entre le compte et le seuil est donc robuste.
- **Preuve** : f=2 True/True ; f=3 False/True ; f=15 False/True ; f=16 False/False (queue 11/12 = 0,003174 contre 0,05/16 = 0,003125).
- **Classe** : E23
- **Verdict** : non confirmé

### P4.c (JUGE) — seuil hérité d'un autre dispositif : harness_min
- **Sonde** : `grep -n HARNESS_MIN tools/evo_runs/s2_credit_retention.py` ; `python -c` (médiane et bornes des S_a publiés a_frozen, seeds 2026-2037)
- **Constat** : le plancher de 20 ticks de la branche 3 vient de P4.4. Là-bas, S_a était une mesure nouvelle. Ici, la branche 2 exige que les âges du no-op soient identiques au bit à a_frozen publié : S_a est donc connu avant le run (médiane 36,0, étendue 17 à 50). Une fois la branche 2 passée, la branche 3, y compris le test de dégénérescence, ne peut plus basculer : c'est une cellule morte. Et la note sur les seuils ne signale comme hérité que delta_min, pas celui-ci.
- **Preuve** : tools/evo_runs/s2_credit_retention.py:46 (HARNESS_MIN = 20.0, bassin WARM-003) ; tools/evo_runs/s2_bassin_fragility.py:457 et :714 (noop_identical exigé avant la branche 3, :719-727) ; médiane 36.0, min 17.0, max 50.0.
- **Classe** : E1
- **Verdict** : confirmé (mineur : contrôle inerte, sans biais de lecture)

### P4.d (JUGE) — cellule E19 hors famille
- **Sonde** : `python -c "from tools.evo_runs.s2_bassin_fragility import published,cold_floor; ..."` (saturation médiane |S_tr−S_a|/(S_a−S_c) de b_tdoff et b_eplr sur les publiés)
- **Constat** : le réétiquetage DIRECTION_DEPEND_DU_REGLAGE est une affirmation émise hors de la correction de Bonferroni. Mais il n'est pas atteignable : la saturation de b_tdoff se calcule entièrement sur des valeurs publiées (S_a, S_tr, S_c), que les branches 2, 4 et 5 imposent au bit, et elle vaut 1,017, au-dessus de 0,9. La garde est donc illisible avec certitude dans tout run qui arrive en 10bis. L'exclure de la famille ne coûte rien. En revanche, écrire « très probablement illisible » sous-estime la situation : c'est une certitude.
- **Preuve** : b_tdoff 1.0170 (n=12), b_eplr 0.6489 ; tools/evo_runs/s2_bassin_fragility.py:547 et :564 (saturés -> lisible=False, aucun réétiquetage :769).
- **Classe** : E1
- **Verdict** : confirmé (mineur : formulation probabiliste d'un fait déterminé ; aucune inflation de famille)

### P4.e (JUGE) — contrôle d'appariement appliqué à chaque cellule
- **Sonde** : `python -c "import numpy as np; from tools.evo_runs.s2_credit_retention import load_bassin; W0=...; print(np.spacing(np.abs(W0)).sum()/2 / 0.08865)"` (borne) + Monte-Carlo lognormal sur les 11 colonnes
- **Constat** : la branche 6 applique une tolérance unique de 1 % à environ 18 000 vérifications par agent (12 seeds × 125 tirages × 12 agents). C'est la forme E23. Mais l'écart n'y est pas aléatoire, il ne vient que de l'arrondi float32. Même en bornant au pire sur la matrice entière du bassin, il reste sous 0,12 % de la L1 eps du plus petit agent du seed 2026, avec une marge de ×8. La fausse alarme est nulle sur un harnais correct. Seule réserve : la borne ne tiendrait plus pour un agent dont le déplacement net de b_full serait inférieur à 10,5, cas non mesuré hors du seed 2026.
- **Preuve** : borne matrice entière 1.05e-4 -> 0.00119 relatif ; 11 colonnes 1.07e-4 relatif ; Monte-Carlo max 1.07e-5 ; L1 nette min par agent 88.65 (results/s2_bassin_fragility_sonde_conception.json, b_full seed 2026) ; MATCH_TOL 0.01 (s2_bassin_fragility.py:92).
- **Classe** : E23
- **Verdict** : non confirmé

## P5 — contrôles positifs et gardes

### P5.1
- **Sonde** : `python scratchpad/p5_v5_e19.py` (published(), cold_floor() et _garde_e19 du runner ; 59536 combinaisons de médianes de sham et de lectures pour la paire tdoff/eplr ; aucun monde)
- **Constat** : la garde de pas ne peut pas réétiqueter dans ce run. Ce n'est pas une probabilité : c'est calculable avant le sceau. Sa lisibilité dépend de la saturation de b_tdoff, fonction de S_a, S_tr et S_c seulement. Les branches 2 et 5 forcent les deux premiers à égaler le publié, et le troisième vient de P4.4. Or chacun des douze seeds de b_tdoff dépasse déjà 0,9. Toute issue qui atteint 10bis rend donc une garde muette, et l'étiquette DIRECTION_DEPEND_DU_REGLAGE de 11c/11d est du code mort. Une lecture DIRECTION de b_eplr (pas 0,004) sortirait sans défense de pas, alors que le runner compte comme appelant réel pour la porte 23. Remplacer « très probablement » par « certainement » et ne plus présenter 10bis comme une branche qui peut tomber.
- **Preuve** : saturation b_tdoff par seed = 1.021, 1.0, 1.028, 1.016, 0.986, 1.018, 1.018, 0.966, 1.024, 0.957, 1.1, 0.946 (minimum 0,946 > seuil 0,9), médiane 1,017 ; combinaisons 59536, garde LISIBLE 0. Code : tools/evo_runs/s2_bassin_fragility.py:547, :564, :769.
- **Classe** : E1 (volet E19 : garde de pas appelée sur une paire qu'elle ne peut pas lire)
- **Verdict** : confirmé

### P5.2
- **Sonde** : `python -c` qui importe tests/sandbox/test_s2_bassin_fragility.py (_rows) et appelle R.fragility_verdict(_rows(S_eps=S_A_DEFAUT, sign=S_a pour les six bras)), puis compte « eps » dans why ; `grep -n controle_direction_non_eprouve tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : le correctif de v4 P5.3 est un champ écrit et jamais relu. Si eps égale exactement le no-op sur les douze seeds (le cas que la règle prédit elle-même pour eps), 9b passe en miroir de la branche 8 et le verdict rend LU DIRECTION. La phrase why ne mentionne alors ni eps ni le témoin non éprouvé, alors que la bande, la saturation et le plancher eps y sont ajoutés. La règle annonce que le verdict le dit ; seul un booléen enfoui dans controles.eps le porte. De plus, le drapeau exige l'égalité sur 12/12 : avec 11 seeds identiques sur 12, 9b reste presque entièrement un miroir et le drapeau vaut faux.
- **Preuve** : eps = S_a (12/12) -> LU DIRECTION, non_eprouve True, 9b passe 12/12 ; why : 0 occurrence de « eps », 0 de « prouv » ; eps = S_a sur 11/12 -> LU DIRECTION, non_eprouve False. Une seule occurrence, tools/evo_runs/s2_bassin_fragility.py:630 (écriture), aucune lecture ; why construit à :790-796 sans ce drapeau.
- **Classe** : E1
- **Verdict** : confirmé

### P5.3
- **Sonde** : `grep -n 'assert_positive_control|assert_not_degenerate|assert_ablation_changes_something' tools/evo_runs/s2_bassin_fragility.py` ; `python -c` qui charge published('a_frozen', s) pour s = 2026..2037, appelle assert_not_degenerate et compare la médiane à HARNESS_MIN
- **Constat** : le runner n'appelle qu'une garde calibrée du trio, la non-dégénérescence (:720). Elle porte sur S_a, que la branche 2 oblige à égaler au bit l'a_frozen publié : la branche 3 est jouée d'avance et ne peut plus tomber. Le risque qu'elle prétend couvrir, des tests de signe dégénérés faute de dispersion, concerne les grandeurs neuves (S_sign, S_eps, contrastes c) ; aucune garde de dispersion n'y est posée. Ni contrôle positif ni ablation-qui-change ne sont appelés ; les contrôles positifs restent codés à la main (branches 7 et 9b).
- **Preuve** : assert_not_degenerate seul, :582 (import) et :720 (appel sur S_a) ; 0 assert_positive_control, 0 assert_ablation_changes_something. S_a publiés [31.5, 35.5, 44.5, 39.0, 42.5, 35.5, 36.0, 36.0, 50.0, 42.0, 17.0, 26.5], médiane 36,0 >= 20, étendue 33 -> la garde passe ; égalité imposée par :457 et :714.
- **Classe** : E1
- **Verdict** : confirmé

## P6 — bruit et bandes

### P6.a — la bande de demi-tirages face à un nul connu
- **Sonde** : `python scratchpad/p6_v5_sonde.py` (partie b : importe _bande_contraste du runner, 4000 réplicats par sigma, contraste vrai = 0)
- **Constat** : la bande de demi-tirages, introduite pour répondre à la v4, n'a jamais été confrontée à un contraste nul connu. Rejouée sur un sham inerte par construction (contraste vrai nul, 12 seeds, 5 tirages bruités arrondis au demi-tick), elle déclare ce nul HORS de sa propre bande dans 14 à 29 % des cas quand l'écart-type des tirages va de 1 à 4 ticks. Sur les six contrastes qui en portent une (cinq c et 9b), la probabilité qu'au moins un nul soit présenté comme distinguable de zéro atteint environ 0,82, en supposant les contrastes indépendants. Le drapeau publié se trompe donc dans le sens qui fabrique un signal. Les tests ne contrôlent que l'arithmétique sur des valeurs fixes : ils ne mesurent aucun taux sous le nul.
- **Preuve** : sigma 1.0 -> nul DANS la bande 0.861 ; sigma 2.0 -> 0.753 ; sigma 4.0 -> 0.707 (bande exactement nulle 0.176 / 0.077 / 0.038) ; 1 - 0.753^6 = 0.82 ; tools/evo_runs/s2_bassin_fragility.py:493-500 ; tests/sandbox/test_s2_bassin_fragility.py:392-396 et :475-478 (entrées fixes).
- **Classe** : E4
- **Verdict** : confirmé

### P6.b — contrastes voisins sans bande
- **Sonde** : `grep -n "_classer(\|bande_c\b\|\"bande_contraste\"\|bc = _bande" tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : le plancher de tirage n'accompagne que deux contrastes : sham moins greffe, et 9b. Les six classes du sham contre le no-op (six cellules de la famille de 14) ne portent aucune bande, pas plus que les classes d'eps et de pos contre S_a. Or ce sont elles qui séparent FRAGILE (le sham érode) de DIRECTION (il n'érode pas) et qui déclenchent 9a. Le bruit de tirage de S_sign entre pourtant dans S_sign - S_a exactement comme dans c. La garde ajoutée pour c n'a pas été étendue aux contrastes voisins, qui portent la même incertitude.
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:618 (eps/pos contre S_a : classe seule) et :645 (sham contre S_a : classe seule) ; bande calculée seulement en :622 (9b) et :651/:658-659 (c).
- **Classe** : E14
- **Verdict** : confirmé

### P6.c — bande chaotique déclarée « measured »
- **Sonde** : `grep -rn chaotique tools/evo_runs/s2_bassin_fragility.py tests/sandbox/test_s2_bassin_fragility.py ; grep -c chaotique scratchpad/S2-BASSIN-FRAGILITY.v5.json`
- **Constat** : à l'agrégation, le design déclare « measured » une bande chaotique qui viendrait d'eps. Aucune ligne du runner ne la calcule et aucun champ ne la publie. Aucun contraste ne lui est comparé, et la règle v5 ne la nomme nulle part. Dans le code, eps sert seulement au test de crête et au contrôle positif de DIRECTION. Un lien marqué mesuré alors que rien ne le mesure, c'est justement ce que declare_design devait interdire.
- **Preuve** : une seule occurrence : tools/evo_runs/s2_bassin_fragility.py:974 (le lien déclaré) ; 0 dans les tests ; 0 dans la règle v5.
- **Classe** : E8
- **Verdict** : confirmé

### P6.d — dénominateur de saturation hérité
- **Sonde** : `python scratchpad/p6_v5_sonde.py` (partie a : S_a de P4.16, S_c de P4.4, S_tr publiés)
- **Constat** : le dénominateur de la saturation vient de P4.4 et non de ce dispositif, et il passe sous le seuil sur plusieurs seeds. Mais c'était déjà relevé en v4, et le verdict n'en dépend pas : b_tdoff est à 0,9 ou plus sur 12/12 seeds, donc la garde E19 est illisible quel que soit le bruit de S_c. La saturation ne change aucune lecture.
- **Preuve** : b_tdoff sat 0.95-1.10, S_tr<S_c 7/12, sat>=0.9 12/12 ; b_full 3/12 sous S_c ; docs/reviews/2026-09-26-S2-BASSIN-FRAGILITY.v4.md:35-37 et :172.
- **Classe** : aucune
- **Verdict** : non confirmé

### P6.e — position des contrastes publiés dans leur bande
- **Sonde** : `python -c` qui liste les clés de results/s2_bassin_fragility_sonde_conception.json
- **Constat** : on ne peut pas encore situer un contraste publié par rapport à sa bande. Avant le sceau, aucune survie sous sign, iso, eps ni pos n'a été mesurée. Le no-op de phase 2 rend a_frozen au bit, avec un bruit nul, mais il ne dit rien des contrastes de sham. La comparaison devra être faite dans le record, après le run.
- **Preuve** : ['W_sonde_sha256', '_comment', 'sonde_net_chemin', 'sources', 'temoin_parallelisme'] : aucune cellule de sham.
- **Classe** : aucune
- **Verdict** : hors périmètre

## P7 — dose

### P7.1 (JUGE) — nul d'apprentissage ou nul de létalité ?
- **Sonde** : `python <scratchpad>/p7v5_confound.py` ; `sed -n 765,797p tools/evo_runs/s2_bassin_fragility.py` ; recevabilité vérifiée par scratchpad/p7v5_recev.py (1 recevable, 0 rejet, seuil 8 mots)
- **Constat** : la branche 11c impute à l'amplitude nette un partage des bras que la mortalité de phase 1 produit aussi bien. Le partage que la règle annonce elle-même (full et tdonly fragiles, const et eplr orientés) classe aussi les bras par nombre de morts : 8 à 10 résurrections d'un côté, 16,5 à 65,5 de l'autre, sans chevauchement. Si b_tdoff, le bras qui meurt le moins, sort FRAGILE avec un net supérieur à 28, la confusion devient totale. Le runner ne compare que les nets, son motif de verdict tait les résurrections, et le nom PAR_AMPLITUDE est gardé alors que l'étiquette de la garde E19 a été corrigée pour nommer ce facteur. Or la mortalité agit sur l'issue : dans b_tdonly, plus un seed a de morts, moins sa greffe érode. Un MIXTE_PAR_AMPLITUDE, et l'ancre qu'il recommande sous un seuil d'amplitude, pourraient donc traduire un effet de mortalité jamais séparé.
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:782-784 (11c ne teste que net_l1_median_agent) et :791-793 (why sans résurrections) contre :709 (étiquette E19 : pas et létalité non séparés). Split fr=[full,tdonly] di=[const,eplr] -> létalité séparée à l'identique True (max res fr 10.0 < min res di 16.5) ; tdoff net=35 FRAGILE -> 11c=True, même partition par létalité=True ; intra-bras tdonly spearman(résurrections, S_appris - S_a) = +0.75 (p=0.005).
- **Classe** : E8
- **Verdict** : confirmé

### P7.2 (JUGE) — dose publiée et cohorte constante
- **Sonde** : `python scratchpad/p7v5_dose.py ; python scratchpad/p7v5_dose3.py ; sed -n 117,165p tools/evo_runs/s2_credit_retention.py`
- **Constat** : aucun défaut. Pour chacun des six bras, les compteurs de phase 1 (TD, épisodique, résurrections, chemin) existent dans les 72 cellules publiées, et la branche 4 les exige au bit. Le lot reste à 12 pendant toute la phase 1. La phase 2 tourne à poids gelés, le gel est asserté et chaque condition publie ses censurés : aucun nul de phase 2 ne peut cacher un apprentissage. Pour b_full, 11 seeds sur 12 sont importés de P4.4 par un compteur plus ancien. P4.16 a rejoué le seed 2026 et retrouvé la ligne de P4.4 au bit, ce qui rend peu probable un échec de réplication propre à ces imports.
- **Preuve** : td None 0, ep None 0, res None 0 sur les 6 bras × 12 seeds ; td ∈ {1999, 0}, ep ∈ {250, 0}. tools/evo_runs/s2_credit_retention.py:163 (assert dW_abs_sum == 0.0) ; tools/evo_runs/s2_bassin_fragility.py:360 (censored publié). dW de P4.4 b_warm_credit 2026 = 18242.03954219818 = dW de P4.16 b_full 2026.
- **Classe** : aucune
- **Verdict** : non confirmé

### P7.3 (JUGE) — ticks dans la dose répliquée
- **Sonde** : `sed -n 453,480p tools/evo_runs/s2_bassin_fragility.py ; python scratchpad/p7v5_dose2.py`
- **Constat** : dans « mesure », la règle compte les ticks dans la dose qui doit égaler le publié au bit, mais le runner ne les compare pas. L'écart est sans effet : la recharge remet chaque mort dans la liste à chaque tick, donc la boucle ne peut pas s'arrêter avant 2000, et les 72 cellules publiées valent 2000.
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:466-470 (dW, âges, td, ep, résurrections : pas ticks) ; tools/evo_runs/s2_credit_retention.py:111,132-135 ; ticks = [2000] sur les 6 bras.
- **Classe** : aucune
- **Verdict** : non confirmé

## P8 — canaux d'identité, corps, vues

### P8.a (JUGE) — chevauchement entrée/sortie
- **Sonde** : `python tools/check_io_overlap.py ; python scratchpad/p8_v5_sonde.py ; grep -n savez tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : sur le bassin DAgger, le bloc des capteurs et le bloc des logits sont séparés. Les capteurs occupent les nœuds 0 à 58, les sorties commencent au 64, et cinq nœuds cachés les séparent. Aucune édition de W, sham ou greffe, ne peut donc réécrire l'observation dans une sortie. Les W appris seront persistés sous results/, hors du périmètre de la porte 17. Mais le npz porte num_inputs et num_outputs, et load_bassin vérifie le chevauchement à chaque chargement.
- **Preuve** : 358 génomes persistés, 10 chevauchants (10 connus, 0 nouveau), OK, exit 0. N 172, I 59, O 108, N-O 64, overlap 0. tools/evo_runs/s2_credit_retention.py:61 ; tools/evo_runs/s2_bassin_fragility.py:349-350 ; tools/check_io_overlap.py:13-14.
- **Classe** : E24
- **Verdict** : non confirmé

### P8.b (JUGE) — corps dérivé des lignes 0:10 de W
- **Sonde** : `python scratchpad/p8_v5_sonde.py` (part de |ΔW| dans les lignes 0:10 par bras) ; `grep -n 'absorb_knowledge|update_phenotype()|new_agents.append' src/worlds/world_1_stoneage.py` ; `sed -n 1870,1900p` et `1640,1668p` du monde
- **Constat** : toutes les interventions écrivent bien dans les lignes 0 à 9 de W, où le monde lit le corps. Mesuré sur le seed 2026, ces lignes portent 3,1 à 5,7 % de |ΔW| selon le bras. Mais le monde ne relit le corps qu'à trois endroits : deux copies prises à l'ajout de l'agent, et une lecture de l'attribut du modèle à chaque tick. La garde contrôle les objets mêmes que le monde utilise. Les chemins du monde qui réécrivent W et recalculent le corps (absorption de savoir, HGT, reproduction) sont tous coupés, parce que le mode benchmark est forcé.
- **Preuve** : body_rows 0,0340 (full), 0,0351 (tdonly), 0,0482 (const), 0,0573 (eplr), 0,0308 (zero). world_1_stoneage.py:375 et :388 (copie à l'ajout) ; :702 (lecture par tick) ; :1878-1883 et :1657 (écrivains coupés) ; tools/evo_runs/s2_credit_retention.py:73 (benchmark_mode forcé) ; :363-375 (même objet modèle).
- **Classe** : E26
- **Verdict** : non confirmé

### P8.c (JUGE) — logits = VUE de H réécrite par le vote
- **Sonde** : `grep -n batch_logits src/worlds/world_1_stoneage.py` ; `sed -n <l>p` sur backend_torch.py 200 et 210, et sur le monde 963, 972, 973, 1269, 1340 ; `python scratchpad/p8_v5_sonde.py`
- **Constat** : ce que le monde modifie est bien une vue de l'état récurrent. Le tableau renvoyé par forward passe au vote sans aucune copie, et toutes les références citées par la v5 sur ce canal concordent. Les blocs du bassin qui relient les 11 nœuds du crédit aux nœuds 77 et 78 pèsent 0,727 et 0,929, soit 8,7 % et 9,7 % de la L1 hors capteurs : la part de 11 nœuds quelconques sur 113. Le couplage est générique, pas privilégié. Le verbe employé par la règle reste exact.
- **Preuve** : world_1_stoneage.py:1263, :1269, :973 ; backend_torch.py:200 et :210 ; col 77, 0,727/8,332 = 0,087 ; col 78, 0,929/9,574 = 0,097 ; 11/113 = 0,097.
- **Classe** : E5
- **Verdict** : non confirmé

### P8.d (JUGE) — second écrivain (-0,1) et support de ΔW
- **Sonde** : `sed -n 1300,1345p src/worlds/world_1_stoneage.py ; sed -n 155,170p src/agents/backend_torch.py ; python scratchpad/p8_v5_sonde.py`
- **Constat** : le décalage de -0,1 porte toujours sur le nœud de la dernière action, l'un des nœuds 64 à 71, une colonne où vit le crédit dans les six bras, et tout le support de b_eplr. La part qui subsiste au pas suivant vaut 1-δ, et δ vient de la diagonale, que la greffe et le sham modifient. Dans le bassin, 1-δ vaut environ 0,22 sur les nœuds 68-71. Pour b_full, ΔW déplace δ de 0,035 au plus sur 64-71. La règle déclare cet écrivain non compté et sa propagation par la W propre à chaque condition, ce qui englobe la diagonale. C'est une précision, pas une omission.
- **Preuve** : world_1_stoneage.py:1339-1342 ; backend_torch.py:160-161 et :170 ; δ 0,988 à 0,993 sur 64-67 et 0,767 à 0,781 sur 68-71 ; |Δδ| max sur 64-71 : 3,49e-02 (full), 6,28e-03 (eplr), 9,58e-05 (zero).
- **Classe** : E5
- **Verdict** : non confirmé

### P8.e (JUGE) — colonnes des nœuds capteurs réputées inertes
- **Sonde** : `grep -n '_torch_pop\.H|\.H\[|w_gate\s*=|torch_throw_gate\s*=' src/worlds/world_1_stoneage.py src/agents/backend_torch.py ; python scratchpad/p8_v5_sonde.py` (input_cols par bras)
- **Constat** : rien ne lit l'état des nœuds capteurs avant qu'il soit écrasé. L'observation est réinjectée avant tout calcul d'excitation. Le gate de conditionnement est absent, et les deux lecteurs de H côté monde ne tournent que si le gate de lancer est activé, ce qui n'est pas le cas. Le crédit ne met aucune masse dans ces colonnes. Il est donc exact que iso et pos y dépensent une part de leur masse sans effet sur la politique.
- **Preuve** : backend_torch.py:159 ; CONDITION_GATE = False :48 ; w_gate = None :115 ; torch_throw_gate = False world_1_stoneage.py:59 ; lectures conditionnées :1144 et :1359 ; input_cols = 0,0000 pour les 5 bras sondés.
- **Classe** : aucune
- **Verdict** : non confirmé

## P9 — provenance et sceau (DÉLÉGUÉ)

### P9.a — provenance, porte 20
- **Sonde** : `python tools/check_evidence_provenance.py --only <scratchpad>/S2-BASSIN-FRAGILITY.v5.json ; git merge-base --is-ancestor 3c9414f6 HEAD ; git ls-files --error-unmatch results/s2_bassin_fragility_sonde_conception.json ; git cat-file -e HEAD:results/s2_bassin_fragility_sonde_conception.json`
- **Constat** : verdict recopié de la porte 20 : OK, code de sortie 0, 18 chemins légataires gelés, rien de nouveau. Ce vert ne dit rien de la cible : la porte ne lit que docs/EDR/*.md, et un --only qui désigne un fichier hors de ce répertoire filtre la totalité des records sans le signaler — la forme E4 que P2.128 (3c9414f6) corrige, commit ABSENT de HEAD 82927108 dans ce worktree. Hors porte, par git seul : le JSON de sonde cité par la règle est suivi dans l'INDEX mais absent de HEAD ; il doit partir dans le commit qui porte le sceau. Défaut de porte, donc dette (P2.128 déjà inscrite, à fusionner dans tmp/science), pas une critique de la règle.
- **Preuve** : 'records : 304 | ... absents : 18 ... OK : 18 chemin(s) legataire(s) gele(s)', exit=0 ; tools/check_evidence_provenance.py:86 (périmètre docs/EDR seulement) et :362 ; merge-base -> P2.128 ABSENT de HEAD ; ls-files OK, cat-file HEAD -> absent.
- **Classe** : E4
- **Verdict** : hors périmètre — porte aveugle à une pré-inscription, dette P2.128 non fusionnée

### P9.b — intégrité du sceau
- **Sonde** : `python -c "from tools.preregister import verify; verify('S2-BASSIN-FRAGILITY')" ; ls docs/preregistrations | grep -ci bassin`
- **Constat** : la vérification du sceau lève FileNotFoundError : aucune règle S2-BASSIN-FRAGILITY n'existe sous docs/preregistrations. La cible est une v5 relue AVANT scellement : pas encore de hash à confronter, donc ni altération ni intégrité à constater. À rejouer une fois preregister(..., reviewed_by=docs/reviews/...) exécuté ; le hash rendu est celui à transmettre à Master 2.
- **Preuve** : FileNotFoundError (tools/preregister.py:196), exit=1 ; grep -ci bassin -> 0.
- **Classe** : aucune
- **Verdict** : hors périmètre — revue antérieure au sceau, intégrité non évaluable

## P10 — mécanismes

### P10.a (JUGE) — mesure de la garde E19
- **Sonde** : `grep -o "measure(0,04) = ([^)]*)" S2-BASSIN-FRAGILITY.v5.json ; grep -o "measure(lr) = (0, f)" S2-BASSIN-FRAGILITY.v5.json ; grep -n "lambda lr: (0.0, frac" tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : deux définitions incompatibles de la mesure E19 coexistent dans la règle. L'entrée 10bis de la table de décision (celle qui tranche) calcule l'écart en ticks bruts à partir des médianes de greffe et de sham du bras ; le runner passe à la garde la fraction de perte épargnée normalisée, comme le décrit clause_E19. La branche 10bis ne mentionne pas non plus les deux conditions de lisibilité (aucun bras de la paire à saturation >= 0,9, au moins un bras DIRECTION ou PARTIEL) que le code impose avant tout réétiquetage. verifier_seuils ne relie que le bloc seuils au code, jamais ce texte : le décalage passerait le sceau.
- **Preuve** : v5.json:8 -> measure(0,04) = (médiane S_tr_tdoff, médiane S_sign_tdoff) ; v5.json:4 -> measure(lr) = (0, f) ; tools/evo_runs/s2_bassin_fragility.py:558 -> lambda lr: (0.0, frac[float(lr)]) ; :564 lisible = not satures and a_defendre ; :920-930 verifier_seuils ne lit que rule['seuils'].
- **Classe** : E10
- **Verdict** : confirmé — réécrire 10bis sur (0, f) et y inscrire les deux conditions de lisibilité avant le sceau

### P10.b (JUGE) — commande seed sur nexus
- **Sonde** : `grep -n "SEULS les fichiers SUIVIS" tools/jobs/remote.py ; grep -n '"source.tar.gz", archive_gz' tools/jobs/remote.py ; grep -n "^results/\*$" .gitignore ; grep -n "replay = _replay or cellule\|if os.path.exists(pj) and os.path.exists(pn)\|cell_reloaded" tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : sur nexus, le chemin décrit ne marche pas tel qu'écrit. Un pod ne reçoit que le dépôt au sha plus le script d'entrée, et les W et JSON de cellule sont sous un répertoire que git ignore. Un Job seed ne voit donc aucune de ses six cellules. run_fragility_seed passe par cellule, qui rejoue alors les six phases 1 sans rien signaler : le contrôle cell_reloaded n'existe que dans la commande tout, et seulement pour le premier seed. Conséquences : environ 1300 s CPU de rejeu s'ajoutent aux environ 100 s de phases 2 du seed ; le coût est compté deux fois à l'agrégation (le cpu_s du seed englobe le rejeu et cells_cpu_s le compte déjà) ; et les JSON de cellule réécrits dans le pod (pid, wall_s, charge différents) entrent en conflit au rapatriement avec ceux des Jobs cellule.
- **Preuve** : tools/jobs/remote.py:19-20 et :315 ; .gitignore:18 results/* ; s2_bassin_fragility.py:333 (relecture seulement si pj et pn existent, sinon :346 replay_arm) ; :391/:403 ; :398/:443 ; :994-996 ; unique garde de relecture :1023 (_commande_tout) ; remote.py:369-391 (conflit -> rien installé).
- **Classe** : E13
- **Verdict** : confirmé — exiger cell_reloaded dans la commande seed (refus sinon) ou faire d'un seed complet un seul Job nexus, et corriger le plafond

### P10.c (JUGE) — effet du vote social
- **Sonde** : `grep -n "consensus = np.sum(vectors \* weights" src/swarm/consensus.py ; grep -n "if out_share > 0.5 and out_accept > 0.0\|for idx in indices:" src/worlds/world_1_stoneage.py`
- **Constat** : le texte dit que le vote masque ΔW pour le groupe. Le code fait autre chose : la ligne de sorties de CHAQUE agent de la case, qu'il ait voté ou non, est remplacée par une moyenne pondérée (softmax des fitness) des logits des seuls votants, et chacun de ces logits porte son propre ΔW. ΔW est donc moyenné entre clones, pas masqué. Et comme les logits sont une vue de H, un non-votant reçoit dans son état récurrent des sorties calculées sous le ΔW d'autres agents. Parler de masquage sous-estime le couplage inter-agents que compter_consensus est censé circonscrire.
- **Preuve** : src/swarm/consensus.py:55 ; src/worlds/world_1_stoneage.py:965, :972-973 ; src/agents/backend_torch.py:200 et :210.
- **Classe** : aucune
- **Verdict** : confirmé — portée limitée (descriptif hors verdict) : écrire « moyenne des votants imposée à toute la case », pas « masque »

### P10.d (JUGE) — contrôle de réplication de la dose
- **Sonde** : `grep -o "(td_updates, episode_updates, resurrections, ticks)" S2-BASSIN-FRAGILITY.v5.json ; sed -n 277,280p tools/evo_runs/s2_bassin_fragility.py | grep -c ticks` ; `python -c` (charge s2_credit_ablation_2.json et s2_credit_ablation.json, teste 'ticks' in learning)
- **Constat** : la mesure annonce que la dose rejouée, ticks compris, doit coïncider au bit avec le publié. Le contrôle exécuté compare le chemin, les âges, les compteurs TD et épisodiques et les résurrections, mais jamais les ticks. published() ne les lit même pas, alors que les JSON de P4.16 et de P4.9 les publient (2000). Sans conséquence pratique sous immortalité, mais c'est une vérification annoncée qui n'est pas exécutée.
- **Preuve** : v5.json:27 ; s2_bassin_fragility.py:466-470 sans ticks ; :277-280 grep ticks = 0 ; results/s2_credit_ablation_2.json b_full/2026 learning.ticks = 2000, présent aussi dans s2_credit_ablation.json.
- **Classe** : E10
- **Verdict** : confirmé — mineur : ajouter ticks au contrôle ou le retirer du texte

### P10.e (JUGE) — affirmations de mécanisme relues et trouvées exactes
- **Sonde** : `python -c` (npz bassin : dims, densité, L1 des blocs vers 77/78) ; `python -c` (JSON P4.16/P4.9/P4.4 : ratio de chemin, saturation, résurrections, td_updates) ; `grep -n` sur backend_torch.py, world_1_stoneage.py, learning_events.py
- **Constat** : contrôle de couverture ; aucune de ces affirmations n'est fausse. Les logits sont une vue de H et le monde retranche 0,1 en place. Le gradient TD touche onze colonnes (sortie à partir de 64, constantes 24/25/28) et l'épisodique seul en touche huit. Le pas par agent vaut lr/12 sous SGD avec une perte moyennée. TD est compté par appel de population : 1999 sur les six bras publiés. La résurrection place le corps en fin de liste sans reconstruire la population. Le chemin se cumule à chaque mise à jour. _write_back ne recalcule pas le corps. Le bassin est dense ; 59 entrées donnent 34,3 % de colonnes d'entrée, inertes sans gate.
- **Preuve** : backend_torch.py:32-35, :141, :155-167, :200, :210, :502, :509-513 ; world_1_stoneage.py:1060-1066, :1312, :1340 ; s2_credit_retention.py:111 ; learning_events.py:173,187 ; bassin I=59 O=108 N=172, densité 1,0, blocs 0,727 et 0,929 (8,7 et 9,7 %) ; ratio de chemin médiane 1,363 (0,828-2,838, min seed 2027) ; saturation b_tdoff 1,017 ; résurrections eplr > tdoff 12/12 ; td_updates 1999 partout.
- **Classe** : aucune
- **Verdict** : non confirmé — mécanismes exacts à la lecture

### P10.f (JUGE) — appariement eps après arrondi float32
- **Sonde** : `ls results/ | grep -i bassin_frag`
- **Constat** : on ne peut pas vérifier ici que eps (1e-3 du ΔW de b_full) tient 1 % en L1 effective après l'arrondi float32 : aucune cellule n'est persistée sur disque, et reconstruire ΔW demande un rejeu de monde, exclu de la revue. La branche 6 le contrôle pendant le run.
- **Preuve** : seul s2_bassin_fragility_sonde_conception.json (clés : _comment, sonde_net_chemin, temoin_parallelisme, sources, W_sonde_sha256), aucun npz.
- **Classe** : aucune
- **Verdict** : hors périmètre — exige une simulation ; dette si on veut le savoir avant le sceau

---

## Addendum de l'auteur (session SCIENCE-HARNAIS, 2026-09-26) — suites données, v5 → v6

Cette revue porte sur la v5 (sceau de brouillon `0a11ba3b…`). Elle DISCRIMINE sur ce passage : le témoin cru sain rend
6 critiques recevables, les trois témoins à défaut au moins 7. Ses 17 critiques confirmées ont été revérifiées une à
une contre le code avant d'être suivies. Plusieurs portent sur le fond, ce qui interdit de sceller la v5 : P6.a (la
bande fabriquait du signal), P7.1 (une étiquette qui attribuait à l'amplitude ce que la létalité sépare aussi), P10.b
(l'exécution sur nexus rejouait des phases 1 en silence), P5.2 (un drapeau écrit et jamais lu), P1.a et P10.a (texte
et code en désaccord sur la garde E19, prémisse du remède). La version soumise au sceau est la **v6**, relue à son tour
(`docs/reviews/2026-09-26-S2-BASSIN-FRAGILITY.v6.md`).

**Suites données aux critiques confirmées.**
- **P6.a (E4)** — critique REPRODUITE avant correction. Le simulateur de la revue, rejoué, donne une couverture du nul
  de 0,86 / 0,75 / 0,69 à σ = 1 / 2 / 4 ; la revue mesurait 0,861 / 0,753 / 0,707. La bande de demi-tirages est
  remplacée par un bootstrap des tirages dans chaque seed : quantile 0,95 de |m_b − m| sur 2000 rééchantillonnages,
  flux privé. Sa couverture mesurée est >= 0,98 de σ = 0,5 à 8 ticks, et 0,99 sous des σ hétérogènes entre 0,5 et 8.
  Sa puissance est de 0,97 à un effet égal à σ = 2. Deux témoins gelés : le premier exige une couverture >= 0,95 à
  σ = 1, 2 et 4 et REFUSE la bande de la v5 (< 0,85) ; le second exige qu'un effet de 4 sous σ = 2 sorte de la bande.
  B et q entrent au bloc `seuils` scellé.
- **P6.b (E14)** — la même bande est désormais portée par la classe de chaque sham contre S_a, et par eps et pos
  contre S_a (`bande_vs_S_a`, `dans_la_bande_vs_S_a`). Elle est dite dans le motif du verdict.
- **P6.c (E8)** — le lien « bande_chaotique_eps » déclaré mesuré ne mesurait rien. Il est remplacé par ce qui est
  effectivement calculé : `bande_de_tirage_bootstrap` et `plancher_eps`.
- **P7.1 (E8)** — nouvelle issue MIXTE_AMPLITUDE_OU_LETALITE. Si la partition FRAGILE / DIRECTION ordonnée par le net
  l'est aussi par les résurrections médianes (sans chevauchement, dans un sens ou l'autre), rien n'est attribué à
  l'amplitude. Le verdict publie `partition_par_letalite`, et le motif donne les résurrections de chaque bras. Témoin
  gelé sur les résurrections publiées, qui sortent cette issue pour la répartition prédite.
- **P10.b (E13)** — la commande `seed` REFUSE, avant tout monde, un seed dont une cellule manque. La relecture passe
  par une injection qui lève au lieu de rejouer. Témoin : refus en moins de 0,5 s, aucun monde construit, rien
  d'écrit. Le plafond décrit l'exécution réelle : cellules sur nexus (un Job = une cellule), rapatriées, puis les
  phases 2 sur la batcave par `tout`, qui relit les 72 cellules et compte leur CPU nexus. Chaque cellule publie son
  hôte. Le double comptage n'existe plus, puisqu'une cellule relue ne rejoue rien.
- **P5.2 (E1)** — `controle_direction_non_eprouve` vaut vrai dès 11 seeds sur 12 où eps égale le no-op au bit :
  c'est le seuil à partir duquel 9b peut passer par les seuls seeds miroirs de la branche 8. Il est LU, et le motif
  du verdict dit « contrôle de DIRECTION NON ÉPROUVÉ ». Témoins à 11/12 (vrai) et à 10/12 (faux).
- **P5.1, P4.d (E1)** — l'illisibilité de la garde E19 est écrite comme CERTAINE (saturation de b_tdoff >= 0,9 sur
  12/12 seeds publiés, min 0,946), dans 10bis et dans clause_E19. Toute lecture DIRECTION ou PARTIEL de b_eplr ou de
  b_tdoff porte `defendu_contre_le_pas = faux`, et le motif le dit. La garde reste appelée : la porte 23 l'exige, et
  un run futur à paire lisible s'en servira.
- **P10.a (E10)** — la clé et la valeur de 10bis sont réécrites sur measure(lr) = (0, f), avec les deux conditions de
  lisibilité ; clause_E19 est alignée. Le texte et le code disent désormais la même chose.
- **P1.a (E8)** — le rapport de norme d'opérateur tirage/crédit est publié par bras, doublé à ×2, avec le contraste
  sign ×2 − greffe à côté. 11b est réécrite : DIRECTION désigne la STRUCTURE des pas (orientation et cohérence, dont
  la norme d'opérateur), que ce run ne sépare pas. Le remède en découle sous condition : l'ancre si le tirage ×2
  reste nettement moins érodé, sinon un clip spectral à mettre en concurrence avec elle.
- **P1.b (E8)** — S_c est nommé pour ce qu'il est : la cohorte froide de P4.4, héritée, qui n'est PAS un plancher
  (les greffes passent dessous). La saturation est un indice relatif qui peut dépasser 1.
- **P1.c (E2)** — la marge du seed 2035 pour b_const est écrite (2,5 ticks, sous le bruit publié d'un petit ΔW). La
  prédiction dit NON_TRANCHE plus probable que DIRECTION pour b_const.
- **P4.c (E1)** — la branche 3 est déclarée jouée d'avance et inerte ici. La dispersion des grandeurs NEUVES est
  gardée par `contraste_degenere`, qui répond aussi à P5.3.
- **P5.3 (E1)** — `assert_not_degenerate` est appelé sur chaque contraste sham − greffe : un contraste sans
  dispersion est publié et dit. Les contrôles positifs 7 et 9b restent des critères à deux parties (compte ET
  médiane), exécutés par `_classer` / `_moins` et calibrés par les témoins du runner. `assert_positive_control`
  compare un seul scalaire à un seuil et ne les exprime pas : c'est déclaré, pas contourné.
- **P10.c** — « masque » devient « moyenne des votants imposée à toute la case », dans la règle comme dans le code.
- **P10.d (E10)** — les ticks entrent dans la réplication : `published` les lit, et 72/72 cellules publiées valent
  2000. Témoin gelé.
- **P2, P9.a (E4)** — défaut des portes 19 et 20 sur un `--only` qui ne désigne rien. C'est P2.128, corrigé dans d1
  (3c9414f6) ; il sera fusionné dans tmp/science avant le run.

**Deux exigences de Master 2 ajoutées avant la relecture de la v6.** (1) Un CONTRE-EXEMPLE à réponse connue pour la bande : un contraste nul par construction (σ = 2, valeurs gelées dans le test), que la bande de la v5 déclare HORS de sa bande (bande 0,0, contraste +0,5) et que le bootstrap couvre (bande >= 1,0). (2) « NON DÉFENDU contre le pas » est écrit AVANT le verdict : dans la règle (10bis, et ce que ce run ne tranche pas), en TÊTE du motif du verdict (témoin gelé), et il le sera en tête du record ; la paire reste jouée.

Non confirmées ou hors périmètre : sans suite (P1.d, P3, P4.a, P4.b, P4.e, P6.d, P6.e, P7.2, P7.3, P8.a-e, P9.b, P10.e,
P10.f).
