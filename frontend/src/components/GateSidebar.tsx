// frontend/src/components/GateSidebar.tsx
import { useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ExperimentSummary } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { useHashRoute } from "../hooks/useHashRoute";
import { TAB_KEYS } from "../tabs";
import { formatPercentage } from "../lib/charts";

export function GateSidebar() {
  const { gate: selectedGate, setGate } = useHashRoute(TAB_KEYS, "edr");
  const { data: experiments = [] } = useQuery({
    queryKey: queryKeys.experiments.list,
    queryFn: () => apiFetch<ExperimentSummary[]>("/api/experiments"),
    staleTime: 30_000,
  });

  const selectedExperiment = useMemo(
    () => experiments.find((item) => item.gate === selectedGate),
    [experiments, selectedGate],
  );

  const summaryMetrics = useMemo(() => {
    if (!experiments.length) return null;
    const fitnessValues = experiments.map((item) => item.latest_fitness);
    const accuracyValues = experiments.map((item) => item.latest_accuracy);
    const sizes = experiments.flatMap((item) => (item.latest_size !== undefined ? [item.latest_size] : []));
    const bestFitness = experiments.reduce((best, current) => (current.latest_fitness > best.latest_fitness ? current : best), experiments[0]);
    const bestAccuracy = experiments.reduce((best, current) => (current.latest_accuracy > best.latest_accuracy ? current : best), experiments[0]);
    const emergentScores = experiments.flatMap((item) => (item.emergent_score !== undefined ? [item.emergent_score] : []));
    const robustnessScores = experiments.flatMap((item) => (item.robustness_score !== undefined ? [item.robustness_score] : []));
    const stabilityScores = experiments.flatMap((item) => (item.performance_stability !== undefined ? [item.performance_stability] : []));
    return {
      count: experiments.length,
      averageFitness: fitnessValues.reduce((sum, value) => sum + value, 0) / fitnessValues.length,
      averageAccuracy: accuracyValues.reduce((sum, value) => sum + value, 0) / accuracyValues.length,
      averageEmergentScore: emergentScores.length ? emergentScores.reduce((sum, value) => sum + value, 0) / emergentScores.length : 0,
      averageRobustness: robustnessScores.length ? robustnessScores.reduce((sum, value) => sum + value, 0) / robustnessScores.length : 0,
      averageStability: stabilityScores.length ? stabilityScores.reduce((sum, value) => sum + value, 0) / stabilityScores.length : 0,
      bestFitnessGate: bestFitness.gate,
      bestAccuracyGate: bestAccuracy.gate,
      bestEmergentGate: experiments.reduce((best, current) => (current.emergent_score !== undefined && current.emergent_score > (best.emergent_score ?? -Infinity) ? current : best), experiments[0]).gate,
      smallestSize: sizes.length ? Math.min(...sizes) : undefined,
    };
  }, [experiments]);

  useEffect(() => {
    if (experiments.length && !selectedGate) {
      setGate(experiments[0].gate);
    }
  }, [experiments, selectedGate]);

  return (
    <aside className="sidebar">
      <label htmlFor="gate-select">Sélectionner une porte</label>
      <select id="gate-select" value={selectedGate} onChange={(event) => setGate(event.target.value)}>
        {experiments.map((experiment) => (
          <option key={experiment.gate} value={experiment.gate}>
            {experiment.gate}
          </option>
        ))}
      </select>

      {summaryMetrics ? (
        <div className="summary-panel">
          <h2>Vue globale</h2>
          <p>Total portes : {summaryMetrics.count}</p>
          <p>Meilleure fitness : {summaryMetrics.bestFitnessGate}</p>
          <p>Meilleure précision : {summaryMetrics.bestAccuracyGate}</p>
          <p>Meilleur score d'intelligence : {summaryMetrics.bestEmergentGate}</p>
          <p>Fitness moyenne : {summaryMetrics.averageFitness.toFixed(4)}</p>
          <p>Précision moyenne : {formatPercentage(summaryMetrics.averageAccuracy)}</p>
          <p>Score d'intelligence moyen : {summaryMetrics.averageEmergentScore.toFixed(3)}</p>
          <p>Robustesse moyenne : {summaryMetrics.averageRobustness.toFixed(3)}</p>
          <p>Stabilité moyenne : {summaryMetrics.averageStability.toFixed(3)}</p>
          {summaryMetrics.smallestSize !== undefined && <p>Plus petite topologie : {summaryMetrics.smallestSize}</p>}
        </div>
      ) : null}

      {selectedExperiment ? (
        <div className="metrics-panel">
          <h2>{selectedExperiment.gate}</h2>
          <p>Fitness finale : {selectedExperiment.latest_fitness.toFixed(4)}</p>
          <p>Précision finale : {formatPercentage(selectedExperiment.latest_accuracy)}</p>
          {selectedExperiment.emergent_score !== undefined && <p>Score d'intelligence : {selectedExperiment.emergent_score.toFixed(3)}</p>}
          {selectedExperiment.robustness_score !== undefined && <p>Robustesse : {selectedExperiment.robustness_score.toFixed(3)}</p>}
          {selectedExperiment.performance_stability !== undefined && <p>Stabilité : {selectedExperiment.performance_stability.toFixed(3)}</p>}
          {selectedExperiment.modularity !== undefined && <p>Modularité : {selectedExperiment.modularity.toFixed(3)}</p>}
          {selectedExperiment.motif_density !== undefined && <p>Densité de motifs : {selectedExperiment.motif_density.toFixed(3)}</p>}
          {selectedExperiment.latest_size !== undefined && <p>Taille finale : {selectedExperiment.latest_size}</p>}
        </div>
      ) : null}
    </aside>
  );
}
