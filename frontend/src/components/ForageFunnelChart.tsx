import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  LabelList,
} from "recharts";
import { cssVar, vizColors } from "../theme";
import type { ForageBar } from "../lib/forage";

interface ForageFunnelChartProps {
  bars: ForageBar[];
  title: string;
}

/** Barres horizontales d'un entonnoir de forage (probabilité 0-1 + % par étage). */
export function ForageFunnelChart({ bars, title }: ForageFunnelChartProps) {
  const viz = vizColors();
  return (
    <div className="forage-chart">
      <h4 style={{ margin: "0 0 var(--space-2)" }}>{title}</h4>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={bars} layout="vertical" margin={{ top: 8, right: 56, bottom: 20, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={cssVar("--color-border")} horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 1]}
            stroke={cssVar("--color-text-dim")}
            fontSize={11}
            label={{ value: "probabilité", position: "insideBottom", offset: -8, fill: cssVar("--color-text-dim") }}
          />
          <YAxis type="category" dataKey="name" width={140} stroke={cssVar("--color-text-dim")} fontSize={11} />
          <RechartsTooltip
            contentStyle={{ backgroundColor: cssVar("--color-surface"), border: `1px solid ${cssVar("--color-border")}` }}
          />
          <Bar dataKey="value" name="probabilité" isAnimationActive={false}>
            {bars.map((b, i) => (
              <Cell key={b.name} fill={viz[i % viz.length]} />
            ))}
            <LabelList dataKey="pct" position="right" formatter={(v) => `${Number(v).toFixed(1)}%`} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
