# AGAGI — instructions projet

## Backlog

**`docs/roadmap/PRIORITES_ET_DETTES.md`** — backlog ACTIONNABLE priorisé (méthodologie, dettes,
science),
P0→P4. Le consulter avant de choisir quoi faire ; y inscrire toute nouvelle dette.

## Protocole expérimental (obligatoire avant tout run coûteux)

Ce dépôt fait de la recherche empirique : la plupart des conclusions viennent de runs longs et
irréversibles. **Avant de lancer un run, passer le pré-vol** — `tools/experiment_preflight.py`,
documenté dans `docs/REF/REF-EXPERIMENT-PREFLIGHT.md`.

Quatre questions, dont deux ont des assertions exécutables :

1. **L'instrument peut-il produire LES DEUX issues ?** Un contrôle qui ne peut pas échouer, ou un bras
   qui ne peut pas réussir, ne prouve rien. → `assert_ablation_changes_something`,
   `assert_positive_control`, `assert_not_degenerate`, `assert_selection_nonempty`
2. **La grandeur mesurée est-elle celle qui agit ?** ⚠️ Et le CHEMIN qu'on croit couper est-il le seul ? Mesuré le 2026-09-08 : le **champion HoF** déclare 64 entrées + 126 sorties dans **172 nœuds** — ses blocs d'entrée et de sortie se chevauchent sur **18**, donc 18 de ses logits d'action SONT l'observation, sans traverser un poids. Annuler `W[:num_inputs, :]` ne l'aveugle pas : on ne supprime pas un chemin d'IDENTITÉ en annulant des poids. `max_H` devient négatif **en silence** ; `assert_no_io_overlap` le chiffre désormais (classe E24). → `assert_no_aliasing` (⚠️ `forward` renvoie des
   VUES de l'état : écrire dans une sortie mute l'état récurrent), `assert_predictor_measured_in_situ`
3. **Quelle est l'unité de réplication ?** Dans ce dépôt c'est l'**ère/le seed**, pas l'agent — les
   agents d'un seed partagent entraînement, optimiseur et monde. → `declare_design`
4. **Est-ce que je raisonne au lieu de mesurer ?** Réduire le n, **jamais** supprimer le maillon : une
   chaîne causale transporte son signe, pas son amplitude. → `declare_design`

## Calibration des instruments — **DETTE CLOSE le 2026-09-01** (104/105, baseline à zéro)

