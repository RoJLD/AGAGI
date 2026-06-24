import { useEffect, useRef, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer, Legend,
} from "recharts";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch } from "../../api/client";
import { queryKeys } from "../../api/queryKeys";
import { cssVar, vizColors } from "../../theme";
import { Button } from "../ui/Button";
import { Panel } from "../ui/Panel";

/** Tableau de bord live d'un run sandbox en cours (monde 2D, console, télémétrie,
 *  journal du superviseur, interventions god-mode). Extrait de SandboxView pour
 *  être réutilisé par le Parcours (étape Suivre). Les panneaux pollent le backend. */
export function LiveDashboard() {
  return (
    <div className="live-dashboard">
      <div className="grid-3 mt-5">
        <LiveWorld />
        <LiveConsole />
        <LiveTelemetry />
      </div>
      <LiveSupervisor />
      <GodModePanel />
    </div>
  );
}

const LiveWorld = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { data: state } = useQuery({
    queryKey: queryKeys.sandbox.state,
    queryFn: () => apiFetch<any>("/api/sandbox/state"),
    refetchInterval: 500,
    staleTime: 0,
  });

  useEffect(() => {
    if (!state || !(state.size > 0)) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const size = state.size;
    const cellSize = canvas.width / size;
    const c = {
      bgNight: cssVar("--world-bg-night"),
      bgDay: cssVar("--world-bg-day"),
      grid: cssVar("--world-grid"),
      tree: cssVar("--world-tree"),
      fire: cssVar("--world-fire"),
      item: cssVar("--world-item"),
      prey: cssVar("--world-prey"),
      agentHi: cssVar("--world-agent-hi"),
      agentLo: cssVar("--world-agent-lo"),
    };

    ctx.fillStyle = state.is_night ? c.bgNight : c.bgDay;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = c.grid;
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= size; i++) {
      ctx.beginPath(); ctx.moveTo(i * cellSize, 0); ctx.lineTo(i * cellSize, canvas.height); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, i * cellSize); ctx.lineTo(canvas.width, i * cellSize); ctx.stroke();
    }

    ctx.fillStyle = c.tree;
    state.trees?.forEach((t: any) => ctx.fillRect(t.x * cellSize, t.y * cellSize, cellSize, cellSize));

    state.items?.forEach((it: any) => {
      ctx.fillStyle = it.type === "Fire" ? c.fire : c.item;
      ctx.fillRect(it.x * cellSize + 2, it.y * cellSize + 2, cellSize - 4, cellSize - 4);
      if (it.type === "Fire") {
        ctx.fillStyle = "rgba(243, 139, 168, 0.2)";
        ctx.beginPath(); ctx.arc(it.x * cellSize + cellSize / 2, it.y * cellSize + cellSize / 2, cellSize * 2.5, 0, Math.PI * 2); ctx.fill();
      }
    });

    ctx.fillStyle = c.prey;
    state.preys?.forEach((p: any) => {
      ctx.beginPath(); ctx.arc(p.x * cellSize + cellSize / 2, p.y * cellSize + cellSize / 2, cellSize / 2.5, 0, Math.PI * 2); ctx.fill();
    });

    state.agents?.forEach((a: any) => {
      ctx.fillStyle = a.energy > 50 ? c.agentHi : c.agentLo;
      ctx.beginPath(); ctx.arc(a.x * cellSize + cellSize / 2, a.y * cellSize + cellSize / 2, cellSize / 2, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "white";
      ctx.font = "8px Arial";
      ctx.fillText(a.energy?.toFixed(0), a.x * cellSize, a.y * cellSize + cellSize);
    });
  }, [state]);

  return (
    <Panel className="live-world">
      <h4>🌍 Visualisation 2D</h4>
      <canvas
        ref={canvasRef}
        width={400}
        height={400}
        style={{ border: "1px solid var(--color-border)", borderRadius: "var(--radius-sm)", background: "var(--color-bg)", width: "100%", height: "auto" }}
      />
    </Panel>
  );
};

const LiveConsole = () => {
  const consoleRef = useRef<HTMLPreElement>(null);
  const { data } = useQuery({
    queryKey: queryKeys.sandbox.logs,
    queryFn: () => apiFetch<{ logs: string[] }>("/api/sandbox/logs"),
    refetchInterval: 1000,
    staleTime: 0,
  });
  const logs = data?.logs ?? [];

  useEffect(() => {
    if (consoleRef.current) consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
  }, [logs]);

  return (
    <Panel className="live-console">
      <h4>🖥️ Terminal Biosphère (Live)</h4>
      <pre ref={consoleRef} className="console-block">
        {logs.map((log, i) => (
          <div key={i}>{log}</div>
        ))}
      </pre>
    </Panel>
  );
};

const LiveTelemetry = () => {
  const { data } = useQuery({
    queryKey: queryKeys.sandbox.telemetry,
    queryFn: () => apiFetch<{ data: any[] }>("/api/sandbox/telemetry"),
    refetchInterval: 2000,
    staleTime: 0,
  });
  const rows = data?.data ?? [];
  const viz = vizColors();

  return (
    <div className="panel-base live-telemetry" style={{ height: "400px", overflow: "hidden" }}>
      <h4>📊 Télémétrie Cognitive</h4>
      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" stroke={cssVar("--color-border")} />
          <XAxis dataKey="tick" stroke={cssVar("--color-text-dim")} fontSize={10} />
          <YAxis stroke={cssVar("--color-text-dim")} fontSize={10} />
          <RechartsTooltip contentStyle={{ backgroundColor: cssVar("--color-surface"), border: `1px solid ${cssVar("--color-border")}` }} />
          <Legend />
          <Line type="monotone" dataKey="mean_energy" stroke={viz[0]} dot={false} name="Énergie" />
          <Line type="monotone" dataKey="mean_surprise" stroke={viz[1]} dot={false} name="Surprise" />
          <Line type="monotone" dataKey="mean_doubt" stroke={viz[4]} dot={false} name="Doute" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

const LiveSupervisor = () => {
  const { data: article } = useQuery({
    queryKey: queryKeys.sandbox.article,
    queryFn: () => apiFetch<{ title: string; content: string; timestamp: number }>("/api/sandbox/article"),
    refetchInterval: 5000,
    staleTime: 0,
  });

  return (
    <div className="supervisor-block">
      <h4>🤖 Journal du Superviseur (Ollama LLM)</h4>
      {article ? (
        <div>
          <strong>{article.title}</strong>
          <p>{article.content}</p>
        </div>
      ) : (
        <p className="dim">Chargement du journal...</p>
      )}
    </div>
  );
};

const GodModePanel = () => {
  const [action, setAction] = useState("");
  const godAction = useMutation({
    mutationFn: (a: string) =>
      apiFetch("/api/sandbox/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: a }),
      }),
    onSuccess: () => setAction(""),
  });

  return (
    <Panel className="mt-5">
      <h4>⚡ Interventions God-Mode</h4>
      <div className="row">
        <input
          type="text"
          placeholder="Ex: Apparition d'un incendie (Fire)"
          value={action}
          onChange={(e) => setAction(e.target.value)}
          style={{ flex: 1, padding: "var(--space-2)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-sm)", background: "var(--color-surface)", color: "var(--color-text)" }}
        />
        <Button variant="danger" size="sm" onClick={() => action && godAction.mutate(action)} disabled={godAction.isPending}>
          Lancer
        </Button>
      </div>
    </Panel>
  );
};
