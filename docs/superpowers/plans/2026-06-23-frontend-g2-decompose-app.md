# G2 — Dégonfler App.tsx — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extraire les 4 onglets inline d'`App.tsx` en composants auto-suffisants (+ `GateSidebar`, `lib/charts`), réduisant App à un shell.

**Architecture:** Chaque vue possède ses données (`useQuery`, dédup par `queryKeys`) et lit la route (`useHashRoute`, synchro `hashchange`) — pas de prop drilling. App ne garde que routing d'onglet + thème + layout. Les 4 nouvelles vues sont lazy (synergie G1) ; `GateSidebar` reste eager.

**Tech Stack:** React 18, @tanstack/react-query v5, TypeScript, Vitest + RTL.

## Global Constraints

- Comportement runtime **identique** : mêmes onglets, mêmes vues, mêmes deep-links `?gate=` / `?ab=`.
- Pas de changement CSS (réutiliser les classes existantes : `sidebar`, `summary-panel`, `metrics-panel`, `chart-svg`, `legend-row`, `legend-dot`, `comparison-list`, `comparison-card`, `topology-grid`, `topology-visual`, `topology-analysis`, `motif-summary`, `academy-box`, `row`, `mb-4`).
- Pas de changement backend / API → pas de régénération OpenAPI/`schema.ts`.
- Vues qui lisent la route : `useHashRoute(TAB_KEYS, "edr")` (import `TAB_KEYS` depuis `../tabs`).
- Données : `queryKeys.experiments.list`, `queryKeys.experiments.detail(gate)`, `queryKeys.academy` ; `apiFetch` depuis `../api/client`.
- Commits français, conventionnels, sans emoji, finissant par `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Tests : `QueryClientProvider` (client `retry: false`) + `vi.mock("../api/client")` ; `import { vi, test, expect } from "vitest"` (pas de globals).

---

### Task 1 : `lib/charts.ts` (helpers purs)

**Files:**
- Create: `frontend/src/lib/charts.ts`
- Test: `frontend/src/lib/charts.test.ts`

**Interfaces:**
- Produces: `createLinePath(values: number[], width: number, height: number): string` ; `createStabilitySeries(values: number[]): number[]` ; `formatPercentage(value: number): string`.

- [ ] **Step 1 : test (RED)**

```ts
// frontend/src/lib/charts.test.ts
import { test, expect } from "vitest";
import { createLinePath, createStabilitySeries, formatPercentage } from "./charts";

test("formatPercentage formate en pourcentage à 1 décimale", () => {
  expect(formatPercentage(0.5)).toBe("50.0%");
  expect(formatPercentage(1)).toBe("100.0%");
});

test("createLinePath: vide si aucune valeur, sinon path SVG non vide", () => {
  expect(createLinePath([], 100, 100)).toBe("");
  expect(createLinePath([0, 0.5, 1], 700, 260)).toMatch(/^M /);
});

test("createStabilitySeries: bornée dans [0,1], 1 pour série triviale", () => {
  expect(createStabilitySeries([0.5])).toEqual([1]);
  const s = createStabilitySeries([0, 1, 0, 1]);
  expect(s.every((v) => v >= 0 && v <= 1)).toBe(true);
});
```

- [ ] **Step 2 : run RED** — `cd /c/Users/robla/VScode_Project/AGAGI-front && npm --prefix frontend run test -- charts` → FAIL (module introuvable).

- [ ] **Step 3 : implémentation**

```ts
// frontend/src/lib/charts.ts
export function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function createLinePath(values: number[], width: number, height: number): string {
  const count = values.length;
  if (!count) return "";
  const maxValue = Math.max(...values, 1);
  const minValue = Math.min(...values, 0);
  const scaleY = (v: number) => height - ((v - minValue) / (maxValue - minValue || 1)) * height;
  const step = width / Math.max(count - 1, 1);
  return values
    .map((value, index) => `${index === 0 ? "M" : "L"} ${index * step} ${scaleY(value)}`)
    .join(" ");
}

