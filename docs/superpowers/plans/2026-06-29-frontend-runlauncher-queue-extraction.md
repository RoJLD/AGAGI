# J4 — Extraction du pilote de file RunLauncher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extraire le pilote séquentiel de la file multi-seed de `RunLauncher.tsx` vers un module pur `lib/queue.ts` testable, en corrigeant le bug latent de matching seed-vs-id.

**Architecture:** Functional core / imperative shell. `queueTick(state, sandboxRunning)` retourne `{ state, effect }` (descripteur d'effet, aucun side-effect). Le composant devient un shell mince qui exécute les effets (`startRun`/`notify`) et tient un unique `useState<QueueState>`.

**Tech Stack:** React 18, TypeScript strict, Vitest, @testing-library/react, @tanstack/react-query v5.

## Global Constraints

- Frontend-only — aucun fichier backend touché.
- TypeScript strict, **zéro `any`**.
- `tsc` 0 erreur, suite verte avant chaque commit final de tâche.
- Commits **path-scoped** (`git commit -- <chemins>`, jamais `git add -A`) — tree partagé, sessions parallèles.
- Worktree : `c:\Users\robla\VScode_Project\AGAGI-front`. Branche : `feat/frontend-queue-extraction` (depuis `origin/main`).
- Tout commit finit par le trailer : `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Commandes lancées depuis `frontend/` : `cd frontend && npx vitest run ...` et `cd frontend && npx tsc --noEmit`.

## File Structure

- **Create** `frontend/src/lib/queue.ts` — module pur du pilote de file (6 fonctions + types `QueueState`/`QueueEffect`).
- **Create** `frontend/src/lib/queue.test.ts` — tests purs de chaque transition.
- **Modify** `frontend/src/components/RunLauncher.tsx` — recâblage shell (un `useState<QueueState>`).
- **Create** `frontend/src/components/RunLauncher.test.tsx` — smoke test de câblage.

Types réutilisés depuis `frontend/src/types.ts` (inchangé) : `QueuedRun { id: string; seed: number; status: QueueStatus }`, `QueueStatus = "pending" | "running" | "done" | "error"`, `RunConfig`.

---

### Task 1: Module pur `lib/queue.ts` + tests

**Files:**
- Create: `frontend/src/lib/queue.ts`
- Test: `frontend/src/lib/queue.test.ts`

**Interfaces:**
- Consumes (depuis `frontend/src/types.ts`, déjà existants) :
  - `type QueueStatus = "pending" | "running" | "done" | "error"`
  - `interface QueuedRun { id: string; seed: number; status: QueueStatus }`
  - `interface RunConfig { script_name: string; world_type: string; base_seed: number; n_seeds: number; mutation_rate: number | null; variable_tested: string; tags: string[] }`
- Produces (consommés par Task 2) :
  - `interface QueueState { items: QueuedRun[]; running: boolean; current: { id: string; sawRunning: boolean } | null }`
  - `type QueueEffect = { type: "start"; id: string; seed: number } | { type: "complete" } | { type: "none" }`
  - `function buildQueueItems(config: RunConfig): QueuedRun[]`
  - `function mergeQueue(prev: QueuedRun[], incoming: QueuedRun[]): QueuedRun[]`
  - `function queueTick(state: QueueState, sandboxRunning: boolean): { state: QueueState; effect: QueueEffect }`
  - `function applyStartFailure(state: QueueState, id: string): QueueState`
  - `function stopQueue(state: QueueState): QueueState`
  - `function queueCounts(items: QueuedRun[]): Partial<Record<QueueStatus, number>>`

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `frontend/src/lib/queue.test.ts` :

```ts
import { describe, it, expect } from "vitest";
import {
  buildQueueItems,
  mergeQueue,
  queueTick,
  applyStartFailure,
  stopQueue,
  queueCounts,
  type QueueState,
} from "./queue";
import type { RunConfig, QueuedRun } from "../types";

const config: RunConfig = {
  script_name: "main_biosphere.py",
  world_type: "stoneage",
  base_seed: 10,
  n_seeds: 3,
  mutation_rate: null,
  variable_tested: "x",
  tags: [],
};

function item(id: string, seed: number, status: QueuedRun["status"]): QueuedRun {
  return { id, seed, status };
}

describe("buildQueueItems", () => {
  it("construit n_seeds items pending avec id=script#seed", () => {
    const items = buildQueueItems(config);
    expect(items).toEqual([
      { id: "main_biosphere.py#10", seed: 10, status: "pending" },
      { id: "main_biosphere.py#11", seed: 11, status: "pending" },
      { id: "main_biosphere.py#12", seed: 12, status: "pending" },
    ]);
  });
});

describe("mergeQueue", () => {
  it("dédup par id, préserve l'ordre, append les nouveaux", () => {
    const prev = [item("a#0", 0, "done"), item("a#1", 1, "pending")];
    const incoming = [item("a#1", 1, "pending"), item("a#2", 2, "pending")];
    expect(mergeQueue(prev, incoming)).toEqual([
      item("a#0", 0, "done"),
      item("a#1", 1, "pending"),
      item("a#2", 2, "pending"),
    ]);
  });
});

describe("queueTick", () => {
  it("file inactive => aucun effet, état inchangé", () => {
    const state: QueueState = { items: [item("a#0", 0, "pending")], running: false, current: null };
    const { state: next, effect } = queueTick(state, false);
    expect(effect).toEqual({ type: "none" });
    expect(next).toBe(state);
  });

  it("idle + pending + sandbox libre => effet start, item->running, current posé", () => {
    const state: QueueState = { items: [item("a#0", 0, "pending")], running: true, current: null };
    const { state: next, effect } = queueTick(state, false);
    expect(effect).toEqual({ type: "start", id: "a#0", seed: 0 });
    expect(next.items[0].status).toBe("running");
    expect(next.current).toEqual({ id: "a#0", sawRunning: false });
  });

  it("current + sandbox running => sawRunning=true, effet none", () => {
    const state: QueueState = {
      items: [item("a#0", 0, "running")],
      running: true,
      current: { id: "a#0", sawRunning: false },
    };
    const { state: next, effect } = queueTick(state, true);
    expect(effect).toEqual({ type: "none" });
    expect(next.current).toEqual({ id: "a#0", sawRunning: true });
    expect(next.items[0].status).toBe("running");
  });

  it("current + sawRunning + sandbox libre => item->done par id, current cleared", () => {
    const state: QueueState = {
      items: [item("a#0", 0, "running")],
      running: true,
      current: { id: "a#0", sawRunning: true },
    };
    const { state: next, effect } = queueTick(state, false);
    expect(effect).toEqual({ type: "none" });
    expect(next.items[0].status).toBe("done");
    expect(next.current).toBeNull();
  });

  it("current + PAS sawRunning + sandbox libre => patiente (pas de done prématuré)", () => {
    const state: QueueState = {
      items: [item("a#0", 0, "running")],
      running: true,
      current: { id: "a#0", sawRunning: false },
    };
    const { state: next, effect } = queueTick(state, false);
    expect(effect).toEqual({ type: "none" });
    expect(next.items[0].status).toBe("running");
    expect(next.current).toEqual({ id: "a#0", sawRunning: false });
  });

  it("pas de current + sandbox running (ad hoc) => attente, pas de start", () => {
    const state: QueueState = { items: [item("a#0", 0, "pending")], running: true, current: null };
    const { state: next, effect } = queueTick(state, true);
    expect(effect).toEqual({ type: "none" });
    expect(next.items[0].status).toBe("pending");
    expect(next.current).toBeNull();
  });

  it("plus aucun pending => effet complete, running=false", () => {
    const state: QueueState = { items: [item("a#0", 0, "done")], running: true, current: null };
    const { state: next, effect } = queueTick(state, false);
    expect(effect).toEqual({ type: "complete" });
    expect(next.running).toBe(false);
  });

  it("deux items même seed, ids différents => seul l'id lancé passe done", () => {
    const state: QueueState = {
      items: [item("a#5", 5, "running"), item("b#5", 5, "pending")],
      running: true,
      current: { id: "a#5", sawRunning: true },
    };
    const { state: next } = queueTick(state, false);
    expect(next.items[0].status).toBe("done"); // a#5 (lancé)
    expect(next.items[1].status).toBe("pending"); // b#5 intact
  });
});

describe("applyStartFailure", () => {
  it("seul l'id échoué passe error, current cleared", () => {
    const state: QueueState = {
      items: [item("a#5", 5, "running"), item("b#5", 5, "pending")],
      running: true,
      current: { id: "a#5", sawRunning: false },
    };
    const next = applyStartFailure(state, "a#5");
    expect(next.items[0].status).toBe("error");
    expect(next.items[1].status).toBe("pending");
    expect(next.current).toBeNull();
  });
});

describe("stopQueue", () => {
  it("running=false, current=null", () => {
    const state: QueueState = {
      items: [item("a#0", 0, "running")],
      running: true,
      current: { id: "a#0", sawRunning: true },
    };
    const next = stopQueue(state);
    expect(next.running).toBe(false);
    expect(next.current).toBeNull();
  });
});

describe("queueCounts", () => {
  it("tally par statut (clés absentes pour statuts absents)", () => {
    const items = [item("a#0", 0, "pending"), item("a#1", 1, "pending"), item("a#2", 2, "done")];
    expect(queueCounts(items)).toEqual({ pending: 2, done: 1 });
  });
});
```

- [ ] **Step 2: Lancer les tests, vérifier qu'ils échouent**

Run: `cd frontend && npx vitest run src/lib/queue.test.ts`
Expected: FAIL — `Failed to resolve import "./queue"` (le module n'existe pas).

- [ ] **Step 3: Implémenter le module pur**

Créer `frontend/src/lib/queue.ts` :

```ts
import type { QueuedRun, QueueStatus, RunConfig } from "../types";

/** État complet du pilote de file (remplace queue + queueRunning + launched). */
export interface QueueState {
  items: QueuedRun[];
  running: boolean;
  current: { id: string; sawRunning: boolean } | null;
}

/** Descripteur d'effet retourné par queueTick ; exécuté par le shell React. */
export type QueueEffect =
  | { type: "start"; id: string; seed: number }
  | { type: "complete" }
  | { type: "none" };

/** Construit n_seeds items pending (graine = base + i, id = script#seed). */
export function buildQueueItems(config: RunConfig): QueuedRun[] {
  return Array.from({ length: config.n_seeds }, (_, i) => ({
    id: `${config.script_name}#${config.base_seed + i}`,
    seed: config.base_seed + i,
    status: "pending" as QueueStatus,
  }));
}

/** Dédup par id : append les items dont l'id n'est pas déjà présent. */
export function mergeQueue(prev: QueuedRun[], incoming: QueuedRun[]): QueuedRun[] {
  return [...prev, ...incoming.filter((it) => !prev.some((p) => p.id === it.id))];
}

/** Met à jour le statut de l'item d'id `id` (retourne un nouveau tableau). */
function setStatus(items: QueuedRun[], id: string, status: QueueStatus): QueuedRun[] {
  return items.map((it) => (it.id === id ? { ...it, status } : it));
}

/**
 * Un pas du pilote séquentiel (le backend ne tient qu'un subprocess).
 * Pur : ne mute rien, retourne { state, effect }. Idempotent à signal constant.
 * La garde sawRunning évite de marquer "done" pendant la latence de polling
 * avant que la sandbox passe running.
 */
export function queueTick(
  state: QueueState,
  sandboxRunning: boolean,
): { state: QueueState; effect: QueueEffect } {
  if (!state.running) return { state, effect: { type: "none" } };

  if (state.current) {
    if (sandboxRunning) {
      if (state.current.sawRunning) return { state, effect: { type: "none" } };
      return {
        state: { ...state, current: { ...state.current, sawRunning: true } },
        effect: { type: "none" },
      };
    }
    if (state.current.sawRunning) {
      return {
        state: { ...state, items: setStatus(state.items, state.current.id, "done"), current: null },
        effect: { type: "none" },
      };
    }
    return { state, effect: { type: "none" } }; // latence : pas encore running, on patiente
  }

  if (sandboxRunning) return { state, effect: { type: "none" } }; // sandbox occupée : attendre
  const next = state.items.find((it) => it.status === "pending");
  if (!next) {
    return { state: { ...state, running: false }, effect: { type: "complete" } };
  }
  return {
    state: {
      ...state,
      items: setStatus(state.items, next.id, "running"),
      current: { id: next.id, sawRunning: false },
    },
    effect: { type: "start", id: next.id, seed: next.seed },
  };
}

/** Event async : l'item d'id `id` a échoué au démarrage -> error, clear current. */
export function applyStartFailure(state: QueueState, id: string): QueueState {
  return {
    ...state,
    items: setStatus(state.items, id, "error"),
    current: state.current?.id === id ? null : state.current,
  };
}

/** Bouton Stop : arrête la file et oublie le run courant. */
export function stopQueue(state: QueueState): QueueState {
  return { ...state, running: false, current: null };
}

/** Tally par statut (clés absentes pour les statuts absents ; consommé avec ?? 0). */
export function queueCounts(items: QueuedRun[]): Partial<Record<QueueStatus, number>> {
  return items.reduce<Partial<Record<QueueStatus, number>>>((acc, it) => {
    acc[it.status] = (acc[it.status] ?? 0) + 1;
    return acc;
  }, {});
}
```

- [ ] **Step 4: Lancer les tests, vérifier qu'ils passent**

Run: `cd frontend && npx vitest run src/lib/queue.test.ts`
Expected: PASS — tous les `describe` verts.

- [ ] **Step 5: Vérifier le typage**

Run: `cd frontend && npx tsc --noEmit`
Expected: 0 erreur.

- [ ] **Step 6: Commit**

```bash
git commit -m "feat(J4): module pur lib/queue.ts (pilote de file) + tests

Réducteur queueTick clé-par-id (corrige le bug seed/id du driver),
buildQueueItems/mergeQueue/applyStartFailure/stopQueue/queueCounts.
Functional core : aucun side-effect, effet retourné comme descripteur.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" -- frontend/src/lib/queue.ts frontend/src/lib/queue.test.ts
```

---

### Task 2: Recâblage `RunLauncher.tsx` en shell + smoke test

**Files:**
- Modify: `frontend/src/components/RunLauncher.tsx`
- Create: `frontend/src/components/RunLauncher.test.tsx`

**Interfaces:**
- Consumes (depuis Task 1, `../lib/queue`) :
  - `QueueState`, `QueueEffect`
  - `buildQueueItems(config)`, `mergeQueue(prev, incoming)`, `queueTick(state, sandboxRunning)`, `applyStartFailure(state, id)`, `stopQueue(state)`, `queueCounts(items)`
- Produces : aucun nouvel export (le composant `RunLauncher` garde sa signature `{ onLaunch?: (config: RunConfig) => void }`).

- [ ] **Step 1: Écrire le smoke test qui échoue**

Créer `frontend/src/components/RunLauncher.test.tsx` :

```tsx
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { ToastProvider } from "../contexts/ToastContext";
import { RunLauncher } from "./RunLauncher";

afterEach(() => cleanup());

beforeEach(() => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue({
    running: false,
    available_scripts: ["main_biosphere.py"],
  });
});

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ToastProvider>{ui}</ToastProvider>
    </QueryClientProvider>,
  );
}

