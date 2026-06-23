// frontend/src/components/LiveEvolution.test.tsx
import { act, render, screen } from "@testing-library/react";
import { vi, test, expect } from "vitest";

let captured: ((e: unknown) => void) | null = null;
vi.mock("../hooks/useWebSocket", () => ({
  useWebSocket: (_path: string, onMessage: (e: unknown) => void) => {
    captured = onMessage;
    return { status: "open" };
  },
}));

import { LiveEvolution } from "./LiveEvolution";

test("affiche l'empty state puis les points reçus", () => {
  render(<LiveEvolution />);
  expect(screen.getByText(/Aucun run en cours/)).toBeTruthy();
  act(() => {
    captured!({ run: "soup", generation: 1, fitness: 0.4 });
    captured!({ run: "soup", generation: 2, fitness: 0.55 });
  });
  expect(screen.getByText("soup")).toBeTruthy();
  expect(screen.getByText("0.5500")).toBeTruthy();
});
