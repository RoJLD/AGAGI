# C4 — Sécurité & Sandbox — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fermer le trou RCE de `/api/sandbox/start` (whitelist + confinement), restreindre CORS, et rendre l'auth (token) et le timeout subprocess disponibles en opt-in — sans casser le dashboard local.

**Architecture:** Whitelist de scripts + CORS restreint = toujours actifs ; auth par token (header) + timeout watchdog = opt-in via env. Nouveau module `security.py` (dependency `require_token`) appliqué aux endpoints mutateurs.

**Tech Stack:** Python 3.13, FastAPI (`Depends`/`Header`/`HTTPException`), subprocess/threads, pytest + TestClient. Aucune dépendance nouvelle.

**Spec:** `docs/superpowers/specs/2026-06-22-C4-Securite-Sandbox-design.md`

---

## File Structure

- **Create** `backend/app/security.py` — `API_TOKEN` + dependency `require_token`.
- **Modify** `backend/app/routes/sandbox.py` — `dependencies=[Depends(require_token)]` sur start/stop/action/curriculum.
- **Modify** `backend/app/routes/flatland.py` — idem sur POST/DELETE `/runs`.
- **Modify** `backend/app/routes/sociologist.py` — idem sur POST `/analyze`.
- **Modify** `backend/app/main.py:21-27` — CORS depuis env, plus de `*`.
- **Modify** `backend/app/services/sandbox_service.py` — `_is_allowed_script`, `start()` refuse, `_start_watchdog`.
- **Create** `tests/test_security.py` ; **Modify** `tests/test_sandbox.py`, `.github/workflows/ci.yml:27`.

Convention : tests via `python -m pytest`. Un commit atomique par tâche.

---

### Task 1: Auth opt-in (`security.py` + dependency sur endpoints mutateurs)

**Files:**
- Create: `backend/app/security.py`
- Modify: `backend/app/routes/sandbox.py` (start l.41, stop l.58, curriculum l.62, action l.109), `flatland.py`, `sociologist.py`
- Test: `tests/test_security.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_security.py
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app import security


def test_require_token_open_when_unset(monkeypatch):
    monkeypatch.setattr(security, "API_TOKEN", None)
    assert security.require_token(x_api_token=None, authorization=None) is None


def test_require_token_enforced_when_set(monkeypatch):
    monkeypatch.setattr(security, "API_TOKEN", "s3cret")
    with pytest.raises(HTTPException):
        security.require_token(x_api_token=None, authorization=None)
    with pytest.raises(HTTPException):
        security.require_token(x_api_token="wrong", authorization=None)
    assert security.require_token(x_api_token="s3cret", authorization=None) is None
    assert security.require_token(x_api_token=None, authorization="Bearer s3cret") is None


def test_mutating_endpoint_401_without_token(monkeypatch):
    monkeypatch.setattr(security, "API_TOKEN", "s3cret")
    from backend.app.main import app
    client = TestClient(app)
    # /api/sandbox/stop est mutateur et idempotent (rien a nettoyer)
    assert client.post("/api/sandbox/stop").status_code == 401
    assert client.post("/api/sandbox/stop", headers={"X-API-Token": "s3cret"}).status_code == 200


def test_get_endpoints_stay_open(monkeypatch):
    monkeypatch.setattr(security, "API_TOKEN", "s3cret")
    from backend.app.main import app
    client = TestClient(app)
    assert client.get("/api/sandbox/status").status_code == 200   # GET non protege
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_security.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.app.security` (puis 200 au lieu de 401)

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/security.py
"""Auth opt-in par token (C4). API_TOKEN absent -> ouvert (dev local) ; defini -> exige le header."""
import os

from fastapi import Header, HTTPException

API_TOKEN = os.environ.get("AGISEED_API_TOKEN") or None   # "" ou absent -> None (ouvert)


def require_token(x_api_token: str | None = Header(default=None),
                  authorization: str | None = Header(default=None)) -> None:
    """Dependency FastAPI : laisse passer si API_TOKEN est None, sinon exige X-API-Token ou Bearer."""
    if API_TOKEN is None:
        return
    if x_api_token == API_TOKEN:
        return
    if authorization and authorization.removeprefix("Bearer ").strip() == API_TOKEN:
        return
    raise HTTPException(status_code=401, detail="Token invalide ou manquant")
