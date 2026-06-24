# Design C2 — A/B Live Multi-run (backend)

> Spec de conception. Chantier 2 de la **roadmap backend** (Observabilité → A/B live → Stubs/CI →
> Sécurité). Issu du scan global (Dev #5 / D6 « FlatlandServer→FlatlandManager, /ws/flatland/{run_id},
> compare-live ») et de la cartographie backend. Brainstorm 2026-06-15. Suite de C1.

## 1. Problème

`backend/app/flatland_server.py` expose **un seul** `flatland_server` (singleton, l.209) : une biosphère
live streamée à 30 FPS via `/ws/flatland`. Impossible de **comparer 2 lignées** (baseline vs
intervention) **côte à côte en direct** — pourtant c'est le geste scientifique central du dashboard.

`FlatlandServer` est déjà self-contained (chaque instance a son monde, sa `Queue`, son thread). Le
singleton est une *politique*, pas une limite d'architecture : il suffit de **dé-singletoniser**
(un `Dict` de runs) + paramétrer le constructeur, et d'ajouter la **gestion de cycle de vie**
(création/suppression, cap, routing par `run_id`).

## 2. Décisions (figées)

| # | Fork | Choix |
|---|---|---|
| 1 | Forme | **Multi-run générique** : manager (dict) + REST lifecycle + `/ws/flatland/{run_id}` ; le frontend compose l'A/B |
| 2 | Nature de l'A/B | **Observationnel** (regarder 2 lignées) — *PAS* un appariement reproductible (cf. §7) |
| 3 | Cap | **`MAX_RUNS = 4`** (anti-explosion threads/mémoire) |
| 4 | Intervention | **overrides whitelistés** appliqués à la `WorldConfig` |
| 5 | Rétro-compat | garder `flatland_server` (run `"default"`) + `/ws/flatland` legacy |
| 6 | Périmètre | **backend** ; *pas* de frontend (onglet compare-live = plus tard) |

## 3. Architecture

```
backend/app/flatland_server.py
  FlatlandServer.__init__(self, config_overrides=None, pop_size=10, label=None)
    -> applique les overrides whitelistés sur WorldConfig (etait hardcode size=32/altars=5/semi)
    -> stocke self.label ; reste (queue/thread/world/era) inchange
  FlatlandManager
    runs: Dict[str, FlatlandServer]              # "default" + runs crees a la demande
    create_run(overrides, pop_size, label) -> run_id   # cap MAX_RUNS ; uuid court ; ValueError si plein
    get_run(run_id) -> FlatlandServer | None
    stop_run(run_id) -> bool                     # stop() + retire du dict (False si inconnu)
    list_runs() -> [ {run_id, label, status, era, agent_count} ]
  flatland_server  = FlatlandServer(label="default")   # singleton legacy (run "default")
  flatland_manager = FlatlandManager()                 # enregistre flatland_server comme "default"

backend/app/routes/flatland.py
  POST   /api/flatland/runs   {config_overrides?, pop_size?, label?} -> {run_id}   # 429 cap / 400 override inconnu
  GET    /api/flatland/runs   -> [ {run_id, label, status, era, agent_count} ]
  DELETE /api/flatland/runs/{run_id} -> {stopped: bool}                            # 404 si inconnu

backend/app/main.py
  app.include_router(flatland_router, prefix="/api/flatland", tags=["Flatland"])
  @app.websocket("/ws/flatland/{run_id}")   # connecte la queue du run (close 1008 si inconnu)
  @app.websocket("/ws/flatland")            # LEGACY inchange (run "default")
```

## 4. Cycle de vie (`FlatlandManager`)

- **`create_run`** : refuse si `len(runs) >= MAX_RUNS` (lève `RunCapExceeded` → 429). Génère `run_id`
  = `uuid4().hex[:8]`. Instancie `FlatlandServer(config_overrides, pop_size, label)` et l'ajoute au dict.
  Le run **ne démarre pas** à la création (son thread démarre au 1ᵉʳ connect WebSocket, comme le legacy).
- **`stop_run`** : `server.stop()` (pose `running=False` → le thread daemon sort de `_simulation_loop`) +
  retire du dict. Le `"default"` n'est **pas** supprimable (retourne False ou ignore) pour préserver le legacy.
- **`list_runs`** : statut = `"running"`/`"idle"` selon `server.running`.
- **`get_run`** : `runs.get(run_id)`.

## 5. Overrides d'intervention (whitelist)

`FlatlandServer.__init__` applique sur la `WorldConfig` **seulement** des clés whitelistées (toute autre
clé → `ValueError` → 400 côté route) :

```
WHITELIST = {"active_exp_variable", "robust_hof_K", "mutation_rate", "base_metabolism",
             "forage_payoff", "size", "num_altars", "prey_mode"}
```

