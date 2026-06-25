import type { EdrLinks } from "../types";

export interface EdrIndexRow {
  edr: number;
  title: string;
  mapped: boolean;
  runIds: string[];
  runCount: number;
}

/** Croise les docs EDR avec les EDR curés (mappés) et les liens runs. Tri EDR décroissant. */
export function buildEdrIndex(
  docs: { edr: number; title: string }[],
  curatedEdrs: number[],
  edrLinks: EdrLinks,
): EdrIndexRow[] {
  const curated = new Set(curatedEdrs);
  return docs
    .map((d) => {
      const runIds = edrLinks[String(d.edr)] ?? [];
      return { edr: d.edr, title: d.title, mapped: curated.has(d.edr), runIds, runCount: runIds.length };
    })
    .sort((a, b) => b.edr - a.edr);
}

export interface IndexSummary {
  total: number;
  mapped: number;
  withRuns: number;
}

/** Couverture globale : total / mappés / avec ≥1 run. */
export function summarizeIndex(rows: EdrIndexRow[]): IndexSummary {
  return {
    total: rows.length,
    mapped: rows.filter((r) => r.mapped).length,
    withRuns: rows.filter((r) => r.runCount > 0).length,
  };
}

export interface IndexFilter {
  query: string;
  mappedOnly: boolean;
  withRunsOnly: boolean;
}

/** Filtre : recherche `<edr> <titre>` (insensible casse) + mappés-only + avec-runs-only. */
export function filterIndex(rows: EdrIndexRow[], f: IndexFilter): EdrIndexRow[] {
  const q = f.query.trim().toLowerCase();
  return rows.filter((r) => {
    if (f.mappedOnly && !r.mapped) return false;
    if (f.withRunsOnly && r.runCount === 0) return false;
    if (q && !`${r.edr} ${r.title}`.toLowerCase().includes(q)) return false;
    return true;
  });
}
