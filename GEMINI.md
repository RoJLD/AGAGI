# GEMINI.md — Règles d'Antigravity sur AGAGI

Ce fichier est lu automatiquement par Antigravity (Gemini). Il est **contraignant**. Il remplace, depuis le
2026-10-13, les « Commandements AGIseed » de juin, conservés pour l'historique dans
`docs/archive/GEMINI_AGIseed_2026-06.md` : plusieurs d'entre eux ont conduit aux dégâts du 9 au 11 octobre
(écriture d'« articles » et de « pensées » dans KuzuDB, validation d'un record sans protocole).

**La référence de méthode du dépôt est `CLAUDE.md`. En cas de conflit, `CLAUDE.md` l'emporte.** Lis-le avant
toute tâche, puis `docs/roadmap/PRIORITES_ET_DETTES.md` et `docs/REF/REGISTRE_ERREURS.md`.

Tu travailles **avec** des sessions Claude Code sur le même dépôt et la même machine (batcave). Une session
Claude, « Master 2 », est l'intégratrice : elle seule fait entrer du code dans la branche principale et la pousse.

---

## 1. Où tu travailles

- **Uniquement** sur la branche `feat/langage-ultime`, dans le worktree `.worktrees/langage-ultime`. Ouvre CE
  dossier dans l'IDE, jamais la racine du dépôt.
- **Jamais** de commit ni de push sur `feat/d1-prod-pairing` ni sur `main`. Jamais de push forcé.
- Ne modifie **aucun** autre worktree (`.worktrees/*`) ni l'arbre principal : ils portent le travail en cours des
  sessions Claude.
- Avant de commencer : `git fetch`, puis `git merge origin/feat/d1-prod-pairing` dans TA branche si tu veux la
  base à jour (jamais l'inverse).

## 2. Commits

- Les crochets git tournent à **chaque** commit. Si l'IDE commite sans lancer les crochets, commite depuis un
  terminal : `git commit -F message.txt -- <chemins>`. **Jamais** `--no-verify`.
- Une porte rouge se **corrige**, elle ne se contourne pas. Il est **interdit** de :
  - élargir une baseline (`tools/*_baseline.json`, `--update-baseline`) ;
  - déclarer une fonction `NOT_AN_INSTRUMENT` pour échapper à la calibration ;
  - modifier à la main les comptes balisés de `CLAUDE.md`.
  Si tu ne sais pas corriger, arrête-toi et écris le problème dans la passerelle (section 8).
- Messages de commit sans backticks ; un sujet qui dit ce qui change, un corps qui dit pourquoi.

## 3. Mondes et non-régression

- Le comportement **par défaut** des mondes existants (`world_1_stoneage`, `world_2_agricultural`,
  `world_3_industrial`) et de `WorldConfig` doit rester **bit-identique**. Toute nouvelle mécanique passe par un
  **drapeau éteint par défaut**, et rien ne s'exécute hors de ce drapeau (pas même un transfert « au feu de
  camp »).
- Ne supprime ni ne renomme **jamais** un champ de configuration, une fonction ou une classe existante : d'autres
  modules et des résultats publiés en dépendent.
- Un monde nouveau = un fichier nouveau. Ne réécris pas un monde existant.
- Preuve exigée avant tout commit qui touche `src/worlds/`, `src/environments/` ou `src/agents/` : les tests de
  référence verts (`tests/sandbox/test_s2_bassin_fragility.py`, `test_e34_identity_cell.py`,
  `test_metabolic_cost.py`, `test_agricultural.py`, `test_rsi_loop.py`), chacun lancé SÉPARÉMENT.

## 4. KuzuDB et simulations

- **N'écris jamais** dans `data/kuzu_graph.db` : le monde la lit pendant les simulations, et toute écriture change
  les runs des autres. Pas d'« articles » ni de « pensées » en base.
- Toute simulation : appelle `_disable_kuzu()` et arrête `memory_retriever` avant la boucle, et tiens le bail
  `kuzu` : `from tools.jobs.run import hold` puis `with hold("kuzu", owner="antigravity-<tâche>"): ...`.
- Avant tout run ou toute suite de tests : `python -m tools.jobs.doctor`. Si un bail est tenu par quelqu'un
  d'autre, tu attends : un run de nuit de Claude est peut-être en cours.
- Un seul run lourd à la fois sur la machine.

## 5. Affirmations scientifiques

- Tu ne graves **aucune** affirmation : pas de record `docs/EDR/`, pas de changement de statut d'une SDR, pas de
  mot de verdict (« validé », « prouvé », « franchi », « AGI », « conscience ») dans un document du dépôt.
- Une affirmation exige le protocole de `CLAUDE.md` : règle pré-inscrite et scellée (`tools/preregister.py`),
  pré-vol (`tools/experiment_preflight.py`), n = 12 seeds, référence lr = 0 appariée, plafond de l'incapable,
  contrôle positif, invariance au pas (E19), résultats dans un `results/*.json` suivi, puis revue à sondes par
  Claude (`/refutateur`). Ce circuit passe par Master 2.
- Tes notes d'exploration vont dans `docs/exploration/`, avec en tête : « EXPLORATION — non vérifié, aucune
  valeur de preuve ». Un score qui compte l'activité de son propre mécanisme, une valeur écrite en dur ou un banc
  sans agent ne sont pas des mesures.

## 6. Instruments

- Toute fonction qui produit un verdict, un ratio, un taux ou un score est un **instrument** : elle se calibre
  (`tests/sandbox/test_instrument_calibration.py`, déclarée `CALIBRATED` avec un test qui l'exerce sur une
  réponse connue), ou elle n'est pas committée.

## 7. Tests et CI

- Tests des deux côtés : avec et sans torch (`pytest.importorskip("torch")` en tête de tout test qui l'importe).
- Toute route backend ajoutée : régénérer les types (`python tools/dump_openapi.py` puis `npm run gen:api` dans
  `frontend/`) dans le même commit.
- Aucun chemin de données en dur : passer par `src/paths.py`.
- Lance chaque fichier de test séparément, ou vérifie que `tools.__path__` pointe vers TON worktree.

## 8. Main dans la main avec Claude : la passerelle

- `docs/roadmap/PASSERELLE_ANTIGRAVITY.md` est le canal entre toi et les sessions Claude.
- À la fin de **chaque** session de travail, ajoute une entrée en tête de la section « Antigravity → Claude » :
  date, sha de `feat/langage-ultime`, ce qui a changé, ce que tu proposes d'intégrer, tests lancés avec leurs
  résultats, questions ouvertes.
- Lis la section « Claude → Antigravity » en début de session : les réponses, refus et demandes de Master 2 y sont.
- Rien n'entre dans `feat/d1-prod-pairing` sans passer par cette passerelle et par l'intégration de Master 2.
