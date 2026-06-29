# Hygiène du polling live (J2) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cesser le polling react-query en arrière-plan (onglet masqué) et réduire le refetch superflu au montage du status, en factorisant les options dans un helper pur `lib/polling.ts`.

**Architecture:** Frontend-only, zéro changement de comportement onglet visible. Un helper pur (`STATUS_POLL` constante + `livePoll(ms)` fabrique) est testé en unitaire, puis spread dans les 4 `useQuery` de `LiveDashboard` et les 3 queries `sandbox.status` (corrige aussi la triplication du config status).

**Tech Stack:** React 18 + TypeScript strict + @tanstack/react-query v5 + Vitest.

## Global Constraints

- **Frontend-only**, sur `feat/frontend-perf-live-fetching` → PR vers `main`. Aucune touche backend.
- **Langue** : commentaires en français.
- **Pas d'emoji** dans le code ni les commits.
- **TypeScript** : zéro `any`, types explicites.
- **Zéro changement de comportement onglet visible** : `queryKey`/`queryFn`/intervalles inchangés ; seules ajoutées/modifiées : `refetchIntervalInBackground:false` (partout) et `staleTime` (status `0→2000` ; LiveDashboard `0` conservé).
- **Commits** : chaque commit se termine par le trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Tests/typage** depuis `frontend/` : `npx vitest run <chemin>` et `npx tsc --noEmit`. Un seul appel bash composé (`cd frontend && ...`).

---

### Task 1: Helper `lib/polling.ts` + câblage des 7 sites de polling

**Files:**
- Create: `frontend/src/lib/polling.ts`
- Test: `frontend/src/lib/polling.test.ts`
- Modify: `frontend/src/components/parcours/LiveDashboard.tsx` (4 `useQuery` : state/logs/telemetry/article)
- Modify: `frontend/src/components/parcours/ParcoursView.tsx` (1 query status)
- Modify: `frontend/src/components/RunLauncher.tsx` (1 query status)
- Modify: `frontend/src/components/SandboxView.tsx` (1 query status)

**Interfaces:**
- Produces:
  - `export const STATUS_POLL = { refetchInterval: 3000, staleTime: 2000, refetchIntervalInBackground: false } as const`
  - `export function livePoll(intervalMs: number): { refetchInterval: number; staleTime: number; refetchIntervalInBackground: boolean }`

- [ ] **Step 1: Écrire le test du helper (échec)**

Créer `frontend/src/lib/polling.test.ts` :

```ts
import { test, expect } from "vitest";
import { STATUS_POLL, livePoll } from "./polling";

test("STATUS_POLL : pas de polling en fond, staleTime 2s, intervalle 3s", () => {
  expect(STATUS_POLL).toEqual({
    refetchInterval: 3000,
    staleTime: 2000,
    refetchIntervalInBackground: false,
  });
});

test("livePoll : intervalle paramétré, staleTime 0, pas de polling en fond", () => {
  expect(livePoll(500)).toEqual({
    refetchInterval: 500,
    staleTime: 0,
    refetchIntervalInBackground: false,
  });
  expect(livePoll(2000).refetchInterval).toBe(2000);
});
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/lib/polling.test.ts`
Expected : FAIL (`polling.ts` introuvable).

- [ ] **Step 3: Implémenter `lib/polling.ts`**

Créer `frontend/src/lib/polling.ts` :

```ts
/** Options react-query communes au sondage du statut sandbox (3 composants).
 *  Pas de polling en arrière-plan ; cache 2 s pour éviter le refetch au montage. */
export const STATUS_POLL = {
  refetchInterval: 3000,
  staleTime: 2000,
  refetchIntervalInBackground: false,
} as const;

/** Options react-query pour une query live de LiveDashboard, à intervalle donné.
 *  staleTime 0 (données fraîches à l'affichage) ; pas de polling en arrière-plan. */
export function livePoll(intervalMs: number) {
  return {
    refetchInterval: intervalMs,
    staleTime: 0,
    refetchIntervalInBackground: false,
  } as const;
}
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run : `cd frontend && npx vitest run src/lib/polling.test.ts`
Expected : PASS (2 tests).

- [ ] **Step 5: Câbler les 4 queries de `LiveDashboard.tsx`**

Dans `frontend/src/components/parcours/LiveDashboard.tsx`, ajouter l'import (après les imports existants, ex. après `import { queryKeys } from "../../api/queryKeys";`) :

```ts
import { livePoll } from "../../lib/polling";
```

Puis, dans chaque `useQuery`, remplacer les lignes `refetchInterval: <ms>, staleTime: 0,` par `...livePoll(<ms>),`.

`LiveWorld` (state, 500 ms) :
```ts
  const { data: state } = useQuery({
    queryKey: queryKeys.sandbox.state,
    queryFn: () => apiFetch<SandboxWorldState>("/api/sandbox/state"),
    ...livePoll(500),
  });
