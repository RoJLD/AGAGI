import { render, screen, fireEvent, cleanup, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));

const notify = vi.fn();
vi.mock("../contexts/ToastContext", () => ({ useToast: () => ({ notify }) }));

import { apiFetch } from "../api/client";
import { RunNotes } from "./RunNotes";

afterEach(() => cleanup());

beforeEach(() => {
  (apiFetch as ReturnType<typeof vi.fn>).mockReset();
  notify.mockReset();
});

const NOTE = { id: "n1", text: "seed 3 a divergé", ts: "2026-06-25T10:00:00+00:00" };

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

test("liste vide affiche un message", async () => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  renderWithClient(<RunNotes runId="lewis_42" />);
  expect(await screen.findByText(/Aucune note pour ce run/)).toBeTruthy();
});

test("affiche une note existante", async () => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue([NOTE]);
  renderWithClient(<RunNotes runId="lewis_42" />);
  expect(await screen.findByText("seed 3 a divergé")).toBeTruthy();
});

test("ajouter une note poste sur l'endpoint et affiche un toast succès", async () => {
  const fn = apiFetch as ReturnType<typeof vi.fn>;
  fn.mockResolvedValueOnce([]); // GET initial
  fn.mockResolvedValueOnce(NOTE); // POST
  fn.mockResolvedValueOnce([NOTE]); // GET après invalidation
  renderWithClient(<RunNotes runId="lewis_42" />);
  await screen.findByText(/Aucune note pour ce run/);
  fireEvent.change(screen.getByLabelText("Nouvelle note"), { target: { value: "seed 3 a divergé" } });
  fireEvent.click(screen.getByText("Ajouter"));
  await waitFor(() =>
    expect(fn).toHaveBeenCalledWith("/api/runs/lewis_42/notes", expect.objectContaining({ method: "POST" })),
  );
  expect(notify).toHaveBeenCalledWith("Note ajoutée.", "success");
});

test("échec d'ajout → toast d'erreur", async () => {
  const fn = apiFetch as ReturnType<typeof vi.fn>;
  fn.mockResolvedValueOnce([]); // GET initial
  fn.mockRejectedValueOnce(new Error("boom")); // POST échoue
  renderWithClient(<RunNotes runId="lewis_42" />);
  await screen.findByText(/Aucune note pour ce run/);
  fireEvent.change(screen.getByLabelText("Nouvelle note"), { target: { value: "seed 3 a divergé" } });
  fireEvent.click(screen.getByText("Ajouter"));
  await waitFor(() => expect(notify).toHaveBeenCalledWith("Échec de l'ajout de la note.", "error"));
});
