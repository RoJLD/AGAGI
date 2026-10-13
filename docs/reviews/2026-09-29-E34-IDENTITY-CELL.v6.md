# Revue adversariale — E34-IDENTITY-CELL v6

- **Cible** : `C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/E34-IDENTITY-CELL.v6.json` (pré-inscription, brouillon non scellé)
- **Date** : 2026-09-29
- **SHA** : `edafbb66ac7ad8296d4ba6a3820c8a1051605df9` (worktree `.worktrees/e34`, branche `tmp/e34`)
- **Critiques** : 34 au total, 13 confirmées.
- **Exécution** (ajouté par la session E34 après le rendu, hors workflow) : run `wf_7dd53fc7-2cb`, lancé le 2026-09-29 à
  00:56, rendu à 09:49 (heure locale ; 31 975 793 ms de mur). **Fenêtre MUETTE de 02:36 à 09:07** : aucun événement dans
  aucun agent — **veille probable, non établie** (aucune requête d'éveil ne couvre un workflow : P2.144, élargie par
  agagi-32). Les premières tentatives de P1, P5 et P6 se sont arrêtées à 02:36, celles de P4 et P10 à 09:07 (P10 porte
  « Request interrupted by user », cause non établie) : les cinq ont été RELANCÉES, et ce sont les relances qui sont
  consolidées ici. Coût : 3 557 865 jetons de sous-agents selon le workflow (19 agents comptés) ; relevé des 24
  fichiers d'agents, relances comprises : entrée + création de cache + sortie = 4 093 875, dont 712 302 pour les cinq
  premières tentatives (lectures de cache en plus : 65,8 M). Les deux compteurs ne mesurent pas exactement la même
  chose.

## Témoins

| témoin | statut | code | critiques recevables | fichier de critiques |
|---|---|---|---|---|
| S2-BLIND-CHAMPION-42e9357 | RETROUVE | 0 | 9 | `scratchpad/refutateur_v6/critiques-S2-BLIND-CHAMPION-42e9357.json` |
| LOCK-002-286f244 (cru sain) | MESURE | 0 | 7 | `scratchpad/refutateur_v6/critiques-LOCK-002-286f244.json` |
| EDR-GRAB-COST-1828371 | RETROUVE | 0 | 7 | `scratchpad/refutateur_v6/critiques-EDR-GRAB-COST-1828371.json` |
| EDR-RETAIN-COMPOSE-4204f8f | RETROUVE | 0 | 9 | `scratchpad/refutateur_v6/critiques-EDR-RETAIN-COMPOSE-4204f8f.json` |

PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5
plancher mesure sur LOCK-002-286f244 : 7 critiques recevables (seuil historique 1)
⚠ INDISCRIMINANT : le record cru sain rend autant de critiques recevables que les defectueux

Commandes (rejouables ; `<S>` = `C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad`, `<W>` = `C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34`) :

    PYTHONIOENCODING=utf-8 python <W>/tools/refutateur_temoins.py --verifier S2-BLIND-CHAMPION-42e9357 <S>/refutateur_v6/critiques-S2-BLIND-CHAMPION-42e9357.json --extrait <S>/temoins_v5/temoin-1.md --jugement OUI
    PYTHONIOENCODING=utf-8 python <W>/tools/refutateur_temoins.py --verifier LOCK-002-286f244 <S>/refutateur_v6/critiques-LOCK-002-286f244.json --extrait <S>/temoins_v5/temoin-2.md
    PYTHONIOENCODING=utf-8 python <W>/tools/refutateur_temoins.py --verifier EDR-GRAB-COST-1828371 <S>/refutateur_v6/critiques-EDR-GRAB-COST-1828371.json --extrait <S>/temoins_v5/temoin-3.md --jugement OUI
    PYTHONIOENCODING=utf-8 python <W>/tools/refutateur_temoins.py --verifier EDR-RETAIN-COMPOSE-4204f8f <S>/refutateur_v6/critiques-EDR-RETAIN-COMPOSE-4204f8f.json --extrait <S>/temoins_v5/temoin-4.md --jugement OUI

---

## P1

### P1.1 — sens du contrôle positif non mesuré
- **Sonde** : `python -c "import json;d=json.load(open('results/s2_credit_ablation_2.json'));c=d['arms']['a_frozen']['2026'];print(c['learning'],c['survival']['survival_median'],c['elapsed_s'])"` ; `python -c "import json;e=json.load(open('results/s2_credit_ablation.json'));c=e['arms']['b_zero']['2026'];print(c['credit'],c['survival']['survival_median'])"` ; `python -c "import json;v=json.load(open('results/s2_bassin_fragility.json'))['verdict'];print(v['verdict'],v['par_bras']['full']['sign']['S_median'])"` ; `grep -n 'sens connu' tools/evo_runs/s2_credit_retention.py` ; comparaison du champ controle_positif v5/v6
- **Constat** : La branche NON_MATERIEL exige que S_pos passe au-dessus de la bande. Aucun results suivi ne mesure la direction attendue d'une coupe du crédit au tick 281. Les seules sources sont des bras où le crédit n'a jamais agi : a_frozen (aucune phase 1, 31,5) et b_zero (reward_scale 0 pendant 2000 ticks, 32,0). La seule étude du même régime sur l'amplitude (P4.18) se termine en INDETERMINE_INSTRUMENT, et son bras sign, à 1x l'amplitude nette du crédit, érode déjà à 10,75 (12/12). Le commentaire du harnais affirme ce sens sans citer de mesure. La justification de la puissance inconnue (t1 absent des résultats) est reprise mot pour mot de la v5, alors que la v6 mesure t1 = 281 : la vraie lacune est qu'aucune survie après 281 ticks de crédit n'a été mesurée. Si ce sens est faux, NON_MATERIEL devient inatteignable et il ne reste que MATERIEL ou NON_TRANCHE. C'est une prémisse héritée d'un autre dispositif, non mesurée.
- **Preuve** : results/s2_credit_ablation_2.json a_frozen/2026 : learning=None, S=31.5, elapsed_s=0.99 ; results/s2_credit_ablation.json b_zero/2026 : reward_scale=0.0, S=32.0 ; results/s2_bassin_fragility.json : verdict=INDETERMINE_INSTRUMENT, full.sign.S_median=10.75, négatifs 12/12 ; tools/evo_runs/s2_credit_retention.py:152 ; extrait de controle_positif identique en v5 et v6 ; mesure_pre_sceau v6 : t1 = 281
- **Classe** : E8
- **Verdict** : confirmé

