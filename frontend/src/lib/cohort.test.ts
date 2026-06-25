import { test, expect } from "vitest";
import { quantile, computeBoxStats, buildCohort } from "./cohort";

test("quantile : interpolation linéaire type-7", () => {
  const s = [1, 2, 3, 4];
  expect(quantile(s, 0.25)).toBeCloseTo(1.75, 10);
  expect(quantile(s, 0.5)).toBeCloseTo(2.5, 10);
  expect(quantile(s, 0.75)).toBeCloseTo(3.25, 10);
});

test("computeBoxStats : quartiles, IQR, médiane", () => {
  const s = computeBoxStats([1, 2, 3, 4]);
  expect(s.q1).toBeCloseTo(1.75, 10);
  expect(s.median).toBeCloseTo(2.5, 10);
  expect(s.q3).toBeCloseTo(3.25, 10);
  expect(s.iqr).toBeCloseTo(1.5, 10);
  expect(s.n).toBe(4);
  expect(s.outliers).toEqual([]);
});

test("computeBoxStats : détecte un outlier hors 1,5×IQR", () => {
  const s = computeBoxStats([1, 2, 3, 4, 100]);
  // q1=2, q3=4, iqr=2, hiFence=7 -> 100 est outlier, moustache haute = 4
  expect(s.q1).toBeCloseTo(2, 10);
  expect(s.q3).toBeCloseTo(4, 10);
  expect(s.upperWhisker).toBe(4);
  expect(s.outliers).toEqual([100]);
});

test("computeBoxStats : cas dégénéré n=1", () => {
  const s = computeBoxStats([5]);
  expect(s.q1).toBe(5);
  expect(s.median).toBe(5);
  expect(s.q3).toBe(5);
  expect(s.iqr).toBe(0);
  expect(s.lowerWhisker).toBe(5);
  expect(s.upperWhisker).toBe(5);
  expect(s.outliers).toEqual([]);
  expect(s.n).toBe(1);
});

test("buildCohort : tri par médiane décroissante, vides exclus", () => {
  const rows = buildCohort([
    { name: "basse", vals: [1, 1, 1], n: 3 },
    { name: "vide", vals: [], n: 0 },
    { name: "haute", vals: [10, 10, 10], n: 3 },
  ]);
  expect(rows.map((r) => r.name)).toEqual(["haute", "basse"]);
});
