# Revue adversariale -- DEPORT-NEXUS-TEMOIN_Meme_Seed_Batcave_Contre_Nexus

- **Cible** : `docs/EDR/DEPORT-NEXUS-TEMOIN_Meme_Seed_Batcave_Contre_Nexus.md`
- **Date** : 2026-09-26
- **SHA** : `def16adccccfeb36cd211e8e5264c0e4e5d69dbe`
- **Résultat des TÉMOINS** :
  - `S2-BLIND-CHAMPION-42e9357` : RETROUVE (code 0, 7 recevables) -- `PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier S2-BLIND-CHAMPION-42e9357 <scratchpad>/refutateur/critiques-S2-BLIND-CHAMPION-42e9357.json --extrait <scratchpad>/refutateur/temoins/temoin-1.md --jugement OUI`
  - `LOCK-002-286f244` (témoin cru sain) : MESURE (code 0, 8 recevables) -- `PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier LOCK-002-286f244 <scratchpad>/refutateur/critiques-LOCK-002-286f244.json --extrait <scratchpad>/refutateur/temoins/temoin-2.md`
  - `EDR-GRAB-COST-1828371` : RETROUVE (code 0, 5 recevables) -- `... --verifier EDR-GRAB-COST-1828371 <scratchpad>/refutateur/critiques-EDR-GRAB-COST-1828371.json --extrait <scratchpad>/refutateur/temoins/temoin-3.md --jugement OUI`
  - `EDR-RETAIN-COMPOSE-4204f8f` : RETROUVE (code 0, 5 recevables) -- `... --verifier EDR-RETAIN-COMPOSE-4204f8f <scratchpad>/refutateur/critiques-EDR-RETAIN-COMPOSE-4204f8f.json --extrait <scratchpad>/refutateur/temoins/temoin-4.md --jugement OUI`
  - (`<scratchpad>` = `C:/Users/robla/AppData/Local/Temp/claude/c--Users-robla-VScode-Project-AGAGI/9ee49c0e-22c7-40f5-84c6-55466533a5d5/scratchpad`)
- **PLANCHER DE FAUSSES RETROUVAILLES (majorant, étage 1 seul, seuil de recopie 8 mots) : 0/5** ; **plancher mesure sur LOCK-002-286f244 : 8 critiques recevables (seuil historique 1)**
- **⚠ INDISCRIMINANT : le record cru sain rend autant de critiques recevables que les defectueux**

Bilan : 42 critiques, **19 confirmées**.

---

## P1

### P1.1
- **Sonde** : `python -c "import json; from tools.jobs.remote import ecarts_hors_volatils as E; d=json.load(open('results/deport_temoin_nexus.json',encoding='utf-8')); s=d['tour_2']['sorties_brutes_texte']; a=s['batcave1'].encode(); b=s['nexus1'].encode(); print(len(E(a,b)), len(E(a,b,volatils=())), len(E(a.replace(b'\n',b'\r\n'),b)))"`
- **Constat** : Prémisse qui porte le verdict final : les quatre sorties du tour 2, lues en octets, ne s'écartent que sur les deux lignes de durée. Mesurée DANS ce run et rejouée : 0 écart sous la règle, 2 sans masque, 572 si l'on réinjecte des CRLF. L'instrument pouvait produire les deux issues. Preuve : sortie 0 / 2 / 572 ; JSON tour_2.comparaisons_regle_declaree = 6×0, controle_sans_volatils = 6×2.
- **Classe** : aucune
- **Verdict** : non confirmé

### P1.2
- **Sonde** : `python -c` (lecture de tour_1.cotes.*.entry_sha256 et debut_utc) ; `git cat-file -e da09f7a1:tools/jobs/remote_entry.py` ; `for c in 7f639e35 def16adc; do git show $c:tools/jobs/remote_entry.py | sha256sum; done`
- **Constat** : L'en-tête affirme que les deux côtés passent par le même chemin (lignes 13-15), sans distinguer les tours. Faux au tour 1 : la référence batcave est passée par un script d'entrée qu'aucun commit ne contient, et a tourné avant que remote.py et remote_entry.py soient committés (7f639e35, 11:32:22 UTC). Le côté nexus a pris une autre version. Le verdict final n'est pas renversé (tour 2 : entrée 28aaf8d1 partout), mais le NON du tour 1 compare deux instruments différents. Preuve : record:13 ; tour_1 batcave entry_sha256 = c136aeff… contre nexus = 09ca2e91… (7f639e35) ; def16adc = 28aaf8d1… ; debut_utc batcave = 11:04:18 UTC ; git cat-file : 'exists on disk, but not in da09f7a1'.
- **Classe** : E8
- **Verdict** : confirmé

