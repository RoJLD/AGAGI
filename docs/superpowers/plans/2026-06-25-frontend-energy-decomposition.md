# Décomposition énergétique (I1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un onglet « Énergie » qui visualise le budget énergétique par tick/agent (4 phases + sous-décomposition biologie) à partir des runs de décomposition persistés par `main_decompose`.

**Architecture:** Helpers purs `lib/energy.ts` (phases/bio → barres + %) → composant recharts `EnergyChart` → vue `EnergyView` (sélecteur de run décompo + verdicts + 2 charts). Données via un nouvel endpoint `GET /api/runs/decompositions` (lit les fichiers `data.phases`, patch-and-handoff vers `feat/d1-prod-pairing`).

**Tech Stack:** React 18 + TypeScript strict + @tanstack/react-query v5 + recharts + Vitest + Testing Library (frontend) ; FastAPI + Pydantic + pytest (backend).

## Global Constraints

- **Frontière session parallèle** : tâches 1-4 = frontend (`frontend/src/**` + `docs/**`) sur `feat/frontend-energy-decomposition` → PR vers `main`. Tâche 5 = backend → branche depuis `feat/d1-prod-pairing`, **PR dans leur branche** (jamais de push direct).
- **Langue** : libellés/commentaires en français.
- **Pas d'emoji** dans le code ni les commits.
- **TypeScript** : zéro `any`, types explicites.
- **Commits** : chaque commit se termine par le trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **`phases` est un dict plat** : `brain, action, biologie, mouvement, net, n_agents, bio_metab, bio_terrain, bio_carry, bio_autres`.
- **pct** : phases = `100*value/net` ; bio = `100*value/(somme des 4 bio_*)` ; **dénominateur 0 → pct 0** (pas de division par zéro). Tri décroissant par valeur.
- **Tests frontend** depuis `frontend/` : `npx vitest run <chemin>`. **Tests backend** depuis la racine : `PYTHONPATH=. python -m pytest <chemin>::<test> -v`. Un seul appel bash composé (`cd ... && ...`).

---

### Task 1: types + queryKeys + `lib/energy.ts`

**Files:**
- Modify: `frontend/src/types.ts` (ajout `EnergyPhases`, `Decomposition`)
- Modify: `frontend/src/api/queryKeys.ts` (ajout `runs.decompositions`)
- Create: `frontend/src/lib/energy.ts`
- Test: `frontend/src/lib/energy.test.ts`

**Interfaces:**
- Produces:
  - `interface EnergyPhases { brain; action; biologie; mouvement; net; n_agents; bio_metab; bio_terrain; bio_carry; bio_autres }` (tous `number`)
  - `interface Decomposition { run_id: string; name: string; seed: number; commit?: string | null; phases: EnergyPhases; verdict: string; bio_verdict: string }`
  - `interface EnergyBar { name: string; value: number; pct: number }`
  - `function buildPhaseBreakdown(phases: EnergyPhases): EnergyBar[]`
  - `function buildBioBreakdown(phases: EnergyPhases): EnergyBar[]`
  - `queryKeys.runs.decompositions => ["runs","decompositions"]`

- [ ] **Step 1: Ajouter les types**

Dans `frontend/src/types.ts`, après l'interface `SweepResult` (fin de fichier) :

```ts
/** Budget énergétique décomposé (par tick/agent) — sortie de main_decompose (EDR 099/100). */
export interface EnergyPhases {
  brain: number;
  action: number;
  biologie: number;
  mouvement: number;
  net: number;
  n_agents: number;
  bio_metab: number;
  bio_terrain: number;
  bio_carry: number;
  bio_autres: number;
}

/** Un run de décomposition énergétique persisté (lewis_drain_decompose_<seed>.json). */
export interface Decomposition {
  run_id: string;
  name: string;
  seed: number;
  commit?: string | null;
  phases: EnergyPhases;
  verdict: string;
  bio_verdict: string;
}
```

- [ ] **Step 2: Ajouter la clé de query**

Dans `frontend/src/api/queryKeys.ts`, dans l'objet `runs` (après la ligne `distributions: ...`) :

