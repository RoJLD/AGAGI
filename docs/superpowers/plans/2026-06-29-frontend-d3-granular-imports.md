# J5 — Imports d3 granulaires Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trimmer le chunk lazy `d3` (~104 KB → ~35-45 KB) en remplaçant `import * as d3` par des imports nommés depuis `d3-selection`/`d3-force`/`d3-drag` dans les 3 viewers, et en corrigeant `manualChunks`.

**Architecture:** Refactor purement de style d'import (zéro changement de comportement). Couper le baril de ré-exports du méta-paquet `d3` pour que Rollup ne garde que les sous-modules réellement utilisés. Les 3 viewers + `vite.config.ts` changent ensemble (le chunk d3 propre l'exige) → une seule tâche, gate = mesure du build.

**Tech Stack:** Vite, Rollup, TypeScript strict, d3 (d3-selection/d3-force/d3-drag), Vitest.

## Global Constraints

- Frontend-only — aucun fichier backend touché.
- TypeScript strict, **zéro `any`**.
- `cd frontend && npx tsc --noEmit` → 0 erreur ; `cd frontend && npx vitest run` → suite verte ; `cd frontend && npx vite build` → réussit.
- Commits **path-scoped** (`git commit -- <chemins>`, jamais `git add -A`) — tree partagé, sessions parallèles.
- Worktree : `c:\Users\robla\VScode_Project\AGAGI-front`. Branche : `feat/frontend-bundle-trim` (depuis `main`).
- Trailer commit : `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

## File Structure

- **Modify** `frontend/src/components/TimelineViewer.tsx` — import nommé (select + force\*, pas de drag/collide).
- **Modify** `frontend/src/components/ProvenanceGraph.tsx` — import nommé (select + force\* + collide + drag valeur).
- **Modify** `frontend/src/components/TopologyViewer.tsx` — import nommé (select + force\* + collide + drag valeur + types DragBehavior/SubjectPosition).
- **Modify** `frontend/vite.config.ts:15` — `manualChunks.d3`.

---

### Task 1: Imports d3 granulaires + manualChunks

**Files:**
- Modify: `frontend/src/components/TimelineViewer.tsx:2`
- Modify: `frontend/src/components/ProvenanceGraph.tsx:2`
- Modify: `frontend/src/components/TopologyViewer.tsx:2`
- Modify: `frontend/vite.config.ts:15`

**Interfaces:**
- Consumes : paquets npm déjà installés `d3-selection`, `d3-force`, `d3-drag` (vérifiés présents dans `node_modules`).
- Produces : aucun export nouveau. Comportement runtime identique.

**Méthode commune aux 3 viewers :** remplacer la ligne `import * as d3 from "d3";` par les imports nommés indiqués, puis **remplacer toutes les occurrences restantes de `d3.` par rien** (chaîne vide) dans le fichier — p.ex. `d3.forceSimulation<NodeDatum>(...)` → `forceSimulation<NodeDatum>(...)`, `d3.SimulationLinkDatum<NodeDatum>` → `SimulationLinkDatum<NodeDatum>`. Tous les noms accédés sont importés, donc ce remplacement global est sûr. La ligne d'import elle-même contient `as d3 from` (pas `d3.`) et n'est pas affectée par le remplacement — elle est déjà remplacée à l'étape précédente.

- [ ] **Step 1: TimelineViewer — imports nommés**

Dans `frontend/src/components/TimelineViewer.tsx`, remplacer la ligne 2 :

```ts
import * as d3 from "d3";
```

par :

```ts
import { select } from "d3-selection";
import {
  forceSimulation,
  forceCenter,
  forceLink,
  forceManyBody,
  type SimulationNodeDatum,
  type SimulationLinkDatum,
} from "d3-force";
```

Puis remplacer toutes les occurrences restantes de `d3.` par rien dans ce fichier.
Membres concernés (tous importés) : `select`, `forceSimulation`, `forceCenter`, `forceLink`, `forceManyBody`, `SimulationNodeDatum`, `SimulationLinkDatum`.

- [ ] **Step 2: ProvenanceGraph — imports nommés**

Dans `frontend/src/components/ProvenanceGraph.tsx`, remplacer la ligne 2 :

```ts
import * as d3 from "d3";
```

par :

```ts
import { select } from "d3-selection";
import {
  forceSimulation,
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  type SimulationNodeDatum,
  type SimulationLinkDatum,
} from "d3-force";
import { drag } from "d3-drag";
```

Puis remplacer toutes les occurrences restantes de `d3.` par rien dans ce fichier.
Membres concernés (tous importés) : `select`, `forceSimulation`, `forceCenter`, `forceCollide`, `forceLink`, `forceManyBody`, `drag`, `SimulationNodeDatum`, `SimulationLinkDatum`.

- [ ] **Step 3: TopologyViewer — imports nommés**

Dans `frontend/src/components/TopologyViewer.tsx`, remplacer la ligne 2 :

```ts
import * as d3 from "d3";
```

par :

```ts
import { select } from "d3-selection";
import {
  forceSimulation,
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  type SimulationNodeDatum,
  type SimulationLinkDatum,
} from "d3-force";
import { drag, type DragBehavior, type SubjectPosition } from "d3-drag";
```

Puis remplacer toutes les occurrences restantes de `d3.` par rien dans ce fichier.
Membres concernés (tous importés) : `select`, `forceSimulation`, `forceCenter`, `forceCollide`, `forceLink`, `forceManyBody`, `drag`, `SimulationNodeDatum`, `SimulationLinkDatum`, `DragBehavior`, `SubjectPosition`.

Note : le type annoté ligne 50 `d3.DragBehavior<SVGGElement, NodeDatum, NodeDatum | d3.SubjectPosition>` devient `DragBehavior<SVGGElement, NodeDatum, NodeDatum | SubjectPosition>`.

- [ ] **Step 4: vite.config.ts — manualChunks.d3**

Dans `frontend/vite.config.ts`, remplacer la ligne 15 :

```ts
          d3: ["d3", "d3-sankey"],
