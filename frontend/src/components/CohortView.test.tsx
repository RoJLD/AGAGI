import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { CohortView } from "./CohortView";

afterEach(() => cleanup());

const CONDITIONS = [
  { name: "A", n_seeds: 3, seeds: [0, 1, 2], metrics: ["fitness", "survie"] },
  { name: "B", n_seeds: 3, seeds: [0, 1, 2], metrics: ["fitness"] },
];
const DISTS = [
  { name: "A", vals: [9, 10, 11], n: 3 },
  { name: "B", vals: [1, 2, 3], n: 3 },
];

function mockApi(conditions: unknown, dists: unknown) {
  (apiFetch as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
    if (path.endsWith("/api/runs/conditions")) return Promise.resolve(conditions);
    if (path.includes("/api/runs/distributions")) return Promise.resolve(dists);
    return Promise.resolve([]);
  });
}

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => mockApi(CONDITIONS, DISTS));

test("rend le sélecteur de métrique et le graphe", async () => {
  const { container } = renderWithClient(<CohortView />);
  expect(await screen.findByLabelText(/Métrique/)).toBeTruthy();
  expect(container.querySelector("svg.cohort-chart")).toBeTruthy();
  expect(container.querySelectorAll('[data-testid="cohort-row"]').length).toBe(2);
});

test("état vide quand aucune métrique numérique", async () => {
  mockApi([{ name: "A", n_seeds: 1, seeds: [0], metrics: [] }], []);
  renderWithClient(<CohortView />);
  expect(await screen.findByText(/Aucune métrique numérique/)).toBeTruthy();
});

test("changer de métrique met à jour l'en-tête", async () => {
  renderWithClient(<CohortView />);
  await screen.findByLabelText(/Métrique/);
  fireEvent.change(screen.getByLabelText(/Métrique/), { target: { value: "survie" } });
  expect(
    screen.getByText((_, el) => el?.tagName === "STRONG" && el.textContent === "survie"),
  ).toBeTruthy();
});
