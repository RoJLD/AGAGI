import type { ExperimentSummary } from "../types";

type ComparisonChartProps = {
  experiments: ExperimentSummary[];
};

const metricDefinitions = [
  {
    key: "latest_fitness" as const,
    label: "Fitness finale",
    color: "var(--viz-1)",
    format: (value: number) => value.toFixed(3),
  },
  {
    key: "latest_accuracy" as const,
    label: "Précision finale",
    color: "var(--viz-2)",
    format: (value: number) => `${(value * 100).toFixed(1)}%`,
  },
  {
    key: "emergent_score" as const,
    label: "Score d'intelligence",
    color: "var(--viz-3)",
    format: (value: number) => value.toFixed(3),
  },
  {
    key: "robustness_score" as const,
    label: "Robustesse",
    color: "var(--viz-4)",
    format: (value: number) => value.toFixed(3),
  },
];

export function ComparisonChart({ experiments }: ComparisonChartProps) {
  if (!experiments.length) {
    return <p>Aucune donnée comparative disponible.</p>;
  }

  const maxValues = {
    latest_fitness: Math.max(...experiments.map((item) => item.latest_fitness), 1),
    latest_accuracy: 1,
    emergent_score: Math.max(...experiments.map((item) => item.emergent_score ?? 0), 1),
    robustness_score: Math.max(...experiments.map((item) => item.robustness_score ?? 0), 1),
  };

  return (
    <div className="comparison-chart">
      {metricDefinitions.map((metric) => (
        <div key={metric.key} className="comparison-metric-group">
          <h3>{metric.label}</h3>
          <div className="comparison-metric-rows">
            {experiments.map((experiment) => {
              const value = experiment[metric.key] ?? 0;
              const percent = Math.round((value / maxValues[metric.key]) * 100);

              return (
                <div key={experiment.gate} className="comparison-metric-row">
                  <div className="comparison-metric-info">
                    <span className="comparison-gate-name">{experiment.gate}</span>
                    <span className="comparison-value">{metric.format(value)}</span>
                  </div>
                  <div className="comparison-bar-track">
                    <div
                      className="comparison-bar-fill"
                      style={{ width: `${percent}%`, background: metric.color }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
