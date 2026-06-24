import { render, cleanup } from "@testing-library/react";
import { afterEach, test, expect } from "vitest";
import { ProvenanceGraph } from "./ProvenanceGraph";

afterEach(() => cleanup());

test("monte un svg avec les nœuds", () => {
  const { container } = render(
    <ProvenanceGraph
      nodes={[
        { id: "cond:condA", type: "condition", label: "condA" },
        { id: "edr:81", type: "edr", label: "EDR 81" },
      ]}
      edges={[{ source: "cond:condA", target: "edr:81" }]}
      onSelect={() => {}}
    />,
  );
  const svg = container.querySelector("svg");
  expect(svg).toBeTruthy();
  // 2 nœuds rendus (groupes <g> avec cercle)
  expect(container.querySelectorAll("circle").length).toBe(2);
});