export function createStabilitySeries(values: number[]): number[] {
  if (values.length <= 1) {
    return values.map(() => 1);
  }
  const deltas = values.map((value, index) => (index === 0 ? 0 : Math.abs(value - values[index - 1])));
  const maxDelta = Math.max(...deltas.slice(1), 0.01);
  return deltas.map((delta) => 1 - Math.min(1, delta / maxDelta));
}
```

- [ ] **Step 4 : run GREEN** — `npm --prefix frontend run test -- charts` → PASS.
- [ ] **Step 5 : commit**

```bash
cd /c/Users/robla/VScode_Project/AGAGI-front && git add frontend/src/lib/charts.ts frontend/src/lib/charts.test.ts && git commit -m "$(cat <<'EOF'
refactor(frontend): lib/charts — helpers purs (createLinePath/createStabilitySeries/formatPercentage)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2 : `GateSidebar`

**Files:**
- Create: `frontend/src/components/GateSidebar.tsx`
- Test: `frontend/src/components/GateSidebar.test.tsx`

**Interfaces:**
- Consumes: `formatPercentage` (Task 1) ; `useHashRoute`, `queryKeys`, `apiFetch`, `TAB_KEYS`, type `ExperimentSummary`.
- Produces: `GateSidebar()` (export nommé) — rend `<aside className="sidebar">…`. Aucun prop.

> Note staging : App garde encore son bandeau inline jusqu'à Task 7 (duplication temporaire assumée).

- [ ] **Step 1 : test (RED)**

```tsx
// frontend/src/components/GateSidebar.test.tsx
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { GateSidebar } from "./GateSidebar";

const EXPS = [
  { gate: "AND", latest_fitness: 0.9, latest_accuracy: 1, emergent_score: 0.5, robustness_score: 0.4, performance_stability: 0.3, latest_size: 7 },
  { gate: "OR", latest_fitness: 0.8, latest_accuracy: 0.9 },
];

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  window.location.hash = "#/evolution?gate=AND";
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue(EXPS);
});

test("affiche le select de porte et une métrique agrégée", async () => {
  renderWithClient(<GateSidebar />);
  expect(await screen.findByText("Vue globale")).toBeTruthy();
  expect(screen.getByText(/Total portes : 2/)).toBeTruthy();
});
```

- [ ] **Step 2 : run RED** — `npm --prefix frontend run test -- GateSidebar` → FAIL.

- [ ] **Step 3 : implémentation**

