import type { ReactNode } from "react";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

vi.mock("../../api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/client")>()),
  apiFetch: vi.fn(),
}));
import { apiFetch, ApiError } from "../../api/client";
import { IndexView } from "./IndexView";
import { indexFixture } from "./indexFixture";

const mocked = apiFetch as ReturnType<typeof vi.fn>;
function rendre(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}
beforeEach(() => mocked.mockResolvedValue(indexFixture()));
afterEach(() => {
  cleanup();
  mocked.mockReset();
});

test("table des familles : comptes, exclus, illisibles avec raison, champs introuvables par raison", async () => {
  rendre(<IndexView />);
  const t = await screen.findByRole("table", { name: "Familles d'artefacts" });
  const rec = within(t).getByText("record").closest("tr")!;
  expect(within(rec).getByText("4")).toBeTruthy();
  expect(within(rec).getByText("README.md")).toBeTruthy();
  expect(within(rec).getByText(/frontmatter_yaml_invalide/)).toBeTruthy();
  expect(within(rec).getAllByText("1 (frontmatter_absent 1)")).toHaveLength(2); // titre ET état
  expect(within(rec).getByText("2 (frontmatter_absent 2)")).toBeTruthy(); // date déclarée
  expect(mocked).toHaveBeenCalledWith("/api/pm/index");
});

test("famille à répertoire absent : « inconnu », jamais 0", async () => {
  rendre(<IndexView />);
  const t = await screen.findByRole("table", { name: "Familles d'artefacts" });
  const adr = within(t).getByText("adr").closest("tr")!;
  expect(within(adr).getAllByText("inconnu").length).toBeGreaterThan(0);
  expect(within(adr).queryByText("0")).toBeNull();
  expect(within(adr).queryByText("aucun")).toBeNull(); // exclus non lus : jamais « aucun » (revue du pas 1, I5)
});

test("format déclaré : un compte par clé, sans seuil ni couleur", async () => {
  rendre(<IndexView />);
  const t = await screen.findByRole("table", { name: "Familles d'artefacts" });
  const rec = within(t).getByText("record").closest("tr")!;
  expect(within(rec).getByText("date 0 · etat 0 · sujet 0 · liens 0 sur 2")).toBeTruthy();
  expect(rec.querySelector(".badge")).toBeNull();
});

test("artefact sans titre : « sans titre », jamais le nom du fichier ; sans date d'ajout : dit", async () => {
  rendre(<IndexView />);
  const t = await screen.findByRole("table", { name: "Artefacts indexés" });
  const b = within(t).getByText("docs/EDR/002_b.md").closest("tr")!;
  expect(within(b).getByText("sans titre")).toBeTruthy();
  expect(within(b).getByText("sans date d'ajout")).toBeTruthy();
});

test("dates : âge et état de l'historique publiés ; instantané absent → dit, pas de date inventée", async () => {
  rendre(<IndexView />);
  expect(await screen.findByText(/historique complet, instantané de 10 min/)).toBeTruthy();
  cleanup();
  const ligne = "dates : DATES_GIT.json introuvable à C:/x/data/pm/DATES_GIT.json -- écrivain jamais passé";
  mocked.mockResolvedValue(indexFixture({ dates: null, hors_familles: null, aveugle: [ligne] }));
  rendre(<IndexView />);
  expect(await screen.findByText(/Dates d'ajout indisponibles/)).toBeTruthy();
  expect(screen.getByText(/Fichiers hors familles : inconnus/)).toBeTruthy();
  expect(screen.getByRole("status").textContent).toContain(ligne);
});

test("hors familles : le compte et ses répertoires", async () => {
  rendre(<IndexView />);
  expect(await screen.findByText("12 fichier(s) suivi(s) hors familles : docs/roadmap 10 · docs/specs 2")).toBeTruthy();
});

test("filtre de famille et de texte ; au-delà de la limite, la coupe est DITE", async () => {
  const beaucoup = Array.from({ length: 305 }, (_, i) => ({ ...indexFixture().artefacts![0], chemin: `docs/EDR/${i}.md` }));
  mocked.mockResolvedValue(indexFixture({ artefacts: beaucoup }));
  rendre(<IndexView />);
  expect(await screen.findByText("300 affiché(s) sur 305 — affinez le filtre")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Texte"), { target: { value: "docs/EDR/12" } });
  expect(screen.getByText(/affiché\(s\) sur 305$/)).toBeTruthy();
});

test("mode dégradé : alerte + Empty ; backend injoignable : ErrorState", async () => {
  mocked.mockResolvedValue(
    indexFixture({
      aveugle: ["index: ImportError: No module named 'yaml'"],
      dates: null,
      familles: null,
      hors_familles: null,
      artefacts: null,
    }),
  );
  rendre(<IndexView />);
  expect((await screen.findByRole("alert")).textContent).toContain("index: ImportError");
  expect(screen.getByText(/^Familles indisponibles — index: ImportError/)).toBeTruthy();
  cleanup();
  mocked.mockRejectedValue(new ApiError(0, "/api/pm/index", "Timeout après 10000 ms"));
  rendre(<IndexView />);
  expect((await screen.findByRole("alert")).textContent).toContain("Erreur de chargement");
});