### P1.3
- **Sonde** : `python -c` (parcours récursif du JSON, hors sorties_brutes, valeurs dans [60,70], [19,20], [99,5;100] et motifs '64 s|19,6|99,9|Mo') ; `git log -1 --format=%B 28810f52 | grep -oE '[0-9]+ s'`
- **Constat** : Trois chiffres de coût (64 s de bout en bout, 19,6 Mo envoyés, 99,9 % sur 3 s) absents de l'évidence citée. Le « 64 s » vient du message du commit 28810f52 ; aucune source pour les deux autres. Le qualificatif « batcave chargée » s'appuie sur le 99,9 % pour batcave1, alors que le JSON publie 23,8 % au départ de ce réplicat (celui du rapport 1,55). Preuve : parcours 0 correspondance ; record:53 et :59-60 ; tour_2.cotes.batcave1.charge_debut.cpu_pct_systeme_1s = 23.8.
- **Classe** : E8
- **Verdict** : confirmé

### P1.4
- **Sonde** : `python -c` (split b'\n' de sorties_brutes_texte.batcave1 puis ecarts_hors_volatils après injection de CRLF)
- **Constat** : Le compte du tour 1 est donné de trois manières : record 572 sur 572 non volatiles ; lecture JSON 574 sur 574 ; rejeu 572 sur 573 (575 segments, dont une accolade finale sans saut de ligne donc sans CR, 2 volatils). Le « toutes » est faux d'une unité. Réserve : octets bruts du tour 1 non publiés ; le rejeu injecte des CRLF dans le texte du tour 2. Preuve : 'lignes 575 575', 'instrument sur CRLF injecte 572' ; record:31 contre tour_1.lecture = '574 lignes sur 574'.
- **Classe** : aucune
- **Verdict** : confirmé

### P1.5
- **Sonde** : `git show 7f639e35:tools/jobs/remote.py | grep -n '^VOLATILS_DEFAUT'` ; sed de ecarts_hors_volatils à 7f639e35 et def16adc `| md5sum`
- **Constat** : La règle fixée avant nexus est vérifiable : VOLATILS_DEFAUT et le comparateur committés à 11:32:22 UTC, avant le premier run nexus (12:15:34 UTC), inchangés jusqu'à def16adc. Preuve : remote.py:787 = ('elapsed_s',) aux deux commits ; md5 691995f9… identiques.
- **Classe** : aucune
- **Verdict** : non confirmé

### P1.6
- **Sonde** : `grep -n dirty tools/preregister.py ; sed -n 1041,1047p tools/evo_runs/evo011_preflight.py ; git check-ignore -v results/evo011_preflight_smoke.json`
- **Constat** : Le JSON ne publie que dirty = vrai, sans le fichier fautif. L'explication du record (le fichier de résultat) n'est pas mesurée, mais le code la rend cohérente. Preuve : preregister.py:162 ; evo011_preflight.py:1044-1045 ; .gitignore:19 '!results/*.json'.
- **Classe** : aucune
- **Verdict** : non confirmé

### P1.7
- **Sonde** : `git status --short -- <record> results/deport_temoin_nexus.json ; git ls-files --error-unmatch results/deport_temoin_nexus.json`
- **Constat** : Ni le record ni son JSON ne sont suivis : un clone ne peut rouvrir la preuve. Relève de P9 (porte 20). Preuve : '??' pour les deux ; 'did not match any file(s) known to git'.
- **Classe** : E27
- **Verdict** : hors périmètre

## P2 (DÉLÉGUÉ) -- Régime

