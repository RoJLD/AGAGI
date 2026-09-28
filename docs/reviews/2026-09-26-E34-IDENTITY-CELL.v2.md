# Revue adversariale : E34-IDENTITY-CELL (v2)

- **Cible** : `C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad/E34-IDENTITY-CELL.v2.json` (pré-inscription, brouillon non scellé)
- **Date** : 2026-09-26
- **SHA** : `f1d6a98708aa171931e284cf702e777db3cc2336` (worktree `.worktrees/e34`)
- **Résultat des TÉMOINS** (les planchers sont sur les mêmes lignes que le score) :
  - `S2-BLIND-CHAMPION-42e9357` : RETROUVE (code 0, 7 recevables) · PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 · plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1) · ⚠ INDISCRIMINANT : le record cru sain rend autant de critiques recevables que les defectueux
  - `LOCK-002-286f244` (cru sain) : MESURE (code 0, 6 recevables) · PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 · plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1) · ⚠ INDISCRIMINANT : le record cru sain rend autant de critiques recevables que les defectueux
  - `EDR-GRAB-COST-1828371` : RETROUVE (code 0, 6 recevables) · PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 · plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1) · ⚠ INDISCRIMINANT : le record cru sain rend autant de critiques recevables que les defectueux
  - `EDR-RETAIN-COMPOSE-4204f8f` : RETROUVE (code 0, 8 recevables) · PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5 · plancher mesure sur LOCK-002-286f244 : 6 critiques recevables (seuil historique 1) · ⚠ INDISCRIMINANT : le record cru sain rend autant de critiques recevables que les defectueux
- **Commandes de vérification** (scratchpad `.../5d7a8f62-2b9c-4c98-89cf-422f8bf285b1/scratchpad`) :
  - `PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier S2-BLIND-CHAMPION-42e9357 <scratchpad>/refutateur_v2/critiques-S2-BLIND-CHAMPION-42e9357.json --extrait <scratchpad>/temoins_v2/temoin-1.md --jugement OUI`
  - `PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier LOCK-002-286f244 <scratchpad>/refutateur_v2/critiques-LOCK-002-286f244.json --extrait <scratchpad>/temoins_v2/temoin-2.md`
  - `PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier EDR-GRAB-COST-1828371 <scratchpad>/refutateur_v2/critiques-EDR-GRAB-COST-1828371.json --extrait <scratchpad>/temoins_v2/temoin-3.md --jugement OUI`
  - `PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier EDR-RETAIN-COMPOSE-4204f8f <scratchpad>/refutateur_v2/critiques-EDR-RETAIN-COMPOSE-4204f8f.json --extrait <scratchpad>/temoins_v2/temoin-4.md --jugement OUI`
- **Bilan** : 41 critiques, 22 confirmées.

## P1

### P1.a
- **Sonde** : `python -c "import json,math; from tools.evo_runs.e34_identity_cell import ARMS; r=json.load(open('results/s2_credit_retention.json'))['arms']['b_warm_credit']['2026']; a=json.load(open('results/s2_credit_ablation_2.json'))['arms']['b_full']['2026']; v=math.ceil(len(ARMS)/6); print(len(ARMS),v,7200/(v*3)); [print(c['elapsed_s'],c['elapsed_s']*v*3,c['survival']['ages']==r['survival']['ages'],c['learning']['dW_abs_sum']==r['learning']['dW_abs_sum']) for c in (r,a)]"`
- **Constat** : Le plafond de 7200 s ne tient que si une cellule dure au plus 800 s : 13 bras répartis en 3 vagues, marge x3, donc 9 fois l'unité. La règle ne s'appuie que sur la durée de P4.4 (536 s). Or le rejeu bit-identique de cette même cellule dans P4.16 a pris 815 s, et la règle cite pourtant ce fichier pour S_a et pour la dispersion. La projection monte alors à 7333 s et project_cost la refuse. Autre point : l'unité projetée est la première cellule TERMINÉE parmi 6 qui tournent en même temps (as_completed), donc la plus rapide, dans un régime de concurrence où aucune des deux durées publiées n'a été mesurée. Si cette prémisse est fausse, la garde E13 annule les 12 cellules restantes et il n'y a aucun verdict. Les 30 min annoncées supposent aussi que 6 ouvriers concurrents ne ralentissent rien, ce qui n'a pas été mesuré.
- **Preuve** : Sortie : n_arms 13, vagues 3, seuil 800,0 s/cellule. P4.4 : 536,3 s, projection 4827 (acceptée). P4.16 : 814,8 s, projection 7333 > 7200 (refusée), avec ages_eq True et dW_eq True, donc c'est la même cellule au bit. Côté code : tools/evo_runs/e34_identity_cell.py:338 (as_completed) et :346-349 (project_cost sur la première cellule terminée, n_units = vagues).
- **Classe** : E12 (unité de coût prise dans un autre régime) / E13
- **Verdict** : confirmé

### P1.b
- **Sonde** : `sed -n 195,215p tools/evo_runs/e34_identity_cell.py ; sed -n 196,202p tools/evo_runs/s2_credit_retention.py ; grep -n np.random src/worlds/world_1_stoneage.py`
- **Constat** : La bande n'a de largeur que si les tirages numpy ajoutés font vraiment bifurquer les shams. Or le verdict ne contrôle que le nombre de tirages et le tick où ils ont lieu. Aucune ligne ne compare la somme |dW| ou les âges d'un sham à ceux du bras éteint. Si les onze shams restaient identiques au bras éteint, la bande se réduirait à S_off seul. Un écart d'une demi-graduation donnerait alors MATERIEL, alors qu'il faudrait signaler que le témoin de bruit est inerte. La bifurcation est plausible à la lecture du monde (un tirage numpy global par agent et par tick), mais c'est un raisonnement : la règle affirme la divergence sans la faire vérifier par une branche.
- **Preuve** : tools/evo_runs/e34_identity_cell.py:206-209 teste seulement slot_order_fix, sham_draws == k et sham_tick == t1 ; :211 bâtit la bande sans garde d'étendue non nulle. tools/evo_runs/s2_credit_retention.py:198-199 tire une seule fois. Le support de la bifurcation, inféré et non mesuré, est src/worlds/world_1_stoneage.py:1187-1188 (_cog_sig par agent via np.random.choice).
- **Classe** : E1
- **Verdict** : confirmé

