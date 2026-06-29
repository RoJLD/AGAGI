import { test, expect } from "vitest";
import { buildFunnelStages } from "./forage";
import type { ForageLevel } from "../types";

const L: ForageLevel = {
  metab: 0, p_reach: 0.18, p_cap: 1, income_t: 0.5, drain_t: 0.2,
  mean_captures: 1.2, mean_contacts: 6.5, mean_min_dist: 3.1, n_agents: 40,
};

test("buildFunnelStages : 3 étages dans l'ordre cascade", () => {
  const bars = buildFunnelStages(L);
  expect(bars.map((b) => b.name)).toEqual([
    "atteinte (p_reach)",
    "capture si atteint (p_cap)",
    "capture globale",
  ]);
  expect(bars[0].value).toBeCloseTo(0.18, 10);
  expect(bars[1].value).toBe(1);
});

test("buildFunnelStages : capture globale = p_reach × p_cap ; pct = value × 100", () => {
  const bars = buildFunnelStages(L);
  expect(bars[2].value).toBeCloseTo(0.18, 10);
  expect(bars[0].pct).toBeCloseTo(18, 10);
});