- **Sonde** : `python tools/check_regime_claims.py --only docs/EDR/DEPORT-NEXUS-TEMOIN_Meme_Seed_Batcave_Contre_Nexus.md` ; `python -c "from tools.check_regime_claims import analyze; ..."` (HEAD def16adc)
- **Constat** : Porte 19 : OK, exit 0. Le record ne cite aucun paramètre du vocabulaire de la porte (SANS_PARAMETRE), rien n'est confronté. Verdict de la porte recopié, enquête non rouverte. Preuve : 'OK : 64 record(s) sans regime concordant [...] Aucun nouveau, aucune regression.' ; 'SANS_PARAMETRE {} ['results/deport_temoin_nexus.json'] []' ; check_regime_claims.py:253-254.
- **Classe** : aucune
- **Verdict** : non confirmé

## P3 (DÉLÉGUÉ) -- Balayage du pas, runner tools/evo_runs/evo011_preflight.py

- **Sonde** : `python tools/check_e19_optimizer_sweep.py --only tools/evo_runs/evo011_preflight.py ; python tools/check_e19_optimizer_sweep.py --report | grep -n evo011`
- **Constat** : Porte E19 : exit 0, runner classé couvert (scellé via verify(), aucune grille de pas). Le record compare deux plateformes au même sha, pas des bras à pas distincts. Verdict recopié. Preuve : HEAD def16adc ; 'OK : aucun nouveau runner sous gradient sans garde E19, aucune régression, aucune perte d'appelant.' ; '[couvert] tools/evo_runs/evo011_preflight.py' ; evo011_preflight.py:927.
- **Classe** : aucune
- **Verdict** : non confirmé

## P4

### P4.1
- **Sonde** : lecture de regime.seeds, ticks_run, agent_ticks dans la sortie brute nexus1 ; `grep -n '^TICKS' tools/evo_runs/evo011_preflight.py`
- **Constat** : La clause « établi » vaut pour toute une classe de runners, alors que la famille comparée compte une cellule indépendante : un runner, seed 0, trois bras, cohortes éteintes entre les ticks 27 et 49 sur 200 prévus (1291 agent-ticks). Les 6 paires du tour 2 viennent de 4 exécutions de cette cellule : au plus 3 comparaisons indépendantes, sur un seul point runner x seed. La généralisation dépasse la mesure. Preuve : regime.seeds=1 ; ticks_run 43/49/27 contre TICKS = 200 (evo011_preflight.py:110) ; 494+516+281 = 1291 ; record:64.
- **Classe** : E9
- **Verdict** : confirmé

### P4.2
- **Sonde** : empreintes sha256 (LF et CRLF) de remote_entry.py à 7f639e35 et def16adc ; lecture entry_sha256 et cpu_mesure par tour et côté
- **Constat** : Les cellules du tour 1 ne sortent pas du même dispositif : empreinte batcave ne correspondant à aucune version committée, nexus = blob de 7f639e35 ; cpu_mesure absent côté batcave, renseigné côté nexus. Le record présente le chemin comme commun. Verdict final non touché (tour 2 : même empreinte partout). Preuve : batcave c136aeff contre nexus 09ca2e91 ; 09ca2e91, 763cdd5c, 28aaf8d1, cd531815 tous différents de c136aeff ; tour_2 : 28aaf8d1 x4 ; record:14.
- **Classe** : E8
- **Verdict** : confirmé

### P4.3
- **Sonde** : `grep -n 'FAMILY_CELLS\|SEALED_SEEDS =' tools/evo_runs/evo011_preflight.py` ; lecture design.control_family dans la sortie nexus1
- **Constat** : La sortie embarque un seuil Bonferroni sur 24 cellules (alpha_cell = 0,00208) hérité du plan à 12 seeds, alors que le smoke produit 2 cellules. Ce seuil sert au verdict propre du runner, jamais à la règle d'identité. Preuve : evo011_preflight.py:140 ; cells = 24, alpha_cell = 0.0020833, regime.seeds = 1.
- **Classe** : E23
- **Verdict** : hors périmètre

