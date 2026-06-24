import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from "recharts";
import { cssVar, vizColors } from "../theme";
import { buildSweepData } from "../lib/sweep";

interface SweepChartProps {
  x: number[];
  knob: string;
  metric: string;
  y: number[];
  yStd?: number[];
}

/** Paysage de paramètres : métrique Y le long du paramètre balayé (knob) en X,
 *  + bande de variance ±std si fournie. recharts, couleurs thème-aware. */
export function SweepChart({ x, knob, metric, y, yStd }: SweepChartProps) {
  const viz = vizColors();
  const data = buildSweepData(x, y, yStd);
  const hasBand = data.some((p) => p.band !== undefined);

  return (
    <ResponsiveContainer width="100%" height={360}>
      <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 28, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={cssVar("--color-border")} />
        <XAxis
          dataKey="x"
          type="number"
          domain={["auto", "auto"]}
          stroke={cssVar("--color-text-dim")}
          fontSize={11}
          label={{ value: knob, position: "insideBottom", offset: -14, fill: cssVar("--color-text-dim") }}
        />
        <YAxis
          stroke={cssVar("--color-text-dim")}
          fontSize={11}
          label={{ value: metric, angle: -90, position: "insideLeft", fill: cssVar("--color-text-dim") }}
        />
        <RechartsTooltip
          contentStyle={{ backgroundColor: cssVar("--color-surface"), border: `1px solid ${cssVar("--color-border")}` }}
        />
        {hasBand ? <Area dataKey="band" stroke="none" fill={viz[0]} fillOpacity={0.15} name="±écart-type" isAnimationActive={false} /> : null}
        <Line type="monotone" dataKey="y" stroke={viz[0]} strokeWidth={2.5} name={metric} isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
