// frontend/src/components/LiveEvolution.test.tsx
import { act, cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, vi, test, expect } from "vitest";

afterEach(cleanup);

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

test("flush le buffer quand le run change", () => {
  render(<LiveEvolution />);
  act(() => {
    captured!({ run: "soup", generation: 1, fitness: 0.4 });
    captured!({ run: "soup", generation: 2, fitness: 0.55 });
  });
  act(() => {
    captured!({ run: "stoneage", generation: 1, fitness: 0.7 });
  });
  expect(screen.getByText("stoneage")).toBeTruthy();
  // Après le changement de run, le buffer est vidé : un seul point affiché
  expect(screen.getByText("0.7000")).toBeTruthy();
  // Points = 1 (pas 3 — le merge inter-stage est interdit)
  // On cible le bloc "Points" pour éviter l'ambiguïté avec Génération=1
  const pointsStat = screen.getByText("Points").closest(".live-stat")!;
  expect(within(pointsStat).getByText("1")).toBeTruthy();
});
