# C1 — Observabilité & Provenance — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Donner au backend l'observabilité (santé KuzuDB + métriques AsyncLogger) et un ledger de provenance (seed+commit+config_hash+git_dirty ↔ KPIs, cross-link KuzuDB) pour tuer les « données fantômes » et rendre chaque run traçable/reproductible.

**Architecture:** Le moteur (`Harness`/`AsyncLogger`) gagne des compteurs + un nœud `Run` de provenance ; le backend ajoute un `provenance_service` (lecture `results/*.json` + KuzuDB read-only via la connexion partagée) et un router `observability` (4 endpoints). Tout dégrade gracieusement sans KuzuDB.

**Tech Stack:** Python 3.13, FastAPI + TestClient, KuzuDB (kuzu), numpy, pytest. Aucune dépendance nouvelle.

**Spec:** `docs/superpowers/specs/2026-06-15-C1-Observability-Provenance-design.md`

---

## File Structure

- **Modify** `src/graph_rag/async_logger.py` — compteurs + `metrics()` ; `RUN_START`/`RUN_END` (état `_current_run` + nœud `Run`) ; lien `ERA_RESULT`→`Run`.
- **Modify** `src/seed_ai/harness.py` — helpers `_git_dirty`/`_config_hash` ; `save(data, config=None)` ; `Harness.__init__(config=None)` ; `__enter__`/`__exit__` émettent `RUN_START`/`RUN_END`.
- **Create** `backend/app/services/provenance_service.py` — `list_runs`, `get_run`, `kuzu_health`, `logger_metrics`.
- **Create** `backend/app/routes/observability.py` — 4 endpoints GET.
- **Modify** `backend/app/main.py:16-39` — enregistrer le router.
- **Create** `tests/sandbox/test_async_logger.py` — métriques + état run.
- **Modify** `tests/sandbox/test_harness.py` — provenance dans `save`.
- **Create** `tests/test_observability.py` — endpoints backend (TestClient).

Convention : tests via `python -m pytest`. Un commit atomique par tâche.

---

### Task 1: `AsyncLogger` — compteurs + `metrics()`

**Files:**
- Modify: `src/graph_rag/async_logger.py:16-22` (`__init__`), `:124-134` (`_worker`), `:321-322` (except)
- Test: `tests/sandbox/test_async_logger.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_async_logger.py
from src.graph_rag.async_logger import AsyncLogger


def test_metrics_has_expected_keys():
    lg = AsyncLogger(db_path="data/nonexistent_test.db")
    m = lg.metrics()
    for k in ("events_processed", "events_by_type", "error_count",
              "last_latency_ms", "queue_size", "running", "db_connected"):
        assert k in m
    assert m["events_processed"] == 0
    assert m["events_by_type"] == {}
    assert m["queue_size"] == 0
    assert m["running"] is False
    assert m["db_connected"] is False


def test_metrics_queue_size_reflects_pending():
    lg = AsyncLogger(db_path="data/nonexistent_test.db")
    lg._running = True                 # autorise emit() sans démarrer le worker
    lg.emit("PING", {"x": 1})
    assert lg.metrics()["queue_size"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_async_logger.py -k metrics -v`
Expected: FAIL — `AttributeError: 'AsyncLogger' object has no attribute 'metrics'`

- [ ] **Step 3: Write minimal implementation**

Dans `__init__` (après `self._events_processed = 0`, l.22) ajouter :

```python
        self._events_by_type: Dict[str, int] = {}
        self._error_count = 0
        self._last_latency_ms = 0.0
        self._current_run = None       # provenance : id du Run courant (RUN_START/RUN_END)
```

Dans `_worker`, remplacer le bloc de traitement (l.125-129) :

```python
            try:
                event = self.queue.get(timeout=0.1)
                self._process_event(event, db_conn)
                self.queue.task_done()
                self._events_processed += 1
```

par (mesure de latence + compteur par type) :

