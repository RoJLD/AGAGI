import { render, cleanup } from "@testing-library/react";
import { afterEach, test, expect } from "vitest";
import { EnergyChart } from "./EnergyChart";
import type { EnergyBar } from "../lib/energy";

afterEach(() => cleanup());

const bars: EnergyBar[] = [
  { name: "biologie", value: 9, pct: 75 },
  { name: "action", value: 2, pct: 16.7 },
];

test("monte un conteneur recharts avec les barres", () => {
  const { container } = render(<EnergyChart bars={bars} title="Budget par phase" unit="énergie/tick/agent" />);
  expect(container.querySelector(".recharts-responsive-container")).toBeTruthy();
});
