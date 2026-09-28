# Revue adversariale — E34-IDENTITY-CELL.v5

* **Cible** : `C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/E34-IDENTITY-CELL.v5.json` (pré-inscription, non scellée)
* **Date** : 2026-09-28
* **SHA** : `2103e890d5f76f01f07ec77145ddbf08032f3a62` (worktree `.worktrees/e34`)
* **Résultat des TÉMOINS** — PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 · plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1)

| témoin | statut | code | critiques recevables | planchers |
|---|---|---|---|---|
| S2-BLIND-CHAMPION-42e9357 | RETROUVE | 0 | 7 | PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 · plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1) |
| EDR-GRAB-COST-1828371 | RETROUVE | 0 | 7 | PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 · plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1) |
| EDR-RETAIN-COMPOSE-4204f8f | RETROUVE | 0 | 8 | PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 · plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1) |
| LOCK-002-286f244 (cru sain) | MESURE | 0 | 6 | PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 · plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1) |

Commandes rejouables (fichiers de critiques dans `<scratchpad>/refutateur_v5/`, témoins dans `<scratchpad>/temoins_v5/`) :

    PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier S2-BLIND-CHAMPION-42e9357 <scratchpad>/refutateur_v5/critiques-S2-BLIND-CHAMPION-42e9357.json --extrait <scratchpad>/temoins_v5/temoin-1.md --jugement OUI
    PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier EDR-GRAB-COST-1828371 <scratchpad>/refutateur_v5/critiques-EDR-GRAB-COST-1828371.json --extrait <scratchpad>/temoins_v5/temoin-3.md --jugement OUI
    PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier EDR-RETAIN-COMPOSE-4204f8f <scratchpad>/refutateur_v5/critiques-EDR-RETAIN-COMPOSE-4204f8f.json --extrait <scratchpad>/temoins_v5/temoin-4.md --jugement OUI
    PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier LOCK-002-286f244 <scratchpad>/refutateur_v5/critiques-LOCK-002-286f244.json --extrait <scratchpad>/temoins_v5/temoin-2.md

(`<scratchpad>` = `C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad`.)

Bilan : 32 critiques, **15 confirmées**.

---

## P1

### P1.1
* **Sonde** : `python -c "import itertools as I;[print(m,len([s for s in I.permutations(range(m)) if all(s[i]!=(i+1)%m for i in range(m))]),tuple(range(m)) in [...]) for m in range(2,6)]"` ; Read `tools/evo_runs/s2_credit_retention.py:196-230`
* **Constat** : Le seul verdict positif (MATERIEL, qui déclenche un plan n=12 et des bandeaux candidats) n'est protégé que par la borne 2/14, laquelle suppose les 14 survies échangeables sous H0. Cette hypothèse vient d'un raisonnement : ce run ne la mesure pas, et la construction du sham la contredit. Le tirage par rejet n'exclut que le cerveau propre au corps. L'affectation du bras éteint (permutation identité des lignes) reste donc toujours admissible, alors que celle du bras réindexé ne l'est jamais. À un événement de m positions déplacées, chaque réétiquetage retombe sur la trajectoire de S_off avec la probabilité 1/D(m) : 1 pour m=2, 1/2 pour m=3, 1/9 pour m=4. S_on n'y retombe jamais. La bande se resserre donc autour de S_off, et la fausse alarme vers MATERIEL peut dépasser 0,143. La garde BANDE_INERTE ne se déclenche que si les treize sommes |dW| sont toutes identiques : un effondrement partiel (par exemple six réétiquetages collés à S_off) passe sans signal.
* **Preuve** : Sortie de la sonde : m=2 donne 1 permutation valide (identité admise), m=3 en donne 2, m=4 en donne 9, m=5 en donne 44, avec l'identité admise à chaque fois et le cycle réindexé jamais admis. `tools/evo_runs/s2_credit_retention.py:218` : le test de rejet est `all(perm[j] != propre[j])`, `perm[j]=j` n'y est pas exclu. Dans la règle : ligne 6 (échangeabilité posée), ligne 13 (borne 2/14), ligne 22 (garde tout-égal).
* **Classe** : E8
* **Verdict** : confirmé — la prémisse porte le verdict MATERIEL, elle est posée par raisonnement et n'est mesurée ni dans ce run ni ailleurs

### P1.2
* **Sonde** : `python -c "import json;d=json.load(open('results/s2_credit_ablation.json',encoding='utf-8'));print(sorted((c['survival']['survival_median'],a,s) for a in ('b_neg','b_tdoff') for s,c in d['arms'][a].items())[:4])"`
* **Constat** : La règle présente 7,0 comme le minimum des survies sous crédit publiées, ce qui fonde l'idée que la sortie par le bas est comprimée. Ce minimum n'est vrai que sur les deux fichiers P4.4 et P4.16. Un troisième résultat suivi, au même régime (métabolisme 0,75, énergie 80, phase 1 immortelle), publie quatre cellules plus basses. Deux sont sous crédit à récompense inversée (b_neg), deux sous REINFORCE seul (b_tdoff). Leurs âges descendent à 2-3 ticks, sous le plafond de famine d'environ 7,2. La conclusion (NON_MATERIEL limité au sens haut) reste conservatrice et ne se renverse pas. En revanche, la branche MATERIEL_BAISSE garde au moins deux pas de grille publiés sous 7,0.
* **Preuve** : Sortie : (6.0, b_neg, 2036), (6.0, b_tdoff, 2036), (6.5, b_neg, 2031), (6.5, b_tdoff, 2031). Ces cellules ont td_updates=1999 (b_neg, reward_scale -1.0) et episode_updates=250 (b_tdoff). Valeurs opposées au 7,0 de la ligne 11 de la règle.
* **Classe** : E9
* **Verdict** : confirmé — la prémisse est fausse hors de P4.4/P4.16 ; elle qualifie la portée du verdict sans renverser la décision