```tsx
// frontend/src/components/GateSidebar.tsx
import { useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ExperimentSummary } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { useHashRoute } from "../hooks/useHashRoute";
import { TAB_KEYS } from "../tabs";
import { formatPercentage } from "../lib/charts";

export function GateSidebar() {
  const { gate: selectedGate, setGate } = useHashRoute(TAB_KEYS, "edr");
  const { data: experiments = [] } = useQuery({
    queryKey: queryKeys.experiments.list,
    queryFn: () => apiFetch<ExperimentSummary[]>("/api/experiments"),
    staleTime: 30_000,
  });

  const selectedExperiment = useMemo(
    () => experiments.find((item) => item.gate === selectedGate),
    [experiments, selectedGate],
  );

  const summaryMetrics = useMemo(() => {
    if (!experiments.length) return null;
    const fitnessValues = experiments.map((item) => item.latest_fitness);
    const accuracyValues = experiments.map((item) => item.latest_accuracy);
    const sizes = experiments.flatMap((item) => (item.latest_size !== undefined ? [item.latest_size] : []));
    const bestFitness = experiments.reduce((best, current) => (current.latest_fitness > best.latest_fitness ? current : best), experiments[0]);
    const bestAccuracy = experiments.reduce((best, current) => (current.latest_accuracy > best.latest_accuracy ? current : best), experiments[0]);
    const emergentScores = experiments.flatMap((item) => (item.emergent_score !== undefined ? [item.emergent_score] : []));
    const robustnessScores = experiments.flatMap((item) => (item.robustness_score !== undefined ? [item.robustness_score] : []));
    const stabilityScores = experiments.flatMap((item) => (item.performance_stability !== undefined ? [item.performance_stability] : []));
    return {
      count: experiments.length,
      averageFitness: fitnessValues.reduce((sum, value) => sum + value, 0) / fitnessValues.length,
      averageAccuracy: accuracyValues.reduce((sum, value) => sum + value, 0) / accuracyValues.length,
      averageEmergentScore: emergentScores.length ? emergentScores.reduce((sum, value) => sum + value, 0) / emergentScores.length : 0,
      averageRobustness: robustnessScores.length ? robustnessScores.reduce((sum, value) => sum + value, 0) / robustnessScores.length : 0,
      averageStability: stabilityScores.length ? stabilityScores.reduce((sum, value) => sum + value, 0) / stabilityScores.length : 0,
      bestFitnessGate: bestFitness.gate,
      bestAccuracyGate: bestAccuracy.gate,
      bestEmergentGate: experiments.reduce((best, current) => (current.emergent_score !== undefined && current.emergent_score > (best.emergent_score ?? -Infinity) ? current : best), experiments[0]).gate,
      bestRobustGate: experiments.reduce((best, current) => (current.robustness_score !== undefined && current.robustness_score > (best.robustness_score ?? -Infinity) ? current : best), experiments[0]).gate,
      smallestSize: sizes.length ? Math.min(...sizes) : undefined,
    };
  }, [experiments]);

  useEffect(() => {
    if (experiments.length && !selectedGate) {
      setGate(experiments[0].gate);
    }
  }, [experiments, selectedGate]);

  return (
    <aside className="sidebar">
      <label htmlFor="gate-select">Sélectionner une porte</label>
      <select id="gate-select" value={selectedGate} onChange={(event) => setGate(event.target.value)}>
        {experiments.map((experiment) => (
          <option key={experiment.gate} value={experiment.gate}>
            {experiment.gate}
          </option>
        ))}
      </select>

      {summaryMetrics ? (
        <div className="summary-panel">
          <h2>Vue globale</h2>
          <p>Total portes : {summaryMetrics.count}</p>
          <p>Meilleure fitness : {summaryMetrics.bestFitnessGate}</p>
          <p>Meilleure précision : {summaryMetrics.bestAccuracyGate}</p>
          <p>Meilleur score d'intelligence : {summaryMetrics.bestEmergentGate}</p>
          <p>Fitness moyenne : {summaryMetrics.averageFitness.toFixed(4)}</p>
          <p>Précision moyenne : {formatPercentage(summaryMetrics.averageAccuracy)}</p>
          <p>Score d'intelligence moyen : {summaryMetrics.averageEmergentScore.toFixed(3)}</p>
          <p>Robustesse moyenne : {summaryMetrics.averageRobustness.toFixed(3)}</p>
          <p>Stabilité moyenne : {summaryMetrics.averageStability.toFixed(3)}</p>
          {summaryMetrics.smallestSize !== undefined && <p>Plus petite topologie : {summaryMetrics.smallestSize}</p>}
        </div>
      ) : null}

      {selectedExperiment ? (
        <div className="metrics-panel">
          <h2>{selectedExperiment.gate}</h2>
          <p>Fitness finale : {selectedExperiment.latest_fitness.toFixed(4)}</p>
          <p>Précision finale : {formatPercentage(selectedExperiment.latest_accuracy)}</p>
          {selectedExperiment.emergent_score !== undefined && <p>Score d'intelligence : {selectedExperiment.emergent_score.toFixed(3)}</p>}
          {selectedExperiment.robustness_score !== undefined && <p>Robustesse : {selectedExperiment.robustness_score.toFixed(3)}</p>}
          {selectedExperiment.performance_stability !== undefined && <p>Stabilité : {selectedExperiment.performance_stability.toFixed(3)}</p>}
          {selectedExperiment.modularity !== undefined && <p>Modularité : {selectedExperiment.modularity.toFixed(3)}</p>}
          {selectedExperiment.motif_density !== undefined && <p>Densité de motifs : {selectedExperiment.motif_density.toFixed(3)}</p>}
          {selectedExperiment.latest_size !== undefined && <p>Taille finale : {selectedExperiment.latest_size}</p>}
        </div>
      ) : null}
    </aside>
  );
}
```

- [ ] **Step 4 : run GREEN** — `npm --prefix frontend run test -- GateSidebar` → PASS.
- [ ] **Step 5 : commit**

