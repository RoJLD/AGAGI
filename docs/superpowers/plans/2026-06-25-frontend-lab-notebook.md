# Carnet de labo / annotations — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Annoter les runs avec des notes horodatées append-only — écriture inline dans l'Historique, lecture dans un onglet Carnet agrégé chronologique.

**Architecture:** Store JSON `results/run_notes.json` + 4 endpoints (même moule que `run_links.json`). Frontend : composant `RunNotes` (query + mutations add/delete) intégré au détail de `RunsHistoryView` ; onglet `CarnetView` (flux agrégé `/api/notes`) avec deep-link `?run=` vers l'Historique.

**Tech Stack:** React 18 + TypeScript strict + @tanstack/react-query v5 (useQuery/useMutation) + Vitest + Testing Library (frontend) ; FastAPI + Pydantic + pytest (backend).

## Global Constraints

- **Frontière session parallèle** : tâches 1-4 = frontend (`frontend/src/**` + `docs/**`) sur `feat/frontend-lab-notebook` → PR vers `main`. Tâche 5 = backend → branche depuis `feat/d1-prod-pairing`, **PR dans leur branche** (ne jamais pousser dessus directement).
- **Langue** : libellés/commentaires en français.
- **Pas d'emoji** dans le code ni les commits.
- **TypeScript** : zéro `any`, types explicites.
- **Commits** : chaque commit se termine par le trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Notes append-only horodatées** : une note = `{id, text, ts}` ; pas d'édition en place (supprimer + réajouter). Cible = **runs** uniquement.
- **`ts` stampé backend** (ISO 8601 UTC) ; le frontend ne génère pas d'horodatage.
- **Tests frontend** depuis `frontend/` : `npx vitest run <chemin>`. **Tests backend** depuis la racine : `PYTHONPATH=. python -m pytest <chemin>::<test> -v`. Un seul appel bash composé (`cd ... && ...`).

---

### Task 1: types & clés de query

**Files:**
- Modify: `frontend/src/types.ts` (ajout `RunNote`, `NoteFeedItem`)
- Modify: `frontend/src/api/queryKeys.ts` (ajout `runs.notes` + `notes`)
- Test: `frontend/src/api/queryKeys.test.ts` (créer — test trivial des clés)

**Interfaces:**
- Produces :
  - `interface RunNote { id: string; text: string; ts: string }`
  - `interface NoteFeedItem extends RunNote { run_id: string; run_name: string }`
  - `queryKeys.runs.notes(runId: string) => ["runs","notes",runId]` et `queryKeys.notes => ["notes"]`

- [ ] **Step 1: Écrire le test des clés (échoue)**

Créer `frontend/src/api/queryKeys.test.ts` :

```ts
import { test, expect } from "vitest";
import { queryKeys } from "./queryKeys";

test("clé notes d'un run", () => {
  expect(queryKeys.runs.notes("lewis_42")).toEqual(["runs", "notes", "lewis_42"]);
});

test("clé du flux notes", () => {
  expect(queryKeys.notes).toEqual(["notes"]);
});
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/api/queryKeys.test.ts`
Expected: FAIL (`runs.notes`/`notes` non définis).

- [ ] **Step 3: Ajouter les types**

Dans `frontend/src/types.ts`, après l'interface `RunDetail` (vers la ligne 153) :

```ts
/** Note de carnet attachée à un run (append-only, horodatée backend). */
export interface RunNote {
  id: string;
  text: string;
  ts: string;
}

/** Item du flux agrégé du Carnet : une note + son run d'origine. */
export interface NoteFeedItem extends RunNote {
  run_id: string;
  run_name: string;
}
```

- [ ] **Step 4: Ajouter les clés de query**

Dans `frontend/src/api/queryKeys.ts`, à l'intérieur de l'objet `runs` (après la ligne `distributions: ...`), ajouter :

```ts
    notes: (runId: string) => ["runs", "notes", runId] as const,
```

Puis, au niveau racine de l'objet (à côté de `sweeps: ["sweeps"] as const,`), ajouter :

```ts
  notes: ["notes"] as const,
```

- [ ] **Step 5: Lancer le test pour vérifier le succès**

