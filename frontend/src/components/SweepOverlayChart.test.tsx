import { render, cleanup } from "@testing-library/react";
import { afterEach, test, expect } from "vitest";
import { SweepOverlayChart } from "./SweepOverlayChart";
import type { OverlaySeries } from "../lib/sweep";

afterEach(() => cleanup());

const series: OverlaySeries[] = [
  { id: "r1::m", label: "run1 · m", knob: "k", x: [1, 2, 3], y: [1, 2, 3] },
  { id: "r2::m", label: "run2 · m", knob: "k", x: [1, 2, 3], y: [3, 2, 1] },
];

test("monte un conteneur recharts en superposition (2 séries)", () => {
  const { container } = render(<SweepOverlayChart series={series} knob="forage_payoff" normalize={false} />);
  expect(container.querySelector(".recharts-responsive-container")).toBeTruthy();
});

test("monte avec une seule série en mode normalisé", () => {
  const { container } = render(<SweepOverlayChart series={[series[0]]} knob="k" normalize={true} />);
  expect(container.querySelector(".recharts-responsive-container")).toBeTruthy();
});
