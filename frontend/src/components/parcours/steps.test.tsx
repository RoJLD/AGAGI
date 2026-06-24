// frontend/src/components/parcours/steps.test.tsx
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect, beforeEach, afterEach } from "vitest";

vi.mock("../../api/client", () => ({ apiFetch: vi.fn() }));
// LiveEvolution (monté par StepSuivre) ouvre un WebSocket réel — stubbé en jsdom.
vi.mock("../../hooks/useWebSocket", () => ({
  useWebSocket: () => ({ status: "closed" }),
}));
import { apiFetch } from "../../api/client";
import { ToastProvider } from "../../contexts/ToastContext";
import { RunLauncher } from "../RunLauncher";
import { StepSuivre } from "./StepSuivre";
import { StepLancer } from "./StepLancer";
import { ActiveExperimentProvider } from "../../contexts/ActiveExperimentContext";

function renderWithProviders(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ToastProvider>{ui}</ToastProvider>
    </QueryClientProvider>,
  );
}

afterEach(() => cleanup());

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

test("StepSuivre montre un indice quand aucune expérience active et rien ne tourne", () => {
  renderWithProviders(
    <ActiveExperimentProvider>
      <StepSuivre running={false} hasActive={false} onNext={() => {}} />
    </ActiveExperimentProvider>,
  );
  expect(screen.getByText(/Aucune expérience active/)).toBeTruthy();
});

test("StepSuivre rend la courbe d'évolution ET le dashboard quand un run tourne", () => {
  renderWithProviders(
    <ActiveExperimentProvider>
      <StepSuivre running={true} hasActive={false} onNext={() => {}} />
    </ActiveExperimentProvider>,
  );
  expect(screen.getByText("Évolution en direct")).toBeTruthy(); // LiveEvolution en tête
  expect(screen.getByText(/Visualisation 2D/)).toBeTruthy(); // LiveDashboard dessous
});

test("StepLancer enregistre l'expérience active au lancement", async () => {
  window.localStorage.clear();
  renderWithProviders(
    <ActiveExperimentProvider>
      <StepLancer onNext={() => {}} />
    </ActiveExperimentProvider>,
  );
  // Attendre que le script soit chargé (useEffect post-query) avant d'enfiler
  await waitFor(() => {
    const select = document.querySelector("select") as HTMLSelectElement;
    expect(select?.value).toBe("run.py");
  });
  fireEvent.click(await screen.findByText(/Enfiler/));
  fireEvent.click(screen.getByText("Lancer la file"));
  const stored = JSON.parse(window.localStorage.getItem("agiseed.activeExperiment")!);
  expect(stored.scriptName).toBe("run.py");
  expect(stored.seeds).toEqual([0, 1, 2, 3]);
});
