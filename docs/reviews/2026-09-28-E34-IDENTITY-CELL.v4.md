# Revue adversariale — E34-IDENTITY-CELL (v4)

- **Cible** : C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/E34-IDENTITY-CELL.v4.json (pré-inscription)
- **Date** : 2026-09-28
- **SHA** : b27083797bf6ed1e3612dfbe08ce84e6346bbe76 (worktree .worktrees/e34)
- **Résultat des TÉMOINS** (commandes rejouables : `PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier <témoin> <scratchpad>/refutateur_v4/critiques-<témoin>.json --extrait <scratchpad>/temoins_v4/temoin-N.md [--jugement OUI]`) :
  - S2-BLIND-CHAMPION-42e9357 : RETROUVE, code 0, 9 recevables (temoin-1.md, jugement OUI)
  - EDR-GRAB-COST-1828371 : RETROUVE, code 0, 7 recevables (temoin-3.md, jugement OUI)
  - EDR-RETAIN-COMPOSE-4204f8f : RETROUVE, code 0, 8 recevables (temoin-4.md, jugement OUI)
  - LOCK-002-286f244 (cru sain) : MESURE, code 0, 5 recevables (temoin-2.md)
  - PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5
  - plancher mesure sur LOCK-002-286f244 : 5 critiques recevables (seuil historique 1)

Critiques confirmées : **15** sur 35.

## P1

### P1.a — puissance du contrôle positif non chiffrée
- **Sonde** : `python -c "import json; d=json.load(open('results/s2_credit_ablation_2.json'))['arms']; a=d['a_frozen']['2026']; print(a['learning'], a['elapsed_s'], d['b_full']['2026']['elapsed_s']); [print(k, d[k]['2026']['learning']['dW_abs_sum'], d[k]['2026']['survival']['survival_median']) for k in ('b_const','b_eplr')]" ; git grep -l first_order_change_tick -- 'results/*.json' | wc -l`
- **Constat** : Ce qui départage NON_MATERIEL de NON_TRANCHE, c'est la capacité de pos à passer au-dessus de la bande. Or aucune évidence suivie ne chiffre cette capacité. t1 n'apparaît dans aucun results/ suivi, donc le levier est inconnu au scellement. Le sens invoqué et la marge S_a = 31,5 viennent de a_frozen (P4.16), un bras qui n'a jamais exécuté de phase 1. Et les petites doses publiées érodent déjà : dW à 5-6 % du plein donne 21,0 et 11,5. Si la coupe tombe tard, le NON_TRANCHE devient quasi certain avant même le run, et le sceau ne l'a pas estimé.
- **Preuve** : a_frozen seed 2026 : learning=None, elapsed_s=0,99 contre 815 s pour b_full ; b_const dW=941,5 (ratio 0,054) S=21,0 ; b_eplr dW=1168,2 (ratio 0,064) S=11,5 ; git grep de first_order_change_tick dans results/ suivis : 0 fichier
- **Classe** : E8
- **Verdict** : confirmé — prémisse porteuse du côté nul HÉRITÉE d'un autre dispositif et non mesurée (ne produit pas de faux verdict, grâce au repli NON_TRANCHE, mais laisse le run sans puissance chiffrée : c'est la leçon de P4.18, 838446e6)

### P1.b — « épisodique seul » hors régime
- **Sonde** : `python -c "import json; d=json.load(open('results/s2_credit_ablation_2.json')); print(d['regime']['arms_credit']['b_eplr'], d['regime']['lr_published'], d['arms']['b_eplr']['2026']['survival']['survival_median'])"`
- **Constat** : La valeur 11,5 citée pour « épisodique seul » vient du bras b_eplr de P4.16. Ce bras tournait avec TD coupé et un pas dix fois plus petit (0,004) que le pas publié (0,04), celui que les quinze bras de v4 utiliseront. Le texte range pourtant cette valeur parmi les doses partielles publiées pour prédire que pos restera dans la bande. La prémisse vient donc d'un autre régime, et rien ne mesure l'épisodique seul au pas publié.
- **Preuve** : arms_credit.b_eplr = {td_enabled: False, lr: 0.004, episode_enabled: True} contre lr_published = 0.04 ; S seed 2026 = 11.5
- **Classe** : E6
- **Verdict** : confirmé — valeur mesurée hors du régime où la cellule opère ; elle n'infléchit que l'attente écrite d'avance, pas la table de discrimination

### P1.c — 72 cellules annoncées, 60 distinctes
- **Sonde** : `python -c "import json; r=json.load(open('results/s2_credit_retention.json'))['arms']['b_warm_credit']; d=json.load(open('results/s2_credit_ablation_2.json'))['arms']['b_full']; print(sum(r[s]['survival']['ages']==d[s]['survival']['ages'] for s in r), sum(round(r[s]['elapsed_s'])==round(d[s]['elapsed_s']) for s in r))"`
- **Constat** : Le texte parle de « 72 cellules sous crédit » et attribue à P4.16 la dispersion b_full [7,0 ; 9,5]. Mais le b_full de P4.16 reprend le b_warm_credit de P4.4. Les âges sont identiques sur les 12 seeds et le temps écoulé l'est sur 11 : seul le seed 2026 a été rejoué. Il n'y a donc que 60 cellules distinctes, et cette dispersion est celle de P4.4, citée une seconde fois sous un autre nom. Le minimum à 7,0 ne change pas, mais le compte et l'attribution ne tiennent pas.
- **Preuve** : âges identiques 12/12 seeds ; elapsed_s identiques 11/12 (seul 2026 : 536 contre 815) ; 12+12+48 = 72 annoncées, 60 distinctes
- **Classe** : aucune
- **Verdict** : confirmé — descriptif, ne renverse pas le verdict

