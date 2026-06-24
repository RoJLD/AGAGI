import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Article } from "../types";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";
import { Button } from "./ui/Button";
import { Field } from "./ui/Field";
import { Panel } from "./ui/Panel";

interface GateOption {
  gate: string;
}

export function LaboratoryView({
  initialBaseline = "",
  initialIntervention = "",
}: { initialBaseline?: string; initialIntervention?: string } = {}) {
  const queryClient = useQueryClient();
  const [baseline, setBaseline] = useState(initialBaseline);
  const [intervention, setIntervention] = useState(initialIntervention);
  const [validationError, setValidationError] = useState("");

  const articlesQuery = useQuery({
    queryKey: queryKeys.sociologist.articles,
    queryFn: () => apiFetch<Article[]>("/api/sociologist/articles"),
    staleTime: 60_000,
  });

  const experimentsQuery = useQuery({
    queryKey: queryKeys.experiments.list,
    queryFn: () => apiFetch<GateOption[]>("/api/experiments"),
    staleTime: 30_000,
  });
  const experiments = experimentsQuery.data ?? [];

  // Valeurs par défaut une fois les expériences chargées.
  useEffect(() => {
    if (experiments.length >= 2 && !baseline && !intervention) {
      setBaseline(experiments[0].gate);
      setIntervention(experiments[1].gate);
    }
  }, [experiments, baseline, intervention]);

  const analyze = useMutation({
    mutationFn: (body: { baseline: string; intervention: string }) =>
      apiFetch<{ status: string; message?: string }>("/api/sociologist/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        timeoutMs: 120_000, // le LLM peut être lent
      }),
    onSuccess: (result) => {
      if (result.status === "success") {
        queryClient.invalidateQueries({ queryKey: queryKeys.sociologist.articles });
      }
    },
  });

  const handleAnalyze = () => {
    if (!baseline || !intervention) {
      setValidationError("Veuillez sélectionner une Baseline et une Intervention.");
      return;
    }
    if (baseline === intervention) {
      setValidationError("La Baseline et l'Intervention doivent être différentes.");
      return;
    }
    setValidationError("");
    analyze.mutate({ baseline, intervention });
  };

  const analyzeMessage = analyze.isError
    ? "Erreur réseau ou timeout du LLM."
    : analyze.data && analyze.data.status !== "success"
      ? analyze.data.message || "Erreur lors de l'analyse."
      : "";

  return (
    <div className="laboratory-view">
      <h2>Laboratoire & Publications (IA Sociologue)</h2>
      <p>
        Cette page consigne les découvertes scientifiques extraites automatiquement de KuzuDB par
        l'Agent Sociologue après chaque comparaison d'évolution.
      </p>

      <Panel className="mb-5">
        <h3>Lancer une nouvelle étude</h3>
        <p className="mb-4 text-dim">Sélectionnez deux expériences à comparer par le LLM Sociologue :</p>

        <div className="row">
          <Field label="Baseline">
            <select value={baseline} onChange={(e) => setBaseline(e.target.value)}>
              <option value="">Sélectionner...</option>
              {experiments.map((exp) => (
                <option key={`base-${exp.gate}`} value={exp.gate}>
                  {exp.gate}
                </option>
              ))}
            </select>
          </Field>

          <span className="text-dim">VS</span>

          <Field label="Intervention">
            <select value={intervention} onChange={(e) => setIntervention(e.target.value)}>
              <option value="">Sélectionner...</option>
              {experiments.map((exp) => (
                <option key={`int-${exp.gate}`} value={exp.gate}>
                  {exp.gate}
                </option>
              ))}
            </select>
          </Field>

          <Button onClick={handleAnalyze} disabled={analyze.isPending}>
            {analyze.isPending ? "Analyse en cours (LLM)..." : "Générer l'Article"}
          </Button>
        </div>

        {(validationError || analyzeMessage) && (
          <p className="text-danger">{validationError || analyzeMessage}</p>
        )}
      </Panel>

      {articlesQuery.isLoading ? (
        <Loading label="Chargement des publications…" />
      ) : articlesQuery.error ? (
        <ErrorState error={articlesQuery.error} onRetry={() => articlesQuery.refetch()} />
      ) : (articlesQuery.data?.length ?? 0) > 0 ? (
        <div className="articles-list">
          {articlesQuery.data!.map((article) => {
            const dateStr = new Date(article.timestamp).toLocaleString();
            return (
              <Panel as="article" key={article.id} className="article-card mt-4">
                <h3>{article.title}</h3>
                <p className="article-meta">
                  <small className="text-dim">
                    Publié le {dateStr} | ID: {article.id}
                  </small>
                </p>
                <div style={{ whiteSpace: "pre-wrap", marginTop: "var(--space-4)", lineHeight: 1.5 }}>
                  {article.content}
                </div>
              </Panel>
            );
          })}
        </div>
      ) : (
        <Empty message="Aucun article publié pour le moment." />
      )}
    </div>
  );
}
