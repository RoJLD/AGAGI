import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, beforeEach } from "vitest";

vi.mock("../../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../../api/client";
import { LiveDashboard } from "./LiveDashboard";

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue({ size: 0, logs: [], data: [] });
});

test("rend les panneaux live (monde, terminal, télémétrie)", () => {
  renderWithClient(<LiveDashboard />);
  expect(screen.getByText(/Visualisation 2D/)).toBeTruthy();
  expect(screen.getByText(/Terminal Biosphère/)).toBeTruthy();
  expect(screen.getByText(/Télémétrie Cognitive/)).toBeTruthy();
  expect(screen.getByText(/Interventions God-Mode/)).toBeTruthy();
  expect(screen.getByText(/Journal du Superviseur/)).toBeTruthy();
});
