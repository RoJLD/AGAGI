// frontend/src/components/TopologyView.test.tsx
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
vi.mock("./TopologyViewer", () => ({ TopologyViewer: () => <div>topology-stub</div> }));
import { apiFetch } from "../api/client";
import { TopologyView } from "./TopologyView";

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  window.location.hash = "#/topology?gate=AND";
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue({
    gate: "AND",
    graph: { nodes: [{ id: 0, label: "x", type: "input" }], links: [] },
    metrics: { modularity: 0.1, motif_density: 0.2, performance_stability: 0.3, robustness_score: 0.4, sparsity: 0.5, hidden_ratio: 0.6 },
  });
});

test("rend la topologie (stub) et l'analyse des motifs", async () => {
  renderWithClient(<TopologyView />);
  expect(await screen.findByText("topology-stub")).toBeTruthy();
  expect(screen.getByText(/Modularité/)).toBeTruthy();
});
