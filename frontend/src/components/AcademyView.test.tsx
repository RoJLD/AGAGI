import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { AcademyView } from "./AcademyView";

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue({
    version_history: [{ title: "v1", description: "première" }],
    timeline: ["étape 1"],
    learning_goals: ["objectif 1"],
  });
});

test("rend les 3 boîtes Academy", async () => {
  renderWithClient(<AcademyView />);
  expect(await screen.findByText("Historique des versions")).toBeTruthy();
  expect(screen.getByText("Timeline")).toBeTruthy();
  expect(screen.getByText("Objectifs pédagogiques")).toBeTruthy();
});
