# Scan global AGIseed — juin 2026 (76 findings, 7 agents + synthese + critique de completude)

> ⚠️ **VERIFICATION — lire AVANT d'agir.** Ce scan est un *generateur d'hypotheses*, PAS un verdict.
> Deux "criticals" ont ete VERIFIES et sont FAUX / sur-affirmes :
>
> 1. **"World Model mort, surprise=0" → FAUX.** Le WM est cable (`world_1_stoneage.py:38` l'instancie,
>    `:945` le passe au batch). Surprise reelle MESUREE = 0.25 moyenne (max 1.0, 65/80 non-nulles). La
>    cause-racine A d'EDR 010 est resolue. Les agents ont vu le defaut `=None` dans `mamba_agent.py` mais
>    rate le cablage dans le monde. -> Tous les findings derives (curiosite morte, dreaming jamais
>    declenche faute de surprise) TOMBENT.
> 2. **"De-bruitage du HoF robuste casse (RNG correle)" → SUR-AFFIRME.** Les K eres consecutives tirent
>    des segments DIFFERENTS du flux PRNG (pas identiques) -> echantillons distincts -> le de-bruitage
>    (EDR 078/080, valide empiriquement powered) TIENT. Le vrai probleme RNG est l'**APPARIEMENT** des
>    comparaisons (corrige en EDR 087), pas le de-bruitage.
>
> **Regle** : verifier chaque finding (surtout les "critiques") avant d'agir. Le RESTE est
> plausible/reel : dreaming=random-shooting, supervisor_coder mocke, mondes 2&3 stubs, cœur cognitif
> sous-teste, et les ANGLES MORTS (budget compute, stats multi-comparaisons, securite sandbox avant RSI,
> versioning des donnees) sont excellents et valides.

---

# SCAN GLOBAL AGIseed — synthese

Findings: 76 | science=19 dev=44 les_deux=13 | critiques=15


## SYNTHESE
Voici la synthèse. Le contenu des 7 rapports est suffisant pour produire le brainstorm — pas besoin de fouiller le code, l'audit est déjà fait.

# SYNTHÈSE STRATÉGIQUE AGIseed — Deux sessions parallèles

## 1. ÉTAT GLOBAL

Le projet a une **vraie ossature** : connectome liquide ODE opérationnel, double boucle d'apprentissage (Hebbien + évolution topologique), harnais d'évaluation rigoureux (multi-seed/Welch), dashboard powered branché sur de vraies données, et un journal EDR honnête de 87 entrées avec discipline "1 variable, power avant de conclure". Mais le cœur souffre d'un **découplage gène-phénotype** massif : le World Model est instancié à `None` par défaut (surprise=0 partout), la boucle RSI et le LLM réel tournent uniquement sur banc (`tools/`) jamais en production, et plusieurs gènes (bytecode, parts du dreaming) sont mutés sans jamais être lus. Les faiblesses structurantes sont donc moins des bugs que des **fils débranchés** : des capacités codées qui n'alimentent pas la boucle vivante. Deux mondes (Agricultural, Industrial) restent des stubs cosmétiques, et la reproductibilité (RNG global non seedé) fragilise toute conclusion future.

## 2. 🔬 PISTE SCIENCE — chantiers ordonnés par impact/effort

**S1. Brancher le World Model → restaurer la surprise réelle [S]**
*Quoi* : instancier `WorldModel(...)` dans `MambaBatchModel` au lieu de `None`.
*Pourquoi ça débloque* : c'est la racine de tout. Surprise=0 aujourd'hui ⇒ aucune curiosité intrinsèque, dreaming jamais déclenché, signal d'erreur de prédiction inexistant. Un fil débranché qui rallume trois systèmes d'un coup. **Fondation absolue.**

**S2. Prouver que chaque monde EXIGE l'intelligence (cause-racine B) [M]**
*Quoi* : agent DUMMY (logit constant) vs champion HoF, mesurer ratio survie par monde.
*Pourquoi* : hygiène scientifique non négociable. Si ratio≈1 quelque part, ce monde est factice (réflexe suffit) et toute mesure de "compétence" y est du bruit. Conditionne la validité du curriculum entier.

