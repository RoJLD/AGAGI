# Vue cohorte / distributions — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un onglet « Cohorte » affichant la distribution par seed (box plot + points bruts) de toutes les conditions portant une métrique choisie, triées par médiane décroissante.

**Architecture:** Helper pur `lib/cohort.ts` (stats Tukey) → composant SVG `CohortChart` → vue `CohortView` (2 useQuery + sélecteur de métrique) → intégration onglet lazy. Données par seed via un nouvel endpoint backend `GET /api/runs/distributions?metric=X` (réutilise `_values`), livré en patch-and-handoff dans `feat/d1-prod-pairing`.

**Tech Stack:** React 18 + TypeScript strict + @tanstack/react-query v5 + Vitest + Testing Library (frontend) ; FastAPI + Pydantic + pytest (backend).

## Global Constraints

- **Frontière session parallèle** : tâches 1-4 = frontend uniquement (`frontend/src/**` + `docs/**`) sur la branche `feat/frontend-cohort-view` → PR vers `main`. Tâche 5 = backend → branche séparée depuis `feat/d1-prod-pairing`, **PR dans leur branche** (ne jamais pousser dessus directement).
- **Langue** : tout libellé/commentaire en français.
- **Pas d'emoji** dans le code ni les commits.
- **TypeScript** : zéro `any` ; types explicites.
- **Commits** : chaque commit se termine par le trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Tri** : conditions triées par **médiane décroissante**.
- **Box plot Tukey** : moustaches à 1,5×IQR ; quantiles par interpolation linéaire type-7 ; **pas de violin**.
- **Jitter déterministe** : offset des points basé sur l'index du seed, **jamais `Math.random`**.
- **Tests frontend** depuis `frontend/` : `npx vitest run <chemin>`. **Tests backend** depuis la racine : `PYTHONPATH=. python -m pytest <chemin>::<test> -v`.

---

### Task 1: `lib/cohort.ts` — stats de box plot (pur)

**Files:**
- Create: `frontend/src/lib/cohort.ts`
- Test: `frontend/src/lib/cohort.test.ts`
- Modify: `frontend/src/types.ts` (ajout `DistributionSummary`)

**Interfaces:**
- Consumes: rien (premier module).
- Produces :
  - `interface DistributionSummary { name: string; vals: number[]; n: number }` (dans `types.ts`)
  - `interface BoxStats { min; q1; median; q3; max; iqr; lowerWhisker; upperWhisker; outliers: number[]; n: number }` (tous `number` sauf `outliers: number[]`)
  - `interface CohortRow { name: string; vals: number[]; stats: BoxStats }`
  - `function quantile(sorted: number[], p: number): number`
  - `function computeBoxStats(vals: number[]): BoxStats`
  - `function buildCohort(dists: DistributionSummary[]): CohortRow[]`

- [ ] **Step 1: Ajouter le type `DistributionSummary` dans `types.ts`**

Ajouter après l'interface `ConditionSummary` (vers la ligne 83) :

```ts
export interface DistributionSummary {
  name: string;
  vals: number[];
  n: number;
}
```

- [ ] **Step 2: Écrire les tests qui échouent**

Créer `frontend/src/lib/cohort.test.ts` :