### P1.c
- **Sonde** : `python -c "import json; d=json.load(open('results/s2_credit_retention.json')); print(d['arms']['b_warm_credit']['2026']['learning']); a=json.load(open('results/s2_credit_ablation_2.json'))['arms']; print(a['a_frozen']['2026']['survival']['survival_median'], sorted(c['survival']['survival_median'] for c in a['b_full'].values()))"`
- **Constat** : Les prémisses chiffrées du témoin sont bien lues et mesurées. La cellule b_warm_credit 2026 de P4.4 porte une dose TD de 1999, 12 résurrections et Σ|ΔW| = 18242.03954219818, et b_full 2026 de P4.16 la reproduit au bit (mêmes âges, même somme). S_a = 31,5 figure dans a_frozen 2026, et l'étendue 7,0 à 9,5 entre seeds est dans le fichier cité. La borne de dose 144/(12x1999), environ 0,60 %, se déduit des 12 résurrections mesurées. Rien n'est recopié de mémoire.
- **Preuve** : Sortie : td_updates 1999, resurrections 12, dW_abs_sum 18242.03954219818 ; a_frozen/2026 = 31.5 ; médianes b_full min 7.0, max 9.5 ; b_full/2026 : mêmes âges [5,6,6,7,7,7,7,8,8,9,9,11] et même dW.
- **Classe** : aucune
- **Verdict** : non confirmé

### P1.d
- **Sonde** : `python -c "import json; [print(f, json.load(open(f))['provenance'], json.dumps(json.load(open(f))).count('thread'), json.dumps(json.load(open(f))).count('platform')) for f in ('results/s2_credit_retention.json','results/s2_credit_ablation_2.json')]"`
- **Constat** : Aucun des deux JSON publiés n'indique le lieu : ni nombre de threads, ni version de torch, ni plateforme. Leur provenance est un arbre sale. La reproduction au bit sur la batcave avec 6 ouvriers concurrents est donc une hypothèse héritée, pas un fait établi. Mais la branche TEMOIN_ROMPU la mesure dans ce run et bloque toute lecture si elle casse. Le risque est donc de perdre le run, pas de renverser le verdict.
- **Preuve** : Sortie : provenance dirty true (sha 05cf8888 et 16163f30) ; 0 mention de thread, 0 de platform, 0 de torch_version dans les deux fichiers. La couverture est à tools/evo_runs/e34_identity_cell.py:170-173 et :195-197 (le témoin ne certifie que la ligne éteinte lue, sinon TEMOIN_ROMPU).
- **Classe** : aucune
- **Verdict** : non confirmé

### P1.e
- **Sonde** : `python -c (arms de results/s2_credit_retention.json et s2_credit_ablation_2.json ; os.listdir('results') filtre e34)`
- **Constat** : La lecture entiere (le 2/13 comme la note NON_MATERIEL) repose sur l'echangeabilite de S_on avec les douze trajectoires. Aucun resultat cite ne la mesure, et le dispositif n'a qu'UNE trajectoire allumee : aucune donnee de ce run ne pourra la tester non plus. C'est une premisse raisonnee, pas mesuree, et la limite declaree ne vise que le bras eteint.
- **Preuve** : s2_credit_retention.json : 3 bras (a_warm_frozen, b_warm_credit, c_cold_credit) ; s2_credit_ablation_2.json : 5 bras (a_frozen, b_const, b_eplr, b_full, b_tdonly), aucun replicat intra-seed ; results e34 presents : [] ; ARMS = 13 dont 1 seul 'on' (e34_identity_cell.py:41)
- **Classe** : E8
- **Verdict** : confirmé

## P2

### P2.a
- **Sonde** : `cd C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34 && python tools/check_regime_claims.py --only "<cible>"; echo EXIT=$?` (worktree à HEAD f1d6a987)
- **Constat** : Porte 19 lancée comme P2 l'exige. Elle refuse, avec une sortie 2 et avant toute analyse. Un JSON de pré-inscription posé dans le scratchpad n'est pas un record docs/EDR/<nom>.md, donc la porte n'a aucun régime cité à confronter aux results. Je recopie ce verdict : aucune vérification du régime n'a eu lieu sur cette cible. Ce refus n'est pas un feu vert. La porte n'est pas fautive, puisque la cible est hors de son périmètre. Aucune dette n'est ouverte et je m'arrête là, comme le prévoit un prompt DÉLÈGUE.
- **Preuve** : La sortie de la commande dit « REFUS : --only designe 1 chemin(s) INCONNU(S) de cette porte -- ni record docs/EDR/<nom>.md present [...] » puis « EXIT=2 ». Ce refus est codé dans tools/check_regime_claims.py:404-405 (_perimetre_only appelle _refus_only quand un chemin est inconnu).
- **Classe** : aucune
- **Verdict** : hors périmètre

### P2.b
- **Sonde** : `python tools/check_regime_claims.py --only <cible>`
- **Constat** : Porte lancee : elle refuse la cible, qui n'est pas un record docs/EDR.
- **Preuve** : REFUS : --only designe 1 chemin(s) INCONNU(S) de cette porte
- **Classe** : aucune
- **Verdict** : hors périmètre

## P3

