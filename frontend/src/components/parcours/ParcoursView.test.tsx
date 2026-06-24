import { render, screen, fireEvent, cleanup, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, beforeEach, afterEach } from "vitest";

vi.mock("../../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../../api/client";
import { ToastProvider } from "../../contexts/ToastContext";
import { ActiveExperimentProvider } from "../../contexts/ActiveExperimentContext";
import { ParcoursView } from "./ParcoursView";

function renderView() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ToastProvider>
        <ActiveExperimentProvider>
          <ParcoursView />
        </ActiveExperimentProvider>
      </ToastProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  window.localStorage.clear();
  window.location.hash = "#/parcours";
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue({ running: false, available_scripts: ["run.py"] });
});

afterEach(() => {
  cleanup();
});

test("affiche la barre d'étapes et démarre sur Lancer", () => {
  renderView();
  expect(screen.getAllByRole("tab")).toHaveLength(4);
  expect(screen.getByTestId("step-lancer").getAttribute("aria-selected")).toBe("true");
});

test("cliquer sur Suivre sans run actif montre l'indice", async () => {
  renderView();
  fireEvent.click(screen.getByTestId("step-suivre"));
  await waitFor(() => {
    expect(screen.getByText(/Aucune expérience active/)).toBeTruthy();
  });
});