```bash
cd /c/Users/robla/VScode_Project/AGAGI-front && git add frontend/src/components/GateSidebar.tsx frontend/src/components/GateSidebar.test.tsx && git commit -m "$(cat <<'EOF'
refactor(frontend): extraire GateSidebar (experiments + résumé + porte par défaut)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3 : `EvolutionView`

**Files:**
- Create: `frontend/src/components/EvolutionView.tsx`
- Test: `frontend/src/components/EvolutionView.test.tsx`

**Interfaces:**
- Consumes: `createLinePath`, `createStabilitySeries` (Task 1) ; `LiveEvolution` (existant) ; `useHashRoute`, `queryKeys`, `apiFetch`, `TAB_KEYS`, type `ExperimentDetail`.
- Produces: `EvolutionView()` (export nommé).

> `ChartLine` est défini local dans ce fichier (mono-usage). App garde son bloc inline jusqu'à Task 7.

- [ ] **Step 1 : test (RED)**

```tsx
// frontend/src/components/EvolutionView.test.tsx
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
vi.mock("./LiveEvolution", () => ({ LiveEvolution: () => <div>live-evolution-stub</div> }));
import { apiFetch } from "../api/client";
import { EvolutionView } from "./EvolutionView";

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  window.location.hash = "#/evolution?gate=AND";
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue({
    gate: "AND",
    history: { generation: [1, 2], fitness: [0.5, 0.8], accuracy: [0.6, 0.9], size: [5, 6] },
  });
});

test("rend le titre, le stub live et le graphe quand detail est chargé", async () => {
  renderWithClient(<EvolutionView />);
  expect(screen.getByText("live-evolution-stub")).toBeTruthy();
  expect(await screen.findByLabelText("Evolution chart")).toBeTruthy();
});
```

- [ ] **Step 2 : run RED** — `npm --prefix frontend run test -- EvolutionView` → FAIL.

- [ ] **Step 3 : implémentation**

```tsx
// frontend/src/components/EvolutionView.tsx
import { useQuery } from "@tanstack/react-query";
import type { ExperimentDetail } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { useHashRoute } from "../hooks/useHashRoute";
import { TAB_KEYS } from "../tabs";
import { LiveEvolution } from "./LiveEvolution";
import { createLinePath, createStabilitySeries } from "../lib/charts";

function ChartLine({ values, color }: { values: number[]; color: string }) {
  return <path d={createLinePath(values, 700, 260)} fill="none" style={{ stroke: color }} strokeWidth={3} />;
}

