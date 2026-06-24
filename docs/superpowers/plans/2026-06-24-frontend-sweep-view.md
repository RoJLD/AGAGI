# Vue Sweep (paysage de paramètres) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un onglet « Sweeps » qui trace une métrique le long d'un paramètre balayé (`knob`), avec bande de variance, en lisant un nouvel endpoint `/api/sweeps`.

**Architecture:** Helper pur `buildSweepData` (testable) + composant recharts `SweepChart` (présentationnel) + `SweepView` (query/sélecteurs/états) câblé dans la nav. Le frontend est bâti contre une **fixture** conforme au contrat ; le **patch backend** (`runs_service.list_sweeps` + route) est livré comme document remis à la session parallèle, hors de cette branche.

**Tech Stack:** React 18, TypeScript (strict), Vite, @tanstack/react-query v5, recharts, lucide-react, Vitest + @testing-library/react.

## Global Constraints

- TypeScript `strict: true` — aucun `any`.
- Copie UI en **français**. Réutiliser primitives (`Loading`, `ErrorState`, `Empty`, `Field`, `Panel`) et tokens (`var(--…)` / `theme.ts`) — pas de couleur en dur.
- Contrat `/api/sweeps` (verbatim) :
  `SweepResult = { run_id: string; name: string; knob: string; x: number[]; series: Record<string, number[]>; y_std?: Record<string, number[]>; seed: number; commit?: string | null }`.
- v1 = **un sweep à la fois** (sélecteur) ; pas de superposition multi-sweep (YAGNI).
- Branche frontend = `frontend/src/**` + `docs/**` UNIQUEMENT. Le patch backend est un **document** (Task 5), pas du code committé en `backend/`.
- Tests restent hors tsconfig (inchangé). Chaque commit finit par `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Test : `npm --prefix frontend run test -- <fichier>`. Build : `npm --prefix frontend run build`.
- Branche : `feat/frontend-sweep-view` (déjà créée).

---

## File Structure

Créés :
- `frontend/src/lib/sweep.ts` — helper pur `buildSweepData`.
- `frontend/src/lib/sweep.test.ts`
- `frontend/src/components/SweepChart.tsx` — chart recharts.
- `frontend/src/components/SweepChart.test.tsx`
- `frontend/src/components/SweepView.tsx` — vue (query + sélecteurs + états).
- `frontend/src/components/SweepView.test.tsx`
- `docs/superpowers/patches/2026-06-24-sweeps-endpoint-backend-patch.md` — patch backend remis.

Modifiés :
- `frontend/src/types.ts` — interface `SweepResult`.
- `frontend/src/api/queryKeys.ts` — clé `sweeps`.
- `frontend/src/tabs.ts` — clé `"sweeps"` + entrée famille Analyse.
- `frontend/src/App.tsx` — lazy `SweepView` + branche `tab === "sweeps"`.

---

## Task 1: Helper pur `buildSweepData` + type `SweepResult`

**Files:**
- Create: `frontend/src/lib/sweep.ts`
- Test: `frontend/src/lib/sweep.test.ts`
- Modify: `frontend/src/types.ts`

**Interfaces:**
- Produces:
  - `interface SweepResult` (dans `types.ts`, voir Global Constraints).
  - `interface SweepPoint { x: number; y: number; band?: [number, number] }`
  - `buildSweepData(x: number[], y: number[], yStd?: number[]): SweepPoint[]` — `band = [y-std, y+std]` seulement si `yStd` fourni (et de même longueur).

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/lib/sweep.test.ts
import { test, expect } from "vitest";
import { buildSweepData } from "./sweep";

test("sans yStd : points x/y sans bande", () => {
  expect(buildSweepData([1, 2], [10, 20])).toEqual([
    { x: 1, y: 10 },
    { x: 2, y: 20 },
  ]);
});

test("avec yStd : bande [y-std, y+std]", () => {
  expect(buildSweepData([1, 2], [10, 20], [1, 2])).toEqual([
    { x: 1, y: 10, band: [9, 11] },
    { x: 2, y: 20, band: [18, 22] },
  ]);
});

test("yStd de longueur incohérente est ignoré (pas de bande)", () => {
  expect(buildSweepData([1, 2], [10, 20], [1])).toEqual([
    { x: 1, y: 10 },
    { x: 2, y: 20 },
  ]);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/lib/sweep.test.ts`
Expected: FAIL — `./sweep` n'existe pas.

- [ ] **Step 3: Write implementation**

