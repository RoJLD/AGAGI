# Parcours chercheur guidé (G3) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter une vue « Parcours » qui guide le chercheur à travers Lancer → Suivre → Comparer → Conclure, en orchestrant les composants existants autour d'un état « expérience active » partagé.

**Architecture:** Un contexte React (`ActiveExperimentProvider`, persisté en `localStorage`) tient le descripteur du run en cours. Un orchestrateur `ParcoursView` rend une `StepBar` souple (4 étapes toujours cliquables) puis l'étape active ; chaque étape est un wrapper mince qui réutilise les composants actuels (`RunLauncher`, le dashboard live extrait de `SandboxView`, `ComparisonView`, `LaboratoryView`). Aucun nouvel endpoint backend ; additif et réversible (les onglets actuels survivent).

**Tech Stack:** React 18, TypeScript (strict), Vite, @tanstack/react-query v5, lucide-react, Vitest + @testing-library/react.

## Global Constraints

- TypeScript `strict: true` — aucun `any` introduit ; typer toutes les props.
- Communication/copie UI en **français**.
- Réutiliser les primitives UI existantes (`Button`, `Empty`, `Panel`, `Loading`) et les tokens CSS (`var(--...)`) — pas de couleurs en dur.
- **Zéro modification backend** ; périmètre strictement `frontend/src/**` (+ ce plan). Commits path-scopés.
- react-query : réutiliser les `queryKeys` existants (dédup réseau).
- Chaque commit termine par le trailer : `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Commande de test : `npm --prefix frontend run test -- <chemin du fichier de test>` (vitest run, filtré).
- Branche de travail : `feat/frontend-g3-parcours` (déjà créée).

---

## File Structure

Créés :
- `frontend/src/contexts/ActiveExperimentContext.tsx` — état partagé du run actif (+ persistance localStorage).
- `frontend/src/contexts/ActiveExperimentContext.test.tsx`
- `frontend/src/components/parcours/LiveDashboard.tsx` — dashboard live extrait de SandboxView.
- `frontend/src/components/parcours/LiveDashboard.test.tsx`
- `frontend/src/components/parcours/steps.ts` — type `ParcoursStep` + ordre.
- `frontend/src/components/parcours/StepBar.tsx` — barre d'étapes accessible.
- `frontend/src/components/parcours/StepBar.test.tsx`
- `frontend/src/components/parcours/NextStepButton.tsx` — CTA « étape suivante ».
- `frontend/src/components/parcours/StepLancer.tsx`
- `frontend/src/components/parcours/StepSuivre.tsx`
- `frontend/src/components/parcours/StepComparer.tsx`
- `frontend/src/components/parcours/StepConclure.tsx`
- `frontend/src/components/parcours/steps.test.tsx` — tests des wrappers (Lancer/Suivre).
- `frontend/src/components/parcours/ParcoursView.tsx` — orchestrateur.
- `frontend/src/components/parcours/ParcoursView.test.tsx`

Modifiés :
- `frontend/src/main.tsx` — monte `ActiveExperimentProvider`.
- `frontend/src/components/SandboxView.tsx` — importe `LiveDashboard` (composants live retirés du fichier).
- `frontend/src/components/RunLauncher.tsx` — prop optionnelle `onLaunch`.
- `frontend/src/components/LaboratoryView.tsx` — props optionnelles `initialBaseline`/`initialIntervention`.
- `frontend/src/tabs.ts` — clé + famille `parcours`.
- `frontend/src/App.tsx` — lazy `ParcoursView`, branche `tab === "parcours"`, défaut de route → `"parcours"`.
- `frontend/src/styles.css` — styles `.step-bar` / `.step-pill`.

---

## Task 1: Contexte « expérience active » + montage du provider

**Files:**
- Create: `frontend/src/contexts/ActiveExperimentContext.tsx`
- Test: `frontend/src/contexts/ActiveExperimentContext.test.tsx`
- Modify: `frontend/src/main.tsx`

**Interfaces:**
- Consumes: rien.
- Produces:
  - `interface ActiveExperiment { condition: string; variableTested: string; scriptName: string; worldType: string; seeds: number[]; launchedAt: number; baseline?: string; }`
  - `ActiveExperimentProvider({ children }: { children: ReactNode })`
  - `useActiveExperiment(): { activeExperiment: ActiveExperiment | null; setActiveExperiment(exp): void; updateActiveExperiment(patch: Partial<ActiveExperiment>): void; clearActiveExperiment(): void }`
  - Clé localStorage : `"agiseed.activeExperiment"`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/contexts/ActiveExperimentContext.test.tsx
import { act, render, screen } from "@testing-library/react";
import { beforeEach, expect, test } from "vitest";
import {
  ActiveExperimentProvider,
  useActiveExperiment,
  type ActiveExperiment,
} from "./ActiveExperimentContext";

const SAMPLE: ActiveExperiment = {
  condition: "robust_hof_K",
  variableTested: "robust_hof_K",
  scriptName: "run.py",
  worldType: "stoneage",
  seeds: [0, 1, 2, 3],
  launchedAt: 1000,
};

let api: ReturnType<typeof useActiveExperiment>;
function Probe() {
  api = useActiveExperiment();
  return <div>{api.activeExperiment?.condition ?? "none"}</div>;
}
const renderProbe = () =>
  render(
    <ActiveExperimentProvider>
      <Probe />
    </ActiveExperimentProvider>,
  );

beforeEach(() => window.localStorage.clear());

test("set persiste dans localStorage et expose la valeur", () => {
  renderProbe();
  expect(screen.getByText("none")).toBeTruthy();
  act(() => api.setActiveExperiment(SAMPLE));
  expect(screen.getByText("robust_hof_K")).toBeTruthy();
  expect(JSON.parse(window.localStorage.getItem("agiseed.activeExperiment")!).condition).toBe("robust_hof_K");
});

test("update fait un merge partiel", () => {
  window.localStorage.setItem("agiseed.activeExperiment", JSON.stringify(SAMPLE));
  renderProbe();
  act(() => api.updateActiveExperiment({ baseline: "AND" }));
  expect(JSON.parse(window.localStorage.getItem("agiseed.activeExperiment")!).baseline).toBe("AND");
  expect(api.activeExperiment!.condition).toBe("robust_hof_K");
});

test("clear vide la valeur et le storage", () => {
  window.localStorage.setItem("agiseed.activeExperiment", JSON.stringify(SAMPLE));
  renderProbe();
  act(() => api.clearActiveExperiment());
  expect(screen.getByText("none")).toBeTruthy();
  expect(window.localStorage.getItem("agiseed.activeExperiment")).toBeNull();
});

test("lecture défensive sur storage corrompu", () => {
  window.localStorage.setItem("agiseed.activeExperiment", "{pas du json");
  renderProbe();
  expect(screen.getByText("none")).toBeTruthy();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/contexts/ActiveExperimentContext.test.tsx`