### P3.a (DELEGUE) - balayage du pas, porte 23
- **Sonde** : `cd .worktrees/e34 && python tools/check_e19_optimizer_sweep.py --only tools/evo_runs/e34_identity_cell.py; echo exit=$? ; puis python tools/check_e19_optimizer_sweep.py --report | grep -n e34 ; git ls-files | grep -i E34-IDENTITY`
- **Constat** : Porte 23 lancee sur le runner de la cible : sortie 0, rien de bloquant, mais le runner est range dans la categorie regle_absente (nouveau, a geler). La porte n'a donc PAS pu dire si le dispositif est sous gradient ni si la garde E19 est appelee : la regle que le runner verifie (PREREG E34-IDENTITY-CELL, verify a la ligne 305) n'existe pas encore dans docs/preregistrations/ puisque la cible est un brouillon v2 non scelle. Verdict recopie : OK non bloquant, question P3 NON tranchee par la porte ; a relancer telle quelle apres le scellement.
- **Preuve** : Sortie de la porte (HEAD f1d6a987) : 'runners scelles : 35 | sous gradient (PLANCHER) : 12 | nus (PLANCHER) : 9 | indetermines : 4 | non resolus : 6 | regle absente : 1 | illisibles : 0 | appelants de la garde : 3 | geles : 19' puis 'NOUVEAU (non bloquant) : [regle_absente] tools/evo_runs/e34_identity_cell.py', exit=0. tools/evo_runs/e34_identity_cell.py:37 PREREG = "E34-IDENTITY-CELL" ; :305 verify(PREREG) ; git ls-files ne rend que docs/reviews/2026-09-26-E34-IDENTITY-CELL.v1.md, aucune regle scellee.
- **Classe** : E19
- **Verdict** : confirmé - la porte rend OK (exit 0) mais classe le runner regle_absente : P3 reste ouvert jusqu'au scellement, relancer la meme commande sur la regle scellee

### P3.b
- **Sonde** : `python tools/check_e19_optimizer_sweep.py --only tools/evo_runs/e34_identity_cell.py`
- **Constat** : Porte OK. Le runner est classe regle_absente (non bloquant) tant que la regle n'est pas scellee.
- **Preuve** : runners scelles : 35 | ... | NOUVEAU [regle_absente] tools/evo_runs/e34_identity_cell.py | OK
- **Classe** : aucune
- **Verdict** : non confirmé

## P4

### P4.a
- **Sonde** : `python -c 'from tools.evo_runs.e34_identity_cell import ARMS,K_SHAMS,WORKERS_MAX' ; python tools/check_control_family.py --report`
- **Constat** : Compte relu dans le runner : 13 bras, 11 shams, 3 vagues de 6 ouvriers, une seule comparaison bilaterale. Le 2/(K+2) du code vaut bien le 2/13 annonce. Rien a redire.
- **Preuve** : 13 bras ; 11 shams ; vagues 3 ; 2/(K+2)=0.1538 ; porte : 33 runners scelles, 0 sans design
- **Classe** : aucune
- **Verdict** : non confirmé

## P5

### P5.a
- **Sonde** : `grep -c random tools/slot_identity.py ; sed -n 1184,1190p src/worlds/world_1_stoneage.py ; grep -n 'np.random.random' tools/evo_runs/s2_credit_retention.py`
- **Constat** : Le bras allume et les shams ne perturbent pas la meme chose. La remise en ordre ne tire rien, et le monde tire le signal cognitif agent par agent dans l'ordre de la liste : la tranche i recoit donc la i-eme paire dans les DEUX bras on/off, et les evenements du monde restent synchrones. sham_k, lui, decale tout le flux numpy. La bande mesure 'un autre monde aleatoire', le traitement 'le meme monde, corps reattribues' : S_on part structurellement plus pres de S_off, d'ou un biais vers NON_MATERIEL (robustesse fabriquee). Parade : des shams de PERMUTATION a t1 (0 tirage).
- **Preuve** : tools/slot_identity.py : 0 occurrence de random ; world_1_stoneage.py:1186-1188 (for _a in self.agents : 2 np.random.choice par agent et par tick) ; s2_credit_retention.py:199 (np.random.random(k) une fois a t1)
- **Classe** : E2
- **Verdict** : confirmé

### P5.b (JUGE) — le contrôle pouvait-il échouer : la bande de shams
- **Sonde** : `grep -c assert_positive_control|assert_not_degenerate|assert_ablation_changes_something` sur tools/evo_runs/e34_identity_cell.py et s2_credit_retention.py ; `python scratchpad/p5_sonde.py` (injection sans monde : 11 shams copies exactes de off, S_on = 9,0 contre S_off = 8,5)
- **Constat** : Rien ne garantit que les onze shams divergent réellement de la ligne éteinte. identity_cell_verdict assemble la bande sans comparer le dW ni les âges des shams à ceux de off, et le runner n'appelle aucune des trois gardes du pré-vol. Si les tirages numpy supplémentaires ne changent rien à la phase 1, la bande se réduit à un seul point, S_off, et le moindre écart de S_on sur la grille 0,5 devient un verdict MATERIEL. Aucun des 22 tests de verdict ne couvre ce cas, et aucun test en monde réel ne montre qu'un sham modifie ce qui est appris : le seul test de sham (ligne 200) ne vérifie que l'état des RNG.
- **Preuve** : Les grep rendent 0/0/0 dans les deux fichiers. La sonde rend « verdict: MATERIEL_HAUSSE », « band: 8.5 8.5 », « distinct dW in band: 1 ». La bande est construite sans contrôle de largeur (tools/evo_runs/e34_identity_cell.py:211-213). Le seul test de sham est tests/sandbox/test_e34_slot_identity.py:200-224, qui porte sur les RNG et ne calcule aucun digest.
- **Classe** : E1
- **Verdict** : confirmé

### P5.c (JUGE) — contrôle positif du MÊME dispositif, au MÊME régime
- **Sonde** : Read tests/sandbox/test_e34_slot_identity.py:283-315 et 357-363 ; grep -c des trois gardes dans le runner (0)
- **Constat** : Le seul contrôle positif du drapeau tourne sur un dispositif sans commune mesure avec la cellule jugée : 3 agents, 16 ticks, deux morts FORCÉES en tête (la dose maximale de désalignement), et une DV qui est l'empreinte des poids W. La cellule, elle, compte 12 agents, 2000 ticks, des morts naturelles (au plus 144 commutations, soit environ 0,6 % des transitions), et sa DV est la médiane de survie sur la grille 0,5. Qu'une empreinte change au dernier bit ne dit pas que la survie médiane peut sortir de la bande. Aucun contrôle ne montre qu'un effet de taille connue, à la dose réelle, franchirait la bande de douze trajectoires : l'issue MATERIEL n'est jamais démontrée atteignable par l'instrument.
- **Preuve** : _trace a pour défauts n=3, ticks=16, kills=((2, 0), (6, 1)) (test_e34_slot_identity.py:283). Le contrôle positif ne teste que fix[digest] != ref[digest] (ligne 363). La DV du verdict est survival_median (e34_identity_cell.py:143), et la cellule tourne en num_agents=12, ticks_learn=2000 (lignes 103-117).
- **Classe** : E6
- **Verdict** : confirmé

