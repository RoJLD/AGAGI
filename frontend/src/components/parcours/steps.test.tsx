// frontend/src/components/parcours/steps.test.tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, beforeEach } from "vitest";

vi.mock("../../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../../api/client";
import { ToastProvider } from "../../contexts/ToastContext";
import { RunLauncher } from "../RunLauncher";

function renderWithProviders(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ToastProvider>{ui}</ToastProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue({ running: false, available_scripts: ["run.py"] });
});

test("RunLauncher appelle onLaunch au lancement de la file", async () => {
  const onLaunch = vi.fn();
  renderWithProviders(<RunLauncher onLaunch={onLaunch} />);
  // Attendre que le script soit sélectionné (useEffect post-query)
  await waitFor(() => {
    const select = document.querySelector("select") as HTMLSelectElement;
    expect(select?.value).toBe("run.py");
  });
  // enfile puis lance
  fireEvent.click(await screen.findByText(/Enfiler/));
  fireEvent.click(screen.getByText("Lancer la file"));
  expect(onLaunch).toHaveBeenCalledTimes(1);
  expect(onLaunch.mock.calls[0][0]).toMatchObject({ script_name: "run.py", n_seeds: 4 });
});
