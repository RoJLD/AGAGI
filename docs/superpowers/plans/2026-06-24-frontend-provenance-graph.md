# Graphe de provenance EDR↔condition↔article — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un onglet « Provenance » : un graphe D3 reliant conditions, EDR et articles, où cliquer un nœud navigue vers l'onglet concerné.

**Architecture:** Deux helpers purs (`buildProvenanceGraph` assemble le graphe depuis 4 endpoints existants ; `provenanceTarget` mappe un nœud → cible de navigation) — tous deux testables. `ProvenanceGraph` (D3 force, présentationnel) + `ProvenanceView` (queries + états + deep-link). 100% frontend, aucun nouvel endpoint backend.

**Tech Stack:** React 18, TypeScript (strict), Vite, @tanstack/react-query v5, d3 v7, lucide-react, Vitest + @testing-library/react.

## Global Constraints

- TypeScript `strict: true` — aucun `any` (les callbacks d3 sont typés, cf. `TopologyViewer`).
- Copie UI/a11y en **français**. Couleurs via tokens (`theme.ts` / `var(--…)`).
- Granularité = **conditions** (pas de run individuel). Edges agrégés + dédupliqués. **Nœuds orphelins exclus** (≥1 edge requis).
- Deep-link au clic : condition → `navigate("comparison", { ab: <name> })` ; EDR → `navigate("edr")` ; article → `navigate("laboratoire")`.
- 100% frontend : assemblage client-side depuis endpoints existants. Périmètre `frontend/src/**` + ce plan.
- Tests restent hors tsconfig. Chaque commit finit par `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Test : `npm --prefix frontend run test -- <fichier>`. Build : `npm --prefix frontend run build`.
- Branche : `feat/frontend-provenance-graph` (déjà créée).

---

## File Structure

Créés :
- `frontend/src/lib/provenance.ts` — `buildProvenanceGraph` + `provenanceTarget` + types.
- `frontend/src/lib/provenance.test.ts`
- `frontend/src/components/ProvenanceGraph.tsx` — graphe D3.
- `frontend/src/components/ProvenanceGraph.test.tsx`
- `frontend/src/components/ProvenanceView.tsx` — queries + états + deep-link.
- `frontend/src/components/ProvenanceView.test.tsx`

Modifiés :
- `frontend/src/tabs.ts` — clé `"provenance"` + entrée famille Connaissance.
- `frontend/src/App.tsx` — lazy `ProvenanceView` + branche `tab === "provenance"`.

---

## Task 1: Helpers purs `buildProvenanceGraph` + `provenanceTarget`

**Files:**
- Create: `frontend/src/lib/provenance.ts`
- Test: `frontend/src/lib/provenance.test.ts`

**Interfaces:**
- Consumes: `Article`, `RunSummary` de `../types`.
- Produces:
  - `type ProvNodeType = "condition" | "edr" | "article"`
  - `interface ProvNode { id: string; type: ProvNodeType; label: string }`
  - `interface ProvEdge { source: string; target: string }`
  - `buildProvenanceGraph(edrLinks: Record<string,string[]>, articleLinks: Record<string,string[]>, runs: RunSummary[], articles: Article[]): { nodes: ProvNode[]; edges: ProvEdge[] }`
  - `provenanceTarget(node: ProvNode): { tab: string; query: Record<string, string> }`

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/lib/provenance.test.ts
import { test, expect } from "vitest";
import { buildProvenanceGraph, provenanceTarget } from "./provenance";
import type { Article, RunSummary } from "../types";

const runs: RunSummary[] = [
  { run_id: "condA_0", name: "condA", seed: 0, metrics: [] },
  { run_id: "condA_1", name: "condA", seed: 1, metrics: [] },
];
const articles: Article[] = [{ id: "art1", title: "Découverte X", content: "", timestamp: "" }];

test("assemble nœuds/edges et déduplique", () => {
  const { nodes, edges } = buildProvenanceGraph(
    { "81": ["condA_0", "condA_1"] },          // EDR 81 lié aux 2 seeds de condA
    { condA_0: ["art1"] },                     // article art1 lié à condA via condA_0
    runs,
    articles,
  );
  const ids = nodes.map((n) => n.id).sort();
  expect(ids).toEqual(["art:art1", "cond:condA", "edr:81"]);
  expect(nodes.find((n) => n.id === "edr:81")!.label).toBe("EDR 81");
  expect(nodes.find((n) => n.id === "art:art1")!.label).toBe("Découverte X");
  // edge condA–EDR dédupliqué (2 seeds -> 1 edge), + condA–article
  expect(edges).toHaveLength(2);
  expect(edges).toContainEqual({ source: "cond:condA", target: "edr:81" });
  expect(edges).toContainEqual({ source: "cond:condA", target: "art:art1" });
});

test("exclut les orphelins (lien vers un run inconnu)", () => {
  const { nodes } = buildProvenanceGraph({ "99": ["ghost_0"] }, {}, runs, articles);
  expect(nodes).toHaveLength(0); // run inconnu -> aucune condition -> EDR 99 orphelin exclu
});

test("article sans titre connu -> label = id", () => {
  const { nodes } = buildProvenanceGraph({}, { condA_0: ["artX"] }, runs, []);
  expect(nodes.find((n) => n.id === "art:artX")!.label).toBe("artX");
});

test("provenanceTarget mappe chaque type vers sa cible", () => {
  expect(provenanceTarget({ id: "cond:condA", type: "condition", label: "condA" })).toEqual({
    tab: "comparison",
    query: { ab: "condA" },
  });
  expect(provenanceTarget({ id: "edr:81", type: "edr", label: "EDR 81" })).toEqual({ tab: "edr", query: {} });
  expect(provenanceTarget({ id: "art:art1", type: "article", label: "X" })).toEqual({
    tab: "laboratoire",
    query: {},
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/lib/provenance.test.ts`
Expected: FAIL — `./provenance` n'existe pas.

