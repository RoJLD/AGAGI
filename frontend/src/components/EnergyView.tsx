import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { Decomposition } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { buildPhaseBreakdown, buildBioBreakdown } from "../lib/energy";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";
import { Field } from "./ui/Field";
import { Panel } from "./ui/Panel";
import { EnergyChart } from "./EnergyChart";

/** Vue énergie : budget par phase + sous-décomposition biologie d'un run de décompo (EDR 099/100). */
export function EnergyView() {
  const { data: decomps = [], isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.runs.decompositions,
    queryFn: () => apiFetch<Decomposition[]>("/api/runs/decompositions"),
    staleTime: 30_000,
  });

  const [selId, setSelId] = useState<string>("");
  const current = decomps.find((d) => d.run_id === selId) ?? decomps[0];

  if (isLoading) return <Loading label="Chargement des décompositions…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!decomps.length || !current) {
    return (
      <Empty message="Aucune décomposition énergétique. Lance python tools/lewis_survival_sweep.py (main_decompose) côté backend." />
    );
  }

  const phaseBars = buildPhaseBreakdown(current.phases);
  const bioBars = buildBioBreakdown(current.phases);

  return (
    <div className="energy-view">
      <h2>Budget énergétique (décomposition du drain)</h2>
      <div className="row mb-4">
        <Field label="Run de décomposition">
          <select value={current.run_id} onChange={(e) => setSelId(e.target.value)}>
            {decomps.map((d) => (
              <option key={d.run_id} value={d.run_id}>
                {d.name} — seed {d.seed}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <p className="text-dim">
        net <strong>{current.phases.net.toFixed(2)}</strong>/tick · {current.phases.n_agents} agents · seed{" "}
        {current.seed}
      </p>
      <div className="energy-verdicts mb-4">
        <p>
          <strong>Verdict phases :</strong> {current.verdict || "—"}
        </p>
        <p>
          <strong>Verdict biologie :</strong> {current.bio_verdict || "—"}
        </p>
      </div>
      <Panel>
        <EnergyChart bars={phaseBars} title="Budget par phase" unit="énergie/tick/agent" />
      </Panel>
      <Panel className="mt-4">
        <EnergyChart bars={bioBars} title="Sous-décomposition biologie" unit="énergie/tick/agent" />
      </Panel>
    </div>
  );
}