```ts
// frontend/src/lib/sweep.ts
export interface SweepPoint {
  x: number;
  y: number;
  band?: [number, number];
}

/** Construit les points d'un sweep pour recharts : {x, y} + bande [y-std, y+std]
 *  si un écart-type de même longueur est fourni. Pur (aucun effet de bord). */
export function buildSweepData(x: number[], y: number[], yStd?: number[]): SweepPoint[] {
  const withBand = Array.isArray(yStd) && yStd.length === x.length;
  return x.map((xv, i) => {
    const point: SweepPoint = { x: xv, y: y[i] };
    if (withBand) point.band = [y[i] - yStd![i], y[i] + yStd![i]];
    return point;
  });
}
```

Ajouter l'interface dans `frontend/src/types.ts` (à la fin) :

```ts
/** Résultat d'un sweep : une métrique tracée le long d'un paramètre balayé (knob). */
export interface SweepResult {
  run_id: string;
  name: string;
  knob: string;
  x: number[];
  series: Record<string, number[]>;
  y_std?: Record<string, number[]>;
  seed: number;
  commit?: string | null;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/lib/sweep.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/sweep.ts frontend/src/lib/sweep.test.ts frontend/src/types.ts
git commit -m "feat(sweep): helper pur buildSweepData + type SweepResult

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `SweepChart` (recharts)

**Files:**
- Create: `frontend/src/components/SweepChart.tsx`
- Test: `frontend/src/components/SweepChart.test.tsx`

**Interfaces:**
- Consumes: `buildSweepData` (Task 1), `cssVar`/`vizColors` de `../theme`.
- Produces: `SweepChart({ x, knob, metric, y, yStd }: { x: number[]; knob: string; metric: string; y: number[]; yStd?: number[] })`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/SweepChart.test.tsx
import { render, cleanup } from "@testing-library/react";
import { afterEach, test, expect } from "vitest";
import { SweepChart } from "./SweepChart";

afterEach(() => cleanup());

test("monte un conteneur recharts avec une bande", () => {
  const { container } = render(
    <SweepChart x={[0.1, 0.2, 0.3]} knob="forage_payoff" metric="median_survival" y={[0.2, 0.5, 0.8]} yStd={[0.05, 0.05, 0.05]} />,
  );
  expect(container.querySelector(".recharts-responsive-container")).toBeTruthy();
});

test("monte sans bande quand yStd absent", () => {
  const { container } = render(
    <SweepChart x={[0.1, 0.2]} knob="k" metric="m" y={[1, 2]} />,
  );
  expect(container.querySelector(".recharts-responsive-container")).toBeTruthy();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/components/SweepChart.test.tsx`
Expected: FAIL — `./SweepChart` n'existe pas.

- [ ] **Step 3: Write implementation**

```tsx
// frontend/src/components/SweepChart.tsx
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from "recharts";
import { cssVar, vizColors } from "../theme";
import { buildSweepData } from "../lib/sweep";

interface SweepChartProps {
  x: number[];
  knob: string;
  metric: string;
  y: number[];
  yStd?: number[];
}

/** Paysage de paramètres : métrique Y le long du paramètre balayé (knob) en X,
 *  + bande de variance ±std si fournie. recharts, couleurs thème-aware. */
export function SweepChart({ x, knob, metric, y, yStd }: SweepChartProps) {
  const viz = vizColors();
  const data = buildSweepData(x, y, yStd);
  const hasBand = data.some((p) => p.band !== undefined);

  return (
    <ResponsiveContainer width="100%" height={360}>
      <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 28, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={cssVar("--color-border")} />
        <XAxis
          dataKey="x"
          type="number"
          domain={["auto", "auto"]}
          stroke={cssVar("--color-text-dim")}
          fontSize={11}
          label={{ value: knob, position: "insideBottom", offset: -14, fill: cssVar("--color-text-dim") }}
        />
        <YAxis
          stroke={cssVar("--color-text-dim")}
          fontSize={11}
          label={{ value: metric, angle: -90, position: "insideLeft", fill: cssVar("--color-text-dim") }}
        />
        <RechartsTooltip
          contentStyle={{ backgroundColor: cssVar("--color-surface"), border: `1px solid ${cssVar("--color-border")}` }}
        />
        {hasBand ? <Area dataKey="band" stroke="none" fill={viz[0]} fillOpacity={0.15} name="±écart-type" /> : null}
        <Line type="monotone" dataKey="y" stroke={viz[0]} strokeWidth={2.5} name={metric} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/components/SweepChart.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/SweepChart.tsx frontend/src/components/SweepChart.test.tsx
git commit -m "feat(sweep): SweepChart recharts (ligne + bande de variance, thème-aware)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: `SweepView` + `queryKeys.sweeps`

**Files:**
- Create: `frontend/src/components/SweepView.tsx`
- Test: `frontend/src/components/SweepView.test.tsx`
- Modify: `frontend/src/api/queryKeys.ts`

**Interfaces:**
- Consumes: `SweepResult` (Task 1), `SweepChart` (Task 2), `apiFetch`, `queryKeys.sweeps`, primitives `Loading`/`ErrorState`/`Empty`/`Field`/`Panel`.
- Produces: `SweepView()` (sans props, lazy-loadé par App).

- [ ] **Step 1: Ajouter la clé de query**

Modifier `frontend/src/api/queryKeys.ts` — ajouter après `health` (dans l'objet) :

```ts
  sweeps: ["sweeps"] as const,
