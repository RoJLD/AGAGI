import React, { useEffect, useState, useRef } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Legend } from "recharts";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8001";

interface SandboxConfig {
  script_name: string;
  enable_supervisor: boolean;
  run_migration: boolean;
  run_sociologist: boolean;
  world_type?: string;
  run_linguist?: boolean;
  run_metacognition?: boolean;
  run_dream_analyzer?: boolean;
  mutation_rate?: number;
  seed?: number;
}

interface SandboxStatus {
  running: boolean;
  script: string | null;
  pid: number | null;
  config: SandboxConfig | null;
  available_scripts: string[];
}

export function SandboxView() {
  const [status, setStatus] = useState<SandboxStatus | null>(null);
  
  const [selectedScript, setSelectedScript] = useState<string>("");
  const [enableSupervisor, setEnableSupervisor] = useState<boolean>(false);
  const [runMigration, setRunMigration] = useState<boolean>(false);
  const [runSociologist, setRunSociologist] = useState<boolean>(false);
  
  // Nouveaux champs restaurés
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
  
  const [loading, setLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<string | null>(null);

  const fetchStatus = () => {
    fetch(`${API_BASE}/api/sandbox/status`)
      .then((res) => res.json())
      .then((data: SandboxStatus) => {
        setStatus(data);
        if (data.available_scripts.length > 0 && !selectedScript) {
          setSelectedScript(data.available_scripts[0]);
        }
      })
      .catch((err) => console.error("Erreur status:", err));
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleStart = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const payload: any = {
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

      const res = await fetch(`${API_BASE}/api/sandbox/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      setMessage(data.message || (data.status === "success" ? "Démarré" : "Erreur"));
      fetchStatus();
    } catch (err: any) {
      setMessage(`Erreur: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_BASE}/api/sandbox/stop`, {
        method: "POST",
      });
      const data = await res.json();
      setMessage(data.message || (data.status === "success" ? "Arrêté" : "Erreur"));
      fetchStatus();
    } catch (err: any) {
      setMessage(`Erreur: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (!status) return <p>Chargement du statut Sandbox...</p>;

  return (
    <div className="sandbox-view">
      <h2>Contrôle Sandbox / Simulation</h2>
      <div className="academy-box" style={{ marginBottom: "20px" }}>
        <p><strong>Statut :</strong> {status.running ? <span style={{ color: "green" }}>EN COURS</span> : <span style={{ color: "red" }}>ARRÊTÉ</span>}</p>
        {status.running && status.config && (
          <p>
            Script : {status.config.script_name} (PID: {status.pid})<br />
            Superviseur : {status.config.enable_supervisor ? "Oui" : "Non"} | Monde : {status.config.world_type || "stoneage"}
          </p>
        )}
      </div>

      <div className="academy-box">
        <h3>Lancer une simulation (Configuration)</h3>
        
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "20px" }}>
            
            {/* Colonne de Gauche : Configurations Générales */}
            <div>
                <h4>Paramètres Généraux</h4>
                <div style={{ marginBottom: "1rem" }}>
                  <label style={{ display: "block", marginBottom: "5px" }}>Script principal</label>
                  <select 
                    value={selectedScript} 
                    onChange={(e) => setSelectedScript(e.target.value)} 
                    disabled={status.running} 
                    style={{ width: "100%", padding: "5px" }}
                  >
                    {status.available_scripts.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                
                <div style={{ marginBottom: "1rem" }}>
                  <label style={{ display: "block", marginBottom: "5px" }}>Type de Monde</label>
                  <select 
                    value={worldType} 
                    onChange={(e) => setWorldType(e.target.value)} 
                    disabled={status.running}
                    style={{ width: "100%", padding: "5px" }}
                  >
                    <option value="stoneage">Stone Age (Défaut)</option>
                    <option value="waterworld">Waterworld</option>
                    <option value="3d_world">Monde 3D</option>
                  </select>
                </div>
                
                <div style={{ marginBottom: "1rem", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                    <div>
                        <label style={{ display: "block", fontSize: "0.9em" }}>Taux Mutation (ex: 0.1)</label>
                        <input type="number" step="0.01" value={mutationRate} onChange={e => setMutationRate(e.target.value === "" ? "" : Number(e.target.value))} disabled={status.running} style={{ width: "100%", padding: "4px" }} placeholder="Auto" />
                    </div>
                    <div>
                        <label style={{ display: "block", fontSize: "0.9em" }}>Graine (Seed)</label>
                        <input type="number" value={seed} onChange={e => setSeed(e.target.value === "" ? "" : Number(e.target.value))} disabled={status.running} style={{ width: "100%", padding: "4px" }} placeholder="Auto" />
                    </div>
                </div>

                <div style={{ marginBottom: "1rem" }}>
                    <label style={{ display: "block", fontSize: "0.9em" }}>ID Agent à Importer (Optionnel)</label>
                    <input type="text" value={importAgentId} onChange={e => setImportAgentId(e.target.value)} disabled={status.running} style={{ width: "100%", padding: "4px" }} placeholder="Ex: e6f2b4a..." />
                </div>
                
                <div style={{ marginBottom: "1rem" }}>
                  <label><input type="checkbox" checked={keepMemory} onChange={(e) => setKeepMemory(e.target.checked)} disabled={status.running} /> Conserver la Mémoire KuzuDB</label>
                </div>
                
                <div style={{ marginBottom: "1rem" }}>
                  <label><input type="checkbox" checked={runMigration} onChange={(e) => setRunMigration(e.target.checked)} disabled={status.running} /> Forcer la migration</label>
                </div>
            </div>

            {/* Colonne de Droite : Modules & Analyses */}
            <div>
                <h4>Modules & Analyses Post-Mortem</h4>
                
                <div style={{ marginBottom: "0.8rem" }}>
                  <label><input type="checkbox" checked={enableSupervisor} onChange={(e) => setEnableSupervisor(e.target.checked)} disabled={status.running} /> Activer le Superviseur IA (LangGraph)</label>
                </div>
                <div style={{ marginBottom: "0.8rem" }}>
                  <label><input type="checkbox" checked={runSociologist} onChange={(e) => setRunSociologist(e.target.checked)} disabled={status.running} /> Lancer le Sociologue en fin de run</label>
                </div>
                <div style={{ marginBottom: "0.8rem" }}>
                  <label><input type="checkbox" checked={runLinguist} onChange={(e) => setRunLinguist(e.target.checked)} disabled={status.running} /> Lancer le Linguiste (Analyse Vocale)</label>
                </div>
                <div style={{ marginBottom: "0.8rem" }}>
                  <label><input type="checkbox" checked={runMetacognition} onChange={(e) => setRunMetacognition(e.target.checked)} disabled={status.running} /> Analyser la Métacognition</label>
                </div>
                <div style={{ marginBottom: "0.8rem" }}>
                  <label><input type="checkbox" checked={runDreamAnalyzer} onChange={(e) => setRunDreamAnalyzer(e.target.checked)} disabled={status.running} /> Analyser les Rêves (Test-Time Compute)</label>
                </div>
                
                <hr style={{ margin: "15px 0", borderTop: "1px solid var(--color-border)" }} />
                
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                    <div>
                        <label style={{ display: "block", fontSize: "0.9em" }}>Limite Ressources (Go)</label>
                        <input type="number" value={resourceLimit} onChange={e => setResourceLimit(Number(e.target.value))} disabled={status.running} style={{ width: "100%", padding: "4px" }} />
                    </div>
                    <div>
                        <label style={{ display: "block", fontSize: "0.9em" }}>Taille Batch (0=Auto)</label>
                        <input type="number" value={batchSize} onChange={e => setBatchSize(Number(e.target.value))} disabled={status.running} style={{ width: "100%", padding: "4px" }} />
                    </div>
                </div>
            </div>
            
        </div>

        <div style={{ marginTop: "20px", textAlign: "right" }}>
          {status.running ? (
            <button onClick={handleStop} disabled={loading} style={{ background: "red", color: "white", padding: "12px 24px", borderRadius: "5px", border: "none", cursor: "pointer", fontWeight: "bold" }}>Arrêter la Sandbox</button>
          ) : (
            <button onClick={handleStart} disabled={loading || !selectedScript} style={{ background: "green", color: "white", padding: "12px 24px", borderRadius: "5px", border: "none", cursor: "pointer", fontWeight: "bold" }}>Démarrer la Sandbox</button>
          )}
        </div>
        {message && <p style={{ marginTop: "1rem", fontWeight: "bold", textAlign: "right", color: "var(--color-accent)" }}>{message}</p>}
      </div>

      {status.running && (
        <div className="live-dashboard">
          <div className="live-row" style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "20px", marginTop: "20px" }}>
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

// --- Live Components ---

const LiveWorld = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [worldSize, setWorldSize] = useState(30);

  useEffect(() => {
    const fetchState = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/sandbox/state`);
        const state = await res.json();
        
        if (state.size > 0) {
          setWorldSize(state.size);
          const canvas = canvasRef.current;
          if (!canvas) return;
          const ctx = canvas.getContext("2d");
          if (!ctx) return;
          
          const size = state.size;
          const cellSize = canvas.width / size;
          
          ctx.fillStyle = state.is_night ? "#11111b" : "#1e1e2e";
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          
          ctx.strokeStyle = "#313244";
          ctx.lineWidth = 0.5;
          for(let i=0; i<=size; i++) {
            ctx.beginPath(); ctx.moveTo(i*cellSize, 0); ctx.lineTo(i*cellSize, canvas.height); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(0, i*cellSize); ctx.lineTo(canvas.width, i*cellSize); ctx.stroke();
          }

          ctx.fillStyle = "#a6e3a1";
          state.trees?.forEach((t: any) => {
             ctx.fillRect(t.x * cellSize, t.y * cellSize, cellSize, cellSize);
          });

          state.items?.forEach((it: any) => {
             ctx.fillStyle = it.type === "Fire" ? "#f38ba8" : "#f9e2af";
             ctx.fillRect(it.x * cellSize + 2, it.y * cellSize + 2, cellSize - 4, cellSize - 4);
             if (it.type === "Fire") {
                ctx.fillStyle = "rgba(243, 139, 168, 0.2)";
                ctx.beginPath(); ctx.arc(it.x * cellSize + cellSize/2, it.y * cellSize + cellSize/2, cellSize * 2.5, 0, Math.PI*2); ctx.fill();
             }
          });

          ctx.fillStyle = "#cba6f7";
          state.preys?.forEach((p: any) => {
             ctx.beginPath(); ctx.arc(p.x * cellSize + cellSize/2, p.y * cellSize + cellSize/2, cellSize/2.5, 0, Math.PI*2); ctx.fill();
          });

          state.agents?.forEach((a: any) => {
             ctx.fillStyle = a.energy > 50 ? "#89b4fa" : "#89dceb";
             ctx.beginPath(); ctx.arc(a.x * cellSize + cellSize/2, a.y * cellSize + cellSize/2, cellSize/2, 0, Math.PI*2); ctx.fill();
             ctx.fillStyle = "white";
             ctx.font = "8px Arial";
             ctx.fillText(a.energy?.toFixed(0), a.x * cellSize, a.y * cellSize + cellSize);
          });
        }
      } catch (e) { }
    };
    
    const interval = setInterval(fetchState, 500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="live-world academy-box" style={{ padding: "10px" }}>
      <h4>🌍 Visualisation 2D</h4>
      <canvas ref={canvasRef} width={400} height={400} style={{ border: "1px solid var(--color-border)", borderRadius: "4px", background: "var(--color-bg)", width: "100%", height: "auto" }} />
    </div>
  );
};

const LiveConsole = () => {
  const [logs, setLogs] = useState<string[]>([]);
  const consoleRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/sandbox/logs`);
        const data = await res.json();
        setLogs(data.logs || []);
      } catch (e) { }
    };
    const interval = setInterval(fetchLogs, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="live-console academy-box" style={{ padding: "10px" }}>
      <h4>🖥️ Terminal Biosphère (Live)</h4>
      <pre ref={consoleRef} style={{ background: "#11111b", color: "#a6adc8", padding: "10px", height: "400px", overflowY: "auto", fontSize: "0.8em", borderRadius: "4px", margin: 0 }}>
        {logs.map((log, i) => <div key={i}>{log}</div>)}
      </pre>
    </div>
  );
};

const LiveTelemetry = () => {
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    const fetchTelemetry = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/sandbox/telemetry`);
        const json = await res.json();
        setData(json.data || []);
      } catch (e) { }
    };
    const interval = setInterval(fetchTelemetry, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="live-telemetry academy-box" style={{ padding: "10px", height: "400px", overflow: "hidden" }}>
      <h4>📊 Télémétrie Cognitive</h4>
      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#313244" />
          <XAxis dataKey="tick" stroke="#a6adc8" fontSize={10} />
          <YAxis stroke="#a6adc8" fontSize={10} />
          <RechartsTooltip contentStyle={{ backgroundColor: "#1e1e2e", border: "1px solid #313244" }} />
          <Legend />
          <Line type="monotone" dataKey="mean_energy" stroke="#a6e3a1" dot={false} name="Énergie" />
          <Line type="monotone" dataKey="mean_surprise" stroke="#f38ba8" dot={false} name="Surprise" />
          <Line type="monotone" dataKey="mean_doubt" stroke="#89b4fa" dot={false} name="Doute" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

const LiveSupervisor = () => {
  const [article, setArticle] = useState<{title: string, content: string, timestamp: number} | null>(null);

  useEffect(() => {
    const fetchArticle = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/sandbox/article`);
        const json = await res.json();
        setArticle(json);
      } catch (e) { }
    };
    const interval = setInterval(fetchArticle, 5000);
    fetchArticle();
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="live-supervisor" style={{ background: "#11111b", padding: "15px", borderRadius: "6px", border: "1px solid #cba6f7", marginTop: "15px" }}>
      <h4 style={{ margin: 0, color: "#cba6f7", marginBottom: "10px" }}>🤖 Journal du Superviseur (Ollama LLM)</h4>
      {article ? (
        <div>
          <strong style={{ color: "#89b4fa" }}>{article.title}</strong>
          <p style={{ color: "#cdd6f4", fontSize: "0.9em", whiteSpace: "pre-wrap", marginTop: "5px" }}>{article.content}</p>
        </div>
      ) : (
        <p style={{ color: "#a6adc8", fontSize: "0.9em" }}>Chargement du journal...</p>
      )}
    </div>
  );
};

const GodModePanel = () => {
  const [action, setAction] = useState("");
  
  const handleGodAction = async () => {
    if (!action) return;
    try {
      await fetch(`${API_BASE}/api/sandbox/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action })
      });
      setAction("");
    } catch (e) { console.error(e); }
  };

  return (
    <div className="academy-box" style={{ marginTop: "20px" }}>
      <h4>⚡ Interventions God-Mode</h4>
      <div style={{ display: "flex", gap: "10px" }}>
        <input 
          type="text" 
          placeholder="Ex: Apparition d'un incendie (Fire)" 
          value={action} 
          onChange={(e) => setAction(e.target.value)}
          style={{ flex: 1, padding: "8px" }}
        />
        <button onClick={handleGodAction} style={{ padding: "8px 16px", background: "#f38ba8", color: "black", fontWeight: "bold", border: "none", borderRadius: "4px", cursor: "pointer" }}>
          Lancer
        </button>
      </div>
    </div>
  );
};
