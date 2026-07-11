# Roadmap SCIENCE — AGIseed (axe 🔬 Scientifique)

> **Domaine** : la frontière scientifique (capacités cognitives à faire émerger/mesurer). Sœurs :
> [`NAS.md`](NAS.md) (moteur évolutif) · [`BACKEND.md`](BACKEND.md) · [`FRONTEND.md`](FRONTEND.md).
> Carte complète : [`../README.md`](../README.md).
>
> **Vision** : un *« algorithme de la vie »* où la bonne chose à faire n'est **pas dite mais trouvée** —
> l'intelligence *trouvée* (connectomes évolués, bottom-up), pas *donnée*.
>
> **Cette page = ce qui reste à faire + où on en est.** L'**historique** scientifique :
> [`../FIL_CONDUCTEUR.md`](../FIL_CONDUCTEUR.md) (récit) + [`../EDR/`](../EDR/) (détail, 93 décisions).
> Les **idées futures / aspirationnel** : [`../BACKLOG.md`](../BACKLOG.md). Méthode : **Commandement 15**
> (1 variable, ≥... mesures, valide ou revert — *powerer avant de conclure*).

---

## Architecture (V15/V16)
- **59 entrées / 108 sorties** ; moteur **Liquid Mamba BatchModel** vectorisé + TTC adaptatif ; écologie 9 proies + apex + feu + crafting ; **World Model** (RND), **Actor-Critic TD** intra-vie, **HoF robuste** inter-ère.

## Les 7 Arcs (phylogénèse)

| Arc | Thème | Statut |
|---|---|---|
| 1 | L'Animal (Survie) | ✅ TERMINÉ |
| 2 | Le Primate (Outils) | ✅ TERMINÉ (V14) |
| 3 | L'Homo Habilis (Crafting) | ✅ chaîne moyens→fins émergente+robuste (`027-030`) |
| **4** | **L'Homo Sapiens (Langage)** | 🔵 **EN COURS** — code référentiel fiable câblé (`072-074`) ; bénéfice fonctionnel en cours de test rigoureux (`087`) |
| 5 | La Tribu (Culture) | ⚪ après clôture Arc 4 |
| 6-7 | Penseur, Conscience | ⚪ gelé (`docs/BACKLOG.md`) |

## Diagnostic — 3 causes-racines (orientation)

> De l'audit `EDR 010` (causes A, B) + la trouvaille de session (cause C).

| # | Cause | État |
|---|---|---|
| **A** | Le cerveau ne prédit pas | ✅ World Model RND (`011`) |
| **B** | Le monde n'exige pas l'intelligence | ✅/🔵 monde exigeant (`012`) **+ sweet spot d'énergie** (`085` : il était *trop dur* pour la survie soutenue → réglé : ×5 compétents/frais) |
| **C** | *(nouveau)* Le moteur de SÉLECTION limité par le bruit de fitness | ✅ **HoF robuste en prod** (`078-081`, gated) → +50 % compétence qui *compose* |

---

## Où on en est (037→087)

> Grand arc de session : **langage → gradient → compétence → survie**. Récit complet : `FIL_CONDUCTEUR.md`.

- **Langage (037-074)** : de « bruit » à un **code référentiel fiable câblé dans l'agent** (gradient → convergence 100 % `072` → tête dédiée `074`, MI live +0.22, gated).
- **Gradient (067-071)** *(hors plan)* : la mutation est un **chercheur faible** en supervisé (mémoire `067`, langage `072`) ; mais le **BPTT NUIT en RL** (`077`, auto-réfutation).
- **Compétence (075-081)** : plateau = **bruit de fitness** (`078`) → remède robuste en prod, qui **compose** (`081`).
- **Survie (082-087)** : le langage ne payait pas car les agents mouraient ~45 ticks (`082`). Cause = **économie d'énergie** (`084` : 79 % starvent) → **sweet spot** (`085`, survie ×4) → débloquer la survie a *révélé et corrigé* une **instabilité du connectome** sur les longs épisodes (`086`) → **re-test rigoureux du bénéfice du langage en cours** (`087`, design audité contre 12 confounds).

