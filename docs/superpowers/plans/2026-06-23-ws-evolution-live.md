# /ws/evolution temps-réel — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Streamer en direct les métriques par génération d'un run lancé via le Bac à sable, dans l'onglet Évolution.

**Architecture:** Le run append des événements JSONL dans `results/live_progress.jsonl` via un helper `emit_progress` opt-in (env `AGISEED_LIVE_PROGRESS` posée par le sandbox ; no-op sinon). Le WS `/ws/evolution` *tail -f* ce fichier et pousse chaque événement. Le front consomme via `useWebSocket` et rend une vue live (sparkline). Découplage total : aucun accès à la simulation, append-only fichier → pas de risque non-repro.

**Tech Stack:** Python 3.13 / FastAPI / pytest ; React 18 / TypeScript / Vite / Vitest+RTL.

## Global Constraints

- Sécurité F3.12 déjà en place : ne pas régresser (sandbox bornée par liste blanche, auth opt-in).
- `emit_progress` doit être **no-op** sans la variable d'env, et ne **jamais** propager d'exception.
- Aucun changement d'API REST → **pas** de régénération OpenAPI/`schema.ts` (les WS sont hors schéma).
- Commits en français, conventionnels, sans emoji ; finir le message par `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Schéma d'événement canonique : `{"run": str, "generation": int, "fitness": float, "accuracy": float | None, "size": int | None}`.

---

### Task 1: Helper producteur `emit_progress`

**Files:**
- Create: `src/seed_ai/live_progress.py`
- Test: `tests/sandbox/test_live_progress.py`

**Interfaces:**
- Produces: `emit_progress(event: dict) -> None` ; constante `ENV_VAR = "AGISEED_LIVE_PROGRESS"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_live_progress.py
import json
from src.seed_ai.live_progress import emit_progress, ENV_VAR


def test_noop_when_env_unset(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    emit_progress({"run": "x", "generation": 1, "fitness": 0.5})
    assert not list(tmp_path.iterdir())  # rien créé, pas d'exception


def test_writes_jsonl_when_env_set(tmp_path, monkeypatch):
    sink = tmp_path / "live.jsonl"
    monkeypatch.setenv(ENV_VAR, str(sink))
    emit_progress({"run": "x", "generation": 1, "fitness": 0.5})
    emit_progress({"run": "x", "generation": 2, "fitness": 0.7})
    lines = sink.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1])["fitness"] == 0.7
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python -m pytest tests/sandbox/test_live_progress.py -q`
Expected: FAIL (`ModuleNotFoundError: src.seed_ai.live_progress`)

- [ ] **Step 3: Write minimal implementation**

```python
# src/seed_ai/live_progress.py
"""Puits de progression live (/ws/evolution). Append-only, opt-in via env.

emit_progress n'écrit QUE si AGISEED_LIVE_PROGRESS est défini (posé par le sandbox au
lancement d'un run). Sinon : no-op total -> aucun impact sur les runs CLI / tests /
sessions parallèles. Ne propage jamais d'exception : la télémétrie ne doit pas pouvoir
faire échouer le run qu'elle observe.
"""
from __future__ import annotations

import json
import os

ENV_VAR = "AGISEED_LIVE_PROGRESS"


def emit_progress(event: dict) -> None:
    path = os.environ.get(ENV_VAR)
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python -m pytest tests/sandbox/test_live_progress.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/seed_ai/live_progress.py tests/sandbox/test_live_progress.py
git commit -m "feat(evolution): helper emit_progress (puits JSONL live, opt-in env, no-op par défaut)"
```

---

### Task 2: Service tail incrémental

**Files:**
- Create: `backend/app/services/live_progress_service.py`
- Test: `tests/test_live_progress_tail.py`

**Interfaces:**
- Produces: `class LiveProgressTail(path: Path)` avec `read_new() -> list[dict]` (événements ajoutés depuis le dernier appel ; reset si truncation ; lignes invalides/partielles ignorées) et `reset() -> None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_live_progress_tail.py
from backend.app.services.live_progress_service import LiveProgressTail


