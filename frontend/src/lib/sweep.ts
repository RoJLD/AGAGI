export interface OverlaySeries {
  id: string;        // ex. `${run_id}::${metric}` — dataKey unique
  label: string;     // ex. `${name} · ${metric}` — légende
  knob: string;
  x: number[];
  y: number[];
  yStd?: number[];
}

export interface OverlayPoint {
  x: number;
  [seriesKey: string]: number | [number, number] | undefined;
}

/** Min-max [0,1] par série. Si max == min -> tableau de 0 (série plate). Pur. */
export function normalizeSeries(y: number[]): number[] {
  if (y.length === 0) return [];
  const min = Math.min(...y);
  const max = Math.max(...y);
  if (max === min) return y.map(() => 0);
  return y.map((v) => (v - min) / (max - min));
}

/** Aligne les séries sur l'union triée de leurs X (niveaux pouvant différer entre runs ->
 *  valeur absente si la série n'a pas ce X). Bande `${id}__band` = [y-std, y+std] émise
 *  UNIQUEMENT si une seule série, mode brut, et yStd de même longueur que y. Pur. */
export function buildOverlayData(series: OverlaySeries[], normalize: boolean): OverlayPoint[] {
  const yEff = series.map((s) => (normalize ? normalizeSeries(s.y) : s.y));
  const xSet = new Set<number>();
  series.forEach((s) => s.x.forEach((xv) => xSet.add(xv)));
  const xs = [...xSet].sort((a, b) => a - b);

  const withBand =
    series.length === 1 &&
    !normalize &&
    Array.isArray(series[0].yStd) &&
    series[0].yStd!.length === series[0].y.length;

  return xs.map((xv) => {
    const point: OverlayPoint = { x: xv };
    series.forEach((s, si) => {
      const i = s.x.indexOf(xv);
      if (i !== -1) point[s.id] = yEff[si][i];
    });
    if (withBand) {
      const s = series[0];
      const i = s.x.indexOf(xv);
      if (i !== -1) point[`${s.id}__band`] = [s.y[i] - s.yStd![i], s.y[i] + s.yStd![i]];
    }
    return point;
  });
}