Expected: FAIL — le module `./ActiveExperimentContext` n'existe pas.

- [ ] **Step 3: Write minimal implementation**

```tsx
// frontend/src/contexts/ActiveExperimentContext.tsx
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

export interface ActiveExperiment {
  condition: string;
  variableTested: string;
  scriptName: string;
  worldType: string;
  seeds: number[];
  launchedAt: number;
  baseline?: string;
}

interface ActiveExperimentApi {
  activeExperiment: ActiveExperiment | null;
  setActiveExperiment: (exp: ActiveExperiment) => void;
  updateActiveExperiment: (patch: Partial<ActiveExperiment>) => void;
  clearActiveExperiment: () => void;
}

const STORAGE_KEY = "agiseed.activeExperiment";

function readStored(): ActiveExperiment | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as ActiveExperiment) : null;
  } catch {
    return null;
  }
}

function writeStored(exp: ActiveExperiment | null): void {
  try {
    if (exp) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(exp));
    else window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* localStorage indisponible (navigation privée) : on reste en mémoire. */
  }
}

const ActiveExperimentContext = createContext<ActiveExperimentApi | null>(null);

export function ActiveExperimentProvider({ children }: { children: ReactNode }) {
  const [activeExperiment, setState] = useState<ActiveExperiment | null>(readStored);

  const setActiveExperiment = useCallback((exp: ActiveExperiment) => {
    setState(exp);
    writeStored(exp);
  }, []);

  const updateActiveExperiment = useCallback((patch: Partial<ActiveExperiment>) => {
    setState((prev) => {
      if (!prev) return prev;
      const next = { ...prev, ...patch };
      writeStored(next);
      return next;
    });
  }, []);

  const clearActiveExperiment = useCallback(() => {
    setState(null);
    writeStored(null);
  }, []);

  return (
    <ActiveExperimentContext.Provider
      value={{ activeExperiment, setActiveExperiment, updateActiveExperiment, clearActiveExperiment }}
    >
      {children}
    </ActiveExperimentContext.Provider>
  );
}

export function useActiveExperiment(): ActiveExperimentApi {
  const ctx = useContext(ActiveExperimentContext);
  if (!ctx) throw new Error("useActiveExperiment doit être utilisé dans <ActiveExperimentProvider>");
  return ctx;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/contexts/ActiveExperimentContext.test.tsx`
Expected: PASS (4 tests).

- [ ] **Step 5: Monter le provider dans main.tsx**

Modifier `frontend/src/main.tsx` — ajouter l'import et envelopper `<App />` (à l'intérieur de `ToastProvider`) :

```tsx
import { ActiveExperimentProvider } from "./contexts/ActiveExperimentContext";
```

```tsx
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <ActiveExperimentProvider>
          <App />
        </ActiveExperimentProvider>
      </ToastProvider>
    </QueryClientProvider>
```

- [ ] **Step 6: Vérifier la compilation TypeScript**

Run: `npm --prefix frontend run build`
Expected: build OK (tsc sans erreur).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/contexts/ActiveExperimentContext.tsx frontend/src/contexts/ActiveExperimentContext.test.tsx frontend/src/main.tsx
git commit -m "feat(G3): contexte expérience active (persisté localStorage) + montage provider

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Extraire `LiveDashboard` de `SandboxView`

**Files:**
- Create: `frontend/src/components/parcours/LiveDashboard.tsx`
- Test: `frontend/src/components/parcours/LiveDashboard.test.tsx`
- Modify: `frontend/src/components/SandboxView.tsx`

**Interfaces:**
- Consumes: les `queryKeys.sandbox.*` existants, `apiFetch`, `cssVar`, `vizColors`.
- Produces: `LiveDashboard()` — composant sans props rendant monde 2D + console + télémétrie + journal superviseur + god-mode.

**Contexte :** Aujourd'hui `SandboxView.tsx` définit en bas de fichier `LiveWorld`, `LiveConsole`, `LiveTelemetry`, `LiveSupervisor`, `GodModePanel`, rendus dans le bloc `{running && (<div className="live-dashboard">…</div>)}` ([SandboxView.tsx:265-275](frontend/src/components/SandboxView.tsx#L265-L275), définitions [280-468](frontend/src/components/SandboxView.tsx#L280-L468)). On déplace ces 5 composants + le wrapper dans `LiveDashboard.tsx`, sans changer leur logique.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/parcours/LiveDashboard.test.tsx
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, beforeEach } from "vitest";