### P4.4
- **Sonde** : `git log --format='%h %cI' -S VOLATILS_DEFAUT -- tools/jobs/remote.py ; ls docs/preregistrations | grep -iE 'deport|nexus|temoin'` ; debut_utc du tour_1
- **Constat** : VOLATILS_DEFAUT entre dans l'historique 26 minutes après la paire batcave du tour 1, qui révélait déjà les deux lignes variables. Elle précède le premier run nexus, mais aucune règle scellée ne la fige : le choix avant vue des écarts n'est ni démontré ni réfuté. Preuve : 7f639e35 à 11:32 UTC contre batcave 11:04:18 et 11:05:56, nexus 12:15:34 ; aucune pré-inscription ; remote.py:787.
- **Classe** : E11
- **Verdict** : non confirmé

### P4.5
- **Sonde** : lecture de cpu.threads_poses, os_cpu_count et recherche de num_threads dans le JSON
- **Constat** : Deux chiffres de prose absents de l'évidence : 16 threads torch côté batcave (aucune clé, aucune variable de thread, 22 coeurs logiques) et la pointe de charge 99,9 % (relevés batcave 23,8 à 89,3 %). Relève de P1/P10. Preuve : threads_poses None, os_cpu_count 22, num_threads False ; record:69 et :53.
- **Classe** : E8
- **Verdict** : hors périmètre

## P5 (JUGE)

### P5.1 -- le contrôle pouvait-il échouer ?
- **Sonde** : `python <scratchpad>/p5_sonde.py` ; liste des lignes nexus1 à flottant >= 12 chiffres significatifs ; `grep -n 'assert_positive_control|assert_not_degenerate|assert_ablation_changes_something' tools/jobs/remote.py`
- **Constat** : Le seul contrôle positif du tour 2 porte sur les deux lignes de durée, qui diffèrent par construction : il ne pouvait pas rendre zéro. Aucun contrôle ne montre que les octets non volatils bougent sous une perturbation arithmétique (seed changée, 1 ULP). Sortie surtout faite d'entiers, constantes, NaN et rapports d'entiers : l'identité repose sur au plus 7 flottants continus. Preuve : 0 / 2 écarts (lignes 45, 569) ; 573 lignes non volatiles, 25 à >= 12 chiffres dont 6 rapports d'entiers ; restent 7 valeurs (lignes 97, 193, 274, 391, 402, 509, 520) ; 0 appel aux gardes de experiment_preflight.
- **Classe** : E1
- **Verdict** : confirmé

### P5.2 -- l'instrument pouvait-il échouer sur une ligne mixte ?
- **Sonde** : `R.ecarts_hors_volatils(b'{\n "elapsed_s": 1.4, "r": 0.5\n}', b'{\n "elapsed_s": 1.5, "r": 0.9\n}')` ; `sed -n 500,520p tests/sandbox/test_jobs_remote.py`
- **Constat** : Le comparateur ignore une ligne entière dès que la clé volatile l'ouvre des deux côtés ; toute valeur posée après elle est invisible. Le témoin unitaire annonce couvrir ce cas, mais sa ligne mixte commence par une accolade : le chemin qui excuse la ligne n'est pas exercé. Défaut latent pour ce run (une clé par ligne). Preuve : sortie [] alors que r passe de 0.5 à 0.9 ; remote.py:794, :800 ; test_jobs_remote.py:516.
- **Classe** : E4
- **Verdict** : confirmé

### P5.3 -- les valeurs du contrôle sont-elles rejouables ?
- **Sonde** : `python <scratchpad>/p5_sonde.py` ; `grep -rln controle_sans_volatils --include=*.py . | wc -l ; grep -n controle_sans_volatils results/deport_temoin_nexus.json`
- **Constat** : Sur 7 sorties comparées, seules 2 ont leur texte brut (batcave1, nexus1) ; hashes et comptes 0/2 s'y rejouent. Les 5 autres paires du tour 2, les 3 du tour 1 (572, 574) et la normalisation CRLF->LF a posteriori sont des nombres déclarés ; le script producteur n'existe dans aucun .py. Preuve : textes bruts ['batcave1','nexus1'], tour_1 False ; sha256 True/True ; hits_py=0 contre JSON lignes 200 et 487.
- **Classe** : aucune
- **Verdict** : confirmé

