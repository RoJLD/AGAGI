import { useQuery } from "@tanstack/react-query";
import type { NoteFeedItem } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { useHashRoute } from "../hooks/useHashRoute";
import { TAB_KEYS } from "../tabs";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";
import { Panel } from "./ui/Panel";
import { Button } from "./ui/Button";

/** Carnet de labo : flux chronologique read-only de toutes les notes, deep-link vers le run. */
export function CarnetView() {
  const { navigate } = useHashRoute(TAB_KEYS, "carnet");
  const { data: notes = [], isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.notes,
    queryFn: () => apiFetch<NoteFeedItem[]>("/api/notes"),
    staleTime: 30_000,
  });

  if (isLoading) return <Loading label="Chargement du carnet…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!notes.length) {
    return <Empty message="Aucune note. Annote des runs depuis l'Historique des runs." />;
  }

  return (
    <div className="carnet-view">
      <h2>Carnet de labo</h2>
      <p className="text-dim">
        {notes.length} note{notes.length > 1 ? "s" : ""} · journal chronologique inter-runs.
      </p>
      <Panel>
        <ul className="carnet-feed">
          {notes.map((n) => (
            <li key={`${n.run_id}:${n.id}`} className="carnet-feed__item">
              <div className="carnet-feed__meta text-dim">
                {new Date(n.ts).toLocaleString()} · <strong>{n.run_name}</strong>{" "}
                <Button variant="ghost" size="sm" onClick={() => navigate("runs", { run: n.run_id })}>
                  → run
                </Button>
              </div>
              <p className="carnet-feed__text">{n.text}</p>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
