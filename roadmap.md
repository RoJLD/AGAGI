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
2. **Brancher le `supervisor_coder` sur un vrai LLM** (mock Swish hardcodé) + **boucle RSI itérative à mémoire** en prod — *après* durcir la sandbox.
3. **Brancher le `CurriculumRunner`** (existe, testé, **dormant**) dans `main_biosphere` — la 2ᵉ échelle de temps (inter-mondes).
4. **Tests du cœur cognitif** (policy-gradient end-to-end, langage) — sous-testés (~2 sur `mamba_agent`).
5. **Frontend** : contrôle A/B live (comparer 2 lignées), tests Vitest+RTL, CI ; nettoyer stubs (`sandbox_service`, academy/strategy mock).
6. **Unifier le moteur** (`world_0_soup` duplique `Biosphere3D`) ; **ontologie Hypothesis/Fact** (vide → chaque EDR=`Hypothesis`) ; **ablation** (Ratio de Transfert sur les mécanismes).
7. **Versioning des données / Observabilité** : 🔵 **C1 livré (roadmap backend, chantier 1)** — **ledger de provenance** (`/api/provenance` : seed+commit+config_hash+git_dirty ↔ KPIs ; nœud `Run` KuzuDB, `ERA_RESULT`→`Run`), **santé KuzuDB** (`/api/health/kuzu` : reachable/writable/schema/counts → tue les *données fantômes*), **drain KuzuDB instrumenté** (`/api/observability/logger` : queue/latence/events/erreurs). Le **verdict S2** apparaît au dashboard *via le ledger* (ses `results/s2_demand_*.json` sont déjà au format `Harness.save`). *(spec/plan : `docs/superpowers/{specs,plans}/2026-06-15-C1-Observability-Provenance*`)*. **Reste** : checkpoint reproductible binaire (HoF+RNG+WM). **Roadmap backend** : C2 A/B live multi-run · C3 brancher stubs + dette/CI · C4 sécurité & sandbox.

## 🧭 Garde-fous méthodo *(angles morts du scan — à poser avant les benchmarks)*

- **Budget compute** : la rigueur multi-seed × K-éval × R-runs *explose* sur mono-machine → profiling / parallélisme / early-stopping **avant** S2/S4.
- **Stats au-delà du RNG** : correction multi-comparaisons (Bonferroni/Holm) + **power analysis a priori** (quel K ?) + **taille d'effet** (pas que p<.05).
- **Sécurité** : durcir la sandbox (conteneur / limites mémoire-réseau) **AVANT** d'armer la RSI en prod (`run_sandboxed` = subprocess sans limites).
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
