# C2 — A/B Live Multi-run — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettre N runs flatland concurrents (≤4), chacun configurable et streamé sur `/ws/flatland/{run_id}`, pour comparer 2 lignées (baseline vs intervention) côte à côte en direct.

**Architecture:** Dé-singletoniser `FlatlandServer` (paramétrer son constructeur) + un `FlatlandManager` (dict de runs, cap, cycle de vie) ; ajouter un router REST `/api/flatland/runs` et un WebSocket `/ws/flatland/{run_id}` ; garder `flatland_server` + `/ws/flatland` legacy intacts.

**Tech Stack:** Python 3.13, FastAPI + TestClient (websocket_connect), threads/asyncio, pytest. Aucune dépendance nouvelle.

**Spec:** `docs/superpowers/specs/2026-06-15-C2-Flatland-Multirun-design.md`

---

## File Structure

- **Modify** `backend/app/flatland_server.py` — `FlatlandServer.__init__(config_overrides, pop_size, label)` + `WHITELIST` ; `FlatlandManager` + `RunCapExceeded` ; singletons `flatland_server` (`"default"`) + `flatland_manager`.
- **Create** `backend/app/routes/flatland.py` — POST/GET/DELETE `/runs`.
- **Modify** `backend/app/main.py:16-39` (router), `:50-61` (ajout `/ws/flatland/{run_id}`).
- **Create** `tests/test_flatland_manager.py` — manager + serveur paramétré.
- **Modify** `tests/test_backend.py` — endpoints REST + ws par run_id.

Convention : tests via `python -m pytest`. Un commit atomique par tâche.

---

### Task 1: `FlatlandServer` paramétré (overrides whitelistés)

**Files:**
- Modify: `backend/app/flatland_server.py:13-22` (`__init__`), `:209` (singleton)
- Test: `tests/test_flatland_manager.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_flatland_manager.py
import pytest
from backend.app.flatland_server import FlatlandServer


def test_server_applies_whitelisted_override():
    s = FlatlandServer(config_overrides={"size": 16, "num_altars": 2}, pop_size=2, label="t")
    assert s.cfg.size == 16 and s.cfg.num_altars == 2
    assert s.label == "t" and s.pop_size == 2


def test_server_rejects_unknown_override():
    with pytest.raises(ValueError):
        FlatlandServer(config_overrides={"evil_key": 1}, pop_size=2)


def test_server_default_config_unchanged():
    s = FlatlandServer(pop_size=2)
    assert s.cfg.size == 32 and s.cfg.num_altars == 5 and s.cfg.prey_mode == "semi"
    assert s.label is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_flatland_manager.py -k server -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'config_overrides'`

- [ ] **Step 3: Write minimal implementation**

Dans `backend/app/flatland_server.py`, ajouter la whitelist en tête (après les imports, vers l.12) :

```python
# Overrides de config autorisés pour un run (la "variable d'intervention" de l'A/B). Spec §5.
WHITELIST = {"active_exp_variable", "robust_hof_K", "mutation_rate", "base_metabolism",
             "forage_payoff", "size", "num_altars", "prey_mode"}
```

Remplacer `FlatlandServer.__init__` (l.14-22) par :

```python
    def __init__(self, config_overrides=None, pop_size=10, label=None):
        cfg = WorldConfig(size=32, num_altars=5, prey_mode="semi")
        for k, v in (config_overrides or {}).items():
            if k not in WHITELIST:
                raise ValueError(f"override de config non autorise: {k} (autorises: {sorted(WHITELIST)})")
            setattr(cfg, k, v)
        self.cfg = cfg
        self.label = label
        self.world = Biosphere3D(self.cfg)
        self.queue = None
        self.running = False
        self.loop = None
        self.era = 1                 # run ÉVOLUTIVE live : la pop descend du HoF, qui s'améliore par ère
        self.pop_size = pop_size
        self._seed_from_hof()
```

Remplacer le singleton (l.209) :

