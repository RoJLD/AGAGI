# Revue adversariale — S2-BASSIN-FRAGILITY (v4, pré-inscription)

- **Cible** : `C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/S2-BASSIN-FRAGILITY.v4.json` (kind : pré-inscription, avant sceau)
- **Date** : 2026-09-26
- **SHA** : `82927108f6244537bee0a35d44fa06dcf36cea03` (`git -C .worktrees/science rev-parse HEAD`)
- **Critiques confirmées** : 20

## Témoins

| témoin | statut | code | recevables | jugement |
|---|---|---|---|---|
| S2-BLIND-CHAMPION-42e9357 | RETROUVE | 0 | 7 | OUI |
| LOCK-002-286f244 (cru sain) | MESURE | 0 | 7 | — |
| EDR-GRAB-COST-1828371 | RETROUVE | 0 | 7 | OUI |
| EDR-RETAIN-COMPOSE-4204f8f | RETROUVE | 0 | 8 | OUI |

Commande de chaque ligne : `PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier <nom> <scratchpad>/refutateur_v4/critiques-<nom>.json --extrait <scratchpad>/temoins/temoin-N.md [--jugement OUI]` (N = 1..4 dans l'ordre du tableau).

**PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5**
**plancher mesure sur LOCK-002-286f244 : 7 critiques recevables (seuil historique 1)**
**⚠ INDISCRIMINANT : le record cru sain rend autant de critiques recevables que les defectueux**

---

## P1

### P1.1
- **Sonde** : `python -c "from tools.evo_runs import s2_bassin_fragility as m; S_a=[36.0]*12; S_tr=[8.0]*12; S_sign=[28.0]*10+[8.0,8.0]; tc=m._classer([t-a for t,a in zip(S_tr,S_a)],11,5.0); sc=m._classer([s-a for s,a in zip(S_sign,S_a)],11,5.0); c=[s-t for s,t in zip(S_sign,S_tr)]; ...; print(m._lecture_bras(tc[0],sc[0],moins))"` (aucun monde)
- **Constat** : La lecture FRAGILE, et avec elle 11a (l'orientation du crédit ne compterait pas, l'ancre serait écartée), suppose que le sham détruit autant que le crédit. Aucun test de la règle ne mesure cette équivalence : FRAGILE est obtenu comme complément de MOINS, et MOINS tombe dès que deux seeds ont un contraste nul ou négatif (ex aequo compris), quel que soit l'écart médian. Injection à dose connue dans les fonctions du runner : un sham qui ne reproduit que 29 % de la perte de greffe, avec un contraste médian de +20 sur 10 seeds, est lu FRAGILE. Le qualificatif publié (fraction requise 1 − 5/écart, ici 82 %) est donc faux comme condition : il ne décrit que la voie médiane et ignore la voie du comptage, qui rend FRAGILE beaucoup plus facile, pas plus dur, aux grands écarts.
- **Preuve** : sortie : transplant ERODE, sham ERODE -8.0, c_med 20.0, c_pos 10/12, moins False -> lecture FRAGILE ; perte reproduite 0.286 contre requise publiée 0.821 ; tools/evo_runs/s2_bassin_fragility.py:506 (FRAGILE = sham ERODE et non moins), :577 (moins = cpos >= 11 ET cmed >= 5), :639 (fraction publiée 1 - delta_min/gap)
- **Classe** : E8
- **Verdict** : confirmé — prémisse porteuse de 11a non mesurée, et le qualificatif publié la décrit à tort

### P1.2
- **Sonde** : python -c qui lit les rows de results/s2_credit_ablation.json, s2_credit_ablation_2.json et s2_credit_retention.json et calcule |S_arm - S_a|/(S_a - S_c) et le nombre de seeds où S_arm <= S_c ; `grep -n reference_floor tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : La garde 10bis interprète une fermeture de l'écart sham − crédit au-delà de 2/3 comme un effet du pas ou de la létalité. Or, au pas 0,04, le bras crédit de la paire (b_tdoff) est déjà au niveau de la cohorte froide dans les données publiées : saturation médiane 1,02, au plancher ou dessous sur 8 seeds sur 12. b_eplr, au pas 0,004, en est loin : 0,65, aucun seed au plancher. Au pas 0,04, un sham qui descend lui aussi au plancher referme l'écart par simple écrasement des deux bras. C'est la seconde cause que la garde nomme elle-même, et elle ne la sépare que si on lui passe un plancher de référence. L'appel du runner n'en passe aucun, alors que S_c est présent dans chaque ligne. Une lecture DIRECTION_DEPEND_DU_REGLAGE, puis MIXTE, peut donc sortir d'un artefact de plancher : c'est un troisième confondant, absent de la clause E19, qui ne cite que le pas et la létalité.
- **Preuve** : sortie : tdoff S méd 7.5, sat méd 1.017, 8/12 seeds <= S_c ; eplr S méd 17.0, sat 0.649, 0/12 ; S_c méd 7.5 ; grep reference_floor : 0 ligne ; appel sans plancher à tools/evo_runs/s2_bassin_fragility.py:526 ; distingo conditionné à reference_floor dans tools/experiment_preflight.py:349-356
- **Classe** : E3
- **Verdict** : confirmé — le bras de la paire au pas 0,04 est saturé au plancher et la garde n'est pas armée pour le voir

### P1.3
- **Sonde** : `python -c "import json; v=json.load(open('results/s2_credit_ablation.json',encoding='utf-8'))['verdict']; print(v['S_tdoff_median'], v['d_tdoff_median'])"`
- **Constat** : La prédiction pré-enregistrée pour b_tdoff chiffre son érosion à 7,5. Ce nombre est en réalité la survie médiane de b_tdoff après crédit dans P4.9. Son érosion appariée vaut −29,0, la plus forte des six bras, et elle est plus éloignée de b_eplr (−19,0) que ne le suggère le rapprochement fait dans la prédiction. Aucune branche n'en dépend, mais le texte scellé rapporte une grandeur sous le nom d'une autre.
- **Preuve** : sortie : 7.5 -29.0 ; cible S2-BASSIN-FRAGILITY.v4.json:29 (champ predictions_avant_le_run)
- **Classe** : E8
- **Verdict** : confirmé — hors verdict (prédiction seulement)

### P1.4
- **Sonde** : python -c sur les verdict/rows de results/s2_credit_ablation{,_2}.json (médianes, comptes de signe, résurrections, dW_tdoff/dW_eplr) ; `python -c 'from tools.evo_runs import s2_bassin_fragility as m; print(m.seuil_tient(), m.FAMILLE, m.E19_PAIRE)'`
- **Constat** : J'ai revérifié contre les JSON suivis les autres prémisses qui renverseraient une branche. Elles tiennent. Harnais : S_a médiane 36,0, de 17 à 50. Classes de greffe : full, tdonly et tdoff érodent sur 12/12 ; const et eplr sur 11/12, exactement au seuil ; zero est neutre (8/12, −0,75). b_eplr a plus de résurrections que b_tdoff sur 12/12 seeds. Le rapport de chemin de la paire vaut 1,36 (de 0,83 à 2,84). Le seuil 11/12 tient pour une famille de 14 : queue 0,00317 contre 0,00357. Rien d'hérité sans contrôle n'a été trouvé en dehors des deux critiques précédentes.
- **Preuve** : sortie : S_a 36.0 [17, 50] ; d_const_negative 11/12, d_eplr_negative 11/12, d_zero 8/12 méd -0.75, d_tdoff 12/12 -29.0 ; eplr>tdoff résurrections 12/12 ; ratio 1.363 0.828 2.838 ; seuil_tient (True, 0.003173828125, 0.00357) famille 14
- **Classe** : aucune
- **Verdict** : non confirmé — prémisses porteuses mesurées ou vérifiées au bit

## P2 (DÉLÉGUÉ)

### P2.1 — Régime : chaque paramètre cité est-il publié par l'evidence ?
- **Sonde** : `python tools/check_regime_claims.py --only <scratchpad>/S2-BASSIN-FRAGILITY.v4.json` ; `python tools/check_regime_claims.py --only docs/EDR/S2-BASSIN-FRAGILITY.md` (inexistant) ; `python -c 'from tools.check_regime_claims import evaluer ...'` appliqué au texte de la cible ; python -c re.findall des motifs :94 et :95 sur la cible
- **Constat** : Verdict recopié de la porte 19 : OK, exit 0. Ce vert ne dit rien de la cible. La porte ne balaie que les records Markdown de docs/EDR, et une pré-inscription JSON posée dans le scratchpad n'entre pas dans ce périmètre. Le même OK, au caractère près, sort pour un record qui n'existe pas. Même quand on donne le texte de la cible directement à son extracteur, celui-ci ne trouve ni paramètre ni citation : les chemins results/ n'y sont pas entre backticks, et les valeurs de pas ou de ticks n'ont jamais la forme 'nom = nombre'. P2 portera sur le record EDR à venir, quand il citera le results agrégé suivi. Rien à critiquer ici.
- **Preuve** : tools/check_regime_claims.py:347 (os.path.join(root, 'docs', 'EDR') = seul périmètre balayé). Les deux appels --only rendent la même sortie : 'records : 304 | ... OK : 64 record(s) ...', exit=0. evaluer(texte cible) -> statut=SANS_PARAMETRE, params={}, cites=[]. Sur la cible : 2 chemins results/*.json en clair, 0 entre backticks (motif _RESULTS, :95), 0 forme param=nombre (motif _CLAIM, :94), alors que le texte écrit 'lr 0,04', '2000 ticks', '200 ticks'.
- **Classe** : aucune
- **Verdict** : hors périmètre

### P2.2 — dette sur la porte, pas une critique de la cible
- **Sonde** : `grep -c check_regime_claims docs/roadmap/PRIORITES_ET_DETTES.md` ; `grep -n check_regime_claims ... | grep -ic only` ; `grep -n only tools/check_e19_optimizer_sweep.py | grep -i refus`
- **Constat** : La porte 19 accepte sans rien dire un filtre --only qui ne désigne aucun record balayé, puis rend OK avec exit 0. On obtient un vert vide, qu'on ne peut pas distinguer d'une vraie concordance. La porte 23 refuse déjà un --only vide ; la porte 19 ne refuse ni un filtre vide, ni un filtre hors périmètre. Selon la règle de partage, c'est une dette à ouvrir au backlog : le chemin filtré doit appartenir aux records scannés, sinon REFUS avec exit non nul. Je ne l'ai pas inscrite moi-même : un numéro s'alloue au moment de l'écriture et l'arbre est partagé, donc je la laisse à la session appelante.
- **Preuve** : tools/check_regime_claims.py:425-432 (le filtre only restreint 'nouveaux' sans vérifier son appartenance à a['records']) ; tools/check_e19_optimizer_sweep.py:375-377 (REFUS du --only vide, absent de la porte 19) ; backlog : 4 mentions de la porte, 0 sur --only (motif validé sur le cas positif)
- **Classe** : E4
- **Verdict** : hors périmètre

## P3 (DÉLÉGUÉ) — Balayage du pas : la garde E19 est-elle appelée par le runner scellé ?

### P3.1
- **Sonde** : `cd .worktrees/science && python tools/check_e19_optimizer_sweep.py --only tools/evo_runs/s2_bassin_fragility.py; echo EXIT=$?`
- **Constat** : Porte 23 lancée sur le runner de la cible : aucun défaut E19 bloquant. Le runner est rangé dans la catégorie regle_absente (la v4 vit dans le scratchpad et n'est pas encore scellée au registre, la porte ne peut donc pas lier runner et règle), mais il est compté parmi les appelants directs de la garde d'invariance au pas. Verdict de la porte recopié tel quel, enquête non rouverte ; le rangement définitif (couvert attendu) ne pourra être lu qu'après le sceau.
- **Preuve** : Sortie : 'runners scelles : 34 | sous gradient (PLANCHER) : 12 | nus (PLANCHER) : 9 | indetermines : 4 | non resolus : 6 | regle absente : 1 | illisibles : 0 | appelants de la garde : 3 | geles : 19' ; 'NOUVEAU (non bloquant) : [regle_absente] tools/evo_runs/s2_bassin_fragility.py : appelle assert_verdict_invariant_to_optimizer(...) directement' ; 'OK : aucun nouveau runner sous gradient sans garde E19' ; EXIT=0. Runner stagé (git status : A tools/evo_runs/s2_bassin_fragility.py).
- **Classe** : E19
- **Verdict** : non confirmé — la porte 23 rend OK (exit 0) : le runner appelle directement la garde E19 ; statut regle_absente tant que la v4 n'est pas scellée, à relancer après le sceau

## P4

### P4.1
- **Sonde** : `python tools/check_control_family.py --report` (32 runners scellés ; ce runner, pas encore scellé, n'y figure pas) ; `python scratchpad/p4_sonde_transplant.py` (classe les greffes publiées avec _classer à 10/12 et à 11/12) ; lecture de tools/evo_runs/s2_bassin_fragility.py:396-437 et :580-615
- **Constat** : Recompte fait dans fragility_verdict : la lecture applique le critère de signe à 14 endroits (pos, eps contre S_a, eps contre transplant full, 6 classes sign, 5 contrastes MOINS). Les 5 contrastes n'existent que pour les bras dont la greffe érode, et cette érosion est fixée par le publié : 5 bras érodent, b_zero ne bouge pas. Côté mesures, chaque seed demande 137 phases 2 (1 + 6×21 + 10), comme annoncé. La famille déclarée est donc la bonne. Deux réserves chiffrées : b_const et b_eplr passent la barre à 11/12 tout juste, et la famille peut monter à 15 cellules, pas à 16.
- **Preuve** : Classes des greffes à 11/12 : full 12/12 (−28,25), tdonly 12/12 (−27,75), const 11/12 (−12,25), eplr 11/12 (−19,00), tdoff 12/12 (−29,00) ERODE ; zero 8/12 (−0,75) NEUTRE. seuil_tient(11,12,f) : f=14 et f=15 tiennent, f=16 échoue (0,003174 > 0,003125). Phases 2 par seed : s2_bassin_fragility.py:396 (noop), :413-426 (21 par bras), :429-437 (5 eps + 5 pos) = 137
- **Classe** : aucune
- **Verdict** : non confirmé

### P4.2
- **Sonde** : grep -c sur FAMILLE, SIGN_MIN, DELTA_MIN, famille_de_controles et rule[ dans tests/sandbox/test_s2_bassin_fragility.py et test_instrument_calibration.py ; `grep -o 'rule\["[a-z_]*"\]' tools/evo_runs/s2_bassin_fragility.py | sort -u`
- **Constat** : Le lien entre le nombre de cellules scellé et celui qu'utilise le code ne repose que sur un commentaire. Le runner code en dur FAMILLE, SIGN_MIN et DELTA_MIN, et il ne lit dans la règle que trois champs, dont aucun seuil. Le seul test concerné appelle seuil_tient avec le littéral 14, pas R.FAMILLE. Le correctif v3 P4.3 relie le seuil à la constante, mais pas la constante au texte scellé. Si un -bis agrandit la famille sans toucher le runner, 11/12 reste accepté et aucun test ne rougit.
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:94 dit que le test confronte les constantes au sceau. Réalité : 0 occurrence de FAMILLE, SIGN_MIN, DELTA_MIN ou famille_de_controles dans test_s2_bassin_fragility.py (les 7 FAMILLE de test_instrument_calibration.py sont sans rapport). Le runner lit seulement rule["question"], rule["plafond"] et rule["budget_s"] (:893, :899, :1011). tests/sandbox/test_s2_bassin_fragility.py:401 appelle seuil_tient(11, 12, 14) avec des littéraux
- **Classe** : E10
- **Verdict** : confirmé

### P4.3
- **Sonde** : `grep -n DELTA_MIN tools/evo_runs/s2_credit_retention.py` ; python -c (extraction regex de la justification ±5 dans docs/preregistrations/S2-CREDIT-RETENTION.json) ; python -c (médianes publiées de S_a et S_tr par bras via published()) ; grep dans la v4 de '5 ticks' et 'hérit'
- **Constat** : La v4 a recalculé le seuil de signe pour ce dispositif, mais elle reprend sans le dire l'écart minimal de 5 ticks de P4.4. Là-bas, ce chiffre valait un peu plus de deux rounds DAgger et environ 15 % du bassin. Ici, le contraste MOINS se mesure à partir de la survie greffée, qui est bien plus basse. Pour full, tdonly et tdoff, 5 ticks représentent donc environ 60 à 67 % de ce niveau de référence, et non plus 14 %. La justification d'origine n'est ni reprise ni recalculée.
- **Preuve** : s2_bassin_fragility.py:96 DELTA_MIN = 5.0, identique à s2_credit_retention.py:49. Justification P4.4 : ±5 ticks = plus de 2 x le pas par round de DAgger (+2/round, WARM-003) et ~15 % du bassin. v4 : 0 occurrence de '5 ticks', 0 de 'hérit'. Médianes publiées : S_a 36,0 (5/S_a = 0,14) ; S_tr full 8,0 (0,62), tdonly 8,5 (0,59), tdoff 7,5 (0,67), eplr 17,0 (0,29), const 23,25 (0,22)
- **Classe** : E8
- **Verdict** : confirmé

### P4.4
- **Sonde** : python -c : injection dans _garde_e19 d'écarts (3g ; g) pour g = 0,5 à 20 par pas de 0,5 (40 paires) ; `python -c "print(repr(1-5/15), repr(2.0/3.0))"` ; lecture de tools/experiment_preflight.py:419
- **Constat** : Le seuil de 2/3 de la garde E19 est la valeur par défaut de assert_verdict_invariant_to_optimizer, calibrée sur des exactitudes continues. Ici, il s'applique à des médianes de survie posées sur une grille de 0,25 tick, où un rapport d'écarts exactement égal à 1/3 est atteignable. La règle ne fait basculer la lecture qu'au-delà de 2/3, strictement. En flottant, pourtant, 1 − 1/3 vaut un peu plus que 2/3, si bien que l'égalité exacte bascule toujours en DIRECTION_DEPEND_DU_REGLAGE. Le résultat global devient alors MIXTE.
- **Preuve** : 40/40 paires à fermeture exactement 2/3 basculent en invariant=False, aucune n'est gardée. Exemples : (1,5 ; 0,5), (15 ; 5). 1-5/15 = 0.6666666666666667 contre 2.0/3.0 = 0.6666666666666666. tools/experiment_preflight.py:419 : if closure > float(max_gap_closure). Le runner n'importe pas grid_compare (0 occurrence de cmp_grille)
- **Classe** : E30
- **Verdict** : confirmé

### P4.5
- **Sonde** : `python scratchpad/p4_sonde_transplant.py` (S_a publiés des seeds 2026 à 2037) ; lecture de s2_bassin_fragility.py:659-672
- **Constat** : La branche 3 tient la barre de 20 ticks héritée de P4.4, mais elle ne peut plus échouer une fois la branche 2 passée : S_a est alors identique au bit à l'a_frozen publié. Sa médiane et son étendue sont donc connues avant le run. C'est un contrôle incapable d'échouer, ce qui relève de P5 et non de la taille de la famille.
- **Preuve** : S_a publiés = [31.5, 35.5, 44.5, 39.0, 42.5, 35.5, 36.0, 36.0, 50.0, 42.0, 17.0, 26.5] : médiane 36,0 ≥ 20, étendue 33 > 1 ; a_frozen de P4.9 == a_frozen de P4.16 : True
- **Classe** : E1
- **Verdict** : hors périmètre

## P5

### P5.1
- **Sonde** : python -c qui charge results/s2_credit_ablation.json (tdoff) et results/s2_credit_ablation_2.json (full, tdonly, const, eplr), pose S_sign = S_a (sham parfaitement inerte), compte c = S_a - S_tr > 0 et applique SIGN_MIN, DELTA_MIN et _lecture_bras importés du runner
- **Constat** : Même avec un tirage de signes strictement inerte, b_const et b_eplr n'obtiennent MOINS qu'au seuil exact : 11 seeds positifs sur 12, sans aucun seed de réserve. Au seed 2036, la greffe de b_const ALLONGE la survie de 10,5 ticks et celle de b_eplr la laisse égale au no-op (l'égalité compte contre) : ce seed est perdu d'avance. Il suffit d'un seul autre seed défavorable pour faire tomber le bras en NON_TRANCHE ; pour b_const, le seed 2035 ne tolère que 2,5 ticks d'érosion du sham. Or la lecture globale DIRECTION (11b) exige les cinq bras érodés. Le seul témoin de DIRECTION (9b) tourne sur b_full : 12/12, avec au moins 9 ticks d'avance. C'est le régime facile, et il ne calibre pas ces deux bras. La critique v3 P5.2 raisonnait sur un seul seed et sur une largeur d'écart ; mesurée ici sur les 12 seeds publiés, elle devient une borne dure.
- **Preuve** : sortie : full 12/12 (plus petite marge 9,0), tdonly 12/12 (9,5), tdoff 12/12 (11,0) ; const 11/12, seed 2036 c = -10,5, marge suivante 2,5 ; eplr 11/12, seed 2036 c = 0,0, marge suivante 7,0. SIGN_MIN = 11 à tools/evo_runs/s2_bassin_fragility.py:95 ; 9b ne porte que sur b_full (:703) ; 11b exige tous les érodés (:726)
- **Classe** : E2 (témoin en régime facile : E19)
- **Verdict** : confirmé

### P5.2
- **Sonde** : python -c qui passe au vrai _garde_e19 du runner les médianes publiées (S_a 36,0 ; S_tr tdoff 7,5 ; S_tr eplr 17,0), avec un sham inerte côté tdoff et une érosion x du sham côté eplr, x dans {0, 5, 8, 9, 10, 12}
- **Constat** : La garde de pas compare des écarts sham moins crédit exprimés en ticks bruts. Or, en médiane, la greffe coûte 19 ticks à b_eplr contre 28,5 à b_tdoff. Avec un sham qui ne fait rien aux deux pas, la fermeture vaut donc déjà 0,333 : la moitié du budget de 2/3 est consommée avant tout effet d'orientation. Dès que le tirage de b_eplr érode 10 ticks, les deux bras sont relus DIRECTION_DEPEND_DU_REGLAGE. Le chiffre de fermeture confond deux choses : l'effet du pas sur l'AMPLITUDE d'érosion du crédit, et son effet sur l'écart dû à la direction. Publier la fermeture de référence à sham inerte, ou normaliser l'écart par la perte de greffe, séparerait les deux. L'appel ne passe pas non plus reference_floor : une fermeture causée par l'effondrement du sham (la référence) n'est donc pas distinguée (P2.21).
- **Preuve** : sortie : x=0 -> closure 0,333 invariant True ; x=9 -> 0,649 True ; x=10 -> 0,684 False ; x=12 -> 0,754 False ; appel sans reference_floor à tools/evo_runs/s2_bassin_fragility.py:526
- **Classe** : E19
- **Verdict** : confirmé

### P5.3
- **Sonde** : `grep -n seeds_eps_egal_noop tools/evo_runs/s2_bassin_fragility.py` ; python -c (mêmes JSON publiés) : _classer(S_tr_full - S_a) puis MOINS de S_a - S_tr_full avec S_eps = S_a
- **Constat** : La v4 a répondu à v3 P5.1 en publiant combien de seeds rendent eps identique au no-op, mais aucune branche ne consulte ce compte. Si les 12 seeds sont dans ce cas, 9b rejoue la branche 8 au signe près et ne peut plus tomber. Il reste pourtant compté parmi les 14 tests de la famille et présenté comme le témoin positif de DIRECTION. La limite est écrite, pas appliquée. Remède possible : au-delà d'un nombre scellé de seeds identiques au no-op, déclarer 9b non éprouvé et dire que DIRECTION n'a pas de témoin.
- **Preuve** : une seule occurrence, :588 (publication) ; branche 8 : ERODE, 12/12 négatifs, médiane -28,25 ; 9b à eps inerte : 12/12 positifs, médiane +28,25, les mêmes nombres au signe près ; FAMILLE = 14 inclut ce contraste (:84)
- **Classe** : E1
- **Verdict** : confirmé — résiduel (limite déclarée, non appliquée)

### P5.4
- **Sonde** : `grep -nE '^POS_REL|assert_positive_control|assert_ablation_changes_something' tools/evo_runs/s2_bassin_fragility.py` ; python -c imprimant les clés de results/s2_bassin_fragility_sonde_conception.json
- **Constat** : Le bruit gaussien pos, à la norme L1 entière du bassin, peut échouer (la branche 7 le teste), mais il vit hors du régime des bras : les déplacements nets par agent vont de 3,4 à 100,5. La règle le dit, et l'échelle x2/x4 le complète hors verdict. Aucun JSON ne publie encore de survie de contrôle : impossible de juger sa valeur avant le run. Ce n'est pas un défaut d'issue impossible.
- **Preuve** : POS_REL = 1.0 à :91 ; 0 appel de assert_positive_control et 0 de assert_ablation_changes_something (le contrôle positif est codé en branches 7 et 9b) ; clés de la sonde : _comment, sonde_net_chemin, temoin_parallelisme, sources, W_sonde_sha256 — aucune survie eps/pos
- **Classe** : aucune
- **Verdict** : non confirmé

## P6

### P6.1
- **Sonde** : `python scratchpad/p6_v4_sonde.py` (bloc A : _garde_e19 sur médianes synthétiques) ; `python scratchpad/p6_v4_sonde2.py` (bloc D : Monte-Carlo sur 200000 couples d'écarts iid centrés) ; lecture de tools/evo_runs/s2_bassin_fragility.py:513-532 et :714-731, et de tools/experiment_preflight.py (closure = 1 - g_min/g_max ; seul g_max <= 0 la rend muette)
- **Constat** : La fermeture E19 est un RAPPORT de deux écarts (différence de médianes non appariée), et rien ne lui fixe de plancher de bruit : ni la bande de tirage ni DELTA_MIN ne la conditionnent. Deux écarts de l'ordre du bruit (0,5 et 0 tick, soit dix fois moins que le seuil de 5) suffisent pour déclarer la paire non invariante, relabelliser tdoff et eplr et interdire 11a, 11b et 11c. Sans aucun effet de direction, la garde lève dans 60 % des cas : un FRAGILE unanime devient MIXTE par le seul bruit des tirages.
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:714-718 relabellise quand invariant vaut False ; sortie : écarts 0,5 / 0,0 -> closure 1.0, invariant False ; écarts 0,5 / -0,5 -> closure 2.0, invariant False ; écarts 6 / 12 -> closure 0.5, invariant True ; P(la garde lève | aucun effet) = 0.604
- **Classe** : E19 (application de sa garde : fermeture lue sans plancher de bruit ; le registre n'a pas de classe dédiée au ratio sans plancher)
- **Verdict** : confirmé

### P6.2
- **Sonde** : `python scratchpad/p6_v4_sonde.py` (bloc B : inspect.getsource(fragility_verdict), recherche de 'bande' entre la boucle eps/pos et la boucle par bras)
- **Constat** : Le contraste 9b (eps moins la greffe de b_full) est une cellule de la famille et le contrôle positif de DIRECTION. Il est calculé sans qu'aucune bande soit publiée à côté : le drapeau de bande n'existe que dans la boucle des shams de bras, pas dans celle des contrôles. Le lecteur ne peut donc pas savoir si ce contraste sort du bruit des tirages eps.
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:580-588 (eps/pos : classe, médiane et contraste, aucune bande) contre :605-614 (bande calculée pour sign/iso seulement) ; sortie : bande pour eps : False
- **Classe** : E4 (forme : traitement appliqué à un membre de la famille et pas à son voisin)
- **Verdict** : confirmé

### P6.3
- **Sonde** : `python scratchpad/p6_v4_sonde3.py` (20000 jeux de 12 seeds x 5 tirages, sigma 1) ; lecture de tools/evo_runs/s2_bassin_fragility.py:605-614
- **Constat** : La bande publiée n'est pas le plancher de CE contraste. Elle mesure l'écart entre deux tirages uniques d'un même seed, alors que le contraste lu est une médiane sur 12 seeds de médianes de 5 tirages. Sous un modèle gaussien, la bande vaut 5,4 fois l'écart-type du contraste. À un effet de 0,8 sigma, le critère de signe 11/12 passe dans 81 % des cas, tandis que le drapeau déclare le contraste noyé dans 68 % des cas. Le drapeau sur-signale et contredit le test qu'il accompagne.
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:605 (draws[0] - draws[1], un seul tirage de chaque côté) ; sortie : bande 0.973 contre sd(cmed) 0.181, rapport 5.39 ; à un effet de 0,8 sigma : P(dans_la_bande) 0.678 contre P(>= 11/12) 0.812
- **Classe** : aucune (défaut de calibration du drapeau, sans effet sur la lecture)
- **Verdict** : confirmé

### P6.4
- **Sonde** : `python scratchpad/p6_v4_sonde2.py` (bloc C2)
- **Constat** : Le plancher du ratio de saturation vient de P4.4 (S_c) et non du présent harnais, d'où le soupçon d'un no-op étranger. Vérification faite : le bras gelé de P4.4 et celui de P4.16 rendent les mêmes âges au bit sur les douze seeds, et le no-op de ce run est confronté à P4.16 à chaque seed. Par transitivité, le plancher est donc celui du même dispositif.
- **Preuve** : sortie : a_warm_frozen(P4.4) == a_frozen(P4.16) au bit, 12 / 12 ; le régime ne diffère que sur arms_credit, lr_low et lr_published
- **Classe** : aucune
- **Verdict** : non confirmé

### P6.5
- **Sonde** : grep -niE 'no.?op' sur la cible et sur le runner ; lecture de tools/evo_runs/s2_bassin_fragility.py:396, :413-416, :453 et :659-663
- **Constat** : Le no-op exact est publié et vérifié à chaque seed, en tête de processus : les âges du bassin nu sont confrontés à a_frozen publié (branche 2). La greffe de chaque bras, rejouée APRÈS les tirages du bras précédent, doit rendre au bit les âges des objets appris (branche 5), ce qui couvre une dérive d'état du processus entre les tirages. Rien à redire au plancher des contrastes déterministes.
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:396 (noop en premier) et :413-416 (greffe au bit après les tirages)
- **Classe** : aucune
- **Verdict** : non confirmé

## P7 (JUGÉ)

### P7.1 — Dose : mises à jour reçues par agent et létalité
- **Sonde** : python -c (stub, aucun monde) : immortal_refill de tools/evo_runs/s2_credit_retention.py sur 12 agents dont l'id 3 est mort ; `grep -n need_rebuild src/worlds/world_1_stoneage.py` ; `grep -n 'self.agents = agents|for i, a in enumerate(self.agents)|self._prev = None' src/agents/backend_torch.py` ; `python <scratchpad>/p7_dose.py` (td_updates et résurrections des 6 bras x 12 seeds dans results/s2_credit_ablation.json et s2_credit_ablation_2.json)
- **Constat** : L'inconnue n'est pas le NOMBRE de mises à jour par agent. En phase 1, la population torch n'est construite qu'une fois : le lot reste à 12. Chaque objet-agent reçoit donc exactement les 1999 pas TD et les 250 pas épisodiques du compteur, au pas lr/12. Ce que la létalité modifie, c'est l'ATTRIBUTION. Chaque mort renvoie le corps ressuscité en queue de liste, alors que les slots de W gardent l'ordre de construction. Après une seule mort, jusqu'à 11 slots pilotent un autre corps : la transition TD en attente et l'état récurrent H sont alors à cheval sur deux corps, et la fenêtre épisodique, réalignée par identité, crédite à un slot des actions tirées par un autre. La part de ces mises à jour croît avec les résurrections, qui varient d'un facteur 51 entre bras et sont anticorrélées au net. La règle ne traite la létalité que comme une covariable de l'amplitude, pas comme un canal qui écrit dans ΔW lui-même. Aucun compteur de ces chevauchements n'est prévu, et les lectures des bras très létaux (const, zero), donc DIRECTION et MIXTE_PAR_AMPLITUDE, en héritent sans le dire.
- **Preuve** : Sortie du stub : ordre des ids [0,1,2,4,...,11,3], 9 corps sur 12 changent de slot W, 12 agents. Reconstruction seulement si B change : src/worlds/world_1_stoneage.py:1062. Le ressuscité est ajouté en fin de liste : tools/evo_runs/s2_credit_retention.py:111. Slots de W et write-back dans l'ordre de construction : src/agents/backend_torch.py:87, :109, :512. Logits lus dans l'ordre courant : src/worlds/world_1_stoneage.py:1310-1312. td_updates vaut 1999 (2000 - 1) sur les 48 cellules à TD, avec des résurrections de 2 à 380 : une reconstruction remettrait _prev à None (backend_torch.py:93) et coûterait un pas, il n'y en a donc eu aucune. Résurrections médianes : tdoff 3,5 contre zero 179.
- **Classe** : E5
- **Verdict** : confirmé

### P7.2 — Dose de la paire E19 (b_tdoff / b_eplr)
- **Sonde** : `python <scratchpad>/p7_dose.py` (dW_abs_sum et résurrections par seed : b_tdoff dans results/s2_credit_ablation.json, b_eplr dans results/s2_credit_ablation_2.json) ; `sed -n 136,146p` et `453,506p` src/agents/backend_torch.py ; `grep -n 'return self.lr / self.B|loss = -(R' src/agents/backend_torch.py`
- **Constat** : La règle présente le facteur 10 de la paire E19 comme purement nominal, faute de compteur. Le code permet pourtant de le calculer sans run : les deux voies utilisent le même SGD sans moment, et la perte est moyennée sur un lot qui reste à 12. Le pas reçu par agent est donc exactement dix fois plus petit dans b_eplr (0,00333 contre 0,000333). Avec un rapport des chemins de 1,36, la masse de gradient de b_eplr doit alors valoir environ 7,3 fois celle de b_tdoff. La paire fait donc varier deux facteurs de dose en sens contraires, et celui qui compense le pas n'est ni nommé ni publié. La garde qualifie de « réglage » un contraste dont la dose effective ne varie que d'un facteur 1,36. Le pas lr/B peut être publié tel quel, et la masse de gradient (chemin/pas) doit l'être à côté ; sa cause (retours plus grands, trajectoire restée près du bassin) n'est pas identifiée.
- **Preuve** : Rapport des chemins tdoff/eplr : médiane 1,363 (étendue 0,83 à 2,84 sur 12 seeds) ; lr_effective_per_agent publié None pour les deux bras. SGD sans moment : src/agents/backend_torch.py:141 ; perte moyennée sur B dans learn_episode : :502 ; pas par agent = lr/B : :153 ; B = 12 sur toute la phase 1, puisque td_updates vaut 1999 partout (critique précédente). Masse de gradient eplr/tdoff = 10/1,363 = 7,33 en médiane (3,52 au seed 2037, 12,08 au seed 2027).
- **Classe** : E8
- **Verdict** : confirmé

### P7.3 — Cohorte constante et nul de létalité en phase 2
- **Sonde** : stub immortal_refill ci-dessus (12 agents après résurrection) ; `grep -n 'immortal_refill|dW_abs_sum\"\] == 0.0|censored' tools/evo_runs/s2_credit_retention.py`
- **Constat** : Aucun défaut de cohorte. La phase 1 garde 12 agents à chaque tick, car la résurrection a lieu dans le même tick, sur 2000 ticks publiés. La phase 2 n'a pas d'apprenant : elle vérifie que ΔW est nul et publie ses 12 âges et ses censurés. Un nul de phase 2 ne peut donc pas être un nul d'apprentissage déguisé. Seule la létalité de phase 1 pose problème, et elle relève des deux critiques précédentes.
- **Preuve** : tools/evo_runs/s2_credit_retention.py:132-135 (boucle de phase 1 avec recharge à chaque tick) ; :163 (assertion de gel de la phase 2) ; :164 (censurés publiés) ; le stub rend 12 agents.
- **Classe** : aucune
- **Verdict** : non confirmé

## P8 (JUGÉ)

### P8.1 — VUE de l'état récurrent
- **Sonde** : `python scratchpad/p8_vue.py` (population torch bâtie sur 3 clones du bassin, sans monde ; forward, puis row=logits[0]; row[3]-=0.1, soit la forme exacte de world_1_stoneage.py:1340) ; puis python -c qui charge p418_W_p416_b_full_2026.npz et calcule la part de |ΔW| dans les lignes 64:72
- **Constat** : La v4 recense un seul site où le monde écrit dans les logits du modèle torch : le vote social. Il en existe un second, qui s'exécute à chaque tick pour chaque agent. Le monde retranche 0,1 au logit de la dernière action, en place, sur une ligne de batch_logits. Cette ligne est une vue de H, donc l'écriture modifie l'état récurrent (nœuds 64-71). Le compteur compter_consensus n'enveloppe que _apply_social_consensus : ce second écrivain n'est ni déclaré ni compté. Il n'est pas neutre vis-à-vis de l'intervention. L'écriture passe au pas suivant par les lignes 64-71 de W, et ΔW de b_full y met 5,95 % de sa L1 (64 entrées non nulles sur 64 dans le bloc 64-71 × 64-71). Le shift est commun à toutes les conditions, mais c'est la W perturbée de chacune qui le propage.
- **Preuve** : src/worlds/world_1_stoneage.py:1340 (logits[agent["last_action"]] -= 0.1, avec logits = batch_logits[idx] et last_action posé à :1355) ; sortie : np.shares_memory(logits, H) = True, un seul nœud de H modifié, [0, 67], de −0,1 ; le nœud 67 a 171 poids sortants non nuls ; part des lignes 64-71 dans |ΔW| de b_full = 0,0595 ; tools/evo_runs/s2_bassin_fragility.py:206-232 n'enveloppe que Biosphere3D._apply_social_consensus
- **Classe** : E5
- **Verdict** : confirmé

### P8.2 — chevauchement entrée/sortie
- **Sonde** : `python tools/check_io_overlap.py` ; python -c 'load_bassin() : W.shape, num_inputs, num_outputs'
- **Constat** : Le génome du bassin a 59 entrées, 108 sorties et 172 nœuds. Le premier nœud de sortie est le 64 et la dernière entrée le 58 : les deux blocs sont disjoints, séparés par 5 nœuds cachés. load_bassin appelle assert_no_io_overlap avant tout usage. La porte 17 ne signale aucun nouveau génome chevauchant.
- **Preuve** : sortie de la porte : 358 génomes persistés, 10 chevauchants (connus 10, nouveaux 0, aggravés 0), OK ; sortie python : N (172,172), I 59, O 108, N-O 64 ; tools/evo_runs/s2_credit_retention.py:61
- **Classe** : E24
- **Verdict** : non confirmé

### P8.3 — corps dérivé de W (E26)
- **Sonde** : `grep -hno 'phenotype_[a-z_]*' src/worlds/world_1_stoneage.py | sort | uniq -c` ; python -c qui mesure la part de |ΔW| de b_full dans les lignes 0:10
- **Constat** : Les interventions touchent bien les lignes 0-9 de W, qui portent aussi l'observation : ΔW de b_full y met 3,4 % de sa L1, et iso et pos y écrivent par construction. Mais le corps n'est jamais recalculé, dans aucune condition, transplant compris. La garde compare aux valeurs de phenotype_of les trois attributs que le monde lit réellement, avant et après chaque phase 2. Le corps est donc le même partout.
- **Preuve** : le monde lit seulement phenotype_hp_bonus (:375, :1652), phenotype_inv_capacity (:388) et phenotype_energy_drain (:702) ; les trois sont vérifiés par tools/evo_runs/s2_bassin_fragility.py:240-242 ; part des lignes 0:10 dans |ΔW| = 0,034 ; metabolic_cost_coef vaut 0,0 par défaut (src/environments/config.py:98), donc aucun coût métabolique ne dépend de la densité de W
- **Classe** : E26
- **Verdict** : non confirmé

### P8.4 — citations du canal de vote social
- **Sonde** : `sed -n 196,202p src/agents/backend_torch.py` ; `sed -n 1255,1270p src/worlds/world_1_stoneage.py` ; python -c qui compte (W[cols][:, [77,78]] != 0).sum() pour cols = 64..71, 88, 89, 92
- **Constat** : Les références de la v4 sur le vote tiennent à la lecture. Les logits 13 et 14 correspondent aux nœuds 77 et 78, puisque les sorties commencent au 64. Les 22 poids qui relient les 11 colonnes de ΔW à ces deux nœuds sont tous non nuls dans le bassin. Les colonnes des nœuds d'entrée sont bien inertes : l'observation les écrase à chaque pas et aucun logit ne les lit. Elles font 59 sur 172, soit 34,3 %.
- **Preuve** : backend_torch.py:200 (logits = H_new[:, N-O:N]) et :159 (H[:, :I] = obs_t) ; world_1_stoneage.py:1269 (appel du vote) ; sortie : 22 / 22
- **Classe** : aucune
- **Verdict** : non confirmé

### P8.5 — état récurrent remis à zéro
- **Sonde** : `grep -n 'need_rebuild\|self.agents = survivors' src/worlds/world_1_stoneage.py` ; `sed -n 109,111p src/agents/backend_torch.py`
- **Constat** : À chaque mort de phase 2, la population torch est reconstruite et H revient à zéro pour tous les survivants. Une condition qui tue plus remet donc l'état à zéro plus souvent. C'est un couplage entre la VD et la dynamique récurrente, commun à tous les bras et hérité des runs publiés. Il relève du mécanisme (P10), pas de l'aliasing.
- **Preuve** : world_1_stoneage.py:1784 (self.agents = survivors) → :1060-1066 (reconstruction quand B change) → backend_torch.py:111 (self.H = torch.zeros)
- **Classe** : aucune
- **Verdict** : hors périmètre

## P9

### P9.1 (DÉLÉGUÉ) — provenance : porte 20 sur la cible
- **Sonde** : `python tools/check_evidence_provenance.py --only C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/e63b8e13-dd83-4068-9b84-4fba689a7d72/scratchpad/S2-BASSIN-FRAGILITY.v4.json ; echo $?`
- **Constat** : La porte rend vert (exit 0), mais ce vert ne dit rien de la cible. Elle ne parcourt que les records EDR : le JSON de règle, placé dans le scratchpad, n'entre pas dans son balayage. Le filtre --only a seulement exclu toute la liste, et la ligne OK rapporte les 18 légataires de tout le dépôt. Verdict de la porte recopié : OK. Il est vide pour cet objet.
- **Preuve** : sortie : 'records : 304 | ... | absents : 18 | records fautifs : 17' puis 'OK : 18 chemin(s) legataire(s) gele(s)', exit 0 ; tools/check_evidence_provenance.py:352 et :362 (le filtre ne garde que les clés de records EDR)
- **Classe** : aucune
- **Verdict** : hors périmètre

### P9.2 (DÉLÉGUÉ) — défaut de la porte 20 elle-même, vu en la lançant
- **Sonde** : `python tools/check_evidence_provenance.py --only docs/EDR/INEXISTANT.md ; echo $?`
- **Constat** : Si --only nomme un chemin qu'aucun record ne porte, la porte ne refuse pas. Elle filtre tout, puis affiche OK avec exit 0. Un nom de record mal tapé passe donc pour une provenance vérifiée. Les portes 23 et 24 refusent déjà un --only vide ; la porte 20 n'a pas cette protection. C'est une dette à inscrire au backlog, avec son contre-exemple gelé.
- **Preuve** : sortie 'OK : 18 chemin(s) legataire(s) gele(s). Aucun nouveau, aucune regression.' et exit_only_bidon=0 ; tools/check_evidence_provenance.py:361-369 (aucun contrôle que les chemins donnés à --only existent ni qu'ils sont des records) et :383-385 (compte pris sur toutes les fautes, pas sur la sélection)
- **Classe** : E4
- **Verdict** : confirmé

### P9.3 — les results/ cités par la cible existent-ils, sont-ils suivis ?
- **Sonde** : `for p in results/s2_bassin_fragility_sonde_conception.json; do echo disque=$(test -f $p && echo 1) index=$(git ls-files -- $p | wc -l) head=$(git cat-file -e HEAD:$p 2>/dev/null && echo 1 || echo 0); done ; git check-ignore -v results/s2_bassin_fragility_genomes/x.npz`
- **Constat** : La cible cite deux artefacts de résultats. (1) Le JSON de sonde de conception existe sur disque et figure dans l'index, mais pas encore dans HEAD. Il est seulement stagé, donc il doit partir dans le même commit que le sceau. (2) Le dossier de génomes est volontairement exclu de git par .gitignore:18 ; sa provenance ne sera qu'un sha256 publié par l'agrégat, ce que la porte classerait par_hash, déclaratif. Aucun défaut de provenance à ce stade du pré-sceau.
- **Preuve** : disque=1 index=1 head=0 (HEAD de la worktree = 82927108) ; '.gitignore:18:results/*  results/s2_bassin_fragility_genomes/x.npz' ; grep des motifs results/ dans la cible : 3 motifs (results/*, results/s2_bassin_fragility_genomes/, sonde_conception.json cité 2 fois)
- **Classe** : E27
- **Verdict** : non confirmé

### P9.4 (DÉLÉGUÉ) — sceau de la pré-inscription
- **Sonde** : `python -c "from tools.preregister import verify; verify('S2-BASSIN-FRAGILITY')"` ; `python scratchpad/p9_sonde.py` (calcule _seal(v4), puis preregister avec _dir temporaire, sans puis avec reviewed_by, et verify)
- **Constat** : La porte lève : aucune règle sous ce nom n'existe dans docs/preregistrations, ni dans la worktree ni dans le checkout principal. Il n'y a donc pas de sceau à contrôler, ce qui est normal pour une revue faite avant le scellement. J'ai aussi fait un scellement à blanc dans un répertoire temporaire. Sans reviewed_by, il est refusé, car la règle déclare un coût. Avec reviewed_by, verify rend une règle identique à la v4. Hash que la v4 obtiendra au scellement : 4f24c6d342a56bd4cec57139b4e4b7c22bead8d56b1ef63506b38ab9346c23e6 ; comparer ce hash au sceau réel une fois la règle scellée.
- **Preuve** : FileNotFoundError : aucune pré-inscription « S2-BASSIN-FRAGILITY » ; grep bassin dans docs/preregistrations = 0 (worktree) et aucun résultat (checkout principal) ; p9_sonde : seal_v4 4f24c6d3...23e6, declare_un_cout True, exhaustive OK, sans reviewed_by -> ReviewRequired, verify tmp True
- **Classe** : aucune
- **Verdict** : hors périmètre

## P10

### P10.1
- **Sonde** : `sed -n 955,975p src/worlds/world_1_stoneage.py` ; `sed -n 195,210p src/agents/backend_torch.py` ; python -c (np.load results/warm003_dagger_genome.npz) -> 'N 172 I 59 O 108 N-O 64' ; `grep -n CONDITION_GATE src/agents/backend_torch.py`
- **Constat** : Le vote de groupe n'est pas seulement déclenché en aval des nœuds modifiés par le crédit : il ÉCRASE leur état. La ligne affectée par le vote est la vue des sorties (nœuds 64 à 171 pour le bassin, N−O = 64), qui contient les 11 nœuds où vit ΔW, tête de valeur comprise. À chaque tick de vote, l'effet du crédit ou du sham sur les actions de tout le groupe est remplacé par une moyenne pondérée par la forme physique, et l'état réécrit alimente le pas suivant. Ce masquage dépend de la condition. La docstring de compter_consensus dit l'inverse (canal hors des colonnes de ΔW), et la règle ne décrit qu'un lien indirect vers 77-78 par récurrence : que ce canal ne sépare pas les bras n'est pas établi par le code.
- **Preuve** : src/worlds/world_1_stoneage.py:972 (batch_logits[idx] = consensus_logits, ligne entière) ; src/agents/backend_torch.py:200 (logits = H_new[:, N-O:N], vue sans copie) et :48 (CONDITION_GATE = False, donc aucun clone) ; bassin N-O = 64 donc nœuds réécrits 64..171 ⊃ {64-71, 88, 89, 92} ; tools/evo_runs/s2_bassin_fragility.py:207-208 affirme « hors des colonnes où vit ΔW »
- **Classe** : E5
- **Verdict** : confirmé

### P10.2
- **Sonde** : python -c (médianes publiées) -> 'S_c med 7.5 [7.0..8.5]' ; 'b_tdoff med 7.5 [6.0..9.0]' ; 'b_eplr med 17.0' ; `grep -n reference_floor tools/evo_runs/s2_bassin_fragility.py` -> 0 ligne
- **Constat** : La paire de la garde E19 a son bras crédit collé au plancher au pas 0,04 : les objets appris de b_tdoff survivent en médiane 7,5, exactement la médiane de la cohorte froide S_c (7,5). Au pas 0,04, l'écart sham moins crédit ne peut donc pas devenir négatif et devient presque nul dès que le sham tombe lui aussi au plancher, ce qui donne une fermeture proche de 1. La garde appelée prévoit précisément ce cas avec reference_floor (effondrement contre artefact, P2.21), mais _garde_e19 ne le passe pas. Un effet de plancher serait alors lu comme DIRECTION_DEPEND_DU_REGLAGE, et la clause E19 n'invoque que deux causes, le pas et la létalité, jamais le plancher.
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:526 (appel sans reference_floor) ; tools/experiment_preflight.py:304 (reference_floor=None par défaut) et :344-352 (distingo P2.21 désactivé) ; b_tdoff 7,5 contre S_c 7,5 (results/s2_credit_ablation.json, results/s2_credit_retention.json)
- **Classe** : E3
- **Verdict** : confirmé

### P10.3
- **Sonde** : `python -c "np.load('results/warm003_dagger_genome.npz') ; (W!=0).sum() ; W[np.ix_(cols,[77,78])]"`
- **Constat** : Le compte de 22 poids non nuls, présenté comme preuve que les nœuds du crédit alimentent 77-78, ne pouvait pas donner un autre résultat : la matrice du bassin est entièrement dense. N'importe quel sous-bloc aurait rendu 100 % de non-nuls. Le chiffre ne dit rien de la force de ce couplage ; une preuve discriminante porterait sur la magnitude de ces poids ou sur la sensibilité des logits 13-14 à ΔW.
- **Preuve** : sortie : 'nnz W 29584 of 29584' ; 'W[cols,[77,78]] nnz 22 of 22'
- **Classe** : E1
- **Verdict** : confirmé

### P10.4
- **Sonde** : `grep -n workers tools/evo_runs/s2_bassin_fragility.py`
- **Constat** : La borne de six processus ouvriers, qui justifie la marge de contention du plafond (unité CPU acceptée jusqu'à 2000 s), n'est pas appliquée dans le code. --workers vient de SBF_WORKERS ou de la ligne de commande et arrive tel quel au pool, sans maximum, donc rien n'empêche un lancement hors du régime de charge déclaré.
- **Preuve** : tools/evo_runs/s2_bassin_fragility.py:1003 (default SBF_WORKERS '1', aucune borne) et :941 (ProcessPoolExecutor(max_workers=max(1, int(args.workers))))
- **Classe** : E10
- **Verdict** : confirmé

### P10.5
- **Sonde** : `python scratchpad/p10_sonde_shams.py` (W de la sonde de conception, shams purs) ; python -c (td_updates, résurrections des JSON P4.16/P4.9) ; `sed -n 165,192p tools/learning_events.py` ; `sed -n 144,164p tools/evo_runs/s2_credit_retention.py`
- **Constat** : J'ai vérifié les autres affirmations sur le code à la ligne ou par recalcul sans monde, et elles tiennent. Le crédit occupe 11 colonnes (8 pour eplr), ce qui correspond à N−O + {0..7, 24, 25, 28}. Les colonnes d'entrée pèsent 59/172 = 0,343. Le rapport L1/L2 d'un gaussien vaut 137,2 et ‖W_bassin‖₁ = 2442,8, soit ×24,3 pour full et ×718 pour zero. Le rapport de norme d'opérateur crédit/sham va de 1,06 à 1,54. Les compteurs td_updates valent 1999 sur 12/12 seeds quelles que soient les résurrections. Le pas effectif n'est publié que dans la branche TD. La phase 2 est bien gelée. L'appariement effectif en float32 tient à au plus 3,6e-6 (eps) : la tolérance de 1 % est une garde contre une machinerie cassée, pas un contrôle.
- **Preuve** : sortie : 'b_full cols=11 [64..71, 88, 89, 92] ... eps match_max=3.613e-06' ; 'b_eplr cols=8' ; 'td [1999]' pour full/tdonly/const/zero ; tools/learning_events.py:173,187,174 ; .gitignore:18 ; src/agents/backend_torch.py:32-35 ; tools/evo_runs/s2_credit_retention.py:148,163
- **Classe** : aucune
- **Verdict** : non confirmé

---

## Addendum de l'auteur (session SCIENCE-HARNAIS, 2026-09-26) — suites données, v4 → v5

Cette revue porte sur la v4 (sceau de brouillon `4f24c6d3…`) ; elle est INDISCRIMINANTE sur ce passage (témoin cru sain
7 recevables = minimum des défauts), ce qui borne ce qu'elle peut voir — ses critiques confirmées ont donc été
revérifiées une à une contre le code avant d'être suivies. La version soumise au sceau est la **v5**, relue à son tour
(`docs/reviews/2026-09-26-S2-BASSIN-FRAGILITY.v5.md`).

**Suites données aux critiques confirmées.**
- **P1.1 (E8)** — le défaut de fond de cette passe : FRAGILE sortait par la seule voie du COMPTAGE (un sham à 29 % de la
  perte, contraste médian +20 sur 10/12, était lu FRAGILE). FRAGILE exige désormais sham ERODE ET médiane(c) < 5 ; sham
  ERODE avec médiane(c) >= 5 sans 11/12 → NON_TRANCHE. Le scénario exact est gelé en test.
- **P1.2, P10.2 (E3), P5.2 (E19), P6.1 (E19), P4.4 (E30)** — garde E19 : écarts NORMALISÉS par la perte de greffe (part
  épargnée par le sham ; fermeture 0 pour un sham inerte), garde toujours exécutée et publiée mais réétiquetage
  seulement si LISIBLE (aucun bras de la paire saturé >= 0,9, et un bras DIRECTION/PARTIEL à défendre), égalité exacte à
  2/3 gardée invariante. Et c'est écrit : b_tdoff est au plancher dans les données publiées, AUCUNE paire de pas n'est
  lisible dans ce dispositif — la dépendance au pas n'est pas tranchable par ce run.
- **P1.3 (E8)** — la prédiction de b_tdoff dit « survie 7,5, soit −29,0 apparié ».
- **P4.2 (E10)** — bloc `seuils` scellé et confronté AU BIT aux constantes exécutées (`verifier_seuils`, appelé dans
  chaque commande) ; témoins : famille 16, clé en trop, bloc absent → lève.
- **P4.3 (E8)** — l'héritage des 5 ticks de P4.4 est écrit, avec ce qu'ils valent ici (≈60-67 % de S_tr au plancher).
- **P5.1 (E2)** — puissance connue d'avance publiée par bras (`moins_max_atteignable` : 11/12 sans marge pour const et
  eplr, seed 2036) et écrite dans la branche 10.
- **P5.3 (E1)** — la limite de 9b est APPLIQUÉE : `controle_direction_non_eprouve` si S_eps = S_a au bit sur 12/12.
- **P6.2 (E4), P6.3** — bande de DEMI-TIRAGES pour chaque contraste, 9b compris ; la dispersion par seed reste publiée.
- **P7.1 (E5)** — le brassage cerveau/corps du harnais immortel (résurrection en fin de liste, slots W figés) est
  VÉRIFIÉ à la lecture du code, déclaré dans `mesure` et « ne tranche pas », et inscrit au backlog (P2.132) : P4.18 le
  rejoue tel quel, puisque ce sont ces W qui ont produit les survies publiées.
- **P7.2 (E8)** — pas effectif (lr/12) et masse de gradient (×7,3) de la paire publiés à côté de la garde.
- **P8.1, P10.1 (E5)** — le vote réécrit la ligne entière des sorties (masque l'effet de ΔW au tick du vote) et un
  second écrivain (−0,1 sur le logit de la dernière action, `world_1_stoneage.py:1340`) existe : écrits, docstring du
  compteur corrigée.
- **P9.2 (E4)** — `--only` de la porte 20 : P2.128 (agagi-32).
- **P10.3 (E1)** — « 22/22 poids non nuls » ne prouvait rien (matrice dense) : remplacé par les magnitudes (L1 0,73 et
  0,93, ≈9-10 % de la L1 hors entrées des colonnes 77-78).
- **P10.4 (E10)** — la borne de 6 processus est appliquée (`--workers` > 6 lève).

Non confirmées ou hors périmètre : sans suite (P1.4, P2.1, P2.2, P3.1, P4.1, P4.5, P5.4, P6.4, P6.5, P7.3, P8.2, P8.3,
P8.4, P8.5, P9.1, P9.3, P9.4, P10.5).
