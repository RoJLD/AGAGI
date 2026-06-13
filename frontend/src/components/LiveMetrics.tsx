import { useEffect, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8001";
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
      <path d={d} fill="none" stroke={color} strokeWidth={2.5} />
    </svg>
  );
}

export function LiveMetrics() {
  const [points, setPoints] = useState<Point[]>([]);
  const [era, setEra] = useState<number>(0);
  const [status, setStatus] = useState<string>("connexion…");
  const bufRef = useRef<Point[]>([]);

  useEffect(() => {
    const wsUrl = API_BASE.replace(/^http/, window.location.protocol === "https:" ? "wss" : "ws");
    const ws = new WebSocket(`${wsUrl}/ws/flatland`);
    ws.addEventListener("open", () => setStatus("en direct"));
    ws.addEventListener("error", () => setStatus("backend hors-ligne (lance uvicorn app.main:app --port 8001)"));
    ws.addEventListener("close", () => setStatus("déconnecté"));
    ws.addEventListener("message", (event) => {
      try {
        const frame = JSON.parse(event.data);
        const s = frame.summary ?? {};
        setEra(s.era ?? 0);
        const next = [...bufRef.current, { energy: s.avg_energy ?? 0, agents: s.agent_count ?? 0 }].slice(-MAX);
        bufRef.current = next;
        setPoints(next);
      } catch {
        /* ignore */
      }
    });
    return () => ws.close();
  }, []);

  const last = points[points.length - 1];
  return (
    <div className="edr-dashboard">
      <h2>Biosphère en direct</h2>
      <p className="edr-intro">
        Run évolutive réelle servie par <code>flatland_server</code> (la population descend du Hall of
        Fame, qui s'améliore à chaque ère). État : <strong>{status}</strong>.
      </p>
      <div className="live-stats">
        <div className="live-stat"><span>Ère</span><strong>{era}</strong></div>
        <div className="live-stat"><span>Agents vivants</span><strong>{last?.agents ?? "—"}</strong></div>
        <div className="live-stat"><span>Énergie moyenne</span><strong>{last ? last.energy.toFixed(1) : "—"}</strong></div>
        <div className="live-stat"><span>Frames</span><strong>{points.length}</strong></div>
      </div>
      <div className="edr-grid">
        <article className="edr-card">
          <header className="edr-card-head"><span className="edr-badge">LIVE</span><h3>Énergie moyenne</h3></header>
          {liveSparkline(points.map((p) => p.energy), "#0f766e")}
        </article>
        <article className="edr-card">
          <header className="edr-card-head"><span className="edr-badge">LIVE</span><h3>Agents vivants (extinction → nouvelle ère)</h3></header>
          {liveSparkline(points.map((p) => p.agents), "#be123c")}
        </article>
      </div>
    </div>
  );
}
