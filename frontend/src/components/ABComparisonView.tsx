import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import type { ABCompareResult, ABGroup, ConditionSummary } from "../types";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";
import { Field } from "./ui/Field";
import { Badge } from "./ui/Badge";
import { Panel } from "./ui/Panel";

function GroupBar({ g, color, winner, maxV }: { g: ABGroup; color: string; winner: string | null; maxV: number }) {
  const pct = Math.max(0, Math.min(100, (g.mean / maxV) * 100));
  return (
    <div className="comparison-metric-row">
      <div className="comparison-metric-info">
        <span className="comparison-gate-name">
          {g.name} {winner === g.name ? "🏆" : ""}
        </span>
        <span>
          {g.mean.toFixed(3)} ± {g.std.toFixed(3)} (n={g.n})
        </span>
      </div>
      <div className="comparison-bar-track">
        <div className="comparison-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-dim" style={{ fontSize: "var(--font-size-xs)" }}>
        seeds : {g.vals.map((v) => v.toFixed(1)).join(", ")}
      </span>
    </div>
  );
}

function VerdictCard({ r }: { r: ABCompareResult }) {
  const maxV = Math.max(r.a.mean + r.a.std, r.b.mean + r.b.std, 1e-9);
  const variant = r.significant ? "success" : r.underpowered ? "warning" : "danger";
  return (
    <Panel className="mt-4">
      <GroupBar g={r.a} color="var(--viz-1)" winner={r.winner} maxV={maxV} />
      <GroupBar g={r.b} color="var(--viz-2)" winner={r.winner} maxV={maxV} />
      <p className="row" style={{ gap: "var(--space-5)" }}>
        <span>
          t = <strong>{r.t.toFixed(2)}</strong>
        </span>
        <span>
          Cohen d = <strong>{r.d.toFixed(2)}</strong>
        </span>
        <span className="text-dim">
          seuils : t ≥ {r.t_thresh}, d ≥ {r.d_thresh}
        </span>
      </p>
      <p>
        <Badge variant={variant}>{r.verdict_label}</Badge> <span className="text-dim">{r.verdict_detail}</span>
      </p>
      {r.underpowered && (
        <p className="text-dim">⚠ Puissance insuffisante (n &lt; 4) — augmente le nombre de seeds avant de conclure.</p>
      )}
    </Panel>
  );
}

export function ABComparisonView({
  preselectA,
  onBaselineChange,
}: {
  preselectA?: string;
  onBaselineChange?: (name: string) => void;
}) {
  const conditionsQuery = useQuery({
    queryKey: queryKeys.runs.conditions,
    queryFn: () => apiFetch<ConditionSummary[]>("/api/runs/conditions"),
    staleTime: 30_000,
  });
  const conditions = conditionsQuery.data ?? [];

  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const [metric, setMetric] = useState("");
  const appliedPreselect = useRef<string | null>(null);

  useEffect(() => {
    if (!conditions.length) return;
    // Deep-link depuis l'Historique des runs : préselectionne la condition A (une seule fois par valeur).
    if (preselectA && conditions.some((c) => c.name === preselectA) && appliedPreselect.current !== preselectA) {
      appliedPreselect.current = preselectA;
      setA(preselectA);
      setB((prev) => (prev && prev !== preselectA ? prev : conditions.find((c) => c.name !== preselectA)?.name ?? ""));
      return;
    }
    if (conditions.length >= 2 && !a && !b) {
      setA(conditions[0].name);
      setB(conditions[1].name);
    }
  }, [conditions, preselectA, a, b]);

  const condA = conditions.find((c) => c.name === a);
  const condB = conditions.find((c) => c.name === b);
  const sharedMetrics = condA && condB ? condA.metrics.filter((m) => condB.metrics.includes(m)) : [];

  useEffect(() => {
    if (sharedMetrics.length && !sharedMetrics.includes(metric)) {
      setMetric(sharedMetrics[0]);
    }
  }, [sharedMetrics, metric]);

  const canCompare = Boolean(a && b && a !== b && metric);
  const compareQuery = useQuery({
    queryKey: queryKeys.runs.compare(a, b, metric),
    queryFn: () =>
      apiFetch<ABCompareResult>(
        `/api/runs/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}&metric=${encodeURIComponent(metric)}`,
      ),
    enabled: canCompare,
  });

  if (conditionsQuery.isLoading) return <Loading label="Chargement des conditions…" />;
  if (conditionsQuery.error) return <ErrorState error={conditionsQuery.error} onRetry={() => conditionsQuery.refetch()} />;
  if (conditions.length < 2) {
    return (
      <Empty message="Au moins 2 conditions (expériences avec seeds, écrites dans results/) sont nécessaires pour un A/B. Lance des runs via la Sandbox." />
    );
  }

  return (
    <div>
      <p className="edr-intro">
        Compare deux conditions (groupes de seeds) sur une métrique : moyenne ± écart-type, Welch t, taille
        d'effet de Cohen, verdict aux seuils du projet. <strong>Powerer avant de conclure.</strong>
      </p>
      <div className="row">
        <Field label="Condition A">
          <select value={a} onChange={(e) => setA(e.target.value)}>
            {conditions.map((c) => (
              <option key={c.name} value={c.name}>
                {c.name} ({c.n_seeds} seeds)
              </option>
            ))}
          </select>
        </Field>
        <span className="text-dim">vs</span>
        <Field label="Condition B">
          <select
            value={b}
            onChange={(e) => {
              setB(e.target.value);
              onBaselineChange?.(e.target.value);
            }}
          >
            {conditions.map((c) => (
              <option key={c.name} value={c.name}>
                {c.name} ({c.n_seeds} seeds)
              </option>
            ))}
          </select>
        </Field>
        <Field label="Métrique">
          <select value={metric} onChange={(e) => setMetric(e.target.value)} disabled={!sharedMetrics.length}>
            {sharedMetrics.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </Field>
      </div>

      {a === b ? (
        <Empty message="Choisis deux conditions différentes." />
      ) : !sharedMetrics.length ? (
        <Empty message="Aucune métrique commune aux deux conditions." />
      ) : compareQuery.isLoading ? (
        <Loading label="Calcul du verdict…" />
      ) : compareQuery.error ? (
        <ErrorState error={compareQuery.error} onRetry={() => compareQuery.refetch()} />
      ) : compareQuery.data ? (
        <VerdictCard r={compareQuery.data} />
      ) : null}
    </div>
  );
}