```ts
    decompositions: ["runs", "decompositions"] as const,
```

- [ ] **Step 3: Écrire les tests qui échouent**

Créer `frontend/src/lib/energy.test.ts` :

```ts
import { test, expect } from "vitest";
import { buildPhaseBreakdown, buildBioBreakdown } from "./energy";
import type { EnergyPhases } from "../types";

const P: EnergyPhases = {
  brain: 1, action: 2, biologie: 9, mouvement: 0, net: 12, n_agents: 40,
  bio_metab: 13.47, bio_terrain: 0.27, bio_carry: 0.13, bio_autres: 0.13,
};

test("buildPhaseBreakdown : pct du net, tri décroissant", () => {
  const bars = buildPhaseBreakdown(P);
  expect(bars.map((b) => b.name)).toEqual(["biologie", "action", "brain", "mouvement"]);
  expect(bars[0]).toEqual({ name: "biologie", value: 9, pct: 75 });
});

test("buildBioBreakdown : pct du drain bio, métab domine", () => {
  const bars = buildBioBreakdown(P);
  expect(bars[0].name).toBe("métab");
  // bioNet = 13.47 + 0.27 + 0.13 + 0.13 = 14
  expect(bars[0].pct).toBeCloseTo((100 * 13.47) / 14, 6);
});

test("net == 0 -> pct 0 (pas de division par zéro)", () => {
  const z: EnergyPhases = { ...P, net: 0 };
  expect(buildPhaseBreakdown(z).every((b) => b.pct === 0)).toBe(true);
});

test("drain bio nul -> pct 0", () => {
  const z: EnergyPhases = { ...P, bio_metab: 0, bio_terrain: 0, bio_carry: 0, bio_autres: 0 };
  expect(buildBioBreakdown(z).every((b) => b.pct === 0)).toBe(true);
});
```

- [ ] **Step 4: Lancer les tests pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/lib/energy.test.ts`
Expected: FAIL (`energy.ts` introuvable).

- [ ] **Step 5: Implémenter `lib/energy.ts`**

Créer `frontend/src/lib/energy.ts` :

```ts
import type { EnergyPhases } from "../types";

export interface EnergyBar {
  name: string;
  value: number;
  pct: number;
}

const PHASES: { key: keyof EnergyPhases; label: string }[] = [
  { key: "brain", label: "cerveau" },
  { key: "action", label: "action" },
  { key: "biologie", label: "biologie" },
  { key: "mouvement", label: "mouvement" },
];

const BIO: { key: keyof EnergyPhases; label: string }[] = [
  { key: "bio_metab", label: "métab" },
  { key: "bio_terrain", label: "terrain" },
  { key: "bio_carry", label: "port" },
  { key: "bio_autres", label: "autres" },
];

function toBars(
  phases: EnergyPhases,
  defs: { key: keyof EnergyPhases; label: string }[],
  total: number,
): EnergyBar[] {
  return defs
    .map((d) => {
      const value = phases[d.key];
      return { name: d.label, value, pct: total ? (100 * value) / total : 0 };
    })
    .sort((a, b) => b.value - a.value);
}

/** 4 phases en part du net (tri décroissant). Si net == 0, pct = 0. */
export function buildPhaseBreakdown(phases: EnergyPhases): EnergyBar[] {
  return toBars(phases, PHASES, phases.net);
}

/** 4 composantes biologie en part du drain bio (somme des 4 ; tri décroissant). Si somme == 0, pct = 0. */
export function buildBioBreakdown(phases: EnergyPhases): EnergyBar[] {
  const bioNet = phases.bio_metab + phases.bio_terrain + phases.bio_carry + phases.bio_autres;
  return toBars(phases, BIO, bioNet);
}
```

- [ ] **Step 6: Lancer les tests pour vérifier le succès**

Run : `cd frontend && npx vitest run src/lib/energy.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/queryKeys.ts frontend/src/lib/energy.ts frontend/src/lib/energy.test.ts
git commit -m "$(cat <<'EOF'
feat(energie): types Decomposition/EnergyPhases + helpers lib/energy (phases + bio)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `EnergyChart` — barres recharts