```

- [ ] **Step 2: Write the failing test**

```tsx
// frontend/src/components/SweepView.test.tsx
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { SweepView } from "./SweepView";

afterEach(() => cleanup());

const FIXTURE = [
  {
    run_id: "lewis_survival_sweep_42",
    name: "lewis_survival_sweep",
    knob: "forage_payoff",
    x: [0.1, 0.2, 0.3],
    series: { median_survival: [0.2, 0.5, 0.8], median_competence: [0.1, 0.3, 0.6] },
    y_std: { median_survival: [0.05, 0.05, 0.05] },
    seed: 42,
    commit: "abc1234",
  },
];

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue(FIXTURE);
});

test("affiche le sweep, le knob et un sélecteur de métrique (2 séries)", async () => {
  renderWithClient(<SweepView />);
  expect(await screen.findByText(/forage_payoff/)).toBeTruthy();
  // 2 séries -> sélecteur métrique présent
  expect(screen.getByLabelText(/Métrique/)).toBeTruthy();
});

test("état vide quand aucun sweep", async () => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  renderWithClient(<SweepView />);
  expect(await screen.findByText(/Aucun sweep disponible/)).toBeTruthy();
});

test("changer de métrique met à jour l'en-tête", async () => {
  renderWithClient(<SweepView />);
  await screen.findByText(/forage_payoff/);
  fireEvent.change(screen.getByLabelText(/Métrique/), { target: { value: "median_competence" } });
  expect(screen.getByText(/median_competence/)).toBeTruthy();
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/components/SweepView.test.tsx`
Expected: FAIL — `./SweepView` n'existe pas.

- [ ] **Step 4: Write implementation**

```tsx
// frontend/src/components/SweepView.tsx
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { SweepResult } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";
import { Field } from "./ui/Field";
import { Panel } from "./ui/Panel";
import { SweepChart } from "./SweepChart";

export function SweepView() {
  const { data: sweeps = [], isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.sweeps,
    queryFn: () => apiFetch<SweepResult[]>("/api/sweeps"),
    staleTime: 30_000,
  });

  const [selId, setSelId] = useState<string>("");
  const [metric, setMetric] = useState<string>("");

  const current = sweeps.find((s) => s.run_id === selId) ?? sweeps[0];
  const metrics = current ? Object.keys(current.series) : [];

  useEffect(() => {
    if (current && !selId) setSelId(current.run_id);
  }, [current, selId]);
  useEffect(() => {
    if (metrics.length && !metrics.includes(metric)) setMetric(metrics[0]);
  }, [metrics, metric]);

  if (isLoading) return <Loading label="Chargement des sweeps…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!sweeps.length) {
    return (
      <Empty message="Aucun sweep disponible. Lance un balayage de paramètre (ex. lewis_survival_sweep) côté backend." />
    );
  }
  if (!current) return <Empty message="Aucun sweep sélectionné." />;

  return (
    <div className="sweep-view">
      <h2>Paysage de paramètres (sweeps)</h2>
      <div className="row mb-4">
        <Field label="Sweep">
          <select value={current.run_id} onChange={(e) => setSelId(e.target.value)}>
            {sweeps.map((s) => (
              <option key={s.run_id} value={s.run_id}>
                {s.name} — {s.knob}
              </option>
            ))}
          </select>
        </Field>
        {metrics.length > 1 && (
          <Field label="Métrique (Y)">
            <select value={metric} onChange={(e) => setMetric(e.target.value)}>
              {metrics.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </Field>
        )}
      </div>
      <p className="text-dim">
        {current.name} · paramètre <strong>{current.knob}</strong> · métrique <strong>{metric}</strong> ·{" "}
        {current.x.length} points
      </p>
      <Panel>
        <SweepChart
          x={current.x}
          knob={current.knob}
          metric={metric}
          y={current.series[metric] ?? []}
          yStd={current.y_std?.[metric]}
        />
      </Panel>
    </div>
  );
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/components/SweepView.test.tsx`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/SweepView.tsx frontend/src/components/SweepView.test.tsx frontend/src/api/queryKeys.ts
git commit -m "feat(sweep): SweepView (query /api/sweeps, sélecteurs sweep/métrique, états)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Intégration — onglet Sweeps + lazy

**Files:**
- Modify: `frontend/src/tabs.ts`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `SweepView` (Task 3).

- [ ] **Step 1: Ajouter la clé d'onglet (`tabs.ts`)**

Importer l'icône `Spline` depuis `lucide-react` (ajouter à l'import existant). Ajouter `"sweeps"` à `TAB_KEYS` (après `"topology"`, dans la famille Analyse — l'ordre du tableau suit les familles). Ajouter l'entrée dans la famille « Analyse » de `TAB_FAMILIES`, après `topology` :

```ts
      { key: "topology", label: "Topologie", icon: Network },
      { key: "sweeps", label: "Sweeps", icon: Spline },
```

Et dans `TAB_KEYS`, insérer `"sweeps"` juste après `"topology"`.

- [ ] **Step 2: Brancher `SweepView` dans `App.tsx`**

Ajouter le lazy import (après les autres `const … = lazy(...)`) :

```tsx
const SweepView = lazy(() => import("./components/SweepView").then((m) => ({ default: m.SweepView })));
```

Ajouter la branche de rendu (après `tab === "topology"`) :

```tsx
          {tab === "topology" && <TopologyView />}
          {tab === "sweeps" && <SweepView />}
```

(`sweeps` n'est PAS dans `showSidebar` → pleine largeur, pas de GateSidebar. Laisser `showSidebar` inchangé.)

- [ ] **Step 3: Vérifier build + suite complète**

Run: `npm --prefix frontend run build`
Expected: build OK (tsc + vite).

Run: `npm --prefix frontend run test`
Expected: tous les tests passent (dont `tabs.test.tsx` : `buildNavItems` inclut désormais `sweeps` — si une assertion d'ordre `toEqual(TAB_KEYS)` existe, elle reste vraie car `TAB_KEYS` et la famille sont mis à jour de façon cohérente).

- [ ] **Step 4: Vérification manuelle (dev)**

Run: `npm --prefix frontend run dev`
Vérifier : onglet « Sweeps » présent dans la famille Analyse ; sans backend `/api/sweeps`, l'onglet affiche l'état `Empty` (« Aucun sweep disponible… ») sans planter ; deep-links existants intacts.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/tabs.ts frontend/src/App.tsx
git commit -m "feat(sweep): intégrer l'onglet Sweeps (famille Analyse) + lazy-load

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Document de patch backend (remis à la session parallèle)

**Files:**
- Create: `docs/superpowers/patches/2026-06-24-sweeps-endpoint-backend-patch.md`

**Interfaces:**
- Produces: le patch `runs_service.list_sweeps()` + route `/api/sweeps` + modèle Pydantic `SweepResult` + test pytest, conformes au contrat du frontend. **Aucun fichier `backend/` n'est modifié sur cette branche** — c'est un document remis.

- [ ] **Step 1: Écrire le document de patch**

Créer `docs/superpowers/patches/2026-06-24-sweeps-endpoint-backend-patch.md` avec le contenu suivant :

````markdown
# Patch backend — endpoint `/api/sweeps` (à appliquer sur `feat/d1-prod-pairing`)

Expose les runs *sweep* (`Harness.save({knob, levels, <metric arrays>, …})`) au frontend. Lecture
seule, aucune dépendance moteur. Contrat aligné sur `frontend/src/types.ts::SweepResult`.

## 1) `backend/app/services/runs_service.py` — ajouter

```python
    @staticmethod
    def _is_num_list(v: object) -> bool:
        return isinstance(v, list) and len(v) > 0 and all(
            isinstance(x, (int, float)) and not isinstance(x, bool) for x in v
        )

    def list_sweeps(self) -> list[dict]:
        """Runs *sweep* : data.knob (str) + data.levels (liste num) = axe X ;
        chaque autre liste num de même longueur = série Y ; <metric>_std|_spread = y_std."""
        out: list[dict] = []
        for r in self._scan():
            data = r["data"]
            knob, levels = data.get("knob"), data.get("levels")
            if not isinstance(knob, str) or not self._is_num_list(levels):
                continue
            n = len(levels)
            series: dict[str, list[float]] = {}
            y_std: dict[str, list[float]] = {}
            for k, v in data.items():
                if k in ("knob", "levels") or not self._is_num_list(v) or len(v) != n:
                    continue
                if k.endswith("_std") or k.endswith("_spread"):
                    y_std[k.rsplit("_", 1)[0]] = [float(x) for x in v]
                else:
                    series[k] = [float(x) for x in v]
            if not series:
                continue
            out.append({
                "run_id": r["_run_id"], "name": r["name"], "knob": knob,
                "x": [float(x) for x in levels], "series": series,
                "y_std": y_std or None, "seed": r["seed"], "commit": r.get("commit"),
            })
        return out
```

## 2) `backend/app/routes/runs.py` — ajouter le modèle + la route

```python
from pydantic import BaseModel

class SweepResult(BaseModel):
    run_id: str
    name: str
    knob: str
    x: list[float]
    series: dict[str, list[float]]
    y_std: dict[str, list[float]] | None = None
    seed: int
    commit: str | None = None

@router.get("/sweeps", response_model=list[SweepResult])
def list_sweeps() -> list[dict]:
    return runs_service.list_sweeps()
```

## 3) `tests/test_backend.py` — ajouter

```python
def test_list_sweeps_extracts_knob_levels_series(tmp_path, monkeypatch) -> None:
    """Un run sweep (knob+levels+series) -> 1 SweepResult ; un run scalaire -> ignoré."""
    import backend.app.services.runs_service as rs_mod
    monkeypatch.setattr(rs_mod, "RESULTS_DIR", tmp_path)
    (tmp_path / "lewis_survival_sweep_42.json").write_text(json.dumps({
        "name": "lewis_survival_sweep", "seed": 42, "commit": "abc1234",
        "data": {"knob": "forage_payoff", "levels": [0.1, 0.2, 0.3],
                 "median_survival": [0.2, 0.5, 0.8], "median_survival_std": [0.05, 0.05, 0.05],
                 "R": 4, "n_eval": 8},
    }), encoding="utf-8")
    (tmp_path / "AND_0.json").write_text(json.dumps({
        "name": "AND", "seed": 0, "data": {"fitness": 0.9},
    }), encoding="utf-8")
    sweeps = rs_mod.runs_service.list_sweeps()
    assert len(sweeps) == 1
    s = sweeps[0]
    assert s["knob"] == "forage_payoff"
    assert s["x"] == [0.1, 0.2, 0.3]
    assert s["series"]["median_survival"] == [0.2, 0.5, 0.8]
    assert s["y_std"]["median_survival"] == [0.05, 0.05, 0.05]
```

## Vérif (sur leur branche)
```
PYTHONPATH=. python -m pytest tests/test_backend.py::test_list_sweeps_extracts_knob_levels_series -q
PYTHONPATH=. python tools/dump_openapi.py && npm --prefix frontend run gen:api   # rafraîchit schema.ts
```
Attendu : test PASS ; le codegen ajoute `SweepResult` à `schema.ts` (la gate de drift CI restera verte une fois committé).

## Note
Le frontend (vue Sweeps) est déjà livré et fonctionne en `Empty` tant que cette route n'existe pas ;
une fois mergée, l'onglet se peuple automatiquement (aucune coordination de timing requise).
````

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/patches/2026-06-24-sweeps-endpoint-backend-patch.md
git commit -m "docs(sweep): patch backend /api/sweeps à remettre à la session parallèle

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (effectuée)

- **Couverture du spec :** contrat `SweepResult` (Task 1) ; chart recharts + bande (Task 2) ; vue query/sélecteurs/états/Empty gracieux (Task 3) ; onglet Analyse + lazy (Task 4) ; patch backend remis avec règle `knob/levels` + pytest (Task 5). v1 mono-sweep respectée (sélecteur, pas de superposition).
- **Placeholders :** aucun — code complet à chaque step.
- **Cohérence des types :** `SweepResult`/`SweepPoint`/`buildSweepData(x,y,yStd?)`/`SweepChart({x,knob,metric,y,yStd})` cohérents Tasks 1→3 ; le patch backend (Task 5) émet exactement les champs de `SweepResult` (run_id, name, knob, x, series, y_std, seed, commit).
- **Frontière :** Tasks 1-4 = `frontend/src/**` ; Task 5 = `docs/**` (patch remis, zéro fichier `backend/` touché). Aucun conflit avec `feat/d1-prod-pairing`.
- **recharts/jsdom :** la logique testée est `buildSweepData` (pur) + le câblage `SweepView` (DOM hors canvas) ; `SweepChart` est un smoke-test de montage du conteneur — honnête vu les limites recharts en jsdom.