```python
            try:
                event = self.queue.get(timeout=0.1)
                _t0 = time.time()
                self._process_event(event, db_conn)
                self._last_latency_ms = (time.time() - _t0) * 1000.0
                self.queue.task_done()
                self._events_processed += 1
                et = event.get("type", "?")
                self._events_by_type[et] = self._events_by_type.get(et, 0) + 1
```

Dans `_process_event`, dans le `except` final (l.321-322), ajouter le compteur d'erreurs :

```python
        except Exception as e:
            self._error_count += 1
            log.error(f"KuzuDB insert error for {e_type}: {e}")
```

Ajouter la méthode `metrics()` (après `get_db`, vers l.33) :

```python
    def metrics(self) -> Dict[str, Any]:
        """Snapshot d'observabilité (best-effort, lecture de compteurs in-process, non bloquant)."""
        return {
            "events_processed": self._events_processed,
            "events_by_type": dict(self._events_by_type),
            "error_count": self._error_count,
            "last_latency_ms": round(self._last_latency_ms, 3),
            "queue_size": self.queue.qsize(),
            "running": self._running,
            "db_connected": self.get_db() is not None,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_async_logger.py -k metrics -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/graph_rag/async_logger.py tests/sandbox/test_async_logger.py
git commit -m "feat(observability): AsyncLogger.metrics() + compteurs (queue/events/erreurs/latence) (C1)"
```

---

### Task 2: `AsyncLogger` — `RUN_START`/`RUN_END` + nœud `Run` + lien `ERA_RESULT`

**Files:**
- Modify: `src/graph_rag/async_logger.py:179-205` (haut de `_process_event`), `:267-296` (branche `ERA_RESULT`)
- Test: `tests/sandbox/test_async_logger.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_async_logger.py
def test_run_start_sets_current_run_without_db():
    lg = AsyncLogger(db_path="data/nonexistent_test.db")
    # _process_event avec conn=None ne doit pas crasher ET doit poser l'état run (en mémoire)
    lg._process_event({"type": "RUN_START", "timestamp": 1,
                       "payload": {"name": "exp", "seed": 7, "commit": "abc", "config_hash": "h"}}, None)
    assert lg._current_run == "run_7_abc"
    lg._process_event({"type": "RUN_END", "timestamp": 2, "payload": {}}, None)
    assert lg._current_run is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_async_logger.py -k run_start -v`
Expected: FAIL — `assert None == 'run_7_abc'` (état non posé)

- [ ] **Step 3: Write minimal implementation**

Dans `_process_event`, JUSTE après l'extraction `e_type/payload/timestamp` (vers l.183) et **AVANT** le `if conn is None:` (l.186), ajouter le suivi d'état run (indépendant de la DB) :

```python
        # Provenance : état du Run courant, suivi en mémoire (même sans DB).
        if e_type == "RUN_START":
            self._current_run = f"run_{payload.get('seed')}_{payload.get('commit')}"
        elif e_type == "RUN_END":
            self._current_run = None
```

Dans le `if conn is None` (l.186-189), c'est inchangé (early return, pas de crash).

Dans la chaîne `elif` d'insertion DB, ajouter la création du nœud `Run` (par ex. juste après la branche `LANGUAGE_ALIGNMENT`, n'importe où dans la chaîne) :

```python
            elif e_type == "RUN_START":
                try:
                    conn.execute("CREATE NODE TABLE IF NOT EXISTS Run (id STRING, name STRING, seed INT64, commit STRING, config_hash STRING, git_dirty BOOLEAN, timestamp DOUBLE, PRIMARY KEY (id))")
                    rid = self._current_run
                    gd = "true" if payload.get("git_dirty") else "false"
                    conn.execute(
                        f"MERGE (r:Run {{id: '{rid}'}}) SET r.name = '{payload.get('name','')}', "
                        f"r.seed = {int(payload.get('seed', 0))}, r.commit = '{payload.get('commit','')}', "
                        f"r.config_hash = '{payload.get('config_hash','')}', r.git_dirty = {gd}, r.timestamp = {timestamp}")
                except Exception as ex:
                    log.warning(f"RUN_START node write failed: {ex}")
```

