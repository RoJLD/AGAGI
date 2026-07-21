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
