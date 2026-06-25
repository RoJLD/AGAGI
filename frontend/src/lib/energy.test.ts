import { test, expect } from "vitest";
import { buildPhaseBreakdown, buildBioBreakdown } from "./energy";
import type { EnergyPhases } from "../types";

const P: EnergyPhases = {
  brain: 1, action: 2, biologie: 9, mouvement: 0, net: 12, n_agents: 40,
  bio_metab: 13.47, bio_terrain: 0.27, bio_carry: 0.13, bio_autres: 0.13,
};

test("buildPhaseBreakdown : pct du net, tri décroissant", () => {
  const bars = buildPhaseBreakdown(P);
  expect(bars.map((b) => b.name)).toEqual(["biologie", "action", "cerveau", "mouvement"]);
  expect(bars[0]).toEqual({ name: "biologie", value: 9, pct: 75 });
});

test("buildBioBreakdown : pct du drain bio, métab domine", () => {
  const bars = buildBioBreakdown(P);
  expect(bars[0].name).toBe("métab");
  // bioNet = 13.47 + 0.27 + 0.13 + 0.13 = 14
  expect(bars[0].pct).toBeCloseTo((100 * 13.47) / 14, 6);
});

test("net == 0 -> pct 0 (pas de division par zéro)", () => {
  const z: EnergyPhases = { ...P, net: 0 };
  expect(buildPhaseBreakdown(z).every((b) => b.pct === 0)).toBe(true);
});

test("drain bio nul -> pct 0", () => {
  const z: EnergyPhases = { ...P, bio_metab: 0, bio_terrain: 0, bio_carry: 0, bio_autres: 0 };
  expect(buildBioBreakdown(z).every((b) => b.pct === 0)).toBe(true);
});