- [ ] **Step 3: Write implementation**

```ts
// frontend/src/lib/provenance.ts
import type { Article, RunSummary } from "../types";

export type ProvNodeType = "condition" | "edr" | "article";
export interface ProvNode {
  id: string;
  type: ProvNodeType;
  label: string;
}
export interface ProvEdge {
  source: string;
  target: string;
}

/** Assemble le graphe de provenance (conditions↔EDR↔articles) depuis les liens existants.
 *  Granularité condition (pas de run individuel) ; edges dédupliqués ; orphelins exclus. Pur. */
export function buildProvenanceGraph(
  edrLinks: Record<string, string[]>,
  articleLinks: Record<string, string[]>,
  runs: RunSummary[],
  articles: Article[],
): { nodes: ProvNode[]; edges: ProvEdge[] } {
  const condOf = new Map<string, string>();
  for (const r of runs) condOf.set(r.run_id, r.name);
  const titleOf = new Map<string, string>();
  for (const a of articles) titleOf.set(a.id, a.title);

  const edgeSet = new Set<string>();
  const edges: ProvEdge[] = [];
  const usedConditions = new Set<string>();
  const usedEdr = new Set<string>();
  const usedArticles = new Set<string>();

  const addEdge = (source: string, target: string) => {
    const key = `${source}__${target}`;
    if (edgeSet.has(key)) return;
    edgeSet.add(key);
    edges.push({ source, target });
  };

  for (const [edr, runIds] of Object.entries(edrLinks)) {
    for (const runId of runIds) {
      const cond = condOf.get(runId);
      if (!cond) continue;
      addEdge(`cond:${cond}`, `edr:${edr}`);
      usedConditions.add(cond);
      usedEdr.add(edr);
    }
  }

  for (const [runId, articleIds] of Object.entries(articleLinks)) {
    const cond = condOf.get(runId);
    if (!cond) continue;
    for (const artId of articleIds) {
      addEdge(`cond:${cond}`, `art:${artId}`);
      usedConditions.add(cond);
      usedArticles.add(artId);
    }
  }

  const nodes: ProvNode[] = [
    ...[...usedConditions].map((c): ProvNode => ({ id: `cond:${c}`, type: "condition", label: c })),
    ...[...usedEdr].map((e): ProvNode => ({ id: `edr:${e}`, type: "edr", label: `EDR ${e}` })),
    ...[...usedArticles].map((a): ProvNode => ({ id: `art:${a}`, type: "article", label: titleOf.get(a) ?? a })),
  ];

  return { nodes, edges };
}

/** Cible de navigation au clic d'un nœud (deep-link via useHashRoute.navigate). Pur. */
export function provenanceTarget(node: ProvNode): { tab: string; query: Record<string, string> } {
  if (node.type === "condition") return { tab: "comparison", query: { ab: node.label } };
  if (node.type === "edr") return { tab: "edr", query: {} };
  return { tab: "laboratoire", query: {} };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/lib/provenance.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/provenance.ts frontend/src/lib/provenance.test.ts
git commit -m "feat(H1): helpers purs buildProvenanceGraph + provenanceTarget

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `ProvenanceGraph` (D3 force)

**Files:**
- Create: `frontend/src/components/ProvenanceGraph.tsx`
- Test: `frontend/src/components/ProvenanceGraph.test.tsx`

**Interfaces:**
- Consumes: `ProvNode`/`ProvEdge` (Task 1), `cssVar`/`vizColors` de `../theme`.
- Produces: `ProvenanceGraph({ nodes, edges, onSelect }: { nodes: ProvNode[]; edges: ProvEdge[]; onSelect: (node: ProvNode) => void })`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/ProvenanceGraph.test.tsx
import { render, cleanup } from "@testing-library/react";
import { afterEach, test, expect } from "vitest";
import { ProvenanceGraph } from "./ProvenanceGraph";

afterEach(() => cleanup());

test("monte un svg avec les nœuds", () => {
  const { container } = render(
    <ProvenanceGraph
      nodes={[
        { id: "cond:condA", type: "condition", label: "condA" },
        { id: "edr:81", type: "edr", label: "EDR 81" },
      ]}
      edges={[{ source: "cond:condA", target: "edr:81" }]}
      onSelect={() => {}}
    />,
  );
  const svg = container.querySelector("svg");
  expect(svg).toBeTruthy();
  // 2 nœuds rendus (groupes <g> avec cercle)
  expect(container.querySelectorAll("circle").length).toBe(2);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/components/ProvenanceGraph.test.tsx`
