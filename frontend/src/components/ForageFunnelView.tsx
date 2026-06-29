import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ForageFunnel } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { buildFunnelStages } from "../lib/forage";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";
import { Field } from "./ui/Field";
import { Panel } from "./ui/Panel";
import { ForageFunnelChart } from "./ForageFunnelChart";

/** Vue forage : entonnoir d'acquisition (atteinte/capture/globale) par niveau de métab (EDR 105). */
export function ForageFunnelView() {
  const { data: funnels = [], isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.runs.forageFunnels,
    queryFn: () => apiFetch<ForageFunnel[]>("/api/runs/forage-funnels"),
    staleTime: 30_000,
  });

  const [selId, setSelId] = useState<string>("");
  const current = funnels.find((f) => f.run_id === selId) ?? funnels[0];

  if (isLoading) return <Loading label="Chargement des entonnoirs…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!funnels.length || !current) {
    return (
      <Empty message="Aucun entonnoir de forage. Lance python tools/lewis_survival_sweep.py (main_forage) côté backend." />
    );
  }

  return (
    <div className="forage-view">
      <h2>Entonnoir de forage (acquisition)</h2>
      <div className="row mb-4">
        <Field label="Run d'entonnoir">
          <select value={current.run_id} onChange={(e) => setSelId(e.target.value)}>
            {funnels.map((f) => (
              <option key={f.run_id} value={f.run_id}>
                {f.name} — seed {f.seed}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <div className="forage-verdict mb-4">
        <p>
          <strong>Verdict :</strong> {current.verdict || "—"}
        </p>
      </div>
      {current.levels.map((lv) => (
        <Panel key={lv.metab} className="mt-4">
          <ForageFunnelChart bars={buildFunnelStages(lv)} title={`métab ${lv.metab}`} />
          <p className="text-dim">
            revenu <strong>{lv.income_t.toFixed(3)}</strong>/tick · drain <strong>{lv.drain_t.toFixed(3)}</strong>/tick ·
            contacts {lv.mean_contacts.toFixed(2)} · dist. min {lv.mean_min_dist.toFixed(2)} · {lv.n_agents} agents
          </p>
        </Panel>
      ))}
    </div>
  );
}