### P1.2 — la bande exclut le bruit du monde de phase 2
- **Sonde** : `sed -n '65,72p;370,380p' tools/evo_runs/s2_credit_retention.py` ; `sed -n '17,22p' src/seed_ai/harness.py` ; lecture de tools/evo_runs/e34_identity_cell.py:150-157 et :328-337
- **Constat** : La décorrélation des treize membres est vérifiée en phase 1, mais la grandeur lue est la survie de phase 2. Or la phase 2 reconstruit le monde par _world(seed, 1), soit seed_at(2026, 1) = np.random.seed(2027), dans les quinze bras : tous entrent dans la phase mortelle avec le même état du RNG global. En phase 2, la dispersion de la bande ne vient donc plus que des W appris après t1. Le recensement ne tourne qu'en phase 1, et BANDE_DEGENEREE juge la somme |dW| de phase 1, jamais la phase lue. La borne 2/14 tient (traitement commun aux quinze bras, nombres aléatoires communs). En revanche, la bande exclut le bruit du monde de phase 2, alors que la dispersion entre seeds [7,0 ; 9,5] publiée à côté l'inclut : les deux ne sont pas comparables, et la règle ne mentionne pas ce réensemencement.
- **Preuve** : tools/evo_runs/s2_credit_retention.py:377 (e = _world(seed, 1)) -> :71 (seed_at(seed, era)) -> src/seed_ai/harness.py:21 (np.random.seed) ; tools/evo_runs/e34_identity_cell.py:153 (rng_census=True, phase 1 seule) contre :156 (phase 2 sans recensement) ; e34_identity_cell.py:330 (trajectoires distinctes comptées sur dW_abs_sum de phase 1)
- **Classe** : E35
- **Verdict** : confirmé (ne renverse pas la borne 2/14 ; restreint ce que la bande mesure)

