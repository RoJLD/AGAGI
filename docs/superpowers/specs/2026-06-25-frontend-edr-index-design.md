# Fil conducteur EDR — index navigable (design)

Date : 2026-06-25
Vague : I (pistes net-new) — item I2
Statut : design approuvé, prêt pour le plan d'implémentation.

## Problème

Le corpus EDR compte ~106 décisions documentées (`docs/EDR/NNN_*.md`), mais le dashboard n'en montre
qu'une **galerie de highlights** (cartes curées + liste plate des non-mappés dans `EDRDashboard`).
Aucun moyen de **rechercher** dans le corpus, de voir la **couverture** (lesquels sont mis en carte),
ni la **liaison aux runs** de façon complète. Le « fil conducteur » de la recherche n'est pas navigable.

## Objectif

Un onglet **Fil EDR** : l'index complet des 106 EDR, **recherchable/filtrable**, avec pour chaque EDR
son titre (le verdict en prose), un indicateur « mappé » (carte curée existante) et ses runs liés —
chaque run étant un **deep-link** vers son détail (réutilise le `?run=` livré en H4). Colonne
vertébrale de navigation, complémentaire de la galerie curée.

## Décisions (cadrage validé)

| Sujet | Décision |
|---|---|
| Verdicts | **Pas d'enum fabriqué** (RÉSOLU/RÉFUTÉ/OUVERT). Le **titre** EDR (prose) porte le verdict ; on l'affiche tel quel. |
| Données | 100% endpoints existants : `/api/edr` (curés), `/api/edr/docs` (les 106), `/api/runs/edr-links`. **Aucun backend.** |
| Valeur nette | Recherche + complétude (106 vs galerie curée) + linkage runs + deep-link `→ run`. |
| Deep-link | Par run lié : `navigate("runs", { run: run_id })` (ouvre le détail via le `?run=` de H4). Pas de deep-link provenance (le graphe n'est pas filtrable par EDR — affordance trompeuse évitée). |
| Placement | Nouvel onglet `synthese`, famille **Connaissance** (icône lucide `ListChecks`). |

## Architecture (frontend-only)

### 1. `lib/edrIndex.ts` (pur, testable)

```ts
import type { EdrLinks } from "../types";

export interface EdrIndexRow {
  edr: number;
  title: string;
  mapped: boolean;       // une carte curée (non-stub) existe pour cet EDR
  runIds: string[];      // runs liés (depuis edr-links)
  runCount: number;
}

/** Croise les 106 docs EDR avec les EDR curés (mappés) et les liens runs. Tri EDR décroissant. */
export function buildEdrIndex(
  docs: { edr: number; title: string }[],
  curatedEdrs: number[],
  edrLinks: EdrLinks,
): EdrIndexRow[];

export interface IndexSummary { total: number; mapped: number; withRuns: number }
/** Compte total / mappés / avec ≥1 run (sur les lignes fournies). */
export function summarizeIndex(rows: EdrIndexRow[]): IndexSummary;

export interface IndexFilter { query: string; mappedOnly: boolean; withRunsOnly: boolean }
/** Filtre : recherche sur `<edr> <titre>` (insensible casse), + mappés-only, + avec-runs-only. */
export function filterIndex(rows: EdrIndexRow[], f: IndexFilter): EdrIndexRow[];
```

- `buildEdrIndex` : pour chaque doc, `runIds = edrLinks[String(edr)] ?? []`, `mapped = curated.has(edr)` ;
  tri `b.edr - a.edr`. Pur, aucun effet de bord.
- `summarizeIndex` calculé sur les lignes **non filtrées** (couverture globale).

### 2. `components/EdrIndexView.tsx`

- 3 `useQuery` :
  - `queryKeys.edr` → `{ findings: { edr: number; stub?: boolean }[] }` (forme minimale typée localement) ;
    `curatedEdrs = findings.filter((f) => !f.stub).map((f) => f.edr)`.
  - `queryKeys.edrDocs` (`["edr","docs"]`) → `EdrDoc[]`.
  - `queryKeys.runs.edrLinks` → `EdrLinks`.
- `rows = buildEdrIndex(docs, curatedEdrs, edrLinks)` ; `summary = summarizeIndex(rows)` ;
  états locaux `query`/`mappedOnly`/`withRunsOnly` → `filtered = filterIndex(rows, ...)`.
- `navigate` via `useHashRoute(TAB_KEYS, "synthese")`.
- Rendu : titre, **bandeau stats** (`total` EDR · `mapped` mappés · `withRuns` avec runs), champ
  recherche (`Field` + `<input>`), 2 cases à cocher (mappés / avec runs), puis une **table** :
  colonnes EDR · Titre · Mappé · Runs. Par ligne : badge `EDR n`, titre, badge « mappé » si `mapped`,
  et dans la cellule Runs un bouton `→ run` par `run_id` (appelle `navigate("runs", { run })`) ou
  `—` si aucun. Ligne « aucun résultat » si `filtered` vide.
- États : `Loading` (une requête en cours), `ErrorState` (avec retry), `Empty` (aucun doc EDR).

### 3. Intégration

- `frontend/src/types.ts` : `export interface EdrDoc { edr: number; title: string; file: string }`.
- `frontend/src/api/queryKeys.ts` : `edrDocs: ["edr", "docs"] as const` (niveau racine, à côté de `edr`).
- `frontend/src/tabs.ts` : clé `"synthese"` (après `"carnet"`) + entrée famille **Connaissance**
  `{ key: "synthese", label: "Fil EDR", icon: ListChecks }` (import `ListChecks` de lucide-react).
- `frontend/src/App.tsx` : lazy `EdrIndexView` + branche `tab === "synthese"`. Hors `showSidebar`.

## Tests

- `lib/edrIndex.test.ts` : `buildEdrIndex` (mapped depuis curatedEdrs ; runIds depuis edrLinks ; tri EDR
  décroissant ; EDR sans lien → runCount 0) ; `summarizeIndex` (total/mapped/withRuns) ; `filterIndex`
  (recherche titre + numéro, mappedOnly, withRunsOnly, combinés).
- `EdrIndexView.test.tsx` : Empty (docs vides) ; rendu stats + table avec fixture (3 queries mockées,
  désambiguïsées par `endsWith("/docs")` / `endsWith("/edr-links")` / `endsWith("/api/edr")`) ; la
  recherche filtre les lignes ; clic sur un bouton `→ run` appelle `navigate("runs", { run })` (spy).

## Risques

- **Désambiguïsation des mocks** : `/api/edr`, `/api/edr/docs`, `/api/runs/edr-links` — ordonner les
  tests `endsWith` du plus spécifique au plus général (`/docs` et `/edr-links` avant `/api/edr`).
- **EDR sans titre lisible** : `docs` fournit toujours un `title` (slug dérivé du nom de fichier),
  jamais vide — pas de fallback nécessaire.
- **Volume** : 106 lignes, recherche/filtre client → trivial, pas de pagination v1.
- **Coordination** : `frontend/src/**` + `docs/**` uniquement, données déjà sur main → aucune
  dépendance session parallèle, aucun conflit.

## Non-objectifs (YAGNI v1)

- Enum de verdict fabriqué (les titres en prose font foi).
- Lineage inter-EDR (références `[[…]]` en prose, non structurées).
- Contenu markdown du doc inline (aucun endpoint de contenu).
- Graphe (c'est H1/Provenance) ; deep-link provenance par EDR (pas de filtre).
- Pagination, tri configurable, export.

## Périmètre des fichiers

Créés : `lib/edrIndex.ts` (+ test), `components/EdrIndexView.tsx` (+ test).
Modifiés : `types.ts` (`EdrDoc`), `api/queryKeys.ts` (`edrDocs`), `tabs.ts` (onglet), `App.tsx` (lazy + branche).
**Aucun backend.**

## Suite

Plan d'implémentation via `writing-plans`, tâches TDD :
(1) `lib/edrIndex.ts` + `EdrDoc` + `queryKeys.edrDocs` ;
(2) `EdrIndexView` (3 queries, stats, recherche/filtres, table, deep-link run) ;
(3) intégration onglet/lazy.
Chacune testée. Frontend-only, zéro dépendance backend.