**Files:**
- Create: `frontend/src/components/EnergyChart.tsx`
- Test: `frontend/src/components/EnergyChart.test.tsx`

**Interfaces:**
- Consumes: `EnergyBar` de `../lib/energy` ; `cssVar`, `vizColors` de `../theme`.
- Produces: `function EnergyChart(props: { bars: EnergyBar[]; title: string; unit: string }): JSX.Element`.

- [ ] **Step 1: Écrire le test smoke qui échoue**

Créer `frontend/src/components/EnergyChart.test.tsx` :

```tsx
import { render, cleanup } from "@testing-library/react";
import { afterEach, test, expect } from "vitest";
import { EnergyChart } from "./EnergyChart";
import type { EnergyBar } from "../lib/energy";

afterEach(() => cleanup());

const bars: EnergyBar[] = [
  { name: "biologie", value: 9, pct: 75 },
  { name: "action", value: 2, pct: 16.7 },
];

test("monte un conteneur recharts avec les barres", () => {
  const { container } = render(<EnergyChart bars={bars} title="Budget par phase" unit="énergie/tick/agent" />);
  expect(container.querySelector(".recharts-responsive-container")).toBeTruthy();
});
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/components/EnergyChart.test.tsx`
Expected: FAIL (`EnergyChart` introuvable).

- [ ] **Step 3: Implémenter `EnergyChart.tsx`**

Créer `frontend/src/components/EnergyChart.tsx` :

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
import type { EnergyBar } from "../lib/energy";

interface EnergyChartProps {
  bars: EnergyBar[];
  title: string;
  unit: string;
}