```ts
import { test, expect } from "vitest";
import { quantile, computeBoxStats, buildCohort } from "./cohort";

test("quantile : interpolation linéaire type-7", () => {
  const s = [1, 2, 3, 4];
  expect(quantile(s, 0.25)).toBeCloseTo(1.75, 10);
  expect(quantile(s, 0.5)).toBeCloseTo(2.5, 10);
  expect(quantile(s, 0.75)).toBeCloseTo(3.25, 10);
});

test("computeBoxStats : quartiles, IQR, médiane", () => {
  const s = computeBoxStats([1, 2, 3, 4]);
  expect(s.q1).toBeCloseTo(1.75, 10);
  expect(s.median).toBeCloseTo(2.5, 10);
  expect(s.q3).toBeCloseTo(3.25, 10);
  expect(s.iqr).toBeCloseTo(1.5, 10);
  expect(s.n).toBe(4);
  expect(s.outliers).toEqual([]);
});

test("computeBoxStats : détecte un outlier hors 1,5×IQR", () => {
  const s = computeBoxStats([1, 2, 3, 4, 100]);
  // q1=2, q3=4, iqr=2, hiFence=7 -> 100 est outlier, moustache haute = 4
  expect(s.q1).toBeCloseTo(2, 10);
  expect(s.q3).toBeCloseTo(4, 10);
  expect(s.upperWhisker).toBe(4);
  expect(s.outliers).toEqual([100]);
});

test("computeBoxStats : cas dégénéré n=1", () => {
  const s = computeBoxStats([5]);
  expect(s.q1).toBe(5);
  expect(s.median).toBe(5);
  expect(s.q3).toBe(5);
  expect(s.iqr).toBe(0);
  expect(s.lowerWhisker).toBe(5);
  expect(s.upperWhisker).toBe(5);
  expect(s.outliers).toEqual([]);
  expect(s.n).toBe(1);
});

test("buildCohort : tri par médiane décroissante, vides exclus", () => {
  const rows = buildCohort([
    { name: "basse", vals: [1, 1, 1], n: 3 },
    { name: "vide", vals: [], n: 0 },
    { name: "haute", vals: [10, 10, 10], n: 3 },
  ]);
  expect(rows.map((r) => r.name)).toEqual(["haute", "basse"]);
});
```

- [ ] **Step 3: Lancer les tests pour vérifier l'échec**

Run (depuis `frontend/`) : `npx vitest run src/lib/cohort.test.ts`
Expected: FAIL (`cohort.ts` introuvable / fonctions non définies).

- [ ] **Step 4: Implémenter `lib/cohort.ts`**

Créer `frontend/src/lib/cohort.ts` :

```ts
import type { DistributionSummary } from "../types";

export interface BoxStats {
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
  iqr: number;
  lowerWhisker: number; // plus petite valeur >= q1 - 1,5*iqr
  upperWhisker: number; // plus grande valeur <= q3 + 1,5*iqr
  outliers: number[];   // valeurs hors [lowerWhisker, upperWhisker]
  n: number;
}

export interface CohortRow {
  name: string;
  vals: number[];
  stats: BoxStats;
}

/** Quantile par interpolation linéaire (type-7, comme d3.quantile / numpy par défaut).
 *  `sorted` doit être trié ascendant et non vide ; p dans [0,1]. */
export function quantile(sorted: number[], p: number): number {
  if (sorted.length === 1) return sorted[0];
  const idx = (sorted.length - 1) * p;
  const lo = Math.floor(idx);
  const hi = Math.ceil(idx);
  if (lo === hi) return sorted[lo];
  const frac = idx - lo;
  return sorted[lo] * (1 - frac) + sorted[hi] * frac;
}

/** Stats de box plot (Tukey). Précondition : vals non vide. */
export function computeBoxStats(vals: number[]): BoxStats {
  const sorted = [...vals].sort((a, b) => a - b);
  const n = sorted.length;
  const q1 = quantile(sorted, 0.25);
  const median = quantile(sorted, 0.5);
  const q3 = quantile(sorted, 0.75);
  const iqr = q3 - q1;
  const loFence = q1 - 1.5 * iqr;
  const hiFence = q3 + 1.5 * iqr;
  const inFence = sorted.filter((v) => v >= loFence && v <= hiFence);
  const lowerWhisker = inFence.length ? inFence[0] : sorted[0];
  const upperWhisker = inFence.length ? inFence[inFence.length - 1] : sorted[n - 1];
  const outliers = sorted.filter((v) => v < lowerWhisker || v > upperWhisker);
  return { min: sorted[0], q1, median, q3, max: sorted[n - 1], iqr, lowerWhisker, upperWhisker, outliers, n };
}

/** Lignes de cohorte triées par médiane décroissante ; conditions à vals vide exclues. */
export function buildCohort(dists: DistributionSummary[]): CohortRow[] {
  return dists
    .filter((d) => d.vals.length > 0)
    .map((d) => ({ name: d.name, vals: d.vals, stats: computeBoxStats(d.vals) }))
    .sort((a, b) => b.stats.median - a.stats.median);
}
```