test("le bouton Enfiler ajoute n_seeds badges pending à la file", async () => {
  renderWithClient(<RunLauncher />);
  // attend que le script se peuple depuis /api/sandbox/status
  await screen.findByRole("option", { name: "main_biosphere.py" });
  fireEvent.click(screen.getByText(/Enfiler/));
  const badges = await screen.findAllByText(/· pending$/);
  expect(badges).toHaveLength(4); // n_seeds défaut = 4
});
```

- [ ] **Step 2: Lancer le test, vérifier qu'il échoue**

Run: `cd frontend && npx vitest run src/components/RunLauncher.test.tsx`
Expected: FAIL — le composant compile encore avec l'ancien état ; le test échoue car `ToastProvider` n'enveloppe pas comme attendu OU (après refactor partiel) l'assertion de badges. Si l'ancien code passe déjà ce test, c'est acceptable : il sert de filet de non-régression pendant le recâblage. Le but du recâblage est de garder ce test vert.

> Note implémenteur : ce test décrit le comportement attendu APRÈS recâblage. S'il passe déjà sur le code actuel, ne pas s'en alarmer — procéder au recâblage (Steps 3-4) et garder le test vert.

- [ ] **Step 3: Recâbler le composant**

Dans `frontend/src/components/RunLauncher.tsx` :

1. Remplacer l'import de types/état. En tête, ajouter :

```tsx
import {
  buildQueueItems,
  mergeQueue,
  queueTick,
  applyStartFailure,
  stopQueue,
  queueCounts,
  type QueueState,
} from "../lib/queue";
```

Et retirer de l'import `../types` le besoin de `QueueStatus`/`QueuedRun` s'ils ne servent plus directement (garder `RunConfig` ; `QueueStatus` reste utilisé par `STATUS_VARIANT`). Vérifier les imports après coup.

2. Remplacer les trois déclarations d'état (lignes ~52-54) :

```tsx
  const [queue, setQueue] = useState<QueuedRun[]>([]);
  const [queueRunning, setQueueRunning] = useState(false);
  const launched = useRef<{ seed: number; sawRunning: boolean } | null>(null);