> **Discipline** : 5 fois un signal à peu de seeds s'est évaporé sous puissance (`057/075/077/082/083`). *Powerer + auditer le design avant de conclure.*

---

> **Backlog enrichi par le scan global** (`docs/SCAN_GLOBAL.md`, juin 2026). ⚠️ Le scan est un
> *générateur d'hypothèses* : 2 « criticals » vérifiés et **réfutés** (World Model est bien actif,
> surprise=0.25 ; le dé-bruitage HoF tient). *Vérifier avant d'agir.*

## 🔬 Frontière scientifique — prochains leviers

1. **Clore le bénéfice fonctionnel du langage (Arc 4)** — re-test `087` (FIABLE vs BROUILLÉ, isole le *contenu* du téléguidage) + **power (R≥4)** : à survie longue, le contenu référentiel paye-t-il ? Si oui → Arc 4 clos. *(Prérequis de CAPACITÉ désormais dé-risqués en proxy : trilogie `LANG-001/002/003` — cf. § Fil langage.)*
2. **Prouver que chaque monde EXIGE l'intelligence** *(hygiène fondatrice, scan S2)* — benchmark **agent dummy vs champion HoF** (ratio de survie par monde). Si ratio≈1 → le monde est factice et toute mesure de « compétence » y est du bruit. Conditionne la validité du curriculum.
3. **Vrai planning** *(scan S6)* — le « dreaming/MCTS » est du **random-shooting latent** (perturbe `H`, n'exploite PAS le World Model). Le brancher sur `world_model.predict()` pour simuler des trajectoires (obs→action→reward) → imagination instrumentale.
4. **Co-évoluer l'usage du langage** (`083`, +0.29 sous 2 SE) — pression de sélection explicite sur l'écoute ; + **récompenses intrinsèques** (curiosité comme fitness — le World Model EST actif).
5. **Régler le sweet spot d'énergie** (`085`) comme variable d'expérience ; **étoffer les mondes 2&3** (Agri=anticipation, Industrial=coopération) — substrat de l'Arc 5 *(design détaillé → `../BACKLOG.md`)*.
6. **Vraie RSI** (#8 armé `065-069`) — **après** durcir la sandbox (cf. garde-fous) ; Arc 5 **après** clôture Arc 4.

> **Audit Mémoire & Typologie d'intelligence (2026-06-30)** → backlog priorisé complet dans
> [`../AUDIT_MEMOIRE_INTELLIGENCE.md`](../AUDIT_MEMOIRE_INTELLIGENCE.md). Constat : mémoire surtout
> câblée (récup KuzuDB = 5 scalaires top-500 global, pas épisodique) ; modèle = connectome PLAT, têtes
> = tranches de sortie sans isolation de gradient, fitness scalaire `life_score` (aucune dissociation
> des facultés). Leviers ordonnés P0→P4 : **P0** fix `clear()` robust_hof + retirer gènes morts (`memory_cache`) ;
> **P1** banc « demande mémoire » (n-back) + **BPTT dans la boucle** (EDR 067 : 0.78→1.00) ; **P2** [moteur torch]
> têtes disjointes/losses séparées + récup épisodique réelle ; **P3** fitness per-type + MAP-Elites 4-tier +
> worlds 2/3 réels (KPI cognitif) + G2 ; **P4** Theory of Mind. Recoupe la migration moteur (`NAS.md`, `sota-gap-substrate`).

### 🔩 Fil torch / migration moteur — proxies H-unif (EDR 134-148, 158-168, 170 ; détail `sota-gap-substrate`)

**Carte de valeur torch COMPLÈTE, exécutable prod flag-OFF** : (1) migration faisable (torch≈legacy,
140/141) ; (2) mémoire BPTT numpy-impossible mais capacité prod (145) ; (3) **binding means→ends LIVRÉ**
= gate + anti-saturation + `learn_episode` (crédit ÉPISODIQUE, pas TD 1-pas ; 158/159, task-agnostique,
gate multi-cible `GATE_TARGETS` pour multi-compétences).

**Pari H-unif VALIDÉ en proxy standalone** (famille routage/crédit conditionnel) :
- **binding/composition PAIE** sous demande (161) ; **spécialisation** émerge + **division du travail**
  (165) — les deux POSITIFS.
- **rétention** d'un moyen COÛTEUX = **BISTABILITÉ** entièrement cartographiée (162→164→167→168→170) :
  deux seuils — cold ≈0.04 (barrière de *bootstrap*) vs warm = **r·P** (rentabilité statique, LOI
  confirmée par scaling 170) ; hystérésis ~22× ; warm-start **court (~50 ép)** rescape ; au-delà de r·P,
  métastable puis collapse.

**➡️ Handoff axe 3 in-world** (`[[torch-inworld-integration-plan]]`, la session in-world exécute) —
recommandations CHIFFRÉES des proxies, à valider in-world (P y sera différent) :
1. **Porter le binding via crédit ÉPISODIQUE** (`learn_episode`), PAS le `learn()` TD 1-pas (148).
2. **Rétention d'un moyen coûteux** : garantir `coût_du_moyen < récompense × P(suite|moyen)` OU
   **warm-start court** du binding (pré-entraîner à coût faible / curriculum de coût croissant / warm-start
   du gate EDR-132). Le levier n'est PAS « renforcer le binding » (déjà fort, P~0.9) mais le **bassin**.
3. **Multi-compétences** : gate multi-cible (`GATE_TARGETS`) route conditionnellement vers plusieurs ends.

**Raffinements restants (backlog, faible priorité — substrat synthétique dégénéré)** :
- Loi c_warm = r·P : forme exacte de P(r) (super-linéaire léger, 170) ; plus de r + seeds.
- Profondeur de warm-start en 2D (ws × coût) ; seuil warm exact près de r·P.
- Combiner les 3 axes (tâche exigeant binding + spécialisation + rétention coûteuse simultanément).
- Le vrai test = in-world (axe 1/3), pas plus de proxy.

### 🗣️ Fil langage — trilogie proxy Arc 4 (LANG-001/002/003 ; détail `lang-referential-capability`)

**Les 3 paliers du langage établis EN PROXY synthétique** (hors biosphère, substrat torch, crédit
épisodique `learn_episode`, sans toucher le code monde) — dé-risquent la roadmap #1 (re-test `087`) comme
les proxies H-unif ont dé-risqué le binding :
- **LANG-001 — CAPACITÉ** : jeu de Lewis 2-pops → signalisation référentielle porteuse (FIABLE 0.77 vs
  chance/BROUILLÉ 0.17, K=6) ; le contenu PAIE (brouiller le signal = hasard). `referential_game_probe.py`.
- **LANG-002 — PARTAGE** : un batch torch = N politiques distinctes → paires FIGÉES = codes PRIVÉS
  (within 0.80 mais cross-partenaire = chance, MI≈0) ; la **rotation de partenaires** produit un protocole
  PARTAGÉ (MI≈0.94–1.06, tout transfère à un partenaire neuf). Loi de consensus : précision partagée ↓ avec
  la taille M (goulot de conventionnalisation), MI reste ≈1. `referential_community_probe.py`.
- **LANG-003 — SYSTÉMATICITÉ** : référents (a0,a1), messages 2-symboles → code **compositionnel** qui
  GÉNÉRALISE zéro-shot aux combos jamais vus (zeroshot 0.505 ≈ within 0.539 ≫ chance 0.333) + **topsim +0.30**
  (double-confirmé, répliqué M=8/M=16). La rotation NE converge PAS sur 2-symboles (structure du message, pas
  communauté). `compositional_language_probe.py`.
- **LANG-004 — CONCILIATION (curriculum)** : le goulot de consensus de 003 est un DÉMARRAGE À FROID. Un
  **curriculum dyade→rotation** (warm-start figé puis rotation) donne un code COMPOSITIONNEL (zeroshot 0.51,
  topsim +0.31 retenus) ET PARTAGÉ (cross_mi 0.045→**0.59**, ×13) — ce que ni les dyades (privé) ni la
  rotation à froid (échoue) ne donnaient. Partage PARTIEL + érosion du within (métastabilité). Analogue exact
  du **warm-start de rétention (167/168/170)** : même hystérésis de bootstrap. `compositional_curriculum_probe.py`.
- **LANG-005 — PLAFOND = RÉGIME D'OPTIM, pas capacité** : le plafond d'accuracy (within ~0.54) est INVARIANT
  au budget (2× ép : 0.547→0.547 exact), au crédit (per_attr ≈ joint) ET à la capacité (num_nodes 172→384,
  cachés 5→217 = ×43 : plat) → c'est l'**équilibre partiel de la co-adaptation REINFORCE** (verrou récurrent
  « optim pas capacité », 131/132/133, 105/110), PAS la taille du substrat. MAIS capacité et crédit
  par-attribut améliorent la **généralisation zéro-shot** (0.49→0.57) sans toucher l'accuracy → systématicité
  et maîtrise sont des axes DISSOCIÉS. Levier compo parfaite = **optimiseur/critique** (pas + de neurones).
  `compositional_ceiling_probe.py`.

**➡️ Handoff in-world (roadmap #1, `087`)** — le re-test 087 n'a plus à prouver la CAPACITÉ (établie), seulement
le **bénéfice de survie** du contenu référentiel in-world :
1. **Recette langage torch** : crédit ÉPISODIQUE suffit pour la signalisation ; **rotation de partenaires**
   pour un protocole partagé ; **messages multi-symboles indicés par position + prédiction par attribut**
   pour la compositionnalité.
2. **Insight transférable — le levier de qualité dépend de la COMPLEXITÉ** : la rotation (communauté) paie
   sur tâche simple (partage 1-symbole) mais **s'effondre en consensus** sur tâche complexe (2-symboles, ne
   converge pas) ; là c'est la **structure du message** qui porte la compositionnalité (émerge en dyades
   figées). In-world : langage compositionnel possible même en interactions dyadiques stables SI référents
   structurés + messages multi-tokens ; le langage PARTAGÉ exige des partenaires VARIÉS (design du monde).
3. Recoupe #4 frontière (co-évoluer l'usage, `083`) : le proxy n'a PAS de coût de signal ni de pression sur
   l'écoute — in-world plus dur.

**Backlog langage (faible priorité — proxy)** : compositionnalité PARFAITE (within ~0.54 = plafond substrat ;
E rotation plus court / LR décru phase 2 / warm-start plus long ; pression longueur/vocab) ; scaling
consensus×complexité ; coût de signal + sélection sur l'écoute (`083`) ; le vrai test = in-world `087`.

> 🔑 **Loi transversale du substrat (TRIANGULÉE — 3 fils indépendants).** Sous crédit épisodique, le verrou
> n'est PAS la capacité du substrat mais le **régime de crédit/optimisation** ; et un **bassin pré-formé
> (warm-start / curriculum)** franchit une barrière de bootstrap infranchissable à froid. Trois fils, méthodes
> disjointes, même conclusion :
> - **Rétention** (fil torch `167/168/170`) : un moyen coûteux n'est PAS retenu à froid (seuil cold ≈0.04) mais
>   l'est jusqu'à ≈`r·P` après warm-start ; hystérésis ~22× ; **~50 ép de warm-start suffisent**.
> - **Langage** (`LANG-004/005`) : la rotation ne partage rien à froid mais partage (cross_mi ×13) après un
>   warm-start dyade (004) ; le plafond d'accuracy est **invariant à la capacité** (num_nodes ×43 cachés = plat)
>   = régime d'optim, pas capacité (005).
> - **Craft-or-starve** (`EDR-200` Phase B, session //, `[[decisive-substrate-thesis-test]]`) : sur un réseau
>   12-cachés, le binding échoue à froid mais un **curriculum warm-start binde 1.000 + survit 1.000** → substrat
>   CAPABLE, verrou = crédit/objectif ; thèse « migrer torch pour la capacité » **réfutée**.
> - **Prédiction actionnable (in-world)** : un verrou qui *ressemble* à une limite de capacité est
>   probablement une **barrière de bootstrap / de crédit** → (1) tester un **warm-start** (cohorte/gate
>   pré-entraîné, curriculum de coût/social) et (2) soigner le **crédit/objectif** (retour épisodique, critique)
>   AVANT de conclure à l'incapacité. Recoupe le cran 2 B2 in-world (cohorte fraîche éteinte avant l'horizon =
>   cold-start ; `[[torch-inworld-integration-plan]]`).

## 🛠️ Outillage / Dev

**Livré (session)** : **Dashboard EDR** + **Biosphère live** (onglets `edr`/`live`, `/api/edr`) ; **HoF robuste** en prod (`robust_hof_K`, gated) ; **knobs d'énergie** (`base_metabolism`/`forage_payoff`, gated) ; **stabilité connectome** longs épisodes (`086`) ; **D1 — socle de validité (RNG/Harness)** : `SeedManager` + `Harness` (composition : seed aux frontières, cycle async_logger, éval robuste **appariée**, provenance), seed boot **loggé** dans `main_biosphere` (run rejouable via `EXPERIMENT_SEED`), `robust_evaluate(seed=)`, pilote `robust_eval` migré (repro exacte prouvée sur la vraie biosphère). **+21 tests.** *(spec/plan : `../superpowers/{specs,plans}/2026-06-13-D1-RNG-Harness*`)*.

> ⚠️ **Trouvaille D1 (corrige EDR 081)** : `main_biosphere` **écrasait** `robust_hof_K=4` (2ᵉ `WorldConfig()` réinstancié) → la prod tournait en sélection **bruitée K=0**, pas robuste. **Corrigé** (le K=4 d'EDR 080/081 prend enfin effet). C'est un *changement de comportement de sélection en prod* — à garder en tête pour interpréter les prochains runs.

**Reste** *(priorisé par le scan)* :
1. **Finir D1** : (a) **apparier le HoF en prod** — `robust_rank`→`robust_evaluate` ne passe pas encore le seed (le ranking de prod reste non apparié ; le run global *est* reproductible via le seed boot) ; (b) **migrer les ~55 tools** sur `Harness`/`seed_boundary` (vague comparative `coevolve_language`/`func_benefit`/… puis le reste, mécanique) ; (c) DRY : factoriser les 4 sites inline `(base+i)%2³²` sur `seed_boundary`. *(PR de suivi)*.
2. **RSI — brancher le LLM + boucle itérative à mémoire** *(audit 2026-06-23 : machine complète, débranchée)*. La machinerie existe et est testée (`src/metaprog/rsi_loop.py`, 20 tests) : `rsi_step`/`rsi_demand_step`, `LLMProposer` (câblé mais **verrouillé** sans `llm_fn`), `make_powered_measure` (multi-seed). Clients LLM **déjà là** (`llm_proposer_fn.py` : `anthropic_llm_fn`/`local_llm_fn`/`scripted_llm_fn`). Mock actuel : `supervisor.py:103` appelle `supervisor_coder.generate_and_test_new_activation()` (Swish hardcodé). **Deux voies de risque** : (a) `world_demand` = JSON de params sanitisés (allow-list), **pas de code-exec → sans blocage sandbox**, mais *optimise un KPI non encore validé → risque Goodhart* (cf. S2) ; (b) `activation` = code généré → exige le durcissement sandbox OS. Manque pour la voie (a) : `graph.read_recent_proposals()` (injection du contexte). **Priorité : 2ᵉ** (après que la mesure de transfert du #3 valide le KPI).
3. **CurriculumRunner — 2ᵉ échelle de temps (inter-mondes)** *(audit 2026-06-23 : prêt, testé, dormant ; PRIORITÉ #1 moteur)*. `src/curriculum/runner.py` traverse une séquence de mondes par portes de maîtrise (plateau de compétence), transfère le champion via `import_agent_id`. Découplé (callback `run_era_fn`), 10 tests. Utilisé par `main_curriculum.py` mais **absent de `main_biosphere`** (boucle plate mono-monde). Branchement = **opt-in `USE_CURRICULUM`**, extraire la boucle intra-monde en `run_era_fn` (~2-3 j). **Cœur scientifique = la mesure de transfert manquante** (curriculum vs tabula-rasa, multi-seed apparié — `transfer_ratio` n'existe pas) : sans elle, le brancher serait du théâtre ; *avec* elle, c'est une expérience falsifiable (curriculum bat-il tabula-rasa ?) qui **bâtit l'instrument de validité dont la RSI #2 dépend**. Risques : seed apparié par monde (`seed_boundary` à chaque promo), non-régression du chemin legacy (opt-in off par défaut). 🟢 **Mesure de transfert LIVRÉE** (`tools/curriculum_transfer.py`) : verdict {TRANSFERE/NEUTRE/NUIT} apparié multi-seed à **budget compute égal** (tabula-rasa = `CurriculumRunner` single-stage `c_floor=1.1` tournant exactement T ères), test de signe binomial exact, provenance via ledger C1 (`Harness.save`). `run_era_fn` injectable → orchestration testée sans biosphère. **Reste** : *lancer* l'expérience à l'échelle (compute), puis l'opt-in `main_biosphere` (optionnel). *(spec/plan : `../superpowers/{specs,plans}/2026-06-23-Curriculum-Transfer*`)*.

   > **Priorité moteur (audit 2026-06-23)** : **#3 CurriculumRunner + mesure de transfert** d'abord (falsifiable, fondé, validité-natif, dé-risque la RSI) → **#2 RSI `world_demand`** ensuite (une fois le KPI validé) → durcir la sandbox OS (gate, = TODO C4) → **RSI `activation`** (code-exec, levier étroit). Rationale : *fondations de validité avant éclat*, comme C1 avant le reste du backend.
4. **Tests du cœur cognitif** (policy-gradient end-to-end, langage) — sous-testés (~2 sur `mamba_agent`).
5. **Unifier le moteur** (`world_0_soup` duplique `Biosphere3D`) ; **ontologie Hypothesis/Fact** (vide → chaque EDR=`Hypothesis`) ; **ablation** (Ratio de Transfert sur les mécanismes — cf. [`NAS.md`](NAS.md) §X2). **Réconcilier les deux forwards** (legacy `recurrent_forward` ↔ prod `MambaBatchModel`) → [`NAS.md`](NAS.md) §1.
6. **Hygiène du moteur évolutif (NAS)** → déplacé vers [`NAS.md`](NAS.md) : table de vérité génotype→phénotype, gènes morts (`bytecode`, `mutation_genes[2,3]`, `memory_cache`), Phase 0.
7. **Hygiène de mesure de l'INSTRUMENT (« garder l'instrument, migrer le moteur », cf. [`NAS.md`](NAS.md) audit substrat)** — le harnais EDR (`tools/lewis_survival_sweep.py`, mondes, métriques) est l'actif à CONSERVER pendant la migration moteur. **Livré (EDR 114b)** : knob `disable_repro` dans `_measure_forage` (pose `benchmark_mode` → cohorte fixe) — `p_reach` mesuré sur le pool `agents+dead` était **confondu ×2.3-3.3 par le pooling-reproduction** (nouveau-nés tardifs diluent), baselines forage 105/106 re-basés (figées 0.22→0.52, mobiles 0.21→0.69). **Règle générale dégagée** : toute métrique de fraction sur un pool à population variable doit figer la cohorte (`disable_repro=True`) sinon la repro déflate. **Reste (backlog tooling)** : (a) auditer les autres métriques-pool de `lewis_survival_sweep` (`p_cap`, `income_t`) pour le même confond ; (b) porter le pattern cohorte-fixe sur les futurs harnais du moteur torch (banc transfert means→ends, `transfer_ratio`) ; (c) provenance — `name=` distinct par expérience (collision JSON EDR 107) systématisée. *(doc : `docs/EDR/114b_*`.)*

> **Chantiers d'infra déplacés** *(split du 2026-06-24)* :
> - **Backend** (Observabilité/Provenance C1, A/B multi-run C2, Stubs/dette/CI C3, Sécurité/sandbox C4 —
>   ✅ C1-C4 complète) → [`BACKEND.md`](BACKEND.md).
> - **Frontend** (A/B live, tests Vitest+RTL, CI, nettoyage stubs) → [`FRONTEND.md`](FRONTEND.md).

## 🧭 Garde-fous méthodo *(angles morts du scan — à poser avant les benchmarks)*

- **Budget compute** : la rigueur multi-seed × K-éval × R-runs *explose* sur mono-machine → profiling / parallélisme / early-stopping **avant** S2/S4.
- **Stats au-delà du RNG** : correction multi-comparaisons (Bonferroni/Holm) + **power analysis a priori** (quel K ?) + **taille d'effet** (pas que p<.05).
- **Sécurité** : RCE *applicatif* fermé (✅ **C4** : whitelist + confinement + CORS + auth/timeout opt-in). **Reste** avant d'armer la RSI en prod : durcir l'**isolation OS** de la sandbox (conteneur / limites mémoire-réseau) — `run_sandboxed` reste un subprocess local.
- **« 1 variable »** : tout changement cognitif **gèle l'aval** d'abord (sinon confound — rallumer 3 systèmes = 3 variables).

---

## Statut des Vagues (pointeurs)

| Vague | Statut |
|---|---|
| **0 — Fondations** | ✅ LIVRÉE (`010-030`) : moteur évolutif réparé (`016`), Actor-Critic (`020`), chaîne moyens→fins auto-suffisante (`030`) |
| **1 — Honnêteté/hygiène** | 🟠 gènes câblés ✅ (`031`) ; ablation + unify-engine + ontologie ⏳ (cf. Dev) |
| **2 — RSI (graine d'AGI)** | ✅ sandbox isolée (`035`) + supervisor réflexif (`036`) + **#8 armé** (`065-069`) ; vraie RSI ⏳ (différée) |
| **3 — Émergence avancée** | 🔵 **langage émergent EN COURS** (`037-087`, Arc 4) ; protoconcepts/économie cognitive → `../BACKLOG.md` |
| **4 — Différé/gelé** | ⚪ NAS Macro, Arcs 6-7 → `../BACKLOG.md`. À ne pas toucher tant que V0-V3 ne livrent pas. |

> **Règle** : on ne passe à la vague N+1 que si N est *livrée ET mesurée*.

## Méthode & Outils
- **Commandement 15** : 1 variable, mesures suffisantes (≥ ce que la puissance exige), Sociologue, valide ou revert.
- Outils : `tools/sociologist.py` (rapport KuzuDB), `tools/skinner_box.py` (audit neuronal), `tools/progress.py` (barres+ETA), `migrate_v10.py` (chirurgie génétique).