```python
flatland_server = FlatlandServer(label="default")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_flatland_manager.py -k server -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/flatland_server.py tests/test_flatland_manager.py
git commit -m "feat(flatland): FlatlandServer parametre (overrides whitelistes + label) (C2)"
```

---

### Task 2: `FlatlandManager` (dict de runs, cap, cycle de vie)

**Files:**
- Modify: `backend/app/flatland_server.py` (ajout `RunCapExceeded`, `FlatlandManager`, `flatland_manager`)
- Test: `tests/test_flatland_manager.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/test_flatland_manager.py
from backend.app.flatland_server import FlatlandManager, RunCapExceeded


def _mgr():
    return FlatlandManager(FlatlandServer(label="default", pop_size=2))


def test_manager_create_get_list():
    mgr = _mgr()
    rid = mgr.create_run(config_overrides={"size": 16}, pop_size=2, label="exp")
    assert mgr.get_run(rid).cfg.size == 16
    runs = mgr.list_runs()
    assert any(r["run_id"] == rid and r["label"] == "exp" and r["status"] == "idle" for r in runs)
    assert any(r["run_id"] == "default" for r in runs)


def test_manager_stop_run_and_default_preserved():
    mgr = _mgr()
    rid = mgr.create_run(pop_size=2)
    assert mgr.stop_run(rid) is True
    assert mgr.get_run(rid) is None
    assert mgr.stop_run("default") is False        # default non supprimable (legacy)
    assert mgr.stop_run("inconnu") is False


def test_manager_cap_enforced():
    mgr = _mgr()                                   # default = 1 run, cap = 4
    for _ in range(3):
        mgr.create_run(pop_size=2)
    with pytest.raises(RunCapExceeded):
        mgr.create_run(pop_size=2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_flatland_manager.py -k manager -v`
Expected: FAIL — `ImportError: cannot import name 'FlatlandManager'`

- [ ] **Step 3: Write minimal implementation**

Dans `backend/app/flatland_server.py`, ajouter en tête `import uuid` (après les imports existants), puis APRÈS la classe `FlatlandServer` (avant/à la place du singleton final) :

```python
class RunCapExceeded(Exception):
    """Levée quand le nombre de runs concurrents atteint MAX_RUNS."""


class FlatlandManager:
    """Cycle de vie de N runs flatland concurrents (dict run_id -> FlatlandServer). Spec §4."""
    MAX_RUNS = 4

    def __init__(self, default_server):
        self.runs = {"default": default_server}

    def create_run(self, config_overrides=None, pop_size=10, label=None):
        if len(self.runs) >= self.MAX_RUNS:
            raise RunCapExceeded(f"cap atteint ({self.MAX_RUNS} runs)")
        # FlatlandServer valide les overrides (ValueError si hors whitelist) AVANT d'occuper un slot.
        server = FlatlandServer(config_overrides=config_overrides, pop_size=pop_size, label=label)
        run_id = uuid.uuid4().hex[:8]
        self.runs[run_id] = server
        return run_id

    def get_run(self, run_id):
        return self.runs.get(run_id)

    def stop_run(self, run_id) -> bool:
        if run_id == "default" or run_id not in self.runs:
            return False
        self.runs[run_id].stop()
        del self.runs[run_id]
        return True

    def list_runs(self) -> list:
        return [{"run_id": rid, "label": s.label,
                 "status": "running" if s.running else "idle",
                 "era": s.era, "agent_count": len(s.world.agents)}
                for rid, s in self.runs.items()]
```

Remplacer la ligne du singleton par les deux singletons :

```python
flatland_server = FlatlandServer(label="default")
flatland_manager = FlatlandManager(flatland_server)
```

