import { render, screen, fireEvent, cleanup, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { ABComparisonView } from "./ABComparisonView";

const CONDITIONS = [
  { name: "A", n_seeds: 4, seeds: [0, 1, 2, 3], metrics: ["fitness"] },
  { name: "B", n_seeds: 4, seeds: [0, 1, 2, 3], metrics: ["fitness"] },
  { name: "C", n_seeds: 4, seeds: [0, 1, 2, 3], metrics: ["fitness"] },
];

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue(CONDITIONS);
});

afterEach(() => {
  cleanup();
});

describe("ABComparisonView", () => {
  it("appelle onBaselineChange quand l'utilisateur change la Condition B", async () => {
    const spy = vi.fn();
    renderWithClient(<ABComparisonView onBaselineChange={spy} />);

    // Attendre que les conditions soient chargées
    await waitFor(() => {
      expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(2);
    });

    // Le second select est la Condition B
    const selects = screen.getAllByRole("combobox");
    const selectB = selects[1];

    fireEvent.change(selectB, { target: { value: "C" } });

    expect(spy).toHaveBeenCalledWith("C");
  });

  it("ne appelle pas onBaselineChange lors du pré-remplissage automatique", async () => {
    const spy = vi.fn();
    renderWithClient(<ABComparisonView onBaselineChange={spy} />);

    // Attendre que les conditions soient chargées (auto-fill useEffect)
    await waitFor(() => {
      expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(2);
    });

    // L'auto-fill ne doit pas déclencher le callback
    expect(spy).not.toHaveBeenCalled();
  });
});
