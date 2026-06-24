// frontend/src/components/EvolutionView.tsx
import { useQuery } from "@tanstack/react-query";
import type { ExperimentDetail } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { useHashRoute } from "../hooks/useHashRoute";
import { TAB_KEYS } from "../tabs";
import { LiveEvolution } from "./LiveEvolution";
import { createLinePath, createStabilitySeries } from "../lib/charts";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";

function ChartLine({ values, color }: { values: number[]; color: string }) {
  return <path d={createLinePath(values, 700, 260)} fill="none" style={{ stroke: color }} strokeWidth={3} />;
}

export function EvolutionView() {
  const { gate } = useHashRoute(TAB_KEYS, "edr");
  const { data: detail = null, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.experiments.detail(gate),
    queryFn: () => apiFetch<ExperimentDetail>(`/api/experiments/${gate}`),
    enabled: !!gate,
  });

  const chartData = detail?.history;
  const sizeSeries = chartData?.size ?? [];
  const stabilitySeries = chartData ? createStabilitySeries(chartData.accuracy) : [];

  return (
    <>
      <LiveEvolution />
      <h2>Évolution dynamique</h2>
      {chartData ? (
        <>
          <svg viewBox="0 0 720 300" className="chart-svg" aria-label="Evolution chart">
            <ChartLine values={chartData.fitness} color="var(--viz-1)" />
            <ChartLine values={chartData.accuracy} color="var(--viz-2)" />
            {sizeSeries.length ? <ChartLine values={sizeSeries.map((value: number) => value / Math.max(...sizeSeries, 1))} color="var(--color-text-dim)" /> : null}
            {stabilitySeries.length ? <ChartLine values={stabilitySeries} color="var(--viz-4)" /> : null}
          </svg>
          <div className="legend-row">
            <span className="legend-dot" style={{ background: "var(--viz-1)" }} /> Fitness
            <span className="legend-dot" style={{ background: "var(--viz-2)" }} /> Précision
            <span className="legend-dot" style={{ background: "var(--color-text-dim)" }} /> Taille normalisée
            <span className="legend-dot" style={{ background: "var(--viz-4)" }} /> Stabilité
          </div>
        </>
      ) : !gate ? (
        <Empty message="Sélectionne une porte dans la barre latérale pour voir son évolution." />
      ) : isLoading ? (
        <Loading label="Chargement des données d'évolution…" />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : (
        <Empty message="Aucune donnée d'évolution pour cette porte." />
      )}
    </>
  );
}
