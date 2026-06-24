# Design C1 — Observabilité & Provenance (backend, Dev #7)

> Spec de conception. Chantier 1 de la **roadmap backend** (Observabilité → A/B live → Stubs/CI →
> Sécurité). Issu du scan global (Dev #7 « versioning des données : hash config/commit ↔ KPI ;
> drain KuzuDB instrumenté ») et de la cartographie backend du 2026-06-15. Brainstorm 2026-06-15.

## 1. Problème

Le backend AGIseed est un dashboard scientifique, mais il a le **même angle mort que le moteur avant
D1 : la confiance dans les chiffres**.

- **Données fantômes** : `strategy.py`/`sociologist.py` retombent sur du **mock** si KuzuDB est vide,
  *sans alerte* → le dashboard peut afficher du faux sans le dire.
- **Observabilité zéro** : l'`AsyncLogger` (331 LOC, retry + dégradation gracieuse) n'expose **aucune**
  métrique — on ne sait pas s'il ingère ou s'il décroche silencieusement.
- **Provenance absente** : un KPI affiché n'est relié à **rien** — ni seed, ni commit, ni config. Or
  `Harness.save` (D1) écrit déjà `seed`+`commit` dans `results/*.json` : la moitié du socle existe.

**Objectif** : pour chaque run, répondre *« avec quel code/config/seed a-t-il tourné, ses KPIs, et où
sont ses données ? »*, et voir d'un coup d'œil si KuzuDB ingère. C'est le **socle de validité du
dashboard**, prolongement direct de D1 jusqu'à l'écran.

## 2. Décisions (figées)

| # | Fork | Choix |
|---|---|---|
| 1 | Provenance | **Ledger riche (Dev #7)** : `config_hash` + `git_dirty` + cross-link KuzuDB |
| 2 | Cross-link résultats↔DB | **Nœud `Run`** dans KuzuDB (B) ; `ERA_RESULT` rattachés via `BELONGS_TO_RUN` |
| 3 | Santé KuzuDB | **Lecture seule via la connexion partagée** `async_logger.get_db()` (évite les locks) |
| 4 | Métriques logger | **In-process minimales** (queue, events/type, erreurs, dernière latence) — YAGNI percentiles |
| 5 | Périmètre | **Backend + extension moteur** ; *pas* de frontend (session backend) |

## 3. Architecture

```
MOTEUR (src/)
  src/seed_ai/harness.py
    Harness.save(data, config=None)   -> + config_hash + git_dirty dans results/<name>_<seed>.json
    Harness.__enter__                 -> emit RUN_START {name,seed,commit,config_hash,git_dirty}
    Harness.__exit__                  -> emit RUN_END
  src/graph_rag/async_logger.py
    + gère RUN_START/RUN_END (crée le nœud Run, retient current_run)
    + rattache ERA_RESULT au Run courant (BELONGS_TO_RUN)
    + instrumentation : events_processed (total+par type), error_count, last_latency_ms, queue.qsize()
    + metrics() -> dict

BACKEND (backend/app/)
  services/provenance_service.py
    list_runs()        -> [ {name, seed, commit, config_hash, git_dirty, kpis, mtime} ]  (scan results/*.json)
    get_run(name)      -> détail fichier + cross-link KuzuDB (Run/Result par seed+commit+config_hash)
    kuzu_health()      -> {reachable, writable, schema_present, counts_by_label}  (read-only, conn partagée)
    logger_metrics()   -> async_logger.metrics()
  routes/observability.py
    GET /api/health/kuzu            -> kuzu_health()
    GET /api/observability/logger   -> logger_metrics()
    GET /api/provenance             -> list_runs()
    GET /api/provenance/{name}      -> get_run(name)
  main.py : app.include_router(observability.router)
```

## 4. Le ledger (cœur)

- **`Harness.save(data, config=None)`** : si `config` fourni, calculer `config_hash` = hash stable et
  déterministe d'une **vue sérialisable** de la config (helper qui essaie `model_dump()` pydantic →
  `dataclasses.asdict()` → `vars()`, puis `sha1(json.dumps(view, sort_keys=True, default=str))`, tronqué).
  `git_dirty` = `git status --porcelain` non vide. Écrits à côté de `seed`+`commit`. **Sans
  `config`, les champs sont omis** → aucun run existant ne casse.
- **Nœud `Run`** (KuzuDB) : clé = `(seed, commit, config_hash)`. Créé sur `RUN_START`. Les `ERA_RESULT`
  (et événements de run) émis pendant que `current_run` est posé s'y rattachent → on peut demander
  « montre-moi les entrées DB du run X ».
- **Cross-link backend** : `get_run(name)` lit le fichier `results/<name>.json` (provenance + KPIs) PUIS,
  si KuzuDB joignable, requête le nœud `Run` correspondant + ses `Result` liés. Dégradation : si pas de
  DB, renvoie la provenance fichier seule (jamais de 500).

> **Le ledger sert S2 gratuitement** : `results/s2_demand_*.json` est *déjà* un `Harness.save` → il
> apparaît dans `/api/provenance` et son verdict par monde dans `/api/provenance/s2_demand_<seed>`.
> Aucun endpoint S2 dédié.

