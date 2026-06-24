import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { SweepResult } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";
import { Field } from "./ui/Field";
import { Panel } from "./ui/Panel";
import { SweepChart } from "./SweepChart";

export function SweepView() {
  const { data: sweeps = [], isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.sweeps,
    queryFn: () => apiFetch<SweepResult[]>("/api/sweeps"),
    staleTime: 30_000,
  });

  const [selId, setSelId] = useState<string>("");
  const [metric, setMetric] = useState<string>("");

  const current = sweeps.find((s) => s.run_id === selId) ?? sweeps[0];
  const metrics = current ? Object.keys(current.series) : [];

  useEffect(() => {
    if (current && !selId) setSelId(current.run_id);
  }, [current, selId]);
  useEffect(() => {
    if (metrics.length && !metrics.includes(metric)) setMetric(metrics[0]);
  }, [metrics, metric]);

  if (isLoading) return <Loading label="Chargement des sweeps…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!sweeps.length) {
    return (
      <Empty message="Aucun sweep disponible. Lance un balayage de paramètre (ex. lewis_survival_sweep) côté backend." />
    );
  }
  if (!current) return <Empty message="Aucun sweep sélectionné." />;

  return (
    <div className="sweep-view">
      <h2>Paysage de paramètres (sweeps)</h2>
      <div className="row mb-4">
        <Field label="Sweep">
          <select value={current.run_id} onChange={(e) => setSelId(e.target.value)}>
            {sweeps.map((s) => (
              <option key={s.run_id} value={s.run_id}>
                {s.name} — {s.knob}
              </option>
            ))}
          </select>
        </Field>
        {metrics.length > 1 && (
          <Field label="Métrique (Y)">
            <select value={metric} onChange={(e) => setMetric(e.target.value)}>
              {metrics.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </Field>
        )}
      </div>
      <p className="text-dim">
        {current.name} · paramètre <strong>{current.knob}</strong> · métrique <strong>{metric}</strong> ·{" "}
        {current.x.length} points
      </p>
      <Panel>
        <SweepChart
          x={current.x}
          knob={current.knob}
          metric={metric}
          y={current.series[metric] ?? []}
          yStd={current.y_std?.[metric]}
        />
      </Panel>
    </div>
  );
}
