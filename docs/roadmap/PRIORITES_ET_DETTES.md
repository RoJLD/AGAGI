# Priorités & dettes — backlog ACTIONNABLE

> À ne pas confondre avec [`../BACKLOG.md`](../BACKLOG.md), qui est le « someday » aspirationnel.
> Ici : ce qui est **à faire**, dans l'ordre, avec la preuve et le coût.

Établi le **2026-07-21**, à l'issue de l'arc WARM-005→009 et du chantier méthodologique qui en est sorti.
Ordre de priorité **décroissant**. Chaque entrée porte : ce qu'il faut faire, **pourquoi** (avec la preuve),
et le coût estimé.

> Contexte chiffré qui justifie l'ordre : sur cet arc, **7 revues adversariales → 7 erreurs réelles**, et
> **71 instruments détectés, 1 calibré**. Le déficit dominant n'est pas l'honnêteté du compte-rendu
> (négatifs consignés, auto-réfutations écrites, portées bornées) mais l'**absence de calibration** et
> l'**absence d'application exécutable** des règles déjà documentées.

---

## ✅ 2026-08-04 (soir) — DETTE DE PRODUCTION RÉGLÉE (correctif prêt, bascule à décider)

**Le défaut** : `add_node` ET `add_meso_gated_unit` (`src/seed_ai/mutation.py`) insèrent des lignes et
colonnes à l'indice `j` **sans mettre à jour `num_inputs`/`num_outputs`**. Insérer dans le bloc de sortie
re-mappe quelle décision chaque nœud pilote — **56 % de désalignement mesuré**, ce qui détruit un lecteur
câblé ~65 % du temps ([[EDR-EVO-021]]).

**Le correctif** : `MutationConfig.preserve_io_blocks`, **désactivé par défaut** (off = bit-identique).
L'insertion est contrainte à la région cachée et les indices `i`/`j` sont décalés correctement — l'
off-by-one signalé par la revue est réglé du même coup. Pré-vol : **38/200 décalages en historique,
0/200 corrigé**.

**Validation** ([[EDR-EVO-024]]) : 2 bras × 12 seeds, **0/12 des deux côtés, Fisher p = 1.000**. Le
correctif **ne change aucune conclusion** — les records EVO-005→023 restent valides, aucune re-mesure
nécessaire. La prédiction avait été posée avant le run (EVO-023 : le défaut est réel mais non
contraignant).

**Ce qui reste — une DÉCISION, pas une tâche** : basculer `preserve_io_blocks=True` par défaut. Ce n'est
pas fait ici parce que `mutation.py` est partagé avec des sessions parallèles et que changer le
comportement sous les pieds d'un run en vol est exactement la contamination que le bail `kuzu` empêche
pour les mondes. **Critère proposé** : quand aucun run n'est en vol, sur décision explicite.

**Anti-récidive, automatisé** : `tests/sandbox/test_mutation_block_invariants.py` ne teste pas une liste
d'opérateurs, **il la DÉCOUVRE** — toute fonction de `mutation.py` qui fait grandir `num_nodes` est
soumise au contrat de bloc, y compris celles ajoutées plus tard. Nécessaire : le défaut avait deux
porteurs et je n'en avais vu qu'un.

---

## ⏱️ 2026-08-04 — ARC EVO CLOS (005→018). Trois directions restantes, priorisées

**Énoncé de clôture** : dans ce substrat, la découverte d'un câblage cognitif ne s'obtient qu'en
FOURNISSANT la réponse. Ni objectif (EVO-005/016), ni récompense (×2.4 de durée de vie, mesuré), ni
atteignabilité (1 seul poids), ni difficulté de la cible (EVO-018), ni inertie de la sélection.
**C'est le TIRAGE** : `add_connection` doit tomber sur ~3 arêtes utiles parmi ~11 000, et **six** méthodes
de recherche ont échoué à changer cette probabilité (009 ciblage=triche · 010 volume · 013 plafond fan-in ·
014 préservation de R · 015 réutilisation de motif · 017 nouveauté).

**D1 — VOLUME × PRÉSERVATION DU FAN-IN (la cellule VIDE, priorité haute).** L'analyse à deux régimes
d'[[EDR-EVO-013]] la désigne : le baseline est limité par le NUMÉRATEUR (l'arête n'est jamais créée), le
régime densifié par le DÉNOMINATEUR (sorties saturées). EVO-010 a testé le volume SEUL, EVO-014 le
fan-in SEUL — **jamais les deux ensemble**. Beaucoup de tirages ET des sorties maintenues propres attaque
les deux régimes à la fois. Agnostique, bon marché (~30 min), et c'est le seul levier que l'arc désigne
sans l'avoir essayé. *Coût : ~1 h avec pré-vol.*

**D2 — Horizon d'un autre ORDRE.** À ~2.7e-4 par tirage et ~400 tirages/lignée, l'espérance est de 0.11
découverte. Pour atteindre ~90 % il faut ~21× plus de tirages (≈750 ères, ou une population bien plus
large). Mesurable, mais ce n'est plus la même expérience — et EVO-010 suggère que le volume seul sature.
À faire APRÈS D1, qui teste la même idée en bornant le coût. *Coût : plusieurs heures.*

**D3 — Changer le MOTEUR, pas la recherche.** Un substrat où la variation ne soit pas un tirage d'arêtes
isolées. ⚠️ **Recoupe le travail en cours d'une session parallèle** (`bilinear-substrate-unlocks-composition`,
2026-08-03) — coordonner avant d'engager quoi que ce soit, sous peine de doublon.

---

## ⏱️ MISE À JOUR 2026-07-28 — arc EVO-005→009 livré, et les DEUX dernières dettes P3 sont CLOSES

> Lire ce bloc avant tout le reste : il périme plusieurs entrées ci-dessous.

**P3 est TERMINÉ. Le registre n'a plus AUCUNE classe sans garde exécutable** (18/18).
* **P3.1 / E11** — `tools/preregister.py` + 6 tests. Règle de lecture scellée par hash ; la ré-écrire sous
  le même nom LÈVE (on écrit une `-bis`, le changement devient VISIBLE) ; édition manuelle DÉTECTÉE.
* **P3.2 / E13** — `tools/cost_guard.py` + 6 tests. Projection AVANT (marge ×3) + plafond PENDANT, et un
  plafond de population DÉTERMINISTE dans la boucle de ticks (`MAX_AGENTS`).

⚠️ **Chacune a corrigé l'énoncé de sa propre dette en se fermant**, et c'est l'enseignement le plus
réutilisable de la passe : E11 ne fuit pas par le SEUIL (la discipline manuelle le protégeait déjà) mais
par l'**INSTRUMENT** ; E13 ne se borne pas par une projection, parce que **le coût dépend du SEED** (il suit
le succès évolutif) — le débit mesuré au smoke était JUSTE et le run a explosé quand même.

**Arc EVO-005→009 — 5 records, dont un RÉTRACTÉ par les suivants :**
* **EVO-005** : un objectif cognitif dense achète le plafond de ce qu'on gagne SANS lire (raw max 0.472 /
  plafond analytique 0.500) et rien au-delà. Réconcilie « fitness = non-levier » (EDR-056/WLD-002, artefact
  de RARETÉ du comportement noté) et « verrou = objectif » (surestimé).
* **EVO-006 — ⛔ RÉTRACTÉ** : « le crédit partiel est le gradient manquant », bâti sur **1 seed sur 5**.
  Réfuté par EVO-007 (0/12 à difficulté appariée). Classe **E9**, occurrence la plus coûteuse à ce jour.
* **EVO-007** : 0/12 lecteurs dans les trois bras. Ni le crédit partiel ni la facilité ne produisent la
  lecture. Réplication du jeu mixte : 1/12 vs 0/11, **Fisher p = 1.000**.
* **EVO-008** : la lecture apparaît d'un **SAUT** mutationnel (0.00 → 1.00 en une ère) puis est RETENUE
  28/29 ères -> **le verrou est la DÉCOUVERTE, pas la rétention**.
* **EVO-009** : biaiser l'**opérateur de variation** fait passer la lecture de **1/12 à 12/12**
  (**Fisher p = 9.6e-6**), sans coût de survie. ⚠️ **DIAGNOSTIC, pas algorithme** — le biais connaît les
  arêtes qui comptent.

