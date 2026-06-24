import { useQuery } from "@tanstack/react-query";
import type { AcademyPayload } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";

export function AcademyView() {
  const { data: academy = null, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.academy,
    queryFn: () => apiFetch<AcademyPayload>("/api/academy"),
    staleTime: Infinity,
  });

  return (
    <>
      <h2>Academy</h2>
      {academy ? (
        <div>
          <div className="academy-box">
            <h3>Historique des versions</h3>
            <ol>
              {academy.version_history.map((item) => (
                <li key={item.title}>
                  <strong>{item.title}</strong> — {item.description}
                </li>
              ))}
            </ol>
          </div>
          <div className="academy-box">
            <h3>Timeline</h3>
            <ol>
              {academy.timeline.map((event, index) => (
                <li key={index}>{event}</li>
              ))}
            </ol>
          </div>
          <div className="academy-box">
            <h3>Objectifs pédagogiques</h3>
            <ul>
              {academy.learning_goals.map((goal, index) => (
                <li key={index}>{goal}</li>
              ))}
            </ul>
          </div>
        </div>
      ) : isLoading ? (
        <Loading label="Chargement des contenus Academy…" />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : (
        <Loading label="Chargement des contenus Academy…" />
      )}
    </>
  );
}