### P5.d (JUGE) — fausse alarme sous H0 publiée sans mesure
- **Sonde** : `python scratchpad/p5_sonde.py` (même injection que ci-dessus)
- **Constat** : Le taux de fausse alarme est une constante, 2/(n+2), écrite dans le verdict quelle que soit la bande observée. Avec une bande réduite à une seule valeur distincte, le runner publie 0,1538, alors que la fausse alarme réelle s'approche de la probabilité que S_on diffère de S_off d'un seul pas de grille. Le chiffre qui accompagne un MATERIEL n'est donc pas mesuré sur la cellule qu'il qualifie.
- **Preuve** : La sortie affiche « fausse_alarme_h0 publiee: 0.1538 » pour « distinct dW in band: 1 ». La valeur est une constante codée en dur (e34_identity_cell.py:157, 2.0 / (int(n_shams) + 2)), et aucun compte d'ex-aequo n'est fait dans la bande (lignes 211-212).
- **Classe** : E8
- **Verdict** : confirmé

### P5.e (JUGE) — la référence gelée et le témoin sont-ils du même dispositif ?
- **Sonde** : python heredoc qui lit results/s2_credit_retention.json et results/s2_credit_ablation_2.json au seed 2026
- **Constat** : Le témoin éteint peut échouer (égalité exacte au bit) et vient de la même cellule que la bande publiée : P4.4 b_warm_credit et P4.16 b_full donnent la même survie au seed 2026, et le S_a gelé n'intervient que comme descriptif. Je n'ai pas trouvé de défaut de dispositif sur ce point.
- **Preuve** : La sortie donne P44 b_warm_credit S=7.0 avec res=12, P416 b_full S=7.0 et P416 a_frozen S=31.5. Le témoin est vérifié par égalité exacte (e34_identity_cell.py:127).
- **Classe** : aucune
- **Verdict** : non confirmé

### P5.f (JUGE) — référence à pas nul de P3
- **Sonde** : `grep -n lr_override tools/evo_runs/e34_identity_cell.py`
- **Constat** : Il n'y a aucune référence lr=0 : les treize bras ont le même pas, celui du learner, sans override. La question du même dispositif pour une référence à pas nul ne se pose donc pas sur cette cellule.
- **Preuve** : e34_identity_cell.py:249 (lr_override=None) et :250 (même pas dans tous les bras) ; ligne 23 de la cible (champ pas).
- **Classe** : aucune
- **Verdict** : hors périmètre

## P6

### P6.a
- **Sonde** : `python scratchpad/e34_v2_probe.py` (injection, aucun monde)
- **Constat** : L'etiquette FORT et la part d'erosion levee se calculent contre S_off seul, sans leur equivalent sur les shams. Un contraste noye dans la bande sort donc etiquete FORT avec un ratio de 24 %, et aucun plancher n'est publie a cote de ce ratio.
- **Preuve** : e34_identity_cell.py:192-193 ; sortie (1) : NON_MATERIEL | fort = True | dS = 6.0 | part_erosion_levee = 0.245 | bande 2.0 16.0
- **Classe** : aucune
- **Verdict** : confirmé

