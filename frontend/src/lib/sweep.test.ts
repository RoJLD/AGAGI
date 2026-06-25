import { test, expect } from "vitest";
import { normalizeSeries, buildOverlayData, type OverlaySeries } from "./sweep";

// Tests pour les helpers de superposition
const S = (id: string, x: number[], y: number[], yStd?: number[]): OverlaySeries => ({
  id, label: id, knob: "k", x, y, yStd,
});

test("normalizeSeries : min-max [0,1]", () => {
  expect(normalizeSeries([1, 2, 3, 4, 5])).toEqual([0, 0.25, 0.5, 0.75, 1]);
});

test("normalizeSeries : série plate -> zéros", () => {
  expect(normalizeSeries([2, 2])).toEqual([0, 0]);
});

test("buildOverlayData : 2 séries même X -> une clé par série", () => {
  expect(buildOverlayData([S("a", [1, 2], [10, 20]), S("b", [1, 2], [30, 40])], false)).toEqual([
    { x: 1, a: 10, b: 30 },
    { x: 2, a: 20, b: 40 },
  ]);
});

test("buildOverlayData : X disjoints -> union triée, trous absents", () => {
  expect(buildOverlayData([S("a", [1, 3], [10, 30]), S("b", [2, 3], [20, 33])], false)).toEqual([
    { x: 1, a: 10 },
    { x: 2, b: 20 },
    { x: 3, a: 30, b: 33 },
  ]);
});

test("buildOverlayData : normalize=true -> valeurs normalisées, pas de bande", () => {
  expect(buildOverlayData([S("a", [1, 2, 3], [0, 5, 10], [1, 1, 1])], true)).toEqual([
    { x: 1, a: 0 },
    { x: 2, a: 0.5 },
    { x: 3, a: 1 },
  ]);
});

test("buildOverlayData : 1 série + yStd + brut -> clé band [y-std, y+std]", () => {
  expect(buildOverlayData([S("a", [1, 2], [10, 20], [1, 2])], false)).toEqual([
    { x: 1, a: 10, a__band: [9, 11] },
    { x: 2, a: 20, a__band: [18, 22] },
  ]);
});

test("buildOverlayData : bande absente si >1 série", () => {
  expect(buildOverlayData([S("a", [1], [10], [1]), S("b", [1], [20], [1])], false)).toEqual([
    { x: 1, a: 10, b: 20 },
  ]);
});
