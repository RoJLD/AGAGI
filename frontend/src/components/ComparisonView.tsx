// frontend/src/components/ComparisonView.tsx
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ExperimentSummary } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { useHashRoute } from "../hooks/useHashRoute";
import { TAB_KEYS } from "../tabs";
import { Button } from "./ui/Button";
import { ComparisonChart } from "./ComparisonChart";
import { RadarChart } from "./RadarChart";
import { ABComparisonView } from "./ABComparisonView";
import { formatPercentage } from "../lib/charts";

export function ComparisonView({ onBaselineChange }: { onBaselineChange?: (name: string) => void } = {}) {
  const { query } = useHashRoute(TAB_KEYS, "edr");
  const { data: experiments = [] } = useQuery({
    queryKey: queryKeys.experiments.list,
    queryFn: () => apiFetch<ExperimentSummary[]>("/api/experiments"),
    staleTime: 30_000,
  });
  const [compareMode, setCompareMode] = useState<"global" | "ab">("global");

  useEffect(() => {
    if (query.ab) setCompareMode("ab");
  }, [query.ab]);

  return (
    <>
      <div className="row mb-4">
        <Button variant={compareMode === "global" ? "primary" : "ghost"} size="sm" onClick={() => setCompareMode("global")}>
          Vue globale
        </Button>
        <Button variant={compareMode === "ab" ? "primary" : "ghost"} size="sm" onClick={() => setCompareMode("ab")}>
          A/B rigoureux
        </Button>
      </div>
      {compareMode === "ab" ? (
        <>
          <h2>A/B rigoureux (runs multi-seed)</h2>
          <ABComparisonView preselectA={query.ab} onBaselineChange={onBaselineChange} />
        </>
      ) : (
        <>
          <h2>Comparaison des portes</h2>
          <ComparisonChart experiments={experiments} />
          <RadarChart experiments={experiments} />
          <div className="comparison-list">
            {experiments.map((item) => (
              <div key={item.gate} className="comparison-card">
                <strong>{item.gate}</strong>
                <span>Fitness: {item.latest_fitness.toFixed(3)}</span>
                <span>Précision: {formatPercentage(item.latest_accuracy)}</span>
                {item.robustness_score !== undefined && <span>Robustesse: {item.robustness_score.toFixed(3)}</span>}
                {item.performance_stability !== undefined && <span>Stabilité: {item.performance_stability.toFixed(3)}</span>}
                {item.hidden_ratio !== undefined && <span>Ratio caché: {item.hidden_ratio.toFixed(3)}</span>}
                {item.num_nodes !== undefined && <span>Nœuds: {item.num_nodes}</span>}
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}
