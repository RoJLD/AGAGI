# Entonnoir de forage (acquisition) — design

Date : 2026-06-25
Vague : I (pistes net-new) — item I5
Statut : design approuvé, prêt pour le plan d'implémentation.

## Problème

Le mur métabolique de Lewis (dépense) est clos (chaîne 090-101) ; le goulot vivant a pivoté vers
l'**acquisition** (EDR 105 : `p_reach=0.18`, `p_cap=1.00` → le mur est la **navigation/approche**, pas
la capture ni le revenu). L'outil `tools/lewis_survival_sweep.py` (`main_forage`) décompose cet
entonnoir mais n'en sort qu'une table console. C'est le **pendant acquisition de I1** (qui décompose
la dépense) : il devrait être un instrument vivant.

## Objectif

Un onglet **Forage** : pour chaque run d'entonnoir (`lewis_forage_funnel_<seed>.json`), visualiser par
niveau de métab l'acquisition — **atteinte** (`p_reach`) → **capture si atteint** (`p_cap`) → capture
globale (produit), + revenu/drain et contacts/distance, avec le verdict pré-enregistré.

## Décisions (cadrage validé)

| Sujet | Décision |
|---|---|
| Donnée | Lit les runs dont `data.table` (dict par niveau) + `data.metab_levels` existent. **Nouvel endpoint** `GET /api/runs/forage-funnels` (patch-and-handoff vers d1, comme `/api/runs/decompositions`). |
| Visualisation | 3 barres par niveau : atteinte / capture-si-atteint / capture-globale (= produit). **Pas un entonnoir décroissant strict** (`p_cap` conditionnel peut dépasser `p_reach`) → libellés honnêtes. |
| Verdict | Affiché tel quel (`verdict`, prose pré-enregistrée). |
| Placement | Nouvel onglet `forage`, famille **Analyse** (icône lucide `Crosshair`). |

## Architecture

### 1. Backend — endpoint forage-funnels (PR séparée dans `feat/d1-prod-pairing`)

Un run d'entonnoir = `results/lewis_forage_funnel_<seed>.json` :
`{name, seed, commit, data: {knob: "base_metab", metab_levels: [float], verdict, R, n_eval, table:
{"<metab>": agg}}}`. Chaque `agg` = `{p_reach, p_cap, income_t, drain_t, mean_captures, mean_contacts,
mean_min_dist, n_agents}` (floats ; `n_agents` entier). Les clés de `table` sont `str(metab_level)`.

- `backend/app/schemas.py` :
  ```python
  class ForageLevel(BaseModel):
      metab: float
      p_reach: float
      p_cap: float
      income_t: float
      drain_t: float
      mean_captures: float
      mean_contacts: float
      mean_min_dist: float
      n_agents: float

  class ForageFunnel(BaseModel):
      run_id: str
      name: str
      seed: int
      commit: str | None = None
      verdict: str
      levels: list[ForageLevel]
  ```
- `runs_service.list_forage_funnels() -> list[dict]` : pour chaque run de `_scan()` dont
  `isinstance(data.get("table"), dict)` ET `isinstance(data.get("metab_levels"), list)`, construire
  `levels` en parcourant `metab_levels` (clé `table[str(lv)]`, ne garder que les aggs dict contenant
  `p_reach`) ; émettre `{run_id: _run_id, name, seed, commit, verdict: data.get("verdict",""), levels}`
  si au moins un niveau valide. Trié par `run_id`.
- `backend/app/routes/runs.py` : `@router.get("/runs/forage-funnels", response_model=list[ForageFunnel])`
  **avant** la route générique `/runs/{run_id}`.
- `tests/test_backend.py` (racine) : écrit un fichier `lewis_forage_funnel_7.json` avec `table` à 2
  niveaux + un run scalaire (ignoré) ; vérifie `len==1`, `levels[0].p_reach`, `verdict`, l'ordre des
  niveaux.
- Régénérer `frontend/openapi.json` + `frontend/src/api/schema.ts` (drift gate).

### 2. Frontend — types & clés

- `frontend/src/types.ts` :
  ```ts
  export interface ForageLevel {
    metab: number; p_reach: number; p_cap: number; income_t: number; drain_t: number;
    mean_captures: number; mean_contacts: number; mean_min_dist: number; n_agents: number;
  }
  export interface ForageFunnel {
    run_id: string; name: string; seed: number; commit?: string | null;
    verdict: string; levels: ForageLevel[];
  }
  ```
- `frontend/src/api/queryKeys.ts` : `forageFunnels: ["runs", "forage-funnels"] as const` dans `runs`.

### 3. `lib/forage.ts` (pur, testable)

