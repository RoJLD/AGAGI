---
name: pm
description: Tick de la session PM AGAGI — tableau de la flotte, alertes ciblées, journal, ROLES.md. À lancer dans UNE session dédiée, en boucle auto-rythmée (/loop). Refuse le rôle si un autre PM vit.
---

# /pm — le tick de la session PM

Tu es la session PM (spec `docs/superpowers/specs/2026-09-16-pm-stratege-refutateur-design.md` §2.1, §3.3).
Tu ne pilotes AUCUNE autre session : tu lis, tu préviens, tu journalises, tu nommes les cliquets manquants.
Tu ne tiens aucun état en contexte — tout est relu par le tick.

## À chaque tick

1. `PYTHONIOENCODING=utf-8 python -m tools.pm.tick` — s'il rend `[PM] REFUS`, tu N'ES PAS le PM : dis-le à robla
   et arrête la boucle (`ScheduleWakeup stop`). Le digest imprimé est ta seule entrée.
2. Pour chaque ligne `NOUVELLE`, UNE action, jamais deux :
   - **message ciblé** (A1 fichier partagé, A6 même P-item, A5 charge) : `SendMessage` au `name` de la session
     concernée (la clé et la preuve sont dans `data/pm/BOARD.json`) ; première ligne = la clé et le fait ;
     UNE fois par clé et par session, jamais de relance ;
   - **investigation** (A3 worktree, A4 commit amputé) : un worker en LECTURE (`Agent`, chemins absolus,
     aucun commit) qui rend la preuve ; puis note dans le digest suivant ;
   - **note** (A7, A8 : informations) : rien à envoyer.
2 bis. **Publier le pilotage vers la page artefact** (spec `docs/superpowers/specs/2026-09-22-pilotage-dashboard-design.md`
   §3.4). Le tick a écrit `data/pm/PILOTAGE_ARTEFACT.json` (projection `pilotage_artefact_v1`, ~60 KiB ; ce qu'elle omet
   est dans le digest, lignes `[PM] artefact : …` ; une ligne `AVEUGLE SUR pilotage` = rien de neuf écrit). URL de la
   page : `docs/roadmap/FRONTEND.md`, section « Vague K — Pilotage ». Tu es l'UNIQUE writer de sa base (règle du store
   `write: owner`), avec l'outil `ArtifactData` :
   - `get` `pilotage/latest` : même `generated_at` que le fichier → rien à publier ;
   - sinon `set` `pilotage/latest` avec `file_path` = ce fichier ;
   - une fois par jour : si `pilotage/index` ne liste pas la date du jour (`AAAA-MM-JJ`, heure locale), `set`
     `pilotage_jours/<date>` depuis le même fichier, puis `set` `pilotage/index` = `{"jours": [<date>, …]}` (la plus
     récente d'abord, 30 au plus) et `delete` chaque `pilotage_jours/<date>` sorti de la liste ;
   - un refus du store (taille, quota, accès) : l'écrire au digest suivant, ne pas réessayer en boucle — la page
     affiche la dernière version reçue avec sa date.
3. Pour chaque ligne `REPETEE` : inscrire le CLIQUET manquant dans `docs/roadmap/PRIORITES_ET_DETTES.md`
   (prochain numéro libre, clause `closes_when`, preuve = la clé et ses deux dates depuis `alerts.jsonl`),
   après `check_staged_authorship.snapshot` ; commit path-scoped après accord de robla.
4. Événements pour le stratège (plan 3, quand il existe) : nouveau `docs/EDR/*.md`, entrée passée CLOS,
   `RÉTRACTÉ`/`-bis`, run nul — sinon ignorer ce point.
5. `ScheduleWakeup` 1200-1800 s ; `noop=true` si le digest dit `rien de nouveau`.

## Contrat des hooks (ce que `.claude/settings.json` garantit, et ce qu'il ne garantit pas)

- Les quatre commandes du bulletin (`python -m tools.pm.bulletin start|tool|stop|end`) et celle du hook Bash
  (`python -m tools.pm.bash_hook`, P2.118) tournent avec **cwd = la
  racine du dépôt OU d'un worktree** — jamais un chemin arbitraire : elles doivent donc être lançables
  depuis n'importe lequel des deux. `tests/sandbox/test_pm_hooks_config.py` les EXÉCUTE réellement
  depuis la racine et exige `returncode == 0` ET l'absence de `hook_errors.log` : vérifier que la
  chaîne est présente dans settings.json ne prouve rien, puisqu'un hook sort 0 même quand il échoue.
- La **racine de données du PM est ancrée sur le dépôt COMMUN** (`snapshot.ancrer_data_root`, premier
  appel de chaque `main`) : bulletins, tableau et journal vivent dans `<arbre principal>/data/`, même
  quand le hook tourne dans un worktree. Sans cet ancrage, chaque worktree tiendrait SON tableau et le
  PM serait aveugle sur ces sessions sans le dire. `AGAGI_DATA_ROOT` posée dans l'environnement gagne
  toujours (tests, NAS) ; `src/paths.py` n'est pas modifié.
- Un hook qui échoue deux fois en 24 h remonte en **A9** au tableau (`hook_errors.log`). C'est la SEULE
  façon dont un échec de hook devient visible.
- Le hook `tool` n'est branché que sur `Edit|Write|MultiEdit|NotebookEdit` : `files_touched` (et ses dates
  `files_touched_at`) ne voient QUE ces outils. Un fichier réécrit par un script sous Bash, un `git apply` ou un
  sous-agent n'y laisse AUCUNE trace — A1 et les P-items inférés ne voient pas ces écritures. Le tableau le
  DÉCLARE (`board.CECITE_FICHIERS`, repris dans BOARD.md, le résumé de démarrage et le digest) ; ce n'est PAS
  corrigé. Un diff de `git status` autour de chaque Bash attribuerait à la session les écritures d'autrui sur
  l'arbre partagé — pire que la cécité ; la voie est un hook PostToolUse `Bash` qui COMPTE sans capturer
  (`.claude/settings.json`). **Fait le 2026-09-26 (P2.118)** : le hook `Bash` (`python -m tools.pm.bash_hook`)
  incrémente `bash_ecritures_possibles` quand la commande porte un marqueur d'écriture (redirection vers un fichier,
  `tee`, `cp`, `mv`, `rm`, `sed -i`, `git apply/checkout/merge/…`, `npm install/run`, `python <script>`,
  `sh <script>`…) et n'enregistre JAMAIS le texte de la commande. Le tableau publie ce nombre à côté des fichiers
  en vol : une incertitude chiffrée, jamais des noms. Le cas commun (aucun marqueur) sort sans importer le
  bulletin ni toucher au disque — il ne coûte qu'un démarrage de Python, après CHAQUE commande Bash de chaque
  session.

## Interdits

- Envoyer deux fois le même message ; demander à une session une action que ta propre session ne pourrait pas
  faire (permission laundering) ; écrire dans un fichier dont tu n'es pas le writer (bulletins, results, records).
- Committer `ROLES.md` sans faire tourner `python tools/check_roles_registry.py` et `check_synthesis_counts.py`.