```

par :

```ts
          d3: ["d3-selection", "d3-force", "d3-drag"],
```

(`d3-sankey` n'est importé nulle part — config morte. `react` et `recharts` inchangés.)

- [ ] **Step 5: Vérifier le typage**

Run: `cd frontend && npx tsc --noEmit`
Expected: 0 erreur. (Si une erreur du type « Cannot find name 'd3' » apparaît, c'est qu'une occurrence `d3.` a été manquée → la corriger.)

- [ ] **Step 6: Vérifier la suite de tests (non-régression)**

Run: `cd frontend && npx vitest run`
Expected: suite complète verte (même nombre de tests qu'avant, aucune régression — le comportement est inchangé).

- [ ] **Step 7: Build + mesure du chunk d3**

Run: `cd frontend && npx vite build && ls -la dist/assets/*.js | awk '{printf "%8d KB  %s\n", $5/1024, $9}' | sort -rn | head -6`

Expected :
- le build réussit ;
- le chunk `d3-*.js` est **sous 50 KB** (était ~104 KB ; cible ~35-45 KB) ;
- le chunk `index-*.js` reste ~73 KB (n'augmente pas) ;
- aucun nouveau gros chunk de vue (pas de fuite de sous-module d3 dans TimelineViewer/ProvenanceView/TopologyView).

Si le chunk d3 n'a PAS diminué ou si un sous-module d3 a fui dans un chunk de vue : vérifier que `manualChunks.d3` liste bien les 3 sous-modules et qu'aucun `import * as d3 from "d3"` ne subsiste (`grep -rn "from \"d3\"" frontend/src`).

- [ ] **Step 8: Commit**

```bash
git commit -m "perf(J5): imports d3 granulaires (d3-selection/force/drag) + manualChunks

Coupe le baril de re-exports du meta-paquet d3 dans les 3 viewers
(TimelineViewer/ProvenanceGraph/TopologyViewer) ; manualChunks.d3
liste les sous-modules reels, d3-sankey mort retire. Chunk d3 ~104->~40KB.
Zero changement de comportement.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" -- frontend/src/components/TimelineViewer.tsx frontend/src/components/ProvenanceGraph.tsx frontend/src/components/TopologyViewer.tsx frontend/vite.config.ts
```

---

## Notes d'exécution

- **Tâche unique** : le chunk d3 propre exige que les 3 viewers + `manualChunks` changent ensemble (sinon les sous-modules d3 fuient dans les chunks de vues). Pas de découpage par fichier.
- **Pas de revue finale séparée** : 1 tâche, frontend-only, refactor de style ; si la revue de tâche est propre et les gates vérifiées (tsc 0, suite verte, chunk d3 réduit mesuré), la revue whole-branch est repliée dans la revue de tâche.
- **Modèle SDD** : transcription mécanique (imports fournis verbatim) MAIS l'interprétation de la mesure de build au Step 7 demande du jugement → implémenteur sonnet ; reviewer sonnet.
- **Pas de nouveau test** : refactor de style d'import à comportement nul ; le rendu d3 (force/svg) n'est pas testable en jsdom. Gate = build mesuré + smoke tests existants des viewers verts.
