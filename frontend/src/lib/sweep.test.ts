import { test, expect } from "vitest";
import { buildSweepData } from "./sweep";

test("sans yStd : points x/y sans bande", () => {
  expect(buildSweepData([1, 2], [10, 20])).toEqual([
    { x: 1, y: 10 },
    { x: 2, y: 20 },
  ]);
});

test("avec yStd : bande [y-std, y+std]", () => {
  expect(buildSweepData([1, 2], [10, 20], [1, 2])).toEqual([
    { x: 1, y: 10, band: [9, 11] },
    { x: 2, y: 20, band: [18, 22] },
  ]);
});

test("yStd de longueur incohérente est ignoré (pas de bande)", () => {
  expect(buildSweepData([1, 2], [10, 20], [1])).toEqual([
    { x: 1, y: 10 },
    { x: 2, y: 20 },
  ]);
});
