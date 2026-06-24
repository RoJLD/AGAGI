import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ConditionSummary, DistributionSummary } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { buildCohort } from "../lib/cohort";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";
import { Field } from "./ui/Field";
import { Panel } from "./ui/Panel";
import { CohortChart } from "./CohortChart";

/** Vue cohorte : distribution par seed (box+strip) de toutes les conditions
 *  portant la métrique choisie, triées par médiane décroissante. */
export function CohortView() {
  const {
    data: conditions = [],
    isLoading: isLoadingConditions,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.runs.conditions,
    queryFn: () => apiFetch<ConditionSummary[]>("/api/runs/conditions"),
    staleTime: 30_000,
  });

  const metrics = useMemo(
    () => [...new Set(conditions.flatMap((c) => c.metrics))].sort(),
    [conditions],
  );

  // Métrique sélectionnée par l'utilisateur ; "" = "choisir la première disponible".
  const [selectedMetric, setSelectedMetric] = useState<string>("");

  // Métrique effective : celle choisie si toujours valide, sinon la première disponible.
  const metric = metrics.includes(selectedMetric) ? selectedMetric : (metrics[0] ?? "");

  const {
    data: dists = [],
    isLoading: isLoadingDists,
  } = useQuery({
    queryKey: queryKeys.runs.distributions(metric),
    queryFn: () =>
      apiFetch<DistributionSummary[]>(
        `/api/runs/distributions?metric=${encodeURIComponent(metric)}`,
      ),
    enabled: !!metric,
    staleTime: 30_000,
    // Conserver les données précédentes pendant le rechargement (changement de métrique)
    placeholderData: (prev) => prev,
  });

  const rows = useMemo(() => buildCohort(dists), [dists]);

  // Chargement initial : conditions OU première requête distributions (sans données précédentes)
  if (isLoadingConditions || (!!metric && isLoadingDists)) {
    return <Loading label="Chargement des conditions…" />;
  }
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!metrics.length) {
    return (
      <Empty message="Aucune métrique numérique disponible. Lance des expériences (runs) pour peupler les conditions." />
    );
  }

  return (
    <div className="cohort-view">
      <h2>Cohorte — distributions par condition</h2>
      <div className="row mb-4">
        <Field label="Métrique">
          <select value={metric} onChange={(e) => setSelectedMetric(e.target.value)}>
            {metrics.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <p className="text-dim">
        métrique <strong>{metric}</strong> · {rows.length} condition
        {rows.length > 1 ? "s" : ""} · triées par médiane décroissante
      </p>
      {rows.length === 0 ? (
        <Empty message={`Aucune valeur pour la métrique ${metric}.`} />
      ) : (
        <>
          <Panel>
            <CohortChart rows={rows} metric={metric} />
          </Panel>
          <p className="text-dim cohort-legend">
            Box = IQR (q1–q3) · trait épais = médiane · points = seeds · couleur d'accent = outliers
            (hors 1,5×IQR)
          </p>
        </>
      )}
    </div>
  );
}