Expected: FAIL — `./ProvenanceGraph` n'existe pas.

- [ ] **Step 3: Write implementation**

```tsx
// frontend/src/components/ProvenanceGraph.tsx
import { useEffect, useRef } from "react";
import * as d3 from "d3";
import type { ProvNode, ProvEdge, ProvNodeType } from "../lib/provenance";
import { cssVar, vizColors } from "../theme";

type NodeDatum = ProvNode & d3.SimulationNodeDatum & { fx?: number | null; fy?: number | null };
type LinkDatum = d3.SimulationLinkDatum<NodeDatum>;

interface ProvenanceGraphProps {
  nodes: ProvNode[];
  edges: ProvEdge[];
  onSelect: (node: ProvNode) => void;
}

export function ProvenanceGraph({ nodes, edges, onSelect }: ProvenanceGraphProps) {
  const ref = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    if (!ref.current || !nodes.length) return;
    const viz = vizColors();
    const colorOf = (t: ProvNodeType) => (t === "condition" ? viz[0] : t === "edr" ? viz[1] : viz[2]);

    const svg = d3.select(ref.current);
    svg.selectAll("*").remove();
    const width = ref.current.clientWidth || 800;
    const height = ref.current.clientHeight || 500;

    // Copies locales : d3 mute les data (positions, source/target résolus).
    const nodeData: NodeDatum[] = nodes.map((n) => ({ ...n }));
    const linkData: LinkDatum[] = edges.map((e) => ({ source: e.source, target: e.target }));

    const simulation = d3
      .forceSimulation<NodeDatum>(nodeData)
      .force("link", d3.forceLink<NodeDatum, LinkDatum>(linkData).id((d) => d.id).distance(90))
      .force("charge", d3.forceManyBody().strength(-240))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide(28));

    const link = svg
      .append("g")
      .style("stroke", "var(--color-border-subtle)")
      .selectAll<SVGLineElement, LinkDatum>("line")
      .data(linkData)
      .join("line")
      .attr("stroke-width", 1.4);

    const drag = d3
      .drag<SVGGElement, NodeDatum>()
      .on("start", (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });

    const node = svg
      .append("g")
      .selectAll<SVGGElement, NodeDatum>("g")
      .data(nodeData)
      .join("g")
      .style("cursor", "pointer")
      .on("click", (_event, d) => onSelect(d))
      .call(drag);

    node.append("circle").attr("r", 14).style("fill", (d) => colorOf(d.type));
    node
      .append("text")
      .attr("text-anchor", "middle")
      .attr("dy", 26)
      .attr("font-size", 10)
      .style("fill", "var(--color-text)")
      .text((d) => d.label);

    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as NodeDatum).x ?? 0)
        .attr("y1", (d) => (d.source as NodeDatum).y ?? 0)
        .attr("x2", (d) => (d.target as NodeDatum).x ?? 0)
        .attr("y2", (d) => (d.target as NodeDatum).y ?? 0);
      node.attr("transform", (d) => `translate(${d.x ?? 0}, ${d.y ?? 0})`);
    });

    return () => {
      simulation.stop();
      svg.selectAll("*").remove();
    };
  }, [nodes, edges, onSelect]);

  return <svg ref={ref} className="topology-svg" aria-label="Graphe de provenance" />;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/components/ProvenanceGraph.test.tsx`