**S3. Fermer la boucle Actor-Critic TD(0) [M]**
*Quoi* : extraire l'action réelle des logits après forward, stocker (s,a,r,s'), appliquer δ=r+γV(s')−V(s) au tick N+1.
*Pourquoi* : transforme le Hebbien brut en vrai crédit d'action+temps. Sans ça, l'agent n'apprend pas *quelle action* mène à la récompense. Valider d'abord sur curriculum toy (1 action, récompense immédiate).

**S4. Clôturer l'Arc 4 — langage fonctionnel sous puissance [M]**
*Quoi* : relancer `coevolve_language` avec **R=4 runs** par régime (use_head on/off), vérifier séparation >2 SE.
*Pourquoi* : le "+1.62 Mammouths" repose sur **1 seule run** = bruit possible. Soit on valide (Arc 4 clos, langage référentiel prouvé utile hors gradient), soit c'est un vrai négatif à acter. Tranche un arc ouvert avec les outils déjà livrés.

**S5. Mécaniques cognitives RÉELLES des mondes 2 & 3 [L]**
*Quoi* : Agricultural EXIGE l'anticipation (semis/récolte, pénalité d'hiver force le stockage, horizon MCTS ~20-50 ticks) ; Industrial EXIGE la coordination (chaîne rock→craft→delivery infaisable en solo, chasse Mammouth multi-agent synchrone).
*Pourquoi* : débloque le curriculum développemental complet (réflexe→outil→planification→coopération). Sans demande exigeante, le curriculum n'a rien à apprendre.

**S6. Dreaming = vrai planning instrumental [L]**
*Quoi* : remplacer le random-shooting latent par `world_model.predict()` simulant trajectoires (obs→action→reward), best branch = argmax retour γ-discounté.
*Pourquoi* : donne au cerveau une vraie imagination instrumentale ("si je fais X, je reçois Y"). Dépend de S1. C'est le saut planification.

**S7. Mesurer l'oubli catastrophique inter-mondes [L]**
*Quoi* : ablation KEEP_MEMORY=0 vs 1, rejouer KPI Soup après Agricultural.
*Pourquoi* : valide ou invalide le carry-over NTM. Si oubli >20%, implémenter freeze_mask. Garde-fou du curriculum.

## 3. 🛠️ PISTE DEV — chantiers ordonnés par impact/effort

**D1. FIX reproductibilité RNG/appariement [S→M]** *(le plus critique)*
*Quoi* : `np.random.seed(EXPERIMENT_SEED)` au boot de `main_biosphere` ; seed incrémental (seed+i) dans `robust_evaluate`/`run_era` ; audit `refgame_bio`/`lewis_world`/`coevolve_language` pour seed-per-event.
*Pourquoi* : **les K ères clones du HoF robuste partagent le RNG global ⇒ sorties corrélées ⇒ le dé-bruitage ne marche pas.** Sans ça, AUCUNE conclusion scientifique n'est solide. C'est le socle de la piste Science.

**D2. Brancher la boucle RSI + LLM réel en production [S+M]**
*Quoi* : (a) remplacer le mock Swish hard-codé de `supervisor_coder.py` par un appel `local_llm_fn` injecté (1 ligne) ; (b) câbler `rsi_demand_step` dans `main_biosphere` après chaque ère avec mesure multi-seed.
*Pourquoi* : la RSI tourne sur banc, zéro feedback vers la prod. Le pivot "graine auto-modifiante" n'existe pas en ligne. EDR 065/066 prouvent que ça marche — il faut juste le brancher. Variable d'env `LLM_MODE=local|anthropic|scripted|off`.

**D3. Activer le curriculum inter-mondes dans main_biosphere [M]**
*Quoi* : remplacer la boucle monolithique par `CurriculumRunner.run()` avec stages Soup→Stoneage→Agri→Industrial, portes de maîtrise, transcript→KuzuDB.
*Pourquoi* : le runner existe, testé, mais dormant. C'est la "deuxième échelle de temps" — le cœur observable d'AGIseed. **Pré-requis** : pré-éval robuste K=3 ères pour ne pas promouvoir sur 1 ère bruitée.

**D4. Boucle RSI itérative à mémoire + ontologie [M]**
*Quoi* : boucle N_ITERATIONS dans `run_once` où `context['recent']` accumule scores mesurés ; enregistrer Hypothesis/Fact/SUPPORTS dans KuzuDB.
*Pourquoi* : aujourd'hui chaque ère repart clean — le LLM ne peut pas *itérer* ni apprendre de ses tentatives. C'est le feedback fermé, fondation du #8.

**D5. BaseHarness unifié + RNG seedé [M]**
*Quoi* : `src/seed_ai/experiment_harness.py` — classe mère (seed, async_logger, eras, eval_robust(K=3), save_results). ~60 outils héritent.
*Pourquoi* : fragmentation actuelle (chaque tool réinvente seed/logging/progress). Réduit la friction pour créer un nouvel outil fiable. Synergie directe avec D1.

