import type { DistributionSummary } from "../types";

export interface BoxStats {
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
  iqr: number;
  lowerWhisker: number; // plus petite valeur >= q1 - 1,5*iqr
  upperWhisker: number; // plus grande valeur <= q3 + 1,5*iqr
  outliers: number[];   // valeurs hors [lowerWhisker, upperWhisker]
  n: number;
}

export interface CohortRow {
  name: string;
  vals: number[];
  stats: BoxStats;
}

/** Quantile par interpolation linéaire (type-7, comme d3.quantile / numpy par défaut).
 *  `sorted` doit être trié ascendant et non vide ; p dans [0,1]. */
export function quantile(sorted: number[], p: number): number {
  if (sorted.length === 1) return sorted[0];
  const idx = (sorted.length - 1) * p;
  const lo = Math.floor(idx);
  const hi = Math.ceil(idx);
  if (lo === hi) return sorted[lo];
  const frac = idx - lo;
  return sorted[lo] * (1 - frac) + sorted[hi] * frac;
}

/** Stats de box plot (Tukey). Précondition : vals non vide. */
export function computeBoxStats(vals: number[]): BoxStats {
  const sorted = [...vals].sort((a, b) => a - b);
  const n = sorted.length;
  const q1 = quantile(sorted, 0.25);
  const median = quantile(sorted, 0.5);
  const q3 = quantile(sorted, 0.75);
  const iqr = q3 - q1;
  const loFence = q1 - 1.5 * iqr;
  const hiFence = q3 + 1.5 * iqr;
  const inFence = sorted.filter((v) => v >= loFence && v <= hiFence);
  const lowerWhisker = inFence.length ? inFence[0] : sorted[0];
  const upperWhisker = inFence.length ? inFence[inFence.length - 1] : sorted[n - 1];
  const outliers = sorted.filter((v) => v < lowerWhisker || v > upperWhisker);
  return { min: sorted[0], q1, median, q3, max: sorted[n - 1], iqr, lowerWhisker, upperWhisker, outliers, n };
}

/** Lignes de cohorte triées par médiane décroissante ; conditions à vals vide exclues. */
export function buildCohort(dists: DistributionSummary[]): CohortRow[] {
  return dists
    .filter((d) => d.vals.length > 0)
    .map((d) => ({ name: d.name, vals: d.vals, stats: computeBoxStats(d.vals) }))
    .sort((a, b) => b.stats.median - a.stats.median);
}
