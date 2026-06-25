# Décomposition énergétique (mur Lewis) — design

Date : 2026-06-25
Vague : I (pistes net-new) — item I1
Statut : design approuvé, prêt pour le plan d'implémentation.

## Problème

L'énergie exposée au dashboard est grossière (`mean_energy` live + CSV `metacognition_logs`). La
**décomposition du budget énergétique** — qui localise le drain (EDR 099/100 : `bio_metab ≈50×
terrain`, biologie = 90% du drain) — n'existe qu'en sortie console de l'outil offline
`tools/lewis_survival_sweep.py` (`main_decompose`). C'est pourtant le **goulot scientifique vivant**
(mur métabolique de Lewis, pivot acquisition EDR 102) ; il devrait être un instrument, pas un print.

## Objectif

Un onglet **Énergie** : pour chaque run de décomposition (`lewis_drain_decompose_<seed>.json`),
visualiser le budget par tick/agent — les 4 phases (`brain`/`action`/`biologie`/`mouvement`) et la
sous-décomposition biologie (`bio_metab`/`bio_terrain`/`bio_carry`/`bio_autres`) — avec les verdicts
pré-enregistrés. Auto-actualisé : tout nouveau run de décompo apparaît sans curation manuelle.

## Décisions (cadrage validé)

| Sujet | Décision |
|---|---|
| Donnée | Lit les fichiers run dont `data.phases` existe (persistés par `main_decompose` via `Harness.save`). **Nouvel endpoint** `GET /api/runs/decompositions` (patch-and-handoff vers d1, comme `/api/runs/distributions`). |
| Visualisation | Barres (recharts) : budget par phase (% du `net`) + sous-décompo biologie (% du drain bio). Dominant mis en évidence. |
| Verdicts | Affichés tels quels (`verdict`, `bio_verdict`, texte pré-enregistré) — pas de ré-interprétation. |
| Placement | Nouvel onglet `energie`, famille **Analyse** (icône lucide `Zap`). |
| Acquisition/forage | **Différée** : l'artefact `phases` est côté dépense ; le revenu (forage, pivot EDR 102) demande une autre instrumentation. Hors v1. |

## Architecture

### 1. Backend — endpoint decompositions (PR séparée dans `feat/d1-prod-pairing`)

Un run de décompo = fichier `results/lewis_drain_decompose_<seed>.json` :
`{name, seed, commit, data: {phases: {...}, verdict, bio_verdict, R, n_eval}}`. `phases` est un dict
**plat** : `brain, action, biologie, mouvement, net, n_agents, bio_metab, bio_terrain, bio_carry,
bio_autres` (floats ; `n_agents` entier).

- `backend/app/schemas.py` :
  ```python
  class EnergyPhases(BaseModel):
      brain: float
      action: float
      biologie: float
      mouvement: float
      net: float
      n_agents: float
      bio_metab: float
      bio_terrain: float
      bio_carry: float
      bio_autres: float

  class Decomposition(BaseModel):
      run_id: str
      name: str
      seed: int
      commit: str | None = None
      phases: EnergyPhases
      verdict: str
      bio_verdict: str
  ```
- `runs_service.list_decompositions() -> list[dict]` : pour chaque run de `_scan()` dont
  `isinstance(r["data"].get("phases"), dict)` et dont les 10 clés de phase sont présentes, émettre
  `{run_id: r["_run_id"], name, seed, commit, phases, verdict: data.get("verdict",""),
  bio_verdict: data.get("bio_verdict","")}`. Trié par `run_id`.
- `backend/app/routes/runs.py` : `@router.get("/runs/decompositions", response_model=list[Decomposition])`
  **avant** la route générique `/runs/{run_id}`.
- `tests/test_backend.py` (racine) : écrit un fichier `lewis_drain_decompose_7.json` avec un `phases`
  complet + un run scalaire (ignoré) ; vérifie `len==1`, `phases.bio_metab`, `verdict`.
- Régénérer `frontend/openapi.json` + `frontend/src/api/schema.ts` (drift gate).

### 2. Frontend — types & clés

- `frontend/src/types.ts` :
  ```ts
  export interface EnergyPhases {
    brain: number; action: number; biologie: number; mouvement: number;
    net: number; n_agents: number;
    bio_metab: number; bio_terrain: number; bio_carry: number; bio_autres: number;
  }
  export interface Decomposition {
    run_id: string; name: string; seed: number; commit?: string | null;
    phases: EnergyPhases; verdict: string; bio_verdict: string;
  }
  ```
- `frontend/src/api/queryKeys.ts` : `decompositions: ["runs", "decompositions"] as const` dans `runs`.

### 3. `lib/energy.ts` (pur, testable)

