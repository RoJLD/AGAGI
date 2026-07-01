# Capacité cachée dans Comparaison + Radar (J1a) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Afficher `hidden_ratio` (axe radar + carte) et `num_nodes` (carte) dans la comparaison cross-gate, pour servir EDR 108 (capacité cachée), à partir de champs déjà exposés par `/api/experiments`.

**Architecture:** Frontend-only, zéro changement de flux de données. `RadarChart` gagne un 6ᵉ axe `hidden_ratio` (1 entrée `metrics` + 1 clé `maxValues`, garde-fou anti-`NaN`). `ComparisonView` gagne 2 spans sous garde `!== undefined`. Deux tests : un nouveau pour le radar, une extension de l'existant pour la vue.

**Tech Stack:** React 18 + TypeScript strict + Vitest + Testing Library.

## Global Constraints

- **Frontend-only**, sur `feat/frontend-hidden-capacity` → PR vers `main`. Aucune touche backend.
- **Langue** : libellés/commentaires en français.
- **Pas d'emoji** dans le code ni les commits.
- **TypeScript** : zéro `any`, types explicites.
- **`hidden_ratio`** = ratio ∈[0,1] → axe radar normalisé par `maxValues.hidden_ratio = 1`. **Sans cette clé, le rendu divise par `undefined` → `NaN`** : la clé est obligatoire.
- **`num_nodes`** n'est PAS un axe radar (échelle non bornée) — uniquement une ligne de carte.
- Champs lus sous garde `!== undefined` (pattern existant `robustness_score`/`performance_stability`).
- **Commits** : chaque commit se termine par le trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Tests** depuis `frontend/` : `npx vitest run <chemin>` ; type-check `npx tsc --noEmit`. Un seul appel bash composé (`cd frontend && ...`).

---

### Task 1: Axe radar `hidden_ratio` + cartes Comparaison (`hidden_ratio`, `num_nodes`)

**Files:**
- Modify: `frontend/src/components/RadarChart.tsx` (tableau `metrics` + objet `maxValues`)
- Modify: `frontend/src/components/ComparisonView.tsx` (2 spans dans `comparison-card`)
- Create: `frontend/src/components/RadarChart.test.tsx`
- Test: `frontend/src/components/ComparisonView.test.tsx` (existant, étendu)

**Interfaces:**
- Consumes: `ExperimentSummary` de `../types` — possède déjà `hidden_ratio?: number` et `num_nodes?: number` (optionnels). `RadarChart({ experiments }: { experiments: ExperimentSummary[] })`. `ComparisonView` lit `experiments` via `useQuery` sur `/api/experiments`.
- Produces: un axe radar « Ratio caché » ; deux lignes de carte « Ratio caché » / « Nœuds ».

- [ ] **Step 1: Écrire le test radar qui échoue**

Créer `frontend/src/components/RadarChart.test.tsx` :

```tsx
import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, test, expect } from "vitest";
import { RadarChart } from "./RadarChart";
import type { ExperimentSummary } from "../types";

afterEach(() => cleanup());

const EXP: ExperimentSummary[] = [
  {
    gate: "AND",
    latest_fitness: 0.8,
    latest_accuracy: 0.9,
    emergent_score: 0.5,
    performance_stability: 0.7,
    robustness_score: 0.6,
    hidden_ratio: 0.12,
    num_nodes: 172,
  },
];

test("le radar rend l'axe Ratio caché en plus des 5 axes existants", () => {
  render(<RadarChart experiments={EXP} />);
  expect(screen.getByText("Ratio caché")).toBeTruthy();
  expect(screen.getByText("Fitness")).toBeTruthy();
  expect(screen.getByText("Précision")).toBeTruthy();
  expect(screen.getByText("Intelligence")).toBeTruthy();
  expect(screen.getByText("Stabilité")).toBeTruthy();
  expect(screen.getByText("Robustesse")).toBeTruthy();
});
```

- [ ] **Step 2: Lancer le test radar pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/components/RadarChart.test.tsx`
Expected : FAIL (« Ratio caché » introuvable — l'axe n'existe pas encore).

- [ ] **Step 3: Ajouter l'axe `hidden_ratio` au `RadarChart`**

Dans `frontend/src/components/RadarChart.tsx`, dans le tableau `metrics`, ajouter une 6ᵉ entrée après `robustness_score` :

```ts
const metrics = [
  { key: "latest_fitness" as const, label: "Fitness", maxScale: 1.0 },
  { key: "latest_accuracy" as const, label: "Précision", maxScale: 1.0 },
  { key: "emergent_score" as const, label: "Intelligence", maxScale: 1.0 },
  { key: "performance_stability" as const, label: "Stabilité", maxScale: 1.0 },
  { key: "robustness_score" as const, label: "Robustesse", maxScale: 1.0 },
  { key: "hidden_ratio" as const, label: "Ratio caché", maxScale: 1.0 },
];
```

Puis, dans l'objet `maxValues` (à l'intérieur de `RadarChart`), ajouter la clé `hidden_ratio` (garde-fou anti-`NaN` ; le ratio est borné [0,1] → normaliser par 1, comme `latest_accuracy`) :

```ts
  const maxValues = {
    latest_fitness: Math.max(...experiments.map((item) => item.latest_fitness), 1),
    latest_accuracy: 1,
    emergent_score: Math.max(...experiments.map((item) => item.emergent_score ?? 0), 1),
    performance_stability: Math.max(...experiments.map((item) => item.performance_stability ?? 0), 1),
    robustness_score: Math.max(...experiments.map((item) => item.robustness_score ?? 0), 1),
    hidden_ratio: 1,
  };
