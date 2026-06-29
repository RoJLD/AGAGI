# Clôture du typage de l'état sandbox live (I4) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Éliminer les 6 `any` résiduels de `frontend/src/components/parcours/LiveDashboard.tsx` en typant l'état du monde sandbox et les lignes de télémétrie.

**Architecture:** Pur raffinement de types, zéro changement de comportement. Six interfaces `Sandbox*` ajoutées dans `types.ts` (foyer des types de réponses API du projet), puis 3 sites de `LiveDashboard.tsx` re-typés (2 `apiFetch`, 4 annotations `forEach` retirées par inférence). Vérification par `tsc` + garde-fou grep + non-régression de la suite.

**Tech Stack:** React 18 + TypeScript strict + @tanstack/react-query v5 + recharts + Vitest.

## Global Constraints

- **Frontend-only**, sur `feat/frontend-sandbox-typing` → PR vers `main`. Aucune touche backend.
- **Langue** : libellés/commentaires en français.
- **Pas d'emoji** dans le code ni les commits.
- **TypeScript** : zéro `any`, types explicites.
- **Zéro changement de comportement** : mêmes endpoints, même polling, même rendu. Gardes existantes (`state.size > 0`, optional chaining `?.`) conservées telles quelles.
- **Commits** : chaque commit se termine par le trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Vérification** depuis `frontend/` : `npx tsc --noEmit` et `npx vitest run`. Un seul appel bash composé (`cd frontend && ...`).

---

### Task 1: Typer l'état sandbox live + retirer les 6 `any`

**Files:**
- Modify: `frontend/src/types.ts` (ajout de 6 interfaces `Sandbox*`, en fin de fichier)
- Modify: `frontend/src/components/parcours/LiveDashboard.tsx` (3 sites : `LiveWorld` `apiFetch` + 4 callbacks `forEach` ; `LiveTelemetry` `apiFetch`)
- Test: `frontend/src/components/parcours/LiveDashboard.test.tsx` (smoke existant — non-régression, non modifié)

**Interfaces:**
- Produces (dans `types.ts`) :
  - `interface SandboxEntity { x: number; y: number }`
  - `interface SandboxItem extends SandboxEntity { type: string }`
  - `interface SandboxAgent extends SandboxEntity { energy: number }`
  - `interface SandboxWorldState { size: number; is_night: boolean; trees: SandboxEntity[]; items: SandboxItem[]; preys: SandboxEntity[]; agents: SandboxAgent[] }`
  - `interface SandboxTelemetryRow { tick: number; mean_energy: number; mean_surprise: number; mean_doubt: number }`

- [ ] **Step 1: Constater l'état initial (les `any` présents, le smoke vert)**

Run : `cd frontend && grep -n ": any\|<any>" src/components/parcours/LiveDashboard.tsx`
Expected : 6 lignes affichées (≈ lignes 34, 71, 73, 83, 87, 138).

