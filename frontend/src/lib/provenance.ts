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
