import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

const navigate = vi.fn();
vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
vi.mock("../hooks/useHashRoute", () => ({
  useHashRoute: () => ({ tab: "synthese", gate: "", query: {}, setTab: vi.fn(), setGate: vi.fn(), navigate }),
}));
import { apiFetch } from "../api/client";
import { EdrIndexView } from "./EdrIndexView";

afterEach(() => cleanup());

const DOCS = [
  { edr: 102, title: "Monoculture porte l'apex", file: "102_x.md" },
  { edr: 101, title: "Metabolisme rescale", file: "101_y.md" },
];
const CURATED = { findings: [{ edr: 102 }, { edr: 50, stub: true }] };
const LINKS = { "102": ["lewis_7"] };

function mockApi(docs: unknown, curated: unknown, links: unknown) {
  (apiFetch as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
    if (path.endsWith("/api/edr/docs")) return Promise.resolve(docs);
    if (path.endsWith("/api/runs/edr-links")) return Promise.resolve(links);
    if (path.endsWith("/api/edr")) return Promise.resolve(curated);
    return Promise.resolve([]);
  });
}

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  navigate.mockReset();
  mockApi(DOCS, CURATED, LINKS);
});

test("affiche le bandeau stats et la table", async () => {
  renderWithClient(<EdrIndexView />);
  expect(await screen.findByText(/2 EDR/)).toBeTruthy();
  expect(screen.getByText("Monoculture porte l'apex")).toBeTruthy();
  expect(screen.getByText("Metabolisme rescale")).toBeTruthy();
});

test("la recherche filtre les lignes", async () => {
  renderWithClient(<EdrIndexView />);
  await screen.findByText("Monoculture porte l'apex");
  fireEvent.change(screen.getByLabelText(/Rechercher/), { target: { value: "metabolisme" } });
  expect(screen.queryByText("Monoculture porte l'apex")).toBeNull();
  expect(screen.getByText("Metabolisme rescale")).toBeTruthy();
});

test("clic sur un run deep-linke vers son détail", async () => {
  renderWithClient(<EdrIndexView />);
  await screen.findByText("Monoculture porte l'apex");
  fireEvent.click(screen.getByText(/→ lewis_7/));
  expect(navigate).toHaveBeenCalledWith("runs", { run: "lewis_7" });
});

test("état vide quand aucun EDR documenté", async () => {
  mockApi([], { findings: [] }, {});
  renderWithClient(<EdrIndexView />);
  expect(await screen.findByText(/Aucun EDR documenté/)).toBeTruthy();
});