vi.mock("../../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../../api/client";
import { LiveDashboard } from "./LiveDashboard";

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue({ size: 0, logs: [], data: [] });
});

test("rend les panneaux live (monde, terminal, télémétrie)", () => {
  renderWithClient(<LiveDashboard />);
  expect(screen.getByText(/Visualisation 2D/)).toBeTruthy();
  expect(screen.getByText(/Terminal Biosphère/)).toBeTruthy();
  expect(screen.getByText(/Télémétrie Cognitive/)).toBeTruthy();
  expect(screen.getByText(/Interventions God-Mode/)).toBeTruthy();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/components/parcours/LiveDashboard.test.tsx`
Expected: FAIL — `./LiveDashboard` n'existe pas.

- [ ] **Step 3: Créer `LiveDashboard.tsx` (déplacer les composants live)**

Couper depuis `SandboxView.tsx` les définitions de `LiveWorld`, `LiveConsole`, `LiveTelemetry`, `LiveSupervisor`, `GodModePanel` (lignes ~280-468) et les coller dans le nouveau fichier. Ajouter le composant exporté `LiveDashboard` qui reprend exactement le markup du bloc `running` actuel. Les imports nécessaires (recharts, react-query, apiFetch, queryKeys, cssVar/vizColors, Panel, Button, useEffect/useRef/useState) sont déplacés avec.

```tsx
// frontend/src/components/parcours/LiveDashboard.tsx
import { useEffect, useRef, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer, Legend,
} from "recharts";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch } from "../../api/client";
import { queryKeys } from "../../api/queryKeys";
import { cssVar, vizColors } from "../../theme";
import { Button } from "../ui/Button";
import { Panel } from "../ui/Panel";

/** Tableau de bord live d'un run sandbox en cours (monde 2D, console, télémétrie,
 *  journal du superviseur, interventions god-mode). Extrait de SandboxView pour
 *  être réutilisé par le Parcours (étape Suivre). Les panneaux pollent le backend. */
export function LiveDashboard() {
  return (
    <div className="live-dashboard">
      <div className="grid-3 mt-5">
        <LiveWorld />
        <LiveConsole />
        <LiveTelemetry />
      </div>
      <LiveSupervisor />
      <GodModePanel />
    </div>
  );
}

const LiveWorld = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { data: state } = useQuery({
    queryKey: queryKeys.sandbox.state,
    queryFn: () => apiFetch<any>("/api/sandbox/state"),
    refetchInterval: 500,
    staleTime: 0,
  });

  useEffect(() => {
    if (!state || !(state.size > 0)) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const size = state.size;
    const cellSize = canvas.width / size;
    const c = {
      bgNight: cssVar("--world-bg-night"),
      bgDay: cssVar("--world-bg-day"),
      grid: cssVar("--world-grid"),
      tree: cssVar("--world-tree"),
      fire: cssVar("--world-fire"),
      item: cssVar("--world-item"),
      prey: cssVar("--world-prey"),
      agentHi: cssVar("--world-agent-hi"),
      agentLo: cssVar("--world-agent-lo"),
    };

    ctx.fillStyle = state.is_night ? c.bgNight : c.bgDay;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = c.grid;
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= size; i++) {
      ctx.beginPath(); ctx.moveTo(i * cellSize, 0); ctx.lineTo(i * cellSize, canvas.height); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, i * cellSize); ctx.lineTo(canvas.width, i * cellSize); ctx.stroke();
    }

    ctx.fillStyle = c.tree;
    state.trees?.forEach((t: any) => ctx.fillRect(t.x * cellSize, t.y * cellSize, cellSize, cellSize));

    state.items?.forEach((it: any) => {
      ctx.fillStyle = it.type === "Fire" ? c.fire : c.item;
      ctx.fillRect(it.x * cellSize + 2, it.y * cellSize + 2, cellSize - 4, cellSize - 4);
      if (it.type === "Fire") {
        ctx.fillStyle = "rgba(243, 139, 168, 0.2)";
        ctx.beginPath(); ctx.arc(it.x * cellSize + cellSize / 2, it.y * cellSize + cellSize / 2, cellSize * 2.5, 0, Math.PI * 2); ctx.fill();
      }
    });

    ctx.fillStyle = c.prey;
    state.preys?.forEach((p: any) => {
      ctx.beginPath(); ctx.arc(p.x * cellSize + cellSize / 2, p.y * cellSize + cellSize / 2, cellSize / 2.5, 0, Math.PI * 2); ctx.fill();
    });

    state.agents?.forEach((a: any) => {
      ctx.fillStyle = a.energy > 50 ? c.agentHi : c.agentLo;
      ctx.beginPath(); ctx.arc(a.x * cellSize + cellSize / 2, a.y * cellSize + cellSize / 2, cellSize / 2, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "white";
      ctx.font = "8px Arial";
      ctx.fillText(a.energy?.toFixed(0), a.x * cellSize, a.y * cellSize + cellSize);
    });
  }, [state]);

  return (
    <Panel className="live-world">
      <h4>🌍 Visualisation 2D</h4>
      <canvas
        ref={canvasRef}
        width={400}
        height={400}
        style={{ border: "1px solid var(--color-border)", borderRadius: "var(--radius-sm)", background: "var(--color-bg)", width: "100%", height: "auto" }}
      />
    </Panel>
  );
};

const LiveConsole = () => {
  const consoleRef = useRef<HTMLPreElement>(null);
  const { data } = useQuery({
    queryKey: queryKeys.sandbox.logs,
    queryFn: () => apiFetch<{ logs: string[] }>("/api/sandbox/logs"),
    refetchInterval: 1000,
    staleTime: 0,
  });
  const logs = data?.logs ?? [];

  useEffect(() => {
    if (consoleRef.current) consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
  }, [logs]);

  return (
    <Panel className="live-console">
      <h4>🖥️ Terminal Biosphère (Live)</h4>
      <pre ref={consoleRef} className="console-block">
        {logs.map((log, i) => (
          <div key={i}>{log}</div>
        ))}
      </pre>
    </Panel>
  );
};

