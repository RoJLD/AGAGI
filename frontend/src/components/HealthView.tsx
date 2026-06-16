import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Badge } from "./ui/Badge";
import { Panel } from "./ui/Panel";
import { Stat } from "./ui/Stat";

interface Section {
  lines: string[];
  warn: string[];
  fail: string[];
}
interface ParityReport {
  narration: Section;
  dev_parity: Section;
  edr_coverage: { docs_total?: number; curated?: number; max_doc?: number | null; max_finding?: number | null };
  ok: boolean;
  warn_count: number;
  error?: string;
}

function SectionCard({ title, section }: { title: string; section: Section }) {
  const badge = section.fail.length ? (
    <Badge variant="danger">{section.fail.length} FAIL</Badge>
  ) : section.warn.length ? (
    <Badge variant="warning">{section.warn.length} WARN</Badge>
  ) : (
    <Badge variant="success">OK</Badge>
  );
  return (
    <Panel className="mb-4">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>{title}</h3>
        {badge}
      </div>
      {section.lines.map((l, i) => (
        <p key={i} className="text-dim" style={{ margin: "var(--space-1) 0" }}>
          {l}
        </p>
      ))}
      {section.fail.map((m, i) => (
        <p key={`f${i}`} className="text-danger">
          ⛔ {m}
        </p>
      ))}
      {section.warn.map((m, i) => (
        <p key={`w${i}`} className="text-dim">
          ⚠ {m}
        </p>
      ))}
    </Panel>
  );
}

export function HealthView() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.health.parity,
    queryFn: () => apiFetch<ParityReport>("/api/health/parity"),
    staleTime: 30_000,
  });

  if (isLoading) return <Loading label="Analyse de parité…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  const cov = data.edr_coverage ?? {};
  return (
    <div>
      <h2>Santé &amp; parité</h2>
      <p className="edr-intro">
        Rapport de la gate de parité (<code>tools/parity_check.py</code>) : drift de narration EDR,
        endpoints backend non consommés, couverture des découvertes. « Détecter → montrer ».
      </p>
      <div className="row mb-5">
        {data.ok ? (
          <Badge variant="success">Invariants durs OK</Badge>
        ) : (
          <Badge variant="danger">Invariant dur violé</Badge>
        )}
        <Badge variant={data.warn_count ? "warning" : "success"}>{data.warn_count} avertissement(s)</Badge>
      </div>
      {data.error ? <ErrorState error={new Error(data.error)} /> : null}
      <div className="live-stats">
        <Stat label="EDR documentés" value={cov.docs_total ?? "—"} />
        <Stat label="EDR curés (cartes)" value={cov.curated ?? "—"} />
        <Stat label="Dernier EDR doc" value={cov.max_doc ?? "—"} />
        <Stat label="Dernier EDR curé" value={cov.max_finding ?? "—"} />
      </div>
      <SectionCard title="Narration (EDR → findings → fil conducteur)" section={data.narration} />
      <SectionCard title="Parité dev (endpoint backend ↔ consommateur frontend)" section={data.dev_parity} />
    </div>
  );
}
