# Hygiène du polling live (J2) — design

Date : 2026-06-29
Vague : J (audit transverse) — item J2, tranche « hygiène polling » (J2a).
Statut : design approuvé, prêt pour le plan d'implémentation.

## Problème

L'audit perf (Vague J) relève que les composants live pollent le backend **en continu, y compris
onglet navigateur masqué** :
- `LiveDashboard` monte 4 `useQuery` à cadence haute (state 500 ms, logs 1 s, telemetry 2 s,
  article 5 s) — aucun n'a `refetchIntervalInBackground: false`, donc ~60 req/min continuent même
  onglet caché.
- La query `sandbox.status` (`refetchInterval: 3000, staleTime: 0`) est **triplée à l'identique** dans
  `ParcoursView`, `RunLauncher`, `SandboxView` ; `staleTime: 0` force un refetch à chaque montage même
  si une réponse vient d'arriver.

## Objectif

Cesser le polling en arrière-plan et réduire le refetch superflu au montage du status, en factorisant
les options de polling dans un helper pur (DRY + testable). **Frontend-only, zéro changement de
comportement quand l'onglet est visible.**

## Contexte du code (grounded)

- `frontend/src/components/parcours/LiveDashboard.tsx` : 4 `useQuery` —
  `LiveWorld` (`queryKeys.sandbox.state`, 500 ms, `staleTime:0`),
  `LiveConsole` (`queryKeys.sandbox.logs`, 1000 ms, `staleTime:0`),
  `LiveTelemetry` (`queryKeys.sandbox.telemetry`, 2000 ms, `staleTime:0`),
  `LiveSupervisor` (`queryKeys.sandbox.article`, 5000 ms, `staleTime:0`).
- `sandbox.status` identique dans `ParcoursView.tsx`, `RunLauncher.tsx`, `SandboxView.tsx` :
  `{ queryKey: queryKeys.sandbox.status, queryFn: …, refetchInterval: 3000, staleTime: 0 }` (seul le
  type de retour du `queryFn` diffère).

## Décisions (cadrage validé)

| Sujet | Décision |
|---|---|
| Périmètre | **Hygiène polling seule** : `refetchIntervalInBackground:false` partout + `staleTime:2000` sur le status. Mémo `cssVar`/`vizColors` (J2b) et partage WS `/ws/flatland` (J2c) **différés**. |
| Factorisation | Un helper pur `lib/polling.ts` : une constante `STATUS_POLL` (status, 3 sites) et une fabrique `livePoll(intervalMs)` (4 queries LiveDashboard). Corrige la triplication du config status. |
| `refetchIntervalInBackground` | `false` sur les 4 LiveDashboard ET sur le status (le status pollait aussi en fond). |
| `staleTime` | LiveDashboard : `0` conservé (données live, montées une fois). Status : `0 → 2000` (évite le refetch au montage sous 2 s). |
| Backend | Aucune touche. |

## Architecture

### 1. `frontend/src/lib/polling.ts` (pur, testable)

```ts
/** Options react-query communes au sondage du statut sandbox (3 composants). */
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

### 2. Câblage `LiveDashboard.tsx`

Chaque `useQuery` remplace `refetchInterval: <ms>, staleTime: 0` par `...livePoll(<ms>)` :

```ts
  const { data: state } = useQuery({
    queryKey: queryKeys.sandbox.state,
    queryFn: () => apiFetch<SandboxWorldState>("/api/sandbox/state"),
    ...livePoll(500),
  });
```

Idem pour logs (`livePoll(1000)`), telemetry (`livePoll(2000)`), article (`livePoll(5000)`).

### 3. Câblage des 3 queries status

Dans `ParcoursView.tsx`, `RunLauncher.tsx`, `SandboxView.tsx`, remplacer
`refetchInterval: 3000, staleTime: 0` par `...STATUS_POLL` (queryKey + queryFn inchangés) :

```ts
  const statusQuery = useQuery({
    queryKey: queryKeys.sandbox.status,
    queryFn: () => apiFetch<…>("/api/sandbox/status"),
    ...STATUS_POLL,
  });
```

## Flux / comportement

- Onglet visible : identique (mêmes intervalles, mêmes données).
- Onglet masqué : le polling se met en pause (`refetchIntervalInBackground:false`).
- Retour sur l'onglet : react-query v5 refetch sur focus (défaut `refetchOnWindowFocus:true`, non
  désactivé globalement dans le `QueryClient`) → pas de donnée périmée ; l'intervalle reprend.
- Montage d'un composant status < 2 s après le dernier fetch : sert le cache au lieu de refetch.

## Tests

- **`frontend/src/lib/polling.test.ts`** (nouveau, pur) :
  - `STATUS_POLL` égale `{ refetchInterval: 3000, staleTime: 2000, refetchIntervalInBackground: false }`.
  - `livePoll(500)` égale `{ refetchInterval: 500, staleTime: 0, refetchIntervalInBackground: false }`
    (et `livePoll(2000).refetchInterval === 2000`).
- **Non-régression** : `tsc --noEmit` 0 erreur + suite complète verte (les composants spread les helpers ;
  les tests existants de `LiveDashboard`/`ParcoursView`/`SandboxView` doivent rester verts). Les options
  react-query ne sont pas observables en rendu jsdom → pas de test comportemental sur le polling lui-même.

## Risques

- **`staleTime:2000` sur le status** : au pire 2 s de retard sur une transition `running`, sur une query
  qui poll déjà à 3 s → négligeable (recommandation directe de l'audit).
- **`refetchIntervalInBackground:false`** : pas de perte de fraîcheur — refetch au focus + reprise de
  l'intervalle dès visibilité. Si un jour `refetchOnWindowFocus` était désactivé globalement, le retour
  d'onglet attendrait le prochain tick d'intervalle (acceptable, ≤ intervalle).
- **`as const` sur les options** : `refetchInterval`/`staleTime` typés littéraux — compatibles avec
  `UseQueryOptions` (nombres). Le spread n'introduit aucun `any`.

## Non-objectifs (YAGNI)

- J2b : mémo `cssVar()`/`vizColors()` hors chemin chaud (LiveTelemetry 2 Hz, LiveWorld effect 500 ms).
- J2c : partage de la connexion WebSocket `/ws/flatland` (LiveMetrics + FlatlandViewer).
- Aucune touche backend ; pas de changement d'intervalle ni de `queryKey`/`queryFn`.

## Périmètre des fichiers

Frontend-only (→ `main`). Créé : `frontend/src/lib/polling.ts` (+ `polling.test.ts`). Modifiés :
`frontend/src/components/parcours/LiveDashboard.tsx` (4 sites), `frontend/src/components/parcours/ParcoursView.tsx`,
`frontend/src/components/RunLauncher.tsx`, `frontend/src/components/SandboxView.tsx` (1 site chacun).

## Suite

Plan d'implémentation via `writing-plans`, probablement **une seule tâche TDD** (helper + test + câblage 4+3 sites).
