import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import type { ArticleLinks, RunDetail, RunSummary } from "../types";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";
import { Field } from "./ui/Field";
import { Button } from "./ui/Button";
import { Badge } from "./ui/Badge";
import { Panel } from "./ui/Panel";
import { useToast } from "../contexts/ToastContext";
import { useHashRoute } from "../hooks/useHashRoute";
import { TAB_KEYS } from "../tabs";
import { RunNotes } from "./RunNotes";

export function RunsHistoryView({ onCompare }: { onCompare?: (condition: string) => void }) {
  const { query } = useHashRoute(TAB_KEYS, "runs");
  const runsQuery = useQuery({
    queryKey: queryKeys.runs.list,
    queryFn: () => apiFetch<RunSummary[]>("/api/runs"),
    staleTime: 30_000,
  });

  const articleLinksQuery = useQuery({
    queryKey: queryKeys.runs.articleLinks,
    queryFn: () => apiFetch<ArticleLinks>("/api/runs/article-links"),
    staleTime: 30_000,
  });
  const articleLinks = articleLinksQuery.data ?? {};

  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<string | null>(query.run || null);

  const detailQuery = useQuery({
    queryKey: queryKeys.runs.detail(selected ?? ""),
    queryFn: () => apiFetch<RunDetail>(`/api/runs/${encodeURIComponent(selected ?? "")}`),
    enabled: !!selected,
  });

  const queryClient = useQueryClient();
  const { notify } = useToast();
  const [edrInput, setEdrInput] = useState("");
  const linkMutation = useMutation({
    mutationFn: (edr: number[]) =>
      apiFetch(`/api/runs/${encodeURIComponent(selected ?? "")}/links`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ edr }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.runs.detail(selected ?? "") });
      queryClient.invalidateQueries({ queryKey: queryKeys.runs.edrLinks });
      notify("Liens EDR mis à jour.", "success");
    },
  });
  const submitLinks = () => {
    const edr = edrInput
      .split(",")
      .map((s) => parseInt(s.trim(), 10))
      .filter((n) => Number.isInteger(n));
    linkMutation.mutate(edr);
  };

  const runs = runsQuery.data ?? [];
  const filtered = useMemo(
    () => runs.filter((r) => r.name.toLowerCase().includes(filter.toLowerCase())),
    [runs, filter],
  );
  const conditionCount = useMemo(() => new Set(runs.map((r) => r.name)).size, [runs]);

  if (runsQuery.isLoading) return <Loading label="Chargement des runs…" />;
  if (runsQuery.error) return <ErrorState error={runsQuery.error} onRetry={() => runsQuery.refetch()} />;
  if (!runs.length) {
    return <Empty message="Aucun run dans results/. Lance des expériences via le Bac à sable (lanceur multi-seed)." />;
  }

  return (
    <div>
      <h2>Historique des runs</h2>
      <p className="edr-intro">
        {runs.length} runs · {conditionCount} conditions. Provenance (commit), graine et KPIs de chaque
        réplicat écrit dans <code>results/</code> — la traçabilité des expériences.
      </p>

      <div className="row mb-4" style={{ maxWidth: 320 }}>
        <Field label="Filtrer par condition">
          <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="ex: robust_eval" />
        </Field>
      </div>

      <Panel>
        <table className="runs-table">
          <thead>
            <tr>
              <th>Condition</th>
              <th>Seed</th>
              <th>Commit</th>
              <th>Métriques</th>
              <th aria-label="actions" />
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <tr key={r.run_id} className={selected === r.run_id ? "is-selected" : undefined}>
                <td>
                  {r.name}
                  {articleLinks[r.run_id]?.length ? (
                    <>
                      {" "}
                      <Badge variant="purple">{articleLinks[r.run_id].length} article(s)</Badge>
                    </>
                  ) : null}
                </td>
                <td>{r.seed}</td>
                <td>
                  <code>{r.commit ?? "—"}</code>
                </td>
                <td className="text-dim">{r.metrics.join(", ") || "—"}</td>
                <td className="text-right">
                  <Button variant="ghost" size="sm" onClick={() => setSelected(r.run_id)}>
                    Détail
                  </Button>
                  {onCompare && (
                    <Button variant="ghost" size="sm" onClick={() => onCompare(r.name)}>
                      Comparer
                    </Button>
                  )}
                </td>
              </tr>
            ))}
            {!filtered.length && (
              <tr>
                <td colSpan={5} className="text-dim">
                  Aucune condition ne correspond au filtre.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Panel>

      {selected && (
        <Panel className="mt-4">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <h3 style={{ margin: 0 }}>Détail — {selected}</h3>
            <Button variant="ghost" size="sm" onClick={() => setSelected(null)}>
              Fermer
            </Button>
          </div>
          {detailQuery.isLoading ? (
            <Loading />
          ) : detailQuery.error ? (
            <ErrorState error={detailQuery.error} onRetry={() => detailQuery.refetch()} />
          ) : detailQuery.data ? (
            <>
              <p className="text-dim">
                commit <code>{detailQuery.data.commit ?? "—"}</code> · seed {detailQuery.data.seed} · condition{" "}
                {detailQuery.data.name}
              </p>
              <div className="motif-summary">
                {Object.entries(detailQuery.data.data).map(([k, v]) => (
                  <p key={k}>
                    <strong>{k}</strong> : {typeof v === "number" ? v : String(v)}
                  </p>
                ))}
              </div>
              <div className="mt-4">
                <p className="text-dim">
                  EDR liés :{" "}
                  {detailQuery.data.links?.edr.length
                    ? detailQuery.data.links.edr.map((e) => `EDR ${e}`).join(", ")
                    : "aucun"}
                </p>
                <div className="row">
                  <input
                    value={edrInput}
                    onChange={(e) => setEdrInput(e.target.value)}
                    placeholder="ex: 81, 87"
                    style={{ padding: "var(--space-2)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-sm)", background: "var(--color-surface)", color: "var(--color-text)" }}
                  />
                  <Button variant="ghost" size="sm" disabled={linkMutation.isPending} onClick={submitLinks}>
                    Lier EDR
                  </Button>
                </div>
                <p className="text-dim" style={{ fontSize: "var(--font-size-xs)" }}>
                  Remplace la liste d'EDR liés à ce run (numéros séparés par des virgules).
                </p>
              </div>
              <div className="mt-4">
                <p className="text-dim">
                  Articles Sociologue liés :{" "}
                  {detailQuery.data.links?.articles?.length ? (
                    <>
                      {detailQuery.data.links.articles.join(", ")}{" "}
                      <a href="#/laboratoire">→ Laboratoire</a>
                    </>
                  ) : (
                    "aucun"
                  )}
                </p>
                <p className="text-dim" style={{ fontSize: "var(--font-size-xs)" }}>
                  Lien automatique : un article généré par le Sociologue sur cette condition apparaît ici.
                </p>
              </div>
              <RunNotes runId={selected} />
            </>
          ) : null}
        </Panel>
      )}
    </div>
  );
}
