// frontend/src/components/ComparisonView.test.tsx
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
vi.mock("./ComparisonChart", () => ({ ComparisonChart: () => <div>comparison-chart-stub</div> }));
vi.mock("./RadarChart", () => ({ RadarChart: () => <div>radar-stub</div> }));
vi.mock("./ABComparisonView", () => ({ ABComparisonView: () => <div>ab-stub</div> }));
import { apiFetch } from "../api/client";
import { ComparisonView } from "./ComparisonView";

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue([{ gate: "AND", latest_fitness: 0.9, latest_accuracy: 1 }]);
});

test("mode global par défaut (sans ?ab=)", async () => {
  window.location.hash = "#/comparison";
  renderWithClient(<ComparisonView />);
  expect(await screen.findByText("comparison-chart-stub")).toBeTruthy();
});

test("mode AB si ?ab= présent dans le hash", async () => {
  window.location.hash = "#/comparison?ab=robust_eval";
  renderWithClient(<ComparisonView />);
  expect(await screen.findByText("ab-stub")).toBeTruthy();
});

test("la carte affiche Ratio caché et Nœuds quand présents, les masque sinon", async () => {
  window.location.hash = "#/comparison";
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue([
    { gate: "AND", latest_fitness: 0.8, latest_accuracy: 0.9, hidden_ratio: 0.12, num_nodes: 172 },
    { gate: "OR", latest_fitness: 0.7, latest_accuracy: 0.85 },
  ]);
  renderWithClient(<ComparisonView />);
  expect(await screen.findByText(/Ratio caché: 0\.120/)).toBeTruthy();
  expect(screen.getByText(/Nœuds: 172/)).toBeTruthy();
  expect(screen.getAllByText(/Ratio caché:/).length).toBe(1);
  expect(screen.getAllByText(/Nœuds:/).length).toBe(1);
});