Run : `cd frontend && npx vitest run src/api/queryKeys.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/queryKeys.ts frontend/src/api/queryKeys.test.ts
git commit -m "$(cat <<'EOF'
feat(carnet): types RunNote/NoteFeedItem + cles de query notes

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `RunNotes` — panneau notes inline (query + mutations)

**Files:**
- Create: `frontend/src/components/RunNotes.tsx`
- Test: `frontend/src/components/RunNotes.test.tsx`
- Modify: `frontend/src/styles.css` (styles minimaux `.run-notes*`)

**Interfaces:**
- Consumes: `apiFetch` ; `queryKeys.runs.notes`/`queryKeys.notes` ; `RunNote` de `../types` ; `Button` ; `useToast`.
- Produces: `function RunNotes({ runId }: { runId: string }): JSX.Element`.

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `frontend/src/components/RunNotes.test.tsx` :

```tsx
import { render, screen, fireEvent, cleanup, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
vi.mock("../contexts/ToastContext", () => ({ useToast: () => ({ notify: vi.fn() }) }));
import { apiFetch } from "../api/client";
import { RunNotes } from "./RunNotes";

afterEach(() => cleanup());

const NOTE = { id: "n1", text: "seed 3 a divergé", ts: "2026-06-25T10:00:00+00:00" };

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => (apiFetch as ReturnType<typeof vi.fn>).mockReset());

test("liste vide affiche un message", async () => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  renderWithClient(<RunNotes runId="lewis_42" />);
  expect(await screen.findByText(/Aucune note pour ce run/)).toBeTruthy();
});

test("affiche une note existante", async () => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue([NOTE]);
  renderWithClient(<RunNotes runId="lewis_42" />);
  expect(await screen.findByText("seed 3 a divergé")).toBeTruthy();
});

test("ajouter une note poste sur l'endpoint", async () => {
  const fn = apiFetch as ReturnType<typeof vi.fn>;
  fn.mockResolvedValueOnce([]); // GET initial
  fn.mockResolvedValueOnce(NOTE); // POST
  fn.mockResolvedValueOnce([NOTE]); // GET après invalidation
  renderWithClient(<RunNotes runId="lewis_42" />);
  await screen.findByText(/Aucune note pour ce run/);
  fireEvent.change(screen.getByLabelText("Nouvelle note"), { target: { value: "seed 3 a divergé" } });
  fireEvent.click(screen.getByText("Ajouter"));
  await waitFor(() =>
    expect(fn).toHaveBeenCalledWith("/api/runs/lewis_42/notes", expect.objectContaining({ method: "POST" })),
  );
});
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/components/RunNotes.test.tsx`
Expected: FAIL (`RunNotes` introuvable).

- [ ] **Step 3: Implémenter `RunNotes.tsx`**

Créer `frontend/src/components/RunNotes.tsx` :

```tsx
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import type { RunNote } from "../types";
import { Button } from "./ui/Button";
import { useToast } from "../contexts/ToastContext";

