# Priorités & dettes — backlog ACTIONNABLE

> À ne pas confondre avec [`../BACKLOG.md`](../BACKLOG.md), qui est le « someday » aspirationnel.
> Ici : ce qui est **à faire**, dans l'ordre, avec la preuve et le coût.

Établi le **2026-07-21**, à l'issue de l'arc WARM-005→009 et du chantier méthodologique qui en est sorti.
Ordre de priorité **décroissant**. Chaque entrée porte : ce qu'il faut faire, **pourquoi** (avec la preuve),
et le coût estimé.

> Contexte chiffré qui justifie l'ordre : sur cet arc, **7 revues adversariales → 7 erreurs réelles**, et
> **71 instruments détectés, 1 calibré** *(chiffre d'origine, 2026-07-21 ; au 2026-09-01 : **101 détectés, 32 calibrés**, 69 restants — puis CLOS le jour même à 104/105 ; au 2026-09-15 : 234 détectés, 226 calibrés, 2 dettes NOMMÉES — le déficit dominant de ce contexte est donc HISTORIQUE, cf. CLAUDE.md « DETTE CLOSE »)*. Le déficit dominant n'est pas l'honnêteté du compte-rendu
> (négatifs consignés, auto-réfutations écrites, portées bornées) mais l'**absence de calibration** et
> l'**absence d'application exécutable** des règles déjà documentées.

---

## 🧭 2026-09-14 — AUDIT GLOBAL + BRAINSTORM : où nous en sommes, où aller, dans quel ordre

> **Provenance.** Audit du dépôt le 2026-09-08 (16 cliquets verts sur l'arbre entier, suite complète
> 2407 verts / 13 rouges pré-existants — corrigés le 09-09 par P2.54 —, doctor 0 bail / 0 fantôme),
> puis **panel de 7 lentilles indépendantes** (stratège scientifique, réfutateur dédié, débit, instruments
> in-world, ingénierie du dépôt, chercheur extérieur, north-star), **24 candidats** fusionnés, **72
> réfutations** à trois lentilles (périmé-ou-doublon / coût-et-méthode / valeur), 3 juges à pondérations
> opposées, synthèse. **14 candidats sur 24 réfutés à la majorité — dont la recommandation initiale de
> l'orchestrateur** (deux prémisses fausses, cf. « Deux faits neufs »). Direction et décisions validées
> avec robla le 2026-09-14. Ce bloc REMPLACE la lecture stratégique de
> [`SPECIFICATION_10ANS.md`](SPECIFICATION_10ANS.md) (un seul commit, 2026-07-21), archivée de fait ;
> le document vivant reste [`FIL_DIRECTEUR_AGI.md`](FIL_DIRECTEUR_AGI.md).

### État, mesuré

- **La méthodologie est saturée, la science in-world n'avance plus.** Depuis le 2026-09-01 (mesuré le
  09-08) : 26 commits « science » contre 78 « méthodo / fix / docs ». 16 portes, 25 classes d'erreur,
  221 instruments. Le chiffre directeur est INCHANGÉ : **proxy 9 / in-world 0**.
- **Les deux derniers records S2 sont des ARRÊTS** (au contrôle, [[EDR-S2-BLIND-CHAMPION]] ; au smoke,
  [[EDR-S2-SUBJECT-VARIANCE]]). Avec [[EDR-S2-012]] (survie = corps), [[EDR-EVO-004]] (la politique ne
  lit pas l'observation) et [[EDR-HOF-IO-OVERLAP]] (18 logits SONT l'observation), **le champion prod
  stoneage ne peut plus servir de sujet pour mesurer la cognition.**
- **Le point d'appui in-world existe** : [[EDR-S2-009]] a réalisé la recette à trois conditions (oracle 21×
  vs ablé). Mais le crédit n'y « apprend pas à froid » ([[EDR-S2-010]], [[EDR-S2-011]]) — et ce nul est
  le premier des deux faits neufs ci-dessous.
- **Les quatre paris** de SPECIFICATION_10ANS (A tâche-vs-sélection, B modalité, C warm-start, D
  métrique) n'avaient AUCUNE entrée ici depuis le 2026-07-21 ; le doc les appelait « pari central de la
  décennie » et « premier chantier ». Tranchés ci-dessous.

### Deux faits NEUFS (vérifiés dans le code le 2026-09-14 ; écrits nulle part avant)

1. **L'apprenant in-world n'a AUCUN contrôle positif, et les nuls « le crédit n'apprend pas » sont des
   nuls à dose infime.** Le crédit publié passe par un **TD(0) par tick** (`src/worlds/world_1_stoneage.py:1717`,
   `batch_model.learn` à chaque tick ; `src/agents/backend_torch.py:12`, Actor-Critic TD(0)) que S2-010
   §Portée ne nomme pas ; le critic vit sur un nœud `tanh` (`src/agents/backend_torch.py:132`) face à des
   récompenses ≈ −18/tick ; `torch_episode_k = 8` (`src/worlds/world_1_stoneage.py:52`) sur des agents
   qui meurent à 7-9 ticks ; `lr = 0.04` fixe (`src/agents/backend_torch.py:61`), jamais balayé ; et la
   cohorte est RECRÉÉE à chaque ère (`tools/cognitive_demand_inworld.py:147-148`). Le panel a compté
   (scripts de scratchpad, n = 1, NON versionnés — à re-mesurer avant tout record) **≈ 48 mises à jour
   par agent** sur le bras COLD de S2-011, et un apprenant **PLAT** sur 2000 ticks là où deux variantes
   triviales (récompense ×0,05, TD coupé) apprennent. Toute la chaîne « verrou = crédit » (S2-009 §crédit
   → S2-010 → S2-011 → SPÉC §2) repose sur cet apprenant sans réponse connue : classes **E2** (bras qui
   ne peut pas réussir) et **E19** (réglage validé sur le cas facile) candidates. La garde existe déjà
   (`tools/experiment_preflight.py:303`, `assert_verdict_invariant_to_optimizer`) : elle n'a jamais été
   appliquée à l'in-world.
2. **Le CORPS est dérivé des lignes 0-9 de W.** `src/agents/mamba_agent.py:47-50` : `hp_bonus = 10·Σ|W[0:5]|`,
   `inv_capacity = max(3, Σ|W[5:10]|)`, `drain = 1 + hp_bonus/100 + 0,1·inv_capacity`. Donc **toute
   annulation, édition ou amplification de lignes de W est AUSSI une intervention métabolique.**
   `make_blind` (`tools/evo_runs/s2_blind_champion.py:127-131`) annonce « corps, biais et récurrence
   restent identiques » — c'est FAUX par construction : annuler `W[:num_inputs, :]` fait tomber le drain
   (panel, numpy pur : 2,40 → 1,30, −46 %), et les contrôles câblés de SUBJECT-VARIANCE sont morts de
   leur corps (drain 11,0 / 15,0), pas de leur couplage. **Le « +39 % 7/7 seeds » de S2-BLIND et le
   « aucun contrôle positif constructible » de SUBJECT-VARIANCE sont des ARTEFACTS CANDIDATS.** Vérifiable
   à ZÉRO simulation (réponses exactes par la formule) ; `phenotype_of`
   (`tools/evo_runs/evo011_preflight.py:300`) existe déjà et n'est appelé que par EVO-011.

### Direction (décidée le 2026-09-14) — A + B en parallèle, C en réserve

- **A — Calibrer l'apprenant et le corps, PUIS un seul run in-world dont chaque branche a une suite.**
  Pari : « proxy 9 / in-world 0 » est d'abord un défaut d'INSTRUMENT (apprenant sans contrôle positif,
  corps confondu avec la politique), pas un mur. ≈ 15 h d'agent, < 1 h de calcul, puis le run P4.4.
  Sa règle dit explicitement ce qu'il NE tranche PAS : ni LOCK-001 (tâche réactive), ni le pari A2, ni
  le pari C hors tâche réactive.
- **B — Attaquer [[EDR-LOCK-001]] là où il a de la marge : proxy mémoire D = 2, sans monde ni bail.**
  La seule manifestation du mur avec de la marge (D = 0 : 0,744 ; D = 2 : 0,17-0,21 ; contrôle 0,54-0,57).
  Teste directement la prédiction falsifiable de LOCK-001 (amorçage court puis REINFORCE). Tourne en
  fond pendant que A tient le bail `kuzu`. → P4.5.
- **C — Porte IW-1 / IW-2 (demi-lecteur étendu par le crédit, puis transfert zéro-shot avec DV
  cognitive).** Seul livrable lisible de l'extérieur, mais RÉFUTÉ tel qu'écrit par trois lentilles
  (bras pré-mesuré inerte, pré-vol tautologique, IW-2 tautologique par G1-001). Réserve conditionnelle,
  re-spécifiée seulement après les verdicts de P1.6 et P4.4. → P4.6.
- **Les paris, tranchés sur pièces** : **A** est mal posé — ni la tâche ni la sélection ne décident, la
  PORTÉE de l'optimiseur décide ([[EDR-EVO-005]] : un fitness cognitif dense s'arrête sous le plafond
  non-cognitif ; [[EDR-EVO-016]] : 0/12 même quand lire double la vie ; seul le CIBLAGE marche, et il
  fournit la réponse). **B → mémoire / écriture** (D ≥ 1) est l'axe cognitif primaire des trois mois.
  **C** : warm-start = régime standard pour le BOOTSTRAP (6 fils), rétention in-world jamais testée à
  récompense dense — c'est ce que P4.4 mesure, avec le froid comme témoin. **→ TRANCHÉ le 2026-09-14,
  sens défavorable ([[EDR-S2-CREDIT-RETENTION]]) : le crédit publié EFFACE le bassin (36 → 8, 12/12) et ne
  construit rien à froid. Le levier suivant est la RÉCOMPENSE (P4.8), pas le warm-start.** **D** est périmé : la métrique
  de verdict existe et est calibrée (ratio within-subject, plancher chiffré) ; comme FITNESS elle est
  testée et insuffisante (EVO-005). Ce n'est pas le premier chantier.
- **Règle des portes** : « on ne franchit une porte que si la précédente est mesurée » est satisfaite à
  la lettre et vide — G0 est `validated` sur un marqueur between réfuté depuis (S2-001), et G1-G4 ont été
  tentées in-world sur un sujet sans contenu cognitif. La re-sceller (within-subject, contrôle positif
  co-exécuté, plancher de bruit publié) fait partie de P3.5.

### 🧭 2026-09-15 — LA FOURCHE STRATÉGIQUE (à trancher par robla) et le north-star déclaré

> **North-star déclaré par robla le 2026-09-15** : « donner au modèle directement un jeu de logique, un
> nouveau monde, un WSL, un corps robot — et qu'il apprenne tout seul ». C'est l'apprenant ouvert
> général. Ce bloc mesure la distance entre ce but et le VÉHICULE actuel, et inscrit la décision que
> le dépôt ne peut pas prendre seul.

**Distance mesurée par le dépôt lui-même.** Le véhicule = un connectome de ~172 nœuds, REINFORCE
épisodique + TD(0) sans BPTT, UN monde construit à la main. Le graphe dit : la survie seule n'a aucun
gradient cognitif ([[EDR-EVO-016]] : 0/12 même quand lire double la vie) ; le crédit publié EFFACE un
bassin pré-formé ([[EDR-S2-CREDIT-RETENTION]] : 36 → 8, 12/12) et le mur est le MÉCANISME de crédit,
pas la récompense (P4.8) ; cinq leviers de sélection agnostiques réfutés ; **proxy 9 / in-world 0**
inchangé depuis le 2026-07-10. Les résultats POSITIFS les plus forts pointent tous dans la même
direction : **un a priori pré-formé + du gradient** (loi warm-start sur 6 fils, bilinéaire, DAgger) —
c'est la route que prend le champ vers le north-star (pré-entraînement + RL + modèles du monde,
[`REF-DreamerV3-2023`](../REF/DreamerV3_2023.md)), pas celle du connectome évolué sous survie. Sur le
« marché » : AGAGI n'est pas sur celui des modèles de fondation ; il est dans la niche open-endedness /
vie artificielle (lignée NEAT → POET → OMNI-EPIC, dont les REF existent), où les acteurs dotés
travaillent 3-6 ordres de grandeur au-dessus et **avec un LLM dans la boucle** — ici `LLMProposer` est
armable mais son périmètre est **5 paramètres bornés** (`src/metaprog/rsi_loop.py:96`). Visibilité
externe : **zéro preprint** (`grep -rIl "arxiv|publication|paper" docs/*.md docs/roadmap/*.md` ne
touche que ce fichier). Débit : 26 commits science contre 78 méthodo depuis le 09-01.

**P3.7 — ✅ CLOSE (2026-09-16, [`ADR-004`](../ADR/004_fourche_strategique_demande_generee_ou_concue.md)
`status: accepted`) — la fourche : « le monde EXIGE » (thèse fondatrice) vs « la demande est CONÇUE ».**
Tranchée par robla sur sept questions : **branche (b) avec (a) dedans** — AGAGI devient un HARNAIS (génère
des environnements ET des architectures, mesure l'acquisition) pointé sur un modèle À POIDS que robla possède ;
espace d'architectures ouvert sous règle d'entrée (contrôle positif par famille, E2) ; première famille = jeux
de logique VÉRIFIABLES générés par Claude Code sous sandbox + revue humaine ; deux fils (S2 continue sur `kuzu`,
harnais CPU pur) ; preprint MÉTHODO maintenant ; critère à 3 mois = record à trois conditions — sans (ii),
l'ADR est amendé et cette entrée ROUVERTE. Spec : `docs/superpowers/specs/2026-09-16-harness-contracts-design.md`
(contrats Task/Learner, registre de pièces artificiel↔biologique, cellule, premier contrôle positif, plan
12 semaines). Un fait corrigé en conception : le plafond gelé du plain (34/36 = 0,944) DÉPASSE le bilinéaire
(0,932) — la nécessité de `bilinear` ne peut être qu'une nécessité d'ACQUISITION à dose. *(Une session parallèle
avait rédigé un ADR-004 `proposed` le 09-15 ; sa version a été écrasée dans l'arbre par celle-ci — signalé,
fusion à faire si elle est re-fournie.)* *Les trois branches telles qu'elles étaient posées :*
- **(a) Garder la thèse, changer la méthode : la demande est GÉNÉRÉE.** Un LLM propose des mondes/tâches
  (POET/OMNI-EPIC), le marqueur within-subject dit lesquels EXIGENT réellement une capacité. C'est la seule
  branche où « pas dit mais trouvé » reste testable. → P2.66 puis P4.10. Coût : durcir le conteneur
  EDR 044 (jamais livré) + un run multi-seed par proposition.
- **(b) Accepter que la demande est conçue à la main → graver que la thèse est RÉFUTÉE pour ce monde,
  et réorienter AGAGI comme INSTRUMENT** (marqueur de demande within-subject, cliquet de calibration,
  pré-inscription) pointé sur un apprenant CAPABLE, externe au dépôt (modèle pré-entraîné, agent de
  classe Dreamer, ou un agent Claude Code dans un WSL — le cas « WSL » du north-star). Le connectome
  cesse d'être le sujet. Coût : un record de réfutation + une interface `learner` agnostique.
- **(c) Statu quo : continuer les ablations sur le connectome (P4.9…).** Valeur attendue bornée par les
  293 records : la réponse sera « pourquoi REINFORCE sans BPTT n'apprend pas », déjà connue du champ.
**Trois conditions pour qu'UNE branche porte ses fruits (aucune satisfaite aujourd'hui)** : (1) PUBLIER
— l'objet publiable est le cliquet de calibration + le graphe de négatifs contrôlés (ALIFE / GECCO /
ateliers open-endedness), pas un checkpoint ; (2) un LLM dans la boucle comme GÉNÉRATEUR, pas comme
échantillonneur de 5 boutons ; (3) cesser d'élargir le cliquet (saturé) — un commit méthodo seulement
quand un run le demande. Se ferme par un ADR qui nomme la branche.
<!-- closes_when:grep_absent=docs/ADR/004_fourche_strategique_demande_generee_ou_concue.md::status: proposed -->

**P2.66 — ✅ CLOSE (2026-09-22) — `claude_code_llm_fn` : un terminal Claude Code comme `llm_fn` du #8.**
Fait : `src/metaprog/llm_proposer_fn.py::claude_code_llm_fn(binary=None, timeout_s=600, allowed_tools="")
-> llm_fn(prompt) -> str`, quatrième fonction à côté de `anthropic_llm_fn` / `local_llm_fn` /
`scripted_llm_fn`, même contrat. Interface fixée par c9, consommée par propose.py en semaine 5. Prompt
par STDIN (jamais en argument : limite de ligne de commande sous Windows) ; commande `[bin, "-p",
"--output-format", "text", "--allowedTools", allowed_tools]` ; `bin` = `binary`, sinon
`AGAGI_CLAUDE_BIN`, sinon `"claude"` — résolu par `shutil.which` (⚠️ mesuré : sous Windows
`subprocess.run(["claude", …])` ne consulte pas PATHEXT, le shim `claude.cmd` d'npm est invisible sous
le nom nu, 6/8 cas rouges avec la forme littérale) ; `subprocess.run(input=prompt, capture_output=True,
text=True, encoding="utf-8", timeout=timeout_s)` ; timeout -> `TimeoutExpired` REMONTÉE ; exit != 0 ->
`RuntimeError` portant le stderr ; sortie = stdout BRUT (`parse_demand_response` /
`sanitize_demand_params` inchangés) ; aucun secret ; périmètre = PARAMÈTRES JSON (`rsi_loop.py:96`),
aucun code exécuté, raisonnement d'[[EDR-065]]. Tests : `tests/sandbox/test_claude_code_llm_fn.py`
(8 cas, TDD RED->GREEN, faux exécutable = script Python derrière un shim `claude.cmd` / `claude` sh,
PATH RÉDUIT au tmp_path — aucun appel réel, jamais) : texte OK via PATH nu · texte OK via
`AGAGI_CLAUDE_BIN` (avec contraste `FileNotFoundError` sans la variable) · `binary=` prime · exit 3 ->
`RuntimeError` avec stderr · timeout remonté · stdin intact (é/ç/€, plusieurs lignes, égalité exacte) ·
argv exact (`-p`, `--output-format text`, `--allowedTools ""`, prompt ABSENT) · `allowed_tools`
transmis tel quel. Pas un instrument (nom non capté par le cliquet, vérifié : 234 détectés, rien
déclaré). NON branché dans `tools/rsi_demand_loop.py` (semaine 5 de c9). ⚠️ Tant que l'allow-list a
5 entrées, c'est un échantillonneur d'hyperparamètres — la valeur est dans P4.10.
*Brique libre livrée le 2026-09-22 : `proposals_root()` / `proposals_file(*parties)` dans `src/paths.py` — variable `AGAGI_PROPOSALS_ROOT`, défaut `proposals`, jointure `/`, relue à chaque appel, exposée dans `__all__` et `describe()` ; 6 cas dans `tests/sandbox/test_paths.py` (11 → 17 def test), porte `check_data_paths` verte SANS toucher la baseline (44 gelés / 0 nouveau : `src/paths.py` est hors périmètre et le motif ne vise que `data/`, `results/`, `/app/data/`). ⚠️ Ce même motif ne couvre PAS `proposals/` : un littéral `"proposals/x.json"` écrit en dur chez un consommateur passerait la porte — élargir `_EST_DONNEE` impose de re-geler la baseline par un acte explicite, à faire quand la racine porte des fichiers réels.*
Quoi (énoncé d'origine) : une quatrième
fonction dans `src/metaprog/llm_proposer_fn.py`, même contrat `str -> str` que `anthropic_llm_fn`
(`:13`, clé + conteneur jetable) et `local_llm_fn` (`:33`, LM Studio) : `subprocess.run(["claude", "-p",
prompt, "--output-format", "text"], timeout=...)`, outils désactivés côté proposition (`--allowedTools`
vide) ; sortie parsée par `parse_demand_response` → `sanitize_demand_params` inchangés. Test : un faux
exécutable `claude` scripté posé sur le `PATH` du test (aucun appel réel en CI), cas « JSON valide »,
« hors allow-list rejeté », « timeout ». Pourquoi : le terminal est déjà sur la machine, authentifié, et
peut LIRE le dépôt — `context["recent"]` (`rsi_loop.py:69`) devient le graphe entier de records au lieu
des dernières lignes. Sûreté : le périmètre reste des PARAMÈTRES JSON (`rsi_loop.py:96`), aucun code
exécuté → le raisonnement d'[[EDR-065]] tient, pas de conteneur requis. ⚠️ Tant que l'allow-list a 5
entrées, c'est un échantillonneur d'hyperparamètres avec un bon prior — la valeur est dans P4.10.
Coût ≈ 1 h. Preuve : `tools/rsi_demand_loop.py:8` (« ARMER = une seule ligne »).
<!-- closes_when:grep_present=src/metaprog/llm_proposer_fn.py::def claude_code_llm_fn -->

**P5.1 — Preprint MÉTHODO (ADR-004 (i) « preprint maintenant ») — plan, figures F1-F7 et brouillon v0 livrés le 2026-09-16 ; relecture adversariale, cible/langue, annexe et soumission à faire (décision robla).**
Quoi : `docs/preprint/PLAN.md` — titre de travail, thèse (les erreurs qui comptent sont des affirmations produites SANS
mesure, et elles ont une direction : le négatif), six objets publiables avec leur chiffre RECOMPUTÉ et sa commande
(297 EDR dont 2 rétractés et 39 verdicts négatifs ; 234/226 instruments ; 28 classes d'erreur, 23 exécutables ; 17 portes,
22/22 mutants tués ; 58 règles scellées ; plancher de bruit 1,058/0,922), cinq résultats de méthode (biais directionnel,
E19, dose E2, E28, E24) chacun avec record + chiffre + garde, sept figures depuis les artefacts existants, plan des
sections. Fait : `tools/preprint/figures.py` — F1 (dette gelée par commit de la baseline, via `git show`), F3 (bascule E19
sur trois instruments), F4 (dose vs nul, six bras), F5 (E28 avec/sans garde), F6 (cliquet des cliquets, parsé depuis le
rapport), F2 (occurrences DATÉES par classe du registre — jours distincts, première et dernière) → `docs/preprint/figures/*.csv|png` ;
aucune valeur en dur, une source absente est RAPPORTÉE (2 tests). `docs/preprint/DRAFT.md` (v0, ~3 pages, français) : résumé,
trois mécanismes, le registre comme objet, cinq cas (biais directionnel, E19, dose, E28, E24), coût/rendement, limites,
suite — chaque chiffre avec sa source. F7 livrée (per-seed `within_ratio` intact/aveugle de `results/s2_blind_champion.json`
+ bande du no-op exact LUE dans le tableau du record — 4/7 seeds intacts SOUS la bande). Reste : relecture
adversariale du brouillon (les chiffres BOUGENT : recompute le jour J), choix de la cible (atelier open-endedness / ALIFE /
GECCO) et de la langue, annexe = registre. *Coût : agent 1 j ; calcul 0.*
<!-- closes_when:grep_present=docs/preprint/DRAFT.md::status: submitted -->

**P5.2 — Revue adversariale n° 1 de la spec du harnais (lecture seule, sondes rejouées) — trois corrections à porter dans la spec / les contrats avant la semaine 2.**
Quoi : `docs/superpowers/specs/2026-09-16-harness-contracts-REVIEW-01.md`. **R1 (E1)** : le contrôle de spécificité de la
cellule A, `permute_distractor_slot`, permute des ZÉROS (sonde : colonnes 12..58 de l'obs same_tick toutes nulles) — `DECOY`
et « > 0,9 » sont obtenus par construction ; il faut un slot distracteur PORTEUR (one-hot tiré du rng) et une clause de contrat
« l'ablation non mordante change l'observation ». **R2** : la spec ne dit pas qui porte `meta` après `apply` — écrire que
`meta` décrit l'obs ablatée et `target` reste celui de l'intact (sinon (c) refuse toute Task). **R5 (E4)** : `PRIOR_SOLVES
si référence > barre` avec barre = référence + 0,05 ne peut jamais se déclencher (le tabular `oracle_init` ne rendra pas
PRIOR_SOLVES) — comparer à `incapable_ceiling + 2 se`. **R3** chiffré : la bande de bruit d'un ratio à n_eval 640 vaut ±3 %
à p = 0,93 mais ±18 % à 0,27 et ±25 % à la chance — la publier PAR BRAS. **R4, R6** vérifiés sans correction (référence
lr=0 mesurée 0,161 ≈ 1/K ; cellule A → PARTIAL, annoncé). ⚠️ Lu contre le plan d'implémentation de l'autre session (`docs/superpowers/plans/2026-09-16-harness-r1-weeks-1-3.md`, non
versionné au moment de la lecture, 07:00) : R2 et R5 y sont RÉGLÉS ; **R1 y est CODÉ tel quel** (Task 3, `_permute_distractor` sur le slot `[2K:3K]` avec le
commentaire « le slot distracteur est vide : rien n'est détruit ») — à corriger avant la Task 3. *Coût : agent 1 h.* Dépend de : rien.
<!-- closes_when:grep_present=docs/superpowers/specs/2026-09-16-harness-contracts-design.md::REVIEW-01 -->

**P4.10 — Élargir le proposeur de 5 paramètres à l'ÉCRITURE d'une TÂCHE (OMNI-EPIC), sous sandbox + revue
humaine, évaluée par le harnais à trois conditions.** *(Re-spécifié le 2026-09-16 par ADR-004 / spec
`2026-09-16-harness-contracts-design.md` : la première famille est « jeux de logique vérifiables », pas des
mondes ; la génération vit dans `tools/harness/propose.py`, pas dans `rsi_loop.ALLOWED_KINDS` ; pas de
conteneur en v1.)* Dépend de P2.66. Quoi : `claude -p --allowedTools ""` reçoit le contrat Task en prose
(`REF-HARNESS-CONTRACTS`), un gabarit qui passe `assert_task_contract`, les demandes déjà couvertes et les
refus passés ; il rend UN module numpy-only qui passe `validate_code` (AST : `np.random.*`, `global`,
`try/except`, `import src`, `torch` refusés) puis `run_sandboxed` avec un smoke à réponse connue (oracle 1,0 ;
chaque `must_bite` → 1/K ; chaque `must_bite=False` > 0,9 ; oracle décalé → 0,0 — le contrôle positif de
l'INSTRUMENT, zéro entraînement) ; puis **revue humaine** (`accept.py`, seul écrivain du registre, cap 5 en
attente). Chaque Task acceptée est mesurée par `run_harness_cell` (n ≥ 12 seeds, famille E23, plancher de
bruit MESURÉ par second rng d'éval, dose publiée) : elle ne « compte » pour Q7 que si (i) une ablation
`must_bite` sort de la bande de bruit ET (ii) ≥ 1 famille acquiert au-dessus de sa référence lr=0 ET (iii)
une pièce est nécessaire à l'acquisition. Règle à sceller AVANT (`HARNESS-GEN-1`) : sur 20 propositions, ≥ 1
Task qui passe (i)+(ii) sur une capacité ∉ {composition, retention_D1} ou avec des ablations ≠
{permute_key, permute_query} (fuite de réponse : le proposeur peut relire les tâches portées). Les deux
issues nommées : aucune → « un générateur LLM ne trouve pas de tâche exigeante plus vite que la main »
([[EDR-090]] s'étend) ; ≥ 1 → première demande GÉNÉRÉE et non conçue, la thèse survit sous forme générée.
Démarre à la semaine 5, APRÈS la revue adversariale de `HARNESS-R1` (aucune génération sur un instrument non
revu). Learners générés (style ADAS, torch) : HORS v1 — la sandbox ne laisse passer que numpy ; élargir est
une décision de sûreté à part (EDR 044), inscrite comme dette, jamais glissée. Preuves :
[`REF-POET-2019`](../REF/POET_2019.md) ; [`REF-ELM-2022`](../REF/ELM_2022.md) ;
`src/metaprog/secure_sandbox.py:23` (`ALLOWED_MODULES = {"numpy", "math"}`).
<!-- closes_when:path_present=tools/harness/propose.py -->

### Ce qu'on ARRÊTE (chacun avec sa raison)

- **Lire la cognition du champion prod stoneage pour elle-même** (reprise du plan complet
  SUBJECT-VARIANCE par amplification ; question « le chevauchement HoF a-t-il été sélectionné ? » sans règle
  scellée) : la survie y vaut ≈ énergie / drain phénotypique, et [[EDR-EVO-011]] a mesuré que lire COÛTE.
- **Tout run in-world à crédit sans dose publiée ni contrôle positif de l'APPRENANT** : un NON y est
  indiscernable d'un apprenant inerte (fait neuf n° 1).
- **Inférer « NON → pari A2 rationnel »** : A2 est déjà mesuré in-world et échoue (EVO-005, EVO-016).
- **Poser des bandeaux ou des rétractations AVANT le verdict mesuré** (E8) : un bandeau est une
  affirmation, il se grave après la mesure (→ P3.6, subordonnée à P1.6).
- **Nouveaux leviers de sélection agnostiques** (lexicase, QD, POET/UED, spéciation, nouveauté) : cinq
  réfutés (EVO-010/013/014/017/019-020), prédits inertes par l'argument arithmétique EVO-014/018.
- **Baldwin-avec-essais dans le harnais EVO** : bras « Baldwin pur » non constructible (le write-back
  vit dans `forward` à chaque tick), coût réel 24-30 h de calcul. **Iterated learning contre le plafond
  LANG-005** : cible close par le record lui-même, prémisse à `lr = 0,05` jamais balayé (E19).
- **Outillage de boucle et refontes documentaires AVANT le run** (harnais de run en une commande,
  générateur de record, worktree par session, réécriture de SPECIFICATION_10ANS) : le facteur 2 de débit
  est ailleurs (voir leviers) et chaque brique existe déjà (`tools/preregister.py`, `tools/cost_guard.py`,
  `tools/jobs/`, `src/seed_ai/harness.py`).
- **Un RNG dédié pour le no-op de `run_ablation_map`** : un no-op bit-identique ne mesure que le
  déterminisme du harnais ; le plancher RÉEL contre une ablation qui change les actions reste ±8 %. Garder
  P2.41a (bande no-op PUBLIÉE à côté de chaque ratio) — c'est une règle de lecture, pas un instrument.
- **Citer « CI verte » sans périmètre ni `gh run list`** ; committer nu ; emporter le travail non relu
  d'une session parallèle ; recopier un compte au lieu de le recomputer.

### Leviers « plus loin, plus vite, mieux » (mesurés ou déduits du panel)

- **La garde E19 comme test standard de tout NUL sous gradient** — `assert_verdict_invariant_to_optimizer`
  avec la référence oracle du même run, AVANT toute recommandation « le crédit n'apprend pas ». Un nul se
  conteste en ≤ 10 min de calcul au lieu d'un arc de rétractation (RETAIN-COMPOSE-LR : des jours).
- **L'injection à dose connue étendue aux APPRENANTS** (pas seulement aux orchestrateurs) : compteurs
  d'événements d'apprentissage en context manager + variante d'apprenant à effet connu (TD coupé, ×0,05).
  Même technique que P2.44/P2.48 : calibre la couche « mesures → affirmation » à coût nul.
- **Vérification de phénotype en numpy pur AVANT tout sujet W-édité** : `phenotype_of(genome)` en < 5 s,
  sans monde. Aurait évité les deux records arrêtés du 2026-09-08.
- **Réutiliser le bassin persisté** `results/warm003_dagger_genome.npz` (2026-07-19, 59 + 108 dans
  172 : sans chevauchement E24) au lieu de re-DAgger (≈ 90 min/seed ; 12 rounds > 8 h abandonnés).
- **Paralléliser proxy (CPU, sans bail) et in-world (bail `kuzu`)** : deux fils de résultats par semaine
  au lieu d'un — charge machine mesurée avant de citer un coût (E12).
- **Mesurer le coût sur un smoke PAR TYPE d'unité** (torch gelé / torch apprenant / évolution mamba),
  borner en agent-ticks, jamais en secondes.
- **Pousser après chaque commit** et citer « CI verte » avec périmètre : une CI rouge est restée invisible
  deux jours (09-07 → 09-09).
- **Le débit se perd HORS calcul** : scellement → record = 85-114 min pour 9-13 min de run (EVO-026/028),
  23 des 26 `fix` du 09-01 → 09-08 tombent moins d'une heure après le `feat` qu'ils réparent. Ce n'est pas
  le hook (≤ 16 s) ni le calcul.

### Liste PRIORISÉE (rang = ordre d'exécution ; le P dit la nature : P1 avant tout run, P2 dette ou instrument, P3 méthodo, P4 science)

**P1.6 — ✅ CLOSE (2026-09-14, [[EDR-CALIB-LEARNER]]) — rang 1 — Contrôle positif IN-WORLD de l'apprenant torch à dose PUBLIÉE, via la garde E19
existante. PRÉREQUIS scellé du run P4.4.** *(Résidus (i)-(iii) ci-dessous restent ouverts, rattachés à cette entrée.)*
→ **INSTRUMENT LIVRÉ le 2026-09-14, run n = 12 en cours.** `tools/learning_events.py`
(`count_learning_events` : patch de CLASSE restauré en `finally`, bit-identique par défaut — prouvé par
`tests/sandbox/test_learning_events.py`, 9 cas) ; les trois sondes crédit publient leur dose
(`learning`, branche `learning-dose:published`) ; `run_learner_probe` (cohorte IMMORTELLE, DV = taux de
coups par bloc, oracle câblé à 1,0 EXACT, bras `lr=0` sans aucun poids déplacé = plafond de l'incapable
mesuré dans le dispositif, dose = un TD par tick + un épisode tous les 8 ticks, reproductible) et
`learner_verdict` (lève sur entrée absente, `INDETERMINE_HARNAIS` si l'oracle ou la référence sont hors
bornes) sont calibrés (13 cas). Runner `tools/learner_calibration.py` : 6 bras appariés par seed
(oracle / lr0 / natural / lr 0,004 / TD coupé / ×0,05), `declare_design` (unité = seed, famille 2n),
`project_cost` sur une unité MESURÉE, reprise par seed, provenance git, balayage E19 natural-vs-lr_low.
→ **✅ VERDICT GRAVÉ le 2026-09-14 — [[EDR-CALIB-LEARNER]] : l'apprenant tel que publié APPREND à dose
non bornée par la mort.** n = 12 seeds, cohorte immortelle, 2000 ticks : `natural` 0,227 → 0,277 contre
référence lr=0 à 0,126 (= chance), **12/12 seeds au-dessus de la référence appariée, +0,156 (min
+0,068)**, courbe monotone, écart à l'oracle (1,0) INVARIANT au pas (E19). Aucune variante n'est
fiablement meilleure : `lr_low` +0,028 (10/12), `x0.05` +0,024 (8/12), **`td_off` PIRE (−0,046, 2/12)** —
le TD par tick contribue ; l'hypothèse « critic tanh saturé » n'a pas d'effet mesurable. **Les deux
issues nommées d'avance : c'est la première** — S2-010 et S2-011 sont ROUVERTS (bandeaux posés APRÈS
mesure, `corrected_by`), leurs nuls étaient des nuls de DOSE (≈ 48 mises à jour contre 2250 ici).
Deux faits de méthode payés sur ce run : (a) le v1 à recharge d'énergie seule
(`results/learner_calibration_v1_energy_only.json`) perdait la moitié des cohortes apprenantes dès le
bloc 1 (le monde tue DANS le tick) et donnait `x0.05` à 0,390 — **tout l'avantage des variantes était un
biais de survivants** ; v2 = énergie + hp + résurrection intra-tick, cohorte 12/12 dans tous les blocs,
cellule gelée en test (seed 2027) ; (b) **un apprenant meurt ~100× plus qu'un non-apprenant** (126
résurrections par seed pour `natural`, 1 pour lr=0, 0 pour l'oracle) — mécanisme NON établi (candidats :
canaux grab/rub mis à jour par BCE → taxe de portage, lancers entre pairs, riposte du gibier).
**Décision robla (recommandation)** : sceller pour P4.4 l'apprenant tel que publié (`natural`, bit-identique
aux records) ; `lr_low` en bras de sensibilité si le budget le permet ; ×0,05 et TD coupé écartés.
**Résidus (ouverts, rattachés ici)** : (i) mesurer le mécanisme de la létalité des apprenants — ablation
par canal (grab/rub/throw coupés) à cohorte immortelle, 4 cellules × 30 s ; (ii) le garde-fou de bail
de `tests/conftest.py` s'évalue à la COLLECTE : un run lancé après la collecte fait échouer les tests
monde en `ResourceBusy` (5 rouges visibles le 2026-09-14, aucune contamination) — l'évaluer au SETUP
fermerait l'angle mort ; (iii) la sonde ne publie pas la valeur du critic : 56 % des `value_pred`
loggés sous −0,99 pendant le run, bras mélangés — à publier par bras avant de citer.
**Conséquence pour P4.4** : la règle scellée doit PUBLIER la dose (`learning`) et TRAITER la létalité
des apprenants — phase d'apprentissage immortelle puis test de survie mortel, ou DV qui ne confond pas
« apprend » et « meurt en apprenant ». **P3.6 partiellement faite** : bandeaux S2-010/S2-011 posés.
<!-- closes_when:path_present=docs/EDR/CALIB-LEARNER_InWorld_Learner_Learns_At_Unbounded_Dose_The_Published_Nulls_Were_Dose_Bounded.md -->
Quoi : (a) les trois sondes de `tools/cognitive_demand_inworld.py` (`run_credit_probe`,
`run_credit_linear`, `run_warmstart_credit_probe`) publient `n_learn_calls` (TD), `n_episode_calls`,
`n_skip` par raison et ‖ΔW‖ — compteur en context manager posé sur le backend, restauré en `finally` ;
(b) `assert_verdict_invariant_to_optimizer` appliquée à `run_credit_linear` sur la cohorte immortelle
`cog_linear` (déjà outillée : 12-46 s par bras), avec deux variantes d'apprenant derrière flag
bit-identique par défaut : TD coupé (REINFORCE épisodique seul) et récompense ×0,05 (TD conservé,
centré) ; n = 12 seeds, DV = taux de coups et survie, contrôle positif = oracle du même run
(`run_linear_sanity`, déjà calibré). (c) Les deux issues nommées d'avance : une variante apprend → S2-010
/ S2-011 sont ROUVERTS (bandeau APRÈS mesure, P3.6) et « in-world 0 » peut bouger ; aucune n'apprend à
n = 12 → S2-010 / S2-011 sont RENFORCÉS, le run P4.4 devient légitime, et le chantier suivant est le
crédit lui-même (BPTT tronqué, critic centré — fichier partagé). Pourquoi : fait neuf n° 1 ; le pré-vol
(question 1 : les DEUX issues) l'exige pour tout run à crédit. *Coût : agent 4-6 h ; calcul ≤ 10 min.*
Dépend de : rien. **Décision robla à prendre APRÈS le verdict** : quelle variante sceller pour P4.4
(recommandation : TD coupé d'abord ; ×0,05 seulement si TD coupé n'apprend pas à n = 12).
<!-- closes_when:grep_present=tests/sandbox/test_instrument_calibration.py::td_calls -->

**P1.7 — ✅ CLOSE (2026-09-14) — rang 2 — Classe neuve du registre + `assert_phenotype_matched` / ballast : toute édition de
W est AUSSI une intervention métabolique.**
→ **LIVRÉ le 2026-09-14** : classe **E26** au registre (`exécutable`, contre-exemple gelé) ;
`phenotype_of` (formule du monde, promue depuis le pré-vol d'EVO-011 — une seule définition),
`assert_phenotype_matched` (tol EXPLICITE sur le drain, `inv_capacity` exigé égal) et
`ballast_phenotype` (lest EXACT par la diagonale des nœuds d'entrée — canal inerte sur la politique,
prouvé BIT-IDENTIQUE sur 4 ticks du forward legacy ; REFUSE le chevauchement E24, donc le champion HoF
tel quel, et tout corps à réduire) dans `tools/experiment_preflight.py` ; `make_blind` dit désormais
la vérité et `make_blind_ballasted` fournit le sujet du `-bis` (P2.42). 7 tests, TDD
(`tests/sandbox/test_phenotype_guard.py`). **(c) re-lue** : le seul contraste entre sujets de
`run_ablation_map` (réflexe) partage déjà le génome, donc le corps — le confond vit dans les runners
qui passent un sujet ÉDITÉ (`subject=make_blind(...)`) : la garde s'applique là, sur le sujet passé,
pas dans `run_ablation_map`. Résidu rattaché à P2.42/P2.43 : rejouer les deux cellules à corps lesté.
Quoi : (a) classe neuve dans `docs/REF/REGISTRE_ERREURS.md` (prochain numéro libre), énoncée sur le
MÉCANISME (le monde dérive le CORPS des mêmes paramètres que la POLITIQUE) — statut `exécutable`, garde
ET contre-exemples dans la même passe ; (b) promouvoir `phenotype_of` d'`evo011_preflight` dans
`tools/experiment_preflight.py` en `assert_phenotype_matched(subject, reference, tol)` + `ballast(genome,
reference)` (compensation exacte du drain), avec trois cas de calibration à réponse EXACTE par la
formule (champion, `make_blind`, ×3) ; (c) l'appliquer dans `run_ablation_map` UNIQUEMENT aux contrastes
ENTRE sujets (jamais au within, qui compare un sujet à lui-même) ; (d) corriger la docstring de
`make_blind`. Pourquoi : fait neuf n° 2 — deux records arrêtés le 2026-09-08 sont des artefacts
candidats. *Coût : agent 2,5-3 h ; calcul 0 (réponses exactes).* Dépend de : rien.
<!-- closes_when:grep_present=tools/experiment_preflight.py::assert_phenotype_matched -->

**P1.8 — ✅ CLOSE (2026-09-14) — rang 3 — Hygiène minimale qui conditionne la LECTURE du prochain run.**
→ **LIVRÉ le 2026-09-14** : (a) 18 commits poussés le matin, push après chaque commit depuis ; (b) le cliquet
REFUSE toute clause `path_present`/`path_absent` dont le fichier existe ICI sans être SUIVI par git
(`_tracked_by_git`, `git ls-files --error-unmatch` ; hors dépôt : indécidable, pas de refus) — deux
contre-exemples gelés (`test_a_path_clause_on_an_UNTRACKED_existing_file_is_REFUSED`, spécificité hors dépôt) ;
(c) data/articles.json, data/state.json, `tests/test_kuzudb` retirés de l'index et ignorés — écrits par
l'app ou par `test_memory_sync.py`, jamais lus comme fixtures (le backend rend un état par défaut) ;
`frontend/package-lock.json` reste suivi (vrai verrou de dépendances) ; (d) 9 worktrees propres retirés,
`reconcile` (MERGE_HEAD) et `wld-lifescore` conservés, tags `keep/` posés.
Quoi : (a) pousser (18 commits non poussés au 2026-09-14 ; fait le jour même) et pousser après chaque
commit ; (b) `tools/check_backlog_freshness.py` REFUSE toute clause `path_present` dont le chemin est
ignoré par `.gitignore` ou non suivi (`git check-ignore` / `git ls-files`) — contre-exemple gelé : la
clause exacte de `5b0025e` (`data/hof_famine_harsh_s42.pkl`) qui a tenu la CI ROUGE trois pushes
(09-07 → 09-09) pendant que le cliquet passait en local ; (c) `.gitignore` des artefacts RUNTIME suivis
et mutés par l'app et les tests (data/articles.json : +1902 lignes de « Rapport d'Observation » en une
journée ; data/state.json ; le binaire `tests/test_kuzudb`) — après vérification qu'aucun test ne les
lit comme fixture ; (d) `git worktree prune` + retrait des worktrees PROPRES (fait le 2026-09-14, voir
« Décisions ») ; le worktree `reconcile` (170 fichiers sales + MERGE_HEAD) et `wld-lifescore` (1 sale)
sont CONSERVÉS. *Coût : agent 1,5-2 h ; calcul 0.* Dépend de : rien.
<!-- closes_when:grep_present=tools/check_backlog_freshness.py::_tracked_by_git -->

**P4.4 — ✅ CLOSE (2026-09-14, [[EDR-S2-CREDIT-RETENTION]] : ERODE + PAS_APPRIS_FROID) — rang 4 — LE run in-world re-spécifié : `S2-CREDIT-RETENTION` — bassin DAgger persisté ×
{gelé / crédit calibré / froid à dose publiée} dans le monde S2-009, n = 12.**
Quoi : sujet = `results/warm003_dagger_genome.npz` (UNE lignée, `n_lineage = 1` DÉCLARÉ ; bassin
PARTIEL : 35,2 / 200 selon [[EDR-WARM-003]], à citer tel quel — S2-011 posait « survit ~200 sans crédit »
comme précondition, elle est mesurée fausse par [[EDR-WARM-001]] et WARM-003) ; bras appariés par seed :
(a) warm + W gelé (réplique WARM-003 = contrôle positif co-exécuté), (b) warm + crédit CALIBRÉ (variante
scellée par P1.6, cohorte PERSISTÉE entre ères, dose ≥ 300 mises à jour par agent DÉCLARÉE dans la
règle), (c) froid + même crédit, mêmes seeds ; bras optionnel (d) bassin DÉGRADÉ à dose connue + crédit
(contrôle positif du chemin lr > 0). DV = survie médiane par ère (unité = ère/seed), plancher 9,0 (pas
7,0), bande no-op PUBLIÉE (P2.41a), `project_cost` SÉPARÉ par type d'unité, `rounds` plafonné DUR à 6.
Branches nommées d'avance : RETENU / ÉRODÉ (→ échelle de lr, [[EDR-175]] : érosion quand r·P < coût) /
INERTE (→ garde E2 : la fenêtre de 8 ticks ne se déclenche pas sur des agents qui meurent tôt — P1.6 le
vérifie avant). **Ce que ce run ne tranche PAS, écrit dans la règle** : ni LOCK-001 (tâche RÉACTIVE, pas
de dépendance état-interne → sortie), ni le pari A2, ni C hors tâche réactive. Ce qu'il tranche : le
seul maillon jamais mesuré de la chaîne warm-start in-world (tous les verdicts WARM gèlent `lr = 0,0` :
`tools/warmstart_evolution_inworld.py:150,169`). Contrôle positif in-world de P2.43 : un sujet qui
survit EN LISANT, s'il existe à l'issue. *Coût : agent 4-6 h ; calcul 0,5-1,5 h.* Dépend de : P1.6,
P1.7, P1.8.
→ **VERDICT SCELLÉ, LU (2026-09-14)** : règles `S2-CREDIT-RETENTION` (+ `-bis` markup, `-ter` budget), n = 12,
phase 1 IMMORTELLE 2000 ticks (dose 1999 TD/agent, résurrections publiées), phase 2 MORTELLE 200 ticks à poids
gelés. **Bassin gelé 36,0** (WARM-003 : 35,2 — harnais sain) ; **bassin + crédit 8,0** (`d_ba` médiane −28,25,
12/12 négatifs) ; **froid + crédit 7,5** (< plancher 9,0, 0/12 au-dessus de 2×). Le crédit publié EFFACE une
compétence de survie qu'il n'a pas construite et n'en construit aucune à froid : il apprend (CALIB-LEARNER),
et ce qu'il apprend n'est pas la survie. Pari C tranché (défavorable) ; P4.6 (IW-1) CADUQUE (exigeait un bassin
non érodé). Coût : première projection REFUSÉE (unité 675 s vs 136 extrapolés — E12 sur le coût), budget relevé
par sceau `-ter`, réel 190 min ; le runner sauve désormais l'unité AVANT la garde (11 min perdues sinon).
Réserve E6 : entraînement en distribution « bien nourri », test en distribution naturelle.
<!-- closes_when:path_present=docs/EDR/S2-CREDIT-RETENTION_The_Published_Credit_Erases_The_DAgger_Bassin_And_Builds_Nothing_Cold.md -->

**Rang 5 — amendement de P2.43 (2026-09-14)** : re-smoke SUBJECT-VARIANCE à CORPS APPARIÉ (ballast de
P1.7) — 4 cellules × 30 s. C'est le premier contrôle positif possible de `run_ablation_map` sur une
politique qui LIT. Voir l'annotation sous l'entrée P2.43. Dépend de : P1.7.

**P2.59 — ✅ CLOSE (2026-09-15) — rang 6 — Seam de politique sur `run_ablation_map` + réponses connues
sur le corps du champion — et l'attente « lecteur câblé → DEMANDED » est RÉFUTÉE par la mesure.**
**Livré** : `batch_model_cls` (politique du bras intact ; le bras ablaté est
`perception_ablated_variant(cls)`, le no-op `perception_null_variant(cls)` — la MÊME ablation, le MÊME
no-op, au MÊME point, pour n'importe quelle politique ; pour Mamba ce sont les classes historiques,
bit-identiques), `reference_body` (garde E26 `assert_phenotype_matched`, LÈVE avant tout monde),
`between_same_body` (le réflexe du between sur le corps du SUJET — mesuré : réflexe sur corps champion
7,5 / 24,5 ticks d'ère contre 6,0 / 7,5 sur génome frais, le between publié comparait deux CORPS),
`phenotype` et `policy` publiés. Deux politiques câblées sur le corps du champion (`ObsBlindOnBody`,
`ObsReaderOnBody`). **Mesuré, K = 12, stoneage** : aveugle → DECOY, within **1,000 exact**, no-op 1,000
(réponse par construction) ; lecteur-chasseur → DECOY 0,86 *dans* la bande no-op 0,88 ; sous corps
insuffisant (metab 0,5, payoff 3) → **`INCONCLUSIVE_INVERTED` 0,66, hors bande** : lire pour poursuivre
COÛTE la survie (EVO-011 retrouvé par le chemin réel) ; lecteur prudent = chasseur (le signal hostile ne
se présente pas), fuyard = inerte. ⚠️ **Aucune lecture câblée n'est net-positive sur stoneage : le
DEMANDED du chemin réel n'existe pas dans ce monde par défaut** — c'est S2-002/S2-012 par une autre
voie. DEMANDED reste calibré par injection, et la déclaration le dit. ⚠️ Défaut trouvé en calibrant :
le no-op restait une politique MAMBA quand la politique intacte était câblée (0,68 « de bruit » qui
comparait deux politiques) — corrigé par la variante nulle générique. 6 cas gelés
(`tests/sandbox/test_s2_ablation_real_path.py`), 52 s.
*Énoncé d'origine :*
Quoi : `run_ablation_map` accepte un `batch_model_cls` (comme `run_condition` dans `tools/s2_demand.py`)
et se calibre sur son CHEMIN RÉEL génome → politique → monde (aujourd'hui `CALIBRATED` ne contient que
`empty-cohort` et `guard-before-world`, `tests/sandbox/test_instrument_calibration.py`) : un réflexe
câblé sur le corps exact du champion (DECOY attendu), un lecteur câblé sur le même corps (DEMANDED
attendu), no-op publié. *Coût : agent ~3 h ; calcul ≤ 5 min.* Dépend de : P1.7.
<!-- closes_when:grep_present=tools/s2_demand_ablation.py::assert_phenotype_matched -->

**Rang 7 — amendement de P2.46 (2026-09-14)** : câbler `assert_no_io_overlap` (E24) dans les sondes qui
lisent la perception, relire [[EDR-EVO-004]] paire par paire (18 partagées vs 108), bandeau sur les
records `PERCEPTION_DECOY`. Voir l'annotation sous l'entrée P2.46. Dépend de : rien.

**Rang 8 — CI complète : FAIT** par P2.54 (2026-09-09, job `suite-complete` par répertoire, 2597 verts,
25 min 44 s). Reste : mesurer le temps mur sur runner à charge connue avant tout shard.

**P2.60 — ✅ CLOSE (2026-09-15) — rang 9 — Porter EDR-177 / EDR-178 dans HEAD.**
(seconde passe, worktree wf_d544703b-586-1 sur 1e84b827). Porte par FUSION 3-voies (`git merge --no-commit --no-ff keep/edr-177-178-factorial-regime-sweep`, base 111c1c0, `merge-tree` = 39aa160 SANS conflit, +1933/−4) et non par checkout : les 6 gardes E14 en tete et les 5 defauts `seeds=(0,1,2,3,4)` de HEAD dans `tools/torch_throw_gate_inworld_ab.py` sont intacts (grep ligne a ligne), et le banc arrive entier — `compare_factorial`, `_factorial_effects`, mode CLI `TTG_MODE=factorial`, 3 kwargs de `run_arm`, leviers F1/F2/F4 du monde (`_maybe_reseed_spear`/`_carry_weight`/`_throw_advantage`, coexistant avec les compteurs `throw_*` de HEAD), 4 tests de `test_torch_throw_gate_world.py` (10 → 14), `tools/factorial_regime_sweep.py`, 2 tests + 4 plans/specs. Records `docs/EDR/177_*` / `178_*` (gate: G1, comme 175/176) avec note de portage MESUREE ; la note « diff rapporte, pas applique » de la 1re passe (E8) est retiree. Instruments CALIBRES par injection a dose connue, zero simulation (`tests/sandbox/test_edr177_178_calibration.py`, 28 cas, RED 7 → GREEN 28) : `compare_factorial` (garde en tete posee AU portage, defaut seeds 4 → 5 — le tag etait sous le plancher n ≥ 5 de `compute_ab_verdict`, classe E2), `tools/factorial_regime_sweep.py::run_sweep` (qualifie : collision avec `tools/metabolic_cost_sweep.py::run_sweep`, entree legataire qualifiee en place), `_cell0_verdict` (sorti de `__main__`, n ≥ 12 strict, nul sous puissance = NON-CONCLUANT) ; `_factorial_effects` corrige porte 14 (pool vide → `nan`, une seule definition). Cliquet STRICT : 234 / 225 / 3 (0 nouveau). Graphe regenere : 316 records / 433 aretes (+2 en perimetre ; +9 records / +69 aretes HORS perimetre — le JSON de HEAD etait perime) ; SCIENCE.md `records_total=316`, G2 `234/225`. RESTE DEHORS et pourquoi : `run_arm` et les 3 leviers du monde ne sont calibres que par les tests qui SIMULENT ; NON LANCES (un run tient `kuzu`) : `test_torch_throw_gate_factorial.py` ×3, `test_factorial_regime_sweep.py::test_run_sweep_smoke`, les 4 tests fusionnes de `test_torch_throw_gate_world.py` — a rejouer apres le run (`python -m pytest tests/sandbox/test_torch_throw_gate_world.py tests/sandbox/test_torch_throw_gate_factorial.py tests/sandbox/test_factorial_regime_sweep.py`). DETTE RESIDUELLE : `CLAUDE.md:31-32` publie 232/223, reel 234/225 (`check_synthesis_counts` exit 1 sur ces deux seules lignes — fichier non editable par l'agent, a corriger au commit). Le fichier `tests/sandbox/test_edr177_178_calibration.py` est UNTRACKED dans le worktree (hors `git diff HEAD`) : l'ajouter au commit.
<!-- closes_when:grep_present=results/records_graph.json::EDR-177 -->

**P2.61 — ✅ CLOSE (2026-09-15) — rang 10 — Provenance minimale : une évidence citée ne se réécrit plus en silence.**
→ **LIVRÉ le 2026-09-15** : (1) `src/seed_ai/harness.py` — `Harness.__init__` lit la racine par `src/paths.py::results_root()` (`self.results_dir`, porte 12 : zéro nouveau littéral) et DÉCIDE `self.results_path` : si `<results_dir>/<name>_<seed>.json` EXISTE et est SUIVI par git (`_tracked_by_git`, `git ls-files --error-unmatch` interrogé depuis le répertoire DU FICHIER, pas du cwd ; hors dépôt ou git absent = indécidable = chemin nominal), l'écriture part vers `<name>_<seed>_rerun.json` — puis `_rerun2`… si le rerun est lui-même committé, sinon le défaut se reformerait là où on l'a déplacé — et le JSON porte `rerun_of`. `save` n'interroge plus rien : la décision est prise AVANT le run (pas d'E13 fabriqué par la garde). Huit contre-exemples gelés dans `tests/sandbox/test_harness_provenance.py` (dépôt git JOUET dans `tmp_path`, `GIT_*` purgés) : suivi → détourné et évidence bit-identique ; non suivi → écrasé (comportement historique) ; hors dépôt → nominal ; absent → nominal SANS sous-processus ; décision à l'init (git INTERDIT au save) ; rerun suivi → `_rerun2` ; racine absolue `AGAGI_RESULTS_ROOT` interrogée depuis SON dépôt ; `AGAGI_RESULTS_ROOT=tmp_path` sort l'écriture de l'arbre. RED 8/8 avant le correctif — et le dernier cas RED a RÉÉCRIT `results/competence_profile_99240.json` dans le worktree : le défaut, reproduit en direct par son propre test. (2) **11 fichiers de tests basculés** — pas 10 : le `grep -rln 'results/' tests` annoncé ne rend que des commentaires et docstrings, AUCUN de ses 13 fichiers n'écrit ; les vrais écrivains, retrouvés par AST sur les constructions de `Harness(`, sont les tests de fumée qui rejouent le runner RÉEL au seed PUBLIÉ, et ce sont exactement les 11 JSON du git status du 2026-09-14 : `test_competence_profile` (99240), `test_edr107_evolve_nav` (107), `test_edr110_capacity_nav` (12345), `test_edr113_landing` (88113), `test_edr114_reach_oracle` (88114), `test_memory_credit_horizon` (99167), `test_p_reach_deconfound` (99140), `test_qd_tier_rescue` (99260), `test_tom_coordination` (99300), `test_tom_probe` (99280), `test_s2_demand::test_run_s2_smoke_one_world` (2026, le seul cas du fichier sur le VRAI Harness). Chacun pose `AGAGI_RESULTS_ROOT=tmp_path` (un `chdir` casserait leurs chargements relatifs de `data/`) ; les cinq autres appelants de `main()` à sortie suivie (`altar_tool_funnel_0`, `curriculum_transfer_0`, `dream_causal_0`, `dream_distress_0`, `dreaming_probe_0`) faisaient déjà `chdir(tmp_path)`. (3) **Runners SCELLÉS sans tampon `git_sha` + `dirty` : 14 sur 15** (liste par `tools/check_control_family.py::scan_runners`, puis grep) — RAPPORTÉS, non édités → **P2.68**. Portes : calibration, fabricated_defaults, test_census, guard_negative_cases, data_paths, control_family toutes vertes ; backlog_freshness ne signalait que cette fermeture.
Quoi (énoncé d'origine) : `src/seed_ai/harness.py` — `Harness.__init__` (pas `save`, appelé en FIN de run : E13 fabriqué par
la garde) détourne vers un chemin `_rerun` tout `results/<name>_<seed>.json` existant ET suivi par git ;
les tests qui écrivent sous `results/` passent `tmp_path` ; tout runner SCELLÉ tamponne `git_sha` + `dirty` +
sceau de règle dans son JSON. Pourquoi : 11 fichiers `results/*.json` cités par des records sont MODIFIÉS par
la suite de tests à chaque passe (git status du 2026-09-14). *Coût : agent ~3 h ; calcul 0.* Dépend de : rien.
<!-- closes_when:grep_present=src/seed_ai/harness.py::results_dir -->

**P2.62 — rang 11 — ✅ CLOSE le 2026-09-15 — Les APPRENANTS sont des instruments hors périmètre du cliquet.**
Fait : 11ᵉ élargissement de `tools/check_instrument_calibration.py` — motifs `learn*` et `compute_policy_gradient`, **tolérants à l'INDENTATION** : les apprenants sont TOUS des méthodes de classe et tous les motifs précédents sont ancrés `^def` (un motif `^def learn` aurait rendu 0 hit) — 5ᵉ axe de faillibilité de l'heuristique après « ce qu'elle cherche / où / comment elle identifie / sous quels verbes » : à quelle PROFONDEUR. Mesuré avant/après : **227 → 231 détectés** (+4 noms / +12 définitions : `learn` ×5 dans 4 fichiers, `learn_episode` ×2, `learn_episode_bptt` ×1, `compute_policy_gradient` ×4), **221 → 222 calibrés**, collisions 22 → 25 (total réel 295). **4 déclarations CALIBRATED qualifiées** (noms en collision) : `src/agents/backend_torch.py::learn` (7 branches — cas P1.6 de `tests/sandbox/test_learning_events.py` : 1ᵉʳ learn différé, un update par tick, no-op EXACT par défaut, TD coupé → dW=0, dose-réponse ×0,05, lr override ; + `test_run_learner_probe_lr0_reference_moves_no_weight`), `src/agents/backend_torch.py::learn_episode` (3 branches), et les deux wrappers du compteur `tools/learning_events.py::learn` / `::learn_episode` → `learn_episode` ENTIÈREMENT couvert. **3 dettes gelées** dans `tools/instrument_calibration_baseline.json` — la baseline n'est plus vide, première fois depuis le 2026-09-01, et ce n'est PAS masqué : `compute_policy_gradient` (`src/agents/mamba_agent.py` legacy = objet de P3.4 ; `torch_batch_model.py` ; `baseline_models.py` no-op ; `ablation_models.py` délégué), `learn` (`src/agents/backend.py` abstrait + Legacy qui délègue au legacy ; `tools/evo_runs/s2_reward_ablation.py` 2 seams de capture), `learn_episode_bptt`. Témoin : `tests/sandbox/test_check_instrument_calibration_learners.py` (5 cas, RED 4/5 avant, GREEN après) ; porte 2 de `check_gate_mutation.py` : +2 mutations (retrait de chaque motif), **3/3 TUÉES**. Trouvé EN PASSANT et corrigé dans `tools/hooks/pre-commit` : la porte 2 ne se déclenchait **ni** sur sa propre baseline (pas un `.py` — E4 occ.5 rejouée sur une autre porte, invisible tant que la baseline était VIDE) **ni** sur `src/` hors `src/seed_ai` (le 9ᵉ élargissement du checker n'avait jamais été répercuté dans le hook) → regex élargi à `^((tools|src)/.*\.py|tools/instrument_calibration_baseline\.json)$`, baseline stagée seule = run non scopé (modèle porte 1). Ce qui reste OUVERT et MESURÉ : (a) **P3.4** (calibrer le legacy, inchangé) ; (b) étendre les 10 autres motifs aux méthodes = **+12 définitions / 7 noms** (`measure` ×3, `sweep` ×2, `run_seed` ×2, `run` ×2, `run_once`, `run_era`, `assert_isolated`) — chantier à part ; (c) ⚠️ la clause `closes_when:grep_present=tests/sandbox/test_instrument_calibration.py::compute_policy_gradient` de P3.4 se satisfait d'une simple MENTION du nom dans un commentaire — constaté : mon commentaire de CALIBRATED l'a fermée À TORT (rattrapé par `check_backlog_freshness`, commentaire reformulé sans le nom) ; une clause de fermeture par nom nu dans un fichier de tests ne distingue pas « calibré » de « cité » → à durcir (P3.5 hygiène : exiger `::nom` comme CLÉ du dict CALIBRATED, pas comme sous-chaîne).
<!-- closes_when:grep_present=tools/check_instrument_calibration.py::learn_episode -->

**P2.63 — rang 12 — ✅ CLOSE le 2026-09-15 — DÉCIDÉ : basculer `preserve_io_blocks=True` par défaut.**
Quoi : `src/seed_ai/mutation.py:28` passe de `False` à `True` **quand aucun run n'est en vol**
(`python -m tools.jobs.doctor` : 0 bail) ; les baselines qui en dépendent (EVO-023/024 le déclarent déjà
explicitement) sont vérifiées bit-identiques ; test de non-régression. Pourquoi : correctif prêt et validé
neutre depuis le 2026-08-04 (voir « DETTE DE PRODUCTION RÉGLÉE ») ; l'attente était une décision, prise
le 2026-09-14. *Coût : agent 1 h.* Dépend de : doctor à 0 bail.
Fait : bascule à **doctor 0 bail** (après le run P3.4). `False` EXPLICITE reste bit-identique à l'historique :
les deux contre-exemples gelés (`test_flag_OFF_reproduces_the_legacy_defect` × opérateurs découverts,
`test_output_semantics_shift_on_insertion_inside_the_output_block` ~56 %) se rejouent sous `False` ; deux
no-op appariés épinglent que le défaut ON ne désaligne plus rien (0/200 sur le génome câblé, 0/60 par
opérateur). Les runners EVO-024/026/026bis/027/028 le posaient déjà explicitement. 51 tests touchant
`MutationConfig` verts. ⚠️ Toute évolution lancée après ce jour (main_biosphere, evolve_inworld, NAS) tourne
avec l'insertion contrainte à la région cachée — la porte 17 ne verra donc plus de nouveau chevauchement
par cette voie.
<!-- closes_when:grep_present=src/seed_ai/mutation.py::preserve_io_blocks: bool = True -->

**P2.64 — rang 13 — ✅ CLOSE le 2026-09-15 — DÉCIDÉ (P1.4) : ÉPINGLER l'aliasing de production par un test, corriger APRÈS
P4.4.**
Quoi : un test nommé tests/sandbox/test_infra001_aliasing_pinned.py (à créer) qui gèle le comportement
de [[EDR-INFRA-001]] (`world_1_stoneage.py` écrit dans l'état récurrent par la pénalité anti-répétition
et le consensus social) sur les 3 génomes qui diffèrent, avec l'écart mesuré (+37 % sur `agent02`) — pour
qu'il ne dérive pas en silence ; la correction (qui change TOUTES les baselines torch) est reportée
après le run P4.4, sur décision. *Coût : agent 1-1,5 h.* Dépend de : rien.
Fait : `tests/sandbox/test_infra001_aliasing_pinned.py` (4 tests, 16 s, bail libre). ⚠️ Les 6 génomes
d'INFRA-001 (ag00…ag09) ne sont PAS versionnés : l'écart +37 % n'est pas rejouable tel quel — on rejoue le
MÊME dispositif (`_torch_survival_eras`, étalon `GroundTruthCarryWorld`, W gelé, pop nue vs
`_DecoupledTorchPop`) sur des génomes FRAIS seedés : 4 mesurés, **2 diffèrent** (seeds 101 : [50,5 ; 44,5] vs
[47,0 ; 45,5] ; 102 : [14,0 ; 13,5] vs [14,5 ; 12,5]), 2 idem dont un au plancher 9,0. Gelé : le FAIT (survies
différentes sur ces deux génomes), les deux sites d'écriture du monde (pénalité anti-répétition, consensus),
et un no-op apparié (deux passes découplées bit-identiques → l'écart n'est pas du bruit). S'il rougit, c'est
que l'aliasing a été corrigé : mettre à jour INFRA-001 et re-mesurer les baselines torch, en le disant.
<!-- closes_when:path_present=tests/sandbox/test_infra001_aliasing_pinned.py -->

**P2.65 — rang 13 bis — ✅ CLOSE le 2026-09-15 (décision (b) : DÉCLARÉE, `docs/REF/RND_2018.md`) — La CURIOSITÉ (EDR 014) est MORTE sous le backend torch : la brancher ou la déclarer.**
Quoi : `Biosphere3D` publie `curiosity_scale = 2.0` et additionne `curiosity_scale · model.surprise` à la
récompense (`world_1_stoneage.py:1713`), mais `backend_torch.py` n'écrit jamais `surprise` — seul le forward
legacy numpy le pose (`mamba_agent.py:824`). Sous le chemin PUBLIÉ (`use_torch_inworld`), le terme vaut 0 à
chaque tick (mesuré P4.8 : 50 ticks, 200 récompenses bit-identiques à échelle 0 vs 2 ; deux bras sur cinq d'un
design scellé ne pouvaient rien changer, E16 occ. 2 au registre). Toute prose qui invoque la « curiosité »
in-world depuis EDR 014 décrit le chemin legacy. Deux issues : (a) porter la surprise du World Model dans le
forward torch — c'est une EXPÉRIENCE, elle change la récompense du crédit publié ; (b) la déclarer morte sous
torch dans `docs/REF` et retirer le terme de la ligne de récompense (bit-identique). Garde en place :
`preflight_curiosity_dead` (`tools/evo_runs/s2_reward_ablation.py`). Clause de fermeture à poser avec la
décision (a)/(b). *Coût : agent 1 h (b) ; (a) = un run.* Dépend de : P4.8 (résultat).
Fait : (b) **déclarée** dans `docs/REF/RND_2018.md` (la REF qui fonde le terme), section « État dans le dépôt ».
⚠️ Correction de l'énoncé : « retirer le terme de la ligne de récompense (bit-identique) » était FAUX — c'est
bit-identique sous torch seulement ; sous le legacy (`MambaBatchModel.forward` écrit `a.surprise`, ~L826) le terme
vaut jusqu'à +2/tick et TOUT l'arc EVO tourne dessus (P3.4 l'a vu vivre : débordements `surprise[m] = err`). La
ligne reste ; (a) reste une expérience non ouverte, subordonnée au verdict de P4.9.
<!-- closes_when:grep_present=docs/REF/RND_2018.md::MORTE sous le backend torch -->

**P2.70 — rang 21 — ✅ CLOSE le 2026-09-15 (MESURÉ : `SEPARATION_TIENT`, règle `BILINEAR-ALIGNED-R1`) — Reste de P2.15, extrait en entrée OUVERTE (P3.5 b) : le désalignement entraînement/éval de `bilinear_composition_probe`.**
Quoi : `tools/bilinear_composition_probe.py` supervise `out[:, :8]` (`_MOVE_LOGITS`, `src/agents/backend_torch.py:32`,
`:304`) et évalue `argmax` sur `logits[:, :K]` avec K=6 (`:158`) — deux classes distractrices (nœuds 70-71) entrent
dans le softmax d'entraînement et sont ignorées à la mesure : ça ne déplace pas le plafond, mais ça change le
GRADIENT et la comparaison au hasard `1/K` (la barre n'est pas celle de la tâche optimisée). Aligner (softmax sur K)
change les chiffres publiés d'EDR-BILINEAR (plain 0,271 / bilinéaire 0,932) → c'est une RE-MESURE, à décider ; sinon
DÉCLARER l'écart dans la docstring de la sonde (marqueur `DESALIGNEMENT_TRAIN_EVAL`). ⚠️ Vérifié le 2026-09-15 en
extrayant : les deux autres « restes » listés par P2.15 étaient PÉRIMÉS par P2.15 elle-même — (1) le plafond de
`retain_compose_diagnostic_probe` est mesuré par condition depuis le 09-08 (`bar_status = SEPARATES_MEASURED` ;
sa docstring décrivait encore l'ancien contrat, corrigée en HISTORIQUE), (2) l'arête `language→memory` déclare son
plafond 0,1859 depuis le 09-08 (`_LEGATAIRES_SANS_PLAFOND` vide, `tools/check_agi_taxonomy.py`). *Coût : décision ;
si re-mesure, ~1 h CPU.* Dépend de : rien.
Fait : ni décision à l'aveugle ni déclaration seule — MESURÉ. Seam `n_classes` sur `imitate_episode_bptt` (défaut
bit-identique, prouvé : W identique à `n_classes=8` ; à `n_classes=K` les colonnes des deux distracteurs ne reçoivent
PLUS de gradient et seulement elles) et `align_train_eval` sur la sonde ; règle scellée AVANT les cellules (seed 0 =
fumée, exclu), runner `tools/bilinear_aligned_run.py` (design déclaré, famille 48 cellules, tampon de provenance),
**94 s CPU**. Résultat (`results/bilinear_aligned_r1.json`) : aligné, plain **0,284** vs bilinéaire **0,941**, 12/12 —
contre 0,271 / 0,932 publiés ; à lr=0,002 : 0,185 / 0,426. Le désalignement était INERTE pour EDR-BILINEAR ; bandeau
posé sur le record (verdict intact), marqueur `DESALIGNEMENT_TRAIN_EVAL` dans la docstring de la sonde, défaut inchangé.
<!-- closes_when:grep_present=tools/bilinear_composition_probe.py::DESALIGNEMENT_TRAIN_EVAL -->

**P2.71 — rang 22 — ✅ CLOSE le 2026-09-15 — Restes de P2.26, extraits en entrée OUVERTE (P3.5 b) : l'empreinte d'autorat survit à son commit.**
Quoi : `tools/check_staged_authorship` — (a) inscrire le SHA dans l'empreinte après commit (exige un hook `post-commit`,
absent du dépôt) ; (b) retirer l'empreinte quand son travail est committé, pour qu'une empreinte SURVIVANTE signifie
quelque chose ; (c) horodater l'empreinte et AVERTIR quand elle est postérieure à la dernière mtime des fichiers
couverts (« empreinte tardive, `verify` non concluant » — observation du 2026-09-07, bloc ci-dessous). Limite de fond à
ne PAS contourner : le sens B n'est pas décidable sans déclaration. *Coût : agent 1 h.* Dépend de : rien.
Fait : (c) `snapshot()` décide `dirty_at_snapshot` (le fichier diffère déjà de HEAD — décidable, coût nul), l'écrit dans
l'empreinte et AVERTIT sur stderr ; `verify()` qui rougit sur une telle empreinte ajoute « EMPREINTE_TARDIVE possible …
NON CONCLUANTE » et expose `ForeignHunkDetected.dirty_at_snapshot`. La garde ne tranche toujours pas (elle ne le PEUT
pas : « étranger » et « mien, écrit trop tôt » sont le même contenu) — elle l'avoue au lieu de refuser comme si elle
savait. 2 tests appariés (tardive → drapeau + message ; propre → aucun drapeau, verify passe) ; 31/31.
(a) était PÉRIMÉ en l'extrayant : le hook `post-commit` existe (`tools/hooks/post-commit`, P2.26, `declare_head_commit`)
et inscrit le SHA dans `own_commits` quand la session correspond. (b) déclaré INUTILE : une empreinte survivante avec
`own_commits` renseigné signifie déjà « travail committé par moi » ; la retirer effacerait cette information.
<!-- closes_when:grep_present=tools/check_staged_authorship.py::EMPREINTE_TARDIVE -->

**P2.72 — rang 23 — ✅ CLOSE le 2026-09-15 (deux règles scellées, deux addenda dans [[EDR-CALIB-LEGACY-LEARNER]]) — Restes de P3.4 : la courbe de pas du legacy n'est pas tracée, et ce qui TUE ses apprenants n'est pas mesuré.**
Quoi : (a) deux points seulement (lr 0,04 instable : 4 seeds à 0,000 + 1 NaN ; 0,004 : 11/12, 0,446) — ajouter 0,01 et
0,001 au même dispositif (`tools/legacy_learner_calibration.py`, bras `lr_low` paramétrable), 12 seeds, pour dire OÙ
l'instabilité commence (~80 s/cellule → 2 × 12 × 80 s ≈ 32 min sous bail) ; (b) le bras `natural` ressuscite **18 265**
fois par seed (0,76 mort/agent/tick ; lr_low 10 206 ; lr0 1 717 ; oracle 0) — instrumenter la CAUSE de mort dans
`run_learner_probe` (énergie ≤ 0 vs hp ≤ 0 ; projectile d'un pair vs riposte du gibier vs drain), à dose connue par
injection avant tout run (CALIB-LEARNER nomme les mêmes candidats sans les avoir mesurés). Pourquoi : un run MORTEL de
l'arc EVO sous cet apprenant a une dose bornée par sa propre létalité — sans la cause, « meurt en apprenant » reste une
phrase. *Coût : (a) ~35 min calcul ; (b) agent 1,5 h + ~10 min.* Dépend de : rien.
*(Trace :)* (a) lancé le 2026-09-15 ~16:55 — règle `docs/preregistrations/LEGACY-LR-CURVE-R1.json` (lr 0,01 et 0,001 ×
12 seeds, référence lr0 IMPORTÉE par seed de P3.4, quatre branches nommées), runner `tools/legacy_lr_curve.py` (lecture
calibrée sur 6 cas synthétiques, `tests/sandbox/test_legacy_lr_curve.py`), résultats à écrire dans
`results/legacy_lr_curve_r1.json` ; ~35 min sous bail.
✅ **(a) MESURÉ le 2026-09-15 (30 min) : `SEUIL_ENTRE_0001_ET_001`** — lr 0,01 : 0,303, 8/12, 1 effondré ; **lr 0,001 :
0,518 [0,40-0,74], 12/12, 0 effondré, 0 NaN** — mieux que 0,004 (0,446). La courbe est MONOTONE dans le sens du pas
jusqu'au point le plus bas mesuré (0,04 → 0,249 ; 0,01 → 0,303 ; 0,004 → 0,446 ; 0,001 → 0,518), les effondrements
s'éteignent (4 → 1 → 0 → 0) et la létalité aussi (18 265 → 16 067 → 10 206 → 5 817 résurrections) ; le seed NaN de
0,04 apprend à 0,591 à 0,001. Ce n'est pas un seuil, c'est une pente — et le plafond n'est pas atteint (sous 0,001 non
mesuré). Addendum gravé dans [[EDR-CALIB-LEGACY-LEARNER]] ; `results/legacy_lr_curve_r1.json`.
**(b) instrumenté le 2026-09-15** : `_cause_de_mort(agent)` (énergie ≤ 0 / hp ≤ 0 / les deux / `AUCUNE` qui crie sur un
vivant — projectile et drain tuent par l'énergie, riposte du gibier et attrition par les hp) compté AVANT la recharge et
publié dans `run_learner_probe` (`cause_de_mort`) ; cas de calibration à réponse connue. ⚠️ Le run (a) en vol avait chargé
le module AVANT ce patch : il ne porte pas `cause_de_mort` — la mesure viendra du prochain run de la sonde (ou d'un
re-run ciblé de `natural`, ~15 min, à écrire dans `results/legacy_cause_de_mort.json`).
✅ **(b) MESURÉ le 2026-09-15 (`LEGACY-CAUSE-DE-MORT-R1`, 3 bras × 12 seeds, 22,5 min) : `ENERGIE`** — `part_energie` **1,000**
(natural), 0,99994 (lr_low), 1,000 (lr0) ; `part_hp` 0 / 0,00006 / 0 ; `AUCUNE` = 0/36 (instrument sain) ; résurrections
bit-identiques au run principal (déterminisme par seed). La riposte du gibier et l'attrition sont HORS DE CAUSE ; drain vs
projectile d'un pair non départagés (inférence « un drain de 0,75/tick ne tue pas en un tick sous recharge à 30 » notée
comme telle, E8). Reste ouvert, non chiffré : compter les lancers reçus par agent pour départager — nouvelle entrée si
quelqu'un en a besoin. Lecture calibrée : `tests/sandbox/test_legacy_cause_de_mort.py` (5 cas).
<!-- closes_when:path_present=results/legacy_cause_de_mort.json -->

**P2.73 — rang 1 — ✅ CLOSE le 2026-09-15 (a-d faits ; l'arc EVO n'est PAS touché : `wm_resets` = 0 à son régime) — E28 : le World Model par agent DIVERGE et le monde en fait une MORT (`max(0.0, nan)`) — relire tout le legacy du jour sous garde, puis auditer l'arc EVO.**
Quoi : mesuré le 2026-09-15 (`LEGACY-NAN-GUARD-R1` : PAS_NAN ; `LEGACY-WM-GUARD-R1` : **ARTEFACT_WM**, résurrections 18 265 → 139,
0 effondré, 0 NaN, hit_last médian 0,197 à lr 0,04). Gardes posées (`observe_batch`, `compute_policy_gradient`), E28 au
registre, bandeau sur CALIB-LEGACY-LEARNER. À faire : (a) **re-mesurer la courbe de pas sous garde** — règle
`LEGACY-LR-CURVE-R2` (0,04 / 0,01 / 0,004 / 0,001 × 12 seeds), résultats à écrire dans `results/legacy_lr_curve_r2.json`
(~30 min) ; relire les addenda a/b du record et le titre si la lecture change ; (b) le monde fait encore
`max(0.0, energy - brain_cost)` sans vérifier `brain_cost` — poser une garde qui COMPTE (`nan_brain_cost`) au lieu de tuer ;
(c) **auditer l'arc EVO** : tout run legacy avec World Model actif portait cette divergence — quantifier `wm_resets` sur un
run évolutif court (EVO-001/005 régime) avant de relire « les apprenants meurent / l'évolution élague » ; (d) CALIB-LEARNER
(torch) n'est pas touché (torch n'écrit pas `surprise`) — le dire dans son texte. *Coût : (a) 30 min ; (b) 30 min ;
(c) 1 h ; (d) 10 min.* Dépend de : rien.
✅ **(a) MESURÉ (60 cellules, ~45 min + reprise) : `APPREND_QUELQUE_PART`, pas 0,001** — lr 0 → 0,126 (référence sous garde,
6 résurrections) ; 0,04 → 0,197 (9/12) ; 0,01 → 0,209 (8/12) ; 0,004 → 0,310 (9/12) ; **0,001 → 0,449, 12/12, 0 effondré**.
Bandeau correctif final sur CALIB-LEGACY-LEARNER (ce qui tient / ce qui tombe). ⚠️ E13 en passant : la cellule
`lr=0.001|seed=2036` du runner a tourné > 3 h (1,7 Go) avant d'être tuée ; re-mesurée isolément sous `timeout 900`
(`tools/_r2_cellule.py`) en 416 s — le dépassement n'était pas intrinsèque (logger asynchrone ? non tranché) ; règle :
borner CHAQUE cellule dans le runner, pas seulement le total. ✅ **(b)** garde du monde posée (`nan_brain_cost`, compté,
pas facturé ; `tests/sandbox/test_world_nan_brain_cost_guard.py`). ✅ **(d)** note sur CALIB-LEARNER. **Reste (c)** : audit de
l'arc EVO. ✅ **(c) MESURÉ** : `evolve_cognitive` (régime EVO-005, monde MORTEL, legacy) — 3 ères × 30 agents × 120 ticks,
5 ères × 300 ticks, 3 ères × 12 agents × 1000 ticks : **`wm_resets` = 0 dans les trois** (seeds 0 et 1). Le World Model ne
diverge qu'avec des agents qui VIVENT longtemps sous récompense d'énergie accumulée (cohorte immortelle, `cog_gain` +12/tick,
divergence dès le tick ~51) ; au régime évolutif les agents meurent à 7-9 ticks et l'obs ne s'emballe pas. **L'arc EVO n'est
pas touché** ; l'artefact était confiné aux mesures legacy à cohorte immortelle du 2026-09-15 (P3.4, P2.72), toutes relues.
n = 2 seeds, 3 régimes : c'est un audit, pas une preuve d'absence — le compteur `WorldModel.nonfinite_resets` reste publié par
les sondes pour que toute récidive se voie.
<!-- closes_when:path_present=results/legacy_lr_curve_r2.json -->

**P2.74 — ✅ CLOSE le 2026-09-16 — Flake d'ORDRE de la suite complète : `test_flatland_runs_crud` mourait sur « Event loop is closed » (vert en isolation).**
Quoi : la suite complète relancée à bail libre (2 589 passés, 116 sautés, 35 min 41 s, machine à charge non contrôlée — E12 sur le
coût) rendait UN rouge : `backend/app/flatland_server.py::start` prenait `asyncio.get_event_loop()`, qui rend une boucle FERMÉE par un
test précédent du même processus. Fait : une boucle fermée n'est pas une boucle — `is_closed()` → boucle neuve ; témoin
`test_flatland_server_does_not_reuse_a_CLOSED_event_loop` (fermée → neuve ; ouverte → gardée ; thread de simulation non lancé),
vérifié ROUGE sur le mutant sans `is_closed()`. Suite : 33/33 sur `test_backend.py`. Porte 15 le même soir : 15 portes, 22/22
mutants tués. En passant (E12/E13) : `run_learner_probe` poussait un `AGENT_THOUGHT` par agent et par tick dans KuzuDB
(210 243 émissions sur 60 cellules) — logger neutralisé avant la création du monde, comme `_disable_kuzu`. **Bit-identité
VÉRIFIÉE** (seed 2026, lr 0,001, bloc 400 : `hit_rate` 0,20635… et `n_decisions` 4 754 identiques avec et sans logger) et coût
divisé par ~3 (400 ticks : 8 s au lieu de ~25).
<!-- closes_when:grep_present=backend/app/flatland_server.py::is_closed -->

**P2.75 — ✅ CLOSE le 2026-09-16 (décision par délégation de robla, accord agagi-c9 : le fichier est VERSIONNÉ, sha normalisé ce499410b9b2…) — E29 : l'activation du substrat LEGACY est un fichier NON VERSIONNÉ,
réécrit par la boucle métaprog et rechargé à chaque pas — Swish ici, tanh sur un clone, et un sha INCONNU pour
tous les records legacy.**
Quoi (mesuré le 2026-09-16, critique de complétude de la piste biomimétique) : `src/metaprog/sandbox/generated_ops.py`
(Swish x·σ(x)) est écrit par `src/metaprog/compiler.py:35`, ignoré (`.gitignore:72`), supprimé de l'index à d4982b0
(EDR 035), absent de HEAD (`git cat-file -e HEAD:src/metaprog/sandbox/generated_ops.py` échoue), et
`MambaBatchModel.forward` le recharge à CHAQUE pas dès que son mtime bouge (`mamba_agent.py::_get_activation_function`,
appelée aux lignes 575 et 667, dans un `try/except Exception: pass`). Le fichier a été réécrit cette nuit (mtime 01:07).
Fait : (a) EDR-139, l'arc EVO, EDR-135, CALIB-LEGACY R1/R2 ont tourné sous une activation qu'un clone n'a pas ;
(b) un run peut changer d'activation EN COURS ; (c) `check_substrate_pinning` ne connaît que `BILINEAR`.
**Livré dans la même passe** : `mamba_agent.ACTIVATION_PIN` (None = historique bit-identique / "builtin" / sha256
→ `ActivationPinMismatch`), `activation_provenance()` publié dans `regime.legacy_activation` de `run_learner_probe`,
`pinned_activation()` câblé dans `_pinned_substrate` (gèle le hash présent pour la durée du run) ; 13 contre-exemples
`tests/sandbox/test_activation_pin.py` ; classe E29 au registre ; bandeau sur [[EDR-CALIB-LEGACY-LEARNER]].
**DÉCISION (1) prise et livrée** : le fichier est sorti de `.gitignore` et committé — son contenu est IDENTIQUE
(fins de ligne près) à celui supprimé en juillet (d4982b0) : la boucle métaprog réécrit le MÊME Swish depuis EDR-035,
donc versionner ne fige rien qui bougeait, et toute dérive future se VOIT dans `git status`. `versioned` est désormais
MESURÉ par `activation_provenance()` (git ls-files ; `None` si git absent, jamais un False fabriqué) ; le sha du pin
normalise CRLF→LF (le même fichier vaut le même hash sur cette machine autocrlf et sur un clone LF) ; cliquet :
`test_le_fichier_d_activation_du_depot_est_VERSIONNE` rougit si quelqu'un le re-ignore. `ACTIVATION_PIN` reste `None`
par défaut (bit-identité avec les records du 2026-09-15). Le sha sous lequel R1/R2 ont tourné n'avait pas été
enregistré ; celui du fichier versionné est ce499410b9b2de518c1cb18de0a64cd8657f459eda320e2060a1834c7643a230.
Reste hors périmètre (dette, pas décision) : faire publier `legacy_activation` par les runners `evo_runs/`.
<!-- closes_when:grep_absent=.gitignore::\nsrc/metaprog/sandbox/generated_ops\.py\n -->

**P2.76 — ✅ CLOSE le 2026-09-16 — E19 occ. 7 : sous torch in-world le pas EFFECTIF par agent est lr/B — « 0,04 »
à B = 12 vaut 0,0033 ; aucun record ne le disait, et deux backends étaient comparés « à lr égal » avec un facteur 12.**
Quoi : `TorchPopulationModel` porte un W (B, N, N) DISJOINT par agent, `_td_update` MOYENNE la perte sur B
(`backend_torch.py:219-221`), SGD (`:117`) — le 1/B ne s'annule pas (il s'annulerait sous Adam). `count_learning_events`
posait `LR_ACTOR = lr` legacy (par agent) ↔ SGD `lr` torch (/B) comme équivalents (`learning_events.py:189-192`) :
le couple E19 {0,04 ; 0,004} de P1.6 vaut {0,0033 ; 0,00033} par agent, et « le legacy à 0,004 bat torch à 0,04 »
(CALIB-LEGACY) compare 0,004 à 0,0033. **Vérifié par PRÉDICTION, pas par lecture** : le même agent, en population
de 1 et de 12 copies, sous la même transition, bouge 12,000× moins à B = 12 (`tests/sandbox/test_torch_effective_step.py`,
4 cas ; un `.sum()` ou Adam le rougit). Livré : `TorchPopulationModel.effective_lr_per_agent`,
`summary()["lr_effective_per_agent"]` + `lr_effective_unit` publiés à côté du `lr` nominal dans tout bloc `learning` ;
registre E19 occ. 7 ; bandeau sur [[EDR-CALIB-LEGACY-LEARNER]] (chiffres inchangés, lecture comparative changée).
Ce que ça NE dit pas : quel pas est « bon » — seulement que deux règles comparées « au même lr » ne l'étaient pas.
<!-- closes_when:grep_present=tools/learning_events.py::lr_effective_per_agent -->

**P2.77 — ✅ CLOSE le 2026-09-16 — Les fixtures et docstrings gravaient encore « plafond 0.3889 / substrat PROUVABLEMENT
incapable », rétracté deux fois (0,8333 le 2026-09-07, puis 34/36 = 0,944 MINORANT le 2026-09-08).**
Quoi : 7 sites hors records affirmaient encore la version du 2026-09-02 comme un fait —
`tests/sandbox/test_experiment_preflight.py` (3 : la réponse connue n°2 de la garde E19 décrite comme « nul STRUCTUREL »,
la fixture `_P215_CEIL`, le contre-exemple P2.15), `tests/sandbox/test_instrument_calibration.py` (2),
`tests/sandbox/test_agi_taxonomy_gate.py` (1), `tools/experiment_preflight.py` (1), `tools/bilinear_composition_probe.py`
(docstring de `_resolve_ceiling`), `CLAUDE.md` (description de `check_bar_separation`). Les CHIFFRES (0,3141 / 0,3719 /
0,966 ; barre 0,3167 ; fixture 0,3889) sont des mesures ou des fixtures et restent tels quels — les gardes n'ont jamais
vérifié la VALEUR du plafond, elles exigent sa provenance ; leur LECTURE change : un nul d'APPRENABILITÉ à budget
fixe, jamais un nul de capacité ; « un bras qui n'a pas appris franchit la barre », jamais « un bras prouvablement
incapable ». Les records gardent leur texte d'époque (historique) ; `plain_substrate_ceiling.py` et le backlog
portaient déjà la rétractation. 103 tests des fichiers touchés passent (12,8 s).
<!-- closes_when:grep_present=tests/sandbox/test_experiment_preflight.py::CORRECTION 2026-09-16 -->
**P2.78 — rang 14 ter — ✅ CLOSE le 2026-09-22 (session loop 766eabae ; entrée ouverte par la session P4.9) — la garde de QUEUE porte sur le temps CPU du processus  le temps mur est publié À CÔTÉ  jamais à la place ; `Stopwatch` pour les runners.**
Fait : `tools/cost_guard.py` — `CostGuard(clock=time.process_time  wall_clock=time.monotonic)` : `tick()` lève sur le CPU
(`clock` reste l'horloge GATÉE  injectable : les cas existants sont inchangés)  `spent_wall_s` et `report()` publient le mur
et `wall_over_cpu` (machine endormie ou contention = ratio ≫ 1  LISIBLE  plus tueur) ; `CostExceeded` dit le mur à côté du CPU ;
`Stopwatch().elapsed()` rend `elapsed_s` ET `elapsed_cpu_s` (+ ratio  `None` à CPU nul — pas de ratio fabriqué). 4 cas neufs
(`tests/sandbox/test_cost_guard.py`) : défaut = `process_time` ; une suspension (mur 5000 s  CPU 5 s) ne tue PAS l'unité et se lit
dans le rapport ; ratio seulement sur une garde CPU ; `Stopwatch` prédit le ratio exactement. Seconde occurrence mesurée le
jour même  qui a motivé la fermeture : `results/s2_blind_champion_decomp_r1.json` publie `_cout_s` = 510 334 s (5 9 jours de mur
à travers une veille machine) pour 14 cellules que le `-ter` a faites en 1 039 s — annoté dans le JSON (`_cout_note`)  le coût CPU
n'est pas mesuré. ⚠️ Deux limites dites dans le module : `process_time` ne compte que CE processus (un parent de pool de workers
a un CPU ~0 → garde qui ne peut pas échouer, E1 : passer `clock=time.monotonic`) ; une contention gonfle le mur sans le CPU et
n'est plus attrapée par la garde de queue — elle se lit ; (c) `process_time` somme TOUS les threads : un run torch multi-thread publie
`_cout_cpu_s` 2 142 s pour `_cout_s` 1 191 s (TD-STEP-PILOT-R2, mesuré), donc `wall_over_cpu` < 1 — le budget CPU d'une unité vaut
~ threads × mur, à connaître avant de fixer `budget_s`. **Reste, par runner (recommandation, pas une clause)** : publier
`elapsed_cpu_s` à côté de `elapsed_s` via `Stopwatch` dans les 9 runners qui n'écrivent que `time.time()` (les trois miens compris :
`td_step_pilot`, `bilinear_sham_run`, `s2_blind_champion_bis`).
Énoncé d'origine : `project_cost` / `CostGuard` mesurent du temps MUR : une cellule de P4.9 a duré 33 060 s (9,2 h) sans qu'on
puisse dire si la machine calculait ou dormait.
Quoi : `results/s2_credit_ablation.json` → `arms.b_zero.2029.elapsed_s` = 33 060 s contre 26 à 3885 s pour les 59
autres cellules (total hors cellule 7699 s, DANS la projection de 20 007 s ; réel publié 40 759 s = 11,3 h, sous le
budget scellé de 16 h). Le run a traversé la nuit du 15 au 16 : suspension de la machine ou contention, le chiffre
ne le dit pas. `tools/cost_guard.py` (`project_cost`, `CostGuard`) et les runners (`elapsed_s` = `time.time()`)
ne publient que du temps mur. Faire publier À CÔTÉ le temps CPU du processus (`time.process_time()`) par bras et
par run (`elapsed_cpu_s`), et faire porter la garde de QUEUE (`CostGuard.tick`) sur le temps CPU, pas sur le mur —
une suspension ne doit ni tuer un run ni gonfler un coût publié. Un chiffre de coût mesuré sur une machine dont on
ne connaît pas l'état est la classe E12 appliquée au coût (CLAUDE.md § Calibration). *Coût : agent 1 h ; calcul
0.* Dépend de : rien.
<!-- closes_when:grep_present=tools/cost_guard.py::process_time -->

**P2.79 — ⚠️ OUVERTE (2026-09-22, décision de robla en attente) — « gitdata » : faut-il un gestionnaire de données
versionnées (DVC ou équivalent) PAR-DESSUS `src/paths.py`, ou rester à git ?**
Quoi : le 2026-09-09 robla a demandé « un gitignore pour les datas, un gitdata » pour héberger les données sur un NAS
plutôt que dans le code. Tranché ce jour-là : indirection `src/paths.py` (AGAGI_DATA_ROOT / AGAGI_RESULTS_ROOT /
AGAGI_DB_ROOT, relues à chaque appel) + porte 12 (`tools/check_data_paths.py`, baseline gelée) ; la base kuzu reste
LOCALE et se sauvegarde vers le NAS. NON décidé : versionner les données elles-mêmes avec un outil dédié — le « gitdata »
demandé existe déjà sous trois noms (DVC, git-annex, git LFS) : pointeurs suivis par git, octets sur le NAS, dvc pull
sur un clone. Mesuré le 2026-09-22 (git ls-files + du) : les données SUIVIES par git pèsent **7,5 Mo** (454 fichiers
sous data/ et results/, le plus gros data/hall_of_fame.pkl à 1,2 Mo) contre **3,6 Go** sur disque pour data/ (kuzu,
états d'agents — non suivis) et 62 Mo pour results/ ; le pack git fait 437 Mo. Le volume versionné est donc petit : un
DVC ne s'impose pas AUJOURD'HUI, et il coûte un outil de plus par session et un remote NAS à configurer. Deux issues :
(a) rester à git + `src/paths.py` — fermer cette entrée en RETIRANT sa clause ; (b) DVC par-dessus (dvc init, remote
NAS, les .pkl/.npz sortent de git) — la clause se satisfait d'elle-même. Le seuil qui renverse (a) : un artefact
NÉCESSAIRE à la reprise qui dépasse ~50 Mo, ou le pack qui double. *Coût : (a) 0 ; (b) agent 2 h + configuration du
NAS.* Dépend de : rien. Voir aussi P2.80 (les 44 littéraux qui contournent l'indirection).
<!-- closes_when:path_present=.dvc/config -->

**P2.80 — ⚠️ OUVERTE (2026-09-22) — 44 chemins de données encore ÉCRITS EN DUR dans 25 fichiers (dette légataire
gelée par la porte 12) : tant qu'ils y sont, AGAGI_DATA_ROOT ne déplace qu'une PARTIE des données, en silence.**
Quoi : la porte 12 (`tools/check_data_paths.py`) refuse tout NOUVEAU littéral data/… ou results/… mais gèle les anciens
dans `tools/data_paths_baseline.json` — recompté le 2026-09-22 par le cliquet lui-même : « 44 dans 25 fichiers |
gelés : 44 | NOUVEAUX : 0 ». Ces sites lisent ou écrivent À CÔTÉ de l'indirection : un NAS monté via AGAGI_DATA_ROOT
laisserait src/graph_rag/ (kuzu, pending_article), `tools/confirm_b.py`, `tools/curriculum_craft.py`,
`tools/skinner_box.py`… sur le disque local, sans un mot. Trois familles, comptées dans la baseline (un fichier peut
en porter deux) : bases kuzu / experiment_graph — **13 fichiers** (trois chemins différents pour ce que
`paths.kuzu_graph()` / `paths.experiment_graph()` nomment déjà) ; Hall of Fame et ses variantes — **10 fichiers**
(→ `paths.hall_of_fame(variante)` / `paths.agent_states`) ; sorties results/ — **4 fichiers** (→ `paths.results_file`).
Migrer un site ne déclenche RIEN (c'est le but de la porte) ; après chaque famille, `--update-baseline` resserre la
baseline. Ordre : kuzu d'abord (une seule fonction cible, 13 fichiers), HoF ensuite, results/ enfin. *Coût : agent
2-3 h ; calcul 0.* Dépend de : rien. Lié à P2.79.
<!-- closes_when:grep_present=tools/data_paths_baseline.json::"fichiers": \{\} -->

**P2.81 — ⚠️ OUVERTE (2026-09-22, vue en passant pendant le design du dashboard) — `backend/app/main.py:68` résout la
racine du dépôt un niveau TROP HAUT : le WebSocket « Évolution temps réel » tail un fichier qui ne peut pas exister.**
Quoi : `RESULTS_DIR = Path(__file__).resolve().parents[3] / "results"` est la forme copiée des routes et des services,
qui vivent un niveau PLUS PROFOND (`backend/app/routes/*.py`, `backend/app/services/runs_service.py:18` — pour eux
`parents[3]` EST le dépôt). Pour `main.py`, `parents[3]` est le dossier PARENT du dépôt. Mesuré à l'import le
2026-09-22 : `C:\Users\robla\VScode_Project\results`, `existe = False` (sous docker : `/results`, alors que
docker-compose monte `./results:/app/results`). Deux consommateurs : `service = ExperimentDataService(RESULTS_DIR)`
(l.70) — construit, jamais utilisé, inoffensif ; et `LIVE_PROGRESS_PATH` (l.69), tailé par `/ws/evolution`
(l.126-129), consommé par `frontend/src/components/LiveEvolution.tsx:34`. Or le lanceur
(`backend/app/services/sandbox_service.py:9,59`) arme `AGISEED_LIVE_PROGRESS` sur `<dépôt>/results/live_progress.jsonl`
— le BON chemin : le runner écrit là, le WS lit ailleurs, les deux ne se rejoignent jamais, et `emit_progress`
(`src/seed_ai/live_progress.py:21-23`) avale toute erreur d'ouverture. Le seul test du flux (`tests/test_backend.py:168-171`)
monkeypatche `LIVE_PROGRESS_PATH` vers un `tmp_path` : un contrôle qui ne peut pas échouer sur le vrai chemin (E1).
Depuis `b0f2620b` (2026-06-05, commit initial). Correctif : UNE résolution de racine pour tout le backend
(`tools.parity_check.find_repo_root` ou `src.paths`), et un test qui compare `main.LIVE_PROGRESS_PATH` au chemin
armé par `sandbox_service._arm_live_progress` SANS monkeypatch. *Coût : agent 30 min ; calcul 0.* Dépend de : rien.
<!-- closes_when:grep_absent=backend/app/main.py::parents\[3\] -->

**P4.11 — rang 5 — ✅ CLOSE le 2026-09-24 (revue de la session qui porte le harnais, réserves appliquées telles quelles) — ⚠️ BILLET ACQUIS À UN SEUL POINT DE FONCTIONNEMENT : lr 4,0 = 0,25/agent, λ 0,9-0,99 (aide09 12/12, aide099 11/12) ; **invariance au pas NON ÉTABLIE** — à lr 2,0 l'aide est nulle (aide09 0/12, R1) mais ce point N'A PAS SON CONTRÔLE DE CHEMIN : les bras de R1 à ce pas sont `lr0_reference@2`, `td0@2`, `tdlam09@2`, **jamais `td0_d0@2`**, et la ligne lr 2,0 de R2 était coupée ; or **aucun des deux bras ne franchit sa propre barre** à ce pas : mesuré indépendamment par la session du harnais sur `results/td_step_pilot_r1.json`, `lr0_reference@2` = 0,1643, `td0@2` = 0,1840, `tdlam09@2` = 0,1917, pour une barre réf + 0,05 = **0,2143**. Le 0/12 du pas 2 oppose donc deux bras qui n'apprennent NI l'un NI l'autre : la grandeur contrastée n'existe pas à ce point. Une trace transporte du crédit ; s'il n'y a pas de crédit à transporter, son inertie ne la concerne pas. ⚠️ **Et le critère de lisibilité ne comble pas ce trou tout seul** : `lisible@lr` se mesure sur la paire SANS DÉLAI (`td0_d0` contre `lr0_reference_d0`), alors que l'aide se lit sur la paire AVEC délai — un pas peut donc être déclaré « lisible » pendant que les bras qui portent le contraste restent sous leur barre. ✅ **TRANCHÉ depuis, et dans le sens de cet amendement** (P4.17 CLOSE, lecture scellée `AIDE_A_UN_POINT`) : la reprise a récupéré la ligne lr 2,0 avec son bras de chemin, et `td0_d0` y passe **12/12** pendant qu'**aucun bras à délai ne franchit sa barre** (1/12, 0/12, 1/12, 2/12) — le pas est « lisible » au sens de la règle par la paire SANS délai, et le 0/12 d'aide oppose bien deux bras qui n'apprennent ni l'un ni l'autre. L'invariance au pas reste donc **OUVERTE**, et le balayage utile va vers le **HAUT**, pas vers le bas. ⚠️ Et la lecture complète RENFORCE le billet au lieu de l'affaiblir : à lr 4,0, contre la référence lr=0 du même dispositif (barre 0,2125), `lam0` ne franchit que sur **1/12** et `lam05` sur 3/12, tandis que `lam09` et `lam099` franchissent sur **11/12** — les bras SANS trace n'apprennent pas du tout, donc le +0,063 de R0 n'était pas un bonus sur une tâche apprise : à ce point, la trace est **CE QUI REND la tâche différée apprenable**. Ce qui manque à la pièce reste ce que dit P4.19 (le sham δ-permuté et la dose appariée), pas une invariance. ✅ **Ce que le billet ne risque PAS, recompté sur ce que le CODE compare** (ma première liste, faite de mémoire, en manquait quatre — corrigé le jour même) : **25 comparaisons** effectives de `_lecture`/`_lecture_r1`/`_lecture_r2`, dont 5 NON LISIBLES (bras de lr 1,0 absents, jamais comptées 0) et 20 recomptées en arithmétique de GRILLE (640 évaluations, marge = 32 pas ; médianes sur 1/1280, barre 0,5 = 640 pas) — **0 changement, 0 égalité exacte**, écart maximal à un compte entier 1,526e-05 pas sur 504 valeurs. E30 est donc LATENT ici et n'a touché aucun de ces chiffres. ⚠️ **Mais la marge en PAS, que le compte cachait** : le `12/12` de `tdlam > td0` à lr 4,0 — la mesure qui PORTE ce billet — tient à **+1 pas de grille**, une évaluation sur 640 chez un seul seed (et `aide099` 11/12 à −2 pas). Le compte est au plancher de RÉSOLUTION ; le verdict, lui, est robuste (seuil scellé `seeds_aide` = 11, donc 12 → 11 laisserait la branche intacte). À citer avec sa marge, jamais nu. ⚠️ **Corrigé le 2026-09-24, même jour** : la première rédaction de cette clôture écrivait « invariance RÉFUTÉE », ce qui SUR-DÉCLARAIT — trouvé en vérifiant les bras de R1 après que la session propriétaire du pilote ait corrigé sa propre lecture (la ligne lr 2,0 avait été coupée et sa reprise la récupère : 48 cellules, qui ont tranché depuis — ⚠️ la NATURE de cette coupe, « contention », n'est PAS établie : le rapport CPU/mur de la reprise dite libre vaut 0,78 contre 1,80 pour la passe dite chargée, cf. E33 occ. 6). lr 1,0 JAMAIS mesuré (coupe E13 publiée dans `_regime.coupe` ; sa nature « structurelle, tenue machine libre » n'est PAS établie non plus, pour la même raison). La pièce `eligibility_trace_credit` N'ENTRE PAS au registre : deux contrôles de son billet manquent (P4.19). ([`ADR-005`](../ADR/005_mecanismes_biomimetiques_pieces_familles_prerequis.md), item 1) —
Trace d'éligibilité de politique TD(λ) dans `TorchPopulationModel._td_update` : le crédit local SANS BPTT, calibré à
0 simulation ; l'issue positive se mesure sur un PILOTE TD PAR PAS (`CompositionTask(same_tick=False)`), pas sur le
proxy D=2.**
⚠️ **CORRECTION 2026-09-16 (mesurée)** : la première version de cette entrée envoyait le run positif sur le proxy D=2 de
LOCK-002 (`tools/lang_memory_edge_run.py`). Or `language_memory_demand_probe._train_and_eval` apprend par
`agent.learn_episode(...)` (l.282, l.321) — la voie ÉPISODIQUE, jamais `learn()`/`_td_update` : une trace dans `_td_update`
n'y serait JAMAIS exercée, le run aurait été un no-op. `_td_update` ne tourne aujourd'hui qu'in-world, tick par tick, sur une
tâche same-tick. Le lieu correct = un pilote TD par pas sur `CompositionTask(same_tick=False)` (key t0, q t1, récompense
t1) : forward par pas, `learn(rewards_t, actions_t)` par pas, CPU pur, sans monde — c'est le billet `credit="td"` de
l'ADR-005, et c'est accepté par la session harnais comme MODE `credit="td"` de `ConnectomeLearner` en R2 (la Dose compte
les T mises à jour, la trace = kwarg `trace_lambda` de `build`).
**État au 2026-09-16 (session loop 766eabae / agagi-b0, non committé)** : trace posée dans `_td_update` — drapeaux de
classe `CREDIT_TRACE_LAMBDA` (0,0 = chemin d'ORIGINE pris tel quel : bit-identique par construction) et
`CREDIT_TRACE_BYPASS_OPTIMIZER` (sous un optimiseur autre que SGD sans momentum, λ>0 REFUSE sauf contournement DEMANDÉ
par kwarg, publié dans `regime`) ; chemin `_td_update_trace` : e ← γλ·e + ∇ sur TOUS les paramètres de l'optimiseur
(`_trace_params` = W, U, V, W_bl — listes alignées), ΔW = lr·(δ·e_a − (v−cible)·e_v)/B (mêmes signes et même /B que
−(δ·logp).mean() et 0,5·((v−cible)²).mean() ; ⚠️ pas EFFECTIF lr/B, P2.76) ; refus explicite sous `CONDITION_GATE` /
`ANTISAT` ; `reset_traces(mask)` option COMPTÉE (résurrection : pas de reset par défaut — immortel veut dire immortel ;
rebuild à changement de B perd la trace, dit dans le docstring) ; `trace_updates` / `trace_resets` publiés ;
`count_learning_events(trace_lambda=, trace_bypass_optimizer=)` publié dans `regime` ; pin 0,0 dans `_pinned_substrate`.
Cellule de référence de la session harnais re-mesurée APRÈS le patch : 0,932812511920929 / 0,27031248807907104,
bit-identiques. 9 cas `tests/sandbox/test_credit_trace_lambda.py`, contrôle POSITIF en premier (la formule rejouée hors du
modèle prédit W à 1e-6 sur deux mises à jour et sur les quatre paramètres, et prédit AUTRE CHOSE à λ=0,5) ; déclaration
CALIBRATED qualifiée `backend_torch.py::_td_update`.
**Pilote `tools/td_step_pilot.py`, règle `TD-STEP-PILOT-R0` scellée, 144 cellules en cours.** Deux fumées seed 0 (déclarées
dans la règle, seed 0 EXCLU) ont changé le design AVANT scellement — la question A du pré-vol : (1) le contrôle positif
« BPTT 0,923 » est BILINÉAIRE ; en plain, BPTT 2 pas rend 0,21/0,27 à 600 ép. → un bras TD plain ne pouvait pas réussir
(E1) : substrat bilinéaire sur tous les bras, trace généralisée aux 4 paramètres ; (2) il manquait un contrôle positif du
CHEMIN de crédit : TD par pas à D=0 n'apprend RIEN à lr 0,04-0,4 même à 4000 ép. (0,18 vs 0,17 réf.), apprend à lr 4,0
(0,25/agent) : 0,30 à 1500 ép., 0,52 à 3000 ; 8,0 → 0,38 ; 40 diverge → bras `td0_d0` + `lr0_reference_d0`, branche
`CONTROLE_CHEMIN_ECHOUE` avant toute lecture de D=1. Régime scellé : 3000 ép., lr {4,0 ; 8,0} (E19), λ=0,9, reset des
traces par épisode (publié) ; 6 bras × 2 pas × 12 seeds. Fumée D=1 seed 0 (1500 ép., lr 4) : td0 0,189, λ=0,9 0,178,
réf. 0,145. Branches, dans l'ordre : INCOMPLET ; CONTROLE_SUBSTRAT_ECHOUE ; CONTROLE_CHEMIN_ECHOUE ;
TD0_{APPREND|INERTE} | TRACE_{AIDE|NUIT|NEUTRE}. Réponse connue positive sur la même Task = `bptt_credit` (bilinéaire).
Le bras `hebb_delta` (Hebb×δ, prédit INERTE par EDR-020) SORT de R1 — à sceller à part, R1 ne mesure qu'une chose.
P1.6 = QUALIFICATION seulement (no-op exact, non inerte, non dégradante — précédent EDR-130 —, E19), pas le lieu de
l'issue positive. Motivation : EDR-148 (TD(λ) nommé, jamais tenté) ; P4.9 (l'érosion est portée par la voie ÉPISODIQUE — une
trace dans `_td_update` ne peut PAS la changer sans couper/remplacer l'épisodique : run n°3, pas n°1). ⚠️ Le modulateur δ
vient d'un critic saturé (56 % < −0,99, S2-REWARD-ABLATION) — NAV-005 : publier la distribution de δ à côté du verdict.
**Se ferme** avec le record `EDR-TD-STEP-PILOT-R0` (verdict lu dans `results/td_step_pilot_r0.json`, committé) — la clause
ci-dessous est un motif d'auto-clôture ancré (vérifiable sur un clone ; `grep_present` sur le JSON non suivi ne l'était pas).
⚠️ **Clause corrigée le 2026-09-24** : la précédente grep-ait sa PROPRE ligne « P4.11 — ✅ CLOSE » dans ce fichier — une clause auto-référentielle ne peut STRUCTURELLEMENT pas signaler qu'une condition de fond est remplie, elle ne fait que recopier la décision de l'auteur (E1). Ancrée désormais sur la SORTIE : le verdict du record.
<!-- closes_when:grep_present=docs/EDR/TD-STEP-PILOT-R0_Per_Step_TD_Credit_Is_Inert_At_D1_And_The_Eligibility_Trace_Transports_Credit.md::verdict: TD0_INERTE -->

**P4.19 — rang 6 — OUVERTE (2026-09-24, issue de la revue de la session qui porte le harnais) — Les DEUX contrôles manquants du billet de la pièce
`eligibility_trace_credit` : le sham « δ PERMUTÉ » et la dose appariée en Σ|ΔW|.**
ADR-005 exige pour cette pièce un `matched_sham` « même trace, δ PERMUTÉ dans le temps » et une entrée « à dose
appariée en Σ|ΔW| ». Mesuré le 2026-09-24, aucun des deux n'existe :
* **(a) sham δ-permuté : JAMAIS mesuré** — `git show HEAD:tools/td_step_pilot.py | grep -ciE 'permut|shuffl|sham|scramble'`
  → **0** (motif validé sur un cas positif : 5 occurrences de `sham` dans `src/agents/backend_torch.py`). Les bras
  réellement joués sont `['td0','tdlam','lr0_reference','td0_d0','lr0_reference_d0','bptt']` (R0) et
  `['lam0','lam05','lam09','lam099','td0_d0']` (R2). C'est le SEUL bras qui sépare « la trace TRANSPORTE du crédit »
  de « la trace fait un pas effectif plus GROS » : à λ = 0,9 et γ = 0,9, γλ = 0,81 ajoute 0,81·g₀ au pas 1 — plus
  gros autant que mieux orienté. Le record R0 ne mentionne ce manque nulle part (grep `sham`/`permut` → 0).
  Coût : un bras de plus dans le pilote, ~12 cellules à 75-90 s hors contention (~20 min) + un addendum au record.
* **(b) dose appariée en Σ|ΔW| : NON PUBLIÉE, donc non mesurable** — 0 occurrence de `sum_abs_dW`, `sigma_dW`,
  `dW_abs` ni `"dW` dans `results/td_step_pilot_r0.json`, `_r1.json`, `_r2.json` ; leurs blocs `_dose` ne portent que
  `{updates, trace_updates, trace_resets, lr_effective_per_agent, optimiseur}`. L'appariement publié est NOMINAL
  (td0 et tdlam déclarent tous deux `lr_effective 0,25`), pas effectif. Coût : une somme accumulée dans le runner —
  **nul**, et à faire AVANT tout nouveau tir, sinon le tir suivant sera à refaire.
Tant que (a) et (b) ne sont pas payés, la pièce reste « attend » au registre du harnais (la session harnais l'y
maintient avec ces deux manques nommés). Prérequis de l'ENTRÉE de la pièce, pas dette diffuse.
<!-- closes_when:grep_present=tools/td_step_pilot.py::permut -->

**P4.20 — rang 12 — OUVERTE (2026-09-24, balayage demandé par la session qui porte le harnais) — Deux familles de clauses `closes_when`
qui ne peuvent pas faire ce qu'elles promettent.**
Balayage complet des 60 clauses du backlog (41 `grep_present`, 14 `path_present`, 5 `grep_absent`) :
* **(i) AUTO-RÉFÉRENTIELLES — 2 cas.** Une clause qui grep sa propre ligne « ✅ CLOSE » dans ce fichier ne peut
  structurellement pas échouer autrement qu'en restant fausse, ni signaler qu'une condition de fond est remplie :
  elle recopie la décision de l'auteur (E1, contrôle qui ne peut pas échouer). **P4.11** (la mienne, corrigée ici,
  ancrée sur le verdict du record) et **P4.17** (écrite en copiant mon motif — le défaut s'est PROPAGÉ ; à son
  propriétaire de l'ancrer sur `EDR-TD-STEP-PILOT-R2` quand ce record existera). ⚠️ Contre-exemple de
  SPÉCIFICITÉ : la clause de **P4.15** vise `P4.9`, une AUTRE entrée — c'est une dépendance légitime, et elle a
  fonctionné (P4.15 s'est fermée quand P4.9 est passée CLOSE). Ne pas interdire la famille, interdire l'auto-visée.
* **(ii) ANCRÉES SUR L'ARTEFACT D'ENTRÉE — 6 cas.** `path_present=docs/preregistrations/<règle>.json` est VRAI dès
  le SCELLEMENT, avant tout run : l'entrée peut passer « ✅ CLOSE » avec le cliquet au vert alors que le record et
  l'évidence n'existent pas. Vu en acte sur **P4.16** (l'arbre annonçait CLOSE et `records_total=325` pendant que le
  record et `results/s2_credit_ablation_2.json` étaient non suivis). Les 6 : `LOCK-001-PROXY-R1`,
  `S2-REWARD-ABLATION`, `S2-CREDIT-ABLATION`, `S2-CREDIT-ABLATION-2`, `S2-BASSIN-FRAGILITY`, `S5-G4-PHASE-A`.
  Une clause doit viser la SORTIE (record, `results/<run>.json`), jamais l'entrée.
* **Aggravant commun** : `_CLOSE_MARQUEURS` de `tools/check_backlog_freshness.py` contient « ✅ » SEUL, donc
  « ✅ SCELLÉE ET LANCÉE » bascule l'entrée du côté CLOSE de la logique à deux sens — c'est pourquoi P4.16 ne
  déclenchait aucune violation malgré son état réel.
* **(iii) ANCRÉES SUR LA PRÉSENCE DU REMÈDE — 1 cas, le mien, ajouté le 2026-09-24 le jour même du balayage.** Viser la SORTIE ne suffit pas : encore faut-il que ce soit la sortie que l'entrée CHERCHE. La clause de **P2.107** était `grep_present=tests/conftest.py::GIT_DIR` — donc satisfaite dès qu'une fixture existe — alors que l'entrée déclare explicitement ne pas se clore tant que le SITE d'appel fautif n'est pas nommé. Elle a basculé au vert **dans l'heure**, par la pose du remède, sur une entrée dont la condition de fond était intacte. Différence avec (i) : l'auto-référentielle recopie la DÉCISION de l'auteur ; celle-ci constate l'EXISTENCE DU CORRECTIF. Aucune des deux ne constate ce que l'entrée cherche. ⚠️ Et le défaut a été écrit PENDANT ce balayage-ci, par son auteur : un balayage de forme ne protège pas contre la production d'un exemplaire neuf de la même forme, ce qui est l'argument le plus fort pour que la porte 4 le refuse EXÉCUTABLEMENT au lieu qu'on le relise. Durcissement (4) à ajouter à la liste ci-dessous : refuser une clause dont le motif vise le fichier livrable du REMÈDE quand l'entrée porte une réserve de fond explicite — ou, plus simple et plus sûr, faire DÉCLARER par l'auteur ce que la clause constate, et refuser le silence.
* **Aggravant commun** : `_CLOSE_MARQUEURS` de `tools/check_backlog_freshness.py` contient « ✅ » SEUL, donc
  « ✅ SCELLÉE ET LANCÉE » bascule l'entrée du côté CLOSE de la logique à deux sens — c'est pourquoi P4.16 ne
  déclenchait aucune violation malgré son état réel.
**À faire, en une passe** : durcir la porte 4 — (1) refuser une clause dont le motif vise l'entrée qui la porte ;
(2) refuser (ou signaler, baseline gelée sur les 6) une clause `path_present` pointant dans `docs/preregistrations/` ;
(3) distinguer « ✅ CLOSE » de « ✅ SCELLÉE / LANCÉE » dans `_CLOSE_MARQUEURS`. Chaque durcissement avec son
contre-exemple gelé et sa mutation (porte 15), dans la même passe — et une baseline pour ne pas bloquer les 6 entrées
existantes d'autrui.
<!-- closes_when:grep_present=tools/check_backlog_freshness.py::auto-référentielle -->

**P2.105 — rang 12 — OUVERTE (2026-09-24, second cas d'E30 paru le jour de la classe) — La porte qui manque à
E30 : un seuil dont la marge est un multiple EXACT du pas d'une grille se compare sur la grille, et rien ne
l'applique.**
Le registre disait « garde exécutable à écrire quand un second cas paraîtra ». Il est paru : `tools/td_step_pilot.py`
(`n_sup`/`n_inf`, l. 136, 240, 350) compare en flottants une accuracy qui est un COMPTE sur 40 × 16 = **640**
évaluations, avec une marge 0,05 qui vaut **exactement 32 pas**, sur des valeurs stockées en **float32**. Les
17 comptes publiés de R0/R1/R2 ne changent PAS (zéro égalité exacte sur 12 seeds) — le défaut y est LATENT — mais
la reprise de P4.17 tourne sur 48 cellules NEUVES avec le code non corrigé, et une égalité qui y apparaîtrait
serait perdue du côté qui refuse (E14 en formation).
**Le travail est déjà à moitié fait** : le motif est écrit et VALIDÉ sur le cas positif connu (`bilinear_sham_run`
avant `ba56ede3`), et l'inventaire des **12 sites** est mesuré, donc la baseline est prête à geler. Deux des 12
produisent un VERDICT publié avec marge et leur commensurabilité n'est pas mesurée :
`tools/adaptive_planning_probe.py:154` (`ADAPTIVE_NEUTRAL`) et `tools/hunif_retention_probe.py:148`
(`NO_RETENTION_ADVANTAGE`) — deux négatifs de fond ; les autres ne gouvernent qu'un affichage.
**Forme** : porte qui refuse tout NOUVEAU site de la forme hors baseline, plus l'heuristique gratuite là où
l'instrument connaît son N (`n_eval`, `eval_batches × n_agents`) — « la marge est-elle un multiple du pas ? » est
décidable sans simuler.
⚠️ **Spécification COMPLÉTÉE le 2026-09-24, après deux mesures : mon motif initial était INCOMPLET sur deux axes.**
(i) **L'étage des MÉDIANES.** Une médiane de 12 comptes est un demi-entier sur N, donc vit sur la grille `2N` —
où 0,05 vaut 64 pas et une barre 0,5 vaut 640 pas, encore entiers. Mon motif ne visait que les comparaisons
par seed : il aurait manqué le contrôle positif de R0 (`max(médianes de bptt) < 0,5`, l. 145) et les deux
comparaisons de médianes du module de verdict du harnais. Une porte qui ne couvre pas cet étage certifie à moitié.
(ii) **La marge 0,0.** `tdlam09@4 > tdlam05@4` compare à marge NULLE (l. 270) : trivialement commensurable,
donc à classer explicitement plutôt qu'à faire lever une heuristique.
**Second livrable, tiré du recompte et moins coûteux que la porte** : publier à côté de chaque compte sa
**marge minimale EN PAS DE GRILLE**. C'est la discipline « tout ratio se publie avec son plancher de bruit »
appliquée au bruit de REPRÉSENTATION, et elle a une valeur immédiate — elle révèle que le `12/12` du billet
de P4.11 tient à **+1 pas** (une évaluation sur 640). Publier aussi `N` dans le bloc `regime` : il n'est
aujourd'hui que DÉDUCTIBLE (`eval_batches × n_agents`), donc une prémisse non mesurée (E8).
**Contre-exemple naturel disponible** : l'égalité exacte `126/640` contre `94/640 + 32` mesurée par la session
du harnais dans un run publié — à PORTER sur une comparaison que le code effectue vraiment, sa propre revue
ayant montré que le contraste où elle l'a trouvée n'est jamais calculé.
⚠️ Entrée VOISINE à ne pas prendre : **P2.106** est réservée par la session du harnais pour le même sujet côté
module de verdict (comparaison en grille dans `_acquisition`/`_necessity`, ou publication des marges en pas).
Son insertion attend la fin d'une re-revue qui COMPTE les numéros du backlog : ne pas l'écrire à sa place. Contre-exemple gelé et mutation (porte 15) dans la même passe. ✅ Le correctif de `ba56ede3` A ÉTÉ rétro-appliqué à `td_step_pilot.py` (ses TROIS lectures) par sa
session propriétaire le jour même, AVANT la lecture de la reprise, avec recompte avant/après : aucun compte
ne bouge, pas même sur les 48 cellules neuves. Cette entrée ne porte donc plus l'urgence, seulement le
CLIQUET : empêcher un NOUVEAU site, couvrir l'étage des médianes, et trancher les 9 autres sites de
l'inventaire (dont les deux qui publient un verdict négatif).
<!-- closes_when:grep_present=tools/hooks/pre-commit::check_grid_threshold -->


**P2.107 — rang 3 — OUVERTE (2026-09-24, mécanisme REPRODUIT le jour même) — Les variables que git exporte
aux hooks fuient dans TOUTE la chaîne de sous-processus, et un test peut alors MUTER LE DÉPÔT RÉEL : fermer la
CLASSE par une fixture, pas les sites un par un.**
Ce matin la fuite de `GIT_INDEX_FILE` a été fermée SITE PAR SITE dans `tests/sandbox/test_jobs.py`
(`_env_sans_git`). Ça n'a pas suffi : la même famille est repassée quelques heures plus tard par **`GIT_DIR`**
et a mis l'arbre PARTAGÉ hors service (`core.bare = true`, `git status` mort pour toutes les sessions du
checkout principal). Corriger des sites ne ferme pas une classe — c'est E14 appliqué à l'hygiène
d'environnement. Mesuré : `tests/conftest.py` porte **zéro** occurrence de `GIT_DIR`, `GIT_WORK_TREE` ou
`GIT_INDEX_FILE`, donc la protection existe pour UN fichier de tests et pour aucun des ~2000 autres.
Preuve du mécanisme (deux dépôts JOUETS, jamais celui-ci) : `git init` + `GIT_DIR` hérité + pas de
`GIT_WORK_TREE` + cwd ailleurs ⇒ le dépôt POINTÉ bascule `core.bare` false → true, son `git status` rend le
message exact observé, le tmpdir ne reçoit aucun `.git`, et le `git config user.email` suivant écrase
l'identité du dépôt pointé.
**Forme demandée** : une fixture `autouse=True` dans `tests/conftest.py` qui RETIRE `GIT_DIR`, `GIT_WORK_TREE`,
`GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY` et `GIT_CEILING_DIRECTORIES` de l'environnement. ⚠️ **De portée
FONCTION, pas SESSION** : une fixture de session nettoie l'environnement hérité une seule fois, ce qui suffit
pour la fuite du hook mais laisse le second chemin ouvert — un test qui pose `os.environ["GIT_DIR"]` sans
`monkeypatch` empoisonne tous les tests SUIVANTS de la même exécution. La portée fonction couvre les deux pour
un coût nul, et reste compatible avec les tests qui ont BESOIN de ces variables (un `monkeypatch.setenv` dans
le test s'applique après le nettoyage — c'est le cas de `_en_commit()` dans `check_backlog_freshness`).
**Contre-exemple gelé, DÉJÀ ÉCRIT** : le script de reproduction à deux dépôts jouets ; il doit ROUGIR si la
fixture est retirée, et c'est ce qui en fait une garde plutôt qu'une note.
**Garde d'appoint à coût nul** : refuser toute sortie de test contenant `re-init: ignored` — l'empreinte que
l'accident émet de lui-même, et la seule qui survive à un `env=` explicite qui contournerait la fixture.
**À fermer quoi qu'il arrive** : les trois `subprocess.run(..., cwd=repo)` sans `env=` de
`test_pm_roles_counts.py:95`, `test_pm_snapshot.py:22`, `test_staged_authorship.py:53`. L'identité intacte
prouve seulement qu'ils n'ont pas été le chemin d'AUJOURD'HUI, pas qu'ils sont sûrs.
⚠️ Le site d'appel réellement emprunté le 2026-09-24 n'est **PAS identifié** : ne pas clore cette entrée sur la
seule pose de la fixture sans l'avoir cherché, sinon la prochaine variante repassera par le trou non vu. La
CLASSE est établie, le CAS ne l'est pas.
⚠️ **CETTE ENTRÉE NE PORTE VOLONTAIREMENT AUCUNE CLAUSE `closes_when`, et voici pourquoi** — la première rédaction en portait une, `grep_present=tests/conftest.py::GIT_DIR`, et elle était FAUSSE de la même façon que les deux familles de P4.20, un cran plus subtil : elle a été **SATISFAITE dans l'heure** par la pose de la fixture, alors que l'entrée déclare au paragraphe précédent qu'elle ne se clôt PAS tant que le site n'est pas nommé. Elle ancrait sur la **PRÉSENCE DU REMÈDE**, pas sur la condition de fond. Trouvée par la session qui a posé la fixture, pas par moi — et je venais de balayer les 60 clauses du backlog pour cette famille exacte quelques heures plus tôt (P4.20), en écrivant simultanément un nouvel exemplaire du défaut. La condition réelle (« le site d'appel est NOMMÉ et gelé en régression ») n'est pas exprimable dans le vocabulaire fermé de prédicats PURS ; le dépôt interdit de proxifier ce qu'on ne sait pas mesurer, donc l'entrée reste HORS périmètre de clause — RAPPORTÉE par la porte 4, jamais comptée comme un succès, ce qui est le comportement prescrit et non un oubli.



✅ **SITE IDENTIFIÉ le soir même, à la vraisemblance forte** — la chaîne complète et ses sept concordances
sont dans l'occurrence E5 du registre : le témoin `tests/sandbox/test_record_graph_completeness.py`, dans sa
première version jamais committée sur la branche `chantier/pm-portes`, lancé par le hook d'un commit AVORTÉ
(13:29:39 → 13:31:37) sous le `GIT_DIR` du worktree. La réserve « ne pas clore sans avoir cherché le site »
est donc levée. **L'entrée reste OUVERTE**, pour deux raisons mesurées : (a) le correctif du TRANSPORT — la
purge de la famille GIT_* dans le lanceur de témoins de la porte 15 — existe sur la branche PM, avec son
utilitaire `f6bb56a0:tools/_git_env.py` et un contre-exemple à deux issues ancré sur l'ÉTAT, mais il n'est PAS
fusionné ici, où `tools/check_gate_mutation.py` construit toujours son environnement depuis `os.environ` sans
purge ; (b) les trois sites non protégés restent à fermer.
**P2.111 — rang 8 — OUVERTE (2026-09-24, mesuré contre le motif RÉEL de la porte) — La porte 4 ne refuse pas
la forme `sha:chemin` parce qu'un DEUX-POINTS casse sa classe de caractères, pas parce qu'elle l'a vérifiée :
une échappatoire SILENCIEUSE à la garde des chemins non suivis.**
Mesure, motif recopié depuis `tools/check_backlog_freshness.py` (`_BACKTICK_PATH`) et exécuté sur les deux
formes : un chemin nu entre backticks est SIGNALÉ comme non suivi ; la même citation préfixée d'un sha ne
l'est pas. La porte ne voit tout simplement pas la seconde.
**Pourquoi ça compte dans les DEUX sens.** (a) La forme `sha:chemin` est LÉGITIME et même préférable sur ce
dépôt : elle résout depuis n'importe quelle branche, elle est plus précise qu'un chemin nu, et elle ne bloque
pas la flotte quand on cite du travail vivant sur une autre branche — c'est la seule façon correcte de citer
une garde qui existe ailleurs (cf. **E33** occ. 4). (b) Mais rien ne vérifie qu'elle RÉSOUT : une citation
`sha:chemin` vers un sha inexistant, ou vers un chemin absent de ce sha, passe en silence — exactement le
défaut que la porte existe pour empêcher, déplacé d'un cran.
**Forme demandée** : ACCEPTER explicitement `sha:chemin` (ou `ref:chemin`) comme forme de citation, et vérifier
qu'elle résout par `git cat-file -e <sha>:<chemin>`. Une échappatoire silencieuse devient une forme CONTRÔLÉE.
Contre-exemple gelé et mutation (porte 15) dans la même passe, comme pour tout durcissement de porte.
⚠️ **Je ne prends pas cette entrée** : j'ai durci cette porte deux fois aujourd'hui, mais la session qui tient
le tableau des rôles la déclare « ni la sienne ni la mienne ». Elle est inscrite avec sa mesure pour que le
propriétaire la prenne ; si personne ne la revendique, elle reste ouverte et RAPPORTÉE, ce qui est le
comportement prescrit pour une dette sans propriétaire — pas un oubli.
<!-- closes_when:grep_present=tools/check_backlog_freshness.py::cat-file -->


**P2.112 — rang 4 — OUVERTE (2026-09-24, après un dégât RÉEL et mesuré) — Toute réécriture d'un fichier
PARTAGÉ doit asserter que rien du DISQUE COURANT ne disparaît — pas seulement rien de HEAD.**
Preuve (E22, occurrence du jour) : mon script alignait le disque depuis son BLOB après le commit, et a
détruit l'entrée `P2.110` d'une autre session — écrite à 13:00, absente du disque, de l'index et de tout
commit. Aucune porte ne pouvait le voir : la porte 16 juge un commit, et ce hunk n'en a jamais fait partie.
Mes scripts portaient déjà l'assertion « aucune ligne de HEAD ne disparaît », qui est INOPÉRANTE ici :
l'état écrasé n'était pas HEAD, c'était le disque.
**Forme demandée** : un helper partagé — domicile naturel `tools/check_amputation.py`, qui porte déjà la
logique d'amputation — du type `ecrire_sans_perte(chemin, nouveau, retraits_declares=())` qui RELIT le
fichier juste avant d'écrire, refuse si une ligne non vide du disque courant disparaît sans être déclarée,
et dit LAQUELLE. Coût nul, et il transforme une discipline en refus.
**Contre-exemple gelé à écrire dans la même passe** : un fichier portant un hunk « étranger », une
réécriture bâtie depuis une base qui ne le contient pas, et l'assertion qui ROUGIT ; plus le cas symétrique
d'un retrait DÉCLARÉ qui passe.
⚠️ **Ce n'est pas automatisable par une porte** : une porte s'exécute au commit et ne voit pas les écritures
disque. C'est donc un helper que les scripts doivent APPELER — et une règle documentée sans application
exécutable est la classe E10. La parade contre E10 ici est que le helper soit le chemin le plus COURT :
s'il est plus simple à appeler qu'un `open(...).write(...)`, il sera appelé.
⚠️ **Tension à ne pas oublier en le concevant** : différer l'écriture après le commit protège la flotte du
blocage par la porte 8 (P2.85) ; l'écrire depuis le blob détruit. Le helper doit rendre les deux
compatibles, et c'est en croyant résoudre la première que j'ai créé la seconde.
<!-- closes_when:grep_present=tools/check_amputation.py::ecrire_sans_perte -->


**P4.21 — rang 12 — OUVERTE (2026-09-24, trouvée en amendant ma propre clôture) — Un verdict de SYNTHÈSE qui
agrège plusieurs POINTS DE FONCTIONNEMENT n'a aucune garde : le pré-vol garde une CELLULE, pas une CONCLUSION.**
Preuve (E2 occ. 6) : `7fa6b2d8` publiait « invariance au pas RÉFUTÉE » depuis `aide09 = 0/12` à lr 2,0, alors que
les bras de R1 à ce pas sont `lr0_reference@2`, `td0@2`, `tdlam09@2` — jamais `td0_d0@2`, donc aucun contrôle de
CHEMIN — et que `td0@2` lui-même n'y rend que 1/12 : une seule issue était atteignable. Amendé le jour même par
`17cff006`. Le pré-vol POSE la bonne question (« l'instrument peut-il produire LES DEUX issues ? ») et
`assert_positive_control` / `assert_bar_is_reachable` y répondent — mais pour UNE cellule, UNE fois, au lancement.
Rien ne les rejoue à l'instant où une prose agrège plusieurs cellules en un mot (« réfutée », « invariant »,
« confiné »), et c'est ce mot qui est lu et cité.
**Forme demandée** : un verdict qui nomme plus d'un point de fonctionnement DÉCLARE, point par point, si ce point
porte son propre contrôle ; la garde refuse le vocabulaire de RÉFUTATION sur un point déclaré sans contrôle, et
accepte « non établie ». Déclaration plutôt que devinette — on ne sait pas décider automatiquement lequel des bras
est « le contrôle » d'un point, et proxifier ça serait la faute que le dépôt interdit ailleurs : même patron que
`tools/demand_marker.py::_degeneracy`. Domicile naturel : `tools/experiment_preflight.py`, à côté de
`assert_verdict_invariant_to_optimizer` qui est son cousin exact (lui garde l'invariance AU PAS, mais seulement
entre deux lr tous deux LISIBLES). Coût : une assertion, son contre-exemple gelé, sa mutation (porte 15) ; et
l'entrée au périmètre du cliquet de calibration si la fonction produit une affirmation.
**Deux règles apportées par la session du harnais, mesurées un étage plus bas sur la MÊME forme, et qui doivent contraindre la garde** : (1) *le vocabulaire du verdict doit avoir une branche pour « l'entrée ne permettait pas de décider »* — chez elle aucun `INCONCLUSIVE*` ne peut devenir un négatif, `_demand` les route vers `DEMAND_INCONCLUSIVE` et jamais vers `NOT_DEMANDED` ; sans cette branche l'auteur n'a pas d'autre mot que le négatif de fond, **et il le prend** (c'est littéralement ce que j'ai fait) ; (2) *l'ORDRE des branches est lui aussi une garde, et il peut PRÉEMPTER la protestation* — mesuré chez elle : un défaut qui déclenche bien l'alarme d'alias ressort quand même en `NOT_DEMANDED`, simplement parce que `NOT_DEMANDED` précède `INCONCLUSIVE_ALIAS` dans l'ordre scellé. La garde criait, personne ne l'entendait. Donc le refus du vocabulaire de réfutation doit être rendu **AVANT** qu'un verdict de fond ait pu être choisi, pas après.
**Contre-exemple gelé, offert et prêt à l'emploi** (mesuré par la session du harnais dans son propre code) : `_necessity` lisait `INCONCLUSIVE_INVERTED` — le bras SANS la pièce fait MIEUX, ratio 0,703, soit 1,42× dans l'autre sens — et publiait « aucun effet de l'ablation détecté ». Un effet de 1,42× annoncé comme AUCUN effet, par le fichier même qui route correctement ce verdict quand il s'agit de la demande, et qui avait survécu à un cliquet de calibration et à 135 tests verts. Il est du bon côté de la frontière que cette entrée décrit : à prendre tel quel plutôt qu'à fabriquer.
⚠️ Peut se reformer en SILENCE : n'importe quelle clôture future peut refaire exactement ça, hook au vert.
<!-- closes_when:grep_present=tools/experiment_preflight.py::assert_verdict_points_controlled -->



**P4.12 — rang 6 — ✅ CLOSE le 2026-09-16 (session loop 766eabae, accord agagi-c9 sur l'interface) — Sham LINÉAIRE à paramètres APPARIÉS pour la pièce `bilinear` : le contrôle EXISTE, est mesuré, et sa lecture scellée est `SHAM_PARTIEL`.**
Quoi : `(H·U + H·V)·W_sh` à MÊME nombre de paramètres que `((H·U)⊙(H·V))·W_bl` (rang 16), flag `BILINEAR_SHAM`,
~30 lignes dans `backend_torch.py::_step`, 1 cas de calibration (no-op exact quand OFF ; compte de paramètres ÉGAL au
bilinéaire quand ON — asserté, pas lu), puis 12 seeds × 300 épisodes de `bilinear_composition_probe` (CPU pur, minutes).
Remplace l'item « calcul dendritique multi-compartiments contre une tâche où le bilinéaire est prouvablement
incapable » : ce prérequis est IMPOSSIBLE en l'état (aucune borne supérieure prouvée sur la forme complète de `_step`,
deux rétractations du plain déjà payées — P2.77). Le contrôle qui manque n'est pas une tâche plus dure, c'est le sham.
Fait : `TorchPopulationModel.BILINEAR_SHAM` (défaut False = bit-identique ; ON = `((H·U)+(H·V))·W_bl`, MÊMES tenseurs U/V/W_bl, même init, même optimiseur — pas un `W_sh` séparé : le compte est égal PAR CONSTRUCTION), couture `bilinear_sham` dans `_train_eval_one`, 3 cas de calibration (no-op exact OFF, compte ÉGAL et sortie différente ON, drapeau restauré). Règle scellée `BILINEAR-SHAM-R1` AVANT toute cellule, le smoke seed 0 (sham 0,309) DÉCLARÉ dans la règle et EXCLU (seeds 1-12) ; runner `tools/bilinear_sham_run.py` (design déclaré, famille 72 cellules = 3 bras × 2 pas × 12 seeds, tampon de provenance), `results/bilinear_sham_r1.json`, 209 s. Compte de paramètres par agent ASSERTÉ puis publié dans `_regime` : plain 29,584, bilinéaire 37,840, sham 37,840. Bit-identité des bras plain/bilinéaire seeds 1-11 contre le JSON d'EDR-BILINEAR : **22/22**. Lecture scellée : **`SHAM_PARTIEL`** — à lr 0,02 : plain **0,270**, sham **0,315**, bilinéaire **0,934** ; à lr 0,002 (E19) : 0,180 / 0,189 / 0,413 ; sham ≤ plain + 0,05 sur **9/12** seeds (la branche `SHAM_INERTE` exigeait 11/12). ⚠️ **Ce compte a été RECTIFIÉ le 2026-09-24 : 8/12 → 9/12**, sans re-mesurer une seule cellule (les 72 restent identiques, cf. `_rectification` du JSON). Cause, trouvée par la revue d'agagi-52 et recomptée indépendamment seed par seed : le critère était comparé en FLOTTANTS alors que l'accuracy est un COMPTE sur `n_grille` = 640 évaluations (40 lots × 16 agents) et que la marge scellée 0,05 vaut EXACTEMENT 32 pas de grille — le seed 3 (`210/640` contre `178/640 + 32/640`) est une **ÉGALITÉ** que le binaire rendait fausse pour 1,19e-08 (0,328125 > 0,32812498807907104). Les 11 autres seeds sont identiques dans les deux arithmétiques et le VERDICT `SHAM_PARTIEL` ne change pas (9 < 11). Correctif à la SOURCE (`tools/bilinear_sham_run.py::_sous_barre`, comparaison sur la grille, repli déclaré si la marge n'est pas commensurable) + 2 cas gelés, et `n_grille` est désormais PUBLIÉ dans la lecture (une prémisse est une mesure). Règle apprise : **un seuil dont la marge est un multiple exact du pas d'une grille se compare sur la grille, jamais en flottants** — sinon le critère perd ses égalités, et il les perd TOUJOURS du même côté (celui qui refuse). La règle impose de RAPPORTER sans inférer : c'est fait. Faits POST-HOC, hors verdict, publiés pour qu'on puisse les chiffrer : sham ≥ barre 0,5 sur **0/24** cellules ; sham sous le plafond affine 0,3889 du plain sur **12/12** à 0,02 (la somme `H·(U+V)·W_bl` reste AFFINE en H — le sham est un terme linéaire de rang 16 ajouté à W) ; sham > plain sur 12/12 à 0,02 (+0,045 : de la capacité LINÉAIRE, pas de la composition) ; bilinéaire > sham + 0,05 sur 12/12 et 12/12. Le critère scellé « sham ≤ plain + 0,05 par seed » était un mauvais mètre pour « ne compose pas » ; le bon (distance à la barre) est vu APRÈS coup — une `BILINEAR-SHAM-R2` qui le scellerait doit le déclarer (E11), décision laissée à robla. Pour le registre de pièces (agagi-c9) : `matched_sham = {"bilinear_sham": True}` est désormais DÉCLARABLE (le contrôle existe et est mesuré) ; la nécessité de la multiplication n'est pas ÉTABLIE par la lecture scellée. Bandeau en tête d'EDR-BILINEAR.
<!-- closes_when:grep_present=src/agents/backend_torch.py::BILINEAR_SHAM -->

**P4.13 — rang 8 — OUVERTE (partie (a) mesurée le 2026-09-16, session loop 766eabae ; reste (b)) (ADR-005, item 3) — « Hormone » = δ_j = σ(W_jj), le seul levier de constante de temps à
une ligne : PUBLIER sa distribution sur le HoF (0 run), puis un facteur par agent sous garde E19.**
Quoi : (a) 0 run — `mamba_agent.delta_distribution(genome)` + un runner qui l'applique à chaque génome du HoF principal et des HoF famine (JSON sous `results/`, nom fixé par le runner) :
la distribution de δ_j = σ(clip(W_jj, ±10)) (min / médiane / max / part de nœuds à δ < 0,01 et > 0,99) — trois
entiers par nœud ; (b) ensuite seulement, un facteur par agent sur δ piloté par un signal qui EXISTE sous torch
(EMA|δ| ou Δénergie — jamais `surprise`, morte sous torch P4.8 ; jamais `W_router`, None sur tout agent frais et
absent de torch), flag OFF bit-identique, publié dans `regime`, jugé par `assert_verdict_invariant_to_optimizer` à
DEUX réglages du gate. Lire d'abord EDR-194 (LR_CLOSES, lr∝1/EMA(loss) sur le tronc) et COG-001 (LR_INSUFFICIENT sur
les readouts) : « le LIEU de la modulation décide ». ⚠️ La diagonale a DEUX écrivains (TD `mamba_agent.py:923-924`
n'exclut pas la diagonale ; mutation) — un facteur posé sur δ doit dire lequel il module.
Fait (a), 0 run : `mamba_agent.delta_distribution(genome)` (même formule que `MambaBatchModel.forward` et `_step` :
σ(clip(W_jj, ±10)) ; nan COMPTÉ et exclu ; aucune diagonale finie → None), runner `tools/delta_distribution_hof.py`
→ `results/delta_distribution_hof.json` (tampon de provenance), 7 cas de calibration (`tests/sandbox/test_delta_distribution.py`).
Mesuré sur les **30** génomes des trois HoF présents (principal, famine, famine_s43 ; 0 illisible, 0 non fini) :
**la diagonale est EXACTEMENT nulle sur 0,936 des nœuds de CHAQUE génome** (161/172, la même fraction sur les 30 —
deux jeux d'indices quasi identiques : nœuds 46-53, 70, 71, 74 ; 30 jeux de valeurs), donc **δ = 0,5 (médiane des médianes 0,500)
est GELÉ sur 161 nœuds** ; sur les 11 restants δ va de 0,007 à 0,993 ; part gelée (δ < 0,01) ≤ 0,017, part
instantanée (δ > 0,99) ≤ 0,006. Un agent FRAIS a 172/172 diagonales non nulles : la sparsification a mis la diagonale à
zéro, et `mutate_weights` ne touche que les poids NON NULS (EVO-009) — **l'évolution n'a AUCUN écrivain sur δ** ; seul le crédit
TD (`mamba_agent.py:923-924`) peut l'écrire, et il n'a jamais tourné sur ces champions. Conséquence pour (b) : un facteur par agent
sur δ multiplierait une CONSTANTE 0,5 sur 161/172 nœuds — c'est un bouton GLOBAL de constante de temps, pas une modulation
par nœud ; le design de (b) doit le dire et se mesurer contre ce plancher (sinon E8). Clause déplacée sur (b).
<!-- closes_when:grep_present=src/agents/backend_torch.py::DELTA_MODULATION -->

**P4.14 — rang 9 — ✅ CLOSE le 2026-09-16 (session loop 766eabae) — « Glia » réduit à une PUBLICATION : `compute_spent` / `brain_cost`
comme prix à côté de toute dose d'apprentissage.**
Quoi : `count_learning_events().summary()` publie `compute_spent_total` et `brain_cost_total` lus sur le monde (champs
existants : `world_1_stoneage.py:1284`, `mamba_agent.py:281-296`) — 0 ligne de moteur. Aucune pièce
`compute_allocation` tant que le backend torch ne porte pas de calcul allouable (`compute_spent = 0`, `backend_torch.py:155,172`)
et tant que le calcul ne coûte rien in-world (brain = −0,1 % du drain, EDR-099 ; un acte cognitif RAPPORTE +0,1) : une
grandeur qui n'agit pas ne s'instrumente pas (E2). L'allocateur legacy existant (rêve TTC, K∈[1,8] par agent) est OFF
sur 60/60 génomes HoF et son bénéfice est du BRUIT d'état (DREAM-002, sham = dream).
Fait, 0 ligne de moteur : `count_learning_events` enveloppe `forward` (legacy ET torch, pass-through bit-identique) et publie
`compute_spent_total` + `forward_calls` ; `run_learner_probe` pose `trace_energy_sinks` (DV **bit-identique** vérifiée : bloc
400, seed 2026, lr 0,001 — `hit_rate` 0,20635… / 4 754 décisions, identiques à R2) et publie `glia = {compute_spent_total,
brain_cost_total, energie_perdue_total, brain_share}`. Première mesure (legacy sous garde E28, 400 ticks) : `compute_spent`
**0** (aucun rêve), `brain_share` **0,11 %** — EDR-099 (« −0,1 % du drain ») reproduit à la sonde. 3 tests (compteur à 0,
rêve forcé K=4 chez un porteur d'organe → Σ = 4 avec sortie bit-identique à RNG apparié, sonde). Conclusion tenue : une
grandeur qui n'agit pas ne s'instrumente pas comme PIÈCE — elle est désormais publiée pour qu'on puisse le dire chiffré.
<!-- closes_when:grep_present=tools/learning_events.py::compute_spent -->

**P4.15 — ✅ CLOSE (2026-09-22, par la session P4.9 : record [[EDR-S2-CREDIT-ABLATION]] + `results/s2_credit_ablation.json`
committés, P4.9 CLOSE) — rang 3 — Graver `EDR-S2-CREDIT-ABLATION` : P4.9 est FINI et
son verdict change la lecture du crédit, mais il n'a ni record ni commit.**
Quoi (mesuré le 2026-09-16, sceptique C10) : `results/s2_credit_ablation.json` (non suivi, 74 977 o, 15 sept 12:04)
porte un bloc `verdict` complet — n=12, `SIGNAL_QUELCONQUE` / `EPISODIQUE_SUFFIT` / `ATTENUE_A_PETIT_PAS` ; S_a 36,0 /
S_full 8,0 / **S_zero 33,25** / S_neg 7,25 / S_lr 21,5 / S_tdoff 7,5 ; d_full −28,25, 12/12 négatifs ; 40 758 s
(≈ 11,3 h) ; `replication.identical = True` ; provenance git_sha 9de2b3b dirty. Lecture : le bras SANS signal n'érode
PAS (33,25 ≈ 36,0) ; le signe inversé érode autant que le complet ; TD coupé érode aussi (b_tdoff −29,0 à dW 0,08×) ;
l'érosion est portée par la voie ÉPISODIQUE seule et n'est PAS proportionnelle à Σ|ΔW| (0,08× érode autant que 1×).
Ce record est le prérequis de P4.11 (run n°3) et le backlog dit encore « SCELLÉE ET LANCÉE ». Je ne touche pas à
l'entrée P4.9 ni au JSON : ils appartiennent à la session qui a lancé le run.
<!-- closes_when:grep_present=docs/roadmap/PRIORITES_ET_DETTES.md::\n\*\*P4\.9 — ✅ CLOSE -->

**P2.68 — rang 14 — ✅ CLOSE le 2026-09-15 — 14 runners SCELLÉS sur 15 n'écrivent ni `git_sha` ni `dirty` dans leur JSON : leur règle est scellée par hash, leur code ne l'est pas.**
Fait : **un seul site**, `tools/preregister.py::provenance(name)` → `{git_sha, dirty, rule, seal}` (le sceau de la
règle voyage avec le code ; sans git → `None` + `error`, jamais une valeur) et `stamp(db, name)` pour les runners
REPRIS par cellules (un tampon par provenance DISTINCTE, dans l'ordre : un run repris sur trois commits porte
trois tampons). Les deux copies existantes (`learner_calibration`, `s2_credit_retention` → donc `s2_reward_ablation`)
délèguent. Portage : 6 runners à JSON (`evo011_preflight`, `s2_blind_champion`, `s2_subject_variance`,
`lang_memory_edge_run`, `lock001_proxy_r1`, `lock001_pred2_r1`) tamponnent leur JSON ; 8 runners dont l'ÉVIDENCE est
le stdout (`evo022`→`evo028`, `s2_floor_pronostic_run` — ils n'écrivent AUCUN JSON, seulement des `.npz` de génomes et
une lecture imprimée que les records transcrivent) impriment `[provenance] {...}` juste après `verify`. Témoin :
`test_every_sealed_runner_carries_the_provenance_stamp` (AST, sur les runners que la porte 11 reconnaît comme
SCELLÉS ; vérifié qu'il rougit sur un mutant sans l'appel) + 4 cas de `provenance`/`stamp`. Ce qui reste : les 8
runners à stdout devraient écrire un JSON de lecture (leur mesure n'est durable que dans le transcript du record) —
chantier à part, non ouvert ici.
Quoi : tamponner `{"git_sha": rev-parse HEAD, "dirty": bool(status --porcelain)}` (le bloc `provenance` de `tools/evo_runs/s2_credit_retention.py:248-252`, seul runner qui le fait) dans les 14 restants : `tools/evo_runs/evo011_preflight.py`, `evo022_run.py`, `evo023_run.py`, `evo024_run.py`, `evo026_run.py`, `evo026bis_run.py`, `evo027_run.py`, `evo028_run.py`, `s2_blind_champion.py`, `s2_subject_variance.py`, `tools/lang_memory_edge_run.py`, `tools/lock001_proxy_r1.py`, `tools/s2_floor_pronostic_run.py` (AUCUN tampon, aucun `commit` non plus) et `tools/evo_runs/s2_reward_ablation.py` (n'IMPORTE que le `git_sha` de P4.4 — `imported_git_sha` — sans tamponner le sien). Mesuré le 2026-09-15 en fermant P2.61 (P2.61 (3)), par `scan_runners` + grep `git_sha` / `dirty` sur chaque module. Pourquoi : un record qui cite l'un de ces JSON ne peut pas dire QUEL code a produit la mesure ; `Harness.save` le fait depuis juin, ces runners n'y passent pas. Extension naturelle : faire porter le tampon par `tools/preregister.py::verify` (un seul site) plutôt que 14 copies. *Coût : agent 1 h (tampon commun) ; calcul 0.* Dépend de : rien.
<!-- closes_when:grep_present=tools/evo_runs/evo028_run.py::git_sha -->

**P2.69 — rang 14 bis — ✅ CLOSE le 2026-09-15 — Angles morts de la GARDE DE BAIL, trouvés par les vérificateurs du 2026-09-15 : (i) bail ancré au dépôt, (ii) filet runtime, (iii) vert à bail libre.**
Quoi : (i) le bail `kuzu` vit dans `runs/leases` RELATIF au cwd (`tools/jobs/lease.py`) : un worktree ne voit pas le
bail tenu dans l'arbre principal — pendant le run P4.9, 503 tests simulant un monde ont TOURNÉ dans un worktree
(sautés dans l'arbre principal) ; les chemins `data/` étant relatifs eux aussi (`src/paths.py`), la KuzuDB n'est pas
partagée, mais la CHARGE l'est (E12 sur tout coût mesuré pendant) → ancrer le bail au dépôt (`git rev-parse
--git-common-dir`) ou le déclarer par worktree ; (ii) `tests/sandbox/test_p_reach_deconfound.py` simule un monde
(`_measure_forage` → `env.step`) sans AUCUN des `_WORLD_HINTS` de `tests/conftest.py` : la garde de bail ne le saute
pas pendant un run en vol → ajouter l'indice ou déclarer le fichier ; (iii) rouge PRÉ-EXISTANT dans ce même fichier
(`p_reach` 0,4479 vs 0,51 attendu, bit-identique à HEAD) : lire ou geler. Pourquoi : une garde qui ne voit pas
l'arbre partagé ne garde rien (E10). *Coût : agent 1-1,5 h.* Dépend de : rien.
Fait (ii), 2026-09-15 : pas un indice de plus — un **FILET RUNTIME**. Mesuré avant : **58 fichiers** de tests
importent un module qui construit un monde SANS porter d'indice (balayage AST à un niveau d'import), et
`test_p_reach_deconfound.py` a TOURNÉ 62 s de monde pendant le run P3.4, deux fois. `tests/conftest.py::_arm_runtime_net`
— armé par le hook de collecte quand un bail étranger est détenu — remplace `Biosphere3D.__init__` (dont héritent soup,
agricultural, industrial, famine, ground-truth ; Lewis est monté dessus) par un `pytest.skip` portant la même raison :
le test est sauté **au point de construction**. Même fichier après : 2 purs passés, 3 mondes sautés, 0,76 s.
Témoins : 3 cas dans `test_lease_guard.py` (saute à la construction, non armé sans bail, armé par le hook réel sans
indice textuel), restauration vérifiée. **Fait (i)**, à bail libre : `tools/jobs/lease._repo_root()` — `git rev-parse
--git-common-dir`, parent du `.git` COMMUN, mis en cache par processus ; sans git → cwd (ancien comportement) ;
vérifié RÉELLEMENT depuis `.claude/worktrees/wf_…-1` : le bail se résout sur `AGAGI/runs/leases` ; 3 tests
(`test_jobs.py` : ancré à la racine, worktree simulé → arbre principal, hors dépôt → cwd). ⚠️ Les worktrees existants
portent l'ANCIEN code tant qu'ils ne sont pas rebasés. **(iii)** : `test_p_reach_deconfound.py` **5/5 vert** à bail libre le
2026-09-15 (deux runs, bail libre) — le rouge signalé le matin a été vu pendant le run P4.9 ; la contention KuzuDB
est la cause DOCUMENTÉE d'une mesure de monde contaminée, mais elle n'est pas prouvée ici (pas reproduite) ; s'il
revient à bail libre, le lire ou geler à ce moment-là.
<!-- closes_when:grep_present=tests/conftest.py::_arm_runtime_net -->
**P2.82 — ✅ CLOSE (2026-09-23) — rang 14 quater — Un skip levé au MAUVAIS NIVEAU devient un verdict : quatre faux rouges sous bail `kuzu`,
reproduits (suite complète du PM, nuit du 22 au 23 ; 4 failed en 2,7 s sous le bail de P4.16).**
Quoi : (a) `tests/sandbox/test_s2_ablation_real_path.py` (2 cas, l.74 et l.92) prend `hold("kuzu")` LUI-MÊME et ne
porte AUCUN des `_WORLD_HINTS` de `tests/conftest.py` : la garde de collecte ne le saute pas, `ResourceBusy` (« détenue
par pid=… owner=s2-credit-ablation-2 ») devient FAIL. Un test qui tient un bail est par définition un test de monde :
faire de `ResourceBusy` à la prise de bail par un test un `pytest.skip` nommant le détenteur (même issue que la garde de
collecte), et ajouter `hold(` aux indices. (b) `tests/test_backend.py::test_flatland_runs_crud` et
`::test_ws_flatland_run_id_streams_frames` : le `Skipped` du garde runtime (`_arm_runtime_net`) est levé DANS
l'application ASGI, traversé par Starlette et rendu « RuntimeError: No response returned » / `BaseExceptionGroup` =
FAIL. Le skip se décide dans le test (fixture), jamais dans le code servi. Pourquoi : les deux formes n'apparaissent
QUE bail tenu — invisibles à toute suite lancée machine au repos, donc jamais vues par la CI (E14 : la garde de
collecte, apprise sur un cas, n'a pas été généralisée aux tests qui la contournent ; E10 : « sautée, jamais rouge »
était une règle documentée, pas exécutée). Contre-exemples à geler : un test qui appelle `hold` sous détenteur étranger
est SKIPPED, pas FAILED ; un `Skipped` levé côté serveur ne traverse pas l'app.
**Livré le 2026-09-23 (sous le bail de P4.16, seul moment où les deux issues étaient mesurables)** : hook
`pytest_runtest_call` de `tests/conftest.py` (ResourceBusy pendant l'appel → skip nommant le détenteur ; toute
autre exception passe) ; fixture `sans_bail_etranger` (décision `_skip_si_bail_etranger`, calibrée sans monde) posée
sur les deux tests backend ; `tests/sandbox/test_lease_skip_guard.py` (6 cas : conversion, spécificité, deux
bouts-en-bout sous détenteur PRÉSENT ou FACTICE — un sous-processus enfant qui tient `kuzu` 120 s, lancé par le
test lui-même quand le bail est libre, donc mesurable AUSSI machine au repos —, décision au repos / sous détenteur,
câblage de la fixture). **Remis au PM (suite complète = son périmètre), hors de cette entrée** : un job CI ou une passe manuelle « suite complète sous
bail tenu par un détenteur factice » (`tools/jobs/run.hold` dans un sous-processus pendant `pytest tests/`), sans
quoi la prochaine forme de ce défaut sera découverte par la suite de nuit de quelqu'un d'autre — E12 côté tests :
une suite mesurée machine au repos ne mesure pas l'état « bail tenu ». *Coût : agent 1 h ; calcul 0.*
Dépend de : rien. Occurrence au registre : E14 (2026-09-23, session d7).
<!-- closes_when:grep_present=tests/conftest.py::ResourceBusy -->
**P2.101 — rang 14 quinquies — La PERTE DE NOMMAGE : réécrire la prose d'un record peut dé-nommer une grandeur
SCELLÉE sans la substituer — indétectable par l'auteur, refusé par la porte 5, et découvert au commit.**
Quoi (mesuré le 2026-09-24 sur moi-même, P4.16) : après une revue adversariale, j'ai réécrit le tableau de
`EDR-S2-CREDIT-ABLATION-2` pour le rendre lisible — « TD seul », « 1999 », « 0,71 » à la place de `S_tdonly`,
`dose_tdonly`, `dW_tdonly`. Aucune DV n'était substituée, aucun chiffre faux, la mesure était la bonne : seules
les ÉTIQUETTES avaient disparu. `check_preregistration_applied` a refusé le commit en listant **huit** grandeurs
exigées par la règle scellée et absentes du record (`S_eplr`, `S_tdonly`, `dW_const`, `dW_eplr`, `dW_full`,
`dW_tdonly`, `dose_const_ep`, `dose_const_td`, …). La porte a eu raison — son contrat est LEXICAL et elle ne peut
pas distinguer « dé-nommée » de « substituée », ce qui est précisément sa valeur. Mais le coût tombe au pire
moment : l'auteur l'apprend après les douze portes de l'export, plusieurs minutes, sur un arbre partagé où HEAD
bouge. Ce n'est ni un faux ni une omission : c'est une **perte de nommage**, une forme qu'aucune entrée du backlog
ne décrivait. Elle frappe exactement les récritures qui AMÉLIORENT un record, donc elle taxe la correction.
Remède proposé, bon marché : un mode LISTANT de la porte — `python tools/check_preregistration_applied.py --names
docs/EDR/<record>.md` qui rend, en quelques secondes et sans rien juger, les grandeurs que les règles scellées
dont ce record se réclame l'obligent à nommer, avec celles qui manquent. L'auteur l'appelle PENDANT qu'il écrit,
pas après. Deux cas de calibration : un record complet rend une liste de manquantes VIDE ; un record dont on
retire une étiquette la voit apparaître (et le mode ne doit pas, lui, prononcer de verdict : il RAPPORTE).
Vu en passant, à consigner par le PM (son périmètre) : le hook `pre-commit` ne s'exécute pas sur un merge propre
(0 appel contre 1 pour un commit ordinaire, mesuré par agagi-11) — les douze portes ne s'arment pas à la fusion.
*Coût : agent 1 h ; calcul 0.* Dépend de : rien.
<!-- closes_when:grep_present=tools/check_preregistration_applied.py::--names -->

**P2.108 — rang 12 bis — CLOSE (2026-09-24) — Les portes ne tiraient JAMAIS sur l'union de deux branches, et
la copie deployee des crochets ne repondait de rien. Les deux trous sont fermes, avec leurs contre-exemples.**
Quoi (mesure, depot JETABLE, git 2.54.0.windows.1). Sur une fusion PROPRE : `pre-commit` **0 appel** (1 sur un
commit ordinaire, controle positif fait), `commit-msg` 1 appel avec MERGE_HEAD present et un code 1 **annule la
fusion**, `post-merge` appele mais **son code de retour est ignore**. Le cas est vivant, pas theorique : deux
sessions corrigent le meme compte publie en comptant des objets DIFFERENTS ; chaque branche est localement juste,
l'union est fausse, et aucun conflit git ne le signale. Deux collisions de numeros de backlog reelles le meme jour
(rapportees par `agagi-c9`) ont la meme cause : la cle `numero-double` de `check_backlog_freshness` EXISTE et sait
les attraper -- elle ne tournait simplement pas au moment ou une fusion introduit le doublon.
⚠️ DEUXIEME MESURE, et c'est elle qui decide la forme : relancer le `pre-commit` TEL QUEL ne suffit pas. Ses
**17 appels** a `git diff --cached --name-only` comparent l'index au PREMIER PARENT, donc au seul cote entrant.
Quand les deux branches portent la MEME valeur de balise -- le cas qui ne conflicte pas, donc le cas dangereux --
le document PORTEUR DU COMPTE est identique a HEAD : absent du diff, porte non armee. Un crochet naif aurait laisse
passer son propre contre-exemple. D'ou la comparaison a la BASE DE FUSION (bloc `AGAGI:FUSION-SCOPE`), qui vaut
aussi pour un SQUASH -- lequel ne pose AUCUN MERGE_HEAD et reproduisait le trou integralement.
Livre : `tools/hooks/commit-msg` (relance les portes sur une fusion propre, jamais deux fois), les deux blocs
balises de `tools/hooks/pre-commit`, `tools/check_hook_deployment.py` + sa baseline (porte 22),
`tests/sandbox/test_hook_on_merge.py` (16 cas) et `tests/sandbox/test_hook_deployment.py` (18 cas).
Ce que DEUX revues adversariales ont coute, et pourquoi elles valaient leur prix : la v1 du temoin (fichier VIDE
juge sur sa PRESENCE) et la v2 (horodatage + HEAD + MERGE_HEAD) ont ete REFUTEES toutes les deux. La v2 tombait sur
une sequence sans rien d'anormal, reproduite 4 fois : fusion refusee -> MERGE_HEAD reste -> l'auteur corrige et
recommite -> `pre-commit` PASSE et pose le temoin -> le commit AVORTE a l'editeur, donc `commit-msg` n'a rien
consomme -> un temoin VALIDE survit dans un git-dir PARTAGE et desarme la fusion suivante, avec un index DIFFERENT.
Classe **E31** (l'identite d'une garde omet CE QU'ELLE A VERIFIE) ; remede : 4e ligne = `git write-tree`. Classe
**E32** trouvee dans la meme passe (une garde degrade son PERIMETRE en silence : `git merge-base` rend du vide sur
des histoires sans ancetre commun, la portee retombait au premier parent sans le dire).
⚠️ CE QUI RESTE A FAIRE, ET QUI N'EST PAS UN DETAIL : `tools/hooks/commit-msg` est LIVRE mais **PAS DEPLOYE**.
`core.hooksPath` vaut un chemin ABSOLU vers le `.git/hooks` du depot principal : le deployer arme la FLOTTE
ENTIERE d'un coup. C'est un acte ANNONCE, pas l'effet de bord d'un commit -- la baseline de la porte 22 le dit et
le tolere explicitement, et c'est son retrait qui rendra la garde effective sur ce crochet.
⚠️ DOUBLON A RESORBER A LA FUSION, et il n'est pas de la meme nature que les collisions de NUMERO : `agagi-c9`
porte sur une branche non fusionnee une entree **P2.104** (« aucune porte ne tourne a la fusion ») qui decrit le
MEME defaut, mesure independamment, avec pour remede l'installation d'un `pre-merge-commit` / `commit-msg`
relancant au moins les portes de compte et de doublon. Deux entrees sur le meme mecanisme polluent le backlog :
celle-ci est le LIVRABLE (code + 34 cas geles), P2.104 est le CONSTAT. A la fusion, n'en garder qu'une -- et c'est
`agagi-c9` qui decide du sort de la sienne, pas moi. La garde de copie `tools/hooks` -> `.git/hooks`, elle, n'a
d'equivalent nulle part : c'est la partie de ce lot qui ne peut pas faire doublon.
⚠️ NUMERO, et c'est la TROISIEME collision du jour : ce chantier a ete annonce sous **P2.102** dans la prose du
2026-09-24 ; P2.102 etait deja pris par une entree committee d'une branche non fusionnee (`agagi-c9`). Regle
d'arbitrage retenue (proposee par `agagi-c9`, confirmee par le PM) : **le numero NON ENCORE COMMITTE cede**. Le PM
a propose 107 ; `agagi-c9` rapporte qu'`agagi-52` le vise deja, donc 108/109, verifies libres sur le motif
d'EN-TETE (`^**P2.`) dans la branche principale -- une recherche en prose trouve aussi les CITATIONS d'autres
entrees et fabrique des collisions imaginaires, piege paye deux fois aujourd'hui.
⚠️ Et l'occurrence qui vaut le plus cher est la troisieme : **elle s'est formee dans le message de coordination du
PM lui-meme**, celui qui m'annoncait qu'un crochet mecanique rendrait ces collisions impossibles -- un numero donne
de memoire, sur une liste de reservation incomplete. Le PM, dont c'est le perimetre, en a produit une a la main en
expliquant pourquoi il ne fallait pas creer un role d'Integrateur pour les eviter. C'est l'argument, et il n'est
pas rhetorique : **la parade n'est pas quelqu'un qui surveille, c'est une garde qui tourne au moment ou ca casse**.
La cle `numero-double` de `check_backlog_freshness` savait attraper les trois ; elle ne tournait pas la ou elles
naissent. *Cout : agent 4 h ; calcul 0.*
⚠️ REFUTEE PUIS CORRIGEE LE JOUR MEME (commit 3e26caf2, puis le suivant). La re-verification
adversariale lancee AVANT le premier commit a rendu son verdict APRES : REFUTE, quatre griefs de
gravite HAUTE, tous mesures en depots jetables avec controle apparie, et 4 mutations sur 9
survivantes. Le premier commit le dit dans son message -- il livrait du code teste, pas un verdict.
Ce qui est tombe, et ce qui le remplace :
1. LE TEMOIN EST SUPPRIME. Son identite couvrait l'INDEX (`git write-tree`) alors que les portes de
   ce depot jugent le DISQUE, et l'arbre est PARTAGE donc le disque change tout seul pendant qu'un
   editeur est ouvert. Mesure APPARIEE : le meme etat du monde passe rc=0 avec ZERO porte quand le
   residu est la, et est REFUSE rc=1 sans lui. Trois identites essayees, trois refutees -> on ne
   raffine pas une quatrieme, on retire le raccourci. Le cout est chiffre et borne : les portes
   tournent DEUX fois sur une fusion conflictuelle, ce qui etait deja paye des qu'un editeur
   depassait 120 s. Quatre mutations survivantes disparaissent avec lui. Classe E31, occurrence 2.
2. `commit-msg` VERIFIE AVANT D'ANNONCER. Il imprimait « portee = base de fusion » sans verifier que
   le pre-commit qu'il lance porte le bloc -- et le pre-commit DEPLOYE ne le portait pas (0
   occurrence mesuree). La fusion fautive passait pendant que le crochet imprimait le contraire.
3. `CHERRY_PICK_HEAD` entre dans la portee : un cherry-pick CONFLICTUEL arme bien le pre-commit mais
   ne pose pas MERGE_HEAD, donc la portee restait le premier parent -- le trou du squash sur une
   autre reference. `REVERT_HEAD` est exclu DELIBEREMENT (le commit annule est un ancetre, la base
   serait lui-meme et la portee engloberait tout l'historique depuis) et une garde d'ancetre rend ce
   raisonnement executable au lieu de le laisser en commentaire.
4. CE QUI RESTE NON COUVERT, ECRIT NOIR SUR BLANC plutot que laisse en creux : `git rebase`,
   `git cherry-pick` PROPRE et `git pull --rebase` rendent rc=0 avec ZERO appel de pre-commit ET de
   commit-msg (seul `prepare-commit-msg` tourne, et il ne peut rien refuser). La voie d'integration
   la plus courante du depot n'est donc couverte par AUCUN crochet de commit, et ca reste vrai apres
   cette livraison -- la protection de ces voies doit vivre en `pre-push` ou en CI. Une session
   voisine a annule son rebase sur cette seule mesure.
LA LECON DE METHODE, qui vaut plus que les quatre correctifs : une revue adversariale qui lance ses
propres sondes a tue DEUX versions successives d'une garde de quinze lignes, dont une que son auteur
croyait avoir durcie une heure plus tot. Aucune relecture ne les aurait vues ; les deux refutations
sont venues de sequences ORDINAIRES, sans malveillance ni fabrication.
DEPLOIEMENT FLOTTE (2026-09-24, soir, sur demande de robla) -- deux defauts trouves EN LE PREPARANT, avant
tout cp, et fermes avec leurs cas geles :
(a) UN CROCHET PARTAGE BLOQUE LES BRANCHES ANTERIEURES A SES PORTES. core.hooksPath est ABSOLU : les trois
    worktrees actifs (harness-r1, pilotage, pm-portes) executent le pre-commit deploye, et AUCUN de leurs
    branches ne porte tools/check_hook_deployment.py (mesure : git cat-file -e <branche>:... rend non pour les
    trois). Python rend 2 sur un fichier absent, la porte le lit comme un refus : deployer la porte 22 aurait
    bloque tous les commits de ces trois worktrees. Bloc AGAGI:PORTE-ABSENTE : une porte dont le fichier
    manque A LA FOIS sur le disque et dans HEAD (signature d'une branche anterieure) est sautee ET DITE ;
    une porte presente dans HEAD mais supprimee sur le disque bloque toujours. tests/sandbox/test_hook_porte_absente.py.
(b) LA PORTE 22 NE CONNAISSAIT QUE L'HISTORIQUE DE HEAD : vu depuis une branche divergente, le contenu
    deploye n'est dans aucun de ses commits, donc INCONNU (« code jamais relu ») et blocage. Historique
    elargi a toutes les references (--all) ; ce qui doit bloquer est ce qui n'a existe NULLE PART.
<!-- closes_when:grep_present=tools/hooks/pre-commit::check_hook_deployment -->

**P2.109 — rang 12 ter — ⚠️ OUVERTE (2026-09-24) — La moitie MANQUANTE de la regle des commits path-scopes : un
pathspec qui NOMME un fichier qu'une autre session est en train d'ecrire l'emporte, et rien ne le dit.**
Quoi (reproduit le 2026-09-24 sur l'arbre principal, 5 sessions actives). La regle du depot -- « tout commit passe
par `git commit -- <chemins>`, JAMAIS nu » -- protege contre le commit NU, qui emporte l'index ENTIER. Elle ne
protege PAS contre le cas symetrique : `git commit -- <chemins>` prend le **contenu de l'ARBRE DE TRAVAIL** des
chemins nommes (verifie en depot jetable : HEAD=V1, index=V2, disque=V3 -> le commit grave V3). Nommer dans son
pathspec un fichier qu'un autre edite grave donc son travail en cours, sous un message qui ne le decrit pas.
L'incident : un lot de 11 chemins incluait `tools/hooks/pre-commit`, que cette session modifiait depuis une heure.
Il n'a pas atterri (le hook l'a refuse pour une autre raison), et l'auteur travaillait dans un worktree LIE -- donc
sa copie, pas la mienne. Mais l'isolation etait un ACCIDENT HEUREUX, pas une garde : les cinq sessions de l'arbre
PRINCIPAL sont exposees, et c'est la que le plus gros du travail se fait.
Pourquoi ca peut BLOQUER alors que la garde existante se contente d'avertir, et c'est le point de bascule (argument
de `agagi-c9`) : `tools/hooks/pre-commit` lance deja `check_staged_authorship` en mode scan avec `|| true`, et le
commentaire au-dessus dit pourquoi -- la PREEMPTION n'est pas reparable par celui qui commite (le travail de la
victime est deja dans HEAD), et un cliquet qui bloque sur de l'irreparable est un cliquet qu'on desactive. Le cas
inverse, lui, est REPARABLE a l'instant ou il se produit : il suffit de retirer le chemin du pathspec. **Un cliquet
doit bloquer sur du reparable et avertir sur l'irreparable** -- regle a retenir, elle explique proprement pourquoi
certaines gardes de ce depot refusent et d'autres crient.
Remede propose : au `pre-commit`, confronter les chemins STAGES aux empreintes de `check_staged_authorship` et
REFUSER quand l'un d'eux porte l'empreinte d'une AUTRE session, avec le nom du proprietaire et la commande de
retrait. ⚠️ Deux garde-fous a ne pas oublier, sans quoi la garde sera desarmee en trois faux positifs : (a) en
worktree LIE le cas n'existe pas -- chaque worktree a sa copie, mesure a l'appui (blobs distincts) -- donc la
comparaison porte sur l'arbre que CE commit va prendre, jamais sur celui d'un autre worktree ; (b) une empreinte
perimee (session morte) ne doit pas bloquer eternellement : TTL, comme les bails de `tools/jobs`.
Contre-exemple a geler dans la meme passe : deux empreintes concurrentes sur le meme chemin -> REFUS ; une seule
empreinte, la sienne -> PASSE. *Cout : agent 2 h ; calcul 0.* Depend de : rien.
⚠️ DEUX EXCEPTIONS A LA REGLE AFFICHEE, mesurees le 2026-09-24 et ecrites nulle part -- elles
appartiennent a cette entree parce qu'elles portent sur la MEME phrase de CLAUDE.md (« tout commit
passe par `git commit -- <chemins>`, JAMAIS nu ») :
(a) PENDANT UNE FUSION, `git commit -- <chemins>` est FATAL : `cannot do a partial commit during a
    merge`, exit 128. Le commit NU est alors le SEUL chemin disponible. La regle affichee est donc
    inapplicable exactement la ou le risque de tout emporter est le plus grand, et personne ne le
    sait avant de buter dessus. A ecrire A COTE de la regle, pas a sa place.
(b) LA TECHNIQUE D'INDEX TEMPORAIRE DU DEPOT, appliquee a une fusion, est ACCEPTEE par git et ne fait
    PAS ce qu'on croit : `GIT_INDEX_FILE=<tmp> git commit -F msg` pendant une fusion conflictuelle
    resolue rend rc=0, le commit porte bien DEUX parents -- donc il conclut la fusion -- mais son
    arbre est celui de l'INDEX TEMPORAIRE. Le cote entrant est PERDU tout en etant enregistre comme
    fusionne, et les portes tirent sur l'index temporaire, pas sur l'union. C'est la contradiction la
    plus silencieuse des trois : elle produit un commit de fusion d'apparence normale. Ce depot
    commite par index temporaire tous les jours ; la regle a en tirer est simple et executable :
    **ne jamais conclure une fusion par la technique d'index temporaire** -- verifier `MERGE_HEAD`
    avant de la lancer, et refuser.
<!-- closes_when:grep_present=tools/hooks/pre-commit::check_pathspec_collision -->

⚠️ **TROISIÈME VECTEUR DU MÊME OUTIL, mesuré le 2026-09-24 — le commit par index TEMPORAIRE n'avance pas
l'index PARTAGÉ, et l'écart devient une ANNULATION de HEAD sous un commit nu.** Un commit fait sous
`GIT_INDEX_FILE` fait avancer HEAD sans toucher l'index partagé : pour chaque chemin committé, celui-ci garde
l'ANCIENNE version. `git status` la présente alors comme un changement stagé qui revient en arrière, et tout
commit qui emporte l'index l'installerait — donc supprimerait du travail déjà publié.
**Mesure, faite à deux sessions puis recoupée** : l'index partageé portait ADR-005 à **131 lignes** contre 152
dans HEAD et sur le disque, l'amendement du critère de révision manquant ; et les deux blobs de l'index
correspondaient EXACTEMENT à des commits antérieurs — vérifié, le blob de l'ADR est celui de `3e2a9f83`
(11:41) et celui du registre celui de `a49f839c` (17:24). Le reset n'a donc rien pu perdre, et la séquence est
complète : un script qui fait le reset laisse l'index juste ; le commit suivant fait par index temporaire le
laisse en arrière.
**Remède, une ligne à la FIN de toute procédure de commit par index temporaire** : `git reset -q --` suivi des
chemins committés, avec vérification que le pathspec n'est pas vide. Ça ne touche QUE l'index partagé et le
remet sur le nouveau HEAD. Mesuré chez moi : **19 scripts** de commit utilisent un index temporaire, **aucun**
ne faisait ce reset.
⚠️ **La racine est commune aux TROIS vecteurs de cette technique**, et c'est ce qu'il faut retenir plutôt que
les trois cas : le commit par index temporaire est ISOLÉ par construction — c'est sa vertu, il n'emporte pas le
travail d'autrui — mais isolé signifie qu'il ne propage RIEN vers les deux autres états qui comptent, le
DISQUE et l'INDEX PARTAGÉ. (1) Lire HEAD plusieurs fois dans un même script annule les commits des autres ;
(2) écrire le disque depuis son blob détruit leurs hunks non committés ; (3) ne pas rafraîchir l'index laisse
un piège armé contre HEAD. Chaque vecteur est un état qu'on a oublié de faire avancer AVEC HEAD.
**P2.110 — rang 12 quater — ✅ CLOSE le 2026-09-24 (code livré ; ouverte le même jour, extraite du bloc P4.17) — Le cliquet de COÛT
projette depuis UNE cellule, sur une horloge MUR, et ne dit pas POURQUOI il coupe : trois défauts mesurés le même jour
sur la même expérience, dont l'un a déjà produit une sur-déclaration et un autre une preuve fausse dans un record.**
Quoi. (i) **`_regime.coupe` ne porte qu'une PHRASE — et elle MENT sur la coupe courante.** Les deux coupes E13 de
TD-STEP-PILOT-R2 sont marquées `coupe=True` à l'identique alors que leurs natures sont OPPOSÉES : `lr 2,0` a été coupée
par CONTENTION (unité 217,4 s machine chargée) et RÉCUPÉRÉE par la reprise déclarée (unité 196,4 s machine libre) ;
`lr 1,0` est STRUCTURELLE — elle tient machine libre, c'est une sous-estimation au scellement. Un lecteur ne peut pas
les distinguer, et la clôture de P4.11 en a tiré « invariance au pas RÉFUTÉE » avant d'être amendée en « NON ÉTABLIE »
(`17cff006`, `181a9819`). Mesuré en ré-écrivant cette entrée : la `raison` publiée pour la coupe COURANTE de `lr 1,0`
(60 clés) est « relevee (--relever-coupe) : unite re-mesuree machine libre » — la raison de la LEVÉE, pas celle de la
re-coupe (95 unités × 196,4 s × marge 1,5 = 466 min > 240) : `tools/td_step_pilot.py` pose la coupe par `setdefault`,
qui conserve le dict écrit par `--relever-coupe`. À faire : un vocabulaire FERMÉ `nature` ∈ {`contention`,
`structure`, `budget`} à côté du drapeau, et une raison écrite à CHAQUE coupe. Sens déclarés : `budget` = projection
> budget, charge au moment de la mesure NON qualifiée (le seul fait établi — le « je ne sais pas » de la porte 14, pas
un défaut) ; `contention` = unité mesurée sous une charge MESURÉE, coupe PROVISOIRE, reprise déclarée due ;
`structure` = la coupe tient sur une unité mesurée machine LIBRE. Une reprise RE-QUALIFIE la coupe précédente dans
`coupes_precedentes` (récupérée → `contention` établie ; re-coupée → `structure`).
(ii) **L'unité est mesurée sur UNE cellule et appliquée à une grille HÉTÉROGÈNE.** La règle scellée justifie sa
projection par « cellules uniformes : mêmes épisodes, mêmes agents » ; mesuré sur les 28 cellules chronométrées de la
reprise, c'est FAUX — `lam05` 161,9 s, `lam099` 157,6 s, `td0_d0` **56,2 s**, soit **2,8×** entre familles de bras (le
contrôle de chemin n'a ni trace ni délai). L'unité est prise sur la PREMIÈRE cellule neuve, qui appartient à la
famille lente : la projection sur-estime et le cliquet mord plus qu'il ne devrait. C'est **E8 appliqué au modèle de
coût** — une prémisse posée en décor, scellée par moi. À faire : unité PAR BRAS (`project_cost_per_arm`) quand les
bras diffèrent, ou sceller explicitement « unité du bras le plus lent, projection MAJORANTE » et le dire dans le record.
(iii) **L'unité de la projection est du temps MUR, et le record dit le contraire.** `_mesure` rend `time.time() - tc`,
et c'est cette valeur qui entre dans `project_cost` ; P2.78 ne gate sur le CPU que `CostGuard.tick`, que ce runner
n'appelle pas. C'est précisément pourquoi une contention a pu gonfler l'unité (217,4 s contre 196,4 s) et couper une
ligne. Or [[EDR-TD-STEP-PILOT-R2]] écrit que la DÉCISION du garde « est gouvernée par le temps CPU du processus » : la
conclusion qu'il en tire (les deux rafales n'ont pas touché la décision) est JUSTE, mais pour une autre raison —
l'unité est mesurée sur la première cellule, AVANT les rafales. Preuve fausse, conclusion juste : **E33**, dans mon
propre record. À faire : rectifier le record par un bandeau ; publier `unite_cpu_s` et la charge au moment de la
mesure à côté de `unite_s` — ce sont elles qui permettent de qualifier `nature`. ⚠️ Ne PAS basculer la projection sur
le CPU : `budget_s` est du mur, et un run torch multi-thread rend un CPU > mur (`tools/cost_guard.py`, docstring,
point (c)).
⚠️ Ce qui rend l'ensemble mordant, et qui vaut plus que les correctifs : **une projection à 6 % de son seuil transforme
10 % de contention en une ligne de grille perdue** (255 min contre 231 min pour un budget de 240) — la fragilité est
dans la MARGE entre projection et budget, et rien ne la publie aujourd'hui. Preuve : `results/td_step_pilot_r2.json`
(`_regime.coupe`, `_regime.coupes_precedentes`), [[EDR-TD-STEP-PILOT-R2]] § « Coût, coupes, et pourquoi leurs natures
diffèrent ». *Coût : agent 1 h 30 ; calcul 0.* Dépend de : rien.
**✅ CLOSE le 2026-09-24 — code livré, et la revue a changé le design sur trois points.** `tools/cost_guard.py` :
`NATURES_COUPE`, `classify_cut_nature` (INSTRUMENT, déclaré dans `CALIBRATED`, 12 cas à réponse connue dans
`tests/sandbox/test_cost_guard.py`), `cut_geometry` / `cut_record`, `margin_to_budget`, `LoadWindow`, `cost_per_arm` /
`project_cost_per_arm` ; et `project_cost` refuse désormais une unité NaN ou négative (`nan > budget` valait False : la
garde ne pouvait pas échouer, E1). `tools/td_step_pilot.py`, `main_r2` seul : la décision est extraite en fonction PURE
`_decider_coupes_r2`, **bit-identique à l'ancienne boucle sur 610 cas** (aléatoires seedés, égalité exacte au budget,
unité nulle, et les deux points publiés : 96 clés à 3 587,78 s, 60 clés à 10 308,46 s) ; la coupe est RECONSTRUITE à
chaque passe (plus de `setdefault`, clause `holds_when` ci-dessous), avec une raison PAR LIGNE ; le temps de CHAQUE
cellule est persisté (`_temps_s`) ; l'unité CPU et la charge sont publiées à côté de l'unité mur, qui reste la seule à
décider. Trois écarts à l'énoncé, tous issus de la revue (deux critiques adversariales, 32 amendements dont 7
bloquants) : (1) la nature se décide PAR LIGNE et non par mesure — les deux lignes de la passe 1 ont été coupées sur la
MÊME unité, donc un classifieur de la mesure leur rendait forcément la même nature, ce qui est le défaut (i) lui-même ;
ce qui distingue les lignes, c'est leur dépassement (1,065 pour lr 2,0 ; 2,424 pour lr 1,0) et leur unité de bascule
(204,3 s ; 89,7 s), désormais publiés ; (2) le mot `budget` devient **`indeterminee`** — toute coupe est causée par le
budget, et un libellé d'absence qui ressemble à une cause de fond est le biais absence → affirmation ; (3) la charge est
la charge EXTÉRIEURE INTÉGRÉE sur la fenêtre de la cellule (`LoadWindow`, en cœurs, lectures HORS du chronomètre : un
capteur posé dedans aurait gonflé l'unité scellée elle-même, E11), jamais un instantané ni un compte de processus (qui
mesure la PRÉSENCE, pas la charge). Seuil `COEURS_EXTERIEURS_LIBRE_MAX` = 8,0 cœurs, déclaré PROVISOIRE et non calibré
comme certificat ; `contention` n'est ÉTABLIE que par la RÉPLIQUE de la même cellule, jamais en comparant deux cellules
différentes (E8). Tests : `test_cost_guard.py` 10 → 29, `test_td_step_pilot.py` 22 → 34, 79 verts. ⚠️ **Ce que la
clôture ne corrige PAS, et qui est dit** : le JSON publié de R2 garde sa raison fausse (artefact d'un record fermé, non
réécrit) ; et sur l'entrée historique réelle, le classificateur rend `indeterminee` pour les DEUX lignes — il ne confirme
pas les natures que le record attribue, et la revue en donne une raison chiffrée sur les totaux committés : la reprise
dite LIBRE a un rapport CPU/mur de 0,78 (4 836 / 6 226 s), la passe 1 dite CHARGÉE de 1,80 (2 142 / 1 191 s). Le bandeau
de rectification du record (point (iii), E33) part dans un commit séparé.
<!-- closes_when:grep_present=tools/cost_guard.py::(?s)^(?=.*NATURES_COUPE)(?=.*def project_cost_per_arm) -->
<!-- holds_when:grep_absent=tools/td_step_pilot.py::(?m)^[^#\n]*setdefault\("coupe" -->

**P2.83 — ⚠️ OUVERTE (2026-09-24, vue en passant pendant la revue de la spec du dashboard Pilotage) — le cliquet de
calibration ne connaît NI `compute_*` NI `parse_*`, et une déclaration qu'il ne détecte pas est ignorée EN SILENCE :
7ᵉ angle mort de nommage, dette nette CHIFFRÉE à 7 fonctions.**
Quoi : `tools/check_instrument_calibration.py` porte **14 motifs** (`*verdict*`, `measure*`, `run_*`, `classify*`,
`benchmark*`, `assert_*`, `compare*`, `sweep*`, `probe*`, `learn*`, `compute_policy_gradient`, `*_survival_eras`) et
aucun ne capte `compute_*` ni `parse_*` — vérifié le 2026-09-24 en passant les deux signatures aux motifs chargés
depuis le module : zéro correspondance. Or une déclaration `CALIBRATED` dont le nom n'est pas détecté n'est pas
signalée : elle tombe dans la branche « déclaration périmée » et est **ignorée sans un mot** (`:249`, et le commentaire
`:74` le dit déjà pour le 5ᵉ angle mort `assert_*`). Déclarer un instrument nommé `compute_…` revient donc à ne rien
déclarer, et c'est la classe **E10** appliquée au cliquet lui-même. Coût de l'élargissement, mesuré AVANT de le
décider (règle du dépôt : chaque élargissement révèle de la dette réelle, on la compte d'abord) : **7 fonctions non
déjà captées** — `tools/pm/roles_counts.py::compute_counts` (un instrument du PM, qui publie le ratio
science/méthodo), `tools/compositional_transfer_probe.py::compute_transfer`,
`tools/cartography.py::parse_territories`, `tools/consolidate_records.py::parse_record`,
`src/visualization.py::compute_genome_layers`, `src/graph_rag/reflexive_supervisor.py::compute_trend`,
`src/metaprog/rsi_loop.py::parse_demand_response` ; les cinq `compute_*_verdict` du dépôt sont déjà prises par le
motif `*verdict*`, donc l'élargissement ne les compte pas deux fois. À faire : ajouter les deux motifs, geler les 7
(ou les calibrer), et une ligne dans `check_gate_mutation.PORTES` pour la porte 2 qui rougit si un motif est retiré.
⚠️ La déclaration silencieusement ignorée est le vrai défaut : même sans élargissement, le cliquet devrait CRIER
quand une clé de `CALIBRATED` ne correspond à aucun symbole détecté. *Coût : agent 1-2 h ; calcul 0.*
Dépend de : rien. Trouvé en écrivant `docs/superpowers/specs/2026-09-22-pilotage-dashboard-design.md` (section 6).
⚠️ Clause corrigée dans la même passe : la première version citait le motif `parse_` — SATISFAITE d'emblée par
`ap.parse_args(argv)` (`:337`), et le cliquet l'a immédiatement dénoncée (« condition DÉCLARÉE satisfaite mais l'entrée
s'annonce ouverte »). La clause vise donc le motif tel qu'il s'écrirait DANS un `re.compile`, absent aujourd'hui.

**AVANCEMENT 2026-09-24 (agagi-b0, sur passation du PM) : la moitie SILENCE est FERMEE ; la moitie MOTIFS reste,
et elle est desormais chiffree motif par motif.** Le defaut dominant n'etait pas l'absence de deux motifs mais
l'IGNORANCE MUETTE : `scan_calibrated` sautait toute declaration non detectee sous le commentaire « declaration
perimee », donc l'auteur croyait avoir declare et rien ne le contredisait. Mesure faite AVANT de decider (recomptee
sur cet arbre, pas reprise) : **9 declarations y tombaient et AUCUNE n'etait perimee** — 6 fonctions bien PRESENTES
qu'aucun des 14 motifs ne voit (`_cause_de_mort` — nommage FRANCAIS —, `plain_readout_ceiling`,
`additive_argmax_exact_ceiling`, `verify_plain_ceiling_witness`, `_td_update`, `logit_median_at_outputs`) et
3 CLASSES (`GrabOffMamba`, `NullGrabOffMamba`, `GrabForcedMamba`) : **le cliquet ne scanne que `def`, jamais
`class`** — neuvieme angle mort, de la meme famille que les huit precedents. Livre : le cliquet CRIE desormais,
et il TRANCHE LA CAUSE (`_cause_ignoree` : `MOTIF_AVEUGLE` si un `def` du meme nom existe dans le perimetre,
`CLASSE` si c'est une classe, `PERIMEE` si le symbole n'existe nulle part) parce que les remedes sont OPPOSES —
elargir un motif, etendre aux classes, ou supprimer une declaration morte ; un cri unique enverrait au mauvais
correctif. Cliquet : les 9 sont GELEES dans la baseline (`declarations_ignorees`), toute NOUVELLE bloque. Deux
mutations de plus a la porte 2 (le cri redevient silencieux ; la cause n'est plus tranchee) : **5/5 tuees**.
Cout de chaque elargissement, MESURE sur l'arbre courant (instruments NEUFS que le motif ferait entrer, donc a
calibrer) : `compute_*` **+5** (dont `tools/pm/roles_counts.py::compute_counts`), `parse_*` **+3**, `*ceiling*`
**+5**, `verify_*` **+1**, `_td_update*` **+2**, `*median*` **+9 mais rejete** (ce sont des formateurs :
`_fmt_mediane`, `_median`, `_median_norm`… — un motif qui ratisse des helpers rend le cliquet inutilisable).
⚠️ Fait qui change l'arbitrage : `*ceiling*` + `verify_*` + `_td_update*` **RESORBENT 4 des 9 ignorees** (elles
sont deja declarees : elles passeraient d'« ignoree » a « calibree » le jour ou le motif les voit) pour 3 dettes
neuves, tandis que `compute_*`/`parse_*` en revelent 8 sans en resorber aucune — deux passes distinctes, la
premiere presque gratuite. Reste a faire : (i) elargir aux trois motifs resorbants, (ii) elargir a
`compute_*`/`parse_*` en calibrant ou gelant les 8, (iii) decider pour les 3 CLASSES (les declarer
`NOT_AN_INSTRUMENT` qualifiees, ou etendre le scan aux `class`). *Cout : agent 1-2 h par passe ; calcul 0.*
**FUSION 2026-09-25 (PM, `chantier/pm-portes` → `feat/d1-prod-pairing`) : +3 déclarations FRANÇAISES gelées, 9 → 12.**
`tools/refutateur_temoins.py::recevabilite`, `::plancher`, `::juge_est_calibre` — cause `MOTIF_AVEUGLE` (noms français,
motifs anglais), la même que `_cause_de_mort`. Le bloc REFUTATEUR de `CALIBRATED` les annonçait déjà comme « NON
DÉTECTÉ par le cliquet » ; la branche entrante ne pouvait pas entendre le cri, son cliquet étant encore muet. Gelées EN
CONNAISSANCE dans `declarations_ignorees` (mesuré à la fusion : `check_instrument_calibration.py` refusait 3 NOUVELLES,
0 après gel). ⚠️ Aucun des motifs des passes (i)/(ii) ci-dessus ne les verrait (`*ceiling*`, `verify_*`, `_td_update*`,
`compute_*`, `parse_*` — tous anglais) : les résorber demande un motif NOMMÉ pour ces trois fonctions, ou un motif
français, ou leur renommage — mesuré en revue de fusion, pas déduit.
<!-- closes_when:grep_present=tools/check_instrument_calibration.py::parse_\w+\) -->

**P2.84 — ⚠️ OUVERTE (2026-09-24, demande de robla le 2026-09-23) — lot 2 « Science » du dashboard : arbres en temps
réel, taxonomies, pipeline des runs, « à quoi ça sert / ce qu'on en tire », visuel des avancées — À BRAINSTORMER avant
toute implémentation, sources déjà MESURÉES.**
Quoi : le lot 1 (`docs/superpowers/specs/2026-09-22-pilotage-dashboard-design.md`) livre Flotte / Roadmap / Portes et
s'arrête là ; robla a demandé en plus « la visu de nos arbres en temps réel, les taxonomies, nos runs, la
compréhension, à quoi ils servent, ce qu'on en tire, visuelle de nos avancées », et a tranché le 2026-09-23 : **lot 2
séparé, à brainstormer**. Ce que le lot 1 couvre déjà : worktrees (liste, branche, fusionné, session attachée), runs
EN VOL (bails, processus), portes G0-G4 avec `tested_by`, comptes datés. Ce qu'il ne couvre pas, avec la source
mesurée le 2026-09-22/24 : (a) **taxonomie** — `data/agi_taxonomy/{capabilities,demands,refuted}.json`
(`tools/check_agi_taxonomy.py:40-43`), aucune vue, et le frontend a déjà un rendu d3-force réutilisable
(`ProvenanceGraph`, `TopologyViewer`) ; (b) **pipeline scellée → run → record → arête** — 66
`docs/preregistrations/*.json` (`{name, rule, seal}`), `check_preregistration_applied.couverture()` (`:177`) et
`familles_sans_record()` (`:193`) disent déjà quelle règle scellée n'a pas de record ; (c) **ce qu'on en tire** —
`results/records_graph.json` : 321 nœuds (296 EDR, 5 ADR, 15 REF, 5 SDR), **131 verdicts**, 454 arêtes ; (d)
**rythme** — records ajoutés par semaine ISO (`git log --diff-filter=A -- docs/EDR` : 13 / 4 / 6 / 3 sur S36→S39
2026), fermetures par semaine (dates des têtes d'entrée), ratio science/méthodo (`tools/pm/roles_counts.py`, fenêtre
glissante 30 j) ; (e) **arbres** — avance/retard par branche (`git rev-list --left-right --count` : `pm-roles` 22/18,
`harness-r1` 7/23, `reconcile-d1-main` 0/644 le 2026-09-22 avant la fusion). Aucune donnée à produire : tout existe,
le coût est le cadrage puis le rendu. Note annexe trouvée en passant : `/api/strategy/strategy_tree` **n'a aucun
consommateur frontend** (`grep -rln strategy_tree frontend/src/components` vide le 2026-09-22) — à confirmer par la
porte de parité avant de le brancher ou de le retirer. *Coût : brainstorm 2 h ; implémentation non estimée avant
cadrage.* Dépend de : lot 1 (pas 1-3 de la spec).
<!-- closes_when:path_present=docs/superpowers/specs/2026-09-24-pilotage-science-design.md -->

**P2.85 — ⚠️ OUVERTE (2026-09-24, mesurée en étant bloquée par elle) — la porte 8 juge le DISQUE et non l'INDEX : le
travail NON COMMITTÉ d'une session rend un compteur « périmé » et bloque le commit de TOUTES les autres, sur des
chemins sans rapport. Même défaut que la porte 4 avant `2ffef2ab`, jamais rétro-appliqué (E14).**
**Preuve ANCRÉE, indépendante de tout état transitoire** (c'est elle qui porte l'entrée) :
`tools/check_synthesis_counts.py` ne contient **aucune** référence à l'index — `grep -c` sur
`GIT_INDEX_FILE|ls-files|git show :` rend **0**, contre **7** pour `tools/check_backlog_freshness.py`, la porte 4
CORRIGÉE le 2026-09-22 par `2ffef2ab`. La porte 8 recompute donc ses comptes depuis le disque **par construction**, et
le contraste 0 contre 7 se rejoue à tout moment sur n'importe quel sha.

**Occurrence observée, datée et ANCRÉE comme un instantané** : le 2026-09-24 vers 11 h, sous un `GIT_INDEX_FILE`
construit par `git read-tree HEAD` — donc un index où le registre était EXACTEMENT celui de HEAD — la porte rendait
`[CHIFFRE PÉRIMÉ] docs/REF/REGISTRE_ERREURS.md:72 classes_documentees publié=4 RÉEL=5`, et **elle a refusé mon commit
de l'amendement de P2.83, qui ne touche QUE `docs/roadmap/PRIORITES_ET_DETTES.md`** : un hunk étranger a bloqué un
commit sain. À cet instant, une classe `E30` était sur le disque (`git show HEAD:… | grep -c E30` → 0 ; disque → 1)
**sans sa balise**. La session `agagi-52` a depuis mis la phrase à jour et la porte rend `exit 0` : l'occurrence est
résorbée, le mécanisme demeure.

**DEUXIÈME occurrence, une heure plus tard, et elle est décisive** : le même commit a été refusé une seconde fois, cette
fois sur `docs/roadmap/SCIENCE.md:11 records_total publié=325 RÉEL=326`. Or `SCIENCE.md` est **identique sur le disque
et dans HEAD** (vérifié ligne à ligne) : rien n'a été édité. La cause est la simple **PRÉSENCE d'un fichier non
committé** — `docs/EDR/S2-002-PAIRED-R1_Paired_Band_Exact_NoOp….md`, en `??` dans `git status`, créé par une autre
session — que la porte compte parce qu'elle balaye le **répertoire du disque** (302 fichiers) au lieu de l'index
(301 suivis). Conséquence structurelle, pas anecdotique : sur un dépôt où des records naissent en continu, **tout
record non encore committé bloque le commit de toutes les sessions**, y compris sur des chemins qui n'ont aucun rapport.
Deux occurrences en une heure, sur deux compteurs et deux fichiers différents, suffisent à la promotion (règle du
registre : deux fois documenté → promu).

⚠️ **Leçon de méthode, payée par TROIS sessions le même jour sur le même fichier** : cette session, `agagi-d7` et
`agagi-11` ont mesuré `REGISTRE_ERREURS.md` à trois instants et en ont tiré trois diagnostics différents, **sans
qu'aucune ne se trompe sur sa propre mesure** — le fichier était édité entre-temps. Le dépôt exige de DATER un chiffre
publié ; il n'exige pas encore d'**ancrer une mesure de diagnostic**. Règle à retenir (candidate au registre) : une
mesure destinée à un diagnostic se rejoue sur `git show <sha>:<chemin>` ou cite le sha de l'instant, **jamais sur le
disque nu d'un arbre partagé**. C'est la racine commune de deux inférences trop rapides du même jour, dont
« l'auteur `Test <test@example.com>` est un processus de test » — alors que c'est l'identité git du dépôt
(`git config user.email` = `test@example.com`), portée par 6 des 30 derniers commits **et par mes deux propres commits
par index temporaire**, qui ne passent pas l'identité explicite à `commit-tree`.

**Élargissement du balayage, mesuré par `agagi-11` (non revérifié ici)** : le hook `pre-commit` **ne s'exécute pas du
tout sur un merge propre** (0 appel contre 1 pour un commit ordinaire, contrôle positif fait) ; seuls
`prepare-commit-msg` et `commit-msg` s'arment, et tous deux peuvent annuler le merge par un code 1. Tout invariant qui
tient sur chaque branche séparément et casse à l'UNION traverse donc sans qu'aucune porte ne parle — et la porte 8 en
est le cas d'école : deux branches peuvent corriger le même compte en comptant des objets différents, et la fusion
publie un chiffre faux sans conflit. **Le crochet de merge et la garde de copie `tools/hooks` → `.git/hooks` sont pris
par la session `agagi-d7` en P2.102** : les deux entrées se répondent — celle-ci fait juger l'INDEX au lieu du disque
pendant un commit, celle-là fait tourner les portes à la FUSION. Les deux trous se ferment ensemble et il faut les
livrer dans cet ordre (juger le bon état d'abord, l'étendre au merge ensuite).
Pourquoi c'est la même erreur qu'une déjà corrigée : le 2026-09-22, la porte 4 lisait elle aussi le disque tout en
étant jugée contre l'index temporaire du commit, et `2ffef2ab` l'a fait lire l'index sous `GIT_INDEX_FILE` (CLAUDE.md,
section Environnement : « elle juge exactement ce qui sera committé »). Le correctif n'a jamais été **rétro-appliqué**
aux autres portes — classe **E14**. À faire : sous `GIT_INDEX_FILE`, faire lire l'index à `check_synthesis_counts`
(mêmes deux modes que la porte 4 : index en commit, disque hors commit), avec un contre-exemple gelé — un compteur
périmé UNIQUEMENT sur le disque doit passer en commit et être signalé hors commit — et une ligne dans
`check_gate_mutation.PORTES`. ⚠️ **Balayer les 19 portes du hook pour le même défaut** : toute porte qui recompute
depuis un fichier est concernée. *Coût : agent 1-2 h ; calcul 0.* Dépend de : rien.
<!-- closes_when:grep_present=tools/check_synthesis_counts.py::GIT_INDEX_FILE -->

**P2.86 — ⚠️ OUVERTE (2026-09-24) — dans un test, l'identité git se passe PAR `-c`, jamais par `git config` : trois
tests l'ÉCRIVENT dans un dépôt jetable, et une seule régression d'isolation suffit à polluer le dépôt réel.**
Quoi : mesuré le 2026-09-24 — **trois** tests posent l'identité par une écriture (`tests/sandbox/test_pm_roles_counts.py:96-97`,
`test_pm_snapshot.py:23-24`, `test_staged_authorship.py:54-55` : `git config user.name/user.email`) et **trois** la
passent en ligne (`test_backlog_freshness.py`, `test_harness_provenance.py`, `test_hook_on_merge.py` :
`git -C <repo> -c user.name=t -c user.email=t@t <commande>`). La forme `-c` **n'écrit rien** : il n'y a donc aucune
fenêtre d'isolation à protéger. La forme `git config` est correcte tant que le `cwd` et l'`env` du sous-processus sont
justes — et la nuit du 2026-09-23 a montré ce qu'il arrive sinon : la config LOCALE du dépôt AGAGI est passée à
`user.name = Test` / `user.email = test@example.com` (mtime de `.git/config` : 2026-09-23 22:51), et **33 commits sur
1725, toutes branches — 11 le 23, 22 le 24 —** ont porté cette identité au lieu de celle du propriétaire, dont deux des
miens (par `commit-tree`, qui ne reçoit pas l'identité de l'appelant). Corrigé à la racine par robla le 2026-09-24
(config locale remise à `Robin Denis`), donc l'occurrence est close — mais le MÉCANISME reste : trois tests peuvent la
reposer. La session `agagi-11` fait passer le sien à la forme `-c` dans sa passe et attribue la fenêtre d'isolation à
une ronde intermédiaire de son propre chantier de porte, sans pouvoir la rejouer (état non reproductible). À faire :
les trois écritures passent à `-c`, et la règle entre dans `CLAUDE.md` en une ligne — c'est une famille entière fermée
par une forme, pas par une garde. *Coût : agent 30 min ; calcul 0.* Dépend de : rien.
<!-- closes_when:grep_absent=tests/sandbox/test_pm_snapshot.py::config", "user\. -->

**P2.87 — ⚠️ OUVERTE (2026-09-24, demande de robla) — le dashboard doit s'INDEXER TOUT SEUL à mesure que le projet
produit : donner un FORMAT déclaré aux résultats et aux artefacts pour qu'un type neuf soit ingéré sans écrire un
parseur. À BRAINSTORMER (robla demande une session dédiée après redémarrage).**
Quoi : le lot 1 du dashboard (`docs/superpowers/specs/2026-09-22-pilotage-dashboard-design.md`) lit des sources
EXISTANTES une par une, chacune avec son lecteur écrit à la main. La demande est l'inverse : que produire un artefact
suffise à l'indexer. État mesuré le 2026-09-24, qui dit à la fois ce qui existe et ce qui manque.

**Trois ingesteurs existent déjà**, et ils prouvent que le dépôt sait faire : `tools/consolidate_records.py` (les
frontmatter des EDR → `results/records_graph.json`, 321 nœuds et 454 arêtes), `tools/pm/board.py` (registre de
sessions + bulletins + git → le tableau data/pm/BOARD.json, artefact runtime non suivi), `tools/check_synthesis_counts.py` (les balises `count:` de
9 documents → recompute). Chacun connaît SA source : rien ne se branche par convention.

**Quatre familles de format, inégalement tenues** : `results/*.json` — **95 fichiers dont 21 seulement portent un bloc
`regime`** (c'est le format que les records doivent citer, cf. E8 occ. 4) ; `docs/EDR/*.md` — 303, frontmatter
`gate:`/`tests:`/`adopts:` imposé par la porte 1 ; `docs/preregistrations/*.json` — 68, forme `{name, rule, seal}` ;
data/pm/*.json — 2, écrits par le tick PM (runtime, non suivis). La leçon utile : **le seul format réellement tenu est celui qu'une PORTE
exige** (le frontmatter des EDR, 303/303) ; celui que personne ne vérifie est tenu à 22 % (le bloc `regime`, 21/95).

**Et les artefacts de travail de Claude ne sont ingérés par RIEN** : 130 specs, 124 plans, 7 ledgers d'exécution SDD et
53 rapports de tâche — **314 fichiers**, zéro lecteur. Vérifié plutôt que supposé : `grep -l docs/superpowers tools/*.py`
rend trois fichiers, mais les trois occurrences sont des CITATIONS en docstring (« Design : … », `tools/cartography.py`:7,
`tools/altar_tool_funnel_probe.py`:4, `tools/coevolve_use_long.py`:5), aucune lecture. Or ces artefacts portent précisément ce
qu'aucune autre source ne dit : ce qui a été DÉCIDÉ (specs), ce qui est PRÉVU (plans), ce qui a été TRANCHÉ en cours
d'exécution (les `Ruling:` des ledgers) et ce qui a été RÉFUTÉ (les rapports de revue).

**À brainstormer, dans cet ordre de questions** : (a) quel jeu minimal de champs rend un artefact auto-descriptible
(type, date, sujet, verdict ou état, liens sortants) sans alourdir son écriture ? (b) la convention s'impose-t-elle par
une PORTE (le seul mécanisme qui tienne, mesuré ci-dessus) ou par un lecteur tolérant qui signale ce qu'il n'a pas su
lire — la seconde voie étant la seule compatible avec 314 artefacts déjà écrits ? (c) l'indexation se fait-elle au
MOMENT de l'écriture (un hook, donc un writer de plus) ou à la LECTURE (un balayage par le tick PM, donc rien à
changer aux auteurs) ? (d) que devient l'index : un fichier, une collection de l'artefact Claude, ou le graphe de
records élargi ? (e) ⚠️ un piège nommé d'avance : un index qui rend une liste VIDE quand il n'a rien su lire serait la
forme (c) du registre — un motif qui tronque en silence. Il doit publier ce qu'il n'a pas indexé, comme
`chemins_non_captes` du lot 1. *Coût : brainstorm 2 h ; implémentation non estimée avant cadrage.*
Dépend de : rien (mais recoupe P2.84, le lot 2 « Science » du dashboard — à décider s'ils fusionnent).
<!-- closes_when:path_present=docs/superpowers/specs/2026-09-25-auto-indexation-artefacts-design.md -->


**P2.88 — ✅ CLOSE le 2026-09-24 (ouverte le même jour, mesurée en revue adversariale de la porte 19, HEAD `636c65b1`) — la porte 19
rend `DISCORDE` sur TROIS situations qu'elle ne distingue pas — prémisse FAUSSE, clé qu'elle n'a pas su LIRE, clé
ABSENTE — avec la même chaîne de détail au caractère près, et c'est le libellé du pire cas qui s'affiche.**
Fait : livrée par `107229a0` (fix porte 19, 2026-09-24), dont le commit n'a pas enregistré la fermeture — c'est la porte 4 qui l'a détectée seule (clause satisfaite, entrée encore ouverte), et elle est enregistrée avec le renumérotage 22 → 23 de la porte E19. `DISCORDE` (rang 3) nomme désormais LES DEUX valeurs lues et le fichier ; `SANS_VALEUR_LUE` (rang 2, hors `OK`) publie le nombre de results lus et les clés VOISINES. Mesuré le 2026-09-24 : `python tools/check_regime_claims.py` rend `records : 300 | {'SANS_PARAMETRE': 226, 'CONCORDE': 5, 'CONCORDE_HORS_REGIME': 5, 'SANS_RESULTS': 53, 'SANS_REGIME': 3, 'SANS_VALEUR_LUE': 6, 'DISCORDE': 2}`, exit 0 — exactement la migration prévue ci-dessous (8 DISCORDE → 2 + 6). Les trois témoins demandés sont présents et verts dans `tests/sandbox/test_regime_claims_gate.py` : (a) `test_aucune_valeur_lue_rend_SANS_VALEUR_LUE_et_PUBLIE_ou_il_a_regarde` (statut ET clé voisine dans le détail) ; (b) `test_CONTRE_EXEMPLE_GELE_EDR_GRAB_COST_au_2026_09_09_est_DISCORDE` durci (`3.0` ET `1.0` dans le détail) ; (c) l'ancien `test_1_valeur_introuvable_nulle_part_reste_DISCORDE` renommé `test_1_valeur_CONTREDITE_par_le_regime_ET_par_le_hors_regime_est_DISCORDE`. Porte 15 : les 2 mutations de la porte 19, qui visent la distinction neuve, sont TUÉES.
Quoi : `tools/check_regime_claims.py::evaluer` apparie par INTERSECTION D'ENSEMBLES (l.179 sur `regime_par_fichier`,
l.187 sur `hors_par_fichier`) ; quand l'intersection est vide il écrit `<p> cite [...] : introuvable dans les results
cites` et pose `pire = max(pire, 3)` (l.194-196), donc `DISCORDE` (l.197, rang 3 = le pire de `_RANG` l.46) — sans
jamais nommer la valeur qu'il a pourtant LUE et qu'il tient dans ces deux dictionnaires. Témoin à réponse connue
(lecteur FACTICE, aucun disque, aucun git, 5 cas) : les deux contrôles positifs passent — (A) cité 3.0 / publié 3.0 →
`CONCORDE`, (D) publié hors du bloc `regime` → `CONCORDE_HORS_REGIME`, l'instrument n'est pas dégénéré. Mais (B) cité
3.0 / publié 1.0 — le cas fondateur EDR-GRAB-COST, E8 occ. 4 —, (C) clé jamais lue et (E) contradiction hors-régime
rendent le MÊME statut ET la MÊME chaîne : `statut B == statut C ? True`, `detail B == detail C ? True`, et « la
valeur publiée (1.0) est-elle nommée dans le détail de B ? False ». Trois situations épistémiques sous un seul mot,
et ce mot affirme la première. Absence de LECTURE → affirmation négative de fond, commise par l'instrument même qui
traque E8.
État relancé le 2026-09-24 : `records : 300 | {'SANS_PARAMETRE': 226, 'CONCORDE': 5, 'CONCORDE_HORS_REGIME': 5,
'SANS_RESULTS': 53, 'SANS_REGIME': 3, 'DISCORDE': 8}`, exit 0 ; `tools/regime_claims_baseline.json` = 64 légataires
(53 + 8 + 3). ⚠️ Reclassées contre les JSON réels avec TROIS catégories (la 3ᵉ étant « le nom du paramètre est dans le
fichier mais le lecteur à clés ne le voit pas »), les 10 lignes fautives des 8 DISCORDE donnent `{'ABSENCE_CLE': 4,
'CONTRADICTION': 2, 'ILLISIBLE_PAR_L_INSTRUMENT': 4}` — **la moitié des « absences » sont des valeurs BIEN PRÉSENTES** :
`results/retain_compose_lr_replication.json` porte `/lr_0.02`, `/lr_0.002`, `/_params/lrs` (`_CELL_LR` l.40 n'accepte
que `lr=0.02|`) ; `results/lang_memory_diagnostic.json` porte `D1_lr0.02_ep1200` ; `results/s2_credit_retention.json`
porte `/regime/frozen_phase2_lr = 0.0` ; `results/td_step_pilot_r0.json` porte `/_regime/lr_td` (une LISTE). Un statut
nommé `NON_PUBLIE` (« jamais publié ») serait donc un SECOND négatif fabriqué par-dessus le premier : l'instrument ne
peut pas établir ce que le runner a publié, seulement ce que LUI a lu.
Un E8 RÉEL, vivant dans HEAD, sort sous le même mot. `docs/EDR/107_..._Substrate_Blocked.md:21` annonce « Trajectoire
`p_reach` sur 20 générations (run réduit `R=1`, `pop=24`, `max_ticks=80`, `seed=107`) » ; le SEUL results cité publie
`generations: 2, num_agents: 6, max_ticks: 12` et une `traj` de DEUX valeurs. Ce n'est pas un paramètre qui diverge,
c'est un smoke de 2 générations cité comme preuve d'une trajectoire de 20 — et les deux fichiers sont propres
vis-à-vis de HEAD (`git status --porcelain` vide). La 2ᵉ « contradiction » est un faux positif de l'extracteur :
`docs/EDR/S2-REWARD-ABLATION_…md:106` cite `reward_scale = 0` à l'INTÉRIEUR d'une prédiction.
Coût s'il reste : la porte est branchée au hook (`tools/hooks/pre-commit:370`, déclenchée par tout `docs/EDR/*.md`,
`results/*.json`, la baseline ou son module). ⚠️ Une dette GELÉE n'imprime AUCUN détail (`OK`, exit 0) — le détail ne
sort que pour un record NOUVEAU ou RÉGRESSÉ, c'est-à-dire exactement quand la porte BLOQUE et que l'auteur doit agir :
là, deux réparations opposées reçoivent la même phrase, et le pied de page (l.309) propose les deux remèdes sans dire
lequel s'applique.
À ÉCRIRE, en nommant ce qui a été LU et jamais ce que le runner aurait fait : (1) une valeur lue, différente de la
citée → garder `DISCORDE` rang 3 (le mot devient exact), détail nommant LES DEUX valeurs et le fichier ; (2) aucune
valeur lue → nouveau statut **`SANS_VALEUR_LUE`**, **rang 2** (avec `SANS_RESULTS` / `SANS_REGIME`), hors de `OK`
(l.41) — un inconnu ne devient pas un vert, mais il cesse d'affirmer —, détail publiant le nombre de results lus et,
à coût nul (`_sous_noeuds` les parcourt déjà), les clés VOISINES portant le nom du paramètre. Témoins à ajouter dans
`tests/sandbox/test_regime_claims_gate.py` : (a) un témoin d'absence exigeant `SANS_VALEUR_LUE` ET la présence des
clés voisines dans le détail ; (b) le témoin GRAB-COST (l.40) durci — exiger `DISCORDE` ET la présence de `1.0` dans
le détail, sans quoi rien ne teste que la valeur publiée est nommée (l.42 n'assert aujourd'hui que le NOM du
paramètre) ; (c) l.122 renommé — il s'appelle `test_1_valeur_introuvable_nulle_part_reste_DISCORDE` alors que ses
données publient `forage_payoff: 1.0`. Les trois témoins DISCORDE gelés (l.40, l.122, l.128 phase 2) sont TOUS des
contradictions : **zéro témoin** pour la branche majoritaire. Puis `--update-baseline` : 2 restent DISCORDE, 6 passent
`SANS_VALEUR_LUE` (rang 2 = une AMÉLIORATION, donc aucun faux rouge). Libellés libres, mesuré avec contrôle positif
(`grep -rn --include=*.py` sur `tools/` + `tests/`) : `SANS_VALEUR_LUE` → 0, `DISCORDE` → 18. *Coût : agent 1-2 h ;
calcul 0.* Dépend de : rien. À faire AVANT tout resserrement de la baseline de la porte 19, sinon les 8 DISCORDE se
regèlent sous le mauvais nom. Même famille que P2.83 et P2.92 (une branche de rejet qui confond des causes opposées).
Occurrence au registre : E8.
**FUSION 2026-09-25 (PM) : un DISCORDE gelé EN CONNAISSANCE, lu comme « citation ≠ prémisse ».** À l'union avec la cible,
la porte 19 a rencontré `S2-CREDIT-ABLATION-2` (né sur la cible, où la porte n'existait pas) et l'a classé `DISCORDE`
(`reward_scale` cité `0` l. 146, publié `1.0` sur les 4 bras et dans `regime/arms_credit`). Gelé dans
`tools/regime_claims_baseline.json`. Lecture tranchée en revue de fusion (lentille baselines, re-mesurée) : la citation
renvoie au bras `b_zero` du record PARENT `S2-CREDIT-ABLATION`, pas à une prémisse de CE run — la forme que la porte
déclare ne pas savoir distinguer ; pas d'E8. À l'auteur (P4.16) de citer le results parent ou de reformuler, jamais à
une fusion de toucher un record.
<!-- closes_when:grep_present=tests/sandbox/test_regime_claims_gate.py::SANS_VALEUR_LUE -->

**P2.89 — ⚠️ OUVERTE (2026-09-24, vue en passant pendant l'audit des portes) — la porte 8 n'est armée que par les NEUF
documents qui PUBLIENT les comptes : 13 des 18 balises n'ont aucun de leurs intrants dans sa ligne de déclenchement,
318 des 325 records entrent ou sortent sans la réveiller — le compte d'instruments est FAUX dans HEAD aujourd'hui
(240 publié, 242 réel), et la porte juge le DISQUE, pas l'index (faux VERT mesuré dans l'arbre principal).**
Quoi : `tools/hooks/pre-commit:149` n'appelle `tools/check_synthesis_counts.py` que si le commit stage l'un des NEUF
documents où vivent les balises (`CLAUDE.md`, `docs/REF/REGISTRE_ERREURS.md`, `docs/roadmap/PRIORITES_ET_DETTES.md`,
`docs/EDR/README.md`, `docs/SDR/*.md`, `docs/REF/REF-DEMAND-MARKER.md`, `docs/roadmap/FIL_DIRECTEUR_AGI.md`,
`docs/roadmap/SCIENCE.md`, `docs/roadmap/ROLES.md`) ou la porte elle-même. Ces neuf documents sont les SORTIES des
comptes, pas leurs INTRANTS. Les portes voisines font l'inverse et s'arment sur LEURS intrants : porte 1 sur
`docs/(EDR|ADR|SDR|REF)/.*\.md` (hook:15), porte 3 sur `(tools|src)/.*\.py` (hook:46), porte taxonomy sur
`data/agi_taxonomy/.*\.json` (hook:262).
Sur les **18 balises** publiées (recomptées le 2026-09-24 : 18), **5 seulement sont correctement armées — et
uniquement parce que leur intrant EST le document qui les publie** (`classes_executables` / `classes_documentees` dans
`REGISTRE_ERREURS.md`, `roles_instancies` / `roles_candidats` dans `ROLES.md`, `syntheses_balisees` auto-référentiel).
L'écrivain arme donc la porte exactement dans les cas où il est aussi le lecteur, jamais ailleurs. Les **13 autres
sont MUETTES** : les 4 `records_*` (intrant = tout `.md` de `docs/{EDR,ADR,SDR,REF}`), les 6 `instruments_*` (intrant =
tout `.py` de `tools/` et `src/` hors `check_*`, plus le dict `CALIBRATED` de
`tests/sandbox/test_instrument_calibration.py`), `portes_hook` (intrant = `tools/hooks/pre-commit`) et les 2
`aretes_taxonomy` (intrant = `data/agi_taxonomy/demands.json`). Côté records : **7 sur 325** arment la porte (les 5
SDR, `REGISTRE_ERREURS.md`, `REF-DEMAND-MARKER.md`) — **318 ne l'arment pas, soit 97,8 %**.
Ce n'est pas un risque : **le compte est FAUX dans HEAD au moment où cette entrée est écrite.** `python
tools/check_synthesis_counts.py` rend **exit=1** et quatre `[CHIFFRE PÉRIMÉ]` : `CLAUDE.md:31` `instruments_detectes`
publié=240 RÉEL=**242**, `CLAUDE.md:32` `instruments_calibres` publié=232 RÉEL=**234**, et les deux mêmes à
`docs/SDR/G2_agent_composes.md:59`. Cause tracée : `c4d69b79` ajoute `verdict_temoin` et `verdict_phase_temoins` dans
`tools/refutateur_temoins.py`, tous deux capturés par `^def\s+(\w*verdict\w*)\s*\(` — et ce commit **n'arme pas** la
porte. Deux occurrences antérieures, datées et indépendantes : (a) `62763305` ajoute `docs/REF/REF-REVUE-ADVERSARIALE.md`
sans armer la porte (grep EXIT=1, contrôle positif du même motif sur une liste contenant `SCIENCE.md` : EXIT=0), et
`SCIENCE.md` a publié `records_total=324` pour un réel de 325 à ce commit ET au suivant `72879d76`, corrigé seulement
à `b9aec5cc` ; (b) 5 commits publient un `portes_hook` faux — quatre à `16` quand le hook en câblait `17` (de
`7ed985d6`, qui câble la porte 17, à `48ef27ea`), et `7fb183d4` publie `8` alors que son propre message dit « le hook
passe de 8 a 11 gardes ». Dans les deux cas la correction est tombée sur un commit SANS RAPPORT. Exposition sur les
200 derniers commits : 24 commits ajoutent/suppriment un record → **7 n'arment pas** ; 22 modifient le hook → **5** ;
112 touchent un intrant `instruments_*` → **53**. (`aretes_taxonomy` est armé 4/4 par HASARD, ces commits stageant
aussi une synthèse — rien dans le hook ne le garantit.)
Second défaut, indépendant : **elle lit le DISQUE, jamais l'INDEX.** `grep -c GIT_INDEX_FILE` rend **0** dans
`check_synthesis_counts.py`, `check_record_links.py` et `check_instrument_calibration.py`, contre **3** dans
`check_backlog_freshness.py` et **7** dans `check_evidence_provenance.py`. Faux VERT mesuré aujourd'hui dans l'arbre
principal : `ls docs/{EDR,ADR,SDR,REF}/*.md | wc -l` = 327 contre `git ls-files` = 326, le non-suivi étant
`docs/EDR/S2-CREDIT-ABLATION-2_….md` que `parse_record` accepte ; `SCIENCE.md` sur disque publie 325 et la porte rend
OK, alors que `git show HEAD:docs/roadmap/SCIENCE.md` publie 324 — un vert sur un chiffre qu'aucun clone du commit ne
peut reproduire. C'est la classe corrigée pour la porte 4 le 2026-09-22 et jamais rétro-appliquée (E14).
Rien ne protège la ligne d'armement elle-même : `tests/sandbox/test_synthesis_counts.py` porte 7 tests, dont **0**
mentionne `staged_syn` ou `pre-commit` (contrôle positif : le même grep trouve 7 `def test`) ; et la porte 15 mute 19
MODULES dont `tools.check_synthesis_counts` (`check_gate_mutation.py:186`) mais **jamais le fichier
`tools/hooks/pre-commit`**. Le harnais mesure si chaque porte SAIT trouver, jamais si elle est APPELÉE — la question
se pose à l'identique pour les 20 autres portes et mérite sa propre entrée. Nuance : le 7ᵉ test
(`test_the_repository_published_counts_are_all_current`) lance `scan()` sur le dépôt réel et attrape donc la
péremption — mais seulement dans la suite complète (~30 min), pas au commit, et la facture tombe sur qui n'a rien fait.
À ÉCRIRE : (1) une seconde liste `staged_syn_intrants` dans le bloc 8 du hook, couvrant
`docs/(EDR|ADR|SDR|REF)/.*\.md`, `(tools|src)/.*\.py`, `tests/sandbox/test_instrument_calibration\.py`,
`tools/hooks/pre-commit`, `data/agi_taxonomy/.*\.json`, la porte tournant si l'une OU l'autre est non vide ; (2) un
contre-exemple gelé confrontant la regex à une liste connue (un record EDR doit armer, un `results/*.json` non), plus
une mutation déclarée à la porte 15 — ce qui suppose d'abord de lui donner prise sur le hook ; (3) un mode `--index`.
⚠️ Ce 3ᵉ point n'est PAS du même coût que pour la porte 4 : celle-ci lit du TEXTE depuis l'index, alors que les
compteurs d'ici délèguent à `check_record_links.py` et `check_instrument_calibration.py`, qui parcourent le SYSTÈME DE
FICHIERS (`os.walk`, `os.listdir`) — les rendre index-aware fait partie du travail. ⚠️ Avant d'élargir, deux
préalables mesurés : la porte coûte **11,3-11,9 s** (3 réplicats, charge relevée : 7 processus python, 22 CPU
logiques — MAJORANT, l'unité machine libre n'est pas mesurée), dont **9,67 s sur 10,93 s** passées dans `_calib()`
(`check_synthesis_counts.py:72`), appelé **5 fois** par passe faute de mémo — trois de ces appels dans la seule lambda
`instruments_non_calibres` (l.130) ; un `functools.lru_cache` divise par ~3,4, et scoper la recompute à la famille de
l'intrant stagé rend un commit de record quasi gratuit (~0,3 s). Sans ces deux-là on ajoute ~11 s à chaque commit de
science, et un cliquet qu'on désactive ne mesure rien. *Coût : agent 1 h 30 ; calcul 0.* Dépend de : rien. Lié à
P2.83 (qui explique pourquoi le compteur d'instruments ne veut pas dire ce qu'il annonce : une
déclaration que le cliquet ne détecte pas est ignorée en silence) et à P2.56.
<!-- closes_when:grep_present=tools/hooks/pre-commit::staged_syn_intrants -->

**P2.91 — ⚠️ OUVERTE (2026-09-24) — la porte 23 compte mal dans LES DEUX SENS (deux de ses « non résolus » sont des
nus qui DÉCLARENT `clause_E19`, quatre des douze chemins signalés ne comparent aucun pas) — et le patron de
remédiation naturel est un appel DÉCORATIF qui rend `True` par court-circuit sans rien mesurer.**
Quoi : la porte 23 (ex-22, `tools/check_e19_optimizer_sweep.py`, branchée au hook `tools/hooks/pre-commit`, bloc `# 23.`) est VERTE
et son résumé se lit « 8 nus pour 1 appelant », ce qui invite à conclure « poser la garde partout ». Mesuré le
2026-09-24 : `runners scellés : 29 | sous gradient (PLANCHER) : 9 | nus (PLANCHER) : 8 | indéterminés : 4 | non
résolus : 4 | règle absente : 0 | illisibles : 0 | appelants de la garde : 1 | gelés : 16`, pour 13 lignes `couvert`
(13 + 8 + 4 + 4 = 29). Le compte est faux dans les DEUX sens, et le patron de remédiation évident est pire que le
défaut.
⚠️ **(0) LE PIÈGE PRINCIPAL — LE PATRON ÉVIDENT EST UN APPEL QUI NE PEUT PAS ÉCHOUER.** La garde attend
`measure(lr) -> (bras_testé, bras_de_référence)` et calcule `gap = référence − testé` ;
`tools/experiment_preflight.py:399-401` rend `True` SANS RIEN CALCULER dès que `g_max <= 0`. Mesuré sur la grille
réelle `results/bilinear_aligned_r1.json` (médianes recomputées : lr=0,02 plain 0,2844 / bilinear 0,9414 ; lr=0,002
plain 0,1852 / bilinear 0,4258, 12 seeds) : écrire l'appel dans le sens naturel — testé = `bilinear`, le bras CAPABLE
— donne des gaps NÉGATIFS aux deux pas et **rend `True` par court-circuit**. Or la porte déclare elle-même compter un
appel **même DÉCORATIF** : le chemin passerait de `nu` à `couvert`, la porte verdirait, et RIEN ne serait mesuré — un
couvert fabriqué par un instrument incapable de produire les deux issues. **Le nul à défendre est « `plain` ne compose
pas » : testé = `plain`, référence = `bilinear`.** Dans ce sens, closure mesurée **63,4 %** contre un seuil de
66,7 % — la garde PASSE, de 3,3 points seulement. Sur `BILINEAR-SHAM-R1` : `plain|bilinear` **65,1 %**,
`sham|bilinear` **63,9 %**. Ces chiffres sont le critère d'acceptation de la passe ; ils se re-dérivent en secondes,
sans aucune simulation.
(a) DEUX des quatre « non résolus » sont des NUS DÉGUISÉS. `_resoudre` (l.126-135) ne lit que les constantes CHAÎNE de
niveau MODULE ; `tools/lock001_pred2_r1.py:34` `NOM_REGLE = "LOCK-001-PRED2-R1"` puis `:138` `nom = argv[...] if
"--regle" in argv else NOM_REGLE` et `:139` `verify(nom)` ; idem `tools/lock001_proxy_r1.py:33`. En résolvant à la
main, les deux rendent `sous_gradient = True (clause_E19 déclarée)` et aucun n'appelle la garde : ils relèvent du rang
`nu` (5, BLOQUANT) et sortent `non_resolu` (rang 2, seulement RAPPORTÉ). **Les nus atteignables statiquement sont donc
10, pas 8** — et ces deux-là servent `docs/EDR/LOCK-002_D2_Retention_Is_Learned_Under_REINFORCE_At_The_Right_Step_The_Fourth_Manifestation_Was_E19.md` et
`docs/EDR/LOCK-003_The_Same_Lever_Pierces_Both_Threads_Low_Step_And_Duration_Prediction_2_Of_LOCK-001_Holds.md` : la porte est aveugle sur le record qui PORTE la 4ᵉ occurrence de la classe qu'elle police.
Correctif : propager les constantes CHAÎNE LOCALES de la fonction englobante. ⚠️ La branche `ast.IfExp` de `_resoudre`
est du CODE MORT sur le corpus réel (son unique témoin, `tests/sandbox/test_e19_sweep_gate.py:43-47`, emploie la forme
INLINE `verify("EVO-028-SMOKE" if SMOKE else "EVO-028")`, qu'aucun runner n'utilise).
⚠️ (a-bis) `tools/lang_memory_edge_run.py` N'EST PAS un nu caché, et le correctif « lire le défaut de
`os.environ.get` » y FABRIQUERAIT un négatif : sa ligne 31 est à la COLONNE 0 (module), son défaut littéral est
`LANG-MEMORY-EDGE` (mesuré `sous_gradient=False`), et la règle qui déclare `clause_E19` est `LANG-MEMORY-EDGE-D2`,
atteinte uniquement par la variable d'environnement (`docs/EDR/LOCK-002_...md:34`). Le résoudre statiquement ferait
passer le chemin `non_resolu` → `indetermine` (régression bloquante) tout en affirmant « pas sous gradient » d'un
runner que le record dit avoir tourné sous gradient. Le nom n'est pas décidable : le faire DÉCLARER est la seule voie.
(b) QUATRE des douze chemins signalés ne comparent aucun pas. `tools/legacy_nan_guard_run.py` et
`tools/legacy_wm_guard_run.py` sortent `nu` parce que `cellule.lr = null` est lu « comparaison de pas hors grille
littérale, DÉCLARÉE » ; or ici `null` porte l'AUTRE sens, celui de `LEGACY-CAUSE-DE-MORT-R1` (`bras: {"lr0_reference":
0.0, "lr_low": 0.004, "natural": null}`) : le pas NON SURCHARGÉ. `legacy_nan_guard_run.py:8` dit « re-mesure le bras
`natural` (lr 0,04) sur les 12 seeds de P3.4 » — UN bras, UN pas — et sa référence lr0 est IMPORTÉE, déclarée
`allow_inferred_reason` (`:78-81`). Le docstring de la garde les exclut (`experiment_preflight.py:301-302` : « un
verdict à UN SEUL bras et seuil absolu n'est pas protégeable par ce mécanisme »). De même, `S2-REWARD-ABLATION` et
`S2-CREDIT-RETENTION` ne balaient rien : leurs seules occurrences de `lr` sont « poids GELÉS lr=0 » (phase 2 à poids
figés, l'inverse d'un balayage) et « lr 0,04 » nommant le régime PUBLIÉ. ⚠️ Le docstring de la porte
(`check_e19_optimizer_sweep.py:51-53`) affirme « AU MOINS TROIS runners VIVANTS comparant réellement sous gradient
[…] `s2_reward_ablation.py` » : mesuré, c'est FAUX — seuls `s2_credit_ablation.py` et `s2_credit_ablation_2.py` en
portent un. C'est DEUX, pas trois. Le témoin qui gèle ce trio (`test_e19_sweep_gate.py:266`) n'exige, lui, que
`indetermine` : il est juste, c'est la PROSE qui surclame.
À ÉCRIRE, dans l'ordre : (1) `tools/bilinear_aligned_run.py` —
`assert_verdict_invariant_to_optimizer(lambda lr: (med("plain", lr), med("bilinear", lr)), lrs=tuple(c["lr"]))`,
**dans CET ordre**, et PUBLIER la closure dans la lecture sur le modèle de `tools/learner_calibration.py:116-125`
(dont le `measure(lr)` ne relance RIEN : il projette une grille déjà calculée) ; le helper `med(sub, lr)` existe déjà
aux lignes 39-40. Attendu : closure 63,4 %, statut `INVARIANT_AU_PAS` — un autre chiffre signale un appel mal orienté.
(2) `tools/bilinear_sham_run.py`, même orientation (65,1 %). (3) et (4) `lock001_proxy_r1.py` et `lock001_pred2_r1.py`
— rendre le nom RÉSOLVABLE d'abord, puis munir de la garde. (5) `legacy_lr_curve_r2.py` (5 pas, référence lr 0,0
RE-MESURÉE dans la grille, le cas le plus propre). (6) `legacy_lr_curve.py`. (7) `td_step_pilot.py`. (8)
`legacy_cause_de_mort.py` — applicable, mais sa DV est une PART de canal de mort : écrire la lecture AVANT d'appeler.
(9) rectifier « AU MOINS TROIS » en DEUX dans le docstring et en retirer `s2_reward_ablation.py`. (10) l'avis imprimé
PAR LIGNE (`:302-304`) doit dire « déclarer ET appeler » : suivi seul, il fait passer un chemin de `indetermine`
(rang 4) à `nu` (rang 5) — vérifié en mémoire, `REGRESSION (donc COMMIT BLOQUE) : True`. ⚠️ À NE PAS traiter mais à
trancher : les deux gardes legacy et les deux `s2_*` sont hors périmètre de la garde, et les « reclasser dans
`tools/e19_sweep_baseline.json` » n'est PAS faisable en l'état — le vocabulaire des raisons est FERMÉ à cinq valeurs
(mesuré : `Counter({'nu': 8, 'non_resolu': 4, 'indetermine': 4})`) ; les sortir demande d'ÉCRIRE une sixième raison
(`hors_perimetre`, rang 0, exigeant une justification) avec son contre-exemple gelé. Les 11 grilles concernées sont
présentes et SUIVIES par git : *coût agent 2-3 h ; calcul 0*, aucune simulation. Ajouter un appelant ne bloque jamais
(seule la PERTE d'un appelant gelé bloque, `main()` l.445-448). Dépend de : rien.
⚠️ FAIT MESURÉ EN PASSANT, à consigner dans `docs/EDR/EDR-BILINEAR_Bilinear_Substrate_Unlocks_Composition.md` et non ici : sur
`results/bilinear_sham_r1.json`, le couple testé=`plain` / référence=`sham` rend une closure de **80,7 %**, au-dessus
du seuil — la garde LÈVE. L'avantage post-hoc publié « sham > plain à 0,02 (+0,045 : capacité LINÉAIRE) » tombe à
+0,0086 à lr 0,002. Ce fait est POST-HOC et hors verdict scellé ; il ne rétracte rien, mais il appartient au record.
**FUSION 2026-09-25 (PM, `feat/harness-r1`) : un « nu » gelé qui est un défaut d'ATTRIBUTION, pas de garde.** La porte 23
attribue la règle `HARNESS-R1-bis` (`clause_E19` déclarée) à `tools/harness/seal_r1.py` — le SCELLEUR, qui n'exécute
aucune cellule — et le classe `nu` ; or `src/seed_ai/harness_verdict.py` appelle `assert_verdict_invariant_to_optimizer`
et entre au même gel comme APPELANT réel (2 désormais). Même famille que les deux sens ci-dessus : le runner d'une
règle n'est pas forcément le fichier qui la nomme. Gelé `nu` EN CONNAISSANCE dans `tools/e19_sweep_baseline.json`
(+ `cell.py`, `run_r1.py` en `non_resolu`, argv) ; à résorber quand l'attribution lira l'appelant.
<!-- closes_when:grep_present=tools/bilinear_aligned_run.py::assert_verdict_invariant_to_optimizer -->

**P2.92 — ⚠️ OUVERTE (2026-09-24) — les 18 chemins d'évidence gelés par la porte 20 n'ont JAMAIS été committés
(`results/` ignoré jusqu'au 2026-09-08, records de juin 2026), et 11 des 17 records ne disent nulle part que leur
évidence est introuvable.**
Quoi : `python tools/check_evidence_provenance.py` (porte 20) rend, relancé le 2026-09-24 : « records : 300 | motifs
cites : 76 | chemins distincts : 78 | paires record×chemin : 97 | absents : 18 | non suivis : 0 | glob vides : 0 |
publies par hash : 0 | records fautifs : 17 », puis « OK : 18 chemin(s) legataire(s) gele(s) ».
`tools/evidence_provenance_baseline.json` porte exactement ces 18 paires dans 17 records, toutes de cause `absent`.
CE QUE SONT CES 18. Quatre oracles DISTINCTS par chemin — disque (`os.path.exists`), index (`git ls-files
--error-unmatch`), arbre (`git cat-file -e HEAD:`), historique (`git log --all --`) — rendent 18/18 : absent, absent,
absent, 0 commit. Le quatrième a son témoin positif sur la MÊME commande (`git log --all --oneline --
results/records_graph.json` rend 4 commits), donc le 0 est une absence mesurée. Renommage : 18 renommages dans le
dépôt (tous dans `docs/EDR/`, ex. 135→142), **0** touchant `results/`. Suppression : 15 suppressions (ex.
data/articles.json), **0** sur le pathspec `results/*.json` — pathspec validé sur un cas positif
(`--diff-filter=A -- "results/*.json"` rend 102 ajouts). Aucun `results/` présent-mais-non-suivi : `git ls-files
--others -- results/` rend 0, et l'inventaire RÉCURSIF rend 95 suivis = 95 sur disque (⚠️ un `os.listdir` NON récursif
rend 93 et fabrique un faux écart : `results/s6/` existe).
MÉCANISME, daté. `.gitignore:18-19` porte `results/*` puis `!results/*.json` depuis le commit `7936c2b5` du
2026-09-08 ; juste avant, et au commit du record 088, la ligne est `results/` NU. Ce commit n'a ajouté que **44**
`.json` — ceux encore présents sur le disque ce jour-là. Or les 17 records fautifs sont tous antérieurs de deux à
trois mois (2026-06-15 pour 088 → 2026-07-01 pour 127/150/151). ⚠️ Un `.gitignore` n'a jamais rendu le suivi
IMPOSSIBLE : `git ls-tree -r 7936c2b5 results/` rend **57** `.json`, donc 13 étaient déjà suivis. Mais le premier de
ces 13 date du **2026-07-21**, trois semaines APRÈS le dernier des 17 : pendant toute la fenêtre de rédaction, ZÉRO
`results/*.json` n'était suivi.
CE QUI MANQUE VRAIMENT — et ce n'est pas ce qu'on croit. Les 6 records les plus récents (114b, 123, 125, 127, 150,
151) DISENT déjà que leur évidence n'est pas au dépôt : re-mesuré le 2026-09-24, le mot `gitignore` est présent dans
**6** des 17 et ABSENT des **11** autres (088, 089, 090, 093, 094, 098, 099, 100, 101, 105, 106), 0 illisible. Les six
nomment en plus leur graine de fumée à côté de leur graine de verdict (`docs/EDR/150_*.md:16` « **Seed** : 1280, R=3
… (smoke 99280) », `123:5` « **Seed** : 1167 (smoke 99167) », `127:101` « -> results/qd_tier_rescue_1260.json
(gitignore) ») : la substitution « prendre le 99xxx suivi pour le 1xxx publié » n'est donc PAS indétectable, la ligne
du record la contredit. Ce qui est vrai et mesuré, c'est que **11 des 17 records citent un `results/*.json`
introuvable sans un mot d'avertissement**, et que `docs/EDR/106_*.md` qualifie même son évidence de « régénérable ».
C'est là qu'un lecteur croit pouvoir rouvrir et ne peut pas. (Fait annexe, publié pour qu'on cesse d'y revenir : sur
les 6 qui ont un voisin suivi, 5 étiquettes de verdict sur 6 sont identiques entre le smoke R=1 et le verdict publié ;
114b est la seule qui diffère, CONFOND CONFIRME publié contre CONFOND NEGLIGEABLE au smoke.)
À ÉCRIRE, par valeur mesurée décroissante. (1) **Faire DÉCLARER l'irrécupérable au lieu de le deviner** : ajouter à
`tools/check_evidence_provenance.py` une cause `non_refutable`, rangée dans `_RANG`, posée par un bandeau écrit dans
le record (« évidence perdue : conclusion non réfutable en l'état ») et gelant la paire sous cette cause au lieu
d'`absent` ; écrire le bandeau dans les **11** records muets d'abord, dans les 6 autres ensuite. C'est ce que teste la
clause. (2) **Confronter un sha256 déclaré au fichier quand le fichier existe** : `grep -c hashlib
tools/check_evidence_provenance.py` rend **0** (témoin positif : `hashlib` est dans `tools/preregister.py`), donc la
cause `par_hash` n'est jamais vérifiée, même fichier présent. ⚠️ Ce n'est PAS un trou caché — le docstring l'énonce
(« une DECLARATION, pas une VERIFICATION … ni le fichier (qui peut avoir disparu) »), le message d'échec le PROPOSE
comme remède, et le comportement est GELÉ en test (`tests/sandbox/test_evidence_provenance_gate.py:17-23`, où
`results/perdu.json` est absent, non suivi, porteur d'un sha256, et asserté `par_hash`). Le résidu à écrire est donc
étroit et sans risque (0 paire `par_hash` aujourd'hui) : distinguer `hash + fichier présent` (vérifiable, donc à
vérifier) de `hash + fichier nulle part` (invérifiable, donc à refuser ou classer `non_refutable`). (3) **Ne PAS
re-runner pour « restituer »** : les runners cités par les 17 records sont **11** (et non 9), tous présents ET suivis,
mais les records épinglent des commits de juin (dda4080, eb81cff, bdb7cb9) sur du code qui a dérivé depuis (E28) —
un re-run serait une mesure NOUVELLE, pas la restitution de celle qui est publiée. *Coût : agent 2-3 h ; calcul 0.*
Dépend de : rien. C'est E27 exactement, sur des paires que la porte laisse passer par construction (un légataire gelé
ne bloque qu'en RÉGRESSANT). Même famille que P2.88 et P2.83.
⚠️ VU EN PASSANT, À NE PAS FONDRE ICI (entrée séparée, calibration d'instrument) : `tools/tom_probe.py:97-102` —
`_verdict_tom_emergence(0.0, 0.0, 0.0)` rend `TOM_INERT` (témoin positif : `(0.5, 0.1, 0.1)` rend `TOM_EMERGES`), sans
aucun plancher de n ; et `results/tom_probe_99280.json`, le seul fichier `tom_probe` suivi par le dépôt, porte
`n_ctrl=0.0`, `n_tom=0.0` et ce même verdict de fond, qui est l'étiquette publiée par EDR-150. Même forme sur
`results/qd_tier_rescue_99260.json` (`d_craft=0.0`, `n_confirme_seeds=0` → `QD_NEUTRE`). C'est la forme (a) de
CLAUDE.md — entrée vide → affirmation négative de fond — et `tom_probe` est absent de
`tools/fabricated_defaults_baseline.json` (témoin positif : `tom_coordination` y apparaît 2 fois), donc la porte 14 ne
l'attrape pas.
<!-- closes_when:grep_present=tools/check_evidence_provenance.py::non_refutable -->

**P2.93 — ⚠️ OUVERTE (2026-09-24, vue en passant en auditant `tools/preregister.py`) — la porte de revue ne reconnaît
un coût que sous CINQ noms de clé au PREMIER niveau : aucune règle n'est aveuglée par la seule profondeur (0/68), mais
4 à 5 déclarent leur échelle sous `design` / `regime_scelle` / `n`, et la prochaine qui fera pareil sera scellée SANS
revue — contournement REPRODUIT.**
Quoi : `tools/preregister.py:57` fige `_CLES_COUT = ("cout", "budget_s", "garde_cout", "plafond", "cout_scelle")` et
`:60-61` teste `any(k in rule for k in _CLES_COUT)` — **premier niveau seulement**. Conséquence REPRODUITE dans un
répertoire temporaire hors dépôt : la MÊME échelle, mot pour mot, fait mordre ou ne fait pas mordre la porte selon le
NOM de la clé qui la porte. Contrôle positif d'abord — la règle d'`EVO-006-REPLICATION` avec son échelle recopiée sous
`cout` lève bien `ReviewRequired` ; puis la même règle, échelle laissée sous `design` (« 2 bras x 12 seeds x 35
eres… »), est **scellée sans revue**, enveloppe `['name','rule','seal']` ; idem pour l'échelle STRUCTURÉE de
`DELAYED-COORD-LR-N12` (`n` = 12 **plus** `regime_scelle` = {episodes: 1600, n_agents: 16, seeds: "0..11",
eval_batches: 40}) ; et une règle qui ne déclare rien du tout passe aussi. La porte échoue donc **OUVERTE**, en
silence.
La cause SUPPOSÉE — « elle ne lit que le premier niveau, donc des clés se cachent plus bas » — est **réfutée**, mais
pas par le chiffre d'abord publié. Descente récursive sur dicts ET listes, mêmes 5 clés, sur les 68 fichiers de
`docs/preregistrations/` (68 fichiers, 68 suivis par git, **0 illisible**) : **61** rendent `declare_un_cout(rule) is
True` au premier niveau ; **1** — `TD-STEP-PILOT-R2.json` — porte en plus `controles.cout` et `seuils.budget_s` à la
profondeur 1, mais elle en porte AUSSI une au premier niveau, donc **0 règle est aveuglée par la seule profondeur**
(et non « 0 clé profonde » : ce chiffre-là vaut 1). Contrôle de portée de la descente : **60/68** règles contiennent
au moins un conteneur imbriqué, profondeur de conteneur max **4** — la descente pouvait voir quelque chose, son zéro
est un vrai zéro et non un instrument muet.
Le vrai défaut est le **VOCABULAIRE FERMÉ** (5 noms) et la FORME. Sur les **7** règles sans aucune clé reconnue :
**4** déclarent une échelle de RUN sous un autre nom — `EVO-006-REPLICATION` et `EVO-007` (`design` = « N bras x 12
seeds x 35 eres »), `DELAYED-COORD-LR-N12` et `-bis` (`n` + `regime_scelle` structuré) ; **`EVO-012`** déclare une
PORTÉE de 4 sujets pour une mesure que sa propre clé `note` dit « purement mecaniste (passages avant + inspection de
W) : n'utilise NI le harnais de survie NI les compteurs du monde » — la ranger dans l'angle mort est un jugement, pas
une mesure ; **`EVO-007-bis`** et **`-bis2`** sont des re-scellements d'une règle de LECTURE (clés `remplace`,
`defaut_de_la_regle_initiale`, `lecon`, `pourquoi_bis2`). L'angle mort vaut donc **4, au plus 5**. ⚠️ Ne pas publier
de total « 66/68 » : 61 est MESURÉ par clé, le reste est LU dans de la prose, et les deux ne s'additionnent pas dans
la même unité. Le chiffre « 61 » n'est d'ailleurs publié dans AUCUN fichier suivi (`git grep "61 declarent|61/68"` →
vide, contrôle positif du même `git grep` : `declare_un_cout` → 2) : il vit dans le message du commit `5c7b0d47`, qui
ne se corrige pas.
Ce qu'il coûte s'il reste : la dette est **entièrement à VENIR**, ce qui est exactement le moment où elle est
gratuite. Les 7 ont été ajoutées du 2026-07-28 au 2026-09-02, la plus récente des 68 date du 2026-09-22, et
`ReviewRequired` (`tools/preregister.py:141-144`) a été posée le 2026-09-23 : **aucune règle n'a jamais traversé la
porte**, et 0/68 enveloppe porte `reviewed_by` (les 68 valent exactement `['name','rule','seal']`, recompté le
2026-09-24). Rien d'autre ne l'attrape : `check_preregistration_applied.py` ne lit que des noms de DV
(`_MEASURE_FIELDS:37`), `check_control_family.py` ne contient ni « cout » ni « revue ».
À ÉCRIRE : ne pas élargir le motif (deviner), mais **faire DÉCLARER** — doctrine du dépôt
(`tools/demand_marker._degeneracy`, `tools/check_guard_negative_cases.py`) : dans `preregister()`, refuser une
NOUVELLE règle qui ne porte ni clé de coût ni déclaration EXPLICITE d'absence de run (`cout: "aucun run"`, ou
`sans_run: true`), via une exception nommée `CoutNonDeclare`. ⚠️ **Le témoin à geler n'est PAS « la branche fausse »** :
elle est DÉJÀ exercée — `tests/sandbox/test_preregistration_guard.py:179`
(`test_une_regle_SANS_cout_declare_ne_l_exige_pas_et_une_existante_se_rescelle_sans`) scelle une règle sans clé de
coût sans `reviewed_by` et affirme `declare_un_cout(rule) is False` à `:186`. Le témoin MANQUANT est l'autre : une
règle qui déclare une échelle sous un nom HORS vocabulaire doit être REFUSÉE. ⚠️ Et il ne peut pas être
`EVO-006-REPLICATION` verbatim : mesuré, la sceller telle quelle lève `IncompleteDiscrimination` (ses 3 branches n'ont
pas d'attrape-tout) AVANT d'atteindre la branche de coût — le cas à geler est sa FORME plus une
`regle_de_lecture_continue`. La demande ne porte QUE sur la création : le re-scellement à l'identique sort en `:135`
avant d'y arriver, et `verify()` passe **68/68** aujourd'hui. Aucun appelant ne bouge, et pour une raison plus forte
que « les 43 importateurs n'y touchent pas » : **aucun module du dépôt n'appelle `preregister()`** — les 43
importateurs (32 sous `tools/`) importent `verify` (32), `stamp, verify` (14) ou `provenance` (13), et le seul `from
tools.preregister import preregister` est `preregister.py` lui-même. Les 68 règles ont donc toutes été scellées hors
code suivi — raison de plus pour que la demande vive DANS `preregister()`, seul point de passage possible. *Coût :
agent ~1 h ; calcul 0.* Dépend de : rien. Lié à P2.94.
<!-- closes_when:grep_present=tools/preregister.py::CoutNonDeclare -->

**P2.94 — ⚠️ OUVERTE (2026-09-24) — `reviewed_by` est posé HORS du sceau : sa SUPPRESSION et sa FORGERIE passent
toutes deux `verify()`, et aucun lecteur ne peut même le relire — alors que le mettre DANS le sceau coûte ZÉRO
re-scellement.**
⚠️ **Entrée trouvée EN PASSANT pendant la mesure de P2.93 et NON passée au réfutateur** : les trois faits structurels
ci-dessous ont été re-vérifiés par le synthétiseur le 2026-09-24 ; le prototype « design B » (68/68 sceaux préservés)
est en revanche la mesure du seul investigateur et n'a été rejouée par personne.
Quoi : `_seal()` (`tools/preregister.py:106-108`) ne hache que `rule` — vérifié : `return
hashlib.sha256(json.dumps(rule, sort_keys=True, …))` ; `preregister()` écrit `payload["reviewed_by"] = reviewed_by`
dans l'ENVELOPPE (`:145-146`, à côté de `name` et `seal`) ; `verify()` recompute `_seal(payload.get("rule", {}))`
(`:199`) et rend `payload["rule"]` seul (`:202`). Mesuré dans un répertoire temporaire, avec contrôle POSITIF
d'abord : retoucher `rule` lève bien `PreregistrationTampered` — le sceau MARCHE ; puis SUPPRIMER `reviewed_by` →
`verify()` PASSE ; puis FORGER un `reviewed_by` (« docs/reviews/2026-01-01-revue-qui-n-a-jamais-eu-lieu.md ») sur une
règle qui n'en avait pas → `verify()` PASSE ; et `verify()` ne rend que `rule`, donc `reviewed_by` n'est même pas
LISIBLE par l'API : aucun lecteur ne peut vérifier l'attestation ni constater son effacement. La porte `ReviewRequired`
est donc DÉCORATIVE au sens d'E10 — elle exige une revue à l'écriture, et le dépôt ne peut ni la relire ni détecter sa
disparition.
Instances aujourd'hui : **0/68** — recensement refait le 2026-09-24, les 68 enveloppes portent exactement
`['name','rule','seal']`, 0 illisible, la porte ayant un jour d'âge. C'est précisément la fenêtre où le correctif est
gratuit. Le point qui DÉCIDE, mesuré et non raisonné : *design A* (le sceau porte TOUJOURS `{rule, reviewed_by}`, même
absent) change **68/68** sceaux, casserait les **13** sceaux CITÉS hors `docs/preregistrations/`
(`results/bilinear_aligned_r1.json`, `legacy_cause_de_mort.json`, `legacy_lr_curve_r1.json`,
`legacy_lr_curve_r2.json`, `legacy_nan_guard_r1.json`, `legacy_wm_guard_r1.json`,
`s2_blind_champion_bis.json`, `s2_blind_champion_ter.json`, `s2_blind_champion_decomp_r1.json`,
`td_step_pilot_r0.json`, `td_step_pilot_r1.json`, `td_step_pilot_r2.json`, `bilinear_sham_r1.json`) et rendrait tout re-scellement idempotent impossible
(`PreregistrationConflict`, `:130`). *Design B* — le sceau BRANCHE : `_seal(rule)` quand `reviewed_by` est absent,
`_seal({"rule": rule, "reviewed_by": …})` quand il est présent — prototypé et mesuré : **68/68 règles gardent leur
sceau exact, 0 cassée, 0 re-scellement, 13 citations intactes**, et les six cas se comportent (intacte VRAI · `rule`
retouchée FAUX · `reviewed_by` supprimé FAUX · `reviewed_by` forgé FAUX · légataire sans revue intacte VRAI · revue
AJOUTÉE à une légataire FAUX). Donc **non, les 68 n'ont PAS à être re-scellées** — à condition d'écrire la branche.
(Le premier prototype, qui enveloppait TOUJOURS `rule` dans `{"rule": …}`, cassait 68/68 : l'écart entre les deux
designs est mesuré, pas argumenté.)
À ÉCRIRE : la branche dans `_seal`/`verify` de `tools/preregister.py`, `verify()` qui rend aussi l'attestation (ou un
`attestation(name)`), et les témoins manquants dans `tests/sandbox/test_preregistration_guard.py` — ses 19 tests
couvrent la FORME de `reviewed_by` (`:189`, `:198`) mais AUCUN n'essaie de l'effacer ni de le forger :
`def test_supprimer_reviewed_by_est_DETECTE`, `def test_forger_reviewed_by_est_DETECTE`, et le test de non-régression
des 68 (`test_the_repository_preregistrations_are_all_intact:67`) qui doit rester vert. ⚠️ Traiter dans la même passe
le cas jumeau : `name` est lui aussi HORS du sceau (0/68 instance, mais un payload dont le `name` ment passe
`verify()`) — l'y ajouter changerait 68/68 comme le design A, donc le laisser hors sceau et le VÉRIFIER contre le nom
de fichier dans `verify()`, ce qui est gratuit. *Coût : agent ~1 h ; calcul 0.* Dépend de : rien. Lié à P2.93.
<!-- closes_when:grep_present=tests/sandbox/test_preregistration_guard.py::def test_supprimer_reviewed_by_est_DETECTE -->

**P2.95 — ⚠️ OUVERTE (2026-09-24, mesurée en lecture seule) — la règle `review:` est ARMÉE et GELÉE sur 232 EDR à
verdict, et son chemin de SUCCÈS n'a jamais été parcouru sur un record réel : `docs/reviews/` ne contient que son
README.**
Quoi : `tools/check_record_links.py` exige qu'un EDR à verdict porte `review:` désignant un fichier RÉEL — forme
`docs/reviews/<AAAA-MM-JJ>-<slug>.md` (`_REVIEW_PATH`, l.49) ET existence sur disque (`_review_defect`, l.52-61),
exigence appliquée l.150-153. Re-mesuré le 2026-09-24 : `--report` rend `records=325 orphelins=18 collisions=7
gate_non_raccordés=67 mismatches_gate_tests=0 sans_revue=232`. Décomposition recomputée depuis `scan_records`,
jamais recopiée : 325 = **299 EDR + 16 REF + 5 SDR + 5 ADR** ; le périmètre est les **232 EDR à verdict** (`gate:`
dans G0-G4/`foundational` OU `tests:[SDR-Gx]`), et **93 records sont HORS périmètre** (67 EDR sans aucun raccord de
porte + 26 non-EDR, la branche étant `r["type"] == "EDR"`). Les 232 défauts sont tous de raison `absente`, et
**aucun record du dépôt, tous types confondus, ne porte un champ `review:` non vide**.
⚠️ **La moitié « poser la règle pour les NOUVEAUX » est DÉJÀ FAITE — la réécrire produirait une entrée née close.**
`tools/record_link_baseline.json` gèle `review_missing_files = 232`, **set-égal** au courant (vérifié élément par
élément : 0 en trop, 0 en moins) ; `tools/hooks/pre-commit` l.22/24 lance la porte ; `tools/preregister.py:141`
refuse une règle scellée à coût déclaré sans `reviewed_by=` au même format. Le cliquet produit bien les DEUX issues :
baseline réelle → exit 0 ; même baseline amputée d'une entrée → `[EDR-097, absente]`, exit 1.
Ce qui manque est autre chose : **le chemin de SUCCÈS de la porte n'a jamais été parcouru sur un record réel.**
`git ls-files docs/reviews/` rend UNE ligne, son README. Zéro revue, zéro `review:`. Et ce n'est pas une porte
aveugle — contrôle de BOUT EN BOUT (confronter `_review_defect` à des chaînes ne suffit pas : ça contourne
`parse_record`) : dans un faux dépôt, un record dont le frontmatter porte `review: docs/reviews/…md` est LU et SORT
de `review_missing` ; le fichier de revue supprimé, il y rentre en `fichier introuvable`. La porte sait dire OUI ;
personne ne le lui a jamais fait dire sur un record du dépôt.
Pourquoi ce n'est pas de la négligence, et pourquoi ça reste une dette : l'instrument de revue a échoué DEUX fois sa
propre calibration (`.superpowers/sdd/2026-09-16-portes-18-19-20-refutateur/progress.md`) — clé de réponse voyageant
avec l'instrument, puis **plancher de fausses retrouvailles à 4/4** (une revue VIDE passait les quatre témoins, une
revue JUSTE échouait) ; la ronde 4 (`c4d69b7`) ramène ce plancher à 0/5. Le « Step 4 : première revue réelle » du plan
est **NON EXÉCUTÉ**, et sa cible est un TÉMOIN gelé (un SHA), pas le record courant : l'exécuter ne posera `review:`
sur aucun record et ne bougera pas la baseline. Cette entrée porte exactement ce résidu.
Ce que ça coûte : `CLAUDE.md:329` justifie l'obligation de revue par « **7 revues, 7 erreurs réelles trouvées** » —
ligne **sans balise `count:`** (contrôle positif : 4 balises existent), donc jamais recomputée. Ces 7 revues ont bien
laissé des traces, mais **en PROSE dans les records** (`grep -c -i revue` : 4 sur WARM-004, 3 sur WARM-008, 2 sur
WARM-006 — « ## Corollaires établis par la revue adversariale », « Correction majeure post-revue ») : jamais un
document autonome portant ses sondes, ses verdicts par prompt et ses commandes rejouables. Conséquence mesurable :
les compteurs du rôle Réfutateur (spec §2.3, « critiques émises / confirmées », lus dans `docs/reviews/*.md`) ont
zéro entrée.
À ÉCRIRE : (1) une première revue `docs/reviews/<date>-<slug>.md` produite par le workflow sur un record COURANT
(§ « Lancer une revue » de `docs/reviews/README.md:9`, témoins extraits par `tools/refutateur_temoins.py --extraire` ;
`statut: NUL` → rien ne s'écrit) ; (2) le `review:` correspondant au frontmatter du record ; (3) `python
tools/check_record_links.py --update-baseline`, qui ne retire la ligne QUE si `_review_defect` rend None (forme ET
existence). Les trois dans le MÊME commit (règle citation+artefact). **Cible n°1 mesurée : `EDR-CALIB-LEARNER`**
(`docs/EDR/CALIB-LEARNER_InWorld_Learner_Learns_At_Unbounded_Dose_The_Published_Nulls_Were_Dose_Bounded.md`), indegré
**7** — maximum du périmètre, ex æquo avec `EDR-AUDIT-001` — ET cité par CLAUDE.md. Vérifié : ce chemin n'apparaît
dans AUCUNE autre liste de la baseline, donc la clause bascule sur ce seul motif. ⚠️ **Échappatoire connue de la
clause, à ne pas emprunter** : supprimer ou renommer le record puis regeler la baseline la satisferait sans aucune
revue — la clause observe le resserrement, pas l'intention ; le commit de fermeture doit porter le fichier de revue
lui-même.
Lot PORTEUR pour la suite, mesuré : sur les 232, **98 sont cibles d'au moins une arête entrante** (471 arêtes, **0
pendante**), **16 ont un indegré ≥3**, et **14 sont cités par CLAUDE.md**. ⚠️ Ce 14 est une mesure REFAITE : un
appariement par id ENTIER n'en trouve que 7, parce que CLAUDE.md cite aussi par id NU (`S2-011`, `WARM-005`,
`S2-CREDIT-ABLATION`, `S6-FALLBACK-RATE`…) ; la variante qui accepte en plus un suffixe NUMÉRIQUE nu en rend 25, mais
ses gains sont des faux positifs de prose (`121 sites légataires` → « EDR-121 », `+0,156` → « EDR-156 »). Union
{indegré ≥3} ∪ {cités} = 25, moins `EDR-RETAIN-COMPOSE` (rétracté ; dans `build_graph`, `from` est le RÉTRACTÉ) →
**lot net de 24**. Exiger 232 revues rétroactives est absurde ; 24 ne l'est pas, et les **206** restants demeurent
gelés sans dette nouvelle possible. ⚠️ `adopts:` n'est PAS un proxy de « porteur » : les 113 arêtes `ADOPTE` visent 7
cibles — 112 des ancres REF et 1 l'ADR-004 ; **aucun EDR n'est adopté**. *Coût : un agent par revue, lecture seule +
sondes, aucun run de monde.* Dépend de : la ronde 5 du Réfutateur (calibrer l'instrument AVANT de graver un
artefact). Lié à P2.25 (une revue dont les vérificateurs meurent rend « 0 défaut confirmé »).
**FUSION 2026-09-25 (PM) : trois records nés sur la cible SANS `review:` gelés, 232 → 235.** `S2-002-PAIRED-R1`,
`S2-CREDIT-ABLATION-2`, `TD-STEP-PILOT-R2` ont été committés sur `feat/d1-prod-pairing` avant que la règle « nouveau
record ⇒ revue SUIVIE » n'y arrive par cette fusion ; la porte 1 les refusait comme NOUVEAUX. Gelés dans
`tools/record_link_baseline.json` (`review_missing`). `S2-CREDIT-ABLATION-2` déclare une revue EN PROSE (21 griefs
confirmés sur 22) sans aucun chemin suivi — exactement le cas de cette entrée. La règle vaut pour tout record né APRÈS. Fusion de `feat/harness-r1` le même jour : + `EDR-HARNESS-R1` (né sur sa branche avant la règle), même gel → 236.
<!-- closes_when:grep_absent=tools/record_link_baseline.json::CALIB-LEARNER_InWorld_Learner -->

**P3.4 — rang 14 — ✅ CLOSE le 2026-09-15 ([[EDR-CALIB-LEGACY-LEARNER]], `results/legacy_learner_calibration.json`) — Cas de calibration de l'apprenant LEGACY.**
Quoi : `MambaBatchModel.compute_policy_gradient` (le chemin actif pendant tout l'arc EVO), mêmes bras
que P1.6 (oracle / apprenant / apprenant coupé), cohorte immortelle, n = 12. Le panel l'a mesuré à n = 1
comme NON plat (OFF 0,13 = chance 1/8, naturel 0,35) — à confirmer ou infirmer. *Coût : agent 1-1,5 h ;
calcul ~5 min.* Dépend de : P1.6.
Fait : (a) `LR_ACTOR = 0.04` / `LR_CRITIC = 0.05` deviennent des **knobs de classe** de `MambaBatchModel`
(forme de `TD_GAMMA`, bit-identiques) — le bras de référence `lr=0` est le **même code à pas nul** (clip,
écriture de `genome.W`, bookkeeping `_td`), jamais un no-op patché ; (b) `count_learning_events` couvre le
legacy (`legacy_calls` / `legacy_updates`, ΔW mesuré sur les GÉNOMES avant/après — le monde recrée le modèle
à chaque tick ; `td_enabled=False` saute, `reward_scale` multiplie, `lr` pose l'acteur et garde le ratio
critic 1,25) ; (c) `run_learner_probe(policy="legacy")` ; (d) `tools/legacy_learner_calibration.py`, mêmes
quatre bras que P1.6 (`oracle` / `lr0_reference` / `natural` / `lr_low`), `summarize(learner_arms=…)` ;
(e) la collision `compute_policy_gradient` est couverte **5/5, qualifiée** (mamba_agent : 1ᵉʳ appel différé,
**signe de l'update PRÉDIT** sur la colonne du move choisi, `sign(ΔW[:, col]) == sign(δ·h)` pour les deux
signes de δ, lr=0 bit-identique, knobs par défaut ; torch_batch_model par ses tests ; baseline no-op PROUVÉ ;
ablation délégation PROUVÉE ; wrapper du compteur 6 cas) — baseline `instrument_calibration_baseline.json`
**3 → 2** ; CLAUDE.md / SDR G2 226 calibrés / 2 dettes. Coût réel du run : unité **78 s** (legacy 2000
ticks × 12 agents), 48 cellules ≈ 50 min — l'estimation « ~5 min » du panel était fausse d'un ordre de
grandeur — mesuré au final **37,8 min** de cellules. **VERDICT n = 12 GRAVÉ** : `lr_low` (0,004) apprend
**11/12**, +0,318 vs lr=0 apparié (0,446 contre 0,277 pour le torch de P1.6) ; `natural` (0,04, tel que publié)
est **INSTABLE** — 2 seeds à 0,51, **4 seeds effondrés à 0,000** (sous la chance, politique bang-bang au clip),
**1 seed NaN** (cellule non mesurée, PUBLIÉE avec sa raison, comptée au dénominateur), 6/12 ; létalité 18 265
résurrections/seed contre 0 pour l'oracle. Trouvé EN PASSANT et attrapé par le COMPTEUR : à `lr=0` W bouge
quand même (180 updates/2000 ticks ; 299/300 hors monde) — le compilateur NTM (`compile_and_apply` dans
`forward`) écrit W_batch, persisté par l'appel de gradient ; `ABLATE_NTM=True` → 0/300. **W a deux auteurs**
(E8 occ. 5 au registre). Bandeau sur EVO-005 (sa convergence « crédit ET sélection » perd la jambe crédit,
verdict intact). Le runner publie une cellule refusée au lieu de tomber (`summarize` tolère `learning=None`,
`non_mesures` et `seeds_non_mesures` publiés, 2 tests). Ce qui reste (ouvert, non chiffré) : la courbe de pas
n'est pas tracée (deux points) ; ce qui TUE les apprenants legacy (0,76 mort/agent/tick) n'est pas mesuré.
<!-- closes_when:grep_present=tests/sandbox/test_instrument_calibration.py::compute_policy_gradient -->

**P3.5 — rang 15 — ✅ CLOSE le 2026-09-15 — Hygiène de backlog CIBLÉE (pas de refonte) + re-scellage de la règle des portes.**
Quoi : (a) `_ENTREE` de `tools/check_backlog_freshness.py` ne voit pas `**P1.x / P2.45 —` (le `x`) : les
titres composites échappent au compte de doublons ; (b) les entrées « ✅ CLOSE » qui portent un « Ce qui
reste » avec du travail réel (P2.13, P2.15, P2.26, P2.28, P2.29, P3.3, SP-2) : extraire le reste en
entrée OUVERTE ou le déclarer abandonné ; (c) l'en-tête l.11 (« le déficit reste dominant ») contredit
le titre l.17 (« DETTE CLOSE ») ; (d) `## P3` se dit « BLOC PÉRIMÉ » et contient P3.3, mesurée le 09-08 ;
(e) la puce `check_staged_authorship` « empreinte TARDIVE » est en double (bloc 2026-09-07) ;
(f) re-sceller la règle des portes dans `docs/roadmap/FIL_DIRECTEUR_AGI.md` : within-subject, contrôle
positif co-exécuté, plancher de bruit publié, et le statut RÉEL de G0 (validée sur un marqueur réfuté).
*Coût : agent 1,5-2 h.* Dépend de : rien.
**(a) à (f) LIVRÉES le 2026-09-15.** (b) : P2.13 → reste RÉGLÉ le 09-06 (famille `run_*`), annoté ; P2.15 → extrait en **P2.70** ; P2.26 → extrait en **P2.71** ; P2.28, P2.29 → aucun reste actionnable (limites de conception déclarées) ; P3.3 → reste DÉCLARÉ NON PLANIFIÉ (direction de recherche) ; SP-2 → son reste (type de nœud « tâche », power-up à n ≥ 12) est structurel, laissé en place. (c) l'en-tête l.10 porte désormais l'état au 09-15 et renvoie à « DETTE CLOSE » ; (d) `## P3` est « BLOC HISTORIQUE, sauf P3.3 » ; (e) la seconde puce « empreinte TARDIVE » retirée (compte d'entrées inchangé, −8 lignes signalées par la porte 16). (a) `_NUM`/`_TETE` dans `tools/check_backlog_freshness.py` : une tête composite vote pour chacun de ses numéros, `P1.x` est un substitut (jamais un numéro), et `_ENTREE`, `_TASKNUM` et `compter_entrees` lisent la MÊME tête (une entrée invisible au compte serait effaçable sans que le plancher bouge) ; 4 contre-exemples gelés dans `tests/sandbox/test_backlog_freshness.py` (3 ROUGES contre HEAD + 1 no-op de spécificité) ; mutation « les titres COMPOSITES redeviennent invisibles » déclarée à la porte 15 (porte 4 : 3/3 TUÉES). Le cliquet élargi a révélé un VRAI doublon — P2.45 en tête de l.2326 et l.2981 — résolu en renommant l.2326 en `P1.x` (jamais gelé en baseline). (f) règle des portes re-scellée dans `docs/roadmap/FIL_DIRECTEUR_AGI.md` § « Règle des portes — re-scellée le 2026-09-15 » : within-subject, contrôle positif co-exécuté, plancher de bruit publié, statut RÉEL de G0 ; ratio S2-009 harmonisé (≥ 22× = cap/plancher, 21,05 au run d'origine). **Restent (b), (c), (d), (e).** Vu en passant : `compter_entrees()` ré-épelle le chemin du backlog au lieu de lire `_BACKLOG` — un test qui monkeypatche `_BACKLOG` vers un jouet ne fait pas compter ce jouet par le plancher (sans effet aujourd'hui, les tests du plancher monkeypatchent `compter_entrees` ; à aligner quand on touche (b)).

**P3.6 — ✅ CLOSE (2026-09-15) — rang 16 — Bandeaux de portée posés APRÈS le verdict de P1.6 (jamais avant : E8).**
→ **LIVRÉ le 2026-09-15** (worktree isolé, 5 fichiers, +114 lignes, 0 suppression ; tests GREEN 8/8, sept portes OK).
Bandeaux de PORTÉE datés 2026-09-15, chaque phrase citant la mesure et le record :
(1) S2-010 — complément du bandeau du 09-14 (le « prochain test décisif » a été exécuté : bassin DAgger 36,0 → 8,0,
12/12, `ERODE`, S2-CREDIT-RETENTION ; Δénergie seule érode autant, −28,5 vs −28,25, différence appariée 0,0, et
curiosité MORTE sous torch, S2-REWARD-ABLATION) + bandeau §Portée qui nomme le **TD par tick**
(`src/worlds/world_1_stoneage.py:1717`, il CONTRIBUE : TD coupé = pire variante, 2/12, CALIB-LEARNER) et la dose
≈ 48 mises à jour / agent (S2-CREDIT-RETENTION § Verdict) ; (2) S2-011 — complément + bandeau sous « Prochain pas
précis » : exécuté par WARM-001 (acc on-policy 0,734, survie ~15) et WARM-003 (35,2/200, marqueur 5,04) ; la
précondition « survit SANS crédit ~200 » est mesurée FAUSSE (35,2 WARM-003 ; 36,0 bras a de S2-CREDIT-RETENTION)
et « PUIS activer le crédit » = ÉRODE 12/12 ; (3) S2-BLIND-CHAMPION et S2-SUBJECT-VARIANCE — corps NON apparié
(classe E26 : `make_blind` fait tomber le drain de 2,40 à 1,30, −46 % ; câblés / amplifiés à drain 11,0 / 15,0),
tout contraste ENTRE sujets à relire avec `assert_phenotype_matched(subject, reference, tol=0)`, lest
`ballast_phenotype` disponible mais REFUSÉ sur le champion HoF tel quel (E24, 64 + 126 > 172) ;
(4) SPECIFICATION_10ANS — bandeau d'archive COMPLÉTÉ, pas écrasé : « §2 conditionnelle à P1.6 » levée par la
mesure (CALIB-LEARNER : contrôle positif oracle 1,000, référence lr=0 à 0,126, 12/12, +0,156), contrainte 6
(bassin pré-formé) NÉCESSAIRE et non suffisante, pari C tranché défavorable, « 1 sur 71 » périmé, plancher de bruit
±6-8 % de l'instrument d'ablation (S2-BLIND-CHAMPION). **Frontmatter — choix et raison** : S2-010 / S2-011 GARDENT
`corrected_by: [EDR-CALIB-LEARNER]` (une seule occurrence, pas de doublon ; S2-CREDIT-RETENTION déclare `extends`,
pas `corrects`, donc aucune arête inverse ajoutée) ; S2-BLIND-CHAMPION / S2-SUBJECT-VARIANCE : bandeau SEUL, sans
`corrected_by:` — nul record ne porte la mesure E26 (elle vit dans le registre, la garde et
tests/sandbox/test_phenotype_guard.py), les verdicts scellés (`INDETERMINE-HARNAIS` / `INDETERMINE-INSTRUMENT`) ne
changent pas et n'ont jamais lu leur DV ; seules les lectures secondaires (+39 % ; dose-réponse ×3 / ×8, phrase du
titre de SUBJECT-VARIANCE) deviennent des ARTEFACTS CANDIDATS jusqu'aux `-bis` à corps lesté (P2.42 rang 20,
P2.43 rang 5). Gelé par tests/sandbox/test_p36_scope_banners.py (8 cas : littéral « TD par tick », chiffres
35,2 / 36,0 / 2,40 / 1,30 / 11,0 / 15,0, non-duplication du bandeau du 09-14, `corrected_by` conservé, bandeau
d'archive conservé, tout record cité par un bandeau du 09-15 EXISTE — garde E8 sur le bandeau lui-même).
Résidu consigné, non bloquant : le bandeau du 09-14 de S2-011 cite `results/warm003_dagger_genome.npz`, que
`tools/evo_runs/s2_credit_retention.py::BASSIN_PATH` charge, et ce fichier n'est PAS suivi par git (absent d'un
clone : même forme que la CI rouge du 2026-09-07) — à persister ou à documenter comme artefact local.
Quoi (tel que posé) : S2-010 §Portée (le TD par tick n'est pas nommé ; dose de crédit ≈ 48 mises à jour / agent),
S2-011 (« prochain pas » déjà exécuté par WARM-001 / WARM-003 ; précondition « survit ~200 » mesurée
fausse), S2-BLIND-CHAMPION et SUBJECT-VARIANCE (corps non apparié, P1.7), SPÉCIFICATION_10ANS (bandeau
« 1 sur 71 » périmé, §2 conditionnelle à P1.6). Chaque bandeau cite la mesure qui le fonde.
*Coût : agent 1 h.* Dépend de : P1.6, P1.7.
<!-- closes_when:grep_present=docs/EDR/S2-010_InWorld_Credit_Does_Not_Bootstrap_Perception_Even_Under_Curriculum.md::TD par tick -->

**P4.5 — rang 17 — ✅ CLOSE le 2026-09-15 ([[EDR-LOCK-002]], [[EDR-LOCK-003]]) — Test de la prédiction de LOCK-001 en PROXY : `LOCK-001-PROXY` — mémoire D = 2,
dans l'ordre déjà prescrit par le dépôt.**
> **Clôture** : les sept barreaux scellés (`LOCK-001-PROXY-R1`, `-R1c`, `LOCK-001-PRED2-R1`…`-R4`, `-N12`) sont mesurés,
> deux records gravés, bandeaux posés après verdict. Reste OUVERT, non chiffré et hors de cette entrée : le troisième fil
> (régime de recherche, EVO-016), 28 800 épisodes, et la question du substrat favorable (bilinéaire / plain).
> ✅ **BARREAU 1 MESURÉ le 2026-09-14 (75 min CPU réels, majorant projeté 105) : branche `PERCE_PAR_LR`.**
> À D = 2, 14 400 épisodes : **`lr = 0,002` reste à la chance** (0,178 / 0,167 / 0,156) **et son contrôle
> est DÉGRADÉ** (ctrl_i 0,29–0,31) ; **`lr = 0,0005` apprend : 0,837 / 0,781 / 0,784** (médiane 0,784),
> bras ablaté à la chance (0,19 / 0,16 / 0,17), contrôle sain (0,998 / 0,981 / 0,997). À 7 200 épisodes et
> `lr = 0,002` : chance aussi (0,15–0,19). **Le « mur D = 2 » du point-référence était un artefact de pas
> d'apprentissage — E19, le motif exact de RETAIN-COMPOSE-LR (0,02 → 0,173 / 0,002 → 0,923)** — et c'est la
> clause E19 scellée AVANT le run qui l'a attrapé : sans le second `lr`, la branche eût été `NE_PERCE_PAS`
> et le levier « épisodes plus longs » déclaré épuisé. ⚠️ n = 3, indicatif seulement : la règle interdit
> tout record et impose le barreau 1b.
> ✅ **BARREAU 1b MESURÉ le 2026-09-14 (24/24 cellules, ~5 h à charge partagée) : branche `mur_perce`.**
> PRINCIPAL `X_DEMANDED` **4,85×** (0,814 / 0,168, n = 12), PRESENT `X_DECOY` (0,941 / 0,859), garde
> d'alias `SURGICAL` (fuite 0,028, 0 seed), barre 0,814 ≥ 0,5. **Record gravé : [[EDR-LOCK-002]]** ;
> bandeaux posés APRÈS le verdict : LOCK-001 (`corrected_by`, 4ᵉ manifestation retirée — E19) et
> DELAYED-COORD (sa re-mesure à `lr = 0,002` n'est pas un balayage suffisant : 0,002 est encore trop
> haut pour D = 2 sur la tâche mémoire). Aucune arête neuve (language→memory existe) : son evidence
> s'étend d'un délai à deux. **Suite, dans l'ordre** : (1c) `lr = 0,0005` à 3 600 épisodes, 3 seeds,
> ~9 min — « le pas seul ? » ; (2) **la prédiction n° 2 de LOCK-001 est devenue testable** : le pas
> perce le fil mémoire ; perce-t-il DELAYED-COORD à `lr = 0,0005` ? Si non, l'identité des trois murs
> est réfutée par sa propre clause — c'est le prochain run du fil B, à sceller. Le curriculum et
> l'amorçage (barreaux 2-3) ne sont PLUS nécessaires pour ce fil : le mur y est tombé au barreau 1.
> ✅ **1c MESURÉ (7,5 min) : `PAS_SEUL`** — à 3 600 épisodes, `lr = 0,0005` donne 0,523 / 0,503 / 0,420
> (médiane 0,503 > plafond 0,389 du séparable) contre 0,18 à 0,002 : le pas SEUL débloque, la durée
> amplifie (0,78 à 14 400). Règle `docs/preregistrations/LOCK-001-PROXY-R1c.json`, résultats
> `results/lock_001_proxy_r1c.json`, addendum dans EDR-LOCK-002.
> ✅ **PRÉDICTION N° 2, barreau 1 MESURÉ (2026-09-14, 23:15, ~1 h 10) : `SANS_REFERENCE`** — PRESENT
> (référence sans rétention) reste sous 0,30 aux trois points (0,270 / 0,245 / 0,259), RETAIN 0,195 /
> 0,256 / 0,245 : la clause E19 refuse la lecture. **Ni soutien ni réfutation.** Fait utile : sur cette
> tâche la référence apprend à `lr` ÉLEVÉ (0,40 à 0,05, plain, n = 12) et pas à 0,0005 — l'inverse de
> la tâche mémoire. **Barreau 2 (à sceller) : balayage `lr` de la référence sur bilinéaire (0,05 /
> 0,01 / 0,002 / 0,0005, 3 600 ép., RETAIN + PRESENT, 3 seeds) ; tester RETAIN là où PRESENT ≥ 0,30.**
> ✅ **Barreau 2 MESURÉ (23:40, 30 min) : `SANS_REFERENCE` aux QUATRE pas** — sur bilinéaire, PRESENT reste
> à 0,245–0,270 partout (0,05 : 0,269 ; 0,01 : 0,269 ; 0,002 : 0,270 ; 0,0005 : 0,245), RETAIN 0,17–0,26.
> Le fait neuf est le SUBSTRAT, pas le pas : sur plain la référence atteignait 0,40 (n = 12, 1 600 ép.) ;
> le bilinéaire qui débloque la mémoire semble nuire à la coordination. **Barreau 3 : même grille sur
> PLAIN à 3 600 ép.** — sépare substrat et durée ; si PRESENT y apprend, RETAIN se lit enfin.
> ✅ **Barreau 3 MESURÉ (2026-09-15, 00:20, ~35 min) : `AUTRE`** — sur PLAIN à 3 600 ép., la référence
> apprend à pas élevé (PRESENT 0,480 à 0,05 ; 0,439 à 0,01) et RETAIN y reste à 0,21–0,22 ; à 0,002
> PRESENT est exactement au seuil (0,303) et RETAIN à 0,331 (zone nommée AUTRE : entre 0,30 et 0,35) ;
> à 0,0005 PRESENT 0,278 (non interprétable), RETAIN 0,320. Rapporté tel quel, sans inférence, comme
> la règle l'impose. Faits bruts : (a) le SUBSTRAT est en cause — même grille, PRESENT ≈ 0,26 partout
> sur bilinéaire vs 0,48 sur plain ; (b) les deux bras tirent en sens INVERSE du pas (réplique le
> 12/12 du n = 12) ; (c) RETAIN à pas bas MONTE avec la durée : 0,284 (1 600) → 0,331 (3 600).
> **Barreau 4 : la durée à pas bas sur plain** — 0,002 et 0,0005 × 14 400 ép. × 2 bras × 3 seeds.
> ✅ **Barreau 4 MESURÉ (2026-09-15, ~01:40) : `PERCE`** — plain, 14 400 ép. : à 0,0005, RETAIN **0,422 /
> 0,438 / 0,439** (médiane 0,438 ≥ 0,40, 3/3 > 0,30), PRESENT 0,347 (référence OK) ; à 0,002, RETAIN
> 0,353 (`MONTE`), PRESENT 0,447. **Le même levier (pas bas + durée) perce le second fil** : la
> prédiction n° 2 de LOCK-001 est SOUTENUE — l'identité survit à son propre test. n = 3 : la règle
> impose n = 12 sur ce point avant de graver → **barreau N12 scellé et lancé** (voir ci-dessous).
> Chemin complet du fil coordination : 1 600 ép. 0,284 (n = 12, lr 0,002) → 3 600 : 0,331 → 14 400 :
> 0,353 (0,002) / **0,438** (0,0005). Règle `docs/preregistrations/LOCK-001-PRED2-R4.json`, résultats
> `results/lock_001_pred2_r4.json`.
> ✅ **N = 12 MESURÉ (2026-09-15, 13:20, 2,6 h CPU) : `PERCE`** — RETAIN médiane **0,420** [0,400–0,439],
> **12/12 > 0,30**, ablaté 0,170 (chance), référence PRESENT 0,334 (tient, sous RETAIN : pas d'effet global).
> **Record gravé : [[EDR-LOCK-003]]** — le même levier (pas bas ET durée) perce les deux fils ; la
> prédiction n° 2 de LOCK-001 TIENT à puissance. Bandeaux APRÈS verdict : LOCK-001 (prédiction testée),
> DELAYED-COORD (« ne marche pas à 0,05 » → « apprend à 0,0005 / 14 400 »), LOCK-002 (justification
> de la barre 0,40 corrigée : le plafond 0,3889 cité est RÉFUTÉ depuis le 09-08). Aucune arête.
> **Ce que le fil B laisse ouvert** : le troisième fil (régime de recherche, EVO-016) n'est pas testé ;
> 28 800 ép. non mesurés ; le substrat favorable diffère entre les deux fils (bilinéaire / plain) —
> une identité de LEVIER, pas de réglage. **Fil B : objectif atteint, à mettre en pause au profit du
> fil A (P1.6/P4.4) sauf décision contraire.**
> *(Trace :)* N = 12 lancé le 2026-09-15 ~10:55 — règle `docs/preregistrations/LOCK-001-PRED2-N12.json` (seeds 0-11,
> population neuve, PERCE exige ≥ 11/12 seeds > 0,30 : convention de puissance du n = 12 de DELAYED-COORD ;
> branche PERCE → record LOCK-003 « le levier commun » + bandeau DELAYED-COORD ; NE_PERCE_PAS → identité
> réfutée), résultats à écrire dans `results/lock_001_pred2_n12.json` ; ~3 h 20.
> *(Trace :)* Barreau 3 lancé le 2026-09-14 ~23:45 — règle `docs/preregistrations/LOCK-001-PRED2-R3.json`
> (`fixe_override: bilinear=False`, lu par le runner), résultats à écrire dans `results/lock_001_pred2_r3.json` ; ~50 min.
> *(Trace :)* Barreau 2 lancé le 2026-09-14 ~23:35 — règle `docs/preregistrations/LOCK-001-PRED2-R2.json` (les deux
> points bas importés du barreau 1, les deux hauts mesurés), même runner (`--regle LOCK-001-PRED2-R2`),
> résultats à écrire dans `results/lock_001_pred2_r2.json` ; ~40 min.
> *(Trace du lancement du barreau 1 :)*
> 🔄 PRÉDICTION N° 2 — lancée le 2026-09-14 ~22:05 : règle `docs/preregistrations/LOCK-001-PRED2-R1.json`,
> runner `tools/lock001_pred2_r1.py` (lecture calibrée, 8 cas + continuum), DELAYED-COORD au point de
> LOCK-002 (bilinéaire, D = 2, `sender_lr` 0,05 fixe) : (0,002 ; 3 600), (0,0005 ; 3 600), (0,0005 ;
> 14 400) × {RETAIN, PRESENT} × 3 seeds, PRESENT = référence E19 (un point ne se lit que si PRESENT y
> apprend). Branches : PERCE (l'identité survit à son test) / MONTE / **NE_PERCE_PAS (la clause n° 2
> de LOCK-001 réfute l'identité des trois murs)** / SANS_REFERENCE / AUTRE — n = 12 avant de graver
> dans les deux sens. Coût mesuré machine libre : ~2 h ; résultats à écrire dans `results/lock001_pred2_r1.json`.
> *(Trace du lancement de 1b :)*
> 🔄 BARREAU 1b — lancé le 2026-09-14 ~16:20 (même session, fil B, fond CPU sans bail).
> Règle scellée `docs/preregistrations/LANG-MEMORY-EDGE-D2.json` : harnais `lang_memory_edge_run.py`
> (`EDGE_RULE=LANG-MEMORY-EDGE-D2`), protocole `-bis` (bruit de contrôle 0,15 — le contrôle saturait à
> 1,0/1,0 au barreau 1, donc la garde d'alias eût rendu DEGENERATE_CONTROL), 2 bras × **12 seeds**, D = 2,
> `lr = 0,0005`, 14 400 épisodes, barre d'émergence 0,5. Branches : `mur_perce` → record
> LOCK-001-PROXY-R1b + bandeaux de portée sur LOCK-001 et DELAYED-COORD APRÈS (P3.6), aucune arête neuve ;
> `reference_sous_barre` → négatif gravé puis barreau 1d (lr 0,0002 / 0,001) ; `instrument_indetermine` /
> `specificite_absente` / autre → tel quel. Coût projeté ~4 h (majorant).
> Résultats à écrire dans `results/lang_memory_edge_d2.json` (naît à la première cellule). **Question cheap laissée ouverte** : `lr = 0,0005` suffit-il déjà
> à 3 600 épisodes (le point-référence) ? — 3 seeds, ~9 min, à mesurer après 1b pour ne pas concurrencer
> son CPU.
> *(Trace du lancement du barreau 1 :)*
> Règle scellée AVANT toute cellule : `docs/preregistrations/LOCK-001-PROXY-R1.json` (branches
> INCOMPLET / PERCE_INDICATIF / PERCE_PAR_LR / TENDANCE / NE_PERCE_PAS / AUTRE, ordre imposé ; clause
> E19 par un second `lr` = 0,0005 sur le barreau du haut ; `AUTRE` prouvé VIDE sur le continuum des
> médianes par `tests/sandbox/test_lock001_proxy_r1.py`). Runner résumable `tools/lock001_proxy_r1.py`
> (design déclaré, famille de 9 cellules), résultats à écrire dans `results/lock001_proxy_r1.json`
> (le fichier naît à la première cellule, ~12 min après le lancement). Cellules : D = 2,
> lr 0,002 × {7200, 14400} et lr 0,0005 × 14400, seeds 0-2. **Coût mesuré à charge connue** (un job
> in-world tenait `kuzu`) : ~97 s / 1000 épisodes → ~105 min, majorant. n = 3 est EXPLORATOIRE : un
> PERCE déclenche le barreau 1b (n = 12), jamais un record. ⚠️ Re-scellé une fois avant toute cellule
> (grandeurs backtickées, porte 5) — noté dans la règle. Lecture : `python tools/lock001_proxy_r1.py --lecture`.

Quoi : dispositif = `tools/language_memory_demand_probe.py` au point-référence (bilinéaire, `lr = 0,002`,
3600 épisodes, D = 0 apprend à 0,744 ; D = 2 à la chance 3/3). Ordre des options, du moins cher au plus
cher (`tools/lang_memory_sweep_reference_point.py:101-103`) : épisodes plus longs → curriculum D = 0 → 1
→ 2 → **amorçage supervisé COURT du canal d'écriture, puis REINFORCE** (le test que LOCK-001 nomme
lui-même). Instrument NEUF à construire et calibrer d'abord : DV « écriture apprise » = dérangement
within-subject du canal PORTÉ + sender oracle ; no-op = fraction d'amorçage 0 ≡ froid bit-identique ;
famille déclarée (`assert_control_family`) ; `assert_verdict_invariant_to_optimizer` obligatoire sur tout
nul 2-pas (E19, RETAIN-COMPOSE-LR). Coût projeté ~22 s / cellule à 800 épisodes → ~14 h avec marge ×3,
CPU, sans bail : tourne EN FOND pendant P4.4. Deux issues : PERCE → premier levier sur le mur, à
transporter in-world (P4.6) ; NE PERCE PAS → la « quatrième manifestation » de LOCK-001 tient, et
l'amorçage rejoint les leviers réfutés. *Coût : agent 4-6 h (dont instrument) ; calcul ~14 h CPU fond.*
Dépend de : rien (parallèle à A).
<!-- closes_when:path_present=docs/preregistrations/LOCK-001-PROXY-R1.json -->

**P4.6 — 🗑️ CADUQUE (2026-09-14 : P4.4 rend ERODE, le bassin non érodé qu'elle exigeait n'existe pas) — rang 18 — Porte IW-1 (CONDITIONNELLE) : le crédit calibré ÉTEND-il un demi-lecteur warm vers
le bit non donné ?**
Ne s'ouvre qu'après P1.6 (variante d'apprenant scellée) ET P4.4 (bassin non ÉRODÉ). Re-spécifier avant
toute règle : demi-oracle p = 1/3 (prédiction [[EDR-WARM-010]] : 13-14 ticks, pas 17,5), DAgger (pas
BPTT : plafond 0,734 on-policy), volume enseignant APPARIÉ entre warms, DV `accuracy` conditionnée sur
le bit non donné = instrument neuf calibré, no-op torch construit. IW-2 (transfert zéro-shot) exige un
paramètre-monde θ qui VARIE réellement (G1-001) — famine hérite du flag `cognitive_demand`, donc même
tâche : ne pas lancer sans θ. *Coût : agent 3-5 j ; calcul 12-18 h.* Dépend de : P1.6, P4.4.

**P4.8 — ✅ CLOSE (2026-09-15, [[EDR-S2-REWARD-ABLATION]] : CREDIT_ERODE_SEUL, PLEIN) — rang 4 bis — Ablation
de la RÉCOMPENSE : le crédit poursuit-il la curiosité et la nouveauté plutôt que l'énergie ?**
Résultat : **Δénergie SEULE érode le bassin exactement autant que la récompense complète** (36,0 → 8,0 dans les
deux bras ; `d_energy` −28,5 vs `d_full` −28,25, 12/12 seeds ; différence appariée médiane 0,0, 3/12). Aucun terme
intrinsèque n'est nécessaire à l'érosion : le mur est le MÉCANISME DE CRÉDIT (TD(0) + REINFORCE, lr 0,04) sur
Δénergie, pas la récompense. Réplication de P4.4 bit-identique (b_full importé pour 11/12 seeds sur preuve) ;
réel 40 min. Suite : P4.9 (ablation du CRÉDIT).
État à la préparation : règle `S2-REWARD-ABLATION` scellée (cinq bras, 8 branches ordonnées) PUIS réduite en `-bis` à TROIS bras
(gelé / complète / Δénergie seule, budget 12 h dérivé des mesures P4.4) sur un fait de PRÉ-VOL trouvé au smoke
et qui valait ~10 h de calcul : **la curiosité (EDR 014) est MORTE sous le backend torch** — `backend_torch.py`
n'écrit jamais `model.surprise` (seul le forward legacy numpy le pose, `mamba_agent.py:824`), donc le terme
`curiosity_scale·surprise` vaut 0 à chaque tick et les bras « +curiosité » étaient BIT-IDENTIQUES à leurs jumeaux
(dW 1442,82 = 1442,82 sur 200 ticks). La récompense EFFECTIVE du crédit publié est `Δénergie + nouveauté`.
Runner `tools/evo_runs/s2_reward_ablation.py` : SEAM vérifié à réponse connue (décomposition exacte au tick 1,
`preflight_reward_seam`), curiosité morte MESURÉE avant chaque run (`preflight_curiosity_dead`, refuse un réveil),
`b_full` importé de P4.4 seulement sur réplication bit-identique constatée, verdict calibré 12 cas. Résultat →
record `EDR-S2-REWARD-ABLATION` (results/s2_reward_ablation.json, committé avec le record). Ce qu'il ne tranche pas : le contrôle à
récompense NULLE (dérive du critic seul) — à inscrire si l'issue est CREDIT_ERODE_SEUL ; et ce que ferait une
curiosité VIVANTE (voir P2.65).
Quoi (design initial) : même dispositif que P4.4 (bassin DAgger, phase immortelle 2000 ticks puis test mortel 200 ticks, n = 12,
bras appariés), bras (b) décliné sur la récompense de `world_1_stoneage.py:1713` : `Δénergie` seule ;
`Δénergie + curiosité` ; `Δénergie + nouveauté` ; récompense complète (réplique P4.4 = contrôle). DV `S_b`
par bras, `d_ba` apparié ; même règle de lecture (signe 10/12, ±5). Deux issues : l'érosion DISPARAÎT sans les
termes intrinsèques → le mur est une récompense mal alignée (levier : la récompense, pas le crédit) ; elle
RESTE avec `Δénergie` seule → le mécanisme TD(0) sur critic saturé (56 % des `value_pred` < −0,99 loggés,
P1.6) devient la cible. Pré-vol : le seam de récompense doit exister (curiosity_scale, novelty_scale à 0 —
vérifier qu'ils sont des paramètres, sinon en faire un). Coût : 4 bras × 12 seeds × ~10 min = projeter par
type de bras et sceller le budget sur MESURE (leçon P4.4). Pourquoi : [[EDR-S2-CREDIT-RETENTION]].
*Coût : agent 3-4 h ; calcul ~4-6 h sous bail.* Dépend de : rien.
<!-- closes_when:path_present=docs/preregistrations/S2-REWARD-ABLATION.json -->

**P4.9 — ✅ CLOSE (2026-09-22, [[EDR-S2-CREDIT-ABLATION]] : SIGNAL_QUELCONQUE / EPISODIQUE_SUFFIT /
ATTENUE_A_PETIT_PAS) — rang 4 ter — Ablation du CRÉDIT : l'érosion vient-elle du SIGNE du signal, du PAS, ou
du TD par tick ?**
Résultat (n = 12, mêmes seeds, `b_full` importé sur réplication bit-identique) : sans signal (`reward_scale` 0) le
crédit ne bouge presque pas (Σ|ΔW| 2,5 % du complet) et n'érode pas (`S_zero` 33,25 vs `S_a` 36,0, NEUTRE) ; le
signal INVERSÉ (`reward_scale` −1) efface le bassin autant que le vrai (`S_neg` 7,25 vs `S_full` 8,0, 12/12) ; la
voie ÉPISODIQUE seule (TD coupé) suffit (`S_tdoff` 7,5, 12/12, à 8 % du mouvement) ; le pas 0,004 atténue sans
retenir (`S_lr` 21,5, 9/12 érodés, mais 12/12 mieux que le pas publié). **Les deux mécanismes candidats de P4.8
(avantage constant négatif ; pas trop grand) sont RÉFUTÉS : l'érosion exige un signal, ignore son signe, n'est pas
proportionnelle au mouvement, et le destructeur est la mise à jour épisodique (REINFORCE k = 8) elle-même.**
Coût : réel 11,3 h dont 9,2 h sur UNE cellule (b_zero seed 2029 ; les 59 autres = 2,1 h, dans la projection) →
P2.78 (temps mur vs CPU). Suite : P4.16 (TD seul / retour constant / épisodique à petit pas, puis ancre au bassin).
État à la préparation :
règle `S2-CREDIT-ABLATION` scellée (10 branches ordonnées, budget 16 h dérivé des coûts P4.8, charge machine
connue et publiée : agents parallèles), runner `tools/evo_runs/s2_credit_ablation.py` (six bras : gelé / complète
importée sur réplication / `reward_scale` 0 / `reward_scale` −1 / `lr` 0,004 / TD coupé), quatre seams vérifiés à
réponse connue avant le run (`preflight_credit_seams` : ce qui ATTEINT le learner d'origine), verdict calibré 16 cas.
Pré-vol publié (32 ticks) : le bras sans signal bouge à ~2 % du complet (Σ|ΔW| 4 vs 186), le signe inversé à 84 %,
l'épisodique seul à 124 % — la discrimination signe/pas repose donc sur le bras à signe inversé, et un NEUTRE du bras
nul se lit avec son ratio de mouvement (règle, branche 7). Résultat → record `EDR-S2-CREDIT-ABLATION`
(results/s2_credit_ablation.json, committé avec le record).
Quoi (design initial) : même dispositif que P4.4/P4.8 (bassin DAgger cloné ×12, phase immortelle 2000 ticks, test mortel 200
ticks poids gelés, n = 12, mêmes seeds, `a_frozen` re-mesuré, `b_full` importé sur réplication bit-identique),
bras (b) décliné sur le CRÉDIT via `count_learning_events` — seams déjà calibrés par P1.6 : (b_zero)
`reward_scale = 0` (dérive du critic seul, aucun signal) ; (b_lr) `lr = 0,004` (E19, le premier suspect
depuis EDR-LOCK-002 — record de la session parallèle, à lier une fois committé) ; (b_td_off) `td_enabled = False` (épisodique seul). Issues nommées d'avance :
b_zero ERODE → le pas lui-même détruit à dose égale (bruit d'estimation) → cible = pas/optimiseur ; b_zero NEUTRE
et b_lr ERODE → le signe de l'avantage détruit (critic tanh saturé : 56 % des `value_pred` < −0,99) → cible =
centrer la récompense ; b_td_off NEUTRE → le TD par tick est le destructeur. Attention E2 : b_lr à dose égale
(1999 TD) déplace 10× moins — publier `Σ|ΔW|` par bras et lire « NEUTRE » à lr 0,004 comme « pas assez bougé »
si `Σ|ΔW|` < 10 % du bras complet. Pré-vol : le no-op `reward_scale = 1` est bit-identique (P1.6) ; le seam
`reward_scale = 0` doit rendre une trace de récompense nulle (à vérifier à réponse connue comme P4.8). Coût :
~50-370 s par bras et par seed mesuré en P4.8 → 3 bras × 12 seeds ≈ 1-2 h ; sceller le budget sur MESURE.
Pourquoi : [[EDR-S2-REWARD-ABLATION]]. *Coût : agent 2-3 h ; calcul 1-2 h sous bail.* Dépend de : rien.
<!-- closes_when:path_present=docs/preregistrations/S2-CREDIT-ABLATION.json -->

**P4.16 — ✅ CLOSE (2026-09-23, [[EDR-S2-CREDIT-ABLATION-2]] : CONTENU_INDIFFERENT / TD_SUFFIT_AUSSI /
EPISODIQUE_DESTRUCTEUR_A_PETIT_PAS) — rang 4 quater — Ablation du CRÉDIT, seconde passe : la voie ÉPISODIQUE
détruit-elle quel que soit le CONTENU du signal, et le TD seul détruit-il ?**
Résultat (n = 12, mêmes seeds, `b_full` importé sur réplication bit-identique) : **chacune des deux voies SUFFIT
seule à amener le bassin au PLANCHER** — TD par tick sans un épisode `S_tdonly` 8,5, complet 8,0, épisodique seul de
P4.9 7,5, contre un plancher froid mesuré à 7,5 (saturation 96-98 %) : le run établit une suffisance, PAS un ordre
(contraste apparié p = 0,344, DV saturée). Un retour constant +1 érode à mi-chemin (`S_const` 23,25, −12,25, 11/12,
à 5,4 % du mouvement) — mais ce bras mesure un OFFSET POSITIF de l'avantage (auto-renforcement), **pas** une absence
de contenu : l'avantage épisodique est centré par le monde en amont, et δ ≈ +1 sous critic borné. Le PAS reste la
seule dépendance quantitative de l'arc et il INTERAGIT avec la voie : à voie et dose égales, diviser lr par 10 fait
passer l'écart de −29,0 à −19,0 (12/12, p = 2,4e−4), mais à pas identique 0,004 couper le TD AGGRAVE l'érosion
(−14,0 → −19,0) en réduisant le mouvement de moitié. Direction contre amplitude NON tranché (aucun bras ne fait
varier la direction à amplitude appariée) → P4.18. **Record réécrit après revue adversariale à trois lentilles
(21 griefs confirmés sur 22) : les trois verdicts scellés tiennent, la prose débordait sur cinq points.**
Coût : mur 19,5 h contre CPU 4,3 h ; dénominateurs recomputés par le runner (`cost_cells`) — 60 cellules déclarées,
11 importées, 49 calculées dont 2 hors échelle (nuit), 431 s par cellule sur les 47 restantes. Suite : P4.18
(contrôle de FRAGILITÉ : bruit apparié en mouvement, avant tout remède), puis P4.19 (ancre au bassin).
État à la préparation : règle `S2-CREDIT-ABLATION-2` scellée (12 branches ordonnées, budget 16 h dérivé des coûts P4.9, charge
déclarée : deux agents en worktrees + sessions parallèles), runner `tools/evo_runs/s2_credit_ablation_2.py`
(cinq bras : gelé / complète importée sur réplication / TD seul / retour constant +1 / épisodique seul à 0,004) ;
les seams `episode_enabled` / `reward_const` vivent dans le runner (`credit_variant`, sous `count_learning_events`,
fichier en cours d'édition par b0) et sont vérifiés à réponse connue avant le run (`preflight_credit_seams_2` :
no-op EXACT contre la trace de P4.9, épisodique jamais appelé, constante seule reçue, pas lu sur l'optimiseur) ;
verdict calibré 16 cas ; temps CPU publié à côté du temps mur (P2.78, côté runner). Pré-vol (32 ticks) : Σ|ΔW|
complet 186, TD seul 100, constante 25, épisodique 0,004 → 20. Résultat → record `EDR-S2-CREDIT-ABLATION-2`
(results/s2_credit_ablation_2.json, committé avec le record). À replier ensuite : les deux seams dans
`count_learning_events` quand `tools/learning_events.py` sera libre.
Quoi (design initial) : même dispositif (bassin DAgger cloné ×12, phase immortelle 2000 ticks, test mortel 200 ticks poids gelés,
n = 12, mêmes seeds, `a_frozen` re-mesuré, `b_full` importé sur réplication bit-identique), trois bras sur le
crédit : (b_tdonly) épisodique COUPÉ, TD seul — seam `episode_enabled=False` à AJOUTER à `count_learning_events`
et à calibrer à réponse connue (learn_episode d'origine jamais appelé, TD vivant) ; (b_const) retour CONSTANT +1
partout — seam `reward_const` à ajouter (signal non nul, contenu nul : si ça érode, c'est la dérive de politique
de REINFORCE, indépendante du contenu) ; (b_ep_lr) épisodique seul à `lr` 0,004 (dose de mouvement de
`b_tdoff`, 10× moins). Issues nommées d'avance : b_const ERODE → le destructeur est l'opérateur épisodique
lui-même → remède candidat = ANCRE au bassin (perte d'imitation / KL vers la politique DAgger pendant le crédit,
forme DAgger + RL) à sceller ensuite ; b_const NEUTRE → le contenu compte (magnitude / variance du retour) →
cible = normalisation du retour ; b_tdonly ERODE → le TD par tick suffit AUSSI (deux destructeurs) ; b_tdonly
NEUTRE → un seul destructeur, `learn_episode` (`gate_last_only=True` : ce qu'il déplace devient la question).
Pré-vol : les deux nouveaux seams à réponse connue (ce qui ATTEINT le learner d'origine, comme P4.9). Coût
mesuré P4.9 (charge connue) : 26-713 s par bras-seed → ~1-3 h ; sceller le budget sur MESURE ; publier le temps
CPU à côté du temps mur (P2.78). Pourquoi : [[EDR-S2-CREDIT-ABLATION]]. *Coût : agent 2-3 h ; calcul 1-3 h
sous bail.* Dépend de : P2.78 (souhaitable, non bloquant).
<!-- closes_when:path_present=docs/preregistrations/S2-CREDIT-ABLATION-2.json -->
**P4.18 — rang 4 quinquies (PROCHAIN RUN, bon marché) — Contrôle de FRAGILITÉ du bassin : une perturbation ALÉATOIRE
de W appariée en mouvement érode-t-elle autant que le crédit ?**
Quoi : même dispositif de test (bassin DAgger cloné ×12, phase 2 MORTELLE 200 ticks à poids gelés, n = 12, mêmes seeds,
`a_frozen` re-mesuré), mais SANS phase d'apprentissage : W est perturbé par un bruit gaussien de direction aléatoire,
normalisé pour que `Σ|ΔW|` égale la médiane mesurée d'un bras de P4.16/P4.9 — quatre niveaux appariés : 5 % (retour
constant), 6 % (épisodique 0,004), 71 % (TD seul), 100 % (complet) — plus un bras à `Σ|ΔW|` = 2,5 % (P4.9 sans signal :
n'érodait pas). Aucune simulation d'apprentissage : quelques secondes par cellule (phase 2 seule), ~15 min de run.
Issues nommées d'avance : le bruit apparié érode AUTANT que le bras de crédit de même mouvement → le bassin est une
CRÊTE fragile à toute perturbation, le crédit n'est pas spécial, un remède d'ANCRAGE (P4.19) ne répond pas à la
question ; le bruit n'érode PAS (ou bien moins) à mouvement égal → la DIRECTION des pas du crédit est le destructeur,
et l'ancre au bassin (imitation / KL vers la politique DAgger pendant le crédit, forme DAgger + RL) devient le remède à
sceller. Pré-vol : no-op exact à bruit nul (S = `S_a` au bit près) ; l'appariement en `Σ|ΔW|` vérifié à 1 % ; la
direction tirée d'un rng dédié publié. Règle à sceller `S2-BASSIN-FRAGILITY` : classement de chaque niveau contre
`S_a` (signe 10/12, ±5), et lecture par COMPARAISON appariée niveau-à-bras (bruit − crédit, 10/12, ±5) → FRAGILE /
DIRECTION / MIXTE. Pourquoi : [[EDR-S2-CREDIT-ABLATION-2]] § Portée. *Coût : agent 2 h ; calcul ~15 min sous bail.*
Dépend de : rien.
<!-- closes_when:path_present=docs/preregistrations/S2-BASSIN-FRAGILITY.json -->

**P4.17 — rang 4 quinquies — ✅ CLOSE le 2026-09-24 (verdict `AIDE_A_UN_POINT` ; ouverte le 2026-09-22, décision robla déléguée via agagi-52 ; session loop 766eabae) — Balayage
lr × λ sur le pilote TD PAR PAS : où la trace d'éligibilité vit-elle, et jusqu'où descend-elle en lr ? Le billet à deux issues de
la ligne `eligibility_trace_credit` (ADR-005) se joue ici, PAS in-world (P4.16-bis refusé : 0,0033/agent in-world = 75× sous le
seul point où la trace ait jamais marché).**
Motivation : R0 (`TD-STEP-PILOT-R0`, EDR-TD-STEP-PILOT-R0) — à lr 4,0 (0,25/agent), λ 0,9 déplace de +0,063, 12/12, séparation
totale ; R1 (`TD-STEP-PILOT-R1`) — rien à lr 2,0 (0/12), λ 0,5 sous la marge (0/12) : un effet à UN point n'est pas une pièce.
Quoi : règle `TD-STEP-PILOT-R2` scellée le 2026-09-22 (`docs/preregistrations/TD-STEP-PILOT-R2.json`), R0/R1 déclarés (E11) :
grille lr {4,0 ; 2,0 ; 1,0} × λ {0 ; 0,5 ; 0,9 ; 0,99} + contrôle CHEMIN `td0_d0` à chaque lr + références lr = 0 (D=1, D=0),
12 seeds, 3000 épisodes, substrat bilinéaire ; 96 cellules IMPORTÉES de R0/R1 (mêmes seeds, même code, sceaux vérifiés, relues à
chaque appel), 108 neuves. Écarts déclarés au design proposé : lr 0,5 ÉCARTÉ (R1 a déjà rendu 0/12 à 0,125/agent ; « jusqu'où »
est répondu par 1,0 si 1,0 est nul ; 60 cellules), lr 8,0 aussi (R0 : contrôles inertes). Branches, ordre imposé : INCOMPLET ;
CONTROLE_CHEMIN_ECHOUE (aucun lr lisible) ; AIDE_INVARIANTE (λ 0,9 > λ 0 + 0,05 sur ≥ 11/12 à DEUX lr lisibles ADJACENTS) ;
AIDE_A_UN_POINT ; PAS_D_AIDE — aide05 / aide099 publiés (dose en λ) hors verdict. Garde E13 : unité MESURÉE sur la première
cellule neuve, `project_cost(budget 14 400 s, marge 1,5)`, coupe des lr BAS d'abord, publiée. Runner : `tools/td_step_pilot.py --r2`
(reprenable, `_cout_s` ET `_cout_cpu_s`), 5 cas de lecture (`tests/sandbox/test_td_step_pilot.py`, 22 verts).
**État** : run n°1 lancé à 21:50 EN PARALLÈLE du run kuzu de d7 — première cellule neuve **217 s** contre 75-90 s pour la même cellule en R0 (contention machine, pas coût de la cellule) ; la garde a projeté 34 800 s > budget
et COUPÉ lr 1.0 puis lr 2.0 (96 cellules, publiées dans `_regime.coupe`), projection restante 3588 s ; les 11 cellules λ 0,99 à lr 4,0 tournent à 74-97 s (l'unité mesurée était un transitoire). Décision
déclarée : REPRISE `--relever-coupe` dès que la machine est libre — rien d'effacé, historique des coupes conservé
(`_regime.coupes_precedentes`), unité RE-MESURÉE sur la première cellule coupée, MÊME budget scellé ; relever la marge aurait été le
mauvais correctif (E12 sur le coût : une unité mesurée pendant qu'un autre job tourne n'est pas une unité — même classe que la
mesure « 8 h 30 pendant que seize agents tournaient »). Pas en parallèle de S2-002-PAIRED-R1 (les deux veulent une machine libre).
**Se ferme** avec le record `EDR-TD-STEP-PILOT-R2` (verdict lu dans `results/td_step_pilot_r2.json`, committé avec ses artefacts) —
clause ancrée, vérifiable sur un clone.
⚠️ Clause RÉ-ANCRÉE le 2026-09-24 (revue d'agagi-52, classe **E1**) : elle visait la ligne « ✅ CLOSE » de CETTE entrée, donc elle grepait sa propre décision d'auteur et ne pouvait structurellement rien constater. Elle vise désormais la SORTIE que l'entrée se donne — le record `EDR-TD-STEP-PILOT-R2`, qui n'existe pas encore : un verdict qui ne vit que dans `results/td_step_pilot_r2.json` n'est pas un record.
**REPRISE FAITE le 2026-09-24, et elle REFUTE la cause supposee.** `--relever-coupe` relance sur machine LIBRE
(0 bail, 0 processus python du projet, verifie au depart) : l'unite RE-MESUREE vaut **196,4 s**, contre 217 s
sous la contention du 2026-09-22 — **10 % d'ecart, pas un facteur 2**. La ligne lr 1.0 est donc RE-COUPEE, et
cette fois sans aucune charge a incriminer : `95 unites x 196,4 s x marge 1,5 = 466 min > budget 240 min`. Ce que
j'avais attribue a la contention etait une **sous-estimation au SCELLEMENT** : la grille, telle que scellee, ne
tient pas dans son budget, et les cellules de la ligne lr 4,0 qui tournaient a 74-97 s n'etaient pas
representatives des cellules neuves. Le protocole a fonctionne exactement comme ecrit (reprise declaree, unite
re-mesuree machine libre, MEME budget scelle, marge jamais relevee) et il rend un verdict que je n'attendais
pas. Consequence pour le record `EDR-TD-STEP-PILOT-R2` : il publiera la ligne lr 1.0 comme NON MESUREE, avec sa
raison chiffree, et non comme un accident de machine.
**✅ CLOSE le 2026-09-24 — lecture scellée `AIDE_A_UN_POINT`** ([[EDR-TD-STEP-PILOT-R2]],
`results/td_step_pilot_r2.json`, 96 cellules importées + 48 neuves). Ce que la grille ajoute à R0, et c'est le
résultat : **à lr 4,0 la trace n'est pas un bonus, elle est CE QUI REND la tâche différée apprenable** — λ 0,9
(médiane 0,2531) et λ 0,99 (0,2563) franchissent la barre de leur propre référence lr = 0 (0,1625 + 0,05) sur
**11/12 seeds**, quand λ 0 (0,1898) la franchit sur 1/12 et λ 0,5 (0,2078) sur 3/12. Comptes scellés :
`aide09@lr` 12/12, `aide099@lr` 11/12, `aide05@lr` 0/12.
⚠️ **Au pas moitié (lr 2,0), AUCUN bras à délai n'apprend** — `lam0` 1/12, `lam05` 0/12, `lam09` 1/12,
`lam099` 2/12 au-dessus de la barre — donc le `0/12` d'aide y oppose deux bras qui n'apprennent ni l'un ni
l'autre, et il ne réfute PAS l'invariance au pas : elle reste OUVERTE. La règle mesure `lisible@lr` sur la
paire SANS délai (`td0_d0` 0,3203 contre 0,168, 12/12), l'aide sur la paire AVEC délai ; le record publie les
deux côte à côte pour que le glissement soit impossible. Le balayage utile est donc vers le HAUT, pas vers le
bas. (Tension nommée par agagi-52 AVANT la lecture ; sa clôture de P4.11 est amendée en conséquence.)
**Complément à ma note de reprise ci-dessus, qui était partielle.** Chiffré exactement : à 107 unités, budget
240 min, marge 1,5 — unité contaminée 217,4 s → 255 min restants après la coupe de lr 1,0, donc une SECONDE
coupe ; unité libre 196,4 s → 231 min, donc une seule. **La contention a coûté EXACTEMENT une ligne (les 48
cellules de lr 2,0, que la reprise a récupérées), et seulement parce que la projection était déjà à 6 % du
seuil** ; la coupe de lr 1,0, elle, tient machine libre : elle est STRUCTURELLE. Les deux portent pourtant le
même `coupe=True` dans le JSON — d'où la dette ci-dessous.
⚠️ **Et la prémisse de coût que j'avais SCELLÉE est fausse** : la règle justifie sa projection par « cellules
uniformes : mêmes épisodes, mêmes agents ». Mesuré sur les 28 cellules chronométrées : `lam05` 161,9 s,
`lam099` 157,6 s, `td0_d0` **56,2 s** — le contrôle de chemin est **2,8× plus rapide**. L'unité est mesurée sur
la PREMIÈRE cellule neuve (famille lente) et appliquée à une grille hétérogène : la projection sur-estime, et
le cliquet de coût mord plus qu'il ne devrait. C'est E8 appliqué au modèle de coût. *(Ne change pas la coupe de
lr 1,0, qui tient même à l'unité médiane toutes familles.)* **Ces dettes sont SORTIES en [[P2.110]]** le 2026-09-24 (avec une troisième, trouvée en les ré-écrivant) :
une entrée fermée ne porte pas de travail à faire — personne ne va chercher un « à faire » sous un coché vert.
<!-- closes_when:path_present=docs/EDR/TD-STEP-PILOT-R2_The_Eligibility_Trace_Is_What_Makes_The_Delayed_Task_Learnable_At_One_Operating_Point.md -->

**P4.7 — rang 19 — S5 / G4 phase A : `g` PER-ACTION vs agnostique vs labels PERMUTÉS (nœud 74).**
Sonde livrée (fix de persistance ACTIF depuis le 2026-09-07, voir le bloc S5 plus bas et
`docs/SDR/G4_agent_anticipates.md`). Rang bas parce que G4 in-world est dormant tant que le sujet est
le champion prod ; à relancer sur le sujet issu de P4.4. *Coût : agent ~2 h ; calcul ~1 h.*
<!-- closes_when:path_present=docs/preregistrations/S5-G4-PHASE-A.json -->

**Rang 20 — amendement de P2.42 (2026-09-14)** : le `-bis` de S2-BLIND se fait à CORPS APPARIÉ (ballast
P1.7) et apprenant GELÉ, pour lire ou rétracter la DV 7/7 (+39 %). Voir l'annotation sous l'entrée
P2.42. Dépend de : P1.7.

**P2.96 — Le split `control` du harnais n'est JAMAIS entraîné : la garde d'alias est structurellement aveugle.**
Mesuré par [[EDR-HARNESS-R1]] (cellule B, `INCONCLUSIVE_ALIAS`) : `run_harness_cell` entraîne l'instance
uniquement sur le split `"train"` (`tools/harness/cell.py:121-127`) puis évalue le contrôle sur CETTE instance
(`tools/harness/cell.py:146-148`), alors que le split existe (`tools/harness/tasks/composition.py:53-56`). La
politique apprend à lire `key` au pas 0 dans son état et jamais au pas 1 : réinitialiser l'état tue aussi la tâche
de contrôle (0,9078 → 0,1781, `leakage` 0,7297) et `alias_guard_verdict` rend `FUNCTIONAL_LEAK` PAR CONSTRUCTION.
Un contrôle non entraîné ne peut pas séparer « l'état est nécessaire » de « ce slot n'est jamais lu ». Quoi :
entraîner en ALTERNANCE sur `train` et `control` dès qu'une ablation `site="state"` est déclarée (précédent
exécutable : `tools/language_memory_demand_probe.py::_train_and_eval`, paramètre `train_control=True`), la dose du
contrôle publiée à part ; OU faire porter au contrat de tâche l'exigence que le contrôle soit résoluble par la
politique entraînée sur `train` seul, et REFUSER en tête sinon. Prérequis de toute cellule à ablation d'état (donc
de la re-mesure de B en R2). Coût ≈ 2 h + un run de cellule.
<!-- closes_when:grep_present=tools/harness/cell.py::train_control -->

**P2.97 — La garde E19 ne distingue pas un écart nul par PLAFOND d'un écart nul par effondrement.**
Mesuré par [[EDR-HARNESS-R1]] (cellule A′, `LR_ARTIFACT`) : `_e19` (`src/seed_ai/harness_verdict.py:288-330`)
protège par `reference_floor` contre une référence qui s'effondre vers le plancher, mais deux bras SATURÉS au
plafond au même pas du balayage donnent `gap = 0` — donc `closure = 1,0` et `LR_ARTIFACT` — alors qu'aucun des
deux n'a échoué. Sur une tâche facile (rappel `same_tick`, 150 épisodes, les deux bras à 1,000 à lr 0,02), la
garde mêle saturation et vitesse d'apprentissage. Quoi : ajouter au calcul un plafond symétrique du
`reference_floor` (si les DEUX bras dépassent `ceiling - 2 se` à un pas, ce pas ne porte pas d'information sur la
nécessité : statut `GAP_AT_CEILING`, publié, pas `LR_ARTIFACT`), avec son contre-exemple gelé ; et, côté
protocole, sceller une cellule facile avec un régime qui ne sature pas au pas le plus rapide (le smoke doit
mesurer les DEUX pas, pas un seul — c'est ce qui a manqué à A′). Coût ≈ 3 h, zéro run.
<!-- closes_when:grep_present=src/seed_ai/harness_verdict.py::GAP_AT_CEILING -->

**P2.98 — `check_preregistration_applied.py` PLANTE (AttributeError) sur un `.json` de `docs/preregistrations/`
dont `rule` n'est pas un dict.** Mesuré en écrivant [[EDR-HARNESS-R1]] : `payload.get("rule", {}).get(...)`
(`tools/check_preregistration_applied.py:105-106`, `:154`, `:217`) suppose un dict ; un fichier de provenance dont
`rule` est une chaîne fait tomber la porte 5 en exception au lieu d'un refus propre — c'est pourquoi la provenance
de `-bis` est tamponnée sur le SMOKE (`tools/harness/seal_r1.py:30-37`) plutôt que déposée là. Une porte qui
plante ne dit pas « non », elle ne dit rien. Quoi : ignorer proprement (avec un message nommant le fichier) tout
payload dont `rule` n'est pas un dict, et un cas de calibration qui pose un tel fichier dans un `_dir` temporaire.
Coût ≈ 30 min.
<!-- closes_when:grep_present=tests/sandbox/test_preregistration_guard.py::rule_non_dict -->

**P2.99 — `assert_verdict_invariant_to_optimizer` ne surveille que l'effondrement ABSOLU de la référence, pas sa
dégradation relative.** `tools/experiment_preflight.py:303-372` : `reference_floor` est un plancher bas (ici la
barre d'acquisition, ~0,19-0,22) ; une référence qui passe de 1,00 à 0,70 — dégradation massive, toujours très
au-dessus du plancher — ne déclenche rien, et la closure attribue au PAS ce qui vient du bras de référence.
Trouvée en revue de [[EDR-HARNESS-R1]] (héritage P2.21). Quoi : publier `refs_by_lr` dans le retour de la garde
(aujourd'hui elle ne rend que `True`) et refuser, ou marquer `INDETERMINE_REFERENCE_MOVED`, quand la référence
varie de plus d'un seuil DÉCLARÉ entre les deux pas ; contre-exemple gelé des deux côtés. Coût ≈ 1 h.
<!-- closes_when:grep_present=tools/experiment_preflight.py::INDETERMINE_REFERENCE_MOVED -->

**P2.100 — Le bloc `regime` publié par une cellule est RECOPIÉ des arguments du runner, jamais re-dérivé d'un
comptage.** `tools/harness/cell.py:238-245` construit `regime` depuis `task.regime()` et les kwargs reçus
(`episodes`, `n_agents`, `eval_batches`) : rien ne prouve que le nombre d'épisodes réellement exécutés est celui
publié — c'est la forme E8 (« une prémisse est une mesure, pas un décor ») appliquée au régime du harnais, et le
sceau lui-même ne peut pas la rattraper puisque le runner prend ces valeurs en arguments. Quoi : compter les
itérations dans `_run_arm` (épisodes d'entraînement, lots d'évaluation) et publier `regime_mesure` à côté de
`regime`, avec une assertion d'égalité ; le record cite `regime_mesure`. Coût ≈ 1 h.
<!-- closes_when:grep_present=tools/harness/cell.py::regime_mesure -->

**P2.102 — La garde d'alias de la condition (iii) (« la pièce est-elle tout le learner ? ») n'a jamais été
appliquée à la PIÈCE, seulement à l'état.** Le spec (`docs/superpowers/specs/2026-09-16-harness-contracts-
design.md:293-296`) prévoit `alias_guard_verdict(ctrl_A, ctrl_D)` : la tâche de CONTRÔLE doit survivre au
retrait de la pièce, sinon la « pièce » ablatée est en réalité tout le learner. Mesuré ([[EDR-HARNESS-R1]] §7,
revue finale de branche C1) : le bloc `necessity` des trois cellules n'a AUCUNE clé `alias` (la cellule B en
porte une, mais pour l'ablation D'ÉTAT `state_reset` de la DEMANDE, jamais pour la nécessité de la pièce) ;
`tools/harness/cell.py:146-148` n'évalue les contrôles que sur le bras A (AVEC la pièce), jamais sur D (sans
elle). Non posée pour A (`without={"bilinear": false}`) ni pour B (`without={"feedforward": true}`, une
lésion LARGE) : `PIECE_PARTIAL` (A) et `NECESSARY` (B, non décisif) pourraient, sans cette garde, documenter
une pièce qui n'est en réalité qu'un nom pour « le learner entier ». Quoi : un bras de contrôle par cellule à
ablation de pièce (construit et évalué SANS la pièce, comme D, symétrique du contrôle déjà présent pour les
ablations d'état), confronté par `alias_guard_verdict` — coût d'un bras de contrôle par cellule (R2). Coût ≈
2 h + un run de cellule.
**FUSION 2026-09-25 (PM, `feat/harness-r1` ⟂ plan 2) : le scelleur du harnais est sous le contrat revue-avant-sceau.**
`tools/preregister.py` (plan 2, 2026-09-23) refuse toute NOUVELLE règle qui déclare un coût sans `reviewed_by`
(`ReviewRequired`) ; `tools/harness/seal_r1.py::main` scelle `HARNESS-R1-ter` sans le passer — `-bis` existant n'est
pas touché (ré-écriture identique, retour avant la garde), mais `-ter` ne pourra pas être scellé tant que `main`
n'accepte pas `--reviewed-by` ET qu'une revue de R1 n'existe pas (P2.95 : HARNESS-R1 est gelé SANS revue). Mesuré à la
fusion : 14 erreurs + 1 échec dans `test_harness_cell.py` / `test_harness_seal_r1.py`, dont les fixtures scellent des
règles jouets à coût — adaptées avec un chemin de FORME (`_REVUE_FIXTURE`), jamais une revue prétendue.
<!-- closes_when:grep_present=tools/harness/cell.py::alias_guard_verdict -->

**P2.103 — Cinq dettes mineures du harnais, chacune avec sa preuve (regroupées : aucune ne vaut une entrée
seule).** ⚠️ Renumérotée de P2.101 en P2.103 le 2026-09-24 (collision de numéro mesurée avec
`feat/d1-prod-pairing`, qui porte un P2.101 sans rapport — « La PERTE DE NOMMAGE », depuis b2736a49 ; voir
`.superpowers/sdd/2026-09-16-harness-r1-weeks-1-3/merge-preflight.md` §6). Contenu inchangé sauf l'item (d),
corrigé par la revue finale de branche (C2) sur un fait FAUX de l'artefact.
(a) Le bris d'égalité du second `lr` choisit le pas le plus PROCHE de `sweep0_lr` (`tools/harness/seal_r1.py:148`),
donc la sonde E19 la plus faible, là où le plus ÉLOIGNÉ discriminerait mieux — déclarer le critère dans le sceau.
(b) `ConnectomeLearner.build` valide `obs_dim` et `K` mais jamais `n >= 1`
(`tools/harness/learners/connectome.py:194-199`) : `n=0` construit une instance vide au lieu d'un refus en tête.
(c) `TabularLearner.state_dict` omet `seen_cols` (`tools/harness/learners/tabular.py:103-104` vs `:31`, `:48-51`) :
un rechargement filtre tout jusqu'à ré-apprentissage. (d) Aucun bras `sham` n'a tourné en R1
(`src/seed_ai/harness_verdict.py:47`, `_ARMS`) : la nécessité de A publie `sham`=`DECLARED` (le registre
`PIECES["bilinear"].matched_sham` existe) — **PAS** `PARAMS_NON_APPARIES` comme l'affirmait cette entrée avant
correction (C2, revue finale de branche : le texte d'origine était FAUX sur l'artefact, `results/harness_r1_A_0.json`
porte `sham="DECLARED"`). `sham="DECLARED"` documente une entrée du registre, jamais une mesure : `sham_arm_run`
= `false` (constante, publiée à côté depuis C2, `src/seed_ai/harness_verdict.py::_necessity`) le dit désormais
explicitement. Courir réellement un sixième bras `sham` reste à faire (R2). (e) Le champ `cout` du sceau
`HARNESS-R1-ter` décrit le budget de `-bis` (« 81 min ») alors que son `budget_family_s` vaut 14 534 s = 242 min
(`docs/preregistrations/HARNESS-R1-ter.json`) : `build_rule_r1_ter` (`tools/harness/seal_r1.py:278-309`) hérite
`cout` au lieu de le DÉRIVER — le sceau est immuable et reste reproductible, mais un futur `-quater` doit dériver
le texte des budgets qu'il vient de changer (classe E8 ; commentaire déjà posé dans la fonction).
<!-- closes_when:grep_present=tools/harness/learners/connectome.py::n < 1 -->

**P2.104 — Aucune porte ne tourne à la FUSION : les 19 cliquets sont contournés par tout commit de fusion.**
Mesuré le 2026-09-24 : `core.hooksPath` vaut `.git/hooks` et les seuls hooks installés y sont `pre-commit` et
`post-commit` (tous les autres sont des `.sample`). Il n'existe ni `pre-merge-commit`, ni `commit-msg`, ni
`prepare-commit-msg` : un `git merge` qui crée un commit de fusion ne déclenche AUCUNE des 19 portes.
Conséquences mesurées sur la fusion de `feat/harness-r1` : (a) la collision de numéros P2.101 ci-dessus
(P2.103) serait passée en silence, la clé « numero-double » de `check_backlog_freshness` ne s'exécutant pas
sur une fusion ; (b) un compteur de comptage sur une ligne partagée (ex. `SCIENCE.md` records_total) en
CONFLIT GIT choisit naïvement un camp au lieu de RECALCULER, publiant un compte faux ; (c) deux compteurs sur
des plages de lignes DISJOINTES fusionnent par prise silencieuse, sans le moindre conflit pour signaler qu'un
compteur doit être recomputé. C'est la classe E10 (« une règle documentée sans application exécutable est
violée ») appliquée au hook lui-même, et la forme est celle de E4 : le journal de bord de cette branche
croyait la parade armée à la fusion. Quoi : installer un hook `pre-merge-commit` qui lance au moins les
portes de COMPTE et de DOUBLON (`check_synthesis_counts`, `check_backlog_freshness`, `check_test_census`,
`check_record_links`), avec son contre-exemple gelé ; décision à prendre avec robla car le hook est partagé
entre toutes les sessions et un refus au mauvais moment bloque la fusion de n'importe qui. Preuve
reproductible : `ls .git/hooks | grep -v sample`. Coût ≈ 1 h + un tour de test de mutation.
⚠️ Pas de clause `closes_when` : le fichier cible (`tools/hooks/pre-merge-commit`) n'existe pas encore —
`check_backlog_freshness` refuse un chemin cité qui n'existe pas (« invérifiable »), et une clause qui
pointe vers un fichier absent serait exactement le mensonge que la garde existe pour attraper. À poser
UNE FOIS le hook créé.

**P2.106 — La forme E30 est ATTEIGNABLE dans le verdict du harnais : la marge 0,05 vaut un nombre
ENTIER de pas de grille, sur les accuracies COMME sur les médianes.**
Mesuré le 2026-09-24 en recomptant les trois cellules de [[EDR-HARNESS-R1]] en arithmétique exacte
(Fraction), après l'ouverture de la classe E30 par une session voisine sur un autre runner (P2.105).
Le régime publié donne N = `eval_batches` × `n_agents` = 40 × 16 = **640** évaluations, donc une
accuracy est un compte k/640 — vérifié : chaque valeur publiée est k/640 arrondi en float32, pire
écart **1,526e-05** pas. Or la marge du harnais vaut **0,05 × 640 = 32 pas EXACTEMENT** sur cette
grille, et **0,05 × 1280 = 64 pas exactement** sur celle des médianes (une médiane de 12 valeurs est
un demi-entier sur 640). Les quatre comparaisons que le module fait réellement sont donc toutes
exposées à une égalité exacte, que la représentation flottante tranche alors arbitrairement :
`src/seed_ai/harness_verdict.py:254` (compte par seed A contre A0, PUBLIÉ en `per_seed_above_ref`),
`:451` (idem A2 contre A0), `:319` (`med_D <= ref + min_sep`, qui DÉCIDE `NECESSARY`) et `:349`
(`without_clears_bar`, PUBLIÉ).
**État : LATENTE dans R1, et c'est mesuré, pas supposé.** Sur les quatre comparaisons réelles des
trois cellules, l'arithmétique exacte et le flottant concordent PARTOUT, zéro égalité : marges les
plus serrées +66 pas (cellule A, `med(D)` au-dessus de la barre) et −59 pas (cellule B). Aucun
chiffre publié n'est à re-graver. ⚠️ Une égalité exacte EXISTE bien dans les données (cellule B,
D2 seed 5 : 126/640 contre une barre à 94/640 + 32 = 126/640) mais elle porte sur un contraste par
seed que le module ne calcule JAMAIS — j'avais d'abord conclu « un nombre publié a été changé »,
c'était faux, rectifié par relecture du code avant publication. La leçon de méthode est la même que
celle du grep : une sonde de vérification doit être confrontée à ce que le code fait, pas à ce qu'on
croit qu'il compare.
**Pourquoi ça ne peut pas rester une note** : la latence ne tient qu'aux valeurs de CE run. Il suffit
d'un `eval_batches` ou d'un `n_agents` différent, ou d'une cellule plus serrée, pour qu'une égalité
tombe sur une comparaison publiée — et rien ne le dirait, puisque le verdict sortirait normal.
**Quoi** : (a) comparer en arithmétique de GRILLE dans `_acquisition` et `_necessity` (compte entier
contre compte entier + pas), ou à défaut publier à côté de chaque compte la **marge minimale en pas
de grille** sur les seeds — c'est la discipline « tout ratio se publie avec son plancher de bruit » de
ce dépôt, appliquée au bruit de REPRÉSENTATION ; (b) publier N (le dénominateur) dans le bloc
`regime`, aujourd'hui seulement déductible de `eval_batches` × `n_agents` ; (c) une garde qui REFUSE,
ou au minimum SIGNALE dans le JSON, toute comparaison dont la marge est nulle en pas de grille, avec
son contre-exemple gelé (la cellule B seed 5 le fournit tout fait, en le portant sur une comparaison
réelle). Coût ≈ 2 h, zéro run.
<!-- closes_when:grep_present=src/seed_ai/harness_verdict.py::pas_de_grille -->

### Décisions tranchées le 2026-09-14 (robla : « ce qu'il y a de mieux pour l'avenir »)

- **P1.1 → FERMÉE** : `pytest-timeout` est installé et imposé par la CI (`.github/workflows/ci.yml`).
- **`preserve_io_blocks=True` par défaut → OUI**, quand aucun run n'est en vol (P2.63).
- **P1.4 → ÉPINGLER** par un test maintenant, corriger après P4.4 (P2.64).
- **P2.27 (défaut bilinéaire divergent) → pas de défaut global** : chaque sonde DÉCLARE `bilinear=` et
  l'écrit dans `_params["substrate"]` (la porte 6 l'exige déjà).
- **Git** : les 18 commits sont poussés ; PR vers `main` APRÈS le record de P4.4, pas de protection de
  branche pour l'instant ; branches `chantier/factorial-regime-sweep` et `chantier/throw-gate-factorial`
  taguées `keep/...` ; worktrees PROPRES retirés (branches conservées) ; `reconcile` (MERGE_HEAD, 170 sales)
  et `wld-lifescore` (1 sale) conservés ; jamais `gc --prune=now`.
- **Pari B → mémoire / écriture** comme axe cognitif primaire des trois mois.

### Péremptions constatées EN PASSANT (annotées sur place, pas ré-écrites)

- **P2.44** se disait OUVERTE : ses 25 défauts sont corrigés depuis `d7557ec` (172 cas d'injection,
  zéro `xfail`) — fermée.
- **P1.x** (ex-« P1.x / P2.45 », CI à 6 %) est close par P2.54 — annotée ; depuis P3.5 (a) (2026-09-15) le titre
  composite n'échappe plus au cliquet des doublons, qui a révélé que P2.45 désignait DEUX entrées : renommée P1.x.
- **C2** (harnais EVO-011) : EVO-011 est FERMÉE par pré-vol (P2.39) — le « reste » est fait.
- **C4** (couche de lecture + M5) : M5 et T3 sont CLOS depuis le 2026-09-06/07.
- Les 13 rouges de la suite complète du 09-08 étaient tous dans `tests/` racine (hors CI d'alors), tous
  corrigés par P2.54.

---

## ✅ 2026-09-01 — DETTE DE CALIBRATION CLOSE (32 → 104/105, baseline à ZÉRO)

Le déficit que `CLAUDE.md` désignait comme **dominant** est refermé. 238 tests de calibration passent
(110 le matin même), la baseline du cliquet est **vide** — donc tout nouvel instrument non calibré
bloque le commit.

**⚠️ Le motif compte plus que le compte.** Sur ~40 instruments examinés, une trentaine de défauts
réels, et la direction est **CONSTANTE** : des données absentes ou incomplètes ne produisaient pas
« inconnu » mais une **affirmation NÉGATIVE de fond** — `PAS DE RUNG`, `MUR INTRINSÈQUE`, `AUTEL MORT`,
`N_EMERGE_PAS`, `SUBSTRAT BLOQUÉ`, `TOM_INERT`, `[1] SUBSTRAT-LIMITE`. Dans un dépôt dont la plupart des
résultats **sont** négatifs, un négatif fabriqué ressemble à tous les autres. **Ça n'invalide aucun
négatif publié — ça dit où regarder.**

**Ce qui reste OUVERT et qui est maintenant le meilleur candidat au titre de dette dominante :**

1. **Les 9 appels à `ablation_verdict` sans borne déclarée** (7 fichiers, section ci-dessous). Ils ne
   sont pas corrigeables « en code » : chacun demande de **MESURER le plancher no-capacité de son
   régime**, puis de le déclarer. C'est du travail expérimental, pas de la relecture — et ce sont les
   sondes qui alimentent les arêtes de l'AGI-Taxonomy.
2. **Le portail CI ne lance que 8 fichiers sur 207.** Le vert du gate ne dit presque rien, et rien de ce
   qui a été livré aujourd'hui n'y tourne.
3. **42 orphelins et 7 collisions** dans le graphe de records (dette légataire gelée).

**Deux techniques à réutiliser** (documentées dans `CLAUDE.md`) : la garde posée **en tête de fonction,
avant la construction du monde** (une vingtaine de cas passent à coût nul) ; et **l'injection** pour les
orchestrateurs — 13 des 24 « instruments de monde » ne simulaient pas eux-mêmes, et leur imposer une
dose CONNUE teste la couche qui transforme des mesures en affirmation.

---

## 🕳️ 2026-09-01 — LACUNES ET ANGLES MORTS recensés (balayage 6 lecteurs + critique de complétude)

> Consignés **en passant**, conformément à la règle de `CLAUDE.md` §« Consigner en PASSANT ». Chacun
> porte sa preuve ; aucun n'était l'objet de la tâche en cours. Non triés par valeur — par domaine.

### Dans la machinerie de calibration elle-même (le plus grave : l'outil qui compte se trompe)

* ✅ **RÉSORBÉE À 7/7 — DETTE CLOSE (2026-09-02)** : table `PLANCHER_NOPERC` mesurée sous bail (campagne `measure_noperc_floors`, constructions concordantes) et câblée avec régime-gate `_floor_for` (E8 : jamais un plancher d'un autre régime). *(État intermédiaire du jour : 5/7.)* — planchers MESURÉS et câblés (30.0 régime partagé, 54.0 composition par énumération, 34.0 world_demand_marker), avec bascule de la consommation sur `v["verdict"]` (sans quoi `floor=` était inerte). **Restent 2 fichiers** (`s2_demand_ablation`, `s2_openloop_probe`) : leur table `PLANCHER_NOPERC` exige une campagne SOUS BAIL kuzu (clones du champion, design prêt). **→ CAMPAGNE FAITE ET PRONOSTIC TRANCHÉ (2026-09-02, [[EDR-S2-013]], règle scellée `S2-FLOOR-PRONOSTIC`)** : soup intact 29,25 < plancher 32,0 → ligne soup ILLISIBLE (annotée sur S2-002) ; les 4 autres mondes tiennent au-dessus (+3,5 à +6,0), leurs DECOY désormais adossés à des bornes mesurées. Reste ouvert (petit) : apparier plancher et intact par SEED pour élever « champion < hasard à corps égal sur soup » au rang d'effet.
* ✅ **CLOS (2026-09-06, avec P2.28 — S2-FLOOR-PRONOSTIC est désormais confrontée à S2-013, 5/5 grandeurs présentes, aucune dette révélée)** — Gap (consigné en passant, 2026-09-02) : `check_preregistration_applied` appariait règle scellée ↔ record par PRÉFIXE DE NOM DE FICHIER seulement (`tools/check_preregistration_applied.py:71`) — la famille `S2-FLOOR-PRONOSTIC` n'est donc jamais confrontée à son record `S2-013_*` (nom différent). Couverture honnête affichée, mais l'appariement par mention du nom de la règle DANS le corps du record élargirait la vérification réelle. À faire avec son contre-exemple gelé (le scan élargi peut révéler de la dette réelle sur les règles existantes : la traiter, pas la baseliner).
  * **9 appels à `ablation_verdict` ne déclarent AUCUNE borne, dans 7 fichiers — classe E14 littérale.**
  La garde `_degeneracy` ne s'active que si l'appelant passe `floor=` / `ceiling=` (un plancher n'est
  pas déductible de deux tableaux). Elle est armée chez 7 appelants et **jamais rétro-appliquée** aux
  autres : `anticipation_demand_world_probe`, `cognitive_demand_world_probe`,
  `composition_demand_world_probe`, `memory_demand_world_probe`, `s2_demand_ablation`,
  `s2_openloop_probe` (×3), `world_demand_marker_probe`.
  ⚠️ Ce sont les sondes de DEMANDE in-world — celles qui produisent les `X_DEMANDED` alimentant les
  arêtes de l'AGI-Taxonomy. Un ratio non borné fabrique mécaniquement un `X_DECOY` quand un bras est
  collé à une borne ; c'est ce qui a produit « le paysage de fitness est PLAT » ([[EDR-WARM-002]],
  réfuté depuis par [[EDR-WARM-010]]).
  **Pourquoi ce n'est PAS corrigé ici** : un `floor` est une DÉCLARATION SCIENTIFIQUE
  (`PLANCHER_COG = 9.0` est « mesuré au régime cognitive_demand »). Inventer un plancher pour cinq
  régimes non mesurés fabriquerait le genre de chiffre que ce dépôt traque. **Ce qu'il faut** : mesurer
  le plancher no-capacité de chaque régime, puis le déclarer. Cliquet en place
  (`tests/sandbox/test_ablation_bounds_ratchet.py`) : dette gelée, tout NOUVEL appel non borné bloqué,
  et un test refuse que la dette reste gelée si elle est résorbée.
  *(Relevé par AST : le `grep` en manquait deux — leurs appels sont formatés autrement.)*

* **`ablation_verdict` : la garde de plancher est ASYMÉTRIQUE — elle laisse passer les FAUX POSITIFS.**
  Mesuré : `ablation_verdict([7.0]*12, [3.0]*12, floor=9.0)` rend **`X_DEMANDED`** avec
  `degenerate=True` et `why="bras intact au PLANCHER déclaré (médiane 7 <= floor 9)"`. La
  dégénérescence est **détectée, rapportée dans le dict, et non lue** par la branche `collapse` —
  exactement la forme de `sign_p` calculé puis jeté. Deux bras mourant à 7 et 3 ticks, tous deux sous
  le plancher de survivabilité, ne peuvent pas prouver qu'une capacité est exigée.
  Le commentaire du code montre l'origine de l'asymétrie : la garde a été armée contre le faux NÉGATIF
  de WARM-002 (« un bras intact au sol rendrait NEUTRAL »), et l'exemption « un positif censuré reste
  un positif, le ratio est une borne INF » — juste pour le PLAFOND — a été appliquée à **toutes** les
  raisons de dégénérescence, plancher compris.
  ⚠️ **Fichier d'une session parallèle en cours de travail** (elle traite ces branches une par une :
  `decoy`, puis `inverted` — commit « round 1 »). **Non modifié ici.** Documenté par un
  `xfail(strict=True)` dans `tests/sandbox/test_instrument_calibration.py`, qui échouera le jour de la
  correction pour forcer le retrait du marqueur.

* **La porte de calibration du hook BLOQUE les sessions les unes contre les autres.** Mesuré le
  2026-09-01 : un instrument NON SUIVI créé par une session parallèle
  (`run_delayed_coordination_demand_probe`) a bloqué un commit sans aucun rapport, parce que la porte 2
  scanne l'**arbre entier** dès qu'on touche un `.py` de `tools/` ou `src/seed_ai/`. Le comportement est
  délibéré (« bloque tout commit qui touche du code d'instrument tant qu'un NOUVEL instrument non
  calibré existe dans l'arbre ») — mais l'arbre est **partagé entre sessions**, et la porte sœur
  (graphe de records) a déjà résolu exactement ça avec `--only` sur les fichiers **indexés**.
  ⚠️ Ni contourner (`--no-verify`), ni geler la dette d'autrui (`--update-baseline` déclarerait
  « légataire » un instrument né il y a une heure, et le laisserait passer en silence). **Piste** :
  ne compter comme NOUVEAU que ce qui est indexé, tout en continuant à rapporter l'état de l'arbre.

* ✅ **RÉSOLU (2026-09-01)** — déclaration nue refusée ET le refus est désormais CRIÉ.
  * **Collision de noms — 8 instruments réels INVISIBLES.** `tools/check_instrument_calibration.py:82`
  indexe par `name` seul (`found.setdefault(name, ...)`). Deux fonctions homonymes dans deux fichiers
  n'en font qu'une : déclarer l'une calibrée **verdirait l'autre, jamais testée**. Clé à passer en
  `(chemin, nom)`, et `CALIBRATED` à indexer `"fichier::fonction"`. **À faire AVANT de continuer à
  calibrer** — sinon le compteur monte sans que la couverture monte.
* **Le registre `CALIBRATED` vit dans UN fichier codé en dur** (`_CALIB_TESTS`, ligne 35). Dans un arbre
  partagé entre sessions parallèles, ça garantit les conflits : toute calibration, quel que soit son
  domaine, doit toucher le même fichier. Piste : accepter des déclarations depuis plusieurs fichiers.
* ✅ **RÉSOLU (2026-09-01)** — l'appelant lui passe `s2_degeneracy` ; sa levée sur entrée vide est gelée.
  * **`verdict_from_survival_cmps` ne PEUT PAS s'auto-garder.** Il reçoit des comparaisons déjà calculées
  (`{p, cliff, ratio}`) et non les distributions : la garde de dégénérescence armée sur `s2_verdict`
  (2026-09-01) ne peut pas s'y étendre sans changer son contrat. Il faut que l'appelant lui PASSE le
  résultat de `s2_degeneracy`. Tant que ce n'est pas fait, il existe un chemin non gardé vers le verdict.
* ✅ **RÉSOLU (2026-09-02)** — le cliquet dit sa couverture RÉELLE (9/23), nomme les 13 légataires pré-convention non inspectables, et REFUSE toute règle nouvelle sans grandeur backtickée.
  * **`check_preregistration_applied.py` n'inspecte que 6 règles scellées sur 23** et ignore le champ
  `instruments_autorises` — celui que la clôture d'E11 avait inventé. Le cliquet couvre moins que ce que
  son nom promet (classe E4).
* ✅ **RÉSOLU (rétro-appliqué le 2026-09-02, statué le 2026-09-06)** — les 29 candidats d'alors ont été examinés à la MAIN : 0 à re-mesurer, 6 annotés (S2-009, S2-002, S2-005, DELAYED-COORD, EVO-024, INFRA-001), 8 déjà corrigés. Les DEUX risque-4 (portée=MONDE) : WARM-002 corrigé par [[EDR-WARM-010]] (bandeau + `corrected_by` en place, vérifié sur pièce le 2026-09-06) ; S2-009 corrigé par [[EDR-AUDIT-001]] (`corrects:` + 3 renvois dans le record) (son `within` publie des ratios sans absolus — défaut épinglé, pas un négatif fabriqué). Triage du 2026-09-06 : 66 examinés / 31 candidats — les 2 nouveaux (LANG-MEMORY-EDGE, LOCK-001) sont à portée instrument/synthèse, légitimes. *Candidat de cliquet (consigné) : tout NOUVEAU record au risque 4 portée=MONDE doit DÉCLARER son contrôle positif en frontmatter — pattern « faire déclarer l'auteur ».*
  * (historique) **`retro_audit_records.py` n'a jamais été rétro-appliqué** : `58 records examinés | 27 à EXAMINER
  (risque >= 2)`, dont EDR-S2-009 au risque maximal 4. La garde de la classe « garde jamais
  rétro-appliquée » est elle-même en attente de rétro-application. C'est E14 au carré.

### Dans le graphe de records

* ✅ **RÉSOLU (2026-09-01)** — 122 arêtes réintégrées (graphe 157 → 279), rétractations comprises ; détecteur de silence branché sur le cliquet.
  * **Le parseur IGNORE SILENCIEUSEMENT 101 arêtes déclarées — dont TOUTES les arêtes de rétractation**
  (`retracted_by`, `corrects`, `corrected_by`, `supersedes_mechanism`…). Un graphe de records qui ne
  lit pas ses rétractations ne peut pas signaler une conclusion périmée : c'est le défaut le plus grave
  de la liste.
* ✅ **RÉSOLU (2026-09-01)** — collision EDR-135 tranchée (anticipation → EDR-142) et arêtes `corrects`/`corrected_by` posées.
  * **Deux records `accepted` s'affirment le CONTRAIRE** sans rétractation ni renvoi : EDR-134
  (`InWorld_Torch_vs_Legacy_Inconclusive_Organs_Are_LoadBearing`) contre EDR-135 (`LegacyCore_Contr…`).
* ✅ **RÉSOLU (2026-09-01)** — frontmatter ajouté, le nœud existe.
  * **`docs/REF/REF-AGI-TAXONOMY.md` n'a AUCUN frontmatter** → le nœud n'existe pas dans le graphe et
  **3 liens `adopts` pointent dans le vide**. La collision EDR-135 **détourne** en plus l'arête de la
  porte G4 (`docs/SDR/G4_agent_anticipates.md:7`), et le validateur affiche `problèmes=0`.
* **Canonicalisation EDR 126/129/130 ↔ 155/156/157 : dette CONFIRMÉE et résoluble sans AUCUNE perte** —
  `diff --strip-trailing-cr` des 3 paires : seules les lignes d'`id` et les renvois diffèrent.
* **16 des 42 orphelins tombent en DEUX éditions** (vérifié par simulation) — dé-orphanisation bon marché.

### Dans la suite de tests (le vert qui ne veut rien dire)

* ✅ **RÉSOLU (2026-09-01)** — corrigés ; l'un cachait une régression d'API RÉELLE. Cliquet posé.
  * **`tests/test_fixes.py` : 5 tests AVALENT leur propre `AssertionError` et passent VERT**
  (`:29-33` — `assert` puis `except Exception: return False`). Un test qui ne peut pas échouer.
* ✅ **RÉSOLU (2026-09-02)** — job `garde-methodologique` ajouté (5 cliquets + 46 gardes, 16 s), et les déclencheurs couvrent enfin les branches de travail : les 43 commits de la veille n'avaient JAMAIS vu la CI.
  * **Le portail CI ne lance que 8 fichiers sur 207** (`.github/workflows/ci.yml:26-38`) : le vert du gate
  ne dit presque rien.
* ✅ **RÉSOLU / non reproduit (2026-09-01)** — 0 occurrence mesurée du motif `assert verdict in <co-domaine>`.
  * **~50 tests « smoke » assertent `verdict in <co-domaine COMPLET>`** — tautologie payée au prix d'une
  simulation (ex. `tools/disjoint_heads_v3.py:49-60`).
* ✅ **RÉSOLU (2026-09-02)** — 3 des 6 signalés étaient des faux positifs du scan (fixture, `np.testing.assert_*`, no-crash légitime documenté) ; les vrais corrigés, dont le no-op qui vérifie désormais l'état du RNG GLOBAL (classe E5).
  * **4 tests sans AUCUNE assertion**, dont 3 dont le NOM promet une propriété non vérifiée ; deux
  `assert True` décoratifs (`tests/sandbox/test_ntm_compiler.py:71-75`).
* **`tests/test_frontend_build.py`** : skip silencieux si npm absent, build non vérifié, dépasse le
  timeout global.

### Dans le registre d'erreurs

* ✅ **RÉSOLU (2026-09-02)** — E15 PROMUE (`assert_n_per_arm`, contre-exemple gelé aux chiffres d'EDR-095), E10 occ.4 reclassée `non automatisable` avec justification, occ.7 exécutable (garde de bail). Plus aucune occurrence en `documenté`.
  * **Le registre viole sa propre règle « pas de troisième fois »** : E10 compte **3** occurrences
  `documenté` (4, 5, 6) et sa cellule affirme encore « occurrence unique » ; E8 en a 2 et n'a jamais été
  statuée. La règle exige promotion en `exécutable` ou reclassement.
* ✅ **RÉSOLU (2026-09-02)** — voir ci-dessus.
  * **E15 est la seule classe dont la « garde » est une phrase adressée à un humain**, alors qu'elle est
  trivialement exécutable (vérifier `n` PAR BRAS avant de comparer des médianes).
* ✅ **RÉSOLU (2026-09-01)** — 4 fichiers de `tools/` l'invoquent désormais.
  * **E19 est calibrée dans les deux sens mais n'est appelée par AUCUN dispositif** ; seuls 3 outils sur
  183 importent le pré-vol. Une garde que rien n'invoque ne garde rien.

### En production

* **`PRESERVE_DIMS` par défaut à OFF** (`tools/map_elites_compare.py:38`) : le chemin d'aplatissement
  64/126 est atteignable PAR DÉFAUT et **échoue en SILENCE**. Même famille que la dette d'indices réglée
  ce jour — un défaut qui ne lève pas.

---

## 📌 2026-09-01 — état de session : dette réglée, D2 en vol, DEUX décisions en attente

**Réglé** — la dette de production d'indices ([[EDR-EVO-024]], commit `d4844fb`). Détail dans le bloc
suivant.

**⛔ [[EDR-EVO-026]] est NON LISIBLE, et le dit.** Son bras long a planté sur `LIMIT_N = 256`
(`src/agents/mamba_agent.py:405`) dès le premier seed : à 735 ères le génome passe de 172 à ~300 nœuds.
Le crash a révélé un défaut **plus grave que le plantage** — les arêtes possibles vont en **N²**
(29 584 à N=172, 65 536 à N=256), donc le bras long **accumulait des tirages tout en diluant chacun
d'eux ~2,2×**. La prédiction scellée `1−(1−p)²¹` suppose *p* constant ; l'appareil ne le tenait pas.
Un nul aurait été lu « modèle B confirmé » alors qu'une part venait de la dilution — **classe E2**, un
bras qui ne peut pas réussir. Le bras standard, lui, a TERMINÉ et vaut comme mesure : **0/12**, sal max
0.013, ~450 tirages/lignée.

**🔬 EVO-026-bis tourne** (~2 h) : croissance de nœuds **coupée dans les deux bras** → N constant à 172,
dénominateur fixe, plafond jamais atteint ; n porté à **24** par bras (la puissance manquait) ; base de
prédiction **poolée sur tout l'arc** (~2-3 lecteurs / ~130 lignées → p≈0.02) et non tirée d'un seul run ;
trois contrôles de manipulation mesurés **in situ** qui bloquent le verdict si l'un échoue. Contrôle
précoce validé : N=172 exactement, ~450 tirages/lignée.

**Deux DÉCISIONS en attente — elles ne sont pas des tâches :**
1. **Basculer `preserve_io_blocks=True` par défaut.** Le correctif est prêt, testé, validé neutre. Mais
   `src/seed_ai/mutation.py` est partagé avec une session parallèle : changer le comportement sous les
   pieds d'un run en vol est exactement la contamination que le bail `kuzu` interdit pour les mondes.
   → **DÉCIDÉ le 2026-09-14 : OUI**, quand le doctor rend 0 bail — tâche P2.63.
2. **Commit du travail D2** (préinscriptions EVO-026/-bis, runners, smoke de débit, backlog, registre).

**Deux occurrences ajoutées au registre**, trouvées en faisant et non en relisant :
* **E4 (forme SILENCIEUSE)** — un runner dérivé par regex a gardé le pré-vol d'EVO-023 tout en annonçant
  celui d'EVO-024 : il tournait, affichait un titre juste, et ne vérifiait **pas** ce qu'il prétendait.
  Les 4 dérivations ratées précédentes avaient échoué bruyamment ; celle-ci non.
* **E6 étendu aux CONTRÔLES** — un pré-vol appliquait 16 905 mutations cumulatives à un seul génome, un
  régime que le run ne visite jamais (`apply_mutations` CLONE). Un contrôle de manipulation doit
  s'exécuter dans le régime du dispositif, sinon il contrôle un proxy.

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
→ **DÉCIDÉ le 2026-09-14** (cf. P2.63).

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

**D1 — VOLUME × PRÉSERVATION DU FAN-IN : ✅ FAIT, c'est [[EDR-EVO-019]].** La cellule vide a été
remplie — verdict `ISOLATED_READER_NOT_ELEVATED_CLOSURE_HOLDS` : **un lecteur isolé à 1/12, NON élevé**,
la clôture tient. *(Cette entrée est restée listée « à faire » après coup ; corrigé le 2026-09-01.)*

**D2 — Horizon d'un autre ORDRE : ⚠️ NON CONCLUANT par DÉGRADATION ([[EDR-EVO-026]]).** Le dispositif
a tenu toutes ses promesses — **21,3× de tirages** (447 → 9 508 par lignée), dénominateur strictement
constant (N=172 des deux côtés), zéro extinction, zéro abandon, les **trois contrôles de manipulation
passent**. Et pourtant : **0/24 des deux côtés, Fisher p = 1.000**, non lisible.

**Pourquoi ce n'est PAS « modèle B confirmé »** : la santé de lignée du bras long s'effondre à **0,57×**
du standard (`age_fin` 7,0 → 4,0), sous le seuil de 0,70 posé dans le sceau. Le bras long ne pouvait pas
réussir — classe **E2**. La DV qui l'a attrapé avait été déclarée d'avance parce que le smoke de débit
montrait un coût par ère qui BAISSE, signe d'une lignée qui survit de moins en moins bien. **Sans elle,
ce record affirmerait aujourd'hui une conclusion fabriquée.**

**Fait acquis, contraignant pour toute suite** : dans ce substrat, un horizon long **dégrade** la lignée
même croissance coupée — ce sont `mutate_weights` et `prune` seuls qui érodent sur 735 ères. **On ne peut
pas accumuler des tirages en PROFONDEUR.**

**➡️ D2-bis : ⛔ ABANDONNÉ (2026-09-02, panel 3 juges + réfutateur — unanimité PROUVÉE).** La largeur à longueur fixe a une puissance discriminante **exactement nulle** : sous A comme sous B, N lignées indépendantes donnent `P(≥1) = 1−(1−p_lignée)^N` — la largeur mesure `p_lignée`, elle n'arbitre rien (information de Fisher A-contre-B nulle). Tout run en largeur est de la **calibration de base** (utile : la limite 0.005-vs-0.02 du sceau EVO-026-bis reste ouverte), jamais un arbitre. Deux designs de remplacement RÉFUTÉS sur pièce par le panel : la dose `add_connection_rate` a DÉJÀ couru ×10 (EVO-019/020, p=0.415, fan-in 0.64→10.05 = dilution mesurée) ; le bras ELITE confond sélection et fenêtre de composition. **La voie qui sépare : [[EDR-EVO-027]]** — forcer le tirage (biais EVO-009, seul levier ayant jamais déplacé le taux : 12/12, p=9.6e-6) et varier sa **POSITION** (fenêtre ères 1-15 vs 21-35, horizon post-fenêtre apparié). La clause discriminante : « la valeur d'un tirage réussi dépend-elle de l'historique accumulé ? » — A dit non, B dit oui. Règle scellée, coût ~13 min, contrôle positif INTERNE (le bras EARLY est le 12/12 d'EVO-009). **→ TRANCHÉ le 2026-09-02 ([[EDR-EVO-027]]) : MODÈLE A — la dépendance FORTE à la position est RÉFUTÉE** (EARLY 22/24 vs LATE 18/24, p=0,245, les 4 contrôles passent, santé 0,77). Un hit tardif convertit comme un hit précoce : « le verrou est le tirage » se relit **« le verrou est le NOMBRE de tirages »**, et l'échec d'EVO-019/020 reste attribué à la DILUTION. Observation non élevée : 6 porteurs-non-lecteurs LATE vs 2 EARLY — une dépendance FAIBLE reste possible, illisible à ce n (limite scellée). **Dette des DV mécanistes RÉSORBÉE le 2026-09-02** : |logit| extrait, corrigé (`H_prev` réel, échec bruyant) et calibré (`tools/evo_mech_dv.py`, 3 cas dont forme close) ; le runner persiste désormais chaque champion (`data/genomes/evo027/`). Tout replay livrera les deux DV. **→ PANEL EVO-028 RENDU (2026-09-02, spec `docs/superpowers/specs/2026-09-02-evo028-weak-position-design.md`)** : les 3 designs within-seed MORTS sur preuve d'identité (estimand = produit position × carry-over, équivalence observationnelle 0,858) ; retenu = between EVO-027 verbatim n=86/bras (puissance 0,804 au point), bande (0,818;1,0) fermée sur preuve de coût ((1−r)⁻²). Seuils de smoke scellés (`EVO-028-SMOKE`). Dette annexe : taux per-paire d'EVO-027 jamais publiés (ancre externe incommensurable) — rétro-extractibles seulement par replay (champions non persistés à l'époque). **→ RUN FAIT ET TRANCHÉ le jour même ([[EDR-EVO-028]]) : DÉPENDANCE FAIBLE ÉTABLIE** (77/86 vs 50/86, p=3,9×10⁻⁶, ratio 0,649 [0,535;0,788] ; sensibilité anti-déflation 0,769 — l'anomalie best-ever prédite est réelle, 10 déflations LATE, sans renverser). Question position FERMÉE (forte réfutée / faible établie / >0,818 sur coût). **Dettes ouvertes** : (a) DV best-ever déflate les bras longs → tout futur harnais à horizons inégaux mesure au top-1 d'ère FIXE (la lecture secondaire d'EVO-028 devient la DV primaire candidate) ; (b) move (5→2/5→3) ne convertit JAMAIS (0/172) — pourquoi l'arête + argmax ne suffit pas est documenté (E6 dérive d'état) mais la conversion différentielle throw-vs-accept (27/63 vs 42/68) reste inexpliquée ; (c) mécanisme B-M1/M2 : injection post-run possible, champions persistés data/genomes/evo028/.
* **Flake CI consigné en passant (2026-09-02)** : le job `test-and-build` (docker frontend) a échoué sur `npm run build` → « Cannot find native binding » (bug npm optional-deps, npm/cli#4828) sur un commit purement docs/tools (run 33636235017), alors qu'il passait 3 h plus tôt — aucune modification frontend entre les deux. Si ça récidive : pin des bindings natifs (rollup/esbuild) ou `npm ci` reconstruit sans lockfile dans l'image. À vérifier sur le prochain run.
* **Brainstorm taxonomies (2026-09-02)** — cartographie complète :
  `docs/superpowers/specs/2026-09-02-cartographie-taxonomies.md` (5 strates, gaps S1-S7/T1-T4/M1-M7,
  3 convergences transversales). Décision : C1 (3ᵉ arête, après point-référence) + C5 (M1/M4/M6)
  lancés le 2026-09-02. **Restent au backlog** :
  - **C3** : sceller SDR-G2 (critère exécutable de composition), re-tagger ~5 records
    compositionnels (EDR-BILINEAR, RETAIN-COMPOSE, S2-008…), warning gate↔tests dans
    check_record_links — ~1 jour, zéro run. Preuve du besoin : 19/19 records d'août-sept en
    `gate: G0` par défaut.
  - **C4** : resynchronisation de la couche de LECTURE (EDR-114b invisible
    `consolidate_records.py:32` ; EDR-124/194 sans frontmatter ; README EDR faux ; REF-DEMAND-MARKER
    arrêté à WARM-005 et contredit par S2-012/013 ; en-tête backlog auto-contradictoire l.11 vs
    l.17) + trancher le CLIQUET DES SYNTHÈSES (M5 : une doc qui publie un compte doit le recompter).
    → ⚠️ **PÉRIMÉE (constaté le 2026-09-14)** : M5 est CLOS (porte 8, `check_synthesis_counts.py`) et T3
    (couche de lecture) est CLOS depuis le 2026-09-06/07. Rien à faire ici ; l'en-tête l.11 vs l.17 est
    repris par P3.5 (c).
  - **C2 — harnais EVO-011 : PARTIELLEMENT RÉPARÉ le 2026-09-07, et il y avait un 4ᵉ défaut.**
    → ⚠️ **PÉRIMÉE (constaté le 2026-09-14)** : EVO-011 est FERMÉE par pré-vol, sans run évolutif
    (P2.39, [[EDR-EVO-011]]) ; le « reste » de cette entrée est fait.
    Le fichier n'est pas `src/environments/` mais `src/worlds/world_1_stoneage.py` ; les 3 défauts du
    2026-08-03 étaient intacts. **(2) E4 CORRIGÉ** : 4 compteurs de lancer écrits dans TOUS les régimes
    (`throw_decided` AVANT le gate d'inventaire — c'est ce qui rend le défaut E2 lisible —, `throws`,
    `throw_hits`, `throw_prey_hits`) ; aucun appel RNG, aucun flux de contrôle changé → runs gravés
    bit-identiques ; `_throw_did` NON touché (un test de non-régression exige son absence en legacy).
    4 contre-exemples gelés (`tests/sandbox/test_throw_counters_legacy.py`), 14/14 avec la suite du
    gate torch. **(1) E2 : aucun patch monde** — le gate `len(inventory) > 0` est une loi physique ;
    c'est le harnais qui ré-équipera. **(3) life_score** : la formule est saine, l'incohérence venait
    d'un runner perdu → garde d'IDENTITÉ à poser dans le runner, pas de patch.
    ⚠️ **(4) DÉFAUT TROUVÉ DANS LA RÈGLE SCELLÉE** (registre E2 occ. 3) : `EVO-011.json` fait peser
    `mammoth_kills` 400 sur la chaîne obs[4]→throw→kill — **un lancer ne peut pas tuer une proie**
    (pas de clé `energy` : il ÉTOURDIT ; `mammoth_kills` n'est incrémenté que par la mêlée). La chaîne
    scellée est coupée par construction ; elle existe par un DÉTOUR mesurable (stun → l'apex ne se
    déplace ni ne riposte → mêlée sans riposte). **Reste** : sceller `EVO-011-PREVOL` (la règle
    d'origine ne se corrige pas), écrire le runner de pré-vol (explicite, sous `tools/evo_runs/` — 3 bras : lecteur
    câblé / brouillé / témoin, 12 seeds) et son verdict calibré, puis le smoke.
  - **GAPS SCIENTIFIQUES : 6 designs écrits et RÉFUTÉS le 2026-09-06/07** (un concepteur + un
    réfutateur par gap ; aucun run engagé). Verdicts :
    * **➡️ SUITE DIRECTE DE S6, design écrit le 2026-09-07** (`docs/superpowers/specs/2026-09-07-inworld-subject-variance-design.md`, prêt à sceller) :
      **le verdict du marqueur varie-t-il avec le SUJET, dans le MÊME monde ?** C'est l'analogue
      in-world exact de `k(σ)` — σ y était l'init, ici c'est l'ORIGINE du sujet. 7 sujets (champion
      HoF, soupe fraîche, champion bruité ×2, réflexe câblé, lecteur câblé) dans le régime GRAVÉ de
      S2-002/003, instrument et plancher inchangés. **Les DEUX issues informent** : verdicts
      DIFFÉRENTS → S6 se transporte et « le monde n'exige pas X » se relit « CE sujet a un repli »
      (bandeau sur tout record concluant sur LE MONDE depuis un sujet unique) ; verdicts IDENTIQUES →
      S6 est borné au jouet et les records tiennent, renforcés. Apport annexe : ce serait le premier
      **contrôle positif in-world** d'un marqueur de demande hors du gabarit S2-009 — ce qui manquait
      à WARM-002 et à S2-006. Coût ~15-25 min sous bail, smoke 1 sujet obligatoire avant engagement.
    * ✅ **S6 — RUN FAIT ET GRAVÉ le 2026-09-07 ([[EDR-S6-FALLBACK-RATE]])** : k(σ) = **0 / 6 / 8 / 8**
      sur 12 seeds. Dans la cellule où le CORPS SUFFIT, l'ablation mord sur 8 seeds dès que l'init n'est
      plus nulle — le NEUTRE de S2-004/005/007/008 était celui de σ=0 SEULEMENT. Gate pré-enregistré
      PASSÉ (contrôle positif 12/12, ancre 0/12 bit-identique). **Le marqueur mesure une propriété du
      SUJET, pas du MONDE** ; `REF-DEMAND-MARKER` corrigé. Trouvé en chemin : le barreau `zero` produit
      des FAUX NÉGATIFS (5 seeds), et le protocole d'origine rend une ÉGALITÉ 6-6 sur ces mêmes données
      (majorité dépendante de `PYTHONHASHSEED`). Runner `tools/s2_fallback_rate_probe.py`, 29 cas de
      calibration, 60 points en 360 s, zéro bail.
    * *(historique)* **S6 — GO, et son résultat principal est DÉJÀ ACQUIS SANS RUN** : la moitié NÉCESSITÉ de
      [[EDR-S2-006]] est **DÉFINITIONNELLE**. Vérifié en forme close : `survive` ne dépend que du SIGNE
      du gain net (métrique-SEUIL) et `fit_policy` part de `W=zeros` avec acceptation STRICTE — dans
      toute cellule à corps suffisant, la politique initiale survit déjà au plafond, rien n'est jamais
      accepté, `|W|=0.0000` est l'INIT et l'ablation est inerte par construction (classe E1). Bandeau
      posé sur le record. **Reste à mesurer** (pur numpy, zéro bail) : le taux de repli `k(σ)` sous
      init NON nulle — il dit si le NEUTRE des sondes est robuste (marqueur spécifique) ou un artefact
      de σ=0. Règle réutilisable qui en sort : *une cellule NULLE se déclare avec le plancher « privé
      de X SEULEMENT » ; si ce plancher égale l'intact, c'est une définition, pas une mesure.*
    * ✅ **S5 — ÉTAPE 0 FAITE le 2026-09-07 : le fix de persistance est ACTIF sur cette branche**
      (`tests/test_planner_g_persistence.py` passe, test `slow`, 40 s). `SDR-G4` disait encore « fix
      recommandé, WIP » : corrigé, et enrichi de la raison pour laquelle son NEUTRE du linéaire est
      FORCÉ (la variance de ΔH est dominée par le terme état-dépendant `−δ·H`, qu'un `g`
      delta-constant-par-action ignore → ratio → 1 quel que soit le contenu anticipable ; le plancher
      `r=1.0` est IMPORTÉ, E8). La phase A peut donc partir sur la BONNE référence : oracle
      action-AGNOSTIQUE + bras à labels PERMUTÉS, DV sur le nœud 74 (la seule dim que `plan_rollout` lit).
    * *(diagnostic d'origine)* **S5 — CONDITIONNEL** : le design soumis rendait sa branche positive PAR CONSTRUCTION (E1+E2+E8
      à la fois) — son plancher `r=1.0` (g≡0) est IMPORTÉ, et une carte linéaire-en-H capture la
      relaxation endogène du connectome, donc l'oracle le bat sans aucune anticipation. Corrigé : la
      référence est l'oracle **action-AGNOSTIQUE** + un bras à labels PERMUTÉS ; la DV « ce qui agit »
      est la fidélité sur le nœud 74 (seule dim que `plan_rollout` lit). Étape 0 (< 1 min) : vérifier
      que le fix de persistance est actif sur cette branche.
    * **S3 (mémoire) — CONDITIONNEL** ; **S3 (langage) — NO-GO STRUCTUREL** : `nnz(W[12:14,:]) = 0` sur
      le champion — le canal de communication n'a AUCUN chemin vers les actionneurs, l'ablation ne peut
      rien retirer.
    * **S7 — NO-GO sur l'arête** : « X demande generalization » a pour principal une identité
      capacité ≡ prérequis et pour contrôle une tautologie d'échangeabilité ; « generalization demande
      X » exige d'abord 8 cas de calibration (held-out oracle qui doit rendre 0.0, pas 1/6). Le nœud
      cesse d'attirer des arêtes fabriquées : sa nature est une PROPRIÉTÉ DE RÉGIME de chaque capacité,
      à inscrire comme telle.
    * **Résultat transversal gravé** : la survie à métabolisme fixe est une **métrique-SEUIL** —
      gradient nul sur tout l'ensemble soutenable. C'est la face « objectif » du mur [[EDR-LOCK-001]] :
      une fois soutenable, plus rien ne sélectionne la lecture ([[EDR-EVO-016]] voit le même mur côté
      recherche).
  - **Tiroirs de pré-inscription (consigné en fermant T4, 2026-09-06).** `check_preregistration_applied.py`
    apparie règle→record par PRÉFIXE de nom de fichier (`_record_text_for`) et ne fait JAMAIS échouer une
    règle sans record : (a) une règle scellée jamais conclue (EVO-022 pendant 5 jours ; EVO-011 depuis le
    2026-08-03) a la même signature qu'un run à venir ; (b) 6 règles RAPPORTÉES dans un autre record
    (`EVO-006-REPLICATION`→EVO-006, `EVO-028-SMOKE`→EVO-028, `S2-FLOOR-PRONOSTIC`/`-bis`→S2-013,
    `DELAYED-COORD-LR-N12`/`-bis`→DELAYED-COORD) sont SAUTÉES au lieu d'être inspectées. Garde proposée :
    clé optionnelle HORS sceau `"reported_in": "EDR-…"` (`verify` ne hache que `rule`) ; règle sans record
    ET sans `reported_in` ET plus vieille que 7 jours (date git) = ÉCHEC ; contre-exemple gelé = JSON
    antidaté sans record.

**D3 — Changer le MOTEUR, pas la recherche.** Un substrat où la variation ne soit pas un tirage d'arêtes
isolées. ⚠️ **L'avertissement de doublon est PÉRIMÉ** : ce travail parallèle est LIVRÉ et gravé (`EDR-BILINEAR`, 2026-08-03 — le terme bilinéaire fait passer `(q+key)%K` de nul à appris). D3 doit donc être re-formulé à partir de ce qui existe, pas coordonné avec un chantier fini.

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
  28/29 ères -> **le verrou est la DÉCOUVERTE, pas la rétention**. ⚠️ **Nuancé par [[EDR-EVO-021]]** : la
  rétention observée était en partie un effet d'ÉLITISME, `add_node` détruisant 56 % des lecteurs câblés.
  La conclusion « le verrou est la découverte » tient ([[EDR-EVO-023]] : sans aucune croissance, 0/12),
  mais le « 28/29 » ne mesure pas ce qu'il semblait mesurer.
* **EVO-009** : biaiser l'**opérateur de variation** fait passer la lecture de **1/12 à 12/12**
  (**Fisher p = 9.6e-6**), sans coût de survie. ⚠️ **DIAGNOSTIC, pas algorithme** — le biais connaît les
  arêtes qui comptent.

**Dette HoF 59↔64 / 108↔126 : CLOSE.** Ce n'était pas une divergence de lignée mais **deux contrats
coexistants** — `WorldConfig` (59/108) vs `MambaAgent` V18 (64/126 = +8 ToM +5 Goal +5 masque), le monde
tronquant ses 5 colonnes `manager_goal`. Débloquer tient en deux lignes de config ; fait, et les champions
canoniques probés confirment EVO-004 (bascule médiane **0.0000**).

**Ce qui reste ouvert, par ordre de valeur :**
1. ⛔ **RÉFUTÉ — ne pas relancer.** « Rendre `mutate_weights` capable de RÉVEILLER des poids nuls » a été
   fait et mesuré : [[EDR-EVO-010]], **254 117 réveils de poids nuls → 0 lecteur**. L'ingrédient actif
   d'EVO-009 était le **CIBLAGE**, pas le volume. Le document se contredisait ici avec son propre bloc de
   clôture plus haut (« 010 volume » listé parmi les six méthodes échouées).
2. ⚠️ **Largement tranché, et la tentative directe est bloquée.** L'enjeu (« la lecture paie-t-elle en
   survie ? ») a reçu sa réponse par [[EDR-EVO-016]] : une lecture qui **double** la durée de vie
   (6.5→14.0) donne quand même **0/12** sous survie seule. La tentative in-world dédiée (EVO-011) a été
   **arrêtée au pré-vol** sur trois défauts de harnais et n'a produit aucun résultat — le harnais reste
   à rebâtir avant toute relance.
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

**P1.1 — ✅ CLOSE (décision du 2026-09-14) : `pytest-timeout` est installé et IMPOSÉ par la CI (`.github/workflows/ci.yml`, `--timeout`) ; racine #1 corrigée le 2026-07-22, le résidu « timeout par test » est fait.**
<!-- closes_when:grep_present=.github/workflows/ci.yml::pytest-timeout -->
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

**P1.2-bis — 🗑️ PÉRIMÉE, RETIRÉE du flux actionnable (re-constaté 2026-09-07).** Elle se déclarait
elle-même périmée depuis le 2026-07-22 et n'a jamais été sortie : une entrée qui annonce sa propre
péremption et reste dans la liste est du bruit qui coûte à chaque lecture.
*Corps d'origine, conservé pour l'historique :* Les cibles nommées `measure_inworld_grab_rate`
(`warmstart_evolution_inworld.py:1043`) ET `_torch_survival_eras` tiennent DÉJÀ le VRAI bail
(`_acquire_kuzu` → `tools.jobs.lease.acquire("kuzu")`, pas un correctif ad hoc). L'entrée décrit un état
antérieur à leur câblage. De plus, sa motivation « suite en timeout » était en réalité le bug `stop()`
de P1.1 (corrigé), **pas** la contention de lock. Reste, en défense-en-profondeur (valeur moindre,
sessions parallèles finies) : les sondes standalone actives sans bail exclusif — `dreaming_probe.main()`
(utilise `_acquire_shared_db` mais pas le bail) et `s2_demand` — plus ~70 scripts one-off legacy à ne
PAS wirer en masse (morts, risque > valeur). *Coût résiduel : ~30 min pour les 2 sondes actives.*

**P1.3 — Graver un EDR : aliasing des bancs torch + défaut du retriever. ✅ FAIT — c'est [[EDR-INFRA-001]].** Deux findings mesurés, désormais consignés, qui **changent la lecture de WARM-005/007/008** :
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

**P1.4 — ✅ DÉCIDÉ le 2026-09-14 : ÉPINGLER par un test maintenant (→ P2.64), corriger APRÈS le run P4.4.** *(Question d'origine : corriger l'aliasing en production, ou l'épingler ?)* Le monde écrit dans l'état
récurrent par cette voie dans tous les bancs torch. Corriger changerait **toutes les baselines torch** ;
ne pas corriger exige un test qui **épingle** le comportement pour qu'il ne dérive pas silencieusement.
Décision hors de mon périmètre (code partagé, arbre partagé entre sessions). *Coût : décision.*

**P1.5 — 🗑️ PÉRIMÉE (2026-09-07) — décrit l'état non committé d'une session de JUILLET, close depuis.**
Énoncé d'origine : « Rien n'est committé de cette session (~20 fichiers, tous scopés).
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

**P2.0-bis — ✅ RÉSOLU** *(l'entrée de journal plus bas dans cette même section porte le résultat : `champion_body` est gravé en `EDR-S2-012`)*. Énoncé d'origine : `champion_body` n'avait AUCUN record (`grep docs/EDR/` : 0 hit) alors qu'il porte le verdict
fondateur S2, sur lequel repose toute la §2 de `SPECIFICATION_10ANS.md`. Finding fondateur sans record
**ni** calibration. Candidat sérieux au top 3. *(non traité)*

**P2.1 — ✅ RÉSOLU** *(entrée de journal plus bas : branche `perception` calibrée le 2026-07-21)*. Énoncé d'origine : `_torch_survival_eras`, branche `perception` — 85 ✔ *(passait DEVANT `ablation_verdict`)*
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

**P2.17 — ✅ DÉPASSÉE (2026-09-07) — l'exhaustivité a été atteinte, ce que cette entrée déconseillait.**
*Mesuré : le cliquet compte **196 détectés / 192 calibrés / 0 dette** (4 non-instruments motivés) ; son
énoncé parlait de « 70 non calibrés » et de viser les porteurs plutôt que l'exhaustivité. La 7ᵉ vague
d'élargissement (famille `run_*`, 72 fonctions) a absorbé le reste sans un gramme de dette.*
Énoncé d'origine — calibrer par ordre de citation dans le graphe de records.** *(renumérotée le 2026-09-01 : portait « P2.2 », déjà pris par une tâche DIFFÉRENTE plus haut)*
`python tools/check_instrument_calibration.py --report` donne la liste (70 non calibrés). Ne PAS viser
l'exhaustivité : viser les **porteurs**. *Coût : ~2 h par instrument.*

**P2.18 — ✅ FAIT (2026-07-22) — hook pre-commit du cliquet de calibration livré.** *(renumérotée le 2026-09-01 : portait « P2.3 », déjà pris par une tâche DIFFÉRENTE plus haut)*
`tools/hooks/pre-commit` fait désormais DEUX vérifications indépendantes (records + calibration), chacune
gatée sur ses fichiers stagés, drapeau `fail` partagé. La garde calibration ne se déclenche que quand un
`.py` de `tools/` ou `src/seed_ai/` est stagé (le checker scanne l'arbre entier, pas de `--only`) →
n'ennuie pas les commits de docs seuls. Testé dans les deux sens : un instrument bidon non calibré
**bloque** (exit 1, message actionnable) ; l'arbre propre **passe** (81/12/0 nouveaux) ; un commit
hook-seul **skippe** la garde. Le cliquet ne dépend plus de la discipline — principe transverse n°1
(règle documentée sans application exécutable => violée) enfin fermé pour la calibration comme il l'était
pour les records. *Bypass d'urgence : `git commit --no-verify`.*

**P2.13 — ✅ CLOSE (2026-09-07) par un ÉCRAN MÉCANIQUE, à coût de simulation NUL — et ma propre
qualification « dette scientifique dominante », écrite le matin même, était FAUSSE sur 2 des 3
cibles.** Classe E19 : balayer le PAS, et RE-AUDITER au réglage le stock de
conclusions de l'arc BILINEAR / LANG-MEMORY / MEM-PERCEPTION / RETAIN-COMPOSE (tous à `lr=0.02`).**
*Preuve : à protocole identique et n=12, la seule variation de `lr` bascule le verdict d'un record ENTIER*
— `run_retain_compose_diagnostic_probe`, `episodes=600`, `n_agents=16`, `K=6`, `bar=0.3167` :
`lr=0.02` → `learned` **0.173** (verdict `RETENTION`) ; `lr=0.002` → `learned` **0.923** (`INCONCLUSIVE`),
**0/144** chevauchement, 12/12 seeds. Cause : `n_agents` n'est PAS un minibatch (chaque agent a ses propres
`W/U/V/W_bl`, `src/agents/backend_torch.py:85-86`) → **batch effectif = 1**, toléré par les conditions à un
`_step` et divergent sur les deux `_step`.

**Résultat du crible, 2026-09-07 — les 3 arcs restants sont PEU SENSIBLES, et c'est MÉCANIQUE :**

E19 n'est pas « un `lr` trop grand » : c'est un pas trop grand **sur un batch effectif 1**, dont l'effet
n'explose que si le gradient doit traverser une frontière récurrente. La grandeur qui décide n'est donc
pas la longueur de la séquence mais la **PROFONDEUR DU GRADIENT**. Écran appliqué aux trois :

| arc | `lr` publié | profondeur du gradient | exposé ? |
|---|---|---|---|
| BILINEAR (cellule décisive) | 0.02 | **1** — `same_tick=True` ⇒ séquence de longueur 1, `H_in` = zéros littéraux | non |
| MEM-PERCEPTION | 0.02 | **1, invariante** — `learn_episode` détache EN TÊTE de boucle (`backend_torch.py:357`) | non |
| LANG-MEMORY (l'arête) | **0.002** | 1 | non — déjà au `lr` correctif |

Trois corrections à ce que j'avais écrit le matin même, toutes vérifiées :

1. **L'arête `language→memory` n'est pas portée par `EDR-LANG-MEMORY`** mais par
   `LANG-MEMORY-EDGE_Third_Edge_Established_…` (c'est le champ `record` de `demands.json` qui le dit),
   et elle est scellée à **`lr=0.002`, 3600 ép.** — la valeur correctrice elle-même. Jamais exposée.
2. **`EDR-BILINEAR` porte déjà son encart de rétro-audit** : sa clause secondaire 2-pas a été
   re-mesurée (0.1789 à `lr=0.02` → 0.3797 à `lr=0.002`, 0/144, n=12) et sa clause principale est à
   UN pas, explicitement « hors du régime suspect ».
3. **Seul `MEM-PERCEPTION` n'a jamais été re-audité** — et son crédit est à 1 pas, le régime que
   `EDR-RETAIN-COMPOSE-LR` a mesuré comme TOLÉRANT à `lr` élevé.

⚠️ **Et le crible que je proposais était un INSTRUMENT À ISSUE UNIQUE.** « Balayage court n=3 » :
`ablation_verdict` a `n_floor=12` en dur (`tools/demand_marker.py:70`), et le garde-fou bloque les TROIS
branches sous ce seuil. Vérifié en exécutant l'instrument sur des formes connues — effondrement net,
inerte, inversé — **les trois rendent `INCONCLUSIVE` à n=3**, et discriminent à n=12. Ma proposition ne
pouvait donc rendre qu'une seule issue : c'est la question 1 du pré-vol, ratée sur mon propre design.
L'écran mécanique l'a remplacée, et il a coûté zéro simulation.

**Ce qui RESTE, et ce n'est pas E19** — le crible a redirigé la dette au lieu de la fermer à blanc :

- **BILINEAR est exposé à P2.15, pas au pas.** Sa barre `1/K+0.15 = 0.3167` est 0.072 SOUS le plafond
  structurel du plain (0.3889 — **SUPERSÉDÉ le 2026-09-07 : 30/36 ≈ 0.833**, cf. P2.15 ; l'écart réel
  est 0.517, pas 0.072). Corollaire mesuré et contre-intuitif : **allonger `episodes` ne renforce
  pas cette mesure, il la CASSE** — le plain monte vers son plafond pendant que le bilinéaire est déjà
  haut, et la séparation se referme par le bas. Un budget plus grand n'est pas ici un budget plus sûr.
- **MEM-PERCEPTION : les défauts du module ne sont PAS le régime publié** (`episodes=800`, `lr=0.05` en
  signature contre `1200`, `0.02` gravés). Un « simple re-run » ne reproduirait pas le record.
- **Signalé par un réfutateur, à instruire séparément** : d'après `test_agi_taxonomy_gate.py:8-11`, le
  bras DELAYED de MEM-PERCEPTION serait « arithmétiquement FORCÉ » et incapable de produire l'issue
  négative. Si c'est exact, c'est une E1/E2 sur une arête GRAVÉE — et sans rapport avec le pas.
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

**➡️ (a) FAIT le 2026-09-02** (commit 481117e : `BILINEAR` dans le try/finally + optimiseur `U/V/W_bl`) **et le point-référence S1 est ÉTABLI** : au crédit REINFORCE de la sonde, la référence LANG intact apprend à **lr=0.002/ep=3600/D=0 → médiane 0.744** (0.74/0.74/0.82, 3/3 seeds ; ablaté ~0.17=chance ; contrôle ~1.0) et **lr=0.02 tue tout** (~0.17 partout) — la bascule au lr d'EDR-RETAIN-COMPOSE-LR se reproduit. Balayage résumable : `tools/lang_memory_sweep_reference_point.py` → `results/lang_memory_sweep.json`. **(b) FAIT le jour même** : D=2 réfuté au point (3/3 chance, contrôle dégradé) → règle scellée `LANG-MEMORY-EDGE` à D=0 → run n=12 complet ([[EDR-LANG-MEMORY-EDGE]]) : **INDÉTERMINÉ D'INSTRUMENT** — PRINCIPAL X_DEMANDED (4,66×) ET PRESENT X_DECOY (1,18, la spécificité PASSE) ET barre franchie (0,750 ≥ 0,5), mais la garde d'alias rend DEGENERATE_CONTROL (contrôle saturé ~1,0 des deux côtés — le cas calibré E3 occ.3 tire en production). **(c) EN COURS le soir même — et les deux candidats initiaux étaient MORTS** : le sous-échantillonnage (budget réduit) est un piège arithmétique MESURÉ (smoke cte=6 : ci=0,702 mais ca épinglé à 1,000 → `ci<0,95 ∧ ca=1,0 ⇒ leakage>tol` forcé ; `ci≥0,95 ⇒ DEGENERATE`) — il ne peut JAMAIS passer la garde tant que H=0 rend la tâche triviale. Correctif retenu : **bruit d'entrée à dose connue** (`control_input_noise=0,15` → plafond (1−p)+p/K=0,875 des DEUX bras ; calibration PRÉDICTIVE : mesuré 0,853/0,870, leak 0,017 ; LANG inchangé). `LANG-MEMORY-EDGE-bis` scellé, RE-RUN COMPLET 3 bras n=12 en tranches (le bruit modifie l'interférence de tête partagée → pas de mélange de populations ; la première mesure reste gravée). **→ ARÊTE ÉTABLIE le soir même ([[EDR-LANG-MEMORY-EDGE-BIS]]) : les 4 branches scellées positives** — PRINCIPAL X_DEMANDED 4,97× (0,819→0,165, n=12), PRESENT X_DECOY 1,19, garde SURGICAL (leakage 0,003 ; l'injection à dose connue a prédit 0,875 → mesuré ≈0,866). **P2.14 CLOSE** : 3ᵉ arête du graphe, première par ablation SUBSTRAT, première refusée-puis-rouverte par levée de verrou. Portée : D=0 (la rétention longue reste le mur LOCK-001), proxy REINFORCE.
* **C3 FAIT le 2026-09-02 (panel + réfutateur : 2 fatales corrigées AVANT gravure)** : SDR-G2
  re-scellée (proxy FRANCHI / fort OUVERT = mur LOCK-001), 13 frontmatters re-taggés (dont les DEUX
  mismatches gate↔tests réels : S2-008 G2/[SDR-G0] et **S2-007 G4/[SDR-G0], raté par le draft,
  attrapé par le réfutateur**), warning `gate_tests_mismatch` dans check_record_links (cliquet
  strict d'emblée). **Dettes consignées en passant** :
  - ⚠️ **6ᵉ angle mort du cliquet de calibration** : `substrate_ab_compositional.py` et
    `compositional_world_probe.py` rendent des verdicts (`BINDING_FORCED`, `:950,994-995`) et sont
    INVISIBLES au détecteur (117 détectés, 0 signalé) — le KPI de la porte G2 n'a AUCUN instrument
    au registre. Tout nouveau run proxy G2 est BLOQUÉ tant que le banc n'entre pas au registre. **→ LEVÉ le 2026-09-02 (6ᵉ ÉLARGISSEMENT du détecteur)** : les verbes `compare_`/`sweep_`/`probe_` en TÊTE de nom n'étaient couverts par aucun motif (seul `run_*sweep*` l'était). Coût compté AVANT application : **+22 fonctions** — 10 du banc compositionnel calibrées par INJECTION À DOSE CONNUE (les verdicts `BINDING_FORCED`, `GATE_BINDS`, `ANTISAT_RESCUES`… avec leurs branches NÉGATIVES ; l'injection a d'ailleurs trouvé une clé manquante, `gate_bias_margin_end`) et 12 sondes par garde d'arguments en tête (3ᵉ vague, refus < 0,5 s). **Cliquet toujours STRICT** : 139 détectés / 138 calibrés / 0 dette. ⚠️ **Reste ouvert et MESURÉ — puis RÉGLÉ le 2026-09-06 (la famille `run_*`, 72 fonctions, est entrée au périmètre sans créer de dette ; cf. CLAUDE.md)** : un motif `run_\w+` générique ajouterait **+56** fonctions non calibrées (`run_condition`, `run_arm`, `run_cell`, `run_era*`…) — chantier à part, délibérément NON avalé ici (l'avaler aurait forcé à geler 56 dettes, c.-à-d. à rendre le cliquet non strict pour la première fois depuis sa fermeture).
* ✅ **DETTE `run_\w+` CLOSE le 2026-09-06 (7ᵉ ÉLARGISSEMENT — le plus gros du dépôt)** : inventaire
  réfuté = **72 fonctions** (57 simulateurs, 14 orchestrateurs, 4 helpers), toutes gardées/déclarées
  dans la MÊME passe → le motif générique entre **sans un gramme de dette** : le cliquet passe de
  143 à **196 détectés / 192 calibrés / 0 dette**, 4 non-instruments motivés.
  * ⚠️ **DÉFAUT DU CLIQUET trouvé par le réfutateur, et il aurait été FABRIQUÉ PAR CETTE PASSE** :
    `scan_calibrated` faisait `out.add(bare)` — une déclaration QUALIFIÉE `fichier::fonction`
    verdissait le NOM NU, donc TOUS les homonymes. Déclarer `ablation.py::run_condition` aurait verdi
    `s2_demand.py::run_condition`, jamais gardé. Corrigé par `collision_coverage` (fonction pure, un
    nom en collision n'est couvert que si CHAQUE chemin l'est), 4 contre-exemples gelés dans
    `tests/sandbox/test_check_instrument_calibration_collisions.py`. **Dette réelle révélée** : 6
    définitions homonymes roulaient sur ce faux vert (`arc5::_verdict`, `lethality::_verdict`,
    `lewis_survival_sweep::_verdict_capacity`, `lewis_world::measure_mi`,
    `target_competence_probe::run_probe`, `vertical_world_probe::run_probe`) — toutes calibrées.
  * ⚠️ **DETTE RESTANTE, DÉCLARÉE ET NON MASQUÉE** : les 11 orchestrateurs `run_*` n'ont que leur
    garde d'ENTRÉE ; leurs **branches de verdict** ne sont pas couvertes (injection à dose connue à
    écrire : `run_s2`, `run_openloop_ladder`, `run_direction`, `run_transfer_experiment`, `run_q1/q2`,
    `run_causal`, `run_founder_matched`, `run_distress`, `run_experiment`, `run_contrast`).
  * **Identité trouvée en calibrant** (`lewis_survival_sweep::_verdict_capacity`, EDR110) : avec 3
    bras ÉQUIDISTANTS en log₂, la pente vaut exactement `delta/4` → la clause « ET pente > 0 » est
    redondante, une bosse non-monotone est lue INERTE (l'instrument ne la voit pas), et AMBIGUË n'est
    atteignable que si la capacité NUIT. Gravé dans le test.
* ✅ **T3 CLOS le 2026-09-07 — la couche de LECTURE est resynchronisée.** `docs/EDR/README.md`
  (5 collisions annoncées → **7** réelles balisées ; note sur le suffixe lettre ; les arêtes
  `extends`/`corrects`/`retracted_by` sont lues depuis le 2026-09-01 — **une rétractation DOIT porter
  `corrects:` pour être visible** ; ce que le hook bloque vraiment, mismatch et `gate_unlinked`
  inclus) · `REF-DEMAND-MARKER` (**19 adoptants manquants** ajoutés ; **condition de LISIBILITÉ E14**
  — un within ≈ 1.0 n'est un nul que SI l'intact est au-dessus du plancher de SON régime ; |W|
  corroborant FAIBLE et ASYMÉTRIQUE, contredit par S2-005 dans le même fichier ; 4 lignes ajoutées :
  S2-012, WARM-006/007/008, WARM-010, les 3 arêtes) · `FIL_DIRECTEUR_AGI` (north-star
  `transfer_ratio` **CLOS** — métrique dégénérée, AUDIT-002 ; les 5 portes avec leurs outils RÉELS au
  lieu de « à créer » ; section « le mur a TROIS NOMS ») · `SCIENCE.md` (strate taxonomy, absente
  jusqu'ici). **Chaque chiffre est parti en BALISE recomputée** — le périmètre du cliquet des
  synthèses passe à 8 documents, 15 comptes.
* **Observation d'usage sur `check_staged_authorship` (2026-09-07, en l'appliquant à moi-même)** :
  une empreinte **TARDIVE** (prise APRÈS édition) rend `verify()` inutilisable — il classe VOTRE
  PROPRE travail comme étranger et refuse le commit. C'est le symétrique exact de la limite déjà
  documentée (occ. 12 : le travail écrit APRÈS le snapshot lui échappe), mais il produit un FAUX
  POSITIF au lieu d'un faux négatif. La garde suppose donc un `snapshot()` au DÉMARRAGE de la tâche et
  **ne dégrade pas gracieusement** si on l'invoque tard. Correctif candidat à coût nul : horodater
  l'empreinte et AVERTIR quand elle est postérieure à la dernière mtime des fichiers couverts —
  « empreinte prise après édition, `verify` non concluant » vaut mieux qu'un refus qui ressemble à une
  détection. *(Constaté en adoptant la garde après l'incident E10 occ. 19 ; le commit a été fait après
  inspection MANUELLE des hunks, un par fichier, tous à l'emplacement de mes éditions.)*
* ⛔ **RÉTRACTÉ le 2026-09-07, le jour même de son écriture — « E10 sens B, forme ÉCRASEMENT » N'EXISTE
  PAS.** J'avais conclu qu'un texte écrit ici avait DISPARU sans trace pendant un commit parallèle, et
  j'en avais fait une TROISIÈME forme d'E10. **C'est faux, et la cause est mon INSTRUMENT** : je
  vérifiais par `grep -c "empreinte TARDIVE"` alors que le texte porte `empreinte **TARDIVE**` — le
  gras Markdown coupe le motif. Les TROIS vérifications qui « prouvaient » la disparition (arbre,
  commit d'autrui, `git log --all -S`) portaient le même motif et rendaient donc toutes 0. Refaites
  avec le motif correct : le texte est dans l'arbre, et il est **dans `d0431be`** — il a été
  **PRÉEMPTÉ** (committé par la session parallèle), c'est-à-dire le sens B DÉJÀ inscrit (occ. 9/16),
  pas une forme nouvelle.
  ⚠️ **Ce que cet épisode vaut vraiment** : j'ai fabriqué une affirmation POSITIVE (« une forme
  inédite existe ») à partir d'une absence produite par un instrument non calibré — la faute exacte
  que ce dépôt traque chez ses sondes, commise par moi, dans le paragraphe où je consignais des
  leçons de méthode. **Règle qui en sort** : un `grep` de vérification sur du Markdown doit viser un
  motif SANS mise en forme (un mot nu), et une absence de correspondance n'est JAMAIS une preuve
  d'absence tant que le motif n'a pas été validé sur un cas POSITIF connu.
* ✅ **M5 CLOS le 2026-09-07 — les SYNTHÈSES sont sous cliquet.** `tools/check_synthesis_counts.py`
  (porte 8 du hook) : une phrase qui publie un compte porte une balise `<!-- count:nom=valeur -->`,
  le cliquet RECOMPUTE la grandeur et vérifie aussi que le nombre figure dans le TEXTE VISIBLE — le
  mode d'échec le plus probable étant de mettre la balise à jour en oubliant la phrase. **14
  compteurs**, 9 comptes balisés, 7 contre-exemples gelés (`tests/sandbox/test_synthesis_counts.py`,
  dont la configuration EXACTE des trois péremptions mesurées : « 19 classes sur 19 », « 5 cliquets
  tous branchés », « 105/104 »). **Il a mordu DEUX fois pendant sa propre pose** : quatre balises
  posées sur la ligne suivant leur nombre (texte désynchronisé), puis `portes_hook=7` rendu périmé
  par le branchement de la porte 8 elle-même. ⚠️ **Portée déclarée** : il vérifie ce qu'on lui
  DÉCLARE, il ne découvre pas les chiffres non balisés (deviner produirait des faux positifs sur
  toute date et tout chiffre historique) ; la couverture croît par annotation : aujourd'hui
  **18 comptes balisés** <!-- count:syntheses_balisees=18 --> — et ce nombre-là est balisé LUI AUSSI, donc
  une régression de couverture se voit. *(Auto-audit du 2026-09-07 : cette phrase AFFIRMAIT cette
  propriété sans la tenir — la balise n'existait pas. Une affirmation non vérifiée écrite dans le
  cliquet qui les traque : c'est E10 au méta-niveau, corrigé le jour même. ⚠️ Et ce compteur est
  AUTO-RÉFÉRENTIEL : la balise se compte elle-même, donc poser « 15 » l'a immédiatement rendu
  faux — la valeur juste est le POINT FIXE, 16. Le cliquet l'a signalé dans la seconde qui a
  suivi sa pose.)* **Un chiffre HISTORIQUE daté
  ne se balise jamais** — « 105 au 2026-09-01 » est vrai pour toujours.
* ✅ **T2 CLOS le 2026-09-06** : `114b_*.md` était INVISIBLE au graphe (regex `^(\d{3})_`) — patchée
  avec le suffixe DANS l'id (le patcher seule aurait fabriqué une collision silencieuse 114b→EDR-114),
  `cartography._edr_number` idem, 8 frontmatters rétroactifs (114b, 124, 150-154, 194) et 15
  `gate: null` → G2. **Orphelins 31→18, non-raccordés 89→67**, 0 mismatch, baseline resserrée. **Suite immédiate (même soirée)** : le mot-clé CIBLÉ `world` (+3 mesurées, pas +56) débloque le NIVEAU 2 de G2 — `run_world` détecté et gardé, et son verdict EXTRAIT de `main` en fonction pure `capability_payoff_verdict`, calibrée (dont le refus sur un seul point de demande : l'ancien code inline fabriquait un « la capacité ne paie pas » là où aucune pente n'existe). La collision de noms a révélé **2 autres `run_world` invisibles** — dette réelle, traitée. Cliquet : 143 détectés / 142 calibrés / **0 dette**.
  - `gate_unlinked` jamais ratcheté : 11 `gate: G2` légataires sans `tests:` (017, 018, 021, 022,
    025, 027, 028, 029, 096, 102, 104) — affiché en `--report` seulement (`check_record_links.py:166`).
  - Trou E4 occ.6 (héritée, réfutateur N7) : baseline stagée SEULE → `--only` vide → le ratchet ne
    peut pas échouer sur ce commit. Corrigé dans le hook le 2026-09-02 (baseline stagée → run NON
    scopé).
**P2.14 — ✅ CLOSE (2026-09-02, commit `26ca13d`) — l'arête `language→memory` est GRAVÉE : ratio **4.967**,
n=12, ablation SUBSTRAT (une première), refusée-puis-rouverte. Le graphe AGI-Taxonomy est à **3 arêtes**.
Correctif d'instrument associé : bruit CONTROL à dose connue (`p=0.15`, prédit 0.875 → mesuré 0.866).**
Énoncé d'origine — l'arête `language→memory` est REDEVENUE MESURABLE : sonde à mettre à
niveau, puis mesure d'arête complète.**
*Diagnostic corrigé le jour même, après inspection du code* : ce n'est **PAS** l'artefact E19.
`tools/language_memory_demand_probe.py:134-137` ne sauvegarde que `(CONDITION_GATE, GATE_TARGET)` —
**`BILINEAR` n'est jamais activé** — et `:143` construit `Adam([agent.W])`, **`W` SEUL**. La sonde a donc
mesuré le substrat **PLAIN**, prouvablement incapable de représenter `(q+key)%K` (plafond structurel
⛔ **RÉFUTÉ le 2026-09-08** : la forme close du plain compose PARFAITEMENT — 9/9 à K=3, 16/16 à K=4, vérifié en Python pur ET in situ (témoins `results/plain_ceiling_witness_K{3,4}.json`). L'incapacité est FAUSSE, pas seulement mal chiffrée.
**0.3889** — **SUPERSÉDÉ : 30/36 ≈ 0.833**, cf. P2.15). **Son verdict NÉGATIF était CORRECT pour son
substrat**, mais l'argument « prouvablement incapable » qui le soutenait ne l'est PAS : la séparabilité
n'implique pas l'incapacité ici (le gain par nœud `σ(W[j,j])` casse l'inférence).
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

**P2.15 — ✅ CLOS (2026-09-07) — la garde est branchée, le plafond est MESURÉ, et la mesure a
RÉVISÉ le chiffre publié d'un facteur 2.1.** État d'origine : `assert_bar_separates_the_incapable`
existait depuis le 2026-09-02 et n'était **appelée nulle part** — E10 dans sa définition même.
<!-- closes_when:grep_present=tools/hooks/pre-commit::check_bar_separation -->

**Ce que la fermeture a livré**
- `tools/plain_substrate_ceiling.py` — le PLAFOND CONSTRUCTIF, mesuré, avec sa provenance gelée.
- `assert_bar_separates_the_incapable` **appelée** : `bilinear_composition_probe` (barre dérivée du
  plafond, garde EN TÊTE de fonction — refus instantané, zéro simulation) et
  `retain_compose_diagnostic_probe` (déclare-ou-refuse).
- `tools/check_bar_separation.py` — **PORTE 9** du hook. Détection par AST, jamais par regex : ce dépôt
  CITE `1/K + 0.15` en prose dans des dizaines de docstrings, y compris dans les fichiers qui dénoncent
  la dette. Audit fondateur : **8 sondes**, dont les DEUX qui ont gravé `language→perception` et
  `memory→perception` — le même motif, sur les mêmes fichiers, que l'audit d'épinglage du substrat.
- Porte du graphe durcie : toute NOUVELLE arête déclarant `emergence_bar` déclare aussi
  `incapable_ceiling` + `ceiling_provenance`, barre STRICTEMENT au-dessus. 5 réponses connues.

**Le résultat scientifique, et il n'était pas attendu.** Le plafond du substrat plain sur `(q+key)%K`
(K=6, un seul `_step` depuis `H_in=0`, forme close `σ(W[j,j])·tanh(W[key,j]+W[K+q,j])`) vaut
**0.8333 (30/36)**, pas 0.3889. Mesuré à 24 restarts × 20 000 pas, **re-vérifié cellule par cellule
sans autograd**. La barre `1/K+0.15 = 0.3167` n'est donc pas 0.072 sous le plafond de l'incapable mais
**0.517 sous** — la dette était sous-estimée d'un facteur 7.

⚠️ **La cause de l'erreur d'origine vaut plus que le chiffre corrigé, et elle est GÉNÉRALE.** La mesure
du 2026-09-02 portait deux contrôles appariés qui PASSAIENT tous les deux — table libre → 1.000, forme
close sur cible séparable → 1.000 — alors que sa recherche n'avait pas convergé. Ces deux contrôles
innocentent la FORME et l'OPTIMISEUR ; **ni l'un ni l'autre ne peut dire si l'on a cherché assez
longtemps sur le problème DUR**, et c'est la seule question qui fixe la valeur d'un plafond. Reproduit
ici à dessein : à 2 restarts × 60 pas, les deux contrôles valent 1.000 pendant que le plafond lit 0.278.
D'où un TROISIÈME contrôle, `saturation_control` (moitié budget vs budget plein) — et la règle
transposable : **un contrôle de CAPACITÉ ne calibre pas un contrôle de BUDGET.** C'est E19 déplacé du
pas d'apprentissage vers l'effort de recherche.

**Le chiffre est AUDITABLE et VÉRIFIÉ SUR LE SUBSTRAT.** Témoin gelé (78 coefficients) dans
`results/plain_ceiling_witness.json` : 30/36 en forme close (Python pur, sans autograd) ET 30/36
injecté dans le `W` d'un vrai `TorchPopulationModel`, lu par le VRAI `forward`. La dérivation est
donc exacte — une divergence aurait signé un aliasing au sens d'EDR-WARM-007.

⛔ **RECTIFICATION LE JOUR MÊME — la séparation de CAPACITÉ d'`EDR-BILINEAR` n'est PAS établie, et
l'erreur est la mienne.** J'ai d'abord écrit ici « la conclusion tient, marge 0.084 » : j'avais adossé
une conclusion à un MINORANT en le traitant comme un plafond — exactement le défaut P2.15, déplacé d'un
cran. Trois recherches INDÉPENDANTES sur la MÊME forme close, le même jour, par ordre d'effort
croissant : **29/36 (0.806) → 34/36 (0.944) → 36/36 (1.000)** ; la mienne atteint 33/36. Un plafond qui
monte à chaque fois qu'on cherche plus fort est le **plancher de l'optimiseur**, pas un plafond.
- Le bilinéaire mesure 0.932, les candidats-plafond du plain 0.944 et 1.000 : **la capacité du plain
  n'est pas inférieure à ce que le bilinéaire atteint**. Ce qui subsiste est une séparation
  d'**APPRENABILITÉ à budget fixe** (0.271 vs 0.932 à `episodes=300`, séparation par-seed totale) —
  un résultat réel, mais pas celui qui est écrit dans le record.
- **La sonde ne certifie plus** : `unlocked=None` et `bar_status="CEILING_IS_MINORANT"` tant qu'aucune
  borne SUPÉRIEURE PROUVÉE n'est fournie. Une condition nécessaire n'est pas une preuve.
- **Leçon transposable, et c'est la plus chère de la passe** : un plafond obtenu par RECHERCHE est un
  minorant, et un minorant ne peut pas fonder une affirmation de la forme « X ne peut pas ». La preuve
  que la recherche est faible ici est directe : sur la sous-forme additive, dont le MILP donne 0.75,
  la descente de gradient rend 0.36 — et un des trois chercheurs a REFUSÉ son propre 35/36 après
  s'être calibré sur cette réponse exacte connue (son pipeline y sous-estimait de 13 cellules). **Tâche bornée et prioritaire** :
pousser la recherche jusqu'à saturation franche et publier l'intervalle, pas le point.

⚠️ **UNE PISTE DE BORNE SUPÉRIEURE EST RÉFUTÉE, et ça oriente la suivante.** Relaxer `c_j·tanh` en une
fonction croissante QUELCONQUE par colonne (`argmax_j g_j(a[k,j]+b[q,j])`) rend le problème MILP-able —
seul compte alors l'ORDRE dans chaque colonne. Mesuré, PROUVÉ optimal, et vérifié indépendamment
(0 violation d'ordre, argmax recompté hors solveur) : cette relaxation atteint la **PERFECTION** (9/9 à
K=3, 16/16 à K=4). Elle ne borne donc rien. Conséquence utile : ce qui limite le substrat n'est **ni la
séparabilité de `a+b`, ni la monotonie par nœud**, mais la **FORME de `tanh`** — une sigmoïde unique,
seulement remise à l'échelle par nœud. Une borne supérieure devra contraindre cette forme, pas l'ordre.

⚠️ **PREUVE MÉCANIQUE de l'origine du 0.3889, et elle disqualifie un de mes contrôles.** Sur la
sous-forme ADDITIVE — dont le MILP PROUVE l'optimum à 27/36 = 0.75 — une descente à marge rend,
par budget croissant : 13/36 · **14/36 = 0.3889** · **14/36 = 0.3889** · 15/36. Le chiffre publié
se reproduit comme un **PLATEAU STABLE qui TIENT SUR UN DOUBLEMENT DU BUDGET**. Donc
`saturation_control` (demi-budget vs plein) l'aurait **BÉNI** : les deux rendent 0.3889. Le seul
contrôle qui le refuse est `dominates_proven_bound` (0.3889 < 0.75), ajouté APRÈS qu'un
réfutateur me l'ait signalé. **Règle** : un plateau de recherche est indiscernable d'un plafond
par tout contrôle qui ne dispose pas d'une VÉRITÉ EXACTE de référence.

**Bilan de la revue adversariale (9 agents, 0 mort) — elle a trouvé QUATRE défauts RÉELS, tous à moi.**
Aucun n'aurait été vu par de la relecture ; chacun est devenu un cas de calibration.
1. **Deux tests RENDUS ROUGES par mon propre correctif, et je ne les avais pas lancés** :
   `tests/test_bilinear_composition_probe.py` (`isinstance(None, bool)`) et le test DÉCISIF
   `test_bilinear_unlocks_composition_same_tick_supervised` (`assert r["unlocked"]`). Les deux gèlent
   désormais le NOUVEAU contrat — dont un contrôle apparié : le verdict REDEVIENT booléen dès qu'une
   borne prouvée est déclarée, sinon « ne certifie jamais » serait indiscernable de « ne sait pas ».
2. **Faux NÉGATIF du cliquet** : il déclarait PROPRE un fichier dès qu'un appel à la garde EXISTAIT, même
   enfermé dans une branche ÉTEINTE au réglage par défaut (`retain_compose`, `incapable_ceiling=None`).
   Nouveau code `C` — « la garde existe, rien ne montre qu'elle TOURNE ». *Et mon premier correctif était
   lui-même faux* (il parcourait le corps du module, où une `FunctionDef` est un statement non
   conditionnel : tout appel ressortait inconditionnel) — attrapé par sa propre calibration, gelé.
3. **Trois tests qui PUNISSAIENT LE CORRECTIF** : ils exigeaient que la dette reste non vide et que les
   deux sondes graveuses restent DANS la baseline. Corriger les 6 sondes — le but même de P2.15 — les
   aurait fait échouer. C'est le défaut que j'avais explicitement fermé dans la LOGIQUE du cliquet et
   ré-introduit dans ses TESTS. Le fait historique est gelé ; le périmètre est vérifié ; la dette non.
4. **Le 4ᵉ contrôle manquant** de l'instrument de plafond (cf. plus haut) : les trois premiers
   laissaient passer une recherche bloquée, et mon test lent — désélectionné, donc jamais exécuté —
   assertait `valid is True` sur le budget qui est justement AUTO-INVALIDÉ.

**SUITE DU 2026-09-08 — les barres de VITALITÉ des DEUX arêtes gravées sont désormais MESURÉES, et
l'exemption légataire de la porte du graphe est LEVÉE.** C'est la conséquence la plus lourde de P2.15,
et elle se termine bien — mais pour une raison qu'il faut dire exactement.

- **La barre était `1/K + 0.05 = 0.2167`, posée à l'estime.** Mesuré, agent NON ENTRAÎNÉ (zéro épisode,
  même monde, même éval, **régime PUBLIÉ `flip_p=0.3`**, MAX sur 12 seeds) : plafond **0.2266**
  (MEM-PERCEPTION delayed), **0.2109** (present), **0.1836** (coord), **0.1906** (nocoord). La barre
  était donc SOUS le plafond du bras principal de MEM-PERCEPTION, et à moins d'une erreur-type
  (0.016) des trois autres. **Elle ne séparait rien de démontré, dans aucun des deux sens.**
- **Les arêtes ne tombent pas, et ce n'est pas de la chance** : les valeurs publiées dépassent leur
  plafond d'incapable d'un facteur **1.87 à 3.88**. La vitalité était établie PAR LA MESURE ; ce qui
  manquait était la preuve que la barre séparait quelque chose.
- ⚠️ **Un réfutateur avait conclu l'inverse** (« à une barre de 0.75 les deux arêtes tombent ») en
  transposant le plafond de `(q+key)%K` sur un autre régime et une autre tâche. C'est exactement la
  faute que P2.15 corrige, commise dans le rapport qui l'analyse. Le plafond se mesure DANS le
  dispositif, au régime configuré — jamais importé.
- **Livré** : `_untrained_ceiling` dans les deux sondes (garde EN TÊTE, avant tout entraînement, coût
  nul) ; barre = plafond + une erreur-type ; `assert_bar_separates_the_incapable` appelée sans
  condition ; `data/agi_taxonomy/demands.json` porte les trois champs pour les deux arêtes ;
  `_LEGATAIRES_SANS_COORD` est **vide** — une exemption qui survit à la mesure qui pourrait la lever
  devient une décoration. 6 cas de calibration, 23 tests de porte.
- **Effet de bord mesuré** : les deux sondes SORTENT du périmètre de `check_bar_separation` — elles
  n'ont plus AUCUNE barre `chance + constante`. C'est l'issue idéale, et elle a fait rougir mon propre
  test qui assertait `examines >= 8`. **Troisième fois** que ce fichier punit un correctif : une
  assertion sur un COMPTE VIVANT punit le progrès. Règle appliquée depuis : geler le FAIT HISTORIQUE,
  asserter l'INVARIANT.

**LE GRAPHE AGI-TAXONOMY EST INTÉGRALEMENT DÉCLARÉ (2026-09-08) — les DEUX ensembles d'exemption sont
VIDES.** La dernière, `language→memory`, disait : « ni la forme close du plain ni le bras ablé (~`1/K`)
ne fournissent le plafond ». C'était vrai des deux candidats que j'avais envisagés, et **faux de la
question**. Le plafond pertinent est celui d'un agent qui n'a RIEN APPRIS, mesurable à coût nul dans le
dispositif. Mesuré au régime publié (D=0, K=6, bilinéaire, 12 seeds) : **0.1859** — au-dessus du hasard
`1/K = 0.1667`, donc ce n'est pas le niveau de chance passé par réflexe. La barre déclarée 0.5 sépare
(marge 0.30) et le bras intact 0.819 la franchit d'un facteur **4.40**.

| arête | plafond de l'incapable | barre | bras intact | marge |
|---|---|---|---|---|
| `language→perception` | 0.1836 | 0.1989 | 0.3438 | 1.87× |
| `memory→perception` | 0.2266 | 0.2431 | 0.6547 | 2.89× |
| `language→memory` | 0.1859 | 0.5 | 0.819 | 4.40× |

⚠️ **Ce que j'en retiens sur ma propre méthode.** J'avais écrit noir sur blanc qu'établir ce plafond
était « une mesure bornée, inscrite au backlog », puis gelé l'exemption. La mesure a coûté **zéro
entraînement** et douze forward. J'avais confondu « je ne vois pas quel candidat convient » avec « ce
n'est pas mesurable » — la forme exacte du biais que ce dépôt traque chez ses sondes : une donnée
absente devenue affirmation de fond. Une exemption qui survit à la mesure qui pourrait la lever est une
DÉCORATION, et un cliquet qui décore ment sur sa couverture ; un test l'interdit désormais de revenir.

**RETAIN-COMPOSE : une barre PAR CONDITION, mesurée (2026-09-08).** Sa clause décisive était un NUL
(`learned <= bar`), et un nul n'a de sens que contre le plafond d'un bras dont on a montré qu'il ne
peut pas faire la tâche. Le plafond de chaque condition est désormais mesuré à ZÉRO épisode, et **ils
diffèrent** : `same_tick` 0.2031 · `oracle` 0.1922 · `learned` 0.1859 · `oracle_decorrelated` 0.2016.
Une barre unique ne pouvait pas en rendre compte.

Le gain porte sur la clause qui PORTE le verdict : **`learned <= bar` ne veut plus dire « sous un seuil
arbitraire » mais « pas mieux qu'un agent qui n'a rien appris »**. Et recâbler ne réécrit PAS le passé —
vérifié : les chiffres publiés rendent les MÊMES verdicts (`lr=0.02` → RETENTION, `lr=0.002` →
INCONCLUSIVE). La bascule E19 est intacte ; seule sa justification change, et elle se renforce.
La sonde ne rend donc plus `INCONCLUSIVE_BAR_UNVALIDATED` : `bar_status = SEPARATES_MEASURED`.

**Dette de barre : 8 → 5 sondes.** Sorties du périmètre parce qu'elles n'ont plus AUCUNE barre
`chance + constante` : `memory_perception`, `perception_coordination`, `retain_compose`. Restent
`bilinear_composition` (code `C` — structurel : aucune borne SUPÉRIEURE PROUVÉE n'existe pour sa forme,
donc sa garde ne peut pas s'exécuter, et la sonde refuse de certifier) et **4 sondes de langage**
(`referential_game`, `referential_community`, `compositional_language`, `compositional_curriculum`),
dont les barres valent `chance + 0.10` / `+ 0.12`. ⚠️ Leur plafond d'incapable n'est PAS celui mesuré
ici : il se mesure dans LEUR dispositif, à LEUR régime. Le transposer serait rejouer P2.15.

**SONDES DE LANGAGE — LANG-001 et LANG-002 recâblées sur LEUR PROPRE incapable (2026-09-08).**
Aucune des trois n'accepte `episodes=0` : elles portent toutes une garde de dégénérescence qui refuse
l'argument (« ne pas confondre avec une mesure nulle OBSERVÉE »). Elle a raison, et elle m'a empêché de
plaquer une technique là où elle ne s'appliquait pas. L'incapable devait donc venir d'un **bras de
référence du même run** — et deux sondes en portaient déjà un.

- **LANG-001** (`referential_game`) : le bras **BROUILLÉ** est un agent ENTRAÎNÉ dont le canal ne
  transporte rien. Barre = son MAX sur les seeds + une erreur-type. Vérifié sur le publié : BROUILLÉ
  0.17 → barre 0.203 contre `chance + 0.10 = 0.267` ; FIABLE 0.767 franchit les deux. **L'ancienne barre
  séparait bien — mais personne ne l'avait montré.** C'est exactement ce que P2.15 corrige.
- **LANG-002** (`referential_community`) : le bras **FIXED** EST le régime à code privé, donc son
  `cross` est « ce qu'atteint un protocole NON partagé ». ⚠️ **Et là, la barre ne séparait PAS** : FIXED
  cross vaut **0.54**, soit 3.2× le hasard et bien au-dessus de `chance + 0.10 = 0.267`. La conception
  postulait « code privé → cross ~ chance » ; la mesure dit le contraire. Le verdict publié
  (`NO_SHARED_PROTOCOL`) est INCHANGÉ — il reposait sur `d_cross ≈ 0`, pas sur cette barre.

⚠️ **QUATRIÈME défaut du cliquet, et je l'ai FABRIQUÉ en corrigeant.** En validant UNE des deux barres de
LANG-002, le cliquet — qui jugeait au FICHIER — a aussitôt déclaré le fichier propre, rendant INVISIBLE
la seconde (`learned = within > chance + 0.05`) **dans le geste même qui corrigeait la première**.
Nouveau code `P` (partiel), étroit à dessein : signalé seulement quand `0 < gardes < barres`, c.-à-d.
l'auteur a COMMENCÉ à valider sans finir. Exiger un appel PAR expression punirait une garde qui en couvre
plusieurs (boucle sur conditions) et compterait comme barres des expressions qui n'en sont pas — mesuré :
`compositional_language_probe` porte 5 expressions pour 2 verdicts réels.

**Dette de barre : 8 → 4.** Reste `bilinear_composition` (`C`, structurel), `referential_community`
(`P`, une barre sur deux), et `compositional_language` + `compositional_curriculum` (`S`). Ces deux
dernières jugent une généralisation ZÉRO-SHOT contre `chance + 0.12` et **n'ont aucun bras de référence
interne**. Ce qui les fermerait est identifié et borné : ajouter une évaluation zéro-shot à MESSAGE
BROUILLÉ — le même dispositif que LANG-001, en éval seule, sans entraînement supplémentaire.

**DETTE DE BARRE : 8 → 1 (2026-09-08). Sept fermetures, sept MESURES, aucun gel.**

| sonde | incapable mesuré | comment |
|---|---|---|
| `memory_perception` | agent NON ENTRAÎNÉ, régime publié | zéro épisode |
| `perception_coordination` | idem | zéro épisode |
| `retain_compose` | une barre PAR CONDITION | les incapables diffèrent |
| `referential_game` | bras **BROUILLÉ** déjà présent | aucun ajout |
| `referential_community` | bras **FIXED** = code privé + bras brouillé | éval seule |
| `compositional_language` | **message BROUILLÉ** zéro-shot ET within | éval seule |
| `compositional_curriculum` | idem (moteur partagé) | éval seule |

Les trois sondes de langage **refusaient** `episodes=0` — une garde de dégénérescence qui m'a empêché de
plaquer la technique du non-entraîné là où elle ne s'appliquait pas, et m'a forcé à chercher l'incapable
DANS le dispositif. Deux l'avaient déjà ; pour les deux dernières j'ai ajouté un bras à **message
brouillé** (mêmes agents entraînés, même décodeur, même jeu tenu à l'écart, symboles aléatoires) — en
**éval seule**, sans un épisode d'entraînement de plus.

**Ce que la mesure a appris, au-delà du câblage** : le plafond de l'incapable n'est PAS le hasard.
Mesuré à A=4 : brouillé **0.281** contre un hasard de 0.250. Toute barre ancrée sur `chance` était donc
aveugle à cet écart, par construction.

**Ce qui reste est STRUCTUREL et doit le rester** : `bilinear_composition_probe` porte `C` parce
qu'AUCUNE borne SUPÉRIEURE PROUVÉE n'existe pour sa forme — sa garde ne peut pas s'exécuter, et la sonde
REFUSE de certifier (`unlocked=None`). Un `C` gelé y décrit l'état des connaissances, pas une dette
remise à plus tard.

⚠️ **Choix DÉCLARÉ, pas silencieux** : `n_eval` est le nombre d'AGENTS, pas combos × agents. C'est
conservateur — l'erreur-type en est sur-estimée, donc la barre plus HAUTE, donc plus dure à franchir.
L'unité de réplication du dépôt est le seed ; compter combos × agents comme indépendants serait le choix
OPTIMISTE, celui qui abaisse la barre.

**Ce qui reste ouvert, nommément**
- `retain_compose_diagnostic_probe` rend `INCONCLUSIVE_BAR_UNVALIDATED` tant que le plafond de sa
  condition `learned` n'est pas établi. Il n'est PAS égal à `1/K` : `_step` écrit l'observation dans
  `H[:, :I]`, donc l'agent qui ne sait pas ÉCRIRE reçoit tout de même `key` par report PASSIF. Mesure
  bornée : le bras `learned` à `BILINEAR=False`, budget saturant.
- L'arête `language→memory` déclare `emergence_bar: 0.5` sans plafond, et le gel est ÉTROIT et daté.
  Son bras LANG est une séquence à délai `D` sur substrat bilinéaire : ni la forme close (un seul pas)
  ni le bras ablé (~`1/K`, le niveau de chance qu'il est justement interdit de passer) ne le fournissent.
- **6 sondes** restent en dette gelée dans `tools/bar_separation_baseline.json`.
- **DÉSALIGNEMENT ENTRAÎNEMENT/ÉVAL dans `bilinear_composition_probe`** (trouvé en passant, VÉRIFIÉ dans
  le code) : `imitate_episode_bptt` supervise `out[:, :_MOVE_LOGITS]` avec `_MOVE_LOGITS = 8`
  (`src/agents/backend_torch.py:32,304`), alors que l'éval prend `argmax` sur `logits[:, :K]` avec K=6
  (`tools/bilinear_composition_probe.py:158`). Deux classes distractrices (nœuds 70-71) entrent dans le
  softmax d'entraînement et sont ignorées à la mesure. Ça ne déplace pas le plafond, mais ça change le
  GRADIENT et la comparaison au hasard `1/K` — la barre n'est pas celle de la tâche optimisée.
- **La forme close tient à UN nœud près, et la branche `d1` consomme la marge.** Elle repose sur
  l'absence de chevauchement entre la fenêtre d'observation `[0:I)` et la fenêtre de readout
  `[N-O : N-O+K)` = `[64:70)`. À `I=59` (main) la marge est de 5 nœuds ; à **`I=64`** (branche `d1`,
  divergence déjà connue) elle est **NULLE** — un input de plus et `obs` écraserait le readout `j=0`,
  changeant la forme close et donc le plafond. À vérifier avant tout portage.

**P2.16 — ✅ CLOS (2026-09-02, commit `481117e`) — le cliquet est la PORTE 5 du hook pre-commit**, gatée
sur `docs/preregistrations/*.json`, `docs/EDR/*.md` et le cliquet lui-même. Vérifié le 2026-09-07 :
1 occurrence dans `tools/hooks/pre-commit`.
Énoncé d'origine — `tools/check_preregistration_applied.py` n'est branché à AUCUNE
porte du hook.** `tools/hooks/pre-commit` ne contient que **deux** portes (vérifié : `:14`
`check_record_links.py --only`, gatée sur `docs/(EDR|ADR|SDR|REF)/*.md` ; `:31`
`check_instrument_calibration.py`, gatée sur `(tools|src/seed_ai)/*.py`). Le cliquet de l'occ. 4 d'E11 —
celui qui attrape une **DV substituée en silence** dans un record se réclamant d'une règle scellée — n'est
donc exécuté que par son fichier pytest. C'est exactement le principe transverse n°1 (« règle documentée
sans application exécutable finit violée ») appliqué à une garde pourtant déjà ÉCRITE : elle protège le
travail de qui pense à la lancer. *Correctif : une 3ᵉ porte gatée sur `docs/EDR/*.md` stagés. Coût : ~15 min.*
<!-- closes_when:grep_present=tools/hooks/pre-commit::check_preregistration_applied -->

**P2.21 — ✅ FAIT (2026-09-02) — la garde E19 avait le trou qu'elle traque : `assert_verdict_invariant_to_optimizer`
tirait DÉGÉNÉRÉMENT quand c'est le bras de RÉFÉRENCE qui s'effondre. Corrigée dans cette même passe (vitalité du
bras de référence exigée + verdict `INCONCLUSIVE_REFERENCE_COLLAPSED` + contrôle positif apparié) et rattachée
au registre des erreurs comme occurrence (5) d'**E3** — cf. `docs/REF/REGISTRE_ERREURS.md`.**
*(numérotée 21 et non 19 : `P2.19`/`P2.20` sont déjà référencés depuis du code COMMITTÉ —
`tests/sandbox/test_instrument_calibration.py:187,195,2213,2290,2465,2659,3027,3201` — pour la garde de
dégénérescence de `s2_verdict` et pour `sign_p` calculé-puis-jeté. Le code référençant gagne.)*
Elle refuse un nul dont l'écart au bras de référence se referme de plus de 2/3 sur une décade de `lr`.
Mais elle ne vérifie jamais **POURQUOI** l'écart se referme : si le bras testé monte, le nul est un
artefact (le cas visé) ; si c'est la RÉFÉRENCE qui s'effondre, l'écart se referme tout autant et la garde
tire — alors qu'il n'y a aucun artefact à dénoncer. Constaté en acte sur les données de
[[EDR-DELAYED-COORD]], où les deux bras sont au plancher. C'est le motif **E3** (métrique dégénérée lue
comme un effet) **dans la garde même qui a été écrite pour attraper les nuls dégénérés** — exactement la
forme du défaut qu'elle corrigeait chez `functional_aliasing` la veille.
- **Correctif** : exiger que le bras de RÉFÉRENCE reste VIVANT aux deux points de `lr` avant de lire une
  fermeture d'écart ; sinon rendre un verdict distinct (`INCONCLUSIVE_REFERENCE_COLLAPSED`), jamais un
  refus silencieux. Contre-exemple gelé disponible : les deux bras au plancher de ce record.
- ⚠️ **Ne PAS se contenter d'ajouter la garde** : ajouter aussi le contrôle POSITIF apparié (une vraie
  fermeture d'écart, référence vivante, doit continuer à tirer) — sans lui on remplace une garde trop
  laxiste par une garde trop stricte, ce qui est le même défaut de l'autre côté.

**P2.22 — ✅ FAIT (2026-09-02) — la classe E10 avait récidivé DEUX fois dans la même journée, sur le
MÊME fichier partagé, dans les DEUX sens ; promue.**
`tests/sandbox/test_instrument_calibration.py` est le point de contention maximal du dépôt. Le 2026-09-01 :
(a) un commit de cette session a happé ~159 lignes de travail non committé d'une session parallèle
(P2.19/P2.20 d'alors) via un `git add` path-scopé mais **pas contenu-scopé** ; (b) en sens inverse, des
sessions parallèles ont committé le contenu d'un implémenteur **avant lui** (`37bb389`, `8207b46`), le
laissant sans commit propre. Le path-scoping protège des fichiers étrangers, **pas des hunks étrangers
dans un fichier partagé**. La règle du registre s'applique : deux occurrences en `documenté` doivent être
**promues** ou reclassées — pas de troisième sans changement de statut.
- **Garde exécutable proposée, déjà éprouvée en pratique ce jour** : avant tout commit touchant un fichier
  partagé à forte contention, inspecter `git diff --cached <fichier>` **hunk par hunk** et ABANDONNER si un
  hunk n'est pas de son fait. Injectée dans les dispatches de la passe DELAYED-COORD, elle a fonctionné :
  le commit `814a2a6` rapporte « 11 hunks tous vérifiés miens ».
- **Correctif livré (2026-09-02)** : `tools/check_staged_authorship.py` (`snapshot()`/`verify()`) — une
  empreinte (contenu de l'arbre de travail + blob HEAD) prise AVANT l'édition permet de distinguer, au
  moment du commit, un hunk stagé écrit par la tâche courante d'un hunk ÉTRANGER (déjà présent dans le
  snapshot, absent du HEAD capturé au même instant) ; `verify()` NOMME les hunks étrangers et refuse.
  Calibré sur la FORME gelée du commit `e21c1f3` (dépôt git temporaire) + contrôle positif apparié
  (`tests/sandbox/test_staged_authorship.py`, 6 tests). Ne couvre que le sens (a) : le sens (b) reste sans
  garde exécutable, cf. `docs/REF/REGISTRE_ERREURS.md` (E10, occ. 8-9).

**P2.23 — ✅ FAIT (2026-09-02) — E10 occ.13 : ce n'était PAS un correctif incomplet, c'était une SECONDE
cause racine. La garde `check_staged_authorship` avait un angle mort de VOL D'ANCRE.**
Le soupçon inscrit était « correctif incomplet de la fusion de hunks contigus (`e21c1f3` → `cdbc6a2`) ».
Diagnostic : **faux**, et c'est ce qui rend le cas intéressant. La seconde passe de diff reste un
**alignement GLOBAL unique** — `SequenceMatcher.get_opcodes()` n'attribue chaque ligne qu'à UN rôle et
ancre sur le PLUS LONG appariement. Si le travail PROPRE contient un run de lignes recopié de HEAD (motif
banal : écrire un test en partant d'un test existant) plus long que le bloc étranger, l'ancre bascule sur
la copie et **le bloc étranger redevient invisible**. Ce n'est donc pas l'adjacence, c'est la COMPÉTITION
D'ANCRE. Seuil mesuré sur le fichier réel : un bloc étranger de ≤ 41 lignes disparaît face à un run copié
de 40 lignes, et réapparaît à 60.

- **Contre-exemple gelé** : `test_FORME_occ13_a_long_run_copied_from_HEAD_must_not_STEAL_the_anchor`
  et son positif apparié `test_POSITIVE_occ13_my_copy_of_HEAD_alone_is_NOT_flagged` (sans lui, on ne
  saurait pas si le correctif se contente de crier sur tout run recopié de HEAD). Le fichier passe de
  6 à 8 tests.
- **Causalité VÉRIFIÉE, pas supposée** : garde remise à sa version HEAD, le contre-exemple rend
  `DID NOT RAISE` ; garde corrigée, il détecte. Un correctif dont on n'a pas vu échouer le test n'est pas
  un correctif établi.

**P2.24 — ✅ FAIT (2026-09-02) — quatre défauts d'instrument de `tools/delayed_coordination_demand_probe.py`,
trouvés par critique adversariale AVANT de payer un run, corrigés en défauts bit-identiques.**

- **Substrat non épinglé** : `TorchPopulationModel.BILINEAR` est un attribut de CLASSE lu par `__init__`
  (`backend_torch.py:111`) et par `_step` (`:128`), ni forcé ni sauvegardé par la sonde et **absent de
  `_params`**. Un processus qui l'aurait mis à `True` ailleurs faisait mesurer un AUTRE substrat — celui-là
  même dont le terme bilinéaire débloque la composition — sans trace. Désormais épinglé au défaut déclaré
  et publié dans `_params["substrate"]`.
- **Fuite des RNG globaux (E5)** : `np.random.seed`/`torch.manual_seed` (`:295-296`) écrivaient l'état
  global du processus sans restauration, alors que le `finally` juste en dessous restaurait scrupuleusement
  trois flags de classe. La sonde re-seedait silencieusement tout ce qui tournait après elle.
- **Débit sans provenance** : `torch.set_num_threads(1)` n'était posé que sur le chemin wrapper. Un appel
  DIRECT à `_train_and_eval_arm` — c'est-à-dire exactement la façon dont on mesure un modèle de coût —
  tournait au nombre de threads AMBIANT. Le premier modèle de coût de la journée a été mesuré ainsi.
- **`lr` pilotait DEUX optimiseurs** : le baisser ne ralentissait pas seulement l'apprentissage du
  RECEIVER (l'axe E19 qu'on veut interroger), il dégradait l'émergence du code de Lewis chez le SENDER,
  donc **l'information du canal**. Tout balayage en `lr` changeait la TÂCHE en même temps que la vitesse
  d'apprentissage. Levier `sender_lr` ajouté (`None` = comportement d'avant).
- Ajouté au passage : `eval_every` (trajectoire d'apprentissage), calibré par un **no-op EXACT** à trois
  valeurs — deux ne suffiraient pas, un décalage identique passerait inaperçu — et sur les DEUX
  configurations utilisées (`RETAIN`+leurre, `PRESENT`+sans-leurre : la seconde est celle des balayages,
  et son préfixe ne porte aucun symbole). Confronté à sa réponse connue dans les deux cas : isolement du
  RNG cassé → 0.25→0.10 et 0.20→0.25, le test échoue. Aucune des deux n'est vacuité.

**P2.25 — ⚠️ OUVERT — une revue adversariale dont les vérificateurs MEURENT rend « 0 défaut confirmé »,
c'est-à-dire un VERT indiscernable d'un vrai vert. Motif dominant du dépôt, cette fois dans l'outillage
de revue lui-même.**
Le 2026-09-02, une critique du design de déconfondage `episodes × lr` a produit **24 défauts** sur 4
lentilles, puis ses 24 vérificateurs sont TOUS morts sur une limite de session. Le script post-traitait
`confirmés = défauts dont le verdict dit réel` et `réfutés = tout le reste` — les 24 sont donc sortis
classés **`refutes`**, avec `confirmes: []`. Un lecteur pressé y lit « design propre ». Seul le champ
`pourquoi: "agent mort"` a permis la lecture correcte, et il n'était là que par accident de format.
Vérification faite à la main ensuite : **au moins quatre des 24 étaient RÉELS** (cf. P2.24), dont un
confond fatal au design (`lr` pilotant aussi le sender).
- **La règle** : dans tout post-traitement de fan-out, `non vérifié` est une TROISIÈME catégorie, jamais
  fusionnée avec `réfuté`. Un agent mort n'a pas réfuté ; il n'a rien dit.
- **Critère d'automatisation** : ça se reforme silencieusement à chaque nouveau script de revue → une note
  ne suffit pas. Correctif : que le script compte les échecs et REFUSE de rendre un verdict global si
  `agents_error > 0`, au lieu de rendre une liste vide.
- ⚠️ **RÉCIDIVE le 2026-09-07, mesurée** : une orchestration à 7 chantiers a perdu **3 réfutateurs sur
  7** sur une limite de session. Les 3 plans concernés (`P2.26`, `P2.28`, `cognitive_demand_inworld`)
  sont sortis SANS vérification — et l'un d'eux portait un défaut RÉEL (collision de la clé `record:`
  avec un `rule.record` en prose dans 24 règles scellées), rattrapé seulement par le test sur données
  réelles. **Deuxième occurrence : la règle du registre s'applique — promouvoir ou reclasser.**
  Le correctif reste d'une ligne, et il n'a toujours pas été écrit.
- ✅ **APPLIQUÉ le 2026-09-07, et RECLASSÉ `non automatisable` au niveau du dépôt.** Le correctif
  a été écrit dans l'orchestration suivante (crible P2.13) : le script compte les morts, sépare
  `non vérifié` de `réfuté` en TROISIÈME catégorie, et publie un champ `verdict_global_fiable`
  qui est faux dès qu'un agent meurt. Résultat mesuré : 3 cibles, 3 vérifiées, 0 mort, verdict
  déclaré fiable — et la fois d'avant, sur 7 chantiers, 3 réfutateurs morts avaient été
  correctement signalés comme NON VÉRIFIÉS au lieu de « réfutés ».
  ⚠️ **Pourquoi `non automatisable` et pas `exécutable`** : un script d'orchestration s'exécute
  dans un bac à sable JS sans accès au dépôt — il ne peut ni importer un garde-fou d'ici, ni être
  inspecté par un cliquet pre-commit, car il ne vit pas dans l'arbre. Le remède est un PATRON,
  démontré des deux côtés (une fois en échec catastrophique, une fois en fonctionnement), pas
  une garde. C'est le plafond honnête, et le déclarer vaut mieux que proxifier une garde qui ne
  pourrait pas s'exécuter là où le défaut se produit.

**P2.26 — ✅ CLOSE (2026-09-07) — déclaration AUTOMATIQUE (post-commit) + balayage CÂBLÉ (porte 7,
avertissement seul) — `detect_preempted()` (E10
sens B) est exécutable mais sa précision est CONDITIONNÉE À LA DÉCLARATION : 2 faux positifs mesurés,
tous deux des commits de l'auteur non déclarés.**
*Livré : hook `tools/hooks/post-commit` + sous-commande `declare` de `check_staged_authorship.py` —
après CHAQUE commit (même `--no-verify`), le SHA est inscrit dans les empreintes de LA SESSION QUI
COMMITE (`session_id` dans l'empreinte, lu de `$AGAGI_SESSION_ID` puis `$CLAUDE_CODE_SESSION_ID`) pour
les chemins portés. La question dure — le hook tourne pour TOUTES les sessions du même `.git` — est
tranchée par IDENTITÉ DÉCLARÉE, pas par contenu (le contenu ne porte pas d'auteur : déclarer par contenu
aurait inscrit le commit préempteur dans l'empreinte de la victime, annulant la détection). Sans
identité : RIEN n'est déclaré (statu quo, jamais une détection annulée). 5 tests `-k P226` (fires /
spares / scope, dont le hook réel dans un dépôt temporaire). Installation : `cp tools/hooks/post-commit
.git/hooks/post-commit`. Reste : (1) les 8 empreintes réelles sont LÉGATAIRES (sans `session_id`) et
rendent donc encore 2 faux + 1 vrai — réponse connue inchangée = contrôle que le hook ne les touche pas ;
(2) ✅ **CÂBLÉ le 2026-09-07** — la condition inscrite ici avant de câbler (« une re-mesure après
quelques commits déclarés ») est REMPLIE : sur les 9 empreintes réelles, **1 seul signalement, et
c'est le VRAI positif connu** (`bar-reachable`, emporté par `481117e`) — **zéro faux positif**.
Porte 7 du hook, `scan_own_snapshots` SCOPÉ à la session : un balayage global parlerait à qui
commite de préemptions subies par d'AUTRES — du bruit adressé à la mauvaise personne. **Jamais
bloquante**, et l'argument n'est pas la prudence : une préemption n'est pas réparable par celui qui
commite (son travail est déjà dans HEAD) ; bloquer sur l'irréparable produit un cliquet qu'on
désactive. Les empreintes LÉGATAIRES restent invisibles à ce balayage — assumé et gelé par un test.
Vérifié EN PRODUCTION : le post-commit a déclaré `084a676` sur ses 3 empreintes, porte 7 silencieuse.
⚠️ **Défaut d'USAGE trouvé le 2026-09-07 en production, et corrigé : une empreinte est une UNITÉ DE
TRAVAIL, pas un abonnement.** Laissée vivante après que son travail fut committé ET déclaré, elle
re-crie dès qu'une AUTRE session édite légitimement le même chemin — mesuré sur
`tools/hooks/pre-commit`, signalé comme préempté par `27dd55b` alors que les lignes en cause
étaient CELLES DE L'AUTRE SESSION. La garde ne peut pas trancher (le contenu ne porte pas
d'auteur, même indécidabilité que pour la déclaration), donc l'issue est opératoire :
sous-commande `retire` (2 cas de calibration, dont le positif apparié qui empêche `retire` de
devenir un balai). Sans elle, la porte 7 serait devenue du bruit en quelques jours.
4 cas de calibration (`-k SCAN`), 9/9 avec les 5 P226 d'origine.
Hook INSTALLÉ dans `.git/hooks/post-commit` le 2026-09-06 (LF, exécutable, identique à sa source).
Prémisse laissée « non mesurée » par le design, MESURÉE : `CLAUDE_CODE_SESSION_ID` est le même dans la
session-mère et dans ses shells enfants — `CLAUDE_CODE_CHILD_SESSION` vaut `1`, c'est un drapeau, pas
un identifiant distinct ; et la variable est bien propagée à un script `sh` lancé par git (mesuré :
36 caractères dans le hook). La déclaration couvre donc toute une lignée de travail, sans trou.*
Le sens B — « une session parallèle commite mon travail avant moi » — a récidivé le 2026-09-02
(occurrence 14 : P2.23-P2.25 emportées par un commit de l'arc EVO-028). La garde promue le matin même
pour ce cas exact ne s'est pas déclenchée : **elle n'a jamais été invoquée**, faute d'empreinte prise
avant édition. Le manque n'est donc pas la détection mais l'**invocation**.
La promotion apparemment évidente — un balayage automatique de toutes les empreintes, câblé au
pre-commit — a été **réfutée par la mesure avant d'être livrée** : lancée sur les 8 empreintes réelles
de `runs/staged_authorship/`, `detect_preempted` rend **2 préemptions sur 2 qui sont FAUSSES**, les
deux désignant `7de1b54`, le propre commit de l'auteur. Cause : l'exclusion d'un commit « mien » repose
entièrement sur `confirm_commit(..., owner=)`, que rien n'oblige à appeler.
<!-- closes_when:grep_present=tools/hooks/pre-commit::check_staged_authorship -->

- **Conséquence opératoire immédiate** : la garde est SAINE EN FLUX (`snapshot` → édite → commite →
  `confirm --owner`) et TROMPEUSE EN BALAYAGE. Un cliquet qui crie à tort est pire qu'absent — on
  apprend à l'ignorer, et le dépôt a déjà payé ce prix (deux cliquets à 5 puis 2 faux positifs le
  2026-09-01).
- **Ce qu'il faudrait pour promouvoir pour de bon** : rendre l'attribution décidable sans dépendre de
  la mémoire de l'opérateur. Deux pistes, aucune gratuite — (a) inscrire automatiquement le SHA dans
  l'empreinte après commit (nécessite un hook `post-commit`, absent du dépôt) ; (b) retirer l'empreinte
  quand son travail est committé, pour qu'une empreinte SURVIVANTE signifie quelque chose.
- **Limite de fond, à ne pas contourner par un proxy** : le sens B n'est pas décidable sans DÉCLARATION
  — c'est la règle « ne pas proxifier ce qu'on ne sait pas mesurer ». Toute version qui devine
  l'auteur d'un commit rejoue la forme RÉTROSPECTIVE déjà déclarée non automatisable en occ. 4.

**P2.27 — ✅ CLOSE (2026-09-07) — DETTE À ZÉRO : 19 sondes examinées, **0 en défaut A, 0 en défaut B**.
Le SUBSTRAT mesuré n'était identifiable a posteriori
dans presque aucune sonde. Point de départ mesuré : **13 sondes sur 19** sans épinglage, **8 sur 19**
avec un optimiseur incomplet.**
*Livré : `tools/check_substrate_pinning.py` + baseline gelée + porte 6 du hook pre-commit +
`tests/sandbox/test_substrate_pinning.py` (16 cas, autant de `spares` que de `fires`). Vérifié en
acte : la garde TIRE sur une sonde neuve défectueuse et ÉPARGNE une sonde neuve correcte.*
<!-- closes_when:grep_present=tools/hooks/pre-commit::check_substrate_pinning -->

**État au 2026-09-02, après la passe de correction :**

| défaut | départ | reste |
|---|---|---|
| **B** — optimiseur incomplet (`U/V/W_bl` gelés à l'init) | 8 | **0 — CLOS** |
| **A** — substrat non épinglé | 13 | **5** |

B est le plus grave des deux — c'est lui qui **fabrique un nul** dès qu'on active le flag — et il est
fermé. Les 8 sondes corrigées dans cette passe (13 → 5) le sont par un patch BIT-IDENTIQUE : épinglage en dur à `False` (le
défaut de classe) et ajout de `U/V/W_bl` à une liste déjà filtrée par `if p is not None`. Aucune
signature ne change : on ferme le trou d'identifiabilité, on n'ajoute pas un levier que personne ne
demande.

⚠️ **Les 5 restantes ne sont PAS un reliquat mécanique** — elles n'importent même pas
`TorchPopulationModel`, et deux d'entre elles (`substrate_ab`, `substrate_ab_compositional`)
construisent leur population avec un `backend=` variable, donc parfois `legacy`, où épingler un flag
de classe torch n'a pas de sens. Chacune demande une décision de conception, pas un patch : c'est
pour ça qu'elles restent. Les autres : `cognitive_demand_inworld`, `torch_binary_gate_probe`,
`torch_binary_gate_heldout_probe`.

⚠️ **LE CHIFFRE A ÉTÉ CORRIGÉ, et la correction est la partie intéressante.** L'audit d'origine
annonçait **16 en défaut A et 11 en défaut B** ; c'était en partie un artefact de mon propre
détecteur. Quatre défauts du cliquet, trouvés en s'en servant pour trier la dette (commit `7df4347`) :
il ne reconnaissait pas un épinglage fait via un **alias d'import** (`TPM.BILINEAR = …`, sonde déjà
correcte comptée en dette) ; il jugeait des `Adam([w_throw, b_throw])` qui n'optimisent **aucune
population** ; il ne lisait que le **premier crochet** d'une liste concaténée ; et il **punissait un
correctif partiel** en comparant à la baseline par égalité stricte au lieu de différence d'ensembles.
Deux des « 16 » n'ont jamais été en dette. **Un compteur produit par un détecteur non calibré est un
résultat, pas une observation** — exactement ce que ce dépôt reproche à ses instruments.

⚠️ **Et un bug FRÔLÉ, qui vaut la leçon** : en corrigeant l'un de ces faux positifs, la regex de
poids de population a été écrite avec un backslash simple dans une chaîne non brute — `` \b `` y est un
caractère BACKSPACE, pas une frontière de mot. La détection B était **morte**, et l'outil affichait
« 0 défaut ». Rattrapé par les **tests de calibration**, pas par la sortie de l'outil : une sortie
confirme ce qu'on espère, un test à réponse connue non. Vérifier une garde en lisant ce qu'elle
imprime, c'est ne pas la vérifier.

Audit exhaustif des 19 fichiers de `tools/` qui construisent une population torch (2026-09-02), né de
la rencontre de deux correctifs indépendants le même jour : `481117e` (session parallèle, sur
`language_memory_demand_probe`) et `3b5554a` (sur `delayed_coordination_demand_probe`).

- **Défaut A — substrat NON ÉPINGLÉ (16/19)** : `TorchPopulationModel.BILINEAR` est un attribut de
  CLASSE lu par `__init__` (`backend_torch.py:111`) et `_step` (`:128`). Une sonde qui ne le pose pas
  hérite de l'ambiant du processus, et rien ne l'enregistre. Deux sondes mesurant le même jour dans le
  même interpréteur peuvent donc mesurer des SUBSTRATS DIFFÉRENTS sans qu'aucun `_params` ne l'indique.
- **Défaut B — optimiseur INCOMPLET (11/19)** : `Adam([pop.W])` laisse `U/V/W_bl` **gelés à leur init**
  même quand `BILINEAR` est actif. Le terme qui débloque la composition n'apprend jamais. C'est un
  piège ARMÉ : latent tant que le flag est faux, il rend un nul dès que quelqu'un l'active — et ce nul
  ne mesure que l'initialisation.
- ⚠️ **Les deux sondes qui ont GRAVÉ les deux arêtes du graphe AGI-Taxonomy portent A ET B** :
  `memory_perception_demand_probe.py` et `perception_coordination_demand_probe.py`. Cela n'invalide
  pas leurs résultats (l'ambiant était vraisemblablement `False`, donc substrat plain — ce qui est
  publié), mais **rien dans le record ne permet de le VÉRIFIER**, et quiconque activera le flag
  obtiendra un nul artefactuel.
- **Divergence à trancher** : les deux sondes déjà corrigées ont fait des choix OPPOSÉS —
  `language_memory` épingle `bilinear=True` par défaut (au motif que le plain est prouvablement
  incapable, plafond structurel 0.3889 — **SUPERSÉDÉ : 30/36 ≈ 0.833**, cf. P2.15), `delayed_coordination` épingle `False` (pour rester
  bit-identique à ses propres mesures gravées). Les deux sont défendables ; ce qui ne l'est pas, c'est
  que la différence soit invisible. Minimum : `_params["substrate"]` dans toutes les sondes.
  → **TRANCHÉ le 2026-09-14** : PAS de défaut global. Chaque sonde DÉCLARE `bilinear=` explicitement à
  l'appel et l'écrit dans `_params["substrate"]` ; la porte 6 l'exige déjà pour l'épinglage, il n'y a
  rien à harmoniser — seulement à rendre la déclaration obligatoire là où elle manque encore.
- **Reproduire l'audit** : le script de détection tient en 30 lignes (motifs `make_population(`,
  `TorchPopulationModel.BILINEAR =`, `optim.Adam([...])` sans `U`/`V`/`W_bl`). Candidat naturel à un
  CLIQUET, sur le modèle de `check_instrument_calibration.py` : le défaut se reforme silencieusement à
  chaque nouvelle sonde.

**P2.28 — ✅ CLOSE (2026-09-06) — une FAMILLE de pré-inscriptions POUVAIT passer TOUTES les portes de
`check_preregistration_applied` sans être vérifiée par AUCUNE. Mesuré sur la famille scellée le
2026-09-02.**
La sémantique de FAMILLE (base + chaîne `-bis`) — introduite le 2026-09-02 pour qu'une règle amendée
reste réparable — est appliquée au contrôle « la règle NOMME-t-elle des grandeurs ? » mais **PAS** au
contrôle « le record les MESURE-t-il ? ». Les deux membres tombent alors chacun dans un trou
différent, et l'union n'est jamais reformée :

| membre | grandeurs extractibles | record rattaché | sort |
|---|---|---|---|
| `DELAYED-COORD-LR-N12` | **0** | non | `scan()` la saute (rien à exiger) |
| `DELAYED-COORD-LR-N12-bis` | 7 | **non** | `scan()` la saute (rien à quoi comparer) |

Résultat mesuré : ni `nouvelles_sans_grandeur()` ni `scan()` ne signalent la famille — alors que le
record EXISTE et mentionne bien les 7 grandeurs. La vérification annoncée n'a jamais eu lieu.

- **Cause immédiate** : le rattachement règle→record se fait par **PRÉFIXE DE NOM DE FICHIER**
  (`fn.startswith(base + "_")`). `DELAYED-COORD-LR-N12` ne préfixe pas
  `EDR-DELAYED-COORD_Deferred_….md`, donc aucun lien. Et le compteur « sans record écrit » CONFOND
  deux situations opposées : « la mesure n'est pas encore écrite » (transitoire, légitime) et
  « le record existe mais n'est pas rattaché » (non-couverture silencieuse).
- **Correctif de fond, et il suit la règle du dépôt** : faire **DÉCLARER** à la règle le record
  qu'elle vise (clé `record:`), au lieu de le deviner par convention de nommage. Deviner l'appariement
  est exactement ce que `_record_text_for` fait aujourd'hui, et c'est ce qui rate.
- **Correctif minimal, indépendant du précédent** : appliquer la sémantique de FAMILLE au contrôle du
  record comme elle l'est déjà à celui des grandeurs — une famille dont UN membre nomme des grandeurs
  et UN AUTRE a un record doit être inspectée sur l'UNION.
- ⚠️ **Mon propre audit de ce défaut a d'abord rendu « 0 cas »** — sa notion de « record au nom
  similaire » ne rattrapait pas justement celui-ci. Un audit d'une non-couverture silencieuse peut
  être silencieusement non couvrant : ne pas le croire sur un seul passage.
- **CLÔTURE (2026-09-06)** : `scan()`/`couverture()` jugent par FAMILLE (UNION des grandeurs, UNION des
  records) via une source unique `_inspection()` ; rattachement en trois formes toutes DÉCLARÉES —
  `record:` d'enveloppe (hors sceau, STRICTE), citation `docs/preregistrations/<nom>.json` dans le record
  (13 records le faisaient déjà), préfixe de nom. Mention nue du nom = non rattaché (contre-exemple gelé).
  Sous-produit trouvé en calibrant : `lr=0.002` normalisé en `lr0002` aurait flaggé la famille À TORT le
  jour de son rattachement → un niveau n'est pas une grandeur (coupure sur `=`). Mesuré après : **14/25**
  familles inspectées (10 sans grandeur, **1** non rattachée et NOMMÉE : EVO-028-SMOKE, transitoire ;
  EVO-022 s'est rattachée par un record cite désormais sa règle), `scan()`
  vide ; S2-FLOOR-PRONOSTIC désormais confrontée à S2-013 (5/5 grandeurs présentes). ⚠️ Séparer « aucun
  record » de « record existant non rattaché » sans deviner est impossible : le cliquet NOMME les familles
  non rattachées au lieu de les compter. Tests : 6 cas dans `tests/sandbox/test_preregistration_applied.py`.

---

**P2.29 — ✅ CLOS (2026-09-07) — la clause `closes_when:` est livrée, et c'est le cliquet qui a
exigé la fermeture de cette entrée-ci.**
<!-- closes_when:grep_present=tools/check_backlog_freshness.py::closes_when -->
*Mécanisme : une entrée fermable DÉCLARE sa condition de fermeture ; le cliquet évalue CETTE
clause, dans les DEUX sens. Le sens le plus utile est le second — « l'entrée s'annonce CLOSE
mais sa condition ne l'est plus » attrape une fermeture qui a RÉGRESSÉ en silence, ce qu'aucune
relecture ne voit. Vocabulaire FERMÉ (`path_present`, `path_absent`, `grep_present`,
`grep_absent`) et prédicats PURS : un backlog est un fichier que toute session édite, et un
cliquet qui exécuterait ce qu'on y écrit serait une porte d'entrée, pas une garde. Un prédicat
inconnu est REFUSÉ bruyamment. Les entrées SANS clause restent hors périmètre et sont
RAPPORTÉES (48 au moment de la livraison) — jamais comptées comme un succès.*

⚠️ **SECOND PRÉDICAT `holds_when:` (2026-09-08), ajouté après que le premier a MAL VISÉ — défaut mesuré
en production.** `closes_when:` décrit la fermeture de l'ENTRÉE. Posé sur un SOUS-ITEM il est mal
attribué : en fermant le sous-item « SP-2 dette » de P4.3, le cliquet a réclamé la fermeture de **P4.3
tout entière**, qui reste ouverte à juste titre (elle porte une vision en cinq sous-projets).
`holds_when:` dit autre chose — « cette affirmation doit RESTER vraie » — et une SEULE direction est une
violation : la clause cesse d'être satisfaite, quel que soit l'état de l'entrée. C'est le cas très
fréquent d'un fait ÉTABLI cité dans une entrée encore OUVERTE, et il n'avait pas de véhicule.

Énoncé d'origine — le cliquet de fraîcheur du backlog était AVEUGLE à la péremption
SÉMANTIQUE : six entrées annonçaient l'inverse de l'état mesuré, et il rendait « OK ».
Mesuré en relisant le backlog pour choisir quoi faire — c'est-à-dire au pire moment, celui que
`check_backlog_freshness` existe précisément pour protéger. Les six : **P2.14** (« ⚠️ OUVERTE, arête à
mesurer » alors qu'elle est gravée depuis `26ca13d`), **P2.16** (« branché à AUCUNE porte » alors qu'il
est la porte 5 depuis `481117e`), **P2.27** (« défaut A à 5/19 » contre 0/19 mesuré), **P2.17**
(« 70 non calibrés » contre 196/192/0), **P1.5** (décrit l'état non committé d'une session de juillet),
et `P1.2-bis` (qui se déclare elle-même périmée depuis le 2026-07-22 et n'a jamais été sortie).

- **Ce que le cliquet vérifie** : liens de records morts, numéros de tâche dupliqués, chemins disparus.
  Trois propriétés SYNTAXIQUES. Aucune ne peut voir qu'une entrée affirme le contraire du réel.
- **Ce qui rend le cas intéressant** : ces six entrées étaient toutes réfutables MÉCANIQUEMENT, sans
  jugement — un `grep` dans le hook, un compte rendu par un cliquet, un `git log`. La péremption
  n'était pas « difficile à voir », elle n'était vérifiée par personne.
- **Piste, à ne pas sur-promettre** : faire DÉCLARER à une entrée fermable sa condition de fermeture
  exécutable (`closes_when:` — une commande et sa sortie attendue), et vérifier CETTE clause. Une
  entrée sans clause reste hors périmètre et le cliquet le RAPPORTE, au lieu de compter son ignorance
  comme un succès. C'est la règle du dépôt : déclarer, pas deviner.
- ⚠️ **Ne pas proxifier** : deviner la péremption depuis le texte (dates, mots-clés « OUVERTE ») serait
  exactement la forme rétrospective déjà déclarée non automatisable en E10 occ. 4.

**P2.30 — ✅ CLOSE (2026-09-07, commit `58edefc`) — la suite du graphe repasse au VERT (16 tests).**
*Correction de fond, au-delà du compte : `functional_aliasing` n'est plus figé à une VALEUR
LITTÉRALE (`'n/a'`) mais DÉRIVÉ de la cible d'ablation — `n/a` si `input`, `pass` si `substrate` —
c'est-à-dire l'invariant que la porte applique. Le littéral encodait une COÏNCIDENCE des deux
premières arêtes, et obligeait à ré-éditer le test à chaque arête : c'est exactement ce qui l'a
laissé rouge cinq jours. L'ensemble attendu reste ÉNUMÉRÉ (un compte accepterait une arête
SUBSTITUÉE — vérifié : ce cas fait échouer le test, à compte inchangé). Calibré sur 5 réponses
connues, en substituant `demands.json` en mémoire sans toucher au dépôt.*
Énoncé d'origine —
`test_the_two_REAL_edges_remain_valid_after_hardening` et
`test_the_two_REAL_edges_are_exactly_the_expected_ones` échouent avec
`Extra items in the left set: ('language', 'memory')`. Le graphe porte bien 3 arêtes valides
(`language→perception` 2.115, `memory→perception` 3.934, `language→memory` 4.967, toutes n=12).
Vérifié que ce n'est pas un effet de bord d'une autre passe : ces tests n'importent que
`tools.check_agi_taxonomy` et lisent `data/agi_taxonomy/`.
⚠️ **Une suite rouge à HEAD est un cliquet éteint** : tant qu'elle l'est, plus personne ne distingue une
NOUVELLE régression de la rougeur connue. Correctif : porter les tests à 3 arêtes, en gardant leur
propriété — l'ensemble ATTENDU est énuméré, pas compté (un test qui compte laisserait passer une arête
substituée).
- ⚠️ **DÉFAUT DU DESIGN, trouvé par le test du dépôt réel — son réfutateur était mort** (limite de
  session) : la clé `record:` COLLISIONNE avec un champ `rule.record` qui existait déjà dans **24 règles
  scellées**, en PROSE (`"EDR-EVO-006 (replication directe)"`), pas en chemin. Lu strictement, il criait
  « record déclaré INTROUVABLE » sur 13 familles — incorrigibles, puisque scellées. Correctif par
  LOCALISATION : l'enveloppe (hors sceau, corrigeable) reste stricte, une valeur qui ne résout pas est
  un problème visible ; `rule.record` (dans le sceau) n'est utilisé que s'il RÉSOUT vers un fichier et
  n'est jamais signalé pendant. Leçon P2.25 rejouée : un plan dont le vérificateur est mort n'est pas
  vérifié — c'est le test sur données réelles qui a tenu lieu de réfutateur.

---

**P2.32 — ✅ LIVRÉE (2026-09-07) — les CINQ orchestrateurs prioritaires sont calibrés PAR BRANCHE DE
VERDICT, pas seulement à l'entrée.** `tests/sandbox/test_orchestrator_injection.py` — 43 cas, aucun
monde construit (injection à DOSE CONNUE de l'attribut de module appelé), contrôle **E1 par MUTATION**
(6/6 des tests concernés meurent sur un orchestrateur rendu aveugle à la dose). Couvre `run_s2`,
`run_openloop_ladder`, `run_causal`, `run_q1`, `run_contrast`.
**Trois défauts CORRIGÉS dans la foulée**, chacun avec son test de non-régression :
- `tools/s2_demand.py::run_s2` itérait `worlds` DEUX FOIS → en itérateur, **la correction de Holm
  disparaissait en silence** (registre **E23** occ. 1) ; et `worlds or list(WORLDS)` lançait la grille
  COMPLÈTE (5 mondes × 6 conditions) quand on demandait ZÉRO monde — le run le plus cher du dépôt ;
- `tools/s2_openloop_probe.py::run_openloop_ladder` rendait `{}` sur une famille vide **sans lever**,
  et `main()` en tirait DEUX affirmations de fond depuis zéro mesure ;
- `tools/evo_memory_inworld.py::run_contrast` faisait `list(seeds)` dans sa garde, **consommant
  l'itérateur** : la garde écrite pour empêcher un négatif fabriqué le fabriquait elle-même.

**P2.33 — ✅ CLOSE (2026-09-08) — les 11 défauts réels sont CORRIGÉS, et la réfutation
adversariale en a trouvé 11 de plus.** Cinq correcteurs (un par fichier, aucun conflit) suivis chacun
de son réfuteur, qui lançait ses propres sondes. Les 11 `xfail(strict)` sont devenus des tests de
non-régression : `tests/sandbox/test_orchestrator_injection.py` passe **43/43**, sans qu'un seul test
ait disparu (vérifié par recompte — classe E22).

**Ce que les RÉFUTEURS ont trouvé, et que les correcteurs avaient laissé** — c'est là que la revue
adversariale paie, et le bilan du dépôt reste intact (toute revue trouve quelque chose) :
- `s2_demand` : **la MÊME `KeyError`, 12 lignes plus bas**. `_print_table` lisait `wi["causal_cmp"]`
  et `wi["residual_cmp"]` sans garde, alors que `verdict_within_subject` porte EXACTEMENT la même
  garde de dégénérescence que `s2_verdict` et rend alors un dict SANS ces clés. Le correcteur avait
  gardé la tête de boucle et laissé le sous-bloc causal ouvert ;
- `s2_openloop` : **TROIS gardes DÉCORATIVES** (classe E1). Le fichier de calibration restait 15/15
  vert quand on cassait la garde à la main — parce que les 15 cas tournaient tous à `num_agents=13`,
  c.-à-d. **hors du régime où `_floor_for` rend un plancher**. La clause centrale du correctif
  n'était exercée par AUCUN cas ;
- `dream_causal` : **le dénominateur publié ne correspondait pas au test qui l'utilise** (le test de
  signe jette les ex aequo), des **seeds/K dupliqués** passaient la garde et fabriquaient un verdict
  causal depuis UN tirage, et `run_founder_matched._pair` fabriquait un **ratio 0,0 depuis deux bras
  éteints** — à 40 lignes de la garde qui l'interdit ;
- `dreaming` : `run_q2` portait le MÊME défaut que `run_q1` (garde consommant l'itérateur, défauts de
  fond `else 0.0` / `else 1.0` sur les médianes) ;
- `evo_memory` : **deux tests non discriminants** (classe E1) — celui qui prétendait graver
  l'appariement ne vérifiait que le CONTENU des listes, jamais l'alignement POSITIONNEL ; celui qui
  prétendait graver l'ordre utilisait une fixture où première et dernière occurrence sont
  **indistinguables**.

Aucune régression silencieuse : chaque réfuteur a rejoué les artefacts de records archivés
(`results/dream_causal_0.json`, `dream_founder_matched_n20.json`, les rapports S2) et vérifié qu'aucun
verdict publié ne change de valeur.

**P2.34 — ✅ CLOSE (2026-09-08) — les 11 orchestrateurs sont calibrés SUR LEURS BRANCHES, plus
seulement sur leur entrée.** Les 6 restants (`run_direction`, `run_transfer_experiment`, `run_q2`,
`run_founder_matched`, `run_distress`, `run_experiment`) ont reçu leur injection à dose connue :
**83 cas** dans `tests/sandbox/test_inj_run_*.py`, aucun monde construit, contrôle **E1 par mutation**
sur chacun. Déposés en six fichiers SÉPARÉS et non fusionnés : la garde de fusion a détecté une
collision de helpers homonymes (`_inj6_injecte`) qui aurait fait disparaître des définitions en
silence — exactement la classe E22, évitée cette fois par une assertion et non par la chance.

**P2.44 — ✅ CLOSE (corrigée le 2026-09-08 par `d7557ec` — 172 cas d'injection, ZÉRO `xfail` ; le titre était resté OUVERT jusqu'au 2026-09-14) — 25 défauts RÉELS de plus, tenus en `xfail(strict=True)`.**
<!-- closes_when:grep_absent=tests/sandbox/test_inj_run_direction.py::mark\.xfail -->
Trouvés par l'injection des 6 derniers orchestrateurs et NON corrigés. Les trois plus graves sont de
la forme (a) du biais du dépôt — une entrée vide devient une affirmation de FOND **publiée** :
`run_direction` publie **NEUTRE** sur une baseline VIDE, publie **NUIT** sur une extinction totale, et
**TRONQUE EN SILENCE** quand la baseline n'a pas la longueur du bras mesuré. Cet orchestrateur porte
le KPI `transfer_ratio` de la spec SDR-G1, publié par EDR-156/129. Liste complète :
`python -m pytest tests/sandbox/test_inj_run_*.py -rx`.

**P2.35 — ✅ LIVRÉE (2026-09-07) — cliquet de RECENSEMENT DES TESTS (porte 10), classe E22 ouverte.**
`tools/check_test_census.py` + baseline `tools/test_census_baseline.json` (221 fichiers, 1785 tests) +
15 cas dans `tests/sandbox/test_test_census.py`, dont le contre-exemple GELÉ : la réécriture regex non
ancrée qui a supprimé QUATRE tests **sans lever**, faisant passer la suite de « 28 passés / 15 xfail » à
« 32 / 7 » — plus verte qu'avant. Un test disparu est une garde désarmée en silence, et c'est le seul
défaut du dépôt dont le signal habituel s'AMÉLIORE. Les 4 tests ont été récupérés depuis les
transcripts d'agents puis re-vérifiés.

**P2.36 — ✅ LIVRÉE (2026-09-07) — 8ᵉ angle mort du cliquet de calibration : le PÉRIMÈTRE était PLAT.**
`scan_instruments` parcourait `os.listdir`, donc **tout sous-répertoire de `tools/` était invisible** —
à commencer par `tools/evo_runs/` (les scripts qui ont produit EVO-022 → EVO-028) et `tools/jobs/`.
Rendu récursif ; dette RÉELLE révélée : 2 instruments (`verdict_evo011_prevol`, `classify_leases`),
tous deux calibrés dans la même passe (202 → 204 détectés, 200 calibrés, **baseline toujours à ZÉRO**).
Confirme la règle : chaque élargissement du cliquet révèle de la dette réelle.

**P2.37 — ✅ LIVRÉE (2026-09-07) — `check_preregistration_applied.py` normalisait de façon ASYMÉTRIQUE.**
Les grandeurs de la règle passaient par `re.sub(r"[^A-Za-z0-9_\[\]]", "", ...)` (`env.big_kills` →
`envbig_kills`) mais le record était confronté en texte BRUT : un record écrivant honnêtement
`env.big_kills` ne pouvait JAMAIS satisfaire le cliquet, et le seul moyen de passer était d'y coller le
token MUTILÉ — l'outil dégradait les records qu'il est censé protéger. Normalisation symétrique + deux
cas appariés dans `tests/sandbox/test_preregistration_applied.py`.

**P2.38 — ✅ CLOSE (2026-09-07) — E23 est automatisée, par DÉCLARATION et non par proxy.**
Première tentative REFUSÉE par la mesure : un détecteur syntaxique « seuil littéral dans une boucle »
trouve **2 sites dans tout le dépôt, et aucune des deux occurrences réelles** — dans les deux, la
famille se forme ENTRE les appels, pas dans une boucle. Un tel cliquet aurait été vert en permanence
(classe E4, « vérification vide »). On fait donc DÉCLARER le seul nombre que l'auteur connaît :
- `tools/experiment_preflight.py::assert_control_family` — rend le seuil par cellule, REFUSE un seuil
  non corrigé **en nommant la borne de fausse alarme**, et exige une raison écrite pour
  `method='none'` (mêmes formes que la garde E8) ;
- `declare_design(..., control_family=...)` REFUSE tout run à `n_independent > 1` sans famille
  déclarée, et PUBLIE la déclaration dans le design — donc dans le record ;
- **rétro-appliqué** aux 3 runners à n > 1 (E14 : une garde jamais rétro-appliquée est une garde
  absente). EVO-011 déclare la famille que son sceau `-bis` contenait déjà, et une assertion vérifie
  que le seuil DÉCLARÉ est celui APPLIQUÉ — sans quoi la déclaration serait décorative (E10) ;
- `tools/check_control_family.py` (porte 11, AST) ferme le trou mesuré : **9 runners scellés sur 12
  ne déclaraient AUCUN design**, donc n'étaient jamais interrogés — dont `tools/lang_memory_edge_run.py`,
  qui a produit la 3ᵉ arête établie du graphe. 20 cas de calibration.

**P2.40 — ✅ CLOSE le 2026-09-08 (commit `5969d08b`, « la dette légataire d'E23 résorbée dans la foulée, 9 runners, baseline à ZÉRO ») — entrée laissée OUVERTE par oubli, péremption vue EN PASSANT le 2026-09-16 (session loop 766eabae).**
Énoncé d'origine : dette légataire de la porte 11, 9 runners scellés sans `declare_design` (`evo022`, `evo023`, `evo024`,
`evo026`, `evo026bis`, `evo027`, `evo028`, `lang_memory_edge_run`, `s2_floor_pronostic_run`), verdicts publiés. Preuve de
la fermeture, recomputée : `tools/control_family_baseline.json` porte `"runners_nus": []`, et la porte 11 rend
« runners scellés : 24 | sans design : 0 (dont 0 NOUVEAUX) | légataires gelés : 0 ». ⚠️ Le test de fraîcheur `test_la_dette_legataire_est_REELLE_et_pas_un_commentaire`
passe désormais À VIDE (aucun gelé → aucun disparu) : il ne garde plus rien, ce qui est le sort normal d'un test de
péremption dont la dette a disparu — pas une E4, car il ne PORTE aucun verdict.
<!-- closes_when:grep_absent=tools/control_family_baseline.json::evo027 -->

**P2.39 — ✅ CLOSE (2026-09-07) — EVO-011 est FERMÉE, sans run évolutif.**
[`EDR-EVO-011`](../EDR/EVO-011_Reading_The_Type_Costs_Survival_The_Enabled_Act_Is_Net_Negative.md) :
un lecteur CÂBLÉ À LA MAIN du canal de type survit **37 % moins longtemps** que le témoin
(r = 0,631, `sign_p` = 0,0064, 11/12 seeds sous 1, 12/12 contrôles passés). La dose-réponse est
monotone sur les trois bras (lancers 0 / 95 / 164 → âge 20,8 / 13,8 / 11,0) et les agents meurent de
FAIM, pas de riposte. **L'acte que la lecture débloque est net-négatif en énergie**, donc la survie ne
peut pas sélectionner cette lecture — quelle que soit sa découvrabilité. Le pré-vol a répondu pour
29 s de calcul là où un run évolutif complet était prévu.

**P2.41 — ✅ CLOSE le 2026-09-16 (session loop 766eabae) — le PLANCHER DE BRUIT de `run_ablation_map` (±6-8 %) est désormais ANNONCÉ sur les quatre records qui le lisent, et la référence à bande APPARIÉE est une couture de l'instrument.**
Fait : (a) bandeau « RÉSOLUTION DE L'INSTRUMENT » en tête d'EDR-124, S2-002, S2-003, S2-013 (chiffres d'EDR-S2-BLIND-CHAMPION
vérifiés avant écriture ; par record, ce qui est DANS la bande — 0,991 ; ≈ 1,00 ; 0,99/0,99/1,07 — et ce qui en sort : 1,19
agricultural ; aucun verdict modifié) ; (b) `run_ablation_map(paired_band=True)` : le bras INTACT devient
`perception_null_variant(intact_cls)` (mêmes tirages que l'ablation, perception intacte), `reference` publié (`paired_band` /
`bare`), défaut False bit-identique, 1 cas d'injection à 0 monde (classes passées à `run_condition` = Null, Ablated, Reflex ;
défaut = None ; politique injectée → SA variante nulle). ⚠️ Ce que la bande appariée a DÉJÀ mesuré (EDR-S2-BLIND-CHAMPION, 2026-09-08,
stoneage) : champion aveuglé 1,0122 (bruit résiduel 1,2 %), **champion 0,9369** — dérangé, le champion survit 6,7 % de PLUS, hors du
bruit apparié : un signal que la bande nue masquait sous ses 8 %. **Recommandation (décision robla, run ~1 h avec bail kuzu,
peut déplacer des verdicts)** : re-mesurer la carte S2-002 sur les 4 mondes à `paired_band=True` + `noop_control=True`, sous une
règle scellée `S2-002-PAIRED-R1` (branches : plancher apparié publié par monde ; `PERCEPTION_HURTS` si intact < nul − bruit sur
≥ K−1 ères ; `DECOY` dans la bande ; `DEMANDED`), avant toute réécriture de S2-002/S2-013.
Énoncé d'origine : le PLANCHER DE BRUIT de `run_ablation_map` vaut ±6-8 %, et aucun record ne le mentionne. Mesuré par no-op exact (`NullAblatedMamba`, livré) : 1,058 sur le
champion, 0,922 sur un champion aveuglé, *perception intacte dans les deux cas*. Le `within_ratio`
publié du champion vaut 0,991 — DEDANS. Aucun faux `DEMANDED` n'en découle (du bruit ne crée pas de
demande), mais la résolution de tout l'arc S2 est bornée : `PERCEPTION_DECOY` doit se lire « aucun
effet détectable au-dessus de 8 % ». **Deux actions** : (a) bandeau de résolution sur les records qui
lisent cet instrument ([EDR-124], S2-002/003, S2-013) ; (b) passer la référence à `NullAblatedMamba`
(bande APPARIÉE), ce qui divise le bruit par 6 — mesuré : 1,0122 sur un sujet aveuglé contre 0,897-1,059
à bande non appariée. Preuve : [`EDR-S2-BLIND-CHAMPION`](../EDR/S2-BLIND-CHAMPION_Stopped_At_Control_The_Ablation_Instrument_Has_An_8_Percent_RNG_Noise_Floor.md).
**S2-002-PAIRED-R1 MESUREE ET LUE le 2026-09-24 (15/15 cellules, 54 min mur, machine LIBRE au depart) :
lecture scellee `CARTE_MODIFIEE`** — [[EDR-S2-002-PAIRED-R1]], `results/s2_002_paired_r1.json`. Le controle qui
motivait toute la passe est EXACT : **le no-op apparie vaut 1,0000 sur 15/15 cellules**, contre 1,058 / 0,922 a
bande nue et 1,012 au `-bis` — le plancher de bruit de +-6-8 % n'est pas reduit, il est SUPPRIME. A cette
resolution, deux lectures bougent : `soup` (within median 1,073) et `agricultural` (0,969) passent de
`PERCEPTION_DECOY` a `INCONCLUSIVE_DEGENERATE`, non par changement de signe mais par le PLANCHER (leur bras
INTACT est au niveau ou sous le plancher no-perception : soup 32,00 / 29,25 / 28,50 contre 32,00 ; agricultural
28,00 / 23,25 / 22,75 contre 25,25). `stoneage`, `industrial` et `famine` restent DECOY, desormais a bruit nul ;
aucun monde en HARNAIS, aucun MIXTE. Bandeaux poses sur EDR-S2-002 et EDR-S2-013. Deux faits publies a cote du
verdict : le `between_ratio` des memes cellules vaut 3,57 a 5,42 quand le `within` vaut ~1,00 (le faux positif
between-subject reproduit sur 15 cellules a bruit nul) ; et les trois cellules `industrial` sont BIT-POUR-BIT
identiques a celles de `stoneage` sur TOUS les champs mesures — duplication DEJA consignee par EDR-S2-002 et
EDR-S2-013 (via EDR-S2-012), ici confirmee au bit pres et employee comme **controle de determinisme** du harnais,
jamais comme replication. ⚠️ En verifiant ce dernier point j'ai failli publier comme inedit ce que les deux
records portaient deja : recidive de la regle du grep (CLAUDE.md, section Records, ligne ajoutee dans la meme
passe) — le motif avait ete valide sur le CODE et l'OUTILLAGE, jamais sur les records que j'allais bander.
<!-- closes_when:grep_present=tools/s2_demand_ablation.py::paired_band -->

**P2.42 — ✅ CLOSE le 2026-09-16 (session loop 766eabae) — `S2-BLIND-CHAMPION` re-scellé (`-bis`, puis `-ter` à seeds neufs) et LU : `AVEUGLE_SURVIT_MIEUX`, r = 1,614 sur 7/7, p = 0,016 — à corps identique, W identique, apprenant gelé, chemin d'identité coupé, bande RNG appariée.**
Fait : aveuglement à l'ENTRÉE (`InputBlindFrozenMamba`, obs = 0 : aucun poids touché, donc corps de P1.7 intact et chemin
d'identité E24 coupé), apprenant legacy gelé dans les DEUX bras (`FrozenCreditMamba`), `run_ablation_map(paired_band=True,
noop_control=True)`. Contrôles EXACTS : (i) 7/7 ; (ii) within du bras aveugle = 1,000 exactement 7/7 ; no-op apparié = 1,000 sur les
14 cellules (la bande appariée efface les ±6-8 %). `-bis` (seeds d'origine) : `INDETERMINE-DEGENERE` — sa clause (iii) écartait
tout intact sous le plancher 24,0, et l'intact à crédit gelé survit 20.5-22.5 : le phénomène lui-même ;
`-ter` (clause corrigée : écarté seulement si les DEUX bras ≤ plancher ; seeds 3032-3038, `-bis` déclaré en entier) : intact 21.0-22.0
(sous le plancher 7/7, publié), aveugle 33.25-35.5, r 1,511-1,679. Record
[`EDR-S2-BLIND-CHAMPION-TER`](../EDR/S2-BLIND-CHAMPION-TER_Blinded_At_Input_Same_Body_Frozen_Learner_The_Champion_Survives_61_Percent_Longer.md),
bandeau sur l'original ; 8 cas (`tests/sandbox/test_s2_blind_champion_bis.py`), CALIBRATED déclaré ; règles `-bis`/`-ter` scellées avant
leurs cellules. **Ce que les données disent DÉJÀ** : l'information seule n'explique pas l'effet — l'intact à perception DÉRANGÉE (obs d'un pair,
bande appariée) survit comme l'intact (within 0,977-1,035) ; le +61 % vient de la suppression de l'ENTRÉE, et par le chemin
d'identité E24 « obs = 0 » met aussi 18 logits d'ACTION à zéro. Lire « survit mieux SANS ENTRÉE », pas « sans voir ».
**Décomposé le 2026-09-22** (règle `S2-BLIND-CHAMPION-DECOMP-R1` scellée avant, mêmes 7 seeds, références importées du `-ter`,
`results/s2_blind_champion_decomp_r1.json`) : `NI_L_UN_NI_L_AUTRE` — entrée coupée / identités gardées : r 0,864 (le champion survit MOINS, 19,0 ticks sur 7/7) ; identités coupées / entrée gardée : r 0,989 (rien) ; no-op 1,000 sur
14/14. Le +61 % est une INTERACTION (aucune coupure seule ne le produit, l'une fait pire) ; mécanisme à nommer — **reste, hors de
cette entrée (décision robla)** : un bras à entrée BROUILLÉE (même excitation, information détruite). ⚠️ `_cout_s` du JSON = horloge
murale à travers une veille machine de six jours (noté dans le JSON), coût CPU non mesuré.
Énoncé d'origine : `S2-BLIND-CHAMPION` à re-sceller en `-bis` : l'intervention n'est pas celle que le sceau décrit. Annuler `W[:num_inputs, :]` coupe le chemin POLITIQUE, mais
l'observation continue d'entrer par `H[:, :max_I] = x` et par
`world_model.observe_batch(..., x_obs, train=True)` (surprise → curiosité → récompense intrinsèque).
Classe **E8**, commise dans la formulation d'une règle scellée. Le `-bis` doit (a) décrire
l'intervention pour ce qu'elle est, (b) ajouter un bras coupant AUSSI le monde-modèle, (c) mesurer à
bande appariée. La DV observée — `r` = 1,375 à 1,753, **7 seeds sur 7 dans le même sens** — n'est PAS
lue tant que ce n'est pas fait.

→ **P2.42, amendement du 2026-09-14 (panel, rang 20).** Le `-bis` se fait à CORPS APPARIÉ (ballast de
P1.7 : `make_blind` fait tomber le drain de 2,40 à 1,30, −46 %, panel en numpy pur — à re-mesurer) et à
apprenant GELÉ, en aveuglant à l'ENTRÉE. Tant que ce n'est pas fait, la DV 7/7 (+39 %) se lit comme un
effet métabolique candidat, pas comme un effet de la cécité.
<!-- closes_when:grep_present=tools/evo_runs/s2_blind_champion_bis.py::def blind_champion_verdict_ter -->

**P2.43 — ⚠️ OUVERTE (2026-09-08) — le marqueur de demande in-world n'a TOUJOURS pas de contrôle
POSITIF, et l'amplification ne peut pas en fabriquer un.** Dose-réponse mesurée dans `stoneage` :
couplage `obs → action` ×1 / ×3 / ×8 → survie 27,5 / 13,8 / 6,2, les deux derniers SOUS le plancher
24,0. Il n'existe donc pas par cette voie de sujet à la fois survivable et perception-dépendant. Trois
pistes, par coût croissant : câbler un comportement obs-dirigé BÉNÉFIQUE ; changer de monde (les 5
planchers sont mesurés) ; **jamais** abaisser le plancher après coup. Preuve :
[`EDR-S2-SUBJECT-VARIANCE`](../EDR/S2-SUBJECT-VARIANCE_Stopped_At_Smoke_No_Positive_Control_Is_Constructible_By_Amplification.md).

→ **P2.43, amendement du 2026-09-14 (panel, rang 5).** Les deux contrôles câblés du smoke sont morts
de leur CORPS, pas de leur couplage : le drain est dérivé de `W[0:10]` (`src/agents/mamba_agent.py:47-50`),
et amplifier `obs → action` ×3 / ×8 a multiplié le drain (11,0 / 15,0 en numpy pur, panel — à re-mesurer).
« Aucun contrôle positif constructible par amplification » est donc un ARTEFACT CANDIDAT. À faire, après
P1.7 : re-smoke à corps APPARIÉ (ballast exact), 4 cellules × 30 s ; si le lecteur câblé ballasté survit
ET rend DEMANDED, c'est le premier contrôle positif de `run_ablation_map` sur une politique qui lit.
→ **P2.43, note du 2026-09-22 (session loop 766eabae, en passant).** Le re-smoke à corps apparié est RÉPONDU par P2.59
(2026-09-15) : `ObsReaderOnBody` lit l'obs SUR le corps du champion (aucun poids touché, corps apparié par construction)
et rend **DECOY 0,86** (lire pour poursuivre COÛTE ; `INCONCLUSIVE_INVERTED` 0,66 sous corps insuffisant). L'artefact
candidat du panel (mort par le corps) est écarté : à corps apparié, aucune lecture câblée n'est net-positive sur stoneage.
Depuis P2.41 (b) la RÉSOLUTION n'est plus l'obstacle (`paired_band=True` : no-op 1,000 exact sur 14/14 cellules, -ter/DECOMP)
— l'obstacle est le MONDE : l'obs de stoneage n'encode que la direction de la proie la plus proche (+ type d'apex adjacent,
lidar, énergies, inventaire), et poursuivre la proie ne paie pas (EVO-011, S2-012). Un contrôle positif exige soit un
comportement obs-dirigé dont le PAYOFF est positif dans ce monde (aucun candidat câblable identifié), soit un monde où
lire paie (les 5 planchers sont mesurés). Entrée laissée OUVERTE ; décision robla.

**P1.x — ✅ CLOSE par P2.54 (2026-09-09 ; titre laissé OUVERT jusqu'au 2026-09-14) — « CI VERTE » couvrait 6 % de la suite : 1937 tests
sur 2059 n'étaient exécutés par AUCUN job.** Mesuré en parsant `.github/workflows/ci.yml` : les deux
invocations `pytest` prennent une **liste NOMMÉE de fichiers** (16 au total), jamais un répertoire.
`tests/sandbox/` — 220 fichiers — n'est donc jamais lancé en entier.

**Ce n'est pas théorique** : trouvé parce que la suite sandbox complète, lancée à la main ce jour-là,
a rendu un **rouge PRÉ-EXISTANT dans HEAD** —
`tests/sandbox/test_altar_tool_funnel_probe.py::test_funnel_empty_no_crash` exigeait qu'une cohorte
VIDE produise `AUTEL_MORT` et `GAP_ACQUISITION`, c.-à-d. deux affirmations de fond fabriquées depuis
une absence de mesure (`AUTEL MORT` est l'exemple que CLAUDE.md cite en tête de cette classe).
L'instrument avait été corrigé — il rend `INDETERMINE_AUCUN_AGENT` — mais **son test était resté sur
l'ancien contrat**, donc rouge, invisible, indéfiniment. Corrigé, avec sa branche négative appariée
(une cohorte RÉELLE à zéro doit publier `0.0`, pas `None` : c'est toute la différence que la
correction achète).

**Pourquoi c'est le gap le plus grave de la journée** : tout l'édifice méthodologique du dépôt —
instruments « calibrés », gardes « exécutables », contre-exemples « gelés » — repose sur des tests
dont **94 % ne sont exécutés par aucun gate automatique**. Un contre-exemple gelé qui ne s'exécute
jamais est indiscernable d'une garde absente ; c'est la classe **E1** appliquée à l'infrastructure de
test elle-même, et c'est déjà l'objet de P2.31 (« un contre-exemple gelé qui ne peut plus s'exécuter »),
dont ceci est la forme SYSTÉMIQUE.

**Trois actions, par ordre de valeur** :
1. faire lancer `tests/sandbox/` EN ENTIER par la CI (mesurer d'abord le temps mur — la suite tourne
   localement en quelques minutes ; les tests qui simulent un monde ont déjà leur garde de bail) ;
2. si le coût est prohibitif, un cliquet `check_ci_coverage.py` : baseline gelée des fichiers non
   couverts, aucun NOUVEAU fichier non couvert — même patron que les portes 1, 2, 10 et 11 ;
3. dans les deux cas, **cesser de citer « CI VERTE » comme un signal de santé de la suite** tant que
   le périmètre n'est pas écrit à côté du mot.

⚠️ Le hook pre-commit, lui, exécute bien ses 11 gardes — cette dette porte sur la SUITE, pas sur les
cliquets.

**Ce que la première exécution complète a rendu (2026-09-08, 8 h 30 de mur)** : **18 rouges,
1992 verts, 3 sautés, 26 xfail**. Neuf rouges ont pu être identifiés et **tous corrigés** (la sortie
des neuf autres a été tronquée ; une seconde passe avec `--tb=no -rf` est en cours) :
- **huit** venaient d'UNE SEULE garde de puissance ajoutée le 2026-09-01 et jamais rétro-appliquée à
  ses fixtures — classe **E14**, occurrence gravée ;
- un test exigeait qu'une cohorte VIDE rende `AUTEL_MORT` ;
- `test_s6_aucun_monde_aucun_bail_kuzu` portait `assert "kuzu" not in sys.modules` : **vert seul,
  rouge en suite**, une assertion sur l'état du PROCESSUS et non sur la sonde ;
- `run_aux_off_validation` écrivait son compteur de mesures manquantes **DANS la carte des bras**, et
  inconditionnellement : tout consommateur qui itérait les bras voyait des bras FANTÔMES
  (`0.0__mesures_manquantes`). Corrigé en sortant le compteur dans sa propre carte — avec l'assertion
  appariée qui interdit de « faire passer le test » en supprimant le compteur, lequel EST le correctif
  du 2026-09-01 (« un refus n'est pas un non »).

⚠️ **CORRECTION (2026-09-08) — le chiffre de 8 h 30 était FAUX, et il inversait la décision.**
Cette mesure a été prise pendant que **seize agents d'un workflow** tournaient sur la même machine,
dont plusieurs simulations de monde. Seconde passe, machine au repos : **30 min 40 s**, soit un
facteur 17. Un chiffre de coût se mesure sur une machine dont on connaît la charge — c'est la classe
**E12** appliquée au coût, et ici elle faisait conclure « la CI ne peut pas », alors qu'elle peut.

**Décision revue** : l'action 1 (faire lancer `tests/sandbox/` en entier par la CI) est TENABLE à
30 min et doit être préférée — un cliquet de couverture ne vérifie que la présence d'un fichier dans
une liste, jamais qu'il PASSE. Les deux restent complémentaires (le cliquet attrape le fichier ajouté
hors CI ; la CI attrape le rouge), mais l'ordre de priorité s'inverse.

**Seconde passe (machine au repos) : 8 rouges, 2008 verts, 3 sautés, 26 xfail — les 8 CORRIGÉS.**
Trois étaient de MOI : la garde E23 posée le matin, rétro-appliquée aux 3 runners et **oubliée sur ses
propres tests** — j'ai commis E14 le jour où je gravais une occurrence d'E14. Les cinq autres étaient
pré-existants, dans les deux mêmes familles : trois de plancher de puissance (`curriculum_transfer`),
et deux qui **EXIGEAIENT** qu'une entrée vide rende un verdict de fond (`distress_verdict([])` →
« NEUTRE », `_verdict_evolve_nav([])` → « SUBSTRAT BLOQUE »). Chaque correction porte sa branche
négative appariée : un zéro MESURÉ doit rester un verdict.

**Bilan des deux passes : 17 rouges pré-existants trouvés et corrigés, plus 3 introduits et corrigés
le même jour.** Aucun n'aurait été vu sans lancer la suite entière.

**P2.46 — ✅ CLOSE le 2026-09-15 (rang 7) : (a)(b)(c) livrés, (d) en CLIQUET (porte 17) — 18 des 126 logits d'action du champion SONT l'observation.**
**(a) câblé** : `measure_channel_saliency` REFUSE un sujet à chevauchement avant tout monde
(`allow_overlap=True` explicite ; `shared_decision_channels(genome, n_out)` en forme close, 46-53 pour le
champion) ; `run_ablation_map` PUBLIE `io_overlap` (annonce, pas refus : l'ablation à l'entrée couvre les
deux chemins). 3 témoins gelés. **(b) relu, et l'attribution était FAUSSE** : les sujets d'EVO-004 sont
quatre champions évolués in-world sans chevauchement (0/348) — sa conclusion tient sur eux ; le champion
HoF n'y était pas mesurable (monde à 59 entrées). Mesuré le 2026-09-15 dans son monde, obs complétée à 64
comme en production (`results/evo004_relecture_e24_champion.json`, n = 1 seed) : canaux partagés 46-53
bascule 0,51 (identité, `argmax(obs[46:54])` = mouvement dans 71 % des cas — `in_mem`, `in_confort`,
`is_night`, `fire_nearby`, avec le retriever ARRÊTÉ en S2 donc `in_mem` = 0) ; **8 canaux hors partage
lus par poids** (`lidar_n` 0,83, `adj_energy` 0,74, `ax` 0,62…) ; 48 au plancher. « Plancher partout » ne
s'étend PAS au champion prod. **(c) bandeaux** sur S2-002, S2-003, 124 (le verdict DECOY tient ; sa lecture
= « lire ne paie pas la survie », P2.59/EVO-011), HOF-IO-OVERLAP (attribution corrigée + mesure), EVO-004
(portée). **(d) FAIT le 2026-09-15 — porte 17, `tools/check_io_overlap.py`** : balayage des trois entiers de
chaque `.npz` de `data/genomes/` ET de chaque entrée des trois Hall of Fame (378 sujets, 0,5 s, jamais les
poids) ; baseline `tools/io_overlap_baseline.json` = les 10 entrées du HoF principal à 18 (une lignée), les
348 `.npz` et les deux HoF famine à 0 ; bloque tout NOUVEAU chevauchant et tout connu AGGRAVÉ ; un fichier
illisible est rapporté, jamais compté 0. Branché sur le hook (génomes / HoF / baseline stagés, la baseline
seule déclenche), enregistré à la porte 15 (**2/2 mutations tuées**), 6 témoins dans
`tests/sandbox/test_io_overlap_gate.py` (l'invariant « tout chevauchant est gelé », pas le nombre de génomes — E25). ⚠️ Vu en passant : `recurrent_forward` ne complète pas l'obs alors que
`MambaBatchModel.forward` le fait — deux voies, deux contrats pour le même génome (à consigner, P2.69 ?).
*Texte d'origine :*
→ **Amendement du 2026-09-14 (panel, rang 7)** : (a) câbler `assert_no_io_overlap` en TÊTE des sondes qui
lisent la perception (`tools/s2_demand_ablation.py`, `tools/cognitive_demand_inworld.py`, sondes de
saillance), refus instantané ; (b) relire [[EDR-EVO-004]] paire par paire (18 partagées vs 108) avant de
citer « plancher sur TOUS les canaux » ; (c) bandeau sur les records `PERCEPTION_DECOY` qui ont lu le
champion HoF ; (d) balayer les 348 `.npz` de `data/genomes/` (0/348 au 2026-09-08 — à refaire à chaque
nouveau lot). Ne PAS ouvrir la question « le chevauchement a-t-il été SÉLECTIONNÉ ? » sans règle scellée
(cf. « Ce qu'on ARRÊTE »).
Son génome déclare **64 entrées + 126 sorties dans 172 nœuds** : les blocs se chevauchent sur 18, et
`forward` écrit l'observation dans `H[:, :max_I]` puis lit les logits à partir de `max_I + max_H`
= 46. Vérifié composante par composante (écart 0,0025, qui est la mise à jour récurrente). Un agent
FRAIS n'a pas le défaut (59+108 = 167 ≤ 172) : c'est la lignée du champion. Garde posée
(`assert_no_io_overlap`, classe **E24**), mais **la dette de lecture reste entière** :
1. **[EDR-EVO-004]** conclut « saillance action/canal au PLANCHER sur TOUS les canaux » sur ce
   champion. Une saillance nulle mesurée sur une politique dont un dixième des sorties EST l'entrée
   n'a pas le même sens — il faut RE-LIRE la mesure en séparant les 18 logits partagés des 108 autres.
   C'est peu coûteux (la sonde de saillance existe et est calibrée) et cela peut changer une
   conclusion citée par tout l'arc S2.
2. Les verdicts `PERCEPTION_DECOY` publiés ne sont PAS invalidés (`PerceptionAblatedMamba` permute à
   l'ENTRÉE, donc ablate les deux chemins) — mais les records qui les lisent doivent porter la mention.
3. Ouvrir la question amont : **combien de génomes persistés ont ce chevauchement ?** 348 `.npz` sous
   `data/genomes/` ; le compte est un balayage de trois entiers par fichier.


**P2.47 — ✅ CLOSE (2026-09-08) — le chargement du champion pouvait pointer, en silence, sur un Hall
of Fame VIDE.** Chaîne à trois maillons, tous mesurés, tous corrigés, avec 7 cas de calibration
(`tests/sandbox/test_hall_of_fame_loading.py`) :
1. `tools/evo_memory_inworld.py:51` pose `HOF_PATH` vers un HoF vide **à l'import** — intention
   légitime (tabula rasa d'EVO-003), effet processus-global. Elle CRIE désormais, et signale aussi le
   cas où elle arrive **trop tard** (`persistence` déjà importé) : la redirection est alors sans
   effet, et le bras croit partir de zéro **en partant du champion** ;
2. `load_hall_of_fame` avalait toute exception et rendait « vide » : ABSENT, CORROMPU et VIDE étaient
   indiscernables. Distingue désormais — absent → silencieux (cas nominal du dépôt neuf), illisible →
   lève, en nommant le chemin ET `HOF_PATH` ;
3. `tools/arm_nas` rendait `(0, 0)` — une taille de génome moyenne MESURÉE à zéro. Refuse désormais.

Symptôme qui a mis sur la piste : une sonde annonçait « HoF vide : évoluer d'abord » alors que
`data/hall_of_fame.pkl` contenait ses 10 entrées, **intactes depuis juillet**.

**P2.48 — ⚠️ OUVERTE (2026-09-08) — le Hall of Fame est un `pickle`, et son format n'est pas versionné
au-delà d'un entier.** Trouvé en durcissant son chargement : `pickle.load` sur un artefact local n'est
pas un risque de sécurité ici, mais c'est un format qui **casse silencieusement** quand une classe est
renommée ou déplacée — et l'ancien `except: pass` transformait exactement cela en « HoF vide ». Migrer
vers un format à schéma (les génomes sont déjà persistés en `.npz` ailleurs, 348 fichiers) fermerait
la classe entière. Coût non estimé ; à faire avant toute refonte de `src/seed_ai/mutation.Genome`.


**P2.49 — 🔴 OUVERTE (2026-09-09) — 114 des 272 instruments « calibrés » n'ont AUCUN cas qui atteigne
leur corps : leur certification ne porte que sur leur garde d'entrée.**
<!-- holds_when:grep_present=tests/sandbox/test_perimeter_widening.py::test_the_measured_EXPOSURE_of_head_guard_only_calibration_is_PUBLISHED -->
Mesuré, pas supposé : `tools/hcm_analyzer.py::run_hcm_analysis` était **déclaré CALIBRÉ** et **ne
pouvait pas s'exécuter** — `TypeError` à la ligne 29 sur le contrat de `load_hall_of_fame`, à chaque
appel. Ses deux cas (`empty-cohort:raises`, `guard-before-world`) n'exercent que la garde d'arguments,
qui lève AVANT. Le recompte donne **114/272 (42 %)** de déclarations dans ce cas — 92/248 à la découverte, puis
**+22 que le 10ᵉ élargissement (le VERBE NU) a ajoutées le jour même**, faute d'un cas CORPS-ATTEINT
abordable : il y coûterait un monde. La dette s'AGGRAVE donc pendant qu'on la mesure, et c'est écrit
ici plutôt que masqué. Origine commune : la **7ᵉ passe** (famille `run_*`, 72 fonctions) puis la
**10ᵉ** (verbe nu, 20 fonctions), toutes deux fermées « par garde d'en-tête ».

Ce n'est pas dire que les 92 sont cassées — c'est dire qu'on **ne sait pas**, et que le compteur vert
ne le dit pas. Classe **E19** (un contrôle d'une région ne calibre pas une autre région), transposée du
RÉGIME à la RÉGION DE CODE.

**Ce qu'il faudrait, et son coût.** Un cas CORPS-ATTEINT par instrument, c'est-à-dire un appel à
arguments valides dont la réponse est connue. Pour les 57 simulateurs, cela coûte un monde (cher) ;
pour les 14 orchestrateurs, l'**injection à dose connue** le rend gratuit — c'est la technique qui a
déjà fermé 13 des 24 « instruments de monde ». Chantier à découper, pas à avaler d'un coup.
**Ordre proposé** : (a) les orchestrateurs, par injection ; (b) les instruments dont un record publie
un chiffre ; (c) le reste, ou déclaration explicite que la garde d'entrée suffit, avec sa raison.
**Inventaire mesuré le 2026-09-09** : sur les 114, **70 sont des ORCHESTRATEURS** (ils ne construisent
aucun monde et délèguent à une fonction de module patchable — injection à coût nul), **38 des
SIMULATEURS** (un cas atteignant le corps y coûte un monde), 6 restent à classer.

**Avancement — 10 déclarations sorties de la famille (114 → 104), 34 cas atteignant le corps.**
*Premier lot* : les **trois sondes de demande in-world** (`anticipation`/`composition`/`memory`, qui
portent les chiffres de S2-007 et S2-008) et **trois bancs A/B** (`torch_inworld_ab`,
`torch_binary_gate_heldout_probe`, `torch_gate_persist_ab`).
*Second lot, choisi par la PRIORITÉ (b)* — mesure du nombre de records citant chaque module, plutôt
qu'un ordre de découverte :

- ⭐ **`tools/ablation.py::run_condition` — cité par 61 records**, trois fois plus que le suivant.
  Son corps porte la question dont TOUT dépend : `apply_fn` est-il appliqué à **chaque ère** ? S'il
  ne l'était pas, chaque record d'ablation comparerait un bras intact à un bras intact et rendrait
  sereinement « ce mécanisme ne contribue pas » — le verdict le plus courant de la famille. Aucune
  relecture ne distingue ces deux mondes ; un **compte** les sépare. Vérifié aussi : l'agrégation est
  une moyenne sur les ères (dose connue 2/4/6 → 4.0 exact) et le pool est bien *vivants **et** morts*
  (ne compter que les survivants biaiserait vers le bras que l'ablation est censée dégrader).
  ✅ **DÉFAUT CORRIGÉ le 2026-09-09 (décision prise).** La ligne `np.mean([...]) if pool else 0.0`
  rendait **0.0 proie** sur un pool VIDE — que l'aval lit comme « l'ablation a supprimé le foraging »,
  forme (a) des trois documentées. Le test montrait qu'un pool vide et une cohorte qui n'a **vraiment**
  rien mangé rendaient le **même chiffre**. **Décision : LEVER**, et voici pourquoi c'est la bonne et
  non `nan` ni une moyenne sur les ères restantes — `dead_agents` est initialisé à `[]` puis alimenté
  à **chaque mort**, et `num_agents` est déjà gardé en tête : un pool vide est donc une **anomalie de
  harnais, impossible en fonctionnement normal**, pas un état du monde. Pour un état qui ne peut pas
  se produire, l'échec bruyant est la bonne réponse — et les **trois** appelants dépaquettent un
  2-uplet, donc lever **ne change aucune signature**. Le no-op apparié est gelé : une cohorte qui n'a
  vraiment rien mangé se mesure **encore** à zéro.
- **`substrate_ab.py::compare` (16 records)** — l'appariement est le dispositif : les DEUX backends
  doivent tourner sur CHAQUE seed, sans quoi la différence par ligne mélangerait des mondes
  différents.
  ✅ **DÉFAUT DE DESIGN CORRIGÉ le 2026-09-09 (décision prise), sur les SIX fonctions concernées.**
  `substrate_ab.compare` était à **3 seeds** (`sign_p = 0,25`, plus du double du seuil) et cinq autres
  à **4**. Tous relevés à **5**, le plus petit n conclusif. ⚠️ **Le relèvement est coût-POSITIF** :
  dépenser 3 ou 4 seeds pour n'apprendre **rien** coûte plus cher que 5 pour apprendre quelque chose.
  Les appelants qui passent leurs seeds explicitement sont inchangés — et les records le font tous.
  Indice qui a guidé la décision : `substrate_ab_compositional` était **déjà à 5**, donc quelqu'un
  l'avait su sans le généraliser. **Cliquet posé** :
  `test_EVERY_ab_bench_DEFAULT_is_AT_OR_ABOVE_its_own_power_floor` lit le plancher **à la source**
  (`compute_ab_verdict` le calcule en forme close), donc il suivra un changement de `sign_alpha` ;
  et le fait historique est gelé à part, pour qu'il continue de dire **pourquoi** la correction était
  nécessaire — sans punir la correction.
- **`substrate_ab_compositional.py::compare` et `::sweep` (15 records chacun)** — le banc qui porte le
  KPI `binding_gap`/`comp_rate` de la porte G2. `sweep` déduplique par (hidden, facteur d'init), car
  `normalized` à l'ancrage vaut **exactement** `prod`. La dédup est légitime, mais un `seen` trop
  large avalerait des cellules distinctes **en silence** et la grille publiée aurait des trous que
  personne ne verrait : les **deux** issues sont gelées — dédup quand les facteurs coïncident,
  **aucune** dédup quand ils diffèrent.

⚠️ **DÉFAUT STRUCTUREL TROUVÉ PAR CETTE CALIBRATION.** `compute_ab_verdict` exige la bande **ET**
le test de signe (`sign_p < 0.1`). En séparation PARFAITE `sign_p = 2·0,5ⁿ`, donc **n ≥ 5** est
nécessaire pour qu'un verdict positif soit seulement POSSIBLE. Or **6 des 7** fonctions `compare`
du dépôt tournent par défaut à **4 seeds** (`substrate_ab` à 3) : à ces réglages, aucune amplitude
ne peut produire autre chose que `NEUTRE` — un bras qui ne peut pas réussir, **classe E2**.
**Ce qui innocente les records**, vérifié fichier par fichier : EDR-163 a fait le power-up
(12 seeds, `sign_p` 0,55), EDR-166 déclare ses 4 seeds « sous-puissant » dans ses limites, EDR-172
déclare sa fenêtre VIDE. Aucun négatif fabriqué n'a été publié — les auteurs déclaraient leur n à
la main ; l'instrument, lui, ne le disait pas. **Armé** : `compute_ab_verdict` rend désormais
`n_min_positif` et `peut_conclure`, qui portent sur le **DESIGN** et non sur les données — un
`NEUTRE` à `peut_conclure=False` n'est pas un nul mesuré, c'est une absence de dispositif. Le
drapeau `underpowered` préexistant couvrait déjà le cas dangereux (effet franchissant la bande
sans la puissance) : ce qui manquait était l'effet MINUSCULE à petit n, indiscernable d'un nul
mesuré. Frontière gelée des deux côtés dans
`test_the_POWER_FLOOR_of_compute_ab_verdict_is_frozen_in_CLOSED_FORM`.

⚠️ **À ne pas confondre avec un simple manque de tests** : un instrument non calibré ne se contente pas
d'échouer, il **PRODUIT un résultat**. Ici il n'en produisait aucun — il levait — mais l'appelant
(`multiverse_runner`) avalait la levée dans un `except Exception` et **imprimait une cause fausse**,
donc l'absence devenait un diagnostic.

**P2.50 — ⚠️ OUVERTE (2026-09-09) — deux `hcm_analyzer` et deux `Biosphere3D` cohabitent, et les
doublons divergent.**
<!-- holds_when:path_present=src/graph_rag/hcm_analyzer.py -->
`tools/hcm_analyzer.py` (2026-09-06, calibré, garde d'arguments) et `src/graph_rag/hcm_analyzer.py`
(2026-06-04, sans garde jusqu'à ce jour) définissent tous deux `run_hcm_analysis` ; de même
`src/environments/biosphere.py` et `src/worlds/world_1_stoneage.py` définissent tous deux
`Biosphere3D`. Les deux `hcm_analyzer` portaient **le même défaut de contrat** et ont dû être corrigés
séparément — c'est le coût de la duplication, payé deux fois dans la même passe. En outre
`tools/hcm_analyzer.py` filtre sur `num_inputs == 32` (format « V13 ») alors que le HoF courant ne
contient que du 59/64 : **il ne peut plus rien analyser**, ce que son nouveau refus chiffre désormais
au lieu de le taire. Décision à prendre (suppression du doublon de juin, ou fusion) — non prise ici
parce qu'une suppression dans un arbre PARTAGÉ se demande.

---

**P2.51 — ✅ CLOSE (2026-09-14) — les cellules de CONTRÔLE de quatre records S2 étaient publiées
`SURVIVAL_NEUTRAL` alors que l'instrument les rend INDÉCIDABLES ; les quatre portent désormais la rectification.**

**Décision (a)/(b) tranchée par la docstring de `_degeneracy` elle-même** : ces cellules sont son cas
**(a)** — l'intervention ne s'est PAS appliquée (`W = np.zeros` jamais quitté, politique constante) —
et non son cas (b). `intervention_verified=True` y serait un mensonge. Donc **(b)** : rectifier la
lecture de spécificité, sans toucher aux bras positifs.
**État trouvé** : S2-004 et S2-007 étaient déjà rectifiés par [[EDR-AUDIT-001]] (bandeau +
`corrected_by`) ; S2-005 avait le bandeau mais **pas l'arête** dans le graphe ; S2-008 n'avait
**rien**. Mécanisme de S2-008 vérifié dans la sonde (`composition_demand_world_probe.py:103,114`,
même idiome). **Livré** : bandeau + `corrected_by` sur S2-008, `corrected_by` sur S2-005, `corrects`
d'AUDIT-001 étendu à 005 et 008 avec un addendum daté qui dit aussi ce que l'extension ne dit PAS.
La seule cellule de contrôle authentique de la famille reste « rappel PRÉSENT » de S2-005
(`|W| = 0.909` entraîné) — modèle pour ré-établir la spécificité de S2-008, si un run l'exige un jour.

*Texte d'origine :*
<!-- holds_when:grep_present=.github/workflows/ci.yml::test_cognitive_demand_world_probe -->
Trouvé en calibrant les sondes de demande in-world (P2.49). **Huit tests** de
`tests/test_{cognitive,anticipation,composition,memory}_demand_world_probe.py` affirmaient
`SURVIVAL_NEUTRAL` sur leurs cellules de contrôle ; l'instrument rend `INDETERMINE_DEGENERATE`. Ils
étaient **ROUGES depuis l'armement de la garde de dégénérescence le 2026-07-21** — sept semaines — et
**aucun job de CI ne les lançait**, donc rien ne pouvait le dire. Rectifiés et branchés sur la CI.

**Le dépôt avait déjà le diagnostic, pour UNE des quatre.**
`tools/s2_fallback_rate_probe.py` écrit : *« tout ratio ~1 devient (à juste titre)
`INCONCLUSIVE_DEGENERATE` [...] le "NEUTRE" de S2-004 est ILLISIBLE à tout sigma avec ce
mesureur-SEUIL »*. La mesure de ce jour l'étend aux **trois autres** : même mécanisme, mêmes bras
littéralement identiques.

⚠️ **Ce que ça change pour les records, et c'est le point.** `S2-004`, `S2-005`, `S2-007` et `S2-008`
publient chacun **3 occurrences de `SURVIVAL_NEUTRAL`** sur leurs cellules de contrôle. Une cellule
indécidable n'établit **PAS la SPÉCIFICITÉ** de la demande : elle dit seulement qu'aucun effondrement
n'est détecté. Ce qui TIENT dans ces records est le bras POSITIF (la demande mesurée) ; ce qui ne
tient plus est la lecture « et le contrôle est neutre, donc la demande est spécifique ».
**À faire** : (a) décider si les cellules de contrôle peuvent déclarer `intervention_verified=True` —
le `_degeneracy` prévoit explicitement ce cas de sortie, et c'est la seule façon de rendre un
`X_DECOY` légitime ; (b) sinon, rectifier les quatre records sur ce point précis, sans toucher aux
bras positifs.

**Ce que la passe a livré** : les 8 assertions rectifiées séparent désormais ce qui tient (« aucune
demande n'est détectée ») de ce qui ne tient plus (« donc c'est neutre »), et les 4 fichiers sont
dans `ci.yml` pour que le silence ne se reforme pas.

⚠️ **NEUVIÈME ROUGE de la même famille, trouvé le même jour** — `tests/test_openloop_probe.py::test_ladder_wiring`,
lui aussi absent de la CI. Sa fixture était irréaliste sur **DEUX axes**, et le second n'a été vu
qu'en corrigeant le premier : (1) elle rendait le **même tableau** pour l'intact et les bras ablés,
donc des listes littéralement identiques que `_degeneracy` refuse de trancher ; (2) elle rendait des
survies de **100** alors que le test passe `max_ticks=10` — or le module déclare `ceiling=max_ticks`,
et la garde refusait « les DEUX bras au PLAFOND déclaré », **à juste titre** : survivre 100 ticks
quand l'horizon en compte 10 est impossible.
⚠️ **Correction par la FIXTURE, pas par l'attente.** L'intention des deux cas — « 3 barreaux plats →
neutre », « un barreau s'effondre → sensible » — est valide et vaut d'être testée ; changer l'attente
en `INDETERMINE_DEGENERATE` l'aurait perdue. Les bras diffèrent désormais légèrement à médiane égale
(ce qu'on observe sur des flottants réels) et restent sous le plafond. Fichier branché sur la CI.

---

**P2.52 — 🔴 OUVERTE (2026-09-09) — 121 agrégations rendent une CONSTANTE sur une collection VIDE :
une cohorte vide y est indiscernable d'une cohorte qui a survécu 0 tick.**
<!-- holds_when:path_present=tools/fabricated_defaults_baseline.json -->
Trouvé en appliquant la leçon d'E23 (chercher la **forme**, pas l'instance) après avoir corrigé
`ablation.py::run_condition` : le motif `float(np.median(ages)) if ages else 0.0` est **systémique**.
Mesure sur l'arbre entier hors tests : **147 sites**, dont **49 HONNÊTES** (`None` / `nan` — ils
DISENT « je ne sais pas ») et **98 qui FABRIQUENT** une constante. ⚠️ La détection **AST** en trouve
en réalité **121** — 23 de plus que la regex, qui ratait les formes multi-lignes et `np.std`. C'est
la huitième fois dans ce dépôt qu'un détecteur syntaxique promet plus que ce qu'il voit.

⚠️ **LE PIRE CAS MESURÉ est un défaut à `1.0` sur un RATIO** (`tools/g_fidelity_probe.py`, 3 sites) :
l'absence de donnée y prend **exactement la valeur du résultat nul** — « l'ablation n'a rien fait ».
L'absence n'y devient pas seulement un chiffre, elle devient **la conclusion**. C'est la forme (a) des
trois documentées dans `CLAUDE.md`, et elle a déjà produit des conclusions gravées (`PAS DE RUNG`,
`AUTEL MORT`, `N_EMERGE_PAS`).

**Ce qui est fait** : le 99ᵉ site ne peut plus apparaître. `tools/check_fabricated_defaults.py`
(**porte 14** du hook + étape de CI, baseline gelée à 121, comparaison par **différence d'ensembles**
donc corriger un site ne fait jamais échouer le cliquet), **12 cas** de calibration dont autant de
`spares` que de `fires` — `sum([])` est épargné parce que la somme d'un ensemble vide **est**
arithmétiquement zéro, et un booléen aussi (`bool` est une sous-classe d'`int`, il serait passé pour
une constante numérique sans exclusion explicite).

✅ **(a) FAIT le 2026-09-09 — les défauts à `1.0` sur des RATIOS sont corrigés : 121 → 115.**
Six sites dans `tools/g_fidelity_probe.py`, et le mécanisme est démontré et non supposé. Un `1.0`
fabriqué est **exclu du test de signe** (`eff = [r for r in ratios if r != 1.0]` — les égalités sont
écartées, correctement), **mais il entre dans `n` et dans la médiane** : il durcit la majorité
`2·n_fav > n` **dans les deux sens** et tire la médiane vers 1.0. Un seed sans mesure votait donc
« aucun effet » **deux fois**, et la direction est mécaniquement **vers NEUTRE**.
Corrigé en suivant le précédent déjà établi par `cross_world_transfer` — *« on ne le corrige pas en
silence, on l'ANNONCE »* : un seed sans ratio **ne vote plus** et son absence est **comptée**
(`seeds_sans_mesure`) puisque l'unité de réplication est le seed ; `fidelity_verdict([])` rend
`median_ratio: None` et le verdict `INDETERMINE_SANS_MESURE` ; le diagnostic par tick rend `None`.
**`None` et non `nan`** pour la raison que ce précédent donne : *le nan avale, le None crie*.

⚠️ **ET LE CLIQUET S'EST PRIS EN DÉFAUT LUI-MÊME, le jour de sa livraison.** Keyé par **numéro de
ligne**, corriger six sites en a fait apparaître **trois faux NOUVEAUX** — les légataires situés plus
bas dans le même fichier, simplement décalés. Un cliquet qui crie sur une édition sans rapport finit
désarmé, ce que son propre test affirmait déjà. Clé stabilisée en `chemin::fonction#rang`, avec trois
cas gelés (survie au décalage, distinction de deux sites d'une même fonction, nommage de la fonction
englobante).

🔧 **(b) ENTAMÉ le 2026-09-09 par la cible de meilleur rapport records/site : `demand_marker`.**
**11 records** citent ce module pour **2 sites** seulement — l'instrument FONDATIONNEL du dépôt, celui
que traverse tout verdict de demande within-subject. Mesure : `ablation_verdict([50]*12, [0]*12)`
rend **`X_DEMANDED` avec un ratio de 5,0 × 10¹⁰** et `degenerate = False`.

⚠️ **Ce n'est PAS un faux verdict, et c'est ce qui rend le cas subtil.** Une cohorte ablatée qui
s'éteint face à un intact qui survit **est** le contraste le plus tranché qui soit : le signe est
réel, et le verdict — qui ne lit qu'un seuil — reste valide. C'est l'**AMPLITUDE** qui est fabriquée :
`50 / 1e-9`, fixée par `eps` et non par le monde. Un record qui citerait « ratio = 5e10 » citerait un
artefact d'epsilon comme une mesure.
**Remède : celui que le dépôt avait DÉJÀ tranché** dans `cross_world_transfer`
(`n_denominateurs_eteints`) — *« on ne le corrige pas en silence, on l'ANNONCE »*. L'instrument
fondationnel, lui, ne l'avait pas. `ablation_verdict` publie désormais `denominateur_eteint`,
`bras_vide`, `n_intact`, `n_ablated` et surtout **`ratio_est_une_borne`**, qui réunit les trois cas où
le ratio n'est pas une mesure — dénominateur éteint, bras vide, intact censuré. Ce dernier cas était
déjà connu (« le ratio est une borne INFÉRIEURE », dit sa docstring) : le drapeau **rejoint** ce
savoir au lieu de le dupliquer. 4 cas gelés, dont le **no-op apparié** — sur un contraste ordinaire
(50 vs 25) le drapeau reste FAUX, sans quoi un drapeau levé en permanence ne distinguerait rien.

✅ **(b) POURSUIVI le 2026-09-09 : `substrate_world_ab` (6 records, 6 sites) — 114 → 108.**
Appliqué le **partage déjà tranché** pour `ablation.py` plutôt qu'un jugement au cas par cas :
**LEVER** là où l'état est impossible, **`None`** pour un champ de rapport. `measure_survival` lève
désormais sur une cohorte introuvable (mêmes raisons : `dead_agents` alimenté à chaque mort,
`num_agents` gardé en tête → anomalie de harnais, pas état du monde) ; les cinq médianes de rapport
rendent `None`. ⚠️ Conséquence **assumée et voulue** : un `None` formaté par `:.1f` lèvera — c'est
précisément *« le nan avale, le None crie »*, et c'est préférable à imprimer `med=0.0`.

🔧 **MÉCANISME AJOUTÉ AU CLIQUET, trouvé en l'UTILISANT : `NOT_A_MEASURE`.**
`src/swarm/consensus.py` remplit les NaN d'un vecteur de logits **avant un softmax** : quand tout est
NaN, remplir par `0.0` rend le softmax **uniforme** — aucune préférence, la réponse correcte d'un vote
sans information. Ce n'est pas une mesure fabriquée, c'est une **valeur de remplissage**. Le cliquet
ne sait pas distinguer « agrégation qui MESURE » de « agrégation qui REMPLIT », et un cliquet à faux
positifs finit désarmé — c'est écrit dans son propre test. Doctrine du dépôt appliquée : **faire
DÉCLARER l'auteur plutôt que deviner** (comme `NOT_AN_INSTRUMENT`). Une déclaration exige un **motif
écrit ≥ 60 caractères** — le cliquet **échoue** sinon plutôt que d'ignorer, ce qui laisserait croire
à l'auteur qu'il a déclaré ce qu'il n'a pas déclaré — sort du **compte** de dette, et reste
**RAPPORTÉE**. ⚠️ Et une `sites_a_corriger()` expose la **source unique** : mes deux premiers tests
refaisaient le filtre à la main et voyaient donc le site déclaré comme NOUVEAU — un filtre dupliqué
est un filtre qui divergera.

✅ **(b) POURSUIVI — les DEUX gros volumes, 108 → 85.**

- **`substrate_ab_compositional` (15 records, 17 sites), qui porte le KPI de la porte G2.** Trois
  familles, lues dans le CODE et non décidées au jugé. ⚠️ **7 des 17 étaient du CODE MORT** :
  `qb = max(1, compo_trials // 4) if compo_trials else 0` et la garde d'en-tête exige
  `compo_trials > 0`, donc `qb ≥ 1` **toujours** — le `else 0.0` y est inatteignable. Les retirer
  plutôt que d'y écrire `None` compte : **maquiller du code mort en dette résorbée serait un faux
  vert**, et la dette réelle de ce fichier était de **10**, pas 17. Les 4 branches `qa` sont bien
  vivantes (la docstring dit *« warmup_trials=0 → phase B seule »*, donc l'absence de warmup est une
  configuration SUPPORTÉE, et `0.0` y affirmait un indice de discrimination pour une phase
  INEXISTANTE) ; elles rendent `None`, avec les 6 branches gardées par `.size`. Le fichier
  **anticipait déjà** ce `None` en deux endroits (`if c["compo_didx_end"] is not None`) : on
  généralise **son propre idiome**, et les deux agrégations qui manquaient sont gardées.
- **`lewis_survival_sweep` (13 records) — 6 sites sur 16, ceux qui alimentent un VERDICT.** Le plus
  dangereux était `medians`, qui entre dans `verdict_fn` : un `0.0` fabriqué y devient une **survie
  médiane nulle dans un verdict de TENDANCE**, capable d'en **inverser le sens**. ⚠️ Plutôt que cinq
  `None` disséminés, **UNE garde en tête** qui NOMME le niveau fautif rend les cinq branches
  inatteignables. Et le pool suit la décision déjà prise deux fois — **lever** —, d'autant qu'il
  corrompait **déjà** le sweep en silence : `ticks.extend(...)` n'ajoutait rien pour l'ère perdue,
  donc la médiane du niveau se calculait sur moins d'ères sans que personne ne le sache.

**Ce qui reste** : **85 légataires**, dont **10 statistiques de rapport** dans
`lewis_survival_sweep` — aucune n'alimente un verdict, d'où leur report assumé. Ils ne se corrigent pas en masse — chacun demande de décider
entre `None`/`nan` (« je ne sais pas ») et **lever** (si l'état est impossible, comme tranché pour
`ablation.py`). **Prochaines cibles de (b)**, par poids mesuré : `s2_demand.py` (10 records, 3 sites),
`src/swarm/consensus.py` (10 records, 1 site), `substrate_world_ab.py` (6 records, 6 sites), puis les
deux gros volumes `substrate_ab_compositional.py` (15 records, 17 sites) et `lewis_survival_sweep.py`
(13 records, 16 sites). **(c)** le reste.
Précédent à suivre : `tools/s2_openloop_probe.py`, corrigé avant cette passe, dont le commentaire
explique déjà la faute — ce cliquet généralise ce correctif au lieu de le laisser isolé.

**P2.56 — 🟠 P2.49 RAFFINEE (2026-09-10) : la dette de 103 se scinde en 62 DECLARATIVES + 39 MUETTES**

La dette « garde-seule » etait lue dans les DECLARATIONS de `CALIBRATED`, pas dans les tests. Elle
melangeait donc deux choses dont **le prix differe d'un facteur enorme** :

* **62 declarations SOUS-DECLAREES** — un test AILLEURS importe le symbole DEPUIS SON MODULE et
  atteint son corps. Exemple fondateur : `_verdict_forage` etait declare `["empty:raises"]` alors
  que ses QUATRE branches etaient confrontees a des reponses connues dans
  `tests/sandbox/test_edr105_forage_funnel.py` depuis des mois. **Coût de resorption : une ligne.**
* **39 declarations REELLEMENT MUETTES** — aucun test n'importe le symbole. **Coût : un monde**,
  ou une injection d'orchestrateur.

⚠️ **L'instrument qui mesure cette dette a failli publier un chiffre FAUX, du defaut que ce depot
connait le mieux.** La premiere version appariait par NOM NU : les trois declarations `compare`
(defini dans 10 fichiers) pointaient les DEUX MEMES fichiers de test, qui n'en testent qu'un. Corrige
par analyse AST des IMPORTS (`from tools.x import nom`, ou `import tools.x`), seule facon de savoir
QUEL `compare` un test importe. Le script vit dans le scratchpad ; **le porter dans le depot est la
suite naturelle** — la scission 62/39 devrait etre RECOMPUTEE et non recopiee (cf. porte 8).

**AVANCEMENT 2026-09-22 (session loop 766eabae) : l'instrument v3 est DANS LE DÉPÔT, et les deux comptes sont recomputés à
chaque appel.** `tools/check_calibration_reach.py` (AST strict : `nom(` après `from m import nom [as a]`, `y.nom(` après
`import m [as y]` / `from p import m` ; un appel INDIRECT ne compte pas — choix déclaré ; une clé NUE en collision est
NON RÉSOLUE, rapportée, jamais comptée d'un côté) ; même expression « garde-seule » que `test_perimeter_widening` (égalité
gelée par un test). Mesuré à la livraison : **305 déclarations, 81 garde-seule = 38 DÉCLARATIVES + 43 MUETTES + 0 non résolue** (284 fichiers de tests balayés). Baseline gelée dans la même passe (`tools/calibration_reach_baseline.json` : la liste des 43 muettes ; toute NOUVELLE muette
bloque, une résorbée est rapportée) ; 7 cas (`tests/sandbox/test_calibration_reach.py`) dont le verdict du cliquet à réponse connue.
⚠️ Pas encore branché sur le hook (porte 18 candidate) : brancher une porte exige son témoin de mutation (porte 15) et touche
`tools/hooks/pre-commit` + le compte `portes_hook` — à faire dans une passe dédiée, coordonnée (le hook est partagé).
**Même jour, (b) entamé** : six orchestrateurs muets de la famille throw-gate (`compare`, `compare_debias`, `compare_density`,
`compare_warmstart`, `compare_rp_sweep` de `torch_throw_gate_inworld_ab`, `compare` de `torch_binary_gate_probe`) reçoivent une
injection à dose connue (`tests/sandbox/test_torch_gate_orchestrators_injection.py`, 8 cas, 0 monde : ON +0,30 vs SHUFFLE +0,05 sur
5 seeds → `GRADIENT_GAGNE`, no-op EXACT → `NEUTRE`, n = 3 → `NEUTRE` + `underpowered`, bras séparés par `penalty` / `shaping` /
`warm_w` / `prey_count`, label mémorisé → `verdict_vs_shuffle` NEUTRE, gap indéfini COMPTÉ). Puis trois autres (`tests/sandbox/test_mute_orchestrators_injection_2.py`, 6 cas, 0 monde) :
`run_diagnostic` (grille 2 régimes × 3 agents — la sentinelle `run_condition` journalise politique, génome, config du régime, K,
seed ; E8 : la config de CHAQUE régime est celle de la grille), `probe_substrate_attractor` (trajectoires connues, `measure_convergence`
RÉEL : P1 {off n, action n, H 0}, P2 = n, P3 {1, 1, T/2}), `run_probe` vertical (Z_UTILISE / Z_INERTE prédits, `survival_ratio` 1,2).
Puis trois instruments (`tests/sandbox/test_mute_orchestrators_injection_3.py`, 4 cas, 0 monde) : `transfer_ratio.measure` (ratio 2,0
prédit, bras invalide ignoré et compté, aucun bras valide → `None`), `measured_floor` (24 vies = seed + 5 : médiane et vies
prédites exactement, politique corps-seul de K), `probe_genome_free_channels` (clones à lr = 0, trajectoire transmise, trajectoire
vide → `None`). Recomputé après : **81 garde-seule = 50 déclaratives + 31 muettes**, baseline resserrée trois fois
(43 → 37 → 34 → 31 ; la porte a rapporté chaque résorption avant qu'on la gèle). Leurs douze déclarations restent à ré-écrire
(fenêtre sur le fichier partagé), avec celle du nouvel instrument `run_s2_paired`. **Fait le 2026-09-22, 22:30** (fenêtre
ouverte par agagi-52 après d7) : les 12 déclarations sont RÉ-ÉCRITES d'après ce que leurs témoins affirment (cas nommés :
dose → verdict, no-op exact, n = 3 → underpowered, label mémorisé, gap indéfini compté, bras séparés par paramètre, grille
complète + E8, P1/P2/P3, Z_UTILISE / Z_INERTE, ratio 2,0 / None, vies prédites, clones à lr 0) et `run_s2_paired` déclaré
(6 cas). Recomputé après : **306 déclarations, 69 garde-seule = 38 déclaratives + 31 muettes** — les 12 ont quitté
le périmètre garde-seule ; cliquet de calibration : 240 détectés / 232 calibrés / 2 légataires.

**Fournées 4–9 (2026-09-22, après 4b68b121) : les 31 MUETTES sont à ZÉRO** — 19 simulateurs sous CLASSE de monde
factice injectée dans le module (`_world`, `Biosphere3D`, `FamineWorld`, `AgriculturalWorld`, `WORLDS[clé]` remplacés
par un environnement minimal à dose connue : cohorte de dicts, `step()` qui compte les ticks et tue la cohorte à un tick
connu), 6 runners de monde de plus avec leurs maillons coûteux en enregistreurs (`train_population` : 24 têtes × 5000
pas, `_setup3`, `seed_at`), les 3 sondes d'`evo_memory_inworld` sous `MemoryDemandBiosphere` factice (dont le logit
d'attaque par un `MambaBatchModel.forward` remplacé qui rend des logits CONNUS, restauration vérifiée), `run_retention_map`
en ORCHESTRATEUR injecté (quatre maillons, chemin de sortie en dur capturé par un `chdir` temporaire) et les 2 fonctions
pures (`run_bptt_act` : W nul → 0,0 et gradient −0,25, fil direct → 1,0 ; `run_refgame` : déterminisme, code effondré à
1 epoch, `acc ≤ injectivité`). Six fichiers, 36 tests, 0 monde réel, ~2 s par fournée :
`tests/sandbox/test_mute_simulators_fake_world.py`, `_2.py`, `_3.py`, `_4.py`, `_5.py`, `_6.py`. Ce qui est jugé : la
boucle d'ères, les réglages de régime POSÉS sur le monde (E8), l'état global posé puis RESTAURÉ même sur exception (E5 :
`persistence.SPECIATE`, `forward`, logger), ce qui COMPTE ou est IGNORÉ (tués des seuls survivants, agent sans génome,
agent sans apex perçu, mort en attaquant = engagé), les agrégats et les valeurs d'absence publiées telles quelles (0,0 /
1,0 / `nan` / `None` sans fichier : défauts légataires de porte 14, documentés, jamais corrigés en silence). Les 31
re-déclarées d'après leurs témoins (compte de clés inchangé). Portée recomputée : **38 garde-seule = 38 déclaratives + 0 muette** ; baseline gelée VIDE (comme le
cliquet de calibration le 2026-09-01) ; porte 2 : 240 / 232 / 2 inchangés. Suite naturelle : la porte 18 (brancher
`tools/check_calibration_reach.py` sur le hook — aucune NOUVELLE muette), passe dédiée avec témoin de mutation.

**(a) SOLDÉE le 2026-09-23 : 306 déclarations, 0 garde-seule** (`python
tools/check_calibration_reach.py`, recomputé). Les 32 sous-déclarées re-déclarées d'après ce que leurs témoins AFFIRMENT
(extraction AST des appels et assertions de chaque témoin, `witness_extract` ; un smoke est annoncé `:smoke`, une réponse
connue est nommée — `adaptatif:succes~=max-fixe-a-cout<0.6`, `champion>tabula-rasa:condition-necessaire`,
`ablation:effondre-SEULEMENT-sous-demande`, `repro:appariee-exacte`…). ⚠️ **Trouvé en le faisant (E4 occ. 9) : six
« déclaratives » ne l'étaient que par un appel SOUS `pytest.raises`** (les quatre `s2_*::run_arm`, `run_curriculum`,
`run_world_era`) — l'instrument de portée comptait un refus à la garde comme une atteinte du corps, donc 4b68b121
annonçait 6 muettes de moins qu'il n'y en avait. Corrigé dans l'outil (un appel sous `raises` n'atteint pas ; cas gelé
`test_a_call_under_pytest_raises_does_NOT_reach_the_body…`), les six résorbées en fournée 10
(`tests/sandbox/test_mute_orchestrators_injection_4.py` : seams `_bassin_cohort` / `phase1` / `phase2` / `credit_variant`
/ `effective_reward` en enregistreurs — variante PUBLIÉE et transmise (E8), ordre des maillons, bras gelé sans phase 1,
cohorte froide sans bassin ; `run_curriculum` orchestré sous `chdir` ; `run_world_era` à classe de monde) et
re-déclarées. Le mode `--index` (juger ce qui SERA committé : `git ls-files -s` + `cat-file --batch`) est dans l'outil
avec ses témoins (index synthétique, plomberie git réelle sur index temporaire, muette neuve injectée → rouge). **Porte 18
LIVRÉE le 2026-09-24** (passe dédiée, après la fusion PM `79af2944` ; numéro attribué par le PM) : bloc dans
`tools/hooks/pre-commit` ET dans la copie ACTIVE `.git/hooks/pre-commit` (non versionnée — les deux, sinon l'arbre
annonce 19 portes et le hook en exécute 18), déclenchée par tout test / le fichier de calibration / l'outil / sa
baseline stagés (`--diff-filter` incluant **D** : une SUPPRESSION de test peut rendre une déclaration muette),
`--index` donc jugeant ce qui SERA committé, ~3 s. Calibrée dans la même passe (porte 15) : **3 mutations sur 3
TUÉES, témoins intacts verts** — périmètre vidé (verte à vide), « une muette neuve n'est jamais nouvelle » (vue,
jamais bloquée), mode index lisant le disque (la faille même de la porte 4). `portes_hook` **18 → 19**, recomputé
depuis le hook. **P2.56 est CLOSE** : (a), (b) et la porte.
**Suite** : (a) ✅ FAIT le 2026-09-23 (32 re-déclarées + 6 démasquées, ci-dessus) — re-déclarer d'après ce que leurs
témoins AFFIRMENT (une ligne chacune, dans `test_instrument_calibration.py`) ; (b) ✅ FAIT le 2026-09-22 (31 → 0 par les fournées 4–9, ci-dessus) — injection
à dose connue pour les orchestrateurs, un monde FACTICE pour les simulateurs ; aucune déclaration « la garde suffit » n'a été nécessaire.

**AVANCEMENT 2026-09-14 (tick 3) : 103 → 80.** ⚠️ **La scission 62/39 était encore surcomptée** :
la v2 créditait `import tools.x` de TOUS les symboles de `x`, même jamais appelés (elle comptait
SIX fonctions de `warmstart_evolution_inworld` pour un test qui en appelle une). Mesure STRICTE
(v3 : le symbole doit être APPELÉ, par AST — `nom(` après `from m import nom`, ou `y.nom(` après
`import m as y`) : **48 déclaratives / 48 muettes** à 96 ; **35 / 45 à 80**. Treize re-déclarées
d'après ce que leurs témoins AFFIRMENT (dont `run_ablation_map`, 15 records : une injection à dose
connue — within 5.0, between 10.0, `PERCEPTION_DEMANDED` — que la déclaration taisait) ; trois
orchestrateurs de `substrate_world_ab` (11 records) dont les seuls témoins étaient des tests de
SIGNATURE reçoivent une **injection à dose connue** (`compare_backends` : +20 → GRADIENT_GAGNE,
apparié même seed ; `compare_arms` : trois verdicts en forme close + no-op NEUTRE ×3 ;
`sweep_lr_torch` : une sous-classe par lr, dose lue). `measure_survival` reste muet : c'est le
maillon qui simule.

**AVANCEMENT antérieur : 103 → 96.** Le banc G2 (`substrate_ab_compositional`, 31 records) était
déclaratif pour ses QUATRE fonctions — dont un vrai contrôle positif à dose connue
(`gate_mode="oracle", oracle_bias=8.0` → `binding_gap_end > 0.5`) que la déclaration taisait. Et
**deux clés en DOUBLE dans `CALIBRATED`** : `run_hcm_analysis` déclaré riche (CORPS-ATTEINT, 4 cas)
puis, 220 lignes plus bas, pauvre — dans un dict littéral la DERNIÈRE gagne, donc l'instrument
comptait garde-seule à tort. Garde gelée : `test_CALIBRATED_n_a_AUCUNE_cle_en_double` (AST : le
dict évalué ne peut plus voir le doublon).

**PREMIERE RESORPTION, et elle rapporte plus que son compte** : `tools/lewis_survival_sweep.py`
(49 records, le module le plus cite du lot) — 2 declarations re-declarees, **103 -> 101**, et DEUX
DEFAUTS REELS trouves dans les corps enfin regardes :
* `_verdict_landing` sur **UN SEUL bras** rendait `AFFORDANCE INERTE` — `delta` vaut 0 par
  construction et `slope` etait FABRIQUE a `0.0`. Un verdict de fond, negatif, tire d'un point.
  **Classe E14** : le jumeau structurel `_verdict_capacity` porte cette garde depuis le 2026-09-06 et
  elle n'avait jamais ete retro-appliquee a ses DEUX freres.
* `_verdict_forage` sur une agregation **TOUT NAN** rendait `FORAGE SUFFISANT` — `nan < 0.5` vaut
  False, donc les trois etages de la cascade tombent et le verdict de QUEUE sort. C'est un **positif**
  fabrique : plus rare dans ce depot, donc **plus dangereux**, parce qu'il ne ressemble pas aux
  autres resultats. Et le `nan` en entree est exactement ce que la porte 14 demande de RENDRE en cas
  d'absence : le consommer comme une mesure casse la chaine au maillon suivant.

**ORDRE DE TRAVAIL, par poids de records mesure** : `substrate_ab_compositional.py` (31 records,
4 declarations), `substrate_ab.py` (17, 1), `evolve_ceiling_probe.py` (16, 1), `map_elites_compare.py`
(15, 4), `s2_demand_ablation.py` (15, 1), `warmstart_evolution_inworld.py` (11, 6),
`substrate_world_ab.py` (11, 4), `anticipation_bench.py` (11, 2). Commencer par verifier si la dette
est DECLARATIVE (une ligne) avant d'ecrire un test.

**P2.57 — ✅ CLOSE (2026-09-14) : 2e élargissement de la porte 14, sur l'IDENTIFICATION — 26 révélés, 16 réglés, 10 gelés**

Trouve en resorbant P2.56. `check_fabricated_defaults` detecte
`agregation if collection else CONSTANTE` — la veracite d'une collection. Il ne voit NI
`float(np.polyfit(x, y, 1)[0]) if len(arms) >= 2 else 0.0` (une COMPARAISON DE LONGUEUR), NI une
cascade de comparaisons sur `nan` (aucune agregation en vue). Les deux defauts de
`lewis_survival_sweep.py` etaient donc **structurellement invisibles** a la porte qui existe pour ca.

**MESURÉ le 2026-09-14, et le diagnostic du 09-10 était FAUX sur la cause** : le cas Lewis
échappait au cliquet non pas à cause de la condition (`len(...) >= 2`, que le détecteur ne regarde
jamais) mais parce que `np.polyfit(...)[0]` n'était pas une agrégation LISTÉE. Mesure large :
**167 sites `<appel> if … else <constante>`, 86 vus, 81 non vus** — et parmi les non vus, ~25
étaient EXACTEMENT l'agrégation cherchée, cachée par la façon dont le cliquet l'IDENTIFIAIT :
module aliasé (`import statistics as st` → `st.mean`, `_np.median`), MÉTHODE numpy (`a.std()`,
`cons[m].mean()`), nom NU (`stdev`), INDEXAGE d'un appel (`polyfit(...)[0]`). C'est l'angle mort
« comment il identifie » payé trois fois par le cliquet-frère, reproduit à l'identique.

**Élargi sur l'identification ; 26 sites révélés, 0 glissement de rang ; 16 réglés dans la passe :**
* **la FAMILLE `eval_harness`** — `powered_eval` + HUIT copies du même `_stats`
  (`aligned_selection`, `fiabiliser`, `lang_speciation`, `mem_nas`, `nas_memory`, `nas_rich`,
  `reconfirm_047`, `speciation`), toutes vers `verdict`. Avec UN réplicat, `std = 0` → Welch
  `t = 0, d = 0` → « NON significatif (bruit) » : **un nul fabriqué depuis n = 1, sur neuf outils**.
  `std` rend `None`, `welch` REFUSE l'indéfini en nommant la condition et son n, les 8 copies
  reçoivent la même substitution (chercher la FORME, pas l'instance). 3 témoins gelés.
* **`lewis_survival_sweep`** — `_verdict_evolve_nav` gardait le VIDE mais pas UNE génération
  (`first == last` → « SUBSTRAT BLOQUÉ », un négatif de fond tiré d'un point ; `slope` fabriquée à
  0 et PUBLIÉE dans le JSON) ; deux branches mortes derrière les gardes de `_verdict_landing` /
  `_verdict_capacity` retirées.
* **`anticipation_bench`** (11 records) — 3 branches MORTES derrière les gardes d'en-tête
  existantes (`run_bench` lève sur `len(seeds) == 0`), retirées.
* `mamba_agent.forward` — borne de boucle, déclarée `NOT_A_MEASURE` avec son motif.

**Baseline 85 → 95** (10 gelés) **→ 89 le 2026-09-14 (tick 2)**. Les six sites de BINDING sont
RÉGLÉS, et ils cachaient une découverte : **le contrôle NUL de `craft_or_starve_edr` est MORT**.
`null_metronome_gap` (métronome open-loop, borne nulle du binding) à `T = 200` — la valeur par
défaut de `Params` — n'a **0 vivant sur 64** au dernier quart, pour E0 = 16, 32 et 64. Ses deux
masques étaient vides, `p1 = p0 = 0.0` par défaut, et « gap ≈ 0 » était `0 − 0` ; le test
`test_null_metronome_gap_is_low` gelait ce zéro. Un contrôle qui ne survit pas jusqu'à la mesure
n'est pas un contrôle (E1). Aucun record ne s'en réclame (grep `metronome` sur `docs/EDR` : vide) ;
`recalibrate_learner` est un diagnostic SUPERSÉDÉ. Le nul n'est mesurable qu'à T ≤ 40, où il vaut
0 **pour de vrai** (p1 = p0 = 1 : le métronome consomme à chaque S2).
Remède, celui d'`ablation_verdict` : **annoncer sans altérer le verdict**. Les probabilités
conditionnelles indéfinies rendent `None`, le gap `None` ; chaque agrégation applique la règle de
l'auteur (kchain L386, « indéfini = ne compose pas ») **explicitement** via `_gaps_pour_verdict`
et publie `n_gap_indefini` ; `null_metronome_gap` lève sur un métronome mort et
`recalibrate_learner` publie `null_mesure: False` au lieu d'avaler. Seul changement numérique : là
où l'ancien gap valait `−p0` (conditionnement jamais observé), il vaut 0 pour le verdict — l'ancienne
valeur n'était pas une mesure. `_gaps_pour_verdict` est un instrument (la porte 2 l'a vu, en
collision ×3) : calibré à réponse connue, un jeu par exemplaire + identité des trois.

Avant ce tick, la liste des six :
`craft_or_starve_edr::_binding_from_log` ×2, `kchain_edr::binding_gap` ×2,
`torch_binary_gate_probe::_binding_gap` ×2 — `cons[m1].mean() if m1.any() else 0.0` : une
probabilité conditionnelle sans aucun événement conditionnant devient 0 (« jamais Y sachant X »), et
`binding_gap = p1 − p0` en hérite. **Cibles prioritaires de P2.52 (b)** : le gap devrait rendre
`None` et l'aval le refuser — mais l'aval est un verdict d'EDR, donc à lire avant de toucher.

**FORME RATIO MESURÉE (tick 3, 2026-09-14) : 27 sites `a / b if … else CONSTANTE` dans 15
fichiers — 21 à `0.0`, 6 à `1.0`.** Les six à 1.0 sont la pire forme et sont RÉGLÉS, tous lus :
* `life_score_contamination_probe` — tau-b `else 1.0` (dénominateur nul = tau INDÉFINI, pas
  « corrélation parfaite »), jaccard `else 1.0` (union vide), part de masse `else 0.0`. ⚠️
  L'agrégation lisait `med_t == 1.0 and med_j == 1.0 → METRIQUE_INERTE` : un tau fabriqué aurait
  CONCLU. Les None sont filtrés et comptés (`n_indefini`), un lot entièrement indéfini rend
  `INDETERMINE_METRIQUE_NON_MESUREE`.
* `s2_regime_diagnostic` — `lift = 1.0` quand les DEUX régimes sont au plancher : 0/0 n'est pas
  « aucun lift ». None ; `lift_ok` reste False ; verdict inchangé.
* `prerequisite_recovery_probe` — précision 1.0 sans AUCUNE arête récupérée, rappel 1.0 sans
  aucune imposée, et le go/no-go SP-3 lisait `== 1.0` : **un PASS fabriqué sur zéro arête**. None.
* **`eval_harness.welch`** (9 outils) — `t = 0 si se ≤ 1e-12` : deux échantillons CONSTANTS et
  DIFFÉRENTS (A = [1,1,1], B = [2,2,2]) rendaient « NON significatif (bruit) ». Une décision GELÉE
  par un test qui disait « l'instrument refuse de prononcer » — mais « NON significatif » n'est pas
  un refus, c'est un prononcé. Séparé en deux, et les deux gelés : n < 2 → REFUS (levée) ; n ≥ 2 à
  variance nulle et moyennes distinctes → séparation parfaite (±inf, significatif).
* ⚠️ **Forme (b) trouvée en passant** : `backend/runs_service._welch` faisait `except Exception`
  autour de l'import de la source — la ValueError que `welch` lève sur n < 2 y était AVALÉE et le
  repli fabricant reprenait. `except ImportError` seulement, repli aligné.

**Les 21 ratios à `0.0` restent NON DÉTECTÉS par la porte 14** (le détecteur ne voit pas les
divisions). Un élargissement flaguerait ~10 sites légitimes (mémoire RSS dans `doctor.py`,
combinatoire dans `data_service.py`, moyenne dans `ground_truth_worlds.py`) : à faire avec
`NOT_A_MEASURE` dès le départ, ou pas du tout. Mesuré, pas encore décidé.

**RESTE HORS PÉRIMÈTRE, chiffré et différé** : `max` (16), `min` (7), `np.argmax` (13) —
`max(xs) if xs else 0` est discutable au cas par cas (clamp ? borne ? mesure ?) et les compter sans
les lire fabriquerait des faux positifs en masse. **Troisième forme vue en passant, non mesurée** :
le RATIO `a / b if b > 0 else 0.0` (`avoidance = avoided / faced if faced > 0 else 0.0` dans
`anticipation_bench.run_bench`) — « 0 danger affronté sur 0 » devient « 0 % d'évitement ». Le
détecteur ne voit pas les divisions. À MESURER avant d'élargir, comme cette fois.

**Avant d'elargir, MESURER** : chaque elargissement du cliquet-frere (calibration) a revele de la
dette REELLE, et celui-ci en revelera. La forme `... if len(<nom>) <op> <entier> else <constante>`
est detectable par AST au meme prix que l'existante. ⚠️ Attention au faux positif legitime : une
comparaison de longueur peut garder un CALCUL et non une MESURE (un `[:n]`, un pas de boucle) —
prevoir `NOT_A_MEASURE` des le depart, comme la porte 14 l'a appris en tirant sur un assainisseur de
softmax.

**P2.58 — ✅ CLOSE (2026-09-14) : la redirection de HoF inopérante ne FUIT plus vers les sous-processus**

**Mesuré** : seul, `tests/sandbox/test_evo_memory_inworld.py` redirige bien (message « redirigé ») ; dans
la suite complète (ou via `test_instrument_calibration`, qui importe `persistence` avant), la
redirection est inopérante et l'avertissement crie — comme prévu — mais **aucun test n'y lit le HoF**
(injections et monkeypatch partout ; `test_hall_of_fame_loading` impose son chemin explicitement).
Aucun verdict n'en dépend. **Défaut réel trouvé en lisant** : dans le cas inopérant, le module POSAIT
quand même `HOF_PATH` dans l'environnement — sans effet ici, mais **hérité par tout sous-processus**
(pytest du harnais de mutation, jobs), qui aurait lu un HoF VIDE en croyant lire le vrai : le défaut
que l'avertissement dénonce, déplacé d'un processus. Corrigé (la variable n'est posée que si la
redirection s'applique) ; paire gelée en sous-processus, seule façon d'avoir un interprète frais par
ordre d'import (`test_la_redirection_INOPERANTE_ne_pose_PAS_HOF_PATH` / `..._OPERANTE_pose_...`).

*Texte d'origine :*

`tests/sandbox/test_evo_memory_inworld.py` (ou son module) imprime a l'import :
« ATTENTION : `src.seed_ai.persistence` est deja importe, la redirection HOF_PATH vers un HoF VIDE est
SANS EFFET -- ce processus lira le VRAI Hall of Fame. » Le message apparait des qu'on importe
`tests.sandbox.test_instrument_calibration` dans le meme processus. **Le garde-fou fait son travail**
(il ANNONCE au lieu de se taire, ce qui est exactement la bonne conception) mais la consequence n'est
pas suivie : un test qui croit tourner sur un HoF vide tourne sur le vrai. A verifier : quels tests
sont concernes, et si l'un d'eux publie un verdict.

**P2.53 — ✅ CLOSE (2026-09-09) : le CLIQUET DES CLIQUETS, et ce qu'il reste a en tirer**

`tools/check_gate_mutation.py` (porte 15) casse chaque porte du hook d'UNE ligne, **en mémoire**
(l'arbre est partagé : jamais sur disque), et exige qu'au moins un témoin ROUGISSE. C'est la mesure
que **deux cliquets déclaraient hors de portée** — `check_guard_negative_cases` et `check_test_census`
écrivent tous deux « ce test discrimine-t-il ? […] demanderait du test de mutation, qu'on ne proxifie
pas ». La décision de ne pas proxifier était juste ; l'impossibilité, non.

**Mesure de livraison : 14 portes, 17 mutations, 4 défauts RÉELS au premier tir.** Trois portes dont
le verdict BLOQUANT n'avait aucun contre-exemple (`orphans` porte 1, `scan_collisions` porte 2, le
report de la porte 6) et un test qui PUNISSAIT son propre correctif (porte 14). Détail dans
`docs/REF/REGISTRE_ERREURS.md`, E1 occurrence méta et classe neuve **E25**.

**CE QUI RESTE OUVERT, et c'est écrit dans le module lui-même :**
1. **Une porte est couverte par les mutations DÉCLARÉES, pas par une exploration de son espace de
   sabotage.** 17 mutations pour 14 portes : la plupart n'en ont qu'UNE. Une seconde mutation par
   porte, visant une autre branche décisive, est du travail à coût de run nul — et le premier tir
   suggère qu'il paierait (c'est en rendant les témoins de la porte 14 verts qu'un SECOND survivant
   est apparu, sur la fonction centrale du cliquet écrit le jour même).
2. **La mutation vit en MÉMOIRE, donc un témoin qui lit le SOURCE SUR DISQUE ne peut pas la voir.**
   Les témoins « le cliquet est-il branché dans le hook ? » sont structurellement incapables de tuer
   un mutant. Conservateur dans le bon sens (le harnais crie au lieu de se taire) mais à savoir en
   lisant un verdict `SURVECUE`.
3. **Coût** : ~15 s par porte, ~4 min pour les 14. Le hook n'appelle QUE les portes dont le cliquet ou
   les témoins sont stagés (`--pour-fichiers`) ; la CI les fait toutes.

**P2.54 — ✅ CLOSE (2026-09-09) : la CI lance la suite PAR REPERTOIRE, 6 rouges legataires en sont sortis**

`ci.yml` prenait une **liste NOMMÉE de 16 fichiers**, jamais un répertoire : **1937 tests sur 2059
(94 %)** n'étaient lancés par aucun job. Le job `suite-complete` lance `tests/`.

**Coût MESURÉ sur machine à charge connue : 2611 collectés, 2597 passés, 7 skips, 25 min 44 s** — et
la mesure a été prise PENDANT le harnais de mutation, donc c'est un MAJORANT. ⚠️ Une première mesure
du 2026-09-08 avait rendu **8 h 30**, prise pendant que seize agents tournaient sur la même machine :
E12 appliquée au COÛT, et elle inversait la décision (« impossible en CI » → « 26 minutes »).

**Les six rouges trouvés en branchant, tous corrigés dans la même passe** : trois fixtures
d'`tests/test_agi_taxonomy.py` périmées par deux durcissements de la porte (M4 puis P2.15, corrigées
par la FIXTURE et non par l'attente) ; `test_verdict_empty` qui exigeait `N_EMERGE_PAS` sur **zéro
seed** — un négatif FABRIQUÉ gelé par le test censé l'attraper, rouge depuis huit jours ;
`test_run_curriculum_warmup0_is_compositional` et le seuil de la porte 14, tous deux rendus rouges
par un correctif de la veille sans que rien ne le dise pendant 24 h. Classe **E25**.

**RESTE À VÉRIFIER, et ce n'est pas vérifiable d'ici** : la parité d'ENVIRONNEMENT du runner GitHub
(torch, kuzu, dépendances lourdes). Le premier run de CI est lui-même la mesure. Si des tests échouent
pour cause d'environnement et non de code, la réponse juste est un `-m "not slow"` DÉCLARÉ avec sa
raison écrite — jamais un retour à la liste nommée, qui est la maladie et non le remède.

**P2.55 — ✅ CLOSE (2026-09-10) : E22 generalisee au MECANISME (porte 16)**

Le dépôt répondait à deux des trois occurrences d'E22 par des cliquets liés à **UN artefact** : la
porte 10 compte les TESTS, la porte 4 les entrées du BACKLOG. Le mécanisme, lui, est indifférent au
fichier qu'il détruit — le même accident sur `tools/ablation.py`, sur un record d'EDR, sur `ci.yml` ou
sur une baseline JSON n'était couvert par **RIEN**.

`tools/check_amputation.py` BLOQUE l'**anéantissement** (compte d'ENTITÉ tombé à zéro sur un fichier
CONSERVÉ, statut `M`) et SIGNALE, sans bloquer, toute baisse partielle. ⚠️ **Le choix de ne pas
bloquer les baisses est délibéré** : retirer du code mort est légitime et fréquent (sept branches
mortes retirées le 2026-09-09 même), et « un cliquet qui bloque sur le légitime est un cliquet qu'on
désactive ». Ce qui manquait n'était pas un refus mais **le chiffre sous les yeux** au moment du
commit — celui-là même (`2372 deletions`) qui a révélé l'anéantissement du backlog.

**LIMITE ASSUMÉE ET ÉCRITE** : l'amputation PARTIELLE d'un fichier quelconque reste non bloquée. La
bloquer demanderait de savoir ce que le fichier compte, ce que seuls les cliquets d'entité dédiés
savent. Ouvrir un cliquet d'entité pour une troisième famille de fichiers (les records ? les
baselines JSON ?) est la suite naturelle, **si** une occurrence l'exige — pas avant.

---

## P3 — Générateurs d'erreur encore sans réponse exécutable

*(⚠️ **BLOC HISTORIQUE** : E13 est CLOSE depuis le 2026-07-28 — `tools/cost_guard.py` + `tests/sandbox/test_cost_guard.py`. Le registre n'a plus aucune classe sans garde exécutable. Conservé pour l'historique — SAUF P3.3, qui n'est pas périmée : mesurée le 2026-09-08, réponse en deux morceaux de signes opposés, et ses entrées vivantes (P3.4-P3.7) sont dans le bloc 🧭 du 2026-09-14.)*


**P2.31 — ⛔ RÉTRACTÉE le 2026-09-08. La dette n'existait pas, et elle était à moi.**
`test_bilinear_composition_null_under_retention_is_lr_dependent` **PASSE en 205 s**, sous son plafond de
600 s et à 3 % des 199.7 s documentés le 2026-09-01. Rien n'avait ralenti.

**Ce qui s'est passé, et c'est la seule chose à retenir.** J'ai observé DEUX timeouts consécutifs et j'ai
conclu, la première fois « c'est la contention que je crée », la seconde « non, ce n'est pas la
contention puisque ça retimeoute sur CPU libre » — alors que le CPU n'était PAS libre : trois agents de
revue tournaient encore. Mesures successives du MÊME code, même machine, même paramètres :

| charge | wall par seed |
|---|---|
| 9 agents de revue actifs | **30.6 s** puis **55.1 s** |
| machine calme | **11.7 s** |

Soit un facteur **2.6 à 4.7**, du même ordre que la variance de 2.7× que ce dépôt DOCUMENTE déjà dans
`test_instrument_calibration.py`. Je l'avais lue, citée, et je ne l'ai pas appliquée à moi-même.

⚠️ **Règle : une observation de WALL-CLOCK n'est pas attribuable sans la CHARGE de la machine.** Un
timeout n'est pas une propriété du code ; c'est une mesure de l'ensemble (code, machine, charge), au même
titre qu'un plafond de recherche est une mesure de l'ensemble (forme, optimiseur, budget) — c'est la
MÊME faute que P2.15, sur une autre grandeur. Et j'ai en plus publié le diagnostic AVANT de mesurer sur
machine calme, deux fois, dans deux directions opposées.

**P2.45 — ✅ LIVRÉE (2026-09-08) — le cliquet du registre exige un contre-exemple COLLECTIBLE,
pas seulement PRÉSENT.**
<!-- closes_when:grep_present=tools/check_guard_negative_cases.py::_collectibles -->
`_exists` cherchait `def <nom>(` n'importe où sous `tools/`, `src/` ou `tests/`. Un test défini DANS une
autre fonction, ou posé dans un fichier que pytest ne collecte pas (`helpers.py`), y passait donc pour
présent alors qu'il ne s'exécutera JAMAIS : une classe `exécutable` aurait nommé un contre-exemple
**FANTÔME**, indiscernable d'une garde absente — E1 au méta-niveau, dans l'outil écrit pour la fermer.
La détection porte désormais sur ce que pytest collecterait réellement (AST, `def test*` au niveau
module ou méthode d'une classe `Test*`, dans `test_*.py` / `*_test.py`).

⚠️ **Fermé alors que ZÉRO classe est concernée** — mesuré. C'est le bon moment, et c'est la même
situation que le trou des collisions de noms, fermé le 2026-09-01 sans qu'aucun faux vert n'existe
encore. Un trou prospectif se ferme quand on le voit, pas quand il coûte.

⚠️ **Ce que le cliquet ne vérifie TOUJOURS pas, et c'est DÉCLARÉ** : que le test PASSE, ni qu'il tienne
dans son plafond de temps. La première est une propriété d'exécution ; la seconde dépend de la CHARGE
de la machine et n'est donc pas une propriété du test — cf. la rétractation de P2.31 juste au-dessus.

**Ce qui reste vrai et utile de l'entrée d'origine** : le cliquet du registre vérifie qu'une classe
`exécutable` NOMME son test, jamais qu'il PEUT tourner. Le trou est réel mais PROSPECTIF (mesuré : 0
classe concernée aujourd'hui), et il se ferme par une vérification de COLLECTIBILITÉ — cf. l'entrée
suivante. Le contre-exemple gelé, lui, s'exécute et passe : vérifié à n=12, plein budget.


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

**P3.2 — Budget obligatoire, mesuré au smoke. ✅ CLOSE (2026-07-28).** `tools/cost_guard.py` (`project_cost` avant + `CostGuard` pendant + `budget_agent_ticks` DÉTERMINISTE) + `tests/sandbox/test_cost_guard.py`. *Preuve : 3 runs abandonnés (8 h, 4 h projetées, 89 min),
plus WARM-009 nul et un run de 1,8 h sur une question sans objet.* Exiger un débit mesuré sur smoke + un
coût projeté avant tout run long, et **ne pas extrapoler une tendance depuis un préfixe court** (un
transitoire d'apprentissage y ressemble — erreur commise sur la dérive du grab). *Coût : ~1 h.*

**P3.3 — ✅ MESURÉE (2026-09-08), et la réponse est en DEUX MORCEAUX de signes opposés.**
Énoncé d'origine : les 7 revues ont trouvé du réel, mais ce sont des agents de même architecture avec
les mêmes priors — de l'auto-critique outillée, pas une réplication. La piste demandée était « faire
re-dériver un résultat porteur depuis les données brutes par un chemin indépendant ». C'est exactement
ce qui s'est produit le 2026-09-07, sans que ce soit le but : **SEPT dérivations indépendantes de la
même grandeur** (le plafond du substrat plain), chacune par sa propre méthode.

**0.8056 · 0.8333 · 0.8611 · 0.9444 · 0.9444 · 1.000 · 1.000** — soit **29/36 à 36/36, une étendue de
SEPT cellules sur 36** pour une question à réponse unique.

**Sur la MESURE, la divergence est massive — mais elle ne relève PAS l'inquiétude de P3.3.** Cette
dispersion n'est pas de l'indépendance de jugement : c'est la variance d'une recherche stochastique.
Mêmes agents, mêmes priors, tirages différents. La grandeur est limitée par l'optimiseur, donc toute
estimation par recherche varie — ce qui est le sujet de P2.15, pas de P3.3.

**Sur le JUGEMENT, l'inquiétude est CONFIRMÉE :** 3 réfutateurs sur 3 ont conclu `refute=False`, tous
avec `confiance=haute`. Unanimité parfaite, corrélation totale — exactement ce que l'entrée redoutait.

⚠️ **Ce qui a produit la valeur de la revue n'est donc PAS l'indépendance des agents : c'est
l'ORCHESTRATION.** Les quatre défauts réels ont été trouvés par des agents DIFFÉRENTS, sur des axes
DIFFÉRENTS, aucun deux fois — mais ces axes leur avaient été ASSIGNÉS dans le prompt (fidélité de la
forme · fiabilité de la mesure · cohérence avec le publié). La complémentarité était **conçue, pas
émergente**. Conséquence pratique : ne pas payer N agents pour le même angle en espérant de la
diversité — la diversité se prescrit.

⚠️ **RÈGLE MÉTHODOLOGIQUE, et c'est le vrai produit de cette mesure.** La grandeur cherchée était un
**EXTREMUM** (un maximum sur un espace de recherche). **Agréger des estimations d'un extremum par
CONSENSUS est faux : il faut agréger par EXTREMUM.** Ici la médiane des sept vaut 0.9444 et sous-estime
d'au moins deux cellules ; chaque estimation sous-cherchée tire le consensus vers le bas, et le
présente avec l'assurance d'un accord. C'est l'erreur P2.15 déplacée au niveau de l'AGRÉGATION — un
minorant, habillé en consensus.

**RÉPLICATION INDÉPENDANTE — tentative du 2026-09-08, et son premier chemin était INVALIDE.**
Chemin v1 : restreindre l'espace aux constructions **CIRCULANTES** (`a[k,j]=f[j-k]`, `b[q,j]=g[j-q]`),
18 paramètres au lieu de 78, avec un optimiseur SANS gradient (`differential_evolution` + `SLSQP`) —
indépendant sur l'espace, l'optimiseur ET l'objectif, et dont une solution serait un certificat lisible.

⚠️ **L'ancrage l'a tué, et c'est le résultat le plus utile de la tentative.** À `c_j` uniforme
l'instrument devait retrouver 27/36 (MILP, gap 0) ; il rendait 3/36. MILP sur la forme circulante :
**6/36 = 0.1667 à K=6, EXACTEMENT le hasard** (et 5/25 à K=5 — le hasard aussi), contre 27/36 pour
l'additif général. La forme circulante est celle qu'on écrit *spontanément* pour une tâche modulaire —
bonne symétrie, peu de paramètres — et elle **ne vaut rien**.

**Sans la référence exacte, j'aurais accusé l'optimiseur** et passé des heures à le régler : il avait
déjà trouvé 6/36, c'est-à-dire l'optimum de cet espace. Une référence EXACTE est la seule chose qui
sépare « recherche faible » de « forme pauvre » — c'est P2.15 appliquée à l'instrument de réplication
lui-même. Contrôle positif de la formulation : le même MILP circulant sur une cible SÉPARABLE rend
36/36, donc le 6/36 n'est pas un artefact d'encodage. Gelé dans
`test_the_CIRCULANT_construction_is_WORTHLESS_and_that_is_why_ANCHORS_matter`.

**Chemin v2 — ⛔ INSTRUMENT INVALIDE, et il s'est ARRÊTÉ TOUT SEUL.** Espace COMPLET (78 paramètres),
indépendant sur le seul axe OPTIMISEUR : `differential_evolution` (population, sans gradient) + `SLSQP`.
Ancrage obligatoire AVANT tout rapport. Résultat après **8814 s (2 h 27)** : **11/36** contre 27/36
PROUVÉ. La sonde a refusé de mesurer la vraie forme et l'a écrit.

⚠️ **C'EST LE RÉSULTAT LE PLUS UTILE DE TOUTE LA TENTATIVE.** Sans l'ancrage, j'aurais rapporté « un
chemin indépendant trouve 11/36 » — et ce chiffre aurait été lu comme une CORROBORATION que le plafond
est bas, c'est-à-dire l'exact contraire de la vérité, et une résurrection du `0.3889` que je venais de
rétracter. **L'ancrage a empêché une corroboration FABRIQUÉE d'un résultat déjà retiré.**

⚠️ **Et il apprend quelque chose de plus grave sur TOUTES les estimations, la mienne comprise.** Sur la
sous-forme dont l'optimum EXACT est connu (27/36) :

| méthode | trouve | vérité |
|---|---|---|
| descente de gradient (Adam + CE) | **14/36** | 27/36 |
| `differential_evolution` + `SLSQP`, 2 h 27 | **11/36** | 27/36 |
| MILP (HiGHS, gap 0) | 27/36 | 27/36 |

**AUCUNE méthode numérique testée n'atteint l'optimum exact du cas le PLUS FACILE** — toutes
sous-trouvent d'environ la moitié. Or les SEPT estimations du plafond de la forme complète viennent
toutes de méthodes numériques. Le minorant gelé (34/36, vérifié in situ) est donc très probablement
LARGEMENT sous-estimé, et le 36/36 rapporté par un des chercheurs est plausible.

**Conséquence pour `EDR-BILINEAR`, énoncée sans adoucissement** : la séparation de capacité n'est pas
seulement « non établie » — les éléments disponibles suggèrent qu'elle est **fausse**. Le plafond est
≥ 0.9444 (mesuré, vérifié dans le substrat), le bilinéaire mesure 0.932, et toutes les méthodes qui ont
produit ces plafonds sous-trouvent d'un facteur ~2 là où la vérité est connue.

⛔⛔ **CHANTIER CLOS AVANT D'AVOIR COMMENCÉ (2026-09-08) — il n'y a RIEN à borner.**
<!-- holds_when:path_present=results/plain_ceiling_witness_K3.json -->
Le cadrage de la relaxation de moments demandait de mesurer le plus petit cas. La réponse a supprimé le
chantier : **la forme close du plain atteint la PERFECTION** — **9/9 à K=3**, **16/16 à K=4** — là où sa
sous-forme additive plafonne à 7/9 et 12/16 (MILP, gap 0). En 23 secondes de calcul.

Vérifié TROIS fois : torch float64 · Python PUR en victoire STRICTE · **IN SITU dans un vrai
`TorchPopulationModel`, en float32**, marges polies 2.4e-2 et 7.0e-3. Témoins gelés dans
`results/plain_ceiling_witness_K{3,4}.json`, et un test interdit de relancer le chantier
(`test_the_UPPER_BOUND_project_is_MOOT`).

**Trois conséquences, sans adoucissement :**
1. **Le substrat plain n'est PAS incapable de composer.** L'échec à trouver 36/36 à K=6 est une
   défaillance de RECHERCHE — cohérent avec le fait qu'aucune méthode numérique testée n'atteint
   l'optimum EXACT du cas le plus facile (11, 14, 18 contre 27 prouvé).
2. **On ne majore pas ce qui atteint déjà le maximum.** Le chantier SDP/SOS est sans objet.
3. **La séparation de CAPACITÉ d'`EDR-BILINEAR` est FAUSSE**, pas seulement non établie. Ce qui subsiste
   est une séparation d'**APPRENABILITÉ à budget fixe** (0.271 vs 0.932, 0/144) — un résultat réel, et
   le seul. Gravé dans le record.

⚠️ **La méthode qui a produit ça vaut d'être retenue : mesurer le PLUS PETIT cas AVANT de dimensionner
le grand.** Le cadrage exigeait de savoir ce que vaut K=3 ; la réponse a rendu le chantier caduc. Même
économie que le pré-vol sur les runs, et que le test de viabilité à K=3/K=4 qui a réfuté les deux
relaxations.

**LA VOIE RESTANTE — une REFORMULATION acquise, deux relaxations RÉFUTÉES (2026-09-08).**
L'actif : `α = tanh(a)`, `β = tanh(b)` donne `tanh(a+b) = (α+β)/(1+αβ)`, donc un système d'inégalités
**POLYNOMIALES de degré 4 sur une BOÎTE BORNÉE**. Plus de réels non bornés, plus de saturation de `tanh`.

| méthode, sur l'ancrage dont l'optimum EXACT vaut 27/36 | trouve |
|---|---|
| `differential_evolution` + `SLSQP` (2 h 27) | 11/36 |
| gradient, paramétrisation NON bornée | 14/36 |
| **gradient sur la BOÎTE bornée** | **18/36** |
| MILP (HiGHS, gap 0) | **27/36** |

La boîte est la meilleure méthode numérique testée — et reste **33 % sous la vérité**. Elle s'est
arrêtée elle-même sur son ancrage, comme les deux précédentes.

**Deux relaxations réfutées, chacune pour un coût nul en testant à petit K d'abord** : « monotone
quelconque par colonne » atteint la PERFECTION (9/9, 16/16) ; **McCormick** sur la forme polynomiale
rend une borne duale TRIVIALE (9/9, 16/16). Tester la viabilité à K=3/K=4 AVANT d'investir a économisé
deux chantiers — c'est la même économie que le pré-vol fait sur les runs.

**Candidat restant, nommé et NON entamé** : relaxation de MOMENTS (Lasserre/SOS), le seul outil qui
donne des bornes serrées sur un système polynomial. `cvxpy` est présent ; `z3`, `SumOfSquares`, `picos`
non. Chantier à part entière, à cadrer avant d'être commencé.

En résumé sur la réplication indépendante — **ÉCHEC INSTRUCTIF, pas abandon.** Les deux chemins tentés ont été
recalés par leur propre ancrage (v1 : espace au niveau du hasard ; v2 : optimiseur trop faible). Ce qui
est désormais SU : le problème est une optimisation globale dure où les méthodes « naturellement
indépendantes » sont nettement PLUS faibles que celle qu'on voulait répliquer. Le seul chemin qui a
jamais atteint une réponse exacte ici est **exact** (MILP), pas numérique — et il ne s'applique qu'aux
sous-formes linéarisables. **La voie restante est donc une BORNE PROUVÉE pour la forme complète, pas une
réplication numérique.**

**Ce qui reste ouvert, et c'est plus étroit qu'avant — DÉCLARÉ NON PLANIFIÉ le 2026-09-15 (P3.5 b : une direction de recherche, pas une tâche ; aucune entrée ouverte ne la porte)** : une réplication par un chemin VRAIMENT
indépendant (autre architecture, autres priors) reste non faite. Ce qui est désormais mesuré, c'est que
la variance INTRA-architecture suffit à disperser une mesure, mais pas à disperser un JUGEMENT.

---

## P4 — Science

**P4.1 — ✅ VERDICT + MÉCANISME FERMÉS (mécanisme le 2026-09-09) — [`EDR-GRAB-COST`](../EDR/EDR-GRAB-COST_Carry_Tax_On_Unchosen_Rocks_And_The_Feeding_Premise_Is_Refuted.md).**
<!-- holds_when:path_present=results/p41_grab_famine.json -->
<!-- holds_when:path_present=results/p41_grab_mechanism.json -->
**Le grab NUIT** : retirer l'action améliore la survie médiane de **+39 %** (40.75 contre 29.25), sur
**30 ères APPARIÉES** (3 champions × 10 ères, même seed de monde par paire) : **28+ / 2−**, médiane des
différences **+10.75**, sign **p = 8.7e-07**, cohérent sur les 3 seeds (1.29× · 1.39× · 1.50×).

**Ce qui rend le résultat lisible** : le contrôle no-op `NullGrabOffMamba` est **BIT-IDENTIQUE** au bras
intact — plancher de bruit **EXACTEMENT NUL**. Différence structurelle avec la sonde sœur :
`derange_rows` CONSOMME des tirages et déplace la bande ([0.92 ; 1.06], dans laquelle son propre
résultat publié 0.991 TOMBE) ; écrire une constante dans une sortie n'en consomme aucun.

**LE CANAL, mesuré (2026-09-09) : la TAXE DE PORTAGE.** `carry` vaut **0.6418 / agent-tick** à l'intact
contre **0.0000** en `grab_off`, quand le différentiel énergétique TOTAL vaut **0.6262** — soit **102 %**,
tout le reste se compensant. Elle pèse **34.2 % du métabolisme de base**. Le bouclage comptable
(`carry` du moteur = 0.5 × poids recensé) tient à **2.3e-16**.
**Cause structurelle** : `_spawn_rocks` pose des rochers de poids `uniform(1,10)` (moyenne 5.5) **à
l'initialisation**, donc en tête de `self.items` ; le grab prend `nearby_items[0]`, **le premier de la
liste, jamais le meilleur**. Le grab est un ramasse-rochers par ordre de liste, pas un choix.

⚠️ **RECTIFICATION — la prémisse de la v1 était fausse TROIS fois** (classe **E8 occ. 4**). Elle
annonçait « `forage_payoff = 3.0`, ramasser un fruit RAPPORTE » : (a) la valeur réelle est **1.0**
(`run_condition` construit avec `config=None`) ; (b) `forage_payoff` ne multiplie que `prey_reward` sur
une mise à mort — il ne touche **jamais** `do_grab` ; (c) le grab nourrit **exactement 0 fois** sur
20 776 agent-ticks, par les DEUX chemins (revenu moteur +20, cache de famine). Le champion ne porte
aucun aliment : 4 549 `rock`, 1 166 `Spark`, 663 `stick`, 513 `Spear`… **zéro `Fruit`**.
**Pourquoi** — fait sur le MONDE, pas sur la politique : **25 ères sur 30 n'ont AUCUN arbre fruitier**, et
dans les 5 autres le cooldown initial (139-140, décrémenté seulement pendant l'abondance) place la
première récolte vers le tick **219** quand l'agent le plus âgé du dispositif meurt au tick **198**.
Le record est renommé et rectifié ; **les chiffres de survie tiennent intégralement**.

⚠️ **Deux bornes qui doivent être lues avec le résultat.** (1) **L'intervention n'est PAS minimale** :
l'inventaire conditionne aussi le **lancer** (`world_1_stoneage.py:1404`), donc le bras ablaté ne peut
jamais lancer — les +39 % sont le net de (taxe retirée) − (lancer retiré), le poste `autres` plus
favorable de 0.18/tick à l'intact en étant la trace. Le signe n'est pas en cause, la surgicalité l'est.
(2) **Ce record entre DANS la borne de portée déclarée par [`EDR-WARM-008`](../EDR/WARM-008_Aux_Off_Zeroes_Grab_But_Survival_Gain_Is_Null_And_Channel_Is_Load_Bearing.md)** :
« le grab nuit » n'est établi que dans un monde où grabber n'a aucun avantage possible. La borne est
donc **répliquée sur un troisième banc**, et la question « grabber paie-t-il quand grabber nourrit ? »
reste OUVERTE — aucun banc du dépôt ne peut y répondre.

**Ce que ça APPORTE à WARM-008** : le point de dose ÉLEVÉE qui lui manquait. `carry`/métabolisme
2.4-9.5 % → gain **NUL** (WARM-008) ; **34.2 % → +39 %** (ici). WARM-008 avait prédit la condition
(« le ×2.06 de WARM-005 venait d'un génome à inventaire lourd ») : c'est ce génome qui est mesuré.

**Contrôles supplémentaires** : *ancrage* — la boucle recensée rend une survie **exactement égale** à
`run_condition` (E19 occ. 6), ce qui établit aussi que `trace_energy_sinks=True` est un no-op sur la
dynamique ; *hypothèse du scaffold RÉFUTÉE* — le banc annule la prime de ramassage (`current_era=10 000`
→ `anneal=0`) alors qu'elle valait ~0.967 à l'évolution ; testé à prime **0.9667**, `grab_off` gagne
encore **46 contre 31** et l'écart s'élargit ; *taux de grab in situ* = **0.5547** (la v1 le déclarait
« plausible et NON MESURÉ »), cohérent avec l'asymétrie `grab_off` (p=8.7e-07) / `grab_force` (p=0.185).

Livré : `tools/grab_mechanism_probe.py` (`GrabCensusMamba`, `GrabCensusWorld`, `run_census_arm`,
`anchor_against_run_condition`) + **14 cas** dans `tests/sandbox/test_grab_mechanism.py` dont **12 sans
aucune simulation** ; `tools/s2_demand_ablation.py::{GrabOffMamba, NullGrabOffMamba, GrabForcedMamba}` +
6 cas dans `tests/sandbox/test_grab_cost.py`. Bruts : `results/p41_grab_mechanism{,_era1}.json`.

**P4.2 — 🔧 RÉÉCRITE le 2026-09-09 après cartographie et un PILOTE À COÛT ZÉRO. Les deux items tels
qu'ils étaient écrits ne sont pas à lancer : l'un est périmé, l'autre a son prédicteur littéral
mesuré NUL.**
<!-- holds_when:path_present=results/warm007_incidence.json -->

**Item (1) « incidence du canal né-ON sur ≥6 agents et ≥2 seeds » — PÉRIMÉ DANS SA LETTRE.**
La mesure existe : `results/warm007_incidence.json`, **12 agents × 2 seeds**, avec `birth_grab`,
`birth_on_frac`, `final_on_frac` et le ratio de survie par agent. Ce qui reste ouvert n'est pas un run
mais une **définition** : pour le MÊME seed 2026, l'incidence vaut **3/12** au critère « le monde
exécuterait le grab » (`on_frac > 0.5`, champ `n_born_on`) et **1/12** au critère « saturé au plafond
de tanh » (`|grab| > 0.9`, chiffre publié par [`WARM-006`](../EDR/WARM-006_No_Grab_Drift_Unit_Of_Analysis_Artefact.md):45).
Les deux sont exacts et répondent à deux questions différentes ; l'item ne disait pas laquelle.
**→ à faire : déclarer le critère, pas relancer la mesure.**

**Item (2) « canal porteur : corrélation coût ↔ poids de W autour du nœud 88 » — PRÉDICTEUR LITTÉRAL
MESURÉ NUL, à coût zéro.** Le nœud est identifié et vérifié : `N=172`, `num_outputs=108`, donc
`logits = H[N−O:]` et le logit 24 (grab) EST l'unité récurrente **88**. Sur les 24 génomes persistés
(`results/warm007_genomes/*.npz`), contre le ratio de survie grab-off/intact :

| prédicteur | rho de Spearman | p | CV entre agents |
|---|---|---|---|
| `Σ\|W[:, 88]\|` (entrant) — **le prédicteur littéral de WARM-008** | **−0.016** | 0.942 | **0.059** |
| `Σ\|W[88, :]\|` (sortant) | +0.347 | 0.097 | 0.064 |
| `Σ\|W[88, mouvement]\|` | −0.106 | 0.622 | 0.239 |
| **`final_on_frac`** (ce que l'agent FAIT) | **+0.598** | **0.0020** | — |

Deux lectures, et la seconde compte plus que la première. (a) Le prédicteur **structurel** ne prédit
rien — et son **CV de 6 %** dit pourquoi : il ne varie presque pas d'un agent à l'autre, donc il ne
peut quasiment pas discriminer. (b) Ce qui prédit, c'est la grandeur **fonctionnelle** : plus l'agent
grabbe effectivement, plus lui retirer le grab paie. Signe conservé dans les DEUX seeds
(**+0.866** p=0.0003 ; **+0.397** p=0.201), donc lisible ; **n indépendant = 2 seeds**, sous le
`n_floor=12` — le SIGNE se lit, l'AMPLITUDE non, exactement la leçon de WARM-008.

⚠️ **CE QUE CE PILOTE NE RÉFUTE PAS, et il faut le dire.** La prédiction de WARM-008 porte sur le
**coût collatéral en `move_acc`** dans la population **bootstrap-oracle** ; ce pilote porte sur le
**ratio de survie** dans la population **DAgger** de WARM-007. Ce ne sont ni la même variable
dépendante ni les mêmes génomes — et les W de la population bootstrap-oracle **n'ont jamais été
persistés** (`run_aux_off_validation` ne sauve que des scalaires). Tester la prédiction *telle
qu'écrite* exige donc un **ré-entraînement** (~75 min pour 4 seeds) plus un patch de persistance.
La prédiction souffre en outre d'un défaut de forme signalé dans le record lui-même : « corréler …
chez `ag04` » — une corrélation demande des agents, pas un agent.

**Ce que le pilote CONVERGE avec, et qui vaut plus que les deux items** : `final_on_frac` prédisant le
bénéfice du grab-off est la **même dose-réponse** que la taxe de portage de
[`EDR-GRAB-COST`](../EDR/EDR-GRAB-COST_Carry_Tax_On_Unchosen_Rocks_And_The_Feeding_Premise_Is_Refuted.md) —
plus on ramasse, plus on porte, plus la taxe pèse, plus la retirer paie. **Deux populations
indépendantes** (DAgger warm-start ; champion HoF évolué), **deux mondes** (banc WARM ; FamineWorld),
**même mécanisme**. C'est le troisième point de la dose-réponse `carry`/métabolisme, après les
2.4-9.5 % → nul de WARM-008 et les 34 % → +39 % de P4.1.

**Avancement du 2026-09-09 — (a) et (b) FERMÉS, (c) reste seul.**

✅ **(a) CRITÈRE D'INCIDENCE DÉCLARÉ.** Le critère opératoire est **`final_on_frac > 0.5`**, et la
raison n'est pas conventionnelle : c'est le seuil que le MONDE applique — il exécute le grab ssi
`logits[24] > 0` ([`world_1_stoneage.py:1523`](../../src/worlds/world_1_stoneage.py)). L'incidence
vaut donc **3/12** sous seed 2026. Le second chiffre (**1/12**, WARM-006) reste vrai et mesure une
**autre grandeur** : `|grab| > 0.9`, c'est-à-dire « le canal est-il ÉPINGLÉ au plafond de `tanh` ? ».
Les deux coexistent désormais sous des noms distincts — *né-ON* (le monde agirait) et *SATURÉ* (le
canal ne peut plus bouger) — et l'ambiguïté qui les confondait est levée sans aucun run.

✅ **(b) LES W SONT PERSISTÉS.** `run_aux_off_validation` ne sauvait que des scalaires, alors que
c'est SA population — bootstrap-oracle — qui porte le coût collatéral sur lequel `EDR-WARM-008`
énonce sa prédiction. Tester celle-ci exigeait donc un ré-entraînement complet **pour des poids qui
existaient déjà en mémoire au moment de la mesure** : un coût évitable, payé deux fois. Le patch
reprend l'idiome de `run_grab_incidence_and_ablation` (« ne JAMAIS re-payer l'entraînement »).
⚠️ **Le BRAS est une dimension** : les deux valeurs d'`aux_off_weight` produisent des populations
différentes à partir de la MÊME init, donc le nom de fichier porte le poids — sans quoi le second
bras écraserait le premier **en silence**. Calibré par injection (aucune trajectoire oracle, aucun
BPTT, aucun monde) : 3 cas, dont l'ancrage sur l'idiome de relecture déjà utilisé pour WARM-007 et
le contrôle apparié `genome_dir=None` → **rien n'est écrit**.

**Reste (c), et lui seul** : le ré-entraînement (~75 min, 4 seeds) qui produira les W du bras
bootstrap-oracle. ⚠️ **À ne lancer qu'en connaissant le pilote** : le prédicteur littéral de la
prédiction (`Σ|W[:, 88]|`) est déjà mesuré **NUL** sur la population DAgger (rho = −0.016, CV = 6 %),
et ce qui prédit y est **fonctionnel** (`final_on_frac`, rho = +0.598). Le ré-entraînement teste la
prédiction *telle qu'écrite* — sur l'autre population et l'autre variable dépendante — mais il part
avec une présomption défavorable, et c'est le pilote gratuit qui l'a établie. *Coût : ~75 min.*

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
- **SP-1 branchement — ✅ CLOS le 2026-09-09, et le trou était ACTIF.** `check_agi_taxonomy.py` est
  la porte la plus **stricte** du dépôt — verdict `X_DEMANDED` obligatoire, `incapable_ceiling`
  numérique avec provenance écrite (≥ 20 car.), `emergence_bar > incapable_ceiling`, et ses **deux**
  ensembles d'exemption légataire vidés le 2026-09-08. Elle ne tirait **nulle part** : mesuré,
  `grep -c check_agi_taxonomy tools/hooks/pre-commit` = **0** (contrôle positif :
  `check_bar_separation` = 2), **0** dans `ci.yml`, et `tools/agi_taxonomy_baseline.json`
  **n'existait pas**. Donc `data/agi_taxonomy/demands.json` était éditable et committable **sans
  aucun contrôle**, et la non-régression des 3 arêtes établies — pourtant écrite dans
  `test_every_GRAVEN_edge_remains_valid_after_hardening` — n'était exécutée par rien. Même scénario
  que `check_record_links` et `check_test_census` : une régression y aurait été **silencieuse**
  (classe E10). Livré : **porte 13** du hook (déclencheur couvrant les données, le cliquet ET sa
  propre baseline, classe E4 occ. 5), étape dédiée dans `ci.yml` + `test_agi_taxonomy_gate.py` et
  `test_perimeter_widening.py` ajoutés à la liste nommée, baseline gelée à **0 violation**, et
  **3 cas** de garde-de-la-garde (dont un contrôle POSITIF sur une porte connue branchée — sans lui,
  un motif de grep faux rendrait le test vert par absence de correspondance).
  <!-- holds_when:grep_present=tools/hooks/pre-commit::check_agi_taxonomy -->
- **SP-1 résiduel — ✅ CLOS le 2026-09-09, les trois écarts fermés à coût de run nul.**
  (a) **Schéma resynchronisé ET rendu PORTANT.** Il était en retard de **quatre** champs sur
  `validate_edge` (`coord_intact`, `emergence_bar`, `incapable_ceiling`, `ceiling_provenance`) et
  **n'était chargé par aucun code** — motif de recherche validé sur un cas positif avant de conclure
  à l'absence. Publier un contrat de forme que la porte refuserait est pire que ne rien publier
  (classe **E10**). `validate_against_schema` est branchée dans `validate_graph` (jsonschema, présent),
  et refuse effectivement une arête sans `reason` ou à `strength` invalide. ⚠️ Surtout, un **cliquet
  de dérive** (`test_the_SCHEMA_does_not_DRIFT_from_the_validator`) exige que tout champ lu par
  `validate_edge` soit déclaré au schéma : sans lui, une resynchronisation ponctuelle re-diverge à la
  première évolution — c'est exactement ce qui s'était produit.
  (b) **Champ `reason` posé sur les 3 arêtes**, en langue naturelle, disant POURQUOI le prérequis
  tient (et non seulement qu'il est mesuré). Requis par le schéma.
  (c) **Exporteur écrit** : `to_os_topics`, `to_os_dependencies`, `export_os_taxonomy` produisent
  `data/agi_taxonomy/export/{topics,dependencies}.json` aux clés EXACTES d'os-taxonomy. **Ancrage** :
  l'export est relu par le lecteur du format que le dépôt possédait déjà (`subgraph_for`), qui
  retrouve `['memory', 'perception']` comme prérequis durs de `language`.
  ⚠️ **La projection est LOSSY, et c'est le sens du fork** : os-taxonomy porte 4 champs par arête,
  l'AGI-Taxonomy en porte 14 — tout le bloc `evidence` (verdict d'ablation, ratio, n, contrôle de
  spécificité, plafond de l'incapable et sa provenance) disparaît à l'export. La provenance est donc
  réinjectée dans `reason`, sinon une arête exportée perdrait toute trace de ce qui l'établit.
  Garde en tête de l'exporteur : un graphe VIDE est **refusé** — deux JSON vides se liraient en aval
  comme « la taxonomie ne contient rien ». **9 cas** ajoutés (31 au total sur la porte).
- **SP-2 Peupler** — convertir gates G0→G4 + arc EDR + tétralogie G4 en nœuds/arêtes v0 (force = force de
  preuve empirique). Rend le records-graph **prédictif** au lieu de descriptif. *Dépend de SP-1 ; suppose
  la forme validée par SP-3.*
- **SP-2 — ✅ AVANCÉE le 2026-09-09 : le graphe peut enfin loger ce qu'il a RÉFUTÉ.**
  `validate_edge` exigeait `X_DEMANDED` : le graphe ne pouvait contenir **que du positif**. Or
  `CLAUDE.md` prescrit l'inverse — *« les résultats NÉGATIFS et les auto-réfutations se gravent au
  même titre que les positifs »* — et un record entier ([`EDR-LANG-MEMORY`](../EDR/EDR-LANG-MEMORY_Language_Demands_Memory.md),
  verdict NÉGATIF/NON-MESURABLE, qui `adopts: REF-AGI-TAXONOMY`) n'avait aucun logement.
  **La conséquence était opératoire, pas esthétique** : le graphe montrait trois arêtes propres et
  **aucune trace** que `language ← memory` a été tentée **deux fois** et refusée avant d'aboutir sur
  un AUTRE substrat — rien n'empêchait de relancer une arête déjà réfutée.
  Livré : `data/agi_taxonomy/refuted.json` (2 entrées, les deux tentatives) + `validate_refuted`
  branchée sur la porte, aux exigences **symétriques** de celles d'une arête établie, à une inversion
  près : un verdict `X_DEMANDED` y est **REFUSÉ** (sa place est `demands.json`). ⚠️ Et une paire à la
  fois ÉTABLIE et RÉFUTÉE doit déclarer `superseded_by`, sinon le graphe **se contredit en silence**
  et le lecteur ne sait pas laquelle des deux est à jour — contre-exemple gelé. La porte annonce
  désormais « 3 arêtes ÉTABLIES, 2 RÉFUTÉES ».
  **Reste ouvert** : les ~9 autres demandes within-subject mesurées sont des demandes
  **TÂCHE→capacité**, que le schéma ne peut structurellement pas exprimer (aucun type de nœud
  « tâche ») ; et deux nœuds mesurés manquent (anticipation 16,23×, composition 8,45×) mais à
  **8 seeds**, sous le plancher `n ≥ 12` des arêtes. Les inscrire exigerait soit un type de nœud
  nouveau, soit un power-up — aucun des deux n'est gratuit.
- **SP-2 dette — ✅ CLOSE (2026-09-02 puis DURCIE le 2026-09-08), et l'entrée était PÉRIMÉE depuis six
  jours.** Elle décrivait un état où `validate_edge` « ne lit pas du tout `coord_intact` ». Vérifié :
  la porte lit `coord_intact`, `emergence_bar`, `incapable_ceiling` ET `ceiling_provenance`, et les
  **trois** arêtes du graphe les déclarent :
  <!-- holds_when:grep_present=tools/check_agi_taxonomy.py::incapable_ceiling -->

  | arête | bras intact | barre | plafond de l'incapable |
  |---|---|---|---|
  | `language→perception` | 0.34375 | 0.1989 | 0.1836 |
  | `memory→perception` | 0.6547 | 0.2431 | 0.2266 |
  | `language→memory` | 0.819 | 0.5 | 0.1859 |

  Deux inexactitudes de l'énoncé d'origine, mesurées : la barre des sondes valait `1/K + 0.05`, pas
  `1/K + 0.15` ; et le fix proposé (« champ optionnel `coord_intact_median` ») est en-deçà de ce qui a
  été livré — la barre n'est pas seulement LUE, elle doit désormais SÉPARER un plafond d'incapable
  MESURÉ, et aucune arête n'est exemptée. **Trouvée en allant chercher quoi faire dans P4** : c'est le
  scénario exact que `check_backlog_freshness` était censé couvrir, et qu'il ne voyait pas — la clause
  `closes_when:` ci-dessus le ferme, dans les deux sens.
- **SP-3 Calibrer — ✅ MESURÉE ET GRAVÉE (`EDR-CALIB-SP3`, verdict GO), pas seulement spécifiée.** Le demand-marker récupère-t-il un DAG
  de prérequis *imposé* (os-taxonomy comme clé de réponse), en no-opant sur les non-arêtes **corrélées** ?
  Go/no-go de toute la vision. Design : `docs/superpowers/specs/2026-07-23-sp3-prerequisite-recovery-calibration-design.md`.
  *Pur numpy, aucun bail, aucun run long — cheap.*
- **SP-4 Forker/publier** — `agi-taxonomy` en fork-schéma, contribuer les critères within-subject en
  retour. *Dépend de SP-1→3.*
- **SP-4 — ✅ CLOS le 2026-09-09 PAR DÉCISION : pas de contribution en amont.** La question a été
  posée au propriétaire du dépôt et tranchée — ces arêtes ne sont **PAS** contribuées à
  `withmarbleapp/os-taxonomy`, parce que le faire placerait la contribution sous ODbL/CC BY-SA, qui
  n'est pas la licence de ce dépôt (MIT). ⚠️ **C'est un CHOIX, pas un blocage** : les quatre
  obligations techniques sont remplies, et si la décision était révisée, rien ne serait à
  reconstruire. L'export reste comme artefact LOCAL — il prouve la convertibilité du fork vers le
  format d'origine, vérifiée par aller-retour. Le durcissement qui avait une valeur de contribution
  (critère d'évidence within-subject) reste documenté dans `data/agi_taxonomy/NOTICE` et
  `REF-AGI-TAXONOMY`. *Détail de ce qui a été livré avant la décision :*
  Les trois obligations techniques sont remplies : l'**exporteur** existe (SP-1 (c)), le champ
  **`reason`** est posé, le **schéma** est resynchronisé et portant. La quatrième — le **NOTICE** —
  est écrite : `data/agi_taxonomy/NOTICE` déclare que les données sont MESURÉES ici (donc MIT, comme
  le dépôt), que seul le **FORMAT** est emprunté à `withmarbleapp/os-taxonomy` (ODbL 1.0 + CC BY-SA
  4.0), que `data/os_taxonomy/` est une fixture SYNTHÉTIQUE et non un extrait de leur base, et ce que
  l'export **PERD** (14 champs → 4 ; les arêtes réfutées ne sont pas exportables, le format ne sait
  pas les exprimer).
  ⚠️ **CE QUI RESTE N'EST PAS DU CODE.** Contribuer en amont placerait la contribution sous la
  licence du projet d'accueil (ODbL/CC BY-SA), qui **n'est pas** celle de ce dépôt. C'est une
  décision du propriétaire du dépôt : rien ici ne publie quoi que ce soit, l'export écrit des
  fichiers **locaux**. Le NOTICE existe pour que la question soit posée AVANT, et non découverte
  après.

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