### P5.4 -- les deux côtés sont-ils au même régime ?
- **Sonde** : lecture de tour_2.cotes[*].cpu.threads_poses
- **Constat** : Réglage de threads différent (4 variables à 2 sur nexus, aucune sur batcave), mais une identité obtenue malgré cet écart renforce le verdict. Seul reste invérifié le chiffre de 16 threads torch. Preuve : nexus OMP/OPENBLAS/MKL/NUMEXPR='2' ; batcave None ; os_cpu_count 22.
- **Classe** : aucune
- **Verdict** : non confirmé

### P5.5 -- un bras est-il structurellement plus dur à optimiser ?
- **Sonde** : `grep -n 'assert_ablation_changes_something|assert_not_degenerate' tools/evo_runs/evo011_preflight.py` ; lecture de w_drift et control_failures dans nexus1
- **Constat** : Aucun optimiseur n'intervient (poids gelés, deux machines) : E19 ne s'applique pas. Les gardes du runner ne signalent aucun échec. Preuve : evo011_preflight.py:775, :784 ; w_drift = 0.0 x3 ; control_failures = [].
- **Classe** : aucune
- **Verdict** : hors périmètre

## P6

### P6.1
- **Sonde** : `grep -niE "no.?op" <record> results/deport_temoin_nexus.json` ; max/min des elapsed_s_runner et duree_mur_s par tour
- **Constat** : Le rapport de coût (1,6 à 1,9) paraît sans sa bande de bruit, pourtant calculable : batcave 1,16 à 1,27, nexus 1,002 à 1,005. Le contraste [1,56 ; 1,90] en sort, mais ni le record ni le JSON ne la chiffrent. Preuve : grep 0 ; bruit batcave tour 2 1,164/1,213, tour 1 1,193/1,268 ; nexus 1,0017/1,0053 ; contraste elapsed [1,587 ; 1,850], mur [1,558 ; 1,900] ; record:55.
- **Classe** : aucune
- **Verdict** : confirmé

### P6.2
- **Sonde** : lecture de charge_debut et elapsed_s_runner par côté au tour 2
- **Constat** : Côté Windows, la seule bande vient de deux réplicats à charges très différentes : leur écart de 16 % mesure l'effet de charge. Aucune cellule batcave au repos : le dénominateur du rapport est une unité sous charge. Le record l'avoue sans la mesurer. Preuve : batcave1 23,8 %, 2,213 s ; batcave2 89,3 %, 2,576 s (1,164) ; nexus 2,1/2,3 %, 1,3946/1,3921 s ; record:55-56.
- **Classe** : E12
- **Verdict** : confirmé

### P6.3
- **Sonde** : `grep -noE "\"(OMP_NUM_THREADS|threads_source)\": [^,]*" results/deport_temoin_nexus.json`
- **Constat** : Le no-op intra-côté ne borne pas le contraste croisé : machine, OS, charge et fils BLAS (2 côté nexus via cgroup, défaut bibliothèque sur 22 coeurs côté batcave) changent ensemble. La section coût (lignes 48-60) ne mentionne pas cet écart pour cette cellule numpy, seulement plus bas pour torch. Preuve : JSON:305, :310 contre :367, :372 ; os_cpu_count 22 contre 16.
- **Classe** : aucune
- **Verdict** : confirmé

### P6.4
- **Sonde** : `grep -nE "57[24]" results/deport_temoin_nexus.json <record>`
- **Constat** : La lecture du tour 1 dans le JSON donne comme contraste sous la règle le compte du contrôle sans volatils (574/574), alors que le bloc de la règle rend 572 et le record 572 : contraste et contrôle confondus sous la même étiquette. Preuve : JSON:197-198 = 572 ; :202-203 = 574 ; :210 '574 lignes sur 574' ; record:31.
- **Classe** : aucune
- **Verdict** : confirmé

### P6.5
- **Sonde** : lecture de comparaisons_regle_declaree (tours 1 et 2) et controle_sans_volatils (tour 2)
- **Constat** : Le no-op du verdict d'identité est publié et tient : paires même côté à 0 ; tour 2 croisées à 0 ; tour 1 croisées hors bande (572) ; contrôle positif 2 par paire. Aucun défaut de plancher sur le verdict principal.
- **Classe** : aucune
- **Verdict** : non confirmé