**D6. Frontend — contrôle A/B live + tests unitaires [M→L]**
*Quoi* : `FlatlandServer`→`FlatlandManager` (dict de runs, `/ws/flatland/{run_id}`), onglet compare-live (baseline vs intervention côte à côte) ; ajouter Vitest+RTL (couverture 0 aujourd'hui hors E2E).
*Pourquoi* : on ne peut pas comparer 2 lignées en parallèle dans le dashboard — c'est précisément le geste scientifique central. Tests unitaires = anti-bitrot.

**D7. Dette + drain KuzuDB + CI [S→M]**
*Quoi* : instrumenter `AsyncLogger` (queue_size, latency, warn si queue>1000/timeout>5s, dégradation gracieuse si DB absente) ; nettoyer les gènes fantômes (supprimer bytecode OU câbler une VM 8-ops) ; extraire `SoupWorldLegacyV13` ; `.github/workflows/ci.yml` (pytest + npm build + tsc).
*Pourquoi* : réduit le bruit de sélection (bytecode muté sans effet = dérive aléatoire de la pop), protège contre les backlogs DB silencieux, et verrouille la non-régression.

## 4. CE QUI MANQUE STRUCTURELLEMENT (capacités AGI absentes)

| Capacité | État | Nature |
|---|---|---|
| **Planification** (lookahead par modèle du monde) | Random-shooting latent, pas de prédiction de trajectoire | **SCIENCE** (S6, dépend S1) |
| **Curiosité intrinsèque** | Codée mais morte (surprise=0) | **SCIENCE/infra** (S1 — fil débranché) |
| **Crédit temporel** (apprendre *quelle* action) | TD(0) implémenté mais boucle ouverte | **SCIENCE** (S3) |
| **Théorie de l'esprit / coopération** | Inexistante — Industrial est un stub | **SCIENCE** (S5) — exige une mécanique multi-agent |
| **Auto-modification réelle** (RSI) | Mock hard-codé, LLM jamais appelé en prod | **INFRA** (D2) puis **science** (que proposer ?) |
| **Mémoire épistémique inter-vies** (skills, pas juste NTM) | Carry-over NTM seulement, oubli non mesuré | **SCIENCE** (S7) |
| **Reproductibilité** | RNG global non seedé | **INFRA** (D1) — pré-requis de tout le reste |
| **Accumulation de connaissance** (ontologie vivante) | KuzuDB câblé mais zéro entrée RSI | **INFRA** (D4) |

**Lecture** : la planification, le crédit temporel, la ToM/coopération et la mémoire épistémique sont des chantiers **science** (nouvelles capacités cognitives à faire émerger/mesurer). La curiosité et la RSI sont **infra d'abord** (rebrancher des fils) **puis science** (qu'en fait-on ?). La reproductibilité est **pure infra** mais conditionne la validité de tout le volet science.

## 5. THÉÂTRE RÉSIDUEL (stubs de l'audit EDR 010 encore vivants aujourd'hui)

**Persiste vraiment :**
- **World Model débranché** (`world_model=None`) → surprise=0. *Le théâtre central de EDR 010, toujours là.* (cause-racine A non résolue)
- **RSI/LLM mock** : `supervisor_coder.py` renvoie un Swish hard-codé identique à chaque appel ; aucun des 3 modes LLM n'est déclenché par `main_biosphere`. La réflexivité n'est pas testée en ligne.
- **Bytecode fantôme** : muté/hérité/crossover mais jamais lu en inférence ⇒ bruit de sélection pur.
- **Dreaming "MCTS"** : random-shooting dans le latent, sans arbre ni back-up ni modèle du monde — "on ne rêve pas vraiment, on explore le latent brut".
- **Mondes 2 & 3** : héritent puis ajoutent des cosmétiques (saisons, pollution) sans aucune pénalité sélective exigeante.
- **Actions Actor-Critic** : viennent d'un dict `_pg` posé sur l'agent, jamais associées au choix réel de l'agent dans le monde.

**Résolu / honnête (à ne pas confondre avec du théâtre) :**
- Neuromodulation W_router (FONCTIONNE, l.438), thresholds (FONCTIONNE), attention QKV (implémentée), stabilité numérique EDR 086 (clipping ±30 validé, 146 tests), sandbox AST deny-by-default (réelle), dashboard EDR (vraies données curées).