def test_read_new_incremental(tmp_path):
    sink = tmp_path / "live.jsonl"
    tail = LiveProgressTail(sink)
    assert tail.read_new() == []  # fichier absent
    sink.write_text('{"generation": 1}\n', encoding="utf-8")
    assert tail.read_new() == [{"generation": 1}]
    assert tail.read_new() == []  # rien de nouveau
    with sink.open("a", encoding="utf-8") as f:
        f.write('{"generation": 2}\n')
    assert tail.read_new() == [{"generation": 2}]


def test_read_new_resets_on_truncation(tmp_path):
    sink = tmp_path / "live.jsonl"
    sink.write_text('{"generation": 1}\n{"generation": 2}\n', encoding="utf-8")
    tail = LiveProgressTail(sink)
    assert len(tail.read_new()) == 2
    sink.write_text('{"generation": 1}\n', encoding="utf-8")  # nouveau run, plus petit
    assert tail.read_new() == [{"generation": 1}]


def test_read_new_skips_invalid_and_partial(tmp_path):
    sink = tmp_path / "live.jsonl"
    sink.write_text('not json\n{"generation": 5}\n{partial', encoding="utf-8")
    tail = LiveProgressTail(sink)
    # 'not json' ignorée ; gen 5 ok ; '{partial' (pas de \n) pas encore consommée
    assert tail.read_new() == [{"generation": 5}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python -m pytest tests/test_live_progress_tail.py -q`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/live_progress_service.py
"""Tail incrémental du puits de progression live (results/live_progress.jsonl).

read_new() renvoie les événements ajoutés depuis le dernier appel. On ne consomme que
les lignes complètes (terminées par \\n) : une ligne partielle (write en cours) est
gardée pour le prochain appel. Reset de l'offset si le fichier a rétréci (nouveau run
qui a tronqué). Ligne JSON invalide -> ignorée. Aucune dépendance à la simulation.
"""
from __future__ import annotations

import json
from pathlib import Path


class LiveProgressTail:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._offset = 0

    def reset(self) -> None:
        self._offset = 0

    def read_new(self) -> list[dict]:
        if not self.path.exists():
            self._offset = 0
            return []
        size = self.path.stat().st_size
        if size < self._offset:  # fichier tronqué -> nouveau run
            self._offset = 0
        if size == self._offset:
            return []
        start = self._offset
        with self.path.open("rb") as f:
            f.seek(start)
            raw = f.read()
        nl = raw.rfind(b"\n")
        if nl == -1:
            return []  # pas encore de ligne complète
        consumed = raw[: nl + 1]
        self._offset = start + len(consumed)
        events: list[dict] = []
        for line in consumed.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                continue
        return events
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python -m pytest tests/test_live_progress_tail.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/live_progress_service.py tests/test_live_progress_tail.py
git commit -m "feat(backend): LiveProgressTail (lecture incrémentale du puits live, reset sur truncation)"
```

---

### Task 3: Réécrire `/ws/evolution` en tail -f

**Files:**
- Modify: `backend/app/main.py` (imports ; constante `LIVE_PROGRESS_PATH` ; corps de `websocket_evolution`)
- Test: `tests/test_backend.py` (ajout)

**Interfaces:**
- Consumes: `LiveProgressTail` (Task 2).
- Produces: WS `/ws/evolution` qui envoie en `send_json` chaque événement ajouté ; lit `backend.app.main.LIVE_PROGRESS_PATH` (monkeypatchable en test).

- [ ] **Step 1: Write the failing test** (ajouter dans `tests/test_backend.py`, avant `def test_flatland_websocket_streams_frames`)

```python
def test_ws_evolution_streams_appended_events(tmp_path, monkeypatch) -> None:
    sink = tmp_path / "live_progress.jsonl"
    import backend.app.main as main_mod
    monkeypatch.setattr(main_mod, "LIVE_PROGRESS_PATH", sink)
    sink.write_text('{"run":"demo","generation":1,"fitness":0.4}\n', encoding="utf-8")
    with client.websocket_connect("/ws/evolution") as ws:
        event = ws.receive_json()
        assert event["generation"] == 1
        assert event["run"] == "demo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python -m pytest tests/test_backend.py::test_ws_evolution_streams_appended_events -q`
Expected: FAIL (l'endpoint actuel rejoue `stream_experiment_updates`, n'envoie pas `run`/`demo` ; `LIVE_PROGRESS_PATH` n'existe pas → AttributeError au monkeypatch)

- [ ] **Step 3: Implement — remplacer l'endpoint**

Ajouter l'import près des autres imports de services dans `backend/app/main.py` :

```python
from .services.live_progress_service import LiveProgressTail
```

Ajouter la constante juste après `RESULTS_DIR = Path(__file__).resolve().parents[3] / "results"` :

```python
LIVE_PROGRESS_PATH = RESULTS_DIR / "live_progress.jsonl"
```

Remplacer entièrement le corps de `websocket_evolution` :

```python
@app.websocket("/ws/evolution")
async def websocket_evolution(websocket: WebSocket) -> None:
    await websocket.accept()
    tail = LiveProgressTail(LIVE_PROGRESS_PATH)
    try:
        while True:
            for event in tail.read_new():
                await websocket.send_json(event)
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python -m pytest tests/test_backend.py::test_ws_evolution_streams_appended_events -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py tests/test_backend.py
git commit -m "feat(backend): /ws/evolution tail -f du puits live (remplace le rejeu historique)"
```

---

### Task 4: Câblage sandbox (arme le puits)

**Files:**
- Modify: `backend/app/services/sandbox_service.py` (méthode `_arm_live_progress` ; appel dans `start()`)
- Test: `tests/test_backend.py` (ajout)

**Interfaces:**
- Produces: `SandboxService._arm_live_progress(env: dict) -> str` — pose `env["AGISEED_LIVE_PROGRESS"]`, vide/crée le fichier `results/live_progress.jsonl`, renvoie son chemin. Appelée par `start()` avant le `Popen`.

- [ ] **Step 1: Write the failing test** (ajouter dans `tests/test_backend.py`)

```python
def test_arm_live_progress_sets_env_and_clears_file() -> None:
    import os as _os
    env: dict = {}
    path = sandbox_service._arm_live_progress(env)
    assert env["AGISEED_LIVE_PROGRESS"] == path
    assert _os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        assert f.read() == ""  # vidé au démarrage
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python -m pytest tests/test_backend.py::test_arm_live_progress_sets_env_and_clears_file -q`
Expected: FAIL (`AttributeError: _arm_live_progress`)

- [ ] **Step 3: Implement**

Ajouter la méthode dans la classe `SandboxService` (au-dessus de `def start`) :

```python
    def _arm_live_progress(self, env: dict) -> str:
        """Arme le puits de progression live pour CE run : pose l'env + vide le fichier."""
        progress_path = os.path.join(PROJECT_ROOT, "results", "live_progress.jsonl")
        os.makedirs(os.path.dirname(progress_path), exist_ok=True)
        try:
            open(progress_path, "w", encoding="utf-8").close()  # vide / crée
        except Exception:
            pass
        env["AGISEED_LIVE_PROGRESS"] = progress_path
        return progress_path
```

Dans `start()`, juste après la ligne `env["PYTHONPATH"] = PROJECT_ROOT  # Ensure it can import src.*`, ajouter :

```python
        self._arm_live_progress(env)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python -m pytest tests/test_backend.py -q`
Expected: PASS (tous, dont le nouveau)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/sandbox_service.py tests/test_backend.py
git commit -m "feat(sandbox): arme le puits live (AGISEED_LIVE_PROGRESS + vidage) au lancement d'un run"
```

---

### Task 5: Instrumenter `CurriculumRunner`

**Files:**
- Modify: `src/curriculum/runner.py` (import ; un appel `emit_progress` dans `run()`)
- Test: `tests/sandbox/test_curriculum_live_progress.py`

**Interfaces:**
- Consumes: `emit_progress` (Task 1) ; `CurriculumRunner(stages, run_era_fn, grad_cfg)`, `EraResult(competence, champion_agent_id)`.
- Produces: un événement `{"run": stage.name, "generation": era, "fitness": result.competence, "accuracy": None, "size": None}` par ère.

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_curriculum_live_progress.py
import json
from src.curriculum.runner import CurriculumRunner, WorldStage, GraduationConfig, EraResult
from src.seed_ai.live_progress import ENV_VAR


def test_curriculum_runner_emits_progress_per_era(tmp_path, monkeypatch):
    sink = tmp_path / "live.jsonl"
    monkeypatch.setenv(ENV_VAR, str(sink))

    def fake_era(world_type, carried, keep):
        return EraResult(competence=0.5)  # < c_floor (0.6) -> jamais diplômé

    runner = CurriculumRunner(
        stages=[WorldStage("soup")],
        run_era_fn=fake_era,
        grad_cfg=GraduationConfig(max_eras=3),
    )
    runner.run()

    lines = sink.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3  # 3 ères
    assert json.loads(lines[0]) == {
        "run": "soup", "generation": 1, "fitness": 0.5, "accuracy": None, "size": None,
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python -m pytest tests/sandbox/test_curriculum_live_progress.py -q`
Expected: FAIL (fichier vide / inexistant : aucun emit_progress encore)

- [ ] **Step 3: Implement**

Ajouter en tête de `src/curriculum/runner.py` (après les imports existants) :

```python
from src.seed_ai.live_progress import emit_progress
```

Dans `run()`, juste après la ligne `history.append(result.competence)`, ajouter :

```python
                emit_progress({
                    "run": stage.name,
                    "generation": era,
                    "fitness": result.competence,
                    "accuracy": None,
                    "size": None,
                })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python -m pytest tests/sandbox/test_curriculum_live_progress.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/curriculum/runner.py tests/sandbox/test_curriculum_live_progress.py
git commit -m "feat(curriculum): emit_progress par ère dans CurriculumRunner (producteur live)"
```

---

### Task 6: Vue front « Évolution en direct »

**Files:**
- Create: `frontend/src/components/LiveEvolution.tsx`
- Create: `frontend/src/components/LiveEvolution.test.tsx`
- Modify: `frontend/src/App.tsx` (supprimer le hook inline `/ws/evolution` + l'état `wsLog` + le panneau « Flux évolution » ; importer et rendre `<LiveEvolution />` dans l'onglet `evolution`)

**Interfaces:**
- Consumes: `useWebSocket<T>(path, onMessage)` (existant) ; endpoint `/ws/evolution` (Task 3) ; événements `{run?, gate?, generation?, fitness?, accuracy?, size?}`.
- Produces: composant `LiveEvolution()` (default export nommé).

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/LiveEvolution.test.tsx
import { act, render, screen } from "@testing-library/react";
import { vi } from "vitest";

let captured: ((e: unknown) => void) | null = null;
vi.mock("../hooks/useWebSocket", () => ({
  useWebSocket: (_path: string, onMessage: (e: unknown) => void) => {
    captured = onMessage;
    return { status: "open" };
  },
}));

import { LiveEvolution } from "./LiveEvolution";

test("affiche l'empty state puis les points reçus", () => {
  render(<LiveEvolution />);
  expect(screen.getByText(/Aucun run en cours/)).toBeTruthy();
  act(() => {
    captured!({ run: "soup", generation: 1, fitness: 0.4 });
    captured!({ run: "soup", generation: 2, fitness: 0.55 });
  });
  expect(screen.getByText("soup")).toBeTruthy();
  expect(screen.getByText("0.5500")).toBeTruthy();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- LiveEvolution`
Expected: FAIL (`Cannot find module './LiveEvolution'`)

- [ ] **Step 3: Implement the component**

```tsx
// frontend/src/components/LiveEvolution.tsx
import { useRef, useState } from "react";
import { useWebSocket } from "../hooks/useWebSocket";
import { Badge } from "./ui/Badge";

type EvoEvent = {
  run?: string; gate?: string; generation?: number;
  fitness?: number; accuracy?: number | null; size?: number | null;
};
type Point = { generation: number; fitness: number };

const MAX = 200;

function sparkline(values: number[], color: string, w = 640, h = 120) {
  if (!values.length) return null;
  const max = Math.max(...values, 1e-9);
  const min = Math.min(...values, 0);
  const sx = (i: number) => (i / Math.max(values.length - 1, 1)) * w;
  const sy = (v: number) => h - ((v - min) / (max - min || 1)) * h;
  const d = values.map((v, i) => `${i === 0 ? "M" : "L"} ${sx(i)} ${sy(v)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="chart-svg" preserveAspectRatio="none" role="img" aria-label="évolution live">
      <path d={d} fill="none" style={{ stroke: color }} strokeWidth={2.5} />
    </svg>
  );
}

export function LiveEvolution() {
  const [points, setPoints] = useState<Point[]>([]);
  const [run, setRun] = useState<string>("");
  const bufRef = useRef<Point[]>([]);

  const { status } = useWebSocket<EvoEvent>("/ws/evolution", (e) => {
    if (typeof e.fitness !== "number" || typeof e.generation !== "number") return;
    setRun(e.run ?? e.gate ?? "");
    const next = [...bufRef.current, { generation: e.generation, fitness: e.fitness }].slice(-MAX);
    bufRef.current = next;
    setPoints(next);
  });

  const statusLabel = status === "open" ? "connecté" : status === "connecting" ? "connexion…" : "hors-ligne";
  const last = points[points.length - 1];

  return (
    <div className="edr-dashboard">
      <h2>Évolution en direct</h2>
      <p className="edr-intro">
        Métriques par génération d'un run lancé via le Bac à sable, streamées en direct
        (<code>/ws/evolution</code>). WS : <strong>{statusLabel}</strong>.
      </p>
      {points.length === 0 ? (
        <p className="text-dim">Aucun run en cours — lance une expérience via le Bac à sable.</p>
      ) : (
        <>
          <div className="live-stats">
            <div className="live-stat"><span>Run</span><strong>{run || "—"}</strong></div>
            <div className="live-stat"><span>Génération</span><strong>{last?.generation ?? "—"}</strong></div>
            <div className="live-stat"><span>Fitness</span><strong>{last ? last.fitness.toFixed(4) : "—"}</strong></div>
            <div className="live-stat"><span>Points</span><strong>{points.length}</strong></div>
          </div>
          <article className="edr-card">
            <header className="edr-card-head"><Badge variant="teal">LIVE</Badge><h3>Fitness par génération</h3></header>
            {sparkline(points.map((p) => p.fitness), "var(--viz-1)")}
          </article>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run the component test to verify it passes**

Run: `npm --prefix frontend run test -- LiveEvolution`
Expected: PASS

- [ ] **Step 5: Wire into App.tsx, remove the redundant text panel**

Dans `frontend/src/App.tsx` :

a. Ajouter l'import avec les autres imports de composants :
```tsx
import { LiveEvolution } from "./components/LiveEvolution";
```

b. Supprimer le hook inline (le bloc `useWebSocket<{ gate?: ... }>("/ws/evolution", ...)` qui alimente `setWsLog`).

c. Supprimer la déclaration d'état `wsLog`/`setWsLog` (rechercher `wsLog` : `const [wsLog, setWsLog] = useState<string[]>([]);`).

d. Supprimer le panneau latéral « Flux évolution » :
```tsx
          <div className="ws-panel">
            <h3>Flux évolution</h3>
            <div className="ws-log">
              {wsLog.length ? wsLog.map((line, index) => <div key={index}>{line}</div>) : <div>En attente de données...</div>}
            </div>
          </div>
```

e. Dans le bloc `{tab === "evolution" && (` , rendre `<LiveEvolution />` en tête du fragment, juste après `<>` et avant `<h2>Évolution dynamique</h2>` :
```tsx
          {tab === "evolution" && (
            <>
              <LiveEvolution />
              <h2>Évolution dynamique</h2>
```

- [ ] **Step 6: Run frontend tests + build to verify no regression / no unused vars**

Run: `npm --prefix frontend run test && npm --prefix frontend run build`
Expected: tous les tests PASS ; build `tsc` vert (aucune variable `wsLog` orpheline, aucun import inutilisé).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/LiveEvolution.tsx frontend/src/components/LiveEvolution.test.tsx frontend/src/App.tsx
git commit -m "feat(frontend): vue Évolution en direct (sparkline live /ws/evolution), remplace le panneau texte"
```

---

### Task 7: Vérification globale + mise à jour roadmap

**Files:**
- Modify: `docs/FRONTEND_UIUX_ROADMAP.md` (marquer le WS live livré ; roadmap frontend terminée)

- [ ] **Step 1: Suite complète backend**

Run: `PYTHONPATH=. python -m pytest tests/test_backend.py tests/sandbox/test_visualization.py tests/sandbox/test_live_progress.py tests/sandbox/test_curriculum_live_progress.py tests/test_live_progress_tail.py -q`
Expected: tout PASS.

- [ ] **Step 2: Gate parité (ne doit pas régresser)**

Run: `PYTHONIOENCODING=utf-8 PYTHONPATH=. python tools/parity_check.py --strict`
Expected: `[ok] aucun invariant dur violé`, exit 0.

- [ ] **Step 3: Front test + build**

Run: `npm --prefix frontend run test && npm --prefix frontend run build`
Expected: tests PASS, build vert.

- [ ] **Step 4: Mettre à jour la roadmap**

Dans `docs/FRONTEND_UIUX_ROADMAP.md`, remplacer la ligne `- **Reste** : WS ...` par :
```markdown
- **WS `/ws/evolution` temps-réel** ✅ : suivi live d'un run lancé. Producteur `emit_progress` (opt-in env `AGISEED_LIVE_PROGRESS`, no-op par défaut) instrumenté dans `CurriculumRunner` ; sandbox arme/vide le puits ; `/ws/evolution` tail -f ; vue « Évolution en direct » (sparkline) dans l'onglet Évolution.
- **Roadmap frontend : terminée.**
```

- [ ] **Step 5: Commit**

```bash
git add docs/FRONTEND_UIUX_ROADMAP.md
git commit -m "docs(roadmap): WS /ws/evolution temps-réel livré — roadmap frontend terminée"
```

---

## Self-Review

- **Couverture spec** : producteur (T1+T5), sandbox arme/vide (T4), tail+WS (T2+T3), vue front (T6), tests à chaque tâche, vérif globale (T7). ✅ Raffinements documentés : producteur = `CurriculumRunner` (la classe `Population` d'`evolution.py` est du code mort, non instanciée) ; front = enrichir l'onglet `evolution` existant (déjà consommateur de `/ws/evolution`) plutôt qu'un nouvel onglet.
- **Placeholders** : aucun — tout le code est explicite.
- **Cohérence des types** : schéma d'événement `{run, generation, fitness, accuracy, size}` identique du producteur (T1/T5) au consommateur (T6) ; `read_new()` / `_arm_live_progress` / `LIVE_PROGRESS_PATH` nommés de façon cohérente entre tâches.
