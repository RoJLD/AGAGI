import { render, cleanup } from "@testing-library/react";
import { afterEach, test, expect } from "vitest";
import { CohortChart } from "./CohortChart";
import type { CohortRow } from "../lib/cohort";
import { computeBoxStats } from "../lib/cohort";

afterEach(() => cleanup());

const ROWS: CohortRow[] = [
  { name: "haute", vals: [9, 10, 11], stats: computeBoxStats([9, 10, 11]) },
  { name: "basse", vals: [1, 2, 3], stats: computeBoxStats([1, 2, 3]) },
];

test("monte un <svg> avec une ligne par condition", () => {
  const { container } = render(<CohortChart rows={ROWS} metric="fitness" />);
  const svg = container.querySelector("svg");
  expect(svg).toBeTruthy();
  expect(svg?.getAttribute("aria-label")).toContain("fitness");
  expect(container.querySelectorAll('[data-testid="cohort-row"]').length).toBe(2);
});

test("trace un cercle par seed", () => {
  const { container } = render(<CohortChart rows={ROWS} metric="fitness" />);
  // 3 + 3 seeds -> 6 cercles
  expect(container.querySelectorAll("circle").length).toBe(6);
});
