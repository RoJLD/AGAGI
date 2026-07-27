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

> **Discipline** : **6 fois** un signal à peu de seeds s'est évaporé sous puissance (`057/075/082/083/163` ; `077` = réfutation d'hypothèse, mécanique distincte). Cause-racine (diagnostic 2026-07-10) = puissance **RÉACTIVE** (on mesure à n=3-6 → positif → *puis* on double) + la **bande-sur-médiane** de `compute_ab_verdict` est plus permissive que le **test de signe** (explicite `163` : « bande fragile ; le sign-test tranche »). **Règle : aucun verdict POSITIF sous n=12 seeds** (sous 12 = verdict *exploratoire* seulement) ; **`sign_p` prime sur la seule bande-sur-médiane** ; l'effet-taille juge s'il **SURVIT à la puissance** (pas à n=4). *Powerer + auditer le design avant de conclure.*

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

> 📋 **Priorités & dettes (actionnable) : `docs/roadmap/PRIORITES_ET_DETTES.md`** (P0 environnement → P1 dettes →
> P2 calibration → P3 générateurs d'erreur → P4 science). Les leviers WARM ci-dessous sont en P4.2.

### 🧪 Fil WARM — warm-start in-world sous `cognitive_demand` (EDR-WARM-001→006 ; `tools/warmstart_evolution_inworld.py`)

Arc livré : le substrat **imite l'oracle jusqu'à acc 1.000** (001) donc le plafond n'est PAS la capacité ;
l'**évolution W-only** ÉCHOUE (002) — mais ~~sur un paysage de fitness PLAT~~ : **WARM-010 réfute ce
mécanisme**, la fitness récompense densément la compétence partielle (9→200, monotone, 12/12 ères par
marche) ; l'échec est celui de l'**OPTIMISEUR**, pas du monde, et 002 rejoint donc la loi transversale au
lieu d'en être l'exception. Question ouverte reformulée : l'**atteignabilité** en espace génome ; le
**DAgger on-policy** lève l'acc
on-policy 0.73→0.99 et donne le marqueur le plus fort de l'arc (003, ratio 5.04) ; la dégradation avec la
**profondeur récurrente** est réelle mais n'est ni couverture ni précision (004). **WARM-005 amende les
trois premiers** : ~la moitié du déficit de SURVIE venait d'un **canal d'action non supervisé** (`grab`,
nœud 24) bloqué ON qui saignait l'énergie — ablation causale ×2.06 (12/12, sign_p=0.00024) — alors que la
décision était déjà correcte à 98.7 %. **WARM-006 amende à son tour WARM-005 : il n'y a JAMAIS eu de
dérive.** L'agent persisté (`agents[0]`, seed 2026) est **né saturé ON** (grab +0.9626 à zéro pas de
gradient) et n'a pas bougé (Δ = −0.011) ; le « OFF → ON » comparait la **moyenne des 12 agents à t=0**
(−0.2447) au **réplicat unique agent 0 à t=fin** — erreur d'unité d'analyse.

