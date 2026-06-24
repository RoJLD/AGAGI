# C3 — Brancher les stubs + Dette/CI — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tuer la dernière donnée fantôme (mock stratégie), réparer le bug dormant du schéma `Article` (sociologue renvoyait toujours `[]`), couvrir `sandbox_service`, et fermer le trou CI (les tests C1/C2 ne tournaient pas).

**Architecture:** Honnêteté côté `strategy.py` (flag `source`, plus de mock) ; unification du nœud `Article` sur `date` (l'intrus `Sociologist` corrigé) ; nouveaux tests backend rapides ; CI étendue. Backend + 1 fichier moteur (`src/graph_rag/sociologist.py`).

**Tech Stack:** Python 3.13, FastAPI + TestClient, KuzuDB (kuzu) temp pour fixtures, pytest. Aucune dépendance nouvelle.

**Spec:** `docs/superpowers/specs/2026-06-16-C3-Stubs-Dette-CI-design.md`

---

## File Structure

- **Modify** `backend/app/routes/strategy.py:88-138` — supprimer le mock, ajouter `source`.
- **Modify** `src/graph_rag/sociologist.py:104-110` — `Article{timestamp}` → `Article{date}`.
- **Modify** `backend/app/routes/sociologist.py:9-13,36-57` — `ArticleResponse.timestamp`→`date` ; query `a.date`.
- **Create** `tests/test_strategy.py`, `tests/test_sociologist.py`, `tests/test_sandbox.py`.
- **Modify** `.github/workflows/ci.yml:27` — ajouter les fichiers de tests.

Convention : tests via `python -m pytest`. Un commit atomique par tâche.

---

### Task 1: `strategy.py` — honnête (tuer le mock, flag `source`)

**Files:**
- Modify: `backend/app/routes/strategy.py:88-138`
- Test: `tests/test_strategy.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_strategy.py
import gc

from fastapi.testclient import TestClient


def _empty_schema_db(tmp_path):
    """KuzuDB temp avec le schéma (Article/WorldVersion/...) mais AUCUNE donnée de stratégie."""
    from src.graph_rag.experiment_tracker import ExperimentGraph
    db_path = str(tmp_path / "strat.db")
    g = ExperimentGraph(db_path, read_only=False)   # bootstrap schema, pas de WorldVersion
    del g.conn
    del g.db
    gc.collect()
    return db_path


def test_strategy_tree_is_honest_when_empty(tmp_path, monkeypatch):
    db_path = _empty_schema_db(tmp_path)
    from backend.app.services.kuzu_service import kuzu_service
    monkeypatch.setattr(kuzu_service, "db_path", db_path)
    from backend.app.main import app
    client = TestClient(app)
    body = client.get("/api/strategy/strategy_tree").json()
    # plus AUCUN mock fantôme
    assert "StoneAge (Mock)" not in str(body)
    assert "Tabula_Rasa" not in str(body)
    # flag de source explicite
    assert body["source"] in ("empty", "error")
    assert body["tree"] == {} and body["sankey"]["nodes"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_strategy.py -v`
Expected: FAIL — `KeyError: 'source'` (ou `StoneAge (Mock)` présent)

- [ ] **Step 3: Write minimal implementation**

Dans `backend/app/routes/strategy.py`, remplacer tout le bloc depuis `if has_results:` (l.88) jusqu'au
`return {"tree": ..., "sankey": ...}` (l.132-135) ET le `except` (l.136-138) par :

```python
        if has_results:
            tree_data = {
                "name": "AGIseed Base",
                "children": [
                    {"name": w, "children": children} for w, children in world_dict.items()
                ]
            }
            sankey_data = {
                "nodes": [{"id": name, "group": grp} for name, grp in sankey_nodes_set],
                "links": sankey_links
            }
            return {"tree": tree_data, "sankey": sankey_data, "source": "live"}

        # DB sans donnée de stratégie : état vide HONNÊTE (plus de mock fantôme). Le frontend
        # distingue "pas encore de run" (empty) de vrai (live) via `source`.
        return {"tree": {}, "sankey": {"nodes": [], "links": []}, "source": "empty"}
    except Exception as e:
        log.error(f"Strategy Tree Error: {e}")
        return {"tree": {}, "sankey": {"nodes": [], "links": []}, "source": "error"}
```

(Les lignes 100-130, le bloc `else:` du mock `StoneAge (Mock)`, disparaissent entièrement.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_strategy.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/strategy.py tests/test_strategy.py
git commit -m "fix(strategy): tuer le mock fantome, flag source live/empty/error (C3)"
```

---

### Task 2: `Article` — unifier le schéma sur `date`

**Files:**
- Modify: `src/graph_rag/sociologist.py:104-110`
- Modify: `backend/app/routes/sociologist.py:9-13`, `:36-57`
- Test: `tests/test_sociologist.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sociologist.py
import gc

from fastapi.testclient import TestClient


def _article_db(tmp_path):
    """KuzuDB temp avec le schéma Article(id,title,content,date) + 1 article."""
    from src.graph_rag.experiment_tracker import ExperimentGraph
    db_path = str(tmp_path / "soc.db")
    g = ExperimentGraph(db_path, read_only=False)
    g.conn.execute(
        "CREATE (a:Article {id: 'a1', title: 'T1', content: 'C1', date: '2026-06-16 10:00:00'})")
    del g.conn
    del g.db
    gc.collect()
    return db_path


def test_sociologist_articles_returns_real_article(tmp_path, monkeypatch):
    db_path = _article_db(tmp_path)
    from backend.app.services.kuzu_service import kuzu_service
    monkeypatch.setattr(kuzu_service, "db_path", db_path)
    from backend.app.main import app
    client = TestClient(app)
    r = client.get("/api/sociologist/articles")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["id"] == "a1" and data[0]["date"] == "2026-06-16 10:00:00"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sociologist.py -v`
Expected: FAIL — réponse vide `[]` (la route interroge `a.timestamp`, colonne absente) ou erreur de
validation (`ArticleResponse` attend `timestamp`)

- [ ] **Step 3: Write minimal implementation**

Dans `src/graph_rag/sociologist.py`, remplacer (l.104-110) :

```python
        article_id = str(uuid.uuid4())[:8]
        title = f"Étude de l'évolution : {intervention}"
        timestamp = int(time.time() * 1000)

        # Save to KuzuDB
        safe_content = content.replace("'", "\\'")
        query = f"""
        CREATE (a:Article {{id: '{article_id}', title: '{title}', content: '{safe_content}', timestamp: {timestamp}}})
        """
```

par (schéma unifié sur `date`, comme async_logger/experiment_tracker) :

```python
        article_id = str(uuid.uuid4())[:8]
        title = f"Étude de l'évolution : {intervention}"
        date_str = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S")

        # Save to KuzuDB (schéma Article unifié sur `date`, cohérent avec async_logger/experiment_tracker)
        safe_content = content.replace("'", "\\'")
        query = f"""
        CREATE (a:Article {{id: '{article_id}', title: '{title}', content: '{safe_content}', date: '{date_str}'}})
        """
```

Vérifier que `import datetime` est présent en tête de `src/graph_rag/sociologist.py` ; sinon l'ajouter
à côté des imports existants (`import time`, `import uuid`).

Dans `backend/app/routes/sociologist.py`, remplacer le modèle (l.9-13) :

```python
class ArticleResponse(BaseModel):
    id: str
    title: str
    content: str
    date: str
```

et `get_articles` (l.43-56) — la requête et le mapping :

```python
        tracker = ExperimentGraph(kuzu_service.db_path, read_only=True)
        query = "MATCH (a:Article) RETURN a.id, a.title, a.content, a.date ORDER BY a.date DESC"
        res = tracker.conn.execute(query)

        articles = []
        while res.has_next():
            row = res.get_next()
            articles.append({
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "date": row[3]
            })

        return articles
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_sociologist.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/graph_rag/sociologist.py backend/app/routes/sociologist.py tests/test_sociologist.py
git commit -m "fix(sociologist): unifier le schema Article sur date (bug dormant: articles toujours vides) (C3)"
```

---

### Task 3: Tests `sandbox_service` (chemins d'erreur + statut/logs, sans subprocess)

**Files:**
- Test: `tests/test_sandbox.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sandbox.py
from backend.app.services.sandbox_service import SandboxService


def test_status_idle_when_nothing_running():
    svc = SandboxService()
    st = svc.get_status()
    assert st["running"] is False and st["pid"] is None


def test_stop_when_idle_is_graceful():
    svc = SandboxService()
    res = svc.stop()
    assert res["status"] == "success"
    assert res["message"] == "Aucune expérimentation en cours"


def test_start_without_script_errors():
    svc = SandboxService()
    res = svc.start({})
    assert res["status"] == "error" and "script principal" in res["message"]


def test_start_missing_script_errors():
    svc = SandboxService()
    res = svc.start({"script_name": "__does_not_exist__.py"})
    assert res["status"] == "error" and "introuvable" in res["message"]


def test_logs_deque_roundtrip():
    svc = SandboxService()
    assert svc.get_logs() == []
    svc._logs.append("ligne 1")
    assert svc.get_logs() == ["ligne 1"]


def test_available_scripts_lists_python_files():
    svc = SandboxService()
    scripts = svc.get_available_scripts()
    assert isinstance(scripts, list) and any(s.endswith(".py") for s in scripts)
```

- [ ] **Step 2: Run test to verify it fails... or passes**

Run: `python -m pytest tests/test_sandbox.py -v`
Expected: PASS immédiat — ces tests caractérisent le comportement EXISTANT de `sandbox_service`
(aucun code applicatif à écrire ; ils ferment un trou de couverture). Si un test échoue, c'est un vrai
bug à corriger dans `sandbox_service.py`.

- [ ] **Step 3: (pas d'implémentation — tests de caractérisation)**

Aucun changement de code applicatif. Ces tests verrouillent le contrat de `SandboxService` (statut,
arrêt gracieux, validation d'entrée, logs) **sans** lancer de subprocess.

- [ ] **Step 4: Confirmer le vert**

Run: `python -m pytest tests/test_sandbox.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/test_sandbox.py
git commit -m "test(sandbox): couvrir statut/stop/start(erreurs)/logs sans subprocess (C3)"
```

---

### Task 4: CI — fermer le trou (tests C1/C2/C3)

**Files:**
- Modify: `.github/workflows/ci.yml:27`

- [ ] **Step 1: Modifier la ligne pytest**

Remplacer (l.26-27) :

```yaml
      - name: Run Python tests
        run: python -m pytest tests/test_backend.py tests/sandbox/test_visualization.py -q
```

par :

```yaml
      - name: Run Python tests
        run: >-
          python -m pytest
          tests/test_backend.py
          tests/sandbox/test_visualization.py
          tests/test_observability.py
          tests/test_flatland_manager.py
          tests/test_strategy.py
          tests/test_sociologist.py
          tests/test_sandbox.py
          -q
```

- [ ] **Step 2: Vérifier localement que la liste exacte passe**

Run: `python -m pytest tests/test_backend.py tests/sandbox/test_visualization.py tests/test_observability.py tests/test_flatland_manager.py tests/test_strategy.py tests/test_sociologist.py tests/test_sandbox.py -q`
Expected: PASS (toute la liste CI verte en local)

- [ ] **Step 3: Vérifier la syntaxe YAML**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('YAML OK')"`
Expected: `YAML OK`

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: lancer les tests C1/C2/C3 (observability, flatland, strategy, sociologist, sandbox) (C3)"
```

---

### Task 5: Intégration & non-régression + roadmap

**Files:** `roadmap.md`

- [ ] **Step 1: Non-régression backend complète**

Run: `python -m pytest tests/test_backend.py tests/test_observability.py tests/test_flatland_manager.py tests/test_strategy.py tests/test_sociologist.py tests/test_sandbox.py -q`
Expected: PASS

- [ ] **Step 2: Smoke import (app charge toujours)**

Run: `python -c "from backend.app.main import app; print('OK', len(app.routes), 'routes')"`
Expected: `OK <n> routes`

- [ ] **Step 3: Mettre à jour la roadmap (C3 livré)**

Modifier `roadmap.md` : marquer le chantier backend **C3** livré (stub stratégie honnête + schéma Article
unifié + couverture sandbox + CI étendue).

```bash
git add roadmap.md
git commit -m "docs(roadmap): C3 stubs honnetes + dette Article + CI livres (C3)"
```

---

## Self-Review (effectuée)

**1. Spec coverage :**
- §4 strategy honnête (mock supprimé, source live/empty/error) → Task 1. ✓
- §5 Article unifié sur `date` (classe Sociologist + route + modèle) → Task 2. ✓
- §6 CI (ajout tests C1/C2/C3) → Task 4. ✓
- §7 tests (strategy empty/no-mock, sociologist articles réels, sandbox sans subprocess) → Tasks 1/2/3. ✓
- §8 erreurs (strategy ne lève jamais, sociologist `[]` sans DB, pas de subprocess) → Tasks 1/2/3. ✓

**2. Placeholder scan :** aucun TODO/TBD ; code complet (patterns `strategy.py`/`sociologist.py`/
`ExperimentGraph._init_schema`/`sandbox_service` lus). Fixtures KuzuDB temp via `ExperimentGraph(read_only=
False)` (bootstrap le schéma `Article{date}` l.70) puis libération des locks (`del conn/db; gc.collect()`).

**3. Type consistency :** `source` ∈ {live, empty, error} cohérent Task 1↔spec. `ArticleResponse.date:str`
cohérent route↔modèle↔test Task 2. `kuzu_service.db_path` monkeypatché cohérent Tasks 1↔2. `SandboxService`
méthodes (`get_status`/`stop`/`start`/`get_logs`/`get_available_scripts`) cohérentes Task 3↔source lu.
