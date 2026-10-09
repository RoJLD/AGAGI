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
  role?: string;
  is_speaking?: boolean;
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
  season?: string | null;
  granary_reserves?: number | null;
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
  season?: string | null;
  granary_reserves?: number | null;
  granary?: { x: number; y: number; reserves: number } | null;
  furnace?: { x: number; y: number; heat: number; fuel: number } | null;
  pollution_level?: number | null;
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
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);

  // Viewport state
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const isDragging = useRef(false);
  const lastMouse = useRef({ x: 0, y: 0 });
  const dragDistance = useRef(0);

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

    // Palettes saisonnières pour le sol
    const isWinter = frame.season === "winter";
    const isAutumn = frame.season === "autumn";
    const isSummer = frame.season === "summer";

    // 1. Draw terrain & geometry
    for (let y = 0; y < frame.size; y++) {
      for (let x = 0; x < frame.size; x++) {
        const terrain = frame.terrain_type[y][x];
        const geo = frame.geometry[y][x];

        // Terrain colors adaptatifs selon la saison
        if (terrain === 0) {
          ctx.fillStyle = isWinter ? "#cbd5e1" : isAutumn ? "#d97706" : isSummer ? "#84cc16" : "#84cc6c"; // Plains
        } else if (terrain === 1) {
          ctx.fillStyle = isWinter ? "#64748b" : isAutumn ? "#b45309" : "#2d7a36"; // Forest
        } else if (terrain === 2) {
          ctx.fillStyle = isWinter ? "#93c5fd" : "#5c92ff"; // Water (glacée en hiver)
        } else if (terrain === 3) {
          ctx.fillStyle = "#f5d173"; // Desert
        }
        ctx.fillRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE);

        // Geometry (Walls, Trees, etc)
        if (geo > 0) {
          if (geo === 1) ctx.fillStyle = "#555"; // Wall
          else if (geo === 2) ctx.fillStyle = "#777"; // Low wall
          else if (geo === 3) ctx.fillStyle = "#333"; // Ceiling
          else if (geo === 4) ctx.fillStyle = isWinter ? "#475569" : "#5c4033"; // Trunk
          else if (geo === 5) ctx.fillStyle = isWinter ? "#e2e8f0" : isAutumn ? "#ea580c" : "#228b22"; // Leaves
          ctx.fillRect(x * TILE_SIZE + 4, y * TILE_SIZE + 4, TILE_SIZE - 8, TILE_SIZE - 8);
        }
      }
    }

    // 2. Draw Bâtiments (Grenier & Fourneau)
    if (frame.granary) {
      const gx = frame.granary.x * TILE_SIZE;
      const gy = frame.granary.y * TILE_SIZE;
      // Structure grenier en bois
      ctx.fillStyle = "#78350f";
      ctx.fillRect(gx + 2, gy + 8, TILE_SIZE - 4, TILE_SIZE - 10);
      // Toit triangulaire
      ctx.fillStyle = "#b45309";
      ctx.beginPath();
      ctx.moveTo(gx, gy + 8);
      ctx.lineTo(gx + TILE_SIZE / 2, gy);
      ctx.lineTo(gx + TILE_SIZE, gy + 8);
      ctx.closePath();
      ctx.fill();
    }

    if (frame.furnace) {
      const fx = frame.furnace.x * TILE_SIZE;
      const fy = frame.furnace.y * TILE_SIZE;
      // Corps du fourneau en pierre réfractaire
      ctx.fillStyle = "#1e293b";
      ctx.fillRect(fx + 2, fy + 2, TILE_SIZE - 4, TILE_SIZE - 4);
      // Foyer incandescent (couleur liée à la chaleur heat)
      const glow = frame.furnace.heat > 50 ? "#ea580c" : frame.furnace.heat > 10 ? "#f97316" : "#475569";
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(fx + TILE_SIZE / 2, fy + TILE_SIZE / 2, 7, 0, Math.PI * 2);
      ctx.fill();
    }

    // 3. Draw Altars
    for (const alt of frame.altars) {
      ctx.fillStyle = "#a855f7";
      ctx.beginPath();
      ctx.arc(alt.x * TILE_SIZE + TILE_SIZE / 2, alt.y * TILE_SIZE + TILE_SIZE / 2, 10, 0, Math.PI * 2);
      ctx.fill();
    }

    // 4. Draw Items (Minerais, Lingots, Outils, Céréales)
    for (const it of frame.items) {
      const ix = it.x * TILE_SIZE + TILE_SIZE / 2;
      const iy = it.y * TILE_SIZE + TILE_SIZE / 2;
      if (it.type === "iron_ore") {
        ctx.fillStyle = "#64748b"; // Minerai de fer (gris sombre métallisé)
        ctx.beginPath();
        ctx.arc(ix, iy, 6, 0, Math.PI * 2);
        ctx.fill();
      } else if (it.type === "iron_ingot") {
        ctx.fillStyle = "#e2e8f0"; // Lingot de fer (acier brillant)
        ctx.fillRect(ix - 5, iy - 3, 10, 6);
      } else if (it.type === "metal_tool") {
        ctx.fillStyle = "#06b6d4"; // Outil métallique (cyan forgé)
        ctx.beginPath();
        ctx.arc(ix, iy, 7, 0, Math.PI * 2);
        ctx.fill();
      } else if (it.type === "ripe_wheat" || it.type === "bread") {
        ctx.fillStyle = "#fbbf24"; // Blé ou pain doré
        ctx.beginPath();
        ctx.arc(ix, iy, 5, 0, Math.PI * 2);
        ctx.fill();
      } else {
        ctx.fillStyle = "orange";
        ctx.beginPath();
        ctx.arc(ix, iy, 5, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // 5. Draw Worms
    for (const w of frame.worms) {
      ctx.fillStyle = "#f472b6";
      ctx.beginPath();
      ctx.arc(w.x * TILE_SIZE + TILE_SIZE / 2, w.y * TILE_SIZE + TILE_SIZE / 2, 4, 0, Math.PI * 2);
      ctx.fill();
    }

    // 6. Draw Preys
    for (const p of frame.preys) {
      ctx.fillStyle = p.stunned > 0 ? "grey" : (p.type === "Lapin" ? "white" : p.type === "Cerf" ? "#854d0e" : p.type === "Sanglier" ? "#7f1d1d" : "#1e3a8a");
      ctx.beginPath();
      ctx.arc(p.x * TILE_SIZE + TILE_SIZE / 2, p.y * TILE_SIZE + TILE_SIZE / 2, 12, 0, Math.PI * 2);
      ctx.fill();
    }

    // 7. Draw Agents
    // 7. Draw Agents avec rôles tribaux & ondes de Gigatokens LU
    for (const a of frame.agents) {
      const ax = a.x * TILE_SIZE + TILE_SIZE / 2;
      const ay = a.y * TILE_SIZE + TILE_SIZE / 2;

      // Ondes de Gigatoken LU (si l'agent émet de la communication continue)
      if (a.is_speaking) {
        ctx.strokeStyle = "rgba(192, 132, 252, 0.7)"; // Halo violet améthyste LU
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(ax, ay, 22, 0, Math.PI * 2);
        ctx.stroke();

        ctx.strokeStyle = "rgba(192, 132, 252, 0.35)";
        ctx.beginPath();
        ctx.arc(ax, ay, 28, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Couleur de corps selon la spécialisation tribale
      if (a.role === "SCOUT") ctx.fillStyle = "#f59e0b"; // Or / éclaireur
      else if (a.role === "HUNTER") ctx.fillStyle = "#e11d48"; // Rouge meute / chasseur
      else if (a.role === "CRAFTER") ctx.fillStyle = "#06b6d4"; // Cyan forge / artisan
      else ctx.fillStyle = "#38bdf8"; // Bleu tribal par défaut

      ctx.beginPath();
      ctx.arc(ax, ay, 14, 0, Math.PI * 2);
      ctx.fill();

      // HP bar
      ctx.fillStyle = "#ef4444";
      ctx.fillRect(a.x * TILE_SIZE, a.y * TILE_SIZE - 6, TILE_SIZE, 4);
      ctx.fillStyle = "#22c55e";
      ctx.fillRect(a.x * TILE_SIZE, a.y * TILE_SIZE - 6, TILE_SIZE * Math.max(0, Math.min(1, a.hp / 100)), 4);
    }

    // Anneau de mise en valeur de l'agent sélectionné
    if (selectedAgent) {
      ctx.strokeStyle = "#facc15";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(selectedAgent.x * TILE_SIZE + TILE_SIZE / 2, selectedAgent.y * TILE_SIZE + TILE_SIZE / 2, 20, 0, Math.PI * 2);
      ctx.stroke();
    }

    // 8. Draw Nuage de Pollution Industrielle (voile atmosphérique)
    if (frame.pollution_level && frame.pollution_level > 0) {
      const alpha = Math.min(0.5, (frame.pollution_level / 200) * 0.45);
      ctx.fillStyle = `rgba(51, 65, 85, ${alpha})`;
      ctx.fillRect(0, 0, frame.size * TILE_SIZE, frame.size * TILE_SIZE);
    }

    ctx.restore();
  }, [frame, scale, offset, selectedAgent]);

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    setScale((s) => Math.max(0.2, Math.min(5, s - e.deltaY * 0.001)));
  };

  const handlePointerDown = (e: React.PointerEvent) => {
    isDragging.current = true;
    dragDistance.current = 0;
    lastMouse.current = { x: e.clientX, y: e.clientY };
    (e.target as Element).setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDragging.current) return;
    const dx = e.clientX - lastMouse.current.x;
    const dy = e.clientY - lastMouse.current.y;
    dragDistance.current += Math.hypot(dx, dy);
    setOffset((prev) => ({ x: prev.x + dx, y: prev.y + dy }));
    lastMouse.current = { x: e.clientX, y: e.clientY };
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    isDragging.current = false;
    (e.target as Element).releasePointerCapture(e.pointerId);

    // Si clic sans glissement significatif (< 6px), inspecter la tuile cliquée
    if (dragDistance.current < 6 && canvasRef.current && frame) {
      const canvas = canvasRef.current;
      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      // Inversion de la matrice de vue du canvas
      const worldPxX = (mouseX - canvas.width / 2 - offset.x) / scale + (frame.size * TILE_SIZE) / 2;
      const worldPxY = (mouseY - canvas.height / 2 - offset.y) / scale + (frame.size * TILE_SIZE) / 2;
      const tileX = Math.floor(worldPxX / TILE_SIZE);
      const tileY = Math.floor(worldPxY / TILE_SIZE);

      const clickedAgent = frame.agents.find((a) => Math.hypot(a.x - tileX, a.y - tileY) <= 1.2);
      setSelectedAgent(clickedAgent || null);
    }
  };

  return (
    <div className="flatland-frame">
      <div className="flatland-overlay">
        <div style={{ fontWeight: 700, marginBottom: 6 }}>Flatland Metrics</div>
        <div>Ticks: {frame?.ticks || 0}</div>
        <div>Agents: {frame?.agents.length || 0}</div>
        {frame?.season && (
          <div style={{ color: "var(--color-accent)", fontWeight: 600 }}>
            Saison: {frame.season.toUpperCase()}
          </div>
        )}
        {frame?.granary_reserves !== undefined && frame?.granary_reserves !== null && (
          <div style={{ color: "#f97316", fontWeight: 600 }}>
            Grenier: {frame.granary_reserves.toFixed(1)} réserves
          </div>
        )}
        {frame?.pollution_level !== undefined && frame?.pollution_level !== null && frame.pollution_level > 0 && (
          <div style={{ color: "#94a3b8", fontWeight: 600 }}>
            Pollution: {frame.pollution_level.toFixed(1)} ppm
          </div>
        )}
        {frame?.furnace && (
          <div style={{ color: "#ea580c", fontWeight: 600 }}>
            Fourneau: {frame.furnace.heat.toFixed(0)}°C (carburant: {frame.furnace.fuel.toFixed(0)})
          </div>
        )}
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

        {selectedAgent && (
          <div
            style={{
              marginTop: 10,
              padding: 8,
              background: "rgba(250, 204, 21, 0.1)",
              border: "1px solid #facc15",
              borderRadius: 6,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong style={{ color: "#facc15" }}>Agent ({selectedAgent.x}, {selectedAgent.y})</strong>
              <button
                onClick={() => setSelectedAgent(null)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#aaa",
                  cursor: "pointer",
                  fontSize: "0.8rem",
                }}
              >
                &times;
              </button>
            </div>
            <div>Énergie: {selectedAgent.energy.toFixed(1)} / 100</div>
            <div>HP: {selectedAgent.hp.toFixed(1)} / 100</div>
            <div>
              Rôle:{" "}
              <span
                style={{
                  fontWeight: 600,
                  color:
                    selectedAgent.role === "SCOUT"
                      ? "#f59e0b"
                      : selectedAgent.role === "HUNTER"
                      ? "#e11d48"
                      : selectedAgent.role === "CRAFTER"
                      ? "#06b6d4"
                      : "#38bdf8",
                }}
              >
                {selectedAgent.role || "STANDARD"}
              </span>
            </div>
            {selectedAgent.is_speaking && (
              <div style={{ color: "#c084fc", fontWeight: 600 }}>📡 Émet un Gigatoken LU</div>
            )}
            <div>Inventaire: {selectedAgent.inventory_size} items</div>
            <div>Action courante: #{selectedAgent.last_action}</div>
          </div>
        )}
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
