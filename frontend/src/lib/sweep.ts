export interface SweepPoint {
  x: number;
  y: number;
  band?: [number, number];
}

/** Construit les points d'un sweep pour recharts : {x, y} + bande [y-std, y+std]
 *  si un écart-type de même longueur est fourni. Pur (aucun effet de bord). */
export function buildSweepData(x: number[], y: number[], yStd?: number[]): SweepPoint[] {
  const withBand = Array.isArray(yStd) && yStd.length === x.length;
  return x.map((xv, i) => {
    const point: SweepPoint = { x: xv, y: y[i] };
    if (withBand) point.band = [y[i] - yStd![i], y[i] + yStd![i]];
    return point;
  });
}
