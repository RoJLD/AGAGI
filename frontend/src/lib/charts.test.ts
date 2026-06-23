import { test, expect } from "vitest";
import { createLinePath, createStabilitySeries, formatPercentage } from "./charts";

test("formatPercentage formate en pourcentage à 1 décimale", () => {
  expect(formatPercentage(0.5)).toBe("50.0%");
  expect(formatPercentage(1)).toBe("100.0%");
});

test("createLinePath: vide si aucune valeur, sinon path SVG non vide", () => {
  expect(createLinePath([], 100, 100)).toBe("");
  expect(createLinePath([0, 0.5, 1], 700, 260)).toMatch(/^M /);
});

test("createStabilitySeries: bornée dans [0,1], 1 pour série triviale", () => {
  expect(createStabilitySeries([0.5])).toEqual([1]);
  const s = createStabilitySeries([0, 1, 0, 1]);
  expect(s.every((v) => v >= 0 && v <= 1)).toBe(true);
});
