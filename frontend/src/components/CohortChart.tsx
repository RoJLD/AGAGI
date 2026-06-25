import { cssVar, vizColors } from "../theme";
import type { CohortRow } from "../lib/cohort";

interface CohortChartProps {
  rows: CohortRow[];
  metric: string;
}

const ROW_H = 46;
const LABEL_W = 160;
const PAD_R = 56;
const PAD_TOP = 16;
const VIEW_W = 840;
const BOX_H = 18;
const JITTER = 14;

/** Box plot horizontal (une ligne par condition) + points par seed jitterés.
 *  SVG auto-rendu, échelle X linéaire partagée. Pas de recharts box natif. */
export function CohortChart({ rows, metric }: CohortChartProps) {
  const viz = vizColors();
  const boxColor = viz[0];
  const accent = viz[2];
  const height = PAD_TOP * 2 + rows.length * ROW_H;

  const all = rows.flatMap((r) => r.vals);
  const lo = all.length ? Math.min(...all) : 0;
  const hi = all.length ? Math.max(...all) : 1;
  const span = hi - lo || 1;
  const x0 = LABEL_W;
  const x1 = VIEW_W - PAD_R;
  const scaleX = (v: number) => x0 + ((v - lo) / span) * (x1 - x0);

  return (
    <svg
      className="cohort-chart"
      width="100%"
      viewBox={`0 0 ${VIEW_W} ${height}`}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label={`Distributions par condition pour la métrique ${metric}`}
    >
      {rows.map((row, ri) => {
        const cy = PAD_TOP + ri * ROW_H + ROW_H / 2;
        const s = row.stats;
        const c = row.vals.length;
        return (
          <g key={row.name} data-testid="cohort-row">
            <title>{`${row.name} — médiane ${s.median.toFixed(3)}, IQR ${s.iqr.toFixed(3)}, n=${s.n}`}</title>
            <text x={LABEL_W - 10} y={cy} textAnchor="end" dominantBaseline="middle" fontSize={12} fill={cssVar("--color-text")}>
              {row.name}
            </text>
            <line x1={scaleX(s.lowerWhisker)} x2={scaleX(s.upperWhisker)} y1={cy} y2={cy} stroke={cssVar("--color-text-dim")} strokeWidth={1} />
            <rect x={scaleX(s.q1)} y={cy - BOX_H / 2} width={Math.max(1, scaleX(s.q3) - scaleX(s.q1))} height={BOX_H} fill={boxColor} fillOpacity={0.18} stroke={boxColor} strokeWidth={1.5} />
            <line x1={scaleX(s.median)} x2={scaleX(s.median)} y1={cy - BOX_H / 2} y2={cy + BOX_H / 2} stroke={boxColor} strokeWidth={2.5} />
            {row.vals.map((v, i) => {
              const offset = c > 1 ? (i / (c - 1) - 0.5) * JITTER : 0;
              const isOut = v < s.lowerWhisker || v > s.upperWhisker;
              return (
                <circle
                  key={i}
                  cx={scaleX(v)}
                  cy={cy + offset}
                  r={3}
                  fill={isOut ? accent : boxColor}
                  fillOpacity={isOut ? 0.95 : 0.6}
                  stroke={isOut ? accent : "none"}
                  strokeWidth={isOut ? 1 : 0}
                />
              );
            })}
            <text x={VIEW_W - PAD_R + 8} y={cy} dominantBaseline="middle" fontSize={11} fill={cssVar("--color-text-dim")}>
              n={s.n}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
