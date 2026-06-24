// frontend/src/components/GateSidebar.test.tsx
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { GateSidebar } from "./GateSidebar";

const EXPS = [
  { gate: "AND", latest_fitness: 0.9, latest_accuracy: 1, emergent_score: 0.5, robustness_score: 0.4, performance_stability: 0.3, latest_size: 7 },
  { gate: "OR", latest_fitness: 0.8, latest_accuracy: 0.9 },
];

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  window.location.hash = "#/evolution?gate=AND";
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue(EXPS);
});

test("affiche le select de porte et une métrique agrégée", async () => {
  renderWithClient(<GateSidebar />);
  expect(await screen.findByText("Vue globale")).toBeTruthy();
  expect(screen.getByText(/Total portes : 2/)).toBeTruthy();
});
