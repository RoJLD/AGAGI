# Entonnoir de forage (I5) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un onglet « Forage » qui visualise l'entonnoir d'acquisition (atteinte → capture-si-atteint → capture globale) par niveau de métab, à partir des runs persistés par `main_forage`.

**Architecture:** Helper pur `lib/forage.ts` (niveau → 3 étages) → composant recharts `ForageFunnelChart` → vue `ForageFunnelView` (sélecteur run + verdict + un chart par niveau). Données via un nouvel endpoint `GET /api/runs/forage-funnels` (lit `data.table`, patch-and-handoff vers `feat/d1-prod-pairing`).

**Tech Stack:** React 18 + TypeScript strict + @tanstack/react-query v5 + recharts + Vitest + Testing Library (frontend) ; FastAPI + Pydantic + pytest (backend).

## Global Constraints

- **Frontière session parallèle** : tâches 1-4 = frontend (`frontend/src/**` + `docs/**`) sur `feat/frontend-forage-funnel` → PR vers `main`. Tâche 5 = backend → branche depuis `feat/d1-prod-pairing`, **PR dans leur branche** (jamais de push direct).
- **Langue** : libellés/commentaires en français.
- **Pas d'emoji** dans le code ni les commits.
- **TypeScript** : zéro `any`, types explicites.
- **Commits** : chaque commit se termine par le trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **3 étages** par niveau : atteinte (`p_reach`), capture-si-atteint (`p_cap`), capture globale (= `p_reach × p_cap`). `value` ∈ [0,1], `pct = value × 100`. Ordre fixe (cascade), pas de tri.
- **Clés de `table`** = `str(metab_level)` ; les niveaux suivent l'ordre de `metab_levels`.
- **Tests frontend** depuis `frontend/` : `npx vitest run <chemin>`. **Tests backend** depuis la racine : `PYTHONPATH=. python -m pytest <chemin>::<test> -v`. Un seul appel bash composé (`cd ... && ...`).

---

### Task 1: types + queryKeys + `lib/forage.ts`

**Files:**
- Modify: `frontend/src/types.ts` (ajout `ForageLevel`, `ForageFunnel`)
- Modify: `frontend/src/api/queryKeys.ts` (ajout `runs.forageFunnels`)
- Create: `frontend/src/lib/forage.ts`
- Test: `frontend/src/lib/forage.test.ts`

**Interfaces:**
- Produces:
  - `interface ForageLevel { metab; p_reach; p_cap; income_t; drain_t; mean_captures; mean_contacts; mean_min_dist; n_agents }` (tous `number`)
  - `interface ForageFunnel { run_id: string; name: string; seed: number; commit?: string | null; verdict: string; levels: ForageLevel[] }`
  - `interface ForageBar { name: string; value: number; pct: number }`
  - `function buildFunnelStages(level: ForageLevel): ForageBar[]`
  - `queryKeys.runs.forageFunnels => ["runs","forage-funnels"]`

- [ ] **Step 1: Ajouter les types**

Dans `frontend/src/types.ts`, après l'interface `Decomposition` (fin de fichier) :

```ts
/** Un niveau de métab d'un entonnoir de forage (sortie de main_forage, EDR 105). */
export interface ForageLevel {
  metab: number;
  p_reach: number;
  p_cap: number;
  income_t: number;
  drain_t: number;
  mean_captures: number;
  mean_contacts: number;
  mean_min_dist: number;
  n_agents: number;
}

/** Un run d'entonnoir de forage persisté (lewis_forage_funnel_<seed>.json). */
export interface ForageFunnel {
  run_id: string;
  name: string;
  seed: number;
  commit?: string | null;
  verdict: string;
  levels: ForageLevel[];
}
```

- [ ] **Step 2: Ajouter la clé de query**

Dans `frontend/src/api/queryKeys.ts`, dans l'objet `runs` (après la ligne `decompositions: ...`) :

```ts
    forageFunnels: ["runs", "forage-funnels"] as const,
```

- [ ] **Step 3: Écrire les tests qui échouent**

Créer `frontend/src/lib/forage.test.ts` :