export function EvolutionView() {
  const { gate } = useHashRoute(TAB_KEYS, "edr");
  const { data: detail = null } = useQuery({
    queryKey: queryKeys.experiments.detail(gate),
    queryFn: () => apiFetch<ExperimentDetail>(`/api/experiments/${gate}`),
    enabled: !!gate,
  });

  const chartData = detail?.history;
  const sizeSeries = chartData?.size ?? [];
  const stabilitySeries = chartData ? createStabilitySeries(chartData.accuracy) : [];

  return (
    <>
      <LiveEvolution />
      <h2>Évolution dynamique</h2>
      {chartData ? (
        <>
          <svg viewBox="0 0 720 300" className="chart-svg" aria-label="Evolution chart">
            <ChartLine values={chartData.fitness} color="var(--viz-1)" />
            <ChartLine values={chartData.accuracy} color="var(--viz-2)" />
            {sizeSeries.length ? <ChartLine values={sizeSeries.map((value: number) => value / Math.max(...sizeSeries, 1))} color="var(--color-text-dim)" /> : null}
            {stabilitySeries.length ? <ChartLine values={stabilitySeries} color="var(--viz-4)" /> : null}
          </svg>
          <div className="legend-row">
            <span className="legend-dot" style={{ background: "var(--viz-1)" }} /> Fitness
            <span className="legend-dot" style={{ background: "var(--viz-2)" }} /> Précision
            <span className="legend-dot" style={{ background: "var(--color-text-dim)" }} /> Taille normalisée
            <span className="legend-dot" style={{ background: "var(--viz-4)" }} /> Stabilité
          </div>
        </>
      ) : (
        <p>Chargement des données...</p>
      )}
    </>
  );
}
```

- [ ] **Step 4 : run GREEN** — PASS.
- [ ] **Step 5 : commit**

```bash
cd /c/Users/robla/VScode_Project/AGAGI-front && git add frontend/src/components/EvolutionView.tsx frontend/src/components/EvolutionView.test.tsx && git commit -m "$(cat <<'EOF'
refactor(frontend): extraire EvolutionView (detail + graphe d'évolution)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4 : `TopologyView`

**Files:**
- Create: `frontend/src/components/TopologyView.tsx`
- Test: `frontend/src/components/TopologyView.test.tsx`

**Interfaces:**
- Consumes: `TopologyViewer` (existant) ; `useHashRoute`, `queryKeys`, `apiFetch`, `TAB_KEYS`, type `ExperimentDetail`.
- Produces: `TopologyView()` (export nommé).

- [ ] **Step 1 : test (RED)**

```tsx
// frontend/src/components/TopologyView.test.tsx
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
vi.mock("./TopologyViewer", () => ({ TopologyViewer: () => <div>topology-stub</div> }));
import { apiFetch } from "../api/client";
import { TopologyView } from "./TopologyView";

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  window.location.hash = "#/topology?gate=AND";
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue({
    gate: "AND",
    graph: { nodes: [{ id: 0, label: "x", type: "input" }], links: [] },
    metrics: { modularity: 0.1, motif_density: 0.2, performance_stability: 0.3, robustness_score: 0.4, sparsity: 0.5, hidden_ratio: 0.6 },
  });
});

test("rend la topologie (stub) et l'analyse des motifs", async () => {
  renderWithClient(<TopologyView />);
  expect(await screen.findByText("topology-stub")).toBeTruthy();
  expect(screen.getByText(/Modularité/)).toBeTruthy();
});
```

- [ ] **Step 2 : run RED** → FAIL.

- [ ] **Step 3 : implémentation**

```tsx
// frontend/src/components/TopologyView.tsx
import { useQuery } from "@tanstack/react-query";
import type { ExperimentDetail } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { useHashRoute } from "../hooks/useHashRoute";
import { TAB_KEYS } from "../tabs";
import { TopologyViewer } from "./TopologyViewer";

export function TopologyView() {
  const { gate } = useHashRoute(TAB_KEYS, "edr");
  const { data: detail = null } = useQuery({
    queryKey: queryKeys.experiments.detail(gate),
    queryFn: () => apiFetch<ExperimentDetail>(`/api/experiments/${gate}`),
    enabled: !!gate,
  });

  return (
    <>
      <h2>Topologie du meilleur modèle</h2>
      <div className="topology-grid">
        <div className="topology-visual">
          {detail?.graph ? <TopologyViewer graph={detail.graph} /> : <p>Topologie indisponible.</p>}
        </div>
        <div className="topology-analysis">
          <h3>Analyse des motifs</h3>
          {detail?.metrics ? (
            <div className="motif-summary">
              <p>Modularité : {detail.metrics.modularity.toFixed(3)}</p>
              <p>Densité de motifs : {detail.metrics.motif_density.toFixed(3)}</p>
              <p>Stabilité : {detail.metrics.performance_stability.toFixed(3)}</p>
              <p>Robustesse : {detail.metrics.robustness_score.toFixed(3)}</p>
              <p>Sparsité : {detail.metrics.sparsity.toFixed(3)}</p>
              <p>Ratio caché : {detail.metrics.hidden_ratio.toFixed(3)}</p>
            </div>
          ) : (
            <p>Chargement de l’analyse...</p>
          )}
        </div>
      </div>
    </>
  );
}
```

- [ ] **Step 4 : run GREEN** → PASS.
- [ ] **Step 5 : commit**

```bash
cd /c/Users/robla/VScode_Project/AGAGI-front && git add frontend/src/components/TopologyView.tsx frontend/src/components/TopologyView.test.tsx && git commit -m "$(cat <<'EOF'
refactor(frontend): extraire TopologyView (detail.graph + métriques motifs)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5 : `ComparisonView`

**Files:**
- Create: `frontend/src/components/ComparisonView.tsx`
- Test: `frontend/src/components/ComparisonView.test.tsx`

**Interfaces:**
- Consumes: `formatPercentage` (Task 1) ; `Button`, `ComparisonChart`, `RadarChart`, `ABComparisonView` (existants) ; `useHashRoute`, `queryKeys`, `apiFetch`, `TAB_KEYS`, type `ExperimentSummary`.
- Produces: `ComparisonView()` (export nommé).

- [ ] **Step 1 : test (RED)**

```tsx
// frontend/src/components/ComparisonView.test.tsx
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
vi.mock("./ComparisonChart", () => ({ ComparisonChart: () => <div>comparison-chart-stub</div> }));
vi.mock("./RadarChart", () => ({ RadarChart: () => <div>radar-stub</div> }));
vi.mock("./ABComparisonView", () => ({ ABComparisonView: () => <div>ab-stub</div> }));
import { apiFetch } from "../api/client";
import { ComparisonView } from "./ComparisonView";

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue([{ gate: "AND", latest_fitness: 0.9, latest_accuracy: 1 }]);
});

