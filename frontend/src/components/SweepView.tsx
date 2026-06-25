import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { SweepResult } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";
import { Field } from "./ui/Field";
import { Panel } from "./ui/Panel";
import { SweepOverlayChart } from "./SweepOverlayChart";
import type { OverlaySeries } from "../lib/sweep";

/** Onglet Sweeps v2 : superposer des séries (sweep × métrique) partageant un knob. */
export function SweepView() {
  const { data: sweeps = [], isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.sweeps,
    queryFn: () => apiFetch<SweepResult[]>("/api/sweeps"),
    staleTime: 30_000,
  });

  const knobs = [...new Set(sweeps.map((s) => s.knob))].sort();
  const [selectedKnob, setSelectedKnob] = useState<string>("");
  const knob = knobs.includes(selectedKnob) ? selectedKnob : (knobs[0] ?? "");

  // Séries disponibles pour le knob courant : (sweep × métrique).
  const available: OverlaySeries[] = sweeps
    .filter((s) => s.knob === knob)
    .flatMap((s) =>
      Object.keys(s.series).map((m) => ({
        id: `${s.run_id}::${m}`,
        label: `${s.name} · ${m}`,
        knob: s.knob,
        x: s.x,
        y: s.series[m],
        yStd: s.y_std?.[m],
      })),
    );
  const availableIds = available.map((s) => s.id);

  // null = sélection jamais touchée -> défaut 1ère série (= comportement v1).
  const [selectedIds, setSelectedIds] = useState<string[] | null>(null);
  const shownIds =
    selectedIds === null ? availableIds.slice(0, 1) : selectedIds.filter((id) => availableIds.includes(id));
  const shownSeries = available.filter((s) => shownIds.includes(s.id));

  const [normalize, setNormalize] = useState(false);

  function toggleId(id: string) {
    setSelectedIds((prev) => {
      const base = prev === null ? availableIds.slice(0, 1) : prev.filter((x) => availableIds.includes(x));
      return base.includes(id) ? base.filter((x) => x !== id) : [...base, id];
    });
  }

  if (isLoading) return <Loading label="Chargement des sweeps…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!sweeps.length) {
    return (
      <Empty message="Aucun sweep disponible. Lance un balayage de paramètre (ex. lewis_survival_sweep) côté backend." />
    );
  }

  return (
    <div className="sweep-view">
      <h2>Paysage de paramètres (sweeps)</h2>
      <div className="row mb-4">
        <Field label="Paramètre (knob)">
          <select
            value={knob}
            onChange={(e) => {
              setSelectedKnob(e.target.value);
              setSelectedIds(null);
            }}
          >
            {knobs.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Normalisation">
          <label className="checkbox-inline">
            <input type="checkbox" checked={normalize} onChange={(e) => setNormalize(e.target.checked)} />
            min-max [0,1]
          </label>
        </Field>
      </div>
      <fieldset className="sweep-series mb-4">
        <legend>Séries à superposer</legend>
        {available.map((s) => (
          <label key={s.id} className="checkbox-inline">
            <input
              type="checkbox"
              checked={shownIds.includes(s.id)}
              onChange={() => toggleId(s.id)}
              aria-label={s.label}
            />
            {s.label}
          </label>
        ))}
      </fieldset>
      <p className="text-dim">
        paramètre <strong>{knob}</strong> · {shownSeries.length} série{shownSeries.length > 1 ? "s" : ""} superposée
        {shownSeries.length > 1 ? "s" : ""}
      </p>
      {shownSeries.length === 0 ? (
        <Empty message="Sélectionne au moins une série à superposer." />
      ) : (
        <Panel>
          <SweepOverlayChart series={shownSeries} knob={knob} normalize={normalize} />
        </Panel>
      )}
    </div>
  );
}