### P6.6 (relève P9)
- **Sonde** : `git status --short -- results/deport_temoin_nexus.json <record> ; git ls-files results/deport_temoin_nexus.json`
- **Constat** : Ni le record ni son évidence ne sont suivis au sha def16adc ; à trancher par la porte 20. Preuve : '??' x2 ; ls-files 0 ligne.
- **Classe** : E27
- **Verdict** : hors périmètre

## P7 (JUGE) -- Dose

### P7.1
- **Sonde** : lecture de regime.freeze et w_drift pour batcave1 et nexus1 ; `grep -n compute_policy_gradient tools/evo_runs/evo011_preflight.py src/worlds/world_1_stoneage.py ; grep -cEi 'freeze|plasticit|gradient|w_drift|apprenti' <record>`
- **Constat** : L'identité n'a été éprouvée que sur un run dont l'unique apprenant numpy est neutralisé (compute_policy_gradient remplacé par une fonction vide sous freeze ; dérive de W = 0,0 partout). Dose = ZÉRO mise à jour, non publiée dans le record, dont la ligne Établi s'étend pourtant à tout runner numpy mono-processus : la mise à jour W <- clip(W+dW), la plus sensible aux arrondis, n'a jamais tourné. Preuve : evo011_preflight.py:377-378 ; world_1_stoneage.py:1782 ; freeze=True, w_drift 0.0 x3 ; grep = 0 (contrôle positif cgroup = 3) ; record:64.
- **Classe** : E9
- **Verdict** : confirmé

### P7.2
- **Sonde** : lecture ticks_run, agent_ticks, alive_end, died_energy, regime.ticks dans nexus1 (même sortie batcave1) ; `sed -n 109,112p tools/evo_runs/evo011_preflight.py`
- **Constat** : Cohorte non constante : les 24 agents de chaque bras meurent d'énergie avant le plafond ; 43/49/27 ticks sur 200 ; 1291 agent-ticks contre 14400 budgétés (9 %). L'identité couvre une trajectoire tronquée par la létalité, où les écarts flottants ont le moins de temps pour s'accumuler ; ni la durée simulée ni l'extinction ne figurent au record. Preuve : 3 x 4800 = 14400 (evo011_preflight.py:112) ; alive_end = 0, died_energy = 24 x3.
- **Classe** : E12
- **Verdict** : confirmé

### P7.3
- **Sonde** : `grep -c INDETERMINE <record>` ; lecture de verdict.verdict dans nexus1
- **Constat** : Le record ne tire aucun nul scientifique du runner ; le verdict interne INDETERMINE-HARNAIS (1 seed) n'est ni cité ni exploité. Rien à départager. Preuve : grep = 0 ; n_seeds = 1 contre 12 scellés (evo011_preflight.py:113).
- **Classe** : aucune
- **Verdict** : hors périmètre

## P8 (JUGE) -- Corps et aliasing

### P8.1 -- volet E26
- **Sonde** : `grep -n "W\[" tools/evo_runs/evo011_preflight.py` ; build_genome + phenotype_of pour les 3 bras ; lecture phenotype_insitu (batcave1, nexus1)
- **Constat** : Le déport ne modifie aucun poids ; le runner écrit en W[4] (arête ou ballast), mais le ballast égalise le corps des trois bras et le phénotype est le même des deux côtés. Pas de confusion par le corps. Preuve : evo011_preflight.py:294-296 ; somme |W[4]| = 18.0 x3 ; phenotype_insitu = (1220.0, 50, 18.2) partout ; mamba_agent.py:77.
- **Classe** : E26
- **Verdict** : non confirmé

### P8.2 -- volet E24
- **Sonde** : `python tools/check_io_overlap.py` ; assert_no_io_overlap(build_genome(a)) pour a dans ARMS
- **Constat** : La porte 17 ne voit que les génomes persistés ; sonde directe : 59 entrées + 108 sorties dans 172 nœuds, 5 cachés, aucun logit n'est l'observation. Preuve : 358 génomes, 10 chevauchants connus, 0 nouveau, EXIT=0 ; retour -5 x3 ; evo011_preflight.py:91-92.
- **Classe** : E24
- **Verdict** : non confirmé

