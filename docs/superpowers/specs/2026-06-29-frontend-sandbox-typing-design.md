# Clôture du typage de l'état sandbox live — design

Date : 2026-06-29
Vague : I (hygiène) — item I4
Statut : design approuvé, prêt pour le plan d'implémentation.

## Problème

L'audit G/Vague I listait une « dette de typage d3 résiduelle » dans I4. L'inventaire réel la
réduit à un seul foyer : **6 `any` dans `frontend/src/components/parcours/LiveDashboard.tsx`**.
Tout le reste du panier I4 est déjà absorbé :

- typage d3 des gros viewers (`TopologyViewer`/`TimelineViewer`) — fait en **G4** ;
- `FlatlandViewer` — déjà entièrement typé (`FlatlandFrame`/`Agent`/`Prey`/`Item`/`Entity`), zéro `any` ;
- navigation a11y (tablist/`aria-selected`) — primitive `TabList`, fait en **G4** ;
- couverture de tests — passée de ~15 à **117 tests / 42 fichiers** (vagues G→I) ;
- a11y des vues récentes (Sweep/Cohorte/Énergie/Forage) — utilisent déjà `Field`/aria.

Le seul résidu à fort retour et bien borné est donc le typage de l'état sandbox live.

## Objectif

Éliminer les 6 `any` de `LiveDashboard.tsx` en typant l'état du monde sandbox et les lignes de
télémétrie. **Pur raffinement de types, zéro changement de comportement.** Clôt définitivement la
ligne « dette de typage d3/any » d'I4.

## Inventaire des `any` (cartographie exacte)

| Ligne | `any` | Forme réelle (déduite de l'usage canvas/recharts) |
|---|---|---|
| 34 | `apiFetch<any>("/api/sandbox/state")` | état du monde |
| 71 | `state.trees?.forEach((t: any) => …)` | `{ x, y }` |
| 73 | `state.items?.forEach((it: any) => …)` | `{ x, y, type: string }` (branche `type === "Fire"`) |
| 83 | `state.preys?.forEach((p: any) => …)` | `{ x, y }` |
| 87 | `state.agents?.forEach((a: any) => …)` | `{ x, y, energy: number }` (`a.energy > 50`, `a.energy?.toFixed(0)`) |
| 138 | `apiFetch<{ data: any[] }>("/api/sandbox/telemetry")` | `{ tick, mean_energy, mean_surprise, mean_doubt }` |

## Décisions (cadrage validé)

| Sujet | Décision |
|---|---|
| Approche | **A — types maison locaux.** Pas de génération backend (l'état sandbox est un dict peu typé côté Python → coûteux, backend-gated, disproportionné pour 6 `any`). |
| Foyer des types | `frontend/src/types.ts` (convention du projet : foyer des types de réponses API — `Decomposition`, `ForageFunnel`, `DistributionSummary`…). L'état sandbox EST une réponse API (`/api/sandbox/state`). |
| Comportement | **Inchangé.** Mêmes endpoints, même polling, même rendu. Gardes existantes (`state.size > 0`, `?.`) conservées telles quelles. |
| Périmètre des entités | Types distincts des `Sandbox*` vs les types de `FlatlandViewer` (`/ws/flatland`, forme différente : `hp`/`stunned`/`terrain`). Ne PAS forcer un partage. |

## Architecture

### 1. Types (frontend/src/types.ts)

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

### 2. LiveDashboard.tsx

- `LiveWorld` : `apiFetch<SandboxWorldState>("/api/sandbox/state")`. Les callbacks `forEach` perdent
  leur annotation `: any` (le type est inféré depuis l'état typé : `t`→`SandboxEntity`,
  `it`→`SandboxItem`, `p`→`SandboxEntity`, `a`→`SandboxAgent`).
- `LiveTelemetry` : `apiFetch<{ data: SandboxTelemetryRow[] }>("/api/sandbox/telemetry")`.
- Le reste (gardes, halo Fire, barres, recharts) est conservé à l'identique.

## Flux de données

Inchangé : mêmes endpoints (`/api/sandbox/state` polling 500 ms, `/api/sandbox/telemetry` 2 s),
même rendu canvas/recharts.

## Tests

Raffinement de types pur ; le canvas n'est pas testable en jsdom. Vérification :

1. `cd frontend && npx tsc --noEmit` → **0 erreur**.
2. Garde-fou : `grep -n ': any\|<any>' frontend/src/components/parcours/LiveDashboard.tsx` → **0 occurrence**.
3. Non-régression : `LiveDashboard.test.tsx` (smoke existant) + suite complète verte.

**Aucun nouveau test comportemental** : rien de nouveau à exécuter à l'exécution ; ajouter un test sur
un canvas non-testable en jsdom serait du bruit (YAGNI).

## Risques

- **Champs additionnels non typés** : si `/api/sandbox/state` ou `/telemetry` renvoient plus de champs
  que ceux consommés, le type les omet — sans danger (TypeScript tolère les champs surnuméraires sur
  un objet structurel ; on ne lit que ce qu'on type). On type exactement ce que le rendu consomme.
- **Forme réelle backend** : déduite de l'usage (canvas + dataKeys recharts), non d'un schéma Pydantic.
  Risque faible — si un champ manque à l'exécution, les gardes `?.` existantes encaissent (comportement
  inchangé vs `any`).

## Non-objectifs (YAGNI)

- Aucun changement de comportement, aucune extraction de helper, aucune touche backend.
- Pas de couverture de tests diffuse ni d'audit a11y (déjà couverts par G4/H/I — marginaux).
- Pas de génération de types depuis le backend (état sandbox non schématisé côté Python).

## Périmètre des fichiers

Frontend-only (→ `main`) — Modifiés : `frontend/src/types.ts` (6 interfaces `Sandbox*`),
`frontend/src/components/parcours/LiveDashboard.tsx` (3 sites : 2 `apiFetch`, 4 annotations `forEach`).

## Suite

Plan d'implémentation via `writing-plans`, probablement **une seule tâche** (types + rewire + gates).