```ts
import { test, expect } from "vitest";
import { buildFunnelStages } from "./forage";
import type { ForageLevel } from "../types";

const L: ForageLevel = {
  metab: 0, p_reach: 0.18, p_cap: 1, income_t: 0.5, drain_t: 0.2,
  mean_captures: 1.2, mean_contacts: 6.5, mean_min_dist: 3.1, n_agents: 40,
};

test("buildFunnelStages : 3 étages dans l'ordre cascade", () => {
  const bars = buildFunnelStages(L);
  expect(bars.map((b) => b.name)).toEqual([
    "atteinte (p_reach)",
    "capture si atteint (p_cap)",
    "capture globale",
  ]);
  expect(bars[0].value).toBeCloseTo(0.18, 10);
  expect(bars[1].value).toBe(1);
});

test("buildFunnelStages : capture globale = p_reach × p_cap ; pct = value × 100", () => {
  const bars = buildFunnelStages(L);
  expect(bars[2].value).toBeCloseTo(0.18, 10);
  expect(bars[0].pct).toBeCloseTo(18, 10);
});
```

- [ ] **Step 4: Lancer les tests pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/lib/forage.test.ts`
Expected: FAIL (`forage.ts` introuvable).

- [ ] **Step 5: Implémenter `lib/forage.ts`**

Créer `frontend/src/lib/forage.ts` :

```ts
import type { ForageLevel } from "../types";

export interface ForageBar {
  name: string;
  value: number;
  pct: number;
}

/** 3 étages d'acquisition d'un niveau : atteinte (p_reach), capture-si-atteint (p_cap),
 *  capture globale (= p_reach × p_cap). `value` dans [0,1], `pct` = value × 100. Ordre fixe (cascade). */
export function buildFunnelStages(level: ForageLevel): ForageBar[] {
  const global = level.p_reach * level.p_cap;
  return [
    { name: "atteinte (p_reach)", value: level.p_reach, pct: level.p_reach * 100 },
    { name: "capture si atteint (p_cap)", value: level.p_cap, pct: level.p_cap * 100 },
    { name: "capture globale", value: global, pct: global * 100 },
  ];
}
```

- [ ] **Step 6: Lancer les tests pour vérifier le succès**

Run : `cd frontend && npx vitest run src/lib/forage.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/queryKeys.ts frontend/src/lib/forage.ts frontend/src/lib/forage.test.ts
git commit -m "$(cat <<'EOF'
feat(forage): types ForageFunnel/ForageLevel + helper lib/forage (3 etages)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `ForageFunnelChart` — barres recharts

**Files:**
- Create: `frontend/src/components/ForageFunnelChart.tsx`
- Test: `frontend/src/components/ForageFunnelChart.test.tsx`

**Interfaces:**
- Consumes: `ForageBar` de `../lib/forage` ; `cssVar`, `vizColors` de `../theme`.
- Produces: `function ForageFunnelChart(props: { bars: ForageBar[]; title: string }): JSX.Element`.

- [ ] **Step 1: Écrire le test smoke qui échoue**

Créer `frontend/src/components/ForageFunnelChart.test.tsx` :

```tsx
import { render, cleanup } from "@testing-library/react";
import { afterEach, test, expect } from "vitest";
import { ForageFunnelChart } from "./ForageFunnelChart";
import type { ForageBar } from "../lib/forage";

afterEach(() => cleanup());

const bars: ForageBar[] = [
  { name: "atteinte (p_reach)", value: 0.18, pct: 18 },
  { name: "capture si atteint (p_cap)", value: 1, pct: 100 },
  { name: "capture globale", value: 0.18, pct: 18 },
];

test("monte un conteneur recharts avec les barres", () => {
  const { container } = render(<ForageFunnelChart bars={bars} title="métab 0" />);
  expect(container.querySelector(".recharts-responsive-container")).toBeTruthy();
});
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/components/ForageFunnelChart.test.tsx`
Expected: FAIL (`ForageFunnelChart` introuvable).

- [ ] **Step 3: Implémenter `ForageFunnelChart.tsx`**

