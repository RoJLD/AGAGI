import { render, cleanup } from "@testing-library/react";
import { afterEach, test, expect } from "vitest";
import { ForageFunnelChart } from "./ForageFunnelChart";
import type { ForageBar } from "../lib/forage";

afterEach(() => cleanup());

const bars: ForageBar[] = [
  { name: "atteinte (p_reach)", value: 0.18, pct: 18 },
  { name: "capture si atteint (p_cap)", value: 1, pct: 100 },
  { name: "capture globale", value: 0.18, pct: 18 },
];

test("monte un conteneur recharts avec les barres", () => {
  const { container } = render(<ForageFunnelChart bars={bars} title="métab 0" />);
  expect(container.querySelector(".recharts-responsive-container")).toBeTruthy();
});
