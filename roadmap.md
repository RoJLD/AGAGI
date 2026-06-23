# Roadmap AGIseed — Ce qui reste

> **Vision** : un *« algorithme de la vie »* où la bonne chose à faire n'est **pas dite mais trouvée** —
> l'intelligence *trouvée* (connectomes évolués, bottom-up), pas *donnée*.
>
> **Cette page = ce qui reste à faire + où on en est.** L'**historique** scientifique :
> `docs/FIL_CONDUCTEUR.md` (récit) + `docs/EDR/*` (détail, 87 décisions). Les **idées futures /
> aspirationnel** : `docs/BACKLOG.md`. Méthode : **Commandement 15** (1 variable, ≥... mesures, valide ou
> revert — *powerer avant de conclure*).

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

1. **Clore le bénéfice fonctionnel du langage (Arc 4)** — re-test `087` (FIABLE vs BROUILLÉ, isole le *contenu* du téléguidage) + **power (R≥4)** : à survie longue, le contenu référentiel paye-t-il ? Si oui → Arc 4 clos.
2. **Prouver que chaque monde EXIGE l'intelligence** *(hygiène fondatrice, scan S2)* — benchmark **agent dummy vs champion HoF** (ratio de survie par monde). Si ratio≈1 → le monde est factice et toute mesure de « compétence » y est du bruit. Conditionne la validité du curriculum.
3. **Vrai planning** *(scan S6)* — le « dreaming/MCTS » est du **random-shooting latent** (perturbe `H`, n'exploite PAS le World Model). Le brancher sur `world_model.predict()` pour simuler des trajectoires (obs→action→reward) → imagination instrumentale.
4. **Co-évoluer l'usage du langage** (`083`, +0.29 sous 2 SE) — pression de sélection explicite sur l'écoute ; + **récompenses intrinsèques** (curiosité comme fitness — le World Model EST actif).
5. **Régler le sweet spot d'énergie** (`085`) comme variable d'expérience ; **étoffer les mondes 2&3** (Agri=anticipation, Industrial=coopération) — substrat de l'Arc 5 *(design détaillé → `BACKLOG.md`)*.
6. **Vraie RSI** (#8 armé `065-069`) — **après** durcir la sandbox (cf. garde-fous) ; Arc 5 **après** clôture Arc 4.

## 🛠️ Outillage / Dev

**Livré (session)** : **Dashboard EDR** + **Biosphère live** (onglets `edr`/`live`, `/api/edr`) ; **HoF robuste** en prod (`robust_hof_K`, gated) ; **knobs d'énergie** (`base_metabolism`/`forage_payoff`, gated) ; **stabilité connectome** longs épisodes (`086`) ; **D1 — socle de validité (RNG/Harness)** : `SeedManager` + `Harness` (composition : seed aux frontières, cycle async_logger, éval robuste **appariée**, provenance), seed boot **loggé** dans `main_biosphere` (run rejouable via `EXPERIMENT_SEED`), `robust_evaluate(seed=)`, pilote `robust_eval` migré (repro exacte prouvée sur la vraie biosphère). **+21 tests.** *(spec/plan : `docs/superpowers/{specs,plans}/2026-06-13-D1-RNG-Harness*`)*.

> ⚠️ **Trouvaille D1 (corrige EDR 081)** : `main_biosphere` **écrasait** `robust_hof_K=4` (2ᵉ `WorldConfig()` réinstancié) → la prod tournait en sélection **bruitée K=0**, pas robuste. **Corrigé** (le K=4 d'EDR 080/081 prend enfin effet). C'est un *changement de comportement de sélection en prod* — à garder en tête pour interpréter les prochains runs.

**Reste** *(priorisé par le scan)* :
1. **Finir D1** : (a) **apparier le HoF en prod** — `robust_rank`→`robust_evaluate` ne passe pas encore le seed (le ranking de prod reste non apparié ; le run global *est* reproductible via le seed boot) ; (b) **migrer les ~55 tools** sur `Harness`/`seed_boundary` (vague comparative `coevolve_language`/`func_benefit`/… puis le reste, mécanique) ; (c) DRY : factoriser les 4 sites inline `(base+i)%2³²` sur `seed_boundary`. *(PR de suivi)*.
2. **RSI — brancher le LLM + boucle itérative à mémoire** *(audit 2026-06-23 : machine complète, débranchée)*. La machinerie existe et est testée (`src/metaprog/rsi_loop.py`, 20 tests) : `rsi_step`/`rsi_demand_step`, `LLMProposer` (câblé mais **verrouillé** sans `llm_fn`), `make_powered_measure` (multi-seed). Clients LLM **déjà là** (`llm_proposer_fn.py` : `anthropic_llm_fn`/`local_llm_fn`/`scripted_llm_fn`). Mock actuel : `supervisor.py:103` appelle `supervisor_coder.generate_and_test_new_activation()` (Swish hardcodé). **Deux voies de risque** : (a) `world_demand` = JSON de params sanitisés (allow-list), **pas de code-exec → sans blocage sandbox**, mais *optimise un KPI non encore validé → risque Goodhart* (cf. S2) ; (b) `activation` = code généré → exige le durcissement sandbox OS. Manque pour la voie (a) : `graph.read_recent_proposals()` (injection du contexte). **Priorité : 2ᵉ** (après que la mesure de transfert du #3 valide le KPI).
3. **CurriculumRunner — 2ᵉ échelle de temps (inter-mondes)** *(audit 2026-06-23 : prêt, testé, dormant ; PRIORITÉ #1 moteur)*. `src/curriculum/runner.py` traverse une séquence de mondes par portes de maîtrise (plateau de compétence), transfère le champion via `import_agent_id`. Découplé (callback `run_era_fn`), 10 tests. Utilisé par `main_curriculum.py` mais **absent de `main_biosphere`** (boucle plate mono-monde). Branchement = **opt-in `USE_CURRICULUM`**, extraire la boucle intra-monde en `run_era_fn` (~2-3 j). **Cœur scientifique = la mesure de transfert manquante** (curriculum vs tabula-rasa, multi-seed apparié — `transfer_ratio` n'existe pas) : sans elle, le brancher serait du théâtre ; *avec* elle, c'est une expérience falsifiable (curriculum bat-il tabula-rasa ?) qui **bâtit l'instrument de validité dont la RSI #2 dépend**. Risques : seed apparié par monde (`seed_boundary` à chaque promo), non-régression du chemin legacy (opt-in off par défaut).

   > **Priorité moteur (audit 2026-06-23)** : **#3 CurriculumRunner + mesure de transfert** d'abord (falsifiable, fondé, validité-natif, dé-risque la RSI) → **#2 RSI `world_demand`** ensuite (une fois le KPI validé) → durcir la sandbox OS (gate, = TODO C4) → **RSI `activation`** (code-exec, levier étroit). Rationale : *fondations de validité avant éclat*, comme C1 avant le reste du backend.
4. **Tests du cœur cognitif** (policy-gradient end-to-end, langage) — sous-testés (~2 sur `mamba_agent`).
5. **Frontend** : contrôle A/B live (comparer 2 lignées), tests Vitest+RTL, CI ; nettoyer stubs (`sandbox_service`, academy/strategy mock).
6. **Unifier le moteur** (`world_0_soup` duplique `Biosphere3D`) ; **ontologie Hypothesis/Fact** (vide → chaque EDR=`Hypothesis`) ; **ablation** (Ratio de Transfert sur les mécanismes).
7. **Versioning des données / Observabilité** : 🔵 **C1 livré (roadmap backend, chantier 1)** — **ledger de provenance** (`/api/provenance` : seed+commit+config_hash+git_dirty ↔ KPIs ; nœud `Run` KuzuDB, `ERA_RESULT`→`Run`), **santé KuzuDB** (`/api/health/kuzu` : reachable/writable/schema/counts → tue les *données fantômes*), **drain KuzuDB instrumenté** (`/api/observability/logger` : queue/latence/events/erreurs). Le **verdict S2** apparaît au dashboard *via le ledger* (ses `results/s2_demand_*.json` sont déjà au format `Harness.save`). *(spec/plan : `docs/superpowers/{specs,plans}/2026-06-15-C1-Observability-Provenance*`)*. **Reste** : checkpoint reproductible binaire (HoF+RNG+WM). **Roadmap backend** : ✅ **C1-C4 complète** — C1 observabilité/provenance · C2 A/B live multi-run · C3 stubs+dette/CI · C4 sécurité & sandbox (cf. chantiers ci-dessous).
8. **A/B live multi-run** : 🔵 **C2 livré (roadmap backend, chantier 2)** — N runs flatland concurrents (cap `MAX_RUNS=4`) comparant 2 lignées côte à côte en direct : **`FlatlandServer` paramétré** (overrides whitelistés + `label`), **`FlatlandManager`** (dict de runs, cycle de vie, `default` legacy préservé), **router REST** `/api/flatland/runs` (POST/GET/DELETE → 429 cap / 400 override / 404 delete) et **WebSocket** `/ws/flatland/{run_id}` (stream par run, close 1008 si inconnu ; legacy `/ws/flatland` intact). ⚠️ **Caveat observationnel** : le moteur consomme `np.random` **global** → deux runs concurrents = flux entrelacés, **non appariés et non reproductibles** (le GIL garantit l'atomicité, pas la repro). L'A/B live est donc **observationnel** ; la mesure rigoureuse (appariement seedé) reste l'affaire du harness offline (D1/S2). *(spec/plan : `docs/superpowers/{specs,plans}/2026-06-15-C2-Flatland-Multirun*`)*.
9. **Brancher stubs + dette/CI** : 🔵 **C3 livré (roadmap backend, chantier 3)** — **honnêteté** : `strategy.py` ne renvoie plus le mock fantôme `StoneAge (Mock)` ; flag `source` ∈ {`live`,`empty`,`error`} (le frontend distingue *pas encore de run* de *vrai*). **Bug dormant corrigé** : le nœud `Article` avait deux schémas (`timestamp` chez `Sociologist` vs `date` partout ailleurs) → `/sociologist/articles` renvoyait toujours `[]` ; **unifié sur `date`** (insertion + `_init_schema` + route + modèle). **Couverture** : `test_sandbox` (statut/stop/start-erreurs/logs sans subprocess), `test_strategy`, `test_sociologist`. **CI** : la pipeline exécute enfin les tests C1/C2/C3 (`ci.yml` ne lançait que `test_backend`+`test_visualization`). *(spec/plan : `docs/superpowers/{specs,plans}/2026-06-16-C3-Stubs-Dette-CI*`)*. **Reste backend** : C4 sécurité & sandbox (auth/CORS + subprocess borné) — ✅ **livré** (cf. ci-dessous, chantier 4).
10. **Sécurité & sandbox** : ✅ **C4 livré (roadmap backend, chantier 4 — dernier ⇒ roadmap backend C1-C4 complète)** — ferme le trou **RCE** de `/api/sandbox/start` : **whitelist de scripts + confinement `PROJECT_ROOT`** (`_is_allowed_script` tue le path-traversal `../../` et l'exécution de fichiers arbitraires ; `start()` refuse sans lancer) ; **CORS restreint** à l'origine frontend (`AGISEED_CORS_ORIGINS`, plus de wildcard `*`) ; **auth opt-in par token** (`require_token` : `X-API-Token`/`Bearer`, env `AGISEED_API_TOKEN` ⇒ ouvert en dev local, exigé en prod) sur les endpoints **mutateurs** (sandbox start/stop/curriculum/action, flatland POST/DELETE runs, sociologist analyze) ; **timeout subprocess opt-in** (watchdog daemon `AGISEED_SANDBOX_TIMEOUT`). Whitelist + CORS **toujours actifs** ; auth + timeout **opt-in env** ⇒ le dashboard local n'est pas cassé. **Couverture** : `test_security` (auth open/enforced/401/GET-ouvert, CORS non-wildcard) + `test_sandbox` (whitelist accepte/rejette traversal, start refuse, watchdog tue) ; ajoutés à la CI. *(spec/plan : `docs/superpowers/{specs,plans}/2026-06-22-C4-Securite-Sandbox*`)*. ⚠️ **Reste** (durcissement profond, avant RSI en prod) : conteneur isolé + limites mémoire/réseau (cf. garde-fous) — la whitelist ferme le RCE *applicatif*, pas l'isolation OS.

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
| **3 — Émergence avancée** | 🔵 **langage émergent EN COURS** (`037-087`, Arc 4) ; protoconcepts/économie cognitive → `BACKLOG.md` |
| **4 — Différé/gelé** | ⚪ NAS Macro, Arcs 6-7 → `BACKLOG.md`. À ne pas toucher tant que V0-V3 ne livrent pas. |

> **Règle** : on ne passe à la vague N+1 que si N est *livrée ET mesurée*.

## Méthode & Outils
- **Commandement 15** : 1 variable, mesures suffisantes (≥ ce que la puissance exige), Sociologue, valide ou revert.
- Outils : `tools/sociologist.py` (rapport KuzuDB), `tools/skinner_box.py` (audit neuronal), `tools/progress.py` (barres+ETA), `migrate_v10.py` (chirurgie génétique).