/** Carnet d'un run : notes horodatées append-only (ajout + suppression). */
export function RunNotes({ runId }: { runId: string }) {
  const queryClient = useQueryClient();
  const { notify } = useToast();
  const [text, setText] = useState("");

  const notesQuery = useQuery({
    queryKey: queryKeys.runs.notes(runId),
    queryFn: () => apiFetch<RunNote[]>(`/api/runs/${encodeURIComponent(runId)}/notes`),
  });
  const notes = notesQuery.data ?? [];

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.runs.notes(runId) });
    queryClient.invalidateQueries({ queryKey: queryKeys.notes });
  };

  const addMutation = useMutation({
    mutationFn: (body: string) =>
      apiFetch(`/api/runs/${encodeURIComponent(runId)}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: body }),
      }),
    onSuccess: () => {
      setText("");
      invalidate();
      notify("Note ajoutée.", "success");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (noteId: string) =>
      apiFetch(`/api/runs/${encodeURIComponent(runId)}/notes/${encodeURIComponent(noteId)}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      invalidate();
      notify("Note supprimée.", "success");
    },
  });

  const submit = () => {
    const t = text.trim();
    if (t) addMutation.mutate(t);
  };

  return (
    <div className="run-notes mt-4">
      <h4 style={{ margin: "0 0 var(--space-2)" }}>Carnet</h4>
      {notesQuery.isLoading ? (
        <p className="text-dim">Chargement des notes…</p>
      ) : notesQuery.error ? (
        <p className="text-dim">Notes indisponibles.</p>
      ) : notes.length === 0 ? (
        <p className="text-dim">Aucune note pour ce run.</p>
      ) : (
        <ul className="run-notes__list">
          {notes.map((n) => (
            <li key={n.id} className="run-notes__item">
              <span className="run-notes__ts text-dim">{new Date(n.ts).toLocaleString()}</span>
              <span className="run-notes__text">{n.text}</span>
              <Button
                variant="ghost"
                size="sm"
                disabled={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate(n.id)}
              >
                Supprimer
              </Button>
            </li>
          ))}
        </ul>
      )}
      <div className="row mt-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Consigner une observation…"
          rows={2}
          aria-label="Nouvelle note"
          style={{
            flex: 1,
            padding: "var(--space-2)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            background: "var(--color-surface)",
            color: "var(--color-text)",
          }}
        />
        <Button variant="ghost" size="sm" disabled={!text.trim() || addMutation.isPending} onClick={submit}>
          Ajouter
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Ajouter les styles minimaux**

Ajouter à la fin de `frontend/src/styles.css` :

```css
.run-notes__list {
  list-style: none;
  padding: 0;
  margin: 0 0 var(--space-2);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.run-notes__item {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}
.run-notes__ts {
  font-size: var(--font-size-xs);
  white-space: nowrap;
}
.run-notes__text {
  flex: 1;
}
```

- [ ] **Step 5: Lancer les tests pour vérifier le succès**

Run : `cd frontend && npx vitest run src/components/RunNotes.test.tsx`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/RunNotes.tsx frontend/src/components/RunNotes.test.tsx frontend/src/styles.css
git commit -m "$(cat <<'EOF'
feat(carnet): composant RunNotes (notes horodatees, ajout/suppression)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: intégration `RunsHistoryView` + deep-link `?run=`

**Files:**
- Modify: `frontend/src/components/RunsHistoryView.tsx`
- Test: `frontend/src/components/RunsHistoryView.test.tsx` (créer)

**Interfaces:**
- Consumes: `RunNotes` (Task 2) ; `useHashRoute` de `../hooks/useHashRoute` ; `TAB_KEYS` de `../tabs`.
- Produces: détail de run affichant `<RunNotes>` + ouverture initiale via `query.run`.

- [ ] **Step 1: Écrire le test (échoue)**

Créer `frontend/src/components/RunsHistoryView.test.tsx` :

```tsx
import { render, screen, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
vi.mock("../contexts/ToastContext", () => ({ useToast: () => ({ notify: vi.fn() }) }));
vi.mock("../hooks/useHashRoute", () => ({
  useHashRoute: () => ({
    tab: "runs",
    gate: "",
    query: { run: "lewis_42" },
    setTab: vi.fn(),
    setGate: vi.fn(),
    navigate: vi.fn(),
  }),
}));
import { apiFetch } from "../api/client";
import { RunsHistoryView } from "./RunsHistoryView";

afterEach(() => cleanup());

const RUNS = [{ run_id: "lewis_42", name: "lewis", seed: 42, commit: "abc", metrics: ["median_survival"] }];
const DETAIL = {
  run_id: "lewis_42",
  name: "lewis",
  seed: 42,
  commit: "abc",
  data: { median_survival: 0.5 },
  links: { edr: [], articles: [] },
};

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  (apiFetch as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
    if (path === "/api/runs") return Promise.resolve(RUNS);
    if (path.endsWith("/article-links")) return Promise.resolve({});
    if (path.endsWith("/notes")) return Promise.resolve([]);
    if (path === "/api/runs/lewis_42") return Promise.resolve(DETAIL);
    return Promise.resolve([]);
  });
});

test("deep-link ?run ouvre directement le détail du run", async () => {
  renderWithClient(<RunsHistoryView />);
  expect(await screen.findByText(/Détail — lewis_42/)).toBeTruthy();
});

test("le panneau Carnet est rendu dans le détail", async () => {
  renderWithClient(<RunsHistoryView />);
  expect(await screen.findByText(/Aucune note pour ce run/)).toBeTruthy();
});
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/components/RunsHistoryView.test.tsx`
Expected: FAIL (pas de deep-link ni de panneau Carnet).

- [ ] **Step 3: Câbler le deep-link et `RunNotes`**

Dans `frontend/src/components/RunsHistoryView.tsx` :

a) Ajouter les imports (après les imports existants) :

