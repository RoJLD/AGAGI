import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";
import { Badge } from "./ui/Badge";
import type { EdrLinks } from "../types";

type Serie = { name: string; values?: number[]; value?: number; err?: number; color: string };
type Finding = {
  edr: number;
  title: string;
  subtitle: string;
  type: "multiline" | "bar" | "bar_err";
  x?: number[];
  xlabel?: string;
  series: Serie[];
  insight: string;
  stub?: boolean;
};
type Payload = { title: string; findings: Finding[] };
type EdrDoc = { edr: number; title: string; file: string };

const W = 640;
const H = 240;
const PAD = 36;

function LineChart({ f }: { f: Finding }) {
  const xs = f.x ?? [];
  const allVals = f.series.flatMap((s) => s.values ?? []);
  const maxV = Math.max(...allVals, 1);
  const minV = Math.min(...allVals, 0);
  const sx = (i: number) => PAD + (i / Math.max(xs.length - 1, 1)) * (W - 2 * PAD);
  const sy = (v: number) => H - PAD - ((v - minV) / (maxV - minV || 1)) * (H - 2 * PAD);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart-svg" role="img" aria-label={f.title}>
      <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="#cbd5e1" />
      <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="#cbd5e1" />
      {xs.map((xv, i) => (
        <text key={i} x={sx(i)} y={H - PAD + 16} fontSize={11} fill="#64748b" textAnchor="middle">{xv}</text>
      ))}
      <text x={W / 2} y={H - 4} fontSize={11} fill="#94a3b8" textAnchor="middle">{f.xlabel}</text>
      {f.series.map((s) => (
        <g key={s.name}>
          <path d={(s.values ?? []).map((v, i) => `${i === 0 ? "M" : "L"} ${sx(i)} ${sy(v)}`).join(" ")}
                fill="none" stroke={s.color} strokeWidth={3} />
          {(s.values ?? []).map((v, i) => <circle key={i} cx={sx(i)} cy={sy(v)} r={3.5} fill={s.color} />)}
        </g>
      ))}
    </svg>
  );
}

function BarChart({ f }: { f: Finding }) {
  const vals = f.series.map((s) => (s.value ?? 0) + (s.err ?? 0));
  const maxV = Math.max(...vals, 1);
  const n = f.series.length;
  const bw = (W - 2 * PAD) / (n * 1.6);
  const bx = (i: number) => PAD + (i + 0.3) * (bw * 1.6);
  const by = (v: number) => H - PAD - (v / maxV) * (H - 2 * PAD);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart-svg" role="img" aria-label={f.title}>
      <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="#cbd5e1" />
      {f.series.map((s, i) => {
        const v = s.value ?? 0;
        return (
          <g key={s.name}>
            <rect x={bx(i)} y={by(v)} width={bw} height={H - PAD - by(v)} fill={s.color} rx={3} />
            {s.err !== undefined && (
              <line x1={bx(i) + bw / 2} y1={by(v + s.err)} x2={bx(i) + bw / 2} y2={by(Math.max(0, v - s.err))}
                    stroke="#1e293b" strokeWidth={2} />
            )}
            <text x={bx(i) + bw / 2} y={by(v) - 6} fontSize={12} fill="#1e293b" textAnchor="middle" fontWeight={600}>
              {v.toFixed(v < 10 ? 2 : 1)}
            </text>
            <text x={bx(i) + bw / 2} y={H - PAD + 16} fontSize={10.5} fill="#64748b" textAnchor="middle">{s.name}</text>
          </g>
        );
      })}
    </svg>
  );
}

export function EDRDashboard() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.edr,
    queryFn: () => apiFetch<Payload>("/api/edr"),
    staleTime: Infinity,
  });
  const docsQuery = useQuery({
    queryKey: ["edr", "docs"] as const,
    queryFn: () => apiFetch<EdrDoc[]>("/api/edr/docs"),
    staleTime: Infinity,
  });
  const linksQuery = useQuery({
    queryKey: queryKeys.runs.edrLinks,
    queryFn: () => apiFetch<EdrLinks>("/api/runs/edr-links"),
    staleTime: 30_000,
  });

  if (isLoading) return <Loading label="Chargement des découvertes EDR…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data || !data.findings?.length) return <Empty message="Aucun finding EDR." />;

  const curated = new Set(data.findings.filter((f) => !f.stub).map((f) => f.edr));
  const uncurated = (docsQuery.data ?? []).filter((d) => !curated.has(d.edr));
  const links = linksQuery.data ?? {};

  return (
    <div className="edr-dashboard">
      <h2>{data.title}</h2>
      <p className="edr-intro">
        Les vraies expériences du journal de bord — mesurées, powered, honnêtes. Chaque carte = une
        décision (EDR) qui a déplacé la compréhension du projet.
      </p>
      <div className="edr-grid">
        {data.findings.filter((f) => !f.stub).map((f) => (
          <article key={f.edr} className="edr-card">
            <header className="edr-card-head">
              <Badge variant="teal">EDR {f.edr}</Badge>
              {links[String(f.edr)]?.length ? (
                <Badge variant="purple">{links[String(f.edr)].length} run(s) liés</Badge>
              ) : null}
              <h3>{f.title}</h3>
            </header>
            <p className="edr-sub">{f.subtitle}</p>
            {f.type === "multiline" ? <LineChart f={f} /> : <BarChart f={f} />}
            {f.type === "multiline" && (
              <div className="edr-legend">
                {f.series.map((s) => (
                  <span key={s.name}><i style={{ background: s.color }} /> {s.name}</span>
                ))}
              </div>
            )}
            <p className="edr-insight">{f.insight}</p>
          </article>
        ))}
      </div>

      {uncurated.length > 0 && (
        <section className="mt-5">
          <h3>EDR documentés non encore mis en carte ({uncurated.length})</h3>
          <p className="text-dim">
            Couverture automatique : tout EDR de <code>docs/EDR/</code> apparaît ici dès son ajout ; la
            mise en carte (graphique curé dans <code>edr_findings.json</code>) l'enrichit ensuite.
          </p>
          <div className="row" style={{ flexWrap: "wrap" }}>
            {uncurated.map((d) => (
              <span key={d.edr} className="row" style={{ gap: "var(--space-2)" }}>
                <Badge variant="warning">EDR {d.edr}</Badge>
                <span className="text-dim">{d.title}</span>
              </span>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
