// frontend/src/components/LiveEvolution.tsx
import { useRef, useState } from "react";
import { useWebSocket } from "../hooks/useWebSocket";
import { Badge } from "./ui/Badge";

type EvoEvent = {
  run?: string; gate?: string; generation?: number;
  fitness?: number; accuracy?: number | null; size?: number | null;
};
type Point = { generation: number; fitness: number };

const MAX = 200;

function sparkline(values: number[], color: string, w = 640, h = 120) {
  if (!values.length) return null;
  const max = Math.max(...values, 1e-9);
  const min = Math.min(...values, 0);
  const sx = (i: number) => (i / Math.max(values.length - 1, 1)) * w;
  const sy = (v: number) => h - ((v - min) / (max - min || 1)) * h;
  const d = values.map((v, i) => `${i === 0 ? "M" : "L"} ${sx(i)} ${sy(v)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="chart-svg" preserveAspectRatio="none" role="img" aria-label="évolution live">
      <path d={d} fill="none" style={{ stroke: color }} strokeWidth={2.5} />
    </svg>
  );
}

export function LiveEvolution() {
  const [points, setPoints] = useState<Point[]>([]);
  const [run, setRun] = useState<string>("");
  const bufRef = useRef<Point[]>([]);

  const { status } = useWebSocket<EvoEvent>("/ws/evolution", (e) => {
    if (typeof e.fitness !== "number" || typeof e.generation !== "number") return;
    setRun(e.run ?? e.gate ?? "");
    const next = [...bufRef.current, { generation: e.generation, fitness: e.fitness }].slice(-MAX);
    bufRef.current = next;
    setPoints(next);
  });

  const statusLabel = status === "open" ? "connecté" : status === "connecting" ? "connexion…" : "hors-ligne";
  const last = points[points.length - 1];

  return (
    <div className="edr-dashboard">
      <h2>Évolution en direct</h2>
      <p className="edr-intro">
        Métriques par génération d'un run lancé via le Bac à sable, streamées en direct
        (<code>/ws/evolution</code>). WS : <strong>{statusLabel}</strong>.
      </p>
      {points.length === 0 ? (
        <p className="text-dim">Aucun run en cours — lance une expérience via le Bac à sable.</p>
      ) : (
        <>
          <div className="live-stats">
            <div className="live-stat"><span>Run</span><strong>{run || "—"}</strong></div>
            <div className="live-stat"><span>Génération</span><strong>{last?.generation ?? "—"}</strong></div>
            <div className="live-stat"><span>Fitness</span><strong>{last ? last.fitness.toFixed(4) : "—"}</strong></div>
            <div className="live-stat"><span>Points</span><strong>{points.length}</strong></div>
          </div>
          <article className="edr-card">
            <header className="edr-card-head"><Badge variant="teal">LIVE</Badge><h3>Fitness par génération</h3></header>
            {sparkline(points.map((p) => p.fitness), "var(--viz-1)")}
          </article>
        </>
      )}
    </div>
  );
}
