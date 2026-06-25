# Sweep v2 — superposition multi-knob (design)

Date : 2026-06-25
Vague : H (pistes net-new) — item H3
Statut : design approuvé, prêt pour le plan d'implémentation.

## Problème

L'onglet Sweeps (v1) n'affiche qu'**un sweep à la fois** (`current = sweeps.find(selId) ?? sweeps[0]`)
et **une seule métrique** (`SweepChart` trace une `<Line>` + bande ±std). Impossible de **superposer**
plusieurs courbes pour comparer : ni deux runs balayant le même knob, ni plusieurs métriques d'un
même sweep.

## Objectif

Faire évoluer l'onglet Sweeps en **superposition de séries** : choisir un knob, sélectionner
plusieurs séries `(sweep × métrique)` partageant ce knob, les tracer superposées sur un même graphe.
La sélection à une seule série reproduit exactement le comportement v1 (aucune régression).

## Décisions (cadrage validé)

| Sujet | Décision |
|---|---|
| Unité de superposition | Une **série** = `(sweep, métrique)`. |
| Cohérence de l'axe X | Superposition **groupée par knob** : on choisit un knob, seules les séries de ce knob sont superposables → X reste l'unité physique du knob, honnête. |
| Échelles Y hétérogènes | **Toggle normalisation** min-max [0,1] par série (pour mélanger des métriques d'échelles différentes, ex. survie 0-1 vs metab 13). Défaut : brut. |
| Bande ±std | Affichée **uniquement si 1 seule série** sélectionnée et mode brut (sinon illisible en multi-lignes). |
| Placement | **Évolution de l'onglet Sweeps existant** (pas de nouvel onglet). |
| Cross-knob (X normalisé) | **Différé** (option C du brainstorm) — illisible pour v1. |

## Architecture (frontend-only ; `/api/sweeps` déjà sur `main`)

### 1. `lib/sweep.ts` (étendu, pur/testable)

L'ancien `buildSweepData`/`SweepPoint` (mono-série) est **remplacé** par les helpers de superposition
(le composant overlay couvre aussi le cas 1 série). Ils sont retirés avec leurs tests (pas de code mort).

```ts
export interface OverlaySeries {
  id: string;        // ex. `${run_id}::${metric}` — clé unique de dataKey
  label: string;     // ex. `${name} · ${metric}` — légende
  knob: string;
  x: number[];
  y: number[];
  yStd?: number[];
}

// Une ligne de données recharts : x + une clé par série (valeur) + clé band optionnelle.
export interface OverlayPoint {
  x: number;
  [seriesKey: string]: number | [number, number] | undefined;
}

/** Min-max [0,1] par série. Si max == min → tableau de 0 (série plate). Pur. */
export function normalizeSeries(y: number[]): number[];

/** Aligne les séries sur l'UNION triée de leurs valeurs X (les niveaux peuvent différer
 *  entre runs → valeur `undefined` si la série n'a pas ce X, géré par connectNulls).
 *  - `normalize` true → chaque série passée par normalizeSeries.
 *  - Bande `${id}__band` = [y-std, y+std] émise UNIQUEMENT si une seule série, mode brut,
 *    et yStd de même longueur que y. Pur (aucun effet de bord). */
export function buildOverlayData(series: OverlaySeries[], normalize: boolean): OverlayPoint[];
```

- Les tableaux normalisés sont calculés **une fois par série** avant la boucle (pas par point).
- Alignement : `xValues = union triée de toutes les series[].x` ; pour chaque x, `row[s.id] = valeur à
  l'index de x dans s.x`, sinon `undefined`.

### 2. `components/SweepOverlayChart.tsx`

```ts
interface SweepOverlayChartProps {
  series: OverlaySeries[];
  knob: string;
  normalize: boolean;
}
```

recharts `ComposedChart` sur `buildOverlayData(series, normalize)` :
- une `<Line dataKey={s.id} name={s.label} stroke={viz[i % viz.length]} connectNulls
  isAnimationActive={false} />` par série ;
- `<Legend />`, `<XAxis dataKey="x" type="number" label={knob}>`, `<YAxis label={normalize ?
  "valeur normalisée [0,1]" : "valeur"}>`, `<Tooltip>` (couleurs thème via `cssVar`) ;
- si `series.length === 1 && !normalize` et que la donnée contient une clé band → `<Area
  dataKey={`${series[0].id}__band`} fillOpacity={0.15} stroke="none" />` (réplique la bande ±std de v1).

Couleurs via `vizColors()`, chrome via `cssVar()` (mêmes imports que `SweepChart` v1). Zéro `any`.

### 3. `components/SweepView.tsx` (rewire)

- `useQuery` sweeps inchangé (`queryKeys.sweeps`, `/api/sweeps`).
- `knobs` = knobs distincts triés des sweeps. **Knob sélectionné** = état dérivé (`selectedKnob`
  valide sinon `knobs[0]`) — pattern état-dérivé (pas de useEffect, comme CohortView).
- `available` = pour chaque sweep du knob, pour chaque métrique de `Object.keys(sweep.series)` :
  `{ id: `${run_id}::${metric}`, label: `${name} · ${metric}`, knob, x: sweep.x, y:
  sweep.series[metric], yStd: sweep.y_std?.[metric] }`.
- **Sélection de séries** : état `selectedIds: string[]` ; `effectiveSelected = selectedIds.filtré sur
  available` ; si vide → `[available[0].id]` (défaut = 1 série = comportement v1). Rendu via des
  **cases à cocher** (une par série de `available`).
- **Toggle normalisation** : case à cocher, défaut `false`.
- Rendu : sélecteur knob (`Field` + `<select>`), liste de cases séries, toggle normalisation, puis
  `<SweepOverlayChart series={selectedSeriesObjets} knob={selectedKnob} normalize={normalize} />`.
- États : `Loading` / `ErrorState` (onRetry) / `Empty` (« Aucun sweep disponible… » — message v1
  conservé). Si knob choisi mais aucune série cochée → message « Sélectionne au moins une série ».

### 4. Intégration

- `tabs.ts` / `App.tsx` : **inchangés** (onglet `sweeps` déjà présent, lazy `SweepView` déjà câblé).
- `queryKeys` : inchangé (`sweeps` existe).
- Suppression : `components/SweepChart.tsx` + `components/SweepChart.test.tsx` (remplacés par
  l'overlay) ; `buildSweepData`/`SweepPoint` retirés de `lib/sweep.ts` et de `lib/sweep.test.ts`.

## Tests

- `lib/sweep.test.ts` (réécrit) :
  - `normalizeSeries` : `[1,2,3,4,5] → [0,0.25,0.5,0.75,1]` ; série plate `[2,2] → [0,0]`.
  - `buildOverlayData` : 2 séries même X → lignes avec les 2 clés ; X disjoints → union triée +
    `undefined` aux trous ; `normalize=true` → valeurs normalisées, **pas** de clé band ; 1 série + yStd
    + brut → clé `${id}__band = [y-std, y+std]` présente ; band **absente** si >1 série ou si normalize.
- `components/SweepOverlayChart.test.tsx` : smoke — `.recharts-responsive-container` monté avec 2
  séries (recharts en jsdom ne produit pas de géométrie mesurable → assertion conteneur).
- `components/SweepView.test.tsx` (réécrit) : Empty (aucun sweep) ; rendu sélecteur knob + cases séries
  + chart avec fixture ; cocher une 2ᵉ série met à jour le rendu ; toggle normalisation présent. Mock
  `apiFetch` (réutilise le pattern existant du fichier).

## Risques

- **recharts en jsdom** : pas de géométrie. Logique testée = `lib/sweep.ts` (pur) + câblage `SweepView`
  (sélection → données → rendu) ; `SweepOverlayChart` = smoke.
- **Niveaux X divergents entre runs** : gérés par union + `connectNulls` (lignes avec trous), pas une
  erreur. Documenté.
- **Suppression de `SweepChart`** : vérifier qu'aucun autre import ne subsiste (seul `SweepView`
  l'utilise aujourd'hui) avant retrait.
- **Coordination** : `frontend/src/**` + `docs/**` uniquement → aucun conflit avec `feat/d1-prod-pairing`.

## Non-objectifs (YAGNI v1)

- Cross-knob avec X normalisé (comparer la forme entre knobs différents).
- Double axe Y.
- Superposition de plusieurs bandes ±std.
- Persistance de la sélection (localStorage).

## Périmètre des fichiers

Modifiés : `lib/sweep.ts` (+ test réécrit), `components/SweepView.tsx` (+ test réécrit).
Créés : `components/SweepOverlayChart.tsx` (+ test).
Supprimés : `components/SweepChart.tsx` (+ test).

## Suite

Plan d'implémentation via `writing-plans`, tâches TDD :
(1) helpers `lib/sweep.ts` (normalizeSeries + buildOverlayData) — réécrire les tests ;
(2) `SweepOverlayChart` ;
(3) rewire `SweepView` (knob + multi-sélection + normalisation) + retrait `SweepChart`.
Chacune testée.