### P6.b
- **Sonde** : `grep -nE "part_erosion_levee|fort|S_shams" tools/evo_runs/e34_identity_cell.py` ; python -c qui charge results/s2_credit_ablation_2.json (a_frozen et b_full, seed 2026)
- **Constat** : Les deux descriptifs chiffrés du contraste (fraction d'érosion rattrapée, étiquette FORT) sortent sans leur équivalent calculé sur les onze perturbations témoins. La sortie peut donc afficher FORT et une fraction rattrapée non nulle à côté d'un NON_MATERIEL, sans dire que les shams atteignent les mêmes valeurs. Le plancher de bruit existe (band_values), mais pas dans l'unité du ratio publié.
- **Preuve** : tools/evo_runs/e34_identity_cell.py:192-193 calculent dS/erosion_off et |dS|>=5 pour le SEUL bras allumé ; la ligne 183 publie les S_sham bruts, sans dS_k ni part_k. erosion_off = 31,5 - 7,0 = 24,5 (JSON). Le seuil 5 est hérité de P4.4, alors que l'étendue entre seeds de b_full vaut 2,5 (7,0 à 9,5).
- **Classe** : aucune
- **Verdict** : confirmé

### P6.c
- **Sonde** : `grep -n "e.agents.append(a)" tools/evo_runs/s2_credit_retention.py ; grep -n "e.agents\[:\] = ordonne" tools/slot_identity.py ; sed -n 1310p et 1575,1590p src/worlds/world_1_stoneage.py ; grep -ciE "traitement|processing|premier servi" <cible>` -> 1
- **Constat** : Le correctif agit en réordonnant la liste des corps. Il change donc aussi QUI est servi en premier dans la boucle d'action, alors que dans le bras éteint et les onze shams le ressuscité passe toujours en dernier. Aucune des douze valeurs de la bande ne vient d'une trajectoire qui change la priorité de service sans réparer l'appariement : la bande n'est pas le plancher du contraste entier, et un MATERIEL ne séparerait pas l'identité de la priorité. Ce canal n'est pas déclaré dans la règle, et son amplitude n'est pas mesurée.
- **Preuve** : s2_credit_retention.py:111 (le ressuscité va en queue) contre slot_identity.py:69 (le drapeau réordonne e.agents). world_1_stoneage.py:1310 : la boucle d'action suit l'ordre de e.agents ; :1587 : ramassage au premier servi (items.remove). Dans la cible, 1 seule occurrence (ligne 6), sans rapport.
- **Classe** : aucune (voisine d'E34 : la position porte aussi la priorité de service)
- **Verdict** : confirmé

### P6.d
- **Sonde** : `ls results/e34_identity_cell` ; python -c qui charge s2_credit_ablation_2.json et s2_credit_retention.json (b_full min/max, a_frozen 2026, âges, td_updates, résurrections, dW)
- **Constat** : La comparaison du contraste à sa bande n'est pas faisable : aucune cellule n'a été mesurée. Les valeurs de bande et de témoin citées sont exactes. La cellule publiée se trouve au bord BAS de la dispersion entre seeds (S_off = minimum de b_full). Le plafond de fausse alarme 2/13 (0,154) est bien celui que publie le runner.
- **Preuve** : ls : répertoire absent. b_full : n=12, min 7,0, max 9,5 ; a_frozen 2026 = 31,5. Âges [5,6,6,7,7,7,7,8,8,9,9,11], 1999 / 12 / 18242.03954219818, identiques dans les deux JSON. e34_identity_cell.py:157 calcule 2/(11+2).
- **Classe** : aucune
- **Verdict** : hors périmètre (pré-inscription sans résultat ; chiffres cités vérifiés exacts)

### P6.e
- **Sonde** : `grep -ciE "no.?op" <cible>` -> 0 ; `grep -nE "def test_.*noop" tests/sandbox/test_e34_slot_identity.py`
- **Constat** : Il existe un no-op EXACT de l'instrument lui-même : sans mort, le drapeau est testé bit-identique, et la ligne éteinte, audit allumé, doit reproduire au bit la cellule publiée. La cible ne le cite pas (0 occurrence de no-op), mais il existe et il est exécutable.
- **Preuve** : tests/sandbox/test_e34_slot_identity.py:348 (test_without_death_the_fix_is_a_bit_exact_noop) et :336 (drapeau éteint + audit bit-identiques à la référence) ; e34_identity_cell.py:177-180 : le verdict lève si le témoin ne certifie pas la ligne éteinte lue.
- **Classe** : aucune
- **Verdict** : non confirmé

## P7

### P7.a
- **Sonde** : `python scratchpad/e34_v2_probe.py`
- **Constat** : La phrase NON_MATERIEL cite la dose du bras ETEINT. Or les trajectoires divergent apres t1, et ce que le drapeau a retire se lit dans positions_reordered du bras allume, publie mais non cite. Par injection (60 contre 3), la phrase dit 60. Enfin, rien ne garde la dose TD des bras allume et shams : seul le bras eteint passe par le temoin.
- **Preuve** : e34_identity_cell.py:221 (desc['switches_off']) ; sortie (3) : switches_off = 60 | positions_reordered_on = 3 | why: ... a SA dose (60 commutations)
- **Classe** : E8
- **Verdict** : confirmé

### P7.b (JUGE) Dose : canal episodique non dose
- **Sonde** : `python -c "import json;d=json.load(open('results/s2_credit_retention.json'))['arms']['b_warm_credit']['2026']['learning'];sw=12*d['resurrections'];print(d['td_updates'],d['episode_updates'],sw/(12*d['td_updates']),sw/(12*d['episode_updates']))" ; grep -n 'torch_episode_k = 8|current_ids|idx = \[pos|learn_episode(obs_seq' src/worlds/world_1_stoneage.py ; sed -n 132,137p tools/evo_runs/s2_credit_retention.py | grep -c episode`
- **Constat** : La dose du defaut n'est chiffree que sur le canal TD (denominateur = appels TD par agent). Or la cellule publiee a aussi recu 250 mises a jour episodiques, que le monde realigne par id sur la position COURANTE : chaque commutation contamine donc aussi une fenetre de 8 ticks sur 250 par tranche. Borne episodique 4,8 %, huit fois la borne TD sur laquelle la regle ecrit son pronostic a priori (effet improbable). L'audit n'a aucun compteur d'episodes a cheval : cette part de la dose n'est ni mesuree ni publiee.
- **Preuve** : sortie : td_updates 1999, episode_updates 250, borne TD 0,0060 contre borne episodique 0,048 (ratio 7,996) ; world_1_stoneage.py:52 (k=8), :1080, :1092, :1097 (replay aligne par id sur la position courante) ; e34_identity_cell.py:186 (fraction TD seule) ; compteurs d'identite s2_credit_retention.py:132-137 : 0 cle episode
- **Classe** : E8
- **Verdict** : confirmé

### P7.c (JUGE) Dose : nul de letalite sous le plancher
- **Sonde** : `python -c "import json;r=json.load(open('results/s2_credit_retention.json'))['arms']['b_warm_credit']['2026']['survival'];p=json.load(open('results/s2_credit_ablation_2.json'))['arms']['b_full'];b=[p[s]['survival']['survival_median'] for s in p];print(r['survival_median'],r['ages'],r['censored'],sum(v<9.0 for v in b))" ; grep -n '^FLOOR' tools/evo_runs/s2_credit_retention.py ; grep -ciE 'plancher|floor|9,0 ' E34-IDENTITY-CELL.v2.json` (motif valide : 10 lignes sur docs/REF/REGISTRE_ERREURS.md)
- **Constat** : La DV lue par la sonde vit sous le plancher no-perception du meme regime : la ligne eteinte publiee perd ses 12 agents en 11 ticks (mediane 7,0, zero censure) et 9 des 12 seeds b_full de P4.16 sont sous 9,0. Un NON_MATERIEL y confond nul d'identite et nul de letalite ; la sortie par le bas de la bande est comprimee (ages minimaux 5-6), seule la hausse a de la marge. La regle ne nomme ni ce plancher ni une branche qui le traite ; c'est la forme de WARM-002 (5-7 ticks sous 9,0 lus comme absence d'effet).
- **Preuve** : sortie : S_off 7.0, ages [5..11], censures 0, b_full P4.16 9/12 < 9,0 ; tools/evo_runs/s2_credit_retention.py:45 FLOOR = 9.0 (plancher no-perception, meme regime) ; regle v2 : 0 ligne plancher/floor ; docs/REF/REGISTRE_ERREURS.md:37 (E3, precedent WARM-002 sous 9,0)
- **Classe** : E3
- **Verdict** : confirmé

### P7.d (JUGE) Dose : dose par bras absente de l'agregat
- **Sonde** : `grep -n 'switches_off|"resurrections": {|"dW": {' tools/evo_runs/e34_identity_cell.py ; sed -n 183,191p tools/evo_runs/e34_identity_cell.py | grep -oE '"(switches_[a-z]+|resurrections|dW|td_updates|episode_updates)"' | sort | uniq -c`
- **Constat** : L'agregat du verdict ne remonte les commutations que pour la ligne eteinte, alors que la bande a douze membres qui divergent apres t1 et accumulent chacun leur propre compte (zero cote allume). La phrase NON_MATERIEL cite donc une dose unique pour un contraste qui en porte treize ; td_updates et episode_updates par bras ne remontent pas non plus (seuls resurrections et somme |dW|). Les compteurs existent dans chaque fichier de cellule, mais l'objet que lit le verdict ne les porte pas.
- **Preuve** : e34_identity_cell.py:185 (switches_off seul), :189-190 (resurrections et dW par bras), :221 (texte NON_MATERIEL = desc['switches_off']) ; comptage des cles de dose dans desc : switches_off 1, dW 1, resurrections 2 (cle + get), td_updates 0, episode_updates 0, switches des shams 0
- **Classe** : aucune
- **Verdict** : confirmé

## P8

### P8.a
- **Sonde** : `python tools/check_io_overlap.py ; grep -n 'W\[' runner ; grep -rnE '\.surprise\s*=' src/`
- **Constat** : Le runner ne touche aucune ligne de W. Le phenotype est fige a from_genome et la voie torch n'ecrit jamais model.surprise : un desalignement durable ne fait donc pas fuir la curiosite d'une tranche a l'autre. La premisse de re-etiquetage tient a la lecture.
- **Preuve** : 358 genomes, 10 chevauchants connus, 0 nouveau ; seul 'W[' = docstring slot_identity.py:5 ; surprise ecrit en mamba_agent.py:114 et :947 (chemins numpy), jamais dans backend_torch.py
- **Classe** : aucune
- **Verdict** : non confirmé

### P8.b (JUGE) — vue de l'état récurrent
- **Sonde** : `python scratchpad/p8_sonde.py` (3 clones du bassin, forward, puis logits[1][2] -= 0.1 comme le monde) ; `grep -n 'logits\[agent\["last_action"\]\] -= 0.1\|return logits.cpu().numpy()' src/worlds/world_1_stoneage.py src/agents/backend_torch.py`
- **Constat** : Le monde écrit sa pénalité anti-répétition (-0,1) dans le tableau de logits rendu par le forward. Ce tableau partage sa mémoire avec pop.H, donc l'écriture atterrit dans l'état de la TRANCHE i, mais l'indice pénalisé est last_action, un champ porté par le CORPS i. Sans le drapeau, à chaque commutation la tranche reçoit la pénalité sur l'action choisie par l'autre tranche qui conduisait ce corps juste avant ; avec le drapeau, cela n'arrive plus. L'aliasing d'INFRA-001 n'est donc pas une nuisance neutre posée sur le contraste : c'est un quatrième canal du défaut E34, que le drapeau coupe. Ce canal manque dans la liste de la dose (TD, H, fenêtre épisodique), et P2.138 le supprimerait. L'ampleur d'un MATERIEL éventuel dépend donc de l'état d'INFRA-001, et la section des exclusions doit le dire. Ordre de grandeur : une pénalité de 0,1 au plus par commutation.
- **Preuve** : src/agents/backend_torch.py:210 (return logits.cpu().numpy(), une vue) ; src/worlds/world_1_stoneage.py:1278 (corps i <-> ligne i) ; :1340 (indice = agent["last_action"]) ; :1355 (last_action stocké sur le corps). Sortie de la sonde : H[1,out+2] passe de 0.0 à -0.10000000149 après écriture dans logits, shares_memory True. Cible E34-IDENTITY-CELL.v2.json:9 (trois canaux listés) opposée à :29 (aliasing traité comme commun aux treize bras).
- **Classe** : E34
- **Verdict** : confirmé

### P8.c (JUGE) — corps dérivé de W (E26)
- **Sonde** : `grep -n 'W\[' tools/evo_runs/e34_identity_cell.py tools/evo_runs/s2_credit_retention.py tools/slot_identity.py ; python scratchpad/p8_sonde.py`
- **Constat** : Le drapeau ne touche aucune ligne de W : il permute la liste des corps. Le phénotype est calculé une seule fois dans from_genome. Le write-back ne le recalcule pas : après avoir forcé W[0:5] de +1, hp_bonus reste à 688,83 alors qu'un recalcul donnerait 8613,29. Les douze clones ont donc le même corps (hp_bonus 688,83, drain 14,89) dans les deux phases et dans les treize bras. Le contraste ne compare pas des corps. Effet de bord commun à tous les bras, qui ne biaise pas le contraste : le corps de phase 2 est celui du bassin et non celui du W appris.
- **Preuve** : grep : 0 indexation de W dans les runners (seule occurrence : docstring tools/slot_identity.py:5). src/agents/mamba_agent.py:83-88 (update_phenotype) n'est appelé ni par backend_torch.py:509-513 ni par le runner. Sonde : hp_bonus [688.82666 x3], drain [14.888267 x3] ; après write-back, 688.82666 contre 8613.287354 au recalcul.
- **Classe** : E26
- **Verdict** : non confirmé

### P8.d (JUGE) — chevauchement entrée/sortie (E24)
- **Sonde** : `python tools/check_io_overlap.py ; python scratchpad/p8_sonde.py`
- **Constat** : Le bassin WARM-003 déclare 59 entrées et 108 sorties dans 172 nœuds, soit 167 nœuds occupés et aucun slot partagé. load_bassin appelle la garde avant de cloner, et la porte ne voit aucun génome persisté nouveau ou aggravé.
- **Preuve** : porte : 358 génomes persistés, 10 chevauchants (10 connus, 0 nouveau, 0 aggravé), OK. Sonde : bassin I O N 59 108 172, overlap 0. tools/evo_runs/s2_credit_retention.py:61 (assert_no_io_overlap).
- **Classe** : E24
- **Verdict** : non confirmé

### P8.e (JUGE) — seconde écriture aliasée (consensus social)
- **Sonde** : `grep -n 'batch_logits\[idx\] = consensus_logits' src/worlds/world_1_stoneage.py ; sed -n 32,70p src/swarm/consensus.py`
- **Constat** : Le consensus écrit un même vecteur dans plusieurs lignes de H (couplage entre tranches), commun aux treize bras. Le vote ne garde aucun état et ne mémorise aucun identifiant (fitness pondérée seulement). Si le désalignement persiste, l'effet se réduit à un ré-étiquetage. Je ne trouve aucun canal propre au bras sur ce site.
- **Preuve** : src/worlds/world_1_stoneage.py:973 ; src/swarm/consensus.py:32-70 (vote sans état, softmax des fitness)
- **Classe** : aucune
- **Verdict** : non confirmé

### P8.f — hors champ, à renvoyer vers P5/P10
- **Sonde** : `grep -n 'e.agents\[:\] = ordonne' tools/slot_identity.py ; grep -n 'for i, agent in enumerate(self.agents)' src/worlds/world_1_stoneage.py`
- **Constat** : Le correctif réordonne les CORPS au lieu de permuter les tranches (W, H, _prev). À partir de t1, le bras allumé résout donc les actions dans un autre ordre séquentiel que le bras éteint, ce qu'aucun sham ne reproduit. Permuter la population laisserait l'ordre de traitement du monde intact. Autre point : la clause 5 considère toute remise en ordre après t1 comme un mensonge du harnais, alors que le drapeau en fait une à chaque résurrection qui désaligne.
- **Preuve** : tools/slot_identity.py:69 ; src/worlds/world_1_stoneage.py:1278 ; E34-IDENTITY-CELL.v2.json:16 (clause 5) opposée à :9 (12 résurrections)
- **Classe** : aucune
- **Verdict** : hors périmètre

## P9

### P9.a
- **Sonde** : `python tools/check_evidence_provenance.py --only <cible> ; python -c "from tools.preregister import verify; verify('E34-IDENTITY-CELL')"`
- **Constat** : Porte de provenance : cible refusee (ce n'est pas un record). Sceau : la regle n'existe pas encore sous docs/preregistrations.
- **Preuve** : REFUS : --only designe 1 chemin(s) INCONNU(S) ; FileNotFoundError : aucune pre-inscription E34-IDENTITY-CELL
- **Classe** : aucune
- **Verdict** : hors périmètre

### P9.b (DELEGUE) -- provenance : porte 20
- **Sonde** : `cd .worktrees/e34 && python tools/check_evidence_provenance.py --only <cible> ; echo exit=$?`
- **Constat** : La porte 20 ne rend aucun verdict de provenance sur cette cible : elle ne connaît que les records docs/EDR/*.md, et la cible est un brouillon de pré-inscription posé hors du dépôt. Verdict recopié : REFUS, code 2. Les results/*.json que cite la règle (s2_credit_retention.json, s2_credit_ablation_2.json) n'ont été confrontés à aucune porte dans ce prompt.
- **Preuve** : sortie : 'REFUS : --only designe 1 chemin(s) INCONNU(S) de cette porte -- ni record docs/EDR/<nom>.md present' ; exit=2 ; ls docs/EDR | grep -i e34 -> 0 ligne (aucun record E34 à HEAD f1d6a987)
- **Classe** : aucune
- **Verdict** : hors périmètre

### P9.c (DELEGUE) -- sceau de la pré-inscription
- **Sonde** : `cd .worktrees/e34 && python -c "from tools.preregister import verify; verify('E34-IDENTITY-CELL')" ; echo exit=$? ; ls docs/preregistrations | grep -ic e34 ; grep -n 'PREREG = \|verify(PREREG)' tools/evo_runs/e34_identity_cell.py`
- **Constat** : Le sceau n'existe pas encore : aucun fichier E34-IDENTITY-CELL dans docs/preregistrations, et verify lève FileNotFoundError. C'est l'état attendu d'une v2 soumise à revue, puisque la règle déclare un coût (budget_s) et ne se scelle qu'après revue (reviewed_by). Le runner lit ce nom (PREREG, ligne 37) et lève sans lui (verify aux lignes 267 et 305) : aucune cellule ne peut tourner avant le sceau. La sonde a un contrôle positif : verify('S2-BASSIN-FRAGILITY') rend une règle de 17 clés.
- **Preuve** : FileNotFoundError : aucune pré-inscription « E34-IDENTITY-CELL » (tools/preregister.py:196), exit=1 ; grep -ic e34 -> 0 ; tools/evo_runs/e34_identity_cell.py:37 PREREG = "E34-IDENTITY-CELL", :267 et :305 verify(PREREG)
- **Classe** : aucune
- **Verdict** : hors périmètre

## P10

### P10.a
- **Sonde** : `sed -n 201-205p tools/evo_runs/e34_identity_cell.py ; python scratchpad/e34_v2_probe.py`
- **Constat** : Le texte de la branche 5 traite comme un mensonge du harnais toute remise en ordre hors de t1. Or le bras allume doit en faire une a chaque mort non terminale apres t1, et le code ne teste que la PREMIERE. Lu a la lettre, le texte rend presque tout run INDETERMINE : le lecteur devra trancher apres coup entre le texte et le code.
- **Preuve** : e34_identity_cell.py:202-203 (seul first_reorder_tick == t1) ; sortie (2) : ticks_reordered_on = 7 accepte, verdict MATERIEL_HAUSSE sans lever
- **Classe** : E11
- **Verdict** : confirmé

### P10.b
- **Sonde** : `grep -n '_charge()' tools/evo_runs/e34_identity_cell.py`
- **Constat** : Les descriptifs promettent la charge machine au debut ET a la fin de chaque cellule. Le runner ne mesure le debut qu'une fois pour les treize, et la 'fin' est prise par le parent quand il recoit le resultat. Les cellules des vagues 2 et 3 n'ont donc pas de charge de depart.
- **Preuve** : e34_identity_cell.py:330 (charge_depart, une fois dans tout) ; :251 (charge_fin dans _cell_record, cote parent)
- **Classe** : E12
- **Verdict** : confirmé

### P10.c
- **Sonde** : `python <scratchpad>/p10_v2_sondes.py` (bras allumé injecté : 6 réordonnancements, dont 5 après t1) ; `sed -n 180,190p tests/sandbox/test_e34_slot_identity.py`
- **Constat** : Texte scellé et code divergent sur la branche 5 : la règle traite comme harnais défaillant tout réordonnancement du bras allumé à un autre tick que t1. Or le drapeau réordonne à chaque résurrection désalignante, et le verdict ne contrôle que le PREMIER réordonnancement. Lue à la lettre, la règle rendrait INDETERMINE toute cellule à deux résurrections désalignantes ou plus ; le code, lui, l'accepte et lit la bande. Corriger le texte (première remise en ordre = t1) avant de sceller.
- **Preuve** : tools/evo_runs/e34_identity_cell.py:203 ne teste que first_reorder_tick == t1 ; tests/sandbox/test_e34_slot_identity.py:189 exige ticks_reordered == 2 sous drapeau ; sonde : verdict NON_MATERIEL, aucune levée, avec 5 réordonnancements hors t1.
- **Classe** : E10
- **Verdict** : confirmé

### P10.d
- **Sonde** : `python <scratchpad>/p10_v2_sondes.py` (témoin rompu avec 4 shams présents sur 11, puis avec les 13 cellules)
- **Constat** : La branche TEMOIN_ROMPU est quasi inatteignable par la sous-commande tout. Sur un témoin raté, le runner annule, quitte la boucle sans sauver les cellules en vol, puis lit. Comme l'absence de cellule est testée avant le témoin, le JSON publié dit INCOMPLET et « reprise ». La cause connue (le témoin est cassé) n'arrive ni au verdict ni au registre, et la consigne publiée pousse à relancer le même dispositif.
- **Preuve** : tools/evo_runs/e34_identity_cell.py:354-358 (break) puis :360-361 (_lire) ; :161-164 (INCOMPLET) est testé avant :195 (TEMOIN_ROMPU) ; sonde : témoin rompu + 7 cellules absentes -> INCOMPLET ; témoin rompu + 13 cellules -> TEMOIN_ROMPU.
- **Classe** : aucune
- **Verdict** : confirmé

### P10.e
- **Sonde** : `grep -n 'provenance\|sha' tools/evo_runs/e34_identity_cell.py ; grep -c 'remove\|unlink\|rmtree' tools/evo_runs/e34_identity_cell.py`
- **Constat** : Aucune ligne ne garantit que les treize cellules viennent du même commit, contrairement à ce que la règle annonce. Chaque fichier de cellule porte sa provenance, mais la lecture ne garde que la clé row, et la seule garde d'homogénéité compare le lieu. La sous-commande tout ne vide pas le répertoire des cellules : un fichier resté d'une exécution antérieure (sous-commande cellule, run coupé, autre commit sur la même machine) comble un trou et entre dans la bande sans laisser de trace.
- **Preuve** : tools/evo_runs/e34_identity_cell.py:246 écrit la provenance, :272 ne relit que ["row"], :172-173 ne compare que le lieu ; nettoyage du répertoire : 0 occurrence.
- **Classe** : E31
- **Verdict** : confirmé

### P10.f
- **Sonde** : `grep -c 'CostGuard\|timeout' tools/evo_runs/e34_identity_cell.py` -> 0 ; `python <scratchpad>/p10_v2_sondes.py` (sonde d : même geste cancel puis raise)
- **Constat** : Le plafond de 7200 s n'existe que comme une projection faite sur la première cellule terminée. Aucune garde ne tourne pendant le run (0 CostGuard, 0 timeout), et le refus ne coupe rien : cancel() échoue sur les tâches déjà confiées aux ouvriers, et la sortie du bloc ProcessPoolExecutor attend leur fin, bail kuzu tenu. Aucune ligne ne publie une coupe ni la charge qui l'accompagne.
- **Preuve** : tools/evo_runs/e34_identity_cell.py:344-353 ; sonde : cancel() = [False, False, False, False], 12,2 s de mur après un refus levé à 1 s.
- **Classe** : E13
- **Verdict** : confirmé

### P10.g
- **Sonde** : sed/grep sur s2_credit_retention.py, world_1_stoneage.py, backend_torch.py, grid_compare.py ; python -c chargeant results/s2_credit_retention.json et results/s2_credit_ablation_2.json
- **Constat** : Lignes citées relues et conformes au texte. Le mort est rajouté en queue, et la population n'est reconstruite que si B change. Le write-back suit l'index de construction, et le monde écrit dans la vue des logits. La fenêtre épisodique de 8 est réalignée par identifiant sur l'ordre courant, donc rejouée sur une autre tranche après une commutation. Les survivants gardent leur ordre : au plus 12 commutations par tick, 144 au total. Le sham ne tire que le RNG numpy, que le monde consomme à chaque pas. Les bords de bande sont inclus par comparaison stricte. Les valeurs du témoin et de P4.16 sont lues dans les JSON.
- **Preuve** : s2_credit_retention.py:111 et :199 ; world_1_stoneage.py:52, :973, :1060-1067, :1079-1093, :1187, :1340, :1784 ; backend_torch.py:109, :512 ; grid_compare.py:68 ; JSON : 1999 / 12 / 18242.03954219818, b_full [7.0 ; 9.5], a_frozen 31.5.
- **Classe** : aucune
- **Verdict** : non confirmé