**Inventaire au 2026-09-01 : 105 détectés, 104 calibrés, 1 déclaré non-instrument, ZÉRO dette.**
**État COURANT, recomputé et jamais recopié :**
**241 détectés** <!-- count:instruments_detectes=241 -->
· **233 calibrés** <!-- count:instruments_calibres=233 -->
· **2 non calibrés** <!-- count:instruments_non_calibres=2 -->
— la famille `run_*` (72 fonctions) est entrée le 2026-09-06 sans créer de dette. *(Les chiffres datés ci-dessus sont HISTORIQUES : ils restent vrais
et ne sont donc pas balisés.)*
*(Point de départ, 2026-07-21 : 71 détectés, 1 calibré.)* Le cliquet est désormais un **cliquet
strict** : tout NOUVEL instrument non calibré bloque le commit ; sa baseline, vide du 2026-09-01 au
2026-09-15, gèle depuis P2.62 **3 dettes NOMMÉES** (`compute_policy_gradient` legacy = P3.4, `learn` legacy,
`learn_episode_bptt`) — les apprenants sont entrés au périmètre (motifs `learn*` tolérants à l'INDENTATION :
tous les motifs précédents étaient ancrés `^def`, or les apprenants sont des MÉTHODES — 5ᵉ axe de
faillibilité de l'heuristique, la PROFONDEUR).

⚠️ **Ce que la fermeture a appris, et qui vaut plus que le compte.** Sur ~40 instruments
examinés, une trentaine de défauts réels — et la direction est **CONSTANTE** : des données
absentes ou incomplètes ne produisaient pas « inconnu » mais une **affirmation NÉGATIVE de
fond** (`PAS DE RUNG`, `AUTEL MORT`, `N_EMERGE_PAS`, `[1] SUBSTRAT-LIMITE`…). Dans un dépôt dont
la plupart des résultats SONT négatifs, un négatif fabriqué ressemble à tous les autres.
**Trois formes à chercher en priorité** : (a) entrée vide → verdict de fond ; (b) le `nan`
DÉTECTÉ puis avalé dans une branche `else` (l'instrument SAIT et ne le dit pas) ; (c) `zip` /
`min` / `[-1]` qui TRONQUE en silence — un « BARREAU TROUVÉ » y devenait « PAS DE RUNG ».

**Deux techniques qui rendent la calibration presque gratuite :**
* **Garde EN TÊTE de fonction, avant la construction du monde** — une vingtaine de cas passent
  de « quelques secondes chacun » à ZÉRO simulation. Tester non pas QUE la garde lève mais **OÙ**
  elle est posée (un refus doit être instantané).
* **Injection pour les ORCHESTRATEURS** — 13 des 24 « instruments de monde » ne simulaient pas
  eux-mêmes : leur imposer une mesure factice à DOSE CONNUE teste la couche qui transforme des
  mesures en affirmation (agrégation, appariement, unité de réplication), à coût nul.

⚠️ **Le cliquet est faillible sur QUATRE axes, tous mesurés** : ce qu'il cherche (motif), OÙ il
cherche (périmètre), comment il IDENTIFIE (collisions de noms — 8 définitions invisibles), et
sous quels VERBES (`classify_*`). Chaque élargissement a révélé de la dette RÉELLE : ne pas
tenir le compteur pour acquis. Il refusait aussi **en silence** une déclaration ambiguë ; il
crie désormais. Un « instrument » = une fonction qui
produit une affirmation scientifique (verdict, ratio, survie, taux). 70 d'entre eux n'ont jamais été
confrontés à une réponse connue — et un instrument non calibré ne se contente pas d'échouer, il
**PRODUIT un résultat** : le bug d'aliasing d'EDR-WARM-007 a généré dose-réponse, corrélations et
contrôle négatif cohérents, qui ont tenu une passe entière.

- **Calibrer sur vérité-terrain** : `tools/ground_truth_worlds.py` — un monde jouet dont la réponse est
  connue. Préférer la calibration **par PRÉDICTION** (identifier les nuisances en un point, prédire en un
  autre) à la valeur absolue : remplacer `_resolve_biology` ne contrôle PAS le bilan énergétique (la
  phase `action` pèse 5× plus), et l'étalon s'est trompé avant l'instrument.
- **Trois formes de test** : no-op EXACT (spécificité) · prédiction (linéarité en la dose imposée) ·
  monotonie (direction). Cf. `tests/sandbox/test_instrument_calibration.py`.
- ⚠️ **Le no-op EXACT vaut aussi pour l'INSTRUMENT LUI-MÊME, pas seulement pour ses tests** — et son
  résultat est un **PLANCHER DE BRUIT à publier à côté de chaque ratio**. Mesuré le 2026-09-08 :
  `run_ablation_map` (qui porte les verdicts `PERCEPTION_DEMANDED`/`DECOY` de S2-002/003 et d'EDR-124)
  rend **1,058 et 0,922** sur un no-op où *aucune observation n'a changé* — l'ablation consomme des
  tirages du flux global (`derange_rows`, boucle de rejet) et DÉSYNCHRONISE la bande RNG. Le
  commentaire « tape intra-ère non identique » existait depuis le début ; personne ne l'avait CHIFFRÉ.
  Le champion publié est à **0,991**, donc DEDANS. Conséquences opératoires : (a) un contraste dont le
  ratio est dans la bande du no-op n'est pas distinguable de zéro — le dire dans le record ;
  (b) apparier la BANDE (faire consommer les mêmes tirages au bras de référence) divise ce bruit par
  6 ; (c) `noop_control=True` est disponible sur `run_ablation_map`. Un instrument de contraste sans
  plancher de bruit mesuré ne sait pas ce qu'il ne peut pas voir.
- **Cliquet** : `tools/check_instrument_calibration.py` — dette légataire gelée, **aucun NOUVEL
  instrument non calibré**. ⚠️ **Il vérifie qu'une DÉCLARATION existe, jamais que ses cas
  PASSENT** — et jusqu'au 2026-09-09 rien ne les exécutait : **1937 tests sur 2059 (94 %) n'étaient
  lancés par aucun job de CI** (`ci.yml` prenait une liste NOMMÉE de 16 fichiers, jamais un
  répertoire). **CLOS le 2026-09-09** : le job `suite-complete` lance `tests/` PAR RÉPERTOIRE.
  Coût mesuré sur machine à charge connue, et il inverse la décision qu'on croyait tranchée :
  **2597 passés, 0 rouge, 25 min 44 s** — la mesure ayant été prise PENDANT le harnais de mutation,
  c'est un MAJORANT. Les six rouges légataires trouvés en branchant sont corrigés (trois fixtures
  d'AGI-Taxonomy périmées par deux durcissements de la porte, un test exigeant `N_EMERGE_PAS` sur
  ZÉRO seed — un négatif FABRIQUÉ gelé par le test censé l'attraper —, et deux contrats changés la
  veille dont personne n'a su qu'ils rougissaient).
  La suite `tests/sandbox/` lancée en entier ce jour-là a rendu **18 rouges pré-existants**, dont huit
  d'une seule garde de puissance jamais rétro-appliquée (E14) et un qui exigeait qu'une cohorte VIDE
  rende `AUTEL_MORT`. Un compteur d'instruments « calibrés » n'a de sens que si ses cas TOURNENT ;
  la suite complète coûte **30 min** sur machine au repos, donc la CI PEUT la lancer — ⚠️ une première mesure avait donné 8 h 30, prise pendant que seize agents tournaient sur la même machine : **un chiffre de coût se mesure sur une machine dont on connaît la charge**, sinon c'est la classe E12 appliquée au coût, et ici elle inversait la décision. Même mécanisme que `check_record_links.py`.
- ⚠️ **L'APPRENANT est un instrument : sa DOSE se publie à côté de tout nul, et il a un contrôle
  positif.** Mesuré le 2026-09-14 ([[EDR-CALIB-LEARNER]], P1.6) : trois records disaient « le crédit
  in-world n'apprend pas à froid » sans compter la dose reçue — quelques dizaines de mises à jour avant
  la mort à 7-9 ticks. À dose non bornée (cohorte IMMORTELLE, ≈ 2000 TD + 250 épisodes par agent),
  l'apprenant tel que publié apprend la tâche linéaire de S2-011, **12/12 seeds** au-dessus de la
  référence lr=0 appariée (+0,156) — lentement (0,28 vs oracle 1,0), et l'écart résiduel est
  **invariant au pas** (garde E19). Outils : `tools/learning_events.py::count_learning_events`
  (compteur en context manager, bit-identique par défaut, variantes `td_enabled` / `reward_scale` /
  `lr`), `run_learner_probe` + `learner_verdict` (barre = référence lr=0 du MÊME dispositif + 0,05,
  jamais « chance + marge »). Deux leçons de méthode payées sur ce run : (a) **immortel veut dire
  immortel** — une recharge d'énergie seule laissait les bras APPRENANTS perdre la moitié de leur
  cohorte dès le premier bloc (le monde tue DANS le tick : projectile d'un pair, riposte du gibier) et
  tout l'avantage apparent des variantes (×0,05 : 0,39 → 0,26 à cohorte complète) était un **biais de
  survivants corrélé au bras** ; publier `n_agents` par bloc et `resurrections` ; (b) un apprenant
  **meurt ~100× plus** qu'un non-apprenant (126 résurrections par seed contre 1) — dans le monde mortel,
  sa dose est bornée par sa propre létalité, et une DV de survie confond « apprend » et « meurt en
  apprenant ».
- **Auto-amélioration** : tout bug d'instrument trouvé en revue **devient un cas de calibration**. La
  suite croît de façon monotone ; un bug corrigé ne peut plus repasser silencieusement.
- Le monde expose `trace_energy_sinks` (EDR-099/100) : l'utiliser pour diagnostiquer un bilan
  énergétique plutôt que de raisonner sur les sources.

## Registre des erreurs (rituel obligatoire)

**`docs/REF/REGISTRE_ERREURS.md`** — toute erreur trouvée en revue, tout run nul ou contaminé, doit y
atterrir : rattachée à une classe (ou en créant une), avec un statut de garde `exécutable` /
`documenté` / `non automatisable`. Si `exécutable`, la garde est écrite ET testée dans la même passe.
Une erreur qui repasse deux fois en `documenté` est **promue** ou reclassée — pas de troisième fois.

C'est le pendant, pour les classes d'erreur, du cliquet de calibration pour les instruments. Sans lui,
la même erreur revient : elle est revenue **3 fois** sur l'arc WARM, dont une dans le record qui la
dénonçait.

## Consigner en PASSANT (règle permanente)

**Toute lacune, tout défaut, toute occasion d'automatiser vue en chemin s'écrit AU MOMENT où on la voit**
— même (surtout) quand on faisait autre chose. Ne pas attendre qu'on la demande, ne pas la garder « pour
plus tard » : plus tard, elle est perdue, et elle recoûtera le prix fort.

Justification mesurée (session du 2026-09-01, tout trouvé **en passant**) : douze péremptions du backlog,
dont une direction déjà tranchée par un record et présentée comme « à faire » ; un **faux vert** de
cliquet lu contre une baseline élargie ; une récidive d'E14 dont la conséquence était **encore publiée**
(`sign_p` calculé puis jeté, deux lignes adjacentes de NAS.md appliquant le même critère de façon
inconstante). Aucune n'était l'objet de la tâche en cours.

**Où consigner, selon la nature :**

| ce qu'on voit | où ça va |
|---|---|
| classe d'erreur (méthodologique, reproductible) | `docs/REF/REGISTRE_ERREURS.md` + sa garde, **dans la même passe** |
| instrument non calibré / mal calibré | cas dans `tests/sandbox/test_instrument_calibration.py` + `CALIBRATED` |
| dette actionnable, gap, angle mort | `docs/roadmap/PRIORITES_ET_DETTES.md`, avec la PREUVE (`fichier:ligne` ou sortie de commande) |
| règle qu'on vient d'apprendre | ici, dans ce fichier |

**Le critère qui décide s'il faut automatiser** : est-ce que ça peut se **reformer silencieusement** ? Si
oui, une note ne suffit pas — il faut un cliquet (baseline gelée + hook + garde de la garde), sur le
modèle de `check_record_links.py`. Une règle documentée sans application exécutable est violée : c'est la
classe **E10**, et elle a récidivé plusieurs fois.

⚠️ **Un cliquet doit pouvoir ÉCHOUER, et se calibrer comme un instrument.** Écrire son contre-exemple
gelé dans la même passe, et le confronter à une réponse connue avant de le croire : les deux cliquets
livrés le 2026-09-01 ont rendu **5 puis 2 faux positifs** avant d'être corrigés. Un outil de vérification
non calibré ne se contente pas d'échouer — il **produit** un verdict, exactement comme un instrument.

**Ne pas proxifier ce qu'on ne sait pas mesurer.** Quand une propriété n'est pas décidable (« ce test
discrimine-t-il ? », « ce plancher est-il un plancher ? »), la règle est de faire **DÉCLARER** l'auteur
plutôt que de deviner. Cf. `tools/demand_marker._degeneracy` et `tools/check_guard_negative_cases.py`.

## Cliquets en place

`check_record_links.py` (graphe de records) · `check_instrument_calibration.py` (calibration) ·
`check_preregistration_applied.py` (DV scellée mesurée) · `check_guard_negative_cases.py` (toute garde
`exécutable` nomme son contre-exemple) · `check_backlog_freshness.py` (liens morts, numéros dupliqués,
chemins disparus — **et péremption SÉMANTIQUE par clause DÉCLARÉE** `<!-- closes_when:pred=arg -->` :
vocabulaire fermé, prédicats PURS, les deux sens vérifiés — dont « l'entrée s'annonce CLOSE mais sa
condition ne l'est plus », qui attrape une fermeture régressée en silence ; les entrées SANS clause
sont hors périmètre et RAPPORTÉES, jamais comptées comme un succès) · `check_agi_taxonomy.py` (preuve complète d'une arête) ·
`check_synthesis_counts.py` (tout compte publié se recompute) · `check_substrate_pinning.py` ·
`check_bar_separation.py` (toute barre de verdict `chance + marge` confrontée au PLAFOND DE
L'INCAPABLE — P2.15 : `1/K+0.15` était franchie par un substrat qui n'avait pas appris la tâche ; le
« prouvablement incapable » de l'époque est rétracté depuis le 2026-09-08 — le plafond du plain est 0,944 MINORANT) ·
`check_test_census.py` (un test qui DISPARAÎT rend la suite plus verte — aucun signal habituel ne
peut alerter ; porte 10, session parallèle) ·
`check_data_paths.py` (aucun NOUVEAU chemin de données écrit en dur — inventaire : 57 littéraux
dans 26 fichiers et UNE seule variable d'environnement, donc héberger les données sur un NAS
demandait d'éditer 26 fichiers ; `src/paths.py` porte l'indirection, porte 12) ·
`check_fabricated_defaults.py` (aucune NOUVELLE agrégation ne rend une CONSTANTE sur une
collection vide — porte 14 : `float(np.median(ages)) if ages else 0.0` rend une cohorte VIDE
indiscernable d'une cohorte qui a survécu 0 tick ; **121 sites légataires** gelés, dont un défaut à
**1.0 sur un RATIO** où l'absence prend exactement la valeur du résultat nul. `None` et `nan` sont
acceptés : ils DISENT « je ne sais pas ») ·
`check_control_family.py` (tout runner d'une règle SCELLÉE déclare son design, donc le NOMBRE de
cellules de sa famille de contrôles — porte 11 ; à seuil de test unique, une famille de 24 cellules
donnait 0,216 de fausse alarme sur un harnais PARFAIT) ·
`check_gate_mutation.py` (**le cliquet DES cliquets**, porte 15 — chaque porte est cassée d'UNE
ligne, EN MÉMOIRE (l'arbre est partagé : jamais sur disque), et au moins un témoin doit ROUGIR.
C'est la mesure que deux cliquets déclaraient impossible : « ce test discrimine-t-il ? […]
demanderait du test de mutation ». Elle ne l'était pas — elle n'avait pas été faite. Livraison :
13 portes, 16 mutations, **quatre défauts réels du premier tir** — les verdicts `orphans` (porte 1),
`scan_collisions` (porte 2) et le report de la porte 6 n'avaient **aucun** contre-exemple, et un test
de la porte 14 PUNISSAIT son propre correctif. ⚠️ Un contrôle INTACT précède chaque mutation :
sans lui, des témoins déjà rouges « tueraient » tous les mutants et le harnais annoncerait une
couverture parfaite en ne mesurant rien).
`check_amputation.py` (porte 16 — **E22 généralisée au MÉCANISME**. Le dépôt répondait déjà à deux
de ses trois occurrences, mais par des cliquets liés à UN artefact : la porte 10 compte les TESTS,
la porte 4 les entrées du BACKLOG. Le mécanisme, lui, est indifférent au fichier qu'il détruit — le
même accident sur `tools/ablation.py`, sur un record ou sur une baseline JSON n'était couvert par
RIEN. BLOQUE l'**anéantissement** : un fichier encore présent dont le compte d'ENTITÉ tombe à zéro
alors que HEAD en portait. SIGNALE, sans bloquer, toute baisse partielle — retirer du code mort est
légitime, et ce qui manquait n'était pas un refus mais **le chiffre sous les yeux** : c'est en lisant
« 2372 deletions » par réflexe que l'anéantissement du backlog a été découvert).
`check_io_overlap.py` (porte 17 — **E24 au dépôt de génomes** : aucun NOUVEAU génome persisté dont les
blocs d'entrée et de sortie se chevauchent. `assert_no_io_overlap` protège les SONDES ; rien ne protégeait
les 348 `.npz` de `data/genomes/` ni les Hall of Fame. Coût nul — trois entiers par fichier, 378 sujets en
0,5 s ; les 10 entrées du HoF principal (64 + 126 dans 172 = 18, une seule lignée) sont gelées, les deux HoF
famine et les 348 `.npz` sont à 0. Un fichier illisible est RAPPORTÉ, jamais compté 0 ; deux mutations
tuées par ses témoins).
`check_calibration_reach.py` (porte 18 — **PORTÉE de la calibration, cliquet strict à baseline VIDE**. La porte 2
vérifie qu'une DÉCLARATION existe ; celle-ci vérifie qu'un test **IMPORTE et APPELLE** le symbole quand tous les cas
déclarés sont des gardes d'entrée (« garde-seule ») : sinon le corps n'a jamais rencontré une réponse connue, et la
certification ne porte que sur le refus d'un argument dégénéré. Les 31 muettes légataires sont résorbées par injection
(P2.56, 0 monde réel) → **baseline VIDE**, toute NOUVELLE muette bloque. Elle juge l'**INDEX** (`--index`), pas le
disque, comme la porte 4 durcie. ⚠️ Elle s'est prise en défaut elle-même (**E4 occ. 9**) : un appel sous
`pytest.raises` était compté comme une ATTEINTE du corps, donc six déclarations passaient pour calibrées par leur seul
test de garde — la baseline avait été gelée sur cette mesure avant d'être confrontée à un cas connu).
`check_hook_deployment.py` (porte 22, P2.108 — **la copie DÉPLOYÉE contre la version RELUE**. `.git/hooks/`
n'est pas versionné : les crochets y sont recopiés à la main, et entre les deux rien ne tenait. ⚠️
`core.hooksPath` vaut ici un chemin **ABSOLU** vers le `.git/hooks` du dépôt principal, donc **tous les
worktrees exécutent le MÊME fichier** : y écrire arme la flotte entière. Les deux sens sont des occurrences
RÉELLES et ils n'ont pas le même remède, donc pas la même sanction — une copie **en retard** (un `cp` oublié,
contenu déjà committé) CRIE avec la commande exacte sans bloquer, parce que le commit qui met à jour un crochet
est dans cet état par construction ; une copie **en avance** (du code qui n'existe dans AUCUN commit, écrit dans
le crochet commun par un worktree — mesuré par le PM, il bloquait chaque session qui committait un record)
REFUSE. La référence est l'**INDEX**, jamais le disque : l'arbre est partagé. ⚠️ Elle ne peut PAS voir sa
propre absence — elle est lancée PAR le pre-commit déployé ; celle de tout AUTRE crochet, si, et c'est elle qui
compte, un `commit-msg` manquant rouvrant le trou de la fusion).
**20 gardes** <!-- count:portes_hook=20 --> sont branchées sur le hook pre-commit
(`tools/hooks/pre-commit`) — compte RECOMPUTÉ depuis le hook lui-même : la phrase « 5 cliquets, tous
branchés » qui vivait ici était fausse.
⚠️ **La baseline d'un cliquet doit elle-même déclencher le hook** — sinon l'élargir et la committer seule
ne vérifie rien (faux vert mesuré le 2026-09-01, classe E4 occ. 5).

## Revue adversariale
Toute conclusion destinée au graphe de records passe par une **revue qui lance ses propres sondes**,
pas une relecture. Bilan mesuré sur l'arc WARM-005→009 : **7 revues, 7 erreurs réelles trouvées** —
aucune n'aurait été attrapée par de la prudence rédactionnelle.

## Coût des runs
Le pipeline est lent et **le coût suit le succès** (quand la survie augmente, les épisodes s'allongent
et tout ralentit). Trois runs ont déjà été abandonnés (8 h, 4 h projetées, 89 min). Borner le coût
DANS le design : plafonner `max_ticks` pour les traces, réserver le n complet au verdict final,
**persister les génomes entraînés** (les avoir perdus a coûté un réentraînement complet).
Mesurer le débit sur un smoke avant d'engager un run long — mais ne pas extrapoler une tendance depuis
un préfixe court (un transitoire d'apprentissage y ressemble).
⚠️ **Une unité de coût mesurée SOUS CHARGE n'est pas une unité — payé trois fois le 2026-09-22.** La
garde E13 projette le coût d'un run depuis UNE cellule mesurée ; si cette cellule tourne pendant qu'un
autre job occupe la machine, la projection est fausse et la garde COUPE ou ABANDONNE sur un chiffre qui
ne décrit pas le run : b0 (P4.17, 217 s par cellule au lieu de 75-90 s → deux lignes de grille coupées),
d7 (P4.16, 815 s contre 283 s en P4.8 pour la MÊME cellule bit-identique), c9 (cellule A du harnais
`INCONCLUSIVE_N` par abandons sous neuf processus python). C'est E12 appliqué au coût — la classe qui
avait déjà inversé une décision de CI (8 h 30 mesurées sous seize agents, 30 min au repos). Règles :
**un seul run lourd à la fois** sur la machine ; **une vague de commits COMPTE comme un run lourd** (la
porte 15 lance un `pytest` par mutation) ; noter la charge au départ de chaque cellule
(`python -m tools.jobs.doctor`, lecture seule) ; publier l'unité LIBRE et l'unité SOUS CHARGE, la charge
se mesurant par la réplication d'une cellule bit-identique ; en cas de coupe, une REPRISE déclarée à unité
re-mesurée machine libre et même budget scellé (jamais relever la marge) ; des abandons qui persistent
sous marge explicite se GRAVENT comme E12, ils ne se relancent pas.
⚠️ **Et la charge ne fausse pas que les COÛTS : elle fausse les GARDE-TEMPS, et le faux rouge qu'elle produit est indiscernable d'un vrai blocage.** Mesuré le 2026-09-24 : `tests/sandbox/test_hook_on_merge.py` a dépassé le garde-temps de 300 s sur UN cas ; reproduit hors pytest, le même dispositif rend la main en **4,1 s**. Dans le dépôt jouet, un `git commit` trivial prenait **6 à 10 s** au lieu de moins d'une seconde, CPU à 100 % et **ZÉRO processus python du projet** (`doctor` : 0 bail, 0 processus) — la charge venait d'ailleurs. Quarante minutes perdues à chercher une boucle infinie qui n'existait pas. ⚠️ **La cause est INFÉRÉE, pas établie** : le blocage ne s'est PAS reproduit à la passe suivante (21 cas comportementaux verts en 478 s, CE cas compris, garde-temps 600 s), et l'expérience contrôlée — même cas, charge mesurée à deux niveaux — n'a pas été faite. Un second mécanisme produit exactement le même symptôme (paragraphe suivant) ; il est écarté ICI par la pile — l'appel bloqué était `sh sonde.sh`, pas pytest. Règle : devant un test qui dépasse son garde-temps, **reproduire le dispositif HORS du harnais avant de diagnostiquer une boucle**, **lire la pile** du garde-temps pour savoir QUEL appel attend ; et noter la charge, `doctor` seul ne la voit pas puisqu'il ne compte que les processus du projet.
⚠️ **Et un faux blocage sous pytest peut venir de pytest lui-même.** Mesuré le 2026-09-24 par une session voisine (`agagi-e4`) : un témoin qui lance pytest sur un fichier placé dans `tmp_path` a bloqué **plus de 180 s** ; pile `faulthandler` : `Session.collect` crée un nœud `Dir` pour chaque entrée en remontant vers la racine, et `C:\Users\robla\AppData\Local\Temp` en compte **30 407**. Un `pytest.ini` posé à côté du fichier ramène la collecte à **0,25 s**. Même symptôme que la charge — bloqué sous pytest, rien hors pytest — et cause entièrement différente. Règle : tout test qui lance pytest sur un fichier de `tmp_path` pose un `pytest.ini` à côté ; et devant un dépassement, **distinguer les deux causes avant d'en retenir une** — la pile dit si le blocage est dans la collecte ou dans le dispositif. Deux causes, un symptôme, et la pile qui les sépare.

## Records
Nouveau record → frontmatter `gate:` / `tests:[SDR-Gx]` / `adopts:` ou `foundational`, sinon
`tools/check_record_links.py` le signale comme orphelin (le hook pre-commit bloque les nouveaux).
Les résultats NÉGATIFS et les auto-réfutations se gravent au même titre que les positifs.

⚠️ **Avant de BANDER un record, lire ce record — et valider le motif DEDANS.** Mesuré le 2026-09-24
(**récidive** de la règle du grep ci-dessous, écrite le 2026-09-07) : j'ai cherché `industrial` dans le CODE et
dans l'OUTILLAGE, j'y ai trouvé une seule note, et j'allais publier comme inédit (« la carte ne l'a jamais
tiré », avec une classe E10 à la clé) un fait que **les deux records visés portaient déjà** —
`EDR-S2-002` ligne 15 (bandeau « COMPTE DES MONDES CORRIGÉ ») et `EDR-S2-013` dans ses réserves. Rétracté avant
publication, et une session voisine était à un pas de graver la classe sur ma formulation. Le périmètre est la
variante neuve : *valider le motif sur un cas positif connu* ne suffit pas si on le valide sur le MAUVAIS
corpus. Règle opératoire, déclarative faute d'être automatisable : **un record qu'on cite se lit, et le motif se
grep dans CE fichier** ; un bandeau qui annonce une nouveauté nomme ce qu'il a lu pour l'affirmer. *(Même passe,
même mécanisme, deuxième fois : mon `grep "occ. 9, 2026-09-23"` a rendu 0 sur une ligne que j'avais moi-même
écrite et committée — le motif exact était « (9, 2026-09-23, … ». Une absence de correspondance n'est pas une
absence.)*

⚠️ **Une PRÉMISSE est une mesure, pas un décor.** Toute valeur de configuration citée dans un record
doit être PUBLIÉE par le runner (bloc `regime` du JSON de résultats), jamais recopiée de mémoire.
Mesuré le 2026-09-09 (**E8 occ. 4**) : `EDR-GRAB-COST` s'ouvrait sur « le régime porte
`forage_payoff = 3.0` » alors que (a) `run_condition` construit avec `config=None`, donc le défaut
**1.0**, (b) ce paramètre ne multiplie que la récompense de mise à mort — il ne touche **jamais**
l'action ablatée, et (c) le fait annoncé (« grabber nourrit ») était mesurable et **faux**. La garde
E8 existante ne pouvait rien voir : `declare_design(links=…)` couvre les liens CAUSAUX inférés, pas la
description du RÉGIME. Balayage de la forme : **56 affirmations de paramètre** dans la prose des
records, aucune vérifiable avant ce bloc.

## Jobs & ressources exclusives

**`tools/jobs/`** — bail sur ressource NOMMÉE, run gouverné, doctor. Toute simulation de monde doit
tenir la ressource `kuzu` :

    from tools.jobs.run import hold, run
    with hold("kuzu", owner="mon-job"): ...        # une autre sim lève ResourceBusy
    run("nom", cmd, resources=["kuzu"], timeout_s=3600)   # timeout -> kill de l'ARBRE

Pourquoi : deux sondes monde concurrentes se disputent le lock KuzuDB -> **mesure silencieusement
contaminée** (mesuré le 2026-07-21) + suite de tests en timeout. Le bail rend ça *impossible* au lieu de
déconseillé. Ressources distinctes ne se bloquent PAS entre elles (un cap global à 1 sérialiserait des
jobs indépendants). Crash-recoverable : TTL + heartbeat + identité PID/`create_time`.

`python -m tools.jobs.doctor` — état des bails et des processus. **Lecture seule par défaut** ; `--kill`
explicite, jamais le processus courant ni ses ancêtres, jamais un bail dont le détenteur est vivant.
⚠️ `tools/sim_session.py` est DÉPRÉCIÉ au profit de ce module.

## Environnement
- Arbre de travail **partagé entre sessions parallèles** → commits path-scoped obligatoires.
- ⚠️ **Une CITATION et son ARTEFACT partent dans le MÊME commit — stager ne suffit pas.** Mesuré le
  2026-09-22, sur trois sessions bloquées coup sur coup : un `git commit -- <chemins>` (et la méthode
  d'index temporaire `git read-tree HEAD` + `git add`) construit un index qui contient **HEAD plus les
  chemins du commit, rien d'autre** — vérifié : un fichier stagé par une AUTRE session y rend `0`
  occurrence à `git ls-files` alors que l'index partagé le voit. Donc un fichier cité (clause
  `closes_when:path_present`, ou simple citation en prose depuis le durcissement de la porte 4) et
  seulement STAGÉ reste « non suivi » pour la porte, qui a raison : elle juge ce qu'un CLONE verra
  après CE commit. ⚠️ La conséquence en chaîne qui a bloqué TROIS sessions le même soir : la porte lisait
  le backlog et les fichiers cibles des clauses SUR DISQUE — où traînent les hunks en vol de tout le
  monde — et les jugeait contre l'index TEMPORAIRE du commit ; le travail non committé de B rendait rouge
  le commit de A (chemins « non suivis », clause de P2.66 « satisfaite » par une fonction écrite sur disque
  par une autre session), et la porte 15 refusait alors tout commit touchant une porte. **Corrigé le jour
  même** : sous `GIT_INDEX_FILE`, la porte 4 lit le texte du backlog, l'existence des chemins ET le contenu
  des cibles `grep_*` depuis l'INDEX — elle juge exactement ce qui sera committé. Hors commit, elle lit le
  disque (ce qu'un auteur veut voir en écrivant). La règle « même commit » reste : c'est elle qui rend un
  commit vert par lui-même et un clone cohérent.
- Ne jamais committer sans demande explicite.
- ⚠️ **Un `grep` de vérification sur du Markdown doit viser un motif SANS mise en forme** (un mot nu) : `grep "empreinte TARDIVE"` ne trouve pas `empreinte **TARDIVE**`. Et **une absence de correspondance n'est jamais une preuve d'absence** tant que le motif n'a pas été validé sur un cas POSITIF connu — mesuré le 2026-09-07 : trois greps faux m'ont fait graver une « forme d'erreur inédite » qui n'existait pas, rétractée le jour même. C'est la faute que le dépôt traque chez ses sondes (absence → affirmation), commise sur l'outil de vérification lui-même.
- ⚠️ **Pas de backticks dans AUCUNE chaîne passée au shell** — `git commit -m`, `python -c`,
  `echo`… : ils sont interprétés comme SUBSTITUTION DE COMMANDE et le fragment est remplacé par du VIDE — le message part mutilé, sans erreur (mesuré le 2026-09-07 : « mon `git commit` NU » est devenu « mon  NU »). Écrire sans backticks, ou passer par un FICHIER (`git commit -F`, un script `.py` écrit
  ⚠️ **Et ça ne fait pas que MUTILER : ça ÉCRIT.** Récidive mesurée le 2026-09-08, la règle étant déjà écrite ici : un `python -c` contenant un fragment backtické a fait exécuter par bash `learned = within > chance + 0.05` — d'où `learned: command not found`, le fragment remplacé par du vide dans la sortie, **et la création silencieuse d'un fichier vide nommé `chance`** (le `>` a redirigé). Le fichier a survécu plusieurs heures dans l'arbre PARTAGÉ avant d'être vu par un `git status`. Une substitution de commande ratée peut donc laisser des DÉCHETS dans l'arbre, pas seulement un texte tronqué.
  avec l'outil Write). ⚠️ La première version de cette règle ne visait que `git commit -m` : elle a
  été prise en défaut une heure plus tard par un `python -c` qui a scellé une règle de pré-inscription MUTILÉE (S6-FALLBACK-RATE → re-scellée en `-bis`). **Une règle apprise sur UN cas doit être énoncée sur le MÉCANISME, pas sur le cas.**
- ⚠️ **Un patch qui contient des BACKSLASHS (`
`, `\`) ou des backticks ne passe PAS par un heredoc `python - <<'EOF'`** :
  mesuré deux fois le 2026-09-15, la séquence `"\n"` d'un motif de remplacement est arrivée à Python comme un SAUT DE
  LIGNE réel — le motif ne correspondait plus, l'assertion a levé (heureusement AVANT l'écriture). Même mécanisme que la
  règle des backticks : le canal shell transforme la chaîne. Écrire le script avec l'outil Write dans le scratchpad et
  l'exécuter par son chemin ; réserver le heredoc aux patches sans aucune séquence d'échappement.
- ⚠️ **Ne JAMAIS imbriquer une lecture dans l'appel qui ouvre le même fichier en ÉCRITURE.**
  `open(p, "w").write(open(p).read().replace(a, b))` évalue ses arguments de **gauche à droite** : le
  mode `"w"` TRONQUE le fichier **avant** que le `read()` interne ne le lise. Le read rend `""`, le
  replace rend `""`, le fichier est écrasé par du vide — **sans exception, sans avertissement**.
  Mesuré le 2026-09-09 : `PRIORITES_ET_DETTES.md` est passé de **2352 lignes à 0** et a été committé.
  Forme correcte : **LIRE dans une variable, transformer, puis ÉCRIRE** — et faire porter à toute
  réécriture de fichier une **assertion de TAILLE avant d'écrire**.
  ⚠️ **ET L'ASSERTION DE TAILLE NE SUFFIT PAS** — récidive le jour même, 3 h plus tard, sur un
  autre mécanisme : `s = s[:i] + NOUVEAU` lit bien dans une variable, puis **jette toute la
  queue du fichier**. Quatre tests ont disparu et la suite est restée VERTE (77 passés) parce
  qu'elle ne compte pas ce qui manque. Ce qu'il faut asserter n'est pas la taille mais un
  **COMPTE DE L'ENTITÉ** — nombre de `def test`, d'entrées de backlog, d'arêtes — et il doit
  être **>= au compte d'AVANT**, pris **hors de l'artefact modifié** (`git show HEAD:fichier`).
  Un découpage par index est la forme la plus dangereuse : il ne lève jamais. ⚠️ Et l'aval n'a rien dit : les
  **12 portes** du hook sont passées sur le fichier vide, `check_backlog_freshness` a rendu `exit 0`
  et a *invité* à resserrer sa baseline dessus. Seul le `2372 deletions` de la sortie de `git commit`
  l'a révélé — **lire le compte de suppressions de chaque commit** (classe E22 occ. 2).
- ⚠️ **Tout commit passe par `git commit -- <chemins>`, JAMAIS nu.** Un `git commit` sans pathspec
  emporte l'index ENTIER — donc le travail non committé d'une session parallèle sur un fichier qu'on
  n'a jamais touché (mesuré le 2026-09-07 : E10 occ. 19). Et avant d'éditer un fichier PARTAGÉ :
  `python -c "from tools.check_staged_authorship import snapshot; snapshot([...], owner='ma-tache')"`
  puis `verify(...)` avant de committer — la garde existe depuis le 2026-09-01, ne pas l'invoquer
  revient à ne pas l'avoir.
- ⚠️ **Sous Git Bash, `set -e` N'ARRÊTE PAS une chaîne quand un `python - <<'EOF'` échoue** (mesuré le 2026-09-06 : un patch a levé, la chaîne a continué, et un commit est parti avec un message annonçant un travail absent — rectifié par `b2a6ce3`). Chaîner par `&&` explicite, et faire échouer la chaîne AVANT `git commit`, jamais après.
- `_disable_kuzu()` / arrêter `memory_retriever` avant les boucles de simulation (contention + non-repro).