Dans la branche `ERA_RESULT`, après le bloc qui crée/relie le `Result` (après l.291, dans le `try`), rattacher au Run courant :

```python
                    if self._current_run:
                        try:
                            conn.execute("CREATE REL TABLE IF NOT EXISTS BELONGS_TO_RUN (FROM Result TO Run)")
                            conn.execute(f"MATCH (r:Result {{id: '{result_id}'}}), (run:Run {{id: '{self._current_run}'}}) MERGE (r)-[:BELONGS_TO_RUN]->(run)")
                        except Exception as ex:
                            log.warning(f"BELONGS_TO_RUN link failed: {ex}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_async_logger.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/graph_rag/async_logger.py tests/sandbox/test_async_logger.py
git commit -m "feat(provenance): noeud Run (RUN_START/END) + lien ERA_RESULT->Run (C1)"
```

---

### Task 3: `Harness` — provenance dans `save` (`config_hash` + `git_dirty`)

**Files:**
- Modify: `src/seed_ai/harness.py:47-54` (zone helpers), `:76-85` (`__init__`), `:141-148` (`save`)
- Test: `tests/sandbox/test_harness.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_harness.py
import os, json as _json
from src.seed_ai.harness import Harness


def test_save_writes_provenance_with_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    class Cfg:                          # objet config minimal
        def __init__(self): self.size = 32; self.seed = 1
    h = Harness(seed=5, name="prov", with_db=False, config=Cfg())
    path = h.save({"kpi": 1.0})
    out = _json.loads(open(path, encoding="utf-8").read())
    assert out["seed"] == 5 and "commit" in out and "git_dirty" in out
    assert "config_hash" in out and len(out["config_hash"]) >= 8


def test_save_without_config_omits_hash_and_does_not_crash(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    h = Harness(seed=5, name="prov2", with_db=False)
    out = _json.loads(open(h.save({"kpi": 2.0}), encoding="utf-8").read())
    assert "config_hash" not in out and "git_dirty" in out


def test_config_hash_deterministic_and_sensitive(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from src.seed_ai.harness import _config_hash
    class Cfg:
        def __init__(self, s): self.size = s
    assert _config_hash(Cfg(32)) == _config_hash(Cfg(32))     # déterministe
    assert _config_hash(Cfg(32)) != _config_hash(Cfg(64))     # sensible
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_harness.py -k "provenance or config_hash" -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'config'`

- [ ] **Step 3: Write minimal implementation**

Dans `src/seed_ai/harness.py`, ajouter les helpers (après `_git_short_commit`, vers l.54) :

```python
def _git_dirty():
    """True si l'arbre de travail a des modifications non commitées (run non reproductible du commit seul)."""
    try:
        import subprocess
        out = subprocess.check_output(["git", "status", "--porcelain"], stderr=subprocess.DEVNULL).decode().strip()
        return bool(out)
    except Exception:
        return False


def _config_view(config):
    """Vue sérialisable d'une config : pydantic (model_dump/dict) -> dataclass (asdict) -> __dict__."""
    for attr in ("model_dump", "dict"):
        fn = getattr(config, attr, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                pass
    try:
        import dataclasses
        if dataclasses.is_dataclass(config):
            return dataclasses.asdict(config)
    except Exception:
        pass
    return getattr(config, "__dict__", None) or {"repr": repr(config)}


def _config_hash(config):
    """Hash stable et déterministe d'une config (sha1 tronqué). 'unknown' si non sérialisable."""
    try:
        import hashlib
        blob = json.dumps(_config_view(config), sort_keys=True, default=str)
        return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:12]
    except Exception:
        return "unknown"
```

