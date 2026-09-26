import type { ReactNode } from "react";
import { cleanup, render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

vi.mock("../../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../../api/client";
import { PilotagePortesView } from "./PilotagePortesView";
import { pilotageDegrade, pilotageFixture, RACINE } from "./fixture";

const mocked = apiFetch as ReturnType<typeof vi.fn>;

function rendre(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => mocked.mockResolvedValue(pilotageFixture()));
afterEach(() => {
  cleanup();
  mocked.mockReset();
});

test("table des portes, dans l'ordre publié, avec la phrase fixe « aucune porte n'est exécutée d'ici »", async () => {
  rendre(<PilotagePortesView />);
  const table = await screen.findByRole("table", { name: "Portes du hook pre-commit" });
  expect(screen.getByText(/aucune porte n'est exécutée d'ici/)).toBeTruthy();
  const nums = within(table)
    .getAllByRole("row")
    .slice(1)
    .map((r) => r.querySelector("td")!.textContent);
  expect(nums).toEqual(["1", "4", "7", "12"]);
  expect(screen.getByText("4 porte(s) branchée(s) au hook.")).toBeTruthy();
});

test("porte hors PORTES : « non mutée », jamais 0 ; baseline non recensée : jamais « aucune »", async () => {
  rendre(<PilotagePortesView />);
  const table = await screen.findByRole("table", { name: "Portes du hook pre-commit" });
  const ligne7 = within(table).getByText("tools.check_staged_authorship").closest("tr")!;
  expect(within(ligne7).getByText("non mutée (hors PORTES)")).toBeTruthy();
  expect(within(ligne7).getByText("non recensée (BASELINES)")).toBeTruthy();
  expect(within(ligne7).queryByText(/aucune/)).toBeNull();
  const ligne1 = within(table).getByText("tools.check_record_links").closest("tr")!;
  expect(within(ligne1).getByText("non comptée")).toBeTruthy();
  const ligne4 = within(table).getByText("tools.check_backlog_freshness").closest("tr")!;
  expect(within(ligne4).getByText("2")).toBeTruthy(); // dette comptée : servie telle quelle
});

test("baseline présente : lien ; absente : barrée, non cliquable, dette « non comptée » (lue DANS le fichier)", async () => {
  rendre(<PilotagePortesView />);
  const table = await screen.findByRole("table", { name: "Portes du hook pre-commit" });
  expect(
    within(table)
      .getByRole("link", { name: "ouvrir tools/record_link_baseline.json dans VS Code" })
      .getAttribute("href"),
  ).toBe(`vscode://file/${RACINE}/tools/record_link_baseline.json`);
  const absente = within(table).getByText("tools/data_paths_baseline.json");
  expect(absente.tagName).toBe("S");
  expect(absente.closest("a")).toBeNull();
  expect(within(absente.closest("tr")!).getByText("non comptée")).toBeTruthy();
});

test("portes null : Empty qui reprend la ligne, aucune table", async () => {
  const ligne = "portes : tools/hooks/pre-commit illisible";
  mocked.mockResolvedValue(pilotageFixture({ portes: null, aveugle: [ligne] }));
  rendre(<PilotagePortesView />);
  expect(await screen.findByText(`Portes indisponible — ${ligne}`)).toBeTruthy();
  expect(screen.queryByRole("table")).toBeNull();
});

test("mode dégradé : alerte + Empty", async () => {
  mocked.mockResolvedValue(pilotageDegrade());
  rendre(<PilotagePortesView />);
  expect((await screen.findByRole("alert")).textContent).toContain("pilotage: ImportError");
  expect(screen.getByText(/^Portes indisponible — pilotage: ImportError/)).toBeTruthy();
});
