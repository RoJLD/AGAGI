import type { ForageLevel } from "../types";

export interface ForageBar {
  name: string;
  value: number;
  pct: number;
}

/** 3 étages d'acquisition d'un niveau : atteinte (p_reach), capture-si-atteint (p_cap),
 *  capture globale (= p_reach × p_cap). `value` dans [0,1], `pct` = value × 100. Ordre fixe (cascade). */
export function buildFunnelStages(level: ForageLevel): ForageBar[] {
  const global = level.p_reach * level.p_cap;
  return [
    { name: "atteinte (p_reach)", value: level.p_reach, pct: level.p_reach * 100 },
    { name: "capture si atteint (p_cap)", value: level.p_cap, pct: level.p_cap * 100 },
    { name: "capture globale", value: global, pct: global * 100 },
  ];
}
