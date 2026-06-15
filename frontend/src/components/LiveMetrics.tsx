import { useRef, useState } from "react";
import { useWebSocket } from "../hooks/useWebSocket";
import { Badge } from "./ui/Badge";

const MAX = 160;

type Point = { energy: number; agents: number };

function liveSparkline(values: number[], color: string, w = 640, h = 120) {
  if (!values.length) return null;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const sx = (i: number) => (i / Math.max(values.length - 1, 1)) * w;
  const sy = (v: number) => h - ((v - min) / (max - min || 1)) * h;
  const d = values.map((v, i) => `${i === 0 ? "M" : "L"} ${sx(i)} ${sy(v)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="chart-svg" preserveAspectRatio="none">
      <path d={d} fill="none" style={{ stroke: color }} strokeWidth={2.5} />
    </svg>
  );
}

export function LiveMetrics() {
  const [points, setPoints] = useState<Point[]>([]);
  const [era, setEra] = useState<number>(0);
  const bufRef = useRef<Point[]>([]);

  const { status: wsStatus } = useWebSocket<{ summary?: { era?: number; avg_energy?: number; agent_count?: number } }>(
    "/ws/flatland",
    (frame) => {
      const s = frame.summary ?? {};
      setEra(s.era ?? 0);
      const next = [...bufRef.current, { energy: s.avg_energy ?? 0, agents: s.agent_count ?? 0 }].slice(-MAX);
      bufRef.current = next;
      setPoints(next);
    },
  );

  const statusLabel =
    wsStatus === "open" ? "en direct" : wsStatus === "connecting" ? "connexion…" : "hors-ligne (backend ?)";
  const last = points[points.length - 1];
  return (
    <div className="edr-dashboard">
      <h2>Biosphère en direct</h2>
      <p className="edr-intro">
        Run évolutive réelle servie par <code>flatland_server</code> (la population descend du Hall of
        Fame, qui s'améliore à chaque ère). État : <strong>{statusLabel}</strong>.
      </p>
      <div className="live-stats">
        <div className="live-stat"><span>Ère</span><strong>{era}</strong></div>
        <div className="live-stat"><span>Agents vivants</span><strong>{last?.agents ?? "—"}</strong></div>
        <div className="live-stat"><span>Énergie moyenne</span><strong>{last ? last.energy.toFixed(1) : "—"}</strong></div>
        <div className="live-stat"><span>Frames</span><strong>{points.length}</strong></div>
      </div>
      <div className="edr-grid">
        <article className="edr-card">
          <header className="edr-card-head"><Badge variant="teal">LIVE</Badge><h3>Énergie moyenne</h3></header>
          {liveSparkline(points.map((p) => p.energy), "var(--viz-1)")}
        </article>
        <article className="edr-card">
          <header className="edr-card-head"><Badge variant="teal">LIVE</Badge><h3>Agents vivants (extinction → nouvelle ère)</h3></header>
          {liveSparkline(points.map((p) => p.agents), "var(--viz-2)")}
        </article>
      </div>
    </div>
  );
}
