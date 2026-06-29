import { useEffect, useRef, useState } from "react";
import { useWebSocket } from "../hooks/useWebSocket";

interface Entity {
  x: number;
  y: number;
}

interface Agent extends Entity {
  hp: number;
  energy: number;
  inventory_size: number;
  last_action: number;
}

interface Prey extends Entity {
  type: string;
  hp: number;
  stunned: number;
}

interface Item extends Entity {
  type: string;
}

interface FlatlandSummary {
  agent_count: number;
  avg_energy: number;
  avg_hp: number;
  energy_std: number;
  hp_std: number;
  social_density: number;
  genome_diversity: number;
  prey_count: number;
  item_count: number;
  altar_count: number;
}

interface FlatlandFrame {
  ticks: number;
  size: number;
  agents: Agent[];
  preys: Prey[];
  items: Item[];
  worms: Entity[];
  altars: Entity[];
  terrain_type: number[][];
  geometry: number[][];
  summary?: FlatlandSummary;
}

const TILE_SIZE = 32;

export function FlatlandViewer() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [frame, setFrame] = useState<FlatlandFrame | null>(null);

  // Viewport state
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const isDragging = useRef(false);
  const lastMouse = useRef({ x: 0, y: 0 });

  useWebSocket<FlatlandFrame>("/ws/flatland", (f) => setFrame(f));

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !frame) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();

    // Center map
    ctx.translate(canvas.width / 2 + offset.x, canvas.height / 2 + offset.y);
    ctx.scale(scale, scale);
    ctx.translate(-(frame.size * TILE_SIZE) / 2, -(frame.size * TILE_SIZE) / 2);

    // Draw terrain & geometry
    for (let y = 0; y < frame.size; y++) {
      for (let x = 0; x < frame.size; x++) {
        const terrain = frame.terrain_type[y][x];
        const geo = frame.geometry[y][x];

        // Terrain colors
        if (terrain === 0) ctx.fillStyle = "#84cc6c"; // Plains
        else if (terrain === 1) ctx.fillStyle = "#2d7a36"; // Forest
        else if (terrain === 2) ctx.fillStyle = "#5c92ff"; // Water
        else if (terrain === 3) ctx.fillStyle = "#f5d173"; // Desert
        ctx.fillRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE);

        // Geometry (Walls, Trees, etc)
        if (geo > 0) {
          if (geo === 1) ctx.fillStyle = "#555"; // Wall
          else if (geo === 2) ctx.fillStyle = "#777"; // Low wall
          else if (geo === 3) ctx.fillStyle = "#333"; // Ceiling
          else if (geo === 4) ctx.fillStyle = "#5c4033"; // Trunk
          else if (geo === 5) ctx.fillStyle = "#228b22"; // Leaves
          ctx.fillRect(x * TILE_SIZE + 4, y * TILE_SIZE + 4, TILE_SIZE - 8, TILE_SIZE - 8);
        }
      }
    }

    // Draw Altars
    for (const alt of frame.altars) {
      ctx.fillStyle = "purple";
      ctx.beginPath();
      ctx.arc(alt.x * TILE_SIZE + TILE_SIZE / 2, alt.y * TILE_SIZE + TILE_SIZE / 2, 10, 0, Math.PI * 2);
      ctx.fill();
    }

    // Draw Items
    for (const it of frame.items) {
      ctx.fillStyle = "orange";
      ctx.beginPath();
      ctx.arc(it.x * TILE_SIZE + TILE_SIZE / 2, it.y * TILE_SIZE + TILE_SIZE / 2, 5, 0, Math.PI * 2);
      ctx.fill();
    }

    // Draw Worms
    for (const w of frame.worms) {
      ctx.fillStyle = "pink";
      ctx.beginPath();
      ctx.arc(w.x * TILE_SIZE + TILE_SIZE / 2, w.y * TILE_SIZE + TILE_SIZE / 2, 4, 0, Math.PI * 2);
      ctx.fill();
    }

    // Draw Preys
    for (const p of frame.preys) {
      ctx.fillStyle = p.stunned > 0 ? "grey" : (p.type === "Lapin" ? "white" : p.type === "Cerf" ? "brown" : p.type === "Sanglier" ? "darkred" : "darkblue");
      ctx.beginPath();
      ctx.arc(p.x * TILE_SIZE + TILE_SIZE / 2, p.y * TILE_SIZE + TILE_SIZE / 2, 12, 0, Math.PI * 2);
      ctx.fill();
    }

    // Draw Agents
    for (const a of frame.agents) {
      ctx.fillStyle = "cyan";
      ctx.beginPath();
      ctx.arc(a.x * TILE_SIZE + TILE_SIZE / 2, a.y * TILE_SIZE + TILE_SIZE / 2, 14, 0, Math.PI * 2);
      ctx.fill();

      // HP bar
      ctx.fillStyle = "red";
      ctx.fillRect(a.x * TILE_SIZE, a.y * TILE_SIZE - 6, TILE_SIZE, 4);
      ctx.fillStyle = "green";
      ctx.fillRect(a.x * TILE_SIZE, a.y * TILE_SIZE - 6, TILE_SIZE * (a.hp / 100), 4);
    }

    ctx.restore();
  }, [frame, scale, offset]);

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    setScale((s) => Math.max(0.2, Math.min(5, s - e.deltaY * 0.001)));
  };

  const handlePointerDown = (e: React.PointerEvent) => {
    isDragging.current = true;
    lastMouse.current = { x: e.clientX, y: e.clientY };
    (e.target as Element).setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDragging.current) return;
    const dx = e.clientX - lastMouse.current.x;
    const dy = e.clientY - lastMouse.current.y;
    setOffset((prev) => ({ x: prev.x + dx, y: prev.y + dy }));
    lastMouse.current = { x: e.clientX, y: e.clientY };
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    isDragging.current = false;
    (e.target as Element).releasePointerCapture(e.pointerId);
  };

  return (
    <div className="flatland-frame">
      <div className="flatland-overlay">
        <div style={{ fontWeight: 700, marginBottom: 6 }}>Flatland Metrics</div>
        <div>Ticks: {frame?.ticks || 0}</div>
        <div>Agents: {frame?.agents.length || 0}</div>
        {frame?.summary ? (
          <>
            <div>Énergie moyenne: {frame.summary.avg_energy.toFixed(1)}</div>
            <div>HP moyenne: {frame.summary.avg_hp.toFixed(1)}</div>
            <div>σ énergie: {frame.summary.energy_std.toFixed(1)}</div>
            <div>σ HP: {frame.summary.hp_std.toFixed(1)}</div>
            <div>Densité sociale: {frame.summary.social_density.toFixed(2)}</div>
            <div>Diversité génétique: {frame.summary.genome_diversity.toFixed(1)}</div>
            <div>Proies: {frame.summary.prey_count}</div>
            <div>Objets: {frame.summary.item_count}</div>
            <div>Autels: {frame.summary.altar_count}</div>
          </>
        ) : null}
      </div>
      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        role="img"
        aria-label="Carte Flatland 2D (terrain, agents, proies, objets)"
        style={{ width: "100%", height: "100%", touchAction: "none", cursor: "grab" }}
        onWheel={handleWheel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
      />
    </div>
  );
}