```

Dans `backend/app/routes/sandbox.py` : ajouter en tête `from fastapi import Depends` (compléter l'import
fastapi existant) et `from ..security import require_token`. Puis ajouter `dependencies=[Depends(require_token)]`
aux décorateurs mutateurs :

```python
@router.post("/start", dependencies=[Depends(require_token)])
@router.post("/stop", dependencies=[Depends(require_token)])
@router.delete("/curriculum_state", dependencies=[Depends(require_token)])
@router.post("/action", dependencies=[Depends(require_token)])
```

Dans `backend/app/routes/flatland.py` : ajouter `from fastapi import Depends` (compléter) +
`from ..security import require_token`, puis :

```python
@router.post("/runs", dependencies=[Depends(require_token)])
@router.delete("/runs/{run_id}", dependencies=[Depends(require_token)])
```

Dans `backend/app/routes/sociologist.py` : ajouter `from fastapi import APIRouter, Depends` (compléter) +
`from ..security import require_token`, puis :

```python
@router.post("/analyze", dependencies=[Depends(require_token)])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_security.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/security.py backend/app/routes/sandbox.py backend/app/routes/flatland.py backend/app/routes/sociologist.py tests/test_security.py
git commit -m "feat(security): auth opt-in par token (X-API-Token/Bearer) sur endpoints mutateurs (C4)"
```

---

### Task 2: CORS restreint (plus de `*`)

**Files:**
- Modify: `backend/app/main.py:21-27`
- Test: `tests/test_security.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/test_security.py
def test_cors_is_not_wildcard():
    from backend.app.main import app
    client = TestClient(app)
    r_evil = client.get("/health", headers={"Origin": "http://evil.example"})
    assert r_evil.headers.get("access-control-allow-origin") not in ("http://evil.example", "*")
    r_ok = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert r_ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_security.py::test_cors_is_not_wildcard -v`
Expected: FAIL — l'ACAO renvoie `*` (origine evil acceptée)

- [ ] **Step 3: Write minimal implementation**

Dans `backend/app/main.py`, remplacer le bloc CORS (l.21-27) par :

```python
import os