```ts
import type { EnergyPhases } from "../types";

export interface EnergyBar { name: string; value: number; pct: number }

/** 4 phases en part du net (tri décroissant). Si net == 0, pct = 0. */
export function buildPhaseBreakdown(phases: EnergyPhases): EnergyBar[];

/** 4 composantes biologie en part du drain bio (somme des 4). Si somme == 0, pct = 0. Tri décroissant. */
export function buildBioBreakdown(phases: EnergyPhases): EnergyBar[];
```

- Phases : clés `brain/action/biologie/mouvement`, libellés FR identiques ; `pct = 100*value/net`.
- Bio : clés `bio_metab/bio_terrain/bio_carry/bio_autres`, libellés FR (`métab`, `terrain`, `port`,
  `autres`) ; `bioNet = somme des 4` ; `pct = 100*value/bioNet`. Pur, aucun effet de bord.

### 4. `components/EnergyChart.tsx`

`EnergyChart({ bars, title, unit }: { bars: EnergyBar[]; title: string; unit: string })` :
recharts `BarChart` horizontal (une barre par composante, `value`), couleurs `vizColors()` cyclées,
libellé `value` + `pct%` par barre, `aria-label` FR, `isAnimationActive={false}`. Réutilisé pour
les phases ET la sous-décompo biologie.

### 5. `components/EnergyView.tsx`

- `useQuery(queryKeys.runs.decompositions, () => apiFetch<Decomposition[]>("/api/runs/decompositions"))`.
- Sélecteur de run décompo (`Field` + `<select>`, défaut = 1ᵉʳ ; état dérivé comme CohortView).
- États Loading / ErrorState(onRetry) / Empty (« Aucune décomposition énergétique. Lance
  `python tools/lewis_survival_sweep.py` (`main_decompose`) côté backend. »).
- Rendu : titre, sélecteur, bandeau **verdicts** (`verdict` phases + `bio_verdict`), deux `Panel` —
  `EnergyChart` phases (« Budget par phase », unité « énergie/tick/agent ») et `EnergyChart` bio
  (« Sous-décomposition biologie »). Caption `net`/`n_agents`.

### 6. Intégration

- `frontend/src/tabs.ts` : clé `"energie"` (après `"cohorte"`) + entrée famille **Analyse**
  `{ key: "energie", label: "Énergie", icon: Zap }` (import `Zap` de lucide-react).
- `frontend/src/App.tsx` : lazy `EnergyView` + branche `tab === "energie"`. Hors `showSidebar`.

## Tests

- Backend : `test_list_decompositions_*` — fichier décompo → 1 `Decomposition` (phases/verdict) ; run
  scalaire ignoré.
- `lib/energy.test.ts` : `buildPhaseBreakdown` (pct du net, tri décroissant, net=0 → pct 0) ;
  `buildBioBreakdown` (pct du drain bio, somme=0 → pct 0).
- `EnergyChart.test.tsx` : smoke — `.recharts-responsive-container` monté avec N barres.
- `EnergyView.test.tsx` : Empty (aucune décompo) ; rendu sélecteur + 2 charts + verdicts (fixture) ;
  changement de run met à jour. Mock `apiFetch`.

## Risques

- **recharts en jsdom** : pas de géométrie → logique testée = `lib/energy.ts` (pur) + câblage
  `EnergyView` ; `EnergyChart` = smoke.
- **Propagation backend** : tant que `/api/runs/decompositions` n'est pas sur `main`, l'onglet dégrade
  en Empty/Error. Identique à Cohorte/Carnet.
- **Rareté des données** : peu de runs décompo en pratique (N_APEX=0, coûteux) → souvent 1-N runs.
  Acceptable ; l'Empty oriente vers l'outil.
- **Coordination** : frontend `frontend/src/**` + `docs/**` ; backend PR séparée dans
  `feat/d1-prod-pairing`. Aucun conflit.

## Non-objectifs (YAGNI v1)

- Revenu / acquisition (forage) — instrumentation côté gains, pivot EDR 102, autre artefact.
- Série temporelle par tick (l'artefact est un agrégat).
- Superposition multi-décompo, normalisation, comparaison inter-runs.

## Périmètre des fichiers

Frontend (→ `main`) — Créés : `lib/energy.ts` (+ test), `components/EnergyChart.tsx` (+ test),
`components/EnergyView.tsx` (+ test). Modifiés : `types.ts`, `api/queryKeys.ts`, `tabs.ts`, `App.tsx`.
Backend (→ `feat/d1-prod-pairing`) : `backend/app/schemas.py`, `backend/app/services/runs_service.py`,
`backend/app/routes/runs.py`, `tests/test_backend.py` (racine), régén `frontend/openapi.json` +
`frontend/src/api/schema.ts`.

## Suite

Plan d'implémentation via `writing-plans`, tâches TDD :
(1) types + queryKeys + `lib/energy.ts` ;
(2) `EnergyChart` ;
(3) `EnergyView` + sélecteur + états ;
(4) intégration onglet/lazy ;
(5) backend endpoint decompositions (patch-and-handoff d1).
Chacune testée.