Expected: PASS (1 test — 2 cercles montés).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ProvenanceGraph.tsx frontend/src/components/ProvenanceGraph.test.tsx
git commit -m "feat(H1): ProvenanceGraph (D3 force typé, couleur par type, clic→onSelect)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: `ProvenanceView` + deep-links

**Files:**
- Create: `frontend/src/components/ProvenanceView.tsx`
- Test: `frontend/src/components/ProvenanceView.test.tsx`

**Interfaces:**
- Consumes: `buildProvenanceGraph`/`provenanceTarget`/`ProvNode` (Task 1), `ProvenanceGraph` (Task 2), `apiFetch`, `queryKeys`, primitives `Loading`/`ErrorState`/`Empty`, `useHashRoute` (`navigate`), `TAB_KEYS`.
- Produces: `ProvenanceView()` (lazy-loadé par App).

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/ProvenanceView.test.tsx
import { render, screen, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { ProvenanceView } from "./ProvenanceView";

afterEach(() => cleanup());

function mockEndpoints(map: Record<string, unknown>) {
  (apiFetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
    const key = Object.keys(map).find((k) => url.includes(k));
    return Promise.resolve(key ? map[key] : []);
  });
}

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  window.location.hash = "#/provenance";
  mockEndpoints({
    "edr-links": { "81": ["condA_0"] },
    "article-links": { condA_0: ["art1"] },
    "runs": [{ run_id: "condA_0", name: "condA", seed: 0, metrics: [] }],
    "sociologist/articles": [{ id: "art1", title: "Découverte X", content: "", timestamp: "" }],
  });
});

test("rend le graphe (svg) et la légende avec des données liées", async () => {
  renderWithClient(<ProvenanceView />);
  expect(await screen.findByText(/Provenance/)).toBeTruthy();
  // légende des 3 types
  expect(screen.getByText(/Condition/)).toBeTruthy();
  expect(screen.getByText(/Article/)).toBeTruthy();
});

