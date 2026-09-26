# Revue adversariale — E34-IDENTITY-CELL.v1

- **Cible** : `C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/E34-IDENTITY-CELL.v1.json` (pré-inscription brouillon, non scellée)
- **Date** : 2026-09-26
- **SHA** : `8ccdda52b5b401b6a8b3b761d8f766aa50726bb8` (worktree `.worktrees/e34`)

## Résultat des TÉMOINS

| témoin | statut | code | critiques recevables |
|---|---|---|---|
| S2-BLIND-CHAMPION-42e9357 | RETROUVE | 0 | 10 |
| EDR-GRAB-COST-1828371 | RETROUVE | 0 | 6 |
| EDR-RETAIN-COMPOSE-4204f8f | RETROUVE | 0 | 6 |
| LOCK-002-286f244 (cru sain) | MESURE | 0 | 6 |

**PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5**

**plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1) -- N imprime par --verifier ; S non imprime par --verifier (main n'affiche pas r['seuil']), lu dans seuil_critiques du roster, valeur que verdict_temoin rend (refutateur_temoins.py:504) ; 6 > 1, seuil depasse, MESURE sans barrage**

**⚠ INDISCRIMINANT : le record cru sain rend autant de critiques recevables que les defectueux**

Commandes de vérification (rejouables) :

- `PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34/tools/refutateur_temoins.py --verifier S2-BLIND-CHAMPION-42e9357 C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/refutateur_v1/critiques-S2-BLIND-CHAMPION-42e9357.json --extrait C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/temoins/temoin-1.md --jugement OUI`
- `PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34/tools/refutateur_temoins.py --verifier EDR-GRAB-COST-1828371 C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/refutateur_v1/critiques-EDR-GRAB-COST-1828371.json --extrait C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/temoins/temoin-3.md --jugement OUI`
- `PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34/tools/refutateur_temoins.py --verifier EDR-RETAIN-COMPOSE-4204f8f C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/refutateur_v1/critiques-EDR-RETAIN-COMPOSE-4204f8f.json --extrait C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/temoins/temoin-4.md --jugement OUI`
- `PYTHONIOENCODING=utf-8 python C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34/tools/refutateur_temoins.py --verifier LOCK-002-286f244 C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/refutateur_v1/critiques-LOCK-002-286f244.json --extrait C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/temoins/temoin-2.md`

Bilan : 32 critiques, **16 confirmées**, 11 non confirmées, 5 hors périmètre.

---

## P1 (JUGE) — prémisse porteuse

### P1.a — loi nulle porteuse (interchangeabilité inter-seed)

- **Sonde** : `python -c "import json;a=json.load(open('results/s2_credit_ablation_2.json',encoding='utf-8'));print(sorted((v['survival']['survival_median'],s) for s,v in a['arms']['b_full'].items()));print(a['replication']['identical'],a['replication']['measured_S'])"` (lancée au sha 8ccdda52, JSON non modifié sur disque)
- **Constat** : Ce qui décide MATERIEL contre NON_MATERIEL, c'est l'hypothèse que S_on, sous H0, se comporte comme un treizième tirage interchangeable avec les douze médianes inter-seeds (d'où 2/13, symétrique). Or au seed 2026 S_off vaut 7,0 : c'est le minimum de l'étendue, à égalité avec 2029. Pour une trajectoire rejouée au MÊME seed, il suffit donc d'UN pas de grille vers le bas (6,5) pour tomber en 5b. Il en faut SIX vers le haut (10,0) pour 5a. La variabilité intra-seed d'une trajectoire perturbée n'est mesurée ni dans ce run ni dans un JSON cité : la réplication donne un écart nul, jamais une dispersion. Le taux réel de fausse alarme de 5b est donc inconnu, et probablement bien au-dessus de 1/13 ; celui de 5a probablement en dessous. C'est la position de S_off qui oriente le verdict vers BAISSE, pas le drapeau, et c'est aussi ce qui rend peu atteignable le sens attendu (hausse). Dette proposée : centrer la bande sur S_off, ou mesurer la dispersion intra-seed avant de sceller. Réfutateur : aucun monde construit.
- **Preuve** : Sortie : [(7.0,'2026'),(7.0,'2029'),(7.5,'2027'),...,(9.5,'2030'),(9.5,'2037')] ; True 7.0. Valeur opposée : E34-IDENTITY-CELL.v1.json:8 déclare P(sortie)=2/13=0,1538 réparti sur les deux bords, alors que S_off=7,0=min de la bande (E34-IDENTITY-CELL.v1.json:7) : la sortie basse est à 0,5 et la sortie haute à 3,0 de S_off. Aucun champ intra-seed dans les clés de s2_credit_ablation_2.json (preregistration, design, provenance, regime, params, arms, cost, preflight, replication, rows, verdict)
- **Classe** : E8
- **Verdict** : **confirmé** — la loi nulle porteuse (interchangeabilité inter-seed) est supposée et non mesurée ; la donnée publiée la contredit, car S_off est au bord bas de la bande

### P1.b — les valeurs du témoin et de la bande

- **Sonde** : `python -c "import json;r=json.load(open('results/s2_credit_retention.json',encoding='utf-8'));c=r['arms']['b_warm_credit']['2026'];print(c['learning']['td_updates'],c['learning']['resurrections'],c['learning']['dW_abs_sum'],c['survival']['ages'],r['cost']['unit_b_warm_credit_s']);a=json.load(open('results/s2_credit_ablation_2.json',encoding='utf-8'));print(a['arms']['a_frozen']['2026']['survival']['survival_median'])"`
- **Constat** : J'ai confronté aux JSON suivis tous les chiffres dont dépendent la branche 2 (témoin rompu), les branches 5a-5c et les descriptifs. Âges du seed 2026 [5,6,6,7,7,7,7,8,8,9,9,11], td_updates 1999, resurrections 12, dW_abs_sum 18242.03954219818, ticks 2000/200, 12 agents : identiques dans s2_credit_retention.json (b_warm_credit) et dans s2_credit_ablation_2.json (b_full, replication.identical=True). Étendue b_full [7,0 ; 9,5], S_a du bassin gelé 31,5, unité 536 s : retrouvées aussi. Aucune de ces valeurs n'est recopiée de mémoire.
- **Preuve** : Sortie : 1999 12 18242.03954219818 [5, 6, 6, 7, 7, 7, 7, 8, 8, 9, 9, 11] 536.2984244823456 ; 31.5. Cohérent avec E34-IDENTITY-CELL.v1.json:6, :19, :23
- **Classe** : aucune
- **Verdict** : non confirmé — prémisses numériques mesurées et retrouvées

### P1.c — provenance de la bande (P4.16 contre P4.4)

- **Sonde** : `python -c "import json;a=json.load(open('results/s2_credit_ablation_2.json',encoding='utf-8'));print(a['cost']['b_full_imported'],a['cost']['cells_imported'],a['cost']['cells_measured'])"`
- **Constat** : Le texte date la bande de P4.16. Pourtant, dans ce fichier, 11 des 12 cellules b_full sont importées de P4.4 : seul le seed 2026 a été rejoué. Comme les médianes par seed sont identiques dans les deux JSON, l'étendue ne change pas et le verdict non plus. Il s'agit d'une attribution imprécise, pas d'une prémisse fausse.
- **Preuve** : Sortie : True 11 49 ; les médianes par seed de b_full (ablation_2) et de b_warm_credit (retention) coïncident sur les 12 seeds (7.0,7.5,8.0,7.0,9.5,8.0,8.0,7.5,9.0,8.5,8.0,9.5)
- **Classe** : aucune
- **Verdict** : non confirmé — sans effet sur le verdict

## P2 (DELEGUE) — Régime : chaque paramètre cité est-il publié par l'évidence ?

- **Sonde** : `cd C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34 && python tools/check_regime_claims.py --only "C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/E34-IDENTITY-CELL.v1.json"; echo EXIT=$?` (HEAD 8ccdda52)
- **Constat** : La porte 19 refuse de juger la cible : elle n'accepte que des records Markdown sous docs/EDR, et la cible est une regle de pre-inscription JSON non scellee posee dans le scratchpad. Verdict de la porte recopie tel quel (REFUS, sortie 2), aucune enquete rouverte. Les valeurs de regime que la regle invoque (reward_scale, ticks des deux phases, bande lue dans un JSON suivi) ne sont donc confrontees a rien par cette porte ; si ce trou doit etre comble, c'est une dette au backlog, pas une critique.
- **Preuve** : Sortie : 'REFUS : --only designe 1 chemin(s) INCONNU(S) de cette porte -- ni record docs/EDR/<nom>.md present, ni record supprime par le commit en cours' ; EXIT=2. Perimetre code en dur : tools/check_regime_claims.py:353-355 (_est_record : docs/EDR/<nom>.md seulement).
- **Classe** : aucune
- **Verdict** : hors périmètre

## P3 (DELEGUE) — Balayage du pas / garde E19

- **Sonde** : `cd .worktrees/e34 && python tools/check_e19_optimizer_sweep.py --only tools/evo_runs/e34_identity_cell.py; echo exit=$? ; grep -n "verify" tools/evo_runs/e34_identity_cell.py ; ls docs/preregistrations | grep -i e34`
- **Constat** : Porte lancee au sha 8ccdda52 sur le runner de la cellule : elle rend OK (exit 0) et ne bloque rien, mais elle ne juge pas le fond. Elle classe e34_identity_cell.py en regle_absente parce que verify(PREREG) (ligne 201 et 234) vise docs/preregistrations/E34-IDENTITY-CELL.json, qui n'existe pas encore : la cible relue n'est qu'un brouillon v1 dans le scratchpad. La porte ne dit donc ni que le runner est sous gradient, ni qu'il est couvert. Verdict recopie, sans rouvrir l'enquete. La question P3 reste ouverte et se rejoue apres le sceau. Au passage, un point possible sur la porte elle-meme, qui releve d'une dette et pas d'une critique : la ligne NOUVEAU affiche un motif vide apres les deux-points, sans nommer la regle manquante. La question de la reference a pas nul (on/off sous le meme td_enabled) releve de P5, pas d'ici.
- **Preuve** : Sortie de la porte : 'runners scelles : 34 | sous gradient (PLANCHER) : 11 | nus : 9 | indetermines : 4 | non resolus : 6 | regle absente : 1 | illisibles : 0 | appelants de la garde : 2 | geles : 19' ; 'NOUVEAU (non bloquant) : [regle_absente] tools/evo_runs/e34_identity_cell.py : ' ; 'OK : aucun nouveau runner sous gradient sans garde E19' ; exit=0. tools/evo_runs/e34_identity_cell.py:201 et :234 appellent verify(PREREG), avec PREREG=E34-IDENTITY-CELL en :38. ls docs/preregistrations | grep -i e34 ne rend rien, donc la regle n'est pas scellee.
- **Classe** : aucune
- **Verdict** : non confirmé -- la porte E19 rend OK (exit 0) sans juger le runner, classe regle_absente tant que la regle n'est pas scellee ; P3 est a rejouer apres le sceau

## P4 (JUGE) — famille de contrôles

### P4.a — seuil hérité d'un autre dispositif

- **Sonde** : `python -c "import json;a=json.load(open('results/s2_credit_ablation_2.json',encoding='utf-8'));bf=a['arms']['b_full'];print(sorted(bf[s]['survival']['survival_median'] for s in bf), [s for s in sorted(bf) if bf[s]['survival']['survival_median']==7.0])" ; python -c "from tools.grid_compare import cmp_grille; [print(s, cmp_grille(s,7.0,0.0,2,sens=-1), cmp_grille(s,9.5,0.0,2,sens=+1)) for s in (6.5,7.0,9.5,10.0)]"`
- **Constat** : Le bord inferieur de la bande n'est pas un repere exterieur : c'est la survie publiee du seed teste lui-meme (7,0, ex aequo avec 2029, minimum des douze). Consequence sur la lecture : depuis S_off = 7,0, un seul cran de grille vers le bas (6,5) suffit a declencher MATERIEL_BAISSE, tandis qu'il en faut six vers le haut (10,0) pour MATERIEL_HAUSSE -- or c'est la hausse que P2.132 predit. Le taux 2/13 vaut pour un treizieme tirage interchangeable avec les seeds ; S_on est une autre trajectoire du seed deja place au plancher, donc lie a lui : la fausse alarme cote baisse est sous-estimee, et la puissance cote hausse est quasi nulle pour tout effet inferieur a +3 ticks. Le seuil est emprunte a la dispersion inter-seeds pour juger une perturbation intra-seed dont l'ampleur n'a jamais ete mesuree.
- **Preuve** : results/s2_credit_ablation_2.json b_full : tri [7.0, 7.0, 7.5, 7.5, 8.0, 8.0, 8.0, 8.0, 8.5, 9.0, 9.5, 9.5], seeds a 7.0 = ['2026','2029'] ; results/s2_credit_retention.json b_warm_credit seed 2026 : survival_median 7.0 (valeur que le bras eteint doit reproduire au bit). Rejeu cmp_grille : 6.5 -> BAISSE, 7.0 et 9.5 -> rien, 10.0 -> HAUSSE, soit 1 pas contre 6. Taux code : tools/evo_runs/e34_identity_cell.py:132 (2/(n+1)) ; lecture :160-162 ; cible E34-IDENTITY-CELL.v1.json:8 (2/13) et :20 (sens attendu 5a) ; aucune ligne de la cible (grep 2026 -> lignes 2,4,6,19) ne dit que S_off est le minimum de la bande.
- **Classe** : E8
- **Verdict** : **confirmé**

### P4.b — taille réelle contre taille déclarée

- **Sonde** : `python tools/check_control_family.py --report ; python tools/check_control_family.py --only tools/evo_runs/e34_identity_cell.py ; grep -n "^DOSE_MIN\|^DELTA_MIN" tools/evo_runs/s2_credit_retention.py`
- **Constat** : Compte fait a la lecture du runner : deux cellules (off, on) ; une seule decision, bilaterale, par deux comparaisons strictes aux bords ; l'etiquette FORT est calculee mais ne modifie jamais le verdict. Le taux publie par le code couvre bien deux queues. Les seuils importes de P4.4 (dose 1000, ecart 5,0) sont ceux que la regle ecrit, et viennent du meme harnais (phase immortelle de 2000 ticks). La taille de famille declaree tient ; le defaut est dans le TAUX et dans la position de la bande (critique precedente), pas dans le compte des cellules.
- **Preuve** : porte 11 : runners scelles 32 | sans design 0 (dont 0 NOUVEAUX) | legataires geles 0 ; --only : OK, exit 0. tools/evo_runs/e34_identity_cell.py:40 ARMS = (off, on) ; :159 fort descriptif ; :160-165 seule branche decisive ; tools/evo_runs/s2_credit_retention.py:47 DOSE_MIN = 1000, :49 DELTA_MIN = 5.0 (cible :13 seuil 1000, :19 seuil 5 ticks).
- **Classe** : aucune
- **Verdict** : non confirmé

## P5

### P5.a — asymétrie des deux issues matérielles

- **Sonde** : `python C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/p5_probe_e34.py` (injecte des S_on connus dans identity_cell_verdict, avec la bande réelle et S_a lus dans results/s2_credit_ablation_2.json)
- **Constat** : Le seed retenu est celui dont la survie publiée tombe exactement sur la borne basse de l'étendue, donc les deux issues matérielles ne sont pas à la même distance. Un recul d'un demi-tick (un pas de grille) déclenche MATERIEL_BAISSE, alors que le sens prédit, la hausse, exige +3 (six pas). Le taux 2/13 suppose que S_on se tire comme un seed de plus parmi les douze. Or S_on est une perturbation de trajectoire autour de 7,0, et 7,0 est justement le minimum de la bande. Sous H0, la fausse alarme vers le bas vaut donc à peu près P(S_on < S_off), et non 0,15. La fonction publie pourtant une constante, quelle que soit la place de S_off.
- **Preuve** : results/s2_credit_ablation_2.json arms.b_full : seed 2026 = 7.0 = min de [7.0, 9.5]. Injection : S_on 6.5 (dS -0.5) -> MATERIEL_BAISSE ; S_on 9.5 (dS +2.5) -> NON_MATERIEL ; S_on 10.0 (dS +3.0) -> MATERIEL_HAUSSE. fausse_alarme_h0 = 0.154 sur les 7 injections (tools/evo_runs/e34_identity_cell.py:132, 2/(n+1) sans conditionnement sur S_off).
- **Classe** : E2 (l'issue attendue est structurellement plus difficile à atteindre que l'issue opposée), voisine de E1
- **Verdict** : **confirmé**

### P5.b — témoin et paire comparée de deux exécutions différentes

- **Sonde** : `python C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/p5_probe_e34_lieu.py`
- **Constat** : Le contrôle du code et la paire comparée peuvent venir de deux exécutions différentes. La lecture accepte un --temoin pris dans un autre fichier que le bras éteint. Ensuite, identity_cell_verdict ne vérifie à aucun moment que la ligne éteinte lue porte les âges et le Σ|ΔW| que le témoin a certifiés. Un bras éteint qui n'est pas la cellule publiée passe donc la barrière du témoin et reçoit quand même un verdict matériel. Le témoin certifie un dispositif, la comparaison en lit un autre.
- **Preuve** : tools/evo_runs/e34_identity_cell.py:241-245 (tem_p = args.temoin or off_p ; off vient toujours de off_p) et :151 (seul witness['identical'] est consulté). Injection : off S=9.5, Σ|ΔW|=17000 contre un témoin identique ailleurs (18242.03954219818) -> MATERIEL_HAUSSE avec dS = +0.5.
- **Classe** : E31
- **Verdict** : **confirmé**

### P5.c — lieu d'origine de la bande non publié

- **Sonde** : `python -c "import json; d=json.load(open('results/s2_credit_ablation_2.json',encoding='utf-8')); print(d['provenance'], d['cost'].get('b_full_imported')); s=json.dumps(d); print([s.count(k) for k in ('platform','host','lieu','batcave','nexus','cu124')])"`
- **Constat** : Rien dans l'évidence de la bande n'indique la machine ni la version de torch qui l'ont produite. La provenance se limite à un sha, marqué dirty, et le bras b_full y est signalé comme importé. Or la clause du scellé sur l'invariance au lieu suppose que la bande a une origine connue (la batcave). Cette origine n'est lisible nulle part dans le JSON : c'est une inférence, pas une mesure.
- **Preuve** : provenance = {git_sha 16163f306cbd…, dirty: true} ; b_full_imported = true ; occurrences de platform/host/lieu/batcave/nexus/cu124 = 0/0/0/0/0/0
- **Classe** : E8
- **Verdict** : **confirmé**

### P5.d — témoin et bande du même dispositif

- **Sonde** : python -c comparant results/s2_credit_retention.json arms.b_warm_credit et results/s2_credit_ablation_2.json arms.b_full, et diff de tools.evo_runs.s2_credit_retention.REGIME contre le bloc regime
- **Constat** : J'ai vérifié que le témoin (P4.4 b_warm_credit) et la bande (P4.16 b_full) sortent bien du même dispositif et du même régime. Au seed 2026, les âges et le Σ|ΔW| sont égaux, l'étendue sur les 12 seeds est la même, et REGIME ne diffère du bloc regime de P4.16 que par des clés propres aux bras. Aucun défaut sur ce point.
- **Preuve** : ages égaux True, dW égal True (18242.03954219818) ; bande P4.4 [7.0, 9.5] = bande P4.16 [7.0, 9.5] ; clés qui diffèrent = {lr_low, lr_published, arms_credit}
- **Classe** : aucune
- **Verdict** : non confirmé

### P5.e — gardes de pré-vol

- **Sonde** : `grep -n "assert_positive_control\|assert_not_degenerate\|assert_ablation_changes_something" tools/evo_runs/e34_identity_cell.py`
- **Constat** : Le runner n'appelle aucune des trois gardes de pré-vol, mais leur rôle est tenu en ligne. Une cellule publiée sans désalignement sort en SANS_OBJET, un bras allumé qui garde des tranches désalignées lève, et une DV non finie lève. Quant à la référence à pas nul (volet E19), elle ne s'applique pas : aucun des deux bras ne fait varier le pas.
- **Preuve** : 0 occurrence ; équivalents aux lignes e34_identity_cell.py:154 (SANS_OBJET), :137-140 (levée si misaligned_on != 0), :116-117 (_needs) ; lr = None dans les deux bras (:86)
- **Classe** : aucune
- **Verdict** : hors périmètre

## P6 (JUGE) — plancher de bruit

### P6.a — position de la référence dans la bande

- **Sonde** : python -c (lecture de results/s2_credit_ablation_2.json, arms.b_full.*.survival.survival_median, min/max) ; Read tools/evo_runs/e34_identity_cell.py:53-66 et :121-170 ; python -c qui injecte dans identity_cell_verdict une ligne off à 7,0 et des lignes on à 6,5 / 7,0 / 9,5 / 10,0 (aucun monde construit)
- **Constat** : La cellule de référence (seed 2026, médiane 7,0) compte parmi les douze valeurs qui fixent l'étendue, et elle en occupe le minimum, ex aequo avec 2029. Le lecteur est donc asymétrique : reculer d'un seul pas de grille (-0,5) suffit à déclencher la branche baisse, alors que le sens annoncé (hausse) exige +3,0, soit six pas. Le taux 2/13 que le verdict imprime suppose que le bras allumé soit un tirage neuf, échangeable avec les douze seeds. Or il partage avec le bras éteint le monde, la cohorte et le début de trajectoire du seed 2026 : sous H0, sa chance de passer sous 7,0 dépend d'un bruit intra-seed jamais mesuré, et non de 2/13. La pré-inscription ne signale pas que la référence est au bord.
- **Preuve** : Médianes b_full : 2026=7.0, 2029=7.0, 2030=9.5, 2037=9.5 -> min 7.0 (2 seeds), max 9.5 (2 seeds). e34_identity_cell.py:58-65 prend les 12 seeds, 2026 compris ; :132 fixe fausse_alarme_h0 = 2/(n+1) = 0,154, que S_off soit au bord ou non. Injection : S_on 6,5 -> MATERIEL_BAISSE (dS -0,5) ; 9,5 -> NON_MATERIEL (dS +2,5) ; 10,0 -> MATERIEL_HAUSSE (dS +3,0).
- **Classe** : E7
- **Verdict** : **confirmé**

### P6.b — no-op exact du contraste

- **Sonde** : `grep -niE "no.?op"` sur la cible E34-IDENTITY-CELL.v1.json ; même grep sur tools/evo_runs/e34_identity_cell.py ; `grep -ciE "no.?op" results/s2_credit_ablation_2.json results/s2_credit_retention.json` ; injection ci-dessus (part_erosion_levee)
- **Constat** : Aucun plancher de bruit propre à ce contraste n'est prévu. La réplication bit-identique (écart nul) contrôle le code, pas l'effet du drapeau, qui modifie surtout la trajectoire. Il manque un bras qui ferait dévier la trajectoire SANS réparer l'identité (drapeau factice, permutation neutre ou tirage RNG supplémentaire) : c'est lui qui donnerait la bande de CE contraste. L'étendue entre seeds le remplace par une hypothèse. Les descriptifs ont le même manque : la part d'érosion levée vaut dS/24,5, soit 0,020 par pas de grille, et elle est publiée sans bande ; l'étiquette FORT (|dS| >= 5) aussi.
- **Preuve** : grep no.?op : 0 ligne dans la cible, 0 ligne dans le runner ; s2_credit_ablation_2.json : 2 lignes (:11 et :3324, noop_exact_vs_P49 = no-op de P4.16, pas du drapeau) ; s2_credit_retention.json : 0. Injection : part_erosion_levee = -0,0204 pour dS = -0,5 (S_a 31,5 - S_off 7,0 = 24,5).
- **Classe** : E8
- **Verdict** : **confirmé**

### P6.c — la bande vient-elle du même dispositif que le témoin ?

- **Sonde** : python -c qui compare arms.b_full[s] de results/s2_credit_ablation_2.json à arms.b_warm_credit[s] de results/s2_credit_retention.json, et imprime d['replication']
- **Constat** : Oui, et ce n'est donc pas un défaut. Le bras b_full de P4.16 (source de la bande) et le bras b_warm_credit de P4.4 (source du témoin) donnent la même médiane sur chacun des douze seeds, et le bloc replication de P4.16 déclare le seed 2026 bit-identique (âges, dW). La bande et le témoin viennent donc bien du même harnais, au même régime.
- **Preuve** : 12/12 paires égales (2026: 7.0/7.0 ... 2037: 9.5/9.5) ; replication : identical=true, p44_dW_abs_sum = measured_dW_abs_sum = 18242.03954219818, td_updates 1999, resurrections 12
- **Classe** : aucune
- **Verdict** : non confirmé

## P7

### P7.a — SANS_OBJET sur audit aveugle

- **Sonde** : `python C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/p7_sonde.py` (injection à dose connue dans identity_cell_verdict, aucun monde construit)
- **Constat** : Le bras éteint peut rendre SANS_OBJET sans avoir rien mesuré. Si l'audit n'a apparié aucun tick (ticks_known = 0, slot_ticks_total = 0), le compteur de tranches mal appariées reste à 0 PAR ABSENCE, et la branche 3 en tire que le défaut n'a pas agi. Ni la règle ni _needs n'exigent ticks_known > 0 ou ticks_unknown = 0 : une dose de défaut non mesurée devient une dose nulle affirmée, c'est-à-dire un négatif de fond fabriqué à partir d'un vide.
- **Preuve** : tools/evo_runs/e34_identity_cell.py:154 (seul test : misaligned_off == 0) et :113-117 (_needs ne contrôle que la finitude, et 0 est fini). Sortie : « audit aveugle (ticks_known=0, total=0) -> SANS_OBJET ».
- **Classe** : E4
- **Verdict** : **confirmé**

### P7.b — dose du traitement sans plancher

- **Sonde** : même script : ligne éteinte injectée avec slot_ticks_misaligned = 1, slot_ticks_total = 24000, S_on = 8,0
- **Constat** : La dose du TRAITEMENT n'a pas de plancher : une seule valeur l'écarte, zéro exactement. Un slot-tick mal apparié sur 24 000 suffit à ouvrir la lecture 5c et sa note de robustesse, parce que la fraction mal appariée et first_misaligned_tick ne sont que descriptifs et n'entrent dans aucune branche. Un NON_MATERIEL peut donc venir d'un défaut presque absent de la cellule, pas de l'absence d'effet. Or la cellule publiée ne donne que le nombre de résurrections (12), jamais leur date : sa dose de défaut est inconnue.
- **Preuve** : Sortie : « dose 1/24000 -> NON_MATERIEL | S_on 8.0 dans l'étendue publiée [7.0, 9.5] ». La règle, ligne 19 (champ descriptifs), classe la fraction des slot-ticks du bras éteint parmi les valeurs qui ne décident rien. Code : e34_identity_cell.py:154.
- **Classe** : E2
- **Verdict** : **confirmé**

### P7.c — td_updates ne mesure pas la dose reçue par le bon corps

- **Sonde** : python -c qui lit td_updates et resurrections par bras dans results/s2_credit_retention.json et results/s2_credit_ablation_2.json ; puis une injection td_on = 1999 avec resur_on = 946
- **Constat** : td_updates compte les appels à learn qui ont rendu une perte, au niveau de TOUTE la population. Dès que le TD est actif, il vaut ticks − 1 par construction : la branche 4 (seuil 1000) vérifie que le TD tourne, pas qu'un corps a reçu sa dose. Il ne voit pas non plus vers quelle tranche une mise à jour est allée. Le verdict publie donc la même dose, 1999, pour les deux bras, alors que la différence entre eux tient justement à l'acheminement. La dose reçue par le BON corps, slot_ticks_total − slot_ticks_misaligned, n'est ni calculée ni lue.
- **Preuve** : 60 cellules apprenantes à td = 1999 : b_warm_credit (résurrections 2-30), c_cold_credit (5-946), b_full, b_tdonly, b_const. b_eplr, TD coupé, est à 0. src/agents/backend_torch.py:216 et :224 : learn ne rend None qu'au premier appel. L'injection avec 946 résurrections rend NON_MATERIEL.
- **Classe** : E1
- **Verdict** : **confirmé**

### P7.d — bande produite sous défaut actif

- **Sonde** : python -c : dans results/s2_credit_ablation_2.json, compter les cellules b_full dont le bloc learning contient slot_identity, et lister (seed, S, résurrections)
- **Constat** : La bande de lecture [7,0 ; 9,5] vient de cellules b_full où le défaut E34 AGISSAIT à une dose jamais mesurée : aucun audit d'identité, et 2 à 30 résurrections selon le seed. S_on, mesuré défaut retiré, est donc comparé à une dispersion que le défaut a peut-être produite en partie. C'est une question de dispositif de comparaison, qui relève de P1/P5 et non de la dose de l'apprenant.
- **Preuve** : slot_identity présent dans 0/12 cellules b_full. Survies médianes de 7,0 à 9,5, résurrections de 2 à 30. Par exemple seed 2037 : S 9,5 avec 2 résurrections ; seed 2026 : S 7,0 avec 12.
- **Classe** : aucune
- **Verdict** : hors périmètre

### P7.e — constance de la cohorte

- **Sonde** : `grep -n dead_agents.append src/worlds/world_1_stoneage.py` ; lecture de e34_identity_cell.py:145-146 et s2_credit_retention.py:213-221
- **Constat** : La cohorte de la phase 1 est constante par construction (tous les morts reviennent). Les résurrections sont publiées dans les deux bras, et la phase 2 publie la liste des âges. _needs ne vérifie pas que len(ages) vaut num_agents, mais je n'ai trouvé aucun chemin par lequel un agent disparaîtrait sans passer par dead_agents.
- **Preuve** : world_1_stoneage.py:1681 est le seul ajout à dead_agents. e34_identity_cell.py:145-146 publie resurrections_off et resurrections_on. Le témoin publié donne 12 âges pour 12 agents.
- **Classe** : aucune
- **Verdict** : non confirmé

## P8

### P8.a — clones à phénotype figé : la dose surestime le tort

- **Sonde** : `python scratchpad/p8_sonde.py` (3 clones via from_genome, aucun monde) ; `grep -rn update_phenotype src/` ; `grep -n 'slot_ticks_misaligned|positions_reordered' tools/evo_runs/s2_credit_retention.py` ; lecture de results/s2_credit_retention.json arms/b_warm_credit/2026
- **Constat** : Les douze sujets sont des clones d'un même génome, et leur phénotype (hp_bonus, inv_capacity, drain) est figé au clonage : l'écriture de retour des poids appris ne le recalcule jamais, et la phase 2 ré-apparie chaque modèle à son propre corps dans un monde neuf, avec une médiane sur la cohorte. Un décalage tranche/corps qui PERSISTE n'est donc qu'un ré-étiquetage entre corps identiques ; le tort réel se concentre aux ticks où le décalage SE PRODUIT (une transition TD croisée par tranche déplacée, un transitoire de H, une fenêtre épisodique k=8 rejouée sur l'autre corps). Or la dose du bras éteint cumule chaque tick où le décalage dure, et ce bras ne compte pas les déplacements eux-mêmes (compteur incrémenté seulement sous drapeau). Avec 12 résurrections publiées, au plus 144 déplacements contre 24 000 slot-ticks : la fraction publiée surestimera la dose de deux ordres, et un NON_MATERIEL lu à côté passerait pour une robustesse à une dose massive.
- **Preuve** : 3 clones : (688.82666, 70, 14.888267) identiques ; après write-back simulé hp_bonus reste 688.82666 contre 8613.29 recalculé ; update_phenotype appelé seulement à mamba_agent.py:140,152,177,198 et world_1_stoneage.py:990, jamais par backend_torch.py:509-513 ; drain lu figé à world_1_stoneage.py:702 ; dose cumulée à s2_credit_retention.py:158, déplacements comptés seulement sous drapeau à :147 ; JSON publié : resurrections 12, ticks 2000, n 12.
- **Classe** : aucune
- **Verdict** : **confirmé**

### P8.b — l'état récurrent est écrit par le monde (aliasing)

- **Sonde** : `python scratchpad/p8_sonde.py` (forward, puis lg[1][2] -= 0.1, np.shares_memory) ; `grep -n 'logits\[' src/worlds/world_1_stoneage.py` ; `grep -n 'shares_memory|-= 0.1|_apply_social_consensus' docs/REF/REGISTRE_ERREURS.md docs/roadmap/PRIORITES_ET_DETTES.md`
- **Constat** : L'état récurrent de la population torch est ÉCRIT par le monde : forward rend les logits comme une vue numpy d'une tranche de H (device cpu, pas de porte donc pas de clone), puis le monde retranche 0,1 au logit de la dernière action et le consensus social réécrit des lignes, en place. Le H que le drapeau ré-apparie porte donc un canal côté corps (last_action) que le design ne liste pas parmi ses liens. Commun aux deux bras et au harnais publié P4.4-P4.16 : ne biaise pas S_on contre la bande, mais c'est un aliasing inscrit ni au registre ni au backlog.
- **Preuve** : H[1,N-O+2] 0.99086 -> 0.89086 après écriture dans les logits, shares_memory True, TorchPopulationModel device cpu gate False ; écritures en place world_1_stoneage.py:1340 et :973 ; logits = tranche de H_new, backend_torch.py:198-200 et :210 ; grep registre + backlog : 0 ligne.
- **Classe** : E5
- **Verdict** : **confirmé** — hérité du harnais publié, commun aux deux bras

### P8.c — chevauchement entrée/sortie

- **Sonde** : `python tools/check_io_overlap.py ; python scratchpad/p8_sonde.py`
- **Constat** : Pas de chevauchement entrée/sortie : le bassin cloné déclare 59 entrées et 108 sorties sur 172 nœuds, marge de 5 ; la porte ne signale aucun génome nouveau.
- **Preuve** : porte : 358 génomes, 10 chevauchants connus, 0 nouveau, 0 aggravé ; bassin I/O/N 59/108/172, chevauchement -5.
- **Classe** : E24
- **Verdict** : non confirmé

### P8.d — voie E26 ouverte par l'intervention ?

- **Sonde** : `grep -c 'W\[' tools/evo_runs/e34_identity_cell.py` ; lecture tools/slot_identity.py
- **Constat** : Le drapeau n'édite aucune ligne de W : il permute la liste des corps dans l'ordre de construction de la population ; et le corps ne peut pas suivre W appris (phénotype figé, critique 1). Aucune voie E26 ouverte par l'intervention.
- **Preuve** : 0 occurrence dans le runner ; tools/slot_identity.py:67-69 (tri puis affectation e.agents[:]) ; seule mention de W[ dans slot_identity.py:5 (docstring).
- **Classe** : E26
- **Verdict** : non confirmé

## P9 (DELEGUE)

### P9.a — provenance des results/ cités, porte 20

- **Sonde** : `python tools/check_evidence_provenance.py --only C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/E34-IDENTITY-CELL.v1.json ; echo exit=$?` (HEAD 8ccdda52)
- **Constat** : La porte 20 refuse la cible : elle ne juge que des records sous docs/EDR, or la cible est une pre-inscription brouillon posee dans le scratchpad. Verdict de porte recopie : REFUS, code 2. Les deux results/ que la regle cite (s2_credit_retention.json, s2_credit_ablation_2.json) n'ont donc recu AUCUN verdict de provenance de la porte ; il reviendra au record qui citera ces fichiers de le recevoir.
- **Preuve** : sortie : 'REFUS : --only designe 1 chemin(s) INCONNU(S) de cette porte -- ni record docs/EDR/<nom>.md present' ; exit=2
- **Classe** : aucune
- **Verdict** : hors périmètre

### P9.b — sceau de la pré-inscription, tools.preregister.verify

- **Sonde** : `python -c "from tools.preregister import verify; verify('E34-IDENTITY-CELL.v1')"` puis `verify('E34-IDENTITY-CELL')` ; `ls docs/preregistrations | grep -ci e34`
- **Constat** : Il n'existe aucun sceau, donc aucun sceau rompu : verify leve FileNotFoundError sous les deux noms possibles, et docs/preregistrations ne contient aucun fichier e34. C'est l'etat attendu a ce stade : budget_s et plafond font partie des cles de cout, et une regle qui declare un cout ne se scelle qu'avec reviewed_by, donc apres la revue en cours. Le verdict de la porte est recopie tel quel : elle n'a pas encore ete scellee.
- **Preuve** : les deux appels : FileNotFoundError 'aucune pre-inscription ... n'a pas ete scellee avant le run' ; grep -ci e34 = 0 ; tools/preregister.py:57 _CLES_COUT contient budget_s et plafond
- **Classe** : aucune
- **Verdict** : non confirmé

### P9.c — dette sur l'instrument verify, vue en passant

- **Sonde** : `python -c "from tools.preregister import verify; verify('E34-IDENTITY-CELL.v1', _dir=r'<scratchpad>')"` ; `python -c "import json; d=json.load(open(<cible>)); print(len(d), 'seal' in d, 'rule' in d)"`
- **Constat** : verify, appelee avec _dir sur le scratchpad, lit le brouillon qui n'a jamais ete enveloppe (16 cles, sans seal ni rule). Elle compare le hash d'une regle VIDE a None et affirme que le fichier a ete edite apres son enregistrement. L'absence d'enveloppe produit donc une accusation d'alteration, c'est-a-dire une affirmation de fond au lieu de 'ce fichier n'est pas une pre-inscription'. Regle DELEGUE : c'est une dette sur la porte, pas une critique de la cible.
- **Preuve** : sortie 1 : PreregistrationTampered '... ne correspond plus a son sceau : le fichier a ete edite apres enregistrement' ; sortie 2 : '16 cles; seal False ; rule False' ; tools/preregister.py:199 : _seal(payload.get('rule', {})) != payload.get('seal')
- **Classe** : aucune
- **Verdict** : hors périmètre

## P10 (JUGE) — mécanisme et référents

### P10.a — ce que compte la dose slot_ticks_misaligned

- **Sonde** : `sed -n 191,230p src/agents/backend_torch.py ; sed -n 1250,1260p src/worlds/world_1_stoneage.py ; sed -n 1750,1785p src/worlds/world_1_stoneage.py ; python C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/p10_sondes.py`
- **Constat** : Entre deux morts, une tranche est lue ET créditée sur un seul corps : le forward suit l'ordre courant (world_1_stoneage.py:1254-1256), learn reçoit récompenses et actions dans ce même ordre (:1763-1765), et la transition TD est bâtie sur l'obs de ce forward (backend_torch.py:199,226). Les corps ne se mélangent qu'au tick de permutation : V(s') est bootstrappé sur le nouveau corps (:220,225), H est hérité (:195), et une fenêtre épisodique est à cheval (world:1092). Or l'audit compare à l'ordre de CONSTRUCTION, écart qui persiste en général jusqu'à la fin de la phase : il reflète la précocité de la première mort, pas le nombre de mises à jour contaminées. Le compte de corps changés par tranche n'est relevé que sous drapeau (s2_credit_retention.py:143-147), jamais dans le bras éteint. La dose publiée et le mécanisme du sens attendu surestiment donc l'exposition réelle de deux ordres de grandeur. La branche 3 (zéro) reste valide.
- **Preuve** : Sortie de p10_sondes.py sur la cellule publiée (12 résurrections) : au plus 144 transitions TD entre corps sur 23988 (0,6 %) et au plus 144 épisodes-tranche sur 3000 (4,8 %), contre jusqu'à 24000 slot-ticks désalignés pour une seule mort en tête. Lignes : backend_torch.py:220,225 ; world_1_stoneage.py:1254,1765.
- **Classe** : E16
- **Verdict** : **confirmé**

### P10.b — référent de td_updates et branche 4

- **Sonde** : `grep -n "_prev = None\|self._prev = \|self._last = " src/agents/backend_torch.py ; sed -n 164,175p tools/learning_events.py ; python C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/p10_sondes.py`
- **Constat** : Sous drapeau, td_updates ne peut pas passer sous 1000. learn() ne rend None qu'au premier appel d'une population : _prev et _last ne sont remis à None qu'à la construction (backend_torch.py:92-93). Le drapeau ne provoque aucune reconstruction, puisque B reste constant (world:1060-1066). Le compteur vaut donc ticks-1 par construction, et INDETERMINE_DOSE est une branche morte. Le canal épisodique (episode_updates) n'est lu par aucune branche. Si le correctif échoue, SlotIdentityError est levée (s2_credit_retention.py:150) : on tombe dans INCOMPLET, jamais dans la branche 4.
- **Preuve** : Sur les 36 cellules publiées (P4.4 b_warm_credit et c_cold_credit, P4.16 b_full), td_updates = ticks_learn-1 = 1999 dans 36 cas sur 36. C'est vrai aussi pour les seeds qui comptent 30 résurrections. Resets : backend_torch.py:92-93 uniquement.
- **Classe** : E1
- **Verdict** : **confirmé**

### P10.c — référent de la bande publiée [7,0 ; 9,5]

- **Sonde** : `python C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/p10_sondes.py ; sed -n 53,66p tools/evo_runs/e34_identity_cell.py`
- **Constat** : La cellule témoin est l'un des douze tirages de la bande. Le seed 2026 est la même cellule au bit dans b_full de P4.16 et dans b_warm_credit de P4.4, et sa survie de 7,0 est le MINIMUM de l'étendue. Le bras allumé perturbe donc ce point-plancher : il a 0 tick de marge vers le bas contre 2,5 vers le haut, et un recul d'un demi-tick suffit pour MATERIEL_BAISSE. Le taux de fausse alarme de 2/13 suppose que S_on est échangeable avec les 12 seeds. Ce n'est pas le cas : sa trajectoire de référence est l'extrémité basse de l'échantillon. La règle ne dit nulle part que S_off est la borne inférieure.
- **Preuve** : Sortie : bande 7.0 / 9.5 ; b_full 2026 = 7.0 ; b_warm_credit 2026 = 7.0 ; dW_abs_sum identiques True ; âges identiques True. S_off = 7,0 est égal au minimum, contre un maximum de 9,5.
- **Classe** : aucune
- **Verdict** : **confirmé**

### P10.d — loi B - p du contexte et divergence de H0

- **Sonde** : `python C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/p10_sondes.py` (stub sans monde, vraie recette immortal_refill + slot_identity_violations)
- **Constat** : Quand le mort occupe le dernier rang, il est retiré puis remis en queue et retrouve sa place : 0 tranche désalignée au lieu de B-p = 1. Après une première permutation, une nouvelle mort ne se lit plus en B-p, car les permutations se composent. Pour la même raison, dire que la trajectoire diverge dès la première mort est faux si cette mort est en queue : restore_slot_order ne déplace alors rien, et l'ordre d'itération, donc les tirages, reste inchangé. C'est sans effet sur le verdict, puisque l'audit compte au lieu de calculer, mais le contexte présente cette formule comme une loi.
- **Preuve** : Sortie : p=0 → 12 ; p=5 → 7 ; p=10 → 2 ; p=11 → 0, contre B-p = 1.
- **Classe** : aucune
- **Verdict** : **confirmé**

### P10.e — citations de code du contexte (contrôle)

- **Sonde** : `grep -n "def immortal_refill\|e.agents.append" tools/evo_runs/s2_credit_retention.py ; sed -n 1048,1067p src/worlds/world_1_stoneage.py ; grep -n "np.stack\|def _write_back" src/agents/backend_torch.py` ; lecture des JSON (voir p10_sondes.py)
- **Constat** : Toutes les lignes citées tiennent à la lecture. La remise en queue est bien en s2_credit_retention.py:107-113 (append :111). La reconstruction ne dépend que de la taille (world_1_stoneage.py:1060-1066). Les tranches sont empilées dans l'ordre de construction (backend_torch.py:109) et la réécriture va de la tranche i au modèle i (:512-513). L'audit ne fait que des comparaisons d'identité, sans aucun tirage. Les défauts du crédit et les valeurs du sceau (1999, 12, 18242.03954219818, S_a 31,5) sont retrouvés dans les JSON suivis. La phase 2 reconstruit dans l'ordre : E34 n'y agit pas.
- **Preuve** : Lignes s2_credit_retention.py:111, world_1_stoneage.py:1061-1066, backend_torch.py:109 et 513. JSON P4.4 : td 1999, résurrections 12, dW 18242.03954219818 ; a_frozen 2026 = 31.5.
- **Classe** : aucune
- **Verdict** : non confirmé
