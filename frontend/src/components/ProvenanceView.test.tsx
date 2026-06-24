// frontend/src/components/ProvenanceView.test.tsx
import { render, screen, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { ProvenanceView } from "./ProvenanceView";

afterEach(() => cleanup());

function mockEndpoints(map: Record<string, unknown>) {
  (apiFetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
    const key = Object.keys(map).find((k) => url.includes(k));
    return Promise.resolve(key ? map[key] : []);
  });
}

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  window.location.hash = "#/provenance";
  mockEndpoints({
    "edr-links": { "81": ["condA_0"] },
    "article-links": { condA_0: ["art1"] },
    "runs": [{ run_id: "condA_0", name: "condA", seed: 0, metrics: [] }],
    "sociologist/articles": [{ id: "art1", title: "Découverte X", content: "", timestamp: "" }],
  });
});

test("rend le graphe (svg) et la légende avec des données liées", async () => {
  renderWithClient(<ProvenanceView />);
  expect(await screen.findByText(/Provenance/)).toBeTruthy();
  // légende des 3 types
  expect(screen.getByText(/Condition/)).toBeTruthy();
  expect(screen.getByText(/Article/)).toBeTruthy();
});

test("état vide quand aucun lien", async () => {
  mockEndpoints({ "runs": [{ run_id: "condA_0", name: "condA", seed: 0, metrics: [] }] }); // pas de liens
  renderWithClient(<ProvenanceView />);
  expect(await screen.findByText(/Aucun lien/)).toBeTruthy();
});