### P1.3
* **Sonde** : `python -c "import json;d=json.load(open('results/s2_credit_retention.json'));print(d['arms']['b_warm_credit']['2026'])"` ; parcours de `results/s2_bassin_fragility.json` ; min/max par bras de `results/s2_credit_ablation_2.json`
* **Constat** : Les prémisses du témoin et de la dose sont mesurées dans l'évidence citée, pas recopiées. Pour b_warm_credit seed 2026 : 1999 mises à jour TD, 12 résurrections, 250 mises à jour épisodiques, somme |dW| exacte et liste des 12 âges. La même somme |dW| est reproduite dans un résultat qui publie lieu=batcave. Les bornes de dose se recalculent exactement : 144/(12×1999) = 0,60 % et 144/(12×250) = 4,8 %. S_a=31,5, la bande P4.16 [7,0 ; 9,5] et b_tdonly(2026)=9,0 concordent avec leurs JSON. Seul résidu : aucun résultat suivi ne publie le nombre de threads torch de la cellule publiée. S'il diffère, l'issue est TEMOIN_ROMPU (un arrêt), pas une inversion du verdict.
* **Preuve** : `results/s2_credit_retention.json` /arms/b_warm_credit/2026/learning : td_updates 1999, resurrections 12, episode_updates 250, dW_abs_sum 18242.03954219818. `results/s2_bassin_fragility.json` : /execution/lieu = batcave et /cells/2026/arms/b_full/learning/dW_abs_sum = 18242.03954219818. P4.16 : b_full min/max 7.0/9.5, a_frozen(2026)=31.5.
* **Classe** : aucune
* **Verdict** : non confirmé — prémisses mesurées ; seul le nombre de threads reste non publié

### P1.4
* **Sonde** : `git grep -lE 'first_order_change|"t1"' -- 'results/*.json'` ; `grep -n first_order_change_tick tools/evo_runs/s2_credit_retention.py`
* **Constat** : Le sens attendu du contrôle positif est emprunté à un autre dispositif : le bassin gelé de P4.4, sans aucun apprentissage (31,5 contre 7,0), et non une coupe à t1. De plus, aucun JSON suivi ne publie t1. La règle le déclare elle-même et fait de NON_TRANCHE l'issue attendue si l'érosion est précoce. Le runner publiera t1 (first_order_change_tick). Rien ici n'est une prémisse cachée.
* **Preuve** : git grep ne rend aucun fichier dans results/. `tools/evo_runs/s2_credit_retention.py:206-207` : t1 enregistré au premier changement d'ordre. Règle, ligne 9 : puissance déclarée inconnue.
* **Classe** : aucune
* **Verdict** : non confirmé — l'héritage est déclaré dans la règle et traité par NON_TRANCHE

## P2 (DÉLÉGUÉ) — Régime : chaque paramètre cité est-il publié par l'évidence ?

* **Sonde** : `cd C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34 && ls docs/EDR | grep -i -E 'e34|identity' ; python tools/check_regime_claims.py --only <scratchpad>/E34-IDENTITY-CELL.v5.json ; echo EXIT=$?`
* **Constat** : La porte 19 refuse de juger la cible : elle ne connaît que les records docs/EDR/<nom>.md, et la cible est une pré-inscription JSON du scratchpad, sans record EDR correspondant (aucun fichier e34/identity dans docs/EDR au sha 2103e890). Verdict de porte recopié tel quel : REFUS, sortie 2, aucun paramètre jugé. Enquête non rouverte ; la porte n'est pas jugée fausse (son périmètre est déclaré), donc aucune dette ouverte : P2 prendra un objet quand le record et son results/e34_identity_cell.json suivi existeront.
* **Preuve** : Sortie de la porte : « REFUS : --only designe 1 chemin(s) INCONNU(S) de cette porte -- ni record docs/EDR/<nom>.md present [...] » puis EXIT=2 ; grep docs/EDR : 0 ligne. Forme acceptée par la porte : `tools/check_regime_claims.py:361-363` (_est_record exige le préfixe docs/EDR/ et le suffixe .md).
* **Classe** : aucune
* **Verdict** : hors périmètre

## P3 (DÉLÉGUÉ) — Balayage du pas : garde E19 appelée par le runner scellé ?

* **Sonde** : `cd C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34 && python tools/check_e19_optimizer_sweep.py --only tools/evo_runs/e34_identity_cell.py ; echo exit=$? ; ls docs/preregistrations/E34-IDENTITY-CELL.json ; git ls-files docs/preregistrations | grep -ci e34`
* **Constat** : Verdict de la porte recopié : OK, code de sortie 0, aucun runner neuf sous gradient sans garde, aucune régression, aucun appelant perdu. Mais elle range le runner de la cible dans la catégorie regle_absente, en NOUVEAU non bloquant : le runner référence bien sa règle, et le fichier scellé correspondant n'existe pas encore dans le dépôt (la v5 n'est que dans le scratchpad). La porte n'a donc PAS lu le contenu de la v5 et n'a tranché ni couvert ni nu pour ce runner : son OK signifie seulement qu'elle n'a rien vu, pas qu'elle a contrôlé. Par la règle de partage je m'arrête là, sans rouvrir l'enquête. La porte n'est pas fausse, c'est l'état avant scellement. Il faut donc relancer la même commande après le scellement dans docs/preregistrations/ et recopier ce verdict-là. L'absence de balayage du pas, que la cible déclare elle-même (un seul pas, aucune invariance revendiquée), relève de P5 et n'est pas jugée ici.
* **Preuve** : HEAD 2103e890 : « runners scelles : 35 | sous gradient (PLANCHER) : 12 | nus (PLANCHER) : 9 | indetermines : 4 | non resolus : 6 | regle absente : 1 | appelants de la garde : 3 | geles : 19 » ; « [regle_absente] tools/evo_runs/e34_identity_cell.py » ; exit=0. Sens de la catégorie : `tools/check_e19_optimizer_sweep.py:396` (nom résolu, fichier scellé introuvable ou illisible). Le runner cite sa règle en `tools/evo_runs/e34_identity_cell.py:16` et `:42` (PREREG) ; ls rend « No such file or directory » ; `git ls-files docs/preregistrations | grep -ci e34` rend 0.
* **Classe** : aucune
* **Verdict** : non confirmé — la porte rend OK sans défaut E19, mais sur regle_absente : verdict aveugle à la v5 tant qu'elle n'est pas scellée, à relancer après le scellement

