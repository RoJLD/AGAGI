import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { STATUS_POLL } from "../lib/polling";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Button } from "./ui/Button";
import { Field } from "./ui/Field";
import { Panel } from "./ui/Panel";
import { Badge } from "./ui/Badge";
import { LiveDashboard } from "./parcours/LiveDashboard";

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

interface RsiResult {
  status: string;
  proposal?: {
    name: string;
    kind: string;
    code: string;
    rationale: string;
    params?: Record<string, unknown>;
  };
  validation?: {
    ok: boolean;
    reason: string;
  };
  message?: string;
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
  const [rsiResult, setRsiResult] = useState<RsiResult | null>(null);

  const statusQuery = useQuery({
    queryKey: queryKeys.sandbox.status,
    queryFn: () => apiFetch<SandboxStatus>("/api/sandbox/status"),
    ...STATUS_POLL,
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

  const [useLlmRsi, setUseLlmRsi] = useState<boolean>(false);

  const rsiMutation = useMutation({
    mutationFn: () =>
      apiFetch<RsiResult>("/api/sandbox/iterate_rsi", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ use_llm: useLlmRsi }),
      }),
    onSuccess: (data) => {
      setRsiResult(data);
      if (data.status === "success" && data.proposal) {
        setMessage(`Mutation validée : ${data.proposal.name} (${data.proposal.kind})`);
      } else {
        setMessage(data.message || "Erreur lors du pas RSI");
      }
    },
    onError: (err) => setMessage(`Erreur RSI: ${err instanceof Error ? err.message : String(err)}`),
  });

  const busy = startMutation.isPending || stopMutation.isPending || rsiMutation.isPending;

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
                <option value="stoneage">Monde 1 : Âge de Pierre (Défaut)</option>
                <option value="agricultural">Monde 2 : Âge Agricole (Greniers, Saisons)</option>
                <option value="industrial">Monde 3 : Âge Industriel (Fourneaux, Métal)</option>
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

      <Panel className="mt-5">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h3 style={{ margin: 0 }}>🧬 Méta-Programmation &amp; Auto-Amélioration Récursive (RSI #8)</h3>
            <p style={{ margin: "4px 0 0 0", color: "var(--color-text-muted)", fontSize: "0.9rem" }}>
              Cycle DÉTECTER &rarr; PROPOSER &rarr; VALIDER (Sandbox AST isolée) &rarr; MESURER &rarr; ENREGISTRER (KuzuDB).
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <label style={{ fontSize: "0.85rem", display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={useLlmRsi}
                onChange={(e) => setUseLlmRsi(e.target.checked)}
                disabled={rsiMutation.isPending}
              />
              Armer avec LLM Ollama
            </label>
            <Button
              variant="ghost"
              onClick={() => rsiMutation.mutate()}
              disabled={rsiMutation.isPending}
            >
              {rsiMutation.isPending ? "Évaluation Sandbox en cours…" : "Exécuter un pas RSI (#8)"}
            </Button>
          </div>
        </div>

        {rsiResult && rsiResult.proposal && (
          <div className="mt-4" style={{ background: "rgba(255, 255, 255, 0.03)", padding: "16px", borderRadius: "8px", border: "1px solid var(--color-border)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
              <strong>Proposition :</strong>
              <code style={{ fontSize: "1rem", color: "var(--color-accent)" }}>{rsiResult.proposal.name}</code>
              <Badge variant="purple">{rsiResult.proposal.kind}</Badge>
              {rsiResult.validation?.ok ? (
                <Badge variant="success">SANDBOX VALIDÉE (AST PASSED)</Badge>
              ) : (
                <Badge variant="danger">REJETÉ ({rsiResult.validation?.reason})</Badge>
              )}
            </div>
            <p style={{ margin: "4px 0", fontSize: "0.85rem", color: "var(--color-text-muted)" }}>
              <strong>Rationale :</strong> {rsiResult.proposal.rationale}
            </p>
            {rsiResult.proposal.code && (
              <pre
                style={{
                  background: "#111",
                  padding: "12px",
                  borderRadius: "6px",
                  fontSize: "0.85rem",
                  overflowX: "auto",
                  marginTop: "8px",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                }}
              >
                <code>{rsiResult.proposal.code}</code>
              </pre>
            )}
          </div>
        )}
      </Panel>

      {running && <LiveDashboard />}
    </div>
  );
}