test("état vide quand aucun lien", async () => {
  mockEndpoints({ "runs": [{ run_id: "condA_0", name: "condA", seed: 0, metrics: [] }] }); // pas de liens
  renderWithClient(<ProvenanceView />);
  expect(await screen.findByText(/Aucun lien/)).toBeTruthy();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/components/ProvenanceView.test.tsx`
Expected: FAIL — `./ProvenanceView` n'existe pas.

- [ ] **Step 3: Write implementation**

```tsx
// frontend/src/components/ProvenanceView.tsx
import { useQuery } from "@tanstack/react-query";
import type { Article, RunSummary } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { useHashRoute } from "../hooks/useHashRoute";
import { TAB_KEYS } from "../tabs";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";
import { buildProvenanceGraph, provenanceTarget, type ProvNode } from "../lib/provenance";
import { ProvenanceGraph } from "./ProvenanceGraph";

type LinkMap = Record<string, string[]>;

export function ProvenanceView() {
  const { navigate } = useHashRoute(TAB_KEYS, "provenance");

  const edrQ = useQuery({
    queryKey: queryKeys.runs.edrLinks,
    queryFn: () => apiFetch<LinkMap>("/api/runs/edr-links"),
    staleTime: 30_000,
  });
  const artQ = useQuery({
    queryKey: queryKeys.runs.articleLinks,
    queryFn: () => apiFetch<LinkMap>("/api/runs/article-links"),
    staleTime: 30_000,
  });
  const runsQ = useQuery({
    queryKey: queryKeys.runs.list,
    queryFn: () => apiFetch<RunSummary[]>("/api/runs"),
    staleTime: 30_000,
  });
  const artListQ = useQuery({
    queryKey: queryKeys.sociologist.articles,
    queryFn: () => apiFetch<Article[]>("/api/sociologist/articles"),
    staleTime: 60_000,
  });

  const isLoading = edrQ.isLoading || artQ.isLoading || runsQ.isLoading || artListQ.isLoading;
  const error = edrQ.error || artQ.error || runsQ.error || artListQ.error;

  if (isLoading) return <Loading label="Chargement du graphe de provenance…" />;
  if (error) {
    const refetchAll = () => {
      edrQ.refetch();
      artQ.refetch();
      runsQ.refetch();
      artListQ.refetch();
    };
    return <ErrorState error={error} onRetry={refetchAll} />;
  }

  const { nodes, edges } = buildProvenanceGraph(
    edrQ.data ?? {},
    artQ.data ?? {},
    runsQ.data ?? [],
    artListQ.data ?? [],
  );

  if (!nodes.length) {
    return <Empty message="Aucun lien finding↔run↔EDR↔article à afficher. Lie des runs à des EDR (Historique) ou publie un article (Laboratoire)." />;
  }

  const onSelect = (node: ProvNode) => {
    const target = provenanceTarget(node);
    navigate(target.tab as (typeof TAB_KEYS)[number], target.query);
  };

  return (
    <div className="provenance-view">
      <h2>Provenance — toile EDR ↔ condition ↔ article</h2>
      <div className="row mb-4" style={{ gap: "var(--space-4)" }}>
        <span><span className="legend-dot" style={{ background: "var(--viz-1)" }} /> Condition</span>
        <span><span className="legend-dot" style={{ background: "var(--viz-2)" }} /> EDR</span>
        <span><span className="legend-dot" style={{ background: "var(--viz-3)" }} /> Article</span>
      </div>
      <ProvenanceGraph nodes={nodes} edges={edges} onSelect={onSelect} />
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/components/ProvenanceView.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ProvenanceView.tsx frontend/src/components/ProvenanceView.test.tsx
git commit -m "feat(H1): ProvenanceView (4 queries → graphe, états, deep-link au clic)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Intégration — onglet Provenance + lazy

**Files:**
- Modify: `frontend/src/tabs.ts`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `ProvenanceView` (Task 3).

- [ ] **Step 1: Ajouter la clé d'onglet (`tabs.ts`)**

Importer l'icône `Workflow` depuis `lucide-react` (ajouter à l'import existant, en ordre alphabétique). Ajouter `"provenance"` à `TAB_KEYS` **juste après `"timeline"`** (la famille Connaissance est la dernière). Ajouter l'entrée dans la famille « Connaissance » de `TAB_FAMILIES`, après `timeline` :

```ts
      { key: "timeline", label: "Chronologie", icon: History },
      { key: "provenance", label: "Provenance", icon: Workflow },
```

Et insérer `"provenance"` juste après `"timeline"` dans `TAB_KEYS` (même position relative que la famille — `tabs.test.tsx` asserte `buildNavItems(...).map(i => i.id) === TAB_KEYS`).

- [ ] **Step 2: Brancher `ProvenanceView` dans `App.tsx`**

Ajouter le lazy import (après les autres `const … = lazy(...)`) :

```tsx
const ProvenanceView = lazy(() => import("./components/ProvenanceView").then((m) => ({ default: m.ProvenanceView })));
```

Ajouter la branche de rendu (après `tab === "timeline"`) :

```tsx
          {tab === "timeline" && <TimelineViewer />}
          {tab === "provenance" && <ProvenanceView />}
```

(`provenance` PAS dans `showSidebar` → pleine largeur. Laisser `showSidebar` inchangé.)

- [ ] **Step 3: Vérifier build + suite complète**

Run: `npm --prefix frontend run build`
Expected: build OK (tsc + vite).

Run: `npm --prefix frontend run test`
Expected: tous les tests passent (dont `tabs.test.tsx` — `provenance` ajouté de façon cohérente dans `TAB_KEYS` et la famille).

- [ ] **Step 4: Vérification manuelle (dev)**

Run: `npm --prefix frontend run dev`
Vérifier : onglet « Provenance » dans la famille Connaissance ; sans liens, état `Empty` sans crash ; un clic sur un nœud navigue vers l'onglet attendu (condition→Comparaison `?ab=`, EDR→EDR, article→Laboratoire).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/tabs.ts frontend/src/App.tsx
git commit -m "feat(H1): intégrer l'onglet Provenance (famille Connaissance) + lazy-load

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (effectuée)

- **Couverture du spec :** `buildProvenanceGraph` (granularité condition, dédup, orphelins exclus, labels) + `provenanceTarget` (deep-link) en Task 1 ; `ProvenanceGraph` D3 typé clic→onSelect en Task 2 ; `ProvenanceView` 4 queries/états/légende/deep-link en Task 3 ; onglet Connaissance + lazy en Task 4. 100% frontend, aucun endpoint créé. v1 sans run-level/filtres (YAGNI).
- **Placeholders :** aucun — code complet à chaque step.
- **Cohérence des types :** `ProvNode`/`ProvEdge`/`ProvNodeType`/`buildProvenanceGraph(...)`/`provenanceTarget(...)`/`ProvenanceGraph({nodes,edges,onSelect})` cohérents Tasks 1→3 ; ids namespacés `cond:`/`edr:`/`art:` ; `provenanceTarget` utilise `node.label` (= name brut de condition) pour `ab`.
- **D3/jsdom :** logique testée = `buildProvenanceGraph`/`provenanceTarget` (purs) + `ProvenanceView` (états/légende) ; `ProvenanceGraph` = montage svg + cercles (D3 rend les éléments même sans géométrie en jsdom). Le clic→navigate est couvert indirectement (provenanceTarget pur testé + onSelect câblé).
- **Frontière :** `frontend/src/**` + `docs/**` uniquement. Aucun conflit avec `feat/d1-prod-pairing`.