Dans `Harness.__init__`, ajouter le paramètre `config=None` (signature) et le stocker. Remplacer la ligne `def __init__(self, seed=None, name="exp", robust_K=3, num_agents=20, with_db=True, db_wait=5.0):` par :

```python
    def __init__(self, seed=None, name="exp", robust_K=3, num_agents=20, with_db=True, db_wait=5.0, config=None):
```

et ajouter dans le corps (après `self.db = None`, vers l.84) :

```python
        self._config = config          # provenance : config du run (hashée dans save / RUN_START)
```

Remplacer `save` (l.141-148) par :

```python
    def save(self, data, config=None):
        """Écrit results/<name>_<seed>.json avec provenance (seed + commit + git_dirty [+ config_hash]).
        config explicite > self._config ; sans config -> config_hash omis (run sans config inchangé)."""
        os.makedirs("results", exist_ok=True)
        cfg = config if config is not None else self._config
        out = {"name": self.name, "seed": self.seed, "commit": _git_short_commit(),
               "git_dirty": _git_dirty(), "data": data}
        if cfg is not None:
            out["config_hash"] = _config_hash(cfg)
        path = os.path.join("results", f"{self.name}_{self.seed}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, default=_json_default)
        return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_harness.py -k "provenance or config_hash" -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Non-régression Harness**

Run: `python -m pytest tests/sandbox/test_harness.py -q`
Expected: PASS (les tests Harness existants restent verts — `save` rétro-compatible)

- [ ] **Step 6: Commit**

```bash
git add src/seed_ai/harness.py tests/sandbox/test_harness.py
git commit -m "feat(provenance): Harness.save ecrit config_hash + git_dirty (ledger D1->dashboard) (C1)"
```

---

### Task 4: `Harness` — émettre `RUN_START`/`RUN_END`

**Files:**
- Modify: `src/seed_ai/harness.py:87-109` (`__enter__`/`__exit__`)
- Test: `tests/sandbox/test_harness.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_harness.py
def test_harness_emits_run_start_to_logger(monkeypatch):
    # capture les emit sans DB : on remplace l'AsyncLogger global par un espion
    import src.graph_rag.async_logger as al
    events = []
    class Spy:
        _running = True
        def start(self): pass
        def stop(self): pass
        def get_db(self): return None
        def emit(self, t, p): events.append((t, p))
    monkeypatch.setattr(al, "logger", Spy())
    with Harness(seed=3, name="run", with_db=True, db_wait=0.0):
        pass
    types = [t for t, _ in events]
    assert "RUN_START" in types and "RUN_END" in types
    start_payload = next(p for t, p in events if t == "RUN_START")
    assert start_payload["seed"] == 3 and "commit" in start_payload and "git_dirty" in start_payload
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_harness.py::test_harness_emits_run_start_to_logger -v`
Expected: FAIL — `RUN_START` absent de `types`

- [ ] **Step 3: Write minimal implementation**

Dans `Harness.__enter__`, le bloc `with_db` démarre `async_logger`. Après ce bloc (juste avant `return self`, vers l.102), émettre `RUN_START` :

```python
        # Provenance : annonce le run au logger (best-effort) -> noeud Run + current_run.
        try:
            from src.graph_rag.async_logger import logger as _alog
            _alog.emit("RUN_START", {"name": self.name, "seed": self.seed,
                                     "commit": _git_short_commit(), "git_dirty": _git_dirty(),
                                     "config_hash": _config_hash(self._config) if self._config is not None else ""})
        except Exception:
            pass
        return self
```

Dans `Harness.__exit__`, AVANT l'arrêt de l'async_logger (avant `async_logger.stop()`, vers l.106), émettre `RUN_END` :

```python
        try:
            from src.graph_rag.async_logger import logger as _alog
            _alog.emit("RUN_END", {"name": self.name, "seed": self.seed})
        except Exception:
            pass