```ts
import { useHashRoute } from "../hooks/useHashRoute";
import { TAB_KEYS } from "../tabs";
import { RunNotes } from "./RunNotes";
```

b) Au début du composant (avant `const [filter, setFilter] = useState("")`), lire la query :

```ts
  const { query } = useHashRoute(TAB_KEYS, "runs");
```

c) Initialiser `selected` depuis `query.run` — remplacer `const [selected, setSelected] = useState<string | null>(null);` par :

```ts
  const [selected, setSelected] = useState<string | null>(query.run || null);
```

d) Dans le panneau de détail, juste après la `</div>` de la section « Articles Sociologue liés »
(celle qui contient le `<a href="#/laboratoire">`) et avant la fermeture `</>`, insérer :

```tsx
              <RunNotes runId={selected} />
```

(`selected` est garanti non-null dans ce bloc, narrowed par `{selected && (`.)

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run : `cd frontend && npx vitest run src/components/RunsHistoryView.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/RunsHistoryView.tsx frontend/src/components/RunsHistoryView.test.tsx
git commit -m "$(cat <<'EOF'
feat(carnet): integrer RunNotes au detail + deep-link ?run dans l'Historique

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `CarnetView` + onglet (lecture agrégée)

**Files:**
- Create: `frontend/src/components/CarnetView.tsx`
- Test: `frontend/src/components/CarnetView.test.tsx`
- Modify: `frontend/src/tabs.ts` (clé `carnet` + famille Connaissance)
- Modify: `frontend/src/App.tsx` (lazy + branche)
- Modify: `frontend/src/styles.css` (styles `.carnet-feed*`)

**Interfaces:**
- Consumes: `apiFetch` ; `queryKeys.notes` ; `NoteFeedItem` de `../types` ; `useHashRoute` ; `TAB_KEYS` ; UI `Loading`/`ErrorState`/`Empty`/`Panel`/`Button`.
- Produces: onglet `carnet` rendant le flux + deep-link `navigate("runs", { run })`.

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `frontend/src/components/CarnetView.test.tsx` :

```tsx
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

const navigate = vi.fn();
vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
vi.mock("../hooks/useHashRoute", () => ({
  useHashRoute: () => ({ tab: "carnet", gate: "", query: {}, setTab: vi.fn(), setGate: vi.fn(), navigate }),
}));
import { apiFetch } from "../api/client";
import { CarnetView } from "./CarnetView";

afterEach(() => cleanup());

const FEED = [{ run_id: "lewis_42", run_name: "lewis", id: "n1", text: "obs A", ts: "2026-06-25T10:00:00+00:00" }];

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => navigate.mockReset());

test("état vide", async () => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  renderWithClient(<CarnetView />);
  expect(await screen.findByText(/Aucune note/)).toBeTruthy();
});

test("rend le flux et deep-link vers le run", async () => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue(FEED);
  renderWithClient(<CarnetView />);
  expect(await screen.findByText("obs A")).toBeTruthy();
  fireEvent.click(screen.getByText("→ run"));
  expect(navigate).toHaveBeenCalledWith("runs", { run: "lewis_42" });
});
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/components/CarnetView.test.tsx`
Expected: FAIL (`CarnetView` introuvable).

- [ ] **Step 3: Implémenter `CarnetView.tsx`**

Créer `frontend/src/components/CarnetView.tsx` :

```tsx
import { useQuery } from "@tanstack/react-query";
import type { NoteFeedItem } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { useHashRoute } from "../hooks/useHashRoute";
import { TAB_KEYS } from "../tabs";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";
import { Panel } from "./ui/Panel";
import { Button } from "./ui/Button";