test("mode global par défaut (sans ?ab=)", async () => {
  window.location.hash = "#/comparison";
  renderWithClient(<ComparisonView />);
  expect(await screen.findByText("comparison-chart-stub")).toBeTruthy();
});

test("mode AB si ?ab= présent dans le hash", async () => {
  window.location.hash = "#/comparison?ab=robust_eval";
  renderWithClient(<ComparisonView />);
  expect(await screen.findByText("ab-stub")).toBeTruthy();
});
```

- [ ] **Step 2 : run RED** → FAIL.

- [ ] **Step 3 : implémentation**

```tsx
// frontend/src/components/ComparisonView.tsx
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ExperimentSummary } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { useHashRoute } from "../hooks/useHashRoute";
import { TAB_KEYS } from "../tabs";
import { Button } from "./ui/Button";
import { ComparisonChart } from "./ComparisonChart";
import { RadarChart } from "./RadarChart";
import { ABComparisonView } from "./ABComparisonView";
import { formatPercentage } from "../lib/charts";

export function ComparisonView() {
  const { query } = useHashRoute(TAB_KEYS, "edr");
  const { data: experiments = [] } = useQuery({
    queryKey: queryKeys.experiments.list,
    queryFn: () => apiFetch<ExperimentSummary[]>("/api/experiments"),
    staleTime: 30_000,
  });
  const [compareMode, setCompareMode] = useState<"global" | "ab">("global");

  useEffect(() => {
    if (query.ab) setCompareMode("ab");
  }, [query.ab]);

  return (
    <>
      <div className="row mb-4">
        <Button variant={compareMode === "global" ? "primary" : "ghost"} size="sm" onClick={() => setCompareMode("global")}>
          Vue globale
        </Button>
        <Button variant={compareMode === "ab" ? "primary" : "ghost"} size="sm" onClick={() => setCompareMode("ab")}>
          A/B rigoureux
        </Button>
      </div>
      {compareMode === "ab" ? (
        <>
          <h2>A/B rigoureux (runs multi-seed)</h2>
          <ABComparisonView preselectA={query.ab} />
        </>
      ) : (
        <>
          <h2>Comparaison des portes</h2>
          <ComparisonChart experiments={experiments} />
          <RadarChart experiments={experiments} />
          <div className="comparison-list">
            {experiments.map((item) => (
              <div key={item.gate} className="comparison-card">
                <strong>{item.gate}</strong>
                <span>Fitness: {item.latest_fitness.toFixed(3)}</span>
                <span>Précision: {formatPercentage(item.latest_accuracy)}</span>
                {item.robustness_score !== undefined && <span>Robustesse: {item.robustness_score.toFixed(3)}</span>}
                {item.performance_stability !== undefined && <span>Stabilité: {item.performance_stability.toFixed(3)}</span>}
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}
```

- [ ] **Step 4 : run GREEN** → PASS (2 tests).
- [ ] **Step 5 : commit**

```bash
cd /c/Users/robla/VScode_Project/AGAGI-front && git add frontend/src/components/ComparisonView.tsx frontend/src/components/ComparisonView.test.tsx && git commit -m "$(cat <<'EOF'
refactor(frontend): extraire ComparisonView (toggle global/AB + deep-link ?ab=)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6 : `AcademyView`

**Files:**
- Create: `frontend/src/components/AcademyView.tsx`
- Test: `frontend/src/components/AcademyView.test.tsx`

**Interfaces:**
- Consumes: `queryKeys`, `apiFetch`, type `AcademyPayload`.
- Produces: `AcademyView()` (export nommé). N'utilise pas la route.

- [ ] **Step 1 : test (RED)**

```tsx
// frontend/src/components/AcademyView.test.tsx
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { AcademyView } from "./AcademyView";

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue({
    version_history: [{ title: "v1", description: "première" }],
    timeline: ["étape 1"],
    learning_goals: ["objectif 1"],
  });
});

test("rend les 3 boîtes Academy", async () => {
  renderWithClient(<AcademyView />);
  expect(await screen.findByText("Historique des versions")).toBeTruthy();
  expect(screen.getByText("Timeline")).toBeTruthy();
  expect(screen.getByText("Objectifs pédagogiques")).toBeTruthy();
});
```

- [ ] **Step 2 : run RED** → FAIL.

- [ ] **Step 3 : implémentation**

```tsx
// frontend/src/components/AcademyView.tsx
import { useQuery } from "@tanstack/react-query";
import type { AcademyPayload } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";

export function AcademyView() {
  const { data: academy = null } = useQuery({
    queryKey: queryKeys.academy,
    queryFn: () => apiFetch<AcademyPayload>("/api/academy"),
    staleTime: Infinity,
  });

  return (
    <>
      <h2>Academy</h2>
      {academy ? (
        <div>
          <div className="academy-box">
            <h3>Historique des versions</h3>
            <ol>
              {academy.version_history.map((item) => (
                <li key={item.title}>
                  <strong>{item.title}</strong> — {item.description}
                </li>
              ))}
            </ol>
          </div>
          <div className="academy-box">
            <h3>Timeline</h3>
            <ol>
              {academy.timeline.map((event, index) => (
                <li key={index}>{event}</li>
              ))}
            </ol>
          </div>
          <div className="academy-box">
            <h3>Objectifs pédagogiques</h3>
            <ul>
              {academy.learning_goals.map((goal, index) => (
                <li key={index}>{goal}</li>
              ))}
            </ul>
          </div>
        </div>
      ) : (
        <p>Chargement des contenus Academy...</p>
      )}
    </>
  );
}
```

- [ ] **Step 4 : run GREEN** → PASS.
- [ ] **Step 5 : commit**

```bash
cd /c/Users/robla/VScode_Project/AGAGI-front && git add frontend/src/components/AcademyView.tsx frontend/src/components/AcademyView.test.tsx && git commit -m "$(cat <<'EOF'
refactor(frontend): extraire AcademyView (payload academy)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7 : Réécrire `App.tsx` en shell + câbler les vues (lazy)

**Files:**
- Modify: `frontend/src/App.tsx` (réécriture complète)

**Interfaces:**
- Consumes: `GateSidebar` (T2, eager), `EvolutionView` (T3), `ComparisonView` (T5), `TopologyView` (T4), `AcademyView` (T6) — les 4 dernières en lazy ; vues existantes lazy de G1 ; `EDRDashboard` eager ; `Loading`, `ErrorBoundary`, `useTheme`, `useHashRoute`, `TAB_KEYS`/`TAB_FAMILIES`.
- Produces: `App` (default export) — shell sans données métier.

- [ ] **Step 1 : remplacer intégralement `frontend/src/App.tsx` par :**

```tsx
import { lazy, Suspense } from "react";
import { useTheme } from "./hooks/useTheme";
import { useHashRoute } from "./hooks/useHashRoute";
import { TAB_KEYS, TAB_FAMILIES } from "./tabs";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { GateSidebar } from "./components/GateSidebar";
import { EDRDashboard } from "./components/EDRDashboard";
import { Loading } from "./components/ui/Loading";
import { Sun, Moon } from "lucide-react";

const LiveMetrics = lazy(() => import("./components/LiveMetrics").then((m) => ({ default: m.LiveMetrics })));
const FlatlandViewer = lazy(() => import("./components/FlatlandViewer").then((m) => ({ default: m.FlatlandViewer })));
const EvolutionView = lazy(() => import("./components/EvolutionView").then((m) => ({ default: m.EvolutionView })));
const ComparisonView = lazy(() => import("./components/ComparisonView").then((m) => ({ default: m.ComparisonView })));
const TopologyView = lazy(() => import("./components/TopologyView").then((m) => ({ default: m.TopologyView })));
const AcademyView = lazy(() => import("./components/AcademyView").then((m) => ({ default: m.AcademyView })));
const LaboratoryView = lazy(() => import("./components/LaboratoryView").then((m) => ({ default: m.LaboratoryView })));
const TimelineViewer = lazy(() => import("./components/TimelineViewer").then((m) => ({ default: m.TimelineViewer })));
const SandboxView = lazy(() => import("./components/SandboxView").then((m) => ({ default: m.SandboxView })));
const RunLauncher = lazy(() => import("./components/RunLauncher").then((m) => ({ default: m.RunLauncher })));
const RunsHistoryView = lazy(() => import("./components/RunsHistoryView").then((m) => ({ default: m.RunsHistoryView })));
const HealthView = lazy(() => import("./components/HealthView").then((m) => ({ default: m.HealthView })));

export default function App() {
  const { theme, toggle } = useTheme();
  const { tab, setTab, navigate } = useHashRoute(TAB_KEYS, "edr");
  const showSidebar = tab === "evolution" || tab === "comparison" || tab === "topology";

  return (
    <div className="page-shell">
      <header className="topbar">
        <div>
          <h1>AGIseed Dashboard</h1>
          <p>Instrument d'expérimentation — biosphère évolutive, runs multi-seed &amp; A/B rigoureux</p>
        </div>
        <div className="topbar-right">
          <button className="theme-toggle" onClick={toggle} aria-label="Basculer le thème">
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            {theme === "dark" ? "Clair" : "Sombre"}
          </button>
          <nav className="tabs">
            {TAB_FAMILIES.map((group) => (
              <div key={group.family} className="tab-family" title={group.family}>
                {group.tabs.map(({ key, label, icon: Icon }) => (
                  <button
                    key={key}
                    data-testid={`tab-${key}`}
                    className={key === tab ? "active" : ""}
                    onClick={() => setTab(key)}
                  >
                    <Icon size={16} />
                    {label}
                  </button>
                ))}
              </div>
            ))}
          </nav>
        </div>
      </header>

      <main className={showSidebar ? "content" : "content content--full"}>
        {showSidebar && <GateSidebar />}

        <section className="panel">
          <ErrorBoundary key={tab}>
          <Suspense fallback={<Loading label="Chargement de la vue…" />}>
          {tab === "edr" && <EDRDashboard />}
          {tab === "live" && (
            <>
              <LiveMetrics />
              <FlatlandViewer />
            </>
          )}
          {tab === "evolution" && <EvolutionView />}
          {tab === "comparison" && <ComparisonView />}
          {tab === "topology" && <TopologyView />}
          {tab === "academy" && <AcademyView />}
          {tab === "laboratoire" && <LaboratoryView />}
          {tab === "timeline" && <TimelineViewer />}
          {tab === "sandbox" && (
            <>
              <RunLauncher />
              <SandboxView />
            </>
          )}
          {tab === "runs" && <RunsHistoryView onCompare={(cond) => navigate("comparison", { ab: cond })} />}
          {tab === "sante" && <HealthView />}
          </Suspense>
          </ErrorBoundary>
        </section>
      </main>
    </div>
  );
}
```

- [ ] **Step 2 : typecheck + suite complète**

Run : `cd /c/Users/robla/VScode_Project/AGAGI-front && npm --prefix frontend run test`
Expected : tous les tests passent (15 existants + 8 nouveaux des tâches 1-6).

- [ ] **Step 3 : build + vérifier App réduit**

Run : `cd /c/Users/robla/VScode_Project/AGAGI-front && npm --prefix frontend run build`
Expected : build `tsc` vert (aucun import inutilisé, aucune variable orpheline). Confirmer `App.tsx` < ~120 lignes.

- [ ] **Step 4 : commit**

```bash
cd /c/Users/robla/VScode_Project/AGAGI-front && git add frontend/src/App.tsx && git commit -m "$(cat <<'EOF'
refactor(frontend): App.tsx réduit au shell (vues extraites + lazy, G2)

App ne porte plus de données métier : routing d'onglet + thème + layout. Les 4
onglets jadis inline (evolution/comparison/topology/academy) sont des composants
auto-suffisants et lazy ; GateSidebar extrait. ~381 -> ~110 lignes.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

- **Spec coverage** : lib/charts (T1) ; GateSidebar (T2, + sélection par défaut) ; EvolutionView (T3) ; TopologyView (T4) ; ComparisonView (T5, toggle + ?ab=) ; AcademyView (T6) ; App shell + lazy + showSidebar + onCompare (T7). ✅ Tous les éléments du spec couverts.
- **Placeholders** : aucun — code complet pour chaque fichier et chaque test.
- **Type consistency** : exports nommés cohérents (`GateSidebar`, `EvolutionView`, `ComparisonView`, `TopologyView`, `AcademyView`) ; wrappers lazy de T7 utilisent ces noms exacts ; `queryKeys.experiments.list`/`.detail(gate)`/`academy` cohérents entre vues (dédup) ; helpers `lib/charts` signatures identiques entre T1 et consommateurs (T2/T3/T5).
- **Staging note** : T2-T6 créent des composants qui dupliquent temporairement la logique encore inline dans App ; T7 retire l'inline et câble. Duplication intentionnelle et transitoire (résolue à T7), à ne pas traiter comme defect.
