# Vue Sweep — paysage de paramètres (design)

Date : 2026-06-24
Statut : design approuvé, prêt pour le plan d'implémentation.

## Problème

La session backend produit une rafale de **sweeps** (`lewis_survival_sweep`, `lewis_apex_sweep`,
`metabolic_cost_sweep`, `lethality_curriculum`…) qui balaient un paramètre. Le frontend ne sait
comparer que **2 conditions** (`/runs/compare`, A/B pairwise) ; il n'existe **aucune vue traçant une
métrique le long d'un paramètre balayé**. Or trouver le **premier barreau survivable** (goulot #1 du
projet, EDR 014/090) se lit comme une courbe survie-vs-paramètre, pas comme un A/B binaire.

### Réalité des données (audit)

- `results/` est **gitignored** (données générées au runtime, sur le tree backend).
- Un sweep s'écrit via `Harness.save(data)` → `results/<name>_<seed>.json` =
  `{name, seed, commit, git_dirty, data, [config_hash]}`, où `data` contient des **tableaux
  parallèles** (ex. `lewis_survival_sweep` : `{knob:"forage_payoff", levels:[…], medians:[…], R, n_eval}`).
- Ces tableaux sont **invisibles** à la machinerie A/B : `runs_service._numeric_metrics` ne retient
  que les **scalaires**. → un endpoint dédié est nécessaire.

## Objectif

Un onglet **Sweeps** qui trace une métrique (ex. survie médiane) le long du paramètre balayé
(`knob`), avec bande de variance si disponible. Réutilise recharts (déjà dép, déjà lazy-chunké) et
les primitives existantes. Additif ; ne touche pas l'A/B.

## Décisions (cadrage validé)

| Sujet | Décision |
|---|---|
| Dépendance backend | Contrat d'endpoint défini ici ; **frontend bâti sur fixture** conforme ; **patch backend préparé et remis** à la session parallèle (PR dans `feat/d1-prod-pairing`). Le front ne dépend pas du merge ; onglet `Empty` tant que l'endpoint n'existe pas. |
| Placement | Nouvel onglet `sweeps` dans la famille **Analyse**. |
| Chart | recharts `LineChart` + bande de variance (`Area` ±std) si `y_std` présent. |
| v1 scope | **Un sweep à la fois** (sélecteur). Superposition multi-knob = enhancement futur (YAGNI). |

## Contrat backend

```
GET /api/sweeps → SweepResult[]
SweepResult = {
  run_id: string;
  name: string;
  knob: string;            // nom du paramètre balayé (axe X)
  x: number[];             // valeurs du paramètre (= data.levels)
  series: Record<string, number[]>;     // chaque métrique Y de même longueur que x
  y_std?: Record<string, number[]>;     // spread optionnel par métrique (même longueur)
  seed: number;
  commit?: string | null;
}
```

**Règle d'identification (backend)** : un run est un *sweep* si `data.knob` est une `str` ET
`data.levels` est un tableau numérique (→ `x`). Chaque autre tableau **numérique de même longueur**
que `levels` devient une série dans `series` (clé = nom du champ). Un champ `<metric>_std` (ou
`<metric>_spread`) de même longueur alimente `y_std[<metric>]`. Convention documentée dans le patch ;
les sweeps qui ne la respectent pas n'apparaissent simplement pas (dégradation silencieuse acceptable).

## Architecture

### Backend (patch remis — hors merge de cette branche frontend)
- `backend/app/services/runs_service.py` : `list_sweeps() -> list[dict]` (lecture seule, scanne
  `results/`, applique la règle ci-dessus).
- `backend/app/routes/runs.py` : `@router.get("/sweeps", response_model=list[SweepResult])`.
- Modèle Pydantic `SweepResult` (précise le codegen TS).
- Test pytest `test_list_sweeps` (fixture run sweep en `tmp_path`).
- Livré comme **document de patch** (`scratchpad/`) + PR dans `feat/d1-prod-pairing` ; la session
  parallèle l'applique. Zéro fichier backend modifié sur la branche frontend.

### Frontend
- `frontend/src/tabs.ts` : clé `"sweeps"` + entrée famille Analyse (icône lucide `Spline`).
- `frontend/src/types.ts` : interface `SweepResult` (miroir du contrat, en attendant `schema.ts`).
- `frontend/src/api/queryKeys.ts` : clé `sweeps`.
- `frontend/src/components/SweepView.tsx` : `useQuery(/api/sweeps)` ; sélecteur de sweep (par
  `name`/`knob`) ; sélecteur de série Y (si `Object.keys(series).length > 1`) ; états
  Loading/ErrorState/Empty ; rend `<SweepChart>`. Lazy-loadé dans `App.tsx`.
- `frontend/src/components/SweepChart.tsx` : recharts `LineChart` — X = `x` (label `knob`), Y =
  série choisie ; si `yStd` fourni → `Area` de bande (`y-std`..`y+std`) sous la ligne ; axes
  labellés ; couleurs via `theme.ts` (`cssVar`/`vizColors`). Props `{ x, knob, metric, y, yStd? }`.

### Données / flux
Aucun endpoint existant modifié. `/api/sweeps` (nouveau, côté patch). react-query met en cache par
`queryKeys.sweeps`. Onglet `sweeps` hors `showSidebar` (pleine largeur).

## Tests

- `SweepView` (`SweepView.test.tsx`) : Loading ; Empty (réponse `[]`) ; avec fixture (1 sweep,
  ≥1 série) → sélecteurs rendus + `SweepChart` monté ; changement de série met à jour le chart.
- `SweepChart` (`SweepChart.test.tsx`) : monte avec `x`/`y` ; rend la bande quand `yStd` fourni,
  ligne seule sinon (assertions sur labels d'axe/série, pas pixels — recharts en jsdom via
  `ResponsiveContainer` largeur 0 ne trace pas de path mesurable).
- Backend : `test_list_sweeps` (dans le patch) — un run sweep en `tmp_path` → 1 `SweepResult` avec
  `x`/`series` corrects ; un run scalaire normal → ignoré.

## Risques

- **recharts en jsdom** : pas de rendu pixel mesurable (largeur 0). Mitigation : tester câblage
  données/sélecteurs/labels + montage, pas la géométrie du tracé.
- **Frontière backend** : front sur fixture ; données réelles au merge du patch. Onglet `Empty`
  gracieux entre-temps. Le patch respecte la frontière (PR dans leur branche, pas de push direct).
- **Convention `knob`/`levels`** : couplage aux noms de champs. Documentée ; sweeps non conformes
  absents (pas d'erreur).
- **Coordination session parallèle** : branche frontend = `frontend/src/**` + `docs/**` uniquement ;
  le patch backend est un artefact séparé remis, pas committé ici.

## Non-objectifs (YAGNI)

- Pas de superposition multi-sweep/multi-knob en v1 (enhancement futur).
- Pas de modification des sweeps backend pour normaliser leur sortie (la règle s'adapte à l'existant
  `knob/levels`).
- Pas de refonte de l'A/B ni de la vue Comparaison.

## Suite

Plan d'implémentation via `writing-plans`, découpé en tâches TDD : (1) contrat de types + fixture ;
(2) `SweepChart` ; (3) `SweepView` + états ; (4) intégration onglet/lazy ; (5) document de patch
backend + test pytest (remis à la session parallèle). Chacune testée.