const LiveTelemetry = () => {
  const { data } = useQuery({
    queryKey: queryKeys.sandbox.telemetry,
    queryFn: () => apiFetch<{ data: any[] }>("/api/sandbox/telemetry"),
    refetchInterval: 2000,
    staleTime: 0,
  });
  const rows = data?.data ?? [];
  const viz = vizColors();

  return (
    <div className="panel-base live-telemetry" style={{ height: "400px", overflow: "hidden" }}>
      <h4>📊 Télémétrie Cognitive</h4>
      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" stroke={cssVar("--color-border")} />
          <XAxis dataKey="tick" stroke={cssVar("--color-text-dim")} fontSize={10} />
          <YAxis stroke={cssVar("--color-text-dim")} fontSize={10} />
          <RechartsTooltip contentStyle={{ backgroundColor: cssVar("--color-surface"), border: `1px solid ${cssVar("--color-border")}` }} />
          <Legend />
          <Line type="monotone" dataKey="mean_energy" stroke={viz[0]} dot={false} name="Énergie" />
          <Line type="monotone" dataKey="mean_surprise" stroke={viz[1]} dot={false} name="Surprise" />
          <Line type="monotone" dataKey="mean_doubt" stroke={viz[4]} dot={false} name="Doute" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

const LiveSupervisor = () => {
  const { data: article } = useQuery({
    queryKey: queryKeys.sandbox.article,
    queryFn: () => apiFetch<{ title: string; content: string; timestamp: number }>("/api/sandbox/article"),
    refetchInterval: 5000,
    staleTime: 0,
  });

  return (
    <div className="supervisor-block">
      <h4>🤖 Journal du Superviseur (Ollama LLM)</h4>
      {article ? (
        <div>
          <strong>{article.title}</strong>
          <p>{article.content}</p>
        </div>
      ) : (
        <p className="dim">Chargement du journal...</p>
      )}
    </div>
  );
};

const GodModePanel = () => {
  const [action, setAction] = useState("");
  const godAction = useMutation({
    mutationFn: (a: string) =>
      apiFetch("/api/sandbox/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: a }),
      }),
    onSuccess: () => setAction(""),
  });

  return (
    <Panel className="mt-5">
      <h4>⚡ Interventions God-Mode</h4>
      <div className="row">
        <input
          type="text"
          placeholder="Ex: Apparition d'un incendie (Fire)"
          value={action}
          onChange={(e) => setAction(e.target.value)}
          style={{ flex: 1, padding: "var(--space-2)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-sm)", background: "var(--color-surface)", color: "var(--color-text)" }}
        />
        <Button variant="danger" size="sm" onClick={() => action && godAction.mutate(action)} disabled={godAction.isPending}>
          Lancer
        </Button>
      </div>
    </Panel>
  );
};
```

- [ ] **Step 4: Mettre à jour `SandboxView.tsx`**

Supprimer de `SandboxView.tsx` les définitions des 5 composants live ET les imports devenus inutiles (recharts, `useRef`, `cssVar`/`vizColors` s'ils ne servent plus ailleurs dans le fichier — vérifier). Ajouter l'import :

```tsx
import { LiveDashboard } from "./parcours/LiveDashboard";
```

Remplacer le bloc `{running && (<div className="live-dashboard">…</div>)}` ([SandboxView.tsx:265-275](frontend/src/components/SandboxView.tsx#L265-L275)) par :

```tsx
      {running && <LiveDashboard />}
```

- [ ] **Step 5: Run tests (LiveDashboard + non-régression build)**

Run: `npm --prefix frontend run test -- src/components/parcours/LiveDashboard.test.tsx`
Expected: PASS.

Run: `npm --prefix frontend run build`
Expected: build OK (tsc sans erreur — confirme que SandboxView n'a plus d'import orphelin et que `LiveDashboard` se compile).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/parcours/LiveDashboard.tsx frontend/src/components/parcours/LiveDashboard.test.tsx frontend/src/components/SandboxView.tsx
git commit -m "refactor(G3): extraire LiveDashboard de SandboxView (source unique réutilisable)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: `StepBar` accessible + type `ParcoursStep`

**Files:**
- Create: `frontend/src/components/parcours/steps.ts`
- Create: `frontend/src/components/parcours/StepBar.tsx`
- Test: `frontend/src/components/parcours/StepBar.test.tsx`

**Interfaces:**
- Produces:
  - `type ParcoursStep = "lancer" | "suivre" | "comparer" | "conclure"` (dans `steps.ts`)
  - `const STEP_ORDER: ParcoursStep[]`
  - `StepBar({ current, reached, onSelect }: { current: ParcoursStep; reached: Record<ParcoursStep, boolean>; onSelect: (s: ParcoursStep) => void })`

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/parcours/StepBar.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { test, expect, vi } from "vitest";
import { StepBar } from "./StepBar";

const reached = { lancer: true, suivre: true, comparer: false, conclure: false };

test("rend 4 onglets d'étape avec aria-selected sur l'étape courante", () => {
  render(<StepBar current="suivre" reached={reached} onSelect={() => {}} />);
  const tabs = screen.getAllByRole("tab");
  expect(tabs).toHaveLength(4);
  expect(screen.getByTestId("step-suivre").getAttribute("aria-selected")).toBe("true");
  expect(screen.getByTestId("step-lancer").getAttribute("aria-selected")).toBe("false");
});

test("clic sur une étape appelle onSelect avec sa clé", () => {
  const onSelect = vi.fn();
  render(<StepBar current="lancer" reached={reached} onSelect={onSelect} />);
  fireEvent.click(screen.getByTestId("step-comparer"));
  expect(onSelect).toHaveBeenCalledWith("comparer");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/components/parcours/StepBar.test.tsx`
Expected: FAIL — `./StepBar` n'existe pas.

- [ ] **Step 3: Write minimal implementation**

```ts
// frontend/src/components/parcours/steps.ts
export type ParcoursStep = "lancer" | "suivre" | "comparer" | "conclure";

export const STEP_ORDER: ParcoursStep[] = ["lancer", "suivre", "comparer", "conclure"];
```

```tsx
// frontend/src/components/parcours/StepBar.tsx
import { STEP_ORDER, type ParcoursStep } from "./steps";

const LABELS: Record<ParcoursStep, string> = {
  lancer: "Lancer",
  suivre: "Suivre",
  comparer: "Comparer",
  conclure: "Conclure",
};

/** Barre d'étapes du parcours — souple : toutes cliquables. role=tablist + aria-selected. */
export function StepBar({
  current,
  reached,
  onSelect,
}: {
  current: ParcoursStep;
  reached: Record<ParcoursStep, boolean>;
  onSelect: (s: ParcoursStep) => void;
}) {
  return (
    <div className="step-bar" role="tablist" aria-label="Étapes du parcours">
      {STEP_ORDER.map((s, i) => {
        const state = s === current ? "active" : reached[s] ? "done" : "todo";
        return (
          <button
            key={s}
            role="tab"
            aria-selected={s === current}
            aria-current={s === current ? "step" : undefined}
            data-testid={`step-${s}`}
            className={`step-pill step-pill--${state}`}
            onClick={() => onSelect(s)}
          >
            <span className="step-pill__index">{i + 1}</span>
            {LABELS[s]}
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/components/parcours/StepBar.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/parcours/steps.ts frontend/src/components/parcours/StepBar.tsx frontend/src/components/parcours/StepBar.test.tsx
git commit -m "feat(G3): StepBar accessible (tablist/aria-selected) + type ParcoursStep

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Props optionnelles sur `RunLauncher` et `LaboratoryView`

**Files:**
- Modify: `frontend/src/components/RunLauncher.tsx`
- Modify: `frontend/src/components/LaboratoryView.tsx`
- Test: `frontend/src/components/parcours/steps.test.tsx` (créé ici, complété en Task 5)

**Interfaces:**
- Produces:
  - `RunLauncher({ onLaunch }?: { onLaunch?: (config: RunConfig) => void })` — `onLaunch` appelé au clic « Lancer la file ».
  - `LaboratoryView({ initialBaseline, initialIntervention }?: { initialBaseline?: string; initialIntervention?: string })` — pré-remplissage des sélecteurs.
- Backward compatible : sans props, comportement strictement identique à aujourd'hui.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/parcours/steps.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, beforeEach } from "vitest";

vi.mock("../../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../../api/client";
import { ToastProvider } from "../../contexts/ToastContext";
import { RunLauncher } from "../RunLauncher";

function renderWithProviders(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ToastProvider>{ui}</ToastProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue({ running: false, available_scripts: ["run.py"] });
});

test("RunLauncher appelle onLaunch au lancement de la file", async () => {
  const onLaunch = vi.fn();
  renderWithProviders(<RunLauncher onLaunch={onLaunch} />);
  // enfile puis lance
  fireEvent.click(await screen.findByText(/Enfiler/));
  fireEvent.click(screen.getByText("Lancer la file"));
  expect(onLaunch).toHaveBeenCalledTimes(1);
  expect(onLaunch.mock.calls[0][0]).toMatchObject({ script_name: "run.py", n_seeds: 4 });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/components/parcours/steps.test.tsx`
Expected: FAIL — `onLaunch` n'est pas encore appelé (prop inexistante).

- [ ] **Step 3: Modifier `RunLauncher.tsx`**

Changer la signature ([RunLauncher.tsx:26](frontend/src/components/RunLauncher.tsx#L26)) :

```tsx
export function RunLauncher({ onLaunch }: { onLaunch?: (config: RunConfig) => void } = {}) {
```

Au bouton « Lancer la file » ([RunLauncher.tsx:233-239](frontend/src/components/RunLauncher.tsx#L233-L239)), ajouter l'appel `onLaunch` :

```tsx
          <Button
            variant="primary"
            disabled={!queue.some((it) => it.status === "pending")}
            onClick={() => {
              setQueueRunning(true);
              onLaunch?.(config);
            }}
          >
            Lancer la file
          </Button>
```

- [ ] **Step 4: Modifier `LaboratoryView.tsx`**

Changer la signature ([LaboratoryView.tsx:17](frontend/src/components/LaboratoryView.tsx#L17)) et l'init des états ([LaboratoryView.tsx:19-20](frontend/src/components/LaboratoryView.tsx#L19-L20)) :

```tsx
export function LaboratoryView({
  initialBaseline = "",
  initialIntervention = "",
}: { initialBaseline?: string; initialIntervention?: string } = {}) {
  const queryClient = useQueryClient();
  const [baseline, setBaseline] = useState(initialBaseline);
  const [intervention, setIntervention] = useState(initialIntervention);
```

Le `useEffect` de valeurs par défaut ([LaboratoryView.tsx:37-42](frontend/src/components/LaboratoryView.tsx#L37-L42)) reste inchangé : sa garde `!baseline && !intervention` fait qu'il ne s'exécute pas si les initiales sont fournies — comportement correct (pré-remplissage prioritaire, fallback auto sinon).

- [ ] **Step 5: Run tests + build**

Run: `npm --prefix frontend run test -- src/components/parcours/steps.test.tsx`
Expected: PASS.

Run: `npm --prefix frontend run build`
Expected: build OK.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/RunLauncher.tsx frontend/src/components/LaboratoryView.tsx frontend/src/components/parcours/steps.test.tsx
git commit -m "feat(G3): RunLauncher.onLaunch + LaboratoryView pré-remplissable (rétrocompatible)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: `NextStepButton` + les 4 wrappers d'étape

**Files:**
- Create: `frontend/src/components/parcours/NextStepButton.tsx`
- Create: `frontend/src/components/parcours/StepLancer.tsx`
- Create: `frontend/src/components/parcours/StepSuivre.tsx`
- Create: `frontend/src/components/parcours/StepComparer.tsx`
- Create: `frontend/src/components/parcours/StepConclure.tsx`
- Test: `frontend/src/components/parcours/steps.test.tsx` (compléter)

**Interfaces:**
- Consumes: `useActiveExperiment` (Task 1), `LiveDashboard` (Task 2), `RunLauncher`/`LaboratoryView` props (Task 4), `ComparisonView` (existant), `Empty`/`Button` (existants).
- Produces:
  - `NextStepButton({ label, onClick, disabled }: { label: string; onClick: () => void; disabled?: boolean })`
  - `StepLancer({ onNext }: { onNext: () => void })`
  - `StepSuivre({ running, hasActive, onNext }: { running: boolean; hasActive: boolean; onNext: () => void })`
  - `StepComparer({ hasActive, onNext }: { hasActive: boolean; onNext: () => void })`
  - `StepConclure({ hasActive }: { hasActive: boolean })`

- [ ] **Step 1: Compléter le test (failing)**

Ajouter à `frontend/src/components/parcours/steps.test.tsx` :

```tsx
import { StepSuivre } from "./StepSuivre";
import { StepLancer } from "./StepLancer";
import { ActiveExperimentProvider } from "../../contexts/ActiveExperimentContext";

test("StepSuivre montre un indice quand aucune expérience active et rien ne tourne", () => {
  renderWithProviders(
    <ActiveExperimentProvider>
      <StepSuivre running={false} hasActive={false} onNext={() => {}} />
    </ActiveExperimentProvider>,
  );
  expect(screen.getByText(/Aucune expérience active/)).toBeTruthy();
});

test("StepLancer enregistre l'expérience active au lancement", async () => {
  window.localStorage.clear();
  renderWithProviders(
    <ActiveExperimentProvider>
      <StepLancer onNext={() => {}} />
    </ActiveExperimentProvider>,
  );
  fireEvent.click(await screen.findByText(/Enfiler/));
  fireEvent.click(screen.getByText("Lancer la file"));
  const stored = JSON.parse(window.localStorage.getItem("agiseed.activeExperiment")!);
  expect(stored.scriptName).toBe("run.py");
  expect(stored.seeds).toEqual([0, 1, 2, 3]);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/components/parcours/steps.test.tsx`
Expected: FAIL — modules d'étape inexistants.

- [ ] **Step 3: Créer `NextStepButton.tsx`**

```tsx
// frontend/src/components/parcours/NextStepButton.tsx
import { Button } from "../ui/Button";

export function NextStepButton({
  label,
  onClick,
  disabled,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <div className="text-right mt-5">
      <Button variant="primary" onClick={onClick} disabled={disabled}>
        {label} →
      </Button>
    </div>
  );
}
```

- [ ] **Step 4: Créer `StepLancer.tsx`**

```tsx
// frontend/src/components/parcours/StepLancer.tsx
import { RunLauncher } from "../RunLauncher";
import { useActiveExperiment } from "../../contexts/ActiveExperimentContext";
import { NextStepButton } from "./NextStepButton";
import type { RunConfig } from "../../types";

export function StepLancer({ onNext }: { onNext: () => void }) {
  const { setActiveExperiment, activeExperiment } = useActiveExperiment();

  const handleLaunch = (config: RunConfig) => {
    setActiveExperiment({
      condition: config.variable_tested || config.script_name,
      variableTested: config.variable_tested,
      scriptName: config.script_name,
      worldType: config.world_type,
      seeds: Array.from({ length: config.n_seeds }, (_, i) => config.base_seed + i),
      launchedAt: Date.now(),
    });
  };

  return (
    <>
      <RunLauncher onLaunch={handleLaunch} />
      <NextStepButton label="Suivre le run en direct" onClick={onNext} disabled={!activeExperiment} />
    </>
  );
}
```

- [ ] **Step 5: Créer `StepSuivre.tsx`**

```tsx
// frontend/src/components/parcours/StepSuivre.tsx
import { LiveDashboard } from "./LiveDashboard";
import { Empty } from "../ui/Empty";
import { NextStepButton } from "./NextStepButton";

export function StepSuivre({
  running,
  hasActive,
  onNext,
}: {
  running: boolean;
  hasActive: boolean;
  onNext: () => void;
}) {
  if (!hasActive && !running) {
    return (
      <Empty message="Aucune expérience active — commence par l'étape Lancer, ou choisis une condition existante dans l'Historique des runs." />
    );
  }
  return (
    <>
      <LiveDashboard />
      <NextStepButton label="Comparer les résultats" onClick={onNext} />
    </>
  );
}
```

- [ ] **Step 6: Créer `StepComparer.tsx`**

```tsx
// frontend/src/components/parcours/StepComparer.tsx
import { ComparisonView } from "../ComparisonView";
import { Empty } from "../ui/Empty";
import { NextStepButton } from "./NextStepButton";

export function StepComparer({ hasActive, onNext }: { hasActive: boolean; onNext: () => void }) {
  return (
    <>
      {!hasActive && (
        <Empty message="Astuce : lance une expérience pour pré-remplir l'A/B avec sa condition. Tu peux comparer librement ci-dessous." />
      )}
      <ComparisonView />
      <NextStepButton label="Conclure & publier" onClick={onNext} />
    </>
  );
}
```

- [ ] **Step 7: Créer `StepConclure.tsx`**

```tsx
// frontend/src/components/parcours/StepConclure.tsx
import { LaboratoryView } from "../LaboratoryView";
import { useActiveExperiment } from "../../contexts/ActiveExperimentContext";
import { Empty } from "../ui/Empty";

export function StepConclure({ hasActive }: { hasActive: boolean }) {
  const { activeExperiment } = useActiveExperiment();
  return (
    <>
      {!hasActive && (
        <Empty message="Aucune expérience active — l'étape Conclure interprète et archive une comparaison. Lance d'abord un run." />
      )}
      <LaboratoryView
        initialBaseline={activeExperiment?.baseline}
        initialIntervention={activeExperiment?.condition}
      />
    </>
  );
}
```

- [ ] **Step 8: Run tests + build**

Run: `npm --prefix frontend run test -- src/components/parcours/steps.test.tsx`
Expected: PASS (tous les tests du fichier).

Run: `npm --prefix frontend run build`
Expected: build OK.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/parcours/NextStepButton.tsx frontend/src/components/parcours/StepLancer.tsx frontend/src/components/parcours/StepSuivre.tsx frontend/src/components/parcours/StepComparer.tsx frontend/src/components/parcours/StepConclure.tsx frontend/src/components/parcours/steps.test.tsx
git commit -m "feat(G3): wrappers d'étape (Lancer/Suivre/Comparer/Conclure) + NextStepButton

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: `ParcoursView` (orchestrateur)

**Files:**
- Create: `frontend/src/components/parcours/ParcoursView.tsx`
- Test: `frontend/src/components/parcours/ParcoursView.test.tsx`

**Interfaces:**
- Consumes: `useActiveExperiment`, `useHashRoute`, `queryKeys.sandbox.status`, `apiFetch`, `StepBar`/`STEP_ORDER`, les 4 wrappers (Task 5).
- Produces: `ParcoursView()` — composant sans props (lazy-loadé par App).
- Routing : lit/écrit `#/parcours?step=<étape>` ; ajoute `ab=<condition>` quand on passe à Comparer (consommé par `ComparisonView`).

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/parcours/ParcoursView.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, beforeEach } from "vitest";

vi.mock("../../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../../api/client";
import { ToastProvider } from "../../contexts/ToastContext";
import { ActiveExperimentProvider } from "../../contexts/ActiveExperimentContext";
import { ParcoursView } from "./ParcoursView";

function renderView() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ToastProvider>
        <ActiveExperimentProvider>
          <ParcoursView />
        </ActiveExperimentProvider>
      </ToastProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  window.localStorage.clear();
  window.location.hash = "#/parcours";
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue({ running: false, available_scripts: ["run.py"] });
});

test("affiche la barre d'étapes et démarre sur Lancer", () => {
  renderView();
  expect(screen.getAllByRole("tab")).toHaveLength(4);
  expect(screen.getByTestId("step-lancer").getAttribute("aria-selected")).toBe("true");
});

test("cliquer sur Suivre sans run actif montre l'indice", () => {
  renderView();
  fireEvent.click(screen.getByTestId("step-suivre"));
  expect(screen.getByText(/Aucune expérience active/)).toBeTruthy();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/components/parcours/ParcoursView.test.tsx`
Expected: FAIL — `./ParcoursView` n'existe pas.

- [ ] **Step 3: Write minimal implementation**

```tsx
// frontend/src/components/parcours/ParcoursView.tsx
import { useQuery } from "@tanstack/react-query";
import { useActiveExperiment } from "../../contexts/ActiveExperimentContext";
import { useHashRoute } from "../../hooks/useHashRoute";
import { TAB_KEYS } from "../../tabs";
import { apiFetch } from "../../api/client";
import { queryKeys } from "../../api/queryKeys";
import { StepBar } from "./StepBar";
import { STEP_ORDER, type ParcoursStep } from "./steps";
import { StepLancer } from "./StepLancer";
import { StepSuivre } from "./StepSuivre";
import { StepComparer } from "./StepComparer";
import { StepConclure } from "./StepConclure";

const STEP_SET = new Set<string>(STEP_ORDER);
const isStep = (v: string): v is ParcoursStep => STEP_SET.has(v);

export function ParcoursView() {
  const { query, navigate } = useHashRoute(TAB_KEYS, "parcours");
  const { activeExperiment } = useActiveExperiment();
  const step: ParcoursStep = isStep(query.step ?? "") ? (query.step as ParcoursStep) : "lancer";

  const statusQuery = useQuery({
    queryKey: queryKeys.sandbox.status,
    queryFn: () => apiFetch<{ running: boolean }>("/api/sandbox/status"),
    refetchInterval: 3000,
    staleTime: 0,
  });
  const running = statusQuery.data?.running ?? false;

  const reached: Record<ParcoursStep, boolean> = {
    lancer: true,
    suivre: !!activeExperiment || running,
    comparer: !!activeExperiment,
    conclure: !!activeExperiment?.baseline,
  };

  const go = (s: ParcoursStep) => {
    const q: Record<string, string> = { step: s };
    if (s === "comparer" && activeExperiment) q.ab = activeExperiment.condition;
    navigate("parcours", q);
  };

  return (
    <div className="parcours-view">
      <h2>Parcours d'expérimentation</h2>
      <p className="text-dim mb-4">
        Lancer → Suivre en direct → Comparer → Conclure. Le run que tu lances reste le fil
        conducteur d'étape en étape.
      </p>
      <StepBar current={step} reached={reached} onSelect={go} />

      <div className="parcours-step mt-5">
        {step === "lancer" && <StepLancer onNext={() => go("suivre")} />}
        {step === "suivre" && <StepSuivre running={running} hasActive={!!activeExperiment} onNext={() => go("comparer")} />}
        {step === "comparer" && <StepComparer hasActive={!!activeExperiment} onNext={() => go("conclure")} />}
        {step === "conclure" && <StepConclure hasActive={!!activeExperiment} />}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/components/parcours/ParcoursView.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/parcours/ParcoursView.tsx frontend/src/components/parcours/ParcoursView.test.tsx
git commit -m "feat(G3): ParcoursView orchestrateur (stepper souple, deep-link ab vers Comparer)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Intégration — onglet, landing, lazy-load, styles

**Files:**
- Modify: `frontend/src/tabs.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `ParcoursView` (Task 6).
- Produces: onglet `parcours` dans la nav ; route par défaut `parcours` ; styles `.step-bar`/`.step-pill`.

- [ ] **Step 1: Ajouter la clé d'onglet dans `tabs.ts`**

Importer l'icône `Compass` depuis `lucide-react` (ajouter à l'import existant). Ajouter `"parcours"` en tête de `TAB_KEYS` :

```ts
export const TAB_KEYS = [
  "parcours",
  "edr",
  "live",
  "evolution",
  "comparison",
  "topology",
  "academy",
  "laboratoire",
  "timeline",
  "sandbox",
  "runs",
  "sante",
] as const;
```

Ajouter l'entrée en tête de la famille « Expérimentation » :

```ts
  {
    family: "Expérimentation",
    tabs: [
      { key: "parcours", label: "Parcours", icon: Compass },
      { key: "laboratoire", label: "Laboratoire", icon: FlaskConical },
      { key: "sandbox", label: "Bac à sable", icon: Gamepad2 },
      { key: "runs", label: "Historique runs", icon: Database },
    ],
  },
```

- [ ] **Step 2: Brancher `ParcoursView` dans `App.tsx`**

Ajouter le lazy import (après les autres `const ... = lazy(...)`) :

```tsx
const ParcoursView = lazy(() => import("./components/parcours/ParcoursView").then((m) => ({ default: m.ParcoursView })));
```

Changer le défaut de route ([App.tsx:26](frontend/src/App.tsx#L26)) :

```tsx
  const { tab, setTab, navigate } = useHashRoute(TAB_KEYS, "parcours");
```

Ajouter la branche de rendu (en tête, avant `tab === "edr"`) :

```tsx
          {tab === "parcours" && <ParcoursView />}
          {tab === "edr" && <EDRDashboard />}
```

- [ ] **Step 3: Ajouter les styles dans `styles.css`**

Ajouter en fin de fichier (tokens existants réutilisés) :

```css
/* --- Parcours chercheur (G3) --- */
.step-bar {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-3);
}
.step-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-dim);
  cursor: pointer;
  font: inherit;
}
.step-pill__index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.4em;
  height: 1.4em;
  border-radius: 50%;
  background: var(--color-border);
  color: var(--color-text);
  font-size: var(--font-size-xs);
}
.step-pill--active {
  border-color: var(--color-accent);
  color: var(--color-text);
}
.step-pill--active .step-pill__index {
  background: var(--color-accent);
  color: var(--color-bg);
}
.step-pill--done {
  color: var(--color-text);
}
```

- [ ] **Step 4: Vérifier build + suite de tests complète**

Run: `npm --prefix frontend run build`
Expected: build OK (tsc + vite).

Run: `npm --prefix frontend run test`
Expected: tous les tests passent (existants + nouveaux).

- [ ] **Step 5: Vérification manuelle (dev)**

Run: `npm --prefix frontend run dev`
Vérifier :
- Au chargement sans hash → onglet « Parcours » actif, étape Lancer.
- Cliquer les pastilles d'étapes : navigation libre, indices d'absence de run actif sur Suivre/Comparer/Conclure.
- L'onglet « Bac à sable » fonctionne toujours (dashboard live via `LiveDashboard` quand un run tourne).
- Les deep-links existants (`#/comparison?ab=...`, `#/evolution?gate=...`) restent fonctionnels.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/tabs.ts frontend/src/App.tsx frontend/src/styles.css
git commit -m "feat(G3): intégrer l'onglet Parcours (accueil par défaut) + styles step-bar

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (effectuée)

- **Couverture du spec :** état partagé (Task 1) ; extraction LiveDashboard (Task 2) ; StepBar souple a11y (Task 3) ; lancer multi-seed → setActiveExperiment + Comparer pré-rempli + Conclure article/archivage (Tasks 4-5) ; orchestrateur stepper + dérivation progression + indices Empty (Task 6) ; onglet + landing par défaut + lazy + styles (Task 7). Courbes d'évolution live = non-objectif (future), conforme au spec.
- **Placeholders :** aucun — chaque step porte le code complet.
- **Cohérence des types :** `ActiveExperiment`, `ParcoursStep`, props `onLaunch(config: RunConfig)` / `initialBaseline`/`initialIntervention` / `StepBar({current,reached,onSelect})` cohérents entre Tasks 1→7. `condition` sert de valeur `ab` (deep-link) et d'`initialIntervention`.
- **Note de coordination :** périmètre `frontend/src/**` uniquement → aucun conflit avec `feat/d1-prod-pairing` (backend).
