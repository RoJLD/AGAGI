import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

const navigate = vi.fn();
vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
vi.mock("../hooks/useHashRoute", () => ({
  useHashRoute: () => ({ tab: "carnet", gate: "", query: {}, setTab: vi.fn(), setGate: vi.fn(), navigate }),
}));
import { apiFetch } from "../api/client";
import { CarnetView } from "./CarnetView";

afterEach(() => cleanup());

const FEED = [{ run_id: "lewis_42", run_name: "lewis", id: "n1", text: "obs A", ts: "2026-06-25T10:00:00+00:00" }];

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => navigate.mockReset());

test("état vide", async () => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  renderWithClient(<CarnetView />);
  expect(await screen.findByText(/Aucune note/)).toBeTruthy();
});

test("rend le flux et deep-link vers le run", async () => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue(FEED);
  renderWithClient(<CarnetView />);
  expect(await screen.findByText("obs A")).toBeTruthy();
  fireEvent.click(screen.getByText("→ run"));
  expect(navigate).toHaveBeenCalledWith("runs", { run: "lewis_42" });
});
