import { test, expect } from "vitest";
import { buildProvenanceGraph, provenanceTarget } from "./provenance";
import type { Article, RunSummary } from "../types";

const runs: RunSummary[] = [
  { run_id: "condA_0", name: "condA", seed: 0, metrics: [] },
  { run_id: "condA_1", name: "condA", seed: 1, metrics: [] },
];
const articles: Article[] = [{ id: "art1", title: "Découverte X", content: "", timestamp: "" }];

test("assemble nœuds/edges et déduplique", () => {
  const { nodes, edges } = buildProvenanceGraph(
    { "81": ["condA_0", "condA_1"] },          // EDR 81 lié aux 2 seeds de condA
    { condA_0: ["art1"] },                     // article art1 lié à condA via condA_0
    runs,
    articles,
  );
  const ids = nodes.map((n) => n.id).sort();
  expect(ids).toEqual(["art:art1", "cond:condA", "edr:81"]);
  expect(nodes.find((n) => n.id === "edr:81")!.label).toBe("EDR 81");
  expect(nodes.find((n) => n.id === "art:art1")!.label).toBe("Découverte X");
  // edge condA–EDR dédupliqué (2 seeds -> 1 edge), + condA–article
  expect(edges).toHaveLength(2);
  expect(edges).toContainEqual({ source: "cond:condA", target: "edr:81" });
  expect(edges).toContainEqual({ source: "cond:condA", target: "art:art1" });
});

test("exclut les orphelins (lien vers un run inconnu)", () => {
  const { nodes } = buildProvenanceGraph({ "99": ["ghost_0"] }, {}, runs, articles);
  expect(nodes).toHaveLength(0); // run inconnu -> aucune condition -> EDR 99 orphelin exclu
});

test("article sans titre connu -> label = id", () => {
  const { nodes } = buildProvenanceGraph({}, { condA_0: ["artX"] }, runs, []);
  expect(nodes.find((n) => n.id === "art:artX")!.label).toBe("artX");
});

test("provenanceTarget mappe chaque type vers sa cible", () => {
  expect(provenanceTarget({ id: "cond:condA", type: "condition", label: "condA" })).toEqual({
    tab: "comparison",
    query: { ab: "condA" },
  });
  expect(provenanceTarget({ id: "edr:81", type: "edr", label: "EDR 81" })).toEqual({ tab: "edr", query: {} });
  expect(provenanceTarget({ id: "art:art1", type: "article", label: "X" })).toEqual({
    tab: "laboratoire",
    query: {},
  });
});
