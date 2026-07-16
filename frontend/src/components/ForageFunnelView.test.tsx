import { render, screen, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { ForageFunnelView } from "./ForageFunnelView";

afterEach(() => cleanup());

const FIXTURE = [
  {
    run_id: "lewis_forage_funnel_7",
    name: "lewis_forage_funnel",
    seed: 7,
    commit: "abc",
    verdict: "APPROCHE casse (p_reach 0.18)",
    levels: [
      { metab: 0, p_reach: 0.18, p_cap: 1, income_t: 0.5, drain_t: 0.2, mean_captures: 1.2, mean_contacts: 6.5, mean_min_dist: 3.1, n_agents: 40 },
      { metab: 0.25, p_reach: 0.12, p_cap: 1, income_t: 0.3, drain_t: 0.4, mean_captures: 0.8, mean_contacts: 5.0, mean_min_dist: 3.6, n_agents: 38 },
    ],
  },
];

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue(FIXTURE));

test("affiche le sélecteur, le verdict et un chart par niveau", async () => {
  const { container } = renderWithClient(<ForageFunnelView />);
  expect(await screen.findByLabelText(/Run d'entonnoir/)).toBeTruthy();
  expect(screen.getByText(/APPROCHE casse/)).toBeTruthy();
  expect(container.querySelectorAll(".recharts-responsive-container").length).toBe(2);
});

test("état vide quand aucun entonnoir", async () => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  renderWithClient(<ForageFunnelView />);
  expect(await screen.findByText(/Aucun entonnoir de forage/)).toBeTruthy();
});
