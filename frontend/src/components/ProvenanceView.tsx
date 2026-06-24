// frontend/src/components/ProvenanceView.tsx
import { useCallback } from "react";
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

  const onSelect = useCallback((node: ProvNode) => {
    const target = provenanceTarget(node);
    navigate(target.tab, target.query);
  }, [navigate]);

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
