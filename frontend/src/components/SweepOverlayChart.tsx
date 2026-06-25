import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from "recharts";
import { cssVar, vizColors } from "../theme";
import { buildOverlayData, type OverlaySeries } from "../lib/sweep";

interface SweepOverlayChartProps {
  series: OverlaySeries[];
  knob: string;
  normalize: boolean;
}

/** Superposition de séries (sweep × métrique) le long d'un knob.
 *  N lignes colorées ; bande ±std seulement si 1 série en mode brut. */
export function SweepOverlayChart({ series, knob, normalize }: SweepOverlayChartProps) {
  const viz = vizColors();
  const data = buildOverlayData(series, normalize);
  const bandKey = series.length === 1 ? `${series[0].id}__band` : null;
  const hasBand = bandKey !== null && data.some((p) => p[bandKey] !== undefined);

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
          label={{
            value: normalize ? "valeur normalisée [0,1]" : "valeur",
            angle: -90,
            position: "insideLeft",
            fill: cssVar("--color-text-dim"),
          }}
        />
        <RechartsTooltip
          contentStyle={{ backgroundColor: cssVar("--color-surface"), border: `1px solid ${cssVar("--color-border")}` }}
        />
        <Legend />
        {hasBand ? (
          <Area dataKey={bandKey!} stroke="none" fill={viz[0]} fillOpacity={0.15} name="±écart-type" isAnimationActive={false} />
        ) : null}
        {series.map((s, i) => (
          <Line
            key={s.id}
            type="monotone"
            dataKey={s.id}
            name={s.label}
            stroke={viz[i % viz.length]}
            strokeWidth={2.5}
            connectNulls
            dot={false}
            isAnimationActive={false}
          />
        ))}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
