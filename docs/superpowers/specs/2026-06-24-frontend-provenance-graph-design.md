# Graphe de provenance EDR↔condition↔article (design)

Date : 2026-06-24
Vague : H (pistes net-new) — item H1
Statut : design approuvé, prêt pour le plan d'implémentation.

## Problème

Les liens finding↔run↔EDR↔article existent (F2.9) et sont exposés par des endpoints
(`/api/runs/edr-links`, `/api/runs/article-links`, `RunDetail.links`), mais ne sont affichés que
sous forme de **badges/listes plats** dans `RunsHistoryView`. Aucune vue ne rend la **toile** de la
recherche navigable : on ne peut pas voir d'un coup d'œil quelles conditions relient quels EDR et
quels articles Sociologue.

## Objectif

Un onglet **Provenance** : un graphe interactif (D3 force) reliant **conditions**, **EDR** et
**articles**, où cliquer un nœud **navigue** vers l'onglet concerné. Rend visible et actionnable la
structure de la recherche. **100% frontend** — assemblé client-side depuis des endpoints existants,
aucun nouvel endpoint backend, aucune dépendance à la session parallèle.

## Décisions (cadrage validé)

| Sujet | Décision |
|---|---|
| Granularité | Nœuds = **conditions** (groupes de seeds), EDR, articles. Edges agrégés (condition↔EDR si un de ses runs lie l'EDR ; condition↔article). Pas de niveau run individuel (illisible). |
| Interaction | **Deep-link** au clic : condition → Comparaison (`?ab=`), EDR → onglet EDR, article → Laboratoire. Le graphe est un hub de navigation. |
| Scope nœuds | Seuls les nœuds avec **≥1 edge** (orphelins exclus → graphe focalisé). |
| Données | Client-side, 4 endpoints existants. **Aucun backend.** |
| Placement | Nouvel onglet `provenance`, famille **Connaissance** (icône lucide `Workflow`). |

## Architecture

### 1. Assemblage (pur, testable) — `frontend/src/lib/provenance.ts`

```ts
export type ProvNodeType = "condition" | "edr" | "article";
export interface ProvNode { id: string; type: ProvNodeType; label: string }
export interface ProvEdge { source: string; target: string }

export function buildProvenanceGraph(
  edrLinks: Record<string, string[]>,      // {edr: [run_id]}
  articleLinks: Record<string, string[]>,  // {run_id: [article_id]}
  runs: RunSummary[],                       // run_id -> name (condition)
  articles: Article[],                      // id -> title
): { nodes: ProvNode[]; edges: ProvEdge[] };
```

- Ids namespacés pour éviter les collisions : `cond:<name>`, `edr:<n>`, `art:<id>`.
- `runId → condition` via `runs` (`run.run_id → run.name`).
- Edges **condition↔EDR** : pour chaque `edr → [run_id]`, mapper run_id→condition, edge `cond:<name>`–`edr:<n>` (dédupliqué).
- Edges **condition↔article** : pour chaque `run_id → [article_id]`, mapper run_id→condition, edge `cond:<name>`–`art:<id>` (dédupliqué).
- Labels : condition = `name` ; EDR = `EDR <n>` ; article = titre (depuis `articles`, fallback `id`).
- **Seuls les nœuds participant à ≥1 edge** sont émis (pas d'orphelins). Pur, aucun effet de bord.

### 2. `ProvenanceGraph` (D3 force) — `frontend/src/components/ProvenanceGraph.tsx`

Calqué sur `TopologyViewer` : `forceSimulation` **typée** (zéro `any`, types `NodeDatum`/`LinkDatum`
comme post-G4), couleur par `type` via `--viz-*`, labels de nœuds, drag. Props
`{ nodes: ProvNode[]; edges: ProvEdge[]; onSelect: (node: ProvNode) => void }`. Au clic d'un nœud →
`onSelect(node)`. Couleurs/chrome via `theme.ts` (`cssVar`/`vizColors`). `aria-label` FR.

### 3. `ProvenanceView` + navigation — `frontend/src/components/ProvenanceView.tsx`

4 `useQuery` (`queryKeys.runs.edrLinks`, `queryKeys.runs.articleLinks`, `queryKeys.runs.list`,
`queryKeys.sociologist.articles`) → `buildProvenanceGraph(...)` → `ProvenanceGraph`. États
Loading/Error/Empty (Empty si `nodes` vide — « aucun lien finding↔run↔EDR à afficher »). Légende des
3 types (pastilles colorées). Deep-link au clic via le `navigate` de `useHashRoute` :
- `condition` → `navigate("comparison", { ab: <name> })` ;
- `edr` → `navigate("edr")` ;
- `article` → `navigate("laboratoire")`.

### 4. Intégration

- `frontend/src/tabs.ts` : clé `"provenance"` + entrée famille **Connaissance** (icône `Workflow`).
- `frontend/src/App.tsx` : lazy `ProvenanceView` + branche `tab === "provenance"`. Hors `showSidebar`.
- `queryKeys` : `edrLinks`/`articleLinks`/`runs.list`/`sociologist.articles` existent déjà — rien à ajouter.

### 5. Données / flux

Aucun endpoint modifié/créé. react-query met en cache par les `queryKeys` existants. Si certaines
queries sont déjà chargées (Historique/Laboratoire/EDR consultés), la dédup évite tout fetch
supplémentaire.

## Tests

- `buildProvenanceGraph` (`lib/provenance.test.ts`) : nœuds/edges depuis un échantillon (mapping
  run→condition correct ; dédup des edges ; **orphelins exclus** ; labels article via titre, fallback id).
- `ProvenanceView` (`ProvenanceView.test.tsx`) : Loading ; Empty (toutes queries vides) ; rendu du
  graphe + légende avec fixture ; **un clic sur un nœud appelle `navigate`** avec la bonne cible
  (mock du hook / spy).
- `ProvenanceGraph` (`ProvenanceGraph.test.tsx`) : smoke — montage du `<svg>` avec nœuds/edges (D3 en
  jsdom ne produit pas de géométrie mesurable ; assertion sur le conteneur).

## Risques

- **D3 en jsdom** : pas de géométrie mesurable. La logique testée est `buildProvenanceGraph` (pur) +
  le câblage `ProvenanceView` (clic→navigate) ; `ProvenanceGraph` = smoke de montage.
- **Densité du graphe** : si beaucoup d'EDR/articles liés, le graphe peut être dense. Mitigation v1 :
  orphelins exclus (déjà) ; un filtrage par type est un enhancement futur (YAGNI v1).
- **Coordination** : `frontend/src/**` + `docs/**` uniquement, frontend-only → aucun conflit avec
  `feat/d1-prod-pairing`.

## Non-objectifs (YAGNI)

- Pas de niveau run individuel (dépliage seeds) en v1.
- Pas de filtres/recherche dans le graphe en v1.
- Pas de nouvel endpoint backend (assemblage client-side).
- Pas de panneau de détail in-place (le deep-link remplace).

## Périmètre des fichiers

Créés : `lib/provenance.ts` (+ test), `components/ProvenanceGraph.tsx` (+ test),
`components/ProvenanceView.tsx` (+ test).
Modifiés : `tabs.ts` (clé + famille Connaissance), `App.tsx` (lazy + branche).

## Suite

Plan d'implémentation via `writing-plans`, tâches TDD : (1) `buildProvenanceGraph` pur + types ;
(2) `ProvenanceGraph` D3 ; (3) `ProvenanceView` + deep-links ; (4) intégration onglet/lazy. Chacune testée.
