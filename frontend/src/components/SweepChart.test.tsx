import { render, cleanup } from "@testing-library/react";
import { afterEach, test, expect } from "vitest";
import { SweepChart } from "./SweepChart";

afterEach(() => cleanup());

test("monte un conteneur recharts avec une bande", () => {
  const { container } = render(
    <SweepChart x={[0.1, 0.2, 0.3]} knob="forage_payoff" metric="median_survival" y={[0.2, 0.5, 0.8]} yStd={[0.05, 0.05, 0.05]} />,
  );
  expect(container.querySelector(".recharts-responsive-container")).toBeTruthy();
});

test("monte sans bande quand yStd absent", () => {
  const { container } = render(
    <SweepChart x={[0.1, 0.2]} knob="k" metric="m" y={[1, 2]} />,
  );
  expect(container.querySelector(".recharts-responsive-container")).toBeTruthy();
});