```

Aucun autre changement : le rendu des axes, polygones et cercles boucle déjà génériquement sur `metrics` via `experiment[metric.key] ?? 0` et `maxValues[metric.key]`.

- [ ] **Step 4: Lancer le test radar pour vérifier le succès**

Run : `cd frontend && npx vitest run src/components/RadarChart.test.tsx`
Expected : PASS (1 test).

- [ ] **Step 5: Étendre le test `ComparisonView` (échec)**

Le fichier existant possède déjà : `vi.mock("../api/client", …)` + `import { apiFetch }`, un helper `renderWithClient(ui)`, et stube `RadarChart`/`ComparisonChart`/`ABComparisonView` (les cartes `comparison-card` sont donc rendues par `ComparisonView` lui-même, non stubées). **Réutilise ce harnais** (ne crée pas de second mock). Ajouter ce test à la fin du fichier :

```tsx
test("la carte affiche Ratio caché et Nœuds quand présents, les masque sinon", async () => {
  window.location.hash = "#/comparison"; // mode global (sans ?ab=) -> les cartes sont rendues
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue([
    { gate: "AND", latest_fitness: 0.8, latest_accuracy: 0.9, hidden_ratio: 0.12, num_nodes: 172 },
    { gate: "OR", latest_fitness: 0.7, latest_accuracy: 0.85 },
  ]);
  renderWithClient(<ComparisonView />);
  expect(await screen.findByText(/Ratio caché: 0\.120/)).toBeTruthy();
  expect(screen.getByText(/Nœuds: 172/)).toBeTruthy();
  // La porte OR n'a ni hidden_ratio ni num_nodes -> une seule occurrence de chaque libellé.
  expect(screen.getAllByText(/Ratio caché:/).length).toBe(1);
  expect(screen.getAllByText(/Nœuds:/).length).toBe(1);
});
```

(`(0.12).toFixed(3) === "0.120"`. Le mode global est garanti par le hash sans `?ab=`.)

- [ ] **Step 6: Lancer le test `ComparisonView` pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/components/ComparisonView.test.tsx`
Expected : FAIL (« Ratio caché: 0.120 » / « Nœuds: 172 » introuvables — non encore rendus).

- [ ] **Step 7: Ajouter les 2 spans aux cartes `ComparisonView`**

Dans `frontend/src/components/ComparisonView.tsx`, dans le `map` des `comparison-card`, après la ligne `performance_stability`, ajouter :

```tsx
                {item.hidden_ratio !== undefined && <span>Ratio caché: {item.hidden_ratio.toFixed(3)}</span>}
                {item.num_nodes !== undefined && <span>Nœuds: {item.num_nodes}</span>}
```

La carte devient :

```tsx
              <div key={item.gate} className="comparison-card">
                <strong>{item.gate}</strong>
                <span>Fitness: {item.latest_fitness.toFixed(3)}</span>
                <span>Précision: {formatPercentage(item.latest_accuracy)}</span>
                {item.robustness_score !== undefined && <span>Robustesse: {item.robustness_score.toFixed(3)}</span>}
                {item.performance_stability !== undefined && <span>Stabilité: {item.performance_stability.toFixed(3)}</span>}
                {item.hidden_ratio !== undefined && <span>Ratio caché: {item.hidden_ratio.toFixed(3)}</span>}
                {item.num_nodes !== undefined && <span>Nœuds: {item.num_nodes}</span>}
              </div>
```

- [ ] **Step 8: Vérifier le test `ComparisonView`, le typage et toute la suite**

Run : `cd frontend && npx vitest run src/components/ComparisonView.test.tsx`
Expected : PASS.

Run : `cd frontend && npx tsc --noEmit`
Expected : 0 erreur (le `metric.key` union inclut désormais `hidden_ratio`, présent dans `maxValues`).

Run : `cd frontend && npx vitest run`
Expected : toute la suite verte (incluant le nouveau test radar).

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/RadarChart.tsx frontend/src/components/ComparisonView.tsx frontend/src/components/RadarChart.test.tsx frontend/src/components/ComparisonView.test.tsx
git commit -m "$(cat <<'EOF'
feat(J1a): afficher hidden_ratio (axe radar + carte) et num_nodes (carte) dans Comparaison

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Notes d'exécution

- Tâche unique, frontend-only, sur `feat/frontend-hidden-capacity` → PR vers `main`.
- `RadarChart.tsx` n'avait pas de test ; le nouveau fichier en pose un (couvre aussi la non-régression des 5 axes existants).
- Si `tsc` se plaint de l'indexation `maxValues[metric.key]`, c'est le signe que la clé `hidden_ratio` manque dans `maxValues` (garde-fou) — l'ajouter, ne PAS contourner par un cast `any`.
- Le test `ComparisonView` étendu doit être aligné sur le harnais réel du fichier (mock `apiFetch` + `QueryClientProvider` déjà présents) ; ne pas dupliquer le mock.