```ts
import type { ForageLevel } from "../types";

export interface ForageBar { name: string; value: number; pct: number }

/** 3 étages d'acquisition d'un niveau : atteinte (p_reach), capture-si-atteint (p_cap),
 *  capture globale (= p_reach × p_cap). `value` ∈ [0,1], `pct` = value × 100. */
export function buildFunnelStages(level: ForageLevel): ForageBar[];
```

- `global = p_reach * p_cap` ; trois barres dans l'ordre fixe (atteinte, capture-si-atteint, globale).
  Pas de tri (l'ordre raconte la cascade). Pur, aucun effet de bord.

### 4. `components/ForageFunnelChart.tsx`

`ForageFunnelChart({ bars, title }: { bars: ForageBar[]; title: string })` : barres recharts
horizontales (même moule que `EnergyChart` : `BarChart layout="vertical"`, `Cell` couleurs
`vizColors()` cyclées, `LabelList` du `pct`, axes), `isAnimationActive={false}`, domaine X `[0,1]`.
Zéro `any`, libellés FR.

### 5. `components/ForageFunnelView.tsx`

- `useQuery(queryKeys.runs.forageFunnels, () => apiFetch<ForageFunnel[]>("/api/runs/forage-funnels"))`.
- Sélecteur de run (`current = funnels.find(run_id===selId) ?? funnels[0]`, pattern SweepView v1).
- États Loading / ErrorState(onRetry) / Empty (« Aucun entonnoir de forage. Lance
  `python tools/lewis_survival_sweep.py` (`main_forage`) côté backend. »).
- Rendu : titre, sélecteur, bandeau **verdict**, puis **un bloc par niveau de métab** : `Panel` avec
  `ForageFunnelChart` (`buildFunnelStages(level)`, titre `métab <metab>`) + caption
  `income/tick`, `drain/tick`, `contacts`, `min_dist`, `n_agents`.

### 6. Intégration

- `frontend/src/tabs.ts` : clé `"forage"` (après `"energie"`) + entrée famille **Analyse**
  `{ key: "forage", label: "Forage", icon: Crosshair }` (import `Crosshair` de lucide-react).
- `frontend/src/App.tsx` : lazy `ForageFunnelView` + branche `tab === "forage"`. Hors `showSidebar`.

## Tests

- Backend : `test_list_forage_funnels_*` — fichier entonnoir (2 niveaux) → 1 `ForageFunnel`
  (levels/verdict, ordre métab) ; run scalaire ignoré.
- `lib/forage.test.ts` : `buildFunnelStages` (3 barres, valeurs/ordre, `global = p_reach*p_cap`,
  `pct = value*100`).
- `ForageFunnelChart.test.tsx` : smoke — `.recharts-responsive-container` monté.
- `ForageFunnelView.test.tsx` : Empty (aucun entonnoir) ; rendu sélecteur + verdict + 1 chart par
  niveau (fixture 2 niveaux → 2 conteneurs) ; changement de run. Mock `apiFetch`.

## Risques

- **recharts en jsdom** : pas de géométrie → logique testée = `lib/forage.ts` (pur) + câblage
  `ForageFunnelView` ; `ForageFunnelChart` = smoke.
- **Propagation backend** : tant que `/api/runs/forage-funnels` n'est pas sur `main`, l'onglet dégrade
  en Empty/Error. Identique à I1/Cohorte.
- **Rareté des données** : peu de runs d'entonnoir (N_APEX=0, coûteux). Acceptable ; l'Empty oriente.
- **Coordination** : frontend `frontend/src/**` + `docs/**` ; backend PR séparée. Aucun conflit.

## Non-objectifs (YAGNI v1)

- Trajectoires de navigation / heatmap spatiale (pas de données spatiales persistées).
- Superposition multi-runs, série temporelle, comparaison inter-runs.
- Réinterprétation du verdict (prose pré-enregistrée).

## Périmètre des fichiers

Frontend (→ `main`) — Créés : `lib/forage.ts` (+ test), `components/ForageFunnelChart.tsx` (+ test),
`components/ForageFunnelView.tsx` (+ test). Modifiés : `types.ts`, `api/queryKeys.ts`, `tabs.ts`, `App.tsx`.
Backend (→ `feat/d1-prod-pairing`) : `backend/app/schemas.py`, `backend/app/services/runs_service.py`,
`backend/app/routes/runs.py`, `tests/test_backend.py` (racine), régén `frontend/openapi.json` +
`frontend/src/api/schema.ts`.

## Suite

Plan d'implémentation via `writing-plans`, tâches TDD :
(1) types + queryKeys + `lib/forage.ts` ;
(2) `ForageFunnelChart` ;
(3) `ForageFunnelView` + sélecteur + états ;
(4) intégration onglet/lazy ;
(5) backend endpoint forage-funnels (patch-and-handoff d1).
Chacune testée.
