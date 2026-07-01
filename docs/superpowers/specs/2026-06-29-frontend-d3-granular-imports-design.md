# J5 — Imports d3 granulaires (tree-shaking du chunk d3)

> Vague J, item J5. Frontend-only. Optimisation bundle : trimmer le chunk `d3`
> en remplaçant `import * as d3` par des imports nommés depuis les sous-modules.

## Objectif

Réduire le chunk lazy `d3` (~104 KB → ~35-45 KB) en coupant le baril de ré-exports
du méta-paquet `d3` : passer de `import * as d3 from "d3"` à des imports nommés depuis
`d3-selection` / `d3-force` / `d3-drag` dans les 3 viewers qui utilisent d3.

## Contexte mesuré (vérité terrain, build du 2026-06-29)

| Chunk | Taille (raw) | Chargement |
|---|---|---|
| `recharts` | 457 KB | lazy (chunk isolé) |
| `d3` | 104 KB | lazy (chunk isolé) |
| `index` (initial) | 73 KB | eager |
| vues | 2-9 KB chacune | lazy |

La vague G1 (lazy-load des routes) + `manualChunks` ont déjà sorti recharts ET d3 du
bundle initial. **La piste audit « recharts sync +444 Ko dans LiveDashboard » est périmée** :
recharts est déjà un chunk lazy de 457 KB, monolithe tiers non tree-shakable par style
d'import → DESCOPÉ. Seul d3 est actionnable.

### Pourquoi `import * as d3` empêche le tree-shaking

Le paquet `d3` est un baril de ré-exports (`export * from "d3-scale"`, `export * from "d3-geo"`, …).
Avec `import * as d3` + accès par propriété (`d3.select`), le bundler ne peut pas prouver
statiquement quelles ré-exports sont mortes → il garde tout le baril. Importer directement
depuis les sous-modules coupe le baril.

## API d3 réellement utilisée

Relevé sur les 3 viewers (`grep d3.<member>`) :

| Membre | Sous-module |
|---|---|
| `select` | `d3-selection` |
| `forceSimulation`, `forceCenter`, `forceCollide`, `forceLink`, `forceManyBody` | `d3-force` |
| types `SimulationNodeDatum`, `SimulationLinkDatum` | `d3-force` |
| types `DragBehavior`, `SubjectPosition` (TopologyViewer) | `d3-drag` |

`forceCollide` : utilisé par TopologyViewer + ProvenanceGraph, pas TimelineViewer.
**`d3-sankey` n'est importé nulle part** (config morte dans `manualChunks` ; il n'est même
pas dans le méta-paquet `d3` par défaut) → retiré.

## Changements

### 1. Les 3 viewers — imports nommés

`frontend/src/components/TimelineViewer.tsx`, `ProvenanceGraph.tsx`, `TopologyViewer.tsx` :
remplacer `import * as d3 from "d3";` par des imports nommés, puis réécrire chaque `d3.xxx`
en `xxx` (y compris les annotations de type `d3.SimulationNodeDatum` → `SimulationNodeDatum`).

- **TimelineViewer** : `select` (d3-selection) ; `forceSimulation, forceCenter, forceLink, forceManyBody` + types `SimulationNodeDatum, SimulationLinkDatum` (d3-force).
- **ProvenanceGraph** : idem TimelineViewer + `forceCollide`.
- **TopologyViewer** : idem ProvenanceGraph + depuis `d3-drag` : `drag` (si réellement appelé) et/ou les types `DragBehavior, SubjectPosition`. L'implémenteur lit le fichier complet pour déterminer si `drag()` est appelé (import valeur) ou seulement référencé en type (import `type`).

Imports de type : utiliser la syntaxe `import { type X }` ou `import type { X }` pour ne pas
émettre de require runtime inutile.

### 2. `vite.config.ts` — manualChunks

```ts
// avant
d3: ["d3", "d3-sankey"],
// après
d3: ["d3-selection", "d3-force", "d3-drag"],
```

Les dépendances transitives (`d3-quadtree`, `d3-dispatch`, `d3-timer`) suivent
automatiquement dans le chunk `d3` (seuls les modules du chunk d3 les référencent).
`react` et `recharts` inchangés.

## Comportement

**Zéro changement de comportement.** Refactor purement de style d'import ; les viewers
exécutent le même rendu d3 impératif (svg via refs dans `useEffect`).

## Tests

Pas de nouveau test. Le rendu d3 (force simulation + manipulation svg) n'est pas testable
en jsdom ; les smoke tests existants de ces viewers (rendu du conteneur) restent le filet de
non-régression. Le gate réel est la mesure du build.

## Gates (critères de succès)

1. `cd frontend && npx tsc --noEmit` → 0 erreur (les types d3-* résolvent identiquement).
2. `cd frontend && npx vitest run` → suite complète verte (aucune régression).
3. `cd frontend && npx vite build` → réussit, et :
   - le chunk `d3-*.js` tombe sous ~50 KB (raw), idéalement ~35-45 KB ;
   - le chunk `index-*.js` n'augmente pas (~73 KB) ;
   - aucun sous-module d3 ne fuit dans les chunks de vues (pas de nouveau gros chunk de vue).

## Hors-scope (YAGNI)

- recharts (déjà chunk lazy optimal ; monolithe tiers).
- Lazy-load des composants chart au rendu (gain marginal, complexité Suspense).
- Toute migration d3 → autre lib.
- EnergyChart/ForageFunnelChart/SweepOverlayChart (recharts, pas d3).

## Contraintes globales

- Frontend-only (aucun fichier backend touché).
- TypeScript strict, **zéro `any`**.
- `tsc` 0 erreur, suite verte, build réussi.
- Commits path-scoped (tree partagé — sessions parallèles).
- Branche : `feat/frontend-bundle-trim` (depuis `main`), PR vers `main`.
- Trailer commit : `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