- [ ] **Step 5: Lancer les tests pour vérifier le succès**

Run : `npx vitest run src/lib/cohort.test.ts`
Expected: PASS (5 tests).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/cohort.ts frontend/src/lib/cohort.test.ts frontend/src/types.ts
git commit -m "$(cat <<'EOF'
feat(cohort): stats de box plot Tukey (lib/cohort) + type DistributionSummary

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `CohortChart` — box plot SVG horizontal + strip

**Files:**
- Create: `frontend/src/components/CohortChart.tsx`
- Test: `frontend/src/components/CohortChart.test.tsx`

**Interfaces:**
- Consumes: `CohortRow` de `../lib/cohort` ; `cssVar`, `vizColors` de `../theme`.
- Produces: `function CohortChart(props: { rows: CohortRow[]; metric: string }): JSX.Element`. Chaque condition = un `<g data-testid="cohort-row">`.

- [ ] **Step 1: Écrire le test smoke qui échoue**

Créer `frontend/src/components/CohortChart.test.tsx` :

```tsx
import { render, cleanup } from "@testing-library/react";
import { afterEach, test, expect } from "vitest";
import { CohortChart } from "./CohortChart";
import type { CohortRow } from "../lib/cohort";
import { computeBoxStats } from "../lib/cohort";

afterEach(() => cleanup());

const ROWS: CohortRow[] = [
  { name: "haute", vals: [9, 10, 11], stats: computeBoxStats([9, 10, 11]) },
  { name: "basse", vals: [1, 2, 3], stats: computeBoxStats([1, 2, 3]) },
];

test("monte un <svg> avec une ligne par condition", () => {
  const { container } = render(<CohortChart rows={ROWS} metric="fitness" />);
  const svg = container.querySelector("svg");
  expect(svg).toBeTruthy();
  expect(svg?.getAttribute("aria-label")).toContain("fitness");
  expect(container.querySelectorAll('[data-testid="cohort-row"]').length).toBe(2);
});

test("trace un cercle par seed", () => {
  const { container } = render(<CohortChart rows={ROWS} metric="fitness" />);
  // 3 + 3 seeds -> 6 cercles
  expect(container.querySelectorAll("circle").length).toBe(6);
});
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run : `npx vitest run src/components/CohortChart.test.tsx`
Expected: FAIL (`CohortChart` introuvable).

- [ ] **Step 3: Implémenter `CohortChart.tsx`**

Créer `frontend/src/components/CohortChart.tsx` :

```tsx
import { cssVar, vizColors } from "../theme";
import type { CohortRow } from "../lib/cohort";

interface CohortChartProps {
  rows: CohortRow[];
  metric: string;
}

const ROW_H = 46;
const LABEL_W = 160;
const PAD_R = 56;
const PAD_TOP = 16;
const VIEW_W = 840;
const BOX_H = 18;
const JITTER = 14;

/** Box plot horizontal (une ligne par condition) + points par seed jitterés.
 *  SVG auto-rendu, échelle X linéaire partagée. Pas de recharts box natif. */
