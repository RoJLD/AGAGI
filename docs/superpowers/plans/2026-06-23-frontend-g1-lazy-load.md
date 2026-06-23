# G1 — Lazy-load + découpage bundle — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sortir `recharts` (438 kB) et `d3` (~107 kB) du chunk initial en lazy-loadant les vues d'onglet non-landing.

**Architecture:** `React.lazy` (wrapper export-nommé) sur les vues lourdes + une frontière `<Suspense>` unique autour du switch d'onglets dans `App.tsx`. Seul fichier modifié : `App.tsx`. `EDRDashboard` (landing) reste eager. `manualChunks` de Vite inchangé.

**Tech Stack:** React 18 (`lazy`/`Suspense`), Vite 5 (rollup manualChunks), TypeScript, Vitest.

## Global Constraints

- Composants en **exports nommés** → `lazy(() => import("./components/X").then((m) => ({ default: m.X })))`.
- `EDRDashboard` reste **eager** (onglet d'atterrissage `edr`). `ComparisonChart`, `RadarChart`, `LiveEvolution` restent **eager** (légers, pas de lib, rendus dans des onglets inline).
- **Une seule** frontière `<Suspense fallback={<Loading label="Chargement de la vue…" />}>`, à l'intérieur de l'`ErrorBoundary` existante.
- `vite.config.ts` **non modifié**.
- Aucun changement d'API REST → pas de régénération OpenAPI/`schema.ts`.
- Commits en français, conventionnels, sans emoji ; finir par `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

### Task 1: Lazy-load des vues d'onglet + frontière Suspense

**Files:**
- Modify: `frontend/src/App.tsx` (bloc d'imports lignes 1-26 ; wrap du switch d'onglets lignes ~232-376)

**Interfaces:**
- Consomme : les composants de vue existants (exports nommés inchangés) ; `Loading` (`./components/ui/Loading`).
- Produit : aucun export nouveau ; comportement runtime identique, chunks asynchrones par vue lazy.

- [ ] **Step 1: Mesurer le bundle AVANT (baseline)**

Run : `cd /c/Users/robla/VScode_Project/AGAGI-front && npm --prefix frontend run build`
Noter dans le rapport : la taille du chunk d'entrée `index-*.js`, et le fait que `recharts-*.js` (~438 kB) et `d3-*.js` (~107 kB) sont présents. (Baseline de référence pour le Step 6.)

- [ ] **Step 2: Remplacer le bloc d'imports de vues par des imports lazy**

Dans `frontend/src/App.tsx`, remplacer la première ligne d'import React et les imports statiques des vues. Concrètement :

Remplacer `import { useEffect, useMemo, useState } from "react";` par :
```tsx
import { lazy, Suspense, useEffect, useMemo, useState } from "react";
```

Supprimer les imports statiques de ces vues lazy (lignes actuelles) :
`TopologyViewer`, `LaboratoryView`, `TimelineViewer`, `SandboxView`, `LiveMetrics`, `FlatlandViewer`, `ABComparisonView`, `RunLauncher`, `RunsHistoryView`, `HealthView`.

Conserver en eager : `ComparisonChart`, `RadarChart`, `EDRDashboard`, `LiveEvolution`, `Button`, `ErrorBoundary`, et ajouter l'import de `Loading`.

Après le bloc d'imports eager, ajouter les consts lazy :
```tsx
import { Loading } from "./components/ui/Loading";

const TopologyViewer = lazy(() => import("./components/TopologyViewer").then((m) => ({ default: m.TopologyViewer })));
const LaboratoryView = lazy(() => import("./components/LaboratoryView").then((m) => ({ default: m.LaboratoryView })));
const TimelineViewer = lazy(() => import("./components/TimelineViewer").then((m) => ({ default: m.TimelineViewer })));
const SandboxView = lazy(() => import("./components/SandboxView").then((m) => ({ default: m.SandboxView })));
const LiveMetrics = lazy(() => import("./components/LiveMetrics").then((m) => ({ default: m.LiveMetrics })));
const FlatlandViewer = lazy(() => import("./components/FlatlandViewer").then((m) => ({ default: m.FlatlandViewer })));
const ABComparisonView = lazy(() => import("./components/ABComparisonView").then((m) => ({ default: m.ABComparisonView })));
const RunLauncher = lazy(() => import("./components/RunLauncher").then((m) => ({ default: m.RunLauncher })));
const RunsHistoryView = lazy(() => import("./components/RunsHistoryView").then((m) => ({ default: m.RunsHistoryView })));
const HealthView = lazy(() => import("./components/HealthView").then((m) => ({ default: m.HealthView })));
```

Laisser les imports eager existants tels quels :
```tsx
import { EDRDashboard } from "./components/EDRDashboard";
import { ComparisonChart } from "./components/ComparisonChart";
import { RadarChart } from "./components/RadarChart";
import { LiveEvolution } from "./components/LiveEvolution";
import { Button } from "./components/ui/Button";
import { ErrorBoundary } from "./components/ErrorBoundary";
```

- [ ] **Step 3: Envelopper le switch d'onglets dans `<Suspense>`**

Dans le rendu, l'`ErrorBoundary` entoure actuellement directement les `{tab === ... && <View/>}`. Ajouter un `<Suspense>` juste à l'intérieur. Remplacer :
```tsx
          <ErrorBoundary key={tab}>
          {tab === "edr" && <EDRDashboard />}
```
par :
```tsx
          <ErrorBoundary key={tab}>
          <Suspense fallback={<Loading label="Chargement de la vue…" />}>
          {tab === "edr" && <EDRDashboard />}
```
et la fermeture, remplacer :
```tsx
          {tab === "sante" && <HealthView />}
          </ErrorBoundary>
```
par :
```tsx
          {tab === "sante" && <HealthView />}
          </Suspense>
          </ErrorBoundary>
```

- [ ] **Step 4: Vérifier le typage + les tests existants**

Run : `cd /c/Users/robla/VScode_Project/AGAGI-front && npm --prefix frontend run test`
Attendu : les 15 tests passent (aucune régression).

- [ ] **Step 5: Build APRÈS + vérifier le découpage**

Run : `cd /c/Users/robla/VScode_Project/AGAGI-front && npm --prefix frontend run build`
Attendu : build vert (`tsc` ok). Comparer au baseline du Step 1 :
- le chunk d'entrée `index-*.js` doit **diminuer nettement** ;
- `recharts-*.js` et `d3-*.js` doivent rester des chunks **séparés** désormais chargés à la demande (Vite/rollup les marque comme chunks asynchrones — ils n'apparaissent plus dans le graphe d'entrée, mais comme chunks émis pour les `import()` dynamiques).
Consigner les tailles avant/après dans le rapport.

- [ ] **Step 6: Commit**

```bash
cd /c/Users/robla/VScode_Project/AGAGI-front && git add frontend/src/App.tsx && git commit -m "$(cat <<'EOF'
perf(frontend): lazy-load des vues d'onglet (recharts/d3 hors du chunk initial)

React.lazy (wrapper export-nommé) sur les 10 vues non-landing + Suspense unique.
EDRDashboard (landing) reste eager. recharts (438kB) et d3 (107kB) deviennent
des chunks asynchrones chargés au clic sur Sandbox/Topologie/Timeline/Temps réel.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

- **Spec coverage** : périmètre lazy (10 vues) + eager (EDR/Comparison/Radar/LiveEvolution) ✅ ; Suspense unique dans ErrorBoundary ✅ ; manualChunks inchangé ✅ ; vérification = mesure bundle avant/après ✅. Déviation assumée vs spec : le test RTL Suspense (qualifié « secondaire » dans le spec) est **omis** au profit de la mesure de build (preuve principale) + suite existante ; signalé à l'utilisateur.
- **Placeholders** : aucun — le code exact des imports et du wrap Suspense est fourni.
- **Type consistency** : tous les wrappers lazy utilisent l'export nommé réel (`m.SandboxView`, etc.) ; `Loading` importé depuis `./components/ui/Loading` (chemin existant, déjà utilisé par les vues).
