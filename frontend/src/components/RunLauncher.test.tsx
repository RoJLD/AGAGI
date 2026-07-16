import { render, screen, fireEvent, cleanup, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, afterEach, beforeEach } from "vitest";

vi.mock("../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../api/client";
import { ToastProvider } from "../contexts/ToastContext";
import { RunLauncher } from "./RunLauncher";

afterEach(() => cleanup());

beforeEach(() => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue({
    running: false,
    available_scripts: ["main_biosphere.py"],
  });
});

function renderWithClient(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ToastProvider>{ui}</ToastProvider>
    </QueryClientProvider>,
  );
}

test("le bouton Enfiler ajoute n_seeds badges pending à la file", async () => {
  renderWithClient(<RunLauncher />);
  // attend que le script se peuple depuis /api/sandbox/status
  await screen.findByRole("option", { name: "main_biosphere.py" });
  // ANTI-FLAKE : script_name est peuplé par un useEffect async ; tant qu'il est vide, validateRunConfig
  // renvoie une erreur et le bouton Enfiler reste désactivé (enqueue no-op). On attend donc que le bouton
  // soit ACTIVÉ (précondition observable) avant de cliquer — sinon course perdue en CI = zéro badge.
  await waitFor(() =>
    expect((screen.getByRole("button", { name: /Enfiler/ }) as HTMLButtonElement).disabled).toBe(false),
  );
  fireEvent.click(screen.getByRole("button", { name: /Enfiler/ }));
  const badges = await screen.findAllByText(/· pending$/);
  expect(badges).toHaveLength(4); // n_seeds défaut = 4
});