/** Carnet de labo : flux chronologique read-only de toutes les notes, deep-link vers le run. */
export function CarnetView() {
  const { navigate } = useHashRoute(TAB_KEYS, "carnet");
  const { data: notes = [], isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.notes,
    queryFn: () => apiFetch<NoteFeedItem[]>("/api/notes"),
    staleTime: 30_000,
  });

  if (isLoading) return <Loading label="Chargement du carnet…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!notes.length) {
    return <Empty message="Aucune note. Annote des runs depuis l'Historique des runs." />;
  }

  return (
    <div className="carnet-view">
      <h2>Carnet de labo</h2>
      <p className="text-dim">
        {notes.length} note{notes.length > 1 ? "s" : ""} · journal chronologique inter-runs.
      </p>
      <Panel>
        <ul className="carnet-feed">
          {notes.map((n) => (
            <li key={`${n.run_id}:${n.id}`} className="carnet-feed__item">
              <div className="carnet-feed__meta text-dim">
                {new Date(n.ts).toLocaleString()} · <strong>{n.run_name}</strong>{" "}
                <Button variant="ghost" size="sm" onClick={() => navigate("runs", { run: n.run_id })}>
                  → run
                </Button>
              </div>
              <p className="carnet-feed__text">{n.text}</p>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
```

- [ ] **Step 4: Ajouter l'onglet `carnet`**

Dans `frontend/src/tabs.ts` :

a) Ajouter `"carnet"` à `TAB_KEYS` juste après `"provenance"` :

```ts
  "provenance",
  "carnet",
] as const;
```

b) Importer l'icône `NotebookPen` (ordre alpha, après `Network`) :

```ts
  Network,
  NotebookPen,
  ShieldAlert,
```

c) Dans la famille **Connaissance** (après l'entrée `provenance`), ajouter :

```ts
      { key: "provenance", label: "Provenance", icon: Workflow },
      { key: "carnet", label: "Carnet", icon: NotebookPen },
```

- [ ] **Step 5: Câbler `App.tsx`**

Dans `frontend/src/App.tsx`, ajouter le lazy import (après `CohortView`) :

```ts
const CarnetView = lazy(() => import("./components/CarnetView").then((m) => ({ default: m.CarnetView })));
```

Puis la branche de rendu après `{tab === "provenance" && <ProvenanceView />}` :

```tsx
          {tab === "carnet" && <CarnetView />}
```

- [ ] **Step 6: Ajouter les styles minimaux**

Ajouter à la fin de `frontend/src/styles.css` :

```css
.carnet-feed {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.carnet-feed__item {
  border-left: 2px solid var(--color-border);
  padding-left: var(--space-3);
}
.carnet-feed__meta {
  font-size: var(--font-size-xs);
}
.carnet-feed__text {
  margin: var(--space-1) 0 0;
}
```

- [ ] **Step 7: Vérifier le typage et toute la suite**

Run : `cd frontend && npx tsc --noEmit`
Expected: aucune erreur.

Run : `cd frontend && npx vitest run`
Expected: PASS (toute la suite, incluant carnet).

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/CarnetView.tsx frontend/src/components/CarnetView.test.tsx frontend/src/tabs.ts frontend/src/App.tsx frontend/src/styles.css
git commit -m "$(cat <<'EOF'
feat(carnet): onglet Carnet (flux agrege /api/notes) + deep-link run

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Backend — store `run_notes.json` + 4 endpoints (patch-and-handoff vers d1)

> **Branche dédiée** : depuis `origin/feat/d1-prod-pairing`, créer `feat/notes-endpoint` (worktree séparé) ; PR **dans** `feat/d1-prod-pairing`. Indépendante des tâches 1-4.

**Files:**
- Modify: `backend/app/schemas.py` (`RunNote`, `NoteCreate`, `NoteFeedItem`)
- Modify: `backend/app/services/runs_service.py` (store + 4 méthodes)
- Modify: `backend/app/routes/runs.py` (4 routes)
- Test: `tests/test_backend.py` (racine du dépôt)
- Modify (régén) : `frontend/openapi.json`, `frontend/src/api/schema.ts`

**Interfaces:**
- Consumes: `runs_service._scan()` (déjà présent, fournit `_run_id`/`name`) ; `HTTPException` (déjà importé dans `routes/runs.py`).
- Produces: `GET/POST/DELETE /api/runs/{run_id}/notes`, `GET /api/notes`.

- [ ] **Step 1: Écrire le test backend (échoue)**

Dans `tests/test_backend.py`, ajouter (après `test_list_distributions_returns_per_seed_vals`) :

```python
def test_run_notes_roundtrip_and_feed(tmp_path, monkeypatch) -> None:
    """Carnet : add -> list -> feed agrégé (run_name) -> delete ; texte vide rejeté ; delete absent 404."""
    import backend.app.services.runs_service as rs_mod
    monkeypatch.setattr(rs_mod, "RESULTS_DIR", tmp_path)
    (tmp_path / "lewis_42.json").write_text(
        json.dumps({"name": "lewis", "seed": 42, "data": {"x": 1.0}}), encoding="utf-8"
    )

    r = client.post("/api/runs/lewis_42/notes", json={"text": "  seed 3 diverge  "})
    assert r.status_code == 200
    note = r.json()
    assert note["text"] == "seed 3 diverge"
    assert note["id"] and note["ts"]

    assert client.post("/api/runs/lewis_42/notes", json={"text": "   "}).status_code == 400

    lst = client.get("/api/runs/lewis_42/notes").json()
    assert len(lst) == 1 and lst[0]["text"] == "seed 3 diverge"

    feed = client.get("/api/notes").json()
    assert feed[0]["run_id"] == "lewis_42" and feed[0]["run_name"] == "lewis"

    assert client.delete(f"/api/runs/lewis_42/notes/{note['id']}").status_code == 200
    assert client.get("/api/runs/lewis_42/notes").json() == []
    assert client.delete("/api/runs/lewis_42/notes/nope").status_code == 404
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run : `cd "<worktree>" && PYTHONPATH=. python -m pytest tests/test_backend.py::test_run_notes_roundtrip_and_feed -v`
Expected: FAIL (routes/méthodes absentes).

- [ ] **Step 3: Ajouter les modèles Pydantic**

Dans `backend/app/schemas.py`, à côté de `DistributionSummary` :

```python
class RunNote(BaseModel):
    id: str
    text: str
    ts: str


class NoteCreate(BaseModel):
    text: str


class NoteFeedItem(BaseModel):
    run_id: str
    run_name: str
    id: str
    text: str
    ts: str
```

- [ ] **Step 4: Implémenter le store et les méthodes**

En tête de `backend/app/services/runs_service.py`, ajouter aux imports :

```python
from datetime import datetime, timezone
from uuid import uuid4
```

Puis, dans la classe `RunsService` (après les méthodes de liens), ajouter :

```python
    # --- Notes de run (carnet de labo ; store results/run_notes.json) ---
    def _notes_path(self) -> Path:
        return RESULTS_DIR / "run_notes.json"

    def _load_notes(self) -> dict:
        p = self._notes_path()
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                return d if isinstance(d, dict) else {}
            except Exception:  # noqa: BLE001
                return {}
        return {}

    def _save_notes(self, notes: dict) -> None:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        self._notes_path().write_text(
            json.dumps(notes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    def list_notes(self, run_id: str) -> list[dict]:
        """Notes d'un run, triées par horodatage croissant."""
        return sorted(self._load_notes().get(run_id, []), key=lambda n: n.get("ts", ""))

    def add_note(self, run_id: str, text: str) -> dict | None:
        """Ajoute une note horodatée ; renvoie None si le texte est vide."""
        clean = text.strip()
        if not clean:
            return None
        notes = self._load_notes()
        note = {"id": uuid4().hex[:8], "text": clean, "ts": datetime.now(timezone.utc).isoformat()}
        notes.setdefault(run_id, []).append(note)
        self._save_notes(notes)
        return note

    def delete_note(self, run_id: str, note_id: str) -> bool:
        """Retire une note ; renvoie True si une note a été retirée."""
        notes = self._load_notes()
        items = notes.get(run_id, [])
        kept = [n for n in items if n.get("id") != note_id]
        if len(kept) == len(items):
            return False
        notes[run_id] = kept
        self._save_notes(notes)
        return True

    def all_notes(self) -> list[dict]:
        """Flux agrégé de toutes les notes, run_name résolu, trié par horodatage décroissant."""
        name_by_id = {r["_run_id"]: r["name"] for r in self._scan()}
        out: list[dict] = []
        for run_id, items in self._load_notes().items():
            for n in items:
                out.append(
                    {
                        "run_id": run_id,
                        "run_name": name_by_id.get(run_id, run_id),
                        "id": n.get("id", ""),
                        "text": n.get("text", ""),
                        "ts": n.get("ts", ""),
                    }
                )
        return sorted(out, key=lambda n: n["ts"], reverse=True)
```

- [ ] **Step 5: Ajouter les routes**

Dans `backend/app/routes/runs.py`, ajouter `NoteCreate, NoteFeedItem, RunNote` à l'import depuis `..schemas`, puis ajouter ces routes **avant** la route `@router.get("/runs/{run_id}")` (la route détail générique, en fin de fichier) :

```python
@router.get("/runs/{run_id}/notes", response_model=list[RunNote])
def list_notes(run_id: str) -> list[dict]:
    """Notes du carnet pour un run (triées par horodatage croissant)."""
    return runs_service.list_notes(run_id)


@router.post("/runs/{run_id}/notes", response_model=RunNote)
def add_note(run_id: str, body: NoteCreate) -> dict:
    """Ajoute une note horodatée au run."""
    note = runs_service.add_note(run_id, body.text)
    if note is None:
        raise HTTPException(status_code=400, detail="Le texte de la note ne peut pas être vide.")
    return note


@router.delete("/runs/{run_id}/notes/{note_id}")
def delete_note(run_id: str, note_id: str) -> dict:
    """Supprime une note du run."""
    if not runs_service.delete_note(run_id, note_id):
        raise HTTPException(status_code=404, detail="Note introuvable.")
    return {"deleted": True}


@router.get("/notes", response_model=list[NoteFeedItem])
def all_notes() -> list[dict]:
    """Flux agrégé de toutes les notes (carnet de labo), trié par horodatage décroissant."""
    return runs_service.all_notes()
```

- [ ] **Step 6: Lancer le test pour vérifier le succès**

Run : `cd "<worktree>" && PYTHONPATH=. python -m pytest tests/test_backend.py::test_run_notes_roundtrip_and_feed -v`
Expected: PASS.

- [ ] **Step 7: Régénérer le schéma OpenAPI + types TS (drift gate)**

Run :
```bash
cd "<worktree>" && PYTHONPATH=. python tools/dump_openapi.py && cd frontend && npm run gen:api
```
Expected: `frontend/openapi.json` et `frontend/src/api/schema.ts` contiennent les opérations notes (`list_notes_…`, `add_note_…`, `delete_note_…`, `all_notes_…`). `git diff --stat` non vide sur ces 2 fichiers.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas.py backend/app/services/runs_service.py backend/app/routes/runs.py tests/test_backend.py frontend/openapi.json frontend/src/api/schema.ts
git commit -m "$(cat <<'EOF'
feat(runs): store run_notes + endpoints carnet (GET/POST/DELETE notes + flux /api/notes)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Notes d'exécution

- **Tâches 1→4** sur `feat/frontend-lab-notebook`, dans l'ordre (T2 dépend des types T1 ; T3 de RunNotes T2 ; T4 des types/queryKeys T1). PR vers `main`.
- **Tâche 5** indépendante, worktree depuis `origin/feat/d1-prod-pairing`, PR dans leur branche. Jusqu'à propagation d→main, l'onglet Carnet et le panneau de notes dégradent proprement (Empty/erreur douce, POST échoue → toast).
- Avant de finir la branche frontend : vérifier qu'aucun fichier backend/test.setup parasite (LF/CRLF) n'entre dans les commits.
