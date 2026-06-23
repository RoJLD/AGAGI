import { useEffect, useRef, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { cssVar, vizColors } from "../theme";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Button } from "./ui/Button";
import { Field } from "./ui/Field";
import { Panel } from "./ui/Panel";
import { Badge } from "./ui/Badge";

interface SandboxConfig {
  script_name: string;
  enable_supervisor: boolean;
  world_type?: string;
}

interface SandboxStatus {
  running: boolean;
  script: string | null;
  pid: number | null;
  config: SandboxConfig | null;
  available_scripts: string[];
}

export function SandboxView() {
  const queryClient = useQueryClient();

  const [selectedScript, setSelectedScript] = useState<string>("");
  const [enableSupervisor, setEnableSupervisor] = useState<boolean>(false);
  const [runMigration, setRunMigration] = useState<boolean>(false);
  const [runSociologist, setRunSociologist] = useState<boolean>(false);
  const [worldType, setWorldType] = useState<string>("stoneage");
  const [importAgentId, setImportAgentId] = useState<string>("");
  const [keepMemory, setKeepMemory] = useState<boolean>(false);
  const [resourceLimit, setResourceLimit] = useState<number>(4);
  const [batchSize, setBatchSize] = useState<number>(0);
  const [mutationRate, setMutationRate] = useState<number | "">("");
  const [seed, setSeed] = useState<number | "">("");
  const [runLinguist, setRunLinguist] = useState<boolean>(false);
  const [runMetacognition, setRunMetacognition] = useState<boolean>(false);
  const [runDreamAnalyzer, setRunDreamAnalyzer] = useState<boolean>(false);
  const [message, setMessage] = useState<string | null>(null);

  const statusQuery = useQuery({
    queryKey: queryKeys.sandbox.status,
    queryFn: () => apiFetch<SandboxStatus>("/api/sandbox/status"),
    refetchInterval: 3000,
    staleTime: 0,
  });
  const status = statusQuery.data;
  const running = status?.running ?? false;

  useEffect(() => {
    if (status && status.available_scripts.length > 0 && !selectedScript) {
      setSelectedScript(status.available_scripts[0]);
    }
  }, [status, selectedScript]);

  const startMutation = useMutation({
    mutationFn: () => {
      const payload: Record<string, unknown> = {
        script_name: selectedScript,
        enable_supervisor: enableSupervisor,
        run_migration: runMigration,
        run_sociologist: runSociologist,
        world_type: worldType,
        keep_memory: keepMemory,
        resource_limit: resourceLimit,
        batch_size: batchSize,
        run_linguist: runLinguist,
        run_metacognition: runMetacognition,
        run_dream_analyzer: runDreamAnalyzer,
      };
      if (importAgentId.trim() !== "") payload.import_agent_id = importAgentId.trim();
      if (mutationRate !== "") payload.mutation_rate = Number(mutationRate);
      if (seed !== "") payload.seed = Number(seed);
      return apiFetch<{ status: string; message?: string }>("/api/sandbox/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    },
    onSuccess: (data) => {
      setMessage(data.message || (data.status === "success" ? "Démarré" : "Erreur"));
      queryClient.invalidateQueries({ queryKey: queryKeys.sandbox.status });
    },
    onError: (err) => setMessage(`Erreur: ${err instanceof Error ? err.message : String(err)}`),
  });

  const stopMutation = useMutation({
    mutationFn: () => apiFetch<{ status: string; message?: string }>("/api/sandbox/stop", { method: "POST" }),
    onSuccess: (data) => {
      setMessage(data.message || (data.status === "success" ? "Arrêté" : "Erreur"));
      queryClient.invalidateQueries({ queryKey: queryKeys.sandbox.status });
    },
    onError: (err) => setMessage(`Erreur: ${err instanceof Error ? err.message : String(err)}`),
  });

  const busy = startMutation.isPending || stopMutation.isPending;

  if (statusQuery.isLoading) return <Loading label="Chargement du statut Sandbox…" />;
  if (statusQuery.error) return <ErrorState error={statusQuery.error} onRetry={() => statusQuery.refetch()} />;
  if (!status) return <Loading label="Chargement du statut Sandbox…" />;

  return (
    <div className="sandbox-view">
      <h2>Contrôle Sandbox / Simulation</h2>

      <Panel className="mb-5">
        <p>
          <strong>Statut :</strong>{" "}
          {running ? <Badge variant="success">EN COURS</Badge> : <Badge variant="danger">ARRÊTÉ</Badge>}
        </p>
        {running && status.config && (
          <p>
            Script : {status.config.script_name} (PID: {status.pid})<br />
            Superviseur : {status.config.enable_supervisor ? "Oui" : "Non"} | Monde :{" "}
            {status.config.world_type || "stoneage"}
          </p>
        )}
      </Panel>

      <Panel>
        <h3>Lancer une simulation (Configuration)</h3>

        <div className="grid-2 mb-5">
          <div>
            <h4>Paramètres Généraux</h4>
            <Field label="Script principal">
              <select value={selectedScript} onChange={(e) => setSelectedScript(e.target.value)} disabled={running}>
                {status.available_scripts.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Type de Monde">
              <select value={worldType} onChange={(e) => setWorldType(e.target.value)} disabled={running}>
                <option value="stoneage">Stone Age (Défaut)</option>
                <option value="waterworld">Waterworld</option>
                <option value="3d_world">Monde 3D</option>
              </select>
            </Field>

            <div className="grid-2">
              <Field label="Taux Mutation (ex: 0.1)">
                <input
                  type="number"
                  step="0.01"
                  value={mutationRate}
                  onChange={(e) => setMutationRate(e.target.value === "" ? "" : Number(e.target.value))}
                  disabled={running}
                  placeholder="Auto"
                />
              </Field>
              <Field label="Graine (Seed)">
                <input
                  type="number"
                  value={seed}
                  onChange={(e) => setSeed(e.target.value === "" ? "" : Number(e.target.value))}
                  disabled={running}
                  placeholder="Auto"
                />
              </Field>
            </div>

            <Field label="ID Agent à Importer (Optionnel)">
              <input
                type="text"
                value={importAgentId}
                onChange={(e) => setImportAgentId(e.target.value)}
                disabled={running}
                placeholder="Ex: e6f2b4a..."
              />
            </Field>

            <div className="mb-4">
              <label>
                <input type="checkbox" checked={keepMemory} onChange={(e) => setKeepMemory(e.target.checked)} disabled={running} />{" "}
                Conserver la Mémoire KuzuDB
              </label>
            </div>
            <div className="mb-4">
              <label>
                <input type="checkbox" checked={runMigration} onChange={(e) => setRunMigration(e.target.checked)} disabled={running} />{" "}
                Forcer la migration
              </label>
            </div>
          </div>

          <div>
            <h4>Modules &amp; Analyses Post-Mortem</h4>
            <div className="mb-4">
              <label>
                <input type="checkbox" checked={enableSupervisor} onChange={(e) => setEnableSupervisor(e.target.checked)} disabled={running} />{" "}
                Activer le Superviseur IA (LangGraph)
              </label>
            </div>
            <div className="mb-4">
              <label>
                <input type="checkbox" checked={runSociologist} onChange={(e) => setRunSociologist(e.target.checked)} disabled={running} />{" "}
                Lancer le Sociologue en fin de run
              </label>
            </div>
            <div className="mb-4">
              <label>
                <input type="checkbox" checked={runLinguist} onChange={(e) => setRunLinguist(e.target.checked)} disabled={running} />{" "}
                Lancer le Linguiste (Analyse Vocale)
              </label>
            </div>
            <div className="mb-4">
              <label>
                <input type="checkbox" checked={runMetacognition} onChange={(e) => setRunMetacognition(e.target.checked)} disabled={running} />{" "}
                Analyser la Métacognition
              </label>
            </div>
            <div className="mb-4">
              <label>
                <input type="checkbox" checked={runDreamAnalyzer} onChange={(e) => setRunDreamAnalyzer(e.target.checked)} disabled={running} />{" "}
                Analyser les Rêves (Test-Time Compute)
              </label>
            </div>

            <hr style={{ margin: "var(--space-4) 0", border: "none", borderTop: "1px solid var(--color-border)" }} />

            <div className="grid-2">
              <Field label="Limite Ressources (Go)">
                <input type="number" value={resourceLimit} onChange={(e) => setResourceLimit(Number(e.target.value))} disabled={running} />
              </Field>
              <Field label="Taille Batch (0=Auto)">
                <input type="number" value={batchSize} onChange={(e) => setBatchSize(Number(e.target.value))} disabled={running} />
              </Field>
            </div>
          </div>
        </div>

        <div className="text-right mt-4">
          {running ? (
            <Button variant="danger" onClick={() => stopMutation.mutate()} disabled={busy}>
              Arrêter la Sandbox
            </Button>
          ) : (
            <Button variant="primary" onClick={() => startMutation.mutate()} disabled={busy || !selectedScript}>
              Démarrer la Sandbox
            </Button>
          )}
        </div>
        {message && <p className="text-right mt-4" style={{ fontWeight: "bold", color: "var(--color-accent)" }}>{message}</p>}
      </Panel>

      {running && (
        <div className="live-dashboard">
          <div className="grid-3 mt-5">
            <LiveWorld />
            <LiveConsole />
            <LiveTelemetry />
          </div>
          <LiveSupervisor />
          <GodModePanel />
        </div>
      )}
    </div>
  );
}

// --- Composants live (montés uniquement quand la sandbox tourne) ---

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
