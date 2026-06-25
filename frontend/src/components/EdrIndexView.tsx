import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { EdrDoc, EdrLinks } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { useHashRoute } from "../hooks/useHashRoute";
import { TAB_KEYS } from "../tabs";
import { buildEdrIndex, summarizeIndex, filterIndex } from "../lib/edrIndex";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";
import { Field } from "./ui/Field";
import { Panel } from "./ui/Panel";
import { Badge } from "./ui/Badge";
import { Button } from "./ui/Button";

/** Forme minimale du payload /api/edr (on n'a besoin que de edr + stub pour la couverture). */
interface CuratedPayload {
  findings: { edr: number; stub?: boolean }[];
}

/** Fil conducteur EDR : index recherchable des 106 EDR (titre = verdict, couverture, runs liés). */
export function EdrIndexView() {
  const { navigate } = useHashRoute(TAB_KEYS, "synthese");

  const curatedQuery = useQuery({
    queryKey: queryKeys.edr,
    queryFn: () => apiFetch<CuratedPayload>("/api/edr"),
    staleTime: 30_000,
  });
  const docsQuery = useQuery({
    queryKey: queryKeys.edrDocs,
    queryFn: () => apiFetch<EdrDoc[]>("/api/edr/docs"),
    staleTime: 30_000,
  });
  const linksQuery = useQuery({
    queryKey: queryKeys.runs.edrLinks,
    queryFn: () => apiFetch<EdrLinks>("/api/runs/edr-links"),
    staleTime: 30_000,
  });

  const [query, setQuery] = useState("");
  const [mappedOnly, setMappedOnly] = useState(false);
  const [withRunsOnly, setWithRunsOnly] = useState(false);

  const docs = docsQuery.data ?? [];
  const rows = useMemo(
    () =>
      buildEdrIndex(
        docs,
        (curatedQuery.data?.findings ?? []).filter((f) => !f.stub).map((f) => f.edr),
        linksQuery.data ?? {},
      ),
    [docs, curatedQuery.data, linksQuery.data],
  );
  const summary = useMemo(() => summarizeIndex(rows), [rows]);
  const filtered = useMemo(
    () => filterIndex(rows, { query, mappedOnly, withRunsOnly }),
    [rows, query, mappedOnly, withRunsOnly],
  );

  if (docsQuery.isLoading || curatedQuery.isLoading || linksQuery.isLoading) {
    return <Loading label="Chargement du fil EDR…" />;
  }
  const error = docsQuery.error ?? curatedQuery.error ?? linksQuery.error;
  if (error) {
    return (
      <ErrorState
        error={error}
        onRetry={() => {
          docsQuery.refetch();
          curatedQuery.refetch();
          linksQuery.refetch();
        }}
      />
    );
  }
  if (!rows.length) return <Empty message="Aucun EDR documenté." />;

  return (
    <div className="edr-index-view">
      <h2>Fil conducteur EDR</h2>
      <p className="text-dim">
        {summary.total} EDR · {summary.mapped} mappés · {summary.withRuns} avec runs liés. Le titre porte le
        verdict ; clique un run pour ouvrir son détail.
      </p>
      <div className="row mb-4">
        <Field label="Rechercher">
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="ex: monoculture, 101" />
        </Field>
        <label className="checkbox-inline">
          <input type="checkbox" checked={mappedOnly} onChange={(e) => setMappedOnly(e.target.checked)} /> mappés
        </label>
        <label className="checkbox-inline">
          <input type="checkbox" checked={withRunsOnly} onChange={(e) => setWithRunsOnly(e.target.checked)} /> avec runs
        </label>
      </div>
      <Panel>
        <table className="runs-table">
          <thead>
            <tr>
              <th>EDR</th>
              <th>Titre</th>
              <th>Mappé</th>
              <th>Runs liés</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <tr key={r.edr}>
                <td>
                  <Badge variant="teal">EDR {r.edr}</Badge>
                </td>
                <td>{r.title}</td>
                <td>{r.mapped ? <Badge variant="success">mappé</Badge> : <span className="text-dim">—</span>}</td>
                <td>
                  {r.runIds.length ? (
                    r.runIds.map((id) => (
                      <Button key={id} variant="ghost" size="sm" onClick={() => navigate("runs", { run: id })}>
                        → {id}
                      </Button>
                    ))
                  ) : (
                    <span className="text-dim">—</span>
                  )}
                </td>
              </tr>
            ))}
            {!filtered.length && (
              <tr>
                <td colSpan={4} className="text-dim">
                  Aucun EDR ne correspond aux filtres.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Panel>
    </div>
  );
}
