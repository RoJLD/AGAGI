# Fil conducteur EDR (I2) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un onglet « Fil EDR » : l'index recherchable/filtrable des 106 EDR (titre = verdict, couverture, runs liés en deep-link).

**Architecture:** Helper pur `lib/edrIndex.ts` (croise docs EDR × curés × liens runs) → vue `EdrIndexView` (3 useQuery, bandeau stats, recherche/filtres, table avec deep-link `→ run`). 100% endpoints existants, zéro backend.

**Tech Stack:** React 18 + TypeScript strict + @tanstack/react-query v5 + Vitest + Testing Library.

## Global Constraints

- **Frontend uniquement** : `frontend/src/**` + `docs/**`. Branche `feat/frontend-edr-index` → PR vers `main`. Données déjà sur main (`/api/edr`, `/api/edr/docs`, `/api/runs/edr-links`), **aucune dépendance backend / session parallèle**.
- **Langue** : libellés/commentaires en français.
- **Pas d'emoji** dans le code ni les commits.
- **TypeScript** : zéro `any`, types explicites.
- **Commits** : chaque commit se termine par le trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Pas d'enum de verdict** : le titre EDR (prose) fait foi.
- **Deep-link run** : `navigate("runs", { run: run_id })` (réutilise le `?run=` de RunsHistoryView).
- **Réutiliser** les classes CSS existantes `.runs-table` et `.checkbox-inline` (pas de nouveau CSS).
- **Tests** depuis `frontend/` : `npx vitest run <chemin>`. Un seul appel bash composé (`cd frontend && npx ...`).

---

### Task 1: `lib/edrIndex.ts` + type `EdrDoc` + `queryKeys.edrDocs`

**Files:**
- Modify: `frontend/src/types.ts` (ajout `EdrDoc`)
- Modify: `frontend/src/api/queryKeys.ts` (ajout `edrDocs`)
- Create: `frontend/src/lib/edrIndex.ts`
- Test: `frontend/src/lib/edrIndex.test.ts`

**Interfaces:**
- Produces:
  - `interface EdrDoc { edr: number; title: string; file: string }` (dans `types.ts`)
  - `queryKeys.edrDocs => ["edr","docs"]`
  - `interface EdrIndexRow { edr: number; title: string; mapped: boolean; runIds: string[]; runCount: number }`
  - `function buildEdrIndex(docs: { edr: number; title: string }[], curatedEdrs: number[], edrLinks: EdrLinks): EdrIndexRow[]`
  - `interface IndexSummary { total: number; mapped: number; withRuns: number }` ; `function summarizeIndex(rows: EdrIndexRow[]): IndexSummary`
  - `interface IndexFilter { query: string; mappedOnly: boolean; withRunsOnly: boolean }` ; `function filterIndex(rows: EdrIndexRow[], f: IndexFilter): EdrIndexRow[]`

- [ ] **Step 1: Ajouter le type `EdrDoc`**

Dans `frontend/src/types.ts`, après le type `EdrLinks` (vers la ligne 169) :

```ts
/** Un EDR documenté (docs/EDR/NNN_*.md), exposé par /api/edr/docs. */
export interface EdrDoc {
  edr: number;
  title: string;
  file: string;
}
```

- [ ] **Step 2: Ajouter la clé de query `edrDocs`**

Dans `frontend/src/api/queryKeys.ts`, juste après la ligne `edr: ["edr"] as const,` :

```ts
  edrDocs: ["edr", "docs"] as const,
```

- [ ] **Step 3: Écrire les tests qui échouent**

Créer `frontend/src/lib/edrIndex.test.ts` :