C'est la « variable d'intervention » : ex. `{"active_exp_variable": "LANGUAGE"}` vs baseline sans
override. On part de `WorldConfig(size=32, num_altars=5, prey_mode="semi")` (défaut actuel) puis on
applique chaque override par `setattr(cfg, k, v)` ; toute clé hors whitelist → `ValueError` (→ 400).
*(Import d'une lignée spécifique `import_agent_id` = différé, cf. §11 : le seeding ne le câble pas encore.)*

## 6. WebSocket routing

- `/ws/flatland/{run_id}` : `server = manager.get_run(run_id)` ; si `None` → `await ws.close(code=1008)`.
  Sinon : `server.start(loop=asyncio.get_running_loop())` si pas running, puis boucle
  `frame = await server.queue.get(); await ws.send_json(frame)` (identique au legacy).
- `/ws/flatland` (legacy) : inchangé, connecte le run `"default"`.

## 7. Concurrence & RNG (caveat assumé)

Le moteur consomme `np.random` **global**. Deux runs concurrents = deux threads tirant du même RNG →
flux **entrelacés**, non-déterministes. Le GIL garantit l'**atomicité** de chaque appel (pas de crash /
corruption d'état), mais **pas la reproductibilité ni l'appariement**.

> **Conséquence pré-enregistrée** : l'A/B live de C2 est **observationnel** (voir l'effet d'une
> intervention en direct), **pas** une mesure appariée. La mesure rigoureuse (appariement seedé) reste
> l'affaire du **harness offline** (façon D1/S2). L'appariement live exigerait le refactor « Generator
> par run » que D1 a explicitement différé → hors périmètre C2.

## 8. Gestion d'erreurs

- `POST /runs` : cap atteint → **429** (`RunCapExceeded`) ; override hors whitelist → **400** ; corps
  invalide → 422 (pydantic).
- `DELETE /runs/{id}` : inconnu → **404** ; `"default"` → refus propre (`{stopped: false}`).
- `/ws/flatland/{run_id}` : inconnu → `close(1008)` (jamais d'exception non gérée).
- `create_run` n'écrase jamais un run existant ; `stop_run` est idempotent.
- Un run dont le thread meurt (exception interne) : `list_runs` le montre `idle` ; `stop_run` le nettoie.

## 9. Tests

- **`tests/test_flatland_manager.py`** :
  - `create_run` → run_id ; `get_run` retrouve ; `list_runs` contient le run avec label/statut.
  - **Cap** : créer `MAX_RUNS` runs OK, le suivant lève `RunCapExceeded`.
  - **Override** appliqué : `create_run({"size": 16})` → `get_run(id).world.size == 16` ; clé hors
    whitelist → `ValueError`.
  - `stop_run` retire du dict ; `stop_run("default")` → False (préservé) ; `stop_run(inconnu)` → False.
- **`tests/test_backend.py`** (extension, TestClient) :
  - `POST /api/flatland/runs` → 200 + run_id ; `GET` → liste ; `DELETE` → 200 ; DELETE inconnu → 404.
  - cap : 429 après MAX_RUNS ; override invalide → 400.
  - **WebSocket** `/ws/flatland/{run_id}` reçoit une frame (agents/preys/summary) ; `/ws/flatland`
    legacy reçoit toujours une frame.
- **Non-régression** : `tests/test_backend.py` + `tests/test_observability.py` verts.

## 10. Critères de succès

1. N runs concurrents (≤ MAX_RUNS), chacun configurable et streamé sur `/ws/flatland/{run_id}`.
2. REST lifecycle complet (POST/GET/DELETE) avec codes d'erreur corrects (429/400/404).
3. Legacy `/ws/flatland` + `flatland_server` inchangés (zéro régression du dashboard actuel).
4. Override d'intervention appliqué à la config du run (vérifié par test).
5. Caveat observationnel/RNG documenté ; suites de tests vertes.

## 11. Hors périmètre (YAGNI)

- **Frontend** (onglet compare-live, 2 vues côte à côte) — session backend ; viendra plus tard.
- **Appariement seedé live** (Generator par run) — différé avec le refactor RNG de D1.
- **Attribution KuzuDB par run** (émettre `RUN_START` de C1 depuis chaque run flatland) — extension
  possible plus tard ; C2 reste sur le streaming live.
- **Auth sur les endpoints flatland** — Chantier 4 (Sécurité).
- **Persistance/reprise d'un run** après redémarrage du backend — runs éphémères en mémoire.

## 12. Dépendances

- `FlatlandServer` (`backend/app/flatland_server.py`) — existant, self-contained.
- `backend/app/main.py` (pattern `include_router`, `@app.websocket`), `tests/test_backend.py`
  (TestClient + `client.websocket_connect`) — existants.
- `WorldConfig` (`src/environments/config.py`) — champs cibles des overrides.