Créer `frontend/src/components/ForageFunnelChart.tsx` :

```tsx
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  LabelList,
} from "recharts";
import { cssVar, vizColors } from "../theme";
import type { ForageBar } from "../lib/forage";

interface ForageFunnelChartProps {
  bars: ForageBar[];
  title: string;
}

/** Barres horizontales d'un entonnoir de forage (probabilité 0-1 + % par étage). */
export function ForageFunnelChart({ bars, title }: ForageFunnelChartProps) {
  const viz = vizColors();
  return (
    <div className="forage-chart">
      <h4 style={{ margin: "0 0 var(--space-2)" }}>{title}</h4>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={bars} layout="vertical" margin={{ top: 8, right: 56, bottom: 20, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={cssVar("--color-border")} horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 1]}
            stroke={cssVar("--color-text-dim")}
            fontSize={11}
            label={{ value: "probabilité", position: "insideBottom", offset: -8, fill: cssVar("--color-text-dim") }}
          />
          <YAxis type="category" dataKey="name" width={140} stroke={cssVar("--color-text-dim")} fontSize={11} />
          <RechartsTooltip
            contentStyle={{ backgroundColor: cssVar("--color-surface"), border: `1px solid ${cssVar("--color-border")}` }}
          />
          <Bar dataKey="value" name="probabilité" isAnimationActive={false}>
            {bars.map((b, i) => (
              <Cell key={b.name} fill={viz[i % viz.length]} />
            ))}
            <LabelList dataKey="pct" position="right" formatter={(v) => `${Number(v).toFixed(1)}%`} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run : `cd frontend && npx vitest run src/components/ForageFunnelChart.test.tsx`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ForageFunnelChart.tsx frontend/src/components/ForageFunnelChart.test.tsx
git commit -m "$(cat <<'EOF'
feat(forage): composant ForageFunnelChart (barres recharts probabilite + pourcentage)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `ForageFunnelView` — sélecteur, verdict, un chart par niveau

**Files:**
- Create: `frontend/src/components/ForageFunnelView.tsx`
- Test: `frontend/src/components/ForageFunnelView.test.tsx`

**Interfaces:**
- Consumes: `apiFetch` ; `queryKeys.runs.forageFunnels` ; `buildFunnelStages` de `../lib/forage` ; `ForageFunnelChart` ; `ForageFunnel` de `../types` ; UI `Loading`/`ErrorState`/`Empty`/`Field`/`Panel`.
- Produces: `function ForageFunnelView(): JSX.Element` (export nommé).

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `frontend/src/components/ForageFunnelView.test.tsx` :

```tsx
import { render, screen, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { ForageFunnelView } from "./ForageFunnelView";

afterEach(() => cleanup());

const FIXTURE = [
  {
    run_id: "lewis_forage_funnel_7",
    name: "lewis_forage_funnel",
    seed: 7,
    commit: "abc",
    verdict: "APPROCHE casse (p_reach 0.18)",
    levels: [
      { metab: 0, p_reach: 0.18, p_cap: 1, income_t: 0.5, drain_t: 0.2, mean_captures: 1.2, mean_contacts: 6.5, mean_min_dist: 3.1, n_agents: 40 },
      { metab: 0.25, p_reach: 0.12, p_cap: 1, income_t: 0.3, drain_t: 0.4, mean_captures: 0.8, mean_contacts: 5.0, mean_min_dist: 3.6, n_agents: 38 },
    ],
  },
];

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue(FIXTURE));

test("affiche le sélecteur, le verdict et un chart par niveau", async () => {
  const { container } = renderWithClient(<ForageFunnelView />);
  expect(await screen.findByLabelText(/Run d'entonnoir/)).toBeTruthy();
  expect(screen.getByText(/APPROCHE casse/)).toBeTruthy();
  expect(container.querySelectorAll(".recharts-responsive-container").length).toBe(2);
});

test("état vide quand aucun entonnoir", async () => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  renderWithClient(<ForageFunnelView />);
  expect(await screen.findByText(/Aucun entonnoir de forage/)).toBeTruthy();
});
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/components/ForageFunnelView.test.tsx`
Expected: FAIL (`ForageFunnelView` introuvable).

- [ ] **Step 3: Implémenter `ForageFunnelView.tsx`**

Créer `frontend/src/components/ForageFunnelView.tsx` :

```tsx
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ForageFunnel } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { buildFunnelStages } from "../lib/forage";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";
import { Field } from "./ui/Field";
import { Panel } from "./ui/Panel";
import { ForageFunnelChart } from "./ForageFunnelChart";