```

(Placer ce bloc en tête de `__exit__`, avant le `if self._logger_started:` qui stoppe le logger — sinon l'emit serait ignoré, `_running=False`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_harness.py::test_harness_emits_run_start_to_logger -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/seed_ai/harness.py tests/sandbox/test_harness.py
git commit -m "feat(provenance): Harness emet RUN_START/RUN_END (provenance par run) (C1)"
```

---

### Task 5: `provenance_service` (ledger fichier + santé KuzuDB + métriques)

**Files:**
- Create: `backend/app/services/provenance_service.py`
- Test: `tests/test_observability.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_observability.py
import json
from pathlib import Path
from backend.app.services.provenance_service import ProvenanceService


def _write_run(results_dir: Path, name: str, seed: int, kpi: float):
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / f"{name}_{seed}.json").write_text(json.dumps(
        {"name": name, "seed": seed, "commit": "abc123", "git_dirty": False,
         "config_hash": "deadbeef", "data": {"kpi": kpi}}), encoding="utf-8")


def test_list_runs_reads_results_json(tmp_path):
    _write_run(tmp_path, "s2_demand", 2026, 0.9)
    svc = ProvenanceService(tmp_path)
    runs = svc.list_runs()
    assert len(runs) == 1
    r = runs[0]
    assert r["name"] == "s2_demand" and r["seed"] == 2026
    assert r["commit"] == "abc123" and r["config_hash"] == "deadbeef" and r["git_dirty"] is False


def test_get_run_returns_detail_and_unknown_is_none(tmp_path):
    _write_run(tmp_path, "exp", 7, 1.5)
    svc = ProvenanceService(tmp_path)
    assert svc.get_run("exp_7")["data"]["kpi"] == 1.5
    assert svc.get_run("does_not_exist") is None


def test_list_runs_skips_corrupt_json(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "broken_1.json").write_text("{not json", encoding="utf-8")
    _write_run(tmp_path, "ok", 1, 0.5)
    svc = ProvenanceService(tmp_path)
    names = [r["name"] for r in svc.list_runs()]
    assert "ok" in names and "broken" not in names


def test_kuzu_health_graceful_without_db(tmp_path, monkeypatch):
    import src.graph_rag.async_logger as al
    monkeypatch.setattr(al.logger, "get_db", lambda: None)
    svc = ProvenanceService(tmp_path)
    h = svc.kuzu_health()
    assert h["reachable"] is False        # pas d'exception


def test_logger_metrics_shape(tmp_path):
    svc = ProvenanceService(tmp_path)
    m = svc.logger_metrics()
    assert "queue_size" in m and "events_processed" in m
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_observability.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.services.provenance_service'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/provenance_service.py
"""Ledger de provenance + observabilité (C1).

Lit results/*.json (format Harness.save : seed/commit/config_hash/git_dirty/data) et expose la santé
KuzuDB (lecture seule, via la connexion PARTAGÉE de l'AsyncLogger -> pas de lock concurrent) + les
métriques du logger. Tout dégrade gracieusement sans KuzuDB (jamais de 500). Spec §4-§6.
"""
import json
from pathlib import Path
from typing import Optional


class ProvenanceService:
    def __init__(self, results_dir: Path):
        self.results_dir = Path(results_dir)

    def list_runs(self) -> list[dict]:
        """Tous les runs (results/*.json), triés par mtime décroissant. Ignore les fichiers corrompus."""
        runs = []
        if not self.results_dir.exists():
            return runs
        for p in sorted(self.results_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(d, dict) or "seed" not in d:
                continue
            runs.append({
                "file": p.stem,
                "name": d.get("name"), "seed": d.get("seed"),
                "commit": d.get("commit"), "config_hash": d.get("config_hash"),
                "git_dirty": d.get("git_dirty"),
                "kpis": d.get("data"), "mtime": p.stat().st_mtime,
            })
        return runs

    def get_run(self, file_stem: str) -> Optional[dict]:
        """Détail d'un run (provenance + KPIs) + cross-link KuzuDB best-effort. None si introuvable."""
        p = self.results_dir / f"{file_stem}.json"
        if not p.exists():
            return None
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
        d["kuzu"] = self._run_db_link(d.get("seed"), d.get("commit"))
        return d

    def _run_db_link(self, seed, commit) -> dict:
        """Nœud Run + Result liés (best-effort). {linked:false} si DB absente/sans correspondance."""
        db = self._get_db()
        if db is None or seed is None or commit is None:
            return {"linked": False}
        try:
            import kuzu
            conn = kuzu.Connection(db)
            rid = f"run_{seed}_{commit}"
            res = conn.execute(f"MATCH (r:Run {{id: '{rid}'}})<-[:BELONGS_TO_RUN]-(x:Result) RETURN count(x)")
            n = res.get_next()[0] if res.has_next() else 0
            return {"linked": True, "run_id": rid, "result_count": int(n)}
        except Exception:
            return {"linked": False}

    def kuzu_health(self) -> dict:
        """Santé KuzuDB (lecture seule, connexion partagée). reachable/writable/schema/counts."""
        from src.graph_rag.async_logger import logger as async_logger
        db = self._get_db()
        if db is None:
            return {"reachable": False, "writable": False, "schema_present": False, "counts_by_label": {}}
        out = {"reachable": True, "writable": bool(getattr(async_logger, "_running", False)),
               "schema_present": False, "counts_by_label": {}}
        try:
            import kuzu
            conn = kuzu.Connection(db)
            for label in ("Run", "Result", "Article", "LogEvent"):
                try:
                    res = conn.execute(f"MATCH (n:{label}) RETURN count(n)")
                    out["counts_by_label"][label] = int(res.get_next()[0]) if res.has_next() else 0
                except Exception:
                    pass
            out["schema_present"] = len(out["counts_by_label"]) > 0
        except Exception:
            out["reachable"] = False
        return out

    def logger_metrics(self) -> dict:
        from src.graph_rag.async_logger import logger as async_logger
        return async_logger.metrics()

    def _get_db(self):
        try:
            from src.graph_rag.async_logger import logger as async_logger
            return async_logger.get_db()
        except Exception:
            return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_observability.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/provenance_service.py tests/test_observability.py
git commit -m "feat(backend): provenance_service (ledger + sante KuzuDB + metriques logger) (C1)"
```

