import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { SweepView } from "./SweepView";

afterEach(() => cleanup());

const FIXTURE = [
  {
    run_id: "lewis_42",
    name: "lewis",
    knob: "forage_payoff",
    x: [0.1, 0.2, 0.3],
    series: { median_survival: [0.2, 0.5, 0.8], median_competence: [0.1, 0.3, 0.6] },
    y_std: { median_survival: [0.05, 0.05, 0.05] },
    seed: 42,
    commit: "abc",
  },
  {
    run_id: "lewis_43",
    name: "lewis2",
    knob: "forage_payoff",
    x: [0.1, 0.2, 0.3],
    series: { median_survival: [0.25, 0.55, 0.85] },
    seed: 43,
    commit: "def",
  },
];

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue(FIXTURE);
});

test("affiche le sélecteur de knob, la liste de séries et le graphe", async () => {
  const { container } = renderWithClient(<SweepView />);
  expect(await screen.findByLabelText(/Paramètre \(knob\)/)).toBeTruthy();
  expect(screen.getByText("lewis · median_survival")).toBeTruthy();
  expect(screen.getByText("lewis · median_competence")).toBeTruthy();
  expect(container.querySelector(".recharts-responsive-container")).toBeTruthy();
});

test("état vide quand aucun sweep", async () => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  renderWithClient(<SweepView />);
  expect(await screen.findByText(/Aucun sweep disponible/)).toBeTruthy();
});

test("le toggle de normalisation est présent", async () => {
  renderWithClient(<SweepView />);
  await screen.findByLabelText(/Paramètre \(knob\)/);
  expect(screen.getByText(/min-max/)).toBeTruthy();
});

test("cocher une 2e série l'ajoute à la superposition", async () => {
  renderWithClient(<SweepView />);
  await screen.findByLabelText(/Paramètre \(knob\)/);
  const second = screen.getByLabelText("lewis · median_competence") as HTMLInputElement;
  expect(second.checked).toBe(false);
  fireEvent.click(second);
  expect(second.checked).toBe(true);
});