**Verdict** : le théâtre n'est pas du faux affichage — c'est du **code réel non câblé à la boucle vivante**. La cure est mécanique (brancher) avant d'être conceptuelle.

## 6. RECOMMANDATION DE DÉMARRAGE

**🔬 Session SCIENCE — commencer par S1 (brancher le World Model).**
Une poignée de lignes (`world_model=WorldModel(input_dim=64, out_dim=8)` à l'instanciation, valider que `Wp_batch` est round-trippé par agent). Gain immédiat et fondateur : la surprise redevient non-nulle, la curiosité intrinsèque s'allume, le dreaming devient logiquement cohérent. Validation rapide : agent voit obs_t, prédit obs_t+1, signal curiosité = erreur de prédiction non-nulle sur un changement d'observation. **C'est le fil qui rallume le plus de systèmes pour le moins d'effort** — et il débloque S6 (planning) en aval.

**🛠️ Session DEV — commencer par D1 (FIX RNG/reproductibilité).**
`np.random.seed(EXPERIMENT_SEED)` au boot + seed incrémental dans `robust_evaluate`/`run_era`. Gain rapide et **fondateur pour les deux sessions** : sans RNG indépendant par répétition, le dé-bruitage du HoF robuste est illusoire (sorties corrélées) et aucune conclusion de la session Science ne tiendra. C'est le socle de validité — à poser avant que S2/S4 ne produisent des chiffres qu'on voudra croire.

**Synergie** : S1 (surprise réelle) + D1 (mesure reproductible) posés ensemble = on peut **immédiatement** lancer S2 (ablation dummy vs champion) sur une base saine. Les deux premiers gestes se renforcent mutuellement.


## ANGLES MORTS
Voici les angles morts, priorisés.

**1. Coût/scaling de calcul — le multiplicateur caché (CRITIQUE, sous-estimé)**
La synthèse empile des exigences qui multiplient le compute sans jamais budgéter le temps machine. D1 (seed incrémental sur K répétitions) × S2 (dummy vs champion) × S4 (R=4 runs × 2 régimes) × D3 (pré-éval K=3 ères par promotion) × S6 (rollouts de trajectoires en dreaming) = explosion combinatoire. Sur un poste Windows mono-machine (pas de cluster mentionné), passer de 1 run à K runs reproductibles peut transformer une ère de minutes en heures. **Aucun finding ne chiffre le budget compute, ni ne propose de profiling/parallélisation.** Risque : la "rigueur multi-seed" devient théoriquement juste mais pratiquement inexécutable. À poser : un budget temps/ère mesuré + early-stopping + parallélisme avant de lancer S2/S4.

**2. Validité scientifique des comparaisons multi-seed — au-delà du RNG (MAJEUR, angle mort méthodo)**
D1 traite le *mécanisme* (RNG seedé) mais pas la *méthode*. Findings absents : (a) **correction multi-comparaisons** — avec ~8 mondes/régimes testés en Welch, le taux de faux positifs explose (pas de Bonferroni/Holm mentionné) ; (b) **détermination a priori de K** (power analysis : quel K pour détecter l'effet attendu ?) — la discipline "power avant de conclure" est citée mais jamais opérationnalisée en N ; (c) **taille d'effet vs significativité** — "+1.62 Mammouths" est-il *grand* ou juste *significatif* ? Sans ça, S2/S4 produiront des p-values qu'on sur-interprétera. Le RNG est nécessaire mais non suffisant.

**3. Sécurité de la métaprogrammation — déprioritisée à tort (CRITIQUE mal rangé)**
"SANDBOX METAPROG: ISOLEMENT INSUFFISANT" est classé `risque/critique` dans la liste brute mais **disparaît des recommandations D1-D7**. Or D2 propose d'*armer la RSI en production* (LLM réel générant du code exécuté dans la boucle vivante). Brancher l'exécution de code auto-généré AVANT de durcir le sandbox, c'est inverser l'ordre sûr. La synthèse dit "sandbox AST deny-by-default (réelle)" en colonne "résolu" tout en gardant "isolement insuffisant" en risque critique — **contradiction non résolue.** Avant D2 : threat-model du code généré (boucles infinies, exhaustion mémoire, accès fichiers/réseau via imports non couverts par l'AST).

**4. Persistance/intégrité des données expérimentales (MAJEUR, sous-traité)**
KuzuDB n'apparaît que via perf/drain (D7) et ontologie vide (D4). Manquent : **schéma de versioning des résultats** (quand le code change, comment relier un KPI à la version de code/gènes qui l'a produit ? pas de hash de config/commit dans les findings) ; **format de checkpoint reproductible** (D6 mentionne la gestion d'état entre ères comme "mineur" — mais sans sérialisation déterministe du HoF+RNG+World Model, un run interrompu n'est pas reprenable à l'identique) ; **provenance** (l'EDR a 87 entrées honnêtes, mais les *données brutes* derrière chaque verdict sont-elles archivées/rejouables ?). Sans ça, la repro D1 s'arrête au RNG et ne couvre pas la repro *end-to-end*.

**5. Risque de confusion S1 — "brancher le World Model" peut tout casser silencieusement (MAJEUR, optimisme non questionné)**
La reco de démarrage vend S1 comme "une poignée de lignes, gain immédiat". Angle mort : **réactiver surprise≠0 change la distribution de récompense de TOUS les mécanismes en aval simultanément** (curiosité, dreaming, sélection). Sans ablation contrôlée, on ne saura pas si un changement de KPI vient du World Model ou d'un effet de bord. La synthèse viole sa propre discipline "1 variable" dès le premier geste : S1 rallume "trois systèmes d'un coup" — c'est exactement *3 variables*. Il faut un protocole : brancher le WM avec curiosité/dreaming d'abord *gelés*, valider surprise≠0 isolément, puis dégeler un mécanisme à la fois.

**Méta-angle mort transversal** : la synthèse est entièrement tournée vers *capacités cognitives* et *rigueur statistique*, mais ignore l'**exécutabilité opérationnelle** (compute, repro end-to-end, sécurité d'exécution) — précisément ce qui décide si les sessions Science/Dev produiront des résultats *réels* ou *théoriques*.


## FINDINGS CRITIQUES (bruts)

- [les_deux/S] Prediction & surprise signal : World Model initialise mais logiquement MORT en batch : world_model existe (world_model.py) mais self.world_model passe en None par defaut dans MambaBatchModel.__init__ (l.276), donc observe_batch jam -> Brancher le World Model en production : passer world_model=WorldModel(input_dim=64, out_dim=8) lors de la creation du batch. Valider que Wp_batch (B,I,O) est in

- [science/L] Dreaming : random-shooting, pas d'arbre MCTS reel : Le 'MCTS' dans mamba_agent.py:519-549 est du random-shooting dans l'espace latent : (1) pas d'arbre = chaque iteration k cree une branche H_branch+noise (l.525-527), zero trace de trajectoire, zero ba -> V1 planning reel : (1) Brancher world_model.predict() pour generer la prochaine obs depuis le latent ; (2) generer action logits depuis la branche de latent ; (

- [dev/S] Brancher World Model : world_model=None par defaut : MambaBatchModel.__init__(world_model=None) laisse world_model=None par defaut (l.276). Consequence : observe_batch (l.418-424) test `if self.world_model is not None` et skip silencieusement, donc surp -> Passer world_model=WorldModel(...) lors de l'instanciation MambaBatchModel dans world_1_stoneage (la ou batch_model est cree). Verifier que Wp_batch est init co

- [dev/S] Surprise signal toujours zero en batch (EDR 010 cause-racine A) : world_model.observe_batch() (world_model.py:51-68) n'est JAMAIS APPELE car self.world_model=None par defaut. Ligne mamba_agent.py:418 : `if self.world_model is not None and self.Wp_batch is not None.. -> Instant-win (EDR 010 levier 1) : instancier WorldModel et passer a MambaBatchModel. 1 ligne dans main. Valider : surprise doit etre non-zero sur changements obs

- [science/M] Cause-racine B : l'intelligence est-elle EXIGÉE ? : Question centrale non résolue : chaque monde exige-t-il vraiment l'intelligence, ou un réflexe préencodé suffit-il ? SOUP : c'est un sensorimoteur pur, homéostasie. Évaluation : agents stupides surviv -> Benchmark par ablation réflexive : (i) implémenter un agent DUMMY stupide (logit constant), tester sa survie dans chaque monde. Si survie(Soup) ≥ 50 ticks mais 

- [dev/M] Reproducibilité intra-harnais (tools/) vs inter-harnais : robust_eval.py (lin. 40-46) ne pose JAMAIS de seed explicite dans run_era(). Les appels _robust_score() et _true_competence() répètent run_era() K ou n fois sans seed différent à chaque répétition. L' -> Modifier robust_evaluate() et run_era() pour accepter seed kwarg, incrémenter seed à chaque répétition (seed+i pour i in range(K)). Documenter dans eval_harness

- [dev/S] Supervisor-Coder : génération réelle vs. mockée : supervisor_coder.py (27 lignes) contient du code **codé en dur** : la fonction Swish complète (lignes 12-18) est un string littéral, jamais générée. Le fichier avait la bonne intention (appel à valida -> Remplacer supervisor_coder.generate_and_test_new_activation() par un appel qui (a) lève une exception (refus d'armer sans LLM vrai) ou (b) utilise llm_proposer_

- [dev/M] Fermeture de la boucle : aucune tentative du #8 n'alimente la prochaine : Aujourd'hui, le flow est : supervisor détecte famine -> génère Swish -> valide -> charge. Demain (si LLM est armé) : supervisor détecte famine -> LLM propose activation/world_demand -> valide -> mesur -> Ajouter une boucle N_ITERATIONS (default 3-4) dans supervisor_runner.run_once() : à chaque itération, (a) proposer (LLM lit context['recent']), (b) mesurer, (c)

- [dev/M] Pas d'authentification/multi-utilisateurs : Pas d'auth dans FastAPI main.py (allow_origins=["*"] CORS). Pas de session, JWT, roles (admin vs viewer). Endpoint /api/sandbox/start accessible à quiconque → lancer n'importe quel script. État shared -> Si besoin multi-user : ajouter FastAPI auth (JWT + roles). Sandbox: owner-based isolation (user peut voir/contrôler ses runs). Si usage single-user (local dev) 

- [les_deux/L] MONDE N'EXIGE PAS L'INTELLIGENCE (cause-racine B, EDR 010) : Énergie abondante : visite case +0.5 (free), dopamine-surprise +0.5 (récompense non-gagnée), alignement vocal +0.5 (constant si signal), respawn infini. Crafting profond débranché → intelligence sous- -> LEVIER #2 d'EDR 010 : rareté dure en curriculum. Stage 0 (monde sûr) : visite+grab+fire. Stage 1 : retirer bonus (visite=-0.1, dopamine-surprise→vraie prédictio

- [les_deux/L] COUVERTURE TESTS: CORE COGNITIF NON TESTÉ : 166 tests, 2718 LOC. Couverture par área: curriculum (10 tests, solide), world_model (10 tests, learning validated), mamba_agent (2 tests basique, forward pass + dimensions), evolution (1 test XOR, co -> Ajouter 20+ tests critiques : (1) test_policy_gradient_delta_advantage : vérifier que RL augmente la probabilité d'action récompensée sur 5 steps, (2) test_lang

- [dev/M] SANDBOX METAPROG : ISOLEMENT INSUFFISANT : secure_sandbox.py:run_sandboxed() : subprocess pytest, timeout 5s. Pas de restriction imports (peut importer os, socket), pas de limite mémoire/CPU/réseau. Vulnérable RCE dès qu'un code généré (future -> Avant d'armer RSI (#8, LLMProposer.llm_fn), configurer container vrai (Docker, bubblewrap) OU whitelist d'imports sévère (numpy, scipy only) + AST-scanning du c

- [les_deux/L] Planification réelle & World Model exploité (manque fondamental) : World Model (EDR 011, 015) implémentée (src/agents/world_model.py) : prédiction linéaire RND, erreur→surprise utilisée pour curiosité. MAIS jamais exploitée en planification. Agents réagissent (1-tick -> (1) Implémentation dreaming.py : given obs(t)+action(t), inverser WM pour prédire obs(t+1..t+T); Value Head appris du critic pour évaluation simulée. (2) Point 

- [science/L] Theory of Mind léger — inférer intentions/croyances d'autrui (Arc 5) : Aucune implémentation : grep pour 'belief', 'intention', 'other_agent_model' → 0 résultats. Agents perçoivent pairs comme objets mobiles + émetteurs tokens, pas agents intentionnels. Implication d'Arc -> (1) Différé après Arc 4 clos + planification. (2) Prototype theory_of_mind.py : pour chaque agent observé, maintenir vecteur d'état latent (belief, goal) entraî

- [science/M] Récompenses intrinsèques pures vs survie injectée (Vague 3) : Système actuel : life_score = ticks × facteur (récompense EXTRINSÈQUE injectée par évoluteur). Vision BACKLOG 4.1 : évoluer vers signaux intrinsèques purs (curiosité/minimisation erreur prédiction) ;  -> (1) Prototype fitness_curiosity : fitness = surprise_resolved (WM error baisse) plutôt que life_score brut. (2) Test : agents sous curiosité seule survivent-ils