---

### Task 6: Router `observability` + enregistrement

**Files:**
- Create: `backend/app/routes/observability.py`
- Modify: `backend/app/main.py:16-39`
- Test: `tests/test_observability.py`

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/test_observability.py
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_kuzu_endpoint():
    r = client.get("/api/health/kuzu")
    assert r.status_code == 200
    assert "reachable" in r.json()


def test_observability_logger_endpoint():
    r = client.get("/api/observability/logger")
    assert r.status_code == 200
    assert "queue_size" in r.json()


def test_provenance_list_endpoint():
    r = client.get("/api/provenance")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_provenance_detail_unknown_returns_404():
    r = client.get("/api/provenance/__nope__")
    assert r.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_observability.py -k "endpoint or 404" -v`
Expected: FAIL — 404 sur `/api/health/kuzu` (route non enregistrée)

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/routes/observability.py
"""Routes d'observabilité & provenance (C1) : santé KuzuDB, métriques logger, ledger des runs."""
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..services.provenance_service import ProvenanceService

router = APIRouter()

_RESULTS_DIR = Path(__file__).resolve().parents[3] / "results"
_svc = ProvenanceService(_RESULTS_DIR)


@router.get("/health/kuzu")
def health_kuzu() -> dict:
    return _svc.kuzu_health()


@router.get("/observability/logger")
def observability_logger() -> dict:
    return _svc.logger_metrics()


@router.get("/provenance")
def provenance_list() -> list:
    return _svc.list_runs()


@router.get("/provenance/{file_stem}")
def provenance_detail(file_stem: str) -> dict:
    run = _svc.get_run(file_stem)
    if run is None:
        raise HTTPException(status_code=404, detail=f"run inconnu: {file_stem}")
    return run
```