_origins = os.environ.get("AGISEED_CORS_ORIGINS", "http://localhost:5173,http://localhost:4173")
ALLOWED_ORIGINS = [o.strip() for o in _origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

(Si `import os` est déjà présent en tête de `main.py`, ne pas le dupliquer.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_security.py::test_cors_is_not_wildcard -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py tests/test_security.py
git commit -m "feat(security): CORS restreint a l'origine frontend (env AGISEED_CORS_ORIGINS), plus de wildcard (C4)"
```

---

### Task 3: Whitelist de scripts + confinement (le fix RCE)

**Files:**
- Modify: `backend/app/services/sandbox_service.py` (`_is_allowed_script` + garde en tête de `start`)
- Test: `tests/test_sandbox.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/test_sandbox.py
def test_is_allowed_script_accepts_known_rejects_traversal():
    svc = SandboxService()
    assert svc._is_allowed_script("main_biosphere.py") is True
    assert svc._is_allowed_script("../../evil.py") is False
    assert svc._is_allowed_script("__inconnu__.py") is False
    assert svc._is_allowed_script("main_biosphere.txt") is False
    assert svc._is_allowed_script("") is False


def test_start_rejects_unauthorized_script_without_launching():
    svc = SandboxService()
    res = svc.start({"script_name": "../../x.py"})
    assert res["status"] == "error" and "autoris" in res["message"].lower()
    assert svc.get_status()["running"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sandbox.py -k "allowed_script or unauthorized" -v`
Expected: FAIL — `AttributeError: 'SandboxService' object has no attribute '_is_allowed_script'`

- [ ] **Step 3: Write minimal implementation**

Dans `backend/app/services/sandbox_service.py`, ajouter la méthode (par ex. après `get_available_scripts`) :

```python
    def _is_allowed_script(self, name: str) -> bool:
        """Autorise un script SEULEMENT s'il est decouvert (racine/tools) ET confine dans PROJECT_ROOT.
        Tue le path-traversal (../../) et l'execution de fichiers arbitraires."""
        if not name or not name.endswith(".py"):
            return False
        resolved = os.path.realpath(os.path.join(PROJECT_ROOT, name))
        root = os.path.realpath(PROJECT_ROOT)
        try:
            if os.path.commonpath([resolved, root]) != root:
                return False
        except ValueError:
            return False
        return name.replace("\\", "/") in set(self.get_available_scripts())
```

Dans `start()`, tout en haut, **après** la lecture de `main_script = config.get("script_name")` et la
garde « script non spécifié », et **avant** la garde `isfile` / toute migration / tout `Popen`, ajouter :

```python
        if not self._is_allowed_script(main_script):
            return {"status": "error", "message": f"Script non autorisé : {main_script}"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_sandbox.py -k "allowed_script or unauthorized" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/sandbox_service.py tests/test_sandbox.py
git commit -m "fix(security): whitelist scripts + confinement PROJECT_ROOT dans sandbox.start (anti-RCE/traversal) (C4)"
```

---

### Task 4: Timeout subprocess opt-in (watchdog)

**Files:**
- Modify: `backend/app/services/sandbox_service.py` (`_start_watchdog` + branchement dans `start`)
- Test: `tests/test_sandbox.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/test_sandbox.py
def test_watchdog_kills_process_after_timeout():
    import subprocess
    import sys
    import time
    svc = SandboxService()
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    svc._start_watchdog(proc, 1.0)
    time.sleep(4)
    assert proc.poll() is not None   # tué par le watchdog
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sandbox.py::test_watchdog_kills_process_after_timeout -v`
Expected: FAIL — `AttributeError: 'SandboxService' object has no attribute '_start_watchdog'`

- [ ] **Step 3: Write minimal implementation**

Dans `backend/app/services/sandbox_service.py`, ajouter la méthode :

```python
    def _start_watchdog(self, proc, timeout_s: float):
        """Tue proc apres timeout_s s'il tourne encore (thread daemon). Best-effort."""
        def _kill_after():
            end = time.time() + timeout_s
            while time.time() < end:
                if proc.poll() is not None:
                    return
                time.sleep(1.0)
            if proc.poll() is None:
                self._logs.append(f"⏱️ Timeout {timeout_s}s atteint -> arrêt du process")
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
        threading.Thread(target=_kill_after, daemon=True).start()
```

Dans `start()`, juste après le `Popen` du process principal (après `self._processes["main"] = subprocess.Popen(...)`
et le démarrage du thread de logs), ajouter :

```python
            _timeout = os.environ.get("AGISEED_SANDBOX_TIMEOUT")
            if _timeout:
                try:
                    _t = float(_timeout)
                    if _t > 0:
                        self._start_watchdog(self._processes["main"], _t)
                except ValueError:
                    pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_sandbox.py::test_watchdog_kills_process_after_timeout -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/sandbox_service.py tests/test_sandbox.py
git commit -m "feat(security): timeout subprocess opt-in (watchdog AGISEED_SANDBOX_TIMEOUT) (C4)"
```

---

### Task 5: CI + intégration & non-régression + roadmap

**Files:**
- Modify: `.github/workflows/ci.yml:27`, `roadmap.md`

- [ ] **Step 1: Ajouter test_security.py à la CI**

Dans `.github/workflows/ci.yml`, ajouter `tests/test_security.py` à la liste pytest (après
`tests/test_sandbox.py`).

- [ ] **Step 2: Non-régression complète (liste CI)**

Run: `python -m pytest tests/test_backend.py tests/sandbox/test_visualization.py tests/test_observability.py tests/test_flatland_manager.py tests/test_strategy.py tests/test_sociologist.py tests/test_sandbox.py tests/test_security.py -q`
Expected: PASS

- [ ] **Step 3: Vérifier la syntaxe YAML**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('YAML OK')"`
Expected: `YAML OK`

- [ ] **Step 4: Smoke import (app charge avec CORS env + deps auth)**

Run: `python -c "from backend.app.main import app; print('OK', len(app.routes), 'routes')"`
Expected: `OK <n> routes`

- [ ] **Step 5: Mettre à jour la roadmap (C4 livré, roadmap backend complète)**

Modifier `roadmap.md` : marquer **C4** livré (whitelist anti-RCE + CORS restreint + auth opt-in + timeout
opt-in) et noter la **roadmap backend C1-C4 complète**.

```bash
git add .github/workflows/ci.yml roadmap.md
git commit -m "docs(roadmap): C4 securite & sandbox livre, roadmap backend C1-C4 complete (C4)"
```

---

## Self-Review (effectuée)

**1. Spec coverage :**
- §4 whitelist + confinement (`_is_allowed_script`, garde dans `start`) → Task 3. ✓
- §5 CORS restreint (env) → Task 2. ✓
- §6 auth opt-in (`require_token` + dependencies sur mutateurs) → Task 1. ✓
- §7 timeout watchdog opt-in → Task 4. ✓
- §9 tests (auth open/enforced/401/GET-ouvert, CORS, whitelist, start-rejette, watchdog) → Tasks 1-4. ✓
- §9 CI + non-régression → Task 5. ✓

**2. Placeholder scan :** aucun TODO/TBD ; code complet (patterns `main.py` CORS, `sandbox.py` décorateurs
l.41/58/62/109, `sandbox_service.start`, `Header`/`Depends` FastAPI lus). `commonpath` lève `ValueError`
si lecteurs différents (Windows) → capté.

**3. Type consistency :** `require_token(x_api_token, authorization)` cohérent Task 1 (def↔test↔Depends).
`security.API_TOKEN` monkeypatché cohérent Task 1↔2. `_is_allowed_script(name)->bool` cohérent Task 3.
`_start_watchdog(proc, timeout_s)` cohérent Task 4. `AGISEED_*` env vars cohérents spec↔plan.
