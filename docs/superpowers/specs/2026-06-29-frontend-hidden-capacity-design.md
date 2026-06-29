# Capacité cachée dans Comparaison + Radar (J1a) — design

Date : 2026-06-29
Vague : J (audit transverse) — item J1, tranche J1a (quick win).
Statut : design approuvé, prêt pour le plan d'implémentation.

## Problème

Le goulot scientifique a re-pivoté vers l'**architecture du connectome** (EDR 107 : `p_reach` plafonne
~0.36 même après ré-évolution de la navigation → substrat bloqué ; EDR 108 NAS : « la capacité cachée
monte-t-elle le plafond ? »). Le frontend expose `hidden_ratio` et `num_nodes` dans le type
`ExperimentSummary` (déjà servis par `/api/experiments`), mais **ne les affiche nulle part** : ni dans
la `ComparisonView` (cartes par porte), ni comme axe du `RadarChart`. La comparaison cross-gate de la
capacité cachée — première lecture utile pour EDR 108 — est donc invisible.

## Objectif

Rendre `hidden_ratio` et `num_nodes` visibles dans la comparaison cross-gate. **Frontend-only**, zéro
dépendance backend (champs déjà exposés). Tranche J1a (quick win) ; J1b (vue Introspection) et J1c/J1d
(backend-gated) restent des cycles ultérieurs.

## Contexte du code (grounded)

- `frontend/src/types.ts` : `ExperimentSummary` contient déjà `num_nodes?: number`, `hidden_ratio?:
  number`, `sparsity?: number` (tous optionnels).
- `frontend/src/components/RadarChart.tsx` : tableau `metrics` de 5 axes codé en dur
  (`latest_fitness`, `latest_accuracy`, `emergent_score`, `performance_stability`, `robustness_score`),
  chacun avec `key`/`label`/`maxScale`. Le rendu (polygones + cercles) boucle génériquement sur
  `metrics` via `experiment[metric.key] ?? 0`, normalisé par un objet `maxValues` indexé par `metric.key`.
- `frontend/src/components/ComparisonView.tsx` : chaque `comparison-card` affiche fitness, précision, et
  (sous garde `!== undefined`) robustesse et stabilité.

## Décisions (cadrage validé)

| Sujet | Décision |
|---|---|
| Métriques affichées | `hidden_ratio` (ratio ∈[0,1]) **et** `num_nodes` (entier). Pas d'autres (YAGNI). |
| Radar | Ajouter `hidden_ratio` comme **6ᵉ axe** (ratio → `maxScale 1.0`, normalisé par 1 comme `latest_accuracy`). `num_nodes` n'est PAS un axe radar (échelle non bornée [0,1] → fausserait le polygone). |
| ComparisonView | Ajouter `hidden_ratio` et `num_nodes` aux cartes, sous garde `!== undefined` (même pattern que robustesse/stabilité). |
| Backend | Aucune touche. Données déjà servies. |

## Architecture

### 1. RadarChart.tsx

- Ajouter au tableau `metrics`, après `robustness_score` :
  ```ts
  { key: "hidden_ratio" as const, label: "Ratio caché", maxScale: 1.0 },
  ```
- Ajouter à l'objet `maxValues` la clé correspondante :
  ```ts
  hidden_ratio: 1,
  ```
  **Garde-fou critique** : sans cette clé, `(experiment[metric.key] ?? 0) / maxValues[metric.key]`
  diviserait par `undefined` → `NaN` → polygone cassé. La clé `maxValues.hidden_ratio` est donc
  obligatoire et normalise sur `[0,1]` (le ratio est déjà borné).
- Aucun autre changement : le rendu des axes/polygones/cercles boucle déjà sur `metrics`.

### 2. ComparisonView.tsx

Dans chaque `comparison-card`, après la ligne `performance_stability`, ajouter :

```tsx
{item.hidden_ratio !== undefined && <span>Ratio caché: {item.hidden_ratio.toFixed(3)}</span>}
{item.num_nodes !== undefined && <span>Nœuds: {item.num_nodes}</span>}
```

## Flux de données

Inchangé : `useQuery` sur `/api/experiments` → `ExperimentSummary[]`. Les champs `hidden_ratio` /
`num_nodes` sont déjà dans la réponse ; on les lit, on ne les fetch pas différemment.

## Tests

- **`RadarChart.test.tsx`** (nouveau) : rendre un `RadarChart` avec un `ExperimentSummary` (incluant
  `hidden_ratio`), asserter que le texte d'axe **« Ratio caché »** est rendu, ainsi que les 5 libellés
  existants (« Fitness », « Précision », « Intelligence », « Stabilité », « Robustesse »). SVG testable
  via `getByText` sur les `<text>` d'axe.
- **`ComparisonView.test.tsx`** (existant, étendu) : avec un `ExperimentSummary` portant `hidden_ratio`
  et `num_nodes`, asserter qu'une carte affiche « Ratio caché » et « Nœuds » ; avec un summary SANS ces
  champs, asserter leur **absence** (non-régression de la garde `!== undefined`).

## Risques

- **`NaN` radar si `maxValues.hidden_ratio` oublié** : explicitement couvert par la décision (garde-fou)
  et par le test radar (un axe rendu n'implique pas un polygone correct, mais l'oubli ferait planter le
  rendu ou produire un point hors-grille visible). Mitigation : la spec impose la clé `maxValues`.
- **`hidden_ratio` absent pour certaines portes** : optionnel → l'axe radar lit `?? 0` (point au
  centre) et la carte masque la ligne (garde). Comportement gracieux, identique à `emergent_score`.

## Non-objectifs (YAGNI)

- J1b (vue Introspection `w_connectome`) : cycle séparé.
- Aucune touche backend ; pas de nouvel endpoint ; pas de KPI sauvegardé (J1d).
- Pas d'autres métriques de connectome (`sparsity`, `num_edges`, `modularity`…) — hors besoin EDR 108.
- Pas de refonte de la mise en page du radar ni des cartes.

## Périmètre des fichiers

Frontend-only (→ `main`). Modifiés : `frontend/src/components/RadarChart.tsx` (1 axe + 1 clé maxValues),
`frontend/src/components/ComparisonView.tsx` (2 spans). Tests : `frontend/src/components/RadarChart.test.tsx`
(créé), `frontend/src/components/ComparisonView.test.tsx` (étendu).

## Suite

Plan d'implémentation via `writing-plans`, probablement **une seule tâche TDD** (radar + view + 2 tests).