(Si `flatland_server = FlatlandServer(label="default")` existe déjà de Task 1, ne garder qu'une définition + ajouter `flatland_manager`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_flatland_manager.py -k manager -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/flatland_server.py tests/test_flatland_manager.py
git commit -m "feat(flatland): FlatlandManager (dict de runs, cap MAX_RUNS, cycle de vie) (C2)"
```

---

### Task 3: Router REST `/api/flatland/runs` + enregistrement

**Files:**
- Create: `backend/app/routes/flatland.py`
- Modify: `backend/app/main.py:16` (import), `:39` (include_router)
- Test: `tests/test_backend.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/test_backend.py
def test_flatland_runs_crud() -> None:
    r = client.post("/api/flatland/runs", json={"config_overrides": {"size": 16}, "pop_size": 2, "label": "e2e"})
    assert r.status_code == 200
    rid = r.json()["run_id"]
    try:
        lst = client.get("/api/flatland/runs").json()
        assert any(x["run_id"] == rid and x["label"] == "e2e" for x in lst)
    finally:
        d = client.delete(f"/api/flatland/runs/{rid}")
        assert d.status_code == 200 and d.json()["stopped"] is True


def test_flatland_delete_unknown_returns_404() -> None:
    assert client.delete("/api/flatland/runs/__nope__").status_code == 404


def test_flatland_bad_override_returns_400() -> None:
    r = client.post("/api/flatland/runs", json={"config_overrides": {"evil_key": 1}, "pop_size": 2})
    assert r.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_backend.py -k flatland_runs -v`
Expected: FAIL — 404 sur `POST /api/flatland/runs` (route absente)

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/routes/flatland.py
"""Routes REST du multi-run flatland (C2) : créer / lister / supprimer des runs A/B live."""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..flatland_server import flatland_manager, RunCapExceeded

router = APIRouter()


class CreateRunBody(BaseModel):
    config_overrides: Optional[dict] = None
    pop_size: int = 10
    label: Optional[str] = None


@router.post("/runs")
def create_run(body: CreateRunBody) -> dict:
    try:
        run_id = flatland_manager.create_run(body.config_overrides, body.pop_size, body.label)
    except RunCapExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"run_id": run_id}


@router.get("/runs")
def list_runs() -> list:
    return flatland_manager.list_runs()


@router.delete("/runs/{run_id}")
def delete_run(run_id: str) -> dict:
    if not flatland_manager.stop_run(run_id):
        raise HTTPException(status_code=404, detail=f"run inconnu ou non supprimable: {run_id}")
    return {"stopped": True}
```

Dans `backend/app/main.py`, ajouter l'import (après l.16) :

```python
from .routes.flatland import router as flatland_router
```

et l'enregistrement (après l.39) :

```python
app.include_router(flatland_router, prefix="/api/flatland", tags=["Flatland"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_backend.py -k flatland -v`
Expected: PASS (les 3 nouveaux + l'existant `test_flatland_websocket_streams_frames`)

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/flatland.py backend/app/main.py tests/test_backend.py
git commit -m "feat(backend): router /api/flatland/runs (POST/GET/DELETE, 429/400/404) (C2)"
```

---

### Task 4: WebSocket `/ws/flatland/{run_id}` (+ legacy conservé)

**Files:**
- Modify: `backend/app/main.py:50-61` (ajout du ws paramétré, legacy inchangé)
- Test: `tests/test_backend.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/test_backend.py
def test_ws_flatland_run_id_streams_frames() -> None:
    rid = client.post("/api/flatland/runs", json={"pop_size": 2, "label": "wt"}).json()["run_id"]
    try:
        with client.websocket_connect(f"/ws/flatland/{rid}") as ws:
            frame = ws.receive_json()
            assert "agents" in frame and "summary" in frame
    finally:
        client.delete(f"/api/flatland/runs/{rid}")


def test_ws_flatland_unknown_run_closes() -> None:
    from starlette.websockets import WebSocketDisconnect
    import pytest
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/flatland/__nope__") as ws:
            ws.receive_json()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_backend.py -k "ws_flatland_run_id or unknown_run" -v`
Expected: FAIL — 404/erreur sur `/ws/flatland/{rid}` (route ws paramétrée absente)

- [ ] **Step 3: Write minimal implementation**

Dans `backend/app/main.py`, APRÈS le `@app.websocket("/ws/flatland")` legacy (qui reste **inchangé**, vers l.61), ajouter :

```python
@app.websocket("/ws/flatland/{run_id}")
async def websocket_flatland_run(websocket: WebSocket, run_id: str):
    await websocket.accept()
    from .flatland_server import flatland_manager
    server = flatland_manager.get_run(run_id)
    if server is None:
        await websocket.close(code=1008)        # run inconnu
        return
    if not server.running:
        server.start(loop=asyncio.get_running_loop())
    try:
        while True:
            frame = await server.queue.get()
            await websocket.send_json(frame)
    except WebSocketDisconnect:
        pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_backend.py -k "ws_flatland" -v`
Expected: PASS (run_id stream + unknown closes + legacy `test_flatland_websocket_streams_frames`)

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py tests/test_backend.py
git commit -m "feat(backend): ws /ws/flatland/{run_id} (stream par run, close 1008 si inconnu) (C2)"
```

---

### Task 5: Intégration & non-régression

**Files:** (aucun nouveau)

- [ ] **Step 1: Suite backend complète + manager (non-régression)**

Run: `python -m pytest tests/test_backend.py tests/test_observability.py tests/test_flatland_manager.py -q`
Expected: PASS (backend existant + observability C1 + flatland C2 ; legacy `/ws/flatland` intact)

- [ ] **Step 2: Smoke import (app charge avec router + ws paramétré)**

Run: `python -c "from backend.app.main import app; print(sorted(r.path for r in app.routes if 'flatland' in r.path))"`
Expected: liste contenant `/api/flatland/runs`, `/api/flatland/runs/{run_id}`, `/ws/flatland`, `/ws/flatland/{run_id}`

- [ ] **Step 3: Vérifier le cap de bout en bout (manager partagé propre)**

Run: `python -c "from backend.app.flatland_server import FlatlandManager, FlatlandServer, RunCapExceeded; m=FlatlandManager(FlatlandServer(label='default', pop_size=2)); [m.create_run(pop_size=2) for _ in range(3)];
try:
    m.create_run(pop_size=2); print('FAIL: pas de cap')
except RunCapExceeded:
    print('OK cap')"`
Expected: `OK cap`

- [ ] **Step 4: Mettre à jour la roadmap (C2 livré)**

Modifier `roadmap.md` : marquer le chantier backend **C2 (A/B live multi-run)** comme livré (manager + REST + `/ws/flatland/{run_id}`), caveat observationnel.

```bash
git add roadmap.md
git commit -m "docs(roadmap): C2 A/B live multi-run livre (FlatlandManager + ws par run) (C2)"
```

---

## Self-Review (effectuée)

**1. Spec coverage :**
- §3/§4 FlatlandManager (dict, create/get/stop/list, cap, default préservé) → Task 2. ✓
- §3 FlatlandServer paramétré → Task 1. ✓
- §3 router REST (POST/GET/DELETE) → Task 3. ✓
- §6 ws `/ws/flatland/{run_id}` + legacy conservé → Task 4. ✓
- §5 overrides whitelistés (ValueError → 400) → Tasks 1 (whitelist) + 3 (400). ✓
- §8 erreurs (429 cap, 400 override, 404 delete, close 1008 ws) → Tasks 2/3/4. ✓
- §9 tests (manager, cap, override, REST CRUD, ws par run, ws inconnu, legacy) → Tasks 1-4. ✓
- §7 caveat RNG observationnel → documenté dans le spec (pas de code).

**2. Placeholder scan :** aucun TODO/TBD ; tout le code est complet (patterns `FlatlandServer`/`main.py`/`WorldConfig`/TestClient lus). `setattr(cfg, k, v)` validé (main_biosphere fait `config.robust_hof_K = 4`).

**3. Type consistency :** `FlatlandServer(config_overrides, pop_size, label)` cohérent Tasks 1↔2↔3. `FlatlandManager.create_run/get_run/stop_run/list_runs` cohérent Tasks 2↔3↔4. `RunCapExceeded` cohérent Tasks 2↔3. `flatland_manager` singleton importé cohérent Tasks 3↔4. `run_id` (`uuid4().hex[:8]`) + `"default"` préservé cohérent Tasks 2↔4.
