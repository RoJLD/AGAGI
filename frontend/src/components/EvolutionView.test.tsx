// frontend/src/components/EvolutionView.test.tsx
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
vi.mock("./LiveEvolution", () => ({ LiveEvolution: () => <div>live-evolution-stub</div> }));
import { apiFetch } from "../api/client";
import { EvolutionView } from "./EvolutionView";

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  window.location.hash = "#/evolution?gate=AND";
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue({
    gate: "AND",
    history: { generation: [1, 2], fitness: [0.5, 0.8], accuracy: [0.6, 0.9], size: [5, 6] },
  });
});

test("rend le titre, le stub live et le graphe quand detail est chargé", async () => {
  renderWithClient(<EvolutionView />);
  expect(screen.getByText("live-evolution-stub")).toBeTruthy();
  expect(await screen.findByLabelText("Evolution chart")).toBeTruthy();
});