### P1.d — témoin du code
- **Sonde** : `python -c "import json; c=json.load(open('results/s2_credit_retention.json'))['arms']['b_warm_credit']['2026']; print(c['learning']['td_updates'], c['learning']['resurrections'], c['learning']['dW_abs_sum'], c['learning']['episode_updates'], c['survival']['survival_median'])"`
- **Constat** : Prémisse qui renverserait tout : le témoin du code. Elle est mesurée dans une évidence suivie et elle concorde : 1999 mises à jour TD, 12 résurrections, somme 18242,03954219818, S = 7,0 et 250 épisodes (d'où 4,8 %). P4.16 l'a déjà rejouée bit pour bit.
- **Preuve** : 1999 12 18242.03954219818 250 7.0 ; replication P4.16 : identical=True, reason=bit-identique
- **Classe** : aucune
- **Verdict** : non confirmé — prémisse mesurée et concordante

## P2 (DÉLÉGUÉ) — régime

- **Sonde** : `python tools/check_regime_claims.py --only C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/E34-IDENTITY-CELL.v4.json ; echo EXIT=$?` (worktree e34, HEAD b2708379) ; puis `ls docs/EDR | grep -ci 'e34|identity'`
- **Constat** : La porte 19 ne juge que des records Markdown sous docs/EDR ; la cible est une pre-inscription JSON du scratchpad, aucun record E34 n'existe encore dans docs/EDR, donc la porte refuse le filtre et ne rend aucun verdict de regime. Rien a recopier : P2 s'arrete ici, sans rouvrir l'enquete. Les parametres cites (reward_scale 1.0, 2000/200 ticks, FLOOR 9,0, k = 8) ne seront juges par la porte qu'une fois le record ecrit.
- **Preuve** : Sortie de la porte : 'REFUS : --only designe 1 chemin(s) INCONNU(S) de cette porte', EXIT=2 ; ls docs/EDR | grep -ci e34|identity -> 0 (seuls docs/reviews/2026-09-26-E34-IDENTITY-CELL.v1.md, .v2.md et 2026-09-28-...v3.md sont suivis). tools/check_regime_claims.py:404-406 : un chemin inconnu rend 2 avant toute analyse.
- **Classe** : aucune
- **Verdict** : hors périmètre

## P3 (DÉLÉGUÉ) — balayage du pas / garde E19 appelée par le runner scellé

- **Sonde** : `cd C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34 && python tools/check_e19_optimizer_sweep.py --only tools/evo_runs/e34_identity_cell.py; echo exit=$? ; grep -n 'verify(' tools/evo_runs/e34_identity_cell.py ; git ls-files | grep -i E34-IDENTITY`
- **Constat** : La porte ne peut pas classer le runner E34 : elle ne trouve pas la preregistration qu'il reference (la v4 relue vit dans le scratchpad, pas encore scellee dans docs/preregistrations/). Verdict de porte recopie : regle_absente, NOUVEAU non bloquant, exit 0 ; ni 'nu' ni 'couvert'. La question E19 reste donc a trancher par la meme porte APRES le sceau ; aucun defaut E19 n'est etabli ici. Arret conforme au role DELEGUE (pas de reouverture de l'enquete).
- **Preuve** : Sortie de la porte a HEAD b2708379 : 'runners scelles : 35 | sous gradient (PLANCHER) : 12 | nus (PLANCHER) : 9 | indetermines : 4 | non resolus : 6 | regle absente : 1 | illisibles : 0 | appelants de la garde : 3 | geles : 19' puis '[regle_absente] tools/evo_runs/e34_identity_cell.py', 'OK : aucun nouveau runner sous gradient sans garde E19', exit=0. tools/evo_runs/e34_identity_cell.py:15 et :41 nomment la regle E34-IDENTITY-CELL (verify(PREREG) aux lignes 352 et 457) ; git ls-files ne rend que 3 fichiers E34-IDENTITY-CELL, tous sous docs/reviews/, aucun sous docs/preregistrations/.
- **Classe** : aucune
- **Verdict** : non confirmé

## P4

### P4.a — famille réelle : deux grandeurs contre une même bande
- **Sonde** : python (script) : 400 000 tirages de 14 valeurs échangeables (12 relabs, off, on), fréquences de S_off hors bande, S_on hors bande, union ; grep -n de fausse_alarme_h0_borne, BANDE_DEPLACEE et declare_design dans tools/evo_runs/e34_identity_cell.py
- **Constat** : La lecture confronte à la bande de douze DEUX grandeurs et non une : S_off (branche 9, qui refuse de lire) puis S_on (10a/10b). La règle pose elle-même que les shams partagent avec le bras éteint l'ordre de service et la dose ; sous H0, S_off est alors un quatorzième tirage échangeable et tombe hors de [min, max] avec probabilité 2/13 : environ 15 % de BANDE_DEPLACEE sur un instrument parfait, annoncée comme une panne de la bande. La probabilité qu'un H0 produise une issue non nulle (panne annoncée ou faux MATERIEL) vaut 25/91 = 0,275 et n'est publiée nulle part ; seule la marginale de S_on (0,154) l'est, et le design déclare une famille vide (n_independent = 1, control_family absent).
- **Preuve** : sortie : P(S_off hors bande) = 0,1537 (exact 2/13 = 0,1538) ; P(MATERIEL et lecture) = 0,1199 (11/91) ; P(union) = 0,2736 (25/91 = 0,2747) ; P(MATERIEL | lecture) = 0,1417 (1/7). e34_identity_cell.py:190 (borne sur S_on seule), :282-286 (BANDE_DEPLACEE), :459-467 (declare_design sans control_family)
- **Classe** : E23
- **Verdict** : confirmé

### P4.b — taille réelle de la bande au premier événement
- **Sonde** : python : np.random.RandomState(k).permutation(m) pour k = 1..12 et m = 2..12, comparée à l'identité (traitement de off) et à la rotation (traitement de on) ; lecture de tools/evo_runs/s2_credit_retention.py:204-214
- **Constat** : Le sham tire parmi TOUTES les permutations des positions déplacées, identité et rotation comprises. Si la première mort frappe la position 10, 9 ou 8 (m = 2, 3 ou 4 lignes déplacées à t1), les douze graines ne donnent que 2, 4 ou 10 traitements distincts. À m = 2, cinq shams appliquent exactement la réindexation de on et sept laissent les lignes comme off ; ils restent bit-identiques à l'un ou l'autre jusqu'au changement d'ordre suivant. La bande n'a alors pas douze membres distincts, et un sham qui répare l'identité reçoit la dose de on, pas celle de off. Ni m à t1 ni le nombre de permutations distinctes ne sont publiés ou gardés : seule la dégénérescence totale (douze Σ|ΔW| égaux) est refusée.
- **Preuve** : sortie : m=2 distincts=2 (=off 7, =on 5 : k 2,3,4,6,9) ; m=3 distincts=4 (=off 3 : k 5,6,12) ; m=4 distincts=10 (=off 2) ; m>=5 distincts=12. s2_credit_retention.py:208 (permutation(len(moved)) sans exclusion) ; e34_identity_cell.py:276-281 (seule garde : dw_distincts < 2)
- **Classe** : E2
- **Verdict** : confirmé (propriété du runner ; son incidence sur le seed 2026 dépend de m à t1, non mesurable sans monde)

### P4.c — compte des cellules et des vagues
- **Sonde** : python -c important tools.evo_runs.e34_identity_cell (len(ARMS), K_RELABS, N_GRILLE, 2/(K+1)) ; grep -n def project_cost -A12 tools/cost_guard.py ; python tools/check_control_family.py --only tools/evo_runs/e34_identity_cell.py
- **Constat** : Quinze bras codés pour quinze annoncés, douze dans la bande, grille 2, borne 0,1538. 14 cellules sur 6 ouvriers font 3 vagues, avec la marge par défaut de 3,0 dans project_cost : le compte déclaré concorde avec le runner. La porte 11 passe, car le runner déclare un design.
- **Preuve** : ARMS 15, K 12, N_GRILLE 2, borne 0.1538 ; cost_guard.py:75 safety=3.0 ; porte : 33 runners scellés, 0 sans design, exit 0
- **Classe** : aucune
- **Verdict** : non confirmé

### P4.d — seuil hérité d'un autre dispositif
- **Sonde** : grep -n floor, FLOOR, band_publiee, s_frozen dans tools/evo_runs/e34_identity_cell.py
- **Constat** : FLOOR = 9,0 (P4.4), la dispersion de P4.16 et S_a n'entrent dans aucune branche : ils alimentent seulement sous_plancher_off, band_publiee et part_erosion_levee, qui sont descriptifs. Les seuils de décision sont internes à la cellule (bande, S_off, S_pos).
- **Preuve** : e34_identity_cell.py:189-190, :239-243, :360 ; aucune occurrence de floor entre :255 et :304
- **Classe** : aucune
- **Verdict** : non confirmé

## P5

### P5.a — gardes de pré-vol
- **Sonde** : `grep -n "assert_positive_control\|assert_not_degenerate\|assert_ablation_changes_something" tools/evo_runs/e34_identity_cell.py tools/evo_runs/s2_credit_retention.py tools/slot_identity.py`
- **Constat** : Aucune des trois gardes du pré-vol n'est invoquée ; leurs équivalents sont codés dans la lecture (zéro commutation → SANS_OBJET, coupe exigée à t1 avec TD en baisse, sommes |ΔW| toutes égales → bande inerte). État inchangé depuis v3.
- **Preuve** : 0 ligne ; e34_identity_cell.py:255-257, :272-274, :279-281
- **Classe** : aucune
- **Verdict** : hors périmètre

### P5.b — dose de la bande contre bras éteint
- **Sonde** : python scratchpad/p5_v4_dose.py (VRAI immortal_after_step sur monde et population FACTICES, mêmes morts scriptées pour tous les bras, aucune simulation) puis python scratchpad/p5_v4_h1.py (modèle jouet déclaré)
- **Constat** : La parité de dosage entre off et réétiquetages est raisonnée, pas mesurée, et elle est fausse : un mélange uniforme des lignes déplacées retombe en moyenne sur une ligne juste par événement, donc chaque réétiquetage commute environ une fois de moins par changement d'ordre, et off est TOUJOURS l'extrême du dosage. Sous un H1 à dose-réponse, S_off glisse vers le bord « défaut » de la bande : le témoin de la branche 9 n'est pas neutre, et sa justification (cible ligne 8, le mot « donc ») repose sur la prémisse fausse. Conséquence chiffrée modeste dans le jouet ; phrase à corriger, dose de la bande à publier contre celle d'off.
- **Preuve** : 20 scripts × 12 morts : commutations off 78,0 en moyenne contre 68,0 pour les douze réétiquetages (ratio 0,872), réindexé 0 ; off au-dessus du MAX des douze dans 20/20 scripts, sous le min 0/20 ; s2_credit_retention.py:207-210 ; jouet : BANDE_DEPLACEE 0,099 (effet 0) → 0,148 (effet 5 ticks)
- **Classe** : E8
- **Verdict** : confirmé

### P5.c — le témoin S_off dans la bande échoue par hasard
- **Sonde** : python scratchpad/p5_v4_hasard.py (200 000 tirages échangeables, continus puis à ex-aequo tirés dans les 12 médianes b_full de P4.16 ; aucun monde)
- **Constat** : Sous l'échangeabilité que la règle invoque elle-même pour S_on, S_off est seul extrême parmi 13 valeurs avec probabilité 2/13 : la branche 9 attribue alors à la bande un défaut de représentativité que le hasard seul fabrique, et le run est perdu. Seule la borne sur S_on est publiée ; la probabilité qu'une exécution PARFAITE sous H0 finisse illisible ou en fausse alarme n'est écrite nulle part, et elle vaut presque le double.
- **Preuve** : continu : P(BANDE_DEPLACEE) 0,1536 (exact 2/13 = 0,1538), P(illisible ou fausse alarme) 0,2736 (exact 4/14 − 1/91 = 0,2747) contre 0,15 publié ; ex-aequo P4.16 : 0,0431 et 0,0759 ; cible ligne 13 ; e34_identity_cell.py:282-286
- **Classe** : aucune (bruit converti en diagnostic de fond)
- **Verdict** : confirmé

### P5.d — contrôle positif : même dispositif, peut-il échouer ?
- **Sonde** : `grep -n "\.learn(\|learn_episode(\|torch_throw_gate = " src/worlds/world_1_stoneage.py ; grep -n detach src/agents/backend_torch.py`
- **Constat** : La coupe d'instance neutralise les deux seuls écrivains de W de la phase 1 (TD par tick, épisodique) ; la tête throw à Adam propre est éteinte par défaut ; forward détache H, aucun graphe ne grossit après la coupe. Même seed, t1, lieu, commit ; pos peut rater (NON_TRANCHE). Rien à redire.
- **Preuve** : world_1_stoneage.py:59, :1097, :1765 ; backend_torch.py:220-223 ; s2_credit_retention.py:163-166
- **Classe** : aucune
- **Verdict** : non confirmé

### P5.e — référence à pas nul
- **Sonde** : `grep -n "lr_override\|lr_effective" tools/evo_runs/e34_identity_cell.py`
- **Constat** : Un seul pas pour les quinze bras, aucun bras à pas nul : la question E19 est sans objet.
- **Preuve** : e34_identity_cell.py:336-338 ; cible ligne 31
- **Classe** : aucune
- **Verdict** : hors périmètre

## P6 (JUGE)

### P6.a — plancher de bruit : la bande est-elle le no-op de CE contraste ?
- **Sonde** : python C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/p6_band_dose.py (rejoue tools/evo_runs/s2_credit_retention.py:198-214 sans monde : RandomState(k).permutation(len(moved)), k=1..12, B=12, mort en p à t1 depuis l'ordre aligné, commutations comptées par bras) ; `grep -nE 'slot_switches|switches_off' tools/evo_runs/e34_identity_cell.py`
- **Constat** : Le plancher de bruit du contraste, la bande des douze shams, n'est pas un no-op de CE contraste : chaque sham tire une permutation uniforme des lignes déplacées, qui coïncide avec celle du correctif sur une position par événement en espérance, et en ENTIER quand la mort frappe l'avant-dernière position. La bande porte donc une fraction du traitement ; sa dose de commutations est inférieure à celle du bras éteint, contrairement à l'égalité revendiquée, et aucune branche du verdict ne confronte ces doses. Effet : bande tirée vers S_on, biais vers NON_MATERIEL / NON_TRANCHE ; S_off dans la bande ne le détecte pas.
- **Preuve** : Sortie de la sonde : p=10 -> 5/12 shams IDENTIQUES au correctif à t1 (0 commutation) et 7/12 identiques au bras éteint (2 commutations) ; p=2 -> 8 à 10 commutations contre 10 pour off ; p=6 -> moyenne 5,33 contre 6. Le verdict ne lit la dose que via switches_off == 0 (tools/evo_runs/e34_identity_cell.py:255) ; la dose des shams est publiée (:230) sans jamais être comparée à celle de off. Cible, clé bande (ligne 8) et question (ligne 2) : égalité de dose affirmée ; le code dit seulement « ≈ » (tools/evo_runs/s2_credit_retention.py:135-136).
- **Classe** : aucune (voisine E1 : le témoin de bruit absorbe une part de l'effet testé)
- **Verdict** : confirmé

### P6.b — tout ratio a-t-il son no-op publié à côté ?
- **Sonde** : `grep -nE 'part_erosion|relabs_dS|P416_RESULTS' tools/evo_runs/e34_identity_cell.py`
- **Constat** : L'unique ratio du dispositif, la part d'érosion levée dS/(S_a - S_off), sort sans sa propre bande : ses douze homologues sous les shams (dS_k sur le même dénominateur) ne sont pas calculés, alors que dS_k l'est en ticks. Son dénominateur S_a provient en outre d'une autre exécution (P4.16), dont le bruit n'est pas mesuré ici. Un pourcentage publié sans le plancher du même pourcentage. Mineur : descriptif, ne décide rien.
- **Preuve** : tools/evo_runs/e34_identity_cell.py:252 (part_erosion_levee = dS / erosion, seul) contre :253 (relabs_dS en ticks, jamais divisé) ; S_a lu dans s2_credit_ablation_2.json (:48, :92-95) ; 1 seule occurrence de part_erosion dans le runner.
- **Classe** : aucune
- **Verdict** : confirmé

### P6.c — sonde imposée : grep no-op, comparaison du ratio publié à la bande
- **Sonde** : `grep -ciE 'no.?op' E34-IDENTITY-CELL.v4.json ; grep -ciE 'no.?op' CLAUDE.md` (témoin positif du motif) ; `ls results/e34_identity_cell.json`
- **Constat** : Rien à comparer encore : le JSON de résultats cité n'existe pas (pré-inscription avant run), et le motif no-op est absent de la cible ; la question « le contraste sort-il de la bande » est à rejouer à la lecture.
- **Preuve** : cible = 0 occurrence, CLAUDE.md = 5 (motif validé) ; ls : No such file or directory
- **Classe** : aucune
- **Verdict** : hors périmètre

### P6.d — no-op EXACT de l'instrument lui-même (machinerie de permutation)
- **Sonde** : `grep -rcE 'permute_population_rows\([^)]*list\(range' tests/sandbox/test_e34_slot_identity.py ; grep -nE '\.H = ' src/agents/backend_torch.py`
- **Constat** : Le no-op de la machinerie de permutation (permutation identité à un événement, que 7/12 shams exécutent à t1 si p=10) n'a pas de test au bit ; mais le test de valeurs déplace chaque ligne exactement et H est remplacé à chaque forward : pas de dérive attendue.
- **Preuve** : 0 appel avec la permutation identité ; tests/sandbox/test_e34_slot_identity.py:229-241 (valeurs ligne par ligne, paramètre conservé) ; src/agents/backend_torch.py:223 (self.H = H_new.detach() à chaque forward)
- **Classe** : aucune
- **Verdict** : non confirmé

## P7 (JUGE)

### P7.a — dose du défaut portée par la bande
- **Sonde** : python scratchpad/p7_v4_dose_relab.py (combinatoire pure de la logique de s2_credit_retention.py:197-214 et :253-264 ; RandomState(k) réels, k = 1..12 ; 200 séquences de 12 morts uniques ; aucun monde)
- **Constat** : L'égalité de dose annoncée entre les douze réétiquetages et le bras éteint est fausse en espérance. À chaque changement d'ordre, la permutation privée des positions déplacées recolle par hasard environ un cerveau au corps qu'il pilotait au tick précédent (point fixe attendu d'une permutation aléatoire rapporté à la permutation de réindexation). Chaque réétiquetage commute donc environ 0,9 fois de moins par événement que le bras éteint : sur une séquence, cela fait 13 % de défaut en moins. Pour une mort en avant-dernière position, 5 réétiquetages sur 12 appliquent exactement la réindexation. Sous H1, la bande est un défaut partiellement réparé : elle se rapproche du bras réindexé, et un NON_MATERIEL devient plus facile à obtenir. De plus, la phrase du verdict NON_MATERIEL cite la dose du bras éteint et celle du correctif, jamais celle de la bande. Les slot_switches sont publiés par bras, mais aucune branche ne les confronte à ceux du bras éteint.
- **Preuve** : Commutations par séquence : bras éteint 74,19, réétiquetages 64,44, soit un ratio de 0,869 et un déficit de 0,904 par événement. Événements où un réétiquetage égale la réindexation : 1528 sur 25872. Mort en position 10 : k = 2, 3, 4, 6, 9 donnent 0 commutation. Code : s2_credit_retention.py:207-210 ; e34_identity_cell.py:299-300 ; affirmation contraire dans E34-IDENTITY-CELL.v4.json:8 et :2.
- **Classe** : E6
- **Verdict** : confirmé

### P7.b — dose reçue par le contrôle positif
- **Sonde** : `grep -nE 'W\.data|with torch.no_grad' src/agents/backend_torch.py ; grep -rn 'learn_episode_bptt|_torch_pop\.\w*learn' src/worlds/` ; python -c affichant le bloc learning de results/s2_credit_retention.json b_warm_credit 2026
- **Constat** : La garde exige seulement que td_updates de pos soit strictement inférieur à celui du bras éteint. La valeur attendue est pourtant exactement t1 : le premier appel ne met rien à jour (td_calls 2000 pour td_updates 1999), et la coupe survient après le pas du tick t1. Rien ne vérifie episode_updates pour pos. Le levier est déduit de t1 au lieu d'être lu sur td_updates. Autre point : la lambda posée sur l'instance masque le patch de classe du compteur, donc td_calls cesse lui aussi de compter après la coupe. La dose nulle après t1 vient de la construction, pas d'une observation. Cette faiblesse reste sans conséquence : W n'a pas d'autre écrivain que learn et learn_episode, le monde n'appelle que ces deux voies, et la population ne se reconstruit pas quand B reste constant. La coupe tient.
- **Preuve** : Garde lâche : e34_identity_cell.py:272. Levier déduit : e34_identity_cell.py:242. Instance contre classe : s2_credit_retention.py:165-166 contre learning_events.py:234-235. Écritures de W seulement dans les chemins learn (backend_torch.py:351, :397). Monde : world_1_stoneage.py:1097 et :1765 seulement. Cellule publiée : td_calls 2000, td_updates 1999, episode_updates 250, skips {}.
- **Classe** : aucune
- **Verdict** : non confirmé

### P7.c — cohorte constante
- **Sonde** : `grep -n 'def slot_identity_violations' -A 22 tools/slot_identity.py` ; python -c comptant len(ages) dans results/s2_credit_retention.json et results/s2_credit_ablation_2.json
- **Constat** : En phase 1, exiger ticks_known = 2000 et ticks_unknown = 0 revient à imposer, à chaque tick, que la population ait autant de lignes qu'il y a de corps. L'audit rend None dès que ces deux tailles divergent. Les résurrections sont publiées par bras. En phase 2, le verdict ne contrôle pas la longueur de la liste des âges pour les 14 bras hors témoin. Aucun chemin ne peut pourtant la changer : benchmark_mode coupe la reproduction, et un agent ne quitte la cohorte qu'en mourant.
- **Preuve** : slot_identity.py:39-40 ; e34_identity_cell.py:208-213 ; world_1_stoneage.py:78-80. Longueur des âges égale à 12 dans 36 cellules sur 36 et dans 60 sur 60.
- **Classe** : aucune
- **Verdict** : non confirmé

### P7.d — nul d'apprentissage ou nul de létalité
- **Sonde** : python -c affichant survival de results/s2_credit_retention.json b_warm_credit 2026 ; `grep -n 'NON_MATERIEL' tools/evo_runs/e34_identity_cell.py`
- **Constat** : En phase 2, la variable dépendante de la cellule publiée est collée à la mort par la faim. Tout résultat dans la bande serait donc un nul de létalité : il ne dirait rien de l'apprentissage. La règle en tient compte. Elle n'autorise NON_MATERIEL que vers le haut. Elle l'assortit en plus de deux conditions : S_pos doit sortir au-dessus de la bande et dépasser S_off. Sinon le verdict est NON_TRANCHE. La distinction est donc bien tracée.
- **Preuve** : Âges [5, 6, 6, 7, 7, 7, 7, 8, 8, 9, 9, 11], 0 censuré, dernier décès au tick 11, médiane 7,0 contre un plafond de famine d'environ 7,2 ; garde : e34_identity_cell.py:295
- **Classe** : aucune
- **Verdict** : non confirmé

## P8

### P8.a — reconstructions et vote social non comptés en phase 2
- **Sonde** : `grep -c compter_reconstructions tools/evo_runs/e34_identity_cell.py tools/evo_runs/s2_bassin_fragility.py ; grep -c '_assert_body_is_bassin|phenotype_of'` (idem) ; `sed -n 137,140p tools/evo_runs/e34_identity_cell.py ; grep -o reconstru E34-IDENTITY-CELL.v4.json | wc -l` ; python -c sur results/s2_credit_retention.json arms/b_warm_credit/2026/survival
- **Constat** : La DV se mesure en phase 2, et pendant cette phase l'etat recurrent est reecrit par deux mecanismes que le runner E34 ne compte pas. (1) A chaque tick qui tue, B baisse, le monde reconstruit la population torch et le constructeur remet H a zero pour tous les survivants. (2) Le vote social continue d'agir en phase 2, mais le compteur se ferme a la fin de la phase 1. Dans la cellule publiee, six ticks de mort distincts en 11 ticks donnent cinq remises a zero de H chez les survivants. Leur frequence depend des morts, donc du bras. Le runner voisin applique la meme fonction de phase 2 au meme bassin et publie ces deux compteurs, avec une garde du corps avant et apres. Le runner E34 ne fait rien de cela. Le design affirme pourtant que tous ses liens sont mesures. H0 ne s'en trouve pas biaise : les quinze bras passent par cette phase 2, et la bande l'absorbe. Mais la DV n'est pas une survie de douze cerveaux independants, et cela n'est pas publie. Remede : envelopper phase2_survive_mortal dans compter_reconstructions et compter_consensus, publier les comptes par bras, et ajouter _assert_body_is_bassin.
- **Preuve** : e34_identity_cell.py : 0 compter_reconstructions, 0 garde de corps ; s2_bassin_fragility.py : 2 et 8, phase 2 enveloppee a :229-230. e34_identity_cell.py:137-140 : le compteur se ferme avant phase2_survive_mortal. backend_torch.py:129 (H = zeros a la construction) ; world_1_stoneage.py:1060-1066 (reconstruction si B change). Ages publies [5,6,6,7,7,7,7,8,8,9,9,11] : ticks de mort {5,6,7,8,9,11}, soit 5 reconstructions avec survivants. Regle v4 : 1 seule occurrence de 'reconstru', dans le contexte de la phase 1 (temoin positif du grep : 'vote social' = 6). Recevabilite verifiee par tools/refutateur_temoins.recevabilite (mots_recopie = 8) : recevable.
- **Classe** : E5
- **Verdict** : confirmé : incompletude de publication sur la phase de la DV ; ne biaise pas H0

### P8.b — E26 : le corps suit-il la permutation de W ?
- **Sonde** : python scratchpad/p8_v4_sonde.py (TorchPopulationModel sur 12 clones, sans monde) ; `grep -n 'def update_phenotype|phenotype_' src/agents/mamba_agent.py`
- **Constat** : E26 : l'intervention permute tout W sur l'axe des agents, lignes 0-9 comprises (celles d'ou le monde tire le corps). Le corps n'en depend pourtant pas. Le phenotype est fige au clonage et le write-back ne le recalcule jamais ; add_agent le lit tel quel. Les douze clones partagent un seul triplet. L'etiquette de modele voyage avec sa ligne, donc chaque genome recoit la ligne de son propre cerveau. Aucun contraste de corps entre bras.
- **Preuve** : phenotypes {(688.8267, 70, 14.8883)} ; apres W[:,0:5]+1 et write-back, hp_bonus = 688.8267 contre 8613.2849 recalcule ; 'chaque modele recoit SA ligne : True' ; mamba_agent.py:77-80, :82 ; world_1_stoneage.py:375, :388, :702.
- **Classe** : E26
- **Verdict** : non confirmé

### P8.c — aliasing après permutation
- **Sonde** : python scratchpad/p8_v4_sonde.py ; `grep -n 'logits = batch_logits\[|last_action"\]\] -= 0.1|_last_logits' src/worlds/world_1_stoneage.py`
- **Constat** : La permutation ne cree pas de nouvel alias. Elle remplace H par une copie, donc l'ancienne vue n'est plus liee a l'etat, et une ecriture dans cette vue n'atteint plus H. Or le monde ne garde aucune vue d'un tick a l'autre : ses trois acces aux logits se font a l'interieur de step, avant l'appel au traitement. Les quatre cles de la transition TD en attente sont bien permutees, avec W, H et agents.
- **Preuve** : shares_memory avant = True, apres = False ; ecriture dans l'ancienne vue -> H change : False ; cles _prev = [H_in, act, obs, reward] ; W, H, agents suivent perm : True True True ; acces world_1_stoneage.py:962, :1312, :1340 seulement ; slot_identity.py:79-89.
- **Classe** : E5
- **Verdict** : non confirmé

### P8.d — E24 : chevauchement entrées/sorties
- **Sonde** : `python tools/check_io_overlap.py` ; python scratchpad/p8_v4_sonde.py
- **Constat** : E24 : le bassin clone ne presente aucun chevauchement entre entrees et sorties (marge de cinq noeuds). La porte ne signale aucun genome persiste nouveau ou aggrave.
- **Preuve** : 358 genomes, 10 chevauchants connus, 0 nouveau, 0 aggrave, EXIT=0 ; I,O,N = 59,108,172, I+O-N = -5.
- **Classe** : E24
- **Verdict** : non confirmé

## P9 (DÉLÉGUÉ)

### P9.a — provenance des results/ cités : porte 20
- **Sonde** : `python tools/check_evidence_provenance.py --only <scratchpad>/E34-IDENTITY-CELL.v4.json ; python tools/check_evidence_provenance.py --only E34-IDENTITY-CELL ; ls docs/EDR | grep -i -c 'e34\|identity'`
- **Constat** : La porte 20 refuse la cible : elle ne connaît que des records docs/EDR/<nom>.md, et la v4 est un brouillon de pré-inscription posé dans le scratchpad, sans record associé (0 fichier EDR ne porte E34 ou identity). La porte ne rend aucun verdict de provenance ; je le recopie tel quel et je m'arrête. Remarque, qui relève d'une dette et non d'une critique : pour un brouillon de règle, P9 n'a aucune porte vers laquelle déléguer.
- **Preuve** : exit=2 sur les deux appels : « REFUS : --only designe 1 chemin(s) INCONNU(S) de cette porte -- ni record docs/EDR/<nom>.md present » ; ls docs/EDR | grep -c e34|identity = 0
- **Classe** : aucune
- **Verdict** : hors périmètre

### P9.b — intégrité du sceau de la pré-inscription
- **Sonde** : `python -c "from tools.preregister import verify; verify('E34-IDENTITY-CELL')" ; ls docs/preregistrations | wc -l ; ls docs/preregistrations | grep -c -i BASSIN ; git ls-files docs/preregistrations | grep -i -c 'e34\|identity'`
- **Constat** : La règle n'a jamais été scellée : preregister.verify lève FileNotFoundError, et aucun fichier E34 n'existe dans docs/preregistrations, ni sur le disque ni dans l'index. Le contrôle positif du grep tient (BASSIN = 1 sur 72 règles). La revue passe avant le sceau, donc il n'y a aucun sceau à vérifier. Je recopie le verdict de la garde. Cette vérification sera à rejouer quand la règle aura été scellée, avant tout run.
- **Preuve** : exit=1, tools/preregister.py:196 : FileNotFoundError « aucune pré-inscription « E34-IDENTITY-CELL » — la règle n'a pas été scellée avant le run » ; 72 règles, BASSIN 1, E34 0 (disque) et 0 (index)
- **Classe** : aucune
- **Verdict** : hors périmètre

## P10

### P10.a — ticks_reordered nul par construction
- **Sonde** : `grep -n 'ticks_reordered"\] +=' tools/evo_runs/s2_credit_retention.py ; grep -c slot_order_fix tools/evo_runs/e34_identity_cell.py`
- **Constat** : Le compteur ticks_reordered ne s'incrémente que dans la branche slot_order_fix d'immortal_after_step, et aucun des quinze bras ne l'active : arm_config ne pose jamais ce drapeau. Il vaut donc zéro PAR CONSTRUCTION. La garde de la branche 7 censée attraper un harnais qui réordonne les corps ne peut pas se déclencher, et aucune grandeur du run ne détecterait un réordonnancement venu d'ailleurs que la recharge. La propriété tient à la LECTURE de permute_population_rows (qui ne touche pas e.agents) et aux tests jouets, pas à ce compteur présenté comme une mesure.
- **Preuve** : tools/evo_runs/s2_credit_retention.py:224 (seul incrément, sous 'if slot_order_fix:' ligne 221) ; grep -c slot_order_fix dans le runner = 0 ; garde morte tools/evo_runs/e34_identity_cell.py:258-261
- **Classe** : E1
- **Verdict** : confirmé

### P10.b — 11,5 « épisodique seul » : deux variables bougent
- **Sonde** : `grep -n b_eplr tools/evo_runs/s2_credit_ablation_2.py` ; python -c qui charge results/s2_credit_ablation_2.json et imprime lr, td_updates, episode_updates par bras au seed 2026
- **Constat** : Le 11,5 présenté comme dose partielle « épisodique seule » de P4.16 est la cellule du bras b_eplr, qui coupe le TD ET divise le pas par dix (lr 0,004 contre le défaut 0,04 du bras complet, soit 0,00333 par agent publié pour b_full). Deux variables bougent : ce n'est pas une dose partielle du crédit au pas publié, et la prédiction écrite d'avance sur S_pos (érosion installée tôt, NON_TRANCHE attendu) s'appuie sur un chiffre dont le régime diffère de celui qu'on lui prête.
- **Preuve** : tools/evo_runs/s2_credit_ablation_2.py:54 (b_eplr : td_enabled False, lr=LR_LOW) et :8 (épisodique seul à pas 0,004) ; JSON seed 2026 : b_eplr lr 0.004, td_updates 0, episode_updates 250, S 11.5 ; b_full lr None, lr_effective_per_agent 0.00333 (= 0,04 / 12), S 7.0
- **Classe** : E8
- **Verdict** : confirmé

### P10.c — absence de tirage RNG vérifiée sur un traitement sur trois
- **Sonde** : `grep -n 'get_rng_state\|np.random.seed' tests/sandbox/test_e34_slot_identity.py ; grep -c get_rng_state tests/sandbox/test_e34_slot_identity.py`
- **Constat** : L'absence de tirage RNG est dite VÉRIFIÉE par le fichier de tests E34, mais ce fichier ne compare l'état des générateurs (numpy global, torch) que dans le test du réétiquetage. Ni le test de la réindexation, ni celui de la coupe du crédit, ni l'audit seul n'en contrôlent aucun. À la lecture, permute_population_rows et _cut_credit n'appellent aucun générateur : le fond tient, mais la vérification citée couvre un traitement sur trois.
- **Preuve** : tests/sandbox/test_e34_slot_identity.py:287-302 (seul contrôle RNG, sham_relabel=3) ; get_rng_state : 2 occurrences, toutes dans ce test ; réindexation :260-277 et contrôle positif :306-320 sans assertion RNG ; tools/slot_identity.py:78-89 sans appel RNG
- **Classe** : E4
- **Verdict** : confirmé

### P10.d — refus de la garde de coût non persisté
- **Sonde** : `grep -n 'CostTooHighToStart\|except' tools/evo_runs/e34_identity_cell.py ; sed -n 400,427p tools/evo_runs/e34_identity_cell.py`
- **Constat** : Le refus de la garde de coût avant la phase B n'est persisté nulle part : project_cost lève CostTooHighToStart, que ni _tout ni main n'attrapent. Restent une trace d'exception et un off.json déjà écrit ; une lecture ultérieure rendrait INCOMPLET sans nommer le refus comme cause. La coupe PENDANT la phase B, elle, est bien écrite (_coupe.json) : les deux sorties annoncées n'ont pas le même traitement.
- **Preuve** : tools/evo_runs/e34_identity_cell.py:410-411 (project_cost sans try) ; seule clause except du runner à :105 (lieu) ; tools/cost_guard.py:88-92 (lève) ; off.json écrit à :400 avant la garde ; coupe persistée à :425
- **Classe** : E10
- **Verdict** : confirmé

### P10.e — chaîne des canaux
- **Sonde** : `sed -n 216,252p src/agents/backend_torch.py ; sed -n 1069,1098p src/worlds/world_1_stoneage.py ; sed -n 65,89p tools/slot_identity.py`
- **Constat** : Chaîne des canaux vérifiée à la lecture et tenue : sans gate (CONDITION_GATE False), forward rend une vue numpy du bloc de sortie de H ; le vote (:973) et la pénalité (:1340) écrivent donc dans H, et V(s') est relu dans self.H par learn ; la réindexation permute W en place, H, _last, _prev et pop.agents ; la fenêtre épisodique est alignée par id de corps et rejouée depuis H nul ; morts retirées après learn (:1784). Aucune contradiction avec le texte.
- **Preuve** : src/agents/backend_torch.py:48, :223-235, :245 ; src/worlds/world_1_stoneage.py:973, :1312, :1340, :1765, :1784 ; tools/slot_identity.py:79-89
- **Classe** : aucune
- **Verdict** : non confirmé

### P10.f — ancres de lignes et valeurs de code
- **Sonde** : `diff --strip-trailing-cr <(git show f1d6a987:src/worlds/world_1_stoneage.py) src/worlds/world_1_stoneage.py` ; python -c (starvation_ceiling sur _bassin_cohort(2026,1), lecture de results/s2_credit_retention.json et s2_credit_ablation_2.json)
- **Constat** : Ancres de lignes et valeurs de code vérifiées : immortal_refill 107-113, FLOOR 9.0 ligne 45, reconstruction 1060-1066 (fichier monde identique à f1d6a987 hors fins de ligne), backend 109/512 au sha d'ancrage, k=8 ligne 52, marge 3 de project_cost, plafond de famine 7,16 ticks recalculé sur le bassin (drain 14,888), témoin 1999 / 12 / 18242.03954219818 lu dans le JSON suivi, minimum 7,0 atteint par 9 des 72 cellules sous crédit.
- **Preuve** : diff rc=0 ; ceiling 7.164478546849247 ; I,O,N = 59,108,172 ; td 1999, résurrections 12, dW 18242.03954219818 ; n 72, min 7.0, count_min 9
- **Classe** : aucune
- **Verdict** : non confirmé
