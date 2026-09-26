import type { ReactNode } from "react";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

vi.mock("../../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../../api/client";
import { PilotageRoadmapView } from "./PilotageRoadmapView";
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

async function tableEntrees() {
  rendre(<PilotageRoadmapView />);
  return screen.findByRole("table", { name: "Entrées du backlog" });
}

test("lien d'une entrée : vscode://file/ + racine de TÊTE + backlog + lignes[0]", async () => {
  const table = await tableEntrees();
  const lien = within(table).getByRole("link", { name: /ouvrir P2\.78 dans VS Code/ });
  expect(lien.getAttribute("href")).toBe(`vscode://file/${RACINE}/docs/roadmap/PRIORITES_ET_DETTES.md:671`);
});

test("chemin cité présent : lien SANS ligne ; absent : barré, « (absent) », non cliquable", async () => {
  const table = await tableEntrees();
  const lien = within(table).getByRole("link", { name: "ouvrir tools/cost_guard.py dans VS Code" });
  expect(lien.getAttribute("href")).toBe(`vscode://file/${RACINE}/tools/cost_guard.py`);
  const absent = within(table).getByText("tools/disparu.py");
  expect(absent.tagName).toBe("S");
  expect(absent.closest("a")).toBeNull();
  expect(within(table).getByText("(absent)")).toBeTruthy();
});

test("chemins non captés par le motif : dits par entrée ET sous la table", async () => {
  const table = await tableEntrees();
  expect(within(table).getByText("+ 2 non reconnu(s) par le motif")).toBeTruthy();
  expect(screen.getByText(/^2 chemin\(s\) cité\(s\) non reconnu\(s\) par le motif du cliquet/)).toBeTruthy();
});

test("clauses : satisfaite / invérifiable avec sa raison en TEXTE visible", async () => {
  const table = await tableEntrees();
  expect(within(table).getByText("satisfaite").className).toContain("badge--success");
  expect(within(table).getByText("invérifiable").className).toContain("badge--purple");
  expect(within(table).getByText("existe ICI mais n'est PAS SUIVI par git")).toBeTruthy();
});

test("une entrée illisible est rendue, avec sa raison", async () => {
  const table = await tableEntrees();
  expect(within(table).getByText("illisible").className).toContain("badge--danger");
  expect(within(table).getByText("IndexError: list index out of range")).toBeTruthy();
});

test("le titre est rendu EN ENTIER, markdown tel quel (jamais interprété ni tronqué dans le DOM)", async () => {
  const table = await tableEntrees();
  expect(within(table).getByText("garde de coût — voir [ADR-004](docs/ADR/ADR-004.md) pour le détail")).toBeTruthy();
});

test("filtre de statut", async () => {
  const table = await tableEntrees();
  fireEvent.change(screen.getByLabelText("Statut"), { target: { value: "close" } });
  expect(within(table).getByText("P2.78")).toBeTruthy();
  expect(within(table).queryByText("P2.114")).toBeNull();
  expect(screen.getByText("1 entrée(s) affichée(s) sur 4")).toBeTruthy();
});

test("direction : un rang porté par deux entrées donne UNE ligne, chaque entrée avec SON statut", async () => {
  rendre(<PilotageRoadmapView />);
  const dir = await screen.findByRole("table", { name: /Direction/ });
  const ligne = within(dir).getByText("1").closest("tr")!;
  const statutDe = (p: string) =>
    [...ligne.querySelectorAll(".pilotage-rang-item")]
      .find((e) => e.textContent!.startsWith(p + " "))!
      .querySelector(".badge")!;
  expect(statutDe("P1.6").textContent).toBe("close");
  expect(statutDe("P1.6").className).toContain("badge--success");
  expect(statutDe("P2.73").textContent).toBe("ouverte");
  expect(statutDe("P2.73").className).toContain("pilotage-ouverte"); // contour : accent == success en couleur
});

test("clause NON satisfaite : badge warning « non satisfaite », jamais le badge de succès", async () => {
  const table = await tableEntrees();
  const ligne = within(table).getByText("P2.120").closest("tr")!;
  const badges = within(ligne).getAllByText("non satisfaite");
  expect(badges[0].className).toContain("badge--warning");
  expect(within(ligne).queryByText("satisfaite")).toBeNull();
  expect(within(ligne).getByText("grep_present=tools/x.py::y")).toBeTruthy();
});

test("affirmation permanente (holds) rompue : affichée à côté de la clause", async () => {
  const table = await tableEntrees();
  const ligne = within(table).getByText("P2.120").closest("tr")!;
  expect(within(ligne).getByText("tient :")).toBeTruthy();
  expect(within(ligne).getByText("grep_absent=tools/z.py::w")).toBeTruthy();
  expect(within(ligne).getAllByText("non satisfaite")).toHaveLength(2);
});

test("portes_agi VIDE : dit, jamais un bloc vide muet", async () => {
  const f = pilotageFixture();
  mocked.mockResolvedValue({ ...f, roadmap: { ...f.roadmap!, portes_agi: {} } });
  rendre(<PilotageRoadmapView />);
  expect(await screen.findByText(/records_graph\.json ne publie aucune porte G/)).toBeTruthy();
});

test("rythme : comptes publiés et ratio avec SA fenêtre glissante", async () => {
  await tableEntrees();
  expect(screen.getByText("2 / 1 / 0")).toBeTruthy();
  expect(screen.getByText("Science / méthodo (fichiers, 30 j depuis 2026-08-27)")).toBeTruthy();
  expect(screen.getByText("0.83")).toBeTruthy();
});

test("portes G0-G4 : cartes lues de records_graph", async () => {
  await tableEntrees();
  expect(screen.getByText("G0")).toBeTruthy();
  expect(screen.getByText("2 record(s) : EDR-001, EDR-002")).toBeTruthy();
});

test("portes_agi null : SON Empty seul, le reste de la roadmap reste servi", async () => {
  const f = pilotageFixture();
  const ligne = "graphe de records : results/records_graph.json introuvable";
  mocked.mockResolvedValue({ ...f, aveugle: [ligne], roadmap: { ...f.roadmap!, portes_agi: null } });
  rendre(<PilotageRoadmapView />);
  expect(await screen.findByText(`Portes G0-G4 indisponible — ${ligne}`)).toBeTruthy();
  expect(screen.getByRole("table", { name: "Entrées du backlog" })).toBeTruthy();
});

test("roadmap null : Empty qui reprend la ligne, aucune table", async () => {
  const ligne = "backlog : docs/roadmap/PRIORITES_ET_DETTES.md introuvable";
  mocked.mockResolvedValue(pilotageFixture({ roadmap: null, aveugle: [ligne] }));
  rendre(<PilotageRoadmapView />);
  expect(await screen.findByText(`Roadmap indisponible — ${ligne}`)).toBeTruthy();
  expect(screen.queryByRole("table")).toBeNull();
});

test("mode dégradé : alerte + Empty, aucun lien", async () => {
  mocked.mockResolvedValue(pilotageDegrade());
  rendre(<PilotageRoadmapView />);
  expect((await screen.findByRole("alert")).textContent).toContain("pilotage: ImportError");
  expect(screen.getByText(/^Roadmap indisponible — pilotage: ImportError/)).toBeTruthy();
  expect(screen.queryByRole("link")).toBeNull();
});
