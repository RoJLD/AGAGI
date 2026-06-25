# Vue cohorte / distributions par condition (design)

Date : 2026-06-25
Vague : H (pistes net-new) — item H2
Statut : design approuvé, prêt pour le plan d'implémentation.

## Problème

L'A/B (`/api/runs/compare`) est **pairwise** : il compare deux conditions sur une métrique et
renvoie un verdict (Welch t, Cohen d). Mais il n'existe aucune vue de la **dispersion multi-seed
par condition** : on ne peut pas voir, pour une métrique donnée, comment chaque condition se
distribue sur ses seeds, ni comparer cette dispersion entre toutes les conditions. Or c'est
exactement ce qu'il faut pour juger si un résultat **tient** (effet réel) ou s'il est porté par un
outlier / un n trop faible.

## Objectif

Un onglet **Cohorte** : on choisit une métrique, on voit la **distribution par seed** (box plot +
points bruts jitterés) de **toutes les conditions** qui portent cette métrique, triées par médiane
décroissante. Vue de robustesse autonome.

## Décisions (cadrage validé)

| Sujet | Décision |
|---|---|
| Portée | **N conditions** sur une métrique (vue d'ensemble), pas l'enrichissement pairwise. |
| Donnée | **Nouvel endpoint** `GET /api/runs/distributions?metric=X` (réutilise `_values`). Patch-and-handoff vers `feat/d1-prod-pairing` (comme `/api/sweeps` #47). Liste des métriques via `/api/runs/conditions` (déjà en cache). |
| Visualisation | **Box plot + strip** (tous les seeds en points jitterés, outliers surlignés). **Pas de violin** (trompeur à petit n). |
| Layout | **Horizontal** (une ligne par condition) — gère noms longs + nombreuses conditions, échelle X partagée. |
| Tri | Par **médiane décroissante** (la condition la plus forte en haut). |
| Placement | Nouvel onglet `cohorte`, famille **Analyse** (icône lucide `CandlestickChart`). |
| Points | **Tous** les seeds tracés sur le strip ; ceux hors moustaches (1.5×IQR) surlignés. |

## Architecture

### 1. Backend — endpoint distributions (patch-and-handoff vers d1)

Aucune dépendance à la session parallèle côté frontend, mais l'endpoint vit côté backend → PR
**dans `feat/d1-prod-pairing`** (je ne pousse pas sur leur branche ; cf. parallel-sessions).

- `backend/app/schemas.py` :
  ```python
  class DistributionSummary(BaseModel):
      name: str
      vals: list[float]
      n: int
  ```
- `backend/app/services/runs_service.py` — nouvelle méthode :
  ```python
  def list_distributions(self, metric: str) -> list[dict]:
      out = []
      for name in sorted({r["name"] for r in self._scan()}):
          vals = self._values(name, metric)   # déjà présent
          if vals:
              out.append({"name": name, "vals": vals, "n": len(vals)})
      return out
  ```
- `backend/app/routes/runs.py` :
  ```python
  @router.get("/runs/distributions", response_model=list[DistributionSummary])
  def list_distributions(metric: str = Query(..., description="métrique numérique")) -> list[dict]:
      return runs_service.list_distributions(metric)
  ```
- `backend/tests/test_backend.py` : un test qui pose 2 conditions × N seeds avec une métrique
  scalaire, appelle `/api/runs/distributions?metric=...`, vérifie `name`/`vals`/`n` et l'exclusion
  des conditions sans la métrique.
- Régénérer `frontend/openapi.json` (`tools/dump_openapi.py`) puis `frontend/src/api/schema.ts`
  (`npm run gen:api`) pour garder le **drift gate** vert.

> Jusqu'à propagation d→main, l'endpoint 404 : l'onglet dégrade en Empty/Error proprement
> (comportement déjà vécu avec Sweep). Le frontend type la réponse via `types.ts` (hand-rolled),
> pas via `schema.ts` — la vue compile et fonctionne dès que l'endpoint répond.

### 2. `lib/cohort.ts` (pur, testable)

```ts
import type { DistributionSummary } from "../types";

export interface BoxStats {
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
  iqr: number;
  lowerWhisker: number;   // plus petite valeur >= q1 - 1.5*iqr
  upperWhisker: number;   // plus grande valeur <= q3 + 1.5*iqr
  outliers: number[];     // valeurs hors [lowerWhisker, upperWhisker]
  n: number;
}

export interface CohortRow {
  name: string;
  vals: number[];
  stats: BoxStats;
}

/** Quantiles par interpolation linéaire (méthode type-7, comme numpy/d3.quantile). */
export function quantile(sorted: number[], p: number): number;

/** Stats de box plot Tukey. Préconditions : vals non vide. */
export function computeBoxStats(vals: number[]): BoxStats;

/** Construit les lignes de cohorte triées par médiane décroissante ; conditions vides exclues. */
export function buildCohort(dists: DistributionSummary[]): CohortRow[];
```

- `quantile` : tri ascendant supposé fait par l'appelant ; `computeBoxStats` trie une copie.
- Cas `n === 1` : q1 = median = q3 = la valeur ; iqr = 0 ; pas d'outliers ; moustaches = la valeur.
- Pur, aucun effet de bord, entièrement testé en jsdom.

### 3. `components/CohortChart.tsx` (SVG box+strip, horizontal)

SVG auto-rendu (pas de recharts box natif, pas besoin de D3 — échelles linéaires simples). Une
**ligne par condition**, échelle X linéaire partagée sur `[globalMin, globalMax]` (avec marge).
Par ligne : moustache (trait), box q1–q3 (rect), médiane (trait épais), **un cercle par seed**
jitteré verticalement par offset **déterministe** (basé sur l'index du seed, pas `Math.random`),
outliers en couleur d'accent. Libellé de condition à gauche, `n=…` à droite.

```ts
interface CohortChartProps {
  rows: CohortRow[];
  metric: string;
}
```

- Typé (`zéro any`), couleurs via `vizColors()`/`cssVar()` (thème-aware), `aria-label` FR
  (« Distributions par condition pour la métrique <metric> »).
- Hauteur = `rows.length * ROW_H` (constante), largeur responsive (conteneur `Panel`).
- Tooltip natif `<title>` par box (médiane, IQR, n) — léger, suffisant v1.

### 4. `components/CohortView.tsx`

- 2 `useQuery` :
  - `queryKeys.runs.conditions` → union des `metrics` de toutes les conditions (sélecteur).
  - `queryKeys.runs.distributions(metric)` → `DistributionSummary[]` (activée seulement si `metric`
    défini : `enabled: !!metric`).
- Sélecteur de métrique (`Field` + `<select>`), défaut = 1ʳᵉ métrique disponible (effet
  d'initialisation comme `SweepView`).
- États : `Loading` (conditions en cours), `ErrorState` (avec `onRetry`), `Empty` (aucune métrique
  numérique disponible, ou `distributions` vide pour la métrique choisie).
- Rendu : titre, sélecteur, caption (« métrique <m> · <k> conditions »), `Panel` + `CohortChart`,
  légende (box = IQR, trait = médiane, points = seeds, accent = outliers).

### 5. Intégration

- `frontend/src/types.ts` : `export interface DistributionSummary { name: string; vals: number[]; n: number }`.
- `frontend/src/api/queryKeys.ts` : `runs.distributions: (metric: string) => ["runs", "distributions", metric] as const`.
- `frontend/src/tabs.ts` : clé `"cohorte"` ajoutée à `TAB_KEYS` (après `"sweeps"`) + entrée famille
  **Analyse** `{ key: "cohorte", label: "Cohorte", icon: CandlestickChart }` (import `CandlestickChart` de lucide-react).
- `frontend/src/App.tsx` : `const CohortView = lazy(...)` + branche `tab === "cohorte"`. Hors `showSidebar`.

## Tests

- `lib/cohort.test.ts` :
  - `quantile` sur un échantillon connu (médiane, q1, q3 par interpolation).
  - `computeBoxStats` : IQR, moustaches Tukey, détection d'un outlier ; cas `n===1` (dégénéré).
  - `buildCohort` : tri par médiane décroissante ; exclusion des conditions à `vals` vide.
- `CohortChart.test.tsx` : smoke — montage du `<svg>` avec K lignes (assertion sur le conteneur +
  nombre de groupes de lignes ; la géométrie SVG n'est pas mesurable en jsdom).
- `CohortView.test.tsx` : Loading ; Empty (conditions sans métrique numérique) ; rendu du
  sélecteur + chart avec fixture (mock `apiFetch` pour `/api/runs/conditions` et
  `/api/runs/distributions`) ; changement de métrique re-fetch (mock disambiguïsé par `endsWith`).
- Backend `test_backend.py::test_list_distributions_*` (cf. §1).

## Risques

- **SVG en jsdom** : pas de géométrie mesurable. La logique testée est `lib/cohort.ts` (pur) + le
  câblage `CohortView` (sélecteur → fetch → rendu) ; `CohortChart` = smoke de montage.
- **Petit n** : à n<4 la box est peu informative ; mitigation = strip de tous les points (chaque
  seed visible) + caption `n`. Pas de violin (volontaire).
- **Propagation backend** : l'onglet reste Empty/Error tant que `/api/runs/distributions` n'est pas
  sur `main` (PR d1 + merge d→main). Acceptable, dégradation propre, identique à Sweep.
- **Coordination** : frontend = `frontend/src/**` + `docs/**` uniquement → aucun conflit avec
  `feat/d1-prod-pairing`. Backend = PR séparée dans leur branche.

## Non-objectifs (YAGNI v1)

- Pas de violin (densité par noyau trompeuse à petit n).
- Pas de deep-link au clic d'une condition (la vue est read-only v1).
- Pas de multi-métrique simultanée ni de filtre/sélection de sous-ensemble de conditions.
- Pas de tests statistiques inter-conditions (ANOVA, etc.) — l'A/B pairwise reste la voie du verdict.

## Périmètre des fichiers

Créés (frontend → `main`) : `lib/cohort.ts` (+ test), `components/CohortChart.tsx` (+ test),
`components/CohortView.tsx` (+ test).
Modifiés (frontend → `main`) : `types.ts`, `api/queryKeys.ts`, `tabs.ts`, `App.tsx`.
Backend (→ `feat/d1-prod-pairing`) : `schemas.py`, `services/runs_service.py`, `routes/runs.py`,
`tests/test_backend.py`, régén `openapi.json` + `api/schema.ts`.

## Suite

Plan d'implémentation via `writing-plans`, tâches TDD :
(1) `lib/cohort.ts` pur + types ;
(2) `CohortChart` SVG ;
(3) `CohortView` + sélecteur + états ;
(4) intégration onglet/lazy ;
(5) endpoint backend distributions (patch-and-handoff, PR séparée d1).
Chacune testée.