### P1.3 — plafond de famine lu comme cause de mort
- **Sonde** : `sed -n '125,133p' tools/evo_runs/e34_identity_cell.py` ; `python -c "import json;r=json.load(open('e34_v6_temoin_off.json'))['row'];print(r['plafond_famine_ticks'],r['survival']['ages'])"` ; `python -c "import json;print(json.load(open('results/s2_credit_retention.json'))['arms']['b_warm_credit']['2026']['survival'].keys())"`
- **Constat** : Le plafond de famine sert à conclure une cause de mort. Or la docstring de starvation_ceiling le déclare lui-même MAJORANT (le coût cérébral s'y ajoute), aucun results ne publie de cause de mort, et 5 des 12 âges de la cellule éteinte (8, 8, 9, 9, 11) dépassent ce majorant de 7,16 : ces agents-là ont mangé. Une médiane de 7,0 sous un majorant est compatible avec n'importe quelle cause de mort. C'est un raisonnement, pas une mesure. Il ne décide aucune branche : le sens unique du verdict vient de l'absence de contrôle vers le bas.
- **Preuve** : tools/evo_runs/e34_identity_cell.py:126-128 ; plafond_famine_ticks = 7.164478546849247 contre âges [5,6,6,7,7,7,7,8,8,9,9,11] ; clés de survie : survival_median, ages, censored, ticks (aucune cause de mort)
- **Classe** : E8
- **Verdict** : confirmé (non porteur du verdict)

### P1.4 — valeurs héritées
- **Sonde** : python -c sur results/s2_credit_retention.json (arms.b_warm_credit.2026), results/s2_credit_ablation_2.json (min/max par bras, bloc replication), results/s2_credit_ablation.json (trois minima par bras)
- **Constat** : Valeurs héritées vérifiées une à une dans les JSON suivis : témoin (âges, 1999 TD, 12 résurrections, somme |dW| 18242.03954219818, 250 épisodes, d'où 144/(12x250) = 4,8 %), S_a 31,5, b_full [7,0 ; 9,5], b_tdonly 9,0 au seed 2026, 6,0 (b_neg et b_tdoff, seed 2036) et 6,5 (seed 2031), FLOOR 9,0. La cellule b_full 2026 de P4.16 est bit-identique à b_warm_credit. Aucune de ces valeurs n'est recopiée de mémoire.
- **Preuve** : tools/evo_runs/s2_credit_retention.py:45 ; replication.identical=True ; p44_dW_abs_sum = measured_dW_abs_sum = 18242.03954219818
- **Classe** : aucune
- **Verdict** : non confirmé

### P1.5 — dose publiée = commutation
- **Sonde** : `grep -nE 'surprise|phenotype_energy_drain' src/worlds/world_1_stoneage.py src/agents/backend_torch.py src/agents/mamba_agent.py`
- **Constat** : La dose publiée est la commutation (16), alors que la mesure pré-sceau compte 11 733 slot-ticks désalignés sur 24 000 (48,9 %). La prémisse tient si aucun canal ne lit, à chaque tick, le modèle du corps plutôt que la ligne qui le pilote. Les deux lectures trouvées (entrée surprise, drain) portent sur des attributs figés : le backend torch ne les écrit jamais, et ils sont posés à la construction sur douze clones identiques.
- **Preuve** : src/worlds/world_1_stoneage.py:537 et :702 ; src/agents/mamba_agent.py:80 ; backend_torch.py : 0 affectation de surprise ; slot_ticks_misaligned 11733 contre slot_switches 16
- **Classe** : aucune
- **Verdict** : non confirmé

## P2 (DÉLÉGUÉ) — Régime : chaque paramètre cité est-il publié par l'évidence ?

- **Sonde** : `cd C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34 && python tools/check_regime_claims.py --only <S>/E34-IDENTITY-CELL.v6.json ; echo exit=$? ; ls docs/EDR | grep -i -E 'e34|identity' ; git ls-files | grep -i E34-IDENTITY`
- **Constat** : La porte 19 ne sait pas juger cette cible : c'est une pre-inscription JSON du scratchpad, pas un record docs/EDR/<nom>.md, et aucun record EDR ni regle suivie E34-IDENTITY-CELL n'existe au sha edafbb66. La porte refuse avant toute analyse (sortie 2). Aucun verdict de regime n'est rendu pour cette cible, ni OK ni DISCORDE. Conformement au prompt, l'enquete n'est pas rouverte a la main : la verification cite -> publie se fera quand le record qui citera results/e34_identity_cell.json existera.
- **Preuve** : Sortie de la porte : 'REFUS : --only designe 1 chemin(s) INCONNU(S) de cette porte -- ni record docs/EDR/<nom>.md present [...]', exit=2. Le perimetre de la porte est docs/EDR/*.md seul (tools/check_regime_claims.py:70 et :361-363, _est_record). 0 fichier docs/EDR correspondant a e34/identity et 0 fichier suivi nomme E34-IDENTITY (seules les revues docs/reviews/*E34-IDENTITY-CELL.v1..v5.md sortent du grep, hors perimetre de la porte).
- **Classe** : aucune
- **Verdict** : hors périmètre

## P3 (DÉLÉGUÉ) — balayage du pas, porte 23

- **Sonde** : `cd .worktrees/e34 (HEAD edafbb66) && python tools/check_e19_optimizer_sweep.py --only tools/evo_runs/e34_identity_cell.py ; echo EXIT=$?` ; puis `git ls-files docs/preregistrations | grep -c E34` ; `git ls-tree -r --name-only HEAD docs/preregistrations | grep -c E34` ; `python tools/check_e19_optimizer_sweep.py --report | grep e34_identity_cell`
- **Constat** : Verdict recopie de la porte 23 : OK, code de sortie 0, rien de bloquant. Le runner y est classe regle_absente, parce que la pre-inscription v6 n'est pas encore scellee sur disque au sha edafbb66 : la porte n'a donc lu aucun contenu de regle et ne tranche pas si ce dispositif est sous gradient. Ce OK ne vaut pas couverture E19 ; il faudra relancer la meme commande une fois la regle scellee. Rien d'autre n'est rouvert ici : la question de la reference a pas nul du meme dispositif releve de P5.
- **Preuve** : Sortie de la porte : 'runners scelles : 35 | sous gradient (PLANCHER) : 12 | nus (PLANCHER) : 9 | indetermines : 4 | non resolus : 6 | regle absente : 1 | illisibles : 0 | appelants de la garde : 3 | geles : 19' ; 'NOUVEAU (non bloquant) : [regle_absente] tools/evo_runs/e34_identity_cell.py' ; 'OK : aucun nouveau runner sous gradient sans garde E19' ; EXIT=0. Le runner cherche PREREG = 'E34-IDENTITY-CELL' (tools/evo_runs/e34_identity_cell.py:48, verify aux lignes 405 et 519) ; fichiers E34 dans docs/preregistrations : 0 dans l'index, 0 dans HEAD. La porte indexe les regles par docs/preregistrations/*.json (tools/check_e19_optimizer_sweep.py:246).
- **Classe** : aucune
- **Verdict** : hors périmètre

## P4

### P4.1 — famille de deux tests, un seul taux déclaré
- **Sonde** : `python scratchpad/p4_v6_refut_sonde.py` (AST de identity_cell_verdict ; Monte Carlo de 400 000 tirages de 15 valeurs échangeables, continues puis tirées dans les 12 médianes b_full de results/s2_credit_ablation_2.json ; injection de lignes synthétiques du test dans le verdict ; aucun monde)
- **Constat** : Le verdict s'appuie sur trois comparaisons aléatoires contre la même bande, et non sur une seule. La troisième, S_pos au-dessus du maximum, réussit par pur hasard environ une fois sur quatorze si couper le crédit à t1 ne change rien. Sous H0 complet, NON_MATERIEL sort alors dans 5,7 % des tirages. La règle ne chiffre que l'erreur portant sur S_on et affirme qu'il n'en existe pas d'autre. Ni elle ni la sortie du verdict ne publient ce taux de réussite fortuite, alors que la règle reconnaît ignorer la puissance de ce contrôle.
- **Preuve** : tools/evo_runs/e34_identity_cell.py:339, :343 et :347, soit 3 appels cmp_grille (s_on > band_max, s_on < band_min, s_pos > band_max) contre 1 décision déclarée. Continu : P(S_pos > max) = 0,0715 contre 1/14 = 0,0714, P(NON_MATERIEL | on et pos nuls) = 0,0572, P(MATERIEL) = 0,1426. Avec ex-aequo : 0,0184, 0,0145 et 0,0343. Injection (bande [6,5 ; 8,5], S_on 7,5, S_pos 9,0) : NON_MATERIEL. Seules les clés fausse_alarme_h0_borne, fausse_alarme_h0_borne_condition et fausse_alarme_h0_ex_aequo sont publiées, toutes sur S_on. Le champ fausse_alarme_h0 de la règle contient 0 occurrence de S_pos.
- **Classe** : E23
- **Verdict** : confirmé : la famille réelle compte deux tests (S_on bilatéral, S_pos unilatéral). Le second qualifie NON_MATERIEL sans que son taux de passage fortuit (≤ 1/14) soit déclaré ou publié.

### P4.2 — compte nominal
- **Sonde** : `python scratchpad/p4_v6_refut_sonde.py` ; `python tools/check_control_family.py --report` ; python -c avec tools.check_control_family.scan_runners()
- **Constat** : Le compte nominal concorde entre la règle, le runner et la borne : 15 bras codés pour 15 annoncés, une bande de 13 membres et 14 graines de réensemencement toutes distinctes. La borne 2/14 est retrouvée par simulation. La porte 11 voit le runner avec un design déclaré.
- **Preuve** : ARMS 15, K_REPS 12, 13 membres, graines 14/14 distinctes de 202601 à 202614. P(MATERIEL | H0) = 0,1426 contre 2/14 = 0,1429. Porte : 33 runners scellés, 0 sans design. scan_runners renvoie tools/evo_runs/e34_identity_cell.py avec {scelle: True, declare: True}.
- **Classe** : aucune
- **Verdict** : non confirmé

### P4.3 — seuils importés
- **Sonde** : grep -n cmp_grille/floor dans tools/evo_runs/e34_identity_cell.py ; Monte Carlo avec ex-aequo de p4_v6_refut_sonde.py
- **Constat** : Aucun seuil de décision ne vient d'un autre dispositif. FLOOR (9,0, pris dans le runner de P4.4) n'entre que dans le dictionnaire des seuils publiés et dans un booléen descriptif. Les trois branches qui tranchent ne lisent que la bande interne de la cellule. Avec les ex-aequo de la grille, la borne est conservatrice : le taux réel de MATERIEL sous H0 est 0,034.
- **Preuve** : floor n'apparaît qu'aux lignes e34_identity_cell.py:212 (th) et :283 (sous_plancher_off). Les lignes :339, :343 et :347 ne comparent qu'à band_max et band_min. P(MATERIEL | H0, ex-aequo) = 0,0343, contre une borne de 0,1429.
- **Classe** : aucune
- **Verdict** : non confirmé

## P5

### P5.1 — contrôle positif réussi par hasard
- **Sonde** : `python <S>/p5_v6_sondes.py` (partie A : 20000 tirages de 15 valeurs échangeables S_on, S_pos et 13 membres ; verdict rejoué dans l'ordre de tools/evo_runs/e34_identity_cell.py:339-354 avec la vraie tools.grid_compare.cmp_grille)
- **Constat** : La note de robustesse repose sur deux comparaisons soumises au hasard, pas sur une seule : S_on doit rester entre les bornes des treize, et S_pos doit dépasser leur maximum, sans marge. Si couper le crédit à t1 ne change plus rien (scénario que la règle tient elle-même pour plausible quand l'érosion est déjà acquise), S_pos n'est qu'un tirage de plus et franchit ce maximum environ une fois sur quatorze. NON_MATERIEL s'écrit alors avec un contrôle positif réussi par pur hasard. Ce second taux d'erreur n'est ni borné ni publié, alors que le texte n'en déclare qu'un et nie toute famille.
- **Preuve** : instrument aveugle -> branche NON_MATERIEL atteinte 0.0398 (loi normale arrondie à la grille 0,5) et 0.0138 (loi empirique b_full P4.16, 12 seeds) ; en face : E34-IDENTITY-CELL.v6.json:14 (une SEULE fausse alarme, 2/14) et :36 (aucune famille de contrôles) ; e34_identity_cell.py:347 compare S_pos au maximum avec une marge 0.0
- **Classe** : E23
- **Verdict** : confirmé

### P5.2 — accessibilité de NON_MATERIEL
- **Sonde** : `python <S>/p5_v6_sondes.py` (partie B : lecture de results/s2_credit_ablation_2.json, seed 2026) ; python -c qui liste les clés de scratchpad/e34_v6_temoin_off.json
- **Constat** : Sur les points publiés du même seed, la survie s'effondre dès les premiers milliers de somme |dW| : l'épisodique seul (1168) laisse déjà 11,5 contre 31,5 pour le bassin gelé. À débit uniforme, le bras coupé aurait reçu environ 2564 à t1 = 281 ; S_pos se situerait plausiblement vers 9 à 11,5, au contact du haut attendu de la bande, donc NON_MATERIEL serait peu accessible. Mais c'est une extrapolation entre mécanismes de crédit différents, sous une hypothèse de débit que rien ne mesure ; la règle prévoit déjà NON_TRANCHE pour ce cas. Le chiffre qui trancherait (somme |dW| cumulée à t1) manque à la mesure pré-sceau, qui l'avait sous la main : dette, pas critique.
- **Preuve** : seed 2026 : a_frozen 31.5 ; b_const dW 941.5 -> 21.0 ; b_eplr dW 1168.2 (td 0) -> 11.5 ; b_tdonly 11742.9 -> 9.0 ; b_full 18242.0 -> 7.0 ; débit moyen 9.13 par tick TD ; b_full entre seeds 7.0-9.5 ; e34_v6_temoin_off.json : seul dW_abs_sum total, aucun cumul à t1
- **Classe** : aucune
- **Verdict** : non confirmé

### P5.3 — gardes de pré-vol
- **Sonde** : `grep -n 'assert_positive_control|assert_not_degenerate|assert_ablation_changes_something' tools/evo_runs/e34_identity_cell.py tools/evo_runs/s2_credit_retention.py` ; `ls results/e34_identity_cell*` ; lecture de s2_credit_retention.py:183-187 et :370-395
- **Constat** : Aucune des trois gardes de pré-vol n'est appelée ; leur rôle est tenu par des branches du verdict : NON_TRANCHE pour le contrôle positif, BANDE_DEGENEREE pour des copies dans la bande, levée si la coupe n'a pas eu lieu à t1 avec exactement t1 mises à jour. Le fichier de résultats n'existe pas encore : aucune valeur de contrôle à confronter. S_pos ne dépend que des poids communs à t1 (plus rien ne les écrit ensuite), ce qui le place bien dans le même dispositif. Pas de défaut propre à la v6 sur ce point.
- **Preuve** : grep : 0 ligne (exit 1) ; results/e34_identity_cell* absent ; contrôle positif tranché à e34_identity_cell.py:347, dose exigée à :325 ; _cut_credit remplace learn et learn_episode (s2_credit_retention.py:183-187) ; mesure pré-sceau : S_off 7.0, témoin bit-identique, t1 281
- **Classe** : aucune
- **Verdict** : non confirmé

### P5.4 — référence à pas nul
- **Sonde** : `grep -n lr_override tools/evo_runs/e34_identity_cell.py`
- **Constat** : La question de la référence à pas nul ne se pose pas : les quinze bras tournent au pas par défaut du learner, sans surcharge, et aucun bras ne compare deux pas. Aucun bras n'est plus dur à optimiser : la réindexation permute des lignes sous SGD sans état, et la phase 2 est à poids gelés partout.
- **Preuve** : e34_identity_cell.py:389 et :424 (lr_override=None) ; pré-sceau lr_effective_per_agent 0.0033333 ; dose_phase2 dW_abs_sum 0.0
- **Classe** : aucune
- **Verdict** : hors périmètre

## P6

### P6.1 — seconde décision aléatoire non comptée
- **Sonde** : `grep -nE "_fausse_alarme_ex_aequo[(]|cmp_grille[(]s_pos" tools/evo_runs/e34_identity_cell.py` ; python -c énumérant les 210 couples ordonnés de rangs (pos, on) parmi 15 valeurs échangeables distinctes (aucun monde)
- **Constat** : Le contrôle positif est jugé contre la même bande par le même test de rang : c'est une seconde décision soumise au hasard, que la règle ne compte pas. Si la coupe du crédit n'a aucun effet, S_pos passe au-dessus des treize membres une fois sur quatorze ; si ni la coupe ni la réindexation n'agissent, la branche NON_MATERIEL est atteinte à peu près une fois sur dix-sept, et ce taux n'est publié nulle part : seul S_on reçoit un calcul de fausse alarme.
- **Preuve** : tools/evo_runs/e34_identity_cell.py:347 (s_pos contre band_max) ; :338 seul appel de _fausse_alarme_ex_aequo, sur s_on ; sortie : P(S_pos > max bande | aucun effet) = 15/210 = 0.0714 ; P(NON_MATERIEL | double nul) = 12/210 = 0.0571 ; contre les champs fausse_alarme_h0 et design de la cible (une seule fausse alarme, aucune famille)
- **Classe** : E23
- **Verdict** : confirmé

### P6.2 — bruit du contraste
- **Sonde** : `grep -nE "e = _world[(]seed|seed_at[(]seed, era[)]" tools/evo_runs/s2_credit_retention.py` ; `grep -niE "no.?op"` sur la cible
- **Constat** : Le bruit mesuré est bien celui de ce contraste : la phase 2 repart de la même graine dans les quinze bras et le préfixe jusqu'à t1 est commun, donc une réplique ne diffère du bras réindexé que par la réindexation ; la permutation a son no-op au bit, identité appliquée à chaque tick avec des morts.
- **Preuve** : tools/evo_runs/s2_credit_retention.py:377 (_world(seed, 1)) -> :71 (seed_at) ; tests/sandbox/test_e34_slot_identity.py:644-649 ; grep no-op sur la cible : 2 lignes (4 et 13)
- **Classe** : aucune
- **Verdict** : non confirmé

### P6.3 — comparaison au plancher
- **Sonde** : `ls results/e34_identity_cell*` ; `git ls-files results | grep -c e34` ; `python -c "from tools.evo_runs.e34_identity_cell import published_band; print(published_band())"`
- **Constat** : Aucune valeur de S_on ni de réplique n'existe encore : la comparaison de dS et de la part d'érosion levée à leur plancher ne peut pas se faire ici. Seul fait déjà acquis : le membre éteint vaut 7,0, déjà au plus bas de la dispersion publiée entre seeds, donc le minimum de la bande ne dépassera pas 7,0.
- **Preuve** : ls : No such file ; git ls-files : 0 ; published_band : min 7.0, max 9.5, la valeur 7.0 deux fois sur 12
- **Classe** : aucune
- **Verdict** : hors périmètre

## P7 (JUGÉ)

### P7.1 — Dose : les treize bras comparés ont-ils reçu la même dose ?
- **Sonde** : `cd .worktrees/e34 && grep -cE "(td_updates|episode_updates|resurrections)[\"'\]]*\)? *(!=|==|<|>)" tools/evo_runs/e34_identity_cell.py` ; `grep -n "compter_reconstructions()" tools/evo_runs/e34_identity_cell.py` ; `grep -n "lr_note=" tools/evo_runs/e34_identity_cell.py` ; `sed -n 241,251p src/agents/backend_torch.py`
- **Constat** : Sur les quinze bras, un seul (pos) voit sa dose d'apprentissage confrontée à une valeur attendue. Les treize autres cellules comparées (on et les douze répliques) publient td, épisodes et résurrections, mais aucune branche ne les exige égaux à ceux du bras éteint ; et nulle part on ne compte les reconstructions de phase 1, alors qu'une reconstruction remet _prev à None et fait disparaître une mise à jour sans bruit. L'égalité de dose sur laquelle repose l'échangeabilité sous H0 est donc posée, pas contrôlée ; la note de pas écrite dans chaque cellule est une chaîne constante, pas une comparaison des valeurs mesurées.
- **Preuve** : Sortie : 1 seule comparaison de dose, tools/evo_runs/e34_identity_cell.py:325 (pos uniquement, == t1) pour 15 bras (ARMS=15, REPS=12) ; compter_reconstructions n'enveloppe que la phase 2 (e34_identity_cell.py:155) ; lr_note constante (e34_identity_cell.py:391) ; src/agents/backend_torch.py:249-251 : après reconstruction _prev vaut None, learn rend None, td_updates n'est pas incrémenté (learning_events.py:171-172). Le bras éteint n'est ancré qu'à 1999 par le témoin, on et les 12 répliques par rien.
- **Classe** : E8
- **Verdict** : confirmé — la dose est publiée mais pas confrontée pour 13 des 14 bras lus par la décision ; il manque une branche INDETERMINE « td/épisodes de on ou d'une réplique différents de ceux du bras éteint » et un compteur de reconstructions en phase 1 dans les quinze bras

### P7.2 — Dose : le compteur de référence compte-t-il des mises à jour REÇUES ?
- **Sonde** : `cd .worktrees/e34 && grep -nE "réellement mis à jour W|ev.episode_updates \+= 1" tools/learning_events.py` ; `sed -n 184,187p tools/learning_events.py` ; `grep -oE "1 appel épisodique compté à pas nul|somme \|dW\| 0,0" <cible v6>`
- **Constat** : Le compteur de référence de P7 appelle mise à jour tout appel dont le retour n'est pas None, sans regarder le delta de W qu'il calcule pourtant à la ligne suivante. En phase 2 cela publie une mise à jour épisodique reçue alors que la somme des deltas vaut exactement zéro : la dose publiée compte des appels, pas des mises à jour reçues, et sa docstring affirme le contraire.
- **Preuve** : tools/learning_events.py:16 annonce « ceux qui ont réellement mis à jour W » ; tools/learning_events.py:185-186 incrémente episode_updates sur `out is not None`, sans condition sur _delta_W. Valeur opposée dans la cible (mesure_pre_sceau (d)) : 1 appel épisodique compté contre Σ|ΔW| = 0,0 en phase 2. Le champ phase2_episode_updates (e34_identity_cell.py:271) publiera donc 1 « mise à jour » là où aucune n'a été reçue. Sans effet sur la décision (la branche lit Σ|ΔW|, :304), mais la dose publiée ment d'une unité.
- **Classe** : E8
- **Verdict** : confirmé — défaut du compteur de référence (sémantique « appel » publiée sous le nom « mise à jour ») ; correctif : incrémenter seulement si ΔW > 0, ou publier episode_calls à la place en phase 2

### P7.3 — Cohorte constante (n_agents par bloc, résurrections)
- **Sonde** : `cd .worktrees/e34 && sed -n 39,40p tools/slot_identity.py` ; `grep -nE "benchmark_mode" src/worlds/world_1_stoneage.py tools/evo_runs/s2_credit_retention.py` ; `sed -n 236,240p tools/evo_runs/e34_identity_cell.py`
- **Constat** : Cohorte constante : en phase 1 l'audit exige 2000 ticks appariés, ce qui impose pop.B égal à la taille de e.agents à chaque tick ; en phase 2 le mode benchmark coupe toute naissance, donc les âges portent toujours douze agents. Rien à signaler.
- **Preuve** : tools/slot_identity.py:39 rend None (tick inconnu) si pop.B != len(e.agents) ; e34_identity_cell.py:236 fait lever INCOMPLET si ticks_known != 2000 ; naissances coupées en benchmark : world_1_stoneage.py:1657 et :1878, benchmark_mode posé par tools/evo_runs/s2_credit_retention.py:73 ; résurrections publiées par bras (e34_identity_cell.py:269).
- **Classe** : aucune
- **Verdict** : non confirmé

### P7.4 — Nul d'apprentissage ou nul de létalité ?
- **Sonde** : `cd .worktrees/e34 && sed -n 125,133p tools/evo_runs/e34_identity_cell.py` ; `sed -n 339,357p tools/evo_runs/e34_identity_cell.py`
- **Constat** : Nul de létalité : la DV touche le majorant de famine (7,0 contre environ 7,2), donc un nul vers le bas serait un nul de létalité ; la règle le sait déjà, elle ne lit NON_MATERIEL que vers le haut et sous contrôle positif sorti. Pas de défaut nouveau.
- **Preuve** : e34_identity_cell.py:125-133 : starvation_ceiling est un MAJORANT (coût cérébral exclu) ; S_off = 7,0 publié (results/s2_credit_retention.json, b_warm_credit/2026, survival_median 7.0) contre ≈ 7,2 ; e34_identity_cell.py:347 n'écrit NON_MATERIEL que si S_pos sort par le haut, sinon NON_TRANCHE (:354).
- **Classe** : E3
- **Verdict** : non confirmé

## P8 (JUGÉ)

### P8.1 — corps E26 : la réindexation touche-t-elle les lignes de W d'où le monde dérive le corps ?
- **Sonde** : `grep -n 'W\[' tools/evo_runs/e34_identity_cell.py tools/evo_runs/s2_credit_retention.py tools/slot_identity.py | wc -l` -> 1 (docstring slot_identity.py:5) ; `grep update_phenotype src tools` ; `python scratchpad/p8_sonde.py` (3 clones, AUCUN monde)
- **Constat** : Non. La permutation agit sur l'axe AGENT (dimension 0) du tenseur W, pas sur les lignes-nœuds 0:10. Le monde lit le corps sur des attributs phenotype_* calculés une seule fois au clonage (from_genome). Ni l'apprentissage, ni la permutation, ni le write-back ne les recalculent. Les 12 clones gardent donc le corps du bassin dans les quinze bras.
- **Preuve** : slot_identity.py:80 (copy_ de W[idx], idx = axe agent) ; mamba_agent.py:77-80 et :82-88 ; update_phenotype n'est appelé qu'en mamba_agent.py:140,152,177,198 et world_1_stoneage.py:990 ; add_agent lit le cache (world:375, :388, drain :702). Sonde : Σ|W[0:5]| passe de 431,43 à 1291,33 selon la ligne perturbée, et le drain reste 14,8883 pour les 3 avant ET après permutation [2,0,1] + write-back
- **Classe** : E26
- **Verdict** : non confirmé

### P8.2 — corps E26 : l'égalité des corps entre bras est-elle MESURÉE ou gardée ?
- **Sonde** : `for f in e34_identity_cell.py s2_credit_retention.py; grep -cE '_assert_body_is_bassin|phenotype_of|assert_phenotype_matched'` -> 0 et 0 ; `grep -n starvation_ceiling e34_identity_cell.py`
- **Constat** : Elle n'est ni gardée ni mesurée après l'apprentissage. Le seul chiffre de corps publié par cellule, le plafond de famine, vient de l'agent 0 et il est calculé juste après le clonage, avant la phase 1. Il ne peut donc pas voir une dérive du corps. Le runner voisin S2-BASSIN-FRAGILITY confronte au contraire le corps au bassin avant et après la phase 2. Aujourd'hui sans effet, puisque la sonde P8.1 montre le cache figé. Mais si un recalcul apparaît sur le chemin, le corps suivra un W appris différent selon le bras : la note gelée donne un écart d'environ 430 sur hp_bonus. Ce recalcul passerait en silence, alors que la pré-inscription affirme que rien d'autre que le traitement ne distingue les bras.
- **Preuve** : e34_identity_cell.py:147 (_bassin_cohort) puis :150 starvation_ceiling(agents[0]), avant la phase 1 (:152) et la phase 2 (:156) ; comparer s2_bassin_fragility.py:228 et :231 (garde appelée avant/après la phase 2), :329-339 (_assert_body_is_bassin), :331 (témoin gelé ~430 sur hp_bonus)
- **Classe** : E26
- **Verdict** : confirmé — garde manquante, sans effet sur le verdict au code actuel (cf. P8.1)

### P8.3 — chevauchement entrée/sortie E24
- **Sonde** : `python tools/check_io_overlap.py` -> 'génomes persistés : 358 | chevauchants : 10 (connus 10, nouveaux 0, aggravés 0)' EXIT=0 ; scratchpad/p8_sonde.py
- **Constat** : Pas de chevauchement. Le bassin garde 5 nœuds libres entre le bloc d'entrée et le bloc de sortie, et son chargeur refuse tout recouvrement avant la construction de la cohorte. La porte ne signale aucun nouveau génome chevauchant.
- **Preuve** : sonde : I=59, O=108, N=172, I+O-N = -5 ; s2_credit_retention.py:61 assert_no_io_overlap dans load_bassin
- **Classe** : E24
- **Verdict** : non confirmé

### P8.4 — vue de l'état récurrent (aliasing) sous la permutation
- **Sonde** : `python scratchpad/p8_sonde.py` ; `python scratchpad/p8_sonde2.py` (forward+learn x3, inventaire de vars(pop))
- **Constat** : Les logits rendus au monde partagent bien la mémoire de pop.H : le vote (:973) et la pénalité (:1340) écrivent donc dans l'état récurrent. Mais la permutation vient après learn et remplace H par une copie, donc aucune vue ne franchit la frontière du tick. Tout état par ligne est permuté, et rien de ce qui a B en première dimension n'est oublié. _prev['H_in'] et _last[1] sont le même objet, mais chacun est cloné depuis la même source non permutée : il n'y a pas de double permutation.
- **Preuve** : np.shares_memory(logits, pop.H) : True avant, False après ; pop.H is not H_old : True ; attributs de dimension B = agents, W, H, tous couverts ; 'non couverts : []' ; clés de _prev = H_in, act, obs, reward, toutes permutées en slot_identity.py:87 ; learn en world:1765, puis survivors en :1784, puis recharge et permutation dans immortal_after_step
- **Classe** : E5
- **Verdict** : non confirmé

## P9 (DÉLÉGUÉ)

### P9.1 — porte 20, provenance de l'évidence
- **Sonde** : `cd C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34 && python tools/check_evidence_provenance.py --only <S>/E34-IDENTITY-CELL.v6.json ; echo EXIT=$?`
- **Constat** : La porte refuse d'examiner la cible : elle ne juge que des records docs/EDR/*.md, et un brouillon de pre-inscription pose dans le scratchpad n'en est pas un. Aucun verdict de provenance n'est donc rendu sur les results/ cites ; selon la regle DELEGUE, je recopie ce refus sans rouvrir l'enquete a la main. Si l'absence de porte pour les brouillons de regle pose probleme, cela releve d'une dette, pas d'une critique.
- **Preuve** : Sortie : REFUS : --only designe 1 chemin(s) INCONNU(S) de cette porte -- ni record docs/EDR/<nom>.md present [...] ; EXIT=2 (sha edafbb66, worktree e34).
- **Classe** : aucune
- **Verdict** : hors périmètre

### P9.2 — sceau de la pré-inscription
- **Sonde** : `cd C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34 && python -c "from tools.preregister import verify; verify('E34-IDENTITY-CELL')" ; echo EXIT=$? ; ls docs/preregistrations | wc -l ; ls docs/preregistrations | grep -ic 'identity\|e34'`
- **Constat** : Aucune regle nommee E34-IDENTITY-CELL n'est scellee dans docs/preregistrations : verify leve FileNotFoundError, et non PreregistrationTampered. Il n'y a donc aucun sceau a comparer. La v6 est un brouillon soumis a revue avant scellement, et son champ mesure renvoie lui-meme a un commit futur qui portera le sceau. La porte ne peut pas encore trancher.
- **Preuve** : tools/preregister.py:196 leve FileNotFoundError (aucune pre-inscription E34-IDENTITY-CELL) ; EXIT=1 ; 72 regles dans docs/preregistrations, 0 correspondance pour identity/e34.
- **Classe** : aucune
- **Verdict** : hors périmètre

## P10

### P10.1 — coupe de la phase B hors de l'évidence suivie
- **Sonde** : `cd C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34 && grep -n '_coupe\|_refus_cout' tools/evo_runs/e34_identity_cell.py ; git check-ignore -v results/e34_identity_cell/off.json ; grep -c coupe tests/sandbox/test_e34_identity_cell.py`
- **Constat** : Le dépassement du plafond pendant la phase B n'atteint jamais l'évidence suivie : _tout écrit _coupe.json dans le répertoire ignoré, et _lire ne relit que _refus_cout.json. Après une coupe, le verdict tombe en INCOMPLET sous la cause générique d'une cellule absente, sans le mur ni la charge au moment de la coupe, donc sans ce qui permettrait de trancher entre contention et structure. Aucun test n'exerce ce chemin.
- **Preuve** : tools/evo_runs/e34_identity_cell.py:487 ecrit _coupe.json ; :413 ne lit que _refus_cout.json ; :231-232 cause 'une cellule manque' quand refus_cout est None ; .gitignore:18 (results/*) ignore le repertoire ; 0 occurrence de 'coupe' dans tests/sandbox/test_e34_identity_cell.py
- **Classe** : E13
- **Verdict** : confirmé

### P10.2 — le recensement compte des appels, pas des tirages
- **Sonde** : `cd C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34 && python -c "import numpy as np; from tools.rng_census import RecensementTirages as T; np.random.seed(0); r=T().__enter__(); r.marquer('t1'); np.random.uniform(0,1,size=4); np.random.randint(0,10,2); r.__exit__(); print(r.resume()['tirages_apres'])"`
- **Constat** : Le recensement ajoute 1 par APPEL de fonction numpy, pas par valeur tirée : les 164 345 unités publiées après t1 sont des appels. Or plusieurs des sites cités tirent plusieurs valeurs par appel (2 aux lignes 335/347/357 hors 3D, 4 à la ligne 1375). Aucun effet sur la décorrélation, qui n'exige qu'un tirage non nul, mais le nombre publié est présenté comme un compte de tirages alors qu'il compte des appels.
- **Preuve** : tools/rng_census.py:94 incremente de 1 par appel ; sonde : 2 comptes pour 6 valeurs tirees (position MT19937 624 -> 10) ; src/worlds/world_1_stoneage.py:1375 tire size=4 par appel, :335/:347/:357 tirent 2 valeurs par appel hors 3D
- **Classe** : aucune
- **Verdict** : confirmé

### P10.3 — empreinte 94e779e8 non rejouable
- **Sonde** : `cd C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34 && git grep -c 94e779e8 HEAD -- tests tools ; git grep -n 94e779e8 HEAD ; git cat-file -t 94e779e8`
- **Constat** : Dire que le chemin par défaut de P4.19 (a) retrouve l'empreinte 94e779e8 ne peut pas se rejouer depuis l'arbre : aucun test ni outil ne contient cette empreinte, qui ne figure que dans une phrase du backlog, et le script de la trace n'est pas versionné. Cela ne change pas le verdict, puisque le témoin de la phase A refait le contrôle au bit et à pleine échelle, mais c'est une affirmation sur le code sans ligne à lire.
- **Preuve** : git grep -c 94e779e8 HEAD -- tests tools : 0 occurrence (code retour 1) ; seule occurrence docs/roadmap/PRIORITES_ET_DETTES.md:1508 ; git cat-file -t 94e779e8 : 'Not a valid object name' (empreinte de trace, pas un commit)
- **Classe** : E10
- **Verdict** : confirmé

### P10.4 — LIEU_MIXTE plus large que la branche scellée
- **Sonde** : `cd C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34 && sed -n '113,122p;246,249p' tools/evo_runs/e34_identity_cell.py`
- **Constat** : LIEU_MIXTE compare tout le dictionnaire rendu par lieu(), y compris la version de python et deux variables d'environnement (AGAGI_CPU_LIMIT, AGAGI_IMAGE), alors que la branche 5 scellée ne nomme que la plateforme, la version et les threads de torch. Le code peut donc refuser une lecture pour une raison que la règle ne déclare pas. Le risque est faible, car tous les ouvriers sont engendrés par un même parent.
- **Preuve** : tools/evo_runs/e34_identity_cell.py:121-122 lieu() = platform, python, torch, torch_threads, AGAGI_CPU_LIMIT, AGAGI_IMAGE ; :246-247 compare json.dumps du dictionnaire ENTIER (6 cles) contre 3 attributs nommes par la branche 5
- **Classe** : aucune
- **Verdict** : confirmé

### P10.5 — plafond de famine et recalcul du corps
- **Sonde** : `cd C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34 && git grep -n 'update_phenotype(' HEAD -- src tools ; sed -n '697,722p' src/worlds/world_1_stoneage.py`
- **Constat** : Soupçon écarté : le corps (bonus de PV, drain) se dérive de W, et W apprend. Le plafond de famine calculé sur le clone AVANT la phase 1 aurait donc pu ne plus valoir en phase 2. Mais le phénotype n'est recalculé que par mutate, absorb_knowledge, from_genome et la reproduction HGT, jamais sur le chemin des phases 1 et 2. Le drain réellement appliqué est bien métabolisme de base fois drain du modèle.
- **Preuve** : src/agents/mamba_agent.py:140,152,177,198 et src/worlds/world_1_stoneage.py:990 (HGT) sont les seuls appels ; drain = base_metabolism x phenotype_energy_drain a world_1_stoneage.py:702, soustrait a :722 ; starvation_ceiling = 80/(0,75 x drain) a e34_identity_cell.py:129-133
- **Classe** : E26
- **Verdict** : non confirmé

### P10.6 — état par tranche hors permutation
- **Sonde** : `cd C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34 && sed -n '44,89p' tools/slot_identity.py ; sed -n '561,572p;288,294p' src/agents/backend_torch.py ; sed -n '1080,1095p' src/worlds/world_1_stoneage.py`
- **Constat** : Soupçon écarté : un état indexé par tranche échapperait à la permutation. En dehors de W, H, _last, _prev et agents, les seuls états par tranche (traces, bilinéaire, tampons δ) font refuser la permutation. Le rejeu épisodique repart d'un H nul, sur des observations alignées par identifiant, et zero_grad précède chaque backward : aucun gradient périmé n'est porté d'une ligne à l'autre.
- **Preuve** : tools/slot_identity.py:50-61 refus (e_a/e_v, _delta_*, U/V/W_bl, etat d'optimiseur, momentum), :80-89 permutation de W, H, _last, _prev, agents ; src/agents/backend_torch.py:564 H = zeros dans learn_episode, :292 zero_grad avant backward ; world_1_stoneage.py:1088-1093 alignement par id
- **Classe** : E34
- **Verdict** : non confirmé

### P10.7 — canaux d'écriture dans l'état récurrent
- **Sonde** : `cd C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34 && sed -n '48p;223,235p;245p' src/agents/backend_torch.py ; sed -n '1312p;1340p;973p' src/worlds/world_1_stoneage.py ; grep -n '_VALUE_NODE =' src/agents/backend_torch.py`
- **Constat** : Vérifié et vrai : gate éteint par défaut, les logits rendus par forward sont une vue de H, et le monde prend une ligne de cette vue par corps. La soustraction anti-répétition et l'affectation du consensus écrivent donc dans l'état récurrent. V(s') se lit dans self.H au nœud 28, qui est dans le bloc réécrit par le vote. Les quatre canaux et le cinquième écrivain sont correctement décrits.
- **Preuve** : src/agents/backend_torch.py:48 CONDITION_GATE = False, :225 logits = H_new[:, N-O:N], :235 .cpu().numpy() (vue), :245 v_next lu dans self.H, :35 _VALUE_NODE = 28 ; world_1_stoneage.py:1312 logits = batch_logits[idx], :1340 -= 0.1, :973 affectation de ligne entiere
- **Classe** : E5
- **Verdict** : non confirmé