```

`LiveConsole` (logs, 1000 ms) :
```ts
  const { data } = useQuery({
    queryKey: queryKeys.sandbox.logs,
    queryFn: () => apiFetch<{ logs: string[] }>("/api/sandbox/logs"),
    ...livePoll(1000),
  });
```

`LiveTelemetry` (telemetry, 2000 ms) :
```ts
  const { data } = useQuery({
    queryKey: queryKeys.sandbox.telemetry,
    queryFn: () => apiFetch<{ data: SandboxTelemetryRow[] }>("/api/sandbox/telemetry"),
    ...livePoll(2000),
  });
```

`LiveSupervisor` (article, 5000 ms) :
```ts
  const { data: article } = useQuery({
    queryKey: queryKeys.sandbox.article,
    queryFn: () => apiFetch<{ title: string; content: string; timestamp: number }>("/api/sandbox/article"),
    ...livePoll(5000),
  });
```

> Note : conserver le `queryFn` exact existant de chaque query (les types `SandboxWorldState`/`SandboxTelemetryRow` proviennent du typage J1/I4 déjà en place). Ne modifier QUE les lignes `refetchInterval`/`staleTime`.

- [ ] **Step 6: Câbler les 3 queries status (`ParcoursView`, `RunLauncher`, `SandboxView`)**

Dans chacun des 3 fichiers, ajouter l'import (au niveau des imports existants) :

```ts
import { STATUS_POLL } from "../lib/polling";
```

Attention au chemin relatif : `ParcoursView.tsx` est sous `components/parcours/` → `"../../lib/polling"` ;
`RunLauncher.tsx` et `SandboxView.tsx` sont sous `components/` → `"../lib/polling"`.

Puis, dans la query `statusQuery` de chaque fichier, remplacer `refetchInterval: 3000, staleTime: 0,` par `...STATUS_POLL,`. Exemple pour `SandboxView.tsx` :

```ts
  const statusQuery = useQuery({
    queryKey: queryKeys.sandbox.status,
    queryFn: () => apiFetch<SandboxStatus>("/api/sandbox/status"),
    ...STATUS_POLL,
  });
```

Identique dans `ParcoursView.tsx` (`queryFn` → `apiFetch<{ running: boolean }>`) et `RunLauncher.tsx` (`queryFn` → `apiFetch<SandboxStatusLite>`). Ne changer QUE les 2 lignes `refetchInterval`/`staleTime` ; `queryKey`/`queryFn` inchangés.

- [ ] **Step 7: Vérifier le typage et toute la suite**

Run : `cd frontend && npx tsc --noEmit`
Expected : 0 erreur (le spread des options littérales `as const` est compatible avec `UseQueryOptions` ; aucun `any`).

Run : `cd frontend && npx vitest run`
Expected : toute la suite verte (incluant `polling.test.ts` et la non-régression de `LiveDashboard`/`ParcoursView`/`SandboxView`).

- [ ] **Step 8: Vérifier qu'aucun site de polling résiduel n'a été oublié**

Run : `cd frontend && grep -rn "refetchInterval" src/components`
Expected : chaque occurrence de `refetchInterval` restante est SOIT issue du spread (`...livePoll(`/`...STATUS_POLL`), SOIT hors-périmètre documenté. Aucune ligne `refetchInterval: <n>, staleTime: 0` résiduelle dans LiveDashboard/ParcoursView/RunLauncher/SandboxView.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/lib/polling.ts frontend/src/lib/polling.test.ts frontend/src/components/parcours/LiveDashboard.tsx frontend/src/components/parcours/ParcoursView.tsx frontend/src/components/RunLauncher.tsx frontend/src/components/SandboxView.tsx
git commit -m "$(cat <<'EOF'
perf(J2): hygiene du polling live (refetchIntervalInBackground false + staleTime status via lib/polling)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Notes d'exécution

- Tâche unique, frontend-only, sur `feat/frontend-perf-live-fetching` → PR vers `main`.
- Le helper est le seul code testable en unitaire ; le câblage est garanti par `tsc` + non-régression.
- Chemins d'import : `LiveDashboard`/`ParcoursView` sous `components/parcours/` → `"../../lib/polling"` ;
  `RunLauncher`/`SandboxView` sous `components/` → `"../lib/polling"`.
- Ne PAS toucher aux intervalles, `queryKey`, `queryFn` ; ne PAS ajouter `staleTime` aux 4 queries
  LiveDashboard (elles conservent `staleTime:0` via `livePoll`).
