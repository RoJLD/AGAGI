import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, test, expect } from "vitest";
import { RadarChart } from "./RadarChart";
import type { ExperimentSummary } from "../types";

afterEach(() => cleanup());

const EXP: ExperimentSummary[] = [
  {
    gate: "AND",
    latest_fitness: 0.8,
    latest_accuracy: 0.9,
    emergent_score: 0.5,
    performance_stability: 0.7,
    robustness_score: 0.6,
    hidden_ratio: 0.12,
    num_nodes: 172,
  },
];

test("le radar rend l'axe Ratio caché en plus des 5 axes existants", () => {
  render(<RadarChart experiments={EXP} />);
  expect(screen.getByText("Ratio caché")).toBeTruthy();
  expect(screen.getByText("Fitness")).toBeTruthy();
  expect(screen.getByText("Précision")).toBeTruthy();
  expect(screen.getByText("Intelligence")).toBeTruthy();
  expect(screen.getByText("Stabilité")).toBeTruthy();
  expect(screen.getByText("Robustesse")).toBeTruthy();
});
