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
2. **La grandeur mesurée est-elle celle qui agit ?** → `assert_no_aliasing` (⚠️ `forward` renvoie des
   VUES de l'état : écrire dans une sortie mute l'état récurrent), `assert_predictor_measured_in_situ`
3. **Quelle est l'unité de réplication ?** Dans ce dépôt c'est l'**ère/le seed**, pas l'agent — les
   agents d'un seed partagent entraînement, optimiseur et monde. → `declare_design`
4. **Est-ce que je raisonne au lieu de mesurer ?** Réduire le n, **jamais** supprimer le maillon : une
   chaîne causale transporte son signe, pas son amplitude. → `declare_design`

## Calibration des instruments (le déficit dominant du dépôt)

**Inventaire au 2026-07-21 : 71 instruments détectés, 1 calibré.** Un « instrument » = une fonction qui
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
- **Cliquet** : `tools/check_instrument_calibration.py` — dette légataire gelée, **aucun NOUVEL
  instrument non calibré**. Même mécanisme que `check_record_links.py`.
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
chemins disparus). Tous branchés sur le hook pre-commit (`tools/hooks/pre-commit`).
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

## Records
Nouveau record → frontmatter `gate:` / `tests:[SDR-Gx]` / `adopts:` ou `foundational`, sinon
`tools/check_record_links.py` le signale comme orphelin (le hook pre-commit bloque les nouveaux).
Les résultats NÉGATIFS et les auto-réfutations se gravent au même titre que les positifs.

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
- Ne jamais committer sans demande explicite.
- `_disable_kuzu()` / arrêter `memory_retriever` avant les boucles de simulation (contention + non-repro).