```ts
import { test, expect } from "vitest";
import { buildEdrIndex, summarizeIndex, filterIndex } from "./edrIndex";

const DOCS = [
  { edr: 101, title: "Metabolisme rescale" },
  { edr: 102, title: "Monoculture porte l'apex" },
  { edr: 99, title: "Decomposition du drain" },
];
const CURATED = [102, 99];
const LINKS = { "102": ["lewis_7", "lewis_8"], "99": [] };

test("buildEdrIndex : mapped, runIds, tri EDR décroissant", () => {
  const rows = buildEdrIndex(DOCS, CURATED, LINKS);
  expect(rows.map((r) => r.edr)).toEqual([102, 101, 99]);
  const r102 = rows.find((r) => r.edr === 102)!;
  expect(r102.mapped).toBe(true);
  expect(r102.runIds).toEqual(["lewis_7", "lewis_8"]);
  expect(r102.runCount).toBe(2);
  const r101 = rows.find((r) => r.edr === 101)!;
  expect(r101.mapped).toBe(false);
  expect(r101.runCount).toBe(0);
});

test("summarizeIndex : total / mapped / withRuns", () => {
  const rows = buildEdrIndex(DOCS, CURATED, LINKS);
  expect(summarizeIndex(rows)).toEqual({ total: 3, mapped: 2, withRuns: 1 });
});

test("filterIndex : recherche titre + numéro", () => {
  const rows = buildEdrIndex(DOCS, CURATED, LINKS);
  expect(filterIndex(rows, { query: "monoculture", mappedOnly: false, withRunsOnly: false }).map((r) => r.edr)).toEqual([102]);
  expect(filterIndex(rows, { query: "101", mappedOnly: false, withRunsOnly: false }).map((r) => r.edr)).toEqual([101]);
});

test("filterIndex : mappedOnly et withRunsOnly", () => {
  const rows = buildEdrIndex(DOCS, CURATED, LINKS);
  expect(filterIndex(rows, { query: "", mappedOnly: true, withRunsOnly: false }).map((r) => r.edr)).toEqual([102, 99]);
  expect(filterIndex(rows, { query: "", mappedOnly: false, withRunsOnly: true }).map((r) => r.edr)).toEqual([102]);
});
```

- [ ] **Step 4: Lancer les tests pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/lib/edrIndex.test.ts`
Expected: FAIL (`edrIndex.ts` introuvable).

- [ ] **Step 5: Implémenter `lib/edrIndex.ts`**

Créer `frontend/src/lib/edrIndex.ts` :

```ts
import type { EdrLinks } from "../types";

export interface EdrIndexRow {
  edr: number;
  title: string;
  mapped: boolean;
  runIds: string[];
  runCount: number;
}

/** Croise les docs EDR avec les EDR curés (mappés) et les liens runs. Tri EDR décroissant. */
export function buildEdrIndex(
  docs: { edr: number; title: string }[],
  curatedEdrs: number[],
  edrLinks: EdrLinks,
): EdrIndexRow[] {
  const curated = new Set(curatedEdrs);
  return docs
    .map((d) => {
      const runIds = edrLinks[String(d.edr)] ?? [];
      return { edr: d.edr, title: d.title, mapped: curated.has(d.edr), runIds, runCount: runIds.length };
    })
    .sort((a, b) => b.edr - a.edr);
}

export interface IndexSummary {
  total: number;
  mapped: number;
  withRuns: number;
}

/** Couverture globale : total / mappés / avec ≥1 run. */
export function summarizeIndex(rows: EdrIndexRow[]): IndexSummary {
  return {
    total: rows.length,
    mapped: rows.filter((r) => r.mapped).length,
    withRuns: rows.filter((r) => r.runCount > 0).length,
  };
}

export interface IndexFilter {
  query: string;
  mappedOnly: boolean;
  withRunsOnly: boolean;
}

