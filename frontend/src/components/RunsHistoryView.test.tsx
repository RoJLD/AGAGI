import { render, screen, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
vi.mock("../contexts/ToastContext", () => ({ useToast: () => ({ notify: vi.fn() }) }));
vi.mock("../hooks/useHashRoute", () => ({
  useHashRoute: () => ({
    tab: "runs",
    gate: "",
    query: { run: "lewis_42" },
    setTab: vi.fn(),
    setGate: vi.fn(),
    navigate: vi.fn(),
  }),
}));
import { apiFetch } from "../api/client";
import { RunsHistoryView } from "./RunsHistoryView";

afterEach(() => cleanup());

const RUNS = [{ run_id: "lewis_42", name: "lewis", seed: 42, commit: "abc", metrics: ["median_survival"] }];
const DETAIL = {
  run_id: "lewis_42",
  name: "lewis",
  seed: 42,
  commit: "abc",
  data: { median_survival: 0.5 },
  links: { edr: [], articles: [] },
};

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  (apiFetch as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
    if (path === "/api/runs") return Promise.resolve(RUNS);
    if (path.endsWith("/article-links")) return Promise.resolve({});
    if (path.endsWith("/notes")) return Promise.resolve([]);
    if (path === "/api/runs/lewis_42") return Promise.resolve(DETAIL);
    return Promise.resolve([]);
  });
});

test("deep-link ?run ouvre directement le détail du run", async () => {
  renderWithClient(<RunsHistoryView />);
  expect(await screen.findByText(/Détail — lewis_42/)).toBeTruthy();
});

test("le panneau Carnet est rendu dans le détail", async () => {
  renderWithClient(<RunsHistoryView />);
  expect(await screen.findByText(/Aucune note pour ce run/)).toBeTruthy();
});
