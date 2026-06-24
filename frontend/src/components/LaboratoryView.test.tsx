import { render, screen, cleanup, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { LaboratoryView } from "./LaboratoryView";

const EXPERIMENTS = [
  { gate: "A" },
  { gate: "B" },
  { gate: "C" },
];

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  (apiFetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
    if (url === "/api/experiments") return Promise.resolve(EXPERIMENTS);
    if (url === "/api/sociologist/articles") return Promise.resolve([]);
    return Promise.resolve([]);
  });
});

afterEach(() => {
  cleanup();
});

describe("LaboratoryView", () => {
  it("auto-remplit la baseline quand initialIntervention est défini mais pas initialBaseline", async () => {
    renderWithClient(<LaboratoryView initialIntervention="B" />);

    await waitFor(() => {
      // Le select Baseline ne doit pas être vide — il doit choisir une gate != "B"
      const selects = screen.getAllByRole("combobox");
      const baselineSelect = selects[0]; // premier select = Baseline
      expect(baselineSelect).toBeDefined();
      // La valeur doit être "A" ou "C" (pas "B", pas "")
      const val = (baselineSelect as HTMLSelectElement).value;
      expect(val).toBeTruthy();
      expect(val).not.toBe("B");
    });
  });

  it("auto-remplit baseline ET intervention quand aucun prop n'est passé", async () => {
    renderWithClient(<LaboratoryView />);

    await waitFor(() => {
      const selects = screen.getAllByRole("combobox");
      const baselineVal = (selects[0] as HTMLSelectElement).value;
      const interventionVal = (selects[1] as HTMLSelectElement).value;
      expect(baselineVal).toBeTruthy();
      expect(interventionVal).toBeTruthy();
    });
  });
});
