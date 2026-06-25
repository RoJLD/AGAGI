import { render, screen, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { EnergyView } from "./EnergyView";

afterEach(() => cleanup());

const PHASES = {
  brain: 1, action: 2, biologie: 9, mouvement: 0, net: 12, n_agents: 40,
  bio_metab: 13.47, bio_terrain: 0.27, bio_carry: 0.13, bio_autres: 0.13,
};
const FIXTURE = [
  {
    run_id: "lewis_drain_decompose_7",
    name: "lewis_drain_decompose",
    seed: 7,
    commit: "abc",
    phases: PHASES,
    verdict: "biologie domine (75%)",
    bio_verdict: "métabolisme domine",
  },
];

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue(FIXTURE));

test("affiche le sélecteur, les verdicts et deux charts", async () => {
  const { container } = renderWithClient(<EnergyView />);
  expect(await screen.findByLabelText(/Run de décomposition/)).toBeTruthy();
  expect(screen.getByText(/biologie domine/)).toBeTruthy();
  expect(container.querySelectorAll(".recharts-responsive-container").length).toBe(2);
});

test("état vide quand aucune décomposition", async () => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  renderWithClient(<EnergyView />);
  expect(await screen.findByText(/Aucune décomposition énergétique/)).toBeTruthy();
});