**WARM-007 clôt l'arc, et amende les DEUX précédents.** Le phénomène est **réel et réplique** : causalité
établie **bidirectionnellement** (retirer le grab améliore ; le FORCER dégrade **8/8** non-grabbers,
sign_p = 0.0078), en forward production. **Mais le mécanisme n'était pas le bon** : le grab coûte un
one-shot de −1.0, alors que le vrai puits est la **TAXE DE PORTAGE** (`world_1_stoneage:738-739`,
`energy -= carry_weight*0.5` **à chaque tick, à vie**) = 1.66/agent-tick ≈ **55 % de la marge nette**.
Corollaire vérifié : l'ampleur croît avec la durée de vie de base (ρ = −0.83). **Trois négatifs importants** :
(i) **aucune dose-réponse** au taux de grab n'est établie (intra-répondeurs ρ = +0.09, p = 0.73 — la
corrélation apparente n'était que le contraste zéro/non-zéro) ; (ii) le contrôle négatif « agents qui ne
grabbent jamais » est **TAUTOLOGIQUE** (clamper une action non exécutée est un no-op par construction,
6/8 tableaux bit-identiques) — le vrai contrôle est la manipulation **inverse** ; (iii) **le ×2.06 n'est
pas répliqué** (3000 epochs vs 18 000 ; médiane répondeurs 1.69). WARM-007 réfute aussi la thèse de
WARM-006 « canal fixé par l'initialisation » : |final − birth| médian = **0.557**, le canal est plastique
(l'agent 0 est saturé au plafond de tanh, donc le seul qui ne PEUT pas bouger).

> ⚠️ **Pseudo-réplication : alerte ÉMISE PUIS RÉTRACTÉE (audit fait le 2026-07-20).** J'avais annoncé que
> tout `sign_p` du projet comptant « 12 agents » était invalide. **FAUX** : `ablation_verdict` documente
> son entrée comme « survies appariées par **ère/seed** », et tous les bancs agrègent d'abord les agents
> (`era_survival.append(np.median(ages))` — `s2_demand:56`, `cross_world_transfer:74`,
> `cognitive_demand_inworld:108`, `substrate_world_ab:84`, …), soit **une valeur par ère**, chaque ère
> tirant un monde distinct (`seed_at(seed, i)`) ; `curriculum_transfer:42` dit « ratio par seed ».
> **L'unité de réplication du projet est l'ÈRE/le SEED — le design est sain**, le couplage inter-agents
> (consensus social) étant absorbé dans la médiane.
> **Ce qui reste vrai** : le `sign_p = 1.5e-05` de WARM-007 portait sur **16 AGENTS** partageant oracle,
> augmentation DAgger, optimiseur et mondes (corr inter-agents +0.345/+0.309) → invalide, n indépendant
> ≈ 2. **Défaut local à ce banc, pas de l'idiome.** Aucun audit transversal requis.

**WARM-008 ferme le levier 2 — et son résultat est NÉGATIF.** `aux_off_weight` fait bien ce qu'il prétend
sur le canal (`gi` in-world 0.690 → **0.000**, 4/4 seeds, 39/39 paires réduites) **mais le gain de survie
est MESURÉ NUL** (ratio 1.000, 6 améliorés/6 dégradés) : dans une population **bootstrap-oracle** la taxe
de portage ne pèse que **2.4-9.5 % du métabolisme**, contre le génome **DAgger à inventaire lourd** de
WARM-005/007. **La chaîne causale de WARM-007 ne TRAVERSE PAS les populations** — c'est le vrai résultat.
Trois autres négatifs : « sans coût sur le mouvement » est un **effet de plafond** (32/48 déjà à 1.000 ;
sd(Δ)=0.293 sur les mobiles) ; n indépendant = **4 seeds** (sign_p 0.0625, sous le garde-fou) ; et le banc
`cognitive_demand=True` **coupe tous les revenus d'inventaire** en laissant la taxe → « grab nuit » y est
quasi-tautologique, et la moitié `rub` du correctif y est testée à effet nul.
**Découverte** : le canal « libre » est **fonctionnellement PORTEUR** chez certains agents — `ag04` perd
`move_acc` 0.886 → 0.457, **identiquement sous BCE et sous charnière à gradient nul**, donc le coût n'est
pas optimisationnel. Les nœuds 24/25 sont les unités 88/89 d'un récurrent 172×172, pas des readouts.

> 🔒 **BORNE DE PORTÉE DE TOUT L'ARC (WARM-009, run NUL).** « Le grab nuit » n'est établi que dans un
> monde où grabber **n'a aucun avantage possible** : le banc engendre `stick ×2, stick_short ×3,
> stick_long ×1, rock ×18` et **AUCUN `Fruit`**, alors que le revenu +20 exige `item_type == "Fruit"`
> (`world:746-749`). L'inventaire y est un **coût pur par construction**. Le bras `cognitive_demand=False`
> tenté pour tester la validité externe est **NUL** : les 24 génomes y meurent tous à **6.0-7.2 ticks**
> (plancher de famine), car basculer le flag retire le revenu cognitif sans en activer aucun autre —
> le bras était **structurellement incapable** de montrer que grabber paie (miroir du contrôle
> tautologique : un bras qui ne pouvait pas *réussir*). Drain mesuré ~12.5/tick dans LES DEUX régimes
> alors que `base_metabolism = 0.75` : le flag n'est même pas le terme dominant.
> **La validité externe de WARM-005/007/008 reste OUVERTE.** Le paramètre `cognitive_demand` est livré
> et testé dans le banc (`_torch_survival_eras`, `measure_inworld_grab_rate`) pour le jour où un monde
> à revenu d'inventaire sera utilisé.

**🎯 EXPÉRIENCE SPÉCIFIÉE (prête à lancer, ~2 h construction + ~1 h calcul) — « le grab nuit-il quand
grabber NOURRIT ? »** Reconnaissance faite le 2026-07-20 ; tout est vérifié sauf le run.

*Le matériel existe déjà* : `FamineWorld` (`src/worlds/world_famine.py:30`) **hérite de `Biosphere3D`**,
donc porte la taxe de portage — qu'elle documente explicitement (« coût COMPOSITE = drain de portage réel
`carry_weight×0.5`/tick ») — ET tourne à `forage_payoff = 3.0`, `base_metabolism = 0.25` (`_sweet()` dans
`tools/famine_harshness_probe.py`). Des **champions entraînés dedans sont persistés** :
`data/hof_famine_harsh_s{42,43,44}.pkl`, dict `{version, entries}` avec 10 `AgentSnapshot` chacun
(attribut `.genome`) → **30 génomes, aucun réentraînement nécessaire**.

*L'obstacle identifié* : ce banc tourne en backend **legacy/mamba** (aucun `use_torch_inworld`), donc
l'ablation `_GrabOffTorchPop` livrée pour WARM-007/008 **ne s'y applique pas**. Forcer le forward torch
changerait le calcul sous lequel ces champions ont été sélectionnés — confond à proscrire.

*Ce qu'il reste à écrire* : un `GrabOffMamba(MambaBatchModel)` sur le patron de
`PerceptionAblatedMamba` (`tools/s2_demand_ablation.py:42`) mais clampant la SORTIE 24 sous 0 — avec
⚠️ **vérification d'aliasing obligatoire** (`np.shares_memory`) et **découplage appliqué aux DEUX bras**
si le forward mamba renvoie une vue, leçon non négociable de [[EDR-WARM-007]] ; puis un
`_famine_survival_eras` calqué sur `measure_regime` (n_eras=3, n_agents=12, max_ticks=600).

*Garde-fous du design* : répliquer sur les **ères/seeds** (3 seeds HoF), pas sur les agents ; contrôle
négatif = manipulation **INVERSE** (forcer grab ON), pas les non-grabbers ; mesurer `gi` **dans ce
monde-là**, pas ailleurs. *Portée bornée d'avance* : régime **famine dure**, pas « la production » générique.

> 🛑 **`aux_off_weight` est INTERDIT hors `craft_level=0`, `torch_throw_gate=off`, `explore_eps=0`.**
> Forcer `rub` OFF ferme un gate DUR du craft (`stone_economy:103`) et du feu (`world:1507`) ; grab OFF
> vide l'inventaire (craft impossible même à L0). **Contagion silencieuse** : sans rub → pas de Spear →
> `_throw_kill_tool` (`world:1455,1482`) jamais déclenché → **KPI de l'arc EDR-172→178 à 0 sans erreur**.
> Garde runtime livrée : `assert_aux_off_safe(env)`. Le défaut 0.0 protège le code existant, pas le
> prochain appelant.

**Backlog (ordonné, non démarré)** :
1. Si l'on veut le gain de survie : le **mesurer** sur ≥12 seeds, mondes par agent
   (`seed_at(seed*1000+agent, i)`), sur une population **DAgger** (inventaire lourd) — pas bootstrap.
2. Tester l'hypothèse du **canal porteur** (corrélation coût ↔ poids de W autour du nœud 88).
3. Bras `cognitive_demand=False` : vérifier que supprimer le grab ne détruit pas le revenu-fruit (+20),
   que ce banc annule par construction.
4. **Identifier les termes résiduels du bilan énergétique** — *partiellement répondu* : WARM-007 identifie
   la taxe de portage (~55 % de la marge nette sur le génome DAgger). Reste l'écart `delta_bio(correct)`
   −0.075 contre +0.583 pour l'oracle. Méthode qui a marché : instrumenter `_resolve_biology` DANS le
   monde et comparer poste par poste, plutôt que raisonner sur les instruments d'entraînement.
   ⚠️ Contrainte de design non négociable (leçon 005) : plafonner `max_ticks` pour les traces et réserver
   K=12 au verdict final — quand la survie augmente, les épisodes s'allongent et TOUT le pipeline ralentit
   (3 runs abandonnés : 8 h, 4 h projetées, 89 min).
   *(L'ancien levier 2 « valider `aux_off_weight` bout-en-bout » est CLOS par [[EDR-WARM-008]] : le canal
   est bien annulé, mais le gain de survie est mesuré NUL et le correctif est interdit hors craft_level=0.)*

> ⚠️ **Leçons méthodo transverses de l'arc** (à appliquer hors WARM) :
> 1. Avant d'imputer un déficit de SURVIE à la cognition, vérifier le **bilan énergétique** et les
>    **canaux d'action NON supervisés**.
> 2. **Un contrôle négatif qui ne PEUT pas échouer n'est pas un contrôle** (ablater une action que le
>    sujet n'exécute jamais est un no-op analytique). Le contrôle informatif est la manipulation
>    **INVERSE** : forcer l'action chez ceux qui ne la font pas.
> 3. **Un sham doit reproduire la VOIE de l'artefact suspecté**, pas seulement « ne rien faire » — c'est
>    en clampant un nœud non lu *via la même vue aliasée* qu'on a prouvé qu'un bug était inerte.
> 4. **Vérifier l'aliasing mémoire** (`np.shares_memory`) avant de déclarer une ablation propre :
>    `forward` renvoie une VUE de `H`, donc écrire dans les logits mute l'état récurrent.
> 5. **Ne pas généraliser depuis `agents[0]`** ni depuis quelques cas saillants — c'est la faute commise
>    **trois fois** dans cet arc, y compris par le record qui la dénonçait.
>
> Sur **six** passages en revue adversariale, **six** ont trouvé une erreur réelle (dont un bug
> d'aliasing, une fausse alerte transversale et une inférence réfutée par mesure). Le mécanisme qui les a
> attrapées est la **revue qui lance ses propres sondes**, pas la prudence rédactionnelle.

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
> - **Difficulté de tâche** (`CURR-001`, proxy de `transfer_ratio` Dev #3) : à budget égal, un curriculum
>   facile→plein BAT le tabula-rasa (within ×1.41, zeroshot ×1.84 au-dessus de la chance ; 6000 facile + 6000
>   plein > 12000 plein) — bénéfice plus fort en généralisation. Proxy POSITIF pour Dev #3 in-world.
> - **Prédiction actionnable (in-world)** : un verrou qui *ressemble* à une limite de capacité est
>   probablement une **barrière de bootstrap / de crédit** → (1) tester un **warm-start** (cohorte/gate
>   pré-entraîné, curriculum de coût/social) et (2) soigner le **crédit/objectif** (retour épisodique, critique)
>   AVANT de conclure à l'incapacité. Recoupe le cran 2 B2 in-world (cohorte fraîche éteinte avant l'horizon =
>   cold-start ; `[[torch-inworld-integration-plan]]`).

> 🔑 **Instrument transversal : le témoin causal de « le monde EXIGE-t-il X / X PAIE-t-il » = ablation
> WITHIN-subject de X**, pas l'existence d'un agent qui réussit. Le marqueur **between-subject** (« un champion
> bat un dummy ») FAUX-POSITIVE : un survivant compétent peut exister dans un monde qui n'exige pas X, et gagner
> par un autre facteur. Le marqueur **within-subject** (décorréler X sur le MÊME agent : obs/canal randomisé) ne
> s'effondre que si X est causalement porteur. Corroborant gratuit : le **poids que la politique optimale met
> sur X → 0 EXACT** quand X ne paie pas. Validé par vérité-terrain (mondes DEMANDING vs TRIVIAL) sur 2 modalités :
> - **Perception** (`S2-001`, `world_demand_marker_probe.py`) : ablation obs → demand 5-7× / trivial 1.0× ;
>   between faux-positive 5-7× sur trivial ; corroborant `|W|` 0.996 vs 0.000. Reco : bras d'ablation-perception
>   dans `s2_demand` (verdict CAUSAL).
> - **Communication** (`LANG-006`, porte G3, `language_payoff_probe.py`) : ablation canal → demand 5-7× /
>   trivial 1.0× ; le protocole n'émerge même pas s'il ne paie pas (`MI(m;a)` 1.04 vs 0.000). Reco pour clôre
>   `087` : la tâche in-world doit imposer une **asymétrie d'info**, sinon NEUTRE attendu (structure, pas capacité).
> - **Généralise** à toute capacité (mémoire, anticipation, spécialisation) ; prochaine cible = **G1** (une
>   compétence transférée est-elle causalement réutilisée ?). `[[within-subject-demand-marker]]`.

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

- 🗺️ **Territoires de recherche & convention d'IDs** : `docs/roadmap/SPECIALITES.md` (registre vivant, source de vérité de la spécialisation).

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