/** Barres horizontales d'une décomposition énergétique (valeur + % par composante). */
export function EnergyChart({ bars, title, unit }: EnergyChartProps) {
  const viz = vizColors();
  return (
    <div className="energy-chart">
      <h4 style={{ margin: "0 0 var(--space-2)" }}>{title}</h4>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={bars} layout="vertical" margin={{ top: 8, right: 56, bottom: 20, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={cssVar("--color-border")} horizontal={false} />
          <XAxis
            type="number"
            stroke={cssVar("--color-text-dim")}
            fontSize={11}
            label={{ value: unit, position: "insideBottom", offset: -8, fill: cssVar("--color-text-dim") }}
          />
          <YAxis type="category" dataKey="name" width={90} stroke={cssVar("--color-text-dim")} fontSize={11} />
          <RechartsTooltip
            contentStyle={{ backgroundColor: cssVar("--color-surface"), border: `1px solid ${cssVar("--color-border")}` }}
          />
          <Bar dataKey="value" name={unit} isAnimationActive={false}>
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

Run : `cd frontend && npx vitest run src/components/EnergyChart.test.tsx`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/EnergyChart.tsx frontend/src/components/EnergyChart.test.tsx
git commit -m "$(cat <<'EOF'
feat(energie): composant EnergyChart (barres recharts valeur + pourcentage)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `EnergyView` — sélecteur, verdicts, états

**Files:**
- Create: `frontend/src/components/EnergyView.tsx`
- Test: `frontend/src/components/EnergyView.test.tsx`

**Interfaces:**
- Consumes: `apiFetch` ; `queryKeys.runs.decompositions` ; `buildPhaseBreakdown`/`buildBioBreakdown` de `../lib/energy` ; `EnergyChart` ; `Decomposition` de `../types` ; UI `Loading`/`ErrorState`/`Empty`/`Field`/`Panel`.
- Produces: `function EnergyView(): JSX.Element` (export nommé).

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `frontend/src/components/EnergyView.test.tsx` :

```tsx
import { render, screen, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { EnergyView } from "./EnergyView";

afterEach(() => cleanup());

const PHASES = {
  brain: 1, action: 2, biologie: 9, mouvement: 0, net: 12, n_agents: 40,
  bio_metab: 13.47, bio_terrain: 0.27, bio_carry: 0.13, bio_autres: 0.13,
};
const FIXTURE = [
  {
    run_id: "lewis_drain_decompose_7",
    name: "lewis_drain_decompose",
    seed: 7,
    commit: "abc",
    phases: PHASES,
    verdict: "biologie domine (75%)",
    bio_verdict: "métabolisme domine",
  },
];

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue(FIXTURE));

test("affiche le sélecteur, les verdicts et deux charts", async () => {
  const { container } = renderWithClient(<EnergyView />);
  expect(await screen.findByLabelText(/Run de décomposition/)).toBeTruthy();
  expect(screen.getByText(/biologie domine/)).toBeTruthy();
  expect(container.querySelectorAll(".recharts-responsive-container").length).toBe(2);
});

test("état vide quand aucune décomposition", async () => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  renderWithClient(<EnergyView />);
  expect(await screen.findByText(/Aucune décomposition énergétique/)).toBeTruthy();
});
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/components/EnergyView.test.tsx`
Expected: FAIL (`EnergyView` introuvable).

- [ ] **Step 3: Implémenter `EnergyView.tsx`**

Créer `frontend/src/components/EnergyView.tsx` :

```tsx
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { Decomposition } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { buildPhaseBreakdown, buildBioBreakdown } from "../lib/energy";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";
import { Field } from "./ui/Field";
import { Panel } from "./ui/Panel";
import { EnergyChart } from "./EnergyChart";

/** Vue énergie : budget par phase + sous-décomposition biologie d'un run de décompo (EDR 099/100). */
export function EnergyView() {
  const { data: decomps = [], isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.runs.decompositions,
    queryFn: () => apiFetch<Decomposition[]>("/api/runs/decompositions"),
    staleTime: 30_000,
  });

  const [selId, setSelId] = useState<string>("");
  const current = decomps.find((d) => d.run_id === selId) ?? decomps[0];

  if (isLoading) return <Loading label="Chargement des décompositions…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!decomps.length || !current) {
    return (
      <Empty message="Aucune décomposition énergétique. Lance python tools/lewis_survival_sweep.py (main_decompose) côté backend." />
    );
  }

  const phaseBars = buildPhaseBreakdown(current.phases);
  const bioBars = buildBioBreakdown(current.phases);

  return (
    <div className="energy-view">
      <h2>Budget énergétique (décomposition du drain)</h2>
      <div className="row mb-4">
        <Field label="Run de décomposition">
          <select value={current.run_id} onChange={(e) => setSelId(e.target.value)}>
            {decomps.map((d) => (
              <option key={d.run_id} value={d.run_id}>
                {d.name} — seed {d.seed}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <p className="text-dim">
        net <strong>{current.phases.net.toFixed(2)}</strong>/tick · {current.phases.n_agents} agents · seed{" "}
        {current.seed}
      </p>
      <div className="energy-verdicts mb-4">
        <p>
          <strong>Verdict phases :</strong> {current.verdict || "—"}
        </p>
        <p>
          <strong>Verdict biologie :</strong> {current.bio_verdict || "—"}
        </p>
      </div>
      <Panel>
        <EnergyChart bars={phaseBars} title="Budget par phase" unit="énergie/tick/agent" />
      </Panel>
      <Panel className="mt-4">
        <EnergyChart bars={bioBars} title="Sous-décomposition biologie" unit="énergie/tick/agent" />
      </Panel>
    </div>
  );
}
```

- [ ] **Step 4: Lancer les tests pour vérifier le succès**

Run : `cd frontend && npx vitest run src/components/EnergyView.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/EnergyView.tsx frontend/src/components/EnergyView.test.tsx
git commit -m "$(cat <<'EOF'
feat(energie): vue EnergyView (selecteur decompo, verdicts, 2 charts, etats)

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
- Consumes: `EnergyView` de `./components/EnergyView` ; `Zap` de `lucide-react`.
- Produces: onglet `"energie"` navigable.

- [ ] **Step 1: Ajouter la clé `energie` à `TAB_KEYS`**

Dans `frontend/src/tabs.ts`, dans `TAB_KEYS`, ajouter `"energie"` juste après `"cohorte"` :

```ts
  "cohorte",
  "energie",
```

- [ ] **Step 2: Importer l'icône et ajouter l'entrée famille Analyse**

Dans `frontend/src/tabs.ts`, ajouter `Zap` à l'import lucide-react (après `Workflow`, en dernier) :

```ts
  Workflow,
  Zap,
} from "lucide-react";
```

Puis, dans la famille **Analyse** (après l'entrée `cohorte`), ajouter :

```ts
      { key: "cohorte", label: "Cohorte", icon: CandlestickChart },
      { key: "energie", label: "Énergie", icon: Zap },
```

- [ ] **Step 3: Câbler le lazy import et la branche dans `App.tsx`**

Dans `frontend/src/App.tsx`, ajouter le lazy import après la ligne `CohortView` :

```ts
const EnergyView = lazy(() => import("./components/EnergyView").then((m) => ({ default: m.EnergyView })));
```

Puis ajouter la branche de rendu juste après `{tab === "cohorte" && <CohortView />}` :

```tsx
          {tab === "energie" && <EnergyView />}
```

- [ ] **Step 4: Vérifier le typage et toute la suite**

Run : `cd frontend && npx tsc --noEmit`
Expected: aucune erreur.

Run : `cd frontend && npx vitest run`
Expected: PASS (toute la suite, incluant energie).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/tabs.ts frontend/src/App.tsx
git commit -m "$(cat <<'EOF'
feat(energie): integrer l'onglet Energie (famille Analyse) + lazy-load

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Backend — endpoint `/api/runs/decompositions` (patch-and-handoff vers d1)

> **Branche dédiée** : depuis `origin/feat/d1-prod-pairing`, créer `feat/decompositions-endpoint` (worktree séparé) ; PR **dans** `feat/d1-prod-pairing`. Indépendante des tâches 1-4.

**Files:**
- Modify: `backend/app/schemas.py` (`EnergyPhases`, `Decomposition`)
- Modify: `backend/app/services/runs_service.py` (`list_decompositions`)
- Modify: `backend/app/routes/runs.py` (route GET)
- Test: `tests/test_backend.py` (racine du dépôt)
- Modify (régén) : `frontend/openapi.json`, `frontend/src/api/schema.ts`

**Interfaces:**
- Consumes: `runs_service._scan()` (fournit `_run_id`, `name`, `seed`, `commit`, `data`).
- Produces: `GET /api/runs/decompositions` → `list[Decomposition]`.

- [ ] **Step 1: Écrire le test backend qui échoue**

Dans `tests/test_backend.py`, ajouter (après `test_list_distributions_returns_per_seed_vals`) :

```python
def test_list_decompositions_extracts_phases(tmp_path, monkeypatch) -> None:
    """Un run avec data.phases -> 1 Decomposition ; un run scalaire -> ignoré."""
    import backend.app.services.runs_service as rs_mod
    monkeypatch.setattr(rs_mod, "RESULTS_DIR", tmp_path)
    phases = {
        "brain": 1.0, "action": 2.0, "biologie": 9.0, "mouvement": 0.0,
        "net": 12.0, "n_agents": 40.0,
        "bio_metab": 13.47, "bio_terrain": 0.27, "bio_carry": 0.13, "bio_autres": 0.13,
    }
    (tmp_path / "lewis_drain_decompose_7.json").write_text(json.dumps({
        "name": "lewis_drain_decompose", "seed": 7, "commit": "abc1234",
        "data": {"phases": phases, "verdict": "biologie domine", "bio_verdict": "metab domine",
                 "R": 4, "n_eval": 8},
    }), encoding="utf-8")
    (tmp_path / "AND_0.json").write_text(json.dumps({
        "name": "AND", "seed": 0, "data": {"fitness": 0.9},
    }), encoding="utf-8")
    decomps = rs_mod.runs_service.list_decompositions()
    assert len(decomps) == 1
    d = decomps[0]
    assert d["run_id"] == "lewis_drain_decompose_7"
    assert d["phases"]["bio_metab"] == 13.47
    assert d["verdict"] == "biologie domine"

    resp = client.get("/api/runs/decompositions")
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "lewis_drain_decompose"
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run : `cd "<worktree>" && PYTHONPATH=. python -m pytest tests/test_backend.py::test_list_decompositions_extracts_phases -v`
Expected: FAIL (`list_decompositions` n'existe pas / route 404).

- [ ] **Step 3: Ajouter les modèles Pydantic**

Dans `backend/app/schemas.py`, à côté de `DistributionSummary` :

```python
class EnergyPhases(BaseModel):
    brain: float
    action: float
    biologie: float
    mouvement: float
    net: float
    n_agents: float
    bio_metab: float
    bio_terrain: float
    bio_carry: float
    bio_autres: float


class Decomposition(BaseModel):
    run_id: str
    name: str
    seed: int
    commit: str | None = None
    phases: EnergyPhases
    verdict: str
    bio_verdict: str
```

- [ ] **Step 4: Implémenter la méthode de service**

Dans `backend/app/services/runs_service.py`, ajouter cette méthode dans la classe (après `list_distributions`) :

```python
    _PHASE_KEYS = (
        "brain", "action", "biologie", "mouvement", "net", "n_agents",
        "bio_metab", "bio_terrain", "bio_carry", "bio_autres",
    )

    def list_decompositions(self) -> list[dict]:
        """Runs de décomposition énergétique (data.phases avec les 10 clés) — vue Énergie."""
        out: list[dict] = []
        for r in self._scan():
            phases = r["data"].get("phases")
            if not isinstance(phases, dict) or any(k not in phases for k in self._PHASE_KEYS):
                continue
            out.append({
                "run_id": r["_run_id"],
                "name": r["name"],
                "seed": r["seed"],
                "commit": r.get("commit"),
                "phases": {k: phases[k] for k in self._PHASE_KEYS},
                "verdict": r["data"].get("verdict", ""),
                "bio_verdict": r["data"].get("bio_verdict", ""),
            })
        return sorted(out, key=lambda d: d["run_id"])
```

- [ ] **Step 5: Ajouter la route**

Dans `backend/app/routes/runs.py`, ajouter `Decomposition` à l'import depuis `..schemas`, puis ajouter la route **avant** `@router.get("/runs/{run_id}")` :

```python
@router.get("/runs/decompositions", response_model=list[Decomposition])
def list_decompositions() -> list[dict]:
    """Décompositions énergétiques (budget par phase + sous-décompo biologie) pour la vue Énergie."""
    return runs_service.list_decompositions()
```

- [ ] **Step 6: Lancer le test pour vérifier le succès**

Run : `cd "<worktree>" && PYTHONPATH=. python -m pytest tests/test_backend.py::test_list_decompositions_extracts_phases -v`
Expected: PASS.

- [ ] **Step 7: Régénérer le schéma OpenAPI + types TS (drift gate)**

Run :
```bash
cd "<worktree>" && PYTHONPATH=. python tools/dump_openapi.py && cd frontend && npm run gen:api
```
Expected: `frontend/openapi.json` et `frontend/src/api/schema.ts` contiennent l'opération
`list_decompositions_api_runs_decompositions_get`. `git diff --stat` non vide sur ces 2 fichiers.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas.py backend/app/services/runs_service.py backend/app/routes/runs.py tests/test_backend.py frontend/openapi.json frontend/src/api/schema.ts
git commit -m "$(cat <<'EOF'
feat(runs): endpoint GET /api/runs/decompositions (budget energetique pour la vue Energie)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Notes d'exécution

- **Tâches 1→4** sur `feat/frontend-energy-decomposition`, dans l'ordre (T2 dépend de `EnergyBar`/T1 ; T3 de T1+T2 ; T4 de T3). PR vers `main`.
- **Tâche 5** indépendante, worktree depuis `origin/feat/d1-prod-pairing`, PR dans leur branche. Jusqu'à propagation d→main, l'onglet Énergie dégrade en Empty/Error proprement.
- Avant de finir la branche frontend : vérifier qu'aucun fichier backend/test.setup parasite (LF/CRLF) n'entre dans les commits.
