import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { STATUS_POLL } from "../lib/polling";
import type { RunConfig, QueueStatus } from "../types";
import { validateRunConfig } from "../lib/validateRunConfig";
import { useRunPresets } from "../hooks/useRunPresets";
import { useToast } from "../contexts/ToastContext";
import { Panel } from "./ui/Panel";
import { Field } from "./ui/Field";
import { Button } from "./ui/Button";
import { Badge } from "./ui/Badge";
import {
  buildQueueItems,
  mergeQueue,
  queueTick,
  applyStartFailure,
  stopQueue,
  queueCounts,
  type QueueState,
} from "../lib/queue";

interface SandboxStatusLite {
  running: boolean;
  available_scripts: string[];
}

const STATUS_VARIANT: Record<QueueStatus, "teal" | "warning" | "success" | "danger"> = {
  pending: "teal",
  running: "warning",
  done: "success",
  error: "danger",
};

export function RunLauncher({ onLaunch }: { onLaunch?: (config: RunConfig) => void } = {}) {
  const { notify } = useToast();
  const { presets, savePreset, deletePreset } = useRunPresets();

  const statusQuery = useQuery({
    queryKey: queryKeys.sandbox.status,
    queryFn: () => apiFetch<SandboxStatusLite>("/api/sandbox/status"),
    ...STATUS_POLL,
  });
  const scripts = statusQuery.data?.available_scripts ?? [];

  const [config, setConfig] = useState<RunConfig>({
    script_name: "",
    world_type: "stoneage",
    base_seed: 0,
    n_seeds: 4,
    mutation_rate: null,
    variable_tested: "",
    tags: [],
  });
  useEffect(() => {
    if (scripts.length && !config.script_name) setConfig((c) => ({ ...c, script_name: scripts[0] }));
  }, [scripts, config.script_name]);

  const [presetLabel, setPresetLabel] = useState("");
  const [q, setQ] = useState<QueueState>({ items: [], running: false, current: null });

  const { errors, warnings } = validateRunConfig(config);
  const set = <K extends keyof RunConfig>(k: K, v: RunConfig[K]) => setConfig((c) => ({ ...c, [k]: v }));

  const enqueue = () => {
    if (errors.length) {
      notify(errors[0], "error");
      return;
    }
    const incoming = buildQueueItems(config);
    setQ((s) => ({ ...s, items: mergeQueue(s.items, incoming) }));
    notify(`${incoming.length} run(s) enfilé(s).`, "info");
  };

  const startRun = async (seed: number) => {
    const payload: Record<string, unknown> = {
      script_name: config.script_name,
      world_type: config.world_type,
      seed,
      enable_supervisor: false,
      run_migration: false,
      run_sociologist: false,
      keep_memory: false,
      resource_limit: 4,
      batch_size: 0,
    };
    if (config.mutation_rate !== null) payload.mutation_rate = config.mutation_rate;
    await apiFetch("/api/sandbox/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  };

  // Pilote séquentiel piloté par le signal de poll (statusQuery.data).
  // queueTick est pur ; on ne commit l'état que s'il change, on exécute l'effet retourné.
  useEffect(() => {
    if (!statusQuery.data) return;
    const { state: next, effect } = queueTick(q, statusQuery.data.running);
    if (next !== q) setQ(next);
    if (effect.type === "start") {
      startRun(effect.seed).catch(() => setQ((s) => applyStartFailure(s, effect.id)));
    } else if (effect.type === "complete") {
      notify("File de runs terminée.", "success");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusQuery.data, q]);

  const counts = queueCounts(q.items);

  return (
    <Panel className="mb-5">
      <h3>🧪 Lanceur de runs reproductibles (multi-seed)</h3>
      <p className="text-dim mb-4">
        Empile R réplicats seedés (graine = base + i) lancés <strong>séquentiellement</strong> via la Sandbox.
        Sauvegarde des configurations en presets. 1 variable testée à la fois (Commandement 15).
      </p>

      <div className="grid-3">
        <Field label="Script principal">
          <select value={config.script_name} onChange={(e) => set("script_name", e.target.value)}>
            {scripts.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Type de monde">
          <select value={config.world_type} onChange={(e) => set("world_type", e.target.value)}>
            <option value="stoneage">Stone Age</option>
            <option value="waterworld">Waterworld</option>
            <option value="3d_world">Monde 3D</option>
          </select>
        </Field>
        <Field label="Variable testée">
          <input
            type="text"
            value={config.variable_tested}
            onChange={(e) => set("variable_tested", e.target.value)}
            placeholder="ex: robust_hof_K"
          />
        </Field>
        <Field label="Graine de base">
          <input type="number" value={config.base_seed} onChange={(e) => set("base_seed", Number(e.target.value))} />
        </Field>
        <Field label="Nombre de seeds (R)">
          <input type="number" min={1} value={config.n_seeds} onChange={(e) => set("n_seeds", Number(e.target.value))} />
        </Field>
        <Field label="Taux mutation (vide = auto)">
          <input
            type="number"
            step="0.01"
            value={config.mutation_rate ?? ""}
            onChange={(e) => set("mutation_rate", e.target.value === "" ? null : Number(e.target.value))}
            placeholder="Auto"
          />
        </Field>
      </div>

      {errors.length > 0 && errors.map((er) => <p key={er} className="text-danger">⛔ {er}</p>)}
      {warnings.map((w) => (
        <p key={w} className="text-dim">⚠ {w}</p>
      ))}

      {/* Presets */}
      <div className="row mt-4">
        <input
          type="text"
          value={presetLabel}
          onChange={(e) => setPresetLabel(e.target.value)}
          placeholder="Nom du preset"
          style={{ padding: "var(--space-2)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-sm)", background: "var(--color-surface)", color: "var(--color-text)" }}
        />
        <Button
          variant="ghost"
          size="sm"
          disabled={!presetLabel.trim()}
          onClick={() => {
            savePreset(presetLabel, config);
            notify(`Preset « ${presetLabel.trim()} » sauvegardé.`, "success");
            setPresetLabel("");
          }}
        >
          Sauver preset
        </Button>
      </div>
      {presets.length > 0 && (
        <div className="row mt-4" style={{ flexWrap: "wrap" }}>
          {presets.map((p) => (
            <span key={p.id} className="row" style={{ gap: "var(--space-1)" }}>
              <Button variant="ghost" size="sm" onClick={() => setConfig(p.config)}>
                {p.label}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => deletePreset(p.id)} aria-label={`Supprimer ${p.label}`}>
                ✕
              </Button>
            </span>
          ))}
        </div>
      )}

      {/* Actions file */}
      <div className="row mt-5">
        <Button variant="ghost" onClick={enqueue} disabled={errors.length > 0}>
          Enfiler {config.n_seeds} seed(s)
        </Button>
        {q.running ? (
          <Button variant="danger" onClick={() => setQ(stopQueue)}>
            Stopper la file
          </Button>
        ) : (
          <Button
            variant="primary"
            disabled={!q.items.some((it) => it.status === "pending")}
            onClick={() => {
              setQ((s) => ({ ...s, running: true }));
              onLaunch?.(config);
            }}
          >
            Lancer la file
          </Button>
        )}
        {q.items.length > 0 && (
          <Button variant="ghost" size="sm" onClick={() => { if (!q.running) setQ((s) => ({ ...s, items: [] })); }} disabled={q.running}>
            Vider
          </Button>
        )}
      </div>

      {/* File */}
      {q.items.length > 0 && (
        <div className="mt-4">
          <p className="text-dim">
            File : {counts.pending ?? 0} en attente · {counts.running ?? 0} en cours · {counts.done ?? 0} fini ·{" "}
            {counts.error ?? 0} erreur
          </p>
          <div className="row" style={{ flexWrap: "wrap" }}>
            {q.items.map((it) => (
              <Badge key={it.id} variant={STATUS_VARIANT[it.status]}>
                seed {it.seed} · {it.status}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </Panel>
  );
}