### P8.3 -- volet vue de l'état récurrent
- **Sonde** : `sed -n 430,500p tools/evo_runs/evo011_preflight.py` ; lecture de rows[0].detail.e6 (batcave1, nexus1)
- **Constat** : La sonde E6 prend une copie de l'état, pas une vue ; aucune écriture ne remonte. Grandeurs continues identiques entre machines. Preuve : evo011_preflight.py:441-442 ; gap LECTEUR = 6.996999621391296 des deux côtés, n = 240, sign_agree = 1.0.
- **Classe** : E5
- **Verdict** : non confirmé

### P8.4 -- W jamais réécrit pendant la mesure
- **Sonde** : `grep -n -iE "freeze|compute_policy_gradient" tools/evo_runs/evo011_preflight.py` ; lecture regime.freeze et w_drift dans tour_2
- **Constat** : Le verdict « établi » vaut pour tout runner numpy mono-processus, or le gel remplace la mise à jour de W par une fonction vide : W constant dans les six runs. Le record décrit le runner sans le gel. Le chemin par défaut du monde (accumulation float32 dans W) n'a jamais été confronté entre plateformes. Preuve : evo011_preflight.py:377-378 ; en-tête :51-53 ; freeze = True ; w_drift 0.0 x3 ; record:24-26 contre :64-65.
- **Classe** : E9
- **Verdict** : confirmé

### P8.5 -- citation de ligne périmée (relève de P10)
- **Sonde** : `grep -n "phenotype_" src/agents/mamba_agent.py ; sed -n 30,70p src/agents/mamba_agent.py`
- **Constat** : Le runner et l'outil de phénotype renvoient pour la formule du corps à des lignes de mamba_agent.py qui contiennent aujourd'hui le constructeur. Défaut du runner, pas du record ; à consigner au backlog. Preuve : cité mamba_agent.py:47-50 (evo011_preflight.py:42, :301 ; experiment_preflight.py:488) contre réel :77-80 et :83-88.
- **Classe** : aucune
- **Verdict** : hors périmètre

### P8.6 -- provenance (relève de P9)
- **Sonde** : `git status --short <record> results/deport_temoin_nexus.json ; git ls-files <record> | wc -l`
- **Constat** : Ni le record ni son JSON dans l'index ; à trancher par la porte 20. Preuve : '??' x2 ; ls-files 0 ; HEAD = def16adc.
- **Classe** : E27
- **Verdict** : hors périmètre

## P9 (DÉLÉGUÉ) -- Provenance

### P9.1 -- porte 20
- **Sonde** : `python tools/check_evidence_provenance.py --only docs/EDR/DEPORT-NEXUS-TEMOIN_Meme_Seed_Batcave_Contre_Nexus.md ; git ls-files --error-unmatch results/deport_temoin_nexus.json`
- **Constat** : Porte 20 : ÉCHEC. Le JSON cité est sur disque mais non suivi (non_suivi, NOUVEAU/REGRESSE, hors baseline) : un clone ne pourra pas rouvrir l'évidence. Preuve : 'non suivis : 1', '[NOUVEAU/REGRESSE] ... results/deport_temoin_nexus.json [non_suivi]', EXIT=1 ; ls-files EXIT=1, fichier de 41887 octets ; .gitignore:19 négation.
- **Classe** : E27
- **Verdict** : confirmé

### P9.2 -- sceau de la pré-inscription
- **Sonde** : `python -c "from tools.preregister import verify; print(verify('DEPORT-NEXUS-TEMOIN'))"` ; `grep -rliE 'deport|nexus|evo011_preflight --smoke' docs/preregistrations | wc -l` (contrôle positif BILINEAR)
- **Constat** : Aucun sceau : verify lève FileNotFoundError, aucun fichier de docs/preregistrations ne nomme le déport. L'antériorité de la règle n'est attestée que par la prose et regle_declaree d'un JSON non suivi : une déclaration, pas un sceau. Preuve : FileNotFoundError 'aucune pré-inscription DEPORT-NEXUS-TEMOIN' ; 0/71 contre 17 pour BILINEAR.
- **Classe** : E11
- **Verdict** : confirmé