/** Filtre : recherche `<edr> <titre>` (insensible casse) + mappés-only + avec-runs-only. */
export function filterIndex(rows: EdrIndexRow[], f: IndexFilter): EdrIndexRow[] {
  const q = f.query.trim().toLowerCase();
  return rows.filter((r) => {
    if (f.mappedOnly && !r.mapped) return false;
    if (f.withRunsOnly && r.runCount === 0) return false;
    if (q && !`${r.edr} ${r.title}`.toLowerCase().includes(q)) return false;
    return true;
  });
}
```

- [ ] **Step 6: Lancer les tests pour vérifier le succès**

Run : `cd frontend && npx vitest run src/lib/edrIndex.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/queryKeys.ts frontend/src/lib/edrIndex.ts frontend/src/lib/edrIndex.test.ts
git commit -m "$(cat <<'EOF'
feat(fil-edr): lib/edrIndex (build/summarize/filter) + type EdrDoc + queryKeys.edrDocs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `EdrIndexView` — 3 queries, stats, recherche/filtres, table

**Files:**
- Create: `frontend/src/components/EdrIndexView.tsx`
- Test: `frontend/src/components/EdrIndexView.test.tsx`

**Interfaces:**
- Consumes: `buildEdrIndex`/`summarizeIndex`/`filterIndex` de `../lib/edrIndex` ; `EdrDoc`/`EdrLinks` de `../types` ; `apiFetch` ; `queryKeys` (`edr`, `edrDocs`, `runs.edrLinks`) ; `useHashRoute` + `TAB_KEYS` ; UI `Loading`/`ErrorState`/`Empty`/`Field`/`Panel`/`Badge`/`Button`.
- Produces: `function EdrIndexView(): JSX.Element` (export nommé).

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `frontend/src/components/EdrIndexView.test.tsx` :

```tsx
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

const navigate = vi.fn();
vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
vi.mock("../hooks/useHashRoute", () => ({
  useHashRoute: () => ({ tab: "synthese", gate: "", query: {}, setTab: vi.fn(), setGate: vi.fn(), navigate }),
}));
import { apiFetch } from "../api/client";
import { EdrIndexView } from "./EdrIndexView";

afterEach(() => cleanup());

const DOCS = [
  { edr: 102, title: "Monoculture porte l'apex", file: "102_x.md" },
  { edr: 101, title: "Metabolisme rescale", file: "101_y.md" },
];
const CURATED = { findings: [{ edr: 102 }, { edr: 50, stub: true }] };
const LINKS = { "102": ["lewis_7"] };

function mockApi(docs: unknown, curated: unknown, links: unknown) {
  (apiFetch as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
    if (path.endsWith("/api/edr/docs")) return Promise.resolve(docs);
    if (path.endsWith("/api/runs/edr-links")) return Promise.resolve(links);
    if (path.endsWith("/api/edr")) return Promise.resolve(curated);
    return Promise.resolve([]);
  });
}

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  navigate.mockReset();
  mockApi(DOCS, CURATED, LINKS);
});

test("affiche le bandeau stats et la table", async () => {
  renderWithClient(<EdrIndexView />);
  expect(await screen.findByText(/2 EDR/)).toBeTruthy();
  expect(screen.getByText("Monoculture porte l'apex")).toBeTruthy();
  expect(screen.getByText("Metabolisme rescale")).toBeTruthy();
});

test("la recherche filtre les lignes", async () => {
  renderWithClient(<EdrIndexView />);
  await screen.findByText("Monoculture porte l'apex");
  fireEvent.change(screen.getByLabelText(/Rechercher/), { target: { value: "metabolisme" } });
  expect(screen.queryByText("Monoculture porte l'apex")).toBeNull();
  expect(screen.getByText("Metabolisme rescale")).toBeTruthy();
});

test("clic sur un run deep-linke vers son détail", async () => {
  renderWithClient(<EdrIndexView />);
  await screen.findByText("Monoculture porte l'apex");
  fireEvent.click(screen.getByText(/→ lewis_7/));
  expect(navigate).toHaveBeenCalledWith("runs", { run: "lewis_7" });
});

test("état vide quand aucun EDR documenté", async () => {
  mockApi([], { findings: [] }, {});
  renderWithClient(<EdrIndexView />);
  expect(await screen.findByText(/Aucun EDR documenté/)).toBeTruthy();
});
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/components/EdrIndexView.test.tsx`
Expected: FAIL (`EdrIndexView` introuvable).

