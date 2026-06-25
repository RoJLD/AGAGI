# Sweep v2 — superposition multi-knob — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faire évoluer l'onglet Sweeps pour superposer plusieurs séries `(sweep × métrique)` partageant un knob, avec normalisation optionnelle.

**Architecture:** Helpers purs dans `lib/sweep.ts` (`normalizeSeries`, `buildOverlayData` qui aligne les séries sur l'union de leurs X) → composant recharts `SweepOverlayChart` (N lignes) → rewire `SweepView` (sélecteur knob + multi-sélection de séries par cases + toggle normalisation). Le mono-série `SweepChart` (et `buildSweepData`) est retiré en fin de chantier (pas de code mort).

**Tech Stack:** React 18 + TypeScript strict + @tanstack/react-query v5 + recharts + Vitest + Testing Library.

## Global Constraints

- **Frontend uniquement** : `frontend/src/**` + `docs/**`. Branche `feat/frontend-sweep-overlay` → PR vers `main`. `/api/sweeps` est déjà sur `main`, aucune dépendance backend.
- **Langue** : libellés/commentaires en français.
- **Pas d'emoji** dans le code ni les commits.
- **TypeScript** : zéro `any`, types explicites.
- **Commits** : chaque commit se termine par le trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Tests** depuis `frontend/` : `npx vitest run <chemin>`. Un seul appel bash composé (`cd frontend && npx ...`) pour éviter les resets de cwd.
- **Superposition groupée par knob** (X = unité du knob, honnête). Pas de cross-knob normalisé en v1.
- **Normalisation** = min-max [0,1] par série (défaut OFF). **Bande ±std** uniquement si 1 série sélectionnée et mode brut.
- **Sélection à 1 série = comportement v1** (aucune régression).
- **Chaque tâche laisse la suite verte** : Tâche 1 AJOUTE les helpers overlay (garde `buildSweepData`) ; le retrait du mono-série mort n'a lieu qu'en Tâche 3.

---

### Task 1: `lib/sweep.ts` — helpers de superposition (ajout)

**Files:**
- Modify: `frontend/src/lib/sweep.ts` (ajout en fin de fichier, `buildSweepData`/`SweepPoint` conservés)
- Test: `frontend/src/lib/sweep.test.ts` (ajout de tests, ceux existants conservés)

**Interfaces:**
- Consumes: rien (helpers purs).
- Produces:
  - `interface OverlaySeries { id: string; label: string; knob: string; x: number[]; y: number[]; yStd?: number[] }`
  - `interface OverlayPoint { x: number; [seriesKey: string]: number | [number, number] | undefined }`
  - `function normalizeSeries(y: number[]): number[]`
  - `function buildOverlayData(series: OverlaySeries[], normalize: boolean): OverlayPoint[]`

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter en fin de `frontend/src/lib/sweep.test.ts` (NE PAS toucher aux tests `buildSweepData` existants) :

```ts
import { normalizeSeries, buildOverlayData, type OverlaySeries } from "./sweep";

const S = (id: string, x: number[], y: number[], yStd?: number[]): OverlaySeries => ({
  id, label: id, knob: "k", x, y, yStd,
});

test("normalizeSeries : min-max [0,1]", () => {
  expect(normalizeSeries([1, 2, 3, 4, 5])).toEqual([0, 0.25, 0.5, 0.75, 1]);
});

test("normalizeSeries : série plate -> zéros", () => {
  expect(normalizeSeries([2, 2])).toEqual([0, 0]);
});

test("buildOverlayData : 2 séries même X -> une clé par série", () => {
  expect(buildOverlayData([S("a", [1, 2], [10, 20]), S("b", [1, 2], [30, 40])], false)).toEqual([
    { x: 1, a: 10, b: 30 },
    { x: 2, a: 20, b: 40 },
  ]);
});

test("buildOverlayData : X disjoints -> union triée, trous absents", () => {
  expect(buildOverlayData([S("a", [1, 3], [10, 30]), S("b", [2, 3], [20, 33])], false)).toEqual([
    { x: 1, a: 10 },
    { x: 2, b: 20 },
    { x: 3, a: 30, b: 33 },
  ]);
});

test("buildOverlayData : normalize=true -> valeurs normalisées, pas de bande", () => {
  expect(buildOverlayData([S("a", [1, 2, 3], [0, 5, 10], [1, 1, 1])], true)).toEqual([
    { x: 1, a: 0 },
    { x: 2, a: 0.5 },
    { x: 3, a: 1 },
  ]);
});

test("buildOverlayData : 1 série + yStd + brut -> clé band [y-std, y+std]", () => {
  expect(buildOverlayData([S("a", [1, 2], [10, 20], [1, 2])], false)).toEqual([
    { x: 1, a: 10, a__band: [9, 11] },
    { x: 2, a: 20, a__band: [18, 22] },
  ]);
});

test("buildOverlayData : bande absente si >1 série", () => {
  expect(buildOverlayData([S("a", [1], [10], [1]), S("b", [1], [20], [1])], false)).toEqual([
    { x: 1, a: 10, b: 20 },
  ]);
});
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/lib/sweep.test.ts`
Expected: FAIL (`normalizeSeries`/`buildOverlayData` non exportés).

- [ ] **Step 3: Implémenter les helpers (ajout en fin de `lib/sweep.ts`)**

Ajouter à la fin de `frontend/src/lib/sweep.ts`, sans modifier `buildSweepData`/`SweepPoint` :

```ts
export interface OverlaySeries {
  id: string;        // ex. `${run_id}::${metric}` — dataKey unique
  label: string;     // ex. `${name} · ${metric}` — légende
  knob: string;
  x: number[];
  y: number[];
  yStd?: number[];
}

export interface OverlayPoint {
  x: number;
  [seriesKey: string]: number | [number, number] | undefined;
}

/** Min-max [0,1] par série. Si max == min -> tableau de 0 (série plate). Pur. */
export function normalizeSeries(y: number[]): number[] {
  if (y.length === 0) return [];
  const min = Math.min(...y);
  const max = Math.max(...y);
  if (max === min) return y.map(() => 0);
  return y.map((v) => (v - min) / (max - min));
}

/** Aligne les séries sur l'union triée de leurs X (niveaux pouvant différer entre runs ->
 *  valeur absente si la série n'a pas ce X). Bande `${id}__band` = [y-std, y+std] émise
 *  UNIQUEMENT si une seule série, mode brut, et yStd de même longueur que y. Pur. */
export function buildOverlayData(series: OverlaySeries[], normalize: boolean): OverlayPoint[] {
  const yEff = series.map((s) => (normalize ? normalizeSeries(s.y) : s.y));
  const xSet = new Set<number>();
  series.forEach((s) => s.x.forEach((xv) => xSet.add(xv)));
  const xs = [...xSet].sort((a, b) => a - b);

  const withBand =
    series.length === 1 &&
    !normalize &&
    Array.isArray(series[0].yStd) &&
    series[0].yStd!.length === series[0].y.length;

  return xs.map((xv) => {
    const point: OverlayPoint = { x: xv };
    series.forEach((s, si) => {
      const i = s.x.indexOf(xv);
      if (i !== -1) point[s.id] = yEff[si][i];
    });
    if (withBand) {
      const s = series[0];
      const i = s.x.indexOf(xv);
      if (i !== -1) point[`${s.id}__band`] = [s.y[i] - s.yStd![i], s.y[i] + s.yStd![i]];
    }
    return point;
  });
}
```

- [ ] **Step 4: Lancer les tests pour vérifier le succès**

Run : `cd frontend && npx vitest run src/lib/sweep.test.ts`
Expected: PASS (tests existants `buildSweepData` + 7 nouveaux).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/sweep.ts frontend/src/lib/sweep.test.ts
git commit -m "$(cat <<'EOF'
feat(sweep): helpers de superposition (normalizeSeries + buildOverlayData)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `SweepOverlayChart` — graphe multi-lignes recharts

**Files:**
- Create: `frontend/src/components/SweepOverlayChart.tsx`
- Test: `frontend/src/components/SweepOverlayChart.test.tsx`

**Interfaces:**
- Consumes: `buildOverlayData`, `OverlaySeries` de `../lib/sweep` ; `cssVar`, `vizColors` de `../theme`.
- Produces: `function SweepOverlayChart(props: { series: OverlaySeries[]; knob: string; normalize: boolean }): JSX.Element`.

- [ ] **Step 1: Écrire le test smoke qui échoue**

Créer `frontend/src/components/SweepOverlayChart.test.tsx` :

```tsx
import { render, cleanup } from "@testing-library/react";
import { afterEach, test, expect } from "vitest";
import { SweepOverlayChart } from "./SweepOverlayChart";
import type { OverlaySeries } from "../lib/sweep";

afterEach(() => cleanup());

const series: OverlaySeries[] = [
  { id: "r1::m", label: "run1 · m", knob: "k", x: [1, 2, 3], y: [1, 2, 3] },
  { id: "r2::m", label: "run2 · m", knob: "k", x: [1, 2, 3], y: [3, 2, 1] },
];

test("monte un conteneur recharts en superposition (2 séries)", () => {
  const { container } = render(<SweepOverlayChart series={series} knob="forage_payoff" normalize={false} />);
  expect(container.querySelector(".recharts-responsive-container")).toBeTruthy();
});

test("monte avec une seule série en mode normalisé", () => {
  const { container } = render(<SweepOverlayChart series={[series[0]]} knob="k" normalize={true} />);
  expect(container.querySelector(".recharts-responsive-container")).toBeTruthy();
});
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/components/SweepOverlayChart.test.tsx`
Expected: FAIL (`SweepOverlayChart` introuvable).

- [ ] **Step 3: Implémenter `SweepOverlayChart.tsx`**

Créer `frontend/src/components/SweepOverlayChart.tsx` :

```tsx
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from "recharts";
import { cssVar, vizColors } from "../theme";
import { buildOverlayData, type OverlaySeries } from "../lib/sweep";

interface SweepOverlayChartProps {
  series: OverlaySeries[];
  knob: string;
  normalize: boolean;
}

/** Superposition de séries (sweep × métrique) le long d'un knob.
 *  N lignes colorées ; bande ±std seulement si 1 série en mode brut. */
export function SweepOverlayChart({ series, knob, normalize }: SweepOverlayChartProps) {
  const viz = vizColors();
  const data = buildOverlayData(series, normalize);
  const bandKey = series.length === 1 ? `${series[0].id}__band` : null;
  const hasBand = bandKey !== null && data.some((p) => p[bandKey] !== undefined);

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
          label={{
            value: normalize ? "valeur normalisée [0,1]" : "valeur",
            angle: -90,
            position: "insideLeft",
            fill: cssVar("--color-text-dim"),
          }}
        />
        <RechartsTooltip
          contentStyle={{ backgroundColor: cssVar("--color-surface"), border: `1px solid ${cssVar("--color-border")}` }}
        />
        <Legend />
        {hasBand ? (
          <Area dataKey={bandKey!} stroke="none" fill={viz[0]} fillOpacity={0.15} name="±écart-type" isAnimationActive={false} />
        ) : null}
        {series.map((s, i) => (
          <Line
            key={s.id}
            type="monotone"
            dataKey={s.id}
            name={s.label}
            stroke={viz[i % viz.length]}
            strokeWidth={2.5}
            connectNulls
            dot={false}
            isAnimationActive={false}
          />
        ))}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run : `cd frontend && npx vitest run src/components/SweepOverlayChart.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/SweepOverlayChart.tsx frontend/src/components/SweepOverlayChart.test.tsx
git commit -m "$(cat <<'EOF'
feat(sweep): composant SweepOverlayChart (N lignes recharts, bande si 1 serie)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: rewire `SweepView` + retrait du mono-série mort

**Files:**
- Modify: `frontend/src/components/SweepView.tsx` (rewire complet)
- Modify: `frontend/src/components/SweepView.test.tsx` (réécriture)
- Modify: `frontend/src/lib/sweep.ts` (retrait `buildSweepData` + `SweepPoint`)
- Modify: `frontend/src/lib/sweep.test.ts` (retrait des tests `buildSweepData`)
- Modify: `frontend/src/styles.css` (ajout de styles minimaux pour les cases/fieldset)
- Delete: `frontend/src/components/SweepChart.tsx`
- Delete: `frontend/src/components/SweepChart.test.tsx`

**Interfaces:**
- Consumes: `SweepOverlayChart` (Task 2) ; `OverlaySeries` de `../lib/sweep` ; `SweepResult` de `../types` ; `apiFetch`, `queryKeys`, UI `Loading`/`ErrorState`/`Empty`/`Field`/`Panel`.
- Produces: `SweepView` (export nommé, inchangé) rendant la superposition.

- [ ] **Step 1: Réécrire le test de `SweepView`**

Remplacer tout le contenu de `frontend/src/components/SweepView.test.tsx` par :

```tsx
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { SweepView } from "./SweepView";

afterEach(() => cleanup());

const FIXTURE = [
  {
    run_id: "lewis_42",
    name: "lewis",
    knob: "forage_payoff",
    x: [0.1, 0.2, 0.3],
    series: { median_survival: [0.2, 0.5, 0.8], median_competence: [0.1, 0.3, 0.6] },
    y_std: { median_survival: [0.05, 0.05, 0.05] },
    seed: 42,
    commit: "abc",
  },
  {
    run_id: "lewis_43",
    name: "lewis2",
    knob: "forage_payoff",
    x: [0.1, 0.2, 0.3],
    series: { median_survival: [0.25, 0.55, 0.85] },
    seed: 43,
    commit: "def",
  },
];

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue(FIXTURE);
});

test("affiche le sélecteur de knob, la liste de séries et le graphe", async () => {
  const { container } = renderWithClient(<SweepView />);
  expect(await screen.findByLabelText(/Paramètre \(knob\)/)).toBeTruthy();
  expect(screen.getByText("lewis · median_survival")).toBeTruthy();
  expect(screen.getByText("lewis · median_competence")).toBeTruthy();
  expect(container.querySelector(".recharts-responsive-container")).toBeTruthy();
});

test("état vide quand aucun sweep", async () => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  renderWithClient(<SweepView />);
  expect(await screen.findByText(/Aucun sweep disponible/)).toBeTruthy();
});

test("le toggle de normalisation est présent", async () => {
  renderWithClient(<SweepView />);
  await screen.findByLabelText(/Paramètre \(knob\)/);
  expect(screen.getByText(/min-max/)).toBeTruthy();
});

test("cocher une 2e série l'ajoute à la superposition", async () => {
  renderWithClient(<SweepView />);
  await screen.findByLabelText(/Paramètre \(knob\)/);
  const second = screen.getByLabelText("lewis · median_competence") as HTMLInputElement;
  expect(second.checked).toBe(false);
  fireEvent.click(second);
  expect(second.checked).toBe(true);
});
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/components/SweepView.test.tsx`
Expected: FAIL (l'UI knob/séries n'existe pas encore).

- [ ] **Step 3: Réécrire `SweepView.tsx`**

Remplacer tout le contenu de `frontend/src/components/SweepView.tsx` par :

```tsx
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { SweepResult } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";
import { Field } from "./ui/Field";
import { Panel } from "./ui/Panel";
import { SweepOverlayChart } from "./SweepOverlayChart";
import type { OverlaySeries } from "../lib/sweep";

/** Onglet Sweeps v2 : superposer des séries (sweep × métrique) partageant un knob. */
export function SweepView() {
  const { data: sweeps = [], isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.sweeps,
    queryFn: () => apiFetch<SweepResult[]>("/api/sweeps"),
    staleTime: 30_000,
  });

  const knobs = [...new Set(sweeps.map((s) => s.knob))].sort();
  const [selectedKnob, setSelectedKnob] = useState<string>("");
  const knob = knobs.includes(selectedKnob) ? selectedKnob : (knobs[0] ?? "");

  // Séries disponibles pour le knob courant : (sweep × métrique).
  const available: OverlaySeries[] = sweeps
    .filter((s) => s.knob === knob)
    .flatMap((s) =>
      Object.keys(s.series).map((m) => ({
        id: `${s.run_id}::${m}`,
        label: `${s.name} · ${m}`,
        knob: s.knob,
        x: s.x,
        y: s.series[m],
        yStd: s.y_std?.[m],
      })),
    );
  const availableIds = available.map((s) => s.id);

  // null = sélection jamais touchée -> défaut 1ère série (= comportement v1).
  const [selectedIds, setSelectedIds] = useState<string[] | null>(null);
  const shownIds =
    selectedIds === null ? availableIds.slice(0, 1) : selectedIds.filter((id) => availableIds.includes(id));
  const shownSeries = available.filter((s) => shownIds.includes(s.id));

  const [normalize, setNormalize] = useState(false);

  function toggleId(id: string) {
    setSelectedIds((prev) => {
      const base = prev === null ? availableIds.slice(0, 1) : prev.filter((x) => availableIds.includes(x));
      return base.includes(id) ? base.filter((x) => x !== id) : [...base, id];
    });
  }

  if (isLoading) return <Loading label="Chargement des sweeps…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!sweeps.length) {
    return (
      <Empty message="Aucun sweep disponible. Lance un balayage de paramètre (ex. lewis_survival_sweep) côté backend." />
    );
  }

  return (
    <div className="sweep-view">
      <h2>Paysage de paramètres (sweeps)</h2>
      <div className="row mb-4">
        <Field label="Paramètre (knob)">
          <select
            value={knob}
            onChange={(e) => {
              setSelectedKnob(e.target.value);
              setSelectedIds(null);
            }}
          >
            {knobs.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Normalisation">
          <label className="checkbox-inline">
            <input type="checkbox" checked={normalize} onChange={(e) => setNormalize(e.target.checked)} />
            min-max [0,1]
          </label>
        </Field>
      </div>
      <fieldset className="sweep-series mb-4">
        <legend>Séries à superposer</legend>
        {available.map((s) => (
          <label key={s.id} className="checkbox-inline">
            <input type="checkbox" checked={shownIds.includes(s.id)} onChange={() => toggleId(s.id)} />
            {s.label}
          </label>
        ))}
      </fieldset>
      <p className="text-dim">
        paramètre <strong>{knob}</strong> · {shownSeries.length} série{shownSeries.length > 1 ? "s" : ""} superposée
        {shownSeries.length > 1 ? "s" : ""}
      </p>
      {shownSeries.length === 0 ? (
        <Empty message="Sélectionne au moins une série à superposer." />
      ) : (
        <Panel>
          <SweepOverlayChart series={shownSeries} knob={knob} normalize={normalize} />
        </Panel>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Ajouter les styles minimaux**

Ajouter à la fin de `frontend/src/styles.css` :

```css
.sweep-series {
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 8px 12px;
}
.sweep-series legend {
  padding: 0 6px;
  color: var(--color-text-dim);
  font-size: 0.85rem;
}
.checkbox-inline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-right: 16px;
}
```

- [ ] **Step 5: Retirer le mono-série mort**

Supprimer les fichiers `frontend/src/components/SweepChart.tsx` et `frontend/src/components/SweepChart.test.tsx`.

Dans `frontend/src/lib/sweep.ts`, retirer l'interface `SweepPoint` et la fonction `buildSweepData` (en tête de fichier) — ne garder que les helpers overlay de la Task 1.

Dans `frontend/src/lib/sweep.test.ts`, retirer les 3 tests `buildSweepData` (« sans yStd… », « avec yStd… », « yStd de longueur incohérente… ») et l'import `buildSweepData` — ne garder que les tests overlay.

```bash
git rm frontend/src/components/SweepChart.tsx frontend/src/components/SweepChart.test.tsx
```

- [ ] **Step 6: Vérifier le typage et toute la suite**

Run : `cd frontend && npx tsc --noEmit`
Expected: aucune erreur (notamment aucun import résiduel de `SweepChart`/`buildSweepData`).

Run : `cd frontend && npx vitest run`
Expected: PASS (toute la suite ; `SweepChart.test.tsx` disparu, `SweepView`/`SweepOverlayChart`/`sweep` verts).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/SweepView.tsx frontend/src/components/SweepView.test.tsx frontend/src/lib/sweep.ts frontend/src/lib/sweep.test.ts frontend/src/styles.css
git commit -m "$(cat <<'EOF'
feat(sweep): rewire SweepView en superposition multi-serie + retrait du mono-serie

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Notes d'exécution

- Tâches 1→3 dans l'ordre (Task 3 dépend des helpers de Task 1 et du composant de Task 2).
- Le retrait de `SweepChart`/`buildSweepData` n'a lieu qu'en Task 3 : Tâches 1 et 2 laissent la suite verte (les deux coexistent un temps).
- Avant de finir : vérifier qu'aucun import résiduel de `SweepChart` ou `buildSweepData` ne subsiste (`tsc --noEmit` le garantit). PR vers `main` une fois la suite complète verte.