```

par un état unique :

```tsx
  const [q, setQ] = useState<QueueState>({ items: [], running: false, current: null });
```

Retirer l'import `useRef` s'il n'est plus utilisé ailleurs (vérifier).

3. Remplacer `enqueue` (lignes ~59-71) :

```tsx
  const enqueue = () => {
    if (errors.length) {
      notify(errors[0], "error");
      return;
    }
    const incoming = buildQueueItems(config);
    setQ((s) => ({ ...s, items: mergeQueue(s.items, incoming) }));
    notify(`${incoming.length} run(s) enfilé(s).`, "info");
  };
```

4. Remplacer le `useEffect` de polling (lignes ~95-124) :

```tsx
  // Pilote séquentiel piloté par le signal de poll (statusQuery.data).
  // queueTick est pur ; on ne commit l'état que s'il change, on exécute l'effet retourné.
  useEffect(() => {
    if (!statusQuery.data) return;
    const { state: next, effect } = queueTick(q, statusQuery.data.running);
    if (next !== q) setQ(next);
    if (effect.type === "start") {
      startRun(effect.seed).catch(() => setQ((s) => applyStartFailure(s, effect.id)));
    } else if (effect.type === "complete") {
      notify("File de runs terminée.", "success");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusQuery.data, q]);
```

5. Remplacer `counts` (lignes ~126-129) :

```tsx
  const counts = queueCounts(q.items);
```

6. Mettre à jour le JSX qui lisait `queue`/`queueRunning` :

- Bouton « Lancer la file » `disabled` (ligne ~235) : `disabled={!q.items.some((it) => it.status === "pending")}`
- onClick « Lancer la file » (ligne ~236-239) : `onClick={() => { setQ((s) => ({ ...s, running: true })); onLaunch?.(config); }}`
- Condition `queueRunning ?` (ligne ~228) : `q.running ?`
- Bouton « Stopper la file » onClick (ligne ~229) : `onClick={() => setQ(stopQueue)}`
- Bouton « Vider » (lignes ~244-248) : `{q.items.length > 0 && (` … `onClick={() => { if (!q.running) setQ((s) => ({ ...s, items: [] })); }} disabled={q.running}`
- Bloc « File » (ligne ~252) : `{q.items.length > 0 && (` et la map `{q.items.map((it) => (` (ligne ~259).

- [ ] **Step 4: Lancer le smoke test + la suite + typage**

Run: `cd frontend && npx vitest run src/components/RunLauncher.test.tsx`
Expected: PASS — 4 badges `pending`.

Run: `cd frontend && npx vitest run`
Expected: PASS — toute la suite verte (aucune régression).

Run: `cd frontend && npx tsc --noEmit`
Expected: 0 erreur (notamment : plus de `QueuedRun`/`useRef` importés inutilement).

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(J4): recâble RunLauncher en shell mince sur lib/queue

useState<QueueState> unique remplace queue+queueRunning+launched ;
le useEffect de polling exécute l'effet retourné par queueTick.
Smoke test de câblage (Enfiler -> badges).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" -- frontend/src/components/RunLauncher.tsx frontend/src/components/RunLauncher.test.tsx
```

---

## Notes d'exécution

- **Ordre** : Task 1 (module pur, fondation) puis Task 2 (shell qui le consomme).
- **Pas de revue finale séparée** : 2 tâches cohérentes, frontend-only ; si les deux revues de tâche sont propres et les gates vérifiées (tsc 0, suite verte), la revue whole-branch peut être repliée dans la revue de Task 2 (comme I4/J1a/J2).
- **Modèles SDD** : Task 1 = transcription (code complet fourni) → implémenteur haiku ; Task 2 = intégration multi-points dans un composant existant → implémenteur sonnet ; reviewers sonnet.