- [ ] **Step 3: Implémenter `EdrIndexView.tsx`**

Créer `frontend/src/components/EdrIndexView.tsx` :

```tsx
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { EdrDoc, EdrLinks } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { useHashRoute } from "../hooks/useHashRoute";
import { TAB_KEYS } from "../tabs";
import { buildEdrIndex, summarizeIndex, filterIndex } from "../lib/edrIndex";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";
import { Field } from "./ui/Field";
import { Panel } from "./ui/Panel";
import { Badge } from "./ui/Badge";
import { Button } from "./ui/Button";

/** Forme minimale du payload /api/edr (on n'a besoin que de edr + stub pour la couverture). */
interface CuratedPayload {
  findings: { edr: number; stub?: boolean }[];
}

/** Fil conducteur EDR : index recherchable des 106 EDR (titre = verdict, couverture, runs liés). */
export function EdrIndexView() {
  const { navigate } = useHashRoute(TAB_KEYS, "synthese");

  const curatedQuery = useQuery({
    queryKey: queryKeys.edr,
    queryFn: () => apiFetch<CuratedPayload>("/api/edr"),
    staleTime: 30_000,
  });
  const docsQuery = useQuery({
    queryKey: queryKeys.edrDocs,
    queryFn: () => apiFetch<EdrDoc[]>("/api/edr/docs"),
    staleTime: 30_000,
  });
  const linksQuery = useQuery({
    queryKey: queryKeys.runs.edrLinks,
    queryFn: () => apiFetch<EdrLinks>("/api/runs/edr-links"),
    staleTime: 30_000,
  });

  const [query, setQuery] = useState("");
  const [mappedOnly, setMappedOnly] = useState(false);
  const [withRunsOnly, setWithRunsOnly] = useState(false);

  const docs = docsQuery.data ?? [];
  const rows = useMemo(
    () =>
      buildEdrIndex(
        docs,
        (curatedQuery.data?.findings ?? []).filter((f) => !f.stub).map((f) => f.edr),
        linksQuery.data ?? {},
      ),
    [docs, curatedQuery.data, linksQuery.data],
  );
  const summary = useMemo(() => summarizeIndex(rows), [rows]);
  const filtered = useMemo(
    () => filterIndex(rows, { query, mappedOnly, withRunsOnly }),
    [rows, query, mappedOnly, withRunsOnly],
  );

  if (docsQuery.isLoading || curatedQuery.isLoading || linksQuery.isLoading) {
    return <Loading label="Chargement du fil EDR…" />;
  }
  const error = docsQuery.error ?? curatedQuery.error ?? linksQuery.error;
  if (error) {
    return (
      <ErrorState
        error={error}
        onRetry={() => {
          docsQuery.refetch();
          curatedQuery.refetch();
          linksQuery.refetch();
        }}
      />
    );
  }
  if (!rows.length) return <Empty message="Aucun EDR documenté." />;

  return (
    <div className="edr-index-view">
      <h2>Fil conducteur EDR</h2>
      <p className="text-dim">
        {summary.total} EDR · {summary.mapped} mappés · {summary.withRuns} avec runs liés. Le titre porte le
        verdict ; clique un run pour ouvrir son détail.
      </p>
      <div className="row mb-4">
        <Field label="Rechercher">
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="ex: monoculture, 101" />
        </Field>
        <label className="checkbox-inline">
          <input type="checkbox" checked={mappedOnly} onChange={(e) => setMappedOnly(e.target.checked)} /> mappés
        </label>
        <label className="checkbox-inline">
          <input type="checkbox" checked={withRunsOnly} onChange={(e) => setWithRunsOnly(e.target.checked)} /> avec runs
        </label>
      </div>
      <Panel>
        <table className="runs-table">
          <thead>
            <tr>
              <th>EDR</th>
              <th>Titre</th>
              <th>Mappé</th>
              <th>Runs liés</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <tr key={r.edr}>
                <td>
                  <Badge variant="teal">EDR {r.edr}</Badge>
                </td>
                <td>{r.title}</td>
                <td>{r.mapped ? <Badge variant="success">mappé</Badge> : <span className="text-dim">—</span>}</td>
                <td>
                  {r.runIds.length ? (
                    r.runIds.map((id) => (
                      <Button key={id} variant="ghost" size="sm" onClick={() => navigate("runs", { run: id })}>
                        → {id}
                      </Button>
                    ))
                  ) : (
                    <span className="text-dim">—</span>
                  )}
                </td>
              </tr>
            ))}
            {!filtered.length && (
              <tr>
                <td colSpan={4} className="text-dim">
                  Aucun EDR ne correspond aux filtres.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Panel>
    </div>
  );
}
```

