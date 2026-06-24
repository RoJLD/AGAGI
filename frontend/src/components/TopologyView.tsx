// frontend/src/components/TopologyView.tsx
import { useQuery } from "@tanstack/react-query";
import type { ExperimentDetail } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { useHashRoute } from "../hooks/useHashRoute";
import { TAB_KEYS } from "../tabs";
import { TopologyViewer } from "./TopologyViewer";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";

export function TopologyView() {
  const { gate } = useHashRoute(TAB_KEYS, "edr");
  const { data: detail = null, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.experiments.detail(gate),
    queryFn: () => apiFetch<ExperimentDetail>(`/api/experiments/${gate}`),
    enabled: !!gate,
  });

  return (
    <>
      <h2>Topologie du meilleur modèle</h2>
      <div className="topology-grid">
        <div className="topology-visual">
          {detail?.graph ? <TopologyViewer graph={detail.graph} /> : <p>Topologie indisponible.</p>}
        </div>
        <div className="topology-analysis">
          <h3>Analyse des motifs</h3>
          {detail?.metrics ? (
            <div className="motif-summary">
              <p>Modularité : {detail.metrics.modularity.toFixed(3)}</p>
              <p>Densité de motifs : {detail.metrics.motif_density.toFixed(3)}</p>
              <p>Stabilité : {detail.metrics.performance_stability.toFixed(3)}</p>
              <p>Robustesse : {detail.metrics.robustness_score.toFixed(3)}</p>
              <p>Sparsité : {detail.metrics.sparsity.toFixed(3)}</p>
              <p>Ratio caché : {detail.metrics.hidden_ratio.toFixed(3)}</p>
            </div>
          ) : !gate ? (
            <Empty message="Sélectionne une porte pour voir l'analyse des motifs." />
          ) : isLoading ? (
            <Loading label="Chargement de l'analyse…" />
          ) : error ? (
            <ErrorState error={error} onRetry={() => refetch()} />
          ) : (
            <Empty message="Aucune métrique de topologie pour cette porte." />
          )}
        </div>
      </div>
    </>
  );
}
