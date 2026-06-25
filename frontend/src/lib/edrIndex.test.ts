import { test, expect } from "vitest";
import { buildEdrIndex, summarizeIndex, filterIndex } from "./edrIndex";

const DOCS = [
  { edr: 101, title: "Metabolisme rescale" },
  { edr: 102, title: "Monoculture porte l'apex" },
  { edr: 99, title: "Decomposition du drain" },
];
const CURATED = [102, 99];
const LINKS = { "102": ["lewis_7", "lewis_8"], "99": [] };

test("buildEdrIndex : mapped, runIds, tri EDR décroissant", () => {
  const rows = buildEdrIndex(DOCS, CURATED, LINKS);
  expect(rows.map((r) => r.edr)).toEqual([102, 101, 99]);
  const r102 = rows.find((r) => r.edr === 102)!;
  expect(r102.mapped).toBe(true);
  expect(r102.runIds).toEqual(["lewis_7", "lewis_8"]);
  expect(r102.runCount).toBe(2);
  const r101 = rows.find((r) => r.edr === 101)!;
  expect(r101.mapped).toBe(false);
  expect(r101.runCount).toBe(0);
});

test("summarizeIndex : total / mapped / withRuns", () => {
  const rows = buildEdrIndex(DOCS, CURATED, LINKS);
  expect(summarizeIndex(rows)).toEqual({ total: 3, mapped: 2, withRuns: 1 });
});

test("filterIndex : recherche titre + numéro", () => {
  const rows = buildEdrIndex(DOCS, CURATED, LINKS);
  expect(filterIndex(rows, { query: "monoculture", mappedOnly: false, withRunsOnly: false }).map((r) => r.edr)).toEqual([102]);
  expect(filterIndex(rows, { query: "101", mappedOnly: false, withRunsOnly: false }).map((r) => r.edr)).toEqual([101]);
});

test("filterIndex : mappedOnly et withRunsOnly", () => {
  const rows = buildEdrIndex(DOCS, CURATED, LINKS);
  expect(filterIndex(rows, { query: "", mappedOnly: true, withRunsOnly: false }).map((r) => r.edr)).toEqual([102, 99]);
  expect(filterIndex(rows, { query: "", mappedOnly: false, withRunsOnly: true }).map((r) => r.edr)).toEqual([102]);
});