## P10

### P10.1
- **Sonde** : `sed -n 153,165p tools/preregister.py ; sed -n 60,93p tools/jobs/lease.py ; sed -n 224,267p tools/jobs/remote_entry.py ; time git -c core.autocrlf=false status --porcelain`
- **Constat** : La justification de l'écart de méthode CPU (un seul processus) est fausse : le smoke engendre au moins trois fils git (rev-parse --git-common-dir via le bail kuzu, rev-parse HEAD et status --porcelain via la provenance). RUSAGE_CHILDREN les compte sur nexus ; GetProcessTimes ne voit que le fils direct sur batcave. Écart probablement petit (git status ~0,08 s CPU contre ~1,7-2,5 s) : la conclusion tient à quelques pour cent, l'argument est faux. Preuve : preregister.py:161-162 (appelé depuis evo011_preflight.py:1048) ; lease.py:70 via :92, evo011_preflight.py:956 ; remote_entry.py:231 contre :262 ; record ligne 58 ; git status real 0,193 s, user 0,046 s, sys 0,031 s.
- **Classe** : E33
- **Verdict** : confirmé (justification fausse, conclusion probablement juste ; l'amplitude sur nexus ne se chiffre pas sans relancer)

### P10.2
- **Sonde** : `git show da09f7a1:tools/evo_runs/evo011_preflight.py | sed -n 1040,1044p`
- **Constat** : L'appel cité comme cause du tour 1 n'est pas la ligne du sha du tour 1 : l'argument d'encodage y était déjà. Le mécanisme (mode texte -> CRLF sous Windows) reste exact. Preuve : da09f7a1:evo011_preflight.py:1042 = `with open(out, "w", encoding="utf-8") as fh:` ; le record cite en ligne 33 `open(out, "w")`.
- **Classe** : aucune
- **Verdict** : confirmé (mineur, sans effet sur le verdict)

### P10.3
- **Sonde** : `git ls-tree def16adc -- results/evo011_preflight_smoke.json ; git check-ignore -v runs/leases/x __pycache__/x.pyc results/evo011_preflight_smoke.json ; find . -name MANIFEST.json -path '*deport*'`
- **Constat** : La provenance est bien sale à cause du fichier de sortie : tampon pris après l'ouverture en écriture, fichier ni suivi ni ignoré ; les autres écritures (bail, __pycache__) sont ignorées. Limite : MANIFEST des runs introuvables. Preuve : ls-tree vide ; .gitignore:19, :84, :2 ; evo011_preflight.py:1044 précède :1048 ; 0 MANIFEST.
- **Classe** : aucune
- **Verdict** : non confirmé

### P10.4
- **Sonde** : `python -c "import sys; import tools.evo_runs.evo011_preflight; import tools.evo_memory_inworld, src.seed_ai.persistence, src.seed_ai.rl_evolution, src.seed_ai.mutation; print('torch' in sys.modules)"` ; `sed -n 123,142p tools/jobs/remote.py ; sed -n 818,838p tools/jobs/remote.py`
- **Constat** : Deux mécanismes tiennent : les imports de run_arm ne chargent pas torch ; la source part des deux côtés en dépôt superficiel sans conversion de fin de ligne (arbre batcave en LF), executer et local partageant preparer_source et remote_entry. Réserve : imports seulement, pas d'import tardif pendant la simulation. Preuve : False ; remote.py:133, :690, :821.
- **Classe** : aucune
- **Verdict** : non confirmé

### P10.5
- **Sonde** : `sed -n 272,296p tools/jobs/remote_entry.py ; grep -c '2025\.0\|get_num_threads' results/deport_temoin_nexus.json` (motif validé : OMP_NUM_THREADS = 4)
- **Constat** : Le code permet de déclarer les threads (source declare, rien posé d'office) ; tour 2 cohérent (cgroup/2 côté pod, défaut bibliothèque côté batcave). Mais les 16 threads torch et la version MKL citée ne figurent pas dans le JSON : ils viennent du message de commit. Relève de P1/P2. Preuve : remote_entry.py:285-286 ; grep 0.
- **Classe** : aucune
- **Verdict** : hors périmètre (prémisse non publiée : P1/P2)