Dans `backend/app/main.py`, ajouter l'import (après l.16) :

```python
from .routes.observability import router as observability_router
```

et l'enregistrement (après l.39) :

```python
app.include_router(observability_router, prefix="/api", tags=["Observability"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_observability.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/observability.py backend/app/main.py tests/test_observability.py
git commit -m "feat(backend): router observability (/health/kuzu, /observability/logger, /provenance) (C1)"
```

---

### Task 7: Intégration & non-régression

**Files:**
- Test: (aucun nouveau) — vérifie l'ensemble

- [ ] **Step 1: Suite backend complète (non-régression)**

Run: `python -m pytest tests/test_backend.py tests/test_observability.py -q`
Expected: PASS (les 18 tests backend existants + les 10 nouveaux)

- [ ] **Step 2: Suite moteur impactée**

Run: `python -m pytest tests/sandbox/test_harness.py tests/sandbox/test_async_logger.py -q`
Expected: PASS

- [ ] **Step 3: Smoke import du backend (l'app se charge avec le nouveau router)**

Run: `python -c "from backend.app.main import app; print([r.path for r in app.routes if 'provenance' in r.path or 'health/kuzu' in r.path])"`
Expected: liste contenant `/api/health/kuzu`, `/api/provenance`, `/api/provenance/{file_stem}`

- [ ] **Step 4: Vérifier que le verdict S2 est servi par le ledger (si un results/s2_demand_*.json existe)**

Run: `python -c "from pathlib import Path; from backend.app.services.provenance_service import ProvenanceService; svc=ProvenanceService(Path('results')); print([r['name'] for r in svc.list_runs()][:5])"`
Expected: la liste des runs présents (dont `s2_demand` si un pilote a tourné) — sinon liste des runs existants, sans erreur.

- [ ] **Step 5: Mettre à jour la roadmap (C1 livré)**

Modifier `roadmap.md` §🛠️ Dev : marquer l'item 7 (versioning données + drain KuzuDB instrumenté) comme **en cours/livré (C1 : observabilité + ledger de provenance)**.

```bash
git add roadmap.md
git commit -m "docs(roadmap): C1 observabilite + ledger de provenance livre (Dev #7)"
```

---

## Self-Review (effectuée)

**1. Spec coverage :**
- §3/§4 ledger (config_hash+git_dirty, nœud Run, cross-link) → Tasks 2,3,5. ✓
- §5 santé KuzuDB (lecture seule, connexion partagée, counts, DB absente gracieuse) → Task 5 (`kuzu_health`). ✓
- §6 métriques AsyncLogger (queue/events/erreurs/latence) → Task 1. ✓
- §4 « sert S2 gratuitement » → Task 7 Step 4 (vérification). ✓
- §7 dégradation gracieuse → Tasks 5 (`kuzu_health`/`get_run` sans DB), 1 (`db_connected`). ✓
- §8 tests (health DB présente/absente, métriques, ledger liste/détail/corrompu, save provenance, RUN_START) → Tasks 1-6. ✓

**2. Placeholder scan :** aucun TODO/TBD ; tout le code est complet et déterminable (patterns backend/AsyncLogger/Harness lus). Les requêtes Kuzu utilisent `IF NOT EXISTS` + try/except comme le reste du fichier.

**3. Type consistency :** `ProvenanceService(results_dir)` → `.list_runs()/.get_run(file_stem)/.kuzu_health()/.logger_metrics()` cohérent Tasks 5↔6. `AsyncLogger.metrics()` clés cohérentes Task 1↔5↔6. `Harness(...,config=None)`/`save(data, config=None)`/`_config_hash` cohérents Tasks 3↔4. `_current_run = "run_<seed>_<commit>"` cohérent Tasks 2 (set) ↔ 5 (`_run_db_link` lit le même id).