## P4

### P4.1
* **Sonde** : `python scratchpad/p4_v5_sonde.py` (boucle de rejet recopiée de `tools/evo_runs/s2_credit_retention.py:209-219`, ordre aligné, B = 12, graines 1..12, aucun monde) ; lecture de `tools/evo_runs/e34_identity_cell.py:176-182`, `:196`, `:290-296`
* **Constat** : La borne 2/14 et la formule ex-aequo tiennent la bande pour treize tirages distincts. Or le filtre de rejet laisse passer la permutation identité, qui est précisément le traitement du bras éteint. Si le premier changement d'ordre ne déplace que trois lignes, deux permutations seulement franchissent le filtre : la moitié des graines recopie off et la bande part de deux traitements au lieu de treize ; à quatre lignes, de six. Le runner publie band_dW_distincts mais ne s'en sert que pour refuser l'effondrement complet ; la borne reste figée à 2/(K+2), et le calcul ex-aequo divise toujours par quatorze en comptant chaque copie de off comme un tirage. Incidence sur le seed 2026 inconnue sans monde : elle dépend de la place de la première mort, et une copie peut diverger à un événement ultérieur.
* **Preuve** : sortie : m=2 -> 12 shams = off, 1 membre distinct sur 13 ; m=3 -> 6 shams = off (k 3,5,6,7,9,12), 2 distincts, 2/(d+1) = 0,667 contre 2/14 = 0,143 ; m=4 -> 2 = off, 6 distincts, 0,286 ; m>=5 -> 12 ou 13 distincts. Formule ex-aequo publiée sur 14 valeurs dont 7 copies de off : 0,143 contre 0,250 sur 8 trajectoires distinctes. `s2_credit_retention.py:215-218` (perm[j] = j admis) ; `e34_identity_cell.py:196` (2/(K_RELABS+2) fixe) ; `:294` (seule garde : dw_distincts < 2)
* **Classe** : E23
* **Verdict** : confirmé — propriété du runner (la borne publiée cesse d'en être une dès qu'un sham recopie off) ; incidence sur le seed 2026 non mesurable sans monde

### P4.2
* **Sonde** : `python -c` import tools.evo_runs.e34_identity_cell (len(ARMS), K_RELABS, N_GRILLE) ; `python -c` 400 000 tirages uniformes de 15 valeurs (on, 13 de bande, pos) ; `python tools/check_control_family.py --report`
* **Constat** : Compte nominal : quinze bras codés pour quinze annoncés, bande de treize, grille 2 ; le défaut v4 P4.a (S_off testé deux fois) est résorbé : sous échangeabilité continue de quatorze valeurs, la seule issue non nulle garde exactement sa probabilité 2/14. La porte 11 passe (design déclaré, n = 1, aucune famille exigée).
* **Preuve** : ARMS 15, K_RELABS 12, N_GRILLE 2 ; P(MATERIEL | H0) = 0,1427 contre 2/14 = 0,1429 ; porte : 33 runners scellés, 0 sans design
* **Classe** : aucune
* **Verdict** : non confirmé

### P4.3
* **Sonde** : `sed -n 268,314p tools/evo_runs/e34_identity_cell.py | grep -ci floor` ; awk des symboles floor, band_publiee, s_frozen sur les lignes 268-314
* **Constat** : Aucun seuil de décision n'est importé d'un autre dispositif : FLOOR 9,0, S_a et la dispersion de P4.16 n'alimentent que des descriptifs ; les branches qui tranchent comparent S_on et S_pos à la bande interne de la cellule.
* **Preuve** : 0 occurrence de floor dans `e34_identity_cell.py:268-314` ; FLOOR 9.0 utilisé seulement à `:255` (sous_plancher_off, descriptif)
* **Classe** : aucune
* **Verdict** : non confirmé

## P5

### P5.1
* **Sonde** : `python scratchpad/p5_sondes.py` (partie A : 200000 tirages sur la grille 0,5, avec la vraie tools.grid_compare.cmp_grille)
* **Constat** : La seconde moitié de l'exigence posée au contrôle positif (S_pos au-dessus de S_off) ne peut jamais échouer seule : depuis la v5, S_off compte parmi les treize valeurs, donc franchir le maximum de la bande suffit toujours à la satisfaire. La règle scellée présente une double condition alors qu'une seule peut tomber, reste de la v4 où S_off était hors de la bande. Aucune issue n'en change, mais le texte annonce un garde-fou qui n'agit pas.
* **Preuve** : `tools/evo_runs/e34_identity_cell.py:289` (band = [s_off] + relabs) et `:305` (cmp_grille(s_pos, band_max) and cmp_grille(s_pos, s_off)) ; E34-IDENTITY-CELL.v5.json:9 et :25 ; sonde A : 11885 tirages où la clause 1 tient, 0 où la clause 2 échoue
* **Classe** : E1
* **Verdict** : confirmé

