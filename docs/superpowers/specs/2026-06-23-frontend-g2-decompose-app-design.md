# Design — G2 : dégonfler App.tsx (extraction des onglets inline)

Date : 2026-06-23
Statut : validé (brainstorming)
Vague : G2 (dette & qualité frontend — audit 2026-06-23)

## Problème

`App.tsx` (381 lignes) est un god-component. Extraction incohérente : 7 onglets sont des composants,
mais `evolution`/`comparison`/`topology`/`academy` sont rendus **inline**, et App porte en plus les helpers
chart (`createLinePath`, `ChartLine`, `createStabilitySeries`, `formatPercentage`), les 3 `useQuery`
(experiments/detail/academy), le calcul `summaryMetrics`, l'état `compareMode`, et le bandeau latéral (gate
select + panneaux de métriques). App mélange data-fetching, calculs, layout et 4 vues.

## Objectif

Réduire `App.tsx` à un **shell** (routing d'onglet + thème + layout) ; chaque vue devient un composant
**auto-suffisant** (isolé, testable, lazy-loadable). Cela referme aussi la lacune de G1 (les onglets inline
n'étaient pas lazy-loadables).

## Principe : vues auto-suffisantes (option A)

Chaque vue extraite possède ses propres données et lit la route elle-même — **pas de prop drilling** :
- **Données** : `useQuery` avec les `queryKeys` existants (`experiments.list`, `experiments.detail(gate)`,
  `academy`). react-query **déduplique par clé** → cache partagé, zéro requête réseau dupliquée entre
  plusieurs consommateurs.
- **Route** : `useHashRoute(TAB_KEYS, "edr")` ; le hook écoute `hashchange`, donc plusieurs instances restent
  synchronisées (un `setGate`/`setTab` écrit le hash → l'événement met à jour tous les consommateurs).

## Architecture cible

### Nouveaux fichiers
- `frontend/src/lib/charts.ts` — helpers **purs** déplacés depuis App :
  - `createLinePath(values: number[], width: number, height: number): string`
  - `createStabilitySeries(values: number[]): number[]`
  - `formatPercentage(value: number): string`
- `frontend/src/components/GateSidebar.tsx` — bandeau latéral. Possède `experiments` (useQuery) + `detail`
  (useQuery sur `gate` via useHashRoute). Rend : `<select>` de porte (→ `setGate`), panneau « Vue globale »
  (calcul `summaryMetrics` à partir d'`experiments`, mémoïsé), panneau métriques de la porte sélectionnée.
  **Porte aussi la sélection par défaut** : si `experiments` chargé et `gate` vide → `setGate(experiments[0].gate)`.
- `frontend/src/components/EvolutionView.tsx` — possède `detail` (useQuery sur `gate`). Rend `<LiveEvolution/>`
  (eager, déjà extrait) + le graphe d'évolution (`detail.history` via `ChartLine` local + `createStabilitySeries`)
  + la légende. `ChartLine` (JSX, mono-usage) est défini **local** dans ce fichier, utilisant `createLinePath`.
- `frontend/src/components/ComparisonView.tsx` — possède `experiments` (useQuery). État local `compareMode`
  (`"global" | "ab"`), initialisé à `"ab"` si `query.ab` présent (via useHashRoute), sinon `"global"`. Rend le
  toggle Vue globale / A/B, puis soit `ComparisonChart`+`RadarChart`+liste, soit `ABComparisonView preselectA={query.ab}`.
- `frontend/src/components/TopologyView.tsx` — possède `detail` (useQuery sur `gate`). Rend `TopologyViewer`
  (`detail.graph`) + l'analyse des métriques (`detail.metrics`).
- `frontend/src/components/AcademyView.tsx` — possède `academy` (useQuery). Rend les 3 boîtes (historique des
  versions / timeline / objectifs).

### `App.tsx` (shell réduit)
- Conserve : `useHashRoute(TAB_KEYS, "edr")` (tab/setTab/navigate), `useTheme`, le rendu de la topbar (nav
  onglets), la logique `showSidebar = tab === "evolution" || tab === "comparison" || tab === "topology"`,
  le `<Suspense>`/`ErrorBoundary` (G1), et le passage `onCompare={(cond) => navigate("comparison", { ab: cond })}`
  à `RunsHistoryView`.
- Supprime : les 3 `useQuery`, `summaryMetrics`, `compareMode`, les helpers chart, le `useEffect` de sélection
  par défaut (→ GateSidebar), les corps inline des 4 onglets, le markup du bandeau.
- Rend `<GateSidebar/>` quand `showSidebar`, et les 4 nouvelles vues dans le switch.

### Lazy-load (synergie G1)
Les 4 nouvelles vues (`EvolutionView`, `ComparisonView`, `TopologyView`, `AcademyView`) sont importées en
`React.lazy` dans App (wrapper export-nommé), comme les autres vues. `GateSidebar` reste **eager** (léger, hors
du `<Suspense>` des onglets, rendu dans le layout). `ComparisonChart`/`RadarChart` (utilisés par ComparisonView)
restent des imports normaux **dans** ComparisonView.

## Flux de données

```
useHashRoute (hashchange) ─ gate/tab/query partagés
QueryClient (main.tsx) ─ cache partagé par queryKey
  GateSidebar      → experiments + detail(gate)   (sélectionne la porte par défaut)
  EvolutionView    → detail(gate)
  TopologyView     → detail(gate)
  ComparisonView   → experiments (+ query.ab)
  AcademyView      → academy
App (shell)        → tab/route + layout, aucune donnée métier
```

## Gestion d'erreur / états
- Chaque vue conserve les états loading/empty existants (ex. « Chargement... ») — **inchangés** dans cette
  passe (l'uniformisation via primitives `Loading`/`Empty` est G4, hors scope ici).
- `<Suspense>` (G1) couvre le chargement des chunks lazy ; `ErrorBoundary` par onglet couvre les erreurs.

## Tests
- Un test de rendu par nouvelle vue (RTL + `QueryClientProvider` + `apiFetch` mocké) :
  - `GateSidebar` : avec experiments mockés, affiche le select + une métrique agrégée ; déclenche la sélection
    par défaut.
  - `EvolutionView` / `TopologyView` : avec `detail` mocké, rendent le graphe / la topologie ; état de
    chargement si pas de gate.
  - `ComparisonView` : mode global par défaut ; mode AB si `query.ab` (hash) présent.
  - `AcademyView` : avec academy mocké, rend les 3 boîtes.
- Les **15 tests existants** restent verts.
- `lib/charts.ts` : tests unitaires purs (`createLinePath` non vide pour une série ; `createStabilitySeries`
  borne dans [0,1] ; `formatPercentage(0.5) === "50.0%"`).
- Build `tsc` vert ; App.tsx nettement réduit (cible < ~120 lignes). Pas de changement d'API → pas de drift.

## Contraintes
- Comportement runtime **identique** (mêmes onglets, mêmes vues, mêmes deep-links `?gate=`/`?ab=`).
- Aucun changement de style/CSS (les classes existantes sont réutilisées telles quelles).
- Aucun changement backend / API.

## Hors scope (YAGNI)
- Uniformisation loading/error/empty via primitives (= G4).
- a11y des onglets (= G4).
- Typage des callbacks d3 (= G4).
- Toute refonte visuelle ou de parcours (= G3).