- [ ] **Step 4: Lancer les tests pour vérifier le succès**

Run : `cd frontend && npx vitest run src/components/EdrIndexView.test.tsx`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/EdrIndexView.tsx frontend/src/components/EdrIndexView.test.tsx
git commit -m "$(cat <<'EOF'
feat(fil-edr): vue EdrIndexView (stats, recherche/filtres, table, deep-link run)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Intégration onglet (tabs + App lazy)

**Files:**
- Modify: `frontend/src/tabs.ts`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `EdrIndexView` de `./components/EdrIndexView` ; `ListChecks` de `lucide-react`.
- Produces: onglet `"synthese"` navigable.

- [ ] **Step 1: Ajouter la clé `synthese` à `TAB_KEYS`**

Dans `frontend/src/tabs.ts`, dans `TAB_KEYS`, ajouter `"synthese"` juste après `"carnet"` :

```ts
  "carnet",
  "synthese",
```

- [ ] **Step 2: Importer l'icône et ajouter l'entrée famille Connaissance**

Dans `frontend/src/tabs.ts`, ajouter `ListChecks` à l'import lucide-react (ordre alpha, après `History`) :

```ts
  History,
  ListChecks,
  Network,
```

Puis, dans la famille **Connaissance** (après l'entrée `carnet`), ajouter :

```ts
      { key: "carnet", label: "Carnet", icon: NotebookPen },
      { key: "synthese", label: "Fil EDR", icon: ListChecks },
```

- [ ] **Step 3: Câbler le lazy import et la branche dans `App.tsx`**

Dans `frontend/src/App.tsx`, ajouter le lazy import après la ligne `CarnetView` (ou la dernière vue lazy) :

```ts
const EdrIndexView = lazy(() => import("./components/EdrIndexView").then((m) => ({ default: m.EdrIndexView })));
```

Puis ajouter la branche de rendu après `{tab === "carnet" && <CarnetView />}` :

```tsx
          {tab === "synthese" && <EdrIndexView />}
```

- [ ] **Step 4: Vérifier le typage et toute la suite**

Run : `cd frontend && npx tsc --noEmit`
Expected: aucune erreur.

Run : `cd frontend && npx vitest run`
Expected: PASS (toute la suite, incluant fil-edr).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/tabs.ts frontend/src/App.tsx
git commit -m "$(cat <<'EOF'
feat(fil-edr): integrer l'onglet Fil EDR (famille Connaissance) + lazy-load

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Notes d'exécution

- Tâches 1→3 dans l'ordre (T2 dépend des helpers + `EdrDoc` + `queryKeys.edrDocs` de T1 ; T3 de T2).
- 100% frontend, zéro dépendance backend (toutes les données sont sur `main`). PR vers `main` une fois la suite verte.
- Avant de finir : vérifier qu'aucun fichier backend/test.setup parasite (LF/CRLF) n'entre dans les commits.
