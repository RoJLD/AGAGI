import type { ExperimentSummary } from "../types";

const palette = ["#0f766e", "#be123c", "#7c3aed", "#c2410c", "#2563eb", "#0d9488"];

const metrics = [
  { key: "latest_fitness" as const, label: "Fitness", maxScale: 1.0 },
  { key: "latest_accuracy" as const, label: "Précision", maxScale: 1.0 },
  { key: "emergent_score" as const, label: "Intelligence", maxScale: 1.0 },
  { key: "performance_stability" as const, label: "Stabilité", maxScale: 1.0 },
  { key: "robustness_score" as const, label: "Robustesse", maxScale: 1.0 },
];

type RadarChartProps = {
  experiments: ExperimentSummary[];
};

function toRadians(deg: number) {
  return (deg * Math.PI) / 180;
}

function polygonPoints(values: number[], radius: number, center: number) {
  const step = 360 / values.length;
  return values
    .map((value, index) => {
      const angle = toRadians(index * step - 90);
      const x = center + Math.cos(angle) * value * radius;
      const y = center + Math.sin(angle) * value * radius;
      return `${x},${y}`;
    })
    .join(" ");
}

export function RadarChart({ experiments }: RadarChartProps) {
  if (!experiments.length) {
    return <p>Aucune donnée pour le radar chart.</p>;
  }

  const radius = 160;
  const center = 180;
  const gridSteps = 4;

  const maxValues = {
    latest_fitness: Math.max(...experiments.map((item) => item.latest_fitness), 1),
    latest_accuracy: 1,
    emergent_score: Math.max(...experiments.map((item) => item.emergent_score ?? 0), 1),
    performance_stability: Math.max(...experiments.map((item) => item.performance_stability ?? 0), 1),
    robustness_score: Math.max(...experiments.map((item) => item.robustness_score ?? 0), 1),
  };

  const axes = metrics.map((metric, index) => {
    const angle = toRadians(index * (360 / metrics.length) - 90);
    return {
      x: center + Math.cos(angle) * radius,
      y: center + Math.sin(angle) * radius,
      label: metric.label,
    };
  });

  return (
    <div className="radar-chart">
      <h3>Radar des performances</h3>
      <svg width={360} height={360} viewBox="0 0 360 360" aria-label="Radar chart des performances">
        {[...Array(gridSteps)].map((_, index) => {
          const level = (index + 1) / gridSteps;
          const points = metrics.map((metric, metricIndex) => {
            const angle = toRadians(metricIndex * (360 / metrics.length) - 90);
            const value = level * radius;
            return `${center + Math.cos(angle) * value},${center + Math.sin(angle) * value}`;
          });

          return (
            <polygon
              key={`grid-${index}`}
              points={points.join(" ")}
              fill="none"
              stroke="#cbd5e1"
              strokeWidth={1}
            />
          );
        })}

        {axes.map((axis, index) => (
          <g key={`axis-${index}`}>
            <line
              x1={center}
              y1={center}
              x2={axis.x}
              y2={axis.y}
              stroke="#e2e8f0"
              strokeWidth={1}
            />
            <text x={axis.x} y={axis.y} dy={axis.y < center ? -10 : 18} textAnchor="middle" fontSize={11} fill="#0f172a">
              {axis.label}
            </text>
          </g>
        ))}

        {experiments.map((experiment, experimentIndex) => {
          const values = metrics.map((metric) => (experiment[metric.key] ?? 0) / maxValues[metric.key]);
          return (
            <polygon
              key={experiment.gate}
              points={polygonPoints(values, radius, center)}
              fill={palette[experimentIndex % palette.length]}
              fillOpacity={0.2}
              stroke={palette[experimentIndex % palette.length]}
              strokeWidth={2}
            />
          );
        })}

        {experiments.map((experiment, experimentIndex) => {
          const values = metrics.map((metric) => (experiment[metric.key] ?? 0) / maxValues[metric.key]);
          return values.map((value, valueIndex) => {
            const angle = toRadians(valueIndex * (360 / metrics.length) - 90);
            return (
              <circle
                key={`${experiment.gate}-${valueIndex}`}
                cx={center + Math.cos(angle) * value * radius}
                cy={center + Math.sin(angle) * value * radius}
                r={4}
                fill={palette[experimentIndex % palette.length]}
              />
            );
          });
        })}
      </svg>
      <div className="radar-legend">
        {experiments.map((experiment, index) => (
          <div key={experiment.gate} className="radar-legend-item">
            <span className="radar-legend-color" style={{ background: palette[index % palette.length] }} />
            <span>{experiment.gate}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