### P5.2
* **Sonde** : `python scratchpad/p5_sondes.py` (partie B : énumération des dérangements relatifs au décalage cyclique pour m = 2..5 ; appel de _fausse_alarme_ex_aequo du runner)
* **Constat** : Rien ne garantit que la bande contienne treize trajectoires distinctes. Le tirage par rejet retombe forcément sur l'affectation du bras éteint quand un événement déplace deux positions depuis l'ordre aligné, une fois sur deux à trois positions, une fois sur neuf à quatre, et deux shams peuvent aussi coïncider entre eux. Le refus pour bande inerte ne se déclenche que si les treize sommes |dW| sont toutes égales. La borne 2/14 et la valeur ex-aequo supposent treize tirages échangeables distincts : des copies conformes font baisser le chiffre publié alors qu'elles augmentent la vraie fausse alarme. band_dW_distincts est mesuré, mais il n'entre ni dans la borne ni dans le verdict.
* **Preuve** : `tools/evo_runs/s2_credit_retention.py:213-219` (rejet si perm[j] == propre[j]) ; `tools/evo_runs/e34_identity_cell.py:294` (refus seulement si dw_distincts < 2) et `:176-182` ; sonde B : m=2 -> 1 dérangement, m=3 -> 2, m=4 -> 9, l'identité du bras éteint toujours admise ; _fausse_alarme_ex_aequo(8.0, [7.0]*12+[7.5]) = 0.0714 contre 0.667 si seules trois trajectoires sont distinctes, et à 2 |dW| distincts ce cas va jusqu'à MATERIEL_HAUSSE
* **Classe** : E7
* **Verdict** : confirmé

### P5.3
* **Sonde** : `python scratchpad/p5_sondes.py` (partie C : ordre des corps du harnais publié simulé en liste, sans monde) ; lecture de `s2_credit_retention.py:150-158`
* **Constat** : La règle affirme que le bras éteint, comme les shams, ne remet jamais un cerveau déplacé sur son propre corps. C'est faux dès que deux morts se composent : le harnais publié pousse le mort en queue sans toucher aux lignes, et une seconde mort peut ramener un corps à son rang de construction. À ce type d'événement, le sham est obligé de s'écarter du bras éteint (le rejet interdit justement ce recollement). S_off et les S_relab ne reçoivent donc pas le même traitement. Aucun compteur de l'audit n'isole ces recollements : l'égalité de traitement est déduite, pas mesurée.
* **Preuve** : sonde C : depuis l'ordre aligné, mort du corps 3 puis du corps 11 -> positions déplacées [10, 11], recollée [11], ordre final [0,1,2,4,...,10,3,11] ; `tools/evo_runs/s2_credit_retention.py:111` (append en fin) et `:218` (le sham rejette perm[j] == propre[j]) ; aucun compteur de recollement dans _identity_counters (`:150-158`) ; E34-IDENTITY-CELL.v5.json:6 et :8 affirment l'inverse pour le bras éteint
* **Classe** : E8
* **Verdict** : confirmé

### P5.4
* **Sonde** : `grep -n 'assert_positive_control|assert_not_degenerate|assert_ablation_changes_something|declare_design' tools/evo_runs/e34_identity_cell.py` ; `ls results/e34_identity_cell*` ; `python -c` lisant results/s2_credit_ablation_2.json, seed 2026
* **Constat** : La sonde imposée ne trouve aucune des trois gardes de pré-vol dans le runner : seul declare_design y est appelé. Le contrôle positif est vérifié en interne (coupe à t1, dose TD plus basse), ce qui prouve que la coupe a eu lieu ; c'est la branche NON_TRANCHE qui tient lieu de garde de succès. Le JSON de résultats n'existe pas encore, donc il n'y a aucune valeur de contrôle à confronter. Les régimes diffèrent (la coupe retire tout le crédit après t1, le traitement touche au plus 144 commutations), mais NON_MATERIEL reste borné à l'ampleur de la bande, et le contrôle ne sert qu'à exclure un plafond : ce n'est pas un E19 ici. Aucun bras n'est optimisé en phase 2 (poids gelés).
* **Preuve** : grep : 0 garde, declare_design seul (`e34_identity_cell.py:458`, `:478`) ; results/e34_identity_cell* absent ; P4.16 seed 2026 : a_frozen 31.5, b_full 7.0 (|dW| 18242), b_tdonly 9.0 (11743), b_eplr 11.5 (1168), b_const 21.0 (941)
* **Classe** : aucune
* **Verdict** : non confirmé

## P6