## 5. Santé KuzuDB

`kuzu_health()` utilise **la connexion partagée** `async_logger.get_db()` (pas une connexion concurrente
— KuzuDB verrouille en écriture). Renvoie :
- `reachable` : la connexion existe et répond à une requête triviale.
- `writable` : le thread `AsyncLogger` est vivant (`_running` + thread alive) — proxy du « ça ingère ».
- `schema_present` : les tables/labels clés existent (ex. `Result`, `Article`, `Run`).
- `counts_by_label` : `MATCH (n:<Label>) RETURN count(n)` pour les labels clés → détecte « DB vide » (la
  cause des données fantômes de `strategy`/`sociologist`).

Tout en **lecture seule**. Si `get_db()` renvoie `None` → `{reachable:false, ...}`, pas d'exception.

## 6. Métriques AsyncLogger

Instrumenter (compteurs in-process, négligeable) :
- `events_processed` (total) + `events_by_type` (dict).
- `error_count` (échecs d'insertion DB).
- `last_latency_ms` (durée du dernier `_process_event`).
- `queue_size` (`self.queue.qsize()`).
- `running` (thread vivant), `db_connected` (bool).

Exposés par `metrics() -> dict`, servis par `GET /api/observability/logger`. **Non bloquant** (lecture
de compteurs). Un WARNING est loggé si `queue_size` dépasse un seuil (ex. 1000) — détection de backlog.

## 7. Gestion d'erreurs

- Tout endpoint **dégrade gracieusement** sans KuzuDB : `health` → `{reachable:false}` (200, pas 500) ;
  `provenance` lit les fichiers même DB absente ; `logger` renvoie les compteurs même si `db_connected=false`.
- `config_hash`/`git_dirty` : `try/except` autour de `git`/sérialisation → si échec, champ à `"unknown"`,
  jamais de crash d'un run.
- `RUN_START`/`RUN_END` : si l'émission échoue, le run continue (best-effort, comme tous les `emit`).
- `list_runs` ignore un `results/*.json` illisible/corrompu (loggé, sauté).

## 8. Tests

- **`tests/test_observability.py`** (backend, TestClient) :
  - `/api/health/kuzu` : DB présente → `reachable:true` + counts ; DB absente (monkeypatch `get_db→None`)
    → `reachable:false`, pas d'exception.
  - `/api/observability/logger` : forme des métriques (clés présentes, types).
  - `/api/provenance` : avec une fixture `results/<tmp>.json` → run listé avec seed/commit/config_hash.
  - `/api/provenance/{name}` : détail = provenance + KPIs ; nom inconnu → 404.
- **`tests/sandbox/test_harness.py`** (extension) :
  - `save(data, config=cfg)` écrit `config_hash` + `git_dirty` ; `save(data)` (sans config) ne casse pas
    et omet les champs.
  - `config_hash` **déterministe** (même config → même hash) et **sensible** (config différente → hash différent).
- **`tests/sandbox/test_async_logger.py`** (nouveau ou extension) : `metrics()` renvoie les clés ;
  `events_processed` s'incrémente ; `RUN_START` pose `current_run` (sans DB → ne crashe pas).
- **Non-régression** : suite sandbox + `test_backend.py` verts.

## 9. Critères de succès

1. `GET /api/health/kuzu` distingue **DB peuplée / DB vide / DB absente** (tue les données fantômes).
2. `GET /api/observability/logger` expose queue/events/erreurs/latence.
3. `GET /api/provenance` liste les runs avec **seed+commit+config_hash+git_dirty+KPIs** ; le verdict S2 y
   apparaît sans endpoint dédié.
4. `Harness.save(data, config)` écrit la provenance étendue ; runs sans config inchangés.
5. Nœud `Run` créé sur `RUN_START`, `ERA_RESULT` rattachés ; `get_run` cross-linke fichier↔DB.
6. Tous les endpoints dégradent gracieusement sans KuzuDB. Suites de tests vertes.

## 10. Hors périmètre (YAGNI)

- **Frontend** (panneau qui consomme ces endpoints) — session backend ; viendra plus tard.
- Percentiles de latence / time-series / métriques Prometheus — compteurs simples suffisent.
- Auth sur les endpoints d'observabilité — c'est le **Chantier 4** (Sécurité).
- Migrer `strategy`/`sociologist` hors du mock — **Chantier 3** (le health endpoint de C1 rend juste le
  mock *visible* ; le débrancher est C3).
- Checkpoint reproductible binaire (sérialisation HoF+RNG+WM) — extension future du ledger.

## 11. Dépendances

- **D1 `Harness`** (`save`, `__enter__`/`__exit__`, `_git_short_commit`) — livré, sur `feat/d1-prod-pairing`.
- **`AsyncLogger`** (`emit`, `set_database`/`get_db`, `_process_event`) — existant.
- **`backend/app/main.py`** (pattern `include_router`), `tests/test_backend.py` (pattern TestClient) — existants.