/** Vue forage : entonnoir d'acquisition (atteinte/capture/globale) par niveau de métab (EDR 105). */
export function ForageFunnelView() {
  const { data: funnels = [], isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.runs.forageFunnels,
    queryFn: () => apiFetch<ForageFunnel[]>("/api/runs/forage-funnels"),
    staleTime: 30_000,
  });

  const [selId, setSelId] = useState<string>("");
  const current = funnels.find((f) => f.run_id === selId) ?? funnels[0];

  if (isLoading) return <Loading label="Chargement des entonnoirs…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!funnels.length || !current) {
    return (
      <Empty message="Aucun entonnoir de forage. Lance python tools/lewis_survival_sweep.py (main_forage) côté backend." />
    );
  }

  return (
    <div className="forage-view">
      <h2>Entonnoir de forage (acquisition)</h2>
      <div className="row mb-4">
        <Field label="Run d'entonnoir">
          <select value={current.run_id} onChange={(e) => setSelId(e.target.value)}>
            {funnels.map((f) => (
              <option key={f.run_id} value={f.run_id}>
                {f.name} — seed {f.seed}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <div className="forage-verdict mb-4">
        <p>
          <strong>Verdict :</strong> {current.verdict || "—"}
        </p>
      </div>
      {current.levels.map((lv) => (
        <Panel key={lv.metab} className="mt-4">
          <ForageFunnelChart bars={buildFunnelStages(lv)} title={`métab ${lv.metab}`} />
          <p className="text-dim">
            revenu <strong>{lv.income_t.toFixed(3)}</strong>/tick · drain <strong>{lv.drain_t.toFixed(3)}</strong>/tick ·
            contacts {lv.mean_contacts.toFixed(2)} · dist. min {lv.mean_min_dist.toFixed(2)} · {lv.n_agents} agents
          </p>
        </Panel>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Lancer les tests pour vérifier le succès**

Run : `cd frontend && npx vitest run src/components/ForageFunnelView.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ForageFunnelView.tsx frontend/src/components/ForageFunnelView.test.tsx
git commit -m "$(cat <<'EOF'
feat(forage): vue ForageFunnelView (selecteur, verdict, un chart par niveau, etats)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Intégration onglet (tabs + App lazy)

**Files:**
- Modify: `frontend/src/tabs.ts`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `ForageFunnelView` de `./components/ForageFunnelView` ; `Crosshair` de `lucide-react`.
- Produces: onglet `"forage"` navigable.

- [ ] **Step 1: Ajouter la clé `forage` à `TAB_KEYS`**

Dans `frontend/src/tabs.ts`, dans `TAB_KEYS`, ajouter `"forage"` juste après `"energie"` :

```ts
  "energie",
  "forage",
```

- [ ] **Step 2: Importer l'icône et ajouter l'entrée famille Analyse**

Dans `frontend/src/tabs.ts`, ajouter `Crosshair` à l'import lucide-react (ordre alpha, après `Compass`) :

```ts
  Compass,
  Crosshair,
  Database,
```

Puis, dans la famille **Analyse** (après l'entrée `energie`), ajouter :

```ts
      { key: "energie", label: "Énergie", icon: Zap },
      { key: "forage", label: "Forage", icon: Crosshair },
```

- [ ] **Step 3: Câbler le lazy import et la branche dans `App.tsx`**

Dans `frontend/src/App.tsx`, ajouter le lazy import après la ligne `EnergyView` :

```ts
const ForageFunnelView = lazy(() => import("./components/ForageFunnelView").then((m) => ({ default: m.ForageFunnelView })));
```

Puis ajouter la branche de rendu juste après `{tab === "energie" && <EnergyView />}` :

```tsx
          {tab === "forage" && <ForageFunnelView />}
```

- [ ] **Step 4: Vérifier le typage et toute la suite**

Run : `cd frontend && npx tsc --noEmit`
Expected: aucune erreur.

Run : `cd frontend && npx vitest run`
Expected: PASS (toute la suite, incluant forage).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/tabs.ts frontend/src/App.tsx
git commit -m "$(cat <<'EOF'
feat(forage): integrer l'onglet Forage (famille Analyse) + lazy-load

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Backend — endpoint `/api/runs/forage-funnels` (patch-and-handoff vers d1)

> **Branche dédiée** : depuis `origin/feat/d1-prod-pairing`, créer `feat/forage-funnels-endpoint` (worktree séparé) ; PR **dans** `feat/d1-prod-pairing`. Indépendante des tâches 1-4.

**Files:**
- Modify: `backend/app/schemas.py` (`ForageLevel`, `ForageFunnel`)
- Modify: `backend/app/services/runs_service.py` (`list_forage_funnels`)
- Modify: `backend/app/routes/runs.py` (route GET)
- Test: `tests/test_backend.py` (racine du dépôt)
- Modify (régén) : `frontend/openapi.json`, `frontend/src/api/schema.ts`

**Interfaces:**
- Consumes: `runs_service._scan()` (fournit `_run_id`, `name`, `seed`, `commit`, `data`).
- Produces: `GET /api/runs/forage-funnels` → `list[ForageFunnel]`.

- [ ] **Step 1: Écrire le test backend qui échoue**

Dans `tests/test_backend.py`, ajouter (après `test_list_decompositions_extracts_phases`) :

```python
def test_list_forage_funnels_extracts_levels(tmp_path, monkeypatch) -> None:
    """Un run d'entonnoir (data.table par niveau) -> 1 ForageFunnel ; un run scalaire -> ignoré."""
    import backend.app.services.runs_service as rs_mod
    monkeypatch.setattr(rs_mod, "RESULTS_DIR", tmp_path)
    agg0 = {"p_reach": 0.18, "p_cap": 1.0, "income_t": 0.5, "drain_t": 0.2,
            "mean_captures": 1.2, "mean_contacts": 6.5, "mean_min_dist": 3.1, "n_agents": 40}
    agg25 = {"p_reach": 0.12, "p_cap": 1.0, "income_t": 0.3, "drain_t": 0.4,
             "mean_captures": 0.8, "mean_contacts": 5.0, "mean_min_dist": 3.6, "n_agents": 38}
    (tmp_path / "lewis_forage_funnel_7.json").write_text(json.dumps({
        "name": "lewis_forage_funnel", "seed": 7, "commit": "abc1234",
        "data": {"knob": "base_metab", "metab_levels": [0.0, 0.25], "verdict": "APPROCHE casse",
                 "R": 4, "n_eval": 8, "table": {"0.0": agg0, "0.25": agg25}},
    }), encoding="utf-8")
    (tmp_path / "AND_0.json").write_text(json.dumps({
        "name": "AND", "seed": 0, "data": {"fitness": 0.9},
    }), encoding="utf-8")
    funnels = rs_mod.runs_service.list_forage_funnels()
    assert len(funnels) == 1
    f = funnels[0]
    assert f["run_id"] == "lewis_forage_funnel_7"
    assert [lv["metab"] for lv in f["levels"]] == [0.0, 0.25]
    assert f["levels"][0]["p_reach"] == 0.18
    assert f["verdict"] == "APPROCHE casse"

    resp = client.get("/api/runs/forage-funnels")
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "lewis_forage_funnel"
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run : `cd "<worktree>" && PYTHONPATH=. python -m pytest tests/test_backend.py::test_list_forage_funnels_extracts_levels -v`
Expected: FAIL (`list_forage_funnels` n'existe pas / route 404).

- [ ] **Step 3: Ajouter les modèles Pydantic**

Dans `backend/app/schemas.py`, à côté de `Decomposition` :

```python
class ForageLevel(BaseModel):
    metab: float
    p_reach: float
    p_cap: float
    income_t: float
    drain_t: float
    mean_captures: float
    mean_contacts: float
    mean_min_dist: float
    n_agents: float


class ForageFunnel(BaseModel):
    run_id: str
    name: str
    seed: int
    commit: str | None = None
    verdict: str
    levels: list[ForageLevel]
```

- [ ] **Step 4: Implémenter la méthode de service**

Dans `backend/app/services/runs_service.py`, ajouter cette méthode dans la classe (après `list_decompositions`) :

```python
    def list_forage_funnels(self) -> list[dict]:
        """Runs d'entonnoir de forage (data.table par niveau de metab) — vue Forage."""
        out: list[dict] = []
        for r in self._scan():
            data = r["data"]
            table = data.get("table")
            levels_raw = data.get("metab_levels")
            if not isinstance(table, dict) or not isinstance(levels_raw, list):
                continue
            levels: list[dict] = []
            for lv in levels_raw:
                agg = table.get(str(lv))
                if not isinstance(agg, dict) or "p_reach" not in agg:
                    continue
                levels.append({
                    "metab": float(lv),
                    "p_reach": agg["p_reach"], "p_cap": agg["p_cap"],
                    "income_t": agg["income_t"], "drain_t": agg["drain_t"],
                    "mean_captures": agg["mean_captures"], "mean_contacts": agg["mean_contacts"],
                    "mean_min_dist": agg["mean_min_dist"], "n_agents": agg["n_agents"],
                })
            if not levels:
                continue
            out.append({
                "run_id": r["_run_id"], "name": r["name"], "seed": r["seed"],
                "commit": r.get("commit"), "verdict": data.get("verdict", ""), "levels": levels,
            })
        return sorted(out, key=lambda d: d["run_id"])
```

- [ ] **Step 5: Ajouter la route**

Dans `backend/app/routes/runs.py`, ajouter `ForageFunnel` à l'import depuis `..schemas`, puis ajouter la route **avant** `@router.get("/runs/{run_id}")` :

```python
@router.get("/runs/forage-funnels", response_model=list[ForageFunnel])
def list_forage_funnels() -> list[dict]:
    """Entonnoirs de forage (acquisition : approche/capture/revenu par niveau de métab) pour la vue Forage."""
    return runs_service.list_forage_funnels()
```

- [ ] **Step 6: Lancer le test pour vérifier le succès**

Run : `cd "<worktree>" && PYTHONPATH=. python -m pytest tests/test_backend.py::test_list_forage_funnels_extracts_levels -v`
Expected: PASS.

- [ ] **Step 7: Régénérer le schéma OpenAPI + types TS (drift gate)**

Run :
```bash
cd "<worktree>" && PYTHONPATH=. python tools/dump_openapi.py && cd frontend && npm run gen:api
```
Expected: `frontend/openapi.json` et `frontend/src/api/schema.ts` contiennent l'opération
`list_forage_funnels_api_runs_forage_funnels_get`. `git diff --stat` non vide sur ces 2 fichiers.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas.py backend/app/services/runs_service.py backend/app/routes/runs.py tests/test_backend.py frontend/openapi.json frontend/src/api/schema.ts
git commit -m "$(cat <<'EOF'
feat(runs): endpoint GET /api/runs/forage-funnels (entonnoir d'acquisition pour la vue Forage)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Notes d'exécution

- **Tâches 1→4** sur `feat/frontend-forage-funnel`, dans l'ordre (T2 dépend de `ForageBar`/T1 ; T3 de T1+T2 ; T4 de T3). PR vers `main`.
- **Tâche 5** indépendante, worktree depuis `origin/feat/d1-prod-pairing`, PR dans leur branche. Jusqu'à propagation d→main, l'onglet Forage dégrade en Empty/Error proprement.
- Avant de finir la branche frontend : vérifier qu'aucun fichier backend/test.setup parasite (LF/CRLF) n'entre dans les commits.