**Dette HoF 59↔64 / 108↔126 : CLOSE.** Ce n'était pas une divergence de lignée mais **deux contrats
coexistants** — `WorldConfig` (59/108) vs `MambaAgent` V18 (64/126 = +8 ToM +5 Goal +5 masque), le monde
tronquant ses 5 colonnes `manager_goal`. Débloquer tient en deux lignes de config ; fait, et les champions
canoniques probés confirment EVO-004 (bascule médiane **0.0000**).

**Ce qui reste ouvert, par ordre de valeur :**
1. **Un biais de variation AGNOSTIQUE à la tâche** — la vraie question posée par EVO-009. Candidat le plus
   net : rendre `mutate_weights` capable de RÉVEILLER des poids nuls (il ne touche aujourd'hui que les
   non-nuls, ce qui rend la découverte dépendante du seul `add_connection`).
2. **Pointer le levier sur un canal à contenu de MONDE** (obs[4], type d'apex) : la lecture apparaît-elle,
   et **PAIE-t-elle en survie** ? Un négatif confirmerait [[EDR-S2-012]] causalement.
3. `benchmark_discrimination` : seule la branche du DÉFAUT est calibrée (`disc` sature à 1.00 sur 1-2
   rencontres). La branche « `disc` mesure vraiment un choix » exige un génome connu-discriminant
   in-world — qui n'existe pas encore, et que le point 2 produirait. **Dépendance explicite, pas oubli.**

---

## ⏱️ MISE À JOUR 2026-07-23 — état réel (le corps du doc ci-dessous est en partie PÉRIMÉ)

> Ce doc date du 2026-07-21. Plusieurs entrées marquées « ouvert » sont en fait CLOSES (vérifié) ; ne pas
> repartir dessus sans vérifier le cliquet / les tests. État à jour :

**Cliquet de calibration : 83 détectés, 14 calibrés** (vs « 71 / 1 » de l'en-tête et « 80 / 10 » de P2).
Items P2 marqués ouverts mais en réalité CLOS : **P2.1** (branche `perception` de `_torch_survival_eras` —
3 vrais tests, `make_perception_world`, `test_instrument_calibration.py:385-426`), **P2.5**
(`compute_ab_verdict` calibré `["*"]`), le confond **n_lived** de P2.2 (tranché par EDR-DREAM-001).

**Arc EVO-001→003 livré cette session (2026-07-22/23)** :
- **EDR-EVO-002** (`513ef7e`) : test discriminant d'EVO-001 → `OBJECTIVE_IS_LEVER`. Un objectif qui EXIGE
  la mémoire fait ÉVOLUER un substrat qui la maîtrise (rappel différé 1.00 sur 8/8, sign_p=0.0078) ; FRESH/
  MLESS à chance. Le verrou est l'OBJECTIF, pas le substrat ni la recherche. 2 instruments calibrés (dont
  `sep(D)` réfuté comme mesure de capacité → mesurer la CAPACITÉ, pas un proxy dynamique).
- **EDR-EVO-003** (`1e8cfce`/`a02a34e`/`47a2b71`) : pont in-world. Infra bâtie (`tools/evo_memory_inworld.py` :
  évolution in-world auto-contenue + `MemoryDemandBiosphere` + ablation). Verdict mémoire in-world genuinement
  DIFFÉRÉ — **3 murs distincts** : délai-1 non-contraignant · corps-insuffisant → plancher EDR-090 · agent
  ISOLÉ figé (la sonde dense hors-contexte est invalidée par son propre contrôle positif, `agent_moved=0.00`).
  Contrôle positif PARTIEL trouvé (discrimination VISIBLE s'évolue sous Leurre létal). Frontière = mesure
  dense **IN-CONTEXTE**. Rigueur tenue : aucune fausse victoire gravée.

**Le déficit dominant du doc (calibration P2) est ESSENTIELLEMENT RÉSOLU.** Tous les items P2 « ouverts »
vérifiés ce jour sont clos : P2.0-bis (`champion_body` **est** gravé — EDR-S2-012), P2.1, P2.5, confond
n_lived (DREAM-001). Le cliquet est passé de 1 à 14 calibrés. Ce doc a besoin d'un vrai refresh, pas d'items.

**Frontière genuinement OUVERTE (le doc n'y pointe plus)** :
- **Cognition IN-WORLD** — le vrai gap « proxy 9 / in-world 0 ». EVO-002 l'a tranché en PROXY (objectif =
  levier) ; EVO-003 a montré que le porter in-world bute sur survivable↔exigeant (3 murs). Frontière concrète =
  mesure dense **IN-CONTEXTE** (cf. [[inworld-memory-bridge-status]]), et plus largement la recette S2-005 in-world.
- **Axes science ouverts** (cf. mémoire `research-backlog-and-gaps`) : H-unif in-world, G4, langage in-world
  (087), vrai planning. C'est là qu'est la valeur, pas dans la calibration (close).
- **DÉCISION robla** hors périmètre agent : P1.4 (aliasing prod), P1.5 (commits).

---

## P0 — Bloquant : restaurer un environnement vérifiable

**P0.1 — ~~Redémarrer l'environnement~~ → RÉSOLU, et mon diagnostic était FAUX.**
J'avais écrit « processus/threads orphelins probables » **sans le mesurer**. Mesure faite :
**zéro processus orphelin**, 18 Go de RAM libres sur 64. L'échec réel était
`bash: fork: retry: Resource temporarily unavailable` (code `0xC000012D`) = défaillance de fork
**côté Cygwin/MSYS**, transitoire — pas une saturation par des processus Python. Vérifié depuis :
fork OK, 13/13 tests passent. *(Classe E9 du registre — conclure depuis un symptôme saillant sans
mesurer, commis dans le document qui liste E9.)*

**P0.2 — ✅ RÉSOLU (2026-07-22) — la suite passe BOUT-EN-BOUT, plus aucun hang.**
Collecte : **1266 tests, 0 erreur** (en hausse de 1170). Bout-en-bout `pytest -m "not slow"` : **1215
passed, 6 failed, 6 skipped, 41 deselected en 13 min 21 s** — plus AUCUN hang. Les DEUX hangs (racine #1
`async_logger.stop`, racine #2 `edr114` smoke lent) étaient les seuls blocages ; pas de racine #3.
Les **6 échecs étaient tous PRÉ-EXISTANTS, rapides (pas des hangs), NON liés à mes changements** (vérifié :
persistent avec `mamba_agent.py` à l'état pré-DREAM `f9b1845`). **TOUS CORRIGÉS (2026-07-22)** — 6 vrais
fix, 0 xfail, suite VERTE (43 passed / 0 xfailed / 0 failed sur les 4 fichiers) :
- ✅ `test_substrate_world_ab` ×2 : `_ab_from_meds` testé à **n=3** (`sign_p=0.25`), impossible sous la
  garde de puissance P2.5 → bumpé à **n=6**. Même correctif que les 7 autres tests bumpés quand la garde
  a été armée ; celui-ci avait été manqué.
- ✅ `test_g_fidelity_probe` ×2 : le seuil `base_err > 0.01` filtrait 100 % des transitions RÉELLES
  (mesurées ~5e-3, substrat CONTRACTIF EDR-DREAM-005) → `ratios` vide. Seuil calibré sur l'échelle
  mesurée → **1e-3** (garde les vraies transitions, exclut le quasi-figé). Le « blocueur n=0 » était un
  seuil miscalibré, PAS une incapacité de l'arc anticipation.
- ✅ `test_edr113_landing::test_landing_reward_is_paid_monotone` : l'ancien test comparait l'énergie
  AGRÉGÉE (40 pas, proie tuée) — gain du scaffold effacé par le clamp `energy_max` du repas (L833) ET
  rendu CHAOTIQUE par le couplage énergie→obs→comportement (delta 0.00 à start=80, −55 à start=20).
  Réécrit : **proie SURVIVANTE, 1 pas** → isole le paiement, `delta = scaffold_land × anneal` **exact**
  (9.667). Le scaffold EST correctement payé (L773) ; c'était le test qui était mal conçu.
- ✅ `test_famine_storage_probe::test_evolve_in_famine_returns_genome` : le test hardcodait 59/108
  (MambaAgent nu) alors qu'`evolve_in_famine` utilise `init_primordial_soup` → dims du MONDE (64/126 sur
  feat/d1, obs étendue). Test rendu **agnostique** : dérive la référence d'`init_primordial_soup`.

---

## P1 — Dettes ouvertes

**P1.1 — ⏳ RACINE #1 CORRIGÉE (2026-07-22), accumulation profonde restante.**
Le hang `async_logger.stop() → time.sleep` est ÉLUCIDÉ par la démarche systématique (faulthandler →
`async_logger.py:80`) : `stop()` faisait `while not queue.empty()` **SANS BORNE** ; si le worker meurt
(échec de connexion KuzuDB, 5 retries → `return`), la queue ne se vide jamais → boucle infinie. **Fix
livré** : `stop()` borné (worker vivant ET délai 5 s ; le flush restant se termine sous le join, pas de
perte). Test `test_async_logger_stop_bounded.py` (échec→passe, + non-régression worker-vivant). Effet
mesuré : la suite passe de **6 % à 24 %** (`competence_profile`, `behavioral_diversity` et les hangers
intermédiaires DÉBLOQUÉS).
**RACINE #2 — RÉSOLUE (2026-07-22), et ce n'était PAS de l'accumulation.** Diagnostic corrigé par la
mesure : `test_main_reach_oracle_smoke_and_determinism` **hange AUSSI en isolation** (2m10 seul via
pytest) — mon hypothèse d'accumulation était FAUSSE (mesure : 200 workers retriever zombies ne
ralentissent un `einsum` que ×1.3, pas ×1000). Faulthandler (isolation propre) : le thread principal est
dans `mamba_agent.forward`, à des lignes DIFFÉRENTES entre deux snapshots (659 puis 831) → il **progresse,
c'est LENT pas infini**. Mesuré : `main_reach_oracle` = **135 s**, et le test le lance **2×**
(déterminisme) ≈ 270 s. Cause : world model divergé en régime oracle → `surprise` sature à 1.0
(`mamba_agent:549`, overflow clippé) → dreaming naturel à CHAQUE tick sur 4 cellules × 2 seeds × 150
ticks. **Fix : `@pytest.mark.slow`** (7 autres tests du fichier passent, 1 désélectionné). C'était juste
un smoke lourd **mal catégorisé**, démasqué par le fix racine #1 (qui a laissé la suite progresser
au-delà de 6 %).
⚠️ **Systémique probable** : d'autres smokes lourds sont sans doute non marqués `slow`. Le fix propre
serait un **timeout PAR-TEST** (`pytest-timeout`, dép. dev) faisant ÉCHOUER vite tout test >N s au lieu
de hanger la suite — surface tous les mal-catégorisés d'un coup au lieu du whack-a-mole. *Décision robla
(ajout de dépendance).* ⚠️ Note d'efficacité hors sujet : la divergence du world model en régime oracle
(overflow ligne 549) est peut-être elle-même corrigeable, ce qui accélérerait le smoke.

**P1.2 — ~~Câbler `sim_session`~~ → FAIT, et remplacé par un JOB MANAGER.**
`tools/jobs/` livré (lease/run/doctor, **11/11 tests**), inspiré de `cmex_crypto.batch` (Quant-lab) dont
la recherche SOTA — 5 angles, 19 sources, 25 claims vérifiés à 3 votes — avait déjà tranché : *construire
le gouverneur, réutiliser les primitives*. **Écart de conception assumé** : Quant-lab gouverne par cap de
concurrence (un nombre) ; AGAGI a besoin de **ressources NOMMÉES exclusives** (KuzuDB), car un cap global
à 1 sérialiserait des jobs indépendants sans dire pourquoi. Câblé dans `_torch_survival_eras` ;
`sim_session.py` est **déprécié**. Reste à câbler : `measure_inworld_grab_rate` et les ~70 autres sondes.
*(Ancien texte ci-dessous conservé pour la traçabilité de la preuve.)*

**P1.2-bis — ⚠️ LARGEMENT PÉRIMÉ (constaté 2026-07-22).** Les cibles nommées `measure_inworld_grab_rate`
(`warmstart_evolution_inworld.py:1043`) ET `_torch_survival_eras` tiennent DÉJÀ le VRAI bail
(`_acquire_kuzu` → `tools.jobs.lease.acquire("kuzu")`, pas un correctif ad hoc). L'entrée décrit un état
antérieur à leur câblage. De plus, sa motivation « suite en timeout » était en réalité le bug `stop()`
de P1.1 (corrigé), **pas** la contention de lock. Reste, en défense-en-profondeur (valeur moindre,
sessions parallèles finies) : les sondes standalone actives sans bail exclusif — `dreaming_probe.main()`
(utilise `_acquire_shared_db` mais pas le bail) et `s2_demand` — plus ~70 scripts one-off legacy à ne
PAS wirer en masse (morts, risque > valeur). *Coût résiduel : ~30 min pour les 2 sondes actives.*

**P1.3 — Graver un EDR : aliasing des bancs torch + défaut du retriever.** Deux findings mesurés, non
encore consignés, qui **changent la lecture de WARM-005/007/008** :
- *Aliasing* : les écritures du monde dans `H` (`world_1_stoneage:1289` pénalité anti-répétition, `:966`
  consensus social) ne sont **PAS inertes** — mesure propre et séquentielle sur l'étalon : **3/6 génomes
  diffèrent, `agent02` de +37 %** (`[50.5, 46.0, 55.0]` aliasé vs `[35.0, 36.0, 41.0]` découplé).
  ⚠️ Ceci **corrige** la conclusion antérieure « prod ≈ découplé, le découplage est inutile », qui ne
  tenait que sur 3 génomes d'un seul monde. Portée : **bancs torch uniquement** — la production tourne en
  `LegacyPopulationModel` (`use_torch_inworld = False` par défaut), sans état aliasé.
- *Retriever* : `_torch_survival_eras` laissait `memory_retriever` **actif pendant toute la simulation**
  (thread daemon, `_running = True`), contre la règle documentée du projet. **Toutes** les mesures de
  survie de l'arc ont tourné ainsi. Corrigé ; reproductibilité désormais vérifiée (`run1 == run2` exact).
*Coût : ~1 h.*

**P1.4 — DÉCISION robla : corriger l'aliasing en production, ou l'épingler ?** Le monde écrit dans l'état
récurrent par cette voie dans tous les bancs torch. Corriger changerait **toutes les baselines torch** ;
ne pas corriger exige un test qui **épingle** le comportement pour qu'il ne dérive pas silencieusement.
Décision hors de mon périmètre (code partagé, arbre partagé entre sessions). *Coût : décision.*

**P1.5 — DÉCISION robla : le commit.** Rien n'est committé de cette session (~20 fichiers, tous scopés).
Trois touchent du code partagé — `src/agents/backend_torch.py` (couvert 28/28), et deux nouveaux outils.
*Coût : décision + revue.*

---

## P2 — Calibration des instruments (le déficit dominant)

> 🔬 **CLASSEMENT ÉTABLI PAR MESURE** (workflow 15 agents : 8 cartographes + 6 contre-vérificateurs
> adversariaux + synthèse, 2026-07-21). **Règle de lecture qui en sort** : sur 6 contre-vérifications,
> tout score justifié par « beaucoup de records le citent » a perdu **18 à 46 points** (présumé gonflé de
> ~30 %) ; ceux fondés sur un **seam d'injection réel** en ont gagné. Les scores ci-dessous sont ceux du
> VÉRIFICATEUR quand il existe (✔), sinon marqués ⚠.
>
> ⚠️ **PRÉREQUIS RÉGLÉ** : le cliquet lui-même mentait — `scan_calibrated()` validait par SUBSTRING du
> nom, donc `_torch_survival_eras` passait pour calibré alors que seule sa branche `grab_off` l'était.
> Classe **E4** dans l'outil écrit pour l'empêcher. Corrigé (clé = `(fonction, branche)` DÉCLARÉE) +
> régression permanente.

**P2.0 — ✅ FAIT (2026-07-21) — le contrôle positif gratuit a coûté 6 s et RÉFUTÉ un record.**
Résultat gravé : **[EDR-WARM-010](../EDR/WARM-010_Fitness_Landscape_Is_Not_Flat_Partial_Competence_Is_Rewarded.md)**.
- Le banc est **INNOCENTÉ** : ratio **22.22** avec l'oracle (21.05 publié) → il sait produire un positif.
- Donc le NEUTRAL de WARM-002 n'est pas un artefact de banc — mais la dose-réponse de fidélité
  (`partial_oracle`, nouvel étalon de compétence GRADUÉE) montre **9.0 → 12.0 → 17.5 → 37.0 → 94.2 →
  200.0**, strictement monotone, 12/12 ères séparées à chacune des 5 marches. **Le paysage n'est PAS
  plat** ; le mécanisme de WARM-002 est réfuté, son échec empirique tient, l'attribution passe du MONDE à
  l'OPTIMISEUR (converge [[warm-start-transversal-law]]).
- Deux erreurs : **E3** (ratio lu sur un bras à 5.0-7.2 ticks, SOUS le plancher 9.0) et **E8** (seuil
  « ~99 % » importé de WARM-001). Nouvelle classe **E14** ouverte (garde jamais rétro-appliquée).
- ⚠️ **Question ouverte installée** : l'ATTEIGNABILITÉ. Le gradient est dense dans l'espace des
  COMPORTEMENTS ; rien ne dit que la mutation W-only le trouve dans l'espace des GÉNOMES. C'est
  maintenant la formulation correcte de l'échec de WARM-002 — et elle est testable.

**P2.0-bis — `champion_body` n'a AUCUN record** (`grep docs/EDR/` : 0 hit) alors qu'il porte le verdict
fondateur S2, sur lequel repose toute la §2 de `SPECIFICATION_10ANS.md`. Finding fondateur sans record
**ni** calibration. Candidat sérieux au top 3. *(non traité)*

**P2.1 — `_torch_survival_eras`, branche `perception` — 85 ✔** *(passe DEVANT `ablation_verdict`)*
Le seam `world_cls` existe déjà ; la branche porte les ratios publiés de WARM-001 (1.6→2.1) et WARM-003
(5.04) et n'a **aucun** cas. **Effet de levier** : le même étalon perceptif ferme d'un coup les trous de
`_mamba_survival_eras` (34 ⚠) et `verdict_demand_marker` (48 ⚠). Ajouter 2 seams manquants au passage.

**P2.2 — ✅ FAIT (2026-07-21) — bug RÉEL corrigé, et EDR-095 n'est PAS affecté.**
Le défaut latent soupçonné est **confirmé par mesure** : `_paired_ratios` faisait `arm / max(off, 1e-6)`
sans condition → une paire **doublement ÉTEINTE** rendait `0.0`, survivait au filtre `r != 1.0` et
comptait **contre le rêve**. Avant correctif, deux bras **strictement identiques et éteints** rendaient
`CAUSE_NUISIBLE, ratio 0.0, sign_p 0.00195` (classe **E1** — un contrôle qui ne peut pas rendre NEUTRE).
- **Le défaut agissait dans les DEUX sens** : sur un jeu où le rêve aide dans 4 paires informatives sur 4,
  six paires éteintes empoisonnaient la médiane (ratio 0.0 au lieu de 1.40) et **masquaient le bénéfice**.
- **Correctif** : paires non informatives ÉCARTÉES (champ `n_ecartees`) ; si toutes le sont →
  `INCONCLUSIVE_DEGENERATE` (même nomenclature que la garde de `ablation_verdict`).
- ✅ **EDR-095 tient** : ses bras publiés (`off ∈ [0.113,0.165]`, forcés `∈ [0.055,0.090]`) n'ont **aucun
  zéro**. Rejoué après correctif : `ratio 0.547, sign_p 0.00195` contre `0.543 / 0.00195` publiés.
  **On ne peut le dire que parce qu'il a publié ses VALEURS ABSOLUES** — l'argument le plus concret de
  toute la passe en faveur de cette pratique.
- 5 cas de calibration, dont le **générateur A** (l'instrument peut-il rendre LES DEUX issues ? — non
  établi jusqu'ici ; vérifié). **Cliquet : 80 détectés, 7 calibrés.**

**P2.12 — ✅ FAIT (2026-07-21) — EDR-095 est RÉFUTÉ dans son verdict principal.**
Résultat gravé : **[EDR-DREAM-001](../EDR/DREAM-001_Forced_Dreaming_Harm_Is_A_Birth_Flood_Artifact_Effect_Absent_On_Matched_Cohort.md)**.
Cohorte fondatrice marquée par IDENTITÉ dans `run_era_organ`, 12 seeds, 25 vs 25 par cellule :

| métrique | off | K=8 | ratio | K8>off | `sign_p` |
|---|---|---|---|---|---|
| TOUS *(publiée)* | 29.0 | 13.0 | **0.448** | 0/12 | 0.0005 |
| FONDATEURS *(apparié)* | 35.5 | 54.5 | **1.535** | **8/12** | 0.3877 |

`n_lived` : off 56 / K=8 756 → **×13.4**. Le chiffre publié **se reproduit exactement** : mesure juste
d'une grandeur CONFONDUE, pas erreur de mesure. Sur agents comparables, la pénalité de ~45 % **n'existe
pas** — si le vrai ratio valait 0.448 on attendrait ~0/12 favorables à K=8, on en observe 8/12.
- ⚠️ **Une première correction REJETÉE par moi avant publication** : « les N plus vieux » est biaisé
  (top 26 % vs top **1,6 %** — sélection sur la variable de sortie à quantiles incomparables). Elle
  rendait 1.339 et aurait donné un titre inverse tout aussi faux.
- ⚠️ `sign_p = 0.39` n'établit PAS l'effet inverse, et le record ne l'affirme pas. Il établit l'ABSENCE
  de l'effet publié — une question différente, et décidable à ce n.
- **Nouvelle classe E15** au registre : statistique de population comparée entre populations de
  compositions différentes. **Aucune garde de borne ne voit ça** (aucun bras au plancher/plafond).

*(entrée d'origine)* — Confond `n_lived` d'EDR-095 *(non tranché)*. Le record note lui-même que le rêve
forcé fait passer `n_lived` de ≈74 à ≈1205 (**×16**), en « effet secondaire ». Or `survival_competence`
est la **médiane des âges** sur les agents de l'ère : une population 16× plus nombreuse dont la plupart
naissent tard a des âges mécaniquement faibles. **La baisse de survie pourrait être un artefact de
calendrier de naissance.** Test décisif : restreindre la médiane aux agents nés avant un tick donné, ou
apparier les cohortes sur la date de naissance. *C'est le confond que le backlog soupçonnait ; il n'est
pas dans la fonction de verdict mais dans la GRANDEUR qu'on lui donne.*

**P2.3 — ✅ FAIT (2026-07-21) — `_verdict_decomposition` calibré, et il PASSE.** La crainte (« le
bilinéaire a plus de paramètres et gagne mécaniquement par surajustement ») est **réfutée par mesure** :
sur un système authentiquement linéaire, le fit bilinéaire est **pire que la ligne de base** (1.587 vs
0.000) → `LATENT_LINEAR`. 3 formes livrées (bilinéaire / linéaire / monotonie en le bruit). **La prémisse
de la tétralogie G4 (PLAN-001/002/003/004) survit.**

**P2.4 — ✅ FAIT (2026-07-21) — l'instrument le plus central est calibré, et il PASSE.**
Étalon `world_demand_marker_probe` (DEMANDING = l'obs porte l'info / TRIVIAL = l'obs est un leurre) :
- **DEMANDING → `X_DEMANDED`** : 46.0 → 25.0 (ratio 1.84), `|W| ≈ 35.9` = politique réellement ENTRAÎNÉE.
- **TRIVIAL → `X_DECOY`** : 101.0 vs 101.0, ratio 1.00, `|W| = 0.000`.
- ⚠️ **Mesuré HORS PLAFOND exprès** (`gain < metab`) : aux défauts de l'étalon, les deux bras de TRIVIAL
  sont à **200/200**, le cap — la spécificité y serait démontrée sur une métrique SATURÉE. Régime durci
  → TRIVIAL vit à 101, DEMANDING à 46. C'est une **faiblesse de l'étalon** corrigée dans le cas de test.
- ⚠️ **En TRIVIAL, `|W| = 0.000` est la BONNE réponse**, pas un artefact d'optimiseur (contraste avec
  S2-004) : une politique optimale doit ignorer une obs non informative. Le gel de W y est la
  *conséquence* de la vérité-terrain, pas un plafond parasite.

**P2.4-bis — ⚠️ DÉFAUT DE MA PROPRE GARDE, trouvé en la calibrant (le jour même où je l'ai armée).**
La règle « bras identiques → `INCONCLUSIVE_DEGENERATE` » **bloquait le cas TRIVIAL**, c'est-à-dire la
vérité-terrain qui VALIDE le marqueur. Cause : des bras identiques ont **deux causes opposées**, et deux
tableaux de SORTIES ne permettent pas de les distinguer —
(a) l'intervention ne s'est pas appliquée (S2-007 matrice identité, S2-004 W gelé) → à bloquer ;
(b) elle s'est appliquée et n'a rien fait (l'obs EST randomisée, la politique l'ignore) → **nul légitime**.
Correctif : paramètre **`intervention_verified`** (défaut `False`, conservateur) — l'appelant atteste
avoir vérifié la perturbation de l'**ENTRÉE**, pas de la sortie. *Une garde trop zélée refuse le nul
là où le nul est la bonne réponse.* **Cliquet : 80 détectés, 8 calibrés.**

*(ancienne entrée P2.4, conservée pour le contexte)* **— 78 ✔** (carto 96, déflaté −18). **Dépendants réels : 10, pas 25** —
WARM-004/006/007/008 adoptent la MÉTHODE via `adopts:`, jamais la fonction ; S2-001/LANG-006/G1-001/
MEM-001 sont les **sources** dont le module fut extrait, pas des dépendants. Pur numpy, aucun bail ;
l'étalon est **déjà écrit** (`tools/world_demand_marker_probe.py`, mondes DEMANDING/TRIVIAL).
Dette annexe : l'`adopt_for` de REF-DEMAND-MARKER (19 entrées) est périmé — c'est ce décalage qui a
permis le gonflage.

**P2.5 — `compute_ab_verdict` — 74 ✔** (carto 92, déflaté −18). **19 dépendants réels, pas 32.** Risque
plus faible qu'il n'y paraît : le défaut ne produit que des **faux positifs**, or 13/19 concluent NEUTRE
et les 4 affirmations positives appliquent déjà `sign_p` à la main. ⚠️ **NE PAS MODIFIER** la fonction
(consigne sessions //) — calibration strictement ADDITIVE.

**P2.6 — ✅ FAIT (2026-07-21) — bundle Lewis calibré, 4 cas.** Mappings purs, aucun monde, aucun bail.
- **Générateur A** : les 4 coupables (`THROW` / `BIOLOGIE` / `BRAIN` / `MOUVEMENT`) + la branche diffuse
  sont TOUS atteignables. Un mapping qui ne sait désigner qu'un seul coupable ne diagnostique rien.
- **Frontière `> 0.5` STRICTE vérifiée** : un partage exactement 50/50 rend `DRAIN DIFFUS`, pas un
  coupable — c'est ce qui rend le verdict interprétable.
- **La bascule METABOLISME→CARRY est enfin ASSERTÉE** là où la docstring de `GroundTruthCarryWorld`
  l'annonçait sans jamais la tester : à `gt_carry == gt_metab` → `DIFFUS` ; à ±5 % → le bon coupable.
- **Piège documenté** : `bio_autres` porte les GAINS, n'est pas une cible de tarif, mais entre au
  DÉNOMINATEUR — un revenu important dilue les parts et pousse vers `DIFFUS`. À ne pas lire comme
  « rien ne domine » alors que c'est « un revenu masque ».
**Cliquet : 80 détectés, 10 calibrés.**

**P2.7 — ✅ FAIT (2026-07-21) — rétro-audit livré, 3 défauts trouvés, cause mécanique corrigée.**
Résultat gravé : **[EDR-AUDIT-001](../EDR/AUDIT-001_Retro_Audit_Null_Verdicts_Read_At_A_Bound_And_The_Guard_Is_Now_Armed.md)**.
- **Cause mécanique commune trouvée et CORRIGÉE** : `ablation_verdict` était un pur ratio de médianes
  sans garde de borne — il **produisait** le verdict NUL au lieu de le mesurer. Garde **armée par
  défaut** (décision robla) : `X_DECOY` → `INCONCLUSIVE_DEGENERATE`. `floor=9.0` déclaré dans
  `verdict_demand_marker`. 6 cas de calibration, non-régression 60 tests.
- **S2-004** : 3 cellules sur 4 ont `|W| = 0.0000` — W **gelé à l'init** (`sc > best` strict + score au
  cap). Le corroborant « |W| = 0.000 EXACT » est le zéro de départ. Sa cellule POSITIVE tient.
- **S2-007** : cellule `shift0` = **identité algébrique** (`_model_matrix(0,K) == np.eye(K)`, vérifié)
  → les deux bras calculent la même chose. Condition de nécessité tautologique (E1).
- **S2-006** (`foundational`) : transporte « corps SUFFISANT » du jouet (300/300 infini) vers la
  biosphère (champion mort à 27.5/200). ⚠️ Sa CONCLUSION garde un appui indépendant (cognition-vs-corps,
  BODY 5/5) — c'est la **dérivation** qui tombe, pas le verdict.
- **Négatif méthodologique consigné** : le rétro-audit **n'est pas automatisable de bout en bout**
  (2 échecs de calibration). Le code énumère, le jugement tranche — même partage que E9.

**P2.8 — ✅ FAIT (2026-07-21) — dettes du rétro-audit réglées PAR LA MESURE.**
- **`LinearCognitiveOracle` n'est plus du code mort** : `run_linear_sanity` livré. Mesuré K=12 →
  **oracle 200.0, ratio 14.81, `X_DEMANDED`**. La ligne que S2-011 publiait sans chemin d'exécution
  était **VRAIE** — elle n'avait juste jamais été lancée. *Une dette d'exécution n'est pas une
  présomption de fausseté.*
- **Le plancher de `cog_linear` était FAUX** : mesuré **13.5**, pas « ~7-8 » (importé du régime
  4-directions — classe E8 ; avec `dir ∈ {0,1}` on tombe juste 1 fois sur 2, pas 1 sur 4).
  ⚠️ **Conséquence** : les 3 bras de crédit (7.5 / 7.5 / 8.0) sont **SOUS** le plancher aveugle.
- **Bras « sans crédit » livré** (`use_credit=`) : `use_torch_inworld` était codé EN DUR. Les 3 bras
  reproduisent les chiffres publiés (7.5 / 7.5 / 8.0 vs 8 / 8 / 9).
- **Retriever corrigé dans `run_condition`** (`tools/s2_demand.py`) — la fonction PARTAGÉE, pas seulement
  `s2_demand_ablation` : il tournait pendant toute la simulation de **toutes** les sondes S2.
- **5 tests ajoutés**, dont 2 régressions **anti-code-mort** (un contrôle positif doit rester
  ATTEIGNABLE) + correction d'une égalité stricte de clés qui aurait cassé en silence (`skipif RUN_SLOW`).
- ⚠️ **ANGLE MORT DU CLIQUET trouvé en y tombant** : l'heuristique ne couvrait que
  `run_*_probe|diagnostic|ablation|validation`. `run_linear_sanity` est donc entré **sans que le cliquet
  bronche**. Motif élargi (`sanity|control|oracle|floor|map|sweep`) → **71 → 76 instruments détectés**,
  5 nouvellement VISIBLES. `run_linear_sanity` **calibré** (pas gelé — la discipline s'applique d'abord à
  ce qu'on vient d'écrire) ; les 4 légataires gelés au baseline. **Cliquet : 76 détectés, 4 calibrés.**

**P2.10 — ✅ FAIT (2026-07-21) — `run_cog_demand_map` calibré, et son contrôle NÉGATIF était vide.**
La sonde qui produit le **21.05 d'EDR-S2-009**, restée hors du champ du cliquet à cause du suffixe `_map`.
Re-mesurée au régime **publié** (0.75/12.0, pas les défauts de signature 4.0/6.0) :
- **ON : 200.0 vs 9.0, ratio 22.22, `X_DEMANDED`, non dégénéré** → le contrôle positif est CONFIRMÉ, et
  c'est lui qui porte le verdict de S2-009.
- **OFF : 7.0 vs 7.0 — bras BIT À BIT IDENTIQUES sur les 12 ères** → `INCONCLUSIVE_DEGENERATE`. En OFF,
  `forage_payoff=0` et pas de nourriture cognitive : tout le monde meurt à 7 ticks quoi qu'il fasse. Le
  « ratio 1.00 NEUTRAL » ne montre pas que le marqueur est spécifique, mais que **la métrique est morte**.
- ⚠️ **Portée** : la spécificité du marqueur est établie **ailleurs** (S2-001 monde TRIVIAL, LANG-006
  MI 0.000, MEM-001 — bras où les agents VIVENT et le ratio vaut 1.0). Le verdict de S2-009 tient.
- **La garde armée attrape le défaut sur des données de PRODUCTION**, pas une fixture ; pinée en
  calibration permanente. **Cliquet : 76 détectés, 5 calibrés.**
- **Subtilité d'ordre trouvée en chemin** : `ablation_verdict` teste `n >= n_floor` AVANT la garde de
  dégénérescence → à petit n, des bras identiques sortent `INCONCLUSIVE` (sous-puissant) et non
  `INCONCLUSIVE_DEGENERATE`. Sous-puissance et dégénérescence sont **deux défauts distincts** ; lire le
  champ `degenerate`, pas seulement le verdict.

**P2.9 — ✅ FAIT (2026-07-21) — hypothèse RÉFUTÉE en 30 s de calcul.** « Le substrat torch in-world a-t-il
un coût propre ? » Contraste within-subject sur le SEUL axe substrat (même cohorte fraîche, même monde,
même seed ; on bascule `use_torch_inworld`) : **ON = 7.2, OFF = 7.0**, ratio 0.97 sur 6 ères.
**Basculer le chemin torch ne change rien** → pas de coût de substrat.
L'écart avec le repère oracle-ablé (13.5) est une différence de **POLITIQUE** : un oracle au signal
brouillé émet une direction DÉCISIVE à chaque tick (juste 1 fois sur 2 en 1-bit), un `MambaAgent` à poids
aléatoires fait moins bien. **« Aveugle mais décidé » bat « aléatoire ».**
→ **S2-011 en sort RENFORCÉ** : la cohorte froide n'apprend réellement pas, aucun artefact ne l'excuse.
*Leçon : la piste ouverte le matin même a été fermée le soir pour un coût dérisoire — mesurer d'abord.*

**P2.1 — ✅ FAIT (2026-07-21) — branche `perception` calibrée, la plus vieille dette du cliquet.**
Elle porte les ratios publiés de WARM-001 (1.6→2.1) et WARM-003 (5.04) et n'avait **aucun** cas.
Étalon livré : `GroundTruthPerceptionWorld` + `make_perception_world` (dose = `cog_gain`, revenu corporel
`gt_income` obs-INDÉPENDANT). Sujet : le génome DAgger persisté (`results/warm003_dagger_genome.npz`).
- **inertie** à dose 0 : ratio **0.96** avec métrique VIVANTE (survie 19.5, plancher 9, plafond 200) ;
- **effondrement** à dose 6 : **4.25** (126.5 → 29.8) ;
- **monotonie** 0.96 → 2.64 → 4.25 sur doses 0/3/6.
- ⚠️ **L'étalon a une FENÊTRE, trouvée par échec** : revenu trop bas → la cellule à dose 0 est au
  plancher (inertie indémontrable) ; trop haut → la cellule à dose forte est au plafond (effondrement
  invisible, ratio retombé à 1.06). Point de fonctionnement mesuré : `gt_income = 10.0`.
- ⚠️ **FINDING pour les chiffres publiés** : au-delà de la fenêtre le ratio **REDESCEND** (3.14 à dose 12)
  car l'intact plafonne (~179/200) pendant que l'ablé continue de croître. **Tout ratio de cette branche
  dont le bras intact frôle `max_ticks` est une borne INFÉRIEURE compressée, pas une amplitude** — c'est
  ce que signale le champ `censored`. Même phénomène que la cellule positive de S2-007.

**P2.0-bis — ✅ FAIT (2026-07-21) — `champion_body` enfin gravé : [EDR-S2-012](../EDR/S2-012_Champion_Body_Foundational_Verdict_Finally_Recorded_With_Its_Four_Weaknesses.md).**
Direction CONFIRMÉE (le corps porte la survie, la politique du champion est survival-négative), mais
quatre affaiblissements **re-vérifiés par sonde propre** :
1. **« 5/5 mondes » en vaut 4** — `IndustrialWorld` est un clone de `Biosphere3D` (compteur `pollution`
   jamais lu) et `stoneage` EST `Biosphere3D` ; les deux lignes publiées sont identiques au chiffre près.
2. **Le volet `life_score` tombe à 2/5** sous la fonction `holm` du dépôt (appliquée à la branche survie
   mais pas à celle-ci) : `[0.009,0.038,0.007,0.038,0.025]` → `[0.036,0.076,0.035,0.076,0.075]`.
3. **`p = 0.0025` est le PLANCHER du test** (vérifié : `W=78, p=0.00253` à n=12 en séparation parfaite),
   apparu 10 fois sur 10 → statistique SATURÉE, ne gradue plus rien.
4. **Le bras qui produit le verdict est BETWEEN-subject** (`champion_body` vs `random_action` = génome
   champion vs génomes frais), et le n effectif sur « le corps » est **1 génome** cloné 20×.
+ aucun artefact de run (chiffres non re-dérivables) ; `random_action = 6` exactement sur les 5 mondes.
+ **2ᵉ angle mort du cliquet** : `scan_instruments` ne parcourait que `tools/` → `verdict_cognition_body`
  (`src/seed_ai/s2_stats.py`) était invisible. Scan étendu → **80 détectés, 5 calibrés**.
+ ⚠️ **J'ai amendé mes propres bandeaux** de S2-006 et AUDIT-001, qui citaient « 5/5 » comme appui
  indépendant sans l'avoir vérifié.

**P2.11 — ✅ FAIT (2026-07-21) — le contrôle positif du verdict FONDATEUR passe.**
Grille 2×2 dans le régime `cognitive_demand` calibré, cellule `champion` remplacée par l'oracle (politique
DONT ON SAIT qu'elle utilise sa cognition), génomes tous FRAIS (aucun corps à créditer) :
**oracle 200.0 / actions random 7.0 → verdict `COGNITION`** (`policy` p=0.0025 cliff=1.000 ;
`body` p=1 cliff=0.000).
- **Le verdict BODY de `champion_body` n'est donc PAS une incapacité d'instrument** : il discrimine.
  La moitié NULLE du finding fondateur devient **interprétable** — différence exacte avec WARM-002 et
  S2-006, dont les nuls n'avaient aucun contrôle positif. *« On n'a rien vu » vs « on aurait vu ».*
- ⚠️ Ne corrige AUCUN des 4 affaiblissements de S2-012 : établit la CAPACITÉ, pas l'amplitude.
- ⚠️ **Confirme le point 3 au passage** : même sur 200 contre 7, `p = 0.002526` (plancher) et
  `cliff = 1.000` (plafond). Les deux statistiques SATURENT — elles ne gradueront jamais rien.
- **Premier instrument de `src/` calibré.** Cliquet : **80 détectés, 6 calibrés**.

**P2.2 — Calibrer les instruments suivants par ordre de citation dans le graphe de records.**
`python tools/check_instrument_calibration.py --report` donne la liste (70 non calibrés). Ne PAS viser
l'exhaustivité : viser les **porteurs**. *Coût : ~2 h par instrument.*

**P2.3 — ✅ FAIT (2026-07-22) — hook pre-commit du cliquet de calibration livré.**
`tools/hooks/pre-commit` fait désormais DEUX vérifications indépendantes (records + calibration), chacune
gatée sur ses fichiers stagés, drapeau `fail` partagé. La garde calibration ne se déclenche que quand un
`.py` de `tools/` ou `src/seed_ai/` est stagé (le checker scanne l'arbre entier, pas de `--only`) →
n'ennuie pas les commits de docs seuls. Testé dans les deux sens : un instrument bidon non calibré
**bloque** (exit 1, message actionnable) ; l'arbre propre **passe** (81/12/0 nouveaux) ; un commit
hook-seul **skippe** la garde. Le cliquet ne dépend plus de la discipline — principe transverse n°1
(règle documentée sans application exécutable => violée) enfin fermé pour la calibration comme il l'était
pour les records. *Bypass d'urgence : `git commit --no-verify`.*

**P2.13 — ⚠️ OUVERTE (2026-09-01) — classe E19 : balayer le PAS, et RE-AUDITER au réglage le stock de
conclusions de l'arc BILINEAR / LANG-MEMORY / MEM-PERCEPTION / RETAIN-COMPOSE (tous à `lr=0.02`).**
*Preuve : à protocole identique et n=12, la seule variation de `lr` bascule le verdict d'un record ENTIER*
— `run_retain_compose_diagnostic_probe`, `episodes=600`, `n_agents=16`, `K=6`, `bar=0.3167` :
`lr=0.02` → `learned` **0.173** (verdict `RETENTION`) ; `lr=0.002` → `learned` **0.923** (`INCONCLUSIVE`),
**0/144** chevauchement, 12/12 seeds. Cause : `n_agents` n'est PAS un minibatch (chaque agent a ses propres
`W/U/V/W_bl`, `src/agents/backend_torch.py:85-86`) → **batch effectif = 1**, toléré par les conditions à un
`_step` et divergent sur les deux `_step`.
- **À faire** : (a) tout probe dont le verdict compare des conditions de **profondeur récurrente
  différente** doit exhiber la stabilité de son verdict sur ≥ 1 décade de `lr` ; le critère porte sur
  l'**écart au bras de référence** (flaguer si le balayage le referme de plus de 2/3), **jamais** sur le
  franchissement d'une barre absolue — ce dernier produit un faux positif sur un nul réel (cf. P2.15).
  (b) Re-auditer le stock : les quatre passes de l'arc partagent `lr=0.02`, `n_agents=16` et le même
  substrat torch. **Aucune re-mesure ne doit être extrapolée par raisonnement** (classe E8) : le signe se
  transporte, pas l'amplitude ni le seuil.
- ⚠️ **C'est une occurrence de plus d'E14** (garde jamais rétro-appliquée) sur le stock de conclusions
  ACTIVES, et le cliquet de calibration ne peut pas la voir : il déclare l'instrument couvert
  (`"run_retain_compose_diagnostic_probe": ["*"]`) alors que ses deux cas gelés vivent dans le régime
  facile. **Déclarer la couverture PAR RÉGIME, pas par fonction.**
- *Coût mesuré du balayage-garde : 4 `lr` × 4 seeds × 600 épisodes en condition 1-pas = **92.6 s**
  (1 thread, `torch.set_num_threads(1)`). Coût unitaire 2-pas : 10-25 s par (seed × condition).*

**P2.14 — ⚠️ OUVERTE (2026-09-01) — l'arête `language→memory` est REDEVENUE MESURABLE : sonde à mettre à
niveau, puis mesure d'arête complète.**
*Diagnostic corrigé le jour même, après inspection du code* : ce n'est **PAS** l'artefact E19.
`tools/language_memory_demand_probe.py:134-137` ne sauvegarde que `(CONDITION_GATE, GATE_TARGET)` —
**`BILINEAR` n'est jamais activé** — et `:143` construit `Adam([agent.W])`, **`W` SEUL**. La sonde a donc
mesuré le substrat **PLAIN**, prouvablement incapable de représenter `(q+key)%K` (plafond structurel
**0.3889**, cf. P2.15). **Son verdict NÉGATIF était CORRECT pour son substrat.**
- ⚠️ **Piège à ne pas tomber dedans** : rejouer sa tâche à `lr=0.002` **sur la sonde telle quelle** rendra
  encore le plancher (plain 2-pas mesuré : **0.2180** @ `lr=0.02`, **0.1812** @ `lr=0.002`) et ce négatif
  ne confirmerait RIEN — baisser le pas ne crée pas une capacité absente. Les deux verrous se lèvent
  ENSEMBLE ou pas du tout.
- **Ce qui a changé** : les DEUX verrous ont été levés depuis, et aucun n'existait quand ce record a été
  mesuré. (1) CAPACITÉ — le terme bilinéaire (`EDR-BILINEAR`, 1 pas : plain 0.271 vs bilinéaire 0.932).
  (2) APPRENABILITÉ à 2 pas — `lr=0.002` (`EDR-RETAIN-COMPOSE-LR`). **Combinés sur EXACTEMENT la tâche
  `D=0` de ce record** (encode(key) puis use(q), cible `(q+key)%K`) : **0.923, n=12, 12/12 seeds**. La
  capacité-antécédent déclarée ABSENTE **existe désormais** → le refus de graver est **caduc pour cause de
  substrat**, pas erroné.
- **À faire** : (a) mettre la sonde à niveau — `BILINEAR=True` dans le `try/finally` des flags (l'y AJOUTER,
  le tuple `saved` ne le couvre pas), optimiseur incluant `U/V/W_bl`, `lr` **balayé** (jamais fixé sur le
  bras facile — classe E19) ; (b) mesure d'arête COMPLÈTE avec la méthodologie du graphe : ablation
  **within-subject**, `ablation_verdict`, garde `functional_aliasing` (cette arête ablate le SUBSTRAT, pas
  l'entrée : `n/a` ne suffit pas), n≥12. **Record à part entière**, pré-inscription propre.
- **Enjeu** : ce serait la **3ᵉ arête** du graphe AGI-Taxonomy — la première à avoir été refusée puis
  rouverte par une levée de verrou de substrat.

**P2.15 — ⚠️ OUVERTE (2026-09-01) — DETTE DE SEUIL : la barre `1/K+0.15` est MAL PLACÉE, 0.072 SOUS le
plafond structurel du substrat qu'elle est censée déclarer nul.**
*Preuve, mesurée en forme close* : à `H_in = 0`, le substrat plain se réduit à
`logit_j = σ(W_jj)·tanh(W[key,j] + W[K+q,j])` — transformée MONOTONE d'un score **SÉPARABLE**, donc
prouvablement incapable de représenter `(q+key)%K`. Optimisation directe plein-batch des 36 paires,
8 restarts → **plafond exact 0.3889** ; contrôle positif du même optimiseur sur une table libre non
séparable → **1.000 (8/8)**. Or `bar = 1/K + 0.15 = 0.3167`. **Un substrat prouvablement incapable de
composer peut donc légitimement franchir la barre** : mesuré à `lr ∈ {0.05, 0.1, 0.2}` (0.3625 / 0.3719 /
0.3391) et même au pas d'origine avec 8× de budget (`lr=0.02`, `episodes=2400` → 0.3703, 3/3 au-dessus).
- **Sondes qui héritent du défaut** : `tools/bilinear_composition_probe.py:174` (dont le critère
  `unlocked = plain <= bar and bil > bar` casse par simple allongement du budget) et
  `tools/retain_compose_diagnostic_probe.py:108`.
- **Recommandation** : tout nul revendiqué devrait embarquer son **PLAFOND CONSTRUCTIF** (ici ~72 s de fit
  en forme close) plutôt qu'un seuil absolu — le plafond est invariant au PAS **et** au BUDGET, un seuil
  ne l'est ni l'un ni l'autre. C'est le vrai contrôle négatif.
- ✅ **Ce que cette mesure ne remet PAS en cause** : le résultat phare de BILINEAR (same_tick supervisé,
  plain 0.271 vs bilinéaire 0.932) en sort **RENFORCÉ** — l'argument de séparabilité est confirmé
  quantitativement, et 0.271 est simplement le point sous-entraîné d'une courbe qui sature à 0.389. Ce qui
  est à corriger, c'est sa **marge de décision** (0.271 vs 0.3167 = 0.046), pas sa conclusion.

**P2.16 — ⚠️ TROU CONSTATÉ (2026-09-01) — `tools/check_preregistration_applied.py` n'est branché à AUCUNE
porte du hook.** `tools/hooks/pre-commit` ne contient que **deux** portes (vérifié : `:14`
`check_record_links.py --only`, gatée sur `docs/(EDR|ADR|SDR|REF)/*.md` ; `:31`
`check_instrument_calibration.py`, gatée sur `(tools|src/seed_ai)/*.py`). Le cliquet de l'occ. 4 d'E11 —
celui qui attrape une **DV substituée en silence** dans un record se réclamant d'une règle scellée — n'est
donc exécuté que par son fichier pytest. C'est exactement le principe transverse n°1 (« règle documentée
sans application exécutable finit violée ») appliqué à une garde pourtant déjà ÉCRITE : elle protège le
travail de qui pense à la lancer. *Correctif : une 3ᵉ porte gatée sur `docs/EDR/*.md` stagés. Coût : ~15 min.*

---

## P3 — Générateurs d'erreur encore sans réponse exécutable

*(Classe **E13** du registre — désormais la SEULE sans aucune garde. E11 close le 2026-07-27, ci-dessous.)*

**P3.1 — Pré-enregistrement du plan d'analyse. ✅ CLOSE (2026-07-27).** `tools/preregister.py` +
`tests/sandbox/test_preregistration_guard.py` (6 tests). Scelle *statistique + seuil + critère + **liste
des instruments autorisés*** par un hash : ré-enregistrer un contenu DIFFÉRENT sous le même nom **lève**
(une règle ne se corrige pas — on écrit une `-bis`, ce qui rend le changement VISIBLE), et une édition du
JSON à la main est DÉTECTÉE ; un test balaie `docs/preregistrations/` et tombe si une règle déjà gravée
est retouchée.

*Ce que la fermeture a appris, et qui ne figurait pas dans l'énoncé de la dette* : la forme fuyante d'E11
n'est pas le SEUIL — la discipline manuelle le protégeait déjà (EVO-005, EVO-006) — mais l'**INSTRUMENT**.
Sur EVO-006, la règle était bien pré-écrite, et pourtant la sonde qui a confirmé le verdict a été choisie
APRÈS avoir vu quelle sous-tâche bougeait. D'où la clause `instruments_autorises` dans le format scellé.
Second enseignement, immédiat : **un seuil pré-enregistré n'est valide que pour la tâche sur laquelle il a
été calibré** — le 0.5 d'EVO-005/006 ne sépare plus sur un jeu de sous-tâches en seuils de signe (plancher
du non-lecteur = 0.514), ce qui a exigé une règle `-bis2` dès EVO-007. *Portée honnête : la garde prouve
la NON-MODIFICATION, pas l'antériorité au run.*

**P3.2 — Budget obligatoire, mesuré au smoke.** *Preuve : 3 runs abandonnés (8 h, 4 h projetées, 89 min),
plus WARM-009 nul et un run de 1,8 h sur une question sans objet.* Exiger un débit mesuré sur smoke + un
coût projeté avant tout run long, et **ne pas extrapoler une tendance depuis un préfixe court** (un
transitoire d'apprentissage y ressemble — erreur commise sur la dérive du grab). *Coût : ~1 h.*

**P3.3 — Indépendance des revues.** Les 7 revues ont trouvé du réel, mais ce sont des agents de même
architecture avec les mêmes priors : c'est de l'auto-critique outillée, **pas une réplication**. Piste :
faire re-dériver un résultat porteur depuis les données brutes par un chemin indépendant. *Coût : à cadrer.*

---

## P4 — Science

**P4.1 — Expérience famine (spécifiée, prête).** Seule question ouverte sur quatre records : « le grab
nuit-il quand grabber NOURRIT ? ». Matériel vérifié : `FamineWorld` hérite de `Biosphere3D` (donc porte la
taxe de portage) à `forage_payoff = 3.0` ; **30 champions déjà entraînés** dans
`data/hof_famine_harsh_s{42,43,44}.pkl`. Obstacle identifié : backend **legacy**, donc écrire un
`GrabOffMamba` sur le patron de `PerceptionAblatedMamba` — avec vérification d'aliasing obligatoire et
découplage des DEUX bras. Garde-fous posés : réplication sur les **ères**, contrôle négatif = manipulation
**INVERSE**, `gi` mesuré *in situ*, portée bornée au régime famine dure. *Coût : ~2 h + ~1 h de calcul.*

**P4.2 — Reste du backlog WARM** (cf. `SCIENCE.md`, fil WARM) : incidence du canal né-ON sur ≥6 agents et
≥2 seeds ; hypothèse du **canal porteur** (corrélation coût ↔ poids de W autour du nœud 88) ; bras à
revenu d'inventaire réel ; termes résiduels du bilan énergétique. *Coût : variable.*

**P4.3 — AGI-Taxonomy : graphe de prérequis vers un world-model, dans le format `os-taxonomy`.**
Vision : construire, dans le format de `withmarbleapp/os-taxonomy` (DAG de prérequis à arêtes taggées
`strength`+`reason`, double licence ODbL/CC BY-SA), un graphe dont les nœuds sont des **capacités-demandes
in-world** — chaque arête une claim falsifiable, chaque nœud un critère d'évidence **within-subject**
(`REF-DEMAND-MARKER`), plus rigoureux que les critères humains de os-taxonomy. **Pourquoi** : le verrou du
dépôt est l'OBJECTIF/curriculum, pas le substrat (fil EVO/S2), et la composition ne bootstrappe que sur un
rythme de prérequis observable (KCHAIN) — os-taxonomy est exactement cette forme. Tension à respecter : un
DAG de capacités *sans canal de demande in-world* est le piège « proxy 9 / in-world 0 ». Décomposé en :

- **SP-1 Schéma** — transposer `schema/` + validateurs os-taxonomy en un « capability-demand graph ».
  *Socle réutilisable, faible coût, documentaire.*
- **SP-2 Peupler** — convertir gates G0→G4 + arc EDR + tétralogie G4 en nœuds/arêtes v0 (force = force de
  preuve empirique). Rend le records-graph **prédictif** au lieu de descriptif. *Dépend de SP-1 ; suppose
  la forme validée par SP-3.*
- **SP-2 dette — barre d'émergence NON vérifiée par un validateur (à fermer en itération 2, avant
  accumulation d'arêtes).** La barre « intact VIVANT » (`coord_intact` médian > `1/K + 0.15`), qui distingue
  une capacité réellement émergente d'un artefact de plancher, n'est appliquée par AUCUN outil :
  `ablation_verdict` ne pose que le plancher de dégénérescence `1/K` (plus lâche), et
  `check_agi_taxonomy.validate_edge` ne lit pas du tout `coord_intact`. Chaque future arête dépend donc
  d'un humain relisant les médianes persistées à l'œil. Fix proposé : champ optionnel `coord_intact_median`
  dans le schéma `evidence` de la demande + une vérification dans `validate_edge` contre le plancher
  d'émergence.
- **SP-3 Calibrer — ✅ SPÉCIFIÉ (2026-07-23), maillon discriminant.** Le demand-marker récupère-t-il un DAG
  de prérequis *imposé* (os-taxonomy comme clé de réponse), en no-opant sur les non-arêtes **corrélées** ?
  Go/no-go de toute la vision. Design : `docs/superpowers/specs/2026-07-23-sp3-prerequisite-recovery-calibration-design.md`.
  *Pur numpy, aucun bail, aucun run long — cheap.*
- **SP-4 Forker/publier** — `agi-taxonomy` en fork-schéma, contribuer les critères within-subject en
  retour. *Dépend de SP-1→3.*

---

## Principes transverses à ne pas reperdre

1. **Toute règle documentée sans application EXÉCUTABLE finit violée** — 3 fois en un jour, par moi, par
   le code d'instrument, et par la suite de tests.
2. **Un instrument non calibré ne se contente pas d'échouer : il PRODUIT un résultat** — l'aliasing a
   généré dose-réponse, corrélations et contrôle négatif cohérents entre eux.
3. **Un contrôle qui ne peut pas échouer n'est pas un contrôle** ; le contrôle informatif est la
   manipulation INVERSE.
4. **Réduire le n, jamais supprimer le maillon** — une chaîne causale transporte son signe, pas son amplitude.
5. **Ne pas généraliser depuis un cas saillant** (`agents[0]`, trois cas, une population) — erreur commise
   **trois fois**, y compris par le record qui la dénonçait. Non automatisable : d'où l'obligation de revue.

Cf. `docs/REF/REF-EXPERIMENT-PREFLIGHT.md`, `CLAUDE.md`, `tools/experiment_preflight.py`,
`tools/ground_truth_worlds.py`, `tools/check_instrument_calibration.py`, `tools/sim_session.py`.