export function CohortChart({ rows, metric }: CohortChartProps) {
  const viz = vizColors();
  const boxColor = viz[0];
  const accent = viz[2];
  const height = PAD_TOP * 2 + rows.length * ROW_H;

  const all = rows.flatMap((r) => r.vals);
  const lo = all.length ? Math.min(...all) : 0;
  const hi = all.length ? Math.max(...all) : 1;
  const span = hi - lo || 1;
  const x0 = LABEL_W;
  const x1 = VIEW_W - PAD_R;
  const scaleX = (v: number) => x0 + ((v - lo) / span) * (x1 - x0);

  return (
    <svg
      className="cohort-chart"
      width="100%"
      viewBox={`0 0 ${VIEW_W} ${height}`}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label={`Distributions par condition pour la métrique ${metric}`}
    >
      {rows.map((row, ri) => {
        const cy = PAD_TOP + ri * ROW_H + ROW_H / 2;
        const s = row.stats;
        const c = row.vals.length;
        return (
          <g key={row.name} data-testid="cohort-row">
            <title>{`${row.name} — médiane ${s.median.toFixed(3)}, IQR ${s.iqr.toFixed(3)}, n=${s.n}`}</title>
            <text x={LABEL_W - 10} y={cy} textAnchor="end" dominantBaseline="middle" fontSize={12} fill={cssVar("--color-text")}>
              {row.name}
            </text>
            <line x1={scaleX(s.lowerWhisker)} x2={scaleX(s.upperWhisker)} y1={cy} y2={cy} stroke={cssVar("--color-text-dim")} strokeWidth={1} />
            <rect x={scaleX(s.q1)} y={cy - BOX_H / 2} width={Math.max(1, scaleX(s.q3) - scaleX(s.q1))} height={BOX_H} fill={boxColor} fillOpacity={0.18} stroke={boxColor} strokeWidth={1.5} />
            <line x1={scaleX(s.median)} x2={scaleX(s.median)} y1={cy - BOX_H / 2} y2={cy + BOX_H / 2} stroke={boxColor} strokeWidth={2.5} />
            {row.vals.map((v, i) => {
              const offset = c > 1 ? (i / (c - 1) - 0.5) * JITTER : 0;
              const isOut = v < s.lowerWhisker || v > s.upperWhisker;
              return (
                <circle
                  key={i}
                  cx={scaleX(v)}
                  cy={cy + offset}
                  r={3}
                  fill={isOut ? accent : boxColor}
                  fillOpacity={isOut ? 0.95 : 0.6}
                  stroke={isOut ? accent : "none"}
                  strokeWidth={isOut ? 1 : 0}
                />
              );
            })}
            <text x={VIEW_W - PAD_R + 8} y={cy} dominantBaseline="middle" fontSize={11} fill={cssVar("--color-text-dim")}>
              n={s.n}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run : `npx vitest run src/components/CohortChart.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/CohortChart.tsx frontend/src/components/CohortChart.test.tsx
git commit -m "$(cat <<'EOF'
feat(cohort): composant CohortChart (box plot SVG horizontal + strip de seeds)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `CohortView` — sélecteur de métrique, états, câblage

**Files:**
- Create: `frontend/src/components/CohortView.tsx`
- Test: `frontend/src/components/CohortView.test.tsx`
- Modify: `frontend/src/api/queryKeys.ts` (ajout `runs.distributions`)

**Interfaces:**
- Consumes: `apiFetch` de `../api/client` ; `queryKeys` de `../api/queryKeys` ; `buildCohort` de `../lib/cohort` ; `CohortChart` ; `ConditionSummary`/`DistributionSummary` de `../types` ; UI `Loading`/`ErrorState`/`Empty`/`Field`/`Panel`.
- Produces: `function CohortView(): JSX.Element` (export nommé) ; `queryKeys.runs.distributions(metric: string)`.

- [ ] **Step 1: Ajouter la clé de query `distributions`**

Dans `frontend/src/api/queryKeys.ts`, à l'intérieur de l'objet `runs` (après la ligne `compare: ...`), ajouter :

```ts
    distributions: (metric: string) => ["runs", "distributions", metric] as const,
```

- [ ] **Step 2: Écrire les tests qui échouent**

Créer `frontend/src/components/CohortView.test.tsx` :

```tsx
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { CohortView } from "./CohortView";

afterEach(() => cleanup());

const CONDITIONS = [
  { name: "A", n_seeds: 3, seeds: [0, 1, 2], metrics: ["fitness", "survie"] },
  { name: "B", n_seeds: 3, seeds: [0, 1, 2], metrics: ["fitness"] },
];
const DISTS = [
  { name: "A", vals: [9, 10, 11], n: 3 },
  { name: "B", vals: [1, 2, 3], n: 3 },
];

function mockApi(conditions: unknown, dists: unknown) {
  (apiFetch as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
    if (path.endsWith("/api/runs/conditions")) return Promise.resolve(conditions);
    if (path.includes("/api/runs/distributions")) return Promise.resolve(dists);
    return Promise.resolve([]);
  });
}

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => mockApi(CONDITIONS, DISTS));

test("rend le sélecteur de métrique et le graphe", async () => {
  const { container } = renderWithClient(<CohortView />);
  expect(await screen.findByLabelText(/Métrique/)).toBeTruthy();
  expect(container.querySelector("svg.cohort-chart")).toBeTruthy();
  expect(container.querySelectorAll('[data-testid="cohort-row"]').length).toBe(2);
});

test("état vide quand aucune métrique numérique", async () => {
  mockApi([{ name: "A", n_seeds: 1, seeds: [0], metrics: [] }], []);
  renderWithClient(<CohortView />);
  expect(await screen.findByText(/Aucune métrique numérique/)).toBeTruthy();
});

test("changer de métrique met à jour l'en-tête", async () => {
  renderWithClient(<CohortView />);
  await screen.findByLabelText(/Métrique/);
  fireEvent.change(screen.getByLabelText(/Métrique/), { target: { value: "survie" } });
  expect(
    screen.getByText((_, el) => el?.tagName === "STRONG" && el.textContent === "survie"),
  ).toBeTruthy();
});
```

- [ ] **Step 3: Lancer les tests pour vérifier l'échec**

Run : `npx vitest run src/components/CohortView.test.tsx`
Expected: FAIL (`CohortView` introuvable).

- [ ] **Step 4: Implémenter `CohortView.tsx`**

Créer `frontend/src/components/CohortView.tsx` :

```tsx
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ConditionSummary, DistributionSummary } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { buildCohort } from "../lib/cohort";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";
import { Field } from "./ui/Field";
import { Panel } from "./ui/Panel";
import { CohortChart } from "./CohortChart";

/** Vue cohorte : distribution par seed (box+strip) de toutes les conditions
 *  portant la métrique choisie, triées par médiane décroissante. */
export function CohortView() {
  const { data: conditions = [], isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.runs.conditions,
    queryFn: () => apiFetch<ConditionSummary[]>("/api/runs/conditions"),
    staleTime: 30_000,
  });

  const metrics = useMemo(
    () => [...new Set(conditions.flatMap((c) => c.metrics))].sort(),
    [conditions],
  );

  const [metric, setMetric] = useState<string>("");
  useEffect(() => {
    if (metrics.length && !metrics.includes(metric)) setMetric(metrics[0]);
  }, [metrics, metric]);

  const { data: dists = [] } = useQuery({
    queryKey: queryKeys.runs.distributions(metric),
    queryFn: () => apiFetch<DistributionSummary[]>(`/api/runs/distributions?metric=${encodeURIComponent(metric)}`),
    enabled: !!metric,
    staleTime: 30_000,
  });

  const rows = useMemo(() => buildCohort(dists), [dists]);

  if (isLoading) return <Loading label="Chargement des conditions…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!metrics.length) {
    return <Empty message="Aucune métrique numérique disponible. Lance des expériences (runs) pour peupler les conditions." />;
  }

  return (
    <div className="cohort-view">
      <h2>Cohorte — distributions par condition</h2>
      <div className="row mb-4">
        <Field label="Métrique">
          <select value={metric} onChange={(e) => setMetric(e.target.value)}>
            {metrics.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <p className="text-dim">
        métrique <strong>{metric}</strong> · {rows.length} condition{rows.length > 1 ? "s" : ""} · triées par médiane décroissante
      </p>
      {rows.length === 0 ? (
        <Empty message={`Aucune valeur pour la métrique ${metric}.`} />
      ) : (
        <>
          <Panel>
            <CohortChart rows={rows} metric={metric} />
          </Panel>
          <p className="text-dim cohort-legend">
            Box = IQR (q1–q3) · trait épais = médiane · points = seeds · couleur d'accent = outliers (hors 1,5×IQR)
          </p>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Lancer les tests pour vérifier le succès**

Run : `npx vitest run src/components/CohortView.test.tsx`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/CohortView.tsx frontend/src/components/CohortView.test.tsx frontend/src/api/queryKeys.ts
git commit -m "$(cat <<'EOF'
feat(cohort): vue CohortView (selecteur metrique, etats, cablage queries)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Intégration onglet (tabs + App lazy)

**Files:**
- Modify: `frontend/src/tabs.ts` (clé `cohorte` + entrée famille Analyse)
- Modify: `frontend/src/App.tsx` (lazy import + branche de rendu)

**Interfaces:**
- Consumes: `CohortView` de `./components/CohortView` ; `CandlestickChart` de `lucide-react`.
- Produces: nouvel onglet `"cohorte"` navigable.

- [ ] **Step 1: Ajouter la clé `cohorte` à `TAB_KEYS`**

Dans `frontend/src/tabs.ts`, dans le tableau `TAB_KEYS`, ajouter `"cohorte"` juste après `"sweeps"` :

```ts
  "sweeps",
  "cohorte",
  "parcours",
```

- [ ] **Step 2: Importer l'icône et ajouter l'entrée de famille**

Dans `frontend/src/tabs.ts`, ajouter `CandlestickChart` à l'import lucide-react (ordre alphabétique, après `BarChart3`) :

```ts
  BarChart3,
  CandlestickChart,
  Compass,
```

Puis, dans la famille **Analyse** (après l'entrée `sweeps`), ajouter :

```ts
      { key: "sweeps", label: "Sweeps", icon: Spline },
      { key: "cohorte", label: "Cohorte", icon: CandlestickChart },
```

- [ ] **Step 3: Lancer le test des onglets pour vérifier la cohérence**

Run : `npx vitest run src/tabs.test.ts`
Expected: PASS si un test d'onglets existe ; sinon (aucun test) la commande affiche « No test files found » — passer à l'étape suivante. (La clé doit figurer dans `TAB_KEYS` ET dans une famille pour rester cohérente.)

- [ ] **Step 4: Câbler le lazy import et la branche dans `App.tsx`**

Dans `frontend/src/App.tsx`, ajouter le lazy import près des autres (après la ligne `SweepView`) :

```ts
const CohortView = lazy(() => import("./components/CohortView").then((m) => ({ default: m.CohortView })));
```

Puis ajouter la branche de rendu juste après `{tab === "sweeps" && <SweepView />}` :

```tsx
          {tab === "cohorte" && <CohortView />}
```

- [ ] **Step 5: Vérifier le typage et la suite frontend**

Run (depuis `frontend/`) : `npx tsc --noEmit`
Expected: aucune erreur de type.

Run : `npx vitest run`
Expected: PASS (toute la suite frontend, incluant cohort).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/tabs.ts frontend/src/App.tsx
git commit -m "$(cat <<'EOF'
feat(cohort): integrer l'onglet Cohorte (famille Analyse) + lazy-load

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Backend — endpoint `/api/runs/distributions` (patch-and-handoff vers d1)

> **Branche dédiée** : depuis `feat/d1-prod-pairing`, créer `feat/distributions-endpoint` ; PR **dans** `feat/d1-prod-pairing` (frontière session parallèle — ne pas pousser sur leur branche). Cette tâche est indépendante des tâches 1-4.

**Files:**
- Modify: `backend/app/schemas.py` (ajout `DistributionSummary`)
- Modify: `backend/app/services/runs_service.py` (méthode `list_distributions`)
- Modify: `backend/app/routes/runs.py` (route GET)
- Test: `tests/test_backend.py` (nouveau test)
- Modify (régén) : `frontend/openapi.json`, `frontend/src/api/schema.ts`

**Interfaces:**
- Consumes: `runs_service._values(name, metric)` et `runs_service._scan()` (déjà présents) ; `Query` de fastapi (déjà importé dans `routes/runs.py`).
- Produces: `GET /api/runs/distributions?metric=X` → `list[DistributionSummary]` où `DistributionSummary = {name: str, vals: list[float], n: int}`.

- [ ] **Step 1: Écrire le test backend qui échoue**

Dans `tests/test_backend.py`, ajouter (à la suite de `test_list_sweeps_extracts_knob_levels_series`) :

```python
def test_list_distributions_returns_per_seed_vals(tmp_path, monkeypatch) -> None:
    """Distributions : vals par seed pour chaque condition portant la métrique ; autres exclues."""
    import backend.app.services.runs_service as rs_mod
    monkeypatch.setattr(rs_mod, "RESULTS_DIR", tmp_path)
    (tmp_path / "A_0.json").write_text(json.dumps({"name": "A", "seed": 0, "data": {"fitness": 0.2}}), encoding="utf-8")
    (tmp_path / "A_1.json").write_text(json.dumps({"name": "A", "seed": 1, "data": {"fitness": 0.4}}), encoding="utf-8")
    (tmp_path / "B_0.json").write_text(json.dumps({"name": "B", "seed": 0, "data": {"autre": 9.0}}), encoding="utf-8")
    dists = rs_mod.runs_service.list_distributions("fitness")
    assert len(dists) == 1
    assert dists[0]["name"] == "A"
    assert sorted(dists[0]["vals"]) == [0.2, 0.4]
    assert dists[0]["n"] == 2

    resp = client.get("/api/runs/distributions", params={"metric": "fitness"})
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "A"
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run (depuis la racine) : `PYTHONPATH=. python -m pytest tests/test_backend.py::test_list_distributions_returns_per_seed_vals -v`
Expected: FAIL (`list_distributions` n'existe pas / route 404).

- [ ] **Step 3: Ajouter le modèle Pydantic**

Dans `backend/app/schemas.py`, à côté de `SweepResult`, ajouter :

```python
class DistributionSummary(BaseModel):
    name: str
    vals: list[float]
    n: int
```

- [ ] **Step 4: Implémenter la méthode de service**

Dans `backend/app/services/runs_service.py`, ajouter cette méthode dans la classe (après `_values`) :

```python
    def list_distributions(self, metric: str) -> list[dict]:
        """Valeurs par seed de chaque condition portant `metric` (conditions sans la métrique exclues)."""
        out: list[dict] = []
        for name in sorted({r["name"] for r in self._scan()}):
            vals = self._values(name, metric)
            if vals:
                out.append({"name": name, "vals": vals, "n": len(vals)})
        return out
```

- [ ] **Step 5: Ajouter la route**

Dans `backend/app/routes/runs.py`, ajouter `DistributionSummary` à l'import depuis `..schemas` (ligne 4), puis ajouter la route après `list_sweeps` (vers la ligne 24) :

```python
@router.get("/runs/distributions", response_model=list[DistributionSummary])
def list_distributions(metric: str = Query(..., description="métrique numérique à distribuer")) -> list[dict]:
    """Distributions par seed des conditions portant `metric` (vue cohorte)."""
    return runs_service.list_distributions(metric)
```

- [ ] **Step 6: Lancer le test pour vérifier le succès**

Run : `PYTHONPATH=. python -m pytest tests/test_backend.py::test_list_distributions_returns_per_seed_vals -v`
Expected: PASS.

- [ ] **Step 7: Régénérer le schéma OpenAPI et les types TS (drift gate)**

Run (depuis la racine) :
```bash
PYTHONPATH=. python tools/dump_openapi.py
cd frontend && npm run gen:api && cd ..
```
Expected: `frontend/openapi.json` et `frontend/src/api/schema.ts` mis à jour avec l'opération `list_distributions_api_runs_distributions_get`. Vérifier `git diff --stat` non vide sur ces 2 fichiers.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas.py backend/app/services/runs_service.py backend/app/routes/runs.py tests/test_backend.py frontend/openapi.json frontend/src/api/schema.ts
git commit -m "$(cat <<'EOF'
feat(runs): endpoint GET /api/runs/distributions (vals par seed pour la vue cohorte)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Notes d'exécution

- **Tâches 1→4** sur `feat/frontend-cohort-view`, dans l'ordre (chacune dépend des types/composants de la précédente). PR vers `main` une fois la suite verte.
- **Tâche 5** indépendante, sur une branche depuis `feat/d1-prod-pairing`, PR dans leur branche. Jusqu'à propagation d→main, l'onglet Cohorte dégrade en Error/Empty proprement.
- Avant de finir la branche frontend : restaurer `backend/test.setup.ts`/fichiers touchés par le linter au changement de branche si nécessaire (LF/CRLF), comme pour les vagues précédentes.