### P6.1
* **Sonde** : `python scratchpad/p6_v5_sonde.py` (vraie immortal_after_step, cohorte factice torch du test, B = 12, une mort en p = 0..10 depuis l'ordre aligné, RNG k = 1..12)
* **Constat** : La bande n'est pas le bruit du contraste on/off. Au premier changement d'ordre, un réétiquetage peut rendre exactement l'affectation du bras éteint : c'est forcé à deux positions déplacées, fréquent à trois ou quatre, alors que le bras réindexé diverge dès t1. Ces membres ne commencent à diverger qu'à un événement ultérieur (ou jamais), avec un levier plus court : l'échangeabilité de S_on avec la bande, donc la borne 2/14, n'est pas garantie. Et la garde de la branche 7 ne le voit pas : le premier réétiquetage est daté à t1 même quand aucune ligne n'a bougé.
* **Preuve** : sortie : m = 2 -> 12/12 réétiquetages identiques au bras éteint ; m = 3 -> 6/12 (k = 3,5,6,7,9,12) ; m = 4 -> 2/12 (k = 5,12) ; m >= 5 -> 0/12 ; first_relabel_tick = t1 dans les 132 cas. Code : `tools/evo_runs/s2_credit_retention.py:224-229` (permutation appliquée puis first_relabel_tick posé sans condition sur rows_relabeled).
* **Classe** : E1 (membre de bruit analytiquement égal au bras éteint) ; garde de branche 7 : E4
* **Verdict** : confirmé

### P6.2
* **Sonde** : `python -c "from tools.evo_runs.e34_identity_cell import _fausse_alarme_ex_aequo as f; print(f(8.0,[7.0]*12+[7.5]), f(13.5,[7.0+0.5*i for i in range(13)]))"`
* **Constat** : Le taux de fausse alarme publié à côté du verdict récompense la bande dégénérée : quand la plupart des membres sont des copies du bras éteint (cas que le dispositif fabrique lui-même, critique précédente), la formule ex-aequo DIVISE par deux le chiffre affiché au lieu de l'alourdir. Et BANDE_INERTE ne tire que si les treize sommes |dW| sont toutes égales : une seule trajectoire divergente suffit à la désarmer.
* **Preuve** : 0.0714 (bande 12 x 7,0 + 7,5 ; S_on 8,0 -> MATERIEL_HAUSSE) contre 0.1429 (13 valeurs distinctes) ; `tools/evo_runs/e34_identity_cell.py:182` (formule) et `:294` (dw_distincts < 2)
* **Classe** : E18
* **Verdict** : confirmé

### P6.3
* **Sonde** : `grep -nE "reindex_events|rows_relabeled|digest" tests/sandbox/test_e34_slot_identity.py`
* **Constat** : Le no-op EXACT de ce contraste (la machinerie de permutation appelée avec l'identité à un vrai événement de recharge, trajectoire comparée au bras éteint) n'est mesuré nulle part. Les tests dits no-op au bit tournent sans aucune mort : celui de la réindexation asserte même que la permutation n'a jamais été appelée ; le test à deux lignes déplacées compare des objets après UN appel, jamais une trajectoire. Le dispositif produit pourtant ce no-op gratuitement (réétiquetage à m = 2) sans exiger qu'il rende S_off au bit.
* **Preuve** : `tests/sandbox/test_e34_slot_identity.py:528-532` (kills=(), reindex_events == 0 asserté : permute_population_rows jamais appelé) ; `:494-497` (kills=(), res == 0, correctif de CORPS) ; `:331` (rows_relabeled == 0 sur des objets, aucun digest) ; 3 égalités de digest dans le fichier (`:486`, `:497`, `:532`), aucune avec une permutation appelée
* **Classe** : E4
* **Verdict** : confirmé

### P6.4
* **Sonde** : `grep -niE "no.?op" <cible>` ; même motif sur CLAUDE.md ; `ls results/e34_identity_cell.json` ; `git ls-files results | grep -c e34`
* **Constat** : Aucun ratio n'est encore publié : la cible est une pré-inscription, le JSON qu'elle cite n'existe pas et n'est pas suivi. La comparaison de la part d'érosion levée à son plancher (les douze équivalents des réétiquetages, `e34_identity_cell.py:264-266`) ne peut donc pas être faite ici. Le mot no-op est absent de la règle ; son plancher y porte le nom de bande.
* **Preuve** : grep cible : 0 correspondance (rc = 1) contre 5 sur CLAUDE.md ; ls : No such file ; git ls-files : 0
* **Classe** : aucune
* **Verdict** : hors périmètre

## P7 (JUGÉ) — Dose

### P7.1
* **Sonde** : `grep -n 'return {"survival_median"\|assert ev.summary' tools/evo_runs/s2_credit_retention.py` ; `grep -n 'out\["survival"\] =' tools/evo_runs/e34_identity_cell.py` ; `grep -rn 'python -O\|"-O"' tools/jobs/*.py tools/evo_runs/e34_identity_cell.py`
* **Constat** : Le JSON de la cellule ne dit rien de l'apprentissage en phase 2. Le compteur y est ouvert, puis son résumé est jeté après une simple instruction assert (|dW| == 0). La ligne publiée ne garde que la survie. Un lecteur de l'évidence suivie ne peut donc pas vérifier que la DV a été mesurée sans apprentissage : il ne voit ni le nombre d'appels épisodiques à pas nul, ni une somme |dW| nulle. La phase 1, elle, publie sa dose par bras. Aujourd'hui l'assert tourne (aucun -O dans tools/jobs), donc le verdict n'est pas faussé : le défaut est une lacune de publication.
* **Preuve** : `tools/evo_runs/s2_credit_retention.py:341` (assert sur ev.summary()[dW_abs_sum]) puis `:342`, qui rend seulement {survival_median, ages, censored, ticks}. `tools/evo_runs/e34_identity_cell.py:143` ne stocke que out[survival], alors que la dose de phase 1 est publiée par bras en `:239-250`. Le grep -O rend 0 ligne.
* **Classe** : aucune
* **Verdict** : confirmé (lacune de publication de la dose de phase 2 ; aucun effet sur la décision tant que l'assert s'exécute)

### P7.2
* **Sonde** : `python -c "import json; c=json.load(open('results/s2_credit_retention.json'))['arms']['b_warm_credit']['2026']; L=c['learning']; B=c['num_agents']; sw=B*L['resurrections']; print(L['td_updates'],L['episode_updates'],L['resurrections'],sw, round(sw/(B*L['td_updates']),4), round(sw/(B*L['episode_updates']),4))"`
* **Constat** : J'ai recalculé, depuis le bloc d'apprentissage publié de la cellule témoin, les bornes que la pré-inscription avance. Avec 12 corps et 12 résurrections, on a au plus 144 changements de corps. Divisé par 12 x 1999 mises à jour TD, cela donne 0,0060 ; divisé par 12 x 250 mises à jour épisodiques, 0,048. Les deux pourcentages annoncés sont exacts. Le dénominateur TD du runner est déduit (ticks_learn - 1) et non lu, mais le témoin le fige à 1999 : l'écart est nul.
* **Preuve** : La sortie donne td 1999, ep 250, res 12, B 12, sw_max 144, frac_td 0.006, frac_ep 0.048. Le dénominateur déduit est en `tools/evo_runs/e34_identity_cell.py:258`.
* **Classe** : aucune
* **Verdict** : non confirmé (dose publiée et cohérente)

### P7.3
* **Sonde** : `sed -n 1052,1067p src/worlds/world_1_stoneage.py` ; `grep -n 'batch_model.learn(\|self.agents = survivors\|energy_max and not self.benchmark_mode' src/worlds/world_1_stoneage.py`
* **Constat** : En phase 1, la cohorte compte bien 12 corps à chaque mise à jour. Le monde ne réaffecte la liste des survivants qu'après l'appel TD. La recharge réinsère ensuite les morts avant le pas suivant, si bien que la condition de reconstruction de la population torch (taille changée) ne se déclenche jamais. Les résurrections sont publiées par bras, et les instants des commutations aussi (switch_events). La reproduction est coupée en benchmark_mode.
* **Preuve** : `src/worlds/world_1_stoneage.py:1765` (learn) précède `:1784` (self.agents = survivors). La reconstruction n'a lieu que si B != len(models) (`:1060-1063`). La reproduction est gardée par not benchmark_mode (`:1657`). Les résurrections par bras sont publiées en `tools/evo_runs/e34_identity_cell.py:244`.
* **Classe** : aucune
* **Verdict** : non confirmé (cohorte constante par construction)

### P7.4
* **Sonde** : `grep -n 'dose\["pos"\]\["td_updates"\]' tools/evo_runs/e34_identity_cell.py` ; `sed -n 164,173p tools/learning_events.py` ; `sed -n 166,169p tools/evo_runs/s2_credit_retention.py`
* **Constat** : Pour le bras pos, la dose n'est confrontée qu'à une inégalité stricte contre le bras éteint. Or sa valeur attendue est connue exactement : le premier appel est différé, donc les mises à jour TD comptées doivent égaler le tick de coupe publié. Ni les mises à jour épisodiques ni |dW| après la coupe ne sont vérifiées. Aucune fuite n'est possible dans le code actuel, car l'instance neutralisée n'est jamais reconstruite en phase 1. Cas limite : si t1 tombait sur le dernier tick, les deux bras auraient 1999 et le runner signalerait à tort un défaut du harnais.
* **Preuve** : `tools/evo_runs/e34_identity_cell.py:285` teste seulement td_pos < td_off. La neutralisation se fait sur l'instance en `tools/evo_runs/s2_credit_retention.py:168-169`. Le compteur est posé sur la classe et compte une mise à jour dès que la perte n'est pas None (`tools/learning_events.py:165-173`).
* **Classe** : aucune
* **Verdict** : non confirmé (garde plus faible que la prédiction disponible, sans conséquence atteignable)

### P7.5
* **Sonde** : `python -c "import json; c=json.load(open('results/s2_credit_retention.json'))['arms']['b_warm_credit']['2026']['survival']; print(c['ages'], c['censored'], c['survival_median'])"`
* **Constat** : Le nul d'apprentissage et le nul de létalité ne sont pas séparables sur cette DV. En phase 2, la cellule publiée meurt entière entre 5 et 11 ticks, sans aucun censuré, et sa médiane de 7,0 est collée au plafond de famine (~7,2). Un nul lu là serait un nul de létalité. Mais la pré-inscription le dit déjà : sortie vers le bas déclarée non éprouvée, NON_MATERIEL réservé au sens montant, NON_TRANCHE si le contrôle positif ne sort pas. Aucun défaut nouveau.
* **Preuve** : La sortie donne [5, 6, 6, 7, 7, 7, 7, 8, 8, 9, 9, 11], 0 censurés, médiane 7.0. Dans E34-IDENTITY-CELL.v5.json, voir la ligne 11 (plancher) et les lignes 25-26 (9c/9d).
* **Classe** : E3
* **Verdict** : non confirmé (déjà déclaré et borné par la pré-inscription)

## P8

### P8.1
* **Sonde** : `python tools/check_io_overlap.py` ; `ls results/*.npz | wc -l` ; `python scratchpad/p8_v5_sonde.py` (lignes [E24])
* **Constat** : La porte 17 rend vert, mais le seul génome de cette cellule (le bassin DAgger, rangé sous results/) n'est pas dans son périmètre : elle ne parcourt que data/genomes et les Hall of Fame. Le bassin lui-même ne chevauche pas : entrées 0-58, sorties 64-171, cinq nœuds cachés entre les deux. La vraie garde est l'assertion exécutée au chargement du bassin. Le vert de la porte n'apporte donc rien à ce record. C'est un trou de la porte 17, à inscrire comme dette : un génome chevauchant écrit sous results/ passerait sans être vu. Le record n'est pas en cause.
* **Preuve** : La porte annonce 358 génomes persistés (348 sous data/genomes + 10 HoF), 0 nouveau chevauchant, exit 0. results/*.npz = 1 fichier. Sonde : bassin I=59, O=108, N=172, I+O=167, chevauchement 0, bassin dans le périmètre de la porte = False. Garde réelle : `tools/evo_runs/s2_credit_retention.py:61` (assert_no_io_overlap dans load_bassin).
* **Classe** : E24
* **Verdict** : hors périmètre

### P8.2
* **Sonde** : `python scratchpad/p8_v5_sonde.py` (lignes [E26]) ; `grep -n phenotype src/agents/mamba_agent.py` ; `grep -n update_phenotype src/worlds/world_1_stoneage.py`
* **Constat** : La réindexation et les réétiquetages déplacent chaque tranche de W en entier, y compris les lignes 0-9 dont le monde tire le métabolisme. Le corps n'est pourtant pas touché : le phénotype est calculé une seule fois, quand le génome est chargé, et rien ne le recalcule après la réécriture des poids appris. Les douze clones ont des génomes copiés, pas partagés, et donc un phénotype identique. Le drain mesuré redonne bien le plafond de famine annoncé.
* **Preuve** : Après W[0:5]+1 et _write_back : sum|genome.W[0:5]|x10 = 8613.287, mais le phenotype_hp_bonus lu par le monde reste 688.827. update_phenotype n'est appelé qu'en `mamba_agent.py:140/152/177/198` et `world_1_stoneage.py:990` (reproduction). Génome partagé entre clones = False. drain = 14.8883, 80/(0.75 x drain) = 7.164, contre environ 7,2 dans le record.
* **Classe** : E26
* **Verdict** : non confirmé

### P8.3
* **Sonde** : `python scratchpad/p8_v5_sonde.py` (lignes [VUE] et [PERM]) ; `git show f1d6a987:src/worlds/world_1_stoneage.py | sed -n '973p;1340p'` ; `git show f1d6a987:src/agents/backend_torch.py | sed -n '109p;512p'`
* **Constat** : forward rend bien une vue de H, et le -0,1 écrit par le monde descend dans l'état récurrent. La permutation remplace H par une copie, ce qui détache l'ancienne vue. Mais elle n'a lieu qu'une fois le pas du monde fini, donc après le TD et l'épisodique, et le monde ne garde aucune vue d'un tick à l'autre (il extrait des flottants). Aucune écriture n'est perdue. W reste l'objet tenu par l'optimiseur, et le gradient non permuté est remis à zéro avant chaque backward. Les ancres au sha f1d6a987 sont exactes.
* **Preuve** : np.shares_memory(logits, pop.H) = True. Écrire logits[1,3]-=0.1 fait passer pop.H[1,67] de 0.815514 à 0.715514. Après permute : pop.W is W_obj = True, ancienne vue partagée = False. Ordre : `s2_credit_retention.py:305-306` (e.step puis immortal_after_step) ; `world_1_stoneage.py:1765` (learn), `:1778` (épisodique), `:1784` (survivants). zero_grad en `backend_torch.py:292`. Au sha f1d6a987 : `:973` = batch_logits[idx] = consensus_logits, `:1340` = pénalité -0,1.
* **Classe** : E5
* **Verdict** : non confirmé

### P8.4
* **Sonde** : `python scratchpad/p8_v5_sonde2.py` (écriture d'une ligne entière dans la vue d'une population, puis forward suivant comparé à une population jumelle non écrite)
* **Constat** : Le vote social écrit dans l'état récurrent et agit surtout sur la politique au tick suivant, bien plus que par V(s'). En gros, la moitié de ce qu'il écrit est encore là au tick d'après, et les nœuds de sortie portent l'essentiel de la récurrence. Le bras pos reste exposé à ce canal pendant la phase 1. Mais ses poids sont gelés dès t1, et la phase 2 ne lit que les poids. Rien de ce canal n'atteint donc S_pos, et « moins exposé » tient.
* **Preuve** : delta des 108 sorties : médiane 0.502 (min 0.446, max 0.992). sum|W_off[sorties,:]| = 1508.53 sur 2405.50. Écart des logits au tick suivant : moyenne 0.366, max 0.991, mais seulement 0.032 sur V (sortie 28). Coupe du crédit du bras pos : `s2_credit_retention.py:166-169`.
* **Classe** : E5
* **Verdict** : non confirmé

## P9

### P9.a (DÉLÉGUÉ) — provenance des results/ cités, porte 20
* **Sonde** : `python tools/check_evidence_provenance.py --only <scratchpad>/E34-IDENTITY-CELL.v5.json` ; `python tools/check_evidence_provenance.py --only docs/preregistrations/E34-IDENTITY-CELL.json` ; `ls docs/EDR | grep -c -i -E 'e34|identity'` ; `ls docs/EDR | wc -l`
* **Constat** : La porte 20 rejette le filtre sur les deux désignations essayées : elle ne traite que les records docs/EDR/<nom>.md, or la cible v5 est un brouillon de règle hors dépôt et aucun record E34 n'existe encore (0 sur 306 fichiers EDR). La porte ne rend donc aucun verdict de provenance ; je recopie son refus et je m'arrête. Les quatre chemins results/ que cite le brouillon ne sont pas rejugés à la main, conformément à la règle de partage. Remarque de dette, pas une critique : pour une pré-inscription, P9 n'a pas de porte vers laquelle déléguer, déjà noté en v4.
* **Preuve** : exit=2 sur les deux appels : REFUS, --only désigne 1 chemin INCONNU de cette porte (ni record docs/EDR/<nom>.md présent) ; edr_e34=0, edr_total=306
* **Classe** : aucune
* **Verdict** : hors périmètre

### P9.b (DÉLÉGUÉ) — intégrité du sceau de la pré-inscription
* **Sonde** : `python -c "from tools.preregister import verify; verify('E34-IDENTITY-CELL')"` ; idem avec `'E34-IDENTITY-CELL.v5'` ; `ls docs/preregistrations | wc -l` ; `ls docs/preregistrations | grep -c -i BASSIN` ; `git ls-files docs/preregistrations | grep -c -i -E 'e34|identity'`
* **Constat** : Aucun sceau n'existe à vérifier : preregister.verify lève FileNotFoundError pour E34-IDENTITY-CELL comme pour E34-IDENTITY-CELL.v5, et aucun fichier E34 n'est présent dans docs/preregistrations, ni sur disque ni dans l'index. Le grep est validé sur un cas positif connu (BASSIN : 1 règle sur 72). La revue précède le scellage, donc l'absence est l'état attendu d'un brouillon ; je recopie le verdict de la garde. À rejouer après scellage et avant la phase A : le runner annonce la règle scellée à ce chemin (`tools/evo_runs/e34_identity_cell.py:16`) et doit lever tant qu'elle manque.
* **Preuve** : exit=1 sur les deux appels, `tools/preregister.py:196` FileNotFoundError (règle non scellée) ; regles=72, bassin=1, e34_disque=0, e34_index=0
* **Classe** : aucune
* **Verdict** : hors périmètre

## P10

### P10.1
* **Sonde** : `python scratchpad/p10v5_sonde_repair.py` ; `python scratchpad/p10v5_sonde_repair_b12.py` (immortal_after_step réel sur bouchon, aucun monde)
* **Constat** : L'équivalence de défaut entre bras éteint et réétiquetages est raisonnée depuis un ordre aligné, jamais mesurée sur un événement composé : dès la 2e mort, la recharge publiée peut rendre à un cerveau déplacé SON propre corps (B = 3 : A0 meurt puis A2 -> le cerveau de A2 retrouve A2). Le dérangement du sham interdit exactement ce cas ; le bras éteint le produit. Les tests E34 ne couvrent que le premier événement depuis l'alignement.
* **Preuve** : B=3 : off remis=[[], ['A2']] contre relab_01 [[], []] ; B=12, 300 suites de 12 morts : off 1143 re-appariements sur 23116 positions déplacées, relab_01 0. Affirmation contraire : `tools/evo_runs/e34_identity_cell.py:11` et `tools/evo_runs/s2_credit_retention.py:138` ; tests alignés seulement : `tests/sandbox/test_e34_slot_identity.py:297`
* **Classe** : E8
* **Verdict** : confirmé

### P10.2
* **Sonde** : `python scratchpad/p10v5_sonde_repair_b12.py` ; `grep -n "propre\[j\]" tools/evo_runs/s2_credit_retention.py`
* **Constat** : Le sham ne contrôle que le retour au corps PROPRE, pas le changement de corps : quand les corps déplacés portent déjà un cerveau étranger, un tirage peut faire suivre à chaque ligne le corps qu'elle pilotait, soit zéro commutation, c'est-à-dire la moitié du correctif. La bande reçoit donc moins de la grandeur déclarée active que le bras éteint, et aucune branche du verdict ne lit cet écart : il est seulement publié. Sous H1 la bande glisse vers S_on, biais vers NON_MATERIEL.
* **Preuve** : relab_01 19846 commutations contre off 23116 (-14 %), 256 événements à zéro commutation contre 0 ; B=3 : slot_switches 3 contre 5. Condition du tirage : `tools/evo_runs/s2_credit_retention.py:218` ; la dose de la bande n'est que publiée : `tools/evo_runs/e34_identity_cell.py:293`
* **Classe** : aucune
* **Verdict** : confirmé

### P10.3
* **Sonde** : `sed -n 116,124p tools/learning_events.py` ; `grep -n "w0 = _snapshot_W" tools/learning_events.py`
* **Constat** : La référence donnée pour le cumul de |dW| pointe à côté : la plage citée commence sur une ligne vide et s'arrête avant le calcul ; l'instantané est pris dans les enveloppes de learn et learn_episode, pas là. Le fond (cumul par mise à jour, insensible aux permutations intercalées) tient.
* **Preuve** : `tools/learning_events.py:120` vide, `:124` porte le calcul du delta, instantanés à `:169` et `:182` (identique au sha f1d6a987)
* **Classe** : aucune
* **Verdict** : confirmé

### P10.4
* **Sonde** : `sed -n 348,366p tests/sandbox/test_e34_slot_identity.py` ; `sed -n 37,42p tests/sandbox/test_e34_slot_identity.py`
* **Constat** : La règle dit l'absence de tirage torch VÉRIFIÉE par test pour la coupe ; le test de la coupe tourne sur un bouchon sans torch et n'asserte que le RNG global numpy. Le code de la coupe (deux lambdas) ne tire rien, mais la vérification annoncée n'existe pas pour ce bras.
* **Preuve** : `tests/sandbox/test_e34_slot_identity.py:351` construit _World(4) (object() comme modèles, `:39`), seule assertion RNG `:366` sur np.random ; la réindexation et le sham, eux, assertent torch.get_rng_state (`:281`, `:316`)
* **Classe** : E4
* **Verdict** : confirmé

### P10.5
* **Sonde** : `grep -n compter_reconstructions tools/evo_runs/e34_identity_cell.py`
* **Constat** : La liste scellée des instruments autorisés omet le compteur de reconstructions que le runner appelle et que le champ mesure nomme ; seul le compteur du vote y figure pour ce module.
* **Preuve** : `tools/evo_runs/e34_identity_cell.py:132` et `:142` (import et usage en phase 2) ; instruments_autorises de la v5 ne cite pour s2_bassin_fragility que _neutraliser_kuzu, _charge, compter_consensus
* **Classe** : aucune
* **Verdict** : confirmé