Run : `cd frontend && npx vitest run src/components/parcours/LiveDashboard.test.tsx`
Expected : PASS (smoke existant vert — c'est le filet de non-régression).

- [ ] **Step 2: Ajouter les 6 interfaces dans `types.ts`**

Dans `frontend/src/types.ts`, à la fin du fichier, ajouter :

```ts
/** Une entité positionnée du monde sandbox live (/api/sandbox/state). */
export interface SandboxEntity {
  x: number;
  y: number;
}

/** Un objet du monde sandbox (les "Fire" ont un rendu de halo spécifique). */
export interface SandboxItem extends SandboxEntity {
  type: string;
}

/** Un agent du monde sandbox (couleur selon l'énergie, label énergie). */
export interface SandboxAgent extends SandboxEntity {
  energy: number;
}

/** L'état du monde sandbox live rendu sur le canvas 2D (/api/sandbox/state). */
export interface SandboxWorldState {
  size: number;
  is_night: boolean;
  trees: SandboxEntity[];
  items: SandboxItem[];
  preys: SandboxEntity[];
  agents: SandboxAgent[];
}

/** Une ligne de télémétrie cognitive (/api/sandbox/telemetry). */
export interface SandboxTelemetryRow {
  tick: number;
  mean_energy: number;
  mean_surprise: number;
  mean_doubt: number;
}
```

- [ ] **Step 3: Importer les types dans `LiveDashboard.tsx`**

Dans `frontend/src/components/parcours/LiveDashboard.tsx`, après les imports existants (après la ligne `import { Panel } from "../ui/Panel";`), ajouter :

```ts
import type {
  SandboxWorldState,
  SandboxTelemetryRow,
} from "../../types";
```

- [ ] **Step 4: Typer `LiveWorld` (état + callbacks `forEach`)**

Dans `LiveDashboard.tsx`, composant `LiveWorld` :

a. Remplacer la requête non typée :

```ts
  const { data: state } = useQuery({
    queryKey: queryKeys.sandbox.state,
    queryFn: () => apiFetch<any>("/api/sandbox/state"),
    refetchInterval: 500,
    staleTime: 0,
  });
```

par :

```ts
  const { data: state } = useQuery({
    queryKey: queryKeys.sandbox.state,
    queryFn: () => apiFetch<SandboxWorldState>("/api/sandbox/state"),
    refetchInterval: 500,
    staleTime: 0,
  });
```

b. Retirer les 4 annotations `: any` des callbacks `forEach` (le type est désormais inféré depuis `state` typé). Les corps de fonction sont **strictement inchangés** :

```ts
    state.trees?.forEach((t) => ctx.fillRect(t.x * cellSize, t.y * cellSize, cellSize, cellSize));

    state.items?.forEach((it) => {
      ctx.fillStyle = it.type === "Fire" ? c.fire : c.item;
      ctx.fillRect(it.x * cellSize + 2, it.y * cellSize + 2, cellSize - 4, cellSize - 4);
      if (it.type === "Fire") {
        ctx.fillStyle = "rgba(243, 139, 168, 0.2)";
        ctx.beginPath(); ctx.arc(it.x * cellSize + cellSize / 2, it.y * cellSize + cellSize / 2, cellSize * 2.5, 0, Math.PI * 2); ctx.fill();
      }
    });

    ctx.fillStyle = c.prey;
    state.preys?.forEach((p) => {
      ctx.beginPath(); ctx.arc(p.x * cellSize + cellSize / 2, p.y * cellSize + cellSize / 2, cellSize / 2.5, 0, Math.PI * 2); ctx.fill();
    });

    state.agents?.forEach((a) => {
      ctx.fillStyle = a.energy > 50 ? c.agentHi : c.agentLo;
      ctx.beginPath(); ctx.arc(a.x * cellSize + cellSize / 2, a.y * cellSize + cellSize / 2, cellSize / 2, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "white";
      ctx.font = "8px Arial";
      ctx.fillText(a.energy?.toFixed(0), a.x * cellSize, a.y * cellSize + cellSize);
    });
```

Note : `a.energy?.toFixed(0)` est conservé tel quel (l'optional chaining sur un `number` est toléré par TS et préserve le comportement exact).

- [ ] **Step 5: Typer `LiveTelemetry` (lignes de télémétrie)**

Dans `LiveDashboard.tsx`, composant `LiveTelemetry`, remplacer :

```ts
  const { data } = useQuery({
    queryKey: queryKeys.sandbox.telemetry,
    queryFn: () => apiFetch<{ data: any[] }>("/api/sandbox/telemetry"),
    refetchInterval: 2000,
    staleTime: 0,
  });
```

par :

```ts
  const { data } = useQuery({
    queryKey: queryKeys.sandbox.telemetry,
    queryFn: () => apiFetch<{ data: SandboxTelemetryRow[] }>("/api/sandbox/telemetry"),
    refetchInterval: 2000,
    staleTime: 0,
  });
```

- [ ] **Step 6: Vérifier — typage, garde-fou `any`, non-régression**

Run : `cd frontend && grep -n ": any\|<any>" src/components/parcours/LiveDashboard.tsx`
Expected : **aucune sortie** (0 occurrence).

Run : `cd frontend && npx tsc --noEmit`
Expected : **0 erreur** (l'inférence sur `t`/`it`/`p`/`a` et `data.data` est satisfaite par les types ajoutés).

Run : `cd frontend && npx vitest run`
Expected : **toute la suite verte** (incluant `LiveDashboard.test.tsx` inchangé).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types.ts frontend/src/components/parcours/LiveDashboard.tsx
git commit -m "$(cat <<'EOF'
refactor(I4): typer l'etat sandbox live (retire 6 any de LiveDashboard)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Notes d'exécution

- Tâche unique, frontend-only, sur `feat/frontend-sandbox-typing` → PR vers `main`.
- Aucun nouveau test : raffinement de types pur ; le canvas n'est pas testable en jsdom. Les gates sont `tsc` + garde-fou grep + non-régression de la suite existante (cf. spec § Tests).
- Si `tsc` signale qu'un champ consommé manque au type (forme backend réelle différente de l'usage déduit), ajouter le champ manquant à l'interface `Sandbox*` correspondante dans `types.ts` — ne PAS réintroduire `any`.
