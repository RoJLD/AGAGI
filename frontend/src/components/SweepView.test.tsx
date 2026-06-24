import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { SweepView } from "./SweepView";

afterEach(() => cleanup());

const FIXTURE = [
  {
    run_id: "lewis_survival_sweep_42",
    name: "lewis_survival_sweep",
    knob: "forage_payoff",
    x: [0.1, 0.2, 0.3],
    series: { median_survival: [0.2, 0.5, 0.8], median_competence: [0.1, 0.3, 0.6] },
    y_std: { median_survival: [0.05, 0.05, 0.05] },
    seed: 42,
    commit: "abc1234",
  },
];

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue(FIXTURE);
});

test("affiche le sweep, le knob et un sélecteur de métrique (2 séries)", async () => {
  renderWithClient(<SweepView />);
  expect(await screen.findAllByText(/forage_payoff/)).toBeTruthy();
  // 2 séries -> sélecteur métrique présent
  expect(screen.getByLabelText(/Métrique/)).toBeTruthy();
});

test("état vide quand aucun sweep", async () => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  renderWithClient(<SweepView />);
  expect(await screen.findByText(/Aucun sweep disponible/)).toBeTruthy();
});

test("changer de métrique met à jour l'en-tête", async () => {
  renderWithClient(<SweepView />);
  await screen.findAllByText(/forage_payoff/);
  fireEvent.change(screen.getByLabelText(/Métrique/), { target: { value: "median_competence" } });
  expect(screen.getByText((_, el) => el?.tagName === 'STRONG' && el.textContent === 'median_competence')).toBeTruthy();
});
